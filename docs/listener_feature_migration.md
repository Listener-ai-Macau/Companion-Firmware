# Listener Feature Migration

This document maps mature Listener behavior into Companion-Firmware without
copying ESP32 or desktop-specific implementation surfaces. Listener repositories
are source references. Companion targets must stay STM32WB, STM32_WPAN, and
Companion-product specific.

## Migration Map

| Listener capability | Companion target | reuse mode | first implementation step | validation | risk |
|---|---|---|---|---|---|
| Listener-Type BLE recovery | Desktop host bridge fixture that can reconnect, classify stale GATT/cache, paired-device disconnect, OTA reboot windows, and low-power idle wake cases against Companion services. | Behavior reference from `Listener-Type/src-tauri/src/embedded_ble.rs` and `coordinator.rs`; no UUID, device-name, or UI string reuse. | Step 1.2 Desktop host bridge fixture and BLE failure classifier. | `tools/companion_ble_probe.ps1 -SelfTest` plus fixture cases for disconnect, stale cache, OTA reboot, and low-power idle recovery guidance. | Windows BLE errors are host-specific; Companion guidance must mention device wake/re-pair/export diagnostics instead of raw WinRT or Listener wording. |
| actionable BLE failure classification | Companion failure taxonomy that maps invalid payload, busy, record missing, offset out of range, CRC/hash mismatch, privacy lock, OTA blocker, and unsupported schema to user-actionable host states. | Adapt the classification pattern and tests, not Listener enum names or service contracts. | Step 1.2 Desktop host bridge fixture and BLE failure classifier. | Host fixture asserts each failure class has retry policy, user guidance, and diagnostic export context. | Lazy string matching can hide product defects; static fixtures must include negative cases for non-retryable errors. |
| diagnostics bundle | Companion diagnostic bundle built from bounded diagnostic log pulls, BLE session state, OTA blockers, recording cache status, and board/build identity. | Adapt Listener diag_log bundle shape and AI-readable summaries while keeping Companion source masks and privacy rules. | Step 1.3 Companion diagnostic bundle and bounded log export. | `tools/verify_diag_log_static.py`, `tools/decode_diag_log.py`, and fixture bundle checks under `docs/validation/`. | Unbounded dumps and raw recording content are forbidden; exported evidence must be bounded and privacy-safe. |
| Recording FSM stop/cancel/race lessons | The single `Denzic-Platform/audio/embedded` C core with explicit start, recording, stopping, stored, failed, cancel, cleanup, and PCM accounting; STM32 keeps only SAI/PDM, storage, BLE, input, and scheduler adapters. | Listener semantics are extracted once into Denzic Platform. Companion must not own a second transition implementation. | Step 1.4 shared recording core and cache transfer hardening. | Platform C tests, `tools/verify_recording_fsm_static.py`, WB55 build, and synthetic plus real two-double-tap fixtures. | Stop/cancel races can corrupt cache state; blocking target capture can also prevent the stop input from being serviced. |
| recording byte-offset transfer | Companion recording chunk pull uses recording id, byte offset, requested length, total length, packet sequence, CRC, and final SHA-256. | Use Listener transfer failure lessons only; Companion byte offset and total length are the source of truth. | Step 1.4 Recording FSM and cache transfer hardening. | `tools/companion_ble_probe.ps1 -SelfTest` and `tools/verify_recording_cache_model.py` cover resume, dedupe, CRC, final hash, and offset bounds. | Reintroducing chunk/fragment ambiguity would break resume and delete verification. |
| delete-after-sync privacy | Host may request delete-after-sync only after validating recording id, total length, and SHA-256; firmware refuses delete during active recording or mismatched metadata. | Adapt Listener retention/privacy lessons, not desktop persistence or OS keyring behavior. | Step 1.4 Recording FSM and cache transfer hardening. | Recording cache fixture proves delete is refused before host verification and accepted only for matching immutable metadata. | Premature delete can lose user audio; privacy wipe must be explicit and auditable. |
| OTA manifest discipline | Companion OTA readiness exposes manifest version, target board, image size, hash prefix, minimum battery/voltage, charger status, and blocker bitmap before any data path. | Reference Listener manifest validation and failure UX; actual OTA transport must come from ST STM32WB OTA examples. | Step 1.6 OTA manifest preflight and blocker UX hardening. | `tools/check_ota_manifest.ps1`, `tools/verify_ota_contract_static.py`, and manifest fixtures under `docs/validation/ota/`. | ESP OTA slots, rollback APIs, and partition layout do not apply to STM32WB; readiness must not become a custom large-write OTA path. |
| low-power state modeling | Companion device status models active mode, battery/charge, transfer activity, recording activity, diagnostics export, display refresh, and OTA blockers before sleep/wake claims. | Reuse Listener low-power diagnostic lesson: model blockers and wake guidance explicitly. Replace PWR_HOLD and Listener LED assumptions. | Step 1.6 OTA manifest preflight and blocker UX hardening, with hardware proof deferred to phase 2 gates. | Static contract checks plus later locked hardware validation for real RTC/LPM, BLE reconnect, serial capture, and board current behavior. | Without hardware, this is a contract only; do not claim real sleep, wake, or current draw until the hardware gate is unblocked. |
| product validation matrices | Companion scripted and manual matrices cover BLE bridge recovery, recording transfer, diagnostics export, OTA blocker UX, low-power recovery, and privacy delete flows. | Reuse Listener matrix discipline: runnable first, hardware locks only for flash, serial, BLE capture, or real-device validation. | Step 2.2 Pendant migrated-feature MVP go/no-go. | `tools/verify_companion_ble_matrix.py` and retained validation artifacts under `docs/validation/`. | Matrices can pass fixtures while missing real-use defects; the final go/no-go must cite hardware and manual evidence. |

## Forbidden Direct Reuse

The following Listener surfaces are forbidden direct reuse in Companion-Firmware:

- ESP-IDF drivers, `idf.py` build assumptions, ESP GPIO policy, ESP task wiring,
  and ESP audio/PDM driver code.
- NimBLE services, NimBLE event names, ESP BLE HID services, and Listener HID keyboard behavior.
- ESP partitions/NVS, ESP OTA slot layout, ESP bootloader rollback APIs, and
  Listener flash partition assumptions.
- PWR_HOLD, Listener battery/current-sense GPIO contracts, charger-status
  assumptions, and V2 power-latch policy.
- Listener LEDs, status strip semantics, RGB color-order assumptions, and
  Listener device names such as `listener` or `Listener Type`.
- Listener UUIDs, advertising names, desktop UI labels, bundle identifiers, and
  product support text.

These items may be read to understand failure modes and evidence expectations,
but Companion code must implement its own STM32WB, GATT, power, storage, display,
and host-support contracts.

## Guardrail Validation

Run these commands before submitting migration-map work:

```powershell
pwsh -NoProfile -Command '$p="docs/listener_feature_migration.md"; if(!(Test-Path $p)){ throw "missing listener_feature_migration" }; $need=@("| Listener capability | Companion target | reuse mode | first implementation step | validation | risk |","Listener-Type BLE recovery","actionable BLE failure","diagnostics bundle","recording byte-offset transfer","delete-after-sync","OTA manifest","low-power state","forbidden direct reuse","ESP-IDF","NimBLE","PWR_HOLD"); foreach($n in $need){ if(-not (Select-String -LiteralPath $p -Pattern $n -SimpleMatch -Quiet)){ throw ("missing migration anchor: "+$n) } }'
pwsh -NoProfile -File .\tools\ai\repo_features.ps1 -Check
git diff --check
```

Reviewers should also confirm the diff is limited to Companion-Firmware docs and
tools for this step. Later steps may add firmware, host fixture, and validation
code under their own acceptance criteria.
