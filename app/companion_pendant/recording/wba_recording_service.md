# WBA recording service

This service coordinates real 16 kHz mono PCM into the existing codec `3`
COP1 stream and `companion_recording_journal`. It uses fixed storage only. It
does not supply seed audio and it does not claim that the WBA microphone,
external NOR timing, BLE transfer, or target encode deadline has passed on
hardware.

## Product sequence

1. Call `comp_wba_recording_service_prepare_port(service, token)`. This reserves
   a non-evicting journal extent and reports `PENDING_START`.
2. Call `comp_wba_recording_service_poll()` from foreground context. Preparation
   erases at most one 4 KiB sector per call, then initializes the 16 kHz / 20 ms
   encoder and COP1 header.
3. Wait for `comp_wba_recording_service_ready_port(service, token)`. Only then
   play the recording-start cue.
4. After the cue completes, call
   `comp_wba_recording_service_control_port(service, true, token)`. Start only
   enables the microphone; it does no erase, catalog commit, or payload program.
5. Forward each foreground 160-sample / 16 kHz block with
   `comp_wba_recording_service_pcm()`, then service work frequently with
   `comp_wba_recording_service_poll()`.
6. Stop with `control_port(service, false, token)`. The service stops the
   microphone first, drains buffered PCM, flushes Opus, programs the tail,
   stores CRC32 and SHA-256, finalizes the journal entry as `UNSYNCED`, and
   trims the completed reservation to its used sector count.

Canceling while `PREPARING` or `READY` aborts the reservation and prevents a
later start for that token. A recording may also stop normally with
`COMP_WBA_RECORDING_STOP_STORAGE_LIMIT`; a conservative worst-case Opus drain
allowance is kept before stopping the microphone.

## Fault contract

Call `comp_wba_recording_service_capture_fault(service, token, reason)` when the
platform observes a stale DMA half, HAL error, capture queue overflow, or PDM
processing rejection. The service stops capture and leaves the partial journal
entry `WRITING`; it never finalizes a damaged recording as successful. Reclaim
that abandoned entry only through the journal's explicit reboot recovery.

PCM ring overflow and foreground encode/program work over
`foreground_budget_ms` also fail closed. Aggregate counters remain diagnostic;
per-session overflow state is reset by `prepare`, so an old failure cannot
poison a later capture. Inspect `last_stop_reason`, `last_fault_reason`, and
`comp_wba_recording_service_get_stats()` for product diagnostics.

The generic journal still keeps its prior reservation behavior. Only callers
that explicitly invoke `comp_recording_journal_trim_completed_extent()` shrink
a completed `UNSYNCED` or `ACKED` extent, and the operation never erases payload.
The WBA service opts in after successful finalize. If trimming fails, the valid
completed recording remains available with its original reservation.

## Validation boundary

Run `python tools/test_wba_recording_service.py`. It builds strict host unit
tests, exercises the real fixed-point libopus path, exports a COP1 artifact,
independently decodes it through PyAV, compares the exported SHA-256 with the
journal value, and strictly compiles the service and journal for Cortex-M33.
The host real-codec build uses a 64 KiB encoder storage override because the
desktop hardening build has a different `opus_encoder_get_size()` than the
embedded configuration. This is not a target RAM measurement.

The result manifest is `.cache/wba-recording-service-host/result.json`. Actual
STM32WBA55 encode time, NOR erase/program latency, DMA safety, microphone audio,
and the full GATT pull chain remain hardware acceptance work.
