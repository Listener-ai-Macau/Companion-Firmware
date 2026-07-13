#ifndef COMPANION_EPAPER_EXPRESSION_ASSETS_200X200_H
#define COMPANION_EPAPER_EXPRESSION_ASSETS_200X200_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "expression_state.h"

#ifdef __cplusplus
extern "C" {
#endif

#define COMPANION_EPAPER_EXPRESSION_ASSET_WIDTH 200u
#define COMPANION_EPAPER_EXPRESSION_ASSET_HEIGHT 200u
#define COMPANION_EPAPER_EXPRESSION_ASSET_BYTES \
    ((COMPANION_EPAPER_EXPRESSION_ASSET_WIDTH / 8u) * COMPANION_EPAPER_EXPRESSION_ASSET_HEIGHT)

/* Copies an approved 1-bit ExpressionV1 frame in SSD1681-compatible polarity. */
bool companion_epaper_expression_asset_200x200_copy(
    comp_epaper_expression_t expression,
    uint8_t *out_frame,
    size_t out_frame_size);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_EXPRESSION_ASSETS_200X200_H */
