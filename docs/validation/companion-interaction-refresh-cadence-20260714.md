# Companion Interaction Refresh Cadence - 2026-07-14

Status: `DIAGNOSTIC_BUILD_READY_HARDWARE_TRACE_PENDING`

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

## Focused Diagnostic Build

The dedicated cadence diagnostic is production-off by default and exists only
to make the remaining hardware trace deterministic. Build it with:

```powershell
pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -EpaperSsd1681Bringup -EpaperMenu 1 -EpaperRefreshCadenceDiagnostic -Force
```

It issues one baseline menu frame, then queues six distinct interactive menu
frames only after the prior panel transaction succeeded. The static contract
and synthetic parser self-test passed:

- `python tools/verify_wb55_refresh_cadence_diagnostic.py`
- `python tools/verify_wb55_refresh_cadence_log.py --self-test`

The parser is intentionally strict: it requires one full baseline, five
`differential/0xFC` refreshes, one sixth `maintenance/0xC7` refresh, all six
queue/completion markers, no diagnostic abort, no obsolete delayed maintenance
marker, and `transfer_after_waveform_ms=0` for every differential frame. The
last condition protects the WB55-only removal of the redundant post-waveform
RAM replay. A parser pass over synthetic data is not hardware proof.

## Vendor Partial A/B Build

The Good Display `0xFF` one-plane partial path is available only as a separate
diagnostic image. It is not production behavior and it must not be copied into
the WBA target. Build it with:

```powershell
pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -EpaperSsd1681Bringup -EpaperMenu 1 -EpaperSsd1681VendorPartialDiagnostic -Force
```

It reuses the six-request sequence but resets before each partial, writes only
`0x24`, records `profile=good_display_vendor_partial_ab`, and activates
`0xFF`. Its trace must be checked separately:

```powershell
python tools/verify_wb55_refresh_cadence_log.py --partial-profile vendor_sample --log <trace> --out <result.json>
```

The normal diagnostic requires `profile=default`, `0xFC`, and two data planes;
the A/B image requires the vendor profile, `0xFF`, and exactly one data plane.
Both require five successful partial frames, zero post-waveform transfer, the
same sixth `0xC7` cleanup, and no delayed maintenance. Neither profile is
visually accepted until the paired on-panel comparison is complete.

## Required Hardware Follow-up

No board was flashed for this change and no human observation was requested.
The existing WB55 runtime logs therefore do not prove this image is running.
When the owner explicitly starts a hardware session:

1. Build and flash the normal cadence diagnostic under the `Companion-WB55`
   hardware lock only after the owner explicitly begins a hardware session.
2. Capture a reset-bounded serial trace through
   `refresh_cadence_diagnostic done`, then parse it with
   `python tools/verify_wb55_refresh_cadence_log.py --partial-profile
   differential --log <trace> --out <result.json>`. It must prove five `0xFC`
   two-plane interactions, then exactly one `0xC7` cleanup, no 1200 ms delayed
   request, and zero post-waveform transfer time on every partial frame.
3. Build and flash the isolated vendor A/B image, capture the same bounded
   trace, then parse it with `--partial-profile vendor_sample`. It must prove
   five reset-bounded `0xFF` one-plane interactions and the same sixth `0xC7`
   cleanup.
4. Compare the two traces and their on-panel results: responsiveness, residual
   image, and maintenance flicker. A lower serial transfer time alone is not a
   promotion criterion.
5. Reflash the normal production image before ACPT-01. Run the focused visual
   review for residual image, a single maintenance flicker, and perceived
   responsiveness. Machine timing does not substitute for that review.
