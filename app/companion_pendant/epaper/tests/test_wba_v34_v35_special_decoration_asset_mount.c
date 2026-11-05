#include "asset_store.h"
#include "expression_rig_asset_pack.h"
#include "expression_rig_asset_pack_set.h"
#include "screen_assets_stm32wba.h"

#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum {
    SPECIAL_DECORATION_FIRST_COMPONENT_ID = 500u,
    SPECIAL_DECORATION_COMPONENT_COUNT = 39u,
    SPECIAL_DECORATION_REVISION = 35u,
};

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

static int exercise_target(file_nor_t *nor,
                           companion_epaper_panel_stm32wba_target_t target)
{
    static const comp_expression_rig_canvas_t canvas = {
        .width = 200u, .height = 200u, .stride_bytes = 25u,
    };
    companion_screen_assets_stm32wba_t adapter;
    companion_screen_assets_stm32wba_config_t config;
    comp_asset_store_t store;
    comp_expression_rig_asset_pack_t pack;
    comp_expression_rig_asset_pack_set_t pack_set;
    uint8_t scratch[256];
    uint16_t component_id;

    companion_screen_assets_stm32wba_init(&adapter);
    config = (companion_screen_assets_stm32wba_config_t){
        .target = target,
        .partition_size = (uint32_t)nor->size,
        .read = file_nor_read,
        .context = nor,
    };
    if (require_true(companion_screen_assets_stm32wba_bind(&adapter, &store, &config),
                     "WBA adapter must bind the special-decoration pack through external NOR") ||
        require_true(store.storage_class == COMP_ASSET_STORAGE_EXTERNAL_NOR && store.mapped_data == NULL,
                     "special-decoration pack must remain callback-only external NOR") ||
        require_true(comp_expression_rig_asset_pack_mount(&pack, &store, &canvas) ==
                         COMP_EXPRESSION_RIG_ASSET_MOUNT_OK,
                     "source-derived special-decoration CRIG must mount") ||
        require_true(pack.revision == SPECIAL_DECORATION_REVISION &&
                         pack.component_count == SPECIAL_DECORATION_COMPONENT_COUNT,
                     "special-decoration CRIG identity must match its generated export") ||
        require_true(comp_expression_rig_asset_pack_verify_payload(&pack, scratch, sizeof(scratch)),
                     "special-decoration CRIG payload CRC must verify")) {
        return 1;
    }
    comp_expression_rig_asset_pack_set_init(&pack_set);
    if (require_true(comp_expression_rig_asset_pack_set_add(&pack_set, &pack) &&
                     !comp_expression_rig_asset_pack_set_add(&pack_set, &pack),
                     "component-pack set must accept one namespace and reject duplicate ids")) {
        return 1;
    }
    for (component_id = SPECIAL_DECORATION_FIRST_COMPONENT_ID;
         component_id < SPECIAL_DECORATION_FIRST_COMPONENT_ID + SPECIAL_DECORATION_COMPONENT_COUNT;
         ++component_id) {
        comp_expression_rig_component_mask_info_t info = {0};

        if (require_true(comp_expression_rig_asset_pack_set_read_component(&pack_set, component_id, scratch,
                                                                            sizeof(scratch), &info) &&
                         info.width > 0u && info.height > 0u &&
                         info.stride_bytes >= (uint16_t)((info.width + 7u) / 8u) &&
                         info.data_size <= sizeof(scratch),
                         "each registered special-decoration component must be readable from NOR")) {
            return 1;
        }
    }
    {
        comp_expression_rig_component_mask_info_t info = {0};

        if (require_true(!comp_expression_rig_asset_pack_set_read_component(
                             &pack_set, (uint16_t)(SPECIAL_DECORATION_FIRST_COMPONENT_ID - 1u), scratch,
                             sizeof(scratch), &info) &&
                         !comp_expression_rig_asset_pack_set_read_component(
                             &pack_set, (uint16_t)(SPECIAL_DECORATION_FIRST_COMPONENT_ID +
                                                   SPECIAL_DECORATION_COMPONENT_COUNT), scratch,
                             sizeof(scratch), &info),
                         "unregistered special-decoration component ids must fail closed")) {
            return 1;
        }
    }
    return require_true(nor->read_count > SPECIAL_DECORATION_COMPONENT_COUNT,
                        "WBA callback must serve special-decoration component reads");
}

int main(int argc, char **argv)
{
    file_nor_t nor = {0};
    int result;

    if (argc != 2 || !load_file(argv[1], &nor)) {
        fprintf(stderr, "FAIL: usage: test_wba_v34_v35_special_decoration_asset_mount <pack.crig>\n");
        return 1;
    }
    result = exercise_target(&nor, COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55);
    if (result == 0) {
        result = exercise_target(&nor, COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA65);
    }
    free(nor.data);
    if (result != 0) {
        return result;
    }
    puts("PASS: WBA55/WBA65 callback-only external NOR mounts and reads every V34/V35 source decoration component");
    return 0;
}
