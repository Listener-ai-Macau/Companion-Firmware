#ifndef COMPANION_R10_BALL_DIAGNOSTIC_H
#define COMPANION_R10_BALL_DIAGNOSTIC_H

#include <stdint.h>

#define COMP_R10_BALL_DIAGNOSTIC_ACTIVATIONS 16u
#define COMP_R10_BALL_DIAGNOSTIC_LOOP_POSITIONS 8u
#define COMP_R10_BALL_DIAGNOSTIC_X_START 32u
#define COMP_R10_BALL_DIAGNOSTIC_X_END 64u
#define COMP_R10_BALL_DIAGNOSTIC_X_STEP 8u
#define COMP_R10_BALL_DIAGNOSTIC_Y 80u
#define COMP_R10_BALL_DIAGNOSTIC_SIZE 12u
#define COMP_R10_BALL_DIAGNOSTIC_TRAVEL 32u

static const uint8_t comp_r10_ball_diagnostic_positions[
    COMP_R10_BALL_DIAGNOSTIC_ACTIVATIONS] = {
        32u, 40u, 48u, 56u, 64u, 56u, 48u, 40u,
        32u, 40u, 48u, 56u, 64u, 56u, 48u, 40u,
};

/* Black-pixel masks for a 12x12 disk centered on the half-pixel at 5.5.
 * Rows are stored as the two bytes crossed by a byte-aligned X origin. */
static const uint8_t comp_r10_ball_diagnostic_row_masks[12u][2u] = {
    {0x0Fu, 0x00u},
    {0x3Fu, 0xC0u},
    {0x7Fu, 0xE0u},
    {0x7Fu, 0xE0u},
    {0xFFu, 0xF0u},
    {0xFFu, 0xF0u},
    {0xFFu, 0xF0u},
    {0xFFu, 0xF0u},
    {0x7Fu, 0xE0u},
    {0x7Fu, 0xE0u},
    {0x3Fu, 0xC0u},
    {0x0Fu, 0x00u},
};

static inline uint8_t comp_r10_ball_diagnostic_previous_x(uint8_t step)
{
    return step == 0u ? 0xFFu : comp_r10_ball_diagnostic_positions[step - 1u];
}

static inline uint8_t comp_r10_ball_diagnostic_current_x(uint8_t step)
{
    return comp_r10_ball_diagnostic_positions[step];
}

#endif /* COMPANION_R10_BALL_DIAGNOSTIC_H */
