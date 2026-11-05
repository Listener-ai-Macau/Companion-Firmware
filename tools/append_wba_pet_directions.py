"""Append eight whole-face up/down states to the exact current pet bank.

This is an offline resource producer, not an ordinary old-layout resource OTA.
Existing faces, glyphs and ornament payload bytes are preserved. A matching
App/Boot must adopt the resulting geometry and capability before installation.
"""
from pathlib import Path
import argparse,copy,hashlib,json,re,shutil,struct,sys,zlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/faraday_upper_art'))
from build_ui_asset_generation import encode_packbits,fnv1a32
from wba_resource_geometry import geometry,choose_static_bytes
from append_wba_pet_polish import replace_number
def sha(data):return hashlib.sha256(data).hexdigest()
def dump(p,j):p.write_bytes((json.dumps(j,ensure_ascii=False,indent=2)+'\n').encode())
def build(base,art,out,generation,soft_transitions=False):
 assert not out.exists(),'Use a fresh candidate directory'
 profile=json.loads((base/'profile.json').read_bytes());bank=(base/'ui-partition.bin').read_bytes()
 assert generation>profile['generation'] and sha(bank).upper()==profile['uiPartitionSha256'].upper()
 old_geo=geometry(len(bank),profile['flashGeometry']['norBytes']);assert old_geo==profile['flashGeometry']
 root=bytearray(bank[old_geo['rootA']:old_geo['rootA']+128]);assert root[:4]==b'CUIR' and zlib.crc32(root[:124])==struct.unpack_from('<I',root,124)[0]
 bo,bs=struct.unpack_from('<II',root,16);mo,ms,mc=struct.unpack_from('<III',root,28)
 old_blob=bank[bo:bo+bs];manifest=old_blob[:ms]
 assert mo==0 and manifest[:4]==b'CUIM' and zlib.crc32(manifest)==mc and zlib.crc32(old_blob)==struct.unpack_from('<I',root,24)[0]
 count,row_bytes=struct.unpack_from('<HH',manifest,8);assert row_bytes==24 and ms==32+count*24 and count==profile['stateCount']
 old_rows=[list(struct.unpack_from('<IHHIIHHI',manifest,32+i*24)) for i in range(count)]
 assert all(a[0]<b[0] for a,b in zip(old_rows,old_rows[1:]))
 choices=[(name,d) for name in ('dejected','protest','nervous','proud')
          for d in (('center','left','right','up','down') if soft_transitions else ('up','down'))]
 selected={}
 if soft_transitions:
  # A partial library must never pull a directional face back to centre.
  selection=json.loads((art/'design-set-complete.json').read_bytes())
  assert selection['schema']=='companion.pet-soft-transition-p132.art.v2'
  selected={(row['emotion'],row['direction']):row for row in selection['frames']}
  assert len(selected)==len(selection['frames'])==20 and set(selected)==set(choices)
  assert all(row['nativeReview']=='AGENT_STATIC_WHOLE_FACE_SELECTED' for row in selected.values())
 shift=len(choices)*24;rows=copy.deepcopy(old_rows);hashes={x[0] for x in rows}
 for row in rows:
  if row[2]:
   assert bo+ms<=row[4] and row[4]+row[5]<=bo+bs
   assert zlib.crc32(bank[row[4]:row[4]+row[5]])==row[7]
   row[4]+=shift
 payload=bytearray();added=[]
 for name,direction in choices:
  state='pet_emotion_'+name+('' if direction=='center' else '_'+direction)+('_soft' if soft_transitions else '')
  h=fnv1a32(state)
  if soft_transitions:
   source=selected[(name,direction)]['files']['frame'];frame=(art/source['path']).read_bytes()
   assert sha(frame)==source['sha256']
  else:frame=(art/(name+'-'+direction+'-frame.bin')).read_bytes()
  assert h not in hashes and len(frame)==5000 and frame[:400]==b'\xff'*400
  packed=encode_packbits(frame);offset=bo+bs+shift+len(payload)
  rows.append([h,65535,2,zlib.crc32(frame),offset,len(packed),1000,zlib.crc32(packed)]);hashes.add(h);payload.extend(packed)
  added.append(dict(state=state,frameSha256=sha(frame),payloadBytes=len(packed),payloadOffset=offset,closedEyesMask=1 if name=='proud' else 0))
 rows.sort(key=lambda x:x[0]);mh=bytearray(manifest[:32]);struct.pack_into('<H',mh,8,len(rows));struct.pack_into('<I',mh,12,ms+shift)
 new_manifest=bytes(mh)+b''.join(struct.pack('<IHHIIHHI',*row) for row in rows)
 blob=new_manifest+old_blob[ms:]+payload;used=bo+len(blob)
 geo=geometry(max(len(bank),choose_static_bytes(used,old_geo['norBytes'])),old_geo['norBytes'])
 identity=sha(bytes.fromhex(profile['resourceId'])+(b'Companion pet soft transitions P132\0' if soft_transitions else b'Companion pet vertical directions P110\0')+blob).upper()
 struct.pack_into('<I',root,8,generation);struct.pack_into('<II',root,20,len(blob),zlib.crc32(blob));struct.pack_into('<II',root,32,len(new_manifest),zlib.crc32(new_manifest));struct.pack_into('<I',root,40,(used+4095)&~4095)
 root[44:76]=bytes.fromhex(identity);struct.pack_into('<I',root,124,zlib.crc32(root[:124]))
 new_bank=bytearray(b'\xff'*geo['staticBytes']);new_bank[:bo]=bank[:bo];new_bank[bo:used]=blob;new_bank[geo['rootA']:geo['rootA']+128]=root
 assert new_bank[bo+ms+shift:bo+bs+shift]==old_blob[ms:]
 indexed={row[0]:row for row in rows}
 for before in old_rows:
  after=indexed[before[0]];assert before[:4]==after[:4] and before[5:]==after[5:]
  if before[2]:assert new_bank[after[4]:after[4]+after[5]]==bank[before[4]:before[4]+before[5]]
 out.mkdir(parents=True)
 for p in base.glob('*.h'):shutil.copyfile(p,out/p.name)
 ao=profile['externalUi']['extensionOffset']+shift;external=bytes(new_bank[ao:used])
 header=(base/'companion_wba_external_ui.h').read_text();header=replace_number(header,'COMP_WBA_EXTERNAL_UI_OFFSET',ao);header=replace_number(header,'COMP_WBA_EXTERNAL_UI_BYTES',len(external))
 header,n=re.subn(r'(COMP_WBA_EXTERNAL_UI_CRC32 )0x[0-9A-Fa-f]+u',r'\g<1>0x%08Xu'%zlib.crc32(external),header);assert n==1
 (out/'companion_wba_external_ui.h').write_text(header,encoding='utf8',newline='\n')
 capability='COMPANION_WBA_PET_EMOTION_SOFT_V6' if soft_transitions else 'COMPANION_WBA_PET_EMOTION_VERTICAL_V5'
 contract=(base/'companion_wba_resource_contract.h').read_text();assert '#define COMPANION_WBA_PET_EMOTION_DIRECTIONS_V4 1' in contract and capability not in contract
 if soft_transitions:assert '#define COMPANION_WBA_PET_EMOTION_VERTICAL_V5 1' in contract
 contract=replace_number(contract,'COMPANION_WBA_RESOURCE_GENERATION',generation);contract=replace_number(contract,'COMPANION_WBA_RESOURCE_STATE_COUNT',len(rows));contract=contract.replace(profile['resourceId'],identity)
 contract=contract.replace('#include <stdint.h>','#include <stdint.h>\n#define '+capability+' 1')
 (out/'companion_wba_resource_contract.h').write_text(contract,encoding='utf8',newline='\n');(out/'ui-partition.bin').write_bytes(new_bank)
 ext=copy.deepcopy(profile['externalUi']);ext.update(extensionOffset=ao,extensionBytes=len(external),headerSha256=sha((out/'companion_wba_external_ui.h').read_bytes()),generation=generation,newBankSha256=sha(new_bank))
 if 'addedOffset' in ext:ext['addedOffset']+=shift
 result=dict(schema='companion.pet-soft-transition-resource.v1' if soft_transitions else 'companion.pet-vertical-resource.v1',generation=generation,baseGeneration=profile['generation'],newStateCount=len(rows),addedStates=added,originalStatePixelsPreserved=True,originalAtlasAndPayloadBytesPreserved=True,addedFramePayloadBytes=len(payload),oldGeometry=old_geo,newGeometry=geo,geometryChanged=old_geo!=geo,pairedAppBootGeometryRequired=True,ordinaryOldGeometryOtaAllowed=False,resourceArenaUsedBytes=used,arenaFreeBytes=geo['rootA']-used,imageSha256=sha(new_bank),fullFirmwareBuilt=False,installed=False,physicalQualified=False,testsRun=False)
 profile.update(generation=generation,resourceId=identity,stateCount=len(rows),uiPartitionBytes=len(new_bank),uiPartitionSha256=sha(new_bank).upper(),resourceArenaUsedBytes=used,resourceBudgetBytes=len(new_bank),generationBytes=len(blob),flashGeometry=geo,externalUi=ext,recordingRegionPreserved=old_geo==geo,dynamicRegionIncluded=False,hardwareAcceptance='NOT_RUN',fullChainAcceptance='NOT_RUN',result='RESOURCE_CANDIDATE_BUILT')
 profile['petSoftTransitions' if soft_transitions else 'petVertical']=result
 for p in [Path(__file__),*out.glob('*.h')]:profile.setdefault('sourceSha256',{})[str(p)]=sha(p.read_bytes()).upper()
 dump(out/'profile.json',profile);dump(out/('pet-transitions.json' if soft_transitions else 'pet-vertical.json'),result);return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('base','art','output'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--generation',type=int,required=True);p.add_argument('--soft-transitions',action='store_true')
 a=p.parse_args();j=build(a.base.resolve(),a.art.resolve(),a.output.resolve(),a.generation,a.soft_transitions)
 print(json.dumps({k:j[k] for k in ('generation','newStateCount','addedFramePayloadBytes','newGeometry','imageSha256','installed')}))
