# STM32WB55 BLE Recovery Notes

Last updated: 2026-06-28

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
  500 microphone blocks with the full 320-byte 10 ms PCM frame, then a terminal stop. This
  keeps the short-command window near 5 s instead of recording extra room audio
  after a 1-2 s TTS phrase.
- The same app accepts `TYPE:READY:A2` for longer text-recognition validation:
  3000 microphone blocks with the full 320-byte 10 ms PCM frame, then a
  terminal stop.
- The NUCLEO bring-up app now locally overrides the ST p2pServer ATT MTU to
  251 and the VKA1 notify value to 248 bytes. A1 and A2 both send the full
  320-byte microphone frame, which the portable VKA1 sender splits across two
  notifications. This keeps short commands and fast speech on the real INMP441
  path from being limited by the older compact-sampling view.

Validation evidence:

- Direct app A1/A2 passed:
  `.cache/validation/companion-type-a1-a2-20260627-172352/companion-type-a1-a2-summary.json`.
- Wired package through repo flash plus A1/A2 passed:
  `.cache/validation/companion-type-a1-a2-20260627-175020/companion-type-a1-a2-summary.json`.
- Type wired flash with SRAM handoff passed:
  `.cache/validation/companion-wired-flash-20260627-180055/companion-wired-flash-summary.json`.
- 2026-06-28 MTU251/full-frame regression passed:
  `.cache/validation/a1-a2-fullframe-20260628-regression/companion-type-a1-a2-summary.json`.
  A1 reached 100% text accuracy; A2 had no missing packets and 0.833333 text
  accuracy on the normal Listener-style TTS phrase.
- 2026-06-28 fast-speech A2 passed:
  `.cache/validation/a2-fullframe-fast-speech-20260628/companion-type-a1-a2-summary.json`.
  A2 uploaded `960000` PCM bytes in one 30 s session with `missing_packets=0`.
  The remaining phrase confusion is audio/acoustic/ASR quality, not BLE loss.
- 2026-06-28 six-round A1 + A2 retry validation passed:
  `.cache/validation/companion-type-a1-a2-recovery-20260628-175130/companion-type-a1-a2-summary.json`.
  It proved the VKA1 notify path stayed lossless (`missing_packets=0`) but also
  exposed two follow-up hardening points: Windows BLE control writes for
  processing/LED feedback can delay headless process exit after the audio path
  has already passed, and a 9 s A1 capture window picks up too much room audio
  for short TTS phrases. Type-side headless validation now disables the
  processing LED sync through
  `LISTENER_TYPE_DISABLE_EMBEDDED_BLE_PROCESSING_SYNC=1`, while the app A1
  autostream window is shortened to 500 blocks.
- 2026-06-28 no-one-shot-heartbeat A1 validation exposed the compact-A1 quality
  limit:
  `.cache/validation/companion-type-a1-a2-nohb-20260628-182142/companion-type-a1-a2-summary.json`.
  BLE transport was mostly lossless (`missing_packets=0` for completed rounds),
  but A1's 132-byte compact payload produced wrong or empty short-command ASR.
  The A1 path is therefore moved to the same full 320-byte frame contract as A2.
- 2026-06-28 latest same-package hardware chain passed with package
  `.cache/ota_firmware/companion-ota-nucleo-wb55rg-d4acb9f-dirty-20260628-183529.zip`.
  Wired flash passed at
  `.cache/validation/companion-wired-flash-a1full-20260628-183554/companion-wired-flash-summary.json`.
  Six-round A1 plus A2 passed at
  `.cache/validation/companion-type-a1-a2-a1full-20260628-183640/companion-type-a1-a2-summary.json`:
  all completed rounds had `missing_packets=0`, A1 text accuracy was 100%, and
  A2 uploaded `960000` PCM bytes with `missing_packets=0`.
- 2026-06-28 Type one-shot heartbeat regression was re-fixed after fast-speech
  testing showed back-to-back A1 sessions could stall or disconnect when
  foreground one-shot capture kept sending periodic `TYPE:HB`. Keep one-shot
  capture to the initial `TYPE:READY` only; reserve periodic heartbeat for the
  background listener.
- 2026-06-28 fast-speech validation passed after restoring no-one-shot
  heartbeat and adding env-scoped ASR hotwords for Companion validation:
  `.cache/validation/companion-type-a1-a2-fast-hotwords-20260628-190919/companion-type-a1-a2-summary.json`.
  A1 rounds 1-4 passed first try with `missing_packets=0` and 100% text
  accuracy. A2 passed with `missing_packets=0`; English/product-name words may
  still be phonetically localized by the ASR, so keep transcript accuracy
  threshold evidence instead of treating brand-word spelling as BLE loss.

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
- Keep the ST base/finish characteristic on the same explicit write-permit path
  as raw data. The 4-byte `OTAS_STM_UPLOAD_FINISHED` command must receive
  `aci_gatt_write_resp()` before the OTA app schedules the confirmation/reset
  work, otherwise Windows can hold the finish write until the disconnect
  handoff.
- In Listener-Type, keep the finish command on the ordinary
  `write_stm32wb_st_ota_value_with_fallback()` path with
  `target.base_write_option`. A Type-side no-wait finish write was tested on
  hardware and did not shorten the finish tail, so leave the transport contract
  simple and loader-driven.
- On connection complete, the Companion OTA loader requests a fast connection
  interval through `aci_l2cap_connection_parameter_update_req()`:
  min `0x0006` (7.5 ms), max `0x0006` (7.5 ms), latency `0`, timeout `0x0064`
  (1 s). Keep this loader-side request guarded by
  `tools/verify_ota_contract_static.py`; the safe data path is still
  WriteWithResponse, not optimistic no-response streaming.
- Keep the ST BLE_Ota finish write callback short: `OTAS_STM_UPLOAD_FINISHED`
  only schedules the reboot sequencer task and returns. The task sends
  `OTAS_STM_REBOOT_CONFIRMED`, gives Windows a short grace window, and then
  finalizes flash/resets; `ACI_GATT_SERVER_CONFIRMATION` remains a valid early
  finalize path. Do not call `OTAS_STM_UpdateChar()`, `HAL_Delay()`, or reset
  inside the finish write callback because that makes Windows wait for the
  disconnect handoff instead of completing the finish write promptly.
- Drain that deferred finalize from the local `BLE_UserEvtRx()` tail, after
  `SVCCTL_UserEvtRx()` has finished processing the ST service event. This avoids
  a private sequencer task bit and keeps the confirmation/reset work tied to the
  existing HCI async event path.
- Do not change the existing confirmation characteristic properties in place to
  add Notify under the same UUID. Hardware validation showed Windows continued
  to expose the cached Indicate-only property, and the experimental notify build
  failed mid-transfer. A notify/credit completion path needs a new characteristic
  or protocol version, not an in-place property change.

Validation evidence:

- BLE OTA through Type passed:
  `.cache/validation/companion-ble-ota-20260627-192828/companion-ble-ota-summary.json`.
- The transfer wrote `59956` bytes in `2998` chunks. The finish write timed out
  during the reboot handoff, but Type observed the WB55 disconnect/reboot and
  marked the transfer PASS.
- 2026-06-28 MTU251 plus loader fast-connection validation passed:
  `.cache/validation/companion-ble-ota-6d50cee-20260628/companion-ble-ota-summary.json`.
  The `61724` byte OTA image transferred in `249` confirmed chunks of up to
  248 bytes. Data phase time dropped from about 22.8 s to about 7.9 s; the full
  BLE capture window dropped from about 36.0 s to 13.4 s on the clean
  `6d50cee` package.
- 2026-06-28 Listener BLE OTA benchmark from retained Type logs is about
  19-20 KB/s with 500-byte confirmed chunks. Companion's safe ST BLE_Ota path is
  about 7.9 KB/s with 248-byte confirmed chunks before the tighter 7.5 ms / 1 s
  connection-parameter retune. Reaching Listener-like throughput requires a
  real STM32WB ACK/credit or offset/CRC path before uncapping large
  WriteWithoutResponse packets; otherwise Type can report progress for data the
  loader did not flash.
- 2026-06-28 hardware retunes showed the 7.5 ms / 1 s connection request and a
  Type-side finish no-wait attempt did not remove the roughly 4 s finish tail.
- 2026-06-28 base/finish write-permit hardware validation also kept the roughly
  4 s finish tail by itself. The current loader-side candidate fix keeps raw
  data confirmed, moves confirmation/reset out of the finish write callback into
  a 300 ms deferred HCI-event grace path, makes the base/finish characteristic use
  `GATT_NOTIFY_WRITE_REQ_AND_WAIT_FOR_APPL_RESP`, and drains the deferred
  finalize from the local HCI event task after ST service event processing.
- A 2026-06-28 notify-confirm experiment was rejected: Windows kept using the
  cached Indicate-only GATT metadata for the same UUID and one hardware run
  aborted at 120/249 chunks. Do not keep this in the product path without a new
  characteristic UUID/protocol version and a full reconnect/cache validation.
- 2026-06-28 final stable validation passed with package
  `.cache/ota_firmware/companion-ota-nucleo-wb55rg-d4acb9f-dirty-20260628-111242.zip`
  and evidence
  `.cache/validation/companion-ble-ota-stable-final-20260628/companion-ble-ota-summary.json`.
  The transfer still used 249 confirmed 248-byte chunks for 61,724 bytes. The
  data phase completed in about 7.6 s, the full capture was 13.63 s, and the
  finish-to-disconnect tail stayed about 4.08 s. Treat this as the safe limit of
  the current ST BLE_Ota/WinRT path; Listener-like 19-20 KB/s needs a new
  Companion OTA protocol with explicit ACK/credit/offset/CRC semantics rather
  than uncapping WriteWithoutResponse on the ST raw characteristic.
- The matching same-package wired factory flash passed before BLE OTA:
  `.cache/validation/companion-wired-factory-6d50cee-20260628/companion-wired-flash-summary.json`.
- 2026-06-28 Companion OTA v2 latest same-package transfer passed with package
  `.cache/ota_firmware/companion-ota-nucleo-wb55rg-d4acb9f-dirty-20260628-183529.zip`
  and evidence
  `.cache/validation/companion-ble-ota-a1full-20260628-184231/companion-ble-ota-summary.json`.
  The v2 path transferred `63288` bytes in `264` chunks of 240 bytes with
  `window=24`, then confirmed completion/reboot handoff.
- The same package also passed wired recovery after BLE OTA:
  `.cache/validation/companion-wired-recovery-a1full-20260628-184519/companion-wired-flash-summary.json`.
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

### Companion OTA v2 adds a Listener-style fast path

Symptom:

- The stable ST BLE_Ota path topped out around 7.5-8 KB/s on Windows because
  every 248-byte raw write was confirmed and the finish handoff had a long
  disconnect tail.
- Listener OTA was already around 19-20 KB/s with larger host-paced chunks, so
  Companion needed an explicit credit/status protocol before using
  WriteWithoutResponse.

Root cause:

- The official ST BLE_Ota service is safe but not a high-throughput Windows
  bulk-transfer protocol.
- Changing the existing ST confirmation characteristic properties in place is
  not reliable on Windows; previous hardware validation showed cached GATT
  metadata could keep the old Indicate-only view.

Fix:

- Keep the ST BLE_Ota service as a fallback and add a new Companion OTA v2
  service with fresh UUIDs:
  `8f7a8007-7b7d-4f3d-9d6f-6c2d1b7c0000` service,
  `8f7a8002-...` control, `8f7a8004-...` data, and
  `8f7a8005-...` status.
- Register v2 from the ST custom service hook after the ST OTA service, and
  guard it with `tools/verify_ota_contract_static.py`.
- Use a 16-byte binary control command (`COV2` magic, op, version, expected
  size, chunk size, window) and 4-byte-offset data packets.
- Make offset mismatch recoverable. The loader keeps state `RECEIVING`, updates
  status with `COMPANION_OTA_V2_ERROR_OFFSET_MISMATCH`, and Type resumes from
  the device-reported `bytes_written` instead of treating one dropped packet as
  fatal.
- Type sends a window of WriteWithoutResponse data packets, writes a sync
  control command, reads the status characteristic, shrinks the window on
  offset mismatch, and grows it again after clean windows.
- Companion OTA packages now advertise `protocol.name=companion_ota_v2` and
  no longer include the ST `confirm_uuid` in the primary manifest. The old ST
  transport remains in Type only as a fallback/recovery contract.

Validation rule:

- Static validation must cover all three sides before hardware: OTA loader build
  includes `Src/companion_ota_v2.c`, package manifest UUIDs/chunk size match
  Type, and the manual/hardware gate expects `transport=companion_ota_v2`.
- Hardware validation must still prove real BLE transfer and reboot handoff
  because STM32WB/GDMA/WinRT timing is not fully proven by compilation.

WBA migration note:

- The v2 host protocol should port to WBA because it depends only on GATT
  control/data/status semantics, not WB55 CPU2/FUS.
- The flash writer, service registration hook, boot handoff, and final reset
  path must be rewritten from the WBA Cube example/flash API rather than copying
  WB55 `SVCCTL_InitCustomSvc`, SRAM1 cookie, or `FD_WriteData` details.

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

## Microphone Migration Note

Current Companion NUCLEO validation uses the confirmed INMP441 bench wiring.
That part outputs I2S PCM, so the WB55 bring-up app captures it through SAI1
I2S-style input and then forwards PCM16 16 kHz frames through the VKA1 bridge.

Listener's active N16R8 validation build is different: it uses an SPH0655 PDM
digital microphone and ESP-IDF's I2S PDM2PCM path. Local Listener evidence:

- `Listener-Firmware/docs/features/firmware-feature-map.md` records
  `SPH0655 PDM audio through ESP-IDF PDM2PCM`.
- `Listener-Firmware/ports/esp32/audio_capture/audio_capture_esp32.c` selects
  `CONFIG_AUDIO_CAPTURE_MIC_SPH0655_PDM`, requires hardware PDM2PCM support,
  configures `I2S_PDM_RX_CLK_DEFAULT_CONFIG`, and applies both hardware and
  software gain.
- Listener board diagnostics name the PDM clock/data pins as GPIO48/GPIO47.

Changing Companion from INMP441 to the Listener microphone family is therefore
hardware-medium and firmware-medium complexity. Hardware is only two signal
lines plus power, but firmware must switch from I2S PCM capture to PDM capture,
decimation/filtering, gain, DC/high-pass tuning, and new audio quality gates.
Keep the portable recording/VKA1 business layer unchanged; add a separate
STM32 PDM backend under the microphone abstraction after checking the exact
WB55CE or WBA peripheral support and Cube example path.

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
