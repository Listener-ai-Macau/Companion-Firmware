# Companion WB55 SPI1 NOR External Loader

Development-only STM32CubeProgrammer external loader for the Companion UI
resource partition.

- Target: STM32WB55
- SPI: SPI1 mode 0, HSI16 / 8 = 2 MHz
- Pins: PA1 SCK, PA7 MOSI, PB4 MISO, PA2 software CS
- Required JEDEC ID: `0B 40 18`
- Advertised and enforced range: `0x90000000..<0x90200000`
- Physical NOR range: `0x000000..<0x200000`
- Erase unit: 4 KiB
- Program page: 256 bytes

The loader deliberately does not expose the remaining 14 MiB recording
partition. `MassErase` erases only the UI partition.

This is a development and factory-provisioning path. It is not the Companion
user OTA transport. Product resource OTA runs in the normal application over
BLE and commits through the same UI generation format.

Build and verify without connecting to hardware:

```powershell
make clean verify
```

The verifier parses the `.stldr` itself and checks the 2 MiB device map,
standard CubeProgrammer entry points, SRAM placement, and range-guard boundary
cases.

Use the repository wrapper for generation-aware writes:

```powershell
python tools/sync_companion_ui_assets_stlink.py `
  --bundle path/to/generation.cuot `
  --current-image path/to/current-2mib.bin `
  --dry-run
```

Real SWD access must use the repository runner:

```powershell
pwsh -NoProfile -File `
  .\tools\run_comp_req_775_external_loader_sync.ps1 -Execute
```

The runner acquires the Companion workflow hardware lock; the Python tool also
requires `--allow-hardware`, explicit workflow-lock acknowledgement, and the
SWD/COM named mutex. It writes changed blob sectors first and the inactive root
sector last. `-BootstrapImage` is reserved for an initial partition with no
valid active generation and is rejected once a generation exists.

The complete COMP-REQ-775 hardware acceptance is one controller command:

```powershell
pwsh -NoProfile -File `
  .\tools\run_comp_req_775_external_loader_acceptance.ps1 -Execute
```

It measures a registered one-frame probe, restores the exact fixed-browser
resource before menu capture, proves the final no-op, and writes one aggregate
machine receipt. It never leaves the synthetic probe active for review.
