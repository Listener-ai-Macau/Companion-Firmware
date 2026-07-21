#include "expression_rig.h"
#include "expression_rig_track_composer.h"
#include "generated/expression_rig_v40_two_track_candidate_profile.h"

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

static int fixed_nose(const comp_expression_rig_plan_t *plan)
{
    uint8_t index;

    for (index = 0u; plan != NULL && index < plan->layer_count; ++index) {
        if (plan->layers[index].component_id == 4u && plan->layers[index].offset_x == 0 &&
            plan->layers[index].offset_y == 0) {
            return 1;
        }
    }
    return 0;
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
            "  \"schema\": \"companion.v40_two_track_wb55_profile_host.v1\",\n"
            "  \"status\": \"PASS_V40_TWO_TRACK_WB55_PROFILE_RUNTIME_INACTIVE\",\n"
            "  \"component_count\": %u,\n"
            "  \"expression_track_count\": %u,\n"
            "  \"functional_track_count\": %u,\n"
            "  \"story_count\": %u,\n"
            "  \"preview_frame_count\": 38,\n"
            "  \"two_track_independence\": true,\n"
            "  \"menu_entry_policy\": {\"state_scene\": \"touch\", \"maximum_expression_duration_ms\": 500, \"after_last_cue\": \"withdraw_expression_and_functional_tracks_then_show_menu_ui\"},\n"
            "  \"runtime_resource_activated\": false,\n"
            "  \"non_claims\": [\"no_firmware_flash\", \"no_panel_or_driver_change\", \"no_human_acceptance\"]\n"
            "}\n",
            (unsigned)COMP_V40_TWO_TRACK_CANDIDATE_COMPONENT_COUNT,
            (unsigned)COMP_V40_TWO_TRACK_CANDIDATE_EXPRESSION_TRACK_COUNT,
            (unsigned)COMP_V40_TWO_TRACK_CANDIDATE_FUNCTIONAL_TRACK_COUNT,
            (unsigned)COMP_V40_TWO_TRACK_CANDIDATE_STORY_COUNT);
    fclose(file);
    return 0;
}

int main(int argc, char **argv)
{
    const comp_expression_rig_profile_t *profile = comp_v40_two_track_candidate_profile();
    const comp_v40_two_track_candidate_story_t *menu_story;
    comp_expression_rig_plan_t calm;
    comp_expression_rig_plan_t recording_calm;
    comp_expression_rig_plan_t recording_warm;
    comp_expression_rig_plan_t error_calm;
    comp_expression_rig_plan_t curious_question;
    comp_expression_rig_plan_t alert_exclamation;
    comp_expression_rig_plan_t menu_entry;
    unsigned int menu_duration = 0u;
    uint8_t story_index;

    if (require_true(profile != NULL && !comp_v40_two_track_candidate_runtime_activation_allowed() &&
                     profile->component_count == COMP_V40_TWO_TRACK_CANDIDATE_COMPONENT_COUNT &&
                     COMP_V40_TWO_TRACK_CANDIDATE_EXPRESSION_TRACK_COUNT == 6u &&
                     COMP_V40_TWO_TRACK_CANDIDATE_FUNCTIONAL_TRACK_COUNT == 4u &&
                     COMP_V40_TWO_TRACK_CANDIDATE_STORY_COUNT == 12u &&
                     !comp_expression_rig_build_plan(profile,
                         &(comp_expression_rig_state_t){.scene = COMP_EXPRESSION_RIG_SCENE_MENU,
                             .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
                             .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
                             .energy = COMP_EXPRESSION_RIG_ENERGY_LOW,
                             .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN},
                         &(comp_expression_rig_plan_t){0}),
                     "V40 profile must stay inactive and generic Menu synthesis must fail closed")) {
        return 1;
    }
    if (require_true(comp_v40_two_track_candidate_build_composed_frame(0u, 0u,
                     COMP_V40_TWO_TRACK_CANDIDATE_NO_FUNCTIONAL_TRACK, COMP_V40_TWO_TRACK_CANDIDATE_NO_FUNCTIONAL_TRACK,
                     NULL, &calm) &&
                     comp_v40_two_track_candidate_build_composed_frame(0u, 0u, 0u, 0u, NULL, &recording_calm) &&
                     comp_v40_two_track_candidate_build_composed_frame(1u, 0u, 0u, 0u, NULL, &recording_warm) &&
                     fixed_nose(&calm) && fixed_nose(&recording_calm) && fixed_nose(&recording_warm) &&
                     has_component(&recording_calm, 557u) && has_component(&recording_warm, 557u) &&
                     has_component(&recording_calm, 13u) && has_component(&recording_warm, 33u) &&
                     !has_component(&recording_calm, 33u) && !has_component(&recording_warm, 13u),
                     "the same recording decoration must compose with independently selected calm and warm face tracks")) {
        return 1;
    }
    if (require_true(comp_v40_two_track_candidate_build_composed_frame(0u, 0u, 3u, 0u, NULL, &error_calm) &&
                     has_component(&error_calm, 566u) && has_component(&error_calm, 13u) &&
                     !has_component(&error_calm, 554u) && !has_component(&error_calm, 555u) && !has_component(&error_calm, 556u),
                     "functional error decoration must not select rejected V38 brow or mouth components")) {
        return 1;
    }
    if (require_true(comp_v40_two_track_candidate_build_composed_frame(2u, 0u,
                     COMP_V40_TWO_TRACK_CANDIDATE_NO_FUNCTIONAL_TRACK, COMP_V40_TWO_TRACK_CANDIDATE_NO_FUNCTIONAL_TRACK,
                     NULL, &curious_question) &&
                     comp_v40_two_track_candidate_build_composed_frame(3u, 0u,
                     COMP_V40_TWO_TRACK_CANDIDATE_NO_FUNCTIONAL_TRACK, COMP_V40_TWO_TRACK_CANDIDATE_NO_FUNCTIONAL_TRACK,
                     NULL, &alert_exclamation) && has_component(&curious_question, 512u) &&
                     has_component(&alert_exclamation, 521u),
                     "question and exclamation remain expression-owned accents, not functional events")) {
        return 1;
    }
    menu_story = comp_v40_two_track_candidate_story(11u);
    if (require_true(menu_story != NULL && menu_story->uses_menu_entry_track &&
                     menu_story->withdraw_all_tracks_after_last_cue && menu_story->frame_count == 3u,
                     "Menu has only the dedicated finite entry cue")) {
        return 1;
    }
    for (story_index = 0u; story_index < menu_story->frame_count; ++story_index) {
        menu_duration += menu_story->frames[story_index].duration_ms;
        if (require_true(comp_v40_two_track_candidate_build_story_frame(menu_story, story_index, NULL, &menu_entry) &&
                         has_component(&menu_entry, (uint16_t)(545u + story_index)) && fixed_nose(&menu_entry),
                         "every Menu entry frame must be a legal touch cue composed from source components")) {
            return 1;
        }
    }
    if (require_true(menu_duration <= 500u,
                     "Menu entry must withdraw both tracks before Menu UI takes the screen")) {
        return 1;
    }
    for (story_index = 0u; story_index < COMP_V40_TWO_TRACK_CANDIDATE_STORY_COUNT; ++story_index) {
        const comp_v40_two_track_candidate_story_t *story = comp_v40_two_track_candidate_story(story_index);
        uint8_t frame_index;

        if (require_true(story != NULL && story->frames != NULL && story->frame_count > 0u,
                         "V40 story descriptor must remain registered")) {
            return 1;
        }
        for (frame_index = 0u; frame_index < story->frame_count; ++frame_index) {
            if (require_true(comp_v40_two_track_candidate_build_story_frame(story, frame_index, NULL, &calm) &&
                             calm.layer_count <= COMP_EXPRESSION_RIG_MAX_LAYERS && fixed_nose(&calm),
                             "every V40 story frame must be a legal two-track source plan")) {
                return 1;
            }
        }
    }
    if (write_report(argc == 2 ? argv[1] : NULL) != 0) {
        return 1;
    }
    puts("PASS: V40 retains the expression track and replaces only functional source decorations");
    return 0;
}
