#ifndef COMPANION_RECORDING_GEOMETRY_H
#define COMPANION_RECORDING_GEOMETRY_H

#include "companion_recording_space_bound.h"

/* Keep the sealed horizon close to two minutes while fitting the actual
 * resource-dependent arena and 64-entry directory. No new partition or RAM.
 * Every candidate retains the existing header/five-frame drain bound. */
#define COMP_RECORDING_GEOMETRY_MAX_FRAMES 6400u
typedef struct {
    uint32_t extent_bytes;
    uint32_t segment_frames;
} comp_recording_geometry_t;

static inline bool comp_recording_geometry_plan_profile(uint32_t arena_bytes,
    uint32_t max_entries,bool profile,comp_recording_geometry_t *out)
{
    if (!out || !max_entries || max_entries > COMP_SEGMENT_CAPACITY ||
        arena_bytes < 4096u || arena_bytes % 4096u) return false;
    const uint32_t maximum_payload = (uint32_t)comp_recording_required_capacity_profile(
        COMP_RECORDING_GEOMETRY_MAX_FRAMES,true,profile);
    const uint32_t maximum_extent = (((maximum_payload + COMP_SEG_AUDIO_DATA_BYTES - 1u) /
        COMP_SEG_AUDIO_DATA_BYTES + 1u) * 256u + 4095u) / 4096u * 4096u;
    comp_recording_geometry_t best = {0};
    uint32_t best_frames = 0u, best_distance = UINT32_MAX;
    for (uint32_t extent = 4096u; extent <= maximum_extent && extent <= arena_bytes;
         extent += 4096u) {
        uint32_t capacity = comp_segment_audio_capacity(extent);
        const uint32_t overhead=12u+comp_recording_boundary_allowance(true)+(profile?COMP_REC_AUDIO_PROFILE_BYTES:0u);
        if (capacity <= overhead + COMP_REC_BOUND_DRAIN_PACKETS * COMP_SEG_AUDIO_FRAME_BYTES) continue;
        uint32_t frames = (capacity - overhead) / COMP_SEG_AUDIO_FRAME_BYTES - COMP_REC_BOUND_DRAIN_PACKETS;
        if (frames > COMP_RECORDING_GEOMETRY_MAX_FRAMES)
            frames = COMP_RECORDING_GEOMETRY_MAX_FRAMES;
        uint32_t slots = arena_bytes / extent;
        if (slots > max_entries) slots = max_entries;
        uint32_t total_frames = slots * frames;
        uint32_t distance = frames > 6000u ? frames - 6000u : 6000u - frames;
        if (total_frames > best_frames ||
            (total_frames == best_frames && distance < best_distance)) {
            best = (comp_recording_geometry_t){extent, frames};
            best_frames = total_frames;
            best_distance = distance;
        }
    }
    if (!best_frames) return false;
    *out = best;
    return true;
}

/* Existing callers retain the exact original planning and schema1..4 bound. */
static inline bool comp_recording_geometry_plan(uint32_t arena_bytes,uint32_t max_entries,comp_recording_geometry_t *out)
{return comp_recording_geometry_plan_profile(arena_bytes,max_entries,false,out);}
#endif
