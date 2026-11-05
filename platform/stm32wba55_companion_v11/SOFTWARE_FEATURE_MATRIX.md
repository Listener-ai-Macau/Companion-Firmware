# Companion V1.1 WBA55 到板前功能矩阵

本表对应 FW1.1.34 / UI52 候选。`软件通过`只表示实际源码已编译并通过对应主机或目标构建检查；
它不替代 WBA55 实板、扬声器空中拾取、断连续传或 Owner 验收。

本轮接通 Type 原生具体录音损失确认与固件单条回收，区别于已有正常同步 ACK；保留真实容量、完整时长预检、已消费自动恢复、三语菜单反馈与认可的 UI48 方向。UI51→UI52 仅关于身份变化。当前 Rust 259 passed / 13 ignored，另两项实际 C→Rust 合同显式通过；当前受影响的 journal/link/product/GATT/OTA、菜单/runtime、资源和 UART 检查已重跑，未改的历史专项不冒充本轮验证。Flash仍V1固定布局，设备本地具体单条候选页、V2共享池、连续分段与WRITING掉电保全仍未实现。

| 本轮新增 | 软件路径与检查 | 剩余门禁 |
|---|---|---|
| 具体未同步录音的损失确认 | 加密 DeletePrivacy READ/WRITE/NOTIFY，schema 2 / 84B 候选绑定最旧已结束 UNSYNCED 的 ID/长度/SHA/目录代次/硬件随机 token 与本连接 60 秒；Type 后端持有证明，原生窗显示时间/时长/释放量/不可撤销风险。取消、过期、断连、并发变化、重复确认及各目录写擦中断有模拟检查。提交 ERASING 不伪造 ACK，最后物理擦完并耐久移除目录才回完成，不自动开录 | Type 与 FW 当前源码匹配并正式配包；设备本地具体候选页待补。安装 GUI 操作、实际 ATT 长写/通知回读、NOR 时延/掉电和全链 NOT_RUN |
| 真实容量与录前拒绝 | 84B DeviceStatus保留原36B身份，报告实际8MiB区域/连续区/三类占用与数量；C journal/product/GATT、C产出→实际Type Rust解析验证。固定时长不足或7个槽满时不缩短、不覆盖，不开麦、不预留/改目录、不启动开录提示音；保留错误宠物音反馈。Type查询未知不造数，开始前再读、固件最终重检 | 设备本地不足空间仍走既有录音失败提示，专门容量页/精确损失确认仍待完善；真实NOR、BLE及完整链NOT_RUN |
| Type时长和设备空间 | 离线不再静默压成43分钟；本次远程时长独立于本地15/30/60/不限偏好，在线>43分钟明确拒绝、收尾预留120秒也检查空间；倒计时使用本次接受值。Type容量标明上次读取，缺失不假设14MiB；原音持久收据后才向设备精确回收 | 软件模拟与状态检查；旧固件没有完整容量能力，实际安装GUI、实板时长/收尾与链路仍NOT_RUN |

| 功能 | 当前软件入口 | 到板前证据 | 真实状态与剩余门禁 |
|---|---|---|---|
| 首页、表情、眨眼、独立饰品时钟、四格菜单、录音声波 | `runtime/companion_renderer.c`、`epaper/motion_coordinator.c`、`epaper/screen_menu.c`、generation 52 UI bank | 12968 资源通过生产解码/渲染；UI51→UI52 仅 51 个关于身份资源状态变化，5969 非菜单状态不变。保留的 UI49 证据中 13 首页提交帧与 93 非关于菜单目录帧保持 UI48 原生像素一致；目录预览 99 帧中 81 为 normal、18 为明确标记的素材反馈 | 保留 UI48 原生字形与无框双列、四项同屏/一次松手翻整页；实际墨水屏刷新、残影与 BUSY 时序 `NOT_RUN`。PCB 没有已确认的 EPD RESET MCU 控制端点，因此默认产品构建仍禁用 panel initialization，这是显示实物验收的明确阻塞。 |
| 触摸、菜单导航与三语偏好 | `touch/browser_interaction_runtime.c`、`touch/ft6336.c`、`epaper/screen_menu.c`、`runtime/companion_runtime.c` | 保留全部 64 行菜单、13 屏与 EN/简中/繁中；每语 18 默认子页位置。FW1.1.32 目标编译通过；显示未完成/失败、重复动作、跨帧接触及失败重试均有生产 C 主机检查 | 新页显示成功前不接受其坐标操作；失败的菜单显示使可见状态失效，成功重试后恢复。FT6336 坐标、手势、唤醒和实物触摸 `NOT_RUN`。旧 ack/processing/result 素材不强刷三帧，真实结果使用下项的动态文字覆盖。 |
| 菜单操作的等待、完成、失败与重试 | `runtime/companion_runtime.c`、`runtime/companion_renderer.c`、`product_app.c`、`ble/ble_product.c` | `.cache/wba-menu-feedback-host/result.json` 为生产 C / 挂载资源 / 显式模拟后端的三语主机证据；陈旧 token、重复动作、保存失败回退、擦除失败重试、配对超时、慢屏失败和跨帧触摸检查通过，文字仅占反馈条 | 实际目标端清空等所有 journal reclaim 完成；配对等新的加密连接事件，120 秒超时；同步设置等持久化读回校验。短操作只显示最终结果，未变化的进度不周期重刷。录音设置失败不会冒充“录音失败”。物理 NOR、BLE 安全连接/持久化、实屏可读性和全链仍 `NOT_RUN`。 |
| IMU 拿起/活动 | `imu/lsm6dso.c`、`imu/imu_service.c`、`power/motion_wake.c` | FW1.1.20 WBA55 目标构建通过；既有 `.cache/host-tests/wba-imu-power/result.json` | 软件通过；实板 I2C、方向、阈值、功耗与唤醒 `NOT_RUN`。 |
| 宠物提示音 | `playback/audio_feedback.c`、`playback/speaker_playback.c` | FW1.1.20 目标构建通过；既有 `.cache/wba-audio-feedback-host/result.json` | 软件路径只含非语音宠物提示音；实际功放、扬声器音量和失真 `NOT_RUN`。 |
| 时钟与复位恢复 | `clock_target.c`、`runtime/companion_clock.c` | FW1.1.20 目标构建通过；既有 `.cache/host-tests/wba-retained-clock/result.json` | 软件支持 Type 校时及带电复位后的 RTC/BKP 恢复；整机断电后必须重新校时。晶体精度、复位保持与长期漂移 `NOT_RUN`。 |
| 板端录音 codec=3 | `microphone_hal.c`、`recording/wba_recording_service.c`、`recording/companion_opus16_rt.c` | FW1.1.20 链接真实 Opus/COP1/NOR 路径；构建 receipt 标记 `product_codec3_recording_linked=true`；去掉重复的 400-byte Opus 包并收紧 service packet 后 BSS 减少 512 bytes，24 KiB 预留栈不变 | 软件通过；实麦 PDM 时钟、声道、非静音、Opus 时限及录音/无线并发 `NOT_RUN`。 |
| 板载存储与 Type 拉录 | `recording/companion_recording_journal.c`、`recording/wba_recording_transfer.c`、`runtime/companion_link.c`、Type `backend/ble_bridge.rs` | 新的链接主机故障测试覆盖 ACKED 掉电/目录半写、失败 ACK 保护、最旧已消费逐扇区恢复、拉取/录音/OTA 避让、精确重复请求、完成通知背压及零 tick 回绕；历史 journal 全 catalog 字节短写/局部擦除等记录保留 | 已消费条目在空闲时自动恢复回收；先耐久 ERASING，再擦除和移除，未经 ACK 的 UNSYNCED/WRITING 保持。满盘仍明确拒绝；容量预检和最旧未同步覆盖确认未实现。真实 NOR 掉电、断连续传与隐私擦除 `NOT_RUN`。 |
| 长会议与无缝分段（未实现） | 当前 `companion_runtime.c` 到时调用 stop；`wba_recording_service.c` 先关麦，再 drain/flush/finalize，下一次 prepare 还会逐扇区擦除；wire 只暴露独立 `recording_id`，`companion_link.c` 的 `segment_count` 仍为 1 | 当前 recording 分区是 `0x800000`（8 MiB），不是旧 prehardware 14 MiB。扣除两个 4 KiB catalog 后为 8,380,416 bytes；16 kHz/20 ms/16 kbps CBR 每帧 40-byte Opus + 2-byte COP1 长度，稳态 2,100 bytes/s，理论约 66.51 分钟。含 4 KiB 安全余量并对齐后，10/15/30/60 分钟 extent 分别为 1,265,664 / 1,896,448 / 3,784,704 / 7,565,312 bytes；目录最多 7 项，分区最多同时容纳 6/4/2/1 个完整 extent | 当前明确没有无缝自动分段；停止后再启动不能冒充无缝。兼容 V2 最小契约需追加 `meeting_session_id`、`segment_index`、`continuation/expected_count`，开录前耐久预留并预擦下一小段，双 segment/encoder 上下文在麦克风不停时切换 PCM，旧段后台 finalize；ACK/reclaim 仍逐段 exact，Type 按 session/index 合并并报告缺段。预擦或 commit 失败必须保留可恢复数据并明确 `STORAGE_FULL`/segment gap。建议 10–15 分钟小段；超过板端约 66 分钟还需要 Type 边录边拉取并 exact reclaim。该 V2 尚未实现、未仿真、未实板验证。 |
| BLE、身份与自动恢复 | `ble/ble_product.c`、`gatt/companion_gatt_stm32wb.h`；Type `backend/ble_bridge.rs`、`src/lib.rs` | DEVICE_STATUS 保留 20-byte 前缀并追加 12-byte HAL UID 与 4-byte 已挂载 UI generation；实际 WBA GATT 注册表测试确认 Repair Control 0x4003 已注册 | 软件通过；UID/UI49 必须到板读取并与首次安装 receipt 绑定。配对、NVM、掉电、射频断线与探测功耗 `NOT_RUN`；手动断开保持不自动重连。 |
| 有界诊断日志 | `diag_log/diag_log_export.c`、`ble/ble_product.c`、`ble/app_ble.c`、`ble/update_product.c` | 加密 WRITE+NOTIFY 单特征；12-byte 请求、20-byte 状态头、最多 8 条 28-byte 事件；CRC/游标/截断、BUSY/INVALID 及生命周期事件定向通过 | 仅导出 RAM 环形缓冲区最近事件，复位会清空；忙态不抢占录音、传输、播放、OTA 或存储工作。Type 可把拉取结果写入本地主机诊断日志，但不代表完整设备历史或硬件通过。 |
| 签名 OTA | `update/*`、`update_storage.c`、resident boot | FW1.1.20/UI38 使用同一 DEV_ONLY 信任锚；metadata A/B 全记录短写、局部擦除和丢失 commit ACK，app/UI backup/install/restore 六个重启阶段、回滚、antirollback、boot/NVM 保护定向通过 | 软件包与签名契约通过后仍只代表离线构建；真实 BLE 传输、重启确认、中断安装、回滚与供电门控 `NOT_RUN`。DEV_ONLY 密钥不能作为量产信任根。 |
| 六针只读诊断 | `diagnostic_console.c`、`board_hal.c`、`main.c`；JP6 `V/C/G/D/RX/TX` | 单字节 `?` 请求；同 `seq` 的 BEGIN、7 个数据 section、END；UID 使用 MCU 原始小端字节顺序；任一 UART TX 失败不发 END；BLE 前先发 `BOOT1 phase=pre_ble`，主线程 BLE 初始化 fatal 尝试发 `BOOT1 FATAL`；host fault-injection 验证截断/重复/字段错误均 fail closed | UART 为已装固件后的 1.8 V 115200 8N1 诊断，不是 ROM 首刷接口。输出会避让录音、播放、显示、存储/传输/OTA/NVM 和电池采样；约 100 ms 的整帧串口占用尚未实板验证。UART 初始化前、UART 自身失效、IRQ/硬 fault 内无法安全发送的崩溃仍需 SWD；这些输出不构成实时性或硬件通过。 |
| 电源与低功耗 | `power/power_monitor.c`、`low_power_target.c`、`power/wba_stop.c` | 默认候选为 WFI，STOP1 不进入；电源监控与门控有主机测试 | 电池分压、参考电压、充电 PG/STAT 上拉尚未获实板确认，ADC 电量保持禁用/未知；STOP1 仍是单独工程目标。实测电流与热/欠压恢复 `NOT_RUN`。 |
| 异常恢复 | resident watchdog、录音 journal、OTA metadata/boot installer、Type 持久化恢复和 60 秒设备健康探测 | FW/boot 构建通过；factory fault-injection 与 Type 恢复测试可复现 | 软件故障注入通过；真实掉电、看门狗、部分 NOR 写入、会议服务断流和整机恢复 `NOT_RUN`。缓存 `recording=true` 不阻止只读状态探测；前台会议和在线 ASR 会让出 BLE 访问。 |

首次安装、身份读回、板端实录、主动断连、Type 拉录、真实 ASR、offlineStore/onlineLive 双模式纪要、
truth 准确率和手工屏幕/触摸/电源检查的执行顺序见 `factory/README.md`。完整链未在实板运行，
`hardwareAcceptance` 与 `fullChainAcceptance` 必须保持 `NOT_RUN`。
