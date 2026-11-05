#include "expression_rig.h"
#include "generated/expression_rig_v41_directional_gaze_candidate_profile.h"

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

static int has_component(const comp_expression_rig_plan_t *plan, uint16_t component_id)
{
    uint8_t index;

    for (index = 0u; plan != NULL && index < plan->layer_count; ++index) {
        if (plan->layers[index].component_id == component_id) {
            return 1;
        }
    }
    return 0;
}

static int has_offset(const comp_expression_rig_plan_t *plan, uint16_t component_id, int8_t offset_x, int8_t offset_y)
{
    uint8_t index;

    for (index = 0u; plan != NULL && index < plan->layer_count; ++index) {
        if (plan->layers[index].component_id == component_id && plan->layers[index].offset_x == offset_x &&
            plan->layers[index].offset_y == offset_y) {
            return 1;
        }
    }
    return 0;
}

static int fixed_nose(const comp_expression_rig_plan_t *plan)
{
    return has_offset(plan, 4u, 0, 0);
}

static const comp_v41_two_track_candidate_story_t *find_story(const char *name)
{
    uint8_t index;

    for (index = 0u; index < COMP_V41_TWO_TRACK_CANDIDATE_STORY_COUNT; ++index) {
        const comp_v41_two_track_candidate_story_t *story = comp_v41_two_track_candidate_story(index);

        if (story != NULL && story->name != NULL && strcmp(story->name, name) == 0) {
            return story;
        }
    }
    return NULL;
}

static int require_gaze(uint8_t expression_track_index, comp_expression_rig_attention_t attention,
                        int8_t primary_x, int8_t primary_y, int8_t sparkle_x, int8_t sparkle_y)
{
    comp_expression_rig_plan_t plan;

    if (!comp_v41_two_track_candidate_build_composed_frame(expression_track_index, 2u,
            COMP_V41_TWO_TRACK_CANDIDATE_NO_FUNCTIONAL_TRACK,
            COMP_V41_TWO_TRACK_CANDIDATE_NO_FUNCTIONAL_TRACK, NULL, &plan)) {
        return 0;
    }
    return plan.effective_state.attention == attention && fixed_nose(&plan) &&
           has_offset(&plan, 1u, primary_x, primary_y) && has_offset(&plan, 5u, primary_x, primary_y) &&
           has_offset(&plan, 3u, sparkle_x, sparkle_y) && has_offset(&plan, 7u, sparkle_x, sparkle_y);
}

static int write_report(const char *path)
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
            "  \"schema\": \"companion.v41_directional_gaze_wb55_profile_host.v1\",\n"
            "  \"status\": \"PASS_V41_DIRECTIONAL_GAZE_WB55_PROFILE_RUNTIME_INACTIVE\",\n"
            "  \"component_count\": %u,\n"
            "  \"expression_track_count\": %u,\n"
            "  \"functional_track_count\": %u,\n"
            "  \"story_count\": %u,\n"
            "  \"preview_frame_count\": 53,\n"
            "  \"five_gaze_states\": [\"center\", \"left\", \"right\", \"up\", \"down\"],\n"
            "  \"fixed_v22_nose\": true,\n"
            "  \"two_track_independence\": true,\n"
            "  \"menu_entry_policy\": {\"state_scene\": \"touch\", \"maximum_expression_duration_ms\": 500, \"after_last_cue\": \"withdraw_expression_and_functional_tracks_then_show_menu_ui\"},\n"
            "  \"runtime_resource_activated\": false,\n"
            "  \"non_claims\": [\"no_firmware_flash\", \"no_panel_or_driver_change\", \"no_human_acceptance\"]\n"
            "}\n",
            (unsigned)COMP_V41_TWO_TRACK_CANDIDATE_COMPONENT_COUNT,
            (unsigned)COMP_V41_TWO_TRACK_CANDIDATE_EXPRESSION_TRACK_COUNT,
            (unsigned)COMP_V41_TWO_TRACK_CANDIDATE_FUNCTIONAL_TRACK_COUNT,
            (unsigned)COMP_V41_TWO_TRACK_CANDIDATE_STORY_COUNT);
    fclose(file);
    return 0;
}

int main(int argc, char **argv)
{
    const comp_expression_rig_profile_t *profile = comp_v41_two_track_candidate_profile();
    const comp_v41_two_track_candidate_story_t *menu;
    comp_expression_rig_plan_t calm;
    comp_expression_rig_plan_t recording_warm;
    unsigned int menu_duration = 0u;
    uint8_t story_index;

    if (require_true(profile != NULL && !comp_v41_two_track_candidate_runtime_activation_allowed() &&
                     profile->component_count == COMP_V41_TWO_TRACK_CANDIDATE_COMPONENT_COUNT &&
                     COMP_V41_TWO_TRACK_CANDIDATE_EXPRESSION_TRACK_COUNT == 11u &&
                     COMP_V41_TWO_TRACK_CANDIDATE_FUNCTIONAL_TRACK_COUNT == 4u &&
                     COMP_V41_TWO_TRACK_CANDIDATE_STORY_COUNT == 17u &&
                     !comp_expression_rig_build_plan(profile,
                         &(comp_expression_rig_state_t){.scene = COMP_EXPRESSION_RIG_SCENE_MENU,
                             .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
                             .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
                             .energy = COMP_EXPRESSION_RIG_ENERGY_LOW,
                             .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN},
                         &(comp_expression_rig_plan_t){0}),
                     "V41 must remain inactive and generic Menu synthesis must fail closed")) {
        return 1;
    }
    if (require_true(require_gaze(6u, COMP_EXPRESSION_RIG_ATTENTION_CENTER, 1, 0, 1, 0) &&
                     require_gaze(7u, COMP_EXPRESSION_RIG_ATTENTION_LEFT, -2, 2, -5, 3) &&
                     require_gaze(8u, COMP_EXPRESSION_RIG_ATTENTION_RIGHT, 5, 2, 5, 3) &&
                     require_gaze(9u, COMP_EXPRESSION_RIG_ATTENTION_UP, 1, -3, 1, -5) &&
                     require_gaze(10u, COMP_EXPRESSION_RIG_ATTENTION_DOWN, 1, 4, 1, 5),
                     "V41 must build all five deterministic source-only Daily gaze endpoints")) {
        return 1;
    }
    if (require_true(comp_v41_two_track_candidate_build_composed_frame(0u, 0u, 0u, 0u, NULL, &calm) &&
                     comp_v41_two_track_candidate_build_composed_frame(1u, 0u, 0u, 0u, NULL, &recording_warm) &&
                     fixed_nose(&calm) && fixed_nose(&recording_warm) && has_component(&calm, 557u) &&
                     has_component(&recording_warm, 557u) && has_component(&calm, 13u) &&
                     has_component(&recording_warm, 33u) && !has_component(&calm, 33u) &&
                     !has_component(&recording_warm, 13u),
                     "the same recording decoration must stay independent of calm and warm face selection")) {
        return 1;
    }
    menu = find_story("menu_entry_notice");
    if (require_true(menu != NULL && menu->uses_menu_entry_track && menu->withdraw_all_tracks_after_last_cue &&
                     menu->frame_count == 3u, "Menu must remain only a finite entry cue")) {
        return 1;
    }
    for (story_index = 0u; story_index < menu->frame_count; ++story_index) {
        comp_expression_rig_plan_t plan;

        menu_duration += menu->frames[story_index].duration_ms;
        if (require_true(comp_v41_two_track_candidate_build_story_frame(menu, story_index, NULL, &plan) &&
                         has_component(&plan, (uint16_t)(545u + story_index)) && fixed_nose(&plan),
                         "every Menu cue frame must use registered components and preserve the nose")) {
            return 1;
        }
    }
    if (require_true(menu_duration <= 500u, "Menu must withdraw both tracks before the UI owns the screen")) {
        return 1;
    }
    for (story_index = 0u; story_index < COMP_V41_TWO_TRACK_CANDIDATE_STORY_COUNT; ++story_index) {
        const comp_v41_two_track_candidate_story_t *story = comp_v41_two_track_candidate_story(story_index);
        uint8_t frame_index;

        if (require_true(story != NULL && story->frames != NULL && story->frame_count > 0u,
                         "V41 story descriptor must remain registered")) {
            return 1;
        }
        for (frame_index = 0u; frame_index < story->frame_count; ++frame_index) {
            if (require_true(comp_v41_two_track_candidate_build_story_frame(story, frame_index, NULL, &calm) &&
                             calm.layer_count <= COMP_EXPRESSION_RIG_MAX_LAYERS && fixed_nose(&calm),
                             "every V41 frame must remain a legal source-only two-track plan")) {
                return 1;
            }
        }
    }
    if (write_report(argc == 2 ? argv[1] : NULL) != 0) {
        return 1;
    }
    puts("PASS: V41 builds five deterministic Daily gaze endpoints with independent functional decoration");
    return 0;
}
