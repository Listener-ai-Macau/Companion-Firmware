#ifndef COMPANION_EPAPER_EXPRESSION_V22_EVERYDAY_BRIDGE_ROUTER_H
#define COMPANION_EPAPER_EXPRESSION_V22_EVERYDAY_BRIDGE_ROUTER_H

#include "generated/expression_rig_v22_emotion_separation_candidate_profile.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* This candidate-only vocabulary describes ordinary affect changes. It
 * deliberately excludes product-function events such as recording, menu,
 * charging, upgrade, sleep, and error; those remain fail-closed until their
 * own source art is accepted and bound. */
typedef enum {
    COMP_V22_EVERYDAY_CUE_ATTENTION_NOVELTY = 0u,
    COMP_V22_EVERYDAY_CUE_NOVELTY_RESOLVED,
    COMP_V22_EVERYDAY_CUE_POSITIVE_RECIPROCITY,
    COMP_V22_EVERYDAY_CUE_ATTENTION_SHIFT,
    COMP_V22_EVERYDAY_CUE_SHARED_PLAY,
    COMP_V22_EVERYDAY_CUE_ENERGY_SETTLE,
    COMP_V22_EVERYDAY_CUE_AMBIGUOUS_INPUT,
    COMP_V22_EVERYDAY_CUE_AMBIGUITY_RESOLVED,
    COMP_V22_EVERYDAY_CUE_HIGH_SALIENCE,
    COMP_V22_EVERYDAY_CUE_SALIENCE_REDUCED,
    COMP_V22_EVERYDAY_CUE_COUNT,
} comp_v22_everyday_cue_t;

typedef struct {
    uint8_t bridge_index;
    comp_expression_rig_emotion_t source_emotion;
    comp_expression_rig_emotion_t target_emotion;
    const comp_v22_emotion_separation_rig_bridge_t *bridge;
} comp_v22_everyday_bridge_selection_t;

const char *comp_v22_everyday_cue_name(comp_v22_everyday_cue_t cue);

/* Select exactly one generated V22 causal edge. This does not activate a
 * runtime resource, choose a product scene, or create pixels. */
bool comp_v22_everyday_bridge_select(
    comp_expression_rig_emotion_t source_emotion,
    comp_v22_everyday_cue_t cue,
    comp_v22_everyday_bridge_selection_t *out_selection);

/* Build one registered source-component plan from a selected V22 bridge.
 * It is intentionally usable for host/browser/target-plan parity while the
 * V22 pack remains runtime inactive. */
bool comp_v22_everyday_bridge_build_step(
    const comp_v22_everyday_bridge_selection_t *selection,
    uint8_t step_index,
    const comp_expression_rig_state_t *dynamic_context,
    comp_expression_rig_plan_t *out_plan);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_EXPRESSION_V22_EVERYDAY_BRIDGE_ROUTER_H */
