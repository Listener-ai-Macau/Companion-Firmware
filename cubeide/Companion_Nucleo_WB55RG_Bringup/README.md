# Companion NUCLEO-WB55RG Bring-up

This is a standalone hardware bring-up image for the NUCLEO-WB55RG wiring in
`C:\Users\Billy\Desktop\STM32.ioc`. It is intentionally separate from the ST
BLE reference project and from the product `Companion_Pendant.ioc`.

It verifies three early production paths:

- USART1 logs through the ST-LINK VCP at 115200 baud.
- External flash is probed non-destructively with SPI2 `0x9F` JEDEC ID and
  `0x05` status reads.
- INMP441-style I2S microphone input is captured with SAI1 Block A master RX,
  PLLSAI1 48 MHz, 16 kHz, 32-bit slots, then downshifted into 16-bit mono
  batches and fed into the Companion recording FSM. PA8/SCK must use
  `GPIO_AF13_SAI1` for this I2S path; `GPIO_AF3_SAI1` is the PDM/CK1 mapping
  and leaves the SAI RX FIFO timing out in this wiring.
- OTA readiness/blocker diagnostics use the Companion diag event contract; this
  image does not write update data or change boot slots.
- NUCLEO board buttons are wired as temporary Companion controls until the
  pendant input board exists: SW1 toggles recording start/stop, SW2 cancels and
  recovers to idle, and SW3 runs the flash/OTA/diag probe on demand.

NUCLEO wiring used by this image:

| Function | STM32WB55RG pin |
|---|---|
| ST-LINK VCP TX/RX | PB6 / PB7 USART1 |
| Flash CS | PA6 GPIO output |
| Flash SPI2 SCK/MOSI/MISO | PA9 / PC1 / PC2 |
| Mic SAI1 SCK/FS/SD | PA8 / PB12 / PC3 |
| Manual record | SW1 / PC4 |
| Cancel / recover | SW2 / PD0 |
| Manual probe | SW3 / PD1 |

Current hardware evidence:

- Microphone bring-up passes: SAI1 initializes at 48 MHz, captures PCM-changing
  blocks, and the recording FSM reaches `transfer_ready` with four fed frames.
- Manual button bring-up is enabled for pressure tests. Press SW1 once to start
  recording and again to stop; the firmware logs the resulting recording
  metadata, simulates the transfer-complete path, and returns to idle so the
  next SW1 press can start a fresh recording.
- OTA readiness bring-up passes: ready plus all required blocker bits are logged
  through `ota.readiness`, `ota.block_result`, `ota.blocker`, and
  `ota.interrupted_transfer`.
- SPI2 flash bus code runs, but the attached flash has not responded with a
  valid JEDEC ID yet. The probe now sweeps mode 0/1/2/3 at low speed plus the
  original mode 0 speed and sends a non-destructive release-from-power-down
  command before `0x9F`; the board still returns only `00-00-00` or
  `FF-FF-FF`. The remaining issue is likely flash wiring, power, CS, HOLD/WP
  strap, or the selected flash interface rather than Companion business logic.

Build:

```powershell
pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1
```

Flash:

```powershell
pwsh -NoProfile -File .\tools\flash_nucleo_bringup.ps1
```

Capture logs:

```powershell
pwsh -NoProfile -File .\tools\capture_nucleo_serial.ps1 -CheckOnly
pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose "Companion NUCLEO serial capture" -Run pwsh -NoProfile -File .\tools\capture_nucleo_serial.ps1 -Execute -WorkflowLockHeld -Seconds 15 -ResetAfterOpen
```
