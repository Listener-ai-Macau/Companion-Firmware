# Companion NUCLEO-WB55RG Bring-up

This is the current NUCLEO-WB55RG Companion app bring-up image. It keeps the
board/peripheral driver layer local to this CubeIDE-style project while using
`app/companion_pendant` for Listener-style portable business logic.

The image now merges the earlier `Companion_BLE_Audio_Fixture` BLE advertising,
GATT, and VKA1 transport into this app. The fixture project remains as historical
bring-up evidence; new NUCLEO app work should happen here.

It verifies three early production paths:

- USART1 logs through the ST-LINK VCP at 115200 baud.
- BLE advertises as `companion` and exposes the Companion VKA1 audio service.
  `TYPE:READY` marks the Type link ready, `TYPE:READY:A1` opens short
  automated TTS ASR validation, and `TYPE:READY:A2` opens the longer Type ASR
  validation window; `VREC:TOGGLE`, `VREC:STOP`, and
  `VREC:CANCEL` drive the same recording FSM path as the temporary board
  buttons.
- External flash is probed non-destructively through the QSPI wiring with
  `0x9F` JEDEC ID and status reads.
- INMP441-style I2S microphone input is captured with SAI1 Block A master RX,
  PLLSAI1 48 MHz, 16 kHz, 32-bit slots, then downshifted into 16-bit mono
  batches, fed into the Companion recording FSM, and streamed to Type as VKA1
  PCM packets when Type has enabled notifications. PA8/SCK must use
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
| Flash QSPI NCS/CLK | PA2 / PA3 |
| Flash QSPI IO0/IO1/IO2/IO3 | PB9 / PB8 / PA7 / PA6 |
| Mic SAI1 SCK/FS/SD | PA8 / PB12 / PC3 |
| Manual record | SW1 / PC4 |
| Cancel / recover | SW2 / PD0 |
| Manual probe | SW3 / PD1 |

Current hardware evidence:

- Microphone bring-up passes: SAI1 initializes at 48 MHz, captures PCM-changing
  blocks, and the recording FSM reaches `transfer_ready` with four fed frames.
- Manual button bring-up is enabled for pressure tests. Press SW1 once to start
  recording and again to stop; the firmware logs the resulting recording
  metadata, streams VKA1 PCM packets when Type is ready, completes the current
  transfer path, and returns to idle so the next SW1 press can start a fresh
  recording.
- OTA readiness bring-up passes: ready plus all required blocker bits are logged
  through `ota.readiness`, `ota.block_result`, `ota.blocker`, and
  `ota.interrupted_transfer`.
- QSPI flash bus code runs the current non-destructive probe. Treat the actual
  JEDEC ID result as hardware evidence from the latest locked bench run, not as
  a static claim in this README.

Build:

```powershell
pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1
pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -OtaApp -Force
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
