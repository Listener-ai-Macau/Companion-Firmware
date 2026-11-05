#ifndef COMPANION_EPAPER_EXPRESSION_TOUCH_GAZE_H
#define COMPANION_EPAPER_EXPRESSION_TOUCH_GAZE_H

#include "expression_rig.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_EXPRESSION_RIG_TOUCH_CANVAS_WIDTH 200u
#define COMP_EXPRESSION_RIG_TOUCH_CANVAS_HEIGHT 200u
#define COMP_EXPRESSION_RIG_TOUCH_CENTER_X 100u
#define COMP_EXPRESSION_RIG_TOUCH_CENTER_Y 100u

typedef struct {
    bool pressed;
    uint16_t x;
    uint16_t y;
} comp_expression_rig_touch_sample_t;

typedef struct {
    comp_expression_rig_attention_t attention;
    uint16_t touch_x;
    uint16_t touch_y;
    int8_t primary_x;
    int8_t primary_y;
    int8_t sparkle_x;
    int8_t sparkle_y;
    bool engaged;
} comp_expression_rig_touch_gaze_target_t;

/* Map one normalized 200x200 FT6336 sample directly to legal V9 highlight and
 * sparkle offsets. Release is a center target; no random selection or emotion
 * change occurs here. */
bool comp_expression_rig_touch_gaze_map(
    const comp_expression_rig_touch_sample_t *sample,
    comp_expression_rig_touch_gaze_target_t *out_target);

/* Apply only registered highlight and sparkle offsets to an already-built
 * component plan. Eye bodies, brows, nose, mouth, and cheeks are untouched. */
bool comp_expression_rig_touch_gaze_apply(
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_touch_gaze_target_t *target,
    comp_expression_rig_plan_t *in_out_plan);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_EXPRESSION_TOUCH_GAZE_H */
