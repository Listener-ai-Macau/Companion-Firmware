# Companion BLE GATT Contract

This contract defines the first Companion pendant BLE surface for the
STM32WB55 product firmware. It is intentionally host-probeable before hardware
bring-up: the UUID table is in `docs/ble_uuid_table.json`, and
`tools/companion_ble_probe.ps1 -SelfTest` validates the static protocol anchors
and a fixture recording transfer.

The device advertises a Companion-specific name and exposes these GATT
services. Multi-byte integers are little-endian. Host writes use
write-with-response unless the characteristic explicitly says notify-only.

## Listener-Compatible Live Audio

For early A1/A2 validation with the existing Listener-Type recorder path, the
STM32WB firmware also exposes a deliberately named compatibility service. This
service reuses Listener's live audio UUIDs and VKA1 packet format so Type can
exercise the same capsule/session/transport/insertion path before Companion's
native pull-model sync is wired into the UI.

This compatibility surface is separate from Companion-native recording storage.
It streams live PCM16 mono 16 kHz notifications only while Type is connected and
subscribed.

| service | characteristic | UUID | direction | payload |
| --- | --- | --- | --- | --- |
| listener_vka1_audio_stream | listener_vka1_audio_notify | `710af845-6d9f-6583-0c4d-9e5b3bc3091b` | device -> host notify | `VKA1` packets with 20-byte headers: session_start=1, audio_data=2, session_stop=3, session_cancel=4, session_error=5. |
| listener_vka1_audio_stream | listener_vka1_audio_control | `710af845-6d9f-6583-0c4d-9e5b3bc3091e` | host -> device write-with-response | `TYPE:READY`, `TYPE:HB`, `TYPE:STOP`/`TYPE:BYE`, `VREC:TOGGLE`, `VREC:STOP`, `VREC:CANCEL`, and processing state text used by Type. |
| listener_vka1_audio_stream | listener_vka1_audio_readiness | `710af845-6d9f-6583-0c4d-9e5b3bc3091c` | device -> host read | Short readiness text for Type diagnostics. |
| listener_vka1_audio_stream | listener_vka1_audio_capabilities | `710af845-6d9f-6583-0c4d-9e5b3bc3091d` | device -> host read | Short capabilities text for Type diagnostics. |

The service UUID is `710af845-6d9f-6583-0c4d-9e5b3bc3091a`. STM32_WPAN code
maps the portable `app/companion_pendant/audio_stream` module through
`audio_stream_stm32wb.c`: `aci_gatt_add_service`, `aci_gatt_add_char`, control
write handling, CCCD notify enable state, and `aci_gatt_update_char_value`. The
portable module intentionally does not include STM32 HAL, STM32_WPAN, NimBLE, or
ESP-IDF symbols.

The STM32WB adapter advertises a 153-byte notify value for this compatibility
service. The current NUCLEO WB55 fixture inherits the ST example ATT MTU of 156,
so each notification can carry 153 bytes after ATT overhead. Do not advertise the
larger 244-byte Listener/ESP value until the STM32WB ATT/mblock settings and
validation fixture are raised together.

`cubeide/Companion_BLE_Audio_Fixture` is the NUCLEO smoke-test image for this
surface. It keeps the product name `companion`, disables PIN/bonding, registers
only the Listener-compatible VKA1 audio service, and sends a deterministic
synthetic PCM session when Type writes `TYPE:READY` after notify subscription.
It also keeps `VREC:TOGGLE` and the board SW1 button on the same fixture path
for manual control-path checks.

| service | characteristic | direction | payload | validation |
| --- | --- | --- | --- | --- |
| device status | device_status | device -> host read/notify | `DeviceStatusV1`: schema version, firmware semantic version, build id, board id, uptime_ms, fault_bitmap, active_mode, advertising_name | Host reads after connect; notify is sent when mode or fault_bitmap changes. |
| device status | battery/charge | device -> host read/notify | `BatteryChargeV1`: percent, millivolts, charge_state, charger_present, temperature_c_x10 | Host accepts percent 0..100 and treats unknown charge_state as degraded status, not a disconnect reason. |
| e-paper card | e_paper_card_write | host -> device write | `CardWriteV1`: request_id, card_slot, utf8_title_len, utf8_body_len, title/body UTF-8 bytes, display_flags | Device validates UTF-8, size, and slot, then stages the update for the display task. |
| e-paper card | e_paper_card_status | device -> host read/notify | `CardStatusV1`: request_id, card_slot, render_state, last_error, content_crc32, refresh_count | Notify confirms accepted, rendered, failed, or busy after a card write. |
| recording | recording_control | host -> device write; device -> host notify | `RecordingControlV1`: request_id, command start/stop/cancel, profile_id, max_seconds, privacy_flags | Device echoes request_id and transitions through idle, recording, stopping, stored, or failed. |
| recording | recording_list | device -> host read/notify | `RecordingListV1`: count plus entries of recording_id, started_unix_s, duration_ms, codec, total_length, sha256_prefix, sync_state | Host refreshes after recording_control stop and after delete/privacy operations. |
| recording | recording chunk pull | host -> device write request; device -> host notify packets | Request: recording_id, byte_offset, requested_length, host_resume_token. Response packet: recording_id, packet sequence, byte offset, total length, payload_length, flags, payload, CRC, final SHA-256 when complete | Host verifies monotonic packet sequence, byte offset continuity, total length stability, CRC per packet, and final hash before marking synced. |
| settings | settings | host -> device read/write; device -> host notify | `SettingsV1`: locale, time_zone_offset_min, quiet_hours, display_brightness, recorder_profile_id, flags | Device validates supported ranges and notifies committed settings_revision. |
| diagnostics | diagnostics/log pull | host -> device write request; device -> host notify packets | `DiagLogPullV1`: cursor, max_events, max_bytes, source mask, severity_mask. Response: cursor, next_cursor, total_available, event records or log payload, CRC | Host pulls default bounded tails without unbounded full dumps and without blocking recording or display work. |
| privacy | delete/privacy | host -> device write; device -> host notify | `DeletePrivacyV1`: request_id, operation delete_recording/delete_all_recordings/factory_privacy_wipe, recording_id, validated_total_length, validated_sha256 | Device deletes only after the request matches stored metadata or after a full privacy wipe confirmation. |
| OTA | OTA readiness | device -> host read/notify | `OtaReadinessV1`: ready_state, boot_slot, battery_percent, charger_present, minimum_required_mv, blocker_bitmap, manifest_version, board_target, mcu, image_size, image_sha256_prefix, interrupted_transfer_resume_token | This only reports OTA readiness and blockers; the later OTA data path must reuse an ST OTA reference rather than inventing a custom large-write path here. |

## Diagnostics Log Pull

`diagnostics/log pull` is a bounded log export command, not a full dump surface.
The default request asks for a small tail window:

```json
{
  "cursor": 0,
  "max_events": 16,
  "max_bytes": 1024,
  "source": "gatt",
  "severity_mask": "warn|error",
  "format": "companion_diag_v1"
}
```

The firmware may return fewer than `max_events` or `max_bytes`. The host
advances by `next_cursor` and returned sequence numbers. A later retained SPI
flash ring keeps the same bounded cursor/source contract so the protocol is
not unbounded full dumps or whole-device dumps.

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

Resume behavior is byte-offset based. If the BLE link drops after a partial
transfer, the host rereads `recording_list`, keeps the same `recording_id`, and
requests the next missing `byte_offset`. The device starts exactly at that
offset. The host deduplicates by byte offset and total length, then uses packet
sequence only as an ordering and loss-detection aid.

Pendant recording storage is backed by the Companion recording cache model. The
cache owns immutable byte length, sample format, CRC, SHA-256, created time/tick,
sync state, and delete state for every stored recording. The cache may map a
known packet sequence back to a byte offset when the host resumes with the same
payload size, but byte offset and total length remain authoritative.

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

OTA readiness is only a readiness/status contract in this step. The actual OTA
transport must be selected later from ST's STM32WB OTA examples, such as
`BLE_p2pServer_ota` or `BLE_Ota`, after the basic Companion GATT server is
working.

## OTA Readiness

`OTA readiness` is a read/notify placeholder that lets the host decide whether
it may offer an update package before any firmware swap path exists. It exposes
only status, blocker, and manifest summary fields. The firmware must not accept
OTA data writes in this step.

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

Future hardware BLE probing must be added as a separate mode after the board is
advertising. Scanning, connecting, BLE capture, and real-device validation must
run only inside the workflow hardware lock window requested for that hardware
activity.
