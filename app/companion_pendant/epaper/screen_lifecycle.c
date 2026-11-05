#include "screen_lifecycle.h"

#include <string.h>

static bool surface_valid(comp_screen_surface_t surface)
{
    return surface <= COMP_SCREEN_SURFACE_LOW_POWER;
}

static comp_screen_lifecycle_action_t action_for_surface(
    comp_screen_surface_t surface)
{
    switch (surface) {
    case COMP_SCREEN_SURFACE_HOME:
        return COMP_SCREEN_LIFECYCLE_ACTION_REARM_HOME;
    case COMP_SCREEN_SURFACE_MENU:
        return COMP_SCREEN_LIFECYCLE_ACTION_HOLD_MENU;
    case COMP_SCREEN_SURFACE_LOW_POWER:
        return COMP_SCREEN_LIFECYCLE_ACTION_FREEZE_LOW_POWER;
    default:
        return COMP_SCREEN_LIFECYCLE_ACTION_NONE;
    }
}

void comp_screen_lifecycle_init(comp_screen_lifecycle_t *lifecycle,
                                comp_screen_surface_t initial_surface)
{
    if (lifecycle == NULL || !surface_valid(initial_surface)) return;
    memset(lifecycle, 0, sizeof(*lifecycle));
    lifecycle->committed_surface = initial_surface;
    lifecycle->requested_surface = initial_surface;
    lifecycle->rollback_surface = initial_surface;
    lifecycle->epoch = 1u;
}

bool comp_screen_lifecycle_request(comp_screen_lifecycle_t *lifecycle,
                                   comp_screen_surface_t target_surface,
                                   uint32_t request_id)
{
    if (lifecycle == NULL || !surface_valid(target_surface) ||
        request_id == 0u) {
        return false;
    }
    if (lifecycle->pending) {
        return lifecycle->pending_request_id == request_id &&
               lifecycle->requested_surface == target_surface;
    }
    lifecycle->rollback_surface = lifecycle->committed_surface;
    lifecycle->requested_surface = target_surface;
    lifecycle->pending_request_id = request_id;
    lifecycle->pending = true;
    lifecycle->epoch++;
    lifecycle->request_count++;
    return true;
}

bool comp_screen_lifecycle_complete(
    comp_screen_lifecycle_t *lifecycle,
    uint32_t request_id,
    bool visible,
    comp_screen_lifecycle_action_t *action)
{
    comp_screen_surface_t resolved_surface;

    if (action != NULL) *action = COMP_SCREEN_LIFECYCLE_ACTION_NONE;
    if (lifecycle == NULL || request_id == 0u) return false;
    if (!lifecycle->pending) {
        if (request_id == lifecycle->last_completed_request_id) {
            lifecycle->duplicate_completion_count++;
        } else {
            lifecycle->stale_completion_count++;
        }
        return false;
    }
    if (request_id != lifecycle->pending_request_id) {
        lifecycle->stale_completion_count++;
        return false;
    }

    resolved_surface = visible ? lifecycle->requested_surface
                               : lifecycle->rollback_surface;
    lifecycle->committed_surface = resolved_surface;
    lifecycle->requested_surface = resolved_surface;
    lifecycle->pending = false;
    lifecycle->last_completed_request_id = request_id;
    lifecycle->pending_request_id = 0u;
    if (visible) {
        lifecycle->commit_count++;
    } else {
        lifecycle->rollback_count++;
    }
    if (action != NULL) *action = action_for_surface(resolved_surface);
    return true;
}

comp_screen_surface_t comp_screen_lifecycle_effective_surface(
    const comp_screen_lifecycle_t *lifecycle)
{
    if (lifecycle == NULL) return COMP_SCREEN_SURFACE_HOME;
    return lifecycle->pending ? lifecycle->requested_surface
                              : lifecycle->committed_surface;
}

void comp_screen_lifecycle_snapshot(
    const comp_screen_lifecycle_t *lifecycle,
    comp_screen_lifecycle_snapshot_t *snapshot)
{
    if (lifecycle == NULL || snapshot == NULL) return;
    *snapshot = (comp_screen_lifecycle_snapshot_t){
        .committed_surface = lifecycle->committed_surface,
        .effective_surface =
            comp_screen_lifecycle_effective_surface(lifecycle),
        .requested_surface = lifecycle->requested_surface,
        .pending_request_id = lifecycle->pending_request_id,
        .epoch = lifecycle->epoch,
        .pending = lifecycle->pending,
    };
}
