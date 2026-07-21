#ifndef COMPANION_EPAPER_EXPRESSION_RIG_ASSET_PACK_H
#define COMPANION_EPAPER_EXPRESSION_RIG_ASSET_PACK_H

#include "asset_store.h"
#include "expression_rig.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_EXPRESSION_RIG_ASSET_PACK_FORMAT_VERSION 1u
#define COMP_EXPRESSION_RIG_ASSET_PACK_HEADER_BYTES 80u
#define COMP_EXPRESSION_RIG_ASSET_PACK_INDEX_ENTRY_BYTES 20u
/* The largest registered source-derived candidate is the 96-component
 * expanded Rig.  Keeping the bound exact avoids reserving 768 unused bytes
 * of WB55 RAM for a hypothetical, unregistered pack. */
#define COMP_EXPRESSION_RIG_ASSET_PACK_MAX_COMPONENTS 96u

typedef enum {
    COMP_EXPRESSION_RIG_ASSET_MOUNT_OK = 0u,
    COMP_EXPRESSION_RIG_ASSET_MOUNT_BAD_ARGUMENT,
    COMP_EXPRESSION_RIG_ASSET_MOUNT_STORAGE_NOT_EXTERNAL,
    COMP_EXPRESSION_RIG_ASSET_MOUNT_IO_ERROR,
    COMP_EXPRESSION_RIG_ASSET_MOUNT_BAD_MAGIC,
    COMP_EXPRESSION_RIG_ASSET_MOUNT_UNSUPPORTED_VERSION,
    COMP_EXPRESSION_RIG_ASSET_MOUNT_BAD_LAYOUT,
    COMP_EXPRESSION_RIG_ASSET_MOUNT_PROFILE_MISMATCH,
    COMP_EXPRESSION_RIG_ASSET_MOUNT_INDEX_CRC_MISMATCH,
    COMP_EXPRESSION_RIG_ASSET_MOUNT_PAYLOAD_CRC_MISMATCH,
} comp_expression_rig_asset_mount_result_t;

typedef struct {
    uint16_t component_id;
    comp_expression_rig_component_mask_info_t mask;
    uint32_t data_offset;
    uint32_t data_size;
} comp_expression_rig_asset_index_entry_t;

typedef struct {
    const comp_asset_store_t *store;
    comp_expression_rig_canvas_t canvas;
    uint32_t revision;
    uint8_t safe_inset_px;
    uint8_t source_sha256[32];
    uint16_t component_count;
    uint32_t data_offset;
    uint32_t payload_crc32;
    comp_expression_rig_asset_index_entry_t
        components[COMP_EXPRESSION_RIG_ASSET_PACK_MAX_COMPONENTS];
} comp_expression_rig_asset_pack_t;

/* Mounts an inactive-or-active Rig component bundle from external NOR only.
 * It validates the complete index before any component can be composed. */
comp_expression_rig_asset_mount_result_t comp_expression_rig_asset_pack_mount(
    comp_expression_rig_asset_pack_t *pack,
    const comp_asset_store_t *store,
    const comp_expression_rig_canvas_t *target);

/* Verifies the complete external payload without retaining it in internal
 * Flash or RAM. Callers supply a bounded scratch buffer. */
bool comp_expression_rig_asset_pack_verify_payload(
    const comp_expression_rig_asset_pack_t *pack,
    uint8_t *scratch,
    size_t scratch_size);

/* Callback compatible with comp_expression_rig_compose_1bpp(). It returns
 * only registered source masks and never creates facial pixels itself. */
bool comp_expression_rig_asset_pack_read_component(
    void *context,
    uint16_t component_id,
    uint8_t *destination,
    size_t destination_size,
    comp_expression_rig_component_mask_info_t *out_info);

const char *comp_expression_rig_asset_mount_result_name(
    comp_expression_rig_asset_mount_result_t result);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_EXPRESSION_RIG_ASSET_PACK_H */
