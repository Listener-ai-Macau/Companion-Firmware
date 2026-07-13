# Companion Premium Pet Art Reference

Status: `DESIGN_REFERENCE_APPLIED_TO_PROCEDURAL_RENDERER`

Generated reference:
`C:\Users\Billy\.codex\generated_images\019f44be-6fce-7140-acbe-cac2c63e2a4e\call_sxOaWkmtZjlSzsysOIcglF4D.png`

The generated sheet is not shipped as firmware art. It is a visual direction
source for the portable one-bit renderer:

- keep only inner cat-face features because the physical shell provides the
  cat outline;
- use rounded bean eyes with visible highlights;
- make the nose/mouth feel like the same pet across states;
- use soft status marks: hollow thought bubble, listening waves, tiny record
  dot, small spark;
- make tap and four-way strokes move the whole inner face, not just the eyes;
- keep all production-sized replaceable art in external `ui_assets`.

Applied implementation:

- `app/companion_pendant/epaper/pet_expression.c`
  - rounded nose highlight;
  - hollow thought bubbles via `stroke_logical_ellipse`;
  - compact spark helper via `draw_small_spark`;
  - softer listening and recording marks.
- `app/companion_pendant/epaper/pet_behavior.c`
  - sparse whole-face living phase for product-state expressions.

Validation:

- `python .\tools\verify_pet_expression_system.py`
- `python .\tools\verify_expression_visual_contract.py`
- `python .\tools\verify_screen_menu_assets.py`
