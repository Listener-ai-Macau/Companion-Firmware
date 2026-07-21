#include "expression_choreographer.h"
#include "expression_v22_everyday_bridge_router.h"
#include "expression_v22_everyday_bridge_session.h"

#include <stdio.h>
#include <string.h>

typedef struct {
    comp_expression_rig_emotion_t source;
    comp_v22_everyday_cue_t cue;
    comp_expression_rig_emotion_t target;
    const char *name;
} expected_edge_t;

static const expected_edge_t k_expected_edges[] = {
    {COMP_EXPRESSION_RIG_EMOTION_CALM, COMP_V22_EVERYDAY_CUE_ATTENTION_NOVELTY,
     COMP_EXPRESSION_RIG_EMOTION_CURIOUS, "calm__curious"},
    {COMP_EXPRESSION_RIG_EMOTION_CURIOUS, COMP_V22_EVERYDAY_CUE_NOVELTY_RESOLVED,
     COMP_EXPRESSION_RIG_EMOTION_CALM, "curious__calm"},
    {COMP_EXPRESSION_RIG_EMOTION_CURIOUS, COMP_V22_EVERYDAY_CUE_POSITIVE_RECIPROCITY,
     COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, "curious__warm"},
    {COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, COMP_V22_EVERYDAY_CUE_ATTENTION_SHIFT,
     COMP_EXPRESSION_RIG_EMOTION_CURIOUS, "warm__curious"},
    {COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, COMP_V22_EVERYDAY_CUE_SHARED_PLAY,
     COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, "warm__playful"},
    {COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, COMP_V22_EVERYDAY_CUE_ENERGY_SETTLE,
     COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, "playful__warm"},
    {COMP_EXPRESSION_RIG_EMOTION_CALM, COMP_V22_EVERYDAY_CUE_AMBIGUOUS_INPUT,
     COMP_EXPRESSION_RIG_EMOTION_PUZZLED, "calm__puzzled"},
    {COMP_EXPRESSION_RIG_EMOTION_PUZZLED, COMP_V22_EVERYDAY_CUE_AMBIGUITY_RESOLVED,
     COMP_EXPRESSION_RIG_EMOTION_CALM, "puzzled__calm"},
    {COMP_EXPRESSION_RIG_EMOTION_PUZZLED, COMP_V22_EVERYDAY_CUE_HIGH_SALIENCE,
     COMP_EXPRESSION_RIG_EMOTION_ALERT, "puzzled__alert"},
    {COMP_EXPRESSION_RIG_EMOTION_ALERT, COMP_V22_EVERYDAY_CUE_SALIENCE_REDUCED,
     COMP_EXPRESSION_RIG_EMOTION_PUZZLED, "alert__puzzled"},
};

static int require_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

static int write_report(const char *path, uint16_t total_steps, uint16_t session_steps)
{
    FILE *file = NULL;
    size_t index;

    if (path == NULL) {
        return 0;
    }
    if (fopen_s(&file, path, "wb") != 0 || file == NULL) {
        fprintf(stderr, "FAIL: could not write %s\n", path);
        return 1;
    }
    fprintf(file,
            "{\n"
            "  \"schema\": \"companion.v22_everyday_bridge_router_host.v1\",\n"
            "  \"status\": \"PASS_V22_EVERYDAY_BRIDGE_ROUTER_RUNTIME_INACTIVE\",\n"
            "  \"runtime_resource_activated\": false,\n"
            "  \"candidate_runtime_activation_allowed\": false,\n"
            "  \"ordinary_affect_only\": true,\n"
            "  \"bridge_count\": %u,\n"
            "  \"replayed_step_count\": %u,\n"
            "  \"session_visible_step_count\": %u,\n"
            "  \"session_requires_visible_acknowledgement\": true,\n"
            "  \"session_min_post_refresh_hold_ms\": %u,\n"
            "  \"unbound_product_states\": [\"menu\", \"recording\", \"upgrade\", \"sleep\", \"charging\", \"error\"],\n"
            "  \"edges\": [\n",
            (unsigned)(sizeof(k_expected_edges) / sizeof(k_expected_edges[0])),
            (unsigned)total_steps, (unsigned)session_steps,
            (unsigned)COMP_V22_EVERYDAY_BRIDGE_MIN_POST_REFRESH_HOLD_MS);
    for (index = 0u; index < sizeof(k_expected_edges) / sizeof(k_expected_edges[0]); ++index) {
        const expected_edge_t *expected = &k_expected_edges[index];
        fprintf(file,
                "    {\"cue\": \"%s\", \"source_emotion\": %u, \"target_emotion\": %u, \"bridge\": \"%s\"}%s\n",
                comp_v22_everyday_cue_name(expected->cue), (unsigned)expected->source,
                (unsigned)expected->target, expected->name,
                index + 1u == sizeof(k_expected_edges) / sizeof(k_expected_edges[0]) ? "" : ",");
    }
    fprintf(file,
            "  ],\n"
            "  \"forbidden\": [\"whole-face card playback\", \"code-drawn face\", \"legacy art\", \"runtime binding\"]\n"
            "}\n");
    fclose(file);
    return 0;
}

int main(int argc, char **argv)
{
    const comp_expression_rig_profile_t *profile =
        comp_v22_emotion_separation_rig_candidate_profile();
    const comp_expression_rig_event_t special_events[] = {
        COMP_EXPRESSION_RIG_EVENT_MENU_HOLD,
        COMP_EXPRESSION_RIG_EVENT_RECORDING_ACTIVE,
        COMP_EXPRESSION_RIG_EVENT_UPGRADE_ACTIVE,
        COMP_EXPRESSION_RIG_EVENT_SLEEP,
        COMP_EXPRESSION_RIG_EVENT_CHARGING,
        COMP_EXPRESSION_RIG_EVENT_ERROR,
    };
    uint16_t total_steps = 0u;
    uint16_t session_steps = 0u;
    size_t edge_index;

    if (require_true(profile != NULL &&
                     !comp_v22_emotion_separation_rig_candidate_runtime_activation_allowed() &&
                     comp_v22_emotion_separation_rig_candidate_bridge_count() ==
                         sizeof(k_expected_edges) / sizeof(k_expected_edges[0]),
                     "V22 candidate identity or bridge count drifted")) {
        return 1;
    }
    if (require_true(!comp_v22_everyday_bridge_select(
                         COMP_EXPRESSION_RIG_EMOTION_CALM,
                         COMP_V22_EVERYDAY_CUE_POSITIVE_RECIPROCITY, NULL) &&
                     !comp_v22_everyday_bridge_select(
                         COMP_EXPRESSION_RIG_EMOTION_THINKING,
                         COMP_V22_EVERYDAY_CUE_ATTENTION_NOVELTY,
                         &(comp_v22_everyday_bridge_selection_t){0}) &&
                     strcmp(comp_v22_everyday_cue_name(COMP_V22_EVERYDAY_CUE_COUNT), "invalid") == 0,
                     "router must reject unsupported source/cue pairs")) {
        return 1;
    }

    for (edge_index = 0u; edge_index < sizeof(k_expected_edges) / sizeof(k_expected_edges[0]); ++edge_index) {
        const expected_edge_t *expected = &k_expected_edges[edge_index];
        comp_v22_everyday_bridge_selection_t selection;
        uint8_t step_index;

        if (require_true(comp_v22_everyday_bridge_select(expected->source, expected->cue, &selection) &&
                         selection.source_emotion == expected->source &&
                         selection.target_emotion == expected->target && selection.bridge != NULL &&
                         strcmp(selection.bridge->name, expected->name) == 0 &&
                         selection.bridge->score != NULL && selection.bridge->frames != NULL &&
                         selection.bridge->score->step_count == selection.bridge->frame_count,
                         "router did not resolve its exact registered V22 edge")) {
            return 1;
        }
        for (step_index = 0u; step_index < selection.bridge->frame_count; ++step_index) {
            comp_expression_rig_plan_t plan;
            const comp_expression_rig_registered_score_step_t *score_step =
                &selection.bridge->score->steps[step_index];

            if (require_true(comp_v22_everyday_bridge_build_step(&selection, step_index, NULL, &plan) &&
                             plan.layer_count > 0u &&
                             plan.effective_state.scene == COMP_EXPRESSION_RIG_SCENE_DAILY &&
                             plan.effective_state.attention == COMP_EXPRESSION_RIG_ATTENTION_CENTER &&
                             plan.effective_state.phase == COMP_EXPRESSION_RIG_PHASE_SUSTAIN &&
                             plan.effective_state.emotion == score_step->state.emotion &&
                             plan.effective_state.energy == score_step->state.energy &&
                             plan.effective_state.interaction_memory == score_step->state.interaction_memory,
                             "router step must replay its registered source-component score context")) {
                return 1;
            }
            total_steps++;
        }
        if (require_true(!comp_v22_everyday_bridge_build_step(
                             &selection, selection.bridge->frame_count, NULL,
                             &(comp_expression_rig_plan_t){0}),
                         "router must reject an unregistered bridge step")) {
            return 1;
        }
    }

    for (edge_index = 0u; edge_index < sizeof(k_expected_edges) / sizeof(k_expected_edges[0]); ++edge_index) {
        const expected_edge_t *expected = &k_expected_edges[edge_index];
        const comp_v22_everyday_bridge_context_t context = {
            .energy = COMP_EXPRESSION_RIG_ENERGY_HIGH,
            .interaction_memory = 2u,
        };
        comp_v22_everyday_bridge_session_t session;
        uint8_t step_index;

        comp_v22_everyday_bridge_session_init(&session);
        if (require_true(comp_v22_everyday_bridge_session_start(
                             &session, expected->source, expected->cue, &context) &&
                         !comp_v22_everyday_bridge_session_start(
                             &session, expected->source, expected->cue, &context),
                         "everyday bridge session must reject a second start while active")) {
            return 1;
        }
        for (step_index = 0u; step_index < session.selection.bridge->frame_count; ++step_index) {
            comp_v22_everyday_bridge_frame_t frame;
            comp_expression_rig_plan_t plan;

            if (require_true(comp_v22_everyday_bridge_session_take_frame(&session, &frame, &plan) &&
                             frame.step_index == step_index && frame.cue != NULL &&
                             frame.post_refresh_hold_ms >=
                                 COMP_V22_EVERYDAY_BRIDGE_MIN_POST_REFRESH_HOLD_MS &&
                             plan.input_state.energy == context.energy &&
                             plan.input_state.interaction_memory == context.interaction_memory &&
                             !comp_v22_everyday_bridge_session_take_frame(
                                 &session, &frame, &plan),
                             "everyday bridge session must wait for the current frame acknowledgement")) {
                return 1;
            }
            if (step_index == 0u) {
                comp_v22_everyday_bridge_frame_t retry_frame;
                comp_expression_rig_plan_t retry_plan;

                if (require_true(comp_v22_everyday_bridge_session_complete_frame(&session, false) &&
                                 comp_v22_everyday_bridge_session_take_frame(
                                     &session, &retry_frame, &retry_plan) &&
                                 retry_frame.step_index == frame.step_index &&
                                 retry_frame.post_refresh_hold_ms == frame.post_refresh_hold_ms &&
                                 memcmp(&retry_plan, &plan, sizeof(plan)) == 0 &&
                                 comp_v22_everyday_bridge_session_complete_frame(&session, true),
                                 "a nonvisible frame must retry the exact same registered plan")) {
                    return 1;
                }
            } else if (require_true(comp_v22_everyday_bridge_session_complete_frame(&session, true),
                                    "a visible frame must advance the everyday bridge session")) {
                return 1;
            }
            session_steps++;
        }
        if (require_true(!session.active && !session.frame_outstanding &&
                         session.visible_frames == session.selection.bridge->frame_count &&
                         session.failed_frame_retries == 1u &&
                         session.selection.target_emotion == expected->target,
                         "everyday bridge session must settle only at its declared causal target")) {
            return 1;
        }
    }
    {
        comp_v22_everyday_bridge_session_t session;

        comp_v22_everyday_bridge_session_init(&session);
        if (require_true(comp_v22_everyday_bridge_session_start(
                             &session, COMP_EXPRESSION_RIG_EMOTION_CALM,
                             COMP_V22_EVERYDAY_CUE_ATTENTION_NOVELTY, NULL) &&
                         comp_v22_everyday_bridge_session_cancel(&session) && !session.active &&
                         !comp_v22_everyday_bridge_session_take_frame(
                             &session, &(comp_v22_everyday_bridge_frame_t){0},
                             &(comp_expression_rig_plan_t){0}),
                         "cancellation must stop without synthesizing a replacement face")) {
            return 1;
        }
    }

    for (edge_index = 0u; edge_index < sizeof(special_events) / sizeof(special_events[0]); ++edge_index) {
        comp_expression_rig_choreography_input_t input = {
            .event = special_events[edge_index],
            .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
            .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL,
            .interaction_memory = 0u,
            .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN,
        };

        if (require_true(!comp_expression_rig_choreograph_plan(
                             profile, &input, &(comp_expression_rig_plan_t){0}),
                         "unbound product states must not borrow an everyday V22 bridge")) {
            return 1;
        }
    }
    if (require_true(total_steps == 72u && session_steps == 72u,
                     "V22 router must replay every accepted bridge step exactly once")) {
        return 1;
    }
    if (write_report(argc == 2 ? argv[1] : NULL, total_steps, session_steps) != 0) {
        return 1;
    }
    puts("PASS: V22 everyday router deterministically selects all accepted component bridges while product states stay fail-closed");
    return 0;
}
