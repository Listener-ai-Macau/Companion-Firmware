#include "expression_choreographer.h"
#include "generated/expression_rig_v9_candidate_profile.h"

#include <stdio.h>
#include <string.h>

static int require_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

static const comp_expression_rig_layer_t *find_layer(const comp_expression_rig_plan_t *plan,
                                                      uint16_t component_id)
{
    uint8_t index;

    for (index = 0u; index < plan->layer_count; ++index) {
        if (plan->layers[index].component_id == component_id) {
            return &plan->layers[index];
        }
    }
    return NULL;
}

static int write_json(const char *path,
                      const comp_expression_rig_state_t *daily,
                      const comp_expression_rig_state_t *memory,
                      const comp_expression_rig_state_t *swipe_left,
                      const comp_expression_rig_state_t *swipe_right,
                      const comp_expression_rig_behavior_decision_t *decision)
{
    FILE *file = NULL;

    if (path == NULL) {
        return 0;
    }
    if (fopen_s(&file, path, "wb") != 0 || file == NULL) {
        fprintf(stderr, "FAIL: could not write %s\n", path);
        return 1;
    }
    fprintf(file,
            "{\n"
            "  \"schema\": \"companion.v9_expression_choreographer_host.v1\",\n"
            "  \"status\": \"PASS\",\n"
            "  \"source_sha256\": \"%s\",\n"
            "  \"runtime_resource_activated\": false,\n"
            "  \"daily_replay\": {\"scene\": %u, \"emotion\": %u, \"attention\": %u, \"energy\": %u, \"memory\": %u},\n"
            "  \"memory_variant\": {\"scene\": %u, \"emotion\": %u, \"attention\": %u, \"energy\": %u, \"memory\": %u},\n"
            "  \"swipe_left\": {\"scene\": %u, \"emotion\": %u, \"attention\": %u, \"energy\": %u, \"memory\": %u},\n"
            "  \"swipe_right\": {\"scene\": %u, \"emotion\": %u, \"attention\": %u, \"energy\": %u, \"memory\": %u},\n"
            "  \"behavior_arbitration\": {\"intent\": \"%s\", \"reason\": \"%s\", \"target_emotion\": %u, \"target_attention\": %u, \"event_priority\": %u, \"cancels_active_intent\": %s, \"route_count\": %u},\n"
            "  \"fail_closed_events\": [\"charging\", \"error\", \"menu_hold\", \"recording_active\", \"upgrade_active\"],\n"
            "  \"forbidden_runtime_paths\": [\"whole-face card loop\", \"code-drawn face\", \"custom LUT\"]\n"
            "}\n",
            COMP_V9_EXPRESSION_RIG_CANDIDATE_SOURCE_SHA256,
            (unsigned)daily->scene,
            (unsigned)daily->emotion,
            (unsigned)daily->attention,
            (unsigned)daily->energy,
            (unsigned)daily->interaction_memory,
            (unsigned)memory->scene,
            (unsigned)memory->emotion,
            (unsigned)memory->attention,
            (unsigned)memory->energy,
            (unsigned)memory->interaction_memory,
            (unsigned)swipe_left->scene,
            (unsigned)swipe_left->emotion,
            (unsigned)swipe_left->attention,
            (unsigned)swipe_left->energy,
            (unsigned)swipe_left->interaction_memory,
            (unsigned)swipe_right->scene,
            (unsigned)swipe_right->emotion,
            (unsigned)swipe_right->attention,
            (unsigned)swipe_right->energy,
            (unsigned)swipe_right->interaction_memory,
            comp_expression_rig_intent_name(decision->intent),
            comp_expression_rig_intent_reason_name(decision->reason),
            (unsigned)decision->target_emotion,
            (unsigned)decision->target_attention,
            (unsigned)decision->event_priority,
            decision->cancels_active_intent ? "true" : "false",
            (unsigned)decision->route.count);
    fclose(file);
    return 0;
}

int main(int argc, char **argv)
{
    const comp_expression_rig_profile_t *profile =
        comp_v9_expression_rig_candidate_profile();
    comp_expression_rig_choreography_input_t input = {
        .event = COMP_EXPRESSION_RIG_EVENT_DAILY_AUTO,
        .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
        .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL,
        .interaction_memory = 1u,
        .seed = 0x12345678u,
        .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN,
    };
    comp_expression_rig_choreography_input_t repeat = input;
    comp_expression_rig_choreography_input_t memory_variant = input;
    comp_expression_rig_choreography_input_t swipe = input;
    comp_expression_rig_choreography_input_t charging = input;
    comp_expression_rig_choreography_input_t error = input;
    comp_expression_rig_choreography_input_t menu = input;
    comp_expression_rig_choreography_input_t recording = input;
    comp_expression_rig_choreography_input_t upgrade = input;
    comp_expression_rig_state_t daily_a;
    comp_expression_rig_state_t daily_b;
    comp_expression_rig_state_t memory_state;
    comp_expression_rig_state_t swipe_left_state;
    comp_expression_rig_state_t swipe_right_state;
    comp_expression_rig_state_t entry_state;
    comp_expression_rig_state_t sustain_state;
    comp_expression_rig_state_t settle_state;
    comp_expression_rig_plan_t left_plan;
    comp_expression_rig_plan_t right_plan;
    comp_expression_rig_plan_t low_plan;
    comp_expression_rig_plan_t high_plan;
    comp_expression_rig_plan_t score_plan;
    const comp_expression_rig_performance_score_t *right_score;
    const comp_expression_rig_layer_t *left_eye;
    const comp_expression_rig_layer_t *right_eye;
    comp_expression_rig_behavior_decision_t behavior_decision;

    if (require_true(comp_expression_rig_choreograph(profile, &input, &daily_a) &&
                         comp_expression_rig_choreograph(profile, &repeat, &daily_b) &&
                         memcmp(&daily_a, &daily_b, sizeof(daily_a)) == 0,
                     "same state/input/seed replays identically")) {
        return 1;
    }

    input.attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT;
    right_score = comp_v9_expression_rig_candidate_daily_score(input.attention);
    if (require_true(right_score != NULL &&
                         comp_expression_rig_choreograph_daily_score_plan(profile, &input, right_score,
                                                                           5u, &score_plan) &&
                         find_layer(&score_plan, 5u) != NULL &&
                         find_layer(&score_plan, 5u)->offset_x == 0 &&
                         find_layer(&score_plan, 6u) != NULL &&
                         find_layer(&score_plan, 6u)->offset_x == 0 &&
                          find_layer(&score_plan, 7u) != NULL &&
                          find_layer(&score_plan, 7u)->offset_x == 0 &&
                          find_layer(&score_plan, 8u) != NULL &&
                          find_layer(&score_plan, 8u)->offset_x == 1 &&
                          find_layer(&score_plan, 9u) != NULL &&
                          find_layer(&score_plan, 9u)->offset_x == 0 &&
                          find_layer(&score_plan, 10u) != NULL &&
                          find_layer(&score_plan, 10u)->offset_x == 1,
                      "daily rightward lead moves only registered right-eye gloss while fixed V9 eye bodies stay still")) {
        return 1;
    }
    input.event = COMP_EXPRESSION_RIG_EVENT_TOUCH_TAP;
    if (require_true(!comp_expression_rig_choreograph_daily_score_plan(profile, &input, right_score,
                                                                        2u, &score_plan),
                     "non-daily events fail closed instead of borrowing the Daily score")) {
        return 1;
    }
    input.event = COMP_EXPRESSION_RIG_EVENT_DAILY_AUTO;

    memory_variant.interaction_memory = 2u;
    if (require_true(comp_expression_rig_choreograph(profile, &memory_variant,
                                                     &memory_state) &&
                         memory_state.emotion == COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE &&
                         memcmp(&daily_a, &memory_state, sizeof(daily_a)) != 0,
                     "interaction memory changes the selected legal performance")) {
        return 1;
    }

    swipe.event = COMP_EXPRESSION_RIG_EVENT_TOUCH_SWIPE;
    swipe.attention = COMP_EXPRESSION_RIG_ATTENTION_LEFT;
    swipe.energy = COMP_EXPRESSION_RIG_ENERGY_HIGH;
    if (require_true(comp_expression_rig_choreograph_plan(profile, &swipe, &left_plan) &&
                         comp_expression_rig_choreograph(profile, &swipe,
                                                         &swipe_left_state),
                     "left swipe builds a source-derived Rig plan")) {
        return 1;
    }
    swipe.attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT;
    if (require_true(comp_expression_rig_choreograph_plan(profile, &swipe, &right_plan) &&
                         comp_expression_rig_choreograph(profile, &swipe,
                                                         &swipe_right_state),
                     "right swipe builds a source-derived Rig plan")) {
        return 1;
    }
    left_eye = find_layer(&left_plan, 5u);
    right_eye = find_layer(&right_plan, 5u);
    if (require_true(left_eye != NULL && right_eye != NULL &&
                         left_eye->offset_x < right_eye->offset_x,
                     "touch direction changes eye component offsets, not a whole-face card")) {
        return 1;
    }

    input.event = COMP_EXPRESSION_RIG_EVENT_TOUCH_TAP;
    input.phase = COMP_EXPRESSION_RIG_PHASE_ENTRY;
    if (require_true(comp_expression_rig_choreograph(profile, &input, &entry_state) &&
                         entry_state.scene == COMP_EXPRESSION_RIG_SCENE_DAILY &&
                         entry_state.attention == COMP_EXPRESSION_RIG_ATTENTION_CENTER,
                     "entry returns to the calm v9 baseline state")) {
        return 1;
    }
    input.phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN;
    if (require_true(comp_expression_rig_choreograph(profile, &input, &sustain_state) &&
                         sustain_state.scene == COMP_EXPRESSION_RIG_SCENE_DAILY &&
                         sustain_state.emotion == COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
                     "touch sustain keeps the real causal event while using the approved Daily visual grammar")) {
        return 1;
    }
    input.phase = COMP_EXPRESSION_RIG_PHASE_SETTLE;
    if (require_true(comp_expression_rig_choreograph(profile, &input, &settle_state) &&
                         settle_state.scene == entry_state.scene &&
                         settle_state.emotion == entry_state.emotion &&
                         settle_state.attention == entry_state.attention &&
                         settle_state.energy == entry_state.energy &&
                         settle_state.interaction_memory ==
                             entry_state.interaction_memory &&
                         settle_state.phase == COMP_EXPRESSION_RIG_PHASE_SETTLE,
                     "settle objectively returns to the entry baseline")) {
        return 1;
    }

    input.phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN;
    input.attention = COMP_EXPRESSION_RIG_ATTENTION_LEFT;
    input.energy = COMP_EXPRESSION_RIG_ENERGY_LOW;
    if (require_true(comp_expression_rig_choreograph_plan(profile, &input, &low_plan),
                     "low energy event builds")) {
        return 1;
    }
    input.energy = COMP_EXPRESSION_RIG_ENERGY_HIGH;
    if (require_true(comp_expression_rig_choreograph_plan(profile, &input, &high_plan) &&
                         memcmp(&low_plan, &high_plan, sizeof(low_plan)) != 0,
                     "energy changes legal component offsets")) {
        return 1;
    }

    charging.event = COMP_EXPRESSION_RIG_EVENT_CHARGING;
    error.event = COMP_EXPRESSION_RIG_EVENT_ERROR;
    menu.event = COMP_EXPRESSION_RIG_EVENT_MENU_HOLD;
    recording.event = COMP_EXPRESSION_RIG_EVENT_RECORDING_ACTIVE;
    upgrade.event = COMP_EXPRESSION_RIG_EVENT_UPGRADE_ACTIVE;
    for (uint32_t phase = 0u; phase < COMP_EXPRESSION_RIG_PHASE_COUNT; ++phase) {
        charging.phase = (comp_expression_rig_phase_t)phase;
        error.phase = (comp_expression_rig_phase_t)phase;
        menu.phase = (comp_expression_rig_phase_t)phase;
        recording.phase = (comp_expression_rig_phase_t)phase;
        upgrade.phase = (comp_expression_rig_phase_t)phase;
        if (require_true(!comp_expression_rig_choreograph_plan(profile, &charging,
                                                               &left_plan) &&
                             !comp_expression_rig_choreograph_plan(profile, &error,
                                                                   &right_plan) &&
                             !comp_expression_rig_choreograph_plan(profile, &menu,
                                                                   &left_plan) &&
                             !comp_expression_rig_choreograph_plan(profile, &recording,
                                                                   &right_plan) &&
                             !comp_expression_rig_choreograph_plan(profile, &upgrade,
                                                                   &score_plan),
                         "unapproved charging/error/menu/recording/upgrade components fail closed for every phase")) {
            return 1;
        }
    }

    {
        const comp_expression_rig_affect_state_t calm_affect = {
            .valence = 0, .arousal = 1u, .affinity = 0u,
            .baseline = COMP_EXPRESSION_RIG_EMOTION_CALM,
        };
        const comp_expression_rig_affect_state_t warm_affect = {
            .valence = 1, .arousal = 1u, .affinity = 2u,
            .baseline = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
        };
        comp_expression_rig_affect_state_t first_update;
        comp_expression_rig_affect_state_t repeat_update;
        comp_expression_rig_behavior_state_t behavior_current;
        comp_expression_rig_behavior_state_t behavior_idle_a;
        comp_expression_rig_behavior_state_t behavior_idle_b;
        comp_expression_rig_behavior_state_t behavior_warm;
        comp_expression_rig_behavior_state_t behavior_hold;
        comp_expression_rig_behavior_state_t behavior_alert;
        comp_expression_rig_behavior_decision_t idle_decision_a;
        comp_expression_rig_behavior_decision_t idle_decision_b;
        comp_expression_rig_emotion_route_t route;
        comp_expression_rig_emotion_t target;
        comp_expression_rig_choreography_input_t affect_input = {
            .event = COMP_EXPRESSION_RIG_EVENT_DAILY_AUTO,
            .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
            .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL,
            .interaction_memory = 0u,
            .seed = 0xAFEC7001u,
            .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN,
        };

        if (require_true(comp_expression_rig_affect_update(&calm_affect, &affect_input, &first_update) &&
                             comp_expression_rig_affect_update(&calm_affect, &affect_input, &repeat_update) &&
                             memcmp(&first_update, &repeat_update, sizeof(first_update)) == 0 &&
                             comp_expression_rig_affect_target_emotion(&first_update, &affect_input, &target) &&
                             target == COMP_EXPRESSION_RIG_EMOTION_CALM,
                         "persistent affect updates deterministically and keeps idle on its stable baseline")) {
            return 1;
        }
        behavior_current = (comp_expression_rig_behavior_state_t){
            .affect = calm_affect,
            .active_intent = COMP_EXPRESSION_RIG_INTENT_PRESENCE,
            .remaining_hold_steps = 0u,
        };
        affect_input.event = COMP_EXPRESSION_RIG_EVENT_DAILY_AUTO;
        affect_input.seed = 0x00000001u;
        if (require_true(comp_expression_rig_resolve_behavior(&behavior_current, &affect_input,
                                                               &behavior_idle_a, &idle_decision_a),
                         "idle behavior arbitration resolves")) {
            return 1;
        }
        affect_input.seed = 0xFFFFFFFFu;
        if (require_true(comp_expression_rig_resolve_behavior(&behavior_current, &affect_input,
                                                               &behavior_idle_b, &idle_decision_b) &&
                             behavior_idle_a.affect.baseline == COMP_EXPRESSION_RIG_EMOTION_CALM &&
                             behavior_idle_b.affect.baseline == COMP_EXPRESSION_RIG_EMOTION_CALM &&
                             idle_decision_a.intent == COMP_EXPRESSION_RIG_INTENT_PRESENCE &&
                             idle_decision_b.intent == COMP_EXPRESSION_RIG_INTENT_PRESENCE &&
                             idle_decision_a.reason == COMP_EXPRESSION_RIG_INTENT_REASON_IDLE_PRESENCE &&
                             idle_decision_a.target_attention == COMP_EXPRESSION_RIG_ATTENTION_CENTER &&
                             idle_decision_a.target_emotion == idle_decision_b.target_emotion,
                         "idle keeps its selected baseline and ignores seed as an emotion source")) {
            return 1;
        }
        affect_input.event = COMP_EXPRESSION_RIG_EVENT_TOUCH_TAP;
        affect_input.interaction_memory = 2u;
        if (require_true(comp_expression_rig_affect_update(&warm_affect, &affect_input, &first_update) &&
                             comp_expression_rig_affect_target_emotion(&first_update, &affect_input, &target) &&
                             target == COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
                         "high-affinity touch resolves through a warm emotional response")) {
            return 1;
        }
        affect_input.attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT;
        if (require_true(comp_expression_rig_resolve_behavior(&behavior_idle_a, &affect_input,
                                                               &behavior_warm, &behavior_decision) &&
                             behavior_decision.intent == COMP_EXPRESSION_RIG_INTENT_WARM_RESPONSE &&
                             behavior_decision.reason == COMP_EXPRESSION_RIG_INTENT_REASON_EVENT_APPRAISAL &&
                             behavior_decision.target_emotion == COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE &&
                             behavior_decision.target_attention == COMP_EXPRESSION_RIG_ATTENTION_RIGHT &&
                             behavior_decision.route.count == 3u &&
                             behavior_warm.remaining_hold_steps == COMP_EXPRESSION_RIG_MIN_INTENT_HOLD_STEPS,
                         "a familiar touch causally selects the warm intent and its directed route")) {
            return 1;
        }
        affect_input.event = COMP_EXPRESSION_RIG_EVENT_CHARGING;
        if (require_true(comp_expression_rig_resolve_behavior(&behavior_warm, &affect_input,
                                                               &behavior_hold, &behavior_decision) &&
                             behavior_decision.reason == COMP_EXPRESSION_RIG_INTENT_REASON_ACTIVE_INTENT_HOLD &&
                             behavior_decision.intent == COMP_EXPRESSION_RIG_INTENT_WARM_RESPONSE &&
                             behavior_decision.target_emotion == COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
                         "a lower-priority context cannot interrupt an active warm bridge")) {
            return 1;
        }
        affect_input.event = COMP_EXPRESSION_RIG_EVENT_ERROR;
        if (require_true(comp_expression_rig_resolve_behavior(&behavior_hold, &affect_input,
                                                               &behavior_alert, &behavior_decision) &&
                             behavior_decision.intent == COMP_EXPRESSION_RIG_INTENT_ALERT_RESPONSE &&
                             behavior_decision.cancels_active_intent &&
                             behavior_alert.affect.baseline == COMP_EXPRESSION_RIG_EMOTION_ALERT,
                         "only a higher-priority event cancels the active intent")) {
            return 1;
        }
        affect_input.event = COMP_EXPRESSION_RIG_EVENT_TOUCH_SWIPE;
        affect_input.energy = COMP_EXPRESSION_RIG_ENERGY_HIGH;
        if (require_true(comp_expression_rig_affect_update(&warm_affect, &affect_input, &first_update) &&
                             comp_expression_rig_affect_target_emotion(&first_update, &affect_input, &target) &&
                             target == COMP_EXPRESSION_RIG_EMOTION_PLAYFUL,
                         "high-energy familiar swipe resolves through a playful response")) {
            return 1;
        }
        if (require_true(!comp_expression_rig_emotion_transition_allowed(
                             COMP_EXPRESSION_RIG_EMOTION_CALM, COMP_EXPRESSION_RIG_EMOTION_PLAYFUL) &&
                             comp_expression_rig_emotion_transition_route(
                                 COMP_EXPRESSION_RIG_EMOTION_CALM,
                                 COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, &route) &&
                             route.count == 4u &&
                             route.emotions[0] == COMP_EXPRESSION_RIG_EMOTION_CALM &&
                             route.emotions[1] == COMP_EXPRESSION_RIG_EMOTION_CURIOUS &&
                             route.emotions[2] == COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE &&
                             route.emotions[3] == COMP_EXPRESSION_RIG_EMOTION_PLAYFUL,
                         "calm reaches playful through the required notice and warm bridge")) {
            return 1;
        }
        if (require_true(comp_expression_rig_emotion_transition_route(
                             COMP_EXPRESSION_RIG_EMOTION_CALM,
                             COMP_EXPRESSION_RIG_EMOTION_THINKING, &route) &&
                             route.count == 3u &&
                             route.emotions[1] == COMP_EXPRESSION_RIG_EMOTION_CURIOUS &&
                             comp_expression_rig_emotion_transition_allowed(
                                 route.emotions[0], route.emotions[1]) &&
                             comp_expression_rig_emotion_transition_allowed(
                                 route.emotions[1], route.emotions[2]),
                         "calm reaches thinking through a directed attention bridge")) {
            return 1;
        }
        affect_input.event = COMP_EXPRESSION_RIG_EVENT_MENU_HOLD;
        if (require_true(comp_expression_rig_affect_target_emotion(&warm_affect, &affect_input, &target) &&
                             target == COMP_EXPRESSION_RIG_EMOTION_THINKING,
                         "menu context has a dedicated thinking target before its art binding")) {
            return 1;
        }
        affect_input.event = COMP_EXPRESSION_RIG_EVENT_RECORDING_ACTIVE;
        if (require_true(comp_expression_rig_affect_target_emotion(&warm_affect, &affect_input, &target) &&
                             target == COMP_EXPRESSION_RIG_EMOTION_FOCUSED,
                         "recording context has a dedicated focused target before its art binding")) {
            return 1;
        }
        affect_input.event = COMP_EXPRESSION_RIG_EVENT_UPGRADE_ACTIVE;
        if (require_true(comp_expression_rig_affect_target_emotion(&warm_affect, &affect_input, &target) &&
                             target == COMP_EXPRESSION_RIG_EMOTION_CALM,
                         "upgrade affect target is defined while its visual scene remains fail closed")) {
            return 1;
        }
    }

    if (require_true(!comp_v9_expression_rig_candidate_runtime_activation_allowed(),
                     "candidate Rig remains runtime-inactive until owner approval")) {
        return 1;
    }
    if (write_json(argc == 2 ? argv[1] : NULL, &daily_a, &memory_state,
                   &swipe_left_state, &swipe_right_state, &behavior_decision) != 0) {
        return 1;
    }
    puts("PASS: deterministic behavior arbitration maps causal event, attention, energy and memory to legal v9 Rig plans with fail-closed special scenes");
    return 0;
}
