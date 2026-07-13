# Companion Function Acceptance Coverage

This is the durable acceptance coverage inventory for Companion. It applies
the workflow's focused-popup rule to this product; it is not a PASS record.
An item may be accepted only after its stated machine evidence and focused
operator observation agree.

## Session Contract

- Start a live session only after the owner explicitly says `开始验收`.
- Use exactly one Chinese popup at a time. It must state `N/12`, the target,
  the single action, the success signal, and what allows the next item.
- Close and triage the current popup result before opening the next one. A
  non-empty note is an implementation input, not an informal PASS.
- Use the Listener canonical `aiw operator-prompt` style for every real-time
  action. Its selection and notes must be persisted next to the matching
  serial/visual artifact, so accepted behavior becomes a regression contract.
- A product-visible modal, toast, confirmation, error, permission, or
  recovery surface is a separate acceptance item when that surface exists.

## Coverage Inventory

### ACPT-01: Boot, Panel, And External Resource

- Normal: normal firmware mounts the current CEMP pack from external Flash and
  performs one coherent first full refresh.
- Failure/recovery: an incomplete resource mount stays NO_GO; provision must
  restore normal firmware before any human check.
- Machine evidence: rev52 provision and normal serial logs, runtime promotion,
  and pre-acceptance health all PASS.
- Popup: `1/12` asks the operator to confirm one stable, correctly oriented
  generated inner-face frame with no old resource mixed in.
- State: rev52 machine evidence is PASS; the visual observation remains an
  independent focused item and is not inferred from the serial result.

### ACPT-02: TP_INT Stop Wake

- Normal: after daily idle queues one static external-Flash `sleepy` pose and
  Stop is allowed, one FT6336 touch on PC6 wakes the application, increments
  and consumes the IRQ, and produces a touch response. The Stop pose must not
  advance through periodic breathing refreshes.
- Failure/recovery: an absent, duplicate, or unconsumed IRQ remains NO_GO;
  I2C recovery or poll fallback must be logged instead of claiming low power.
- Machine evidence: a reset-bounded `--scope stop-wake` capture containing
  `[screen] low_power_idle pose=sleepy animation=stopped`,
  `[power] low_power_face request=sleepy animation=static`, `[power]
  stop=allowed`, a post-idle `irq>0` and `irq_consumed>0`, valid FT6336
  identity, exactly one boot marker, and one `[touch-irq]` line whose consumed
  count catches up to the observed count.
- Popup: `2/12` asks the operator to wait until the closed-eye low-power face
  settles, touch once, then confirm it wakes into a response without a reset,
  repeated full flash, or periodic sleep-frame flicker.
- State: first focused hardware item in the active session.

### ACPT-03: Double-Tap Recording And Visible State

- Normal: the first valid double tap starts touch-originated recording through
  a generated recording-start pose, then enters a low-frequency whole-inner-face
  recording loop. While recording, the next valid double tap exclusively stops,
  stores it in external Flash, and gives generated saving/saved feedback.
- Failure/recovery: rejected starts, write failures, or an interrupted stop
  must expose their real error/recovery surface and leave the next recording
  attempt usable.
- Machine evidence: a separate `--scope double-tap-recording` capture with
  two double-tap events, recording start/stop, and `user_store result=1`.
- Popup: `3/12` asks the operator to double tap twice and confirm generated
  start transition, an alive but e-paper-appropriate active loop, dedicated
  stop/save feedback, and no accidental menu entry.
- State: generated low-power wake, recording start, active, saved, and failed
  poses are COMP-REQ-009 work and must be imported before this item can close.

### ACPT-04: Three-Second Hold Menu Entry

- Normal: a near-still any-position hold gives the short tease response then
  enters the product menu at about three seconds.
- Failure/recovery: shorter presses and ordinary swipes must remain pet input;
  a cancelled hold must leave the daily face usable.
- Machine evidence: hold gesture, menu transaction, and no stale-generation
  frame in the display queue.
- Popup: `4/12` asks the operator to hold one location for three seconds and
  confirm tease, deliberate entry, and the menu entry feedback.
- State: follows ACPT-02 and ACPT-03.

### ACPT-05: Daily Pet Tap And Directional Stroke

- Normal: tap plus four stroke directions produce whole-inner-face responses
  while the physical shell remains responsible for the cat outline.
- Failure/recovery: an ambiguous gesture must not enter settings; a missed
  response is triaged against touch logs and the selected expression clip.
- Machine evidence: portable gesture and pet-behavior self-tests plus
  directional runtime events.
- Popup: `5/12` asks the operator to tap and swipe in four directions, then
  record the best and weakest visible response.
- State: pending focused visual review.

### ACPT-06: Menu Navigation, Language, And Product Surfaces

- Normal: drag follows the finger, a row gives its entry cue, back works, and
  Preferences switches the whole product between one Chinese or one English
  resource set.
- Failure/recovery: mixed language, a blocked action, or a page without its
  declared data/action stays open until fixed or explicitly deferred.
- Machine evidence: menu asset, presentation, and drag-continuity contracts.
- Popup: `6/12` asks the operator to drag, open one row, go back, then switch
  language and inspect both a home and detail page.
- State: pending focused visual review.

### ACPT-07: Refresh, Afterimage, And Generation Hygiene

- Normal: contact uses coalesced differential updates and one quiet cleanup
  only after release; old and new art never interleave.
- Failure/recovery: visible residue is classified as physical afterimage,
  stale queued frame, stale asset revision, rescue fallback, or stale content;
  a full refresh is reserved for baseline or recovery.
- Machine evidence: refresh policy, generation ledger, and runtime coherent
  generation markers.
- Popup: `7/12` asks the operator to finish one tap and one drag, wait two
  seconds, then count cleanup flashes and note any residue.
- State: pending focused visual review.

### ACPT-08: Microphone, Recording Store, And Speaker Feedback

- Normal: microphone capture, external-Flash recording, and the applicable
  recording/speaker response report their true state.
- Failure/recovery: no audio source, clipping, storage failure, or speaker
  disable must be observable and recover without corrupting a later capture.
- Machine evidence: bounded microphone quality, recording FSM, and storage
  logs; physical audio only when the relevant hardware is attached.
- Popup: `8/12` asks for one short audible input/output check when the audio
  fixture is available.
- State: hardware/fixture dependent.

### ACPT-09: Phone Link And Device Status

- Normal: the real BLE phone link and status pages show live connected,
  disconnected, and applicable transfer states.
- Failure/recovery: loss, rejection, or reconnect is shown as an honest state,
  not a stale success screen.
- Machine evidence: GATT and BLE bench logs for the selected host.
- Popup: `9/12` asks the operator to connect and disconnect once, then inspect
  the phone and status pages.
- State: pending Companion BLE bench gate.

### ACPT-10: External Resource OTA And Recovery

- Normal: a replaceable UI resource update is atomically mounted from external
  Flash without losing firmware or user data.
- Failure/recovery: interrupted or invalid assets remain inactive and normal
  rescue behavior stays reachable.
- Machine evidence: Denzic platform OTA component matrix and recovery logs.
- Popup: `10/12` asks for one post-update visual and data-retention check.
- State: deferred until Listener OTA acceptance unfreezes COMP-REQ-007.

### ACPT-11: Standby Current And Battery Product Gate

- Normal: the final product board averages no more than 1 mA for at least
  60 seconds under the declared standby conditions.
- Failure/recovery: a measurement outside the target is a power defect, not a
  reason to suppress wake or diagnostics.
- Machine evidence: timestamped current trace and Stop-resume trace on the
  final product board.
- Popup: `11/12` asks the operator to confirm the declared meter setup and
  recorded interval when the product board exists.
- State: devboard cannot close the final battery/current claim.

### ACPT-12: STM32WBA55/WBA65 Real Parity

- Normal: the selected WBA board uses the portable panel, touch, resource,
  power, and LSE boundaries with a real panel and touch result.
- Failure/recovery: missing CubeWBA project, LSE evidence, pins, or target
  logs remains a pre-port status, never WB55 equivalence by inference.
- Machine evidence: WBA build, panel, touch, BLE sleep, clock, and visual
  artifacts for the selected WBA55 or WBA65 board.
- Popup: `12/12` asks the operator to repeat the smallest affected WB55 check
  on the selected WBA board.
- State: deferred until board and CubeWBA project selection.
