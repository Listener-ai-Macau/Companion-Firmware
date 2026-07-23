#include "motion_coordinator.h"

#include <string.h>

static bool motion_time_reached(uint32_t now_ms, uint32_t deadline_ms)
{
    return (int32_t)(now_ms - deadline_ms) >= 0;
}

static uint32_t motion_next_token(comp_epaper_motion_coordinator_t *coordinator)
{
    uint32_t token = coordinator->next_token++;

    if (token == 0u) {
        token = coordinator->next_token++;
    }
    if (coordinator->next_token == 0u) {
        coordinator->next_token = 1u;
    }
    return token;
}

static void motion_schedule_next(comp_epaper_motion_coordinator_t *coordinator,
                                 uint32_t now_ms)
{
    switch (coordinator->next_phase) {
    case COMP_EPAPER_MOTION_PHASE_ENTRY:
        coordinator->next_phase = COMP_EPAPER_MOTION_PHASE_SUSTAIN;
        coordinator->next_request_ms = now_ms + COMP_EPAPER_MOTION_FRAME_DWELL_MS;
        break;
    case COMP_EPAPER_MOTION_PHASE_SUSTAIN:
        coordinator->next_phase = COMP_EPAPER_MOTION_PHASE_SETTLE;
        coordinator->next_request_ms = now_ms + COMP_EPAPER_MOTION_FRAME_DWELL_MS;
        break;
    case COMP_EPAPER_MOTION_PHASE_SETTLE:
    default:
        coordinator->next_phase = COMP_EPAPER_MOTION_PHASE_ENTRY;
        coordinator->next_request_ms = now_ms + COMP_EPAPER_MOTION_STORY_REST_MS;
        break;
    }
}

void comp_epaper_motion_coordinator_init(
    comp_epaper_motion_coordinator_t *coordinator)
{
    if (coordinator == NULL) {
        return;
    }
    memset(coordinator, 0, sizeof(*coordinator));
    coordinator->initialized = true;
    coordinator->next_token = 1u;
    coordinator->next_phase = COMP_EPAPER_MOTION_PHASE_ENTRY;
    coordinator->last_cancel_reason = COMP_EPAPER_MOTION_CANCEL_HIGH_PRIORITY;
}

void comp_epaper_motion_coordinator_enter_daily(
    comp_epaper_motion_coordinator_t *coordinator,
    uint32_t now_ms)
{
    if (coordinator == NULL || !coordinator->initialized) {
        return;
    }

    coordinator->daily_awake = true;
    coordinator->request_outstanding = false;
    coordinator->outstanding_token = 0u;
    coordinator->next_phase = COMP_EPAPER_MOTION_PHASE_ENTRY;
    coordinator->next_request_ms = now_ms;
    coordinator->idle_deadline_ms = now_ms + COMP_EPAPER_MOTION_IDLE_TIMEOUT_MS;
}

void comp_epaper_motion_coordinator_cancel(
    comp_epaper_motion_coordinator_t *coordinator,
    comp_epaper_motion_cancel_reason_t reason)
{
    if (coordinator == NULL || !coordinator->initialized) {
        return;
    }

    if (coordinator->daily_awake || coordinator->request_outstanding) {
        coordinator->cancelled_requests++;
    }
    coordinator->daily_awake = false;
    coordinator->request_outstanding = false;
    coordinator->outstanding_token = 0u;
    coordinator->next_phase = COMP_EPAPER_MOTION_PHASE_ENTRY;
    coordinator->next_request_ms = 0u;
    coordinator->idle_deadline_ms = 0u;
    coordinator->last_cancel_reason = reason;
}

bool comp_epaper_motion_coordinator_take_request(
    comp_epaper_motion_coordinator_t *coordinator,
    uint32_t now_ms,
    comp_epaper_motion_request_t *out_request)
{
    uint32_t token;

    if (coordinator == NULL || out_request == NULL || !coordinator->initialized ||
        !coordinator->daily_awake || coordinator->request_outstanding ||
        comp_epaper_motion_coordinator_idle_timeout_elapsed(coordinator, now_ms) ||
        !motion_time_reached(now_ms, coordinator->next_request_ms)) {
        return false;
    }

    token = motion_next_token(coordinator);
    coordinator->request_outstanding = true;
    coordinator->outstanding_token = token;
    coordinator->issued_requests++;
    *out_request = (comp_epaper_motion_request_t){
        .token = token,
        .phase = coordinator->next_phase,
    };
    return true;
}

bool comp_epaper_motion_coordinator_complete_request(
    comp_epaper_motion_coordinator_t *coordinator,
    uint32_t token,
    uint32_t now_ms,
    bool visible)
{
    if (coordinator == NULL || !coordinator->initialized ||
        !coordinator->request_outstanding ||
        coordinator->outstanding_token != token) {
        if (coordinator != NULL && coordinator->initialized) {
            coordinator->stale_completion_count++;
        }
        return false;
    }

    coordinator->request_outstanding = false;
    coordinator->outstanding_token = 0u;
    if (!coordinator->daily_awake) {
        coordinator->stale_completion_count++;
        return false;
    }
    if (visible) {
        coordinator->completed_requests++;
        motion_schedule_next(coordinator, now_ms);
    } else {
        coordinator->failed_requests++;
        coordinator->next_request_ms = now_ms + COMP_EPAPER_MOTION_FRAME_DWELL_MS;
    }
    return true;
}

bool comp_epaper_motion_coordinator_idle_timeout_elapsed(
    const comp_epaper_motion_coordinator_t *coordinator,
    uint32_t now_ms)
{
    return coordinator != NULL && coordinator->initialized &&
           coordinator->daily_awake &&
           motion_time_reached(now_ms, coordinator->idle_deadline_ms);
}

void comp_epaper_motion_coordinator_snapshot(
    const comp_epaper_motion_coordinator_t *coordinator,
    comp_epaper_motion_snapshot_t *out_snapshot)
{
    if (out_snapshot == NULL) {
        return;
    }
    memset(out_snapshot, 0, sizeof(*out_snapshot));
    if (coordinator == NULL) {
        return;
    }
    *out_snapshot = (comp_epaper_motion_snapshot_t){
        .daily_awake = coordinator->daily_awake,
        .request_outstanding = coordinator->request_outstanding,
        .next_phase = coordinator->next_phase,
        .next_request_ms = coordinator->next_request_ms,
        .idle_deadline_ms = coordinator->idle_deadline_ms,
        .outstanding_token = coordinator->outstanding_token,
        .issued_requests = coordinator->issued_requests,
        .completed_requests = coordinator->completed_requests,
        .failed_requests = coordinator->failed_requests,
        .cancelled_requests = coordinator->cancelled_requests,
        .stale_completion_count = coordinator->stale_completion_count,
        .last_cancel_reason = coordinator->last_cancel_reason,
    };
}
