#ifndef COMPANION_EPAPER_EXPRESSION_V22_EVERYDAY_BRIDGE_SESSION_H
#define COMPANION_EPAPER_EXPRESSION_V22_EVERYDAY_BRIDGE_SESSION_H

#include "expression_v22_everyday_bridge_router.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_V22_EVERYDAY_BRIDGE_MIN_POST_REFRESH_HOLD_MS 750u

typedef struct {
    comp_expression_rig_energy_t energy;
    uint8_t interaction_memory;
} comp_v22_everyday_bridge_context_t;

typedef struct {
    uint8_t step_index;
    const char *cue;
    comp_expression_rig_score_phase_t score_phase;
    uint16_t post_refresh_hold_ms;
} comp_v22_everyday_bridge_frame_t;

typedef struct {
    comp_v22_everyday_bridge_selection_t selection;
    comp_v22_everyday_bridge_context_t context;
    uint8_t next_step_index;
    uint32_t submitted_frames;
    uint32_t visible_frames;
    uint32_t failed_frame_retries;
    uint32_t rejected_submissions;
    bool active;
    bool frame_outstanding;
} comp_v22_everyday_bridge_session_t;

void comp_v22_everyday_bridge_session_init(comp_v22_everyday_bridge_session_t *session);

/* Start an explicit ordinary-affect edge. The session has no product-function
 * event input, so unavailable special states cannot enter through this path. */
bool comp_v22_everyday_bridge_session_start(
    comp_v22_everyday_bridge_session_t *session,
    comp_expression_rig_emotion_t source_emotion,
    comp_v22_everyday_cue_t cue,
    const comp_v22_everyday_bridge_context_t *context);

/* Take one registered component plan. A caller must acknowledge that the
 * submitted frame became visible before a later step can be requested. */
bool comp_v22_everyday_bridge_session_take_frame(
    comp_v22_everyday_bridge_session_t *session,
    comp_v22_everyday_bridge_frame_t *out_frame,
    comp_expression_rig_plan_t *out_plan);

/* A false acknowledgement retries the exact same step. A true acknowledgement
 * permits the next stable frame or completes the selected bridge. */
bool comp_v22_everyday_bridge_session_complete_frame(
    comp_v22_everyday_bridge_session_t *session,
    bool visible);

/* Product arbitration may stop this candidate sequence without synthesizing a
 * substitute face. A later eligible event must start a new explicit bridge. */
bool comp_v22_everyday_bridge_session_cancel(comp_v22_everyday_bridge_session_t *session);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_EXPRESSION_V22_EVERYDAY_BRIDGE_SESSION_H */
