# Companion Screen Goal Audit

This file is generated. Update it with
`python .\tools\verify_companion_screen_goal_audit.py --write`.

- Status: `GOAL_ACTIVE_NOT_COMPLETE`
- Target: `NUCLEO-WB55RG + GDEY0154D67-T03 + FT6336U; future STM32WBA55/WBA65`
- Current resource: revision `53`, `49901` bytes, CRC `0x2332E300`

## Requirements

### wb55_physical_wiring_and_panel_identity

- Status: `blocked_hardware_recovery`
- Requirement: NUCLEO-WB55RG reaches the GDEY0154D67-T03 SSD1681 digital command path, but the current FTS02 must establish positive/negative refresh rails and deterministic visible frames before physical panel health is proved.
- Evidence:
  - `docs/validation/companion-screen-panel-hardware-gate.json`: `HISTORICAL_PASS_NOT_CURRENT_ACCEPTANCE` - older controller, wiring, refresh, orientation, and contact evidence is retained as history but is superseded for current panel health by the later grain/rail failure
  - `docs/validation/companion-screen-wb55-hardware-recovery-gate.json`: `DEFERRED_HARDWARE_FTS02_BOOST` - official one-plane white/black transfers assert BUSY, but PREVGH/PREVGL and visible output keep the current FTS02/panel gate hardware-deferred

### current_external_resource_runtime

- Status: `proved`
- Requirement: The normal WB55 firmware uses external ui_assets for the current expression/menu art pack.
- Evidence:
  - `docs/validation/companion-screen-bilingual-menu-wb55.json`: `REVISION_53_RUNTIME_RECHECK_PENDING` - revision 53 CEMP pack metadata is current; runtime_status=REVISION_53_RUNTIME_PASS_HUMAN_VISUAL_PENDING
  - `.cache/validation/rev53-runtime-current/normal/nucleo-serial-raw.log`: `PASS` - normal boot log contains mount=ok, revision=53, source=external_flash, and full refresh completion

### generated_pet_and_menu_art_baseline

- Status: `proved`
- Requirement: Normal product expression/menu art follows the generated-image baseline, keeps the cat outline in the physical shell, and prevents regressions to eye-only or legacy procedural faces.
- Evidence:
  - `docs/validation/companion-screen-generated-art-style-contract.json`: `PASS` - style=genref_sheet_12_inner_faces_v5 marks generated reference as source of truth and limits legacy procedural faces to rescue/maintenance fallback
  - `docs/validation/companion-screen-premium-pet-art-contract.json`: `PASS` - 12 generated-baseline poses move multiple inner-face zones including mouth/nose with zero shell-owned outer-margin pixels

### generated_art_handoff_and_refresh_feel_regression_guard

- Status: `proved`
- Requirement: Product rules prevent mixed old/new expression art and prevent e-paper ghosting fixes from regressing into repeated full-screen flicker during touch.
- Evidence:
  - `docs/validation/companion-screen-generated-art-style-contract.json`: `PASS` - normal pack contact sheet proves every normal expression source is generated-sheet-derived; old procedural art is not allowed in the normal product pack
  - `docs/validation/companion-screen-refresh-feel-contract.json`: `PASS` - SCR-16 contract keeps 0xFC differential interaction, latest-frame menu coalescing, one 0xCF quiet maintenance pass after touch settles, and 0xF7 only for baseline/fault recovery
  - `docs/validation/companion-screen-display-queue-generation-hygiene.json`: `PASS` - SCR-17 separates physical e-paper afterimage from stale queued frames by atomically switching active_resource_revision, draining stale requests, and requiring coherent_generation on the first visible result
  - `docs/validation/companion-screen-generation-release-ledger.json`: `RUNTIME_PROMOTED_HUMAN_VISUAL_PENDING` - SCR-17 release ledger records source art, CEMP revision/CRC, external Flash activation status, stale-discard model, first-frame coherent marker, refresh classification, OTA transaction rule, and pending rev53 runtime facts

### screen_refresh_touch_machine_health

- Status: `blocked_hardware_recovery`
- Requirement: WB55 logs retain FT6336 identity, CEMP, BUSY, and quiet-profile facts, but visible refresh health requires FTS02 recovery before human visual acceptance.
- Evidence:
  - `.cache/validation/rev53-runtime-current/normal/nucleo-serial-raw.log`: `PASS` - normal boot log includes refresh complete and touch-health identity addr=0x38 cipher=0x64 fw=0x01 chip=0x11
  - `docs/validation/companion-screen-wb55-runtime-recheck-logs.json`: `PASS` - current rev53 machine health depends on provision and normal runtime logs; pending status keeps this requirement in hardware recheck instead of relying on earlier history
  - `docs/validation/companion-interaction-profile-runtime-gate-20260714.md`: `PASS` - the reset-bounded normal capture must contain the complete quiet interaction boot marker; older resource-only logs do not prove the latency candidate
  - `docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.json`: `PENDING_HUMAN` - operator packet links the current resource state; it does not claim human visual acceptance
  - `docs/validation/companion-screen-refresh-feel-contract.json`: `PASS` - static refresh-feel contract is PASS; real rev53 touch/flicker/ghosting feel remains a pending hardware recheck
  - `docs/validation/companion-screen-wb55-hardware-recovery-gate.json`: `DEFERRED_HARDWARE_FTS02_BOOST` - current visible refresh is blocked by absent FTS02 positive/negative rails despite a responding SSD1681 command/BUSY path

### wb55_screen_firmware_build_matrix

- Status: `proved`
- Requirement: WB55 screen firmware keeps default dry-run, SSD1681 real-panel, and ScreenAssetProvision external ui_assets build variants compilable before any hardware acceptance is requested.
- Evidence:
  - `docs/validation/companion-screen-wb55-build-matrix.json`: `PASS` - build matrix proves the default dry-run build excludes SSD1681 transport, the explicit real-panel build includes panel_target_stm32wb_ssd1681.c and resource-generation queue diagnostics, and the ScreenAssetProvision build links the current external CEMP provision image

### touch_menu_interaction_machine_contract

- Status: `proved`
- Requirement: Portable touch/menu logic preserves any-position 3 s menu entry, daily tap/swipe pet reactions, the menu-v3 static six-row home, row press-cue, and left-edge right-swipe back/exit before subjective human feel review.
- Evidence:
  - `docs/validation/companion-screen-menu-drag-continuity-contract.json`: `PASS` - 1 source-layout home frame per language keeps six visible rows and a black selected row while excluding legacy numbered scroll frames
  - `docs/validation/companion-screen-presentation-wb55.json`: `PASS_STATIC_CURRENT_CODE` - screen_presentation verifier proves any-position long_press entry, pet-only daily swipes, static-home row handling, row press-cue, and left-edge swipe-right navigation
  - `docs/validation/companion-screen-touch-ft6336-wb55.json`: `PASS_STATIC_CURRENT_CODE` - gesture contract keeps 3000 ms any-position long_press with 46 px wobble tolerance and menu-v3 home tracks the current pressed row but never synthesizes legacy scroll frames

### daily_pet_and_menu_human_feel

- Status: `pending_human`
- Requirement: Human confirms daily tap/swipe pet reactions, 3 s hold menu entry, static menu-home vertical strokes, press-cue, language switching, residual/flicker, and premium pet feel on the real panel.
- Evidence:
  - `docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.json`: `PENDING_HUMAN` - asynchronous focused packet must start only after the operator explicitly says 开始验收; machine_precondition=NO_GO_OPEN_OPERATOR_REVIEW_ITEMS: do not start a new touch/visual review until the prior focused menu-density feedback is fixed and re-reviewed with evidence.
  - `docs/validation/companion-interaction-profile-runtime-gate-20260714.md`: `PASS` - the same focused packet remains NO_GO until the reset-bounded normal capture proves the complete quiet interaction marker
  - `docs/validation/companion-screen-wb55-touch-visual-review-template.json`: `TEMPLATE_NOT_ACCEPTANCE_RESULT` - blank structured review template mirrors all focused operator steps and defaults every record to non-publishable until triaged with evidence
  - `docs/validation/companion-screen-wb55-touch-visual-review-record.json`: `NO_GO_OPEN_REVIEW_ITEMS` - filled review record validator is present and stays non-publishable until all operator notes are triaged, closed, and linked to evidence
  - `docs/validation/companion-screen-pre-acceptance-health.json`: `NO_GO_OPEN_OPERATOR_REVIEW_ITEMS` - machine-only pre-acceptance health gate blocks acceptance until rev53 runtime recheck, while retaining last-proven log, touch identity, refresh marker, flash preflight, and packet/resource consistency evidence
  - `docs/validation/companion-screen-wb55-runtime-recheck-runner.json`: `PASS` - rev53 provision flash, provision capture, normal restore, and normal capture sequence is dry-run verified and requires the Companion-WB55 workflow hardware lock before execution
  - `docs/validation/companion-screen-wb55-runtime-hardware-action-card.json`: `PASS_MACHINE_RUNTIME_RECHECK_COMPLETE` - Chinese hardware action card renders the locked rev53 runtime recheck steps, expected markers, promotion sequence, and human acceptance start rule
  - `docs/validation/companion-screen-wb55-runtime-flash-preflight.json`: `PASS` - normal/provision flash CheckOnly preflight proves both hex paths and STM32_Programmer_CLI are available before the locked hardware run
  - `docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json`: `PASS_STATIC_SERIAL_CAPTURE_PREFLIGHT` - static serial-capture preflight proves capture_nucleo_serial.ps1, locked runner calls, raw/summary output names, and log-verifier expectations before opening any COM port; claim_scope=static_serial_capture_contract_no_hardware_claim
  - `docs/validation/companion-screen-wb55-runtime-recheck-logs.json`: `PASS` - rev53 provision/normal runtime logs are the first-hand machine gate; pending status means human touch/visual acceptance must not start
  - `docs/validation/companion-screen-wb55-runtime-promotion.json`: `APPLIED` - promotion gate has applied rev53 runtime evidence; human visual/touch acceptance is still pending
  - `docs/validation/companion-screen-wb55-hardware-recovery-gate.json`: `DEFERRED_HARDWARE_FTS02_BOOST` - do not open the focused touch/visual review until FTS02 replacement or cross-swap passes solid white, solid black, and normal-expression recovery
- Pending steps:
  - `daily_tap_social_response`
  - `daily_swipe_pet_response`
  - `anywhere_hold_menu_entry`
  - `menu_boundary_single_clean_refresh`
  - `menu_home_static_vertical_stroke`
  - `row_press_and_back`
  - `phone_reconnect_advertising`
  - `language_switch_single_language`
  - `maintenance_single_quiet_flash`
  - `premium_pet_feel`

### external_flash_and_ota_resource_policy

- Status: `proved`
- Requirement: Large replaceable UI resources stay in external Flash and remain part of OTA/update scope; internal Flash keeps only rescue UI/code.
- Evidence:
  - `docs/validation/companion-screen-resource-memory-policy.json`: `PASS` - normal linked full-frame static expression bytes remain zero; revision 53 candidate pack bytes/CRC are tracked separately from last real WB55 runtime evidence

### wba55_wba65_portability_boundary

- Status: `pre_port_proved_real_wba_pending`
- Requirement: Portable screen/expression/touch/resource layers preserve WBA55/WBA65 boundaries; real WBA parity remains a future hardware gate.
- Evidence:
  - `docs/validation/companion-screen-wba-port-contract.json`: `PASS` - portable contracts, target-named WBA scaffolds, and forbidden portable dependencies are recorded
  - `docs/validation/companion-screen-wba-cube-dependency-preflight.json`: `PASS` - CubeWBA dependency preflight records that WBA parity stays DRAFT_PRE_PORT until STM32CubeWBA, a separate CubeWBA project, and a scriptable WBA build wrapper exist
  - `docs/validation/companion-screen-wba-real-parity-gate.json`: `PASS_PRE_PORT_PARITY_BLOCKED` - WBA promotion is blocked until target_family=STM32WBA, exact WBA55/WBA65 evidence, WBA-named paths, and real panel/touch/BLE artifacts exist; WB55 evidence is baseline only
  - `docs/validation/companion-screen-wba-lse-clock-contract.json`: `PASS_PRE_PORT_CLOCK_CONTRACT_RECORDED` - WBA55/WBA65 pre-port clock contract requires assembled 32.768 kHz LSE by default and keeps real LSE startup, RTC continuity, BLE sleep, timed wake-up, or no-LSE exception evidence pending; claim_scope=wba_clock_design_contract_no_hardware_claim
  - `docs/validation/companion-screen-pet-behavior-user-data-stm32wba.json`: `PASS` - WBA55/WBA65 comp_pet_behavior_memory_t stays outside ui_assets/CEMP, OTA staging, recording cache, and MCU Flash constants through callback-only logical slots, CRC records, low-frequency commits, explicit privacy erase, and Cortex-M33 ARM GCC object compilation; real WBA storage evidence remains pending
- Future gate: `wba_real_panel_refresh` - WBA real refresh still requires CubeWBA target projects and hardware evidence; the WB55 portable baseline remains useful, but current WB55 visible panel health must also be re-proved after FTS02 recovery.

## Open Requirements

- `wb55_physical_wiring_and_panel_identity`
- `screen_refresh_touch_machine_health`
- `daily_pet_and_menu_human_feel`
- `wba55_wba65_portability_boundary`

Completion rule: Do not mark the active goal complete until every requirement is proved; blocked_hardware_recovery requires FTS02 replacement/cross-swap evidence, pending_human requires operator acceptance evidence, and WBA real parity requires a later WBA hardware/project gate.
