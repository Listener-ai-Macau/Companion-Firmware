/* Generated from the versioned V43 expression-extension layout; do not hand edit. */
#include "expression_rig_v43_recording_input_inward_candidate_profile.h"
#include "expression_rig_track_composer.h"

static const comp_expression_rig_component_info_t k_v43_components[] = {
    {.component_id = 1u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_HIGHLIGHT, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 42, .base_y = 112, .min_offset_x = -2, .min_offset_y = -3, .max_offset_x = 5, .max_offset_y = 4, .z_index = 31u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_ERASE},
    {.component_id = 2u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_EYE, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 42, .base_y = 112, .min_offset_x = -3, .min_offset_y = -2, .max_offset_x = 3, .max_offset_y = 2, .z_index = 30u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 3u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_SPARKLE, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 42, .base_y = 112, .min_offset_x = -6, .min_offset_y = -6, .max_offset_x = 5, .max_offset_y = 6, .z_index = 32u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_ERASE},
    {.component_id = 4u, .role = COMP_EXPRESSION_RIG_ROLE_NOSE, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 94, .base_y = 148, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 50u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 5u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_HIGHLIGHT, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 125, .base_y = 112, .min_offset_x = -2, .min_offset_y = -3, .max_offset_x = 5, .max_offset_y = 4, .z_index = 31u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_ERASE},
    {.component_id = 6u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_EYE, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 125, .base_y = 112, .min_offset_x = -3, .min_offset_y = -2, .max_offset_x = 3, .max_offset_y = 2, .z_index = 30u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 7u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_SPARKLE, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 125, .base_y = 112, .min_offset_x = -6, .min_offset_y = -6, .max_offset_x = 5, .max_offset_y = 6, .z_index = 32u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_ERASE},
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
    {.component_id = 512u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 148, .base_y = 38, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 513u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 145, .base_y = 34, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 514u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 142, .base_y = 29, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 521u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 99, .base_y = 42, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 522u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 96, .base_y = 35, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 523u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 94, .base_y = 25, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 539u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 48, .base_y = 91, .min_offset_x = -1, .min_offset_y = -1, .max_offset_x = 1, .max_offset_y = 2, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 540u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 131, .base_y = 91, .min_offset_x = -1, .min_offset_y = -1, .max_offset_x = 1, .max_offset_y = 2, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 541u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_EYE, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 43, .base_y = 130, .min_offset_x = -2, .min_offset_y = 0, .max_offset_x = 2, .max_offset_y = 2, .z_index = 30u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 542u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_EYE, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 124, .base_y = 130, .min_offset_x = -2, .min_offset_y = 0, .max_offset_x = 2, .max_offset_y = 2, .z_index = 30u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 543u, .role = COMP_EXPRESSION_RIG_ROLE_MOUTH, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 86, .base_y = 160, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 0, .max_offset_y = 1, .z_index = 60u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 545u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 85, .base_y = 47, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 546u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 86, .base_y = 47, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 547u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 86, .base_y = 47, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 563u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 92, .base_y = 12, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 564u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 92, .base_y = 12, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 565u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 92, .base_y = 12, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 566u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 86, .base_y = 5, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 567u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 86, .base_y = 5, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 568u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 86, .base_y = 5, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 569u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 164, .base_y = 116, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 570u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 164, .base_y = 116, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 571u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 164, .base_y = 116, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 572u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 86, .base_y = 178, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 573u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 86, .base_y = 178, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 574u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 86, .base_y = 178, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 90u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 575u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 45, .base_y = 80, .min_offset_x = -1, .min_offset_y = -1, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 576u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_CHEEK, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 33, .base_y = 157, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 40u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 577u, .role = COMP_EXPRESSION_RIG_ROLE_MOUTH, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 87, .base_y = 158, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 60u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 578u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 127, .base_y = 79, .min_offset_x = -1, .min_offset_y = -1, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 579u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_CHEEK, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 152, .base_y = 157, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 40u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 580u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 50, .base_y = 94, .min_offset_x = -1, .min_offset_y = -1, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 581u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_CHEEK, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 43, .base_y = 157, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 40u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 582u, .role = COMP_EXPRESSION_RIG_ROLE_MOUTH, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 89, .base_y = 162, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 60u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 583u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 129, .base_y = 94, .min_offset_x = -1, .min_offset_y = -1, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 584u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_CHEEK, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 143, .base_y = 157, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 40u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 585u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 50, .base_y = 77, .min_offset_x = -1, .min_offset_y = -1, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 586u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_CHEEK, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 33, .base_y = 157, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 40u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 587u, .role = COMP_EXPRESSION_RIG_ROLE_MOUTH, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 86, .base_y = 163, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 60u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 588u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 127, .base_y = 95, .min_offset_x = -1, .min_offset_y = -1, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 589u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 51, .base_y = 95, .min_offset_x = -1, .min_offset_y = -1, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 590u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_CHEEK, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 33, .base_y = 160, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 40u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 591u, .role = COMP_EXPRESSION_RIG_ROLE_MOUTH, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 87, .base_y = 165, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 60u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 592u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 128, .base_y = 95, .min_offset_x = -1, .min_offset_y = -1, .max_offset_x = 1, .max_offset_y = 1, .z_index = 20u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 593u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_CHEEK, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 151, .base_y = 160, .min_offset_x = 0, .min_offset_y = 0, .max_offset_x = 0, .max_offset_y = 0, .z_index = 40u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 594u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 94, .base_y = 27, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 1, .max_offset_y = 1, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 595u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 116, .base_y = 42, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 1, .max_offset_y = 1, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
    {.component_id = 596u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = 134, .base_y = 54, .min_offset_x = 0, .min_offset_y = -1, .max_offset_x = 1, .max_offset_y = 1, .z_index = 10u, .composite_op = COMP_EXPRESSION_RIG_COMPOSITE_INK},
};

static const comp_expression_rig_profile_t k_v43_profile = {
    .components = k_v43_components, .component_count = COMP_V43_TWO_TRACK_CANDIDATE_COMPONENT_COUNT,
    .scene_charm_component = {[COMP_EXPRESSION_RIG_SCENE_DAILY] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_TOUCH] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_SWIPE] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_RECORDING] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_MENU] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_SLEEP] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_CHARGING] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_ERROR] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID},
    .registered_poses = NULL, .registered_pose_count = 0u,
};

static const comp_expression_rig_registered_pose_t k_v43_expression_0_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_0_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_0_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_LEFT,
    .layer_count = 12u, .layers = {
        {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = -2, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = -2, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = -5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = -5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_0_step_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_LEFT,
    .layer_count = 12u, .layers = {
        {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = -2, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = -2, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = -5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = -5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_0_step_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v43_expression_0_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 220u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_0_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 180u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_0_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 260u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_LEFT, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_0_step_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 760u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_LEFT, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_0_step_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_0_step_4_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v43_expression_0 = {.steps = k_v43_expression_0_steps, .step_count = (uint8_t)(sizeof(k_v43_expression_0_steps) / sizeof(k_v43_expression_0_steps[0]))};

static const comp_expression_rig_registered_pose_t k_v43_expression_1_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 33u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 36u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 34u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 37u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_1_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 33u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 36u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 34u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 37u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_1_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT,
    .layer_count = 12u, .layers = {
        {.component_id = 33u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 36u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 5, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 5, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 34u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 37u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 35u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_1_step_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT,
    .layer_count = 12u, .layers = {
        {.component_id = 33u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 36u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 5, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 5, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 34u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 37u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 35u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_1_step_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 33u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 36u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 34u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 37u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v43_expression_1_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 220u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_1_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 180u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_1_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 260u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_1_step_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 760u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_1_step_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_1_step_4_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v43_expression_1 = {.steps = k_v43_expression_1_steps, .step_count = (uint8_t)(sizeof(k_v43_expression_1_steps) / sizeof(k_v43_expression_1_steps[0]))};

static const comp_expression_rig_registered_pose_t k_v43_expression_2_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 18u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 21u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 19u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 22u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_2_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 13u, .layers = {
        {.component_id = 18u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 21u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 19u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 22u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 512u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_2_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_UP,
    .layer_count = 13u, .layers = {
        {.component_id = 18u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 21u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = -3, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = -3, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = -5, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = -5, .dynamic_flags = 0u},
        {.component_id = 19u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 22u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 20u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 513u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_2_step_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_UP,
    .layer_count = 13u, .layers = {
        {.component_id = 18u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 21u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = -3, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = -3, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = -5, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = -5, .dynamic_flags = 0u},
        {.component_id = 19u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 22u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 20u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 514u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_2_step_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 18u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 21u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 19u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 22u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v43_expression_2_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 180u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_2_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 180u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_2_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 260u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_UP, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_2_step_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 760u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_UP, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_2_step_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_2_step_4_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v43_expression_2 = {.steps = k_v43_expression_2_steps, .step_count = (uint8_t)(sizeof(k_v43_expression_2_steps) / sizeof(k_v43_expression_2_steps[0]))};

static const comp_expression_rig_registered_pose_t k_v43_expression_3_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 8u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 11u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 9u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 12u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_3_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 13u, .layers = {
        {.component_id = 8u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 11u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 9u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 12u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 521u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_3_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT,
    .layer_count = 13u, .layers = {
        {.component_id = 8u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 11u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 5, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 5, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 9u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 12u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 10u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 522u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_3_step_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT,
    .layer_count = 13u, .layers = {
        {.component_id = 8u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 11u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 5, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 5, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 9u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 12u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 10u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 523u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_3_step_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 8u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 11u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 9u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 12u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v43_expression_3_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 180u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_3_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 180u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_3_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 260u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_3_step_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 760u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_3_step_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_3_step_4_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v43_expression_3 = {.steps = k_v43_expression_3_steps, .step_count = (uint8_t)(sizeof(k_v43_expression_3_steps) / sizeof(k_v43_expression_3_steps[0]))};

static const comp_expression_rig_registered_pose_t k_v43_expression_4_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 13u, .layers = {
        {.component_id = 23u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 24u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 27u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 25u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 28u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_4_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 13u, .layers = {
        {.component_id = 23u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 24u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 27u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 25u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 28u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_4_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, .attention = COMP_EXPRESSION_RIG_ATTENTION_LEFT,
    .layer_count = 13u, .layers = {
        {.component_id = 23u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 24u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 27u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = -2, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = -2, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = -5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = -5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 25u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 28u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 26u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_4_step_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT,
    .layer_count = 13u, .layers = {
        {.component_id = 23u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 24u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 27u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 5, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 5, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 25u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 28u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 26u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_4_step_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 13u, .layers = {
        {.component_id = 23u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 24u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 27u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 25u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 28u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v43_expression_4_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 220u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_4_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 180u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_4_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 260u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, .attention = COMP_EXPRESSION_RIG_ATTENTION_LEFT, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_4_step_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 760u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_4_step_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_4_step_4_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v43_expression_4 = {.steps = k_v43_expression_4_steps, .step_count = (uint8_t)(sizeof(k_v43_expression_4_steps) / sizeof(k_v43_expression_4_steps[0]))};

static const comp_expression_rig_registered_pose_t k_v43_expression_5_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
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

static const comp_expression_rig_registered_pose_t k_v43_expression_5_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_SLEEP, .emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 8u, .layers = {
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

static const comp_expression_rig_registered_pose_t k_v43_expression_5_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_SLEEP, .emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 9u, .layers = {
        {.component_id = 594u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
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

static const comp_expression_rig_registered_pose_t k_v43_expression_5_step_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_SLEEP, .emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 10u, .layers = {
        {.component_id = 594u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 595u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
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

static const comp_expression_rig_registered_pose_t k_v43_expression_5_step_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_SLEEP, .emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 11u, .layers = {
        {.component_id = 594u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 595u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 596u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
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

static const comp_expression_rig_registered_score_step_t k_v43_expression_5_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 420u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_5_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_SLEEP, .emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_5_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 320u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_SLEEP, .emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_5_step_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, .duration_ms = 420u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_SLEEP, .emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_5_step_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 1400u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_SLEEP, .emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_5_step_4_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v43_expression_5 = {.steps = k_v43_expression_5_steps, .step_count = (uint8_t)(sizeof(k_v43_expression_5_steps) / sizeof(k_v43_expression_5_steps[0]))};

static const comp_expression_rig_registered_pose_t k_v43_expression_6_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 575u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 578u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 576u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 579u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_6_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 575u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 578u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 576u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 579u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_6_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_UP,
    .layer_count = 12u, .layers = {
        {.component_id = 575u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 578u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = -3, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = -3, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = -5, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = -5, .dynamic_flags = 0u},
        {.component_id = 576u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 579u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 577u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_6_step_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_UP,
    .layer_count = 12u, .layers = {
        {.component_id = 575u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 578u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = -3, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = -3, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = -5, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = -5, .dynamic_flags = 0u},
        {.component_id = 576u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 579u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 577u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_6_step_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 575u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 578u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 576u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 579u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v43_expression_6_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 220u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_6_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 180u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_6_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 260u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_UP, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_6_step_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 760u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_UP, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_6_step_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_6_step_4_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v43_expression_6 = {.steps = k_v43_expression_6_steps, .step_count = (uint8_t)(sizeof(k_v43_expression_6_steps) / sizeof(k_v43_expression_6_steps[0]))};

static const comp_expression_rig_registered_pose_t k_v43_expression_7_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 580u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 583u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 581u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 584u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_7_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 580u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 583u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 581u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 584u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_7_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_LEFT,
    .layer_count = 12u, .layers = {
        {.component_id = 580u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 583u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = -2, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = -2, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = -5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = -5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 581u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 584u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 582u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_7_step_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_LEFT,
    .layer_count = 12u, .layers = {
        {.component_id = 580u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 583u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = -2, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = -2, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = -5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = -5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 581u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 584u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 582u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_7_step_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 580u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 583u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 581u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 584u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v43_expression_7_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 220u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_7_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 180u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_7_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 260u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_LEFT, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_7_step_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 760u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_LEFT, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_7_step_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_7_step_4_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v43_expression_7 = {.steps = k_v43_expression_7_steps, .step_count = (uint8_t)(sizeof(k_v43_expression_7_steps) / sizeof(k_v43_expression_7_steps[0]))};

static const comp_expression_rig_registered_pose_t k_v43_expression_8_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 11u, .layers = {
        {.component_id = 585u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 588u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 586u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_8_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 11u, .layers = {
        {.component_id = 585u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 588u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 586u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_8_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_UP,
    .layer_count = 11u, .layers = {
        {.component_id = 585u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 588u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = -3, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = -3, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = -5, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = -5, .dynamic_flags = 0u},
        {.component_id = 586u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 587u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_8_step_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_UP,
    .layer_count = 11u, .layers = {
        {.component_id = 585u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 588u, .offset_x = 0, .offset_y = -1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = -3, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = -3, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = -5, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = -5, .dynamic_flags = 0u},
        {.component_id = 586u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 587u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_8_step_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 11u, .layers = {
        {.component_id = 585u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 588u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 586u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v43_expression_8_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 220u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_8_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 180u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_8_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 260u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_UP, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_8_step_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 760u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_UP, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_8_step_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_8_step_4_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v43_expression_8 = {.steps = k_v43_expression_8_steps, .step_count = (uint8_t)(sizeof(k_v43_expression_8_steps) / sizeof(k_v43_expression_8_steps[0]))};

static const comp_expression_rig_registered_pose_t k_v43_expression_9_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 589u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 592u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 590u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 593u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_9_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 589u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 592u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 590u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 593u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_9_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT,
    .layer_count = 12u, .layers = {
        {.component_id = 589u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 592u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 5, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 5, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 590u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 593u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 591u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_9_step_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT,
    .layer_count = 12u, .layers = {
        {.component_id = 589u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 592u, .offset_x = 0, .offset_y = 1, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 5, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 5, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 590u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 593u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 591u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_9_step_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 589u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 592u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 590u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 593u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v43_expression_9_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 220u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_9_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 180u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_9_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 260u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_9_step_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 760u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_9_step_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, .duration_ms = 360u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_9_step_4_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v43_expression_9 = {.steps = k_v43_expression_9_steps, .step_count = (uint8_t)(sizeof(k_v43_expression_9_steps) / sizeof(k_v43_expression_9_steps[0]))};

static const comp_expression_rig_registered_pose_t k_v43_expression_10_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_10_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_10_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v43_expression_10_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 220u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_10_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 260u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_10_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 900u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_10_step_2_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v43_expression_10 = {.steps = k_v43_expression_10_steps, .step_count = (uint8_t)(sizeof(k_v43_expression_10_steps) / sizeof(k_v43_expression_10_steps[0]))};

static const comp_expression_rig_registered_pose_t k_v43_expression_11_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_11_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_LEFT,
    .layer_count = 12u, .layers = {
        {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = -2, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = -2, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = -5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = -5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_11_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_LEFT,
    .layer_count = 12u, .layers = {
        {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = -2, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = -2, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = -5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = -5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v43_expression_11_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 180u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_11_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 260u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_LEFT, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_11_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 900u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_LEFT, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_11_step_2_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v43_expression_11 = {.steps = k_v43_expression_11_steps, .step_count = (uint8_t)(sizeof(k_v43_expression_11_steps) / sizeof(k_v43_expression_11_steps[0]))};

static const comp_expression_rig_registered_pose_t k_v43_expression_12_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_12_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT,
    .layer_count = 12u, .layers = {
        {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 5, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 5, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_12_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT,
    .layer_count = 12u, .layers = {
        {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 5, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 5, .offset_y = 2, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 5, .offset_y = 3, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v43_expression_12_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 180u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_12_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 260u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_12_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 900u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_12_step_2_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v43_expression_12 = {.steps = k_v43_expression_12_steps, .step_count = (uint8_t)(sizeof(k_v43_expression_12_steps) / sizeof(k_v43_expression_12_steps[0]))};

static const comp_expression_rig_registered_pose_t k_v43_expression_13_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_13_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_UP,
    .layer_count = 12u, .layers = {
        {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = -3, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = -3, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = -5, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = -5, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_13_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_UP,
    .layer_count = 12u, .layers = {
        {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = -3, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = -3, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = -5, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = -5, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v43_expression_13_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 180u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_13_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 260u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_UP, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_13_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 900u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_UP, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_13_step_2_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v43_expression_13 = {.steps = k_v43_expression_13_steps, .step_count = (uint8_t)(sizeof(k_v43_expression_13_steps) / sizeof(k_v43_expression_13_steps[0]))};

static const comp_expression_rig_registered_pose_t k_v43_expression_14_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 12u, .layers = {
        {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_14_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_DOWN,
    .layer_count = 12u, .layers = {
        {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 4, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 4, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 5, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 5, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_expression_14_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_DOWN,
    .layer_count = 12u, .layers = {
        {.component_id = 13u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 16u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 2u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 6u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 1u, .offset_x = 1, .offset_y = 4, .dynamic_flags = 0u},
        {.component_id = 5u, .offset_x = 1, .offset_y = 4, .dynamic_flags = 0u},
        {.component_id = 3u, .offset_x = 1, .offset_y = 5, .dynamic_flags = 0u},
        {.component_id = 7u, .offset_x = 1, .offset_y = 5, .dynamic_flags = 0u},
        {.component_id = 14u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 17u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 4u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
        {.component_id = 15u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v43_expression_14_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 180u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_14_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 260u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_DOWN, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_14_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 900u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_DOWN, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_expression_14_step_2_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v43_expression_14 = {.steps = k_v43_expression_14_steps, .step_count = (uint8_t)(sizeof(k_v43_expression_14_steps) / sizeof(k_v43_expression_14_steps[0]))};

static const comp_expression_rig_registered_pose_t k_v43_functional_0_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_RECORDING, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 569u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_functional_0_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_RECORDING, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 570u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_functional_0_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_RECORDING, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 571u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_functional_0_step_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_RECORDING, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 570u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_functional_0_step_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_RECORDING, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 569u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v43_functional_0_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 260u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_RECORDING, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_functional_0_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 240u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_RECORDING, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_functional_0_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 520u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_RECORDING, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_functional_0_step_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 240u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_RECORDING, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_functional_0_step_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, .duration_ms = 680u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_RECORDING, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_functional_0_step_4_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v43_functional_0 = {.steps = k_v43_functional_0_steps, .step_count = (uint8_t)(sizeof(k_v43_functional_0_steps) / sizeof(k_v43_functional_0_steps[0]))};

static const comp_expression_rig_registered_pose_t k_v43_functional_1_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_CHARGING, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 572u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_functional_1_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_CHARGING, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 573u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_functional_1_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_CHARGING, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 574u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_functional_1_step_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_CHARGING, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 573u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_functional_1_step_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_CHARGING, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 574u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v43_functional_1_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 300u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_CHARGING, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_functional_1_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 260u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_CHARGING, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_functional_1_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 520u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_CHARGING, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_functional_1_step_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 260u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_CHARGING, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_functional_1_step_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, .duration_ms = 680u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_CHARGING, .emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_functional_1_step_4_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v43_functional_1 = {.steps = k_v43_functional_1_steps, .step_count = (uint8_t)(sizeof(k_v43_functional_1_steps) / sizeof(k_v43_functional_1_steps[0]))};

static const comp_expression_rig_registered_pose_t k_v43_functional_2_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_TOUCH, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 563u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_functional_2_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_TOUCH, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 564u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_functional_2_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_TOUCH, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 565u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_functional_2_step_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_TOUCH, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 564u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_functional_2_step_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_TOUCH, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 565u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v43_functional_2_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 420u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_TOUCH, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_functional_2_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 280u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_TOUCH, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_functional_2_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 520u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_TOUCH, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_functional_2_step_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 280u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_TOUCH, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_functional_2_step_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, .duration_ms = 680u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_TOUCH, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_functional_2_step_4_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v43_functional_2 = {.steps = k_v43_functional_2_steps, .step_count = (uint8_t)(sizeof(k_v43_functional_2_steps) / sizeof(k_v43_functional_2_steps[0]))};

static const comp_expression_rig_registered_pose_t k_v43_functional_3_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_ERROR, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 566u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_functional_3_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_ERROR, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 567u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_functional_3_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_ERROR, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 568u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_functional_3_step_3_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_ERROR, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 567u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_functional_3_step_4_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_ERROR, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 568u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v43_functional_3_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 220u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_ERROR, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_functional_3_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 220u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_ERROR, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_functional_3_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE, .duration_ms = 620u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_ERROR, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_functional_3_step_2_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 220u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_ERROR, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_functional_3_step_3_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT, .duration_ms = 820u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_ERROR, .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_functional_3_step_4_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v43_functional_3 = {.steps = k_v43_functional_3_steps, .step_count = (uint8_t)(sizeof(k_v43_functional_3_steps) / sizeof(k_v43_functional_3_steps[0]))};

static const comp_expression_rig_registered_pose_t k_v43_menu_entry_step_0_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_TOUCH, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 545u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_menu_entry_step_1_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_TOUCH, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 546u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_pose_t k_v43_menu_entry_step_2_pose = {
    .scene = COMP_EXPRESSION_RIG_SCENE_TOUCH, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
    .layer_count = 1u, .layers = {
        {.component_id = 547u, .offset_x = 0, .offset_y = 0, .dynamic_flags = 0u},
    },
};

static const comp_expression_rig_registered_score_step_t k_v43_menu_entry_steps[] = {
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY, .duration_ms = 140u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_TOUCH, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_menu_entry_step_0_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD, .duration_ms = 140u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_TOUCH, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_menu_entry_step_1_pose},
    {.phase = COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD, .duration_ms = 180u, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_TOUCH, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v43_menu_entry_step_2_pose},
};
static const comp_expression_rig_registered_performance_score_t k_v43_menu_entry = {.steps = k_v43_menu_entry_steps, .step_count = (uint8_t)(sizeof(k_v43_menu_entry_steps) / sizeof(k_v43_menu_entry_steps[0]))};

static const comp_v43_two_track_candidate_track_t k_v43_expression_tracks[] = {
    {.name = "calm_presence", .score = &k_v43_expression_0, .step_count = 5u},
    {.name = "warm_presence", .score = &k_v43_expression_1, .step_count = 5u},
    {.name = "curious_question", .score = &k_v43_expression_2, .step_count = 5u},
    {.name = "alert_exclamation", .score = &k_v43_expression_3, .step_count = 5u},
    {.name = "playful_presence", .score = &k_v43_expression_4, .step_count = 5u},
    {.name = "sleepy_presence", .score = &k_v43_expression_5, .step_count = 5u},
    {.name = "delighted_presence", .score = &k_v43_expression_6, .step_count = 5u},
    {.name = "bashful_presence", .score = &k_v43_expression_7, .step_count = 5u},
    {.name = "thoughtful_presence", .score = &k_v43_expression_8, .step_count = 5u},
    {.name = "focused_presence", .score = &k_v43_expression_9, .step_count = 5u},
    {.name = "daily_attention_center", .score = &k_v43_expression_10, .step_count = 3u},
    {.name = "daily_attention_left", .score = &k_v43_expression_11, .step_count = 3u},
    {.name = "daily_attention_right", .score = &k_v43_expression_12, .step_count = 3u},
    {.name = "daily_attention_up", .score = &k_v43_expression_13, .step_count = 3u},
    {.name = "daily_attention_down", .score = &k_v43_expression_14, .step_count = 3u},
};

static const comp_v43_two_track_candidate_track_t k_v43_functional_tracks[] = {
    {.name = "recording_input", .score = &k_v43_functional_0, .step_count = 5u},
    {.name = "bottom_connector_charging", .score = &k_v43_functional_1, .step_count = 5u},
    {.name = "upgrade_progress", .score = &k_v43_functional_2, .step_count = 5u},
    {.name = "error_caution", .score = &k_v43_functional_3, .step_count = 5u},
};

static const comp_v43_two_track_candidate_track_t k_v43_menu_entry_track = {.name = "menu_entry_notice", .score = &k_v43_menu_entry, .step_count = 3u};

static const comp_v43_two_track_candidate_frame_t k_v43_story_0_frames[] = {
    {.cue = "calm_entry", .browser_pbm_filename = "calm_presence-00-calm_entry.pbm", .duration_ms = 220u, .expression_step_index = 0u, .functional_step_index = 255u},
    {.cue = "calm_eye_lead", .browser_pbm_filename = "calm_presence-01-calm_eye_lead.pbm", .duration_ms = 180u, .expression_step_index = 1u, .functional_step_index = 255u},
    {.cue = "calm_glance", .browser_pbm_filename = "calm_presence-02-calm_glance.pbm", .duration_ms = 260u, .expression_step_index = 2u, .functional_step_index = 255u},
    {.cue = "calm_hold", .browser_pbm_filename = "calm_presence-03-calm_hold.pbm", .duration_ms = 760u, .expression_step_index = 3u, .functional_step_index = 255u},
    {.cue = "calm_settle", .browser_pbm_filename = "calm_presence-04-calm_settle.pbm", .duration_ms = 360u, .expression_step_index = 4u, .functional_step_index = 255u},
};

static const comp_v43_two_track_candidate_frame_t k_v43_story_1_frames[] = {
    {.cue = "warm_entry", .browser_pbm_filename = "warm_presence-00-warm_entry.pbm", .duration_ms = 220u, .expression_step_index = 0u, .functional_step_index = 255u},
    {.cue = "warm_brow_lead", .browser_pbm_filename = "warm_presence-01-warm_brow_lead.pbm", .duration_ms = 180u, .expression_step_index = 1u, .functional_step_index = 255u},
    {.cue = "warm_smile_arrive", .browser_pbm_filename = "warm_presence-02-warm_smile_arrive.pbm", .duration_ms = 260u, .expression_step_index = 2u, .functional_step_index = 255u},
    {.cue = "warm_hold", .browser_pbm_filename = "warm_presence-03-warm_hold.pbm", .duration_ms = 760u, .expression_step_index = 3u, .functional_step_index = 255u},
    {.cue = "warm_settle", .browser_pbm_filename = "warm_presence-04-warm_settle.pbm", .duration_ms = 360u, .expression_step_index = 4u, .functional_step_index = 255u},
};

static const comp_v43_two_track_candidate_frame_t k_v43_story_2_frames[] = {
    {.cue = "question_entry", .browser_pbm_filename = "curious_question-00-question_entry.pbm", .duration_ms = 180u, .expression_step_index = 0u, .functional_step_index = 255u},
    {.cue = "question_brow_lead", .browser_pbm_filename = "curious_question-01-question_brow_lead.pbm", .duration_ms = 180u, .expression_step_index = 1u, .functional_step_index = 255u},
    {.cue = "question_mouth_arrive", .browser_pbm_filename = "curious_question-02-question_mouth_arrive.pbm", .duration_ms = 260u, .expression_step_index = 2u, .functional_step_index = 255u},
    {.cue = "question_hold", .browser_pbm_filename = "curious_question-03-question_hold.pbm", .duration_ms = 760u, .expression_step_index = 3u, .functional_step_index = 255u},
    {.cue = "question_settle", .browser_pbm_filename = "curious_question-04-question_settle.pbm", .duration_ms = 360u, .expression_step_index = 4u, .functional_step_index = 255u},
};

static const comp_v43_two_track_candidate_frame_t k_v43_story_3_frames[] = {
    {.cue = "exclamation_entry", .browser_pbm_filename = "alert_exclamation-00-exclamation_entry.pbm", .duration_ms = 180u, .expression_step_index = 0u, .functional_step_index = 255u},
    {.cue = "exclamation_brow_lead", .browser_pbm_filename = "alert_exclamation-01-exclamation_brow_lead.pbm", .duration_ms = 180u, .expression_step_index = 1u, .functional_step_index = 255u},
    {.cue = "exclamation_mouth_arrive", .browser_pbm_filename = "alert_exclamation-02-exclamation_mouth_arrive.pbm", .duration_ms = 260u, .expression_step_index = 2u, .functional_step_index = 255u},
    {.cue = "exclamation_hold", .browser_pbm_filename = "alert_exclamation-03-exclamation_hold.pbm", .duration_ms = 760u, .expression_step_index = 3u, .functional_step_index = 255u},
    {.cue = "exclamation_settle", .browser_pbm_filename = "alert_exclamation-04-exclamation_settle.pbm", .duration_ms = 360u, .expression_step_index = 4u, .functional_step_index = 255u},
};

static const comp_v43_two_track_candidate_frame_t k_v43_story_4_frames[] = {
    {.cue = "playful_entry", .browser_pbm_filename = "playful_presence-00-playful_entry.pbm", .duration_ms = 220u, .expression_step_index = 0u, .functional_step_index = 255u},
    {.cue = "playful_brow_lead", .browser_pbm_filename = "playful_presence-01-playful_brow_lead.pbm", .duration_ms = 180u, .expression_step_index = 1u, .functional_step_index = 255u},
    {.cue = "playful_smile_arrive", .browser_pbm_filename = "playful_presence-02-playful_smile_arrive.pbm", .duration_ms = 260u, .expression_step_index = 2u, .functional_step_index = 255u},
    {.cue = "playful_hold", .browser_pbm_filename = "playful_presence-03-playful_hold.pbm", .duration_ms = 760u, .expression_step_index = 3u, .functional_step_index = 255u},
    {.cue = "playful_settle", .browser_pbm_filename = "playful_presence-04-playful_settle.pbm", .duration_ms = 360u, .expression_step_index = 4u, .functional_step_index = 255u},
};

static const comp_v43_two_track_candidate_frame_t k_v43_story_5_frames[] = {
    {.cue = "sleep_entry", .browser_pbm_filename = "sleepy_presence-00-sleep_entry.pbm", .duration_ms = 420u, .expression_step_index = 0u, .functional_step_index = 255u},
    {.cue = "eyes_soften", .browser_pbm_filename = "sleepy_presence-01-eyes_soften.pbm", .duration_ms = 360u, .expression_step_index = 1u, .functional_step_index = 255u},
    {.cue = "zzz_arrive", .browser_pbm_filename = "sleepy_presence-02-zzz_arrive.pbm", .duration_ms = 320u, .expression_step_index = 2u, .functional_step_index = 255u},
    {.cue = "zzz_rise", .browser_pbm_filename = "sleepy_presence-03-zzz_rise.pbm", .duration_ms = 420u, .expression_step_index = 3u, .functional_step_index = 255u},
    {.cue = "sleep_hold", .browser_pbm_filename = "sleepy_presence-04-sleep_hold.pbm", .duration_ms = 1400u, .expression_step_index = 4u, .functional_step_index = 255u},
};

static const comp_v43_two_track_candidate_frame_t k_v43_story_6_frames[] = {
    {.cue = "delighted_entry", .browser_pbm_filename = "delighted_presence-00-delighted_entry.pbm", .duration_ms = 220u, .expression_step_index = 0u, .functional_step_index = 255u},
    {.cue = "delighted_brow_lead", .browser_pbm_filename = "delighted_presence-01-delighted_brow_lead.pbm", .duration_ms = 180u, .expression_step_index = 1u, .functional_step_index = 255u},
    {.cue = "delighted_mouth_arrive", .browser_pbm_filename = "delighted_presence-02-delighted_mouth_arrive.pbm", .duration_ms = 260u, .expression_step_index = 2u, .functional_step_index = 255u},
    {.cue = "delighted_hold", .browser_pbm_filename = "delighted_presence-03-delighted_hold.pbm", .duration_ms = 760u, .expression_step_index = 3u, .functional_step_index = 255u},
    {.cue = "delighted_settle", .browser_pbm_filename = "delighted_presence-04-delighted_settle.pbm", .duration_ms = 360u, .expression_step_index = 4u, .functional_step_index = 255u},
};

static const comp_v43_two_track_candidate_frame_t k_v43_story_7_frames[] = {
    {.cue = "bashful_entry", .browser_pbm_filename = "bashful_presence-00-bashful_entry.pbm", .duration_ms = 220u, .expression_step_index = 0u, .functional_step_index = 255u},
    {.cue = "bashful_brow_lead", .browser_pbm_filename = "bashful_presence-01-bashful_brow_lead.pbm", .duration_ms = 180u, .expression_step_index = 1u, .functional_step_index = 255u},
    {.cue = "bashful_mouth_arrive", .browser_pbm_filename = "bashful_presence-02-bashful_mouth_arrive.pbm", .duration_ms = 260u, .expression_step_index = 2u, .functional_step_index = 255u},
    {.cue = "bashful_hold", .browser_pbm_filename = "bashful_presence-03-bashful_hold.pbm", .duration_ms = 760u, .expression_step_index = 3u, .functional_step_index = 255u},
    {.cue = "bashful_settle", .browser_pbm_filename = "bashful_presence-04-bashful_settle.pbm", .duration_ms = 360u, .expression_step_index = 4u, .functional_step_index = 255u},
};

static const comp_v43_two_track_candidate_frame_t k_v43_story_8_frames[] = {
    {.cue = "thoughtful_entry", .browser_pbm_filename = "thoughtful_presence-00-thoughtful_entry.pbm", .duration_ms = 220u, .expression_step_index = 0u, .functional_step_index = 255u},
    {.cue = "thoughtful_brow_lead", .browser_pbm_filename = "thoughtful_presence-01-thoughtful_brow_lead.pbm", .duration_ms = 180u, .expression_step_index = 1u, .functional_step_index = 255u},
    {.cue = "thoughtful_mouth_arrive", .browser_pbm_filename = "thoughtful_presence-02-thoughtful_mouth_arrive.pbm", .duration_ms = 260u, .expression_step_index = 2u, .functional_step_index = 255u},
    {.cue = "thoughtful_hold", .browser_pbm_filename = "thoughtful_presence-03-thoughtful_hold.pbm", .duration_ms = 760u, .expression_step_index = 3u, .functional_step_index = 255u},
    {.cue = "thoughtful_settle", .browser_pbm_filename = "thoughtful_presence-04-thoughtful_settle.pbm", .duration_ms = 360u, .expression_step_index = 4u, .functional_step_index = 255u},
};

static const comp_v43_two_track_candidate_frame_t k_v43_story_9_frames[] = {
    {.cue = "focused_entry", .browser_pbm_filename = "focused_presence-00-focused_entry.pbm", .duration_ms = 220u, .expression_step_index = 0u, .functional_step_index = 255u},
    {.cue = "focused_brow_lead", .browser_pbm_filename = "focused_presence-01-focused_brow_lead.pbm", .duration_ms = 180u, .expression_step_index = 1u, .functional_step_index = 255u},
    {.cue = "focused_mouth_arrive", .browser_pbm_filename = "focused_presence-02-focused_mouth_arrive.pbm", .duration_ms = 260u, .expression_step_index = 2u, .functional_step_index = 255u},
    {.cue = "focused_hold", .browser_pbm_filename = "focused_presence-03-focused_hold.pbm", .duration_ms = 760u, .expression_step_index = 3u, .functional_step_index = 255u},
    {.cue = "focused_settle", .browser_pbm_filename = "focused_presence-04-focused_settle.pbm", .duration_ms = 360u, .expression_step_index = 4u, .functional_step_index = 255u},
};

static const comp_v43_two_track_candidate_frame_t k_v43_story_10_frames[] = {
    {.cue = "recording_input_0", .browser_pbm_filename = "recording_with_calm-00-recording_input_0.pbm", .duration_ms = 260u, .expression_step_index = 0u, .functional_step_index = 0u},
    {.cue = "recording_input_1", .browser_pbm_filename = "recording_with_calm-01-recording_input_1.pbm", .duration_ms = 240u, .expression_step_index = 1u, .functional_step_index = 1u},
    {.cue = "recording_input_2", .browser_pbm_filename = "recording_with_calm-02-recording_input_2.pbm", .duration_ms = 520u, .expression_step_index = 2u, .functional_step_index = 2u},
    {.cue = "recording_input_3", .browser_pbm_filename = "recording_with_calm-03-recording_input_3.pbm", .duration_ms = 240u, .expression_step_index = 3u, .functional_step_index = 3u},
    {.cue = "recording_input_4", .browser_pbm_filename = "recording_with_calm-04-recording_input_4.pbm", .duration_ms = 680u, .expression_step_index = 4u, .functional_step_index = 4u},
};

static const comp_v43_two_track_candidate_frame_t k_v43_story_11_frames[] = {
    {.cue = "recording_input_0", .browser_pbm_filename = "recording_with_warm-00-recording_input_0.pbm", .duration_ms = 260u, .expression_step_index = 0u, .functional_step_index = 0u},
    {.cue = "recording_input_1", .browser_pbm_filename = "recording_with_warm-01-recording_input_1.pbm", .duration_ms = 240u, .expression_step_index = 1u, .functional_step_index = 1u},
    {.cue = "recording_input_2", .browser_pbm_filename = "recording_with_warm-02-recording_input_2.pbm", .duration_ms = 520u, .expression_step_index = 2u, .functional_step_index = 2u},
    {.cue = "recording_input_3", .browser_pbm_filename = "recording_with_warm-03-recording_input_3.pbm", .duration_ms = 240u, .expression_step_index = 3u, .functional_step_index = 3u},
    {.cue = "recording_input_4", .browser_pbm_filename = "recording_with_warm-04-recording_input_4.pbm", .duration_ms = 680u, .expression_step_index = 4u, .functional_step_index = 4u},
};

static const comp_v43_two_track_candidate_frame_t k_v43_story_12_frames[] = {
    {.cue = "bottom_connector_charging_0", .browser_pbm_filename = "charging_with_calm-00-bottom_connector_charging_0.pbm", .duration_ms = 300u, .expression_step_index = 0u, .functional_step_index = 0u},
    {.cue = "bottom_connector_charging_1", .browser_pbm_filename = "charging_with_calm-01-bottom_connector_charging_1.pbm", .duration_ms = 260u, .expression_step_index = 1u, .functional_step_index = 1u},
    {.cue = "bottom_connector_charging_2", .browser_pbm_filename = "charging_with_calm-02-bottom_connector_charging_2.pbm", .duration_ms = 520u, .expression_step_index = 2u, .functional_step_index = 2u},
    {.cue = "bottom_connector_charging_3", .browser_pbm_filename = "charging_with_calm-03-bottom_connector_charging_3.pbm", .duration_ms = 260u, .expression_step_index = 3u, .functional_step_index = 3u},
    {.cue = "bottom_connector_charging_4", .browser_pbm_filename = "charging_with_calm-04-bottom_connector_charging_4.pbm", .duration_ms = 680u, .expression_step_index = 4u, .functional_step_index = 4u},
};

static const comp_v43_two_track_candidate_frame_t k_v43_story_13_frames[] = {
    {.cue = "upgrade_progress_0", .browser_pbm_filename = "upgrade_with_playful-00-upgrade_progress_0.pbm", .duration_ms = 420u, .expression_step_index = 0u, .functional_step_index = 0u},
    {.cue = "upgrade_progress_1", .browser_pbm_filename = "upgrade_with_playful-01-upgrade_progress_1.pbm", .duration_ms = 280u, .expression_step_index = 1u, .functional_step_index = 1u},
    {.cue = "upgrade_progress_2", .browser_pbm_filename = "upgrade_with_playful-02-upgrade_progress_2.pbm", .duration_ms = 520u, .expression_step_index = 2u, .functional_step_index = 2u},
    {.cue = "upgrade_progress_3", .browser_pbm_filename = "upgrade_with_playful-03-upgrade_progress_3.pbm", .duration_ms = 280u, .expression_step_index = 3u, .functional_step_index = 3u},
    {.cue = "upgrade_progress_4", .browser_pbm_filename = "upgrade_with_playful-04-upgrade_progress_4.pbm", .duration_ms = 680u, .expression_step_index = 4u, .functional_step_index = 4u},
};

static const comp_v43_two_track_candidate_frame_t k_v43_story_14_frames[] = {
    {.cue = "error_caution_0", .browser_pbm_filename = "error_with_calm-00-error_caution_0.pbm", .duration_ms = 220u, .expression_step_index = 0u, .functional_step_index = 0u},
    {.cue = "error_caution_1", .browser_pbm_filename = "error_with_calm-01-error_caution_1.pbm", .duration_ms = 220u, .expression_step_index = 1u, .functional_step_index = 1u},
    {.cue = "error_caution_2", .browser_pbm_filename = "error_with_calm-02-error_caution_2.pbm", .duration_ms = 620u, .expression_step_index = 2u, .functional_step_index = 2u},
    {.cue = "error_caution_3", .browser_pbm_filename = "error_with_calm-03-error_caution_3.pbm", .duration_ms = 220u, .expression_step_index = 3u, .functional_step_index = 3u},
    {.cue = "error_caution_4", .browser_pbm_filename = "error_with_calm-04-error_caution_4.pbm", .duration_ms = 820u, .expression_step_index = 4u, .functional_step_index = 4u},
};

static const comp_v43_two_track_candidate_frame_t k_v43_story_15_frames[] = {
    {.cue = "menu_grid_arrive", .browser_pbm_filename = "menu_entry_notice-00-menu_grid_arrive.pbm", .duration_ms = 140u, .expression_step_index = 0u, .functional_step_index = 0u},
    {.cue = "menu_selection_confirm", .browser_pbm_filename = "menu_entry_notice-01-menu_selection_confirm.pbm", .duration_ms = 140u, .expression_step_index = 1u, .functional_step_index = 1u},
    {.cue = "menu_entry_commit", .browser_pbm_filename = "menu_entry_notice-02-menu_entry_commit.pbm", .duration_ms = 180u, .expression_step_index = 2u, .functional_step_index = 2u},
};

static const comp_v43_two_track_candidate_frame_t k_v43_story_16_frames[] = {
    {.cue = "gaze_center_entry", .browser_pbm_filename = "daily_attention_center-00-gaze_center_entry.pbm", .duration_ms = 220u, .expression_step_index = 0u, .functional_step_index = 255u},
    {.cue = "gaze_center_micro", .browser_pbm_filename = "daily_attention_center-01-gaze_center_micro.pbm", .duration_ms = 260u, .expression_step_index = 1u, .functional_step_index = 255u},
    {.cue = "gaze_center_hold", .browser_pbm_filename = "daily_attention_center-02-gaze_center_hold.pbm", .duration_ms = 900u, .expression_step_index = 2u, .functional_step_index = 255u},
};

static const comp_v43_two_track_candidate_frame_t k_v43_story_17_frames[] = {
    {.cue = "gaze_left_depart", .browser_pbm_filename = "daily_attention_left-00-gaze_left_depart.pbm", .duration_ms = 180u, .expression_step_index = 0u, .functional_step_index = 255u},
    {.cue = "gaze_left_arrive", .browser_pbm_filename = "daily_attention_left-01-gaze_left_arrive.pbm", .duration_ms = 260u, .expression_step_index = 1u, .functional_step_index = 255u},
    {.cue = "gaze_left_hold", .browser_pbm_filename = "daily_attention_left-02-gaze_left_hold.pbm", .duration_ms = 900u, .expression_step_index = 2u, .functional_step_index = 255u},
};

static const comp_v43_two_track_candidate_frame_t k_v43_story_18_frames[] = {
    {.cue = "gaze_right_depart", .browser_pbm_filename = "daily_attention_right-00-gaze_right_depart.pbm", .duration_ms = 180u, .expression_step_index = 0u, .functional_step_index = 255u},
    {.cue = "gaze_right_arrive", .browser_pbm_filename = "daily_attention_right-01-gaze_right_arrive.pbm", .duration_ms = 260u, .expression_step_index = 1u, .functional_step_index = 255u},
    {.cue = "gaze_right_hold", .browser_pbm_filename = "daily_attention_right-02-gaze_right_hold.pbm", .duration_ms = 900u, .expression_step_index = 2u, .functional_step_index = 255u},
};

static const comp_v43_two_track_candidate_frame_t k_v43_story_19_frames[] = {
    {.cue = "gaze_up_depart", .browser_pbm_filename = "daily_attention_up-00-gaze_up_depart.pbm", .duration_ms = 180u, .expression_step_index = 0u, .functional_step_index = 255u},
    {.cue = "gaze_up_arrive", .browser_pbm_filename = "daily_attention_up-01-gaze_up_arrive.pbm", .duration_ms = 260u, .expression_step_index = 1u, .functional_step_index = 255u},
    {.cue = "gaze_up_hold", .browser_pbm_filename = "daily_attention_up-02-gaze_up_hold.pbm", .duration_ms = 900u, .expression_step_index = 2u, .functional_step_index = 255u},
};

static const comp_v43_two_track_candidate_frame_t k_v43_story_20_frames[] = {
    {.cue = "gaze_down_depart", .browser_pbm_filename = "daily_attention_down-00-gaze_down_depart.pbm", .duration_ms = 180u, .expression_step_index = 0u, .functional_step_index = 255u},
    {.cue = "gaze_down_arrive", .browser_pbm_filename = "daily_attention_down-01-gaze_down_arrive.pbm", .duration_ms = 260u, .expression_step_index = 1u, .functional_step_index = 255u},
    {.cue = "gaze_down_hold", .browser_pbm_filename = "daily_attention_down-02-gaze_down_hold.pbm", .duration_ms = 900u, .expression_step_index = 2u, .functional_step_index = 255u},
};

static const comp_v43_two_track_candidate_story_t k_v43_stories[] = {
    {.name = "calm_presence", .expression_track_index = 0u, .functional_track_index = 255u, .uses_menu_entry_track = false, .frames = k_v43_story_0_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_0_frames) / sizeof(k_v43_story_0_frames[0])), .withdraw_all_tracks_after_last_cue = false},
    {.name = "warm_presence", .expression_track_index = 1u, .functional_track_index = 255u, .uses_menu_entry_track = false, .frames = k_v43_story_1_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_1_frames) / sizeof(k_v43_story_1_frames[0])), .withdraw_all_tracks_after_last_cue = false},
    {.name = "curious_question", .expression_track_index = 2u, .functional_track_index = 255u, .uses_menu_entry_track = false, .frames = k_v43_story_2_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_2_frames) / sizeof(k_v43_story_2_frames[0])), .withdraw_all_tracks_after_last_cue = false},
    {.name = "alert_exclamation", .expression_track_index = 3u, .functional_track_index = 255u, .uses_menu_entry_track = false, .frames = k_v43_story_3_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_3_frames) / sizeof(k_v43_story_3_frames[0])), .withdraw_all_tracks_after_last_cue = false},
    {.name = "playful_presence", .expression_track_index = 4u, .functional_track_index = 255u, .uses_menu_entry_track = false, .frames = k_v43_story_4_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_4_frames) / sizeof(k_v43_story_4_frames[0])), .withdraw_all_tracks_after_last_cue = false},
    {.name = "sleepy_presence", .expression_track_index = 5u, .functional_track_index = 255u, .uses_menu_entry_track = false, .frames = k_v43_story_5_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_5_frames) / sizeof(k_v43_story_5_frames[0])), .withdraw_all_tracks_after_last_cue = false},
    {.name = "delighted_presence", .expression_track_index = 6u, .functional_track_index = 255u, .uses_menu_entry_track = false, .frames = k_v43_story_6_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_6_frames) / sizeof(k_v43_story_6_frames[0])), .withdraw_all_tracks_after_last_cue = false},
    {.name = "bashful_presence", .expression_track_index = 7u, .functional_track_index = 255u, .uses_menu_entry_track = false, .frames = k_v43_story_7_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_7_frames) / sizeof(k_v43_story_7_frames[0])), .withdraw_all_tracks_after_last_cue = false},
    {.name = "thoughtful_presence", .expression_track_index = 8u, .functional_track_index = 255u, .uses_menu_entry_track = false, .frames = k_v43_story_8_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_8_frames) / sizeof(k_v43_story_8_frames[0])), .withdraw_all_tracks_after_last_cue = false},
    {.name = "focused_presence", .expression_track_index = 9u, .functional_track_index = 255u, .uses_menu_entry_track = false, .frames = k_v43_story_9_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_9_frames) / sizeof(k_v43_story_9_frames[0])), .withdraw_all_tracks_after_last_cue = false},
    {.name = "recording_with_calm", .expression_track_index = 0u, .functional_track_index = 0u, .uses_menu_entry_track = false, .frames = k_v43_story_10_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_10_frames) / sizeof(k_v43_story_10_frames[0])), .withdraw_all_tracks_after_last_cue = false},
    {.name = "recording_with_warm", .expression_track_index = 1u, .functional_track_index = 0u, .uses_menu_entry_track = false, .frames = k_v43_story_11_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_11_frames) / sizeof(k_v43_story_11_frames[0])), .withdraw_all_tracks_after_last_cue = false},
    {.name = "charging_with_calm", .expression_track_index = 0u, .functional_track_index = 1u, .uses_menu_entry_track = false, .frames = k_v43_story_12_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_12_frames) / sizeof(k_v43_story_12_frames[0])), .withdraw_all_tracks_after_last_cue = false},
    {.name = "upgrade_with_playful", .expression_track_index = 4u, .functional_track_index = 2u, .uses_menu_entry_track = false, .frames = k_v43_story_13_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_13_frames) / sizeof(k_v43_story_13_frames[0])), .withdraw_all_tracks_after_last_cue = false},
    {.name = "error_with_calm", .expression_track_index = 0u, .functional_track_index = 3u, .uses_menu_entry_track = false, .frames = k_v43_story_14_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_14_frames) / sizeof(k_v43_story_14_frames[0])), .withdraw_all_tracks_after_last_cue = false},
    {.name = "menu_entry_notice", .expression_track_index = 0u, .functional_track_index = 255u, .uses_menu_entry_track = true, .frames = k_v43_story_15_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_15_frames) / sizeof(k_v43_story_15_frames[0])), .withdraw_all_tracks_after_last_cue = true},
    {.name = "daily_attention_center", .expression_track_index = 10u, .functional_track_index = 255u, .uses_menu_entry_track = false, .frames = k_v43_story_16_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_16_frames) / sizeof(k_v43_story_16_frames[0])), .withdraw_all_tracks_after_last_cue = false},
    {.name = "daily_attention_left", .expression_track_index = 11u, .functional_track_index = 255u, .uses_menu_entry_track = false, .frames = k_v43_story_17_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_17_frames) / sizeof(k_v43_story_17_frames[0])), .withdraw_all_tracks_after_last_cue = false},
    {.name = "daily_attention_right", .expression_track_index = 12u, .functional_track_index = 255u, .uses_menu_entry_track = false, .frames = k_v43_story_18_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_18_frames) / sizeof(k_v43_story_18_frames[0])), .withdraw_all_tracks_after_last_cue = false},
    {.name = "daily_attention_up", .expression_track_index = 13u, .functional_track_index = 255u, .uses_menu_entry_track = false, .frames = k_v43_story_19_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_19_frames) / sizeof(k_v43_story_19_frames[0])), .withdraw_all_tracks_after_last_cue = false},
    {.name = "daily_attention_down", .expression_track_index = 14u, .functional_track_index = 255u, .uses_menu_entry_track = false, .frames = k_v43_story_20_frames, .frame_count = (uint8_t)(sizeof(k_v43_story_20_frames) / sizeof(k_v43_story_20_frames[0])), .withdraw_all_tracks_after_last_cue = false},
};

const comp_expression_rig_profile_t *comp_v43_two_track_candidate_profile(void) { return &k_v43_profile; }
bool comp_v43_two_track_candidate_runtime_activation_allowed(void) { return false; }
const comp_v43_two_track_candidate_track_t *comp_v43_two_track_candidate_expression_track(uint8_t index) { return index < COMP_V43_TWO_TRACK_CANDIDATE_EXPRESSION_TRACK_COUNT ? &k_v43_expression_tracks[index] : NULL; }
const comp_v43_two_track_candidate_track_t *comp_v43_two_track_candidate_functional_track(uint8_t index) { return index < COMP_V43_TWO_TRACK_CANDIDATE_FUNCTIONAL_TRACK_COUNT ? &k_v43_functional_tracks[index] : NULL; }
const comp_v43_two_track_candidate_track_t *comp_v43_two_track_candidate_menu_entry_track(void) { return &k_v43_menu_entry_track; }

static bool build_with_optional_functional(const comp_v43_two_track_candidate_track_t *expression, uint8_t expression_step, const comp_v43_two_track_candidate_track_t *functional, uint8_t functional_step, const comp_expression_rig_state_t *dynamic_context, comp_expression_rig_plan_t *out_plan) {
    comp_expression_rig_plan_t expression_plan; comp_expression_rig_plan_t functional_plan;
    if (expression == NULL || expression->score == NULL || expression_step >= expression->step_count || out_plan == NULL || !comp_expression_rig_build_registered_score_step(&k_v43_profile, expression->score, expression_step, dynamic_context, &expression_plan)) { return false; }
    if (functional == NULL) { return comp_expression_rig_merge_tracks(&k_v43_profile, &expression_plan, NULL, out_plan); }
    return functional->score != NULL && functional_step < functional->step_count && comp_expression_rig_build_registered_score_step(&k_v43_profile, functional->score, functional_step, NULL, &functional_plan) && comp_expression_rig_merge_tracks(&k_v43_profile, &expression_plan, &functional_plan, out_plan);
}

bool comp_v43_two_track_candidate_build_composed_frame(uint8_t expression_track_index, uint8_t expression_step_index, uint8_t functional_track_index, uint8_t functional_step_index, const comp_expression_rig_state_t *dynamic_context, comp_expression_rig_plan_t *out_plan) {
    const comp_v43_two_track_candidate_track_t *functional = functional_track_index == COMP_V43_TWO_TRACK_CANDIDATE_NO_FUNCTIONAL_TRACK ? NULL : comp_v43_two_track_candidate_functional_track(functional_track_index);
    if (functional == NULL && functional_track_index != COMP_V43_TWO_TRACK_CANDIDATE_NO_FUNCTIONAL_TRACK) { return false; }
    return build_with_optional_functional(comp_v43_two_track_candidate_expression_track(expression_track_index), expression_step_index, functional, functional_step_index, dynamic_context, out_plan);
}

bool comp_v43_two_track_candidate_build_menu_entry_frame(uint8_t expression_track_index, uint8_t expression_step_index, uint8_t menu_entry_step_index, const comp_expression_rig_state_t *dynamic_context, comp_expression_rig_plan_t *out_plan) {
    return build_with_optional_functional(comp_v43_two_track_candidate_expression_track(expression_track_index), expression_step_index, &k_v43_menu_entry_track, menu_entry_step_index, dynamic_context, out_plan);
}

bool comp_v43_two_track_candidate_build_story_frame(const comp_v43_two_track_candidate_story_t *story, uint8_t frame_index, const comp_expression_rig_state_t *dynamic_context, comp_expression_rig_plan_t *out_plan) {
    const comp_v43_two_track_candidate_frame_t *frame;
    if (story == NULL || out_plan == NULL || story->frames == NULL || frame_index >= story->frame_count) { return false; }
    frame = &story->frames[frame_index];
    return story->uses_menu_entry_track ? comp_v43_two_track_candidate_build_menu_entry_frame(story->expression_track_index, frame->expression_step_index, frame->functional_step_index, dynamic_context, out_plan) : comp_v43_two_track_candidate_build_composed_frame(story->expression_track_index, frame->expression_step_index, story->functional_track_index, frame->functional_step_index, dynamic_context, out_plan);
}

const comp_v43_two_track_candidate_story_t *comp_v43_two_track_candidate_story(uint8_t index) { return index < COMP_V43_TWO_TRACK_CANDIDATE_STORY_COUNT ? &k_v43_stories[index] : NULL; }
