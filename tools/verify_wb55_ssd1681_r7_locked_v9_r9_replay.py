"""Permanent offline replay of the real R9 telemetry qualification path."""
from __future__ import annotations
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SNAPSHOT=ROOT/'.cache/validation/wb55-r7-locked-v9-execute-20260723-r9/continuous-monitor/qualification-snapshot.log'
OUT=ROOT/'docs/validation/companion-ssd1681-r7-locked-v9-r9-replay-20260723.json'
sys.path.insert(0,str(ROOT/'tools'))
import verify_wb55_ssd1681_r7_locked_v9_parser as parser
def sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def required(result:dict, expected_contact:int=0)->None:
    keys=('status','metadata_proof','qualification_frames','qualification_cadence_measurements','loop_records','cadence_measurements','start_delta_max','transaction_max','busy_max','continuous','hardware_contact')
    if any(k not in result for k in keys): raise AssertionError('artifact missing key')
    if not (result['status']=='PASS_R7_LOCKED_V9_CHOREOGRAPHY_LOG' and result['metadata_proof'] is True and result['qualification_frames']==16 and result['qualification_cadence_measurements']==15 and result['loop_records']==32 and result['cadence_measurements']==result['loop_records']-1 and result['start_delta_max']<=480 and result['transaction_max']<=480 and result['busy_max']<=600 and result['continuous'] is True and result['hardware_contact']==expected_contact): raise AssertionError('artifact qualification/contact proof')
def main()->int:
    if not SNAPSHOT.is_file(): raise SystemExit('missing real R9 telemetry snapshot')
    text=SNAPSHOT.read_text(encoding='utf-8'); result=parser.parse(text,0); required(result,0)
    replay_root=ROOT/'.cache/validation/wb55-r7-locked-v9-r434-replay-20260723'
    replay_root.mkdir(parents=True,exist_ok=True)
    command=['pwsh','-NoProfile','-File',str(ROOT/'tools/monitor_wb55_ssd1681_r7_locked_v9.ps1'),'-ReplaySnapshot',str(SNAPSHOT),'-OutDir',str(replay_root)]
    run=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    if run.returncode!=0: raise SystemExit('monitor replay NO_GO\n'+run.stdout+'\n'+run.stderr)
    monitor_result=json.loads((replay_root/'monitor-result.json').read_text(encoding='utf-8-sig'))
    if monitor_result.get('status')!='REPLAY_READY_NO_HARDWARE_CONTACT' or monitor_result.get('hardware_contact')!=0 or monitor_result.get('popup_count')!=0 or monitor_result.get('loop_records_seen',0)<32: raise SystemExit('monitor finalization replay binding NO_GO')
    qualification_artifact=json.loads((replay_root/'qualification-parser.json').read_text(encoding='utf-8-sig')); required(qualification_artifact,0)
    final_artifact=json.loads((replay_root/'final-loop-parser.json').read_text(encoding='utf-8-sig')); required(final_artifact,0)
    tail_artifact=json.loads((replay_root/'tail-parser.json').read_text(encoding='utf-8-sig'))
    if tail_artifact.get('status')!='PASS_R7_LOCKED_V9_TAIL' or tail_artifact.get('records')!=2 or tail_artifact.get('hardware_contact')!=0: raise SystemExit('tail artifact NO_GO')
    physical=json.loads(subprocess.run(['python','tools/verify_wb55_ssd1681_r7_locked_v9_parser.py','--log',str(SNAPSHOT),'--hardware-contact','1'],cwd=ROOT,capture_output=True,text=True,check=True).stdout)
    required(physical,1)
    formatted=json.dumps(result,indent=2,sort_keys=False); reordered=json.dumps(result,sort_keys=True,separators=(',',':'))
    if json.loads(formatted)!=json.loads(reordered): raise AssertionError('JSON formatting changed object identity')
    negatives={'contact_mismatch':False,'tail_skip':False,'tail_duplicate':False,'tail_481':False,'tail_fault':False}
    try: required(result,1)
    except AssertionError: negatives['contact_mismatch']=True
    tail_lines='\n'.join([x for x in text.splitlines() if 'phase=l iteration=' in x][-2:])+'\n'
    tail_fixtures={'tail_skip':tail_lines.replace('iteration=32','iteration=33',1),'tail_duplicate':tail_lines.replace('iteration=32','iteration=31',1),'tail_481':tail_lines.replace('d=478','d=481',1),'tail_fault':tail_lines+'[r7] fault reason=simulated\n'}
    for name,value in tail_fixtures.items():
        try: parser.parse_tail(value,0)
        except ValueError: negatives[name]=True
    for name,mut in {'artifact_content_tampered':{**result,'status':'FAIL'},'artifact_missing_key':{k:v for k,v in result.items() if k!='loop_records'},'artifact_wrong_status':{**result,'status':'NO_GO'}}.items():
        try: required(mut,0); negatives[name]=False
        except AssertionError: negatives[name]=True
    if not all(negatives.values()): raise AssertionError(negatives)
    if not all(negatives.values()): raise AssertionError(negatives)
    out={'schema_id':'companion.wb55.ssd1681.r7_locked_v9.r9_replay.v3','status':'PASS_R9_REAL_TELEMETRY_REPLAY','source_snapshot':SNAPSHOT.relative_to(ROOT).as_posix(),'source_snapshot_sha256':sha(SNAPSHOT),'monitor_replay_root':replay_root.relative_to(ROOT).as_posix(),'monitor_result_sha256':sha(replay_root/'monitor-result.json'),'qualification_artifact_sha256':sha(replay_root/'qualification-parser.json'),'final_artifact_sha256':sha(replay_root/'final-loop-parser.json'),'tail_artifact_sha256':sha(replay_root/'tail-parser.json'),'qualification_frames':16,'qualification_cadence_measurements':15,'loop_records':result['loop_records'],'loop_cadence_measurements':result['cadence_measurements'],'loop_cycles':result['loop_records']//16,'serial_collect_to_parser_to_shared_finalization':True,'prompt_eligible_after_complete_two_cycles':True,'hardware_contact':0,'popup_count':0,'stdout_not_identity':True,'formatting_key_order_insensitive':True,'negative_fixtures':negatives,'parser_result':result,'synthetic_physical_contact_artifact_validated':True}
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps(out,indent=2,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
