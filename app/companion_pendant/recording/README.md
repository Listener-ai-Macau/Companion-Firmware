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

`microphone.h` describes a SPH0645-compatible PDM MEMS microphone family when
that part is available. The STM32 ingress choices are documented as HAL/LL
SAI/PDM, HAL/LL I2S/PDM, DFSDM/PDM where available, or the software fixture
used by validation. The code does not call Listener ESP audio drivers.

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
