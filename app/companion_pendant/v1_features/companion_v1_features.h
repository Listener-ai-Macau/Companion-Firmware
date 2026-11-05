#ifndef COMPANION_V1_FEATURES_H
#define COMPANION_V1_FEATURES_H

#include "companion_wire_v1.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMPANION_V1_DEFAULT_BLE_NAME "companion"
#define COMPANION_V1_BLE_NAME_MAX_LEN COMPANION_GATT_BLE_NAME_MAX_BYTES

typedef enum {
    COMPANION_V1_RESULT_OK = 0,
    COMPANION_V1_RESULT_INVALID_NAME = 1,
    COMPANION_V1_RESULT_UNSUPPORTED_COMMAND = 2,
    COMPANION_V1_RESULT_BUSY = 3,
} companion_v1_result_t;

enum {
    COMPANION_V1_IMU_STATE_NOT_POPULATED = 1u,
    COMPANION_V1_IMU_STATE_READY = 2u,
    COMPANION_V1_IMU_STATE_ERROR = 3u,
    COMPANION_V1_SPEAKER_STATE_NOT_POPULATED = 1u,
    COMPANION_V1_SPEAKER_STATE_PROMPT_ACCEPTED = 2u,
    COMPANION_V1_SPEAKER_STATE_PLAYING = 3u,
    COMPANION_V1_SPEAKER_STATE_IDLE = 4u,
    COMPANION_V1_SPEAKER_STATE_ERROR = 5u,
    COMPANION_V1_SPEAKER_ERROR_UNSUPPORTED = 2u,
};

typedef companion_v1_result_t (*companion_v1_speaker_control_fn_t)(
    void *context,
    const companion_gatt_speaker_control_v1_t *request,
    uint32_t now_ms,
    companion_gatt_speaker_status_v1_t *status);
typedef bool (*companion_v1_speaker_status_fn_t)(
    void *context,
    uint32_t now_ms,
    companion_gatt_speaker_status_v1_t *status);
typedef bool (*companion_v1_imu_status_fn_t)(
    void *context,
    uint32_t now_ms,
    companion_gatt_imu_status_v1_t *status);

typedef struct {
    /* Called from the deferred product/GATT task, never from an IRQ. It must
     * stage bounded work and return the real accepted/busy/error status. */
    companion_v1_speaker_control_fn_t speaker_control;
    /* Optional polling snapshots. Return false to preserve the last valid
     * cached wire status; returned schema_version must be 1. */
    companion_v1_speaker_status_fn_t read_speaker_status;
    companion_v1_imu_status_fn_t read_imu_status;
    void *context;
} companion_v1_peripheral_backend_t;

enum {
    COMPANION_V1_REFRESH_NONE = 0u,
    COMPANION_V1_REFRESH_IMU = 1u << 0,
    COMPANION_V1_REFRESH_SPEAKER = 1u << 1,
};

typedef struct {
    companion_gatt_meeting_status_v1_t meeting;
    companion_gatt_imu_status_v1_t imu;
    companion_gatt_speaker_status_v1_t speaker;
    companion_gatt_wake_word_status_v1_t wake_word;
    companion_gatt_ble_name_config_v1_t ble_name;
    companion_v1_peripheral_backend_t peripheral_backend;
    uint32_t next_meeting_id;
} companion_v1_features_t;

void companion_v1_features_init(companion_v1_features_t *features,
                                uint32_t now_ms);
void companion_v1_features_bind_peripheral_backend(
    companion_v1_features_t *features,
    const companion_v1_peripheral_backend_t *backend);
uint8_t companion_v1_features_refresh_peripherals(
    companion_v1_features_t *features,
    uint32_t now_ms);
bool companion_v1_features_update_imu_status(
    companion_v1_features_t *features,
    const companion_gatt_imu_status_v1_t *status);
bool companion_v1_features_update_speaker_status(
    companion_v1_features_t *features,
    const companion_gatt_speaker_status_v1_t *status);

companion_v1_result_t companion_v1_apply_meeting_control(
    companion_v1_features_t *features,
    const companion_gatt_meeting_control_v1_t *request,
    uint32_t now_ms);

companion_v1_result_t companion_v1_apply_speaker_control(
    companion_v1_features_t *features,
    const companion_gatt_speaker_control_v1_t *request,
    uint32_t now_ms);

companion_v1_result_t companion_v1_apply_wake_word_control(
    companion_v1_features_t *features,
    const companion_gatt_wake_word_control_v1_t *request,
    uint32_t now_ms);

companion_v1_result_t companion_v1_apply_ble_name_config(
    companion_v1_features_t *features,
    const companion_gatt_ble_name_config_v1_t *request);

bool companion_v1_ble_name_is_valid(const uint8_t *name, uint8_t length);

void companion_v1_get_meeting_status(
    const companion_v1_features_t *features,
    companion_gatt_meeting_status_v1_t *out);
void companion_v1_get_imu_status(const companion_v1_features_t *features,
                                 companion_gatt_imu_status_v1_t *out);
void companion_v1_get_speaker_status(
    const companion_v1_features_t *features,
    companion_gatt_speaker_status_v1_t *out);
void companion_v1_get_wake_word_status(
    const companion_v1_features_t *features,
    companion_gatt_wake_word_status_v1_t *out);
void companion_v1_get_ble_name_config(
    const companion_v1_features_t *features,
    companion_gatt_ble_name_config_v1_t *out);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_V1_FEATURES_H */
