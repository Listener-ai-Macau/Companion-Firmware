# Companion ExpressionV1 Host Manifest

This manifest is generated. Update it with `python .\tools\render_expression_host_manifest.py --write`.

## Coverage

- Expressions: `10`
- Signals: `18`
- Demo covers all faces: `True`
- Legacy host sequence faces: `error, idle, low_battery, recording, sleepy, sync_complete`
- Legacy gap faces: `happy, listening, speaking, thinking`

## Host Observability

- Card status: CardStatusV1 accepted/final pairs on expression card slot 1
- Diagnostic arg3: `(expression_id << 16) \| signal_id`
- Request id base: `0xe0000000`
- Telemetry snapshot: `comp_epaper_expression_state_snapshot`

## Faces

| ID | Face | Priority | Stability | Auto recover | Signals | Host coverage |
|---:|---|---:|---|---:|---|---|
| 0 | `idle` | 20 | stable | 0 | BOOT_IDLE, WAKE_ARMED, RECORDING_CANCEL, RECOVERY, BATTERY_RECOVERED | legacy+demo |
| 1 | `listening` | 60 | transient | 10000 | WAKE_DETECTED | demo |
| 2 | `thinking` | 50 | transient | 12000 | MEETING_STOP, RECORDING_STOP | demo |
| 3 | `speaking` | 70 | transient | 10000 | SPEAKER_PROMPT | demo |
| 4 | `happy` | 30 | transient | 6000 | SPEAKER_RESULT | demo |
| 5 | `sleepy` | 10 | stable | 0 | WAKE_DISABLED, SETTINGS_SLEEPY | legacy+demo |
| 6 | `recording` | 90 | stable | 0 | MEETING_START, RECORDING_START | legacy+demo |
| 7 | `sync_complete` | 40 | transient | 8000 | MEETING_FINALIZE, RECORDING_FINISHED | legacy+demo |
| 8 | `low_battery` | 80 | stable | 0 | LOW_BATTERY | legacy+demo |
| 9 | `error` | 100 | stable | 0 | ERROR | legacy+demo |
