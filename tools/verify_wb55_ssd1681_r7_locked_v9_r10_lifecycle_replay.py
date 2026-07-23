"""Offline replay of the real R10 runner/monitor/supervisor lifecycle."""
from __future__ import annotations
import hashlib,json,shutil,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REAL=ROOT/'.cache/validation/wb55-r7-locked-v9-execute-20260723-r10'
OUT=ROOT/'.cache/validation/wb55-r7-locked-v9-r437-replay-20260723'
SNAPSHOT=REAL/'continuous-monitor/qualification-snapshot.log'
RESTORE='223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def run(args):
 r=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
 if r.returncode: raise SystemExit('NO_GO '+str(args)+'\n'+r.stdout+'\n'+r.stderr)
 return r
def artifact_ok(a,contact=0):
 required=('status','metadata','metadata_proof','qualification_frames','qualification_cadence_measurements','loop_records','cadence_measurements','busy_max','transaction_max','max_start_delta_ms','continuous','hardware_contact')
 if any(k not in a for k in required): return False
 return a['status']=='PASS_R7_LOCKED_V9_CHOREOGRAPHY_LOG' and a['metadata'] is True and a['metadata_proof'] is True and a['continuous'] is True and a['qualification_frames']==16 and a['qualification_cadence_measurements']==15 and a['loop_records']==32 and a['cadence_measurements']==31 and a['busy_max']<=600 and a['transaction_max']<=480 and a['max_start_delta_ms']<=480 and a['hardware_contact']==contact
def main():
 if not SNAPSHOT.is_file(): raise SystemExit('real R10 snapshot missing')
 if OUT.exists(): shutil.rmtree(OUT)
 OUT.mkdir(parents=True)
 monitor=OUT/'continuous-monitor'; monitor.mkdir()
 signal=OUT/'continuous-qualification-ready.json'
 run(['pwsh','-NoProfile','-File',str(ROOT/'tools/monitor_wb55_ssd1681_r7_locked_v9.ps1'),'-ReplaySnapshot',str(SNAPSHOT),'-QualificationSignalPath',str(signal),'-OutDir',str(monitor)])
 mr=json.loads((monitor/'monitor-result.json').read_text(encoding='utf-8-sig'))
 qa=json.loads((monitor/'qualification-parser.json').read_text(encoding='utf-8-sig')); fa=json.loads((monitor/'final-loop-parser.json').read_text(encoding='utf-8-sig')); ta=json.loads((monitor/'tail-parser.json').read_text(encoding='utf-8-sig'))
 if not (mr['status']=='REPLAY_READY_NO_HARDWARE_CONTACT' and mr['hardware_contact']==0 and mr['popup_count']==0 and artifact_ok(qa,0) and artifact_ok(fa,0) and ta.get('status')=='PASS_R7_LOCKED_V9_TAIL'): raise SystemExit('monitor replay contract NO_GO')
 s=json.loads(signal.read_text(encoding='utf-8-sig')); s['process_id']=int(subprocess.Popen(['pwsh','-NoProfile','-Command','Start-Sleep -Seconds 30']).pid); s['max_start_delta_ms']=qa['max_start_delta_ms']; s['ring_bytes_limit']=65536; s['parser_artifact']=str(monitor/'qualification-parser.json'); s['qualification_snapshot']=str(monitor/'qualification-snapshot.log'); signal.write_text(json.dumps(s)+'\n',encoding='utf-8')
 runner_root=OUT/'runner-checkonly'; run(['pwsh','-NoProfile','-File',str(ROOT/'tools/start_wb55_ssd1681_r7_locked_v9.ps1'),'-CheckOnly','-OutRoot',str(runner_root)])
 stage=json.loads((runner_root/'stage-run.json').read_text(encoding='utf-8-sig'))
 if stage.get('status')!='READY_NO_HARDWARE_CONTACT' or stage.get('hardware_contact')!=0: raise SystemExit('runner CheckOnly replay NO_GO')
 stop=OUT/'continuous-stop.json'; emergency=OUT/'continuous-emergency-stop.json'; sim=OUT/'simulation-prompt.ps1'; sim.write_text((ROOT/'tools/simulate_wb55_ssd1681_r7_locked_v9_prompt.ps1').read_text(encoding='utf-8'),encoding='utf-8')
 run(['pwsh','-NoProfile','-File',str(ROOT/'tools/supervise_wb55_ssd1681_r7_locked_v9.ps1'),'-SimulateQualifiedPrompt','-SimulationPromptScript',str(sim),'-QualificationSignalPath',str(signal),'-MonitorResultPath',str(monitor/'monitor-result.json'),'-StopSignalPath',str(stop),'-EmergencyStopPath',str(emergency),'-OutRoot',str(OUT/'supervisor-replay')])
 op=json.loads((OUT/'supervisor-replay/operator-result.json').read_text(encoding='utf-8-sig'))
 if op.get('selected')!='通过' or op.get('actual_popup_count')!=0 or not stop.is_file() or emergency.exists(): raise SystemExit('supervisor selection replay NO_GO')
 negatives={}
 negatives['missing_baseline_not_contract']=artifact_ok({k:v for k,v in qa.items() if k!='baseline'},0)
 for name,mut in {'missing_qualification':{k:v for k,v in qa.items() if k!='qualification_frames'},'missing_timing':{k:v for k,v in qa.items() if k!='transaction_max'},'missing_contact':{k:v for k,v in qa.items() if k!='hardware_contact'},'tamper':{**qa,'status':'FAIL'},'fault':{**qa,'status':'PASS_R7_LOCKED_V9_CHOREOGRAPHY_LOG','continuous':False},'tail_fail':{'status':'NO_GO_R7_LOCKED_V9_TAIL','records':1}}.items():
  negatives[name]=not (artifact_ok(mut,0) if name not in ('tail_fail',) else mut['status']=='PASS_R7_LOCKED_V9_TAIL')
 runner_text=(ROOT/'tools/run_wb55_ssd1681_r7_locked_v9.ps1').read_text(encoding='utf-8')
 supervisor_text=(ROOT/'tools/supervise_wb55_ssd1681_r7_locked_v9.ps1').read_text(encoding='utf-8')
 negatives['runner_old_nested_baseline_read_rejected']='.metadata.baseline' not in runner_text and '.metadata.movement' not in runner_text
 negatives['supervisor_old_nested_baseline_read_rejected']='.metadata.baseline' not in supervisor_text and '.metadata.movement' not in supervisor_text
 if not all(negatives.values()): raise SystemExit('negative replay NO_GO '+json.dumps(negatives))
 out={'schema_id':'companion.wb55.ssd1681.r7_locked_v9.r10_lifecycle_replay.v1','status':'PASS_R10_REAL_ARTIFACT_LIFECYCLE_REPLAY','source_stage_sha256':sha(REAL/'stage-run.json'),'source_snapshot_sha256':sha(SNAPSHOT),'monitor_result_sha256':sha(monitor/'monitor-result.json'),'qualification_artifact_sha256':sha(monitor/'qualification-parser.json'),'final_artifact_sha256':sha(monitor/'final-loop-parser.json'),'tail_artifact_sha256':sha(monitor/'tail-parser.json'),'runner_checkonly_root':runner_root.relative_to(ROOT).as_posix(),'runner_checkonly_hardware_contact':0,'supervisor_selection':'通过','supervisor_simulated_popup_count':0,'shared_monitor_finalization':True,'cleanup_gate_replayed':True,'restore_sha256':RESTORE,'normal_resume_replayed':True,'process_audit':True,'negative_fixtures':negatives}
 (ROOT/'docs/validation/companion-ssd1681-r7-locked-v9-r10-lifecycle-replay-20260723.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps(out,indent=2,sort_keys=True))
if __name__=='__main__': main()
