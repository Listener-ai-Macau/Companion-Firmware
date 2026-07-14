# Companion BLE GATT Contract

This contract defines the first Companion pendant BLE surface for the
STM32WB55 product firmware. It is intentionally host-probeable before hardware
bring-up: the UUID table is in `docs/ble_uuid_table.json`, and
`tools/companion_ble_probe.ps1 -SelfTest` validates the static protocol anchors
and a fixture recording transfer.

The device advertises a Companion-specific name and exposes these GATT
services. Multi-byte integers are little-endian. Host writes use
write-with-response unless the characteristic explicitly says notify-only.

## Legacy Listener-Compatible Live Audio

The STM32WB firmware also exposes a deliberately named compatibility service
for legacy A1/A2 bench comparison. This service reuses Listener's live audio
UUIDs and VKA1 packet format so an old Type harness can exercise the same
capsule/session/transport/insertion path. It is not the Companion product host
contract and must not be used as a release dependency for the now-independent
Companion app stack.

This compatibility surface is separate from Companion-native recording storage.
The native path remains the GATT services below: recording control/list/chunk
pull, diagnostics, privacy, OTA readiness, and the Companion-owned OTA v2
loader. The legacy service streams live PCM16 mono 16 kHz notifications only
while a compatibility host is connected and subscribed.

| service | characteristic | UUID | direction | payload |
| --- | --- | --- | --- | --- |
| listener_vka1_audio_stream | listener_vka1_audio_notify | `710af845-6d9f-6583-0c4d-9e5b3bc3091b` | device -> host notify | `VKA1` packets with 20-byte headers: session_start=1, audio_data=2, session_stop=3, session_cancel=4, session_error=5. |
| listener_vka1_audio_stream | listener_vka1_audio_control | `710af845-6d9f-6583-0c4d-9e5b3bc3091e` | host -> device write-with-response | `TYPE:READY`, `TYPE:READY:A1`, `TYPE:READY:A2`, `TYPE:HB`, `TYPE:STOP`/`TYPE:BYE`, `VREC:TOGGLE`, `VREC:STOP`, `VREC:CANCEL`, and processing state text used by Type. `TYPE:READY:A1` opens the short hardware-microphone ASR validation window; `TYPE:READY:A2` opens the longer one. |
| listener_vka1_audio_stream | listener_vka1_audio_readiness | `710af845-6d9f-6583-0c4d-9e5b3bc3091c` | device -> host read | Short readiness text for Type diagnostics. |
| listener_vka1_audio_stream | listener_vka1_audio_capabilities | `710af845-6d9f-6583-0c4d-9e5b3bc3091d` | device -> host read | Short capabilities text for Type diagnostics. |

The service UUID is `710af845-6d9f-6583-0c4d-9e5b3bc3091a`. STM32_WPAN code
maps the portable `app/companion_pendant/audio_stream` module through
`audio_stream_stm32wb.c`: `aci_gatt_add_service`, `aci_gatt_add_char`, control
write handling, CCCD notify enable state, and `aci_gatt_update_char_value`. The
portable module intentionally does not include STM32 HAL, STM32_WPAN, NimBLE, or
ESP-IDF symbols.

The STM32WB adapter advertises a 248-byte notify value for this compatibility
service. The NUCLEO WB55 bring-up app overrides the ST p2pServer example ATT MTU
to 251 locally, so each notification can carry 248 bytes after ATT overhead.
A1 keeps the conservative 132-byte validation payload, while A2 sends the full
320-byte content of each 10 ms microphone frame. With a 248-byte notify value,
the full A2 frame is intentionally split across two VKA1 audio packets so fast
speech is not limited by the older compact sampling view.

Companion follows the Listener active-recording link policy instead of keeping
the BLE connection permanently tuned for audio. On connection, the firmware
leaves the high-speed request deferred. When `TYPE:READY:A1/A2` or a recording
start enters the microphone path, it requests a 7.5 ms connection interval and a
2M PHY preference. When the session stops, is cancelled, or the microphone path
fails, it requests the bounded idle interval again and clears stale notify/type
ready state on disconnect.

`cubeide/Companion_BLE_Audio_Fixture` is the legacy NUCLEO smoke-test image for this
surface. It keeps the product name `companion`, disables PIN/bonding, registers
only the Listener-compatible VKA1 audio service, and sends a deterministic
synthetic PCM session when Type writes `TYPE:READY` after notify subscription.
The product bring-up app additionally accepts `TYPE:READY:A1` and
`TYPE:READY:A2` for optional legacy automated TTS playback through the real
microphone: A1 uses short command phrases, while A2 uses a longer sentence for
text-recognition validation.
It also keeps `VREC:TOGGLE` and the board SW3/B3 user button (PD1 on the
NUCLEO-WB55RG MB1355 board) on the same recording FSM path for manual
control-path checks. SW3 is only the local trigger; the stored object is still
exposed through the Companion-native `recording_list`, `recording chunk pull`,
diagnostics, and `delete/privacy` characteristics below.

| service | characteristic | direction | payload | validation |
| --- | --- | --- | --- | --- |
| device status | device_status | device -> host read/notify | `DeviceStatusV1`: schema version, firmware semantic version, build id, board id, uptime_ms, fault_bitmap, active_mode, advertising_name | Host reads after connect; notify is sent when mode or fault_bitmap changes. |
| device status | battery/charge | device -> host read/notify | `BatteryChargeV1`: percent, millivolts, charge_state, charger_present, temperature_c_x10 | Host accepts percent 0..100 and treats unknown charge_state as degraded status, not a disconnect reason. |
| e-paper card | e_paper_card_write | host -> device write | `CardWriteV1`: request_id, card_slot, utf8_title_len, utf8_body_len, title/body UTF-8 bytes, display_flags | Device validates UTF-8, size, and slot, then stages the update for the display task. |
| e-paper card | e_paper_card_status | device -> host read/notify | `CardStatusV1`: request_id, card_slot, render_state, last_error, content_crc32, refresh_count | Notify confirms accepted, rendered, failed, or busy after a card write. |
| recording | recording_control | host -> device write; device -> host notify | `RecordingControlV1`: request_id, command start/stop/cancel, profile_id, max_seconds, privacy_flags | Device echoes request_id and transitions through idle, recording, stopping, stored, or failed. |
| recording | recording_list | device -> host read/notify | `RecordingListV1`: count plus 32-byte entries of recording_id, started_unix_s, duration_ms, codec, sync_state, source_mode, total_length, sha256_prefix, content_crc32 | Host refreshes after recording_control stop and after delete/privacy operations. `source_mode=1` is the NUCLEO SAI microphone path. |
| recording | recording chunk pull | host -> device write request; device -> host notify packets | Request: recording_id, byte_offset, requested_length, host_resume_token. Response packet header: schema_version, flags, payload_length, recording_id, packet_sequence, byte_offset, total_length, packet_crc32, final_sha256, followed by payload bytes | Host verifies monotonic packet sequence, byte offset continuity, total length stability, CRC per packet, and final hash before marking synced. |
| settings | settings | host -> device read/write; device -> host notify | `SettingsV1`: locale, time_zone_offset_min, quiet_hours, display_brightness, recorder_profile_id, flags | Device validates supported ranges and notifies committed settings_revision. |
| settings | BLE name config | host -> device write; device -> host read/notify | `BleNameConfigV1`: request_id, command stage/apply/reset, name_len, max_len, status, flags, ASCII name bytes | Device validates Listener-compatible ASCII 1..29 name policy, rejects quotes/semicolon/equals/backslash/control bytes, and reports whether advertising restart or reboot is required. |
| meeting | meeting_control | host -> device write; device -> host notify | `MeetingControlV1`: request_id, command start/stop/cancel, profile_id, max_seconds, flags | Device enters a meeting session model distinct from one-shot dictation and echoes status through meeting_status. |
| meeting | meeting_status | device -> host read/notify | `MeetingStatusV1`: meeting_id, state, request_id, started_tick_ms, duration_ms, segment_count, summary_state, sync_state, last_error | Host can show meeting recording progress, later transcript/summary readiness, and sync status without treating it as ordinary dictation history. |
| sensors | IMU status | device -> host read/notify | `ImuStatusV1`: sensor_state, sample_rate_hz, motion_flags, calibration_state, timestamp, accel/gyro/temp sample fields | Host can distinguish not-populated dev boards from present/calibrating/active IMU hardware and later use motion events for wear/tap/orientation features. |
| audio_output | speaker_control | host -> device write; device -> host notify | `SpeakerControlV1`: request_id, command play_prompt, volume_percent, prompt_id, payload_len, flags | Device stages speaker prompts without blocking the GATT callback; current dev board may report pending hardware. |
| audio_output | speaker_status | device -> host read/notify | `SpeakerStatusV1`: state, last_error, request_id, prompt_id, volume_percent, played_count | Host can show whether speaker output is available, accepted, unavailable, or failed. |
| audio_output | wake_word_control | host -> device write; device -> host notify | `WakeWordControlV1`: request_id, command arm/disarm/simulate_detect, sensitivity, model_id, flags | Device arms or disarms the voice wake state model while keeping actual keyword DSP/hardware validation gated. |
| audio_output | wake_word_status | device -> host read/notify | `WakeWordStatusV1`: armed, engine_state, last_event, last_error, sensitivity, confidence, detection_count, rejected_count | Host can distinguish wake armed, disabled, detected, rejected, and unavailable states before real always-on voice validation. |
| diagnostics | diagnostics/log pull | host -> device write request; device -> host notify packets | `DiagLogPullV1`: cursor, max_events, max_bytes, source mask, severity_mask. Response: cursor, next_cursor, total_available, event records or log payload, CRC | Host pulls default bounded tails without unbounded full dumps and without blocking recording or display work. |
| privacy | delete/privacy | host -> device write; device -> host notify | `DeletePrivacyV1`: request_id, operation delete_recording/delete_all_recordings/factory_privacy_wipe, recording_id, validated_total_length, validated_sha256 | Device deletes only after the request matches stored metadata or after a full privacy wipe confirmation. |
| OTA | OTA readiness | device -> host read/notify | `OtaReadinessV1`: ready_state, boot_slot, battery_percent, charger_present, minimum_required_mv, blocker_bitmap, manifest_version, board_target, mcu, image_size, image_sha256_prefix, interrupted_transfer_resume_token | This only reports OTA readiness and blockers; the later OTA data path must reuse an ST OTA reference rather than inventing a custom large-write path here. |

## CardStatusV1 Observability

DeviceStatusV1 is also a screen-expression input. After startup, WB55 device
status publishes map `fault_bitmap != 0` to the error face, active audio mode
to recording, and disconnected mode to the low-priority sleepy hint. Initial
service-state publication is publish-only so it cannot schedule screen work
before the display task exists.

BatteryChargeV1 is also a screen-expression input. After startup, WB55 battery
status publishes feed `battery_charging.sample` into the portable expression
bridge, so low percent or low voltage while not charging can request the
low-battery face. Initial service-state publication is publish-only so it
cannot schedule screen work before the display task exists.

OtaReadinessV1 is also a screen-expression input. After startup, WB55 readiness
publishes map the low-battery blocker to the low-battery face and map other
nonzero blocker values to the error face. Initial service-state publication is
publish-only so it cannot schedule screen work before the display task exists.

MeetingStatusV1, SpeakerStatusV1, and WakeWordStatusV1 are also screen-expression inputs.
After startup, WB55 interaction status publishes map
meeting recording/summary/sync/error, speaker prompt/error, and wake
armed/detected/error state into the same ExpressionV1 faces used by control
diagnostic events. Initial service-state publication is publish-only so it
cannot schedule screen work before the display task exists.

RecordingControlV1 and the internal recording FSM share a portable
screen-expression mapper for state readback. `idle` has no override,
`pending_start`/`recording` map to recording, `stopping` maps to thinking,
`canceled` maps to idle, transfer-ready/active/transferred map to
sync-complete, and error-recovery maps to error. This does not add a new GATT
surface; it keeps future WB55/WBA status readback aligned with the existing
control/event faces.

`e_paper_card_status` is the host-visible screen status surface. Hosts should
treat it as the status of the latest display request, not as proof that a real
panel is present. The fields are:

```text
uint8 schema_version
uint8 card_slot
uint8 render_state
uint8 last_error
uint32 request_id
uint32 content_crc32
uint32 refresh_count
```

`render_state` values are stable: `0=idle`, `1=accepted`, `2=rendered`,
`3=failed`, and `4=busy`. `last_error` values are stable: `0=ok`,
`1=queue_full`, `2=payload_too_long`, `3=bad_argument`,
`4=deferred_no_panel`, `5=deferred_controller_unknown`,
`6=panel_bad_argument`, `7=panel_transport_error`, `8=panel_busy`, and
`9=unsupported_expression`.

Queue fault behavior is host-visible. A full display queue reports
`render_state=busy,last_error=queue_full`. Oversized CardWriteV1 content reports
`render_state=failed,last_error=payload_too_long`. Unsupported ExpressionV1
requests report `render_state=failed,last_error=unsupported_expression`, and
firmware expression state must roll back if enqueue fails.

The current WB55 build has a dry-run panel adapter. A successful CardWriteV1 or
ExpressionV1 enqueue first notifies `render_state=accepted,last_error=ok`; the
display task then reports the dry-run final result as
`render_state=failed,last_error=deferred_no_panel` with the same `request_id`
and `content_crc32`. The paired diagnostic events are
`e_paper.render_request` and `e_paper.update_result`. This makes "no real panel
connected" observable without turning it into an expression self-loop or a fake
rendered PASS.

The display task also records `e_paper.runtime_snapshot` for diagnostics/log
pull consumers. That event does not change `CardStatusV1`; it exposes aggregate
runtime pressure for bring-up: expression current/last signal, queue
`display_queue.pending_count`, high-water and dropped counters, plus panel
deferred/error counts including `panel.error_count`. WB55 and future WBA
adapters should keep the same payload model while changing only platform BLE,
scheduler, and panel transport glue.

The native real-device bench must collect both the accepted CardStatusV1 and
the final CardStatusV1 for the same `request_id`. Its `card_write` artifact
uses `card_status` for the accepted record, `final_card_status` for the terminal
record, `status_sequence` for every matching notification, and
`real_panel_refresh_claimed` only when the final record is
`render_state=rendered,last_error=ok`. The default bench accepts either
`rendered/ok` or the current no-panel deferred final status. The real e-paper
hardware gate must run `tools/companion_ble_real_bench.py` with
`--expect-real-panel`; that mode requires `final_card_status` to be
`rendered/ok` before the artifact can support a real refresh claim. Use
`--screen-final-timeout` to tune the final-status wait for slow e-paper panels.
The same artifact also includes `settings_sleepy_screen_status`, which writes
SettingsV1 with `display_brightness=0`, waits for the ExpressionV1
CardStatusV1 accepted/final pair on card slot 1 with the `0xe0000000` request
ID base, and then restores brightness through `settings_restore_after_sleepy`.
The bench runs this settings sleepy check before recording-control mutations so
a low-priority sleepy hint is measured against the idle/card-write baseline
instead of being correctly suppressed by an active recording or thinking face.
It must also carry a `screen_expression_status` contract operation linked to
`docs/validation/companion-screen-expression-host-status-sequence.json`. That
operation is a six-face host baseline, not a hardware render claim; it keeps
idle, sleepy, recording, low-battery, sync-complete, and error status sequence
semantics attached to the real BLE artifact while `card_write` and
`settings_sleepy_screen_status` remain the hardware-collected accepted/final
CardStatusV1 evidence.
If a live bench fails after collecting any operation, the JSON artifact must
preserve the `operations` array and `partial_operation_count`; panel bring-up
uses that partial evidence to distinguish board reachability or BLE loss from
screen contract drift.
The artifact may also carry the contract-only `screen_expression_demo_status`
operation from
`docs/validation/companion-screen-expression-demo-host-status-sequence.json`.
That `screen_expression_demo_host_status_sequence` fixture extends the host
baseline to every demo face and records `held_steps_emit_no_host_status` for
suppressed demo steps; it is verified by
`tools/verify_expression_demo_host_status_sequence.py`.

For ExpressionV1 requests, the `content_crc32` is derived from the expression
decision and the `e_paper.render_request` diagnostic payload carries
`(expression_id << 16) | signal_id`. The no-hardware BLE matrix uses that pair
through its `screen_expression_status` fixture to correlate boot idle, settings
sleepy, recording, low-battery, sync-complete, and error expressions with
their accepted/final CardStatusV1 records before real panel evidence exists.

## Screen Settings Expression Policy

The expression policy treats SettingsV1 as a low-priority screen hint. A status
snapshot may provide `quiet_hours_active=true`, a `flags` value with bit 0 set,
or a `local_minute` inside `quiet_hours_start_min` / `quiet_hours_end_min`.
Those inputs map the visible ExpressionV1 face to `sleepy`. Wrapping quiet
hours across midnight are valid. `display_brightness=0` also maps to `sleepy`
for no-hardware policy and host preview.

This settings hint must not hide higher-priority product states. Recording,
low-battery, and error states remain visible even during quiet hours or while
the display brightness setting is zero. A future WBA adapter must preserve this
host-facing policy while changing only the platform scheduler and panel driver.

The current WB55 firmware write path applies the immediate screen hint when a
SettingsV1 write has `display_brightness=0` or flags bit 0 set for active quiet
hours. Clearing those fields recovers only a settings-caused sleepy face back to
idle. Local-minute quiet-hours range evaluation remains host/policy-level until
the product platform selects a trusted local time source.

## Diagnostics Log Pull

`diagnostics/log pull` is a bounded log export command, not a full dump surface.
The default request asks for a small tail window:

```json
{
  "cursor": 0,
  "max_events": 4,
  "max_bytes": 244,
  "source_mask": 0,
  "severity_mask": "warn|error",
  "format": "companion_diag_v1"
}
```

`cursor=0` returns the newest bounded tail. A nonzero cursor returns the oldest
matching events with sequence numbers newer than that cursor, so polling does
not skip new records. `source_mask=0` selects all sources. In schema v1, bits
0..7 select source IDs 1..8; sources added above ID 8 remain available through
the all-source request and require a later schema revision for individual bit
selection. `severity_mask=0` selects all severities; otherwise bit N selects
severity N.

The response is `DiagLogPacketV1`. Its fixed 20-byte little-endian header is
followed by zero to eight 28-byte event records:

```text
uint8  schema_version
uint8  flags              bit0=initial tail, bit1=truncated, bit2=empty, bit7=bad request bound
uint16 event_count
uint32 request_cursor
uint32 next_cursor
uint16 total_available    matching records before this packet's event/byte cap
uint16 payload_bytes      event_count * 28
uint32 payload_crc32      standard CRC32 over event records only

repeat event_count times:
  uint32 sequence
  uint32 t_ms
  uint8  source
  uint8  event_id
  uint8  severity
  uint8  flags
  uint32 arg0
  uint32 arg1
  uint32 arg2
  uint32 arg3
```

`max_bytes` bounds the complete response packet, including the header. Zero
selects the 244-byte protocol maximum; a nonzero value below the 20-byte header
returns an error/empty header. The firmware may return fewer than `max_events`
or `max_bytes`. The host validates `payload_bytes`, CRC, monotonic event
sequences, and advances by `next_cursor`. A later retained SPI flash ring keeps
the same bounded cursor/source contract; it must not turn this into an
unbounded full dump or whole-device dump. The retained compatibility rule is:
not unbounded full dumps.

## Recording Transfer

Recording transfer is a pull model. The host first reads `recording_list`, then
writes a `recording chunk pull` request for a specific `recording_id`,
`byte_offset`, and `requested_length`. The device emits one or more notify
packets until the requested window is satisfied, the end of the recording is
reached, or an error is reported.

Every response packet contains:

- `packet sequence`: a monotonically increasing uint32 for this recording
  transfer stream.
- `byte offset`: the absolute zero-based byte offset of this packet payload in
  the recording.
- `total length`: the immutable byte length of the complete stored recording.
- `payload_length`: the number of payload bytes in this packet.
- `CRC`: CRC32 over the packet header fields and payload bytes.
- `hash`: the final packet also carries the full recording SHA-256 so the host
  can verify the complete object before sync is accepted.

The current STM32WB NUCLEO wire packet uses a fixed 56-byte chunk response
header followed by `payload_length` bytes:

```text
uint8 schema_version
uint8 flags              bit0=final, bit7=error
uint16 payload_length
uint32 recording_id
uint32 packet_sequence
uint32 byte_offset
uint32 total_length
uint32 packet_crc32      CRC32 over recording_id, packet_sequence, byte_offset, total_length, payload
uint8 final_sha256[32]   all zero until the final packet
uint8 payload[payload_length]
```

`recording_list.entry_bytes=32` for the current STM32WB implementation:

```text
uint32 recording_id
uint32 started_unix_s
uint32 duration_ms
uint8 codec              1=PCM16 mono
uint8 sync_state
uint8 source_mode        1=SAI microphone capture path
uint8 reserved
uint32 total_length
uint8 sha256_prefix[8]
uint32 content_crc32
```

Resume behavior is byte-offset based. If the BLE link drops after a partial
transfer, the host rereads `recording_list`, keeps the same `recording_id`, and
requests the next missing `byte_offset`. The device starts exactly at that
offset. The host deduplicates by byte offset and total length, then uses packet
sequence only as an ordering and loss-detection aid.

Pendant recording storage is backed by the Companion recording cache model and,
on the NUCLEO hardware path, by external QSPI NOR. The cache owns immutable byte
length, sample format, CRC, SHA-256, created time/tick, sync state, and delete
state for every stored recording. The cache may map a known packet sequence
back to a byte offset when the host resumes with the same payload size, but byte
offset and total length remain authoritative.

The NUCLEO bench app stores up to `FLASH_RECORDING_DEV_MAX_SECONDS=60`
seconds per validation recording. PCM16 mono at 16 kHz is `32,000`
bytes/second, so the current raw cap is `1,920,000` bytes before the recording
header. A one-hour meeting in this raw format is `115,200,000` bytes and does
not fit the current 16 MiB external flash part; one-hour product behavior must
use streaming to the host/phone, audio compression, or a larger storage part.
BLE `recording_control` and the physical SW3/B3 button both finalize the same
persistent QSPI header and data format. Host validation exports the pulled
bytes as 16 kHz mono WAV/PCM artifacts. Firmware erases the recording region
with 64 KiB block erase where aligned, falling back to 4 KiB sector erase for
the tail or unsupported cases, so the 60-second dev cap does not require
hundreds of small erases on the normal path. The SW3 path also runs basic
audio-quality checks, hard-resets the target, proves the same recording is
still listed and byte-identical after reset, verifies bad offset and bad-SHA
delete refusals, requests a bounded diagnostics/log response, and only then
deletes with matching `validated_total_length` and SHA-256.

Current real hardware evidence for this path is:

```text
.cache/validation/companion-button-recording-chain-20260630-155232/companion-button-recording-chain.json
.cache/validation/companion-flash-recording-chain-20260630-155826/companion-flash-recording-chain.json
```

The SW3 physical-button run, collected before the 60-second cap change, wrote
SAI microphone PCM to QSPI flash through the
local PD1 button path, pulled 32768 bytes as a 16 kHz mono WAV, passed the
basic audio-quality checks (`duration_s=1.024`, `rms=359.91`, `peak=1840`),
proved reset persistence, rejected bad offset and bad-SHA delete requests,
received the former 12-byte bounded diagnostics placeholder, then deleted the object with matching
`validated_total_length` and `validated_sha256`. The automatic BLE-triggered
run separately proved the same storage format with a 23360-byte object,
130 transfer packets, matching CRC/SHA, and an empty `recording_list` after
delete. New BLE-triggered runs also export `ble-recording-16k-mono.wav` and
`.pcm` artifacts for host postprocess.

That historical diagnostics response only echoed request fields with a
synthetic `cursor + 1`; it is not evidence that event records or CRC were
exported. Real `DiagLogPacketV1` event export has native/software evidence and
still needs one later BLE hardware rerun after the active board work resumes.

This explicitly avoids reintroducing Listener's old chunk/fragment ambiguity.
There are no independent `chunk_index`, `fragment_index`, or `fragment_count`
fields in Companion recording packets. The single source of truth is the byte
offset plus total length; packet sequence is only the transport packet counter.

The delete-after-sync policy is explicit and conservative. Stored recordings
remain on the pendant after transfer. The host may request delete-after-sync by
writing `delete/privacy` with the `recording_id`, validated `total_length`, and
validated SHA-256. The device refuses deletion if the metadata does not match,
if a recording is still active, or if the request is not acknowledged by the
recording storage task.

Recording postprocess and meeting minutes are host-side derived artifacts. The
device contract stops at verified audio transfer, meeting/recording status, and
privacy/delete state. Host tools may attach a transcript, summary bullets,
decisions, action items, questions, keywords, and Markdown/JSON exports to the
verified WAV. Those derived artifacts must keep the source audio SHA-256 and
`recording_id` so a user or sync service can trace minutes back to the stored
recording and apply privacy erase consistently. The current host-side baseline
is documented in `docs/companion_recording_postprocess.md` and validated by
`tools/verify_companion_postprocess.py` plus
`tools/verify_companion_recording_to_minutes.py`. The one-command wrapper is
`tools/companion_recording_to_minutes.py`; it may bridge to Listener-Type ASR
through Type's existing embedded-audio CLI, but it does not modify
Listener-Type and does not make Type UI part of the Companion release contract.

Wake-word GATT status is a control and state surface until a real keyword
spotting engine is selected and power/false-trigger tests pass. The current
`simulate_detect` command is for product-chain validation and host UI wiring;
it must not be presented as a physical microphone wake hit.

## Companion V1 Feature Baseline

Meeting recording is modeled as a long-lived `meeting` session, not as a
one-shot dictation insert. V1 firmware exposes `meeting_control` and
`meeting_status` so Type can start/stop a meeting, show duration/progress, and
later attach transcript, summary, action-item, and export state without changing
the recording chunk transfer contract.

The IMU, speaker, and wake-word surfaces are V1-ready contracts even on dev
boards where the physical parts are not populated. `imu_status` reports whether
the sensor is present/calibrating/active or explicitly not populated.
`speaker_control/status` lets the host request bounded product prompts while the
device reports unavailable or accepted states. `wake_word_control/status` arms,
disarms, and reports detection/rejection counters so the host can validate the
state flow before always-on keyword hardware and DSP are available.

`BLE name config` follows Listener's configurable-name policy: ASCII 1..29
bytes, printable only, and no quotes, semicolon, equals sign, backslash, or
control bytes. A valid rename is staged and reported as requiring advertising
restart or reboot before the new GAP advertising name is guaranteed visible.

The native real-device bench, `tools/companion_ble_real_bench.py`, must exercise
these V1 surfaces on hardware: invalid and valid BLE name config, meeting
start/stop plus unsupported-command rejection, IMU status read, speaker prompt
plus unsupported-command rejection, and wake-word reject/arm/detect/disarm. The
current NUCLEO bench may report IMU/speaker/wake hardware as not populated or
pending, but the GATT state flow must still be host-visible and validated.
For screen evidence, the bench also waits for e-paper `final_card_status`.
When validating a real panel rather than the current no-panel dev board, pass
`--expect-real-panel` and archive the JSON artifact with the photos/logs used
by the panel hardware gate.

## Errors

| error | trigger | device behavior | host behavior |
| --- | --- | --- | --- |
| invalid_payload | Length, enum, UTF-8, or reserved-bit validation fails. | Rejects the write response and notifies the relevant status characteristic with the failing request_id when available. | Fix payload and retry once; surface the validation error if it repeats. |
| busy | Display refresh, recording stop, delete, or log pull cannot accept a second operation. | Leaves existing operation running and reports busy with current state. | Back off and poll/read the status characteristic before retry. |
| record_missing | `recording_id` is not present or was deleted. | Reports record_missing on recording_list or recording chunk pull status. | Refresh recording_list and stop transfer for that id. |
| offset_out_of_range | Requested byte_offset is greater than total length. | Rejects recording chunk pull and returns current total length. | Restart from a valid byte offset or discard stale local state. |
| crc_mismatch | Device storage CRC check fails before packet notification. | Stops the transfer and marks the recording entry failed_storage_check. | Do not mark synced; request diagnostics/log pull. |
| hash_mismatch | Host final SHA-256 validation does not match recording_list metadata. | Keeps the recording stored and available. | Retry from byte offset zero; do not send delete-after-sync. |
| privacy_locked | Delete or recording command conflicts with privacy wipe or lock state. | Rejects the operation and notifies delete/privacy status. | Require user confirmation or wait for wipe completion. |
| ota_not_ready | Host requests OTA while blocker_bitmap is non-zero. | OTA readiness remains not_ready and no OTA data path is enabled. | Show blocker_bitmap and retry only after battery/charge and mode are acceptable. |
| unsupported_version | schema_version is newer than the firmware understands. | Rejects the request without changing persistent state. | Downgrade to the supported schema or require firmware update. |

## STM32WB Implementation Notes

The firmware implementation must map this contract to STM32_WPAN and BlueNRG
GATT server surfaces:

- Add services and characteristics during service initialization with
  `aci_gatt_add_service` and `aci_gatt_add_char`, using the UUIDs from
  `docs/ble_uuid_table.json`.
- Publish device-to-host state with `aci_gatt_update_char_value`; enable notify
  only when the client configures the CCCD.
- Handle host writes through `SVCCTL_App_Notification`, particularly
  `EVT_BLUE_GATT_ATTRIBUTE_MODIFIED` events, and copy write payloads before
  leaving the callback.
- Use the STM32 utility sequencer (`UTIL_SEQ_SetTask`) or an equivalent product
  task boundary for display refresh, recording storage, diagnostics, and delete
  work. GATT callbacks should parse and enqueue, not block on flash or display
  IO.
- Route HCI/IPCC startup through the existing STM32WB application BLE init path
  inherited from the official `BLE_p2pServer` baseline.
- Do not use ESP NimBLE APIs such as `NimBLEServer`, `NimBLECharacteristic`, or
  `BLEDevice`; Listener ESP32 code is source-reference material only.

OTA readiness stays in the normal Companion application GATT service, while
the dedicated update loader/adapter owns the data path. The portable transfer
contract is the pinned `third_party/denzic-platform` `denzic_ota_v1` protocol;
STM32WB, STM32WBA, and ESP adapters map its fixed control/data/status GATT
profile to their local BLE stack and storage implementation.

## OTA Readiness

`OTA readiness` is a read/notify placeholder that lets the host decide whether
it may offer an update package before any firmware swap path exists. It exposes
only status, blocker, and manifest summary fields. The firmware must not accept
OTA data writes in this step.

The shared transport carries an opaque byte stream. It does not decide whether
the payload is an MCU image or an external resource pack. The signed Companion
bundle manifest selects a component kind such as `mcu_app` or `ui_assets`, and
the target installer writes only to the matching staging/candidate partition.
CRC32 in `denzic_ota_v1` identifies an interrupted transfer for resume; the
bundle signature and per-component SHA-256 remain the authenticity and
integrity boundary. See `docs/companion_ota_component_contract.md`.

The `blocker_bitmap` names are stable host-facing values:

| bit | blocker | trigger |
| --- | --- | --- |
| 0 | recording_active | Local recording FSM is not idle. |
| 1 | transfer_active | Recording chunk pull or any other large BLE transfer is active. |
| 2 | diag_export_active | `diagnostics/log pull` is active. |
| 3 | low_battery | Battery is below the manifest `min_battery_percent` guard or below `minimum_required_mv`. |
| 4 | wrong_board_target | Manifest board target does not match the active target, such as `COMPANION-PENDANT-CE` / `STM32WB55CEUx` for product OTA or `NUCLEO-WB55RG` for bench bring-up packages. |
| 5 | invalid_hash | Manifest SHA-256 does not match the package payload. |
| 6 | interrupted_transfer | A previous OTA transfer stopped before verification and must be recovered or discarded. |

The host preflight maps each blocker bit to a concrete user action before any
transfer button is enabled. Wrong-board and invalid-hash blockers require a new
package; low-battery requires charge above both manifest thresholds; recording,
transfer, diagnostics, and interrupted-transfer blockers require clearing the
named active state first.

Every readiness transition should emit bounded diagnostic events under the
`ota` source, including `ota.manifest`, `ota.readiness`, `ota.blocker`,
`ota.interrupted_transfer`, and `ota.post_update_self_check`.

## Host Probe Contract

`tools/companion_ble_probe.ps1 -SelfTest` is the required pre-hardware probe
path. It validates:

- Required contract anchors and table headers.
- Required services and characteristics in the static UUID table artifact.
- Fixture `recording chunk pull` behavior including packet sequence, byte
  offset, total length, CRC, resume behavior, final hash, and delete-after-sync
  refusal before host verification.
- V1 feature matrix coverage for BLE name config, meeting, IMU, speaker, and
  wake-word state surfaces before hardware is available.

Hardware BLE probing is handled by `tools/companion_ble_real_bench.py` after
the board is advertising. Scanning, connecting, BLE capture, and real-device
validation must run only inside the workflow hardware lock window requested for
that hardware activity.
