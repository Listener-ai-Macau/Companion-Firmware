#ifndef COMPANION_RUNTIME_RESOURCES_H
#define COMPANION_RUNTIME_RESOURCES_H
#include "emote_asset_pack.h"
#include "ui_asset_generation.h"
typedef struct {
#if COMPANION_WBA_UI_EXTERNAL
    /* SPI NOR is a reader, not an addressable C pointer. Only the selected
     * frame entry is brought onto the stack; the catalog stays in the bank. */
    const comp_asset_store_t *store;
    uint32_t frame_table_offset, payload_offset, payload_size;
    uint16_t frame_count;
    uint8_t frame_encoding;
#else
    comp_emote_asset_mount_t base;
#endif
    comp_ui_asset_generation_t generation;
    bool ready;
} comp_runtime_resources_t;
/* Store must outlive the binding and be read-only while rendering. Uses the
 * same CEMP + atomic generation-root format as existing asset OTA. No writes. */
bool comp_runtime_resources_mount(comp_runtime_resources_t *, const comp_asset_store_t *);
bool comp_runtime_resources_read(void *, const char *state_id, uint8_t frame[5000]);
bool comp_runtime_resources_read_ui(void *, uint32_t offset, uint8_t *, size_t);
#endif
