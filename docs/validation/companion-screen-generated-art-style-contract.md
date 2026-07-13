# Companion Screen Generated Art Style Contract

Target style: `genref_sheet_12_inner_faces_v5`

Reference images:

- Pet expression reference:
  `C:\Users\Billy\.codex\generated_images\019f44be-6fce-7140-acbe-cac2c63e2a4e\call_sxOaWkmtZjlSzsysOIcglF4D.png`
- Checked-in pet expression sheet:
  `docs/art/generated_pet_expression_sheet_v5.png`
- Menu reference:
  `C:\Users\Billy\.codex\generated_images\019f44be-6fce-7140-acbe-cac2c63e2a4e\call_9d7DlQZ8xM9KMMfALsrQ2lte.png`

The generated images are art direction, not firmware payloads. WB55/WBA firmware
must translate them into a deterministic, replaceable resource pipeline:

- `import_generated_expression_sheet.py` crops the checked-in generated 4x3
  expression sheet into white-background, black inner-face PBM product assets.
- `card_renderer.py` expression drawing primitives are retained only for
  rescue/maintenance art and tooling previews; normal product CEMP expression
  frames must be generated-sheet imports or generated-sheet aliases.
- `pet_visual_style.h` constants for compact rescue/maintenance procedural
  inner-face expressions.
- `MENU_STYLE` constants in `generate_screen_menu_assets.py` for menu PBM
  generation.
- External CEMP resource packs for normal expression/menu art.

Generated-image baseline is the source of truth for normal product art. Older
hand-made procedural faces are allowed only as rescue/maintenance fallback
anchors; they must not replace the external CEMP expression/menu path or become
the visual baseline again.

Human accepted physical-art baseline: the normal WB55 expression pack matches
`generated_pet_expression_sheet_v5.png` on the real panel. Preserve this
approved visual identity during future prompt adjustments; clipping or transport
fixes must not change pose semantics or restore legacy procedural faces.

Normal product packs must not show a mixed old/new handoff. Every
`expression_*.pbm` referenced by the normal CEMP manifest must be emitted by
`import_generated_expression_sheet.py` from the accepted sheet, or be an
explicit alias of one emitted pose. A product resource pack that references
older procedural expression PBMs fails validation even if those files still
exist for rescue tooling.

The physical shell owns the cat outline. Screen assets draw only inner facial
features: eyes, highlights, eyelids, nose, mouth, cheeks, small marks, and menu
state decorations. Firmware must not add cat ears, head outline, whisker outline,
or a second silhouette unless the industrial design changes this boundary.

Adjustment workflow:

1. Generate or select a new reference image.
2. Save the accepted expression sheet under `docs/art/`.
3. Run `python .\tools\import_generated_expression_sheet.py` so generated art
   overwrites every normal-product expression PBM referenced by the CEMP pack.
   Do not mix older procedural support frames into the normal product pack.
4. Open `.cache\validation\generated-expression-sheet-review.png` and compare
   every REF/PBM pair against the checked-in generated sheet before accepting
   the art. Fix cropped ornaments, brows, mouth/nose, cheek marks, or label
   leakage before flashing.
5. Run `python .\tools\render_generated_expression_normal_pack_contact_sheet.py --write`.
   Open `.cache\validation\rev51-generated-expression-normal-pack-sources.png`
   and confirm every expression used by the normal CEMP pack visually belongs
   to the generated-sheet family.
6. Confirm the import report's `machine_review.status` is `PASS`; it guards
   against empty/overfilled faces, canvas-edge clipping, and bottom label
   leakage, but it does not replace the REF/PBM visual review above.
7. Update `COMP_PET_STYLE_NAME` only when the visual contract version changes.
8. Tune `pet_visual_style.h` only for rescue/maintenance procedural anchors.
9. Tune `MENU_STYLE` for menu chip/card/badge placement.
10. Run `python .\tools\render_generated_art_style_contract.py --write` so the
   machine-readable JSON/markdown snapshot records the new style anchors.
11. Regenerate CEMP when PBM output changes.
12. Run the screen menu, normal-pack contact sheet, and pet expression verifiers
   before flashing hardware.
13. Run `python .\tools\verify_generated_expression_sheet_profile_portability.py`
   before claiming a new panel profile is supported. It proves the same source
   sheet can generate isolated, correctly sized assets with a new suffix.
14. When a clipping or source-art correction changes normal PBMs, increment the
   CEMP revision and run `python .\tools\verify_generated_art_clipping_fix_candidate.py`
   before provision/runtime recheck. Never overwrite an accepted external
   revision with different art bytes.

Fast prompt-to-screen rule: when product art changes, use the same ordered path
every time: accepted generated sheet -> importer -> REF/PBM review -> normal-pack
contact sheet -> incremented external CEMP revision -> machine verifiers ->
hardware flash/recheck. Do not manually redraw a generated pose in firmware to
approximate a prompt revision.

Inner-face clipping rule: the accepted generated sheet has no screen-drawn cat
silhouette, so normal imports must not paint a white shell guard inside the
visible 200x200 canvas. The final visible area and shell dimensions are not
yet fixed, so normal art has no arbitrary firmware-side edge margin. If a new
image needs a destructive internal mask, correct or recrop the source and
review it before creating a CEMP revision.

Panel migration rule: `200x200` / `1_54in` are the current WB55 default profile,
not art-engine constants. A new WB55/WBA panel must select its own
`WIDTHxHEIGHT` profile and asset suffix, generate a separate PBM set, then bind
that set through a matching CEMP profile. It must not overwrite the validated
WB55 resource names or create fixed screen margins before industrial geometry
is frozen.

Screen feel policy:

- Use partial/differential refresh for visible interaction, with dirty windows
  and queue coalescing so a slow panel never replays stale finger positions.
- Keep full multi-flash refresh for unknown baseline, fault recovery, or an
  explicit maintenance test, not ordinary touch feedback.
- Schedule ghost cleanup after interaction settles as one quiet maintenance
  pass; if the panel still looks dirty, tune the refresh profile and cleanup
  cadence instead of blending in old art.
- Art changes and refresh changes are separate axes: new PBM/CEMP art must stay
  visually coherent, while the panel target chooses how often to refresh it.

Flash policy: internal flash keeps control code and compact procedural renderers.
Large, rarely changing, or product-art assets go into external flash and are
covered by the screen resource/OTA contract.
