# Companion Hardware Arrival Evidence

Plan: `companion-pendant-firmware-bringup`
Step: `2.1`
Recorded: `2026-06-22T11:47:00.4393795+08:00`
Recorder: `oai1`
Repo commit: `3f3e553`

## Current Result

Status: blocked.

The official STM32CubeWB package artifacts and local STM32 command-line tools needed for the first flash gate are present, but the local bench is not ready for real WB55 hardware validation yet because no WB55/ST-LINK board resource is confirmed.

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

## Tool Installation Update

Recorded: `2026-06-22T12:12:01.3074269+08:00`
Repo commit before update: `cad0808`

| Tool | Result | Evidence |
|---|---|---|
| STM32CubeIDE | PASS | `C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\stm32cubeidec.exe` |
| STM32CubeProgrammer CLI | PASS | `C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_2.2.400.202601091506\tools\bin\STM32_Programmer_CLI.exe`; reports STM32CubeProgrammer `v2.22.0` |
| Arm GNU Toolchain | PASS | `C:\Program Files (x86)\Arm GNU Toolchain arm-none-eabi\14.2 rel1\bin\arm-none-eabi-gcc.exe`; reports `14.2.1 20241119` |
| OpenOCD | PASS | `C:\Users\Billy\AppData\Local\Microsoft\WinGet\Packages\xpack-dev-tools.openocd-xpack_Microsoft.Winget.Source_8wekyb3d8bbwe\xpack-openocd-0.12.0-7\bin\openocd.exe`; reports xPack OpenOCD `0.12.0+dev-02228-ge5888bda3-dirty` |
| `tools/build.ps1 -CheckOnly` after installation | PASS | Detects the CubeIDE command-line tool and official starter project |
| `tools/flash.ps1 -CheckOnly` after script update | PASS | Detects the CubeIDE-bundled STM32CubeProgrammer CLI, reference hex, and BLE full stack binary |
| `tools/build.ps1` headless official example build | PASS | `BLE_p2pServer/Debug` built with `stm32cubeidec.exe`; build output reported 0 errors, 0 warnings, size `text=72744 data=578 bss=13767` |

## Human Confirmation

A visible Chinese Windows prompt was shown for the operator to choose whether the Companion WB55 bench was ready despite automatic detection failure.

Operator result: `continue blocked`.

## Blocking Items

- `NUCLEO-WB55RG` or the selected STM32WB board is not confirmed on the bench.
- Companion debug/serial resource is not recorded in the workflow board ledger.
- E-paper, MEMS microphone, SPI NOR flash, button, battery/charger/fuel gauge, and measurement method are not confirmed for the later bench gate.

## Unblock Requirements

Before `2.2` real flash or BLE validation begins:

- Connect or identify the `NUCLEO-WB55RG` or selected STM32WB board.
- Install STM32CubeIDE and STM32CubeProgrammer, or provide exact executable paths.
- Record the narrowed debug/serial/BLE resource as `Companion-WB55` in the workflow board ledger.
- Run real flash and BLE capture only inside `aiw with-lock -Resource Companion-WB55`.
