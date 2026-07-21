#ifndef COMPANION_EPAPER_EXPRESSION_INTERACTION_SESSION_H
#define COMPANION_EPAPER_EXPRESSION_INTERACTION_SESSION_H

#include "expression_choreographer.h"
#include "expression_rig_performance_score.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* A causal route contains its existing baseline, zero or more bridge emotions,
 * the requested target, and a calm settle.  The session stores state metadata
 * only; each visible plan is rebuilt from registered source components on
 * demand and never stores a face bitmap. */
#define COMP_EXPRESSION_RIG_INTERACTION_MAX_SCORE_KEYFRAMES 5u
#define COMP_EXPRESSION_RIG_INTERACTION_MAX_FRAMES \
    (COMP_EXPRESSION_RIG_INTERACTION_MAX_SCORE_KEYFRAMES + \
     COMP_EXPRESSION_RIG_MAX_EMOTION_ROUTE + 2u)

#define COMP_EXPRESSION_RIG_INTERACTION_NO_SCORE_STEP UINT8_MAX

typedef enum {
    COMP_EXPRESSION_RIG_INTERACTION_FRAME_PERFORMANCE = 0u,
    COMP_EXPRESSION_RIG_INTERACTION_FRAME_ENTRY,
    COMP_EXPRESSION_RIG_INTERACTION_FRAME_BRIDGE,
    COMP_EXPRESSION_RIG_INTERACTION_FRAME_TARGET,
    COMP_EXPRESSION_RIG_INTERACTION_FRAME_SETTLE,
} comp_expression_rig_interaction_frame_kind_t;

typedef struct {
    comp_expression_rig_interaction_frame_kind_t kind;
    uint8_t route_index;
    uint8_t score_step_index;
    comp_expression_rig_score_phase_t score_phase;
    uint16_t post_refresh_hold_ms;
    const comp_expression_rig_performance_score_t *performance_score;
    comp_expression_rig_state_t state;
} comp_expression_rig_interaction_frame_t;

typedef struct {
    comp_expression_rig_behavior_decision_t decision;
    comp_expression_rig_interaction_frame_t
        frames[COMP_EXPRESSION_RIG_INTERACTION_MAX_FRAMES];
    uint8_t frame_count;
} comp_expression_rig_interaction_sequence_t;

typedef struct {
    comp_expression_rig_behavior_state_t behavior;
    comp_expression_rig_interaction_sequence_t sequence;
    uint8_t next_frame_index;
    bool active;
    bool frame_outstanding;
    uint32_t submitted_frames;
    uint32_t visible_frames;
    uint32_t failed_frame_retries;
    uint32_t rejected_submissions;
} comp_expression_rig_interaction_session_t;

void comp_expression_rig_interaction_session_init(
    comp_expression_rig_interaction_session_t *session);

/* Accept one product interaction only when no previous causal sequence is
 * active.  Unsupported special scenes leave the session unchanged and return
 * false, preserving the product fail-closed contract. */
bool comp_expression_rig_interaction_session_start(
    comp_expression_rig_interaction_session_t *session,
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_choreography_input_t *input);

/* A notice score is source-derived, not an additional face card. The session
 * retains only meaningful component poses that can remain visible after an
 * e-paper refresh: entry, completed lead, response, completed accent and
 * completed release. It then continues through the causal affect route.
 * Passing NULL keeps the compact route-only sequence. */
bool comp_expression_rig_interaction_session_start_with_notice_score(
    comp_expression_rig_interaction_session_t *session,
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_choreography_input_t *input,
    const comp_expression_rig_performance_score_t *notice_score);

/* A caller must submit a visible component plan only after the previous plan
 * completed through complete_frame().  Calling this while a frame is pending
 * is rejected rather than replacing a face during a panel refresh. */
bool comp_expression_rig_interaction_session_take_frame(
    comp_expression_rig_interaction_session_t *session,
    const comp_expression_rig_profile_t *profile,
    comp_expression_rig_interaction_frame_t *out_frame,
    comp_expression_rig_plan_t *out_plan);

/* A failed panel transaction leaves the same frame eligible for retry.  A
 * visible completion is the only operation that advances the sequence. */
bool comp_expression_rig_interaction_session_complete_frame(
    comp_expression_rig_interaction_session_t *session,
    bool visible);

const char *comp_expression_rig_interaction_frame_kind_name(
    comp_expression_rig_interaction_frame_kind_t kind);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_EXPRESSION_INTERACTION_SESSION_H */
