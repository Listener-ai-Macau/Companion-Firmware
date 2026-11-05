# STM32WBA dual-PDM capture boundary

`wba_pdm_capture` is the HAL-free processing layer between a completed SAI DMA
span and Companion's existing 16 kHz mono PCM/codec=3 path. It never creates
synthetic recording data and does not own SAI, DMA, clocks, recording storage,
Opus, or BLE.

Companion V1.1 connects two SPH0655-class microphones to shared `PA10/SAI1_D1`
with opposite channel-select levels and uses `PA9/SAI1_CK1` as their shared PDM
clock. The intended target configuration is SAI1 Block A PDM receive with one
microphone pair. SAI1 Block B independently drives the MAX98357A playback bus.

The STM32WBA SAI PDM interface samples the two microphones on opposite clock
edges, de-interleaves them, and emits successive bytes per microphone. It does
not contain a PDM-to-PCM decimation filter. The portable input layouts therefore
describe the observed DMA byte pair as `[left,right]` or `[right,left]`; bit
order is independently selectable. Do not choose either layout from the
schematic alone. On the first board, capture raw DMA bytes while alternately
covering/tapping each microphone and verify byte order, bit order, channel
energy, and clock polarity with a logic analyser.

The processor accepts decimation 64, 96 or 128:

| PDM clock | PCM rate | Decimation |
| --- | --- | --- |
| 1.024 MHz | 16 kHz | 64 (processor only; outside SPH0655 specified active ranges) |
| 1.536 MHz | 16 kHz | 96 (current SPH0655 normal-mode target) |
| 2.048 MHz | 16 kHz | 128 |

These rates are mathematical target values until `PA9` is measured. With the
shared approximately 49.151855 MHz SAI kernel clock and concurrent Block B
playback, the CubeWBA adapter must prove its actual divider/register values and
measured `CK1`; the portable layer does not infer an SAI divider from the
speaker's Block B `MCKDIV=12`.

Each channel uses a third-order CIC decimator with modulo accumulators, then a
stateful Q15 DC blocker (`0.988`) matching the accepted WB55 filter intent.
Output is left, right, or their average, accumulated in fixed 160-sample/10 ms
PCM16 frames. The target callback should copy each frame into the existing PCM
ring consumed by the real codec=3 encoder. Callback rejection is a visible
dropped frame, never silently replaced by a seed.

The WBA HAL uses the one-frame reader entry point to copy its 3840-byte DMA half
in guarded 256-byte spans. Each half is counted once, independent of copy size.
An overwritten source cannot publish a partial frame. The 96x normalization is
checked against an independent bit-by-bit CIC reference, including repeated
accumulator wrap, priming, maximum gain and both input orders.

The CIC integrators advance four bits at a time through a 16-entry constant
table. Two nibble advances exactly replace eight per-bit updates without an
approximation. Host tests retain the original per-bit recurrence as an
independent oracle and compare PCM sample-for-sample across randomized DMA
chunk sizes, byte layouts, MSB/LSB order, channel inversion, output selection,
and both decimation values. This keeps the 2.048 Mbit/s dual-microphone input
well below the cost of calling the CIC recurrence twice for every PDM bit.

Statistics expose DMA sequence gaps/reordering, invalid byte spans, rejected
PCM frames, discarded partial samples, saturation, and independent left/right
energy and peaks. A forward DMA sequence gap resets CIC/DC state and discards
the partial PCM frame so unrelated bit phases cannot be joined. A duplicate or
older sequence is rejected without consuming its bytes or changing the next
expected sequence, preventing stale PCM from entering a real recording.

Primary references:

- [STM32WBA5 reference manual RM0493](https://www.st.com/resource/en/reference_manual/rm0493-multiprotocol-wireless-bluetooth-le-and-ieee802154-stm32wba5xxx-armbased-32bit-mcus-stmicroelectronics.pdf)
- [ST application note AN5027, Interfacing PDM digital microphones](https://www.st.com/resource/en/application_note/an5027-interfacing-pdm-digital-microphones-using-stm32-mcus-and-mpus-stmicroelectronics.pdf)

RM0493 requires enabling the PDM interface before SAI_A and describes the
edge de-interleaver, byte shift registers, microphone count, clock enables and
delay controls. AN5027 documents SAI PDM DMA byte formatting and confirms that
software still owns decimation to PCM.


## Optional calibrated dual microphone candidate (P635)

The installed676 baseline still selects LEFT. An explicit build argument
`--microphone-dual-delay-q8` activates a fixed delay-and-sum candidate in the
PDM-to-PCM path, before PCM16 clipping. Both channels are filtered; original
LEFT/RIGHT/MIX behavior and storage/codec framing remain available unchanged.
Positive delay means right receives the desired voice later, so LEFT is
delayed. Negative delay delays RIGHT. Delay units are 1/256 of a16kHz PCM sample.
`--microphone-dual-right-gain-q15` is fixed calibration trim, not automatic gain;
`--microphone-dual-invert-right` requires measured polarity, not a noise trick.
Configuration is immutable during capture. Startup discarded samples warm its
history; a DMA discontinuity clears that history. No extra frame or heap.

This is a fixed spatial front end, not speaker identity separation, adaptive
noise cancellation or echo cancellation. Equal arrival/gain is only a
broadside assumption. Microphone spacing, enclosure ports, arrival difference,
phase and gain require current-board acoustic evidence before default use.
Linear fractional delay has a frequency-dependent response. Common correlated
noise is not removed, and the wrong direction can attenuate desired speech.
Synthetic independent-noise improvement is not device SNR qualification.

Acceptance needs synchronized current-board left/right/output recordings of
the same desired speech and separate interfering source, intelligibility/noise
comparison and actual PDM/Opus deadline/continuous recording under ordinary
coexistence. Wearer-focused capture and all-speaker meeting capture must be
judged separately. Keep source recordings, calibrations and failed cases.


## Finite paired observation and calibration candidate (P638)

The ordinary LEFT baseline and16kHz mono codec framing stay unchanged.
An explicit `--microphone-dual-probe` build filters both microphones and
observes synchronous, verified, accepted10ms frames in caller-owned storage.
No observer callback is made for priming, a stale partial DMA frame or mono
backpressure. The callback must not block, allocate, transmit or retain pointers.

The board probe retains only the first32000 samples and bounded lag statistics,
not continuous audio or a hidden recording. It runs only during an ordinary
explicitly started recording. A failed start clears/invalidates previous data;
DMA gaps, bad spans and rejected PCM make this take invalid. DMIC1 is formatted
only after capture stops through the existing normal diagnostic idle gate.
Wide sums are emitted as hi/lo32bit values, not unsupported nano-printf64bit.

`tools/calibrate_wba_dual_mic.py` reads a saved probe without device access.
It requires an explicit recording token, device UID, firmware source and known
single broad-band source declaration. It rejects insufficient/discontinuous,
clipped, missing-channel, low-coherence, ambiguous/periodic and out-of-geometry
data; any accepted result is only a fixed-front-end parameter candidate.
No command auto-installs or changes the current capture configuration.
The result is not noise/intelligibility, source identity or real-time proof.
The independent microphone pair cannot be reconstructed from saved mono Opus.
Future same-take speech/noise A/B must retain independent channels explicitly.
