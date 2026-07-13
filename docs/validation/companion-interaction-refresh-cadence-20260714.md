# Companion Interaction Refresh Cadence - 2026-07-14

Status: `MACHINE_BUILD_READY_HARDWARE_TRACE_PENDING`

## Change

Commit `1a52ea9` removes the application-level 1200 ms post-touch maintenance
timer. A normal tap, stroke, menu drag, ordinary menu navigation, recording
status update, or phone reconnect now sends only its `PARTIAL_INTERACTIVE`
request. The portable `refresh_policy` allows five successful differential
requests, then selects one Mode-1 fast cleanup on the sixth request. Explicit
menu enter and right-swipe exit remain one `MAINTENANCE`/`0xC7` visual boundary
each. A normal full `0xF7` refresh is still baseline/fault recovery only.

The behavior is portable to WBA55/WBA65 through `refresh_policy.h/.c`; a WBA
target must supply its panel waveform adapter but must not add a per-touch
delayed cleanup timer.

## Machine Evidence

- Build passed:
  `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -EpaperSsd1681Bringup -EpaperMenu 1 -Force`
  - output: `text=135224`, `data=2436`, `bss=188143`.
  - pre-existing STM32CubeWB warnings remain; this change introduced no build
    errors or warnings.
- Static contracts passed:
  - `python tools/verify_epaper_refresh_policy.py`
  - `python tools/verify_screen_refresh_feel_contract.py`
  - `python tools/verify_screen_presentation.py`
  - `python tools/verify_pet_expression_system.py`
  - `python tools/verify_touch_ft6336.py`
  - `python tools/verify_expression_wba_portability.py`
  - `python tools/verify_expression_panel_target_stm32wba.py`
  - `python tools/verify_touch_target_stm32wba_ft6336.py`
  - `python tools/verify_expression_wba_lse_clock_contract.py`
  - `python tools/verify_expression_panel_gate.py`

Commit `e458dae` also corrected the real-panel gate so it identifies the
verified Good Display Mode-1 `0xC7` path as current and labels the old `0xCF`
record as retired historical evidence.

## Required Hardware Follow-up

No board was flashed for this change and no human observation was requested.
The existing WB55 runtime logs therefore do not prove this image is running.
When the owner explicitly starts a hardware session:

1. Flash the `1a52ea9` (or descendant) WB55 production image under the
   `Companion-WB55` hardware lock.
2. Capture a reset-bounded serial trace covering at least six completed normal
   interaction refresh requests.
3. Confirm requests 1-5 select differential `0xFC`, request 6 selects one
   vendor-profiled `0xC7`, and there is no `screen_maintenance`/1200 ms
   delayed request after an ordinary interaction.
4. Run the focused ACPT-01 visual review for residual image and perceived
   responsiveness. Machine timing does not substitute for that review.
