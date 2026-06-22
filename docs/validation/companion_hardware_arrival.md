# Companion Hardware Arrival Evidence

Plan: `companion-pendant-firmware-bringup`
Step: `2.1`
Recorded: `2026-06-22T11:47:00.4393795+08:00`
Recorder: `oai1`
Repo commit: `3f3e553`

## Current Result

Status: blocked.

The official STM32CubeWB package artifacts needed for the first flash gate are present, but the local bench is not ready for real WB55 hardware validation yet.

## Automatic Checks

| Check | Result | Evidence |
|---|---|---|
| Official `BLE_p2pServer_reference.hex` | PASS | `third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/Binary/BLE_p2pServer_reference.hex`, 106681 bytes |
| BLE full stack binary | PASS | `third_party/STM32CubeWB/Projects/STM32WB_Copro_Wireless_Binaries/STM32WB5x/stm32wb5x_BLE_Stack_full_fw.bin`, 129460 bytes |
| `tools/build.ps1 -CheckOnly` | PARTIAL | Official starter project exists; STM32CubeIDE CLI was not found |
| `tools/flash.ps1 -CheckOnly` | PARTIAL | Reference hex and BLE full stack binary exist; STM32CubeProgrammer CLI was not found |
| STM32CubeIDE command lookup | MISSING | `stm32cubeide.exe` was not found in `PATH` or common ST install directories |
| STM32CubeProgrammer command lookup | MISSING | `STM32_Programmer_CLI.exe` was not found in `PATH` or common ST install directories |
| ST-LINK / STM32WB present-device scan | MISSING | No present `VID_0483`, `ST-LINK`, or STM32WB-like USB device was detected |
| Serial resources | NOT WB55 | Present serial devices are ESP-style `VID_303A` ports, including Listener `COM10` |

## Human Confirmation

A visible Chinese Windows prompt was shown for the operator to choose whether the Companion WB55 bench was ready despite automatic detection failure.

Operator result: `continue blocked`.

## Blocking Items

- `NUCLEO-WB55RG` or the selected STM32WB board is not confirmed on the bench.
- STM32CubeIDE path is not confirmed.
- STM32CubeProgrammer path is not confirmed.
- Companion debug/serial resource is not recorded in the workflow board ledger.
- E-paper, MEMS microphone, SPI NOR flash, button, battery/charger/fuel gauge, and measurement method are not confirmed for the later bench gate.

## Unblock Requirements

Before `2.2` real flash or BLE validation begins:

- Connect or identify the `NUCLEO-WB55RG` or selected STM32WB board.
- Install STM32CubeIDE and STM32CubeProgrammer, or provide exact executable paths.
- Record the narrowed debug/serial/BLE resource as `Companion-WB55` in the workflow board ledger.
- Run real flash and BLE capture only inside `aiw with-lock -Resource Companion-WB55`.
