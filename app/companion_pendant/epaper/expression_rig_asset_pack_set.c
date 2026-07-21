#include "expression_rig_asset_pack_set.h"

#include <string.h>

void comp_expression_rig_asset_pack_set_init(
    comp_expression_rig_asset_pack_set_t *set)
{
    if (set != NULL) {
        memset(set, 0, sizeof(*set));
    }
}

bool comp_expression_rig_asset_pack_set_add(
    comp_expression_rig_asset_pack_set_t *set,
    const comp_expression_rig_asset_pack_t *pack)
{
    uint8_t set_index;
    uint16_t component_index;

    if (set == NULL || pack == NULL || pack->component_count == 0u ||
        set->count >= COMP_EXPRESSION_RIG_ASSET_PACK_SET_MAX_PACKS) {
        return false;
    }
    for (set_index = 0u; set_index < set->count; ++set_index) {
        const comp_expression_rig_asset_pack_t *existing = set->packs[set_index];

        if (existing == NULL || existing->canvas.width != pack->canvas.width ||
            existing->canvas.height != pack->canvas.height ||
            existing->canvas.stride_bytes != pack->canvas.stride_bytes) {
            return false;
        }
        for (component_index = 0u; component_index < pack->component_count; ++component_index) {
            uint16_t existing_index;

            for (existing_index = 0u; existing_index < existing->component_count; ++existing_index) {
                if (existing->components[existing_index].component_id ==
                    pack->components[component_index].component_id) {
                    return false;
                }
            }
        }
    }
    set->packs[set->count++] = pack;
    return true;
}

bool comp_expression_rig_asset_pack_set_read_component(
    void *context,
    uint16_t component_id,
    uint8_t *destination,
    size_t destination_size,
    comp_expression_rig_component_mask_info_t *out_info)
{
    comp_expression_rig_asset_pack_set_t *set =
        (comp_expression_rig_asset_pack_set_t *)context;
    uint8_t index;

    if (set == NULL) {
        return false;
    }
    for (index = 0u; index < set->count; ++index) {
        const comp_expression_rig_asset_pack_t *pack = set->packs[index];

        if (pack != NULL && comp_expression_rig_asset_pack_read_component(
                (void *)pack, component_id, destination, destination_size, out_info)) {
            return true;
        }
    }
    return false;
}
