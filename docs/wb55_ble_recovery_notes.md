# Companion WB55 Denzic OTA And Recovery Notes

## Single OTA Path

Companion has one product OTA protocol: `denzic_ota_v1` from the pinned
`third_party/denzic-platform` submodule. There is no Companion-specific v2
transport and no second host fallback.

- Denzic `protocol/` owns wire identity, GATT UUIDs, packet sizes, status,
  offset recovery, and image CRC used to identify a resumed transfer.
- Denzic `host/rust` owns transfer windows, status reads, retries, progress, and
  resume behavior. Companion Type supplies Windows BLE discovery/read/write.
- Denzic `embedded/c` owns the receiver state machine. The WB55 Loader supplies
  service registration, internal-Flash writes, completion delay, and reset.
- Companion package policy owns target, SHA-256, component metadata, signature
  policy, compatibility, and post-update checks.

Generated Denzic constants are the only UUID and packet-size source. Product
adapters must not copy literal UUIDs or fork the state machine.

## WB55 Platform Substrate

`Companion_BLE_Ota_Loader` still reuses STM32CubeWB startup, linker, CPU2/FUS,
SRAM handoff, Flash driver, and BLE service-control infrastructure. Those files
are STM32WB platform mechanics, not another wire protocol. Portable Denzic code
must not include STM32WB HAL, FUS, IPCC, HSEM, linker addresses, or reboot
cookies.

The NUCLEO OTA application starts at `0x08007000`/sector 7. This is a WB55 bench
fact and is never a WBA or ESP default. The product CE layout is finalized only
after its wireless-stack reservation and resident loader size are measured.

## Build And Static Validation

```powershell
pwsh -NoProfile -File .\tools\build_companion_ota_loader.ps1 -Force
python .\tools\verify_ota_contract_static.py
pwsh -NoProfile -File .\tools\verify_type_companion_package_static.ps1 -SkipTypeFrontend
```

The build must compile these sources directly:

- `Src/companion_ota_v1.c`, the WB55 product adapter;
- `third_party/denzic-platform/ota/embedded/c/src/denzic_ota_v1.c`, the shared
  state machine.

The source directory contains no alternate Companion receiver implementation.

## Package And BLE Validation

`tools/package_ota_firmware.ps1` reads
`third_party/denzic-platform/ota/protocol/ota_v1.json` and writes those exact
UUIDs/version into `ota_manifest.json`. It emits a target-specific `mcu_app`
component; another product uses the same bundle and transport contract with a
different target and installer adapter.

The executable bench path is:

```powershell
pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55,BLE-Companion -Purpose "Companion Denzic OTA validation" -Run pwsh -NoProfile -File .\tools\verify_companion_ble_ota.ps1 -Execute -WorkflowLockHeld -PackagePath <companion-package.zip>
```

The wrapper invokes Companion Type with `--firmware-ota-transfer`; Type then
uses the shared Rust core. Passing evidence requires `protocol=denzic_ota_v1`,
positive firmware/data/status counts, active-link confirmation, reboot, and
post-update version confirmation.

## Recovery Rules

- A recoverable offset mismatch keeps the receiver session alive; the host
  reads device status and resumes at the reported offset.
- Repeating `BEGIN` with the same size and image CRC preserves current device
  progress. A different identity aborts the old storage session and starts a
  fresh erase.
- Denzic CRC is only transfer identity. Package SHA-256/signature checks remain
  required before activation.
- Invalid app vectors, interrupted install, or a non-booting app use the WB55
  ROM DFU/SWD recovery path. Product data partitions are not erased as part of
  normal recovery.
- External resource candidates never overwrite the active pack before atomic
  metadata commit; see `docs/companion_ota_component_contract.md`.

## WBA Migration

WBA55/WBA65 reuse Denzic protocol/host/embedded code and the Companion
component manifest. They do not copy WB55 sector 7, CPU2/FUS, SRAM handoff, or
Flash driver code. A WBA target supplies CubeWBA BLE registration and the
selected Application Install Manager/OEMiROT storage/reboot adapter.
