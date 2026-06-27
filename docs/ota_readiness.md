# Companion OTA Readiness

This document defines the Companion pendant OTA readiness contract. The current
firmware surface is still not a firmware swap implementation: real image
transfer, flash-bank selection, refresh timing, reboot, and post-update
confirmation remain gated by the bootloader and hardware validation steps.

## ST Baseline

The Companion firmware starts from STM32CubeWB on `NUCLEO-WB55RG` for bench
bring-up, then moves to the product target `COMPANION-PENDANT-CE` /
`STM32WB55CEUx`. The OTA data path must be selected from ST examples such as
`BLE_Ota` or `BLE_p2pServer_ota` after the basic Companion GATT server is
proven. This contract records the readiness/status surface that a host can probe
before using an ST OTA transport.

## Bootloader And Flash Layout

The product boot and flash contract lives in
`docs/bootloader_flash_layout.md`. The stable decision for the first CE OTA path
is:

- internal flash contains one resident bootloader plus one runnable Companion app
  image; it does not contain two complete app slots.
- external QSPI NOR contains one `ota_staging` partition for a full pending
  image, plus separate `recording_cache`, `diag_log_mirror`, and redundant boot
  metadata areas.
- factory recovery remains STM32WB ROM DFU / SWD through STM32CubeProgrammer.
- an external `golden_image` partition is optional later; dual external OTA
  partitions are not required for the first implementation.

## Host Contract

The BLE `OTA readiness` characteristic reports:

- `ready_state`: `ready`, `blocked`, `interrupted_transfer`, or
  `post_update_check_pending`.
- `boot_slot`: placeholder text until the STM32WB OTA example defines the true
  image bank or boot path.
- `battery_percent`, `charger_present`, and `minimum_required_mv`.
- `blocker_bitmap` with stable blocker bits listed in
  `docs/ble_gatt_contract.md`.
- Manifest summary fields: `manifest_version`, `board_target`, `mcu`,
  `image_size`, `image_sha256_prefix`, and bootloader/layout policy.
- `interrupted_transfer_resume_token` when a later OTA data path needs recovery
  instead of starting from byte zero.

The host may read and subscribe to this characteristic. The firmware must not
perform a real firmware swap, set boot state, erase image banks, or accept OTA
data writes in this step.

## Manifest Discipline

The Companion manifest is validated before the host offers an update. It covers:

- version and schema version
- board target and MCU compatibility
- image size and SHA-256 hash
- compatibility with the STM32CubeWB baseline and Companion GATT contract
- low-battery guard
- rollback notes
- recovery notes
- required post-update self-checks

The low-battery guard is a policy gate, not a user-facing prompt in this step.
The host should treat a low-battery blocker as retryable after charge.

Required blockers:

- `recording_active`
- `transfer_active`
- `diag_export_active`
- `low_battery`
- `wrong_board_target`
- `invalid_hash`
- `interrupted_transfer`

## Shared Wireless And Wired Package

`tools/package_ota_firmware.ps1` emits one Companion package that supports both
paths:

- wireless OTA uses the package root `ota_manifest.json` plus
  `firmware_ota.bin`.
- wired factory recovery uses `factory/<package>/manifest.json` and must flash
  both artifacts listed there: `Companion_BLE_Ota_Loader.hex` first, then the
  Companion app hex.

The repository wired path is `tools/flash.ps1 -FlashPackage -PackagePath
<package-or-factory-manifest>` inside the workflow hardware lock. Real flashing
shows a Chinese desktop confirmation prompt and plays a sound before touching
the board, so the operator can confirm ST-LINK USB, Type, and serial monitors
are in the expected state.

## Diagnostics

Readiness and manifest decisions are mirrored into the diagnostic log. The
minimum events for this step are:

- `ota.manifest`
- `ota.readiness`
- `ota.blocker`
- `ota.interrupted_transfer`
- `ota.post_update_self_check`

These are bounded status events that can later be exported through
`diagnostics/log pull`; they are not full OTA packet dumps.

## Listener Reuse Boundary

Listener OTA work is reusable as policy and validation discipline:

- manifest schema and checker shape
- blocker taxonomy for recording, transfer, diagnostics, and low-battery
- diagnostic event summaries for host-visible failures
- rollback and recovery documentation style
- post-update self-check gating before a host marks an update complete

Listener implementation details must not be copied into Companion:

- ESP-IDF OTA slot APIs
- ESP partition-table or NVS assumptions
- NimBLE service registration and mbuf handling
- ESP bootloader rollback method names or partition labels
- Listener keyboard-specific BLE UUIDs, battery thresholds, or GPIO policy

Companion must map the policy to STM32_WPAN, STM32CubeProgrammer recovery, the
CE bootloader/QSPI staging layout, and the ST `BLE_Ota` / `BLE_p2pServer_ota`
reference selected in a later step.
