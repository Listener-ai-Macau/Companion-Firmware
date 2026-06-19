#include "recording_fsm.h"

#include "../diag_log/diag_log.h"

#include <string.h>

#define COMP_RECORDING_INITIAL_ID 1u

static const comp_recording_transition_case_t COMP_RECORDING_FSM_ARTIFACT[] = {
    {
        "start_idle_to_recording",
        COMP_RECORDING_STATE_IDLE,
        COMP_RECORDING_EVENT_START_REQUEST,
        true,
        false,
        false,
        false,
        COMP_RECORDING_EFFECT_START_CAPTURE,
        COMP_RECORDING_STATE_RECORDING,
        COMP_RECORDING_RESULT_OK,
        "start_recording",
    },
    {
        "start_idle_to_pending_start",
        COMP_RECORDING_STATE_IDLE,
        COMP_RECORDING_EVENT_START_REQUEST,
        false,
        false,
        false,
        false,
        COMP_RECORDING_EFFECT_ENTER_PENDING_START,
        COMP_RECORDING_STATE_PENDING_START,
        COMP_RECORDING_RESULT_MIC_UNAVAILABLE,
        "pending_start_mic_not_ready",
    },
    {
        "mic_ready_pending_start",
        COMP_RECORDING_STATE_PENDING_START,
        COMP_RECORDING_EVENT_MIC_READY,
        true,
        false,
        false,
        false,
        COMP_RECORDING_EFFECT_START_CAPTURE,
        COMP_RECORDING_STATE_RECORDING,
        COMP_RECORDING_RESULT_OK,
        "pending_start_microphone_ready",
    },
    {
        "reject_start_while_recording",
        COMP_RECORDING_STATE_RECORDING,
        COMP_RECORDING_EVENT_START_REQUEST,
        true,
        true,
        false,
        false,
        COMP_RECORDING_EFFECT_REJECT,
        COMP_RECORDING_STATE_RECORDING,
        COMP_RECORDING_RESULT_BUSY,
        "start_rejected_recording_active",
    },
    {
        "reject_start_while_stopping",
        COMP_RECORDING_STATE_STOPPING,
        COMP_RECORDING_EVENT_START_REQUEST,
        true,
        true,
        true,
        false,
        COMP_RECORDING_EFFECT_REJECT,
        COMP_RECORDING_STATE_STOPPING,
        COMP_RECORDING_RESULT_BUSY,
        "start_rejected_stop_in_progress",
    },
    {
        "stop_recording_to_stopping",
        COMP_RECORDING_STATE_RECORDING,
        COMP_RECORDING_EVENT_STOP_REQUEST,
        true,
        true,
        false,
        false,
        COMP_RECORDING_EFFECT_STOP_CAPTURE,
        COMP_RECORDING_STATE_STOPPING,
        COMP_RECORDING_RESULT_OK,
        "stop_requested",
    },
    {
        "session_finished_after_stop",
        COMP_RECORDING_STATE_STOPPING,
        COMP_RECORDING_EVENT_SESSION_FINISHED,
        true,
        false,
        true,
        false,
        COMP_RECORDING_EFFECT_MARK_TRANSFER_READY,
        COMP_RECORDING_STATE_TRANSFER_READY,
        COMP_RECORDING_RESULT_OK,
        "recording_session_finished",
    },
    {
        "cancel_pending_start",
        COMP_RECORDING_STATE_PENDING_START,
        COMP_RECORDING_EVENT_CANCEL_REQUEST,
        false,
        false,
        false,
        false,
        COMP_RECORDING_EFFECT_CANCEL_CAPTURE,
        COMP_RECORDING_STATE_CANCELED,
        COMP_RECORDING_RESULT_OK,
        "pending_start_canceled",
    },
    {
        "cancel_recording",
        COMP_RECORDING_STATE_RECORDING,
        COMP_RECORDING_EVENT_CANCEL_REQUEST,
        true,
        true,
        false,
        false,
        COMP_RECORDING_EFFECT_CANCEL_CAPTURE,
        COMP_RECORDING_STATE_CANCELED,
        COMP_RECORDING_RESULT_OK,
        "recording_canceled",
    },
    {
        "transfer_ready_to_active",
        COMP_RECORDING_STATE_TRANSFER_READY,
        COMP_RECORDING_EVENT_TRANSFER_BEGIN,
        true,
        false,
        false,
        true,
        COMP_RECORDING_EFFECT_BEGIN_TRANSFER,
        COMP_RECORDING_STATE_TRANSFER_ACTIVE,
        COMP_RECORDING_RESULT_OK,
        "recording_transfer_active",
    },
    {
        "transfer_active_to_transferred",
        COMP_RECORDING_STATE_TRANSFER_ACTIVE,
        COMP_RECORDING_EVENT_TRANSFER_FINISHED,
        true,
        false,
        false,
        true,
        COMP_RECORDING_EFFECT_FINISH_TRANSFER,
        COMP_RECORDING_STATE_TRANSFERRED,
        COMP_RECORDING_RESULT_OK,
        "recording_transferred",
    },
    {
        "error_during_recording",
        COMP_RECORDING_STATE_RECORDING,
        COMP_RECORDING_EVENT_ERROR_DETECTED,
        true,
        true,
        false,
        false,
        COMP_RECORDING_EFFECT_ENTER_ERROR_RECOVERY,
        COMP_RECORDING_STATE_ERROR_RECOVERY,
        COMP_RECORDING_RESULT_INTERNAL_ERROR,
        "recording_error_recovery",
    },
    {
        "recovery_complete_to_idle",
        COMP_RECORDING_STATE_ERROR_RECOVERY,
        COMP_RECORDING_EVENT_RECOVERY_COMPLETE,
        true,
        false,
        false,
        false,
        COMP_RECORDING_EFFECT_RECOVER_TO_IDLE,
        COMP_RECORDING_STATE_IDLE,
        COMP_RECORDING_RESULT_OK,
        "recording_recovered",
    },
};

size_t comp_recording_fsm_artifact_count(void)
{
    return sizeof(COMP_RECORDING_FSM_ARTIFACT) / sizeof(COMP_RECORDING_FSM_ARTIFACT[0]);
}

const comp_recording_transition_case_t *comp_recording_fsm_artifact_at(size_t index)
{
    if (index >= comp_recording_fsm_artifact_count()) {
        return 0;
    }
    return &COMP_RECORDING_FSM_ARTIFACT[index];
}

static comp_recording_snapshot_t comp_recording_snapshot_from_fsm(const comp_recording_fsm_t *fsm)
{
    comp_recording_snapshot_t snapshot = {
        .state = fsm != 0 ? fsm->state : COMP_RECORDING_STATE_ERROR_RECOVERY,
        .microphone_ready = true,
        .active_capture = false,
        .stop_requested = false,
        .transfer_window_open = false,
    };

    if (fsm == 0) {
        return snapshot;
    }

    snapshot.active_capture = fsm->state == COMP_RECORDING_STATE_RECORDING ||
                              fsm->state == COMP_RECORDING_STATE_STOPPING;
    snapshot.stop_requested = fsm->state == COMP_RECORDING_STATE_STOPPING;
    snapshot.transfer_window_open = fsm->state == COMP_RECORDING_STATE_TRANSFER_READY ||
                                    fsm->state == COMP_RECORDING_STATE_TRANSFER_ACTIVE;
    return snapshot;
}

const char *comp_recording_state_name(comp_recording_state_t state)
{
    switch (state) {
    case COMP_RECORDING_STATE_IDLE:
        return "idle";
    case COMP_RECORDING_STATE_PENDING_START:
        return "pending_start";
    case COMP_RECORDING_STATE_RECORDING:
        return "recording";
    case COMP_RECORDING_STATE_STOPPING:
        return "stopping";
    case COMP_RECORDING_STATE_CANCELED:
        return "canceled";
    case COMP_RECORDING_STATE_TRANSFER_READY:
        return "transfer_ready";
    case COMP_RECORDING_STATE_TRANSFER_ACTIVE:
        return "transfer_active";
    case COMP_RECORDING_STATE_TRANSFERRED:
        return "transferred";
    case COMP_RECORDING_STATE_ERROR_RECOVERY:
        return "error_recovery";
    default:
        return "unknown";
    }
}

const char *comp_recording_event_name(comp_recording_event_t event)
{
    switch (event) {
    case COMP_RECORDING_EVENT_START_REQUEST:
        return "start_request";
    case COMP_RECORDING_EVENT_MIC_READY:
        return "mic_ready";
    case COMP_RECORDING_EVENT_STOP_REQUEST:
        return "stop_request";
    case COMP_RECORDING_EVENT_CANCEL_REQUEST:
        return "cancel_request";
    case COMP_RECORDING_EVENT_SESSION_FINISHED:
        return "session_finished";
    case COMP_RECORDING_EVENT_TRANSFER_BEGIN:
        return "transfer_begin";
    case COMP_RECORDING_EVENT_TRANSFER_FINISHED:
        return "transfer_finished";
    case COMP_RECORDING_EVENT_ERROR_DETECTED:
        return "error_detected";
    case COMP_RECORDING_EVENT_RECOVERY_COMPLETE:
        return "recovery_complete";
    default:
        return "unknown";
    }
}

const char *comp_recording_effect_name(comp_recording_effect_t effect)
{
    switch (effect) {
    case COMP_RECORDING_EFFECT_IGNORE:
        return "ignore";
    case COMP_RECORDING_EFFECT_ENTER_PENDING_START:
        return "enter_pending_start";
    case COMP_RECORDING_EFFECT_START_CAPTURE:
        return "start_capture";
    case COMP_RECORDING_EFFECT_STOP_CAPTURE:
        return "stop_capture";
    case COMP_RECORDING_EFFECT_CANCEL_CAPTURE:
        return "cancel_capture";
    case COMP_RECORDING_EFFECT_MARK_TRANSFER_READY:
        return "mark_transfer_ready";
    case COMP_RECORDING_EFFECT_BEGIN_TRANSFER:
        return "begin_transfer";
    case COMP_RECORDING_EFFECT_FINISH_TRANSFER:
        return "finish_transfer";
    case COMP_RECORDING_EFFECT_ENTER_ERROR_RECOVERY:
        return "enter_error_recovery";
    case COMP_RECORDING_EFFECT_RECOVER_TO_IDLE:
        return "recover_to_idle";
    case COMP_RECORDING_EFFECT_REJECT:
        return "reject";
    default:
        return "unknown";
    }
}

static comp_recording_decision_t comp_recording_make_decision(comp_recording_effect_t effect,
                                                              comp_recording_state_t next_state,
                                                              comp_recording_result_t result,
                                                              const char *detail)
{
    comp_recording_decision_t decision = {
        .effect = effect,
        .next_state = next_state,
        .result = result,
        .detail = detail,
    };
    return decision;
}

comp_recording_decision_t comp_recording_fsm_decide_transition(
    comp_recording_event_t event,
    const comp_recording_snapshot_t *snapshot)
{
    comp_recording_state_t state = snapshot != 0 ? snapshot->state : COMP_RECORDING_STATE_ERROR_RECOVERY;

    if (event == COMP_RECORDING_EVENT_ERROR_DETECTED) {
        return comp_recording_make_decision(
            COMP_RECORDING_EFFECT_ENTER_ERROR_RECOVERY,
            COMP_RECORDING_STATE_ERROR_RECOVERY,
            COMP_RECORDING_RESULT_INTERNAL_ERROR,
            "recording_error_recovery");
    }

    if (event == COMP_RECORDING_EVENT_RECOVERY_COMPLETE) {
        if (state == COMP_RECORDING_STATE_ERROR_RECOVERY ||
            state == COMP_RECORDING_STATE_CANCELED ||
            state == COMP_RECORDING_STATE_TRANSFERRED) {
            return comp_recording_make_decision(
                COMP_RECORDING_EFFECT_RECOVER_TO_IDLE,
                COMP_RECORDING_STATE_IDLE,
                COMP_RECORDING_RESULT_OK,
                "recording_recovered");
        }
        return comp_recording_make_decision(
            COMP_RECORDING_EFFECT_IGNORE,
            state,
            COMP_RECORDING_RESULT_INVALID_STATE,
            "recovery_ignored_not_needed");
    }

    if (event == COMP_RECORDING_EVENT_START_REQUEST) {
        if (state == COMP_RECORDING_STATE_IDLE ||
            state == COMP_RECORDING_STATE_CANCELED ||
            state == COMP_RECORDING_STATE_TRANSFERRED) {
            if (snapshot != 0 && snapshot->microphone_ready) {
                return comp_recording_make_decision(
                    COMP_RECORDING_EFFECT_START_CAPTURE,
                    COMP_RECORDING_STATE_RECORDING,
                    COMP_RECORDING_RESULT_OK,
                    "start_recording");
            }
            return comp_recording_make_decision(
                COMP_RECORDING_EFFECT_ENTER_PENDING_START,
                COMP_RECORDING_STATE_PENDING_START,
                COMP_RECORDING_RESULT_MIC_UNAVAILABLE,
                "pending_start_mic_not_ready");
        }
        return comp_recording_make_decision(
            COMP_RECORDING_EFFECT_REJECT,
            state,
            COMP_RECORDING_RESULT_BUSY,
            state == COMP_RECORDING_STATE_STOPPING ? "start_rejected_stop_in_progress" : "start_rejected_busy");
    }

    if (event == COMP_RECORDING_EVENT_MIC_READY) {
        if (state == COMP_RECORDING_STATE_PENDING_START) {
            return comp_recording_make_decision(
                COMP_RECORDING_EFFECT_START_CAPTURE,
                COMP_RECORDING_STATE_RECORDING,
                COMP_RECORDING_RESULT_OK,
                "pending_start_microphone_ready");
        }
        return comp_recording_make_decision(
            COMP_RECORDING_EFFECT_IGNORE,
            state,
            COMP_RECORDING_RESULT_INVALID_STATE,
            "mic_ready_ignored");
    }

    if (event == COMP_RECORDING_EVENT_STOP_REQUEST) {
        if (state == COMP_RECORDING_STATE_RECORDING) {
            return comp_recording_make_decision(
                COMP_RECORDING_EFFECT_STOP_CAPTURE,
                COMP_RECORDING_STATE_STOPPING,
                COMP_RECORDING_RESULT_OK,
                "stop_requested");
        }
        if (state == COMP_RECORDING_STATE_PENDING_START) {
            return comp_recording_make_decision(
                COMP_RECORDING_EFFECT_CANCEL_CAPTURE,
                COMP_RECORDING_STATE_CANCELED,
                COMP_RECORDING_RESULT_OK,
                "stop_cleared_pending_start");
        }
        return comp_recording_make_decision(
            COMP_RECORDING_EFFECT_REJECT,
            state,
            COMP_RECORDING_RESULT_INVALID_STATE,
            "stop_rejected_no_active_session");
    }

    if (event == COMP_RECORDING_EVENT_CANCEL_REQUEST) {
        if (state == COMP_RECORDING_STATE_PENDING_START ||
            state == COMP_RECORDING_STATE_RECORDING ||
            state == COMP_RECORDING_STATE_STOPPING ||
            state == COMP_RECORDING_STATE_TRANSFER_READY ||
            state == COMP_RECORDING_STATE_TRANSFER_ACTIVE) {
            return comp_recording_make_decision(
                COMP_RECORDING_EFFECT_CANCEL_CAPTURE,
                COMP_RECORDING_STATE_CANCELED,
                COMP_RECORDING_RESULT_OK,
                state == COMP_RECORDING_STATE_PENDING_START ? "pending_start_canceled" : "recording_canceled");
        }
        return comp_recording_make_decision(
            COMP_RECORDING_EFFECT_IGNORE,
            state,
            COMP_RECORDING_RESULT_INVALID_STATE,
            "cancel_ignored_no_active_session");
    }

    if (event == COMP_RECORDING_EVENT_SESSION_FINISHED) {
        if (state == COMP_RECORDING_STATE_STOPPING) {
            return comp_recording_make_decision(
                COMP_RECORDING_EFFECT_MARK_TRANSFER_READY,
                COMP_RECORDING_STATE_TRANSFER_READY,
                COMP_RECORDING_RESULT_OK,
                "recording_session_finished");
        }
        if (state == COMP_RECORDING_STATE_RECORDING) {
            return comp_recording_make_decision(
                COMP_RECORDING_EFFECT_ENTER_ERROR_RECOVERY,
                COMP_RECORDING_STATE_ERROR_RECOVERY,
                COMP_RECORDING_RESULT_INTERNAL_ERROR,
                "session_finished_without_stop");
        }
        return comp_recording_make_decision(
            COMP_RECORDING_EFFECT_IGNORE,
            state,
            COMP_RECORDING_RESULT_INVALID_STATE,
            "session_finished_ignored");
    }

    if (event == COMP_RECORDING_EVENT_TRANSFER_BEGIN) {
        if (state == COMP_RECORDING_STATE_TRANSFER_READY) {
            return comp_recording_make_decision(
                COMP_RECORDING_EFFECT_BEGIN_TRANSFER,
                COMP_RECORDING_STATE_TRANSFER_ACTIVE,
                COMP_RECORDING_RESULT_OK,
                "recording_transfer_active");
        }
        return comp_recording_make_decision(
            COMP_RECORDING_EFFECT_REJECT,
            state,
            COMP_RECORDING_RESULT_INVALID_STATE,
            "transfer_begin_rejected");
    }

    if (event == COMP_RECORDING_EVENT_TRANSFER_FINISHED) {
        if (state == COMP_RECORDING_STATE_TRANSFER_ACTIVE) {
            return comp_recording_make_decision(
                COMP_RECORDING_EFFECT_FINISH_TRANSFER,
                COMP_RECORDING_STATE_TRANSFERRED,
                COMP_RECORDING_RESULT_OK,
                "recording_transferred");
        }
        return comp_recording_make_decision(
            COMP_RECORDING_EFFECT_REJECT,
            state,
            COMP_RECORDING_RESULT_INVALID_STATE,
            "transfer_finished_rejected");
    }

    return comp_recording_make_decision(
        COMP_RECORDING_EFFECT_REJECT,
        state,
        COMP_RECORDING_RESULT_BAD_ARGUMENT,
        "unknown_recording_event");
}

static uint8_t comp_recording_diag_source(comp_recording_source_t source)
{
    switch (source) {
    case COMP_RECORDING_SOURCE_USER_BUTTON:
        return 1u;
    case COMP_RECORDING_SOURCE_HOST_BLE_CONTROL:
        return 2u;
    case COMP_RECORDING_SOURCE_SYNTHETIC_FIXTURE:
        return 3u;
    default:
        return 0u;
    }
}

static void comp_recording_log_decision(comp_recording_event_t event,
                                        comp_recording_source_t source,
                                        const comp_recording_decision_t *decision)
{
    uint8_t severity = decision->effect == COMP_RECORDING_EFFECT_REJECT ||
                               decision->result == COMP_RECORDING_RESULT_INTERNAL_ERROR ?
                           COMP_DIAG_SEV_WARN :
                           COMP_DIAG_SEV_INFO;
    uint16_t event_code = COMP_DIAG_EVT_RECORDING_FSM_TRANSITION;

    if (decision->effect == COMP_RECORDING_EFFECT_REJECT) {
        event_code = COMP_DIAG_EVT_RECORDING_FSM_REJECTED;
    } else if (event == COMP_RECORDING_EVENT_START_REQUEST) {
        event_code = COMP_DIAG_EVT_RECORDING_FSM_START_REQUEST;
    } else if (event == COMP_RECORDING_EVENT_STOP_REQUEST) {
        event_code = COMP_DIAG_EVT_RECORDING_FSM_STOP_REQUEST;
    } else if (event == COMP_RECORDING_EVENT_CANCEL_REQUEST) {
        event_code = COMP_DIAG_EVT_RECORDING_FSM_CANCEL_REQUEST;
    } else if (event == COMP_RECORDING_EVENT_SESSION_FINISHED ||
               event == COMP_RECORDING_EVENT_TRANSFER_FINISHED) {
        event_code = COMP_DIAG_EVT_RECORDING_FSM_SESSION_FINISHED;
    } else if (event == COMP_RECORDING_EVENT_ERROR_DETECTED ||
               decision->result == COMP_RECORDING_RESULT_INTERNAL_ERROR) {
        event_code = COMP_DIAG_EVT_RECORDING_FSM_ERROR;
        severity = COMP_DIAG_SEV_ERROR;
    } else if (event == COMP_RECORDING_EVENT_RECOVERY_COMPLETE) {
        event_code = COMP_DIAG_EVT_RECORDING_FSM_RECOVERY;
    }

    comp_diag_log_record_code(event_code,
                              severity,
                              (uint32_t)comp_recording_diag_source(source),
                              (uint32_t)decision->next_state,
                              (uint32_t)decision->effect,
                              (uint32_t)decision->result);
}

static void comp_recording_reset_metadata(comp_recording_fsm_t *fsm)
{
    memset(&fsm->metadata, 0, sizeof(fsm->metadata));
    fsm->metadata.sample_format = *comp_microphone_default_format();
    fsm->metadata.sync_state = COMP_RECORDING_SYNC_UNSYNCED;
}

void comp_recording_fsm_init(comp_recording_fsm_t *fsm)
{
    if (fsm == 0) {
        return;
    }
    memset(fsm, 0, sizeof(*fsm));
    fsm->state = COMP_RECORDING_STATE_IDLE;
    fsm->next_recording_id = COMP_RECORDING_INITIAL_ID;
    comp_recording_reset_metadata(fsm);
}

static void comp_recording_begin_metadata(comp_recording_fsm_t *fsm)
{
    comp_recording_reset_metadata(fsm);
    fsm->metadata.recording_id = fsm->next_recording_id++;
    fsm->metadata.sample_format = *comp_microphone_default_format();
    fsm->metadata.packet_sequence_next = 0u;
    fsm->metadata.byte_offset_ready = 0u;
}

static void comp_recording_apply_decision(comp_recording_fsm_t *fsm,
                                          comp_recording_event_t event,
                                          comp_recording_source_t source,
                                          const comp_recording_decision_t *decision)
{
    comp_recording_log_decision(event, source, decision);
    fsm->state = decision->next_state;

    if (decision->effect == COMP_RECORDING_EFFECT_ENTER_PENDING_START) {
        fsm->pending_source = source;
        return;
    }

    if (decision->effect == COMP_RECORDING_EFFECT_START_CAPTURE) {
        fsm->active_source = source;
        fsm->pending_source = COMP_RECORDING_SOURCE_UNKNOWN;
        comp_recording_begin_metadata(fsm);
        comp_diag_log_record_code(COMP_DIAG_EVT_MICROPHONE_CAPTURE_START,
                                  COMP_DIAG_SEV_INFO,
                                  fsm->metadata.recording_id,
                                  fsm->metadata.sample_format.sample_rate_hz,
                                  fsm->metadata.sample_format.bits_per_sample,
                                  fsm->metadata.sample_format.channels);
        return;
    }

    if (decision->effect == COMP_RECORDING_EFFECT_STOP_CAPTURE) {
        fsm->metadata.byte_offset_ready = fsm->metadata.total_length;
        return;
    }

    if (decision->effect == COMP_RECORDING_EFFECT_CANCEL_CAPTURE) {
        fsm->metadata.sync_state = COMP_RECORDING_SYNC_DELETED;
        fsm->active_source = COMP_RECORDING_SOURCE_UNKNOWN;
        fsm->pending_source = COMP_RECORDING_SOURCE_UNKNOWN;
        return;
    }

    if (decision->effect == COMP_RECORDING_EFFECT_MARK_TRANSFER_READY) {
        fsm->metadata.byte_offset_ready = fsm->metadata.total_length;
        fsm->metadata.sync_state = COMP_RECORDING_SYNC_UNSYNCED;
        return;
    }

    if (decision->effect == COMP_RECORDING_EFFECT_BEGIN_TRANSFER) {
        fsm->metadata.sync_state = COMP_RECORDING_SYNC_TRANSFER_ACTIVE;
        fsm->metadata.packet_sequence_next = 0u;
        return;
    }

    if (decision->effect == COMP_RECORDING_EFFECT_FINISH_TRANSFER) {
        fsm->metadata.sync_state = COMP_RECORDING_SYNC_TRANSFERRED;
        fsm->metadata.byte_offset_ready = fsm->metadata.total_length;
        fsm->active_source = COMP_RECORDING_SOURCE_UNKNOWN;
        return;
    }

    if (decision->effect == COMP_RECORDING_EFFECT_ENTER_ERROR_RECOVERY) {
        fsm->metadata.sync_state = COMP_RECORDING_SYNC_UNSYNCED;
        return;
    }

    if (decision->effect == COMP_RECORDING_EFFECT_RECOVER_TO_IDLE) {
        fsm->active_source = COMP_RECORDING_SOURCE_UNKNOWN;
        fsm->pending_source = COMP_RECORDING_SOURCE_UNKNOWN;
    }
}

comp_recording_result_t comp_recording_fsm_dispatch(comp_recording_fsm_t *fsm,
                                                    comp_recording_event_t event,
                                                    comp_recording_source_t source)
{
    if (fsm == 0) {
        return COMP_RECORDING_RESULT_BAD_ARGUMENT;
    }

    comp_recording_snapshot_t snapshot = comp_recording_snapshot_from_fsm(fsm);
    comp_recording_decision_t decision = comp_recording_fsm_decide_transition(event, &snapshot);
    comp_recording_apply_decision(fsm, event, source, &decision);
    return decision.result;
}

comp_recording_result_t comp_recording_fsm_feed_microphone_frames(
    comp_recording_fsm_t *fsm,
    const comp_microphone_frame_batch_t *batch)
{
    if (fsm == 0 || batch == 0) {
        return COMP_RECORDING_RESULT_BAD_ARGUMENT;
    }
    if (fsm->state != COMP_RECORDING_STATE_RECORDING) {
        comp_diag_log_record_code(COMP_DIAG_EVT_RECORDING_FSM_REJECTED,
                                  COMP_DIAG_SEV_WARN,
                                  COMP_RECORDING_EVENT_MIC_READY,
                                  (uint32_t)fsm->state,
                                  0u,
                                  0u);
        return COMP_RECORDING_RESULT_INVALID_STATE;
    }

    uint32_t bytes = (uint32_t)batch->frame_count * (uint32_t)batch->bytes_per_frame;
    fsm->metadata.frame_count += batch->frame_count;
    fsm->metadata.duration_ms += batch->duration_ms;
    fsm->metadata.total_length += bytes;
    fsm->metadata.content_crc32 ^= batch->crc32;
    fsm->metadata.dropped_frames += batch->dropped_frames;
    fsm->metadata.sha256_prefix_words[0] ^= batch->crc32;
    fsm->metadata.sha256_prefix_words[1] += bytes;

    if (batch->dropped_frames != 0u) {
        comp_diag_log_record_code(COMP_DIAG_EVT_MICROPHONE_CAPTURE_DROP,
                                  COMP_DIAG_SEV_WARN,
                                  fsm->metadata.recording_id,
                                  batch->dropped_frames,
                                  batch->frame_count,
                                  bytes);
    }

    return COMP_RECORDING_RESULT_OK;
}

const comp_recording_metadata_t *comp_recording_fsm_metadata(const comp_recording_fsm_t *fsm)
{
    if (fsm == 0) {
        return 0;
    }
    return &fsm->metadata;
}
