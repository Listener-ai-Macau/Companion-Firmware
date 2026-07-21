# Companion 表情参考模型

> **历史参考模型。** 本文保留角色语法和外部参考；不要把它当作当前美术基线。
> 当前 V9/V45 来源、组件 lineage 和可执行规则见
> [companion_art_generation_lineage.md](companion_art_generation_lineage.md)。

## 用途

Companion 的内脸不再按单张贴图或临时代码印象扩展。每个新状态和新动作先套入本模型，
再从唯一锁定的 v9 美术基线生成、渲染和比较。参考的是成熟陪伴产品的交互语法，不复制
它们的造型、资源或品牌识别。

## 外部参考

- [Sony Aibo design](https://www.sony.com/en/SonyInfo/design/gallery/aibo/):
  同一双眼通过眨眼、瞳孔式变化和眼球运动表达好奇与情绪；身份不随事件而换脸。
- [Eilik product reference](https://www.eilikrobot.com/products/eilik/):
  待机动画、触摸、振动和声音分别触发不同反应；产品把敏感触摸和丰富表情作为
  同一个交互系统，而非两个独立演示。
- [Loona official reference](https://loona-official.com/):
  大量表情服务于打招呼、被抚摸、等待、互动和休息等真实上下文，并随长期互动形成
  陪伴感。
- [robot gaze and facial-expression study](https://www.mdpi.com/1424-8220/22/11/4282):
  注视、微小眼动、眨眼和与嘴部的同步是让屏幕脸具有注意力感的有效组合。

本轮可追溯的产品/研究拆解和可执行结论见
[动态表情参考调研](companion_expression_motion_research_20260717.md)。它补充本模型，
但不授权使用任何外部角色美术或产品资源。

## 三层模型

| 层 | 职责 | Companion 约束 |
|---|---|---|
| 身份层 | 固定眼睛语法、眉形、嘴、腮点、挂件和整脸中心锚点 | 只能来自锁定 v9 家族；不得切换旧工程脸、程序脸或另一套眼睛。 |
| 情绪层 | 保存平静、好奇、亲昵、专注、困倦等持续倾向 | 情绪只选择允许的场景族，不直接画像素；相同输入必须得到确定性状态。 |
| 表演层 | 用版本化 component performance score 把一个真实事件编成 entry -> sustain -> settle/exit | 每眼的 source primary reflection 是唯一移动的注视轨道；更小的 source sparkle 固定在 v9 身份锚点。两眼 primary 错峰到位后，眉、嘴和两侧腮点作为一个表情整体回答，挂件只做短的 secondary accent；同一表演里的脸必须是同一个角色，不是三张无关卡片。 |

三层不等于每层各存一张整脸。身份层应当是经生成图和 source-to-PBM 证明的 v9
组件/组合格点，情绪层保存持续变量，表演层按状态和事件编舞。设备从外部 Flash 读取
已登记的组件掩码，并只在合法锚点和位移范围内组合它们；完整 PBM/CEMP 同时作为可重放的
审计与回归对比产物。设备端不得代码绘制五官；完整架构见
[动态表情参考调研](companion_expression_motion_research_20260717.md)。

## Companion 日常表演语法

1. 日常清醒从 idle.entry 开始。sustain 和 settle 每帧在真实面板完成后至少停留
   3 秒；完成后静置 8 秒再开启下一次日常微表演。
2. 每段表演必须围绕一个可解释的微意图，例如看向一侧 -> 注意到 -> 放松回来，不能
   在无输入时跳到录音、菜单、睡眠或错误表情。
3. 表情变化至少要由两个协调特征承担：眼睛、高光或注视，与眉、嘴、腮点或挂件中的
   另一项。只平移整张脸或只切换一个挂件不能算完成的生命感表演。
4. 触摸、菜单、录音、低功耗、错误和高优先级页面取消未完成的日常表演；它们只能选择
   与事件匹配的 v9 场景。
5. score 的固定语义为 `entry / prepare / lead / response / accent / hold / release / return /
   settle`。每步只声明已登记 component id 的合法姿态与停留时间；固件和电脑预览使用
   同一份由 layout 生成的 score，不能各自补出临时动作。
6. 四个 Daily gaze 是同一坐标合同的方向变体：left 为 primary reflection 负 X、right 为正 X、up 为负 Y、
   down 为正 Y。每只开放眼必须把 source-derived 的最大白色岛屿登记为唯一可移动的 primary reflection，
   并将其余小岛构成的独立 sparkle 固定在精确 v9 锚点。双眼 primary 可以错峰到位，眼球主体和 sparkle
   锚点固定；右看持续姿态必须到达 primary reflection 登记的最右合法范围。
7. `nose_default` 没有批准变体或合法位移，始终固定在 v9 中心锚点。`mouth_default` 只可在
   两个 primary reflection 到位后、其已登记的上下一个像素范围内与双眉、两侧腮点一起开始回应，并
   必须精确回到 entry；挂件只能在这组表情之后补足节奏。
8. 电子纸不伪装成 OLED 的高帧率。表演以稀疏、可读的关键帧和既有刷新策略实现；
   不可接受残影优先于节奏。

## 当前 v9 判断

锁定 v9 的 idle.entry -> idle.sustain -> idle.settle 已证明身份和中心锚点一致，但
sustain 只有 (-1, 0) 的整体相位偏移，entry 与 settle 像素相同。因此它可用于验证
调度、资源和锚点，但不能单独满足上节第 3 条的成熟日常表演要求。

当前候选已经把 Daily 从一次组级插值升级为 v2 component performance score；其每一帧都由
source-derived 的唯一可移动 primary reflection、固定身份 sparkle、固定鼻子，以及整体回应的嘴、眉、
腮点和延后挂件在合法 offset 组合而成，且生成给 host preview 和 portable Rig core。后续扩展触摸、
滑动、录音、菜单或睡眠时必须复用这一 score/compositor 合同；需要不同的小闪点形状时，仍先版本化
记录 prompt/参考，再生图并导出组件，代码不得补画或替换美术。
