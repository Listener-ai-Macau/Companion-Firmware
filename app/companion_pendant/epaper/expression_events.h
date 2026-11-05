#ifndef COMPANION_EPAPER_EXPRESSION_EVENTS_H
#define COMPANION_EPAPER_EXPRESSION_EVENTS_H

#include "diag_log_events.h"
#include "expression_state.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_EPAPER_EXPRESSION_LOW_BATTERY_PERCENT 20u
#define COMP_EPAPER_EXPRESSION_LOW_BATTERY_MV 3600u
#define COMP_EPAPER_EXPRESSION_BATTERY_RECOVERED_PERCENT 25u
#define COMP_EPAPER_EXPRESSION_BATTERY_RECOVERED_MV 3600u
#define COMP_EPAPER_EXPRESSION_DEVICE_ACTIVE_MODE_DISCONNECTED 0u
#define COMP_EPAPER_EXPRESSION_DEVICE_ACTIVE_MODE_AUDIO 1u
#define COMP_EPAPER_EXPRESSION_DEVICE_ACTIVE_MODE_IDLE_LINK 2u
#define COMP_EPAPER_EXPRESSION_MEETING_STATE_RECORDING 1u
#define COMP_EPAPER_EXPRESSION_MEETING_STATE_FINALIZED 2u
#define COMP_EPAPER_EXPRESSION_MEETING_SUMMARY_PENDING 1u
#define COMP_EPAPER_EXPRESSION_MEETING_SYNC_COMPLETE 1u
#define COMP_EPAPER_EXPRESSION_RECORDING_STATE_IDLE 0u
#define COMP_EPAPER_EXPRESSION_RECORDING_STATE_PENDING_START 1u
#define COMP_EPAPER_EXPRESSION_RECORDING_STATE_RECORDING 2u
#define COMP_EPAPER_EXPRESSION_RECORDING_STATE_STOPPING 3u
#define COMP_EPAPER_EXPRESSION_RECORDING_STATE_CANCELED 4u
#define COMP_EPAPER_EXPRESSION_RECORDING_STATE_TRANSFER_READY 5u
#define COMP_EPAPER_EXPRESSION_RECORDING_STATE_TRANSFER_ACTIVE 6u
#define COMP_EPAPER_EXPRESSION_RECORDING_STATE_TRANSFERRED 7u
#define COMP_EPAPER_EXPRESSION_RECORDING_STATE_ERROR_RECOVERY 8u
#define COMP_EPAPER_EXPRESSION_SPEAKER_STATE_PROMPT_ACCEPTED 2u
#define COMP_EPAPER_EXPRESSION_WAKE_ENGINE_ARMED 1u
#define COMP_EPAPER_EXPRESSION_WAKE_EVENT_DETECTED 2u
#define COMP_EPAPER_EXPRESSION_OTA_LOW_BATTERY_BLOCKER_BIT 3u
#define COMP_EPAPER_EXPRESSION_OTA_LOW_BATTERY_BLOCKER \
    (1u << COMP_EPAPER_EXPRESSION_OTA_LOW_BATTERY_BLOCKER_BIT)

bool comp_epaper_expression_signal_from_diag_event(
    uint16_t event_code,
    uint8_t severity,
    uint32_t arg0,
    uint32_t arg1,
    uint32_t arg2,
    uint32_t arg3,
    comp_epaper_expression_signal_t *out_signal);

bool comp_epaper_expression_signal_from_device_status(
    uint8_t active_mode,
    uint16_t fault_bitmap,
    comp_epaper_expression_signal_t *out_signal);

bool comp_epaper_expression_signal_from_meeting_status(
    uint8_t state,
    uint8_t summary_state,
    uint8_t sync_state,
    uint8_t last_error,
    comp_epaper_expression_signal_t *out_signal);

bool comp_epaper_expression_signal_from_recording_state(
    uint8_t state,
    comp_epaper_expression_signal_t *out_signal);

bool comp_epaper_expression_signal_from_speaker_status(
    uint8_t state,
    uint8_t last_error,
    comp_epaper_expression_signal_t *out_signal);

bool comp_epaper_expression_signal_from_wake_word_status(
    uint8_t armed,
    uint8_t engine_state,
    uint8_t last_event,
    uint8_t last_error,
    comp_epaper_expression_signal_t *out_signal);

bool comp_epaper_expression_signal_from_ota_readiness(
    uint16_t blocker_bitmap,
    comp_epaper_expression_signal_t *out_signal);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_EXPRESSION_EVENTS_H */
