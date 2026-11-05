# STM32WBA SSD1681 transaction boundary

`ssd1681_wba` is a portable, task-context transaction engine for the confirmed
GDEY0154D67/SSD1681 panel controller. It contains no STM32 HAL calls, GPIO
numbers, framebuffer art, or heap allocation.

The extracted V1.1 PCB connectivity gives `EPD_RES` only one endpoint,
`JP2.10`; it has no MCU or expander pad. The assembled board currently has
its screen power switch disabled by hardware rework. It explicitly uses
`SOFTWARE_ONLY`: readiness and a 10 ms supply settling interval precede
`0x12`, followed by at least 10 ms and BUSY readiness. This does not simulate
a hardware reset or power cycle. The hardware-reset mode still requires a
real callback, and contradictory mode/callback combinations fail closed.

The full transaction retains the accepted WB55 sequence: 10 ms reset low/high
boundary, SSD1681 software reset, Good Display Mode-1 temperature/LUT selection,
normal 200x200 descending-Y geometry, old/current RAM writes (`0x26`, `0x24`),
one vendor full-update `0xF7` visible activation, current-to-current and
current-to-old full RAM synchronization, and actual-temperature
`0x18:0x80`, `0x22:0xB9/0x20`
Mode-2 rearm. The current production profile does not install the historical
manual 100-degree preset. Mode-1 loading and Mode-2 rearm each wait at least
120 ms without blocking the foreground.

Ordinary paired Mode-2 partial and fast full-window updates use `0xFF/0x20`;
the recording sparse path uses `0xCF/0x20`. Both require a valid baseline.
Ordinary paired updates write the true previous image to `0x26`, the true
current image to `0x24`, activate once, then synchronize the current image
to both RAM planes without another activation. FW246/P32 retains the same
staged byte window for ordinary paired updates after the first qualified
Mode2 baseline. Complete old/current frames must have no changed bytes outside
that window; such requests are rejected before SPI. First Mode2 after a full,
fast full-window baselines, and recovery still normalize the full 200x200 image.
This preserves both-plane synchronization rather than omitting it. Keep both source
buffers immutable until this post-refresh synchronization succeeds. A RAM
write window alone is not evidence of a restricted electrical drive area or
of ghosting elimination.

The library default maintenance count is 64. The product supplies `UINT8_MAX`
to disable count-only maintenance; its presenter retains a separate clean
boundary requiring five minutes, 192 completed Mode-2 updates, and a settled
autonomous family transition outside blinking and recording. Physical ghosting
and the black-frame failure remain unresolved until installed-board observation.

WBA recording refreshes use a separate bounded transaction. The current WBA
safe window is renderer x2..41/y172..195 (controller x-byte0..5/y4..27 after
the row flip). Ordinary dirty-rectangle coverage is split into at most four
rectangles around that window and remains current-plane `0x24`. Only changed
byte runs inside the recording window receive previous/current `0x26`/`0x24`;
the combined transaction restores its dirty-union address window before one
`0xCF` activation and synchronizes all touched regions into both RAM planes
afterward, with no second activation. This prevents an unchanged
microphone glyph from being rewritten by a face/status bounding rectangle.

That WBA geometry is temporary. The accepted generation-21 recording art used
y156..179 and its complete 64-frame source pack is unavailable in this
workspace. The transaction tests prove command ordering, exact byte exclusion,
failure handling, and bounded host/Cortex-M33 compilation; they do not claim
the current three-frame art restores the accepted pixels or that the sequence
has passed on a physical GDEY0154D67 panel.

`comp_ssd1681_wba_poll` sends at most one register item or one in-row RAM
packet per call. A register command and its at-most-four-byte payload use
separate bounded transfer callbacks within that poll. Reset delays and BUSY
waits advance from `now_ms`; they never
spin or sleep. Like the accepted WB55 refresh waiter, each visible activation
must observe BUSY assert and then return ready; a ready sample in the same tick
as `0x20` is not treated as completion. The 100 ms Mode2 BUSY-start gate and
overall configurable BUSY timeout both fail closed. FW239 full updates retain
the original F7 activation until the existing total deadline even when its
BUSY starts after 100 ms; they send no second activation or retry reset.
A timeout or transport failure is visible in status/statistics
and invalidates the cached baseline. The caller must keep frame pointers valid
and unchanged until completion. The driver consumes controller-coordinate
200x200, 1-bpp frames with a 25-byte row stride, so existing expression and
refresh-policy layers remain the source of pixels and refresh decisions.

An unexpected BUSY between register/RAM packets pauses the transaction; writes
resume only after the existing 20 ms stable-ready interval. The original armed
deadline still bounds this pause. BUSY qualification is sampled foreground
evidence, not continuous signal capture or an optical quality measurement.

## FW148 candidate: less overhead, visibility-based dwell

Within a paired Mode-2 transaction, OLD-to-CURRENT and
POST_CURRENT-to-POST_PREVIOUS use the same window and entry direction. Rewind
only `0x4E/0x4F` for those two plane switches; window changes still use the full
setup. This removes eight redundant register items (16 transfer callbacks)
without changing any frame bytes, row packet bounds, or visible activations.

`last_visible_completed_ms` records BUSY assertion followed by stable ready.
Successful completion still waits for RAM synchronization and, for full
updates, Mode-2 rearm. The presenter carries this earlier timestamp to pet
peak dwell and natural-blink cadence only. Input, recording, retry deadlines
and the accepted absolute daily-motion schedule retain actual completion time;
failed or stale completions cannot advance the choreography. An identical
frame has no new activation and uses its current request time.

The existing bounded `PANEL15` trace now includes `visible_ms` and `post_ms`
(RAM synchronization plus any rearm), avoiding additional SPI reads or logs
during capture/playback. FW148 is compiled, not installed; no tests were added
or run in this phase. Latency and ghosting improvements require physical
verification and must not be inferred from register-count savings.

The first failure's stage, operation, sequence, BUSY level and timestamp are
retained in statistics before later retries overwrite the live stage. Cached
`PANEL2` output distinguishes a failed visible activation from a blocked reset
or LUT load. These fields do not turn a software completion into visible owner
acceptance. The FW1.1.48 profile-ordering change was compiled with native tests
not run; its physical result is recorded separately in `docs/board_operations.md`.

This adapter does not establish the unresolved reset connection,
panel polarity, physical waveform quality, BUSY timing on the assembled board,
or real-PCB acceptance.

## Supplier register-LUT quick full (2026-10-14 source candidate)

`COMP_V11_PANEL_VENDOR_QUICK_FULL=1` (builder option
`--panel-vendor-quick-full`) compiles a distinct full-frame supplier LUT route.
It is off by default. Availability additionally requires `RESET_HARDWARE` and
a non-null reset callback. The current board's software-only binding does not
enable it. Bind the actual endpoint through the existing
`comp_v11_hal_bind_panel_reset` only after the wiring and GPIO are known; no
pin assignment or 8-bit/9-bit conversion is guessed here.

`comp_ssd1681_wba_start_vendor_quick_full` copies the supplied active profile
verbatim: 100ms reset low/high, software reset and normal 200x200 geometry,
R3F/R03/R04/R2C bindings from the last six bytes of the159-byte array, exactly
153 one-byte R32 writes, full current RAM24, then one C7/20 activation. Each
LUT byte yields to the foreground; all register/RAM/LUT transfers retain the
same sampled stable-ready and failure deadlines. The original total visible
wait is not shortened and BUSY assertion plus stable ready remain mandatory.

After visible completion, this candidate uses real10ms low/high RESET to
leave the manual voltage/VCOM/LUT profile, restores actual-temperature Mode2
with B9, and synchronizes current24/current26 without a second display
activation. Only then does the frame complete. Reset/LUT/rebase failure leaves
the baseline invalid. The register array adds no new persistent driver state;
`normalize_previous`, unused by normal Mode1, marks only the quick-full return
phase and is reset when starting a full transaction.

When this profile is available, changed menu/navigation requests select this
Mode1 route. Startup, unknown baseline, debug full and genuinely due F7 clean
retain normal full. Unchanged pixels still skip a refresh, and ordinary pet
animation/recording retain their existing paths. A quick-full completion is
counted as full, but does not reset the independent time/update budget since
the last normal F7 clean. With the profile disabled or RESET unavailable,
navigation retains its historical Mode2 full-RAM fallback; that fallback is
not described as the newly implemented supplier quick-full waveform.

This is source implementation, not installed-board validation. The package's
about1s label and the old WB55 measurements are not current-board latency or
temperature qualifications. Fast full still has a visible flash; it is not a
no-flash partial waveform or a cure established for the fading/BUSY defects.
