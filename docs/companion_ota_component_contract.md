# Companion OTA Component Contract

## Product Decision

Everything shipped as replaceable product content is inside OTA scope. This
includes the MCU application and the normal resources stored in external NOR:
screen/menu packs, expression animation packs, prompt audio, and future local
models. External placement does not make a resource invisible to OTA.

OTA scope does not mean one monolithic image. A Companion update bundle is a
signed manifest plus independently versioned components. `mcu_app` and
`ui_assets` have separate target, format, size, SHA-256, version, compatibility,
installation, activation, and fallback fields. A resource-only update must not
rewrite the MCU application. A firmware-only update must preserve the active
resource pack and mutable user data.

The machine-readable source of truth is
`docs/companion_ota_component_contract.json`.

## Shared Transport Boundary

`third_party/denzic-platform` is the pinned shared OTA submodule. Its
`denzic_ota_v1` protocol owns the common BLE byte-transfer state machine,
resume offsets, GATT identity, and host/embedded agreement. It intentionally
transports an opaque byte stream and does not decide where an STM32 or ESP
installs it.

Companion Firmware, Companion Type, Listener Firmware, and Listener Type must
all resolve this submodule to the same commit and expose byte-identical protocol
JSON. This is one update system across products, not one binary for unrelated
hardware: each bundle component still declares its product, MCU family, board,
format, and compatibility, and a wrong-target package is rejected before erase
or activation.

The v1 image CRC identifies an interrupted transfer so the same object can
resume. It is not a signature and is not the product integrity boundary.
Companion must verify the signed bundle manifest and each component SHA-256
before installation or activation.

## Component Installation

| component | normal storage | installer | activation |
|---|---|---|---|
| `mcu_app` | internal MCU Flash after staging | target boot/install adapter | install at boot, self-test, then confirm |
| `ui_assets` | external NOR | application resource installer | verify candidate, then atomically switch redundant metadata |
| `prompt_assets` | external NOR | application resource installer | same inactive/candidate rule as UI assets |
| `model_assets` | external NOR | application resource installer | same rule; optional feature stays disabled if no valid pack exists |

The bundle stages and verifies all included components before any active
pointer changes. For a combined app/resource update, the new app rechecks the
candidate resource format and compatibility before switching `boot_meta_a/b`.
A power loss or failed check leaves the previous resource active. If neither
external copy is valid, the internal rescue UI remains available.

`recording_cache`, `diag_log_mirror`, and `settings_user_data` are mutable user
data, not update components. No normal update may erase them. A privacy wipe or
factory reset is a separate explicit operation.

## STM32 Family Boundary

STM32WB and STM32WBA share the bundle/component contract and Denzic transfer
core, but not the boot installer:

- WB55 uses the resident loader and external-QSPI staging selected by the WB55
  product layout.
- WBA55/WBA65 starts from the matching STM32CubeWBA install/security reference
  for the selected part and maps its slots through a WBA target adapter.
- ESP has its own partition/update adapter. ESP slot names, NVS, and rollback
  APIs are never copied into STM32 portable code.

Physical addresses, erase sizes, slot count, signing backend, and boot-confirm
mechanics remain target profile data. Portable package and resource parsers do
not contain WB55, WBA55, WBA65, or ESP addresses.

## Delivery Stages

1. Current Denzic v1 remains the shared byte transport and is pinned as a
   submodule.
2. The existing Companion firmware-only package remains supported while the
   `companion.update-bundle.v1` host parser and installer adapters are added.
3. The first resource-only implementation updates a CEMP `ui_assets`
   candidate, verifies it, atomically activates it, and proves reset and
   interrupted-write recovery without touching `mcu_app` or recordings.
4. Combined app/resource update and production signature/anti-rollback tests
   follow on WB55, then the same contract is mapped to WBA55/WBA65.

Run the non-regression check with:

```powershell
python .\tools\verify_companion_ota_component_contract.py --write-fixture
python .\tools\verify_denzic_ota_product_matrix.py --write-fixture
```
