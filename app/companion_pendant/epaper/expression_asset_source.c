#include "expression_asset_source.h"

#include <string.h>

static const comp_emote_clip_t *find_clip(const comp_emote_catalog_t *catalog,
                                          const char *name)
{
    if (catalog == NULL || name == NULL) {
        return NULL;
    }
    for (size_t index = 0u; index < catalog->clip_count; ++index) {
        if (strcmp(catalog->clips[index].name, name) == 0) {
            return &catalog->clips[index];
        }
    }
    return NULL;
}

bool comp_epaper_expression_asset_source_init(
    comp_epaper_expression_asset_source_t *source,
    const comp_emote_asset_pack_t *pack)
{
    if (source == NULL) {
        return false;
    }
    memset(source, 0, sizeof(*source));
    if (!comp_emote_asset_pack_validate(pack) ||
        (pack->frame_encoding != COMP_EMOTE_FRAME_ENCODING_RAW_FULL_FRAME &&
         pack->frame_encoding != COMP_EMOTE_FRAME_ENCODING_PACKBITS)) {
        return false;
    }
    source->pack = pack;
    return true;
}

bool comp_epaper_expression_asset_source_copy_frame(
    comp_epaper_expression_asset_source_t *source,
    const comp_emote_frame_t *frame,
    uint8_t *destination,
    size_t destination_size)
{
    if (source == NULL || source->pack == NULL || frame == NULL ||
        !comp_emote_asset_pack_read_frame(source->pack,
                                          frame,
                                          destination,
                                          destination_size)) {
        if (source != NULL) {
            source->failed_reads++;
        }
        return false;
    }
    source->copied_frames++;
    return true;
}

bool comp_epaper_expression_asset_source_copy_frame_index(
    comp_epaper_expression_asset_source_t *source,
    uint16_t frame_index,
    uint8_t *destination,
    size_t destination_size)
{
    const comp_emote_catalog_t *catalog;

    if (source == NULL || source->pack == NULL) {
        return false;
    }
    catalog = source->pack->catalog;
    if (catalog == NULL || frame_index >= catalog->frame_count) {
        source->failed_reads++;
        return false;
    }
    return comp_epaper_expression_asset_source_copy_frame(
        source, &catalog->frames[frame_index], destination, destination_size);
}

bool comp_epaper_expression_asset_source_copy_expression(
    comp_epaper_expression_asset_source_t *source,
    comp_epaper_expression_t expression,
    uint8_t *destination,
    size_t destination_size)
{
    if (source == NULL || source->pack == NULL ||
        !comp_epaper_expression_is_supported(expression)) {
        return false;
    }
    return comp_epaper_expression_asset_source_copy_clip(
        source,
        comp_epaper_expression_name(expression),
        destination,
        destination_size);
}

bool comp_epaper_expression_asset_source_copy_clip(
    comp_epaper_expression_asset_source_t *source,
    const char *clip_name,
    uint8_t *destination,
    size_t destination_size)
{
    return comp_epaper_expression_asset_source_copy_clip_frame(
        source, clip_name, 0u, destination, destination_size);
}

bool comp_epaper_expression_asset_source_copy_clip_frame(
    comp_epaper_expression_asset_source_t *source,
    const char *clip_name,
    uint16_t frame_in_clip,
    uint8_t *destination,
    size_t destination_size)
{
    const comp_emote_clip_t *clip;
    const comp_emote_catalog_t *catalog;

    if (source == NULL || source->pack == NULL || clip_name == NULL) {
        return false;
    }
    catalog = source->pack->catalog;
    clip = find_clip(catalog, clip_name);
    if (clip == NULL || frame_in_clip >= clip->frame_count ||
        (size_t)clip->first_frame + frame_in_clip >= catalog->frame_count) {
        source->failed_reads++;
        return false;
    }
    return comp_epaper_expression_asset_source_copy_frame(
        source,
        &catalog->frames[(size_t)clip->first_frame + frame_in_clip],
        destination,
        destination_size);
}

bool comp_epaper_expression_asset_source_self_test(void)
{
    static const uint8_t payload[] = {0xA5u};
    static const comp_emote_frame_t frames[] = {
        {.data_offset = 0u, .data_size = 1u, .duration_ms = 100u},
    };
    static const comp_emote_clip_t clips[] = {
        {.name = "idle", .first_frame = 0u, .frame_count = 1u,
         .loop_start = 0u, .loop_end = 1u},
    };
    static const comp_emote_catalog_t catalog = {
        .clips = clips,
        .clip_count = 1u,
        .frames = frames,
        .frame_count = 1u,
    };
    comp_asset_store_t store;
    comp_emote_asset_pack_t pack;
    comp_epaper_expression_asset_source_t source;
    uint8_t destination = 0u;

    if (!comp_asset_store_init_memory(&store,
                                      COMP_ASSET_STORAGE_INTERNAL_FLASH,
                                      payload,
                                      sizeof(payload))) {
        return false;
    }
    pack = (comp_emote_asset_pack_t){
        .name = "test",
        .format_version = COMP_EMOTE_ASSET_PACK_FORMAT_VERSION,
        .profile = {
            .width = 8u,
            .height = 1u,
            .stride_bytes = 1u,
            .pixel_format = COMP_SCREEN_PIXEL_FORMAT_MONO_1BPP_WHITE_IS_ONE_MSB,
        },
        .frame_encoding = COMP_EMOTE_FRAME_ENCODING_RAW_FULL_FRAME,
        .payload_size = sizeof(payload),
        .payload_crc32 = 0x74BEB8EAu,
        .has_payload_crc32 = true,
        .catalog = &catalog,
        .store = &store,
    };
    return comp_epaper_expression_asset_source_init(&source, &pack) &&
           comp_epaper_expression_asset_source_copy_expression(
               &source,
               COMP_EPAPER_EXPRESSION_IDLE,
               &destination,
               sizeof(destination)) &&
           comp_epaper_expression_asset_source_copy_clip(
               &source,
               "idle",
               &destination,
               sizeof(destination)) &&
           comp_epaper_expression_asset_source_copy_frame_index(
               &source,
               0u,
               &destination,
               sizeof(destination)) &&
           destination == payload[0] && source.copied_frames == 3u &&
           source.failed_reads == 0u;
}
