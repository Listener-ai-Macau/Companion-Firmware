#ifndef COMPANION_RECORDING_FSM_H
#define COMPANION_RECORDING_FSM_H

#include "microphone.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    COMP_RECORDING_STATE_IDLE = 0,
    COMP_RECORDING_STATE_PENDING_START,
    COMP_RECORDING_STATE_RECORDING,
    COMP_RECORDING_STATE_STOPPING,
    COMP_RECORDING_STATE_CANCELED,
    COMP_RECORDING_STATE_TRANSFER_READY,
    COMP_RECORDING_STATE_TRANSFER_ACTIVE,
    COMP_RECORDING_STATE_TRANSFERRED,
    COMP_RECORDING_STATE_ERROR_RECOVERY,
} comp_recording_state_t;

typedef enum {
    COMP_RECORDING_EVENT_START_REQUEST = 0,
    COMP_RECORDING_EVENT_MIC_READY,
    COMP_RECORDING_EVENT_STOP_REQUEST,
    COMP_RECORDING_EVENT_CANCEL_REQUEST,
    COMP_RECORDING_EVENT_SESSION_FINISHED,
    COMP_RECORDING_EVENT_TRANSFER_BEGIN,
    COMP_RECORDING_EVENT_TRANSFER_FINISHED,
    COMP_RECORDING_EVENT_ERROR_DETECTED,
    COMP_RECORDING_EVENT_RECOVERY_COMPLETE,
} comp_recording_event_t;

typedef enum {
    COMP_RECORDING_SOURCE_UNKNOWN = 0,
    COMP_RECORDING_SOURCE_USER_BUTTON,
    COMP_RECORDING_SOURCE_USER_TOUCH,
    COMP_RECORDING_SOURCE_HOST_BLE_CONTROL,
    COMP_RECORDING_SOURCE_SYNTHETIC_FIXTURE,
} comp_recording_source_t;

typedef enum {
    COMP_RECORDING_RESULT_OK = 0,
    COMP_RECORDING_RESULT_INVALID_STATE,
    COMP_RECORDING_RESULT_MIC_UNAVAILABLE,
    COMP_RECORDING_RESULT_BUSY,
    COMP_RECORDING_RESULT_BAD_ARGUMENT,
    COMP_RECORDING_RESULT_INTERNAL_ERROR,
} comp_recording_result_t;

typedef enum {
    COMP_RECORDING_EFFECT_IGNORE = 0,
    COMP_RECORDING_EFFECT_ENTER_PENDING_START,
    COMP_RECORDING_EFFECT_START_CAPTURE,
    COMP_RECORDING_EFFECT_STOP_CAPTURE,
    COMP_RECORDING_EFFECT_CANCEL_CAPTURE,
    COMP_RECORDING_EFFECT_MARK_TRANSFER_READY,
    COMP_RECORDING_EFFECT_BEGIN_TRANSFER,
    COMP_RECORDING_EFFECT_FINISH_TRANSFER,
    COMP_RECORDING_EFFECT_ENTER_ERROR_RECOVERY,
    COMP_RECORDING_EFFECT_RECOVER_TO_IDLE,
    COMP_RECORDING_EFFECT_REJECT,
} comp_recording_effect_t;

typedef enum {
    COMP_RECORDING_SYNC_UNSYNCED = 0,
    COMP_RECORDING_SYNC_TRANSFER_ACTIVE,
    COMP_RECORDING_SYNC_TRANSFERRED,
    COMP_RECORDING_SYNC_DELETED,
} comp_recording_sync_state_t;

typedef struct {
    uint32_t recording_id;
    uint32_t duration_ms;
    uint32_t frame_count;
    uint32_t dropped_frames;
    uint32_t total_length;
    uint32_t content_crc32;
    uint32_t sha256_prefix_words[2];
    uint32_t packet_sequence_next;
    uint32_t byte_offset_ready;
    comp_recording_sync_state_t sync_state;
    comp_microphone_format_t sample_format;
} comp_recording_metadata_t;

typedef struct {
    comp_recording_state_t state;
    bool microphone_ready;
    bool active_capture;
    bool stop_requested;
    bool transfer_window_open;
} comp_recording_snapshot_t;

typedef struct {
    comp_recording_effect_t effect;
    comp_recording_state_t next_state;
    comp_recording_result_t result;
    const char *detail;
} comp_recording_decision_t;

typedef struct {
    comp_recording_state_t state;
    comp_recording_source_t active_source;
    comp_recording_source_t pending_source;
    uint32_t next_recording_id;
    comp_recording_metadata_t metadata;
} comp_recording_fsm_t;

typedef struct {
    const char *id;
    comp_recording_state_t state;
    comp_recording_event_t event;
    bool microphone_ready;
    bool active_capture;
    bool stop_requested;
    bool transfer_window_open;
    comp_recording_effect_t effect;
    comp_recording_state_t next_state;
    comp_recording_result_t result;
    const char *detail;
} comp_recording_transition_case_t;

void comp_recording_fsm_init(comp_recording_fsm_t *fsm);
comp_recording_decision_t comp_recording_fsm_decide_transition(
    comp_recording_event_t event,
    const comp_recording_snapshot_t *snapshot);
comp_recording_result_t comp_recording_fsm_dispatch(comp_recording_fsm_t *fsm,
                                                    comp_recording_event_t event,
                                                    comp_recording_source_t source);
comp_recording_result_t comp_recording_fsm_feed_microphone_frames(
    comp_recording_fsm_t *fsm,
    const comp_microphone_frame_batch_t *batch);
const comp_recording_metadata_t *comp_recording_fsm_metadata(const comp_recording_fsm_t *fsm);
size_t comp_recording_fsm_artifact_count(void);
const comp_recording_transition_case_t *comp_recording_fsm_artifact_at(size_t index);
const char *comp_recording_state_name(comp_recording_state_t state);
const char *comp_recording_event_name(comp_recording_event_t event);
const char *comp_recording_effect_name(comp_recording_effect_t effect);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_RECORDING_FSM_H */
