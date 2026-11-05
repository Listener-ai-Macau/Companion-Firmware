#include "screen_composition.h"

#include <string.h>

static bool set_track(comp_screen_composition_t *composition,
                      comp_screen_composition_track_t *track,
                      bool active,
                      uint16_t frame_index,
                      uint32_t state_hash)
{
    if (composition == NULL || track == NULL) {
        return false;
    }
    if (track->active == active && track->frame_index == frame_index &&
        track->state_hash == state_hash) {
        return false;
    }
    track->active = active;
    track->frame_index = frame_index;
    track->state_hash = state_hash;
    track->revision++;
    composition->revision++;
    return true;
}

void comp_screen_composition_init(comp_screen_composition_t *composition)
{
    if (composition == NULL) {
        return;
    }
    memset(composition, 0, sizeof(*composition));
    composition->revision = 1u;
}

bool comp_screen_composition_set_base(
    comp_screen_composition_t *composition,
    uint16_t frame_index,
    uint32_t state_hash)
{
    return set_track(composition,
                     composition == NULL ? NULL : &composition->base,
                     true,
                     frame_index,
                     state_hash);
}

bool comp_screen_composition_set_charging(
    comp_screen_composition_t *composition,
    bool active,
    uint8_t frame_index)
{
    return set_track(composition,
                     composition == NULL ? NULL : &composition->charging,
                     active,
                     frame_index,
                     0u);
}

bool comp_screen_composition_set_recording(
    comp_screen_composition_t *composition,
    bool active,
    uint16_t frame_index,
    uint32_t state_hash)
{
    return set_track(composition,
                     composition == NULL ? NULL : &composition->recording,
                     active,
                     frame_index,
                     state_hash);
}

void comp_screen_composition_snapshot(
    const comp_screen_composition_t *composition,
    comp_screen_surface_t surface,
    comp_screen_composition_snapshot_t *snapshot)
{
    bool home;

    if (composition == NULL || snapshot == NULL) {
        return;
    }
    home = surface == COMP_SCREEN_SURFACE_HOME;
    *snapshot = (comp_screen_composition_snapshot_t){
        .surface = surface,
        .base = composition->base,
        .charging = composition->charging,
        .recording = composition->recording,
        .revision = composition->revision,
        .base_visible = home && composition->base.active,
        .charging_visible = home && composition->charging.active,
        .recording_visible = home && composition->recording.active,
    };
}
