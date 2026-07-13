# Companion Recording FSM And Microphone Contract

This directory is the product-owned recording-control surface for the Companion
pendant. It adapts Listener's `voice_recording_control` state-machine shape,
but keeps the STM32 implementation independent of Listener's ESP platform
drivers.

## FSM Scope

The portable FSM in `recording_fsm.c` covers these explicit states:

- idle
- pending start
- recording
- stopping
- canceled
- transfer-ready
- transfer-active
- transferred
- error/recovery

Transition decisions are side-effect free in
`comp_recording_fsm_decide_transition()`. Runtime entry points apply the
decision, update metadata, and emit Companion diagnostic log events. Static
validation checks the transition artifact table instead of relying on hardware.

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

This step does not claim real microphone audio quality. Real capture, signal
quality, clipping/noise, and board wiring remain in the later hardware gate.
