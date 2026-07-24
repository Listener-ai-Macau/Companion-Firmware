#ifndef TOUCH_VISUAL_BOARD_DISPATCH_H
#define TOUCH_VISUAL_BOARD_DISPATCH_H

#include "touch_visual_decision.h"

typedef bool (*comp_touch_visual_board_event_sink_t)(
    void *context, companion_visual_event_t event, uint32_t elapsed_ms,
    uint16_t move_px, uint8_t target_state);
typedef void (*comp_touch_visual_board_route_sink_t)(
    void *context, const comp_screen_menu_result_t *result);
typedef void (*comp_touch_visual_board_render_sink_t)(
    void *context, const comp_screen_menu_t *menu);
typedef void (*comp_touch_visual_board_frame_sink_t)(
    void *context, uint8_t from_state, uint8_t to_state,
    uint32_t previous_hash, uint32_t current_hash);

typedef struct {
    comp_touch_visual_board_event_sink_t event;
    comp_touch_visual_board_route_sink_t route;
    comp_touch_visual_board_render_sink_t render;
    comp_touch_visual_board_frame_sink_t frame;
    void *context;
} comp_touch_visual_board_dispatch_sinks_t;

bool comp_touch_visual_board_dispatch(
    const comp_touch_visual_decision_t *decision,
    const comp_screen_menu_t *menu,
    const comp_touch_visual_board_dispatch_sinks_t *sinks);

#endif
