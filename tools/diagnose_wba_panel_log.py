#!/usr/bin/env python3
"""Explain saved WBA panel telemetry without opening any device or resetting it.

Firmware completion counters and register readback are separate evidence. In
particular, invalid FF readback is not proof of a broken write path or panel.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import statistics

from diagnose_wba_uart import MAX_CAPTURE, parse_frames

POINT_NAMES = {0: 'RESET_READY', 1: 'MODE1_READY', 2: 'MODE2_READY',
               3: 'PARTIAL_RAM_READY'}

def fields(line: str) -> dict[str, str]:
    return dict(re.findall(r'\b([a-z_][a-z_0-9]*)=([^\s]+)', line))


def analyze(path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) > MAX_CAPTURE:
        raise ValueError(f'Log exceeds {MAX_CAPTURE} bytes: {path}')
    frames, rejected = parse_frames(raw)
    lines = raw.decode('ascii', errors='replace').splitlines()
    ready, timeouts, feedback, releases, ram, driver_counts, driver_timing, power_checks = [], [], [], [], [], [], [], []
    stuck_start = []
    start_probes, start_recovery, ram_details, debug_pins, activation_gates = [], [], [], [], []
    recovery_guards, passive_activations, panel_gpio, original_start_misses = [], [], [], []
    readback_ff = False
    for number, line in enumerate(lines, 1):
        row = fields(line)
        if line.startswith(('PANEL1 ', 'PANEL5 ', 'PANEL6 ')):
            readback_ff |= row.get('status', '').upper() == 'FF,FF,FF'
        if line.startswith('PANEL6 point='):
            ready.append({'line': number, 'pointName': POINT_NAMES.get(int(row['point']), 'UNKNOWN'), **row})
        elif line.startswith('PANEL6 ram_probe '):
            ram.append({'line': number, **row})
        elif line.startswith('PANEL4 timeout '):
            timeouts.append({'line': number, **row})
        elif line.startswith('PANEL5 '):
            feedback.append({'line': number, **row})
        elif line.startswith('PANEL7 imu_release '):
            releases.append({'line': number, **row})
        elif line.startswith('PANEL2 '):
            driver_counts.append({'line': number, **row})
        elif line.startswith('PANEL3 '):
            driver_timing.append({'line': number, **row})
        elif line.startswith('PANEL8 mode2_power '):
            power_checks.append({'line': number, **row})
        elif line.startswith('PANEL9 stuck_start '):
            stuck_start.append({'line': number, **row})
        elif line.startswith('PANEL10 start_probe '):
            start_probes.append({'line': number, **row})
        elif line.startswith('PANEL11 start_recovery '):
            start_recovery.append({'line': number, **row})
        elif line.startswith('PANEL12 ram_detail '):
            ram_details.append({'line': number, **row})
        elif line.startswith('SWD1 '):
            debug_pins.append({'line': number, **row})
        elif line.startswith('PANEL13 activation_gate '):
            activation_gates.append({'line': number, **row})
        elif line.startswith('PANEL14 recovery_full '):
            recovery_guards.append({'line': number, **row})
        elif line.startswith('PANEL15 activation '):
            passive_activations.append({'line': number, **row})
        elif line.startswith('PANEL16 gpio '):
            panel_gpio.append({'line': number, **row})
        elif line.startswith('PANEL18 recovery '):
            # This belongs to the original start miss, whereas PANEL15 can
            # already describe the later recovery activation. Keep both.
            original_start_misses.append({'line': number, **row})

    sessions = []
    previous = None
    for frame in frames:
        section = frame['sections']
        identity = section['ID']
        key = tuple(identity[k] for k in ('fw', 'uid', 'ui'))
        if previous is None or key != previous[0] or identity['uptime_ms'] < previous[1]:
            sessions.append({'firmware': identity['fw'], 'uid': identity['uid'],
                             'ui': identity['ui'], 'frames': []})
        sessions[-1]['frames'].append(frame)
        previous = key, identity['uptime_ms']

    conclusions = []
    latest = frames[-1]['sections'] if frames else None
    unique_session = len(sessions) == 1 and not rejected
    max_rendered = max((f['sections']['DISPLAY']['rendered'] for f in frames), default=0)
    latest_driver = driver_counts[-1] if driver_counts else None
    # recording is already a subset of partial in this driver. No-op renderer
    # commits are deliberately absent from these three transaction counters.
    actual_refreshes = (sum(int(latest_driver[key]) for key in ('full', 'partial', 'fast'))
                        if latest_driver is not None else None)
    if not frames:
        conclusions.append({'code': 'NO_COMPLETE_SNAPSHOT',
                            'message': '没有完整状态快照；不能确定固件身份和刷新计数。'})
    elif not unique_session:
        conclusions.append({'code': 'MIXED_OR_INCOMPLETE_CAPTURE',
                            'message': '日志含多次启动或不完整快照，不能跨启动合并计数来证明恢复。'})
    elif latest['DISPLAY']['failed'] or latest['DISPLAY'].get('busy_timeouts', 0) or timeouts:
        conclusions.append({'code': 'REFRESH_FAILURE_REPORTED',
                            'message': '固件快照或后续超时事件记录了实际刷新失败；当前尚未确认恢复。'})
        if latest['DISPLAY']['rendered'] == 0 or actual_refreshes == 0:
            conclusions.append({'code': 'NO_COMPLETED_REFRESH',
                                'message': '本次启动尚无成功完成的刷新事务。'})
    elif actual_refreshes:
        conclusions.append({'code': 'COMPLETED_TRANSACTIONS_ONLY',
                            'message': '存在完成的刷新事务计数；实屏内容、残影和视觉效果仍需观察。'})
    elif latest['DISPLAY']['rendered']:
        conclusions.append({'code': 'RENDER_COMMITS_WITHOUT_DRIVER_COUNTS',
                            'message': 'rendered包含相同画面的提交，不能单独证明实际刷新次数；需要PANEL2驱动计数。'})
    else:
        conclusions.append({'code': 'NOT_YET_EXERCISED',
                            'message': '快照内尚无完成或失败的刷新，观测时窗不足以判断。'})

    if (not activation_gates and any(100 <= int(row.get('wait', '0')) < 5000 for row in timeouts)) or any(
            row.get('first_stage') == '12' and row.get('first_busy') == '0' and
            100 <= int(row.get('first_wait_ms', '0')) < 5000 for row in driver_counts):
        conclusions.append({'code': 'VISIBLE_START_NOT_OBSERVED',
                            'message': '可见激活后100ms内未观察到驱动要求的BUSY启动。不能据此确认实际电压或屏幕是否收到写命令。'})
    if any(int(row.get('timeouts', '0')) for row in activation_gates):
        conclusions.append({'code': 'ACTIVATION_BLOCKED_BY_UNQUALIFIED_STATUS',
                            'message': '发送激活前100ms内没有取得连续20ms有效内部就绪状态；已退出该事务，未将无效读回或等待本身算作刷新完成。'})
    if ready and not any(row.get('valid') == '1' for row in ready):
        conclusions.append({'code': 'STARTUP_READBACK_UNQUALIFIED',
                            'message': '复位/初始化检查没有取得有效控制器状态；读通路尚未得到资格确认。'})
    if any(row.get('transport_confirmed') == '1' for row in ram):
        conclusions.append({'code': 'RAM_TRANSPORT_CONFIRMED_AT_CHECKPOINT',
                            'message': '检查点的两平面RAM挑战通过，只证明当时通信，不能替代可见刷新完成。'})
    if readback_ff and unique_session and actual_refreshes is not None and actual_refreshes > 0:
        conclusions.append({'code': 'FF_COEXISTS_WITH_COMPLETED_REFRESH',
                            'message': '同次启动既有无效FF读回，也有PANEL2确认的刷新事务。FF不能单独作为写通路失败或硬件损坏的证据。'})
    if latest_driver is not None:
        conclusions.append({'code': 'DRIVER_COUNTS_AVAILABLE',
                            'message': f'最后一份PANEL2快照记录完成{actual_refreshes}次刷新；后续PANEL7可能记录更多事务，rendered最大{max_rendered}不能混用。'})
    for release in releases:
        target = int(release.get('target', '1'))
        count = int(release.get('refreshes', '0'))
        if target > 1 and release.get('panel_status') == '4':
            conclusions.append({'code': 'FAILURE_BEFORE_IMU_START',
                                'message': '延后IMU的隔离阶段已发生屏幕失败，随后才启动IMU；这次失败不能归因为先前IMU传输。'})
        elif target > 1 and count >= target:
            conclusions.append({'code': 'ISOLATED_REFRESHES_COMPLETED',
                                'message': f'IMU启动前完成了{count}次实际刷新，可继续比较恢复IMU后的表现。'})
    if feedback:
        conclusions.append({'code': 'EDGE_SAMPLES_NOT_PULSE_MEASUREMENTS',
                            'message': 'BUSY边沿记录是采样区间内的合并标志，不是脉冲宽度；总线活动时出现边沿不能单独证明短路或有效刷新。'})
    for power in power_checks:
        if int(power.get('checks', '0')) == 0:
            continue
        if power.get('sensor_qualified') != '1':
            code, message = 'POWER_SENSING_UNQUALIFIED', '供电检测缺少有效读回或所需BUSY观察，不能把默认零标志当电压正常。'
        elif power.get('vci_low') == '1':
            code, message = 'CONTROLLER_VCI_BELOW_2300MV', '芯片VCI检测报告低于2.3V，检测仅对应该检查点。'
        elif power.get('hv_not_ready') == '1':
            code, message = 'CONTROLLER_HV_NOT_READY', '芯片高压检测报告升压未就绪，检测仅对应该检查点。'
        else:
            code, message = 'CONTROLLER_POWER_FLAGS_NORMAL_AT_CHECKPOINT', '该检查点VCI低压及高压未就绪标志均未置位，不能替代瞬时电压测量或实屏验收。'
        if not any(c['code'] == code for c in conclusions):
            conclusions.append({'code': code, 'message': message})
    for probe in stuck_start:
        if probe.get('read_valid') != '1':
            code, message = 'STUCK_STATUS_READ_UNQUALIFIED', '卡BUSY后的有限状态读取无效，仍无法区分控制器内部忙与反馈线异常。'
        elif probe.get('raw_restored') != '1' or probe.get('raw_read_before') != '7' or probe.get('raw_read_after') != '7':
            code, message = 'STUCK_PROBE_CHANGED_OR_SAMPLED_TRANSITION', '有限诊断期间BUSY发生变化；不能把读后的状态追认为读前状态，也不能据此绕过刷新资格。'
        elif probe.get('ic_busy') == '1':
            code, message = 'CONTROLLER_BUSY_REPORTED_DURING_STUCK_PROBE', '三次一致状态读回报告控制器内部BUSY，外部反馈也持续为高；内部为何未结束仍未确定。'
        else:
            code, message = 'BUSY_FEEDBACK_DISAGREES_WITH_STATUS', '三次一致状态读回报告内部空闲，但反馈持续为高；反馈通路或读回可信度需要继续排查，不能单独锁定电平转换芯片。'
        conclusions.append({'code': code, 'message': message})

    if any(row.get('retry_qualified') == '1' for row in start_probes):
        conclusions.append({'code': 'MISSED_START_WITH_READY_AND_MATCHING_RAM_SAMPLES',
                            'message': '未观察到启动后，控制器报告空闲，选取的新旧RAM样本与本事务一致；仅允许一次有资格的重发，不能把样本当整帧验证。'})
    if any(int(row.get('current_mismatch', '0')) or int(row.get('old_mismatch', '0')) for row in start_probes):
        conclusions.append({'code': 'RAM_SAMPLES_DISAGREE_AT_MISSED_START',
                            'message': '未启动后的RAM样本与本事务不符，因此拒绝直接重发激活；数据写入、地址设置或诊断读回仍需区分。'})
    if start_recovery and int(start_recovery[-1].get('completed', '0')):
        conclusions.append({'code': 'QUALIFIED_START_RECOVERY_COMPLETED',
                            'message': '有资格重发后的事务已通过可见BUSY起落及后续RAM同步；未启动现象仍单独计数，不表示根因已消除。'})
    if any(row.get('repair') == '1' for row in ram_details):
        conclusions.append({'code': 'STABLE_RAM_MISMATCH_WINDOW_REPAIR_REQUESTED',
                            'message': '同址双读稳定但样本不符，已请求一次局部双平面重写；还须重写后的样本复核及真实BUSY完成，不能只按请求计恢复。'})
    if any(int(row.get('unstable', '0')) for row in ram_details):
        conclusions.append({'code': 'UNSTABLE_RAM_READBACK_RECOVERY_DENIED',
                            'message': '同址重复RAM读回不稳定，禁止用该读回授权重写或激活重试。'})
    pin_fields = ('pa13_mode', 'pa13_af', 'pa14_mode', 'pa14_af')
    pin_samples = [row for row in debug_pins
                   if all(row.get(key, '').isdigit() for key in pin_fields)]
    if any((row['pa13_mode'], row['pa13_af'], row['pa14_mode'], row['pa14_af']) !=
           ('2', '0', '2', '0') for row in pin_samples):
        conclusions.append({'code': 'SWD_PIN_MUX_NOT_AF0_OBSERVED',
                            'message': '串口采样发现PA13/PA14至少一个不在SWD的AF0模式；需按时间定位引脚配置来源，不能先归责接线。'})
    elif pin_samples:
        conclusions.append({'code': 'SWD_PIN_AF0_OBSERVED_AT_CHECKPOINTS',
                            'message': '串口采样点PA13/PA14均为AF0；不能据此证明采样间状态或调试线的电平、接触和信号质量。'})

    timing_samples = []
    for row in passive_activations:
        high = int(row.get('high_samples', '0'))
        if not high:
            continue
        first, last = int(row['first_high_ms']), int(row['last_high_ms'])
        # These are discrete foreground samples, never a scope measurement
        # of continuous high pulse width or proof of the physical waveform.
        timing_samples.append({'activation': int(row['n']), 'outcome': row['outcome'],
            'requestedDecision': int(row['decision']),
            'sampledHighSpanMs': (last - first) & 0xffffffff,
            'highSamples': high, 'pollSamples': int(row['polls']),
            'edgeObservationAvailable': row.get('edges_valid') == '1' if 'edges_valid' in row else None,
            'edgeFlags': int(row['edges']) if 'edges' in row else None,
            'maximumPollGapMs': int(row['poll_gap_ms']) if 'poll_gap_ms' in row else None,
            'visibleCompletedMs': int(row['visible_ms']) if 'visible_ms' in row else None,
            'postSyncMs': int(row['post_ms']) if 'post_ms' in row else None})
    missing_starts = [row for row in passive_activations
                      if row.get('outcome') == 'failed' and row.get('high_samples') == '0']
    if missing_starts:
        conclusions.append({'code': 'PASSIVE_ACTIVATIONS_WITHOUT_HIGH_SAMPLE',
                            'message': f'被动记录中{len(missing_starts)}次失败激活没有采到任何BUSY高电平；不能将这些事件描述为BUSY持续拉高。'})
    if passive_activations:
        conclusions.append({'code': 'PASSIVE_TIMING_IS_SAMPLED',
                            'message': 'PANEL15首次/末次高电平时间和样本数来自既有前台轮询；跨度不是连续脉宽，decision只是驱动请求模式。'})
    edge_without_level = []
    observation_gaps = []
    for source, rows in (('PANEL15', passive_activations), ('PANEL18_ORIGINAL', original_start_misses)):
        for row in rows:
            if row.get('high_samples') != '0':
                continue
            # Nonzero flags are positive evidence of a latched edge. Zero
            # flags cannot prove an absent electrical pulse or a failed write.
            if row.get('edges_valid') == '0':
                continue
            if int(row.get('edges', '0')) & 3:
                edge_without_level.append({'source': source, **row})
            if int(row.get('poll_gap_ms', '0')) >= 100:
                observation_gaps.append({'source': source, **row})
    if original_start_misses:
        conclusions.append({'code': 'ORIGINAL_START_MISSES_RETAINED',
                            'message': f'保留{len(original_start_misses)}条恢复前未观察到启动的原记录；恢复完成不能抹掉这些启动缺失，需分别看原窗口与恢复激活。'})
    if edge_without_level:
        conclusions.append({'code': 'BUSY_EDGE_WITHOUT_HIGH_LEVEL_SAMPLE',
                            'message': f'{len(edge_without_level)}条记录有硬件边沿但前台高电平样本为0；可能漏采或存在短脉冲，边沿不等于有效刷新完成，也不能单独归责硬件。'})
    if observation_gaps:
        conclusions.append({'code': 'BUSY_OBSERVATION_GAP_AT_START_DEADLINE',
                            'message': f'{len(observation_gaps)}条零高样本记录有至少100ms轮询间隙；需定位该次前台阻塞，不能将采样空窗解释成整段BUSY持续为低。'})
    full_spans = [row['sampledHighSpanMs'] for row in timing_samples
                  if row['outcome'] == 'completed' and row['requestedDecision'] == 0]
    local_spans = [row['sampledHighSpanMs'] for row in timing_samples
                   if row['outcome'] == 'completed' and row['requestedDecision'] in (1, 2)]
    if unique_session and full_spans and local_spans:
        baseline = statistics.median(full_spans)
        if baseline >= 1000 and min(local_spans) >= baseline * 0.8:
            conclusions.append({'code': 'LOCAL_TIMING_NEAR_FULL_UNCONFIRMED_WAVEFORM',
                                'message': '完成的局刷请求耗时接近本次全刷；驱动计数不能单独证明屏幕实际使用了快速局刷波形，仍需核对模式和通信。'})
    recovery_intervals = []
    if unique_session:
        deadlines = {int(row['started']): int(row['next_ms'])
                     for row in recovery_guards if int(row['started']) > 0}
        for n, deadline in sorted(deadlines.items()):
            if n - 1 in deadlines:
                recovery_intervals.append((deadline - deadlines[n - 1]) & 0xffffffff)
        minimum = max((int(row['min_ms']) for row in recovery_guards), default=0)
        if recovery_intervals and minimum:
            guarded = all(interval >= minimum for interval in recovery_intervals)
            conclusions.append({'code': 'RECOVERY_FULL_INTERVAL_OBSERVED' if guarded else
                                'RECOVERY_FULL_INTERVAL_TOO_SHORT',
                                'message': f'本次记录的故障恢复全刷启动间隔为{recovery_intervals}ms，限制为{minimum}ms；限频观察不能当局刷恢复。'})
    gpio_fields = tuple(f'{pin}_{suffix}' for pin in ('dc', 'mosi', 'cs', 'sck')
                        for suffix in ('mode', 'speed'))
    slew_samples = [row for row in panel_gpio if row.get('low_slew') == '1' and
                    all(row.get(key, '').isdigit() for key in gpio_fields)]
    if slew_samples:
        expected = all(all(row[pin+'_mode'] == '1' and row[pin+'_speed'] == '0'
                           for pin in ('dc', 'mosi', 'cs', 'sck')) for row in slew_samples)
        conclusions.append({'code': 'LOW_SLEW_GPIO_OBSERVED' if expected else
                            'LOW_SLEW_GPIO_CONFIGURATION_DIFFERS',
                            'message': '已采到四根屏幕引脚的实际模式和输出速度；这些寄存器值不能证明电平转换后波形或排线接触正常。'})

    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(raw).hexdigest(),
            'bytes': len(raw), 'snapshotCount': len(frames), 'rejectedSnapshots': rejected,
            'sessionCount': len(sessions),
            'identities': [{k: v for k, v in s.items() if k != 'frames'} for s in sessions],
            'latestSnapshot': latest, 'maximumRenderedCounter': max_rendered,
            'driverCounts': driver_counts, 'driverTiming': driver_timing,
            'actualRefreshTransactions': actual_refreshes,
            'readyCheckpoints': ready, 'activationTimeouts': timeouts,
            'busyObservations': feedback, 'ramChallenges': ram, 'imuReleases': releases,
            'powerChecks': power_checks, 'stuckStartProbes': stuck_start,
            'activationStartProbes': start_probes, 'activationStartRecovery': start_recovery,
            'activationRamDetails': ram_details,
            'activationStatusGates': activation_gates,
            'passiveActivations': passive_activations, 'passiveTimingSamples': timing_samples,
            'passiveMissingStarts': missing_starts, 'panelGpioObservations': panel_gpio,
            'originalStartMisses': original_start_misses,
            'edgesWithoutHighLevelSample': edge_without_level,
            'busyObservationGaps': observation_gaps,
            'recoveryFullGuardObservations': recovery_guards,
            'recoveryFullIntervalsMs': recovery_intervals,
            'debugPinObservations': debug_pins,
            'invalidFfReadbackObserved': readback_ff,
            'ffWithCompletedRefresh': readback_ff and unique_session and actual_refreshes is not None and actual_refreshes > 0,
            'conclusions': conclusions}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    analyses = [analyze(path) for path in args.log]
    result = {'schema': 'companion.panel.saved-log-diagnosis.v1',
              'result': 'LOG_ANALYSIS_ONLY', 'hardwareAccess': False,
              'hardwareRootCause': 'UNRESOLVED', 'physicalAppearance': 'NOT_OBSERVED',
              'readbackAloneProvesHardwareFailure': False,
              'historicalFfWithCompletedRefresh': any(a['ffWithCompletedRefresh'] for a in analyses),
              'analyses': analyses}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for analysis in analyses:
        print(analysis['path'])
        for conclusion in analysis['conclusions']:
            print(f"  {conclusion['code']}: {conclusion['message']}")
    print('Saved:', args.output.resolve())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
