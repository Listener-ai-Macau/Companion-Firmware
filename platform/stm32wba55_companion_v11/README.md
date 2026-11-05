# Companion V1.1 WBA55 板级准备

设计目标：用户提供的 `Companion V1.1 2026_09_19`，原理图 MCU **STM32WBA55CGU6**。
软件现有 CG（1 MiB，默认）与显式 CE（512 KiB）两种容量配置；构建 app/boot 均使用
`--mcu STM32WBA55CEU6` 选择 CE。统一容量合同见 `flash_geometry.json`，签名目标不同，
禁止混装。Owner 实装丝印报告 `STM32WBA55CEuB`；完整后缀与真实容量寄存器尚未读到，
软件 CEU6 配置不表示已经确认实装完整型号。FW1.1.35/UI53 的 CE 固件保留产品功能，
Opus 用 `-Os` 与 LTO 缩减体积；板端编码时限/栈水位仍需实际验证。
原始图纸/来源哈希已归档到相邻硬件仓库
`electronics/companion-v1.1-2026-09-19/`，其 README 含完整引脚表和待核实电气问题。

本目录是真实 CubeWBA HAL、Cortex-M33 启动文件和链接配置组成的**整机预开发固件**。
输出 ELF/BIN，已接入触摸/IMU/表情/菜单/宠物叫声与真实 Opus/COP1/NOR 存储。
`--with-ble` 加入 ST WBA 外设角色、单连接 GATT、配对 NVM、录音目录/分包/断链重拉与校验后删除；
签名固件 OTA、完整 UI 分区安装、备份/断电恢复/未确认回滚已接入独立 resident boot。
SSD1681 事务驱动已编译接入，默认因 PCB 缺少 RESET 控制端保持 NOT_READY。
不能把编译/主机测试结果作为新板产品验收。没有自动刷写，也不改变任何 option bytes。

## 已实现

- 有线调试口：1.8 V、115200 8N1、无流控。`?` 只读状态；完整行 `PAIR\n`（或 CRLF）在空闲时触发与设备菜单相同的两分钟配对窗口，回 `PAIR1 OPEN window_ms=120000`。这只是打开窗口，必须完成 Windows 加密配对后才能使用录音接口。忙时请求立即拒绝、回应延后到串口安全输出时；不自动延迟开启窗口，也不清除原有绑定。没有录音、擦除或修改权限的串口命令。
- SPI1 由 IMU/屏幕事务共同使用，独立 CS，前台单一所有者；IRQ 不做 I2C/SPI 或显示工作。
- SSD1681：复用旧 WB 双平面初始全刷、Mode2 局刷与跨 family 单激活 0xFF；每次 poll 最多一个有界 SPI 提交，BUSY 等待/超时不阻塞音频。全刷建立基线后才可局刷，错误或取消使基线失效。产品关闭按次数周期全刷，菜单视图/休眠边界保留明确刷新。真实复位控制端确认后调用 `comp_v11_hal_bind_panel_reset`。PCB 上 EPD_RES 只到 JP2.10，未接 MCU，所以不会发送必须靠 RESET 才能唤醒的 deep-sleep 命令。
- LSM6DSO：读 WHO_AM_I、复位超时、运行时 52 Hz ±4g/±250dps、BDU/自增、配置读回、完整样本原子发布；休眠画面且显示/音频空闲后切到 12.5 Hz 低功耗加速度计并关闭陀螺仪，继续给拿起/方向算法供样，唤醒后恢复 52 Hz 双传感器；通信或模式切换失败进入故障态，不发布半包或假称运行配置。
- 运动事件：方向稳定窗口、拿起、摇动、重复样本抑制、冷却窗口、时间戳回绕；不擅自改变录音状态。
- TCA6408：输出先于方向初始化、读回校验、各功能按掩码独立更新；写失败使影子状态失效，必须重新初始化。
- 3 V/触摸复位非阻塞上电状态机，20 ms 复位低电平和350 ms释放等待（FT6336U要求至少300 ms）。触摸初始化失败或失联后在空闲时重试，每8次失败只通过TCA P1复位触摸；不切常供电屏幕的3 V轨、不操作未连接的EPD_RES。接口侧供电、应答和实物手势仍需实际确认。
- MAX98357A：16 kHz mono PCM16 → 双声道 I2S，有限队列、异步块、音量渐变/静音、四种无语言宠物声音、故障停播；SAI1 B + GPDMA1 channel 0 已绑定实际引脚。新 runtime 默认 25% 软件增益，第一版明确无 TTS/台词。
- 双 SPH0655：SAI1 A + GPDMA1 channel 1 循环 DMA，7680 字节双半缓冲，IRQ 入队、前台按 256 字节复制，复制前后核对硬件剩余计数/代际；CIC3/DC 滤波、左右选取/混合、10 ms PCM16 帧、丢块/乱序/反压/饱和统计。失效 DMA 半缓冲不会发布半帧 PCM；RAW 字节/位序和实装麦型号仍需声学验证。
- CIC 运算使用 256 项 byte 表批量推进，与独立逐 bit 参考实现逐采样一致。SAI A MCKDIV=16：内部串行时钟约 3.072 MHz、双麦 CK1 约 1.536 MHz、96 倍抽取保持 16 kHz PCM； nominal 时钟处于 SPH0655 正常录音范围，物理时钟未测。首次 10 ms 半缓冲只预热滤波、不发 PCM。
- 播放 DMA 中断只留下完成/错误事件，前台再访问扩展口；停止仅关闭 SAI B，不重置麦克风 A 或共享时钟。
- V1 产品接口可绑定真实 IMU/speaker 后端；旧 WB 未绑定时继续报告未安装/不支持。wire 字节布局与 UUID 不变。完成提示音才增加 played_count，接收命令不等于播放完成。
- `PLAYBACK` 与 `MIC_CAPTURE` 独立电源阻塞位。TCA6408 汇聚中断 `PC13` 与低有效按键 `PB14` 已配置 EXTI；ISR 只锁存来源，前台立刻读取 TCA/IMU/触摸，不在中断里访问总线。默认候选仍使用 WFI；另有显式 opt-in 的 STOP1 工程目标，接 ST LPM、RTC 与固定音频 PLL 恢复，未声明实板唤醒或待机电流已验证。
- SPI3 复用现有 NOR 驱动读取 JEDEC/容量。UI 2 MiB、录音 8 MiB，设置与升级使用独立分区，精确边界以 `update/wba_storage_layout.h` 为准。新目录仅在整个录音区空白时初始化；旧 14 MiB 布局或非空损坏目录不自动格式化。只有录音请求后才预分配/擦除 payload，未同步录音不自动淘汰。
- LPUART1 115200 诊断、按键消抖后调用真实产品提示音接口；根据 SchDoc/PCB 隐藏元件属性确认 GDEY0154D67 家族，复用 FT6336 识别、触发模式、参数读回和触摸报告驱动，200×200 坐标边界检查。
- HSE/PLL + LSE 起振检查；CPU 98.30371 MHz + I-cache，共享音频 kernel 49.151855 MHz，SAI B MCKDIV=12，16 kHz 目标误差约 −2.95 ppm（不含晶体偏差）。播放不重配共享 PLL。
- 当前电池分压量程尚未确认，不使能外部采样；输入无效不会伪造电量。屏幕 RESET 未明确时不伪造屏幕 ready。
- `product_app` 已绑定可移植 runtime、固定帧快照 renderer/presenter、录音 service 与设置日志。生命轨 480 ms，blink/wave 独立；情绪在 episode 边界用真实硬件 RNG 按 16–28 秒目标 dwell 选择，缺少 RNG 就保持当前 family。
- codec=3 使用已有 fixed-point Opus 16 kHz mono / 16 kbps CBR / 20 ms COP1，经固定 PCM ring、分页写、CRC/SHA、journal finalize 成为可传输记录。长录存满正常收尾；HAL/DMA/队列错误或实际采集前台超过 10 ms 保留失败 partial，不报保存成功。24 KiB stack 已预留，目标执行耗时/高水位尚待板测。
- 更多产品取舍、菜单可用范围与资源 identity 边界见 `../../app/companion_pendant/runtime/README.md`。

### 新 WBA 蓝牙目标

从 pinned CubeWBA 的 WBA55 BLE_p2pServer 复用 host/LL 依赖图，以本目录 `ble/` 覆盖板级配置；
不链接 Nucleo LED/按键/温度 ADC/SCM。Peripheral Only LL、一个连接、ATT MTU 251、沿用原 UUID；
原服务表实际注册 20 项，repair 定义保留但未注册，不宣称可在手机触发重新配对。
record/privacy 请求保持 Type V1 wire，单路最多 192-byte payload；普通包 24-byte legacy header，
FINAL/ERROR 为 56-byte header，和 Type 按 flags 选取头长度的逻辑一致。写通知背压不推进 offset。
Host 请求相同录音的新 offset 即恢复拉取；不是固件主动凭空续传。多片段大 card 写当前不支持。

录音目录使用 Type wire 状态 0=待同步、1=录音中、2=已同步，不能直接发送 NOR journal 的内部枚举。
录中只发布当前 service 已成功写入 NOR、且至少包含一个完整 Opus 包的前缀，尾部可以是待下一次
补齐的半包；不增加 journal 写入次数，不把 RAM 缓冲当持久数据。一次拉取固定当时长度，
中途结束录音也不改变窗口长度或给旧窗口追加 FINAL/SHA。PCM 队列和待编程页优先，
只在空闲前台槽读取不超过 192 字节或发送通知；背压/临时忙保持 offset，断链后由 Type 按偏移重拉。
未结束录音拒绝 ACK/删除；最终目录才提供 CRC/SHA。没有采到首帧便停止时取消空录音，
不把只有 COP1 头的文件显示成已保存。失败或开麦前取消允许新 request_id 再次启动会议。

`tools/test_wba_type_recording_wire.py` 直接提取并编译 Type 当前 Rust 目录/分包解析器，
读取真实 Opus 主机测试产生的原始通知容器；检查每包 CRC、重建 COP1 字节与最终 SHA，
并用旧 56-byte 中间头作必定错位的负例。这是跨仓软件契约证据，仍非真实 BLE/麦克风验收。
配套 Type 将会议订阅/写入/状态回读放在共享 deadline 内；录音目录刷新有统一超时与
独立 1 秒取消订阅清理上限，传输错误保留原始原因，防止 WinRT 无响应使主机永远等待。

身份根 key 与 random-static 地址来自共享硬件 RNG，并在双页 NVM 持久成功后才广播。
连接时请求加密；私有属性要求加密，未加密命令/订阅不进入录音控制器。Just Works 不等于已实现用户所有权管理，
首次未绑定启动和本机菜单开放 120 秒配对窗口，窗口外拒绝未知 peer；自动重连偏好、无线开关、设备名已持久化。
首次配对/重复连接/重启保留须实板验证；远程解绑/工厂擦除不开放。
HSE trim 在 PLL 前设置，radio sleep timer 使用 LSE；RTC binary timer 仅供无线时基，不冒充已校准日历。
NVM 写入起点和 flash-manager task 在准备/采集时暂停，单轮先消费麦克风 DMA，radio 工作计入整轮 10 ms 检查。
采集时 sequencer 在外层任务返回且已用 2 ms 后让出前台；单个 ST task 的最坏执行时间仍须实测。

schema 1 删除 operation 1 需要精确 length/SHA ACK，提交 ERASING 后每轮擦一 sector，最后删除目录才报告成功。
擦写失败保留 cursor 并退避；断链继续，重启扫描 ERASING 安全重擦；正在录音时暂停。
FW1.1.34 的容量能力 bit 2 表示支持 schema 2 单条损失确认。加密的 DeletePrivacy
通道同时提供 READ/WRITE/NOTIFY：84 字节 preview 只提出最旧已结束 UNSYNCED 录音，
携带 ID、长度、SHA、目录代次、硬件随机 token、时间/时长、释放量及释放后最大连续区。
确认只接受本连接内 60 秒内逐字节一致的候选，取消、断连、并发目录变化或忙操作均不能
删除。提交 ERASING 不伪造 ACK；每轮最多回收一扇区，最终耐久移除目录后才报完成。
配套 Type 通过原生弹窗显示具体损失，并持有同一连接等完成回执；不会自动开始新录音。
设备本地具体单条候选页仍待实现；原清空页不能代替它。真实 ATT 长写/NOR 耗时、
断电和 GUI 操作未验收，C/Rust 合同使用明确模拟端口，不是实板证明。
schema 1 operation 2/3 明确拒绝；设备菜单确认清空则持久标记全部已结束记录后逐块删除。内部 flash 末尾 16 KiB 留给两页 SNVMA，24 KiB stack 不缩减；
BLE+Opus 镜像 RAM 余量很小，不能在未测 stack 高水位前当作 release。

### WBA 升级与启动

内部 flash：resident boot `0x08000000..0x08008000`，产品 app `0x08008000..0x080FC000`，其后为配对 NVM。
OTA 只更新 app 或完整 UI 分区，不覆盖 boot/NVM；旧 WB 包与本目标不可互刷。
Type 写 WUM1 签名清单，设备验证 P-256 可信公钥后回 WMA1；DOV1 数据每包最多 240 字节，使用有响应写入。
收完后校验实际暂存区 SHA，再持久提交候选。Type 此时确认的是待安装数据，不冒充已经重启成功。
boot 再验签/版本/向量，备份并校验旧镜像后才安装；应用检查存储/BLE就绪并计算实际运行镜像 SHA 后确认。
UI 还需实际挂载匹配 generation，未确认重启则回滚。watchdog 覆盖 boot 到 app，物理掉电与看门狗恢复待实板。
录音准备/采集与删除、升级互斥；录中仅允许上述受预算控制的已落盘前缀拉取。
升级与录音传输互斥，升级验证不在蓝牙事件回调中做 NOR 擦写。

## 原理图逐模块核对（2026-10-03，本轮软件收尾）

| 模块 | 实际接入代码 | 产品功能与联动 | 当前限制 |
|---|---|---|---|
| WBA55 / 晶振 / 调试 | `board_hal.c`、启动文件、`ble/` | 时钟、串口、硬件随机数、配对身份；SWD 初始安装 | 新板起振、射频、栈高水位待测 |
| TCA6408 / TPS62825 | `companion_v11_board.c`、`board_hal.c` | 共享 GPIO 掩码；屏/触摸上电复位；功放开关；PC13 中断前台分发 | 总线失败不报告 ready；STOP1 保持屏/触摸3V轨；断电深睡策略后续 |
| SSD1681 墨水屏 | `ssd1681_wba.c`、`screen_presenter_wba.c`、`product_app.c` | 200×200 原生素材、局刷/全刷、BUSY 完成才推进动画 | PCB RESET 只有 JP2.10，当前明确 NOT_READY |
| FT6336 触摸 | `companion_touch_ft6336_stm32wba.c`、runtime | 手势、菜单、视线跟随、录音入口、触摸唤醒事件 | 实际型号身份、坐标与灵敏度待板测 |
| LSM6DSO IMU | `lsm6dso.c`、motion/runtime | 拿起唤醒、摇动反应；休眠 accel-only，唤醒恢复；不自动切换录音 | 阈值、安装方向、电流待板测 |
| MAX98357A 扬声器 | speaker HAL、`speaker_playback.c`、`audio_feedback.c` | 无语言宠物叫声；开始提示后开麦，录音中静音 | 腔体音色/声压、DMA 时序待测 |
| 双 SPH0655 麦克风 | microphone HAL、PDM、recording service | DMA→PCM→Opus/COP1→NOR；故障不假报保存成功 | PDM 排列、相位、声学及 10ms 并发预算待测 |
| W25Q128 NOR | SPI NOR adapter、journal、preferences、update | 录音、断连重拉、校验后删除、资源、偏好、OTA 暂存/备份 | 真实 JEDEC/擦写时延/掉电待测；旧布局拒绝自动擦除 |
| BLE / Type | `ble_product.c`、`companion_link.c`、transfer | 加密后控制、录中前缀/保存后拉录；Type 既有转写和双模式纪要链 | 新 WBA 的真 BLE→ASR→双模式纪要全链未跑 |
| OTA | update service、`update_product.c`、resident boot | 签名/版本/哈希验证、安装确认、未确认回滚；供电未知/低电/充电故障拒绝写入和安装重启 | 开发信任锚；真实掉电/回滚仍待板 |
| BQ25170 / 电池 ADC | `wba_power_monitor.c`、ADC4 HAL、TCA P7、product/status/GATT | PG 去抖；STAT 1Hz 故障；非阻塞开门/稳定/转换/关门；有效读数与过期控制；获准曲线才显示百分比 | 实板标称100K:68K已进入配置，最坏量程与PG/STAT上拉未确认；默认未知，不伪造满电/温度 |
| PB14 按键 | EXTI latch、`wba_button.c`、product_app | 睡眠时第一整次按键只唤醒；下一次 700ms 长按录音；按住开机也不误录 | 去抖/按键优先与忙闲判断已有软件测试；STOP1 工程目标已编译接入；实际响应/电流待实板 |
| USB-C | 原理图供电连接 | 供电 | D+/D− 未连接，无 USB 数据/DFU 功能可接 |

引脚检查收据对照 ST 封装/AF 数据库及当前 PCB 的 25 个 MCU 网络；这是逻辑网络核对，
不等于铜箔 DRC/实板导通。未到板前可交付软件候选，不能声称上表限制已经解决。

构建必须显式传入 `--update-public-key <raw64 XY> --update-key-id <非零uint32>` 才开放 OTA。
不传公钥仍能构建诊断应用，但 OTA 显示不可用。`.cache` 内开发密钥只用于预开发，私钥不进入交付包。
`--firmware-version` 必须随升级递增；同版本/降级包被拒绝。
`tools/package_wba_ota.py` 从成功构建收据核对源码、BIN、版本和公钥，再生成 Type 可读的签名包。
UI 只支持 format 2 完整分区镜像；旧 CUOT delta 格式不被这版 boot 接受。

### 2026-10-04 到板前电源工作目标与完成条件

这四项是本轮工程目标与进度记录，不冒充 Grok `/goal` 或完整会议验收：

1. 电源数据链：用真实输入经过 PG 去抖、STAT 故障检测、ADC 门控与新鲜度检查，进入菜单/状态栏/GATT/OTA；拒绝不安全分压、失效读数和未经确认的电量曲线。主机故障场景和 M33 构建通过后，软件部分收口。
2. 按键与休眠联动：睡眠首次按键不录音；屏幕真正提交前、录音准备/收尾、播放、拉录、删除、OTA、配对 NVM 和未关闭 ADC 门期间禁止休眠。按键 EXTI 可独立成为就绪的唤醒源，触摸失败不妨碍按键策略。主机产品路径通过后收口到当前 WFI/外设节能层；真实 MCU STOP 另有时钟/无线/看门狗条件。
3. 到板候选：版本、原生资源、正式 Type 安装身份、签名包及测试都绑定同一源码。生成新候选后只补板上电气、时序、物理音频/BLE/显示和完整双模式纪要验收；不把主机测试登记为实板 PASS。
4. STOP1 软件准备：提供单独 opt-in 的 WBA BLE 工程目标，接好 RTC 唤醒、原子忙闲重查、固定音频时钟恢复、watchdog 与时间线。主机故障/时间回绕/1024次短睡眠、完整 M33 链接通过；默认候选保持禁用，启用资格留给实际唤醒/无线时序与电流验收。

电气配置由 `tools/wba_power_profile.py` 生成 `wba_board_power_profile.h` 与 `power-profile.json`。
默认采用Owner确认的实板100K:68K / 1.8V标称参数，`dividerVerified/referenceVerified/chargerPullupsVerified` 全为 false；标称阻值回复不等于满电、阻值公差及最低参考的量程已确认。归档PCB的68K:68K不再作为实板默认值。
`board_hal.c` 已接好 ADC4_IN4(PA5)、TCA P7 门控和最长采样时间；转换轮询不阻塞等待。
确认分压改造、ADC 参考及容差、BQ 上拉后，将构建收据内 parameters 或包内 power-profile.json 复制成自己的配置，
填实测值、明确标志及 `qualificationEvidence`，构建时加 `--power-profile <JSON>`。
只有获准且满足满电电压/最低参考/100mV 余量的分压才开门；SOC 曲线必须另有 `socCurveVerified` 和单调实测点。
有合格电池电压但没有SOC曲线时，宠物主页及菜单顶部显示一位小数电压，电源菜单保留两位小数；百分比可用时优先显示百分比及进度。ADC无效/过期后显示未知，不用内参VDDA或ST-Link参考电压冒充电池电压。主页只因0.1V显示值或有效性改变更新电压状态，电源详情仍按0.01V；睡眠不因电压事件唤醒。此显示改动B01已编译未安装，实板外部ADC仍未开放。
150K:68K 只是主机测试假设的安全改造例子，不是已批准的板上阻值。

充电芯片行为依据 [TI BQ25170 数据手册 §7.3.3](https://www.ti.com/lit/ds/symlink/bq25170.pdf)：
PG 低表示输入合格；STAT 低表示充电，高可能是结束/休眠/禁用；1Hz 闪烁为故障，两个输入都需要外部上拉。
输入连续稳定 120ms 才确认 PG，STAT 稳定 2s 才显示充电/外接电源空闲，三次约500ms半周期确认故障；
输入失败或超过100ms未采样立即回 unknown。电池每5s发起一次读取，15s后旧数无效；未知温度使用 INT16_MIN。
电量百分比和电压可以独立未知。OTA 要求合格外部电源且已判定非故障，或新鲜电压达到配置门槛且有效百分比不低于30%。
供电门控不会阻止已经运行的候选计算哈希/确认自身，也不阻止取消升级。

默认候选仍是 WFI + 1ms SysTick。新的 `--experimental-stop1` 只用于单独工程目标，不能当作已获准 release：

- 外层产品 poll 完成且低功耗画面已实际提交后才尝试；嵌套 sequencer/crypto 等待不负责整机睡眠。
- 使用 pinned CubeWBA `UTIL_LPM`，只提供 Idle/Sleep/STOP1，保持 SCM 关闭，防止无线时钟管理改掉板上共享音频 PLL；无线处于 ACTIVE、任务/IRQ待处理、KEY/TCA中断未消费时取消进入。
- 通过 ST timer server 共用 RTC Alarm A，新增单次20ms唤醒，不覆写其他无线/配对定时器。睡前确认定时器/Alarm启用，喂 resident boot 已启动的 watchdog；保留 PB14/PC13 EXTI。
- 原子重查之后才停整个 SysTick；恢复原先的 HSI/HSE/分数 PLL、CPU及SAI时钟，保留RAM保护位、恢复SRAM等待周期。工程目标的 HAL tick 用同一1024Hz RTC时间线覆盖运行与睡眠，避免每次休眠丢掉不足1ms的运行时间；余数累计，计数回绕有效，倒退或超过1s的时间间隔记为故障并禁用后续尝试，不重复叠加睡眠补时。
- 时钟等待使用RTC及有限轮询，失败不继续运行无线/音频，让 resident watchdog 恢复。串口记录实际STOP标志计数 `stop1`、补偿 `sleep_ms` 与 `sleep_err`。

实现：`low_power_target.c` + `power/wba_stop.c`，遵循 [ST STOP进入条件](https://wiki.st.com/stm32mcu/wiki/Connectivity%3ASTM32CubeWBA_Low_Power_Management)，参考 pinned SDK 的 `stm32_lpm_if.c`。该工程目标已具备完整软件路径；PLL/HSE恢复时延、无线调度裕量、看门狗与电流必须在实板核验，尤其不能以主机回放证明没有丢无线事件。默认候选继续禁用STOP1。

```powershell
python tools/build_wba_v11.py --with-ble --experimental-stop1 --firmware-version 0x0001010E --output .cache/wba-v11-prehardware/stop1-build
python tools/test_wba_stop.py
```

工程bin的身份及大小与默认候选不同，目录标记 `engineering-stop1-not-qualified`；它没有可直接套用的合并boot镜像或OTA安装清单，不是默认安装入口。软件保留 Type 校时，并实现下述带电复位时间恢复；完全断电后不能继续计时。
屏/触摸共用3V轨，当前不为了深睡关闭它而失去触摸；现有 LSM6DSO accel-only 低功耗路径保持拿起输入。

### 2026-10-04：栈观测与带电复位时间恢复（FW 1.1.16 / UI34）

- `stack_paint.S` 在 pinned ST 启动代码首次调用 SystemInit 之前、尚未使用栈时，涂满独立预留的 24KiB 主栈；保留原有 MSPLIM。链接后反汇编检查 Reset_Handler 确实调用包装入口。`memory_target.c` 只在非录音/非播放的一秒诊断窗口扫描，结合当前 MSP，记录最小未触及字节数、低于1024B的粘滞告警及底部保护字损坏。统计不是静态证明；未写过的栈帧/中断最坏组合仍需实板压力验证。
- 串口同时输出 `ram_gap`（静态区与24KiB栈之间）、`stack_total`、`stack_min_free`、`stack_low`、`stack_guard`，以及已有录音主循环的 `audio_max_ms` / `audio_deadlines`。不在采集过程中输出串口或扫描整个栈。默认链接静态余量1160B，STOP1工程984B；不能把这两个数当作“整个运行栈只剩这些字节”。编译器 `stack-usage.json` 是每函数估计，包含动态栈标记，不是完整调用链上限。
- `clock_target.c` 复用1024Hz RTC二进制计数，**不切换日历模式，不占用蓝牙的报警器或 BKP0..2**。产品独占 BKP4..15：两组 UTC日内毫秒/计数锚点、版本、CRC及最后提交字。恢复前核验时钟源、预分频、RTC模式和LSE状态；撕裂写入回退上一组有效记录，计数倒退、超过24小时未检查点、丢失时钟域均使时间未知。RTC自然回绕和跨午夜正确推进，运行中每分钟在空闲时做检查点，Type校时立刻记录；不擦写NOR/flash。
- 这是 **带电的软件/看门狗复位时间恢复**，保留当前13字节Type校时协议中的UTC日内时间，不声称保存完整日期。WBA55没有独立VBAT供电脚，本板1.8V电源消失后备份域和计时都不能保留；冷启动显示未知，等Type重新校时。
- `tools/test_wba_stack_monitor.py` 覆盖未触及/已写/仅预留栈帧、粘滞低水位与边界；`tools/test_wba_retained_clock.py` 覆盖计数/午夜回绕、每一步撕裂写入、CRC、复位、失效/倒退，并编译实际target适配器通过模拟寄存器验证不覆盖ST备份寄存器、采集期间延后检查点。实际WBA主栈峰值、10ms预算、复位保持与晶体精度仍待新板。

`test_wba_power_monitor.py` 验证输入/电量/ADC故障、时间回绕、构建参数与按键；
`test_wba_update_product_power.py` 编译实际 update_product 回调，验证电量门控、供电丢失时延后安装重启和未知电量仍能确认自身；
存储与 radio 在后一个测试中是 mock。`test_wba_product_recording_integration.py` 走实际产品主循环、录音和 Opus。

## 构建和证据

在 Companion-Firmware 目录运行：

```powershell
python tools/build_wba_v11.py --bootstrap-sdk --with-ble --output .cache/wba-v11-prehardware/ble-build
# OTA 目标另加 --update-public-key / --update-key-id；boot 使用同一公钥构建。
powershell -NoProfile -ExecutionPolicy Bypass -File tools/test_wba_speaker_host.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tools/test_wba_speaker_product_interfaces.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tools/test_wba_pdm_capture_host.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tools/test_wba_ssd1681_host.ps1
python tools/verify_wba_v11_pinmap.py
python tools/test_wba_runtime.py
python tools/test_wba_renderer.py
python tools/test_wba_recording_service.py
python tools/test_wba_product_recording_integration.py
python tools/test_wba_recording_transfer.py
python tools/test_wba_type_recording_wire.py
python tools/test_wba_companion_link.py
python tools/test_wba_ble_event_copy.py
python tools/test_wba_preferences.py
python tools/test_wba_wake_events.py
python tools/test_wba_imu_power.py
python tools/test_wba_power_target.py
python tools/test_wba_ota_gatt.py
python tools/test_wba_update_service.py
python tools/test_wba_update_manifest.py
python tools/test_wba_update_metadata.py
python tools/test_wba_boot_installer.py
python tools/test_wba_update_storage_confirm.py
powershell -NoProfile -ExecutionPolicy Bypass -File tools/test_wba_audio_feedback_host.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tools/test_wba_screen_presenter_host.ps1
python tools/export_wba_audio_preview.py
python tools/package_wba_v11_prehardware.py
```

`--bootstrap-sdk` 仅在缓存中准备 ST 官方依赖，不改现有 WB SDK。也可通过 `--sdk PATH` 指定依赖。
脚本固定 STM32CubeWBA v1.10.0 commit `e455b860ceb52aaa0332a98f1e7a10bbd7014fc9`，同时校验 HAL/CMSIS 子模块提交。
需要 Arm GNU Toolchain 与 Visual Studio C++ Build Tools。编译自有代码使用 `-Wall -Wextra -Werror`。

上面命令的产物在 `.cache/wba-v11-prehardware/ble-build/`；不传 `--with-ble` 仍可单独构建板级目标：

- `companion-v11-board-bringup.elf` / `.bin` / `.map`：BLE 产品 app 地址 `0x08008000`，需要配套 boot；不带 BLE 的独立诊断目标仍为 `0x08000000`。TrustZone disabled，不修改 option bytes。
- `result.json`：编译器/SDK/源码哈希、bin-sha256、硬件和完整链路 `NOT_RUN`。
- `native-tests.txt` / `build.log` / `size.txt`：实际主机测试输出、编译和内存证据。

主机测试覆盖上电顺序、共享 GPIO 掩码、ACK 丢失/半包/错误身份、复位超时、时间回绕、电池保护、运动判断、失效样本、后端命令与真实播放完成计数。
另有 speaker PCM/cue/流控测试、V1 wire/后端/电源测试与旧 WB GATT host 回归。
SSD1681 主机测试覆盖既有命令/像素流、窗口边界、必须观察到 BUSY 起落、超时、取消、维护与基线失效；
结果保存在 `.cache/wba-ssd1681-host/result.json`。新增主机测试与 M33 编译均通过。
旧 `verify_epaper_refresh_policy.py` 对工作区既有 WB 驱动的静态字符串匹配仍有失败；
本次没有修改该旧驱动，也没有把这项检查记为通过。实际 refresh-policy self-test、覆盖测试与表情资源包测试通过。
屏幕 scheduler/cache 的前一轮测试独立保留在 `.cache/wba-prehardware-20261003/`；候选表情资源没有替换已验收资源。

## 到板时的执行顺序

固件功能逐项的软件实现、证据和实板门禁见
[`SOFTWARE_FEATURE_MATRIX.md`](SOFTWARE_FEATURE_MATRIX.md)。

首次安装、Type OOBE 身份读回、codec=3 空中实录、主动断连续传、pulled WAV 声学检查、真实
ASR、双模式纪要和 truth 准确率的唯一整链步骤见
`factory/README.md`，入口为 factory-kit 根目录的 `Run-WBA-Board-Arrival.ps1`。WBA 在兼容的
DEVICE_STATUS 尾部报告真实 MCU UID 和已挂载 UI generation，Type 会与安装读回绑定；旧 20-byte
固件仍停在 `BLOCKED_HARDWARE_IDENTITY_BINDING`。显示、触摸和电源继续保留手工实物验收。
不得用主机麦、seed、单测或手改证据 JSON 关闭这些项。

录音美术：generation 24 从保留的 COMP774 烧录 CEMP 恢复原始麦克风（108 黑点）、
细线声波和 x2..41/y156..179 坐标。叠加采用透明白色，退出从干净底图恢复，不擦脸颊。
完整 gen21 64 帧源未找回；本版从原始关键帧重建连续运动，不能称为逐帧原版。
入场 00..03 仅一次；稳定段 04..63 随可见提交循环，失败重试不前进，表情/眨眼时钟独立。
旧 R10 的 0x26 previous -> 0x24 current -> 单次刷新 -> 0x24 current 无激活顺序继续使用；
静态麦克风不随声波重复改写。硬件到货后仍需验证残影、刷新时长和物理采集链路。

### Owner 2026-10-11 临时线性电量 B02

Owner明确先用Listener的线性策略，启用`--battery-linear-estimate`后复用raw工程采样。
仅对已确认的100k/68k、4350mV名义上限开放；P7开启前先在P7关闭状态读取工厂VREFINT，
新鲜VDDA至少1782mV（名义最大输入1761mV加20mV工作余量），同一外部转换再核对内参。
20mV是临时工程策略，并非已经确认的电阻/电芯/参考最坏公差，也不修改严格profile资格。
外部ADC超量程、无效、过期15秒均返回未知；每5秒、录音/准备/播放期间暂停并完成门控清理。
显示用2850mV=0%、4150mV=100%的四舍五入线性估算；顶部`~NN`及填充为估算百分比，
不把这条线性策略称为电芯剩余容量曲线。电源详情的既有资源字形尚跳过`~`，已记待修。
raw样本不进入可信power snapshot/BAS/OTA；PG/STAT及充电状态仍独立未知。
后续同板联合候选保留这个已授权构建选项，不能因更新录音代码静默退回采样禁用。
本次实际结果及包/source/读回证据见`docs/releases/screen/battery-estimate-b02-20261011.json`。
