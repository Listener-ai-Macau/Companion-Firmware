#include "expression_frame_placement.h"

#include <stdio.h>
#include <string.h>

static int require_true(bool condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

int main(void)
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

    if (require_true(comp_expression_frame_placement_self_test(),
                     "built-in placement self-test")) {
        return 1;
    }

    memset(destination, 0x00, sizeof(destination));
    if (require_true(comp_expression_frame_place_1bpp(
                         &profile, source, sizeof(source),
                         (comp_expression_frame_anchor_t){2u, 3u},
                         (comp_expression_frame_anchor_t){5u, 2u},
                         destination, sizeof(destination), &bounds),
                     "whole expression places at requested center") ||
        require_true(destination[1] == 0xEFu && destination[3] == 0xFBu,
                     "both expression pixels move by the same offset") ||
        require_true(bounds.has_ink && bounds.left == 3u && bounds.top == 1u &&
                         bounds.width == 3u && bounds.height == 3u,
                     "output bounds describe the complete moved expression")) {
        return 1;
    }

    memset(destination, 0xA5, sizeof(destination));
    if (require_true(!comp_expression_frame_place_1bpp(
                          &profile, source, sizeof(source),
                          (comp_expression_frame_anchor_t){2u, 3u},
                          (comp_expression_frame_anchor_t){0u, 0u},
                          destination, sizeof(destination), &bounds),
                     "out-of-bounds center is rejected instead of clipped") ||
        require_true(destination[0] == 0xA5u && destination[7] == 0xA5u,
                     "failed placement leaves destination unchanged")) {
        return 1;
    }
    return 0;
}
