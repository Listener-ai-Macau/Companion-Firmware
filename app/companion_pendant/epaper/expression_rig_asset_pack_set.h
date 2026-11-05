#ifndef COMPANION_EPAPER_EXPRESSION_RIG_ASSET_PACK_SET_H
#define COMPANION_EPAPER_EXPRESSION_RIG_ASSET_PACK_SET_H

#include "expression_rig_asset_pack.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* A candidate score may combine a face pack and a separately versioned
 * decoration pack. This routes registered masks only; it owns no pixels. */
#define COMP_EXPRESSION_RIG_ASSET_PACK_SET_MAX_PACKS 2u

typedef struct {
    const comp_expression_rig_asset_pack_t *packs[COMP_EXPRESSION_RIG_ASSET_PACK_SET_MAX_PACKS];
    uint8_t count;
} comp_expression_rig_asset_pack_set_t;

void comp_expression_rig_asset_pack_set_init(
    comp_expression_rig_asset_pack_set_t *set);

/* Rejects a duplicate component id across packs so a score has one source
 * for every layer. */
bool comp_expression_rig_asset_pack_set_add(
    comp_expression_rig_asset_pack_set_t *set,
    const comp_expression_rig_asset_pack_t *pack);

bool comp_expression_rig_asset_pack_set_read_component(
    void *context,
    uint16_t component_id,
    uint8_t *destination,
    size_t destination_size,
    comp_expression_rig_component_mask_info_t *out_info);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_EXPRESSION_RIG_ASSET_PACK_SET_H */
