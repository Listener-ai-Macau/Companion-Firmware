#ifndef COMPANION_EPAPER_EXPRESSION_FRAME_PLACEMENT_H
#define COMPANION_EPAPER_EXPRESSION_FRAME_PLACEMENT_H

#include "emote_asset_pack.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Coordinates identify the semantic center of a complete expression group,
 * not an individual eye or decoration. */
typedef struct {
    uint16_t x;
    uint16_t y;
} comp_expression_frame_anchor_t;

typedef struct {
    bool has_ink;
    uint16_t left;
    uint16_t top;
    uint16_t width;
    uint16_t height;
} comp_expression_frame_placement_bounds_t;

/*
 * White-fill destination and place every black pixel of a 1bpp MSB frame so
 * source_anchor lands on requested_center. The entire expression is checked
 * in-bounds before destination is changed; failed placement never clips and
 * leaves destination untouched. This is portable geometry only: it does not
 * mount a CEMP pack, schedule display work, write Flash, or call target HAL.
 */
bool comp_expression_frame_place_1bpp(
    const comp_screen_asset_profile_t *profile,
    const uint8_t *source,
    size_t source_size,
    comp_expression_frame_anchor_t source_anchor,
    comp_expression_frame_anchor_t requested_center,
    uint8_t *destination,
    size_t destination_size,
    comp_expression_frame_placement_bounds_t *out_bounds);

bool comp_expression_frame_placement_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_EXPRESSION_FRAME_PLACEMENT_H */
