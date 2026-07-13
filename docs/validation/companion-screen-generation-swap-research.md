# Companion Screen Generation-Swap Research

Status: product rule input for SCR-17.

2026-07-13 update: the user reported this as a recurring product-quality
problem, not a one-off screen bug: "总是有新旧交织的问题". Treat every
repeat as SCR-17 until proven otherwise. The first triage question is whether
the old content is a faint physical afterimage or a recognizable stale product
generation. Recognizable old art, old menu layout, old procedural face, old
sheet crop, or old framebuffer content is never acceptable as an e-paper
limitation.

## Why This Exists

The "old/new mixed together" issue has two different causes that must not be
debugged as one bug:

- Physical e-paper ghosting: old pigment state remains visible after partial or
  fast refresh.
- software generation interleaving: old CEMP resources, old menu frames, old
  procedural faces, stale framebuffers, or stale queued requests are displayed
  after a new art revision has been selected.

The product rule is to separate them. A new art pack must be activated as one
generation; stale queued frames from the old generation must be drained or
discarded; then the panel baseline must be refreshed or maintained through the
refresh policy. New art must never cover over old art as a transition trick.

## External Research Notes

- Pervasive Displays explains that global update, fast update, and partial
  update have different speed and image-quality tradeoffs. Their comparison
  calls out ghosting risk for partial update, and describes fast update as using
  optimized waveforms for better optical quality.
- Good Display's GDEY0154D67-T03 product page confirms this exact 1.54 inch
  200x200 SSD1681 touch panel supports partial refresh and 4 grayscale. The
  product can be fast, but it is still an electrophoretic panel with waveform
  and afterimage constraints rather than an OLED-class surface.
- Good Display's FAQ treats full-refresh flicker as the normal afterimage
  removal process, warns that shortening refresh time can increase ghosting, and
  points to waveform matching as a core display-quality factor.
- Good Display's partial-refresh FAQ also recommends a black/white full-screen
  cleanup after several partial or fast updates, and says multiple partial
  regions should be written first and then updated together. For Companion this
  maps to "merge and commit the latest coherent frame", not "show a sequence of
  half-old frames".
- Good Display's public usage guidance also treats full update cadence and
  deep sleep as operating rules, not last-minute visual hacks: partial updates
  need bounded cleanup, and long idle intervals should leave the panel in a
  settled state. For Companion this means touch interaction can be fast, but
  the cleanup belongs after interaction settles, with one explicit baseline or
  maintenance path.
- Current e-paper product guidance from vendors and paper-tablet makers frames
  ghosting as a waveform, temperature, voltage, and refresh-cadence problem.
  Mature products expose this as a controlled refresh policy rather than letting
  old UI layers leak through. Companion must therefore diagnose "old art still
  visible" as either physical afterimage or stale generation playback before
  changing artwork.
- The 2026-07-13 re-check found the same pattern in current e-paper UX guidance:
  products expose content-specific refresh modes, manual/full refresh triggers,
  and firmware waveform improvements. They do not treat recognizable old UI
  generations as acceptable "ghosting". Companion therefore needs a visible
  product gate for stale-generation prevention in addition to the panel refresh
  profile.
- Mature reader/tablet behavior maps to three Companion modes: interactive
  dirty-window refresh while the finger is active, a low-flicker maintenance
  pass after the interaction settles, and an explicit full baseline reset only
  when the baseline is unknown, the view changes radically, or residual
  afterimage exceeds the product threshold. None of these modes may replay old
  resource revisions.
- Redis' cache invalidation guidance frames stale data as a consistency problem:
  old cache entries must be invalidated when the source changes, otherwise users
  can keep seeing outdated state. For Companion, the active CEMP revision is the
  source-of-truth version for all normal screen art.
- Version-based invalidation practice treats each mutable resource version as a
  freshness fingerprint. When the resource changes, the version changes, and
  consumers must fetch or display only the matching generation.
- Double-buffering practice separates "what the user is looking at" from "what
  the renderer is still drawing", then commits only a complete frame. Companion
  cannot afford arbitrary full-screen buffer stacks on every future target, but
  it must keep the same rule: users should see a completed current-generation
  frame, not a mixture of old queue entries, old procedural fallbacks, and new
  generated art.

Sources checked on 2026-07-13:

- https://www.pervasivedisplays.com/how-e-paper-works/fast-update-refresh/
- https://www.good-display.com/product/258.html
- https://www.good-display.com/news/79.html
- https://www.good-display.com/news/80.html
- https://www.good-display.com/news/134.html
- https://www.geniatech.com/solution/e-paper-refresh-technology/
- https://viwoods.com/blogs/paper-tablet/e-ink-ghosting-explained
- https://redis.io/glossary/cache-invalidation/
- https://oneuptime.com/blog/post/2026-01-30-version-based-invalidation/view
- https://wiki.osdev.org/Double_Buffering

2026-07-13 current web re-check for the recurring "new/old interleaving"
complaint:

- Mature e-paper guidance does not promise OLED-like replacement. It separates
  global/full refresh, fast refresh, and partial/window refresh, then lets the
  product choose a mode by content and interaction. The common pattern is:
  fast/partial while the user is interacting, periodic or manual full cleanup
  when residue becomes visible, and firmware/waveform tuning for panel-specific
  quality.
- Good Display guidance repeatedly points to bounded partial-update use and a
  full/black-white cleanup after several partial or fast updates. This supports
  Companion's "one quiet maintenance pass after interaction" rule, but it does
  not justify showing an old art generation as a transition.
- Paper-tablet style products expose refresh modes or manual refresh triggers.
  That is a user-facing acknowledgement that physical afterimage is managed by
  refresh policy. It is not a license for stale UI layouts, stale generated
  faces, or old fallback art to remain recognizable.
- Current cache/versioning practice uses versions as freshness fingerprints:
  when a resource version changes, cached data from the previous version is
  stale and must be invalidated. For Companion, the CEMP revision and pack CRC
  are the screen-art freshness fingerprint.
- Device update practice uses a manifest/package identity for components that
  can update independently. For Companion, future `ui_assets` OTA must update
  the resource manifest, payload, CRC/signature, active revision, display queue,
  and first coherent frame as one product transaction.

Product conclusion: "新旧交织" is a release-quality item, not a visual nit.
Every candidate build must prove both sides: physical residue is controlled by
the refresh profile, and software generations are controlled by versioned
assets, queue invalidation, and coherent-frame commit.

2026-07-13 live web check conclusion for product backlog wording:

- Pervasive Displays separates global, fast, and partial update modes and says
  fast/partial updates are a UX tool with optical-quality tradeoffs. That maps
  to a panel refresh profile decision, not an art-generation transition.
- Good Display's update-mode guidance says partial/fast refresh can leave
  ghosting and recommends a full cleanup after several partial/fast updates.
  That supports bounded cleanup cadence; it does not make recognizable old UI
  acceptable.
- Standard double-buffering guidance keeps the displayed/front image stable
  while drawing into a back buffer, then exposes only the completed frame. On
  STM32 targets with tight SRAM, Companion may implement this with tile
  composition or a single full framebuffer plus queue generation tags, but the
  product rule is the same: never show a half-new/half-old frame.
- Therefore SCR-17 is a product backlog item for every release candidate:
  if the reviewer can identify an old face style, old menu shape, old prompt
  crop, old fallback renderer, or old framebuffer content, the failure is
  `stale_generation_content` until proven to be only physical afterimage.

2026-07-13 recurring-issue web re-check, written as a product project item:

- Pervasive Displays' current fast/partial refresh guide separates global,
  fast, and partial update modes, and calls out ghosting risk as an optical
  refresh tradeoff. This supports a refresh-profile knob, not a license to show
  old Companion art while new art is active.
- Good Display / buy-lcd FAQ guidance says partial/fast ghosting is improved by
  periodic full black-white cleanup, longer intervals, and unified update of
  multiple partial regions. This maps to Companion's "merge latest coherent
  frame, then one maintenance/baseline action" rule.
- Embedded Wizard and SEGGER both describe the mature GUI pattern as keeping a
  visible/front buffer stable while drawing into a hidden/back buffer, then
  swapping only after the frame is complete. On WB55/WBA this can be implemented
  as full framebuffer, tile compose, or one framebuffer plus generation tags,
  but the user-visible rule stays the same.
- Product decision: SCR-17 must remain in the project plan until the current
  release candidate proves no stale generation. It is not closed by improving a
  single firmware build, because the same risk returns whenever prompt art,
  menu art, screen profile, external Flash assets, or OTA resources change.
- Acceptance wording for the project item: "If a human can recognize a previous
  face/menu/style, classify it as stale_generation_content first. Only faint,
  non-identifiable pigment residue can be treated as physical afterimage."

Sources rechecked for this product item:

- https://www.pervasivedisplays.com/how-e-paper-works/fast-update-refresh/
- https://www.good-display.com/faq/1.html
- https://buy-lcd.com/blog/e-paper-display-faq-33
- https://doc.embedded-wizard.de/framebuffer-concepts?v=12.00
- https://kb.segger.com/emWin_Multi-Buffering

## Product Requirements

1. `ui_assets` CEMP activation is atomic at the revision level.
2. The display queue carries the active resource revision on every request.
3. On revision switch, pending requests from the old revision are drained or
   discarded before new product frames are accepted.
4. Normal product rendering uses only the active revision; rescue/procedural
   fallback is allowed only in explicitly named rescue or maintenance paths.
5. The renderer commits only complete current-generation frames. Intermediate
   draw steps, old fallback faces, and old menu frames may never be used as a
   visible bridge while new art is being generated or activated.
6. Physical ghosting is handled by the panel refresh policy: differential
   partial refresh during interaction, a single quiet maintenance refresh after
   contact settles, and full refresh only for unknown baseline or fault recovery.
7. The acceptance index must keep this as a product item, not a temporary bug
   note, because future prompt/art/menu swaps will repeat the same failure mode.
8. Every generated-art prompt swap, menu art swap, screen-size profile swap, or
   future `ui_assets` OTA must pass this generation hygiene gate before human
   visual review: one active revision, no stale queue playback, no old
   procedural product frames, and one explicit panel baseline/maintenance path.
9. UX reviews must record whether a visible old mark is physical ghosting or
   stale-generation content. Physical ghosting is tuned in the panel profile;
   stale-generation content is a product P0 queue/resource bug.
10. This stays on the product project list until the full art pipeline can
    prove an atomic swap from one generated baseline to the next: import,
    contact-sheet review, pack revision bump, external Flash activation, queue
    drain, coherent first frame, and post-interaction maintenance refresh.
11. Future WBA55/WBA65 ports inherit the same rule. A smaller SRAM target may
    implement tile composition instead of two full buffers, but it must still
    preserve front-stable/back-compose/atomic-commit semantics.
12. The product project must carry SCR-17 as a named release/backlog item, not
    only as a verifier note. A candidate release cannot be called visually ready
    if SCR-17 has no ledger entry for source art, CEMP revision/CRC, active
    generation, stale-discard count, first coherent frame, and old-mark triage.

## Mature-Product Playbook

This is the product-level rule to copy, not a one-off repair:

1. Treat the selected art pack revision as the only product source of truth.
   Prompt changes, menu redesigns, screen-profile changes, and OTA `ui_assets`
   swaps all create a new generation.
2. Build the next generation off-screen. Do not show transitional procedural
   faces, old menu PBMs, old sheet crops, or half-rendered frames as a bridge.
3. Activate the new generation atomically, then drain or discard pending display
   requests from earlier generations before accepting new product requests.
4. Commit only a complete coherent frame from the active generation. If memory is
   too tight for two full screen buffers on a later target, the implementation
   still needs equivalent front-stable/back-compose semantics.
5. During touch or animation, coalesce to the newest current-generation frame
   and avoid replaying stale queued frames. It is better to skip an old frame
   than to show a mixed-generation frame.
6. Handle true e-paper ghosting separately with the panel refresh profile:
   bounded partial/fast refresh, one quiet maintenance refresh after interaction,
   and full refresh only for unknown baseline or fault recovery.
7. If a reviewer sees old style mixed with new style, first classify it:
   physical afterimage goes to refresh/profile tuning; recognizable old assets
   or old layout go to the generation hygiene bug path.
8. Keep the product project item open across releases. Every candidate build
   must show whether the visible old mark is pigment afterimage, stale queued
   frame, stale asset revision, or rescue/procedural fallback leakage.
   In acceptance notes this exact triage family is: physical afterimage, stale
   queued frame, stale asset revision, or rescue/procedural fallback leakage.

## Project Tracking Rule

SCR-17 is the recurring "new/old visual interleaving" product item. It must
remain visible in the project plan alongside screen feel, touch, generated art,
external Flash, and OTA. Do not close or hide it merely because one revision
looks better. It can only move from "pending hardware recheck" to "accepted" for
a release candidate after evidence shows:

- a generated-art revision swap does not display old procedural product art;
- a menu-art revision swap does not replay old menu frames;
- queued display requests from the previous revision are drained or discarded;
- the first visible frame after activation is a coherent current-generation
  frame;
- any residual physical afterimage is handled by the refresh profile rather
  than by mixing old and new art.
- candidate release notes name the active CEMP revision, queue stale-discard
  count, first coherent frame marker, and maintenance/full-baseline decision.
- the product project plan still lists SCR-17 as the named recurring
  "new/old visual interleaving" item, so future prompt, menu, screen-size,
  external Flash, or OTA changes cannot bypass it.

Release ledger entry required for every generated-art/menu/ui_assets candidate:

1. Source art identity: prompt/art board path, style name, target screen
   profile, CEMP revision, CRC, and compatible hardware family.
2. Activation evidence: manifest verified, external Flash payload selected,
   active revision set, old queued requests discarded, and no normal product
   path still points to old procedural art.
3. First-frame evidence: the first visible frame after activation reports
   `coherent_generation=1` and the serial log includes generation switch and
   stale-discard counters.
4. Panel evidence: the refresh decision says whether this was baseline,
   interactive partial/fast, maintenance, or fault recovery.
5. Human/visual note when acceptance starts: any visible old mark is classified
   as physical afterimage, stale queued frame, stale asset revision, or
   rescue/procedural fallback leakage.
