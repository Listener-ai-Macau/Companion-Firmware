#include "companion_visual_runtime_controller.h"

bool companion_visual_controller_dispatch(
    companion_visual_runtime_t *runtime,
    companion_visual_event_t event,
    uint32_t elapsed_ms,
    uint16_t move_px,
    uint32_t gap_ms,
    bool contact_active,
    uint8_t target_state)
{
    return companion_visual_runtime_enqueue_visual_event(
        runtime, event, elapsed_ms, move_px, gap_ms, contact_active,
        target_state);
}

bool companion_visual_controller_drag_center(
    companion_visual_runtime_t *runtime,
    uint32_t elapsed_ms,
    uint16_t move_px)
{
    return companion_visual_controller_dispatch(
        runtime, COMPANION_VISUAL_EVENT_POINTER_DRAG_CENTER, elapsed_ms,
        move_px, 0u, true, COMPANION_VISUAL_STATE_GAZE_CENTER);
}

bool companion_visual_controller_hold_cancel(
    companion_visual_runtime_t *runtime,
    uint32_t elapsed_ms,
    uint16_t move_px)
{
    return companion_visual_controller_dispatch(
        runtime, COMPANION_VISUAL_EVENT_EARLY_UP_CANCEL_BLUR_OR_DRAG,
        elapsed_ms, move_px, 0u, false,
        COMPANION_VISUAL_STATE_CENTERED_REST);
}

bool companion_visual_controller_select_ui_assets(
    companion_visual_runtime_t *runtime,
    uint32_t elapsed_ms)
{
    return companion_visual_controller_dispatch(
        runtime, COMPANION_VISUAL_EVENT_SELECT_UI_ASSETS, elapsed_ms, 0u,
        0u, false, COMPANION_VISUAL_STATE_MENU_DEVICE_UI_ASSETS);
}
