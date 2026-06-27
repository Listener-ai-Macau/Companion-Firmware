# Companion Listener-Compatible Audio Stream

This module is the portable half of the Listener-compatible VKA1 live audio
bridge used to bring Companion through the existing Listener-Type A1/A2 path.

It owns:

- Listener-compatible UUID constants for the explicitly named compatibility
  service.
- VKA1 packet construction for session start, audio data, stop, cancel, and
  error packets.
- Type control write classification for `TYPE:READY`, `TYPE:HB`,
  `TYPE:STOP`/`TYPE:BYE`, `VREC:TOGGLE`, `VREC:STOP`, `VREC:CANCEL`, and Type
  processing-state commands.
- GATT value sizing and packet sequence tracking.

It intentionally does not own:

- STM32_WPAN service registration.
- `aci_gatt_add_service`, `aci_gatt_add_char`, or `aci_gatt_update_char_value`.
- HAL/IPCC/HSEM startup.
- Companion-native recording storage, recording-list, or chunk-pull sync.
- ESP-IDF or NimBLE behavior.

The STM32WB service layer should follow the official `BLE_p2pServer` split:

1. Register the compatibility service with
   `COMP_AUDIO_STREAM_SERVICE_UUID_TEXT`.
2. Add notify/read/control characteristics from `docs/ble_uuid_table.json`.
3. Call `comp_audio_stream_set_notify_enabled()` from CCCD modified events.
4. Forward control characteristic writes to
   `comp_audio_stream_handle_control_write()`.
5. Implement `comp_audio_stream_notify_fn_t` with
   `aci_gatt_update_char_value()` for the notify characteristic value handle.
6. Feed PCM16 mono 16 kHz frames from the Companion recording path through
   `comp_audio_stream_send_session_start()`,
   `comp_audio_stream_send_session_audio()`, and
   `comp_audio_stream_send_session_stop()` or terminal error/cancel.

`audio_stream_stm32wb.c` is the STM32_WPAN adapter. It follows the official
`BLE_p2pServer`/`BLE_Ota` service pattern and owns only the GATT glue:

- 128-bit UUID arrays in STM32_WPAN little-endian byte order.
- `SVCCTL_RegisterSvcHandler()` and `ACI_GATT_ATTRIBUTE_MODIFIED_VSEVT_CODE`
  routing.
- Notify CCCD enable/disable handling through the notify characteristic
  descriptor handle (`+2`).
- Type control writes through the control characteristic value handle (`+1`).
- `aci_gatt_update_char_value()` for Listener-compatible notify packets and
  read-only readiness/capabilities text.

The STM32WB adapter fixes its notify value size to 153 bytes, which is the
payload available with the current NUCLEO WB55 ATT MTU of 156 bytes. The
portable VKA1 framing still supports larger packets, but this backend must not
advertise the 244-byte Listener/ESP value until the STM32WB ATT/mblock settings
and validation fixture are raised together.

`tools/verify_listener_vka1_static.py` compares this module against the current
Listener-Type parser, Listener firmware protocol header, and STM32_WPAN adapter
anchors.
