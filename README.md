# Companion Firmware

Companion Firmware starts from the official ST STM32CubeWB package for the
NUCLEO-WB55RG pendant prototype.

Current bring-up baseline:

- Board: `NUCLEO-WB55RG`
- Upstream package: `STMicroelectronics/STM32CubeWB`
- Pinned upstream tag: `v1.24.0`
- First official example: `BLE_p2pServer`
- Example path:
  `third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer`

Run this after cloning or when the submodule checkout is incomplete:

```powershell
.\tools\bootstrap_stm32cubewb.ps1
```

Then follow [docs/bringup_steps.md](docs/bringup_steps.md).

Do not edit files directly under `third_party/STM32CubeWB` for product work.
Use it as the official reference package. Product firmware should be copied or
generated into this repo's own application directory after the official BLE
example is proven on hardware.
