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

## Direct GPIO SPI A/B Build

The direct-BSRR transport image keeps the active `0xFC` two-plane partial
waveform and only replaces the three per-bit HAL GPIO calls with direct GPIO
set/reset writes, matching the edge order in Good Display's bit-banged sample.
It is a separate electrical/timing diagnostic, not production behavior and not
a WBA target implementation. Build it with:

```powershell
pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -EpaperSsd1681Bringup -EpaperMenu 1 -EpaperSsd1681DirectGpioSpiDiagnostic -Force
```

Its trace must retain `profile=default`, `0xFC`, and two data planes, but report
`spi=software_direct_bsrr_diagnostic`. Parse it with:

```powershell
python tools/verify_wb55_refresh_cadence_log.py --partial-profile differential --transport-profile direct_bsrr --log <trace> --out <result.json>
```

The direct-GPIO and vendor-partial A/B switches are deliberately mutually
exclusive: one compares transport with a fixed waveform, while the other
compares waveform/data planes with the known-good transport.

## Quiet Production Trace Policy

Normal WB55 SSD1681 interaction builds set
`COMPANION_EPAPER_SSD1681_VERBOSE_TRACE=0`. This removes synchronous UART
serialization of successful scene, policy, window, and timing messages from
the visual path while retaining failure output. The low-power `_write` route is
bounded but synchronous, so this preserves CPU time for the five-millisecond
touch service without changing the waveform or resource selection.

For a normal image that deliberately needs serial evidence, add:

```powershell
pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -EpaperSsd1681Bringup -EpaperMenu 1 -EpaperSsd1681VerboseTrace -Force
```

The cadence, vendor-partial, and direct-GPIO diagnostic commands enable this
trace automatically. Do not use a quiet production serial capture to prove
refresh timing: use the matching trace-enabled diagnostic image instead.

Machine build evidence on 2026-07-14: quiet production, manual verbose,
vendor-partial, and direct-BSRR images all compiled. The quiet SSD1681 object
contains two remaining failure-path `printf` relocations versus 29 in the
verbose object; linked text is 132324 bytes quiet versus 135020 bytes verbose.
This proves that successful-refresh UART serialization is removed from the
quiet image, not that panel BUSY or human-perceived responsiveness has passed.

## Lock-Guarded Three-Way A/B Runner

`tools/run_wb55_refresh_ab.ps1` packages the already-built differential,
direct-BSRR, and Good Display one-plane images into one short, locked hardware
window. Its default is non-hardware `-CheckOnly`; it refuses `-Execute` unless
the caller acknowledges a `Companion-WB55` workflow lock. Every diagnostic
capture is reset-bounded and parsed before the next image runs. If a flash,
capture, or parser stage fails after any diagnostic image is installed, the
runner attempts to restore the normal quiet production image before releasing
the lock.

Machine-only runner validation:

```powershell
python .\tools\verify_wb55_refresh_ab_runner.py --write
python .\tools\verify_wb55_refresh_ab_runner.py
```

The runner's `-SelfTestRecovery` uses stub commands only. It deliberately
fails the first capture and proves the normal-image recovery path; it is not
hardware evidence. Only after the owner explicitly says `开始验收` may the
locked execute command below be used:

```powershell
pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose "Companion WB55 refresh A/B" -Run pwsh -NoProfile -File .\tools\run_wb55_refresh_ab.ps1 -Execute -WorkflowLockHeld
```

This run collects strict waveform and timing evidence, then restores the
normal image. It still does not promote either diagnostic: promotion requires
the paired real-panel residual/flicker comparison and the focused ACPT-01
touch/visual review.

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
3. Build and flash the direct-GPIO transport image, capture the same bounded
   trace, then parse it with `--partial-profile differential --transport-profile
   direct_bsrr`. It must prove five `0xFC` two-plane interactions using
   `software_direct_bsrr_diagnostic` and the same sixth `0xC7` cleanup.
4. Build and flash the isolated vendor partial A/B image, capture the same
   bounded trace, then parse it with `--partial-profile vendor_sample
   --transport-profile vendor_edges`. It must prove five reset-bounded `0xFF`
   one-plane interactions through `software_vendor_edges` and the same sixth
   `0xC7` cleanup.
5. Compare all three traces and their on-panel results: responsiveness, residual
   image, BUSY/transport completion, and maintenance flicker. A lower serial
   transfer time alone is not a promotion criterion.
6. Reflash the normal production image before ACPT-01. Run the focused visual
   review for residual image, a single maintenance flicker, and perceived
   responsiveness. Machine timing does not substitute for that review.
