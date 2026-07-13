# Companion Interaction Profile Runtime Gate

Date: `2026-07-14`

## Purpose

The external CEMP resource revision proves which art pack mounted. It does not
prove that the WB55 is running the interaction-latency candidate. The normal
firmware therefore emits exactly one boot-time marker, before normal display
or touch work begins:

```text
[build] interaction_profile=quiet epaper_trace=0 touch_trace=0 \
ft6336_threshold=0x70 touch_poll_active_ms=5 touch_poll_refresh_ms=5 \
refresh_policy=partial_x5_then_fast_cleanup
```

This marker is absent from the interaction hot path. It identifies the image
that disables successful e-paper/touch UART traces, uses the shared `0x70`
FT6336 candidate, keeps 5 ms active/BUSY touch service, and has no
per-contact delayed maintenance refresh.

## Machine Evidence

The following completed without change-source warnings on 2026-07-14:

```text
python tools/verify_touch_ft6336.py
python tools/render_wb55_touch_visual_acceptance_packet.py
python tools/render_wb55_touch_visual_review_template.py
python tools/verify_wb55_touch_visual_review_record.py
python tools/verify_screen_presentation.py
python tools/verify_expression_acceptance_index.py
python tools/verify_companion_product_requirements.py
pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -EpaperSsd1681Bringup -EpaperMenu 1 -Force
pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -EpaperSsd1681Bringup -EpaperMenu 1 -EpaperSsd1681VerboseTrace -Force
```

The normal image is `text=130164`, `data=2436`, `bss=188143`; its HEX SHA-256
is `EB54DEE573A1EFE0B953687D55B4FA2ECA00E78072B26885A2EFE05531CCFE2F`.
The trace image is `text=135252`, `data=2436`, `bss=188143`; its HEX SHA-256
is `3644D0A4E0F8D2A0805E1AFA8A32E6E893F060567F119CC0A067E0698E75E6FE`.
The normal compile has neither verbose-trace define; the trace compile has
both `COMPANION_EPAPER_SSD1681_VERBOSE_TRACE=1` and
`COMPANION_TOUCH_VERBOSE_TRACE=1`.

## Hardware Gate

Status: `PENDING_HARDWARE_RUNTIME_MARKER`.

No board was flashed or observed for this change. Before ACPT-01 can reopen,
a reset-bounded **normal** WB55 capture must contain every token in the marker
above. The generated touch/visual packet treats older rev53 resource logs as
insufficient until that happens. After that machine precondition is met, the
same focused `1/13` review still has to confirm right-swipe exit from any menu
position, 3 s hold behavior, touch feel, and the single menu boundary cleanup.
Neither this marker nor the build proves the human-perceived latency result.
