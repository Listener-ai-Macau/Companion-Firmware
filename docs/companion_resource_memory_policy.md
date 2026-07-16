# Companion 资源与 Flash 产品原则

## 当前 Goal 覆盖（2026-07-17）

当前产品视觉边界以 active Codex Goal 和 `COMP-REQ-053/069/072/073/074`
为准。以下历史 r53、救援 UI 和参数化表情描述只保留资源/协议演进证据，不能
作为当前产品可见美术或 fallback。

- 唯一内脸基线是锁定的 `companion-pet-expression-v9`；产品表情帧和菜单底图必须
  由外部 CEMP 资源提供。
- WB55 产品构建不编译 `pet_expression.c`，不链接完整代码绘制菜单，也不链接内部
  200x200 表情数组；这些源文件仅可供历史/主机回归使用。
- 视觉资源不可用时，当前产品路径 fail closed：保持上一帧并返回资源/传输错误，
  不画程序化脸、测试图或整页代码菜单。动态数据只能叠加在已验证的外部 CEMP
  菜单底图上。
- v9 资源候选及四根菜单/特殊场景仍需各自批准和资源激活；本节不授权 PBM/CEMP
  runtime import、外部 Flash provision、刷机或视觉 PASS。当前 provision build
  只作字节一致性构建检查，flash entry point 必须拒绝执行。

## 结论

Companion 产品默认使用外部串行 NOR Flash 保存可替换的大资源。内部 Flash
只保存启动、无线栈、驱动、可移植状态机和最小救援资源。这个原则同时适用
于当前 WB55 验证板和后续 WBA55/WBA65 产品板。

正常表情动画、完整字体、提示音、离线模型、录音缓存和 OTA 暂存都属于外部
资源。它们不能因为开发方便而长期编译成内部 Flash 中的 C 数组。

当前普通 WB55 构建的内部 Flash 占用约为 `140052` bytes（`.text`、`.rodata`
和 `.data` 的 Flash load image），而应用链接区为 512 KiB。正常产品表情已不再
占用其中的全帧位图：历史 `expression_assets_200x200.c` 仍保留为生成/回归资料，
但不进入普通构建。下一批优先外置的可替换内容是本地唤醒词模型/语言前端参数
（`model_assets`）、提示音（`prompt_assets`）、产品语言包和诊断镜像；不把
boot、BLE/屏幕/音频驱动、DMA/中断、资源解析器或实时 KWS 推理代码挪到外部。
详细的唤醒词数据边界见 `docs/companion_wakeword_requirements.md`。

## 内外存职责

| 存储 | 默认内容 | 例外与限制 |
|---|---|---|
| 内部 Flash | bootloader、应用代码、无线栈、驱动、状态机、资源包解析器 | 只允许一套不超过 16 KiB 的救援 UI，用于外部 Flash 缺失、校验失败或恢复模式 |
| 外部 NOR | `ui_assets` 表情包、完整字体、提示音、离线模型、录音、OTA staging、诊断镜像 | 分区地址和总容量由每块 WB/WBA 产品板定义，不进入可移植模块 |
| SRAM | 当前 framebuffer、局刷工作区、短读缓存和播放器状态 | 不把完整资源包复制进 SRAM；是否双缓冲由目标能力决定 |

资源是否放外部 Flash 不只按单文件大小判断。表情、字体、音频和模型本身是
可替换产品资源，即使某个版本暂时很小，也默认位于外部 Flash。内部救援资源
是显式白名单，不是通用缓存区。

## 已退出的过渡基线

WB55 bring-up 曾把 10 张 200x200、1-bit 静态表情编译进内部 Flash，每张
5000 字节，共 50000 字节。2026-07-11 完成外部 `ui_assets` 实机挂载和帧读取
后，这组数组已从正常 Makefile 链接中移除：

- 正常构建链接的完整静态表情帧为 0 字节；
- `expression_assets_200x200.c` 只保留为历史生成结果，不允许重新加入产品构建；
- 新的完整静态脸和动画帧都必须进入 CEMP 外部资源包；
- 历史 `pet_behavior`/`pet_expression` 参数化路径仅保留为主机和协议回归资料；
  当前产品 renderer 不允许把它们画入 framebuffer。行为层仍只保存小型
  valence/arousal/engagement 状态，不把“更多表情”做成内部位图堆叠；
- 当前产品外部包不可用时不显示小型菜单/测试图救援路径；保持上一帧并记录错误。
  救援 UI 的 16 KiB 预算只保留为历史/恢复模式容量边界，不能成为正常可见 UI 的
  回退来源。

## 可换屏与可换表情

可移植层使用三层契约：

```text
emote_player: intro / loop / tail 和逐帧时长
        |
emote_asset_pack: 名称、版本、屏幕 profile、帧索引、CRC
        |
asset_store: 内部映射 / 外部 NOR / 主机流的有界 read(offset)
```

资源包必须声明：

- 格式版本和资源 revision；
- 逻辑画布宽、高、stride 和像素格式；
- 每帧 duration、数据 offset/size 和 16 位 dirty rect；
- 帧编码；当前 `packbits` 按帧独立压缩，允许随机读取和有界流式解码；
- 动画名称及 `intro -> loop -> tail` 索引；
- payload CRC32。

播放器不认识 SSD1681、QSPI、OSPI、GPIO 或固定分辨率。挂载层只接受同时匹配
当前产品批准的资源身份、runtime activation、目标 profile 和 CRC 的资源包，不能
按“最高优先级/最新”自动选到历史美术。面板旋转属于 panel 后端，不写入表情动画
逻辑。以后换屏幕时，新增 profile 和资源包；以后换整套表情时，提高资源 revision。
两种情况都不修改播放器状态机。

## 外部资源启动流程

1. 目标板 storage 后端探测外部 NOR，并取得 `ui_assets` 分区边界。
2. 读取小型 manifest/index，检查 magic、格式版本、范围和目标 profile。
3. 分块计算 payload CRC32；通过后才发布为 active pack。
4. player 输出帧索引，asset store 只读取该帧到有界 framebuffer/解码工作区。
5. 读取、CRC、格式、profile 或产品激活策略失败时，记录诊断并 fail closed，保持
   已有面板内容；不能继续使用未验证资源，也不能显示内部救援 UI 作为产品可见
   替代画面。

当前二进制格式 magic 为 `CEMP`，header 固定 80 字节，随后是 clip table、
frame table、字符串表和 payload。所有多字节字段为 little-endian；解析器逐字段
读取，禁止把外部字节直接 cast 成编译器结构体。WB55 当前提供 32 clips、128
frames、1024 字节字符串表的有界挂载工作区；这些是目标能力，不是 portable
格式上限，WBA 目标可以按 RAM 预算配置自己的容量。

菜单中文字体不进入 MCU 内部字库。主机端用 CJK 字体生成目标 profile 的单色
页面资源，英文和中文页面与表情帧一起放入 `ui_assets`；运行时只叠加少量动态
状态。外部包不可用时，内部英文救援菜单仍可进入录音、状态和设置页。

`tools/build_emote_asset_pack.py` 从 screen profile 清单和 PBM 源文件生成确定性
CEMP 包。WB55 的 `-ScreenAssetProvision` 是开发板一次性写入模式：资源 blob
只进入独立 provision 镜像，写入并回读外部 Flash 后必须刷回不含 blob 的普通
固件。产品更新路径仍应使用 staging/OTA，不能常驻 provision blob。
刷机必须使用 `tools/flash_nucleo_bringup.ps1 -ScreenAssetProvision` 选择
`Companion_Nucleo_WB55RG_ScreenAssetProvision.hex`；普通 `tools/flash_nucleo_bringup.ps1`
只能刷回 `Companion_Nucleo_WB55RG_Bringup.hex`。两种路径都先用 `-CheckOnly`
确认实际 hex，防止资源写入流程误刷成普通固件或把 provision 镜像留在设备上。

revision 19 将 220 张 200x200 白底黑色帧从 raw full-frame 改为逐帧 PackBits：
相同视觉 PBM 资源从约 1.1 MiB 压缩为 403,499 bytes，仍由外部 `ui_assets` 提供。
PackBits 不依赖上一帧，播放器可从任意 frame offset 读取，并在固定 framebuffer
中流式展开；它不是视频编码，也不把完整包或解码副本留在 MCU 内部 Flash/SRAM。
此压缩仅解决开发板 provision 镜像容量，产品 OTA 语义和原子激活边界不变。

revision 20 更新目录的固定标题栏与白色 viewport 隔离带后，PackBits 包为 396,629
bytes、CRC32 `0x478BA8DC`。这仍是单帧独立编码；屏幕目标层可持有一张 5,000-byte
framebuffer 和上一成功帧用于差分窗口，但不得为“手机式滚动”把完整资源包、目录帧组或
解压缓存移回 MCU 内部 Flash/SRAM。

资源包升级必须先完整写入非活动区域或 OTA staging，校验通过后再原子切换
active metadata。是否使用双 `ui_assets` 槽取决于产品 Flash 容量；单槽产品
也必须通过 staging 避免原地覆盖当前有效包。

## 外部资源也属于 OTA

外部 Flash 不是 OTA 范围之外的“数据盘”。正常菜单、表情、字体、提示音和
离线模型都是可替换产品组件，必须能通过 OTA 独立更新。它们与 `mcu_app` 使用
同一个签名 bundle，但各自拥有组件版本、格式版本、目标、长度、SHA-256 和
兼容性条件。Denzic `denzic_ota_v1` 只负责可靠传输不透明字节流；资源安装、
兼容性检查和原子激活由 Companion storage adapter 负责。

- 只更新资源时，不重写 MCU 应用，目标无强制要求时也不重启；
- 只更新固件时，保留当前有效 `ui_assets` 与所有用户数据；
- 同时更新时，先完整暂存并验证全部 component，新应用启动后再次确认资源格式、
  screen profile 与 app 版本兼容，再切换冗余 active metadata；
- 断电、摘要、签名、版本或兼容性失败时继续使用旧资源；旧资源也无效时进入内部
  rescue UI；
- `recording_cache`、诊断和用户设置不是 OTA component，普通升级禁止擦除。

## Companion 情绪记忆

`comp_pet_behavior_memory_t` 是一小段用户数据，不是 CEMP 表情资源，也不是 MCU 固件常量。
它保存长期亲密度、情绪向量、互动计数和性格种子；目标存储层必须使用独立于 `ui_assets`、OTA
staging 和录音缓存的用户数据逻辑分区，并采用 CRC、双记录或等价的断电恢复策略。写入只能在
合并后的低频检查点发生，例如明确会话结束、受控休眠或至少数分钟的稳定状态，绝不能每次触摸
都擦写 NOR。正常 OTA 保留这份用户数据，恢复出厂或明确 privacy/隐私删除才允许清除它。
WBA55/WBA65 的当前预移植边界是 `pet_behavior_user_data_stm32wba.h/.c`：
它只定义 target-owned 逻辑槽 read/write/privacy erase 回调、CRC 记录、序列号和低频提交策略，
不选择物理地址、外设、擦除大小或 NOR 分区；真实产品板仍要补断电、磨损、OTA 保留和
privacy/factory erase 证据。

完整机器契约见 `docs/companion_ota_component_contract.json` 和
`docs/companion_ota_component_contract.md`。物理分区地址继续由 WB/WBA 目标配置，
不能写进 portable 资源解析器。

## Companion 电子宠物表现原则

成熟电子宠物的溢价感来自“像活物一样持续变化”，不是一组孤立图标。参考
Aibo/Loona 这类屏幕表情产品和 Moflin 这类情绪陪伴产品后，Companion 的屏幕
资源必须固定以下原则：

- 表情和菜单美术先用生图或等价视觉稿确定基线，再由固件/资源生成器按该基线
  还原；实现层只能做可移植的 one-bit 重绘、参数化动效、屏幕 profile 适配和
  外部资源打包，不能脱离视觉基线自由发挥另一套脸或菜单风格；
- 生图基线是产品美术 source of truth。以后调整 prompt、换屏幕尺寸或换外壳时，
  先更新视觉基线，再更新 renderer/style constants、PBM 和 CEMP；不得只改
  procedural fallback 后宣称正常产品美术已更新；
- 正常表情美术走外部 CEMP 资源包，便于以后按生图 prompt 或新屏幕 profile
  快速替换；内部 procedural 只做救援、维护和极小的兜底动态；
- 表情状态必须由情绪向量、长期记忆、触摸方向、声音/录音状态和设备状态共同
  驱动，不能只播放固定模板；
- 一次表情变化要尽量让眉毛、眼睛、高光、嘴、脸颊和小状态符号一起变化，
  避免只有眼睛动造成低价感；
- 电子纸不能追求 OLED 高帧率，产品体验靠低频关键帧、保留尾段、状态记忆、
  局刷节流和触摸方向反馈来模拟生命感；
- 慢速或可替换的大资源默认放外部 Flash，即使当前体积不大，也不能为了开发
  方便回退到 MCU 内部全帧数组；
- 用户情绪记忆和资源包分区分离。OTA 更新表情资源不能擦掉长期亲密度、性格
  种子和互动历史。

## WB55 与 WBA 边界

- 当前 WB55 已通过 `companion_screen_assets_stm32wb.*` 将
  `comp_spi_nor_read()` 接成 `asset_store` reader。开发板 `ui_assets`
  只读窗口为 `0x00200000 + 2 MiB`；这是 WB55 bring-up 布局，不是 WBA
  默认地址。
- WB55/WBA55/WBA65 的已选公共协议是普通 `1-1-1 SPI NOR`。WB55 通过独立
  `SPI1` 验证命令核心，WBA55/WBA65 根据最终芯片、封装和引脚实现独立的
  `*_stm32wba.*` target binding。当前
  `screen_assets_stm32wba.h/.c` 已提供 callback-only 的 `ui_assets` reader
  边界：它只接收逻辑分区大小和相对读取 callback，不包含物理地址、外设或引脚。
- 可移植代码只看 `comp_asset_store_t` 和逻辑分区长度，禁止写目标寄存器、HAL
  句柄、物理基地址或固定 Flash 容量。
- WBA55 是资源预算基线；WBA65 的额外内部 Flash 不能成为公共资源包的默认
  存放位置，较大内部容量优先留给固件、无线功能和升级余量。
- WB55/WBA 的情绪记忆都必须通过 target-owned user-data adapter 读写
  `comp_pet_behavior_memory_t`；portable `pet_behavior` 只负责导入/导出和
  schema 检查，禁止包含物理地址、擦除大小或外设调用。清除路径必须是显式
  privacy/factory erase，普通 OTA 和资源更新不得隐式擦除用户情绪记忆。

## 防回退

运行：

```powershell
python .\tools\verify_screen_resource_architecture.py
python .\tools\verify_companion_ota_component_contract.py --write-fixture
python .\tools\verify_expression_screen_assets_stm32wba.py
```

检查器固定以下约束：portable storage/pack 文件无 HAL/QSPI 依赖、脏区坐标为
16 位、Makefile 编译外部 frame source、资源包要求 profile 和 CRC、正常构建
不得重新链接 50000 字节历史静态帧、产品救援资源上限为 16 KiB，并且项目与
WBA 规则保留外部资源优先原则。OTA 检查器另外固定资源属于 OTA、固件/资源
独立更新、原子激活、旧版本回退以及录音与设置不被升级擦除。
