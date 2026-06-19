# Companion BLE GATT Contract

This contract records the first Companion service shape that later STM32_WPAN
GATT implementation work should satisfy. It is intentionally hardware-neutral
until the official `BLE_p2pServer` baseline has been flashed.

| service | characteristic | direction | payload | validation |
|---|---|---|---|---|
| device status | status read | device to host | firmware version, boot counter, current mode | host reads after connect |
| battery/charge | battery notify | device to host | percentage, millivolts, charging flags | host sees value changes |
| e-paper card | card write | host to device | UTF-8 card text plus revision | device accepts bounded write |
| e-paper card | render status notify | device to host | revision, state, error code | host sees render result |
| recording control/list | recording command | host to device | start, stop, cancel, list | device records state transition |
| recording chunk pull | chunk read | device to host | packet sequence, byte offset, total length, CRC, payload bytes | host can resume by offset and delete-after-sync only after CRC success |
| settings | settings write/read | bidirectional | small key/value settings | invalid key returns an error |
| diagnostics/log pull | diag log tail read | device to host | bounded log export: cursor, source mask, max events, event records | default bounded tails, not unbounded full dumps |
| delete/privacy | delete command | host to device | object id, wipe scope | delete is explicit and idempotent |
| OTA readiness | manifest read/write | bidirectional | version, size, hash, block size, readiness flags | host refuses OTA when readiness flags fail |

Diagnostics/log pull uses a bounded request:

```json
{
  "cursor": 0,
  "max_events": 16,
  "source": "gatt",
  "format": "companion_diag_v1"
}
```

The firmware may return fewer than `max_events`; the host advances by returned
sequence numbers. A later retained SPI flash ring keeps the same bounded cursor
contract instead of exposing whole-device dumps.

| error | trigger | device behavior | host behavior |
|---|---|---|---|
| invalid_payload | malformed command or length | reject without state change | show actionable error |
| busy | renderer, recorder, or flash cache owns the resource | keep current operation | retry with backoff |
| not_found | requested record or cursor is absent | return empty result | refresh list or restart tail |
| crc_mismatch | recording chunk CRC/hash mismatch | keep data until retry/delete | retry same byte offset |
| not_ready | OTA, recording, or diagnostics dependency unavailable | report readiness flags | stop flow and surface flags |

STM32 implementation notes:

- Map services to STM32_WPAN GATT server attributes and notification paths.
- Keep diagnostics/log pull bounded by `max_events`, source, and cursor.
- Do not reuse ESP NimBLE callback names, ESP partition offsets, or Listener
  chunk/fragment ambiguity in the Companion contract.
