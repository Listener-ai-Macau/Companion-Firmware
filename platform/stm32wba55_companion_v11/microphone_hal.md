# Companion V1.1 WBA microphone HAL boundary

`microphone_hal` binds the portable `wba_pdm_capture` processor to SAI1 Block A
and GPDMA1 Channel 1. It does not start recording by itself and it does not
create seed audio. The `processing_config.emit_pcm_frame` callback is the only
handoff to the existing real 16 kHz mono PCM/codec=3 path.

The configured receive geometry is one 16-bit SAI slot containing the byte from
each member of the PDM microphone pair. GPDMA transfers halfwords into a fixed
7680-byte circular buffer. The HAL `Size` argument is therefore 3840 halfwords,
not 7680 bytes. DMA half/full callbacks each publish one 3840-byte, 10 ms token.
All copying, CIC/DC processing, and PCM callbacks run later in `poll`.

SAI1 uses one linked-list node in circular mode. Its block-transfer event mode
provides half and full events, making the two fixed halves the ping-pong
buffers. `poll` copies each completed half through 256-byte scratch memory and
checks the half generation and hardware counter before and after every copy.
The reader emits only after the last validated chunk; a failed chunk discards
the partial PCM frame and resets filter history. A late/overwritten half, event-queue
overflow, sequence gap, HAL error, or downstream frame rejection stays visible
in the exported statistics.

The foreground error path always calls `HAL_SAI_DMAStop`; CubeWBA documents
some SAI errors that leave a transfer active for the application to stop. The
coherency checks also read GPDMA `CBR1.BNDT` before and after the scratch copy,
so a DMA boundary crossed before its IRQ is serviced cannot make an actively
overwritten half look safe merely because the software half flag is stale.

The register plan follows RM0493 Rev 7 Table 409: `FSOFF=0` starts the
frame on the first bit of slot zero, and `SLOTSZ=0` takes the slot size from
the 16-bit data size. It must not use the one-bit-leading frame sync common
to I2S. The plan also uses `NODIV=1`, `MCKDIV=16`, and a 16-bit frame. The PDM
interface produces one byte for each of the two microphones per frame, so its
internal SAI_A TDM bit clock must run twice as fast as the microphone bitstream.
The nominal clocks are therefore `49.151855 MHz / 16 = 3.071991 MHz` for SCK_A
and `SCK_A / 2 = 1.535995 MHz` for `CK1`, the 96-times PDM clock for 16 kHz PCM.
SPH0655 specifies normal mode at 1.1–4.8 MHz and low-power mode at 500–900 kHz.
The former 1.024 MHz plan fell between those ranges. The 96x normal-mode change
keeps the speaker PLL and 10 ms capture cadence; it needs acoustic verification.
This is calculated from the configured PLL; it is not a board measurement.
Measure `PA9/SAI1_CK1` on the first PCB and confirm clock frequency, duty cycle,
and microphone timing before hardware acceptance.

RM0493 also marks the first two PDM/TDM frames after enable as invalid. The HAL
conservatively drops the first complete 10 ms DMA half after every start. This
span now warms the CIC/DC history without emitting any PCM callback. Its end
anchors the DC feedback to zero while retaining the settled CIC and last input;
resetting the filters after discarding the span creates a false startup impulse
even with a constant PDM carrier. The existing 10 ms omission is unchanged, and
both generated/discarded sample counters account for it. Priming is restricted
to init/reset, whole decimation boundaries and at least three PCM periods. The
following sequence is checked normally; lost/reordered halves and downstream
rejections remain faults. This addresses a reproduced software transient, not
microphone identity, acoustic calibration or speech-recognition acceptance.

The PDM interface de-interleaves the opposite-edge microphones into two bytes,
but the byte order observed in little-endian DMA memory and the effective bit
order remain probe items. Select `[left,right]` or `[right,left]` and MSB/LSB in
`comp_wba_pdm_config_t`, then verify by alternately stimulating each physical
microphone. No schematic-only choice is reported as hardware evidence.

Board integration must forward GPDMA1 Channel 1 and SAI1 interrupts to the
provided handle-specific helpers. The shared HAL callbacks must forward receive
half, receive complete, and error callbacks to the matching helper. These
helpers only publish tokens and flags. Call `comp_v11_microphone_hal_poll` from
the product task often enough to finish each completed half during the next
10 ms half. The whole ping-pong buffer cycle is 20 ms, but DMA starts reusing a
completed half after the other 10 ms half fills, so 20 ms is not a safe
foreground processing window.

Primary references:

- [STM32WBA5 reference manual RM0493, §42.4.10 and Tables 409–410](https://www.st.com/resource/en/reference_manual/dm00821869.pdf)
- [ST AN5027, Interfacing PDM digital microphones using STM32 MCUs and MPUs](https://www.st.com/resource/en/application_note/an5027-interfacing-pdm-digital-microphones-using-stm32-mcus-and-mpus-stmicroelectronics.pdf)
- [ST SAI product training, including the PDM TDM/bit-clock relationship](https://www.st.com/resource/en/product_training/STM32MP1-Peripheral_Serial_Audio_Interface_SAI.pdf)

The software-only compile and processor tests do not establish real capture,
channel identity, acoustic quality, or codec=3 end-to-end acceptance.

`build_wba_v11.py --microphone-gain 1..128` records a fixed gain in the build
receipt and applies it before Opus encoding. The default remains 1. This is a
board calibration control, not automatic gain or interference rejection. The
processor saturates at int16 and reports clipped samples; a quiet-source
engineering value is not evidence that close or loud speech is unclipped.
The independent 64-bit per-bit oracle also covers the maximum supported gain.
