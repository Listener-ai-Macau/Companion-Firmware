#ifndef COMPANION_SCREEN_LIFECYCLE_H
#define COMPANION_SCREEN_LIFECYCLE_H

#include <stdbool.h>
#include <stdint.h>

typedef enum {
    COMP_SCREEN_SURFACE_HOME = 0u,
    COMP_SCREEN_SURFACE_MENU,
    COMP_SCREEN_SURFACE_LOW_POWER,
} comp_screen_surface_t;

typedef enum {
    COMP_SCREEN_LIFECYCLE_ACTION_NONE = 0u,
    COMP_SCREEN_LIFECYCLE_ACTION_REARM_HOME,
    COMP_SCREEN_LIFECYCLE_ACTION_HOLD_MENU,
    COMP_SCREEN_LIFECYCLE_ACTION_FREEZE_LOW_POWER,
} comp_screen_lifecycle_action_t;

typedef struct {
    comp_screen_surface_t committed_surface;
    comp_screen_surface_t requested_surface;
    comp_screen_surface_t rollback_surface;
    uint32_t pending_request_id;
    uint32_t last_completed_request_id;
    uint32_t epoch;
    uint32_t request_count;
    uint32_t commit_count;
    uint32_t rollback_count;
    uint32_t stale_completion_count;
    uint32_t duplicate_completion_count;
    bool pending;
    /* Cross-task cancellation latch for an ENTER_LOW_POWER intent that was
     * queued just before new touch/recording ownership became visible.  This
     * consumes existing tail padding, so the lifecycle object does not grow. */
    volatile bool cancel_queued_low_power_entry;
} comp_screen_lifecycle_t;

typedef struct {
    comp_screen_surface_t committed_surface;
    comp_screen_surface_t effective_surface;
    comp_screen_surface_t requested_surface;
    uint32_t pending_request_id;
    uint32_t epoch;
    bool pending;
} comp_screen_lifecycle_snapshot_t;

void comp_screen_lifecycle_init(comp_screen_lifecycle_t *lifecycle,
                                comp_screen_surface_t initial_surface);
bool comp_screen_lifecycle_request(comp_screen_lifecycle_t *lifecycle,
                                   comp_screen_surface_t target_surface,
                                   uint32_t request_id);
bool comp_screen_lifecycle_complete(
    comp_screen_lifecycle_t *lifecycle,
    uint32_t request_id,
    bool visible,
    comp_screen_lifecycle_action_t *action);
comp_screen_surface_t comp_screen_lifecycle_effective_surface(
    const comp_screen_lifecycle_t *lifecycle);
void comp_screen_lifecycle_snapshot(
    const comp_screen_lifecycle_t *lifecycle,
    comp_screen_lifecycle_snapshot_t *snapshot);

#endif
