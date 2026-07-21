# Companion 情绪系统调研与候选设计（2026-07-19）

## 问题定义

当前 15 个 source-derived candidate state 只是可用的组件基线，不能被当成 15 张
轮流播放的“情绪卡”。owner 已明确：截图里的 Daily 方向图本质属于同一个角色状态；
产品需要的是更多可解释的情绪细节，以及情绪之间可追溯的因果关系。

本文件只定义产品行为与 source-mask 组合规则。它不授权新美术、整脸替换、代码绘制、
runtime activation，或 Charging/Error/Sleep 的日常脸 fallback。

## 外部调研

| 参考 | 可验证结论 | Companion 采用方式 |
|---|---|---|
| [Casio Moflin 官方说明](https://www.casio.com.cn/moflin/index/) | Moflin 使用二维情绪地图；同一陪伴角色的情绪是一个随互动演化的系统，而不是一次触发一张独立脸。 | 用连续 affect core 保存长期/短期倾向，屏幕只显示其当前可读的局部表演。 |
| [Casio Moflin 产品页](https://www.casio.com/us/moflin/) | 日常互动会影响情绪、依恋与个性，成熟后表现变得更丰富。 | `interaction_memory` 只影响可达的情绪倾向和力度，不随机替换角色脸。 |
| [Russell 情绪环模型综述](https://pmc.ncbi.nlm.nih.gov/articles/PMC2367156/) | affect 可由独立的 valence 与 arousal 维度组织；不同离散情绪在该空间中有邻近关系。 | 用 `valence` 和 `arousal` 做底层连续状态，避免从 calm 直接无因跳到 playfully excited 或 alert。 |
| [Affect-driven robot behaviour](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2022.717193/full) | social interaction、affective memory、time 与 personality 可以共同调制机器人当前 mood，而不是由一次输入永久决定。 | 事件写入 affect core；关系记忆调制目标；没有新事件时只缓慢回稳，不能播放状态轮播。 |
| [Apple GameplayKit state machines](https://developer.apple.com/documentation/gameplaykit/gkstatemachine?language=_5) | state machine 应显式声明可达 next state 与进入/退出行为。 | 编舞器必须产生可审计的 directed route，拒绝不允许的直接跳转。 |
| [Disney Animation 动画流程](https://www.disneyanimation.com/process/animation/) | anticipation、timing、secondary action、follow-through 让角色动作读成表演，而不是同步开关。 | bridge 由 gaze lead、brow answer、lower-face reply、approved accent follow-through 构成；每一拍只动一个因果组。 |
| [Sony aibo Communication](https://us.aibo.com/feature/feature2.html) | aibo 将 curiosity、emotion、desire、seeing/listening/touch 与逐步形成的 personality 连到实际行为，而不是把每次输入映射为一张孤立表情。 | `event` 先改变 continuous affect/attention，再选择当前可达 edge；情绪到达后保持为新的 baseline，绝不为了演示自动反向跳回上一张脸。 |
| [CASIO Moflin 官方产品页](https://www.casio.com/us/moflin/) | Moflin 把 Calm、Joy、Curiosity、Anxious 等放在情绪范围中；交流与互动让情绪和 personality 随时间演化，积极/惊吓/忽略等输入有不同方向。 | 保持 affect graph 的邻接边和 `interaction_memory`，把 browser 的无因正反循环替换为一次 event-causal bridge + target presence；反向 edge 只能由新的反向事件触发。 |
| [Kroczek & Muehlberger, Time to Smile](https://www.leon-kroczek.de/publication/kroczek-time-smile-how-2023/) | 虚拟 agent 的互惠表情响应感在约 700 ms 延迟附近达到峰值，时序本身会被读为社交信息。 | 从事件收到到第一拍 `highlight_lead` 的目标改为 650–750 ms；不再先静止 1200 ms 才开始回应。 |
| [Jiang et al., Dynamic appearance descriptor approach](https://research.utwente.nl/en/publications/a-dynamic-appearance-descriptor-approach-to-facial-actions-tempor/) | 面部动作不能只看静态终点；FACS action unit 的 onset、apex、offset 及其时间一致性都影响可读性。 | 每个 bridge 固定为 component-only 的 `onset`（高光）、`apex`（眉/下半脸/可选 accent）、`offset`（高光 settle），并对相邻 PBM 强制可见变化。 |
| [Emotional modulation of attention orienting by gaze](https://pubmed.ncbi.nlm.nih.gov/28344502/) | gaze shift 和表情展开的先后顺序会改变注意调制；在该研究中，表情跟随 gaze shift 时调制最强。 | 先只移动 primary highlights，再让 sparkle 追上，之后才更新眉和下半脸；避免所有组件在同一拍同步跳变。 |
| [Apple HIG Motion](https://developer.apple.com/design/human-interface-guidelines/motion) | motion 应服务状态/反馈、简短精确、可取消，避免无目的或持续振荡。 | 事件 bridge 可被新高优先事件取消；预览不再自动来回反弹。目标态停留后只允许 state-bound presence，而不是无事件的 emotion playlist。 |

## 四层候选模型

### 1. 身份 Rig

锁定 v9 眼型、眼体、固定 sparkle、鼻子、脸部锚点永远是同一角色。任何可见像素只能来自
已登记的外部 NOR `.crig` source mask；完整 PBM/CEMP 仅用于审计。该层不理解“开心”或
“好奇”，也不生成新线条。

### 2. 持续 affect core

```text
valence:       -2 .. +2   不愉快/中性/愉快
arousal:        0 .. 3    困倦/安静/注意/兴奋
affinity:       0 .. 2    interaction_memory 的关系倾向
attention:      center / left / right / up / down
baseline:       当前稳定表达族，不是当前图片
```

- 触摸会提高 `valence`、`arousal` 与 `affinity`；重复的亲密互动只提高 `affinity`，
  不直接硬切到 Heart/Playful。
- 录音与菜单是产品上下文，分别把可见表达暂时约束为 `focused` 与 `thinking`，退出时返回
  affect core 所允许的邻近 baseline。
- 没有事件时，`arousal` 先缓慢回到安静、`valence` 向中性回稳；只有在同一 selected
  baseline 内播放 component-presence 微表演。它绝不自行挑选另一张脸。
- Sleep/Charging/Error 没有本 active profile 的已批准构图，继续 fail-closed；V15 sleep
  one-shot proof 也不等于 active Rig binding。

### 3. 有向情绪图

可见表达族与现有 candidate source component sets 的对应关系如下；名称是行为语义，
不是让播放器轮换的卡片清单。

| 表达族 | 当前 component baseline | 典型原因 |
|---|---|---|
| calm | `calm_content` | 无新事件、低 arousal 回稳 |
| notice | `daily_attention_*` | 注意目标出现，方向来自 attention |
| curious | `curious_question` core（V11 question charm 未绑定） | 轻触、新信息、未知目标 |
| warm | `affectionate_warm` | 高 affinity 的温和互动 |
| joyful | `joyful_spark` | 积极结果/亲密互动后的正向释放 |
| playful | `playful_bright` | 高 arousal 且高 affinity 的滑动互动 |
| anticipatory | `anticipatory_notice` | 即将发生的已知动作 |
| puzzled | `puzzled_processing` | 信息尚未解析，必须先有 notice/curious |
| thinking | `menu_thinking` | 菜单或明确处理上下文 |
| listening | `listening_focus` | 声音/等待输入上下文 |
| focused | `recording_focus` | 正在录音或任务性专注 |
| alert | `alert_surprised` core（V11 exclamation charm 未绑定） | 高优先级、新颖刺激；非 Error fallback |

允许边只定义“下一步可以是什么”，而不是自动播放：

```text
calm -> notice/curious, listening, sleepy
notice -> calm, curious, anticipatory, focused, alert, puzzled
curious -> calm, warm, playful, anticipatory, puzzled, thinking, alert
warm -> calm, curious, joyful, playful
joyful -> warm, playful, anticipatory, calm
playful -> joyful, warm, curious, calm
anticipatory -> notice, curious, alert, focused, joyful, calm
puzzled -> curious, thinking, alert, calm
thinking -> puzzled, curious, focused, calm
listening -> focused, curious, calm
focused -> listening, thinking, alert, calm
alert -> notice, focused, anticipatory, calm
```

编舞器必须做 deterministic breadth-first route selection：同一 current affect、event、attention、
energy、memory 和 seed 得到同一条最短合法路径；不在图上的跨越必须被拒绝或经中间节点桥接。
`event` 能临时抢占，但其退出仍按图回到可达 baseline。

### 4. 组件级 bridge

从 source baseline A 走到 B 时，浏览器与目标端消耗同一 registered-component sample plan：

1. `source_hold`：保持 A 的完整身份锚点。
2. `gaze_lead`：仅 primary highlights 朝 target attention 预备。
3. `gaze_arrive`：另一眼跟随；sparkle、眼体、鼻子固定。
4. `brow_answer`：只替换/移动成 B 的双眉组。
5. `lower_face_reply`：只替换/移动成 B 的嘴与腮点组。
6. `accent_follow_through`：仅当 B 有 owner-approved accent 时最后进入；V11 question/exclamation
   在 V16 acceptance 前绝不可出现。
7. `target_hold`：B 成为新的稳定 baseline，再使用其 presence track。

每一拍都只由已登记 component id、原始 base position 和 legal offset 组成。桥不能把 A 的全脸
替换为 B 的全脸，也不能让所有 facial components 获得同一个平移向量。由于电子纸是离散刷新，
它使用少量可读关键帧而不是模拟 OLED 高帧率。

## 2026-07-19 V21 审阅后的研究驱动细化

V21 component-bridge 的首轮 canonical screen review 选择 `需修改`，备注为：
`看着还行, 就是这种感觉, 记录一下, 另外情绪切换要上网看看人家怎么弄的`。
这保留了 component-level direction，但拒绝把首轮节奏当作最终屏幕体验。研究后的下一候选遵循：

1. **事件到意图的响应窗口**：event 到 `primary_highlight_lead` 目标为 650–750 ms；当前 1200 ms
   `source_hold` 改为约 680 ms。这个数值是用于 V21 的可测试设计目标，不声称对电子纸本身做了人因测量。
2. **眼神先于表情**：`primary_highlight_lead` 和 `sparkle_arrive` 分两拍；前者只移动白色主高光，
   后者才让小 sparkle 跟随。眼体与鼻子全程不动。
3. **动作有起、峰、收**：眉在 `brow_apex` 到位；嘴/腮点在 `lower_face_apex` 回应；只有 Playful 的
   已批准星形饰物在最后出现/离开；高光在 `settle` 回到目标 baseline。
4. **情绪不是 demo ping-pong**：一次 bridge 结束后停在 target baseline。浏览器重播或反向边仅能由
   owner 显式选择或新的相反 event 触发，不能自动 `A -> B -> A` 往返。
5. **目标态仍然有生命感**：长期可见动态只允许 target selected-state 的 component-presence micro-performance；
   它不更换 emotion、不越过 affect graph，也遵守电子纸 refresh policy。

V21 研究细化仍只使用已接受的 V21 source components 与 locked V9 identity。它不生成新美术，
不修改 v9 原图，也不授权 CRIG/runtime、Menu/Recording/Upgrade、Sleep、Charging 或 Error fallback。

## 2026-07-19 行为仲裁重构：不允许随机抽表情

owner 进一步明确：编舞的职责是把已经被选中的交互意图演成组件级动作，不是为了“看起来活着”
而从表情或 gaze 方向中随机抽签。以下调研只采纳可追溯的成熟 social-robot 行为架构与 HRI
一手研究，不把人类面部连续动画直接套到离散刷新电子纸上。

| 参考 | 可验证结论 | Companion 的具体约束 |
|---|---|---|
| [MIT Kismet behavior system](https://groups.csail.mit.edu/lbr/sociable/behavior.html) | 行为系统以 attention、motivation 和可仲裁的行为来组织社交回应；affect 是行为选择的一部分，而不是独立播放列表。 | 保留 `affect`，但每次只输出一个已说明原因的 `intent`；没有事件时不会跨 baseline。 |
| [Breazeal, A Motivational System for Regulating Human-Robot Interaction](https://web.media.mit.edu/~cynthiab/Papers/BreazealAAAI98.pdf) | drive、emotion 与 behavior 是耦合的：情绪要影响当前 goal/行为竞争，而不只是显示符号。 | `event` 先更新 `valence/arousal/affinity`，再在 directed graph 内选 target；不能直接从 seed 得到一张脸。 |
| [See You See Me: the Role of Eye Contact in Multimodal HRI](https://pubmed.ncbi.nlm.nih.gov/28966875/) | mutual gaze、共同注意和对物注意是可区分的互动状态。 | 高光/attention 方向只取真实 `attention` 输入；CENTER 是明确的无方向注意，绝不用 seed 偷换成左/右/上/下。 |
| [Timing of emotional expression in HRI](https://portal.findresearcher.sdu.dk/en/publications/triggering-anthropomorphism-or-depicting-a-robot-character-the-ef/) | 情绪表达相对于交互内容的时序会改变用户如何理解机器人，而不是可随意装饰的节拍。 | `intent` 选定后才运行 gaze/highlight lead -> local face response -> hold；实机/浏览器节奏取同一 trace，不能随机重播或自动反向。 |

### 可执行状态合同

`comp_expression_rig_behavior_state_t` 是唯一的表情选择记忆：

```text
affect.baseline         当前已选的稳定表达族
affect.valence/arousal  由事件按有界规则改变；Daily 只向静态倾向回稳
affect.affinity         只随 interaction_memory 明确增加或在 Daily 低于当前记忆时逐步衰减
active_intent           当前拥有 bridge 的唯一行为意图
remaining_hold_steps    最短两次调度步的抗闪烁保持
```

`comp_expression_rig_resolve_behavior()` 的输出必须包含 `intent`、`reason`、
`target_emotion`、`target_attention`、`event_priority`、`cancels_active_intent` 和完整
`route`。它执行以下不可变规则：

1. `DAILY_AUTO` 只能保持当前 `affect.baseline` 并消耗已记录 hold；它不选择新情绪、
   新 gaze 或新时间拍。
2. Touch/Wake/任务事件先经 affect appraisal，再得到唯一 intent；同样的 state/history/input
   得到 bit-for-bit 相同的 decision，`seed` 仅为旧调用方保留，选择器完全不读取它。
3. 路由必须调用现有 deterministic breadth-first directed emotion graph；不允许的跨越仍须经
   notice/curious/warm 等中间语义节点。
4. 低优先级事件在 active intent 的最短 hold 内只能得到 `active_intent_hold`，不能抢画面；
   只有更高优先级事件能设置 `cancels_active_intent=true`。
5. 解析出的 intent 仍可能没有已接受的专属美术。此时 renderer 必须 fail-closed；行为决策
   绝不借日常 face 去伪造 Recording/Menu/Upgrade/Sleep/Charging/Error 的完成状态。

原生 host 证据 `companion-v9-expression-choreographer-20260719-deterministic-behavior.json`
固定验证 idle 不消费或解释 seed、familiar touch 走 `calm -> curious -> affectionate` 的 warm
路径、较低优先级 context 不能打断该路径、Error 只能作为更高优先级的行为决策而仍被 visual
renderer fail-closed。候选资源仍为 runtime inactive。

## 自动判定

实现后必须新增/扩展机器证据，至少覆盖：

1. affect 值域、事件更新和同输入同 seed bit-for-bit 一致。
2. 每个表演族的 route 只经过图中允许的边；至少覆盖 calm -> notice -> curious、
   curious -> warm -> playful、notice -> puzzled -> thinking、notice -> alert/focused 四条路径。
3. 一次自动 idle 只播放 selected baseline 的 presence track，绝不自动选择新 state。
4. 每个 bridge 样本只改变一个因果组；highlights 先于 brow，brow 先于 lower face，approved
   accent 最后；眼体、sparkle、鼻子全程保持 v9 identity anchor。
5. browser、target PBM 和 external-NOR CRIG 逐 sample 像素一致；所有 layer 均为已登记 source
   component，Charging/Error/Sleep 仍为 fail-closed。

新的情绪词若没有能支撑它的 approved source component vocabulary，不得先用日常脸假装完成；
必须走锁定 V9-only 的版本化 prompt、生成、导出、机器 gate 和 owner art review。

## 2026-07-20 触摸预览失败 Triage

第一次 runtime-inactive 的触摸预览机器闭环通过，但 canonical browser-only review 选择
`失败`，原始备注为 `完全和以前的风格不同`。这不是可被 host trace 掩盖的审美细节：审计显示
notice 的前五个 keyframe 是已接受的 `daily_right` source-component score，而后续 Touch scene
仍通过旧 `scene_charms.touch = charm_question` 进入被 COMP-REQ-135 拒绝的 V11 问号 glyph。

修复原则如下：

1. `charm_question` 保留为不可删除的 rejected audit mask，但从 active Touch binding 移除；不得
   换成星号、心形或任何其它旧 charm 来伪装同一个语义。
2. `touch_tap` 继续是真实 event 和 affect intent，familiar route 仍为
   `calm -> curious -> affectionate`，但在完整、经 owner-art-review 的 Touch special pose 出现前，
   它的视觉只使用已确认的 Daily V9 grammar。
3. 每次 bridge/target 的 component plan 都必须 machine-audit 为不包含 `charm_question`；它仍可
   使用合法的高光、眉、嘴和腮点 offset，但不能声称已获得新的 Curious/Affectionate 专属 source。
4. 下一次 browser review 必须以修复后的同源 player 为对象。此次 FAIL 是回归证据，不能创建
   accepted baseline，也不能授权 runtime、动态刷写或物理面板验收。
