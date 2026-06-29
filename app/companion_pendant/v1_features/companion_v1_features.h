#ifndef COMPANION_V1_FEATURES_H
#define COMPANION_V1_FEATURES_H

#include "companion_gatt_stm32wb.h"

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

typedef struct {
    companion_gatt_meeting_status_v1_t meeting;
    companion_gatt_imu_status_v1_t imu;
    companion_gatt_speaker_status_v1_t speaker;
    companion_gatt_wake_word_status_v1_t wake_word;
    companion_gatt_ble_name_config_v1_t ble_name;
    uint32_t next_meeting_id;
} companion_v1_features_t;

void companion_v1_features_init(companion_v1_features_t *features,
                                uint32_t now_ms);

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
