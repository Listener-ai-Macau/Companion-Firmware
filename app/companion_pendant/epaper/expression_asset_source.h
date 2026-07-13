#ifndef COMPANION_EPAPER_EXPRESSION_ASSET_SOURCE_H
#define COMPANION_EPAPER_EXPRESSION_ASSET_SOURCE_H

#include "emote_asset_pack.h"
#include "expression_state.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    const comp_emote_asset_pack_t *pack;
    uint32_t copied_frames;
    uint32_t failed_reads;
} comp_epaper_expression_asset_source_t;

bool comp_epaper_expression_asset_source_init(
    comp_epaper_expression_asset_source_t *source,
    const comp_emote_asset_pack_t *pack);
bool comp_epaper_expression_asset_source_copy_frame(
    comp_epaper_expression_asset_source_t *source,
    const comp_emote_frame_t *frame,
    uint8_t *destination,
    size_t destination_size);
bool comp_epaper_expression_asset_source_copy_frame_index(
    comp_epaper_expression_asset_source_t *source,
    uint16_t frame_index,
    uint8_t *destination,
    size_t destination_size);
bool comp_epaper_expression_asset_source_copy_expression(
    comp_epaper_expression_asset_source_t *source,
    comp_epaper_expression_t expression,
    uint8_t *destination,
    size_t destination_size);
bool comp_epaper_expression_asset_source_copy_clip(
    comp_epaper_expression_asset_source_t *source,
    const char *clip_name,
    uint8_t *destination,
    size_t destination_size);
bool comp_epaper_expression_asset_source_copy_clip_frame(
    comp_epaper_expression_asset_source_t *source,
    const char *clip_name,
    uint16_t frame_in_clip,
    uint8_t *destination,
    size_t destination_size);
bool comp_epaper_expression_asset_source_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_EXPRESSION_ASSET_SOURCE_H */
