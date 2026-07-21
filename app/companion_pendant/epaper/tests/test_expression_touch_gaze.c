#include "expression_touch_gaze.h"
#include "generated/expression_rig_v42_expression_extension_candidate_profile.h"

#include <stdio.h>

static int require_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

static int has_offset(const comp_expression_rig_plan_t *plan, uint16_t component_id,
                      int8_t x, int8_t y)
{
    uint8_t index;

    for (index = 0u; index < plan->layer_count; ++index) {
        if (plan->layers[index].component_id == component_id &&
            plan->layers[index].offset_x == x && plan->layers[index].offset_y == y) {
            return 1;
        }
    }
    return 0;
}

static int exercise_sample(const comp_expression_rig_profile_t *profile,
                           uint16_t x, uint16_t y,
                           comp_expression_rig_attention_t expected_attention,
                           int8_t primary_x, int8_t primary_y,
                           int8_t sparkle_x, int8_t sparkle_y)
{
    const comp_expression_rig_touch_sample_t sample = {.pressed = true, .x = x, .y = y};
    comp_expression_rig_touch_gaze_target_t target;
    comp_expression_rig_state_t state = {
        .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
        .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
        .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
        .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL,
        .interaction_memory = 0u,
        .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN,
    };
    comp_expression_rig_plan_t plan;

    if (!comp_expression_rig_touch_gaze_map(&sample, &target) ||
        target.attention != expected_attention ||
        target.touch_x != x || target.touch_y != y ||
        !comp_v42_two_track_candidate_build_composed_frame(10u, 0u,
            COMP_V42_TWO_TRACK_CANDIDATE_NO_FUNCTIONAL_TRACK,
            COMP_V42_TWO_TRACK_CANDIDATE_NO_FUNCTIONAL_TRACK, &state, &plan) ||
        !comp_expression_rig_touch_gaze_apply(profile, &target, &plan)) {
        return 0;
    }
    return has_offset(&plan, 1u, primary_x, primary_y) &&
           has_offset(&plan, 5u, primary_x, primary_y) &&
           has_offset(&plan, 3u, sparkle_x, sparkle_y) &&
           has_offset(&plan, 7u, sparkle_x, sparkle_y) &&
           has_offset(&plan, 4u, 0, 0) &&
           has_offset(&plan, 2u, 0, 0) && has_offset(&plan, 6u, 0, 0);
}

static int write_report(const char *path)
{
    FILE *file;

    if (path == NULL || fopen_s(&file, path, "wb") != 0 || file == NULL) {
        return 0;
    }
    fprintf(file,
            "{\n"
            "  \"schema\": \"companion.expression_touch_gaze_wb55_host.v2\",\n"
            "  \"status\": \"PASS_TOUCH_COORDINATE_GAZE_RUNTIME_INACTIVE\",\n"
            "  \"canvas\": \"200x200\",\n"
            "  \"mapping\": \"direct pixel-derived legal highlight and sparkle offsets\",\n"
            "  \"surface\": \"owner_visible_performance_card_face_box\",\n"
            "  \"gesture_surrogates\": [\"tap\", \"drag\", \"release_to_center\"],\n"
            "  \"release_behavior\": \"center\",\n"
            "  \"eye_body_changed\": false,\n"
            "  \"nose_offset\": [0, 0],\n"
            "  \"random_selection\": false,\n"
            "  \"runtime_resource_activated\": false\n"
            "}\n");
    fclose(file);
    return 1;
}

int main(int argc, char **argv)
{
    const comp_expression_rig_profile_t *profile = comp_v42_two_track_candidate_profile();
    comp_expression_rig_touch_gaze_target_t target;
    const comp_expression_rig_touch_sample_t release = {.pressed = false, .x = 100u, .y = 100u};

    if (require_true(profile != NULL && !comp_v42_two_track_candidate_runtime_activation_allowed(),
                     "touch gaze host test must use inactive V42 profile") ||
        require_true(comp_expression_rig_touch_gaze_map(&release, &target) &&
                     target.attention == COMP_EXPRESSION_RIG_ATTENTION_CENTER &&
                     target.touch_x == 100u && target.touch_y == 100u &&
                     target.primary_x == 1 && target.primary_y == 0 &&
                     target.sparkle_x == 1 && target.sparkle_y == 0,
                     "touch release must return the center target") ||
        require_true(exercise_sample(profile, 0u, 100u, COMP_EXPRESSION_RIG_ATTENTION_LEFT, -2, 0, -6, 0) &&
                     exercise_sample(profile, 199u, 100u, COMP_EXPRESSION_RIG_ATTENTION_RIGHT, 5, 0, 5, 0) &&
                     exercise_sample(profile, 100u, 0u, COMP_EXPRESSION_RIG_ATTENTION_UP, 1, -3, 1, -6) &&
                     exercise_sample(profile, 100u, 199u, COMP_EXPRESSION_RIG_ATTENTION_DOWN, 1, 4, 1, 6) &&
                     exercise_sample(profile, 50u, 75u, COMP_EXPRESSION_RIG_ATTENTION_LEFT, -1, -1, -3, -2) &&
                     exercise_sample(profile, 150u, 125u, COMP_EXPRESSION_RIG_ATTENTION_RIGHT, 3, 1, 3, 2) &&
                     exercise_sample(profile, 100u, 100u, COMP_EXPRESSION_RIG_ATTENTION_CENTER, 1, 0, 1, 0),
                     "touch coordinates must map to deterministic continuous legal V9 gaze offsets") ||
        require_true(!comp_expression_rig_touch_gaze_map(
                         &(comp_expression_rig_touch_sample_t){.pressed = true, .x = 200u, .y = 100u}, &target),
                     "out-of-canvas touch must fail closed") ||
        !write_report(argc > 1 ? argv[1] : NULL)) {
        return 1;
    }
    printf("PASS: simulated touch coordinates drive only registered highlight/sparkle offsets and release centers gaze.\n");
    return 0;
}
