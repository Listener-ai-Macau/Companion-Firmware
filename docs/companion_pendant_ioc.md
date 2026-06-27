# Companion Pendant — STM32CubeIDE / CubeMX 配置

Companion Pendant 的 CubeMX 配置 `.ioc` 在仓库根 `Companion_Pendant.ioc`(即 CubeIDE 工程根),从开发板 NUCLEO-WB55RG(STM32WB55**RG**,68 脚)转到量产芯片 **STM32WB55**CE**(UFQFPN48 / 512KB)。

`.ioc` 是 CubeMX 的"单一事实源";CubeIDE/CubeMX 据此生成 `Core/` 工程代码(`.project`/`.cproject` 由 CubeIDE 在 Generate Code 时自动产生,**不手工写**)。不要从零新建一个散落的 STM32 工程;正式产品工程必须从这个现有 `Companion_Pendant.ioc` 生成。

## 外设一览(WB55CE 上已用 HAL 头核实)

| 功能 | 外设 | 引脚 | 说明 |
|---|---|---|---|
| BLE 射频 + 低功耗基线 | RF / IPCC / HSEM / RTC / STM32_WPAN / SEQUENCER / TINY_LPM | RF1、PC14/PC15(LSE 32.768kHz)、HSE 32MHz | 从官方 `BLE_p2pServer` 模板克隆 |
| 调试串口 RX/TX | USART1 | PB6=TX, PB7=RX | bring-up 专用硬件日志口,兼 BLE console/trace |
| USB CDC 串口 + DFU 升级 | USB(Device) + USB_DEVICE(CDC) | PA11=DM, PA12=DP | DFU 用芯片内置 ROM bootloader(见下) |
| QSPI NOR flash | QUADSPI(AF10) | NCS=PA2, CLK=PA3, IO0=PB9, IO1=PB8, IO2=PA7, IO3=PA6 | 录音缓存;按 STM32WB55CEUx UFQFPN48 可引出 AF 表重排 |
| e-paper 屏 | SPI1(AF5) | SCK=PB3, MISO=PB4, MOSI=PB5 | NSS/DC/BUSY/RST 走普通 GPIO |
| 传感器 / e-paper 控制器 | 暂不占 CubeMX 硬件 I2C | 待定 | 48 脚封装下 I2C1 与 USART1/QSPI 竞争;bring-up 先保调试串口 |
| 电池电压采样 | ADC1 | PA0=IN5 | |
| 麦克风 RX + 喇叭 TX | SAI1 | CK_A=PA8, FS_A=PA9, SD_A=PA10, SD_B=PA5 | **两路音频合用一个 SAI1**:Block A=喇叭 TX,Block B=麦克风 RX,共享 CK_A/FS_A |
| SWD 调试 | SYS | PA13=SWDIO, PA14=SWCLK | |

### 几个关键点(为什么这么配)

1. **WB55 没有 SPI3 / I2S3 / I2C2**。所以"两路 I2S"在 WB55 上不能用 SPI2+SPI3,必须走 **SAI1**。SAI1 单外设用 Block A/B 全双工同时承载喇叭(TX)和麦克风(RX),引脚最省。
2. **QSPI 是 `QUADSPI` 外设(AF10)**,不是 OCTOSPI。STM32WB55CEUx / UFQFPN48 上不能用 PB0/PB1/PB11/PB15 做 QSPI;当前方案改用官方 48 脚封装可用的 PA2/PA3/PB9/PB8/PA7/PA6。
3. **调试优先保留 USART1(PB6/PB7)**。SWD 负责断点/烧录/单步,USART1 负责早期启动、低功耗唤醒、HardFault 前后的连续日志,USB CDC 作为应用层辅助串口。这样 Codex/自动化才能在 bring-up 阶段完整抓日志。
4. **I2C1 暂不占硬件外设**。在 48 脚封装中,硬件 I2C1 的常用脚与 QSPI 或 USART1 竞争。等 e-paper 控制器/传感器需求确认后,再决定牺牲调试串口、改软件 I2C,或调整外设。
5. **48 脚只引出**:PA0–15、PB0–9、PC14、PC15、RF 等;不要把 68 脚开发板上的 PB10–PB15/PC0/PC1 可用性直接带到 UFQFPN48 产品封装。
6. **DFU 升级**用 STM32WB55 内置 ROM USB DFU bootloader(进 system memory,PA11/PA12),无需应用代码;应用侧 USB 只配 CDC(VCP)做串口日志。日后若要应用内 DFU,再在 CubeMX 把 USB_DEVICE 改成 CDC+DFU composite。
7. USB 时钟走 **HSI48**(内部 48MHz,`RCC.USBCLKSOURCE_HSI48`),不占晶振;RNG 也走 CLK48。

## 在 CubeIDE 里打开 + 生成代码

1. 启动 STM32CubeIDE 2.1.1。
2. **File → Open File** → 选仓库根的 `Companion_Pendant.ioc`(完整路径 `C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\Companion_Pendant.ioc`)。
   - 弹出的对话框选 **Generate Code**(工程名 `Companion_Pendant`,工具链 STM32CubeIDE,GCC for Arm)。
   - 若提示 MCU/DB 版本差异,选 Migrate / use installed DB 即可。
3. CubeMX 会校验引脚路由。**下面几处要重点确认**:
   - **QUADSPI**:PA2=NCS、PA3=CLK、PB9=IO0、PB8=IO1、PA7=IO2、PA6=IO3。若 CubeMX 提示冲突,不要退回 PB0/PB1/PB11/PB15,那些不是 STM32WB55CEUx/UFQFPN48 的可用 QSPI 路由。
   - **SAI1 音频**:Block A=TX(喇叭),Block B=RX(麦克风),CK_A/FS_A 共享,16kHz,I2S,TX/RX 各一路 DMA。Pinout:PA8=CK_A、PA9=FS_A、PA10=SD_A、PA5=SD_B。
   - **USART1 调试串口**:PB6=TX、PB7=RX,115200,TX DMA。STM32_WPAN trace/console 使用 hw_uart1。
4. **Generate Code**(CubeMX 图标或 Alt+K)。`Core/Src/` 会生成 `mx_adc1.c / spi.c / i2c.c / quadspi.c / sai.c / dma.c / stm32wbxx_it.c / usb_device.c / usbd_cdc_if.c` 等。
5. HAL/LL/CMSIS 与 STM32_WPAN 中间件从 `third_party/STM32CubeWB/` 链接(只读引用,不复制 —— 遵守 `starter.paths.json` 规则)。

## 构建与烧录

- **构建**:在 CubeIDE 里 Build(Ctrl+B),产物 `Companion_Pendant.elf`。`tools/build.ps1` 目前仍指向第三方 `BLE_p2pServer` 样例(本步不动它);让 build.ps1 转向本产品工程是后续单独一步。
- **烧录**:CubeProgrammer,或 `tools/flash.ps1`(需 `aiw with-lock -Resource Companion-WB55`)。CPU1 应用 + 无线协处理器 BLE 栈(`stm32wb5x_BLE_Stack_full_fw.bin`)。

## 验收

- [ ] `.ioc` 在 CubeIDE 打开,MCU 显示 **STM32WB55CEUx / UFQFPN48**,无致命错误。
- [ ] Pinout 视图 QUADSPI/SPI1/ADC1/SAI1/USART1/USB 外设全部点亮,无红冲突。
- [ ] Generate Code 成功,`Core/Src/` 各 `mx_*.c` 就位。
- [ ] Build **0 error**(warning 可接受)。

## 待确认(会影响 .ioc 后续微调)

- **mic 型号 = INMP441**(已确认)。INMP441 是 **I2S 数字麦克风**(内置 PDM→PCM,输出 I2S PCM,不是 PDM 位流),所以 SAI1 **保持 I2S 模式 RX**(本 .ioc 默认即此,无需改 PDM)。接线:SAI1_CK→SCK,SAI1_FS→WS,SAI1_SD_B(RX)←SD;L/R 选脚接地用左声道。若日后换 PDM mic(如 MP34DT05),再把 SAI1 切 PDM 模式。
- **QSPI flash 型号**:影响 `FlashSize`/Dummy cycle(现按通用 16MB NOR)。
- **e-paper 是否带 I2C 加速芯片**:若有,需在保留 USART1 调试与硬件 I2C 之间重新取舍,或做软件 I2C;若纯 SPI,I2C 可继续后移。
