#!/usr/bin/env python3
"""Build the real WBA55 V1.1 board diagnostic ELF/bin and native peripheral tests.

No flash, option-byte writes, remote pushes or physical PASS claims.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import struct
import sys
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd
from wba_ble_target import configuration as ble_configuration, WPAN_COMMIT
from wba_power_profile import write_header as write_power_profile
from wba_flash_geometry import MCUS, LAYOUTS, SOURCE as GEOMETRY_SOURCE, for_mcu, validate_generated_header
from wba_resource_geometry import from_profile as resource_geometry_from_profile
from inspect_wba_ce_sram import inspect_elf as inspect_ce_elf
from audit_pending_acl_ownership import inspect_elf as inspect_pending_acl_ownership
from wba_face_cache_budget import inspect_bank as inspect_face_cache, capacity_from_header as face_cache_capacity
from compact_wba_recording_ui import generate as compact_recording_ui
from wba_audio_profile import resolve as resolve_audio_profile, write_identity as write_audio_profile_identity
from wba_stack_usage import collect_stack_usage, fresh_lto_reports, lto_report_stamps

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / 'platform/stm32wba55_companion_v11'
APP = ROOT / 'app/companion_pendant'
SDK_COMMIT = 'e455b860ceb52aaa0332a98f1e7a10bbd7014fc9'
MODULES = {'Drivers/CMSIS/Device/ST/STM32WBAxx': '3373b40fa3b71ce114f58b170acd0f8833d42508',
           'Drivers/STM32WBAxx_HAL_Driver': 'c36d9aabc6068051ed27a3a683a6b4f35f04d815'}
PORTABLE = [APP / name for name in ('board/tca6408.c', 'board/companion_v11_board.c',
             'imu/lsm6dso.c', 'imu/motion_events.c', 'playback/speaker_playback.c',
             'storage/spi_nor_stm32wba.c', 'storage/wba_shared_pool_guard.c', 'storage/wba_workspace_layout.c', 'board/companion_v11_services.c',
             'v1_features/companion_v1_features.c', 'power/power_policy.c',
             'power/wba_power_monitor.c', 'power/wba_button.c',
             'power/wba_stop.c',
             'power/wba_stack_monitor.c',
             'power/wba_retained_clock.c',
             'touch/ft6336.c', 'touch/touch_target_stm32wba_ft6336.c', 'recording/wba_pdm_capture.c',
             'epaper/ssd1681_wba.c', 'playback/audio_feedback.c', 'recording/wba_silence_stop.c',
             'runtime/companion_runtime.c', 'runtime/companion_pet_chat.c', 'runtime/companion_renderer.c', 'runtime/companion_resources.c', 'runtime/companion_preferences.c',
             'runtime/companion_pet_behavior.c', 'runtime/companion_pet_profile.c', 'runtime/companion_pet_profile_store.c', 'runtime/companion_pet_profile_wire.c', 'runtime/companion_pet_face.c',
             'touch/touch_gesture.c', 'touch/touch_tap_arbiter.c', 'touch/browser_interaction_runtime.c',
             'epaper/screen_menu.c', 'epaper/screen_framebuffer.c', 'epaper/motion_coordinator.c',
             'epaper/screen_presenter_wba.c', 'epaper/refresh_policy.c', 'epaper/asset_store.c',
             'epaper/wba_frame_store.c',
             'epaper/screen_assets_stm32wba.c', 'epaper/emote_asset_pack.c', 'epaper/emote_player.c',
             'epaper/ui_asset_generation.c', 'power/power_settings_store.c')]
INCLUDES = [PLATFORM, *(APP / name for name in ('board', 'imu', 'playback', 'storage', 'v1_features', 'power', 'touch', 'recording', 'epaper', 'runtime', 'runtime/generated', 'update')),
            ROOT / 'third_party/denzic-platform/audio/embedded/c/include']
HAL_MODULES = ('hal', 'hal_cortex', 'hal_gpio', 'hal_rcc', 'hal_rcc_ex', 'hal_pwr',
               'hal_pwr_ex', 'hal_flash', 'hal_flash_ex', 'hal_dma', 'hal_dma_ex',
               'hal_i2c', 'hal_i2c_ex', 'hal_spi', 'hal_spi_ex', 'hal_sai', 'hal_sai_ex',
               'hal_uart', 'hal_uart_ex', 'hal_icache', 'hal_rng', 'hal_adc', 'hal_adc_ex')

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def prepare_sdk(sdk: Path, bootstrap: bool, out: Path, log: Path) -> None:
    if not sdk.exists():
        if not bootstrap:
            raise RuntimeError('Pinned CubeWBA SDK absent; run with --bootstrap-sdk or --sdk PATH')
        sdk.parent.mkdir(parents=True, exist_ok=True)
        run(['git', 'clone', '--depth', '1', '--filter=blob:none', '--sparse', '--branch',
             'v1.10.0', 'https://github.com/STMicroelectronics/STM32CubeWBA.git', str(sdk)], out, log)
    if bootstrap:
        run(['git', 'sparse-checkout', 'add', '--skip-checks', 'Drivers/CMSIS',
             'Drivers/STM32WBAxx_HAL_Driver'], sdk, log)
        run(['git', '-c', 'submodule.Drivers/CMSIS/Device/ST/STM32WBAxx.url=https://github.com/STMicroelectronics/cmsis_device_wba.git',
             '-c', 'submodule.Drivers/STM32WBAxx_HAL_Driver.url=https://github.com/STMicroelectronics/stm32wbaxx_hal_driver.git',
             'submodule', 'update', '--init', '--depth', '1', *MODULES], sdk, log)
    for folder, expected in [('', SDK_COMMIT), *MODULES.items()]:
        actual = run(['git', 'rev-parse', 'HEAD'], sdk / folder, log).strip()
        if actual != expected:
            raise RuntimeError(f'SDK identity mismatch at {folder}: expected {expected}, got {actual}')
        if run(['git', 'diff', '--name-only', 'HEAD', '--', 'Drivers' if not folder else '.'], sdk / folder, log).strip():
            raise RuntimeError(f'SDK has modified sources: {folder}')

def native(out: Path, log: Path, resource_includes: list[Path] | None = None,
           resource_geometry: dict | None = None) -> str:
    harness = APP / 'board/tests/test_v11_peripherals.c'
    sources = [harness, *PORTABLE]
    exe = out / 'v11_peripherals_test.exe'
    devcmd = find_vsdevcmd()
    if devcmd is None:
        raise RuntimeError('Visual Studio Build Tools needed for native tests')
    args = ['cl.exe', '/nologo', '/std:c11', '/W4', '/WX', '/utf-8', '/DCOMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1',
            '/DCOMPANION_WBA_RESOURCE_PROFILE=1',
            *([f'/DCOMP_WBA_NOR_UI_BYTES={resource_geometry["staticBytes"]}u',
               f'/DCOMP_WBA_NOR_TOTAL_BYTES={resource_geometry["norBytes"]}u'] if resource_geometry else []),
            *(f'/I{p}' for p in [*(resource_includes or []), *INCLUDES]), *(str(p) for p in sources), f'/Fe:{exe}']
    script = out / 'build_native.cmd'
    script.write_text(f'@echo off\ncall "{devcmd}" -arch=amd64 -host_arch=amd64 >nul\n'
                      'if errorlevel 1 exit /b %errorlevel%\n' + subprocess.list2cmdline(args) + '\n', encoding='utf-8')
    run(['cmd.exe', '/d', '/c', str(script)], out, log)
    result = run([str(exe)], out, log)
    if 'PASS_PREHARDWARE:' not in result:
        raise RuntimeError('Native tests did not report completion')
    (out / 'native-tests.txt').write_text(result, encoding='utf-8')
    return result

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--current-recipe', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--sdk', type=Path, default=ROOT / '.cache/deps/STM32CubeWBA')
    parser.add_argument('--output', type=Path, default=ROOT / '.cache/wba-v11-prehardware/build')
    parser.add_argument('--bootstrap-sdk', action='store_true')
    parser.add_argument('--with-ble', action='store_true', default=True, help='Link WBA host/radio and product GATT (product default)')
    parser.add_argument('--product', choices=('companion','capture'), default='companion', help='Product identity is independent of the screen configuration')
    parser.add_argument('--screen-disabled', action='store_true', help='Do not initialize or service the detached screen/touch module')
    parser.add_argument('--periodic-uart-diagnostics', action='store_true', help='Debug only: emit full idle UART snapshots every ten seconds')
    parser.add_argument('--ble-peer-indications', action='store_true', help='Candidate: retain official GATT client indication handling on the unchanged peripheral-only radio controller')
    parser.add_argument('--without-ble', dest='with_ble', action='store_false', help='Explicit CG-only standalone engineering target')
    parser.add_argument('--mcu', choices=MCUS, default='STM32WBA55CEU6')
    parser.add_argument('--flash-layout', choices=LAYOUTS, default='legacy32', help='compact24 uses 24KiB boot/472KiB app/16KiB SNVMA; requires matched boot+app migration')
    parser.add_argument('--acl-readiness-profile', action='store_true',
                        help='Bounded public ACL fragment admission/radio epoch observation; no radio policy change')
    parser.add_argument('--wba-spi-speed', action='store_true',
                        help='Optimize only the pinned official SPI HAL at O3; bus timing, byte polling, error/timeout semantics unchanged')
    parser.add_argument('--size-optimized-codec', action='store_true',
                        help='Use -Os Opus and LTO without removing sources/features; default for CE, physical timing still required')
    parser.add_argument('--wba-opus-fast-memory', action='store_true', help='Opus-only bounded word COPY/MOVE/CLEAR; unchanged audio and system libc')
    parser.add_argument('--wba-opus-wide-mul', action='store_true', help='Exact16x32 wide products on the fixed M33 CELT profile; unchanged32x32 rounding')
    parser.add_argument('--wba-opus-arm-inline-edsp', action='store_true', help='Pinned official Opus ARM inline DSP arithmetic on CortexM33; same quality parameters, upstream rounding may differ')
    parser.add_argument('--wba-opus-m33-tone-covariance', action='store_true', help='Exact paired16 covariance in actually executed CELT tone detector; unchanged analysis/scaling')
    parser.add_argument('--cpu-detailed-profile', action='store_true', help='Explicit high-frequency17-stage engineering costs; default keeps total CPU plus real PDM/Opus/NOR only')
    parser.add_argument('--cpu-residence-profile', action='store_true',
                        help='DEV capture-scoped thread/IRQ/WFI-envelope wall ledger; not physical CPU duty or current qualification')
    parser.add_argument('--cpu-duty-observer', action='store_true',
                        help='Compact opt-in RTC wall/sleep-gated TIM2 one-second CPU busy upper bound; original WFI retained, no DWT/stage/cache/IRQ tracing')
    parser.add_argument('--reclaim-timing-profile', action='store_true', help='DEV only: bounded consume-scoped NOR busy/poll/program timing; default absent, no persistent logging')
    parser.add_argument('--codec-phase-profile', action='store_true', help='Bounded recording Opus wall-phase observation; no output while capturing')
    parser.add_argument('--wba-opus-celt16', action='store_true',
                        help='Candidate WBA16k/16kbps/20ms officialOpus1.6.1 restricted CELT with9KiB OTA-shared arena; requires pinned optional third_party/opus-wba-1.6.1 and real audio qualification before release')
    parser.add_argument('--firmware-version',type=lambda s:int(s,0),default=0x00010100)
    parser.add_argument('--diag-flash-log', action='store_true', help='Temporary reset/fault journal in the unused external NOR F000 sector; default off')
    parser.add_argument('--update-public-key',type=Path,help='Raw 64-byte P-256 X||Y public trust anchor')
    parser.add_argument('--update-key-id',type=lambda s:int(s,0),default=0)
    parser.add_argument('--incremental', action='store_true', help='Reuse objects only with matching flags, source, headers and object digest')
    parser.add_argument('--lto-partition', choices=('balanced','one'), default='balanced',
                        help='LTO link partition model; one can reduce CE image size without dropping features')
    parser.add_argument('--speaker-pcm-streaming',action='store_true',help='Explicitly retain the portable512-frame PCM streaming API/FIFO; current CE product controls use finite cues only')
    parser.add_argument('--compact-ble-amm',action='store_true',help='DEV opt-in: reclaim unused logical timer quota; physical fragmentation/burst capacity remains unqualified')
    parser.add_argument('--external-bond-store-nor-only', action='store_true', help='DEV only: restore existing external BND1 without internal SNVMA')
    parser.add_argument('--external-bond-store-provision', action='store_true', help='Explicit DEV new-board profile: create identity only when both full bond banks are blank')
    parser.add_argument('--external-bond-store-migrate', action='store_true',
                        help='DEV existing-device migration to external NOR; keeps internal16KiB until matched layout qualification')
    parser.add_argument('--skip-native-tests', action='store_true',
                        help='Compile/link a candidate without running portable host tests; result is build-only, not software acceptance')
    parser.add_argument('--ui-resources', type=Path,
                        help='Build with a candidate UI directory containing profile.json, ui-partition.bin and its resource contract, without activating the shared bank')
    parser.add_argument('--panel-software-spi', action='store_true',
                        help='Use the board software SPI transport')
    parser.add_argument('--panel-startup-readback', action='store_true',
                        help='Opt-in engineering status/RAM readback and failed-activation BUSY edge trace; requires software SPI')
    parser.add_argument('--panel-exclusive-spi', action='store_true',
                        help='Defer IMU SPI until the complete panel transaction releases the shared bus; software SPI only')
    parser.add_argument('--panel-defer-imu-start', action='store_true',
                        help='Isolate first panel startup before any IMU SPI traffic or clock/data AF handoff; requires exclusive software SPI')
    parser.add_argument('--panel-isolation-refreshes', type=int, default=1,
                        help='Number of actual refresh transactions before deferred IMU starts, 1..8; engineering startup isolation has a 20s idle fallback')
    parser.add_argument('--panel-staged-mode2-power', action='store_true',
                        help='Power clock/analog with C0 before ordinary CF/FF; requires exclusive software SPI')
    parser.add_argument('--panel-sense-power', action='store_true',
                        help='Engineering-only VCI/HV audit after C0; disabled in normal refresh; requires staged power')
    parser.add_argument('--panel-stuck-busy-audit', action='store_true',
                        help='One ready-timeout status probe before any panel command; install only over a confirmed nonvisible 0x15 hang')
    parser.add_argument('--panel-start-retry', action='store_true',
                        help='One ready/RAM-qualified activation retry after a missed visible start; requires software SPI readback and exclusive bus')
    parser.add_argument('--panel-window-repair', action='store_true',
                        help='Repair a stable mismatching old/current RAM window once before the single activation retry; requires --panel-start-retry')
    parser.add_argument('--panel-status-gate', action='store_true',
                        help='Require 20ms repeatable internal ready before non-recording visible activations; bounded 100ms foreground wait; requires --panel-start-retry')
    parser.add_argument('--panel-idle-clock-divider', type=int, choices=(1,4,16), default=1,
                        help='Translated panel GPIO timing-margin diagnostic during idle panel transactions only; capture/playback retain original timing')
    parser.add_argument('--panel-passive-trace', action='store_true',
                        help='Bounded post-transaction BUSY sample log; no additional panel reads or completion qualification')
    parser.add_argument('--panel-low-slew', action='store_true',
                        help='Use low GPIO output slew for EPD SCK/MOSI/DC/CS only; bit periods and command sequence remain unchanged')
    parser.add_argument('--panel-open-drain', action='store_true',
                        help='Withdrawn comparison; rejected because the V1.1 EPD U3 TXB0104 requires push-pull drivers')
    parser.add_argument('--shared-spi-gpio', action='store_true',
                        help='Use mode-0 GPIO transactions for the IMU as well as the panel; requires software SPI')
    parser.add_argument('--panel-full-refresh-only', action='store_true',
                        help='Screen recovery candidate: Mode-1 full refresh only, no fast-temperature preset or Mode-2 rearm')
    parser.add_argument('--panel-vendor-quick-full', action='store_true',
                        help='Compile supplier register-LUT menu quick-full; inactive until a real RESET callback is bound; physical qualification pending')
    parser.add_argument('--panel-vendor-quick-full-software-reset', action='store_true',
                        help='Explicit unqualified supplier LUT experiment using0x12; no hardware RESET or optical qualification claim')
    parser.add_argument('--power-profile',type=Path,help='Explicit measured/reworked battery and charger qualification JSON; absent keeps unsafe/unverified inputs disabled')
    parser.add_argument('--development-ota-ignore-power',action='store_true',
                        help='Owner-authorized development only: ignore OTA battery/charger admission; raw telemetry and all other OTA gates remain unchanged; never a release-qualified build')
    parser.add_argument('--battery-linear-estimate',action='store_true',
                        help='Owner opt-in: nominal 100k/68k raw ADC with fresh VREF and ~2850..4150mV display estimate; no SOC/OTA qualification')
    parser.add_argument('--battery-raw-diagnostic',action='store_true',
                        help='Engineering raw ADC requires a verified divider within ADC range; cell/SOC/OTA qualification unchanged')
    parser.add_argument('--recording-audio-provenance-source',default=None,
                        help='Explicit exact40hex image source: normal timeline captures retain original-bound microphone processing identity; requires matching schema5 Type before install')
    parser.add_argument('--microphone-dual-calibration',type=Path,default=None,
                        help='Exact saved non-synthetic known-source calibration JSON; its SHA/UID bind recorded directional output, never acoustic qualification')
    parser.add_argument('--microphone-dual-pair-source', default=None,
                        help='Explicit finite engineering paired-capture profile: exact40hex source commit; requires dual probe, CE and BLE; normal audio unchanged')
    parser.add_argument('--microphone-dual-probe', action='store_true', help='Observe bounded synchronous pairs during an ordinary recording; output remains LEFT unless calibrated dual configuration is explicit')
    parser.add_argument('--microphone-dual-delay-q8', type=int, default=None,
                        help='Explicit dual delay-and-sum candidate; positive delays LEFT, 1/256 PCM sample. Requires acoustic calibration; no automatic voice selection.')
    parser.add_argument('--microphone-dual-right-gain-q15', type=int, default=None,
                        help='Fixed right-microphone calibration trim 16384..65535; not AGC')
    parser.add_argument('--microphone-dual-invert-right', action='store_true',
                        help='Explicit measured right-channel polarity correction')
    parser.add_argument('--microphone-gain', type=int, default=1,
                        help='Fixed pre-codec microphone gain, 1..128; uncalibrated engineering setting, default remains 1')
    parser.add_argument('--experimental-stop1',action='store_true',help='Compile unqualified Stop1 engineering path; only with BLE, not a release or physical acceptance')
    parser.add_argument('--automatic-stop1',action='store_true',help='Enable daily idle Stop1 using the existing product, IRQ and radio admission')
    parser.add_argument('--hardware-source-root',type=Path,
                        default=ROOT.parent/'Companion-Hardware/electronics/companion-v1.1-2026-09-19',
                        help='Read-only hardware inputs; explicit path supports an immutable source checkout')
    args = parser.parse_args()
    if args.product == 'capture': args.screen_disabled = True
    if not args.current_recipe:
        print('Direct legacy defaults retired. Use the matched current entry:\n'
              'python C:/Users/Billy/Desktop/Denzic/Companion/tools/build_current_firmware.py --show\n'
              'For a new build, specify --firmware-version <version> at that entry.', file=sys.stderr)
        return 2
    try: audio_profile=resolve_audio_profile(args)
    except (ValueError,OSError,json.JSONDecodeError) as error: parser.error(str(error))
    if args.panel_vendor_quick_full_software_reset and not args.panel_vendor_quick_full:
        parser.error('--panel-vendor-quick-full-software-reset requires --panel-vendor-quick-full')
    if args.battery_linear_estimate: args.battery_raw_diagnostic=True
    if args.panel_open_drain:
        parser.error('--panel-open-drain is unsupported on Companion V1.1: EPD U3 is TXB0104, not TXS0104E; FW119 failed and was withdrawn')
    if args.panel_startup_readback and not args.panel_software_spi:
        parser.error('--panel-startup-readback requires --panel-software-spi')
    if args.panel_exclusive_spi and not args.panel_software_spi:
        parser.error('--panel-exclusive-spi requires --panel-software-spi')
    if args.panel_defer_imu_start and not args.panel_exclusive_spi:
        parser.error('--panel-defer-imu-start requires --panel-exclusive-spi')
    if not 1 <= args.panel_isolation_refreshes <= 8:
        parser.error('--panel-isolation-refreshes must be in 1..8')
    if args.panel_isolation_refreshes != 1 and not args.panel_defer_imu_start:
        parser.error('--panel-isolation-refreshes requires --panel-defer-imu-start')
    if args.panel_staged_mode2_power and not args.panel_exclusive_spi:
        parser.error('--panel-staged-mode2-power requires --panel-exclusive-spi')
    if args.panel_sense_power and not (args.panel_staged_mode2_power and args.panel_startup_readback):
        parser.error('--panel-sense-power requires --panel-staged-mode2-power and --panel-startup-readback')
    if args.panel_stuck_busy_audit and not (args.panel_startup_readback and args.panel_exclusive_spi):
        parser.error('--panel-stuck-busy-audit requires --panel-startup-readback and --panel-exclusive-spi')
    if args.panel_start_retry and not (args.panel_startup_readback and args.panel_exclusive_spi):
        parser.error('--panel-start-retry requires --panel-startup-readback and --panel-exclusive-spi')
    if args.panel_window_repair and not args.panel_start_retry:
        parser.error('--panel-window-repair requires --panel-start-retry')
    if args.panel_status_gate and not args.panel_start_retry:
        parser.error('--panel-status-gate requires --panel-start-retry')
    if args.panel_idle_clock_divider != 1 and not args.panel_software_spi:
        parser.error('--panel-idle-clock-divider requires --panel-software-spi')
    if args.panel_low_slew and not args.panel_software_spi:
        parser.error('--panel-low-slew requires --panel-software-spi')
    if args.shared_spi_gpio and not args.panel_software_spi:
        parser.error('--shared-spi-gpio requires --panel-software-spi')
    geometry = for_mcu(args.mcu, args.flash_layout)
    if args.microphone_dual_pair_source is not None and (not re.fullmatch(r'[0-9a-f]{40}',args.microphone_dual_pair_source) or
        not args.microphone_dual_probe or not args.with_ble or geometry.flash_kib!=512):
        parser.error('Finite paired capture requires exact lowercase40hex source, dual probe, CE and BLE')
    if not 1 <= args.microphone_gain <= 128:
        parser.error('--microphone-gain must be in 1..128')
    if args.microphone_dual_delay_q8 is not None and not -2048 <= args.microphone_dual_delay_q8 <= 2048:
        parser.error('--microphone-dual-delay-q8 must be in -2048..2048')
    if not 16384 <= args.microphone_dual_right_gain_q15 <= 65535:
        parser.error('--microphone-dual-right-gain-q15 must be in 16384..65535')
    if args.microphone_dual_delay_q8 is None and (args.microphone_dual_invert_right or args.microphone_dual_right_gain_q15 != 32768):
        parser.error('Dual trim/polarity requires explicit --microphone-dual-delay-q8')
    if args.external_bond_store_migrate and (not args.with_ble or geometry.flash_kib != 512 or args.update_key_id != 0x44455631):
        parser.error('--external-bond-store-migrate is a DEV-key CE BLE candidate, not a production at-rest security qualification')
    if args.external_bond_store_nor_only and (not args.with_ble or geometry.flash_kib != 512 or args.update_key_id != 0x44455631 or args.external_bond_store_migrate):
        parser.error('NOR-only is a separate DEV CE BLE profile; do not mix it with the internal migration bridge')
    if args.external_bond_store_provision and not args.external_bond_store_nor_only:
        parser.error('New-board provisioning requires the explicit NOR-only DEV profile')
    if not geometry.nvm_bytes and not args.external_bond_store_nor_only:
        parser.error('NVM0 requires NOR-only persistence; SNVMA must never write reclaimed App pages')
    if args.compact_ble_amm and (not args.with_ble or args.update_key_id != 0x44455631):
        parser.error('Compact BLE AMM is a DEV-only unqualified RAM candidate')
    size_optimized = args.size_optimized_codec or geometry.flash_kib == 512
    if geometry.flash_kib == 512 and not args.with_ble:
        parser.error('--mcu STM32WBA55CEU6 requires the relocated --with-ble product target')
    validate_generated_header()
    if args.automatic_stop1: args.experimental_stop1=True
    if args.experimental_stop1 and not args.with_ble:
        parser.error('--experimental-stop1 requires the WBA BLE/LPM target')
    if not 0<args.firmware_version<=0xFFFFFFFF:
        parser.error('--firmware-version must be a nonzero uint32')
    if args.diag_flash_log and (args.cpu_residence_profile or not args.with_ble):
        parser.error('--diag-flash-log requires BLE and CPU residence tracing disabled')
    if args.cpu_duty_observer and (args.cpu_residence_profile or not args.with_ble):
        parser.error('--cpu-duty-observer requires BLE and legacy CPU residence tracing disabled')
    if bool(args.update_public_key)!=(0<args.update_key_id<=0xFFFFFFFF):
        parser.error('Specify both --update-public-key and a nonzero uint32 --update-key-id')
    if args.with_ble and not args.update_public_key:
        parser.error('The BLE product requires its existing OTA trust anchor: --update-public-key and --update-key-id; refusing an update-disabled replacement')
    sdk, out = args.sdk.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    log = out / 'build.log'; log.write_text('', encoding='utf-8')
    result = {'schema': 'companion.wba.v11.board-package.v1', 'result': 'FAIL',
              'mcu': geometry.mcu, 'internal_flash_geometry': geometry.receipt(),
              'codec_optimization': {'opus': '-Os' if size_optimized else '-O3',
                                     'application_16khz': 'RESTRICTED_LOWDELAY',
                                     'complexity_16khz': 0,
                                     'pdm': '-O3',
                                     'resource_cpu': '-O3',
                                     'celt': '-O3',
                                     'lto': size_optimized, 'sources_and_features_removed': False,
                                     'physical_realtime_timing': 'NOT_RUN'},
              'board': 'V1.1 2026-09-19',
              'image_role': 'INTERACTION_PREHARDWARE_NOT_RELEASE', 'hardwareAcceptance': 'NOT_RUN',
              'fullChainAcceptance': 'NOT_RUN', 'flashed': False, 'sdk_commit': SDK_COMMIT,
              'sdk_modules': MODULES, 'trustzone': 'disabled; no option bytes changed',
              'load_address': f'0x{geometry.app_address:08X}' if args.with_ble else '0x08000000',
              'firmware_version':args.firmware_version,
              'battery_raw_diagnostic_enabled':args.battery_raw_diagnostic,
              'development_ota_power_unrestricted':args.development_ota_ignore_power,
              'battery_linear_estimate_enabled':args.battery_linear_estimate,
              'product_ble_linked': False, 'product_codec3_recording_linked': True,
              'product_interaction_runtime_linked': True,
              'panel_initialization_enabled': True,
              'panel_transaction_driver': 'SSD1681 full/partial; explicit software reset only, physical refresh unqualified',
              'panel_reset_mode': 'SOFTWARE_ONLY_NO_POWER_CYCLE',
              'panel_vendor_quick_full_compiled': args.panel_vendor_quick_full,
              'panel_vendor_quick_software_reset_compiled': args.panel_vendor_quick_full_software_reset,
              'panel_vendor_quick_full_requires_hardware_reset': True,
              'screen_power_switch_available': False,
              'panel_bus': 'SOFTWARE_SPI_ENGINEERING_AUDIT' if args.panel_software_spi else 'SPI1_HARDWARE',
              'panel_startup_readback_enabled': args.panel_startup_readback,
              'panel_exclusive_spi_enabled': args.panel_exclusive_spi,
              'panel_defer_imu_start_enabled': args.panel_defer_imu_start,
              'panel_isolation_refreshes': args.panel_isolation_refreshes,
              'panel_isolation_idle_timeout_ms': 20000,
              'panel_staged_mode2_power_enabled': args.panel_staged_mode2_power,
              'panel_power_sensing_enabled': args.panel_sense_power,
              'panel_stuck_busy_audit_enabled': args.panel_stuck_busy_audit,
              'panel_start_retry_enabled': args.panel_start_retry,
              'panel_window_repair_enabled': args.panel_window_repair,
              'panel_status_gate_enabled': args.panel_status_gate,
              'panel_idle_clock_divider': args.panel_idle_clock_divider,
              'panel_passive_trace_enabled': args.panel_passive_trace,
              'panel_low_slew_enabled': args.panel_low_slew,
              'panel_open_drain_enabled': args.panel_open_drain,
              'panel_stuck_busy_audit_previous_command': '15' if args.panel_stuck_busy_audit else None,
              'panel_vci_detect_floor_mv': 2300 if args.panel_sense_power else None,
              'shared_spi_gpio_enabled': args.shared_spi_gpio,
              'imu_bus': 'SOFTWARE_SPI_MODE0' if args.shared_spi_gpio else 'SPI1_HARDWARE_MODE0',
              'panel_refresh_policy': 'MODE1_FULL_ONLY_RECOVERY' if args.panel_full_refresh_only else 'FULL_FAST_PARTIAL',
              'microphone_default_sink': 'Opus16_COP1_NOR_journal_when_mounted',
              'microphone_dual_processing': {
                  'probe_enabled': args.microphone_dual_probe,
                  'session_policy': 'VOICE_ONLY_MEETING_LEFT_PREPARE_SNAPSHOT',
                  'boot_and_pair_diagnostic_output': 'LEFT',
                  'per_recording_durable_processing_metadata': False,
                  'enabled': args.microphone_dual_delay_q8 is not None,
                  'algorithm': 'CALIBRATED_FIXED_DELAY_AND_SUM' if args.microphone_dual_delay_q8 is not None else 'LEFT_MONO_BASELINE',
                  'delay_q8': args.microphone_dual_delay_q8,
                  'right_gain_q15': args.microphone_dual_right_gain_q15,
                  'invert_right': args.microphone_dual_invert_right,
                  'physical_calibration': 'NOT_RUN',
                  'physical_noise_reduction': 'NOT_QUALIFIED',
                  'speaker_identity_extraction': False},
              'microphone_gain': {'linear': args.microphone_gain,
                                  'q15': args.microphone_gain * 32768,
                                  'stage': 'PDM_TO_PCM_BEFORE_OPUS',
                                  'physical_calibration': 'NOT_RUN',
                                  'automatic_gain_control': False},
              'recording_format': 'codec=3 COP1 16kHz mono 16kbps CBR 20ms; physical timing NOT_RUN',
              'segmented_directory': {'source_compiled': True, 'runtime_active': False,
                                      'live_capacity': 64, 'wire_advertised': False,
                                      'preerase_allocator_compiled': True,
                                      'remaining': 'V2 continuous capture/session anchor/NOR priority binding/GATT integration'},
              'stack_reserved_bytes': 21504 if not geometry.nvm_bytes else 24576,
              'product':args.product,
              'screen_enabled':not args.screen_disabled,
              'periodic_uart_diagnostics':args.periodic_uart_diagnostics,
              'low_power': {'stop1_compiled':args.experimental_stop1,'board_qualified':False,
                            'mode':'STOP1_AUTOMATIC' if args.automatic_stop1 else ('EXPERIMENTAL_STOP1' if args.experimental_stop1 else 'WFI_STOP1_DISABLED')},
              'ota_protocol':'companion_simple_ota_v3',
              'remaining': ['Current screen power switch disabled by hardware rework; software-reset-only physical panel validation',
                            'Battery divider and charger pull-up confirmation',
                            'Measured SAI/PDM clocks, raw channel order and concurrent audio continuity',
                            'WBA simple full-package OTA reboot and interrupted-install physical validation',
                            'WBA BLE pairing/NVM/disconnect-resume physical validation' if args.with_ble else 'WBA BLE/NVM/transfer not linked in this build',
                            'Actual microphone/Opus/NOR/radio concurrency timing, RAM/stack high-water and RTC/Stop power',
                            'Stop1 and RTC time retention implemented in software; real reset/clock continuity/power remain unqualified',
                            'Real-board full-chain accuracy acceptance and blocking owner handoff']}
    try:
        hardware=args.hardware_source_root.resolve()
        if not hardware.is_dir():raise RuntimeError('Hardware source inputs are unavailable: '+str(hardware))
        result['hardware_source_sha256']={p.name:digest(p) for p in sorted(hardware.iterdir()) if p.is_file()}
        result['power_profile']=write_power_profile(out,args.power_profile)
        audio_identity_header=write_audio_profile_identity(out,audio_profile)
        result['recording_audio_profile']={**audio_profile,'containerSchema':5 if audio_profile['enabled'] else None,
            'identityHeaderSha256':digest(audio_identity_header) if audio_identity_header else None,
            'receiverCapabilityBit':512 if audio_profile['enabled'] else None,'installed':False}
        resource_dir = args.ui_resources.resolve() if args.ui_resources else ROOT/'.cache/wba-product-resources'
        profile_path=resource_dir/'profile.json'
        profile=json.loads(profile_path.read_text())
        resource_image=profile_path.parent/'ui-partition.bin'
        resource_header = resource_dir/'companion_wba_resource_contract.h' if args.ui_resources else APP/'runtime/generated/companion_wba_resource_contract.h'
        contract=resource_header.read_text()
        resource_includes=[resource_dir] if args.ui_resources else []
        external_ui=bool(profile.get('externalUi'))
        result['external_ui_resources']=profile.get('externalUi')
        if external_ui:
            ui_header=resource_dir/'companion_wba_external_ui.h'
            if digest(ui_header).upper()!=profile['externalUi']['headerSha256'].upper():
                raise RuntimeError('External UI metadata differs from its bank')
            result['recording_ui_lossless_pack']={'storage':'EXTERNAL_NOR','internalAtlasBytes':0}
        else:
            compact_dir=out/'recording-ui-packed'
            result['recording_ui_lossless_pack']=compact_recording_ui(resource_dir,compact_dir)
            resource_includes=[compact_dir,*resource_includes]
        if f'"{profile["resourceId"]}"' not in contract:
            raise RuntimeError('Generated resource contract does not match the bank profile')
        if digest(resource_image).upper()!=profile['uiPartitionSha256'].upper():
            raise RuntimeError('UI image and profile identity differ; rebuild WBA resources')
        resource_geometry=resource_geometry_from_profile(profile,resource_image.stat().st_size)
        for source,expected in profile['sourceSha256'].items():
            if digest(ROOT/source).upper()!=expected.upper():
                raise RuntimeError(f'WBA resource source changed: {source}')
        result['ui_resource_profile']={k:profile[k] for k in ('generation','profileRevision','resourceId','uiPartitionSha256','uiPartitionBytes')}
        result['flash_geometry']=resource_geometry
        result['screen_face_cache'] = inspect_face_cache(resource_image,
            face_cache_capacity(APP/'runtime/companion_renderer.h'), int(profile['generation']))
        if not result['screen_face_cache']['cacheCapacityFits']:
            raise RuntimeError('Exact UI bank exceeds bounded clean-face RAM cache; do not drop states or render a truncated face')
        public_key=args.update_public_key.read_bytes() if args.update_public_key else bytes(64)
        if len(public_key)!=64 or (args.update_public_key and not any(public_key)):
            raise RuntimeError('Update public key must be exactly 64 nonzero raw X||Y bytes')
        trust_header=out/'wba_update_trust_anchor.h'
        trust_header.write_text('#ifndef WBA_UPDATE_TRUST_ANCHOR_H\n#define WBA_UPDATE_TRUST_ANCHOR_H\n#include <stdint.h>\n'
            +f'#define COMP_WBA_UPDATE_KEY_ID {args.update_key_id}u\n'
            +'static const uint8_t comp_wba_update_public_key[64] = {'+','.join(f'0x{b:02x}' for b in public_key)+'};\n#endif\n',encoding='ascii')
        result['update_trust_anchor']={'key_id':args.update_key_id,'public_key_sha256':hashlib.sha256(public_key).hexdigest(),
                                      'enabled':bool(args.with_ble and args.update_public_key)}
        prepare_sdk(sdk, args.bootstrap_sdk, out, log)
        if args.with_ble:
            if args.bootstrap_sdk:
                run(['git','sparse-checkout','add','--skip-checks','Utilities','Projects/Common',
                     'Projects/NUCLEO-WBA55CG/Applications/BLE/BLE_p2pServer','Middlewares/ST/STM32_WPAN'],sdk,log)
                run(['git','submodule','update','--init','--depth','1','Middlewares/ST/STM32_WPAN'],sdk,log)
            if run(['git','rev-parse','HEAD'],sdk/'Middlewares/ST/STM32_WPAN',log).strip()!=WPAN_COMMIT:
                raise RuntimeError('WBA radio/host identity mismatch')
            if run(['git','diff','--name-only','HEAD','--','.'],sdk/'Middlewares/ST/STM32_WPAN',log).strip() or \
               run(['git','diff','--name-only','HEAD','--','Utilities','Projects/Common',
                    'Projects/NUCLEO-WBA55CG/Applications/BLE/BLE_p2pServer'],sdk,log).strip():
                raise RuntimeError('Modified pinned BLE SDK sources')
        if args.skip_native_tests:
            result['native_tests'] = 'NOT_RUN'
            print('Portable host tests not run; compiling a build-only candidate.')
        else:
            print(native(out, log, resource_includes, resource_geometry), end='')
            result['native_tests'] = 'PASS'
        cc = shutil.which('arm-none-eabi-gcc')
        if cc is None:
            raise RuntimeError('Arm GNU toolchain missing')
        result['compiler'] = run([cc, '--version'], out, log).splitlines()[0]
        hal = sdk / 'Drivers/STM32WBAxx_HAL_Driver'
        cmsis = sdk / 'Drivers/CMSIS'
        device = cmsis / 'Device/ST/STM32WBAxx'
        opus = ROOT / ('third_party/opus-wba-1.6.1' if args.wba_opus_celt16 else 'third_party/opus')
        if args.wba_opus_celt16:
            if geometry.mcu != 'STM32WBA55CEU6':
                raise RuntimeError('Restricted WBA codec candidate is qualified only for the CE product profile')
            pinned=json.loads((opus/'companion-profile.json').read_bytes())
            if pinned.get('upstream_version')!='1.6.1' or pinned.get('upstream_archive_sha256')!='6ffcb593207be92584df15b32466ed64bbec99109f007c82205f0194572411a1':
                raise RuntimeError('WBA codec dependency differs from the locked official source')
            for relative,expected in pinned['files'].items():
                if digest(opus/relative)!=expected:
                    raise RuntimeError('Pinned WBA codec profile source differs: '+relative)
            # Referencing the immutable authored raster is equivalent only
            # while the current face hook preserves it. A future procedural
            # replacement must provide its own reconstructible identity.
            # P223 retains the exact no-redraw hook, changing only the closed
            # eye map for spatial tilt to select authored directional faces.
            # Keep explicit immutable identities, not an unrestricted bypass.
            if digest(APP/'runtime/companion_pet_face.c') not in (
                '6a9cae100a4894c6dd1b187ae28d231490566ebc40e4d417371969f3a9737b29',
                '942ff1edad516db13defc58526bf49b741394e95c9ac842ad4a818aaac449bf8'):
                raise RuntimeError('Face reference profile requires the pinned authored-raster-preserving hook')
            result['codec_profile']={'name':'wba16-restricted-celt-1.6.1','sample_rate_hz':16000,'bitrate_bps':16000,
                'frame_ms':20,'channels':1,'encoder_arena_bytes':13136,'encoder_state_capacity_bytes':5456,
                'dma_bytes':7680,'ota_borrow_limit_bytes':8744,'physical_qualified':False,
                'upstream_archive_sha256':pinned['upstream_archive_sha256'],
                'specialization':pinned.get('specialization')}
            result['codec_optimization'].update(application_16khz='RESTRICTED_CELT',
                opus_setup='-O3 (fixed CELT Opus entry and product PCM accumulator)',
                unused_silk_hybrid_encoding_excluded=True)
            result['screen_face_storage']={'mode':'immutable_resource_references',
                'identity_bytes_each':112,'blink_glyph_bytes_each':256,
                'committed_and_staging_controller_frames_retained':True,
                'committed_representation':'lossless_row_delta_rle_canonical_huffman',
                'committed_capacity_bytes':1280,'staging_bytes':5000,
                'physical_timing_qualified':False}
        opus_manifest = opus / 'companion_opus_encode_sources.mk'
        opus_sources = [opus / name for name in re.findall(r'\$\(OPUS_ROOT\)/([^\s]+\.c)', opus_manifest.read_text())]
        if not opus_sources or len(opus_sources) != len(set(opus_sources)):
            raise RuntimeError('Invalid existing Opus source manifest')
        includes = [out,*resource_includes,*INCLUDES, hal / 'Inc', cmsis / 'Include', device / 'Include',
                    opus, *(opus / d for d in ('include', 'celt', 'silk', 'silk/fixed', 'src'))]
        flags = ['-mcpu=cortex-m33', '-mthumb', '-mfpu=fpv5-sp-d16', '-mfloat-abi=hard',
                 f'-DCOMP_V11_DIAG_FLASH_ENABLED={int(args.diag_flash_log)}',
                 f'-DCOMPANION_WBA_ACL_READINESS_PROFILE={int(args.acl_readiness_profile)}',
                 f'-DCOMPANION_WBA_CPU_RESIDENCE_PROFILE={int(args.cpu_residence_profile)}',
                 f'-DCOMPANION_WBA_CPU_DUTY_OBSERVER={int(args.cpu_duty_observer)}',
                 f'-DCOMPANION_WBA_RECLAIM_TIMING={int(args.reclaim_timing_profile)}',
                 '-DCOMPANION_FINE_DURATION_CLOCK=1',
                 f'-DCOMPANION_WBA_CPU_DETAILED_PROFILE={int(args.cpu_detailed_profile)}',
                 f'-DCOMPANION_WBA_BATTERY_RAW_DIAGNOSTIC={int(args.battery_raw_diagnostic)}',
                 f'-DCOMPANION_WBA_OTA_DEV_IGNORE_POWER={int(args.development_ota_ignore_power)}',
                 f'-DCOMPANION_WBA_BATTERY_LINEAR_ESTIMATE={int(args.battery_linear_estimate)}',
                 f'-DCOMP_V11_PANEL_SOFTWARE_SPI={int(args.panel_software_spi)}',
                 f'-DCOMP_V11_PANEL_STARTUP_READBACK={int(args.panel_startup_readback)}',
                 f'-DCOMP_V11_PANEL_EXCLUSIVE_SPI={int(args.panel_exclusive_spi)}',
                 f'-DCOMP_V11_PANEL_DEFER_IMU_START={int(args.panel_defer_imu_start)}',
                 f'-DCOMP_V11_PANEL_ISOLATION_REFRESHES={args.panel_isolation_refreshes}u',
                 f'-DCOMP_V11_PANEL_STAGED_MODE2_POWER={int(args.panel_staged_mode2_power)}',
                 f'-DCOMP_V11_PANEL_SENSE_POWER={int(args.panel_sense_power)}',
                 f'-DCOMP_V11_PANEL_STUCK_BUSY_AUDIT={int(args.panel_stuck_busy_audit)}',
                 f'-DCOMP_V11_PANEL_START_RETRY={int(args.panel_start_retry)}',
                 f'-DCOMP_V11_PANEL_WINDOW_REPAIR={int(args.panel_window_repair)}',
                 f'-DCOMP_V11_PANEL_STATUS_GATE={int(args.panel_status_gate)}',
                 f'-DCOMP_V11_PANEL_IDLE_CLOCK_DIVIDER={args.panel_idle_clock_divider}',
                 f'-DCOMP_V11_PANEL_PASSIVE_TRACE={int(args.panel_passive_trace)}',
                 f'-DCOMP_V11_PANEL_LOW_SLEW={int(args.panel_low_slew)}',
                 f'-DCOMP_V11_PANEL_OPEN_DRAIN={int(args.panel_open_drain)}',
                 f'-DCOMP_V11_SHARED_SPI_GPIO={int(args.shared_spi_gpio)}',
                 f'-DCOMP_V11_PANEL_FULL_REFRESH_ONLY={int(args.panel_full_refresh_only)}',
                 f'-DCOMP_V11_PANEL_VENDOR_QUICK_FULL={int(args.panel_vendor_quick_full)}',
                 f'-DCOMP_V11_PANEL_VENDOR_QUICK_SOFTWARE_RESET={int(args.panel_vendor_quick_full_software_reset)}',
                 f'-DCOMP_WBA_INTERNAL_FLASH_KIB={geometry.flash_kib}u',
                 f'-DCOMP_WBA_BOOT_FLASH_KIB={geometry.boot_bytes // 1024}u',
                 f'-DCOMP_WBA_INTERNAL_NVM_KIB={geometry.nvm_bytes // 1024}u',
                 f'-DCOMPANION_WBA_EXPERIMENTAL_STOP1={int(args.experimental_stop1)}',
                 f'-DCOMPANION_WBA_AUTOMATIC_STOP1={int(args.automatic_stop1)}',
                 f'-DCOMPANION_PRODUCT_CAPTURE={int(args.product=="capture")}',
                 f'-DCOMPANION_WBA_SCREEN_ENABLED={int(not args.screen_disabled)}',
                 f'-DCOMPANION_WBA_PERIODIC_DIAGNOSTICS={int(args.periodic_uart_diagnostics)}',
                 f'-DCOMPANION_WBA_APP_VERSION={args.firmware_version}u',
                 f'-DCOMPANION_WBA_MICROPHONE_GAIN_Q15={args.microphone_gain * 32768}u',
                 f'-DCOMPANION_WBA_AUDIO_PROFILE={int(audio_profile["enabled"])}',
                 *(['-DCOMPANION_WBA_DUAL_MIC_PROBE=1'] if args.microphone_dual_probe else []),
                 *(['-DCOMPANION_WBA_DUAL_PAIR_CAPTURE=1',
                    '-DCOMPANION_DMIC_CAPTURE_SOURCE_BYTES={'+','.join('0x'+args.microphone_dual_pair_source[i:i+2] for i in range(0,40,2))+'}']
                    if args.microphone_dual_pair_source is not None else []),
                 *([f'-DCOMPANION_WBA_DUAL_MIC_DELAY_Q8={args.microphone_dual_delay_q8}',
                    f'-DCOMPANION_WBA_DUAL_MIC_RIGHT_GAIN_Q15={args.microphone_dual_right_gain_q15}u',
                    f'-DCOMPANION_WBA_DUAL_MIC_INVERT_RIGHT={int(args.microphone_dual_invert_right)}']
                   if args.microphone_dual_delay_q8 is not None else []),
                 f'-DCOMP_WBA_NOR_UI_BYTES={resource_geometry["staticBytes"]}u',
                 f'-DCOMP_WBA_NOR_TOTAL_BYTES={resource_geometry["norBytes"]}u',
                 '-DCOMPANION_WBA_RECORDING_UI_PACKED=1',
                 f'-DCOMPANION_WBA_UI_EXTERNAL={int(external_ui)}',
                 '-std=c11', '-Os', '-g3', '-fmax-errors=8', '-ffunction-sections', '-fdata-sections', '-fstack-usage',
                 '-DSTM32WBA55xx', '-DUSE_HAL_DRIVER', '-DCOMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1',
                 '-DCOMPANION_WBA_RESOURCE_PROFILE=1', *(f'-I{p}' for p in includes)]
        if size_optimized:
            flags += ['-flto']
        if args.wba_opus_fast_memory:
            if not args.wba_opus_celt16:
                raise RuntimeError('Opus memory lowering requires the fixed WBA CELT profile')
            flags += ['-DCOMPANION_OPUS_FAST_MEMORY=1']
            result['codec_fast_memory'] = 'Opus-only word copies with bounded tails/overlap, system libc unchanged; physical timing NOT_RUN'
        if args.wba_opus_wide_mul:
            if not args.wba_opus_celt16:
                raise RuntimeError('M33 exact wide multiplication requires the fixed CELT profile')
            flags += ['-DCOMPANION_OPUS_M33_WIDE_MUL=1']
            result['codec_exact_wide_multiply'] = '16x32 products only; original32x32 rounding unchanged; physical timing NOT_RUN'
        if args.wba_opus_arm_inline_edsp:
            if not args.wba_opus_celt16:
                raise RuntimeError('Inline ARM DSP trial requires the fixed WBA CELT profile')
            flags += ['-DOPUS_ARM_INLINE_EDSP=1']
            result['codec_official_arm_inline_edsp'] = 'Pinned upstream ARM arithmetic; codec parameters unchanged, rounding may differ; physical timing/quality NOT_RUN'
        if args.wba_opus_m33_tone_covariance:
            if not args.wba_opus_celt16:
                raise RuntimeError('Exact tone covariance requires the fixed WBA CELT profile')
            flags += ['-DCOMPANION_OPUS_M33_TONE_COVARIANCE=1']
            result['codec_exact_m33_tone_covariance'] = 'Three delayed signed16 covariance sums only, exact original arithmetic, actually executed in complexity0; physical timing NOT_RUN'
        if args.codec_phase_profile:
            if not args.wba_opus_celt16:
                raise RuntimeError('Codec phase observation requires the fixed WBA CELT profile')
            flags += ['-DCOMPANION_WBA_CODEC_PROFILE=1']
            result['codec_phase_profile'] = 'seven contiguous wall phases, SRAM1; includes IRQ; not CPU duty cycle'
        if args.wba_opus_celt16:
            flags += ['-DCOMPANION_OPUS16_WBA_CELT16=1','-DCOMPANION_OPUS16_ENCODER_BYTES=8744u',
                      '-DCOMPANION_OPUS_CELT_ONLY=1','-DCOMP_RUNTIME_WBA_FACE_REFERENCES=1',
                      '-DCOMPANION_WBA_CE_SHARED_CAPTURE=1','-DCOMP_WBA_PACKED_OLD_FRAME=1']
        sources = [*PORTABLE, *(APP / 'recording' / n for n in ('wba_recording_service.c', 'companion_recording_journal.c', 'companion_recording_identity.c', 'companion_segment_catalog.c', 'companion_segment_reserve.c', 'wba_recording_product.c', 'wba_recording_recovery.c', 'wba_recording_pipeline.c', 'wba_segment_discard_preview.c', 'wba_segment_discard_worker.c', 'wba_segment_discard_control.c', 'wba_segment_discard_wire.c', 'wba_segment_storage.c', 'companion_continuous_recording.c', 'companion_segment_audio.c', 'companion_opus16_rt.c', 'companion_silk_live_fast.c')),
                   *opus_sources, PLATFORM / 'board_hal.c', PLATFORM / 'battery_adc.c', PLATFORM / 'main.c', PLATFORM / 'diagnostic_console.c', PLATFORM / 'syscalls.c', PLATFORM / 'microphone_hal.c', PLATFORM / 'product_app.c', PLATFORM / 'product_pet_chat.c', PLATFORM / 'low_power_target.c',
                   PLATFORM / 'memory_target.c', PLATFORM / 'stack_paint.S', PLATFORM / 'clock_target.c',
                   device / 'Source/Templates/system_stm32wbaxx.c',
                   device / 'Source/Templates/gcc/startup_stm32wba55xx.s',
                   *(hal / f'Src/stm32wbaxx_{name}.c' for name in HAL_MODULES)]
        if args.microphone_dual_pair_source is not None:
            sources.append(PLATFORM / 'dual_mic_capture.c')
        result['diag_flash_logging_enabled']=args.diag_flash_log
        result['cpu_duty_observer_enabled']=args.cpu_duty_observer
        result['reclaim_timing_profile_enabled']=args.reclaim_timing_profile
        if args.cpu_duty_observer:
            sources.append(PLATFORM/'cpu_duty_target.c')
        if args.diag_flash_log:
            sources += [PLATFORM/'diag_flash_target.c', APP/'diag_log/diag_flash_journal.c']
        if args.cpu_residence_profile:
            sources.append(PLATFORM / 'cpu_profile_target.c')
            sources.append(PLATFORM / 'reset_witness.c')
            result['cpu_residence_profile']={'enabled':True,'detailed':args.cpu_detailed_profile,'stage_slots':17 if args.cpu_detailed_profile else 3,'clock':'independently ownedTIM2 with RTC sanity',
                'scope':'capture token; thread/IRQ C bodies/WFI nonIRQ envelope; includes instrumentation',
                'physical_cpu_duty_qualified':False,'sleep_current_qualified':False,
                'stop1_supported':False,'output':'cached CPU1 only after capture under original UART gate'}
        if geometry.flash_kib == 512:
            sources.append(PLATFORM / 'ce_reset.S')
        if args.wba_opus_fast_memory:
            sources.append(APP/'recording/companion_opus_memory.c')
        cue_only = geometry.flash_kib == 512 and args.with_ble and not args.speaker_pcm_streaming
        flags += [f'-DCOMP_SPEAKER_CUES_ONLY={int(cue_only)}']
        result['speaker_ram_profile']={'cue_only':cue_only,'fifo_bytes':256 if cue_only else 1024,
            'dma_block_frames':64,'sample_rate':16000,'product_pcm_streaming_endpoint':False,'physical_qualified':False}
        libraries=[]
        if args.with_ble:
            ble_includes,ble_sources,libraries=ble_configuration(sdk,PLATFORM,args.experimental_stop1)
            # GAP peripheral does not imply GATT server only: phones may send
            # Service Changed indications. The optional candidate retains the
            # official host client while pruning central/advanced features.
            # The pinned peripheral controller archive is never substituted.
            host_profile='BLE_STACK_BASIC_FEATURES' if args.ble_peer_indications else 'BLE_STACK_PERIPHERAL_ONLY'
            result['ble_stack_profile'] = {
                'host': host_profile,
                'controller': 'LinkLayer_BLE_Peripheral_Only_V3_0.a',
                'gatt_server': True, 'gatt_client': args.ble_peer_indications, 'central': False,
                'peer_indication_confirmation': args.ble_peer_indications,
                'physical_qualified': False,
            }
            flags += [f'-D{host_profile}',f'-DCOMPANION_WBA_PEER_INDICATIONS={int(args.ble_peer_indications)}']
            if args.ble_peer_indications:
                flags += ['-DBLE_FEATURE_CENTRAL_UNUSED=1','-DACI_GAP_SET_BROADCAST_MODE_UNUSED=1']
            flags += [f'-DCOMPANION_WBA_COMPACT_BLE_AMM={int(args.compact_ble_amm)}', f'-DCOMPANION_WBA_EXTERNAL_BOND_STORE={int(args.external_bond_store_migrate or args.external_bond_store_nor_only)}',
                      f'-DCOMPANION_WBA_EXTERNAL_BOND_NOR_ONLY={int(args.external_bond_store_nor_only)}',
                      f'-DCOMPANION_WBA_EXTERNAL_BOND_PROVISION={int(args.external_bond_store_provision)}', '-DCOMPANION_GATT_WBA_HOST','-DCOMPANION_WBA_BLE_LINKED','-DUSE_FULL_LL_DRIVER',
                      '-DPHY_40nm_3_00_a','-DBLE_LL',
                      '-DCOMPANION_RECORDING_SEGMENTED_ONLY=1',
                      '-DCOMP_DIAG_LOG_RING_CAPACITY=16',f'-I{APP / "platform"}',f'-I{APP / "diag_log"}',f'-I{APP / "gatt"}',
                      f'-I{ROOT / "third_party/denzic-platform/ota/embedded/c/include"}',*(f'-I{p}' for p in ble_includes)]
            sources += [*ble_sources,
                APP/'gatt/companion_gatt_stm32wb.c',
                APP/'runtime/companion_link.c',APP/'recording/wba_recording_transfer.c',
                *(APP/'recording'/n for n in ('wba_recording_radio.c','wba_segment_pull.c',
                    'wba_segment_directory.c')),
                APP/'platform/companion_ble_name.c',APP/'diag_log/diag_log.c',APP/'diag_log/diag_log_export.c',
                *(APP/'update'/n for n in ('wba_update_manifest_wire.c','wba_update_p256.c',
                    'wba_simple_package.c','wba_simple_install.c')),
                # Layout 3 uses explicit development formatting. The retained
                # V1-to-V2 migration kernel is not a production adapter.
                APP/'recording/companion_recording_resource_pack.c',
                ROOT/'third_party/denzic-platform/ota/embedded/c/src/denzic_ota_v1.c',
                *(hal/f'Src/stm32wbaxx_{n}.c' for n in ('hal_rtc','hal_rtc_ex','hal_crc','hal_crc_ex','hal_pka','ll_pka'))]
        if args.external_bond_store_migrate or args.external_bond_store_nor_only:
            sources += [APP/'storage/wba_bond_store.c', APP/'storage/wba_bond_seal.c']
        result['ble_ram_budget']={'gatt_values':'schema_derived_with_128B_auto_and_128B_margin', 'compact_amm':args.compact_ble_amm, 'logical_event_shared_capacity_preserved':True, 'physical_allocator_burst_qualified':False}
        result['ble_bond_persistence']={'backend':'EXTERNAL_NOR_ONLY' if args.external_bond_store_nor_only else 'EXTERNAL_NOR_MIGRATE_EXISTING' if args.external_bond_store_migrate else 'ST_INTERNAL_SNVMA',
            'ram_cache_unchanged':True, 'internal_nvm_reclaimed':geometry.nvm_bytes == 0,
            'new_board_provisioning':args.external_bond_store_provision,
            'torn_first_provisioning':'permanent_BPS1_intent_then_verified_BND1_then_complete_before_HOST; compatible_first_torn_writes_retry_without_seal_erase',
            'provisioning_seal':{'relative_offset':0xe000,'bytes':4096,'header_bytes':48,'never_runtime_erased':True,'cryptographic_authority':False},
            'at_rest_security_qualified':False, 'physical_qualified':False}
        tracked = [p for p in sources if p.is_relative_to(APP) or p.is_relative_to(PLATFORM) or p.is_relative_to(ROOT/'third_party')]
        tracked += list(opus.rglob('*.h')) + [opus_manifest]
        tracked += list(PLATFORM.rglob('*.h')) + list(PLATFORM.glob('*.ld')) + list(PLATFORM.rglob('*.json'))
        tracked += [Path(__file__).with_name('wba_ble_target.py'), GEOMETRY_SOURCE,
                    Path(__file__).with_name('wba_flash_geometry.py'),Path(__file__).with_name('wba_resource_geometry.py')]
        for directory in INCLUDES[1:]:
            tracked += list(directory.glob('*.h'))
        tracked += [Path(__file__), ROOT/'tools/compact_wba_recording_ui.py', ROOT/'tools/wba_stack_usage.py', APP / 'board/tests/test_v11_peripherals.c', resource_header, profile_path, resource_image]
        tracked += [trust_header,out/'wba_board_power_profile.h',out/'power-profile.json',ROOT/'tools/wba_power_profile.py',ROOT/'tools/wba_audio_profile.py',ROOT/'tools/dual_mic_calibration_stability.py']
        if audio_identity_header: tracked.append(audio_identity_header)
        if args.power_profile and args.power_profile.resolve().is_relative_to(ROOT):
            tracked += [args.power_profile.resolve()]
        def source_key(path: Path) -> str:
            try:
                return path.relative_to(ROOT).as_posix()
            except ValueError:
                return f'_external-build-output/{path.name}'
        all_headers=set(p for directory in includes for p in directory.rglob('*.h'))
        if args.with_ble:
            all_headers.update(p for directory in ble_includes for p in directory.rglob('*.h'))
            # These include paths are added with BLE flags above. They must
            # participate in both object reuse and the source receipt, too;
            # otherwise an event/header-only change can reuse stale objects.
            for directory in (APP/'platform', APP/'diag_log', APP/'gatt',
                              ROOT/'third_party/denzic-platform/ota/embedded/c/include'):
                all_headers.update(directory.rglob('*.h'))
        tracked += [p for p in all_headers if p.is_relative_to(ROOT)]
        source_hashes = {source_key(p): digest(p) for p in sorted(set(tracked))}
        header_identity=hashlib.sha256(json.dumps({str(p):digest(p) for p in sorted(all_headers)},sort_keys=True).encode()).hexdigest()
        objects = []
        for i, source in enumerate(sources):
            obj = out / f'{i:02d}-{source.stem}.o'
            warnings = ['-Wall', '-Wextra', '-Werror'] if (source.is_relative_to(APP) or source.is_relative_to(PLATFORM)) and not source.is_relative_to(PLATFORM/'ble') else []
            codec_flags = ['-Os' if size_optimized else '-O3', '-DOPUS_BUILD', '-DFIXED_POINT', '-DDISABLE_FLOAT_API', '-DHAVE_CONFIG_H',
                           '-DCOMPANION_SILK_LIVE_FAST=1'] if source.is_relative_to(opus) or source.name == 'companion_opus16_rt.c' else []
            if source.name == 'companion_opus16_rt.c':
                codec_flags += ['-DCOMPANION_OPUS16_WBA_LOWDELAY=1','-DCOMPANION_OPUS16_STDIO_ERRORS=0']
            if source.is_relative_to(opus/'celt'):
                codec_flags += ['-O3']
            if args.wba_opus_celt16 and (source == opus/'src/opus_encoder.c' or
                                        source.name == 'companion_opus16_rt.c'):
                codec_flags += ['-O3']
            if source.name in ('wba_pdm_capture.c','wba_frame_store.c','companion_renderer.c','companion_resources.c',
                               'emote_asset_pack.c','ui_asset_generation.c','screen_framebuffer.c',
                               'screen_presenter_wba.c'):
                codec_flags += ['-O3']
            if args.wba_spi_speed and source.name == 'stm32wbaxx_hal_spi.c':
                codec_flags += ['-O3']
                result['spi_speed_optimization'] = {'file': str(source), 'sourceSha256': digest(source), 'flag': '-O3', 'driverSourceChanged': False, 'physicalTiming': 'NOT_RUN'}
            command=[cc, *flags, *codec_flags, *(['-fno-lto'] if size_optimized and source.name == 'syscalls.c' else []),
                     *warnings, '-c', str(source), '-o', str(obj)]
            identity=hashlib.sha256(json.dumps([command,digest(source),header_identity,result['compiler']]).encode()).hexdigest()
            receipt=obj.with_suffix('.compile.json')
            cached=json.loads(receipt.read_text()) if args.incremental and receipt.exists() and obj.exists() else {}
            if cached.get('identity')!=identity or cached.get('object_sha256')!=digest(obj):
                run(command, out, log)
                receipt.write_text(json.dumps({'identity':identity,'object_sha256':digest(obj)}))
            objects.append(obj)
        elf = out / 'companion-v11-board-bringup.elf'
        image = elf.with_suffix('.bin')
        linker=geometry.linker(PLATFORM) if args.with_ble else PLATFORM / (geometry.mcu + '.ld')
        geometry.validate_linker(linker,standalone=not args.with_ble)
        result['lto_partition']=args.lto_partition if size_optimized else 'NOT_USED'
        # Private callback interposition is supported only for these exact SDK
        # archives. No SDK source/binary edits; same original function executes.
        if args.with_ble:
            for relative,expected in (
                ('ble/stack/lib/stm32wba_ble_stack_full.a','28d4456b81aae8c36f4c80ab4fbc8a758a5acc32acf19c5fdd2bd4887b69e7d9'),
                ('link_layer/ll_cmd_lib/lib/LinkLayer_BLE_Peripheral_Only_V3_0.a','ec3b82950c96b863bb64f51a788b85e8d91f2cb2d2179dd7705a2cf99fa1d6b7')):
                assert digest(args.sdk/'Middlewares/ST/STM32_WPAN'/relative)==expected,'Unreviewed completion callback SDK'
        link_args=[*flags, *([f'-flto-partition={args.lto_partition}'] if size_optimized else []), '-T', str(linker),
             '--specs=nano.specs', '--specs=nosys.specs', '-Wl,--gc-sections', '-Wl,--wrap=SystemInit',
             *(['-Wl,--wrap=ll_intf_acl_data_from_host_to_cntrlr','-Wl,--wrap=ll_hci_init','-Wl,--wrap=LECTRL_Process','-Wl,--wrap=ACL_List_Remove'] if args.with_ble else []),
             f'-Wl,-Map={elf.with_suffix(".map")}', *(str(p) for p in objects),
             '-Wl,--start-group',*(str(p) for p in libraries),'-lm','-Wl,--end-group', '-o', str(elf)]
        response=out/'link.rsp'
        response.write_text('\n'.join('"'+s.replace('\\','/').replace('"','\\"')+'"' for s in link_args),encoding='utf-8')
        previous_lto_reports=lto_report_stamps(elf)
        run([cc,'@'+str(response)],out,log)
        linked_stack_reports=fresh_lto_reports(elf,previous_lto_reports)
        if args.with_ble:
            result['pending_acl_ownership_call_audit']=inspect_pending_acl_ownership(elf)
        if geometry.flash_kib == 512:
            result['sram_inspection'] = inspect_ce_elf(elf)
            if not result['sram_inspection']['writableSectionAddressesValid']:
                raise RuntimeError('CE image uses unsupported SRAM addresses')
        run(['arm-none-eabi-objcopy', '-O', 'binary', str(elf), str(image)], out, log)
        initial_sp, reset_vector = struct.unpack_from('<II', image.read_bytes())
        if not (geometry.valid_stack_pointer(initial_sp) and
                reset_vector & 1 and int(result['load_address'],16) <= (reset_vector & ~1) < (geometry.app_end if args.with_ble else geometry.flash_base + geometry.flash_bytes)):
            raise RuntimeError('Vector table does not match WBA55 flash/RAM geometry')
        if args.with_ble and image.stat().st_size > geometry.app_bytes:
            raise RuntimeError('Application exceeds selected MCU capacity')
        result['vector_table'] = {'initial_sp': hex(initial_sp), 'reset_vector': hex(reset_vector)}
        size = run(['arm-none-eabi-size', str(elf)], out, log)
        (out / 'size.txt').write_text(size, encoding='utf-8'); print(size, end='')
        symbols=run(['arm-none-eabi-nm','--defined-only',str(elf)],out,log)
        addresses={name:int(address,16) for address,kind,name in
                   (line.split() for line in symbols.splitlines() if len(line.split())==3)
                   if name in ('_sstack','_estack','_end','__wrap_SystemInit','__sram1_free_bytes')}
        if not {'_sstack','_estack','_end','__wrap_SystemInit'} <= addresses.keys() or addresses['_sstack']<addresses['_end']:
            raise RuntimeError('Stack paint or reserved RAM geometry missing from linked target')
        startup=run(['arm-none-eabi-objdump','-d','--disassemble=Reset_Handler',str(elf)],out,log)
        if '<__wrap_SystemInit>' not in startup:
            raise RuntimeError('Reset vector did not call the boot stack-paint wrapper')
        (out/'startup-stack-paint.txt').write_text(startup)
        result['memory']={'static_gap_bytes':addresses['_sstack']-addresses['_end'],
            'sram1_free_bytes':addresses.get('__sram1_free_bytes'),
            'physical_sram_bytes':geometry.sram_bytes,
            'physical_sram_regions':geometry.sram_regions,
            'stack_reserved_bytes':addresses['_estack']-addresses['_sstack'],
            'stack_watermark':'boot-painted MSP; idle UART observation; physical values NOT_RUN',
            'stack_warning_free_bytes':1024,
            'static_usage_scope':'per-function compiler estimates, not maximum call-chain/IRQ stack proof'}
        usage=collect_stack_usage(objects,linked_stack_reports)
        (out/'stack-usage.json').write_text(json.dumps(usage,indent=2)+'\n')
        after_hashes = {source_key(p): digest(p) for p in sorted(set(tracked))}
        if source_hashes != after_hashes:
            raise RuntimeError('Sources changed during compilation; rebuild the frozen source before handoff')
        if args.power_profile and digest(args.power_profile)!=result['power_profile']['source_sha256']:
            raise RuntimeError('Electrical qualification changed during compilation')
        if audio_profile['calibrationSha256'] and digest(Path(audio_profile['calibrationPath']))!=audio_profile['calibrationSha256']:
            raise RuntimeError('Calibration input changed during build; no package qualification')
        result.update(result='COMPILED_BUILD_ONLY'  if args.skip_native_tests else 'PASS_PREHARDWARE_SOFTWARE_ONLY', elf_sha256=digest(elf),
                      bin_sha256=digest(image), bin_bytes=image.stat().st_size,
                      source_sha256=source_hashes)
        result['product_ble_linked']=args.with_ble
        if args.with_ble:
            result['sdk_wpan_commit']=WPAN_COMMIT
            result['ble_libraries_sha256']={str(p.relative_to(sdk)):digest(p) for p in libraries}
            result['ble_nvm_region']=f'0x{geometry.app_end:08X}..0x{geometry.flash_base + geometry.flash_bytes:08X}; ' + ('no internal NVM' if not geometry.nvm_bytes else 'ST SNVMA two 8KiB pages')
            result['ble_security']='Encrypted private attributes; Just Works bonding with persisted random identity; ownership/pairing hardware acceptance NOT_RUN'
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        result['error'] = str(error)[:16000]; print(str(error)[:6000], file=sys.stderr)
    finally:
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f'{result["result"]}: {out / "result.json"}')
    return 0 if result['result'] in ('PASS_PREHARDWARE_SOFTWARE_ONLY', 'COMPILED_BUILD_ONLY') else 1

if __name__ == '__main__':
    raise SystemExit(main())
