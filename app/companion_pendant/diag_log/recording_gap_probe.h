#ifndef COMPANION_RECORDING_GAP_PROBE_H
#define COMPANION_RECORDING_GAP_PROBE_H

#include "diag_log_events.h"

#include <stdbool.h>
#include <stdint.h>

#define COMP_RECORDING_GAP_MIN_INTERVAL_MS 1000u
#define COMP_RECORDING_GAP_STATE_FLAGS 0x0Fu
#define COMP_RECORDING_GAP_FLAGS_MASK 0x0Fu
#define COMP_RECORDING_GAP_ELAPSED_SHIFT 4u

typedef struct {
    uint32_t recording_id;
    uint32_t started_ms;
    uint32_t starting_frames;
    bool active;
    bool event_recorded;
} comp_recording_gap_probe_t;

typedef struct {
    uint16_t code;
    uint32_t arg0;
    uint32_t arg1;
    uint32_t arg2;
    uint32_t arg3;
} comp_recording_gap_probe_event_t;

/* Emit one bounded RAM event only after the normal recording, microphone, and
 * disconnected-link predicates stayed true across the sampling interval.
 * Args: recording_id, starting_frames, ending_frames,
 *       (elapsed_ms << 4) | 0x0f.
 * The low flag nibble means mic-running/link-down at both endpoints. The
 * caller feeds this function on every main-loop pass, so any observed pause,
 * stop, reconnect, or recording switch cancels the interval. */
static inline void comp_recording_gap_probe_reset(comp_recording_gap_probe_t *probe)
{
    if (!probe) return;
    probe->recording_id = 0u;
    probe->started_ms = 0u;
    probe->starting_frames = 0u;
    probe->active = false;
    probe->event_recorded = false;
}

static inline bool comp_recording_gap_probe_step(
    comp_recording_gap_probe_t *probe,
    uint32_t now_ms,
    uint32_t recording_id,
    bool recording_active,
    bool microphone_running,
    bool ble_linked,
    uint32_t processed_frames,
    comp_recording_gap_probe_event_t *event)
{
    if (!probe || !event) return false;

    if (recording_id == 0u || !recording_active || !microphone_running || ble_linked) {
        comp_recording_gap_probe_reset(probe);
        return false;
    }

    if (!probe->active || probe->recording_id != recording_id) {
        probe->recording_id = recording_id;
        probe->started_ms = now_ms;
        probe->starting_frames = processed_frames;
        probe->active = true;
        probe->event_recorded = false;
        return false;
    }

    if (probe->event_recorded) return false;

    const uint32_t elapsed_ms = now_ms - probe->started_ms;
    if (elapsed_ms < COMP_RECORDING_GAP_MIN_INTERVAL_MS ||
        processed_frames <= probe->starting_frames) {
        return false;
    }

    uint32_t bounded_elapsed = elapsed_ms;
    if (bounded_elapsed > (UINT32_MAX >> COMP_RECORDING_GAP_ELAPSED_SHIFT))
        bounded_elapsed = UINT32_MAX >> COMP_RECORDING_GAP_ELAPSED_SHIFT;

    event->code = COMP_DIAG_EVT_MICROPHONE_GAP_CAPTURE_INTERVAL;
    event->arg0 = recording_id;
    event->arg1 = probe->starting_frames;
    event->arg2 = processed_frames;
    event->arg3 = (bounded_elapsed << COMP_RECORDING_GAP_ELAPSED_SHIFT) |
                  COMP_RECORDING_GAP_STATE_FLAGS;
    probe->event_recorded = true;
    return true;
}

#endif
