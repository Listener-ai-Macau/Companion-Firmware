# Companion 低功耗待机需求

## 产品决策

`SCR-21` 的默认交互是日常页双击触控开始录音，再次双击停止同一触控来源的
录音。真实本地唤醒词保持 `deferred`：不得启动 PDM 时钟、DMA、VAD 或 KWS，也
不得以 `wake_word_control` 的模拟状态冒充常驻聆听。

低功耗是核心产品目标。目标值是最终产品板的已定义待机场景在连续 `60 s` 原始
电流轨迹上的平均值不大于 `1 mA`。这只是验收门，不是当前 WB55/NUCLEO 已实测
数值；NUCLEO 的 ST-LINK、板载稳压和外接模块使其不能作为产品电流结论。

## 运行时策略

WB55 使用 CubeWB 的 `UTIL_LPM`，而不是在应用层直接调用裸 Stop 寄存器。可移植
`power_policy` 只表达“现在是否允许 Stop”，目标后端再将其映射为 CubeWB 或
CubeWBA 的低功耗管理器。

```text
触控 PC6/EXTI6 已就绪
  + 无 boot / PDM 录音 / 手指接触 / 菜单计时 / 刷新维护 / BUSY 捕获
  -> 允许 Cube LPM Stop

任一条件不满足
  -> 禁止 Stop，保持短周期服务直到该活动结束
```

当前 WB55 实现的约束如下：

| 条件 | Stop 策略 |
|---|---|
| `TP_INT` (`P10 A0 -> CN10-33 -> PC6`) 已配置 EXTI | 候选触控唤醒源；仍须真机证明从 Stop 可稳定恢复 |
| 双击录音或任何 PDM/外部 Flash 捕获 | 禁止 Stop |
| 手指仍接触、长按菜单计时 | 禁止 Stop，保留 5--10 ms 触控采样 |
| 电子纸刷新 BUSY 期或交互后维护刷新 | 禁止 Stop，保留显示与触摸缓冲服务 |
| 空闲且 `TP_INT` 就绪 | 不再执行固定 `HAL_Delay(10 ms)`；交给 `UTIL_LPM_EnterLowPower()` |
| 日常页准备进入稳定 Stop | 只排队一次外部 Flash `sleepy` 休眠脸并等待该帧完成；随后停止表情播放器和定时器。休眠的呼吸关键帧是可替换美术词汇，不得在 Stop 中周期性唤醒或刷新电子纸。 |
| 触控中断配置失败 | 禁止 Stop，保留现有触摸轮询回退 |

当前 NUCLEO 已接 `TP_SCL/TP_SDA` 和 `P10 A0 -> CN10-33/PC6 (TP_INT)`；`TP_RST` 未接。
开发板构建因此使用 `COMPANION_TOUCH_INT_WIRED=1`、`COMPANION_TOUCH_RST_WIRED=0`。
FT6336 的 I2C 触发模式读回仍不能独立证明硬件唤醒，必须由真实 IRQ 计数和 Stop
恢复验收确认。`P10 A3 -> CN10-29/PC10` 是可选硬件恢复线，接上后才把
`COMPANION_TOUCH_RST_WIRED` 改为 `1`。

开发板 `SW1/SW2/SW3` 只是调试入口。稳定的触控中断空闲态不为它们保留周期性
轮询唤醒；需要调试按键时使用关闭低功耗的调试构建或先由触控唤醒。

`COMPANION_LOW_POWER_ENABLE=1` 会关闭 CubeWB trace 配置，并启用
`CFG_LPM_SUPPORTED`。这是为了避免 Cube 示例因 trace 自动永久关闭 LPM。产品
低功耗构建不得依赖连续 UART `printf`；事件诊断应使用有界日志，并在电流测量时
关闭主机持续输出。

## 功耗测量门

只有最终产品板能够关闭 `SCR-21`。每次测量须记录板 revision、供电点、电压、
固件 hash、BLE 参数、屏幕资源 revision、环境温度和仪器采样/量程设置。

1. `LP-01 standby`：屏幕保持静态，PDM/KWS 关闭，未录音，未触摸，未刷新，
   `TP_INT` 已就绪。BLE 必须使用拟发布的未连接/低占空比广播策略。电池路径或
   产品主电源输入处连续采样至少 `60 s`，平均电流必须不大于 `1 mA`。
2. `LP-02 wake`：从 `LP-01` 连续执行触摸唤醒、轻点、完整双击开始录音、再次双击
   停止。记录中断、状态机、外部 Flash 收尾、屏幕反馈和 BLE 状态，不能只看屏幕。
3. `LP-03 connected`：使用拟发布的 BLE 连接间隔、slave latency 与通知策略单独
   测量平均/峰值；它不得拿 `LP-01` 的离线结果替代，也不得永久阻塞 Stop。
4. `LP-04 fallback`：断开 `TP_INT` 或注入控制器中断配置失败，确认固件明确进入
   轮询回退并报告 `touch_irq_wake=fallback_poll`，不能错误声称 Stop 已可用。
   GPIO 不足的产品变体只能用 RTC 定时轮询作为替代；它不是中断唤醒，轮询间隔与
   实测电流/触摸延迟必须形成单独的产品证据。
5. 每条测试都保留原始电流导出、串口或有界诊断日志、触摸操作记录和结论。缺任一
   原始证据时状态保持 `hardware_current_pending`。

`TP_INT` 物理验收的串口日志可使用下列检查器。采集时需要先接 `P10 A0 -> CN10-33`
并把板级 `COMPANION_TOUCH_INT_WIRED` 设为 `1`，然后在日常页完整双击两次：第一次
启动录音，第二次停止并完成外部 Flash 收尾。检查器要求看到真实 `PC6` 配置、递增的
IRQ/consumed 计数、两次双击、录音启动/停止和 `user_store result=1`；它不替代电流
测量。

```powershell
python .\tools\verify_wb55_touch_wake_log.py --log .\.cache\validation\touch-wake\nucleo-serial-raw.log --out .\.cache\validation\touch-wake\touch-wake-report.json
```

## WBA55/WBA65 移植边界

`power_policy.[ch]` 保持 HAL-free。WBA55/WBA65 只替换以下 target glue：触控
EXTI/唤醒电平、RTC/时基、BLE radio power constraints、音频/外部 Flash 的忙状态，
以及 CubeWBA LPM 调用。不得复制 WB55 的寄存器、NVIC 号、时钟或 P2P 示例宏。

`power_target_stm32wba.[ch]` 已作为 WBA55/WBA65 的无 Cube 依赖脚手架存在：
CubeWBA 板级文件只需提供 `configure_touch_wake` 和 `set_stop_allowed` 两个回调，
先使触控中断可从目标 Stop 模式唤醒，再接受 portable policy 的 Stop 转换请求。它
不提供引脚、时钟、无线栈或低功耗寄存器默认值；这些必须来自将来的 WBA IOC、实际
封装与真机电流证据。

未来自研 WBA 板若继续使用 FT6336 触摸控制器，原理图固定为：`TP_SCL/TP_SDA`
进入共享 I2C 总线，`TP_INT` 进入一根 WBA `WAKE_N`/EXTI GPIO，`TP_RST` 由 RC 或
复位监控器提供，不额外占用 WBA GPIO。`WAKE_N` 可在电气验证后与 IMU/充电告警等
合并，WBA 醒来后通过各自 I2C 状态寄存器判定来源；不可把推挽输出直接硬并。WBA
作为 I2C 主机时，不能用“地址匹配 I2C Stop 唤醒”替代 `TP_INT`，因为 FT6336 也是
I2C 从机，无法主动发起总线事务。若产品完全没有这一根 wake GPIO，只能用 RTC
定时轮询，且必须单独验收触摸延迟和电流。

WBA65 的更多内部 Flash 也不能改变外部 Flash 优先规则：可替换表情、菜单、模型和
录音保持外置；内部 Flash 只保留启动、实时、不可替换的代码与最小救援资产。

## 防回退

```powershell
python .\tools\verify_companion_low_power_requirements.py --write-fixture
```

检查器只证明策略代码、文档、目标和 WBA 边界仍然存在。它不能替代 Stop 唤醒或
`<=1 mA` 的最终产品板测量。

## 依据

- STM32CubeWBA 的官方低功耗管理说明要求由 `UTIL_LPM_SetStopMode` 配合
  `UTIL_LPM_EnterLowPower` 管理 Stop，并由应用/无线栈的约束共同决定可否进入：
  <https://wiki.st.com/stm32mcu/wiki/Connectivity:STM32CubeWBA_Low_Power_Management>
- STM32WB 系列低功耗模式、无线栈和调试限制的官方应用笔记：
  <https://www.st.com/resource/en/application_note/dm00536340-stm32wb-series-wireless-soc-low-power-modes-stmicroelectronics.pdf>
