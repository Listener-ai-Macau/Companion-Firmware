# Companion Premium Menu Art Reference

Status: `MENU_V2_REJECTED_MENU_V3_PENDING_USER_REVIEW`

Iteration ledger:
`docs/art/iterations/companion-menu-v2/iteration-ledger.json`

Rejected output retained for traceability:
`docs/art/generated_companion_menu_reference_v2.png`

Current candidate, not yet implemented or flashed:
`docs/art/generated_companion_menu_reference_v3.png`

Generated art is not shipped verbatim as firmware art. It is the visual source
for the portable 200x200 one-bit menu system. Only an accepted iteration may
become a CEMP resource baseline:

- menu entry remains deliberate: daily pet gestures stay on the pet surface,
  and central 3 s hold opens settings;
- the menu is a companion UI, not a debug list: every row has a distinct icon,
  clear selection state, and a backed product action or live datum;
- the compact header may include only a small inner-face identity mark; it
  must not draw an outer cat or product silhouette;
- detail pages keep small inner-face mood marks; the physical shell owns the
  cat outline, so firmware must not draw ears, head outlines, or whiskers;
- press-cue and arrival cues use one-bit geometric marks rather than bitmap
  transition frames;
- large replaceable menu art, fonts, and future themes stay in external
  `ui_assets`; internal Flash keeps only rescue drawing code.

Planned implementation after design acceptance:

- `tools/generate_screen_menu_assets.py` will reproduce the accepted settings
  home and six detail-page compositions as external PBM assets.
- `app/companion_pendant/epaper/screen_menu.c` will keep the same data/action
  ownership as the product menu information architecture, with a small rescue
  renderer only.

Validation:

- `python .\tools\verify_screen_menu_assets.py`
- `python .\tools\verify_pet_expression_system.py`
- `python .\tools\verify_expression_visual_contract.py`
