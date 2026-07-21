# Companion 动态表情参考调研（2026-07-17）

## 目的

本记录把成熟陪伴产品与屏幕脸研究转成 Companion 可执行的动态表情约束。它们是交互语法参考，不复制任何品牌造型、资源或角色；Companion 始终只使用锁定的 v9 内脸来源。

## 参考结论

| 参考 | 可验证观察 | 迁移到 Companion 的规则 |
|---|---|---|
| [Sony aibo 设计说明](https://www.sony.com/en/SonyInfo/design/gallery/aibo/) | 同一套眼睛依靠眨眼、瞳孔收放与眼动表达好奇和情绪；身份不随一次互动换脸。 | v9 的眼形、眉口、腮点和中心锚点固定。日常表演只允许在既有身份中改变注视/高光，并保持双眼匹配。 |
| [Sony aibo 产品说明](https://www.sony.com/en/SonyInfo/News/Press/201711/17-105E/) | 触摸、声音和环境感知进入行为与长期个性，而不是单独播放装饰动画。 | 事件先选择真实状态，再触发该状态的进入/持续/退出；触控、菜单、录音、休眠与错误能够中断日常，不从日常随机跳转。 |
| [Eilik 官方产品页](https://www.eilikrobot.com/products/eilik/) | 待机、触摸、声音与运动共同构成丰富反应；产品强调 idle animation 而非只在点击时有表情。 | 日常清醒可自主低频微表演，但必须可被事件取消；事件反应和日常表演使用同一身份层、不同的状态场景。 |
| [LivingAI EMO 官方页](https://living.ai/emo/) | 用触摸传感器与大量表情/动作建立反应性。 | Companion 不追求其数量或 OLED 帧率；采用少量高辨识度的、状态驱动的关键帧，先验证一条完整表演语法再扩展场景。 |
| [平面屏幕机器人注视研究](https://pmc.ncbi.nlm.nih.gov/articles/PMC9185237/) | 简化大眼脸的注意力可由眼神跳变、眨眼和小嘴部动作增强；论文在其屏幕脸中发现这些变化以跳变而非平滑过渡时，注意力感更好。 | 电子纸不伪装连续逐帧动画。每段采用少量离散关键帧：眼神/高光为主，眉、嘴或小挂件至少一项协同；相邻帧是局部语义变化，禁止整脸位移伪装成动画。 |

## 2026-07-18：从“组件依次到位”改为表演谱

第一版 Daily 虽然已拆出并移动了 source-derived 的眼内高光，但它用每个组件组的一次线性
`entry -> sustain` 插值排队播放，视觉上仍像机械的逐项切换。为避免继续用零散偏移补丁修正，
本轮补充了两项成熟系统的可迁移原则：

| 参考 | 可验证观察 | Companion 的根层规则 |
|---|---|---|
| [FurhatOS 技术概览](https://furhatrobotics.com/docs/Furhat-Robotics-Technical-Product-Overview.pdf) | 动画系统把眉、眼、鼻区与 gaze target 作为可独立控制的参数，而不是把整张脸当成状态贴图。 | v9 保持眼球主体锚点；每只眼的 source-derived 高光是独立轨道。Daily score 用其合法 offset 表达 gaze，眉/嘴/腮点/挂件各自保留独立轨道。 |
| [Disney Animation 角色动画流程](https://disneyanimation.com/process/animation/) | 明确使用 anticipation、secondary action、follow-through 与 timing 来塑造角色表演。 | score 的固定词汇为 `entry / prepare / lead / response / accent / hold / release / return / settle`；高光先有准备和主动作，另一眼错峰跟随，后续组件重叠响应，收束时保留短余韵再回到 calm baseline。 |

这不是把 OLED 的连续动画照搬到电子纸。score 的每一步仍是一个已登记组件在合法坐标的离散
姿态，带确定性停留时间；它只改变时间结构与组件错峰，绝不新画五官或序列化完整人脸。四个
Daily 方向必须共享同一坐标语义：左为高光负 X、右为正 X、上为负 Y、下为正 Y。播放器每个
故事结束后自动轮换方向，并保留直接选取控件，避免仅循环 `daily_left` 造成“只会向左看”的
假象。

### 2026-07-18：反光岛屿必须拆分，但不能成为两个移动高光

`daily_up` 的可视复查显示：把每只眼的全部 enclosed-white 像素作为一个整体移动时，最大白色
岛屿仍然让人读成固定在左上角的反光。依据独立 gaze 参数与 secondary action 的原则，当前 v9
Rig 将每只开放眼的最大 source-derived 白色岛屿登记为 `primary reflection`，将余下小岛联合登记为
独立 `sparkle`，以便验证两组像素的来源、mask hash 和 in-eye containment。但 owner 可视复查证明若
两组都移动，人眼会读成两个竞争高光，且 gaze 仍像固定在左上角。因此 Daily 只让 `primary reflection`
移动；较小 `sparkle` 固定在 v9 身份锚点，不是第二条 gaze 轨道。双眼主反光仍可错峰，`daily_right`
必须触及登记的最右合法范围。播放器同时给全脸和放大双眼组件审计，逐帧证明“主反光移动、闪点静止”。
该修复仍只重组 v9 已确认源像素，不补画白点、不替换整脸、也不增加未经版本化生图确认的美术。

### 2026-07-18：嘴鼻中脸的延后回应

屏幕脸研究支持把 gaze pickup 之后的小嘴部变化作为注意力提示，而 Furhat 的独立控制模型也说明
眼、眉、鼻区不应被当作整脸卡片一同替换。对 v9 的可执行结论不是给鼻子发明动作：锁定的
`nose_default` 没有批准变体和合法位移，必须 fail-closed 固定在中心。相反，`mouth_default` 在主反光
已经启动后才以其登记的一像素上下范围作离散回应，眉、腮点和挂件随后重叠，最后全部精确回到 entry。
这同时保留电子纸可读的 timing/staging，也让中脸参与表演而不引入任何未确认的线条或完整脸替换。

### 2026-07-18：固定光源，移动唯一 focus spark

对最新 Daily 预览的可视复查说明，问题不只是“两个白岛是否都移动”，而是锁定 v9 的大上方
白岛天然读作一个稳定的环境反光；强行让它承担四向 gaze 会把眼神拉回上左。保留它在精确的
v9 锚点，反而给视线一个不漂移的光源。较小的 source-derived 菱形岛可在黑色眼体内承担唯一的
`focus spark`：左/右只变 X，上/下只变 Y，且两只眼先后落位。这个结论是对前述“主反光移动、
闪点静止”候选的替代，不改变 source split、mask hash、容器边界或禁止代码绘制的约束。

这也更符合角色动画里 "timing, clear staging, anticipation, follow-through, and secondary action" 的
实践：先建立清楚的焦点，再把眉、嘴和两侧腮点作为一个读得出的表情姿态落下，最后才让挂件做
次级余韵，而不是把五个组件依次开关。[Disney Animation](https://disneyanimation.com/process/animation/)
将这些原则列为角色生命感的基础。动态表情研究同样指出，真实表情的特征运动不是线性形变，
时间组织本身会影响情绪识别；因此 score 必须保留不对称的 focus pickup，但避免把 facial core
拆成机械队列。[Vision Research](https://www.sciencedirect.com/science/article/pii/S004269891730250X)

Daily 的可执行顺序现在是：`entry` 平静锚点；一侧 focus spark `prepare/lead`，另一侧到达同一
方向；`response` 让双眉、嘴和两侧腮点同步进入同一个姿态；`accent` 让 charm 短暂跟随；`hold`
是同一确定性 Rig sustain；`release` 收回 charm 和 facial core；`return/settle` 让 focus spark
沿相同坐标轴回到精确 entry。自动验证要求大反光、眼体和鼻子全程固定，两个 focus spark 都有
不同起始帧且都先于 facial core 到位，reaction core 同一帧开始，charm 后到，右看到达登记最右边界。

### 2026-07-18：owner 复核修正，小 sparkle 回到身份锚点

上述“固定大反光、移动小 focus spark”候选已经经过真实播放器复核，owner 选择 `失败` 并备注：
“那个第二个高光的位置就不要调了吧，感觉怪怪的。” 因此它不是可继续的 Daily 基线。小菱形
sparkle 重新固定在精确 `(0,0)` v9 身份锚点，不再承担 gaze 或 focus 语义。仍然只允许一条眼内白色
移动轨道：最大的 source-derived `primary reflection`。这恢复的是正确的组件职责，而不是整脸贴图或
旧的逐项队列。

pose-to-pose 的时间结构保持不变：一只 primary `prepare/lead`，另一只 primary 到达同一方向；两个
primary 都到位后，双眉、嘴和双腮在同一帧启动完整 facial core，charm 再做 secondary action；release
把 core 作为一组收回，primary 沿注册路径回到 entry。验证器必须证明 sparkle、眼体和鼻子全程固定，
且绝不把这次被拒绝的小 sparkle 移动重引入未来 Daily score。任何之后对小 sparkle 形状或位置的尝试
都必须进入版本化 v9 参考图/prompt -> 生图 -> 组件导出的独立美术扩展流程。

## 采用的动态基线

`entry -> sustain -> settle` 是一段表演的生命周期，**不是产品只保留三张完整表情卡**。
成熟实现由身份不变的特征组件、持续状态和事件编舞共同决定每一段的实际输出。每个日常
微表演是同一 v9 角色的一次可解释注意力脉冲：

1. `entry`：平静、正视，作为锚点和回稳参考。
2. `sustain`：像“注意到你”的短暂回应；眼神方向/高光为主变量，双眉同步轻微调整，再由嘴、腮点或一个小挂件跟随。
3. `settle`：回到与 `entry` 同一平静身份；它不是另一张情绪卡。渲染差异必须比 `entry -> sustain` 显著更小。

时间与优先级：面板每帧真正完成后才计时，帧驻留至少 3 秒；`settle` 完成后静置 8 秒。触控、菜单、录音、低功耗、错误和更高优先级页面立即取消自动表演。当前电子纸只使用既有刷新策略，禁止为此路径发送 custom LUT 或追求 OLED 式高帧率。

## 目标架构：美术 Rig + 状态编舞器

### 1. 身份 Rig（美术资产层）

由生成图直接导出的、版本化的 v9 组件与组合格点，而不是代码绘制：

- 锁定的双眼轮廓；每眼的 primary reflection 仅在经审核的 `center / look-left / look-right / look-up / look-down` 位置移动，较小 source sparkle 固定在精确 v9 身份锚点；双眼始终保持相称与同一角色感。
- 成对眉形、嘴形、腮点和小挂件的少量已审核变体；每个组件都有 semantic anchor、边界、源图 SHA-256 和 prompt revision。
- host renderer 根据 manifest 审计所有合法组合为完整 200x200 PBM/CEMP 帧；设备只从外部 Flash 读取已登记组件掩码并按合法锚点组合。设备不重绘五官、不发明线条，也不依赖旧工程脸。

### 2. 状态编舞器（产品行为层）

持续状态不是“当前图片”，而是确定性的：`emotion`（平静/好奇/亲昵/专注/困倦）、
`attention_target`（中心/触点方向/菜单/录音/充电）、`energy`、`interaction_memory` 和
`presentation_phase`。事件更新状态，编舞器在合法资产格点中选择下一关键帧：

- 空闲：偶尔从中心注视切到一个很小的注意方向，再用配套眉口回应，最后回到中心。
- 触控：先看向触点，再给与触点、情绪相符的回应；长按、双击、滑动是不同的表演程序，不是随机卡片。
- 菜单、录音、充电、休眠、错误：每个真实产品状态有专属进入、持续和退出表演，且能抢占空闲。
- 同一输入、初始状态和确定性种子得到同一轨迹，便于机器回放；不同触点/持续情绪/最近互动会选择不同的合法轨迹，因而不是循环播放固定三图。

### 3. 电子纸适配层

电子纸只显示经过选择的关键帧，不模拟 OLED 逐帧插值。每次可见变更仍要先等待前一帧完成，
并遵守残影策略；在一次 `entry -> sustain -> settle` 内，表演值可以不同，但都必须来自同一
v9 Rig。当前三帧 CEMP 候选只用于验证导入、锚点、回稳和调度链路，不能被称为最终动态系统。

## 美术与实现边界

- 每帧必须直接来自版本化生成图，保存 prompt、源图 SHA-256、裁剪布局和 source-to-PBM/CEMP 对比；代码不得补画脸、替换眼型或以旧工程脸兜底。
- v9 锁定身份禁止眼睑弧、眨单眼、大小眼、侧眼、媚态/得意/疲惫/威胁式眼神、猫轮廓、耳朵、胡须、灰阶、渐变和整脸平移。
- `entry`、`sustain`、`settle` 共享同一 semantic anchor；输出必须保持 200x200 安全区域。`settle` 与 `entry` 的全画面像素差不得超过 `entry -> sustain` 的 25%，以防回稳阶段偷换状态。
- 任何新场景先在本动态基线中声明触发、情绪、变化变量和退出条件；机器先验证帧顺序、局部特征差异、回稳、边界、资源身份、队列/取消和 CEMP 解码，之后才进入人工审美和真实电子纸评审。

## 不采用的方向

- 不复制 aibo、Eilik、EMO 或论文中的角色外观、品牌资源、动作数量或连续帧率。
- 不把随机表情轮播、全脸平移、黑球、旧工程脸或单挂件变化称为“生命感”。
- 不因电子纸限制退回到静态贴图；限制由低频且有语义的关键帧解决。
