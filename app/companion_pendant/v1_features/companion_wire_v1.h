#ifndef COMPANION_WIRE_V1_H
#define COMPANION_WIRE_V1_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Transport-neutral byte layouts shared by STM32WB and STM32WBA GATT glue. */
#define COMPANION_GATT_BLE_NAME_MAX_BYTES 29u
#define COMPANION_V1_MEETING_ERROR_REJECTED 2u
#define COMPANION_V1_MEETING_ERROR_STORAGE_FULL 3u
#define COMPANION_V1_MEETING_ERROR_POWER_LOW 4u
#define COMPANION_V1_MEETING_ERROR_POWER_UNKNOWN 5u
#define COMPANION_RECORDING_CAPACITY_TAG 0x31504343u /* CCP1, little endian */
#define COMPANION_RECORDING_CAPACITY_GEOMETRY_TAG 0x32514343u /* CCQ2, same48 bytes */
#define COMPANION_RECORDING_CAPACITY_VALID 1u
#define COMPANION_RECORDING_CAPACITY_BUSY 2u
#define COMPANION_RECORDING_CAPACITY_CONFIRMED_DISCARD 4u
#define COMPANION_RECORDING_DISCARD_PREVIEW 1u
#define COMPANION_RECORDING_DISCARD_CONFIRM 2u
#define COMPANION_RECORDING_DISCARD_CANCEL 3u
#define COMPANION_RECORDING_DISCARD_REFUSED 1u
#define COMPANION_RECORDING_DISCARD_PENDING 2u
#define COMPANION_RECORDING_DISCARD_COMPLETE 4u
#define COMPANION_RECORDING_DISCARD_NO_CANDIDATE 8u
#define COMPANION_RECORDING_DISCARD_CANCELLED 16u
#define COMPANION_RECORDING_DISCARD_TTL_MS 60000u

#pragma pack(push, 1)
/* Optional WBA DeviceStatus tail at byte 36. Counts are reserved NOR bytes,
 * not encoded file lengths. ACKED/ERASING remain occupied until reclaimed. */
typedef struct {
    uint32_t tag;
    uint8_t layout_version;
    uint8_t flags;
    uint8_t used_entries;
    uint8_t max_entries;
    uint32_t catalog_generation;
    uint32_t data_bytes;
    uint32_t free_bytes;
    uint32_t largest_free_extent;
    uint32_t protected_bytes;
    uint32_t consumed_bytes;
    uint32_t bytes_per_second; /* CCP1 bytes/s; CCQ2 segment_frames */
    uint32_t reserve_headroom; /* CCP1 reserve bytes; CCQ2 aligned extent_bytes */
    uint32_t local_limit_seconds;
    uint8_t unsynced_entries;
    uint8_t writing_entries;
    uint8_t consumed_entries;
    uint8_t reserved;
} companion_recording_capacity_v1_t;
/* Schema 2 on the existing encrypted DeletePrivacy characteristic. Schema 1
 * remains exact host-copy ACK/consume. Preview is read-only. Confirmation and
 * cancellation echo every field from request_id onward on the same connection.
 * expires_in_ms is the offered lifetime, not a host wall-clock timestamp. */
typedef struct {
    uint8_t schema_version;
    uint8_t operation;
    uint16_t flags;
    uint32_t request_id;
    uint32_t recording_id;
    uint32_t total_length;
    uint8_t sha256[32];
    uint32_t catalog_generation;
    uint32_t token[2];
    uint32_t started_unix_s;
    uint32_t duration_ms;
    uint32_t reserved_bytes;
    uint32_t expires_in_ms;
    uint32_t requested_seconds;
    uint32_t largest_extent_after;
} companion_recording_discard_v2_t;
typedef struct {
    uint8_t schema_version;
    uint8_t command;
    uint16_t flags;
    uint32_t request_id;
    uint8_t name_len;
    uint8_t max_len;
    uint8_t status;
    uint8_t reserved;
    uint8_t name[COMPANION_GATT_BLE_NAME_MAX_BYTES];
} companion_gatt_ble_name_config_v1_t;

typedef struct {
    uint8_t schema_version;
    uint8_t command;
    uint16_t flags;
    uint32_t request_id;
    uint16_t max_seconds;
    uint8_t profile_id;
    uint8_t reserved;
} companion_gatt_meeting_control_v1_t;

typedef struct {
    uint8_t schema_version;
    uint8_t state;
    uint8_t last_error;
    uint8_t summary_state;
    uint16_t flags;
    uint16_t segment_count;
    uint32_t request_id;
    uint32_t meeting_id;
    uint32_t started_tick_ms;
    uint32_t duration_ms;
    uint8_t sync_state;
    uint8_t reserved[3];
} companion_gatt_meeting_status_v1_t;

typedef struct {
    uint8_t schema_version;
    uint8_t sensor_state;
    uint8_t motion_flags;
    uint8_t calibration_state;
    uint16_t sample_rate_hz;
    uint16_t reserved;
    uint32_t sample_timestamp_ms;
    int16_t accel_x_mg;
    int16_t accel_y_mg;
    int16_t accel_z_mg;
    int16_t gyro_x_dps;
    int16_t gyro_y_dps;
    int16_t gyro_z_dps;
    int16_t temperature_c_x10;
} companion_gatt_imu_status_v1_t;

/* SpeakerControlV1 stays 12 bytes and SpeakerStatusV1 stays 16 bytes.
 * Commands 2/3 require nonzero request_id, volume/prompt/payload/flags=0.
 * Start retries retain the original deadline; matching stop is idempotent.
 * Status reserved[0] advertises support and reserved[1] reports active find.
 * Old hosts ignore these reserved bytes. Old firmware advertises neither bit. */
enum {
    COMPANION_V1_SPEAKER_COMMAND_PROMPT = 1u,
    COMPANION_V1_SPEAKER_COMMAND_FIND_STOP = 2u,
    COMPANION_V1_SPEAKER_COMMAND_FIND_START = 3u,
    COMPANION_V1_SPEAKER_CAP_BOUNDED_FIND = 1u,
    COMPANION_V1_SPEAKER_FLAG_FIND_ACTIVE = 1u,
    COMPANION_V1_FIND_DURATION_MS = 6000u,
    COMPANION_V1_FIND_CUE_INTERVAL_MS = 1250u,
};
typedef struct {
    uint8_t schema_version;
    uint8_t command;
    uint8_t volume_percent;
    uint8_t prompt_id;
    uint32_t request_id;
    uint16_t payload_len;
    uint16_t flags;
} companion_gatt_speaker_control_v1_t;

typedef struct {
    uint8_t schema_version;
    uint8_t state;
    uint8_t last_error;
    uint8_t volume_percent;
    uint32_t request_id;
    uint8_t prompt_id;
    uint8_t reserved[3];
    uint32_t played_count;
} companion_gatt_speaker_status_v1_t;

typedef struct {
    uint8_t schema_version;
    uint8_t command;
    uint8_t sensitivity;
    uint8_t reserved;
    uint16_t flags;
    uint16_t model_id;
    uint32_t request_id;
} companion_gatt_wake_word_control_v1_t;

typedef struct {
    uint8_t schema_version;
    uint8_t armed;
    uint8_t engine_state;
    uint8_t last_event;
    uint8_t last_error;
    uint8_t sensitivity;
    uint8_t last_confidence;
    uint8_t reserved;
    uint16_t flags;
    uint16_t model_id;
    uint32_t request_id;
    uint32_t detection_count;
    uint32_t rejected_count;
} companion_gatt_wake_word_status_v1_t;
#pragma pack(pop)

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_WIRE_V1_H */
