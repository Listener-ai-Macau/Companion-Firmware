# Companion Dev-Board Physical Checklist

This checklist is for the current NUCLEO-WB55RG development-board phase. It is
not a pendant-PCB release checklist.

## Before The Run

- Use the clean canonical checkout only for normal workflow commands.
- Keep the current product stack in the scratch worktree:
  `C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware-devboard-oai1`.
- If collecting physical evidence, hold the workflow hardware lock for the
  short flash, serial, BLE, or operator-prompt window only.
- The development-board record button is the NUCLEO-WB55RG `SW3/B3` user
  button on `PD1`. Do not use RESET, ST-LINK reset, BOOT0, or a host keyboard.
- If no real e-paper panel is connected, record `N/A`. PBM fallback renders are
  automated display-contract evidence, not real panel evidence.
- Battery, charger, and fuel-gauge validation is
  `BLOCKED_ON_PRODUCT_HARDWARE` during the current dev-board phase. The
  NUCLEO-WB55RG bench has no Companion battery/charge circuit, so do not block
  e-paper bring-up on battery evidence; record battery and charge rows as
  `N/A` with this blocker.

## 电子纸接线

### 当前硬件：ESP32-FTS02

当前屏幕为 `GDEY0154D67-T03`，通过 Good Display `ESP32-FTS02` 转接板连接。
它不是普通的 8 针 SPI 转接板：屏幕 24 针 FPC 插入转接板 `P5`，1.54 英寸触摸
FPC 插入 `P6`。开发板从转接板背面的树莓派兼容 `P1` 40 针接口接入。

- FTS02 的 `P3` 电子纸电阻选择必须拨到 `2.2`。这块屏使用 Solomon `SSD1681`
  控制器；`0.47` 是 UltraChip 控制器的档位，会导致屏幕无法正常刷新。
- `GDEY0154D67-T03` 随附的 Good Display STM32 示例按高电平忙、低电平就绪处理
  `BUSY`。规格书说明文字与命令表/厂家示例存在矛盾，本项目以匹配型号的厂家示例
  和实板状态为准：上电空闲时应为低，刷新期间应拉高。
  `P9 T4` 必须接 `CN7-3` / `PC5`；它不能与 `P9 T5` / `RES`（`CN10-24` /
  `PB1`）互换。
- 转接板逻辑电源必须是 `3.3V`。不要把 NUCLEO 的 `5V` 接到 FTS02 的逻辑电源或
  任意信号线；首次点屏也不需要接前光电源。
- 首次黑屏诊断不需要触摸、前光、microSD 或 `MISO`；建议接上 `BUSY`，这样驱动
  会等待屏幕完成刷新，不依赖固定延时。

#### FTS02 实物定位

先断开 NUCLEO 的 USB 供电。`P3` 是转接板顶边、`ESP32-FTS02` 丝印右侧的小型
横向拨码；左侧丝印为 `0.47`，右侧丝印为 `2.2`。本屏必须将拨码推到底到右侧
`2.2` 后再恢复供电。

不要调整底边的 `P2`、`P4` 或 `SS1`，它们属于前光电源/电压选择，不是电子纸
控制器选择。`P5` 是 24 针电子纸 FPC，`P6` 是触摸 FPC；除非后续明确检查排线，
也不要拔插它们。

若需要重插 `P5`，先断开 USB 供电。按厂家手册将电子纸的显示面朝上，把橙色
24 针 FPC 平直插到底，再将 P5 的黑色锁扣完全压下。不要把 P5 的屏幕 FPC 插到
触摸 `P6` 或前光接口。

当前显示与触摸方向验收基准：从使用者正面看，屏幕排线位于下方；菜单箭头指向
物理右侧，触摸上滑/下滑方向已由操作者确认正确。后续固件不得仅凭原始坐标日志
再次翻转 X/Y，必须按这一实物姿态做真人复验。

若 P5 重插后仍然无刷新且现场有万用表，在一次完整刷新期间以 `GND1` 为公共端，
只测板面中上部标有 `PREVGH1` 和 `PREVGL1` 的两个圆形测试点是否出现正/负升压。
它们是 FTS02 的电子纸升压测试点；无升压时检查 P3、P5 和控制信号，有升压而仍无
图像时再检查 P5/FPC 的接触与面板本体。

#### P0 更换显示 FPC 后的 White/Black 复测记录

历史 White 失败发生在旧显示 FPC 已断的状态，不能再被当作当前 FTS02 或面板故障诊断。
本次 White 只接受版本化的 `replacement-display-FPC` 证据：当前 FPC 已更换、照片所见
面板标记为 `0154BN-D67-D2 N524110506`，且正常动态表情当前可见。它仅授权现有官方
`0x24` 单 5000-byte plane、`0x22=0xF7`、`0x20`、BUSY 的 White 复测；不授权
`0xC7`/一秒 LUT、生产刷新策略、猜测波形或直接进入 Black。

White 通过机器日志和中文可见帧复核后，仍须在一个新的、复位边界清晰的 White rail
session 中，以 `GND1` 为公共端测得 `PREVGH1` 为正、`PREVGL1` 为负。通过的 rail
artifact 必须由 `tools/verify_wb55_official_full_rail_measurement.py` 生成且状态为
`PASS_MACHINE_AND_RAILS_ESTABLISHED_WHITE`。只有传入该 artifact，runner 才会允许
`-Execute -Stage Black`。这不是通用 LUT、重刷或日常表情的替代路径。

### 本次接线总表

当前实际接好下列 `11` 根线。前 `8` 根用于电子纸，最后 `3` 根用于触摸和中断。
`P10 A3` 是可选的触摸硬复位线，当前不接以保留 `PC10`。首次刷黑屏时触摸线不会
影响电子纸；不要接 `5V`、`MISO`、`SPI_SS` 或 P8 上的其它针脚。

操作者已确认 `P10 A0/TP_INT -> CN10-33/PC6` 已接入；`P10 A3/TP_RST` 未接。
`P10 A0/TP_INT` 是真正触控中断/Stop 唤醒的必需线；`P10 A3/TP_RST` 只用于硬件
异常恢复，GPIO 紧张时可不接。固件已允许把 `TP_INT` 作为候选 Stop 唤醒源，但仍须
通过真实 IRQ 计数、双击录音和电流验收，不能只凭接线或 I2C 配置宣称通过。

| FTS02 丝印 | NUCLEO 接口-编号 | GPIO | 功能 |
|---|---|---|---|
| `P8 3.3V` | `CN7-12` | `3V3 / IOREF` | 转接板逻辑供电 |
| `P8 GND` | `CN7-19` | `GND` | 共地 |
| `P8 MOSI` | `CN7-30` | `PC1` | 电子纸 `MOSI` |
| `P8 SCK` | `CN10-19` | `PA9` | 电子纸 `SCK` |
| `P9 T7` | `CN10-13` | `PA6` | 电子纸 `CS` |
| `P9 T6` | `CN10-22` | `PB0` | 电子纸 `D/C` |
| `P9 T5` | `CN10-24` | `PB1` | 电子纸 `RESET` |
| `P9 T4` | `CN7-3` | `PC5` | 电子纸 `BUSY` |
| `P10 A4` | `CN7-28` | `PC0` | 触摸 `SCL` |
| `P10 A5` | `CN7-1` | `PB11` | 触摸 `SDA` |
| `P10 A0` | `CN10-33` | `PC6` | 触摸 `INT` / Stop 唤醒 |
| `P10 A3`（可选，不接） | `CN10-29` | `PC10` | 触摸硬复位 |

上表前 `11` 行是当前实接；最后一行不接。若后续必须更换供电位置，`3.3V`
也可改接 `CN6-4` 或 `CN7-16`，GND 也可改接 `CN6-6`、`CN6-7` 或
`CN7-8`，但一次只使用一个明确的 3.3 V 供电点并保持共地，绝不能改接 `5V`。

### 开发板 GPIO 保留

以下 GPIO 已为这块 FTS02 屏幕和触摸保留，后续接 IMU、扬声器或其它外设时不再
复用：

| 用途 | 已保留 GPIO |
|---|---|
| 电子纸 SPI 与控制 | `PA9`、`PC1`、`PA6`、`PB0`、`PB1`、`PC5` |
| 触摸 I2C 与中断 | `PC0`、`PB11`、`PC6` |
| 触摸硬复位（可选） | `PC10`；当前未初始化，可供后续外设使用 |

开发板的 `Companion_Nucleo_WB55RG.ioc` 已把 `PA6`、`PB0`、`PB1`、`PC5`
分别标为 `EPAPER_CS`、`EPAPER_DC`、`EPAPER_RESET`、`EPAPER_BUSY`，并把
`PC6` 标为 `TOUCH_INT`，以免 CubeMX 重新生成配置时误读或丢失这些线。

### 外部 Flash 接线（独立硬件 SPI1）

当前 NUCLEO 固件使用普通 `1-1-1 SPI NOR`。外部 Flash 独占硬件 `SPI1`，
电子纸继续独占硬件 `SPI2`；两者不会因录音或刷屏互相占用。先断开 NUCLEO USB，
再按下表接线。Flash 只能使用 `3.3V`，不能接 `5V`。

| 外部 Flash 丝印 | NUCLEO 接口-编号 | GPIO | 功能 |
|---|---|---|---|
| `VCC / 3.3V` | `CN7-16` | `3V3` | 模块供电 |
| `GND` | `CN10-9` | `GND` | 共地 |
| `CS / NSS / SS` | `CN10-35` | `PA2` | 软件片选 |
| `CLK / SCK` | `CN7-32` | `PA1` | `SPI1_SCK` |
| `DI / MOSI / IO0` | `CN10-15` | `PA7` | `SPI1_MOSI` |
| `DO / MISO / IO1` | `CN10-4` | `PB4` | `SPI1_MISO` |

- `IO0` 必须接 `MOSI/PA7`，`IO1` 必须接 `MISO/PB4`。不要按线色判断；按模块
  丝印逐根核对。2026-07-14 的交叉探针已经证明两根接反时，普通路径返回全
  `00/FF`，交换软件方向后能读到真实 `JEDEC=0x0B4018`。
- 原 `PA3/PB9/PB8` QSPI 信号线已经退役，应从 Flash 模块拔掉。`PA2` 片选、
  `3V3` 和 `GND` 保持不变。
- 常见 SPI/QSPI 模块已经处理 `IO2 / WP`、`IO3 / HOLD`，普通 SPI 不再连接
  它们。若使用裸 Flash 芯片，两脚分别用约 `10 kOhm` 上拉到 `3.3V`，不要悬空。
- 当前屏幕使用 `CN7-12` 供电，外部 Flash 使用独立的 `CN7-16` 取同一条
  `3V3` 电源轨；两块模块必须共地。
- 固件以保守的 `SPI mode 0 / 2 MHz` 启动。通过标准不是“SPI1 初始化成功”，
  而是同一次复位日志同时出现 `raw_jedec=0x0B4018`、
  `[screen-assets] external_store=ready kind=spi1_nor` 和
  `[rec-flash] ready=1 jedec=0x0B4018`，录音容量为 `1920000` 字节，并成功
  挂载当前 CEMP 资源包。
- 正式验收必须连续执行两次独立硬复位并通过同一日志门禁。全 `000000` 或
  `FFFFFF`、内部资源回退、录音存储未就绪均为失败；软件交换探针只用于诊断，
  不能替代正确硬件 SPI 接线。

上述 CN7/CN10 编号来自 ST 的 NUCLEO-WB55RG/MB1355 官方接口图；固件启动日志
必须声明 `flash=SPI1-1IO sck=PA1 mosi=PA7 miso=PB4 cs=PA2`。未来 WBA55/WBA65
只替换目标 SPI/CS/引脚/DMA/时间与电源回调，不改变外部资源、录音、OTA 分区
接口及“真实设备探测后才通过”的规则。

接线前确认 FTS02 `P3` 已拨到 `2.2`。`PD0` 是开发板的 `SW2` 按键，不能接
电子纸 `BUSY`。

触摸务必接 `P10` 的 `A4/A5`，不要接 `P8` 上紧挨 `3.3V` 的 `SCL/SDA`。
原理图中，`P8 SCL/SDA` 是 `P5` 24 针电子纸排线的 `TSCL/TSDA`；当前
`GDEY0154D67-T03` 的触摸 FPC 插在 `P6`，它的 `TP_SCL/TP_SDA` 只引到
`P10 A4/A5`。

### FTS02 P1 接到 NUCLEO-WB55RG

使用 FTS02 背面的树莓派兼容 `P1` 接口。下表来自 Good Display FTS02 官方原理图；
接通电源前先在板子上确认 `P1 pin 1` 的方向。NUCLEO 的针脚号以板上丝印及
MB1355 官方引脚表为准：例如 `PC0` 是 `CN7 pin 28`，因此 `PC1` 是 `CN7 pin 30`。
CN10 的电子纸四条关键线是 `CN10-19=PA9`、`CN10-13=PA6`、
`CN10-22=PB0`、`CN10-24=PB1`，不能接到相邻编号。当前供电使用
`CN7-12/3V3(IOREF)`；若必须换线，也可使用 `CN6-4` 或 `CN7-16` 的同一条
`3.3V` 电源轨，绝不能改接 `5V`。

| FTS02 `P1` 针脚 | FTS02 信号 | NUCLEO-WB55RG 针脚 | MCU 信号 |
|---|---|---|---|
| `1` or `17` | `3.3V` | 当前 `CN7 pin 12`；可选 `CN6 pin 4` or `CN7 pin 16` | `3V3 / IOREF` |
| `6`, `9`, `14`, `20`, `25`, `30`, `34`, or `39` | `GND` | 当前 `CN7 pin 19`；可选 `CN6 pin 6/7` or `CN7 pin 8` | `GND` |
| `23` | `SPI_SCK` | `CN10 pin 19` | `PA9` / `SPI2_SCK` |
| `19` | `SPI_MOSI` | `CN7 pin 30` | `PC1` / `SPI2_MOSI` |
| `24` | `CS` | `CN10 pin 13` | `PA6` / `EPAPER_CS` |
| `22` | `D/C` | `CN10 pin 22` | `PB0` |
| `11` | `RES` | `CN10 pin 24` | `PB1` |
| `18` | `BUSY` | `CN7 pin 3` | `PC5` |

- 若转接板的 `P1` 40 针排母不便接线，可直接使用板上标号的 `P8` 与 `P9`。
  `P8` 的 `SDA`/`SCL` 是 `P5` 的 `TSCL/TSDA`，不是本次 `P6` 触摸 FPC 的
  `TP_SCL/TP_SDA`；`MISO` 与 `SPI_SS` 不用于此屏的首次诊断。屏幕的 `CS`
  位于 `P9 pin 8` 的 `T7`，不是 `P8` 的 `SPI_SS`。

| FTS02 排针 | 板上信号 | NUCLEO-WB55RG 针脚 | MCU 信号 |
|---|---|---|---|
| `P8 pin 8` | `3.3V` | 当前 `CN7 pin 12`；可选 `CN6 pin 4` or `CN7 pin 16` | `3V3 / IOREF` |
| `P8 pin 7` | `GND` | 当前 `CN7 pin 19`；可选 `CN6 pin 6/7` or `CN7 pin 8` | `GND` |
| `P8 pin 6` | `SPI_MOSI` | `CN7 pin 30` | `PC1` / `SPI2_MOSI` |
| `P8 pin 4` | `SPI_SCK` | `CN10 pin 19` | `PA9` / `SPI2_SCK` |
| `P9 pin 8` | `T7` / `CS` | `CN10 pin 13` | `PA6` |
| `P9 pin 7` | `T6` / `D/C` | `CN10 pin 22` | `PB0` |
| `P9 pin 6` | `T5` / `RES` | `CN10 pin 24` | `PB1` |
| `P9 pin 5` | `T4` / `BUSY` | `CN7 pin 3` | `PC5` |

- 绝对不要把 FTS02 的 `P1 pin 2` 或 `P1 pin 4` 接到 NUCLEO，它们是 `5V`。
- `P1 pin 21` 是 `SPI_MISO`，本屏幕不需要接；触摸使用的是 P1 的另一组信号，
  不在这次黑屏诊断范围内。
- `PD0` 是 NUCLEO 的 `SW2` 按键，不能接电子纸 `BUSY`。接好 `BUSY` 后，以
  `-EpaperSsd1681HasBusy 1 -EpaperSsd1681BusyPort GPIOC
  -EpaperSsd1681BusyPin GPIO_PIN_5` 构建。没有 `BUSY` 时固件会退回到保守的
  固定延时模式。
- NUCLEO 上的 `PB0` 与 `PB1` 也连到用户 LED 电路；发送电子纸命令时 LED 短暂
  闪烁属于预期现象。

资料来源：[Good Display ESP32-FTS02 产品页](https://www.good-display.com/product/697.html)
、[ESP32-FTS02 官方原理图](https://ecksteinimg.de/Photo/GD09006/ESP32-FTS02_SCH-20250819.pdf)
及 [ST UM2435 的 MB1355 CN7/CN10 针脚表](https://www.st.com/resource/en/user_manual/um2435-pnucleowb55-mb1355-and-mb1293-stmicroelectronics.pdf)。

### 触摸接线（显示验收后）

`GDEY0154D67-T03` 的触摸 FPC 已插在 FTS02 的 `P6`，不要再拔插这条细排线。
触摸控制器为 `FT6336U`。当前固件采用“中断立即采样、活动期 10 ms 采样、20 ms
轮询兜底”，并在电子纸 BUSY 刷新期间继续缓存带时间戳的触摸轨迹：

| FTS02 排针 | 触摸信号 | NUCLEO-WB55RG 针脚 | MCU 信号 |
|---|---|---|---|
| `P10 pin 3` / `A4` | `TP_SCL` | `CN7 pin 28` | `PC0` / `I2C3_SCL` |
| `P10 pin 4` / `A5` | `TP_SDA` | `CN7 pin 1` | `PB11` / `I2C3_SDA` |
| `P10 pin 1` / `A0` | `TP_INT` | `CN10 pin 33` | `PC6` / `EXTI6` |
| `P10 pin 2` / `A3` | `TP_RST`，低有效 | `CN10 pin 29` | `PC10` / GPIO 输出 |

- `TP_INT` 只通知主机触摸数据已就绪，不能替代 `TP_SCL/TP_SDA`；若要真正触控
  中断/Stop 唤醒，至少保留 `TP_SCL`、`TP_SDA`、`TP_INT` 三根。`TP_RST` 是推荐的
  异常恢复线，不是正常触控读取或唤醒的前置条件。
- `PC6` 与 `PC10` 未被当前电子纸、麦克风、扬声器、QSPI 或板载按键占用。即使
  `TP_INT` 暂时断线，20 ms 轮询与刷新期 10 ms 采样仍可工作；接上后轻点首帧延迟更低。
- 触摸和电子纸逻辑均为 `3.3V`。先完成电子纸黑白刷新验收，再单独连接上述两根
  I2C 线并验证触摸，不把两个问题混在同一次排查中。

触摸时序参考：[FT6336U 数据手册](https://files.waveshare.com/wiki/common/FT6336U_Datasheet.pdf)
与 [NUCLEO-WB55RG MB1355 接口针脚表](https://www.st.com/resource/en/user_manual/um2819-stm32wb-nucleo64-board-mb1355-stmicroelectronics.pdf)。

## Operator Chain

Run the automated chain first. It should remain `PASS` while reporting final
physical confirmation as `PENDING_HUMAN`.

```powershell
python .\tools\verify_companion_operator_chain.py --hardware-acceptance-summary C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\companion-hardware-acceptance-20260630-112402\companion-hardware-acceptance-summary.json --real-ble-bench C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\companion-v1-real-ble-gatt-20260630-114513\companion-ble-real-bench.json --json
```

## Physical Signoff Prompt

Dry-run the prompt without touching hardware:

```powershell
pwsh -NoProfile -File .\tools\verify_companion_physical_signoff.ps1 -NoEpaperPanel
```

Execute it only under the workflow hardware lock:

```powershell
pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose "Companion final physical signoff" -Run pwsh -NoProfile -File .\tools\verify_companion_physical_signoff.ps1 -Execute -WorkflowLockHeld -NoEpaperPanel
```

`-NoEpaperPanel` records all e-paper observation checks and the e-paper refresh
current row as `N/A` with the note `no e-paper panel installed`. Remove the flag
only after a real panel is connected.

## Human Observations To Record

- Real e-paper default card, recording card, sync-complete card, and BLE-written
  short card, or explicit `N/A` if no panel is installed. Use
  `-NoEpaperPanel` for the current no-panel bench. Visual evidence may be
  operator photos or a local webcam capture saved into the session `visual/`
  directory; do not assume live camera access unless the operator has explicitly
  set up a capture path for that run. Use
  `python .\tools\capture_panel_visual_preflight.py --session-root <session-root>`
  to prove the camera capture path without claiming a real panel refresh.
- Real `SW3/B3` button press causes a capture or recording affordance.
- Real microphone/storage chain can capture, pull a non-empty recording, verify
  length plus SHA-256, and delete only after host verification.
- Current measurements for boot/idle, BLE advertising, connected idle,
  recording, e-paper refresh, and BLE chunk transfer. Battery, charger,
  fuel-gauge, and charge/external-power measurements are `N/A` on the current
  dev-board bench unless a separate measurement fixture is connected.
- PCB decision remains `continue_dev_board_iteration_before_first_pendant_pcb`
  unless a human explicitly overrides it with evidence.

## Current Default Decision

The current default is to continue development-board iteration before a first
pendant PCB. PCB go still needs real display timing/refresh observation, real
external SPI NOR timing and power, and measured battery/charger/fuel-gauge or
external-power behavior on product hardware.
