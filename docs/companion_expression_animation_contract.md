# Companion Pet Expression Animation Contract

## Purpose

Companion faces are performances, not sticker swaps. A state owns a small,
event-driven whole-face performance family stored in external Flash:

`entry -> sustained -> settle or exit/recovery`

Each frame changes a coordinated set of features: paired eye/highlight position,
paired brow pose, mouth, cheek dots, gentle whole-face lean, and the semantic
charm. A charm changing alone is not animation.

## E-Paper Cadence

- A scene uses two or three frames, never a fast loop.
- `entry` is requested only after the real product event commits.
- `sustained` remains static during deep sleep, charging, menu presentation,
  and touch-originated recording unless a separately measured asynchronous
  target can prove gesture servicing remains intact.
- `settle` or `exit` is requested only on a real outcome, cancellation,
  recovery or new higher-priority scene.
- Each request carries the scene generation. The queue may discard stale work,
  but one visible transaction may not mix generations.

## First Motion Storyboard

The retained v10 storyboard is historical only; it is not a current art source
or a CEMP candidate. The sole active source is owner-selected v9. Before any
motion art is generated, choose one named v9 state and one named visible motion
variable under the v15 in-context route, then obtain an owner decision. A later
approved motion family remains a three-frame performance, not three unrelated
faces.

| Story | Frame 1 | Frame 2 | Frame 3 |
|---|---|---|---|
| Daily touch | calm notice | curious lean-in | affectionate happy settle |
| Menu entry | long-hold upward anticipation | soft decision lift | calm handoff as menu opens |
| Double-tap recording | record-start attention | bright listening active | focused saving handoff |
| Sleep / wake | sleepy settle | gentle deep-sleep rest | touch-wake bright opening |

After a v9-derived interaction performance has an approved source-to-PBM/CEMP
mapping, a separate system-status sheet may reuse the same choreography for
charge detected -> charging -> full, low battery -> charge request -> recovery,
pairing -> syncing -> linked, OTA offer -> coarse progress -> outcome, and
error -> recovery -> settle.

## Portable Binding

The portable scene layer chooses state family, phase and generation from real
recording, menu, power, link and OTA events. WB55/WBA adapters only choose panel
waveform, timer and storage mechanics. The current CEMP revision remains active
until an owner-selected generated source has a REF/PBM comparison, a CEMP mount
check and a target runtime trace.

## Committed Event Bridge

`pet_performance_event_bridge.*` turns accepted portable expression signals and
precise product interactions into `scene + phase + generation + resource_family`
metadata. WB55 logs the resulting frame after the real event commits; WBA55/WBA65
reuse the same module. The bridge does not load a PBM, select CEMP content or
ask a panel to refresh.

- Recording start, stop and finish map to `recording.start`, `recording.saving`
  and `recording.saved`; cancel/recovery returns to idle.
- Wake detection and speaker prompt map to `voice.listening` and
  `voice.speaking`. A generic speaker result is deliberately not mapped because
  the WB55 touch path supplies the exact tap or swipe event instead.
- Daily taps/swipes, clean menu entry/exit, and low-power entry use exact event
  names so their future v9-derived art can stay semantically distinct. Once the
  clean screen handoff has committed daily presentation, menu exit explicitly
  recovers to `daily.idle`; the next daily gesture therefore cannot remain
  blocked behind menu priority.
- Low battery may preempt active work; battery recovery returns through idle.
  Error selects a recording error only when the portable scene is in the
  recording journey, otherwise it selects a system error.

This is a semantic and logging boundary only. No v9 frame is visible until its
state-specific owner-approved REF/PBM/CEMP comparison has passed.
