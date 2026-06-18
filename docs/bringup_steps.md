# Companion Firmware Bring-Up Steps

## Source Baseline

The earlier Companion planning notes resolved the first firmware path to:

- First product: low-power BLE e-paper pendant.
- First board: `NUCLEO-WB55RG`.
- First firmware milestone: run an official BLE example before writing custom
  services.
- Later steps: custom GATT, fixed e-paper text, button state, microphone
  sample, SPI flash audio storage, then desktop/mobile pull.

The official upstream is pinned as a git submodule:

- URL: `https://github.com/STMicroelectronics/STM32CubeWB.git`
- Tag: `v1.24.0`
- Commit: `7c5aa7dcd2c0abe787f922bb06a6213c724d08e4`

The selected official example is:

```text
third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer
```

Reason: it is an ST GATT server point-to-point BLE example for STM32WB55 and is
closer to the planned custom pendant service than a fixed standard profile such
as Heart Rate.

## Step 0 - Prepare Tools

Install or confirm:

- STM32CubeIDE
- STM32CubeProgrammer
- ST BLE Sensor app on iOS/Android, or another BLE GATT scanner
- One `NUCLEO-WB55RG` board and USB cable connected to `USB_STLINK`

Initialize the official package:

```powershell
.\tools\bootstrap_stm32cubewb.ps1
```

## Step 1 - Run Official BLE Example

Open this project in STM32CubeIDE:

```text
third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32CubeIDE
```

Before flashing the app, confirm the wireless coprocessor has the BLE full
stack. In the current ST package, the expected binary is:

```text
third_party/STM32CubeWB/Projects/STM32WB_Copro_Wireless_Binaries/STM32WB5x/stm32wb5x_BLE_Stack_full_fw.bin
```

Build and flash the application from STM32CubeIDE, or flash the official
reference image first:

```text
third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/Binary/BLE_p2pServer_reference.hex
```

Acceptance:

- The board advertises as `P2PSRVx` or the equivalent ST example device name.
- ST BLE Sensor or a BLE scanner can connect.
- The app can exercise the light/button behavior described by the official
  example readme.

## Step 2 - Create Companion GATT Service

After Step 1 passes on hardware, copy the example into a product-owned
application directory instead of modifying the submodule:

```text
app/companion_pendant/
```

Initial service shape:

- Device information: firmware version, battery placeholder, board role.
- Pendant card write: short UTF-8 text for e-paper display.
- Event notify: button press, recording started/stopped placeholders.
- Audio transfer placeholder: chunk metadata only, before microphone work.

Acceptance:

- Device advertises with a Companion-specific name.
- A BLE scanner sees the Companion service UUID.
- A desktop/mobile tool can write a short text payload and receive one notify.

## Step 3 - E-Paper Fixed Text

Wire the selected e-paper module to SPI and display a fixed short phrase.

Acceptance:

- Reset/boot displays a fixed phrase.
- BLE write from Step 2 can update an in-memory target phrase, even if display
  refresh is still manual or stubbed.

## Step 4 - Button State

Map one board button to a Companion event.

Acceptance:

- Button press changes local state.
- BLE notify sends the new state.

## Step 5 - Microphone Sample Stub

Bring up microphone sampling with the smallest proven path first.

Acceptance:

- Capture 5 to 10 seconds into RAM or a temporary buffer.
- Record sample rate, bit depth, buffer size, and whether clipping/noise is
  visible in the captured artifact.

## Step 6 - SPI Flash Audio Storage

Move the captured audio buffer into external SPI flash.

Acceptance:

- Write one sample block.
- Read it back.
- Compare byte count and checksum.

## Step 7 - Desktop Pull

Use a desktop BLE tool before building a full app.

Acceptance:

- Tool scans for the Companion device.
- Tool connects and pulls one metadata record or small sample payload.
- Failure cases are explicit: no device, disconnect, timeout.
