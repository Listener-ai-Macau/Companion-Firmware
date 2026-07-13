# Companion Gesture-First Wake Deployment Evidence

Date: `2026-07-13`

Product requirement: `COMP-REQ-022`

Firmware commit: `d3406df` (`companion: prioritize gestures over idle wake redraw`)

## Machine Result

- Flash: PASS through the short `Companion-WB55` workflow lock.
- Target: `NUCLEO-WB55RG`, ST-LINK `066EFF535570514867221931`, voltage `3.24 V`.
- Image: `Companion_Nucleo_WB55RG_Bringup.hex`, `133.55 KB`, verified by
  STM32CubeProgrammer before reset.
- Reset-bounded serial capture: PASS, `COM13`, 9,834 bytes.
- Boot confirms external asset pack revision `53`, FT6336U `0x38` on PC6
  interrupt mode, 5/8 ms active/idle touch cadence, and the static low-power
  `sleepy` pose entering Stop.

Artifacts:

- `.cache/validation/flash-nucleo/stm32-programmer-20260713-234752-25356.stdout.log`
- `.cache/validation/companion-performance/gesture-first-wake-20260713/nucleo-serial-raw.log`
- `.cache/validation/companion-performance/gesture-first-wake-20260713/nucleo-serial-summary.json`

## What This Does And Does Not Prove

The deployed code records
`low_power_touch_wake state=active visual=gesture_owned result=deferred` on
the first decoded contact instead of synchronously queuing the old `idle`
differential frame. The actual tap, stroke, double-tap, or long press then
owns the first visible e-paper request.

This capture intentionally contained no operator touch. It proves that the
board is on the new binary and reaches the static low-power state; it does not
claim a human-perceived latency pass. The next focused ACPT-01 trace must
contain a real first contact, the new marker, the classified gesture, and its
single resulting visual request before a Chinese operator review can assess
the feel.
