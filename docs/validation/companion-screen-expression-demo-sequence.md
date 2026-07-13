# Companion Screen Expression Demo Sequence

Status: PASS
Source journey fixture: `docs/validation/companion-screen-expression-journeys.json`
Storyboard: `docs/validation/epaper/expression-storyboard.svg`

## Demo Order

| Order | Demo | Product check | Final face |
|---:|---|---|---|
| 1 | `wake_recording_sync` | Wake, listen, record, think, and show sync complete in order. | `sync_complete` |
| 2 | `speaker_prompt_result` | Speaker prompt shows speaking, then happy after the result. | `happy` |
| 3 | `settings_sleepy_hint` | Display-off and quiet-hours hints show sleepy without hiding recording. | `sleepy` |
| 4 | `recording_low_battery_priority` | Low battery does not interrupt active recording, then appears after recording stops. | `low_battery` |
| 5 | `battery_recovery_guard` | Battery recovery only clears a visible low-battery face. | `idle` |
| 6 | `error_override_recovery` | Error overrides lower-priority faces and returns to idle after recovery. | `idle` |
| 7 | `transient_auto_recovery` | Transient faces recover to idle while recording remains stable. | `recording` |

## Step Checklist

| Demo | Step | Event | Visible face | Result | Fixture |
|---|---:|---|---|---|---|
| `wake_recording_sync` | 0 | `wake_word.armed` | `idle` | `accept` | `docs/validation/epaper/expression_idle_2_13in.pbm` |
| `wake_recording_sync` | 1 | `wake_word.detected` | `listening` | `accept` | `docs/validation/epaper/expression_listening_2_13in.pbm` |
| `wake_recording_sync` | 2 | `recording_fsm.start_request` | `recording` | `accept` | `docs/validation/epaper/expression_recording_2_13in.pbm` |
| `wake_recording_sync` | 3 | `recording_fsm.stop_request` | `thinking` | `accept` | `docs/validation/epaper/expression_thinking_2_13in.pbm` |
| `wake_recording_sync` | 4 | `recording_fsm.session_finished` | `sync_complete` | `accept` | `docs/validation/epaper/expression_sync_complete_2_13in.pbm` |
| `speaker_prompt_result` | 0 | `speaker.prompt` | `speaking` | `accept` | `docs/validation/epaper/expression_speaking_2_13in.pbm` |
| `speaker_prompt_result` | 1 | `speaker.result` | `happy` | `accept` | `docs/validation/epaper/expression_happy_2_13in.pbm` |
| `settings_sleepy_hint` | 0 | `wake_word.armed` | `idle` | `accept` | `docs/validation/epaper/expression_idle_2_13in.pbm` |
| `settings_sleepy_hint` | 1 | `settings.display_off` | `sleepy` | `accept` | `docs/validation/epaper/expression_sleepy_2_13in.pbm` |
| `settings_sleepy_hint` | 2 | `settings.display_on` | `idle` | `accept` | `docs/validation/epaper/expression_idle_2_13in.pbm` |
| `settings_sleepy_hint` | 3 | `recording_fsm.start_request` | `recording` | `accept` | `docs/validation/epaper/expression_recording_2_13in.pbm` |
| `settings_sleepy_hint` | 4 | `settings.display_off` | `recording` | `hold` | `docs/validation/epaper/expression_recording_2_13in.pbm` |
| `settings_sleepy_hint` | 5 | `recording_fsm.cancel_request` | `idle` | `accept` | `docs/validation/epaper/expression_idle_2_13in.pbm` |
| `settings_sleepy_hint` | 6 | `settings.quiet_hours` | `sleepy` | `accept` | `docs/validation/epaper/expression_sleepy_2_13in.pbm` |
| `recording_low_battery_priority` | 0 | `recording_fsm.start_request` | `recording` | `accept` | `docs/validation/epaper/expression_recording_2_13in.pbm` |
| `recording_low_battery_priority` | 1 | `battery_charging.sample` | `recording` | `hold` | `docs/validation/epaper/expression_recording_2_13in.pbm` |
| `recording_low_battery_priority` | 2 | `recording_fsm.stop_request` | `thinking` | `accept` | `docs/validation/epaper/expression_thinking_2_13in.pbm` |
| `recording_low_battery_priority` | 3 | `battery_charging.sample` | `low_battery` | `accept` | `docs/validation/epaper/expression_low_battery_2_13in.pbm` |
| `battery_recovery_guard` | 0 | `battery_charging.sample` | `low_battery` | `accept` | `docs/validation/epaper/expression_low_battery_2_13in.pbm` |
| `battery_recovery_guard` | 1 | `battery_charging.sample` | `low_battery` | `hold` | `docs/validation/epaper/expression_low_battery_2_13in.pbm` |
| `battery_recovery_guard` | 2 | `battery_charging.sample` | `idle` | `accept` | `docs/validation/epaper/expression_idle_2_13in.pbm` |
| `battery_recovery_guard` | 3 | `recording_fsm.start_request` | `recording` | `accept` | `docs/validation/epaper/expression_recording_2_13in.pbm` |
| `battery_recovery_guard` | 4 | `battery_charging.sample` | `recording` | `hold` | `docs/validation/epaper/expression_recording_2_13in.pbm` |
| `battery_recovery_guard` | 5 | `errors.fault` | `error` | `accept` | `docs/validation/epaper/expression_error_2_13in.pbm` |
| `battery_recovery_guard` | 6 | `battery_charging.sample` | `error` | `hold` | `docs/validation/epaper/expression_error_2_13in.pbm` |
| `battery_recovery_guard` | 7 | `warnings.recovered` | `idle` | `accept` | `docs/validation/epaper/expression_idle_2_13in.pbm` |
| `error_override_recovery` | 0 | `battery_charging.sample` | `low_battery` | `accept` | `docs/validation/epaper/expression_low_battery_2_13in.pbm` |
| `error_override_recovery` | 1 | `errors.fault` | `error` | `accept` | `docs/validation/epaper/expression_error_2_13in.pbm` |
| `error_override_recovery` | 2 | `speaker.prompt` | `error` | `hold` | `docs/validation/epaper/expression_error_2_13in.pbm` |
| `error_override_recovery` | 3 | `warnings.recovered` | `idle` | `accept` | `docs/validation/epaper/expression_idle_2_13in.pbm` |
| `transient_auto_recovery` | 0 | `speaker.result` | `happy` | `accept` | `docs/validation/epaper/expression_happy_2_13in.pbm` |
| `transient_auto_recovery` | 1 | `time.elapsed` | `happy` | `hold` | `docs/validation/epaper/expression_happy_2_13in.pbm` |
| `transient_auto_recovery` | 2 | `time.elapsed` | `idle` | `accept` | `docs/validation/epaper/expression_idle_2_13in.pbm` |
| `transient_auto_recovery` | 3 | `meeting.finalize` | `sync_complete` | `accept` | `docs/validation/epaper/expression_sync_complete_2_13in.pbm` |
| `transient_auto_recovery` | 4 | `time.elapsed` | `idle` | `accept` | `docs/validation/epaper/expression_idle_2_13in.pbm` |
| `transient_auto_recovery` | 5 | `recording_fsm.start_request` | `recording` | `accept` | `docs/validation/epaper/expression_recording_2_13in.pbm` |
| `transient_auto_recovery` | 6 | `time.elapsed` | `recording` | `hold` | `docs/validation/epaper/expression_recording_2_13in.pbm` |

## Coverage

- Demo count: 7
- Step count: 37
- Accepted steps: 29
- Held steps: 8
- Expressions: error, happy, idle, listening, low_battery, recording, sleepy, speaking, sync_complete, thinking
