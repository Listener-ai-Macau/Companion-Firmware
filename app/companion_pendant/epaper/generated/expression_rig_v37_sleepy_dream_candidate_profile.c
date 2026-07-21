/* Generated from V22/V34/V35 and locked V9 sleep source components; do not hand edit. */
#include "expression_rig_v37_sleepy_dream_candidate_profile.h"

static const comp_expression_rig_component_info_t k_v37_components[] = {
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
    {.component_id = 500u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 182, .base_y = 127, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 501u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 182, .base_y = 127, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 502u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 168, .base_y = 130, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 503u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 182, .base_y = 127, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 504u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 163, .base_y = 130, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 505u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 170, .base_y = 127, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 506u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 79, .base_y = 172, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 507u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 79, .base_y = 172, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 508u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 96, .base_y = 168, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 509u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 79, .base_y = 172, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 510u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 92, .base_y = 163, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 511u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 95, .base_y = 168, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 512u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 148, .base_y = 38, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 513u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 145, .base_y = 34, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 514u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 142, .base_y = 29, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 515u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 142, .base_y = 29, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 516u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 143, .base_y = 31, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 517u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 145, .base_y = 34, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 518u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 145, .base_y = 34, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 519u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 143, .base_y = 31, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 520u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 142, .base_y = 29, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 521u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 99, .base_y = 42, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 522u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 96, .base_y = 35, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 523u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 94, .base_y = 25, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 524u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 94, .base_y = 25, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 525u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 95, .base_y = 28, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 526u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 96, .base_y = 35, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 527u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 96, .base_y = 35, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 528u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 95, .base_y = 28, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 529u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 94, .base_y = 25, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 530u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 40, .base_y = 41, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 531u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 33, .base_y = 35, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 532u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 27, .base_y = 30, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 533u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 27, .base_y = 30, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 534u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 29, .base_y = 32, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 535u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 33, .base_y = 35, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 536u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 33, .base_y = 35, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 537u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 29, .base_y = 32, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 538u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 27, .base_y = 30, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 539u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 48, .base_y = 91, .min_offset_x = -1, .min_offset_y = -1, .max_offset_x = 1, .max_offset_y = 2, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 540u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 131, .base_y = 91, .min_offset_x = -1, .min_offset_y = -1, .max_offset_x = 1, .max_offset_y = 2, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 541u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 43, .base_y = 130, .min_offset_x = -2, .min_offset_y = 0, .max_offset_x = 2, .max_offset_y = 2, .z_index = 30u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 542u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 124, .base_y = 130, .min_offset_x = -2, .min_offset_y = 0, .max_offset_x = 2, .max_offset_y = 2, .z_index = 30u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 543u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 86, .base_y = 160, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 60u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 544u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 72, .base_y = 27, .min_offset_x = 0, .min_offset_y = -3, .max_offset_x = 2, .max_offset_y = 1, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
};

static const comp_expression_rig_profile_t k_v37_profile = {
    .components = k_v37_components,
    .component_count = COMP_V37_SLEEPY_DREAM_CANDIDATE_COMPONENT_COUNT,
    .scene_charm_component = {[COMP_EXPRESSION_RIG_SCENE_DAILY] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_TOUCH] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_SWIPE] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_RECORDING] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_MENU] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_SLEEP] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_CHARGING] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_ERROR] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID},
    .registered_poses = NULL, .registered_pose_count = 0u,
};

static const comp_expression_rig_registered_pose_t k_v37_score_0_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_RECORDING, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .layer_count = 13u, .layers = {
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
        {.component_id = 500u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v37_score_0_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_RECORDING, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .layer_count = 14u, .layers = {
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
        {.component_id = 501u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 502u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v37_score_0_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_RECORDING, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .layer_count = 15u, .layers = {
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
        {.component_id = 503u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 504u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 505u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v37_score_0_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 700u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_RECORDING, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v37_score_0_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 420u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_RECORDING, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v37_score_0_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 420u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_RECORDING, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v37_score_0_step_2_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v37_score_0 = {.steps = k_v37_score_0_steps, .step_count = (uint8_t)(sizeof(k_v37_score_0_steps) / sizeof(k_v37_score_0_steps[0]))};
static const comp_v37_sleepy_dream_candidate_frame_t k_v37_score_0_frames[] = {
    {.cue = "source_hold", .browser_pbm_filename = "recording_input-00-source_hold.pbm", .duration_ms = 700u},
    {.cue = "primary_highlight_lead", .browser_pbm_filename = "recording_input-01-primary_highlight_lead.pbm", .duration_ms = 420u},
    {.cue = "sparkle_arrive", .browser_pbm_filename = "recording_input-02-sparkle_arrive.pbm", .duration_ms = 420u},
};

static const comp_expression_rig_registered_pose_t k_v37_score_1_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_CHARGING, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .layer_count = 13u, .layers = {
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
        {.component_id = 506u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v37_score_1_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_CHARGING, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .layer_count = 14u, .layers = {
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
        {.component_id = 507u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 508u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v37_score_1_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_CHARGING, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .layer_count = 15u, .layers = {
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
        {.component_id = 509u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 510u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 511u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v37_score_1_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 700u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_CHARGING, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v37_score_1_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 420u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_CHARGING, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v37_score_1_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 420u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_CHARGING, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v37_score_1_step_2_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v37_score_1 = {.steps = k_v37_score_1_steps, .step_count = (uint8_t)(sizeof(k_v37_score_1_steps) / sizeof(k_v37_score_1_steps[0]))};
static const comp_v37_sleepy_dream_candidate_frame_t k_v37_score_1_frames[] = {
    {.cue = "source_hold", .browser_pbm_filename = "bottom_connector_charging-00-source_hold.pbm", .duration_ms = 700u},
    {.cue = "primary_highlight_lead", .browser_pbm_filename = "bottom_connector_charging-01-primary_highlight_lead.pbm", .duration_ms = 420u},
    {.cue = "sparkle_arrive", .browser_pbm_filename = "bottom_connector_charging-02-sparkle_arrive.pbm", .duration_ms = 420u},
};

static const comp_expression_rig_registered_pose_t k_v37_score_2_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .layer_count = 13u, .layers = {
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
        {.component_id = 512u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v37_score_2_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .layer_count = 13u, .layers = {
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
        {.component_id = 513u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v37_score_2_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .layer_count = 13u, .layers = {
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
        {.component_id = 514u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v37_score_2_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v37_score_2_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 240u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v37_score_2_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 960u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v37_score_2_step_2_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v37_score_2 = {.steps = k_v37_score_2_steps, .step_count = (uint8_t)(sizeof(k_v37_score_2_steps) / sizeof(k_v37_score_2_steps[0]))};
static const comp_v37_sleepy_dream_candidate_frame_t k_v37_score_2_frames[] = {
    {.cue = "source_hold", .browser_pbm_filename = "curious_question-00-source_hold.pbm", .duration_ms = 160u},
    {.cue = "primary_highlight_lead", .browser_pbm_filename = "curious_question-01-primary_highlight_lead.pbm", .duration_ms = 240u},
    {.cue = "sparkle_arrive", .browser_pbm_filename = "curious_question-02-sparkle_arrive.pbm", .duration_ms = 960u},
};

static const comp_expression_rig_registered_pose_t k_v37_score_3_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .layer_count = 12u, .layers = {
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
        {.component_id = 521u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v37_score_3_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .layer_count = 12u, .layers = {
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
        {.component_id = 522u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v37_score_3_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .layer_count = 12u, .layers = {
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
        {.component_id = 523u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v37_score_3_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 160u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v37_score_3_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 240u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v37_score_3_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 960u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v37_score_3_step_2_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v37_score_3 = {.steps = k_v37_score_3_steps, .step_count = (uint8_t)(sizeof(k_v37_score_3_steps) / sizeof(k_v37_score_3_steps[0]))};
static const comp_v37_sleepy_dream_candidate_frame_t k_v37_score_3_frames[] = {
    {.cue = "source_hold", .browser_pbm_filename = "alert_exclamation-00-source_hold.pbm", .duration_ms = 160u},
    {.cue = "primary_highlight_lead", .browser_pbm_filename = "alert_exclamation-01-primary_highlight_lead.pbm", .duration_ms = 240u},
    {.cue = "sparkle_arrive", .browser_pbm_filename = "alert_exclamation-02-sparkle_arrive.pbm", .duration_ms = 960u},
};

static const comp_expression_rig_registered_pose_t k_v37_score_4_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_SLEEP, .emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .layer_count = 12u, .layers = {
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

static const comp_expression_rig_registered_pose_t k_v37_score_4_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_SLEEP, .emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .layer_count = 8u, .layers = {
        {.component_id = 539u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 540u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 541u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 542u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 543u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v37_score_4_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_SLEEP, .emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .layer_count = 9u, .layers = {
        {.component_id = 539u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 540u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 541u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 542u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 543u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 544u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v37_score_4_step_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_SLEEP, .emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .layer_count = 10u, .layers = {
        {.component_id = 539u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 540u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 541u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 542u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 543u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 544u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 531u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v37_score_4_step_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_SLEEP, .emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .layer_count = 10u, .layers = {
        {.component_id = 539u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 540u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 541u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 542u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 543u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 544u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 532u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v37_score_4_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 420u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_SLEEP, .emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v37_score_4_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_SLEEP, .emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v37_score_4_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 320u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_SLEEP, .emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v37_score_4_step_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, .duration_ms = 420u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_SLEEP, .emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v37_score_4_step_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 1400u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_SLEEP, .emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v37_score_4_step_4_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v37_score_4 = {.steps = k_v37_score_4_steps, .step_count = (uint8_t)(sizeof(k_v37_score_4_steps) / sizeof(k_v37_score_4_steps[0]))};
static const comp_v37_sleepy_dream_candidate_frame_t k_v37_score_4_frames[] = {
    {.cue = "source_hold", .browser_pbm_filename = "sleepy_dream_cloud-00-source_hold.pbm", .duration_ms = 420u},
    {.cue = "eyes_soften", .browser_pbm_filename = "sleepy_dream_cloud-01-eyes_soften.pbm", .duration_ms = 360u},
    {.cue = "lower_face_arrive", .browser_pbm_filename = "sleepy_dream_cloud-02-lower_face_arrive.pbm", .duration_ms = 320u},
    {.cue = "dream_lift", .browser_pbm_filename = "sleepy_dream_cloud-03-dream_lift.pbm", .duration_ms = 420u},
    {.cue = "sleep_hold", .browser_pbm_filename = "sleepy_dream_cloud-04-sleep_hold.pbm", .duration_ms = 1400u},
};

static const comp_v37_sleepy_dream_candidate_score_t k_v37_scores[] = {
    {.name = "recording_input", .prelude_bridge = "calm__curious", .score = &k_v37_score_0, .frames = k_v37_score_0_frames, .frame_count = (uint8_t)(sizeof(k_v37_score_0_frames) / sizeof(k_v37_score_0_frames[0]))},
    {.name = "bottom_connector_charging", .prelude_bridge = "curious__warm", .score = &k_v37_score_1, .frames = k_v37_score_1_frames, .frame_count = (uint8_t)(sizeof(k_v37_score_1_frames) / sizeof(k_v37_score_1_frames[0]))},
    {.name = "curious_question", .prelude_bridge = "calm__curious", .score = &k_v37_score_2, .frames = k_v37_score_2_frames, .frame_count = (uint8_t)(sizeof(k_v37_score_2_frames) / sizeof(k_v37_score_2_frames[0]))},
    {.name = "alert_exclamation", .prelude_bridge = "puzzled__alert", .score = &k_v37_score_3, .frames = k_v37_score_3_frames, .frame_count = (uint8_t)(sizeof(k_v37_score_3_frames) / sizeof(k_v37_score_3_frames[0]))},
    {.name = "sleepy_dream_cloud", .prelude_bridge = "daily_calm_to_sleepy_component_entry", .score = &k_v37_score_4, .frames = k_v37_score_4_frames, .frame_count = (uint8_t)(sizeof(k_v37_score_4_frames) / sizeof(k_v37_score_4_frames[0]))},
};

const comp_expression_rig_profile_t *comp_v37_sleepy_dream_candidate_profile(void) { return &k_v37_profile; }
bool comp_v37_sleepy_dream_candidate_runtime_activation_allowed(void) { return false; }
uint8_t comp_v37_sleepy_dream_candidate_score_count(void) { return (uint8_t)(sizeof(k_v37_scores) / sizeof(k_v37_scores[0])); }
const comp_v37_sleepy_dream_candidate_score_t *comp_v37_sleepy_dream_candidate_score(uint8_t index) { return index < comp_v37_sleepy_dream_candidate_score_count() ? &k_v37_scores[index] : NULL; }
