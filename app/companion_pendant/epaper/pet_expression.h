#ifndef COMPANION_EPAPER_PET_EXPRESSION_H
#define COMPANION_EPAPER_PET_EXPRESSION_H

#include "expression_state.h"
#include "screen_framebuffer.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    COMP_PET_MOUTH_NEUTRAL = 0u,
    COMP_PET_MOUTH_SMILE = 1u,
    COMP_PET_MOUTH_OPEN = 2u,
    COMP_PET_MOUTH_FROWN = 3u,
    COMP_PET_MOUTH_SOFT = 4u,
    COMP_PET_MOUTH_POUT = 5u,
} comp_pet_mouth_t;

typedef enum {
    COMP_PET_BROW_NONE = 0u,
    COMP_PET_BROW_RELAXED = 1u,
    COMP_PET_BROW_RAISED = 2u,
    COMP_PET_BROW_WARM = 3u,
    COMP_PET_BROW_FOCUSED = 4u,
    COMP_PET_BROW_WORRIED = 5u,
    COMP_PET_BROW_SLEEPY = 6u,
} comp_pet_brow_t;

typedef enum {
    COMP_PET_MARK_NONE = 0u,
    COMP_PET_MARK_LISTEN = 1u,
    COMP_PET_MARK_THINK = 2u,
    COMP_PET_MARK_RECORD = 3u,
    COMP_PET_MARK_SPARK = 4u,
    COMP_PET_MARK_ALERT = 5u,
    COMP_PET_MARK_QUESTION = 6u,
    COMP_PET_MARK_HEART = 7u,
    COMP_PET_MARK_SLEEP = 8u,
} comp_pet_mark_t;

/* All values are logical screen-space parameters, not target or panel facts.
 * The generated reference sheet is a style grammar: product code composes eyes,
 * brows, mouth, cheeks, gaze, marks, and living phase instead of replaying
 * fixed sticker bitmaps. */
typedef struct {
    comp_epaper_expression_t expression;
    int8_t gaze_x;
    int8_t gaze_y;
    uint8_t eye_open;
    int8_t eyelid_tilt;
    uint8_t eye_width;
    uint8_t eye_spacing;
    int8_t eye_pair_tilt;
    uint8_t highlight_scale;
    int8_t face_shift_x;
    int8_t face_shift_y;
    uint8_t brow_lift;
    int8_t brow_asymmetry;
    uint8_t mouth_scale;
    uint8_t cheek_strength;
    uint8_t variation;
    comp_pet_brow_t brow;
    comp_pet_mouth_t mouth;
    comp_pet_mark_t mark;
} comp_pet_expression_pose_t;

bool comp_pet_expression_pose_is_valid(const comp_pet_expression_pose_t *pose);
void comp_pet_expression_pose_from_expression(comp_pet_expression_pose_t *out_pose,
                                              comp_epaper_expression_t expression,
                                              uint8_t phase,
                                              uint32_t variation_seed);
void comp_pet_expression_pose_from_touch(comp_pet_expression_pose_t *out_pose,
                                         uint16_t x,
                                         uint16_t y,
                                         uint16_t width,
                                         uint16_t height,
                                         uint8_t phase,
                                         uint32_t variation_seed);
bool comp_pet_expression_render(const comp_pet_expression_pose_t *pose,
                                comp_screen_framebuffer_t *framebuffer);
bool comp_pet_expression_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_PET_EXPRESSION_H */
