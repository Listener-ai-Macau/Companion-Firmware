#include "companion_v11_services.h"
#include <string.h>

/* Finding reuses the accepted finite confirmation cue. There is no new PCM,
 * looped DMA buffer or volume override. Foreground time owns the six-second
 * budget, including gaps; a repeated request cannot extend that budget. */
static void cancel_find(comp_v11_services_t *s)
{
    s->find_active = false;
    if (s->find_cue_inflight && s->speaker != NULL &&
        s->speaker->playback_generation == s->find_cue_generation &&
        comp_speaker_active(s->speaker)) {
        (void)comp_speaker_stop(s->speaker, false);
    }
    s->find_cue_inflight = false;
}

static void poll_find(comp_v11_services_t *s, uint32_t now_ms)
{
    comp_speaker_t *p = s->speaker;
    if (!s->find_active) { return; }
    if (!s->speaker_available || p == NULL || s->playback_inhibited ||
        p->muted || p->volume_percent == 0u ||
        now_ms - s->find_started_ms >= COMPANION_V1_FIND_DURATION_MS) {
        cancel_find(s);
        return;
    }
    /* A later local/system cue has a different generation even if it uses
     * the same note. Retire only this schedule; never stop that new owner. */
    if (s->find_cue_inflight) {
        if (p->playback_generation != s->find_cue_generation) {
            s->find_cue_inflight = false;
            s->find_active = false;
            return;
        }
        if (comp_speaker_active(p)) { return; }
        s->find_cue_inflight = false;
        if (p->state != COMP_SPEAKER_STATE_SHUTDOWN ||
            p->last_error != COMP_SPEAKER_OK) {
            s->speaker_status.last_error = COMP_V11_SPEAKER_ERROR_IO;
            s->find_active = false;
            return;
        }
        s->speaker_status.played_count++;
    }
    if ((int32_t)(now_ms - s->find_next_cue_ms) < 0) { return; }
    if (comp_speaker_active(p)) {
        s->find_active = false;
        return;
    }
    const comp_speaker_result_t result = comp_speaker_play_cue(p, COMP_SPEAKER_CUE_CONFIRM);
    if (result != COMP_SPEAKER_OK) {
        s->speaker_status.last_error = result == COMP_SPEAKER_BUSY ?
            COMP_V11_SPEAKER_ERROR_BUSY : COMP_V11_SPEAKER_ERROR_IO;
        s->find_active = false;
        return;
    }
    s->find_cue_generation = p->playback_generation;
    s->find_cue_inflight = true;
    /* Skip delayed beats. A slow foreground must not replay a backlog. */
    s->find_next_cue_ms = now_ms + COMPANION_V1_FIND_CUE_INTERVAL_MS;
}

static bool speaker_status(void *context, uint32_t now_ms, companion_gatt_speaker_status_v1_t *out)
{
    comp_v11_services_t *s = context;
    comp_speaker_t *p = s->speaker;
    poll_find(s, now_ms);
    s->speaker_status.schema_version = 1;
    memset(s->speaker_status.reserved, 0, sizeof(s->speaker_status.reserved));
    if (!s->speaker_available || p == NULL) {
        s->speaker_status.state = COMPANION_V1_SPEAKER_STATE_ERROR;
        s->speaker_status.last_error = COMP_V11_SPEAKER_ERROR_IO;
    } else {
        s->speaker_status.reserved[0] = COMPANION_V1_SPEAKER_CAP_BOUNDED_FIND;
        s->speaker_status.reserved[1] = s->find_active ? COMPANION_V1_SPEAKER_FLAG_FIND_ACTIVE : 0u;
        if (s->prompt_inflight && !comp_speaker_active(p)) {
            if (p->state == COMP_SPEAKER_STATE_SHUTDOWN && p->last_error == COMP_SPEAKER_OK) {
                s->speaker_status.played_count++;
            }
            s->prompt_inflight = false;
        }
        s->speaker_status.state = p->state == COMP_SPEAKER_STATE_FAULT ? COMPANION_V1_SPEAKER_STATE_ERROR :
            (comp_speaker_active(p) ? COMPANION_V1_SPEAKER_STATE_PLAYING : COMPANION_V1_SPEAKER_STATE_IDLE);
        s->speaker_status.volume_percent = p->volume_percent;
        if (p->state == COMP_SPEAKER_STATE_FAULT) { s->speaker_status.last_error = COMP_V11_SPEAKER_ERROR_IO; }
    }
    *out = s->speaker_status;
    return true;
}

static companion_v1_result_t speaker_control(void *context, const companion_gatt_speaker_control_v1_t *request,
                                            uint32_t now_ms, companion_gatt_speaker_status_v1_t *out)
{
    comp_v11_services_t *s = context;
    comp_speaker_result_t result;
    (void)speaker_status(context, now_ms, out);
    s->speaker_status.request_id = request->request_id;
    s->speaker_status.prompt_id = request->prompt_id;
    if (request->schema_version != 1 || request->payload_len != 0 || request->flags != 0 ||
        (request->command != COMPANION_V1_SPEAKER_COMMAND_PROMPT &&
         request->command != COMPANION_V1_SPEAKER_COMMAND_FIND_START &&
         request->command != COMPANION_V1_SPEAKER_COMMAND_FIND_STOP) ||
        (request->command == COMPANION_V1_SPEAKER_COMMAND_PROMPT && request->prompt_id > COMP_SPEAKER_CUE_PET_SHY) ||
        (request->command != COMPANION_V1_SPEAKER_COMMAND_PROMPT &&
         (request->request_id == 0u || request->prompt_id != 0u || request->volume_percent != 0u))) {
        s->speaker_status.last_error = COMPANION_V1_SPEAKER_ERROR_UNSUPPORTED;
        *out = s->speaker_status;
        return COMPANION_V1_RESULT_UNSUPPORTED_COMMAND;
    }
    if (!s->speaker_available || s->speaker == NULL) {
        *out = s->speaker_status;
        return COMPANION_V1_RESULT_UNSUPPORTED_COMMAND;
    }
    if (request->command == COMPANION_V1_SPEAKER_COMMAND_FIND_STOP) {
        if (request->request_id != s->find_request_id) {
            s->speaker_status.last_error = COMPANION_V1_SPEAKER_ERROR_UNSUPPORTED;
            *out = s->speaker_status;
            return COMPANION_V1_RESULT_UNSUPPORTED_COMMAND;
        }
        /* Matching stop is idempotent after expiry and cannot stop a newer
         * prompt or another find request. Quiet/capture never block cancel. */
        cancel_find(s);
        s->speaker_status.last_error = 0u;
        (void)speaker_status(context, now_ms, out);
        return COMPANION_V1_RESULT_OK;
    }
    if (request->command == COMPANION_V1_SPEAKER_COMMAND_FIND_START &&
        request->request_id == s->find_request_id) {
        /* A network retry keeps the original deadline, including after the
         * find has already ended. Another user action must use a fresh ID. */
        (void)speaker_status(context, now_ms, out);
        return COMPANION_V1_RESULT_OK;
    }
    if (s->playback_inhibited || s->find_active || comp_speaker_active(s->speaker) ||
        (request->command == COMPANION_V1_SPEAKER_COMMAND_FIND_START &&
         (s->speaker->muted || s->speaker->volume_percent == 0u))) {
        s->speaker_status.last_error = COMP_V11_SPEAKER_ERROR_BUSY;
        *out = s->speaker_status;
        return COMPANION_V1_RESULT_BUSY;
    }
    if (request->command == COMPANION_V1_SPEAKER_COMMAND_FIND_START) {
        s->find_request_id = request->request_id;
        s->find_started_ms = now_ms;
        s->find_next_cue_ms = now_ms;
        s->find_active = true;
        s->find_cue_inflight = false;
        s->speaker_status.last_error = 0u;
        (void)speaker_status(context, now_ms, out);
        return s->find_active ? COMPANION_V1_RESULT_OK : COMPANION_V1_RESULT_UNSUPPORTED_COMMAND;
    }
    (void)comp_speaker_set_volume(s->speaker, request->volume_percent);
    result = comp_speaker_play_cue(s->speaker, (comp_speaker_cue_t)request->prompt_id);
    s->speaker_status.last_error = result == COMP_SPEAKER_OK ? 0 : COMP_V11_SPEAKER_ERROR_IO;
    s->prompt_inflight = result == COMP_SPEAKER_OK;
    (void)speaker_status(context, now_ms, out);
    if (result == COMP_SPEAKER_OK) { out->state = COMPANION_V1_SPEAKER_STATE_PROMPT_ACCEPTED; return COMPANION_V1_RESULT_OK; }
    return result == COMP_SPEAKER_BUSY ? COMPANION_V1_RESULT_BUSY : COMPANION_V1_RESULT_UNSUPPORTED_COMMAND;
}

static bool imu_status(void *context, uint32_t now_ms, companion_gatt_imu_status_v1_t *out)
{
    comp_v11_services_t *s = context;
    const comp_imu_sample_t *v = s->sample;
    *out = (companion_gatt_imu_status_v1_t){.schema_version = 1, .calibration_state = 1};
    /* No bias calibration is claimed by merely configuring the device. */
    if (s->imu == NULL || v == NULL || s->imu->state != COMP_IMU_READY || s->imu->samples == 0 ||
        now_ms - v->timestamp_ms > 500u) {
        out->sensor_state = COMPANION_V1_IMU_STATE_ERROR; return true;
    }
    out->sensor_state = COMPANION_V1_IMU_STATE_READY;
    /* Nominal accelerometer ODR, rounded to integer Hz (idle12.5Hz). */
    out->sample_rate_hz = s->imu->recording_taps ? 417u : s->imu->idle_accel_only ? 13u : 52u;
    out->motion_flags = s->motion_flags; out->sample_timestamp_ms = v->timestamp_ms;
    out->accel_x_mg = v->accel_mg[0]; out->accel_y_mg = v->accel_mg[1]; out->accel_z_mg = v->accel_mg[2];
    out->gyro_x_dps = (int16_t)(v->gyro_mdps[0] / 1000); out->gyro_y_dps = (int16_t)(v->gyro_mdps[1] / 1000);
    out->gyro_z_dps = (int16_t)(v->gyro_mdps[2] / 1000); out->temperature_c_x10 = v->temperature_c_x10;
    return true;
}

void comp_v11_services_bind(comp_v11_services_t *services, companion_v1_features_t *features,
                            comp_speaker_t *speaker, bool speaker_available,
                            comp_lsm6dso_t *imu, const comp_imu_sample_t *sample)
{
    companion_v1_peripheral_backend_t backend = {speaker_control, speaker_status, imu_status, services};
    if (services == NULL || features == NULL) { return; }
    memset(services, 0, sizeof(*services));
    services->speaker = speaker; services->speaker_available = speaker_available;
    services->imu = imu; services->sample = sample;
    companion_v1_features_bind_peripheral_backend(features, &backend);
}
