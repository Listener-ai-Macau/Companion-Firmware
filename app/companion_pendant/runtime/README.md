# WBA 随身伙伴交互框架

对应 Owner 2026-10-03 的整机预开发委托，产品登记 COMP-REQ-791。
目标是「安静、有回应、随手能录的无语言小宠物」。本目录是独立的可移植协调层，
通过 `platform/stm32wba55_companion_v11/product_app` 接入新板，不替换旧 WB 已验收应用。

## 产品判断与本次落实

| 用户场景 | 决策与实现 |
|---|---|
| 日常佩戴/放桌面 | 保留已有角色与 authored 动作；IMU 拿起唤醒、摇动给反应。IMU 不控制录音。 |
| 手指互动 | 日常轻触进入原有情绪评分/过渡动作；拖动注视覆盖左下角；眨眼先完整睁开，再替换眼部画面。 |
| 角色生命感 | life 保留 480 ms authored 基拍；互动强度只控制新反应频率。硬件 RNG 在 episode 边界按 16–28 秒目标 dwell 选其它非 sleepy family，缺少 entropy 则保持当前 family。 |
| 开始录音 | 左下双击/菜单/700 ms 按键长按请求 → 准备 NOR → 两声上扬轻鸣 → 功放关闭 → 开麦；准备中可取消。 |
| 录音中 | 明确 REC 与时长；原始麦克风与细线声波像素、重建的独立 64 帧运动（入场只播一次），只有可见提交才推进；wave 不推进 life/family。普通提示音被抑制。 |
| 结束录音 | 真正关麦后才响低咕噜声；随后显示保存中，journal finalize 后才显示 SAVED。声音表示停止采集，屏幕表示保存结果。 |
| 失败/存满 | DMA/HAL/丢帧/编码或写入超预算显示失败，partial 不伪装成完成；容量不足正常停麦并收尾；未同步记录不自动覆盖。 |
| 菜单 | 复用现有 13 屏与有界导航历史；操作拒绝时回滚值；视图变化一次边界刷新，同页滚动局刷。 |
| 状态栏 | 蓝牙来自真实 setter；时间未知显示 --:--，电量未知显示 ?，WBA 不复用旧板 80% 占位值。 |

表情自身的问号、星星、ZZZ 属于 authored 饰品轨；录音音波与功能状态并不取代这条轨。
保留旧 WB 的绝对 life deadline、眨眼成对开合与可见提交语义。新 WBA 补齐旧版录音公平调度：
一次脸部/状态提交后，下一空闲显示机会先给纯音波（到期睁眼优先），失败保留音波待办，
不能让迟到的 BUSY 回执或音波推进重置 life、family 或眨眼时钟。
录音音波源窗口保持原资源坐标，合成时移至屏幕底部空白区，避免擦掉 curious/sleepy/alert 下部五官。
SSD1681 可见刷新阶段 BUSY 持续占用超过事务期限时明确失败、废弃 baseline；不会永久阻塞全部动画。
存储/清空菜单的数量与用量覆盖旧资源占位值；目录变化在前台同步，KiB 向上取整，8 MiB 用量不做 12-bit 截断。

## 扬声器先做什么

Owner 最新决策：**第一版不说话，只发宠物声音，跨语言使用**。不预设未来必须加入语音。
默认 25% 软件音量：轻触短轻鸣、开始两声上扬轻鸣、停止低咕噜、异常两声疑问式轻鸣。
发声约 140/200/240/240 ms，DMA 包含额外静音收尾；实际声压与腔体音色待新板量测。
使用整数振荡器、圆润谐波、连续滑音/颤动和渐入渐出，不占外部语音资源，也不依赖语言或网络。
主屏主动轻触才回应，至少间隔 1.5 秒；不因摇动/拿起/待机随机鸣叫。拖动只跟随注视。
自动连接/断开只更新状态栏，避免频繁重连声与录音开始/结束混淆。
安静模式/安静时段不播音，录音开始通过静默 gate 继续。
有界队列、重复合并、过期淘汰和冷却限制防止排队补播一串旧提示。

错误的具体含义由屏幕和 Type 呈现；声音只提醒用户看状态。此版无 TTS、台词或唤醒词。
`speaker_playback` 的宠物音色由新 runtime 显式启用，已有旧板调用仍保留原音色。

## 结构与所有权

- `companion_runtime`：触摸/IMU/菜单意图、异步录音 token、独立显示轨道。
- `companion_renderer`：从已有状态资源合成；已提交底图、待提交底图、临时图分离。
- `companion_resources`：只读挂载原有 CEMP + atomic generation，严格匹配 resource id。
- `audio_feedback`：录音提示音 gate 与音频反馈策略；`speaker_playback` 负责实际 PCM/DMA 队列。
- `wba_recording_service`：真实 PCM → 原 fixed-point Opus → COP1 → 原 NOR journal。
- `companion_link` / `wba_recording_transfer`：沿用 Type V1 GATT，真实连接/加密门控、目录、CRC/SHA 分包、背压与断链重拉；精确长度/SHA 确认后才能删除。
- `screen_presenter_wba`：固定帧快照、真实差分、成功 BUSY 完成后提交；只有 board actor 推进 panel poll。

新板 NOR 分区由 `update/wba_storage_layout.h` 统一定义：UI 2 MiB、录音 8 MiB，
独立双页设置、双页升级元数据、升级暂存、2 MiB UI 备份与 1 MiB 固件备份。
检测到旧 14 MiB 录音布局或损坏的非空目录时拒绝自动格式化，先导出旧记录。
录音先预留并分批擦除，保存后缩减空余 extent。15/30/60 分钟按现有 16 kbps CBR 预算；
无上限模式使用最大连续空闲区，接近区尾正常停止。最长准备等待 120 秒，期间有 pending 状态。

`companion_preferences` 双页追加日志持久化语言、音量、名称、连接策略与全部已接入的菜单策略；
旧 PWS1 只读迁移，不再写入 UI 区。先持久成功再更新界面，断电/半写保留上一有效值。
Type Settings V1 的 UTC 时分秒扩展已接入：支持分钟级时区和 12/24 时制；
时钟未知仍显示 --:--，安静时段须收到有效时间才生效。断电后重新校时，不宣称电池日历。
静音自动停默认关闭，可选语音 5 秒/会议 15 秒；先有连续 500 ms 足够能量才计静音，
初始安静或单次碰撞不结束录音。这是能量判断，非语音识别，阈值待实板调校。
清空录音须设备菜单二次确认，持久标记后逐扇区擦除；包含未同步记录。
蓝牙重连、开启配对、改名、关闭无线与恢复设置已绑定；远程整机擦除/解绑仍拒绝。

## 尚未达到的边界

这是 prehardware 软件包，**不是到板即用的完整产品 release**。

1. 已确认 PCB 的 EPD_RES 只有 JP2.10，没有可绑定控制端；驱动保持 NOT_READY，不能猜 GPIO。
2. WBA 使用独立 generation 30 profile（`COMPANION_WBA_RESOURCE_PROFILE=1`），由保留的注册部件重新生成。
   `tools/build_wba_product_resources.py` 生成完整 2MiB UI bank 和匹配 CEMP catalog；固件严格匹配 identity。
   旧 WB generation 21 `B0789203...85E202` 默认配置保持不变，新 WBA 不宣称复原了缺失的旧资源包。
3. `--with-ble` 已链接 pinned ST 外设角色、单连接 GATT、随机身份/配对 NVM、录音拉取/背压/按偏移续传。
   内部 flash 最后 16 KiB 留给双页 NVM；写操作在采集时暂停。Just Works 加密/绑定及 Windows 真连接尚待板测。
   删除 operation 1 先持久 ERASING，再逐 sector 擦除，最终目录提交后才成功回声；掉电后续擦，采集中暂停。
   远程清空/解绑 operation 2/3 继续拒绝；配对窗口只由首次启动或本机菜单打开，已绑定重连沿用原密钥。
   WUM1 P-256 签名、DOV1 暂存/读回校验、resident boot 安装、启动确认与回滚已接入；
   UI 升级使用完整分区镜像，挂载匹配的新 generation 后才确认。未配置公钥时 OTA 不可用。
   当前开发密钥只用于预开发；实板签名验算、掉电恢复与升级回滚尚待验证。
4. 16 kHz PDM 位序、双麦极性、音量/噪声、Opus/NOR/渲染并发 10 ms 预算、24 KiB stack 高水位均需实板。
   超时统计覆盖整个采集前台周期；不能以桌面编码速度替代 MCU 时限。
5. 自动休眠已联动 IMU 加速度计 12.5 Hz 低功耗、关闭陀螺仪，唤醒恢复运行配置；PB14 按键与 PC13 汇聚中断已接入。默认 MCU 仍用 WFI；单独 STOP1 工程目标接好 RTC、LPM 与音频时钟恢复，尚未验证实板唤醒/无线连续性/待机电流。
6. 电池 ADC 仍因 68k:68k 分压与 1.8 V VDDA 问题禁用，充电输入上拉待确认。

## 验证

`tools/test_wba_runtime.py` 覆盖用户操作、错误/取消/过期回调、独立时钟与计时回绕；
`tools/test_wba_renderer.py` 用合成掩码验证像素所有权，不作美术验收；
`tools/test_wba_screen_presenter_host.ps1` / `test_wba_ssd1681_host.ps1` 验证提交/事务/失败与 Mode2 0xFF；
`tools/test_wba_recording_service.py` 使用实际 fixed-point Opus 导出 COP1，并独立解码/核对 SHA。
`tools/test_wba_product_recording_integration.py` 将真实 product_app、runtime、录音 service 和 Opus 连起来，
用假 HAL/NOR 覆盖长按到保存、采集故障后重试、目录满时保留旧记录；测试中录音期间播放块数为 0。
其输入是合成 PCM，不能替代实板麦克风、物理 NOR 或会议端到端证据。
`tools/test_wba_recording_transfer.py` / `test_wba_companion_link.py` 验证拉录、断链重拉、背压、权限门控、远端录音 token 上限、精确 ACK 与掉电/失败续擦。
`tools/test_wba_ble_event_copy.py` 验证 HCI 分段事件拼接、最大包与畸形长度拒绝。
`tools/test_wba_preferences.py` 验证设置写断、跨页恢复、时钟与静音结束策略；
`tools/test_wba_ota_gatt.py` 验证加密门控、有限队列、签名接收回执与连接重置。
`tools/test_wba_update_service.py` / `test_wba_boot_installer.py` / `test_wba_update_metadata.py`
及 `test_wba_update_storage_confirm.py` 分别验证传输、安装/回滚、元数据掉电、实际运行镜像确认。
`tools/build_wba_v11.py --with-ble --output .cache/wba-v11-prehardware/ble-build` 生成 Cortex-M33 ELF/BIN、map、源码与二进制哈希。

## 产品完成条件与继续顺序

2026-10-03 第二轮软件纵向修整：

- WBA 长按四阶段移至状态栏，保留当前表情；闭眼期间的状态/音波提交携带闭合状态，life/触摸表情等重新睁眼后再推进。保持旧 WB 的素材与节奏合同。
- 准备、录音、保存、已保存、同步、错误、不可用改为统一 11×11 非语言图标，时间/蓝牙/电量保留位置。补齐 5×7 字库中的 `?`，未知电量不再因缺字显示为空电池。
- 真实素材复现了 curious 等 family 闭眼时留下半截黑眼睛的问题：原先固定 calm 矩形不能覆盖不同眼形。新 WBA 先有界识别当前眼睛部件，以注册闭眼素材对齐当前眼睛锚点；眉、嘴、饰件保留，睁眼准确恢复提交前的表情。该变更不影响旧 WB 渲染器。
- `tools/render_wba_visual_review.py` 直接编译生产 C 合成器生成 35 张预览，使用保留的 V45 原始像素；`.cache/wba-visual-review/index.html` 可查看十家族、四阶段长按及眨眼/时钟合成，`blink-review.png` 对照十种睁眼/闭眼效果。该预览不替换 generation 21，也不证明缺失资源已经恢复。`tools/check_wba_visual_review.mjs` 检查桌面/窄屏与交互。
- Type 的 meeting_control 12B 协议现已路由至同一录音 runtime；状态必须等真实 capture/finalized journal，重试校验 request_id 与 START 参数，通知失败会重试。相关主机旅程覆盖实际协议、幂等、错误及保存结果。
- Type 保留未决 START 的 session/device/max_seconds，使丢回执或断链后的重试不会新建另一录音请求。连接时读取真实 DEVICE_STATUS、IMU_STATUS、SPEAKER_STATUS；未知身份清除旧缓存，只有测得的扬声器能力才放开短叫声，旧 WB 未装配状态继续禁用。当前进程内重试不冒充跨应用重启恢复；每个可选状态读取最多 2.5 秒，初始空状态最多重读一次。

预开发目标包含交互、声音、真实编码存储和手机传输软件闭环，当前证据只到主机测试与 WBA 链接。
已将配对入口、设置/时钟同步、资源安装与固件 OTA 接回新板目标；
MCU STOP1 软件已提供显式工程构建；实板测量后才决定正式启用及唤醒/音频连续性调校，远程工厂擦除不作为第一版功能。
资源已通过真实 loader 接入；RESET 仍待硬件确认，实板还要逐页检查主屏、状态栏、13 屏菜单和所有 authored 过渡。
硬件阶段测量音色、触摸/IMU 阈值、共享总线与录音时限、RAM/stack 高水位，最后运行下述完整会议验收。

最终验收仍须新板真采集 → codec=3 保存 → 断链续传 → Type 收齐 → 真 ASR → offline+online
纪要与准确率 → 全链 acceptance，再按根 AGENTS 弹阻塞 owner 窗；本次不制造物理 PASS。

### 2026-10-04：按键唤醒与休眠联动已接入

Owner 2026-10-03 明确要求先完成当前模块核对和会议修复，再研究低功耗体验。
优先评估原理图 PB14 实体按键唤醒，区分浅睡与深睡；后续一起确定进入时机、按键消抖、
唤醒响应、是否保留蓝牙连接、录音/传输/OTA 的阻塞条件，以及触摸/拿起是否只在浅睡有效。
已实现：睡眠首次整次按键只唤醒，下一次700ms长按才进入录音状态机；开机时已按住也不误录。
休眠门同时观察实际屏幕提交、准备/录制/收尾、播放、按键/触摸、ADC、BLE拉录、删除、OTA和配对NVM。
实体按键 EXTI 可独立提供唤醒就绪。当前实际节能仍为 WFI/IMU accel-only，MCU STOP 未开启。
充电与电池驱动现在已经接入真实主循环/状态栏/菜单/GATT/OTA；原图不安全分压和未确认上拉默认保持未知。
具体构建电气配置与三项完成条件见 `platform/stm32wba55_companion_v11/README.md`。

## 实际 C 调度预览

`python tools/wba_runtime_preview.py --port 8876` 构建并运行生产 runtime、资源挂载与合成器，
浏览器 `/art/` 只显示已提交的 200×200 1bpp 帧，不自行编排眨眼、生命动作或波形。
触摸输入经过生产手势识别；长按、滚动、返回、设置、录音状态与失败重试经过实际 C 路径。
面板耗时、IMU、蓝牙事件和录音后端在此明确模拟，不采音、不证明真板刷新或外设可用。
`tools/test_wba_runtime_preview.py` 验证十家族、独立时钟、长按/子菜单/返回、
录音状态、慢屏提交失败恢复和休眠唤醒，输出源码、资源和原始帧哈希。

界面资源 29 保留界面资源 28 的全部非菜单像素（表情、眨眼、生活动作、饰品、录音声波）。
界面资源 31 仅更新“关于”页的固件 1.1.13 / 界面 31 文本；其余 9459 个状态与资源 29 逐状态像素哈希相同。
状态栏仅在原16px范围内统一时钟/蓝牙/电池笔画，未知电量以问号显示，禁止虚构电量；合格外部电源或故障使用固定小图标，不播放1Hz闪烁。
WBA 界面资源 29 的菜单首页为两页 2×2 图标入口，上下滑动每次切换整页，返回子页时保留所在页；格间留白和底部分页标记不触发入口，左上返回回到宠物首页。子页继续使用 40px 点击行。菜单中文正文使用 SimSun 内嵌点阵，英文使用 Segoe UI，动态值为 12px 原生字形；菜单入口使用 12px 原生字形并按可见字形居中；八个图标以 28px 为排版框，主要笔画统一为 2px，视觉尺寸收敛到约 24px，爪印使用空心掌垫以平衡黑色面积。分页使用短横线和小圆点。旧 WB 列表和宠物首页像素不变。
录音菜单显示实际准备/录音/保存/同步状态，电量只显示已测得数据，存储数字支持完整8MiB范围。
