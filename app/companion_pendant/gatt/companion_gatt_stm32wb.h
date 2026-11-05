#ifndef COMPANION_GATT_STM32WB_H
#define COMPANION_GATT_STM32WB_H

#if defined(COMPANION_GATT_WBA_HOST)
#include "app_common.h"
#include "ble_core.h"
#include "svc_ctl.h"
#else
#include "ble_types.h"
#include "stm32_wpan_common.h"
#endif
#include "../v1_features/companion_wire_v1.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMPANION_GATT_MAX_PAYLOAD_BYTES 248u
#define COMPANION_GATT_QUEUE_DEPTH 8u
#define COMPANION_GATT_RECORDING_STATUS_STORAGE_FULL 0x40u
#define COMPANION_GATT_RECORDING_STATUS_ERROR 0x80u

typedef enum {
    COMPANION_GATT_CHAR_DEVICE_STATUS = 0,
    COMPANION_GATT_CHAR_BATTERY_CHARGE,
    COMPANION_GATT_CHAR_E_PAPER_CARD_WRITE,
    COMPANION_GATT_CHAR_E_PAPER_CARD_STATUS,
    COMPANION_GATT_CHAR_RECORDING_CONTROL,
    COMPANION_GATT_CHAR_RECORDING_LIST,
    COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,
    /* Product dual-lane bulk notify twin (0x3004). Peak Win wire ~97 KB/s. */
    COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B,
    COMPANION_GATT_CHAR_SETTINGS,
    COMPANION_GATT_CHAR_DIAGNOSTICS_LOG_PULL,
    COMPANION_GATT_CHAR_DELETE_PRIVACY,
    COMPANION_GATT_CHAR_OTA_READINESS,
    COMPANION_GATT_CHAR_BLE_NAME_CONFIG,
    COMPANION_GATT_CHAR_MEETING_CONTROL,
    COMPANION_GATT_CHAR_MEETING_STATUS,
    COMPANION_GATT_CHAR_IMU_STATUS,
    COMPANION_GATT_CHAR_SPEAKER_CONTROL,
    COMPANION_GATT_CHAR_SPEAKER_STATUS,
    COMPANION_GATT_CHAR_WAKE_WORD_CONTROL,
    COMPANION_GATT_CHAR_WAKE_WORD_STATUS,
    COMPANION_GATT_CHAR_REPAIR_CONTROL,
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
/* Additional WBA device-status fault bit. It reports a retained recording
 * tail that could not be recovered; normal in-progress WRITING is not enough
 * to set it. Existing readers may ignore this otherwise-reserved bit. */
enum { COMPANION_GATT_FAULT_RECORDING_TAIL_UNRESOLVED = 1u << 11 };
typedef struct {
    uint8_t schema_version;
    uint8_t active_mode;
    uint16_t fault_bitmap;
    uint32_t firmware_version;
    uint32_t build_id;
    uint32_t board_id;
    uint32_t uptime_ms;
} companion_gatt_device_status_v1_t;

/* Backward-compatible WBA identity tail.  The first 20 bytes stay exactly
 * companion_gatt_device_status_v1_t so existing V1 readers keep working.
 * UID words are emitted in the MCU memory byte order, matching the 12-byte
 * CubeProgrammer read at UID_BASE used by the factory installer. */
typedef struct {
    companion_gatt_device_status_v1_t base;
    uint32_t mcu_uid_word0;
    uint32_t mcu_uid_word1;
    uint32_t mcu_uid_word2;
    uint32_t ui_generation;
} companion_gatt_device_status_v1_wba_ext_t;

/* Preserve the complete 36-byte identity prefix for existing V1 hosts. */
typedef struct {
    companion_gatt_device_status_v1_wba_ext_t identity;
    companion_recording_capacity_v1_t capacity;
} companion_gatt_device_status_v1_wba_capacity_t;

/* WBA continuous-recorder capability follows the unchanged 84-byte V1
 * capacity prefix. Allocate the full value in the WBA GATT database as well
 * as in its publisher; an 84-byte attribute rejects the entire 116-byte
 * update and leaves readers with the initial/previous legacy value. */
typedef struct {
    companion_gatt_device_status_v1_wba_capacity_t legacy;
    uint8_t recording_capability[32];
} companion_gatt_device_status_v1_wba_recording_t;

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
    uint8_t command;
    uint16_t flags;
    uint32_t request_id;
    uint32_t pairing_window_ms;
} companion_gatt_repair_control_v1_t;

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
/* Completion events identify the value handle, never the CCCD/declaration.
 * Only the two registered recording lanes can wake the recording sender. */
bool companion_gatt_stm32wb_is_recording_value_handle(uint16_t attr_handle);
/*1/2 are the two recording value lanes;0 is not a recording value.*/
uint8_t companion_gatt_stm32wb_recording_value_lane(uint16_t attr_handle);
tBleStatus companion_gatt_stm32wb_publish(companion_gatt_char_id_t char_id,
                                          const uint8_t *payload,
                                          uint16_t length);
/* Request/reply on SETTINGS is read back explicitly. Do not emit a long
 * notification to an older subscribed client or an ATT-MTU 23 connection. */
tBleStatus companion_gatt_stm32wb_set_read_value(companion_gatt_char_id_t char_id,
                                               const uint8_t *payload,
                                               uint16_t length);
/* The caller owns the immutable packet and resets staged_bytes on a new
 * packet, lane change, cancel or disconnect. generation changes invalidate
 * a nested ACI result before it can publish/advance another window.
 * WBA staged_bytes is a 240-byte part-index token, not a physical extent:
 * tails are prepared first, prefix0 is committed last to repair short writes
 * to this shared START/resume attribute before notification. */
tBleStatus companion_gatt_stm32wb_publish_progress(
    companion_gatt_char_id_t char_id, const uint8_t *payload, uint16_t length,
    uint16_t *staged_bytes, const uint32_t *generation);
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
companion_gatt_parse_result_t companion_gatt_parse_ble_name_config_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_ble_name_config_v1_t *out);
companion_gatt_parse_result_t companion_gatt_parse_repair_control_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_repair_control_v1_t *out);
companion_gatt_parse_result_t companion_gatt_parse_meeting_control_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_meeting_control_v1_t *out);
companion_gatt_parse_result_t companion_gatt_parse_meeting_status_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_meeting_status_v1_t *out);
companion_gatt_parse_result_t companion_gatt_parse_imu_status_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_imu_status_v1_t *out);
companion_gatt_parse_result_t companion_gatt_parse_speaker_control_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_speaker_control_v1_t *out);
companion_gatt_parse_result_t companion_gatt_parse_speaker_status_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_speaker_status_v1_t *out);
companion_gatt_parse_result_t companion_gatt_parse_wake_word_control_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_wake_word_control_v1_t *out);
companion_gatt_parse_result_t companion_gatt_parse_wake_word_status_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_wake_word_status_v1_t *out);
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
