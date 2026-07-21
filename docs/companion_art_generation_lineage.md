# Companion 美术生成与编舞全套接手档案

本文是 V9 到当前 V45/r7 上层美术的历史索引。它回答三个问题：

1. 这些图是怎样一步步从锁定 V9 源图生成成组件的。
2. 哪些 prompt、request、lineage、台账和 owner 反馈必须保留。
3. 当前表情、情绪切换、编舞和浏览器/WB55 组件计划到底以什么为准。

下一位 AI 先读本文，再读 [V45/r7 美术接手文档](companion_v45_art_handoff.md)、
产品 registry 和机器证据。不要把聊天上下文、旧图片文件名或旧生成 HTML 当作
当前行为合同。

## 当前结论

- 当前 owner-facing 美术版本：`v45-touch-failsafe-r7-20260721`。
- 当前组件计划：
  `docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/`。
- 当前生成页面：该目录下的 `wb55-browser-parity-attempt-01/index.html` 和
  `expanded-review-wall-01/index.html`。
- 当前 profile：`app/companion_pendant/epaper/generated/expression_rig_v45_complete_eye_candidate_profile.c`。
- 当前计划是 15 个 expression tracks、4 个 functional decoration tracks、1 个
  短暂的 menu-entry track；计划内的 200x200 帧由注册 component mask 组合，不是
  整脸贴图轮播。
- 当前状态是机器闭环完成、runtime inactive、人工验收未完成、物理墨水屏未验收。

## 必须保留的历史

`docs/art/iterations/companion-pet-expression-v9*/` 下的文字和结构化元数据是
不可丢失的生成历史，尤其是：

- `generation-prompt*.md`、`prompt*.md`
- `generation-request*.json`、`request*.json`
- `source-lineage*.json`、`art-lineage*.json`
- `iteration-ledger*.json`、`art-direction-ledger*.json`
- `choreography*.json`、`*-layout.json`、`*-target-profile-plan.json`
- `review*.json`、`triage*.json`、owner 反馈和拒绝记录

完整机器清单由
`tools/verify_companion_art_handoff.py` 生成到
`docs/validation/companion-art-generation-lineage-manifest-20260721.json`。
清单记录每个文字/JSON 文件的相对路径、类别、大小和 SHA256；它不依赖图片仍然
存在。这样以后清掉生成图时，prompt 和“为什么这一版被取代”仍能接手。

不要把 prompt 历史和图片现状混为一谈：prompt 可以重现意图，但图像生成本身
可能有变化。要保留当前精确候选，至少保留锁定 V9 源图、当前 component masks、
当前 CRIG、layout 和 target profile。

## 版本路线

### V9：角色视觉母体和硬约束

入口文件：

- `docs/art/iterations/companion-pet-expression-v9/generation-request.json`
- `docs/art/iterations/companion-pet-expression-v9/art-direction-contract-v1.md`
- `docs/art/iterations/companion-pet-expression-v9/art-direction-contract-v1.json`
- `docs/art/iterations/companion-pet-expression-v9/art-lineage-v1.json`
- `docs/art/iterations/companion-pet-expression-v9/iteration-ledger.json`

V9 是唯一的视觉 parent，不是以后可以随手重画的参考图。其硬约束是纯黑白、
200x200 目标、紧凑黑色椭圆眼、白色高光、成对眉毛、鼻子、W-mouth、脸颊点和
留白。V9 源图本身禁止修改，SHA256 为：

`919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA`

后续 prompt 的共同原则是“从 V9 派生 source-only component”，不是生成另一张
完整角色脸。

### V9 extension V1 到 V9：先修眼睛，再建立日常注意力

这些目录保留了每次生成的 request 和 iteration ledger：

| 目录 | 主要目的 | 原始结果 | 现在怎么用 |
|---|---|---|---|
| `extension-v1` | 第一轮扩展源 | owner 拒绝眼睛几何 | 历史 prompt |
| `extension-v2` | 开眼身份修复 | machine 拒绝 | 历史 prompt |
| `extension-v3-daily-eye-proof` | 日常眼神证明 | owner 拒绝预览方向 | 历史 prompt |
| `extension-v4-emotion-transition-anchors` | entry/hold/settle 锚点 | machine 拒绝日常可读性 | 编舞概念来源 |
| `extension-v5-emotion-anchors-direction-repair` | 高光方向修复 | machine 拒绝开眼身份 | 历史 prompt |
| `extension-v6-down-gaze-compact-reflection` | down gaze 和睡眠休息 | machine 拒绝 | 历史 prompt |
| `extension-v7-daily-direction-strip` | 四方向日常 strip | owner 拒绝情绪谱系 | 历史 prompt |
| `extension-v8-emotion-anchor-panel` | 八个情绪 anchor | owner 拒绝情绪谱系 | 历史 prompt |
| `extension-v9-expanded-daily-direction-strip` | 四方向完整 source bundle | owner 批准 source bundle | 历史 source 参考，不是整脸 runtime |

这里最重要的经验是：方向应该用眼内小高光和受控的成对 offset 表达；不能变成
换眼型、斜眼、半边白眼或整脸贴图。

### V10 到 V15：情绪谱系、睡眠组件和动态证明

- `extension-v10-expanded-emotion-panel` 和 `extension-v11-secondary-detail-kit`
  保存了 owner 批准的历史 source bundle。它们不是当前 profile 的直接入口。
- `extension-v12-sleep-anchor-repair`、`extension-v13-sleep-micro-component-repair`
  记录睡眠锚点和微组件缺失的修复；仍保留原始失败状态。
- `extension-v14-sleep-zzz-component-repair` 把 ZZZ 组件和动态证明单独登记，
  结果要求继续优化，不能把静态一张图冒充编舞。
- `extension-v15-sleep-rig-pose-source` 把睡眠 source 与 component choreography
  分开，并保存两个 dynamic-proof layout。

关键经验是：睡眠是注册的眼、眉、嘴和 ZZZ 小组件依次进场；不是把整张睡脸
替换进去。

### V16 到 V22：从装饰尝试转向可解释的情绪组件

- V16 `semantic-charm-refinement`：语义小装饰。
- V17 `functional-context-accents`：功能上下文装饰。
- V18 `menu-special-expression-source`：菜单短暂提示。
- V19 `recording-special-expression-source`：录音状态。
- V20 `upgrade-special-expression-source`：升级状态。
- V21 `everyday-emotion-distinction-source`：日常情绪区分。
- V22 `emotion-separation-source`：把情绪拆成可注册的 face components。

V21/V22 的 prompt、request、generated metadata、component layout 和 CRIG JSON
都要保留。当前 V45 的 face track 依赖 V22 face pack；这不是让 V22 的旧整脸
预览重新成为 runtime，而是复用其已登记的眼、眉、嘴、脸颊、鼻和高光组件。

### V23 到 V33：特殊情绪/物件探索，全部按历史候选归档

这些目录保留了完整的多轮 prompt 和 request：

`extension-v23-core-special-expression-source`、
`extension-v24-glance-readable-special-expression-source`、
`extension-v25-representative-special-expression-source`、
`extension-v26-action-verb-special-expression-source`、
`extension-v27-face-action-gesture-special-expression-source`、
`extension-v28-iconic-ornament-special-expression-source`、
`extension-v29-silhouette-object-special-expression-source`、
`extension-v30-minimal-functional-object-special-expression-source`、
`extension-v31-mouth-contrast-functional-object-special-expression-source`、
`extension-v32-representative-functional-silhouette-special-expression-source`、
`extension-v33-action-readable-special-expression-source`。

其中 V26、V27、V29、V30、V32、V33 的 metadata 明确记录过内部或 owner 级拒绝、
source gate 未通过或已 superseded。它们的图可以清理，但 prompt、request、
source-lineage、rejected/triage 记录不能删除或改写。下一位 AI 不应从这些目录
直接挑一张图作为当前脸；如需复用，只能沿当前 V45 layout 的 component id、mask、
anchor 和 legal offset 重新登记。

### V34 到 V40：功能装饰与 two-track Rig

- V34/V35 special decoration source/rig：把 charging、recording、upgrade、
  error 等功能状态变成脸外的小装饰，并保留 face track。
- `function-state-decoration-source-v1` 和
  `functional-decoration-source-v2`：录音波形、菜单网格、升级刻度、错误提示
  等 source-only icon 的 prompt 和 choreography interpretation。
- `rig-v1`、`rig-v2-expanded-source`、`sleepy-dream-rig-v1`、
  `special-decoration-rig-v1`：早期注册和评分产物，作为历史 machine evidence。
- `two-track-rig-v1` 到 `two-track-rig-v3`：逐步把 expression track 与 functional
  decoration track 分开。
- `two-track-rig-v4`：V42 expression extension，保留 machine closure revisions。
- `two-track-rig-v5`：V43 recording input inward，波形朝向 Companion 内侧。
- `two-track-rig-v6`：V44 stable-center blink。
- `two-track-rig-v7`：当前 V45 complete-eye source、target plan 和 r7 浏览器
  fail-safe 修复。

V34/V35 的设计重点是：功能事件只叠加小装饰，不替换表情脸；最终帧是
`expression_track + functional_decoration_track` 的确定性 union。

### V41 到 V45：当前组件 ancestry

当前 V45 CRIG 中的主要 ancestry 关系如下：

| 当前来源 | 进入 V45 的内容 | 生成/登记方式 |
|---|---|---|
| V22 face | 6 类主要情绪的眼、眉、嘴、脸颊、鼻和高光 | source component + mask + offset |
| V9 sleep / V42 sleep | sleepy eyes、mouth、ZZZ | 小组件组合 |
| V38/V40 functional | menu、upgrade、error 的功能装饰 | 第二轨 union |
| V42 emotion | delighted、bashful、thoughtful、focused 等情绪细节 | source-derived component |
| V43 recording | 固定麦克风和向内波形 0/1/2 | 固定 anchor，不重新生成整脸 |
| V44 blink | 对称 closed-eye 基础 | 组件来源 |
| V45 complete-eye | closing/closed/opening 完整眼组 599-604 | 仅 idle blink choreography 使用 |

V45 当前登记的 source pack 有 60 个组件，包含 37 个 V22 face source 和 60 个
V45 special source 入口；实际组合必须以
`v45-special-component-layout.json` 和
`v45-wb55-target-profile-plan.json` 为准，不以文件名猜位置。

### 旧的顶层美术文档如何看

以下文件仍然有研究或历史价值，但已经加上“历史兼容文档”标记，不能再作为
当前入口：

- `docs/companion_expression_animation_contract.md`
- `docs/companion_expression_emotion_system_cn.md`
- `docs/companion_expression_emotion_system_research_20260719.md`
- `docs/companion_expression_motion_research_20260717.md`
- `docs/companion_expression_reference_model.md`
- `docs/companion_screen_expression_system.md`
- `docs/companion_total_scene_expression_contract.md`
- `docs/validation/companion-v9-art-baseline-20260716.json`

它们不删除，因为其中保留了旧的产品推理、source hash 或机器证据；但接手时只
从本文和 V45 handoff 进入。这样既清掉了“哪个文档才是现在的基线”的歧义，也
保留了未来继续修美术时需要的上下文。

## 当前编舞合同

### 帧模型

每个故事由可读的阶段序列组成：

`entry -> lead -> response -> hold -> settle`

每帧至少登记 `cue`、`duration_ms`、`scene`、`emotion`、`attention`、组件层、
offset、source pack 和必要的 semantic role。生成器按 source component 合成
200x200 1bpp 帧；不允许用 `img` 轮播整张脸，也不允许 Canvas 临时绘制五官。

### 当前故事

| story/track | 含义 | 关键帧节奏 |
|---|---|---|
| `calm_presence` | 日常平静 | `calm_entry 220`，idle blink 的 `140/120/150`，`settle 6800` |
| `warm_presence` | 亲近温暖 | `220/180/260/760/360 ms` |
| `curious_question` | 好奇提问 | `180/180/260/760/360 ms` |
| `alert_exclamation` | 警觉提醒 | `180/180/260/760/360 ms` |
| `playful_presence` | 活泼玩心 | `220/180/260/760/360 ms` |
| `sleepy_presence` | 困倦入睡 | `420/360/320/420/1400 ms` |
| `delighted_presence` | 开心雀跃 | `220/180/260/760/360 ms` |
| `bashful_presence` | 害羞轻笑 | `220/180/260/760/360 ms` |
| `thoughtful_presence` | 安静思考 | `220/180/260/760/360 ms` |
| `focused_presence` | 认真专注 | `220/180/260/760/360 ms` |

机器用的 `daily_attention_center/left/right/up/down` 是内部可复现的眼神端点，
不是 owner-facing 五张额外整脸。功能轨包括 `recording_input`、
`bottom_connector_charging`、`upgrade_progress`、`error_caution`；菜单入口
只有很短的 `menu_entry_notice`，最后撤出 Rig 后由菜单 UI 接管。

### 眨眼规则

眨眼是 `calm_presence` 日常 idle 的确定性事件：

- open interval：`6800 ms`
- closing：`140 ms`
- closed：`120 ms`
- opening：`150 ms`
- cycle：`7430 ms`
- random facial motion：关闭

这套 V45 complete-eye 组件只能被 idle schedule 选中。鼠标按下、拖动、触摸按下、
release 都不能把当前 cue 强制改成 `blink_closing`、`blink_closed` 或
`blink_opening`。

### 按下、拖动、释放和情绪切换

当前交互的准确含义是“有情绪互动，但不是按下立即换情绪脸”：

1. `pointerdown/touch_begin`：冻结当前主脸 frame、story index 和 frame timer；
   只更新合法 gaze/highlight/sparkle overlay。
2. 小范围 `move/drag`：继续只改变 overlay，不推进 frame，不触发 blink，不重置
   story，不替换主脸。
3. 超过已登记阈值的横/竖 swipe：才浏览相邻 story；这不是普通按下的副作用。
4. `pointerup/touch_release`：先把 gaze 回到当前帧的 center，再按剩余/合理
   resume delay 继续同一个 story 和同一个 frame 位置；不能直接跳到下一张
   blink frame。

所以“按下有互动”答案是：有，互动表现为 Companion 看向/回应触点的眼神高光和
小星光变化；按下本身不是 emotion switch。未来如果要把按下改成情绪切换，必须
先记录新的产品 steering，再单独改行为合同和验证，不能把它偷偷塞进 pointerdown。

## 生成和修改规则

1. 所有新 prompt 先引用锁定 V9，并写清楚是 source-only component，不生成完整
   runtime face。
2. 只用 crisp black/white 1bpp-ready source；禁止灰阶、渐变、抗锯齿、文字、
   UI 框、cat outline、legacy art、custom LUT 和 code-drawn facial geometry。
3. 先保留原始 prompt，再写新的 `generation-request` 和 `source-lineage`；不要
   覆盖旧 prompt，失败也要留下。
4. 从候选图到 runtime 前必须登记 component id、role、mask、mask hash、anchor、
   base position、legal offset range、z-index、composite op 和 semantic role。
5. 表情形状改在 source/mask/layout；编舞改在 target profile；浏览器行为改在
   renderer 和 Playwright/strict pixel verifier；不要手改生成 HTML/C/profile。
6. 新版本必须新建 revision 和 cache-busted URL；历史 r4/r5 失败不能覆盖。

## 哪些可以清理

### 可以清理的生成产物

- 已被 V45 取代的旧 PNG/PBM/GIF preview。
- 旧 attempt 的重复导出物和重复 browser playback screenshot。
- 不再被当前 layout、CRIG、profile 或 verifier 引用的旧渲染目录。

清理前先运行 prompt manifest；清理动作只针对图片/二进制预览，不删除同目录的
prompt、request、lineage、ledger、review、triage 和 layout/plan JSON。若清掉当前
V45 的 exact candidate，下一位 AI 只能依据 prompt 重做，不能保证得到同一像素；
因此至少先保留当前 V45 masks、CRIG、layout、target plan 和当前浏览器 evidence。

### 不能清理的东西

- 锁定 V9 源图和它的 SHA256。
- `companion-pet-special-system-owner-acceptance-20260717.json` 及其 SHA256。
- r4/r5 的 owner 失败记录和总审计中的旧 accepted blink note。
- 所有 prompt/request/lineage/ledger/review/triage 文字历史。
- 当前 V45/r7 的 source pack、component masks、layout、target plan、浏览器截图和
  real-browser pixel report，直到新的版本完成替代闭环。
- 任何下层驱动、panel、SSD1681、LUT、waveform、BUSY、刷新、电源、SPI、Flash
  文件；它们不属于本美术清理。

## 重新接手的最短路径

```powershell
git status --short --branch
python tools/verify_companion_art_handoff.py --check
Get-Content docs/companion_art_generation_lineage.md
Get-Content docs/companion_v45_art_handoff.md
Get-Content docs/companion_product_requirements.md
```

若只是改一张表情，优先保持 component id、anchor、semantic role 和故事 cue 不变，
只替换 source mask 并更新 hash。然后重新生成 single/expanded 两页，做真实
Edge press/drag/release 像素证据，再跑 V45 host、expanded verifier 和 total audit。

当前浏览器/WB55 上层与物理屏的边界、截图路径、测试命令和人工验收边界，统一看
[companion_v45_art_handoff.md](companion_v45_art_handoff.md)。
