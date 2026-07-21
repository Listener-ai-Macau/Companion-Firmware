#include "expression_rig.h"
#include "expression_rig_performance_score.h"
#include "generated/expression_rig_v38_function_state_candidate_profile.h"

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

static int plan_is_registered(const comp_expression_rig_profile_t *profile,
                              const comp_expression_rig_plan_t *plan,
                              int *out_has_special)
{
    uint8_t layer_index;
    int has_special = 0;
    int has_fixed_nose = 0;

    if (profile == NULL || plan == NULL || out_has_special == NULL || plan->layer_count == 0u ||
        plan->layer_count > COMP_EXPRESSION_RIG_MAX_LAYERS) {
        return 0;
    }
    for (layer_index = 0u; layer_index < plan->layer_count; ++layer_index) {
        const comp_expression_rig_layer_t *layer = &plan->layers[layer_index];
        size_t component_index;
        int found = 0;

        for (component_index = 0u; component_index < profile->component_count; ++component_index) {
            const comp_expression_rig_component_info_t *component = &profile->components[component_index];
            if (component->component_id == layer->component_id) {
                found = layer->offset_x >= component->min_offset_x &&
                        layer->offset_x <= component->max_offset_x &&
                        layer->offset_y >= component->min_offset_y &&
                        layer->offset_y <= component->max_offset_y;
                break;
            }
        }
        if (!found) {
            return 0;
        }
        if (layer->component_id >= 500u) {
            has_special = 1;
        }
        if (layer->component_id == 4u && layer->offset_x == 0 && layer->offset_y == 0) {
            has_fixed_nose = 1;
        }
    }
    *out_has_special = has_special;
    return has_fixed_nose;
}

static int write_report(const char *path, unsigned int steps)
{
    FILE *file = NULL;

    if (path == NULL) {
        return 0;
    }
    if (fopen_s(&file, path, "wb") != 0 || file == NULL) {
        return 1;
    }
    fprintf(file,
            "{\n"
            "  \"schema\": \"companion.v38_function_state_wb55_profile_host.v1\",\n"
            "  \"status\": \"PASS_V38_FUNCTION_STATE_WB55_PROFILE_RUNTIME_INACTIVE\",\n"
            "  \"target\": \"STM32WB55 upper expression plan only\",\n"
            "  \"component_count\": %u,\n"
            "  \"max_component_mask_bytes\": %u,\n"
            "  \"score_count\": %u,\n"
            "  \"replayed_score_steps\": %u,\n"
            "  \"menu_entry_policy\": {\"maximum_expression_duration_ms\": 500, \"after_last_cue\": \"withdraw_expression_rig_then_show_menu_ui\", \"persistent_menu_score\": \"forbidden\"},\n"
            "  \"runtime_resource_activated\": false,\n"
            "  \"special_event_binding\": \"forbidden_until_total_machine_audit_and_owner_review\",\n"
            "  \"non_claims\": [\"no_firmware_flash\", \"no_panel_or_driver_change\", \"no_human_acceptance\"]\n"
            "}\n",
            (unsigned)COMP_V38_FUNCTION_STATE_CANDIDATE_COMPONENT_COUNT,
            (unsigned)COMP_V38_FUNCTION_STATE_CANDIDATE_MAX_MASK_BYTES,
            (unsigned)COMP_V38_FUNCTION_STATE_CANDIDATE_SCORE_COUNT, steps);
    fclose(file);
    return 0;
}

int main(int argc, char **argv)
{
    static const char *const expected_names[] = {
        "recording_input", "bottom_connector_charging", "curious_question", "alert_exclamation", "sleepy_dream_cloud",
        "menu_entry_notice", "upgrade_progress", "error_caution",
    };
    static const uint8_t expected_counts[] = {3u, 3u, 3u, 3u, 5u, 3u, 3u, 3u};
    const comp_expression_rig_profile_t *profile = comp_v38_function_state_candidate_profile();
    unsigned int replayed_steps = 0u;
    uint8_t score_index;

    if (require_true(profile != NULL && profile->component_count == COMP_V38_FUNCTION_STATE_CANDIDATE_COMPONENT_COUNT &&
                     COMP_V38_FUNCTION_STATE_CANDIDATE_MAX_MASK_BYTES == 506u &&
                     !comp_v38_function_state_candidate_runtime_activation_allowed() &&
                     comp_v38_function_state_candidate_score_count() == COMP_V38_FUNCTION_STATE_CANDIDATE_SCORE_COUNT,
                     "V38 candidate identity or inactive activation policy drifted") ||
        require_true(!comp_expression_rig_build_plan(
                         profile,
                         &(comp_expression_rig_state_t){.scene = COMP_EXPRESSION_RIG_SCENE_MENU,
                             .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
                             .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
                             .energy = COMP_EXPRESSION_RIG_ENERGY_LOW,
                             .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN},
                         &(comp_expression_rig_plan_t){0}),
                     "generic Menu state must fail closed; only a finite entry score may exist")) {
        return 1;
    }
    for (score_index = 0u; score_index < comp_v38_function_state_candidate_score_count(); ++score_index) {
        const comp_v38_function_state_candidate_score_t *descriptor =
            comp_v38_function_state_candidate_score(score_index);
        uint8_t step_index;
        unsigned int score_duration = 0u;

        if (require_true(descriptor != NULL && descriptor->score != NULL && descriptor->frames != NULL &&
                         strcmp(descriptor->name, expected_names[score_index]) == 0 &&
                         descriptor->score->step_count == expected_counts[score_index] &&
                         descriptor->frame_count == expected_counts[score_index] &&
                         descriptor->withdraw_expression_rig_after_last_cue == (score_index == 5u),
                         "V38 score descriptor drifted from registered source plans")) {
            return 1;
        }
        for (step_index = 0u; step_index < descriptor->score->step_count; ++step_index) {
            comp_expression_rig_plan_t plan;
            int has_special = 0;

            if (require_true(comp_expression_rig_build_registered_score_step(
                                 profile, descriptor->score, step_index, NULL, &plan) &&
                             plan_is_registered(profile, &plan, &has_special) &&
                             (score_index == 4u && step_index == 0u ? !has_special : has_special) &&
                             descriptor->frames[step_index].duration_ms == descriptor->score->steps[step_index].duration_ms &&
                             (score_index != 5u || descriptor->score->steps[step_index].state.scene == COMP_EXPRESSION_RIG_SCENE_TOUCH),
                             "every V38 step must preserve legal source masks, a fixed nose and declared duration")) {
                return 1;
            }
            if (score_index == 7u &&
                require_true(plan.layer_count >= 13u && plan.layers[0].component_id == 554u && plan.layers[1].component_id == 555u &&
                             plan.layers[11].component_id == 556u,
                             "Error score must use source-derived brows and mouth rather than a generic daily face")) {
                return 1;
            }
            score_duration += descriptor->frames[step_index].duration_ms;
            replayed_steps++;
        }
        if (score_index == 5u && require_true(score_duration <= 500u,
                                               "Menu entry score must withdraw before persistent Menu UI")) {
            return 1;
        }
    }
    if (require_true(replayed_steps == 26u &&
                     comp_v38_function_state_candidate_score(COMP_V38_FUNCTION_STATE_CANDIDATE_SCORE_COUNT) == NULL,
                     "V38 candidate score range must fail closed") ||
        write_report(argc == 2 ? argv[1] : NULL, replayed_steps) != 0) {
        return 1;
    }
    puts("PASS: WB55 V38 candidate replays all source-component scores; Menu is only a finite pre-UI entry cue while runtime stays inactive");
    return 0;
}
