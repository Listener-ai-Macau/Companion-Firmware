# STM32WB Official BLE Starter

## Selected Baseline

The Companion pendant starts from the official ST STM32CubeWB package before
custom GATT services are added.

| Item | Value |
|---|---|
| Upstream | `STMicroelectronics/STM32CubeWB` |
| Git tag | `v1.24.0` |
| Release commit | `7c5aa7dcd2c0abe787f922bb06a6213c724d08e4` |
| First board | `NUCLEO-WB55RG` |
| First example | `BLE_p2pServer` |
| Product wrapper | `app/companion_pendant/` |

The tag object observed from the upstream remote is
`811bcb9758e8f65f9554913aaa0e020544bb1870`; the release commit checked out by
the submodule is `7c5aa7dcd2c0abe787f922bb06a6213c724d08e4`.

## Official Paths

CubeIDE project:

```text
third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32CubeIDE
```

Reference application image:

```text
third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/Binary/BLE_p2pServer_reference.hex
```

BLE full stack wireless coprocessor binary:

```text
third_party/STM32CubeWB/Projects/STM32WB_Copro_Wireless_Binaries/STM32WB5x/stm32wb5x_BLE_Stack_full_fw.bin
```

## Why BLE_p2pServer

`BLE_p2pServer` is the first baseline because it is an ST-provided STM32WB55
GATT server example for the P-NUCLEO-WB55 Nucleo board. It exercises the same
classes of platform surface the pendant needs first: STM32_WPAN BLE services,
IPCC/HSEM coordination, RTC/LPM support, Nucleo board support, and smartphone
or peer BLE client interaction.

This is closer to the Companion pendant's planned custom card/event/recording
service than a fixed standard profile such as Heart Rate. Product firmware will
only move into Companion-specific services after this official starter builds
and flashes under a hardware validation step.

## Product-Owned Surface

The product-owned starter surface is:

```text
app/companion_pendant/
```

For this scaffold step it contains metadata and operating rules only. It must
not copy or edit ST files until the official baseline is proven. Later steps may
copy or generate a Companion-specific CubeIDE project in this directory, with
STM32CubeWB treated as an upstream reference package.

## Reproducible Include Roots

`tools/bootstrap_stm32cubewb.ps1` restores a sparse checkout with the official
project and these STM32WB dependency roots:

- `Drivers/STM32WBxx_HAL_Driver`
- `Drivers/CMSIS/Device/ST/STM32WBxx`
- `Drivers/CMSIS/Include`
- `Drivers/BSP/P-NUCLEO-WB55.Nucleo`
- `Drivers/BSP/Components/Common`
- `Middlewares/ST/STM32_WPAN`
- `Utilities/lpm/tiny_lpm`
- `Utilities/sequencer`

The sparse checkout intentionally avoids unrelated STM32CubeWB middleware trees
that create long Windows paths and are not needed by `BLE_p2pServer`.

## Commands

Prepare the official package from a clean clone:

```powershell
pwsh -NoProfile -File .\tools\bootstrap_stm32cubewb.ps1
```

Check the CubeIDE starter without requiring hardware:

```powershell
pwsh -NoProfile -File .\tools\build.ps1 -CheckOnly
```

Check flash prerequisites without flashing:

```powershell
pwsh -NoProfile -File .\tools\flash.ps1 -CheckOnly
```

Real flash commands must run inside the workflow hardware lock:

```powershell
pwsh -NoProfile -File ..\..\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose "flash Companion WB55 official BLE starter" -Run pwsh -NoProfile -File .\tools\flash.ps1 -Execute -WorkflowLockHeld -FlashReference
```

The required lock shorthand is `aiw with-lock -Resource Companion-WB55`.
