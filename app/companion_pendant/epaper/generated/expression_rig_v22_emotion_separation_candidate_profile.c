/* Generated from the accepted V22 component bridge; do not hand edit. */
#include "expression_rig_v22_emotion_separation_candidate_profile.h"

static const comp_expression_rig_component_info_t k_v22_components[] = {
    {.component_id = 1u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_HIGHLIGHT, .variant = COMP_EXPRESSION_RIG_VARIANT_OPEN, .base_x = 42, .base_y = 112, .min_offset_x = -2, .min_offset_y = -3, .max_offset_x = 5, .max_offset_y = 4, .z_index = 31u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_ERASE},
    {.component_id = 2u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_EYE, .variant = COMP_EXPRESSION_RIG_VARIANT_OPEN, .base_x = 42, .base_y = 112, .min_offset_x = -3, .min_offset_y = -2, .max_offset_x = 3, .max_offset_y = 2, .z_index = 30u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 3u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_SPARKLE, .variant = COMP_EXPRESSION_RIG_VARIANT_OPEN, .base_x = 42, .base_y = 112, .min_offset_x = -6, .min_offset_y = -6, .max_offset_x = 5, .max_offset_y = 6, .z_index = 32u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_ERASE},
    {.component_id = 4u, .role = COMP_EXPRESSION_RIG_ROLE_NOSE, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 94, .base_y = 148, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 50u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 5u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_HIGHLIGHT, .variant = COMP_EXPRESSION_RIG_VARIANT_OPEN, .base_x = 125, .base_y = 112, .min_offset_x = -2, .min_offset_y = -3, .max_offset_x = 5, .max_offset_y = 4, .z_index = 31u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_ERASE},
    {.component_id = 6u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_EYE, .variant = COMP_EXPRESSION_RIG_VARIANT_OPEN, .base_x = 125, .base_y = 112, .min_offset_x = -3, .min_offset_y = -2, .max_offset_x = 3, .max_offset_y = 2, .z_index = 30u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 7u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_SPARKLE, .variant = COMP_EXPRESSION_RIG_VARIANT_OPEN, .base_x = 125, .base_y = 112, .min_offset_x = -6, .min_offset_y = -6, .max_offset_x = 5, .max_offset_y = 6, .z_index = 32u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_ERASE},
    {.component_id = 8u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 56, .base_y = 86, .min_offset_x = -1, .min_offset_y = -3, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 9u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_CHEEK, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 32, .base_y = 158, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 40u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 10u, .role = COMP_EXPRESSION_RIG_ROLE_MOUTH, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 91, .base_y = 159, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 60u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 11u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 118, .base_y = 83, .min_offset_x = -1, .min_offset_y = -3, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 12u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_CHEEK, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 153, .base_y = 158, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 40u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 13u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 45, .base_y = 86, .min_offset_x = -1, .min_offset_y = -3, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 14u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_CHEEK, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 33, .base_y = 158, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 40u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 15u, .role = COMP_EXPRESSION_RIG_ROLE_MOUTH, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 86, .base_y = 160, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 60u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 16u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 127, .base_y = 86, .min_offset_x = -1, .min_offset_y = -3, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 17u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_CHEEK, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 152, .base_y = 157, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 40u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 18u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 56, .base_y = 71, .min_offset_x = -1, .min_offset_y = -3, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 19u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_CHEEK, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 31, .base_y = 157, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 40u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 20u, .role = COMP_EXPRESSION_RIG_ROLE_MOUTH, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 92, .base_y = 160, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 60u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 21u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 124, .base_y = 90, .min_offset_x = -1, .min_offset_y = -3, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 22u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_CHEEK, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 152, .base_y = 154, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 40u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 23u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 162, .base_y = 146, .min_offset_x = 0, .min_offset_y = -2, .max_offset_x = 2, .max_offset_y = 1, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 24u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 53, .base_y = 85, .min_offset_x = -1, .min_offset_y = -3, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 25u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_CHEEK, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 31, .base_y = 155, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 40u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 26u, .role = COMP_EXPRESSION_RIG_ROLE_MOUTH, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 86, .base_y = 156, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 60u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 27u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 122, .base_y = 82, .min_offset_x = -1, .min_offset_y = -3, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 28u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_CHEEK, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 146, .base_y = 161, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 40u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 29u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 54, .base_y = 70, .min_offset_x = -1, .min_offset_y = -3, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 30u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_CHEEK, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 32, .base_y = 157, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 40u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 31u, .role = COMP_EXPRESSION_RIG_ROLE_MOUTH, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 96, .base_y = 163, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 60u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 32u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 122, .base_y = 97, .min_offset_x = -1, .min_offset_y = -3, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 33u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 49, .base_y = 85, .min_offset_x = -1, .min_offset_y = -3, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 34u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_CHEEK, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 32, .base_y = 155, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 40u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 35u, .role = COMP_EXPRESSION_RIG_ROLE_MOUTH, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 85, .base_y = 157, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 60u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 36u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 122, .base_y = 85, .min_offset_x = -1, .min_offset_y = -3, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 37u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_CHEEK, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 152, .base_y = 154, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 40u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
};

static const comp_expression_rig_profile_t k_v22_profile = {
    .components = k_v22_components,
    .component_count = COMP_V22_EMOTION_SEPARATION_RIG_CANDIDATE_COMPONENT_COUNT,
    .scene_charm_component = {
        [COMP_EXPRESSION_RIG_SCENE_DAILY] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,
        [COMP_EXPRESSION_RIG_SCENE_TOUCH] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,
        [COMP_EXPRESSION_RIG_SCENE_SWIPE] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,
        [COMP_EXPRESSION_RIG_SCENE_RECORDING] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,
        [COMP_EXPRESSION_RIG_SCENE_MENU] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,
        [COMP_EXPRESSION_RIG_SCENE_SLEEP] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,
        [COMP_EXPRESSION_RIG_SCENE_CHARGING] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,
        [COMP_EXPRESSION_RIG_SCENE_ERROR] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,
    },
    .registered_poses = NULL,
    .registered_pose_count = 0u,
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_0_frame_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 8u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 11u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 9u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 12u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 10u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_0_frame_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 8u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 11u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 9u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 12u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 10u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_0_frame_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 8u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 11u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 9u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 12u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 10u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_0_frame_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 29u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 32u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 9u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 12u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 10u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_0_frame_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 11u,
    .layers = {
            {.component_id = 29u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 32u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 30u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 31u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_0_frame_5_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 11u,
    .layers = {
            {.component_id = 29u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 32u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 30u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 31u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_0_frame_6_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 11u,
    .layers = {
            {.component_id = 29u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 32u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 30u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 31u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_v22_emotion_separation_rig_frame_t k_v22_bridge_0_frames[] = {
    {.cue = "source_hold", .source_phase = "entry", .target_pbm_filename = "alert__puzzled-00-source_hold.pbm", .duration_ms = 680u},
    {.cue = "primary_highlight_lead", .source_phase = "onset", .target_pbm_filename = "alert__puzzled-01-primary_highlight_lead.pbm", .duration_ms = 160u},
    {.cue = "sparkle_arrive", .source_phase = "onset", .target_pbm_filename = "alert__puzzled-02-sparkle_arrive.pbm", .duration_ms = 160u},
    {.cue = "brow_apex", .source_phase = "apex", .target_pbm_filename = "alert__puzzled-03-brow_apex.pbm", .duration_ms = 280u},
    {.cue = "lower_face_apex", .source_phase = "apex", .target_pbm_filename = "alert__puzzled-04-lower_face_apex.pbm", .duration_ms = 320u},
    {.cue = "target_hold", .source_phase = "hold", .target_pbm_filename = "alert__puzzled-05-target_hold.pbm", .duration_ms = 1800u},
    {.cue = "highlight_settle", .source_phase = "offset", .target_pbm_filename = "alert__puzzled-06-highlight_settle.pbm", .duration_ms = 360u},
};

static const comp_expression_rig_registered_score_step_t k_v22_bridge_0_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 680u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_0_frame_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_0_frame_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_0_frame_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 280u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_0_frame_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 320u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_0_frame_4_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 1800u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_0_frame_5_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_SETTLE, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_0_frame_6_pose},
};

static const comp_expression_rig_registered_performance_score_t k_v22_bridge_0_score = {
    .steps = k_v22_bridge_0_steps,
    .step_count = (uint8_t)(sizeof(k_v22_bridge_0_steps) / sizeof(k_v22_bridge_0_steps[0])),
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_1_frame_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_1_frame_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -1, .offset_y = -2, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -1, .offset_y = -2, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_1_frame_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -1, .offset_y = -2, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -1, .offset_y = -2, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -1, .offset_y = -2, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -1, .offset_y = -2, .dynamic_flags = 0u},
            {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_1_frame_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 18u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 21u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -1, .offset_y = -2, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -1, .offset_y = -2, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -1, .offset_y = -2, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -1, .offset_y = -2, .dynamic_flags = 0u},
            {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_1_frame_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 18u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 21u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -1, .offset_y = -2, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -1, .offset_y = -2, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -1, .offset_y = -2, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -1, .offset_y = -2, .dynamic_flags = 0u},
            {.component_id = 19u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 22u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 20u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_1_frame_5_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 18u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 21u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -1, .offset_y = -2, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -1, .offset_y = -2, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -1, .offset_y = -2, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -1, .offset_y = -2, .dynamic_flags = 0u},
            {.component_id = 19u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 22u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 20u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_1_frame_6_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 18u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 21u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 19u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 22u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 20u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_v22_emotion_separation_rig_frame_t k_v22_bridge_1_frames[] = {
    {.cue = "source_hold", .source_phase = "entry", .target_pbm_filename = "calm__curious-00-source_hold.pbm", .duration_ms = 680u},
    {.cue = "primary_highlight_lead", .source_phase = "onset", .target_pbm_filename = "calm__curious-01-primary_highlight_lead.pbm", .duration_ms = 160u},
    {.cue = "sparkle_arrive", .source_phase = "onset", .target_pbm_filename = "calm__curious-02-sparkle_arrive.pbm", .duration_ms = 160u},
    {.cue = "brow_apex", .source_phase = "apex", .target_pbm_filename = "calm__curious-03-brow_apex.pbm", .duration_ms = 280u},
    {.cue = "lower_face_apex", .source_phase = "apex", .target_pbm_filename = "calm__curious-04-lower_face_apex.pbm", .duration_ms = 320u},
    {.cue = "target_hold", .source_phase = "hold", .target_pbm_filename = "calm__curious-05-target_hold.pbm", .duration_ms = 1800u},
    {.cue = "highlight_settle", .source_phase = "offset", .target_pbm_filename = "calm__curious-06-highlight_settle.pbm", .duration_ms = 360u},
};

static const comp_expression_rig_registered_score_step_t k_v22_bridge_1_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 680u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_1_frame_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_1_frame_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_1_frame_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 280u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_1_frame_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 320u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_1_frame_4_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 1800u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_1_frame_5_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_SETTLE, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_1_frame_6_pose},
};

static const comp_expression_rig_registered_performance_score_t k_v22_bridge_1_score = {
    .steps = k_v22_bridge_1_steps,
    .step_count = (uint8_t)(sizeof(k_v22_bridge_1_steps) / sizeof(k_v22_bridge_1_steps[0])),
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_2_frame_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_2_frame_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_2_frame_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_2_frame_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 29u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 32u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_2_frame_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 11u,
    .layers = {
            {.component_id = 29u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 32u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 30u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 31u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_2_frame_5_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 11u,
    .layers = {
            {.component_id = 29u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 32u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -2, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 30u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 31u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_2_frame_6_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 11u,
    .layers = {
            {.component_id = 29u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 32u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 30u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 31u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_v22_emotion_separation_rig_frame_t k_v22_bridge_2_frames[] = {
    {.cue = "source_hold", .source_phase = "entry", .target_pbm_filename = "calm__puzzled-00-source_hold.pbm", .duration_ms = 680u},
    {.cue = "primary_highlight_lead", .source_phase = "onset", .target_pbm_filename = "calm__puzzled-01-primary_highlight_lead.pbm", .duration_ms = 160u},
    {.cue = "sparkle_arrive", .source_phase = "onset", .target_pbm_filename = "calm__puzzled-02-sparkle_arrive.pbm", .duration_ms = 160u},
    {.cue = "brow_apex", .source_phase = "apex", .target_pbm_filename = "calm__puzzled-03-brow_apex.pbm", .duration_ms = 280u},
    {.cue = "lower_face_apex", .source_phase = "apex", .target_pbm_filename = "calm__puzzled-04-lower_face_apex.pbm", .duration_ms = 320u},
    {.cue = "target_hold", .source_phase = "hold", .target_pbm_filename = "calm__puzzled-05-target_hold.pbm", .duration_ms = 1800u},
    {.cue = "highlight_settle", .source_phase = "offset", .target_pbm_filename = "calm__puzzled-06-highlight_settle.pbm", .duration_ms = 360u},
};

static const comp_expression_rig_registered_score_step_t k_v22_bridge_2_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 680u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_2_frame_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_2_frame_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_2_frame_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 280u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_2_frame_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 320u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_2_frame_4_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 1800u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_2_frame_5_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_SETTLE, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_2_frame_6_pose},
};

static const comp_expression_rig_registered_performance_score_t k_v22_bridge_2_score = {
    .steps = k_v22_bridge_2_steps,
    .step_count = (uint8_t)(sizeof(k_v22_bridge_2_steps) / sizeof(k_v22_bridge_2_steps[0])),
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_3_frame_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 18u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 21u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 19u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 22u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 20u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_3_frame_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 18u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 21u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 19u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 22u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 20u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_3_frame_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 18u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 21u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 19u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 22u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 20u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_3_frame_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 13u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 16u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 19u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 22u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 20u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_3_frame_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 14u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 17u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 15u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_3_frame_5_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_3_frame_6_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_v22_emotion_separation_rig_frame_t k_v22_bridge_3_frames[] = {
    {.cue = "source_hold", .source_phase = "entry", .target_pbm_filename = "curious__calm-00-source_hold.pbm", .duration_ms = 680u},
    {.cue = "primary_highlight_lead", .source_phase = "onset", .target_pbm_filename = "curious__calm-01-primary_highlight_lead.pbm", .duration_ms = 160u},
    {.cue = "sparkle_arrive", .source_phase = "onset", .target_pbm_filename = "curious__calm-02-sparkle_arrive.pbm", .duration_ms = 160u},
    {.cue = "brow_apex", .source_phase = "apex", .target_pbm_filename = "curious__calm-03-brow_apex.pbm", .duration_ms = 280u},
    {.cue = "lower_face_apex", .source_phase = "apex", .target_pbm_filename = "curious__calm-04-lower_face_apex.pbm", .duration_ms = 320u},
    {.cue = "target_hold", .source_phase = "hold", .target_pbm_filename = "curious__calm-05-target_hold.pbm", .duration_ms = 1800u},
    {.cue = "highlight_settle", .source_phase = "offset", .target_pbm_filename = "curious__calm-06-highlight_settle.pbm", .duration_ms = 360u},
};

static const comp_expression_rig_registered_score_step_t k_v22_bridge_3_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 680u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_3_frame_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_3_frame_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_3_frame_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 280u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_3_frame_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 320u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_3_frame_4_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 1800u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_3_frame_5_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_SETTLE, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_3_frame_6_pose},
};

static const comp_expression_rig_registered_performance_score_t k_v22_bridge_3_score = {
    .steps = k_v22_bridge_3_steps,
    .step_count = (uint8_t)(sizeof(k_v22_bridge_3_steps) / sizeof(k_v22_bridge_3_steps[0])),
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_4_frame_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 18u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 21u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 19u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 22u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 20u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_4_frame_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 18u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 21u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 19u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 22u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 20u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_4_frame_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 18u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 21u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 19u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 22u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 20u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_4_frame_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 33u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 36u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 19u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 22u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 20u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_4_frame_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 33u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 36u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 34u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 37u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 35u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_4_frame_5_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 33u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 36u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 34u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 37u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 35u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_4_frame_6_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 33u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 36u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 34u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 37u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 35u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_v22_emotion_separation_rig_frame_t k_v22_bridge_4_frames[] = {
    {.cue = "source_hold", .source_phase = "entry", .target_pbm_filename = "curious__warm-00-source_hold.pbm", .duration_ms = 680u},
    {.cue = "primary_highlight_lead", .source_phase = "onset", .target_pbm_filename = "curious__warm-01-primary_highlight_lead.pbm", .duration_ms = 160u},
    {.cue = "sparkle_arrive", .source_phase = "onset", .target_pbm_filename = "curious__warm-02-sparkle_arrive.pbm", .duration_ms = 160u},
    {.cue = "brow_apex", .source_phase = "apex", .target_pbm_filename = "curious__warm-03-brow_apex.pbm", .duration_ms = 280u},
    {.cue = "lower_face_apex", .source_phase = "apex", .target_pbm_filename = "curious__warm-04-lower_face_apex.pbm", .duration_ms = 320u},
    {.cue = "target_hold", .source_phase = "hold", .target_pbm_filename = "curious__warm-05-target_hold.pbm", .duration_ms = 1800u},
    {.cue = "highlight_settle", .source_phase = "offset", .target_pbm_filename = "curious__warm-06-highlight_settle.pbm", .duration_ms = 360u},
};

static const comp_expression_rig_registered_score_step_t k_v22_bridge_4_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 680u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_4_frame_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_4_frame_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_4_frame_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 280u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_4_frame_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 320u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_4_frame_4_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 1800u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_4_frame_5_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_SETTLE, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_4_frame_6_pose},
};

static const comp_expression_rig_registered_performance_score_t k_v22_bridge_4_score = {
    .steps = k_v22_bridge_4_steps,
    .step_count = (uint8_t)(sizeof(k_v22_bridge_4_steps) / sizeof(k_v22_bridge_4_steps[0])),
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_5_frame_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 13u,
    .layers = {
            {.component_id = 23u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 24u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 27u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 25u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 28u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 26u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_5_frame_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 13u,
    .layers = {
            {.component_id = 23u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 24u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 27u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 25u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 28u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 26u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_5_frame_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 13u,
    .layers = {
            {.component_id = 23u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 24u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 27u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 25u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 28u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 26u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_5_frame_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 13u,
    .layers = {
            {.component_id = 23u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 33u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 36u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 25u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 28u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 26u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_5_frame_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 13u,
    .layers = {
            {.component_id = 23u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 33u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 36u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 34u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 37u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 35u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_5_frame_5_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 33u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 36u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 34u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 37u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 35u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_5_frame_6_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 33u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 36u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -1, .offset_y = 1, .dynamic_flags = 0u},
            {.component_id = 34u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 37u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 35u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_5_frame_7_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 33u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 36u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 34u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 37u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 35u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_v22_emotion_separation_rig_frame_t k_v22_bridge_5_frames[] = {
    {.cue = "source_hold", .source_phase = "entry", .target_pbm_filename = "playful__warm-00-source_hold.pbm", .duration_ms = 680u},
    {.cue = "primary_highlight_lead", .source_phase = "onset", .target_pbm_filename = "playful__warm-01-primary_highlight_lead.pbm", .duration_ms = 160u},
    {.cue = "sparkle_arrive", .source_phase = "onset", .target_pbm_filename = "playful__warm-02-sparkle_arrive.pbm", .duration_ms = 160u},
    {.cue = "brow_apex", .source_phase = "apex", .target_pbm_filename = "playful__warm-03-brow_apex.pbm", .duration_ms = 280u},
    {.cue = "lower_face_apex", .source_phase = "apex", .target_pbm_filename = "playful__warm-04-lower_face_apex.pbm", .duration_ms = 320u},
    {.cue = "accent_resolve", .source_phase = "apex", .target_pbm_filename = "playful__warm-05-accent_resolve.pbm", .duration_ms = 240u},
    {.cue = "target_hold", .source_phase = "hold", .target_pbm_filename = "playful__warm-06-target_hold.pbm", .duration_ms = 1800u},
    {.cue = "highlight_settle", .source_phase = "offset", .target_pbm_filename = "playful__warm-07-highlight_settle.pbm", .duration_ms = 360u},
};

static const comp_expression_rig_registered_score_step_t k_v22_bridge_5_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 680u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_5_frame_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_5_frame_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_5_frame_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 280u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_5_frame_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 320u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_5_frame_4_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, .duration_ms = 240u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_5_frame_5_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 1800u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_5_frame_6_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_SETTLE, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_5_frame_7_pose},
};

static const comp_expression_rig_registered_performance_score_t k_v22_bridge_5_score = {
    .steps = k_v22_bridge_5_steps,
    .step_count = (uint8_t)(sizeof(k_v22_bridge_5_steps) / sizeof(k_v22_bridge_5_steps[0])),
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_6_frame_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 11u,
    .layers = {
            {.component_id = 29u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 32u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 30u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 31u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_6_frame_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 11u,
    .layers = {
            {.component_id = 29u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 32u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 30u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 31u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_6_frame_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 11u,
    .layers = {
            {.component_id = 29u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 32u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 30u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 31u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_6_frame_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 11u,
    .layers = {
            {.component_id = 8u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 11u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 30u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 31u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_6_frame_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 8u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 11u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 9u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 12u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 10u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_6_frame_5_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 8u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 11u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 9u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 12u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 10u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_6_frame_6_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 8u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 11u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 9u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 12u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 10u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_v22_emotion_separation_rig_frame_t k_v22_bridge_6_frames[] = {
    {.cue = "source_hold", .source_phase = "entry", .target_pbm_filename = "puzzled__alert-00-source_hold.pbm", .duration_ms = 680u},
    {.cue = "primary_highlight_lead", .source_phase = "onset", .target_pbm_filename = "puzzled__alert-01-primary_highlight_lead.pbm", .duration_ms = 160u},
    {.cue = "sparkle_arrive", .source_phase = "onset", .target_pbm_filename = "puzzled__alert-02-sparkle_arrive.pbm", .duration_ms = 160u},
    {.cue = "brow_apex", .source_phase = "apex", .target_pbm_filename = "puzzled__alert-03-brow_apex.pbm", .duration_ms = 280u},
    {.cue = "lower_face_apex", .source_phase = "apex", .target_pbm_filename = "puzzled__alert-04-lower_face_apex.pbm", .duration_ms = 320u},
    {.cue = "target_hold", .source_phase = "hold", .target_pbm_filename = "puzzled__alert-05-target_hold.pbm", .duration_ms = 1800u},
    {.cue = "highlight_settle", .source_phase = "offset", .target_pbm_filename = "puzzled__alert-06-highlight_settle.pbm", .duration_ms = 360u},
};

static const comp_expression_rig_registered_score_step_t k_v22_bridge_6_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 680u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_6_frame_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_6_frame_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_6_frame_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 280u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_6_frame_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 320u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_6_frame_4_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 1800u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_6_frame_5_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_SETTLE, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_6_frame_6_pose},
};

static const comp_expression_rig_registered_performance_score_t k_v22_bridge_6_score = {
    .steps = k_v22_bridge_6_steps,
    .step_count = (uint8_t)(sizeof(k_v22_bridge_6_steps) / sizeof(k_v22_bridge_6_steps[0])),
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_7_frame_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 11u,
    .layers = {
            {.component_id = 29u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 32u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 30u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 31u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_7_frame_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 11u,
    .layers = {
            {.component_id = 29u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 32u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 30u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 31u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_7_frame_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 11u,
    .layers = {
            {.component_id = 29u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 32u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 30u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 31u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_7_frame_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 11u,
    .layers = {
            {.component_id = 13u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 16u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 30u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 31u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_7_frame_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 14u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 17u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 15u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_7_frame_5_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 2, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_7_frame_6_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_v22_emotion_separation_rig_frame_t k_v22_bridge_7_frames[] = {
    {.cue = "source_hold", .source_phase = "entry", .target_pbm_filename = "puzzled__calm-00-source_hold.pbm", .duration_ms = 680u},
    {.cue = "primary_highlight_lead", .source_phase = "onset", .target_pbm_filename = "puzzled__calm-01-primary_highlight_lead.pbm", .duration_ms = 160u},
    {.cue = "sparkle_arrive", .source_phase = "onset", .target_pbm_filename = "puzzled__calm-02-sparkle_arrive.pbm", .duration_ms = 160u},
    {.cue = "brow_apex", .source_phase = "apex", .target_pbm_filename = "puzzled__calm-03-brow_apex.pbm", .duration_ms = 280u},
    {.cue = "lower_face_apex", .source_phase = "apex", .target_pbm_filename = "puzzled__calm-04-lower_face_apex.pbm", .duration_ms = 320u},
    {.cue = "target_hold", .source_phase = "hold", .target_pbm_filename = "puzzled__calm-05-target_hold.pbm", .duration_ms = 1800u},
    {.cue = "highlight_settle", .source_phase = "offset", .target_pbm_filename = "puzzled__calm-06-highlight_settle.pbm", .duration_ms = 360u},
};

static const comp_expression_rig_registered_score_step_t k_v22_bridge_7_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 680u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_7_frame_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_7_frame_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_7_frame_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 280u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_7_frame_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 320u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_7_frame_4_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 1800u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_7_frame_5_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_SETTLE, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PUZZLED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_7_frame_6_pose},
};

static const comp_expression_rig_registered_performance_score_t k_v22_bridge_7_score = {
    .steps = k_v22_bridge_7_steps,
    .step_count = (uint8_t)(sizeof(k_v22_bridge_7_steps) / sizeof(k_v22_bridge_7_steps[0])),
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_8_frame_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 33u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 36u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 34u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 37u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 35u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_8_frame_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 33u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 36u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 34u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 37u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 35u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_8_frame_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 33u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 36u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 34u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 37u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 35u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_8_frame_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 18u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 21u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 34u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 37u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 35u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_8_frame_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 18u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 21u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 19u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 22u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 20u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_8_frame_5_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 18u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 21u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = -2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = -2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = -2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = -2, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 19u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 22u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 20u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_8_frame_6_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 18u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 21u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 19u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 22u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 20u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_v22_emotion_separation_rig_frame_t k_v22_bridge_8_frames[] = {
    {.cue = "source_hold", .source_phase = "entry", .target_pbm_filename = "warm__curious-00-source_hold.pbm", .duration_ms = 680u},
    {.cue = "primary_highlight_lead", .source_phase = "onset", .target_pbm_filename = "warm__curious-01-primary_highlight_lead.pbm", .duration_ms = 160u},
    {.cue = "sparkle_arrive", .source_phase = "onset", .target_pbm_filename = "warm__curious-02-sparkle_arrive.pbm", .duration_ms = 160u},
    {.cue = "brow_apex", .source_phase = "apex", .target_pbm_filename = "warm__curious-03-brow_apex.pbm", .duration_ms = 280u},
    {.cue = "lower_face_apex", .source_phase = "apex", .target_pbm_filename = "warm__curious-04-lower_face_apex.pbm", .duration_ms = 320u},
    {.cue = "target_hold", .source_phase = "hold", .target_pbm_filename = "warm__curious-05-target_hold.pbm", .duration_ms = 1800u},
    {.cue = "highlight_settle", .source_phase = "offset", .target_pbm_filename = "warm__curious-06-highlight_settle.pbm", .duration_ms = 360u},
};

static const comp_expression_rig_registered_score_step_t k_v22_bridge_8_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 680u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_8_frame_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_8_frame_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_8_frame_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 280u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_8_frame_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 320u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_8_frame_4_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 1800u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_8_frame_5_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_SETTLE, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_8_frame_6_pose},
};

static const comp_expression_rig_registered_performance_score_t k_v22_bridge_8_score = {
    .steps = k_v22_bridge_8_steps,
    .step_count = (uint8_t)(sizeof(k_v22_bridge_8_steps) / sizeof(k_v22_bridge_8_steps[0])),
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_9_frame_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 33u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 36u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 34u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 37u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 35u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_9_frame_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 33u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 36u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 34u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 37u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 35u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_9_frame_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 33u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 36u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 34u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 37u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 35u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_9_frame_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 24u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 27u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 34u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 37u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 35u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_9_frame_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u,
    .layers = {
            {.component_id = 24u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 27u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 25u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 28u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 26u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_9_frame_5_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 13u,
    .layers = {
            {.component_id = 23u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 24u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 27u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 25u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 28u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 26u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_9_frame_6_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 13u,
    .layers = {
            {.component_id = 23u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 24u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 27u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 1, .offset_y = -1, .dynamic_flags = 0u},
            {.component_id = 25u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 28u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 26u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v22_bridge_9_frame_7_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
    .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 13u,
    .layers = {
            {.component_id = 23u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 24u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 27u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 1u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 5u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 3u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 7u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 25u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 28u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
            {.component_id = 26u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_v22_emotion_separation_rig_frame_t k_v22_bridge_9_frames[] = {
    {.cue = "source_hold", .source_phase = "entry", .target_pbm_filename = "warm__playful-00-source_hold.pbm", .duration_ms = 680u},
    {.cue = "primary_highlight_lead", .source_phase = "onset", .target_pbm_filename = "warm__playful-01-primary_highlight_lead.pbm", .duration_ms = 160u},
    {.cue = "sparkle_arrive", .source_phase = "onset", .target_pbm_filename = "warm__playful-02-sparkle_arrive.pbm", .duration_ms = 160u},
    {.cue = "brow_apex", .source_phase = "apex", .target_pbm_filename = "warm__playful-03-brow_apex.pbm", .duration_ms = 280u},
    {.cue = "lower_face_apex", .source_phase = "apex", .target_pbm_filename = "warm__playful-04-lower_face_apex.pbm", .duration_ms = 320u},
    {.cue = "accent_resolve", .source_phase = "apex", .target_pbm_filename = "warm__playful-05-accent_resolve.pbm", .duration_ms = 240u},
    {.cue = "target_hold", .source_phase = "hold", .target_pbm_filename = "warm__playful-06-target_hold.pbm", .duration_ms = 1800u},
    {.cue = "highlight_settle", .source_phase = "offset", .target_pbm_filename = "warm__playful-07-highlight_settle.pbm", .duration_ms = 360u},
};

static const comp_expression_rig_registered_score_step_t k_v22_bridge_9_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 680u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_9_frame_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_9_frame_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_9_frame_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 280u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_9_frame_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 320u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_9_frame_4_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, .duration_ms = 240u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_9_frame_5_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 1800u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_9_frame_6_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_SETTLE, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v22_bridge_9_frame_7_pose},
};

static const comp_expression_rig_registered_performance_score_t k_v22_bridge_9_score = {
    .steps = k_v22_bridge_9_steps,
    .step_count = (uint8_t)(sizeof(k_v22_bridge_9_steps) / sizeof(k_v22_bridge_9_steps[0])),
};

static const comp_v22_emotion_separation_rig_bridge_t k_v22_bridges[] = {
    {.name = "alert__puzzled", .source_emotion = "alert", .target_emotion = "puzzled", .event_name = "salience_reduced", .score = &k_v22_bridge_0_score, .frames = k_v22_bridge_0_frames, .frame_count = (uint8_t)(sizeof(k_v22_bridge_0_frames) / sizeof(k_v22_bridge_0_frames[0]))},
    {.name = "calm__curious", .source_emotion = "calm", .target_emotion = "curious", .event_name = "attention_novelty", .score = &k_v22_bridge_1_score, .frames = k_v22_bridge_1_frames, .frame_count = (uint8_t)(sizeof(k_v22_bridge_1_frames) / sizeof(k_v22_bridge_1_frames[0]))},
    {.name = "calm__puzzled", .source_emotion = "calm", .target_emotion = "puzzled", .event_name = "ambiguous_input", .score = &k_v22_bridge_2_score, .frames = k_v22_bridge_2_frames, .frame_count = (uint8_t)(sizeof(k_v22_bridge_2_frames) / sizeof(k_v22_bridge_2_frames[0]))},
    {.name = "curious__calm", .source_emotion = "curious", .target_emotion = "calm", .event_name = "novelty_resolved", .score = &k_v22_bridge_3_score, .frames = k_v22_bridge_3_frames, .frame_count = (uint8_t)(sizeof(k_v22_bridge_3_frames) / sizeof(k_v22_bridge_3_frames[0]))},
    {.name = "curious__warm", .source_emotion = "curious", .target_emotion = "warm", .event_name = "positive_reciprocity", .score = &k_v22_bridge_4_score, .frames = k_v22_bridge_4_frames, .frame_count = (uint8_t)(sizeof(k_v22_bridge_4_frames) / sizeof(k_v22_bridge_4_frames[0]))},
    {.name = "playful__warm", .source_emotion = "playful", .target_emotion = "warm", .event_name = "energy_settle", .score = &k_v22_bridge_5_score, .frames = k_v22_bridge_5_frames, .frame_count = (uint8_t)(sizeof(k_v22_bridge_5_frames) / sizeof(k_v22_bridge_5_frames[0]))},
    {.name = "puzzled__alert", .source_emotion = "puzzled", .target_emotion = "alert", .event_name = "high_salience", .score = &k_v22_bridge_6_score, .frames = k_v22_bridge_6_frames, .frame_count = (uint8_t)(sizeof(k_v22_bridge_6_frames) / sizeof(k_v22_bridge_6_frames[0]))},
    {.name = "puzzled__calm", .source_emotion = "puzzled", .target_emotion = "calm", .event_name = "ambiguity_resolved", .score = &k_v22_bridge_7_score, .frames = k_v22_bridge_7_frames, .frame_count = (uint8_t)(sizeof(k_v22_bridge_7_frames) / sizeof(k_v22_bridge_7_frames[0]))},
    {.name = "warm__curious", .source_emotion = "warm", .target_emotion = "curious", .event_name = "attention_shift", .score = &k_v22_bridge_8_score, .frames = k_v22_bridge_8_frames, .frame_count = (uint8_t)(sizeof(k_v22_bridge_8_frames) / sizeof(k_v22_bridge_8_frames[0]))},
    {.name = "warm__playful", .source_emotion = "warm", .target_emotion = "playful", .event_name = "shared_play", .score = &k_v22_bridge_9_score, .frames = k_v22_bridge_9_frames, .frame_count = (uint8_t)(sizeof(k_v22_bridge_9_frames) / sizeof(k_v22_bridge_9_frames[0]))},
};

const comp_expression_rig_profile_t *comp_v22_emotion_separation_rig_candidate_profile(void)
{
    return &k_v22_profile;
}

bool comp_v22_emotion_separation_rig_candidate_runtime_activation_allowed(void)
{
    return false;
}

uint8_t comp_v22_emotion_separation_rig_candidate_bridge_count(void)
{
    return (uint8_t)(sizeof(k_v22_bridges) / sizeof(k_v22_bridges[0]));
}

const comp_v22_emotion_separation_rig_bridge_t *comp_v22_emotion_separation_rig_candidate_bridge(uint8_t index)
{
    if (index >= comp_v22_emotion_separation_rig_candidate_bridge_count()) {
        return NULL;
    }
    return &k_v22_bridges[index];
}
