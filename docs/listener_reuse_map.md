# Listener Reuse Map for Companion Firmware

This map records what Companion-Firmware may reuse from Listener and what must
be replaced for STM32WB. Listener repositories are read-only source references
for this step.

| source path | reuse class | stm32 target | first step | risk |
|---|---|---|---|---|
| `Listener-Firmware/ports/esp32/audio_capture/` | adaptation | STM32 HAL/LL PDM or SAI/DFSDM-style capture path, DMA buffers, and low-power mic gating | Step 1.5 microphone capture and recording FSM port | Keep microphone behavior and validation ideas, but do not copy ESP-IDF I2S/PDM drivers, ESP task wiring, or ESP GPIO/power policy. |
| `Listener-Firmware/components/voice_recording_control/` | adaptation | Companion recording FSM independent from ESP FreeRTOS assumptions, using STM32 scheduler/timer hooks and Companion BLE state | Step 1.5 microphone capture and recording FSM port | Reuse state-machine lessons such as pending start, cancel, recovery, host cleanup, and transfer boundaries; do not copy ESP-specific control effects. |
| `Listener-Firmware/ports/esp32/ble_audio_stream/` | reference only | STM32_WPAN GATT recording-list and chunk-pull characteristics | Step 1.3 Companion BLE GATT protocol and host probe contract | BLE audio/chunk transfer lessons are useful, but NimBLE-only code and MTU/event-loop assumptions are no reuse. |
| `Listener-Firmware/components/firmware_ota/` | reference only | STM32CubeWB BLE OTA readiness notes, manifest discipline, low-battery blockers, interrupted-transfer behavior, and recovery path | Step 1.8 BLE OTA readiness contract and manifest discipline | ESP-IDF OTA slots, ESP partition assumptions, rollback APIs, and bootloader layout are no reuse. |
| `Listener-Firmware/ports/esp32/ble_firmware_ota/` | reference only | STM32_WPAN OTA control/data GATT shape after official ST OTA reference is understood | Step 1.8 BLE OTA readiness contract and manifest discipline | Reuse preflight and host-transfer concepts, not NimBLE service code. |
| `Listener-Firmware/components/diag_log/` | adaptation | STM32 diagnostic log module backed first by RAM/serial, later SPI flash ring if needed | Step 1.4 STM32 diagnostic log foundation | Event schema, source masks, bounded dump, and AI-readable summaries are useful; ESP flash partition and NVS assumptions are no reuse. |
| `Listener-Firmware/tools/` | adaptation | Companion build, bootstrap, static checks, CubeProgrammer flash wrappers, serial capture, BLE probe, and validation artifact tools | Step 1.2 STM32CubeWB official BLE starter scaffold and later validation steps | Script shape and evidence style transfer well; commands must use STM32CubeIDE/CMake/CubeProgrammer, not idf.py or esptool. |
| `Listener-Type/src-tauri/src/embedded_ble*` | adaptation | Desktop Companion BLE fixture and host probe for status, card write, recording metadata, chunk pull, logs, and OTA preflight | Step 1.9 Desktop BLE fixture tool and validation matrix | Reuse scan/connect/error handling patterns; UUIDs, packet model, and UI naming must become Companion-specific. |
| `Listener-Type/src-tauri/src/firmware_ota.rs` and `commands.rs` OTA paths | reference only | Companion host-side OTA package validation and BLE transfer preflight | Step 1.8 BLE OTA readiness contract and manifest discipline | Manifest validation and failure-path UX are useful; firmware target, image format, and transport are STM32-specific. |
| `Listener-Type/src-tauri/src/recorder.rs`, `asr/*`, and `persistence.rs` recording retention paths | reference only | Companion host evidence for recording list, retained WAV/debug files, and privacy/delete flow | Step 1.7 SPI flash recording cache and chunk pull model | Host retention/deletion lessons apply, but pendant storage protocol must be designed for local SPI flash and BLE pull. |
| `Listener-Firmware/partitions.csv`, ESP board pins, ESP power manager shutdown policy | no reuse | STM32CubeWB linker/flash layout, HAL power domains, RTC/LPM, IPCC/HSEM, NUCLEO-WB55RG board support | Steps 1.2, 1.4, 1.8 | Explicitly forbidden: copying ESP partition assumptions, ESP GPIO/power policy, ESP boot/OTA slots, or current-sense board contracts. |

## STM32 Replacement Surfaces

Companion-Firmware must replace ESP-specific surfaces with:

- `STM32CubeWB` official package and examples.
- `STM32_WPAN` BLE stack and ST GATT application structure.
- HAL/LL drivers for GPIO, SPI, I2C, PDM/SAI/DFSDM-style capture, DMA, and timers.
- IPCC and HSEM coordination for STM32WB CPU1/CPU2 communication.
- RTC/LPM for low-power wake and recording/display scheduling.
- STM32CubeProgrammer for flashing, wireless stack provisioning, and recovery.
- NUCLEO-WB55RG board support for the first bench target.

## Forbidden Copy Rules

Do not copy:

- ESP-IDF drivers or `idf.py` build assumptions.
- ESP partition assumptions, OTA slot layout, NVS storage model, or ESP bootloader rollback APIs.
- NimBLE-only code, event names, or connection-state assumptions.
- ESP GPIO/power policy, PWR_HOLD behavior, or Listener board-specific battery/current-sense contracts.

## First Reuse Order

1. Document the official ST BLE starter and keep the submodule read-only.
2. Define the Companion GATT contract before firmware services are customized.
3. Build the STM32 diagnostic log foundation before microphone, flash cache, or OTA claims.
4. Port the microphone/recording FSM as behavior, not ESP code.
5. Reuse Listener validation style: runnable checks first, hardware locks only for flash, serial, BLE capture, or real-device validation.

