# Companion V45/r7 美术接手文档

这是当前 Companion 上层表情美术、组件 Rig、编舞、浏览器预览和 WB55
目标端组件计划的 canonical handoff。下一位 AI 修改表情美术前，先读本文，
再读产品 registry 和当前机器证据；不要依赖聊天上下文。

完整的 V9 到 V45 生图 prompt、request、lineage、迭代台账、编舞和历史反馈索引
在 [companion_art_generation_lineage.md](companion_art_generation_lineage.md)。
本文负责当前 V45/r7 的可执行入口和验证；不要把历史目录当成当前入口。

## 当前快照

- 仓库：`C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware`
- 分支：`main`
- 当前美术 checkpoint：`59b776e feat(companion): checkpoint V45 component art preview`
- 当前 owner-facing revision：`v45-touch-failsafe-r7-20260721`
- 当前页面 revision marker：`v45-touch-failsafe-r7`
- 当前状态：机器闭环 PASS，人工审美/物理屏验收仍 pending
- runtime：`runtime_resource_activated=false`

本 checkpoint 只保存上层美术与组件链路。工作树中另有其他 Agent 的底层改动，
不要用 `git add -A`，不要把它们并入美术提交。

## 产品行为合同

COMP-REQ-294 的当前解释如下：

1. 鼠标/触摸按下不能触发眨眼。
2. 按下和拖动只改变当前情绪的眼神高光与小星光 overlay。
3. 触摸期间冻结当前故事的当前主脸帧，不推进故事索引或 frame index。
4. 释放先回到当前帧的中心 gaze，再以剩余/合理延迟继续当前故事。
5. 普通按下不切换 emotion/story；横向或纵向 swipe 才浏览相邻故事。
6. 眨眼只允许由日常 idle 的确定性闲置编舞触发。

因此，当前“按下互动”是 gaze/sparkle 互动，不是按下立即换一张情绪脸。

## 明确边界

### 本 handoff 覆盖

- WB55 上层 V9 组件 Rig
- emotion state、story 和 deterministic choreography
- 200x200 1bpp 浏览器预览
- V45 single preview 与 expanded review wall
- WB55 目标端组件计划、CRIG/external-NOR source component parity
- touch gaze overlay、frame staging、decode、release resume

### 本 handoff 不覆盖

禁止修改或在美术提交中暂存：

- `SSD1681`
- LUT、waveform、BUSY、刷新、电源、SPI、Flash
- `panel_target*`
- `display_queue*`、`refresh_policy*`
- 任何底层驱动或物理屏幕恢复逻辑

同时禁止：

- 修改锁定 V9 源图
- 整脸贴图轮播
- 代码绘制五官
- legacy 美术或整脸 fallback
- custom LUT
- canvas
- 独立触控画布或第二个触控卡

## 不可修改的保护物

锁定 V9 源图：

`docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png`

SHA256：

`919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA`

受保护 owner acceptance：

`docs/validation/companion-pet-special-system-owner-acceptance-20260717.json`

SHA256：

`8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227`

历史 r4/r5 owner review 必须保留，不能覆盖或删除。当前没有人工验收窗口；
不要主动打开。

## 当前美术与预览入口

### V45 源与计划

- V45 candidate 根：
  `docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/`
- 注册组件 layout：`v45-special-component-layout.json`
- WB55 target trace：
  `target-score-attempt-01/v45-wb55-target-profile-plan.json`
- V45 source CRIG：
  `companion-v9-v45-complete-eye-special-components-candidate-200x200.crig`
- source component masks：`candidate/component-masks/`
- generated upper profiles：`app/companion_pendant/epaper/generated/`

V22 face source、V34/V35 decoration source 和 V45 blink source 是依赖，不要复制
到新的全脸图里；修改时仍使用注册 component mask、anchor、legal offset 和
ordered layer plan。

### 两个 owner-facing 页面

- Single：
  `docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html`
- Expanded wall：
  `docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/expanded-review-wall-01/index.html`

两页都应显示 `Touch fail-safe r7` 和 `v45-touch-failsafe-r7-20260721`，
资源 URL 应带：

`?review=v45-touch-failsafe-r7-20260721`

不要手工改生成 HTML；改源/trace 后重新运行 renderer。

## 浏览器实现模型

浏览器不是整脸 GIF 轮播。每个 200x200 1bpp frame 由注册 source component
按计划组合；主脸和 gaze overlay 是两个可观察层。

主脸资源切换流程：

1. 把下一张主脸放入隐藏 staging `Image`。
2. 等待 `load` 和严格 `decode()` 成功。
3. 等待 paint frame 后再替换可见主脸。
4. load/decode 失败时保留上一张可见主脸。
5. gaze overlay 失败时只隐藏 overlay，主脸 fail-safe 保留。

触摸流程：

1. `touch_begin` 暂停当前 frame timer，不推进 `frameIndex`。
2. `touch_follow` 只更新 gaze overlay。
3. 小幅 drag 不触发 story browse。
4. `touch_release` 先 center gaze，再按 `resume_delay_ms` 恢复当前故事。
5. 只有超过 swipe threshold 的横/竖移动才切换 story。

运行时调试 hook：

- `window.__v45TouchState()`
- `window.__v45TouchTrace`

关注字段：`story_index`、`active_frame_index`、`active_frame_cue`、
`active_base_src`、`primary_hidden`、`gaze_hidden`、`render_request`。

## 当前真实浏览器证据

证据报告：

`docs/validation/companion-v45-browser-pointer-fail-safe-20260721.json`

| 页面/阶段 | 截图 | 尺寸 | 黑像素 | cue | story/frame |
|---|---|---:|---:|---|---|
| single press | `companion-v45-real-browser-touch-press-20260721.png` | 400x401 | 10618 | `calm_entry` | 0/0 |
| single drag | `companion-v45-real-browser-touch-drag-20260721.png` | 400x401 | 10618 | `calm_entry` | 0/0 |
| single release | `companion-v45-real-browser-touch-release-20260721.png` | 400x401 | 6444 | `calm_entry` | 0/0 |
| expanded press | `companion-v45-expanded-real-browser-touch-press-20260721.png` | 200x200 | 2679 | `calm_entry` | 0/0 |
| expanded drag | `companion-v45-expanded-real-browser-touch-drag-20260721.png` | 200x200 | 2679 | `calm_entry` | 0/0 |
| expanded release | `companion-v45-expanded-real-browser-touch-release-20260721.png` | 200x200 | 1625 | `calm_entry` | 0/0 |

六张图都不是纯白；主脸存在。press/drag/release 没有 blink cue，gaze overlay
在 press、drag、release 间发生了可观察变化。release resume delay 至少 180ms。

总审计：

`docs/validation/companion-v45-total-machine-audit-20260721.json`

当前 status：`PASS_MACHINE_CLOSED_PENDING_V45_R7_REVIEW`

总审计必须继续保留：

- 旧 accepted blink note
- r4 人工失败：`还是一按下表情就消失了`
- r5 人工失败：`还是一样的现象`
- r7 真实浏览器像素证据
- `runtime_resource_activated=false`
- no physical panel acceptance claim

## 重新生成当前页面

在仓库根目录执行 PowerShell：

```powershell
python tools/render_companion_v34_v35_special_decoration_wb55_parity.py `
  --trace docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/target-score-attempt-01/v45-wb55-target-profile-plan.json `
  --special-layout docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/v45-special-component-layout.json `
  --candidate-label v45_complete_eye `
  --output-dir docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01 `
  --report docs/validation/companion-v45-complete-eye-browser-wb55-preview-20260721.json

python tools/render_companion_v45_expanded_review_wall.py
```

不要使用 `--check` 调用 V45 component renderer；它只支持生成参数。Expanded
wall verifier 有自己的 check。

## 完整机器闭环

静态与脚本语法：

```powershell
python -m py_compile tools/render_companion_v34_v35_special_decoration_wb55_parity.py tools/render_companion_v45_expanded_review_wall.py tools/verify_companion_v45_real_browser_pointer_evidence.py tools/verify_companion_v45_total_machine_audit.py
```

真实 Edge：

```powershell
npx playwright test tools/v45-click.spec.js --reporter=json > .cache/v45-browser-pointer-fail-safe-playwright.json
python tools/verify_companion_v45_real_browser_pointer_evidence.py
```

页面与 host verifier：

```powershell
python tools/verify_companion_v45_single_epaper_browser.py
python tools/verify_companion_v45_single_epaper_touch_host.py
python tools/verify_companion_v45_expanded_review_wall.py
```

上层 native host：

```powershell
pwsh -NoProfile -File tools/test_v22_everyday_bridge_router_host.ps1
pwsh -NoProfile -File tools/test_expression_v45_complete_eye_profile_host.ps1
pwsh -NoProfile -File tools/test_expression_v45_complete_eye_wb55_parity_host.ps1
pwsh -NoProfile -File tools/test_expression_touch_gaze_host.ps1
pwsh -NoProfile -File tools/test_expression_v34_v35_special_decoration_profile_host.ps1
pwsh -NoProfile -File tools/test_expression_v34_v35_special_decoration_wb55_parity_host.ps1
```

最终审计：

```powershell
python tools/verify_companion_v45_total_machine_audit.py
```

审计结果只能代表机器/目标计划闭环，不能升级成 runtime activation 或物理屏
验收。

## 以后修改美术的推荐流程

1. 先读 active Goal、`docs/companion_product_requirements.md` 和本文。
2. 执行 `git status --short --branch`，不要覆盖其他 Agent 改动。
3. 给新 source art、component export、layout 或 trace 建立明确 revision；不要
   覆盖 r4/r5 或当前 r7 evidence。
4. 只从 V9 锁定源派生 source component；登记 component id、mask hash、anchor、
   legal offset、composite op 和 semantic role。
5. 更新对应 layout/trace/profile，再运行 export/generate 脚本；不要手写生成的
   C 文件或 HTML。
6. 重新生成 200x200 1bpp single 与 expanded 页面。
7. 用真实 Edge 做 fresh page、cache-busted URL、press、small drag、release；
   保存三阶段截图并用 PIL/strict verifier 检查真实像素。
8. 运行对应 V22/V34/V45 host、expanded verifier 和 total audit。
9. 检查锁定源图 hash、protected acceptance hash、r4/r5 文件和
   `runtime_resource_activated=false`。
10. 只暂存上层美术 allowlist；提交消息写清 revision。不要 `git add -A`。

### 最常见的正确修改点

- 表情形状：V45 `candidate/component-masks/` 和 source export 输入
- 合法组合/位置：`v45-special-component-layout.json`
- 故事/帧/cue/duration：`v45-wb55-target-profile-plan.json`
- 浏览器行为：两个 renderer 的生成逻辑，不改生成 HTML
- 触摸验证：`tools/v45-click.spec.js`
- 真实像素验证：`tools/verify_companion_v45_real_browser_pointer_evidence.py`

如果只是换一张美术源图，优先保持 component id、anchor 和 semantic role 稳定，
只更新 source hash、mask 和必要的 legal offset。这样旧的 Rig、parity、touch
测试和回归证据仍然能直接复用。

## 浏览器与物理屏幕的准确关系

浏览器和 WB55 上层 parity 证明的是：同一组注册组件、同一组 offset、同一组
layer order、同一组 200x200 1bpp frame plan 会产生相同的目标像素内容。若未来
底层驱动逐字节正确地把这份 frame buffer 送到面板，静态图形内容应当对应。

它不能证明物理屏幕一定看起来完全相同。实际屏幕还会受到 SSD1681 驱动、LUT、
waveform、BUSY、刷新时序、残影、面板状态、方向和电气条件影响。当前这些都属于
另一个 Agent 的下层范围；本 handoff 不允许用浏览器 PASS 宣称物理 panel PASS。

## 提交边界

美术 checkpoint `59b776e` 的范围是上层组件和证据。未来提交前检查：

```powershell
git diff --cached --name-only
git show --format= --name-only HEAD
```

提交中不得出现：

`panel_target`、`ssd1681`、`display_queue`、`refresh_policy`、`waveform`、
`LUT`、`SPI`、`Flash`、`power`、受保护 owner acceptance。

## 人工边界

当前没有完成新的 canonical human acceptance；r4/r5 失败必须保留。下一次人工
验收只有在机器闭环重新 PASS 后才可以开始，并且要由产品 owner 明确说“开始验收”。
在此之前，当前版本是可复现的 inactive browser/WB55 upper-art checkpoint，
不是 runtime activation，也不是 physical e-paper acceptance。
