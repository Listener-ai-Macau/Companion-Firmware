# Companion Panel Hardware Facts Worksheet

This worksheet is generated. Update it with `python .\tools\render_expression_panel_facts_worksheet.py --write`.

## Current Status

- Target: `WB55`
- Facts status: `DRAFT_UNFILLED`
- Driver readiness: `BLOCKED_ON_HARDWARE_FACTS`
- Missing fields: `15`
- Known transport: `SPI2 SCK=PA9 MOSI=PC1 MISO=PC2 CS=PA6`

## Fill These Fields

| Status | Field | Current value | Accepted values | Prompt |
|---|---|---|---|---|
| `missing` | `panel_identity.controller_model` | `TODO_CONTROLLER_MODEL` | Non-placeholder string, for example UC8151D. | Controller model from module docs or silkscreen. |
| `missing` | `panel_identity.panel_module_or_label` | `TODO_PANEL_MODULE_OR_LABEL` | Non-placeholder string. | Panel module name or label used for bench traceability. |
| `missing` | `panel_identity.datasheet_revision` | `TODO_DATASHEET_REVISION` | Non-placeholder string. | Datasheet revision used for timing/command sequence. |
| `missing` | `panel_identity.waveform_lut_source` | `TODO_WAVEFORM_LUT_SOURCE` | Non-placeholder string, for example controller OTP. | Waveform LUT source. |
| `missing` | `target_pin_map.dc_pin` | `TODO_DC_PIN` | STM32 pin like PB0. | STM32 GPIO wired to panel DC. |
| `missing` | `target_pin_map.rst_pin` | `TODO_RST_PIN` | STM32 pin like PB1. | STM32 GPIO wired to panel RST. |
| `missing` | `target_pin_map.busy_pin` | `TODO_BUSY_PIN` | STM32 pin like PB2. | STM32 GPIO wired to panel BUSY. |
| `missing` | `target_pin_map.power_enable_pin` | `TODO_POWER_ENABLE_PIN_OR_NOT_PRESENT` | STM32 pin or not_present. | Optional panel power-enable GPIO. |
| `missing` | `target_pin_map.logic_voltage` | `TODO_LOGIC_VOLTAGE` | 1.8V, 3.0V, or 3.3V. | Panel logic voltage. |
| `missing` | `driver_timing.reset_low_ms` | `TODO_RESET_LOW_MS_INTEGER` | Positive integer milliseconds. | Reset low pulse duration from datasheet. |
| `missing` | `driver_timing.reset_high_ms` | `TODO_RESET_HIGH_MS_INTEGER` | Positive integer milliseconds. | Delay after reset release from datasheet. |
| `missing` | `driver_timing.busy_timeout_ms` | `TODO_BUSY_TIMEOUT_MS_INTEGER` | Positive integer milliseconds. | Maximum BUSY wait for full refresh. |
| `missing` | `driver_timing.full_refresh_sequence` | `TODO_FULL_REFRESH_STEP_1` | Non-empty list of named steps. | Full refresh command sequence to implement. |
| `missing` | `driver_timing.partial_refresh_policy` | `TODO_PARTIAL_REFRESH_POLICY` | Non-placeholder string; disabled is allowed until validated. | Initial partial-refresh policy. |
| `missing` | `driver_timing.sleep_or_powerdown_sequence` | `TODO_SLEEP_OR_POWERDOWN_STEP_1` | Non-empty list of named steps. | Sleep or powerdown command sequence after refresh. |

Next step: Fill each missing row in a session panel-hardware-facts.todo.json, then rerun python .\tools\verify_expression_panel_driver_readiness.py --facts <panel-hardware-facts.todo.json> --require-ready.
