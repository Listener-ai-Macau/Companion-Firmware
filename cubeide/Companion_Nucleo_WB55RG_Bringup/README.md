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
- External flash is probed non-destructively through the development-board
  QSPI 2IO wiring with `0x9F` JEDEC ID and status reads.
- Listener-style SPH0655-compatible PDM microphone input is the default WB55
  devboard backend. It captures raw PDM with SAI1 Block A master RX on the
  IOC SCK/FS/SD route, uses raw-SAI DMA, MSB bit order, MCKDIV 31, CIC3
  decimation, and preamp shift 3, then normalizes into 16 kHz PCM16 mono
  batches for the Companion recording FSM, flash recordings, BLE transfer, and
  Type ASR tooling. The older SPH0645-compatible I2S path remains selectable
  with `-MicBackend i2s` for comparison but is not the current devboard
  microphone default.
- SAI1 Block B, SPI2, I2C3, and the MAX98357 shutdown GPIO are initialized from
  the new development-board `.ioc` so later speaker/sensor work has stable
  pins, but playback and sensor drivers are still separate feature work. The
  import from `C:\Users\Billy\Desktop\STM32.ioc` is tracked by
  `python .\tools\verify_devboard_ioc_import.py`.
- OTA readiness/blocker diagnostics use the Companion diag event contract; this
  image does not write update data or change boot slots.
- NUCLEO board buttons are wired as temporary Companion controls until the
  pendant input board exists: SW1 runs the flash/OTA/mic/diag probe, SW2
  cancels and recovers to idle, and SW3 toggles recording start/stop.

NUCLEO wiring used by this image:

| Function | STM32WB55RG pin |
|---|---|
| ST-LINK VCP TX/RX | PB6 / PB7 USART1 |
| Flash QSPI NCS/CLK | PA2 / PA3 |
| Flash QSPI IO0/IO1 | PB9 / PB8 |
| I2C3 SCL/SDA | PC0 / PB11 |
| SPI2 SCK/MOSI/MISO/CS | PA9 / PC1 / PC2 / PA6 |
| Mic SAI1 SCK/FS/SD | PA8 / PB12 / PC3 |
| Speaker SAI1B SCK/FS/SD + amp SD | PB3 / PA4 / PA5 + PA15 |
| Manual probe | SW1 / PC4 |
| Cancel / recover | SW2 / PD0 |
| Manual record | SW3 / PD1 |

The imported IOC records CubeMX's original SPI2 candidate at 16 Mbit/s. The
WB55 e-paper board adapter keeps a 2 MHz hardware-SPI fallback and uses the
matching Good Display sample's MSB-first GPIO-SPI edge sequence during panel
bring-up. These target-specific transport details are not part of the portable
panel contract for WBA55/WBA65.

Current hardware evidence:

- Microphone bring-up logs `quality=` and `[mic-loop]` timing diagnostics on
  verbose blocks. The validated WB55 devboard PDM path uses the default build
  settings, or explicitly:
  `pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -Force
  -BootSelfTests -MicBackend pdm -PdmRawSaiMckdiv 31 -PdmUseCic3Filter 1
  -PdmBitOrderLsb 0 -MicPreampShift 3 -FlashRecordingStageBlocks 450`.
  Validation with a PC-speaker TTS source reached Companion Type ASR; the
  archived artifact is under
  `.cache\validation\companion-real-mic-pc-speaker-tts-pdm-rawsai-dma-gain3-cic3-msb-decim96-mckdiv31-stage450-short-asr-20260710-0515\`.
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
pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -Force -BootSelfTests -MicBackend pdm
pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1 -OtaApp -Force
```

Flash:

```powershell
pwsh -NoProfile -File .\tools\flash_nucleo_bringup.ps1
```

Screen resource provisioning uses a separate oversized one-shot image. After
writing and verifying the external `ui_assets` pack, flash the normal firmware
back immediately so the runtime no longer carries the provision blob:

```powershell
pwsh -NoProfile -File .\tools\flash_nucleo_bringup.ps1 -ScreenAssetProvision -CheckOnly
pwsh -NoProfile -File .\tools\flash_nucleo_bringup.ps1 -ScreenAssetProvision
pwsh -NoProfile -File .\tools\flash_nucleo_bringup.ps1 -CheckOnly
pwsh -NoProfile -File .\tools\flash_nucleo_bringup.ps1
```

Capture logs:

```powershell
pwsh -NoProfile -File .\tools\capture_nucleo_serial.ps1 -CheckOnly
pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose "Companion NUCLEO serial capture" -Run pwsh -NoProfile -File .\tools\capture_nucleo_serial.ps1 -Execute -WorkflowLockHeld -Seconds 15 -ResetAfterOpen
```
