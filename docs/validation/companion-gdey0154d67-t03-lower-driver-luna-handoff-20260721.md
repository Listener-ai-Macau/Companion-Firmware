# GDEY0154D67-T03 Lower-Driver Luna Handoff

状态：`READY_FOR_GOAL_EXECUTION`

日期：`2026-07-21`

范围：仅限 `Companion-Firmware` 的 WB55 + ESP32-FTS02 +
GDEY0154D67-T03/SSD1681 production-off 局刷诊断。上层 V9/Rig/CRIG、浏览器预览、
动态表情绑定及 production 刷新策略不在本任务内。

## 一句话结论

这个方向可以继续，但不能继续 r6 的“单次 activation 直接移动”路径。唯一允许的新方向是
lower-driver `COMP-REQ-243`：保留昨晚人工 PASS 的“两段式先擦旧、再画新”，只把第二段的
单一 union window 改成 1 到 5 个离散 current-only `0x24` 窗口，然后统一完成第二次局刷。

当前代码只是半成品，不能直接刷板。它已有候选 driver block，但没有独立构建开关、runner、
verifier、trace parser 或新候选物理 artifact，并存在可能产生错误轨迹和第三次刷新的代码缺口。

## 已证实的事实

### 1. 真正的人工 PASS 基线

`COMP-REQ-236/237` 的 `vendor_partial_no_union_settle` 是唯一已接受的无残影视觉基线：

- pass 1：previous-frame black byte bounding box，写 CPU-held current-frame `0x24`，执行自己的
  supplier `reset 10/10 ms -> border 0x3C=0x80 -> 0x22=0xFF -> 0x20 -> BUSY`。
- pass 2：previous/current diff union，写 current-frame `0x24`，再执行一次相同 completion。
- 人工接受：无反复旧位置条纹/残影，无整屏黑闪。
- 已知缺陷：第一相位会短暂切掉移动前沿，第二相位恢复。
- 人工原话：`好很多, 就是移动的时候移动方向会切掉一点, 随后还原, 能优化吗`。

### 2. r6 只验证了运动几何

r6 的单个半径 12 px 黑球已经在实板完成五锚点轨迹：

`(100,100) -> (100,58) -> (142,100) -> (100,142) -> (58,100) -> center`

每段 8 个插值位置，轨道半径 42 px。r6 的机器 trace 通过，owner 按钮选择通过只表示球可见且
方向可继续研究；备注明确仍有残影：

`你现在这样子直接移动是会有残影的，你看看昨天的这种工作方式去学习一下`

因此 r6 不是 residue-free PASS，也不得进入 production。

### 3. 为什么 COMP-REQ-243 值得继续

本地逐条对照显示：所有仍有残影或累计缺口的失败路径，要么让擦旧和画新共用一次 activation，
要么先画后擦；两个已接受路径都让“擦旧”独占第一次 activation，再执行画新 activation。
新候选保持这一已接受顺序，只收窄第二段的 RAM staging 区域。这不会从原理上消除第一相位的
短暂切口，但有机会保持无残影，同时减少离散表情组件之间的无关窗口覆盖，适合作为未来眼睛高光、
眉毛或嘴部小范围变化的底层 primitive。

Good Display 官方产品页确认该 T03 是 200x200、SSD1681，并支持约 0.3 s partial refresh；这只证明
面板能力，不证明任意自组拓扑无残影。供应商包的 `EPD_Dis_Part_myself` 则明确允许最多五个窗口在
一个 `0xFF/0x20/BUSY` 前依次写入，正好支持新候选第二段的来源约束。

## 当前证据绑定

| 证据 | 状态 | SHA256 |
|---|---|---|
| 只读供应商 `EPD_W21/EPAPER.c` | source input | `7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896` |
| COMP-REQ-236 operator artifact | accepted baseline | `DA2FE11DB4CB1AFC5D433B2798BADBB576FC9C82BB39C472236E084C48F1EC57` |
| r6 operator artifact | visible geometry; residue steering | `13CF51F221110829949075864973DF769AAF1C8222B73B482124BF14FD55D9C3` |
| yesterday-method study | study complete | `A88B022423E6ADFBA83B1362BAACB0C6CAC3A970DAEC93EB521E63EEB0030C2D` |
| current SSD1681 target at audit | incomplete candidate | `701A048CE53CC2306899B7139356D6F21FE1335395E13CB7CDDAC314C8260042` |
| exact normal image | restore contract | `E1997F29DCB8735899B4BC0B9012CF75025F3CA8D21250485BCC21E4C4691B46` |

主要文件：

- `docs/validation/companion-gdey0154d67-t03-vendor-partial-no-union-settle-operator-20260720.json`
- `docs/validation/companion-gdey0154d67-t03-vendor-partial-disjoint-current-stage-operator-r6-20260721.json`
- `docs/validation/companion-gdey0154d67-t03-yesterday-method-study-20260721.json`
- `app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c`

## 当前实现缺口

1. driver 已有 `COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DISJOINT_NO_UNION_SETTLE_DIAGNOSTIC=0`
   和 erase/draw block，但 Makefile、`build_nucleo_bringup.ps1`、runner、static verifier、trace parser
   都没有为新候选建立独立绑定。
2. request phase 当前只在 `DISJOINT_CURRENT_STAGE` 条件下调用
   `ssd1681_disjoint_component_probe_phase(cycle)`。新宏会落入旧的 0..5 `menu_page` 循环，无法重放
   完整 50-frame 五锚点轨迹。
3. candidate block 自己完成两次局刷后，通用 partial 尾部的排除条件没有包含
   `vendor_partial_disjoint_no_union_settle`，可能再执行第三次 `ssd1681_refresh_display()`。必须修复并由
   parser 证明每个 changed frame 恰好两次 completion。
4. pass 1 之前仍经过通用 union `window_set` setup。必须消除多余 setup，或以静态和运行证据证明其
   没有写 payload、没有 activation、不会改变两段式合同。

## Luna 的实施合同

1. 先重新读取 AI workflow skill、quickstart、Goal contract、产品 registry、runner/gates 和物理 checklist，
   运行 current-goal/registry audit。不得覆盖另一位上层美术 agent 的脏工作树改动。
2. 完成 default-off 的 `vendor_partial_disjoint_no_union_settle`，只保留：
   - pass 1：一个 previous-black bbox/current `0x24`/一次 supplier completion；
   - pass 2：1..5 个 byte-aligned、互不重叠 diff windows/current `0x24` staging/一次 completion。
3. 补齐独立 diagnostic/observer builds、static gate、r2 prerequisite 复用、trace parser、runner
   CheckOnly/Execute/restore 和 fail-closed fixtures。
4. 机器闭环全绿前绝不刷板；物理失败、超时或通过后都恢复 exact normal image。
5. 最后只用 canonical `aiw operator-prompt` 中文窗口收集结果，窗口打开时 observer 必须持续运动。

## 执行所有权

- root 只负责前置调研、Goal 合同、整体计划、方向和用户沟通。
- 当前执行代理 Luna（owner 口述称 Lander）负责本 Goal 的全部项目文件编辑、命令、构建、测试、机器与物理 gate、artifact 和完成审计；不要求 root 重跑 Luna 已完成的命令或文件审读。
- root 不运行本 Goal 的项目 shell、build、test、edit 或 hardware 命令；Luna 是唯一执行者，拥有 implementation、verification 和 completion audit。
- Luna 只在 `MACHINE_READY`、`NEED_HUMAN`、`FINAL/NO_GO` 三个里程碑向 root 发送结构化摘要，普通过程不回报。
- 每个里程碑摘要必须包含 `changed_files`、`commands + exit codes`、`artifact paths + SHA/status`、`remaining gaps`、`hardware_contact` 和 `normal_restore`。
- root 不重复读取或重跑，只依据 Luna 的结构化证据规划、维护 Goal 状态和转达人类验收输入。
- 只有发生安全冲突或证据缺失时，Luna 才请求 root 决策。
- 这是协作流程约束，不新增任何产品行为，也不得写入上层 art registry。

## 机器通过阈值

- 50 requests：1 baseline + 48 changed partial + 1 identical；identical 为 0 payload/0 activation。
- 半径 12 px 单球完整覆盖五锚点，42 px 轨道、8 steps/segment，所有像素在 200x200 内。
- 48 个 changed frame 各恰好两次 completion，共 96 次；96/96 BUSY 完成，0 panel error。
- pass 1 恰好一个 previous-black bbox；pass 2 每帧 1..5 个 byte-aligned/non-overlap diff windows。
- changed partial 两段都只写 current-frame `0x24`；无 `0x26`、`0xC7`、159-byte LUT load、
  old-or-current union、5000-byte full write、历史失败顺序或第三次 activation。
- synthetic 离散差异必须产生至少两个窗口，staged bytes 严格小于 union bytes。
- 每次 partial completion BUSY elapsed 不超过 700 ms；两次合计 p95 不超过 1200 ms、max 不超过
  1400 ms。这是防卡死门限，不是温度完整或 OLED 速度声明。
- normal/diagnostic/observer WB55 build、host/static tests、parser fixtures、runner CheckOnly、
  fail-closed tests、serial-open retry、r2 prerequisite、registry/current-goal audit 和 `git diff --check`
  全部通过；normal image hash 不变。

## 人工边界

相对 COMP-REQ-236，不得出现旧位置条纹/残影、整屏黑闪、屏幕脏化、累计内容丢失或球未移动；
领先边切口不得比 COMP-REQ-236 更大或更久，最终连续感由 owner 决定。任何失败或超时都归档
`NO_GO`。即使通过，也仍是 production-off，不得自动绑定产品表情。

## 禁止事项

- 不修改、移动或删除供应商目录；不猜测、重写或联网借用 LUT/波形。
- 不改 `0xFF`、reset/border、register、timing、rail、temperature policy。
- 不重测 White/Black/正负 20 V rail，不做全刷补偿。
- 不重跑 `0x26 prior + 0x24 current` 单激活、old-or-current union -> final、
  current union -> removed-black、removed-black -> current union 或 r6 单激活路径。
- 不触碰 locked V9、Rig、CRIG、browser、dynamic binding 或 owner acceptance JSON。

## 外部原厂参考

- Good Display GDEY0154D67-T03：`https://www.good-display.com/product/258.html`
- Good Display GDEY0154D67：`https://www.good-display.com/product/388.html`
