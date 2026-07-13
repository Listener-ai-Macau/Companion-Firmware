#ifndef COMPANION_EPAPER_EMOTE_ASSET_PACK_H
#define COMPANION_EPAPER_EMOTE_ASSET_PACK_H

#include "asset_store.h"
#include "emote_player.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_EMOTE_ASSET_PACK_FORMAT_VERSION 1u
#define COMP_EMOTE_ASSET_PACK_HEADER_BYTES 80u
#define COMP_EMOTE_ASSET_PACK_CLIP_ENTRY_BYTES 16u
#define COMP_EMOTE_ASSET_PACK_FRAME_ENTRY_BYTES 20u

typedef enum {
    COMP_SCREEN_PIXEL_FORMAT_MONO_1BPP_WHITE_IS_ONE_MSB = 1u,
} comp_screen_pixel_format_t;

typedef enum {
    COMP_EMOTE_FRAME_ENCODING_RAW_FULL_FRAME = 1u,
    COMP_EMOTE_FRAME_ENCODING_PACKBITS = 2u,
} comp_emote_frame_encoding_t;

typedef struct {
    uint16_t width;
    uint16_t height;
    uint16_t stride_bytes;
    comp_screen_pixel_format_t pixel_format;
} comp_screen_asset_profile_t;

typedef struct {
    const char *name;
    uint16_t format_version;
    uint16_t priority;
    uint32_t revision;
    comp_screen_asset_profile_t profile;
    comp_emote_frame_encoding_t frame_encoding;
    uint32_t payload_offset;
    uint32_t payload_size;
    uint32_t payload_crc32;
    bool has_payload_crc32;
    const comp_emote_catalog_t *catalog;
    const comp_asset_store_t *store;
} comp_emote_asset_pack_t;

typedef enum {
    COMP_EMOTE_ASSET_MOUNT_OK = 0u,
    COMP_EMOTE_ASSET_MOUNT_BAD_ARGUMENT = 1u,
    COMP_EMOTE_ASSET_MOUNT_IO_ERROR = 2u,
    COMP_EMOTE_ASSET_MOUNT_BAD_MAGIC = 3u,
    COMP_EMOTE_ASSET_MOUNT_UNSUPPORTED_VERSION = 4u,
    COMP_EMOTE_ASSET_MOUNT_BAD_LAYOUT = 5u,
    COMP_EMOTE_ASSET_MOUNT_PROFILE_MISMATCH = 6u,
    COMP_EMOTE_ASSET_MOUNT_CAPACITY_EXCEEDED = 7u,
    COMP_EMOTE_ASSET_MOUNT_INDEX_CRC_MISMATCH = 8u,
    COMP_EMOTE_ASSET_MOUNT_PAYLOAD_CRC_MISMATCH = 9u,
    COMP_EMOTE_ASSET_MOUNT_BAD_CATALOG = 10u,
} comp_emote_asset_mount_result_t;

typedef struct {
    comp_emote_catalog_t catalog;
    comp_emote_asset_pack_t pack;
} comp_emote_asset_mount_t;

bool comp_screen_asset_profile_validate(const comp_screen_asset_profile_t *profile);
bool comp_screen_asset_profile_matches(const comp_screen_asset_profile_t *candidate,
                                       const comp_screen_asset_profile_t *target);
bool comp_emote_asset_pack_validate(const comp_emote_asset_pack_t *pack);
const comp_emote_asset_pack_t *comp_emote_asset_pack_select(
    const comp_emote_asset_pack_t *packs,
    size_t pack_count,
    const comp_screen_asset_profile_t *target);
bool comp_emote_asset_pack_read_frame(const comp_emote_asset_pack_t *pack,
                                      const comp_emote_frame_t *frame,
                                      uint8_t *destination,
                                      size_t destination_size);
bool comp_emote_asset_pack_verify_payload(const comp_emote_asset_pack_t *pack,
                                          uint8_t *scratch,
                                          size_t scratch_size);
comp_emote_asset_mount_result_t comp_emote_asset_pack_mount(
    comp_emote_asset_mount_t *mount,
    const comp_asset_store_t *store,
    const comp_screen_asset_profile_t *target,
    comp_emote_clip_t *clips,
    size_t clip_capacity,
    comp_emote_frame_t *frames,
    size_t frame_capacity,
    char *strings,
    size_t string_capacity,
    uint8_t *scratch,
    size_t scratch_size);
const char *comp_emote_asset_mount_result_name(comp_emote_asset_mount_result_t result);
bool comp_emote_asset_pack_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_EMOTE_ASSET_PACK_H */
