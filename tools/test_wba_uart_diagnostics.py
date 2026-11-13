#!/usr/bin/env python3
"""Host-only fault injection for the read-only UART collector."""
import contextlib
import io
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import diagnose_wba_uart as diag


def fixture(reason='query', seq=7):
    values = {name: {key: '0' for key in fields.split()} for name, fields in diag.FIELDS.items()}
    for name, fields in diag.HEX.items():
        for key, digits in fields.items():
            if key in values[name]:
                values[name][key] = '0' * digits
    values['ID'].update(fw='00010128', build='20261004', board='57424155', uid='0123456789abcdef01234567', ui='58')
    values['DISPLAY'].update(bound='1', assets='1', driver='1')
    values['STORAGE'].update(jedec='ef4018', size='16777216', layout='1', recording_ready='1', rec_state='1')
    values['AUDIO'].update(mic_init='1', speaker_ready='1')
    values['BLE'].update(compiled='1', init='1', host='1', connection='ffff')
    values['POWER'].update(adc='1', voltage_valid='1', percent_valid='1', charger_valid='1', mv='4000', pct='80')
    lines = [f'DIAG1 BEGIN seq={seq} reason={reason}']
    for section, fields in values.items():
        lines.append(f'DIAG1 {section} seq={seq} ' + ' '.join(f'{k}={v}' for k, v in fields.items()))
    lines.append(f'DIAG1 END seq={seq}')
    return ('\r\n'.join(lines) + '\r\n').encode('ascii')


class UartDiagnostics(unittest.TestCase):
    def test_display_disabled_frame_may_omit_only_display(self):
        raw = b'\r\n'.join(line for line in fixture().splitlines() if not line.startswith(b'DIAG1 DISPLAY')) + b'\r\n'
        self.assertFalse(diag.parse_frames(raw)[0])
        frames, errors = diag.parse_frames(raw, screen_enabled=False)
        self.assertFalse(errors)
        self.assertEqual(len(frames), 1)
        self.assertNotIn('DISPLAY_NOT_READY', {i['code'] for i in diag.diagnose(frames[0], screen_enabled=False)['issues']})
        self.assertIn('DISPLAY_NOT_READY', {i['code'] for i in diag.diagnose(frames[0])['issues']})
        for section in ('ID', 'CORE', 'STORAGE', 'AUDIO', 'BLE', 'POWER'):
            broken = b'\r\n'.join(line for line in raw.splitlines() if not line.startswith(('DIAG1 '+section+' ').encode())) + b'\r\n'
            self.assertFalse(diag.parse_frames(broken, screen_enabled=False)[0])

    def test_disabled_screen_is_reported_without_requiring_a_panel(self):
        raw=fixture().replace(b'bound=1',b'bound=0').replace(b'driver=1',b'driver=0')
        frame=diag.parse_frames(raw)[0][0]
        self.assertIn('DISPLAY_NOT_READY',{i['code'] for i in diag.diagnose(frame)['issues']})
        self.assertNotIn('DISPLAY_NOT_READY',{i['code'] for i in diag.diagnose(frame,screen_enabled=False)['issues']})
    def test_nor_suspend_fields_are_optional_but_atomic(self):
        old = fixture()
        self.assertEqual(len(diag.parse_frames(old)[0]), 1)
        fields = b' suspend_ok=1 erase_active=1 erase_sus=1 sus_ms=2 resume_ms=2 bfp_dw=16 dw12=330001ec dw13=757a757a'
        raw = old.replace(b'committed=0\r\n', b'committed=0' + fields + b'\r\n')
        frames, errors = diag.parse_frames(raw)
        self.assertFalse(errors)
        self.assertEqual(frames[0]['sections']['STORAGE']['dw13'], '757a757a')
        self.assertEqual(frames[0]['sections']['STORAGE']['suspend_ok'], 1)
        for broken in (raw.replace(b' erase_sus=1', b''),
                       raw.replace(b' erase_sus=1', b' erase_sus=2'),
                       raw.replace(b' dw12=330001ec', b' dw12=330001eg')):
            self.assertFalse(diag.parse_frames(broken)[0])

    def test_raw_battery_keeps_unknown_cell_and_old_frames(self):
        values = {key: '0' for key in diag.OPTIONAL_FIELDS['BATTERY'].split()}
        values.update(raw_mode='1', input_mv='1500', input_valid='1', saturated='0',
                      sample_age_ms='5', raw='3413', samples='2')
        battery = ('DIAG1 BATTERY seq=7 ' + ' '.join(f'{k}={v}' for k,v in values.items()) + '\r\n').encode('ascii')
        raw = fixture().replace(b'voltage_valid=1',b'voltage_valid=0').replace(b'percent_valid=1',b'percent_valid=0')
        frames, errors = diag.parse_frames(raw.replace(b'DIAG1 END',battery+b'DIAG1 END'))
        self.assertFalse(errors)
        self.assertEqual(frames[0]['sections']['BATTERY']['input_mv'],1500)
        self.assertIn('POWER_UNQUALIFIED',{i['code'] for i in diag.diagnose(frames[0])['issues']})
        saturated = battery.replace(b'input_mv=1500',b'input_mv=0').replace(b'input_valid=1',b'input_valid=0').replace(b'saturated=0',b'saturated=1')
        self.assertEqual(diag.parse_frames(raw.replace(b'DIAG1 END',saturated+b'DIAG1 END'))[0][0]['sections']['BATTERY']['saturated'],1)
        for invalid in (battery.replace(b'input_valid=1',b'input_valid=2'),battery.replace(b'input_mv=1500 ',b'')):
            self.assertFalse(diag.parse_frames(raw.replace(b'DIAG1 END',invalid+b'DIAG1 END'))[0])

    def test_optional_battery_reference_does_not_qualify_external_voltage(self):
        values = {key: '0' for key in diag.OPTIONAL_FIELDS['BATTERY'].split()}
        values.update(vref_raw='2730', vref_cal='1638', vdda_mv='1800',
                      vref_valid='1', vref_age_ms='7', vref_n='1')
        battery = ('DIAG1 BATTERY seq=7 ' + ' '.join(f'{k}={v}' for k, v in values.items()) + '\r\n').encode('ascii')
        raw = fixture().replace(b'voltage_valid=1', b'voltage_valid=0').replace(
            b'percent_valid=1', b'percent_valid=0').replace(b'DIAG1 END', battery + b'DIAG1 END')
        frames, errors = diag.parse_frames(raw)
        self.assertFalse(errors)
        self.assertEqual(frames[0]['sections']['BATTERY']['vdda_mv'], 1800)
        self.assertEqual(frames[0]['sections']['BATTERY']['divider_verified'], 0)
        self.assertIn('POWER_UNQUALIFIED', {i['code'] for i in diag.diagnose(frames[0])['issues']})
        for invalid in (battery.replace(b'vref_valid=1', b'vref_valid=2'),
                        battery.replace(b'vref_cal=1638 ', b''),
                        battery + battery):
            self.assertFalse(diag.parse_frames(fixture().replace(b'DIAG1 END', invalid + b'DIAG1 END'))[0])

    def test_optional_duration_samples_keep_legacy_frames_readable(self):
        values = {key: '0' for key in diag.OPTIONAL_FIELDS['TIMING'].split()}
        values.update(rec_id='7', mic_starts='2', tick_us='1000', min_samples='20',
                      enc_n='15000', enc_valid='1', enc_p95_upper_ms='5',
                      enc_peak_upper_ms='7', pdm_n='30000', pdm_valid='1',
                      pdm_p95_upper_ms='3', pdm_peak_upper_ms='4')
        timing = ('DIAG1 TIMING seq=7 ' + ' '.join(f'{k}={v}' for k, v in values.items()) + '\r\n').encode('ascii')
        raw = fixture().replace(b'DIAG1 END', timing + b'DIAG1 END')
        frames, errors = diag.parse_frames(raw)
        self.assertFalse(errors)
        self.assertEqual(frames[0]['sections']['TIMING']['enc_n'], 15000)
        self.assertEqual(frames[0]['sections']['TIMING']['pdm_peak_upper_ms'], 4)
        self.assertTrue(diag.parse_frames(fixture())[0])
        for invalid in (timing.replace(b'enc_valid=1', b'enc_valid=2'),
                        timing.replace(b'tick_us=1000 ', b'')):
            self.assertFalse(diag.parse_frames(fixture().replace(b'DIAG1 END', invalid + b'DIAG1 END'))[0])

    def test_complete_snapshot_is_not_acceptance_or_exercise(self):
        frames, errors = diag.parse_frames(b'normal log\r\n' + fixture())
        self.assertFalse(errors)
        report = diag.diagnose(frames[0])
        self.assertEqual(report['result'], 'NO_REPORTED_FAULTS_ONLY')
        self.assertEqual(report['exercise']['microphone'], 'NOT_EXERCISED')
        self.assertEqual(report['exercise']['bleLink'], 'NOT_CONNECTED')

    def test_missing_duplicate_mixed_or_corrupt_frames_never_complete(self):
        source = fixture()
        candidates = [source[:source.index(b'DIAG1 END')],
                      source.replace(b'DIAG1 END seq=7', b'DIAG1 END seq=8'),
                      source.replace(b'DIAG1 CORE seq=7', b'DIAG1 CORE seq=8'),
                      source.replace(b'ui=58', b'ui=58 ui=34'),
                      source.replace(b'uid=0123456789abcdef01234567', b'uid=0'),
                      source.replace(b'panel=0', b'panel=2'),
                      source.replace(b'reason=query', b'reason=invalid'),
                      source.replace(b'ui=58', b'ui=-1'),
                      source.replace(b'DIAG1 AUDIO', b'BROKEN AUDIO')]
        id_line = source.splitlines()[1] + b'\r\n'
        candidates.append(source.replace(b'DIAG1 CORE', id_line + b'DIAG1 CORE'))
        for corrupted in candidates:
            with self.subTest(corrupted=corrupted[:60]):
                frames, errors = diag.parse_frames(corrupted)
                self.assertFalse(frames)
                self.assertTrue(errors)

    def test_new_begin_recovers_without_stitching_old_snapshot(self):
        truncated = fixture(seq=6).split(b'DIAG1 AUDIO')[0]
        frames, errors = diag.parse_frames(truncated + fixture(seq=7))
        self.assertEqual([f['seq'] for f in frames], [7])
        self.assertTrue(errors)

    def test_key_faults_and_unknown_power_are_reported(self):
        raw = (fixture().replace(b'faults=00000000', b'faults=00000300').replace(b'panel=0', b'panel=1')
               .replace(b'iwdg_reset=0', b'iwdg_reset=1').replace(b'bound=1', b'bound=0')
               .replace(b'jedec=ef4018', b'jedec=ffffff').replace(b'mic_overflow=0', b'mic_overflow=1')
               .replace(b'host_error=0', b'host_error=7').replace(b'voltage_valid=1', b'voltage_valid=0')
               .replace(b'ota_block=0000', b'ota_block=0001'))
        report = diag.diagnose(diag.parse_frames(raw)[0][0])
        self.assertEqual({i['code'] for i in report['issues']}, {'PRODUCT_FAULTS', 'WATCHDOG_RESET',
                         'DISPLAY_NOT_READY', 'STORAGE_NOT_READY', 'MICROPHONE_OR_DEADLINE',
                         'BLE_NOT_READY', 'POWER_UNQUALIFIED', 'OTA_POWER_BLOCKED'})

    def test_wrong_candidate_and_uid_fail_identity(self):
        frame = diag.parse_frames(fixture().replace(b'ui=58', b'ui=34'))[0][0]
        self.assertEqual({i['code'] for i in diag.diagnose(frame, expected_uid='a' * 24)['issues']},
                         {'IDENTITY_MISMATCH', 'UID_MISMATCH'})

    def test_stack_speaker_and_charger_faults_are_explicit(self):
        raw = (fixture().replace(b'stack_guard=0', b'stack_guard=1')
               .replace(b'speaker_ready=1', b'speaker_ready=0').replace(b'charge=0', b'charge=4'))
        report = diag.diagnose(diag.parse_frames(raw)[0][0])
        self.assertEqual({i['code'] for i in report['issues']}, {'STACK_FAULT', 'SPEAKER_NOT_READY', 'CHARGER_FAULT'})

    def test_offline_cli_preserves_raw_and_has_no_hardware_acceptance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'input.log').write_bytes(fixture())
            with patch.object(diag, 'collect', side_effect=AssertionError('serial must not open')), contextlib.redirect_stdout(io.StringIO()):
                code = diag.main(['--input-log', str(root / 'input.log'), '--output', str(root / 'out')])
            self.assertEqual(code, 0)
            result = json.loads((root / 'out/result.json').read_text(encoding='utf-8'))
            self.assertEqual(result['source'], 'OFFLINE_LOG')
            self.assertEqual(result['hardwareAcceptance'], 'NOT_EVALUATED')
            self.assertEqual((root / 'out/uart.log').read_bytes(), fixture())

    def test_serial_error_preserves_partial_evidence_and_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            def broken(port, seconds, listen_only, persist, tail_seconds=0.6):
                persist(b'DIAG1 BEGIN seq=9 reason=query\r\n')
                raise OSError('disconnected')
            with patch.object(diag, 'collect', side_effect=broken), contextlib.redirect_stdout(io.StringIO()):
                code = diag.main(['--port', 'COM999', '--output', temp])
            self.assertEqual(code, 2)
            report = json.loads((Path(temp) / 'result.json').read_text(encoding='utf-8'))
            self.assertEqual(report['result'], 'COLLECTION_ERROR')
            self.assertTrue((Path(temp) / 'uart.log').stat().st_size)

    def test_old_complete_snapshot_cannot_hide_new_truncated_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'input.log').write_bytes(fixture() + b'DIAG1 BEGIN seq=8 reason=query\r\n')
            with contextlib.redirect_stdout(io.StringIO()):
                code = diag.main(['--input-log', str(root / 'input.log'), '--output', str(root / 'out')])
            self.assertEqual(code, 2)
            report = json.loads((root / 'out/result.json').read_text(encoding='utf-8'))
            self.assertEqual(report['result'], 'PARTIAL_OR_CORRUPT_CAPTURE')

    def test_fatal_boot_marker_is_useful_without_a_complete_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'input.log').write_bytes(b'BOOT1 phase=pre_ble\r\nBOOT1 FATAL phase=ble\r\n')
            with contextlib.redirect_stdout(io.StringIO()):
                code = diag.main(['--input-log', str(root / 'input.log'), '--output', str(root / 'out')])
            self.assertEqual(code, 2)
            report = json.loads((root / 'out/result.json').read_text(encoding='utf-8'))
            self.assertEqual(report['result'], 'BOOT_FAILURE_REPORTED')
            self.assertTrue(report['bootPreBleObserved'])
            self.assertNotIn('snapshot', report)
            self.assertEqual(report['issues'][0]['code'], 'FATAL_REPORTED')

    def test_single_read_only_query_and_listen_mode_do_not_reset_lines(self):
        class FakeSerial:
            def __init__(self, **kwargs):
                self.kwargs, self.writes, self.in_waiting = kwargs, [], 4096
                self.closed = self.opened = False
            def open(self):
                self.opened = True
                self.assertions = (self.port, self.dtr, self.rts)
            def reset_input_buffer(self): pass
            def write(self, value): self.writes.append(value); return len(value)
            def flush(self): pass
            def read(self, size): return fixture()
            def close(self): self.closed = True
        for listen in (False, True):
            instance = FakeSerial()
            with patch.dict(sys.modules, {'serial': types.SimpleNamespace(Serial=lambda **kw: instance)}):
                data = []
                diag.collect('COM_TEST_ONLY', 1, listen, data.append)
            self.assertEqual(instance.assertions, ('COM_TEST_ONLY', False, False))
            self.assertEqual(instance.writes, [] if listen else [b'?'])
            self.assertTrue(instance.closed)
            self.assertEqual(data, [fixture()])


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    output = root / '.cache/wba-uart-diagnostics/tests'
    output.mkdir(parents=True, exist_ok=True)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(UartDiagnostics))
    print(stream.getvalue())
    (output / 'tests.log').write_text(stream.getvalue(), encoding='utf-8')
    (output / 'synthetic-query.log').write_bytes(b'HOST_SYNTHETIC_NOT_HARDWARE\r\n' + fixture())
    sources = ['tools/diagnose_wba_uart.py', 'tools/test_wba_uart_diagnostics.py',
               'platform/stm32wba55_companion_v11/factory/Diagnose-WBA.ps1']
    receipt = {'result': 'PASS_HOST_SIMULATION_ONLY' if result.wasSuccessful() else 'FAIL_HOST_TESTS',
               'tests': result.testsRun, 'hardwareAcceptance': 'NOT_RUN', 'fullChainAcceptance': 'NOT_RUN',
               'sources': {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in sources},
               'files': {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                         for name in ['tests.log', 'synthetic-query.log']}}
    (output / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
