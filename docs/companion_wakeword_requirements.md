# Companion 本地唤醒词需求

## 状态与范围

这是 Companion 的正式产品需求，项目项为 `SCR-18`。当前 WB55 只有
`wake_word_control` / `wake_word_status` 的控制、状态、诊断和
`simulate_detect` 演练链路；它**不是**真实关键词识别，也不能宣称产品已经
“常驻聆听”。真实本地唤醒词（KWS, keyword spotting）在本需求落实并通过真机
声学、功耗与隐私验收前保持 `planned`。

产品目标是在不上传持续音频的前提下，检测一个可配置的中文产品唤醒短语，再将
后续语音交给既有录音/语音识别流程。最终短语不是代码常量，必须在模型选择和
真实中文语料验证后由产品确定。

## 产品架构

```text
SPH0655 PDM DMA / WBA target audio adapter
        -> PCM16, mono, 16 kHz normalization
        -> bounded 10 ms or 20 ms frames
        -> optional DC/high-pass/level normalization -> VAD gate
        -> portable KWS engine -> debounce / confidence / cooldown
        -> RAM-only pre-roll -> recording FSM / ASR handoff
        -> diagnostics, BLE status, pet_expression listening/thinking feedback
```

1. `PCM16`、单声道、`16 kHz` 是 WB55 与 WBA55/WBA65 的公共音频契约。WB55
   保留已经验证的 SAI/PDM/DMA 到 PCM 归一化；WBA 只能通过自己的
   SAI/PDM/MDF/ADF/DMA 适配器提供同一契约，禁止复制 WB55 的时钟或寄存器常量。
2. 核心层只接收有时间戳的固定大小 PCM 帧，不能依赖 HAL、QSPI、BLE、屏幕或
   MCU 型号。模型引擎必须经一个可替换的 `wakeword_engine` 接口接入。
3. VAD 只负责“是否值得送入 KWS”的省算力门，不能替代 KWS；KWS 只检测唤醒短语，
   不能常驻运行完整 ASR。检测成功后才进入录音/ASR 状态机。
4. 命中前只允许保留一个有界、RAM 内的短 pre-roll。停用、隐私模式、错误或超时
   时必须清零该缓存；未经用户明确的录音状态，不得把常驻聆听音频写入
   `recording_cache`。
5. 状态至少为 `disabled`、`arming`、`armed`、`detected`、`cooldown`、`error`
   与 `privacy_blocked`。命中必须有去抖、置信度/阈值判定和冷却期，避免同一句话
   多次触发。现有 GATT status/diagnostic 继续作为可观测面，但真实检测事件必须
   来自 PCM/KWS 链路，不能由 `simulate_detect` 冒充。
6. 电子纸只在 arm/disarm、真实命中、录音、思考或错误等有意义的状态转换时给出
   宠物反馈；不能因每个音频帧而刷新屏幕。命中后可进入 listening 表情，随后由
   recording/ASR 状态驱动 recording/thinking/speaking 表情。

## 模型、Flash 与更新边界

| 内容 | 放置 | 规则 |
|---|---|---|
| KWS 推理代码、DSP glue、DMA/中断、最小救援状态 | 内部 Flash | 启动与实时路径必须可用；不含可替换完整模型 |
| KWS 模型、短语包、语言前端参数、可替换提示音 | 外部 NOR `model_assets` / `prompt_assets` | 默认外置，按模型包 metadata 有界读取；不得作为普通固件 C 数组长期链接 |
| 当前帧、特征窗口、推理 arena、RAM pre-roll | SRAM | 容量由每个候选模型的实测预算决定，不能把完整模型或无限音频缓存复制到 SRAM |
| 用户录音 | 外部 NOR `recording_cache` | 仅在检测后的录音流程或明确录音动作中持久化 |

每个模型包必须包含 model revision、hash、目标族/板型、所需 sample rate、frame
length、前端版本、engine ABI、最小应用版本、工作区预算和兼容性声明。激活必须
先完整校验新包，再用冗余 metadata 原子切换；失败继续使用上一有效模型或明确
禁用可选唤醒功能，绝不能部分替换。

现有 OTA 组件契约已预留 `model_assets`。但 Companion OTA 仍受 Listener 验收与
Denzic platform commit 对齐冻结约束：本项目现在只定义模型包与安装语义，**不**
推进 OTA 传输、刷写或真机 OTA 验收。

## 方案筛选与实施顺序

1. 先使用现有 PDM 录音链路录制/回放固定 PCM 夹具，证明帧节奏、溢出、丢帧、
   时间戳和 VAD/KWS 状态交接，不接入 UI 以外的产品承诺。
2. 对 WB55 做候选引擎 spike：优先比较授权可接受的 Cortex-M KWS SDK（例如
   Porcupine）与自有量化模型路线（TensorFlow Lite for Microcontrollers 或
   STM32Cube AI）。选择依据是中文短语效果、Flash/RAM、每帧 CPU、持续电流、
   许可证/离线部署、模型更新与 WBA 可移植性，不按宣传参数直接选型。
3. 选定一个模型后实现 HAL-free `wakeword_engine`、`wakeword_service` 和
   WB55 audio adapter；现有 GATT 仅作控制/状态桥接。模型、阈值和语言包走外部
   `model_assets`，推理二进制仍在内部 Flash。
4. 最后实现 WBA target adapter，并在 WBA55 作为资源/功耗基线复测；WBA65 的
   更多内部 Flash 不能成为把模型重新塞回固件的理由。

## 功耗、隐私与产品交互

- 长期开启 PDM 时钟、DMA 和 MCU 推理会明显影响电池；因此 `always_on` 只能在
  用户开启、麦克风可用、隐私未锁定且电源策略允许时进入。低电、充电策略、睡眠
  唤醒路径和硬件麦克风 mute 都必须由产品板实测后确定，不能从开发板推断。
- `privacy_blocked` 和硬件 mute 的优先级高于 BLE、屏幕和软件 arm 请求；它们必须
  立即停采样/清 pre-roll/停止 KWS，并留下不含音频内容的诊断事件。
- 唤醒短语需要足够区分度，避免过短、近音或易出现在日常对话中的词。中文普通话、
  口音、距离、音乐/人声背景和外壳声学变化都属于模型选择与阈值调优的输入。

## 验收门

每个候选模型都必须提供以下原始证据；未完成任一门不得把状态改成产品 ready：

1. 离线 PCM 回放：真实短语、非短语、静音、连续语音和噪声夹具的结果，含命中、
   拒绝、丢帧、端到端延迟与模型/阈值 revision。
2. WB55 真机声学：不同说话人、距离、普通话口音、环境噪声、背景人声和播放源
   下测量 false accept rate、false reject rate、检测延迟、CPU、SRAM、内部/外部
   Flash 和持续/休眠电流。项目先记录基线，再依据产品场景冻结阈值，不能只报
   单一“准确率”。
3. 交接与隐私：一次真实命中只启动一次录音，会带正确 pre-roll；冷却期不会重复
   触发；disarm、privacy、mute、低电和音频错误均停止采样并清 RAM 音频。
4. WBA 复验：同一 portable PCM/KWS 核心在 WBA adapter 上编译、跑 PCM 夹具，
   并重新测真实产品板资源、功耗和声学；WB55 结果不能代替 WBA 证据。
5. 模型更新：候选模型损坏、目标不匹配、ABI 不匹配、断电中断和回退均保持旧模型
   或安全停用；未来 OTA 解冻后才纳入 Denzic 的真实安装验收。

## 调研依据

- ST 的本地语音方案把 keyword spotting 与 intent recognition 分为边缘侧能力，
  并明确效果取决于目标 MCU、音频前端和应用负载：
  <https://www.st.com/content/st_com/en/ecosystems/stm32-audio-voice.html>
- ST 的 16 kHz、16-bit、单麦 DMA 音频案例说明了“固定 PCM 窗口 -> 特征 ->
  量化网络”的典型嵌入式数据流，而不是直接把 PDM 喂进模型：
  <https://www.st.com/content/st_com/en/st-edge-ai-suite/case-studies/acoustic-scene-classification.html>
- Porcupine 的微控制器 API 要求单声道、16-bit PCM、固定 frame，并把模型与
  8-byte-aligned runtime memory 显式交给引擎；它是一个可评估候选，不是既定依赖：
  <https://picovoice.ai/docs/api/porcupine-microcontroller/>
- TensorFlow Lite for Microcontrollers 是面向资源受限 MCU/DSP 的模型部署基础设施，
  可作为自有量化模型路线的候选：
  <https://github.com/tensorflow/tflite-micro>

## 防回退

```powershell
python .\tools\verify_companion_wakeword_requirements.py --write-fixture
```

检查器固定：当前实现只能标为 control/simulation ready；生产 KWS 必须以 PCM16
16 kHz、VAD/KWS 分层、外部 `model_assets`、OTA 冻结、隐私清缓存与 WB/WBA 分层
验收为前提。
