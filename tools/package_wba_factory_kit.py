"""Bundle verified initial-install tools, matching WBA firmware and installed Type."""
from pathlib import Path
import argparse
import json
import shutil
import zipfile
from provision_wba_v11 import Package, validate_loader, sha, write_json, member

ROOT = Path(__file__).resolve().parents[1]
TYPE = ROOT.parent / 'Companion-Type'
FACTORY = ROOT / 'platform/stm32wba55_companion_v11/factory'

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def verify_sources(root, sources):
    for name, expected in sources.items():
        if sha((root / name).read_bytes()) != expected.lower():
            raise RuntimeError('Stale source evidence: ' + name)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--firmware-package', type=Path, required=True)
    parser.add_argument('--type-evidence', type=Path, default=TYPE / '.cache/wba-v11-oobe')
    parser.add_argument('--output', type=Path, default=ROOT / '.cache/wba-factory/packages')
    parser.add_argument('--loader-dir', type=Path)
    args = parser.parse_args()
    package = Package(args.firmware_package)
    loader_dir = (args.loader_dir or ROOT / ('.cache/wba-factory/loader-ce' if package.geometry.flash_kib == 512 else '.cache/wba-factory/loader')).resolve()
    loader = validate_loader(loader_dir, package.geometry)
    build, parse = load(loader_dir / 'result.json'), load(loader_dir / 'st-parse-result.json')
    tests_dir = ROOT / '.cache/wba-factory/tests'
    tests = load(tests_dir / 'result.json')
    uart_tests_dir = ROOT / '.cache/wba-uart-diagnostics/tests'
    uart_tests = load(uart_tests_dir / 'result.json')
    if uart_tests['result'] != 'PASS_HOST_SIMULATION_ONLY':
        raise RuntimeError('UART diagnostic host tests incomplete')
    verify_sources(ROOT, uart_tests['sources'])
    verify_sources(uart_tests_dir, uart_tests['files'])
    uart_contract_dir = ROOT / '.cache/wba-uart-diagnostics/contract'
    uart_contract = load(uart_contract_dir / 'result.json')
    if uart_contract['result'] != 'PASS_HOST_WIRE_CONTRACT_ONLY':
        raise RuntimeError('C/Python UART contract evidence incomplete')
    verify_sources(ROOT, uart_contract['source_sha256'])
    if sha((uart_contract_dir / 'native-formatter.log').read_bytes()) != uart_contract['log_sha256']:
        raise RuntimeError('UART formatter fixture changed')
    if tests['result'] != 'PASS_HOST_SIMULATION_ONLY' or parse['result'] != 'PASS_ST_OFFLINE_LOADER_PARSE_ONLY':
        raise RuntimeError('Factory evidence incomplete')
    verify_sources(ROOT, build['sources']); verify_sources(ROOT, tests['sources'])
    if parse['loader_sha256'] != build['loader_sha256'] or parse['verifier_sha256'] != sha((ROOT / 'tools/verify_wba_factory_loader.py').read_bytes()):
        raise RuntimeError('ST parser evidence is stale')
    type_build = load(args.type_evidence / 'oobe-build-identity-final.json')
    installed = load(args.type_evidence / 'result.json')
    verify_sources(TYPE, type_build['source_sha256'])
    verify_sources(TYPE, installed['source_sha256'])
    if not type_build['status'].startswith('PASS') or not installed['result'].startswith('PASS') or not installed['installed_payload_match']:
        raise RuntimeError('Type build/install evidence incomplete')
    msi = TYPE / type_build['artifact']['path']
    msi_sha = sha(msi.read_bytes())
    if msi_sha != type_build['artifact']['sha256'] or msi_sha != installed['msi_sha256']:
        raise RuntimeError('Type MSI differs from installed candidate')
    for name, path in [('installed_exe_sha256', Path(installed['installed_exe'])),
                       ('payload_exe_sha256', Path(installed['payload_exe'])),
                       ('installed_dll_sha256', Path(installed['installed_exe']).with_name('companion_type_lib.dll'))]:
        if sha(path.read_bytes()) != installed[name]: raise RuntimeError('Installed Type identity changed')
    if installed['installed_exe_sha256'] != installed['payload_exe_sha256']:
        raise RuntimeError('Installed Type differs from MSI payload')
    if sha(Path(installed['install_log']).read_bytes()) != installed['install_log_sha256']:
        raise RuntimeError('MSI install log changed')
    for item in type_build['logs'].values():
        if sha((TYPE / item['path']).read_bytes()) != item['sha256'].lower(): raise RuntimeError('Type log identity changed')
    arrival_verifier = ROOT / 'tools/verify_wba_v11_board_arrival.py'
    arrival_runner = FACTORY / 'Run-WBA-Board-Arrival.ps1'
    arrival_tools_sha = sha(arrival_verifier.read_bytes() + arrival_runner.read_bytes())
    diagnostic_tools_sha = sha((ROOT / 'tools/diagnose_wba_uart.py').read_bytes() + (FACTORY / 'Diagnose-WBA.ps1').read_bytes())
    kit_id = '-'.join((package.manifest['bin_sha256'][:12], msi_sha[:8],
                       sha((ROOT / 'tools/provision_wba_v11.py').read_bytes())[:8], arrival_tools_sha[:8], diagnostic_tools_sha[:8]))
    out = args.output.resolve() / ('wba-v11-first-install-' + kit_id)
    if out.exists(): raise RuntimeError('Preserve existing kit; choose a new output root')
    out.mkdir(parents=True)
    def copy(source, name):
        target = member(out, name); target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
    names = ['companion-v11-initial-boot-and-app.bin', 'companion-v11-board-bringup.bin',
             'boot/companion_wba55_v11_boot.bin', 'board-integration.md',
             'SOFTWARE_FEATURE_MATRIX.md']
    if 'flash-plan.md' in package.manifest['files']:
        names.append('flash-plan.md')
    names += [n for n in package.manifest['files'] if n.startswith(('type-ota/', 'resource-ota/'))]
    # Keep the actual firmware fault/recovery receipts with the delivered
    # image; the reduced install selection must not drop its verification.
    names += [n for n in package.manifest['files'] if n.startswith('evidence/')]
    firmware_manifest = dict(package.manifest)
    firmware_manifest['files'] = {}
    firmware_manifest['source_delivery_manifest_sha256'] = package.manifest_sha256
    firmware_manifest['selection'] = 'Default FW/boot/UI and signed OTA only; old Type MSI and experimental STOP1 are not included.'
    for name in names:
        source = member(package.directory, name)
        if sha(source.read_bytes()) != package.manifest['files'][name]: raise RuntimeError('Firmware payload changed: ' + name)
        copy(source, 'firmware/' + name)
        firmware_manifest['files'][name] = package.manifest['files'][name]
    write_json(out / 'firmware/manifest.json', firmware_manifest)
    # Verify the actual reduced package with the same entry point users will run.
    Package(out / 'firmware')
    for name in ('Companion_V11_WBA55_UI.stldr', 'result.json', 'st-parse-result.json', 'build.log', 'loader.map'):
        copy(loader_dir / name, 'loader/' + name)
    copy(ROOT / 'tools/provision_wba_v11.py', 'tools/provision_wba_v11.py')
    copy(ROOT / 'tools/wba_flash_geometry.py', 'tools/wba_flash_geometry.py')
    copy(ROOT / 'platform/stm32wba55_companion_v11/flash_geometry.json', 'platform/stm32wba55_companion_v11/flash_geometry.json')
    copy(ROOT / 'app/companion_pendant/update/wba_flash_geometry.h', 'app/companion_pendant/update/wba_flash_geometry.h')
    copy(ROOT / 'tools/diagnose_wba_uart.py', 'tools/diagnose_wba_uart.py')
    copy(arrival_verifier, 'tools/verify_wba_v11_board_arrival.py')
    for name in ('build_wba_factory_loader.py', 'verify_wba_factory_loader.py',
                 'test_wba_factory_provision.py', 'test_wba_uart_diagnostics.py', 'verify_wba_uart_contract.py', 'package_wba_factory_kit.py'):
        copy(ROOT / 'tools' / name, 'source/tools/' + name)
    for source in FACTORY.iterdir():
        if source.is_file(): copy(source, 'source/factory/' + source.name)
    copy(FACTORY / 'Install-WBA.ps1', 'Install-WBA.ps1')
    copy(FACTORY / 'Diagnose-WBA.ps1', 'Diagnose-WBA.ps1')
    copy(arrival_runner, 'Run-WBA-Board-Arrival.ps1')
    copy(FACTORY / 'README.md', 'README.md')
    for name in ('result.json', 'tests.log', 'native.log', 'build.log'):
        copy(tests_dir / name, 'evidence/factory/' + name)
    for name in ('result.json', 'tests.log', 'synthetic-query.log'):
        copy(uart_tests_dir / name, 'evidence/uart/' + name)
    for name in ('result.json', 'native-formatter.log'):
        copy(uart_contract_dir / name, 'evidence/uart/contract/' + name)
    copy(msi, 'type/Companion-Type-x64.msi')
    for name in ('oobe-build-identity-final.json', 'result.json'):
        copy(args.type_evidence / name, 'evidence/type/' + name)
    for item in type_build['logs'].values(): copy(TYPE / item['path'], 'evidence/type/' + Path(item['path']).name)
    capacity_fixture = type_build.get('capacityContract', {}).get('fixture')
    if capacity_fixture:
        source = TYPE / capacity_fixture['path']
        if sha(source.read_bytes()) != capacity_fixture['sha256']:
            raise RuntimeError('Type capacity wire fixture changed')
        copy(source, 'evidence/type/capacity-fixture.bin')
    for name, item in type_build.get('discardContract', {}).get('fixtures', {}).items():
        if name not in ('discard-preview.bin', 'discard-completed.bin') or item.get('bytes') != 84:
            raise RuntimeError('Unexpected Type confirmed-discard wire fixture')
        source = TYPE / item['path']
        if sha(source.read_bytes()) != item['sha256'].lower():
            raise RuntimeError('Type confirmed-discard wire fixture changed')
        copy(source, 'evidence/type/' + name)
    copy(Path(installed['install_log']), 'evidence/type/' + Path(installed['install_log']).name)
    cli_log = Path(installed['installed_cli_log'])
    if sha(cli_log.read_bytes()) != installed['installed_cli_log_sha256']:
        raise RuntimeError('Installed Type read-only validation log changed')
    copy(cli_log, 'evidence/type/' + cli_log.name)
    ota_contract_path = args.type_evidence / 'installed-ota-contract.json'
    if ota_contract_path.exists():
        contract = load(ota_contract_path)
        if (contract.get('result') != 'PASS_INSTALLED_HOST_OTA_CE_CG_CONTRACT_ONLY'
            or contract.get('installedExeSha256') != installed['installed_exe_sha256']
            or contract.get('msiSha256') != msi_sha):
            raise RuntimeError('Installed CE/CG OTA validation belongs to another Type candidate')
        variant = 'ce' if package.geometry.flash_kib == 512 else 'cg'
        correct_app = [item for item in contract.get('checks', [])
                       if item.get('mcu') == variant and item.get('component') == 'firmware'
                       and item.get('wrong_hardware') is False and item.get('exit_code') == 0]
        if len(correct_app) != 1 or correct_app[0]['payload_sha256'] != package.manifest['bin_sha256']:
            raise RuntimeError('Installed Type did not validate this exact MCU app')
        copy(ota_contract_path, 'evidence/type/installed-ota-contract.json')
        for item in contract['checks']:
            source = TYPE / item['log']
            if sha(source.read_bytes()) != item['log_sha256']:
                raise RuntimeError('Installed CE/CG OTA validation log changed')
            copy(source, 'evidence/type/' + source.name)
    startup_path = args.type_evidence / 'installed-startup.json'
    if startup_path.exists():
        startup = load(startup_path)
        if startup.get('exeSha256') != installed['installed_exe_sha256'] or startup.get('msiSha256') != msi_sha:
            raise RuntimeError('Type startup receipt is for a different installed candidate')
        copy(startup_path, 'evidence/type/installed-startup.json')
        ui_log = args.type_evidence / 'installed-ui-ota.log'
        if sha(ui_log.read_bytes()) != startup['uiValidationLogSha256']:
            raise RuntimeError('Installed Type UI validation log changed')
        copy(ui_log, 'evidence/type/installed-ui-ota.log')
    for pattern in ('installed*oobe*.log', '*identity*.json'):
        for source in args.type_evidence.glob(pattern): copy(source, 'evidence/type/' + source.name)
    files = {str(f.relative_to(out)).replace('\\', '/'): sha(f.read_bytes()) for f in sorted(out.rglob('*')) if f.is_file()}
    manifest = {'schema': 'companion.wba.factory-kit.v1', 'result': 'PASS_SOFTWARE_PACKAGE_ONLY',
        'mcu':package.geometry.mcu,'internal_flash_geometry':package.geometry.receipt(),
        'hardwareAcceptance': 'NOT_RUN', 'fullChainAcceptance': 'NOT_RUN', 'flashed': False,
        'firmware_version': package.manifest['firmware_version'], 'ui_generation': package.manifest['ui_resource_profile']['generation'],
        'firmware_sha256': package.manifest['bin_sha256'], 'type_msi_sha256': msi_sha,
        'loader_sha256': build['loader_sha256'], 'arrival_tools_sha256': arrival_tools_sha,
        'diagnostic_tools_sha256': diagnostic_tools_sha, 'uart_host_tests': uart_tests['tests'],
        'factory_tests': tests['tests'], 'files': files}
    write_json(out / 'kit-manifest.json', manifest)
    archive = out.with_suffix('.zip')
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as z:
        for file in sorted(out.rglob('*')):
            if file.is_file(): z.write(file, file.relative_to(out))
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None: raise RuntimeError('ZIP CRC failure')
        for name, expected in files.items():
            if sha(z.read(name)) != expected: raise RuntimeError('ZIP payload mismatch: ' + name)
    receipt = {'result': 'PASS_PACKAGE_INTEGRITY_ONLY', 'archive': str(archive), 'sha256': sha(archive.read_bytes()),
        'payloads': len(files), 'bytes': archive.stat().st_size, 'hardwareAcceptance': 'NOT_RUN'}
    write_json(archive.with_suffix('.verification.json'), receipt)
    print(json.dumps(receipt, indent=2))

if __name__ == '__main__': main()
