# STM32WBA Migration Development Rules

The screen subsystem work breakdown and acceptance order live in
`docs/companion_screen_project_plan.md`. WBA55/WBA65 must replace only the
panel, touch, storage, and time backends; menu, emote player, timeline, and
framebuffer behavior stay portable.

This project may move from the validated WB55 development board to STM32WBA55
or STM32WBA65. During WB55 development, every change must keep that port in
mind.

## Target Assumptions

- Treat `STM32WBA55` as the constrained WBA baseline and `STM32WBA65` as the
  higher-resource WBA option.
- Do not assume a WBA65 peripheral, package pin, USB feature, RAM budget, or
  flash budget is also present on WBA55.
- The screen target capability profile is
  `docs/validation/companion-screen-target-capabilities.json`, verified by
  `tools/verify_expression_target_capabilities.py`. It keeps the common screen
  contract WBA55-safe; WBA65 may add target-specific resources only behind
  capability flags.
- Treat `WB55 -> WBA` as a platform port, not a CubeMX retarget. WB55 uses the
  CPU2/FUS/IPCC/HSEM/STM32_WPAN split; WBA uses the STM32WBA Cortex-M33
  platform and must start from STM32CubeWBA/CubeMX examples.
- The WBA CubeWBA dependency preflight is
  `wba_cube_dependency_preflight`, verified by
  `tools/verify_expression_wba_cube_dependency_preflight.py` and recorded in
  `docs/validation/companion-screen-wba-cube-dependency-preflight.json`.
  Today this workspace has `third_party/STM32CubeWB` but not
  `third_party/STM32CubeWBA`, so the WBA port scaffold must stay
  `DRAFT_PRE_PORT` until a separate CubeWBA IOC/project and WBA build wrapper
  exist.
- The WBA real parity gate is
  `docs/validation/companion-screen-wba-real-parity-gate.json`, verified by
  `tools/verify_expression_wba_real_parity_gate.py`. It must continue to report
  `parity_claim_allowed=false` while the workspace only has scaffold adapters,
  no CubeWBA project/build wrapper, no `--expect-real-panel` WBA BLE artifact,
  no filled WBA panel evidence record, and no real WBA FT6336 evidence.
  Promotion evidence must be target-named: each WBA artifact declares
  `target_family=STM32WBA` and exact target `WBA55` or `WBA65`, and lives under
  WBA55/WBA65-named build, BLE, panel, touch, or visual evidence paths. WB55
  runtime logs, WB55 build logs, NUCLEO-WB55RG wiring, WB55 photos, and
  `panel_target_stm32wb` evidence are baseline history only; they must never
  satisfy a WBA promotion requirement.

## Layer Rules

1. Portable Companion logic stays under `app/companion_pendant/` and must not
   include STM32 HAL, STM32_WPAN, board headers, or CubeIDE-generated headers.
   This includes recording FSM, BLE payload parsers, audio packet framing,
   diagnostic events, cache metadata, and host protocol constants.

2. Platform adapters must name their target family. Use names like
   `*_stm32wb.*` for WB55-specific code and later `*_stm32wba.*` for WBA code.
   Do not hide target-specific code behind generic filenames unless the file is
   genuinely portable.

3. WB55-only mechanics stay out of portable modules:
   `CPU2`, `FUS`, `IPCC`, `HSEM`, `STM32_WPAN`, WB wireless-stack binaries,
   `BLE_p2pServer`, and WB55 linker/OTA magic belong in WB platform code,
   tools, or docs only.

4. GATT contracts are source-of-truth data, not platform code. Keep UUIDs,
   payload structs, parser behavior, recording-list/chunk semantics, OTA
   readiness fields, and Type compatibility behavior stable across WB and WBA.
   Platform adapters only translate that contract to the local BLE stack.

5. Board pins and peripheral instances must be isolated to `.ioc`,
   CubeIDE-generated init, or an explicit board/platform file. No portable
   module may hard-code `GPIOx`, `GPIO_PIN_x`, `SAI1_Block_*`, QSPI, UART,
   I2C, DMA channel, or IRQ names.
   The current WB55 devboard pin/peripheral import from
   `C:\Users\Billy\Desktop\STM32.ioc` is verified by
   `tools/verify_devboard_ioc_import.py` and recorded in
   `docs/validation/companion-devboard-ioc-import.json`; future WBA work must
   create a separate CubeWBA IOC/project rather than copying those WB55
   devboard facts into portable screen files.
   The screen panel wiring preflight is
   `docs/validation/companion-screen-panel-wiring-preflight.json`, verified by
   `tools/verify_expression_panel_wiring_preflight.py`. WB55 SPI2 pins are
   devboard facts; a WBA port must use its own CubeWBA IOC/project and keep
   DC/RST/BUSY/controller choices in target evidence.

6. Any new feature touching BLE, audio, flash, OTA, low power, or security must
   state its WBA impact in the same change. At minimum record:
   portable logic, WB55-only code, expected WBA adapter work, and validation
   still needed on WBA55/WBA65.

7. External flash and OTA layouts must be selected by board target. Do not bake
   one WB55 flash size, wireless-stack reservation, or boot slot address into a
   portable module or host manifest rule. Normal expression animation packs,
   full fonts, prompts, and models default to external flash through
   `comp_asset_store_t`; internal flash keeps only a <=16 KiB rescue UI. See
   `docs/companion_resource_memory_policy.md`.

8. Prefer WBA55-safe budgets until real WBA hardware is chosen. Keep ATT/GATT
   value sizes, SRAM queues, recording buffers, and diagnostics bounded by the
   smaller target unless a capability flag explicitly enables WBA65 expansion.
   Extra WBA65 internal flash is firmware/upgrade headroom, not permission to
   compile normal UI packs into the application image.

9. `pet_behavior.h/.c` and `pet_expression.h/.c` are portable behavior and
   face-composer layers, not a panel driver or a resource store. A WBA adapter
   must pass the same logical behavior state and pose into the existing one-bit
   framebuffer renderer, then send that framebuffer to the WBA panel target.
   It may change profile dimensions and target refresh policy, but it must not
   fork valence/arousal/engagement, touch focus, directional-stroke behavior,
   gaze, eyelid, eye-width,
   eye spacing, paired-eye tilt, highlight, full-face shift, brow, mouth scale, cheek, or mark behavior, nor add full-screen expression
   arrays to internal Flash. CEMP remains the external Flash home for
   replaceable timelines, menu art, fonts, and other product resources.

9a. Daily-to-menu intent belongs to portable `screen_menu` policy. WBA must
    preserve the current any-position near-still 3 s long-press menu entry,
    including the 650 ms pet tease and the rule that ordinary tap/swipe gestures
    remain pet interactions. A target adapter may normalize raw touch
    coordinates, but must not revive the old edge-swipe menu entry or invent a
    second entry rule.

10. Default the WBA55/WBA65 production board to an assembled 32.768 kHz LSE
   crystal and target-specific load capacitors. Companion needs an accurate,
   low-power source for BLE sleep timing, RTC, and timed wake-up; omitting LSE
   is a cost-down variant that requires explicit radio-clock, accuracy, and
   power evidence, not the default design. Select the crystal and capacitors
   from the chosen WBA package datasheet and AN2867/AN5948, place them next to
   `OSC32_IN`/`OSC32_OUT`, keep the traces short and symmetric, and do not copy
   WB55 drive strength or capacitor values without a WBA oscillator check.
   The CubeWBA target must enable LSE and prove startup, RTC continuity, BLE
   advertising/connection through sleep, and timed wake-up on real hardware.

10. Audio backends must normalize to the portable Companion recording contract:
   mono PCM16 at 16 kHz before BLE streaming, flash recording metadata, ASR, or
   meeting-minute tooling sees the data. The current WB55 devboard path is a
   Listener-style SPH0655-compatible PDM source captured through a WB55 raw-SAI
   DMA adapter, then decoded with a CIC3 software filter. Its MCKDIV, SAI pin
   alternate functions, DMA channel, bit order, gain, staging buffer size, and
   timing diagnostics are WB55 bring-up facts only. A WBA55/WBA65 port must add
   a separate CubeWBA microphone adapter, preferably using the WBA HAL
   SAI/PDM, MDF/ADF, PDM2PCM, or DMA path that matches the chosen package and
   board. Portable recording FSM, Companion Type postprocess tools, cache
   metadata, and GATT payloads must not depend on the board-specific microphone
   clock, slot, GPIO pull, edge-strobe choice, DMA channel, or filter
   implementation.
   The accepted WB55 PC-speaker/TTS proof is summarized by
   `docs/validation/companion-mic-wb55-pdm-baseline.json` and verified with
   `python .\tools\verify_companion_mic_wb55_pdm_baseline.py`; WBA evidence
   should keep the same PCM16/16 kHz host contract while replacing the target
   microphone adapter. The PDM CPU/overrun margin gate is
   `docs/validation/companion-mic-wb55-pdm-margin.json`, verified with
   `python .\tools\verify_companion_mic_wb55_pdm_margin.py`; a WBA port should
   use the same zero-`dma_rx_overruns`, 10 ms frame-period, no-missing-packets,
   matching-SHA, and `小伴` transcript exit criteria with WBA-native
   instrumentation. WB55's current O2/CIC3 software-decoder tuning is only a
   local raw-SAI implementation detail; WBA may use a different HAL/MDF/ADF/
   PDM2PCM path as long as it satisfies the same portable contract.

11. Do not edit `third_party/STM32CubeWB/**` or future `third_party/STM32CubeWBA/**`.
   Add local wrappers, board adapters, scripts, or documented CubeMX output
   instead.

12. Validation must stay scriptable. WB55 changes should keep
    `tools/build_nucleo_bringup.ps1` working. The first WBA branch must add a
    separate CubeWBA build wrapper and static checks before claiming parity.

13. A slow e-paper flush must never starve input sampling. The WB55 SSD1681
    target services FT6336 every 10 ms while waiting on BUSY and replays a
    bounded timestamped sample queue after the flush. A WBA55/WBA65 target may
    replace this source with EXTI, a timer, DMA, or an RTOS task, but must keep
    the same portable sample/gesture boundary, preserve ordering and timestamps,
    retain a polling fallback, and prove that taps beginning and ending entirely
    inside a display refresh are delivered exactly once.

14. OTA has a portable transfer/package boundary and a target install boundary.
    `third_party/denzic-platform` supplies `denzic_ota_v1` to WB55, WBA55,
    WBA65, and supported ESP products as a reliable opaque byte stream. The
    Companion bundle keeps `mcu_app`, `ui_assets`, prompt packs, and model packs
    as separate signed components with SHA-256, target, version, compatibility,
    and anti-rollback metadata. CRC32 in Denzic v1 is only a resume identity.
    WB55 may use its resident copier and QSPI staging; WBA must start from the
    matching STM32CubeWBA Application Install Manager and production security
    reference selected for the exact part, then expose it through a
    `*_stm32wba.*` installer/storage adapter. Do not copy the WB55 CPU2/FUS
    layout or ESP partition/rollback APIs. External `ui_assets` must install to
    an inactive slot or staging area and switch atomically; firmware-only OTA
    preserves active resources, and every OTA preserves recording cache and
    user settings. See `docs/companion_ota_component_contract.md`.

## Current Screen Adapter Split

Portable today:

- `app/companion_pendant/epaper/card_renderer.py` and PBM fixtures define the
  no-hardware visual contract.
- `asset_store.*`, `emote_asset_pack.*`, and `expression_asset_source.*`
  form the portable runtime asset path. `tools/build_emote_asset_pack.py`
  converts profile-specific PBM sources into a CRC-protected CEMP pack.
  The old `expression_assets_200x200.c` output costs 50,000 internal-Flash
  bytes and is no longer linked by the WB55 normal build; WBA55/WBA65 must not
  reintroduce it. Each WBA target supplies only its storage adapter and
  partition layout, then mounts the same logical pack contract.
- `app/companion_pendant/epaper/expression_policy.py` maps host/status inputs
  into ExpressionV1 cards, including quiet hours and display-off settings as
  low-priority sleepy hints.
- `app/companion_pendant/epaper/expression_state.h/.c` owns firmware
  ExpressionV1 names, priorities, user-visible copy, state transitions, and
  duplicate visible-expression suppression. It also keeps the settings sleepy
  guard portable: SettingsV1 screen hints may lower idle to sleepy, but must
  not hide active higher-priority product expressions.
- `app/companion_pendant/epaper/pet_behavior.h/.c` owns a bounded,
  target-free companion state: valence, arousal, curiosity, affection,
  engagement, the latest logical touch focus, and transient directional-stroke
  behavior. It changes only on product events and intentional touch; it does
  not create an idle refresh loop.
  `pet_expression.h/.c` maps that state into eye width, reflection scale,
  eye spacing, paired-eye tilt, full-face shift, brows, gaze, lids, mouth scale, cheeks, and marks in the existing framebuffer. WBA must
  reuse both modules unchanged.
- Expression state telemetry is portable:
  `comp_epaper_expression_state_snapshot()` reports current face, last signal,
  revision, visible age, auto-recovery dwell, and suppressed duplicate count
  without target dependencies. WBA scheduler hooks should use that stats
  snapshot instead of reading private state fields directly.
- The ExpressionV1 catalog lives at
  `docs/validation/companion-screen-expression-catalog.json` and is verified by
  `tools/verify_expression_catalog_contract.py`. It locks stable numeric IDs
  for ExpressionV1 faces and signals, the expression card slot, request ID
  base, and the `(expression_id << 16) | signal_id` diagnostic payload model.
  WBA adapters must preserve those IDs and append new faces/signals instead of
  renumbering existing values.
- The ExpressionV1 copy contract lives at
  `docs/validation/companion-screen-expression-copy-contract.json` and is
  verified by `tools/verify_expression_copy_contract.py`. It keeps
  title/body/footer copy aligned across the renderer, firmware expression
  table, catalog, layout, priority, and generated PBM fixtures. WBA adapters
  reuse the same copy and must not fork user-visible text in target glue.
- The ExpressionV1 host manifest lives at
  `docs/validation/companion-screen-expression-host-manifest.json` with
  Markdown at `docs/validation/companion-screen-expression-host-manifest.md` and
  is rendered by `tools/render_expression_host_manifest.py`; its acceptance id
  is `expression_host_manifest`. WBA host/status adapters must preserve the
  same face IDs, signal IDs, CardStatusV1 meanings, and
  `(expression_id << 16) | signal_id` diagnostic model while replacing only
  platform transport.
- The Expression priority matrix lives at
  `docs/validation/companion-screen-expression-priority-matrix.json` and is
  verified by `tools/verify_expression_priority_matrix.py`. WBA scheduler and
  status adapters must preserve higher-priority applies, duplicate suppression,
  blocked lower-priority signals, settings sleepy lowering only idle, battery
  recovered clearing only a visible low-battery face, and transient/stable
  auto-recovery behavior.
- The Expression input source matrix lives at
  `docs/validation/companion-screen-expression-input-source-matrix.json` and is
  verified by `tools/verify_expression_input_source_matrix.py`. It is the WBA
  adapter checklist for boot/default idle, diagnostic events, SettingsV1,
  DeviceStatusV1, BatteryChargeV1, Recording FSM state, MeetingStatusV1,
  SpeakerStatusV1, WakeWordStatusV1, and OtaReadinessV1 expression inputs.
  A WBA port should not claim screen parity until every listed source is wired
  through the same portable mapper or direct ExpressionV1 signal path.
- Unknown ExpressionV1 signals must stay guarded by the portable preflight API:
  `comp_epaper_expression_signal_is_supported()`. WBA adapters should reject
  unsupported or future signals before visible state, duplicate counters,
  display queue work, or CardStatusV1 request identity changes. This keeps the
  append-only signal catalog explicit when WBA work adds new product events.
- `app/companion_pendant/epaper/expression_events.h/.c` maps Companion
  diagnostic events into ExpressionV1 signals and ignores `e_paper.*` events to
  avoid display self-trigger loops.
- `app/companion_pendant/power/power_policy.h/.c` owns the portable Stop
  eligibility blockers. `power_target_stm32wba.h/.c` is the WBA55/WBA65
  callback-only scaffold: a future CubeWBA board target must configure the
  actual FT6336 interrupt wake source and map allow/deny transitions to the
  CubeWBA LPM/radio policy. It must not import WB55 IPCC/P2P macros or treat an
  I2C configuration readback as proof that the interrupt trace is physically
  wired. A WBA board continuing to use FT6336 must reserve exactly one shared
  `WAKE_N`/EXTI GPIO for `TP_INT`; `TP_RST` may be an external RC/supervisor
  reset rather than an MCU GPIO. I2C address-match wake is not a substitute:
  WBA is the I2C master and FT6336 is also a slave. If `WAKE_N` is shared with
  other interrupts, electrical open-drain/diode/logic compatibility must be
  proven and firmware must query each source after wake. See
  `docs/companion_low_power_requirements.md`.
- `app/companion_pendant/epaper/display_queue.h/.c` owns bounded card and
  expression display requests.
- Display generation hygiene is portable and inherited by WBA. Every WBA
  display task must use the same active CEMP revision carried by
  `display_queue.h/.c`; after a resource switch, stale queued requests from the
  old revision are drained or discarded before new product frames are accepted.
  WBA panel, scheduler, GATT, and storage adapters must not bypass
  `comp_epaper_display_queue_set_resource_revision()`,
  `resource_revision`, `active_resource_revision`,
  `generation_switch_count`, `stale_generation_discard_count`, or
  `last_stale_generation_discarded`. The first visible frame after a WBA
  `ui_assets` activation must be a coherent current-generation frame, and the
  WBA bring-up log must carry the same `coherent_generation=1`,
  `generation_switches`, and `last_stale_discarded` semantics as WB55.
- Display queue telemetry is portable: pending count, high-water count,
  dropped count, and in-memory sequence stay in `display_queue.h/.c` and are
  verified by `tools/verify_display_queue_telemetry.py`. A WBA scheduler should
  preserve the `comp_epaper_display_queue_snapshot()` stats snapshot and
  `comp_epaper_display_queue_high_water_count()` so slow real-panel pressure
  can be diagnosed without changing CardStatusV1.
- Display queue fault paths are portable behavior: `queue_full`,
  `payload_too_long`, `bad_argument`, and `unsupported_expression` must keep
  stable CardStatusV1 error meanings, and expression enqueue failures must roll
  back the visible expression state.
- The display drain contract is WBA-facing scheduler evidence:
  `docs/validation/companion-screen-display-drain-contract.json` and
  `tools/verify_expression_display_drain.py` guard the display task lifecycle.
  A WBA display task should process one queued request per pass, refresh only
  through the target panel callback, record runtime diagnostics before final
  CardStatusV1, and ensure pending work reschedules the display task.
- `app/companion_pendant/epaper/panel_adapter.h/.c` is a platform-neutral
  dispatcher. WB55 now has a proven real SSD1681 backend; dry-run remains a
  no-hardware/unsupported-target mode, not the production WB55 state.
- The panel adapter boundary exposes `comp_epaper_panel_refresh_fn_t` as the
  target-owned refresh callback. Portable screen files own dispatch and status
  mapping only; WB55/WBA transport code must live behind target-specific
  adapter files.
- Full/partial/fast selection and the residual-image guard live in the HAL-free
  `refresh_policy.h/.c`. A target establishes a valid baseline before the first
  partial refresh. Five interactive partials are allowed; the sixth request
  selects one target fast-maintenance waveform and resets the baseline count.
  Ordinary touch paths must not add a delayed maintenance refresh of their own.
  Standard full refresh is reserved for an unknown baseline or controlled fault
  recovery. WBA targets reuse the policy but implement their own controller RAM,
  waveform, and update-control sequence.
- The panel adapter behavior matrix fixes callback result semantics before
  hardware arrives: OK maps to rendered/ok, BUSY maps to busy, failures keep
  stable CardStatusV1 last-error values, and request identity remains owned by
  the portable dispatcher.
- The current WB55 target adapter entry point is `panel_target_stm32wb.h/.c`.
  Dry-run remains the fallback, while the production
  `COMPANION_EPAPER_PANEL_SSD1681_BRINGUP` build path selects
  `panel_target_stm32wb_ssd1681.c`. That bring-up driver consumes the portable
  200x200 expression assets for ExpressionV1 requests and keeps SPI/GPIO,
  reset, BUSY, and refresh timing in the WB55-specific file. Its firmware and
  runtime statuses are validated; physical wiring, black update, upright
  orientation, full/partial/fast refresh, and touch contact/release have real
  WB55 evidence. Focused gesture and single-flash perception remain human
  acceptance. WBA55/WBA65 must add a separate `*_stm32wba.*`
  target adapter instead of changing portable panel files. The WB55 SSD1681
  implementation uses Good Display's baseline writes to commands `0x24` and
  `0x26`, full update control `0xF7`, and partial update control `0xFF`; these
  command bytes are SSD1681 facts and must not leak into a WBA adapter for a
  different controller.
- The connected WB55 `ESP32-FTS02/GDEY0154D67` panel uses active-high `BUSY`:
  high means the controller is working and low means ready. Any WBA target driver
  must record the selected panel's documented and observed BUSY polarity in its
  target evidence and implement it through a named ready-level constant. It must
  not assume the WB55 polarity for a different controller.
- A target driver using `BUSY` must observe the expected active-to-ready cycle
  after a physical refresh command before reporting `rendered/ok`. A permanently
  ready line can indicate an unplugged display FPC, wrong control wiring, or a
  controller that did not decode the command; it is not visual-refresh evidence.
- The initial WBA panel target adapter scaffold is
  `panel_target_stm32wba.h/.c`. It exposes
  `companion_epaper_panel_stm32wba_init()` as a dry-run default and
  `companion_epaper_panel_stm32wba_bind()` for a target-owned refresh callback.
  It is verified by `tools/verify_expression_panel_target_stm32wba.py`. This
  `wba_panel_target_adapter_scaffold` is callback-bindable, is not compiled
  into the WB55 build, and must not carry WB55 SPI2 pin facts such as PA9,
  PC1, PC2, PA6, or `SPI2_CS`. A successful bind is an adapter-readiness check,
  not WBA visual evidence. The fixture is
  `docs/validation/companion-screen-panel-target-stm32wba.json`.
- The panel bring-up operator packet is
  `docs/validation/companion-screen-panel-bringup-operator-packet.json` with
  Markdown at `docs/validation/companion-screen-panel-bringup-operator-packet.md`
  and is rendered by `tools/render_expression_panel_bringup_packet.py`; its
  acceptance id is `panel_bringup_operator_packet`. WBA55/WBA65 must generate
  separate packets from target-specific facts and must not reuse WB55 SPI2,
  DC/RST/BUSY, power, voltage, or timing evidence.
- The initial WBA display scheduler scaffold is
  `screen_scheduler_stm32wba.h/.c`. It exposes
  `companion_epaper_stm32wba_schedule_display_task()` and
  `companion_epaper_stm32wba_schedule_expression_tick()` callback boundaries
  for WBA55/WBA65 and is verified by
  `tools/verify_expression_screen_scheduler_stm32wba.py`. This
  `wba_display_scheduler_scaffold` is not compiled into the WB55 build, must
  preserve the display drain contract, and must not copy WB55 `UTIL_SEQ`,
  `HW_TS`, `CFG_TASK_COMPANION_DISPLAY_ID`, CPU2, FUS, IPCC, or HSEM details.
  The fixture is `docs/validation/companion-screen-scheduler-stm32wba.json`.
- The initial WBA screen GATT scaffold is `screen_gatt_stm32wba.h/.c`. It
  exposes `companion_epaper_stm32wba_screen_gatt_accept_card_write()` plus
  CardStatusV1 and SettingsV1 callback boundaries for WBA55/WBA65 and is
  verified by `tools/verify_expression_screen_gatt_stm32wba.py`. This
  `wba_screen_gatt_scaffold` is not compiled into the WB55 build, must preserve
  `settings_sleepy_screen_status`, settings-clear recovery, and
  `screen_expression_status`, and must not
  copy WB55 `companion_gatt_stm32wb`, `STM32_WPAN`, `aci_gatt`, `SVCCTL`,
  `GATT_NOTIFY_ATTRIBUTE_WRITE`, `UTIL_SEQ`, CPU2, FUS, IPCC, or HSEM details.
  The fixture is `docs/validation/companion-screen-gatt-stm32wba.json`.
- Panel adapter telemetry is portable: `comp_epaper_panel_adapter_snapshot()`
  reports hardware/configuration state, attempts, rendered/deferred/error
  counts, and last result without target dependencies. WBA panel drivers should
  update those counters through the dispatcher instead of introducing
  target-specific telemetry.
- The screen runtime snapshot is portable:
  `comp_epaper_screen_runtime_snapshot()` aggregates expression state, display
  queue, and panel adapter stats snapshots without target dependencies. WBA
  display tasks should collect runtime status through this aggregate instead of
  reading private expression, queue, or panel fields directly. The fixture is
  `docs/validation/companion-screen-runtime-snapshot.json` and the verifier is
  `tools/verify_expression_screen_runtime_snapshot.py`.
- Screen runtime diagnostics are host-facing bring-up evidence. The runtime
  snapshot diagnostic
  `e_paper.runtime_snapshot` packs aggregate screen runtime stats without
  changing CardStatusV1. Its payload is fixed as
  `(expression.current << 16) | expression.last_signal`,
  `(display_queue.pending_count << 16) | display_queue.high_water_count`,
  `display_queue.dropped_count`, and
  `(panel.deferred_count << 16) | panel.error_count`. The fixture is
  `docs/validation/companion-screen-runtime-diagnostics.json` and the verifier
  is `tools/verify_expression_screen_runtime_diagnostics.py`.
- Runtime diagnostic decode is portable host tooling:
  `tools/decode_diag_log.py` expands `e_paper.runtime_snapshot` into
  `decoded_args` for expression, display queue, and panel fields. The fixture is
  `docs/validation/companion-screen-runtime-diagnostic-decode.json` and the
  verifier is `tools/verify_expression_screen_runtime_diagnostic_decode.py`.
- The diagnostics bundle fixture must include the runtime snapshot too:
  `tools/collect_companion_diagnostics.ps1 -Fixture` keeps
  `e_paper.runtime_snapshot` in a bounded tail and exposes
  `epaper.runtime_snapshot_decoded` in summary JSON. The verifier is
  `tools/verify_companion_diagnostics_static.py`.
- `CardStatusV1` render-state and last-error values are host-facing contract,
  not WB55 implementation details. A WBA adapter should preserve the same
  accepted/rendered/failed/busy and `deferred_no_panel` meanings.
- The no-hardware BLE `screen_expression_status` fixture is host-facing
  evidence. WBA real BLE validation should keep the same accepted/final
  CardStatusV1 pairing and expression diagnostic payload shape. The fixture
  covers idle, sleepy, recording, low-battery, sync-complete, and error faces
  so a WBA bench can compare extended ExpressionV1 status coverage without a
  real panel. The accepted/final CardStatusV1 pairs must keep contiguous
  `refresh_count` values, stable `request_id`/`content_crc32`, and diagnostic
  arg3 decoding as `(expression_id << 16) | signal_id`.
  This is tracked by the Host BLE ExpressionV1 status sequence integrity gate,
  `docs/validation/companion-screen-expression-host-status-sequence.json`, and
  `tools/verify_expression_host_status_sequence.py`.
- The demo host status sequence extends that host-facing evidence to every
  demo face. WBA adapters should preserve
  `screen_expression_demo_host_status_sequence`,
  `screen_expression_demo_status`,
  `docs/validation/companion-screen-expression-demo-host-status-sequence.json`,
  and `tools/verify_expression_demo_host_status_sequence.py`. The fixture also
  keeps `held_steps_emit_no_host_status` explicit so lower-priority or duplicate
  demo steps do not become WBA-only refresh noise.
- The Expression visual contract is WBA-facing renderer evidence:
  `docs/validation/companion-screen-expression-visual-contract.json` and
  `tools/verify_expression_visual_contract.py` guard every ExpressionV1 PBM
  against blank, overfilled, or visually duplicate faces. WBA ports should keep
  this visual contract passing while changing only target transport.
- The Expression visual acceptance matrix is the per-face WBA handoff:
  `docs/validation/companion-screen-expression-visual-acceptance-matrix.json`,
  `docs/validation/companion-screen-expression-visual-acceptance-matrix.md`,
  and `tools/render_expression_visual_acceptance_matrix.py` guard
  `expression_visual_acceptance_matrix`. WBA ports should keep every PBM hash,
  density result, copy field, source signal, policy case, and host coverage row
  stable before replacing only panel transport. The matrix keeps
  `real_refresh_claimed=false`; real WBA panel evidence still needs the
  hardware gate.
- The Expression layout contract is also WBA-facing renderer evidence:
  `docs/validation/companion-screen-expression-layout-contract.json` and
  `tools/verify_expression_layout_contract.py` guard title/body/footer copy
  against truncation or body/footer overlap on the supported renderer variants.
  WBA ports should keep this layout contract passing when copy or panel size
  assumptions change.
- The real BLE screen bench contract requires `tools/companion_ble_real_bench.py`
  to collect accepted and final CardStatusV1 records. It must preserve both
  `card_write` and `settings_sleepy_screen_status`; the latter proves the
  SettingsV1 display-off path still reaches the portable ExpressionV1 queue.
  The same artifact must carry the contract-only `screen_expression_status`
  operation linked to
  `docs/validation/companion-screen-expression-host-status-sequence.json`, so
  WB55 and WBA benches compare the same six-face host baseline before panel
  parity is claimed. It must also carry the contract-only
  `screen_expression_demo_status` operation linked to
  `docs/validation/companion-screen-expression-demo-host-status-sequence.json`
  so the full demo face baseline and held-step suppression contract travel with
  the real-panel artifact. Failed live artifacts must preserve `operations`
  and `partial_operation_count`, and `settings_sleepy_screen_status` must run
  before recording-control checks so WBA bench failures can distinguish BLE or
  board reachability loss from a screen contract regression.
  The hardware gate uses `--expect-real-panel`,
  `final_card_status=rendered/ok`, and `real_panel_refresh_claimed=true` as the
  BLE side of real refresh evidence.
- The screen expression demo panel handoff is the WBA-facing bridge from the
  no-hardware demo order to real-panel evidence:
  `docs/validation/companion-screen-expression-demo-panel-handoff.json`,
  `docs/validation/companion-screen-expression-demo-panel-handoff.md`, and
  `tools/verify_expression_demo_panel_handoff.py`. WBA55 and WBA65 must reuse
  the same `screen_expression_demo_panel_handoff` order and keep
  `manual_visual_required_faces` explicit until the real BLE
  `screen_expression_status` bench covers every demo face.
- Quiet hours and display-off screen settings are host-facing policy. WBA should
  preserve the same low-priority sleepy behavior and keep recording,
  low-battery, and error faces visible.
- SettingsV1 screen hints use the same portable
  `COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY` signal in firmware. A WBA
  adapter should keep the same signal and the same stable-state guard instead
  of adding a WBA-only sleepy rule.
- DeviceStatusV1 status is also an expression input. The portable
  device-status mapper treats `fault_bitmap != 0` as an error expression,
  active audio mode as recording, and disconnected mode as the low-priority
  sleepy signal. A WBA device-status adapter should call the same mapper after
  its display scheduler exists and keep initial service publication
  scheduler-safe.
- MeetingStatusV1, SpeakerStatusV1, and WakeWordStatusV1 status are also
  expression inputs. The portable interaction-status mapper family mirrors the
  control diagnostic semantics for recording/thinking/sync-complete/speaking,
  listening/idle, and error faces. A WBA interaction-status adapter should call
  the same mappers after its display scheduler exists and keep initial service
  publication scheduler-safe.
- BatteryChargeV1 status is also an expression input. The WB55 hook feeds
  post-startup battery publishes into the portable `battery_charging.sample`
  bridge; a WBA battery adapter should use the same low-battery expression
  thresholds and keep initial GATT publication scheduler-safe. Battery recovery
  must preserve the same hysteresis and state guard:
  `COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED` may clear only a visible
  low-battery face, not recording, error, sleepy, or other active expressions.
- OtaReadinessV1 status is also an expression input. The portable OTA blocker
  mapper treats blocker bit 3 as a low-battery expression and other nonzero OTA
  blocker values as an error expression. A WBA OTA adapter should call the same
  mapper after its display scheduler exists and keep initial readiness
  publication scheduler-safe.
- Duplicate ExpressionV1 signals that resolve to the current visible face are
  portable state behavior. A WBA scheduler should preserve the suppression and
  avoid issuing redundant panel refreshes.
- Transient ExpressionV1 faces recover through the portable
  `comp_epaper_expression_state_tick()` elapsed-time API. WBA should feed that
  API from its own scheduler/timer and preserve the stable-state rule: recording,
  low-battery, error, idle, and sleepy do not disappear because time passed.
- Preserve expression state telemetry in the WBA adapter. Current face,
  last-signal, visible-age, auto-recovery, and suppressed-duplicate stats
  snapshot fields should remain portable expression metrics.
- `docs/validation/companion-screen-panel-hardware-gate.json` records the
  panel hardware gate and keeps real refresh status deferred until controller,
  pin, timing, and visual evidence exists.
- `docs/validation/companion-screen-panel-evidence-template.json` is the panel
  evidence template for WB55, WBA55, and WBA65. It defines the controller,
  target pin map, BUSY/reset timing, CardStatusV1/diagnostic logs,
  `e_paper.runtime_snapshot` decoded runtime diagnostics,
  `diagnostics_bundle_artifact` summary JSON with
  `epaper.runtime_snapshot_decoded`, before/during/after visual proof, and
  target adapter file evidence required before a real refresh can move out of
  the hardware gate.
- `tools/verify_expression_panel_evidence_record.py --record <record.json>` is
  the evidence record validator. A WBA record must pass it with a
  `*_stm32wba.*` adapter file, matching CardStatusV1 request/content identity,
  `real_ble_bench_artifact`, `diagnostics_bundle_artifact`, the
  `screen_expression_status` six-face host sequence baseline, the
  `screen_expression_demo_status` full demo host sequence baseline, visual
  evidence hashes, clean portability notes, and runtime snapshot health
  evidence before claiming parity.
- Panel evidence runtime diagnostics are part of that gate:
  `e_paper.runtime_snapshot decoded_args show zero panel errors`, zero pending
  display work, and zero dropped display work. WBA records must keep
  `panel_error_count=0` and the same decoded_args schema.
- Panel evidence diagnostics bundle validation is also part of that gate:
  `diagnostics_bundle_artifact` must point at a bounded summary JSON whose
  `epaper.runtime_snapshot_decoded` has `panel_error_count=0`, zero pending
  display work, and zero dropped display work.
- `tools/init_expression_panel_evidence_record.py` creates a
  `DRAFT_UNFILLED` scaffold for the record. WB55 scaffolds pre-fill only the
  known SPI2 transport facts from `companion-screen-panel-wiring-preflight.json`
  and keep controller/DC/RST/BUSY/timing/visual evidence as TODOs. WBA branches
  may use it with `--target WBA55` or `--target WBA65`, but the scaffold itself
  is not evidence and must fail the record validator until all TODOs are
  replaced.
- `docs/validation/companion-screen-panel-hardware-acceptance-plan.json` is
  the panel hardware acceptance plan and is verified by
  `tools/verify_expression_panel_hardware_acceptance_plan.py`. WBA55 and WBA65
  must follow that plan with `*_stm32wba.*` target adapter files, a real BLE
  `--expect-real-panel` artifact, a filled panel evidence record, and a passing
  `verify_expression_panel_evidence_record.py --record` check before claiming
  real-panel parity.
- `docs/validation/companion-screen-panel-hardware-session.json` is the panel
  hardware session scaffold and is verified by
  `tools/verify_expression_panel_hardware_session.py`. It keeps
  `panel_hardware_session_scaffold` as a no-hardware PASS contract. WB55 real
  panel refresh is already accepted; each WBA target session still starts
  deferred and needs its own evidence. WB55 uses
  `.cache/validation/companion-real-panel-wb55-<timestamp>` with
  `panel-hardware-facts.todo.json`, `visual/before_photo.jpg`,
  `visual/after_photo.jpg`, `operator-notes.md`, `--expect-real-panel`,
  `tools/collect_companion_diagnostics.ps1`, and
  `verify_expression_panel_evidence_record.py --record`. WBA55/WBA65 must use
  their own session roots, their own generated `panel-hardware-facts.todo.json`,
  `*_stm32wba.*` adapters, and target pin evidence; the scaffold must not carry
  WB55 SPI2 pin facts into WBA records.
  The `panel_driver_readiness_report`, verified by
  `tools/verify_expression_panel_driver_readiness.py` and recorded at
  `docs/validation/companion-screen-panel-driver-readiness.json`, must report
  `BLOCKED_ON_HARDWARE_FACTS` until target-specific WBA controller, DC/RST/BUSY,
  power, voltage, and timing facts reach `READY_FOR_DRIVER_IMPLEMENTATION`.
  This is the panel hardware session scaffold for WBA real-panel parity.

WB55-specific today:

- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c` translates
  STM32WB GATT writes, STM32_WPAN notify events, and `UTIL_SEQ` task scheduling
  into portable display queue calls.
- WB55 startup enqueues `COMP_EPAPER_EXPRESSION_SIGNAL_BOOT_IDLE` after the
  display task is registered; a WBA port should trigger the same signal through
  its own scheduler.
- WB55 uses a single-shot `HW_TS` timer to wake `Companion_Display_Task` for
  transient ExpressionV1 recovery. The callback only schedules the task; the
  task feeds elapsed `HAL_GetTick()` time into the portable state tick API and
  enqueues recovery through the same display queue.
- WB55 SettingsV1 writes map `display_brightness=0` or quiet-hours flag bit 0
  to `COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY`, and clear only
  settings-caused sleepy back to idle. The local-minute quiet-hours schedule
  stays a host/policy input until a platform time source is selected.
- WB55 DeviceStatusV1 reads/notifies map `active_mode` and `fault_bitmap`
  through `comp_epaper_expression_signal_from_device_status()` after initial
  state publishing, so the devboard can expose device faults or active audio
  mode without scheduling screen work before the display task exists.
- WB55 MeetingStatusV1, SpeakerStatusV1, and WakeWordStatusV1 reads/notifies
  map through portable interaction-status mappers after initial state
  publishing, so control-path diagnostics and later status reads/notifies keep
  the same visible faces.
- Recording FSM state readback should stay numeric and portable. A WBA
  recording adapter should feed the current recording FSM state through
  `comp_epaper_expression_signal_from_recording_state()` so active capture,
  stopping, transfer-ready/active/transferred, cancel, and error-recovery
  states keep the same ExpressionV1 faces without pulling recording or platform
  headers into the e-paper module.
- WB55 OtaReadinessV1 reads/notifies map `blocker_bitmap` through
  `comp_epaper_expression_signal_from_ota_readiness()` after initial state
  publishing, so the devboard fixture can report OTA blockers without
  scheduling screen work before the display task exists.
- WB55 uses `companion_epaper_panel_stm32wb_init()` from
  `panel_target_stm32wb.h/.c`; that target adapter currently delegates to
  `comp_epaper_panel_adapter_init_dry_run()` and must not claim real e-paper
  refresh until controller, DC/RST/BUSY pins, and timing are validated.
- WB55 `Companion_Display_Task` reads display runtime telemetry through
  `comp_epaper_screen_runtime_snapshot()` before publishing
  `e_paper.update_result` and deciding whether more display queue work is
  pending.
- WB55 records `e_paper.runtime_snapshot` from that same aggregate after
  `e_paper.update_result`, so queue pressure, duplicate expression state, panel
  deferrals, and panel errors can be diagnosed without changing CardStatusV1.
- Host tools decode that event into `decoded_args`, so WBA bring-up should keep
  the same log semantics rather than creating target-specific packed-argument
  parsing.
- The no-hardware diagnostics bundle fixture includes the same runtime snapshot
  in its bounded tail, proving the host-facing collection path can surface
  screen runtime pressure without hardware access.
- `tools/verify_expression_panel_gate.py` verifies that current WB55 firmware
  still reports this as a hardware gate rather than a finished display driver.
- `tools/verify_expression_panel_adapter_boundary.py` verifies the portable
  panel adapter boundary and target-owned refresh callback before any real
  transport is added.
- `tools/verify_expression_panel_adapter_behavior.py` verifies the panel
  adapter behavior matrix so WBA code does not redefine callback result or
  CardStatusV1 semantics.
- `docs/validation/companion-screen-wba-port-contract.json` is the
  machine-readable pre-port contract. It records the portable screen files,
  forbidden dependencies, WBA55/WBA65 target assumptions, host-visible
  CardStatusV1/SettingsV1/panel callback invariants, ExpressionV1 visual/layout
  contracts, and the first WBA branch artifacts that must exist before claiming
  parity.
- `docs/validation/companion-screen-target-capabilities.json` is the target
  capability profile. It records WB55 as the current validation target, WBA55
  as the shared safe baseline, and WBA65 as an expanded target that must keep
  WBA55-safe behavior unless a target capability flag gates the expansion.
- `docs/validation/companion-screen-wba55-port-scaffold.json` is the current
  WBA port scaffold. It is generated by
  `tools/init_expression_wba_port_scaffold.py`, stays `DRAFT_PRE_PORT`, and
  lists the first target artifacts a WBA branch must create before parity can
  be claimed.
- The WBA adapter M33 compile gate is
  `tools/verify_wba_adapter_m33_compile.py`. It uses `arm-none-eabi-gcc` with a
  strict freestanding Cortex-M33/WBA55-safe baseline and compiles the panel,
  scheduler, GATT, external-assets, FT6336, power, and pet-memory callback
  adapters as real objects. This closes the gap between source-token checks
  and a target compiler, but it is still pre-port evidence: it does not claim
  a CubeWBA project, selected pins/peripherals, or WBA55/WBA65 hardware parity.

Future WBA work:

- Add a separate CubeWBA project and build wrapper. Do not retarget the WB55
  Cube project in place.
- Start from the WBA port scaffold:
  `python .\tools\init_expression_wba_port_scaffold.py --target WBA55 --write`
  for the conservative baseline, or rerun the same tool with `--target WBA65`
  only after preserving the WBA55-safe contract.
- Keep `python .\tools\verify_expression_wba_portability.py` passing against
  `docs/validation/companion-screen-wba-port-contract.json` while adding the
  WBA project.
- Keep `python .\tools\verify_wba_adapter_m33_compile.py` and its fail-closed
  `--self-test` passing whenever a WBA callback API, shared header, compiler
  option, or adapter source changes. A source-token PASS cannot replace this
  Cortex-M33 object compile.
- Keep `python .\tools\verify_expression_target_capabilities.py` passing before
  using any WBA65-only resource or changing a shared queue, payload, BLE,
  diagnostic, or panel evidence limit.
- Keep `python .\tools\verify_expression_visual_contract.py` passing when WBA
  work changes expression copy or fixtures; `sync_complete`, `happy`, and other
  faces must remain visually distinct in the generated PBM assets.
- Keep `python .\tools\render_expression_visual_acceptance_matrix.py` passing
  when WBA work changes expression copy, fixtures, host status coverage, or
  panel evidence planning; the matrix is the shared per-face acceptance map and
  must not claim real refresh.
- Keep `python .\tools\verify_expression_layout_contract.py` passing when WBA
  work changes expression copy, display variants, or renderer layout; no
  ExpressionV1 title/body/footer should be silently truncated.
- Add WBA BLE/platform code that feeds the same Companion GATT payloads,
  diagnostic events, display queue, expression state, and panel adapter
  contract, including the expression elapsed-time tick path and SettingsV1
  screen hints.
- Preserve the display queue fault paths in the WBA adapter. Queue-full should
  remain host-visible as busy/`queue_full`; payload-too-long and
  unsupported-expression should remain failed status paths.
- Preserve display queue telemetry in the WBA adapter. Pending count,
  high-water count, dropped count, and next-sequence stats snapshot fields
  should remain portable queue metrics; do not replace them with
  target-specific scheduler counters.
- Preserve display generation hygiene in the WBA adapter. A WBA resource or
  OTA activation must set the active CEMP revision through the portable display
  queue, discard or drain stale queued requests from the old revision, preserve
  `resource_revision` on every display request, and log the first
  `coherent_generation=1` current-generation frame before human visual review.
  WBA glue may choose storage slots and target metadata, but it must not replay
  stale queued frames or old procedural/menu assets as a transition.
- Reuse the `screen_expression_status` fixture shape in the first WBA real BLE
  bench so boot idle, settings sleepy, recording, low-battery, sync-complete,
  and error expression requests remain host-observable. Preserve the same
  accepted/final refresh_count sequence integrity and expression CRC model.
- Reuse the real BLE screen bench contract for WBA. A WBA bench artifact must
  include `screen_expression_status`, `final_card_status`, preserve
  accepted/final request identity, carry the six-face host sequence baseline,
  preserve `partial_operation_count` when the live run fails partway, and
  require `--expect-real-panel` before claiming rendered/ok hardware parity.
- Replace the WB55 `HW_TS` hook with a WBA scheduler/timer hook that wakes the
  WBA display task and then calls the same portable expression tick API.
- Use `comp_epaper_expression_state_snapshot()` from WBA scheduler/timer glue
  when deciding dwell timing; do not duplicate private expression-state field
  reads in target code.
- Map WBA SettingsV1 writes through
  `COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY`; do not bypass the portable
  priority and stable-state checks.
- Feed WBA DeviceStatusV1 updates through the same portable device-status
  mapper after the WBA display task exists. Initial service publication must
  not schedule screen work before the platform scheduler is ready.
- Feed WBA MeetingStatusV1, SpeakerStatusV1, and WakeWordStatusV1 updates
  through the same portable interaction-status mapper family after the WBA
  display task exists. Initial service publication must not schedule screen
  work before the platform scheduler is ready.
- Feed WBA BatteryChargeV1 updates through the same low-battery expression
  event bridge after the WBA display task exists. Preserve the battery
  recovery expression guard and hysteresis so recovered samples clear only
  low-battery. Initial service publication must not schedule screen work before
  the platform scheduler is ready.
- Feed WBA OtaReadinessV1 updates through the same portable OTA blocker mapper
  after the WBA display task exists. Initial service publication must not
  schedule screen work before the platform scheduler is ready.
- Add a WBA panel adapter file only after the real display controller and WBA
  pins are selected. The file should be explicitly target-named, for example
  `*_stm32wba.*`, and it must not move SPI/GPIO/BUSY logic into portable
  ExpressionV1, display queue, or panel contract files.
- Mirror the WB55 `panel_target_stm32wb.h/.c` split with a WBA target adapter
  that owns only target glue and calls the same portable panel adapter contract.
- Wire WBA real refresh through the same `comp_epaper_panel_refresh_fn_t`
  target-owned refresh callback used by the WB55 adapter boundary.
- Preserve the panel adapter behavior matrix in the WBA adapter: callback OK,
  BUSY, deferred, and transport-error results must keep the same host-visible
  status meanings and request identity rules.
- Preserve panel adapter telemetry in the WBA adapter. Attempts,
  rendered/deferred/error counts, refresh-configured state, and last-result
  stats snapshot fields should remain portable panel metrics.
- Preserve the screen runtime snapshot in the WBA adapter. The WBA display task
  should call `comp_epaper_screen_runtime_snapshot()` after each display
  dispatch and use its expression, display-queue, and panel stats for
  diagnostics and rescheduling.
- Preserve the runtime snapshot diagnostic in the WBA adapter. The WBA display
  task should emit `e_paper.runtime_snapshot` with the same event id, payload
  packing, and warn-on-`panel.error_count` rule after each display dispatch.
- Preserve runtime diagnostic decode for WBA logs. The host-side
  `decoded_args` schema should continue to expose expression, display queue,
  and panel fields from `e_paper.runtime_snapshot`.
- Preserve the runtime snapshot diagnostics bundle behavior for WBA. Bounded
  diagnostics pulls should include enough recent screen runtime evidence for
  host bring-up tools to inspect `epaper.runtime_snapshot_decoded`.
- Preserve panel evidence runtime diagnostics for WBA records. A WBA real-panel
  evidence record must include `e_paper.runtime_snapshot` decoded_args showing
  `panel_error_count=0`, no pending display queue work, and no dropped display
  work before parity can be claimed.
- Preserve panel evidence diagnostics bundle validation for WBA records. A WBA
  real-panel evidence record must include `diagnostics_bundle_artifact` with
  `epaper.runtime_snapshot_decoded` showing zero panel errors, zero pending
  display queue work, and zero dropped display work.
- Reuse the same panel hardware gate for WBA until the WBA target has its own
  controller, pin map, reset timing, refresh sequence, and before/during/after
  visual evidence.
- Fill the panel evidence template for the WBA target before claiming parity
  with the WB55 bench evidence.
- Validate the filled WBA panel evidence record with
  `tools/verify_expression_panel_evidence_record.py --record <record.json>`;
  do not move the gate based on photos or logs alone.
- Generate the first WBA evidence record from
  `tools/init_expression_panel_evidence_record.py --target WBA55` so the
  required fields stay aligned with the WB55 gate.
- Keep `tools/init_expression_wba_port_scaffold.py --self-test` passing so the
  WBA55 and WBA65 scaffolds continue to require separate CubeWBA project,
  build wrapper, WBA BLE/GATT adapter, scheduler/timer hook, target-named panel
  transport, real BLE artifact, and filled panel evidence record.
- Keep `tools/verify_expression_wba_cube_dependency_preflight.py` passing so a
  WBA branch cannot claim parity while `third_party/STM32CubeWBA`, the separate
  CubeWBA IOC/project, or the WBA build wrapper are still missing.

## FT6336U Touch Port Rules

The current GDEY0154D67-T03 panel exposes its FT6336U touch controller through
I2C. `app/companion_pendant/touch/ft6336.h/.c` owns only the controller's
address, report layout, identity register layout, and coordinate decoding, so it is portable and must
remain free of HAL, Cube, and board pin dependencies.

- `touch_target_stm32wb_ft6336.h/.c` is WB55-only glue. Its I2C3 instance,
  `PC0`/`PB11` pins, timing value, pull configuration, timeout, and boot-log
  wording are dev-board facts, not WBA defaults.
- A target adapter must retry an initial address probe from its normal poll or
  task context. FT6336U may still be completing its power-on sequence when the
  MCU starts, so one early NACK is not proof that touch hardware is absent.
- The WB55 acceptance baseline is address `0x38`, cipher `0x64`, firmware
  `0x01`, chip `0x11`, one successful probe, and zero I2C errors. WBA must
  capture its own values; identity bytes are diagnostics, not a hard-coded
  allowlist that rejects future controller firmware.
- The callback-only WBA pre-port adapter is
  `touch_target_stm32wba_ft6336.h/.c`. It supports WBA55/WBA65, uses 7-bit
  probe/register-read-write callbacks, retries discovery after read errors,
  writes and reads back `G_MODE=0x01` when an interrupt-capable target is
  configured, and calls the portable decoder. `tools/verify_touch_target_stm32wba_ft6336.py`
  guards it with fixture
  `docs/validation/companion-screen-touch-ft6336-stm32wba.json`. The eventual
  CubeWBA IOC glue must bind those callbacks without copying WB55 GPIO,
  peripheral, DMA, interrupt, or clock settings.
- A first WBA bring-up may use polling before `TP_INT`/`TP_RST` are wired, but
  it must not pretend that interrupt operation is proven. Once `TP_INT` is
  connected, target glue must configure and read back `G_MODE=0x01`; if that
  fails it must report `poll-fallback` and retain bounded polling rather than
  silently claiming trigger mode. Pin choice, reset timing, and interrupt
  wake-up policy need WBA-specific evidence.

## WBA Screen Resource Storage Rules

`screen_assets_stm32wba.h/.c` is the WBA55/WBA65 boundary for normal external
`ui_assets`. It accepts a target-owned read callback with a logical
partition-relative offset and a declared partition size, then exposes the
portable `comp_asset_store_t` reader. It must reject out-of-range reads before
calling the target callback.

The selected WBA55 baseline transport is ordinary `1-1-1 SPI NOR`, implemented
by the HAL-free `storage/spi_nor_stm32wba.h/.c` adapter. WBA65 keeps this same
baseline unless a separately evidenced board revision explicitly selects a
different transport. The adapter owns release-from-power-down, JEDEC probe,
status polling, bounded 24-bit reads, 256-byte page splitting, 4 KiB/64 KiB
erase and operation timeouts. CubeWBA glue supplies only chip select, full-duplex SPI
transfer, monotonic time and delay callbacks. It also owns the selected SPI
instance, mode, clock, pins, DMA and Flash power control; none of those board
facts may enter the adapter. The WB55 devboard validates the same command core
through target glue on dedicated hardware `SPI1` (`PA1/PA7/PB4`, software
`PA2` chip select), while its e-paper remains on dedicated `SPI2`. WBA55/WBA65
replace only the target callback binding and selected pins/peripheral; portable
storage clients must not branch on WB55 versus WBA.

- The acceptance id is `wba_screen_assets_scaffold`; its current fixture is
  `docs/validation/companion-screen-assets-stm32wba.json`. Keep it in the
  shared `companion-screen-wba-port-contract.json` portability gate rather
  than treating it as a WB55-only external-flash detail.

- CubeWBA glue chooses the actual external NOR, serial peripheral, pins,
  physical partition address, erase geometry, cache policy, and power control.
  None of those facts enter the callback adapter or CEMP/player code.
- `ui_assets`, recording, OTA staging and persistent product data bind through
  separate logical partitions. They may share one physical SPI NOR only when
  the selected-target partition table proves non-overlap and each writer keeps
  erase and activation ownership within its own partition. Screen code consumes
  `companion_spi_nor_stm32wba_partition_read` and never issues SPI commands.
- CEMP frame encoding is portable. Current WB55 resources use frame-local
  PackBits to keep the development provision image within MCU Flash; a WBA
  target must retain the same bounded `comp_emote_asset_pack_read_frame()`
  decoding behavior rather than materializing an entire resource pack in
  internal Flash or SRAM.
- Bind only verified external storage to this normal path. Mount/profile/CRC
  failure keeps the rescue UI path active; a WBA adapter must not map arbitrary
  memory as a resource pack.
- Resource OTA writes a candidate/staging location. The active reader stays on
  the previous verified pack until target-owned redundant metadata switches it
  atomically. The read adapter does not perform erase, write, or activation.
- Resource generation switches must remain coherent. The WBA storage adapter
  may select the inactive slot, validate manifest/CRC/signature, and expose the
  verified reader, but the product switch is not complete until the portable
  display queue reports the new active revision, discards stale queued requests,
  and the first WBA panel refresh commits one complete current-generation
  frame. If this evidence is missing, the result is still pre-port/pending, not
  WBA screen parity.
- `comp_pet_behavior_memory_t` is portable user-data payload, not a CEMP pack.
  A WBA adapter may persist it only through a target-owned CRC/wear-aware
  user-data store, must preserve it across normal OTA, and must keep its
  physical address and erase policy out of `pet_behavior.h/.c`. The current
  pre-port boundary is `pet_behavior_user_data_stm32wba.h/.c`: it exposes only
  logical slots, CRC records, low-frequency commit decisions, and an explicit
  privacy erase callback for WBA55/WBA65. Real WBA parity still requires target
  storage selection, wear budget, power-fail evidence, normal OTA preservation
  evidence, and privacy/factory erase logs.
- `tools/verify_wba_spi_nor_adapter.py` runs the actual C adapter against a
  deterministic fake NOR, including invalid JEDEC, cross-page write/readback,
  bounds, erase, timeout and screen-partition binding. The strict M33 compile
  gate also compiles the adapter. `tools/verify_expression_screen_assets_stm32wba.py`
  proves the transport-neutral screen callback and WB55 build isolation. These
  are pre-port evidence, not real WBA storage parity.
- Before claiming WBA touch parity, capture the detected I2C address and
  identity registers plus idle,
  down, contact, and up reports at both panel corners, and verify that the
  same `comp_ft6336_touch_sample_t` coordinates reach the portable interaction
  layer. Do not make screen-expression behavior depend on a target-specific
  touch event format.

## New Feature Checklist

- Which layer owns this change: portable app, WB adapter, board pinout, host
  tool, or validation?
- Does any portable file include HAL, STM32_WPAN, generated headers, or board
  pin macros? If yes, split it.
- Does the change mention `CPU2`, `FUS`, `IPCC`, or `HSEM`? If yes, it is WB55
  platform code and needs a WBA note.
- Does the change hard-code flash, RAM, MTU, packet, or DMA sizes? If yes, make
  the limit target-aware or justify it as protocol-level.
- Did the change update docs/tests so a future WBA port knows what to rewrite?
- If the change touches the real display path, did it update the panel evidence
  template record instead of only changing code?
- If the change touches FT6336U, are its controller parsing and interaction
  mapping portable while its I2C, optional INT/RST, and pin choices stay in a
  target-named adapter?
- If the change creates a WBA board target, is 32.768 kHz LSE assembled and
  validated, or is an explicit no-LSE radio-clock/power exception recorded?

## References

- ST STM32WBA series overview:
  https://www.st.com/en/microcontrollers-microprocessors/stm32wba-series.html
- ST STM32WBA BLE hardware setup, including WBA55 and WBA65 board memory/package
  differences:
  https://wiki.st.com/stm32mcu/wiki/Connectivity%3ASTM32WBA_BLE_Hardware_Setup
- ST STM32WBA BLE CubeMX generation guide:
  https://wiki.st.com/stm32mcu/wiki/Connectivity%3ASTM32WBA_BLE_STM32CubeMX
- ST STM32WBA RF hardware design guidance (AN5948):
  https://www.st.com/resource/en/application_note/an5948-how-to-develop-rf-hardware-using-stm32wba-mcus-stmicroelectronics.pdf
- ST STM32WBA5xxx datasheet, including LSE requirements:
  https://www.st.com/resource/en/datasheet/stm32wba55ug.pdf
