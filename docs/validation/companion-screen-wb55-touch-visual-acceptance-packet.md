# WB55 Touch/Visual Acceptance Packet

This packet is generated. Update it with
`python .\tools\render_wb55_touch_visual_acceptance_packet.py --write`.

- Status: `PENDING_HUMAN`
- Gate: `wb55_touch_visual_acceptance`
- Target: `NUCLEO-WB55RG + GDEY0154D67-T03 + FT6336U`
- Start rule: Do not start this packet until rev52 runtime logs PASS, promotion is applied, pre-acceptance health PASS, and the operator explicitly says 开始验收.
- Machine precondition: NO_GO_RUNTIME_RECHECK_PENDING: do not start human touch/visual steps until rev52 provision and normal runtime logs pass and promotion is applied.

## Preflight Commands

- `python .\tools\verify_companion_screen_pre_acceptance_health.py`
- `python .\tools\verify_wb55_runtime_flash_preflight.py`
- `python .\tools\verify_wb55_runtime_serial_capture_preflight.py`
- `python .\tools\render_wb55_runtime_hardware_action_card.py`
- `python .\tools\verify_wb55_screen_runtime_recheck_logs.py`
- `python .\tools\promote_wb55_screen_runtime_recheck.py`
- `python .\tools\verify_wb55_screen_runtime_recheck_runner.py`
- `python .\tools\verify_display_queue_generation_hygiene.py`
- `python .\tools\verify_screen_generation_release_ledger.py`
- `python .\tools\render_generated_art_style_contract.py`
- `python .\tools\verify_screen_menu_assets.py`
- `python .\tools\verify_screen_presentation.py`
- `python .\tools\verify_touch_ft6336.py`
- `python .\tools\verify_premium_pet_art_contract.py`
- `python .\tools\verify_epaper_fast_maintenance_runtime.py`
- `python .\tools\verify_epaper_differential_maintenance_runtime.py`

## Machine State

- `resource_revision`: `52`
- `resource_crc32`: `0xDEFC096E`
- `resource_total_bytes`: `287732`
- `runtime_status`: `REVISION_52_RUNTIME_RECHECK_PENDING`
- `normal_firmware_restored`: `True`
- `bilingual_menu_evidence`: `docs/validation/companion-screen-bilingual-menu-wb55.json`
- `provision_log`: ``
- `normal_log`: ``
- `runtime_logs_evidence`: `docs/validation/companion-screen-wb55-runtime-recheck-logs.json`
- `runtime_flash_preflight`: `{'path': 'docs/validation/companion-screen-wb55-runtime-flash-preflight.json', 'status': 'PASS'}`
- `runtime_serial_capture_preflight`: `{'path': 'docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json', 'status': 'PASS_STATIC_SERIAL_CAPTURE_PREFLIGHT', 'claim_scope': 'static_serial_capture_contract_no_hardware_claim'}`
- `runtime_hardware_action_card`: `{'path': 'docs/validation/companion-screen-wb55-runtime-hardware-action-card.json', 'status': 'NO_GO_WAITING_FOR_REAL_HARDWARE_RUN'}`
- `display_queue_generation_hygiene`: `{'path': 'docs/validation/companion-screen-display-queue-generation-hygiene.json', 'status': 'PASS', 'scenario': 'rev50_pending_frames_discarded_before_rev51_first_frame', 'coherent_generation': 1, 'last_stale_discarded': 3}`
- `generation_release_ledger`: `{'path': 'docs/validation/companion-screen-generation-release-ledger.json', 'status': 'PENDING_RUNTIME_RECHECK', 'cemp_revision': 52, 'cemp_crc32': '0xDEFC096E', 'expected_first_frame_marker': 'coherent_generation=1', 'real_runtime_status': 'NO_GO_MISSING_RUNTIME_LOGS', 'visual_triage_classes': ['physical afterimage', 'stale queued frame', 'stale asset revision', 'rescue/procedural fallback leakage', 'stale_generation_content']}`

## Operator Steps

### 1. Daily face tap keeps social mode

- ID: `daily_tap_social_response`
- Action: 在日常表情页轻点上/中/下几个位置，不要长按。
- Success signal: 表情看向触点并有整张内脸反应；不会误进入菜单。
- Regression guard: tap must remain separate from anywhere 3 s menu entry
- Record:
  - tap position
  - observed expression
  - whether menu opened accidentally

### 2. Daily swipes become pet reactions

- ID: `daily_swipe_pet_response`
- Action: 在日常表情页分别左/右/上/下滑动。
- Success signal: 四个方向都有方向化表情反应；左右滑不会进入菜单。
- Regression guard: ordinary swipes must keep feeding pet_behavior instead of navigation
- Record:
  - swipe direction
  - observed response
  - false menu entry yes/no

### 3. Anywhere hold enters menu deliberately

- ID: `anywhere_hold_menu_entry`
- Action: 按住屏幕任意位置约 3 秒，保持近似静止。
- Success signal: 约 650 ms 先出现逗弄反馈，约 3 s 后进入菜单。
- Regression guard: menu entry remains a deliberate anywhere long press
- Record:
  - tease visible yes/no
  - menu entry time feel
  - accidental entry before 3 s yes/no

### 4. Menu drag follows the finger

- ID: `menu_drag_follow_finger`
- Action: 进入菜单后按住列表区域上下拖动，不要从顶部固定系统栏开始。
- Success signal: 列表像电子书目录一样跟随手指，顶部系统栏和白色隔离带不被覆盖，松手后停在合理位置。
- Regression guard: continuous 2 px menu frames and fixed 38 px header must stay intact
- Record:
  - drag direction
  - finger-follow feel
  - header overlap yes/no
  - snap/jump yes/no

### 5. Row press shows entry feedback

- ID: `row_press_and_back`
- Action: 点击任一菜单项，进入详情页后从左边缘右滑返回。
- Success signal: 点击项先有被选中的 press-cue，再到详情页；返回手势可用。
- Regression guard: press-cue and target-arrival partial refreshes must not collapse into multi-flash full refresh
- Record:
  - row
  - press cue visible yes/no
  - detail arrival visible yes/no
  - back success yes/no

### 6. Language toggle stays single-language

- ID: `language_switch_single_language`
- Action: 进入偏好页切换中文/英文，再返回主页检查。
- Success signal: 每次只显示一种语言；主页和详情页语言一致。
- Regression guard: single Chinese or single English mode must stay product-wide
- Record:
  - selected language
  - mixed-language text yes/no
  - return path

### 7. Maintenance is one quiet cleanup

- ID: `maintenance_single_quiet_flash`
- Action: 完成一次点击或拖动后放手等待约 2 秒。
- Success signal: 只出现一次低闪维护感；没有连续多次全刷闪烁。
- Regression guard: 0xCF maintenance must stay post-contact and perceived as one quiet cleanup
- Record:
  - gesture before wait
  - maintenance flash count
  - residual ghosting acceptable yes/no

### 8. Pet expression feels alive enough for next art pass

- ID: `premium_pet_feel`
- Action: 在轻点、滑动、菜单进入前后观察表情整体质感。
- Success signal: 眼睛、眉、嘴鼻、腮线和小标记共同变化；不像只播放固定眼睛模板。
- Regression guard: future art tuning must go through genref_sheet_12_inner_faces_v5 style anchors
- Record:
  - best expression
  - weakest expression
  - specific art adjustment request

## Evidence To Attach

- operator notes for each step
- filled copy of docs/validation/companion-screen-wb55-touch-visual-review-template.md or equivalent structured records
- validated filled review record from docs/validation/companion-screen-wb55-touch-visual-review-record.json
- runtime hardware action card docs/validation/companion-screen-wb55-runtime-hardware-action-card.json
- display queue generation hygiene docs/validation/companion-screen-display-queue-generation-hygiene.json
- SCR-17 generation release ledger docs/validation/companion-screen-generation-release-ledger.json
- runtime flash preflight docs/validation/companion-screen-wb55-runtime-flash-preflight.json
- runtime serial capture preflight docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json
- machine_state currently links the last runtime-proven revision logs; rev52 provision/normal logs are still pending in the runtime recheck report
- serial/runtime diagnostic tail if flashed during the session
- photo or short video only when the operator chooses to capture visual evidence
- if old marks are visible, classify them as physical afterimage, stale queued frame, stale asset revision, rescue/procedural fallback leakage, or stale_generation_content
- issue triage: fixed, deferred by product decision, accepted benign, or still open

Post-session rule: Every non-empty operator note is a task input. Fix AI-solvable issues with machine evidence before asking for another focused review.

## Review Note Triage Contract

- Scope: Every non-empty operator note from this packet, even on a PASS step.
- Publishable PASS rule: The acceptance packet cannot be treated as publishable PASS while any triage item remains open_requires_fix, lacks an evidence_path, or accepts recognizable stale_generation_content as benign.
- Re-review rule: Ask for another focused review only for the fixed item or the smallest touched behavior, not for already accepted steps unless the fix can plausibly regress them.
- Required fields:
  - `source_step_id`
  - `operator_note`
  - `triage_items`
  - `resolution_state`
  - `evidence_path`
  - `next_review_scope`
  - `visual_issue_classification`
- Allowed visual issue classifications:
  - `none`
  - `physical afterimage`
  - `stale queued frame`
  - `stale asset revision`
  - `rescue/procedural fallback leakage`
  - `stale_generation_content`
- Allowed resolution states:
  - `fixed_with_machine_evidence`
  - `deferred_by_product_decision`
  - `accepted_benign_with_evidence`
  - `open_requires_fix`
