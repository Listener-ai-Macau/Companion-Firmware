# WB55 Low-Power Idle Timer

## Purpose

Prevent an ordinary touch from immediately appending a `sleepy` e-paper frame.
The board must retain its low-power goal while treating the rest pose as a
long-idle transition instead of an interaction tail.

## Contract

- Daily-page idle arms one RTC TimerServer one-shot for `15000 ms`.
- The core may enter CubeWB Stop while the timer is armed.
- Timer expiry only sets a flag; the main loop requests one static external
  Flash `sleepy` differential frame and then returns to Stop.
- Any FT6336 contact cancels an armed deadline before gesture recognition.
- There is no periodic sleep animation, polling loop, or immediate post-touch
  sleepy redraw.

## Machine Checks

On 2026-07-14, all static checks passed:

```text
python tools/verify_companion_low_power_requirements.py
python tools/verify_wb55_touch_wake_log.py --self-test --scope stop-wake
python tools/verify_companion_function_acceptance_coverage.py
python tools/verify_touch_ft6336.py
python tools/verify_screen_presentation.py
python tools/verify_companion_product_requirements.py
pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -EpaperSsd1681Bringup -EpaperMenu 1 -Force
```

The production WB55 build passed with `text=136320`, `data=2436`, and
`bss=188175`. The known CubeWB vendor warnings remain unchanged.

## Remaining Hardware Evidence

Capture a reset-bounded trace for at least 20 seconds and prove:

1. `low_power_idle_timer=armed delay_ms=15000` precedes Stop.
2. The RTC deadline emits exactly one static `sleepy` request with
   `trigger=idle_timer`.
3. A later focused touch trace shows `low_power_idle_timer=cancelled
   reason=touch`, then its gesture response without a preceding sleepy redraw.

The first two are machine evidence; the touch feel is still part of the active
ACPT-01 re-review and does not become accepted from this document.
