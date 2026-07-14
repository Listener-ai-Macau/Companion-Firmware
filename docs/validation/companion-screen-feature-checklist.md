# Companion Screen Feature Checklist

This checklist is generated. Update it with `python .\tools\render_expression_feature_checklist.py --write`.

## Current Focus

- Overall status: `DEFERRED_HARDWARE`
- Next gate: `wb55_real_panel_refresh`
- Capability: `panel_driver_readiness`
- Focused gate: `wb55_real_panel_refresh` (`DEFERRED_HARDWARE`)
- Touch visual acceptance packet: `docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.json`
- Pre-acceptance health: `docs/validation/companion-screen-pre-acceptance-health.json`
- Current recovery evidence: `docs/validation/companion-screen-wb55-hardware-recovery-gate.json`
- Missing panel facts: `4`
- Next acceptance: Replace or cross-swap FTS02, prove solid white/black and valid PREVGH/PREVGL rails, then resume touch, gesture, language, and maintenance visual review.

## Capability Checklist

| # | Status | Capability | Next acceptance |
|---:|---|---|---|
| 1 | `PASS` | `expression_artwork_and_copy` | Keep visual/layout/copy contracts green when adding a new face or changing copy. |
| 2 | `PASS` | `screen_generation_hygiene` | Every new prompt/art/menu/profile/ui_assets revision must prove atomic activation, stale-frame draining, current-generation-only rendering, and post-interaction panel maintenance before visual review. |
| 3 | `PASS` | `portable_expression_model` | Append new signals only through the catalog, copy, priority, and journey fixtures. |
| 4 | `PASS` | `screen_demo_acceptance_flow` | Use the same demo order for WB55 real-panel photos and later extend the real BLE bench until no manual visual gaps remain. |
| 5 | `PASS` | `product_status_hooks` | Add each new product signal with a focused hook verifier and update the input source matrix. |
| 6 | `PASS` | `wb55_queue_and_host_status` | Use the same queue/status path for real-panel refresh and WBA scheduler parity. |
| 7 | `PASS` | `runtime_diagnostics_and_evidence` | Attach runtime snapshot and diagnostics bundle evidence to the first real-panel session. |
| 8 | `DEFERRED_HARDWARE` | `panel_driver_readiness` | Replace or cross-swap FTS02, prove solid white/black and valid PREVGH/PREVGL rails, then resume touch, gesture, language, and maintenance visual review. |
| 9 | `PASS` | `wba_migration_readiness` | Add a separate CubeWBA IOC/project and build wrapper before claiming WBA parity. |

## Current Missing Panel Facts

- Replacement or cross-swapped FTS02 board identity and wiring check.
- Deterministic solid-white and solid-black official one-plane frames with BUSY evidence after replacement.
- Established positive PREVGH1 and negative PREVGL1 refresh rails, or equivalent vendor-specified rail evidence.
- Visible current normal expression, partial expression transition, touch response, and maintenance boundary on the recovered panel.
