# Companion Pendant Starter

This directory is the product-owned starter surface for the Companion pendant.
It does not fork or edit `third_party/STM32CubeWB`; it records the official ST
baseline that must pass before Companion-specific GATT work starts.

Current starter baseline:

- Board: `NUCLEO-WB55RG`
- Upstream: `STMicroelectronics/STM32CubeWB`
- Tag: `v1.24.0`
- Commit: `7c5aa7dcd2c0abe787f922bb06a6213c724d08e4`
- Official example: `BLE_p2pServer`
- CubeIDE project:
  `third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32CubeIDE`

Product rules:

- Keep ST files under `third_party/STM32CubeWB` read-only for product work.
- Use `tools/bootstrap_stm32cubewb.ps1` to restore the exact official package.
- Use `tools/build.ps1 -CheckOnly` and `tools/flash.ps1 -CheckOnly` before any
  hardware window.
- Real flashing must run under:
  `aiw with-lock -Resource Companion-WB55`.

The next firmware step may copy or generate a Companion-specific CubeIDE project
under this directory after the official BLE_p2pServer baseline is proven.

Diagnostic logging starts in `diag_log/` as a portable RAM ring with bounded
tail export helpers. A later SPI flash retained ring may mirror events, but it
must keep the same bounded cursor/source contract and avoid ESP partition
assumptions.
