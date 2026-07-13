# WB55 Idle Frame Stop Return

## Scope

Verify the scheduler-side performance and power fix from `86a0f01`:
after the RTC 15 s idle deadline draws its one static `sleepy` frame, the
completed synchronous display task must immediately return the existing
portable policy to CubeWB Stop. This is a serial-log proof only; it is not a
product-current measurement or a focused touch acceptance result.

## Device And Image

- Board: `NUCLEO-WB55RG`, ST-LINK `066EFF535570514867221931`, 3.24 V.
- Image: normal production build, external CEMP revision `53`.
- Flash: `.cache/validation/flash-nucleo/stm32-programmer-20260714-004611-26312.stdout.log`.
- Raw reset-bounded serial capture:
  `.cache/validation/companion-performance/low-power-idle-stop-return-20260714/nucleo-serial-raw.log`.

## Commands

```powershell
pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -EpaperSsd1681Bringup -EpaperMenu 1 -Force
python .\tools\verify_companion_low_power_requirements.py --write-fixture
python .\tools\verify_wb55_touch_wake_log.py --self-test --scope idle-timer
python .\tools\verify_wb55_touch_wake_log.py --log .\.cache\validation\companion-performance\low-power-idle-stop-return-20260714\nucleo-serial-raw.log --scope idle-timer --out .\.cache\validation\companion-performance\low-power-idle-stop-return-20260714\idle-timer-report.json
```

All commands passed. The production image size was `text=136472`,
`data=2436`, `bss=188175`; compiler warnings are unchanged STM32CubeWB vendor
warnings.

## Observed Order

```text
[power] low_power_idle_timer=armed delay_ms=15000
[power] stop=allowed blockers=0x00000000 touch_irq=1
[screen] low_power_idle pose=sleepy animation=stopped
[power] low_power_face request=sleepy trigger=idle_timer
[power] stop=blocked blockers=0x00000000 touch_irq=1
[epaper] refresh mode=differential ... elapsed_ms=307
[power] stop=allowed blockers=0x00000000 touch_irq=1
[power] low_power_face completed=1 stop=allowed
```

The idle-timer parser reports `PASS`: FT6336 trigger mode and PC6 wiring are
present, the timer preceded Stop and one static sleep request, and the new
display-complete marker follows that request. The partial-frame transport was
`53 ms` before and `53 ms` after the `307 ms` panel waveform, using the
retained vendor-edge software SPI path.

## Remaining Gates

- A focused physical touch trace must still prove cancellation of an armed
  timer and the subsequent gesture response; no touch was injected here.
- Product-board `LP-01` current remains `hardware_current_pending`; this
  NUCLEO board is not valid evidence for the final `<=1 mA` target.
- This does not alter ACPT-01's failed status, the pending four-up menu visual
  decision, or the future Good Display profile/temperature investigation.
