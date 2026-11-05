# Companion speaker playback

This directory is the portable playback half of the Companion V1.1 speaker.
It has no HAL, GPIO, SAI, DMA, RTOS, or TCA6408 dependency. The selected board
adapter owns those details through three callbacks in `speaker_playback.h`.

The product format is 16 kHz mono PCM16. The portable layer applies a bounded
gain ramp and duplicates each sample into standard I2S left/right 16-bit slots.
The target therefore configures 32 BCLK periods per LRCLK and submits each
64-frame block asynchronously. Only one block can be in flight. The target
must call `comp_speaker_tx_complete()` from its deferred DMA completion/error
path before `comp_speaker_service()` can submit another block.

`set_amplifier_enabled` represents the logical MAX98357A `SD_MODE` state. On
Companion V1.1 the board owner routes it through TCA6408 P6. The portable layer
does not know that pin or expander. It enables the amplifier, sends one silent
4 ms block before audio, ramps samples, sends a final silent/ramped block, then
disables the amplifier. A callback or DMA failure fails closed to disabled.

`set_playback_active` is the product-policy boundary. CubeWBA glue should map
it to the playback low-power blocker and any recording/playback coexistence
policy. The portable player never starts, stops, or reconfigures microphone
capture itself.

The built-in cues are short generated acknowledgements for confirm, recording
start, recording stop, and error. Arbitrary PCM uses `start_stream()` followed
by bounded `write_pcm16()` calls. There is no heap allocation.

## Product audio feedback policy

`audio_feedback` sits above the portable player and accepts product events for
touch confirmation, connection changes, recording start/stop, and errors. It
uses a fixed eight-item priority queue, per-event cooldown, active/queued
deduplication, and bounded stale-event removal. Connected/disconnected reuse
the existing ascending/descending contours; this layer adds no speech, cloud
audio, gesture, or display asset.

A recording start request creates a gate. Capture must wait until
`comp_audio_feedback_take_recording_start_gate()` returns `PLAYED`, `SILENT`, or
`FAILED`. `PLAYED` means the cue and amplifier shutdown completed. `SILENT`
means quiet mode deliberately skipped or stopped the cue. `FAILED` is released
only after the speaker has faulted closed or stopped, so delayed playback cannot
leak into the microphone. Pending starts can be cancelled without producing a
later READY result. A recording-stop cue is rejected while capture is marked
active and must be submitted only after capture actually stops.

Touch and connection cues are suppressed while recording. `ERROR` is the sole
critical event allowed by this module during capture; the product coordinator
should normally stop capture first, then submit the error, so the diagnostic
tone is not recorded. Quiet mode suppresses every event and resolves a start
gate as `SILENT`. The module is opt-in and does not change the existing WB
product path unless that path explicitly binds and services it.

Run the software-only contract with:

```powershell
pwsh -NoProfile -File .\tools\test_wba_speaker_host.ps1
```

This runs native state-machine/audio checks and a strict freestanding
Cortex-M33 compile when `arm-none-eabi-gcc` is installed. It does not prove
audible output, gain, polarity, noise, current, or speaker thermal limits.

Primary device references:

- [Analog Devices MAX98357A product page](https://www.analog.com/en/products/max98357a.html)
- [MAX98357A/MAX98357B data sheet, Rev. 16](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX98357A-MAX98357B.pdf)

The data sheet establishes standard I2S input for MAX98357A, 8--96 kHz sample
rates, operation without MCLK, and active-low shutdown through `SD_MODE`.
