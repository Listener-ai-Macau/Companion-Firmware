# Companion OLED-to-e-paper 表情编舞研究

研究日期：2026-07-23（访问日期均为 2026-07-23）
研究者：Luna
范围：仅联网一手资料与仓库内约束核对；不修改产品代码、美术、driver、menu、production 或硬件。

## 结论摘要

成熟实现通常把“语义状态”与“可见通道”分开：情绪/意图选择目标状态，眼位、睑线、highlight 和一次性动作在独立通道上合成。高质量感主要来自有界的状态迁移、明确的 gaze/blink 时序、可打断但可恢复的动作，以及微动作叠加；并不要求把整张脸每帧重画。

OLED/TFT 项目依赖高刷新连续插值：RoboEyes 默认 50 fps，并以 `millis()` 限制绘制；Adafruit Uncanny Eyes 以 ARM 板、高速 SPI 和预生成图形表驱动 OLED/TFT。Companion 的约 470 ms 离散帧不能复制这些连续运动，应该把 easing/overshoot 转译成少量确定性关键姿态与 hold，而不是伪造随机或新几何。

## 一手来源与证据

| 来源 | source type | 关键证据摘要 | 可迁移判断 |
|---|---|---|---|
| [FluxGarage/RoboEyes](https://github.com/FluxGarage/RoboEyes) | 原作者官方开源仓库 | README 明确支持 configurable eye geometry、`DEFAULT/TIRED/ANGRY/HAPPY` mood、八方向 position、open/close、autoblinker、idle、confused/laugh oneshot；`begin(width,height,max framerate)` 和 `update()` 有显式帧率门。源码还保存 current/next geometry，并在 `drawEyes()` 中逐步靠近目标。 | 语义 mood、目标/当前状态、独立 blink/idle/oneshot 是可迁移结构；50 fps、逐像素连续插值和随机 interval 不可直接迁移。该项目没有证据表明存在通用 priority/interruption scheduler，故不能从它推导抢占策略。 |
| [Adafruit/Uncanny_Eyes](https://github.com/adafruit/Uncanny_Eyes) 与 [官方 guide](https://learn.adafruit.com/animated-electronic-eyes?view=all) | 制造商官方仓库/文档 | 官方仓库说明支持 Adafruit 1.5in OLED 和 1.44in TFT，`convert` 目录生成可 include 的图形头文件；guide 说明每眼一块显示器、可选 joystick/button/photocell，软件自主处理效果；眼睑像素阈值随帧变化以形成 blink。 | 预生成组件/帧表、输入驱动与“整眼由合法部件构成”可迁移；颜色、alpha、每帧 threshold 和 ARM 高刷新路径不可迁移到 1bpp e-paper。 |
| [Misty II Interaction System](https://docs.mistyrobotics.com/misty-ii/interaction-system/overview/) | 真实教育/开发机器人官方 SDK 文档 | Misty 动作脚本有 `PAUSE:timeMs`、`STOP`、`HALT`、`RESET-LAYERS`、`RESET-EYES`，并可发 `IMAGE`、`TEXT`、`VIDEO`、`LED`、`HEAD`；官方 API 还有 display layers、image/video/text 与清理语义。 | 这是“事件脚本 + 有界清理 + 显示层”的成熟调度参考：高优先级事件应取消/清理低优先级 transient，结束必须回到单一基态。Misty 的多层、视频和 480x272 彩色屏不应搬到 Companion。 |
| [Gaze behaviour, believability, likability and the iCat](https://link.springer.com/article/10.1007/s00146-009-0198-1) | 原创论文，Springer，2009 | iCat 动画引擎固定 10 fps，多 channel，可 merge 或 fade；gaze 系统把 vergence、VOR、smooth pursuit、gaze shift 作为子系统，并把 eyes/head/eyelids 分通道；输入是 gaze target，输出是当前 embodiment state。论文还描述了 gaze 先于复杂行为、需要与动画引擎交互的结构。 | “语义目标 -> 通道目标 -> 当前状态迁移”比单一大表情更稳；通道合成和 fade 可转成 Companion 的 source-component 阶段。10 fps 是其实现事实，不是 Companion 470 ms 的性能承诺。 |
| [I Reach Faster When I See You Look](https://pmc.ncbi.nlm.nih.gov/articles/PMC3342577/) | 原创 HRI 论文，PLOS/PMC | iCub 实验比较 head-fixed、full-gaze、sunglasses；full gaze 中眼/头指向先于 speech，参与者的手部反应出现 anticipatory timing；遮挡眼睛时需等约 600 ms 的头部运动。 | gaze 是事件前置 cue，不应等到语义动作结束才出现；在 Companion 可用一个先导 gaze frame，再做 expression hold。600 ms 是该实验条件，不应机械复制为产品计时。 |
| [Analysis of Timing and Effect of Visual Cue on Turn-Taking](https://www.jstage.jst.go.jp/article/jrobomech/34/1/34_55/_pdf/-char/ja) | 原创论文，Journal of Robotics and Mechatronics，2022 | 研究直接操纵 robot visual cue 的 turn-taking timing，讨论 gaze/face cue 与 speech 的先后及人类可能错过 timing 的风险。 | 对话 cue 要有可测试的相对顺序与 hold；对 Companion 应写成离散 phase 序列和边界，而非追求连续曲线。 |

## 观察维度

### Semantic emotion state

RoboEyes 将 `mood`、position、curiosity、open/close 作为可独立设定的状态；iCat 将 gaze target 作为输入，再由 gaze 子系统修改相关 actuator vector。可迁移的架构是：`semantic_state` 只选择一个完整表情目标和少数允许的通道参数；渲染器只消费已锁定的 source components。不要把情绪直接编码为任意像素或运行时画新脸。

### Eye/gaze/blink

成熟系统将 gaze 作为高频或独立通道，blink 作为短 one-shot，且可与 mood 同时存在。Companion 应把 gaze、blink、highlight/sparkle 的阶段写进每个离散序列，但每个物理提交仍只呈现一张完整表情；保留 locked-V9 白 eye highlight/sparkle。

### Anticipation / attack / hold / settle / recovery

论文中的 gaze-before-speech 与 iCat 的 current/required state 说明：动作应有先导、到达、保持和回归。对于约 470 ms 帧，建议把它们表达为 `lead -> attack -> hold -> settle/recover` 的有限序列。不存在足够时间时宁可减少 phase 数，不可叠加第二个完整脸或跨帧留下旧组件。

### Easing / overshoot

OLED 可用连续 easing；RoboEyes 采用 current/next geometry 的渐进靠近，显示器以 50 fps 采样。e-paper 不应在约 470 ms 的一次提交中声称有连续 easing。可迁移版本是预选 1 个中间关键姿态，必要时 1 个受限 overshoot 姿态，之后必须回到合法 settle；overshoot 只允许改变 locked component 的位置/阶段，不允许创造几何。

### Micro-action layering

RoboEyes 的 mood、curiosity、flicker、sweat、autoblinker、idle 与 oneshot 是可观察的叠加入口；iCat 明确支持多 channel merge/fade；Misty 使用 display layers。Companion 可采用有限层：base emotion、gaze/blink、highlight/sparkle、合法 decoration，每层均从 locked-V9 source components 取值，最后合成一张完整 frame。

### Priority / interruption

Misty 的 `STOP/HALT/RESET-*` 提供明确的中断/清理语义；iCat 的 channel 模型说明通道可合并但需有最终 state。直接可交给 Sagan 的实现约束应是固定优先级：安全/故障清理 > 触摸反馈 > 语义情绪 > idle；抢占时丢弃 transient remainder、保留当前完整 frame 作为新序列起点，并在 bounded duration 内回到一个合法状态。这个 priority 表是 Companion 规则建议，不是对 RoboEyes 的事实归因。

### Idle variation / touch follow

RoboEyes 的 idle/autoblinker 使用随机 interval variation；这在 OLED 上可以避免机械重复。COMP-REQ-407 明确要求 Companion 规则无随机，因此应改为固定、循环长度与固定索引的 idle pattern。iCat 的 gaze target 输入以及 Misty 的事件/skill 模型支持“事件输入改变目标”；Companion 的 touch follow 应只选择有限方向/有限幅度的 locked component，不做每触点连续追踪。

### Bounded scheduling

Misty 的脚本 pause/stop/reset 与 iCat 的固定 10 fps engine 都是显式时序边界。Companion 每个序列应有固定最大 frame 数、固定 timer、固定恢复帧；不允许阻塞等待、隐式 retry、无界队列或随机延迟。R6 物理 baseline 的显示时序是受保护的下层约束，不由本研究重新解释。

### Authoring / testing

Adafruit 的 `convert` 工具把源图形生成 include 表；RoboEyes 把 API 参数暴露为可复用 mood/animation 调用；iCat 论文用固定 engine 与用户测试比较静态/动态 gaze；Misty 用可执行脚本动作。适合 Companion 的 authoring contract 是：组件白名单、状态/phase/timer 表、每帧 200x200 1bpp、源到逻辑像素零差异、合法 bbox、highlight 保留、序列唯一终态，以及负例测试（随机、双脸、越界、未清理 transient、重复激活）。

## OLED-to-e-paper adaptation matrix

| 能力 | OLED/TFT 成熟做法 | Companion 适配 | 结论 |
|---|---|---|---|
| 帧率 | 30-60 fps 连续 draw/interpolation（RoboEyes 默认 50 fps；Adafruit ARM/SPI） | 约 470 ms 离散提交；固定 frame index | 只保留关键姿态和顺序，不模拟连续运动 |
| 几何迁移 | 每帧像素/向量可变 | 200x200 1bpp、locked-V9 source components | 可迁移目标状态，不迁移新几何 |
| blink | 多帧快速闭合/打开，阈值或插值 | 固定 2-3 个离散阶段，完整脸提交 | 可迁移 phase，不迁移阈值细节 |
| gaze | 八方向、smooth pursuit、目标点追踪 | 有限方向表、固定 lead/hold/recover | 可迁移语义与相对顺序；触摸需量化 |
| easing | 每帧 current -> next，连续速度 | 0-1 个中间 keyframe，固定 settle | 只迁移形状意图 |
| overshoot | 连续曲线短暂超调 | 最多一个白名单姿态，固定回收 | 需有界且可验证 |
| micro-actions | channel merge/fade、flicker、sweat | base + gaze/blink + highlight/sparkle + legal decoration | 最终必须单一完整表情 |
| idle | 随机时间/位置 variation | 固定周期、固定序列、无 RNG | 迁移变化感，不迁移随机性 |
| interruption | 实时 loop/animation engine | 优先级队列 + cancel token + bounded recovery | 迁移调度概念，固定状态机实现 |
| authoring | 预生成图形表、运行时参数 | source-component manifest + deterministic frames | 强制源哈希、像素和时序门 |
| testing | 高刷新视频/主观用户测试 | frame diff、状态 trace、负 fixture、后续人工窗口 | 机器先证确定性，人工只看最终体验 |

## 给主 agent 的 R7 确定性规则（按优先级）

以下是建议交给 Sagan 的规则，不是 Luna 自行采用的产品决策；主 agent 必须先在 registry/Goal 流程中记录采纳结果。

1. **单一完整表情**：每个离散 timer tick 只提交一张 200x200 1bpp 完整 frame；禁止把上一情绪、下一情绪或 menu 叠成两张脸。
2. **白名单素材**：每一帧只能由 locked-V9 source components 合成；保持白 eye highlight 与小 sparkle，禁止新画脸、新轮廓和运行时程序化特征。
3. **固定 phase 图**：每个动作必须是 `lead -> attack -> hold -> settle -> recovery` 的有限状态图；每个节点有固定 timer、固定最大次数和固定终态。
4. **先 gaze 后语义峰值**：触摸/事件反馈先放一个有限方向的 gaze lead，再进入完整情绪峰值；不得连续追踪触点或使用浮点/随机目标。
5. **微动作有界**：blink/highlight/sparkle 只能作为白名单通道叠加，最多一次短 one-shot；禁止跨动作残留、重复激活或超过 1 个 transient queue。
6. **优先级与抢占固定**：清理/安全 > touch feedback > semantic emotion > idle；抢占立即取消旧 transient，从当前完整 frame 进入新动作，并在固定 recovery timer 内回合法状态。
7. **无随机 idle**：idle 采用固定索引、固定间隔和固定循环；相同输入、相同初态必须产生完全相同的 frame/state trace。
8. **R6 回归不变量**：R7 只消费 R6 允许的 reviewed outputs，不改 COMP-REQ-405 accepted lower-driver path；离线 gate 必须检查 200x200/1bpp、source pixel parity、highlight、单脸、bounded timers、无随机/无新组件后，才允许主 agent 决定是否进入后续人工边界。

## R6 约束核对

仓库 [COMP-REQ-405/406/407](../companion_product_requirements.md) 记录：COMP-REQ-405 的 R6 物理 review 为 `通过`，并将 clean refresh 作为后续表情编舞回归合同；COMP-REQ-406 要求 locked-V9、200x200 1bpp、约 470 ms cadence 与 exact lower-driver path；COMP-REQ-407 要求本研究只提供 primary-source note、适配矩阵与规则草案，不授权 physical run。当前 R6 offline artifacts 仍显示 `PASS`，并包含 driver SHA、frame/payload hash、mapping negative fixtures 与 pixel parity evidence。该研究没有改动或重写这些 registry/证据。

## 非目标

- 不复制任何来源的 raster asset、proprietary animation data 或代码。
- 不把任何研究规则自动写入 registry，不替主 agent/Sagan 做 R7 采纳决策。
- 不修改产品、艺术、driver、menu、production、硬件、构建或刷写路径。
- 不宣称约 470 ms e-paper 具有 OLED 的连续 30-60 fps 观感；只提出可验证的离散编舞转译。
