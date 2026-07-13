# Companion 屏幕子系统项目计划

## 目标

先在 NUCLEO-WB55RG、GDEY0154D67-T03 200x200 电子纸和 FT6336U
触摸屏上完成屏幕子系统，再通过目标后端移植到 STM32WBA55/WBA65。

菜单和表情共用同一套单色 framebuffer、scene/player、显示队列和目标
驱动。表情采用情绪矩阵中的白底黑色设计，同时保留连续动画、片段循环和
自然交接，不退化成只显示静态关键帧。

## 架构边界

```text
触摸 / 录音 / BLE / 设备状态
              |
              v
      UI 与表情状态机（可移植）
              |
              v
 scene/player + 资源目录 + 时间轴（可移植）
              |
              v
  目标 profile 的 1-bit framebuffer（可移植）
              |
              v
 显示队列、合并、节流、状态快照（可移植）
              |
              v
 WB55 或 WBA panel/touch/storage/time 后端
```

## ESP 表情系统迁移原则

保留 `esp_emote_gen_player` 的核心设计：

- 主机端制作、打包和设备端播放分离；
- 资源包内使用名称和索引定位动画；
- 每个动画支持 `intro -> loop -> tail` 片段计划；
- 支持立即切换，以及当前片段播放到 tail 后自然交接；
- player 只提交像素区域，由目标 display flush 回调完成硬件刷新；
- 菜单 scene 和表情 scene 使用同一个播放器生命周期。

STM32 版本不直接依赖 ESP-IDF、ESP FreeRTOS、`esp_mmap_assets` 或
`esp_emote_gfx`。主机导出器按目标 screen profile 把源动画转换成白底黑色、
1-bit 帧和紧凑二进制索引；STM32 player 通过通用 asset store 读取并按
时间轴播放。正常资源默认位于外部 Flash，内部 Flash 只保留最小救援 UI。

资源存储、可换屏幕和内外 Flash 预算的产品契约见
`docs/companion_resource_memory_policy.md`。播放器和场景不能写死 200x200；
当前尺寸只由 WB55 面板 profile 和对应资源包声明。换屏幕时新增资源 profile，
换表情时新增 pack revision，两者都不改 `intro / loop / tail` 状态机。

## 电子纸动画策略

GDEY0154D67-T03 手册明确支持 full、fast 和 partial refresh。STM32
player 保留每帧时长和完整动画过程，panel scheduler 根据实测刷新能力
决定何时提交下一帧：

- 冷启动且面板 RAM 基线未知时使用标准全刷；
- 连续动画使用局部刷新，只更新变化区域；
- 面板 BUSY 时不重入，过期动画帧可合并到最新帧；
- 连续局刷 5 次后只标记维护到期，不打断当前交互；
- 最迟在 60 次交互差分刷新安全上限执行 `0xCF` 维护刷新并同步旧图 RAM；
- intro、loop 和 tail 都保留，实际帧率以局刷实测结果为准并记录；
- 标准 `0xF7` 多闪全刷只用于未知基线或故障恢复，不作为日常维护；
- 低温、BUSY 超时或残影异常时进入受控恢复，而不是破坏 player 状态机。

产品观感原则按 Good Display/EPD 成熟做法落地：局刷和快刷用于交互响应，
但它们会累积残影；全屏清残只作为低频维护或恢复动作。Companion 不追求把
电子纸伪装成 OLED，而是把可见变化压进局部、把手指接触期的请求合并到最新帧、
把旧图层同步和清残延后到交互结束后一次完成。以后若更换面板或取得供应商
专用快刷波形，只替换 panel target 的 refresh profile，不改 scene/player
和资源包契约。
WBA55/WBA65 移植沿用同一条边界：portable queue 继续携带 `refresh_mode`
和 16-bit dirty rect；`COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE`、`COMP_EPAPER_REFRESH_MAINTENANCE`
和 `COMP_EPAPER_REFRESH_FULL` 只在 `panel_target_stm32wba.*` 内映射到具体控制器波形，
不得在 WBA 移植时重写 scene/player 或菜单触摸策略。

2026-07-12 外部调研固化为 SCR-16 输入：Pervasive Displays 的 fast/partial
refresh 资料把全局刷新、快刷和窗口局刷分成不同质量/速度层级，并指出 partial
window 更容易出现可见残影；Good Display 使用指南也要求局刷后周期性全局清残。
所以产品项目不把“每次都全清”当作高级感，反而把它视为退回：接触期只允许
差分/快刷，放手后一次安静维护，真实残影若仍不可接受则先调 panel profile、
波形和清残节奏，不能用旧表情图层或反复多闪全刷来掩盖。

2026-07-13 外部调研补充为 SCR-17 输入：电子纸 partial/fast refresh 的残影
来自新旧像素电荷没有完全重新平衡；成熟方案不是让新旧资源同时存在，而是把
“旧图残留”和“资源代际切换”分开管理。Companion 的产品规则是：CEMP 资源包
按 revision 原子激活，激活后先 drain/丢弃旧 revision 的待刷帧，再建立一次
明确的 framebuffer/panel RAM 基线；触摸交互期只显示当前 revision 的最新帧，
不得把旧 procedural 脸、旧菜单 PBM、旧 sheet 裁切或旧 framebuffer 作为过渡
混进新美术。若屏上仍看到旧影，只能通过一次交互后的维护刷新、全刷恢复或
panel profile 调整处理，不能用“新图盖旧图”的方式让新旧风格交织。
同一调研还把缓存失效和双缓冲原则纳入项目规则：active CEMP revision 是正常
屏幕美术的 source of truth，所有显示请求都必须携带并匹配这个 generation；
renderer 只能提交完整的当前 generation 帧，不能把半成品、旧队列、旧 fallback
或旧菜单帧作为视觉桥接。未来为了节省 SRAM 可以不强制双全屏缓存，但必须保留
“前台稳定、后台合成、一次提交”的语义。
调研记录和来源固化在 `docs/validation/companion-screen-generation-swap-research.md`，
并由 `verify_screen_refresh_feel_contract.py` 防回退。

SCR-17 不是一次性修屏 bug，而是产品项目里的长期换代卫生项：以后每次换生图
prompt、换菜单视觉、换屏幕 profile、换外部 `ui_assets` 包或通过 OTA 激活新
资源，都必须先证明“当前只有一个 active generation”。成熟做法的共同点是
先让资源版本、缓存/队列和显示提交保持一致，再处理电子纸物理残影；不能把
残影、旧队列和旧 procedural 兜底混在一起解释。项目验收因此固定为：
资源 revision 原子激活、旧 generation 待刷请求 drain/丢弃、renderer 后台完成
当前 generation 的完整帧后一次提交、交互期间只刷最新 coherent frame、放手后
用维护刷新或故障全刷恢复面板基线。任何新旧风格同时可见都先按产品 P0 体验问题
处理，不能把它归类为“墨水屏就是这样”。
成熟产品处理方式已经固化为 SCR-17 playbook：新一代资源在后台合成，激活时
只切到一个 active revision；旧队列宁可丢帧也不能回放；可识别旧资产和旧布局
属于 generation hygiene 缺陷，真实淡影才归 refresh/profile 调参。这个项目项
以后跟着表情、美术、菜单、屏幕尺寸和外部 Flash/OTA 资源一起验收。
2026-07-13 用户再次反馈“总是有新旧交织的问题”，所以 SCR-17 升级为持续产品
项目项：每个候选 release 都必须重新证明换图、换菜单、换屏幕 profile、外部
Flash 资源激活和未来 OTA 激活不会显示上一代产品美术。它不能因为单次固件看起来
改善就关闭；只有当候选包能提供导入 contact sheet、CEMP revision、队列丢弃计数、
首帧 coherent frame、panel baseline/maintenance 日志和真屏观感记录后，才允许
进入人眼验收。WBA55/WBA65 也继承同一条规则：即使 SRAM 不够双全屏缓存，也必须
保留“前台稳定、后台合成、原子提交”的语义，不能用旧资源做过渡。
2026-07-13 重新查阅成熟电子纸产品资料后，SCR-17 再补一条产品判断：成熟产品
会把刷新体验做成模式和节奏管理，例如交互快刷、内容相关刷新、必要时手动或自动
全清、固件波形优化；但它们不会把“上一代 UI 或上一代表情还能被认出来”当作正常
残影。Companion 因此在项目里固定四类诊断结果：physical afterimage、stale queued
frame、stale asset revision、rescue/procedural fallback leakage。只有第一类走
panel profile、维护刷或全刷恢复；后三类都是资源/队列/渲染的 P0 产品问题。
2026-07-13 再按当前资料复核后，SCR-17 被列为每个候选版本都要填写的
release ledger：生图/菜单/source art 路径、CEMP revision、CRC、兼容屏幕 profile、
manifest/外部 Flash 激活结果、旧队列丢弃计数、首帧 `coherent_generation=1`、
刷新模式决策和视觉分类都要留下记录。成熟产品的共识是内容更新靠版本化资源和缓存
失效保证一致，电子纸残影靠刷新 profile 管；所以以后任何“新旧交织”都先进入
SCR-17，而不是散落成一次次临时调参。未来 `ui_assets` OTA 也纳入同一规则：
资源 manifest、payload、CRC/签名、active revision、显示队列和首帧提交必须作为
一个产品事务验收，失败时保留上一代资源，不能显示半新半旧。

2026-07-13 用户再次强调“总是有新旧交织”的问题后，SCR-17 固定为产品
backlog/release item，而不是某个脚本里的备注。成熟方案复核后的结论是：
电子纸 physical afterimage 由 waveform、partial/fast/full 刷新节奏和维护清屏
解决；软件上能认出旧脸、旧菜单、旧 prompt 裁切、旧 fallback renderer 或旧
framebuffer 内容，则属于 `stale_generation_content`，不能归因成墨水屏限制。
因此每个候选版本必须在产品项目里保留 SCR-17：source art、CEMP revision/CRC、
active generation、旧队列丢弃计数、首帧 coherent frame、刷新分类和旧影分类
都要在 release ledger 中可追溯。WBA55/WBA65 SRAM 若不足双全屏缓存，可以用 tile
compose 或单 framebuffer 加 generation tag，但必须保留“前台稳定、后台合成、
原子提交”的语义。

## 美术换图与新旧交接规则

表情和菜单的正常产品美术必须先有生图、视觉稿或等价 art board 作为基线，
然后再导入固件资源；禁止在固件里凭感觉再画一套不同风格。当前基线为
`docs/art/generated_pet_expression_sheet_v5.png` 和对应 menu mock。

换图流程固定为：

1. 保存新的生图/视觉稿到 `docs/art/`，记录 style name。
2. 更新导入器或 style constants，使 PBM/CEMP 尽量还原视觉稿。
3. 运行 `python .\tools\render_generated_expression_normal_pack_contact_sheet.py --write`
   并打开 REF/PBM review 和正常资源 contact sheet，自查裁切、标签泄漏、
   五官比例、装饰符号和白底黑字边界。
4. 重新生成 CEMP revision，并更新 pack bytes/CRC。
5. 跑资源、菜单、premium pet art、style contract 和 runtime recheck runner
   验证；未接硬件时只进入 runtime pending。

正常 CEMP 表情资源不得再混入旧工程味 procedural PBM。`card_renderer.py`
和 `pet_visual_style.h` 只保留救援、维护、预览和小型兜底动态；产品包里
被 manifest 引用的 `expression_*.pbm` 必须全部来自生图导入输出或它的明确
alias。这样以后频繁换 prompt、换屏幕尺寸或换外壳时，改的是 art source 和
导入映射，不是重新手写一套脸。

## 项目项

| ID | 项目 | 当前状态 | 验收条件 |
|---|---|---|---|
| SCR-01 | SSD1681 全刷与 BUSY 时序 | 已实机通过 | 5000 字节帧完成刷新，BUSY 高到低，日志记录刷新耗时 |
| SCR-02 | 屏幕安装方向与触摸坐标 | 人眼方向与非镜像显示已通过；触摸坐标待菜单点击确认 | 人眼文字非镜像且方向为正；触摸日志同时记录 raw 和 200x200 逻辑坐标 |
| SCR-03 | 单色 framebuffer、图元与字体 | 代码与编译通过 | HAL-free，自测通过，WB55/WBA 共用 |
| SCR-04 | scene/player 与资源包 | idle、listening、speaking、thinking、recording 与 happy 的 intro/loop/tail 已实机播放；产品事件交接已通过 | 名称寻址、逐帧时长、intro/loop/tail、now/tail-handoff、profile 选择和 CRC 均可测试 |
| SCR-05 | SSD1681 局刷与动画调度 | revision 20 已改为控制器保留旧图层的差分窗口、触摸空闲维护与菜单请求合并；残影与低闪维护待实机复测 | 差分窗口、BUSY、同类请求合并、5 次软清理点、触摸空闲维护、残影恢复有实机证据；日常动画播完一轮即保持 |
| SCR-06 | FT6336 触控事件层 | PC6 EXTI 中断、PC10 硬复位、活动期 5 ms/空闲 8 ms 轮询、刷新 BUSY 期 5 ms 时间戳缓冲和 I2C 自动恢复已编译；日常双击在 650 ms/40 px 窗口内启动录音，再次双击停止同一触控来源录音；每个变化的 down/move/up 样本记录 `sample_age_ms`，非菜单滑动映射为日常宠物方向互动，菜单真人体验仍待验收 | 单次点击只产生一个动作；双击只控制触控来源录音且不抢占其他来源；右划、上划、下划有起终点、时长和分类日志并在日常页进入宠物回应；刷新期间点击不丢失；轴锁定、去抖、硬复位与 I2C 总线恢复且不重复触发 |
| SCR-07 | 日常页、主菜单与页面导航 | CEMP revision 53 的 v3 六项同屏菜单已完成 provision/normal runtime 机器证据，但 owner 在 `menu_boundary_single_clean_refresh` focused review 中以“菜单太小了, 换成四项一页吧”失败该候选。`menu-v4-2026-07-13` 必须先按新生图基线设计四项一页、两页六项入口和明确页面导航，再替换中文/英文外部资源；日常 3 s 长按进入、四方向宠物滑动、Voice/Status/Phone 等真实功能保持。 | 日常轻点和所有左/右/上/下滑动触发表情反馈；双击是默认录音入口；任意位置近似静止长按 3 s 进入菜单，普通滑动不进菜单；每张 200x200 菜单主页至多四个大而易触的真实入口，两页合计覆盖 Voice & Record、Status、Phone Link、Device、Preferences、About；新的生图必须定义可读页码/页面导航和按下 cue；功能页、语言切换、返回和刷新队列行为不回退。 |
| SCR-08 | 页面功能接入 | 录音状态由日常双击触控的真实录音状态机归一；Voice 页只显示真实麦克风状态和外部 Flash 记录历史，不能出现重复 Start/Stop 控件；BLE 连/断仅在状态页可见时局刷，录音变更仅在 Voice 或状态页可见时局刷，待实机操作 | 双击可启停现有录音链路并在外部 Flash 完结记录；Voice 和状态页只显示真实触摸/屏幕/BLE/录音状态 |
| SCR-09 | 白底黑色表情资源 | revision 52 保持主表情路径为外部 CEMP PBM 帧，并把产品关键帧改为从 `docs/art/generated_pet_expression_sheet_v5.png` 导入；表情按 genref v5 12 格 spec 保持贴纸式内脸构图：更大的高光眼、加粗眉眼嘴鼻、脸颊、气泡、波纹、爱心、闪光和录音点随状态变化；`generated-expression-sheet-review.png` 必须先由 AI 自己对照生图预览，导入机器审查不再用内部白色遮罩或未冻结屏幕尺寸的保护带，PBM threshold 调到 168 以减少硬块感，`premium pet art contract` / `verify_premium_pet_art_contract.py` 防止退回只动眼睛；procedural 保留为救援、维护和少量补帧路径；肉眼高级感仍待逐个验收 | 按效价/唤醒度矩阵分类；动画过程逐帧可见；逐个实机确认；正常产品美术不得回退到内部静态位图或仅程序化脸 |
| SCR-10 | WB55 屏幕闭环 | 待验收 | 串口日志、屏幕照片和触摸操作三类证据一致 |
| SCR-11 | WBA55/WBA65 移植后端 | 预移植边界完成，真实 CubeWBA 工程与硬件证据待移植阶段 | panel 刷新、FT6336 I2C、显示调度和 GATT 均为 WBA55/WBA65 回调脚手架；只替换 panel/touch/storage/time/CubeWBA 后端，可移植模块无需改动 |
| SCR-12 | 可换屏/可换表情资源架构 | CEMP 生成、挂载、外部帧读取已实机通过 | 分辨率、stride、像素格式、资源 revision 和 16 位 dirty rect 来自 pack profile，不写死在 player |
| SCR-13 | 外部 Flash 优先与资源预算 | WB55 实机通过，50 KB 内部静态帧已移除 | 正常 UI 资源位于 `ui_assets`；内部只留 <=16 KiB 救援 UI；普通固件不携带 provision blob |
| SCR-14 | Denzic-Platform 与资源 OTA | Companion WB55 Loader、Type、打包与静态检查已接入 `denzic_ota_v1`；当前跨产品矩阵为 `NO_GO_COMMIT_DRIFT`：Companion 固件/Type 固定在 Denzic `1e727f2`，Listener 固件/Type 固定在 `6ce017f`，协议 JSON SHA 一致但共享平台提交未统一；按 OTA 前置冻结，等待 Listener OTA 验收或明确共享提交对齐后再推进真实 BLE 传输和资源 installer | `denzic_ota_v1` 只负责通用传输；`mcu_app` 与 `ui_assets` 可独立更新；候选资源经签名、SHA-256、版本和兼容性验证后原子激活；错误目标在擦写前拒绝；失败保留旧资源；录音与设置不被擦除；WB55/WBA/ESP 安装器互不复制；跨产品发布前 `verify_denzic_ota_product_matrix.py` 必须从 `NO_GO_COMMIT_DRIFT` 回到 PASS |
| SCR-15 | 美术换图流水线与旧风格清理 | revision 51 已把正常 CEMP 使用的 39 个 `expression_*.pbm` 全部收敛到生图导入输出/alias；`render_generated_expression_normal_pack_contact_sheet.py` 固化正常包 contact sheet；旧 procedural 正常帧不再进入产品包；硬件 runtime pending | 每次换图都从 `docs/art/` 生图基线开始；REF/PBM review 和正常包 contact sheet 先由 AI 自查；manifest 中所有正常表情 PBM 必须被 `companion-screen-generated-expression-sheet-import.json` 覆盖且 contact report 保持 39/39；旧工程味资源只能作为救援/维护/预览，不得与新美术混用 |
| SCR-16 | 屏幕观感与残影控制 | Good Display/EPD 资料已纳入产品规则；`verify_screen_refresh_feel_contract.py` 已固化机器检查；当前策略为交互 `0xFC`、交互后一次 `0xCF`、基线有效时明确 daily/menu 边界各一次 `0xCF`，仅未知基线/故障使用 `0xF7`；边界前取消待执行维护，避免一次导航出现两轮清理；rev53 真屏观感待复验 | 手指接触期间不得插入多闪全刷；菜单当前按下行只保留最新帧；同帧不刷新；局刷计数和清残到期可诊断；普通交互清残必须是交互结束后的单次低闪维护；进入和退出菜单各请求一次单闪快刷，只有未知基线/故障允许全刷；若残影仍不可接受，下一步优先调整波形/profile/清残节奏而不是混入旧图 |
| SCR-17 | 新旧画面交织防回退 | 外部调研已把“残影”和“资源代际混播”拆成两个问题，并补入缓存失效/完整帧提交原则；用户已把反复新旧交织列为产品观感问题，所以它是每个候选 release 都要复验的长期产品 backlog/release item：每次换 prompt、美术、菜单、屏幕 profile、外部 `ui_assets` 或 OTA 资源激活都要先过 generation hygiene；规则已并入 `verify_screen_refresh_feel_contract.py`；每个候选版本必须填写 release ledger，记录 source art、CEMP revision、CRC、兼容 profile、manifest/外部 Flash 激活、active generation、旧队列丢弃计数、首帧 coherent marker、刷新模式和视觉分类；rev51 真屏仍待复验 | 新 CEMP revision 原子激活；旧 revision 待刷帧在切换时 drain 或丢弃；所有显示请求携带 active generation；renderer 只提交完整当前 generation 帧；正常产品路径只显示当前 revision；旧 procedural/旧菜单/旧 sheet 只能用于救援或维护，不得作为过渡混播；首帧必须是 coherent current-generation frame；看到旧影时先分类为 physical afterimage、stale queued frame、stale asset revision、rescue/procedural fallback leakage 或 `stale_generation_content`，只有 physical afterimage 走维护刷新/全刷恢复/profile 调整，其余按产品 P0 修；未来 `ui_assets` OTA 也必须把资源 manifest、payload、CRC/签名、active revision、显示队列和首帧提交作为一个产品事务验收；WBA55/WBA65 即使用 tile compose 或单 framebuffer，也必须保留前台稳定、后台合成、原子提交语义 |
| SCR-18 | 本地唤醒词与语音唤醒交接 | 用户已为低功耗目标明确 deferred；当前 `wake_word_control/status` 仍只是 arm/disarm/simulate 状态面，真实 KWS 未实现、更未做真机声学/功耗验收，不能进入默认产品流程 | 唤醒词恢复排在 SCR-21 的待机功耗验收之后：固定 `PCM16` 单声道 `16 kHz` 的 HAL-free 音频契约；PDM/DMA -> VAD -> 可替换 KWS -> 去抖/冷却 -> RAM pre-roll -> recording/ASR；短语模型与前端参数位于外部 `model_assets`，推理代码留内部 Flash；privacy/mute/disarm 必须停采样并清 RAM 音频；WB55 与 WBA 用不同 target audio adapter 复验；对真实/非短语、多人、口音、距离、噪声和背景人声记录 FAR、FRR、延迟、CPU、SRAM 与电流；模型原子激活/回退遵循 `model_assets` 契约，但 Listener OTA 验收前不推进 OTA 实作或刷写。详见 `docs/companion_wakeword_requirements.md` |
| SCR-19 | 无板载 ST-LINK 的产品 USB 开发与恢复 | 需求已建立，尚未选定 WBA55/WBA65 产品板与完成原理图/真机验收；当前 NUCLEO 屏幕路径仍为 ST-LINK VCP + SWD | WBA55 使用 USB-UART VCP、ROM USART downloader 和 SWD/NRST/BOOT rescue pads，禁止误配原生 USB DFU；WBA65 使用原生 USB CDC、ROM USB DFU、HSE32/VDDUSB 条件和同样的 SWD pads；Host 的日志/诊断协议跨 `stlink_vcp`、`usb_uart_vcp`、`native_usb_cdc` 保持一致；USB recovery、factory flash、Denzic OTA 权限分层。详见 `docs/companion_usb_development_requirements.md` |
| SCR-20 | 参考图驱动的完整菜单与功能闭环 | `menu-v2` 已由用户拒绝；`menu-v3` 已生成总设置页和六个详情页候选，等待用户确认后才转换为 PBM/CEMP。页面功能清单见 `docs/companion_menu_information_architecture.md`；每轮提示词、源图、哈希和评审结论见 `docs/art/iterations/companion-menu-v2/iteration-ledger.json` | 只按已接受生图复刻外置菜单资源；总设置页、语音、状态、手机、设备、偏好、关于均有明确功能 owner；双击录音、语音状态/历史、状态数据、BLE retry、语言、资源 revision 与诊断均以实际代码/日志证明；任何未实现项明确标记 planned 并保留在 backlog，禁止伪造可用控件 |
| SCR-21 | 触控优先的低功耗待机 | 静态策略已编译：CubeWB LPM 启用，`P10 A0/TP_INT -> PC6/EXTI` 已由操作者接入并作为候选唤醒源；`P10 A3/TP_RST` 保持可选未接。真实 IRQ、Stop 恢复和电流尚待验收；录音、触摸接触、菜单计时、屏幕维护/BUSY 期间始终禁止 Stop | 最终产品板在屏幕静态、PDM/KWS 关闭、触控中断就绪、无录音/无刷新/无手指接触的定义待机场景，连续 60 s 原始电流平均值不大于 `1 mA`；必须同时证明触控唤醒、双击录音和 BLE 产品状态无回归，NUCLEO/ST-LINK 电流不得作为产品结论。详见 `docs/companion_low_power_requirements.md` |
| SCR-22 | 生图基线的低功耗、唤醒与录音交互表情 | 已登记，尚未生成或替换当前资源，必须先完成 SCR-21 的真实触控中断/Stop 证据；美术迭代 ledger 为 `docs/art/iterations/companion-pet-interaction-v1/iteration-ledger.json` | 只在用户接受的生图基线后生成外部 `ui_assets` CEMP；覆盖低功耗静止、触控唤醒、轻触/方向滑动、双击录音开始、录音中、保存成功和失败。每个状态须是整张内脸联动，不画猫头轮廓；低功耗状态无定时动画，触控唤醒和录音状态转换各只安排必要的局刷，不能破坏 Stop 或引入频繁闪烁。 |

## 当前菜单待办

| ID | 待办 | 前置条件 | 验收 |
|---|---|---|---|
| MENU-01 | 接受或重做 `menu-v3` 视觉基线 | 用户评审候选图 | 迭代 ledger 记录 accepted/rejected 与下一轮 prompt delta |
| MENU-02 | 从接受稿生成中英文 PBM/CEMP | MENU-01 accepted | 资源 visual review 与 menu verifier 通过，CEMP revision 递增 |
| MENU-03 | 电话页重连动作接入 BLE 广播请求 | MENU-02 | 代码已接入：点击重连调用受保护的广播请求，`ADV`/`LINK`/`ERR` 来自实际请求结果；待 BLE 硬件日志确认 |
| MENU-04 | Voice 页状态与最近条目/计数接入外部 Flash 索引 | 已有录音存储 | 只显示真实条目数和真实当前录音状态，不显示示例数字或重复 Start/Stop 控件 |
| MENU-05 | 设备电池行 | 有电池硬件与采样路径 | 无硬件前显示 planned；接入后显示校验过的电量/充电状态 |
| MENU-06 | 关于页诊断入口 | 诊断操作缩短为有界、可取消产品流程 | 操作不阻塞交互，日志含 start/result，失败可读 |

SCR-17 的项目级处理方式按 2026-07-13 复查的成熟方案固定：电子纸物理残影
归 refresh profile、波形、局刷次数、维护刷和必要全刷处理；任何能认出上一代
脸、菜单、prompt 裁切、fallback renderer 或旧 framebuffer 的现象，都先按
`stale_generation_content` 处理，不能说成“墨水屏就这样”。每个候选 release
必须保留这个项目项和 ledger，即使当前一次刷机观感变好了也不关闭；以后换图、
换菜单、换屏幕 profile、外部 Flash 包或 OTA 激活时都要重新证明 active
generation 唯一、旧队列已丢弃、首帧 coherent、维护刷只处理真实残影。

## OTA 前置冻结

在 Listener 的 OTA 完成明确验收前，Companion 不推进任何 OTA 实作、打包、
传输、刷写或人工验收。现有 OTA 契约和静态验证仅作为已冻结的设计基线；
屏幕、触摸、外部资源和 WBA 适配可继续独立开发与验证，不能借此暗中推进
OTA 范围。

当前跨产品 OTA 矩阵记录在
`docs/validation/denzic-ota-product-matrix.json`：Companion 与 Listener 使用同一
`denzic_ota_v1` 协议 SHA，但 Denzic platform checkout commit 尚未统一，因此状态保持
`NO_GO_COMMIT_DRIFT`。这不是屏幕目标的硬件阻塞项，但它会阻止 SCR-14 被宣称为跨产品
发布 ready；后续只有在 Listener OTA 验收完成或明确产品决策要求对齐共享提交后，才更新
各产品子仓库并重新跑矩阵。

SCR-05 的 2026-07-11 严格诊断基线采用 Good Display 官方 STM32 序列：首帧
同时写入 SSD1681 `0x24` 与 `0x26` RAM 后以 `0xF7` 整刷，随后 5 次以 `0xFF`
局刷，并用第 6 次标准整刷验证清理路径。该严格诊断不是当前交互策略；正式
历史 revision 11 固件在 5 次后只标记维护到期，最迟 60 次执行 `0xC7` fast 单闪；
当前 revision 17 策略见下文，使用 `0xCF` 维护刷新。
局刷 BUSY 高约 225 ms，严格诊断整刷 BUSY 高约 649 ms，全部刷新完成。当前
局刷仍传输完整 5000 字节帧；按 CEMP dirty rect 缩小 RAM window 属于后续性能
优化，不能提前声称完成。证据见
`docs/validation/companion-screen-ssd1681-partial-refresh-wb55.json`。

SCR-02 的显示方向于 2026-07-11 由用户人眼确认通过。目标后端固定
`rotation=180`、`mirror_x=1`；摄像头预览可能自行水平镜像，不能替代人眼验收。

SCR-07 的中文、英文界面是两套独立单语资源，设置页提供语言选择；除语言选择
控件外，中文页不混入英文功能文案，英文页不混入中文功能文案。下一轮被接受的
主页目录依次为语音、状态、手机、设备、偏好、关于。portable gesture 层把触摸后端
的采样归一成 tap、left/right/up/down swipe；菜单只消费这些事件，不引用 FT6336、
HAL 或 WB55 引脚。日常页轻点触发短暂 happy 表情并回到 idle；连续两次合格轻点在
350 ms/32 px 窗口内触发录音，再次双击停止触控来源录音；非菜单入口的
左/右/上/下划全部是宠物方向互动。只有屏幕任意位置的近似静止长按才进入目录：
650 ms 给宠物逗弄回应，持续到 3 s 才打开菜单；明显移动不得进入菜单。
目录上下拖动按连续像素偏移滚动，不吸附项目，左划不打开功能页。只有点击
可见项目才进入：软件层立即确认命中项和目标页，先用一次 press-cue partial 刷新
给命中反馈，再用一次到达页 partial 刷新显示目标页；两次都不得退化成全刷。
详情页左边缘右划返回目录，目录左边缘右划返回日常页。滑动达到 30 px、
轴锁定达到 6 px 且主轴为副轴的 110% 后立即触发一次；点击允许 18 px 手指抖动，
单个有效 DOWN 采样即可成为轻点候选，但一旦进入纵向拖动态，松手事件即被消费，
不得再误触发点击。识别后必须连续 3 个无触点采样才解锁，FT6336 单帧掉点不会
让同一根手指重复触发。

portable gesture 启动自测还覆盖单采样显式松手点击、纵向拖动的连续锁轴与松手、
以及超时拖动后重新点击；这些路径必须保持通过，不能靠后端迁移时的字符串检查
替代。

revision 16 解决慢屏刷新造成的点击丢失：FT6336 的 `TP_INT` 接到 WB55 `PC6/EXTI6`，
`TP_RST` 接到 `PC10`；中断使首帧立即读取，轮询仍作为漏中断兜底。SSD1681 的
BUSY 等待每 10 ms 调用触摸服务，将原始样本和采样时间写入 256 项有界环形缓冲，
刷新完成后按原时间顺序送入 portable gesture。显示队列仍只合并显示请求，不得
冻结输入采样。revision 16 的历史主菜单曾有八项；当前 revision 32 收敛为
录音、状态、手机、设备、偏好、关于六个产品入口，中英文资源只替换文字，
不改变图标语义。
revision 16 CEMP 包为 28 clips、74 frames、372392 字节，CRC32 为
`0x028E38B4`。provision 镜像已写入并回读外部 QSPI，随后恢复普通固件；串口
确认 revision 16 从 `external_flash` 挂载、core selftest 全部通过、整刷约
1297--1299 ms。整刷 BUSY 期间共缓存并按序回放 131 个触摸样本，丢弃 0 个。
机器证据见 `.cache/validation/screen-revision16-provision/` 和
`.cache/validation/screen-revision16-touch-buffer-normal/`；INT/RST 的物理
contact/release 已有证据，真人触摸观感仍留在异步验收清单。

菜单切换必须是事务式的：日常页任意位置 3 s 长按成立时先停止播放器并丢弃尚未显示的旧表情帧，
菜单请求成功进入显示队列后才能把 presentation 状态改成菜单。队列拒绝请求时
必须继续保持日常页状态，避免“屏幕仍是猫脸、内部却认为菜单已显示”，并允许
用户直接重试 3 s 长按。

主页点击允许一笔输入产生两个短局刷阶段：press-cue partial 用于让命中项有被按下的
感觉，随后 target-arrival partial 显示目标页。不得把任一阶段退回标准全刷，也不得
回放过期页面。命中检测、进入状态与日志在软件层立即完成，并在顶部固定系统栏保留
到达提示；连续滚动期间只保留最新待显示菜单帧，不能回放手指已经
越过的旧位置。

FT6336 的 INT 线不能只在 MCU 侧配置 EXTI。目标适配器启动时还必须把控制器
`G_MODE (0xA4)` 写成 `0x01` 触发模式并读回确认；配置失败时保留 20 ms 空闲、
10 ms 接触轮询作为可诊断兜底，日志必须区分 `trigger` 与 `poll-fallback`。WBA
适配接口同样提供寄存器写 callback，避免移植后退回只读坐标的半套驱动。

revision 12 CEMP 包包含 28 clips、66 frames，总长 332232 字节，CRC32 为
`0x4E93E3F3`。其中中英文主页各有 8 张焦点帧，并与表情一起位于外部
`ui_assets`。idle 从 5 帧改为 1 张静止猫脸，开机只建立一次全刷基线；倾听、
思考、说话、开心、困倦和录音仍保留慢速多帧变化。普通固件不携带 provision
blob，实机已挂载 revision 12、通过 menu/gesture/presentation 自检并从外部
Flash 显示猫脸。机器验收日志见
`.cache/validation/screen-revision12-cat-touch-normal/nucleo-serial-raw.log`；真实
手势方向与点击区域仍需真人操作日志确认，不能以启动自检代替。

revision 13 将同一角色收敛为固定、圆润的可爱猫头外壳：耳朵、头部轮廓、鼻子
和胡须不随状态变化，眼睛、嘴、动作提示和状态标记只在猫脸内部变化。idle 仍为
单帧，慢动画时序和 external-Flash-first 原则不变。生成包仍为 28 clips、66
frames、332232 字节，CRC32 为 `0xC8C29EBC`。revision 13 已写入外部 Flash，
普通固件实机日志确认挂载 28 clips/66 frames、外部 renderer ready、自检通过且
启动仅一次 1298 ms 全刷；当时的滑动入口和猫脸真人观感仍需操作者确认。该入口
已被 revision 32 的中央 3 s 长按取代。

revision 14 改为实体外壳感知的表情：产品外壳提供猫头轮廓，屏幕只画白底黑色
眼睛、嘴、动作提示和小型状态标记，不再重复画耳朵、头部轮廓、鼻子或胡须。
物理方向基准为排线朝下，菜单箭头朝实体右侧；操作者已确认上下方向正确。菜单
纵向手势的旧版“松手吸附条目”策略已在 revision 15 废止，当前按连续像素偏移
渲染并只保留最新菜单帧。
生成包为 28 clips、66 frames、332232 字节，CRC32 为 `0x8EFC5024`。revision 14
已写入外部 QSPI，随后刷回 110.13 KB 普通固件；普通固件实机确认挂载 revision
14、从 `external_flash` 读取 idle、启动整刷 1298 ms 完成，触摸身份有效且无采样
错误。机器证据见 `.cache/validation/screen-revision14-features-normal/`。

revision 15 将主菜单改为电子书目录式自由拖动：逻辑状态保存 `0..167 px` 连续偏移，
不吸附条目；当前 200x200 电子纸资源按 16 px 选择最近的 12 档外部 Flash 显示帧，
刷新期间由 display queue 合并到最新位置，避免积压和连续闪屏。资源包为 28 clips、
74 frames、372392 字节，CRC32 为 `0xAF1B4D85`，已写入外部 QSPI 并恢复普通固件。
首次复位日志曾出现 FT6336 未应答，随后加入 WB55 板级 I2C 解锁恢复。最新复位日志
确认 revision 15 挂载、全部 core selftest 通过、1298 ms 启动全刷，FT6336 身份有效，
30 秒累计 963 次采样且 0 错误；连续拖动日志已记录 14/37/82/99 px 等非条目倍数偏移。
点击反白过渡已完成编译与自测，真人观感保留到待验收清单。机器证据见
`.cache/validation/screen-revision15-continuous-scroll-touch-recovery/` 和
`.cache/validation/screen-revision15-click-entry-transition/`。

revision 16 之后，原“反白过渡”改为单刷新直接进入：电子纸的反白帧会额外占用一次
约 1.3 秒刷新，不适合作为日常点击反馈。命中项、目标 view 和 revision 仍会写入
`[touch-ui] menu_entry_activate` 日志，触摸请求只提交最终目标页；该历史反白证据
不再作为当前交互验收标准。

## Revision 17: 手指锚定与低闪刷新

revision 17 的主页保留“连续像素滚动状态”，将 0..167 px 的滚动位置预渲染成每种语言
85 张旧版 external 资源帧，
每帧间隔 2 px。拖动时逻辑偏移严格按当前手指增量累计；队列只保留最新位置，
松手不吸附到项目边界。因此同一内容相对手指的位移保持一致，视觉上是“手指按住
目录再拖动”，而不是翻到下一项。电子纸每次实际波形仍约数百毫秒，不能诚实地
承诺 OLED 帧率；目标是用 2 px 定位、最新帧合并和不回放旧轨迹，减少可感知滞后。

SSD1681 日常交互不再使用旧的 `0xFF` 全帧局刷路径。驱动在面板方向变换后比较
当前帧与上一成功帧，只设定变化字节所覆盖的 RAM window，并以 `0xFC` 差分刷新。
相同帧不触发面板波形。连续五次差分后只标记维护到期；手指仍接触或刷新队列仍在
追随手指时绝不插入维护。最后一次交互后 1600 ms 无触点才以 `0xCF` 做一次
低闪质量维护，重新写入两个 RAM 平面；`0xF7` 多闪全刷仅保留给初次未知基线和
传输故障恢复。这是 machine-ready 策略，残影、可见延迟和维护闪烁仍需 WB55 真屏
复测，记录见 `docs/validation/companion-screen-ssd1681-partial-refresh-wb55.json`。

## Revision 18: 统一电子宠物五官与外部资源

revision 18 将十个白底黑色状态收敛为同一只电子宠物的可复用五官：软豆形眼睛带
双高光、统一 W 形嘴、状态专属视线/眼睑/腮线/动作标记。同步完成状态额外使用
庆祝星光，避免与开心状态成为同一帧。实体外壳继续提供猫脸轮廓，屏幕不得绘制
耳朵、头部、鼻子或胡须。每个表情和两个屏幕 profile 都通过空白、密度、外壳留白
和相互可区分的 PBM 视觉契约验证。

revision 19 的 CEMP 保持 revision 18 的视觉内容，但将逐帧 raw 数据改为独立
PackBits：28 clips、220 frames、403,499 bytes、CRC32 `0x1B01C578`。它已完成
外部 `ui_assets` provision 与普通固件挂载验证；普通 WB55 固件不重新链接大表情数组，
临时 provision 镜像也能装入 MCU Flash。它保留为可回溯的已验证资源版本。

## Revision 20: 固定标题栏与手机式直接拖动

revision 20 保持相同的表情体系，将目录资源更新为 32 px 固定黑色标题栏、其下 6 px
白色隔离带和从 y=38 开始的可滚动 viewport。每种语言的旧版 85 帧都校验标题栏与隔离带
字节完全一致，目录内容永远不能绘制到该区域。拖动会在纵向锁定后保存“手指起点 +
起点滚动偏移”，每个后续采样由这个绝对锚点计算目标偏移；采样丢失、队列合并或慢面板
都不能让积分误差累积。它仍然不做项目吸附，也不在松手后伪造 OLED 式惯性。

FT6336 活动采样和 BUSY 期缓冲轮询均为 5 ms，空闲轮询为 12 ms；纵向锁定为 6 px、
3 px 轴余量和 110% 主轴比例。SSD1681 首次显示或错误恢复才硬复位控制器；局刷在 `0xFC`
前只写新图层 `0x24`，波形完成后才将新图同步到 `0x26/0x24`，复用控制器保留的旧图层。
该顺序避免拖动期间反复复位或把旧图层重写进可见波形。revision 20 CEMP 为 28 clips、
220 frames、396,629 bytes、CRC32 `0x478BA8DC`，已写入 `ui_assets` 并由普通固件挂载。
启动日志见 `.cache/validation/screen-revision20-mobile-scroll-runtime/`；真实手指观感仍仅在
明确“开始验收”后记录。

## Revision 21: 点击宽容度与短手势残影清理

revision 21 让点击优先于轻微手抖：空闲轮询为 8 ms，点击允许 1100 ms、24 px 位移；
只有达到 10 px 且满足 5 px 轴余量、120% 主轴比例才锁入拖动。抬起只需一个无接触样本，
因此 9 px 内的纵向手抖不会被主页拖动吞掉。主页行间的 3 px 视觉分隔与左右 4 px 边缘
也不再形成死区。

FT6336 启动时读回阈值 `0x90`、active/monitor period `0x04/0x04`；同一寄存器契约
同时位于 WB55 HAL target 和 WBA55/WBA65 callback target。`MAINTENANCE` 在最后一次
交互后 1200 ms 无触点时直接执行一次 `0xCF` 低闪清理波形，不再等待累计五次局刷；
手指接触期仍仅走 `0xFC` 差分，`0xF7` 仍只用于未知基线或传输恢复。真屏残影和维护闪烁
仍等待明确验收后记录。

WBA 预移植层已提供 callback-only 的 `panel_target_stm32wba`、
`screen_scheduler_stm32wba`、`screen_gatt_stm32wba` 和
`touch_target_stm32wba_ft6336`，覆盖 WBA55/WBA65，并通过静态验证及 ARM GCC
严格语法编译。当前仍为 `DRAFT_PRE_PORT`：没有 CubeWBA 工程、WBA 引脚绑定和
真实 WBA 屏幕/触摸证据前，不宣称 WBA 硬件等价。

同一日志证明 FT6336U 在 I2C `0x38` 一次探测成功，身份寄存器为
`cipher=0x64`、`firmware=0x01`、`chip=0x11`，10 秒累计 333 次采样且 0 错误。
这完成控制器和轮询链路的机器验收；down/contact/up、点击区域和三种滑动方向仍
必须由真实触摸日志确认。证据见
`docs/validation/companion-screen-touch-ft6336-wb55.json`。

SCR-04/SCR-09 的历史首条真实动画基线是 revision 11 idle 眨眼：frame 0 为 intro 睁眼，
frame 1..3 为 loop 半闭、闭眼、半开，frame 4 为 tail 睁眼。首帧时长
1600 ms 并整刷，后续帧 650/650/650/1000 ms 并局刷；实机日志完整读取
外部 frame index 0..4，首帧刷新 1298 ms，四次局刷各约 450 ms，队列结果
均为成功。该证据证明 player、RTC timer、显示队列、QSPI 帧读取和 SSD1681
刷新链路。revision 12 已把无事件 idle 改成单帧，避免电子纸连续闪动；眨眼
关键帧仍由生成器保留，后续只可作为明确交互反应使用。历史证据见
`docs/validation/companion-screen-emote-animation-wb55.json`。

产品事件和菜单由 HAL-free presentation 状态机统一：非 idle 事件进入表情播放器，
回到 idle 时按来源恢复：菜单触发的临时表情恢复原菜单的 view/page/language/flags，
日常页触发的表情恢复日常 idle，不会误入设置。2026-07-11 实机模拟
`wake_detected` 后显示 listening 的 intro/focus/wave/focus 动画，局刷约
448-450 ms；当时的严格诊断固件在 5 次局刷后执行标准整刷，10 秒后以 450 ms
局刷恢复中文主页。正式 revision 11 已由 fast 单闪维护替代该历史行为。
状态机先处理产品状态再推进 player，实机日志确认 `restore_menu` 与菜单 scene
之间没有陈旧表情帧；随后已刷回普通菜单固件。证据见
`docs/validation/companion-screen-presentation-wb55.json`。

第二条产品动画基线是 speaking：构建脚本通过
`-EpaperProductExpressionDemoExpression speaking` 选择真实 `speaker_prompt`
信号，而不是在 player 内写死表情。frame 11..15 保留 intro/三帧 loop/tail，
嘴型与声波按 medium/soft/open/soft/medium 变化；实机观察到 frame 11..14、
448-450 ms 局刷、历史严格诊断整刷，以及 10 秒后无陈旧帧地恢复中文主页；
正式 revision 11 不再沿用该多闪维护行为。

第三条产品动画基线是 thinking：`recording_stop` 信号进入 12 秒思考状态，眼睛
和思考点按 base/inward/outward/inward/base 变化。revision 7 实机观察到
frame 10..13、448-450 ms 局刷、历史严格诊断整刷和干净恢复菜单。全局 frame index
只在对应 pack revision 内有效；产品和固件始终按 clip 名称寻址，不能依赖索引。

第四条产品动画基线是 recording：右上录制灯按 base/soft/pulse/soft/base 呼吸，
脸部保持稳定。演示构建在 10.206 秒发出真实 `recording_stop`，player 先播放
recording tail frame 26，再自然交接 thinking intro frame 10，thinking 结束后恢复
菜单。普通固件不包含演示超时分支，编译加载段仍为 109524 字节。

第五条产品动画基线是 happy：`speaker_result` 信号进入闭眼笑脸，嘴弧按
broad/soft/bright/soft/broad 变化，bright 帧增加两侧腮线。revision 9 实机
观察到 frame 20..23、448-450 ms 局刷和 6 秒自动恢复。当前交互中，日常页轻点
复用该信号并恢复 idle；从菜单触发时仍恢复菜单。

2026-07-11 revision 12 正式固件实机日志确认：启动只执行一次 1298 ms 全刷，
随后至少 18 秒不再刷新。产品动画只播放一个
intro/loop/tail 周期并保持尾帧；快速连续菜单输入只保留最新菜单请求，避免把
已经过时的中间页面逐张刷出来。交互局刷达到 5 次后记录维护到期但不中断当前
操作，最迟在 60 次局刷安全上限执行一次 `0xC7` fast 单闪维护；标准 `0xF7`
多闪全刷只用于开机建立未知基线。fast 完成后同步 `0x26` 旧图 RAM，后续局刷
继续使用正确基线。

## Revision 22: 方向注意力与安静刷新

revision 22 将日常页的触点映射为 `3x3` 方向注意力区，从外部 Flash 的
`attention.*` 短片选择眼神方向。每个短片保留“注意 -> 回应 -> 安定”三帧；在
开心状态中再次点击也会以新方向重新回应，不被状态去重吞掉。表情的
五官层、时间线、CEMP 资源和屏幕 profile 相互分离，以便未来更换屏幕尺寸、表情资产或
WBA55/WBA65 面板适配器时无需改动核心交互逻辑。

资源包现有 37 clips、247 条帧时间线记录。相同位图在 CEMP 中只存一份帧载荷，但每条时间线仍保持独立时长、脏区和随机读取。资源包从
422,986 B 降至 405,927 B；普通固件仍只从外部 `ui_assets` 读取，一次性写入固件仅因为暂时嵌入
资源包而以 `-Os` 链接。

残影策略保持层级化：相同帧不刷，拖动期只用脏窗口 `0xFC` 局刷且只保留最新一帧，放手 1200 ms 后仅做一次
`0xCF` 低闪维护，`0xF7` 只用于开机基线或传输故障恢复。这不会把墨水屏伪装成 OLED，但会避免在手指接触期又插入多次全刷。

## Revision 23: 参数化电子宠物表情

revision 23 将表情从“按 clip 名播放固定脸”改为 `pet_expression` 参数化合成：
ExpressionV1 状态、触点的连续 gaze、眼睑开合/倾角、嘴形、腮线与小状态标记共同决定
一张脸。日常轻点的三相回应仍沿用 CEMP 的节奏，但每一帧都按真实触点生成，不再只落到
九张预绘制眼神图。十个产品状态仍有稳定身份，并可由 phase/seed 产生受限微变化。

资源原则不回退：菜单、时间线、完整美术、字体和可替换资源仍留在外部 `ui_assets`；
`pet_expression` 只使用既有 200x200 framebuffer，不在内部 Flash 存全屏位图或第二张
持久帧。未来换屏只需更新 profile/目标驱动及视觉参数，WBA55/WBA65 复用同一 pose 和
render API。

静默残影维护扩展到菜单和日常 pet 表面：响应停止后等 1200 ms，只请求一次 `0xCF`，
不会在手指按住或短回应播放中插入全刷。实际观感仍保留到操作者明确开始验收时统一确认。

WB55 已完成机器烧录与串口验证：revision 22 外部 pack 正常挂载，参数化 renderer
及 64x64 缩放自检均通过；启动只执行一次 1297 ms `0xF7`，旧 idle timeline 的后两帧
被消耗但不再刷新。证据为
`docs/validation/companion-screen-pet-expression-wb55.json`；触点精确注视、性格观感和
残影感受尚未启动人工验收。

## Revision 24: 高级陪伴感行为层与防误触菜单

日常猫脸拥有完整的触摸表面：轻点始终是互动，不再把面部中央的左滑误判为设置。
revision 24 曾采用右侧边缘抽屉手势进入菜单；该入口先被 revision 32 的中央
近似静止 3 s 长按取代，后来由 revision 39 收敛为任意位置近似静止 3 s 长按。
菜单主页仍使用左侧边缘右滑退出，因此设置与陪伴的手势
边界清楚、可预测。

新增目标无关的 `pet_behavior`：用 valence、arousal、curiosity、affection、engagement
和精确触点构成小型连续行为状态，再驱动现有 `pet_expression` 的眼宽、反光比例、注视、
眼睑、嘴形、腮线和标记。产品事件和触摸才改变它；静息态不添加高帧率动画，避免为了“活”
而让墨水屏频繁刷新。这样可以逐步做出性格和陪伴关系，而不是把更多固定脸塞进内部 Flash。

触摸也有空间语气：上部是好奇的短暂亮点，中部是亲近的宽眼和腮线，下部是更安静的回应，
左右继续由精确 gaze 表达。它们都由规则合成，不需要新表情位图或额外刷新循环。

资源原则不回退：行为状态和 renderer 是小型应用代码；可替换的大美术、节奏、字体、故事和
未来 personality pack 继续在外部 `ui_assets`。WBA55/WBA65 必须复用 `pet_behavior` 与
`pet_expression`，只替换屏幕 profile、存储和面板 target adapter。

## Revision 25: 完整脸部姿态与可爱溢价感

日常脸不再只依赖眼睛开合。`pet_expression` 以同一套 pose 同时驱动眼形、眼睑、眉势、
眉高/左右不对称、鼻口比例、腮线和整张内脸重心：倾听会抬眉靠近、思考会单侧挑眉并偏头、
开心会收眼、扬眉、笑口和更饱满的脸颊，疲惫与低电量则用下垂重心、困倦眉势和收缩嘴形表达。
触摸后眼睛并非单独追点，鼻口和脸颊也以受限幅度向触点方向靠近，形成一次有起势、回应与
回落的完整面部反应。

这一版取成熟电子宠物的产品原则而不复制其美术：稳定身份、协调的多部位表情、互动累积出的
个体差异，以及克制而有因果的回应。200x200 单色电子纸不追求高帧率动画；每次刷新都必须由
真实触摸或产品事件获得，继续沿用局刷和一次静默维护策略。新增字段与 renderer 全部保持
target-free，并保持零张内部全屏表情位图；未来换屏或迁移 WBA 时复用同一套姿态/行为 API，
可替换的主题、美术和大时间线仍放在外部 `ui_assets`。

## Revision 26: 软萌比例精修

默认待机脸取消常驻眉毛，留出更安静、更高级的白底空间；眉势只在倾听、思考、担忧等需要
表达的状态出现，并收成短而圆的轻笔触。新增眼距和双眼轻微高低差：亲近/开心时眼睛微收，
倾听时轻展，思考时以单侧眉和极小高低差表达，而不是堆叠状态符号。鼻口和脸颊继续共享整脸
重心，保证每次互动看起来是一张统一的猫系内脸。

这一层仍是确定性的参数化几何，只增加几个字节的 pose 状态，内部 Flash 不新增任何完整帧或
可替换美术。产品视觉包、主题、字体和大时间线仍是外部 `ui_assets` 的职责；WBA55/WBA65
继续复用相同的行为与 renderer API。

## Revision 27: 十状态可见差异防回退

嵌入式 `pet_expression` 自检现在会用真实的参数化 renderer 将十个 ExpressionV1 状态逐一
缩放绘制到同一张 64×64 one-bit framebuffer，并计算位图签名；任意两个状态渲染结果相同即
判失败。它保护“不要只有几种固定模板”的已知产品要求，但不替代真实电子纸上的审美判断。
相同算法仍为小型确定性代码，不增加静态位图、额外持久帧缓存或 WBA 专有逻辑。

## Revision 28: 柔和可爱轮廓精修

开心、同步完成和触摸的收束阶段不再只是把圆眼缩小，而是通过真实的上弧黑色轮廓形成弯月
笑眼；困倦状态则使用反向的下弧，避免所有小眼睛变成同一种符号。笑嘴、软嘴和委屈嘴的末端
加入极小圆角收口，让鼻子到嘴巴的线条在 200×200 one-bit 面板上更像完整的猫科内脸。
这仍是同一套参数化几何与现有帧缓冲，不引入面板位图、持久第二帧缓存或 STM32WBA 专有代码。

## Revision 29: 有连续性的情绪系统

Companion 不再把每次事件当作独立的“换脸指令”。`pet_behavior` 现在分离即时事件、会随真实
时间回落的心境和可保存的长期亲密度：心境在 calm、curious、affectionate、delighted、restful、
worried 之间由愉悦度、唤醒度、好奇、亲近、安静时长和固定性格种子共同决定。触摸、倾听/录音、
思考、说话、同步完成、低电和错误都会以不同方式改变这些量，因此下一次看到的内脸有前因，
不会是随机的固定模板。

电子纸不为模拟生命而高频刷新。行为时间只在已经发生的触摸、产品状态或日常页进入时推进；
安静很久后它在内部进入松弛态，并在下一次合理刷新机会才以更安静的眼口表现出来。`comp_pet_behavior_memory_t`
是将来外部 user-data 分区的轻量记录，目标层须低频合并、CRC 校验并与 OTA 资源分区隔离；portable
行为代码不持有 Flash 地址、写入时序或任何 WB/WBA 外设事实。

六种心境及记忆导入导出均由嵌入式自检逐项覆盖，并以启动日志留下机器证据；该自检不申请
电子纸刷新，不能替代后续的真实人眼表情验收。

## Revision 30: BUSY 期触摸时序保真

SSD1681 等待波形完成时，FT6336U 仍以 5 ms 采样。此前无触点样本也进入 256 格缓冲，
一次约 1.3 秒的全刷可能挤掉真正接触的时序。现在缓冲只保留一次接触的按下锚点、最新合并
坐标和抬起样本；无接触样本不入队。这样屏幕恢复后，手势状态机仍用原始按下点和最新手指
位置计算拖动，而不是处理堆积的空样本。WB55 启动机证确认约 300 次采样、`buffered=0`
和 `dropped=0`；真实手指在 BUSY 期间的跟手感仍保留给明确验收。
固件还对空闲、按下、连续移动和抬起的缓冲生命周期运行自检，并在 `touch-health` 中报告
`wait_buffer_selftest=1`；这能防止锚点/最新坐标/抬起顺序退化，但不替代真实手感判断。

## Revision 31: 方向化宠物抚摸

日常猫脸的滑动不再被当成无效输入。管理入口最终收敛为屏幕任意位置近似
静止 3 s 长按，所有 left/right/up/down swipe 都交给 target-free `pet_behavior`：
左右划让内脸朝手指终点
俏皮侧望并带不对称眉眼，上划抬眉睁眼并出现好奇亮点，下划以暖眉、笑口和腮线安定下来。
触点终点仍决定连续 gaze，行程与时长只形成受限的短期能量，不新增高频循环、全屏位图或
额外 Flash 写入。轻点保持“看向你”的独立语义。

这套 `comp_pet_behavior_note_stroke` / `comp_pet_behavior_compose_stroke_pose` API 不引用
FT6336、HAL、WB55 管脚、面板或 Flash。WBA55/WBA65 的触摸 adapter 在完成坐标归一后
必须调用同一逻辑；用户数据只继续保存长期 attachment/interaction，短期 stroke 不写入
Flash。WB55 会先以启动探针获得局刷和完整串口证据，真实手指的可爱度、灵敏度和残影
仍按异步规则留到操作者明确开始验收。

## Revision 32: 产品菜单与长按入口

revision 32 把目录从历史演示型菜单收敛为 Companion 当前产品任务：
录音、状态、手机、设备、偏好、关于。屏幕资源为中英文两套单语页面，每种语言的主页
使用 43 张 2 px 步进外部帧覆盖 0..84 px 连续滚动；大资源继续在外部 `ui_assets`，
普通固件只保留最小救援 UI。旧的表情预览、同步、存储入口不再是主页一层入口，
避免菜单看起来像调试面板。

日常页入口后来被 revision 39 收敛为任意位置近似静止长按：650 ms 先给宠物逗弄回应，3 s 后进入菜单。
普通轻点和四向滑动只改变宠物表情，不能误入设置。主页点击先显示一次 press-cue 局刷，
再进入目标页局刷；这两次都是交互反馈，不得使用标准多闪全刷。BLE 连接状态在
状态页和手机页都可见时更新，避免手机页显示旧连接状态。

当前候选资源已推进到 CEMP revision 52，表情关键帧由 `import_generated_expression_sheet.py`
从 `docs/art/generated_pet_expression_sheet_v5.png` 裁切导入，生成包为 33 clips、159
frames、287732 bytes、CRC32 `0xDEFC096E`；rev52 待 provision/normal 运行机器复验。最后一次已完成的机器实证是 rev51：外部 Flash 挂载 revision 51、`source=external_flash`、`pet_behavior_selftest=pass failure_code=0` 和首次全刷完成；真实触摸手感、残影、
任意位置 3 s 长按入口和语言切换仍在用户明确说“开始验收”时统一记录。
下一次接硬件时先跑 `pwsh -NoProfile -File .\tools\run_wb55_screen_runtime_recheck.ps1 -CheckOnly`
确认 rev52 provision/normal 复验顺序，再通过 workflow hardware lock 执行同一脚本的
`-Execute -WorkflowLockHeld`；该脚本只收集机器日志，不替代人工触摸/视觉验收。
两份 rev52 串口日志都通过 `verify_wb55_screen_runtime_recheck_logs.py` 后，必须使用
`python .\tools\promote_wb55_screen_runtime_recheck.py --apply` 推进证据状态；禁止手工
把 `REVISION_52_RUNTIME_RECHECK_PENDING` 改成 runtime pass。当前 promotion gate
在缺日志时保持 `NO_GO_LOGS_NOT_PASS`，并列出阻塞项。
相关 verifier 允许两种机器状态：pending 时 `pre-acceptance` 必须保持
`NO_GO_RUNTIME_RECHECK_PENDING`，promotion 必须保持 `NO_GO_LOGS_NOT_PASS`；
日志 PASS 并 `--apply` 后，promotion 必须变为 `APPLIED`，pre-acceptance
才可进入机器 PASS，但真实触摸/视觉验收仍保持 `PENDING_HUMAN`。

## Revision 35: premium pet polish 子目标

当前精修目标是让 Companion 更像可出售的电子宠物，而不是一个播放固定模板的屏幕。
对标成熟产品时只吸收原则：大量细微状态、触摸/滑动参与情绪、长期个性和非语言反馈；
不复制其它产品的美术。当前主表情路径使用外部 CEMP PBM 帧，按
`genref_sheet_12_inner_faces_v5` 生图参考把眉毛、豆豆眼、高光、眼睑、嘴鼻、腮线和
小状态符号作为整张内脸一起变化。紧凑程序化 rig 只保留为救援、维护和小型行为兜底。
这样电子纸不需要 OLED 帧率，也能避免“只有眼睛在动”。

菜单精修同步进入这个子目标：外部 CEMP 菜单/表情资源提升到 revision 52，并按生成图参考抽象为
可替换 PBM/CEMP 资源和少量救援 one-bit UI 规则：顶部固定系统栏保留内脸身份 chip，主页增加宠物状态卡，项目使用圆角功能胶囊、反色当前项和不同图标，
关键入口带小星光，偏好页和内部救援菜单只画眼口/状态标记，不画猫耳、头部轮廓或胡须；
这些轮廓由实体外壳负责。录音、状态、手机、设备、偏好、关于继续作为六个产品入口。
大美术、字体、菜单帧和未来 personality pack 仍属于外部 `ui_assets`，内部 Flash 只保留小型
参数化行为和救援 UI。真实“可爱溢价感”、触摸跟手、残影和低闪维护仍等待用户明确开始验收。

生图结果现在被固化为 `genref_sheet_12_inner_faces_v5` 风格契约，而不是散落的临时坐标。
正常表情美术集中在 `card_renderer.py` 的 PBM 生成器，救援/维护锚点集中在
`pet_visual_style.h`；菜单 chip、卡片、详情页内脸锚点集中在 `MENU_STYLE`。以后重新生图或
调整高级可爱风时，先调这些 style/render layer，再重新生成 PBM/CEMP 和运行验证；不得为了
贴图方便把大位图塞回内部 Flash，也不得让固件重新绘制实体外壳负责的猫脸轮廓。

## Revision 54: 运行时交互回归修复

2026-07-13 的 owner 反馈把“旧菜单仍在屏上、触控不跟手、双击录音无可见结果、长按没有
过渡表情、录音没有状态表情、菜单边界残影过多”列为同一条运行时链路的 P0 回归，而不是
静态构建通过后的可接受差异。机器验证必须分别记录当前 CEMP revision、down/move/up
`sample_age_ms`、手势分类、录音状态机和表情播放器的 request/result 标记；未出现这条
reset-bounded trace 前，不能以 source/build PASS 声称开发板正在运行 revision 53。

本轮调研记录：Good Display 的 GDEY0154D67-T03 产品页列出 200x200 SSD1681、局刷约
0.3 s、完整刷新约 2 s，并明确该触摸版使用 FT6336U；其公开规格还列出触控工作/待机电流。
FT6336U datasheet 说明 I2C 主机接口、最高 100 Hz report rate、Active/Monitor/Sleep 三种
模式和上电后由 INT 开始上报。来源分别为
`https://www.good-display.com/product/258.html`（2026-07-13 读取）和
`https://files.waveshare.com/wiki/common/FT6336U_Datasheet.pdf`（2026-07-13 读取）。

因此不会假装电子纸可以成为 OLED：主界面继续用 `0xFC` 差分局刷，菜单主页以队列合并的
当前行 press-cue 跟随手指；当前 owner-accepted v3 是一张六项同屏首页，竖向接触不得再
伪造历史编号滚动帧。进入菜单和从菜单返回日常页是唯一的视觉边界，各先取消延迟维护再做
一次 `0xF7` 净化刷新，确保不会接着再触发一轮 `0xCF`。3 s 长按在 650 ms 先播放外部 CEMP
`thinking` 过渡表情；日常双击使用 650 ms/40 px 候选窗口，触控录音开始请求 `recording`，
存储成功请求 `sync_complete`，失败请求 `error`。这三类状态仍由 CEMP 名称和外部资源决定，
后续换生图只改资源/manifest，不要重新发明 UI 或程序化美术。

## Revision 55: 四项一页菜单与活体入场表情

在 owner 明确开始验收后的第一个 focused review 中，
`menu_boundary_single_clean_refresh` 的结果为失败，原始备注是“菜单太小了, 换成四项一页吧”。
这不是通过调字体或触控阈值回避的问题：`menu-v3` 的六项同屏密度被产品决策替换。先在
`docs/art/iterations/companion-menu-v4/iteration-ledger.json` 固化 prompt 和 source，再生成新的
200x200 单色 UI reference；在 owner 接受 v4 reference 前，不得在 C 代码里自由拼凑四项菜单。

同一轮 owner 还指出长按进菜单的 `thinking` 表情像在播放贴图。新的美术目标固定为
`anticipation -> decision -> settle` 三拍的整张内脸表演：眉、瞳、高光、嘴鼻、腮线和少量
装饰符号必须共同变化，且每拍有可读差异与停留时间。对应 prompt 和 keyframe baseline 先写入
`docs/art/iterations/companion-pet-menu-entry-v1/iteration-ledger.json`，之后才可转 PBM/CEMP；
禁止用程序化眼睛抖动、静态贴图循环或猫头轮廓冒充这条入场表情。

## Revision 56: 菜单入场的同风格活体表演

第一轮 `menu-entry-v1-2026-07-13` 生图被 owner 拒绝：它虽然有三段式变化，
但换成了粗眼线、阴影腮线和夸张嘴形，和已被接受的 v5 内脸完全不是一个美术
语言。该输出保留为拒绝证据，绝不进入 PBM/CEMP 或刷入设备。

后续入场表情只允许在 `generated_pet_expression_sheet_v5.png` 的同一五官语汇里做
连续表演：椭圆黑眼与单个白色高光、短圆眉、微小鼻/W 嘴、点状腮红、极少的黑色
状态符号和大量白色留白。三拍的美术验收重点不是“每一拍换一张贴图”，而是同一张
脸从注意到触摸、做出愉快决定、安静落入菜单的连贯微动作；眼睛位置、眉势、眼睑、
高光、嘴形、腮点和至多一个小符号均须有受限的前后关系。不得引入新的卡通画风、
粗长上眼线、阴影/斜线腮红、巨大的张嘴或实体猫头轮廓。v2 prompt、输出、哈希、
差异审查与 CEMP 映射持续记录在入场表情 ledger；没有 owner 对生成基线的接受，不得
用代码自行补画或替换运行时资源。

## Revision 57: v5 轮廓复用，而非相近画风

owner 明确指出“和以前的风格完全不同”后，入场表情的约束从“使用 v5 元素”收紧为
“复用 v5 的角色轮廓和比例”。后续图像生成必须把
`generated_pet_expression_sheet_v5.png` 作为直接视觉母版：双眼、眉、鼻/W 嘴、腮点的
轮廓、尺寸和相对锚点保持同一角色，只准在瞳光/视线、眉势、嘴的细小开合、腮点偏移和
一枚稀疏符号上做连续姿态变化。不得以“相近可爱风”重新插画一张脸。

`menu-entry-v3` 在账本中先记录精确 prompt、v5 哈希、v2 未接受状态和后续源图到 PBM
比较门槛。图像审查必须同时核对三拍对 v5 的五官锚点/比例以及三拍彼此的连续性；若任一
项不成立，输出仅作为拒绝证据保留，不能改 CEMP、固件或设备。该约束链接
`COMP-REQ-020`，并在 owner 接受生成基线后才进入外部 Flash 导入阶段。

## Revision 58: 四项分页与可靠右滑退出

owner 再次在运行中的 WB55 板上确认：当前仍显示已退休的六项首页，且右滑不能退出菜单。
这证明现有 revision 53 资源/代码尚未实现 `COMP-REQ-019`，不能把候选 v4 图或静态验证当成
板端完成。新的运行时基线由 `COMP-REQ-021` 固定：主页一页最多四项，六个真实入口经明确的
两页切换呈现；从任意菜单页的合格右滑直接回到日常 pet 页面，不能要求从左边缘起滑或依赖
不可见的命中区。手势须使用既有方向锁、去抖和抬起解锁路径，日志记录
`menu_right_swipe_exit`，并在基线有效时只执行一次 menu-to-daily 的 `0xCF` 单闪清理边界。

实现必须先让已记录的 v4 生成稿完成接受、再导入对应中英文 CEMP 主页资源；禁止为了赶进度在
C 代码临时绘制四项菜单。page index、点击命中和页面指示器必须等视觉基线批准后才开始。全局
right-swipe exit 是独立的非视觉修复：它已抽成 HAL-free menu action，由目标层完成一次 clean
menu-to-daily 过渡，不等待候选图导入，但不能以此声称四项主页已完成。该修复不改日常页的
四方向宠物互动或双击录音语义。

owner 已授权在该修复有机器证据后立即启动 Listener 风格的统一中文弹窗验收。视觉四项分页仍为
`PENDING_OWNER_VISUAL_REVIEW`，不可与手势通过混写；第一个 popup 改为 `1/13` 的任意菜单页
右滑退出，记录所用固件/资源 revision、串口重置边界、刷新计数和 operator result/note。通过后才把
这条手势体验写成防回退契约；四项分页在 owner 批准 v4 源图、PBM/CEMP 对照和真实屏幕复核后单独验收，
再推进 TP_INT Stop wake、双击录音和长按入菜单等后续项目。
不能因为用户已说“开始验收”就跳过当前已报告问题的 AI 修复和机器验证，也不得弹窗要求重做
已经记录过的失败观察。

## Revision 59: ACPT-01 失败 triage

ACPT-01 使用 firmware commit `d8f3da9` 对 `NUCLEO-WB55RG` / `COM13` 进行了正常刷入和
reset-bounded serial capture；operator 选择 `失败`，完整备注保存在
`.cache/validation/companion-acceptance/acpt-01-menu-right-swipe/operator-prompt-observation.txt`。
这不是“机器日志成功、人工感受另说”：备注中的每一句都是 P0 修复输入。

串口显示新的 `menu_right_swipe_exit` 已从 `start=48,122` 到 `end=101,122` 分类，随后请求一条
`menu_boundary=exit ... refresh=full`，但在此前还出现同一首页上的 `menu_press` 排队；这解释了
为何仅凭 marker 不能声称退出跟手。修复须让已方向锁定或即将横向退出的接触不会先产生行按下反馈，
并用真实起止样本、识别时延和一次退出帧证明。

日志只有一次逻辑 `0xF7` 请求，肉眼却报告五次闪烁；因此“单个 full request”不等于“一次可见闪烁”。
在改动前必须研究 SSD1681/GDEY0154D67 的局刷/清残波形和控制字，记录波形选择的技术依据，再以
物理可见相位和残影作为判定，禁止用重复全刷掩盖问题。

同一次长按的 `long_press` 在 `3309 ms` 才分派，晚于 3000 ms 合约。触摸事件在屏幕忙时被合并/延后
处理的路径必须使用采样时间或等价的准确时基，且不能以移除长按逗弄/菜单过渡来缩短时间。目标是
stationary long-press 在 3000 ms 合约附近可靠触发，修复后以真实时间戳日志复核。

六项首页仍被 operator 判定为太小，这再次确认 `COMP-REQ-019`。它保持
`PENDING_OWNER_VISUAL_REVIEW`；不得用 C 绘制临时四项替代，也不得把此次右滑修复写成菜单密度通过。
在这四个问题分别有机器证据前，ACPT-01 不重开、更不能推进 ACPT-02 到 ACPT-13。

## Revision 62: ACPT-01 低功耗唤醒与交互卡顿 triage

同一个 `1/13` canonical popup 的第二次结果仍为失败，operator 原文为“直接无反应了，没有首页唤醒”，
随后补充“而且现在用着相当的卡顿, 这个产品, 需要优化”。本轮串口证明 PC6/FT6336 的触控中断与
首个 decoded contact 都到达，Stop 也正确被 touch blocker 解除；650 ms hold marker 已记录，但既没有
`daily_to_menu` 的 3000 ms 决定，也没有把静态 sleepy face 唤回日常 face 的显示请求。触控期间还以约
5 ms cadence 输出 `[touch-irq]`，几秒操作形成上千条同步 UART 文本，这不是产品路径可以保留的开销。

`COMP-REQ-022` 因此增加两项必须先修的同一交互契约：当已批准的静态 low-power face 正在显示时，第一个
已解码 contact 只允许请求一次现有外部 Flash `idle` 日常脸的 differential wake（无全刷、无未批准新美术、
无定时动画）；正常运行时不得为每个 IRQ/采样打印串口，保留状态改变、gesture 和限频健康计数即可。显示
请求的等待期间仍要用采样时间驱动手势，因此唤醒不能把 stationary 3 s long press 再次推迟。修复后先以
reset-bounded log 同时证明 `low_power_touch_wake`、`gesture=long_press` 的时长、无 per-IRQ flood 与
单个 `0xCF` 菜单边界，再重开同一个 `1/13` popup；禁止推进 ACPT-02。

## Revision 63: ACPT-01 菜单边界真实单刷新波形

同一 `1/13` 复验的最新 operator 原文为“进入菜单的刷新不行, 你就不能只全刷一次吗, 一定要5次? 看看手册”。
这不是把已记录的“闪烁一次”缩写成同义句：新日志显示 `daily_to_menu` 在 3006 ms 正确发生，菜单边界也只发送了一次
`0xCF`，但使用方仍看见多次黑闪。SSD1681 手册把 `0xCF` 定义为以 Display Mode 2 激活；随后取得的 Good Display 样例
实际用 `0xB1`、`0x1A 0x64 0x00`、`0x91` 装入 Mode 1 温度/LUT profile，再用 `0xC7` 更新。当前目标两者都没做，
所以 `expected_visible_flicker=single` 是实现侧假设，不是实际物理证据。

已取得并审查 Good Display `GDEY0154D67-T03 STM32 Sample Code`（`S-GDEY0154D67-FP-Touch`，SHA-256
`202ADAB27515FDBA790565F643C3C83C52C11FF36844E8C387F66676C3D82CD4`）的完整快刷序列；将 portable
`MAINTENANCE` 意图映射到该明确 Mode 1 profile。菜单进入与右滑退出各只能请求和执行一次真实面板刷新；运行日志必须
记录 profile、控制字、激活次数和结果。完成静态、编译、刷写、串口与同一 `1/13` 物理复验前，不得推进 ACPT-02。

## Revision 61: ACPT-01 触控时基与单闪边界修复

根因分析确认：主页在第一个接触样本立刻排队 `menu_press`，使本应约 190 ms 的右滑被
面板 BUSY 后的触控缓冲延迟处理；650 ms hold cue 又启动一张电子纸表情，令 3 s 长按直到
3309 ms 的合并样本才触发。修复改为先运行可移植 gesture 状态机，主页 press cue 延迟
160 ms，横向轴一经锁定就取消该候选，因而右滑不会先刷行按下状态。650 ms 时只记录
non-blocking hold acknowledgement，真实 3000 ms 手势在正常 5 ms 触控轮询里触发菜单。

Good Display 的同族资料明确指出全刷可多次闪、fast 刷一次、partial 不闪；研究和链接
保存在 `docs/validation/companion-screen-menu-boundary-waveform-research.md`。因此日常/菜单
边界不再主动请求 `0xF7`：portable 层请求 `MAINTENANCE`，WB55 SSD1681 基线有效时映射到
`0xCF`，驱动日志写入 `expected_visible_flicker=single`。未知基线和传输/故障恢复仍允许
`0xF7`，日志模型为 `multiple`。这不是对真实观感的替代；ACPT-01 重开前仍必须完成
静态、构建和 reset-bounded 串口验证，随后用同一个 `1/13` popup 只复验这三项问题。

## Revision 60: 生图基线作为视觉通过门禁

owner 明确把“先出图，再按图实现”提升为全产品的通过规则：表情、菜单、图标、状态页和后续
屏幕 profile 的任何可见设计，都必须保存参考图、精确 prompt、源图与输出 SHA-256、被拒绝/被
替代轮次、review 结论、下一轮 prompt delta，以及源图到 PBM/CEMP/render 的对照产物。构建、
静态渲染、资源打包和刷机只能证明实现通路，不能替代美术通过；缺任一项时状态只能是
`PENDING_VISUAL_BASELINE` 或 `PENDING_OWNER_VISUAL_REVIEW`。

`tools/verify_visual_reference_evidence.py` 现在审计所有 `docs/art/iterations/*/iteration-ledger.json`，
验证基线文件和哈希、候选/拒绝资源没有被激活、候选仍挂在 owner review，以及历史拒绝图仍可追溯。
它已经并入 `verify_companion_screen_pre_acceptance_health.py`，因此没有这条证据链就不能进入任何
屏幕视觉 `PASS`。这条产品规则对应 `COMP-REQ-023` 和工作流计划
`companion-screen-product-integration`；它不批准当前 v4 菜单或 v3 入场/录音候选，二者仍待 owner
视觉决定。

## Revision 64: 先锁定四项菜单美术，再压缩快刷时长

同一 `1/13` 的 vendor-Mode-1 复验仍由 operator 选择失败，完整备注为“这次还行, 就是这种感觉,
刷新时间再短一点就会, 另外菜单是四项的, 六项实在太小, 先生图一下四项的吧”。这表示原先多次黑闪
问题已有可见改善，但不是通过：串口中的一次 `0xC7` activation 和 `1740 ms` Busy 时间只构成机器
证据，尚未达到 owner 的观感要求。旧的六项首页继续是已拒绝资源，不能为了先缩短波形而延后
四项菜单的视觉修复。

执行顺序固定如下：

1. 把已经保留的 `menu-v4-square-tiles-2026-07-13` 四项/两页候选作为本轮唯一视觉来源展示给
   owner，等待明确视觉决定；未通过则把完整差异写回 ledger 后重生图，不在 C/PBM 中自由设计。
2. owner 通过后，按冻结方格几何完成中英文资源、source-to-PBM/CEMP comparison、外部 Flash
   resource revision 和 WB55 刷机；再用 focused popup 同时确认“每页最多四项”和菜单进入的一次
   快刷观感。
3. 在不触碰已修复的一次 activation、wake、long-press、right-swipe 合约前，只按 Good Display
   公开 fast-profile 和面板温度条件调查 `1740 ms` 到厂家约 `1.5 s` nominal 的差距。记录真实
   BUSY 时间和温度；禁止凭猜测改 LUT、用额外刷新掩盖残影，或把未验证时长称为通过。

因此 ACPT-01 仍是当前唯一人工项，ACPT-02 至 ACPT-13 保持关闭。四项来源批准、资源对照和真实
面板观感是不同证据层，任何一层缺失均不得用另一层替代。

## Revision 65: 先识别触控，再选择第一帧

owner 继续报告产品“相当的卡顿”后，检查最新 runtime trace 发现低功耗静态 `sleepy` 页的首个
contact 会立即排队 `idle` differential，实际占用面板 BUSY `307 ms`。驱动在 BUSY 期间保存了
anchor/latest/release，因而不会丢失手势，但用户先等待一张不表达其动作的 idle 帧，再看见真正的
点击、滑动、录音或菜单效果，观感自然像是没有跟手。

此次性能修复不修改已锁定的宠物美术：首个 contact 只退出 Stop、开始 FT6336 5 ms gesture
timeline 并写一个 `visual=gesture_owned` trace。手势已分辨后，tap/stroke/double-tap/long-press
各自成为第一张可见帧；不会先同步刷新 idle，也不会为此新增程序化美术或增加任何额外的电子纸
刷新。这样保留低功耗触控唤醒和状态可观察性，同时移除前置约 307 ms 的人为阻塞。静态检查、
构建和 reset-bounded trace 必须证明该 deferred path；真实板端观感仍留在 ACPT-01，不能因日志
通过而声称“跟手”。

## Revision 66: BUSY 期间不冻结手势

此前 SSD1681 `wait_service` 在每个 5 ms tick 读取 FT6336 后只保存 anchor/latest/release，直到
当前 partial 或 maintenance waveform 结束才由主循环回放。它保证了动作不丢失，却把右滑、
双击和长按的识别时机推到面板 BUSY 之后，仍然与 owner 所说的“相当的卡顿”相冲突。

`COMP-REQ-024` 要求该服务改为在同一线程直接推进既有 gesture state machine。它只能改变
触控/菜单的逻辑状态并向 display queue 写入可合并的后续请求；不得在 wait loop 中递归调用
display task、启动第二次硬件刷新或额外设计视觉帧。这样电子纸保持其物理刷新限制，而用户的
手势时间线不再被 0.3 s 局刷暂停。构建和机器 trace 只能证明 timing path；真实 touch feel
仍由 ACPT-01 确认。

## Revision 67: 用真实计时决定传输优化

为避免把电子纸固有波形时间误判为软件卡顿，WB55 在保留 vendor-edge software SPI 的情况下增加了
分段计时。`ssd1681-latency-breakdown-20260714` 的 reset-bounded 记录显示：5,000-byte full
frame 的双平面发送为 `103 ms`，之后 `0xF7` waveform 为 `1298 ms`；2,552-byte differential
window 在 `0xFC` 前和同步基线后各发送 `53 ms`，waveform 为 `307 ms`。这说明手势卡顿先由
Revision 65/66 处理，物理刷新上限仍主要来自面板，但 transport 仍有值得回收的几十毫秒。

Good Display 对此型号公开给出的契约是 SPI 接口、fast 约 1.5 s、partial 约 0.3 s；其 STM32
示例使用同相位的软件时钟，但没有给出可直接套用的更快 LUT 或更高时钟保证。因此下一步只允许在
现有 STM32WB SPI2 的 `CPOL=low`/`first edge`、相同 2 MHz 下作 hardware-SPI A/B：不得修改
Mode-1 `0xB1`/`0x1A`/`0x91` profile、`0xC7` 单 activation、外部 Flash 资源、方向或触控代码。
硬件 SPI 必须用 reset-bounded serial 同时证明正确 frame transfer、无 timeout、全/局刷完成和实际
时间改善；任何异常立即刷回已验证的 vendor-edge 软件传输。即使时长改善，也不能声称 ACPT-01
通过，仍要等待同一 focused 人工项的真实观感。

## Revision 68: 硬件 SPI A/B 已拒绝并恢复

在相同 2 MHz、Mode 0 下，hardware-SPI A/B 的 full-frame double-plane transport 从 `103 ms` 降至
`56 ms`，但这不是可保留的优化：两次 reset-bounded 刷新都在约 `101-102 ms` 结束，SSD1681 BUSY
从未有效拉起，`complete=0`，面板结果为 transport failure。该结果保存在
`.cache/validation/companion-performance/ssd1681-hardware-spi-2mhz-20260714/`，因此不猜测为“屏幕
更快”或进入人工复验。

默认 transport 已立即恢复为 Good Display STM32 sample 同相位的 software vendor edges。任何重试
必须先取得逻辑分析/转接板原理图层面的电气解释，并独立证明全刷与局刷都能正确进入 BUSY 和完成；
否则当前可靠路径优先于几十毫秒理论传输收益。保留分段计时，以便后续在不伤害面板稳定性的前提下
调查波形和温度对 1.5 s nominal fast update 的影响。

## Revision 69: BUSY 回调只识别，不执行耗时产品动作

Revision 66 已让 FT6336 在 SSD1681 BUSY 期间继续推进手势时基，但进一步审查发现该同线程回调
仍可能沿着已识别的 double tap、菜单录音或手机重连分支直接进入录音 Flash 擦写、BLE pump 或连接
操作。这些工作不会改善当前波形，反而会拉长触控采样间隔和用户动作后的下一步响应。

本轮把 BUSY 回调收紧为“读取样本、更新 gesture/menu 状态、入队显示或入队一个运行时动作”。录音
开始/结束和 phone reconnect 由当前 display task 返回后的主循环执行，并记录入队到执行的延迟。这样
不会丢掉手势，不会递归显示，也不靠删除录音、外部 Flash 或蓝牙功能来换取速度。机器检查必须证明
四种耗时动作均经过 deferred path；WB55 真实 trace 和 ACPT-01 的实际触控观感仍是后续门禁。

## Revision 70: 静置定时后才显示低功耗表情

当前 Stop policy 的 blocker 一清空便立即调用 `Companion_Screen_EnterLowPowerIdle()`，也就是一次
日常点击、滑动或录音结束后会马上再排一张 `sleepy` differential frame。这与 owner 对“长时间不触摸
才进入低功耗”的理解不一致，而且会让刚结束的交互在约一张 0.3 s 局刷后显得滞后。

改为复用 CubeWB 已在使用的 RTC TimerServer：日常表情安静后仅 arm 一个 15 s one-shot，MCU 此时
仍可进入 Stop；超时回调只置位，由主循环请求一张静态 `sleepy` 差分帧。触控 contact 立即取消
one-shot，不重绘 idle，也不保持主循环轮询。计时参数必须留在 board policy 常量中，未来 WBA 只替换
timer adapter；静态检查、15 s Stop/timer runtime trace 和触碰取消 trace 是 ACPT-01 重开前的机器证据。

## Revision 71: 刷完静态休眠脸立即归还 Stop

15 s one-shot 的第一段真机串口证明了 timer 能从 Stop 唤醒并完成一张 `sleepy` differential
frame，但该 frame 完成后没有新的 `stop=allowed` 记录。根因不是面板继续 BUSY，而是显示任务由
Cube sequencer 执行，主循环的下一次策略复核不应成为归还 Stop 的前提。

因此显示任务在同步 SSD1681 refresh 返回后，调用 board application 的 display-complete 通知。通知只
重新计算既有 portable power policy；当它正完成静态 `sleepy` face 时，记录
`low_power_face completed=1 stop=allowed`。它不排队第二张帧、不增加 polling、也不改变触控或未批准的
四项菜单视觉资源。WB55 reset-bounded trace 必须顺序证明 arm -> Stop -> sleepy -> display complete ->
Stop；WBA 移植层仅需在各自显示任务完成点触发同一 portable policy recheck。

## 逐项验收顺序

本项目遵循 AI Workflow 的全产品异步验收规则：未收到操作者明确的“开始验收”前，
机器验证完成的项目只进入待验收清单，开发继续推进，不要求操作者守在设备旁或重复
报告物理现象；进入验收会话后再按下列顺序逐项确认。

1. 刷入 SCR-02，确认屏幕和触摸方向一致。
2. 完成 SCR-03、SCR-06 和 SCR-07，验收连续拖动、点击和菜单闭环。
3. 完成 SCR-04、SCR-12 和 SCR-13，把资源包从外部 Flash 送入播放器。
4. 完成 SCR-05，实测电子纸局刷动画能力。
5. 完成 SCR-08 和 SCR-09，逐页、逐个表情验收。
6. 完成 SCR-14 的资源-only OTA、断电恢复和保留用户数据机器证据。
7. 固化 WB55 证据后开始 SCR-11，并把同一组件契约映射到 WBA 安装器。

每项只有在代码检查、固件编译、串口证据和必要的真实屏幕确认都完成后
才标记为通过。

当前唯一聚焦人工项是 `wb55_touch_visual_acceptance`。对应的 touch visual acceptance packet
是 `docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.json` 和
`docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.md`；未收到“开始验收”
前它只作为待执行清单，不宣称硬件完成。

当前会话和后续产品功能的完整覆盖以
`docs/companion_function_acceptance_coverage.md` 为准。它把低功耗触控唤醒、双击录音、
长按菜单、日常宠物交互、菜单、刷新、音频、手机链路、资源/OTA 和 WBA 实板分别列为
独立项目；每一项必须先满足机器前提，再显示一个带总进度的中文单项验收弹窗。任何
应用内弹窗、确认、错误、权限或恢复提示也不得被“页面看起来正常”这一类泛化结论覆盖。
