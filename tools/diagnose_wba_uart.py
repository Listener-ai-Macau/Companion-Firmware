#!/usr/bin/env python3
"""Collect read-only WBA DIAG1 snapshots over 1.8 V UART, or parse a saved log.

This does not flash, reset, start recording, exercise hardware, or grant product
acceptance. Only the explicit serial port is opened. Output stays local.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import time

FIELDS = {
    'ID': 'fw build board uid ui uptime_ms',
    'CORE': 'reset iwdg_reset faults clock lse io imu touch audio mic nor panel battery ram_gap stack_min stack_low stack_guard',
    'DISPLAY': 'bound driver error presenter assets rendered failed',
    'STORAGE': 'jedec size layout recording_ready rec_state rec_fault committed',
    'AUDIO': 'mic_init mic_run mic_hal mic_irq_err mic_stale mic_overflow mic_reject deadline frames speaker_ready',
    'BLE': 'compiled init host host_error connection linked secured fatal',
    'POWER': 'adc voltage_valid percent_valid charger_valid charger_present mv pct charge ota_block sleep_block',
}
HEX = {'ID': {'fw': 8, 'build': 8, 'board': 8, 'uid': 24},
       'CORE': {'reset': 8, 'faults': 8}, 'STORAGE': {'jedec': 6, 'dw12': 8, 'dw13': 8},
       'BLE': {'connection': 4}, 'POWER': {'ota_block': 4, 'sleep_block': 8}}
BOOL = {'CORE': set(FIELDS['CORE'].split()) - {'reset', 'faults', 'ram_gap', 'stack_min'},
        'DISPLAY': {'bound', 'assets'}, 'STORAGE': {'layout', 'recording_ready', 'suspend_ok', 'erase_active', 'erase_sus'},
        'AUDIO': {'mic_init', 'mic_run', 'speaker_ready'},
        'BLE': {'compiled', 'init', 'host', 'linked', 'secured'},
        'POWER': {'adc', 'voltage_valid', 'percent_valid', 'charger_valid', 'charger_present'}}
MAX_CAPTURE = 4 * 1024 * 1024
DISPLAY_DETAIL_FIELDS = {'stage', 'busy', 'transfer_calls', 'busy_timeouts'}
AUDIO_TIMING_FIELDS = {'fg_ms', 'hal_ms', 'rec_ms', 'ble_ms', 'runtime_ms', 'present_ms', 'render_ms', 'pdm_ms'}
BLE_SECURITY_FIELDS = {'bond_lost', 'rebond', 'pair_status', 'pair_reason'}
STORAGE_NOR_FIELDS = {'suspend_ok', 'erase_active', 'erase_sus', 'sus_ms', 'resume_ms', 'bfp_dw', 'dw12', 'dw13'}
BATTERY_RAW_FIELDS = {'raw_mode', 'input_mv', 'input_valid', 'saturated', 'sample_age_ms'}
BATTERY_REFERENCE_RANGE_FIELDS = {'vdda_min_mv', 'vdda_max_mv'}
OPTIONAL_FIELDS = {
    'POWERCFG': 'top_ohm bottom_ohm max_cell_mv reference_floor_mv charger_pullups_verified soc_curve_verified',
    'TIMING': 'rec_id mic_starts tick_us min_samples enc_n enc_valid enc_p95_upper_ms enc_peak_upper_ms pdm_n pdm_valid pdm_p95_upper_ms pdm_peak_upper_ms',
    'BATTERY': 'vref_raw vref_cal vdda_mv vref_valid vref_age_ms vref_n raw samples adc_error adc_failures divider_safe divider_verified reference_verified sample_errors gate_errors',
}
BOOL['POWERCFG'] = {'charger_pullups_verified', 'soc_curve_verified'}
BOOL['TIMING'] = {'enc_valid', 'pdm_valid'}
BOOL['BATTERY'] = {'vref_valid', 'divider_safe', 'divider_verified', 'reference_verified',
                   'raw_mode', 'input_valid', 'saturated'}


def _tokens(line):
    parts = line.split()
    if len(parts) < 3 or parts[0] != 'DIAG1':
        raise ValueError('invalid DIAG1 line')
    values = {}
    for token in parts[2:]:
        if token.count('=') != 1:
            raise ValueError('invalid key/value token')
        key, value = token.split('=')
        if key in values or not value:
            raise ValueError('duplicate or empty field')
        values[key] = value
    seq = values.pop('seq', '')
    if not re.fullmatch(r'[0-9]{1,10}', seq) or int(seq) > 0xffffffff:
        raise ValueError('invalid sequence')
    return parts[1], int(seq), values


def parse_frames(raw: bytes):
    """Return complete frames and rejection reasons; never combine two sequences."""
    frames, rejected, active = [], [], None
    for line in raw.decode('ascii', errors='replace').splitlines():
        if not line.startswith('DIAG1'):
            continue  # Normal console text can coexist with snapshots.
        try:
            section, seq, values = _tokens(line)
            if section == 'BEGIN':
                if active is not None:
                    rejected.append('previous frame was truncated before BEGIN')
                active = None
                if set(values) != {'reason'} or values['reason'] not in {'boot', 'periodic', 'query'}:
                    raise ValueError('invalid BEGIN')
                active = {'seq': seq, 'reason': values['reason'], 'sections': {}}
                continue
            if active is None or seq != active['seq']:
                raise ValueError('section has no matching BEGIN sequence')
            if section == 'END':
                if values or not set(FIELDS) <= set(active['sections']):
                    raise ValueError('incomplete frame at END')
                frames.append(active)
                active = None
                continue
            if ((section not in FIELDS and section not in OPTIONAL_FIELDS) or
                    section in active['sections']):
                raise ValueError('unknown or duplicate section')
            expected_fields = set((FIELDS if section in FIELDS else OPTIONAL_FIELDS)[section].split())
            if section == 'DISPLAY' and DISPLAY_DETAIL_FIELDS <= set(values):
                expected_fields |= DISPLAY_DETAIL_FIELDS
            if section == 'AUDIO' and AUDIO_TIMING_FIELDS <= set(values):
                expected_fields |= AUDIO_TIMING_FIELDS
            if section == 'BLE' and BLE_SECURITY_FIELDS <= set(values):
                expected_fields |= BLE_SECURITY_FIELDS
            if section == 'STORAGE' and STORAGE_NOR_FIELDS <= set(values):
                expected_fields |= STORAGE_NOR_FIELDS
            if section == 'BATTERY' and BATTERY_RAW_FIELDS <= set(values):
                expected_fields |= BATTERY_RAW_FIELDS
            if section == 'BATTERY' and BATTERY_REFERENCE_RANGE_FIELDS <= set(values):
                expected_fields |= BATTERY_REFERENCE_RANGE_FIELDS
            if set(values) != expected_fields:
                raise ValueError('missing or unexpected fields in ' + section)
            parsed = {}
            for key, value in values.items():
                digits = HEX.get(section, {}).get(key)
                if digits:
                    if not re.fullmatch('[0-9a-fA-F]{' + str(digits) + '}', value):
                        raise ValueError('invalid hex ' + section + '.' + key)
                    parsed[key] = value.lower()  # Preserve leading zeros / UID byte order.
                else:
                    if not re.fullmatch(r'[0-9]{1,10}', value) or int(value) > 0xffffffff:
                        raise ValueError('invalid integer ' + section + '.' + key)
                    parsed[key] = int(value)
                    if (key in BOOL.get(section, set()) or (section == 'DISPLAY' and key == 'busy')) and parsed[key] not in (0, 1):
                        raise ValueError('invalid boolean ' + section + '.' + key)
            active['sections'][section] = parsed
        except ValueError as exc:
            rejected.append(str(exc))
            active = None
    if active is not None:
        rejected.append('frame truncated without END')
    return frames, rejected


def battery_status(frame):
    """Describe cell and MCU supply separately; invalid values are null, never 0%."""
    power = frame['sections']['POWER']
    adc = frame['sections'].get('BATTERY', {})
    if power['voltage_valid']:
        reason = 'VALID'
    elif not adc:
        reason = 'DETAIL_UNAVAILABLE'
    elif not adc['divider_verified']:
        reason = 'DIVIDER_UNVERIFIED'
    elif not adc['divider_safe']:
        reason = 'DIVIDER_RANGE'
    elif not adc['reference_verified'] and not adc.get('raw_mode', 0):
        reason = 'REFERENCE_UNVERIFIED'
    elif not power['adc']:
        reason = 'SAMPLING_DISABLED'
    elif adc.get('saturated', 0):
        reason = 'SATURATED'
    elif adc['adc_error']:
        reason = 'ADC_ERROR'
    elif not adc['samples']:
        reason = 'NOT_SAMPLED'
    elif adc.get('sample_age_ms', 0xffffffff) >= 15000:
        reason = 'STALE'
    elif adc.get('raw_mode', 0):
        reason = 'RAW_ONLY'
    else:
        reason = 'INVALID'
    supply_valid = bool(adc.get('vref_valid') and adc.get('vref_age_ms', 0xffffffff) < 15000)
    charges = ['UNKNOWN', 'CHARGING', 'POWERED_IDLE', 'DISCHARGING', 'FAULT']
    config = frame['sections'].get('POWERCFG')
    blockers = []
    if adc:
        for key, label in (('divider_verified', 'DIVIDER_UNVERIFIED'),
                           ('divider_safe', 'DIVIDER_RANGE')):
            if not adc[key]: blockers.append(label)
        if not adc['reference_verified'] and not adc.get('raw_mode', 0):
            blockers.append('REFERENCE_UNVERIFIED')
    else:
        blockers.append('DETAIL_UNAVAILABLE')
    sum_ohm = config['top_ohm'] + config['bottom_ohm'] if config else 0
    maximum_input = ((config['max_cell_mv'] * config['bottom_ohm'] + sum_ohm - 1) // sum_ohm
                     if sum_ohm else None)
    return {
        'cellState': reason,
        'cellMillivolts': power['mv'] if power['voltage_valid'] else None,
        'socPercent': power['pct'] if power['voltage_valid'] and power['percent_valid'] else None,
        'supplyMillivolts': adc.get('vdda_mv') if supply_valid else None,
        'supplyAgeMs': adc.get('vref_age_ms'),
        'supplyMinMillivolts': adc.get('vdda_min_mv') if adc.get('vref_n') else None,
        'supplyMaxMillivolts': adc.get('vdda_max_mv') if adc.get('vref_n') else None,
        'chargeState': charges[power['charge']] if power['charger_valid'] and 0 <= power['charge'] < len(charges) else 'UNKNOWN',
        'adcError': adc.get('adc_error'),
        'samplingBlockers': blockers,
        'configuration': config,
        'maximumNominalInputMillivolts': maximum_input,
        # Existing 100mV profile margin is configuration, not a measured rail.
        'requiredProfileSupplyMillivolts': maximum_input + 100 if maximum_input is not None else None,
        'chargeStateObservable': bool(config['charger_pullups_verified']) if config else None,
        'socCurveQualified': bool(config['soc_curve_verified']) if config else None,
    }


def diagnose(frame, expected_fw='00010128', expected_ui=58, expected_uid=None, screen_enabled=True):
    sections, issues = frame['sections'], []
    def issue(code, message):
        issues.append({'code': code, 'message': message})
    identity = sections['ID']
    if (identity['fw'] != expected_fw or identity['build'] != '20261004' or
            identity['board'] != '57424155' or identity['ui'] != expected_ui):
        issue('IDENTITY_MISMATCH', '固件、编译身份、板型或已挂载 UI 与本候选不匹配；核对配套安装包。')
    if identity['uid'] in {'0' * 24, 'f' * 24} or (expected_uid and identity['uid'] != expected_uid.lower()):
        issue('UID_MISMATCH', 'MCU UID 无效或与指定目标板不一致。')
    core, display, storage = sections['CORE'], sections['DISPLAY'], sections['STORAGE']
    audio, ble, power = sections['AUDIO'], sections['BLE'], sections['POWER']
    if int(core['faults'], 16):
        modules = {'clock': '主时钟', 'lse': '低速时钟', 'io': 'IO 扩展器', 'imu': 'IMU',
                   'touch': '触摸', 'audio': '音频', 'mic': '麦克风', 'nor': 'NOR', 'panel': '屏幕', 'battery': '电池'}
        names = '、'.join(label for key, label in modules.items() if core[key])
        issue('PRODUCT_FAULTS', '产品 fault=0x' + core['faults'] + '；已标记模块：' + (names or '未映射故障位') + '。需结合模块状态和实际接线定位。')
    if core['iwdg_reset']:
        issue('WATCHDOG_RESET', '本次启动含独立看门狗复位标志；保留串口日志，排查阻塞或崩溃，不能仅靠重启判定恢复。')
    if core['stack_low'] or core['stack_guard']:
        issue('STACK_FAULT', '栈水位过低或保护区已破坏；需保留日志并修复，不能继续以初始化成功判定运行可靠。')
    if screen_enabled and (not display['bound'] or display['driver'] not in (1, 2, 3) or display['presenter'] not in (0, 1)
            or display['error'] or not display['assets'] or display['failed']):
        issue('DISPLAY_NOT_READY', '屏幕、显示资源或刷新存在异常；检查 EPD_RES 接线和配套 UI，仍需实物显示验收。')
    if (storage['jedec'] in {'000000', 'ffffff'} or not storage['size'] or not storage['layout'] or
            not storage['recording_ready'] or storage['rec_state'] not in range(1, 7) or storage['rec_fault']):
        recording_faults = {0: '无具体错误码', 1: '采集平台', 2: 'PCM 溢出', 3: '处理超时',
                            4: 'Opus 编码', 5: '存储读写', 6: '麦克风控制'}
        detail = recording_faults.get(storage['rec_fault'], '未知码 ' + str(storage['rec_fault']))
        issue('STORAGE_NOT_READY', 'NOR/录音链未就绪或已有错误；录音故障：' + detail + '。检查对应模块；NOR 异常时核对供电、SPI 和分区。保留资料，勿直接擦除。')
    if not audio['mic_init'] or any(audio[k] for k in ('mic_hal', 'mic_irq_err', 'mic_stale', 'mic_overflow', 'mic_reject', 'deadline')):
        issue('MICROPHONE_OR_DEADLINE', '麦克风初始化、DMA/帧处理或处理时限有异常；保存日志并核对 PDM 时钟/数据及负载。')
    if not audio['speaker_ready']:
        issue('SPEAKER_NOT_READY', '扬声器驱动未就绪；核对音频初始化与功放控制，实际宠物音效仍需实听。')
    if not ble['compiled'] or not ble['init'] or not ble['host'] or ble['host_error'] or ble['fatal']:
        issue('BLE_NOT_READY', '蓝牙栈/host 初始化或运行有异常；Type 未连接本身不等于蓝牙故障。')
    if not all(power[k] for k in ('adc', 'voltage_valid', 'percent_valid', 'charger_valid')):
        issue('POWER_UNQUALIFIED', '电池/充电检测有未验证字段；0 mV 或 0% 不能当实测。需确认分压量程与 PG/STAT 上拉。')
    if power['charger_valid'] and power['charge'] == 4:
        issue('CHARGER_FAULT', '充电监测已报告故障，先检查充电器状态与 PG/STAT 信号，勿强行执行 OTA。')
    if int(power['ota_block'], 16):
        issue('OTA_POWER_BLOCKED', '当前电源条件阻止 OTA；先核实供电和电源检测，不能跳过更新门禁。')
    return {
        'issues': issues,
        'battery': battery_status(frame),
        'result': 'ISSUES_DETECTED' if issues else 'NO_REPORTED_FAULTS_ONLY',
        'exercise': {
            'microphone': 'FRAMES_OBSERVED_NOT_ACOUSTIC_ACCEPTANCE' if audio['frames'] else 'NOT_EXERCISED',
            'display': 'REFRESH_COUNTER_ONLY' if display['rendered'] else 'NOT_EXERCISED',
            'bleLink': 'CONNECTED_AT_SNAPSHOT_ONLY' if ble['linked'] else 'NOT_CONNECTED',
            'speaker': 'INITIALIZED_NOT_ACOUSTIC_ACCEPTANCE' if audio['speaker_ready'] else 'NOT_READY',
        },
    }


def collect(port, seconds, listen_only, on_data, tail_seconds=0.0):
    if not 0.0 <= tail_seconds <= 2.0:
        raise ValueError('Diagnostic tail must be between 0 and 2 seconds')
    import serial  # Optional for offline parsing; only needed for explicit UART use.
    connection = serial.Serial(port=None, baudrate=115200, bytesize=8, parity='N', stopbits=1,
                               timeout=0.15, write_timeout=1, rtscts=False, dsrdtr=False, xonxoff=False)
    connection.dtr = False
    connection.rts = False
    connection.port = port
    try:
        connection.open()
        if not listen_only:
            connection.reset_input_buffer()
            if connection.write(b'?') != 1:
                raise RuntimeError('query write incomplete')
            connection.flush()
        deadline = time.monotonic() + seconds
        frame_tail_deadline = None
        raw = bytearray()
        while time.monotonic() < deadline:
            chunk = connection.read(min(max(connection.in_waiting, 1), 4096))
            if chunk:
                raw.extend(chunk)
                on_data(chunk)  # Persist even if later read fails.
                if len(raw) > MAX_CAPTURE:
                    raise RuntimeError('capture exceeds 4 MiB bound')
                if b'DIAG1 END ' in chunk or b'DIAG1 END ' in raw[-512:]:
                    frames, _ = parse_frames(bytes(raw))
                    if any(listen_only or f['reason'] == 'query' for f in frames):
                        if tail_seconds == 0.0:
                            break
                        if frame_tail_deadline is None:
                            # PANEL2/PANEL3 follow DIAG1 END. Retain their
                            # cached driver counts without issuing another query.
                            frame_tail_deadline = time.monotonic() + tail_seconds
            if frame_tail_deadline is not None and time.monotonic() >= frame_tail_deadline:
                break
    finally:
        connection.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--port', help='Explicit target UART, for example COM7; no automatic selection')
    source.add_argument('--input-log', type=Path, help='Offline parsing; never opens serial ports')
    parser.add_argument('--output', type=Path, required=True, help='New or empty local output directory')
    parser.add_argument('--seconds', type=float, default=15)
    parser.add_argument('--tail-seconds', type=float, default=0.6,
                        help='Keep cached UI/PANEL diagnostics after DIAG1 END (0..2 seconds)')
    parser.add_argument('--listen-only', action='store_true', help='Do not even send the read-only ? query')
    parser.add_argument('--expected-uid')
    parser.add_argument('--expected-fw', default='00010128', help='Expected firmware version, eight hex digits')
    parser.add_argument('--expected-ui', type=int, default=58, help='Expected mounted UI generation; current matched builds use 85')
    args = parser.parse_args(argv)
    if not 1 <= args.seconds <= 300:
        parser.error('--seconds must be between 1 and 300')
    if not 0 <= args.tail_seconds <= 2:
        parser.error('--tail-seconds must be between 0 and 2')
    if args.expected_uid and not re.fullmatch('[0-9a-fA-F]{24}', args.expected_uid):
        parser.error('--expected-uid must be 24 hex digits')
    if not re.fullmatch('[0-9a-fA-F]{8}', args.expected_fw):
        parser.error('--expected-fw must be eight hex digits')
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error('output directory must be new or empty; preserve previous evidence')
    out.mkdir(parents=True, exist_ok=True)
    log = out / 'uart.log'
    report = {'schema': 'companion.wba.uart-diagnostic.v1', 'result': 'NO_COMPLETE_SNAPSHOT',
              'source': 'OFFLINE_LOG' if args.input_log else 'UART_QUERY' if not args.listen_only else 'UART_LISTEN',
              'hardwareAcceptance': 'NOT_EVALUATED', 'fullChainAcceptance': 'NOT_RUN',
              'flashed': False, 'resetsRequested': False, 'errors': []}
    try:
        with log.open('wb') as handle:
            def persist(chunk):
                handle.write(chunk)
                handle.flush()
            if args.input_log:
                if args.input_log.stat().st_size > MAX_CAPTURE:
                    raise ValueError('input log exceeds 4 MiB bound')
                persist(args.input_log.read_bytes())
            else:
                collect(args.port, args.seconds, args.listen_only, persist, tail_seconds=args.tail_seconds)
        frames, rejected = parse_frames(log.read_bytes())
        report['rejectedFrames'] = rejected
        eligible = [f for f in frames if args.input_log or args.listen_only or f['reason'] == 'query']
        if eligible:
            report['snapshot'] = eligible[-1]
            screen_enabled=b'SCREEN1 enabled=0' not in log.read_bytes()
            report.update(diagnose(eligible[-1], expected_fw=args.expected_fw.lower(), expected_ui=args.expected_ui, expected_uid=args.expected_uid, screen_enabled=screen_enabled))
            report['screenEnabled']=screen_enabled
            if rejected:
                report['result'] = 'PARTIAL_OR_CORRUPT_CAPTURE'
                report['errors'].append('采集中存在截断或损坏的 DIAG1；已保存完整快照供定位，但不能把旧的完整快照当成最新正常状态，请在空闲时重新查询。')
        else:
            report['errors'].append('未收到完整 DIAG1：确认已安装支持诊断的固件、1.8V UART 电平、交叉 RX/TX、共地与 115200 8N1。录音/播放期间会延后输出，可在结束后查询；无响应不能直接判定坏板。')
        boot_text = log.read_bytes().decode('ascii', errors='replace')
        fatal_phases = re.findall(r'(?m)^BOOT1 FATAL phase=([a-zA-Z0-9_]+)(?:\s|$)', boot_text)
        report['bootPreBleObserved'] = bool(re.search(r'(?m)^BOOT1 phase=pre_ble(?:\s|$)', boot_text))
        if fatal_phases:
            report['result'] = 'BOOT_FAILURE_REPORTED'
            report.setdefault('issues', []).append({'code': 'FATAL_REPORTED',
                'message': '固件记录了致命错误，阶段：' + ', '.join(fatal_phases) + '。保留日志，必要时用 SWD 定位；该标记不等于完整诊断快照。'})
        elif not eligible and report['bootPreBleObserved']:
            report['errors'].append('已见 pre_ble 启动标记，但未见随后完整状态；检查 BLE 初始化阶段。串口日志无法定位所有 IRQ/HardFault，需要时使用 SWD。')
    except Exception as exc:
        report['result'] = 'COLLECTION_ERROR'
        report['errors'].append(str(exc))
    report['rawLogSha256'] = hashlib.sha256(log.read_bytes()).hexdigest()
    (out / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = [report['result'], '只读状态诊断，不构成实板或整机验收。']
    lines += [i['code'] + ': ' + i['message'] for i in report.get('issues', [])]
    lines += report['errors']
    (out / 'summary.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'result': report['result'], 'report': str(out / 'result.json')}, ensure_ascii=True))
    return 0 if report['result'] == 'NO_REPORTED_FAULTS_ONLY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
