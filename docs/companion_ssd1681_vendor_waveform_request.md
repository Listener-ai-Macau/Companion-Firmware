# GDEY0154D67-T03 Manufacturer Waveform Request

## Purpose

This is the concrete material request for the Good Display panel supplier or
seller. It unblocks only a bounded SSD1681 refresh-profile investigation; it
does not authorize a firmware or panel experiment by itself.

The target under test is:

| Field | Value |
|---|---|
| Panel model | `GDEY0154D67-T03` |
| Resolution | `200 x 200`, black and white |
| Display controller | `SSD1681` |
| Touch controller | `FT6336U` |
| Panel marking reported by owner | `N524110506 / 0154BN-D67-D2` |
| Current adapter | Good Display `ESP32-FTS02`, selector `P3 = 2.2` |

The public Good Display material already establishes the basic product facts,
nominal `0.3 s` partial refresh, `1.5 s` fast refresh and `2 s` full refresh.
It also publishes a specification and STM32 sample download. Those are useful
baselines, but they do not identify the supplied panel lot, the intended
temperature profile, or the residual-image limit for this product.

## What We Need From The Supplier

Ask for the following as one response package. The supplier may provide C
source, an archive, a binary waveform file, a command table, or an application
note. We will create the internal `CWF1` manifest after receipt; the supplier
does not need to know that internal format.

### 1. Exact applicability

1. Written confirmation that the material applies to `GDEY0154D67-T03`, not a
   generic SSD1681 or a nearby 1.54-inch panel.
2. The applicable manufacturing lot, FPC marking, date-code range, or another
   traceable way to decide whether it covers `N524110506 / 0154BN-D67-D2`.
3. Controller revision and panel/FPC revision, if they affect refresh setup.
4. The documentation/code revision, release date, supplier contact and source
   channel that supplied the package.

### 2. Complete operating profiles

For each supported profile, please provide the exact initialization and update
sequence, including all command bytes and their order:

| Required profile | Intended product use |
|---|---|
| Full refresh | Unknown baseline, fault recovery and periodic deep cleanup |
| Fast refresh | Explicit visual boundary such as menu entry/exit |
| Partial refresh | Small interaction and expression changes |

For every profile, include:

1. Reset, power, booster/VCOM and display-option setup that must precede it.
2. Temperature-sensor or temperature-register steps, including command values.
3. LUT/waveform selection or payload. If the SSD1681 uses an internal LUT,
   provide the exact selection commands. If it uses externally sent LUT bytes,
   provide the complete byte payload, byte count and byte order.
4. RAM-plane write rules: which old/new planes to write, whether a base image
   is required first, partial-window alignment limits, and whether the current
   frame must be copied after an update.
5. Update-control command values, BUSY polarity/timeout and any required wait,
   power-down or reset sequence after completion.
6. The maximum consecutive fast/partial updates before a cleanup refresh and
   the supplier's stated ghosting/recovery rule.

### 3. Temperature information

1. The temperature range for each profile and the test temperature behind its
   published timing.
2. Whether the display controller's internal sensor is expected to be used,
   and the exact command sequence if it is.
3. If selection depends on a temperature table, provide the original table and
   the selection rule. A statement such as "room temperature" must include a
   numeric range.
4. Any known visible effect or restriction outside the listed range.

We can begin a restricted room-temperature test only if the vendor explicitly
binds the profile to a numerical room-temperature range. That is not a claim
that the panel automatically measures temperature in normal product use.

### 4. Integrity And Demonstration Evidence

1. Original archive/file names and SHA-256 or CRC, if available. If the
   supplier cannot provide a checksum, we will compute SHA-256 upon receipt
   and record the delivery e-mail and revision.
2. A short demonstration record for the same panel/profile: temperature,
   number of repeated partial updates, before/after photo or video, and the
   cleanup step used to remove residue.
3. Known restrictions such as white-to-black-only partial updates, mandatory
   base-map initialization, minimum update rectangle, or a limit on partial
   cycles after sleep.

## Insufficient Material

The following does not unblock an experiment on its own:

- A generic SSD1681 data sheet without a `GDEY0154D67-T03` applicability
  statement.
- A LUT copied from a different panel size, batch, controller revision or web
  example.
- A screenshot of a command sequence instead of the original source/binary or
  complete typed command table.
- A claim that partial refresh is supported without the temperature/profile
  binding and cleanup rule.
- A nominal timing number with no profile, test condition or residual-image
  information.

## Message To Send

```text
您好，我们正在使用 Good Display GDEY0154D67-T03（200x200，SSD1681，带
FT6336U 触摸）。屏幕/FPC 丝印为 N524110506 / 0154BN-D67-D2，配套转接板为
ESP32-FTS02，P3 选择 2.2。

我们需要在 STM32 上实现与本批屏匹配的 full / fast / partial 刷新，并控制局刷
残影。请提供适用于 GDEY0154D67-T03 且可追溯到该批次或 FPC 标识的原始技术资料：

1. full、fast、partial 三种刷新的完整初始化、温度处理、LUT/波形选择或完整
   LUT 数据、旧/新 RAM 平面写法、更新控制命令、BUSY 极性和结束流程；
2. 每个 profile 对应的温度范围、测试温度，以及是否必须用 SSD1681 内部温度
   传感器或温度表；
3. 连续 partial/fast 的最大次数、何时需要 cleanup/full，以及残影限制；
4. 原始 STM32/C 示例工程、波形二进制或完整命令表均可。请保留文件名、版本、
   发布日期，并提供 CRC/SHA-256（如有）；
5. 最好附同型号面板在对应温度下连续局刷和清残的演示记录。

我们已有公开规格书和公开 STM32 示例，但不会把通用 SSD1681 或其他尺寸屏幕的
LUT 用在这块屏上。请确认以上资料是否覆盖 N524110506 / 0154BN-D67-D2；如不覆盖，
请告知应使用的批次/温度对应资料。
谢谢。
```

## Internal Intake Rule

On receipt, archive the original delivery unchanged. Record its SHA-256,
source identity, revision, model/lot scope and temperature scope before parsing
it. The existing fail-closed rule in
`docs/companion_ssd1681_vendor_waveform_freeze.md` remains authoritative: a
matching package must pass model, lot, temperature, payload-integrity and
source checks before a single hardware candidate is considered.
