#include "expression_rig.h"
#include "expression_rig_performance_score.h"
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
                                                      comp_expression_rig_role_t role)
{
    uint8_t index;

    for (index = 0u; index < plan->layer_count; ++index) {
        const comp_expression_rig_component_info_t *component;
        const comp_expression_rig_profile_t *profile = comp_v9_expression_rig_candidate_profile();
        size_t component_index;

        for (component_index = 0u; component_index < profile->component_count; ++component_index) {
            component = &profile->components[component_index];
            if (component->component_id == plan->layers[index].component_id && component->role == role) {
                return &plan->layers[index];
            }
        }
    }
    return NULL;
}

int main(void)
{
    const comp_expression_rig_profile_t *profile = comp_v9_expression_rig_candidate_profile();
    const comp_expression_rig_performance_score_t *right_score;
    const comp_expression_rig_layer_t *left_highlight;
    const comp_expression_rig_layer_t *right_highlight;
    const comp_expression_rig_layer_t *left_sparkle;
    const comp_expression_rig_layer_t *right_sparkle;
    const comp_expression_rig_layer_t *left_eye;
    const comp_expression_rig_layer_t *left_brow;
    const comp_expression_rig_layer_t *right_brow;
    const comp_expression_rig_layer_t *mouth;
    const comp_expression_rig_layer_t *left_cheek;
    const comp_expression_rig_layer_t *right_cheek;
    comp_expression_rig_attention_t presentation_attention;
    comp_expression_rig_score_pose_t invalid_pose;
    comp_expression_rig_score_step_t invalid_step;
    comp_expression_rig_performance_score_t invalid_score;
    comp_expression_rig_state_t story = {
        COMP_EXPRESSION_RIG_SCENE_DAILY,
        COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
        COMP_EXPRESSION_RIG_ATTENTION_RIGHT,
        COMP_EXPRESSION_RIG_ENERGY_HIGH,
        1u,
        COMP_EXPRESSION_RIG_PHASE_SUSTAIN,
    };
    comp_expression_rig_state_t entry_state;
    comp_expression_rig_plan_t entry_plan;
    comp_expression_rig_plan_t step_plan;

    if (require_true(strcmp(comp_expression_rig_score_phase_name(
                         COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY), "entry") == 0 &&
                         strcmp(comp_expression_rig_score_phase_name(
                         COMP_EXPRESSION_RIG_SCORE_PHASE_SETTLE), "settle") == 0 &&
                         strcmp(comp_expression_rig_score_phase_name(
                         COMP_EXPRESSION_RIG_SCORE_PHASE_COUNT), "invalid") == 0,
                     "score phase labels are stable and fail closed")) {
        return 1;
    }
    if (require_true(comp_v9_expression_rig_candidate_daily_presentation_story_count() == 4u &&
                         comp_v9_expression_rig_candidate_daily_presentation_attention(
                             0u, &presentation_attention) &&
                         presentation_attention == COMP_EXPRESSION_RIG_ATTENTION_LEFT &&
                         comp_v9_expression_rig_candidate_daily_presentation_attention(
                             3u, &presentation_attention) &&
                         presentation_attention == COMP_EXPRESSION_RIG_ATTENTION_DOWN &&
                         !comp_v9_expression_rig_candidate_daily_presentation_attention(
                             4u, &presentation_attention),
                     "generated panel presentation order is continuous left-right-up-down")) {
        return 1;
    }
    if (require_true(profile != NULL && !comp_v9_expression_rig_candidate_runtime_activation_allowed() &&
                         comp_expression_rig_story_state(&story, COMP_EXPRESSION_RIG_PHASE_ENTRY, &entry_state) &&
                         comp_expression_rig_build_plan(profile, &entry_state, &entry_plan),
                     "candidate profile creates a calm daily entry plan without activation")) {
        return 1;
    }
    right_score = comp_v9_expression_rig_candidate_daily_score(COMP_EXPRESSION_RIG_ATTENTION_RIGHT);
    if (require_true(right_score != NULL && right_score->step_count == 18u &&
                         comp_v9_expression_rig_candidate_daily_score(COMP_EXPRESSION_RIG_ATTENTION_CENTER) == NULL,
                     "generated score exposes only registered directional Daily performances")) {
        return 1;
    }
    if (require_true(comp_expression_rig_apply_score_step(profile, &entry_plan, right_score, 4u, &step_plan),
                      "generated paired dynamic-rest pose builds")) {
        return 1;
    }
    left_highlight = find_layer(&step_plan, COMP_EXPRESSION_RIG_ROLE_LEFT_HIGHLIGHT);
    right_highlight = find_layer(&step_plan, COMP_EXPRESSION_RIG_ROLE_RIGHT_HIGHLIGHT);
    left_sparkle = find_layer(&step_plan, COMP_EXPRESSION_RIG_ROLE_LEFT_SPARKLE);
    right_sparkle = find_layer(&step_plan, COMP_EXPRESSION_RIG_ROLE_RIGHT_SPARKLE);
    left_eye = find_layer(&step_plan, COMP_EXPRESSION_RIG_ROLE_LEFT_EYE);
    if (require_true(left_highlight != NULL && right_highlight != NULL && left_sparkle != NULL &&
                         right_sparkle != NULL && left_eye != NULL && left_highlight->offset_x == 0 &&
                         left_highlight->offset_y == 2 && right_highlight->offset_x == 0 &&
                         right_highlight->offset_y == 2 && left_sparkle->offset_x == 0 &&
                         left_sparkle->offset_y == 2 && right_sparkle->offset_x == 0 &&
                         right_sparkle->offset_y == 2 &&
                         left_eye->offset_x == 0 && left_eye->offset_y == 0,
                      "right score brings both paired reflections to the shared dynamic rest without moving eye bodies")) {
        return 1;
    }
    if (require_true(comp_expression_rig_apply_score_step(profile, &entry_plan, right_score, 6u, &step_plan),
                     "generated paired rightward gaze pose builds")) {
        return 1;
    }
    left_highlight = find_layer(&step_plan, COMP_EXPRESSION_RIG_ROLE_LEFT_HIGHLIGHT);
    right_highlight = find_layer(&step_plan, COMP_EXPRESSION_RIG_ROLE_RIGHT_HIGHLIGHT);
    left_sparkle = find_layer(&step_plan, COMP_EXPRESSION_RIG_ROLE_LEFT_SPARKLE);
    right_sparkle = find_layer(&step_plan, COMP_EXPRESSION_RIG_ROLE_RIGHT_SPARKLE);
    if (require_true(left_highlight != NULL && right_highlight != NULL && left_sparkle != NULL &&
                         right_sparkle != NULL && left_highlight->offset_x == 1 &&
                         left_highlight->offset_y == 2 && right_highlight->offset_x == 1 &&
                         right_highlight->offset_y == 2 && left_sparkle->offset_x == 1 &&
                         left_sparkle->offset_y == 2 && right_sparkle->offset_x == 1 &&
                         right_sparkle->offset_y == 2,
                      "paired rightward score leads both source reflection groups from the shared dynamic rest")) {
        return 1;
    }
    if (require_true(comp_expression_rig_apply_score_step(profile, &entry_plan, right_score, 7u, &step_plan),
                     "generated coordinated facial response pose builds")) {
        return 1;
    }
    left_brow = find_layer(&step_plan, COMP_EXPRESSION_RIG_ROLE_LEFT_BROW);
    right_brow = find_layer(&step_plan, COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW);
    mouth = find_layer(&step_plan, COMP_EXPRESSION_RIG_ROLE_MOUTH);
    left_cheek = find_layer(&step_plan, COMP_EXPRESSION_RIG_ROLE_LEFT_CHEEK);
    right_cheek = find_layer(&step_plan, COMP_EXPRESSION_RIG_ROLE_RIGHT_CHEEK);
    if (require_true(left_brow != NULL && right_brow != NULL && mouth != NULL &&
                         left_cheek != NULL && right_cheek != NULL &&
                         left_brow->offset_x == 1 && left_brow->offset_y == -2 &&
                         right_brow->offset_x == 1 && right_brow->offset_y == -2 &&
                         mouth->offset_x == 0 && mouth->offset_y == 1 &&
                         left_cheek->offset_x == 0 && left_cheek->offset_y == -1 &&
                         right_cheek->offset_x == 0 && right_cheek->offset_y == -1,
                      "right score lands brows, mouth and both cheeks as one coordinated facial response")) {
        return 1;
    }
    if (require_true(comp_expression_rig_apply_score_step(profile, &entry_plan, right_score,
                                                           (uint8_t)(right_score->step_count - 1u), &step_plan),
                     "generated settle pose builds")) {
        return 1;
    }
    left_highlight = find_layer(&step_plan, COMP_EXPRESSION_RIG_ROLE_LEFT_HIGHLIGHT);
    right_highlight = find_layer(&step_plan, COMP_EXPRESSION_RIG_ROLE_RIGHT_HIGHLIGHT);
    left_sparkle = find_layer(&step_plan, COMP_EXPRESSION_RIG_ROLE_LEFT_SPARKLE);
    right_sparkle = find_layer(&step_plan, COMP_EXPRESSION_RIG_ROLE_RIGHT_SPARKLE);
    if (require_true(left_highlight != NULL && right_highlight != NULL && left_sparkle != NULL &&
                         right_sparkle != NULL &&
                         left_highlight->offset_x == 0 && left_highlight->offset_y == 0 &&
                         right_highlight->offset_x == 0 && right_highlight->offset_y == 0 &&
                         left_sparkle->offset_x == 0 && left_sparkle->offset_y == 0 &&
                         right_sparkle->offset_x == 0 && right_sparkle->offset_y == 0,
                      "generated score settles exactly to the calm Daily entry offsets")) {
        return 1;
    }
    invalid_pose = (comp_expression_rig_score_pose_t){left_eye->component_id, 1, 0};
    invalid_step = (comp_expression_rig_score_step_t){
        COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, 100u, &invalid_pose, 1u,
    };
    invalid_score = (comp_expression_rig_performance_score_t){&invalid_step, 1u};
    if (require_true(!comp_expression_rig_apply_score_step(profile, &entry_plan, &invalid_score, 0u, &step_plan) &&
                         !comp_expression_rig_apply_score_step(profile, &entry_plan, right_score,
                                                               right_score->step_count, &step_plan),
                     "score core fails closed for eye-body or out-of-range score steps")) {
        return 1;
    }
    puts("PASS: generated Daily performance scores move paired legal source reflections without moving eye bodies");
    return 0;
}
