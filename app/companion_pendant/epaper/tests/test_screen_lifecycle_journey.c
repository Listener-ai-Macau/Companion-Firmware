#include "screen_lifecycle.h"

#include <assert.h>
#include <stdio.h>

int main(void)
{
    comp_screen_lifecycle_t lifecycle;
    comp_screen_lifecycle_action_t action;
    comp_screen_lifecycle_snapshot_t snapshot;

    comp_screen_lifecycle_init(&lifecycle, COMP_SCREEN_SURFACE_HOME);
    assert(comp_screen_lifecycle_effective_surface(&lifecycle) ==
           COMP_SCREEN_SURFACE_HOME);

    assert(comp_screen_lifecycle_request(
        &lifecycle, COMP_SCREEN_SURFACE_LOW_POWER, 101u));
    assert(comp_screen_lifecycle_request(
        &lifecycle, COMP_SCREEN_SURFACE_LOW_POWER, 101u));
    assert(!comp_screen_lifecycle_request(
        &lifecycle, COMP_SCREEN_SURFACE_MENU, 102u));
    assert(comp_screen_lifecycle_effective_surface(&lifecycle) ==
           COMP_SCREEN_SURFACE_LOW_POWER);
    assert(lifecycle.committed_surface == COMP_SCREEN_SURFACE_HOME);
    assert(!comp_screen_lifecycle_complete(&lifecycle, 99u, true, &action));
    assert(lifecycle.pending);
    assert(comp_screen_lifecycle_complete(&lifecycle, 101u, true, &action));
    assert(action == COMP_SCREEN_LIFECYCLE_ACTION_FREEZE_LOW_POWER);
    assert(lifecycle.committed_surface == COMP_SCREEN_SURFACE_LOW_POWER);
    assert(!comp_screen_lifecycle_complete(&lifecycle, 101u, true, &action));
    assert(lifecycle.duplicate_completion_count == 1u);

    assert(comp_screen_lifecycle_request(
        &lifecycle, COMP_SCREEN_SURFACE_HOME, 103u));
    assert(comp_screen_lifecycle_complete(&lifecycle, 103u, true, &action));
    assert(action == COMP_SCREEN_LIFECYCLE_ACTION_REARM_HOME);
    assert(lifecycle.committed_surface == COMP_SCREEN_SURFACE_HOME);

    /* Recording is an overlay, not a surface transition. */
    comp_screen_lifecycle_snapshot(&lifecycle, &snapshot);
    assert(!snapshot.pending);
    assert(snapshot.committed_surface == COMP_SCREEN_SURFACE_HOME);
    assert(snapshot.effective_surface == COMP_SCREEN_SURFACE_HOME);

    assert(comp_screen_lifecycle_request(
        &lifecycle, COMP_SCREEN_SURFACE_LOW_POWER, 104u));
    assert(comp_screen_lifecycle_complete(&lifecycle, 104u, false, &action));
    assert(action == COMP_SCREEN_LIFECYCLE_ACTION_REARM_HOME);
    assert(lifecycle.committed_surface == COMP_SCREEN_SURFACE_HOME);
    assert(lifecycle.rollback_count == 1u);

    assert(comp_screen_lifecycle_request(
        &lifecycle, COMP_SCREEN_SURFACE_MENU, 105u));
    assert(comp_screen_lifecycle_complete(&lifecycle, 105u, true, &action));
    assert(action == COMP_SCREEN_LIFECYCLE_ACTION_HOLD_MENU);
    assert(comp_screen_lifecycle_request(
        &lifecycle, COMP_SCREEN_SURFACE_HOME, 106u));
    assert(comp_screen_lifecycle_complete(&lifecycle, 106u, false, &action));
    assert(action == COMP_SCREEN_LIFECYCLE_ACTION_HOLD_MENU);
    assert(lifecycle.committed_surface == COMP_SCREEN_SURFACE_MENU);

    assert(lifecycle.request_count == 5u);
    assert(lifecycle.commit_count == 3u);
    assert(lifecycle.rollback_count == 2u);
    assert(lifecycle.stale_completion_count == 1u);
    puts("PASS: lifecycle journey preserves committed surface, rejects stale "
         "completion, and rolls back failed boundaries atomically.");
    return 0;
}
