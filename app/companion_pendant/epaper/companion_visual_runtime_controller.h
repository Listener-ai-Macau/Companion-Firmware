#ifndef COMPANION_VISUAL_RUNTIME_CONTROLLER_H
#define COMPANION_VISUAL_RUNTIME_CONTROLLER_H

#include "companion_visual_runtime_adapter.h"

/* These are the production event entry points.  Board main and host replay
 * call the same functions; the controller owns the only adapter enqueue. */
bool companion_visual_controller_dispatch(
    companion_visual_runtime_t *runtime,
    companion_visual_event_t event,
    uint32_t elapsed_ms,
    uint16_t move_px,
    uint32_t gap_ms,
    bool contact_active,
    uint8_t target_state);

bool companion_visual_controller_drag_center(
    companion_visual_runtime_t *runtime,
    uint32_t elapsed_ms,
    uint16_t move_px);

bool companion_visual_controller_hold_cancel(
    companion_visual_runtime_t *runtime,
    uint32_t elapsed_ms,
    uint16_t move_px);

bool companion_visual_controller_select_ui_assets(
    companion_visual_runtime_t *runtime,
    uint32_t elapsed_ms);

#endif
