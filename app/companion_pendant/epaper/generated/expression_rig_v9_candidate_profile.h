/* Generated from docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rig-layout.json; do not hand edit. */
#ifndef COMPANION_EPAPER_EXPRESSION_RIG_V9_CANDIDATE_PROFILE_H
#define COMPANION_EPAPER_EXPRESSION_RIG_V9_CANDIDATE_PROFILE_H

#include "expression_rig_performance_score.h"

#include <stdbool.h>

#define COMP_V9_EXPRESSION_RIG_CANDIDATE_REVISION 107u
#define COMP_V9_EXPRESSION_RIG_CANDIDATE_COMPONENT_COUNT 24u
#define COMP_V9_EXPRESSION_RIG_CANDIDATE_DAILY_SCORE_COUNT 4u
#define COMP_V9_EXPRESSION_RIG_CANDIDATE_SOURCE_SHA256 "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
#define COMP_V9_EXPRESSION_RIG_CANDIDATE_PROMPT_REVISION "pet-expression-v9-anti-sly-cute-2026-07-15"
#define COMP_V9_EXPRESSION_RIG_CANDIDATE_PANEL_INITIAL_DWELL_MS 2600u
#define COMP_V9_EXPRESSION_RIG_CANDIDATE_PANEL_MINIMUM_DWELL_MS 750u
#define COMP_V9_EXPRESSION_RIG_CANDIDATE_PANEL_PARTIAL_LIMIT 255u
#define COMP_V9_EXPRESSION_RIG_CANDIDATE_PANEL_STORY_COUNT 4u
#define COMP_V9_EXPRESSION_RIG_CANDIDATE_PANEL_CONTINUOUS_REPLAY 1u

const comp_expression_rig_profile_t *comp_v9_expression_rig_candidate_profile(void);
const comp_expression_rig_performance_score_t *comp_v9_expression_rig_candidate_daily_score(
    comp_expression_rig_attention_t attention);
uint8_t comp_v9_expression_rig_candidate_daily_presentation_story_count(void);
bool comp_v9_expression_rig_candidate_daily_presentation_attention(
    uint8_t story_index,
    comp_expression_rig_attention_t *out_attention);

/* Candidate art never activates itself. A separate owner visual gate controls
 * any future runtime binding. */
bool comp_v9_expression_rig_candidate_runtime_activation_allowed(void);

#endif /* COMPANION_EPAPER_EXPRESSION_RIG_V9_CANDIDATE_PROFILE_H */
