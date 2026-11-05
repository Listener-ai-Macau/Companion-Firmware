"""Run a source-bound Type minimal full-file OTA with continuous passive UART and shared lease.

No SWD, host reset, audio output, cloud call, or forced reconnection.
Optional short real capture follows successful OTA only, to check the shared
recording workspace was released; it never contributes OTA speed evidence.
The expected device reboot/reconnect belongs to the signed OTA product flow.
The historical filename is retained; old paired packages are not accepted.
"""
from pathlib import Path
from datetime import datetime
import argparse,json,os,sys,tempfile,threading,time,subprocess,hashlib,re,traceback,runpy
import serial
from serial.tools import list_ports
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Companion-Firmware/tools'))
from diagnose_wba_uart import parse_frames
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--bundle',type=Path,required=True)
p.add_argument('--operation-owner-label',default='Companion 录音/OTA',help='Shared-record caller identity only; no device behavior change')
p.add_argument('--operation-owner-thread',default='01a105e0-7fe5-7cc0-b712-46de75337261')
p.add_argument('--single-query-admission',action='store_true',help='Accept only the initial query reply within the existing bound; boot snapshots never trigger another admission query')
p.add_argument('--native-start-delay-ms',type=int,default=0,help='Engineering-only0..5000ms phase offset before native CLI; legacy711 UART-periodic collision delivery, no timeout/radio/retry change')
execution=p.add_mutually_exclusive_group(required=True)
execution.add_argument('--installed-receipt',type=Path,help='Receipt for the actual installed Type')
execution.add_argument('--type-candidate',type=Path,help='Explicit diagnostic build-state receipt; candidate remains NOT installed and must match immutable source and both native artifacts')
p.add_argument('--expected-before',required=True);p.add_argument('--output',type=Path,required=True)
p.add_argument('--required-uid',required=True,help='Exact current MCU UID, never the historical board fallback')
p.add_argument('--device-id',required=True,help='Explicit current target BLE MAC')
p.add_argument('--expected-ui-before',type=int,help='Optional exact pre-upgrade resource generation')
p.add_argument('--transport-profile',choices=('automatic','acknowledged','windowed_244','windowed_244_peer_handoff','windowed_215_peer_handoff','windowed_491_peer_handoff','windowed_466_peer_handoff','windowed_215_hold','continuous_215_peer_handoff','continuous_240_peer_handoff','continuous_491_peer_handoff'),default='automatic')
p.add_argument('--open-pair-window',action='store_true',help='Use the existing guarded physical UART PAIR window after an observed bond-loss failure; never clears bonds')
p.add_argument('--trace-submit-prefix',action='store_true',help='Diagnostic candidate only: persist bounded completed submit metadata in stderr batches; no transport/radio control')
p.add_argument('--rf-admission-receipt',type=Path,help='Explicit diagnostic-only current-connection RF gate; native Type waits before BEGIN/ABORT/DATA/FINISH. Normal OTA needs no sniffer.')
p.add_argument('--rf-admission-nonce',help='32 lowercase hex digits bound to the diagnostic receiver proof; required with --rf-admission-receipt')
p.add_argument('--max-seconds',type=int,default=420,help='Diagnostic run bound only; does not change frozen product time/speed targets')
p.add_argument('--interrupt-at-bytes',type=int,default=0,help='Stop only our first CLI after actual nonzero accepted progress, then send the same full file afresh; no SWD or reset')
p.add_argument('--observe-disconnect-after-interruption',action='store_true',help='Require one fresh normal UART reply showing the old App still running with BLE disconnected before the second request; closing a process alone is not physical-link evidence')
p.add_argument('--expected-post-boot-route',type=int,choices=(1,2,3),help='Require BOOT4 in the same fresh post-update query observation; route3 has only its documented erased-entry scope')
p.add_argument('--post-update-recording-seconds',type=int,default=0,help='After confirmed new App and released OTA space, exercise only actual capture/stop/local receive through the installed Type; no ASR or minutes')
p.add_argument('--post-update-isolated-library',action='store_true',help='Diagnostic-only alternate local library; default follows the normal product library')
p.add_argument('--post-update-upload-sample',type=Path,help='After confirmed signed update, keep the same board lease for protected GATT inspection and one original sealed-file receive; no recording or consumption')
a=p.parse_args()
if not 0<=a.native_start_delay_ms<=5000:p.error('--native-start-delay-ms must be0..5000; no device access')
if any(c in a.operation_owner_label+a.operation_owner_thread for c in '\r\n'):p.error('Operation owner identity must be one line')
if bool(a.rf_admission_receipt)!=bool(a.rf_admission_nonce):p.error('RF admission requires both --rf-admission-receipt and --rf-admission-nonce; no board access')
if a.rf_admission_receipt:
 if not a.rf_admission_receipt.is_absolute() or not re.fullmatch(r'[0-9a-f]{32}',a.rf_admission_nonce):p.error('RF admission requires an absolute receipt path and32lowercase hex nonce; no board access')
 if a.rf_admission_receipt.exists():p.error('RF admission receipt already exists; use a fresh per-connection path; no board access')
 if a.interrupt_at_bytes:p.error('RF-gated diagnosis requires one native connection; interruption/retry needs a separate fresh gate; no board access')
if a.post_update_upload_sample and a.post_update_recording_seconds:p.error('Choose existing-file recovery or new recording, not both')
if a.post_update_upload_sample:
 sample=json.loads(a.post_update_upload_sample.read_bytes());assert sample.get('synthetic') is True and sample.get('bytes')==2097152 and len(sample.get('sha256',''))==64,'Post-update qualification uses the existing sealed synthetic2MiB fixture'
if a.trace_submit_prefix and not a.type_candidate:p.error('--trace-submit-prefix requires an explicit uninstalled diagnostic candidate')
if not re.fullmatch(r'[0-9a-fA-F]{24}',a.required_uid):p.error('--required-uid must be24hex digits')
address=a.device_id.replace(':','').replace('-','')
if not re.fullmatch(r'[0-9a-fA-F]{12}',address) or address.lower() in ('0'*12,'f'*12):p.error('--device-id must be an explicit non-wildcard BLE MAC')
a.required_uid=a.required_uid.lower();a.device_id=':'.join(address[i:i+2].upper() for i in range(0,12,2))
type_execution={'mode':'installed','installedTypeSha256':None,'candidateTypeSha256':None}
if a.type_candidate:
 candidate=json.loads(a.type_candidate.read_bytes())
 assert candidate.get('installed') is False and candidate.get('buildExitCode')==0,'Candidate is not a completed uninstalled build'
 assert candidate.get('diagnosticOnly') is True and candidate.get('defaultChanged') is False,'Use only the explicit diagnostic candidate'
 verify_source=runpy.run_path(str(ROOT/'Companion-Type/tools/verify_type_source_checkpoint.py'))['verify']
 candidate_source=Path(candidate.get('sourceRoot',str(ROOT/'Companion-Type'))).resolve()
 proof=verify_source(candidate_source,candidate,candidate['sourceCommit'])
 folder=Path(candidate['artifact']['path']).parent;exe=folder/'companion-type.exe';dll=folder/'companion_type_lib.dll'
 assert hashlib.sha256(exe.read_bytes()).hexdigest()==candidate['exeSha256'],'Candidate EXE differs from build receipt'
 assert hashlib.sha256(dll.read_bytes()).hexdigest()==candidate['dllSha256'],'Candidate DLL differs from build receipt'
 if a.trace_submit_prefix:assert b'companion.ota.submit-prefix.v1' in exe.read_bytes(),'Candidate does not implement the requested diagnostic prefix; no board access'
 type_execution.update(mode='candidate_not_installed',candidateTypeSha256=candidate['exeSha256'],candidateDllSha256=candidate['dllSha256'],sourceVerification=proof,candidateReceiptSha256=hashlib.sha256(a.type_candidate.read_bytes()).hexdigest())
else:
 installed=json.loads(a.installed_receipt.read_bytes());exe=Path(installed['installed_exe'])
 assert hashlib.sha256(exe.read_bytes()).hexdigest()==installed['installed_exe_sha256']
 type_execution['installedTypeSha256']=installed['installed_exe_sha256']
 dll=exe.with_name('companion_type_lib.dll')
 assert hashlib.sha256(dll.read_bytes()).hexdigest()==installed['installed_dll_sha256'],'Installed DLL differs from receipt; no board access'
sys.path.insert(0,str(ROOT/'tools'))
from engineering_ota_safety import require_preserve_capability,enable_preservation
expected_exe_sha=(candidate['exeSha256'] if a.type_candidate else installed['installed_exe_sha256'])
type_execution['preserveExecutableSha256']=require_preserve_capability(exe,expected_exe_sha)
if a.rf_admission_receipt:
 native=exe.read_bytes()
 assert b'rf_admission_wait nonce=' in native and b'current_connect_and_independent_mic=1' in native,'Requested RF gate is absent from this native Type; no board access'
envelope=json.loads(a.bundle.read_bytes());assert envelope['schema']=='companion.wba.simple-ota.v3';version=f"{envelope['firmware_version']:08x}";generation=envelope['resource_version']
out=a.output.resolve();out.mkdir(exist_ok=False);board=ROOT/'docs/board_operations.md'
sys.path.insert(0,str(ROOT/'tools'))
from select_companion_transport_endpoint import require_endpoint,register_stage
endpoint_selection=require_endpoint('windows',out/'endpoint-selection.json')
line='- **占用中**：'+a.operation_owner_label+'（'+a.operation_owner_thread+'，'+datetime.now().astimezone().isoformat(timespec='seconds')+'，最简单文件无线OTA）。绑定Type候选正常加密连接，一份完整固件+资源文件→Boot验证/安装→正常WSI3版本/临时空间释放；全程被动UART（起止各正常查询），无SWD/停核/主机复位/开录/外放/云。实际新字节/墙钟独立保留，不调速或继承录音成绩。'
if a.post_update_upload_sample:
 line+=' 同一占用续作升级后受保护服务/系统CCCD检查和原封口2MiB收取；各步间被动确认真实断开，不新增录音或消费。'
if a.post_update_recording_seconds:
 line=line.replace('无SWD/停核/主机复位/开录/外放/云','升级确认后仅一次短实录/停录/本地收取验证共享区释放，无SWD/停核/主机复位/外放/云')
from shared_board_owner_guard import SharedBoardOwnerGuard,active_owner_lines
import board_turn
turn_item=a.operation_owner_label+'：FW'+str(envelope['firmware_version'])+' 正常无线OTA'
def owners(raw):return active_owner_lines(raw.decode('utf-8-sig'))
def replace(before,after):
 raw=board.read_bytes();old=before.encode();assert raw.count(old)==1
 fd,tmp=tempfile.mkstemp(dir=board.parent,prefix=board.name+'.')
 try:
  with os.fdopen(fd,'wb') as f:f.write(raw.replace(old,after.encode(),1));f.flush();os.fsync(f.fileno())
  assert board.read_bytes()==raw,'Shared board changed'
  os.replace(tmp,board)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
owner_guard=SharedBoardOwnerGuard(board,line)
def guard():owner_guard.check()
stop=threading.Event();opened=threading.Event();query=threading.Event();queried=threading.Event();query_offsets=[];pair=threading.Event();pair_sent=threading.Event();errors=[];thread=child=None;held=False
state=dict(result='NOT_STARTED',operationOwnerLabel=a.operation_owner_label,operationOwnerThread=a.operation_owner_thread,singleQueryAdmission=a.single_query_admission,startedAtLocal=datetime.now().astimezone().isoformat(timespec='seconds'),bundleId=envelope['sha256'],bundlePath=str(a.bundle.resolve()),expectedFirmware=version,expectedUi=generation,typeExecutionMode=type_execution['mode'],installedTypeSha256=type_execution['installedTypeSha256'],typeExecution=type_execution,requiredUid=a.required_uid,deviceId=a.device_id,transportProfile=a.transport_profile,traceSubmitPrefixRequested=a.trace_submit_prefix,rfAdmissionRequested=bool(a.rf_admission_receipt),rfAdmissionReceipt=str(a.rf_admission_receipt) if a.rf_admission_receipt else None,rfAdmissionNonce=a.rf_admission_nonce,toolSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),swd=False,hostReset=False,captureCommands=0,cloudCalls=0,wirelessOtaCompleted=False,ownedHandlesClosed=False)
def save():(out/'result.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def listen():
 try:
  ports=[p.device for p in list_ports.comports() if p.serial_number=='004400403532510B31333430']
  state['fixedV3UartMatchCount']=len(ports)
  if len(ports)!=1:raise RuntimeError(f'Fixed STLINK-V3 UART mapping requires one match, found{len(ports)}; no serial or BLE operation started')
  port=serial.Serial(port=None,baudrate=115200,timeout=.1);port.dtr=port.rts=False;port.port=ports[0]
  with port,(out/'uart.log').open('wb') as log,(out/'uart-read-timeline.jsonl').open('w',encoding='utf-8') as timing:
   port.write(b'?');port.flush();opened.set()
   last_received=time.monotonic()
   while not stop.is_set():
    if pair.is_set() and not pair_sent.is_set() and time.monotonic()-last_received>=.150:
     # The target polls RX and emits its diagnostic snapshot synchronously.
     # Do not burst a line into that output/ORE window. A leading newline
     # clears a previously invalid partial command; no permission is changed
     # until the exact normal PAIR command receives its actual OPEN reply.
     guard()
     for byte in b'\nPAIR\n':
      port.write(bytes([byte]));port.flush();time.sleep(.020)
     pair_sent.set()
    if query.is_set() and not queried.is_set() and time.monotonic()-last_received>=.150:
     query_offsets.append(log.tell());port.write(b'?');port.flush();queried.set()
    read_started_ns=time.monotonic_ns();read_started_unix_us=time.time_ns()//1000
    value=port.read(min(max(port.in_waiting,1),4096))
    read_finished_ns=time.monotonic_ns();read_finished_unix_us=time.time_ns()//1000
    if value:
     timing.write(json.dumps(dict(offset=log.tell(),bytes=len(value),readStartUnixUs=read_started_unix_us,readEndUnixUs=read_finished_unix_us,readStartMonotonicNs=read_started_ns,readEndMonotonicNs=read_finished_ns),separators=(',',':'))+'\n');timing.flush()
     log.write(value);log.flush();last_received=time.monotonic()
 except BaseException as e:
  errors.append(repr(e));state['uartSetupTraceback']=traceback.format_exc();opened.set()

def current_query_snapshot(expected_boot_route=None,timeout=12):
 # Reboot/power loss can truncate a startup frame. Parse only the bytes after
 # THIS query was sent; a complete pre-upgrade frame is never a current reply.
 query.clear();queried.clear();query.set()
 assert queried.wait(4),'UART did not send the current query after a quiet interval'
 start=query_offsets[-1];deadline=time.monotonic()+timeout;fresh_seen_at=None
 while time.monotonic()<deadline:
  guard();assert not errors,errors
  raw=(out/'uart.log').read_bytes()[start:]
  frames,bad=parse_frames(raw)
  fresh=[f for f in frames if f['reason']=='query']
  # BOOT4 follows its DIAG1 END. Do not associate an earlier periodic or
  # truncated frame's route with the fresh query whose END just arrived.
  tail=b''
  if fresh:
   marker=b'DIAG1 END seq='+str(fresh[-1]['seq']).encode()
   at=raw.rfind(marker);end=raw.find(b'\n',at)
   if at>=0 and end>=0:tail=raw[end+1:]
  routes=re.findall(rb'(?m)^BOOT4 schema=1 route=([0-3])\r?$',tail)
  if fresh and fresh_seen_at is None:fresh_seen_at=time.monotonic()
  # DIAG1 END precedes cached RXTRACE/BLE/XFER diagnostics. Keep the same
  # passive reader until its terminal line or a bounded2s detail tail, without
  # sending another query or extending the absolute timeout. Missing details
  # remain partial, not a fabricated normal-App failure.
  details_complete=bool(re.search(rb'(?m)^XFER3 [^\r\n]+\r?$',tail))
  details_done=details_complete or (fresh_seen_at is not None and time.monotonic()-fresh_seen_at>=2.0)
  if fresh and (expected_boot_route is None or routes) and details_done:
   state.setdefault('queryTailObservations',[]).append(dict(startOffset=start,detailsComplete=details_complete,detailTailBoundSeconds=2.0,extraQueryCommands=0))
   frame=fresh[-1]
   if routes:frame['bootRoute']=int(routes[-1])
   if expected_boot_route is not None:
    assert frame.get('bootRoute')==expected_boot_route,('Unexpected fresh Boot route',frame.get('bootRoute'),expected_boot_route)
   return frame,bad
  time.sleep(.1)
 raise RuntimeError('No complete fresh query reply; boot/periodic/previous snapshots were not reused')
def transfer_detail_tail_complete(raw,sequence):
 # DIAG1 END only ends the core snapshot. Cached XFER details follow it.
 # A later snapshot's terminal line must not complete an earlier partial tail.
 marker=b'DIAG1 END seq='+str(sequence).encode()+b'\r\n'
 at=raw.rfind(marker)
 if at<0:return False
 tail=raw[at+len(marker):].split(b'DIAG1 BEGIN ',1)[0]
 return bool(re.search(rb'(?m)^XFER3 [^\r\n]+\r?$',tail))

def passive_post_update_idle(name,initial=None):
 # A closed native process is not an actual BLE disconnect. Current Capture
 # builds disable periodic UART; after the native job has ended, one normal
 # query supplies the missing observation without another BLE operation.
 assert child is None or child.poll() is not None,'Native operation still active; no idle query'
 first=(out/'uart.log').stat().st_size;deadline=time.monotonic()+5
 queried_idle=False
 frame=initial
 while True:
  guard();assert not errors,errors
  if frame:
   sections=frame['sections']
   if sections['ID']['uid']==a.required_uid and sections['ID']['fw']==version and not sections['BLE']['linked'] and sections['BLE']['connection']=='ffff':
    assert not sections['AUDIO']['mic_run'] and not sections['CORE']['stack_low'] and not sections['CORE']['stack_guard']
    # Retain the existing physical-idle decision, then let its already-started
    # diagnostics finish passively. Previously the last UART reader could close
    # at DIAG1 END and lose exactly the post-upload gate/profile evidence.
    # No query, BLE call or deadline extension; partial details stay explicit.
    tail_deadline=min(deadline,time.monotonic()+2.0)
    while True:
     guard();assert not errors,errors
     complete=transfer_detail_tail_complete((out/'uart.log').read_bytes(),frame['seq'])
     if complete or time.monotonic()>=tail_deadline:break
     time.sleep(.025)
    state[name+'DiagnosticTail']=dict(sequence=frame['seq'],detailsComplete=complete,detailTailBoundSeconds=2.0,extraQueryCommands=0)
    state[name]=frame;save();return frame
  if time.monotonic()>=deadline:
   if queried_idle:raise RuntimeError('Fresh post-operation query did not confirm physical idle for '+name+'; no reset or retry')
   frame,rejected=current_query_snapshot()
   state[name+'QueryObservation']=dict(periodicUartMayBeDisabled=True,afterNativeProcessExit=True,
       queryCommands=1,rejectedFrames=rejected)
   queried_idle=True;deadline=time.monotonic()+2;save();continue
  frames,_=parse_frames((out/'uart.log').read_bytes()[first:]);frame=frames[-1] if frames else None;time.sleep(.1)

def post_update_existing_file_recovery():
 global child
 passive_post_update_idle('postOtaPhysicalIdle',state['afterSnapshot'])
 post_env=dict(env,COMPANION_TYPE_STATE_PATH=str(out/'post-recovery-state.json'),COMPANION_TYPE_DELETE_AFTER_SYNC='0')
 inspection=[str(exe),'--system-ota-inspect','--device-id',a.device_id]
 upload=[str(exe),'--benchmark-recording-upload','--device-id',a.device_id,'--benchmark-sample',str(a.post_update_upload_sample.resolve()),'--benchmark-output',str(out/'post-update-receive')]
 for name,cmd,bound in [('protected',inspection,35),('upload',upload,180)]:
  guard();state[name+'RecoveryStartedAt']=datetime.now().astimezone().isoformat(timespec='seconds');save()
  log_path=out/('post-update-'+name+'.log')
  with log_path.open('wb') as log:
   child=subprocess.Popen(cmd,cwd=ROOT/'Companion-Type',stdout=log,stderr=subprocess.STDOUT,env=post_env,creationflags=subprocess.CREATE_NO_WINDOW)
   state['nativeChildPid']=child.pid;save();deadline=time.monotonic()+bound
   while child.poll() is None:
    guard();assert not errors,errors
    if time.monotonic()>=deadline:raise RuntimeError('Post-update '+name+' exceeded bound; stop without retry')
    time.sleep(.1)
  state[name+'RecoveryExitCode']=child.returncode
  assert child.returncode==0,'Post-update '+name+' failed; signed update completion remains a separate fact'
  if name=='protected':
   rows=[json.loads(line.split('system_ota_inspect_json=',1)[1]) for line in log_path.read_text(encoding='utf-8-sig',errors='replace').splitlines() if line.startswith('system_ota_inspect_json=')]
   assert len(rows)==1 and rows[0].get('result')=='OTA_PROTECTED_READ_ONLY_INSPECTION_COMPLETE','Protected current service inspection incomplete'
   state['postUpdateProtectedInspection']=rows[0]
  else:
   measured=json.loads((out/'post-update-receive/benchmark-result.json').read_bytes());data=Path(measured['rawPath']).read_bytes()
   assert len(data)==sample['bytes'] and hashlib.sha256(data).hexdigest()==sample['sha256'] and measured['cachedBytes']==0 and measured['consumeCommands']==0,'Original post-update file integrity/new byte contract failed'
   state['postUpdateOriginalFileReceive']=measured
  save();passive_post_update_idle('post'+name.title()+'PhysicalIdle')
 state['postUpdateOriginalFileRecoveryQualified']=True;save()

try:
 with board_turn.turn_lock():
  turn=board_turn.claim('codex',turn_item,False)
  assert turn['result']=='TURN_CLAIMED',turn
  line=board_turn.load_state()['leaseLine']
 held=True;owner_guard=SharedBoardOwnerGuard(board,line);guard();save()
 register_stage(out/'result.json','windows')
 thread=threading.Thread(target=listen);thread.start()
 if not opened.wait(5):raise RuntimeError('UART setup did not finish within5seconds; no BLE started')
 if errors:raise RuntimeError('UART setup failed before BLE: '+errors[0])
 end=time.monotonic()+12;before=None
 while time.monotonic()<end:
  frames,bad=parse_frames((out/'uart.log').read_bytes())
  eligible=[f for f in frames if f['reason']=='query'] if a.single_query_admission else frames
  if eligible:before=eligible[-1];break
  time.sleep(.1)
 assert before,'No normal App before OTA; no native BLE started'
 # A reconnect can coincide with power-up. The boot snapshot precedes the
 # foreground catalog/lease recovery and is not the current idle/storage
 # reply. Keep that evidence, then ask once after the console is quiet.
 # No reset, reconnect or repeated readiness polling is performed.
 if before['reason']!='query':
  state['initialNonQuerySnapshot']=before;save()
  before,rejected=current_query_snapshot()
  state['rejectedPreUpdateQueryFrames']=rejected
 # The initial read used to accept DIAG1 END while cached UART output
 # was still being transmitted. Require the terminal detail line and a quiet
 # interval before opening the native BLE operation; no second query/reset.
 tail_started=time.monotonic();tail_deadline=tail_started+2.5;previous_bytes=-1;quiet_since=None
 while time.monotonic()<tail_deadline:
  guard();assert not errors,errors
  collected=(out/'uart.log').read_bytes()
  end_marker=b'DIAG1 END seq='+str(before['seq']).encode()
  pos=collected.rfind(end_marker);end=collected.find(b'\n',pos) if pos>=0 else -1
  initial_tail=collected[end+1:] if end>=0 else b''
  terminal=bool(re.search(rb'(?m)^XFER3 [^\r\n]+\r?$',initial_tail))
  if len(collected)!=previous_bytes:previous_bytes=len(collected);quiet_since=time.monotonic()
  if terminal and quiet_since is not None and time.monotonic()-quiet_since>=.150:break
  time.sleep(.025)
 else:raise RuntimeError('Initial UART details did not finish quietly; no native BLE started and no second query')
 state['initialDiagnosticTail']=dict(terminalXfer3Observed=True,quietSecondsAtLeast=.150,elapsedSeconds=time.monotonic()-tail_started,bleNotYetStarted=True,extraQueryCommands=0)
 state['beforeSnapshot']=before;save()
 s=before['sections']
 assert s['ID']['fw']==a.expected_before,('Installed App changed before OTA; no BLE started',s['ID']['fw'],a.expected_before)
 assert s['ID']['uid']==a.required_uid,('Unexpected target; no BLE started',s['ID']['uid'])
 if a.expected_ui_before is not None:assert s['ID']['ui']==a.expected_ui_before,'Pre-upgrade UI changed; no BLE started'
 assert s['STORAGE']['recording_ready']==1 and not s['STORAGE']['rec_fault'],('Recording storage not ready; no BLE started',s['STORAGE'])
 assert not s['AUDIO']['mic_run'] and not s['BLE']['linked'],('Target in use; no BLE started',s['AUDIO']['mic_run'],s['BLE']['linked'])
 if a.open_pair_window:
  pair.set();assert pair_sent.wait(3)
  deadline=time.monotonic()+12
  while time.monotonic()<deadline and b'PAIR1 OPEN window_ms=120000' not in (out/'uart.log').read_bytes():time.sleep(.1)
  assert b'PAIR1 OPEN window_ms=120000' in (out/'uart.log').read_bytes(),'Normal guarded pairing window did not open'
  state['normalPairWindowOpened']=True;save()
 if a.native_start_delay_ms:
  # Old711 can emit a synchronous1s periodic snapshot exactly during its
  # one-second catalog-release deadline. A measured phase offset permits
  # delivery of the firmware fix through the SAME normal signed protocol.
  # Keep UART observation and the ownership guard; no extra query or ATT.
  state['nativeStartDeferral']=dict(milliseconds=a.native_start_delay_ms,reason='legacy_uart_periodic_phase_collision_delivery_only',nativeNotYetStarted=True,changesReleaseDeadline=False,extraQueries=0);save()
  deferred_until=time.monotonic()+a.native_start_delay_ms/1000.0
  while time.monotonic()<deferred_until:
   guard();assert not errors,errors;time.sleep(min(.05,max(0.0,deferred_until-time.monotonic())))
 command=[str(exe),'--system-ota-transfer',str(a.bundle.resolve()),'--device-id',a.device_id];state['command']=command
 # The prior pre-OTA lane-release timeout had no native-stage trace. Enable
 # the installed opt-in only for this engineering child: timestamps are
 # bounded and emitted after release/cancellation, outside the DATA path.
 # This does not extend its deadline, retry CCCD writes, or add ATT requests.
 engineering_host=out/'engineering-host';engineering_host.mkdir(exist_ok=True)
 env=enable_preservation(dict(os.environ,COMPANION_TYPE_DISABLE_AUTO_RECOVERY='1',COMPANION_TYPE_DISABLE_AUTO_RECONNECT='1',COMPANION_TYPE_TRACE_CCCD_RELEASE='1'),engineering_host)
 state['cccdReleaseTrace']=dict(requested=True,environment='COMPANION_TYPE_TRACE_CCCD_RELEASE=1',scope='native_mutex_handler_detach_and_CCCD_wait; emit_after_operation; no_payload_timestamps',nativeStageEvidenceRequired=True,extraAttRequests=0,releaseDeadlineChanged=False,retryAdded=False)
 if a.rf_admission_receipt:
  env['COMPANION_TYPE_OTA_RF_ADMISSION']=str(a.rf_admission_receipt)
  env['COMPANION_TYPE_OTA_RF_NONCE']=a.rf_admission_nonce
 if a.trace_submit_prefix:env['COMPANION_TYPE_OTA_TRACE_PREFIX']='1'
 else:env.pop('COMPANION_TYPE_OTA_TRACE_PREFIX',None)
 if a.transport_profile=='automatic':env.pop('COMPANION_TYPE_SIMPLE_OTA_TRANSPORT',None)
 else:env['COMPANION_TYPE_SIMPLE_OTA_TRANSPORT']=a.transport_profile
 for partial in ([True,False] if a.interrupt_at_bytes else [False]):
  path=out/('type-interrupted.log' if partial else 'type.log')
  cut=None
  with path.open('wb') as log:
   child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=env,cwd=ROOT/'Companion-Type',creationflags=subprocess.CREATE_NO_WINDOW)
   state['nativeChildPid']=child.pid;save();deadline=time.monotonic()+a.max_seconds
   while child.poll() is None:
    guard()
    # UART observes; losing its USB must not abort the signed OTA/Boot flow.
    # Retain the existing native deadline and missing-proof failure. No
    # observer reconnect, board reset, or additional query from this loop.
    if errors and not state.get('uartObserverLostDuringNativeOta'):
     state['uartObserverLostDuringNativeOta']=list(errors);save()
    if partial:
     progress=re.findall(rb'payload_progress accepted=(\d+) total=(\d+)',path.read_bytes())
     if progress:
      accepted,total=map(int,progress[-1])
      if accepted>=a.interrupt_at_bytes:
       assert 0<accepted<total,'Only an actual incomplete download may be cut'
       cut={'deviceAcceptedBytes':accepted,'totalFileBytes':total,'processId':child.pid}
       child.terminate();child.wait(timeout=8);break
    if time.monotonic()>=deadline:raise RuntimeError('Native simple OTA exceeded diagnostic bound; preserve failure, no reset/retry')
    time.sleep(.1)
  if partial:
   assert cut,'First download ended before the requested actual partial receipt'
   state['deliberateHostInterruption']=cut;save()
   # Closing the owned process is the interruption. A second explicit request
   # starts from0 even when Windows temporarily retains the physical link.
   # Do not label it an observed RF disconnect without separate evidence.
   state['physicalDisconnectQualified']=False
   if a.observe_disconnect_after_interruption:
    # One queued normal query, no BLE reconnect/reset or repeated polling
    # commands. App replies only after its own protected operations release.
    observed,rejected=current_query_snapshot(timeout=30)
    s=observed['sections']
    assert s['ID']['fw']==a.expected_before and s['ID']['ui']==generation and s['ID']['uid']==a.required_uid,'Old running App/UI changed during incomplete download'
    assert s['BLE']['linked']==0 and s['BLE']['secured']==0,'No actual device disconnect observed; process exit alone is not enough'
    assert not s['AUDIO']['mic_run'] and s['STORAGE']['recording_ready']==1 and not s['STORAGE']['rec_fault'],'Old recording storage is not available after incomplete download'
    state.update(physicalDisconnectQualified=True,interruptedDownloadRunningSnapshot=observed,rejectedInterruptionFrames=rejected)
    save()
 state['exitCode']=child.returncode
 raw=(out/'type.log').read_text(errors='replace')
 rows=[x.split('firmware_ota_result_json=',1)[1] for x in raw.splitlines() if x.startswith('firmware_ota_result_json=')]
 if rows:
  report=json.loads(rows[-1]);state['nativeReport']=report
  state['wirelessOtaCompleted']=bool(report.get('systemBundle',{}).get('jointConfirmed') and report.get('systemBundle',{}).get('temporarySpaceReleased'))
  if a.interrupt_at_bytes:
   state['freshDownloadFromZero']=report.get('payloadMetrics',{}).get('resumedBytes')==0 and report.get('payloadMetrics',{}).get('newPayloadBytes')==envelope['firmware_bytes']+envelope['resource_bytes'] and report.get('firmwareBytes')==envelope['bytes']
   assert state['freshDownloadFromZero'],'Full new file from0 was not confirmed'
 state['afterSnapshot'],state['rejectedUartFrames']=current_query_snapshot(a.expected_post_boot_route if state['wirelessOtaCompleted'] else None)
 if state['wirelessOtaCompleted']:
  s=state['afterSnapshot']['sections'];assert s['ID']['fw']==version and s['ID']['ui']==generation and s['ID']['uid']==a.required_uid
  assert s['STORAGE']['recording_ready']==1 and not s['STORAGE']['rec_fault'] and not s['CORE']['stack_guard'] and not s['CORE']['stack_low']
  if a.post_update_recording_seconds:
   assert 2<=a.post_update_recording_seconds<=30,'Use a short capture only for the affected OTA workspace-release path'
   capture=out/'post-update-recording.json'
   capture_env=dict(env)
   if a.post_update_isolated_library:
    # Explicit diagnostics must not stand in for the normal product library.
    capture_library=out/'post-update-library';capture_library.mkdir(exist_ok=False)
    capture_env['COMPANION_TYPE_STATE_PATH']=str(capture_library/'sessions.json')
    # This new diagnostic take must satisfy the CLI's durable-consume gate.
    # Do not inherit the sealed throughput fixture's explicit keep policy.
    capture_env['COMPANION_TYPE_DELETE_AFTER_SYNC']='1'
    capture_env['COMPANION_TYPE_PRODUCT_SETTINGS_PATH']=str(capture_library/'product-settings.json')
    capture_env['COMPANION_TYPE_RECORDING_DIR']=str(capture_library/'recordings')
    capture_env['APPDATA']=str(capture_library/'appdata')
    capture_env['LOCALAPPDATA']=str(capture_library/'localappdata')
   state['postUpdateCaptureHostLibraryIsolated']=a.post_update_isolated_library
   state['originalSessionRecoveryQualified']=False
   capture_command=[str(exe),'--v1-real-meeting','--seconds',str(a.post_update_recording_seconds),'--device-id',a.device_id,'--output',str(capture)]
   with (out/'post-update-recording.log').open('wb') as log:
    child=subprocess.Popen(capture_command,stdout=log,stderr=subprocess.STDOUT,env=capture_env,cwd=ROOT/'Companion-Type',creationflags=subprocess.CREATE_NO_WINDOW)
    state.update(nativeChildPid=child.pid,captureCommands=None,postUpdateCaptureRequested=True);save();end=time.monotonic()+180
    while child.poll() is None:
     guard();assert not errors,errors
     if time.monotonic()>=end:raise RuntimeError('Post-update recording did not complete within diagnostic bound; no restart or substitute capture')
     time.sleep(.1)
   state['postUpdateRecordingExitCode']=child.returncode
   if capture.exists():state['postUpdateRecording']=json.loads(capture.read_bytes())
   state['postUpdateRecordingSnapshot'],state['rejectedPostRecordingUartFrames']=current_query_snapshot(a.expected_post_boot_route)
   assert child.returncode==0 and state.get('postUpdateRecording',{}).get('result')=='PASS_RECORDING_CONTROL_AND_RECEIVE_STAGE_ONLY','Actual post-update capture/stop/local receive was not confirmed'
   state['captureCommands']=2
  if a.post_update_upload_sample:post_update_existing_file_recovery()
  terminal_snapshot=(state.get('postUploadPhysicalIdle') if a.post_update_upload_sample else
      state.get('postUpdateRecordingSnapshot') if a.post_update_recording_seconds else state.get('afterSnapshot'))
  if terminal_snapshot:
   # Ordinary OTA has the same asynchronous disconnect as the optional
   # recovery path. Keep this lease/UART reader until the existing passive
   # helper confirms it; do not run another file receive just to wait idle.
   passive_post_update_idle('postPhysicalIdle',terminal_snapshot)
  state['result']='SIMPLE_WIRELESS_UPDATE_RUNNING_VERSIONS_CONFIRMED_NORMAL_APP'
 else:state['result']='SIMPLE_WIRELESS_UPDATE_NOT_COMPLETED'
except BaseException as e:state.update(result='SIMPLE_WIRELESS_UPDATE_NOT_COMPLETED',error=repr(e),failureTraceback=traceback.format_exc())
finally:
 if child and child.poll() is None:child.terminate();child.wait(timeout=8)
 stop.set()
 if thread:thread.join(3);assert not thread.is_alive(),'UART still owns board'
 state.update(ownedHandlesClosed=True,uartErrors=errors,finishedAtLocal=datetime.now().astimezone().isoformat(timespec='seconds'),sharedOwnershipGuard=owner_guard.summary());save()
 if held:
  with board_turn.turn_lock():
   board_turn.release('codex',state['result']+'；实际Type/BLE/UART关闭，wirelessCompleted='+str(state['wirelessOtaCompleted'])+'；依据'+str(out/'result.json'))
 if a.trace_submit_prefix:
  # Only inspect already closed files, after releasing hardware. A partial
  # diagnostic must never replace the real update outcome or trigger a retry.
  try:
   from analyze_companion_submit_prefix import persist_run_prefixes
   state['submitPrefixDiagnostics']=persist_run_prefixes(out)
  except Exception as e:
   state['submitPrefixDiagnosticError']=repr(e)
  save()
 print(json.dumps({k:state.get(k) for k in ['result','wirelessOtaCompleted','error','exitCode']},ensure_ascii=False))
raise SystemExit(0 if state['result']=='SIMPLE_WIRELESS_UPDATE_RUNNING_VERSIONS_CONFIRMED_NORMAL_APP' else 1)
