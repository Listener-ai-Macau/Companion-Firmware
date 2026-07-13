# Companion Menu Information Architecture

Design source: `docs/art/iterations/companion-menu-v2/iteration-ledger.json`.
The active visual candidate is `menu-v3-2026-07-13`; it is not eligible for
firmware resources or hardware flashing until its review outcome is accepted.

| Page | Visible rows or controls | Product owner and current behavior | State |
|---|---|---|---|
| Settings home | Voice, Status, Phone Link, Device, Preferences, About | Six existing `screen_menu` destinations; selection uses press-cue then target arrival. | Implemented, visual redesign pending |
| Voice | Mic state, double-tap recording hint, recent recordings | Daily-page double tap is the only default recording command and uses the real recording FSM plus external Flash path. This page shows real state/history only; it has no duplicate start/stop button. Wake word is deferred for low-power work. | Recording gesture implemented; visual redesign pending |
| Status | Display, touch, BLE, voice record, low-power eligibility | Read-only live flags from panel readiness, FT6336 health, BLE link, recording FSM, and the current Stop-mode blocker summary. | Implemented data path; low-power row visual pending |
| Phone Link | Advertising, paired/connected state, reconnect | Advertising and connection are real BLE states. A user retry action must call the BLE advertising request path and report its result. | State implemented; retry action backlog |
| Device | E-paper profile, touch health, external assets, battery | Profile, touch flag, and CEMP external-pack mount are live product facts. Battery has no devboard hardware path. | Three facts implemented; battery blocked |
| Preferences | Language, gesture behavior, refresh cleanup | Language switches the complete Chinese/English resource set. Gesture and cleanup describe the actual fixed product policy; they must not look editable until their persistence/action exists. | Language implemented; policy rows read-only |
| About | Firmware, UI asset revision, OTA, diagnostics | UI asset revision comes from the active CEMP. OTA remains frozen by SCR-14. Diagnostics needs an explicit bounded user flow before becoming a control. | Asset revision implemented; diagnostics backlog |

No page may render a sample device name, battery percentage, recording count, or
connection result as if it were live. The visual renderer receives only the
states that its target owner provides. Any row not backed by data or an action
is either omitted or marked planned and tracked in the project backlog.
