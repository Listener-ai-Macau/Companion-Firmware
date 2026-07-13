# Companion E-Paper Renderer

This directory owns the no-hardware Companion pendant e-paper card model and
framebuffer renderer. The code is intentionally independent from an SPI driver
so it can be tested before a panel is wired.

The screen-expression acceptance map lives in
`docs/companion_screen_expression_system.md`.
The BLE-to-expression policy lives in `expression_policy.py`; it maps status
snapshot data and diagnostic event names into ExpressionV1 cards without
depending on the display driver. It also treats quiet-hours settings and
`display_brightness=0` as low-priority `sleepy` hints without hiding recording,
low-battery, or error expressions.
The firmware-side ExpressionV1 state model lives in `expression_state.h/.c`.
It mirrors the same state names, priorities, and user-visible copy for WB55
event-driven screen updates and the later WBA adapter. It also suppresses
signals that resolve to the already-visible face so e-paper refreshes are not
repeated without a visible product change. Its elapsed-time tick API lets
transient faces recover to idle while keeping recording, low-battery, and error
states visible until a real event changes them.
`tools/verify_expression_priority_matrix.py` records the expression priority
matrix in `docs/validation/companion-screen-expression-priority-matrix.json`.
It covers every current face against every signal, including settings sleepy,
battery recovered, duplicate suppression, lower-priority blocking, and
transient recovery rules for WB55 and future WBA scheduler adapters.
`tools/verify_expression_input_source_matrix.py` records the expression input
source matrix in
`docs/validation/companion-screen-expression-input-source-matrix.json`. It
links boot/default idle, diagnostic events, SettingsV1, DeviceStatusV1,
BatteryChargeV1, Recording FSM state, MeetingStatusV1, SpeakerStatusV1,
WakeWordStatusV1, and OtaReadinessV1 to the focused fixtures a WBA port must
preserve.
`comp_epaper_expression_signal_is_supported()` exposes the same signal table as
the decision/apply path, so WB55 and future WBA glue can reject an unknown
signal before visible state or display queue work changes.
Expression state telemetry is portable too:
`comp_epaper_expression_state_snapshot()` reports the current face, last
signal, revision, visible age, auto-recovery dwell, and suppressed duplicate
count for WB55 and future WBA scheduler hooks.
The generated `expression_host_manifest`
(`docs/validation/companion-screen-expression-host-manifest.json` and
`docs/validation/companion-screen-expression-host-manifest.md`, rendered by
`python .\tools\render_expression_host_manifest.py`) is the host-facing
acceptance table for every ExpressionV1 face, including copy, priority,
source signals, policy cases, CardStatusV1/diagnostic observability, and the
legacy six-face host coverage gap.
The generated `expression_visual_acceptance_matrix`
(`docs/validation/companion-screen-expression-visual-acceptance-matrix.json`
and
`docs/validation/companion-screen-expression-visual-acceptance-matrix.md`,
rendered by
`python .\tools\render_expression_visual_acceptance_matrix.py`) connects each
face's PBM fixtures and visual contract metrics to the same copy, source
signals, policy cases, and host coverage. It is AI-testable now and does not
claim real panel refresh.
The diagnostic-event bridge lives in `expression_events.h/.c`. It maps portable
Companion diagnostic event codes into ExpressionV1 signals and intentionally
ignores `e_paper.*` update events so display failures cannot self-trigger a
refresh loop.
Recording FSM state snapshots can use
`comp_epaper_expression_signal_from_recording_state()` to map active,
stopping, transfer, canceled, and error-recovery states into the same
ExpressionV1 signals without depending on WB55 or future WBA platform glue.
`tools/verify_expression_firmware_state.py` keeps that C model aligned with
the Python renderer/policy and writes
`docs/validation/companion-screen-firmware-expression-state.json`.
`tools/verify_expression_copy_contract.py` keeps ExpressionV1 title/body/footer
copy aligned across the renderer, firmware expression table, catalog, layout,
priority, and generated PBM fixtures. Its fixture is
`docs/validation/companion-screen-expression-copy-contract.json`.
`tools/verify_expression_state_telemetry.py` records the expression state
stats snapshot contract in
`docs/validation/companion-screen-expression-state-telemetry.json`.
The WB55 firmware queue boundary lives in `display_queue.h/.c`; BLE callbacks
enqueue card or expression display work there and `Companion_Display_Task` owns
completion/status publishing until a real panel driver is connected.
`tools/verify_display_queue_fault_paths.py` records queue-full,
payload-too-long, unsupported-expression, and expression rollback behavior in
`docs/validation/companion-screen-display-queue-faults.json`.
Display queue telemetry is also portable: `display_queue.h/.c` tracks pending
count, high-water count, dropped count, queue capacity, payload bound, and
in-memory sequence without adding platform dependencies. Its stats snapshot API
lets WB55 and future WBA scheduler code observe queue pressure without reaching
into queue internals. `tools/verify_display_queue_telemetry.py` records that
contract in `docs/validation/companion-screen-display-queue-telemetry.json`.
`tools/verify_expression_display_drain.py` records the display drain contract
in `docs/validation/companion-screen-display-drain-contract.json`. It keeps
`Companion_Display_Task` on a one-request-per-pass lifecycle: dequeue, target
panel refresh, runtime diagnostics, final CardStatusV1, then reschedule only
when queue work remains.
WB55 startup enqueues the `BOOT_IDLE` ExpressionV1 signal through that same
queue after the display task is registered, so the default face is covered by
the same acceptance path as runtime expressions.
WB55 also wires transient expression recovery through a single-shot `HW_TS`
timer: the interrupt callback only schedules `Companion_Display_Task`, and the
task feeds elapsed `HAL_GetTick()` time into the portable state tick API before
enqueueing any recovery face.
WB55 DeviceStatusV1 publishing can feed the portable device-status mapper:
faults request the error face, active audio mode requests recording, and
disconnected mode requests the same low-priority sleepy signal used by screen
settings.
WB55 MeetingStatusV1, SpeakerStatusV1, and WakeWordStatusV1 publishing can feed
portable interaction-status mappers: meeting progress requests recording,
thinking, sync-complete, or error; speaker prompt state requests speaking or
error; wake status requests idle, listening, or error.
WB55 SettingsV1 writes also feed the expression state: `display_brightness=0`
or the quiet-hours flag requests the portable settings sleepy signal, while
clearing that hint recovers only settings-caused sleepy back to idle.
WB55 BatteryChargeV1 publishing can feed the same event bridge as
`battery_charging.sample`; the devboard fixture stays at 100 percent, but real
low-battery data can now request the low-battery face without adding a
platform-specific expression rule. Recovered samples use the portable
`COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED` guard, which only clears a
visible low-battery face and does not hide recording, error, sleepy, or other
active expressions.
WB55 OtaReadinessV1 publishing can feed the portable OTA blocker mapper:
low-battery blockers request the low-battery face, while other nonzero OTA
blockers request the error face only after startup publishing has completed.
`tools/verify_expression_status_observability.py` keeps the host-facing
CardStatusV1 render-state/error-code contract aligned with the display queue,
dry-run panel adapter, diagnostic events, and no-hardware BLE fixture.
The no-hardware BLE matrix includes `screen_expression_status`, which
correlates boot idle, settings sleepy, and recording ExpressionV1 requests with
CardStatusV1 records and diagnostic expression/signal payloads.
`tools/verify_expression_demo_host_status_sequence.py` records
`docs/validation/companion-screen-expression-demo-host-status-sequence.json`
for the `screen_expression_demo_host_status_sequence` acceptance item. Its
`screen_expression_demo_status` contract extends the host-visible status
baseline to every demo face and records `held_steps_emit_no_host_status` for
suppressed demo steps.
`tools/render_expression_storyboard.py` turns the journey fixture into
`docs/validation/epaper/expression-storyboard.svg`, so wake, recording,
settings, low-battery, error, and recovery flows can be reviewed visually
without panel hardware.
`tools/verify_expression_demo_sequence.py` records
`docs/validation/companion-screen-expression-demo-sequence.json` and the
human checklist
`docs/validation/companion-screen-expression-demo-sequence.md` for the
`screen_expression_demo_sequence` acceptance item. It gives WB55 and later
WBA55/WBA65 bring-up a stable one-by-one no-hardware demo order before real
panel evidence is claimed.
`tools/verify_expression_demo_panel_handoff.py` records
`docs/validation/companion-screen-expression-demo-panel-handoff.json` and the
human checklist
`docs/validation/companion-screen-expression-demo-panel-handoff.md` for the
`screen_expression_demo_panel_handoff` acceptance item. It maps the same demo
order onto WB55/WBA55/WBA65 panel sessions and records
`manual_visual_required_faces` when the current real BLE
`screen_expression_status` baseline does not cover every demo face.
`tools/verify_expression_visual_contract.py` records
`docs/validation/companion-screen-expression-visual-contract.json`, guarding
the PBM assets with an ExpressionV1 visual contract against blank, overfilled,
or visually duplicate faces before WB55 or future WBA ports reuse them. The
Revision 14 is enclosure-aware: the product housing supplies the cat-head
silhouette, so the 200x200 panel draws only internal eyes, a compact nose/mouth
rig, motion cues, and status marks on white. It must not redraw ears, a head
outline, or whiskers.
Idle is one quiet composed pose after its initial refresh, while CEMP retains
replaceable timing and visual resources for touch reactions and product events.
The current WB55 revision 52 candidate pack keeps the electronic-pet rig external-first
and uses generated-sheet-import PBM frames as the normal expression/menu art
path: 33 clips, 159 timeline frames, a 287732-byte CEMP pack, and CRC32 `0xDEFC096E`.
Revision 52 still needs WB55 provision/normal runtime recheck; revision 51 is
the last machine-proven pack.
The `premium pet art contract` is checked by
`python .\tools\verify_premium_pet_art_contract.py`; it guards whole-face
motion across eyes/brows, mouth/nose, cheeks, and state ornaments so future
generated-art tuning does not regress to eye-only expression swaps.
Identical decoded rasters share one payload record while retaining independent
timing, dirty rectangles, and random access for every clip frame. The ordinary
firmware mounts it from QSPI and does not retain the provision blob in MCU
Flash. The home directory keeps a continuous 0..84 pixel logical scroll offset
and selects one of 43 external two-pixel frames per language for the 200x200
e-paper panel. A fixed 30px compact system header and 8px white gutter sit
above the scroll viewport; the home viewport then keeps a 48px pet status card
and 34px function rows, so the six product entries can never draw over
navigation and the touch hit-test matches the generated-art layout.
The `menu drag continuity contract` is checked by
`python .\tools\verify_menu_drag_continuity_contract.py`; it guards the home
menu frames against fixed-header drift, gutter overdraw, backward scrollbar
motion, and excessive adjacent-frame jumps.
Menu pet identity is limited to inner face marks: the physical shell owns the
cat outline, while generated menu pages and the MCU rescue renderer avoid ears,
head outlines, and whiskers. Vertical drag uses a finger-origin anchor rather
than incremental integration, never snaps to an item, and display-queue
coalescing retains only the latest render frame while a refresh is active.
Opening a function is tap-only inside the menu: the selected row gets a short
press-cue partial refresh, then the destination page arrives with another
partial refresh. Daily mode opens the menu through a nearly-still 3 s hold
anywhere on the screen, after a 650 ms pet tease; normal taps and directional
swipes remain pet interactions.
Revision 23 adds `pet_expression.h/.c`, a portable parameterized face composer.
It maps product state plus continuous touch gaze, eyelid, mouth, cheek, and
mark parameters into the existing one-bit framebuffer. CEMP remains the
external-Flash source of replaceable menu art, timelines, and larger visual
assets; the composer adds no static full-screen expression arrays or second
framebuffer to normal firmware. A WBA target reuses the same pose/render API and
only replaces the target panel transport and profile facts.
`tools/render_expression_visual_acceptance_matrix.py` records
`docs/validation/companion-screen-expression-visual-acceptance-matrix.json`
and `docs/validation/companion-screen-expression-visual-acceptance-matrix.md`,
showing all 10 faces, both PBM variants, host coverage, and the deferred real
panel boundary for the `expression_visual_acceptance_matrix` acceptance item.
`tools/verify_expression_layout_contract.py` records
`docs/validation/companion-screen-expression-layout-contract.json`, guarding
the ExpressionV1 title/body/footer layout contract against truncation or
body/footer overlap on the supported screen variants.
The panel adapter contract lives in `panel_adapter.h/.c`. The production WB55
bring-up build selects the real SSD1681 target backend; dry-run remains available
only for no-hardware fixtures and unsupported targets.
The panel adapter boundary keeps this file pair as a portable dispatcher: real
display transport must be added through the `comp_epaper_panel_refresh_fn_t`
target-owned refresh callback from a target adapter, not by adding board IO to
the portable screen files.
The current WB55 target entry is `panel_target_stm32wb.h/.c`.
WB55 initializes the panel path through `companion_epaper_panel_stm32wb_init()`,
which selects `panel_target_stm32wb_ssd1681.c` for the production bring-up
configuration. Controller, pin, timing, full/partial/fast refresh, operator
orientation, and physical contact evidence are recorded. Future WBA work adds
a separate `*_stm32wba.*` target adapter without changing portable panel files.
`tools/verify_expression_panel_gate.py` verifies the completed WB55 real-panel
gate while retaining the remaining human touch/visual acceptance and records it in
`docs/validation/companion-screen-panel-hardware-gate.json`.
`tools/verify_expression_panel_adapter_boundary.py` records the callback
boundary in
`docs/validation/companion-screen-panel-adapter-boundary.json`.
`tools/verify_expression_panel_target_stm32wb.py` records the WB55 target
adapter scaffold in
`docs/validation/companion-screen-panel-target-stm32wb.json`.
`tools/verify_expression_panel_adapter_behavior.py` records the panel adapter
behavior matrix in
`docs/validation/companion-screen-panel-adapter-behavior.json`, including
dry-run, missing-callback, callback OK/BUSY/error, and request-identity
invariants.
Panel adapter telemetry is portable as well: `comp_epaper_panel_adapter_snapshot()`
reports hardware/configuration state, attempts, rendered/deferred/error counts,
and the last adapter result without adding target dependencies.
`tools/verify_expression_panel_adapter_telemetry.py` records that contract in
`docs/validation/companion-screen-panel-adapter-telemetry.json`.
The screen runtime snapshot lives in `screen_runtime.h/.c`. It aggregates the
ExpressionV1 state, display queue, and panel adapter stats snapshots into one
portable runtime view. WB55 `Companion_Display_Task` uses
`comp_epaper_screen_runtime_snapshot()` for update diagnostics and queue
rescheduling; future WBA display tasks should use the same aggregate instead
of reading private state fields. `tools/verify_expression_screen_runtime_snapshot.py`
records the contract in `docs/validation/companion-screen-runtime-snapshot.json`.
Runtime diagnostics are recorded by target glue from that aggregate snapshot.
WB55 emits `e_paper.runtime_snapshot` with expression current/last signal,
display queue pending/high-water/dropped counts, and panel deferred/error
counts. `tools/verify_expression_screen_runtime_diagnostics.py` records that
contract in `docs/validation/companion-screen-runtime-diagnostics.json`; future
WBA target glue should keep the same event payload while replacing only the
platform scheduler, BLE adapter, and panel transport.
Host runtime diagnostic decode lives in `tools/decode_diag_log.py`: it keeps
the raw packed args and adds `decoded_args` for `e_paper.runtime_snapshot`.
`tools/verify_expression_screen_runtime_diagnostic_decode.py` records that
contract in `docs/validation/companion-screen-runtime-diagnostic-decode.json`
so WBA bring-up logs can reuse the same expression, queue, and panel field
names.
The no-hardware diagnostics bundle fixture also includes this event:
`tools/collect_companion_diagnostics.ps1 -Fixture` writes a bounded tail with
`e_paper.runtime_snapshot` and `epaper.runtime_snapshot_decoded`, checked by
`tools/verify_companion_diagnostics_static.py`.
`tools/verify_expression_real_ble_screen_bench.py` records the real BLE screen
bench contract in `docs/validation/companion-screen-real-ble-bench.json`; the
bench now captures accepted and final CardStatusV1 records for `card_write` and
`settings_sleepy_screen_status`, then uses `--expect-real-panel` before
claiming a rendered/ok hardware refresh. The settings sleepy operation runs
before recording-control checks, and failed live runs must keep `operations`
plus `partial_operation_count` so partial CardStatusV1 evidence is not lost
when hardware reachability or BLE drops interrupt the run.
The panel evidence template in
`docs/validation/companion-screen-panel-evidence-template.json` defines the
controller, target pins, BUSY/reset timing, host logs, decoded
`e_paper.runtime_snapshot` health, `diagnostics_bundle_artifact` summary JSON
with `epaper.runtime_snapshot_decoded`, before/during/after visual proof, and
WB/WBA target adapter file record required before that gate can move to a real
refresh claim.
The evidence record validator,
`tools/verify_expression_panel_evidence_record.py --record`, checks the filled
record before the gate can move: CardStatusV1 identity, real BLE rendered/ok
artifact, the real BLE `screen_expression_status` six-face baseline, the
`screen_expression_demo_status` full demo host baseline, runtime snapshot
health, diagnostics bundle health, visual hashes, target-named adapter file,
and portability notes must all match.
Use `tools/init_expression_panel_evidence_record.py` to create the initial
`DRAFT_UNFILLED` record scaffold; the scaffold is a checklist, not passing
hardware evidence. On WB55 it pre-fills the SPI2 transport pins from
`companion-screen-panel-wiring-preflight.json` while leaving controller,
DC/RST/BUSY, timing, visual artifacts, real BLE, diagnostics bundle, and target
adapter evidence as TODOs.
For a concrete WB55 bench session, run
`python .\tools\init_expression_panel_evidence_record.py --target WB55 --session-root .\.cache\validation\companion-real-panel-wb55-<timestamp> --write-session`;
this creates `panel-evidence-record.json`, `panel-hardware-facts.todo.json`,
`operator-notes.md`, and the `visual/` plus `diagnostics/` folders under the
session root.
Run `python .\tools\verify_expression_panel_session_directory.py --session-root <session-root> --target WB55`
before filling hardware evidence. That `panel_session_directory_preflight`
checks the concrete directory layout, validates the hardware facts draft, keeps
the record `DRAFT_UNFILLED`, and confirms the draft still fails the final
real-panel validator until controller, DC/RST/BUSY, timing, BLE, diagnostics,
and visual proof are filled. If local `panel-bringup-operator-packet.json` or
`panel-bringup-operator-packet.md` files exist, the same preflight requires
them to match the current renderer, keep quoted
`with-lock -Resource 'Companion-WB55,BLE-Companion'`, and retain
`partial_operation_count` evidence for failed live BLE runs. The
`panel_hardware_facts_intake` verifier
(`tools/verify_expression_panel_hardware_facts.py`) accepts
`panel-hardware-facts.todo.json` as a draft, or as
`READY_FOR_DRIVER_FACTS` after controller, DC/RST/BUSY, power, voltage, and
timing fields are filled; it does not claim real refresh.
Run `python .\tools\render_expression_panel_facts_worksheet.py --session-root <session-root> --write --json <session-root>\panel-facts-worksheet.json --markdown <session-root>\panel-facts-worksheet.md`
to create the `panel_hardware_facts_worksheet`; the deterministic fixtures are
`docs/validation/companion-screen-panel-facts-worksheet.json` and
`docs/validation/companion-screen-panel-facts-worksheet.md`. The worksheet
turns the missing driver-readiness fields into a table for filling
`panel-hardware-facts.todo.json`.
Run `python .\tools\render_expression_panel_bringup_packet.py --session-root <session-root> --write --json <session-root>\panel-bringup-operator-packet.json --markdown <session-root>\panel-bringup-operator-packet.md`
to create the `panel_bringup_operator_packet`; the deterministic fixtures are
`docs/validation/companion-screen-panel-bringup-operator-packet.json` and
`docs/validation/companion-screen-panel-bringup-operator-packet.md`. The packet
collects the session commands, missing facts, `--require-ready` gate, target
driver/evidence commands, and visual artifact paths without claiming real
refresh.
Run `python .\tools\verify_expression_panel_driver_readiness.py --session-root <session-root>`
to produce the `panel_driver_readiness_report`; the deterministic fixture is
`docs/validation/companion-screen-panel-driver-readiness.json`. DRAFT facts
report `BLOCKED_ON_HARDWARE_FACTS`, while filled `READY_FOR_DRIVER_FACTS` input
reports `READY_FOR_DRIVER_IMPLEMENTATION` and names the target adapter
entrypoint to implement next. This readiness report still does not claim real
refresh. Use `--require-ready` only with `--session-root <session-root>` or
`--facts <panel-hardware-facts.todo.json>` for the final pre-driver gate.
After the facts file reaches `READY_FOR_DRIVER_FACTS`, run
`python .\tools\apply_expression_panel_hardware_facts.py --facts <facts-json> --record <session-root>\panel-evidence-record.json --write`.
The `panel_hardware_facts_bridge` imports identity, pin map, and timing into
the evidence record, keeps that record `DRAFT_UNFILLED`, and does not claim real refresh.
Use `tools/init_expression_wba_port_scaffold.py` to create the WBA port scaffold
at `docs/validation/companion-screen-wba55-port-scaffold.json`; that
`DRAFT_PRE_PORT` checklist keeps the first CubeWBA project, build wrapper,
`*_stm32wba.*` BLE/GATT adapter, scheduler hook, panel transport, real BLE
artifact, and panel evidence record visible before WBA parity is claimed.
The initial WBA panel target adapter scaffold is
`wba_panel_target_adapter_scaffold`: `panel_target_stm32wba.h/.c`.
It exposes `companion_epaper_panel_stm32wba_init()` as the dry-run default and
`companion_epaper_panel_stm32wba_bind()` for a target-owned refresh callback;
it is verified by `tools/verify_expression_panel_target_stm32wba.py`.
The fixture is `docs/validation/companion-screen-panel-target-stm32wba.json`.
It is not part of the WB55 build and must not carry WB55 SPI2 pin facts.
The WBA display scheduler scaffold is `wba_display_scheduler_scaffold`:
`screen_scheduler_stm32wba.h/.c`. It exposes
`companion_epaper_stm32wba_schedule_display_task()` and
`companion_epaper_stm32wba_schedule_expression_tick()` callback boundaries so a
future CubeWBA display task can preserve the display drain contract and
ExpressionV1 tick recovery without copying WB55 `UTIL_SEQ` or `HW_TS` logic.
The fixture is `docs/validation/companion-screen-scheduler-stm32wba.json`, and
the verifier is `tools/verify_expression_screen_scheduler_stm32wba.py`.
The WBA screen GATT scaffold is `wba_screen_gatt_scaffold`:
`screen_gatt_stm32wba.h/.c`. It exposes
`companion_epaper_stm32wba_screen_gatt_accept_card_write()` and the companion
CardStatusV1/SettingsV1 callbacks so future CubeWBA BLE glue can preserve
`settings_sleepy_screen_status` and `screen_expression_status` without copying
WB55 `companion_gatt_stm32wb` or `STM32_WPAN` details. The fixture is
`docs/validation/companion-screen-gatt-stm32wba.json`, and the verifier is
`tools/verify_expression_screen_gatt_stm32wba.py`.
The WBA screen-assets scaffold is `wba_screen_assets_scaffold`:
`screen_assets_stm32wba.h/.c`. It binds a target-owned logical external-NOR
partition reader to `comp_asset_store_t`, checks every read against the
declared `partition_size`, and keeps physical address, storage peripheral,
erase/write, and active-pack switching outside portable code. The fixture is
`docs/validation/companion-screen-assets-stm32wba.json`, and the verifier is
`tools/verify_expression_screen_assets_stm32wba.py`.
The WBA CubeWBA dependency preflight is `wba_cube_dependency_preflight`:
`tools/verify_expression_wba_cube_dependency_preflight.py` records that this
workspace currently has `third_party/STM32CubeWB` but not
`third_party/STM32CubeWBA`. Its fixture,
`docs/validation/companion-screen-wba-cube-dependency-preflight.json`, keeps
the WBA checklist at `DRAFT_PRE_PORT` until a separate CubeWBA IOC/project,
build wrapper, BLE/GATT adapter, scheduler hook, and target panel evidence
exist.
Use `tools/verify_expression_panel_hardware_session.py` before a real-panel
run. The `panel_hardware_session_scaffold` fixture at
`docs/validation/companion-screen-panel-hardware-session.json` gives WB55 the
target root `.cache/validation/companion-real-panel-wb55-<timestamp>` with
`panel-evidence-record.json`, `companion-ble-real-bench.json`,
`diagnostics/summary.json`, `visual/before_photo.jpg`,
`visual/after_photo.jpg`, and `operator-notes.md`. The same scaffold defines
WBA55/WBA65 roots and keeps `--expect-real-panel`,
`tools/collect_companion_diagnostics.ps1`, and
`python .\tools\verify_expression_panel_evidence_record.py --record` in the
hardware handoff.

Supported card inputs:

- ExpressionV1 cards for idle, listening, thinking, speaking, happy, sleepy,
  recording, sync-complete, low-battery, and error faces.
- Mood, name, event, and reminder cards from the BLE `CardWriteV1` payload.
- Local recording, sync-complete, low-battery, and error states.
- Boot/default card fixtures used by bring-up validation.

Supported display variants:

- `2.13in`: 250 by 122 monochrome pixels.
- `1.54in`: 200 by 200 monochrome pixels.

The renderer produces 1-bit PBM bitmap fixtures with deterministic Bayer
dithering for gray regions. Text rendering uses a compact built-in ASCII font;
unsupported Unicode codepoints are rendered as deterministic placeholder boxes
so multilingual payloads do not disappear.

`tools/render_expression_preview.py --write` converts the ExpressionV1 PBM
fixtures into `docs/validation/epaper/expression-preview.svg` plus a JSON hash
report for no-hardware visual acceptance.
`tools/verify_expression_firmware_state.py --write-fixture` updates the
firmware ExpressionV1 state evidence after intentional C policy changes.
`tools/verify_expression_event_bridge.py --write-fixture` updates the
diagnostic-event bridge evidence.
`tools/verify_expression_journeys.py --write-fixture` updates the user journey
evidence for consecutive expression transitions.

Hardware boundary:

- Renderer model, ExpressionV1 state mapping, text fallback, dithering,
  dimensions, and framebuffer export are AI-testable now.
- Firmware expression state changes from recording, meeting, speaker, and
  wake-word controls are AI-testable now through the display queue boundary.
- ExpressionV1 copy contract is AI-testable now:
  `verify_expression_copy_contract.py` keeps title/body/footer copy aligned
  across the renderer, firmware expression table, catalog, layout, priority,
  and generated PBM fixtures.
- Screen feature roadmap is AI-testable now:
  `verify_expression_feature_roadmap.py` records
  `docs/validation/companion-screen-feature-roadmap.json`, grouping the
  `screen_feature_roadmap` acceptance item into product-facing capabilities
  including `screen_demo_acceptance_flow`; real WB55 panel refresh is PASS and
  `wb55_touch_visual_acceptance` is the focused `PENDING_HUMAN` gate.
- Screen feature checklist is AI-testable now:
  `render_expression_feature_checklist.py` records
  `docs/validation/companion-screen-feature-checklist.json` and
  `docs/validation/companion-screen-feature-checklist.md` for the
  `screen_feature_checklist` acceptance item, giving the current one-by-one
  acceptance focus without reopening resolved panel facts.
- Screen expression demo sequence is AI-testable now:
  `verify_expression_demo_sequence.py` records
  `docs/validation/companion-screen-expression-demo-sequence.json` and
  `docs/validation/companion-screen-expression-demo-sequence.md`, giving
  wake, recording, speaker, settings, low-battery, error, and transient
  recovery flows a stable one-by-one checklist before WB55 real-panel or WBA
  evidence is claimed.
- Screen expression demo host status sequence is AI-testable now:
  `verify_expression_demo_host_status_sequence.py` records
  `docs/validation/companion-screen-expression-demo-host-status-sequence.json`,
  adding the `screen_expression_demo_status` host contract for every demo face
  and `held_steps_emit_no_host_status` for suppressed steps.
- Screen expression demo panel handoff is AI-testable now:
  `verify_expression_demo_panel_handoff.py` records
  `docs/validation/companion-screen-expression-demo-panel-handoff.json` and
  `docs/validation/companion-screen-expression-demo-panel-handoff.md`, mapping
  the demo checklist onto WB55/WBA55/WBA65 evidence sessions while keeping
  `manual_visual_required_faces` explicit until the real bench can cover every
  demo face.
- Unknown ExpressionV1 signal handling is AI-testable now:
  `comp_epaper_expression_signal_is_supported()` preserves the append-only
  signal catalog boundary and rejects unsupported signals before state changes.
- Display queue fault paths are AI-testable now: queue-full, payload-too-long,
  unsupported-expression, and expression enqueue rollback have fixed
  CardStatusV1/diagnostic behavior.
- Display queue telemetry is AI-testable now: pending, high-water, dropped,
  queue capacity, payload bound, and sequence counters stay portable in a
  stats snapshot so slow panel pressure can be diagnosed on WB55 and future WBA
  targets.
- Display drain contract behavior is AI-testable now: the display task drains
  one request per pass, publishes final CardStatusV1 from the target panel
  result, records runtime diagnostics first, and reschedules only for pending
  queue work.
- Target capability profile behavior is AI-testable now:
  `verify_expression_target_capabilities.py` keeps WB55 as the current
  validation target, WBA55 as the WBA55-safe shared baseline, and records that
  WBA65 may add target-specific resources only behind capability flags.
- Devboard IOC screen preflight is AI-testable now:
  `verify_devboard_ioc_import.py` proves the user-provided `STM32.ioc`
  hardware facts are captured in the WB55 devboard IOC while the product IOC
  remains separate for later target work.
- Panel wiring preflight is AI-testable now:
  `verify_expression_panel_wiring_preflight.py` records the imported WB55 SPI2
  transport pins while keeping controller and DC/RST/BUSY choices under the
  real-panel hardware gate.
- Panel evidence scaffold wiring prefill is AI-testable now:
  `init_expression_panel_evidence_record.py` carries the known WB55 SPI2 pins
  into the draft record while keeping real hardware facts as TODOs.
- Panel hardware session scaffold is AI-testable now:
  `verify_expression_panel_hardware_session.py` keeps real-panel artifacts in a
  target-specific session root with required visual evidence and operator notes
  while preserving `wb55_real_panel_refresh` as the hardware gate.
- Screen panel hardware facts worksheet is AI-testable now:
  `render_expression_panel_facts_worksheet.py` records
  `docs/validation/companion-screen-panel-facts-worksheet.json` and
  `docs/validation/companion-screen-panel-facts-worksheet.md` for the
  `panel_hardware_facts_worksheet` acceptance item, keeping the current panel
  facts to fill visible before driver work starts.
- Screen panel bring-up operator packet is AI-testable now:
  `render_expression_panel_bringup_packet.py` records
  `docs/validation/companion-screen-panel-bringup-operator-packet.json` and
  `docs/validation/companion-screen-panel-bringup-operator-packet.md` for the
  `panel_bringup_operator_packet` acceptance item, combining the session
  command order, missing facts, readiness gate, and evidence paths for WB55
  while requiring separate WBA55/WBA65 packets.
- WBA panel target adapter scaffold is AI-testable now:
  `verify_expression_panel_target_stm32wba.py` keeps
  `panel_target_stm32wba.h/.c` dry-run by default, callback-bindable,
  WBA55/WBA65-scoped, outside the WB55 build, and free of WB55 SPI2 pin facts.
- WBA display scheduler scaffold is AI-testable now:
  `verify_expression_screen_scheduler_stm32wba.py` keeps
  `screen_scheduler_stm32wba.h/.c` callback-only, outside the WB55 build, and
  free of WB55 `UTIL_SEQ`/`HW_TS` scheduler details.
- WBA screen GATT scaffold is AI-testable now:
  `verify_expression_screen_gatt_stm32wba.py` keeps
  `screen_gatt_stm32wba.h/.c` target-named, outside the WB55 build, and aligned
  with CardWriteV1, CardStatusV1, SettingsV1, `settings_sleepy_screen_status`,
  and `screen_expression_status` before CubeWBA service registration exists.
- WBA FT6336 touch scaffold is AI-testable now:
  `verify_touch_target_stm32wba_ft6336.py` keeps
  `touch_target_stm32wba_ft6336.h/.c` callback-only, 7-bit-addressed,
  WBA55/WBA65-scoped, outside the WB55 build, and reusing the portable FT6336
  report decoder. Real WBA corner and gesture evidence is still required.
- WBA CubeWBA dependency preflight is AI-testable now:
  `verify_expression_wba_cube_dependency_preflight.py` records the current
  missing `third_party/STM32CubeWBA` upstream reference and keeps WBA parity
  blocked behind `DRAFT_PRE_PORT` until the separate CubeWBA project and build
  wrapper exist.
- Expression state telemetry is AI-testable now: current face, last signal,
  visible age, auto-recovery dwell, and suppressed duplicate count stay
  portable in a stats snapshot for WB55 and future WBA scheduler hooks.
- Duplicate ExpressionV1 refresh suppression is AI-testable now through the
  firmware state fixture and user journey fixture.
- Transient ExpressionV1 auto recovery is AI-testable now through the portable
  state tick API and journey fixture.
- WB55 transient expression scheduling is AI-testable now: `HW_TS` wakes the
  display task, while recovery still goes through the same queue/CardStatus
  path as other screen updates.
- WB55 boot idle face enqueue is AI-testable now through the same queue
  boundary.
- WB55 DeviceStatusV1 expression hints are AI-testable now: post-startup
  device status reads/notifies feed the portable device-status mapper while
  initial GATT state publication stays scheduler-safe.
- WB55 interaction status expression hints are AI-testable now:
  MeetingStatusV1, SpeakerStatusV1, and WakeWordStatusV1 reads/notifies feed
  portable status mappers while initial GATT state publication stays
  scheduler-safe.
- CardStatusV1 observability is AI-testable now: accepted requests and dry-run
  no-panel failures preserve request identity and are paired with diagnostic
  events.
- Host BLE ExpressionV1 status fixtures are AI-testable now: boot idle,
  settings sleepy, and recording expression requests keep request identity,
  content CRCs, and diagnostic expression/signal decoding aligned.
- ExpressionV1 host manifest is AI-testable now:
  `render_expression_host_manifest.py` records
  `docs/validation/companion-screen-expression-host-manifest.json` and
  `docs/validation/companion-screen-expression-host-manifest.md` for the
  `expression_host_manifest` acceptance item, showing all 10 faces, all 18
  signals, host observability, and the legacy `screen_expression_status` gap
  versus full `screen_expression_demo_status` coverage.
- Expression visual acceptance matrix is AI-testable now:
  `render_expression_visual_acceptance_matrix.py` records
  `docs/validation/companion-screen-expression-visual-acceptance-matrix.json`
  and
  `docs/validation/companion-screen-expression-visual-acceptance-matrix.md`
  for the `expression_visual_acceptance_matrix` acceptance item, showing all
  10 faces, both display variants, PBM hash/density acceptance, source signals,
  and host coverage without claiming real panel refresh.
- Screen settings expression policy is AI-testable now: quiet hours and
  display-off settings map to sleepy without hiding higher-priority states.
- Expression priority matrix behavior is AI-testable now: every current
  face/signal pair has a recorded apply, suppress, or block outcome before WBA
  scheduler glue is added.
- Expression input source coverage is AI-testable now: every boot, diagnostic,
  settings, status, recording, battery, and OTA input source has a focused
  fixture and a WBA adapter checklist entry.
- WB55 SettingsV1 expression hints are AI-testable now: the GATT write path
  enqueues the settings sleepy signal through the same queue while preserving
  recording, low-battery, and error priority.
- WB55 BatteryChargeV1 expression hints are AI-testable now: post-startup
  battery publishes feed the portable low-battery event bridge while initial
  GATT state publication stays scheduler-safe. Battery recovery is
  AI-testable too: recovered samples clear only a visible low-battery face and
  use hysteresis around the low-battery threshold.
- WB55 OtaReadinessV1 expression hints are AI-testable now: post-startup OTA
  readiness reads/notifies feed the portable OTA blocker mapper while initial
  GATT state publication stays scheduler-safe.
- Diagnostic-event to expression mapping is AI-testable now, including the
  no-self-loop rule for `e_paper.*` events.
- User journeys are AI-testable now, including recording priority over
  low-battery warnings, battery recovery only clearing low-battery, error
  priority over lower-priority faces, and recovery back to idle.
- Real e-paper SPI timing, busy-pin handling, partial refresh behavior, and
  refresh waveform validation are deferred to the panel hardware gate, panel
  adapter boundary, panel adapter behavior matrix, real BLE screen bench, and
  panel evidence template.
- Panel adapter telemetry is AI-testable now: attempts, rendered/deferred/error
  counts, configuration state, and last result stay portable in a stats
  snapshot for WB55 and future WBA target drivers.
- WB55 panel target adapter is AI-testable now:
  `panel_target_stm32wb.h/.c` keeps initialization target-named and selects the
  real `panel_target_stm32wb_ssd1681.c` backend for the production bring-up build.
- Screen runtime snapshot is AI-testable now: expression state, display queue,
  and panel adapter stats are collected through one portable aggregate API for
  WB55 and future WBA display tasks.
- Screen runtime diagnostics are AI-testable now:
  `e_paper.runtime_snapshot` carries the aggregate runtime stats for WB55 and
  future WBA bring-up without changing CardStatusV1.
- Screen runtime diagnostic decode is AI-testable now: host tools expose
  `decoded_args` for `e_paper.runtime_snapshot` while preserving raw args for
  older log consumers.
- Screen runtime diagnostics bundle coverage is AI-testable now: the bounded
  no-hardware diagnostics fixture carries the decoded runtime snapshot summary
  that WB55 and future WBA bring-up can inspect.
- BLE callbacks should map `CardWriteV1` and product expression signals into
  this model and enqueue display work; they should not block on panel IO.
- WB55 and future WBA55/WBA65 ports should keep this model HAL-free; platform
  code owns SPI, GPIO, refresh timing, and power-state transitions.
- Generated-image art direction is carried through
  `genref_sheet_12_inner_faces_v5`: `card_renderer.py` tunes normal PBM
  expression art, `pet_visual_style.h` tunes compact rescue/maintenance
  anchors, and `MENU_STYLE` tunes generated menu assets. Large or
  slow-changing visual assets stay in external CEMP packs; internal Flash
  keeps compact render code and rescue UI only.
