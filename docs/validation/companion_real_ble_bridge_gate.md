# Companion Real BLE Bridge Gate

Date: 2026-06-29

## Scope

This evidence covers the Companion NUCLEO-WB55RG BLE audio bridge on real hardware. The operator confirmed all hardware is present except IMU and screen, so IMU/display behavior is out of scope for this gate.

## Hardware

- Board: Companion-WB55 / NUCLEO-WB55RG
- ST-LINK SN: 066EFF535570514867221931
- ST-LINK VCP: COM13
- BLE address observed by Type: 0080E127B8EA
- Workflow lock resource: `Companion-WB55,BLE-Companion`
- Board ledger: `aiw board-ledger list` entry `Companion-WB55 board_id=nucleo-wb55rg-stlink-066EFF535570514867221931`

## Versions

- Firmware HEAD: `c31125b Size Companion BLE service callback table`
- Firmware package: `.cache/ota_firmware/companion-ota-nucleo-wb55rg-c31125b-20260629-170753.zip`
- OTA binary: `firmware_ota.bin`, 68240 bytes, SHA-256 `befaeb2611660d9ef9a2a5ef322a0d8a6211993aeb610de9d1983440a8570da3`
- Factory app: `Companion_Nucleo_WB55RG_Bringup_ota_app.hex`, SHA-256 `a49e66cbfd5443538d8c300b5cfa73085d39d9dbddbb806eb581e51c8000f83c`
- Type HEAD used for A1 stats-only smoke: `63f8cd0 Allow BLE one-shot stats-only capture`
- Type HEAD used for A2 stats-only smoke: `20dcc94 Prefer serial recovery for BLE name changes`
- STM32CubeProgrammer: v2.22.0

## Fix Summary

Before the fix, Type could scan, connect, enable the notify CCCD, and send `TYPE:READY:A1`, but Companion did not receive the GATT service events. Firmware readiness stayed at:

`vka1 n=0 t=0 r=0 cw=0 ne=0 nd=0 ss=0 lc=0 cs=0 ls=0`

Root cause: the NUCLEO build still inherited `BLE_CFG_SVC_MAX_NBR_CB=1` while the firmware now registers two service event handlers: VKA1 audio and Companion-native GATT. The second handler wrote past the ST callback table, so VKA1 CCCD/control events were not delivered reliably.

Fix:

- Added NUCLEO `ble_conf.h` overlay with `BLE_CFG_SVC_MAX_NBR_CB=2`.
- Updated `Companion_Pendant.ioc` to match.
- Added static coverage in `tools/verify_companion_gatt_static.py`.
- Added VKA1 readiness diagnostics for notify/control/session state.
- Added Type one-shot stats-only path so hardware smoke proves BLE audio without requiring spoken ASR text.

## Validation

PASS:

- `python .\tools\verify_companion_gatt_static.py`
- `git diff --check`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -Force`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -OtaApp -Force`
- `pwsh -NoProfile -File .\tools\package_ota_firmware.ps1 -Channel development -BoardTarget NUCLEO-WB55RG`
- `cargo test parse_recognizes_embedded_ble_status_with_timeout`
- `cargo test type_heartbeat_prefers_no_response_when_available`
- `cargo test foreground_probe_success_disables_notify_cccd`
- `cargo build`

Real hardware evidence:

- Flash PASS: `.cache/validation/companion-short-a1-c31125b/wired-flash/companion-wired-flash-summary.json`
- Pre-fix A1 failure: `.cache/validation/companion-short-a1-27e9f18/type-a1-smoke.log`
- Post-fix ASR-path A1: `.cache/validation/companion-short-a1-c31125b/type-a1-smoke.log`
- Final stats-only A1 PASS: `.cache/validation/companion-a1-stats-c31125b/type-a1-stats-only.log`
- Final stats-only A2 PASS: `../Listener/Listener-Type/.cache/validation/companion-a2-stats-20dcc94/type-a2-stats-only.log`

Final A1 stats-only result:

- GATT session active.
- Notify CCCD enabled.
- `TYPE:READY:A1` sent.
- First VKA1 notification received about 19 ms after ready.
- 1000 of 1000 packets received.
- 160000 reconstructed PCM bytes.
- 0 missing packets.
- 5.0 seconds duration.
- Terminal stop packet received.

Final A2 stats-only result:

- GATT session active.
- Notify CCCD enabled.
- `TYPE:READY:A2` sent through the Type readiness command path.
- First VKA1 notification received immediately after ready.
- 6000 of 6000 packets received.
- 960000 reconstructed PCM bytes.
- 0 missing packets.
- 30.0 seconds duration.
- Terminal stop packet received.

## Remaining Gaps

- IMU and screen are not installed, so motion/display product behavior is not covered here.
- Full migrated-feature MVP go/no-go remains step `2.2`; it must cover e-paper/display, power table, delete/privacy, OTA readiness, diagnostics, and product decision evidence.
- The ASR path reached the dictation pipeline but returned an empty transcript in a no-operator speech smoke. This is not a BLE transport failure; text accuracy still needs an explicit spoken/TTS acceptance run before production signoff.
