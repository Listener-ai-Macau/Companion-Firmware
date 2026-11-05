# WBA55CE 独立外设诊断

此目标为当前实板的外设功能检查使用。**编译成功、初始化成功、读到芯片 ID、DMA 完成，都不等于外设实物合格。** 各项原始数据和物理现象须分别确认。它不替代正式产品录音、BLE、OTA、显示并发或功耗验收。

## 当前状态（2026-10-09）

07:54 实板恢复完整 FW136/UI67 状态，随后已实际运行 SRAM v1、v2；加载前后内部 Flash/NVM 逐字节相同。加载器已修正为 Cortex-M33 的 AP1，以及产品 UART 半行与 HELLO 连在一起时的识别。实际结果在 `.cache/peripherals-20261009/`：

- NOR：7 个地址各读取 4 KiB；确认两更新元数据整扇区全空后，最后一扇区两个图案的擦除、写入、逐字节读回和原内容恢复通过。只确认基础读写，未覆盖全片寿命／每个存储单元。
- 双麦：各 80 ms PDM 采集、70 ms PCM 导出完整；两路不同、无削顶，分别跟随电脑 1 kHz 和 2 kHz 声源，对应频率幅度相对环境样本增加约 28–34 dB。基础拾音响应成立，非正式录音／音质验收。原始设备 END 失败为采集完成之后的 HSE 关闭超时，不能据此说麦克风失败。
- IMU：45 秒 2236 个样本、0 通信错误，六轴有变化，三轴旋转均响应；六个静置方向尚未完整覆盖。
- 扬声器：24 个 DMA 块全部完成，Owner 明确反馈“完全没有声音”；输出链路未通过，尚未定位到功放、信号或供电。
- I/O 扩展器：4 个寄存器读回有效，IMU INT1 在 P3 有高低变化；其余端点不能因寄存器可读就全部通过。
- 屏幕：Owner 明确反馈“两幅都完整，黑白反转正常”，本次图案显示和反相的实物观察成立。原文中第一幅 BUSY 完成、第二幅未观测到 BUSY 拉高，两项证据须同时保留，不能用软件状态否定目视结果或直接判屏坏。原诊断连续使用两次 Mode1，v3/v4 已改为一次完整刷新建立基线、再以 Mode2 反相；修正后的流程尚未在板上执行。
- 按键：21:23 原生窗口与主机持续采集已实际运行，Owner真实操作产生10次按下、10次松开（事件0–19），并点击“我已按完”。最后一次状态查询3秒未回完整END，原始采集结果仍保留`KEY_LIVE_CAPTURE_FAILED`；期间主板仍发按键事件。21:28以3ms字节节奏读取原ARM，未重新ARM／清零／先复位，即取回完整10/10、最终松开及`THREE_PRESS_RELEASE_OBSERVED`，随后STOP并返回FW136/UI67。按键基础响应通过；此前上午未取得结果的失败保留为历史。证据：`key-popup-battery-2123/owner-result.json`、`key-query-recovery-212808/result.json`。
- 触摸：产品原文出现过 ID `64/01/11` 和 4 次接触，随后轮询 NACK，属于间歇通信失败。已装 FW136 的实际 Flash 代码在 `0x08021A80` 的 I²C 初始化固定写 `TIMINGR=0x10422529`（名义约 100 kHz）；当前产品源码的 50 kHz 修改未装入 FW136，不能把源码当实测。

08:08 SRAM 诊断不再返回 UART；08:09 唯一一次只读 SWD 入口在 init 被拒，调试参考电压报告 `0.003179 V`，未读 UID、未停核、未复位、未写板。这是历史失败现场，不能区分主板断电与调试接线中断，充电根因仍交硬件同事处理。Owner晚间澄清换了有电的电池；实际读回仍是原UID及原FW136全片，21:28已确认退出诊断。随后共享屏幕阶段实装151/UI67；后续入口以当前实际身份及共享占用为准。

21:35 UART查询修正已构建v7，21:45已实板验证查询路径：原诊断只在前台轮询接收，输出日志期间有丢查询字节的风险；本轮未捕获原来的具体丢字节或ORE，不能声称唯一根因已证明。v7启用UART FIFO与接收中断、128B有界队列，输出期间继续收命令；接收故障清除不完整命令并明确报告，HELLO带`rx_irq`／`rx_faults`。主机命令改为3ms字节节奏，窗口将查询超时与采集进程退出分开。`.cache/peripherals-20261009/ram-diag-v7-uart-rx/build.json`，bin SHA `2f07f7c0287983116bf7773d4744a55236ec9f4d85f0e310322bf11bfa52e6dc`，代码/data/BSS 86344B，另留24KiB栈。实际`.cache/peripherals-20261009/uart-rx-overlap-214527/`收到9条完整STATUS＋END，HELLO前后rx_faults=0，Flash/NVM未改；未ARM、未重复Owner按键，结束恢复FW151/UI67并关闭所有自身句柄。首次21:44验证脚本提前解析未换行HELLO的失败保留，脚本修成只解析完整行后才执行本次成功验证。验证只覆盖查询收发，不代表其他外设或整机验收。

v4 已构建未运行：`.cache/peripherals-20261009/ram-diag-v4/build.json`，bin SHA `b377ac2d572a7025d4fd27c889f7003300accf27bc437c5754a477d483861864`。它保留 v3 的触摸 100/50/25/10 kHz、Repeated START/STOP 两种读法矩阵及失败阶段，以及音频退出恢复进入命令前 HSE 软件请求的修正（原状态 HSEON=0、HSERDY=1，继承其他模块的请求），新增按键持续等待和事件保存。代码/data/BSS 共 85948 B，另留 24 KiB 栈。新增路径尚未实板执行，按键尚未 ARM，触摸降频和 BLE 尚无本轮结果。Owner 要求一次只确认一个硬件，当前只推进按键；须有真实恢复的访问条件后才能启动，不因等待回复重复连接。

08:34 Owner 要求先试按键后，一次 UART 查询仍 0 B；随后为绕过 UART 无回应，尝试只读 AP1 直接读取 PB14，工具在 init 拒绝，未取得 UID 或按键电平。原始 `key-entry-0833/`、`key-swd-entry-0837/`，按键仍未 ARM、未测，句柄已实际关闭释放。屏幕聊天修改了诊断引用的共享 SSD1681 驱动，v4 冻结源检查已不匹配，因此依当前源重建 **v5-key**：`.cache/peripherals-20261009/ram-diag-v5-key/build.json`，bin 36240 B，SHA `ac65dd5207c7e45cfaeadc371beb31d00fea2a1d9f6316f5cf7e65533770d2b3`，代码/data/BSS 85992 B，另留 24 KiB 栈；按键代码与 v4 相同。v5-key 同样仅已构建、未加载，恢复后只执行按键命令，不因合入共享驱动就重测其他外设。

09:19 正常 FW136/UI67/正确 UID 恢复后，共享屏幕源再次更新使 v5 冻结检查拒绝加载；未进 SWD 或写板。重新构建 v6-key，二进制仍为上述 SHA；09:20–21 已实际加载运行，内部 Flash/NVM 前后逐字节不变，09:21:08 `KEY_ARM` 实际成功。09:23/09:24 再次中断的原始数据在 `key-status-confirm-0923/`、`key-collection-interruption-092443/`，当时 VTref 报告 0.001588 V。已实际关闭并释放；最后曾运行 SRAM 诊断，当前退出状态未知。不能把历史 ARM 成功当作当前持续采集或按键通过。

09:32 Owner 明确“按了很多次了”。实际动作已完成，当前应记为**已操作但结果未能判定**，不能继续记未操作或0事件。只读原状态时UART仍0B；另准备冻结v6只读代码验证后提取原RAM变量，但09:34 AP1在init拒绝，未到UID/代码验证或RAM读取。没有重新ARM清零或复位，不能断言旧记录已丢失。原始`key-owner-many-presses/`、`key-preserved-ram-093440/`，已实际关闭并释放，不请求Owner继续盲按。

现有产品固件及资源不由此目标覆盖。共享操作和后续实际结果使用项目根目录 `docs/board_operations.md`、`docs/development_log.md`，不另建独立日志。

## 结构与边界

- MCU 固定为 STM32WBA55CE、512 KiB Flash、128 KiB SRAM，UID `180010000d50335754363720`；只用 V3 SN `004400403532510B31333430`。
- 所有 LOAD 段都在 SRAM `0x20000000` 内；预留 24 KiB 栈。构建工具检查段地址、向量和内部 Flash 写 API 未链接。
- 启动使用 HSI16 和 LPUART1，随后等待命令。不启动产品应用、BLE 或全套外设；不改 SMPS/VOS。
- 仅音频命令启用现有 49.151855 MHz 名义音频时钟及其 SAI/DMA；CPU 保持 HSI16。结束关闭本命令的 SAI/PLL，恢复先前的 HSE 软件请求；其他模块继承的 HSE 请求不冒充本命令泄漏或整机低功耗达标。
- 保留屏幕常供电：不复位 TCA、不切 P4、不假装 EPD_RES 有实际连接。屏幕测试复用当前 SSD1681 驱动的 8 bit SPI、软件复位与 BUSY 完成要求，不另造波形。
- 默认 NOR 只读。独立写入命令仅限最后一个动态区扇区 `0xFFF000/4096B`；校验当前布局根后，保存该扇区、两种图案擦写读回，再恢复并逐字节校验。加载时及执行该命令前必须确认没有活跃 OTA／回滚占用。开发录音可清空的 Owner 授权继续适用；此程序不擦静态资源、元数据、内部固件或配对 NVM。
- 保留现有看门狗并持续喂狗；不改 option bytes、发布密钥、云端或付费服务。

## 构建、加载、采集和恢复

在 `Companion-Firmware` 目录中构建：

```powershell
python tools/build_wba_peripheral_diag.py --output .cache/peripherals-20261009/ram-diag-NEW
```

`build.json` 中 `BUILT_NOT_RUN` 只表示构建。共享记录取得独占时段，正常应用模式要求完整正常 UART 且录音／BLE／存储／升级空闲。占用行须包含执行聊天 ID 和 `peripheral-ram-diag`；写入测试还须有依据记录 `ota-idle-confirmed`。

```powershell
python tools/load_wba_peripheral_diag.py --build .cache/peripherals-20261009/ram-diag-v7-uart-rx/build.json --output .cache/peripherals-20261009/ram-load-UNIQUE
python tools/capture_wba_peripheral_diag.py --command IO --lead-in-seconds 0 --output .cache/peripherals-20261009/io-UNIQUE
```

为将外设检查与完整应用启动分开，另有 `--boot-loop-only --installed-image <最后实际安装的boot+app.bin>` 模式：同次 UART 必须只显示至少五个完整 BOOT0/jump_app 循环且没有 BOOT1/DIAG1；停核后还须逐字节核对所给已装镜像（配对 NVM 前的完整范围）。无 live 场景、已有正常应用、任一 DMA 活跃、身份或镜像不符，均拒绝加载。该模式不调查复位／电源原因，不允许绕过缺失 UID 或调试器的连接保护。

加载器使用独立 AP1 配置（RM0493 §43.4：AP0 为系统调试口，AP1 为 Cortex-M33 访问口），核对实际 UID、容量、TZEN 后才停核，检查全部 DMA 通道已关闭，再加载／读回 SRAM。内部 Flash 含配对 NVM 前后比较，并在运行前再与原始内部快照核对。必须收到匹配 UID 的诊断 HELLO，才能记录“已在运行”。2026-10-09 首次入口尝试发现原 AP0 配置读核心标识为 0，已修正为 AP1；实板执行结果仍以实际输出为准。不可访问时结束一次，不强行绕过工具连接保护。启动后四秒没有 HELLO 会在同一调试会话请求回原产品；加载进程异常超时则保留目标状态未确认，不能自动假设已恢复。

每次采集输出串口原文和 JSON。麦克风额外输出左右两个 WAV。其他命令有默认 15 秒准备时间，但不能据此并排启动多个操作者窗口；先确认当前这一项的动作和结果，再决定下一项。代码内部的数据分析由 agent 判断，不要求 Owner 据日志／哈希／状态码验收。

### 按键：先实际 ARM，再只请 Owner 操作这一项

Owner现场操作优先从统一入口打开原生窗口并同步启动后台，避免先弹窗、后准备程序造成空等：

```powershell
python tools/start_wba_key_operator.py --build .cache/peripherals-20261009/ram-diag-v7-uart-rx/build.json --output .cache/peripherals-20261009/key-popup-UNIQUE
```

窗口启动后先取独占、辨认当前产品或SRAM诊断；已有诊断保留ARM，正常产品仅走现有受保护的临时SRAM加载器。真实持续采集已ARM且最近回应有效才显示绿色、允许Owner操作；本轮计数减去连接时的基准，旧事件继续保留。没有操作倒计时，完成后点“我已按完”，程序保存反馈与数据、取最后状态/STOP并尝试返回正式产品，关闭实际句柄后释放。未取得身份显示尚未启动；状态查询缺少完整回应单独显示“状态查询超时”，保留已收事件，不由此判主板掉电。只有Owner显式点击才尝试下一次连接，不循环重连。21:23已真实持续采集并经原状态读回确认按键基础响应通过；09:50窗口UART0B及更早准备期间关闭的反馈原样保留。

优先使用新的 `tools/capture_wba_key_live.py`，在板端 v4 或后续 v5/v6-key 已确认运行后持续保持 UART。唯一占用行除聊天 ID 和 `peripheral-ram-diag` 外，还须含本次输出目录名 `key-live-UNIQUE`，绑定该采集阶段。工具先核对诊断 UID，读取 `KEY_STATUS`；已有 ARM 就保留事件，仅未 ARM 时发一次 `KEY_ARM`。收到当前成功状态并且采集进程仍在运行，才通知 Owner 按键。

```powershell
python tools/capture_wba_key_live.py --output .cache/peripherals-20261009/key-live-UNIQUE
```

每个新按下／松开事件立即写入电脑 `uart.log`、`key-events.jsonl` 并同步到文件；每两秒读当前状态，关联主机时间和板端时间，不重新 ARM。无操作者截止时间，等真实操作完成回复后，agent 在本次输出目录创建 `stop.request`：工具取最后状态并 `KEY_STOP`，关闭 UART，agent 再恢复正式产品并释放。任一回复缺失就保留原文、结束一次，不自动重连／复位／安装；失败时实际关闭 UART 后只释放与本输出目录对应的自身占用，目标状态仍记未知。此工具不因三次计数就自行宣布实物通过。21:23实际运行保存20个事件，21:28完整取回原ARM状态后结合Owner真实完成反馈判定通过；UART接收修正的实板验证单列，不改写原超时失败。

保留单命令方式：以 `--lead-in-seconds 0` 发 `KEY_ARM`，确认返回 `ARMED_AWAITING_OPERATOR`。这一步之前不要请 Owner 按键。板端持续轮询 PB14，15 ms 去抖；串口关闭后也继续采集，并保存前 12 个事件及总按下／松开次数，但主板掉电会丢失这些 RAM 记录。等待 Owner 完成三个短按／松开的真实回复，然后发 `KEY_STATUS` 读取保存的变化。未操作、等候时间长或 `AWAITING_OPERATOR` 都不判故障。

```powershell
python tools/capture_wba_peripheral_diag.py --command KEY_ARM --lead-in-seconds 0 --output .cache/peripherals-20261009/key-arm-UNIQUE
# 只有确认 ARM 后才提示 Owner 操作，并等待其真实回复；不在这里接续倒计时。
python tools/capture_wba_peripheral_diag.py --command KEY_STATUS --lead-in-seconds 0 --output .cache/peripherals-20261009/key-status-UNIQUE
python tools/capture_wba_peripheral_diag.py --command KEY_STOP --lead-in-seconds 0 --output .cache/peripherals-20261009/key-stop-UNIQUE
```

等候时仍保留实板占用，不能将正在采集的诊断交给另一聊天。不要再次 `KEY_ARM` 清掉尚未读取的证据；有异常保留当前事件，先处理本项。采集停止及恢复正式产品后再按实际句柄状态释放。

诊断结束后用现有串口恢复原产品，确认正常产品 UID/UI：

```powershell
python tools/capture_wba_peripheral_diag.py --command RESET --lead-in-seconds 0 --output .cache/peripherals-20261009/ram-return-UNIQUE
```

恢复命令不写内部 Flash；未收到完整产品帧时保留恢复未确认。所有句柄实际关闭后，在共享记录明确释放。诊断运行期间不能交给另一聊天当正式产品使用。

## 每个外设的实物确认依据

| 项目 | 命令／采集 | 必须检查的真实行为 |
|---|---|---|
| 实体键 PB14 | `KEY_ARM` → 等待 Owner 实际完成 → `KEY_STATUS` → `KEY_STOP`，无操作者截止时间；旧 `KEY` 仅保留为有界采集入口 | 三次真实按下／松开均有去抖后的变化，空闲不自发触发；Owner 未按不判故障 |
| TCA6408A | `IO`；结合触摸／IMU／短音 | P0 触摸输入、P3 IMU 输入及主控 INT、P1 触摸 RESET、P6 功放使能的端点效果；寄存器读回不能单独合格。P2/P5 充电信号、P7 电池采样交硬件电源排查，P4 实板禁用开关不能当可切换输出验收 |
| FT6336U | `TOUCH_MATRIX`；必要时仅一次 `TOUCH_MATRIX_RESET`；再选 `TOUCH100/50/25/10` 或对应 `_STOP`，40 秒 | 矩阵每个名义频率、每种读法 32 轮 ID/接触寄存器读取，记录失败阶段／HAL／ISR／GPIO。之后做四角、中心的按下／移动／松手。NACK 保留原错误，不因降频后一次 ACK 就合格；低速诊断超时为 30 ms，不能沿用产品 4 ms 超时直接跑 10 kHz |
| LSM6DSO | `IMU`，45 秒 | 六面重力轴及符号、三轴旋转响应、静止合理性、连续数据和 INT1／扩展器路径；不是仅 WHO_AM_I。主机输出各轴范围和六面稳定时段，不能冒充校准精度或内建自检 |
| W25Q128JW | `NOR`；满足动态区占用条件才 `NOR_RW_LAST_DEV_SECTOR` | ID／容量、多个地址实际读取及两个图案的擦写／逐字节读回／原内容恢复。此写测试只覆盖一扇区，不可称全片每一单元通过 |
| SSD1681 墨水屏 | `EPD`，一次 full 后一次 Mode2 | 棋盘图案和反相图案都真实显示、区域正确、无缺列／大片残留；同时必须观察 BUSY 有效开始和结束。软件事务完成还需实际看屏幕；首次 full 仍遵守已有刷新间隔策略 |
| MAX98357A＋扬声器 | `SPEAKER` | 500／1000／1500 Hz 三个短音实际可听、顺序正确、无明显破音；DMA 全部完成及 P6 恢复。听到声音前不能只凭 speaker_ready 合格 |
| 两只 SPH0655 | `MIC`，先安静、再实际声源，分别检查两路 WAV | 两路各自对真实声源有响应、无卡死位／全零／复制通道／持续削顶。每次采集 80 ms 原始 PDM，首 10 ms 用于启动滤波，左右各输出 70 ms PCM；短片段不能冒充正式实时录音、音质或无丢帧达标 |
| MCU 内置蓝牙／射频 | 原有正式产品链路 | 真实连接、实际数据传输、断链恢复及正常配对；此 SRAM 目标没有 BLE 栈，不给无线通过结论 |
| 电池、充电和电源相关信号 | 硬件同事负责 | Owner 已确认充电芯片损坏并交同事排查；本诊断不继续电压／充电／电源根因调查，也不把未供电的端点误判为外设自身坏 |

硬件改版结论须区分“已确认可用”“有具体功能失败”“尚未测到”。电路连接检查只能说明设计或布线事实，不能替代这些实物结果。

## 给硬件同事的触摸结论

目前应描述为“FT6336U 的 I²C 间歇通信故障”，不能直接说触摸 IC 损坏。旧 FW136 曾读到身份和接触，随后轮询 NACK；当前只读到软件层错误，尚没有失败事务的示波器／逻辑分析仪波形。名义 100/50/25/10 kHz 的独立对照程序已构建，供电／接线恢复后才能执行。修改的是哪颗电阻、原值和现值尚待确认。

若调整的是 SDA/SCL 上拉：阻值调大降低拉低负担，但普通 RC 上升沿会变慢；本板还有 TXS0104E，其两侧各有内部 10 kΩ 上拉及边沿加速，必须看外部上拉与内部上拉的合成效果。应在失败事务同时看转换器两侧 SDA/SCL 的高低电平、上升沿和 ACK，并核实 RESET、OE 和对应供电是否稳定。降低频率是定位对照，不能单凭改电阻／改频率推断根因。

资料：[TI I²C 上拉计算](https://www.ti.com/lit/an/slva689/slva689.pdf)、[TXS0104E 数据手册 §8.3/§9.2](https://www.ti.com/lit/ds/symlink/txs0104e.pdf)、[STM32WBA RM0493 §43.4 访问端口](https://www.st.com/resource/en/reference_manual/dm00821869.pdf)。
