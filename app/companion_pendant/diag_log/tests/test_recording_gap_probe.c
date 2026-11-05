#include "../recording_gap_probe.h"

#include <assert.h>
#include <stdint.h>

int main(void)
{
    comp_recording_gap_probe_t probe = {0};
    comp_recording_gap_probe_event_t event = {0};

    assert(!comp_recording_gap_probe_step(&probe, 10u, 131800u, false, true, false, 10u, &event));
    assert(!probe.active);
    assert(!comp_recording_gap_probe_step(&probe, 20u, 131800u, true, true, true, 10u, &event));
    assert(!probe.active);

    assert(!comp_recording_gap_probe_step(&probe, 100u, 131800u, true, true, false, 50u, &event));
    assert(probe.active && probe.starting_frames == 50u);
    assert(!comp_recording_gap_probe_step(&probe, 1099u, 131800u, true, true, false, 149u, &event));
    assert(comp_recording_gap_probe_step(&probe, 1100u, 131800u, true, true, false, 150u, &event));
    assert(event.code == COMP_DIAG_EVT_MICROPHONE_GAP_CAPTURE_INTERVAL);
    assert(event.arg0 == 131800u && event.arg1 == 50u && event.arg2 == 150u);
    assert((event.arg3 & COMP_RECORDING_GAP_FLAGS_MASK) == COMP_RECORDING_GAP_STATE_FLAGS);
    assert((event.arg3 >> COMP_RECORDING_GAP_ELAPSED_SHIFT) == 1000u);
    assert(!comp_recording_gap_probe_step(&probe, 2100u, 131800u, true, true, false, 250u, &event));

    assert(!comp_recording_gap_probe_step(&probe, 2200u, 131800u, true, true, true, 260u, &event));
    assert(!probe.active);
    assert(!comp_recording_gap_probe_step(&probe, 2300u, 131800u, true, true, false, 260u, &event));
    assert(!comp_recording_gap_probe_step(&probe, 3300u, 131800u, true, false, false, 270u, &event));
    assert(!probe.active);

    assert(!comp_recording_gap_probe_step(&probe, 4000u, 131801u, true, true, false, 300u, &event));
    assert(!comp_recording_gap_probe_step(&probe, 5000u, 131801u, true, true, false, 300u, &event));
    assert(comp_recording_gap_probe_step(&probe, 5001u, 131801u, true, true, false, 301u, &event));
    assert(event.arg0 == 131801u && event.arg1 == 300u && event.arg2 == 301u);
    assert((event.arg3 >> COMP_RECORDING_GAP_ELAPSED_SHIFT) == 1001u);

    comp_recording_gap_probe_reset(&probe);
    assert(!comp_recording_gap_probe_step(&probe, 0xFFFFFF00u, 131802u, true, true, false, 400u, &event));
    assert(comp_recording_gap_probe_step(&probe, 0x000002E8u, 131802u, true, true, false, 401u, &event));
    assert((event.arg3 >> COMP_RECORDING_GAP_ELAPSED_SHIFT) == 1000u);

    return 0;
}
