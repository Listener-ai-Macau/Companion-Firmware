"""Group CRC/channel-qualified observed recording events, retaining RF gaps.

Matches private bytes only through the existing independent RF proof. Outputs
counts/timing/offset metadata, never audio, keys or packet plaintext. A partial
file remains partial; observed events are not a lossless capture claim.
"""
from pathlib import Path
from collections import defaultdict,Counter
import argparse,bisect,hashlib,json,statistics
from analyze_companion_ota_events import channel2
from analyze_companion_ota_rf_windows import require
from analyze_wba_air_nvm import wire_crc
from companion_rf_clock import ReceiverClock

def analyze(capture,prefix,hci_comparison):
 require(all(c.isalnum() or c in '-_' for c in prefix),'Invalid prefix')
 proof=json.loads((capture/(prefix+'current-bond-independent-rf-proof.json')).read_bytes())
 meta=json.loads((capture/(prefix+'rf-transport-metadata.json')).read_bytes())
 source=capture/'packets-private.jsonl';sha=hashlib.sha256(source.read_bytes()).hexdigest()
 require(sha==proof['sourcePacketsSha256']==meta['sourceSha256'],'RF identity differs')
 clock=ReceiverClock.read(source);proof,meta=clock.normalize(proof),clock.normalize(meta)
 epochs=[e for e in proof['epochs'] if e.get('recordingChunks',0)]
 require(len(epochs)==1,'Recording epoch ambiguous');epoch=epochs[0];aa=epoch['aa']
 chunks=sorted([c for c in meta['canonicalRecordingChunks'] if c['aa']==aa],key=lambda c:c['offset'])
 require(chunks and sum(c['bytes'] for c in chunks)==epoch['recordingBytesCovered'],'Observed coverage differs')
 start,end=chunks[0]['firstUs'],chunks[-1]['lastUs']
 mic={p['us']:p for p in meta['micVerifiedPackets'] if p['aa']==aa}
 devices=sorted([p for p in mic.values() if p['direction']==0 and p['llid'] in (1,2) and not p['duplicateCounter']],key=lambda p:p['us'])
 times=[p['us'] for p in devices];keys=set();completions=defaultdict(list)
 for c in chunks:
  fs=devices[bisect.bisect_left(times,c['firstUs']):bisect.bisect_right(times,c['lastUs'])]
  require([p['bytes']-4 for p in fs]==c['llFragments'],'Recording fragments not independently associated')
  keys.update((p['session'],p['counter']) for p in fs);completions[c['lastUs']].append(c)
 connects=[];frames=[]
 for row in clock.rows:
  raw=bytes.fromhex(row['pdu'])
  if len(raw)<2 or len(raw)!=2+raw[1] or not row['crcValid']:continue
  if row['aa']=='8e89bed6' and len(raw)==36 and raw[0]&15==5 and f'{int.from_bytes(raw[14:18],"little"):08x}'==aa and wire_crc(raw,0x555555)==row['crc']:connects.append((row,raw))
  if row['aa']==aa and row['deviceTimestampUs']<=end:frames.append((row,raw))
 require(len(connects)==1,'CONNECT not unique');connect,raw_connect=connects[0]
 require(raw_connect[0]&32,'CSA2 required')
 require(bytes.fromhex(proof['target'].replace(':',''))[::-1]==raw_connect[8:14],'Peer differs')
 require([channel2(i,(1<<37)-1,0x8e89bed6) for i in range(4)]==[25,20,6,21],'SIG CSA2 sample differs')
 seed=int.from_bytes(raw_connect[18:21],'big');valid=[];rejected=0
 for row,raw in frames:
  if wire_crc(raw,seed)!=row['crc']:rejected+=1;continue
  if row['deviceTimestampUs']<=connect['deviceTimestampUs']:continue
  valid.append(dict(us=row['deviceTimestampUs'],endUs=row['deviceTimestampUs']+(11+raw[1])*4,channel=row['channel'],hint=row['direction'],bytes=raw[1],llid=raw[0]&3,md=bool(raw[0]&16),sn=(raw[0]>>3)&1,nesn=(raw[0]>>2)&1,mic=mic.get(row['deviceTimestampUs'])))
 valid.sort(key=lambda x:x['us']);ci=int.from_bytes(raw_connect[24:26],'little')*1250
 earliest=connect['deviceTimestampUs']+(10+raw_connect[1])*8+1250+int.from_bytes(raw_connect[22:24],'little')*1250;latest=earliest+raw_connect[21]*1250
 first=next(x for x in valid if x['hint']==1);possible=[(n,first['us']-n*ci) for n in range(8) if earliest<=first['us']-n*ci<=latest]
 require(len(possible)==1,'Initial event phase ambiguous');first_index,anchor=possible[0]
 schedule=[dict(event=0,anchorUs=anchor,intervalUs=ci)]
 for c in sorted([c for c in epoch['authenticatedControls'] if c['opcode']=='0x0'],key=lambda c:c['instant']):
  prev=schedule[-1];require(prev['event']<c['instant']<65536,'Unsupported event wrap/order')
  schedule.append(dict(event=c['instant'],anchorUs=prev['anchorUs']+(c['instant']-prev['event'])*prev['intervalUs']+c['windowOffsetUnits']*1250,intervalUs=c['intervalUnits']*1250))
 maps=[(0,int.from_bytes(raw_connect[30:35],'little'))]+[(c['instant'],int.from_bytes(bytes.fromhex(c['channelMap']),'little')) for c in epoch['authenticatedControls'] if c['opcode']=='0x1'];maps.sort()
 anchors=[x['anchorUs'] for x in schedule];map_events=[x[0] for x in maps];groups=defaultdict(list);matched=0;mismatches=[]
 for row in valid:
  if not start<=row['us']<=end:continue
  s=schedule[max(0,bisect.bisect_right(anchors,row['us']+100)-1)];event=s['event']+(row['us']-s['anchorUs']+100)//s['intervalUs'];channelmap=maps[bisect.bisect_right(map_events,event)-1][1]
  predicted=channel2(event,channelmap,int(aa,16))
  if predicted!=row['channel']:mismatches.append(dict(us=row['us'],event=event,observed=row['channel'],predicted=predicted))
  else:matched+=1
  groups[event].append(row)
 require(not mismatches,f'Event/channel mismatch: {len(mismatches)}')
 comparison=json.loads(hci_comparison.read_bytes());case=comparison['rows'][-1]
 # Match exact application offsets across RF/HCI. This is NOT a fitted
 # absolute RF/HCI clock, and mixed boundary events remain unclassified.
 classic=hci_comparison.parent/'current-private-derived.pcap'
 import sys
 sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'Companion-Type/tools'))
 from analyse_upload_joint_timeline import read_hci
 ns,*_=read_hci(classic,proof['target'],proof['recordingId']);hci_start=ns[0]['first'];cohorts={}
 bins=case['secondBins']
 for n in ns:
  second=min(int(n['last']-hci_start),len(bins)-1);amount=bins[second]['foreignAclBytes']
  cohorts[n['offset']]='quiet' if amount<=64 else ('busy' if amount>=4096 else 'mixed')
 rows=[];groupkeys=sorted(groups)
 for i,event in enumerate(groupkeys):
  ps=groups[event];ds=[p for p in ps if p['mic'] and p['mic']['direction']==0 and p['llid'] in (1,2)]
  completed=[c for p in ds if not p['mic']['duplicateCounter'] for c in completions.get(p['us'],[])]
  if not completed:continue
  last=ds[-1];later=[p for p in ps if p['us']>last['us']]
  ack=bool(later and later[0]['bytes']==0 and later[0]['nesn']==1-last['sn'] and abs(later[0]['us']-last['endUs']-150)<=20)
  labels={cohorts.get(c['offset'],'unmatched') for c in completed};cohort=next(iter(labels)) if len(labels)==1 else 'mixed'
  rows.append(dict(event=event,firstUs=ps[0]['us'],observedSpanUs=ps[-1]['endUs']-ps[0]['us'],cohort=cohort,observedPackets=len(ps),recordingChunks=len(completed),recordingBytes=sum(c['bytes'] for c in completed),chunkUsefulBytes=dict(Counter(c['bytes'] for c in completed)),deviceDataPackets=len(ds),duplicateDevicePackets=sum(p['mic']['duplicateCounter'] for p in ds),lastDeviceMd=last['md'],lastDeviceObservedEmptyAck=ack,gapToNextObservedEventUs=groups[groupkeys[i+1]][0]['us']-ps[-1]['endUs'] if i+1<len(groupkeys) else None))
 require(sum(x['recordingBytes'] for x in rows)==epoch['recordingBytesCovered'],'Observed event coverage differs')
 def summarize(rs):
  geometry=Counter()
  for row in rs:geometry.update(row['chunkUsefulBytes'])
  return dict(events=len(rs),observedRecordingBytes=sum(x['recordingBytes'] for x in rs),recordingChunks=sum(x['recordingChunks'] for x in rs),chunkUsefulBytes=dict(geometry),chunksPerObservedEvent=statistics.mean(x['recordingChunks'] for x in rs) if rs else None,medianObservedSpanUs=statistics.median(x['observedSpanUs'] for x in rs) if rs else None,oneChunkEvents=sum(x['recordingChunks']==1 for x in rs),lastDeviceMd1=sum(x['lastDeviceMd'] for x in rs),lastDeviceMd1AckObserved=sum(x['lastDeviceMd'] and x['lastDeviceObservedEmptyAck'] for x in rs),duplicateDevicePackets=sum(x['duplicateDevicePackets'] for x in rs))
 return dict(schema='companion.recording.observed_events.v2',qualification='OBSERVED_CRC_MIC_CHANNEL_QUALIFIED_RF_GAPS_RETAINED',accessAddress=aa,sourcePacketsSha256=sha,rfFileComplete=epoch['fullRecordingRfCoverageQualified'],rfCoveredBytes=epoch['recordingBytesCovered'],rfExpectedBytes=proof['recordingImageBytes'],rfGaps=epoch['recordingGapRanges'],initialAnchorUs=anchor,firstObservedCentralEvent=first_index,intervalSchedule=schedule,roiObservedPackets=matched,rejectedCrcPackets=rejected,channelMismatches=0,all=summarize(rows),cohorts={k:summarize([x for x in rows if x['cohort']==k]) for k in ('quiet','busy','mixed','unmatched')},same199UsefulByteEvents={k:summarize([x for x in rows if x['cohort']==k and set(x['chunkUsefulBytes'])=={199}]) for k in ('quiet','busy')},rows=rows,limits=['Observed ROI channels all checked against CONNECT+authenticated instants and CSA2; absent packets/events are not invented.','Offset association maps a notification to its host1s traffic cohort, not exact RF/HCI time alignment or proof of unique causal interference.','Empty ACK evidence is CRC/sequence/IFS only; noMIC and no guarantee its recipient received it.','Only independent canonical recording chunks count as new bytes. Missing RF bytes are never filled from HCI.','MD and short events do not uniquely identify central scheduling, WBA dispatch or RF retries.'])

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capture',type=Path,required=True);p.add_argument('--proof-prefix',required=True);p.add_argument('--hci-comparison',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 x=analyze(a.capture,a.proof_prefix,a.hci_comparison);a.output.write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({k:v for k,v in x.items() if k not in ('rows','limits','rfGaps')}))
