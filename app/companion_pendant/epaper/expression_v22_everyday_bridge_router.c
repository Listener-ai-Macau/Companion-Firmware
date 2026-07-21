#include "expression_v22_everyday_bridge_router.h"

#include <string.h>

typedef struct {
    comp_v22_everyday_cue_t cue;
    comp_expression_rig_emotion_t source_emotion;
    comp_expression_rig_emotion_t target_emotion;
    const char *bridge_name;
    const char *source_name;
    const char *target_name;
    const char *event_name;
} expected_bridge_t;

static const char *const k_cue_names[] = {
    "attention_novelty",
    "novelty_resolved",
    "positive_reciprocity",
    "attention_shift",
    "shared_play",
    "energy_settle",
    "ambiguous_input",
    "ambiguity_resolved",
    "high_salience",
    "salience_reduced",
};

static const expected_bridge_t k_expected_bridges[] = {
    {COMP_V22_EVERYDAY_CUE_ATTENTION_NOVELTY, COMP_EXPRESSION_RIG_EMOTION_CALM,
     COMP_EXPRESSION_RIG_EMOTION_CURIOUS, "calm__curious", "calm", "curious", "attention_novelty"},
    {COMP_V22_EVERYDAY_CUE_NOVELTY_RESOLVED, COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
     COMP_EXPRESSION_RIG_EMOTION_CALM, "curious__calm", "curious", "calm", "novelty_resolved"},
    {COMP_V22_EVERYDAY_CUE_POSITIVE_RECIPROCITY, COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
     COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, "curious__warm", "curious", "warm", "positive_reciprocity"},
    {COMP_V22_EVERYDAY_CUE_ATTENTION_SHIFT, COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
     COMP_EXPRESSION_RIG_EMOTION_CURIOUS, "warm__curious", "warm", "curious", "attention_shift"},
    {COMP_V22_EVERYDAY_CUE_SHARED_PLAY, COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
     COMP_EXPRESSION_RIG_EMOTION_PLAYFUL, "warm__playful", "warm", "playful", "shared_play"},
    {COMP_V22_EVERYDAY_CUE_ENERGY_SETTLE, COMP_EXPRESSION_RIG_EMOTION_PLAYFUL,
     COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE, "playful__warm", "playful", "warm", "energy_settle"},
    {COMP_V22_EVERYDAY_CUE_AMBIGUOUS_INPUT, COMP_EXPRESSION_RIG_EMOTION_CALM,
     COMP_EXPRESSION_RIG_EMOTION_PUZZLED, "calm__puzzled", "calm", "puzzled", "ambiguous_input"},
    {COMP_V22_EVERYDAY_CUE_AMBIGUITY_RESOLVED, COMP_EXPRESSION_RIG_EMOTION_PUZZLED,
     COMP_EXPRESSION_RIG_EMOTION_CALM, "puzzled__calm", "puzzled", "calm", "ambiguity_resolved"},
    {COMP_V22_EVERYDAY_CUE_HIGH_SALIENCE, COMP_EXPRESSION_RIG_EMOTION_PUZZLED,
     COMP_EXPRESSION_RIG_EMOTION_ALERT, "puzzled__alert", "puzzled", "alert", "high_salience"},
    {COMP_V22_EVERYDAY_CUE_SALIENCE_REDUCED, COMP_EXPRESSION_RIG_EMOTION_ALERT,
     COMP_EXPRESSION_RIG_EMOTION_PUZZLED, "alert__puzzled", "alert", "puzzled", "salience_reduced"},
};

const char *comp_v22_everyday_cue_name(comp_v22_everyday_cue_t cue)
{
    if (cue >= COMP_V22_EVERYDAY_CUE_COUNT) {
        return "invalid";
    }
    return k_cue_names[cue];
}

static bool bridge_matches(const comp_v22_emotion_separation_rig_bridge_t *bridge,
                           const expected_bridge_t *expected)
{
    return bridge != NULL && expected != NULL && bridge->name != NULL &&
           bridge->source_emotion != NULL && bridge->target_emotion != NULL &&
           bridge->event_name != NULL && bridge->score != NULL && bridge->frames != NULL &&
           bridge->frame_count > 0u && bridge->score->step_count == bridge->frame_count &&
           strcmp(bridge->name, expected->bridge_name) == 0 &&
           strcmp(bridge->source_emotion, expected->source_name) == 0 &&
           strcmp(bridge->target_emotion, expected->target_name) == 0 &&
           strcmp(bridge->event_name, expected->event_name) == 0;
}

bool comp_v22_everyday_bridge_select(
    comp_expression_rig_emotion_t source_emotion,
    comp_v22_everyday_cue_t cue,
    comp_v22_everyday_bridge_selection_t *out_selection)
{
    uint8_t bridge_index;
    size_t expected_index;

    if (out_selection == NULL || source_emotion >= COMP_EXPRESSION_RIG_EMOTION_COUNT ||
        cue >= COMP_V22_EVERYDAY_CUE_COUNT) {
        return false;
    }
    for (expected_index = 0u;
         expected_index < sizeof(k_expected_bridges) / sizeof(k_expected_bridges[0]);
         ++expected_index) {
        const expected_bridge_t *expected = &k_expected_bridges[expected_index];

        if (expected->cue != cue || expected->source_emotion != source_emotion) {
            continue;
        }
        for (bridge_index = 0u;
             bridge_index < comp_v22_emotion_separation_rig_candidate_bridge_count();
             ++bridge_index) {
            const comp_v22_emotion_separation_rig_bridge_t *bridge =
                comp_v22_emotion_separation_rig_candidate_bridge(bridge_index);

            if (bridge_matches(bridge, expected)) {
                *out_selection = (comp_v22_everyday_bridge_selection_t){
                    .bridge_index = bridge_index,
                    .source_emotion = expected->source_emotion,
                    .target_emotion = expected->target_emotion,
                    .bridge = bridge,
                };
                return true;
            }
        }
        return false;
    }
    return false;
}

bool comp_v22_everyday_bridge_build_step(
    const comp_v22_everyday_bridge_selection_t *selection,
    uint8_t step_index,
    const comp_expression_rig_state_t *dynamic_context,
    comp_expression_rig_plan_t *out_plan)
{
    const comp_v22_emotion_separation_rig_bridge_t *bridge;

    if (selection == NULL || out_plan == NULL || selection->bridge == NULL ||
        selection->bridge_index >= comp_v22_emotion_separation_rig_candidate_bridge_count()) {
        return false;
    }
    bridge = comp_v22_emotion_separation_rig_candidate_bridge(selection->bridge_index);
    if (bridge != selection->bridge || bridge->score == NULL || bridge->frames == NULL ||
        bridge->frame_count == 0u || bridge->score->step_count != bridge->frame_count ||
        step_index >= bridge->frame_count) {
        return false;
    }
    return comp_expression_rig_build_registered_score_step(
        comp_v22_emotion_separation_rig_candidate_profile(), bridge->score, step_index,
        dynamic_context, out_plan);
}
