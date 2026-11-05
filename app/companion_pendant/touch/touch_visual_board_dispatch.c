#include "touch_visual_board_dispatch.h"

static bool event_adapter(void *context, companion_visual_event_t event,
                          uint32_t elapsed_ms, uint16_t move_px,
                          uint8_t target_state)
{
    const comp_touch_visual_board_dispatch_sinks_t *sinks = context;
    return sinks->visual_event(sinks->context, event, elapsed_ms, move_px,
                        target_state);
}

static void route_adapter(void *context, const comp_screen_menu_result_t *result)
{
    const comp_touch_visual_board_dispatch_sinks_t *sinks = context;
    if (sinks->route != NULL) sinks->route(sinks->context, result);
}

static void render_adapter(void *context, const comp_screen_menu_t *menu)
{
    const comp_touch_visual_board_dispatch_sinks_t *sinks = context;
    if (sinks->render != NULL) sinks->render(sinks->context, menu);
}

static void frame_adapter(void *context, uint8_t from_state, uint8_t to_state,
                          uint32_t previous_hash, uint32_t current_hash)
{
    const comp_touch_visual_board_dispatch_sinks_t *sinks = context;
    if (sinks->frame != NULL)
        sinks->frame(sinks->context, from_state, to_state,
                     previous_hash, current_hash);
}

bool comp_touch_visual_board_dispatch(
    const comp_touch_visual_decision_t *decision,
    const comp_screen_menu_t *menu,
    const comp_touch_visual_board_dispatch_sinks_t *sinks)
{
    comp_touch_visual_sinks_t shared;
    if (decision == NULL || sinks == NULL || sinks->visual_event == NULL) return false;
    shared.event = event_adapter;
    shared.route = route_adapter;
    shared.render = render_adapter;
    shared.frame = frame_adapter;
    shared.context = (void *)sinks;
    return comp_touch_visual_emit_decision(decision, menu, &shared);
}
