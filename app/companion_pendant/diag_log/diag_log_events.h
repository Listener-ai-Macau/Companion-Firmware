#ifndef COMPANION_DIAG_LOG_EVENTS_H
#define COMPANION_DIAG_LOG_EVENTS_H

#include <stdint.h>

#define COMP_DIAG_SEV_INFO  0u
#define COMP_DIAG_SEV_WARN  1u
#define COMP_DIAG_SEV_ERROR 2u

#define COMP_DIAG_SOURCE_LIST(X) \
    X(BOOT, 0x01u, "boot") \
    X(BLE, 0x02u, "ble") \
    X(GATT, 0x03u, "gatt") \
    X(EPAPER, 0x04u, "e_paper") \
    X(RECORDING_FSM, 0x05u, "recording_fsm") \
    X(MICROPHONE, 0x06u, "microphone") \
    X(SPI_FLASH_CACHE, 0x07u, "spi_flash_cache") \
    X(OTA, 0x08u, "ota") \
    X(BATTERY_CHARGING, 0x09u, "battery_charging") \
    X(POWER_LPM, 0x0Au, "power_lpm") \
    X(WARNINGS, 0x0Bu, "warnings") \
    X(ERRORS, 0x0Cu, "errors") \
    X(MEETING, 0x0Du, "meeting") \
    X(IMU, 0x0Eu, "imu") \
    X(SPEAKER, 0x0Fu, "speaker") \
    X(WAKE_WORD, 0x10u, "wake_word") \
    X(DEVICE_SETTINGS, 0x11u, "device_settings")

#define COMP_DIAG_EVENT_LIST(X) \
    X(BOOT, START, 0x01u, COMP_DIAG_SEV_INFO, "boot.start") \
    X(BOOT, INIT_RESULT, 0x02u, COMP_DIAG_SEV_INFO, "boot.init_result") \
    X(BLE, ADVERTISING, 0x01u, COMP_DIAG_SEV_INFO, "ble.advertising") \
    X(BLE, CONNECTION, 0x02u, COMP_DIAG_SEV_INFO, "ble.connection") \
    X(GATT, SERVICE_READY, 0x01u, COMP_DIAG_SEV_INFO, "gatt.service_ready") \
    X(GATT, LOG_EXPORT_REQUEST, 0x02u, COMP_DIAG_SEV_INFO, "gatt.log_export_request") \
    X(EPAPER, RENDER_REQUEST, 0x01u, COMP_DIAG_SEV_INFO, "e_paper.render_request") \
    X(EPAPER, UPDATE_RESULT, 0x02u, COMP_DIAG_SEV_INFO, "e_paper.update_result") \
    X(EPAPER, RUNTIME_SNAPSHOT, 0x03u, COMP_DIAG_SEV_INFO, "e_paper.runtime_snapshot") \
    X(RECORDING_FSM, TRANSITION, 0x01u, COMP_DIAG_SEV_INFO, "recording_fsm.transition") \
    X(RECORDING_FSM, REJECTED, 0x02u, COMP_DIAG_SEV_WARN, "recording_fsm.rejected") \
    X(RECORDING_FSM, START_REQUEST, 0x03u, COMP_DIAG_SEV_INFO, "recording_fsm.start_request") \
    X(RECORDING_FSM, STOP_REQUEST, 0x04u, COMP_DIAG_SEV_INFO, "recording_fsm.stop_request") \
    X(RECORDING_FSM, CANCEL_REQUEST, 0x05u, COMP_DIAG_SEV_INFO, "recording_fsm.cancel_request") \
    X(RECORDING_FSM, SESSION_FINISHED, 0x06u, COMP_DIAG_SEV_INFO, "recording_fsm.session_finished") \
    X(RECORDING_FSM, ERROR, 0x07u, COMP_DIAG_SEV_ERROR, "recording_fsm.error") \
    X(RECORDING_FSM, RECOVERY, 0x08u, COMP_DIAG_SEV_INFO, "recording_fsm.recovery") \
    X(MICROPHONE, CAPTURE_START, 0x01u, COMP_DIAG_SEV_INFO, "microphone.capture_start") \
    X(MICROPHONE, CAPTURE_DROP, 0x02u, COMP_DIAG_SEV_WARN, "microphone.capture_drop") \
    X(SPI_FLASH_CACHE, WRITE, 0x01u, COMP_DIAG_SEV_INFO, "spi_flash_cache.write") \
    X(SPI_FLASH_CACHE, READ, 0x02u, COMP_DIAG_SEV_INFO, "spi_flash_cache.read") \
    X(SPI_FLASH_CACHE, DELETE, 0x03u, COMP_DIAG_SEV_INFO, "spi_flash_cache.delete") \
    X(SPI_FLASH_CACHE, LOW_STORAGE, 0x04u, COMP_DIAG_SEV_WARN, "spi_flash_cache.low_storage") \
    X(SPI_FLASH_CACHE, INTERRUPTED_WRITE, 0x05u, COMP_DIAG_SEV_WARN, "spi_flash_cache.interrupted_write") \
    X(SPI_FLASH_CACHE, INTERRUPTED_READ, 0x06u, COMP_DIAG_SEV_WARN, "spi_flash_cache.interrupted_read") \
    X(SPI_FLASH_CACHE, PRIVACY_ERASE, 0x07u, COMP_DIAG_SEV_WARN, "spi_flash_cache.privacy_erase") \
    X(OTA, MANIFEST, 0x01u, COMP_DIAG_SEV_INFO, "ota.manifest") \
    X(OTA, BLOCK_RESULT, 0x02u, COMP_DIAG_SEV_INFO, "ota.block_result") \
    X(OTA, READINESS, 0x03u, COMP_DIAG_SEV_INFO, "ota.readiness") \
    X(OTA, BLOCKER, 0x04u, COMP_DIAG_SEV_WARN, "ota.blocker") \
    X(OTA, INTERRUPTED_TRANSFER, 0x05u, COMP_DIAG_SEV_WARN, "ota.interrupted_transfer") \
    X(OTA, POST_UPDATE_SELF_CHECK, 0x06u, COMP_DIAG_SEV_INFO, "ota.post_update_self_check") \
    X(BATTERY_CHARGING, SAMPLE, 0x01u, COMP_DIAG_SEV_INFO, "battery_charging.sample") \
    X(BATTERY_CHARGING, STATE, 0x02u, COMP_DIAG_SEV_INFO, "battery_charging.state") \
    X(POWER_LPM, STATE, 0x01u, COMP_DIAG_SEV_INFO, "power_lpm.state") \
    X(POWER_LPM, BLOCKER, 0x02u, COMP_DIAG_SEV_WARN, "power_lpm.blocker") \
    X(WARNINGS, RATE_LIMITED, 0x01u, COMP_DIAG_SEV_WARN, "warnings.rate_limited") \
    X(WARNINGS, RECOVERED, 0x02u, COMP_DIAG_SEV_INFO, "warnings.recovered") \
    X(ERRORS, ASSERT, 0x01u, COMP_DIAG_SEV_ERROR, "errors.assert") \
    X(ERRORS, FAULT, 0x02u, COMP_DIAG_SEV_ERROR, "errors.fault") \
    X(MEETING, START, 0x01u, COMP_DIAG_SEV_INFO, "meeting.start") \
    X(MEETING, STOP, 0x02u, COMP_DIAG_SEV_INFO, "meeting.stop") \
    X(MEETING, FINALIZE, 0x03u, COMP_DIAG_SEV_INFO, "meeting.finalize") \
    X(MEETING, REJECTED, 0x04u, COMP_DIAG_SEV_WARN, "meeting.rejected") \
    X(IMU, SAMPLE, 0x01u, COMP_DIAG_SEV_INFO, "imu.sample") \
    X(IMU, MOTION, 0x02u, COMP_DIAG_SEV_INFO, "imu.motion") \
    X(IMU, UNAVAILABLE, 0x03u, COMP_DIAG_SEV_WARN, "imu.unavailable") \
    X(SPEAKER, PROMPT, 0x01u, COMP_DIAG_SEV_INFO, "speaker.prompt") \
    X(SPEAKER, RESULT, 0x02u, COMP_DIAG_SEV_INFO, "speaker.result") \
    X(SPEAKER, REJECTED, 0x03u, COMP_DIAG_SEV_WARN, "speaker.rejected") \
    X(WAKE_WORD, ARMED, 0x01u, COMP_DIAG_SEV_INFO, "wake_word.armed") \
    X(WAKE_WORD, DETECTED, 0x02u, COMP_DIAG_SEV_INFO, "wake_word.detected") \
    X(WAKE_WORD, DISABLED, 0x03u, COMP_DIAG_SEV_INFO, "wake_word.disabled") \
    X(WAKE_WORD, REJECTED, 0x04u, COMP_DIAG_SEV_WARN, "wake_word.rejected") \
    X(DEVICE_SETTINGS, BLE_NAME_ACCEPTED, 0x01u, COMP_DIAG_SEV_INFO, "device_settings.ble_name.accepted") \
    X(DEVICE_SETTINGS, BLE_NAME_REJECTED, 0x02u, COMP_DIAG_SEV_WARN, "device_settings.ble_name.rejected") \
    X(DEVICE_SETTINGS, BLE_NAME_APPLIED, 0x03u, COMP_DIAG_SEV_INFO, "device_settings.ble_name.applied")

typedef enum {
#define COMP_DIAG_SOURCE_ENUM(symbol, value, name) COMP_DIAG_SRC_##symbol = (value),
    COMP_DIAG_SOURCE_LIST(COMP_DIAG_SOURCE_ENUM)
#undef COMP_DIAG_SOURCE_ENUM
} comp_diag_source_t;

typedef enum {
#define COMP_DIAG_EVENT_ENUM(source, event, value, severity, name) \
    COMP_DIAG_EVT_##source##_##event = (uint16_t)(((uint16_t)COMP_DIAG_SRC_##source << 8) | (uint16_t)(value)),
    COMP_DIAG_EVENT_LIST(COMP_DIAG_EVENT_ENUM)
#undef COMP_DIAG_EVENT_ENUM
} comp_diag_event_code_t;

#define COMP_DIAG_EVENT_SOURCE(code) ((uint8_t)(((uint16_t)(code) >> 8) & 0xFFu))
#define COMP_DIAG_EVENT_ID(code)     ((uint8_t)((uint16_t)(code) & 0xFFu))

#endif /* COMPANION_DIAG_LOG_EVENTS_H */
