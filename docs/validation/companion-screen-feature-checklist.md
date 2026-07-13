# Companion Screen Feature Checklist

This checklist is generated. Update it with `python .\tools\render_expression_feature_checklist.py --write`.

## Current Focus

- Overall status: `PENDING_HUMAN`
- Next gate: `wb55_rev51_runtime_recheck`
- Capability: `runtime_diagnostics_and_evidence`
- Focused gate: `wb55_rev51_runtime_recheck` (`DEFERRED_HARDWARE`)
- Touch visual acceptance packet: `docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.json`
- Pre-acceptance health: `docs/validation/companion-screen-pre-acceptance-health.json`
- Missing panel facts: `0`
- Next acceptance: Attach runtime snapshot and diagnostics bundle evidence to the first real-panel session.

## Capability Checklist

| # | Status | Capability | Next acceptance |
|---:|---|---|---|
| 1 | `PASS` | `expression_artwork_and_copy` | Keep visual/layout/copy contracts green when adding a new face or changing copy. |
| 2 | `PASS` | `screen_generation_hygiene` | Every new prompt/art/menu/profile/ui_assets revision must prove atomic activation, stale-frame draining, current-generation-only rendering, and post-interaction panel maintenance before visual review. |
| 3 | `PASS` | `portable_expression_model` | Append new signals only through the catalog, copy, priority, and journey fixtures. |
| 4 | `PASS` | `screen_demo_acceptance_flow` | Use the same demo order for WB55 real-panel photos and later extend the real BLE bench until no manual visual gaps remain. |
| 5 | `PASS` | `product_status_hooks` | Add each new product signal with a focused hook verifier and update the input source matrix. |
| 6 | `PASS` | `wb55_queue_and_host_status` | Use the same queue/status path for real-panel refresh and WBA scheduler parity. |
| 7 | `DEFERRED_HARDWARE` | `runtime_diagnostics_and_evidence` | Attach runtime snapshot and diagnostics bundle evidence to the first real-panel session. |
| 8 | `PENDING_HUMAN` | `panel_driver_readiness` | Operator confirms daily pet gestures, anywhere 3 s menu entry, press-cue/arrival partial refreshes, language switching, and that 0xCF maintenance is perceived as a single quiet flash. |
| 9 | `PASS` | `wba_migration_readiness` | Add a separate CubeWBA IOC/project and build wrapper before claiming WBA parity. |

## Current Missing Panel Facts

- None
