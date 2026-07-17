# Companion Goal Actual Acceptance Contract

This is the current, goal-scoped acceptance contract. It replaces neither the
active Codex Goal nor machine evidence. It makes the remaining owner and
hardware gates reproducible one item at a time.

## Session Rules

- Start a live session only after the owner explicitly says `开始验收`.
- Run all listed machine gates before taking the short hardware lock.
- Open one canonical Chinese `aiw operator-prompt` item at a time. A selection
  records what the operator observed; it cannot override a missing log, image,
  source hash, or current trace.
- A non-empty operator note is a product requirement. Triage it before the
  next item; do not silently retry or infer a pass.
- Use the displayed build and resource hashes in the matching evidence record.
  Do not substitute a legacy CEMP, procedural face, old six-root menu, generic
  LUT, or a nearby panel's waveform.

## Current Blocking Facts

- The v9 expression CEMP remains inactive. The 39-frame machine candidate is
  not permission to provision external Flash or flash WB55.
- The four-root menu and the `system` / `journey` special sheets need the
  sequential visual decisions in `companion-ui-visual-acceptance-manifest-20260717.json`.
- Owner feedback says some expressions are truncated at the lower edge. This
  is an open P0 failure until both the 4 px frame-margin gate and the real-panel
  observation below pass.
- The SSD1681 waveform route is frozen. No refresh-speed acceptance item runs
  until a matching vendor CWF1 package is verified.

## Ordered Acceptance Items

### G1: Protected Behavior And Build Boundary

- Machine gate: run the historical branch audit, low-power policy host test,
  touch gesture host test, v9 resource-binding test, SPI-NOR self-test, strict
  WBA adapter compile, normal WB55 build, and `git diff --check`.
- Pass: the retained branch refs are unchanged; first tap blocks Stop until
  double-tap resolution; default idle is 180000 ms; the menu has exactly four
  roots; v9 is external/inactive with no fallback; the WB55 build and WBA
  callback-only boundary pass.
- Fail: any historical-art reactivation, procedural face, Record menu shortcut,
  missing source/hash evidence, or a build/host failure. No operator popup is
  opened for this machine-only item.

### G2: Visual Source Decisions (Three Sequential Items)

For each item, inspect the listed 200x200 deterministic preview at normal
scale, compare it with the locked v9 identity, then record one decision and an
optional note. Approval authorizes only a later PBM/CEMP import proposal, never
a firmware flash by itself.

- Machine precondition: the visual-reference ledger audit must cover exactly
  the v9 expression, four-root menu and special-state feature families, with an
  exact prompt, reference/output hashes, durable request record, review state
  and next-prompt delta for every candidate. Historical rejected metadata may
  remain only as non-reusable history; it can never become an art source.
- Every G2 popup must take its target, operator action, success signal, failure
  rule, continue condition and recovery condition from the matching manifest
  item. A `通过` records the stated visual-source decision only; it cannot
  override the P0 panel gate or activate a runtime resource.
- Use `tools/run_companion_goal_visual_source_acceptance.ps1` as the only G2
  popup entry: `-CheckOnly` and `-SelfTest` must not open a window; only an
  explicit owner `开始验收` followed by `-Execute -OwnerStartAcknowledged` may
  open the next sequential item. Its result stays beside the matching source
  evidence and must be triaged before a manifest decision or the next item.

1. `menu-v6-four-root`: Voice, Device, Connection and Preferences must be the
   only roots; both English and Chinese overlays must be readable and every row
   must correspond to a real/deferred action.
2. `special-system-v1`: speaking, recording error, charge/charging/charged,
   low battery, pairing/link and system-error states must retain the v9 eye,
   brow, mouth and cheek identity. The current lower-edge truncation feedback
   is unresolved. Inspect the locked-source special-state crop preflight at
   normal 200x200 cell scale: every crop must retain >=4 px canvas clearance,
   but this source-only proof does not clear the focused G5 panel recheck.
3. `special-journey-v1`: menu entry/settle/blocked/exit and upgrade
   offer/prepare/transfer/verify/restart/success/error/recovery must use the
   same v9 grammar and remain distinct enough to communicate state.

### G3: Renderer And External Resource Chain

- Machine gate: render from the locked v9 source, then prove 39/39
  PBM-to-CEMP decode equality, source-to-PBM geometry, scene coverage, CEMP
  identity, and the new 4 px frame-safe-area report.
- Pass: exactly 39 frames / 13 clips are byte and pixel verified; all 40
  portable scene families are either exact v9 candidates or explicitly pending
  with no fallback; no frame has ink closer than 4 px to an edge.
- Fail: any source hash drift, missing frame, old asset fallback, edge ink,
  CEMP activation, Flash write, or firmware flash.

### G4: Four-Root Menu Function And Physical Presentation

- Precondition: G2 menu source approved and the separately reviewed resource
  import proposal accepted. Before that, run only the five host menu replays.
- Hardware action: enter the menu, inspect the four roots, open one detail row
  per root, return, switch language, and repeat the home/detail check.
- Pass: Voice, Device, Connection and Preferences are the only home roots;
  all labels are one language at a time; every row reports a real value/action
  or clearly deferred state; no clipped lower text or stale prior page remains.
- Fail: six-root/two-page UI, fake chevron, mixed language, empty action,
  stale generation, or any clipped content.

### G5: WB55 Panel, Touch, And Low-Power Reality

- Machine precondition: normal product-equivalent WB55 image preflight, the
  39-frame v9 4 px safe-area report, the 24-frame special-state crop preflight,
  and the exhaustive SSD1681 transform/window mapping report must pass for all
  40,000 pixels. These prove only source pixels remain in-bounds; they do not
  clear a real-panel viewport or lower-edge defect.
- Hardware precondition: FTS02 panel health and a bounded hardware lock. Do
  not use a trace-only image that lacks the normal SSD1681 configuration.
- Hardware action: show each available daily v9 clip; inspect all four display
  edges, especially the lower edge. Then perform three independent tap/swipe/
  three-second-hold cycles and a 3-minute idle-to-Stop-to-one-touch-wake cycle.
- Pass: every requested gesture has one matching touch event and visible
  response; a hold enters menu only near three seconds; short taps/swipes do
  not enter menu; the low-power pose is static; `TP_INT` wakes the application;
  no face/charm/text is truncated at the bottom or any other edge.
- Fail: missed/repeated gesture, accidental menu entry, no wake, periodic sleep
  refresh, clipped visual, mixed old/new frame, or missing reset-bounded log.

### G6: Double-Tap Recording And External-Flash Store

- Precondition: G5 touch health passes and the shared Denzic Platform recording
  core is the linked implementation.
- Hardware action: run three complete sessions. For each one, double tap to
  start, speak for a short interval, double tap to stop, and wait for saved or
  an explicit error/recovery state.
- Pass per session: two `double_tap` events; SAI clock restored; DMA starts;
  at least two changing PCM blocks without timeout/overrun; stop commits before
  display work can steal touch; DMA stops; external-Flash `user_store result=1`
  is present; visible start/active/saving/saved feedback matches the state.
- Fail: missing second double tap, no visible state, accidental menu entry,
  timeout, unchanged PCM, overrun, no store, or a later session that cannot
  restart cleanly.

### G7: Refresh, Residue, And Waveform Gate

- Before CWF1: accept only generation coherence and no-fallback checks. Do not
  try generic, adjacent-panel, guessed, online, or hand-authored LUT bytes.
- After a matching CWF1 package passes panel, batch, temperature, CRC and source
  checks: under one bounded hardware lock, test the named candidate on the
  declared temperature condition.
- Pass: no unacceptable afterimage has priority; only then record the measured
  refresh duration against the 0.5 s target. A physical result must identify the
  exact waveform package and panel condition.
- Fail: any source mismatch, missing package field, visible old/new mixing,
  unacceptable residue, or unbounded experimental loop.

### G8: WBA55/WBA65 Board Parity

- Precondition: a selected WBA board, CubeWBA project, SPI-NOR pins, panel,
  touch wiring and clock plan. Callback-only M33 compile evidence does not count
  as board parity.
- Hardware action: repeat the smallest G4, G5 and G6 successful paths on the
  selected board, including external-NOR mount/CRC/read and touch wake.
- Pass: selected target build, real JEDEC/read/program/erase evidence, panel
  and touch logs, resource mount, low-power trace, and focused visual result all
  agree. The final product board alone may close the <=1 mA average over >=60 s
  standby-current target.
- Fail: missing CubeWBA target facts, substituted WB55 logs, no real panel or
  touch evidence, or a current claim from the development board.

## Result Recording

Each completed item stores its machine logs, exact image/source hashes, popup
archive/result, operator note and any physical capture next to the matching
validation artifact. `PASS` is permitted only when every listed pass condition
has evidence; otherwise record `FAIL`, `PENDING`, or `DEFERRED` with the
specific missing gate.
