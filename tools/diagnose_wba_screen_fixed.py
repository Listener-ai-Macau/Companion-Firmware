"""One bounded, exclusively leased fixed-frame isolation, then exact restoration.

Uses only the fixed V3 and its UART. A complete idle normal-app snapshot is
required before any SWD connection. Only the bounded diagnostic boot prefix
may be replaced; the whole prior image is read first and verified after restore.
No option bytes, NOR, recordings, power measurements or alternate reset modes.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, sys, time
from pathlib import Path
import serial
from serial.tools import list_ports

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.cache/screen-visible-cadence-20261009'))
from cube_api_session import Session
from provision_wba_v11 import probe_lock, validate_identity
from wba_flash_geometry import for_mcu
from diagnose_wba_uart import collect, parse_frames
SN='004400403532510B31333430'
UID='180010000d50335754363720'
OWNER='01a113d4-af0d-7d71-89f8-e88e99e2a019'
BOARD=ROOT.parent/'docs/board_operations.md'
sha=lambda b:hashlib.sha256(b).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--diagnostic',type=Path,required=True)
    ap.add_argument('--product',type=Path,required=True)
    ap.add_argument('--reference-product',type=Path,required=True,
        help='Product used when compiling this diagnostic; current product may be newer only with identical screen sources/options')
    ap.add_argument('--checkpoint',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(); diag=a.diagnostic.resolve(); product=a.product.resolve()
    out=a.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    build=json.loads((diag/'build.json').read_bytes())
    checkpoint=json.loads(a.checkpoint.read_bytes())
    app=json.loads((product/'app-build.json').read_bytes())
    boot=json.loads((product/'boot-build.json').read_bytes())
    expected_fw=f'{app["firmware_version"]:08x}'
    assert checkpoint['result']=='GIT_SCREEN_CHECKPOINT_CREATED'
    diagnostic_id=build['diagnosticId']
    assert diagnostic_id in ('COMP_SCREEN_FIXED_V1','COMP_SCREEN_FIXED_GPIO_V2','COMP_SCREEN_BUS_ISOLATION_V3','COMP_SCREEN_STATUS_PHASE_V4','COMP_SCREEN_SELECTED_QUIET_V5','COMP_SCREEN_HELD_CONTROL_V6')
    bus_isolation=build.get('busIsolation',False)
    status_phase=build.get('statusPhase',False)
    assert bus_isolation==(diagnostic_id in ('COMP_SCREEN_BUS_ISOLATION_V3','COMP_SCREEN_HELD_CONTROL_V6'))
    assert build.get('heldControl',False)==(diagnostic_id=='COMP_SCREEN_HELD_CONTROL_V6')
    assert status_phase==(diagnostic_id in ('COMP_SCREEN_STATUS_PHASE_V4','COMP_SCREEN_SELECTED_QUIET_V5'))
    assert build.get('selectedQuietMs',0)==(20 if diagnostic_id=='COMP_SCREEN_SELECTED_QUIET_V5' else 0)
    assert app['firmware_version']==boot['firmware_version']
    # Another chat may have installed a newer joint recording image while
    # this diagnostic was compiled. Reuse the diagnostic only when the exact
    # screen source and every panel/shared-GPIO build setting still match.
    reference=json.loads((a.reference_product.resolve()/'app-build.json').read_bytes())
    assert build['installedAppSha256']==reference['bin_sha256']
    assert build['installedFirmwareReference']==reference['firmware_version']
    screen_sources=('app/companion_pendant/epaper/ssd1681_wba.c',
        'app/companion_pendant/epaper/ssd1681_wba.h','platform/stm32wba55_companion_v11/board_hal.c',
        'platform/stm32wba55_companion_v11/panel_boot_idle.h')
    for name in screen_sources:
        assert app['source_sha256'][name]==build['source_sha256'][name],('Joint screen source changed',name)
    for key in reference:
        if key.startswith('panel_') or key=='shared_spi_gpio_enabled':
            assert app[key]==reference[key],('Joint screen configuration changed',key)
    for name,expected in build['source_sha256'].items():
        assert sha((ROOT/name).read_bytes())==expected,('Diagnostic source changed',name)
    combined=(product/'companion-v11-initial-boot-and-app.bin').read_bytes()
    app_bytes=(product/'companion-v11-app.bin').read_bytes()
    boot_bytes=(product/'companion-v11-boot.bin').read_bytes()
    assert sha(app_bytes)==app['bin_sha256'] and sha(boot_bytes)==boot['bin_sha256']
    assert combined==boot_bytes+b'\xff'*(32768-len(boot_bytes))+app_bytes
    image=(diag/build['image']).read_bytes()
    assert sha(image)==build['imageSha256']
    extent=(len(image)+8191)//8192*8192
    assert 0<extent<=32768, 'Diagnostic must fit entirely within resident boot pages'
    replacement=image+b'\xff'*(extent-len(image))
    diagnostic_file=out/'diagnostic-boot-prefix.bin'; diagnostic_file.write_bytes(replacement)
    g=for_mcu('STM32WBA55CEU6')
    expected_product=combined+b'\xff'*(g.nvm_offset-len(combined))
    report={'result':'NOT_STARTED','startedAtLocal':datetime.datetime.now().isoformat(),
        'diagnosticId':build['diagnosticId'],'diagnosticSha256':build['imageSha256'],
        'diagnosticSourceCommit':checkpoint['commit'],'productFw':expected_fw,
        'productAppSha256':app['bin_sha256'],'writesStarted':False,'productRestored':False,
        'ownedHandlesClosed':True,'norCommands':False,'optionByteWrites':False,
        'bleConnected':False,'powerDiagnosis':False,'screenFixed':False,
        'panelPowerRetained':True,'diagnosticFlashBytes':extent}
    report['gpioMonitor']=build.get('gpioMonitor',False)
    report['instrumentedBitTiming']=build.get('instrumentedBitTiming',False)
    report['busIsolation']=bus_isolation
    report['statusPhase']=status_phase
    report['selectedQuietMs']=build.get('selectedQuietMs',0)
    report['heldControl']=build.get('heldControl',False)
    report['panelCommands']=build.get('panelCommands',True)
    stage='screen-fixed-isolation-'+datetime.datetime.now().strftime('%H%M%S')
    line=(f'- **占用中**：Companion 屏幕修复（{OWNER}，{report["startedAtLocal"]}，{stage}）。'
        f'一次正常{expected_fw}/UI67且录音/上传/BLE空闲UART后，临时运行{diagnostic_id}；'+
        ('零时钟/零命令：先真实20ms静置，分别保持DC低/CS高与CS低/DC高，前后静置对照，不重复双线低或快速单线切换。' if report['heldControl'] else
         '真实20ms静置后仅一条0x2F只读命令，逐位/方向切换记录BUSY，首次高/上升沿即停止后续时钟；无初始化/显示激活。' if status_phase else
         '零屏幕命令：夹入静置对照，分别切换SCK/SDIN/DC；CS单独切换时SCK保持低，MCU数字采样不等于屏幕端波形。' if bus_isolation else
         '同SSD1681源码/软件GPIO发送次序/64NOP/PLL参数，固定两帧，排除产品调度/资源/其它外设任务。')+
        '只替换内部boot前页，完成后恢复读回的当前联合包并全片/NVM比较；两次软件重启用于独立入口和恢复，'
        'EPD不断电、无虚构复位脚，不改NOR/录音/OB/云端、不查供电；关闭实际句柄再释放。')
    if report['gpioMonitor']:
        line+=' 仅新增MCU侧GPIO数字自读，寄存器发送位周期含额外读取，不能当生产电气时序。'
    if report['selectedQuietMs']:
        line+=' 相对V4只在选中CS/DC低后、首时钟前保持20ms并检查BUSY，不忽略上升沿。'
    leased=False; before=None; restore_file=out/'restore-product-boot-prefix.bin'
    def save(): (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def owners(text):
        return [v for v in text.split('## 当前占用',1)[1].split('## 交接方式',1)[0].splitlines() if '**占用中**' in v]
    def lease():
        assert owners(BOARD.read_text(encoding='utf-8-sig'))==[line], 'Exclusive lease changed'
    def uart_snapshot(path,seconds):
        lease(); ports=[p.device for p in list_ports.comports() if p.serial_number==SN]
        assert len(ports)==1,'Fixed V3 UART mapping is not unique'
        report['ownedHandlesClosed']=False; save()
        with path.open('wb') as log:
            collect(ports[0],seconds,False,lambda data:(log.write(data),log.flush()),tail_seconds=.6)
        report['ownedHandlesClosed']=True
        raw=path.read_bytes(); start=raw.find(b'DIAG1 BEGIN '); end=raw.rfind(b'DIAG1 END ')
        assert start>=0 and end>=start,'No complete normal-app UART snapshot'
        end=raw.find(b'\n',end); assert end>=0,'Truncated final END'
        frames,rejected=parse_frames(raw[start:end+1]); assert frames and not rejected,rejected
        s=frames[-1]['sections']
        assert s['ID']['uid']==UID and s['ID']['fw']==expected_fw and s['ID']['ui']==67,s['ID']
        return frames[-1]
    class PrefixSession(Session):
        def write_prefix(self,path):
            lease()
            assert path in (diagnostic_file,restore_file) and path.stat().st_size==extent
            assert extent%8192==0 and extent<=32768
            self.checked(self.api.downloadFile(str(path),g.flash_base,0,1,None),'bounded boot-prefix download/verify')
    def verify_target(p):
        assert validate_identity(p.read(0xE0044000,4,'device-id.bin'),p.read(0x0BF907A0,2,'flash-size.bin'),
            p.read(0x40022040,4,'option-bytes.bin'),p.read(0x0BF90700,12,'uid.bin'),g)==UID
    def frozen(p):
        original=int.from_bytes(p.read(0xE0044008,4,'freeze-original.bin'),'little')
        p.word(0xE0044008,original|0x1000)
        assert int.from_bytes(p.read(0xE0044008,4,'freeze-enabled.bin'),'little')&0x1000
        assert int.from_bytes(p.read(0xE000EDF0,4,'halted.bin'),'little')&(1<<17)
        return original
    def unfreeze(p,original):
        current=int.from_bytes(p.read(0xE0044008,4,'freeze-before-restore.bin'),'little')
        p.word(0xE0044008,(current&~0x1000)|(original&0x1000))
        assert int.from_bytes(p.read(0xE0044008,4,'freeze-restored.bin'),'little')&0x1000==original&0x1000
    def diagnostic_uart():
        lease(); ports=[p.device for p in list_ports.comports() if p.serial_number==SN]; assert len(ports)==1
        report['ownedHandlesClosed']=False; save(); raw=bytearray()
        # Closing serial is guaranteed even if the dedicated diagnostic fails.
        link=serial.Serial(port=None,baudrate=115200,timeout=.1,write_timeout=1)
        link.dtr=link.rts=False; link.port=ports[0]
        with link:
            lease(); link.write(b'\nHELLO\n'); link.flush()
            started=time.monotonic(); qualified=False; sent=False; ready_query=False
            with (out/'diagnostic-uart.log').open('wb') as log:
                while time.monotonic()-started<55:
                    chunk=link.read(min(max(link.in_waiting,1),4096)); raw.extend(chunk); log.write(chunk); log.flush()
                    text=raw.decode('ascii',errors='replace')
                    # The first request may arrive while the diagnostic is
                    # configuring its UART. A captured READY alone is not UID
                    # evidence: request HELLO once after that live marker and
                    # require its complete identity response before RUN_ONCE.
                    if not qualified and not ready_query and f'READY id={diagnostic_id} clock_ok=1 ' in text:
                        lease(); link.write(b'HELLO\n'); link.flush(); ready_query=True
                        report['helloRequestedAfterReady']=True; save()
                    for row in text[:text.rfind('\n')+1].splitlines():
                        if not row.startswith(f'HELLO id={diagnostic_id} '): continue
                        fields=dict(t.split('=',1) for t in row.split()[1:] if '=' in t)
                        if fields.get('uid')==UID and fields.get('target_ok')=='1' and fields.get('ran')=='0' and fields.get('rx_faults')=='0':
                            qualified=True
                    if qualified and not sent:
                        lease(); link.write(b'RUN_ONCE\n'); link.flush(); sent=True
                        report['diagnosticHelloVerified']=True; report['fixedFrameCommandSent']=not (bus_isolation or status_phase)
                        report['busIsolationCommandSent']=bus_isolation; save()
                        report['statusPhaseCommandSent']=status_phase; save()
                    if not qualified and time.monotonic()-started>8: raise RuntimeError('Dedicated diagnostic identity/clock was not qualified')
                    if f'END id={diagnostic_id} ' in text and text.endswith('\n'): break
                    if len(raw)>512*1024: raise RuntimeError('Diagnostic UART exceeded bound')
            text=raw.decode('ascii',errors='replace')
            end=[s for s in text.splitlines() if s.startswith(f'END id={diagnostic_id} ')]
            assert qualified and sent and len(end)==1,'No complete bounded diagnostic result'
            report['diagnosticEnd']=end[0]
            report['diagnosticLines']=[s for s in text.splitlines() if s.startswith(('FRAME ','VISIBLE ','READ_STATUS ','GPIO_CHECK ','GPIO_MISMATCH ','BUS_BEGIN ','PIN_PHASE ','PIN_ABORT ','STATUS_READY ','STATUS_PHASE ','READY ','HELLO '))]
            if bus_isolation:
                fields=dict(t.split('=',1) for t in end[0].split()[1:] if '=' in t)
                assert fields.get('panel_commands')=='0' and fields.get('transfers')=='0','Unexpected panel command/transfer'
                assert not any(s.startswith(('FRAME ','VISIBLE ','READ_STATUS ','BUS ')) for s in text.splitlines())
                report['busIsolationResult']=fields.get('result')
                report['pinPhaseCount']=len([s for s in report['diagnosticLines'] if s.startswith('PIN_PHASE ')])
            if status_phase:
                fields=dict(t.split('=',1) for t in end[0].split()[1:] if '=' in t)
                assert fields.get('activations')=='0' and int(fields['command_bits'])<=8 and int(fields['read_bits'])<=8
                assert int(fields.get('selected_quiet_ms',0))==report['selectedQuietMs']
                assert not any(s.startswith(('FRAME ','VISIBLE ','READ_STATUS ','BUS ','PIN_PHASE ')) for s in text.splitlines())
                report['statusPhaseEndFields']=fields
            report['diagnosticUartSha256']=sha(bytes(raw))
        report['ownedHandlesClosed']=True; save()
    try:
        text=BOARD.read_text(encoding='utf-8-sig'); assert not owners(text),'Another chat holds the board'
        assert BOARD.read_text(encoding='utf-8-sig')==text,'Shared record changed before lease'
        BOARD.write_text(text.replace('## 当前占用','## 当前占用\n\n'+line,1),encoding='utf-8'); leased=True
        lease(); save()
        pre=uart_snapshot(out/'before-uart.log',8); report['preSnapshot']=pre
        s=pre['sections']
        assert s['STORAGE']['recording_ready']==1 and s['STORAGE']['rec_state'] in (1,6)
        assert s['STORAGE']['rec_fault']==0 and s['AUDIO']['mic_run']==0 and s['BLE']['linked']==0
        assert int(s['POWER']['sleep_block'],16)&sum(1<<b for b in (0,1,8,11,12,13,14))==0
        with probe_lock(SN):
            try:
                install=out/'install'; install.mkdir(); report['ownedHandlesClosed']=False; save()
                with PrefixSession(SN,install,lease) as p:
                    verify_target(p); original=frozen(p)
                    try:
                        before=p.read(g.flash_base,g.flash_bytes,'before-internal.bin')
                        assert before[:g.nvm_offset]==expected_product,'Current Flash differs from referenced joint product'
                        restore_file.write_bytes(before[:extent])
                        report['writesStarted']=True; save()
                        p.write_prefix(diagnostic_file)
                        assert p.read(g.flash_base,extent,'diagnostic-prefix-readback.bin')==replacement
                        assert p.read(g.flash_base+g.nvm_offset,g.flash_bytes-g.nvm_offset,'nvm-after-diag.bin')==before[g.nvm_offset:]
                        report['diagnosticInstalledReadbackVerified']=True
                    finally:
                        unfreeze(p,original)
                        p.reset() # Start the isolated entry, or return interrupted product if no writes.
                report['ownedHandlesClosed']=True; save()
                diagnostic_uart()
            finally:
                if report['writesStarted'] and before is not None:
                    # Exact restoration of our own temporary boot pages is a
                    # bounded cleanup, not a no-UART product-install fallback.
                    restore=out/'restore'; restore.mkdir(); report['ownedHandlesClosed']=False; save()
                    with PrefixSession(SN,restore,lease) as p:
                        verify_target(p); original=frozen(p)
                        try:
                            p.write_prefix(restore_file)
                            after=p.read(g.flash_base,g.flash_bytes,'after-internal.bin')
                            assert after==before,'Restored product Flash or pairing NVM differs'
                            report['productRestored']=True; report['fullImageAndNvmRestored']=True
                        finally:
                            unfreeze(p,original)
                        p.reset()
                    report['ownedHandlesClosed']=True; save()
        post=uart_snapshot(out/'after-uart.log',12)
        report['postSnapshot']=post; report['restoredRuntimeIdentityVerified']=True
        report['result']='STATUS_PHASE_RECORDED_PRODUCT_RESTORED' if status_phase else 'BUS_ISOLATION_RECORDED_PRODUCT_RESTORED' if bus_isolation else 'FIXED_FRAME_DIAGNOSTIC_RECORDED_PRODUCT_RESTORED'
    except Exception as e:
        report['result']='DIAGNOSTIC_PHASE_ENDED'; report['error']=repr(e)
        if report['productRestored'] and not report.get('restoredRuntimeIdentityVerified'):
            # Our restoration reset has already run; one necessary identity
            # confirmation completes cleanup even when the diagnostic failed.
            try:
                post=uart_snapshot(out/'after-failed-diag-uart.log',12)
                report['postSnapshot']=post; report['restoredRuntimeIdentityVerified']=True
            except Exception as identity_error:
                report['restoreRuntimeIdentityError']=repr(identity_error)
    finally:
        report['ownedHandlesClosed']=True
        report['finishedAtLocal']=datetime.datetime.now().isoformat(); save()
        if leased:
            text=BOARD.read_text(encoding='utf-8-sig'); assert line in text,'Own lease entry changed'
            release=(f'- **已释放**：Companion 屏幕修复（{OWNER}，{report["finishedAtLocal"]}，{stage}）。'
                f'{report["result"]}；诊断写入={report["writesStarted"]}，原联合包全片/NVM恢复={report["productRestored"]}，'
                f'恢复运行身份={report.get("restoredRuntimeIdentityVerified",False)}；实际UART/SWD/API关闭，'
                '无NOR/OB/录音/消费/BLE/云端/供电诊断。若已写入，发生临时入口及恢复的软件重启，'
                f'后续无线结果须按新的运行上下文；EPD保持供电，屏幕未认定修好。证据{out.relative_to(ROOT.parent).as_posix()}/result.json。')
            assert BOARD.read_text(encoding='utf-8-sig')==text,'Record changed before release'
            BOARD.write_text(text.replace(line,release,1),encoding='utf-8')
        print(json.dumps({k:report.get(k) for k in ('result','error','diagnosticEnd','writesStarted','productRestored','restoredRuntimeIdentityVerified','ownedHandlesClosed')},ensure_ascii=False),flush=True)
    return 0 if report['result'] in ('FIXED_FRAME_DIAGNOSTIC_RECORDED_PRODUCT_RESTORED','BUS_ISOLATION_RECORDED_PRODUCT_RESTORED','STATUS_PHASE_RECORDED_PRODUCT_RESTORED') else 1

if __name__=='__main__': sys.exit(main())
