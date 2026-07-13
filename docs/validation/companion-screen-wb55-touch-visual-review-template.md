# WB55 Touch/Visual Review Template

This file is generated. Fill a copy during the active acceptance session;
do not edit this template as the final evidence record.

- Status: `TEMPLATE_NOT_ACCEPTANCE_RESULT`
- Gate: `wb55_touch_visual_acceptance`
- Target: `NUCLEO-WB55RG + GDEY0154D67-T03 + FT6336U`
- Source packet: `docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.json`
- Start rule: Do not start this packet until rev52 runtime logs PASS, promotion is applied, pre-acceptance health PASS, and the operator explicitly says 开始验收.
- Machine precondition: NO_GO_RUNTIME_RECHECK_PENDING: do not start human touch/visual steps until rev52 provision and normal runtime logs pass and promotion is applied.

## Review Records

### 1. Daily face tap keeps social mode

- Step ID: `daily_tap_social_response`
- Action: 在日常表情页轻点上/中/下几个位置，不要长按。
- Success signal: 表情看向触点并有整张内脸反应；不会误进入菜单。
- Regression guard: tap must remain separate from anywhere 3 s menu entry
- Expected record fields:
  - tap position
  - observed expression
  - whether menu opened accidentally
- Operator observation:
- Operator note:
- Triage items:
  - (pending)
- Visual issue classification: `none`
- Resolution state: `open_requires_fix`
- Evidence path:
- Next review scope:
- Publishable PASS allowed: `false`

### 2. Daily swipes become pet reactions

- Step ID: `daily_swipe_pet_response`
- Action: 在日常表情页分别左/右/上/下滑动。
- Success signal: 四个方向都有方向化表情反应；左右滑不会进入菜单。
- Regression guard: ordinary swipes must keep feeding pet_behavior instead of navigation
- Expected record fields:
  - swipe direction
  - observed response
  - false menu entry yes/no
- Operator observation:
- Operator note:
- Triage items:
  - (pending)
- Visual issue classification: `none`
- Resolution state: `open_requires_fix`
- Evidence path:
- Next review scope:
- Publishable PASS allowed: `false`

### 3. Anywhere hold enters menu deliberately

- Step ID: `anywhere_hold_menu_entry`
- Action: 按住屏幕任意位置约 3 秒，保持近似静止。
- Success signal: 约 650 ms 先出现逗弄反馈，约 3 s 后进入菜单。
- Regression guard: menu entry remains a deliberate anywhere long press
- Expected record fields:
  - tease visible yes/no
  - menu entry time feel
  - accidental entry before 3 s yes/no
- Operator observation:
- Operator note:
- Triage items:
  - (pending)
- Visual issue classification: `none`
- Resolution state: `open_requires_fix`
- Evidence path:
- Next review scope:
- Publishable PASS allowed: `false`

### 4. Menu drag follows the finger

- Step ID: `menu_drag_follow_finger`
- Action: 进入菜单后按住列表区域上下拖动，不要从顶部固定系统栏开始。
- Success signal: 列表像电子书目录一样跟随手指，顶部系统栏和白色隔离带不被覆盖，松手后停在合理位置。
- Regression guard: continuous 2 px menu frames and fixed 38 px header must stay intact
- Expected record fields:
  - drag direction
  - finger-follow feel
  - header overlap yes/no
  - snap/jump yes/no
- Operator observation:
- Operator note:
- Triage items:
  - (pending)
- Visual issue classification: `none`
- Resolution state: `open_requires_fix`
- Evidence path:
- Next review scope:
- Publishable PASS allowed: `false`

### 5. Row press shows entry feedback

- Step ID: `row_press_and_back`
- Action: 点击任一菜单项，进入详情页后从左边缘右滑返回。
- Success signal: 点击项先有被选中的 press-cue，再到详情页；返回手势可用。
- Regression guard: press-cue and target-arrival partial refreshes must not collapse into multi-flash full refresh
- Expected record fields:
  - row
  - press cue visible yes/no
  - detail arrival visible yes/no
  - back success yes/no
- Operator observation:
- Operator note:
- Triage items:
  - (pending)
- Visual issue classification: `none`
- Resolution state: `open_requires_fix`
- Evidence path:
- Next review scope:
- Publishable PASS allowed: `false`

### 6. Language toggle stays single-language

- Step ID: `language_switch_single_language`
- Action: 进入偏好页切换中文/英文，再返回主页检查。
- Success signal: 每次只显示一种语言；主页和详情页语言一致。
- Regression guard: single Chinese or single English mode must stay product-wide
- Expected record fields:
  - selected language
  - mixed-language text yes/no
  - return path
- Operator observation:
- Operator note:
- Triage items:
  - (pending)
- Visual issue classification: `none`
- Resolution state: `open_requires_fix`
- Evidence path:
- Next review scope:
- Publishable PASS allowed: `false`

### 7. Maintenance is one quiet cleanup

- Step ID: `maintenance_single_quiet_flash`
- Action: 完成一次点击或拖动后放手等待约 2 秒。
- Success signal: 只出现一次低闪维护感；没有连续多次全刷闪烁。
- Regression guard: 0xCF maintenance must stay post-contact and perceived as one quiet cleanup
- Expected record fields:
  - gesture before wait
  - maintenance flash count
  - residual ghosting acceptable yes/no
- Operator observation:
- Operator note:
- Triage items:
  - (pending)
- Visual issue classification: `none`
- Resolution state: `open_requires_fix`
- Evidence path:
- Next review scope:
- Publishable PASS allowed: `false`

### 8. Pet expression feels alive enough for next art pass

- Step ID: `premium_pet_feel`
- Action: 在轻点、滑动、菜单进入前后观察表情整体质感。
- Success signal: 眼睛、眉、嘴鼻、腮线和小标记共同变化；不像只播放固定眼睛模板。
- Regression guard: future art tuning must go through genref_sheet_12_inner_faces_v5 style anchors
- Expected record fields:
  - best expression
  - weakest expression
  - specific art adjustment request
- Operator observation:
- Operator note:
- Triage items:
  - (pending)
- Visual issue classification: `none`
- Resolution state: `open_requires_fix`
- Evidence path:
- Next review scope:
- Publishable PASS allowed: `false`

## Triage Contract

- Scope: Every non-empty operator note from this packet, even on a PASS step.
- Publishable PASS rule: The acceptance packet cannot be treated as publishable PASS while any triage item remains open_requires_fix, lacks an evidence_path, or accepts recognizable stale_generation_content as benign.
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

Completion rule: This template is not a PASS artifact. After review, each non-empty operator_note must be split into triage_items, assigned one allowed resolution_state, and linked to evidence_path before the acceptance packet can be considered publishable PASS.
