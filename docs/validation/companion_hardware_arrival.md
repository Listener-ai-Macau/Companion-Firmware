# Companion Hardware Arrival Evidence

Plan: `companion-pendant-firmware-bringup`
Step: `2.1`
Recorded: `2026-06-22T11:47:00.4393795+08:00`
Recorder: `oai1`
Repo commit: `3f3e553`

## Current Result

Status: ready for locked FUS/BLE-stack diagnostic.

The official STM32CubeWB package artifacts, local STM32 command-line tools, and the first WB55 bench resource are present. The board is recorded in the workflow board ledger as `Companion-WB55`, and real flash, FUS, serial, BLE capture, or real-device validation must still run only through the workflow hardware lock.

The latest user-visible symptom is that the Companion BLE device is not found from Type. Treat that as a CPU2 wireless-stack/FUS diagnostic gate before A1/A2 or OTA acceptance; do not assume the STM32WB BLE stack is provisioned until `tools/provision_companion_wireless_stack.ps1 -Execute -ReadFusInfo` succeeds under lock.

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

## Bench Resource Update

Recorded: `2026-06-27T10:24:46+08:00`
Recorder: `codex`
Repo commit before update: `78a5a59`

| Resource | Result | Evidence |
|---|---|---|
| First WB55 board | PASS | `NUCLEO-WB55RG`, ST-LINK serial number `066EFF535570514867221931`, observed by prior locked hardware acceptance flash evidence; board voltage evidence was 3.24 V |
| Workflow board ledger | PASS | `aiw board-ledger get -Resource Companion-WB55` returns board id `nucleo-wb55rg-stlink-066EFF535570514867221931` and board rev `NUCLEO-WB55RG` |
| Debug / flash resource | PASS | Use workflow resource `Companion-WB55` for SWD, FUS, wireless-stack provisioning, and STM32CubeProgrammer flash operations |
| BLE validation resource | PASS | Use workflow resource pair `Companion-WB55,BLE-Companion` for Type Companion BLE discovery, A1/A2, BLE OTA, and aggregate hardware acceptance |
| Serial VCP | PASS | `tools/capture_nucleo_serial.ps1 -CheckOnly` auto-detected `STMicroelectronics STLink Virtual COM Port (COM13)` with PNP id `USB\VID_0483&PID_374B&MI_02\7&ECAD0C&0&0002`; board ledger now records `com=COM13` |
| Product peripheral bench | DEFERRED | E-paper, PDM MEMS microphone, SPI NOR flash, button, battery/charger/fuel gauge, and measurement method are deferred to the later pendant MVP bench gate; the NUCLEO first gate is flash/FUS/BLE bring-up |
| FUS/BLE stack state | PENDING | A locked FUS read was attempted on `2026-06-27T10:54:33+08:00`, but the Chinese operator prompt timed out/cancelled before any hardware command ran; evidence: `.cache/validation/companion-wireless-stack-20260627-105431/companion-wireless-stack-summary.json` has `status=CANCELLED` and `steps=[]`. Run the FUS diagnostic again while the operator can confirm the prompt |

## Human Confirmation

A visible Chinese Windows prompt was shown for the operator to choose whether the Companion WB55 bench was ready despite automatic detection failure.

Operator result: `continue blocked` on `2026-06-22`; superseded by the `2026-06-27` bench resource update above.

## Blocking Items

- CPU2 FUS / BLE wireless-stack state is not yet read; the current Type-side symptom is "Companion BLE not found".
- E-paper, MEMS microphone, SPI NOR flash, button, battery/charger/fuel gauge, and measurement method remain deferred for the later pendant MVP bench gate.

## Unblock Requirements

Before `2.2` real flash or BLE validation begins:

- Keep the `Companion-WB55` board-ledger entry available for this bench.
- Use `tools/provision_companion_wireless_stack.ps1 -Execute -ReadFusInfo` under `aiw with-lock -Resource Companion-WB55` before expecting BLE advertising.
- If FUS is classified as `fus_v2_2_ready_for_wireless_stack`, install `stm32wb5x_BLE_Stack_full_fw.bin` at `0x080D0000` under the same lock before A1/A2 or OTA validation.
- Run real flash and BLE capture only inside `aiw with-lock -Resource Companion-WB55`.
