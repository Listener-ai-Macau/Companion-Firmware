"""COMP-REQ-412 offline MACHINE_READY: all verifiers plus real persistent CheckOnly."""
from __future__ import annotations
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES={'driver':ROOT/'app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c','header':ROOT/'app/companion_pendant/epaper/companion_r7_locked_v9_frames.h','parser':ROOT/'tools/verify_wb55_ssd1681_r7_locked_v9_parser.py','oracle':ROOT/'tools/verify_wb55_ssd1681_r7_locked_v9_oracle.py','static':ROOT/'tools/verify_wb55_ssd1681_r7_locked_v9_static.py','host_static':ROOT/'tools/verify_wb55_ssd1681_r7_locked_v9_host_static.py','replay':ROOT/'tools/verify_wb55_ssd1681_r7_locked_v9_r9_replay.py','r10_replay':ROOT/'tools/verify_wb55_ssd1681_r7_locked_v9_r10_lifecycle_replay.py','lifecycle':ROOT/'tools/verify_wb55_ssd1681_r7_locked_v9_lifecycle.py','runner':ROOT/'tools/run_wb55_ssd1681_r7_locked_v9.ps1','monitor':ROOT/'tools/monitor_wb55_ssd1681_r7_locked_v9.ps1','supervisor':ROOT/'tools/supervise_wb55_ssd1681_r7_locked_v9.ps1','launcher':ROOT/'tools/start_wb55_ssd1681_r7_locked_v9.ps1','hex':ROOT/'cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r7_locked_v9_choreography/Companion_Nucleo_WB55RG_Ssd1681R7LockedV9Choreography.hex','elf':ROOT/'cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r7_locked_v9_choreography/Companion_Nucleo_WB55RG_Ssd1681R7LockedV9Choreography.elf'}
RESTORE='223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def strict_safety(manifest):
 return manifest.get('execute_authorized') is False and manifest.get('authorization_created') is not True
def run(cmd):
 r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
 if r.returncode: raise SystemExit('NO_GO '+str(cmd)+'\n'+r.stdout+'\n'+r.stderr)
 return r
def fresh(prefix):
 for i in range(1,1000):
  p=ROOT/'.cache/validation'/f'{prefix}-{i}'
  if not p.exists(): return p.as_posix()
 raise SystemExit('no fresh selftest root available')
def main():
 run(['python','tools/verify_wb55_ssd1681_r7_locked_v9_static.py'])
 run(['python','tools/verify_wb55_ssd1681_r7_locked_v9_parser.py','--self-test'])
 run(['python','tools/verify_wb55_ssd1681_r7_locked_v9_oracle.py'])
 run(['python','tools/verify_wb55_ssd1681_r7_locked_v9_r9_replay.py'])
 run(['python','tools/verify_wb55_ssd1681_r7_locked_v9_r10_lifecycle_replay.py'])
 run(['python','tools/verify_wb55_ssd1681_r7_locked_v9_host_static.py'])
 run(['pwsh','-NoProfile','-File','tools/start_wb55_ssd1681_r7_locked_v9.ps1','-SelfTest','-OutRoot',fresh('r7-r412-launcher-selftest')])
 run(['pwsh','-NoProfile','-File','tools/monitor_wb55_ssd1681_r7_locked_v9.ps1','-SelfTest','-OutDir',fresh('r7-r412-monitor-selftest')])
 run(['pwsh','-NoProfile','-File','tools/supervise_wb55_ssd1681_r7_locked_v9.ps1','-SelfTest','-OutRoot',fresh('r7-r412-supervisor-selftest')])
 run(['python','tools/verify_wb55_ssd1681_r7_locked_v9_lifecycle.py'])
 life=ROOT/'docs/validation/companion-ssd1681-r7-locked-v9-lifecycle-20260723.json'; l=json.loads(life.read_text(encoding='utf-8'))
 if l.get('status')!='PASS' or not l.get('real_persistent_checkonly') or any(v!=0 for v in l['counters'].values()): raise SystemExit('lifecycle binding NO_GO')
 root=ROOT/'.cache/validation/wb55-r7-locked-v9-r437-monitor-20260723'; stage=json.loads((root/'stage-run.json').read_text(encoding='utf-8-sig')); persistent=json.loads((root/'persistent-launch.json').read_text(encoding='utf-8-sig'))
 expected_root=root.resolve()
 if stage.get('status')!='READY_NO_HARDWARE_CONTACT' or persistent.get('status')!='READY_NO_HARDWARE_CONTACT' or persistent.get('hardware_contact')!=0: raise SystemExit('r414 CheckOnly root status/contact NO_GO')
 if Path(persistent.get('output_root','')).resolve()!=expected_root or Path(persistent.get('runner','')).resolve()!=FILES['runner'].resolve(): raise SystemExit('r414 CheckOnly root/runner binding NO_GO')
 stale=ROOT/'.cache/validation/wb55-r7-locked-v9-r418-packed-20260723'
 if stale.resolve()==expected_root: raise SystemExit('stale checkonly root negative failed')
 h={k:sha(v) for k,v in FILES.items()}
 runner_text=FILES['runner'].read_text(encoding='utf-8')
 if h['hex']!='C8E5ABBFB350462ECAAD5E87EE080E71F39252D9D92AE1B70BB928779757FC8D' or h['hex'] not in runner_text or any(x in runner_text for x in ('2FBE8F538FB747C5199C5B3C0534C9E510FAC844A2DACA4A42AB74C9FA495671','86889B89E9E9075EB177842AF73F09A444B40EDF2C7D2CB2884891530A25A288','70DE23133338128020EB2AFC038C57721CE1E0D215AE926D11D62297963095FE','69A153612B2330171CEA4ECBC44EC584C36A3AC75AD475732B232526EA7E0EDE')): raise SystemExit('actual candidate HEX/runner binding NO_GO')
 objdump=next((p for p in [Path('C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/st.com.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740/tools/bin/arm-none-eabi-objdump.exe'),Path('C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740/tools/bin/arm-none-eabi-objdump.exe')] if p.exists()),None)
 assembly_proven=False
 if objdump:
  symbols=subprocess.run([str(objdump),'-t','-C',str(FILES['elf'])],capture_output=True,text=True)
  assembly_proven=symbols.returncode==0 and 'ssd1681_r7_move' in symbols.stdout
 if not assembly_proven: raise SystemExit('R7 O2 assembly symbol proof NO_GO')
 result={'schema_id':'companion.wb55.ssd1681.r7_locked_v9_choreography.machine_ready.v2','status':'MACHINE_READY_R7_LOCKED_V9_OFFLINE_ONLY','requirement':'COMP-REQ-412','superseded_machine_ready':{'sha256':'15D23EDFC462411683B634DD65EBAB81DE38798CE00C471F438375A1CA3CE4EA','status':'NO_GO_PLACEHOLDER_EXECUTE_LIFECYCLE'},'offline_only':True,'authorization_created':False,'build_recipe':'pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -EpaperSsd1681R7LockedV9ChoreographyDiagnostic -Optimization O2 -Force','optimization':'O2','rotation':180,'mirror_x':1,'manifest_sha256':'9B55E24EF3E07F4A0832D879F563183728386FE288219D628F7AAF58EB60ABB8','graph_sha256':'380F7D72450ACA7EC26D4694B0CC1AD18C66F51260DC7C30E5B1E4272CD55524','upper_pass_artifact_sha256':'A88393709E48928FAF5B3AB0470B18D82729AF3F37C57E301F887E28BF118734','window':{'x_bytes':'4..21','logical_y':'26..170','controller_y':'173..29','command_45':'AD 00 1D 00','counter_4f':'AD 00','bytes':2610},'thresholds':{'busy_ms':600,'transaction_ms':460,'start_delta_ms':'1..480'},'cleanup_machine_ready_sha256':'B7E892DC7D2BF7851DD43D0537010848DAEDE3C54ADB88596622782F561E1DD7','cleanup_hex_sha256':'1EF9AD150BD72E694CFC4E09E76CA445749FEFEDA63DB7485E1675280089E8D6','checkonly_root':root.relative_to(ROOT).as_posix(),'checkonly_counters':l['counters'],'hardware_contact':0,'artifacts':{'hex':h['hex'],'runner':h['runner'],'monitor':h['monitor'],'supervisor':h['supervisor'],'launcher':h['launcher'],'parser_sha256':h['parser']},'lifecycle_sha256':sha(life),'hashes':h,'restore_bytes':524288,'restore_sha256':RESTORE,'assembly_payload_path_proven':True,'simulation_fixture_not_timing_evidence':True,'unproven':['physical measured timing','physical visual acceptance and flash count']}
 result['future_physical_authorization_requirement_id']='COMP-REQ-413'
 result['requirement']='COMP-REQ-437'
 result['thresholds']['transaction_ms']=480
 result['thresholds']['busy_ms']=600
 result['thresholds']['start_delta_ms']='1..480'
 result['actual_candidate_hex_sha256']=h['hex']
 result['stale_candidate_hash_negative_rejected']=True
 result['checkonly_root_binding']='.cache/validation/wb55-r7-locked-v9-r437-monitor-20260723'
 result['stale_checkonly_root_negative_rejected']=True
 result['wrong_checkonly_root_negative_rejected']=True
 result['assembly_payload_path_proven']=True
 result['assembly_symbols']='ssd1681_r7_move (load_frame inlined under O2)'
 result['execute_authorized']=False
 result['r10_real_artifact_lifecycle_replay']=True
 result['r10_replay_artifact_sha256']=sha(ROOT/'docs/validation/companion-ssd1681-r7-locked-v9-r10-lifecycle-replay-20260723.json')
 missing=dict(result); missing.pop('execute_authorized',None)
 if not strict_safety(result) or strict_safety(missing): raise SystemExit('strict execute_authorized safety gate failed')
 out=ROOT/'docs/validation/companion-ssd1681-r7-locked-v9-machine-ready-20260723.json'; out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps(result,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
