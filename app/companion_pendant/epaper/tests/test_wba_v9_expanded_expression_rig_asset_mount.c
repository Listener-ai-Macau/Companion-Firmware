#include "asset_store.h"
#include "expression_choreographer.h"
#include "expression_rig.h"
#include "expression_rig_asset_pack.h"
#include "generated/expression_rig_v9_expanded_candidate_profile.h"
#include "screen_assets_stm32wba.h"

#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    uint8_t *data;
    size_t size;
    uint32_t read_count;
} file_nor_t;

typedef struct {
    const char *frame_name;
    comp_expression_rig_scene_t scene;
    comp_expression_rig_emotion_t emotion;
    comp_expression_rig_attention_t attention;
    comp_expression_rig_energy_t energy;
    uint8_t interaction_memory;
} expected_frame_t;

static const expected_frame_t k_expected_frames[] = {
    {"daily_attention_left", COMP_EXPRESSION_RIG_SCENE_DAILY, COMP_EXPRESSION_RIG_EMOTION_CALM, COMP_EXPRESSION_RIG_ATTENTION_LEFT, COMP_EXPRESSION_RIG_ENERGY_NORMAL, 0u},
    {"daily_attention_right", COMP_EXPRESSION_RIG_SCENE_DAILY, COMP_EXPRESSION_RIG_EMOTION_CALM, COMP_EXPRESSION_RIG_ATTENTION_RIGHT, COMP_EXPRESSION_RIG_ENERGY_NORMAL, 0u},
    {"daily_attention_up", COMP_EXPRESSION_RIG_SCENE_DAILY, COMP_EXPRESSION_RIG_EMOTION_CURIOUS, COMP_EXPRESSION_RIG_ATTENTION_UP, COMP_EXPRESSION_RIG_ENERGY_HIGH, 1u},
    {"daily_attention_down", COMP_EXPRESSION_RIG_SCENE_DAILY, COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, COMP_EXPRESSION_RIG_ATTENTION_DOWN, COMP_EXPRESSION_RIG_ENERGY_NORMAL, 2u},
    {"calm_content", COMP_EXPRESSION_RIG_SCENE_DAILY, COMP_EXPRESSION_RIG_EMOTION_CALM, COMP_EXPRESSION_RIG_ATTENTION_CENTER, COMP_EXPRESSION_RIG_ENERGY_NORMAL, 0u},
    {"curious_question", COMP_EXPRESSION_RIG_SCENE_TOUCH, COMP_EXPRESSION_RIG_EMOTION_CURIOUS, COMP_EXPRESSION_RIG_ATTENTION_CENTER, COMP_EXPRESSION_RIG_ENERGY_HIGH, 1u},
    {"alert_surprised", COMP_EXPRESSION_RIG_SCENE_TOUCH, COMP_EXPRESSION_RIG_EMOTION_ALERT, COMP_EXPRESSION_RIG_ATTENTION_CENTER, COMP_EXPRESSION_RIG_ENERGY_HIGH, 1u},
    {"joyful_spark", COMP_EXPRESSION_RIG_SCENE_DAILY, COMP_EXPRESSION_RIG_EMOTION_JOYFUL, COMP_EXPRESSION_RIG_ATTENTION_CENTER, COMP_EXPRESSION_RIG_ENERGY_HIGH, 2u},
    {"affectionate_warm", COMP_EXPRESSION_RIG_SCENE_SWIPE, COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, COMP_EXPRESSION_RIG_ATTENTION_CENTER, COMP_EXPRESSION_RIG_ENERGY_NORMAL, 2u},
    {"playful_bright", COMP_EXPRESSION_RIG_SCENE_SWIPE, COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, COMP_EXPRESSION_RIG_ATTENTION_CENTER, COMP_EXPRESSION_RIG_ENERGY_HIGH, 2u},
    {"anticipatory_notice", COMP_EXPRESSION_RIG_SCENE_DAILY, COMP_EXPRESSION_RIG_EMOTION_ANTICIPATORY, COMP_EXPRESSION_RIG_ATTENTION_UP, COMP_EXPRESSION_RIG_ENERGY_HIGH, 1u},
    {"puzzled_processing", COMP_EXPRESSION_RIG_SCENE_DAILY, COMP_EXPRESSION_RIG_EMOTION_PUZZLED, COMP_EXPRESSION_RIG_ATTENTION_CENTER, COMP_EXPRESSION_RIG_ENERGY_NORMAL, 1u},
    {"recording_focus", COMP_EXPRESSION_RIG_SCENE_RECORDING, COMP_EXPRESSION_RIG_EMOTION_FOCUSED, COMP_EXPRESSION_RIG_ATTENTION_CENTER, COMP_EXPRESSION_RIG_ENERGY_HIGH, 1u},
    {"listening_focus", COMP_EXPRESSION_RIG_SCENE_DAILY, COMP_EXPRESSION_RIG_EMOTION_LISTENING, COMP_EXPRESSION_RIG_ATTENTION_CENTER, COMP_EXPRESSION_RIG_ENERGY_NORMAL, 1u},
    {"menu_thinking", COMP_EXPRESSION_RIG_SCENE_MENU, COMP_EXPRESSION_RIG_EMOTION_THINKING, COMP_EXPRESSION_RIG_ATTENTION_UP, COMP_EXPRESSION_RIG_ENERGY_NORMAL, 1u},
};

static int require_true(bool condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

static bool file_nor_read(void *context,
                          uint32_t partition_offset,
                          uint8_t *destination,
                          size_t length)
{
    file_nor_t *nor = (file_nor_t *)context;

    if (nor == NULL || destination == NULL || partition_offset > nor->size ||
        length > nor->size - partition_offset) {
        return false;
    }
    memcpy(destination, &nor->data[partition_offset], length);
    nor->read_count++;
    return true;
}

static bool load_file(const char *path, file_nor_t *out_nor)
{
    FILE *file = NULL;
    long length;
    size_t bytes_read;

    if (path == NULL || out_nor == NULL || fopen_s(&file, path, "rb") != 0 || file == NULL) {
        return false;
    }
    if (fseek(file, 0L, SEEK_END) != 0 || (length = ftell(file)) <= 0L ||
        (unsigned long)length > UINT32_MAX || fseek(file, 0L, SEEK_SET) != 0) {
        fclose(file);
        return false;
    }
    out_nor->data = (uint8_t *)malloc((size_t)length);
    if (out_nor->data == NULL) {
        fclose(file);
        return false;
    }
    bytes_read = fread(out_nor->data, 1u, (size_t)length, file);
    fclose(file);
    if (bytes_read != (size_t)length) {
        free(out_nor->data);
        out_nor->data = NULL;
        return false;
    }
    out_nor->size = (size_t)length;
    return true;
}

static bool read_pbm_token(FILE *file, char *destination, size_t destination_size)
{
    int character;
    size_t length = 0u;

    if (file == NULL || destination == NULL || destination_size < 2u) {
        return false;
    }
    do {
        character = fgetc(file);
        if (character == '#') {
            do {
                character = fgetc(file);
            } while (character != '\n' && character != EOF);
        }
    } while (character != EOF && (character == ' ' || character == '\t' ||
                                   character == '\r' || character == '\n'));
    if (character == EOF) {
        return false;
    }
    do {
        if (length + 1u >= destination_size) {
            return false;
        }
        destination[length++] = (char)character;
        character = fgetc(file);
    } while (character != EOF && character != ' ' && character != '\t' &&
             character != '\r' && character != '\n');
    destination[length] = '\0';
    return true;
}

static bool load_p4(const char *path, uint8_t *destination, size_t destination_size)
{
    FILE *file = NULL;
    char token[16];
    unsigned long width;
    unsigned long height;
    size_t bytes;
    size_t index;

    if (path == NULL || destination == NULL || fopen_s(&file, path, "rb") != 0 || file == NULL ||
        !read_pbm_token(file, token, sizeof(token)) || strcmp(token, "P4") != 0 ||
        !read_pbm_token(file, token, sizeof(token))) {
        if (file != NULL) {
            fclose(file);
        }
        return false;
    }
    width = strtoul(token, NULL, 10);
    if (!read_pbm_token(file, token, sizeof(token))) {
        fclose(file);
        return false;
    }
    height = strtoul(token, NULL, 10);
    bytes = ((size_t)width + 7u) / 8u * (size_t)height;
    if (width != 200u || height != 200u || bytes != 5000u || destination_size < bytes ||
        fread(destination, 1u, bytes, file) != bytes) {
        fclose(file);
        return false;
    }
    fclose(file);
    for (index = 0u; index < bytes; ++index) {
        destination[index] = (uint8_t)~destination[index];
    }
    return true;
}

static bool build_expected_path(char *destination, size_t destination_size,
                                const char *directory, const char *frame_name)
{
    int written;

    if (destination == NULL || destination_size == 0u || directory == NULL || frame_name == NULL) {
        return false;
    }
    written = snprintf(destination, destination_size, "%s\\%s.pbm", directory, frame_name);
    return written > 0 && (size_t)written < destination_size;
}

static bool build_performance_path(char *destination, size_t destination_size,
                                   const char *directory, const char *state_name,
                                   uint8_t step_index,
                                   comp_expression_rig_score_phase_t phase)
{
    int written;

    if (destination == NULL || destination_size == 0u || directory == NULL || state_name == NULL) {
        return false;
    }
    written = snprintf(destination, destination_size, "%s\\%s-%02u-%s.pbm", directory, state_name,
                       (unsigned)step_index, comp_expression_rig_score_phase_name(phase));
    return written > 0 && (size_t)written < destination_size;
}

static bool build_presence_path(char *destination, size_t destination_size,
                                const char *directory, const char *state_name,
                                uint8_t step_index,
                                comp_expression_rig_score_phase_t phase)
{
    int written;

    if (destination == NULL || destination_size == 0u || directory == NULL || state_name == NULL) {
        return false;
    }
    written = snprintf(destination, destination_size, "%s\\%s-%02u-%s.pbm", directory, state_name,
                       (unsigned)step_index, comp_expression_rig_score_phase_name(phase));
    return written > 0 && (size_t)written < destination_size;
}

static const char *emotion_baseline_state_name(comp_expression_rig_emotion_t emotion)
{
    switch (emotion) {
    case COMP_EXPRESSION_RIG_EMOTION_CALM: return "calm_content";
    case COMP_EXPRESSION_RIG_EMOTION_CURIOUS: return "curious_question";
    case COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE: return "affectionate_warm";
    case COMP_EXPRESSION_RIG_EMOTION_FOCUSED: return "recording_focus";
    case COMP_EXPRESSION_RIG_EMOTION_ALERT: return "alert_surprised";
    case COMP_EXPRESSION_RIG_EMOTION_JOYFUL: return "joyful_spark";
    case COMP_EXPRESSION_RIG_EMOTION_PLAYFUL: return "playful_bright";
    case COMP_EXPRESSION_RIG_EMOTION_ANTICIPATORY: return "anticipatory_notice";
    case COMP_EXPRESSION_RIG_EMOTION_PUZZLED: return "puzzled_processing";
    case COMP_EXPRESSION_RIG_EMOTION_LISTENING: return "listening_focus";
    case COMP_EXPRESSION_RIG_EMOTION_THINKING: return "menu_thinking";
    case COMP_EXPRESSION_RIG_EMOTION_SLEEPY:
    default:
        return NULL;
    }
}

static const char *emotion_name(comp_expression_rig_emotion_t emotion)
{
    switch (emotion) {
    case COMP_EXPRESSION_RIG_EMOTION_CALM: return "calm";
    case COMP_EXPRESSION_RIG_EMOTION_CURIOUS: return "curious";
    case COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE: return "affectionate";
    case COMP_EXPRESSION_RIG_EMOTION_FOCUSED: return "focused";
    case COMP_EXPRESSION_RIG_EMOTION_SLEEPY: return "sleepy";
    case COMP_EXPRESSION_RIG_EMOTION_ALERT: return "alert";
    case COMP_EXPRESSION_RIG_EMOTION_JOYFUL: return "joyful";
    case COMP_EXPRESSION_RIG_EMOTION_PLAYFUL: return "playful";
    case COMP_EXPRESSION_RIG_EMOTION_ANTICIPATORY: return "anticipatory";
    case COMP_EXPRESSION_RIG_EMOTION_PUZZLED: return "puzzled";
    case COMP_EXPRESSION_RIG_EMOTION_LISTENING: return "listening";
    case COMP_EXPRESSION_RIG_EMOTION_THINKING: return "thinking";
    default: return NULL;
    }
}

static bool build_bridge_path(char *destination, size_t destination_size,
                              const char *directory, const char *from_state,
                              const char *to_state, uint8_t step_index,
                              comp_expression_rig_score_phase_t phase)
{
    int written;

    if (destination == NULL || destination_size == 0u || directory == NULL ||
        from_state == NULL || to_state == NULL) {
        return false;
    }
    written = snprintf(destination, destination_size, "%s\\%s_to_%s-%02u-%s.pbm", directory,
                       from_state, to_state, (unsigned)step_index,
                       comp_expression_rig_score_phase_name(phase));
    return written > 0 && (size_t)written < destination_size;
}

static bool plan_has_only_registered_components(const comp_expression_rig_plan_t *plan)
{
    uint8_t index;

    if (plan == NULL || plan->layer_count == 0u ||
        plan->layer_count > COMP_EXPRESSION_RIG_MAX_LAYERS) {
        return false;
    }
    for (index = 0u; index < plan->layer_count; ++index) {
        if (plan->layers[index].component_id == COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID ||
            plan->layers[index].component_id >
                COMP_V9_EXPANDED_EXPRESSION_RIG_CANDIDATE_COMPONENT_COUNT) {
            return false;
        }
    }
    return true;
}

static int compare_registered_frames(const comp_expression_rig_asset_pack_t *pack,
                                     const char *rendered_directory)
{
    static const comp_expression_rig_canvas_t canvas = {
        .width = 200u, .height = 200u, .stride_bytes = 25u,
    };
    uint8_t scratch[1024];
    uint8_t output[5000];
    uint8_t expected[5000];
    size_t index;

    for (index = 0u; index < sizeof(k_expected_frames) / sizeof(k_expected_frames[0]); ++index) {
        const expected_frame_t *expected_frame = &k_expected_frames[index];
        comp_expression_rig_state_t state = {
            .scene = expected_frame->scene,
            .emotion = expected_frame->emotion,
            .attention = expected_frame->attention,
            .energy = expected_frame->energy,
            .interaction_memory = expected_frame->interaction_memory,
            .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN,
        };
        comp_expression_rig_plan_t plan;
        comp_expression_rig_bounds_t bounds;
        char expected_path[512];

        if (!comp_expression_rig_build_plan(comp_v9_expanded_expression_rig_candidate_profile(),
                                            &state, &plan) ||
            !plan_has_only_registered_components(&plan) ||
            !build_expected_path(expected_path, sizeof(expected_path), rendered_directory,
                                 expected_frame->frame_name) ||
            !load_p4(expected_path, expected, sizeof(expected)) ||
            !comp_expression_rig_compose_1bpp(&canvas, &plan,
                                               comp_expression_rig_asset_pack_read_component,
                                               (void *)pack, scratch, sizeof(scratch), output,
                                               sizeof(output), &bounds) || !bounds.has_ink ||
            memcmp(output, expected, sizeof(output)) != 0) {
            fprintf(stderr, "FAIL: expanded Rig replay diverged for %s\n", expected_frame->frame_name);
            return 1;
        }
    }
    return 0;
}

static int compare_performance_frames(const comp_expression_rig_asset_pack_t *pack,
                                      const char *performance_directory)
{
    static const comp_expression_rig_canvas_t canvas = {
        .width = 200u, .height = 200u, .stride_bytes = 25u,
    };
    uint8_t scratch[1024];
    uint8_t output[5000];
    uint8_t expected[5000];
    size_t state_index;

    for (state_index = 0u; state_index < sizeof(k_expected_frames) / sizeof(k_expected_frames[0]); ++state_index) {
        const expected_frame_t *expected_frame = &k_expected_frames[state_index];
        const comp_expression_rig_registered_performance_score_t *score =
            comp_v9_expanded_expression_rig_candidate_performance_score(
                expected_frame->scene, expected_frame->emotion, expected_frame->attention);
        uint8_t step_index;

        if (score == NULL || score->steps == NULL || score->step_count != 7u) {
            fprintf(stderr, "FAIL: expanded performance score is missing for %s\n", expected_frame->frame_name);
            return 1;
        }
        for (step_index = 0u; step_index < score->step_count; ++step_index) {
            comp_expression_rig_plan_t plan;
            comp_expression_rig_bounds_t bounds;
            char expected_path[512];

            if (!build_performance_path(expected_path, sizeof(expected_path), performance_directory,
                                        expected_frame->frame_name, step_index, score->steps[step_index].phase) ||
                !load_p4(expected_path, expected, sizeof(expected)) ||
                !comp_expression_rig_build_registered_score_step(
                    comp_v9_expanded_expression_rig_candidate_profile(), score, step_index, NULL, &plan) ||
                !plan_has_only_registered_components(&plan) ||
                !comp_expression_rig_compose_1bpp(&canvas, &plan,
                                                   comp_expression_rig_asset_pack_read_component,
                                                   (void *)pack, scratch, sizeof(scratch), output,
                                                   sizeof(output), &bounds) || !bounds.has_ink ||
                memcmp(output, expected, sizeof(output)) != 0) {
                fprintf(stderr, "FAIL: expanded score replay diverged for %s step %u\n",
                        expected_frame->frame_name, (unsigned)step_index);
                return 1;
            }
        }
    }
    return 0;
}

static int compare_presence_frames(const comp_expression_rig_asset_pack_t *pack,
                                   const char *presence_directory)
{
    static const comp_expression_rig_canvas_t canvas = {
        .width = 200u, .height = 200u, .stride_bytes = 25u,
    };
    uint8_t scratch[1024];
    uint8_t output[5000];
    uint8_t expected[5000];
    size_t state_index;

    for (state_index = 0u; state_index < sizeof(k_expected_frames) / sizeof(k_expected_frames[0]); ++state_index) {
        const expected_frame_t *expected_frame = &k_expected_frames[state_index];
        const comp_expression_rig_registered_performance_score_t *score =
            comp_v9_expanded_expression_rig_candidate_presence_score(
                expected_frame->scene, expected_frame->emotion, expected_frame->attention);
        uint8_t step_index;

        if (score == NULL || score->steps == NULL ||
            score->step_count != COMP_V9_EXPANDED_EXPRESSION_RIG_CANDIDATE_PRESENCE_SAMPLE_COUNT) {
            fprintf(stderr, "FAIL: expanded presence score is missing for %s\n", expected_frame->frame_name);
            return 1;
        }
        for (step_index = 0u; step_index < score->step_count; ++step_index) {
            comp_expression_rig_plan_t plan;
            comp_expression_rig_bounds_t bounds;
            char expected_path[512];

            if (!build_presence_path(expected_path, sizeof(expected_path), presence_directory,
                                     expected_frame->frame_name, step_index, score->steps[step_index].phase) ||
                !load_p4(expected_path, expected, sizeof(expected)) ||
                !comp_expression_rig_build_registered_score_step(
                    comp_v9_expanded_expression_rig_candidate_profile(), score, step_index, NULL, &plan) ||
                !plan_has_only_registered_components(&plan) ||
                !comp_expression_rig_compose_1bpp(&canvas, &plan,
                                                   comp_expression_rig_asset_pack_read_component,
                                                   (void *)pack, scratch, sizeof(scratch), output,
                                                   sizeof(output), &bounds) || !bounds.has_ink ||
                memcmp(output, expected, sizeof(output)) != 0) {
                fprintf(stderr, "FAIL: expanded presence replay diverged for %s step %u\n",
                        expected_frame->frame_name, (unsigned)step_index);
                return 1;
            }
        }
    }
    return 0;
}

static int compare_emotion_bridge_frames(const comp_expression_rig_asset_pack_t *pack,
                                         const char *bridge_directory)
{
    static const comp_expression_rig_canvas_t canvas = {
        .width = 200u, .height = 200u, .stride_bytes = 25u,
    };
    uint8_t scratch[1024];
    uint8_t output[5000];
    uint8_t expected[5000];
    uint8_t from;
    uint8_t to;
    uint32_t bridge_count = 0u;

    for (from = 0u; from < COMP_EXPRESSION_RIG_EMOTION_COUNT; ++from) {
        const char *from_state = emotion_baseline_state_name((comp_expression_rig_emotion_t)from);
        const char *from_emotion = emotion_name((comp_expression_rig_emotion_t)from);

        if (from_state == NULL || from_emotion == NULL) {
            continue;
        }
        for (to = 0u; to < COMP_EXPRESSION_RIG_EMOTION_COUNT; ++to) {
            const char *to_state = emotion_baseline_state_name((comp_expression_rig_emotion_t)to);
            const char *to_emotion = emotion_name((comp_expression_rig_emotion_t)to);
            const comp_expression_rig_registered_performance_score_t *score;
            uint8_t step_index;

            if (to_state == NULL || to_emotion == NULL) {
                continue;
            }
            score = comp_v9_expanded_expression_rig_candidate_emotion_bridge_score(
                (comp_expression_rig_emotion_t)from, (comp_expression_rig_emotion_t)to);
            if (score == NULL) {
                continue;
            }
            if (!comp_expression_rig_emotion_transition_allowed(
                    (comp_expression_rig_emotion_t)from, (comp_expression_rig_emotion_t)to) ||
                score->steps == NULL ||
                score->step_count != COMP_V9_EXPANDED_EXPRESSION_RIG_CANDIDATE_EMOTION_BRIDGE_SAMPLE_COUNT) {
                fprintf(stderr, "FAIL: expanded emotion bridge contract is invalid for %s -> %s\n",
                        from_state, to_state);
                return 1;
            }
            ++bridge_count;
            for (step_index = 0u; step_index < score->step_count; ++step_index) {
                comp_expression_rig_plan_t plan = {0};
                comp_expression_rig_bounds_t bounds;
                char expected_path[512];

                if (!build_bridge_path(expected_path, sizeof(expected_path), bridge_directory,
                                       from_emotion, to_emotion, step_index, score->steps[step_index].phase) ||
                    !load_p4(expected_path, expected, sizeof(expected)) ||
                    !comp_expression_rig_build_registered_score_step(
                        comp_v9_expanded_expression_rig_candidate_profile(), score, step_index,
                        NULL, &plan) || !plan_has_only_registered_components(&plan) ||
                    !comp_expression_rig_compose_1bpp(&canvas, &plan,
                                                       comp_expression_rig_asset_pack_read_component,
                                                       (void *)pack, scratch, sizeof(scratch), output,
                                                       sizeof(output), &bounds) || !bounds.has_ink ||
                    memcmp(output, expected, sizeof(output)) != 0) {
                    fprintf(stderr, "FAIL: expanded emotion bridge replay diverged for %s -> %s step %u\n",
                            from_state, to_state, (unsigned)step_index);
                    return 1;
                }
            }
        }
    }
    return require_true(bridge_count == COMP_V9_EXPANDED_EXPRESSION_RIG_CANDIDATE_EMOTION_BRIDGE_COUNT,
                        "all directed emotion bridges must replay from external NOR");
}

static int test_event_choreography(const comp_expression_rig_profile_t *profile)
{
    comp_expression_rig_choreography_input_t input = {
        .event = COMP_EXPRESSION_RIG_EVENT_DAILY_AUTO,
        .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
        .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL,
        .interaction_memory = 0u,
        .seed = 0x51A7E123u,
        .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN,
    };
    comp_expression_rig_plan_t plan;
    comp_expression_rig_plan_t normal;
    comp_expression_rig_plan_t animated;
    comp_expression_rig_state_t state;
    size_t index;
    bool found_offset_change = false;

    input.has_requested_emotion = true;
    input.requested_emotion = COMP_EXPRESSION_RIG_EMOTION_JOYFUL;
    if (require_true(comp_expression_rig_choreograph_plan(profile, &input, &plan) &&
                         plan.effective_state.scene == COMP_EXPRESSION_RIG_SCENE_DAILY &&
                         plan.effective_state.emotion == COMP_EXPRESSION_RIG_EMOTION_JOYFUL &&
                         plan_has_only_registered_components(&plan),
                     "requested daily joyful emotion resolves to an approved registered pose")) {
        return 1;
    }

    input.event = COMP_EXPRESSION_RIG_EVENT_TOUCH_TAP;
    input.requested_emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT;
    if (require_true(comp_expression_rig_choreograph_plan(profile, &input, &plan) &&
                         plan.effective_state.scene == COMP_EXPRESSION_RIG_SCENE_TOUCH &&
                         plan.effective_state.emotion == COMP_EXPRESSION_RIG_EMOTION_ALERT,
                     "requested touch alert emotion resolves to its source-component pose")) {
        return 1;
    }

    input.event = COMP_EXPRESSION_RIG_EVENT_MENU_HOLD;
    input.has_requested_emotion = false;
    for (index = 0u; index < COMP_EXPRESSION_RIG_PHASE_COUNT; ++index) {
        input.phase = (comp_expression_rig_phase_t)index;
        if (require_true(!comp_expression_rig_choreograph_plan(profile, &input, &plan),
                         "menu remains fail-closed until its V18 special-expression pose is accepted and bound")) {
            return 1;
        }
    }
    input.event = COMP_EXPRESSION_RIG_EVENT_RECORDING_ACTIVE;
    for (index = 0u; index < COMP_EXPRESSION_RIG_PHASE_COUNT; ++index) {
        input.phase = (comp_expression_rig_phase_t)index;
        if (require_true(!comp_expression_rig_choreograph_plan(profile, &input, &plan),
                         "recording remains fail-closed until its V19 special-expression pose is accepted and bound")) {
            return 1;
        }
    }
    input.event = COMP_EXPRESSION_RIG_EVENT_UPGRADE_ACTIVE;
    for (index = 0u; index < COMP_EXPRESSION_RIG_PHASE_COUNT; ++index) {
        input.phase = (comp_expression_rig_phase_t)index;
        if (require_true(!comp_expression_rig_choreograph_plan(profile, &input, &plan),
                         "upgrade remains fail-closed until its V20 special-expression pose is accepted and bound")) {
            return 1;
        }
    }

    input.event = COMP_EXPRESSION_RIG_EVENT_SLEEP;
    for (index = 0u; index < COMP_EXPRESSION_RIG_PHASE_COUNT; ++index) {
        input.phase = (comp_expression_rig_phase_t)index;
        if (require_true(!comp_expression_rig_choreograph_plan(profile, &input, &plan),
                         "owner-rejected sleep remains fail-closed without a V12 source pose")) {
            return 1;
        }
    }
    if (require_true(comp_v9_expanded_expression_rig_candidate_performance_score(
                         COMP_EXPRESSION_RIG_SCENE_SLEEP, COMP_EXPRESSION_RIG_EMOTION_SLEEPY,
                         COMP_EXPRESSION_RIG_ATTENTION_CENTER) == NULL,
                     "owner-rejected sleep has no registered performance score")) {
        return 1;
    }

    input.event = COMP_EXPRESSION_RIG_EVENT_CHARGING;
    for (index = 0u; index < COMP_EXPRESSION_RIG_PHASE_COUNT; ++index) {
        input.phase = (comp_expression_rig_phase_t)index;
        if (require_true(!comp_expression_rig_choreograph_plan(profile, &input, &plan),
                         "charging remains fail-closed without an approved source pose")) {
            return 1;
        }
    }
    input.event = COMP_EXPRESSION_RIG_EVENT_ERROR;
    for (index = 0u; index < COMP_EXPRESSION_RIG_PHASE_COUNT; ++index) {
        input.phase = (comp_expression_rig_phase_t)index;
        if (require_true(!comp_expression_rig_choreograph_plan(profile, &input, &plan),
                         "error remains fail-closed without an approved source pose")) {
            return 1;
        }
    }

    state = (comp_expression_rig_state_t){
        .scene = COMP_EXPRESSION_RIG_SCENE_SWIPE,
        .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL,
        .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
        .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL,
        .interaction_memory = 0u,
        .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN,
    };
    if (!comp_expression_rig_build_plan(profile, &state, &normal)) {
        return require_true(false, "normal playful Rig plan builds");
    }
    state.energy = COMP_EXPRESSION_RIG_ENERGY_HIGH;
    state.interaction_memory = 2u;
    if (!comp_expression_rig_build_plan(profile, &state, &animated) ||
        normal.layer_count != animated.layer_count) {
        return require_true(false, "energy and memory preserve a legal playful component set");
    }
    for (index = 0u; index < normal.layer_count; ++index) {
        if (normal.layers[index].component_id != animated.layers[index].component_id) {
            return require_true(false, "dynamic context never swaps a full-face or source component set");
        }
        if (normal.layers[index].offset_x != animated.layers[index].offset_x ||
            normal.layers[index].offset_y != animated.layers[index].offset_y) {
            found_offset_change = true;
        }
    }
    return require_true(found_offset_change,
                        "energy and interaction memory move only registered source components");
}

static int test_score_dynamic_context(const comp_expression_rig_profile_t *profile)
{
    const comp_expression_rig_registered_performance_score_t *score =
        comp_v9_expanded_expression_rig_candidate_performance_score(
            COMP_EXPRESSION_RIG_SCENE_SWIPE, COMP_EXPRESSION_RIG_EMOTION_PLAYFUL,
            COMP_EXPRESSION_RIG_ATTENTION_CENTER);
    comp_expression_rig_state_t low_context = {
        .scene = COMP_EXPRESSION_RIG_SCENE_SWIPE,
        .emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL,
        .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
        .energy = COMP_EXPRESSION_RIG_ENERGY_LOW,
        .interaction_memory = 0u,
        .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN,
    };
    comp_expression_rig_state_t high_context = low_context;
    comp_expression_rig_plan_t low_plan = {0};
    comp_expression_rig_plan_t high_plan = {0};
    uint8_t index;
    bool found_offset_change = false;

    high_context.energy = COMP_EXPRESSION_RIG_ENERGY_HIGH;
    high_context.interaction_memory = 2u;
    if (require_true(score != NULL && score->step_count == 7u &&
                         comp_expression_rig_build_registered_score_step(
                             profile, score, 4u, &low_context, &low_plan) &&
                         comp_expression_rig_build_registered_score_step(
                             profile, score, 4u, &high_context, &high_plan) &&
                         low_plan.layer_count == high_plan.layer_count,
                     "expanded score accepts legal energy and memory context")) {
        return 1;
    }
    for (index = 0u; index < low_plan.layer_count; ++index) {
        if (low_plan.layers[index].component_id != high_plan.layers[index].component_id) {
            return require_true(false,
                                "score context never swaps a registered source-component set");
        }
        if (low_plan.layers[index].offset_x != high_plan.layers[index].offset_x ||
            low_plan.layers[index].offset_y != high_plan.layers[index].offset_y) {
            found_offset_change = true;
        }
    }
    return require_true(found_offset_change,
                        "score context changes only legal source-component offsets");
}

static int exercise_target(file_nor_t *nor,
                           companion_epaper_panel_stm32wba_target_t target,
                           const char *rendered_directory,
                           const char *performance_directory,
                           const char *presence_directory,
                           const char *bridge_directory)
{
    static const comp_expression_rig_canvas_t canvas = {
        .width = 200u, .height = 200u, .stride_bytes = 25u,
    };
    companion_screen_assets_stm32wba_t adapter;
    companion_screen_assets_stm32wba_config_t config;
    comp_asset_store_t store;
    comp_expression_rig_asset_pack_t pack;
    uint8_t scratch[1024];

    companion_screen_assets_stm32wba_init(&adapter);
    config = (companion_screen_assets_stm32wba_config_t){
        .target = target,
        .partition_size = (uint32_t)nor->size,
        .read = file_nor_read,
        .context = nor,
    };
    if (require_true(companion_screen_assets_stm32wba_bind(&adapter, &store, &config),
                     "WBA adapter must bind the expanded Rig through external NOR") ||
        require_true(store.storage_class == COMP_ASSET_STORAGE_EXTERNAL_NOR && store.mapped_data == NULL,
                     "expanded Rig store must remain callback-only external NOR") ||
        require_true(comp_expression_rig_asset_pack_mount(&pack, &store, &canvas) ==
                         COMP_EXPRESSION_RIG_ASSET_MOUNT_OK,
                     "expanded source-mask component pack must mount") ||
        require_true(pack.component_count == COMP_V9_EXPANDED_EXPRESSION_RIG_CANDIDATE_COMPONENT_COUNT,
                     "mounted expanded Rig must expose all registered source components") ||
        require_true(comp_expression_rig_asset_pack_verify_payload(&pack, scratch, sizeof(scratch)),
                     "expanded Rig payload CRC must verify") ||
        require_true(!comp_v9_expanded_expression_rig_candidate_runtime_activation_allowed(),
                     "expanded candidate remains runtime-inactive")) {
        return 1;
    }
    if (compare_registered_frames(&pack, rendered_directory) != 0 ||
        compare_performance_frames(&pack, performance_directory) != 0 ||
        compare_presence_frames(&pack, presence_directory) != 0 ||
        compare_emotion_bridge_frames(&pack, bridge_directory) != 0 ||
        test_event_choreography(comp_v9_expanded_expression_rig_candidate_profile()) != 0 ||
        test_score_dynamic_context(comp_v9_expanded_expression_rig_candidate_profile()) != 0) {
        return 1;
    }
    return require_true(nor->read_count > 0u,
                        "WBA callback must service expanded Rig component reads");
}

int main(int argc, char **argv)
{
    file_nor_t nor = {0};
    int result;

    if (argc != 6 || !load_file(argv[1], &nor)) {
        fprintf(stderr, "FAIL: usage: test_wba_v9_expanded_expression_rig_asset_mount <pack.crig> <rendered-dir> <performance-dir> <presence-dir> <bridge-dir>\n");
        return 1;
    }
    result = exercise_target(&nor, COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55, argv[2], argv[3], argv[4], argv[5]);
    if (result == 0) {
        result = exercise_target(&nor, COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA65, argv[2], argv[3], argv[4], argv[5]);
    }
    free(nor.data);
    if (result != 0) {
        return result;
    }
    puts("PASS: WBA55/WBA65 reconstruct registered expanded V9 source-mask audit states, selected-state presence samples and directed emotion bridges from external NOR; unbound special events remain fail-closed");
    return 0;
}
