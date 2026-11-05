#!/usr/bin/env python3
"""Bounded, shared-board-aware battery observations and a local read-only panel.

One invocation collects at most one cached UART query. It never uses SWD,
resets the target, starts recording, or controls charging. Voltage-derived
percent and extrapolation are estimates, not current/energy measurements.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import re
import statistics
import time
import uuid

from diagnose_wba_uart import collect, parse_frames

FW = Path(__file__).resolve().parents[1]
ROOT = FW.parent
PROBE = '004400403532510B31333430'
UID = '180010000d50335754363720'
DEFAULT = FW / '.cache/battery-trend-20261011'
EMPTY_MV, FULL_MV = 2850, 4150
MAX_AGE_MS = 15000
MIN_POINTS, MIN_HOURS, MIN_DROP_MV = 8, 2, 30
LEASE_MARKER = 'Companion 电池趋势（battery-trend-b03，'


def now():
    return datetime.now().astimezone()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def read_json(path, default=None):
    return json.loads(path.read_bytes()) if path.exists() else default


@contextmanager
def local_lock(path):
    """Prevent two collectors/config edits; close the actual OS lock on exit."""
    import msvcrt
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def board_text():
    return (ROOT / 'docs/board_operations.md').read_bytes().decode('utf-8-sig')


def current_region(text):
    if '## 当前占用' not in text:
        raise RuntimeError('Shared board ownership section missing')
    return text.split('## 当前占用', 1)[1].split('\n## ', 1)[0]


def update_lease(run, released=False, result=None, evidence=None):
    """Preserve concurrent edits; never clear an unrelated owner's lease."""
    path = ROOT / 'docs/board_operations.md'
    for _ in range(2):
        original = board_text()
        region = current_region(original)
        if not released and '**占用中**' in region:
            return False
        nl = '\r\n' if '\r\n' in original else '\n'
        active = '- **占用中**：' + LEASE_MARKER
        mine = next((line for line in region.splitlines() if LEASE_MARKER in line), None)
        if released and (mine is None or active not in mine or run not in mine):
            raise RuntimeError('Battery collector lease changed; do not overwrite another owner')
        status = '已释放' if released else '占用中'
        action = (f'{result}；实际UART句柄已关闭；一次有界缓存查询，无SWD/停核/复位/刷写/开录/BLE/充电控制。'
                  if released else '仅固定V3对应UART的一次有界电池趋势查询，最多15秒；不触及SWD/复位/录音/BLE。')
        if released and evidence:
            action += ' 证据：' + str(evidence / 'result.json') + '。'
        line = f'- **{status}**：{LEASE_MARKER}{now().isoformat()}，{run}）。{action}'
        if mine:
            updated = original.replace(mine, line, 1)
        else:
            updated = original.replace('## 当前占用', '## 当前占用' + nl + nl + line, 1)
        if board_text() != original:
            continue
        path.write_bytes(updated.encode('utf-8'))
        return True
    raise RuntimeError('Shared board record changed concurrently; skipped UART')


def cached_line(raw, name):
    lines = re.findall(r'^' + re.escape(name) + r' (.*)$', raw.decode('ascii', errors='replace'), re.M)
    return dict(re.findall(r'(\w+)=([^\s]+)', lines[-1])) if lines else {}


def sample_from_frame(frame, raw, timestamp, config):
    s = frame['sections']
    identity, power, adc = s['ID'], s['POWER'], s.get('BATTERY', {})
    if identity['uid'] != UID:
        raise RuntimeError('UART target UID mismatch; no battery value accepted')
    cell = None
    reason = 'NO_VALID_CELL_SAMPLE'
    qualified = bool(power['voltage_valid'])
    if qualified:
        if 2800 <= power['mv'] <= 4350:
            cell, reason = power['mv'], 'QUALIFIED_VOLTAGE'
    elif adc.get('raw_mode'):
        cfg = s.get('POWERCFG', {})
        nominal = cfg.get('top_ohm') == 100000 and cfg.get('bottom_ohm') == 68000
        fresh = (adc.get('sample_age_ms', 0xffffffff) < MAX_AGE_MS and
                 adc.get('vref_age_ms', 0xffffffff) < MAX_AGE_MS)
        if (nominal and power['adc'] and adc.get('samples', 0) > 0 and fresh and
                adc.get('input_valid') and adc.get('vref_valid') and
                not adc.get('saturated') and not adc.get('adc_error') and adc.get('vdda_mv', 0) >= 1782):
            estimate = (adc['input_mv'] * 168 + 34) // 68
            if 2800 <= estimate <= 4350:
                cell, reason = estimate, 'NOMINAL_DIVIDER_ESTIMATE'
        elif not fresh:
            reason = 'STALE_SAMPLE'
        elif adc.get('saturated'):
            reason = 'SATURATED'
        elif not nominal:
            reason = 'UNSUPPORTED_DIVIDER'
        elif adc.get('adc_error'):
            reason = 'ADC_ERROR'
        else:
            reason = 'ADC_PENDING_OR_REFERENCE_UNAVAILABLE'
    percent = None if cell is None else max(0, min(100, (max(0, cell - EMPTY_MV) * 100 + 650) // 1300))
    audio, display, ble = s['AUDIO'], s['DISPLAY'], s['BLE']
    ui, panel, transfer = cached_line(raw, 'UI1'), cached_line(raw, 'PANEL2'), cached_line(raw, 'XFER1')
    display_fault = bool(display['error'] or display['failed'] and not display['rendered'])
    mode = ('recording_connected' if ble['linked'] else 'recording_offline') if audio['mic_run'] else (
        'idle_display_error' if display_fault else 'connected' if ble['linked'] else
        'screen_sleep' if ui.get('surface') == '2' else 'pet_or_menu')
    charger = (['UNKNOWN', 'CHARGING', 'POWERED_IDLE', 'DISCHARGING', 'FAULT'][power['charge']]
               if power['charger_valid'] and power['charge'] < 5 else 'UNKNOWN')
    age = adc.get('sample_age_ms')
    return dict(schema='companion.battery.observation.v1', atLocal=timestamp.isoformat(),
                epoch=timestamp.timestamp(), uid=UID, firmware=identity['fw'], ui=identity['ui'],
                uptimeMs=identity['uptime_ms'], querySequence=frame['seq'],
                cellEstimateMv=cell, percentEstimate=percent, voltageState=reason,
                voltageQualified=qualified, percentQualified=bool(power['percent_valid']),
                sampleAgeMs=age, batterySamples=adc.get('samples'), rawAdc=adc.get('raw'),
                inputMv=adc.get('input_mv'), vddaMv=adc.get('vdda_mv'),
                adcError=adc.get('adc_error'), mode=mode, chargerState=charger,
                powerSource=config.get('powerSource', 'unknown'), contextId=config.get('contextId'),
                debuggerAttached=True, displayFault=display_fault, display=display,
                cachedUi=ui, cachedPanel=panel, cachedTransfer=transfer,
                audioFrames=audio['frames'], micStarts=s.get('TIMING', {}).get('mic_starts'),
                chargingMeasured=False, currentMa=None, powerMw=None, temperatureC=None)


def observations(folder):
    path = folder / 'observations.jsonl'
    if not path.exists():
        return []
    # A dashboard GET can overlap the append. Only complete newline records count.
    text = path.read_text(encoding='utf-8')
    complete = text[:text.rfind('\n') + 1]
    return [json.loads(line) for line in complete.splitlines() if line.strip()]


def same_runtime(a, b):
    elapsed = b['epoch'] - a['epoch']
    uptime = (b['uptimeMs'] - a['uptimeMs']) / 1000
    return (0 < elapsed <= 2700 and uptime > 0 and abs(elapsed - uptime) < 30 and
            all(a[k] == b[k] for k in ('uid', 'firmware', 'ui')))


def compatible(a, b):
    return (same_runtime(a, b) and
            all(a[k] == b[k] for k in ('uid', 'firmware', 'ui', 'contextId', 'mode', 'powerSource')) and
            a['chargerState'] not in ('CHARGING', 'POWERED_IDLE', 'FAULT') and
            b['chargerState'] not in ('CHARGING', 'POWERED_IDLE', 'FAULT') and
            not (a['mode'] in ('idle_display_error', 'screen_sleep', 'pet_or_menu', 'connected') and
                 (a['audioFrames'] != b['audioFrames'] or a['micStarts'] != b['micStarts'])) and
            (a['mode'].startswith('recording') or
             int(b['cachedTransfer'].get('notify', 0)) == int(a['cachedTransfer'].get('notify', 0))))


def fit_trend(points):
    result = dict(state='COLLECTING', points=len(points), elapsedHours=0,
                  dropMv=None, slopeMvPerHour=None, remainingHoursEstimate=None,
                  fullRangeHoursEstimate=None, qualifiedEndurance=False,
                  model='2850..4150mV linear voltage proxy; intermittent observations',
                  minimumPoints=MIN_POINTS, minimumHours=MIN_HOURS, minimumDropMv=MIN_DROP_MV)
    if not points:
        result['reason'] = '尚无有效电池读数'
        return result
    latest = points[-1]
    segment = [latest]
    for previous in reversed(points[-96:-1]):
        if (previous['cellEstimateMv'] is None or previous['segmentId'] != segment[0]['segmentId'] or
                not compatible(previous, segment[0])):
            break
        segment.insert(0, previous)
    result.update(points=len(segment), mode=latest['mode'],
                  elapsedHours=(latest['epoch'] - segment[0]['epoch']) / 3600)
    if latest['cellEstimateMv'] is None:
        result['reason'] = '最近一次ADC读数无效，保留历史，不记为0%'
        return result
    if latest['powerSource'] != 'battery':
        result['state'], result['reason'] = 'EXTERNAL_POWER_OR_UNKNOWN', '仅纯电池供电段用于放电趋势；当前供电来源不是已确认电池'
        return result
    if latest['chargerState'] in ('CHARGING', 'POWERED_IDLE', 'FAULT'):
        result['state'], result['reason'] = 'CHARGE_STATE_CONFLICT', '板端充电状态与放电条件冲突，不计算续航'
        return result
    hours = result['elapsedHours']
    drop = segment[0]['cellEstimateMv'] - latest['cellEstimateMv']
    result['dropMv'] = drop
    if len(segment) < MIN_POINTS or hours < MIN_HOURS:
        result['reason'] = '正在积累：同一运行段至少8个读数、2小时且下降至少30mV，才给粗估'
        return result
    if drop < MIN_DROP_MV:
        result['state'], result['reason'] = 'DROP_TOO_SMALL', '下降不足30mV或电压回升；不外推成无限续航'
        return result
    xs = [(p['epoch'] - segment[0]['epoch']) / 3600 for p in segment]
    ys = [p['cellEstimateMv'] for p in segment]
    pairs = [(ys[j] - ys[i]) / (xs[j] - xs[i]) for i in range(len(xs)) for j in range(i + 1, len(xs))
             if xs[j] - xs[i] >= 0.25]
    slope = statistics.median(pairs)
    intercept = statistics.median(y - slope * x for x, y in zip(xs, ys))
    residual = statistics.median(abs(y - (intercept + slope * x)) for x, y in zip(xs, ys))
    half = len(xs) // 2
    rates = [(ys[0] - ys[half]) / (xs[half] - xs[0]),
             (ys[half] - ys[-1]) / (xs[-1] - xs[half])]
    if slope >= 0 or min(rates) <= 0 or max(rates) / min(rates) > 3 or residual > max(12, drop / 4):
        result['state'], result['reason'] = 'UNSTABLE_TREND', '电压趋势不稳定，可能有负载变化或回弹；暂不给续航数字'
        return result
    result.update(state='PROVISIONAL_VOLTAGE_EXTRAPOLATION', slopeMvPerHour=round(slope, 2),
                  remainingHoursEstimate=round(max(0, latest['cellEstimateMv'] - EMPTY_MV) / -slope, 1),
                  fullRangeHoursEstimate=round(1300 / -slope, 1), residualMv=round(residual, 2),
                  reason='按当前电压下降速度粗略外推。调试器连接、间隔行为和非线性曲线均影响结果，非整机续航实测')
    return result


def report(folder):
    config = read_json(folder / 'config.json', {})
    points = observations(folder)
    valid = [p for p in points if p['cellEstimateMv'] is not None]
    latest = valid[-1] if valid else None
    attempt = read_json(folder / 'last-attempt.json', {})
    # A missed observation is a segment boundary, not a fictitious discharge.
    fit_points = points
    if attempt.get('result') not in ('OBSERVED', 'DUPLICATE_CACHED_SAMPLE'):
        fit_points = []
    trend = fit_trend(fit_points)
    age_seconds = max(0, time.time() - latest['epoch']) if latest else None
    if latest and age_seconds >= 1200:
        trend.update(state='LAST_READING_OLD', remainingHoursEstimate=None,
                     fullRangeHoursEstimate=None, reason='最近有效记录已超过20分钟；只展示历史电量，等待下一次采样')
    if config.get('monitoringStatus') == 'CANCELED_BY_OWNER':
        trend.update(state='OBSERVATION_STOPPED', remainingHoursEstimate=None,
                     fullRangeHoursEstimate=None,
                     reason='Owner已取消定时观察；保留历史电压记录，续航仍未知')
    value = dict(schema='companion.battery.panel.v1', generatedAtLocal=now().isoformat(),
                 config=config, latest=latest, lastAttempt=attempt, observationCount=len(points),
                 validObservationCount=len(valid), lastReadingAgeSeconds=age_seconds,
                 recentObservation=bool(latest and age_seconds < 1200 and attempt.get('result') == 'OBSERVED'),
                 trend=trend, observations=points[-288:],
                 measuredCurrentMa=None, measuredPowerMw=None, measuredTemperatureC=None,
                 physicalEnduranceQualified=False,
                 notes=['百分比为2850..4150mV临时线性估算，非实测容量。',
                        'USB调试器仍接着；UART查询本身会扰动功耗，不能当脱离调试器的最终续航。',
                        '供电中断、重启、版本或模式改变会分段；失联不记为0%也不自动重启。',
                        '刷新失败时的数据不代表宠物正常动画时的功耗。'])
    write_json(folder / 'report.json', value)
    return value


def once(folder, seconds):
    folder.mkdir(parents=True, exist_ok=True)
    with local_lock(folder / 'collector.lock'):
        if read_json(folder / 'config.json', {}).get('monitoringStatus') == 'CANCELED_BY_OWNER':
            report(folder)
            print(json.dumps(dict(result='OBSERVATION_STOPPED', uartOpened=False,
                                  handlesClosed=True), ensure_ascii=False))
            return
        run = 'sample-' + now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
        evidence = folder / run
        evidence.mkdir()
        attempt = dict(startedAtLocal=now().isoformat(), result='SKIPPED_BUSY',
                       evidence=str(evidence), uartOpened=False, handlesClosed=True,
                       rawLogSha256=None, flashed=False, reset=False)
        leased = update_lease(run)
        if leased:
            try:
                from serial.tools import list_ports
                ports = [p.device for p in list_ports.comports() if p.serial_number == PROBE]
                if len(ports) != 1:
                    raise RuntimeError('Fixed V3 UART unavailable or ambiguous; no other port selected')
                raw_path = evidence / 'uart.log'
                with raw_path.open('wb') as handle:
                    def persist(chunk):
                        handle.write(chunk)
                        handle.flush()
                    attempt['uartOpened'] = True
                    collect(ports[0], seconds, False, persist, tail_seconds=0.6)
                raw = raw_path.read_bytes()
                attempt['rawLogSha256'] = hashlib.sha256(raw).hexdigest()
                frames, rejected = parse_frames(raw)
                eligible = [f for f in frames if f['reason'] == 'query']
                attempt['rejectedFrames'] = rejected
                if rejected or not eligible:
                    attempt['result'] = 'NO_COMPLETE_NORMAL_REPLY'
                else:
                    timestamp = now()
                    config = read_json(folder / 'config.json', {})
                    point = sample_from_frame(eligible[-1], raw, timestamp, config)
                    point['evidence'] = str(raw_path)
                    prior_attempt = read_json(folder / 'last-attempt.json', {})
                    old = observations(folder)
                    same_boot = bool(old and same_runtime(old[-1], point))
                    same_segment = bool(old and compatible(old[-1], point))
                    same_counter = bool(old and point['batterySamples'] == old[-1]['batterySamples'])
                    if same_boot and same_counter and point['cellEstimateMv'] is not None:
                        attempt['result'] = 'DUPLICATE_CACHED_SAMPLE'
                    else:
                        point['segmentId'] = (old[-1]['segmentId'] if same_segment and
                                              prior_attempt.get('result') in ('OBSERVED', 'DUPLICATE_CACHED_SAMPLE')
                                              else uuid.uuid4().hex)
                        with (folder / 'observations.jsonl').open('a', encoding='utf-8') as handle:
                            handle.write(json.dumps(point, ensure_ascii=False) + '\n')
                        write_json(evidence / 'observation.json', point)
                        attempt['result'] = 'OBSERVED' if point['cellEstimateMv'] is not None else point['voltageState']
                        attempt['sample'] = point
            except Exception as exc:
                attempt['result'], attempt['error'] = 'UNAVAILABLE', str(exc)
            finally:
                # collect closes its Serial object in its own finally, before release.
                attempt['handlesClosed'] = True
                update_lease(run, released=True, result=attempt['result'], evidence=evidence)
        attempt['completedAtLocal'] = now().isoformat()
        write_json(evidence / 'result.json', attempt)
        write_json(folder / 'last-attempt.json', attempt)
        value = report(folder)
        print(json.dumps(dict(result=attempt['result'], latest=value['latest'], trend=value['trend']), ensure_ascii=False))


def serve(folder, port):
    """Serve only the panel and its report. Viewing it never samples hardware."""
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            route = self.path.split('?', 1)[0]
            if route in ('/', '/battery/'):
                body, mime = (FW / 'tools/battery_monitor.html').read_bytes(), 'text/html; charset=utf-8'
            elif route == '/report.json':
                body, mime = json.dumps(report(folder), ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'READY http://127.0.0.1:{port}/battery/ no_hardware_on_view=1', flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, default=DEFAULT)
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--port', type=int, default=8892)
    parser.add_argument('--seconds', type=float, default=12)
    parser.add_argument('--power-source', choices=['battery', 'usb', 'unknown'])
    parser.add_argument('--capacity-mah', type=float)
    parser.add_argument('--stop-observation', action='store_true',
                        help='Stop scheduled collection and preserve its historical readings')
    args = parser.parse_args()
    if not 1 <= args.seconds <= 15:
        parser.error('One bounded observation must be 1..15 seconds')
    if args.capacity_mah is not None and not (math.isfinite(args.capacity_mah) and 1 <= args.capacity_mah <= 10000):
        parser.error('Capacity must be a confirmed value between 1 and 10000mAh')
    folder = args.folder.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    if args.stop_observation and (args.once or args.serve):
        parser.error('Stopping observation does not open UART or start a service')
    if args.power_source or args.capacity_mah is not None or args.stop_observation:
        with local_lock(folder / 'collector.lock'):
            config = read_json(folder / 'config.json', {})
            if args.power_source:
                config.update(powerSource=args.power_source, contextId=uuid.uuid4().hex,
                              contextConfirmedAtLocal=now().isoformat(), contextSource='Owner reported')
            if args.capacity_mah is not None:
                config['capacityMah'] = args.capacity_mah
            if args.stop_observation:
                config.update(monitoringStatus='CANCELED_BY_OWNER',
                              observationStoppedAtLocal=now().isoformat())
            write_json(folder / 'config.json', config)
    if args.stop_observation:
        value=report(folder)
        print(json.dumps(dict(result='OBSERVATION_STOPPED',
                             observationCount=value['observationCount'], uartOpened=False),
                         ensure_ascii=False))
        return
    if args.once:
        once(folder, args.seconds)
    if args.serve:
        serve(folder, args.port)
    elif not args.once:
        print(json.dumps(report(folder), ensure_ascii=False))


if __name__ == '__main__':
    main()
