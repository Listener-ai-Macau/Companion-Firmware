#include "expression_interaction_session.h"

#include <string.h>

#define COMP_EXPRESSION_RIG_INTERACTION_MIN_POST_REFRESH_HOLD_MS 750u

static bool profile_is_valid(const comp_expression_rig_profile_t *profile)
{
    return profile != NULL && profile->components != NULL && profile->component_count > 0u;
}

static bool input_is_valid(const comp_expression_rig_choreography_input_t *input)
{
    return input != NULL && input->event < COMP_EXPRESSION_RIG_EVENT_COUNT &&
           input->attention < COMP_EXPRESSION_RIG_ATTENTION_COUNT &&
           input->energy < COMP_EXPRESSION_RIG_ENERGY_COUNT &&
           input->interaction_memory <= 2u && input->phase < COMP_EXPRESSION_RIG_PHASE_COUNT;
}

static comp_expression_rig_behavior_state_t initial_behavior(void)
{
    return (comp_expression_rig_behavior_state_t){
        .affect = {
            .valence = 0,
            .arousal = 1u,
            .affinity = 0u,
            .baseline = COMP_EXPRESSION_RIG_EMOTION_CALM,
        },
        .active_intent = COMP_EXPRESSION_RIG_INTENT_PRESENCE,
        .remaining_hold_steps = 0u,
    };
}

static bool append_frame(comp_expression_rig_interaction_sequence_t *sequence,
                         comp_expression_rig_interaction_frame_kind_t kind,
                         uint8_t route_index,
                         const comp_expression_rig_state_t *state,
                         const comp_expression_rig_performance_score_t *performance_score,
                         uint8_t score_step_index,
                         comp_expression_rig_score_phase_t score_phase,
                         uint16_t post_refresh_hold_ms)
{
    if (sequence == NULL || state == NULL ||
        sequence->frame_count >= COMP_EXPRESSION_RIG_INTERACTION_MAX_FRAMES) {
        return false;
    }
    sequence->frames[sequence->frame_count++] = (comp_expression_rig_interaction_frame_t){
        .kind = kind,
        .route_index = route_index,
        .score_step_index = score_step_index,
        .score_phase = score_phase,
        .post_refresh_hold_ms = post_refresh_hold_ms,
        .performance_score = performance_score,
        .state = *state,
    };
    return true;
}

static comp_expression_rig_state_t daily_bridge_state(
    comp_expression_rig_emotion_t emotion,
    const comp_expression_rig_choreography_input_t *input,
    uint8_t interaction_memory,
    comp_expression_rig_phase_t phase)
{
    return (comp_expression_rig_state_t){
        .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
        .emotion = emotion,
        .attention = input->attention,
        .energy = input->energy,
        .interaction_memory = interaction_memory,
        .phase = phase,
    };
}

static bool score_step_is_visible_key(const comp_expression_rig_performance_score_t *score,
                                      uint8_t step_index)
{
    const comp_expression_rig_score_phase_t phase = score->steps[step_index].phase;
    const bool is_last_of_phase = step_index + 1u >= score->step_count ||
        score->steps[step_index + 1u].phase != phase;

    return step_index == 0u || phase == COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE ||
           (phase == COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD && is_last_of_phase) ||
           (phase == COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT && is_last_of_phase) ||
           (phase == COMP_EXPRESSION_RIG_SCORE_PHASE_RELEASE && is_last_of_phase);
}

static bool score_step_hold_ms(const comp_expression_rig_performance_score_t *score,
                               uint8_t step_index,
                               uint16_t *out_hold_ms)
{
    uint32_t hold_ms;
    const comp_expression_rig_score_step_t *step;

    if (score == NULL || score->steps == NULL || out_hold_ms == NULL ||
        step_index >= score->step_count) {
        return false;
    }
    step = &score->steps[step_index];
    hold_ms = step->duration_ms;
    /* The score's hold is an intentional dwell of its preceding accent pose,
     * not another identical e-paper submission. */
    if (step->phase == COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT &&
        step_index + 1u < score->step_count &&
        score->steps[step_index + 1u].phase == COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD) {
        hold_ms += score->steps[step_index + 1u].duration_ms;
    }
    if (hold_ms < COMP_EXPRESSION_RIG_INTERACTION_MIN_POST_REFRESH_HOLD_MS) {
        hold_ms = COMP_EXPRESSION_RIG_INTERACTION_MIN_POST_REFRESH_HOLD_MS;
    }
    if (hold_ms > 5000u) {
        return false;
    }
    *out_hold_ms = (uint16_t)hold_ms;
    return true;
}

static bool append_notice_score(comp_expression_rig_interaction_sequence_t *sequence,
                                const comp_expression_rig_choreography_input_t *input,
                                const comp_expression_rig_behavior_decision_t *decision,
                                const comp_expression_rig_performance_score_t *score)
{
    comp_expression_rig_state_t entry;
    uint8_t step_index;
    uint8_t emitted = 0u;

    if (sequence == NULL || input == NULL || decision == NULL || score == NULL ||
        score->steps == NULL || score->step_count == 0u) {
        return false;
    }
    entry = daily_bridge_state(decision->route.emotions[0], input, 0u,
                               COMP_EXPRESSION_RIG_PHASE_ENTRY);
    for (step_index = 0u; step_index < score->step_count; ++step_index) {
        uint16_t hold_ms;
        const comp_expression_rig_score_step_t *step = &score->steps[step_index];

        if (step->phase >= COMP_EXPRESSION_RIG_SCORE_PHASE_COUNT ||
            step->duration_ms < 80u || !score_step_is_visible_key(score, step_index)) {
            continue;
        }
        if (!score_step_hold_ms(score, step_index, &hold_ms) ||
            !append_frame(sequence, COMP_EXPRESSION_RIG_INTERACTION_FRAME_PERFORMANCE, 0u,
                          &entry, score, step_index, step->phase, hold_ms)) {
            return false;
        }
        emitted++;
    }
    return emitted == COMP_EXPRESSION_RIG_INTERACTION_MAX_SCORE_KEYFRAMES;
}

void comp_expression_rig_interaction_session_init(
    comp_expression_rig_interaction_session_t *session)
{
    if (session == NULL) {
        return;
    }
    memset(session, 0, sizeof(*session));
    session->behavior = initial_behavior();
}

bool comp_expression_rig_interaction_session_start(
    comp_expression_rig_interaction_session_t *session,
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_choreography_input_t *input)
{
    return comp_expression_rig_interaction_session_start_with_notice_score(session, profile, input,
                                                                            NULL);
}

bool comp_expression_rig_interaction_session_start_with_notice_score(
    comp_expression_rig_interaction_session_t *session,
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_choreography_input_t *input,
    const comp_expression_rig_performance_score_t *notice_score)
{
    comp_expression_rig_behavior_state_t next_behavior;
    comp_expression_rig_behavior_decision_t decision;
    comp_expression_rig_choreography_input_t target_input;
    comp_expression_rig_state_t entry;
    comp_expression_rig_state_t target;
    comp_expression_rig_state_t settle;
    comp_expression_rig_interaction_sequence_t next_sequence;
    uint8_t route_index;

    if (session == NULL || !profile_is_valid(profile) || !input_is_valid(input) ||
        session->active || session->frame_outstanding ||
        !comp_expression_rig_behavior_state_is_valid(&session->behavior) ||
        !comp_expression_rig_resolve_behavior(&session->behavior, input, &next_behavior, &decision) ||
        decision.route.count == 0u ||
        decision.route.count > COMP_EXPRESSION_RIG_MAX_EMOTION_ROUTE) {
        if (session != NULL) {
            session->rejected_submissions++;
        }
        return false;
    }

    target_input = *input;
    target_input.phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN;
    target_input.has_requested_emotion = true;
    target_input.requested_emotion = decision.target_emotion;
    if (!comp_expression_rig_choreograph(profile, &target_input, &target) ||
        !comp_expression_rig_story_state(&target, COMP_EXPRESSION_RIG_PHASE_SETTLE, &settle)) {
        session->rejected_submissions++;
        return false;
    }

    memset(&next_sequence, 0, sizeof(next_sequence));
    next_sequence.decision = decision;
    if (notice_score != NULL && !append_notice_score(&next_sequence, input, &decision, notice_score)) {
        session->rejected_submissions++;
        return false;
    }
    entry = daily_bridge_state(decision.route.emotions[0], input, 0u,
                               COMP_EXPRESSION_RIG_PHASE_ENTRY);
    if (notice_score == NULL &&
        !append_frame(&next_sequence, COMP_EXPRESSION_RIG_INTERACTION_FRAME_ENTRY, 0u, &entry,
                      NULL, COMP_EXPRESSION_RIG_INTERACTION_NO_SCORE_STEP,
                      COMP_EXPRESSION_RIG_SCORE_PHASE_COUNT,
                      COMP_EXPRESSION_RIG_INTERACTION_MIN_POST_REFRESH_HOLD_MS)) {
        session->rejected_submissions++;
        return false;
    }
    for (route_index = 1u; route_index + 1u < decision.route.count; ++route_index) {
        const uint8_t bridge_memory = route_index > input->interaction_memory
                                          ? input->interaction_memory
                                          : route_index;
        const comp_expression_rig_state_t bridge = daily_bridge_state(
            decision.route.emotions[route_index], input, bridge_memory,
            COMP_EXPRESSION_RIG_PHASE_SUSTAIN);

        if (!append_frame(&next_sequence, COMP_EXPRESSION_RIG_INTERACTION_FRAME_BRIDGE,
                          route_index, &bridge, NULL,
                          COMP_EXPRESSION_RIG_INTERACTION_NO_SCORE_STEP,
                          COMP_EXPRESSION_RIG_SCORE_PHASE_COUNT,
                          COMP_EXPRESSION_RIG_INTERACTION_MIN_POST_REFRESH_HOLD_MS)) {
            session->rejected_submissions++;
            return false;
        }
    }
    if (!append_frame(&next_sequence, COMP_EXPRESSION_RIG_INTERACTION_FRAME_TARGET,
                      (uint8_t)(decision.route.count - 1u), &target, NULL,
                      COMP_EXPRESSION_RIG_INTERACTION_NO_SCORE_STEP,
                      COMP_EXPRESSION_RIG_SCORE_PHASE_COUNT,
                      COMP_EXPRESSION_RIG_INTERACTION_MIN_POST_REFRESH_HOLD_MS) ||
        !append_frame(&next_sequence, COMP_EXPRESSION_RIG_INTERACTION_FRAME_SETTLE,
                      (uint8_t)(decision.route.count - 1u), &settle, NULL,
                      COMP_EXPRESSION_RIG_INTERACTION_NO_SCORE_STEP,
                      COMP_EXPRESSION_RIG_SCORE_PHASE_COUNT,
                      COMP_EXPRESSION_RIG_INTERACTION_MIN_POST_REFRESH_HOLD_MS)) {
        session->rejected_submissions++;
        return false;
    }

    session->behavior = next_behavior;
    session->sequence = next_sequence;
    session->next_frame_index = 0u;
    session->active = true;
    session->frame_outstanding = false;
    return true;
}

bool comp_expression_rig_interaction_session_take_frame(
    comp_expression_rig_interaction_session_t *session,
    const comp_expression_rig_profile_t *profile,
    comp_expression_rig_interaction_frame_t *out_frame,
    comp_expression_rig_plan_t *out_plan)
{
    const comp_expression_rig_interaction_frame_t *frame;

    if (session == NULL || !profile_is_valid(profile) || out_frame == NULL || out_plan == NULL ||
        !session->active || session->frame_outstanding ||
        session->next_frame_index >= session->sequence.frame_count) {
        if (session != NULL) {
            session->rejected_submissions++;
        }
        return false;
    }
    frame = &session->sequence.frames[session->next_frame_index];
    if ((frame->performance_score != NULL &&
         (!comp_expression_rig_build_plan(profile, &frame->state, out_plan) ||
          !comp_expression_rig_apply_score_step(profile, out_plan, frame->performance_score,
                                                 frame->score_step_index, out_plan))) ||
        (frame->performance_score == NULL &&
         !comp_expression_rig_build_plan(profile, &frame->state, out_plan))) {
        session->rejected_submissions++;
        return false;
    }
    *out_frame = *frame;
    session->frame_outstanding = true;
    session->submitted_frames++;
    return true;
}

bool comp_expression_rig_interaction_session_complete_frame(
    comp_expression_rig_interaction_session_t *session,
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
    session->next_frame_index++;
    if (session->next_frame_index >= session->sequence.frame_count) {
        session->active = false;
    }
    return true;
}

const char *comp_expression_rig_interaction_frame_kind_name(
    comp_expression_rig_interaction_frame_kind_t kind)
{
    switch (kind) {
    case COMP_EXPRESSION_RIG_INTERACTION_FRAME_PERFORMANCE: return "performance";
    case COMP_EXPRESSION_RIG_INTERACTION_FRAME_ENTRY: return "entry";
    case COMP_EXPRESSION_RIG_INTERACTION_FRAME_BRIDGE: return "bridge";
    case COMP_EXPRESSION_RIG_INTERACTION_FRAME_TARGET: return "target";
    case COMP_EXPRESSION_RIG_INTERACTION_FRAME_SETTLE: return "settle";
    default: return "invalid";
    }
}
