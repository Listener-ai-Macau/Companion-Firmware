# Companion 产品板 USB 开发与恢复需求

## 结论

Companion 产品板不集成 ST-LINK 芯片。日常开发、日志和工厂恢复必须通过产品
USB-C 入口完成，但实现取决于最终 MCU，不能把 Listener 的 ESP32-S3 USB
Serial/JTAG 机制直接移植到 STM32。

| 目标 | 日常开发/日志 | 工厂下载与恢复 | 结论 |
|---|---|---|---|
| 当前 NUCLEO-WB55RG | 板载 ST-LINK VCP 的 USART1 | ST-LINK/SWD | 仅开发板路径，不是产品板方案 |
| WB55CE 产品板 | 原生 USB CDC | ROM USB DFU；SWD 触点救援 | 已有 `Companion_Pendant.ioc` 规划，尚未在产品 PCB 验证 |
| WBA55 产品板 | 外置 USB-UART bridge 提供电脑 VCP | ROM USART bootloader；SWD 触点救援 | WBA55 无原生 USB/ROM USB DFU，不能做 Listener 式单 USB JTAG |
| WBA65 产品板 | 原生 USB CDC | ROM USB DFU；SWD 触点救援 | 原生 USB-C 是首选用户体验，但仍不是 USB JTAG |

Listener 使用 ESP32-S3 内置 USB Serial/JTAG，同一根线可做 console、烧录和
JTAG。STM32WBA 不提供这种等价的内置 USB JTAG：USB 是数据/CDC/DFU 通道，
SWD 是独立的工程与返修救援通道。

## 当前事实

1. 当前屏幕开发板实际由 `flash_nucleo_bringup.ps1` 通过板载 ST-LINK/SWD
   烧录，运行日志来自 ST-LINK VCP 的 USART1（PB6/PB7）。这条路径继续保留，
   直到产品板 USB 链路实际验收；不能在 NUCLEO 上假装已完成产品 USB 开发。
2. `Companion_Pendant.ioc` 的 WB55CE 规划已经预留 PA11/PA12 的 USB CDC 与
   ROM USB DFU，USB 时钟走 HSI48；它是 WB55 产品板的输入，不是 WBA55 的
   pinout 模板。
3. `Companion_BLE_Ota_Loader`/外部 `ota_staging` 是产品的 OTA 安装层；当前
   屏幕 bring-up 不经过它，而是直接 SWD 写入普通固件。OTA 仍受 Listener/Denzic
   共享提交冻结，USB 项目不绕过该冻结。

## WBA 选型规则

### WBA55

ST 的系统 ROM bootloader 表中，WBA5xxx 支持 USART1/USART2、I2C、SPI，未列
USB DFU；产品系列资料也把 WBA55 的 USB 列为 `None`。因此 WBA55 产品板采用：

- USB-C 连接外置 USB-UART bridge，桥接 MCU 的一组专用 UART TX/RX；Windows
  以普通 VCP 看到日志和开发控制台。
- bridge 的 DTR/RTS（或等价控制）经受控逻辑驱动 `NRST` 与 boot entry；必须仍有
  物理 recovery pad/按键，不能只依赖自动进 boot。
- STM32CubeProgrammer 使用 ROM USART bootloader 下载 factory/recovery 镜像；
  这不是 USB DFU，也不是应用 CDC。
- USB D+/D- 不直连 WBA55。USB-C 的 CC、ESD、VBUS 电源路径和 bridge 供电/电平
  必须由硬件设计单独确认。

### WBA65

WBA65 有原生 USB OTG，并且系统 ROM bootloader 支持 USB DFU。产品板采用：

- USB-C D+/D- 直连 MCU 的 USB 引脚，按 ST 硬件条件提供 VDDUSB、VBUS 检测、
  ESD、防反灌和正确的 CC 下拉；OTG HS 时钟要求 HSE32，不能沿用 WB55 的
  HSI48 假设。
- 应用提供 USB CDC：结构化诊断、版本、屏幕/触摸/麦克风状态和受限开发命令。
- factory/recovery 使用 ROM USB DFU，不依赖可损坏的应用程序；正常产品更新仍
  走 Denzic BLE OTA/安全更新链路，不能把 USB DFU 当成普通 OTA 的替代品。

## 共同软件接口

Host 工具对三种 transport 使用同一命令和日志格式：`identity`、版本、构建 hash、
诊断导出、受限的资源/音频开发操作和 reset/recovery 状态。transport 只替换为
`stlink_vcp`、`usb_uart_vcp` 或 `native_usb_cdc`；业务协议、诊断 schema 和
自动化证据格式不得因 MCU 分叉。

正常应用不应暴露任意 Flash 写命令。开发写入只允许走 ROM bootloader、受签名的
resident updater 或明确受限的 factory mode；USB CDC 只承担日志和经过认证/物理
开启的诊断命令。

所有 Companion 产品 PCB 无论是否有 USB，都必须留：`SWDIO`、`SWCLK`、`NRST`、
`GND` 和稳定供电测试点（建议 Tag-Connect/测试焊盘），供首板、量产失败分析和
无法进入 ROM bootloader 时救援。它们不代表板上需要 ST-LINK 芯片。

## Bootloader 分层

```text
ROM bootloader (不可变 recovery)
  WB55: USB DFU / USART / SPI / I2C
  WBA55: USART / I2C / SPI
  WBA65: USB DFU / USART / I2C / SPI
        ->
resident product bootloader / secure boot (受签名 mcu_app 安装)
        ->
Companion application (USB CDC or UART console, BLE OTA, screen/audio)
```

当前产品设计中的 resident CPU1 bootloader 从外部 `ota_staging` 验证并安装
`mcu_app`，应用通过 vector-table offset 启动；它不替代 ROM bootloader/SWD。
现在它的 OTA 实作和真机验收仍冻结，不能把其设计文档说成已在 WB55 屏幕固件上
运行。

## SCR-19 验收门

1. 原理图审查：按最终芯片验证 USB/UART 引脚、电源、ESD、CC、VBUS、NRST、boot
   entry 和 SWD 测试点；WBA55 不允许直连不存在的原生 USB；WBA65 不允许漏 HSE32
   / VDDUSB 条件。
2. 冷启动、复位和低功耗后，电脑能稳定枚举目标 VCP，并能拉取结构化诊断；日志
   不得依赖 ST-LINK VCP。
3. 在不接 ST-LINK 的条件下，从 ROM download mode 写入、校验并启动 factory/app
   镜像；故意写入错误镜像后仍能通过 BOOT/NRST 或 SWD pads 恢复。
4. 量产接口测试：USB-C 插拔、VBUS/充电共存、异常拔线、桥接器断连和 host 切换
   不影响正在运行的录音、外部 Flash 或产品数据。
5. USB 与 OTA 分层：ROM/recovery、factory/dev flash、Denzic OTA 的证据和权限
   各自独立；USB 恢复不能绕过量产安全策略。

## 调研依据

- STM32WBA5xxx 的 ROM bootloader 支持 USART/I2C/SPI，WBA62/63/64/65 才列出
  USB DFU：<https://www.st.com/resource/en/application_note/an2606-stm32-microcontroller-system-memory-boot-mode-stmicroelectronics.pdf>
- ST 的 WBA 系列总览把 WBA55 列为无 USB、WBA65 列为 USB 2.0 HS：
  <https://www.st.com/en/microcontrollers-microprocessors/stm32wba-series.html>
- WBA65 datasheet 指明原生 USB OTG HS 及 HSE32/VDDUSB 约束：
  <https://www.st.com/resource/en/datasheet/stm32wba65ri.pdf>
- Listener 的 ESP32-S3 USB Serial/JTAG 可以同线 console、烧录和 JTAG，正是
  Companion 不能机械照搬的差异：
  <https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/usb-serial-jtag-console.html>

## 防回退

```powershell
python .\tools\verify_companion_usb_development_requirements.py --write-fixture
```
