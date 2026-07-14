# Companion 电子纸交互性能目标

## 目的

把 owner 对“非常卡顿”的 P0 反馈变成可测、可复验、可移植的产品目标。Companion 不承诺把
电子纸伪装成 OLED；目标是让触控路径立即被系统接住，局刷在该面板的物理能力内尽快稳定，且不让
全刷、维护刷或 UART 日志制造额外等待。

## 来源与边界

- Good Display 官方 GDEY0154D67-T03 页面（2026-07-14 查阅）给出 200x200 SSD1681 面板的
  `partial=0.3 s`、`fast=1.5 s`、`full=2 s`；同页说明 FT6336U 电容触控和 I2C 接口。
  <https://www.good-display.com/product/258.html>
- Good Display 的同型号说明还建议 partial/fast 连续约五次后再做一次全屏清理，以抑制残影。
  <https://www.good-display.com/blank7.html?productId=388>
- E Ink Carta 1200 官方资料强调更快响应与 REAGL 这类减少全刷的平滑过渡。它是成熟产品的
  设计方向，不是本 SSD1681 面板的数值承诺。
  <https://www.eink.com/brand/detail/carta1200>

下列时间仅在 20-30 C、外部 Flash CEMP 已挂载、屏幕 baseline 已知、正常 quiet 镜像下衡量。
温度、未知 baseline、传输故障和恢复全刷必须单独记录，不能混入日常 p95。

## 用户可感知目标

| 层级 | 目标 | 硬性回退线 | 证明方法 |
|---|---|---|---|
| 触控唤醒 | PC6 到 FT6336 首样本 `<=10 ms` p95；Stop 后首个 contact 立即进入 5 ms 手势时间线 | 不得靠第二次按压唤醒 | reset-bounded trace 的 IRQ/consumed、sample_age 与 wake marker |
| 轻触判定 | 手指离开后 `<=20 ms` p95 判为 tap 并入队；快速轻触定义为按下到离开 `<500 ms` | 不得把有效快速轻触变为 3 s 菜单长按 | `gesture=tap`、`daily_reaction` 顺序和 20 次实板操作 |
| 日常表情首帧 | tap 释放到一张差分表情稳定 `<=350 ms` p95 | `>450 ms` 或出现 idle 预刷新即 NO_GO | `daily_reaction -> expression -> display_result` 和面板观察 |
| 滑动/双击 | 已接触期间继续 5 ms 服务；手势确认后不额外插入延迟维护刷 | 不丢 swipe/double-tap，不将横滑/竖拖误作点击 | trace 与 focused popup |
| 菜单边界 | 进入/退出允许一次 Mode-1 fast clean，目标 `<=1.6 s` p95 | `>2.0 s` 或一次边界多次闪烁为 NO_GO | `menu_boundary` 到 `display_result`，实屏观察 |
| 残影维护 | 常规前五次局刷只用无闪烁差分；第六次或显式菜单边界才做一次清理 | 任何普通 tap 的延后清理、周期性刷屏或 full refresh 为 NO_GO | refresh policy trace 和实屏 6 次序列 |
| 全刷 | 只允许开机未知 baseline、故障恢复或明确维护；目标接近厂商 `2 s` | 日常触控/低功耗唤醒触发 full refresh 为 NO_GO | refresh reason、waveform 和 focused popup |

## 当前基线

`docs/validation/companion-low-power-short-touch-wake-20260714.json` 的真实 NUCLEO-WB55RG
trace 已显示一张差分 sleepy 和局刷完成约 `306-307 ms`，接近面板 `0.3 s` 规格；菜单 Mode-1
边界实测 `1740 ms`，高于 `<=1.6 s` 的优化目标。该次操作者验收仍失败：PC6/FT6336/Stop
唤醒均发生，但首个 contact 保持 `3006 ms`，被分类为 `long_press` 并进入菜单，未形成可用于
判断 tap 首帧的样本。

## 执行顺序

1. 先以 `<500 ms` 的真实轻触获得 `PC6 -> contact -> tap -> daily_reaction -> visible expression`
   完整基线；不把 long press 样本算作 tap 通过或失败。
2. 用 trace 剔除阻塞 UART、idle 预刷新、延后维护和不必要的全刷。
3. 再单独优化 Mode-1 菜单边界，比较温度/profile/传输耗时；不得为了快而接受残影或破坏
   WB55/WBA portable refresh policy。
4. 每次改变都重新覆盖轻触、滑动、双击录音、3 s 菜单、右滑退出和 6 次局刷清理。

## WBA55/WBA65 边界

指标、手势语义、external-Flash-first 资源规则和 refresh cadence 属于 portable policy。WBA
只替换 RTC/Stop、FT6336 I2C/EXTI、SPI/panel waveform 和测量 adapter；不得复制 WB55 的 pin、HAL
调用或以 WB55 实测时间直接宣称 WBA 实板已通过。
