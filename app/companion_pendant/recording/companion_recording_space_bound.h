#ifndef COMPANION_RECORDING_SPACE_BOUND_H
#define COMPANION_RECORDING_SPACE_BOUND_H
#include "companion_segment_audio.h"
/* The producer and capacity planner must share all non-audio/drain bounds. */
#define COMP_REC_BOUND_DRAIN_PACKETS 5u
static inline uint32_t comp_recording_boundary_allowance(bool source_boundary)
{return source_boundary?32u+2u*COMP_SEG_AUDIO_DATA_BYTES:0u;}
static inline uint64_t comp_recording_required_capacity(uint32_t frames,bool source_boundary)
{return 12u+comp_recording_boundary_allowance(source_boundary)+
    ((uint64_t)frames+COMP_REC_BOUND_DRAIN_PACKETS)*COMP_SEG_AUDIO_FRAME_BYTES;}
static inline uint64_t comp_recording_required_capacity_profile(uint32_t frames,bool boundary,bool profile)
{return comp_recording_required_capacity(frames,boundary)+(profile?COMP_REC_AUDIO_PROFILE_BYTES:0u);}
#endif
