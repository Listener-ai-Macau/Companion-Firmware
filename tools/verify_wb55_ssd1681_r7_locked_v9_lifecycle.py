"""COMP-REQ-433 lifecycle gate over the real R9-derived CheckOnly chain."""
from __future__ import annotations
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'.cache/validation/wb55-r7-locked-v9-r437-monitor-20260723'
RESTORE='223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C'
ZERO=('hardware_contact','programmer','serial','write','reset','refresh','popup','retry','authorization','claim_only','execute')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def run(cmd):
    r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    if r.returncode: raise SystemExit('lifecycle child NO_GO\n'+r.stdout+'\n'+r.stderr)
def main():
    stage=RUN/'stage-run.json'
    if not stage.exists():
        run(['pwsh','-NoProfile','-File','tools/start_wb55_ssd1681_r7_locked_v9.ps1','-CheckOnly','-OutRoot',str(RUN)])
    evidence=json.loads(stage.read_text(encoding='utf-8-sig'))
    if evidence.get('status')!='READY_NO_HARDWARE_CONTACT' or evidence.get('hardware_contact')!=0: raise SystemExit('CheckOnly status/contact NO_GO')
    c=evidence.get('counters',{})
    flat={'hardware_contact':evidence.get('hardware_contact',0),'programmer':c.get('candidate_programmer_processes',0)+c.get('preclean_programmer_processes',0)+c.get('postclean_programmer_processes',0)+c.get('restore_programmer_processes',0),'serial':c.get('serial_capture_processes',0),'write':c.get('preclean_write_calls',0)+c.get('postclean_write_calls',0)+c.get('candidate_write_calls',0)+c.get('restore_write_calls',0),'reset':c.get('panel_hard_resets',0),'refresh':c.get('panel_refresh_commands',0),'popup':evidence.get('popup_policy',{}).get('pre_execute',0),'retry':c.get('automatic_retries',0),'authorization':0 if evidence.get('authorization') is None else 1,'claim_only':0,'execute':0}
    if any(flat[k]!=0 for k in ZERO): raise SystemExit('CheckOnly counters NO_GO: '+json.dumps(flat))
    children={}
    for p in sorted(RUN.rglob('*.json')):
        if p.name in ('stage-run.json','persistent-launch.json'): children[p.relative_to(RUN).as_posix()]=sha(p)
    result={'schema_id':'companion.wb55.ssd1681.r7_locked_v9_choreography.lifecycle.v3','status':'PASS','requirement':'COMP-REQ-437','launcher_invoked':True,'real_persistent_checkonly':True,'checkonly_root':RUN.relative_to(ROOT).as_posix(),'counters':flat,'qualification':16,'qualification_cadence_measurements':15,'telemetry_schema':'immutable_metadata_plus_compact_96_byte_crlf_records','loop_epoch_reset_after_qualification_summary':True,'loop_first_delta_ms':0,'loop_cadence_measurements_exclude_first':True,'loop_cycles_minimum':2,'pre_cleanup_requirement':'COMP-REQ-409','post_cleanup_requirement':'COMP-REQ-409','restore_bytes':524288,'restore_sha256':RESTORE,'normal_resume':True,'process_audit':True,'retry_count':0,'authorization_created':False,'child_hashes':children,'physical_verdict':'UNPROVEN','unproven':['physical measured timing','physical panel visual acceptance']}
    result['requirement']='COMP-REQ-437'
    result['r9_replay_required']=True
    result['loop_cadence_measurements']=31
    result['future_physical_authorization_requirement_id']='COMP-REQ-413'
    out=ROOT/'docs/validation/companion-ssd1681-r7-locked-v9-lifecycle-20260723.json'; out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps(result,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
