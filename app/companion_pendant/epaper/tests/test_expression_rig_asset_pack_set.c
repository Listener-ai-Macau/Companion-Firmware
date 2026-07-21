#include "asset_store.h"
#include "expression_rig_asset_pack.h"
#include "expression_rig_asset_pack_set.h"

#include <stdio.h>
#include <string.h>

typedef struct {
    const uint8_t *data;
    size_t size;
} memory_nor_t;

static int require_true(bool condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

static bool memory_read(void *context, uint32_t offset, uint8_t *destination, size_t length)
{
    const memory_nor_t *nor = (const memory_nor_t *)context;

    if (nor == NULL || destination == NULL || offset > nor->size || length > nor->size - offset) {
        return false;
    }
    memcpy(destination, &nor->data[offset], length);
    return true;
}

int main(void)
{
    static const uint8_t face_bytes[] = {0xA1u, 0xA2u, 0xA3u, 0xA4u};
    static const uint8_t decoration_bytes[] = {0xD1u, 0xD2u, 0xD3u, 0xD4u};
    static const comp_expression_rig_canvas_t canvas = {200u, 200u, 25u};
    const memory_nor_t face_nor = {face_bytes, sizeof(face_bytes)};
    const memory_nor_t decoration_nor = {decoration_bytes, sizeof(decoration_bytes)};
    comp_asset_store_t face_store;
    comp_asset_store_t decoration_store;
    comp_expression_rig_asset_pack_t face_pack;
    comp_expression_rig_asset_pack_t decoration_pack;
    comp_expression_rig_asset_pack_t duplicate_pack;
    comp_expression_rig_asset_pack_set_t set;
    comp_expression_rig_component_mask_info_t info = {0};
    uint8_t output[2] = {0};

    if (require_true(comp_asset_store_init_reader(&face_store, COMP_ASSET_STORAGE_EXTERNAL_NOR,
                                                  sizeof(face_bytes), memory_read, (void *)&face_nor) &&
                     comp_asset_store_init_reader(&decoration_store, COMP_ASSET_STORAGE_EXTERNAL_NOR,
                                                  sizeof(decoration_bytes), memory_read, (void *)&decoration_nor),
                     "test stores must model external NOR readers")) {
        return 1;
    }
    face_pack = (comp_expression_rig_asset_pack_t){
        .store = &face_store, .canvas = canvas, .component_count = 1u,
        .components = {{.component_id = 1u, .mask = {2u, 1u, 2u, 2u}, .data_offset = 0u, .data_size = 2u}},
    };
    decoration_pack = (comp_expression_rig_asset_pack_t){
        .store = &decoration_store, .canvas = canvas, .component_count = 1u,
        .components = {{.component_id = 500u, .mask = {2u, 1u, 2u, 2u}, .data_offset = 0u, .data_size = 2u}},
    };
    duplicate_pack = decoration_pack;
    duplicate_pack.components[0].component_id = 1u;
    comp_expression_rig_asset_pack_set_init(&set);
    if (require_true(comp_expression_rig_asset_pack_set_add(&set, &face_pack) &&
                     comp_expression_rig_asset_pack_set_add(&set, &decoration_pack) &&
                     !comp_expression_rig_asset_pack_set_add(&set, &duplicate_pack),
                     "set must retain two distinct namespaces and reject a duplicate id")) {
        return 1;
    }
    if (require_true(comp_expression_rig_asset_pack_set_read_component(&set, 1u, output, sizeof(output), &info) &&
                     output[0] == 0xA1u && output[1] == 0xA2u && info.data_size == 2u &&
                     comp_expression_rig_asset_pack_set_read_component(&set, 500u, output, sizeof(output), &info) &&
                     output[0] == 0xD1u && output[1] == 0xD2u &&
                     !comp_expression_rig_asset_pack_set_read_component(&set, 42u, output, sizeof(output), &info),
                     "set must route only registered masks to their owning external pack")) {
        return 1;
    }
    puts("PASS: dual external-NOR Rig pack set routes registered source masks and fails closed");
    return 0;
}
