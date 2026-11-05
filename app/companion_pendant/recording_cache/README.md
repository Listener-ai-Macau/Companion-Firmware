# Companion Recording Cache Model

This directory owns the no-hardware recording cache model for the Companion
pendant. The current backend is a file-backed simulator used by validation.
The later product backend is an external SPI NOR driver with the same metadata
and chunk-pull behavior.

The model stores recording metadata required by the BLE contract:

- `recording_id`
- created Unix time and created tick
- duration, byte length, sample format, CRC32, SHA-256, and SHA-256 prefix
- packet sequence and byte-offset readiness
- sync state and delete state

The BLE recording list and `recording chunk pull` behavior are backed by the
cache model. Resume can be expressed by an absolute byte offset or by packet
sequence when the host uses the same negotiated payload size. Byte offset plus
total length remains the source of truth.

Explicit no-hardware behaviors covered now:

- low storage refusal
- interrupted write
- interrupted read
- duplicate delete
- delete-after-sync refusal before host verification
- delete-after-sync success after total length and SHA-256 validation
- privacy erase

Cache operations emit diagnostic event names under `spi_flash_cache.*`. Real
SPI NOR timing, erase/program alignment, power numbers, and refresh of any
physical flash part are deferred to later hardware-gated validation.
