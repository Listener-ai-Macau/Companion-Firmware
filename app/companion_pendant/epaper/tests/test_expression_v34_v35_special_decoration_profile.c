#include "expression_rig.h"
#include "expression_rig_performance_score.h"
#include "generated/expression_rig_v34_v35_special_decoration_candidate_profile.h"

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
                              int *out_has_decoration)
{
    uint8_t layer_index;
    int has_decoration = 0;
    int has_fixed_nose = 0;

    if (profile == NULL || plan == NULL || out_has_decoration == NULL || plan->layer_count == 0u ||
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
            has_decoration = 1;
        }
        if (layer->component_id == 4u && layer->offset_x == 0 && layer->offset_y == 0) {
            has_fixed_nose = 1;
        }
    }
    *out_has_decoration = has_decoration;
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
            "  \"schema\": \"companion.v34_v35_special_decoration_wb55_profile_host.v1\",\n"
            "  \"status\": \"PASS_V34_V35_SPECIAL_DECORATION_WB55_PROFILE_RUNTIME_INACTIVE\",\n"
            "  \"target\": \"STM32WB55 upper expression plan only\",\n"
            "  \"component_count\": %u,\n"
            "  \"score_count\": %u,\n"
            "  \"replayed_score_steps\": %u,\n"
            "  \"runtime_resource_activated\": false,\n"
            "  \"special_event_binding\": \"forbidden_until_browser_wb55_component_plan_parity_and_owner_review\",\n"
            "  \"dream_cloud\": \"fail_closed_pending_v9_sleep_profile\",\n"
            "  \"non_claims\": [\"no_firmware_flash\", \"no_panel_or_driver_change\", \"no_human_acceptance\"]\n"
            "}\n",
            (unsigned)COMP_V34_V35_SPECIAL_DECORATION_CANDIDATE_COMPONENT_COUNT,
            (unsigned)COMP_V34_V35_SPECIAL_DECORATION_CANDIDATE_SCORE_COUNT, steps);
    fclose(file);
    return 0;
}

int main(int argc, char **argv)
{
    static const char *const expected_names[] = {
        "recording_input", "bottom_connector_charging", "curious_question", "alert_exclamation",
    };
    const comp_expression_rig_profile_t *profile =
        comp_v34_v35_special_decoration_candidate_profile();
    unsigned int replayed_steps = 0u;
    uint8_t score_index;

    if (require_true(profile != NULL && profile->component_count ==
                         COMP_V34_V35_SPECIAL_DECORATION_CANDIDATE_COMPONENT_COUNT &&
                         !comp_v34_v35_special_decoration_candidate_runtime_activation_allowed() &&
                         comp_v34_v35_special_decoration_candidate_score_count() ==
                         COMP_V34_V35_SPECIAL_DECORATION_CANDIDATE_SCORE_COUNT,
                     "candidate profile identity or inactive activation policy drifted")) {
        return 1;
    }
    if (require_true(!comp_expression_rig_build_plan(
                         profile,
                         &(comp_expression_rig_state_t){
                             .scene = COMP_EXPRESSION_RIG_SCENE_RECORDING,
                             .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED,
                             .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
                             .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL,
                             .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN,
                         },
                         &(comp_expression_rig_plan_t){0}),
                     "generic product-state synthesis must fail closed for special candidates")) {
        return 1;
    }

    for (score_index = 0u;
         score_index < comp_v34_v35_special_decoration_candidate_score_count();
         ++score_index) {
        const comp_v34_v35_special_decoration_candidate_score_t *descriptor =
            comp_v34_v35_special_decoration_candidate_score(score_index);
        uint8_t step_index;

        if (require_true(descriptor != NULL && descriptor->score != NULL &&
                         strcmp(descriptor->name, expected_names[score_index]) == 0 &&
                         descriptor->prelude_bridge != NULL && descriptor->score->step_count == 3u,
                         "candidate score descriptor drifted from the source contract")) {
            return 1;
        }
        for (step_index = 0u; step_index < descriptor->score->step_count; ++step_index) {
            comp_expression_rig_plan_t plan;
            int has_decoration = 0;

            if (require_true(comp_expression_rig_build_registered_score_step(
                                 profile, descriptor->score, step_index, NULL, &plan) &&
                             plan_is_registered(profile, &plan, &has_decoration) && has_decoration,
                             "every candidate score step must contain only legal source masks, fixed nose, and a marker")) {
                return 1;
            }
            replayed_steps++;
        }
        if (require_true(!comp_expression_rig_build_registered_score_step(
                             profile, descriptor->score, descriptor->score->step_count, NULL,
                             &(comp_expression_rig_plan_t){0}),
                         "unregistered special score steps must fail closed")) {
            return 1;
        }
    }
    if (require_true(comp_v34_v35_special_decoration_candidate_score(
                         COMP_V34_V35_SPECIAL_DECORATION_CANDIDATE_SCORE_COUNT) == NULL,
                     "out-of-range special score lookup must fail closed") ||
        write_report(argc == 2 ? argv[1] : NULL, replayed_steps) != 0) {
        return 1;
    }
    puts("PASS: WB55 candidate profile replays four registered V34/V35 source-component scores while runtime binding and dream-cloud stay fail-closed");
    return 0;
}
