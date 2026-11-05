"""Fault injection for the actual provisioning orchestrator, with simulated SWD."""
from pathlib import Path
import json
import struct
import tempfile
import unittest
import subprocess
from unittest.mock import patch
import provision_wba_v11 as p
from verify_wba_spi_nor_adapter import find_vsdevcmd

class FakeProgrammer:
    def __init__(self, output, geometry=None):
        self.geometry = geometry or p.for_mcu()
        self.flash_kib = self.geometry.flash_kib
        self.output = output
        self.internal = bytearray(b'\xff' * self.geometry.flash_bytes)
        self.nor = bytearray(b'\xff' * p.NOR_BYTES)
        self.id = struct.pack('<I', 0x10000492)
        self.uid = bytes(range(1, 13))
        self.options = struct.pack('<I', 0x100aa)
        self.events, self.reset_done = [], False
        self.fail = None

    def read(self, address, size, name, external=False):
        registers = {0xE0044000: self.id, 0x0BF907A0: struct.pack('<H', self.flash_kib), 0x40022040: self.options, 0x0BF90700: self.uid}
        data = registers.get(address)
        if data is None:
            source, base = (self.nor, p.NOR_BASE) if external else (self.internal, p.INTERNAL_BASE)
            if address < base or address - base + size > len(source):
                raise RuntimeError('read outside simulated chip capacity')
            data = bytes(source[address - base:address - base + size])
        if self.fail == 'ui_readback' and name == 'verified-ui.bin':
            data = bytes([data[0] ^ 1]) + data[1:]
        if self.fail == 'nvm_changed' and name == 'after-internal.bin':
            offset = self.geometry.nvm_offset
            data = data[:offset] + bytes([0]) + data[offset + 1:]
        (self.output / name).write_bytes(data)
        return data

    def write(self, path, address, external=False):
        data = path.read_bytes()
        self.events.append('ui_write' if external else 'internal_write')
        target = self.nor if external else self.internal
        if self.fail == 'interrupted' and external:
            target[:4096] = data[:4096]
            raise RuntimeError('simulated power loss')
        if self.fail == 'internal_interrupted' and not external:
            target[:64] = data[:64]
            raise RuntimeError('simulated internal power loss')
        target[:len(data)] = data

    def reset(self):
        self.reset_done = True
        self.events.append('reset')

class ProvisionTests(unittest.TestCase):
    mcu = 'STM32WBA55CGU6'

    def setUp(self):
        self.geometry = p.for_mcu(self.mcu)
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.pkg = self.root / 'package'; self.pkg.mkdir()
        (self.pkg / 'resource-ota').mkdir()
        internal = bytearray(b'\xff' * 0x8100)
        struct.pack_into('<II', internal, 0, 0x20020000, 0x08000041)
        struct.pack_into('<II', internal, 0x8000, 0x20020000, 0x08008041)
        self.desired = bytes(internal)
        self.ui = bytes([0x5a]) * p.UI_BYTES
        (self.pkg / 'companion-v11-initial-boot-and-app.bin').write_bytes(internal)
        (self.pkg / 'resource-ota/ui-partition.bin').write_bytes(self.ui)
        self.manifest = {'schema': 'companion.wba.v11.prehardware.delivery.v1', 'mcu': self.mcu,
            'internal_flash_geometry': self.geometry.receipt(),
            'board': 'Companion V1.1 2026-09-19', 'initial_combined_load_address': '0x08000000', 'load_address': '0x08008000',
            'initial_combined_sha256': p.sha(internal), 'bin_sha256': p.sha(internal[0x8000:]),
            'ui_resource_profile': {'uiPartitionBytes': p.UI_BYTES, 'uiPartitionSha256': p.sha(self.ui)},
            'files': {'companion-v11-initial-boot-and-app.bin': p.sha(internal), 'resource-ota/ui-partition.bin': p.sha(self.ui)}}
        p.write_json(self.pkg / 'manifest.json', self.manifest)
        self.package = p.Package(self.pkg)
        self.out = self.root / 'first'; self.out.mkdir()
        self.fake = FakeProgrammer(self.out, self.geometry)

    def tearDown(self):
        self.temp.cleanup()

    def install(self, resume=None):
        return p.install(self.package, self.fake, self.fake.output, resume)

    def test_layout_three_bank_geometry_and_legacy_install_are_explicit(self):
        self.ui = bytes([0x5a]) * (912 * 1024)
        (self.pkg / 'resource-ota/ui-partition.bin').write_bytes(self.ui)
        self.manifest['ui_resource_profile'] = {
            'uiPartitionBytes': len(self.ui), 'uiPartitionSha256': p.sha(self.ui)}
        self.manifest['files']['resource-ota/ui-partition.bin'] = p.sha(self.ui)
        self.manifest['flash_geometry'] = p.resource_geometry(len(self.ui))
        p.write_json(self.pkg / 'manifest.json', self.manifest)
        package = p.Package(self.pkg)
        self.assertEqual(package.flash_geometry['dynamicBytes'], p.NOR_BYTES-len(self.ui))
        with self.assertRaisesRegex(ValueError, 'Layout3 requires'):
            p.install(package, self.fake, self.out)
        self.assertEqual(self.fake.events, [])
        self.assertEqual(list(self.out.iterdir()), [])
        self.manifest['flash_geometry']['dynamicBase'] += 4096
        p.write_json(self.pkg / 'manifest.json', self.manifest)
        with self.assertRaisesRegex(ValueError, 'geometry differs'):
            p.Package(self.pkg)

    def test_blank_board_programs_resources_before_firmware_and_verifies(self):
        result = self.install()
        self.assertEqual(self.fake.events, ['ui_write', 'internal_write', 'reset'])
        self.assertEqual(result['result'], 'PASS_INSTALL_READBACK_ONLY')
        self.assertTrue(result['protected_regions_unchanged'])
        self.assertEqual(result['fullChainAcceptance'], 'NOT_RUN')

    def test_existing_recording_refuses_all_writes(self):
        self.fake.nor[p.UI_BYTES + 51] = 0
        with self.assertRaisesRegex(RuntimeError, 'existing data preserved'): self.install()
        self.assertEqual(self.fake.events, [])

    def test_old_internal_image_refuses_all_writes(self):
        self.fake.internal[0] = 0
        with self.assertRaisesRegex(RuntimeError, 'existing data preserved'): self.install()
        self.assertEqual(self.fake.events, [])

    def test_bad_readback_prevents_firmware_write_and_reset(self):
        self.fake.fail = 'ui_readback'
        with self.assertRaisesRegex(RuntimeError, 'UI readback'): self.install()
        self.assertEqual(self.fake.events, ['ui_write'])
        self.assertEqual(json.loads((self.out / 'result.json').read_text())['result'], 'FAIL_INSTALL')

    def test_protected_nvm_change_prevents_start(self):
        self.fake.fail = 'nvm_changed'
        with self.assertRaisesRegex(RuntimeError, 'protected region'): self.install()
        self.assertFalse(self.fake.reset_done)

    def interrupted(self):
        self.fake.fail = 'interrupted'
        with self.assertRaisesRegex(RuntimeError, 'power loss'): self.install()
        self.fake.fail = None
        self.fake.output = self.root / 'second'; self.fake.output.mkdir()
        self.fake.events.clear()

    def test_interrupted_resource_install_resumes_same_uid_package(self):
        self.interrupted()
        result = self.install(self.out)
        self.assertEqual(result['result'], 'PASS_INSTALL_READBACK_ONLY')
        self.assertEqual(self.fake.events, ['ui_write', 'internal_write', 'reset'])

    def test_resume_rejects_different_uid(self):
        self.interrupted(); self.fake.uid = bytes(range(2, 14))
        with self.assertRaisesRegex(RuntimeError, 'original blank board'): self.install(self.out)
        self.assertEqual(self.fake.events, [])

    def test_resume_rejects_new_recording_or_nvm(self):
        self.interrupted(); self.fake.internal[self.geometry.nvm_offset] = 0
        with self.assertRaisesRegex(RuntimeError, 'new data'): self.install(self.out)
        self.assertEqual(self.fake.events, [])

    def test_resume_rejects_incompatible_bytes_in_writable_ui(self):
        self.interrupted(); self.fake.nor[31] = 0
        with self.assertRaisesRegex(RuntimeError, 'incompatible data'): self.install(self.out)
        self.assertEqual(self.fake.events, [])

    def test_resume_rejects_internal_write_during_ui_phase(self):
        self.interrupted(); self.fake.internal[0] = self.desired[0]
        with self.assertRaisesRegex(RuntimeError, 'UI-only phase'): self.install(self.out)
        self.assertEqual(self.fake.events, [])

    def test_resume_accepts_interrupted_internal_write_only_after_verified_ui(self):
        self.fake.fail = 'internal_interrupted'
        with self.assertRaisesRegex(RuntimeError, 'internal power loss'): self.install()
        self.assertEqual(json.loads((self.out / 'checkpoint.json').read_text())['phase'], 'firmware_write_pending')
        self.fake.fail = None
        self.fake.output = self.root / 'second'; self.fake.output.mkdir()
        self.fake.events.clear()
        self.install(self.out)
        self.assertEqual(self.fake.events, ['internal_write', 'reset'])

    def test_backup_flush_failure_prevents_writes(self):
        with patch.object(p.os, 'fsync', side_effect=OSError('disk flush failed')):
            with self.assertRaisesRegex(OSError, 'disk flush failed'): self.install()
        self.assertEqual(self.fake.events, [])

    def test_write_phase_commit_failure_prevents_programming(self):
        original_write = p.write_json
        commits = []
        def write(path, value):
            if path.name == 'checkpoint.json':
                commits.append(value['phase'])
                if value['phase'] == 'ui_write_pending': raise OSError('checkpoint flush failed')
            original_write(path, value)
        with patch.object(p, 'write_json', side_effect=write):
            with self.assertRaisesRegex(OSError, 'checkpoint flush failed'): self.install()
        self.assertEqual(commits, ['prepared', 'ui_write_pending'])
        self.assertEqual(self.fake.events, [])

    def test_loader_requires_matching_st_parse_evidence(self):
        legacy_cg = p.for_mcu('STM32WBA55CGU6')
        directory = self.root / 'loader'; directory.mkdir()
        binary = b'loader'
        (directory / 'test.stldr').write_bytes(binary)
        p.write_json(directory / 'result.json', {'schema': 'companion.wba.factory-loader.v1', 'result': 'PASS_BUILD_ONLY',
            'loader': 'test.stldr', 'loader_sha256': p.sha(binary), 'read_base': p.NOR_BASE,
            'read_bytes': p.NOR_BYTES, 'write_bytes': p.UI_BYTES, 'mass_erase': 'REFUSED'})
        with self.assertRaises(FileNotFoundError): p.validate_loader(directory, legacy_cg)
        p.write_json(directory / 'st-parse-result.json', {'result': 'PASS_ST_OFFLINE_LOADER_PARSE_ONLY', 'loader_sha256': 'wrong'})
        with self.assertRaisesRegex(ValueError, 'parse evidence'): p.validate_loader(directory, legacy_cg)
        p.write_json(directory / 'st-parse-result.json', {'result': 'PASS_ST_OFFLINE_LOADER_PARSE_ONLY', 'loader_sha256': p.sha(binary)})
        self.assertEqual(p.validate_loader(directory, legacy_cg).name, 'test.stldr')
        with self.assertRaisesRegex(ValueError, 'Legacy factory loader'):
            p.validate_loader(directory)
        ce = p.for_mcu('STM32WBA55CEU6')
        cg = p.for_mcu('STM32WBA55CGU6')
        with self.assertRaisesRegex(ValueError, 'Legacy factory loader'):
            p.validate_loader(directory, ce)
        for selected, wrong in ((ce, cg), (cg, ce)):
            receipt = json.loads((directory / 'result.json').read_text())
            receipt.update(mcu=selected.mcu, internal_flash_geometry=selected.receipt())
            p.write_json(directory / 'result.json', receipt)
            self.assertEqual(p.validate_loader(directory, selected).name, 'test.stldr')
            with self.assertRaisesRegex(ValueError, 'MCU capacity'):
                p.validate_loader(directory, wrong)
        receipt['internal_flash_geometry']['flash_bytes'] -= 8192
        p.write_json(directory / 'result.json', receipt)
        with self.assertRaisesRegex(ValueError, 'geometry identity'):
            p.validate_loader(directory, cg)

    def test_verified_reinstall_preserves_recordings_and_bonds(self):
        self.fake.internal[:len(self.desired)] = self.desired
        self.fake.nor[:p.UI_BYTES] = self.ui
        self.fake.nor[p.UI_BYTES + 7] = 0x19; self.fake.internal[self.geometry.nvm_offset] = 0x29
        result = self.install()
        self.assertEqual(result['result'], 'ALREADY_INSTALLED_READBACK_VERIFIED')
        self.assertEqual(self.fake.events, ['reset'])
        self.assertEqual(self.fake.nor[p.UI_BYTES + 7], 0x19)
        self.assertEqual(self.fake.internal[self.geometry.nvm_offset], 0x29)

    def test_wrong_chip_or_security_configuration_is_rejected(self):
        self.fake.id = struct.pack('<I', 0x495)
        with self.assertRaisesRegex(ValueError, 'Wrong MCU'): self.install()
        self.fake.id = struct.pack('<I', 0x492)
        for options in (0x800100aa, 0x100bb, 0xaa):
            self.fake.options = struct.pack('<I', options)
            with self.assertRaisesRegex(ValueError, 'option bytes'): self.install()
        self.assertEqual(self.fake.events, [])

    def test_package_tampering_and_old_layout_rejected(self):
        (self.pkg / 'resource-ota/ui-partition.bin').write_bytes(b'broken')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'): p.Package(self.pkg)
        self.manifest['load_address'] = '0x08007000'
        p.write_json(self.pkg / 'manifest.json', self.manifest)
        with self.assertRaisesRegex(ValueError, 'package/layout'): p.Package(self.pkg)

    def test_loader_cannot_escape_directory(self):
        with self.assertRaisesRegex(ValueError, 'escapes'): p.member(self.pkg, '../evil.stldr')

    def test_programmer_timeout_and_error_have_no_success(self):
        programmer = p.Programmer(Path('fake.exe'), 'ABC123', Path('loader.stldr'), self.out)
        with patch.object(p.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'Error: write failed', '')):
            with self.assertRaisesRegex(RuntimeError, 'Programmer failed'): programmer.write(self.package.ui_path, p.NOR_BASE, True)
        with patch.object(p.subprocess, 'run', side_effect=subprocess.TimeoutExpired('fake', 180)):
            with self.assertRaisesRegex(RuntimeError, 'timed out'): programmer.reset()

    def test_faster_swd_is_explicit_and_external_deadline_is_bounded(self):
        programmer = p.Programmer(Path('fake.exe'), 'ABC123', Path('loader.stldr'), self.out, frequency_khz=8000)
        with patch.object(p.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'ok', '')) as run:
            programmer.call(['-u', hex(p.NOR_BASE), str(p.NOR_BYTES), 'backup.bin'], external=True)
            self.assertIn('freq=8000', run.call_args.args[0])
            self.assertEqual(run.call_args.kwargs['timeout'], 900)
            programmer.call(['-u', hex(p.INTERNAL_BASE), '4', 'internal.bin'])
            self.assertEqual(run.call_args.kwargs['timeout'], 180)
        self.assertEqual(programmer.connection_identity()['frequency_khz'], 8000)
        with self.assertRaisesRegex(ValueError, 'SWD frequency'):
            p.Programmer(Path('fake.exe'), 'ABC123', Path('loader.stldr'), self.out, frequency_khz=0)
        with patch.object(p.subprocess, 'run', side_effect=subprocess.TimeoutExpired('fake',900,output=b'Read progress: 25%',stderr=b'stopped')):
            with self.assertRaisesRegex(RuntimeError,'timed out'):
                programmer.call(['-u',hex(p.NOR_BASE),'4','partial.bin'],external=True)
        self.assertIn('Read progress: 25%stopped',(self.out/'003-programmer.log').read_text())

    def test_validated_bytes_survive_source_replacement(self):
        # Concurrent resource build cannot swap bytes after Package validation.
        self.package.ui_path.write_bytes(b'wrong')
        self.package.internal_path.write_bytes(b'wrong')
        self.install()
        self.assertEqual(self.fake.nor[:p.UI_BYTES], self.ui)
        self.assertEqual(self.fake.internal[:len(self.desired)], self.desired)

    def test_programmer_commands_select_probe_and_never_mass_erase(self):
        programmer = p.Programmer(Path('fake.exe'), 'ABC123', Path('loader.stldr'), self.out)
        with patch.object(p.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'ok', '')) as run:
            programmer.write(self.package.ui_path, p.NOR_BASE, True)
            command = run.call_args.args[0]
            self.assertIn('sn=ABC123', command)
            self.assertIn('-el', command)
            self.assertNotIn('-v', command)
            self.assertNotIn('-e', command)
            self.assertNotIn('-ob', command)
            programmer.write(self.package.internal_path, p.INTERNAL_BASE)
            self.assertIn('-v', run.call_args.args[0])

    def test_six_pin_default_never_requests_a_missing_nrst_line(self):
        programmer = p.Programmer(Path('fake.exe'), 'ABC123', Path('loader.stldr'), self.out)
        with patch.object(p.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'ok', '')) as run:
            programmer.write(self.package.internal_path, p.INTERNAL_BASE)
            programmer.reset()
            for call in run.call_args_list:
                command = call.args[0]
                self.assertIn('mode=NORMAL', command)
                self.assertIn('reset=SWrst', command)
                self.assertNotIn('mode=UR', command)
                self.assertNotIn('reset=HWrst', command)
                self.assertNotIn('-hardRst', command)
            self.assertEqual(run.call_args.args[0][-2:], ['-rst', '-run'])
            self.assertFalse(programmer.connection_identity()['nrst_connected'])

    def test_hardware_reset_requires_explicit_separate_nrst_connection(self):
        programmer = p.Programmer(Path('fake.exe'), 'ABC123', Path('loader.stldr'), self.out,
                                  nrst_connected=True)
        with patch.object(p.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'ok', '')) as run:
            programmer.reset()
            command = run.call_args.args[0]
            self.assertIn('mode=UR', command)
            self.assertIn('reset=HWrst', command)
            self.assertEqual(command[-2:], ['-hardRst', '-run'])
            self.assertTrue(programmer.connection_identity()['nrst_connected'])

    def test_opposite_capacity_refused_before_backup_or_write(self):
        self.fake.flash_kib = 512 if self.geometry.flash_kib == 1024 else 1024
        with self.assertRaisesRegex(ValueError, 'family/capacity'):
            self.install()
        self.assertEqual(self.fake.events, [])
        self.assertFalse((self.out / 'before-internal.bin').exists())
        self.assertFalse((self.out / 'before-nor.bin').exists())

    def test_geometry_tampering_refuses_package(self):
        self.manifest['internal_flash_geometry']['nvm_offset'] -= 8192
        p.write_json(self.pkg / 'manifest.json', self.manifest)
        with self.assertRaisesRegex(ValueError, 'geometry identity'):
            p.Package(self.pkg)

    def test_capacity_bound_to_backup_readback(self):
        result = self.install()
        self.assertEqual((self.out / 'before-internal.bin').stat().st_size, self.geometry.flash_bytes)
        self.assertEqual((self.out / 'after-internal.bin').stat().st_size, self.geometry.flash_bytes)
        self.assertEqual(result['internal_flash_geometry'], self.geometry.receipt())

    def test_missing_geometry_is_legacy_cg_only(self):
        del self.manifest['internal_flash_geometry']
        p.write_json(self.pkg / 'manifest.json', self.manifest)
        if self.geometry.flash_kib == 1024:
            self.assertEqual(p.Package(self.pkg).geometry, self.geometry)
        else:
            with self.assertRaisesRegex(ValueError, 'geometry identity'):
                p.Package(self.pkg)

    def test_default_identity_guard_accepts_ce_and_rejects_implicit_cg(self):
        self.assertEqual(p.validate_identity(self.fake.id, struct.pack('<H', 512), self.fake.options, self.fake.uid), self.fake.uid.hex())
        with self.assertRaisesRegex(ValueError, 'family/capacity'):
            p.validate_identity(self.fake.id, struct.pack('<H', 1024), self.fake.options, self.fake.uid)


class CEProvisionTests(ProvisionTests):
    mcu = 'STM32WBA55CEU6'


def main():
    root = Path(__file__).resolve().parents[1]
    out = root / '.cache/wba-factory/tests'; out.mkdir(parents=True, exist_ok=True)
    factory = root / 'platform/stm32wba55_companion_v11/factory'
    dev = find_vsdevcmd()
    if not dev: raise RuntimeError('MSVC required')
    exe = out / 'test_loader.exe'
    command = ['cl.exe', '/nologo', '/std:c11', '/W4', '/WX', f'/I{factory}', str(factory / 'test_loader.c'), str(factory / 'loader.c'), f'/Fe:{exe}']
    script = out / 'build.cmd'
    script.write_text(f'@echo off\ncall "{dev}" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n' + subprocess.list2cmdline(command) + '\n')
    build = subprocess.run(['cmd.exe', '/d', '/c', str(script)], cwd=out, capture_output=True, text=True)
    (out / 'build.log').write_text(build.stdout + build.stderr)
    if build.returncode: raise RuntimeError(build.stdout + build.stderr)
    native = subprocess.run([str(exe)], capture_output=True, text=True)
    (out / 'native.log').write_text(native.stdout + native.stderr)
    if native.returncode: raise RuntimeError(native.stdout + native.stderr)
    with (out / 'tests.log').open('w', encoding='utf-8') as log:
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(case)
                                   for case in (ProvisionTests, CEProvisionTests))
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    sources = [Path(__file__), root / 'tools/provision_wba_v11.py', root / 'tools/wba_flash_geometry.py',
               root / 'platform/stm32wba55_companion_v11/flash_geometry.json',
               factory / 'loader.c', factory / 'loader.h', factory / 'test_loader.c']
    report = {'result': 'PASS_HOST_SIMULATION_ONLY' if result.wasSuccessful() else 'FAIL', 'tests': result.testsRun,
        'hardwareAcceptance': 'NOT_RUN', 'sources': {str(f.relative_to(root)): p.sha(f.read_bytes()) for f in sources}, 'native': native.stdout.strip()}
    p.write_json(out / 'result.json', report)
    print(json.dumps(report, indent=2))
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__': raise SystemExit(main())
