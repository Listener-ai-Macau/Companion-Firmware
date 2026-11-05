#include "expression_rig_track_composer.h"

#include <string.h>

static const comp_expression_rig_component_info_t *find_component(
    const comp_expression_rig_profile_t *profile,
    uint16_t component_id)
{
    size_t index;

    if (profile == NULL || profile->components == NULL) {
        return NULL;
    }
    for (index = 0u; index < profile->component_count; ++index) {
        if (profile->components[index].component_id == component_id) {
            return &profile->components[index];
        }
    }
    return NULL;
}

static bool plan_layers_are_registered(const comp_expression_rig_profile_t *profile,
                                       const comp_expression_rig_plan_t *plan)
{
    uint8_t index;

    if (profile == NULL || plan == NULL || plan->layer_count == 0u ||
        plan->layer_count > COMP_EXPRESSION_RIG_MAX_LAYERS) {
        return false;
    }
    for (index = 0u; index < plan->layer_count; ++index) {
        const comp_expression_rig_layer_t *layer = &plan->layers[index];
        const comp_expression_rig_component_info_t *component = find_component(profile, layer->component_id);

        if (component == NULL || layer->base_x != component->base_x || layer->base_y != component->base_y ||
            layer->composite_op != component->composite_op ||
            layer->offset_x < component->min_offset_x || layer->offset_x > component->max_offset_x ||
            layer->offset_y < component->min_offset_y || layer->offset_y > component->max_offset_y) {
            return false;
        }
    }
    return true;
}

static bool append_sorted_layer(const comp_expression_rig_profile_t *profile,
                                comp_expression_rig_plan_t *plan,
                                const comp_expression_rig_layer_t *layer)
{
    const comp_expression_rig_component_info_t *component = find_component(profile, layer->component_id);
    uint8_t insert_index;
    uint8_t index;

    if (component == NULL || plan == NULL || layer == NULL || plan->layer_count >= COMP_EXPRESSION_RIG_MAX_LAYERS) {
        return false;
    }
    for (index = 0u; index < plan->layer_count; ++index) {
        const comp_expression_rig_component_info_t *existing = find_component(profile, plan->layers[index].component_id);

        if (existing == NULL || plan->layers[index].component_id == layer->component_id) {
            return false;
        }
    }
    insert_index = plan->layer_count;
    for (index = 0u; index < plan->layer_count; ++index) {
        const comp_expression_rig_component_info_t *existing = find_component(profile, plan->layers[index].component_id);

        if (component->z_index < existing->z_index) {
            insert_index = index;
            break;
        }
    }
    for (index = plan->layer_count; index > insert_index; --index) {
        plan->layers[index] = plan->layers[(uint8_t)(index - 1u)];
    }
    plan->layers[insert_index] = *layer;
    plan->layer_count++;
    return true;
}

bool comp_expression_rig_merge_tracks(
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_plan_t *expression_plan,
    const comp_expression_rig_plan_t *functional_decoration_plan,
    comp_expression_rig_plan_t *out_plan)
{
    comp_expression_rig_plan_t merged;
    uint8_t index;

    if (profile == NULL || expression_plan == NULL || out_plan == NULL ||
        !plan_layers_are_registered(profile, expression_plan) ||
        (functional_decoration_plan != NULL &&
         !plan_layers_are_registered(profile, functional_decoration_plan)) ||
        expression_plan->layer_count +
            (functional_decoration_plan == NULL ? 0u : functional_decoration_plan->layer_count) >
            COMP_EXPRESSION_RIG_MAX_LAYERS) {
        return false;
    }
    memset(&merged, 0, sizeof(merged));
    merged.input_state = expression_plan->input_state;
    merged.effective_state = expression_plan->effective_state;
    for (index = 0u; index < expression_plan->layer_count; ++index) {
        if (!append_sorted_layer(profile, &merged, &expression_plan->layers[index])) {
            return false;
        }
    }
    if (functional_decoration_plan != NULL) {
        for (index = 0u; index < functional_decoration_plan->layer_count; ++index) {
            if (!append_sorted_layer(profile, &merged, &functional_decoration_plan->layers[index])) {
                return false;
            }
        }
    }
    *out_plan = merged;
    return true;
}
