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

## Implementation Decision

The failed ACPT-01 observation of five visible flashes is consistent with the
old menu-boundary `0xF7` full waveform, even though the serial log contained
only one logical refresh request. The repair distinguishes these layers:

- portable menu boundary intent: `COMP_EPAPER_REFRESH_MAINTENANCE`;
- valid WB55 SSD1681 baseline: `COMP_EPAPER_REFRESH_DECISION_FAST` -> `0xCF`;
- expected visible phase model for `0xCF`: `single`;
- `0xF7` remains only for unknown baseline or transport/fault recovery, where
  the expected visible phase model is `multiple`.

This is a machine and vendor-evidence decision, not a physical acceptance
claim. ACPT-01 must still record the actual panel observation for a menu entry
and a right-swipe exit, plus any ghosting after the single-flicker path.
