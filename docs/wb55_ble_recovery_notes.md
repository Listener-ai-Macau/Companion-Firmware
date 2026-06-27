# STM32WB55 BLE Recovery Notes

Last updated: 2026-06-27

This note records the Companion WB55 BLE/OTA fixes and the operating rules for
future BLE work. Keep it current whenever WB55 BLE, GATT, OTA loader handoff, or
Listener-Type Companion transport behavior changes.

## Repair Rules

- Every WB55 BLE/OTA fix must leave a repair note: symptom, root cause, files,
  validation artifacts, and recovery command if the board can get stuck.
- Check official ST and Microsoft references before closing the work. Use local
  `third_party/STM32CubeWB` examples as code-level authority, then confirm with
  official online docs when behavior depends on tooling, OS BLE, or migration.
- Record the STM32WBA migration impact while the context is fresh.
- Add static validation or script checks for any repeatable failure mode.

## What Was Fixed

### OTA app used the wrong `SystemInit`

Symptom:

- A wired factory package wrote the OTA loader and the app successfully, but the
  board did not advertise the app's VKA1 BLE service after reset.
- Debug evidence showed a valid app vector at `0x08007000`, but execution had
  `VTOR=0` and landed in the loader/HardFault path.

Root cause:

- `cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile` set `SYSTEM_SOURCE` to the
  ST `BLE_p2pServer_ota` `system_stm32wbxx.c`, but generic `vpath %.c` found the
  non-OTA `BLE_p2pServer/Core/Src/system_stm32wbxx.c` first.
- The non-OTA file writes `SCB->VTOR` back to flash base, which is wrong for an
  OTA app linked at `0x08007000`.

Fix:

- Add an explicit rule for `$(BUILD_DIR)/system_stm32wbxx.o` so the OTA app
  always compiles the OTA-specific ST source.
- Guard this in `tools/verify_listener_vka1_static.py`.

Official basis:

- Local ST example
  `third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer_ota/readme.txt`
  says the OTA app variant removes the app-side `SCB->VTOR` update because
  `BLE_Ota` already sets it before jumping.
- Local ST example
  `third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_Ota/Core/Src/system_stm32wbxx.c`
  jumps to the app by setting `SCB->VTOR = FLASH_BASE + CFG_APP_START_SECTOR_INDEX * 0x1000`.

### Wired package stayed in the OTA loader

Symptom:

- Type's `--wired-firmware-flash` reported PASS, but the next BLE scan saw the
  OTA loader advertisement instead of the app VKA1 service.
- Repo-local `tools/flash.ps1` could boot the app only after a manual SRAM
  handoff write.

Root cause:

- ST `BLE_Ota` uses SRAM1 reset handoff bytes to decide whether to run the app
  or stay in the loader after a software reset.
- Type's STM32WB wired flasher wrote HEX files and reset, but did not write the
  `FW_APP` handoff cookie.

Fix:

- `tools/flash.ps1` now writes:
  `-w8 0x20000000 0x00 0x07 0x00 0xC3 -r8 0x20000000 4 -rst`.
- Listener-Type's STM32WB wired factory flasher now performs the same SRAM
  handoff after all HEX artifacts verify.
- `tools/verify_companion_wired_flash.ps1` requires Type evidence containing
  `Wrote STM32WB OTA FW_APP SRAM handoff`.

Recovery command:

```powershell
& 'C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_2.2.400.202601091506\tools\bin\STM32_Programmer_CLI.exe' `
  -c port=SWD mode=UR reset=HWrst freq=4000 `
  -w8 0x20000000 0x00 0x07 0x00 0xC3 `
  -r8 0x20000000 4 -rst
```

### Type READY did not trigger Companion VKA1 streaming

Symptom:

- Type A1/A2 headless capture opened the notify session and sent `TYPE:READY`,
  but no Companion audio stream started unless a manual control path was used.
- The first A1/A2 gate only verified PCM transport. Hardware acceptance now
  requires ASR final text for both A1 and A2. The wrapper now generates and
  plays fixed TTS audio like Listener's BLE TTS smoke test: `TYPE:READY:A1`
  opens the short A1 text window, `TYPE:READY:A2` opens the long A2 text window,
  and normal `TYPE:READY` remains a lightweight link-ready behavior.

Root cause:

- Listener Type's embedded BLE headless path sends readiness/heartbeat messages,
  not the manual record key command.
- The Companion app treated `TYPE:READY` as host-online only.

Fix:

- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c` now starts a bounded
  Type-ready autostream on `TYPE:READY`: 24 blocks, 128 PCM bytes per BLE packet,
  paced with `MX_APPE_Process()` and a terminal stop.
- The same app accepts `TYPE:READY:A1` for short text-recognition validation:
  600 microphone blocks with full 320-byte PCM batches, then a terminal stop.
- The same app accepts `TYPE:READY:A2` for longer text-recognition validation:
  3000 microphone blocks with full 320-byte PCM batches, then a terminal stop.
- The STM32WB notify adapter pumps `MX_APPE_Process()` between fragmented
  153-byte GATT notifications so a full 320-byte PCM block can drain before the
  next microphone block is queued.

Validation evidence:

- Direct app A1/A2 passed:
  `.cache/validation/companion-type-a1-a2-20260627-172352/companion-type-a1-a2-summary.json`.
- Wired package through repo flash plus A1/A2 passed:
  `.cache/validation/companion-type-a1-a2-20260627-175020/companion-type-a1-a2-summary.json`.
- Type wired flash with SRAM handoff passed:
  `.cache/validation/companion-wired-flash-20260627-180055/companion-wired-flash-summary.json`.

### BLE OTA raw writes timed out or transferred without flashing

Symptom:

- Windows could discover the Companion OTA loader and write the base address,
  but the first raw write timed out when the raw characteristic used write
  permit handling.
- When the loader accepted write commands without the permit response path, Type
  could report full progress, but flash at `0x08007000` stayed erased.
- Before the final fix, the finish command could also time out without clear
  evidence that the app had actually been written.

Root cause:

- `APP_BLE_Init()` manually called `OTAS_STM_Init()` immediately after
  `SVCCTL_Init()`.
- ST `SVCCTL_Init()` already calls the weak `SVCCTL_SvcInit()` from
  `svc_ctl.c`, and that default service initializer calls `OTAS_STM_Init()`.
- The duplicate initialization created two identical OTA services. Windows chose
  the first service handles, while the loader's `OTAS_Context` was overwritten by
  the second service handles, so the raw write-permit event did not match the
  active context.
- A Windows write success was therefore not enough evidence that the WB55 loader
  had processed the payload or written internal flash.

Fix:

- Remove the manual `OTAS_STM_Init();` call from
  `cubeide/Companion_BLE_Ota_Loader/Src/app_ble.c`.
- Keep `SVCCTL_Init()` as the single service-registration owner and guard this in
  `tools/verify_ota_contract_static.py`.
- Keep the raw OTA characteristic as
  `CHAR_PROP_WRITE | CHAR_PROP_WRITE_WITHOUT_RESP` with
  `GATT_NOTIFY_WRITE_REQ_AND_WAIT_FOR_APPL_RESP`.
- In `ACI_GATT_WRITE_PERMIT_REQ_VSEVT_CODE`, call `aci_gatt_write_resp()` and,
  only on `BLE_STATUS_SUCCESS`, pass that exact payload once to
  `OTAS_STM_Notification(OTAS_STM_RAW_DATA_ID)`.
- Do not write flash from the raw `ACI_GATT_ATTRIBUTE_MODIFIED_VSEVT_CODE` path;
  it only acknowledges the event so accepted packets are not double-written.
- In Listener-Type, prefer `GattWriteOption::WriteWithResponse` when the
  characteristic supports `Write`, and use the negotiated ATT payload up to the
  ST raw 248-byte block size. Keep the no-response fallback capped to the
  default 20-byte ATT payload until a larger-MTU ACK/credit path exists.

Validation evidence:

- BLE OTA through Type passed:
  `.cache/validation/companion-ble-ota-20260627-192828/companion-ble-ota-summary.json`.
- The transfer wrote `59956` bytes in `2998` chunks. The finish write timed out
  during the reboot handoff, but Type observed the WB55 disconnect/reboot and
  marked the transfer PASS.
- 2026-06-27 follow-up: the host-side cap was raised for confirmed
  WriteWithResponse raw writes. With a 251-byte negotiated MTU the same 59956
  byte image should transfer in about 242 raw chunks instead of 2998; validate
  this on hardware before treating the speed target as closed.
- A1/A2 after BLE OTA passed:
  `.cache/validation/companion-type-a1-a2-20260627-193325/companion-type-a1-a2-summary.json`.
- The same-package wired flash path passed before BLE OTA:
  `.cache/validation/companion-wired-flash-20260627-192610/companion-wired-flash-summary.json`.

Recovery command:

```powershell
pwsh -NoProfile -File .\tools\verify_companion_wired_flash.ps1 `
  -Execute -WorkflowLockHeld `
  -PackagePath .cache\ota_firmware\companion-ota-nucleo-wb55rg-d5c2a80-dirty-20260627-192554.zip
```

## Current Open Risk

Repeated short-lived Windows headless BLE sessions can still destabilize the
bench state.

Observed sequence:

- Type wired package with SRAM handoff boots the app.
- A1 rounds can pass with `pcm_bytes=3072`, `missing_packets=0`.
- After a timeout or early headless process exit, later scans may stop seeing
  the `companion` app advertisement until SWD reset/handoff.
- Validation artifacts:
  `.cache/validation/companion-type-a1-a2-20260627-180115/companion-type-a1-a2-summary.json`,
  `.cache/validation/companion-type-a1-a2-20260627-180356/companion-type-a1-a2-summary.json`,
  `.cache/validation/companion-type-a1-a2-20260627-180635/companion-type-a1-a2-summary.json`.

Working hypothesis:

- Windows BLE can leave a half-open GATT session or stale cache state when many
  short hidden Type processes connect/discover/subscribe in quick succession.
- The firmware may also fail to restart advertising after a central disconnect
  or failed CCCD setup. This must be verified in `app_ble.c`/event callbacks
  before blaming Windows only.

Current state:

- The duplicate-service OTA failure is fixed and guarded by static validation.
- A1/A2 passed immediately after a real BLE OTA transfer, so app boot and the
  VKA1 service are confirmed on the current bench state.

Next diagnostics:

- Add or expose firmware-side BLE event logs for connection complete,
  disconnection complete, CCCD write, notify enable/disable, advertising start,
  and advertising failure status.
- Keep Type headless validation single-owner: kill stale `listener-type`
  processes before each validation and clean up failed child processes.
- Use longer cooldown between repeated sessions. The current validation script
  defaults to `RoundCooldownMs=5000` and `RetryDelayMs=5000`.
- If advertising stops after a failed session, capture whether the firmware is
  connected, idle, advertising, or stuck in an error path before resetting it.

## Source Notes

Official/local references checked:

- ST `BLE_p2pServer_ota` local README:
  `third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer_ota/readme.txt`.
- ST `BLE_Ota` local boot handoff:
  `third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_Ota/Core/Src/system_stm32wbxx.c`.
- ST AN5247, OTA application and wireless firmware update for STM32WB:
  https://www.st.com/resource/en/application_note/an5247-overtheair-application-and-wireless-firmware-update-for-stm32wb-series-microcontrollers-stmicroelectronics.pdf
- ST AN5289, building wireless applications with STM32WB:
  https://www.st.com/resource/en/application_note/an5289-how-to-build-wireless-applications-with-stm32wb-mcus-stmicroelectronics.pdf
- ST PM0271, Bluetooth LE stack programming on STM32WB/STM32WBA:
  https://www.st.com
- Microsoft WinRT GATT client guidance:
  https://learn.microsoft.com/en-us/windows/apps/develop/devices-sensors/gatt-client
- Microsoft `BluetoothCacheMode` docs:
  https://learn.microsoft.com/en-us/uwp/api/windows.devices.bluetooth.bluetoothcachemode

Useful external field reports:

- Microsoft Answers reports retry/delay being needed around
  `GetGattServicesAsync()` on Windows BLE in some conditions.
- Community reports are useful to recognize Windows BLE cache/session symptoms,
  but the design authority remains ST examples, ST application notes, and
  Microsoft WinRT documentation.

## STM32WBA Migration Impact

Portable to WBA:

- Companion business state machine: idle, recording, cancel, diagnostics, OTA
  requested, Type-ready autostream policy.
- VKA1 packet framing and Type-side GATT/audio contract.
- Type package validation, manifest structure, A1/A2 acceptance semantics, and
  most host-side BLE retry discipline.
- Separation between generated low-level code and portable app modules.

WB55-specific and must be replaced:

- CPU2/FUS provisioning and STM32WB wireless stack binary handling.
- IPCC/HSEM/STM32_WPAN initialization details.
- ST `BLE_Ota` SRAM1 handoff bytes at `0x20000000`.
- `0x08007000` OTA app layout and `BLE_p2pServer_ota` `SystemInit` rule.

WBA direction:

- Start from STM32CubeWBA examples and CubeMX WBA BLE server generation, not by
  copying WB55 CPU2/FUS code.
- Treat WBA as a new low-level BLE platform under the same Companion business
  interface.
- Re-evaluate flash/OTA layout with WBA flash size and TrustZone/security
  settings; do not assume the WB55 loader/app split, SRAM handoff cookie, or
  `SVCCTL_SvcInit` service-registration behavior applies.
- Keep the host contract stable: BLE name `companion`, VKA1 notify/control, OTA
  manifest capability, and A1/A2 validation shape.
- Preserve the repair lesson: register each GATT service once from one generated
  platform hook, and require either write-response or an explicit ACK/credit
  protocol before Type reports OTA data as accepted.
