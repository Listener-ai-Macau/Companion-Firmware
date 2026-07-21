#include "expression_v22_everyday_bridge_session.h"

#include <string.h>

static bool context_is_valid(const comp_v22_everyday_bridge_context_t *context)
{
    return context != NULL && context->energy < COMP_EXPRESSION_RIG_ENERGY_COUNT &&
           context->interaction_memory <= 2u;
}

void comp_v22_everyday_bridge_session_init(comp_v22_everyday_bridge_session_t *session)
{
    if (session == NULL) {
        return;
    }
    memset(session, 0, sizeof(*session));
    session->context.energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL;
}

bool comp_v22_everyday_bridge_session_start(
    comp_v22_everyday_bridge_session_t *session,
    comp_expression_rig_emotion_t source_emotion,
    comp_v22_everyday_cue_t cue,
    const comp_v22_everyday_bridge_context_t *context)
{
    comp_v22_everyday_bridge_context_t next_context = {
        .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL,
        .interaction_memory = 0u,
    };
    comp_v22_everyday_bridge_selection_t selection;

    if (session == NULL || session->active || session->frame_outstanding) {
        if (session != NULL) {
            session->rejected_submissions++;
        }
        return false;
    }
    if (context != NULL) {
        next_context = *context;
    }
    if (!context_is_valid(&next_context) ||
        !comp_v22_everyday_bridge_select(source_emotion, cue, &selection)) {
        session->rejected_submissions++;
        return false;
    }
    session->selection = selection;
    session->context = next_context;
    session->next_step_index = 0u;
    session->active = true;
    return true;
}

bool comp_v22_everyday_bridge_session_take_frame(
    comp_v22_everyday_bridge_session_t *session,
    comp_v22_everyday_bridge_frame_t *out_frame,
    comp_expression_rig_plan_t *out_plan)
{
    const comp_v22_emotion_separation_rig_bridge_t *bridge;
    const comp_expression_rig_registered_score_step_t *step;
    const comp_v22_emotion_separation_rig_frame_t *frame;
    comp_expression_rig_state_t context;
    uint32_t hold_ms;

    if (session == NULL || out_frame == NULL || out_plan == NULL || !session->active ||
        session->frame_outstanding || !context_is_valid(&session->context) ||
        session->selection.bridge == NULL) {
        if (session != NULL) {
            session->rejected_submissions++;
        }
        return false;
    }
    bridge = session->selection.bridge;
    if (session->next_step_index >= bridge->frame_count || bridge->score == NULL ||
        bridge->frames == NULL || bridge->score->step_count != bridge->frame_count) {
        session->rejected_submissions++;
        return false;
    }
    step = &bridge->score->steps[session->next_step_index];
    frame = &bridge->frames[session->next_step_index];
    if (step->phase >= COMP_EXPRESSION_RIG_SCORE_PHASE_COUNT || step->duration_ms < 80u ||
        frame->cue == NULL) {
        session->rejected_submissions++;
        return false;
    }
    context = (comp_expression_rig_state_t){
        .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
        .emotion = session->selection.source_emotion,
        .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
        .energy = session->context.energy,
        .interaction_memory = session->context.interaction_memory,
        .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN,
    };
    if (!comp_v22_everyday_bridge_build_step(&session->selection, session->next_step_index,
                                              &context, out_plan)) {
        session->rejected_submissions++;
        return false;
    }
    hold_ms = step->duration_ms;
    if (hold_ms < COMP_V22_EVERYDAY_BRIDGE_MIN_POST_REFRESH_HOLD_MS) {
        hold_ms = COMP_V22_EVERYDAY_BRIDGE_MIN_POST_REFRESH_HOLD_MS;
    }
    if (hold_ms > 5000u) {
        session->rejected_submissions++;
        return false;
    }
    *out_frame = (comp_v22_everyday_bridge_frame_t){
        .step_index = session->next_step_index,
        .cue = frame->cue,
        .score_phase = step->phase,
        .post_refresh_hold_ms = (uint16_t)hold_ms,
    };
    session->frame_outstanding = true;
    session->submitted_frames++;
    return true;
}

bool comp_v22_everyday_bridge_session_complete_frame(
    comp_v22_everyday_bridge_session_t *session,
    bool visible)
{
    if (session == NULL || !session->active || !session->frame_outstanding) {
        if (session != NULL) {
            session->rejected_submissions++;
        }
        return false;
    }
    session->frame_outstanding = false;
    if (!visible) {
        session->failed_frame_retries++;
        return true;
    }
    session->visible_frames++;
    session->next_step_index++;
    if (session->next_step_index >= session->selection.bridge->frame_count) {
        session->active = false;
    }
    return true;
}

bool comp_v22_everyday_bridge_session_cancel(comp_v22_everyday_bridge_session_t *session)
{
    if (session == NULL || !session->active) {
        if (session != NULL) {
            session->rejected_submissions++;
        }
        return false;
    }
    session->active = false;
    session->frame_outstanding = false;
    return true;
}
