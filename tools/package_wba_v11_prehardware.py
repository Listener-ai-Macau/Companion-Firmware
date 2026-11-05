"""Collect a source-matched WBA prehardware package; never flash or claim acceptance."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile
from PIL import Image
from wba_flash_geometry import from_receipt

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / '.cache/wba-v11-prehardware/ble-build'
BOOT = ROOT / '.cache/wba-v11-prehardware/boot-build'
OTA_ROOT = ROOT / '.cache/wba-v11-prehardware/ota-packages'
TYPE = ROOT.parent / 'Companion-Type'
HARDWARE = ROOT.parent / 'Companion-Hardware/electronics/companion-v1.1-2026-09-19'
REPORTS = {
    'build': BUILD / 'result.json',
    'runtime': ROOT / '.cache/wba-product-runtime/result.json',
    'renderer': ROOT / '.cache/wba-product-renderer/result.json',
    'resources': ROOT / '.cache/wba-product-resources/test-result.json',
    'runtime_journeys': ROOT / '.cache/wba-runtime-preview/journey-result.json',
    'accepted_art_preservation': ROOT / '.cache/wba-ui-polish/preservation-result.json',
    'pinmap': ROOT / '.cache/wba-v11-prehardware/pinmap-check.json',
    'wake_events': ROOT / '.cache/host-tests/wba-wake-events/result.json',
    'imu_idle': ROOT / '.cache/host-tests/wba-imu-power/result.json',
    'power_target': ROOT / '.cache/host-tests/wba-power-target/result.json',
    'power_monitor': ROOT / '.cache/host-tests/wba-power-monitor/result.json',
    'stop_lifecycle': ROOT / '.cache/host-tests/wba-stop/result.json',
    'stack_monitor': ROOT / '.cache/host-tests/wba-stack-monitor/result.json',
    'retained_clock': ROOT / '.cache/host-tests/wba-retained-clock/result.json',
    'stop1_engineering_build': ROOT / '.cache/wba-v11-prehardware/stop1-build/result.json',
    'update_product_power': ROOT / '.cache/host-tests/wba-update-product-power/result.json',
    'visual_composition': ROOT / '.cache/wba-visual-review/result.json',
    'type_product_journeys': TYPE / '.cache/wba-v11-type/identity-meeting-retry-result.json',
    'type_ble_timeouts': TYPE / '.cache/wba-v11-type/ble-timeout-result.json',
    'type_auto_recovery': TYPE / '.cache/wba-v11-type/auto-recovery-result.json',
    'type_msi_build': TYPE / '.cache/wba-v11-type/msi-recovery-build.json',
    'presenter': ROOT / '.cache/wba-screen-presenter-host/result.json',
    'panel': ROOT / '.cache/wba-ssd1681-host/result.json',
    'audio_feedback': ROOT / '.cache/wba-audio-feedback-host/result.json',
    'recording': ROOT / '.cache/wba-recording-service-host/result.json',
    'product_recording_integration': ROOT / '.cache/wba-product-recording-integration-host/result.json',
    'journal_regression': ROOT / '.cache/validation/comp-req-778-recording-journal-host/result.json',
    'transfer': ROOT / '.cache/wba-recording-transfer-host/result.json',
    'producer_consumer_wire': ROOT / '.cache/host-tests/wba-type-recording-wire/result.json',
    'product_link': ROOT / '.cache/wba-companion-link-host/result.json',
    'ble_event_copy': ROOT / '.cache/wba-ble-event-copy-host/result.json',
    'old_wb_gatt_regression': ROOT / '.cache/validation/comp-req-562-ble-device-control/result.json',
    'preferences': ROOT / '.cache/wba-preferences-host/result.json',
    'ota_gatt': ROOT / '.cache/wba-ota-gatt-host/result.json',
    'update_service': ROOT / '.cache/wba-update-service-host/result.json',
    'update_manifest': ROOT / '.cache/wba-update-manifest-host/result.json',
    'update_metadata': ROOT / '.cache/wba-update-metadata-host/result.json',
    'boot_installer': ROOT / '.cache/wba-boot-installer-host/result.json',
    'update_confirmation': ROOT / '.cache/wba-update-storage-confirm-host/result.json',
    'resident_boot': BOOT / 'result.json',
    'type_install': TYPE / '.cache/wba-v11-type/result.json',
    'type_ota_tests': TYPE / '.cache/wba-v11-type/ota-tests.json',
}
APP = 'app/companion_pendant/'
ALIASES = {
    'presenter': ('sources', {
        'presenter_c': APP + 'epaper/screen_presenter_wba.c',
        'presenter_h': APP + 'epaper/screen_presenter_wba.h',
        'test': APP + 'epaper/tests/test_screen_presenter_wba.c',
    }),
    'audio_feedback': ('sources', {
        'audio_feedback_c': APP + 'playback/audio_feedback.c',
        'audio_feedback_h': APP + 'playback/audio_feedback.h',
        'test': APP + 'playback/tests/test_audio_feedback.c',
    }),
    'panel': ('hashes', {
        'ssd1681_wba.c': APP + 'epaper/ssd1681_wba.c',
        'ssd1681_wba.h': APP + 'epaper/ssd1681_wba.h',
        'test_ssd1681_wba.c': APP + 'epaper/tests/test_ssd1681_wba.c',
    }),
}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    reports = {name: json.loads(path.read_text(encoding='utf-8-sig')) for name, path in REPORTS.items()}
    for name, report in reports.items():
        status = report.get('result', report.get('status', ''))
        if not str(status).startswith('PASS'):
            raise RuntimeError(f'{name} is not a completed software check: {status}')
        hashes = dict(report.get('source_sha256', report.get('sourceSha256', {})))
        if name == 'type_msi_build':
            hashes.update(report['build_inputs_sha256'])
        if name == 'pinmap':
            hashes.update(report['input_sha256'])
        if name.startswith('update_') or name in ('boot_installer','resident_boot'):
            hashes.update(report.get('sources',{}))
        if name in ALIASES:
            field, aliases = ALIASES[name]
            hashes.update({path: report[field][alias] for alias, path in aliases.items()})
        if not hashes:
            raise RuntimeError(f'{name} has no source identity evidence')
        for source, expected in hashes.items():
            path = Path(source)
            if not path.is_absolute():
                path = (TYPE if name.startswith('type_') else ROOT) / path
            if digest(path).lower() != expected.lower():
                raise RuntimeError(f'{name} evidence is stale: {path}')
    image = BUILD / 'companion-v11-board-bringup.bin'
    if reports['build'].get('product_ble_linked') is not True:
        raise RuntimeError('This delivery requires the WBA BLE product target')
    if reports['build']['low_power']['stop1_compiled']:
        raise RuntimeError('Production prehardware candidate must keep unqualified Stop1 disabled')
    experimental=reports['stop1_engineering_build']
    if not experimental['low_power']['stop1_compiled'] or experimental['low_power']['board_qualified'] or \
       experimental['firmware_version']!=reports['build']['firmware_version'] or \
       experimental['ui_resource_profile']!=reports['build']['ui_resource_profile']:
        raise RuntimeError('Stop1 engineering target must be explicitly experimental and match version/resources')
    image_sha = digest(image)
    ota=OTA_ROOT/image_sha[:12]
    if image_sha != reports['build']['bin_sha256'].lower():
        raise RuntimeError('Binary does not match build result')
    boot=BOOT/'companion_wba55_v11_boot.bin'
    boot_receipt=reports['resident_boot'];app_receipt=reports['build']
    geometry=from_receipt(app_receipt)
    if from_receipt(boot_receipt)!=geometry:
        raise RuntimeError('Resident boot and app target different actual MCU geometry')
    if digest(boot)!=boot_receipt['bin_sha256'] or boot_receipt['installed_image_size']!=image.stat().st_size or \
       boot_receipt['firmware_version']!=app_receipt['firmware_version'] or \
       boot_receipt['public_key_sha256']!=app_receipt['update_trust_anchor']['public_key_sha256'] or \
       boot_receipt['key_id']!=app_receipt['update_trust_anchor']['key_id']:
        raise RuntimeError('Resident boot/app geometry, version or trust anchor mismatch')
    ota_manifest=json.loads((ota/'ota_manifest.json').read_text())
    if ota_manifest['file']['sha256']!=image_sha or digest(ota/'firmware_ota.bin')!=image_sha:
        raise RuntimeError('Type OTA package does not match app')
    resources=ota/'resources'
    resource_manifest=json.loads((resources/'ota_manifest.json').read_text())
    resource_sha=reports['build']['ui_resource_profile']['uiPartitionSha256'].lower()
    if digest(resources/'ui-partition.bin')!=resource_sha or resource_manifest['file']['sha256']!=resource_sha or \
       reports['runtime_journeys']['resource_image_sha256'].lower()!=resource_sha:
        raise RuntimeError('Resource OTA, firmware and runtime preview identities differ')
    type_receipt=reports['type_install']
    type_build=reports['type_msi_build']
    if type_build['msi']['sha256'] != type_receipt['msi_sha256'] or \
       type_build['release_exe']['sha256'] != type_receipt['release_sha256'] or \
       type_build['release_dll']['sha256'] != type_receipt['installed_dll_sha256'] or \
       digest(TYPE/type_build['build_log']['path']) != type_build['build_log']['sha256']:
        raise RuntimeError('Type build/install provenance differs')
    if digest(Path(type_receipt['msi'])).upper()!=type_receipt['msi_sha256'].upper() or \
       digest(Path(type_receipt['installed'])).upper()!=type_receipt['installed_sha256'].upper() or \
       type_receipt['installed_sha256']!=type_receipt['payload_sha256']:
        raise RuntimeError('Type MSI/installed identity differs')
    for name, expected in type_receipt['package_members'].items():
        for directory in (Path(type_receipt['installed']).parent, Path(type_receipt['payload']).parent):
            if digest(directory / name).lower() != expected.lower():
                raise RuntimeError(f'Type package/installed member differs: {directory / name}')
    ota_test_log = TYPE / reports['type_ota_tests'].get('log', '.cache/wba-v11-type/ota-tests-current.log')
    if digest(ota_test_log).lower() != reports['type_ota_tests']['log_sha256'].lower():
        raise RuntimeError('Type OTA test log differs from its receipt')
    if reports['type_ota_tests']['input_payload_sha256'] != image_sha or \
       type_receipt['installed_ota_validation']['payloadSha256'] != image_sha:
        raise RuntimeError('Type did not validate this firmware candidate')
    if digest(ota/'ota_manifest.json')!=reports['type_ota_tests']['input_manifest_sha256']:
        raise RuntimeError('Type test manifest is not the current candidate')
    installed_validation_log=TYPE/type_receipt['installed_ota_validation_log']
    if digest(installed_validation_log)!=type_receipt['installed_ota_validation_log_sha256']:
        raise RuntimeError('Installed Type validation log differs')
    validation_lines=[line.removeprefix('resource_ota_validate_json=')
        for line in installed_validation_log.read_text(encoding='utf-8-sig').splitlines()
        if line.startswith('resource_ota_validate_json=')]
    if len(validation_lines)!=1 or json.loads(validation_lines[0])!=type_receipt['installed_ota_validation']:
        raise RuntimeError('Installed Type log does not substantiate its receipt')
    for report_name in ('type_ble_timeouts', 'type_auto_recovery', 'type_product_journeys'):
        for log in reports[report_name]['logs'].values():
            if digest(TYPE / log['path']).lower() != log['sha256'].lower():
                raise RuntimeError(f'Type test log differs: {log["path"]}')
    preview = json.loads((ROOT / '.cache/wba-audio-preview/manifest.json').read_text(encoding='utf-8'))
    for source, expected in preview['source_sha256'].items():
        if digest(ROOT / source).lower() != expected.lower():
            raise RuntimeError(f'Speaker preview is stale: {source}')
    for path, expected in (
        (ROOT / '.cache/wba-audio-preview/companion-cues.wav', preview['wav_sha256']),
        (ROOT / '.cache/wba-recording-service-host/real-opus.cop1', reports['recording']['cop1_sha256']),
    ):
        if digest(path).lower() != expected.lower():
            raise RuntimeError(f'Artifact no longer matches its evidence: {path}')
    for name, expected in reports['recording']['live_transfer']['artifacts'].items():
        path = ROOT / '.cache/wba-recording-service-host' / name
        if digest(path).lower() != expected.lower():
            raise RuntimeError(f'Live recording artifact differs: {path}')
    for name, expected in reports['producer_consumer_wire']['artifact_sha256'].items():
        path = ROOT / '.cache/wba-recording-service-host' / name
        if digest(path).lower() != expected.lower():
            raise RuntimeError(f'Type wire fixture differs: {path}')
    # Host preview and the installed Type payload can change independently of
    # the MCU binary. Keep each matched combination as an immutable candidate.
    out = ROOT / '.cache/wba-v11-prehardware/packages' / (image_sha[:12]+'-live-'+digest(ROOT/'tools/wba_runtime_preview.html')[:8]+'-type-'+type_receipt['msi_sha256'][:8].lower()+'-p'+digest(Path(__file__))[:8])
    out.mkdir(parents=True, exist_ok=True)
    files = {f'reports/{name}.json': source for name, source in REPORTS.items()}
    stop_build=ROOT/'.cache/wba-v11-prehardware/stop1-build'
    if digest(stop_build/'companion-v11-board-bringup.bin')!=experimental['bin_sha256']:
        raise RuntimeError('Stop1 engineering binary does not match its build receipt')
    for name in ('companion-v11-board-bringup.bin','companion-v11-board-bringup.elf',
                 'companion-v11-board-bringup.map','size.txt','build.log','stack-usage.json','startup-stack-paint.txt'):
        files[f'engineering-stop1-not-qualified/{name}']=stop_build/name
    for name in ('README.md', 'Companion V1.1.pdf', 'source-manifest.json',
                 'pcb-net-evidence.json', 'panel-source-evidence.json'):
        files[f'hardware/{name}'] = HARDWARE / name
    files['hardware/pinmap.json'] = ROOT / 'platform/stm32wba55_companion_v11/pinmap.json'
    for suffix in ('bin', 'elf', 'map'):
        files[f'companion-v11-board-bringup.{suffix}'] = BUILD / f'companion-v11-board-bringup.{suffix}'
        files[f'boot/companion_wba55_v11_boot.{suffix}'] = BOOT / f'companion_wba55_v11_boot.{suffix}'
    for name in ('ota_manifest.json','firmware_ota.bin','wba_manifest.bin','wba_manifest.bin.json','update-public.xy'):
        files[f'type-ota/{name}']=ota/name
    for name in ('ota_manifest.json','ui-partition.bin','wba_manifest.bin','wba_manifest.bin.json','update-public.xy'):
        files[f'resource-ota/{name}']=resources/name
    files['resources/profile.json']=ROOT/'.cache/wba-product-resources/profile.json'
    files['runtime-preview/index.html']=ROOT/'tools/wba_runtime_preview.html'
    for name in ('browser-menu.jpg','browser-home.jpg'):
        files[f'runtime-preview/{name}']=ROOT/'.cache/wba-runtime-preview'/name
    for frame in reports['runtime_journeys']['frames']:
        files[f'runtime-preview/{frame["label"]}.bin']=ROOT/'.cache/wba-runtime-preview'/f'{frame["label"]}.bin'
    files['type/Companion-Type.msi']=Path(type_receipt['msi'])
    files['type/ota-tests.log']=ota_test_log
    files['type/installed-ota-validation.log']=installed_validation_log
    files['type/msi-build.log']=TYPE/type_build['build_log']['path']
    for name, log in reports['type_ble_timeouts']['logs'].items():
        files[f'type/{name}-tests.log'] = TYPE / log['path']
    for name, log in reports['type_auto_recovery']['logs'].items():
        files[f'type/recovery-{name}-tests.log'] = TYPE / log['path']
    for name, log in reports['type_product_journeys']['logs'].items():
        files[f'type/product-{name}-tests.log'] = TYPE / log['path']
    files.update({
        'stack-usage.json': BUILD / 'stack-usage.json',
        'startup-stack-paint.txt': BUILD / 'startup-stack-paint.txt',
        'product-decisions.md': ROOT / 'app/companion_pendant/runtime/README.md',
        'board-integration.md': ROOT / 'platform/stm32wba55_companion_v11/README.md',
        'power-profile.json': BUILD / 'power-profile.json',
        'wba_board_power_profile.h': BUILD / 'wba_board_power_profile.h',
        'contracts-provenance.json': ROOT / 'app/companion_pendant/runtime/generated/provenance.json',
        'speaker-preview.wav': ROOT / '.cache/wba-audio-preview/companion-cues.wav',
        'speaker-preview.json': ROOT / '.cache/wba-audio-preview/manifest.json',
        'visual-review/index.html': ROOT / '.cache/wba-visual-review/index.html',
        'visual-review/review.png': ROOT / '.cache/wba-visual-review/review.png',
        'visual-review/blink-review.png': ROOT / '.cache/wba-visual-review/blink-review.png',
        'visual-review/hold.gif': ROOT / '.cache/wba-visual-review/hold.gif',
        'visual-review/browser-result.json': ROOT / '.cache/wba-visual-review/browser-result.json',
        'ble-upstream-provenance.json': ROOT / 'platform/stm32wba55_companion_v11/ble/upstream-provenance.json',
        'licenses/st-applications.md': ROOT / 'platform/stm32wba55_companion_v11/ble/LICENSE.md',
        'licenses/st-wpan.md': ROOT / '.cache/deps/STM32CubeWBA/Middlewares/ST/STM32_WPAN/LICENSE.md',
        'licenses/st-hal.md': ROOT / '.cache/deps/STM32CubeWBA/Drivers/STM32WBAxx_HAL_Driver/LICENSE.md',
        'licenses/opus.txt': ROOT / 'third_party/opus/COPYING',
        'recording-art-audit.json': ROOT / '.cache/wba-runtime-preview/recording-art-audit.json',
        'recording-art/original.pbm': ROOT / 'docs/art/sources/comp-req-774-recording-overlay.pbm',
        'recording-art/provenance.json': ROOT / 'docs/art/sources/comp-req-774-recording-overlay.json',
        'recording-art/wba_recording_art.py': ROOT / 'tools/wba_recording_art.py',
        'ui-polish/preservation-result.json': ROOT / '.cache/wba-ui-polish/preservation-result.json',
        'ui-polish/menu-review-zh.png': ROOT / '.cache/wba-product-resources/menu-review/zh_cn.png',
        'ui-polish/menu-review-en.png': ROOT / '.cache/wba-product-resources/menu-review/en.png',
        'ui-polish/menu-review-result.json': ROOT / '.cache/wba-product-resources/menu-review/result.json',
        'recording-host-example.cop1': ROOT / '.cache/wba-recording-service-host/real-opus.cop1',
        'recording-live-prefix.cop1': ROOT / '.cache/wba-recording-service-host/real-opus.cop1.prefix.cop1',
        'recording-active-list.bin': ROOT / '.cache/wba-recording-service-host/real-opus.cop1.active-list.bin',
        'recording-final-list.bin': ROOT / '.cache/wba-recording-service-host/real-opus.cop1.final-list.bin',
        'recording-final-wire.bin': ROOT / '.cache/wba-recording-service-host/real-opus.cop1.wire.bin',
        'recording-live-wire.bin': ROOT / '.cache/wba-recording-service-host/real-opus.cop1.live-wire.bin',
        'wire-review/type_recording_wire_harness.rs': ROOT / '.cache/host-tests/wba-type-recording-wire/type_recording_wire_harness.rs',
        'wire-review/test_wba_type_recording_wire.py': ROOT / 'tools/test_wba_type_recording_wire.py',
        'previous-art-review/gen29-browser-result.json': ROOT / '.cache/wba-runtime-preview/browser-result.json',
        'size.txt': BUILD / 'size.txt',
    })
    for frame in reports['visual_composition']['frames']:
        visual=ROOT / '.cache/wba-visual-review/images' / f'{frame}.png'
        raster=Image.open(visual).convert('1',dither=Image.Dither.NONE).tobytes()
        if hashlib.sha256(raster).hexdigest()!=reports['visual_composition']['frames'][frame]['sha256']:
            raise RuntimeError(f'Visual preview differs from production compositor: {frame}')
        files[f'visual-review/images/{frame}.png']=visual
    for name, source in files.items():
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and digest(target) != digest(source):
            raise RuntimeError(f'Existing package differs: {target}')
        shutil.copy2(source, target)
    combined=boot.read_bytes()+bytes([255])*(0x8000-boot.stat().st_size)+image.read_bytes()
    combined_file=out/'companion-v11-initial-boot-and-app.bin'
    if combined_file.exists() and combined_file.read_bytes()!=combined:
        raise RuntimeError('Existing combined initial image differs')
    combined_file.write_bytes(combined)
    manifest = {
        'schema': 'companion.wba.v11.prehardware.delivery.v1',
        'mcu': geometry.mcu, 'internal_flash_geometry': geometry.receipt(), 'board': 'Companion V1.1 2026-09-19',
        'role': 'PREHARDWARE_NOT_RELEASE', 'bin_sha256': image_sha,
        'load_address': '0x08008000', 'stack_reserved_bytes': 24576,
        'initial_combined_load_address':'0x08000000','initial_combined_sha256':digest(combined_file),
        'initial_combined_warning':'Internal flash boot+app only. Separate resource-ota/ui-partition.bin targets external NOR UI bank at offset 0. Preserve BLE NVM and recordings.',
        'ui_resource_profile':app_receipt['ui_resource_profile'],
        'update_trust_anchor':app_receipt['update_trust_anchor'],'dev_only':ota_manifest['dev_only'],
        'power_profile':app_receipt['power_profile'],
        'low_power':app_receipt['low_power'],
        'memory':app_receipt['memory'],
        'time_retention':'RTC-powered reset only; UTC time-of-day anchor in BKP4..15; full 1.8V power loss requires Type sync',
        'meeting_recovery':'Persisted, bounded recovery of explicitly requested sessions in their original mode; hardware and real-service end-to-end acceptance remains NOT_RUN',
        'stop1_engineering':{'mode':experimental['low_power']['mode'],'board_qualified':False,
                            'bin_sha256':experimental['bin_sha256'],'installable_with_default_boot':False},
        'hardwareAcceptance': 'NOT_RUN', 'fullChainAcceptance': 'NOT_RUN', 'flashed': False,
        'remaining': reports['build']['remaining'],
        'pet_voice': 'nonverbal_pet_v1; no speech; default 25 percent digital gain',
        'visual_preview': 'Production C runtime + matched resource loader + compositor. Touch, IMU, recording and panel-completion callbacks are simulated. Old gen21 remains separate.',
        'product_ble_linked': True,
        'ble_nvm_region':reports['build']['ble_nvm_region'],
        'recording_art_restoration': json.loads((ROOT/'.cache/wba-product-resources/profile.json').read_text())['recordingArtRestoration'],
        'host_example_warning': 'Synthetic PCM tests exercise the real codec. This is not a microphone or meeting acceptance recording.',
        'previous_art_review': 'gen29 browser evidence is historical; current source/resource journeys were rerun. Pixel preservation compares every state; only About version text changed in the UI bank. Runtime status adds qualified external-power/fault indicators within the existing 16px rail.',
        'files': {**{name: digest(out / name) for name in files},combined_file.name:digest(combined_file)},
    }
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (out / 'README.txt').write_text(
        'Companion V1.1 WBA55 整机预开发包（不是正式产品 release）\n'
        f'bin-sha256: {image_sha}\n'
        '包含：交互/表情/菜单/宠物叫声/真实 Opus-COP1-NOR、BLE 拉录、设置校时、签名升级/回滚、充电解码、受保护 ADC 采样、按键唤醒与模块休眠门控、测试和试听。\n'
        '已从旧烧录资源恢复麦克风、细线声波和原坐标；64 帧运动重新构建，未声明与旧版逐帧相同，详见 recording-art-audit.json。\n'
        '未刷写；硬件验收、完整会议链路与 Owner 验收均未进行。不可刷到旧 WB55。\n'
        'Type 包含会议处理恢复检查点与有限重试；仅继续已明确请求处理的会话，保留原模式。相关主机故障测试随包，不等同真实 ASR/纪要服务验收。\n'
        f"包含新 WBA generation {app_receipt['ui_resource_profile']['generation']} 资源与匹配固件；旧 WB generation 21 不改。屏幕 RESET 与电池分压/上拉待确认；默认候选 STOP1 关闭。已增加栈水位/录音预算诊断和带电复位时间恢复；完全断电须Type校时。\n"
        'engineering-stop1-not-qualified 是另一个 opt-in 工程构建，只作未到板前软件准备；包含 RTC 唤醒/补时、LPM 门控与固定音频 PLL 恢复，未验证真实时延/无线事件/电流。该bin大小和SHA不同，没有配套合并boot或OTA清单，不能套用默认安装入口。\n'
        'power-profile.json 是本次构建使用的电气参数。默认未获电气确认，因此 ADC 禁用、充电未知、OTA 供电门控拒绝未知供电。到板按 board-integration.md 确认参数后通过 --power-profile 重建；不重写驱动、不通过 BLE 远程放开危险分压。\n'
        '初次 SWD：initial-boot-and-app.bin 从0x08000000；app单独从0x08008000，不能按旧地址刷。\n'
        'type-ota 是同版本签名包，设备会拒绝同版本/降级。后续升级需提高构建 firmware-version。\n'
        'resource-ota/ui-partition.bin 是独立外部 NOR 2MiB UI bank（offset 0），不可写入 MCU flash。签名包只兼容本版本 app。\n'
        'DEV_ONLY 信任锚不可用于正式量产。私钥不随包。\n'
        'BLE/NVM/断链与音频等物理验证未进行；本包不是到板即用或完整会议 PASS。\n'
        'speaker-preview 顺序：确认、开始录音、停止录音、错误；不代表实物音量。\n'
        'recording-host-example.cop1 只是合成输入的真实编码测试文件，不是实板录音。\n'
        '详见 product-decisions.md、board-integration.md、manifest.json。\n', encoding='utf-8')
    archive = out.with_suffix('.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for file in sorted(out.rglob('*')):
            if file.is_file():
                z.write(file, file.relative_to(out))
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise RuntimeError('Archive CRC verification failed')
        archived_manifest = json.loads(z.read('manifest.json'))
        for name, expected in archived_manifest['files'].items():
            if hashlib.sha256(z.read(name)).hexdigest() != expected:
                raise RuntimeError(f'Archived payload differs: {name}')
    verification = {
        'status': 'PASS_PACKAGE_INTEGRITY_ONLY',
        'archive': str(archive), 'archive_sha256': digest(archive),
        'verified_payloads': len(manifest['files']), 'bin_sha256': image_sha,
        'hardwareAcceptance': 'NOT_RUN', 'fullChainAcceptance': 'NOT_RUN',
    }
    archive.with_suffix('.verification.json').write_text(
        json.dumps(verification, indent=2) + '\n', encoding='utf-8')
    print(archive)

if __name__ == '__main__':
    main()
