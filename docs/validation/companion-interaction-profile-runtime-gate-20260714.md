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
that disables successful e-paper, touch, and screen/pet-interaction UART
traces. `app_ble.c` binds its `SCREEN_INTERACTION_TRACE` macro to the same
`COMPANION_TOUCH_VERBOSE_TRACE` switch, so production removes successful menu
enqueue, rendered-frame, pet-attention, and pet-stroke formatting while the
trace image retains it. A separate concise `coherent_generation=1` line is
emitted only after the first successful coherent screen frame following queue
initialization: it preserves the normal-capture resource proof without being a
touch or panel-BUSY hot-path log. The image uses the shared `0x70` FT6336
candidate, keeps 5 ms active/BUSY touch service, and has no per-contact delayed
maintenance refresh.

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

After the one-shot coherent-marker revision, a fresh normal build is
`text=128332`, `data=2436`, `bss=188151`; its HEX SHA-256 is
`A55DAA6F1F2481E1E1AB827164DE212E2559395680FE1D8DFAC68B09C6397FB1`.
The trace image is `text=135396`, `data=2436`, `bss=188151`; its HEX SHA-256
is `E4C33A0310A325D5B1FA1F9842B7907F5497D0BFA757CCD96F2E879C486CD627`.
The linked-image string comparison is retained in
`docs/validation/companion-interaction-serial-quiet-20260714.json`: normal
contains none of the six successful interaction markers while trace contains
one of each. Both images retain the failure marker and exactly one reset-bounded
coherent-generation marker. The normal compile has neither verbose-trace define; the trace compile has
both `COMPANION_EPAPER_SSD1681_VERBOSE_TRACE=1` and
`COMPANION_TOUCH_VERBOSE_TRACE=1`, which also enables
`SCREEN_INTERACTION_TRACE` for its diagnostic logs.

## Hardware Gate

Status: `PENDING_HARDWARE_RUNTIME_MARKER`.

No board was flashed or observed for this change. Before ACPT-01 can reopen,
a reset-bounded **normal** WB55 capture must contain every token in the marker
above. The generated touch/visual packet treats older rev53 resource logs as
insufficient until that happens. After that machine precondition is met, the
same focused `1/13` review still has to confirm right-swipe exit from any menu
position, 3 s hold behavior, touch feel, and the single menu boundary cleanup.
Neither this marker nor the build proves the human-perceived latency result.
