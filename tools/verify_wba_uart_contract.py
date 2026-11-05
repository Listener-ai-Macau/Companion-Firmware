#!/usr/bin/env python3
"""Verify actual native C formatter output with the shipped Python decoder."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
from diagnose_wba_uart import parse_frames, diagnose, battery_status

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-result',type=Path,default=ROOT / '.cache/host-tests/wba-diagnostic-console/result.json')
    parser.add_argument('--output',type=Path,default=ROOT / '.cache/wba-uart-diagnostics/contract')
    parser.add_argument('--battery-only',action='store_true')
    args=parser.parse_args()
    native = args.native_result
    evidence = json.loads(native.read_text(encoding='utf-8-sig'))
    if evidence['result'] != 'PASS_PREHARDWARE_SOFTWARE_ONLY':
        raise RuntimeError('Native console test did not pass')
    sources = dict(evidence['source_sha256'])
    for name, expected in sources.items():
        if sha(ROOT / name) != expected:
            raise RuntimeError('Stale native formatter evidence: ' + name)
    for name in ['tools/diagnose_wba_uart.py', 'tools/verify_wba_uart_contract.py']:
        sources[name] = sha(ROOT / name)
    raw = ('HOST_NATIVE_C_FIXTURE_NOT_HARDWARE\r\n' + '\r\n'.join(evidence['tests']) + '\r\n').encode('ascii')
    frames, rejected = parse_frames(raw)
    if len(frames) != 1 or rejected:
        raise RuntimeError('C/Python wire contract mismatch: ' + repr(rejected))
    # Values below are deliberately set by the native C fault fixture.
    frame = frames[0]
    if (frame['sections']['ID']['uid'] != '67452301efcdab8940302010' or
            frame['sections']['CORE']['faults'] != '00000089' or
            frame['sections']['AUDIO']['frames'] != 600):
        raise RuntimeError('Native UID byte order / fault / counter values changed')
    report = diagnose(frame, expected_uid='67452301efcdab8940302010')
    expected = {'PRODUCT_FAULTS', 'WATCHDOG_RESET', 'STACK_FAULT', 'DISPLAY_NOT_READY',
                'STORAGE_NOT_READY', 'MICROPHONE_OR_DEADLINE', 'BLE_NOT_READY', 'OTA_POWER_BLOCKED'}
    if not args.battery_only and {i['code'] for i in report['issues']} != expected:
        raise RuntimeError('Fault fixture was not diagnosed exactly: ' + repr(report['issues']))
    value=battery_status(frame)
    assert value['cellMillivolts']==3890 and value['socPercent']==76
    assert value['supplyMillivolts'] is None  # Fixture contains an expired VREF.
    fixture=copy.deepcopy(frame);power=fixture['sections']['POWER'];adc=fixture['sections']['BATTERY']
    power.update(voltage_valid=0,percent_valid=0)
    adc.update(vref_age_ms=10)
    value=battery_status(fixture)
    assert value['cellState']=='DIVIDER_UNVERIFIED' and value['cellMillivolts'] is None and value['socPercent'] is None
    assert value['supplyMillivolts']==1800
    adc['divider_verified']=1;assert battery_status(fixture)['cellState']=='DIVIDER_RANGE'
    adc.update(divider_safe=1,saturated=1);assert battery_status(fixture)['cellState']=='SATURATED'
    adc.update(saturated=0,adc_error=5);assert battery_status(fixture)['cellState']=='ADC_ERROR'
    adc.update(adc_error=0);assert battery_status(fixture)['cellState']=='STALE'
    adc.update(sample_age_ms=10);assert battery_status(fixture)['cellState']=='RAW_ONLY'
    del fixture['sections']['BATTERY']
    assert battery_status(fixture)['cellState']=='DETAIL_UNAVAILABLE'
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    (out / 'native-formatter.log').write_bytes(raw)
    result = {'result': 'PASS_HOST_WIRE_CONTRACT_ONLY', 'hardwareAcceptance': 'NOT_RUN',
              'fullChainAcceptance': 'NOT_RUN', 'source_sha256': sources,
              'native_test_receipt_sha256': sha(native), 'snapshot': frame, 'diagnosis': report,
              'log_sha256': sha(out / 'native-formatter.log')}
    (out / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(result['result'])
    print('PASS_BATTERY_WIRE: native C fields decode, separate cell/supply, unverified/range/saturation/error/stale/raw states, old optional section compatible')


if __name__ == '__main__':
    main()
