#ifndef COMPANION_SCREEN_COMPOSITION_H
#define COMPANION_SCREEN_COMPOSITION_H

#include "screen_lifecycle.h"

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    bool active;
    uint16_t frame_index;
    uint32_t state_hash;
    uint32_t revision;
} comp_screen_composition_track_t;

typedef struct {
    comp_screen_composition_track_t base;
    comp_screen_composition_track_t charging;
    comp_screen_composition_track_t recording;
    uint32_t revision;
} comp_screen_composition_t;

typedef struct {
    comp_screen_surface_t surface;
    comp_screen_composition_track_t base;
    comp_screen_composition_track_t charging;
    comp_screen_composition_track_t recording;
    uint32_t revision;
    bool base_visible;
    bool charging_visible;
    bool recording_visible;
} comp_screen_composition_snapshot_t;

void comp_screen_composition_init(comp_screen_composition_t *composition);
bool comp_screen_composition_set_base(
    comp_screen_composition_t *composition,
    uint16_t frame_index,
    uint32_t state_hash);
bool comp_screen_composition_set_charging(
    comp_screen_composition_t *composition,
    bool active,
    uint8_t frame_index);
bool comp_screen_composition_set_recording(
    comp_screen_composition_t *composition,
    bool active,
    uint16_t frame_index,
    uint32_t state_hash);
void comp_screen_composition_snapshot(
    const comp_screen_composition_t *composition,
    comp_screen_surface_t surface,
    comp_screen_composition_snapshot_t *snapshot);

#endif
