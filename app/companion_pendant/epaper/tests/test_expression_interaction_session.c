#include "expression_interaction_session.h"
#include "generated/expression_rig_v9_candidate_profile.h"
#include "touch_gesture.h"

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

static const char *emotion_name(comp_expression_rig_emotion_t emotion)
{
    static const char *const k_names[] = {
        "calm", "curious", "affectionate", "focused", "sleepy", "alert",
        "joyful", "playful", "anticipatory", "puzzled", "listening", "thinking",
    };

    return emotion < COMP_EXPRESSION_RIG_EMOTION_COUNT ? k_names[emotion] : "invalid";
}

static const char *scene_name(comp_expression_rig_scene_t scene)
{
    static const char *const k_names[] = {
        "daily", "touch", "swipe", "recording", "menu", "sleep", "charging", "error",
    };

    return scene < COMP_EXPRESSION_RIG_SCENE_COUNT ? k_names[scene] : "invalid";
}

static const char *attention_name(comp_expression_rig_attention_t attention)
{
    static const char *const k_names[] = {"center", "left", "right", "up", "down"};

    return attention < COMP_EXPRESSION_RIG_ATTENTION_COUNT ? k_names[attention] : "invalid";
}

static const char *score_phase_name_or_null(const comp_expression_rig_interaction_frame_t *frame)
{
    if (frame == NULL || frame->performance_score == NULL) {
        return NULL;
    }
    return comp_expression_rig_score_phase_name(frame->score_phase);
}

static int write_plan(FILE *file, const comp_expression_rig_plan_t *plan)
{
    uint8_t index;

    if (fprintf(file, "[") < 0) {
        return 1;
    }
    for (index = 0u; index < plan->layer_count; ++index) {
        const comp_expression_rig_layer_t *layer = &plan->layers[index];

        if (fprintf(file,
                    "%s{\"component_id\":%u,\"base_x\":%d,\"base_y\":%d,"
                    "\"offset_x\":%d,\"offset_y\":%d,\"composite_op\":%u}",
                    index == 0u ? "" : ",", (unsigned)layer->component_id,
                    (int)layer->base_x, (int)layer->base_y, (int)layer->offset_x,
                    (int)layer->offset_y, (unsigned)layer->composite_op) < 0) {
            return 1;
        }
    }
    return fprintf(file, "]") < 0 ? 1 : 0;
}

static bool plan_has_component(const comp_expression_rig_plan_t *plan, uint16_t component_id)
{
    uint8_t index;

    if (plan == NULL) {
        return false;
    }
    for (index = 0u; index < plan->layer_count; ++index) {
        if (plan->layers[index].component_id == component_id) {
            return true;
        }
    }
    return false;
}

static int write_evidence(const char *path,
                          const comp_expression_rig_interaction_session_t *session,
                          const comp_expression_rig_performance_score_t *notice_score,
                          const comp_expression_rig_interaction_frame_t *frames,
                          const comp_expression_rig_plan_t *plans,
                          uint8_t frame_count)
{
    FILE *file = NULL;
    uint8_t index;

    if (path == NULL) {
        return 0;
    }
    if (fopen_s(&file, path, "wb") != 0 || file == NULL) {
        fprintf(stderr, "FAIL: could not write %s\n", path);
        return 1;
    }
    fprintf(file,
            "{\n"
            "  \"schema\": \"companion.v9_rig_touch_emotion_machine_loop.v1\",\n"
            "  \"status\": \"PASS_TOUCH_TO_RIG_MACHINE_LOOP_RUNTIME_INACTIVE\",\n"
            "  \"source_sha256\": \"%s\",\n"
            "  \"runtime_resource_activated\": false,\n"
            "  \"touch_fixture\": {\"decoder_event\": \"tap\", \"start\": [160, 100], \"end\": [161, 100], \"attention\": \"right\", \"energy\": \"high\", \"interaction_memory\": 2},\n"
            "  \"behavior\": {\"intent\": \"%s\", \"target_emotion\": \"%s\", \"route\": [",
            COMP_V9_EXPRESSION_RIG_CANDIDATE_SOURCE_SHA256,
            comp_expression_rig_intent_name(session->sequence.decision.intent),
            emotion_name(session->sequence.decision.target_emotion));
    for (index = 0u; index < session->sequence.decision.route.count; ++index) {
        fprintf(file, "%s\"%s\"", index == 0u ? "" : ",",
                emotion_name(session->sequence.decision.route.emotions[index]));
    }
    fprintf(file,
            "]},\n"
            "  \"presentation\": {\"notice_score\": \"daily_right\", \"source_score_step_count\": %u, \"selected_component_keyframes\": %u, \"omitted_transient_score_steps\": %u, \"minimum_post_refresh_hold_ms\": 750, \"all_visible_frames_require_prior_refresh_completion\": true},\n"
            "  \"sequencing\": {\"next_frame_blocked_until_completion\": true, \"failed_frame_retries_same_plan\": true, \"visible_frame_count\": %lu, \"submitted_frame_count\": %lu},\n"
            "  \"frames\": [\n",
            (unsigned)notice_score->step_count,
            (unsigned)COMP_EXPRESSION_RIG_INTERACTION_MAX_SCORE_KEYFRAMES,
            (unsigned)(notice_score->step_count - COMP_EXPRESSION_RIG_INTERACTION_MAX_SCORE_KEYFRAMES),
            (unsigned long)session->visible_frames,
            (unsigned long)session->submitted_frames);
    for (index = 0u; index < frame_count; ++index) {
        const comp_expression_rig_interaction_frame_t *frame = &frames[index];

        fprintf(file,
                "    %s{\"index\":%u,\"kind\":\"%s\",\"route_index\":%u,"
                "\"scene\":\"%s\",\"emotion\":\"%s\",\"attention\":\"%s\","
                "\"energy\":%u,\"interaction_memory\":%u,\"phase\":%u,"
                "\"score_phase\":",
                index == 0u ? "" : ",\n", (unsigned)index,
                comp_expression_rig_interaction_frame_kind_name(frame->kind),
                (unsigned)frame->route_index, scene_name(frame->state.scene),
                emotion_name(frame->state.emotion), attention_name(frame->state.attention),
                (unsigned)frame->state.energy, (unsigned)frame->state.interaction_memory,
                (unsigned)frame->state.phase);
        if (score_phase_name_or_null(frame) == NULL) {
            fprintf(file, "null");
        } else {
            fprintf(file, "\"%s\"", score_phase_name_or_null(frame));
        }
        if (frame->performance_score == NULL) {
            fprintf(file, " ,\"score_step_index\":null");
        } else {
            fprintf(file, ",\"score_step_index\":%u", (unsigned)frame->score_step_index);
        }
        fprintf(file, ",\"post_refresh_hold_ms\":%u,\"layers\":",
                (unsigned)frame->post_refresh_hold_ms);
        if (write_plan(file, &plans[index]) != 0) {
            fclose(file);
            return 1;
        }
        fprintf(file, "}");
    }
    fprintf(file,
            "\n  ],\n"
            "  \"fail_closed\": [\"menu_hold\", \"recording_active\", \"charging\", \"error\", \"upgrade_active\"],\n"
            "  \"forbidden_runtime_paths\": [\"whole-face card loop\", \"code-drawn face\", \"legacy art\", \"custom LUT\"]\n"
            "}\n");
    fclose(file);
    return 0;
}

int main(int argc, char **argv)
{
    const comp_expression_rig_profile_t *profile = comp_v9_expression_rig_candidate_profile();
    const comp_expression_rig_performance_score_t *notice_score =
        comp_v9_expression_rig_candidate_daily_score(COMP_EXPRESSION_RIG_ATTENTION_RIGHT);
    comp_touch_gesture_state_t gesture;
    comp_touch_gesture_event_t touch_event;
    comp_expression_rig_choreography_input_t input = {
        .event = COMP_EXPRESSION_RIG_EVENT_TOUCH_TAP,
        .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT,
        .energy = COMP_EXPRESSION_RIG_ENERGY_HIGH,
        .interaction_memory = 2u,
        .seed = 0x715A2C11u,
        .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN,
    };
    comp_expression_rig_interaction_session_t session;
    comp_expression_rig_interaction_session_t replay;
    comp_expression_rig_interaction_frame_t frames[COMP_EXPRESSION_RIG_INTERACTION_MAX_FRAMES];
    comp_expression_rig_plan_t plans[COMP_EXPRESSION_RIG_INTERACTION_MAX_FRAMES];
    comp_expression_rig_interaction_frame_t retry_frame;
    comp_expression_rig_plan_t retry_plan;
    comp_expression_rig_behavior_state_t behavior_before_fail_closed;
    uint8_t frame_count = 0u;

    comp_touch_gesture_init(&gesture, NULL);
    if (require_true(!comp_touch_gesture_process(&gesture, true, false, 160u, 100u, 0u, &touch_event) &&
                         !comp_touch_gesture_process(&gesture, true, false, 161u, 100u, 20u, &touch_event) &&
                         !comp_touch_gesture_process(&gesture, false, false, 0u, 0u, 40u, &touch_event) &&
                         comp_touch_gesture_process(&gesture, false, false, 0u, 0u, 60u, &touch_event) &&
                         touch_event.type == COMP_TOUCH_GESTURE_TAP &&
                         touch_event.start_x == 160u && touch_event.end_x == 161u,
                     "real touch gesture replay must classify the familiar contact as one tap")) {
        return 1;
    }

    comp_expression_rig_interaction_session_init(&session);
    if (require_true(notice_score != NULL &&
                         comp_expression_rig_interaction_session_start_with_notice_score(
                             &session, profile, &input, notice_score) &&
                         session.sequence.decision.route.count == 3u &&
                         session.sequence.decision.route.emotions[0] == COMP_EXPRESSION_RIG_EMOTION_CALM &&
                         session.sequence.decision.route.emotions[1] == COMP_EXPRESSION_RIG_EMOTION_CURIOUS &&
                         session.sequence.decision.route.emotions[2] == COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE &&
                         session.sequence.frame_count == 8u,
                     "familiar touch must open a source-component notice score before the calm-to-curious-to-affectionate causal route")) {
        return 1;
    }

    if (require_true(comp_expression_rig_interaction_session_take_frame(&session, profile,
                                                                          &frames[0], &plans[0]) &&
                         !comp_expression_rig_interaction_session_take_frame(&session, profile,
                                                                               &retry_frame, &retry_plan) &&
                         comp_expression_rig_interaction_session_complete_frame(&session, false) &&
                         comp_expression_rig_interaction_session_take_frame(&session, profile,
                                                                          &retry_frame, &retry_plan) &&
                         memcmp(&frames[0], &retry_frame, sizeof(retry_frame)) == 0 &&
                         memcmp(&plans[0], &retry_plan, sizeof(retry_plan)) == 0 &&
                         comp_expression_rig_interaction_session_complete_frame(&session, true),
                     "next component plan waits for completion and a failed panel retry keeps the same frame")) {
        return 1;
    }
    frame_count = 1u;
    while (session.active && frame_count < COMP_EXPRESSION_RIG_INTERACTION_MAX_FRAMES) {
        if (require_true(comp_expression_rig_interaction_session_take_frame(&session, profile,
                                                                              &frames[frame_count],
                                                                              &plans[frame_count]) &&
                             comp_expression_rig_interaction_session_complete_frame(&session, true),
                         "each causal component plan must complete before the next frame")) {
            return 1;
        }
        frame_count++;
    }
    if (require_true(frame_count == 8u && !session.active && session.visible_frames == 8u &&
                         session.failed_frame_retries == 1u &&
                         frames[0].kind == COMP_EXPRESSION_RIG_INTERACTION_FRAME_PERFORMANCE &&
                         frames[0].score_phase == COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY &&
                         frames[1].score_phase == COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD &&
                         frames[2].score_phase == COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE &&
                         frames[3].score_phase == COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT &&
                         frames[4].score_phase == COMP_EXPRESSION_RIG_SCORE_PHASE_RELEASE &&
                         frames[5].kind == COMP_EXPRESSION_RIG_INTERACTION_FRAME_BRIDGE &&
                         frames[5].state.scene == COMP_EXPRESSION_RIG_SCENE_DAILY &&
                         frames[5].state.emotion == COMP_EXPRESSION_RIG_EMOTION_CURIOUS &&
                         frames[6].kind == COMP_EXPRESSION_RIG_INTERACTION_FRAME_TARGET &&
                         frames[6].state.scene == COMP_EXPRESSION_RIG_SCENE_DAILY &&
                         frames[6].state.emotion == COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE &&
                         !plan_has_component(&plans[5], 20u) &&
                         !plan_has_component(&plans[6], 20u) &&
                         frames[7].kind == COMP_EXPRESSION_RIG_INTERACTION_FRAME_SETTLE &&
                         frames[7].state.scene == COMP_EXPRESSION_RIG_SCENE_DAILY &&
                         frames[7].state.emotion == COMP_EXPRESSION_RIG_EMOTION_CALM,
                     "causal route must expose key component poses, curious bridge, affectionate touch target and calm settle")) {
        return 1;
    }

    comp_expression_rig_interaction_session_init(&replay);
    if (require_true(comp_expression_rig_interaction_session_start_with_notice_score(
                         &replay, profile, &input, notice_score) &&
                         replay.sequence.frame_count == session.sequence.frame_count &&
                         memcmp(&replay.sequence, &session.sequence, sizeof(replay.sequence)) == 0,
                     "same touch/emotion input must produce an identical source-component sequence")) {
        return 1;
    }
    behavior_before_fail_closed = session.behavior;
    input.event = COMP_EXPRESSION_RIG_EVENT_MENU_HOLD;
    if (require_true(!comp_expression_rig_interaction_session_start(&session, profile, &input) &&
                         memcmp(&behavior_before_fail_closed, &session.behavior,
                                sizeof(behavior_before_fail_closed)) == 0,
                     "unbound menu expression must fail closed without borrowing a daily face")) {
        return 1;
    }

    if (write_evidence(argc == 2 ? argv[1] : NULL, &session, notice_score, frames, plans,
                       frame_count) != 0) {
        return 1;
    }
    puts("PASS: touch gesture replay drives an e-paper-safe component score into a deterministic calm-curious-affectionate route");
    return 0;
}
