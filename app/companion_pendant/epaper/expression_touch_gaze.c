#include "expression_touch_gaze.h"

static int16_t absolute_delta(uint16_t value, uint16_t center)
{
    return value >= center ? (int16_t)(value - center) : (int16_t)(center - value);
}

static int16_t rounded_division(int32_t value, int16_t divisor)
{
    if (value >= 0) {
        return (int16_t)((value + divisor / 2) / divisor);
    }
    return (int16_t)(-((-value + divisor / 2) / divisor));
}

static int8_t map_axis(uint16_t value, int8_t negative, int8_t positive, int8_t center)
{
    if (value <= COMP_EXPRESSION_RIG_TOUCH_CENTER_X) {
        return (int8_t)(center + rounded_division(
            ((int32_t)value - (int32_t)COMP_EXPRESSION_RIG_TOUCH_CENTER_X) *
                ((int32_t)center - (int32_t)negative),
            (int16_t)COMP_EXPRESSION_RIG_TOUCH_CENTER_X));
    }
    return (int8_t)(center + rounded_division(
        ((int32_t)value - (int32_t)COMP_EXPRESSION_RIG_TOUCH_CENTER_X) *
            ((int32_t)positive - (int32_t)center),
        (int16_t)(COMP_EXPRESSION_RIG_TOUCH_CANVAS_WIDTH - 1u - COMP_EXPRESSION_RIG_TOUCH_CENTER_X)));
}

static comp_expression_rig_attention_t attention_for_point(uint16_t x, uint16_t y)
{
    int16_t dx = (int16_t)x - (int16_t)COMP_EXPRESSION_RIG_TOUCH_CENTER_X;
    int16_t dy = (int16_t)y - (int16_t)COMP_EXPRESSION_RIG_TOUCH_CENTER_Y;
    int16_t abs_x = absolute_delta(x, COMP_EXPRESSION_RIG_TOUCH_CENTER_X);
    int16_t abs_y = absolute_delta(y, COMP_EXPRESSION_RIG_TOUCH_CENTER_Y);

    if (abs_x == 0 && abs_y == 0) {
        return COMP_EXPRESSION_RIG_ATTENTION_CENTER;
    }
    if (abs_x >= abs_y) {
        return dx < 0 ? COMP_EXPRESSION_RIG_ATTENTION_LEFT : COMP_EXPRESSION_RIG_ATTENTION_RIGHT;
    }
    return dy < 0 ? COMP_EXPRESSION_RIG_ATTENTION_UP : COMP_EXPRESSION_RIG_ATTENTION_DOWN;
}

static void target_for_center(comp_expression_rig_touch_gaze_target_t *target)
{
    *target = (comp_expression_rig_touch_gaze_target_t){
        .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
        .touch_x = COMP_EXPRESSION_RIG_TOUCH_CENTER_X,
        .touch_y = COMP_EXPRESSION_RIG_TOUCH_CENTER_Y,
        .primary_x = 1,
        .primary_y = 0,
        .sparkle_x = 1,
        .sparkle_y = 0,
        .engaged = false,
    };
}

static bool target_is_valid(const comp_expression_rig_touch_gaze_target_t *target)
{
    if (target == NULL || target->attention >= COMP_EXPRESSION_RIG_ATTENTION_COUNT ||
        target->touch_x >= COMP_EXPRESSION_RIG_TOUCH_CANVAS_WIDTH ||
        target->touch_y >= COMP_EXPRESSION_RIG_TOUCH_CANVAS_HEIGHT) {
        return false;
    }
    return target->primary_x == map_axis(target->touch_x, -2, 5, 1) &&
           target->primary_y == map_axis(target->touch_y, -3, 4, 0) &&
           target->sparkle_x == map_axis(target->touch_x, -6, 5, 1) &&
           target->sparkle_y == map_axis(target->touch_y, -6, 6, 0) &&
           target->attention == attention_for_point(target->touch_x, target->touch_y) &&
           (target->engaged || (target->touch_x == COMP_EXPRESSION_RIG_TOUCH_CENTER_X &&
                                target->touch_y == COMP_EXPRESSION_RIG_TOUCH_CENTER_Y));
}

bool comp_expression_rig_touch_gaze_map(
    const comp_expression_rig_touch_sample_t *sample,
    comp_expression_rig_touch_gaze_target_t *out_target)
{
    if (sample == NULL || out_target == NULL || sample->x >= COMP_EXPRESSION_RIG_TOUCH_CANVAS_WIDTH ||
        sample->y >= COMP_EXPRESSION_RIG_TOUCH_CANVAS_HEIGHT) {
        return false;
    }
    if (!sample->pressed) {
        target_for_center(out_target);
        return true;
    }
    *out_target = (comp_expression_rig_touch_gaze_target_t){
        .attention = attention_for_point(sample->x, sample->y),
        .touch_x = sample->x,
        .touch_y = sample->y,
        .primary_x = map_axis(sample->x, -2, 5, 1),
        .primary_y = map_axis(sample->y, -3, 4, 0),
        .sparkle_x = map_axis(sample->x, -6, 5, 1),
        .sparkle_y = map_axis(sample->y, -6, 6, 0),
        .engaged = true,
    };
    return true;
}

static const comp_expression_rig_component_info_t *find_component(
    const comp_expression_rig_profile_t *profile, uint16_t component_id)
{
    size_t index;

    for (index = 0u; index < profile->component_count; ++index) {
        if (profile->components[index].component_id == component_id) {
            return &profile->components[index];
        }
    }
    return NULL;
}

static bool set_offset(const comp_expression_rig_component_info_t *component,
                       comp_expression_rig_layer_t *layer,
                       int8_t offset_x, int8_t offset_y)
{
    if (component == NULL || layer == NULL || offset_x < component->min_offset_x ||
        offset_x > component->max_offset_x || offset_y < component->min_offset_y ||
        offset_y > component->max_offset_y) {
        return false;
    }
    layer->offset_x = offset_x;
    layer->offset_y = offset_y;
    return true;
}

bool comp_expression_rig_touch_gaze_apply(
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_touch_gaze_target_t *target,
    comp_expression_rig_plan_t *in_out_plan)
{
    uint8_t primary_count = 0u;
    uint8_t sparkle_count = 0u;
    uint8_t index;

    if (profile == NULL || profile->components == NULL || profile->component_count == 0u ||
        !target_is_valid(target) || in_out_plan == NULL || in_out_plan->layer_count == 0u ||
        in_out_plan->layer_count > COMP_EXPRESSION_RIG_MAX_LAYERS) {
        return false;
    }
    for (index = 0u; index < in_out_plan->layer_count; ++index) {
        comp_expression_rig_layer_t *layer = &in_out_plan->layers[index];
        const comp_expression_rig_component_info_t *component = find_component(profile, layer->component_id);

        if (component == NULL) {
            return false;
        }
        if (component->role == COMP_EXPRESSION_RIG_ROLE_LEFT_HIGHLIGHT ||
            component->role == COMP_EXPRESSION_RIG_ROLE_RIGHT_HIGHLIGHT) {
            if (!set_offset(component, layer, target->primary_x, target->primary_y)) {
                return false;
            }
            ++primary_count;
        } else if (component->role == COMP_EXPRESSION_RIG_ROLE_LEFT_SPARKLE ||
                   component->role == COMP_EXPRESSION_RIG_ROLE_RIGHT_SPARKLE) {
            if (!set_offset(component, layer, target->sparkle_x, target->sparkle_y)) {
                return false;
            }
            ++sparkle_count;
        }
    }
    return primary_count == 2u && sparkle_count == 2u;
}
