# Companion Menu Information Architecture

Design source: `docs/art/iterations/companion-menu-v2/iteration-ledger.json`.
`menu-v3-2026-07-13` is the owner-accepted visual implementation baseline. It
replaces the legacy CEMP menu treatment: its compact header, line icons, row
spacing, black selected row, detail-page dividers, and page-dot language must
be reproduced through replaceable external-Flash resources, not improvised in
the WB55 renderer. Every generated control remains subject to the real-action
rule below.

| Page | Visible rows or controls | Product owner and current behavior | State |
|---|---|---|---|
| Settings home | Voice, Status, Phone Link, Device, Preferences, About | The accepted v3 sheet fits all six destinations in one 200x200 home view. Selection uses the source-layout press cue then target arrival; normal CEMP no longer selects a retired scroll-frame asset. | menu-v3 resource import complete; hardware review pending |
| Voice & Record | Mic state, explicit recording control, recent recordings, wake-word state | Daily-page double tap remains the fast default. The generated-page recording control uses the same real recording FSM and external-Flash path, so it is not a decorative duplicate. Recent count appears only after it is backed by real metadata. Wake word remains explicitly planned until low-power acceptance. | Runtime action exists; menu-v3 resource mapping pending |
| Status | Display, touch, BLE, voice record, low-power eligibility | Read-only live flags from panel readiness, FT6336 health, BLE link, recording FSM, and the current Stop-mode blocker summary. | Implemented data path; low-power row visual pending |
| Phone Link | Advertising, paired/connected state, reconnect | Advertising and connection are real BLE states. The menu-v3 reconnect row remains visibly planned until it calls the BLE advertising request path and reports its result. | State implemented; retry action backlog |
| Device | E-paper profile, touch health, external assets, battery | Profile, touch flag, and CEMP external-pack mount are live product facts. Battery has no devboard hardware path. | Three facts implemented; battery blocked |
| Preferences | Language, gesture behavior, refresh cleanup | Language switches the complete Chinese/English resource set. Gesture and cleanup describe the actual fixed product policy; they must not look editable until their persistence/action exists. | Language implemented; menu-v3 resource mapping pending |
| About | Firmware, UI asset revision, OTA, diagnostics | UI asset revision comes from the active CEMP. OTA remains frozen by SCR-14. Diagnostics needs an explicit bounded user flow before becoming a control. | Asset revision implemented; diagnostics backlog |

No page may render a sample device name, battery percentage, recording count, or
connection result as if it were live. The visual renderer receives only the
states that its target owner provides. Any row not backed by data or an action
is either omitted or marked planned and tracked in the project backlog.

## Steering History

- 2026-07-13: the owner accepted `menu-v3-2026-07-13` as the replacement for
  the legacy menu. The former pending-review state is retained in the visual
  iteration ledger; it is superseded by this accepted implementation baseline.
- 2026-07-13: the accepted sheet visibly fits all six destinations on one
  200x200 home page. The normal external resource pack therefore maps home to
  one frame per language rather than retaining the legacy 43-frame scrolling
  renderer. Existing directional input remains available to the daily pet and
  detail-page back gesture; home scrolling may return only with a newly
  accepted reference and corresponding external resource sequence.
