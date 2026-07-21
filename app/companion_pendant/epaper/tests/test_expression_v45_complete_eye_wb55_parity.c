#define SPECIAL_PROFILE_HEADER "generated/expression_rig_v45_complete_eye_candidate_profile.h"
#define SPECIAL_SCORE_TYPE comp_v45_two_track_candidate_story_t
#define SPECIAL_GET_PROFILE comp_v45_two_track_candidate_profile
#define SPECIAL_ACTIVATION_ALLOWED comp_v45_two_track_candidate_runtime_activation_allowed
#define SPECIAL_SCORE_COUNT() COMP_V45_TWO_TRACK_CANDIDATE_STORY_COUNT
#define SPECIAL_GET_SCORE(index) comp_v45_two_track_candidate_story(index)
#define SPECIAL_COMPONENT_COUNT COMP_V45_TWO_TRACK_CANDIDATE_COMPONENT_COUNT
#define SPECIAL_PACK_COMPONENT_COUNT 60u
#define SPECIAL_COMPONENT_SCRATCH_BYTES COMP_V45_TWO_TRACK_CANDIDATE_MAX_MASK_BYTES
#define SPECIAL_MAX_COMPONENT_MASK_BYTES COMP_V45_TWO_TRACK_CANDIDATE_MAX_MASK_BYTES
#define SPECIAL_EXPECTED_FRAME_COUNT 93u
#define SPECIAL_PACK_LABEL "v45_special_source"
#define SPECIAL_REPORT_SCHEMA "companion.v45_complete_eye_wb55_component_parity_host.v1"
#define SPECIAL_DESCRIPTOR_IS_VALID(descriptor) \
    ((descriptor) != NULL && (descriptor)->frames != NULL && (descriptor)->frame_count > 0u && \
     (descriptor)->expression_track_index < COMP_V45_TWO_TRACK_CANDIDATE_EXPRESSION_TRACK_COUNT && \
     ((descriptor)->uses_menu_entry_track || \
      (descriptor)->functional_track_index == COMP_V45_TWO_TRACK_CANDIDATE_NO_FUNCTIONAL_TRACK || \
      (descriptor)->functional_track_index < COMP_V45_TWO_TRACK_CANDIDATE_FUNCTIONAL_TRACK_COUNT))
#define SPECIAL_BUILD_FRAME(descriptor, frame_index, out_plan) \
    comp_v45_two_track_candidate_build_story_frame((descriptor), (frame_index), NULL, (out_plan))
#define SPECIAL_FRAME_PHASE(descriptor, frame_index) \
    (((descriptor)->uses_menu_entry_track) ? \
        comp_expression_rig_score_phase_name( \
            comp_v45_two_track_candidate_menu_entry_track()->score->steps[ \
                (descriptor)->frames[(frame_index)].functional_step_index].phase) : \
     ((descriptor)->functional_track_index != COMP_V45_TWO_TRACK_CANDIDATE_NO_FUNCTIONAL_TRACK) ? \
        comp_expression_rig_score_phase_name( \
            comp_v45_two_track_candidate_functional_track((descriptor)->functional_track_index)->score->steps[ \
                (descriptor)->frames[(frame_index)].functional_step_index].phase) : \
        comp_expression_rig_score_phase_name( \
            comp_v45_two_track_candidate_expression_track((descriptor)->expression_track_index)->score->steps[ \
                (descriptor)->frames[(frame_index)].expression_step_index].phase))

#include "test_expression_special_component_parity_impl.inc"
