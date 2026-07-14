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

The STM32CubeWB package itself contains 13 nested ST submodules. This workspace
keeps `.vscode/settings.json` at `git.detectSubmodulesLimit >= 13` so VS Code
can open them without the default "will not be opened automatically" warning.
They are still read-only upstream references; Companion changes must stay in
local wrappers, adapters, tools, docs, or generated CubeMX output. Validate the
policy with:

```powershell
python .\tools\verify_workspace_submodule_policy.py
```

The selected official example is:

```text
third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer
```

Reason: it is an ST GATT server point-to-point BLE example for STM32WB55 and is
closer to the planned custom pendant service than a fixed standard profile such
as Heart Rate.

The repo-owned development-board IOC is:

```text
cubeide/Companion_Nucleo_WB55RG/Companion_Nucleo_WB55RG.ioc
```

It imports the hardware-relevant settings from the user-provided
`C:\Users\Billy\Desktop\STM32.ioc`, while keeping local CubeIDE project
metadata such as project name and toolchain. Validate that relationship with:

```powershell
python .\tools\verify_devboard_ioc_import.py
```

For screen hardware bring-up, also verify the panel wiring preflight:

```powershell
python .\tools\verify_expression_panel_wiring_preflight.py
```

The preflight fixture is
`docs/validation/companion-screen-panel-wiring-preflight.json`. It records the
imported WB55 SPI2 transport candidate while keeping controller and DC/RST/BUSY
facts under the real-panel hardware gate.

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

## Current WB55 Microphone Evidence

The WB55 devboard microphone is being treated as the Listener-style
SPH0655-compatible PDM microphone. The currently validated development path is:

- PC speaker plays the test phrase as the sound source.
- WB55 captures raw PDM on SAI1 Block A with raw-SAI DMA.
- Firmware decodes MSB-ordered PDM with CIC3, decimation 96, MCKDIV 31,
  preamp shift 3, and a 450-block flash-recording stage buffer.
- The resulting 16 kHz PCM16 mono flash recording is pulled over Companion BLE
  and sent to Companion Type ASR.

Latest passing artifacts:

- Baseline summary:
  `docs/validation/companion-mic-wb55-pdm-baseline.json`, verified by
  `python .\tools\verify_companion_mic_wb55_pdm_baseline.py`
- Margin gate:
  `docs/validation/companion-mic-wb55-pdm-margin.json`, verified by
  `python .\tools\verify_companion_mic_wb55_pdm_margin.py`
- Recording chain:
  `.cache\validation\mic-fast2-20260710-060913\companion-flash-recording-chain.json`
- ASR/minutes:
  `.cache\validation\mic-fast2-20260710-060913-asr\companion-recording-to-minutes.json`

The current O2/CIC3 Type transcript is `你好，小伴录音测试。`, so the
end-to-end real-mic path and recognition phrase are proven. The current margin
gate records `max_dma_rx_overruns=0`, `diag=0` steady-state `capture_ms=10`,
`missing_packets=0`, matching SHA-256, and `audio_quality.status=PASS` as
`READY_FOR_LONGER_SOAK`. Full raw diagnostics are now sparse; diagnostic blocks
can still take longer because they compute raw CRC and quality stats.
The current best firmware candidate keeps CIC3 semantics and the default
bring-up build uses O2. Reproduce it with
`pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -Force`, or pass
`-Optimization O2 -PdmCic3ChunkAccumulate 0 -PdmUseCic3Filter 1 -PdmBitOrderLsb 0`
for an explicit A/B run.
Rejected A/B branches are recorded in the margin fixture: `cic3_chunk` worsened
overruns and returned empty ASR; `boxcar_msb` cleared overruns but also returned
empty ASR.

## Current Independent Companion Hardware Gate

The NUCLEO Companion app now carries the Companion-native BLE advertising,
GATT surface, OTA readiness, wired factory package support, and the legacy VKA1
compatibility service in one image:

```powershell
.\tools\build_nucleo_bringup.ps1 -Force
```

For direct bring-up flashing, program it only inside the workflow hardware lock:

```powershell
pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose "flash Companion NUCLEO bring-up" -Run pwsh -NoProfile -File .\tools\flash.ps1 -Execute -WorkflowLockHeld -FlashNucleoBringup
```

The flash tool must show a Chinese desktop confirmation prompt and play a sound
before programming the board. After flashing, the device advertises as
`companion`, uses no PIN/bonding, exposes the Companion-native GATT services in
`docs/ble_uuid_table.json`, and keeps `VREC:TOGGLE` plus SW3 on the same
Companion recording FSM path.

The default hardware proof path is now Companion-owned and does not require
`Listener-Type`:

```powershell
pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource 'Companion-WB55,BLE-Companion' -Purpose "Companion native BLE GATT bench validation" -Run python .\tools\companion_ble_real_bench.py --name companion --timeout 20 --notify-timeout 10 --output .\.cache\validation\companion-real-ble-gatt-<timestamp>\companion-ble-real-bench.json --json
```

It scans for `companion`, connects with Bleak, verifies every required native
service/characteristic, reads status and battery, writes a card, exercises the
recording control/list/chunk-refusal path, settings, V1 BLE name staging/reset,
meeting start/stop/reject state, IMU not-populated reporting, speaker prompt
state, wake-word arm/detect/disarm/reject state, diagnostics, privacy refusal,
and OTA readiness.

For the current no-panel WB55 bench, the `card_write` operation must still
include both `card_status=accepted/ok` and `final_card_status` with
`deferred_no_panel` or `deferred_controller_unknown`. The same artifact must
also include `settings_sleepy_screen_status`: the bench writes SettingsV1 with
`display_brightness=0`, waits for the ExpressionV1 `final_card_status`, and
then runs `settings_restore_after_sleepy`. It must also include the
contract-only `screen_expression_status` operation pointing at
`docs/validation/companion-screen-expression-host-status-sequence.json`, so the
real BLE artifact carries the same idle/sleepy/recording/low-battery/
sync-complete/error sequence baseline used for WBA comparison. It must also
include the contract-only `screen_expression_demo_status` operation pointing at
`docs/validation/companion-screen-expression-demo-host-status-sequence.json`,
so the artifact carries the full demo host baseline and
`held_steps_emit_no_host_status` for suppressed demo steps.
`settings_sleepy_screen_status` must run before recording-control/list checks,
and failed live JSON artifacts must keep `operations` plus
`partial_operation_count` so partial screen evidence survives BLE or hardware
loss. After a real e-paper panel is connected, rerun the same bench with `--expect-real-panel` and archive the JSON
artifact; that mode requires `final_card_status=rendered/ok` and sets
`real_panel_refresh_claimed=true`:

```powershell
pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource 'Companion-WB55,BLE-Companion' -Purpose "Companion real e-paper panel BLE evidence" -Run python .\tools\companion_ble_real_bench.py --name companion --timeout 20 --notify-timeout 10 --screen-final-timeout 30 --expect-real-panel --output .\.cache\validation\companion-real-panel-wb55-<timestamp>\companion-ble-real-bench.json --json
```

The current diagnostics collector has a fixture mode for the bundle format.
Real panel evidence must use a hardware-collected `summary.json` with the same
schema once that path exists, then place it at `diagnostics_bundle_artifact` in
the panel evidence record:

```powershell
pwsh -NoProfile -File .\tools\collect_companion_diagnostics.ps1 -Fixture -OutputDir .\.cache\validation\companion-real-panel-wb55-<timestamp>\diagnostics
```

Before executing the real-panel run, verify the fixed hardware acceptance
handoff:

```powershell
python .\tools\verify_expression_panel_wiring_preflight.py
python .\tools\verify_expression_panel_hardware_session.py
python .\tools\verify_expression_panel_hardware_acceptance_plan.py
```

The hardware handoff fixture is
`docs/validation/companion-screen-panel-hardware-acceptance-plan.json`.
Historical SSD1681 logs and operator observations remain retained, but the
current `wb55_real_panel_refresh` gate is `DEFERRED_HARDWARE` by
`docs/validation/companion-screen-wb55-hardware-recovery-gate.json`: replace or
cross-swap FTS02, prove solid white/black plus valid PREVGH/PREVGL rails, then
resume `wb55_touch_visual_acceptance`. Future target sessions can still use
`--expect-real-panel` and the generic filled evidence-record validator.
The session scaffold fixture,
`docs/validation/companion-screen-panel-hardware-session.json`, is verified by
`tools/verify_expression_panel_hardware_session.py` and keeps
`panel_hardware_session_scaffold` as the target-specific session contract. For
WB55, use `.cache/validation/companion-real-panel-wb55-<timestamp>` with
`panel-evidence-record.json`, `panel-hardware-facts.todo.json`,
`companion-ble-real-bench.json`, `diagnostics/summary.json`,
`visual/before_photo.jpg`,
`visual/after_photo.jpg`, and `operator-notes.md`.
Create a concrete session root with:

```powershell
python .\tools\init_expression_panel_evidence_record.py --target WB55 --session-root .\.cache\validation\companion-real-panel-wb55-<timestamp> --write-session
python .\tools\verify_expression_panel_session_directory.py --session-root .\.cache\validation\companion-real-panel-wb55-<timestamp> --target WB55
python .\tools\verify_expression_panel_hardware_facts.py --facts .\.cache\validation\companion-real-panel-wb55-<timestamp>\panel-hardware-facts.todo.json
python .\tools\render_expression_panel_facts_worksheet.py --session-root .\.cache\validation\companion-real-panel-wb55-<timestamp> --write --json .\.cache\validation\companion-real-panel-wb55-<timestamp>\panel-facts-worksheet.json --markdown .\.cache\validation\companion-real-panel-wb55-<timestamp>\panel-facts-worksheet.md
python .\tools\verify_expression_panel_driver_readiness.py --session-root .\.cache\validation\companion-real-panel-wb55-<timestamp>
python .\tools\apply_expression_panel_hardware_facts.py --facts .\.cache\validation\companion-real-panel-wb55-<timestamp>\panel-hardware-facts.todo.json --record .\.cache\validation\companion-real-panel-wb55-<timestamp>\panel-evidence-record.json --write
```

That evidence record must include decoded `e_paper.runtime_snapshot` health:
`panel.error_count=0`, no pending display queue work, and no dropped display
work. It must also include `diagnostics_bundle_artifact`, pointing at a
`summary.json` produced by `tools\collect_companion_diagnostics.ps1`, with
`epaper.runtime_snapshot_decoded` showing the same zero panel errors, zero
pending display queue work, and zero dropped display work. WBA55/WBA65 must
follow the same path with `*_stm32wba.*` target adapter files.

The screen acceptance fixture for this command is
`docs/validation/companion-screen-real-ble-bench.json`; it is verified by
`python .\tools\verify_expression_real_ble_screen_bench.py`.

Legacy A1/A2 reuse the Listener acceptance meaning and are compatibility
evidence only:

- A1: 5 to 8 quick short-recording rounds through Type's embedded BLE stream.
  Each round must complete `session_start -> audio_data -> session_stop`, create
  Type history with embedded audio stats and ASR final text, and be ready for the
  next round within the normal Listener short-smoke cadence.
- A2: one approximately one-minute recording through the same stream. The Type
  side must show continuous audio progress, ASR final text, complete embedded
  audio stats, and no transport timeout.

The legacy CLI proof path is Type's existing embedded BLE stream command:

```powershell
listener-type --probe-embedded-audio-ble-subscription 30000
listener-type --submit-embedded-audio-ble-stream 120000
```

The repeatable legacy compatibility wrapper is:

```powershell
pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource 'Companion-WB55,BLE-Companion' -Purpose "Companion A1/A2 bench validation" -Run pwsh -NoProfile -File .\tools\verify_companion_type_a1_a2.ps1 -Execute -WorkflowLockHeld
```

The wrapper is dry-run by default. With `-Execute`, it must already be inside
the workflow hardware lock, runs the Type BLE subscription probe, generates
16 kHz mono Chinese TTS WAV fixtures, plays them from the PC speaker near the
Companion microphone, runs A1 as six short
`--submit-embedded-audio-ble-stream 45000` rounds with `TYPE:READY:A1`, then
runs A2 as one `--submit-embedded-audio-ble-stream 120000` long window with
`TYPE:READY:A2`. Hardware acceptance defaults to `RequireA1Text=true` and
`RequireA2Text=true`; `-PromptOperator` is only for a physical placement prompt,
not for asking a human to speak. It records a JSON and Markdown summary under
`.cache/validation/companion-type-a1-a2-*`, including expected text, playback
WAV path, TTS voice, ASR final text, and transport stats.

The temporary Type debug page is no longer a Companion release dependency. It
can still be used for legacy bench comparison when `-IncludeTypeHarness` is
explicitly requested.

The repeatable Companion BLE OTA wrapper is:

```powershell
pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource 'Companion-WB55,BLE-Companion' -Purpose "Companion BLE OTA validation" -Run pwsh -NoProfile -File .\tools\verify_companion_ble_ota.ps1 -Execute -WorkflowLockHeld -PackagePath <companion-package.zip>
```

The wrapper is dry-run by default. With `-Execute`, it must already be inside
the workflow hardware lock, shows a Chinese desktop prompt with an audible
notification when requested, extracts `ota_manifest.json` and
`firmware_ota.bin` from the same Companion package, then invokes Companion Type,
which uses the shared Denzic Rust host core:

```powershell
companion-type.exe --firmware-ota-transfer ota_manifest.json firmware_ota.bin
```

It records the raw transfer output plus a `firmware_ota_result.json` transfer
evidence file under `.cache/validation/companion-ble-ota-*`. The BLE OTA gate
passes only when Type reports `status=PASS`, `protocol=denzic_ota_v1`, positive
data/status evidence, active-link confirmation, and completion/reboot handoff.

The matching wired-flash wrapper is:

```powershell
.\tools\verify_companion_wired_flash.ps1 -PackagePath <companion-package.zip>
```

By default it does not touch hardware. It calls the Companion flash tool in
check-only mode:

```powershell
.\tools\flash.ps1 -CheckOnly -FlashPackage -PackagePath <companion-package.zip>
```

and records the raw output plus `companion-wired-flash-summary.json` under
`.cache/validation/companion-wired-flash-*`. Real ST-LINK/SWD flashing is only
enabled with the workflow hardware lock:

```powershell
pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose "Companion wired factory flash validation" -Run pwsh -NoProfile -File .\tools\verify_companion_wired_flash.ps1 -Execute -WorkflowLockHeld -PackagePath <companion-package.zip>
```

That execute path shows a Chinese audible operator prompt when requested, then
calls:

```powershell
.\tools\flash.ps1 -Execute -WorkflowLockHeld -FlashPackage -PackagePath <companion-package.zip> -Port SWD
```

and passes only when the Companion wrapper reports `status=PASS`,
`mode=execute`, `action=flash`, `port=SWD`, and the STM32CubeProgrammer
verification line is present.

Companion is now treated as an independent product line. Listener-Type can
still be used as a temporary bench harness for early BLE/audio/flash evidence,
but the Companion release gate must not require Listener-Type product UI,
`CompanionSection`, or Type frontend OTA constants. Any Type harness evidence
is compatibility evidence only, not a Companion release dependency.

The retired Listener Type temporary Companion page can still be reviewed for
legacy bench comparison. In a Type dev server, open:

```text
http://127.0.0.1:<vite-port>/?visual=settings-companion&theme=dark
```

This renders the temporary Companion page directly when that legacy surface is
present. Screenshots from this path are optional and should not be used as the
default independent Companion release gate.

The same check can be captured automatically without touching hardware:

```powershell
.\tools\capture_type_companion_visual.ps1
```

It starts a local Type dev server, captures a headless browser screenshot and
rendered DOM, checks the page anchors, then writes
`type-companion-visual-summary.json` under `.cache/validation/type-companion-visual-*`.
The readiness preflight only runs this legacy smoke step when
`-IncludeTypeHarness` is passed.

Before taking hardware, run the fast no-hardware readiness preflight:

```powershell
.\tools\verify_companion_bringup_readiness.ps1
```

When there is no current OTA/wired package yet, run the static-only form. It
skips package, OTA dry-run, wired flash dry-run, and manual-gate emission, but
still checks the workspace submodule policy, devboard IOC import, static
Companion rules, screen-expression software acceptance, and git diff hygiene:

```powershell
.\tools\verify_companion_bringup_readiness.ps1 -StaticOnly
```

The fast preflight reuses the latest Companion package, checks the Companion
build environment, workspace submodule policy, devboard IOC import, OTA/static
contract, BLE probe fixture, recording cache model, recording FSM, diagnostics
static rules, screen-expression software acceptance, manual-gate checklist, and
git diff hygiene. It writes a JSON report under
`.cache/validation/companion-bringup-readiness-*` and `summary.md` beside
`summary.json`; the Markdown report is the human handoff checklist for the
remaining real-device gates, with the exact command/action and expected
evidence for each gate. It exits with `PASS_STATIC_MANUAL_GATES_REMAIN` when
all automatic checks pass and only the real-device gates remain.

To run the older Listener-Type bench harness checks as compatibility evidence,
use:

```powershell
.\tools\verify_companion_bringup_readiness.ps1 -IncludeTypeHarness
```

Before final static signoff, run the full preflight:

```powershell
.\tools\verify_companion_bringup_readiness.ps1 -Full
```

`-Full` rebuilds the OTA loader, normal bring-up app, OTA app, regenerates the
shared OTA/wired package, and then emits the same manual-gate list. Real
flashing, BLE OTA, and A1/A2 still require the workflow hardware lock plus
Chinese audible operator prompts owned by their wrapper tools. Add
`-IncludeTypeHarness` only when the legacy Listener-Type bench harness should
also be checked.

For screen-expression software acceptance, use the aggregate runner before
taking the hardware lock:

```powershell
python .\tools\run_expression_acceptance.py --dry-run --skip-build --output .\.cache\validation\companion-screen-acceptance-dry-run.json
python .\tools\run_expression_acceptance.py --output .\.cache\validation\companion-screen-acceptance-run.json
```

The dry-run writes the planned command list to
`companion-screen-acceptance-dry-run.json`; the full run reads
`docs/validation/companion-screen-acceptance-index.json`, deduplicates
validation commands, keeps the `wb55_real_panel_refresh` hardware gate
as PASS, leaves `wb55_touch_visual_acceptance` pending for the operator, and
records per-item command status.

When hardware is ready, the preferred path is the aggregate acceptance runner:

```powershell
pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource 'Companion-WB55,BLE-Companion' -Purpose "Companion hardware acceptance" -Run pwsh -NoProfile -File .\tools\verify_companion_hardware_acceptance.ps1 -Execute -WorkflowLockHeld -PackagePath <companion-package.zip> -EvidencePath <companion_ui_screenshot_or_log>
```

The runner first ensures the CPU2 BLE stack, then flashes the same Companion
package over wired SWD so the board is running the unified Companion app. It
then hard-resets into the app, runs the Companion-native BLE GATT bench, runs
the Companion-owned BLE OTA wrapper, runs the native GATT bench again after OTA
reboot, and feeds the required summary files into
`verify_companion_manual_gate_evidence.ps1`. The no-hardware readiness preflight
dry-runs this aggregate entry and records
`companion-hardware-acceptance-summary.json` under the readiness report directory.

## Step 5.5 - Operator Chain Simulation For 2.3

After the Companion-owned hardware acceptance runner is PASS, use the operator
chain validator to exercise the remaining pendant MVP flow in the same order a
human would use the device:

```powershell
.\tools\verify_companion_operator_chain.ps1
```

The validator is Companion-owned and does not require Listener-Type. It loads
the latest real Companion BLE bench and hardware acceptance evidence, regenerates
a BLE-written e-paper fallback card, and checks this seven-stage chain:

1. Boot/default display, recording card, sync-complete card, and a BLE-written
   short-card fallback render.
2. Host BLE scan/connect/status on the real Companion NUCLEO GATT surface.
3. Card write and recording/synced display state coverage.
4. Recording metadata, chunk pull, CRC/SHA verification, resume,
   delete-after-sync, and privacy erase. The real NUCLEO chain now has
   separate hardware evidence for SAI microphone capture into QSPI flash and
   BLE pull/delete. The latest automatic BLE-triggered chain is
   `.cache/validation/companion-flash-recording-chain-20260630-155826/companion-flash-recording-chain.json`.
   The physical-button version must use the NUCLEO SW3/B3 user button (PD1)
   and `tools/companion_button_recording_chain.py`; it exports the pulled PCM
   as WAV, checks audio quality, verifies reset persistence, refuses bad
   offset and bad-SHA delete requests, then performs delete-after-sync. The
   latest physical SW3 evidence is
   `.cache/validation/companion-button-recording-chain-20260630-155232/companion-button-recording-chain.json`.
5. Host pull/log/export/OTA blocker behavior from the BLE matrix plus executed
   Companion BLE OTA evidence.
6. Power-state evidence for boot/idle, advertising, connected idle, recording,
   e-paper refresh, chunk transfer, and charge/external-power, with the
   measurement method and caveat recorded for each state.
7. PCB go/no-go recommendation.

It writes:

```text
.cache/validation/companion-operator-chain-<timestamp>/companion-operator-chain-summary.json
.cache/validation/companion-operator-chain-<timestamp>/companion-operator-chain-summary.md
.cache/validation/companion-operator-chain-<timestamp>/display_fallback/ble_card_write_*.pbm
```

`PASS` means the automated operator chain is coherent and has evidence. It does
not claim the final physical chain is complete. The summary keeps
`final_physical_confirmation.status=PENDING_HUMAN` until a human observes the
real e-paper target, real button/microphone/storage flow, non-empty real
recording pull/delete, and measured current for the listed power states. The
default machine recommendation is to continue dev-board iteration before the
first pendant PCB when display, storage, or power are still fallback/dev-board
evidence.

For the current development-board checklist, use
`docs/companion_devboard_physical_checklist.md`. In this phase the physical
record button is the NUCLEO-WB55RG `SW3/B3` user button on `PD1`. If no real
e-paper panel is connected, record `N/A` rather than treating PBM fallback
renders as panel evidence. Use `-NoEpaperPanel` with
`tools\verify_companion_physical_signoff.ps1` for the current no-panel bench.
When a panel is present, the BLE evidence must include `final_card_status` and
`real_panel_refresh_claimed=true` from the `--expect-real-panel` run before the
row can move out of `N/A`. The same artifact must include
`screen_expression_status` so the real-panel record keeps the six-face
ExpressionV1 sequence baseline. Start from the panel evidence scaffold, fill
every `TODO`, including `real_ble_bench_artifact`,
`diagnostics_bundle_artifact`, target pins, timing, visual before/during/after
files, hashes, decoded `e_paper.runtime_snapshot` health, and the target
adapter file, then validate it:
The real BLE artifact should also include `screen_expression_demo_status` so
the panel record can compare all demo faces against
`docs/validation/companion-screen-expression-demo-host-status-sequence.json`,
while visual evidence still proves the real panel image.

On WB55 the scaffold already carries the SPI2 transport facts from
`docs/validation/companion-screen-panel-wiring-preflight.json`: SPI2, PA9 SCK,
PC1 MOSI, PC2 MISO, and PA6 `SPI2_CS`. The remaining controller, DC/RST/BUSY,
power, timing, visual, BLE, diagnostics, and adapter fields must still be
filled from hardware evidence.

Use the hardware session scaffold before the real-panel session so the evidence
files land in a target-specific directory. The WB55 root is
`.cache/validation/companion-real-panel-wb55-<timestamp>` and should contain
`panel-evidence-record.json`, `panel-hardware-facts.todo.json`,
`companion-ble-real-bench.json`, `diagnostics/summary.json`,
`visual/before_photo.jpg`,
`visual/after_photo.jpg`, and `operator-notes.md`. Validate that contract with
`python .\tools\verify_expression_panel_hardware_session.py`, then validate the
concrete generated directory with
`python .\tools\verify_expression_panel_session_directory.py --session-root <session-root> --target WB55`.
That `panel_session_directory_preflight` keeps the record at `DRAFT_UNFILLED`
validates the hardware facts draft, and proves the draft still fails the final
real-panel validator until hardware facts are filled. If the session already
contains `panel-bringup-operator-packet.json` or
`panel-bringup-operator-packet.md`, the same preflight also checks that the
packet matches the current renderer, keeps the quoted
`with-lock -Resource 'Companion-WB55,BLE-Companion'` command, and preserves
`partial_operation_count` evidence for failed live BLE runs. Use
`panel_hardware_facts_intake` to fill the generated controller, DC/RST/BUSY,
power, voltage, and reset/BUSY/full-refresh timing facts in
`panel-hardware-facts.todo.json`; changing that file to
`READY_FOR_DRIVER_FACTS` only says the target driver has enough input facts and
does not claim real refresh. The `panel_driver_readiness_report`
(`docs/validation/companion-screen-panel-driver-readiness.json`, verified by
`python .\tools\verify_expression_panel_driver_readiness.py`) reports
`BLOCKED_ON_HARDWARE_FACTS` for the DRAFT file and
`READY_FOR_DRIVER_IMPLEMENTATION` only after the facts are complete. The
`panel_hardware_facts_worksheet`
(`docs/validation/companion-screen-panel-facts-worksheet.json` and
`docs/validation/companion-screen-panel-facts-worksheet.md`, rendered by
`python .\tools\render_expression_panel_facts_worksheet.py`) turns those same
missing fields into a fillable operator worksheet. The
`panel_bringup_operator_packet`
(`docs/validation/companion-screen-panel-bringup-operator-packet.json` and
`docs/validation/companion-screen-panel-bringup-operator-packet.md`, rendered by
`python .\tools\render_expression_panel_bringup_packet.py`) combines the
session commands, worksheet, readiness gate, target driver/evidence commands,
and visual artifact paths for the operator without claiming real refresh. After
that, use
`python .\tools\verify_expression_panel_driver_readiness.py --session-root <session-root> --require-ready`
as the final pre-driver check, then use
`panel_hardware_facts_bridge` to
copy those facts into `panel-evidence-record.json` while keeping the evidence
record `DRAFT_UNFILLED`; this bridge still does not claim real refresh. WBA55/WBA65 use the same
`panel_hardware_session_scaffold`
structure with their own
`companion-real-panel-wba55-<timestamp>` or
`companion-real-panel-wba65-<timestamp>` roots, `*_stm32wba.*` adapters,
`--expect-real-panel`, `tools\collect_companion_diagnostics.ps1`, and
`python .\tools\verify_expression_panel_evidence_record.py --record`.

```powershell
python .\tools\init_expression_panel_evidence_record.py --target WB55 --session-root .\.cache\validation\companion-real-panel-wb55-<timestamp> --write-session
python .\tools\verify_expression_panel_session_directory.py --session-root .\.cache\validation\companion-real-panel-wb55-<timestamp> --target WB55
python .\tools\verify_expression_panel_hardware_facts.py --facts .\.cache\validation\companion-real-panel-wb55-<timestamp>\panel-hardware-facts.todo.json
python .\tools\render_expression_panel_facts_worksheet.py --session-root .\.cache\validation\companion-real-panel-wb55-<timestamp> --write --json .\.cache\validation\companion-real-panel-wb55-<timestamp>\panel-facts-worksheet.json --markdown .\.cache\validation\companion-real-panel-wb55-<timestamp>\panel-facts-worksheet.md
python .\tools\render_expression_panel_bringup_packet.py --session-root .\.cache\validation\companion-real-panel-wb55-<timestamp> --write --json .\.cache\validation\companion-real-panel-wb55-<timestamp>\panel-bringup-operator-packet.json --markdown .\.cache\validation\companion-real-panel-wb55-<timestamp>\panel-bringup-operator-packet.md
python .\tools\verify_expression_panel_driver_readiness.py --session-root .\.cache\validation\companion-real-panel-wb55-<timestamp>
python .\tools\apply_expression_panel_hardware_facts.py --facts .\.cache\validation\companion-real-panel-wb55-<timestamp>\panel-hardware-facts.todo.json --record .\.cache\validation\companion-real-panel-wb55-<timestamp>\panel-evidence-record.json --write
python .\tools\verify_expression_panel_evidence_record.py --record <panel-evidence-record.json>
```

The Type temporary Companion page real-device gate is optional legacy bench
evidence. Enable it explicitly with `-IncludeTypeUiGate`:

```powershell
pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource 'Companion-WB55,BLE-Companion' -Purpose "Companion Type UI validation" -Run pwsh -NoProfile -File .\tools\verify_companion_type_ui_manual.ps1 -Execute -WorkflowLockHeld -PackagePath <companion-package.zip> -EvidencePath <companion_ui_screenshot_or_log>
```

It shows a Chinese audible prompt, waits while the operator runs BLE
subscription, A1 smoke, A2 smoke, and confirms the `总体验收` command from the
Type page, then writes `companion-type-ui-manual-summary.json` with
`companion_type_ui_manual_result_json`.

After the real-device runs, close the gate with the evidence verifier:

```powershell
.\tools\verify_companion_manual_gate_evidence.ps1 -PackagePath <companion-package.zip> -NativeBleBenchPath <companion-ble-real-bench.json> -BleOtaEvidencePath <companion-ble-ota-summary.json> -WiredFlashEvidencePath <companion-wired-flash-summary.json>
```

Run it with `-ChecklistOnly` before hardware to generate a pending checklist
without failing. Without `-ChecklistOnly`, the independent gate requires
Companion-native BLE GATT JSON status `PASS`, BLE OTA
`protocol=denzic_ota_v1`, and wired ST-LINK/SWD factory flash completion.
Add `-A1A2SummaryPath <companion-type-a1-a2-summary.json> -IncludeTypeHarness`
only when collecting optional legacy Type A1/A2 evidence. Add
`-TypeUiEvidencePath <companion-type-ui-manual-summary.json> -IncludeTypeUiGate`
only when collecting the optional legacy Type page evidence.

## Step 6 - SPI Flash Audio Storage

Move the captured SAI microphone PCM buffer into external QSPI/SPI NOR flash,
then pull the same object over Companion-native BLE. The current NUCLEO app
keeps up to 60 seconds of PCM16 mono at 16 kHz for the bench chain. That is
`1,920,000` bytes of raw audio before the small recording header. A one-hour
meeting in the same raw format would be `115,200,000` bytes, so it does not fit
the current 16 MiB external flash part. One-hour meetings require streaming to
the host/phone, compression, or a larger storage part.

Acceptance:

- Flash the NUCLEO app under the workflow hardware lock.
- Run the BLE-controlled storage chain:

  ```powershell
  pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose "real BLE recording to QSPI flash chain validation" -Run python .\tools\companion_flash_recording_chain.py --notify-timeout 25 --record-seconds 1.0 --chunk-bytes 180
  ```

- PASS evidence must show `recording_start`, `recording_stop_store`,
  non-empty `recording_list`, `source_mode=1` for the SAI microphone path,
  byte count, per-packet CRC, matching host/device SHA-256, successful
  `delete_after_sync`, an empty list after delete, and exported
  `ble-recording-16k-mono.wav`/`.pcm` artifacts.
- Run the SW3 physical-button chain:

  ```powershell
  pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose "Companion SW3 button recording chain validation" -Run python .\tools\companion_button_recording_chain.py --notify-timeout 25 --chunk-bytes 180
  ```

- SW3 PASS evidence must show a Chinese desktop prompt for pressing SW3/B3
  (PD1) to start and stop, one stored flash recording, BLE pull with
  CRC/SHA verification, exported `sw3-button-recording-16k-mono.wav`, audio
  quality PASS, SWD hard reset, the same recording still present after reset,
  bad offset rejection, bad SHA delete refusal, bounded diagnostics pull,
  successful `delete_after_sync`, and an empty list after delete.

Current PASS evidence from the earlier short-cap build:

```text
.cache/validation/companion-button-recording-chain-20260630-155232/companion-button-recording-chain.json
.cache/validation/companion-flash-recording-chain-20260630-155826/companion-flash-recording-chain.json
```

Summary from the SW3 physical-button run, collected before the 60-second cap
change: `total_length=32768`,
`duration_s=1.024`, exported
`sw3-button-recording-16k-mono.wav`, audio quality PASS with
`rms=359.91`, `peak=1840`, `zero_ratio=0.023193`, reset persistence PASS,
bad-offset and bad-SHA refusals PASS, bounded diagnostics PASS, and
`recording_list.count=0` after delete.

Summary from the automatic BLE-triggered run: `total_length=23360`,
`duration_ms=730`, `packet_count=130`, `content_crc32=0xd1a92cc1`, host SHA
and device final SHA both
`94ff8c2c60f125a8353b4251714ba75a092fa38989bb53f5c49d56e514da2fcf`, and
`recording_list.count=0` after delete.

The current firmware should be rebuilt/flashed before new hardware evidence is
recorded so `FLASH_RECORDING_DEV_MAX_SECONDS=60` and the BLE chain WAV export
are both present in the artifact.

2026-07-09 WB55 microphone status:

- The host recording/ASR route is Companion Type first. `Listener-Type` may be
  used only as the current compatibility CLI behind
  `tools\companion_recording_to_minutes.py --asr-provider companion-type`.
- Simulated file input through the Companion Type/Listener-Type bridge now
  PASSes with real Type ASR output. The bridge passes absolute WAV/debug paths
  to survive installed-app single-instance dispatch, filters Type diagnostic
  status text out of transcript parsing, and waits for `asr_final` or
  `submit-embedded-audio-streaming-file done` instead of stopping on the first
  partial transcript. Evidence:
  `.cache\validation\companion-type-simulated-mic-short-final` produced
  provider `companion_type` transcript `你好，小伴录音测试。`;
  `.cache\validation\listener-simulated-mic-long-to-minutes-final` produced
  `这次需要确认 V K A E 和 Audio data 没有被重新解释。`; and
  `.cache\validation\listener-simulated-mic-short-final` produced
  `你好，小伴录音测试。` with wake-word postprocess detection of `小伴`.
- Historical I2S-style WB55 artifacts under
  `.cache\validation\companion-real-mic-silence-48kto16k-falling-serial`,
  `.cache\validation\companion-real-mic-short-tts-48kto16k`, and the
  `20260709` PC-speaker runs remain useful as evidence that the BLE, QSPI
  recording, chunk pull, WAV export, and delete-after-sync chain worked before
  the microphone was correctly identified. They are no longer the accepted
  microphone signal-quality baseline.
- The accepted WB55 devboard microphone baseline is now SPH0655-compatible PDM
  through raw-SAI DMA, MSB+CIC3, MCKDIV 31, decimation 96, preamp shift 3, and
  a 450-block stage buffer with the firmware built using `-Optimization O2`.
  The PC-speaker TTS run produced `122880` bytes / `3.84s`,
  `audio_quality.status=PASS`, `rms=1669.28`,
  `missing_packets=0`, and Companion Type ASR returned
  `你好，小伴录音测试。`.
  Evidence:
  `.cache\validation\mic-fast2-20260710-060913`
  and
  `.cache\validation\mic-fast2-20260710-060913-asr`.
- True acoustic capture is accepted for the firmware-to-Type path. The short
  margin run now shows zero raw-DMA overruns and `diag=0` steady capture at
  `10 ms`; the remaining microphone work is a longer soak and then, for WBA,
  a target-native HAL PDM/PDM2PCM/MDF/ADF path while preserving the same
  16 kHz PCM16 Companion contract.

## Step 6A - Recording Postprocess And Meeting Minutes

After a recording has been pulled and verified, process it on the host. The
pendant keeps capture/storage/transfer/delete responsibilities; transcription,
summary, action items, and meeting-minute exports are host-side artifacts.

Acceptance:

- Input may be a `companion_button_recording_chain.py` or
  `companion_flash_recording_chain.py` JSON artifact, or a direct WAV/PCM path.
- If a transcript is provided, the host writes
  `companion-meeting-minutes.json` and `companion-meeting-minutes.md` with
  source audio SHA-256, transcript segments, summary bullets, decisions,
  action items, questions, keywords, and privacy/delete policy.
- If no transcript is provided, the output state is `needs_transcription` and
  records the next processing actions without claiming AI summary quality.
- The model must keep delete-after-sync tied to verified source byte length and
  SHA-256.
- `tools\companion_recording_to_minutes.py` must run the same host chain from
  direct audio, an existing chain artifact, automatic BLE capture, or the SW3
  physical-button chain. Listener-Type may be used as an optional ASR provider,
  but Companion must not edit or depend on Type product UI.

Run:

```powershell
python .\tools\verify_companion_postprocess.py
python .\tools\verify_companion_recording_to_minutes.py
```

Simulated postprocess from any pulled WAV:

```powershell
python .\tools\companion_recording_postprocess.py --audio-path .\.cache\validation\companion-button-recording-chain-<timestamp>\sw3-button-recording-16k-mono.wav --transcript-text "Billy: 待办：oai1 负责整理会议纪要。"
```

For the full recording-chain artifact:

```powershell
python .\tools\companion_recording_postprocess.py --recording-chain .\.cache\validation\companion-button-recording-chain-<timestamp>\companion-button-recording-chain.json --transcript-file .\transcript.txt
```

For the one-command host chain:

```powershell
python .\tools\companion_recording_to_minutes.py --recording-chain .\.cache\validation\companion-button-recording-chain-<timestamp>\companion-button-recording-chain.json --transcript-file .\transcript.txt --wake-phrase "你好 companion"
```

For a live BLE capture plus optional Type ASR bridge, run under the workflow
hardware lock:

```powershell
pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource 'Companion-WB55,BLE-Companion' -Purpose "Companion recording to minutes validation" -Run python .\tools\companion_recording_to_minutes.py --ble-auto --record-seconds 10 --asr-provider companion-type --wake-phrase "你好 companion"
```

## Step 7 - Desktop Pull

Use a desktop BLE tool before building a full app.

Acceptance:

- Tool scans for the Companion device.
- Tool connects and pulls one metadata record or small sample payload.
- Failure cases are explicit: no device, disconnect, timeout.
