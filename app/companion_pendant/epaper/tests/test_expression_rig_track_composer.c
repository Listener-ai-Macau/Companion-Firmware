#include "expression_rig_track_composer.h"

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

int main(void)
{
    static const comp_expression_rig_component_info_t components[] = {
        {.component_id = 1u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_BROW, .base_x = 20, .base_y = 20, .z_index = 20u},
        {.component_id = 2u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW, .base_x = 40, .base_y = 20, .z_index = 20u},
        {.component_id = 3u, .role = COMP_EXPRESSION_RIG_ROLE_LEFT_EYE, .base_x = 20, .base_y = 40, .z_index = 30u},
        {.component_id = 4u, .role = COMP_EXPRESSION_RIG_ROLE_RIGHT_EYE, .base_x = 40, .base_y = 40, .z_index = 30u},
        {.component_id = 5u, .role = COMP_EXPRESSION_RIG_ROLE_NOSE, .base_x = 30, .base_y = 50, .z_index = 50u},
        {.component_id = 6u, .role = COMP_EXPRESSION_RIG_ROLE_MOUTH, .base_x = 30, .base_y = 60, .z_index = 60u},
        {.component_id = 500u, .role = COMP_EXPRESSION_RIG_ROLE_CHARM, .base_x = 30, .base_y = 5, .z_index = 90u},
    };
    static const comp_expression_rig_profile_t profile = {
        .components = components,
        .component_count = sizeof(components) / sizeof(components[0]),
    };
    comp_expression_rig_plan_t expression = {
        .input_state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
                        .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL,
                        .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN},
        .effective_state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
                            .attention = COMP_EXPRESSION_RIG_ATTENTION_RIGHT, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL,
                            .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN},
        .layers = {
            {.component_id = 1u, .base_x = 20, .base_y = 20}, {.component_id = 2u, .base_x = 40, .base_y = 20},
            {.component_id = 3u, .base_x = 20, .base_y = 40}, {.component_id = 4u, .base_x = 40, .base_y = 40},
            {.component_id = 5u, .base_x = 30, .base_y = 50}, {.component_id = 6u, .base_x = 30, .base_y = 60},
        },
        .layer_count = 6u,
    };
    comp_expression_rig_plan_t functional = {
        .input_state = {.scene = COMP_EXPRESSION_RIG_SCENE_RECORDING, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED,
                        .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW,
                        .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN},
        .effective_state = {.scene = COMP_EXPRESSION_RIG_SCENE_RECORDING, .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED,
                            .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW,
                            .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN},
        .layers = {{.component_id = 500u, .base_x = 30, .base_y = 5}},
        .layer_count = 1u,
    };
    comp_expression_rig_plan_t merged;
    comp_expression_rig_plan_t invalid;

    if (require_true(comp_expression_rig_merge_tracks(&profile, &expression, &functional, &merged) &&
                     merged.layer_count == 7u && merged.layers[0].component_id == 1u &&
                     merged.layers[6].component_id == 500u &&
                     memcmp(&merged.effective_state, &expression.effective_state, sizeof(merged.effective_state)) == 0,
                     "functional decoration merges after an independent expression plan without taking state ownership")) {
        return 1;
    }
    if (require_true(comp_expression_rig_merge_tracks(&profile, &expression, NULL, &merged) &&
                     merged.layer_count == expression.layer_count && merged.layers[0].component_id == 1u,
                     "expression track can run independently with no functional decoration")) {
        return 1;
    }
    invalid = functional;
    invalid.layers[0].component_id = 1u;
    if (require_true(!comp_expression_rig_merge_tracks(&profile, &expression, &invalid, &merged),
                     "track merger fails closed when a functional plan tries to duplicate a face component")) {
        return 1;
    }
    invalid = functional;
    invalid.layers[0].offset_y = 1;
    if (require_true(!comp_expression_rig_merge_tracks(&profile, &expression, &invalid, &merged),
                     "track merger rejects offsets outside registered source bounds")) {
        return 1;
    }
    puts("PASS: two-track composition preserves expression state and merges only registered source layers");
    return 0;
}
