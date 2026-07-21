#include "asset_store.h"
#include "expression_rig.h"
#include "expression_rig_asset_pack.h"
#include "expression_rig_performance_score.h"
#include "generated/expression_rig_v22_emotion_separation_candidate_profile.h"
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
                                const char *directory, const char *filename)
{
    int written;

    if (destination == NULL || destination_size == 0u || directory == NULL || filename == NULL) {
        return false;
    }
    written = snprintf(destination, destination_size, "%s\\%s", directory, filename);
    return written > 0 && (size_t)written < destination_size;
}

static bool plan_has_only_registered_components(const comp_expression_rig_profile_t *profile,
                                                const comp_expression_rig_plan_t *plan)
{
    uint8_t layer_index;

    if (profile == NULL || plan == NULL || plan->layer_count == 0u ||
        plan->layer_count > COMP_EXPRESSION_RIG_MAX_LAYERS) {
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
    static const comp_expression_rig_scene_t special_scenes[] = {
        COMP_EXPRESSION_RIG_SCENE_MENU,
        COMP_EXPRESSION_RIG_SCENE_RECORDING,
        COMP_EXPRESSION_RIG_SCENE_SLEEP,
        COMP_EXPRESSION_RIG_SCENE_CHARGING,
        COMP_EXPRESSION_RIG_SCENE_ERROR,
    };
    comp_expression_rig_state_t state = {
        .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
        .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
        .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
        .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL,
        .interaction_memory = 0u,
        .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN,
    };
    comp_expression_rig_plan_t plan;
    size_t index;

    for (index = 0u; index < sizeof(special_scenes) / sizeof(special_scenes[0]); ++index) {
        state.scene = special_scenes[index];
        if (require_true(profile->scene_charm_component[state.scene] ==
                         COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID &&
                         !comp_expression_rig_build_plan(profile, &state, &plan),
                         "V22 candidate must fail closed for every unbound special event")) {
            return 1;
        }
    }
    return 0;
}

static int exercise_target(file_nor_t *nor,
                           companion_epaper_panel_stm32wba_target_t target,
                           const char *frame_directory)
{
    static const comp_expression_rig_canvas_t canvas = {
        .width = 200u, .height = 200u, .stride_bytes = 25u,
    };
    companion_screen_assets_stm32wba_t adapter;
    companion_screen_assets_stm32wba_config_t config;
    const comp_expression_rig_profile_t *profile;
    comp_asset_store_t store;
    comp_expression_rig_asset_pack_t pack;
    uint8_t scratch[5000];
    uint8_t output[5000];
    uint8_t expected[5000];
    uint8_t bridge_index;

    companion_screen_assets_stm32wba_init(&adapter);
    config = (companion_screen_assets_stm32wba_config_t){
        .target = target,
        .partition_size = (uint32_t)nor->size,
        .read = file_nor_read,
        .context = nor,
    };
    profile = comp_v22_emotion_separation_rig_candidate_profile();
    if (require_true(companion_screen_assets_stm32wba_bind(&adapter, &store, &config),
                     "WBA adapter must bind V22 through callback-only external NOR") ||
        require_true(store.storage_class == COMP_ASSET_STORAGE_EXTERNAL_NOR && store.mapped_data == NULL,
                     "V22 target storage must remain external NOR") ||
        require_true(comp_expression_rig_asset_pack_mount(&pack, &store, &canvas) ==
                         COMP_EXPRESSION_RIG_ASSET_MOUNT_OK,
                     "V22 CRIG source-mask pack must mount") ||
        require_true(pack.component_count == COMP_V22_EMOTION_SEPARATION_RIG_CANDIDATE_COMPONENT_COUNT &&
                         pack.revision == COMP_V22_EMOTION_SEPARATION_RIG_CANDIDATE_REVISION,
                     "mounted V22 pack identity must match its generated profile") ||
        require_true(comp_expression_rig_asset_pack_verify_payload(&pack, scratch, sizeof(scratch)),
                     "V22 CRIG payload CRC must verify") ||
        require_true(!comp_v22_emotion_separation_rig_candidate_runtime_activation_allowed(),
                     "V22 target candidate must remain runtime-inactive") ||
        require_true(comp_v22_emotion_separation_rig_candidate_bridge_count() ==
                         COMP_V22_EMOTION_SEPARATION_RIG_CANDIDATE_BRIDGE_COUNT,
                     "V22 must expose exactly the accepted directed bridge graph")) {
        return 1;
    }

    for (bridge_index = 0u;
         bridge_index < comp_v22_emotion_separation_rig_candidate_bridge_count();
         ++bridge_index) {
        const comp_v22_emotion_separation_rig_bridge_t *bridge =
            comp_v22_emotion_separation_rig_candidate_bridge(bridge_index);
        uint8_t frame_index;

        if (require_true(bridge != NULL && bridge->score != NULL && bridge->frames != NULL &&
                         bridge->frame_count >= 7u && bridge->frame_count <= 8u &&
                         bridge->score->step_count == bridge->frame_count,
                         "V22 generated bridge descriptor is invalid")) {
            return 1;
        }
        for (frame_index = 0u; frame_index < bridge->frame_count; ++frame_index) {
            comp_expression_rig_plan_t plan;
            comp_expression_rig_bounds_t bounds;
            char expected_path[512];

            if (require_true(comp_expression_rig_build_registered_score_step(
                                 profile, bridge->score, frame_index, NULL, &plan) &&
                             plan_has_only_registered_components(profile, &plan),
                             "V22 bridge step must contain only registered source components") ||
                require_true(comp_expression_rig_compose_1bpp(
                                 &canvas, &plan, comp_expression_rig_asset_pack_read_component,
                                 &pack, scratch, sizeof(scratch), output, sizeof(output), &bounds) &&
                             bounds.has_ink,
                             "V22 registered source masks must compose into a nonblank face") ||
                require_true(build_expected_path(expected_path, sizeof(expected_path), frame_directory,
                                                 bridge->frames[frame_index].target_pbm_filename) &&
                             load_p4(expected_path, expected, sizeof(expected)) &&
                             memcmp(output, expected, sizeof(output)) == 0,
                             "WBA external-NOR V22 composition must exactly match browser/PBM bridge frame")) {
                return 1;
            }
        }
    }
    if (verify_special_events_fail_closed(profile) != 0) {
        return 1;
    }
    return require_true(nor->read_count > 0u,
                        "WBA callback must service V22 source-component reads");
}

int main(int argc, char **argv)
{
    file_nor_t nor = {0};
    int result;

    if (argc != 3 || !load_file(argv[1], &nor)) {
        fprintf(stderr, "FAIL: usage: test_wba_v22_emotion_separation_rig_asset_mount <pack.crig> <bridge-frame-dir>\n");
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
    puts("PASS: WBA55/WBA65 rebuild every owner-accepted V22 directed component bridge from external NOR; special events remain fail-closed");
    return 0;
}
