#include "pet_attention.h"

static const char *const k_attention_clip_names[COMP_PET_ATTENTION_COUNT] = {
    "attention.center",
    "attention.up_left",
    "attention.up",
    "attention.up_right",
    "attention.left",
    "attention.right",
    "attention.down_left",
    "attention.down",
    "attention.down_right",
};

static int8_t attention_axis(uint16_t coordinate, uint16_t extent)
{
    if (extent == 0u || coordinate >= extent) {
        return 0;
    }
    if ((uint32_t)coordinate * 3u < extent) {
        return -1;
    }
    if ((uint32_t)coordinate * 3u >= (uint32_t)extent * 2u) {
        return 1;
    }
    return 0;
}

comp_pet_attention_direction_t comp_pet_attention_from_touch(
    uint16_t x,
    uint16_t y,
    uint16_t width,
    uint16_t height)
{
    int8_t horizontal = attention_axis(x, width);
    int8_t vertical = attention_axis(y, height);

    if (vertical < 0) {
        return horizontal < 0 ? COMP_PET_ATTENTION_UP_LEFT
               : horizontal > 0 ? COMP_PET_ATTENTION_UP_RIGHT
                                : COMP_PET_ATTENTION_UP;
    }
    if (vertical > 0) {
        return horizontal < 0 ? COMP_PET_ATTENTION_DOWN_LEFT
               : horizontal > 0 ? COMP_PET_ATTENTION_DOWN_RIGHT
                                : COMP_PET_ATTENTION_DOWN;
    }
    return horizontal < 0 ? COMP_PET_ATTENTION_LEFT
           : horizontal > 0 ? COMP_PET_ATTENTION_RIGHT
                            : COMP_PET_ATTENTION_CENTER;
}

const char *comp_pet_attention_clip_name(comp_pet_attention_direction_t direction)
{
    return direction < COMP_PET_ATTENTION_COUNT
               ? k_attention_clip_names[direction]
               : k_attention_clip_names[COMP_PET_ATTENTION_CENTER];
}

bool comp_pet_attention_self_test(void)
{
    const uint16_t width = 200u;
    const uint16_t height = 200u;

    return comp_pet_attention_from_touch(0u, 0u, width, height) ==
               COMP_PET_ATTENTION_UP_LEFT &&
           comp_pet_attention_from_touch(100u, 0u, width, height) ==
               COMP_PET_ATTENTION_UP &&
           comp_pet_attention_from_touch(199u, 0u, width, height) ==
               COMP_PET_ATTENTION_UP_RIGHT &&
           comp_pet_attention_from_touch(0u, 100u, width, height) ==
               COMP_PET_ATTENTION_LEFT &&
           comp_pet_attention_from_touch(100u, 100u, width, height) ==
               COMP_PET_ATTENTION_CENTER &&
           comp_pet_attention_from_touch(199u, 100u, width, height) ==
               COMP_PET_ATTENTION_RIGHT &&
           comp_pet_attention_from_touch(0u, 199u, width, height) ==
               COMP_PET_ATTENTION_DOWN_LEFT &&
           comp_pet_attention_from_touch(100u, 199u, width, height) ==
               COMP_PET_ATTENTION_DOWN &&
           comp_pet_attention_from_touch(199u, 199u, width, height) ==
               COMP_PET_ATTENTION_DOWN_RIGHT &&
           comp_pet_attention_from_touch(200u, 200u, width, height) ==
               COMP_PET_ATTENTION_CENTER &&
           comp_pet_attention_clip_name(COMP_PET_ATTENTION_DOWN_RIGHT)[0] == 'a';
}
