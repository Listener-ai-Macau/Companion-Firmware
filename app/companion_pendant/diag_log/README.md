# Companion Diagnostic Log Foundation

The Companion diagnostic log starts as a portable RAM ring under
`app/companion_pendant/diag_log/`. The core is C99-style code with overridable
lock hooks and no ESP-IDF, flash partition, or RTOS dependency.

Initial retention model:

- RAM ring capacity defaults to `COMP_DIAG_LOG_RING_CAPACITY=128`.
- Events are fixed records: sequence, millisecond timestamp, source, event ID,
  severity, flags, and four integer arguments.
- `comp_diag_log_read_tail()` and `comp_diag_log_read_tail_by_source()` remain
  local inspection helpers. `comp_diag_log_read_page()` implements the shared
  cursor/source/severity query used by product transports.
- `diag_log_export.c` builds the platform-neutral `DiagLogPacketV1`: a bounded
  20-byte header, up to eight fixed event records, and CRC32. WB55 and future
  WBA adapters only publish those bytes through their own BLE stack.
- Warning and error source groups are explicit sources so host tooling can
  request focused tails without unbounded dumps.

Future retained ring:

- A later SPI flash cache step may mirror selected RAM events into a retained
  SPI flash ring.
- That retained ring must use Companion-owned sector metadata and sequence
  numbers. It must not copy Listener ESP partition table assumptions, NVS
  handles, `esp_partition_*`, or ESP-IDF flash APIs into STM32 code.
- BLE log export remains bounded by count, bytes, source, severity, and cursor
  even after the SPI flash ring exists.
