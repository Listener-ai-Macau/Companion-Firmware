#include "asset_store.h"
#include "expression_rig.h"
#include "expression_rig_asset_pack.h"
#include "expression_rig_performance_score.h"
#include "screen_assets_stm32wba.h"

#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef V36_PROFILE_HEADER
#define V36_PROFILE_HEADER "generated/expression_rig_v36_daily_down_candidate_profile.h"
#endif
#ifndef V36_PROFILE_FRAME_TYPE
#define V36_PROFILE_FRAME_TYPE comp_v36_daily_down_rig_frame_t
#endif
#ifndef V36_PROFILE_COMPONENT_COUNT
#define V36_PROFILE_COMPONENT_COUNT COMP_V36_DAILY_DOWN_RIG_CANDIDATE_COMPONENT_COUNT
#endif
#ifndef V36_PROFILE_FRAME_COUNT
#define V36_PROFILE_FRAME_COUNT COMP_V36_DAILY_DOWN_RIG_CANDIDATE_FRAME_COUNT
#endif
#ifndef V36_PROFILE_GET_PROFILE
#define V36_PROFILE_GET_PROFILE comp_v36_daily_down_rig_candidate_profile
#endif
#ifndef V36_PROFILE_RUNTIME_ACTIVATION_ALLOWED
#define V36_PROFILE_RUNTIME_ACTIVATION_ALLOWED comp_v36_daily_down_rig_candidate_runtime_activation_allowed
#endif
#ifndef V36_PROFILE_GET_SCORE
#define V36_PROFILE_GET_SCORE comp_v36_daily_down_rig_candidate_score
#endif
#ifndef V36_PROFILE_GET_FRAMES
#define V36_PROFILE_GET_FRAMES comp_v36_daily_down_rig_candidate_frames
#endif

#if defined(V36_ATTEMPT_10)
#undef V36_PROFILE_HEADER
#undef V36_PROFILE_FRAME_TYPE
#undef V36_PROFILE_COMPONENT_COUNT
#undef V36_PROFILE_FRAME_COUNT
#undef V36_PROFILE_GET_PROFILE
#undef V36_PROFILE_RUNTIME_ACTIVATION_ALLOWED
#undef V36_PROFILE_GET_SCORE
#undef V36_PROFILE_GET_FRAMES
#define V36_PROFILE_HEADER "generated/expression_rig_v36_daily_down_attempt_10_candidate_profile.h"
#define V36_PROFILE_FRAME_TYPE comp_v36_daily_down_attempt_10_rig_frame_t
#define V36_PROFILE_COMPONENT_COUNT COMP_V36_DAILY_DOWN_ATTEMPT_10_RIG_CANDIDATE_COMPONENT_COUNT
#define V36_PROFILE_FRAME_COUNT COMP_V36_DAILY_DOWN_ATTEMPT_10_RIG_CANDIDATE_FRAME_COUNT
#define V36_PROFILE_GET_PROFILE comp_v36_daily_down_attempt_10_rig_candidate_profile
#define V36_PROFILE_RUNTIME_ACTIVATION_ALLOWED comp_v36_daily_down_attempt_10_rig_candidate_runtime_activation_allowed
#define V36_PROFILE_GET_SCORE comp_v36_daily_down_attempt_10_rig_candidate_score
#define V36_PROFILE_GET_FRAMES comp_v36_daily_down_attempt_10_rig_candidate_frames
#elif defined(V36_ATTEMPT_11)
#undef V36_PROFILE_HEADER
#undef V36_PROFILE_FRAME_TYPE
#undef V36_PROFILE_COMPONENT_COUNT
#undef V36_PROFILE_FRAME_COUNT
#undef V36_PROFILE_GET_PROFILE
#undef V36_PROFILE_RUNTIME_ACTIVATION_ALLOWED
#undef V36_PROFILE_GET_SCORE
#undef V36_PROFILE_GET_FRAMES
#define V36_PROFILE_HEADER "generated/expression_rig_v36_daily_down_attempt_11_candidate_profile.h"
#define V36_PROFILE_FRAME_TYPE comp_v36_daily_down_attempt_11_rig_frame_t
#define V36_PROFILE_COMPONENT_COUNT COMP_V36_DAILY_DOWN_ATTEMPT_11_RIG_CANDIDATE_COMPONENT_COUNT
#define V36_PROFILE_FRAME_COUNT COMP_V36_DAILY_DOWN_ATTEMPT_11_RIG_CANDIDATE_FRAME_COUNT
#define V36_PROFILE_GET_PROFILE comp_v36_daily_down_attempt_11_rig_candidate_profile
#define V36_PROFILE_RUNTIME_ACTIVATION_ALLOWED comp_v36_daily_down_attempt_11_rig_candidate_runtime_activation_allowed
#define V36_PROFILE_GET_SCORE comp_v36_daily_down_attempt_11_rig_candidate_score
#define V36_PROFILE_GET_FRAMES comp_v36_daily_down_attempt_11_rig_candidate_frames
#endif

#include V36_PROFILE_HEADER

typedef struct {
    uint8_t *data;
    size_t size;
    uint32_t read_count;
} file_nor_t;

static int require_true(bool condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

static bool file_nor_read(void *context, uint32_t offset, uint8_t *destination, size_t length)
{
    file_nor_t *nor = (file_nor_t *)context;

    if (nor == NULL || destination == NULL || offset > nor->size || length > nor->size - offset) {
        return false;
    }
    memcpy(destination, &nor->data[offset], length);
    nor->read_count++;
    return true;
}

static bool load_file(const char *path, file_nor_t *out_nor)
{
    FILE *file = NULL;
    long length;

    if (path == NULL || out_nor == NULL || fopen_s(&file, path, "rb") != 0 || file == NULL ||
        fseek(file, 0L, SEEK_END) != 0 || (length = ftell(file)) <= 0L ||
        (unsigned long)length > UINT32_MAX || fseek(file, 0L, SEEK_SET) != 0) {
        if (file != NULL) {
            fclose(file);
        }
        return false;
    }
    out_nor->data = (uint8_t *)malloc((size_t)length);
    if (out_nor->data == NULL || fread(out_nor->data, 1u, (size_t)length, file) != (size_t)length) {
        free(out_nor->data);
        out_nor->data = NULL;
        fclose(file);
        return false;
    }
    fclose(file);
    out_nor->size = (size_t)length;
    return true;
}

static bool read_token(FILE *file, char *destination, size_t destination_size)
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
    } while (character != EOF && (character == ' ' || character == '\t' || character == '\r' || character == '\n'));
    if (character == EOF) {
        return false;
    }
    do {
        if (length + 1u >= destination_size) {
            return false;
        }
        destination[length++] = (char)character;
        character = fgetc(file);
    } while (character != EOF && character != ' ' && character != '\t' && character != '\r' && character != '\n');
    destination[length] = '\0';
    return true;
}

static bool load_p4(const char *path, uint8_t *destination, size_t destination_size)
{
    FILE *file = NULL;
    char token[16];
    unsigned long width;
    unsigned long height;
    size_t index;

    if (path == NULL || destination == NULL || fopen_s(&file, path, "rb") != 0 || file == NULL ||
        !read_token(file, token, sizeof(token)) || strcmp(token, "P4") != 0 ||
        !read_token(file, token, sizeof(token))) {
        if (file != NULL) {
            fclose(file);
        }
        return false;
    }
    width = strtoul(token, NULL, 10);
    if (!read_token(file, token, sizeof(token))) {
        fclose(file);
        return false;
    }
    height = strtoul(token, NULL, 10);
    if (width != 200u || height != 200u || destination_size < 5000u ||
        fread(destination, 1u, 5000u, file) != 5000u) {
        fclose(file);
        return false;
    }
    fclose(file);
    for (index = 0u; index < 5000u; ++index) {
        destination[index] = (uint8_t)~destination[index];
    }
    return true;
}

static bool registered_plan_only(const comp_expression_rig_profile_t *profile,
                                 const comp_expression_rig_plan_t *plan)
{
    uint8_t layer_index;

    if (profile == NULL || plan == NULL || plan->layer_count != 13u) {
        return false;
    }
    for (layer_index = 0u; layer_index < plan->layer_count; ++layer_index) {
        size_t component_index;
        bool found = false;

        for (component_index = 0u; component_index < profile->component_count; ++component_index) {
            if (profile->components[component_index].component_id == plan->layers[layer_index].component_id) {
                found = true;
                break;
            }
        }
        if (!found) {
            return false;
        }
    }
    return true;
}

static int verify_special_events_fail_closed(const comp_expression_rig_profile_t *profile)
{
    static const comp_expression_rig_scene_t scenes[] = {
        COMP_EXPRESSION_RIG_SCENE_MENU, COMP_EXPRESSION_RIG_SCENE_RECORDING,
        COMP_EXPRESSION_RIG_SCENE_SLEEP, COMP_EXPRESSION_RIG_SCENE_CHARGING,
        COMP_EXPRESSION_RIG_SCENE_ERROR,
    };
    comp_expression_rig_state_t state = {
        .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
        .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
        .attention = COMP_EXPRESSION_RIG_ATTENTION_DOWN,
        .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL,
        .interaction_memory = 0u,
        .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN,
    };
    size_t index;

    for (index = 0u; index < sizeof(scenes) / sizeof(scenes[0]); ++index) {
        comp_expression_rig_plan_t plan;
        state.scene = scenes[index];
        if (require_true(profile->scene_charm_component[state.scene] == COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID &&
                         !comp_expression_rig_build_plan(profile, &state, &plan),
                         "unbound special V36 candidate events must fail closed")) {
            return 1;
        }
    }
    return 0;
}

static int exercise_target(file_nor_t *nor, companion_epaper_panel_stm32wba_target_t target,
                           const char *frame_directory)
{
    static const comp_expression_rig_canvas_t canvas = {.width = 200u, .height = 200u, .stride_bytes = 25u};
    companion_screen_assets_stm32wba_t adapter;
    companion_screen_assets_stm32wba_config_t config;
    const comp_expression_rig_profile_t *profile;
    const comp_expression_rig_registered_performance_score_t *score;
    const V36_PROFILE_FRAME_TYPE *frames;
    comp_asset_store_t store;
    comp_expression_rig_asset_pack_t pack;
    uint8_t scratch[5000];
    uint8_t output[5000];
    uint8_t expected[5000];
    uint8_t index;

    companion_screen_assets_stm32wba_init(&adapter);
    config = (companion_screen_assets_stm32wba_config_t){
        .target = target, .partition_size = (uint32_t)nor->size, .read = file_nor_read, .context = nor,
    };
    profile = V36_PROFILE_GET_PROFILE();
    score = V36_PROFILE_GET_SCORE();
    frames = V36_PROFILE_GET_FRAMES();
    if (require_true(companion_screen_assets_stm32wba_bind(&adapter, &store, &config) &&
                     store.storage_class == COMP_ASSET_STORAGE_EXTERNAL_NOR && store.mapped_data == NULL,
                     "WBA adapter must bind V36 through callback-only external NOR") ||
        require_true(comp_expression_rig_asset_pack_mount(&pack, &store, &canvas) == COMP_EXPRESSION_RIG_ASSET_MOUNT_OK &&
                     pack.component_count == V36_PROFILE_COMPONENT_COUNT &&
                     pack.revision == 36u,
                     "V36 CRIG must mount with its generated profile identity") ||
        require_true(comp_expression_rig_asset_pack_verify_payload(&pack, scratch, sizeof(scratch)) &&
                     !V36_PROFILE_RUNTIME_ACTIVATION_ALLOWED() &&
                     score != NULL && frames != NULL && score->step_count == V36_PROFILE_FRAME_COUNT,
                     "V36 target candidate must remain inactive and payload-verified")) {
        return 1;
    }
    for (index = 0u; index < V36_PROFILE_FRAME_COUNT; ++index) {
        comp_expression_rig_plan_t plan;
        comp_expression_rig_bounds_t bounds;
        char expected_path[512];
        int written = snprintf(expected_path, sizeof(expected_path), "%s\\%s", frame_directory,
                               frames[index].target_pbm_filename);

        if (require_true(written > 0 && (size_t)written < sizeof(expected_path) &&
                         frames[index].duration_ms == score->steps[index].duration_ms &&
                         comp_expression_rig_build_registered_score_step(profile, score, index, NULL, &plan) &&
                         registered_plan_only(profile, &plan),
                         "V36 score step must contain only registered source components") ||
            require_true(comp_expression_rig_compose_1bpp(&canvas, &plan, comp_expression_rig_asset_pack_read_component,
                         &pack, scratch, sizeof(scratch), output, sizeof(output), &bounds) && bounds.has_ink &&
                         load_p4(expected_path, expected, sizeof(expected)) && memcmp(output, expected, sizeof(output)) == 0,
                         "WBA external-NOR V36 composition must exactly match browser PBM frame")) {
            return 1;
        }
    }
    if (verify_special_events_fail_closed(profile) != 0) {
        return 1;
    }
    return require_true(nor->read_count > 0u, "WBA callback must service V36 component reads");
}

int main(int argc, char **argv)
{
    file_nor_t nor = {0};
    int result;

    if (argc != 3 || !load_file(argv[1], &nor)) {
        fprintf(stderr, "FAIL: usage: test_wba_v36_daily_down_rig_asset_mount <pack.crig> <frame-dir>\n");
        return 1;
    }
    result = exercise_target(&nor, COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55, argv[2]);
    if (result == 0) {
        result = exercise_target(&nor, COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA65, argv[2]);
    }
    free(nor.data);
    if (result != 0) {
        return result;
    }
    puts("PASS: WBA55/WBA65 rebuild every V36 Daily-down component frame from external NOR; special events stay fail-closed");
    return 0;
}
