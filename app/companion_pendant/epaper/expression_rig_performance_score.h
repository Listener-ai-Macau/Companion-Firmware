#ifndef COMPANION_EPAPER_EXPRESSION_RIG_PERFORMANCE_SCORE_H
#define COMPANION_EPAPER_EXPRESSION_RIG_PERFORMANCE_SCORE_H

#include "expression_rig.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY = 0u,
    COMP_EXPRESSION_RIG_SCORE_PHASE_PREPARE,
    COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD,
    COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE,
    COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT,
    COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD,
    COMP_EXPRESSION_RIG_SCORE_PHASE_RELEASE,
    COMP_EXPRESSION_RIG_SCORE_PHASE_RETURN,
    COMP_EXPRESSION_RIG_SCORE_PHASE_SETTLE,
    COMP_EXPRESSION_RIG_SCORE_PHASE_COUNT,
} comp_expression_rig_score_phase_t;

typedef struct {
    uint16_t component_id;
    int8_t offset_x;
    int8_t offset_y;
} comp_expression_rig_score_pose_t;

typedef struct {
    comp_expression_rig_score_phase_t phase;
    uint16_t duration_ms;
    const comp_expression_rig_score_pose_t *poses;
    uint8_t pose_count;
} comp_expression_rig_score_step_t;

typedef struct {
    const comp_expression_rig_score_step_t *steps;
    uint8_t step_count;
} comp_expression_rig_performance_score_t;

typedef struct {
    comp_expression_rig_score_phase_t phase;
    uint16_t duration_ms;
    comp_expression_rig_state_t state;
    const comp_expression_rig_registered_pose_t *pose;
} comp_expression_rig_registered_score_step_t;

typedef struct {
    const comp_expression_rig_registered_score_step_t *steps;
    uint8_t step_count;
} comp_expression_rig_registered_performance_score_t;

const char *comp_expression_rig_score_phase_name(
    comp_expression_rig_score_phase_t phase);

/* Apply one generated source-component score step to a calm Daily entry plan.
 * This only chooses registered component ids and their legal offsets; the
 * compositor remains the sole reader of the source-derived masks. */
bool comp_expression_rig_apply_score_step(
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_plan_t *entry_plan,
    const comp_expression_rig_performance_score_t *score,
    uint8_t step_index,
    comp_expression_rig_plan_t *out_plan);

/* Build one generated core/accent score step. The optional dynamic context
 * contributes only energy and interaction-memory offsets to the generated
 * source pose; phase identity and components come exclusively from the score. */
bool comp_expression_rig_build_registered_score_step(
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_registered_performance_score_t *score,
    uint8_t step_index,
    const comp_expression_rig_state_t *dynamic_context,
    comp_expression_rig_plan_t *out_plan);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_EXPRESSION_RIG_PERFORMANCE_SCORE_H */
