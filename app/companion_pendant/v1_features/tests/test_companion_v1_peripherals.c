#include "companion_v1_features.h"
#include "power_policy.h"

#include <stdio.h>
#include <string.h>

typedef struct {
    unsigned control_calls;
    unsigned speaker_reads;
    unsigned imu_reads;
    uint32_t last_now_ms;
    companion_gatt_speaker_control_v1_t last_request;
    companion_v1_result_t control_result;
} fake_peripherals_t;

static int fail(const char *message)
{
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

static companion_v1_result_t fake_speaker_control(
    void *context,
    const companion_gatt_speaker_control_v1_t *request,
    uint32_t now_ms,
    companion_gatt_speaker_status_v1_t *status)
{
    fake_peripherals_t *fake = context;
    fake->control_calls++;
    fake->last_now_ms = now_ms;
    fake->last_request = *request;
    status->state = fake->control_result == COMPANION_V1_RESULT_OK ?
        COMPANION_V1_SPEAKER_STATE_PROMPT_ACCEPTED :
        COMPANION_V1_SPEAKER_STATE_ERROR;
    status->last_error = fake->control_result == COMPANION_V1_RESULT_OK ? 0u : 9u;
    status->played_count = 7u;
    return fake->control_result;
}

static bool fake_speaker_status(void *context,
                                uint32_t now_ms,
                                companion_gatt_speaker_status_v1_t *status)
{
    fake_peripherals_t *fake = context;
    fake->speaker_reads++;
    fake->last_now_ms = now_ms;
    status->schema_version = 1u;
    status->state = COMPANION_V1_SPEAKER_STATE_PLAYING;
    status->last_error = 0u;
    status->played_count = 8u;
    return true;
}

static bool fake_imu_status(void *context,
                            uint32_t now_ms,
                            companion_gatt_imu_status_v1_t *status)
{
    fake_peripherals_t *fake = context;
    fake->imu_reads++;
    fake->last_now_ms = now_ms;
    memset(status, 0, sizeof(*status));
    status->schema_version = 1u;
    status->sensor_state = COMPANION_V1_IMU_STATE_READY;
    status->calibration_state = 2u;
    status->motion_flags = 5u;
    status->sample_rate_hz = 104u;
    status->sample_timestamp_ms = now_ms;
    status->accel_x_mg = 125;
    status->accel_y_mg = -250;
    status->accel_z_mg = 1000;
    status->gyro_z_dps = 45;
    status->temperature_c_x10 = 263;
    return true;
}

static int test_wire_layout(void)
{
    const size_t actual[] = {
        sizeof(companion_gatt_ble_name_config_v1_t),
        sizeof(companion_gatt_meeting_control_v1_t),
        sizeof(companion_gatt_meeting_status_v1_t),
        sizeof(companion_gatt_imu_status_v1_t),
        sizeof(companion_gatt_speaker_control_v1_t),
        sizeof(companion_gatt_speaker_status_v1_t),
        sizeof(companion_gatt_wake_word_control_v1_t),
        sizeof(companion_gatt_wake_word_status_v1_t),
    };
    const size_t expected[] = {41u, 12u, 28u, 26u, 12u, 16u, 12u, 24u};
    size_t index;

    for (index = 0u; index < sizeof(actual) / sizeof(actual[0]); ++index) {
        if (actual[index] != expected[index]) {
            return fail("portable wire layout changed");
        }
    }
    return 0;
}

static int test_default_unsupported(void)
{
    companion_v1_features_t features;
    const companion_gatt_speaker_control_v1_t request = {
        .schema_version = 1u,
        .command = 1u,
        .volume_percent = 80u,
        .prompt_id = 2u,
        .request_id = 44u,
    };

    companion_v1_features_init(&features, 100u);
    if (features.imu.sensor_state != COMPANION_V1_IMU_STATE_NOT_POPULATED ||
        features.speaker.state != COMPANION_V1_SPEAKER_STATE_NOT_POPULATED ||
        companion_v1_apply_speaker_control(&features, &request, 110u) !=
            COMPANION_V1_RESULT_UNSUPPORTED_COMMAND ||
        features.speaker.state != COMPANION_V1_SPEAKER_STATE_NOT_POPULATED ||
        features.speaker.last_error != COMPANION_V1_SPEAKER_ERROR_UNSUPPORTED ||
        features.speaker.played_count != 0u) {
        return fail("unbound WB-compatible unsupported behavior");
    }
    return 0;
}

static int test_bound_backend_and_updates(void)
{
    companion_v1_features_t features;
    fake_peripherals_t fake = {.control_result = COMPANION_V1_RESULT_OK};
    const companion_v1_peripheral_backend_t backend = {
        .speaker_control = fake_speaker_control,
        .read_speaker_status = fake_speaker_status,
        .read_imu_status = fake_imu_status,
        .context = &fake,
    };
    const companion_gatt_speaker_control_v1_t request = {
        .schema_version = 1u,
        .command = 1u,
        .volume_percent = 140u,
        .prompt_id = 3u,
        .request_id = 72u,
    };
    companion_gatt_imu_status_v1_t invalid_imu = {.schema_version = 2u};
    companion_gatt_speaker_status_v1_t pushed_speaker = {
        .schema_version = 1u,
        .state = COMPANION_V1_SPEAKER_STATE_IDLE,
        .volume_percent = 55u,
        .played_count = 9u,
    };
    uint8_t refreshed;

    companion_v1_features_init(&features, 0u);
    companion_v1_features_bind_peripheral_backend(&features, &backend);
    if (companion_v1_apply_speaker_control(&features, &request, 500u) !=
            COMPANION_V1_RESULT_OK ||
        fake.control_calls != 1u || fake.last_now_ms != 500u ||
        fake.last_request.volume_percent != 100u ||
        features.speaker.schema_version != 1u ||
        features.speaker.request_id != 72u || features.speaker.prompt_id != 3u ||
        features.speaker.volume_percent != 100u ||
        features.speaker.state != COMPANION_V1_SPEAKER_STATE_PROMPT_ACCEPTED ||
        features.speaker.played_count != 7u) {
        return fail("bound speaker command and normalized status");
    }

    refreshed = companion_v1_features_refresh_peripherals(&features, 525u);
    if (refreshed != (COMPANION_V1_REFRESH_IMU |
                      COMPANION_V1_REFRESH_SPEAKER) ||
        fake.imu_reads != 1u || fake.speaker_reads != 1u ||
        features.imu.sensor_state != COMPANION_V1_IMU_STATE_READY ||
        features.imu.sample_timestamp_ms != 525u ||
        features.imu.accel_y_mg != -250 ||
        features.speaker.state != COMPANION_V1_SPEAKER_STATE_PLAYING ||
        features.speaker.played_count != 8u) {
        return fail("periodic peripheral refresh");
    }
    if (companion_v1_features_update_imu_status(&features, &invalid_imu) ||
        features.imu.sensor_state != COMPANION_V1_IMU_STATE_READY ||
        !companion_v1_features_update_speaker_status(
            &features, &pushed_speaker) ||
        features.speaker.played_count != 9u) {
        return fail("push status validation and update");
    }

    fake.control_result = COMPANION_V1_RESULT_BUSY;
    if (companion_v1_apply_speaker_control(&features, &request, 600u) !=
            COMPANION_V1_RESULT_BUSY ||
        features.speaker.state != COMPANION_V1_SPEAKER_STATE_ERROR ||
        features.speaker.last_error != 9u) {
        return fail("backend busy result propagation");
    }
    companion_v1_features_bind_peripheral_backend(&features, NULL);
    if (companion_v1_apply_speaker_control(&features, &request, 700u) !=
            COMPANION_V1_RESULT_UNSUPPORTED_COMMAND ||
        features.speaker.state != COMPANION_V1_SPEAKER_STATE_NOT_POPULATED ||
        features.imu.sensor_state != COMPANION_V1_IMU_STATE_NOT_POPULATED ||
        features.imu.sample_rate_hz != 0u) {
        return fail("backend unbind restores unsupported behavior");
    }
    return 0;
}

static int test_power_blockers_are_independent(void)
{
    comp_power_policy_t policy;

    comp_power_policy_init(&policy);
    comp_power_policy_set_touch_wake_ready(&policy, true);
    comp_power_policy_set_blocker(&policy, COMP_POWER_BLOCKER_BOOT, false);
    if (!comp_power_policy_stop_allowed(&policy)) return fail("idle power setup");

    comp_power_policy_set_blocker(&policy, COMP_POWER_BLOCKER_MIC_CAPTURE, true);
    comp_power_policy_set_blocker(&policy, COMP_POWER_BLOCKER_PLAYBACK, true);
    comp_power_policy_set_blocker(&policy, COMP_POWER_BLOCKER_PLAYBACK, false);
    if (comp_power_policy_stop_allowed(&policy) ||
        (policy.blockers & COMP_POWER_BLOCKER_MIC_CAPTURE) == 0u) {
        return fail("playback clear released active microphone");
    }
    comp_power_policy_set_blocker(&policy, COMP_POWER_BLOCKER_PLAYBACK, true);
    comp_power_policy_set_blocker(&policy, COMP_POWER_BLOCKER_MIC_CAPTURE, false);
    if (comp_power_policy_stop_allowed(&policy) ||
        (policy.blockers & COMP_POWER_BLOCKER_PLAYBACK) == 0u) {
        return fail("microphone clear released active playback");
    }
    comp_power_policy_set_blocker(&policy, COMP_POWER_BLOCKER_PLAYBACK, false);
    if (!comp_power_policy_stop_allowed(&policy)) {
        return fail("power remains blocked after both activities end");
    }
    return 0;
}

int main(void)
{
    if (test_wire_layout() != 0 || test_default_unsupported() != 0 ||
        test_bound_backend_and_updates() != 0 ||
        test_power_blockers_are_independent() != 0 ||
        !comp_power_policy_self_test()) {
        return 1;
    }
    printf("PASS: portable V1 wire/backend IMU/speaker/default-unsupported and independent playback power blocker\n");
    return 0;
}
