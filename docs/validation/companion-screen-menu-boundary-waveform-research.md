# Companion Menu Boundary Waveform Research

Status: `MACHINE_DECISION_READY_HARDWARE_VISUAL_PENDING`

## Target Facts

- The actual target is `GDEY0154D67-T03`: 200x200, `SSD1681`, SPI, with
  FT6336U touch. Good Display lists full refresh as 2 s, fast refresh as 1.5 s,
  and partial refresh as 0.3 s.
- Good Display's GDEY0154D67 family guidance says a full update may flicker
  multiple times, fast update flickers once, and partial update does not
  flicker. It recommends a full-screen refresh after five consecutive fast or
  partial operations to reduce ghosting.

Sources checked on 2026-07-13:

1. https://www.good-display.com/product/258.html
2. https://www.good-display.com/blank7.html?productId=388

## Vendor Sample Cross-check

The official Good Display `GDEY0154D67-T03 STM32 Sample Code` download is
`S-GDEY0154D67-FP-Touch`, retained for this investigation with SHA-256
`202ADAB27515FDBA790565F643C3C83C52C11FF36844E8C387F66676C3D82CD4`.
Its `Display_EPD_W21.c` specifies a distinct fast profile:

1. reset and software reset (`0x12`);
2. internal temperature sensor (`0x18`, `0x80`);
3. load temperature with Display Mode 1 (`0x22`, `0xB1`, then `0x20`);
4. set `0x0064` temperature register (`0x1A`);
5. load the Mode 1 LUT (`0x22`, `0x91`, then `0x20`);
6. activate fast display with `0x22`, `0xC7`, then `0x20`.

The SSD1681 datasheet defines `0xC7` as the Mode 1 display sequence and
`0xCF` as Mode 2. The earlier target sent `0xCF` without the Good Display Mode
1 setup, so its `expected_visible_flicker=single` log was not physical proof.

## Implementation Decision

The owner failed ACPT-01 again after the earlier `0xCF` change, reporting five
visible flashes. The repair distinguishes the required layers:

- portable menu boundary intent: `COMP_EPAPER_REFRESH_MAINTENANCE`;
- valid WB55 SSD1681 baseline: the exact Good Display Mode 1 profile above,
  then one `0xC7` activation;
- residual samples from the long-press contact must not enqueue a menu press
  refresh after the menu arrives;
- `0xF7` remains only for unknown baseline or transport/fault recovery, where
  the expected visible phase model is `multiple`.

This is a machine and vendor-evidence decision, not a physical acceptance
claim. ACPT-01 must still record the actual panel observation for a menu entry
and a right-swipe exit, plus any ghosting after the single-activation path.

## Revision 72 Interaction Cadence Decision

The previous application-level 1200 ms post-touch maintenance timer requested
the Mode-1 profile after every ordinary interaction. That is not a panel
requirement and adds a visible second wait after a `0xFC` differential frame.

The portable refresh policy now treats `PARTIAL_INTERACTIVE` like every other
bounded partial request: five successful differential requests are allowed;
the sixth selects one `0xC7` Mode-1 cleanup and resets the baseline count.
The explicit menu enter and exit boundaries still request one `0xC7` cleanup.
This follows the target vendor's "five consecutive" cleanup guidance and is
also consistent with Waveshare's partial-refresh guidance to clean after
several partial operations. The policy is a cadence contract, not an assertion
that the physical panel has OLED-like latency; visual ghosting remains an
ACPT-01 hardware check.

Additional source checked on 2026-07-14:

3. https://docs.waveshare.com/4.26inch_e-Paper_G/FAQ
