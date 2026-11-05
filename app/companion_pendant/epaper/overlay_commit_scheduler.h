#ifndef COMPANION_EPAPER_OVERLAY_COMMIT_SCHEDULER_H
#define COMPANION_EPAPER_OVERLAY_COMMIT_SCHEDULER_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    COMP_EPAPER_OVERLAY_COMMIT_INACTIVE = 0,
    COMP_EPAPER_OVERLAY_COMMIT_READY = 1,
    COMP_EPAPER_OVERLAY_COMMIT_IN_FLIGHT = 2,
} comp_epaper_overlay_commit_state_t;

typedef struct {
    comp_epaper_overlay_commit_state_t state;
    uint32_t in_flight_request_id;
    uint32_t dispatched_ms;
    uint32_t last_visible_ms;
    uint32_t dispatch_count;
    uint32_t visible_commit_count;
    uint32_t failed_commit_count;
    uint32_t last_visible_to_dispatch_ms;
    uint8_t has_visible_commit;
    uint8_t candidate_prepared;
    uint8_t candidate_advanced;
} comp_epaper_overlay_commit_scheduler_t;

typedef struct {
    uint32_t request_id;
    uint32_t request_to_visible_ms;
    uint32_t visible_to_dispatch_ms;
    uint8_t visible;
    uint8_t candidate_advanced;
} comp_epaper_overlay_commit_report_t;

void comp_epaper_overlay_commit_scheduler_init(
    comp_epaper_overlay_commit_scheduler_t *scheduler);
bool comp_epaper_overlay_commit_scheduler_activate(
    comp_epaper_overlay_commit_scheduler_t *scheduler);
void comp_epaper_overlay_commit_scheduler_stop(
    comp_epaper_overlay_commit_scheduler_t *scheduler);
bool comp_epaper_overlay_commit_scheduler_prepare(
    comp_epaper_overlay_commit_scheduler_t *scheduler,
    bool candidate_advanced);
bool comp_epaper_overlay_commit_scheduler_mark_dispatched(
    comp_epaper_overlay_commit_scheduler_t *scheduler,
    uint32_t request_id,
    uint32_t dispatched_ms);
bool comp_epaper_overlay_commit_scheduler_complete(
    comp_epaper_overlay_commit_scheduler_t *scheduler,
    uint32_t request_id,
    bool visible,
    uint32_t completed_ms,
    comp_epaper_overlay_commit_report_t *report);
bool comp_epaper_overlay_commit_scheduler_active(
    const comp_epaper_overlay_commit_scheduler_t *scheduler);
bool comp_epaper_overlay_commit_scheduler_ready(
    const comp_epaper_overlay_commit_scheduler_t *scheduler);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_OVERLAY_COMMIT_SCHEDULER_H */
