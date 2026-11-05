# WBA V1.1 首次安装工具

本工具准备“空白板 → 表情资源 → boot/app → 精确读回 → 启动”的流程。
软件已编译和故障注入验证；当前包未刷写，已有连接尝试仍未读到真实身份，实板行为与完整会议验收仍为 NOT_RUN。
本轮候选为 FW1.1.35 / UI53；CE（512 KiB）和 CG（1 MiB）分别打包，包内身份与真实容量必须一致，
不能仅凭丝印或把硬件标签改名后安装。保留未同步录音保护、满盘提示、升级中断恢复、真实 GATT 服务注册与有界诊断日志导出，
沿用六针安装和只读串口故障查询，更新 About 身份文字，保留表情、首页、
独立饰品时钟、录音声波及四格菜单像素与行为，不修改历史 WB55 基线。

## 到板操作

各功能的软件状态和真实硬件门禁见上级目录 `SOFTWARE_FEATURE_MATRIX.md`；factory-kit 内的
`firmware/board-integration.md` 保留同一入口说明。

使用 factory-kit 解压目录里的 `Install-WBA.ps1`。需要 Python 3.10+、STM32CubeProgrammer
和兼容 1.8V 目标参考电压的 ST-LINK。JP6 六针为下表；默认不需要 NRST。这版 USB-C 仅供电。
不要按旧 WB55 的地址烧录，也不要使用其无线栈或 option-byte 脚本。

| JP6 针号 / 标记 | 板端连接 | 用途 |
| --- | --- | --- |
| 1 / V | 经 R38 33Ω 接 1.8VDC | 探针 VTref / 电平参考，不作为供电输入 |
| 2 / G | VSS | 共地 |
| 3 / C | 经 R39 33Ω 接 PA14 | SWCLK |
| 4 / D | 经 R40 33Ω 接 PA13 | SWDIO |
| 5 / RX | 经 R41 33Ω 接 PA1 / LPUART1_RX | 接 USB-UART 适配器 TX |
| 6 / TX | 经 R42 33Ω 接 PA2 / LPUART1_TX | 接 USB-UART 适配器 RX |

依据最新 PCB net evidence 核对针号，不按线束排列猜接线。目标板独立供电；
串口适配器必须支持 **1.8V 逻辑电平**，不能把 3.3V/5V TX 直接接入。JP6 没有 NRST/SWO。
默认使用 `mode=NORMAL reset=SWrst`，校验后软件复位并恢复运行。
只有额外接了板上 NRST 时才传 `-NrstConnected`，改用 `UR/HWrst`。
若已有固件关掉 SWD 或深睡导致普通连接失败，工具会保留错误，不能保证只靠六针解锁；
需确认独立 NRST 连接后再选择该参数，不自动修改保护或 option bytes。

```powershell
# 无板即可执行：只检查文件/地址/哈希，不连接探针。
.\Install-WBA.ps1

# 到板后：明确选择该板所接的 ST-LINK；写入范围固定，无整片擦除。
.\Install-WBA.ps1 -Execute -ProbeSerial YOUR_STLINK_SERIAL -OutputDirectory C:\WBA-runs\first

# 若首次灌装断电，使用原始失败目录及全新的输出目录。
.\Install-WBA.ps1 -Execute -ProbeSerial YOUR_STLINK_SERIAL -ResumeDirectory C:\WBA-runs\first -OutputDirectory C:\WBA-runs\retry
```

## 不接 SWD 的运行诊断

应用固件已安装后，只接 G、RX、TX 即可查询；不需要蓝牙、Type GUI 或 SWD 调试器。
这三针用于应用串口日志，**不是 ROM 首次烧录接口**。STM32WBA5xxx ROM USART 使用的引脚
与 JP6 的 PA1/PA2 LPUART 不同。空白板仍先按上述 SWD 流程安装。

串口为 115200 / 8N1，无流控。安装 Python 的 `pyserial` 后，在解压包根目录运行：

```powershell
# 明确指定目标串口；不会扫描/试开其他 COM，也不会复位、擦除、开始录音或刷写。
.\Diagnose-WBA.ps1 -Port COM7 -OutputDirectory C:\WBA-runs\uart-first

# 只监听，不发送查询；也可用常用串口终端发送一个 ?，无需回车。
.\Diagnose-WBA.ps1 -Port COM7 -ListenOnly -Seconds 30 -OutputDirectory C:\WBA-runs\uart-listen

# 离线解析既有日志，不访问设备。
.\Diagnose-WBA.ps1 -InputLog C:\WBA-runs\uart-first\uart.log -OutputDirectory C:\WBA-runs\uart-parsed
```

默认仅发送单字节 `?`。固件会在非录音/非播放时输出同一序号的完整 `DIAG1 BEGIN` 至 `END`。
忙时延后查询，未知字节无操作。工具默认等待 15 秒；无响应时先确认录音/播放已结束、
固件支持该接口、串口没有被其他程序占用、电平与接线正确。不能仅因超时判断坏板。
启动和周期报告也可监听；串口终端与采集工具不要同时占用同一端口。

输出 `uart.log`、`result.json`、中文 `summary.txt`，分别保留原始字节、结构化快照、问题提示。
诊断包括 FW/build/UID/UI、复位原因及看门狗标志、模块 fault、屏幕/资源、NOR/录音、
麦克风 DMA/溢出/处理时限、BLE 初始化与连接，以及电池有效性/OTA 电源阻塞。
CORE 的模块字段全部 **1=对应故障位已置位**；0 不代表物理验收通过。
录音帧数为 0 会标记未实测；未连接 BLE 不直接判为坏模块；无效电池数据不会显示成实测 0%。
工具拒绝缺项、重复字段、串号混合和截断帧；旧的完整帧不能掩盖后续截断。
返回码 0 仅表示完整快照未报告故障，2 表示发现问题/身份不符/采集不完整或失败。
所有结果均保留 `hardwareAcceptance=NOT_EVALUATED`、`fullChainAcceptance=NOT_RUN`。
日志只保存本地，不含音频或服务密钥，也不会自动上传；MCU UID 会保留以绑定目标板。

若 BLE 初始化未返回，启动日志的 `BOOT1 phase=pre_ble` 可定位最后阶段；主线程可安全输出时，
致命错误会留下 `BOOT1 FATAL phase=...`，工具报告 `BOOT_FAILURE_REPORTED`。
抓取启动故障时先运行 `-ListenOnly`，再给目标板上电，以免错过启动阶段日志。
UART 未初始化前崩溃、UART 本身失效、IRQ/HardFault 中断异常等无法保证通过串口诊断，仍需 SWD。
串口不能替代断点、内存检查或异常栈回溯。正常使用无需连接调试线。

目录应可写；每次输出目录必须为空。初次操作会保存完整 MCU/NOR 读回与逐步日志。
已在用设备的读回可能包含私人录音/配对信息，保存在本地，不随诊断自动上传。
普通产品更新继续使用签名 OTA，不能把本工具当成恢复出厂设置入口。

## 到板整链运行手册

以下步骤都在解压后的 factory-kit 根目录执行。先做无硬件预检；它只校验整包哈希，结果应为
`READY_FOR_INSTALL`，不能当作刷写或产品验收：

```powershell
.\Run-WBA-Board-Arrival.ps1 -KitRoot $PWD -StateOutput C:\WBA-runs\gate-preflight.json
```

接上唯一一块目标板后，用同一运行目录完成首次安装。`install\result.json` 会保存 MCU UID、
固件包身份、MCU/NOR 最终读回哈希；`PASS_INSTALL_READBACK_ONLY` 仍不是硬件或会议链 PASS。

```powershell
.\Run-WBA-Board-Arrival.ps1 -KitRoot $PWD -ExecuteInstall `
  -ProbeSerial YOUR_STLINK_SERIAL -InstallOutput C:\WBA-runs\install `
  -StateOutput C:\WBA-runs\gate-after-install.json
```

安装本包的 Type MSI 后，先在系统设置中配置真实 ASR 与纪要服务。会议播放稿必须在运行前固定，
把其中需要核对的事实短语保存为 UTF-8 JSON 字符串数组，例如
`["决定采用离线先存", "在线实时纪要", "小陈周五验收"]`。不能从 ASR 或纪要结果反向生成
truth。用电脑扬声器播放该稿，让板端麦克风空中拾取；命令必须带主动断线点、truth、设备检查
和整链输出：

```powershell
$exe = 'C:\Program Files\Companion Type\companion-type.exe'
& $exe --board-online-live --seconds 45 --partial-interval-ms 8000 `
  --disconnect-after-seconds 15 --truth-file C:\WBA-runs\truth.json `
  --device-check-output C:\WBA-runs\type-device-check.json `
  --output C:\WBA-runs\full-chain.json
```

该入口先通过正式 OOBE GATT 读取 FW `0x00010114`、build `0x20261004`、board
`0x57424155` 和 WBA55 V1.1 身份，再执行板端 codec=3 实录。它从 pulled WAV 的 RIFF/fmt/data
及 PCM 样本计算可解码、非静音证据，拒绝环境文本和 transcript sidecar 冒充真实 ASR；
offlineStore 与 onlineLive 必须都是非空 final 纪要，准确率分别对照预置 truth。任一早期错误也会
写 `FAIL_WBA_FULL_CHAIN` JSON。不要手填 `PASS_TYPE_DEVICE_CHECK` 或修改证据 JSON。

WBA DEVICE_STATUS 在兼容的 20-byte V1 前缀后追加真实 MCU 96-bit UID 与当前已挂载
UI generation。Type 将原始 UID 字节输出为小写 hex；gate 与安装时 ST-LINK 从同一 UID 地址读取的
值逐字节匹配，同时核对 UI38。旧 20-byte 固件仍可连接，但没有这两个尾部字段时会停在
`BLOCKED_HARDWARE_IDENTITY_BINDING`；不能手填 JSON 绕过。

最后把三个机器产物交给 gate。显示、触摸、电源因没有可读自检 GATT，会保留
`READY_FOR_MANUAL_HARDWARE_CHECKS`，不能变成 `READY_FOR_OWNER_REVIEW`；只有实物检查和最终
Owner 阻塞窗能关闭这些项。

```powershell
.\Run-WBA-Board-Arrival.ps1 -KitRoot $PWD `
  -InstallResult C:\WBA-runs\install\result.json `
  -TypeDeviceCheck C:\WBA-runs\type-device-check.json `
  -FullChainAcceptance C:\WBA-runs\full-chain.json `
  -StateOutput C:\WBA-runs\gate-final.json
```

Type 更新后必须用新的已安装候选证据重建 factory-kit，不能替换旧 kit 内 MSI。仓库根目录命令：

```powershell
python tools\package_wba_factory_kit.py `
  --firmware-package .cache\wba-v11-prehardware\packages\YOUR_VERIFIED_FIRMWARE_PACKAGE `
  --type-evidence ..\Companion-Type\.cache\YOUR_NEW_TYPE_CANDIDATE `
  --output .cache\wba-factory\packages
```

打包器会核对 Type 源码、构建日志、MSI、已安装 EXE/DLL 和安装日志身份，并把
`Run-WBA-Board-Arrival.ps1` 与 verifier 哈希写入新 kit ID。旧 kit 不会被覆盖。

执行次序：

1. 校验匹配的 boot/app/UI 文件、向量地址、分区范围及 SRAM 加载器身份。
2. 选择指定探针，读 DBGMCU family 0x492、包所需的 CE 512 KiB / CG 1024 KiB Flash-size、UID、option bytes；
   要求 TZEN=0、RDP=0xAA、软件 watchdog，不自动改变芯片保护/配置。
   family ID 同属 WBA52/54/55，不能单凭它证明 PCB 料号；板型由显式入口确认。
3. 按包的容量全读 CE 512 KiB / CG 1 MiB MCU 与 16 MiB NOR，并保护各自最后 16 KiB SNVMA。
   首次安装要求产品写入区域全空白；发现已有资料立即拒绝写入。
   若程序与 UI 已逐字节一致，则保留用户数据，只重新启动。中断恢复需匹配原 UID、包身份及空白备份，
   同时检查持久化写入阶段和合法的单向编程位变化；拒绝不相符内容。不要在两次尝试间混用其他刷机工具。
4. SRAM 加载器经 SPI3 写 NOR 前 2MiB，再精确读回。`0x90000000` 是工具的虚拟地址，
   不是 MCU flash 地址，也不是实际 memory-mapped 外设。
5. UI 通过后，从 `0x08000000` 写入配套 boot+app。重新全读 MCU/NOR，确认内容和未写区域。
6. 只有全部读回匹配才发软件复位并恢复运行（明确选择 NRST 时用硬件复位）。`PASS_INSTALL_READBACK_ONLY` 仅表示安装读回通过。
   到板后还需 Type 检查、实录/断连续传/真实转写与双模式纪要，以及屏幕/触摸/声音实测。

首次写板前，两个备份文件会 flush/fsync；阶段记录先写临时文件并 fsync，Windows 使用
MoveFileExW 的 REPLACE_EXISTING + WRITE_THROUGH 提交（POSIX 则另做目录 fsync）。
恢复记录/备份丢失或损坏时拒绝续写，不能通过“忽略校验”绕过。没有宣称主机或目标存储介质物理断电已验证。

加载器 `Read` 可读整个 NOR，`Write` / `SectorErase` 只允许 UI 分区，`MassErase` 永远拒绝。
初始化复用现有 NOR 驱动和已核对 SPI3 引脚（CS PA8、SCK PA0、MOSI PB8、MISO PB9），
使用内部 HSI；不依赖产品固件、蓝牙、屏幕复位、HSE/LSE或中断。

## 到板前验证

下列开发命令在 `Companion-Firmware` 仓库根目录执行，使用仓库已有 SDK 和构建依赖；
交付包内日常安装只运行根目录的 `Install-WBA.ps1`，无需重新编译加载器。

```powershell
python tools/build_wba_factory_loader.py
python tools/verify_wba_factory_loader.py
python tools/test_wba_factory_provision.py
python tools/test_wba_diagnostic_console.py
python tools/test_wba_uart_diagnostics.py
python tools/verify_wba_uart_contract.py
```

包含实际 ARM 编译、ST 官方 API 离线解析 callable ELF 和 StorageInfo、原生 C 越界/错误测试，
以及模拟 SWD 下运行实际安装控制器的中断、错误板型/保护配置、已有录音、读回错误、区域保护测试。
模拟测试不能证明电气、实际写入、声学、BLE 或玻璃显示通过。

外部加载器 ABI 和 CLI 使用依据：
[ST 自定义外部加载器说明](https://dev.st.com/stm32cube-docs/prog/2.23.0/en/docs/markup/CubeProg_UserManual/Memory_programming_and_erasing.html)、
[ST CLI 文档](https://dev.st.com/stm32cube-docs/prog/2.23.0/en/docs/markup/CubeProg_Command_Lines.html)。
SDK 沿用仓库 pinned CubeWBA；ST API 检查只解析文件，不枚举/连接/操作任何探针。

复位方式依据 [ST UM2237](https://www.st.com/resource/en/user_manual/dm00403500-stm32cubeprogrammer-stmicroelectronics.pdf)；
ROM USART 引脚依据 [ST AN2606 的 STM32WBA5xxx 表](https://www.st.com/resource/en/application_note/an2606-introduction-to-system-memory-boot-mode-on-stm32-mcus-stmicroelectronics.pdf)。

当前硬件资料中的 EPD_RES 无 MCU 端点、ADC 满电量程不匹配、PG/STAT 缺少上拉仍需硬件侧确认。
灌装不能修复这些连接；当前产品固件继续明确屏幕 NOT_READY、电池未知。
