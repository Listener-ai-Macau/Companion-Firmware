#include "touch_recording_boundary.h"

#include <string.h>

void comp_touch_recording_boundary_init(
    comp_touch_recording_boundary_t *boundary,
    const comp_touch_recording_boundary_sinks_t *sinks)
{
    if (boundary == NULL) return;
    memset(boundary, 0, sizeof(*boundary));
    if (sinks != NULL) boundary->sinks = *sinks;
}

bool comp_touch_recording_boundary_submit(
    comp_touch_recording_boundary_t *boundary,
    const comp_touch_gesture_event_t *gesture,
    comp_recording_state_t state,
    bool menu_visible,
    uint32_t now_ms)
{
    (void)state;
    (void)now_ms;
    if (boundary == NULL || gesture == NULL || menu_visible ||
        gesture->type != COMP_TOUCH_GESTURE_DOUBLE_TAP) {
        return false;
    }
    boundary->submitted++;
    /* A second report cannot replace a live action.  Since the only action
     * at this boundary is a recording toggle, an already queued toggle is
     * the same logical decision and is consumed exactly once. */
    for (uint8_t i = 0u; i < boundary->queue_count; ++i) {
        if (boundary->queue[i] == COMP_TOUCH_RECORDING_ACTION_TOGGLE) {
            boundary->deduplicated++;
            return true;
        }
    }
    if (boundary->queue_count >= 2u) return false;
    boundary->queue[boundary->queue_count++] =
        COMP_TOUCH_RECORDING_ACTION_TOGGLE;
    return true;
}

bool comp_touch_recording_boundary_dispatch(
    comp_touch_recording_boundary_t *boundary,
    const comp_touch_visual_decision_t *decision,
    bool menu_visible,
    const comp_screen_menu_t *menu,
    comp_recording_state_t state,
    uint32_t now_ms)
{
    if (boundary == NULL || decision == NULL) return false;
    if (menu_visible) {
        if (!decision->menu_result.changed && !decision->ui_assets_selected)
            return true;
        return boundary->sinks.menu == NULL ||
               boundary->sinks.menu(boundary->sinks.context,
                                    decision, menu, now_ms);
    }
    if (!decision->gesture_ready ||
        decision->gesture.type != COMP_TOUCH_GESTURE_DOUBLE_TAP) return true;
    return comp_touch_recording_boundary_submit(
        boundary, &decision->gesture, state, false, now_ms);
}

bool comp_touch_recording_boundary_service(
    comp_touch_recording_boundary_t *boundary,
    comp_recording_state_t state)
{
    comp_touch_recording_action_t action;
    if (boundary == NULL || boundary->queue_count == 0u ||
        boundary->sinks.execute == NULL) return false;
    action = boundary->queue[0];
    if (!boundary->sinks.execute(boundary->sinks.context, action, state)) {
        boundary->failed++;
        return false;
    }
    for (uint8_t i = 1u; i < boundary->queue_count; ++i)
        boundary->queue[i - 1u] = boundary->queue[i];
    boundary->queue[--boundary->queue_count] = COMP_TOUCH_RECORDING_ACTION_NONE;
    boundary->executed++;
    return true;
}

uint8_t comp_touch_recording_boundary_pending(
    const comp_touch_recording_boundary_t *boundary)
{
    return boundary != NULL ? boundary->queue_count : 0u;
}
