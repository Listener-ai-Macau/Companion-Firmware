#include "expression_rig.h"
#include "generated/expression_rig_v45_complete_eye_candidate_profile.h"

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

static int has_offset(const comp_expression_rig_plan_t *plan, uint16_t component_id,
                      int8_t offset_x, int8_t offset_y)
{
    uint8_t index;

    for (index = 0u; plan != NULL && index < plan->layer_count; ++index) {
        if (plan->layers[index].component_id == component_id &&
            plan->layers[index].offset_x == offset_x &&
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

static const comp_v45_two_track_candidate_story_t *find_story(const char *name)
{
    uint8_t index;

    for (index = 0u; index < COMP_V45_TWO_TRACK_CANDIDATE_STORY_COUNT; ++index) {
        const comp_v45_two_track_candidate_story_t *story =
            comp_v45_two_track_candidate_story(index);

        if (story != NULL && story->name != NULL && strcmp(story->name, name) == 0) {
            return story;
        }
    }
    return NULL;
}

static int require_gaze(uint8_t expression_track_index,
                        comp_expression_rig_attention_t attention,
                        int8_t primary_x, int8_t primary_y,
                        int8_t sparkle_x, int8_t sparkle_y)
{
    comp_expression_rig_plan_t plan;

    if (!comp_v45_two_track_candidate_build_composed_frame(
            expression_track_index, 2u,
            COMP_V45_TWO_TRACK_CANDIDATE_NO_FUNCTIONAL_TRACK,
            COMP_V45_TWO_TRACK_CANDIDATE_NO_FUNCTIONAL_TRACK, NULL, &plan)) {
        return 0;
    }
    return plan.effective_state.attention == attention && fixed_nose(&plan) &&
           has_offset(&plan, 1u, primary_x, primary_y) &&
           has_offset(&plan, 5u, primary_x, primary_y) &&
           has_offset(&plan, 3u, sparkle_x, sparkle_y) &&
           has_offset(&plan, 7u, sparkle_x, sparkle_y);
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
            "  \"schema\": \"companion.v45_complete_eye_wb55_profile_host.v1\",\n"
            "  \"status\": \"PASS_V45_COMPLETE_EYE_WB55_PROFILE_RUNTIME_INACTIVE\",\n"
            "  \"component_count\": %u,\n"
            "  \"expression_track_count\": %u,\n"
            "  \"functional_track_count\": %u,\n"
            "  \"story_count\": %u,\n"
            "  \"preview_frame_count\": 93,\n"
            "  \"five_gaze_states\": [\"center\", \"left\", \"right\", \"up\", \"down\"],\n"
            "  \"recording_input_clear_of_face\": true,\n"
            "  \"wireless_dock_charging\": true,\n"
            "  \"sleep_zzz_only\": true,\n"
            "  \"fail_closed\": {\"invalid_functional_track\": true, \"invalid_functional_step\": true, \"missing_source_pose\": true, \"generic_menu_synthesis\": true},\n"
            "  \"runtime_resource_activated\": false,\n"
            "  \"non_claims\": [\"no_firmware_flash\", \"no_panel_or_driver_change\", \"no_human_acceptance\"]\n"
            "}\n",
            (unsigned)COMP_V45_TWO_TRACK_CANDIDATE_COMPONENT_COUNT,
            (unsigned)COMP_V45_TWO_TRACK_CANDIDATE_EXPRESSION_TRACK_COUNT,
            (unsigned)COMP_V45_TWO_TRACK_CANDIDATE_FUNCTIONAL_TRACK_COUNT,
            (unsigned)COMP_V45_TWO_TRACK_CANDIDATE_STORY_COUNT);
    fclose(file);
    return 0;
}

int main(int argc, char **argv)
{
    const comp_expression_rig_profile_t *profile =
        comp_v45_two_track_candidate_profile();
    const comp_v45_two_track_candidate_story_t *recording;
    const comp_v45_two_track_candidate_story_t *charging;
    const comp_v45_two_track_candidate_story_t *upgrade;
    const comp_v45_two_track_candidate_story_t *error;
    const comp_v45_two_track_candidate_story_t *sleep;
    const comp_v45_two_track_candidate_story_t *menu;
    const comp_v45_two_track_candidate_story_t *calm;
    const char *new_emotions[] = {
        "delighted_presence", "bashful_presence", "thoughtful_presence", "focused_presence"
    };
    const uint16_t new_emotion_component_ids[] = {575u, 580u, 585u, 589u};
    comp_expression_rig_plan_t plan;
    comp_expression_rig_registered_pose_t missing_source_pose = {
        .scene = COMP_EXPRESSION_RIG_SCENE_ERROR,
        .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
        .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
        .layer_count = 1u,
        .layers = {{COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, 0, 0, 0}},
    };
    uint8_t story_index;
    uint8_t index;
    unsigned int menu_duration = 0u;

    if (require_true(profile != NULL &&
                     !comp_v45_two_track_candidate_runtime_activation_allowed() &&
                     profile->component_count ==
                         COMP_V45_TWO_TRACK_CANDIDATE_COMPONENT_COUNT &&
                         COMP_V45_TWO_TRACK_CANDIDATE_COMPONENT_COUNT == 97u &&
                         COMP_V45_TWO_TRACK_CANDIDATE_EXPRESSION_TRACK_COUNT == 15u &&
                         COMP_V45_TWO_TRACK_CANDIDATE_FUNCTIONAL_TRACK_COUNT == 4u &&
                         COMP_V45_TWO_TRACK_CANDIDATE_STORY_COUNT == 21u &&
                     !comp_expression_rig_build_plan(
                         profile,
                         &(comp_expression_rig_state_t){
                             .scene = COMP_EXPRESSION_RIG_SCENE_MENU,
                             .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
                             .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
                             .energy = COMP_EXPRESSION_RIG_ENERGY_LOW,
                             .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN},
                         &(comp_expression_rig_plan_t){0}) &&
                     !comp_expression_rig_build_registered_pose_plan(
                         profile,
                         &(comp_expression_rig_state_t){
                             .scene = COMP_EXPRESSION_RIG_SCENE_ERROR,
                             .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
                             .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
                             .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL,
                             .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN},
                         &missing_source_pose, &(comp_expression_rig_plan_t){0}),
                     "V42 must remain inactive and generic Menu synthesis must fail closed")) {
        return 1;
    }
    if (require_true(!comp_v45_two_track_candidate_build_composed_frame(
                         0u, 0u, 4u, 0u, NULL, &(comp_expression_rig_plan_t){0}) &&
                         !comp_v45_two_track_candidate_build_composed_frame(
                         0u, 0u, 0u, 5u, NULL, &(comp_expression_rig_plan_t){0}),
                     "V45 must fail closed for an unknown functional track or step")) {
        return 1;
    }
    if (require_true(require_gaze(10u, COMP_EXPRESSION_RIG_ATTENTION_CENTER, 1, 0, 1, 0) &&
                     require_gaze(11u, COMP_EXPRESSION_RIG_ATTENTION_LEFT, -2, 2, -5, 3) &&
                     require_gaze(12u, COMP_EXPRESSION_RIG_ATTENTION_RIGHT, 5, 2, 5, 3) &&
                     require_gaze(13u, COMP_EXPRESSION_RIG_ATTENTION_UP, 1, -3, 1, -5) &&
                     require_gaze(14u, COMP_EXPRESSION_RIG_ATTENTION_DOWN, 1, 4, 1, 5),
                     "V42 must retain all five deterministic V9 gaze endpoints")) {
        return 1;
    }
    recording = find_story("recording_with_calm");
    charging = find_story("charging_with_calm");
    upgrade = find_story("upgrade_with_playful");
    error = find_story("error_with_calm");
    sleep = find_story("sleepy_presence");
    menu = find_story("menu_entry_notice");
    calm = find_story("calm_presence");
    if (require_true(recording != NULL && charging != NULL && upgrade != NULL && error != NULL &&
                     sleep != NULL && menu != NULL && calm != NULL,
                     "V42 required stories must remain registered")) {
        return 1;
    }
    if (require_true(calm->frame_count == 5u &&
                     calm->frames[0].duration_ms == 220u &&
                     calm->frames[1].duration_ms == 140u &&
                     calm->frames[2].duration_ms == 120u &&
                     calm->frames[3].duration_ms == 150u &&
                     calm->frames[4].duration_ms == 6800u,
                     "V45 blink timing must be open, 140ms closing, 120ms closed, 150ms opening, 6800ms settle")) {
        return 1;
    }
    if (require_true(comp_v45_two_track_candidate_build_story_frame(calm, 1u, NULL, &plan) &&
                     has_component(&plan, 599u) && has_component(&plan, 600u) &&
                     !has_component(&plan, 597u) && !has_component(&plan, 598u) && fixed_nose(&plan) &&
                     comp_v45_two_track_candidate_build_story_frame(calm, 2u, NULL, &plan) &&
                     has_component(&plan, 601u) && has_component(&plan, 602u) &&
                     !has_component(&plan, 599u) && !has_component(&plan, 600u) && fixed_nose(&plan) &&
                     comp_v45_two_track_candidate_build_story_frame(calm, 3u, NULL, &plan) &&
                     has_component(&plan, 603u) && has_component(&plan, 604u) &&
                     !has_component(&plan, 601u) && !has_component(&plan, 602u) && fixed_nose(&plan) &&
                     comp_v45_two_track_candidate_build_story_frame(calm, 4u, NULL, &plan) &&
                     !has_component(&plan, 599u) && !has_component(&plan, 600u) &&
                     !has_component(&plan, 601u) && !has_component(&plan, 602u) &&
                     !has_component(&plan, 603u) && !has_component(&plan, 604u) && fixed_nose(&plan),
                     "V45 calm blink must use complete source eye groups and return to the V9 open baseline")) {
        return 1;
    }
    {
        static const uint16_t recording_wave_ids[] = {606u, 607u, 608u, 607u, 606u};
        for (index = 0u; index < 5u; ++index) {
         if (require_true(comp_v45_two_track_candidate_build_story_frame(recording, index, NULL, &plan) &&
                         has_component(&plan, 605u) && has_component(&plan, recording_wave_ids[index]) &&
                         !has_component(&plan, 569u) && !has_component(&plan, 570u) &&
                         !has_component(&plan, 571u) && fixed_nose(&plan),
                         "V45 recording must keep the microphone fixed and animate only the registered input waveform")) {
            return 1;
         }
        }
    }
    for (index = 0u; index < 3u; ++index) {
         if (require_true(comp_v45_two_track_candidate_build_story_frame(charging, index, NULL, &plan) &&
                         has_component(&plan, (uint16_t)(572u + index)) &&
                         !has_component(&plan, (uint16_t)(560u + index)) && fixed_nose(&plan),
                         "V42 charging must use only the new wireless dock ornament")) {
            return 1;
        }
    }
    {
        static const uint16_t upgrade_ids[] = {563u, 564u, 565u, 564u, 565u};
        static const uint16_t error_ids[] = {566u, 567u, 568u, 567u, 568u};
        for (index = 0u; index < 5u; ++index) {
            if (require_true(comp_v45_two_track_candidate_build_story_frame(upgrade, index, NULL, &plan) &&
                             has_component(&plan, upgrade_ids[index]) && fixed_nose(&plan),
                             "V45 upgrade must use only its registered progress source sequence")) {
                return 1;
            }
            if (require_true(comp_v45_two_track_candidate_build_story_frame(error, index, NULL, &plan) &&
                             has_component(&plan, error_ids[index]) && fixed_nose(&plan),
                             "V45 error must use only its registered caution source sequence")) {
                return 1;
            }
        }
    }
    for (index = 0u; index < sleep->frame_count; ++index) {
         if (require_true(comp_v45_two_track_candidate_build_story_frame(sleep, index, NULL, &plan) &&
                         !has_component(&plan, 531u) && !has_component(&plan, 532u) &&
                         !has_component(&plan, 544u) && fixed_nose(&plan),
                         "V42 sleep must exclude every cloud and moon component")) {
            return 1;
        }
    }
     if (require_true(comp_v45_two_track_candidate_build_story_frame(sleep, 4u, NULL, &plan) &&
                     has_component(&plan, 594u) && has_component(&plan, 595u) &&
                     has_component(&plan, 596u),
                     "V42 sleep hold must contain all three registered Z components")) {
        return 1;
    }
    for (index = 0u; index < (uint8_t)(sizeof(new_emotions) / sizeof(new_emotions[0])); ++index) {
        const comp_v45_two_track_candidate_story_t *story = find_story(new_emotions[index]);
        uint16_t source_component_id = new_emotion_component_ids[index];

        if (require_true(story != NULL &&
                          comp_v45_two_track_candidate_build_story_frame(story, 2u, NULL, &plan) &&
                         has_component(&plan, source_component_id) && fixed_nose(&plan),
                         "every V42 added emotion must compose its own source-derived components")) {
            return 1;
        }
    }
    if (require_true(menu->uses_menu_entry_track && menu->withdraw_all_tracks_after_last_cue &&
                     menu->frame_count == 3u, "Menu must remain only a finite entry cue")) {
        return 1;
    }
    for (index = 0u; index < menu->frame_count; ++index) {
        if (require_true(comp_v45_two_track_candidate_build_story_frame(menu, index, NULL, &plan) &&
                         has_component(&plan, (uint16_t)(545u + index)) && fixed_nose(&plan),
                         "Menu must use its registered finite cue components")) {
            return 1;
        }
    }
    for (index = 0u; index < menu->frame_count; ++index) {
        menu_duration += menu->frames[index].duration_ms;
    }
    if (require_true(menu_duration <= 500u,
                     "Menu must withdraw both tracks before Menu UI ownership")) {
        return 1;
    }
    for (story_index = 0u; story_index < COMP_V45_TWO_TRACK_CANDIDATE_STORY_COUNT; ++story_index) {
        const comp_v45_two_track_candidate_story_t *story =
            comp_v45_two_track_candidate_story(story_index);

        if (require_true(story != NULL && story->frames != NULL && story->frame_count > 0u,
                         "V42 story descriptor must remain registered")) {
            return 1;
        }
        for (index = 0u; index < story->frame_count; ++index) {
            if (require_true(comp_v45_two_track_candidate_build_story_frame(
                                 story, index, NULL, &plan) &&
                             plan.layer_count <= COMP_EXPRESSION_RIG_MAX_LAYERS && fixed_nose(&plan),
                             "every V42 frame must remain a legal source-only two-track plan")) {
                return 1;
            }
        }
    }
    if (write_report(argc == 2 ? argv[1] : NULL) != 0) {
        return 1;
    }
    puts("PASS: V45 retains deterministic gaze, complete-eye blink, inward input, dock, and ZZZ sleep");
    return 0;
}
