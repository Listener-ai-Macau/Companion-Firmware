"""Capture MCU BUSY run lengths without SWD reads during sampling.

Requires an exact installed product ELF/package and one complete idle UART
reply. Only a saved 4 KiB stack scratch region, core context, watchdog debug
freeze and DWT instrumentation may be changed. Restore the same running
product without reset. A failed precondition ends this invocation.
"""
from __future__ import annotations
import argparse
import ctypes as c
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import time
from serial.tools import list_ports

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.cache/screen-visible-cadence-20261009'))
from cube_api_session import Session
from diagnose_wba_uart import collect, parse_frames
from provision_wba_v11 import probe_lock, validate_identity
from wba_flash_geometry import for_mcu

SN = '004400403532510B31333430'
UID = '180010000d50335754363720'
OWNER = '01a113d4-af0d-7d71-89f8-e88e99e2a019'
BOARD = ROOT.parent / 'docs/board_operations.md'
DBG, DHCSR, DCRSR, DCRDR = 0xe0044008, 0xe000edf0, 0xe000edf4, 0xe000edf8
DEMCR, DWT_CTRL, CYCCNT = 0xe000edfc, 0xe0001000, 0xe0001004
SCRATCH, SCRATCH_BYTES, RESULT = 0x2001a000, 4096, 0x2001a400
CODE_SHA = '9669819af47e3a8ae540b80d0c79b96e0c95b1875243d81b40705f43a2a9f292'
ARM = Path('C:/Program Files (x86)/Arm GNU Toolchain arm-none-eabi/14.2 rel1/bin')

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def active_owners(text):
    return [x for x in text.split('## 当前占用', 1)[1].split('## 交接方式', 1)[0].splitlines()
            if '**占用中**' in x]

def elf_addresses(elf):
    expressions = {
        'status': '&companion_v11.panel.status', 'stage': '&companion_v11.panel.stage',
        'calls': '&companion_v11.panel.stats.transfer_calls', 'tick': '&uwTick',
        'next': '&companion_app.presenter.recovery_full_not_before_ms',
        'armed': '&companion_app.presenter.recovery_full_guard_armed',
        'core_hz': '&SystemCoreClock', 'stack_bottom': '&_sstack', 'bss_end': '&_ebss'}
    cmd = [str(ARM / 'arm-none-eabi-gdb.exe'), '--batch', '-q', str(elf)]
    for expression in expressions.values(): cmd += ['-ex', 'p/x ' + expression]
    output = subprocess.run(cmd, capture_output=True, check=True).stdout.decode(errors='replace')
    values = re.findall(r'\$\d+ = (0x[0-9a-f]+)', output)
    if len(values) != len(expressions): raise RuntimeError('ELF address extraction failed: ' + output)
    addresses = dict(zip(expressions, (int(v, 16) for v in values)))
    assert addresses['stack_bottom'] == SCRATCH and addresses['bss_end'] <= SCRATCH
    return addresses

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--elf', type=Path, required=True)
    parser.add_argument('--capture-build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    candidate, elf = args.candidate.resolve(), args.elf.resolve()
    package = json.loads((candidate / 'candidate.json').read_bytes())
    build = json.loads((candidate / 'app-build.json').read_bytes())
    app = candidate / 'companion-v11-app.bin'
    assert sha(app) == package['files'][app.name]['sha256']
    assert sha(elf) == build['elf_sha256']
    assert build['source_sha256']['app/companion_pendant/epaper/ssd1681_wba.c'] == CODE_SHA
    capture_build = json.loads(args.capture_build.read_bytes())
    image = args.capture_build.resolve().parent / capture_build['image']
    data = image.read_bytes()
    assert sha(image) == capture_build['imageSha256'] and 4 <= len(data) <= 1024
    for name, expected in capture_build['source_sha256'].items(): assert sha(ROOT / name) == expected
    addresses = elf_addresses(elf)
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    state = dict(result='BUSY_RAM_PENDING', startedAtLocal=datetime.now().isoformat(),
                 firmware=package['firmware'], appSha256=sha(app), elfSha256=sha(elf),
                 captureSha256=sha(image), addresses=addresses, resetsIssued=False,
                 internalFlashWrites=False, norWrites=False, gpioWrites=False, panelCommands=False,
                 scratchRestored=False, contextRestored=False, coreResumed=False,
                 debugRestored=False, haltIssued=False, cleanupErrors=[])
    stage = out.name
    line = (f'- **占用中**：Companion 屏幕修复（{OWNER}，{state["startedAtLocal"]}，{stage}）。'
            f'新假设：SWD逐次访问或前台采样漏掉BUSY稳定窗口；精确{package["firmware"]}/UI67正常空闲门后，'
            '主控约100ms SRAM密集采样，期间无SWD访问；保存/恢复原4KiB空闲栈、CPU上下文及DWT。'
            '不复位/Flash/NVM/NOR/屏幕命令/电源诊断，实际句柄关闭才释放。')
    leased = False
    def lease(): assert active_owners(BOARD.read_text(encoding='utf-8-sig')) == [line]
    class Limited(Session):
        def __init__(self): super().__init__(SN, out, lease, connection_mode=1)
        def reset(self, *a): raise RuntimeError('Reset forbidden')
        def write_image(self, *a): raise RuntimeError('Flash write forbidden')
        def store(self, address, value, name):
            self.lease()
            if isinstance(value, int): value = value.to_bytes(4, 'little')
            assert ((SCRATCH <= address and address + len(value) <= SCRATCH + SCRATCH_BYTES) or
                    (address in (DBG, DHCSR, DCRSR, DCRDR, DEMCR, DWT_CTRL, CYCCNT) and len(value) == 4))
            self.checked(self.api.writeMemory(address, c.create_string_buffer(value), len(value)),
                         'bounded capture write ' + name)
            (out / name).write_bytes(value)
    try:
        text = BOARD.read_text(encoding='utf-8-sig')
        assert not active_owners(text), 'Other owner holds board; no handle opened'
        assert BOARD.read_text(encoding='utf-8-sig') == text
        BOARD.write_text(text.replace('## 当前占用', '## 当前占用\n\n' + line, 1), encoding='utf-8-sig')
        leased = True
        ports = [p.device for p in list_ports.comports() if p.serial_number == SN]; assert len(ports) == 1
        with (out / 'before-uart.log').open('wb') as log:
            collect(ports[0], 8, False, lambda b: (log.write(b), log.flush()), tail_seconds=.6)
        frames, rejected = parse_frames((out / 'before-uart.log').read_bytes())
        assert frames and not rejected, 'No complete application reply; do not open SWD'
        s = frames[-1]['sections']; state['before'] = s
        assert s['ID']['fw'] == f'{package["firmwareVersion"]:08x}' and s['ID']['uid'] == UID and s['ID']['ui'] == 67
        assert not s['AUDIO']['mic_run'] and not s['BLE']['linked']
        assert s['STORAGE']['rec_state'] in (1, 6) and not s['STORAGE']['rec_fault']
        assert not int(s['POWER']['sleep_block'], 16) & sum(1 << b for b in (0, 1, 8, 11, 12, 13, 14))
        assert s['DISPLAY']['driver'] == 4 and s['DISPLAY']['stage'] == 5 and s['DISPLAY']['transfer_calls'] == 0
        with probe_lock(SN), Limited() as p:
            serial_read = 0
            def word(address, label):
                nonlocal serial_read
                serial_read += 1
                return int.from_bytes(p.read(address, 4, f'{serial_read:03}-{label}.bin'), 'little')
            def reg(selector, value=None):
                nonlocal serial_read
                serial_read += 1; prefix = f'{serial_read:03}-reg{selector}'
                assert selector in (*range(19), 20)
                if value is not None: p.store(DCRDR, value, prefix + '-data.bin')
                p.store(DCRSR, selector | (0x10000 if value is not None else 0), prefix + '-select.bin')
                for _ in range(3):
                    status = word(DHCSR, 'register-ready')
                    if status & 0x10000: break
                assert status & 0x30000 == 0x30000, 'Halted core register transfer unqualified'
                if value is None: return word(DCRDR, 'register-value')
            assert validate_identity(p.read(0xe0044000, 4, 'device-id.bin'), p.read(0x0bf907a0, 2, 'flash-size.bin'),
                p.read(0x40022040, 4, 'option-bytes.bin'), p.read(0x0bf90700, 12, 'uid.bin'),
                for_mcu('STM32WBA55CEU6')) == UID
            assert p.read(0x08008000, 32, 'vector-prefix.bin') == app.read_bytes()[:32]
            assert word(0xe000ed08, 'vtor') == 0x08008000
            assert not word(0xe000ed94, 'mpu-control') & 1, 'SRAM execution permissions not qualified'
            core = word(DHCSR, 'core-before'); assert not core & 0x2000e
            tick, next_ms = word(addresses['tick'], 'tick'), word(addresses['next'], 'next')
            assert p.read(addresses['armed'], 1, 'armed.bin')[0] == 1
            assert 4000 < ((next_ms - tick) & 0xffffffff) < 60000, 'Natural retry too close'
            assert word(addresses['calls'], 'calls-before') == 0
            hz = word(addresses['core_hz'], 'core-hz'); assert 16000000 <= hz <= 100000000
            peripheral = {name: word(address, name) for name, address in
                          [('spi1-cr1', 0x40013000), ('sai-a-cr1', 0x40015404), ('sai-b-cr1', 0x40015424)]}
            peripheral['dma'] = [word(0x40020064 + 0x80 * i, f'dma{i}') for i in range(8)]
            assert not peripheral['spi1-cr1'] & 1
            assert not (peripheral['sai-a-cr1'] | peripheral['sai-b-cr1']) & 0x10000
            assert not any(x & 1 for x in peripheral['dma']), 'Autonomous audio/DMA still enabled'
            state['autonomousPeripheralsBefore'] = peripheral
            gpio = p.read(0x42020000, 16, 'gpio-before.bin')
            assert (int.from_bytes(gpio[:4], 'little') >> 24) & 3 == 0
            assert (int.from_bytes(gpio[12:16], 'little') >> 24) & 3 == 0
            freeze = word(DBG, 'freeze-before'); demcr = word(DEMCR, 'demcr-before')
            dwt = word(DWT_CTRL, 'dwt-before'); cycles = word(CYCCNT, 'cycles-before')
            assert not dwt & (1 << 25), 'Cycle counter absent'
            # Recheck at the mutation boundary; the earlier UART and register
            # preflight cannot certify that natural screen recovery is idle now.
            mutation_tick = word(addresses['tick'], 'mutation-tick')
            mutation_next = word(addresses['next'], 'mutation-next')
            assert 4000 < ((mutation_next - mutation_tick) & 0xffffffff) < 60000
            assert p.read(addresses['status'], 1, 'mutation-status.bin')[0] == 4
            assert p.read(addresses['stage'], 1, 'mutation-stage.bin')[0] == 5
            assert word(addresses['calls'], 'mutation-calls') == 0
            context = {}; scratch = None; dirty_scratch = False; dirty_context = False
            halted = False; dwt_changed = False
            try:
                p.store(DBG, freeze | 0x1000, 'freeze-on.bin')
                state['haltIssued'] = True; halted = True; pause_start = time.monotonic()
                p.store(DHCSR, 0xa05f0003, 'halt.bin')
                assert word(DHCSR, 'halt-confirm') & 0x20000
                context = {i: reg(i) for i in (*range(19), 20)}
                state['savedContext'] = {str(k): hex(v) for k, v in context.items()}
                assert context[16] & 0x1ff == 0 and context[16] & 0x01000000, 'Paused outside foreground'
                # CONTROL.FPCA may already be set by the product's floating
                # point work. The soft-float integer-only capture preserves it;
                # still require privileged MSP foreground and no interrupt mask.
                assert context[20] & ~0x04000000 == 0, 'Foreground privilege/mask/stack state not qualified'
                assert context[13] == context[17] and 0x2001b400 <= context[17] <= 0x20020000
                # BLE uses CYCCNT for short delays. Preserve its halted value,
                # rather than rewinding to an earlier running preflight read.
                demcr = word(DEMCR, 'halted-demcr')
                dwt = word(DWT_CTRL, 'halted-dwt')
                cycles = word(CYCCNT, 'halted-cycles')
                scratch = p.read(SCRATCH, SCRATCH_BYTES, 'scratch-before.bin')
                dwt_changed = True
                p.store(DEMCR, demcr | (1 << 24), 'trace-on.bin')
                p.store(DWT_CTRL, dwt | 1, 'counter-on.bin')
                assert word(DWT_CTRL, 'counter-confirm') & 1
                dirty_scratch = True
                p.store(SCRATCH, data, 'capture-code.bin')
                config = bytearray(1168); struct.pack_into('<II', config, 8, hz // 10, hz)
                p.store(RESULT, bytes(config), 'capture-config.bin')
                assert p.read(SCRATCH, len(data), 'code-readback.bin') == data
                dirty_context = True
                reg(17, 0x2001b000); reg(16, 0x01000000); reg(20, context[20] | 1); reg(15, SCRATCH | 1)
                state['swdQuietStartedHostNs'] = time.perf_counter_ns()
                p.store(DHCSR, 0xa05f0001, 'run-capture.bin'); halted = False
                time.sleep(.2)  # No API calls/polling/SWD reads during the bounded capture.
                state['swdQuietEndedHostNs'] = time.perf_counter_ns()
                stopped = word(DHCSR, 'capture-halt-confirm') & 0x20000
                if not stopped:
                    p.store(DHCSR, 0xa05f0003, 'capture-deadline-halt.bin')
                    assert word(DHCSR, 'deadline-halt-confirm') & 0x20000
                halted = True
                raw = p.read(RESULT, 1168, 'capture-result.bin')
                words = struct.unpack('<292I', raw)
                names = ['magic','done','target_cycles','core_hz','samples','low_samples','high_samples','edges',
                         'elapsed_cycles','longest_low','longest_high','max_sample_gap','first_idr','last_idr',
                         'initial_level','final_level','low_runs','high_runs','low_20ms_runs','high_20ms_runs']
                capture = dict(zip(names, words[:20]))
                capture.update(low_bins=list(words[20:26]), high_bins=list(words[26:32]),
                               edges_recorded=words[32], invalid_counter=words[33],
                               swd_clock_changes=words[34], swd_data_changes=words[35],
                               first_edges=[dict(cycles=words[36+2*i], idr=words[37+2*i]) for i in range(min(words[32],128))])
                state['capture'] = capture
                assert stopped and capture['magic'] == 0x42555359 and capture['done'] == 0x444f4e45
                assert not capture['invalid_counter'] and capture['elapsed_cycles'] >= capture['target_cycles']
                assert capture['samples'] == capture['low_samples'] + capture['high_samples']
                state['result'] = 'MCU_BUSY_RUN_LENGTHS_CAPTURED_WITH_SWD_PIN_OBSERVATION'
            finally:
                def cleanup(label, fn):
                    try: return fn()
                    except Exception as exc:
                        state['cleanupErrors'].append(label + ': ' + repr(exc))
                        return None
                if state['haltIssued']:
                    cleanup('halt for restoration', lambda: p.store(DHCSR, 0xa05f0003, 'restore-halt.bin'))
                    halted = bool((cleanup('confirm restoration halt', lambda: word(DHCSR, 'restore-halt-confirm')) or 0) & 0x20000)
                state['scratchUnchanged'], state['contextUnchanged'] = not dirty_scratch, not dirty_context
                if halted:
                    if dirty_scratch and scratch is not None:
                        cleanup('restore scratch', lambda: p.store(SCRATCH, scratch, 'scratch-restored.bin'))
                        state['scratchRestored'] = cleanup('verify restored scratch',
                            lambda: p.read(SCRATCH, SCRATCH_BYTES, 'scratch-restored-read.bin')) == scratch
                    if dirty_context and context:
                        # SP aliases are restored via MSP/PSP, then r0..r12/LR/PC/xPSR and original CFBP.
                        for i in [17,18,*range(13),14,15,16,20]: cleanup('restore register ' + str(i), lambda i=i: reg(i, context[i]))
                        restored = {i: cleanup('verify restored register ' + str(i), lambda i=i: reg(i))
                                    for i in (*range(19),20)}
                        state['contextRestored'] = restored == context
                    if dwt_changed:
                        cleanup('restore cycle counter', lambda: p.store(CYCCNT, cycles, 'cycles-restored.bin'))
                        cleanup('restore DWT', lambda: p.store(DWT_CTRL, dwt, 'dwt-restored.bin'))
                        cleanup('restore DEMCR', lambda: p.store(DEMCR, demcr, 'demcr-restored.bin'))
                    cleanup('restore watchdog freeze', lambda: p.store(DBG, freeze, 'freeze-restored.bin'))
                    state['debugRestored'] = (cleanup('verify freeze', lambda: word(DBG, 'freeze-after')) == freeze and
                        cleanup('verify DEMCR', lambda: word(DEMCR, 'demcr-after')) == demcr and
                        cleanup('verify DWT', lambda: word(DWT_CTRL, 'dwt-after')) == dwt)
                    safe = (not dirty_scratch or state['scratchRestored']) and (not dirty_context or state['contextRestored'])
                    safe = safe and state['debugRestored'] and not state['cleanupErrors']
                    if safe: cleanup('resume product', lambda: p.store(DHCSR, 0xa05f0000 | (core & 1), 'resume-product.bin'))
                    else: state['cleanupErrors'].append('Product restoration incomplete; unsafe resume refused')
                else:
                    cleanup('restore watchdog freeze', lambda: p.store(DBG, freeze, 'freeze-restored.bin'))
                after_core = cleanup('confirm product running', lambda: word(DHCSR, 'core-after'))
                state['coreResumed'] = after_core is not None and not after_core & 0x20000
                state['pausedHostMs'] = (time.monotonic() - pause_start) * 1000 if state['haltIssued'] else 0
            assert p.read(0x42020000, 16, 'gpio-after.bin') == gpio
            assert word(addresses['calls'], 'calls-after') == 0
            assert state['coreResumed'] and state['debugRestored'] and not state['cleanupErrors']
            state['limits'] = ('MCU digital samples with nominal core clock; CPU foreground and interrupts suspended for the recorded host pause. '
                               'Host issues no reads during sampling; SWD pin counters must be checked before inferring bus quiet. '
                               'Sampling cannot exclude pulses between reads. Panel-side waveform, electrical amplitude, '
                               'translator versus panel cause and optical refresh quality are not measured.')
    except Exception as exc:
        state.update(result='BUSY_RAM_CAPTURE_ENDED', error=repr(exc))
    finally:
        state.update(finishedAtLocal=datetime.now().isoformat(), ownedHandlesClosed=True, screenFixed=False,
                     coreUnchanged=not state['haltIssued'])
        (out / 'result.json').write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        if leased:
            text = BOARD.read_text(encoding='utf-8-sig'); assert line in text
            release = (f'- **已释放**：Companion 屏幕修复（{OWNER}，{state["finishedAtLocal"]}，{stage}）。'
                       f'{state["result"]}；实际UART/SWD/API关闭，未暂停CPU={state["coreUnchanged"]}/恢复运行={state["coreResumed"]}，'
                       f'栈/上下文={state["scratchRestored"]}/{state["contextRestored"]}；无复位/Flash/NOR/屏幕命令/供电诊断。'
                       f'证据{out.relative_to(ROOT.parent).as_posix()}/result.json。')
            BOARD.write_text(text.replace(line, release, 1), encoding='utf-8-sig')
        print(json.dumps({k: state.get(k) for k in ('result','error','coreResumed','scratchRestored',
              'contextRestored','debugRestored','pausedHostMs','cleanupErrors','capture')}, ensure_ascii=False))

if __name__ == '__main__': main()
