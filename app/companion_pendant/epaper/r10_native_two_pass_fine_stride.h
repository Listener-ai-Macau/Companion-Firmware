#ifndef COMPANION_R10_NATIVE_TWO_PASS_FINE_STRIDE_H
#define COMPANION_R10_NATIVE_TWO_PASS_FINE_STRIDE_H

#include <stdint.h>

#define COMP_R10_NATIVE_TWO_PASS_FINE_STRIDE_QUALIFICATION_FRAMES 16u
#define COMP_R10_NATIVE_TWO_PASS_FINE_STRIDE_X_START 32u
#define COMP_R10_NATIVE_TWO_PASS_FINE_STRIDE_X_END 64u
#define COMP_R10_NATIVE_TWO_PASS_FINE_STRIDE_X_STEP 2u
#define COMP_R10_NATIVE_TWO_PASS_FINE_STRIDE_Y 80u
#define COMP_R10_NATIVE_TWO_PASS_FINE_STRIDE_SIZE 12u
#define COMP_R10_NATIVE_TWO_PASS_FINE_STRIDE_TRAVEL 32u

static const uint8_t comp_r10_native_two_pass_fine_stride_qualification[
    COMP_R10_NATIVE_TWO_PASS_FINE_STRIDE_QUALIFICATION_FRAMES] = {
        34u, 36u, 38u, 40u, 42u, 44u, 46u, 48u,
        50u, 52u, 54u, 56u, 58u, 60u, 62u, 64u,
};

static const uint8_t comp_r10_native_two_pass_fine_stride_loop[32u] = {
        62u, 60u, 58u, 56u, 54u, 52u, 50u, 48u,
        46u, 44u, 42u, 40u, 38u, 36u, 34u, 32u,
        34u, 36u, 38u, 40u, 42u, 44u, 46u, 48u,
        50u, 52u, 54u, 56u, 58u, 60u, 62u, 64u,
};

static const uint8_t comp_r10_native_two_pass_fine_stride_row_masks[12u][2u] = {
    {0x0Fu, 0x00u}, {0x3Fu, 0xC0u}, {0x7Fu, 0xE0u}, {0x7Fu, 0xE0u},
    {0xFFu, 0xF0u}, {0xFFu, 0xF0u}, {0xFFu, 0xF0u}, {0xFFu, 0xF0u},
    {0x7Fu, 0xE0u}, {0x7Fu, 0xE0u}, {0x3Fu, 0xC0u}, {0x0Fu, 0x00u},
};

#endif
