#define SPECIAL_PROFILE_HEADER "generated/expression_rig_v39_two_track_candidate_profile.h"
#define SPECIAL_SCORE_TYPE comp_v39_two_track_candidate_story_t
#define SPECIAL_GET_PROFILE comp_v39_two_track_candidate_profile
#define SPECIAL_ACTIVATION_ALLOWED comp_v39_two_track_candidate_runtime_activation_allowed
#define SPECIAL_SCORE_COUNT() COMP_V39_TWO_TRACK_CANDIDATE_STORY_COUNT
#define SPECIAL_GET_SCORE(index) comp_v39_two_track_candidate_story(index)
#define SPECIAL_COMPONENT_COUNT COMP_V39_TWO_TRACK_CANDIDATE_COMPONENT_COUNT
#define SPECIAL_PACK_COMPONENT_COUNT 57u
#define SPECIAL_COMPONENT_SCRATCH_BYTES COMP_V39_TWO_TRACK_CANDIDATE_MAX_MASK_BYTES
#define SPECIAL_MAX_COMPONENT_MASK_BYTES COMP_V39_TWO_TRACK_CANDIDATE_MAX_MASK_BYTES
#define SPECIAL_EXPECTED_FRAME_COUNT 38u
#define SPECIAL_PACK_LABEL "v38_special_source"
#define SPECIAL_REPORT_SCHEMA "companion.v39_two_track_wb55_component_parity_host.v1"
#define SPECIAL_DESCRIPTOR_IS_VALID(descriptor) \
    ((descriptor) != NULL && (descriptor)->frames != NULL && (descriptor)->frame_count > 0u && \
     (descriptor)->expression_track_index < COMP_V39_TWO_TRACK_CANDIDATE_EXPRESSION_TRACK_COUNT && \
     ((descriptor)->uses_menu_entry_track || (descriptor)->functional_track_index == COMP_V39_TWO_TRACK_CANDIDATE_NO_FUNCTIONAL_TRACK || \
      (descriptor)->functional_track_index < COMP_V39_TWO_TRACK_CANDIDATE_FUNCTIONAL_TRACK_COUNT))
#define SPECIAL_BUILD_FRAME(descriptor, frame_index, out_plan) \
    comp_v39_two_track_candidate_build_story_frame((descriptor), (frame_index), NULL, (out_plan))

#include "test_expression_special_component_parity_impl.inc"
