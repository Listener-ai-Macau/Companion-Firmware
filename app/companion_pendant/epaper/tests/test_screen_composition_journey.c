#include "screen_composition.h"

#include <assert.h>
#include <stdio.h>

int main(void)
{
    comp_screen_composition_t composition;
    comp_screen_composition_snapshot_t snapshot;
    uint32_t charging_revision;
    uint32_t recording_revision;

    comp_screen_composition_init(&composition);
    comp_screen_composition_snapshot(
        &composition, COMP_SCREEN_SURFACE_HOME, &snapshot);
    assert(!snapshot.base_visible && !snapshot.charging_visible &&
           !snapshot.recording_visible);

    assert(comp_screen_composition_set_base(
        &composition, 145u, 0x10203040u));
    comp_screen_composition_snapshot(
        &composition, COMP_SCREEN_SURFACE_HOME, &snapshot);
    assert(snapshot.base_visible && snapshot.base.frame_index == 145u);

    assert(comp_screen_composition_set_charging(&composition, true, 0u));
    charging_revision = composition.charging.revision;
    assert(comp_screen_composition_set_recording(
        &composition, true, 701u, 0xAABBCCDDu));
    recording_revision = composition.recording.revision;
    assert(composition.charging.revision == charging_revision);

    assert(comp_screen_composition_set_charging(&composition, true, 1u));
    assert(composition.recording.revision == recording_revision);
    comp_screen_composition_snapshot(
        &composition, COMP_SCREEN_SURFACE_HOME, &snapshot);
    assert(snapshot.charging_visible && snapshot.recording_visible);
    assert(snapshot.charging.frame_index == 1u);
    assert(snapshot.recording.frame_index == 701u);

    comp_screen_composition_snapshot(
        &composition, COMP_SCREEN_SURFACE_MENU, &snapshot);
    assert(!snapshot.base_visible && !snapshot.charging_visible &&
           !snapshot.recording_visible);
    assert(snapshot.base.active && snapshot.base.frame_index == 145u);
    assert(snapshot.charging.active && snapshot.recording.active);
    comp_screen_composition_snapshot(
        &composition, COMP_SCREEN_SURFACE_LOW_POWER, &snapshot);
    assert(!snapshot.charging_visible && !snapshot.recording_visible);
    assert(snapshot.charging.active && snapshot.recording.active);

    comp_screen_composition_snapshot(
        &composition, COMP_SCREEN_SURFACE_HOME, &snapshot);
    assert(snapshot.base_visible && snapshot.charging_visible &&
           snapshot.recording_visible);
    assert(comp_screen_composition_set_recording(
        &composition, false, 701u, 0xAABBCCDDu));
    assert(composition.charging.revision == charging_revision + 1u);
    comp_screen_composition_snapshot(
        &composition, COMP_SCREEN_SURFACE_HOME, &snapshot);
    assert(snapshot.charging_visible && !snapshot.recording_visible);
    assert(!comp_screen_composition_set_charging(&composition, true, 1u));

    puts("PASS: screen composition keeps the committed base, charging, and "
         "recording independent, preserves hidden state across lifecycle "
         "surfaces, and ignores idempotent updates.");
    return 0;
}
