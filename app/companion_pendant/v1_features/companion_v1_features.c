#include "companion_v1_features.h"

#include <stddef.h>
#include <string.h>

#define COMPANION_V1_MEETING_STATE_IDLE 0u
#define COMPANION_V1_MEETING_STATE_RECORDING 1u
#define COMPANION_V1_MEETING_STATE_FINALIZED 2u

/* Electronic pet: IMU = body, speaker = mouth (short calls). Meeting record is
 * a skill. Both stay NOT_POPULATED until productized — contract:
 * Companion-Type/docs/goals/companion-deferred-features-reserved.md */
#define COMPANION_V1_IMU_CALIBRATION_PENDING 1u
#define COMPANION_V1_IMU_MOTION_NONE 0u

#define COMPANION_V1_WAKE_STATE_DISABLED 0u
#define COMPANION_V1_WAKE_STATE_ARMED 1u
#define COMPANION_V1_WAKE_EVENT_DETECTED 2u
#define COMPANION_V1_WAKE_ERROR_UNSUPPORTED 2u

#define COMPANION_V1_BLE_NAME_STATUS_ACTIVE 0u
#define COMPANION_V1_BLE_NAME_STATUS_STAGED 1u
#define COMPANION_V1_BLE_NAME_STATUS_RESTART_REQUIRED 2u
#define COMPANION_V1_BLE_NAME_STATUS_REJECTED 0x80u
#define COMPANION_V1_BLE_NAME_FLAG_PENDING_RESTART 0x0001u
#define COMPANION_V1_BLE_NAME_FLAG_LISTENER_POLICY 0x0002u

static void companion_v1_copy_ble_name(uint8_t out[COMPANION_GATT_BLE_NAME_MAX_BYTES],
                                       uint8_t *out_len,
                                       const char *name)
{
    size_t length = strlen(name);
    if (length > COMPANION_GATT_BLE_NAME_MAX_BYTES) {
        length = COMPANION_GATT_BLE_NAME_MAX_BYTES;
    }
    memset(out, 0, COMPANION_GATT_BLE_NAME_MAX_BYTES);
    memcpy(out, name, length);
    if (out_len != NULL) {
        *out_len = (uint8_t)length;
    }
}

void companion_v1_features_init(companion_v1_features_t *features,
                                uint32_t now_ms)
{
    if (features == NULL) {
        return;
    }
    memset(features, 0, sizeof(*features));
    features->next_meeting_id = 1u;

    features->meeting.schema_version = 1u;
    features->meeting.state = COMPANION_V1_MEETING_STATE_IDLE;
    features->meeting.sync_state = 0u;
    features->meeting.summary_state = 0u;

    features->imu.schema_version = 1u;
    features->imu.sensor_state = COMPANION_V1_IMU_STATE_NOT_POPULATED;
    features->imu.motion_flags = COMPANION_V1_IMU_MOTION_NONE;
    features->imu.calibration_state = COMPANION_V1_IMU_CALIBRATION_PENDING;
    features->imu.sample_rate_hz = 0u;
    features->imu.sample_timestamp_ms = now_ms;
    features->imu.temperature_c_x10 = 250;

    features->speaker.schema_version = 1u;
    features->speaker.state = COMPANION_V1_SPEAKER_STATE_NOT_POPULATED;
    features->speaker.volume_percent = 50u;

    features->wake_word.schema_version = 1u;
    features->wake_word.armed = 0u;
    features->wake_word.engine_state = COMPANION_V1_WAKE_STATE_DISABLED;
    features->wake_word.sensitivity = 50u;

    features->ble_name.schema_version = 1u;
    features->ble_name.command = 0u;
    features->ble_name.flags = COMPANION_V1_BLE_NAME_FLAG_LISTENER_POLICY;
    features->ble_name.status = COMPANION_V1_BLE_NAME_STATUS_ACTIVE;
    features->ble_name.max_len = COMPANION_GATT_BLE_NAME_MAX_BYTES;
    companion_v1_copy_ble_name(features->ble_name.name,
                               &features->ble_name.name_len,
                               COMPANION_V1_DEFAULT_BLE_NAME);
}

void companion_v1_features_bind_peripheral_backend(
    companion_v1_features_t *features,
    const companion_v1_peripheral_backend_t *backend)
{
    if (features == NULL) {
        return;
    }
    memset(&features->peripheral_backend, 0,
           sizeof(features->peripheral_backend));
    if (backend != NULL) {
        features->peripheral_backend = *backend;
    } else {
        features->imu.sensor_state = COMPANION_V1_IMU_STATE_NOT_POPULATED;
        features->imu.motion_flags = COMPANION_V1_IMU_MOTION_NONE;
        features->imu.calibration_state = COMPANION_V1_IMU_CALIBRATION_PENDING;
        features->imu.sample_rate_hz = 0u;
        features->speaker.state = COMPANION_V1_SPEAKER_STATE_NOT_POPULATED;
        features->speaker.last_error = COMPANION_V1_SPEAKER_ERROR_UNSUPPORTED;
    }
}

bool companion_v1_features_update_imu_status(
    companion_v1_features_t *features,
    const companion_gatt_imu_status_v1_t *status)
{
    if (features == NULL || status == NULL || status->schema_version != 1u) {
        return false;
    }
    features->imu = *status;
    return true;
}

bool companion_v1_features_update_speaker_status(
    companion_v1_features_t *features,
    const companion_gatt_speaker_status_v1_t *status)
{
    if (features == NULL || status == NULL || status->schema_version != 1u) {
        return false;
    }
    features->speaker = *status;
    if (features->speaker.volume_percent > 100u) {
        features->speaker.volume_percent = 100u;
    }
    return true;
}

uint8_t companion_v1_features_refresh_peripherals(
    companion_v1_features_t *features,
    uint32_t now_ms)
{
    uint8_t refreshed = COMPANION_V1_REFRESH_NONE;
    companion_gatt_imu_status_v1_t imu;
    companion_gatt_speaker_status_v1_t speaker;

    if (features == NULL) {
        return refreshed;
    }
    if (features->peripheral_backend.read_imu_status != NULL) {
        imu = features->imu;
        if (features->peripheral_backend.read_imu_status(
                features->peripheral_backend.context, now_ms, &imu) &&
            companion_v1_features_update_imu_status(features, &imu)) {
            refreshed |= COMPANION_V1_REFRESH_IMU;
        }
    }
    if (features->peripheral_backend.read_speaker_status != NULL) {
        speaker = features->speaker;
        if (features->peripheral_backend.read_speaker_status(
                features->peripheral_backend.context, now_ms, &speaker) &&
            companion_v1_features_update_speaker_status(features, &speaker)) {
            refreshed |= COMPANION_V1_REFRESH_SPEAKER;
        }
    }
    return refreshed;
}

companion_v1_result_t companion_v1_apply_meeting_control(
    companion_v1_features_t *features,
    const companion_gatt_meeting_control_v1_t *request,
    uint32_t now_ms)
{
    if (features == NULL || request == NULL) {
        return COMPANION_V1_RESULT_UNSUPPORTED_COMMAND;
    }

    features->meeting.schema_version = 1u;
    features->meeting.request_id = request->request_id;
    features->meeting.flags = request->flags;
    features->meeting.last_error = 0u;

    switch (request->command) {
    case 1u:
        features->meeting.state = COMPANION_V1_MEETING_STATE_RECORDING;
        features->meeting.meeting_id = features->next_meeting_id++;
        features->meeting.started_tick_ms = now_ms;
        features->meeting.duration_ms = 0u;
        features->meeting.segment_count = 0u;
        features->meeting.summary_state = 0u;
        features->meeting.sync_state = 0u;
        return COMPANION_V1_RESULT_OK;
    case 2u:
        if (features->meeting.state == COMPANION_V1_MEETING_STATE_RECORDING) {
            features->meeting.duration_ms = now_ms - features->meeting.started_tick_ms;
            features->meeting.segment_count++;
        }
        features->meeting.state = COMPANION_V1_MEETING_STATE_FINALIZED;
        features->meeting.summary_state = 1u;
        features->meeting.sync_state = 1u;
        return COMPANION_V1_RESULT_OK;
    case 3u:
        features->meeting.state = COMPANION_V1_MEETING_STATE_IDLE;
        features->meeting.sync_state = 0u;
        return COMPANION_V1_RESULT_OK;
    default:
        features->meeting.last_error = COMPANION_V1_MEETING_ERROR_REJECTED;
        return COMPANION_V1_RESULT_UNSUPPORTED_COMMAND;
    }
}

companion_v1_result_t companion_v1_apply_speaker_control(
    companion_v1_features_t *features,
    const companion_gatt_speaker_control_v1_t *request,
    uint32_t now_ms)
{
    companion_gatt_speaker_control_v1_t normalized;
    companion_gatt_speaker_status_v1_t status;
    companion_v1_result_t result;

    if (features == NULL || request == NULL) {
        return COMPANION_V1_RESULT_UNSUPPORTED_COMMAND;
    }
    features->speaker.schema_version = 1u;
    features->speaker.request_id = request->request_id;
    features->speaker.prompt_id = request->prompt_id;
    features->speaker.volume_percent = request->volume_percent > 100u ? 100u :
                                                               request->volume_percent;
    if (features->peripheral_backend.speaker_control != NULL) {
        normalized = *request;
        normalized.volume_percent = features->speaker.volume_percent;
        status = features->speaker;
        result = features->peripheral_backend.speaker_control(
            features->peripheral_backend.context, &normalized, now_ms, &status);
        status.schema_version = 1u;
        status.request_id = request->request_id;
        status.prompt_id = request->prompt_id;
        /* Prompt1 keeps its established normalized-volume contract. Find
         * start/stop report the existing physical volume without changing it. */
        if (normalized.command == COMPANION_V1_SPEAKER_COMMAND_PROMPT) {
            status.volume_percent = normalized.volume_percent;
        }
        (void)companion_v1_features_update_speaker_status(features, &status);
        return result;
    }
    /* The current WB55/FTS02 fixture has no bound speaker backend. A control
     * write must not look successful merely because the GATT contract exists:
     * keep the physical state honest and do not advance played_count. */
    features->speaker.state = COMPANION_V1_SPEAKER_STATE_NOT_POPULATED;
    features->speaker.last_error = COMPANION_V1_SPEAKER_ERROR_UNSUPPORTED;
    return COMPANION_V1_RESULT_UNSUPPORTED_COMMAND;
}

companion_v1_result_t companion_v1_apply_wake_word_control(
    companion_v1_features_t *features,
    const companion_gatt_wake_word_control_v1_t *request,
    uint32_t now_ms)
{
    (void)now_ms;
    if (features == NULL || request == NULL) {
        return COMPANION_V1_RESULT_UNSUPPORTED_COMMAND;
    }
    features->wake_word.schema_version = 1u;
    features->wake_word.request_id = request->request_id;
    features->wake_word.flags = request->flags;
    features->wake_word.sensitivity = request->sensitivity > 100u ? 100u :
                                                                  request->sensitivity;
    /* No wake-word engine is linked in the accepted WB55 image.  Never
     * synthesize an armed/detected transition or confidence value. */
    features->wake_word.armed = 0u;
    features->wake_word.engine_state = COMPANION_V1_WAKE_STATE_DISABLED;
    features->wake_word.last_event = 0u;
    features->wake_word.last_confidence = 0u;
    features->wake_word.rejected_count++;
    features->wake_word.last_error = COMPANION_V1_WAKE_ERROR_UNSUPPORTED;
    return COMPANION_V1_RESULT_UNSUPPORTED_COMMAND;
}

bool companion_v1_ble_name_is_valid(const uint8_t *name, uint8_t length)
{
    if (name == NULL || length == 0u ||
        length > COMPANION_GATT_BLE_NAME_MAX_BYTES) {
        return false;
    }
    for (uint8_t index = 0u; index < length; ++index) {
        uint8_t ch = name[index];
        if (ch < 0x20u || ch > 0x7eu) {
            return false;
        }
        if (ch == '"' || ch == '\'' || ch == ';' || ch == '=' || ch == '\\') {
            return false;
        }
    }
    return true;
}

companion_v1_result_t companion_v1_apply_ble_name_config(
    companion_v1_features_t *features,
    const companion_gatt_ble_name_config_v1_t *request)
{
    if (features == NULL || request == NULL) {
        return COMPANION_V1_RESULT_UNSUPPORTED_COMMAND;
    }

    features->ble_name.schema_version = 1u;
    features->ble_name.command = request->command;
    features->ble_name.request_id = request->request_id;
    features->ble_name.max_len = COMPANION_GATT_BLE_NAME_MAX_BYTES;
    features->ble_name.flags = COMPANION_V1_BLE_NAME_FLAG_LISTENER_POLICY;

    switch (request->command) {
    case 1u:
        if (!companion_v1_ble_name_is_valid(request->name, request->name_len)) {
            features->ble_name.status = COMPANION_V1_BLE_NAME_STATUS_REJECTED;
            return COMPANION_V1_RESULT_INVALID_NAME;
        }
        memset(features->ble_name.name, 0, sizeof(features->ble_name.name));
        memcpy(features->ble_name.name, request->name, request->name_len);
        features->ble_name.name_len = request->name_len;
        features->ble_name.status = COMPANION_V1_BLE_NAME_STATUS_STAGED;
        features->ble_name.flags |= COMPANION_V1_BLE_NAME_FLAG_PENDING_RESTART;
        return COMPANION_V1_RESULT_OK;
    case 2u:
        features->ble_name.status = COMPANION_V1_BLE_NAME_STATUS_RESTART_REQUIRED;
        features->ble_name.flags |= COMPANION_V1_BLE_NAME_FLAG_PENDING_RESTART;
        return COMPANION_V1_RESULT_OK;
    case 3u:
        companion_v1_copy_ble_name(features->ble_name.name,
                                   &features->ble_name.name_len,
                                   COMPANION_V1_DEFAULT_BLE_NAME);
        features->ble_name.status = COMPANION_V1_BLE_NAME_STATUS_STAGED;
        features->ble_name.flags |= COMPANION_V1_BLE_NAME_FLAG_PENDING_RESTART;
        return COMPANION_V1_RESULT_OK;
    default:
        features->ble_name.status = COMPANION_V1_BLE_NAME_STATUS_REJECTED;
        return COMPANION_V1_RESULT_UNSUPPORTED_COMMAND;
    }
}

void companion_v1_get_meeting_status(
    const companion_v1_features_t *features,
    companion_gatt_meeting_status_v1_t *out)
{
    if (features != NULL && out != NULL) {
        *out = features->meeting;
    }
}

void companion_v1_get_imu_status(const companion_v1_features_t *features,
                                 companion_gatt_imu_status_v1_t *out)
{
    if (features != NULL && out != NULL) {
        *out = features->imu;
    }
}

void companion_v1_get_speaker_status(
    const companion_v1_features_t *features,
    companion_gatt_speaker_status_v1_t *out)
{
    if (features != NULL && out != NULL) {
        *out = features->speaker;
    }
}

void companion_v1_get_wake_word_status(
    const companion_v1_features_t *features,
    companion_gatt_wake_word_status_v1_t *out)
{
    if (features != NULL && out != NULL) {
        *out = features->wake_word;
    }
}

void companion_v1_get_ble_name_config(
    const companion_v1_features_t *features,
    companion_gatt_ble_name_config_v1_t *out)
{
    if (features != NULL && out != NULL) {
        *out = features->ble_name;
    }
}
