# Shared Recording Core And Companion Adapter

This directory is the Companion adapter for the single recording core in
`third_party/denzic-platform/audio/embedded/c`. Listener's recording semantics
are the shared baseline; STM32 SAI/PDM, QSPI, BLE, touch, and Companion
diagnostics remain product adapters.

## FSM Scope

The Denzic Platform core covers these explicit states:

- idle
- pending start
- recording
- stopping
- canceled
- transfer-ready
- transfer-active
- transferred
- error/recovery

Transition decisions, metadata, and the transition artifact live only in
`denzic_audio_recording_v1.[ch]`. Local `recording_fsm.c` contains no private
state machine; it translates shared transitions into existing Companion
diagnostic events and converts the STM32 microphone format/batch structs.
Static validation rejects a new Companion-owned transition table.

## Microphone Boundary

`microphone.h` keeps the microphone family separate from the STM32 ingress. The
WB55 devboard default is now the Listener-style SPH0655-compatible PDM source on
the IOC's three-signal SAI path (SCK/FS/SD), converted by the WB55 platform
adapter into 16 kHz PCM16 mono frames. The older SPH0645-compatible I2S source
remains a selectable family for comparison. The software fixture is only for
validation, and portable recording code does not call Listener ESP audio
drivers or depend on WB55 SAI/DMA details.
The accepted WB55 PC-speaker/TTS baseline is recorded in
`docs/validation/companion-mic-wb55-pdm-baseline.json` and checked by
`tools/verify_companion_mic_wb55_pdm_baseline.py`.

## BLE Metadata Boundary

The FSM updates metadata required by `docs/ble_gatt_contract.md`:

- `recording_id`
- `duration_ms`
- `frame_count`
- `total_length`
- `content_crc32`
- `sha256_prefix_words`
- `packet_sequence_next`
- `byte_offset_ready`
- `sync_state`
- sample format fields: sample rate, bits per sample, channels, frame samples

The shared core does not claim microphone quality. Real capture, session reuse,
signal quality, clipping/noise, board wiring, and bounded polling are WB/WBA or
ESP hardware-adapter responsibilities and require their hardware gates.
