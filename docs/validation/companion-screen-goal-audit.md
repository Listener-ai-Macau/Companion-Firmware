# Companion Screen Goal Audit

This file is generated. Update it with
`python .\tools\verify_companion_screen_goal_audit.py --write`.

- Status: `GOAL_ACTIVE_NOT_COMPLETE`
- Target: `NUCLEO-WB55RG + GDEY0154D67-T03 + FT6336U; future STM32WBA55/WBA65`
- Current resource: revision `52`, `287732` bytes, CRC `0xDEFC096E`

## Requirements

### wb55_physical_wiring_and_panel_identity

- Status: `proved`
- Requirement: NUCLEO-WB55RG drives the physical GDEY0154D67-T03 panel with verified SSD1681 wiring.
- Evidence:
  - `docs/validation/companion-screen-panel-hardware-gate.json`: `PASS` - controller, panel, voltage, DC/RST/BUSY, full/partial/maintenance refresh, orientation, and contact evidence are recorded

### current_external_resource_runtime

- Status: `pending_hardware_recheck`
- Requirement: The normal WB55 firmware uses external ui_assets for the current expression/menu art pack.
- Evidence:
  - `docs/validation/companion-screen-bilingual-menu-wb55.json`: `REVISION_52_RUNTIME_RECHECK_PENDING` - revision 52 CEMP pack metadata is current; runtime_status=REVISION_52_RUNTIME_RECHECK_PENDING
  - `.`: `LAST_PROVEN_PREVIOUS_REVISION` - last proven normal boot remains revision=51; current revision=52 awaits provision/normal runtime recheck

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
  - `docs/validation/companion-screen-generation-release-ledger.json`: `RUNTIME_LOGS_PASS_PROMOTION_PENDING` - SCR-17 release ledger records source art, CEMP revision/CRC, external Flash activation status, stale-discard model, first-frame coherent marker, refresh classification, OTA transaction rule, and pending rev52 runtime facts

### screen_refresh_touch_machine_health

- Status: `pending_hardware_recheck`
- Requirement: WB55 machine logs prove refresh path and FT6336 identity/health before human visual acceptance.
- Evidence:
  - `.`: `LAST_PROVEN_PREVIOUS_REVISION` - rev52 refresh/touch runtime evidence is pending; rev51 remains last proven
  - `docs/validation/companion-screen-wb55-runtime-recheck-logs.json`: `PASS` - current rev52 machine health depends on provision and normal runtime logs; pending status keeps this requirement in hardware recheck instead of relying on earlier history
  - `docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.json`: `PENDING_HUMAN` - operator packet links the current resource state; it does not claim human visual acceptance
  - `docs/validation/companion-screen-refresh-feel-contract.json`: `PASS` - static refresh-feel contract is PASS; real rev52 touch/flicker/ghosting feel remains a pending hardware recheck

### wb55_screen_firmware_build_matrix

- Status: `proved`
- Requirement: WB55 screen firmware keeps default dry-run, SSD1681 real-panel, and ScreenAssetProvision external ui_assets build variants compilable before any hardware acceptance is requested.
- Evidence:
  - `docs/validation/companion-screen-wb55-build-matrix.json`: `PASS` - build matrix proves the default dry-run build excludes SSD1681 transport, the explicit real-panel build includes panel_target_stm32wb_ssd1681.c and resource-generation queue diagnostics, and the ScreenAssetProvision build links the current external CEMP provision image

### touch_menu_interaction_machine_contract

- Status: `proved`
- Requirement: Portable touch/menu logic preserves any-position 3 s menu entry, daily tap/swipe pet reactions, anchored continuous menu drag, row press-cue, and left-edge right-swipe back/exit before subjective human feel review.
- Evidence:
  - `docs/validation/companion-screen-menu-drag-continuity-contract.json`: `PASS` - 43 two-pixel frames per language keep fixed header, white gutter, monotonic scrollbar, and bounded adjacent-frame jumps
  - `docs/validation/companion-screen-presentation-wb55.json`: `PASS_STATIC_CURRENT_CODE` - screen_presentation verifier proves any-position long_press entry, pet-only daily swipes, vertical drag coalescing, row press-cue, and left-edge swipe-right navigation
  - `docs/validation/companion-screen-touch-ft6336-wb55.json`: `PASS_STATIC_CURRENT_CODE` - gesture contract keeps 3000 ms any-position long_press with 46 px wobble tolerance and anchored continuous finger-distance drag

### daily_pet_and_menu_human_feel

- Status: `pending_human`
- Requirement: Human confirms daily tap/swipe pet reactions, 3 s hold menu entry, drag feel, press-cue, language switching, residual/flicker, and premium pet feel on the real panel.
- Evidence:
  - `docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.json`: `PENDING_HUMAN` - asynchronous focused packet is ready and must start only after the operator explicitly says 开始验收
  - `docs/validation/companion-screen-wb55-touch-visual-review-template.json`: `TEMPLATE_NOT_ACCEPTANCE_RESULT` - blank structured review template mirrors all focused operator steps and defaults every record to non-publishable until triaged with evidence
  - `docs/validation/companion-screen-wb55-touch-visual-review-record.json`: `NO_GO_NOT_STARTED` - filled review record validator is present and stays non-publishable until all operator notes are triaged, closed, and linked to evidence
  - `docs/validation/companion-screen-pre-acceptance-health.json`: `NO_GO_RUNTIME_RECHECK_PENDING` - machine-only pre-acceptance health gate blocks acceptance until rev52 runtime recheck, while retaining last-proven log, touch identity, refresh marker, flash preflight, and packet/resource consistency evidence
  - `docs/validation/companion-screen-wb55-runtime-recheck-runner.json`: `PASS` - rev52 provision flash, provision capture, normal restore, and normal capture sequence is dry-run verified and requires the Companion-WB55 workflow hardware lock before execution
  - `docs/validation/companion-screen-wb55-runtime-hardware-action-card.json`: `NO_GO_WAITING_FOR_REAL_HARDWARE_RUN` - Chinese hardware action card renders the locked rev52 runtime recheck steps, expected markers, promotion sequence, and human acceptance start rule
  - `docs/validation/companion-screen-wb55-runtime-flash-preflight.json`: `PASS` - normal/provision flash CheckOnly preflight proves both hex paths and STM32_Programmer_CLI are available before the locked hardware run
  - `docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json`: `PASS_STATIC_SERIAL_CAPTURE_PREFLIGHT` - static serial-capture preflight proves capture_nucleo_serial.ps1, locked runner calls, raw/summary output names, and log-verifier expectations before opening any COM port; claim_scope=static_serial_capture_contract_no_hardware_claim
  - `docs/validation/companion-screen-wb55-runtime-recheck-logs.json`: `PASS` - rev52 provision/normal runtime logs are the first-hand machine gate; pending status means human touch/visual acceptance must not start
  - `docs/validation/companion-screen-wb55-runtime-promotion.json`: `READY_TO_APPLY` - promotion gate refuses to update runtime evidence until both rev52 provision and normal serial logs verify PASS
- Pending steps:
  - `daily_tap_social_response`
  - `daily_swipe_pet_response`
  - `anywhere_hold_menu_entry`
  - `menu_drag_follow_finger`
  - `row_press_and_back`
  - `language_switch_single_language`
  - `maintenance_single_quiet_flash`
  - `premium_pet_feel`

### external_flash_and_ota_resource_policy

- Status: `proved`
- Requirement: Large replaceable UI resources stay in external Flash and remain part of OTA/update scope; internal Flash keeps only rescue UI/code.
- Evidence:
  - `docs/validation/companion-screen-resource-memory-policy.json`: `PASS` - normal linked full-frame static expression bytes remain zero; revision 52 candidate pack bytes/CRC are tracked separately from last real WB55 runtime evidence

### wba55_wba65_portability_boundary

- Status: `pre_port_proved_real_wba_pending`
- Requirement: Portable screen/expression/touch/resource layers preserve WBA55/WBA65 boundaries; real WBA parity remains a future hardware gate.
- Evidence:
  - `docs/validation/companion-screen-wba-port-contract.json`: `PASS` - portable contracts, target-named WBA scaffolds, and forbidden portable dependencies are recorded
  - `docs/validation/companion-screen-wba-cube-dependency-preflight.json`: `PASS` - CubeWBA dependency preflight records that WBA parity stays DRAFT_PRE_PORT until STM32CubeWBA, a separate CubeWBA project, and a scriptable WBA build wrapper exist
  - `docs/validation/companion-screen-wba-real-parity-gate.json`: `PASS_PRE_PORT_PARITY_BLOCKED` - WBA promotion is blocked until target_family=STM32WBA, exact WBA55/WBA65 evidence, WBA-named paths, and real panel/touch/BLE artifacts exist; WB55 evidence is baseline only
  - `docs/validation/companion-screen-wba-lse-clock-contract.json`: `PASS_PRE_PORT_CLOCK_CONTRACT_RECORDED` - WBA55/WBA65 pre-port clock contract requires assembled 32.768 kHz LSE by default and keeps real LSE startup, RTC continuity, BLE sleep, timed wake-up, or no-LSE exception evidence pending; claim_scope=wba_clock_design_contract_no_hardware_claim
  - `docs/validation/companion-screen-pet-behavior-user-data-stm32wba.json`: `PASS` - WBA55/WBA65 comp_pet_behavior_memory_t stays outside ui_assets/CEMP, OTA staging, recording cache, and MCU Flash constants through callback-only logical slots, CRC records, low-frequency commits, explicit privacy erase, and Cortex-M33 ARM GCC object compilation; real WBA storage evidence remains pending
- Future gate: `wba_real_panel_refresh` - WBA real refresh still requires a CubeWBA project, target pins, timing, refresh logs, and visual evidence; WB55 real refresh is already proven.

## Open Requirements

- `current_external_resource_runtime`
- `screen_refresh_touch_machine_health`
- `daily_pet_and_menu_human_feel`
- `wba55_wba65_portability_boundary`

Completion rule: Do not mark the active goal complete until every requirement is proved; pending_human requires operator acceptance evidence, and WBA real parity requires a later WBA hardware/project gate.
