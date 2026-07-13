# Companion Screen Acceptance Report

Source index: `docs/validation/companion-screen-acceptance-index.json`

This report is generated. Update it with `python .\tools\render_expression_acceptance_report.py --write`.

## Summary

- PASS: 84
- DEFERRED_HARDWARE: 1
- PENDING_HUMAN: 2
- TOTAL: 87
- Next hardware gate: `wb55_rev52_runtime_recheck`
- Next human gate: `wb55_touch_visual_acceptance`

## Item Status

| # | Status | ID | Title |
|---:|---|---|---|
| 1 | PASS | `no_hardware_expression_renderer` | No-hardware ExpressionV1 renderer |
| 2 | PASS | `expression_visual_contract` | Expression visual contract |
| 3 | PASS | `expression_visual_acceptance_matrix` | Expression visual acceptance matrix |
| 4 | PASS | `generated_art_style_contract` | Generated-art style contract |
| 5 | PASS | `screen_generation_swap_guard` | New/old screen generation swap guard |
| 6 | PASS | `screen_refresh_feel_contract` | Screen refresh feel and ghosting contract |
| 7 | PASS | `expression_layout_contract` | Expression layout contract |
| 8 | PASS | `ble_to_expression_policy` | BLE/status to ExpressionV1 policy |
| 9 | PASS | `wb55_display_queue_boundary` | WB55 display queue boundary |
| 10 | PASS | `display_queue_fault_paths` | Display queue fault paths |
| 11 | PASS | `display_queue_telemetry` | Display queue telemetry |
| 12 | PASS | `screen_display_drain_contract` | Screen display drain contract |
| 13 | PASS | `wb55_boot_idle_expression` | WB55 boot idle expression |
| 14 | PASS | `screen_status_observability` | Screen status observability |
| 15 | PASS | `host_ble_expression_status_fixture` | Host BLE ExpressionV1 status fixture |
| 16 | PASS | `host_ble_expression_extended_status_fixture` | Host BLE ExpressionV1 extended status coverage |
| 17 | PASS | `host_ble_expression_status_sequence` | Host BLE ExpressionV1 status sequence integrity |
| 18 | PASS | `expression_host_manifest` | ExpressionV1 host manifest |
| 19 | PASS | `screen_expression_demo_host_status_sequence` | Screen expression demo host status sequence |
| 20 | PASS | `screen_settings_expression_policy` | Screen settings expression policy |
| 21 | PASS | `firmware_expression_state` | Firmware ExpressionV1 state path |
| 22 | PASS | `expression_state_telemetry_snapshot` | Expression state telemetry snapshot |
| 23 | PASS | `expression_catalog_contract` | ExpressionV1 catalog contract |
| 24 | PASS | `expression_copy_contract` | ExpressionV1 copy contract |
| 25 | PASS | `expression_priority_matrix` | Expression priority matrix |
| 26 | PASS | `expression_input_source_matrix` | Expression input source matrix |
| 27 | PASS | `expression_unknown_signal_guard` | Expression unknown signal guard |
| 28 | PASS | `expression_duplicate_refresh_suppression` | Expression duplicate refresh suppression |
| 29 | PASS | `expression_transient_auto_recovery` | Expression transient auto recovery |
| 30 | PASS | `wb55_expression_tick_scheduler` | WB55 expression tick scheduler |
| 31 | PASS | `wb55_settings_expression_hint` | WB55 settings expression hint |
| 32 | PASS | `wb55_device_status_expression_hint` | WB55 device status expression hint |
| 33 | PASS | `wb55_interaction_status_expression_hint` | WB55 interaction status expression hint |
| 34 | PASS | `wb55_battery_expression_hint` | WB55 battery expression hint |
| 35 | PASS | `battery_recovery_expression_guard` | Battery recovery expression guard |
| 36 | PASS | `recording_state_expression_hook` | Recording FSM state expression hook |
| 37 | PASS | `wb55_ota_readiness_expression_hint` | WB55 OTA readiness expression hint |
| 38 | PASS | `diagnostic_event_expression_bridge` | Diagnostic-event expression bridge |
| 39 | PASS | `user_journey_expression_acceptance` | User journey expression acceptance |
| 40 | PASS | `screen_expression_demo_sequence` | Screen expression demo sequence |
| 41 | PASS | `screen_expression_demo_panel_handoff` | Screen expression demo panel handoff |
| 42 | PASS | `screen_acceptance_runner` | Screen acceptance runner |
| 43 | PASS | `screen_feature_roadmap` | Screen feature roadmap |
| 44 | PASS | `screen_feature_checklist` | Screen feature checklist |
| 45 | PASS | `wba_pre_port_gate` | WBA pre-port gate |
| 46 | PASS | `wba_lse_clock_contract` | WBA LSE/RTC/BLE sleep clock contract |
| 47 | PASS | `wba_cube_dependency_preflight` | WBA CubeWBA dependency preflight |
| 48 | PASS | `wba_port_scaffold` | WBA port scaffold |
| 49 | PASS | `wba_panel_target_adapter_scaffold` | WBA panel target adapter scaffold |
| 50 | PASS | `wba_refresh_intent_contract` | WBA refresh intent contract |
| 51 | PASS | `wba_display_scheduler_scaffold` | WBA display scheduler scaffold |
| 52 | PASS | `wba_screen_gatt_scaffold` | WBA screen GATT scaffold |
| 53 | PASS | `wba_screen_assets_scaffold` | WBA screen-assets scaffold |
| 54 | PASS | `wba_pet_behavior_user_data_scaffold` | WBA pet behavior user-data scaffold |
| 55 | PASS | `target_capability_profile` | Target capability profile |
| 56 | PASS | `devboard_ioc_screen_preflight` | Devboard IOC screen preflight |
| 57 | PASS | `panel_wiring_preflight` | Panel wiring preflight |
| 58 | PASS | `panel_evidence_scaffold_wiring_prefill` | Panel evidence scaffold wiring prefill |
| 59 | PASS | `panel_hardware_session_scaffold` | Panel hardware session scaffold |
| 60 | PASS | `panel_session_directory_preflight` | Panel session directory preflight |
| 61 | PASS | `panel_hardware_facts_intake` | Panel hardware facts intake |
| 62 | PASS | `panel_hardware_facts_worksheet` | Panel hardware facts worksheet |
| 63 | PASS | `panel_bringup_operator_packet` | Panel bring-up operator packet |
| 64 | PASS | `panel_driver_readiness_report` | Panel driver readiness report |
| 65 | PASS | `panel_hardware_facts_bridge` | Panel hardware facts bridge |
| 66 | PASS | `panel_target_ops_boundary` | Panel adapter target-ops boundary |
| 67 | PASS | `wb55_panel_target_adapter_scaffold` | WB55 panel target adapter scaffold |
| 68 | PASS | `panel_adapter_behavior_matrix` | Panel adapter behavior matrix |
| 69 | PASS | `panel_adapter_telemetry_snapshot` | Panel adapter telemetry snapshot |
| 70 | PASS | `screen_runtime_snapshot` | Screen runtime snapshot |
| 71 | PASS | `screen_runtime_diagnostics` | Screen runtime diagnostics |
| 72 | PASS | `screen_runtime_diagnostic_decode` | Screen runtime diagnostic decode |
| 73 | PASS | `screen_runtime_diagnostics_bundle` | Screen runtime diagnostics bundle |
| 74 | PASS | `real_ble_screen_final_status_bench` | Real BLE screen final-status bench |
| 75 | PASS | `real_ble_expression_status_sequence_contract` | Real BLE ExpressionV1 status sequence contract |
| 76 | PASS | `panel_hardware_evidence_template` | Panel hardware evidence template |
| 77 | PASS | `panel_evidence_runtime_diagnostics` | Panel evidence runtime diagnostics |
| 78 | PASS | `panel_evidence_diagnostics_bundle_validator` | Panel evidence diagnostics bundle validator |
| 79 | PASS | `panel_evidence_record_validator` | Panel evidence record validator |
| 80 | PASS | `panel_evidence_real_ble_sequence_validator` | Panel evidence real BLE sequence validator |
| 81 | PASS | `panel_hardware_acceptance_plan` | Panel hardware acceptance plan |
| 82 | PASS | `wb55_screen_build_matrix` | WB55 screen build matrix |
| 83 | PASS | `wb55_real_panel_refresh` | WB55 real e-paper panel refresh |
| 84 | PASS | `wb55_runtime_serial_capture_preflight` | WB55 runtime serial capture preflight |
| 85 | DEFERRED_HARDWARE | `wb55_rev52_runtime_recheck` | WB55 rev52 provision/normal runtime recheck |
| 86 | PENDING_HUMAN | `wb55_touch_visual_acceptance` | WB55 touch navigation and fast-refresh visual acceptance |
| 87 | PENDING_HUMAN | `companion_screen_goal_audit` | Active goal completion audit |

## Item Details

### 1. No-hardware ExpressionV1 renderer

- ID: `no_hardware_expression_renderer`
- Status: `PASS`
- Summary: All ExpressionV1 faces render deterministic PBM fixtures for 2.13in and 1.54in variants.
- WBA impact: Portable renderer contract is reusable for WBA without STM32 platform dependencies.

Evidence:
- `app/companion_pendant/epaper/card_renderer.py`
- `docs/validation/companion-pendant-firmware-bringup-1.6-epaper-fixtures.json`
- `docs/validation/epaper/expression-preview.svg`
- `docs/validation/companion-screen-expression-preview.json`

Validation commands:
- `python .\tools\render_epaper_fixtures.py --self-test`
- `python .\tools\render_expression_preview.py`
- `python .\tools\verify_epaper_assets.py`

### 2. Expression visual contract

- ID: `expression_visual_contract`
- Status: `PASS`
- Summary: ExpressionV1 PBM fixtures expose nonblank, density-bounded, visually distinct face crops so sync-complete, happy, and other faces cannot regress into duplicate artwork.
- WBA impact: WBA ports reuse the same PBM fixtures and must preserve visually distinct ExpressionV1 faces while replacing only target transport.

Evidence:
- `app/companion_pendant/epaper/card_renderer.py`
- `tools/verify_expression_visual_contract.py`
- `docs/validation/companion-screen-expression-visual-contract.json`
- `docs/validation/companion-pendant-firmware-bringup-1.6-epaper-fixtures.json`
- `docs/validation/epaper/expression-preview.svg`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\render_epaper_fixtures.py --self-test`
- `python .\tools\verify_expression_visual_contract.py`
- `python .\tools\verify_epaper_assets.py`
- `python .\tools\verify_expression_wba_portability.py`

### 3. Expression visual acceptance matrix

- ID: `expression_visual_acceptance_matrix`
- Status: `PASS`
- Summary: A generated per-face matrix links every ExpressionV1 visual fixture and metric to copy, source signals, policy cases, and host coverage, while explicitly leaving real panel refresh deferred.
- WBA impact: WBA ports must preserve the same per-face visual matrix, PBM hashes, copy, and host face/signal mapping before replacing only target panel transport.

Evidence:
- `tools/render_expression_visual_acceptance_matrix.py`
- `docs/validation/companion-screen-expression-visual-acceptance-matrix.json`
- `docs/validation/companion-screen-expression-visual-acceptance-matrix.md`
- `docs/validation/companion-screen-expression-visual-contract.json`
- `docs/validation/companion-screen-expression-host-manifest.json`
- `docs/validation/companion-pendant-firmware-bringup-1.6-epaper-fixtures.json`
- `docs/validation/epaper/expression-preview.svg`
- `docs/validation/epaper/expression-storyboard.svg`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\render_expression_visual_acceptance_matrix.py`
- `python .\tools\render_expression_visual_acceptance_matrix.py --self-test`
- `python .\tools\verify_expression_visual_contract.py`
- `python .\tools\render_expression_host_manifest.py`
- `python .\tools\verify_epaper_assets.py`
- `python .\tools\verify_expression_wba_portability.py`

### 4. Generated-art style contract

- ID: `generated_art_style_contract`
- Status: `PASS`
- Summary: The generated pet/menu reference art is captured as a named style contract with machine-readable pet and menu anchors, keeping future生图 adjustments fast without scattering hard-coded coordinates or moving large art into internal Flash.
- WBA impact: WBA ports reuse the same style contract and external CEMP resource policy; only target transport, storage drivers, and panel timing are replaced.

Evidence:
- `app/companion_pendant/epaper/pet_visual_style.h`
- `tools/generate_screen_menu_assets.py`
- `tools/render_generated_art_style_contract.py`
- `docs/validation/companion-screen-generated-art-style-contract.md`
- `docs/validation/companion-screen-generated-art-style-contract.json`
- `docs/validation/companion-screen-generated-art-style-contract.snapshot.md`
- `docs/companion_screen_expression_system.md`
- `docs/companion_screen_project_plan.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\render_generated_art_style_contract.py`
- `python .\tools\verify_pet_expression_system.py`
- `python .\tools\verify_screen_menu_assets.py`
- `python .\tools\verify_expression_wba_portability.py`

### 5. New/old screen generation swap guard

- ID: `screen_generation_swap_guard`
- Status: `PASS`
- Summary: The project separates physical e-paper ghosting from old/new resource interleaving using the 2026-07-13 research note and release ledger: CEMP revisions must activate atomically, drain or discard stale queued frames, mark display_result coherent_generation, and never mix old procedural faces, old menu PBM, old sheet crops, or stale framebuffer content into the normal product path.
- WBA impact: WBA55/WBA65 must preserve resource-generation activation and stale-frame draining semantics while replacing only target storage and panel transport.

Evidence:
- `docs/companion_screen_project_plan.md`
- `docs/validation/companion-screen-generation-swap-research.md`
- `docs/validation/companion-screen-display-queue-generation-hygiene.json`
- `docs/validation/companion-screen-generation-release-ledger.json`
- `docs/validation/companion-screen-display-drain-contract.json`
- `tools/verify_screen_refresh_feel_contract.py`
- `tools/verify_display_queue_generation_hygiene.py`
- `tools/verify_expression_display_drain.py`
- `docs/validation/companion-screen-refresh-feel-contract.json`
- `docs/validation/companion-screen-generated-expression-sheet-import.json`
- `docs/validation/companion-screen-generated-expression-normal-pack-contact-sheet.json`

Validation commands:
- `python .\tools\verify_screen_refresh_feel_contract.py`
- `python .\tools\verify_display_queue_generation_hygiene.py`
- `python .\tools\verify_screen_generation_release_ledger.py`
- `python .\tools\verify_expression_display_drain.py`
- `python .\tools\import_generated_expression_sheet.py`
- `python .\tools\render_generated_expression_normal_pack_contact_sheet.py`

### 6. Screen refresh feel and ghosting contract

- ID: `screen_refresh_feel_contract`
- Status: `PASS`
- Summary: The product refresh contract records the vendor-backed e-paper tradeoff: differential partial refresh for touch interaction, one quiet maintenance cleanup after contact settles, and full refresh only for unknown baseline or fault recovery.
- WBA impact: WBA panel targets must preserve portable refresh intents and choose target waveforms without changing scene/player behavior.

Evidence:
- `docs/companion_screen_project_plan.md`
- `tools/verify_screen_refresh_feel_contract.py`
- `docs/validation/companion-screen-refresh-feel-contract.json`
- `app/companion_pendant/epaper/refresh_policy.c`
- `app/companion_pendant/epaper/display_queue.c`
- `app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c`

Validation commands:
- `python .\tools\verify_screen_refresh_feel_contract.py`
- `python .\tools\verify_epaper_refresh_policy.py`
- `python .\tools\verify_screen_menu_assets.py`

### 7. Expression layout contract

- ID: `expression_layout_contract`
- Status: `PASS`
- Summary: ExpressionV1 title/body/footer copy fits the 2.13in and 1.54in renderer budgets without truncation or body/footer overlap.
- WBA impact: WBA ports must keep the same ExpressionV1 copy budget and layout safety while replacing only target transport.

Evidence:
- `app/companion_pendant/epaper/card_renderer.py`
- `tools/verify_expression_layout_contract.py`
- `docs/validation/companion-screen-expression-layout-contract.json`
- `docs/validation/companion-screen-expression-catalog.json`
- `docs/validation/companion-screen-expression-visual-contract.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_layout_contract.py`
- `python .\tools\verify_expression_catalog_contract.py`
- `python .\tools\verify_expression_visual_contract.py`
- `python .\tools\verify_epaper_assets.py`
- `python .\tools\verify_expression_wba_portability.py`

### 8. BLE/status to ExpressionV1 policy

- ID: `ble_to_expression_policy`
- Status: `PASS`
- Summary: Status snapshots and diagnostic event names map to visible ExpressionV1 cards.
- WBA impact: Portable policy can be reused by a WBA host/diagnostic path.

Evidence:
- `app/companion_pendant/epaper/expression_policy.py`
- `docs/validation/companion-screen-expression-policy.json`

Validation commands:
- `python .\tools\verify_expression_policy.py`
- `python .\tools\verify_companion_gatt_static.py`

### 9. WB55 display queue boundary

- ID: `wb55_display_queue_boundary`
- Status: `PASS`
- Summary: WB55 GATT callbacks enqueue card/expression work and a display task owns panel completion.
- WBA impact: WBA should add its own platform task/GATT adapter while reusing the queue contract.

Evidence:
- `app/companion_pendant/epaper/display_queue.h`
- `app/companion_pendant/epaper/display_queue.c`
- `app/companion_pendant/epaper/panel_adapter.h`
- `app/companion_pendant/epaper/panel_adapter.c`
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c`

Validation commands:
- `python .\tools\verify_display_queue_static.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -Force`

### 10. Display queue fault paths

- ID: `display_queue_fault_paths`
- Status: `PASS`
- Summary: Queue-full, payload-too-long, unsupported-expression, and expression enqueue rollback paths publish stable host-visible status.
- WBA impact: WBA must preserve the same queue fault status/error meanings and expression rollback behavior while replacing only platform scheduling.

Evidence:
- `app/companion_pendant/epaper/display_queue.h`
- `app/companion_pendant/epaper/display_queue.c`
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c`
- `docs/validation/companion-screen-display-queue-faults.json`

Validation commands:
- `python .\tools\verify_display_queue_fault_paths.py`
- `python .\tools\verify_display_queue_static.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -Force`

### 11. Display queue telemetry

- ID: `display_queue_telemetry`
- Status: `PASS`
- Summary: The portable display queue exposes a stats snapshot for pending, high-water, dropped, queue bounds, and sequence counters without adding platform dependencies or changing CardStatusV1.
- WBA impact: WBA schedulers should preserve the same queue telemetry stats snapshot so slow real-panel refresh pressure can be diagnosed without changing host-visible CardStatusV1.

Evidence:
- `app/companion_pendant/epaper/display_queue.h`
- `app/companion_pendant/epaper/display_queue.c`
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c`
- `docs/validation/companion-screen-display-queue-telemetry.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`

Validation commands:
- `python .\tools\verify_display_queue_telemetry.py`
- `python .\tools\verify_display_queue_static.py`
- `python .\tools\verify_display_queue_fault_paths.py`
- `python .\tools\verify_expression_wba_portability.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 12. Screen display drain contract

- ID: `screen_display_drain_contract`
- Status: `PASS`
- Summary: WB55 display task drains one queued request per scheduler pass, records runtime diagnostics before final CardStatusV1, and reschedules only while work remains.
- WBA impact: WBA display tasks must preserve one-request drain, target-refresh callback use, runtime diagnostics, final CardStatusV1 identity, and pending-work rescheduling.

Evidence:
- `app/companion_pendant/epaper/display_queue.h`
- `app/companion_pendant/epaper/display_queue.c`
- `app/companion_pendant/epaper/panel_adapter.h`
- `app/companion_pendant/epaper/screen_runtime.h`
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c`
- `tools/verify_expression_display_drain.py`
- `docs/validation/companion-screen-display-drain-contract.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_display_drain.py`
- `python .\tools\verify_display_queue_static.py`
- `python .\tools\verify_display_queue_telemetry.py`
- `python .\tools\verify_expression_screen_runtime_snapshot.py`
- `python .\tools\verify_expression_screen_runtime_diagnostics.py`
- `python .\tools\verify_expression_wba_portability.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 13. WB55 boot idle expression

- ID: `wb55_boot_idle_expression`
- Status: `PASS`
- Summary: WB55 startup enqueues the default idle ExpressionV1 card through the same display queue path.
- WBA impact: Future WBA startup should enqueue BOOT_IDLE through its own platform scheduler while reusing the same state model.

Evidence:
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c`
- `app/companion_pendant/epaper/expression_state.h`
- `app/companion_pendant/epaper/expression_state.c`
- `docs/validation/companion-screen-firmware-expression-state.json`

Validation commands:
- `python .\tools\verify_expression_firmware_state.py`
- `python .\tools\verify_display_queue_static.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 14. Screen status observability

- ID: `screen_status_observability`
- Status: `PASS`
- Summary: CardStatusV1 exposes stable render states, last-error codes, request identity, refresh_count, and dry-run no-panel diagnostics.
- WBA impact: WBA must preserve CardStatusV1 numeric state/error meanings while swapping only the platform scheduler and panel driver.

Evidence:
- `app/companion_pendant/gatt/companion_gatt_stm32wb.h`
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c`
- `docs/ble_gatt_contract.md`
- `docs/validation/companion-screen-status-observability.json`
- `docs/validation/companion_ble_matrix.json`

Validation commands:
- `python .\tools\verify_expression_status_observability.py`
- `python .\tools\verify_companion_ble_matrix.py`
- `python .\tools\verify_display_queue_static.py`

### 15. Host BLE ExpressionV1 status fixture

- ID: `host_ble_expression_status_fixture`
- Status: `PASS`
- Summary: The no-hardware BLE matrix correlates ExpressionV1 CardStatusV1 accepted/final states with diagnostic expression/signal payloads.
- WBA impact: WBA real BLE bench should preserve this same status/diagnostic fixture shape while swapping only the platform BLE adapter.

Evidence:
- `tools/companion_ble_tool.py`
- `tools/verify_companion_ble_matrix.py`
- `docs/validation/companion_ble_matrix.json`
- `docs/validation/companion-screen-status-observability.json`

Validation commands:
- `python .\tools\companion_ble_tool.py --self-test`
- `python .\tools\verify_companion_ble_matrix.py`
- `python .\tools\verify_expression_status_observability.py`

### 16. Host BLE ExpressionV1 extended status coverage

- ID: `host_ble_expression_extended_status_fixture`
- Status: `PASS`
- Summary: The no-hardware BLE matrix observes idle, sleepy, recording, low-battery, sync-complete, and error ExpressionV1 requests through CardStatusV1 and diagnostic arg3 decode.
- WBA impact: WBA real BLE benches should keep the six-face screen_expression_status fixture shape so extended ExpressionV1 status remains host-observable before panel parity is claimed.

Evidence:
- `tools/companion_ble_tool.py`
- `tools/verify_companion_ble_matrix.py`
- `tools/verify_expression_status_observability.py`
- `docs/validation/companion_ble_matrix.json`
- `docs/validation/companion-screen-status-observability.json`
- `docs/companion_screen_expression_system.md`
- `docs/ble_gatt_contract.md`
- `docs/stm32wba_migration_rules.md`

Validation commands:
- `python .\tools\companion_ble_tool.py --self-test`
- `python .\tools\verify_companion_ble_matrix.py`
- `python .\tools\verify_expression_status_observability.py`
- `python .\tools\verify_expression_wba_portability.py`

### 17. Host BLE ExpressionV1 status sequence integrity

- ID: `host_ble_expression_status_sequence`
- Status: `PASS`
- Summary: The no-hardware BLE matrix proves each ExpressionV1 accepted/final CardStatusV1 pair has contiguous refresh_count values, stable request/content identity, deterministic expression CRCs, and matching diagnostic arg3 decode.
- WBA impact: WBA real BLE benches should preserve the same screen_expression_status refresh_count sequence, request/content identity, expression CRC model, and diagnostic arg3 decode before panel parity is claimed.

Evidence:
- `tools/verify_expression_host_status_sequence.py`
- `tools/companion_ble_tool.py`
- `tools/verify_companion_ble_matrix.py`
- `tools/verify_expression_status_observability.py`
- `docs/validation/companion-screen-expression-host-status-sequence.json`
- `docs/validation/companion_ble_matrix.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `docs/ble_gatt_contract.md`

Validation commands:
- `python .\tools\verify_expression_host_status_sequence.py`
- `python .\tools\companion_ble_tool.py --self-test`
- `python .\tools\verify_companion_ble_matrix.py`
- `python .\tools\verify_expression_status_observability.py`
- `python .\tools\verify_expression_wba_portability.py`

### 18. ExpressionV1 host manifest

- ID: `expression_host_manifest`
- Status: `PASS`
- Summary: A generated host manifest lists every ExpressionV1 face with copy, priority, recovery, signals, policy cases, CardStatusV1/diagnostic observability, and legacy/demo host coverage.
- WBA impact: WBA host/status adapters must keep the same face IDs, signal IDs, diagnostic arg3 model, and CardStatusV1 meanings while replacing only platform transport.

Evidence:
- `tools/render_expression_host_manifest.py`
- `docs/validation/companion-screen-expression-host-manifest.json`
- `docs/validation/companion-screen-expression-host-manifest.md`
- `docs/validation/companion-screen-expression-catalog.json`
- `docs/validation/companion-screen-expression-policy.json`
- `docs/validation/companion-screen-expression-host-status-sequence.json`
- `docs/validation/companion-screen-expression-demo-host-status-sequence.json`
- `docs/validation/companion-screen-expression-state-telemetry.json`
- `docs/companion_screen_expression_system.md`
- `app/companion_pendant/epaper/README.md`
- `docs/stm32wba_migration_rules.md`

Validation commands:
- `python .\tools\render_expression_host_manifest.py`
- `python .\tools\render_expression_host_manifest.py --self-test`
- `python .\tools\verify_expression_catalog_contract.py`
- `python .\tools\verify_expression_policy.py`
- `python .\tools\verify_expression_host_status_sequence.py`
- `python .\tools\verify_expression_demo_host_status_sequence.py`
- `python .\tools\verify_expression_state_telemetry.py`

### 19. Screen expression demo host status sequence

- ID: `screen_expression_demo_host_status_sequence`
- Status: `PASS`
- Summary: The full demo sequence has a host-visible CardStatusV1 contract: 29 accepted/final pairs cover every ExpressionV1 face, while 8 held steps emit no host status.
- WBA impact: WBA real BLE artifacts can carry screen_expression_demo_status so every demo face stays host-observable, while held_steps_emit_no_host_status protects duplicate/lower-priority suppression.

Evidence:
- `tools/verify_expression_demo_host_status_sequence.py`
- `docs/validation/companion-screen-expression-demo-host-status-sequence.json`
- `docs/validation/companion-screen-expression-demo-sequence.json`
- `docs/validation/companion-screen-expression-host-status-sequence.json`
- `docs/validation/companion-screen-expression-catalog.json`
- `docs/validation/companion-screen-real-ble-bench.json`
- `tools/companion_ble_real_bench.py`
- `docs/companion_screen_expression_system.md`
- `docs/ble_gatt_contract.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_demo_host_status_sequence.py`
- `python .\tools\verify_expression_demo_sequence.py`
- `python .\tools\verify_expression_host_status_sequence.py`
- `python .\tools\verify_expression_catalog_contract.py`
- `python .\tools\verify_expression_real_ble_screen_bench.py`
- `python .\tools\verify_expression_wba_portability.py`

### 20. Screen settings expression policy

- ID: `screen_settings_expression_policy`
- Status: `PASS`
- Summary: Quiet hours and display-off settings map to sleepy without hiding recording, low-battery, or error faces.
- WBA impact: WBA should reuse the same settings-to-expression policy while replacing only platform-specific settings transport.

Evidence:
- `app/companion_pendant/epaper/expression_policy.py`
- `docs/ble_gatt_contract.md`
- `docs/validation/companion-screen-settings-policy.json`

Validation commands:
- `python .\tools\verify_expression_settings_policy.py`
- `python .\tools\verify_expression_policy.py`
- `python .\tools\verify_expression_wba_portability.py`

### 21. Firmware ExpressionV1 state path

- ID: `firmware_expression_state`
- Status: `PASS`
- Summary: Portable C state model matches renderer copy, policy priorities, and WB55 event enqueue path.
- WBA impact: Expression state is kept HAL-free and reusable under a future WBA adapter.

Evidence:
- `app/companion_pendant/epaper/expression_state.h`
- `app/companion_pendant/epaper/expression_state.c`
- `docs/validation/companion-screen-firmware-expression-state.json`

Validation commands:
- `python .\tools\verify_expression_firmware_state.py`
- `python .\tools\verify_expression_wba_portability.py`

### 22. Expression state telemetry snapshot

- ID: `expression_state_telemetry_snapshot`
- Status: `PASS`
- Summary: The portable ExpressionV1 state model exposes a stats snapshot for current face, last signal, revision, visible age, auto-recovery dwell, and duplicate suppression.
- WBA impact: WBA scheduler hooks should use the same expression state stats snapshot for current face, dwell timing, and duplicate suppression diagnostics while replacing only target timing glue.

Evidence:
- `app/companion_pendant/epaper/expression_state.h`
- `app/companion_pendant/epaper/expression_state.c`
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c`
- `docs/validation/companion-screen-expression-state-telemetry.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `tools/verify_expression_state_telemetry.py`

Validation commands:
- `python .\tools\verify_expression_state_telemetry.py`
- `python .\tools\verify_expression_firmware_state.py`
- `python .\tools\verify_expression_journeys.py`
- `python .\tools\verify_display_queue_static.py`
- `python .\tools\verify_expression_wba_portability.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 23. ExpressionV1 catalog contract

- ID: `expression_catalog_contract`
- Status: `PASS`
- Summary: Stable ExpressionV1 and signal numeric IDs are tied to copy, priority, auto-recovery, and diagnostic payload semantics for host/WBA reuse.
- WBA impact: WBA adapters and host tools must preserve the catalog's stable numeric IDs, expression card slot, request ID base, and diagnostic arg3 model.

Evidence:
- `tools/verify_expression_catalog_contract.py`
- `docs/validation/companion-screen-expression-catalog.json`
- `app/companion_pendant/epaper/expression_state.h`
- `app/companion_pendant/epaper/expression_state.c`
- `app/companion_pendant/epaper/card_renderer.py`
- `app/companion_pendant/epaper/expression_policy.py`
- `docs/validation/companion-screen-firmware-expression-state.json`
- `docs/validation/companion_ble_matrix.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`

Validation commands:
- `python .\tools\verify_expression_catalog_contract.py`
- `python .\tools\verify_expression_firmware_state.py`
- `python .\tools\verify_epaper_assets.py`
- `python .\tools\verify_expression_status_observability.py`
- `python .\tools\verify_expression_wba_portability.py`

### 24. ExpressionV1 copy contract

- ID: `expression_copy_contract`
- Status: `PASS`
- Summary: ExpressionV1 title/body/footer copy is synchronized across renderer, firmware, catalog, layout, priority matrix, and generated PBM fixtures.
- WBA impact: WBA adapters must reuse the same ExpressionV1 user-visible copy and must not fork title/body/footer text in target glue.

Evidence:
- `tools/verify_expression_copy_contract.py`
- `docs/validation/companion-screen-expression-copy-contract.json`
- `app/companion_pendant/epaper/card_renderer.py`
- `app/companion_pendant/epaper/expression_state.c`
- `app/companion_pendant/epaper/expression_policy.py`
- `docs/validation/companion-screen-expression-catalog.json`
- `docs/validation/companion-screen-firmware-expression-state.json`
- `docs/validation/companion-screen-expression-layout-contract.json`
- `docs/validation/companion-screen-expression-priority-matrix.json`
- `docs/validation/companion-pendant-firmware-bringup-1.6-epaper-fixtures.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_copy_contract.py`
- `python .\tools\verify_expression_catalog_contract.py`
- `python .\tools\verify_expression_firmware_state.py`
- `python .\tools\verify_expression_layout_contract.py`
- `python .\tools\verify_expression_priority_matrix.py`
- `python .\tools\verify_epaper_assets.py`
- `python .\tools\verify_expression_wba_portability.py`

### 25. Expression priority matrix

- ID: `expression_priority_matrix`
- Status: `PASS`
- Summary: Every initialized ExpressionV1 face/signal pair has a recorded apply, suppress, or block outcome, including settings sleepy and battery recovered guards.
- WBA impact: WBA scheduler/status adapters must preserve the same priority, duplicate, lowering, battery recovery, and transient/stable recovery matrix.

Evidence:
- `app/companion_pendant/epaper/expression_state.h`
- `app/companion_pendant/epaper/expression_state.c`
- `tools/verify_expression_priority_matrix.py`
- `docs/validation/companion-screen-expression-priority-matrix.json`
- `docs/validation/companion-screen-expression-catalog.json`
- `docs/validation/companion-screen-firmware-expression-state.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_priority_matrix.py`
- `python .\tools\verify_expression_catalog_contract.py`
- `python .\tools\verify_expression_firmware_state.py`
- `python .\tools\verify_expression_journeys.py`
- `python .\tools\verify_expression_wba_portability.py`

### 26. Expression input source matrix

- ID: `expression_input_source_matrix`
- Status: `PASS`
- Summary: Every product input source that can request an ExpressionV1 signal is linked to a focused fixture and WBA adapter checklist entry.
- WBA impact: WBA status adapters must preserve every boot, diagnostic, settings, status, recording, battery, interaction, and OTA expression input source.

Evidence:
- `app/companion_pendant/epaper/expression_events.h`
- `app/companion_pendant/epaper/expression_events.c`
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c`
- `tools/verify_expression_input_source_matrix.py`
- `docs/validation/companion-screen-expression-input-source-matrix.json`
- `docs/validation/companion-screen-expression-event-bridge.json`
- `docs/validation/companion-screen-settings-policy.json`
- `docs/validation/companion-screen-device-status-expression-hook.json`
- `docs/validation/companion-screen-battery-expression-hook.json`
- `docs/validation/companion-screen-recording-state-expression-hook.json`
- `docs/validation/companion-screen-interaction-status-expression-hook.json`
- `docs/validation/companion-screen-ota-expression-hook.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_input_source_matrix.py`
- `python .\tools\verify_expression_event_bridge.py`
- `python .\tools\verify_expression_settings_policy.py`
- `python .\tools\verify_expression_device_status_hook.py`
- `python .\tools\verify_expression_battery_hook.py`
- `python .\tools\verify_expression_recording_state_hook.py`
- `python .\tools\verify_expression_interaction_status_hook.py`
- `python .\tools\verify_expression_ota_hook.py`
- `python .\tools\verify_expression_wba_portability.py`

### 27. Expression unknown signal guard

- ID: `expression_unknown_signal_guard`
- Status: `PASS`
- Summary: Unsupported or future ExpressionV1 signals are rejected through a portable preflight API before visible state, duplicate counters, display queue work, or CardStatusV1 request identity changes.
- WBA impact: WBA adapters should preserve comp_epaper_expression_signal_is_supported() and the append-only signal catalog so unsupported future signals are rejected before platform glue changes display state or queue work.

Evidence:
- `app/companion_pendant/epaper/expression_state.h`
- `app/companion_pendant/epaper/expression_state.c`
- `app/companion_pendant/epaper/README.md`
- `tools/verify_expression_signal_guard.py`
- `docs/validation/companion-screen-expression-signal-guard.json`
- `docs/validation/companion-screen-expression-catalog.json`
- `docs/validation/companion-screen-firmware-expression-state.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`

Validation commands:
- `python .\tools\verify_expression_signal_guard.py`
- `python .\tools\verify_expression_catalog_contract.py`
- `python .\tools\verify_expression_firmware_state.py`
- `python .\tools\verify_expression_wba_portability.py`

### 28. Expression duplicate refresh suppression

- ID: `expression_duplicate_refresh_suppression`
- Status: `PASS`
- Summary: Repeated signals, including equivalent status notifications after control events, are suppressed when they resolve to the current visible ExpressionV1 face.
- WBA impact: WBA should preserve duplicate suppression in the portable state model while replacing only scheduler and panel transport code.

Evidence:
- `app/companion_pendant/epaper/expression_state.h`
- `app/companion_pendant/epaper/expression_state.c`
- `tools/verify_expression_journeys.py`
- `docs/validation/companion-screen-firmware-expression-state.json`
- `docs/validation/companion-screen-expression-journeys.json`

Validation commands:
- `python .\tools\verify_expression_firmware_state.py`
- `python .\tools\verify_expression_journeys.py`
- `python .\tools\verify_display_queue_static.py`

### 29. Expression transient auto recovery

- ID: `expression_transient_auto_recovery`
- Status: `PASS`
- Summary: Transient ExpressionV1 faces recover to idle through a portable elapsed-time tick while recording, low-battery, error, idle, and sleepy remain stable.
- WBA impact: WBA should feed elapsed time from its own scheduler into the same portable state tick API without changing expression names or priorities.

Evidence:
- `app/companion_pendant/epaper/expression_state.h`
- `app/companion_pendant/epaper/expression_state.c`
- `tools/verify_expression_journeys.py`
- `docs/validation/companion-screen-firmware-expression-state.json`
- `docs/validation/companion-screen-expression-journeys.json`

Validation commands:
- `python .\tools\verify_expression_firmware_state.py`
- `python .\tools\verify_expression_journeys.py`
- `python .\tools\verify_expression_wba_portability.py`

### 30. WB55 expression tick scheduler

- ID: `wb55_expression_tick_scheduler`
- Status: `PASS`
- Summary: WB55 uses a single-shot HW_TS timer to wake the display task and feed elapsed time into the portable expression tick API.
- WBA impact: WBA should replace HW_TS/HAL_GetTick with its own scheduler while preserving the same portable tick and enqueue behavior.

Evidence:
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c`
- `app/companion_pendant/epaper/expression_state.h`
- `app/companion_pendant/epaper/expression_state.c`
- `docs/companion_screen_expression_system.md`
- `docs/validation/companion-screen-firmware-expression-state.json`

Validation commands:
- `python .\tools\verify_display_queue_static.py`
- `python .\tools\verify_expression_firmware_state.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 31. WB55 settings expression hint

- ID: `wb55_settings_expression_hint`
- Status: `PASS`
- Summary: WB55 SettingsV1 writes enqueue sleepy/recovery expression hints without hiding recording, low-battery, or error faces.
- WBA impact: WBA must map SettingsV1 quiet-hours/display-off writes through the same settings sleepy signal and preserve the stable-state guard.

Evidence:
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c`
- `app/companion_pendant/epaper/expression_state.h`
- `app/companion_pendant/epaper/expression_state.c`
- `docs/validation/companion-screen-firmware-expression-state.json`
- `docs/validation/companion-screen-expression-journeys.json`

Validation commands:
- `python .\tools\verify_expression_firmware_state.py`
- `python .\tools\verify_expression_journeys.py`
- `python .\tools\verify_display_queue_static.py`

### 32. WB55 device status expression hint

- ID: `wb55_device_status_expression_hint`
- Status: `PASS`
- Summary: WB55 DeviceStatusV1 publishes can feed fault, active-audio, and disconnected mode signals into the portable expression mapper after display scheduling is ready.
- WBA impact: WBA device-status adapters must feed DeviceStatusV1 active_mode/fault_bitmap through the same portable expression mapper after the display scheduler exists.

Evidence:
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c`
- `app/companion_pendant/epaper/expression_events.h`
- `app/companion_pendant/epaper/expression_events.c`
- `docs/validation/companion-screen-device-status-expression-hook.json`

Validation commands:
- `python .\tools\verify_expression_device_status_hook.py`
- `python .\tools\verify_expression_event_bridge.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 33. WB55 interaction status expression hint

- ID: `wb55_interaction_status_expression_hint`
- Status: `PASS`
- Summary: WB55 MeetingStatusV1, SpeakerStatusV1, and WakeWordStatusV1 publishes can feed interaction signals into portable expression mappers after display scheduling is ready.
- WBA impact: WBA interaction-status adapters must feed MeetingStatusV1, SpeakerStatusV1, and WakeWordStatusV1 through the same portable expression mapper family after the display scheduler exists.

Evidence:
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c`
- `app/companion_pendant/epaper/expression_events.h`
- `app/companion_pendant/epaper/expression_events.c`
- `docs/validation/companion-screen-interaction-status-expression-hook.json`

Validation commands:
- `python .\tools\verify_expression_interaction_status_hook.py`
- `python .\tools\verify_expression_event_bridge.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 34. WB55 battery expression hint

- ID: `wb55_battery_expression_hint`
- Status: `PASS`
- Summary: WB55 BatteryChargeV1 publishes can feed low-battery and recovered samples into the portable expression bridge after display scheduling is ready.
- WBA impact: WBA battery adapters must feed BatteryChargeV1 samples through the same low-battery/recovery bridge after the display scheduler exists.

Evidence:
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c`
- `app/companion_pendant/epaper/expression_state.h`
- `app/companion_pendant/epaper/expression_state.c`
- `app/companion_pendant/epaper/expression_events.h`
- `app/companion_pendant/epaper/expression_events.c`
- `docs/validation/companion-screen-battery-expression-hook.json`

Validation commands:
- `python .\tools\verify_expression_battery_hook.py`
- `python .\tools\verify_expression_event_bridge.py`
- `python .\tools\verify_expression_firmware_state.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 35. Battery recovery expression guard

- ID: `battery_recovery_expression_guard`
- Status: `PASS`
- Summary: Recovered battery samples clear only a visible low-battery expression and use hysteresis so near-threshold samples do not flicker the face.
- WBA impact: WBA battery adapters must preserve COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED and the state guard that clears only low_battery.

Evidence:
- `app/companion_pendant/epaper/expression_state.h`
- `app/companion_pendant/epaper/expression_state.c`
- `app/companion_pendant/epaper/expression_events.h`
- `app/companion_pendant/epaper/expression_events.c`
- `app/companion_pendant/epaper/expression_policy.py`
- `tools/verify_expression_battery_hook.py`
- `tools/verify_expression_journeys.py`
- `docs/validation/companion-screen-battery-expression-hook.json`
- `docs/validation/companion-screen-expression-journeys.json`
- `docs/validation/companion-screen-firmware-expression-state.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`

Validation commands:
- `python .\tools\verify_expression_battery_hook.py`
- `python .\tools\verify_expression_journeys.py`
- `python .\tools\verify_expression_firmware_state.py`
- `python .\tools\verify_expression_event_bridge.py`
- `python .\tools\verify_expression_policy.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 36. Recording FSM state expression hook

- ID: `recording_state_expression_hook`
- Status: `PASS`
- Summary: Portable recording FSM state readback maps active, stopping, transfer, canceled, and error-recovery states into existing ExpressionV1 faces without adding platform dependencies.
- WBA impact: WBA recording adapters should feed numeric recording FSM state through comp_epaper_expression_signal_from_recording_state() and keep recording headers/platform glue outside the e-paper module.

Evidence:
- `app/companion_pendant/epaper/expression_events.h`
- `app/companion_pendant/epaper/expression_events.c`
- `app/companion_pendant/epaper/expression_policy.py`
- `app/companion_pendant/recording/recording_fsm.h`
- `tools/verify_expression_recording_state_hook.py`
- `docs/validation/companion-screen-recording-state-expression-hook.json`
- `docs/validation/companion-screen-expression-policy.json`
- `docs/validation/companion-screen-expression-event-bridge.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `docs/ble_gatt_contract.md`

Validation commands:
- `python .\tools\verify_expression_recording_state_hook.py`
- `python .\tools\verify_expression_policy.py`
- `python .\tools\verify_expression_event_bridge.py`
- `python .\tools\verify_expression_wba_portability.py`

### 37. WB55 OTA readiness expression hint

- ID: `wb55_ota_readiness_expression_hint`
- Status: `PASS`
- Summary: WB55 OtaReadinessV1 publishes can feed OTA blocker signals into the portable expression mapper after display scheduling is ready.
- WBA impact: WBA OTA adapters must feed OtaReadinessV1 blocker maps through the same portable expression mapper after the display scheduler exists.

Evidence:
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c`
- `app/companion_pendant/epaper/expression_events.h`
- `app/companion_pendant/epaper/expression_events.c`
- `docs/validation/companion-screen-ota-expression-hook.json`

Validation commands:
- `python .\tools\verify_expression_ota_hook.py`
- `python .\tools\verify_expression_event_bridge.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 38. Diagnostic-event expression bridge

- ID: `diagnostic_event_expression_bridge`
- Status: `PASS`
- Summary: Portable C mapper turns Companion diagnostic events into expression signals and ignores e_paper self loops.
- WBA impact: WBA can feed the same diagnostic event codes into the same expression bridge.

Evidence:
- `app/companion_pendant/epaper/expression_events.h`
- `app/companion_pendant/epaper/expression_events.c`
- `docs/validation/companion-screen-expression-event-bridge.json`

Validation commands:
- `python .\tools\verify_expression_event_bridge.py`
- `python .\tools\verify_display_queue_static.py`

### 39. User journey expression acceptance

- ID: `user_journey_expression_acceptance`
- Status: `PASS`
- Summary: Consecutive wake, recording, meeting, speaker, low-battery, recovery, and error flows preserve product priorities.
- WBA impact: Journey behavior is portable and should be reused unchanged on WBA.

Evidence:
- `tools/verify_expression_journeys.py`
- `tools/render_expression_storyboard.py`
- `docs/validation/companion-screen-expression-journeys.json`
- `docs/validation/companion-screen-expression-storyboard.json`
- `docs/validation/epaper/expression-storyboard.svg`

Validation commands:
- `python .\tools\verify_expression_journeys.py`
- `python .\tools\render_expression_storyboard.py`
- `python .\tools\verify_epaper_assets.py`

### 40. Screen expression demo sequence

- ID: `screen_expression_demo_sequence`
- Status: `PASS`
- Summary: A deterministic no-hardware demo checklist walks wake, recording, speaker, settings, low-battery, error, and transient recovery flows one item at a time.
- WBA impact: WBA ports can reuse the same no-hardware demo order before replacing WB55 transport with WBA target glue and real panel evidence.

Evidence:
- `tools/verify_expression_demo_sequence.py`
- `docs/validation/companion-screen-expression-demo-sequence.json`
- `docs/validation/companion-screen-expression-demo-sequence.md`
- `docs/validation/companion-screen-expression-journeys.json`
- `docs/validation/companion-screen-expression-storyboard.json`
- `docs/validation/epaper/expression-storyboard.svg`
- `docs/companion_screen_expression_system.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_demo_sequence.py`
- `python .\tools\verify_expression_journeys.py`
- `python .\tools\render_expression_storyboard.py`

### 41. Screen expression demo panel handoff

- ID: `screen_expression_demo_panel_handoff`
- Status: `PASS`
- Summary: The no-hardware demo checklist is mapped onto WB55, WBA55, and WBA65 real-panel evidence sessions, with manual visual gaps explicit.
- WBA impact: WBA ports reuse the same demo handoff order and must keep manual_visual_required_faces explicit until target real BLE/visual evidence covers every demo face.

Evidence:
- `tools/verify_expression_demo_panel_handoff.py`
- `docs/validation/companion-screen-expression-demo-panel-handoff.json`
- `docs/validation/companion-screen-expression-demo-panel-handoff.md`
- `docs/validation/companion-screen-expression-demo-sequence.json`
- `docs/validation/companion-screen-real-ble-bench.json`
- `docs/validation/companion-screen-panel-hardware-session.json`
- `docs/validation/companion-screen-panel-hardware-acceptance-plan.json`
- `docs/companion_screen_expression_system.md`
- `app/companion_pendant/epaper/README.md`
- `docs/stm32wba_migration_rules.md`

Validation commands:
- `python .\tools\verify_expression_demo_panel_handoff.py`
- `python .\tools\verify_expression_demo_sequence.py`
- `python .\tools\verify_expression_real_ble_screen_bench.py`
- `python .\tools\verify_expression_panel_hardware_session.py`
- `python .\tools\verify_expression_panel_hardware_acceptance_plan.py`

### 42. Screen acceptance runner

- ID: `screen_acceptance_runner`
- Status: `PASS`
- Summary: The aggregate runner reads the screen acceptance index, deduplicates validation commands, preserves the deferred hardware gate, and writes per-item command status.
- WBA impact: WBA branches can reuse the same runner to prove the portable screen suite before adding target-specific hardware evidence.

Evidence:
- `tools/run_expression_acceptance.py`
- `tools/verify_expression_acceptance_runner.py`
- `tools/render_expression_acceptance_report.py`
- `docs/validation/companion-screen-acceptance-runner.json`
- `docs/validation/companion-screen-acceptance-report.md`
- `docs/validation/companion-screen-acceptance-index.json`
- `docs/companion_screen_expression_system.md`
- `docs/bringup_steps.md`

Validation commands:
- `python .\tools\verify_expression_acceptance_runner.py`
- `python .\tools\render_expression_acceptance_report.py`
- `python .\tools\run_expression_acceptance.py --dry-run --skip-build --output .\.cache\validation\companion-screen-acceptance-dry-run.json`

### 43. Screen feature roadmap

- ID: `screen_feature_roadmap`
- Status: `PASS`
- Summary: The screen roadmap groups every detailed acceptance item into product-facing capabilities and keeps the remaining WB55 human touch/visual review explicit.
- WBA impact: WBA work can use the same feature roadmap to see which portable capabilities must stay green before target-specific panel parity is claimed.

Evidence:
- `tools/verify_expression_feature_roadmap.py`
- `docs/validation/companion-screen-feature-roadmap.json`
- `docs/validation/companion-screen-acceptance-index.json`
- `docs/companion_screen_expression_system.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_feature_roadmap.py`
- `python .\tools\verify_expression_acceptance_index.py`

### 44. Screen feature checklist

- ID: `screen_feature_checklist`
- Status: `PASS`
- Summary: A compact generated checklist shows the current one-by-one acceptance focus, next gate, and missing panel facts.
- WBA impact: WBA ports can use the same generated checklist to keep current focus, next gate, and target-specific missing facts visible during parity work.

Evidence:
- `tools/render_expression_feature_checklist.py`
- `docs/validation/companion-screen-feature-checklist.json`
- `docs/validation/companion-screen-feature-checklist.md`
- `docs/validation/companion-screen-feature-roadmap.json`
- `docs/validation/companion-screen-acceptance-index.json`
- `docs/validation/companion-screen-panel-driver-readiness.json`
- `docs/companion_screen_expression_system.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\render_expression_feature_checklist.py`
- `python .\tools\verify_expression_feature_roadmap.py`
- `python .\tools\verify_expression_acceptance_index.py`
- `python .\tools\verify_expression_panel_driver_readiness.py`

### 45. WBA pre-port gate

- ID: `wba_pre_port_gate`
- Status: `PASS`
- Summary: Portable screen files and the WBA pre-port contract are guarded against WB55 HAL, STM32_WPAN, CPU2/FUS/IPCC/HSEM, pins, peripheral instances, and renderer visual/layout drift.
- WBA impact: WBA55 is the conservative baseline; WBA65 may add resources only after preserving the machine-readable portable screen contract.

Evidence:
- `docs/stm32wba_migration_rules.md`
- `docs/validation/companion-screen-wba-port-contract.json`
- `docs/validation/companion-screen-expression-visual-contract.json`
- `docs/validation/companion-screen-expression-layout-contract.json`
- `tools/verify_expression_wba_portability.py`

Validation commands:
- `python .\tools\verify_expression_wba_portability.py`
- `python .\tools\verify_expression_visual_contract.py`
- `python .\tools\verify_expression_layout_contract.py`
- `git diff --name-only -- third_party\STM32CubeWB third_party\STM32CubeWBA`

### 46. WBA LSE/RTC/BLE sleep clock contract

- ID: `wba_lse_clock_contract`
- Status: `PASS`
- Summary: WBA55/WBA65 production boards default to an assembled 32.768 kHz LSE crystal for BLE sleep timing, RTC continuity, timed wake-up, and low-power behavior; any no-LSE variant requires explicit radio-clock, accuracy, and power evidence before real WBA parity can be claimed.
- WBA impact: WBA hardware parity must prove LSE startup, RTC continuity across sleep, BLE advertising/connection through sleep, and timed wake-up on the selected WBA55/WBA65 board, or record an explicit no-LSE radio-clock/power exception.

Evidence:
- `tools/verify_expression_wba_lse_clock_contract.py`
- `docs/validation/companion-screen-wba-lse-clock-contract.json`
- `docs/stm32wba_migration_rules.md`
- `docs/validation/companion-screen-wba-port-contract.json`
- `docs/validation/companion-screen-wba-real-parity-gate.json`

Validation commands:
- `python .\tools\verify_expression_wba_lse_clock_contract.py`
- `python .\tools\verify_expression_wba_portability.py`
- `python .\tools\verify_expression_wba_real_parity_gate.py`

### 47. WBA CubeWBA dependency preflight

- ID: `wba_cube_dependency_preflight`
- Status: `PASS`
- Summary: The WBA pre-port dependency fixture records that STM32CubeWB is present, STM32CubeWBA is not yet present in this workspace, and WBA parity must stay behind DRAFT_PRE_PORT until a separate CubeWBA project and build wrapper exist.
- WBA impact: WBA55/WBA65 migration now has an explicit dependency gate before CubeWBA IOC/project, build wrapper, BLE service registration, scheduler hook, or panel evidence can be treated as parity work.

Evidence:
- `tools/verify_expression_wba_cube_dependency_preflight.py`
- `docs/validation/companion-screen-wba-cube-dependency-preflight.json`
- `docs/validation/companion-workspace-submodule-policy.json`
- `docs/validation/companion-screen-wba-port-contract.json`
- `docs/validation/companion-screen-wba55-port-scaffold.json`
- `docs/stm32wba_migration_rules.md`
- `docs/companion_screen_expression_system.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_wba_cube_dependency_preflight.py`
- `python .\tools\verify_workspace_submodule_policy.py`
- `python .\tools\verify_expression_wba_portability.py`
- `python .\tools\init_expression_wba_port_scaffold.py --self-test`
- `git diff --name-only -- third_party\STM32CubeWB third_party\STM32CubeWBA`

### 48. WBA port scaffold

- ID: `wba_port_scaffold`
- Status: `PASS`
- Summary: The WBA55 pre-port scaffold lists the first CubeWBA dependency preflight, CubeWBA project, build wrapper, WBA adapters, WBA panel target/GATT/scheduler/external-assets scaffolds, visual/layout invariants, real BLE bench, and panel evidence record required before parity can be claimed.
- WBA impact: Future WBA branches can start from a target-specific checklist while keeping WBA55 as the safe baseline and WBA65 as an explicitly expanded target.

Evidence:
- `tools/init_expression_wba_port_scaffold.py`
- `tools/verify_expression_wba_cube_dependency_preflight.py`
- `tools/verify_expression_panel_target_stm32wba.py`
- `tools/verify_expression_screen_scheduler_stm32wba.py`
- `tools/verify_expression_screen_gatt_stm32wba.py`
- `tools/verify_expression_screen_assets_stm32wba.py`
- `app/companion_pendant/epaper/panel_target_stm32wba.h`
- `app/companion_pendant/epaper/panel_target_stm32wba.c`
- `app/companion_pendant/epaper/screen_scheduler_stm32wba.h`
- `app/companion_pendant/epaper/screen_scheduler_stm32wba.c`
- `app/companion_pendant/epaper/screen_gatt_stm32wba.h`
- `app/companion_pendant/epaper/screen_gatt_stm32wba.c`
- `app/companion_pendant/epaper/screen_assets_stm32wba.h`
- `app/companion_pendant/epaper/screen_assets_stm32wba.c`
- `docs/validation/companion-screen-wba55-port-scaffold.json`
- `docs/validation/companion-screen-wba-port-contract.json`
- `docs/validation/companion-screen-wba-cube-dependency-preflight.json`
- `docs/validation/companion-screen-panel-target-stm32wba.json`
- `docs/validation/companion-screen-scheduler-stm32wba.json`
- `docs/validation/companion-screen-gatt-stm32wba.json`
- `docs/validation/companion-screen-assets-stm32wba.json`
- `docs/validation/companion-screen-expression-visual-contract.json`
- `docs/validation/companion-screen-expression-layout-contract.json`
- `docs/stm32wba_migration_rules.md`
- `docs/companion_screen_expression_system.md`

Validation commands:
- `python .\tools\init_expression_wba_port_scaffold.py`
- `python .\tools\init_expression_wba_port_scaffold.py --self-test`
- `python .\tools\verify_expression_wba_cube_dependency_preflight.py`
- `python .\tools\verify_expression_panel_target_stm32wba.py`
- `python .\tools\verify_expression_screen_scheduler_stm32wba.py`
- `python .\tools\verify_expression_screen_gatt_stm32wba.py`
- `python .\tools\verify_expression_screen_assets_stm32wba.py`
- `python .\tools\verify_expression_wba_portability.py`
- `python .\tools\verify_expression_visual_contract.py`
- `python .\tools\verify_expression_layout_contract.py`

### 49. WBA panel target adapter scaffold

- ID: `wba_panel_target_adapter_scaffold`
- Status: `PASS`
- Summary: The WBA55/WBA65 target-named panel adapter scaffold exists as dry-run code outside the WB55 build and without WB55 SPI2 pin facts.
- WBA impact: WBA55/WBA65 can now start from a real target-named file boundary while real transport remains behind target evidence and the WB55 build stays unchanged.

Evidence:
- `app/companion_pendant/epaper/panel_target_stm32wba.h`
- `app/companion_pendant/epaper/panel_target_stm32wba.c`
- `tools/verify_expression_panel_target_stm32wba.py`
- `docs/validation/companion-screen-panel-target-stm32wba.json`
- `docs/validation/companion-screen-wba-port-contract.json`
- `docs/validation/companion-screen-wba55-port-scaffold.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_panel_target_stm32wba.py`
- `python .\tools\verify_expression_wba_portability.py`
- `python .\tools\init_expression_wba_port_scaffold.py --self-test`
- `python .\tools\verify_expression_panel_gate.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 50. WBA refresh intent contract

- ID: `wba_refresh_intent_contract`
- Status: `PASS`
- Summary: The WBA55/WBA65 pre-port contract keeps refresh_mode and 16-bit dirty rectangles in the portable display request, then maps PARTIAL_INTERACTIVE, MAINTENANCE, and FULL to concrete controller waveforms only inside panel_target_stm32wba.*.
- WBA impact: WBA55/WBA65 ports may tune waveform/profile mapping per controller, but must not rewrite portable queue, dirty-rect, scene/player, menu touch, or pet-expression logic.

Evidence:
- `app/companion_pendant/epaper/display_queue.h`
- `app/companion_pendant/epaper/panel_adapter.h`
- `app/companion_pendant/epaper/panel_target_stm32wba.h`
- `app/companion_pendant/epaper/panel_target_stm32wba.c`
- `tools/verify_expression_panel_target_stm32wba.py`
- `tools/verify_expression_wba_portability.py`
- `docs/validation/companion-screen-panel-target-stm32wba.json`
- `docs/validation/companion-screen-wba-port-contract.json`
- `docs/companion_screen_project_plan.md`
- `docs/stm32wba_migration_rules.md`

Validation commands:
- `python .\tools\verify_expression_panel_target_stm32wba.py`
- `python .\tools\verify_expression_wba_portability.py`
- `python .\tools\verify_screen_refresh_feel_contract.py`

### 51. WBA display scheduler scaffold

- ID: `wba_display_scheduler_scaffold`
- Status: `PASS`
- Summary: The WBA55/WBA65 display scheduler/timer scaffold exists as callback-only code outside the WB55 build and without WB55 UTIL_SEQ/HW_TS details.
- WBA impact: WBA55/WBA65 can wire CubeWBA scheduler/timer APIs behind this callback boundary while preserving the display drain and transient expression recovery contracts.

Evidence:
- `app/companion_pendant/epaper/screen_scheduler_stm32wba.h`
- `app/companion_pendant/epaper/screen_scheduler_stm32wba.c`
- `tools/verify_expression_screen_scheduler_stm32wba.py`
- `docs/validation/companion-screen-scheduler-stm32wba.json`
- `docs/validation/companion-screen-display-drain-contract.json`
- `docs/validation/companion-screen-wba-port-contract.json`
- `docs/validation/companion-screen-wba55-port-scaffold.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_screen_scheduler_stm32wba.py`
- `python .\tools\verify_expression_display_drain.py`
- `python .\tools\verify_expression_wba_portability.py`
- `python .\tools\init_expression_wba_port_scaffold.py --self-test`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 52. WBA screen GATT scaffold

- ID: `wba_screen_gatt_scaffold`
- Status: `PASS`
- Summary: The WBA55/WBA65 screen GATT scaffold exists as target-named code outside the WB55 build and preserves CardWriteV1, CardStatusV1, SettingsV1, settings_sleepy_screen_status, and screen_expression_status before CubeWBA service registration is added.
- WBA impact: WBA55/WBA65 can wire CubeWBA BLE service registration behind this boundary while keeping WB55 STM32_WPAN and companion_gatt_stm32wb details out of the WBA scaffold.

Evidence:
- `app/companion_pendant/epaper/screen_gatt_stm32wba.h`
- `app/companion_pendant/epaper/screen_gatt_stm32wba.c`
- `tools/verify_expression_screen_gatt_stm32wba.py`
- `docs/validation/companion-screen-gatt-stm32wba.json`
- `docs/ble_gatt_contract.md`
- `docs/validation/companion-screen-real-ble-bench.json`
- `docs/validation/companion-screen-expression-host-status-sequence.json`
- `docs/validation/companion-screen-wba-port-contract.json`
- `docs/validation/companion-screen-wba55-port-scaffold.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_screen_gatt_stm32wba.py`
- `python .\tools\verify_companion_gatt_static.py`
- `python .\tools\verify_expression_real_ble_screen_bench.py`
- `python .\tools\verify_expression_host_status_sequence.py`
- `python .\tools\verify_expression_wba_portability.py`
- `python .\tools\init_expression_wba_port_scaffold.py --self-test`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 53. WBA screen-assets scaffold

- ID: `wba_screen_assets_scaffold`
- Status: `PASS`
- Summary: The WBA55/WBA65 screen-assets scaffold binds a target-owned logical external-NOR reader to the portable asset store, rejects out-of-range partition reads, and keeps physical storage facts and activation out of the WB55 build and portable resource code.
- WBA impact: WBA55/WBA65 can choose a target-specific storage peripheral and inactive-pack strategy without changing the portable CEMP/resource reader contract or consuming normal UI assets from constrained internal flash.

Evidence:
- `app/companion_pendant/epaper/screen_assets_stm32wba.h`
- `app/companion_pendant/epaper/screen_assets_stm32wba.c`
- `tools/verify_expression_screen_assets_stm32wba.py`
- `docs/validation/companion-screen-assets-stm32wba.json`
- `docs/validation/companion-screen-wba-port-contract.json`
- `docs/validation/companion-screen-wba55-port-scaffold.json`
- `docs/companion_resource_memory_policy.md`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_screen_assets_stm32wba.py`
- `python .\tools\verify_screen_resource_architecture.py`
- `python .\tools\verify_expression_wba_portability.py`
- `python .\tools\init_expression_wba_port_scaffold.py --self-test`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 54. WBA pet behavior user-data scaffold

- ID: `wba_pet_behavior_user_data_scaffold`
- Status: `PASS`
- Summary: The WBA55/WBA65 pet-behavior user-data scaffold persists comp_pet_behavior_memory_t through callback-only logical slots with CRC records, sequence selection, low-frequency commit gating, and explicit privacy erase, and it passes Cortex-M33 ARM GCC object compilation while keeping physical storage facts out of portable pet behavior.
- WBA impact: WBA55/WBA65 can choose the real user-data partition, storage peripheral, erase geometry, and wear policy later; this scaffold preserves the portable behavior memory and OTA/privacy boundaries without claiming real WBA storage parity.

Evidence:
- `app/companion_pendant/epaper/pet_behavior_user_data_stm32wba.h`
- `app/companion_pendant/epaper/pet_behavior_user_data_stm32wba.c`
- `tools/verify_pet_behavior_user_data_stm32wba.py`
- `docs/validation/companion-screen-pet-behavior-user-data-stm32wba.json`
- `docs/validation/companion-screen-wba-port-contract.json`
- `docs/companion_resource_memory_policy.md`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/pet_behavior.h`

Validation commands:
- `python .\tools\verify_pet_behavior_user_data_stm32wba.py`
- `python .\tools\verify_expression_wba_portability.py`
- `python .\tools\verify_expression_wba_real_parity_gate.py`

### 55. Target capability profile

- ID: `target_capability_profile`
- Status: `PASS`
- Summary: WB55, WBA55, and WBA65 screen capability boundaries are captured so WBA55 remains the shared safe baseline and WBA65 expansion requires explicit capability flags.
- WBA impact: WBA55 is the conservative baseline for shared queue/payload/protocol limits; WBA65 may add target-specific resources only behind capability flags while preserving WBA55-safe behavior.

Evidence:
- `tools/verify_expression_target_capabilities.py`
- `docs/validation/companion-screen-target-capabilities.json`
- `docs/validation/companion-screen-wba-port-contract.json`
- `docs/validation/companion-screen-wba55-port-scaffold.json`
- `app/companion_pendant/epaper/display_queue.h`
- `app/companion_pendant/epaper/panel_adapter.h`
- `docs/stm32wba_migration_rules.md`
- `docs/companion_screen_expression_system.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_target_capabilities.py`
- `python .\tools\verify_expression_wba_portability.py`
- `python .\tools\init_expression_wba_port_scaffold.py --self-test`
- `python .\tools\verify_display_queue_static.py`
- `python .\tools\verify_expression_display_drain.py`
- `git diff --name-only -- third_party\STM32CubeWB third_party\STM32CubeWBA`

### 56. Devboard IOC screen preflight

- ID: `devboard_ioc_screen_preflight`
- Status: `PASS`
- Summary: The user-provided STM32.ioc is captured in the WB55 devboard IOC, preserving SPI2/I2C3/SAI1 board facts while keeping the product IOC separate for later target work.
- WBA impact: WBA ports must create a separate CubeWBA IOC/project and keep board pins/peripheral instances in target files instead of copying WB55 devboard pin facts into portable screen code.

Evidence:
- `tools/verify_devboard_ioc_import.py`
- `docs/validation/companion-devboard-ioc-import.json`
- `cubeide/Companion_Nucleo_WB55RG/Companion_Nucleo_WB55RG.ioc`
- `Companion_Pendant.ioc`
- `cubeide/Companion_Nucleo_WB55RG_Bringup/README.md`
- `docs/bringup_steps.md`
- `docs/codex_development_workflow.md`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`

Validation commands:
- `python .\tools\verify_devboard_ioc_import.py`
- `python .\tools\verify_expression_target_capabilities.py`
- `python .\tools\verify_expression_panel_gate.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 57. Panel wiring preflight

- ID: `panel_wiring_preflight`
- Status: `PASS`
- Summary: The WB55 devboard IOC exposes the SPI2 e-paper transport candidate at PA9/PC1/PC2/PA6 while controller and DC/RST/BUSY facts remain under the real-panel hardware gate.
- WBA impact: WBA55/WBA65 must use a target-specific CubeWBA IOC/project and *_stm32wba.* panel adapter; WB55 SPI2 pins are devboard facts, not portable constants.

Evidence:
- `tools/verify_expression_panel_wiring_preflight.py`
- `docs/validation/companion-screen-panel-wiring-preflight.json`
- `docs/validation/companion-devboard-ioc-import.json`
- `docs/validation/companion-screen-panel-hardware-gate.json`
- `docs/validation/companion-screen-panel-hardware-acceptance-plan.json`
- `cubeide/Companion_Nucleo_WB55RG/Companion_Nucleo_WB55RG.ioc`
- `cubeide/Companion_Nucleo_WB55RG_Bringup/README.md`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_panel_wiring_preflight.py`
- `python .\tools\verify_devboard_ioc_import.py`
- `python .\tools\verify_expression_panel_gate.py`
- `python .\tools\verify_expression_panel_hardware_acceptance_plan.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 58. Panel evidence scaffold wiring prefill

- ID: `panel_evidence_scaffold_wiring_prefill`
- Status: `PASS`
- Summary: The WB55 real-panel evidence scaffold imports the verified SPI2 wiring preflight while leaving controller, DC/RST/BUSY, timing, visual, BLE, diagnostics, and adapter facts as TODOs.
- WBA impact: WBA55/WBA65 scaffolds keep transport pins target-specific; WB55 SPI2 prefill is evidence convenience only, not a portable WBA pin assumption.

Evidence:
- `tools/init_expression_panel_evidence_record.py`
- `tools/verify_expression_panel_evidence_record.py`
- `tools/verify_expression_panel_wiring_preflight.py`
- `docs/validation/companion-screen-panel-evidence-record-scaffold.json`
- `docs/validation/companion-screen-panel-evidence-record-validator.json`
- `docs/validation/companion-screen-panel-wiring-preflight.json`
- `docs/validation/companion-screen-panel-evidence-template.json`
- `docs/companion_screen_expression_system.md`
- `docs/bringup_steps.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\init_expression_panel_evidence_record.py`
- `python .\tools\verify_expression_panel_evidence_record.py --self-test`
- `python .\tools\verify_expression_panel_wiring_preflight.py`
- `python .\tools\verify_epaper_assets.py`

### 59. Panel hardware session scaffold

- ID: `panel_hardware_session_scaffold`
- Status: `PASS`
- Summary: The WB55/WBA real-panel hardware session layout is fixed as target-specific roots, required artifacts, hardware-lock commands, diagnostics, visual evidence, and record validation.
- WBA impact: WBA55/WBA65 sessions reuse the same evidence structure with target-specific roots and *_stm32wba.* adapters, but must not inherit WB55 SPI2 pin facts.

Evidence:
- `tools/verify_expression_panel_hardware_session.py`
- `docs/validation/companion-screen-panel-hardware-session.json`
- `docs/validation/companion-screen-panel-hardware-acceptance-plan.json`
- `docs/validation/companion-screen-panel-hardware-gate.json`
- `docs/validation/companion-screen-panel-evidence-record-scaffold.json`
- `docs/validation/companion-screen-panel-evidence-record-validator.json`
- `docs/validation/companion-screen-panel-wiring-preflight.json`
- `docs/companion_screen_expression_system.md`
- `docs/bringup_steps.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_panel_hardware_session.py`
- `python .\tools\verify_expression_panel_hardware_acceptance_plan.py`
- `python .\tools\verify_expression_panel_hardware_facts.py --self-test`
- `python .\tools\verify_expression_panel_evidence_record.py --self-test`
- `python .\tools\verify_expression_wba_portability.py`

### 60. Panel session directory preflight

- ID: `panel_session_directory_preflight`
- Status: `PASS`
- Summary: A concrete generated real-panel session directory can be checked before hardware evidence is filled, its DRAFT_UNFILLED record is still rejected by the final real-panel validator, and any local operator packet must match the current renderer with quoted hardware locks and partial-failure evidence.
- WBA impact: WBA55/WBA65 concrete sessions use the same directory preflight with target-specific roots, target-specific operator packets, partial-failure evidence, and no WB55 SPI2 pin facts in WBA records.

Evidence:
- `tools/verify_expression_panel_session_directory.py`
- `tools/init_expression_panel_evidence_record.py`
- `tools/render_expression_panel_bringup_packet.py`
- `tools/verify_expression_panel_hardware_facts.py`
- `tools/verify_expression_panel_evidence_record.py`
- `docs/validation/companion-screen-panel-session-directory-preflight.json`
- `docs/validation/companion-screen-panel-hardware-session.json`
- `docs/validation/companion-screen-panel-hardware-gate.json`
- `docs/companion_screen_expression_system.md`
- `docs/bringup_steps.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_panel_session_directory.py --self-test`
- `python .\tools\render_expression_panel_bringup_packet.py --self-test`
- `python .\tools\verify_expression_panel_hardware_session.py`
- `python .\tools\verify_expression_panel_hardware_facts.py --self-test`
- `python .\tools\verify_expression_panel_evidence_record.py --self-test`

### 61. Panel hardware facts intake

- ID: `panel_hardware_facts_intake`
- Status: `PASS`
- Summary: Controller, DC/RST/BUSY, power, voltage, and driver timing facts have a target-specific intake file that can reach READY_FOR_DRIVER_FACTS without claiming real refresh.
- WBA impact: WBA55/WBA65 use the same intake schema with target-specific pin maps; READY_FOR_DRIVER_FACTS still requires separate WBA target adapter evidence before parity is claimed.

Evidence:
- `tools/verify_expression_panel_hardware_facts.py`
- `docs/validation/companion-screen-panel-hardware-facts-intake.json`
- `docs/validation/companion-screen-panel-hardware-gate.json`
- `docs/validation/companion-screen-panel-evidence-template.json`
- `docs/validation/companion-screen-panel-session-directory-preflight.json`
- `docs/companion_screen_expression_system.md`
- `docs/bringup_steps.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_panel_hardware_facts.py`
- `python .\tools\verify_expression_panel_hardware_facts.py --self-test`
- `python .\tools\verify_expression_panel_gate.py`

### 62. Panel hardware facts worksheet

- ID: `panel_hardware_facts_worksheet`
- Status: `PASS`
- Summary: A generated JSON/Markdown worksheet turns missing panel readiness fields into a fillable operator table before driver work starts.
- WBA impact: WBA55/WBA65 can render the same worksheet from target-specific facts so WBA driver work starts from explicit missing fields rather than copied WB55 assumptions.

Evidence:
- `tools/render_expression_panel_facts_worksheet.py`
- `docs/validation/companion-screen-panel-facts-worksheet.json`
- `docs/validation/companion-screen-panel-facts-worksheet.md`
- `docs/validation/companion-screen-panel-driver-readiness.json`
- `docs/validation/companion-screen-panel-hardware-facts-intake.json`
- `docs/companion_screen_expression_system.md`
- `docs/bringup_steps.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\render_expression_panel_facts_worksheet.py`
- `python .\tools\render_expression_panel_facts_worksheet.py --self-test`
- `python .\tools\verify_expression_panel_driver_readiness.py`
- `python .\tools\verify_expression_panel_hardware_facts.py --self-test`

### 63. Panel bring-up operator packet

- ID: `panel_bringup_operator_packet`
- Status: `PASS`
- Summary: A generated JSON/Markdown packet combines the WB55 session root, missing facts, readiness gate, commands, and evidence artifacts for the next real-panel bring-up.
- WBA impact: WBA55/WBA65 must generate separate operator packets from their own session facts instead of reusing WB55 SPI/DC/RST/BUSY evidence.

Evidence:
- `tools/render_expression_panel_bringup_packet.py`
- `docs/validation/companion-screen-panel-bringup-operator-packet.json`
- `docs/validation/companion-screen-panel-bringup-operator-packet.md`
- `docs/validation/companion-screen-panel-facts-worksheet.json`
- `docs/validation/companion-screen-panel-driver-readiness.json`
- `docs/validation/companion-screen-panel-hardware-session.json`
- `docs/validation/companion-screen-panel-hardware-acceptance-plan.json`
- `docs/companion_screen_expression_system.md`
- `docs/bringup_steps.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\render_expression_panel_bringup_packet.py`
- `python .\tools\render_expression_panel_bringup_packet.py --self-test`
- `python .\tools\render_expression_panel_facts_worksheet.py --self-test`
- `python .\tools\verify_expression_panel_driver_readiness.py --self-test`
- `python .\tools\verify_expression_panel_hardware_session.py`

### 64. Panel driver readiness report

- ID: `panel_driver_readiness_report`
- Status: `PASS`
- Summary: A target facts file reports BLOCKED_ON_HARDWARE_FACTS until controller, DC/RST/BUSY, power, voltage, timing, and refresh sequence facts are ready for driver implementation.
- WBA impact: WBA55/WBA65 driver work must reach READY_FOR_DRIVER_IMPLEMENTATION from target-specific facts rather than inheriting WB55 SPI2 pin evidence.

Evidence:
- `tools/verify_expression_panel_driver_readiness.py`
- `tools/verify_expression_panel_hardware_facts.py`
- `docs/validation/companion-screen-panel-driver-readiness.json`
- `docs/validation/companion-screen-panel-hardware-facts-intake.json`
- `docs/validation/companion-screen-panel-hardware-gate.json`
- `docs/validation/companion-screen-panel-session-directory-preflight.json`
- `docs/companion_screen_expression_system.md`
- `docs/bringup_steps.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_panel_driver_readiness.py`
- `python .\tools\verify_expression_panel_driver_readiness.py --self-test`
- `python .\tools\verify_expression_panel_hardware_facts.py --self-test`
- `python .\tools\verify_expression_panel_gate.py`

### 65. Panel hardware facts bridge

- ID: `panel_hardware_facts_bridge`
- Status: `PASS`
- Summary: READY_FOR_DRIVER_FACTS can be imported into panel-evidence-record.json while preserving DRAFT_UNFILLED status and final-validator rejection until BLE, diagnostics, visual, and portability evidence exist.
- WBA impact: WBA55/WBA65 use the same bridge only after target-specific READY_FOR_DRIVER_FACTS are filled, and the bridge still cannot claim WBA panel parity.

Evidence:
- `tools/apply_expression_panel_hardware_facts.py`
- `tools/verify_expression_panel_hardware_facts.py`
- `tools/verify_expression_panel_evidence_record.py`
- `docs/validation/companion-screen-panel-hardware-facts-bridge.json`
- `docs/validation/companion-screen-panel-hardware-facts-intake.json`
- `docs/validation/companion-screen-panel-evidence-record-validator.json`
- `docs/validation/companion-screen-panel-hardware-gate.json`
- `docs/companion_screen_expression_system.md`
- `docs/bringup_steps.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\apply_expression_panel_hardware_facts.py --self-test`
- `python .\tools\verify_expression_panel_hardware_facts.py --self-test`
- `python .\tools\verify_expression_panel_evidence_record.py --self-test`
- `python .\tools\verify_expression_panel_gate.py`

### 66. Panel adapter target-ops boundary

- ID: `panel_target_ops_boundary`
- Status: `PASS`
- Summary: The portable panel adapter dispatches through a target-owned refresh callback so real WB55/WBA transport can be added without moving board code into portable screen files.
- WBA impact: WBA55/WBA65 should add target-specific refresh transport through the same callback field while leaving ExpressionV1, display_queue, and CardStatusV1 unchanged.

Evidence:
- `app/companion_pendant/epaper/panel_adapter.h`
- `app/companion_pendant/epaper/panel_adapter.c`
- `docs/validation/companion-screen-panel-adapter-boundary.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `tools/verify_expression_panel_adapter_boundary.py`

Validation commands:
- `python .\tools\verify_expression_panel_adapter_boundary.py`
- `python .\tools\verify_display_queue_static.py`
- `python .\tools\verify_expression_wba_portability.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 67. WB55 panel target adapter scaffold

- ID: `wb55_panel_target_adapter_scaffold`
- Status: `PASS`
- Summary: WB55 now initializes the portable panel adapter through a target-named panel_target_stm32wb scaffold, which still delegates to dry-run until real controller, pin, and timing evidence exists.
- WBA impact: WBA55/WBA65 should add a separate *_stm32wba.* target adapter with the same dry-run-to-real-evidence promotion path instead of changing portable panel files.

Evidence:
- `app/companion_pendant/epaper/panel_target_stm32wb.h`
- `app/companion_pendant/epaper/panel_target_stm32wb.c`
- `app/companion_pendant/epaper/panel_adapter.h`
- `app/companion_pendant/epaper/panel_adapter.c`
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c`
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile`
- `docs/validation/companion-screen-panel-target-stm32wb.json`
- `docs/validation/companion-screen-panel-hardware-gate.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `tools/verify_expression_panel_target_stm32wb.py`

Validation commands:
- `python .\tools\verify_expression_panel_target_stm32wb.py`
- `python .\tools\verify_expression_panel_gate.py`
- `python .\tools\verify_expression_panel_adapter_boundary.py`
- `python .\tools\verify_display_queue_static.py`
- `python .\tools\verify_expression_wba_portability.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 68. Panel adapter behavior matrix

- ID: `panel_adapter_behavior_matrix`
- Status: `PASS`
- Summary: Dry-run, controller-unknown, missing-callback, callback OK/BUSY/deferred/error, and request identity behavior are fixed as a no-hardware contract for future panel drivers.
- WBA impact: WBA panel drivers must preserve the same callback result, CardStatusV1 render-state/error, and request identity behavior while replacing only transport.

Evidence:
- `app/companion_pendant/epaper/panel_adapter.h`
- `app/companion_pendant/epaper/panel_adapter.c`
- `docs/validation/companion-screen-panel-adapter-behavior.json`
- `docs/validation/companion-screen-panel-adapter-boundary.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `tools/verify_expression_panel_adapter_behavior.py`

Validation commands:
- `python .\tools\verify_expression_panel_adapter_behavior.py`
- `python .\tools\verify_expression_panel_adapter_boundary.py`
- `python .\tools\verify_expression_status_observability.py`
- `python .\tools\verify_expression_wba_portability.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 69. Panel adapter telemetry snapshot

- ID: `panel_adapter_telemetry_snapshot`
- Status: `PASS`
- Summary: The portable panel adapter exposes a stats snapshot for attempts, rendered/deferred/error counts, configuration state, and last result without adding target dependencies.
- WBA impact: WBA panel drivers should preserve the same panel adapter stats snapshot so real-panel attempts, deferrals, busy responses, and errors can be diagnosed without changing CardStatusV1.

Evidence:
- `app/companion_pendant/epaper/panel_adapter.h`
- `app/companion_pendant/epaper/panel_adapter.c`
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c`
- `docs/validation/companion-screen-panel-adapter-telemetry.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `tools/verify_expression_panel_adapter_telemetry.py`

Validation commands:
- `python .\tools\verify_expression_panel_adapter_telemetry.py`
- `python .\tools\verify_expression_panel_adapter_behavior.py`
- `python .\tools\verify_expression_panel_adapter_boundary.py`
- `python .\tools\verify_expression_status_observability.py`
- `python .\tools\verify_expression_wba_portability.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 70. Screen runtime snapshot

- ID: `screen_runtime_snapshot`
- Status: `PASS`
- Summary: The portable screen runtime aggregates expression state, display queue, and panel adapter telemetry snapshots so WB55 and future WBA display tasks observe the same runtime contract.
- WBA impact: WBA display tasks should collect runtime status through the same aggregate snapshot instead of reading private expression, queue, or panel fields directly.

Evidence:
- `app/companion_pendant/epaper/screen_runtime.h`
- `app/companion_pendant/epaper/screen_runtime.c`
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c`
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile`
- `docs/validation/companion-screen-runtime-snapshot.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`
- `tools/verify_expression_screen_runtime_snapshot.py`

Validation commands:
- `python .\tools\verify_expression_screen_runtime_snapshot.py`
- `python .\tools\verify_expression_state_telemetry.py`
- `python .\tools\verify_display_queue_telemetry.py`
- `python .\tools\verify_expression_panel_adapter_telemetry.py`
- `python .\tools\verify_display_queue_static.py`
- `python .\tools\verify_expression_wba_portability.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 71. Screen runtime diagnostics

- ID: `screen_runtime_diagnostics`
- Status: `PASS`
- Summary: WB55 records an e_paper.runtime_snapshot diagnostic event from the aggregate screen runtime snapshot without changing CardStatusV1.
- WBA impact: WBA display tasks must preserve the e_paper.runtime_snapshot event id, payload packing, and warning rule while replacing only scheduler/BLE/panel glue.

Evidence:
- `app/companion_pendant/diag_log/diag_log_events.h`
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c`
- `app/companion_pendant/epaper/screen_runtime.h`
- `app/companion_pendant/epaper/screen_runtime.c`
- `docs/validation/companion-screen-runtime-diagnostics.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`
- `docs/ble_gatt_contract.md`
- `tools/verify_expression_screen_runtime_diagnostics.py`

Validation commands:
- `python .\tools\verify_expression_screen_runtime_diagnostics.py`
- `python .\tools\verify_expression_screen_runtime_snapshot.py`
- `python .\tools\verify_expression_status_observability.py`
- `python .\tools\verify_display_queue_static.py`
- `python .\tools\verify_expression_wba_portability.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`

### 72. Screen runtime diagnostic decode

- ID: `screen_runtime_diagnostic_decode`
- Status: `PASS`
- Summary: The host diagnostic decoder expands e_paper.runtime_snapshot packed args into expression, display-queue, and panel decoded_args fields for bring-up logs.
- WBA impact: WBA bring-up logs should reuse the same decoded_args schema for e_paper.runtime_snapshot instead of inventing target-specific diagnostic parsing.

Evidence:
- `tools/decode_diag_log.py`
- `tools/verify_expression_screen_runtime_diagnostic_decode.py`
- `docs/validation/companion-screen-runtime-diagnostic-decode.json`
- `docs/validation/companion-screen-runtime-diagnostics.json`
- `app/companion_pendant/diag_log/diag_log_events.h`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_screen_runtime_diagnostic_decode.py`
- `python .\tools\verify_expression_screen_runtime_diagnostics.py`
- `python .\tools\decode_diag_log.py --self-test`
- `python .\tools\verify_expression_wba_portability.py`

### 73. Screen runtime diagnostics bundle

- ID: `screen_runtime_diagnostics_bundle`
- Status: `PASS`
- Summary: The no-hardware diagnostics bundle fixture includes e_paper.runtime_snapshot in the bounded tail with decoded_args and epaper runtime summary fields.
- WBA impact: WBA diagnostics bundles should keep e_paper.runtime_snapshot in bounded pulls and preserve decoded_args for host bring-up tooling.

Evidence:
- `tools/collect_companion_diagnostics.ps1`
- `tools/verify_companion_diagnostics_static.py`
- `tools/decode_diag_log.py`
- `docs/validation/companion-diagnostics-fixture/summary.json`
- `docs/validation/companion-diagnostics-fixture/summary.md`
- `docs/validation/companion-diagnostics-fixture/diag_tail_raw.jsonl`
- `docs/validation/companion-diagnostics-fixture/diag_tail_decoded.json`
- `docs/validation/companion-screen-runtime-diagnostic-decode.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `pwsh -NoProfile -File .\tools\collect_companion_diagnostics.ps1 -Fixture`
- `python .\tools\verify_companion_diagnostics_static.py`
- `python .\tools\verify_expression_screen_runtime_diagnostic_decode.py`
- `python .\tools\verify_expression_wba_portability.py`

### 74. Real BLE screen final-status bench

- ID: `real_ble_screen_final_status_bench`
- Status: `PASS`
- Summary: The real BLE bench collects accepted and final CardStatusV1 records for card_write and settings_sleepy_screen_status, and --expect-real-panel requires final rendered/ok before a hardware refresh claim.
- WBA impact: WBA real BLE bench artifacts must keep the same accepted/final CardStatusV1 identity for card writes and SettingsV1-triggered ExpressionV1 updates, then use --expect-real-panel before claiming rendered/ok parity.

Evidence:
- `tools/companion_ble_real_bench.py`
- `tools/verify_expression_real_ble_screen_bench.py`
- `docs/ble_gatt_contract.md`
- `docs/bringup_steps.md`
- `docs/validation/companion-screen-real-ble-bench.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`

Validation commands:
- `python .\tools\verify_expression_real_ble_screen_bench.py`
- `python -m py_compile .\tools\companion_ble_real_bench.py`
- `python .\tools\verify_expression_status_observability.py`
- `python .\tools\verify_expression_wba_portability.py`

### 75. Real BLE ExpressionV1 status sequence contract

- ID: `real_ble_expression_status_sequence_contract`
- Status: `PASS`
- Summary: The real BLE bench artifact carries the contract-only screen_expression_status operation linked to the six-face host status sequence before WB55/WBA panel parity is claimed.
- WBA impact: WBA real BLE artifacts must include screen_expression_status with the same six-face host sequence baseline before using --expect-real-panel to claim rendered/ok parity.

Evidence:
- `tools/companion_ble_real_bench.py`
- `tools/verify_expression_real_ble_screen_bench.py`
- `tools/verify_expression_host_status_sequence.py`
- `docs/validation/companion-screen-real-ble-bench.json`
- `docs/validation/companion-screen-expression-host-status-sequence.json`
- `docs/ble_gatt_contract.md`
- `docs/bringup_steps.md`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`

Validation commands:
- `python .\tools\verify_expression_real_ble_screen_bench.py`
- `python .\tools\verify_expression_host_status_sequence.py`
- `python -m py_compile .\tools\companion_ble_real_bench.py`
- `python .\tools\verify_expression_wba_portability.py`

### 76. Panel hardware evidence template

- ID: `panel_hardware_evidence_template`
- Status: `PASS`
- Summary: The real-panel acceptance template defines the controller, pin map, timing, CardStatus/log/runtime diagnostics, real BLE artifact, visual evidence, and target-adapter facts required before any WB55 or WBA real refresh claim.
- WBA impact: WBA55/WBA65 panel work must fill the same evidence template with a target-specific *_stm32wba.* adapter record before claiming parity.

Evidence:
- `docs/validation/companion-screen-real-ble-bench.json`
- `docs/validation/companion-screen-runtime-diagnostics.json`
- `docs/validation/companion-screen-runtime-diagnostic-decode.json`
- `docs/validation/companion-diagnostics-fixture/summary.json`
- `docs/validation/companion-screen-panel-evidence-template.json`
- `docs/validation/companion-screen-panel-hardware-gate.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `tools/verify_expression_panel_evidence_template.py`

Validation commands:
- `python .\tools\verify_expression_real_ble_screen_bench.py`
- `python .\tools\verify_expression_panel_evidence_template.py`
- `python .\tools\verify_expression_panel_gate.py`
- `python .\tools\verify_expression_screen_runtime_diagnostics.py`
- `python .\tools\verify_expression_screen_runtime_diagnostic_decode.py`
- `python .\tools\verify_companion_diagnostics_static.py`
- `python .\tools\verify_expression_wba_portability.py`

### 77. Panel evidence runtime diagnostics

- ID: `panel_evidence_runtime_diagnostics`
- Status: `PASS`
- Summary: The panel evidence template, scaffold, and validator require e_paper.runtime_snapshot decoded_args with zero panel errors, zero pending display work, and zero dropped display work before a real refresh claim.
- WBA impact: WBA real-panel evidence must include the same decoded runtime snapshot health checks in the filled *_stm32wba.* evidence record.

Evidence:
- `tools/verify_expression_panel_evidence_template.py`
- `tools/verify_expression_panel_evidence_record.py`
- `tools/init_expression_panel_evidence_record.py`
- `docs/validation/companion-screen-panel-evidence-template.json`
- `docs/validation/companion-screen-panel-evidence-record-scaffold.json`
- `docs/validation/companion-screen-panel-evidence-record-validator.json`
- `docs/validation/companion-screen-runtime-diagnostics.json`
- `docs/validation/companion-screen-runtime-diagnostic-decode.json`
- `docs/validation/companion-diagnostics-fixture/summary.json`
- `docs/companion_screen_expression_system.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_panel_evidence_template.py`
- `python .\tools\init_expression_panel_evidence_record.py`
- `python .\tools\verify_expression_panel_evidence_record.py --self-test`
- `python .\tools\verify_expression_screen_runtime_diagnostics.py`
- `python .\tools\verify_expression_screen_runtime_diagnostic_decode.py`
- `python .\tools\verify_companion_diagnostics_static.py`
- `python .\tools\verify_expression_wba_portability.py`

### 78. Panel evidence diagnostics bundle validator

- ID: `panel_evidence_diagnostics_bundle_validator`
- Status: `PASS`
- Summary: Filled real-panel evidence records must point at a diagnostics bundle summary whose epaper.runtime_snapshot_decoded and decoded tail event show zero panel errors, zero pending display work, and zero dropped display work.
- WBA impact: WBA real-panel evidence must attach the same diagnostics bundle summary so a WBA port cannot claim parity without host-decoded screen runtime health.

Evidence:
- `tools/collect_companion_diagnostics.ps1`
- `tools/verify_companion_diagnostics_static.py`
- `tools/verify_expression_panel_evidence_record.py`
- `tools/verify_expression_panel_evidence_template.py`
- `tools/init_expression_panel_evidence_record.py`
- `docs/validation/companion-diagnostics-fixture/summary.json`
- `docs/validation/companion-screen-panel-evidence-template.json`
- `docs/validation/companion-screen-panel-evidence-record-scaffold.json`
- `docs/validation/companion-screen-panel-evidence-record-validator.json`
- `docs/companion_screen_expression_system.md`
- `docs/bringup_steps.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_panel_evidence_template.py`
- `python .\tools\init_expression_panel_evidence_record.py`
- `python .\tools\verify_expression_panel_evidence_record.py --self-test`
- `python .\tools\verify_companion_diagnostics_static.py`
- `python .\tools\verify_expression_wba_portability.py`

### 79. Panel evidence record validator

- ID: `panel_evidence_record_validator`
- Status: `PASS`
- Summary: The real-panel evidence validator rejects missing fields, deferred no-panel status, runtime diagnostic errors, request identity drift, missing visual artifacts, missing screen_expression_status, missing screen_expression_demo_status, and non-target-named adapters before the hardware gate can move.
- WBA impact: WBA panel evidence records must pass the same validator with *_stm32wba.* adapter files before claiming rendered/ok parity.

Evidence:
- `tools/init_expression_panel_evidence_record.py`
- `tools/verify_expression_panel_evidence_record.py`
- `tools/verify_expression_host_status_sequence.py`
- `tools/verify_expression_demo_host_status_sequence.py`
- `docs/validation/companion-screen-panel-evidence-record-scaffold.json`
- `docs/validation/companion-screen-panel-evidence-record-validator.json`
- `docs/validation/companion-screen-panel-evidence-template.json`
- `docs/validation/companion-screen-real-ble-bench.json`
- `docs/validation/companion-screen-expression-host-status-sequence.json`
- `docs/validation/companion-screen-expression-demo-host-status-sequence.json`
- `docs/validation/companion-screen-runtime-diagnostics.json`
- `docs/validation/companion-screen-runtime-diagnostic-decode.json`
- `docs/validation/companion-screen-panel-hardware-gate.json`
- `docs/companion_screen_expression_system.md`
- `docs/bringup_steps.md`
- `docs/stm32wba_migration_rules.md`

Validation commands:
- `python .\tools\init_expression_panel_evidence_record.py`
- `python .\tools\verify_expression_panel_evidence_record.py --self-test`
- `python .\tools\verify_expression_panel_evidence_template.py`
- `python .\tools\verify_expression_screen_runtime_diagnostic_decode.py`
- `python .\tools\verify_expression_host_status_sequence.py`
- `python .\tools\verify_expression_demo_host_status_sequence.py`
- `python .\tools\verify_expression_panel_gate.py`

### 80. Panel evidence real BLE sequence validator

- ID: `panel_evidence_real_ble_sequence_validator`
- Status: `PASS`
- Summary: Filled real-panel evidence records must point at a real BLE artifact that includes both screen_expression_status six-face and screen_expression_demo_status full-demo host sequence baselines as well as rendered/ok hardware statuses.
- WBA impact: WBA real-panel evidence records must reject real BLE artifacts that omit screen_expression_status or screen_expression_demo_status, keeping both host sequence baselines attached to parity evidence.

Evidence:
- `tools/verify_expression_panel_evidence_record.py`
- `tools/verify_expression_real_ble_screen_bench.py`
- `tools/verify_expression_host_status_sequence.py`
- `tools/verify_expression_demo_host_status_sequence.py`
- `docs/validation/companion-screen-panel-evidence-record-validator.json`
- `docs/validation/companion-screen-panel-evidence-template.json`
- `docs/validation/companion-screen-real-ble-bench.json`
- `docs/validation/companion-screen-expression-host-status-sequence.json`
- `docs/validation/companion-screen-expression-demo-host-status-sequence.json`
- `docs/companion_screen_expression_system.md`
- `docs/bringup_steps.md`
- `docs/stm32wba_migration_rules.md`
- `app/companion_pendant/epaper/README.md`

Validation commands:
- `python .\tools\verify_expression_panel_evidence_record.py --self-test`
- `python .\tools\verify_expression_real_ble_screen_bench.py`
- `python .\tools\verify_expression_host_status_sequence.py`
- `python .\tools\verify_expression_demo_host_status_sequence.py`
- `python .\tools\verify_expression_panel_evidence_template.py`
- `python .\tools\verify_expression_wba_portability.py`

### 81. Panel hardware acceptance plan

- ID: `panel_hardware_acceptance_plan`
- Status: `PASS`
- Summary: WB55 real-panel refresh is accepted; the same target-specific evidence plan keeps WBA55/WBA65 hardware parity deferred until each target supplies its own verified record.
- WBA impact: WBA55/WBA65 must use the same plan with *_stm32wba.* adapters, WBA portability checks, and target evidence records before claiming real-panel parity.

Evidence:
- `tools/verify_expression_panel_hardware_acceptance_plan.py`
- `tools/verify_expression_panel_hardware_session.py`
- `docs/validation/companion-screen-panel-hardware-acceptance-plan.json`
- `docs/validation/companion-screen-panel-hardware-session.json`
- `docs/validation/companion-screen-panel-hardware-gate.json`
- `docs/validation/companion-screen-panel-evidence-template.json`
- `docs/validation/companion-screen-panel-evidence-record-validator.json`
- `docs/validation/companion-screen-panel-wiring-preflight.json`
- `docs/validation/companion-screen-real-ble-bench.json`
- `docs/validation/companion-screen-runtime-diagnostics.json`
- `docs/validation/companion-screen-runtime-diagnostic-decode.json`
- `docs/validation/companion-screen-panel-target-stm32wb.json`
- `docs/validation/companion-screen-wba-port-contract.json`
- `docs/validation/companion-screen-wba55-port-scaffold.json`
- `docs/companion_screen_expression_system.md`
- `docs/bringup_steps.md`
- `docs/stm32wba_migration_rules.md`

Validation commands:
- `python .\tools\verify_expression_panel_hardware_acceptance_plan.py`
- `python .\tools\verify_expression_panel_hardware_session.py`
- `python .\tools\verify_expression_panel_gate.py`
- `python .\tools\verify_expression_panel_target_stm32wb.py`
- `python .\tools\verify_expression_panel_evidence_record.py --self-test`
- `python .\tools\verify_expression_panel_wiring_preflight.py`
- `python .\tools\verify_expression_real_ble_screen_bench.py`
- `python .\tools\verify_expression_screen_runtime_diagnostics.py`
- `python .\tools\verify_expression_screen_runtime_diagnostic_decode.py`
- `python .\tools\verify_expression_wba_portability.py`

### 82. WB55 screen build matrix

- ID: `wb55_screen_build_matrix`
- Status: `PASS`
- Summary: The WB55 screen firmware keeps default dry-run, explicit SSD1681 real-panel, and ScreenAssetProvision external ui_assets builds compilable, so machine pre-acceptance cannot pass on a path that only links one transport or skips the current CEMP provision image.
- WBA impact: WBA branches must add an analogous target build wrapper before claiming WBA parity; this WB55 matrix prevents portable code from silently depending on one target transport.

Evidence:
- `tools/verify_wb55_screen_build_matrix.py`
- `tools/build_nucleo_bringup.ps1`
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile`
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c`
- `cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c`
- `app/companion_pendant/epaper/display_queue.h`
- `app/companion_pendant/epaper/display_queue.c`
- `app/companion_pendant/epaper/panel_target_stm32wb.c`
- `app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c`
- `docs/validation/companion-screen-wb55-build-matrix.json`
- `docs/validation/companion-screen-pre-acceptance-health.json`
- `.cache/validation/wb55-build-matrix/default-build.log`
- `.cache/validation/wb55-build-matrix/ssd1681-build.log`
- `.cache/validation/wb55-build-matrix/screen-asset-provision-build.log`

Validation commands:
- `python .\tools\verify_wb55_screen_build_matrix.py`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -Force`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -EpaperSsd1681Bringup -Force`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -ScreenAssetProvision -Force`
- `python .\tools\verify_companion_screen_pre_acceptance_health.py`

### 83. WB55 real e-paper panel refresh

- ID: `wb55_real_panel_refresh`
- Status: `PASS`
- Summary: The physical GDEY0154D67-T03 completed SSD1681 full, partial, and fast refreshes on WB55; operator observations confirm a visible black update and upright non-mirrored orientation.
- WBA impact: WBA panel work must preserve the proven portable queue, policy, presentation, and asset contracts while replacing only target backends.

Evidence:
- `app/companion_pendant/epaper/panel_adapter.h`
- `app/companion_pendant/epaper/panel_adapter.c`
- `app/companion_pendant/epaper/panel_target_stm32wb.h`
- `app/companion_pendant/epaper/panel_target_stm32wb.c`
- `app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c`
- `docs/companion_screen_expression_system.md`
- `docs/validation/companion-screen-panel-hardware-gate.json`
- `docs/validation/companion-screen-wb55-ssd1681-bringup.json`
- `docs/validation/companion-screen-ssd1681-partial-refresh-wb55.json`
- `docs/validation/companion-screen-touch-ft6336-wb55.json`

Validation commands:
- `python .\tools\verify_expression_panel_gate.py`
- `python .\tools\verify_expression_panel_target_stm32wb.py`
- `python .\tools\verify_epaper_refresh_policy.py`
- `python .\tools\verify_epaper_fast_maintenance_runtime.py`
- `python .\tools\verify_touch_ft6336.py`

### 84. WB55 runtime serial capture preflight

- ID: `wb55_runtime_serial_capture_preflight`
- Status: `PASS`
- Summary: The rev52 runtime recheck serial path is statically verified before any COM port is opened: capture_nucleo_serial.ps1 requires -Execute and -WorkflowLockHeld, the locked runner captures provision and normal boots for 25 s into stable raw/summary filenames, and the log verifier consumes those exact artifacts.
- WBA impact: WBA runtime evidence must add an analogous target-specific locked capture preflight before any WBA real-panel parity claim.

Evidence:
- `tools/render_wb55_runtime_hardware_action_card.py`
- `tools/verify_wb55_runtime_flash_preflight.py`
- `tools/verify_wb55_runtime_serial_capture_preflight.py`
- `tools/capture_nucleo_serial.ps1`
- `tools/run_wb55_screen_runtime_recheck.ps1`
- `tools/verify_wb55_screen_runtime_recheck_logs.py`
- `docs/validation/companion-screen-wb55-runtime-hardware-action-card.json`
- `docs/validation/companion-screen-wb55-runtime-hardware-action-card.md`
- `docs/validation/companion-screen-wb55-runtime-flash-preflight.json`
- `docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json`
- `.cache/validation/rev52-runtime-current/runtime-recheck-run.json`

Validation commands:
- `python .\tools\render_wb55_runtime_hardware_action_card.py`
- `python .\tools\verify_wb55_runtime_flash_preflight.py`
- `python .\tools\verify_wb55_runtime_serial_capture_preflight.py`
- `pwsh -NoProfile -File .\tools\run_wb55_screen_runtime_recheck.ps1 -CheckOnly`

### 85. WB55 rev52 provision/normal runtime recheck

- ID: `wb55_rev52_runtime_recheck`
- Status: `DEFERRED_HARDWARE`
- Summary: The current rev52 CEMP resource pack is machine-prepared but not yet first-hand runtime-proven on WB55: the locked hardware action card must flash provision, capture provision logs, restore normal firmware, capture normal logs, verify the SCR-17 release ledger and coherent_generation marker path, then the log verifier and promotion gate may advance pre-acceptance.
- WBA impact: WBA ports must add the same target-specific provision/normal runtime recheck gate before WBA real-panel parity can move from scaffold to hardware evidence.

Evidence:
- `tools/run_wb55_screen_runtime_recheck.ps1`
- `tools/verify_wb55_screen_runtime_recheck_logs.py`
- `tools/promote_wb55_screen_runtime_recheck.py`
- `tools/render_wb55_runtime_hardware_action_card.py`
- `tools/verify_wb55_runtime_flash_preflight.py`
- `tools/verify_wb55_runtime_serial_capture_preflight.py`
- `tools/verify_screen_generation_release_ledger.py`
- `docs/validation/companion-screen-wb55-runtime-recheck-runner.json`
- `docs/validation/companion-screen-wb55-runtime-recheck-logs.json`
- `docs/validation/companion-screen-wb55-runtime-promotion.json`
- `docs/validation/companion-screen-wb55-runtime-hardware-action-card.json`
- `docs/validation/companion-screen-wb55-runtime-hardware-action-card.md`
- `docs/validation/companion-screen-wb55-runtime-flash-preflight.json`
- `docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json`
- `docs/validation/companion-screen-generation-release-ledger.json`
- `.cache/validation/rev52-runtime-current/runtime-recheck-run.json`

Validation commands:
- `python .\tools\verify_wb55_screen_runtime_recheck_runner.py`
- `python .\tools\render_wb55_runtime_hardware_action_card.py`
- `python .\tools\verify_wb55_runtime_flash_preflight.py`
- `python .\tools\verify_wb55_runtime_serial_capture_preflight.py`
- `python .\tools\verify_screen_generation_release_ledger.py`
- `pwsh -NoProfile -File .\tools\run_wb55_screen_runtime_recheck.ps1 -CheckOnly`
- `python .\tools\verify_wb55_screen_runtime_recheck_logs.py`
- `python .\tools\promote_wb55_screen_runtime_recheck.py`

Missing hardware facts:
- rev52 provision serial raw/summary logs
- rev52 normal serial raw/summary logs
- locked Companion-WB55 hardware run with normal_firmware_restored=true

### 86. WB55 touch navigation and fast-refresh visual acceptance

- ID: `wb55_touch_visual_acceptance`
- Status: `PENDING_HUMAN`
- Summary: Machine checks, physical contact/release, revision 52 candidate generation hygiene, and the last runtime-proven external_flash mount are covered by the pre-acceptance health gate; the operator still needs to confirm daily tap/swipe pet reactions, anywhere 3 s menu entry with a 650 ms tease, continuous vertical drag, press-cue plus target-arrival partial refreshes, left-edge return, language switching, and that 0xCF maintenance is perceived as a single quiet flash.
- WBA impact: Repeat the same focused touch and visual acceptance after the WBA backend is available; portable gesture semantics must not change.

Evidence:
- `tools/render_wb55_touch_visual_acceptance_packet.py`
- `tools/render_wb55_runtime_hardware_action_card.py`
- `tools/verify_wb55_runtime_flash_preflight.py`
- `tools/verify_wb55_runtime_serial_capture_preflight.py`
- `tools/render_wb55_touch_visual_review_template.py`
- `tools/verify_wb55_touch_visual_review_record.py`
- `tools/verify_companion_screen_pre_acceptance_health.py`
- `tools/verify_display_queue_generation_hygiene.py`
- `tools/verify_screen_generation_release_ledger.py`
- `docs/validation/companion-screen-pre-acceptance-health.json`
- `docs/validation/companion-screen-display-queue-generation-hygiene.json`
- `docs/validation/companion-screen-generation-release-ledger.json`
- `docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.json`
- `docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.md`
- `docs/validation/companion-screen-wb55-runtime-hardware-action-card.json`
- `docs/validation/companion-screen-wb55-runtime-hardware-action-card.md`
- `docs/validation/companion-screen-wb55-runtime-flash-preflight.json`
- `docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json`
- `docs/validation/companion-screen-wb55-touch-visual-review-template.json`
- `docs/validation/companion-screen-wb55-touch-visual-review-template.md`
- `docs/validation/companion-screen-wb55-touch-visual-review-record.json`
- `docs/companion_screen_project_plan.md`
- `docs/validation/companion-screen-presentation-wb55.json`
- `docs/validation/companion-screen-bilingual-menu-wb55.json`
- `docs/validation/companion-screen-touch-ft6336-wb55.json`
- `docs/validation/companion-screen-ssd1681-partial-refresh-wb55.json`
- `.cache/validation/nucleo-serial-20260712-184908/nucleo-serial-summary.json`
- `.cache/validation/nucleo-serial-20260712-184908/nucleo-serial-raw.log`
- `.cache/validation/nucleo-serial-20260712-185021/nucleo-serial-summary.json`
- `.cache/validation/nucleo-serial-20260712-185021/nucleo-serial-raw.log`

Validation commands:
- `python .\tools\render_wb55_touch_visual_acceptance_packet.py`
- `python .\tools\render_wb55_runtime_hardware_action_card.py`
- `python .\tools\verify_wb55_runtime_flash_preflight.py`
- `python .\tools\verify_wb55_runtime_serial_capture_preflight.py`
- `python .\tools\render_wb55_touch_visual_review_template.py`
- `python .\tools\verify_wb55_touch_visual_review_record.py`
- `python .\tools\verify_companion_screen_pre_acceptance_health.py`
- `python .\tools\verify_display_queue_generation_hygiene.py`
- `python .\tools\verify_screen_generation_release_ledger.py`
- `python .\tools\verify_screen_menu_assets.py`
- `python .\tools\verify_screen_presentation.py`
- `python .\tools\verify_touch_ft6336.py`
- `python .\tools\verify_epaper_fast_maintenance_runtime.py`

### 87. Active goal completion audit

- ID: `companion_screen_goal_audit`
- Status: `PENDING_HUMAN`
- Summary: The full screen goal is machine-audited: WB55 wiring, refresh, rev52 resource generation hygiene, WB55 dry-run/SSD1681 build matrix, last-proven external resources, touch IC health, external Flash policy, pre-acceptance health, and WBA pre-port boundaries are tracked; the open requirements are rev52 provision/normal runtime recheck, screen refresh/touch machine health on the current resource pack, daily pet/menu human feel, and future WBA real-panel parity.
- WBA impact: WBA real-panel parity remains a future hardware/project gate; the audit prevents closing the shared goal on WB55-only evidence.

Evidence:
- `tools/verify_companion_screen_goal_audit.py`
- `tools/verify_companion_screen_pre_acceptance_health.py`
- `docs/validation/companion-screen-goal-audit.json`
- `docs/validation/companion-screen-goal-audit.md`
- `docs/validation/companion-screen-pre-acceptance-health.json`
- `docs/validation/companion-screen-display-queue-generation-hygiene.json`
- `docs/validation/companion-screen-generation-release-ledger.json`
- `docs/validation/companion-screen-wb55-build-matrix.json`
- `docs/validation/companion-screen-bilingual-menu-wb55.json`
- `docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.json`
- `docs/validation/companion-screen-wb55-touch-visual-review-template.json`
- `docs/validation/companion-screen-wb55-touch-visual-review-record.json`
- `docs/validation/companion-screen-wb55-runtime-hardware-action-card.json`
- `docs/validation/companion-screen-wb55-runtime-flash-preflight.json`
- `docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json`
- `docs/validation/companion-screen-wba-port-contract.json`
- `docs/validation/companion-screen-wba-lse-clock-contract.json`

Validation commands:
- `python .\tools\verify_companion_screen_goal_audit.py`
- `python .\tools\verify_companion_screen_pre_acceptance_health.py`
- `python .\tools\verify_display_queue_generation_hygiene.py`
- `python .\tools\verify_screen_generation_release_ledger.py`
- `python .\tools\verify_wb55_screen_build_matrix.py`
- `python .\tools\render_wb55_touch_visual_acceptance_packet.py`
- `python .\tools\render_wb55_runtime_hardware_action_card.py`
- `python .\tools\verify_wb55_runtime_flash_preflight.py`
- `python .\tools\verify_wb55_runtime_serial_capture_preflight.py`
- `python .\tools\render_wb55_touch_visual_review_template.py`
- `python .\tools\verify_wb55_touch_visual_review_record.py`
- `python .\tools\verify_screen_menu_assets.py`
- `python .\tools\verify_screen_resource_architecture.py`
- `python .\tools\verify_expression_wba_portability.py`
- `python .\tools\verify_expression_wba_lse_clock_contract.py`
