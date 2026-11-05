#include "expression_rig.h"

#include <stdio.h>
#include <string.h>

enum {
    COMPONENT_LEFT_BROW_OPEN = 1u,
    COMPONENT_RIGHT_BROW_OPEN,
    COMPONENT_LEFT_BROW_SLEEPY,
    COMPONENT_RIGHT_BROW_SLEEPY,
    COMPONENT_LEFT_EYE_OPEN,
    COMPONENT_RIGHT_EYE_OPEN,
    COMPONENT_LEFT_HIGHLIGHT_OPEN,
    COMPONENT_RIGHT_HIGHLIGHT_OPEN,
    COMPONENT_LEFT_EYE_SLEEPY,
    COMPONENT_RIGHT_EYE_SLEEPY,
    COMPONENT_LEFT_CHEEK,
    COMPONENT_RIGHT_CHEEK,
    COMPONENT_NOSE,
    COMPONENT_MOUTH,
    COMPONENT_LEFT_DETAIL_SWIPE,
    COMPONENT_RIGHT_DETAIL_SWIPE,
    COMPONENT_CHARM,
    COMPONENT_LEFT_SPARKLE_OPEN,
    COMPONENT_RIGHT_SPARKLE_OPEN,
};

static const comp_expression_rig_component_info_t components[] = {
    {COMPONENT_LEFT_BROW_OPEN, COMP_EXPRESSION_RIG_ROLE_LEFT_BROW, COMP_EXPRESSION_RIG_VARIANT_OPEN, 3, 3, -1, -3, 1, 1, 20},
    {COMPONENT_RIGHT_BROW_OPEN, COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW, COMP_EXPRESSION_RIG_VARIANT_OPEN, 11, 3, -1, -3, 1, 1, 20},
    {COMPONENT_LEFT_BROW_SLEEPY, COMP_EXPRESSION_RIG_ROLE_LEFT_BROW, COMP_EXPRESSION_RIG_VARIANT_SLEEPY, 3, 4, -1, -1, 1, 2, 20},
    {COMPONENT_RIGHT_BROW_SLEEPY, COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW, COMP_EXPRESSION_RIG_VARIANT_SLEEPY, 11, 4, -1, -1, 1, 2, 20},
    {COMPONENT_LEFT_EYE_OPEN, COMP_EXPRESSION_RIG_ROLE_LEFT_EYE, COMP_EXPRESSION_RIG_VARIANT_OPEN, 3, 7, -3, -2, 3, 2, 30},
    {COMPONENT_RIGHT_EYE_OPEN, COMP_EXPRESSION_RIG_ROLE_RIGHT_EYE, COMP_EXPRESSION_RIG_VARIANT_OPEN, 11, 7, -3, -2, 3, 2, 30},
    {COMPONENT_LEFT_HIGHLIGHT_OPEN, COMP_EXPRESSION_RIG_ROLE_LEFT_HIGHLIGHT, COMP_EXPRESSION_RIG_VARIANT_OPEN, 3, 7, -2, -3, 5, 4, 31, COMP_EXPRESSION_RIG_COMPOSITE_ERASE},
    {COMPONENT_RIGHT_HIGHLIGHT_OPEN, COMP_EXPRESSION_RIG_ROLE_RIGHT_HIGHLIGHT, COMP_EXPRESSION_RIG_VARIANT_OPEN, 11, 7, -2, -3, 5, 4, 31, COMP_EXPRESSION_RIG_COMPOSITE_ERASE},
    {COMPONENT_LEFT_EYE_SLEEPY, COMP_EXPRESSION_RIG_ROLE_LEFT_EYE, COMP_EXPRESSION_RIG_VARIANT_SLEEPY, 3, 9, -2, 0, 2, 2, 30},
    {COMPONENT_RIGHT_EYE_SLEEPY, COMP_EXPRESSION_RIG_ROLE_RIGHT_EYE, COMP_EXPRESSION_RIG_VARIANT_SLEEPY, 11, 9, -2, 0, 2, 2, 30},
    {COMPONENT_LEFT_CHEEK, COMP_EXPRESSION_RIG_ROLE_LEFT_CHEEK, COMP_EXPRESSION_RIG_VARIANT_DEFAULT, 1, 12, 0, -1, 0, 1, 40},
    {COMPONENT_RIGHT_CHEEK, COMP_EXPRESSION_RIG_ROLE_RIGHT_CHEEK, COMP_EXPRESSION_RIG_VARIANT_DEFAULT, 15, 12, 0, -1, 0, 1, 40},
    {COMPONENT_NOSE, COMP_EXPRESSION_RIG_ROLE_NOSE, COMP_EXPRESSION_RIG_VARIANT_DEFAULT, 8, 11, 0, 0, 0, 0, 50},
    {COMPONENT_MOUTH, COMP_EXPRESSION_RIG_ROLE_MOUTH, COMP_EXPRESSION_RIG_VARIANT_DEFAULT, 8, 13, 0, -1, 0, 1, 60},
    {COMPONENT_LEFT_DETAIL_SWIPE, COMP_EXPRESSION_RIG_ROLE_LEFT_DETAIL, COMP_EXPRESSION_RIG_VARIANT_SWIPE, 1, 7, -1, -1, 1, 1, 35},
    {COMPONENT_RIGHT_DETAIL_SWIPE, COMP_EXPRESSION_RIG_ROLE_RIGHT_DETAIL, COMP_EXPRESSION_RIG_VARIANT_SWIPE, 14, 7, -1, -1, 1, 1, 35},
    {COMPONENT_CHARM, COMP_EXPRESSION_RIG_ROLE_CHARM, COMP_EXPRESSION_RIG_VARIANT_DEFAULT, 8, 5, 0, -3, 2, 1, 10},
    {COMPONENT_LEFT_SPARKLE_OPEN, COMP_EXPRESSION_RIG_ROLE_LEFT_SPARKLE, COMP_EXPRESSION_RIG_VARIANT_OPEN, 3, 7, -6, -6, 5, 6, 32, COMP_EXPRESSION_RIG_COMPOSITE_ERASE},
    {COMPONENT_RIGHT_SPARKLE_OPEN, COMP_EXPRESSION_RIG_ROLE_RIGHT_SPARKLE, COMP_EXPRESSION_RIG_VARIANT_OPEN, 11, 7, -6, -6, 5, 6, 32, COMP_EXPRESSION_RIG_COMPOSITE_ERASE},
};

static const comp_expression_rig_profile_t profile = {
    components,
    sizeof(components) / sizeof(components[0]),
    {COMPONENT_CHARM, COMPONENT_CHARM, COMPONENT_CHARM, COMPONENT_CHARM,
     COMPONENT_CHARM, COMPONENT_CHARM, COMPONENT_CHARM, COMPONENT_CHARM},
};

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

static bool read_component(void *context,
                           uint16_t component_id,
                           uint8_t *destination,
                           size_t destination_size,
                           comp_expression_rig_component_mask_info_t *out_info)
{
    (void)context;
    if (component_id == COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID || destination == NULL ||
        destination_size < 1u || out_info == NULL) {
        return false;
    }
    destination[0] = 0x7Fu;
    *out_info = (comp_expression_rig_component_mask_info_t){
        .width = 1u,
        .height = 1u,
        .stride_bytes = 1u,
        .data_size = 1u,
    };
    return true;
}

int main(void)
{
    comp_expression_rig_state_t center = {
        COMP_EXPRESSION_RIG_SCENE_DAILY,
        COMP_EXPRESSION_RIG_EMOTION_CALM,
        COMP_EXPRESSION_RIG_ATTENTION_CENTER,
        COMP_EXPRESSION_RIG_ENERGY_NORMAL,
        0u,
        COMP_EXPRESSION_RIG_PHASE_SUSTAIN,
    };
    comp_expression_rig_state_t left = center;
    comp_expression_rig_state_t story;
    comp_expression_rig_state_t daily_a;
    comp_expression_rig_state_t daily_b;
    comp_expression_rig_plan_t center_plan;
    comp_expression_rig_plan_t left_plan;
    comp_expression_rig_plan_t swipe_plan;
    comp_expression_rig_plan_t sleepy_plan;
    const comp_expression_rig_layer_t *center_eye;
    const comp_expression_rig_layer_t *left_eye;
    const comp_expression_rig_layer_t *center_highlight;
    const comp_expression_rig_layer_t *left_highlight;
    const comp_expression_rig_layer_t *center_sparkle;
    const comp_expression_rig_layer_t *left_sparkle;
    comp_expression_rig_canvas_t canvas = {18u, 18u, 3u};
    uint8_t scratch[1];
    uint8_t output[54];
    comp_expression_rig_bounds_t bounds = {0};
    uint32_t seed_a = 0x12345678u;
    uint32_t seed_b = 0x12345678u;
    int composed;
    size_t output_index;
    int output_has_ink = 0;

    left.attention = COMP_EXPRESSION_RIG_ATTENTION_LEFT;
    if (require_true(comp_expression_rig_build_plan(&profile, &center, &center_plan) &&
                         comp_expression_rig_build_plan(&profile, &left, &left_plan) &&
                         center_plan.layer_count == 13u &&
                         COMP_EXPRESSION_RIG_MAX_LAYERS >= center_plan.layer_count,
                     "center and directional source-derived plans build")) {
        return 1;
    }
    center_eye = find_layer(&center_plan, COMPONENT_LEFT_EYE_OPEN);
    left_eye = find_layer(&left_plan, COMPONENT_LEFT_EYE_OPEN);
    center_highlight = find_layer(&center_plan, COMPONENT_LEFT_HIGHLIGHT_OPEN);
    left_highlight = find_layer(&left_plan, COMPONENT_LEFT_HIGHLIGHT_OPEN);
    center_sparkle = find_layer(&center_plan, COMPONENT_LEFT_SPARKLE_OPEN);
    left_sparkle = find_layer(&left_plan, COMPONENT_LEFT_SPARKLE_OPEN);
    if (require_true(center_eye != NULL && left_eye != NULL && center_highlight != NULL &&
                         left_highlight != NULL && center_sparkle != NULL && left_sparkle != NULL && left_eye->offset_x == 0 &&
                         left_eye->offset_y == 0 && center_eye->offset_x == 0 && center_eye->offset_y == 0 &&
                         left_highlight->offset_x == -1 && left_highlight->offset_y == 2 &&
                         center_highlight->offset_x == 0 && center_highlight->offset_y == 0 &&
                         left_sparkle->offset_x == -1 &&
                         left_sparkle->offset_y == 2 && center_sparkle->offset_x == 0 &&
                         center_sparkle->offset_y == 0 &&
                         left_highlight->composite_op == COMP_EXPRESSION_RIG_COMPOSITE_ERASE,
                      "daily attention moves paired source reflections from the dynamic rest while eye bodies stay anchored")) {
        return 1;
    }
    story = left;
    story.scene = COMP_EXPRESSION_RIG_SCENE_TOUCH;
    story.emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS;
    if (require_true(comp_expression_rig_story_state(&story, COMP_EXPRESSION_RIG_PHASE_ENTRY, &center) &&
                         center.scene == COMP_EXPRESSION_RIG_SCENE_DAILY &&
                         center.emotion == COMP_EXPRESSION_RIG_EMOTION_CALM &&
                         comp_expression_rig_story_state(&story, COMP_EXPRESSION_RIG_PHASE_SUSTAIN, &left) &&
                         left.scene == COMP_EXPRESSION_RIG_SCENE_TOUCH,
                     "entry and settle return to calm while sustain keeps event context")) {
        return 1;
    }
    story.emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY;
    story.phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN;
    if (require_true(comp_expression_rig_build_plan(&profile, &story, &sleepy_plan) &&
                         find_layer(&sleepy_plan, COMPONENT_LEFT_EYE_SLEEPY) != NULL &&
                         find_layer(&sleepy_plan, COMPONENT_LEFT_EYE_OPEN) == NULL,
                         "sleepy state selects approved sleepy components")) {
        return 1;
    }
    story = left;
    story.scene = COMP_EXPRESSION_RIG_SCENE_SWIPE;
    story.emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE;
    story.phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN;
    if (require_true(comp_expression_rig_build_plan(&profile, &story, &swipe_plan) &&
                         swipe_plan.layer_count == 14u &&
                         find_layer(&swipe_plan, COMPONENT_LEFT_DETAIL_SWIPE) != NULL &&
                         find_layer(&swipe_plan, COMPONENT_RIGHT_DETAIL_SWIPE) == NULL,
                     "swipe state adds only the matching source-derived detail strokes")) {
        return 1;
    }
    if (require_true(comp_expression_rig_next_daily_state(&seed_a, 1u, &daily_a) &&
                         comp_expression_rig_next_daily_state(&seed_b, 1u, &daily_b) &&
                         memcmp(&daily_a, &daily_b, sizeof(daily_a)) == 0 &&
                         seed_a == 0x12345678u && seed_b == 0x12345678u &&
                         daily_a.attention == COMP_EXPRESSION_RIG_ATTENTION_CENTER &&
                         daily_a.energy == COMP_EXPRESSION_RIG_ENERGY_NORMAL,
                     "legacy daily helper does not consume seed or select a random movement")) {
        return 1;
    }
    composed = comp_expression_rig_build_plan(&profile, &daily_a, &left_plan) &&
               comp_expression_rig_compose_1bpp(&canvas, &left_plan, read_component, NULL,
                                                 scratch, sizeof(scratch), output, sizeof(output), &bounds);
    if (require_true(composed && bounds.has_ink && bounds.width > 0u && bounds.height > 0u,
                     "portable compositor returns source-mask bounds")) {
        return 1;
    }
    for (output_index = 0u; output_index < sizeof(output); ++output_index) {
        output_has_ink |= output[output_index] != 0xFFu;
    }
    if (require_true(output_has_ink,
                     "portable compositor paints source-mask pixels into the destination")) {
        return 1;
    }
    puts("PASS: expression Rig builds deterministic component plans and composes source masks without drawing a face");
    return 0;
}
