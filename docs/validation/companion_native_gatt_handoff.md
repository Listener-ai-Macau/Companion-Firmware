# Companion Native GATT Handoff

Date: 2026-06-29

## Current State

- Firmware commit prepared for the next real hardware pass: `84de3acc56ddd8e71e95c40e1fd52ce074a03405`.
- Commit subject: `Add Companion native GATT real BLE bench`.
- Scope: Companion-native STM32WB GATT service handle fix, minimal real BLE read/write bench responses, and `tools/companion_ble_real_bench.py`.
- IMU and display are intentionally out of scope for this pass.

## Offline Evidence

Commands run from `C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware`:

```powershell
python tools\verify_companion_gatt_static.py
python -m py_compile tools\companion_ble_real_bench.py tools\verify_companion_gatt_static.py
pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -Force
```

Results:

- `verify_companion_gatt_static.py`: PASS.
- Python compile check: PASS.
- NUCLEO bring-up build: PASS.
- Build size: `text=67080 data=2392 bss=19487`.

## Hardware Blocker

The real flash and real BLE bench are not completed for `84de3ac`.

Observed local hardware state:

- STM32CubeProgrammer v2.22.0 reported `No debug probe detected`.
- Windows serial devices showed only Listener `COM3` (`USB\VID_303A&PID_1001...`).
- No Companion NUCLEO ST-LINK / prior `COM13` was present.
- BLE scan did not find a `companion` candidate; it did see Listener `Blistener`.
- User confirmed the Companion hardware is currently at the company, not locally online.

Failure artifact:

- `.cache/validation/companion-native-gatt-84de3ac/preflash-scan.json`

Workflow status:

- `companion-listener-feature-migration` step `2.1` is waiting on external hardware.
- Workflow commit: `dd6bf574 Record Companion hardware unavailable block`.

## Resume Commands

When the Companion NUCLEO-WB55RG is locally connected again and Windows shows ST-LINK / STM32 COM:

```powershell
cd C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware
python tools\verify_companion_gatt_static.py
pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1
```

Flash under workflow lock:

```powershell
cd C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow
pwsh -NoProfile -File .\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose "flash Companion native GATT bench firmware 84de3ac" -Run pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\tools\flash.ps1 -Execute -WorkflowLockHeld -FlashNucleoBringup
```

Run real BLE bench under workflow lock:

```powershell
cd C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow
pwsh -NoProfile -File .\scripts\aiw.ps1 with-lock -Resource BLE-Companion -Purpose "Companion native GATT real BLE bench 84de3ac" -Run python C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\tools\companion_ble_real_bench.py --timeout 12 --notify-timeout 6 --json --output .cache\validation\companion-native-gatt-84de3ac\real-bench.json
```

Required passing artifact:

- `.cache/validation/companion-native-gatt-84de3ac/real-bench.json`
- JSON `status` must be `PASS`.
- Operations must include scan, service discovery, status read, card write, recording control/list, recording chunk refusal, settings write, diagnostics log pull, delete/privacy refusal, and OTA readiness.
