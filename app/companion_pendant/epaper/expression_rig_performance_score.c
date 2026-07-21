#include "expression_rig_performance_score.h"

#include <string.h>

const char *comp_expression_rig_score_phase_name(
    comp_expression_rig_score_phase_t phase)
{
    static const char *const k_phase_names[] = {
        "entry",
        "prepare",
        "lead",
        "response",
        "accent",
        "hold",
        "release",
        "return",
        "settle",
    };

    if (phase >= COMP_EXPRESSION_RIG_SCORE_PHASE_COUNT) {
        return "invalid";
    }
    return k_phase_names[phase];
}

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

static comp_expression_rig_layer_t *find_layer(comp_expression_rig_plan_t *plan,
                                                uint16_t component_id)
{
    uint8_t index;

    if (plan == NULL) {
        return NULL;
    }
    for (index = 0u; index < plan->layer_count; ++index) {
        if (plan->layers[index].component_id == component_id) {
            return &plan->layers[index];
        }
    }
    return NULL;
}

static bool pose_is_legal(const comp_expression_rig_component_info_t *component,
                          const comp_expression_rig_score_pose_t *pose)
{
    if (component == NULL || pose == NULL ||
        pose->offset_x < component->min_offset_x || pose->offset_x > component->max_offset_x ||
        pose->offset_y < component->min_offset_y || pose->offset_y > component->max_offset_y) {
        return false;
    }
    return true;
}

bool comp_expression_rig_apply_score_step(
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_plan_t *entry_plan,
    const comp_expression_rig_performance_score_t *score,
    uint8_t step_index,
    comp_expression_rig_plan_t *out_plan)
{
    const comp_expression_rig_score_step_t *step;
    uint8_t pose_index;

    if (profile == NULL || entry_plan == NULL || score == NULL || out_plan == NULL ||
        score->steps == NULL || step_index >= score->step_count ||
        entry_plan->layer_count == 0u || entry_plan->layer_count > COMP_EXPRESSION_RIG_MAX_LAYERS ||
        entry_plan->effective_state.scene != COMP_EXPRESSION_RIG_SCENE_DAILY ||
        entry_plan->effective_state.phase != COMP_EXPRESSION_RIG_PHASE_ENTRY) {
        return false;
    }
    step = &score->steps[step_index];
    if (step->phase >= COMP_EXPRESSION_RIG_SCORE_PHASE_COUNT ||
        step->duration_ms < 80u || step->poses == NULL && step->pose_count != 0u) {
        return false;
    }
    memcpy(out_plan, entry_plan, sizeof(*out_plan));
    for (pose_index = 0u; pose_index < step->pose_count; ++pose_index) {
        const comp_expression_rig_score_pose_t *pose = &step->poses[pose_index];
        const comp_expression_rig_component_info_t *component = find_component(profile, pose->component_id);
        comp_expression_rig_layer_t *layer = find_layer(out_plan, pose->component_id);

        if (!pose_is_legal(component, pose) || layer == NULL ||
            layer->base_x != component->base_x || layer->base_y != component->base_y ||
            (component->role == COMP_EXPRESSION_RIG_ROLE_LEFT_EYE ||
             component->role == COMP_EXPRESSION_RIG_ROLE_RIGHT_EYE) &&
                (pose->offset_x != layer->offset_x || pose->offset_y != layer->offset_y)) {
            return false;
        }
        layer->offset_x = pose->offset_x;
        layer->offset_y = pose->offset_y;
    }
    return true;
}

bool comp_expression_rig_build_registered_score_step(
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_registered_performance_score_t *score,
    uint8_t step_index,
    const comp_expression_rig_state_t *dynamic_context,
    comp_expression_rig_plan_t *out_plan)
{
    const comp_expression_rig_registered_score_step_t *step;
    comp_expression_rig_state_t state;

    if (profile == NULL || score == NULL || out_plan == NULL || score->steps == NULL ||
        step_index >= score->step_count) {
        return false;
    }
    step = &score->steps[step_index];
    if (step->phase >= COMP_EXPRESSION_RIG_SCORE_PHASE_COUNT || step->duration_ms < 80u ||
        step->pose == NULL || step->state.phase != COMP_EXPRESSION_RIG_PHASE_SUSTAIN) {
        return false;
    }
    state = step->state;
    if (dynamic_context != NULL) {
        if (dynamic_context->energy >= COMP_EXPRESSION_RIG_ENERGY_COUNT ||
            dynamic_context->interaction_memory > 2u) {
            return false;
        }
        state.energy = dynamic_context->energy;
        state.interaction_memory = dynamic_context->interaction_memory;
    }
    return comp_expression_rig_build_registered_pose_plan(profile, &state, step->pose, out_plan);
}
