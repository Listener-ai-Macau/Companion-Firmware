# Companion Panel Bring-up Operator Packet

This packet is generated. Update it with `python .\tools\render_expression_panel_bringup_packet.py --write`.

## Status

- Target: `WB55`
- Session root: `.cache/validation/companion-real-panel-wb55-<timestamp>`
- Gate: `wb55_real_panel_refresh` remains `DEFERRED_HARDWARE`
- Facts status: `DRAFT_UNFILLED`
- Driver readiness: `BLOCKED_ON_HARDWARE_FACTS`
- Missing fields: `15`
- Known transport: `SPI2 SCK=PA9 MOSI=PC1 MISO=PC2 CS=PA6`

## Operator Steps

| # | Step | Completion check |
|---:|---|---|
| 1 | `create_session` | Session contains panel-evidence-record.json, panel-hardware-facts.todo.json, visual/, diagnostics/, and operator-notes.md. |
| 2 | `fill_panel_identity` | Controller, module label, datasheet revision, and LUT source are non-placeholder values. |
| 3 | `fill_wiring_and_power` | DC/RST/BUSY/power-enable/logic-voltage facts are target-specific and do not copy another board. |
| 4 | `fill_driver_timing` | Timing and command sequence facts are traceable to the controller datasheet or module vendor notes. |
| 5 | `prove_driver_readiness` | Readiness reports READY_FOR_DRIVER_IMPLEMENTATION for this session only. |
| 6 | `bridge_facts_into_evidence_record` | panel-evidence-record.json remains DRAFT_UNFILLED and still does not claim real refresh. |
| 7 | `implement_target_driver` | Target driver builds and portable expression/display queue files remain free of SPI/GPIO/BUSY code. |
| 8 | `collect_real_panel_evidence` | Final record passes verify_expression_panel_evidence_record.py with rendered/ok, zero runtime errors, and before/during/after visual evidence. |

## Missing Facts

| Field | Current value | Accepted values |
|---|---|---|
| `panel_identity.controller_model` | `TODO_CONTROLLER_MODEL` | Non-placeholder string, for example UC8151D. |
| `panel_identity.panel_module_or_label` | `TODO_PANEL_MODULE_OR_LABEL` | Non-placeholder string. |
| `panel_identity.datasheet_revision` | `TODO_DATASHEET_REVISION` | Non-placeholder string. |
| `panel_identity.waveform_lut_source` | `TODO_WAVEFORM_LUT_SOURCE` | Non-placeholder string, for example controller OTP. |
| `target_pin_map.dc_pin` | `TODO_DC_PIN` | STM32 pin like PB0. |
| `target_pin_map.rst_pin` | `TODO_RST_PIN` | STM32 pin like PB1. |
| `target_pin_map.busy_pin` | `TODO_BUSY_PIN` | STM32 pin like PB2. |
| `target_pin_map.power_enable_pin` | `TODO_POWER_ENABLE_PIN_OR_NOT_PRESENT` | STM32 pin or not_present. |
| `target_pin_map.logic_voltage` | `TODO_LOGIC_VOLTAGE` | 1.8V, 3.0V, or 3.3V. |
| `driver_timing.reset_low_ms` | `TODO_RESET_LOW_MS_INTEGER` | Positive integer milliseconds. |
| `driver_timing.reset_high_ms` | `TODO_RESET_HIGH_MS_INTEGER` | Positive integer milliseconds. |
| `driver_timing.busy_timeout_ms` | `TODO_BUSY_TIMEOUT_MS_INTEGER` | Positive integer milliseconds. |
| `driver_timing.full_refresh_sequence` | `TODO_FULL_REFRESH_STEP_1` | Non-empty list of named steps. |
| `driver_timing.partial_refresh_policy` | `TODO_PARTIAL_REFRESH_POLICY` | Non-placeholder string; disabled is allowed until validated. |
| `driver_timing.sleep_or_powerdown_sequence` | `TODO_SLEEP_OR_POWERDOWN_STEP_1` | Non-empty list of named steps. |

## Session Artifacts

| Artifact | Path | Purpose |
|---|---|---|
| `panel_evidence_record` | `.cache/validation/companion-real-panel-wb55-<timestamp>/panel-evidence-record.json` | Final real-panel evidence record; starts DRAFT_UNFILLED and must remain draft until all evidence is present. |
| `hardware_facts` | `.cache/validation/companion-real-panel-wb55-<timestamp>/panel-hardware-facts.todo.json` | Fill controller, wiring, power, voltage, and timing facts before target driver implementation. |
| `facts_worksheet` | `.cache/validation/companion-real-panel-wb55-<timestamp>/panel-facts-worksheet.md` | Operator-facing table of missing driver-readiness fields. |
| `driver_readiness` | `.cache/validation/companion-real-panel-wb55-<timestamp>/panel-driver-readiness.json` | Machine-readable BLOCKED_ON_HARDWARE_FACTS or READY_FOR_DRIVER_IMPLEMENTATION report. |
| `operator_notes` | `.cache/validation/companion-real-panel-wb55-<timestamp>/operator-notes.md` | Record operator action, panel labels, observed refresh result, and deviations. |
| `visual_before` | `.cache/validation/companion-real-panel-wb55-<timestamp>/visual/before_photo.jpg` | Photo before the refresh attempt. |
| `visual_during` | `.cache/validation/companion-real-panel-wb55-<timestamp>/visual/during_refresh_photo_or_video` | Photo or video during the refresh attempt. |
| `visual_after` | `.cache/validation/companion-real-panel-wb55-<timestamp>/visual/after_photo.jpg` | Photo after the refresh attempt; hash goes into panel-evidence-record.json. |
| `real_ble_bench` | `.cache/validation/companion-real-panel-wb55-<timestamp>/companion-ble-real-bench.json` | BLE artifact created with --expect-real-panel and final rendered/ok status; failed runs must preserve operations and partial_operation_count. |
| `diagnostics_summary` | `.cache/validation/companion-real-panel-wb55-<timestamp>/diagnostics/summary.json` | Diagnostics bundle summary with epaper.runtime_snapshot_decoded health, panel_error_count=0, pending display work=0, and dropped display work=0. |

## Command Groups

### session_setup

- `python .\tools\init_expression_panel_evidence_record.py --target WB55 --session-root .cache/validation/companion-real-panel-wb55-<timestamp> --write-session`
- `python .\tools\verify_expression_panel_session_directory.py --session-root .cache/validation/companion-real-panel-wb55-<timestamp> --target WB55`
- `python .\tools\verify_expression_panel_hardware_facts.py --facts .cache/validation/companion-real-panel-wb55-<timestamp>/panel-hardware-facts.todo.json`

### facts_worksheet

- `python .\tools\render_expression_panel_facts_worksheet.py --session-root .cache/validation/companion-real-panel-wb55-<timestamp> --write --json .cache/validation/companion-real-panel-wb55-<timestamp>/panel-facts-worksheet.json --markdown .cache/validation/companion-real-panel-wb55-<timestamp>/panel-facts-worksheet.md`
- `python .\tools\verify_expression_panel_driver_readiness.py --session-root .cache/validation/companion-real-panel-wb55-<timestamp> --output .cache/validation/companion-real-panel-wb55-<timestamp>/panel-driver-readiness.json`

### pre_driver_gate

- `python .\tools\verify_expression_panel_driver_readiness.py --session-root .cache/validation/companion-real-panel-wb55-<timestamp> --require-ready`

### evidence_record_bridge

- `python .\tools\apply_expression_panel_hardware_facts.py --facts .cache/validation/companion-real-panel-wb55-<timestamp>/panel-hardware-facts.todo.json --record .cache/validation/companion-real-panel-wb55-<timestamp>/panel-evidence-record.json --write`

### driver_and_static_checks

- `edit app/companion_pendant/epaper/panel_target_stm32wb.c`
- `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1`
- `python .\tools\verify_expression_panel_adapter_behavior.py`
- `python .\tools\verify_expression_panel_adapter_telemetry.py`

### real_panel_evidence

- `pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource 'Companion-WB55,BLE-Companion' -Purpose "Companion WB55 real e-paper panel operator packet" -Run python .\tools\companion_ble_real_bench.py --name companion --timeout 20 --notify-timeout 10 --screen-final-timeout 30 --expect-real-panel --output .cache/validation/companion-real-panel-wb55-<timestamp>/companion-ble-real-bench.json --json`
- `pwsh -NoProfile -File .\tools\collect_companion_diagnostics.ps1 -OutputDir .cache/validation/companion-real-panel-wb55-<timestamp>/diagnostics`
- `python .\tools\verify_expression_panel_evidence_record.py --record .cache/validation/companion-real-panel-wb55-<timestamp>/panel-evidence-record.json`
- `git diff --name-only -- third_party\STM32CubeWB third_party\STM32CubeWBA`
