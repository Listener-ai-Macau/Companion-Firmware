/* Generated from the owner-reviewed v9 Rig layout; do not hand edit. */
#include "expression_rig_v9_candidate_profile.h"

static const comp_expression_rig_component_info_t k_v9_candidate_components[] = {
    {.component_id = 1u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_OPEN, .base_x = 47, .base_y = 85, .min_offset_x = -1, .min_offset_y = -3, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 2u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_OPEN, .base_x = 132, .base_y = 85, .min_offset_x = -1, .min_offset_y = -3, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 3u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_SLEEPY, .base_x = 48, .base_y = 91, .min_offset_x = -1, .min_offset_y = -1, .max_offset_x = 1, .max_offset_y = 2, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 4u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_SLEEPY, .base_x = 131, .base_y = 91, .min_offset_x = -1, .min_offset_y = -1, .max_offset_x = 1, .max_offset_y = 2, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 5u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_EYE, .variant = COMP_EXPRESSION_RIG_VARIANT_OPEN, .base_x = 42, .base_y = 112, .min_offset_x = -3, .min_offset_y = -2, .max_offset_x = 3, .max_offset_y = 2, .z_index = 30u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 6u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_EYE, .variant = COMP_EXPRESSION_RIG_VARIANT_OPEN, .base_x = 125, .base_y = 112, .min_offset_x = -3, .min_offset_y = -2, .max_offset_x = 3, .max_offset_y = 2, .z_index = 30u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 7u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_HIGHLIGHT, .variant = COMP_EXPRESSION_RIG_VARIANT_OPEN, .base_x = 42, .base_y = 112, .min_offset_x = -2, .min_offset_y = -3, .max_offset_x = 5, .max_offset_y = 4, .z_index = 31u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_ERASE},
    {.component_id = 8u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_HIGHLIGHT, .variant = COMP_EXPRESSION_RIG_VARIANT_OPEN, .base_x = 125, .base_y = 112, .min_offset_x = -2, .min_offset_y = -3, .max_offset_x = 5, .max_offset_y = 4, .z_index = 31u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_ERASE},
    {.component_id = 9u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_SPARKLE, .variant = COMP_EXPRESSION_RIG_VARIANT_OPEN, .base_x = 42, .base_y = 112, .min_offset_x = -6, .min_offset_y = -6, .max_offset_x = 5, .max_offset_y = 6, .z_index = 32u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_ERASE},
    {.component_id = 10u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_SPARKLE, .variant = COMP_EXPRESSION_RIG_VARIANT_OPEN, .base_x = 125, .base_y = 112, .min_offset_x = -6, .min_offset_y = -6, .max_offset_x = 5, .max_offset_y = 6, .z_index = 32u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_ERASE},
    {.component_id = 11u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_EYE, .variant = COMP_EXPRESSION_RIG_VARIANT_SLEEPY, .base_x = 43, .base_y = 130, .min_offset_x = -2, .min_offset_y = 0, .max_offset_x = 2, .max_offset_y = 2, .z_index = 30u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 12u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_EYE, .variant = COMP_EXPRESSION_RIG_VARIANT_SLEEPY, .base_x = 124, .base_y = 130, .min_offset_x = -2, .min_offset_y = 0, .max_offset_x = 2, .max_offset_y = 2, .z_index = 30u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 13u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_CHEEK, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 33, .base_y = 160, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 40u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 14u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_CHEEK, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 154, .base_y = 160, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 40u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 15u, .role = COMP_EXPRESSION_RIG_ROLE_NOSE, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 94, .base_y = 148, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 50u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 16u, .role = COMP_EXPRESSION_RIG_ROLE_MOUTH, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 86, .base_y = 160, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 60u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 17u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_DETAIL, .variant = COMP_EXPRESSION_RIG_VARIANT_SWIPE, .base_x = 23, .base_y = 108, .min_offset_x = -1, .min_offset_y = -1, .max_offset_x = 1, .max_offset_y = 1, .z_index = 35u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 18u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_DETAIL, .variant = COMP_EXPRESSION_RIG_VARIANT_SWIPE, .base_x = 155, .base_y = 111, .min_offset_x = -1, .min_offset_y = -1, .max_offset_x = 1, .max_offset_y = 1, .z_index = 35u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 19u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 96, .base_y = 31, .min_offset_x = 0, .min_offset_y = -3, .max_offset_x = 2, .max_offset_y = 1, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 20u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 137, .base_y = 26, .min_offset_x = 0, .min_offset_y = -3, .max_offset_x = 2, .max_offset_y = 1, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 21u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 38, .base_y = 41, .min_offset_x = 0, .min_offset_y = -3, .max_offset_x = 2, .max_offset_y = 1, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 22u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 129, .base_y = 34, .min_offset_x = 0, .min_offset_y = -3, .max_offset_x = 2, .max_offset_y = 1, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 23u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 99, .base_y = 50, .min_offset_x = 0, .min_offset_y = -3, .max_offset_x = 2, .max_offset_y = 1, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 24u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 72, .base_y = 27, .min_offset_x = 0, .min_offset_y = -3, .max_offset_x = 2, .max_offset_y = 1, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
};

static const comp_expression_rig_profile_t k_v9_candidate_profile = {
    .components = k_v9_candidate_components,
    .component_count = COMP_V9_EXPRESSION_RIG_CANDIDATE_COMPONENT_COUNT,
    .scene_charm_component = {
        [COMP_EXPRESSION_RIG_SCENE_DAILY] = 19,
        [COMP_EXPRESSION_RIG_SCENE_TOUCH] = 19,
        [COMP_EXPRESSION_RIG_SCENE_SWIPE] = 21,
        [COMP_EXPRESSION_RIG_SCENE_RECORDING] = 22,
        [COMP_EXPRESSION_RIG_SCENE_MENU] = 23,
        [COMP_EXPRESSION_RIG_SCENE_SLEEP] = 24,
        [COMP_EXPRESSION_RIG_SCENE_CHARGING] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,
        [COMP_EXPRESSION_RIG_SCENE_ERROR] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,
    },
};

const comp_expression_rig_profile_t *comp_v9_expression_rig_candidate_profile(void)
{
    return &k_v9_candidate_profile;
}

bool comp_v9_expression_rig_candidate_runtime_activation_allowed(void)
{
    return false;
}

static const comp_expression_rig_score_pose_t k_daily_left_step_1_poses[] = {
    {7u, 0, 1},
    {9u, 0, 1},
};
static const comp_expression_rig_score_pose_t k_daily_left_step_2_poses[] = {
    {7u, 0, 2},
    {9u, 0, 2},
};
static const comp_expression_rig_score_pose_t k_daily_left_step_3_poses[] = {
    {7u, 0, 2},
    {9u, 0, 2},
    {8u, 0, 1},
    {10u, 0, 1},
};
static const comp_expression_rig_score_pose_t k_daily_left_step_4_poses[] = {
    {7u, 0, 2},
    {9u, 0, 2},
    {8u, 0, 2},
    {10u, 0, 2},
};
static const comp_expression_rig_score_pose_t k_daily_left_step_5_poses[] = {
    {7u, -1, 2},
    {9u, -1, 2},
    {8u, 0, 2},
    {10u, 0, 2},
};
static const comp_expression_rig_score_pose_t k_daily_left_step_6_poses[] = {
    {7u, -1, 2},
    {9u, -1, 2},
    {8u, -1, 2},
    {10u, -1, 2},
};
static const comp_expression_rig_score_pose_t k_daily_left_step_7_poses[] = {
    {7u, -1, 2},
    {9u, -1, 2},
    {8u, -1, 2},
    {10u, -1, 2},
    {1u, -1, -2},
    {2u, -1, -2},
    {16u, 0, 1},
    {13u, 0, -1},
    {14u, 0, -1},
};
static const comp_expression_rig_score_pose_t k_daily_left_step_8_poses[] = {
    {7u, -1, 2},
    {9u, -1, 2},
    {8u, -1, 2},
    {10u, -1, 2},
    {1u, -1, -2},
    {2u, -1, -2},
    {16u, 0, 1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 1, -1},
};
static const comp_expression_rig_score_pose_t k_daily_left_step_9_poses[] = {
    {7u, -1, 2},
    {9u, -1, 2},
    {8u, -1, 2},
    {10u, -1, 2},
    {1u, -1, -2},
    {2u, -1, -2},
    {16u, 0, 1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 1, -2},
};
static const comp_expression_rig_score_pose_t k_daily_left_step_10_poses[] = {
    {7u, -1, 2},
    {9u, -1, 2},
    {8u, -1, 2},
    {10u, -1, 2},
    {1u, -1, -3},
    {2u, -1, -3},
    {16u, 0, 1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 1, -3},
};
static const comp_expression_rig_score_pose_t k_daily_left_step_11_poses[] = {
    {7u, -1, 2},
    {9u, -1, 2},
    {8u, -1, 2},
    {10u, -1, 2},
    {1u, -1, -3},
    {2u, -1, -3},
    {16u, 0, 1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 1, -3},
};
static const comp_expression_rig_score_pose_t k_daily_left_step_12_poses[] = {
    {7u, -1, 2},
    {9u, -1, 2},
    {8u, -1, 2},
    {10u, -1, 2},
    {1u, -1, -3},
    {2u, -1, -3},
    {16u, 0, 1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 1, -1},
};
static const comp_expression_rig_score_pose_t k_daily_left_step_13_poses[] = {
    {7u, -1, 2},
    {9u, -1, 2},
    {8u, -1, 2},
    {10u, -1, 2},
    {1u, -1, -3},
    {2u, -1, -3},
    {16u, 0, 1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 0, -1},
};
static const comp_expression_rig_score_pose_t k_daily_left_step_14_poses[] = {
    {7u, 0, 2},
    {9u, 0, 2},
    {8u, 0, 2},
    {10u, 0, 2},
    {1u, -1, -1},
    {2u, -1, -1},
    {19u, 0, -1},
};
static const comp_expression_rig_score_pose_t k_daily_left_step_15_poses[] = {
    {7u, 0, 1},
    {9u, 0, 1},
    {8u, 0, 2},
    {10u, 0, 2},
};
static const comp_expression_rig_score_pose_t k_daily_left_step_16_poses[] = {
    {7u, 0, 1},
    {9u, 0, 1},
    {8u, 0, 1},
    {10u, 0, 1},
};

static const comp_expression_rig_score_step_t k_daily_left_steps[] = {
    {COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, 420u, NULL, 0u},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_PREPARE, 100u, k_daily_left_step_1_poses, (uint8_t)(sizeof(k_daily_left_step_1_poses) / sizeof(k_daily_left_step_1_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, 110u, k_daily_left_step_2_poses, (uint8_t)(sizeof(k_daily_left_step_2_poses) / sizeof(k_daily_left_step_2_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, 120u, k_daily_left_step_3_poses, (uint8_t)(sizeof(k_daily_left_step_3_poses) / sizeof(k_daily_left_step_3_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, 130u, k_daily_left_step_4_poses, (uint8_t)(sizeof(k_daily_left_step_4_poses) / sizeof(k_daily_left_step_4_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, 110u, k_daily_left_step_5_poses, (uint8_t)(sizeof(k_daily_left_step_5_poses) / sizeof(k_daily_left_step_5_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, 120u, k_daily_left_step_6_poses, (uint8_t)(sizeof(k_daily_left_step_6_poses) / sizeof(k_daily_left_step_6_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, 150u, k_daily_left_step_7_poses, (uint8_t)(sizeof(k_daily_left_step_7_poses) / sizeof(k_daily_left_step_7_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, 100u, k_daily_left_step_8_poses, (uint8_t)(sizeof(k_daily_left_step_8_poses) / sizeof(k_daily_left_step_8_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, 110u, k_daily_left_step_9_poses, (uint8_t)(sizeof(k_daily_left_step_9_poses) / sizeof(k_daily_left_step_9_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, 100u, k_daily_left_step_10_poses, (uint8_t)(sizeof(k_daily_left_step_10_poses) / sizeof(k_daily_left_step_10_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, 900u, k_daily_left_step_11_poses, (uint8_t)(sizeof(k_daily_left_step_11_poses) / sizeof(k_daily_left_step_11_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RELEASE, 120u, k_daily_left_step_12_poses, (uint8_t)(sizeof(k_daily_left_step_12_poses) / sizeof(k_daily_left_step_12_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RELEASE, 100u, k_daily_left_step_13_poses, (uint8_t)(sizeof(k_daily_left_step_13_poses) / sizeof(k_daily_left_step_13_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RELEASE, 120u, k_daily_left_step_14_poses, (uint8_t)(sizeof(k_daily_left_step_14_poses) / sizeof(k_daily_left_step_14_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RETURN, 120u, k_daily_left_step_15_poses, (uint8_t)(sizeof(k_daily_left_step_15_poses) / sizeof(k_daily_left_step_15_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RETURN, 120u, k_daily_left_step_16_poses, (uint8_t)(sizeof(k_daily_left_step_16_poses) / sizeof(k_daily_left_step_16_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RETURN, 160u, NULL, 0u},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_SETTLE, 640u, NULL, 0u},
};

static const comp_expression_rig_performance_score_t k_daily_left_score = {
    .steps = k_daily_left_steps,
    .step_count = (uint8_t)(sizeof(k_daily_left_steps) / sizeof(k_daily_left_steps[0])),
};

static const comp_expression_rig_score_pose_t k_daily_right_step_1_poses[] = {
    {8u, 0, 1},
    {10u, 0, 1},
};
static const comp_expression_rig_score_pose_t k_daily_right_step_2_poses[] = {
    {8u, 0, 2},
    {10u, 0, 2},
};
static const comp_expression_rig_score_pose_t k_daily_right_step_3_poses[] = {
    {8u, 0, 2},
    {10u, 0, 2},
    {7u, 0, 1},
    {9u, 0, 1},
};
static const comp_expression_rig_score_pose_t k_daily_right_step_4_poses[] = {
    {8u, 0, 2},
    {10u, 0, 2},
    {7u, 0, 2},
    {9u, 0, 2},
};
static const comp_expression_rig_score_pose_t k_daily_right_step_5_poses[] = {
    {8u, 1, 2},
    {10u, 1, 2},
    {7u, 0, 2},
    {9u, 0, 2},
};
static const comp_expression_rig_score_pose_t k_daily_right_step_6_poses[] = {
    {8u, 1, 2},
    {10u, 1, 2},
    {7u, 1, 2},
    {9u, 1, 2},
};
static const comp_expression_rig_score_pose_t k_daily_right_step_7_poses[] = {
    {8u, 1, 2},
    {10u, 1, 2},
    {7u, 1, 2},
    {9u, 1, 2},
    {1u, 1, -2},
    {2u, 1, -2},
    {16u, 0, 1},
    {13u, 0, -1},
    {14u, 0, -1},
};
static const comp_expression_rig_score_pose_t k_daily_right_step_8_poses[] = {
    {8u, 1, 2},
    {10u, 1, 2},
    {7u, 1, 2},
    {9u, 1, 2},
    {1u, 1, -2},
    {2u, 1, -2},
    {16u, 0, 1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 1, -1},
};
static const comp_expression_rig_score_pose_t k_daily_right_step_9_poses[] = {
    {8u, 1, 2},
    {10u, 1, 2},
    {7u, 1, 2},
    {9u, 1, 2},
    {1u, 1, -2},
    {2u, 1, -2},
    {16u, 0, 1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 1, -2},
};
static const comp_expression_rig_score_pose_t k_daily_right_step_10_poses[] = {
    {8u, 1, 2},
    {10u, 1, 2},
    {7u, 1, 2},
    {9u, 1, 2},
    {1u, 1, -3},
    {2u, 1, -3},
    {16u, 0, 1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 1, -3},
};
static const comp_expression_rig_score_pose_t k_daily_right_step_11_poses[] = {
    {8u, 1, 2},
    {10u, 1, 2},
    {7u, 1, 2},
    {9u, 1, 2},
    {1u, 1, -3},
    {2u, 1, -3},
    {16u, 0, 1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 1, -3},
};
static const comp_expression_rig_score_pose_t k_daily_right_step_12_poses[] = {
    {8u, 1, 2},
    {10u, 1, 2},
    {7u, 1, 2},
    {9u, 1, 2},
    {1u, 1, -3},
    {2u, 1, -3},
    {16u, 0, 1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 1, -1},
};
static const comp_expression_rig_score_pose_t k_daily_right_step_13_poses[] = {
    {8u, 0, 2},
    {10u, 0, 2},
    {7u, 0, 2},
    {9u, 0, 2},
    {1u, 1, -1},
    {2u, 1, -1},
    {19u, 1, -1},
};
static const comp_expression_rig_score_pose_t k_daily_right_step_14_poses[] = {
    {8u, 0, 1},
    {10u, 0, 1},
    {7u, 0, 2},
    {9u, 0, 2},
};
static const comp_expression_rig_score_pose_t k_daily_right_step_15_poses[] = {
    {8u, 0, 1},
    {10u, 0, 1},
    {7u, 0, 1},
    {9u, 0, 1},
};

static const comp_expression_rig_score_step_t k_daily_right_steps[] = {
    {COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, 420u, NULL, 0u},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_PREPARE, 100u, k_daily_right_step_1_poses, (uint8_t)(sizeof(k_daily_right_step_1_poses) / sizeof(k_daily_right_step_1_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, 110u, k_daily_right_step_2_poses, (uint8_t)(sizeof(k_daily_right_step_2_poses) / sizeof(k_daily_right_step_2_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, 120u, k_daily_right_step_3_poses, (uint8_t)(sizeof(k_daily_right_step_3_poses) / sizeof(k_daily_right_step_3_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, 130u, k_daily_right_step_4_poses, (uint8_t)(sizeof(k_daily_right_step_4_poses) / sizeof(k_daily_right_step_4_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, 110u, k_daily_right_step_5_poses, (uint8_t)(sizeof(k_daily_right_step_5_poses) / sizeof(k_daily_right_step_5_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, 120u, k_daily_right_step_6_poses, (uint8_t)(sizeof(k_daily_right_step_6_poses) / sizeof(k_daily_right_step_6_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, 150u, k_daily_right_step_7_poses, (uint8_t)(sizeof(k_daily_right_step_7_poses) / sizeof(k_daily_right_step_7_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, 100u, k_daily_right_step_8_poses, (uint8_t)(sizeof(k_daily_right_step_8_poses) / sizeof(k_daily_right_step_8_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, 110u, k_daily_right_step_9_poses, (uint8_t)(sizeof(k_daily_right_step_9_poses) / sizeof(k_daily_right_step_9_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, 100u, k_daily_right_step_10_poses, (uint8_t)(sizeof(k_daily_right_step_10_poses) / sizeof(k_daily_right_step_10_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, 900u, k_daily_right_step_11_poses, (uint8_t)(sizeof(k_daily_right_step_11_poses) / sizeof(k_daily_right_step_11_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RELEASE, 120u, k_daily_right_step_12_poses, (uint8_t)(sizeof(k_daily_right_step_12_poses) / sizeof(k_daily_right_step_12_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RELEASE, 120u, k_daily_right_step_13_poses, (uint8_t)(sizeof(k_daily_right_step_13_poses) / sizeof(k_daily_right_step_13_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RETURN, 120u, k_daily_right_step_14_poses, (uint8_t)(sizeof(k_daily_right_step_14_poses) / sizeof(k_daily_right_step_14_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RETURN, 120u, k_daily_right_step_15_poses, (uint8_t)(sizeof(k_daily_right_step_15_poses) / sizeof(k_daily_right_step_15_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RETURN, 160u, NULL, 0u},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_SETTLE, 640u, NULL, 0u},
};

static const comp_expression_rig_performance_score_t k_daily_right_score = {
    .steps = k_daily_right_steps,
    .step_count = (uint8_t)(sizeof(k_daily_right_steps) / sizeof(k_daily_right_steps[0])),
};

static const comp_expression_rig_score_pose_t k_daily_up_step_1_poses[] = {
    {7u, 0, 1},
    {9u, 0, 1},
};
static const comp_expression_rig_score_pose_t k_daily_up_step_2_poses[] = {
    {7u, 0, 2},
    {9u, 0, 2},
};
static const comp_expression_rig_score_pose_t k_daily_up_step_3_poses[] = {
    {7u, 0, 2},
    {9u, 0, 2},
    {8u, 0, 1},
    {10u, 0, 1},
};
static const comp_expression_rig_score_pose_t k_daily_up_step_4_poses[] = {
    {7u, 0, 2},
    {9u, 0, 2},
    {8u, 0, 2},
    {10u, 0, 2},
};
static const comp_expression_rig_score_pose_t k_daily_up_step_5_poses[] = {
    {7u, 0, 1},
    {9u, 0, 1},
    {8u, 0, 2},
    {10u, 0, 2},
};
static const comp_expression_rig_score_pose_t k_daily_up_step_6_poses[] = {
    {7u, 0, 1},
    {9u, 0, 1},
    {8u, 0, 1},
    {10u, 0, 1},
};
static const comp_expression_rig_score_pose_t k_daily_up_step_7_poses[] = {
    {7u, 0, 1},
    {9u, 0, 1},
    {8u, 0, 1},
    {10u, 0, 1},
    {1u, 0, -2},
    {2u, 0, -2},
    {16u, 0, 1},
    {13u, 0, -1},
    {14u, 0, -1},
};
static const comp_expression_rig_score_pose_t k_daily_up_step_8_poses[] = {
    {7u, 0, 1},
    {9u, 0, 1},
    {8u, 0, 1},
    {10u, 0, 1},
    {1u, 0, -2},
    {2u, 0, -2},
    {16u, 0, 1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 1, -1},
};
static const comp_expression_rig_score_pose_t k_daily_up_step_9_poses[] = {
    {7u, 0, 1},
    {9u, 0, 1},
    {8u, 0, 1},
    {10u, 0, 1},
    {1u, 0, -2},
    {2u, 0, -2},
    {16u, 0, 1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 1, -2},
};
static const comp_expression_rig_score_pose_t k_daily_up_step_10_poses[] = {
    {7u, 0, 1},
    {9u, 0, 1},
    {8u, 0, 1},
    {10u, 0, 1},
    {1u, 0, -3},
    {2u, 0, -3},
    {16u, 0, 1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 1, -3},
};
static const comp_expression_rig_score_pose_t k_daily_up_step_11_poses[] = {
    {7u, 0, 1},
    {9u, 0, 1},
    {8u, 0, 1},
    {10u, 0, 1},
    {1u, 0, -3},
    {2u, 0, -3},
    {16u, 0, 1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 1, -3},
};
static const comp_expression_rig_score_pose_t k_daily_up_step_12_poses[] = {
    {7u, 0, 1},
    {9u, 0, 1},
    {8u, 0, 1},
    {10u, 0, 1},
    {1u, 0, -3},
    {2u, 0, -3},
    {16u, 0, 1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 1, -1},
};
static const comp_expression_rig_score_pose_t k_daily_up_step_13_poses[] = {
    {7u, 0, 1},
    {9u, 0, 1},
    {8u, 0, 1},
    {10u, 0, 1},
    {1u, 0, -3},
    {2u, 0, -3},
    {16u, 0, 1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 0, -1},
};
static const comp_expression_rig_score_pose_t k_daily_up_step_14_poses[] = {
    {7u, 0, 2},
    {9u, 0, 2},
    {8u, 0, 2},
    {10u, 0, 2},
    {1u, 0, -1},
    {2u, 0, -1},
    {19u, 0, -1},
};
static const comp_expression_rig_score_pose_t k_daily_up_step_15_poses[] = {
    {7u, 0, 1},
    {9u, 0, 1},
    {8u, 0, 2},
    {10u, 0, 2},
};
static const comp_expression_rig_score_pose_t k_daily_up_step_16_poses[] = {
    {7u, 0, 1},
    {9u, 0, 1},
    {8u, 0, 1},
    {10u, 0, 1},
};

static const comp_expression_rig_score_step_t k_daily_up_steps[] = {
    {COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, 420u, NULL, 0u},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_PREPARE, 100u, k_daily_up_step_1_poses, (uint8_t)(sizeof(k_daily_up_step_1_poses) / sizeof(k_daily_up_step_1_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, 110u, k_daily_up_step_2_poses, (uint8_t)(sizeof(k_daily_up_step_2_poses) / sizeof(k_daily_up_step_2_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, 120u, k_daily_up_step_3_poses, (uint8_t)(sizeof(k_daily_up_step_3_poses) / sizeof(k_daily_up_step_3_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, 130u, k_daily_up_step_4_poses, (uint8_t)(sizeof(k_daily_up_step_4_poses) / sizeof(k_daily_up_step_4_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, 110u, k_daily_up_step_5_poses, (uint8_t)(sizeof(k_daily_up_step_5_poses) / sizeof(k_daily_up_step_5_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, 120u, k_daily_up_step_6_poses, (uint8_t)(sizeof(k_daily_up_step_6_poses) / sizeof(k_daily_up_step_6_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, 150u, k_daily_up_step_7_poses, (uint8_t)(sizeof(k_daily_up_step_7_poses) / sizeof(k_daily_up_step_7_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, 100u, k_daily_up_step_8_poses, (uint8_t)(sizeof(k_daily_up_step_8_poses) / sizeof(k_daily_up_step_8_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, 110u, k_daily_up_step_9_poses, (uint8_t)(sizeof(k_daily_up_step_9_poses) / sizeof(k_daily_up_step_9_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, 100u, k_daily_up_step_10_poses, (uint8_t)(sizeof(k_daily_up_step_10_poses) / sizeof(k_daily_up_step_10_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, 900u, k_daily_up_step_11_poses, (uint8_t)(sizeof(k_daily_up_step_11_poses) / sizeof(k_daily_up_step_11_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RELEASE, 120u, k_daily_up_step_12_poses, (uint8_t)(sizeof(k_daily_up_step_12_poses) / sizeof(k_daily_up_step_12_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RELEASE, 100u, k_daily_up_step_13_poses, (uint8_t)(sizeof(k_daily_up_step_13_poses) / sizeof(k_daily_up_step_13_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RELEASE, 120u, k_daily_up_step_14_poses, (uint8_t)(sizeof(k_daily_up_step_14_poses) / sizeof(k_daily_up_step_14_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RETURN, 120u, k_daily_up_step_15_poses, (uint8_t)(sizeof(k_daily_up_step_15_poses) / sizeof(k_daily_up_step_15_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RETURN, 120u, k_daily_up_step_16_poses, (uint8_t)(sizeof(k_daily_up_step_16_poses) / sizeof(k_daily_up_step_16_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RETURN, 160u, NULL, 0u},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_SETTLE, 640u, NULL, 0u},
};

static const comp_expression_rig_performance_score_t k_daily_up_score = {
    .steps = k_daily_up_steps,
    .step_count = (uint8_t)(sizeof(k_daily_up_steps) / sizeof(k_daily_up_steps[0])),
};

static const comp_expression_rig_score_pose_t k_daily_down_step_1_poses[] = {
    {7u, 0, 1},
    {9u, 0, 1},
};
static const comp_expression_rig_score_pose_t k_daily_down_step_2_poses[] = {
    {7u, 0, 2},
    {9u, 0, 2},
};
static const comp_expression_rig_score_pose_t k_daily_down_step_3_poses[] = {
    {7u, 0, 2},
    {9u, 0, 2},
    {8u, 0, 1},
    {10u, 0, 1},
};
static const comp_expression_rig_score_pose_t k_daily_down_step_4_poses[] = {
    {7u, 0, 2},
    {9u, 0, 2},
    {8u, 0, 2},
    {10u, 0, 2},
};
static const comp_expression_rig_score_pose_t k_daily_down_step_5_poses[] = {
    {7u, 0, 2},
    {9u, 0, 2},
    {8u, 0, 2},
    {10u, 0, 2},
    {1u, 0, -1},
    {2u, 0, -1},
    {16u, 0, -1},
    {13u, 0, -1},
    {14u, 0, -1},
};
static const comp_expression_rig_score_pose_t k_daily_down_step_6_poses[] = {
    {7u, 0, 2},
    {9u, 0, 2},
    {8u, 0, 2},
    {10u, 0, 2},
    {1u, 0, -1},
    {2u, 0, -1},
    {16u, 0, -1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 2, -1},
};
static const comp_expression_rig_score_pose_t k_daily_down_step_7_poses[] = {
    {7u, 0, 2},
    {9u, 0, 2},
    {8u, 0, 2},
    {10u, 0, 2},
    {1u, 0, -1},
    {2u, 0, -1},
    {16u, 0, -1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 2, -2},
};
static const comp_expression_rig_score_pose_t k_daily_down_step_8_poses[] = {
    {7u, 0, 2},
    {9u, 0, 2},
    {8u, 0, 2},
    {10u, 0, 2},
    {1u, 0, -2},
    {2u, 0, -2},
    {16u, 0, -1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 2, -3},
};
static const comp_expression_rig_score_pose_t k_daily_down_step_9_poses[] = {
    {7u, 0, 2},
    {9u, 0, 2},
    {8u, 0, 2},
    {10u, 0, 2},
    {1u, 0, -2},
    {2u, 0, -2},
    {16u, 0, -1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 2, -3},
};
static const comp_expression_rig_score_pose_t k_daily_down_step_10_poses[] = {
    {7u, 0, 2},
    {9u, 0, 2},
    {8u, 0, 2},
    {10u, 0, 2},
    {1u, 0, -2},
    {2u, 0, -2},
    {16u, 0, -1},
    {13u, 0, -1},
    {14u, 0, -1},
    {19u, 2, -1},
};
static const comp_expression_rig_score_pose_t k_daily_down_step_11_poses[] = {
    {7u, 0, 2},
    {9u, 0, 2},
    {8u, 0, 2},
    {10u, 0, 2},
    {1u, 0, -1},
    {2u, 0, -1},
    {19u, 2, -1},
};
static const comp_expression_rig_score_pose_t k_daily_down_step_12_poses[] = {
    {7u, 0, 1},
    {9u, 0, 1},
    {8u, 0, 2},
    {10u, 0, 2},
};
static const comp_expression_rig_score_pose_t k_daily_down_step_13_poses[] = {
    {7u, 0, 1},
    {9u, 0, 1},
    {8u, 0, 1},
    {10u, 0, 1},
};

static const comp_expression_rig_score_step_t k_daily_down_steps[] = {
    {COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, 420u, NULL, 0u},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_PREPARE, 100u, k_daily_down_step_1_poses, (uint8_t)(sizeof(k_daily_down_step_1_poses) / sizeof(k_daily_down_step_1_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, 110u, k_daily_down_step_2_poses, (uint8_t)(sizeof(k_daily_down_step_2_poses) / sizeof(k_daily_down_step_2_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, 120u, k_daily_down_step_3_poses, (uint8_t)(sizeof(k_daily_down_step_3_poses) / sizeof(k_daily_down_step_3_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, 130u, k_daily_down_step_4_poses, (uint8_t)(sizeof(k_daily_down_step_4_poses) / sizeof(k_daily_down_step_4_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, 150u, k_daily_down_step_5_poses, (uint8_t)(sizeof(k_daily_down_step_5_poses) / sizeof(k_daily_down_step_5_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, 100u, k_daily_down_step_6_poses, (uint8_t)(sizeof(k_daily_down_step_6_poses) / sizeof(k_daily_down_step_6_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, 110u, k_daily_down_step_7_poses, (uint8_t)(sizeof(k_daily_down_step_7_poses) / sizeof(k_daily_down_step_7_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, 100u, k_daily_down_step_8_poses, (uint8_t)(sizeof(k_daily_down_step_8_poses) / sizeof(k_daily_down_step_8_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, 900u, k_daily_down_step_9_poses, (uint8_t)(sizeof(k_daily_down_step_9_poses) / sizeof(k_daily_down_step_9_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RELEASE, 120u, k_daily_down_step_10_poses, (uint8_t)(sizeof(k_daily_down_step_10_poses) / sizeof(k_daily_down_step_10_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RELEASE, 120u, k_daily_down_step_11_poses, (uint8_t)(sizeof(k_daily_down_step_11_poses) / sizeof(k_daily_down_step_11_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RETURN, 120u, k_daily_down_step_12_poses, (uint8_t)(sizeof(k_daily_down_step_12_poses) / sizeof(k_daily_down_step_12_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RETURN, 120u, k_daily_down_step_13_poses, (uint8_t)(sizeof(k_daily_down_step_13_poses) / sizeof(k_daily_down_step_13_poses[0]))},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_RETURN, 160u, NULL, 0u},
    {COMP_EXPRESSION_RIG_SCORE_PHASE_SETTLE, 640u, NULL, 0u},
};

static const comp_expression_rig_performance_score_t k_daily_down_score = {
    .steps = k_daily_down_steps,
    .step_count = (uint8_t)(sizeof(k_daily_down_steps) / sizeof(k_daily_down_steps[0])),
};

static const comp_expression_rig_attention_t k_v9_candidate_daily_presentation_order[] = {
    COMP_EXPRESSION_RIG_ATTENTION_LEFT, COMP_EXPRESSION_RIG_ATTENTION_RIGHT, COMP_EXPRESSION_RIG_ATTENTION_UP, COMP_EXPRESSION_RIG_ATTENTION_DOWN,
};

uint8_t comp_v9_expression_rig_candidate_daily_presentation_story_count(void)
{
    return (uint8_t)(sizeof(k_v9_candidate_daily_presentation_order) /
                     sizeof(k_v9_candidate_daily_presentation_order[0]));
}

bool comp_v9_expression_rig_candidate_daily_presentation_attention(
    uint8_t story_index,
    comp_expression_rig_attention_t *out_attention)
{
    if (out_attention == NULL ||
        story_index >= comp_v9_expression_rig_candidate_daily_presentation_story_count()) {
        return false;
    }
    *out_attention = k_v9_candidate_daily_presentation_order[story_index];
    return true;
}

const comp_expression_rig_performance_score_t *comp_v9_expression_rig_candidate_daily_score(
    comp_expression_rig_attention_t attention)
{
    switch (attention) {
    case COMP_EXPRESSION_RIG_ATTENTION_LEFT: return &k_daily_left_score;
    case COMP_EXPRESSION_RIG_ATTENTION_RIGHT: return &k_daily_right_score;
    case COMP_EXPRESSION_RIG_ATTENTION_UP: return &k_daily_up_score;
    case COMP_EXPRESSION_RIG_ATTENTION_DOWN: return &k_daily_down_score;
    case COMP_EXPRESSION_RIG_ATTENTION_CENTER:
    case COMP_EXPRESSION_RIG_ATTENTION_COUNT:
    default:
        return NULL;
    }
}
