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

For the recommended Codex + CubeIDE development loop, see
[docs/codex_development_workflow.md](docs/codex_development_workflow.md).

## Product CubeIDE project

The Companion Pendant product CubeMX/CubeIDE configuration lives at the repo
root as `Companion_Pendant.ioc` (target MCU STM32WB55CEUx / UFQFPN48). Pinout,
peripheral mapping, and open/generate/build steps are documented in
[docs/companion_pendant_ioc.md](docs/companion_pendant_ioc.md). Product
application source (recording / diag_log / e-paper) stays under
`app/companion_pendant/` and is linked into the project as a source folder.

Do not edit files directly under `third_party/STM32CubeWB` for product work.
Use it as the official reference package. Product firmware should be copied or
generated into this repo's own application directory after the official BLE
example is proven on hardware.
