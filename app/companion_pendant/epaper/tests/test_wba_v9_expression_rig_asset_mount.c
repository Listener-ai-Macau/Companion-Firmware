#include "asset_store.h"
#include "expression_rig.h"
#include "expression_rig_asset_pack.h"
#include "generated/expression_rig_v9_candidate_profile.h"
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

static int exercise_target(file_nor_t *nor,
                           companion_epaper_panel_stm32wba_target_t target,
                           const char *expected_pbm)
{
    static const comp_expression_rig_canvas_t canvas = {
        .width = 200u, .height = 200u, .stride_bytes = 25u,
    };
    companion_screen_assets_stm32wba_t adapter;
    companion_screen_assets_stm32wba_config_t config;
    comp_asset_store_t store;
    comp_expression_rig_asset_pack_t pack;
    comp_expression_rig_state_t daily = {
        .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
        .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
        .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
        .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL,
        .interaction_memory = 0u,
        .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN,
    };
    comp_expression_rig_state_t unavailable = daily;
    comp_expression_rig_plan_t plan;
    comp_expression_rig_bounds_t bounds;
    uint8_t scratch[1024];
    uint8_t output[5000];
    uint8_t expected[5000];

    companion_screen_assets_stm32wba_init(&adapter);
    config = (companion_screen_assets_stm32wba_config_t){
        .target = target,
        .partition_size = (uint32_t)nor->size,
        .read = file_nor_read,
        .context = nor,
    };
    if (require_true(companion_screen_assets_stm32wba_bind(&adapter, &store, &config),
                     "WBA adapter must bind the Rig pack through external NOR") ||
        require_true(store.storage_class == COMP_ASSET_STORAGE_EXTERNAL_NOR && store.mapped_data == NULL,
                     "WBA Rig store must be callback-only external NOR") ||
        require_true(comp_expression_rig_asset_pack_mount(&pack, &store, &canvas) ==
                         COMP_EXPRESSION_RIG_ASSET_MOUNT_OK,
                     "source-derived Rig component pack must mount") ||
        require_true(pack.component_count == COMP_V9_EXPRESSION_RIG_CANDIDATE_COMPONENT_COUNT &&
                         pack.revision == COMP_V9_EXPRESSION_RIG_CANDIDATE_REVISION,
                     "mounted Rig identity must match the generated profile") ||
        require_true(comp_expression_rig_asset_pack_verify_payload(&pack, scratch, sizeof(scratch)),
                     "Rig component payload CRC must verify") ||
        require_true(!comp_v9_expression_rig_candidate_runtime_activation_allowed(),
                     "candidate profile must remain runtime-inactive") ||
        require_true(comp_expression_rig_build_plan(comp_v9_expression_rig_candidate_profile(),
                                                     &daily, &plan),
                     "candidate profile must build a daily Rig plan") ||
        require_true(comp_expression_rig_compose_1bpp(&canvas, &plan,
                                                       comp_expression_rig_asset_pack_read_component,
                                                       &pack, scratch, sizeof(scratch), output,
                                                       sizeof(output), &bounds) && bounds.has_ink,
                     "component masks must compose into a complete face") ||
        require_true(load_p4(expected_pbm, expected, sizeof(expected)) &&
                         memcmp(output, expected, sizeof(output)) == 0,
                     "external Rig composition must match the source-derived PBM") ||
        require_true(nor->read_count > 0u,
                     "WBA callback must service Rig component reads")) {
        return 1;
    }
    unavailable.scene = COMP_EXPRESSION_RIG_SCENE_CHARGING;
    if (require_true(!comp_expression_rig_build_plan(comp_v9_expression_rig_candidate_profile(),
                                                      &unavailable, &plan),
                     "unapproved charging art must fail closed instead of borrowing another face")) {
        return 1;
    }
    return 0;
}

int main(int argc, char **argv)
{
    file_nor_t nor = {0};
    int result;

    if (argc != 3 || !load_file(argv[1], &nor)) {
        fprintf(stderr, "FAIL: usage: test_wba_v9_expression_rig_asset_mount <pack.crig> <expected.pbm>\n");
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
    puts("PASS: WBA55/WBA65 callback-only external NOR reconstructs the source-derived v9 Rig face");
    return 0;
}
