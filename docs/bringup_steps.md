# Companion Firmware Bring-Up Steps

## Source Baseline

The earlier Companion planning notes resolved the first firmware path to:

- First product: low-power BLE e-paper pendant.
- First board: `NUCLEO-WB55RG`.
- First firmware milestone: run an official BLE example before writing custom
  services.
- Later steps: custom GATT, fixed e-paper text, button state, microphone
  sample, SPI flash audio storage, then desktop/mobile pull.

The official upstream is pinned as a git submodule:

- URL: `https://github.com/STMicroelectronics/STM32CubeWB.git`
- Tag: `v1.24.0`
- Commit: `7c5aa7dcd2c0abe787f922bb06a6213c724d08e4`

The selected official example is:

```text
third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer
```

Reason: it is an ST GATT server point-to-point BLE example for STM32WB55 and is
closer to the planned custom pendant service than a fixed standard profile such
as Heart Rate.

## Step 0 - Prepare Tools

Install or confirm:

- STM32CubeIDE
- STM32CubeProgrammer
- ST BLE Sensor app on iOS/Android, or another BLE GATT scanner
- One `NUCLEO-WB55RG` board and USB cable connected to `USB_STLINK`

Initialize the official package:

```powershell
.\tools\bootstrap_stm32cubewb.ps1
```

## Step 1 - Run Official BLE Example

Open this project in STM32CubeIDE:

```text
third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32CubeIDE
```

Before flashing the app, confirm the wireless coprocessor has the BLE full
stack. In the current ST package, the expected binary is:

```text
third_party/STM32CubeWB/Projects/STM32WB_Copro_Wireless_Binaries/STM32WB5x/stm32wb5x_BLE_Stack_full_fw.bin
```

Use the Companion-owned provisioning wrapper before flashing any CPU1 BLE app:

```powershell
.\tools\provision_companion_wireless_stack.ps1 -CheckOnly
```

For real hardware, first read the FUS state under the workflow lock:

```powershell
pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose "Companion WB55 FUS diagnostic" -Run pwsh -NoProfile -File .\tools\provision_companion_wireless_stack.ps1 -Execute -WorkflowLockHeld -ReadFusInfo
```

Only when the report classifies FUS as `fus_v2_2_ready_for_wireless_stack`, install
the BLE full stack:

```powershell
pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose "Companion WB55 BLE stack provisioning" -Run pwsh -NoProfile -File .\tools\provision_companion_wireless_stack.ps1 -Execute -WorkflowLockHeld -InstallBleStack
```

The wrapper uses ST's current STM32CubeWB v1.24.0 `Release_Notes.html`
Wireless Coprocessor Binary Table. For the NUCLEO-WB55RG's 1 MB WB55G part,
`stm32wb5x_BLE_Stack_full_fw.bin` installs at `0x080D0000` and is marked
`FUS_v2 only`. The wrapper deliberately refuses to upgrade FUS automatically;
follow ST's incremental FUS upgrade flow if the readback is not v2.2.x.

Build and flash the application from STM32CubeIDE, or flash the official
reference image first:

```text
third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/Binary/BLE_p2pServer_reference.hex
```

Acceptance:

- The board advertises as `P2PSRVx` or the equivalent ST example device name.
- ST BLE Sensor or a BLE scanner can connect.
- The app can exercise the light/button behavior described by the official
  example readme.

## Step 2 - Create Companion GATT Service

After Step 1 passes on hardware, copy the example into a product-owned
application directory instead of modifying the submodule:

```text
app/companion_pendant/
```

Initial service shape:

- Device information: firmware version, battery placeholder, board role.
- Pendant card write: short UTF-8 text for e-paper display.
- Event notify: button press, recording started/stopped placeholders.
- Audio transfer placeholder: chunk metadata only, before microphone work.

Acceptance:

- Device advertises with a Companion-specific name.
- A BLE scanner sees the Companion service UUID.
- A desktop/mobile tool can write a short text payload and receive one notify.

## Step 3 - E-Paper Fixed Text

Wire the selected e-paper module to SPI and display a fixed short phrase.

Acceptance:

- Reset/boot displays a fixed phrase.
- BLE write from Step 2 can update an in-memory target phrase, even if display
  refresh is still manual or stubbed.

## Step 4 - Button State

Map one board button to a Companion event.

Acceptance:

- Button press changes local state.
- BLE notify sends the new state.

## Step 5 - Microphone Sample Stub

Bring up microphone sampling with the smallest proven path first.

Acceptance:

- Capture 5 to 10 seconds into RAM or a temporary buffer.
- Record sample rate, bit depth, buffer size, and whether clipping/noise is
  visible in the captured artifact.

## Current Listener-Compatible A1/A2 Gate

Before the real microphone path is ready, the NUCLEO smoke image for the
Listener-compatible VKA1 stream is:

```powershell
.\tools\build_companion_ble_audio_fixture.ps1 -Force
```

Flash it only inside the workflow hardware lock:

```powershell
pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose "flash Companion BLE audio fixture" -Run pwsh -NoProfile -File .\tools\flash.ps1 -Execute -WorkflowLockHeld -FlashAudioFixture
```

The flash tool must show a Chinese desktop confirmation prompt and play a sound
before programming the board. After flashing, the device advertises as
`companion`, uses no PIN/bonding, and sends deterministic VKA1 PCM when Type
writes `TYPE:READY` after notification subscription. The fixture keeps
`VREC:TOGGLE` and SW1 on the same path for control-write and physical-button
checks, but the temporary Type A1/A2 smoke buttons do not require a board press.

Companion A1/A2 reuse the Listener acceptance meaning:

- A1: 5 to 8 quick short-recording rounds through Type's embedded BLE stream.
  Each round must complete `session_start -> audio_data -> session_stop`, create
  Type history with embedded audio stats, and be ready for the next round within
  the normal Listener short-smoke cadence.
- A2: one approximately one-minute recording through the same stream. The Type
  side must show continuous audio progress, final text or a bounded ASR warning,
  complete embedded audio stats, and no transport timeout.

The CLI proof path is Type's existing embedded BLE stream command:

```powershell
listener-type --probe-embedded-audio-ble-subscription 30000
listener-type --submit-embedded-audio-ble-stream 120000
```

The repeatable Companion wrapper is:

```powershell
pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource Companion-WB55,BLE-Companion -Purpose "Companion Type A1/A2 validation" -Run pwsh -NoProfile -File .\tools\verify_companion_type_a1_a2.ps1 -Execute -WorkflowLockHeld
```

The wrapper is dry-run by default. With `-Execute`, it must already be inside
the workflow hardware lock, shows a Chinese desktop prompt with an audible
notification, runs the Type BLE subscription probe, runs A1 as six short
`--submit-embedded-audio-ble-stream 45000` rounds, then runs A2 as one
`--submit-embedded-audio-ble-stream 120000` long window. It records a JSON and
Markdown summary under `.cache/validation/companion-type-a1-a2-*`.

The temporary Type debug page should call the same underlying BLE/VKA1 and OTA
commands. Until that UI branch is accepted, the CLI plus logs are the canonical
pre-hardware evidence.

The repeatable Companion BLE OTA wrapper is:

```powershell
pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource Companion-WB55,BLE-Companion -Purpose "Companion BLE OTA validation" -Run pwsh -NoProfile -File .\tools\verify_companion_ble_ota.ps1 -Execute -WorkflowLockHeld -PackagePath <companion-package.zip>
```

The wrapper is dry-run by default. With `-Execute`, it must already be inside
the workflow hardware lock, shows a Chinese desktop prompt with an audible
notification, extracts `ota_manifest.json` and `firmware_ota.bin` from the same
Companion package, then runs Type headless:

```powershell
listener-type --firmware-ota-transfer ota_manifest.json firmware_ota.bin
```

It records the raw Type output plus a `firmware_ota_result.json` evidence file
under `.cache/validation/companion-ble-ota-*`. The BLE OTA gate passes only when
Type reports `status=PASS`, `transport=stm32wb_st_ble_ota`, and the STM32WB ST
OTA reboot handoff is confirmed.

The matching wired-flash wrapper is:

```powershell
.\tools\verify_companion_wired_flash.ps1 -PackagePath <companion-package.zip>
```

By default it does not touch hardware. It calls Type headless with:

```powershell
listener-type --wired-firmware-check <companion-package.zip>
```

and records the raw Type output plus `wired_firmware_result.json` under
`.cache/validation/companion-wired-flash-*`. Real ST-LINK/SWD flashing is only
enabled with the workflow hardware lock:

```powershell
pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose "Companion wired factory flash validation" -Run pwsh -NoProfile -File .\tools\verify_companion_wired_flash.ps1 -Execute -WorkflowLockHeld -PackagePath <companion-package.zip>
```

That execute path shows a Chinese audible operator prompt first, then calls:

```powershell
listener-type --wired-firmware-flash <companion-package.zip> SWD
```

and passes only when Type reports `status=PASS`, `mode=flash`, `port=SWD`, and
the STM32CubeProgrammer verification line is present.

The Listener Type temporary Companion page also embeds the shared firmware
panel. Use Settings > Companion Pendant bring-up to choose the same Companion
zip once, then switch between `蓝牙 OTA` and `有线刷机` in that page for manual
validation. When that selected package targets STM32WB/Companion, the wired
panel must present `ST-LINK / SWD` and `STM32CubeProgrammer` instead of serial
port, baud rate, OTA-preserve, or Boot-repair controls.

For no-hardware visual review in a Type dev server, open:

```text
http://127.0.0.1:<vite-port>/?visual=settings-companion&theme=dark
```

This renders the temporary Companion page directly so screenshots can prove the
A1/A2 controls, the aggregate `总体验收` command, same-package OTA/wired
controls, and ST-LINK/SWD copy are visible before the real board gate.

The same check can be captured automatically without touching hardware:

```powershell
.\tools\capture_type_companion_visual.ps1
```

It starts a local Type dev server, captures a headless browser screenshot and
rendered DOM, checks the page anchors, then writes
`type-companion-visual-summary.json` under `.cache/validation/type-companion-visual-*`.
The readiness preflight runs this visual smoke step unless
`-SkipTypeCompanionVisual` is passed.

Before taking hardware, run the fast no-hardware readiness preflight:

```powershell
.\tools\verify_companion_bringup_readiness.ps1
```

The fast preflight reuses the latest Companion package, checks the Listener
VKA1 contract, checks the Companion OTA/static contract, verifies that Type can
read the same package as both BLE OTA and wired factory input, captures the Type
temporary Companion visual smoke artifact, dry-runs the A1/A2 wrapper, dry-runs
the BLE OTA, wired-flash, and Type UI manual wrappers, and writes a JSON report under
`.cache/validation/companion-bringup-readiness-*`. It also writes `summary.md`
beside `summary.json`; the Markdown report is the human handoff checklist for
the remaining real-device gates, with the exact command/action and expected
evidence for each gate. It exits with `PASS_STATIC_MANUAL_GATES_REMAIN` when
all automatic checks pass and only the real-device gates remain.

Before final static signoff, run the full preflight:

```powershell
.\tools\verify_companion_bringup_readiness.ps1 -Full
```

`-Full` rebuilds the BLE audio fixture, OTA loader, normal bring-up app, OTA app,
regenerates the shared OTA/wired package, runs Type build/tests, and then emits
the same manual-gate list. Real flashing, BLE OTA, A1/A2, and Type UI button
operation still require the workflow hardware lock plus Chinese audible
operator prompts owned by their wrapper tools.

When hardware is ready, the preferred path is the aggregate acceptance runner:

```powershell
pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource Companion-WB55,BLE-Companion -Purpose "Companion hardware acceptance" -Run pwsh -NoProfile -File .\tools\verify_companion_hardware_acceptance.ps1 -Execute -WorkflowLockHeld -PackagePath <companion-package.zip> -EvidencePath <companion_ui_screenshot_or_log>
```

The runner first flashes the BLE audio fixture, then executes the A1/A2 wrapper,
then the Type UI manual wrapper while the board is still running that fixture,
then the wired SWD flash wrapper, and then the BLE OTA wrapper inside one locked
operator flow. This order matters: the package currently contains the bring-up
app, not the VKA1 audio fixture, so the Type page A1/A2 checks must finish before
OTA/wired package flashing. BLE OTA then runs after the same package has restored
the OTA loader through the wired factory flash path. The runner then feeds the
four summary files into
`verify_companion_manual_gate_evidence.ps1`. The no-hardware readiness preflight
dry-runs this aggregate entry and records
`companion-hardware-acceptance-summary.json` under the readiness report directory.

The Type temporary Companion page real-device gate has its own wrapper:

```powershell
pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource Companion-WB55,BLE-Companion -Purpose "Companion Type UI validation" -Run pwsh -NoProfile -File .\tools\verify_companion_type_ui_manual.ps1 -Execute -WorkflowLockHeld -PackagePath <companion-package.zip> -EvidencePath <companion_ui_screenshot_or_log>
```

It shows a Chinese audible prompt, waits while the operator runs BLE
subscription, A1 smoke, A2 smoke, and confirms the `总体验收` command from the
Type page, then writes `companion-type-ui-manual-summary.json` with
`companion_type_ui_manual_result_json`.

After the real-device runs, close the gate with the evidence verifier:

```powershell
.\tools\verify_companion_manual_gate_evidence.ps1 -PackagePath <companion-package.zip> -A1A2SummaryPath <companion-type-a1-a2-summary.json> -BleOtaEvidencePath <firmware_ota_result_or_log> -WiredFlashEvidencePath <wired_flash_result_or_log> -TypeUiEvidencePath <companion-type-ui-manual-summary.json>
```

Run it with `-ChecklistOnly` before hardware to generate a pending checklist
without failing. Without `-ChecklistOnly`, it requires all four manual gates to
pass: A1/A2 JSON status `PASS`, BLE OTA `transport=stm32wb_st_ble_ota`, wired
ST-LINK/SWD factory flash completion, and Type temporary Companion debug-page
summary status `PASS` with `operator_confirmed=true` and the `总体验收` command in
its required action list.

## Step 6 - SPI Flash Audio Storage

Move the captured audio buffer into external SPI flash.

Acceptance:

- Write one sample block.
- Read it back.
- Compare byte count and checksum.

## Step 7 - Desktop Pull

Use a desktop BLE tool before building a full app.

Acceptance:

- Tool scans for the Companion device.
- Tool connects and pulls one metadata record or small sample payload.
- Failure cases are explicit: no device, disconnect, timeout.
