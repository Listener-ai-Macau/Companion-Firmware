#include "expression_events.h"

#include <stddef.h>

typedef struct {
    uint16_t event_code;
    comp_epaper_expression_signal_t signal;
} comp_epaper_expression_event_def_t;

static const comp_epaper_expression_event_def_t k_event_signal_defs[] = {
    {COMP_DIAG_EVT_WAKE_WORD_ARMED, COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_ARMED},
    {COMP_DIAG_EVT_WAKE_WORD_DISABLED, COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_DISABLED},
    {COMP_DIAG_EVT_WAKE_WORD_DETECTED, COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_DETECTED},
    {COMP_DIAG_EVT_WAKE_WORD_REJECTED, COMP_EPAPER_EXPRESSION_SIGNAL_ERROR},
    {COMP_DIAG_EVT_SPEAKER_PROMPT, COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_PROMPT},
    {COMP_DIAG_EVT_SPEAKER_RESULT, COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_RESULT},
    {COMP_DIAG_EVT_SPEAKER_REJECTED, COMP_EPAPER_EXPRESSION_SIGNAL_ERROR},
    {COMP_DIAG_EVT_MEETING_START, COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_START},
    {COMP_DIAG_EVT_MEETING_STOP, COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_STOP},
    {COMP_DIAG_EVT_MEETING_FINALIZE, COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_FINALIZE},
    {COMP_DIAG_EVT_MEETING_REJECTED, COMP_EPAPER_EXPRESSION_SIGNAL_ERROR},
    {COMP_DIAG_EVT_RECORDING_FSM_START_REQUEST, COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START},
    {COMP_DIAG_EVT_RECORDING_FSM_STOP_REQUEST, COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_STOP},
    {COMP_DIAG_EVT_RECORDING_FSM_CANCEL_REQUEST, COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_CANCEL},
    {COMP_DIAG_EVT_RECORDING_FSM_SESSION_FINISHED, COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_FINISHED},
    {COMP_DIAG_EVT_RECORDING_FSM_REJECTED, COMP_EPAPER_EXPRESSION_SIGNAL_ERROR},
    {COMP_DIAG_EVT_RECORDING_FSM_ERROR, COMP_EPAPER_EXPRESSION_SIGNAL_ERROR},
    {COMP_DIAG_EVT_RECORDING_FSM_RECOVERY, COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY},
    {COMP_DIAG_EVT_WARNINGS_RECOVERED, COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY},
    {COMP_DIAG_EVT_ERRORS_ASSERT, COMP_EPAPER_EXPRESSION_SIGNAL_ERROR},
    {COMP_DIAG_EVT_ERRORS_FAULT, COMP_EPAPER_EXPRESSION_SIGNAL_ERROR},
};

static bool low_battery_sample(uint32_t percent,
                               uint32_t millivolts,
                               uint32_t charger_present)
{
    return percent <= COMP_EPAPER_EXPRESSION_LOW_BATTERY_PERCENT ||
           (millivolts < COMP_EPAPER_EXPRESSION_LOW_BATTERY_MV &&
            charger_present == 0u);
}

static bool battery_recovered_sample(uint32_t percent,
                                     uint32_t millivolts,
                                     uint32_t charger_present)
{
    return percent >= COMP_EPAPER_EXPRESSION_BATTERY_RECOVERED_PERCENT ||
           (charger_present != 0u &&
            millivolts >= COMP_EPAPER_EXPRESSION_BATTERY_RECOVERED_MV);
}

bool comp_epaper_expression_signal_from_diag_event(
    uint16_t event_code,
    uint8_t severity,
    uint32_t arg0,
    uint32_t arg1,
    uint32_t arg2,
    uint32_t arg3,
    comp_epaper_expression_signal_t *out_signal)
{
    (void)arg3;
    if (out_signal == NULL) {
        return false;
    }

    if (COMP_DIAG_EVENT_SOURCE(event_code) == (uint8_t)COMP_DIAG_SRC_EPAPER) {
        return false;
    }
    if (event_code == COMP_DIAG_EVT_BATTERY_CHARGING_SAMPLE &&
        low_battery_sample(arg0, arg1, arg2)) {
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_LOW_BATTERY;
        return true;
    }
    if (event_code == COMP_DIAG_EVT_BATTERY_CHARGING_SAMPLE &&
        battery_recovered_sample(arg0, arg1, arg2)) {
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED;
        return true;
    }

    for (size_t index = 0u; index < sizeof(k_event_signal_defs) / sizeof(k_event_signal_defs[0]); ++index) {
        if (k_event_signal_defs[index].event_code == event_code) {
            *out_signal = k_event_signal_defs[index].signal;
            return true;
        }
    }

    if (severity >= COMP_DIAG_SEV_ERROR) {
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_ERROR;
        return true;
    }
    return false;
}

bool comp_epaper_expression_signal_from_device_status(
    uint8_t active_mode,
    uint16_t fault_bitmap,
    comp_epaper_expression_signal_t *out_signal)
{
    if (out_signal == NULL) {
        return false;
    }

    if (fault_bitmap != 0u) {
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_ERROR;
        return true;
    }
    if (active_mode == COMP_EPAPER_EXPRESSION_DEVICE_ACTIVE_MODE_AUDIO) {
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START;
        return true;
    }
    if (active_mode == COMP_EPAPER_EXPRESSION_DEVICE_ACTIVE_MODE_DISCONNECTED) {
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY;
        return true;
    }
    return false;
}

bool comp_epaper_expression_signal_from_meeting_status(
    uint8_t state,
    uint8_t summary_state,
    uint8_t sync_state,
    uint8_t last_error,
    comp_epaper_expression_signal_t *out_signal)
{
    if (out_signal == NULL) {
        return false;
    }

    if (last_error != 0u) {
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_ERROR;
        return true;
    }
    if (state == COMP_EPAPER_EXPRESSION_MEETING_STATE_RECORDING) {
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_START;
        return true;
    }
    if (state == COMP_EPAPER_EXPRESSION_MEETING_STATE_FINALIZED ||
        sync_state == COMP_EPAPER_EXPRESSION_MEETING_SYNC_COMPLETE) {
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_FINALIZE;
        return true;
    }
    if (summary_state == COMP_EPAPER_EXPRESSION_MEETING_SUMMARY_PENDING) {
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_STOP;
        return true;
    }
    return false;
}

bool comp_epaper_expression_signal_from_recording_state(
    uint8_t state,
    comp_epaper_expression_signal_t *out_signal)
{
    if (out_signal == NULL) {
        return false;
    }

    switch (state) {
    case COMP_EPAPER_EXPRESSION_RECORDING_STATE_PENDING_START:
    case COMP_EPAPER_EXPRESSION_RECORDING_STATE_RECORDING:
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START;
        return true;
    case COMP_EPAPER_EXPRESSION_RECORDING_STATE_STOPPING:
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_STOP;
        return true;
    case COMP_EPAPER_EXPRESSION_RECORDING_STATE_CANCELED:
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_CANCEL;
        return true;
    case COMP_EPAPER_EXPRESSION_RECORDING_STATE_TRANSFER_READY:
    case COMP_EPAPER_EXPRESSION_RECORDING_STATE_TRANSFER_ACTIVE:
    case COMP_EPAPER_EXPRESSION_RECORDING_STATE_TRANSFERRED:
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_FINISHED;
        return true;
    case COMP_EPAPER_EXPRESSION_RECORDING_STATE_ERROR_RECOVERY:
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_ERROR;
        return true;
    default:
        return false;
    }
}

bool comp_epaper_expression_signal_from_speaker_status(
    uint8_t state,
    uint8_t last_error,
    comp_epaper_expression_signal_t *out_signal)
{
    if (out_signal == NULL) {
        return false;
    }

    if (last_error != 0u) {
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_ERROR;
        return true;
    }
    if (state == COMP_EPAPER_EXPRESSION_SPEAKER_STATE_PROMPT_ACCEPTED) {
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_PROMPT;
        return true;
    }
    return false;
}

bool comp_epaper_expression_signal_from_wake_word_status(
    uint8_t armed,
    uint8_t engine_state,
    uint8_t last_event,
    uint8_t last_error,
    comp_epaper_expression_signal_t *out_signal)
{
    if (out_signal == NULL) {
        return false;
    }

    if (last_error != 0u) {
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_ERROR;
        return true;
    }
    if (last_event == COMP_EPAPER_EXPRESSION_WAKE_EVENT_DETECTED) {
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_DETECTED;
        return true;
    }
    if (armed != 0u ||
        engine_state == COMP_EPAPER_EXPRESSION_WAKE_ENGINE_ARMED) {
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_ARMED;
        return true;
    }
    return false;
}

bool comp_epaper_expression_signal_from_ota_readiness(
    uint16_t blocker_bitmap,
    comp_epaper_expression_signal_t *out_signal)
{
    if (out_signal == NULL) {
        return false;
    }

    if ((blocker_bitmap & COMP_EPAPER_EXPRESSION_OTA_LOW_BATTERY_BLOCKER) != 0u) {
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_LOW_BATTERY;
        return true;
    }
    if (blocker_bitmap != 0u) {
        *out_signal = COMP_EPAPER_EXPRESSION_SIGNAL_ERROR;
        return true;
    }
    return false;
}
