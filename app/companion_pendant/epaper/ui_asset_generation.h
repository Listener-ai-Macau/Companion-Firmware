#ifndef COMPANION_EPAPER_UI_ASSET_GENERATION_H
#define COMPANION_EPAPER_UI_ASSET_GENERATION_H

#include "asset_store.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_UI_ASSET_GENERATION_FORMAT_VERSION 1u
#define COMP_UI_ASSET_GENERATION_ROOT_BYTES 128u
#define COMP_UI_ASSET_GENERATION_SECTOR_BYTES 4096u
#if defined(COMPANION_WBA_RESOURCE_PROFILE) && COMPANION_WBA_RESOURCE_PROFILE
/* WBA roots follow the selected bank extent. Keep the legacy WB geometry. */
#include "../update/wba_storage_layout.h"
#define COMP_UI_ASSET_GENERATION_ROOT_A_OFFSET (COMP_WBA_NOR_UI_BYTES - 2u * COMP_WBA_NOR_SECTOR_BYTES)
#define COMP_UI_ASSET_GENERATION_ROOT_B_OFFSET (COMP_WBA_NOR_UI_BYTES - COMP_WBA_NOR_SECTOR_BYTES)
#define COMP_UI_ASSET_GENERATION_ARENA_END COMP_UI_ASSET_GENERATION_ROOT_A_OFFSET
#else
#define COMP_UI_ASSET_GENERATION_ROOT_A_OFFSET 0x001FE000u
#define COMP_UI_ASSET_GENERATION_ROOT_B_OFFSET 0x001FF000u
/* CRRP owns [0x1DC000, 0x1FD000); [0x1FD000, 0x1FE000) is flash-test scratch. */
#define COMP_UI_ASSET_GENERATION_ARENA_END 0x001DC000u
#endif
#define COMP_UI_ASSET_GENERATION_ID_BYTES 32u

#define COMP_UI_ASSET_MANIFEST_HEADER_BYTES 32u
#define COMP_UI_ASSET_MANIFEST_ENTRY_BYTES 24u
#define COMP_UI_ASSET_ENTRY_OVERRIDE_RAW_1BPP 0x0001u
#define COMP_UI_ASSET_ENTRY_OVERRIDE_PACKBITS_1BPP 0x0002u
#define COMP_UI_ASSET_ENTRY_XOR_PATCH_1BPP 0x0004u

typedef struct {
    uint32_t generation;
    uint32_t root_offset;
    uint32_t base_pack_size;
    uint32_t blob_offset;
    uint32_t blob_size;
    uint32_t blob_crc32;
    uint32_t manifest_offset;
    uint32_t manifest_size;
    uint32_t manifest_crc32;
    uint32_t arena_next_offset;
    uint8_t resource_id[COMP_UI_ASSET_GENERATION_ID_BYTES];
} comp_ui_asset_generation_root_t;

typedef struct {
    uint32_t state_hash;
    uint16_t base_frame_index;
    uint16_t flags;
    uint32_t frame_crc32;
    uint32_t payload_offset;
    uint16_t payload_size;
    uint16_t duration_ms;
    uint32_t payload_crc32;
} comp_ui_asset_generation_entry_t;

typedef struct {
    const comp_asset_store_t *store;
    comp_ui_asset_generation_root_t root;
    uint16_t entry_count;
    bool mounted;
} comp_ui_asset_generation_t;

typedef struct {
    bool (*read)(void *context, uint32_t offset, uint8_t *data, size_t length);
    bool (*erase_4k)(void *context, uint32_t offset);
    bool (*write)(void *context, uint32_t offset,
                  const uint8_t *data, size_t length);
    void *context;
    uint32_t partition_size;
} comp_ui_asset_generation_io_t;

typedef enum {
    COMP_UI_ASSET_INSTALL_OK = 0u,
    COMP_UI_ASSET_INSTALL_ALREADY_CURRENT = 1u,
    COMP_UI_ASSET_INSTALL_BAD_ARGUMENT = 2u,
    COMP_UI_ASSET_INSTALL_BAD_LAYOUT = 3u,
    COMP_UI_ASSET_INSTALL_STALE_GENERATION = 4u,
    COMP_UI_ASSET_INSTALL_NO_SPACE = 5u,
    COMP_UI_ASSET_INSTALL_ERASE_FAILED = 6u,
    COMP_UI_ASSET_INSTALL_WRITE_FAILED = 7u,
    COMP_UI_ASSET_INSTALL_VERIFY_FAILED = 8u,
    COMP_UI_ASSET_INSTALL_ROOT_COMMIT_FAILED = 9u,
} comp_ui_asset_install_result_t;

typedef struct {
    comp_ui_asset_install_result_t result;
    uint32_t previous_generation;
    uint32_t active_generation;
    uint32_t blob_offset;
    uint32_t blob_bytes_written;
    uint32_t root_bytes_written;
    uint32_t sectors_erased;
} comp_ui_asset_install_receipt_t;

typedef struct {
    const comp_ui_asset_generation_io_t *io;
    comp_ui_asset_generation_root_t next_root;
    comp_ui_asset_install_receipt_t receipt;
    uint32_t expected_blob_crc32;
    uint32_t running_blob_crc32;
    uint32_t bytes_written;
    bool active;
} comp_ui_asset_generation_transaction_t;

uint32_t comp_ui_asset_state_hash(const char *state_id);

bool comp_ui_asset_generation_mount(
    comp_ui_asset_generation_t *generation,
    const comp_asset_store_t *store);

bool comp_ui_asset_generation_find(
    const comp_ui_asset_generation_t *generation,
    uint32_t state_hash,
    comp_ui_asset_generation_entry_t *entry);

bool comp_ui_asset_generation_read_override(
    const comp_ui_asset_generation_t *generation,
    const comp_ui_asset_generation_entry_t *entry,
    uint8_t *destination,
    size_t destination_size);
bool comp_ui_asset_generation_apply_xor_region(
    const comp_ui_asset_generation_t *generation,
    const comp_ui_asset_generation_entry_t *entry,
    uint8_t *destination,
    size_t destination_size,
    uint16_t frame_stride,
    uint16_t x_byte,
    uint16_t y,
    uint16_t width_bytes,
    uint16_t height,
    uint8_t *payload_scratch,
    size_t payload_scratch_size);

comp_ui_asset_install_receipt_t comp_ui_asset_generation_install(
    const comp_ui_asset_generation_io_t *io,
    uint32_t base_pack_size,
    uint32_t expected_active_generation,
    const uint8_t resource_id[COMP_UI_ASSET_GENERATION_ID_BYTES],
    const uint8_t *blob,
    uint32_t blob_size,
    uint32_t manifest_offset,
    uint32_t manifest_size);

comp_ui_asset_install_receipt_t comp_ui_asset_generation_begin(
    comp_ui_asset_generation_transaction_t *transaction,
    const comp_ui_asset_generation_io_t *io,
    uint32_t base_pack_size,
    uint32_t expected_active_generation,
    const uint8_t resource_id[COMP_UI_ASSET_GENERATION_ID_BYTES],
    uint32_t blob_size,
    uint32_t blob_crc32,
    uint32_t manifest_offset,
    uint32_t manifest_size,
    uint32_t manifest_crc32);

bool comp_ui_asset_generation_write(
    comp_ui_asset_generation_transaction_t *transaction,
    const uint8_t *data,
    size_t length);

comp_ui_asset_install_receipt_t comp_ui_asset_generation_finish(
    comp_ui_asset_generation_transaction_t *transaction);

void comp_ui_asset_generation_abort(
    comp_ui_asset_generation_transaction_t *transaction);

const char *comp_ui_asset_install_result_name(
    comp_ui_asset_install_result_t result);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_UI_ASSET_GENERATION_H */
