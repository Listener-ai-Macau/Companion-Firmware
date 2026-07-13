# Companion ExpressionV1 Visual Acceptance Matrix

This matrix is generated. Update it with `python .\tools\render_expression_visual_acceptance_matrix.py --write`.

## Coverage

- Expressions: `10`
- Variants: `1.54in, 2.13in`
- Matrix cells: `20`
- Demo covers all faces: `True`
- Legacy gap faces: `happy, listening, speaking, thinking`
- Real refresh claimed: `False`
- Panel gate: `DEFERRED_HARDWARE`

## Face Matrix

| ID | Face | Fixtures | Host coverage | Signals | Acceptance |
|---:|---|---|---|---|---|
| 0 | `idle` | 1.54in: docs/validation/epaper/expression_idle_1_54in.pbm, 2.13in: docs/validation/epaper/expression_idle_2_13in.pbm | legacy+demo | BOOT_IDLE, WAKE_ARMED, RECORDING_CANCEL, RECOVERY, BATTERY_RECOVERED | hashes=True, density=True, demo=True |
| 1 | `listening` | 1.54in: docs/validation/epaper/expression_listening_1_54in.pbm, 2.13in: docs/validation/epaper/expression_listening_2_13in.pbm | demo | WAKE_DETECTED | hashes=True, density=True, demo=True |
| 2 | `thinking` | 1.54in: docs/validation/epaper/expression_thinking_1_54in.pbm, 2.13in: docs/validation/epaper/expression_thinking_2_13in.pbm | demo | MEETING_STOP, RECORDING_STOP | hashes=True, density=True, demo=True |
| 3 | `speaking` | 1.54in: docs/validation/epaper/expression_speaking_1_54in.pbm, 2.13in: docs/validation/epaper/expression_speaking_2_13in.pbm | demo | SPEAKER_PROMPT | hashes=True, density=True, demo=True |
| 4 | `happy` | 1.54in: docs/validation/epaper/expression_happy_1_54in.pbm, 2.13in: docs/validation/epaper/expression_happy_2_13in.pbm | demo | SPEAKER_RESULT | hashes=True, density=True, demo=True |
| 5 | `sleepy` | 1.54in: docs/validation/epaper/expression_sleepy_1_54in.pbm, 2.13in: docs/validation/epaper/expression_sleepy_2_13in.pbm | legacy+demo | WAKE_DISABLED, SETTINGS_SLEEPY | hashes=True, density=True, demo=True |
| 6 | `recording` | 1.54in: docs/validation/epaper/expression_recording_1_54in.pbm, 2.13in: docs/validation/epaper/expression_recording_2_13in.pbm | legacy+demo | MEETING_START, RECORDING_START | hashes=True, density=True, demo=True |
| 7 | `sync_complete` | 1.54in: docs/validation/epaper/expression_sync_complete_1_54in.pbm, 2.13in: docs/validation/epaper/expression_sync_complete_2_13in.pbm | legacy+demo | MEETING_FINALIZE, RECORDING_FINISHED | hashes=True, density=True, demo=True |
| 8 | `low_battery` | 1.54in: docs/validation/epaper/expression_low_battery_1_54in.pbm, 2.13in: docs/validation/epaper/expression_low_battery_2_13in.pbm | legacy+demo | LOW_BATTERY | hashes=True, density=True, demo=True |
| 9 | `error` | 1.54in: docs/validation/epaper/expression_error_1_54in.pbm, 2.13in: docs/validation/epaper/expression_error_2_13in.pbm | legacy+demo | ERROR | hashes=True, density=True, demo=True |
