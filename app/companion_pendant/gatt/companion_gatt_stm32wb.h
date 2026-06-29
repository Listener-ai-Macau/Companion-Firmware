#ifndef COMPANION_GATT_STM32WB_H
#define COMPANION_GATT_STM32WB_H

#include "ble_types.h"
#include "stm32_wpan_common.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMPANION_GATT_MAX_PAYLOAD_BYTES 248u
#define COMPANION_GATT_QUEUE_DEPTH 8u

typedef enum {
    COMPANION_GATT_CHAR_DEVICE_STATUS = 0,
    COMPANION_GATT_CHAR_BATTERY_CHARGE,
    COMPANION_GATT_CHAR_E_PAPER_CARD_WRITE,
    COMPANION_GATT_CHAR_E_PAPER_CARD_STATUS,
    COMPANION_GATT_CHAR_RECORDING_CONTROL,
    COMPANION_GATT_CHAR_RECORDING_LIST,
    COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,
    COMPANION_GATT_CHAR_SETTINGS,
    COMPANION_GATT_CHAR_DIAGNOSTICS_LOG_PULL,
    COMPANION_GATT_CHAR_DELETE_PRIVACY,
    COMPANION_GATT_CHAR_OTA_READINESS,
    COMPANION_GATT_CHAR_COUNT,
} companion_gatt_char_id_t;

typedef enum {
    COMPANION_GATT_EVENT_WRITE = 0,
    COMPANION_GATT_EVENT_NOTIFY_ENABLED,
    COMPANION_GATT_EVENT_NOTIFY_DISABLED,
} companion_gatt_event_type_t;

typedef enum {
    COMPANION_GATT_PARSE_OK = 0,
    COMPANION_GATT_PARSE_TOO_SHORT,
    COMPANION_GATT_PARSE_TOO_LONG,
    COMPANION_GATT_PARSE_UNSUPPORTED_VERSION,
    COMPANION_GATT_PARSE_BAD_LENGTH,
    COMPANION_GATT_PARSE_BAD_ARGUMENT,
} companion_gatt_parse_result_t;

typedef struct {
    companion_gatt_event_type_t type;
    companion_gatt_char_id_t char_id;
    uint16_t attr_handle;
    uint16_t payload_len;
    uint8_t payload[COMPANION_GATT_MAX_PAYLOAD_BYTES];
} companion_gatt_event_t;

#pragma pack(push, 1)
typedef struct {
    uint8_t schema_version;
    uint8_t active_mode;
    uint16_t fault_bitmap;
    uint32_t firmware_version;
    uint32_t build_id;
    uint32_t board_id;
    uint32_t uptime_ms;
} companion_gatt_device_status_v1_t;

typedef struct {
    uint8_t schema_version;
    uint8_t percent;
    uint8_t charge_state;
    uint8_t charger_present;
    uint16_t millivolts;
    int16_t temperature_c_x10;
} companion_gatt_battery_charge_v1_t;

typedef struct {
    uint8_t schema_version;
    uint8_t card_slot;
    uint16_t display_flags;
    uint32_t request_id;
    uint16_t utf8_title_len;
    uint16_t utf8_body_len;
} companion_gatt_card_write_v1_t;

typedef struct {
    uint8_t schema_version;
    uint8_t card_slot;
    uint8_t render_state;
    uint8_t last_error;
    uint32_t request_id;
    uint32_t content_crc32;
    uint32_t refresh_count;
} companion_gatt_card_status_v1_t;

typedef struct {
    uint8_t schema_version;
    uint8_t command;
    uint8_t profile_id;
    uint8_t privacy_flags;
    uint32_t request_id;
    uint16_t max_seconds;
} companion_gatt_recording_control_v1_t;

typedef struct {
    uint8_t schema_version;
    uint8_t count;
    uint16_t entry_bytes;
} companion_gatt_recording_list_v1_t;

typedef struct {
    uint8_t schema_version;
    uint8_t flags;
    uint16_t requested_length;
    uint32_t recording_id;
    uint32_t byte_offset;
    uint32_t host_resume_token;
} companion_gatt_recording_chunk_pull_v1_t;

typedef struct {
    uint8_t schema_version;
    uint8_t locale;
    uint16_t flags;
    int16_t time_zone_offset_min;
    uint8_t quiet_hours_start_min;
    uint8_t quiet_hours_end_min;
    uint8_t display_brightness;
    uint8_t recorder_profile_id;
} companion_gatt_settings_v1_t;

typedef struct {
    uint8_t schema_version;
    uint8_t source_mask;
    uint16_t severity_mask;
    uint32_t cursor;
    uint16_t max_events;
    uint16_t max_bytes;
} companion_gatt_diag_log_pull_v1_t;

typedef struct {
    uint8_t schema_version;
    uint8_t operation;
    uint16_t flags;
    uint32_t request_id;
    uint32_t recording_id;
    uint32_t validated_total_length;
    uint8_t validated_sha256[32];
} companion_gatt_delete_privacy_v1_t;

typedef struct {
    uint8_t schema_version;
    uint8_t ready_state;
    uint8_t boot_slot;
    uint8_t battery_percent;
    uint16_t minimum_required_mv;
    uint16_t blocker_bitmap;
    uint32_t manifest_version;
    uint32_t image_size;
    uint8_t image_sha256_prefix[8];
} companion_gatt_ota_readiness_v1_t;
#pragma pack(pop)

typedef void (*companion_gatt_event_fn_t)(const companion_gatt_event_t *event,
                                          void *context);

tBleStatus companion_gatt_stm32wb_init(void);
size_t companion_gatt_stm32wb_drain(companion_gatt_event_fn_t handler,
                                    void *context);
bool companion_gatt_stm32wb_has_pending(void);
tBleStatus companion_gatt_stm32wb_publish(companion_gatt_char_id_t char_id,
                                          const uint8_t *payload,
                                          uint16_t length);
void companion_gatt_stm32wb_schedule_task(void);

companion_gatt_parse_result_t companion_gatt_parse_device_status_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_device_status_v1_t *out);
companion_gatt_parse_result_t companion_gatt_parse_battery_charge_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_battery_charge_v1_t *out);
companion_gatt_parse_result_t companion_gatt_parse_card_write_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_card_write_v1_t *out);
companion_gatt_parse_result_t companion_gatt_parse_card_status_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_card_status_v1_t *out);
companion_gatt_parse_result_t companion_gatt_parse_recording_control_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_recording_control_v1_t *out);
companion_gatt_parse_result_t companion_gatt_parse_recording_list_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_recording_list_v1_t *out);
companion_gatt_parse_result_t companion_gatt_parse_recording_chunk_pull_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_recording_chunk_pull_v1_t *out);
companion_gatt_parse_result_t companion_gatt_parse_settings_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_settings_v1_t *out);
companion_gatt_parse_result_t companion_gatt_parse_diag_log_pull_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_diag_log_pull_v1_t *out);
companion_gatt_parse_result_t companion_gatt_parse_delete_privacy_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_delete_privacy_v1_t *out);
companion_gatt_parse_result_t companion_gatt_parse_ota_readiness_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_ota_readiness_v1_t *out);

const char *companion_gatt_char_name(companion_gatt_char_id_t char_id);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_GATT_STM32WB_H */
