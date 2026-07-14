#include "recording_fsm.h"

#include "../diag_log/diag_log.h"

static uint8_t comp_recording_diag_source(comp_recording_source_t source)
{
    switch (source) {
    case COMP_RECORDING_SOURCE_USER_BUTTON:
        return 1u;
    case COMP_RECORDING_SOURCE_USER_TOUCH:
        return 4u;
    case COMP_RECORDING_SOURCE_HOST_BLE_CONTROL:
        return 2u;
    case COMP_RECORDING_SOURCE_SYNTHETIC_FIXTURE:
        return 3u;
    default:
        return 0u;
    }
}

static comp_recording_snapshot_t comp_recording_snapshot(
    const comp_recording_fsm_t *fsm)
{
    comp_recording_snapshot_t snapshot = {
        .state = fsm != NULL ? fsm->state : COMP_RECORDING_STATE_ERROR_RECOVERY,
        .capture_ready = fsm != NULL && fsm->capture_ready,
        .active_capture = false,
        .stop_requested = false,
        .transfer_window_open = false,
    };
    if (fsm != NULL) {
        snapshot.active_capture = fsm->state == COMP_RECORDING_STATE_RECORDING ||
                                  fsm->state == COMP_RECORDING_STATE_STOPPING;
        snapshot.stop_requested = fsm->state == COMP_RECORDING_STATE_STOPPING;
        snapshot.transfer_window_open =
            fsm->state == COMP_RECORDING_STATE_TRANSFER_READY ||
            fsm->state == COMP_RECORDING_STATE_TRANSFER_ACTIVE;
    }
    return snapshot;
}

static void comp_recording_log_decision(
    comp_recording_event_t event,
    comp_recording_source_t source,
    const comp_recording_decision_t *decision)
{
    uint8_t severity = decision->effect == COMP_RECORDING_EFFECT_REJECT ||
                               decision->result == COMP_RECORDING_RESULT_INTERNAL_ERROR
                           ? COMP_DIAG_SEV_WARN
                           : COMP_DIAG_SEV_INFO;
    uint16_t event_code = COMP_DIAG_EVT_RECORDING_FSM_TRANSITION;

    if (decision->effect == COMP_RECORDING_EFFECT_REJECT) {
        event_code = COMP_DIAG_EVT_RECORDING_FSM_REJECTED;
    } else if (event == COMP_RECORDING_EVENT_START_REQUEST ||
               (event == COMP_RECORDING_EVENT_TOGGLE_REQUEST &&
                decision->effect == COMP_RECORDING_EFFECT_START_CAPTURE)) {
        event_code = COMP_DIAG_EVT_RECORDING_FSM_START_REQUEST;
    } else if (event == COMP_RECORDING_EVENT_STOP_REQUEST ||
               (event == COMP_RECORDING_EVENT_TOGGLE_REQUEST &&
                decision->effect == COMP_RECORDING_EFFECT_STOP_CAPTURE)) {
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

void comp_recording_fsm_init(comp_recording_fsm_t *fsm)
{
    const comp_microphone_format_t *mic_format = comp_microphone_default_format();
    denzic_audio_format_v1_t format = denzic_audio_recording_default_format_v1();
    if (mic_format != NULL) {
        format.source_family =
            (denzic_audio_source_family_v1_t)mic_format->source_family;
        format.ingress = (denzic_audio_ingress_v1_t)mic_format->stm32_ingress;
        format.encoding = (denzic_audio_encoding_v1_t)mic_format->encoding;
        format.sample_rate_hz = mic_format->sample_rate_hz;
        format.bits_per_sample = mic_format->bits_per_sample;
        format.channels = mic_format->channels;
        format.frame_samples = mic_format->frame_samples;
    }
    denzic_audio_recording_init_v1(fsm, &format);
}

void comp_recording_fsm_set_capture_ready(comp_recording_fsm_t *fsm, bool ready)
{
    denzic_audio_recording_set_capture_ready_v1(fsm, ready);
}

comp_recording_decision_t comp_recording_fsm_decide_transition(
    comp_recording_event_t event,
    const comp_recording_snapshot_t *snapshot)
{
    return denzic_audio_recording_decide_v1(event, snapshot);
}

comp_recording_result_t comp_recording_fsm_dispatch(
    comp_recording_fsm_t *fsm,
    comp_recording_event_t event,
    comp_recording_source_t source)
{
    if (fsm == NULL) {
        return COMP_RECORDING_RESULT_BAD_ARGUMENT;
    }
    const comp_recording_snapshot_t snapshot = comp_recording_snapshot(fsm);
    const comp_recording_decision_t decision =
        denzic_audio_recording_decide_v1(event, &snapshot);
    comp_recording_log_decision(event, source, &decision);
    const comp_recording_result_t result =
        denzic_audio_recording_dispatch_v1(fsm, event, source);

    if (decision.effect == COMP_RECORDING_EFFECT_START_CAPTURE) {
        comp_diag_log_record_code(COMP_DIAG_EVT_MICROPHONE_CAPTURE_START,
                                  COMP_DIAG_SEV_INFO,
                                  fsm->metadata.recording_id,
                                  fsm->metadata.sample_format.sample_rate_hz,
                                  fsm->metadata.sample_format.bits_per_sample,
                                  fsm->metadata.sample_format.channels);
    }
    return result;
}

comp_recording_result_t comp_recording_fsm_feed_microphone_frames(
    comp_recording_fsm_t *fsm,
    const comp_microphone_frame_batch_t *batch)
{
    if (batch == NULL) {
        return COMP_RECORDING_RESULT_BAD_ARGUMENT;
    }
    const denzic_audio_frame_batch_v1_t shared_batch = {
        .frame_count = batch->frame_count,
        .samples_per_frame = batch->samples_per_frame,
        .bytes_per_frame = batch->bytes_per_frame,
        .duration_ms = batch->duration_ms,
        .dropped_frames = batch->dropped_frames,
        .crc32 = batch->crc32,
    };
    const comp_recording_result_t result =
        denzic_audio_recording_feed_v1(fsm, &shared_batch);
    if (result != COMP_RECORDING_RESULT_OK) {
        comp_diag_log_record_code(COMP_DIAG_EVT_RECORDING_FSM_REJECTED,
                                  COMP_DIAG_SEV_WARN,
                                  COMP_RECORDING_EVENT_MIC_READY,
                                  fsm != NULL ? (uint32_t)fsm->state : 0u,
                                  0u,
                                  0u);
    } else if (batch->dropped_frames != 0u) {
        comp_diag_log_record_code(COMP_DIAG_EVT_MICROPHONE_CAPTURE_DROP,
                                  COMP_DIAG_SEV_WARN,
                                  fsm->metadata.recording_id,
                                  batch->dropped_frames,
                                  batch->frame_count,
                                  (uint32_t)batch->frame_count *
                                      (uint32_t)batch->bytes_per_frame);
    }
    return result;
}

const comp_recording_metadata_t *comp_recording_fsm_metadata(
    const comp_recording_fsm_t *fsm)
{
    return denzic_audio_recording_metadata_v1(fsm);
}

size_t comp_recording_fsm_artifact_count(void)
{
    return denzic_audio_recording_transition_count_v1();
}

const comp_recording_transition_case_t *comp_recording_fsm_artifact_at(
    size_t index)
{
    return denzic_audio_recording_transition_at_v1(index);
}

const char *comp_recording_state_name(comp_recording_state_t state)
{
    return denzic_audio_recording_state_name_v1(state);
}

const char *comp_recording_event_name(comp_recording_event_t event)
{
    return denzic_audio_recording_event_name_v1(event);
}

const char *comp_recording_effect_name(comp_recording_effect_t effect)
{
    return denzic_audio_recording_effect_name_v1(effect);
}
