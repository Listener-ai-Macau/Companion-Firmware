"""R7 compact telemetry parser: immutable metadata plus bounded records."""
from __future__ import annotations
import argparse,re,json
from pathlib import Path
META=re.compile(r"^\[epaper\] r7_locked_v9 metadata schema=v2 frame_count=16 frame_bytes=5000 payload_bytes=2610 window=x4-21,y26-170 controller_y=173-29 control=0xCF refresh=0x20 busy_limit=600 transaction_limit=480 cadence_limit=480 ring=65536 cleanup=COMP-REQ-409 production_enabled=0$")
MOVE=re.compile(r"^\[epaper\] r7 phase=(q|l) (index|iteration)=(\d+) previous=(\d+) current=(\d+) ready=(\d+) t=(\d+) b=(\d+) d=(\d+) result=(ok|no_go)$")
def parse(text:str, hardware_contact:int=0)->dict[str,object]:
 lines=text.splitlines()
 if sum(bool(META.match(x)) for x in lines)!=1 or any('r7_locked_v9 movement' in x for x in lines): raise ValueError('metadata missing or old verbose record')
 rec=[]
 for line in lines:
  m=MOVE.match(line)
  if m: rec.append((m.group(1),int(m.group(3)),int(m.group(4)),int(m.group(5)),int(m.group(6)),int(m.group(8)),int(m.group(7)),int(m.group(9)),m.group(10)))
 q=[x for x in rec if x[0]=='q']; loop=[x for x in rec if x[0]=='l']
 if len(q)!=16 or len(loop)<32 or len(loop)%16: raise ValueError('qualification/loop count')
 for i,x in enumerate(q):
  _,ordr,prev,cur,ready,busy,t,d,res=x
  if (ordr,prev,cur,ready,res)!=(i+1,16 if i==0 else i,i+1,1,'ok') or busy>600 or t>480 or (d!=0 if i==0 else not 1<=d<=480): raise ValueError('qualification record')
 for cycle in range(len(loop)//16):
  for i,x in enumerate(loop[cycle*16:(cycle+1)*16]):
   _,ordr,prev,cur,ready,busy,t,d,res=x
   if ordr!=cycle*16+i+1 or prev!=(16 if i==0 else i) or cur!=i+1 or ready!=1 or res!='ok' or busy>600 or t>480 or (d!=0 if cycle==0 and i==0 else not 1<=d<=480): raise ValueError('loop record')
 if any(x in text for x in ('0x26','0x32','0x37','0xF7','0xC7','retry=1','fault=','old verbose')): raise ValueError('forbidden/fault telemetry')
 cleanup=[x for x in lines if 'phase=cleanup' in x]
 if cleanup and not all('dual_plane_white=1' in x and 'result=ok' in x for x in cleanup): raise ValueError('cleanup')
 cadence=max(0,len(loop)-1)
 deltas=[x[7] for x in q[1:]]+[x[7] for x in loop[1:]]
 return {'status':'PASS_R7_LOCKED_V9_CHOREOGRAPHY_LOG','metadata':True,'metadata_proof':True,'qualification':16,'qualification_frames':16,'qualification_cadence_measurements':15,'loop_records':len(loop),'cadence_measurements':cadence,'busy_max':max(x[5] for x in rec),'transaction_max':max(x[6] for x in rec),'start_delta_max':max(deltas),'start_delta_max_ms':max(deltas),'max_start_delta_ms':max(deltas),'continuous':True,'hardware_contact':int(hardware_contact)}
def parse_tail(text:str, hardware_contact:int=0)->dict[str,object]:
 lines=[x for x in text.splitlines() if x]
 if any(x.startswith('[r7] fault') or 'retry=1' in x or 'result=no_go' in x for x in lines): raise ValueError('tail fault/retry')
 rec=[]
 for line in lines:
  m=MOVE.match(line)
  if m and m.group(1)=='l': rec.append((int(m.group(3)),int(m.group(4)),int(m.group(5)),int(m.group(6)),int(m.group(8)),int(m.group(7)),int(m.group(9)),m.group(10)))
 if len(rec)!=2: raise ValueError('tail must contain exactly two loop records')
 a,b=rec
 if b[0]!=a[0]+1 or b[1] != a[2] or a[3]!=1 or b[3]!=1 or a[7]!='ok' or b[7]!='ok' or max(a[4],b[4])>600 or max(a[5],b[5])>480 or max(a[6],b[6])>480 or int(hardware_contact) not in (0,1): raise ValueError('tail continuity/threshold')
 return {'status':'PASS_R7_LOCKED_V9_TAIL','records':2,'first_iteration':a[0],'last_iteration':b[0],'hardware_contact':int(hardware_contact)}
def self_test():
 meta='[epaper] r7_locked_v9 metadata schema=v2 frame_count=16 frame_bytes=5000 payload_bytes=2610 window=x4-21,y26-170 controller_y=173-29 control=0xCF refresh=0x20 busy_limit=600 transaction_limit=480 cadence_limit=480 ring=65536 cleanup=COMP-REQ-409 production_enabled=0'
 def rec(p,n,prev,cur,d=470,t=452): return f'[epaper] r7 phase={p} {"index" if p=="q" else "iteration"}={n} previous={prev} current={cur} ready=1 t={t} b=443 d={d} result=ok'
 records=[rec('q',i,16 if i==1 else i-1,i,0 if i==1 else 470) for i in range(1,17)] + [rec('l',i,16 if i%16==1 else (i-2)%16+1,(i-1)%16+1,0 if i==1 else 470) for i in range(1,33)]
 good=meta+'\n'+'\n'.join(records)
 parse(good); negatives={}
 fixtures={'missing_metadata':good.replace(meta,''),'verbose':good.replace(records[0],'[epaper] r7_locked_v9 movement previous=16 current=1 ready=1'),'skip':good.replace('iteration=2','iteration=3',1),'duplicate':good.replace(records[10],records[9],1),'malformed':good.replace('result=ok','result=maybe',1),'over481':good.replace('t=452 b=443','t=481 b=443',1),'delta481':good.replace('d=470','d=481',1),'fault':good+'\nfault=1','retry':good+'\nretry=1','carry_over_487':good.replace(records[16],records[16].replace('d=0','d=487'),1),'loop_first_nonzero':good.replace(records[16],records[16].replace('d=0','d=1'),1),'loop_second_zero':good.replace(records[17],records[17].replace('d=470','d=0'),1)}
 for name,value in fixtures.items():
  try: parse(value); negatives[name]=False
  except ValueError: negatives[name]=True
 if not all(negatives.values()): raise AssertionError(negatives)
 boundary=good.replace('t=452','t=480',1); parse(boundary); negatives['transaction_480_pass']=True
 try: parse(boundary.replace('t=480','t=481',1)); negatives['transaction_481_reject']=False
 except ValueError: negatives['transaction_481_reject']=True
 return {'positive':True,'max_record_bytes':max(len(x.encode('ascii'))+2 for x in records),'negative':negatives}
def render_record(sequence:int,key:str)->str:
 phase='q' if key=='q' else 'l'; name='index' if phase=='q' else 'iteration'
 return f'[epaper] r7 phase={phase} {name}={sequence} previous=1 current=2 ready=1 t=452 b=443 d=470 result=ok'
def parse_metadata(line:str)->dict[str,object]:
 if not META.match(line): raise ValueError('metadata mismatch')
 return {'metadata_proof':True}
def validate_loop_line(line:str,**_:object)->dict[str,object]:
 if not MOVE.match(line): raise ValueError('invalid compact record')
 return {'valid':True}
def cli()->int:
 ap=argparse.ArgumentParser(); ap.add_argument('--self-test',action='store_true'); ap.add_argument('--log'); ap.add_argument('--tail-log'); ap.add_argument('--artifact'); ap.add_argument('--write',action='store_true'); ap.add_argument('--validate-loop-line'); ap.add_argument('--sequence-key'); ap.add_argument('--sequence',type=int); ap.add_argument('--previous',type=int); ap.add_argument('--current',type=int); ap.add_argument('--minimum-loop-iterations',type=int); ap.add_argument('--hardware-contact',type=int,default=0); a=ap.parse_args()
 if a.self_test: print(self_test()); return 0
 if a.validate_loop_line: validate_loop_line(a.validate_loop_line); return 0
 if a.tail_log:
  result=parse_tail(Path(a.tail_log).read_text(encoding='utf-8'),a.hardware_contact); Path(a.artifact).write_text(json.dumps(result,sort_keys=True)+'\n',encoding='utf-8') if a.artifact and a.write else None; print(json.dumps(result)); return 0
 if a.log:
  result=parse(Path(a.log).read_text(encoding='utf-8'),a.hardware_contact); Path(a.artifact).write_text(json.dumps(result,sort_keys=True)+'\n',encoding='utf-8') if a.artifact and a.write else None; print(json.dumps(result)); return 0
 return 2
if __name__=='__main__': raise SystemExit(cli())
