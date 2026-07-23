#ifndef COMPANION_EPAPER_MOTION_COORDINATOR_H
#define COMPANION_EPAPER_MOTION_COORDINATOR_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* The first daily entry pose is committed by the presentation layer. Every
 * following automatic pose stays visible for at least this long. */
#define COMP_EPAPER_MOTION_FRAME_DWELL_MS 3000u
#define COMP_EPAPER_MOTION_STORY_REST_MS 8000u
#define COMP_EPAPER_MOTION_IDLE_TIMEOUT_MS 180000u

typedef enum {
    COMP_EPAPER_MOTION_PHASE_ENTRY = 0u,
    COMP_EPAPER_MOTION_PHASE_SUSTAIN = 1u,
    COMP_EPAPER_MOTION_PHASE_SETTLE = 2u,
} comp_epaper_motion_phase_t;

typedef enum {
    COMP_EPAPER_MOTION_CANCEL_TOUCH = 0u,
    COMP_EPAPER_MOTION_CANCEL_MENU = 1u,
    COMP_EPAPER_MOTION_CANCEL_RECORDING = 2u,
    COMP_EPAPER_MOTION_CANCEL_LOW_POWER = 3u,
    COMP_EPAPER_MOTION_CANCEL_ERROR = 4u,
    COMP_EPAPER_MOTION_CANCEL_HIGH_PRIORITY = 5u,
} comp_epaper_motion_cancel_reason_t;

typedef struct {
    uint32_t token;
    comp_epaper_motion_phase_t phase;
} comp_epaper_motion_request_t;

typedef struct {
    bool initialized;
    bool daily_awake;
    bool request_outstanding;
    comp_epaper_motion_phase_t next_phase;
    uint32_t next_request_ms;
    uint32_t idle_deadline_ms;
    uint32_t outstanding_token;
    uint32_t next_token;
    uint32_t issued_requests;
    uint32_t completed_requests;
    uint32_t failed_requests;
    uint32_t cancelled_requests;
    uint32_t stale_completion_count;
    comp_epaper_motion_cancel_reason_t last_cancel_reason;
} comp_epaper_motion_coordinator_t;

typedef struct {
    bool daily_awake;
    bool request_outstanding;
    comp_epaper_motion_phase_t next_phase;
    uint32_t next_request_ms;
    uint32_t idle_deadline_ms;
    uint32_t outstanding_token;
    uint32_t issued_requests;
    uint32_t completed_requests;
    uint32_t failed_requests;
    uint32_t cancelled_requests;
    uint32_t stale_completion_count;
    comp_epaper_motion_cancel_reason_t last_cancel_reason;
} comp_epaper_motion_snapshot_t;

void comp_epaper_motion_coordinator_init(
    comp_epaper_motion_coordinator_t *coordinator);

/* Start a complete daily story. Every phase, including entry, advances only
 * after its own panel-completion callback and dwell interval. */
void comp_epaper_motion_coordinator_enter_daily(
    comp_epaper_motion_coordinator_t *coordinator,
    uint32_t now_ms);

void comp_epaper_motion_coordinator_cancel(
    comp_epaper_motion_coordinator_t *coordinator,
    comp_epaper_motion_cancel_reason_t reason);

bool comp_epaper_motion_coordinator_take_request(
    comp_epaper_motion_coordinator_t *coordinator,
    uint32_t now_ms,
    comp_epaper_motion_request_t *out_request);

/* Only the matching panel-completion callback may advance the story. A failed
 * transaction retries the same phase after the normal dwell interval. */
bool comp_epaper_motion_coordinator_complete_request(
    comp_epaper_motion_coordinator_t *coordinator,
    uint32_t token,
    uint32_t now_ms,
    bool visible);

bool comp_epaper_motion_coordinator_idle_timeout_elapsed(
    const comp_epaper_motion_coordinator_t *coordinator,
    uint32_t now_ms);

void comp_epaper_motion_coordinator_snapshot(
    const comp_epaper_motion_coordinator_t *coordinator,
    comp_epaper_motion_snapshot_t *out_snapshot);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_MOTION_COORDINATOR_H */
