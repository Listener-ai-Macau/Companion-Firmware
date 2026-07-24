# SSD1681 Local Update Research (2026-07-20)

## Scope

This is a source audit and physical-evidence summary for the connected 200x200
monochrome panel. It does not authorize a new waveform, a production policy
change, or a claim that the `0154BN-D67-D2` FPC marking is identical to
`GDEY0154D67-T03`.

## Answer

Yes: the SSD1681 and the supplied Good Display project provide a local **RAM
write** mechanism. A local RAM window is not, by itself, proof of a clean
local **optical** refresh. The supplied source's local activation path has
already failed the continuous-motion residue observation on this panel.

## Supplied Good Display Source

Input is read-only:

`C:/Users/Billy/Desktop/GDEH0154D67-20211203-P-LUT(1s) -1s快刷/EPD_W21/EPAPER.c`

SHA-256: `7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896`.

The source has two distinct modes:

| Mode | Exact source sequence | Meaning |
| --- | --- | --- |
| 159-byte fast LUT | `0x3F/0x03/0x04/0x2C`, `0x32` with 153 bytes, then 5000-byte `0x24`, `0x22=0xC7`, `0x20`, BUSY | Full-frame fast refresh. `User/main.c` calls `EPD_HW_Init_LUT()` and `EPD_WhiteScreen_ALL_LUT()` for this route. |
| Partial rectangle | reset low/high 10 ms, `0x3C=0x80`, `0x44`, `0x45`, `0x4E`, `0x4F`, local `0x24`, `0x22=0xFF`, `0x20`, BUSY | Local RAM write plus the vendor partial activation. It does not load the 159-byte LUT. |

`EPD_Dis_Part_myself()` demonstrates staging five independent local rectangles
through `0x24`, then one `0xFF -> 0x20 -> BUSY` activation. The source requires
X addresses in bytes (`x / 8`) and supplies `PART_COLUMN * PART_LINE / 8` data
bytes for each rectangle. Its partial demo clears after a short loop with
`EPD_HW_Init()` and `EPD_WhiteScreen_White()`.

## Correct Dirty-Region Rule for an Expression

For each changed component, the driver must:

1. Compare the last successful frame and the new frame.
2. Form the union of the old and new component footprints, so disappearance is
   represented as white data as well as the new black pixels.
3. Expand only the X bounds to whole RAM bytes (eight display pixels); retain
   exact Y bounds.
4. Program `0x44`, `0x45`, `0x4E`, and `0x4F`; write only the window bytes.
5. Batch disjoint component windows before one activation when the chosen,
   source-bound profile supports it; coalesce requests while BUSY is high.

The WB55 driver already has diagnostic-only changed-window and multi-region
implementations of this transfer behavior. The rejected micro-motion test
reduced it to four bytes per plane. Therefore there is no evidence that an
upper-layer full-frame write caused the reported broad visual effect.

## Physical Result

The matching supplied-source partial path (`0x24` local payload followed by
`0xFF`, `0x20`, and BUSY) completed machine checks but failed the real
continuous-motion observation with residual lines. The focused disposition is
`NO_GO_PHYSICAL_CONTINUOUS_PARTIAL_RESIDUE` in
`docs/validation/companion-gdey0154d67-t03-vendor-partial-slow-motion-residue-triage-20260720.json`.

The later four-byte-per-plane `0xFC` differential test was also rejected during
live observation because it still looked broadly flushed and dirty. Its
interrupted trace and disposition are recorded in
`docs/validation/companion-wb55-micro-delta-visual-no-go-20260720.json`.

## External Primary Evidence

The SSD1681 datasheet defines the window/counter RAM commands (`0x44`, `0x45`,
`0x4E`, `0x4F`), `0x24`/`0x26` RAM writes, and a later `0x22`/`0x20` display
activation. It also describes OTP waveform selection by sensed temperature.

Good Display publicly states for `GDEY0154D67(-T03)` that partial refresh is
nominally about 0.3 s and fast refresh about 1.5 s, but recommends a full
refresh after every five fast or partial operations to reduce ghosting. Those
claims are model-specific, at 25 C, and do not bind the connected FPC marking.

- SSD1681 datasheet: https://www.orientdisplay.com/wp-content/uploads/2022/08/SSD1681_v0.13.pdf
- Good Display GDEY0154D67: https://www.good-display.com/product/388.html
- Good Display GDEY0154D67-T03: https://www.good-display.com/product/258.html
- Good Display T03 specification download page: https://www.good-display.com/companyfile/1195.html
- Complete 37-page T03 specification mirror: https://manuals.plus/m/c48705c45800fb54239ae0f1edd1025e2e7f1e864ccc8da0c2f744e4f9242b86.pdf
- Good Display T03 STM32 sample-code download page: https://www.good-display.com/companyfile/1029.html

The complete specification and the sample-code archive are reference material
only. They do not supply a new local-refresh LUT for this connected FPC, and
they do not override the source-bound and production-off limits above.

## Conclusion and Next Boundary

The requested low-payload implementation exists and is already exercised in
production-off diagnostics. It cannot meet the requested "only the ball
changes, no broad dirtying, no residual line" condition with the currently
available source on the observed panel.

The 159-byte LUT must not be repurposed as a partial erase waveform: the
supplied project binds it to the full 5000-byte `0x24` and `0xC7` path. The
next legitimate source input is a Good Display statement binding
`0154BN-D67-D2` to a product profile plus its residue-free partial waveform or
OTP/profile-selection flow, room-temperature range, and maximum consecutive
partial-update/cleanup rule. Until then, no custom, generic, web-derived, or
guessed waveform may be tested.
