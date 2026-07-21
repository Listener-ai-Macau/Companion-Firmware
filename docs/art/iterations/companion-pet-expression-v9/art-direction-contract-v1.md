# Companion V9 Art Direction Contract v1

## Purpose

The locked V9 prompt and source sheet are the character's visual parent. Every
later image is a separate, runtime-inactive extension candidate. It can add
named pose material but cannot rewrite the character.

## Identity Anchors

- Locked parent: `generated_pet_expression_sheet_v9_candidate.png`
  `919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA`.
- Open eyes always remain the same matched, solid-black, upright vertical
  ovals. This is an identity anchor, not an emotion control.
- Per open eye, white is limited to the familiar upper primary reflection and
  small static diamond sparkle, both contained inside the black eye body.
- The primary reflection stays compact and upper-only; it cannot become a white
  cap, a lower-half cutout, or a second eye shape. The diamond remains visibly
  smaller. Eye pairs retain V9's cell-normalized scale and whitespace.
- No rings, exposed sclera, hollow eyes, thin outlines, pupils, lashes,
  half-lids, drooping/romantic eyes, eye-hugging arcs, side-eye, or a second
  mobile highlight.
- Closed sleep eyes are the only eye-body exception. Sleep has no moon,
  crescent, or Z charm.

## Where Expression Comes From

Direction uses the primary reflection inside an unchanged eye body. Emotion
uses paired brows, a petite mouth, cheek dots, and at most one detached
semantic charm. A charm alone is never enough to call a pose an emotion.

Daily left/right/up/down are attention directions, not four separate emotions.
Their thumbnail difference must be intentional and visible. Curiosity,
affection/delight, joy, alert surprise, recording, listening, menu thinking,
and sleep are distinct scene or emotion entries.

A contact-sheet pose is a source anchor, never a playback frame. Later motion
must move registered source components through entry, hold and settle; it may
not cycle full-face source cells to simulate emotional transformation.

## Iteration Rule

Every candidate starts from the original V9 prompt and locked source, then
names one delta. Its record contains parent ID, input hashes, exact prompt,
negative constraints, output hash, automated contract result, and owner
decision. Rejected output is retained for evidence but cannot become a visual
reference or component source.

The machine-readable form is
`art-direction-contract-v1.json`; `tools/verify_companion_v9_art_lineage.py`
must pass before a future image generation, and again before component export.

## Incremental Generation Loop

1. Begin at the locked V9 `generation-request.json`, not chat memory.
2. Version a new request and `prompt_versioned` lineage record. Name one delta,
   what remains inherited, and what is forbidden.
3. Run `python tools/verify_companion_v9_art_lineage.py --preflight-request
   <request> --write <report>`. Any failure forbids image generation.
4. Generate using only the locked V9 source as a visual reference, then archive
   the output hash before inspection.
5. Run the identity gate for the named delta. A failure is retained as evidence
   but cannot become the next reference, component source, or runtime asset.
6. Only a machine-passing and owner-approved candidate can enter separately
   registered component extraction and Rig verification.

This keeps the process deliberately narrow: prove one visual constraint first,
then expand only after it is stable.
