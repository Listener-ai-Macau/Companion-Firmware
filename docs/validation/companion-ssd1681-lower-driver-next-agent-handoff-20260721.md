# SSD1681 下位驱动完整交接

日期：`2026-07-21`

当前需求：`COMP-REQ-320`

当前状态：`OWNER_PAUSED / R10 PLANNED BUT NOT STARTED`

范围：`Companion-Firmware` 的 WB55 + ESP32-FTS02 + replacement display FPC +
GDEY0154D67-T03/SSD1681 production-off 下位驱动。上层 V9/Rig/CRIG、浏览器、
美术、表情绑定、触摸、BLE、录音和 production 刷新策略均不在本交接的改动范围。

## 0. 先读这个结论

owner 已暂停所有 R10 implementation、build、flash、Execute 和实板候选工作，只要求完整交接。
`COMP-REQ-319` 的“真实移动球”只保留为未来计划，已被 `COMP-REQ-320` 暂停。
中断时仅出现过未构建的 R10 预处理宏和静态 oracle 草稿；它们已全部删除，当前没有 R10
driver/tool/artifact，故 R10 的真实状态是 **NOT STARTED**，不是 MACHINE_READY。

最后一次硬件接触是 R9 continuous R2：机器 16/16 通过，W/A/B/A 连续循环 1060 次，owner
在唯一验收窗选择 `失败`，因为它不像一个连续移动的球。随后双平面 White post-clean、524288
字节 raw application 精确恢复/readback 和 normal resume 全部通过，相关进程全部退出。此结果是：

- R9 波形/命令/生命周期：`MACHINE PASS`
- W/A/B/A 视觉拓扑：`HUMAN FAIL`
- 真实球 R10：`NOT RUN`

## 1. 状态词必须严格使用

| 标记 | 含义 |
|---|---|
| `MACHINE PASS` | 机器证据满足该合同；不等于人眼通过。 |
| `MACHINE FAIL` | 机器门失败；不得打开视觉验收或继续候选。 |
| `HUMAN PASS` | owner 对该次限定问题通过；非空备注仍是合同。 |
| `HUMAN FAIL` | owner 视觉拒绝，机器通过不得覆盖。 |
| `NOT OBSERVED` | 没有足够观察，不能推导视觉性质。 |
| `NOT RUN` | 候选或阶段没有执行。 |

## 2. 产品与来源边界

### 2.1 面板身份

- Good Display 公共页/样例：`GDEY0154D67-T03`、`SSD1681`、`200x200`。
- owner 对话照片可读到：`0154BN-D67-D2 N524110506`，且 FPC 已接适配板。
- supplier transcript 把同一 marking 与 T03/SSD1681 关联。
- 原始照片未归档成本地文件，不能提供图片 SHA。
- `GDEH0154D67-20211203-P-LUT(1s)` source tree 不含 `GDEY0154D67-T03` 字符串，
  也没有 temperature-banded CWF1 表或数值常温范围。

因此，身份关联足够支撑受控、production-off 研究，不足以声称 production CWF1、温度覆盖或
无限次局刷保证。

### 2.2 只读供应商输入

`C:/Users/Billy/Desktop/GDEH0154D67-20211203-P-LUT(1s) -1s快刷/EPD_W21/EPAPER.c`

SHA-256：`7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896`

禁止修改、移动、删除、格式化或从网络/相邻面板拼接波形。

### 2.3 上层保护

- locked V9 source：`919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA`
- owner acceptance：`8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227`
- 下位实验不得修改 V9、Rig、CRIG、browser、art、expression binding 或 production default。

## 3. 159 字节供应商 LUT

原始 compiled about-1s LUT SHA-256：
`F83EA7360CFFF04FE9D004A75858A46213CBD710AAA2F0C4A62597E3EA176D15`

- 总长：159 bytes。
- bytes `0..152`：通过 `0x32` 写入，共 153 bytes。
- bytes `153..158`：不是 `0x32` payload，而是 tail `22 17 41 A8 32 58`：
  `0x3F=0x22`、`0x03=0x17`、`0x04=0x41,0xA8,0x32`、`0x2C=0x58`。
- bytes `0..59` 是 LUT0..LUT4 voltage tables；后续包含 TP/SR/RP/FR/XON 等字段。
- voltage byte 的 A/B/C/D 顺序为 D7:D6、D5:D4、D3:D2、D1:D0；
  `00=VSS/DCVCOM`、`01=VSH1`、`10=VSL`。

不能混淆下列命令模式：

1. 官方 ordinary full：单平面 5000-byte `0x24`，`0x22=0xF7`，`0x20`，BUSY。
2. supplier BaseMap：5000-byte `0x24` + 5000-byte `0x26`，两平面后再 activation。
3. external-LUT full：`0x32` 153 bytes + tail，`0x22=0xC7`，`0x20`，BUSY。
4. supplier ordinary partial：reset 10/10 ms，`0x3C=0x80`，local current-only `0x24`，
   `0x22=0xFF`，`0x20`，BUSY；不加载 `0x32`。
5. R9 research：R9 159-byte LUT，local fixed-bank old/new，`0x22=0xCF`，`0x20`，BUSY。

## 4. 电源、FPC 与已接受事实

旧断裂 FPC 上的历史结果是 `HUMAN FAIL`：PREVGH1 约 3.3 V，PREVGL1 最低 4.2 mV，
屏幕无变化/颗粒。它必须保留，但不能继续作为 replacement FPC 的诊断。

replacement FPC 证据：`MACHINE PASS`。owner 报告 replacement display FPC 已安装、逻辑供电仅
3.3 V、当前动态表情可见。artifact：
`docs/validation/companion-screen-wb55-replacement-fpc-evidence-20260720.json`，SHA-256
`E1124866DBBBF083B3512EB75A4C8AE14BF6808ACCDD45B774A5095BD41D7D35`。

replacement FPC White/rail：`MACHINE PASS + HUMAN PASS`。30 个 reset-bounded White cycles，
每次 1288 ms，PREVGH1 `+20.0 V`、PREVGL1 `-20.0 V`、`uniform_white`。artifact：
`docs/validation/companion-screen-wb55-white-rail-measurement-current-source-r2-20260720.json`，
SHA-256 `827DC52B8E7CA8CF0BF0B6E5CC2A64D37F3B1F69C1B73E4D2CED2CA7E6C51A8C`。

这只接受 current FPC 的官方 White/Black/rail prerequisite，不接受 fast LUT、局刷、正常表情或 production。

## 5. 当前最佳视觉基线：COMP-REQ-236/237

状态：`MACHINE PASS + HUMAN PASS`，但带明确缺口。

拓扑：

1. erase-old：previous-black byte bbox，CPU-held current bytes 写 `0x24`，独立
   reset/border/`0xFF`/`0x20`/BUSY。
2. draw-current：old/new difference union，current bytes 写 `0x24`，第二次独立 completion。

每次 activation BUSY `446-447 ms`。接受事实：有可见移动、旧位置 hatch/residue 不再反复出现、
没有整屏黑闪。owner 原话：

`好很多, 就是移动的时候移动方向会切掉一点, 随后还原, 能优化吗`

缺口机制已经被 R7 truth table 证明：对 new-only pixel `P=1,N=0`，第一次 erase activation 后
理想中间态是 `P OR N=1`，新位置仍为白；第二次 activation 才变为 `N=0`。因此“移动方向被切一截”
是真实的两次完整 activation 之间的光学中间态，不是 SPI 少字节或 BUSY 未等完。

artifact：`docs/validation/companion-gdey0154d67-t03-vendor-partial-no-union-settle-operator-20260720.json`

SHA-256：`DA2FE11DB4CB1AFC5D433B2798BADBB576FC9C82BB39C472236E084C48F1EC57`

它是 quality floor/reference，不是必须照搬的 architecture，也不是 production admission。

## 6. 所有相关 partial topology

| 拓扑 | Machine | Human | 结论/原话 |
|---|---|---|---|
| cleanup then draw/no-union | `MACHINE PASS` | `HUMAN PASS` | `这个感觉相当好...但是球可以不要消失再出现吗...没有残影了`；无残影但消失再出现。 |
| old-or-current union -> current settle/draw-final | `MACHINE PASS` | `HUMAN FAIL` | `可以, 但是有一帧会出现残影`；以 residue frame 替代 empty gap。 |
| current union -> old settle | `MACHINE PASS` | canonical `NOT OBSERVED`；async `HUMAN FAIL` | popup timeout；后续 `没修好, 吃掉的部分越来越多了`。 |
| removed-black repair -> current union | `MACHINE PASS` | `HUMAN FAIL` | `以前是消失一小节，现在是消失一大节`。 |
| disjoint current-only r4 | `MACHINE PASS` | `HUMAN FAIL` | `没看见, 再跑一次, 另外球大一点`。 |
| disjoint current-only r5 | `MACHINE PASS` | `HUMAN FAIL` | `你现在没有在移动?`。 |
| disjoint current-only r6 | `MACHINE PASS` | visibility `HUMAN PASS`；residue criterion `HUMAN FAIL` | `直接移动是会有残影的`。 |
| disjoint erase-first no-union settle | `MACHINE PASS` | `HUMAN FAIL` | 无残影，但 `吞掉一截再补全` 仍在。 |
| added-first old-cleanup | `MACHINE PASS` | `HUMAN FAIL` | `其它的残影更多了`、`方向不对`，原 cutoff 也在。 |
| explicit `0x26=P` + `0x24=N` + one FF activation | `MACHINE PASS` | `HUMAN FAIL` | black residue 跟随移动；R7 证明它不是新候选。 |
| post-activation fixed `0x24` sync Phase B | `MACHINE PASS` | `HUMAN FAIL / NOT OBSERVED` | `没有看见移动, 另外整个屏幕都很脏`；后来澄清是不确定，不是永久否定。 |
| fast post-sync R1 | `MACHINE PASS` | `NOT OBSERVED` | 120/120，522-523 ms/frame，BUSY 447 ms；屏幕无变化。 |
| fast post-sync R2 inverse-seed | `MACHINE PASS` | `HUMAN FAIL` | 120/120；仍无反应，inverse-seed 假设被实板证伪。 |

## 7. Phase A、R7 与 R8

### 7.1 Phase A RAM fingerprint

`MACHINE PASS`，人眼 `NOT RUN`。12 次 selector read：

- activation 前，`0x24=N` staging 后：selector0=N、selector1=P。
- activation 后，无额外 RAM write：selector0=P、selector1=N。
- partial BUSY：447 ms。

这只证明 selector-visible content swap；不能由此推导 activation 后 `0x24/0x26` 写到哪个物理 bank。

### 7.2 R7

research audit 为 `MACHINE PASS`，新 visual candidate `NOT RUN`。最终状态：

`NO_GO_R7_POST_ACTIVATION_SYNC_TARGET_UNPROVEN_NO_NEW_VISUAL_CANDIDATE`

- explicit `0x26=P + 0x24=N + one FF/20` 已跑且视觉失败，不能包装成新候选。
- fixed `0x24` post-sync 共执行 264 次/3 runs，但 post-write selector readback 为 0。
- fixed `0x26` sync 和 selector-aware sync 都是 `NOT RUN`；这只是 evidence gap，不是自动候选。

### 7.3 R8 launcher incident

外层 tool timeout 断开 stdout pipe，child 继续。inner artifacts 证明 pre/post-clean、raw restore、
normal resume 是 `MACHINE PASS`；但 candidate start 从未调用，candidate/programmer write counter=0，
swap/tag/mapping experiment `NOT RUN`。空 recovery response 必须保持为空，不能伪造选择。

### 7.4 R8-R2 fixed-bank readback

`MACHINE PASS`，human `NOT RUN`，零 popup：

- `0x24 -> selector0`
- `0x26 -> selector1`
- swap 后 selector0=base，selector1=current
- 28 selector responses，1 次 known swap（447 ms），0 次 post-tag activation，0 retry

runtime：`docs/validation/companion-ssd1681-ram-command-target-r8-r2-runtime-20260721.json`

SHA-256：`BAD97BBABFD2E1B515A2E1D1A45EE3C4E68EF3FFC167D03468E1859659C07FF5`

R8-R2 one-shot 已 consumed；不得重跑。

## 8. Custom LUT R1-R6

所有候选 tail 均保持 `221741A83258`，production-off，最终均未被视觉接受。

| Round | LUT SHA-256 | 单变量 | Timing/Machine | Human |
|---|---|---|---|---|
| R1 | `B0C729D4157054C4EA69521C3E4837B75B2E6A7740A48C5C754714A84925722E` | 清零 supplier stationary BB/LUT0 bytes 0..3 与 WW/LUT3 bytes 36..39 | `MACHINE FAIL`：9 次 1284-1285 ms，超过 600 ms | `HUMAN FAIL`：`你先刷全白恢复游一下?`；且 popup 在 Execute 后才开，时序错误。 |
| R2 | `EBF88D6FB0BEB39AB2428C98BBDF1DC04308CEA156AF61D14C2B1591902B64C7` | active TP total 50 -> 20 | `MACHINE FAIL`：首步 602 ms | `NOT RUN` |
| R3 | `CFE301B8FAA15C09B55509C9110E014FB49B959AD40FDF73F062A84D9D6769D3` | offset74 `02->01`，TP20 -> TP19 | `MACHINE FAIL`：仍 602 ms，量化 plateau | `NOT RUN` |
| R4 | `75D7647188ACF1C79BC37313DC40105AF4445B9B6F422AD4FDAF0A465413984D` | symmetric uniform TP16，offset61/64/75/78 `02->01` | `MACHINE PASS`：9/9，598-599 ms | `HUMAN FAIL`：`不太行, 屏幕很杂` |
| R5 | 同 R4 | candidate byte-identical；只把 pre/post-clean 改为 dual-plane + readback | `MACHINE PASS`：两 bank White、9 activations、精确恢复 | `NOT OBSERVED`，owner 选失败：`没看见...下次搞连续的变动` |
| R6 | 同 R4 | R5 chain 9 -> 16，去 countdown/dwell/in-window verbose UART | `MACHINE PASS`：16 x 599 ms，9633 ms | `HUMAN FAIL`：`方向是错误的, 没有图案了直接` |

### stale-bank 发现

R4 preclean 只初始化 full-plane `0x24`；每次 candidate 只局部写 `0x26/0x24`，而 reset/`0x12`
不清 RAM。窗口外 stale opposite bank 在 full-panel Mode2 activation 下足以解释整屏脏，但不是已证因果。
R5 首次把 pre/post-clean 固化为 dual-plane 并读回两 bank 全白；R5 又因 owner 没观察到候选而没有
得到 cleanliness 结论。以后 raw Flash restore 绝不能代替 panel post-clean。

## 9. R9 lineage

### 9.1 Workbench

artifact：`docs/validation/companion-ssd1681-phase-parallel-r9-workbench-20260721.json`

SHA-256：`E7311523D6FE571434F0C1F2D5EC76B7ED9B64DC725B0726DDEC023421D7E4EF`

状态 `ADMIT_ONE_VARIABLE_R9`（research `MACHINE PASS`，human `NOT RUN`）。R9 LUT：

`9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD`

机制：保留 supplier TP `5/3/5/3`，在同一 timing phase 中并行放置可追溯的 BW/WB opposite-polarity
VS fields。BW/WB 各有 16 effective counts，正/负各 8，net source-frame impulse=0；WW/BB=0；
tail 不变。它是 production-off admitted diagnostic waveform，不是 production CWF1。

### 9.2 R9 one-shot

- `MACHINE PASS`：16/16 local 32x32 activations；BUSY 597-599 ms；CF/20/post-sync 各 16；
  full-frame/F7/C7/FF/retry/motion 均 0。
- `HUMAN FAIL`：`你这个应该要一直运动才行，因为我也不是一直在屏幕前的。`
- note SHA：`E2EDDD3239D7FE8E195D266040B0C1800D585887788FE64D9D6B772692928E56`
- HEX：`724DA17F385756BA779739E73DA47131F563E0C071A2EB173F5F77871F3CADDF`
- runner：`0B0A536E7B03DD5F2A4F9CF7B2B76A1B0DB3F34745172E352CB0B4726011B34B`
- runtime disposition SHA：`B5A1248CE91170631C025B8D7639D8786DBF039DD0917AD32B05A25412A8DC3D`

这次失败是观察呈现不连续，不是否定 R9 机器门。authorization 已 consumed。

### 9.3 R9 continuous R1 supervisor incident

- qualification：`MACHINE PASS`，16 steps，BUSY max 599 ms。
- loop：`MACHINE PASS`，1 record，597 ms，bounded ring 10736/65536 bytes。
- visual：`NOT OBSERVED`；popup `NOT RUN`，无 selection/note。
- 根因：PowerShell line 126 把两个未分别括号包住的 `Test-Path -LiteralPath` 用 `-or` 相连，
  导致 `-LiteralPath` 重复绑定；supervisor 在 guard/popup 前退出。
- runner fail-closed stop，pre/post-clean、524288-byte restore、normal resume 全部 `MACHINE PASS`。
- disposition SHA：`976018FA78CAE8B17B4A06D0AD2CC415DC72598AAE087F5F041B16C3040631DD`

R1 authorization 已 consumed，绝不是视觉失败，也不得重试。

### 9.4 R9 continuous R2 最终结果

- fixed supervisor SHA：`39ACC31A561413717B77ACAFE5E7E562B0C44734F07D72007B46C900C85883D2`
- MACHINE_READY SHA：`59DA81BDCDC31AB93459BFCA6575F5A007182374912D1A476B54B747A106D5E7`
- candidate HEX：`3B416BFF08B630D23BDB6107B2C17DFE9FBBFAAA7D5CFBCA5063AE68E62B79C5`
- qualification：`MACHINE PASS`，16 steps，BUSY max 599 ms。
- loop：`MACHINE PASS`，1060 contiguous iterations，last=1060；ring=65536 bytes；归档 tail=931..1060。
- 唯一 canonical popup：1 次。
- owner：`HUMAN FAIL`，note：
  `呃，这样子的话就不是一个连续的球在运动，作为那个连续球运动的东西。\r\n`
- note SHA：`30DDA3C9CC92110E636C9954652716EA805086DD15E889ED26B4F88D720B5698`
- post-clean、exact restore、normal resume：`MACHINE PASS`。
- runtime disposition：
  `docs/validation/companion-ssd1681-phase-parallel-r9-continuous-r2-runtime-disposition-20260721.json`
- disposition SHA：`C7F097CE905AA84F687C9E2EC6E5FEAEDED8D0D6C9C98DF8E09F3624797DE0CA`

这条 note 只拒绝 W/A/B/A stripe payload topology；没有拒绝 R9 LUT、fixed-bank mapping、CF/20、
BUSY gate、one-activation loop、post-sync、supervisor、cleanup 或 restore lifecycle。authorization 已 consumed，
无 retry、motion、promotion、activation。

## 10. Popup policy 演化

控制规则来自 `COMP-REQ-305`：

- machine-only R8 等流程：0 popup。
- routine White pre/post-clean、recovery、restore、normal-resume、fault/machine failure：0 popup。
- visual candidate：机器门完成后才可出现 exactly one final canonical Chinese acceptance popup。
- R9 continuous 的唯一 popup 在 16/16 qualification 后与观察 loop 并发，仍是 final acceptance popup。
- 不再出现 start、countdown、reminder、cleanup、recovery 或 fault-ack popup。

canonical process tree：supervisor -> `pwsh aiw.ps1 operator-prompt` + conhost -> STA
`operator_prompt.ps1` + conhost。这个 tree 是一个 popup，不是多个 popup。

## 11. 清理与精确恢复合同

每个未来硬件候选无论 PASS、FAIL、abort、exception 都必须：

1. promptless dual-plane preclean：`0x24 5000xFF`、`0x26 5000xFF`、`0xF7/0x20/BUSY`。
2. selector0/selector1 各读两次；每次先重新写 full window/counter；5000 payload bytes 全 `FF`，repeat-identical。
3. 候选结束立即重复同一 promptless dual-plane postclean。
4. 恢复 pre-run captured `0x08000000` 起 524288 bytes，upload/readback 必须 byte-identical。
5. 要求 normal boot/ready resume。

当前 protected restore SHA：
`223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C`

raw MCU Flash restore 只恢复应用，不会清 retained pigment 或 controller RAM，绝不能替代 postclean。

## 12. Runner、PowerShell 与 timeout 陷阱

1. `Test-Path` 与 `-or`：每一个 `Test-Path` expression 必须单独加括号。
2. Win32_Process audit：必须排除 audit PowerShell 自己的 `$PID`；它的 command line 含 run root，
   曾两次造成假阳性。
3. 不能只按历史 PID 数字判断存活；Windows 会复用 PID，必须同时比对 name、command line 与 creation
   identity。最终审计中历史数字 34332/10652 已分别属于无关 WebView/RuntimeBroker，不是 run process。
4. Execute 只用 persistent hidden `Start-Process` launcher，stdout/stderr 先落 durable file，记录 PID、
   args、locked hashes、fresh output root。直接 launcher/外层 timeout 会丢 stdout，child 仍可能继续。
5. 不要只看 runner exit code。owner `失败` 后 runner 可有预期 nonzero diagnostic gate，但 cleanup/restore/
   normal resume 仍 PASS；必须读 `stage-run.json`、`restore-gate.json`、`normal-resume.json`。
6. stable artifact 必须 normalize timestamps/PIDs，并固定 verifier cache path 后再 hash。
7. prompt timeout=900 s；其余 wait 也必须 bounded/fail-closed。
8. R9 ring 固定 65536 bytes。`qualification-and-ring.json` 是 initial gate snapshot；总 loop count 要看最终
   `monitor-result.json`。
9. 长 `functions.exec`/shell session 必须 wait 到 terminal；不得留下 runner/monitor/supervisor/prompt/
   programmer process。
10. output root reuse、consumed authorization reuse、hash drift、Execute simulation injection、automatic retry
   都必须 fail closed。

## 13. 绝不能重跑

- 仅为“确认”而重跑已接受 COMP-REQ-236/237。
- draw-final old+new residue、current-union->old-settle、removed-black->current-union、
  disjoint-no-union duplicate、added-first old-cleanup。
- explicit `0x26=P + 0x24=N + one FF` direct topology。
- Phase-B/fast post-sync R1/R2/inverse-seed。
- custom LUT R1、R2、R3、R4、R5、R6。
- R7 duplicate candidate。
- R8 incident、R8-R2 consumed authorization。
- R9 one-shot、continuous R1、continuous R2 consumed authorizations。
- 任何旧 authorization、旧 output root 或未有新 registry/root authorization 的候选。

## 14. 当前设备、进程与工作树

最后一次设备状态：R9 continuous R2 后 dual-plane postclean PASS、524288-byte restore/readback PASS、
normal application resume PASS。交接阶段没有查询、flash 或接触设备。

`2026-07-21T23:21:17+08:00` 的 PID audit（排除自身 PID）对 R2 run root、runner、monitor、supervisor、
`operator_prompt.ps1`、`STM32_Programmer_CLI` 的匹配为 `[]`；known run PIDs alive=`[]`。
历史 PID 数字 34332/10652 已被无关 `msedgewebview2.exe`/`RuntimeBroker.exe` 复用，不能算 run alive。

交接阶段：`hardware_contact=0`，`popup_count=0`。

工作树约有 1432 个 dirty entries，包含并发上层 agent/owner 变更。规则：

- 不得 `git reset --hard`、`git checkout --` 或删除/移动不相关文件。
- `panel_target_stm32wb_ssd1681.c` 含全部下位历史；只删除了本次 R10-only scaffold，不能回退到 HEAD。
- 遇到 V9/Rig/CRIG/browser/art/touch/recording 变更一律视为他人所有，不覆盖、不清理。

## 15. R10 方向：计划但 NOT STARTED

唯一预期变量是 payload topology：把 W/A/B stripe 改成一个完整移动球；R9 waveform/tail、fixed-bank、
CF/20/BUSY、post-sync、bounded ring、supervisor、promptless cleanup、exact restore 全保持。

临时几何计划：`12x12` solid black，`y=80`，x=`32,40,48,56,64`，stride=8 px，travel=32 px，
ping-pong；每帧一次 activation，不能 erase/draw 各一次。

### 必须先回答的 admission questions

1. owner 说的“球”必须是视觉圆盘，还是 12x12 solid square 也可？不得自行推断。
2. y=80、x=32..64、8 px byte-aligned stride、32 px span 是否满足可见性？
3. initial White->ball 与 first 16 qualification 的 exact position sequence 是什么？
4. 每个 landing 是否必须保持完整 12x12，8 px 移动带 4 px overlap？
5. 当前 supervisor/status schema 名称写死 R9；“unchanged supervisor”是允许 compatibility wrapper，
   还是必须 versioned R10 supervisor？
6. 16/16 后与 loop 并发的唯一 final acceptance popup 是否仍是 owner 要的边界？

### 暂停解除后的顺序

1. registry-first 记录上述答案和新合同。
2. 重读 workflow skill/quickstart、registry/current-goal、本交接，并审计 dirty ownership/hashes。
3. 先做 pure full-frame pixel oracle：完整球、position path、full previous/current hashes、byte-aligned union、
   transition counts、exact first-16 sequence。
4. 再实现 default-off R10 driver，payload topology 以外不变；source/static 审完前不 build。
5. 加 parser/monitor/supervisor/persistent launcher/CheckOnly 和 negatives，保留 bounded ring/forbidden zeros。
6. isolated build 与 stable R10 MACHINE_READY；此阶段仍 `hardware_contact=0`。
7. 回 root；只有新 one-shot authorization 绑定 exact MACHINE_READY/HEX/LUT/supervisor/runner 后才可 hardware。

## 16. 下一位前 30 分钟

1. `0-5 min`：读 workflow skill、quickstart、COMP-REQ-318..320、本 MD/JSON；不 build、不碰硬件。
2. `5-10 min`：验证 handoff JSON、registry、current-goal、protected hashes；确认 `R10_BALL` 在
   app/tools/docs/validation 中不存在。
3. `10-15 min`：只查看自己将拥有的 lower-driver diff；记录并发上层 dirty changes，不回退。
4. `15-20 min`：读 R9 workbench、R8 runtime、R9 continuous R2 runtime/archive；确认 HUMAN FAIL
   没被误写为 machine failure 或 missed observation。
5. `20-25 min`：排除自身 PID 后做 process audit；必须无 runner/monitor/supervisor/prompt/programmer。
6. `25-30 min`：停止；COMP-REQ-320 有效期间只处理 admission/registry/docs。

## 17. Stop/Go gates

立即 STOP：pause 仍有效、R10 问题未答、出现意外 R10 文件、protected hash 漂移、相关 live process、
worktree ownership 不清、或候选改变 waveform/tail/fixed-bank/cleanup/restore/popup lifecycle。

仅可进入 implementation：owner/root 明确解除 pause，新 registry requirement 已记录所有 R10 决策，
protected hash 与 no-R10-start baseline 全 PASS。

仅可进入 MACHINE_READY：pixel oracle、source/static、parser/monitor/supervisor、negative fixtures、isolated
build、persistent CheckOnly 全 PASS 且 `hardware_contact=0`，并生成 distinct stable R10 MACHINE_READY。

仅可进入 hardware：root 新 one-shot authorization 绑定 exact R10 MACHINE_READY/HEX/LUT/supervisor/
runner 与 fresh output root。

未来 run 在任一 machine fault/BUSY>600、popup abnormal/multiple、owner PASS/FAIL、postclean/restore/
normal-resume/process-exit audit 失败时都必须立即 STOP 并归档。

## 18. 安全检查命令

这些命令只读或更新审计文档，不 build、不接触硬件：

```powershell
python tools/verify_companion_product_requirements.py
python tools/verify_companion_current_goal_audit.py
python tools/verify_companion_ssd1681_lower_driver_handoff.py
rg -n "R10_BALL" app tools docs/validation
git diff --check -- docs/companion_product_requirements.md tools/verify_companion_current_goal_audit.py docs/validation/companion-current-goal-audit-20260717.json docs/validation/companion-current-goal-audit-20260717.md docs/validation/companion-ssd1681-lower-driver-next-agent-handoff-20260721.md docs/validation/companion-ssd1681-lower-driver-next-agent-handoff-20260721.json
```

PID audit 必须过滤当前 `$PID`，并只报告匹配，不终止任何未知进程。
