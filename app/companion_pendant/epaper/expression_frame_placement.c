#include "expression_frame_placement.h"

#include <string.h>

static bool profile_is_usable(const comp_screen_asset_profile_t *profile,
                              size_t *required_bytes)
{
    size_t required;
    uint16_t minimum_stride;

    if (profile == NULL || required_bytes == NULL || profile->width == 0u ||
        profile->height == 0u ||
        profile->pixel_format != COMP_SCREEN_PIXEL_FORMAT_MONO_1BPP_WHITE_IS_ONE_MSB) {
        return false;
    }
    minimum_stride = (uint16_t)((profile->width + 7u) / 8u);
    if (profile->stride_bytes < minimum_stride) {
        return false;
    }
    required = (size_t)profile->stride_bytes * profile->height;
    if (profile->height != 0u && required / profile->height != profile->stride_bytes) {
        return false;
    }
    *required_bytes = required;
    return true;
}

static bool pixel_is_black(const uint8_t *data,
                           uint16_t stride_bytes,
                           uint16_t x,
                           uint16_t y)
{
    const size_t index = (size_t)y * stride_bytes + (x / 8u);
    const uint8_t mask = (uint8_t)(0x80u >> (x & 7u));
    return (data[index] & mask) == 0u;
}

static void set_black(uint8_t *data, uint16_t stride_bytes, uint16_t x, uint16_t y)
{
    const size_t index = (size_t)y * stride_bytes + (x / 8u);
    const uint8_t mask = (uint8_t)(0x80u >> (x & 7u));
    data[index] &= (uint8_t)~mask;
}

bool comp_expression_frame_place_1bpp(
    const comp_screen_asset_profile_t *profile,
    const uint8_t *source,
    size_t source_size,
    comp_expression_frame_anchor_t source_anchor,
    comp_expression_frame_anchor_t requested_center,
    uint8_t *destination,
    size_t destination_size,
    comp_expression_frame_placement_bounds_t *out_bounds)
{
    size_t required_bytes;
    int32_t offset_x;
    int32_t offset_y;
    bool has_ink = false;
    uint16_t left = 0u;
    uint16_t top = 0u;
    uint16_t right = 0u;
    uint16_t bottom = 0u;

    if (!profile_is_usable(profile, &required_bytes) || source == NULL ||
        destination == NULL || out_bounds == NULL || source_size < required_bytes ||
        destination_size < required_bytes || source_anchor.x >= profile->width ||
        source_anchor.y >= profile->height || requested_center.x >= profile->width ||
        requested_center.y >= profile->height) {
        return false;
    }

    offset_x = (int32_t)requested_center.x - source_anchor.x;
    offset_y = (int32_t)requested_center.y - source_anchor.y;
    for (uint16_t y = 0u; y < profile->height; ++y) {
        for (uint16_t x = 0u; x < profile->width; ++x) {
            int32_t destination_x;
            int32_t destination_y;

            if (!pixel_is_black(source, profile->stride_bytes, x, y)) {
                continue;
            }
            destination_x = (int32_t)x + offset_x;
            destination_y = (int32_t)y + offset_y;
            if (destination_x < 0 || destination_y < 0 ||
                destination_x >= profile->width || destination_y >= profile->height) {
                return false;
            }
            if (!has_ink) {
                left = (uint16_t)destination_x;
                right = (uint16_t)destination_x;
                top = (uint16_t)destination_y;
                bottom = (uint16_t)destination_y;
                has_ink = true;
            } else {
                if ((uint16_t)destination_x < left) {
                    left = (uint16_t)destination_x;
                }
                if ((uint16_t)destination_x > right) {
                    right = (uint16_t)destination_x;
                }
                if ((uint16_t)destination_y < top) {
                    top = (uint16_t)destination_y;
                }
                if ((uint16_t)destination_y > bottom) {
                    bottom = (uint16_t)destination_y;
                }
            }
        }
    }
    if (!has_ink) {
        return false;
    }

    memset(destination, 0xFF, required_bytes);
    for (uint16_t y = 0u; y < profile->height; ++y) {
        for (uint16_t x = 0u; x < profile->width; ++x) {
            if (pixel_is_black(source, profile->stride_bytes, x, y)) {
                set_black(destination,
                          profile->stride_bytes,
                          (uint16_t)((int32_t)x + offset_x),
                          (uint16_t)((int32_t)y + offset_y));
            }
        }
    }
    *out_bounds = (comp_expression_frame_placement_bounds_t){
        .has_ink = true,
        .left = left,
        .top = top,
        .width = (uint16_t)(right - left + 1u),
        .height = (uint16_t)(bottom - top + 1u),
    };
    return true;
}

bool comp_expression_frame_placement_self_test(void)
{
    static const comp_screen_asset_profile_t profile = {
        .width = 8u,
        .height = 8u,
        .stride_bytes = 1u,
        .pixel_format = COMP_SCREEN_PIXEL_FORMAT_MONO_1BPP_WHITE_IS_ONE_MSB,
    };
    uint8_t source[8] = {0xFFu, 0xFFu, 0x7Fu, 0xFFu, 0xDFu, 0xFFu, 0xFFu, 0xFFu};
    uint8_t destination[8];
    comp_expression_frame_placement_bounds_t bounds;

    memset(destination, 0xA5, sizeof(destination));
    if (!comp_expression_frame_place_1bpp(&profile,
                                           source,
                                           sizeof(source),
                                           (comp_expression_frame_anchor_t){2u, 3u},
                                           (comp_expression_frame_anchor_t){4u, 4u},
                                           destination,
                                           sizeof(destination),
                                           &bounds) ||
        destination[3] != 0xDFu || destination[5] != 0xF7u || !bounds.has_ink ||
        bounds.left != 2u || bounds.top != 3u || bounds.width != 3u ||
        bounds.height != 3u) {
        return false;
    }

    memset(destination, 0xA5, sizeof(destination));
    if (comp_expression_frame_place_1bpp(&profile,
                                          source,
                                          sizeof(source),
                                          (comp_expression_frame_anchor_t){2u, 3u},
                                          (comp_expression_frame_anchor_t){0u, 0u},
                                          destination,
                                          sizeof(destination),
                                          &bounds) ||
        destination[0] != 0xA5u || destination[7] != 0xA5u) {
        return false;
    }
    return true;
}
