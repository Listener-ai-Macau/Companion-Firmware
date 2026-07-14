# Companion Screen Expression Demo Panel Handoff

Status: PASS
Gate snapshot: `wb55_real_panel_refresh` is `DEFERRED_HARDWARE_FTS02_BOOST`
Demo source: `docs/validation/companion-screen-expression-demo-sequence.json`
Real BLE bench source: `docs/validation/companion-screen-real-ble-bench.json`

## Coverage

- Demo steps: 37
- Demo expressions: error, happy, idle, listening, low_battery, recording, sleepy, speaking, sync_complete, thinking
- Real BLE sequence faces: error, idle, low_battery, recording, sleepy, sync_complete
- Manual visual required faces: happy, listening, speaking, thinking
- Manual visual step count: 7

## Step Capture Checklist

| Demo | Step | Event | Face | Result | Capture mode | Fixture |
|---|---:|---|---|---|---|---|
| `wake_recording_sync` | 0 | `wake_word.armed` | `idle` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_idle_2_13in.pbm` |
| `wake_recording_sync` | 1 | `wake_word.detected` | `listening` | `accept` | `manual_visual_required` | `docs/validation/epaper/expression_listening_2_13in.pbm` |
| `wake_recording_sync` | 2 | `recording_fsm.start_request` | `recording` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_recording_2_13in.pbm` |
| `wake_recording_sync` | 3 | `recording_fsm.stop_request` | `thinking` | `accept` | `manual_visual_required` | `docs/validation/epaper/expression_thinking_2_13in.pbm` |
| `wake_recording_sync` | 4 | `recording_fsm.session_finished` | `sync_complete` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_sync_complete_2_13in.pbm` |
| `speaker_prompt_result` | 0 | `speaker.prompt` | `speaking` | `accept` | `manual_visual_required` | `docs/validation/epaper/expression_speaking_2_13in.pbm` |
| `speaker_prompt_result` | 1 | `speaker.result` | `happy` | `accept` | `manual_visual_required` | `docs/validation/epaper/expression_happy_2_13in.pbm` |
| `settings_sleepy_hint` | 0 | `wake_word.armed` | `idle` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_idle_2_13in.pbm` |
| `settings_sleepy_hint` | 1 | `settings.display_off` | `sleepy` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_sleepy_2_13in.pbm` |
| `settings_sleepy_hint` | 2 | `settings.display_on` | `idle` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_idle_2_13in.pbm` |
| `settings_sleepy_hint` | 3 | `recording_fsm.start_request` | `recording` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_recording_2_13in.pbm` |
| `settings_sleepy_hint` | 4 | `settings.display_off` | `recording` | `hold` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_recording_2_13in.pbm` |
| `settings_sleepy_hint` | 5 | `recording_fsm.cancel_request` | `idle` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_idle_2_13in.pbm` |
| `settings_sleepy_hint` | 6 | `settings.quiet_hours` | `sleepy` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_sleepy_2_13in.pbm` |
| `recording_low_battery_priority` | 0 | `recording_fsm.start_request` | `recording` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_recording_2_13in.pbm` |
| `recording_low_battery_priority` | 1 | `battery_charging.sample` | `recording` | `hold` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_recording_2_13in.pbm` |
| `recording_low_battery_priority` | 2 | `recording_fsm.stop_request` | `thinking` | `accept` | `manual_visual_required` | `docs/validation/epaper/expression_thinking_2_13in.pbm` |
| `recording_low_battery_priority` | 3 | `battery_charging.sample` | `low_battery` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_low_battery_2_13in.pbm` |
| `battery_recovery_guard` | 0 | `battery_charging.sample` | `low_battery` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_low_battery_2_13in.pbm` |
| `battery_recovery_guard` | 1 | `battery_charging.sample` | `low_battery` | `hold` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_low_battery_2_13in.pbm` |
| `battery_recovery_guard` | 2 | `battery_charging.sample` | `idle` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_idle_2_13in.pbm` |
| `battery_recovery_guard` | 3 | `recording_fsm.start_request` | `recording` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_recording_2_13in.pbm` |
| `battery_recovery_guard` | 4 | `battery_charging.sample` | `recording` | `hold` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_recording_2_13in.pbm` |
| `battery_recovery_guard` | 5 | `errors.fault` | `error` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_error_2_13in.pbm` |
| `battery_recovery_guard` | 6 | `battery_charging.sample` | `error` | `hold` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_error_2_13in.pbm` |
| `battery_recovery_guard` | 7 | `warnings.recovered` | `idle` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_idle_2_13in.pbm` |
| `error_override_recovery` | 0 | `battery_charging.sample` | `low_battery` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_low_battery_2_13in.pbm` |
| `error_override_recovery` | 1 | `errors.fault` | `error` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_error_2_13in.pbm` |
| `error_override_recovery` | 2 | `speaker.prompt` | `error` | `hold` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_error_2_13in.pbm` |
| `error_override_recovery` | 3 | `warnings.recovered` | `idle` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_idle_2_13in.pbm` |
| `transient_auto_recovery` | 0 | `speaker.result` | `happy` | `accept` | `manual_visual_required` | `docs/validation/epaper/expression_happy_2_13in.pbm` |
| `transient_auto_recovery` | 1 | `time.elapsed` | `happy` | `hold` | `manual_visual_required` | `docs/validation/epaper/expression_happy_2_13in.pbm` |
| `transient_auto_recovery` | 2 | `time.elapsed` | `idle` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_idle_2_13in.pbm` |
| `transient_auto_recovery` | 3 | `meeting.finalize` | `sync_complete` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_sync_complete_2_13in.pbm` |
| `transient_auto_recovery` | 4 | `time.elapsed` | `idle` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_idle_2_13in.pbm` |
| `transient_auto_recovery` | 5 | `recording_fsm.start_request` | `recording` | `accept` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_recording_2_13in.pbm` |
| `transient_auto_recovery` | 6 | `time.elapsed` | `recording` | `hold` | `real_ble_sequence_baseline_plus_visual` | `docs/validation/epaper/expression_recording_2_13in.pbm` |

## Target Sessions

| Target | Visual root | BLE lock |
|---|---|---|
| `WB55` | `.cache/validation/companion-real-panel-wb55-<timestamp>/visual/demo-sequence` | `Companion-WB55,BLE-Companion` |
| `WBA55` | `.cache/validation/companion-real-panel-wba55-<timestamp>/visual/demo-sequence` | `Companion-WBA55,BLE-Companion` |
| `WBA65` | `.cache/validation/companion-real-panel-wba65-<timestamp>/visual/demo-sequence` | `Companion-WBA65,BLE-Companion` |
