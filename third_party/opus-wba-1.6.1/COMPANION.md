This is an opt-in STM32WBA55CE build profile of pinned upstream Opus1.6.1.
The original Companion Opus directory and other products are unchanged.

`companion-profile.json` locks the original archive and every build input.
`companion-celt-only.patch` records the local encoder specialization. Defining
`COMPANION_OPUS_CELT_ONLY=1` permits only restricted-CELT/16kHz/mono/20ms;
it exposes the selected mode to dead-code elimination, retaining upstream
preprocessing, CELT arithmetic and standard Opus packet framing. The firmware
adapter retains16kbps CBR, complexity0 and the original COP1 container.

The8744-byte aligned workspace still fits all17 OTA command slots (8738 bytes)
and the5452-byte ARM encoder state. Encoder and queue ownership are exclusive,
including pause/drain. CE places it in actual SRAM1; it is not an allocation
in the undocumented address hole. Both SRAM banks need normal startup and
retention/DMA qualification.

Native1200-packet output/final-range equivalence is software evidence only.
It does not qualify physical microphone quality, ARM scheduling/stack, power,
BLE throughput, OTA or the whole product. The whole CE App is still RAM-blocked.
The unsuccessful MDCT/input-lifetime experiment was withdrawn; no changes to
`celt/mdct.c` or `celt/celt_encoder.c` remain in this profile.
