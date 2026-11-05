#ifndef COMPANION_RECORDING_FSM_H
#define COMPANION_RECORDING_FSM_H

#include "microphone.h"
#include "denzic_audio_recording_v1.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef denzic_audio_recording_state_v1_t comp_recording_state_t;
typedef denzic_audio_recording_event_v1_t comp_recording_event_t;
typedef denzic_audio_recording_source_v1_t comp_recording_source_t;
typedef denzic_audio_recording_result_v1_t comp_recording_result_t;
typedef denzic_audio_recording_effect_v1_t comp_recording_effect_t;
typedef denzic_audio_recording_sync_v1_t comp_recording_sync_state_t;
typedef denzic_audio_recording_metadata_v1_t comp_recording_metadata_t;
typedef denzic_audio_recording_snapshot_v1_t comp_recording_snapshot_t;
typedef denzic_audio_recording_decision_v1_t comp_recording_decision_t;
typedef denzic_audio_recording_context_v1_t comp_recording_fsm_t;
typedef denzic_audio_recording_transition_case_v1_t
    comp_recording_transition_case_t;

#define COMP_RECORDING_STATE_IDLE DENZIC_AUDIO_RECORDING_STATE_IDLE
#define COMP_RECORDING_STATE_PENDING_START \
    DENZIC_AUDIO_RECORDING_STATE_PENDING_START
#define COMP_RECORDING_STATE_RECORDING DENZIC_AUDIO_RECORDING_STATE_RECORDING
#define COMP_RECORDING_STATE_STOPPING DENZIC_AUDIO_RECORDING_STATE_STOPPING
#define COMP_RECORDING_STATE_CANCELED DENZIC_AUDIO_RECORDING_STATE_CANCELED
#define COMP_RECORDING_STATE_TRANSFER_READY \
    DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY
#define COMP_RECORDING_STATE_TRANSFER_ACTIVE \
    DENZIC_AUDIO_RECORDING_STATE_TRANSFER_ACTIVE
#define COMP_RECORDING_STATE_TRANSFERRED DENZIC_AUDIO_RECORDING_STATE_TRANSFERRED
#define COMP_RECORDING_STATE_ERROR_RECOVERY \
    DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY

#define COMP_RECORDING_EVENT_START_REQUEST \
    DENZIC_AUDIO_RECORDING_EVENT_START_REQUEST
#define COMP_RECORDING_EVENT_MIC_READY DENZIC_AUDIO_RECORDING_EVENT_CAPTURE_READY
#define COMP_RECORDING_EVENT_STOP_REQUEST \
    DENZIC_AUDIO_RECORDING_EVENT_STOP_REQUEST
#define COMP_RECORDING_EVENT_CANCEL_REQUEST \
    DENZIC_AUDIO_RECORDING_EVENT_CANCEL_REQUEST
#define COMP_RECORDING_EVENT_SESSION_FINISHED \
    DENZIC_AUDIO_RECORDING_EVENT_SESSION_FINISHED
#define COMP_RECORDING_EVENT_TRANSFER_BEGIN \
    DENZIC_AUDIO_RECORDING_EVENT_TRANSFER_BEGIN
#define COMP_RECORDING_EVENT_TRANSFER_FINISHED \
    DENZIC_AUDIO_RECORDING_EVENT_TRANSFER_FINISHED
#define COMP_RECORDING_EVENT_ERROR_DETECTED \
    DENZIC_AUDIO_RECORDING_EVENT_ERROR_DETECTED
#define COMP_RECORDING_EVENT_RECOVERY_COMPLETE \
    DENZIC_AUDIO_RECORDING_EVENT_RECOVERY_COMPLETE
#define COMP_RECORDING_EVENT_TOGGLE_REQUEST \
    DENZIC_AUDIO_RECORDING_EVENT_TOGGLE_REQUEST

#define COMP_RECORDING_SOURCE_UNKNOWN DENZIC_AUDIO_RECORDING_SOURCE_UNKNOWN
#define COMP_RECORDING_SOURCE_USER_BUTTON \
    DENZIC_AUDIO_RECORDING_SOURCE_USER_BUTTON
#define COMP_RECORDING_SOURCE_USER_TOUCH \
    DENZIC_AUDIO_RECORDING_SOURCE_USER_TOUCH
#define COMP_RECORDING_SOURCE_HOST_BLE_CONTROL \
    DENZIC_AUDIO_RECORDING_SOURCE_HOST_CONTROL
#define COMP_RECORDING_SOURCE_SYNTHETIC_FIXTURE \
    DENZIC_AUDIO_RECORDING_SOURCE_SYNTHETIC_FIXTURE

#define COMP_RECORDING_RESULT_OK DENZIC_AUDIO_RECORDING_RESULT_OK
#define COMP_RECORDING_RESULT_INVALID_STATE \
    DENZIC_AUDIO_RECORDING_RESULT_INVALID_STATE
#define COMP_RECORDING_RESULT_MIC_UNAVAILABLE \
    DENZIC_AUDIO_RECORDING_RESULT_CAPTURE_UNAVAILABLE
#define COMP_RECORDING_RESULT_BUSY DENZIC_AUDIO_RECORDING_RESULT_BUSY
#define COMP_RECORDING_RESULT_BAD_ARGUMENT \
    DENZIC_AUDIO_RECORDING_RESULT_BAD_ARGUMENT
#define COMP_RECORDING_RESULT_INTERNAL_ERROR \
    DENZIC_AUDIO_RECORDING_RESULT_INTERNAL_ERROR

#define COMP_RECORDING_EFFECT_IGNORE DENZIC_AUDIO_RECORDING_EFFECT_IGNORE
#define COMP_RECORDING_EFFECT_ENTER_PENDING_START \
    DENZIC_AUDIO_RECORDING_EFFECT_ENTER_PENDING_START
#define COMP_RECORDING_EFFECT_START_CAPTURE \
    DENZIC_AUDIO_RECORDING_EFFECT_START_CAPTURE
#define COMP_RECORDING_EFFECT_STOP_CAPTURE \
    DENZIC_AUDIO_RECORDING_EFFECT_STOP_CAPTURE
#define COMP_RECORDING_EFFECT_CANCEL_CAPTURE \
    DENZIC_AUDIO_RECORDING_EFFECT_CANCEL_CAPTURE
#define COMP_RECORDING_EFFECT_MARK_TRANSFER_READY \
    DENZIC_AUDIO_RECORDING_EFFECT_MARK_TRANSFER_READY
#define COMP_RECORDING_EFFECT_BEGIN_TRANSFER \
    DENZIC_AUDIO_RECORDING_EFFECT_BEGIN_TRANSFER
#define COMP_RECORDING_EFFECT_FINISH_TRANSFER \
    DENZIC_AUDIO_RECORDING_EFFECT_FINISH_TRANSFER
#define COMP_RECORDING_EFFECT_ENTER_ERROR_RECOVERY \
    DENZIC_AUDIO_RECORDING_EFFECT_ENTER_ERROR_RECOVERY
#define COMP_RECORDING_EFFECT_RECOVER_TO_IDLE \
    DENZIC_AUDIO_RECORDING_EFFECT_RECOVER_TO_IDLE
#define COMP_RECORDING_EFFECT_REJECT DENZIC_AUDIO_RECORDING_EFFECT_REJECT

#define COMP_RECORDING_SYNC_UNSYNCED DENZIC_AUDIO_RECORDING_SYNC_UNSYNCED
#define COMP_RECORDING_SYNC_TRANSFER_ACTIVE \
    DENZIC_AUDIO_RECORDING_SYNC_TRANSFER_ACTIVE
#define COMP_RECORDING_SYNC_TRANSFERRED DENZIC_AUDIO_RECORDING_SYNC_TRANSFERRED
#define COMP_RECORDING_SYNC_DELETED DENZIC_AUDIO_RECORDING_SYNC_DELETED

void comp_recording_fsm_init(comp_recording_fsm_t *fsm);
void comp_recording_fsm_set_capture_ready(comp_recording_fsm_t *fsm, bool ready);
comp_recording_decision_t comp_recording_fsm_decide_transition(
    comp_recording_event_t event,
    const comp_recording_snapshot_t *snapshot);
comp_recording_result_t comp_recording_fsm_dispatch(
    comp_recording_fsm_t *fsm,
    comp_recording_event_t event,
    comp_recording_source_t source);
comp_recording_result_t comp_recording_fsm_feed_microphone_frames(
    comp_recording_fsm_t *fsm,
    const comp_microphone_frame_batch_t *batch);
const comp_recording_metadata_t *comp_recording_fsm_metadata(
    const comp_recording_fsm_t *fsm);
size_t comp_recording_fsm_artifact_count(void);
const comp_recording_transition_case_t *comp_recording_fsm_artifact_at(
    size_t index);
const char *comp_recording_state_name(comp_recording_state_t state);
const char *comp_recording_event_name(comp_recording_event_t event);
const char *comp_recording_effect_name(comp_recording_effect_t effect);

#ifdef __cplusplus
}
#endif

#endif
