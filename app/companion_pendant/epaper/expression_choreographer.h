#ifndef COMPANION_EPAPER_EXPRESSION_CHOREOGRAPHER_H
#define COMPANION_EPAPER_EXPRESSION_CHOREOGRAPHER_H

#include "expression_rig.h"
#include "expression_rig_performance_score.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    COMP_EXPRESSION_RIG_EVENT_DAILY_AUTO = 0u,
    COMP_EXPRESSION_RIG_EVENT_TOUCH_TAP,
    COMP_EXPRESSION_RIG_EVENT_TOUCH_SWIPE,
    COMP_EXPRESSION_RIG_EVENT_RECORDING_ACTIVE,
    COMP_EXPRESSION_RIG_EVENT_MENU_HOLD,
    COMP_EXPRESSION_RIG_EVENT_SLEEP,
    COMP_EXPRESSION_RIG_EVENT_WAKE,
    COMP_EXPRESSION_RIG_EVENT_CHARGING,
    COMP_EXPRESSION_RIG_EVENT_ERROR,
    COMP_EXPRESSION_RIG_EVENT_UPGRADE_ACTIVE,
    COMP_EXPRESSION_RIG_EVENT_COUNT,
} comp_expression_rig_event_t;

typedef struct {
    comp_expression_rig_event_t event;
    comp_expression_rig_attention_t attention;
    comp_expression_rig_energy_t energy;
    uint8_t interaction_memory;
    /* Retained for replay compatibility only. It must not select an emotion,
     * gaze direction, component response, or a timing beat. */
    uint32_t seed;
    comp_expression_rig_phase_t phase;
    comp_expression_rig_emotion_t requested_emotion;
    bool has_requested_emotion;
} comp_expression_rig_choreography_input_t;

/* Persistent affect is deliberately smaller than the visible expression
 * vocabulary.  It records the continuously evolving reason for a baseline;
 * the renderer still receives only approved, source-derived Rig components. */
typedef struct {
    int8_t valence; /* -2 (unpleasant) through +2 (pleasant). */
    uint8_t arousal; /* 0 (resting) through 3 (highly engaged). */
    uint8_t affinity; /* 0 through 2, informed by interaction_memory. */
    comp_expression_rig_emotion_t baseline;
} comp_expression_rig_affect_state_t;

typedef enum {
    COMP_EXPRESSION_RIG_INTENT_PRESENCE = 0u,
    COMP_EXPRESSION_RIG_INTENT_NOTICE,
    COMP_EXPRESSION_RIG_INTENT_CURIOUS_RESPONSE,
    COMP_EXPRESSION_RIG_INTENT_WARM_RESPONSE,
    COMP_EXPRESSION_RIG_INTENT_PLAYFUL_RESPONSE,
    COMP_EXPRESSION_RIG_INTENT_PROCESSING,
    COMP_EXPRESSION_RIG_INTENT_TASK_FOCUS,
    COMP_EXPRESSION_RIG_INTENT_ALERT_RESPONSE,
    COMP_EXPRESSION_RIG_INTENT_COUNT,
} comp_expression_rig_intent_t;

typedef enum {
    COMP_EXPRESSION_RIG_INTENT_REASON_IDLE_PRESENCE = 0u,
    COMP_EXPRESSION_RIG_INTENT_REASON_EVENT_APPRAISAL,
    COMP_EXPRESSION_RIG_INTENT_REASON_EXPLICIT_REQUEST,
    COMP_EXPRESSION_RIG_INTENT_REASON_ACTIVE_INTENT_HOLD,
    COMP_EXPRESSION_RIG_INTENT_REASON_COUNT,
} comp_expression_rig_intent_reason_t;

/* This is the persistent selection state. It stores behavior intent rather
 * than rendered pixels; the Rig remains the only component-plan authority. */
typedef struct {
    comp_expression_rig_affect_state_t affect;
    comp_expression_rig_intent_t active_intent;
    uint8_t remaining_hold_steps;
} comp_expression_rig_behavior_state_t;

#define COMP_EXPRESSION_RIG_MIN_INTENT_HOLD_STEPS 2u

#define COMP_EXPRESSION_RIG_MAX_EMOTION_ROUTE 12u

typedef struct {
    comp_expression_rig_emotion_t emotions[COMP_EXPRESSION_RIG_MAX_EMOTION_ROUTE];
    uint8_t count;
} comp_expression_rig_emotion_route_t;

typedef struct {
    comp_expression_rig_intent_t intent;
    comp_expression_rig_intent_reason_t reason;
    comp_expression_rig_emotion_t target_emotion;
    comp_expression_rig_attention_t target_attention;
    uint8_t event_priority;
    bool cancels_active_intent;
    comp_expression_rig_emotion_route_t route;
} comp_expression_rig_behavior_decision_t;

const char *comp_expression_rig_event_name(comp_expression_rig_event_t event);

bool comp_expression_rig_affect_is_valid(const comp_expression_rig_affect_state_t *affect);

const char *comp_expression_rig_intent_name(comp_expression_rig_intent_t intent);

const char *comp_expression_rig_intent_reason_name(comp_expression_rig_intent_reason_t reason);

bool comp_expression_rig_behavior_state_is_valid(
    const comp_expression_rig_behavior_state_t *state);

/* Resolve exactly one causal behavior intent. Daily idle keeps the selected
 * baseline and can only consume a recorded hold; it never picks a new emotion.
 * A later event may preempt an active intent only at a higher priority. */
bool comp_expression_rig_resolve_behavior(
    const comp_expression_rig_behavior_state_t *current,
    const comp_expression_rig_choreography_input_t *input,
    comp_expression_rig_behavior_state_t *out_next,
    comp_expression_rig_behavior_decision_t *out_decision);

/* Apply one product event to the persistent affect core. This has no pixel
 * output and is deterministic for a given prior core and choreography input. */
bool comp_expression_rig_affect_update(
    const comp_expression_rig_affect_state_t *current,
    const comp_expression_rig_choreography_input_t *input,
    comp_expression_rig_affect_state_t *out_next);

/* Resolve the next stable expression family from affect plus product context.
 * It can return a family whose scene is currently fail-closed; callers must
 * still ask the registered profile before producing a visual plan. */
bool comp_expression_rig_affect_target_emotion(
    const comp_expression_rig_affect_state_t *affect,
    const comp_expression_rig_choreography_input_t *input,
    comp_expression_rig_emotion_t *out_emotion);

/* Directed graph contract for emotion changes. A false result means that a
 * direct step is not causally legal; callers must obtain the deterministic
 * route instead of jumping between unrelated face baselines. */
bool comp_expression_rig_emotion_transition_allowed(
    comp_expression_rig_emotion_t from,
    comp_expression_rig_emotion_t to);

bool comp_expression_rig_emotion_transition_route(
    comp_expression_rig_emotion_t from,
    comp_expression_rig_emotion_t to,
    comp_expression_rig_emotion_route_t *out_route);

/* Convert product context into one legal Rig state. The requested event scene
 * must be backed by a registered component in the active profile; otherwise it
 * fails closed instead of borrowing a daily face. Menu, Recording and Upgrade
 * additionally remain fail-closed until their separately accepted special-
 * expression source poses are bound, even if an audit profile still registers
 * an older pose. When has_requested_emotion is true, attention is explicit,
 * including CENTER. */
bool comp_expression_rig_choreograph(
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_choreography_input_t *input,
    comp_expression_rig_state_t *out_state);

/* Convenience wrapper for callers that need the component plan immediately.
 * It still performs no drawing and returns only registered component ids plus
 * their legal offsets. */
bool comp_expression_rig_choreograph_plan(
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_choreography_input_t *input,
    comp_expression_rig_plan_t *out_plan);

/* Daily-only bridge from product context to one generated component score
 * step. The score is supplied by the versioned candidate profile; charging,
 * error and non-daily events remain outside this path and fail closed. */
bool comp_expression_rig_choreograph_daily_score_plan(
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_choreography_input_t *input,
    const comp_expression_rig_performance_score_t *score,
    uint8_t step_index,
    comp_expression_rig_plan_t *out_plan);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_EXPRESSION_CHOREOGRAPHER_H */
