#ifndef COMPANION_EPAPER_EXPRESSION_RIG_TRACK_COMPOSER_H
#define COMPANION_EPAPER_EXPRESSION_RIG_TRACK_COMPOSER_H

#include "expression_rig.h"

#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Merge independently selected source-component tracks.  The expression plan
 * retains state ownership; the optional functional plan contributes only its
 * registered layers.  This is a plan operation, never a pixel renderer. */
bool comp_expression_rig_merge_tracks(
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_plan_t *expression_plan,
    const comp_expression_rig_plan_t *functional_decoration_plan,
    comp_expression_rig_plan_t *out_plan);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_EXPRESSION_RIG_TRACK_COMPOSER_H */
