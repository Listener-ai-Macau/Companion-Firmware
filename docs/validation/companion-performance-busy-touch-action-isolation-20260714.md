# WB55 BUSY Touch Action Isolation

## Purpose

Repair the owner-reported interaction lag without changing the approved visual
baseline or dropping recording, phone-link, or external-Flash behavior.

## Contract

While an SSD1681 waveform is BUSY, the FT6336 wait service continues the
existing 5 ms gesture timeline.  It may queue a visual response and one of the
following runtime actions, but it must not execute the action in the display
wait callback:

- daily double-tap recording toggle;
- menu recording start or stop;
- menu phone reconnect.

The main loop executes a queued action only after the synchronous display task
returns.  Runtime logs make both phases observable:

```text
[touch-ui] deferred_runtime_action action=<name> phase=queued
[touch-ui] deferred_runtime_action action=<name> phase=execute delay_ms=<n>
```

## Machine Evidence

Run from `Companion-Firmware-devboard-oai1` on 2026-07-14:

```text
python tools/verify_touch_ft6336.py
python tools/verify_epaper_refresh_policy.py
python tools/verify_screen_presentation.py
python tools/verify_companion_product_requirements.py
python tools/verify_expression_panel_target_stm32wb.py
pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -EpaperSsd1681Bringup -EpaperMenu 1 -BootSelfTests -Force
```

All commands passed.  The WB55 image built with `text=135776`, `data=2436`,
and `bss=188175`; the only compiler warnings are pre-existing STM32CubeWB
vendor warnings in BLE and middleware sources.

The final production build omitted `-BootSelfTests`, then flashed and verified
on `NUCLEO-WB55RG` (`ST-LINK 066EFF535570514867221931`, 3.24 V):

```text
text=135824 data=2436 bss=188175
flash: .cache/validation/flash-nucleo/stm32-programmer-20260714-001950-4620.stdout.log
serial: .cache/validation/companion-performance/busy-touch-action-isolation-production-20260714/nucleo-serial-raw.log
```

The reset-bounded production trace reports `boot_selftests=skipped`, FT6336
trigger mode and runtime tuning applied, the revision-53 external resource
pack mounted, and the restored vendor-edge software SPI path.  It completed a
1298 ms initial full refresh and a 306 ms differential low-power frame.

## Remaining Hardware Evidence

This is not an ACPT-01 pass.  No operator touch was injected during the short
boot capture, so the focused WB55 trace must still show a touch action queued
during a real panel BUSY interval followed by its matching execute marker.
The existing ACPT-01 physical review remains the only human gate.  The device
must keep the verified Good Display vendor-edge software SPI path; the rejected
2 MHz hardware-SPI experiment is not part of this image.
