#ifndef COMPANION_EPAPER_PET_ATTENTION_H
#define COMPANION_EPAPER_PET_ATTENTION_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Logical display coordinates only. Targets transform raw touch samples before
 * calling this portable policy, so the same attention behavior ports to WBA. */
typedef enum {
    COMP_PET_ATTENTION_CENTER = 0,
    COMP_PET_ATTENTION_UP_LEFT,
    COMP_PET_ATTENTION_UP,
    COMP_PET_ATTENTION_UP_RIGHT,
    COMP_PET_ATTENTION_LEFT,
    COMP_PET_ATTENTION_RIGHT,
    COMP_PET_ATTENTION_DOWN_LEFT,
    COMP_PET_ATTENTION_DOWN,
    COMP_PET_ATTENTION_DOWN_RIGHT,
    COMP_PET_ATTENTION_COUNT,
} comp_pet_attention_direction_t;

comp_pet_attention_direction_t comp_pet_attention_from_touch(
    uint16_t x,
    uint16_t y,
    uint16_t width,
    uint16_t height);
const char *comp_pet_attention_clip_name(comp_pet_attention_direction_t direction);
bool comp_pet_attention_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_PET_ATTENTION_H */
