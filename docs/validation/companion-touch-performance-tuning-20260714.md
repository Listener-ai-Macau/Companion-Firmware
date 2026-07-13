# Companion FT6336 Interaction Performance Candidate

Date: `2026-07-14`

Product requirements: `COMP-REQ-022`, `COMP-REQ-024`, `COMP-REQ-028`, and
`COMP-REQ-029`

## Research Boundary

The FT6x36 register map identifies `TH_GROUP` at `0x80` as the touch-detection
threshold and `PERIODACTIVE`/`PERIODMONITOR` at `0x88`/`0x89` as report-rate
controls. The product therefore changes only documented controller tuning
registers; it does not invent controller gestures or alter the portable
gesture classifier.

## Candidate Change

- Shared WB55/WBA default `TH_GROUP`: `0x90` -> `0x70`.
- Shared active/monitor periods remain `0x04` / `0x04`.
- WB55 normal five-byte report reads use a 5 ms timeout. Setup, probe, identity,
  register configuration, and recovery retain 20 ms.
- Normal successful touch sample, gesture, press-cue, navigation, and deferred
  action logs use `COMPANION_TOUCH_VERBOSE_TRACE=0`; I2C failures and recovery
  still print.
- `-EpaperSsd1681VerboseTrace` and each refresh/transport diagnostic enable both
  e-paper and touch traces. `-Ft6336TouchThreshold <1..255>` is a build-only
  calibration override.

## Machine Evidence Required

1. Build quiet production and trace-enabled images.
2. Verify the quiet image retains only touch failure/recovery UART calls in its
   interaction path while the trace image contains `sample_age_ms`, gesture,
   press-cue, and deferred-action markers.
3. Run portable FT6336, gesture, WB55 target, and WBA boundary validation.

## Machine Result

On 2026-07-14, the quiet production image, manual trace image, `0x70`
calibration-override image, and automatic refresh-cadence diagnostic image all
compiled. The override command emitted
`-DCOMP_FT6336_COMPANION_TOUCH_THRESHOLD=0x70u`; the cadence diagnostic emitted
both `-DCOMPANION_EPAPER_SSD1681_VERBOSE_TRACE=1` and
`-DCOMPANION_TOUCH_VERBOSE_TRACE=1`.

`main.o` contains 164 `printf` relocations in the quiet image versus 202 in the
trace image. The quiet object contains none of the successful sample, gesture,
or double-tap format strings; the trace object contains all three. Linked text
is 129932 bytes quiet versus 135020 bytes with the combined e-paper/touch
trace. FT6336, presentation, refresh-cadence, product-requirement, WB55 target,
and WBA portability static checks passed. These are binary/build facts only;
they do not prove a touch-feel improvement or a safe sensitivity level.

## Hardware Gate

No board was flashed and no observation was requested for this candidate.
When the owner explicitly starts acceptance, record a reset-bounded WB55 trace
with register readback and perform one focused check for false contacts, tap,
drag, right-swipe exit, 3 s hold, and double-tap recording. Restore or adjust
the threshold only from that evidence; source/build success is not a touch-feel
PASS.
