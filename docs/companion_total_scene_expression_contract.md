# Companion Total Scene Expression Contract

## Purpose

This contract turns the Companion's three priority product flows into living
whole-inner-face scenes. It uses the existing portable expression event bridge,
pet behavior layer, emote player, and external CEMP resource store. It does not
introduce a second recording or OTA state machine.

The physical enclosure owns the cat silhouette. Scene art contains only the
inner face: eyes, brows, nose/mouth, cheek dots, gaze, and sparse marks. A
scene is not a fixed sticker: every scene has an entry pose, a low-frequency
e-paper-safe sustained pose, and an exit or recovery pose that is selected by a
real product event.

## Art Baseline

- The sole active art source is owner-selected
  `docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png`
  (`919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA`).
- Its exact 3 by 4 canvas, state order, whitespace and inner-face grammar are
  locked by `COMP-REQ-053` and
  `docs/art/iterations/companion-pet-expression-v15-style-lock/iteration-route.json`.
  Later candidates are retired from active routing; no historical source may
  return as a fallback.
- A scene-specific change is an in-context local retouch of one named visual
  variable on the v9 canvas. It requires its own source hash, unchanged-region
  lock, before/after comparison and explicit owner decision before it can seed
  the next round or a CEMP resource.
- The owner selection is a visual-source decision, not an asset activation.
  CEMP revision 53 remains active until a specific v9-derived state has passed
  REF/PBM/CEMP comparison and external-Flash pack verification.
- New frames retain v9's upright paired black oval eyes with white glints,
  detached rounded brows, petite nose/W-mouth, cheek dots, white background
  and sparse semantic marks. They may not add a cat head, ears, whiskers, a
  device outline, shading or gradients; black eyelid arcs may not touch or hug
  an open eye.

## Scene Arbitration

1. `error_recovery` is highest priority and exposes the real product failure.
2. `recording` owns the face from a committed record start until stop/cancel,
   store result, or recovery. Pet input and menu entry cannot replace it.
3. `upgrade` owns the face only after a real OTA adapter/replay event is
   committed. OTA transfer blocks recording and menu mutation according to the
   shared OTA policy.
4. `menu` owns the entry/selection/exit scene while no recording or OTA scene is
   active.
5. Daily pet behavior owns the remaining idle time.

Each transition carries a monotonically increasing scene generation. The screen
queue may coalesce stale work, but may not show frames from two scene generations
in one visible transaction. On current synchronous e-paper, a sustained scene
uses sparse keyframes and must not run a periodic refresh while recording touch
control is active.

`pet_performance_event_bridge` provides the host-testable scene-event boundary
for the three journeys. Its upgrade events are named `upgrade_*` replay metadata
only: they select a portable scene and never invoke Denzic OTA, storage erase,
external-Flash provisioning, target reset, or panel refresh. Recording events
remain event observations of the shared Denzic Platform recording lifecycle;
the bridge neither starts nor stops DMA. Resource activation remains disabled
until the v9 state-specific REF/PBM/CEMP review gate is passed.

## Priority Scenes

| Scene key | Real event boundary | Entry | Sustained state | Exit / recovery | Initial resource status |
|---|---|---|---|---|---|
| `upgrade.offer` | OTA adapter reports an eligible offered component | curious face with down-arrow mark | none; waits for user decision | dismiss -> daily; reject/error -> `upgrade.error` | storyboard reference; implementation pending |
| `upgrade.prepare` | accepted package passes preflight | focused face with gear/spark | none | start transfer -> `upgrade.transfer`; preflight fail -> `upgrade.error` | storyboard reference; implementation pending |
| `upgrade.transfer` | target OTA adapter reports transfer progress | determined face | three-segment progress mark changes only at coarse milestones | verify -> `upgrade.verify`; interrupted -> `upgrade.error` | replay-only until Listener OTA acceptance |
| `upgrade.verify` | target OTA adapter reports integrity verification | attentive face with check/spark | none | activate -> `upgrade.restart`; mismatch -> `upgrade.error` | replay-only until Listener OTA acceptance |
| `upgrade.restart` | target OTA adapter has committed a restart | soft closed-eye smile with restart mark | static handoff frame | next boot -> `upgrade.success` or `upgrade.error` | replay-only until Listener OTA acceptance |
| `upgrade.success` / `upgrade.error` | target OTA adapter reports outcome | happy sparkle / honest worried face | one short settle | return -> daily/status | replay-only until Listener OTA acceptance |
| `recording.start` | shared Denzic Platform recording core commits start | wide attentive eyes and record dot | none | active -> `recording.active`; reject -> `recording.error` | existing recording hook; new art pending |
| `recording.active` | PDM/DMA capture is running | listening face with small sound arcs | two or three sparse frames, never a fast loop | second double tap -> `recording.saving`; transport fault -> `recording.error` | existing listening assets can be fallback only |
| `recording.saving` | shared recording core commits stop/finalize | focused saving face with dot trail | none | store result -> `recording.saved` or `recording.error` | storyboard reference; implementation pending |
| `recording.saved` / `recording.error` | storage result or recovery state | happy sparkle / honest worried face | one settle frame | return -> daily | existing finished/error hook; new art pending |
| `menu.hold` | gesture core commits a valid 3 s hold candidate | upward glance and ellipsis | none | release/cancel -> daily; decision -> `menu.enter` | storyboard reference; implementation pending |
| `menu.enter` | menu transition is committed | lifted brows and one sparkle | none | menu page ready -> `menu.open`; error -> `menu.error` | storyboard reference; implementation pending |
| `menu.open` | menu presentation becomes active | calm neutral face with corner marks | static boundary; menu UI is the next surface | row press -> `menu.press`; right-swipe -> `menu.exit` | existing menu presentation; new transition art pending |
| `menu.press` | a real enabled row is committed | gaze toward selected side and filled mark | none | detail visible -> menu UI; blocked row -> `menu.error` | storyboard reference; implementation pending |
| `menu.exit` / `menu.error` | right-swipe exit or declared action error | relaxed happy face / honest worried face | one settle frame | return -> daily or retained menu | existing exit hook; new art pending |

## Total Scene Acceptance

This overlay is modeled after Listener's product-flow and LED-priority reviews.
It does not replace ACPT-04, ACPT-05, ACPT-07, or ACPT-11; it groups their
visible behavior into three end-to-end scenes.

| Order | Item | Machine proof | Focused human observation |
|---|---|---|---|
| 1/15 | Upgrade offer and prepare | deterministic OTA replay emits `offer -> prepare` with one scene generation per beat | the face shifts from curious offer to focused preparation without old face residue |
| 2/15 | Upgrade transfer milestones | replay emits coarse `0/50/100` transfer milestones without high-rate redraw | progress feels deliberate, not like a fast spinner |
| 3/15 | Upgrade verify and restart | replay emits `verify -> restart` and records OTA policy ownership | verification/check and restart handoff are distinct |
| 4/15 | Upgrade failure/recovery | invalid/interrupted replay emits an honest error and returns safely | no false success face |
| 5/15 | Upgrade real-device gate | Denzic OTA component evidence and recovery log | deferred until Listener OTA acceptance explicitly unfreezes OTA |
| 6/15 | Recording start | two-tap trace commits shared recording start before display service | start face appears once and does not steal the second tap |
| 7/15 | Recording active | bounded PCM/DMA trace and sparse-keyframe schedule | alive listening face, with no fast flicker |
| 8/15 | Recording saving and saved | stop/store result binds saving then saved/error | saving and saved are visibly different |
| 9/15 | Recording failure/recovery | rejected/write-failure trace leaves next capture usable | honest error, then recovery without a stale recording face |
| 10/15 | Recording complete product flow | two double taps, changing PCM, zero overruns, external-Flash store | one complete spoken recording scene |
| 11/15 | Menu hold anticipation | valid 3 s hold trace emits hold then enter once | anticipation reads as a living reaction, not a sticker |
| 12/15 | Menu opening | menu presentation commit follows `menu.enter` generation | decision pose clearly leads into the menu |
| 13/15 | Menu item press | enabled row action emits press only after row commit | selected row and face agree on the action |
| 14/15 | Menu exit settle | right-swipe exit trace has exactly one menu-to-daily boundary | return feels intentional, with no extra flash or old menu frame |
| 15/15 | Menu blocked/recovery | disabled/error row emits real error and preserves a usable menu | no fake success or accidental exit |

The canonical popup title is `Companion 总场景验收 N/15 (本次 M/K)`. It shows
one action and one expected signal at a time, persists the machine artifact and
operator result together, and only opens after the owner says `开始验收`.

## Portability And Storage

- Scene keys, event mapping, arbitration, generation, and acceptance schema are
  portable C/product contracts.
- WB55/WBA target adapters supply display scheduling, timers, physical pins,
  OTA transport, and resource-store access.
- All generated frames, prompt ledgers, CEMP packs, and future OTA/model assets
  are external-Flash first. Internal Flash holds code, parsers, and a compact
  rescue surface only.
- A new display profile requires generated source art, a profile-specific CEMP
  pack, host render proof, and its own target acceptance; it must not inherit a
  200x200 visual PASS by name alone.
