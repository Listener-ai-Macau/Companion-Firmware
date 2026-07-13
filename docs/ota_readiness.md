# Companion Denzic OTA Readiness

## Scope

The normal Companion application exposes OTA readiness and blockers. The
dedicated loader carries update bytes through the single shared
`denzic_ota_v1` contract. Readiness, transfer, install, and activation are
separate states; a device being ready does not imply a candidate is trusted or
installed.

The machine component contract is
`docs/companion_ota_component_contract.json`. External UI, prompt, and model
packs are OTA-managed components alongside `mcu_app`; recordings, diagnostics,
settings, and other mutable user data are not update payloads.

## Readiness Contract

The BLE `OTA readiness` characteristic reports:

- state: ready, blocked, interrupted transfer, or post-update-check pending;
- battery percent, charger state, and minimum required voltage;
- stable blocker bitmap from `docs/ble_gatt_contract.md`;
- manifest version, board target, MCU, component size/hash prefix, and layout;
- interrupted-transfer token when the current candidate can resume.

Required blockers are active recording, another large transfer, diagnostics
export, low battery, wrong board target, invalid hash, and interrupted transfer
that must be resumed or discarded. The host must clear every blocker before it
starts Denzic transfer.

## One Core, Product Adapters

All Denzic products use the same protocol and host/embedded state machines.
Packages remain target-specific:

- the manifest names product, MCU family, board target, component kind, format,
  version, size, SHA-256, compatibility, and anti-rollback data;
- the host rejects a package for the wrong product instead of trying to make
  one binary run on unrelated hardware;
- WB55, WBA55/WBA65, and ESP provide independent BLE/storage/install/reboot
  adapters without changing the shared transfer protocol.

The Denzic image CRC enables same-image resume. It is not authentication. A
production bundle uses a signed manifest and per-component SHA-256 before
install or activation.

## Package Paths

`tools/package_ota_firmware.ps1` emits one Companion archive for both service
paths:

- BLE uses root `ota_manifest.json` plus `firmware_ota.bin` through Companion
  Type and the shared Rust host core;
- wired factory/recovery uses `factory/<package>/manifest.json` through
  STM32CubeProgrammer under the workflow hardware lock.

The manifest protocol/GATT fields are read from
`third_party/denzic-platform/ota/protocol/ota_v1.json`; product scripts must not
copy UUID literals.

## Component Activation

1. Stage every included component without changing active bytes.
2. Verify manifest signature, component SHA-256, target, version, and
   compatibility.
3. Install `mcu_app` through the target boot adapter when present.
4. The new app revalidates external resource candidates.
5. Atomically switch redundant active metadata and confirm the bundle.

A resource-only update does not rewrite the MCU app. A firmware-only update
preserves active external resources. Any failure keeps the old resource or
uses the internal rescue UI, and all ordinary updates preserve user data.

## Diagnostics And Evidence

Readiness and install decisions emit bounded `ota.manifest`, `ota.readiness`,
`ota.blocker`, `ota.interrupted_transfer`, and `ota.post_update_self_check`
events. Machine acceptance requires shared-core tests, Loader/Type builds,
manifest/static gates, and a real locked BLE transfer with reboot/version
confirmation. Resource-only OTA additionally requires interrupted-write and
unchanged-app/unchanged-recording evidence.
