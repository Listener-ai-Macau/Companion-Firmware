#include "overlay_commit_scheduler.h"

#include <string.h>

void comp_epaper_overlay_commit_scheduler_init(
    comp_epaper_overlay_commit_scheduler_t *scheduler)
{
    if (scheduler == NULL) {
        return;
    }
    memset(scheduler, 0, sizeof(*scheduler));
}

bool comp_epaper_overlay_commit_scheduler_activate(
    comp_epaper_overlay_commit_scheduler_t *scheduler)
{
    if (scheduler == NULL ||
        scheduler->state != COMP_EPAPER_OVERLAY_COMMIT_INACTIVE) {
        return false;
    }
    scheduler->state = COMP_EPAPER_OVERLAY_COMMIT_READY;
    scheduler->candidate_prepared = 0u;
    scheduler->candidate_advanced = 0u;
    scheduler->dispatched_ms = 0u;
    scheduler->last_visible_ms = 0u;
    scheduler->last_visible_to_dispatch_ms = 0u;
    scheduler->has_visible_commit = 0u;
    return true;
}

void comp_epaper_overlay_commit_scheduler_stop(
    comp_epaper_overlay_commit_scheduler_t *scheduler)
{
    if (scheduler == NULL) {
        return;
    }
    scheduler->state = COMP_EPAPER_OVERLAY_COMMIT_INACTIVE;
    scheduler->in_flight_request_id = 0u;
    scheduler->candidate_prepared = 0u;
    scheduler->candidate_advanced = 0u;
}

bool comp_epaper_overlay_commit_scheduler_prepare(
    comp_epaper_overlay_commit_scheduler_t *scheduler,
    bool candidate_advanced)
{
    if (scheduler == NULL ||
        scheduler->state != COMP_EPAPER_OVERLAY_COMMIT_READY) {
        return false;
    }
    scheduler->candidate_prepared = 1u;
    scheduler->candidate_advanced = candidate_advanced ? 1u : 0u;
    return true;
}

bool comp_epaper_overlay_commit_scheduler_mark_dispatched(
    comp_epaper_overlay_commit_scheduler_t *scheduler,
    uint32_t request_id,
    uint32_t dispatched_ms)
{
    if (scheduler == NULL || request_id == 0u ||
        scheduler->state != COMP_EPAPER_OVERLAY_COMMIT_READY ||
        scheduler->candidate_prepared == 0u) {
        return false;
    }
    scheduler->last_visible_to_dispatch_ms =
        scheduler->has_visible_commit != 0u
            ? dispatched_ms - scheduler->last_visible_ms
            : 0u;
    scheduler->state = COMP_EPAPER_OVERLAY_COMMIT_IN_FLIGHT;
    scheduler->in_flight_request_id = request_id;
    scheduler->dispatched_ms = dispatched_ms;
    scheduler->dispatch_count++;
    return true;
}

bool comp_epaper_overlay_commit_scheduler_complete(
    comp_epaper_overlay_commit_scheduler_t *scheduler,
    uint32_t request_id,
    bool visible,
    uint32_t completed_ms,
    comp_epaper_overlay_commit_report_t *report)
{
    uint8_t candidate_advanced;

    if (scheduler == NULL || request_id == 0u ||
        scheduler->state != COMP_EPAPER_OVERLAY_COMMIT_IN_FLIGHT ||
        scheduler->in_flight_request_id != request_id) {
        return false;
    }
    candidate_advanced = scheduler->candidate_advanced;
    if (report != NULL) {
        report->request_id = request_id;
        report->request_to_visible_ms = completed_ms - scheduler->dispatched_ms;
        report->visible_to_dispatch_ms =
            scheduler->last_visible_to_dispatch_ms;
        report->visible = visible ? 1u : 0u;
        report->candidate_advanced = candidate_advanced;
    }
    if (visible) {
        scheduler->last_visible_ms = completed_ms;
        scheduler->has_visible_commit = 1u;
        scheduler->visible_commit_count++;
    } else {
        scheduler->failed_commit_count++;
    }
    scheduler->state = COMP_EPAPER_OVERLAY_COMMIT_READY;
    scheduler->in_flight_request_id = 0u;
    scheduler->candidate_prepared = 0u;
    scheduler->candidate_advanced = 0u;
    return true;
}

bool comp_epaper_overlay_commit_scheduler_active(
    const comp_epaper_overlay_commit_scheduler_t *scheduler)
{
    return scheduler != NULL &&
           scheduler->state != COMP_EPAPER_OVERLAY_COMMIT_INACTIVE;
}

bool comp_epaper_overlay_commit_scheduler_ready(
    const comp_epaper_overlay_commit_scheduler_t *scheduler)
{
    return scheduler != NULL &&
           scheduler->state == COMP_EPAPER_OVERLAY_COMMIT_READY;
}
