#include "companion_visual_runtime_adapter.h"
#include "companion_visual_asset_pack.h"

#include <string.h>

static bool is_menu_state(uint8_t state)
{
    return state >= COMPANION_VISUAL_STATE_MENU_ROOTS &&
           state <= COMPANION_VISUAL_STATE_MENU_DEVICE_UI_ASSETS;
}

static bool menu_transition(uint8_t from_state, uint8_t to_state)
{
    return is_menu_state(from_state) || is_menu_state(to_state) ||
           to_state == COMPANION_VISUAL_STATE_MENU_RETURN_REST;
}

#if COMPANION_VISUAL_ASSET_PACK_ENABLE
static bool is_declared_transition(uint8_t from_state, uint8_t to_state)
{
    uint32_t from_mask = UINT32_C(1) << from_state;
    uint32_t to_mask = UINT32_C(1) << to_state;
    for (size_t i = 0u; i < COMPANION_VISUAL_TRANSITION_COUNT; ++i) {
        if ((companion_visual_transition_table[i].from_state_mask & from_mask) != 0u &&
            (companion_visual_transition_table[i].to_state_mask & to_mask) != 0u) {
            return true;
        }
    }
    return false;
}
#endif

void companion_visual_runtime_init(companion_visual_runtime_t *runtime)
{
    if (runtime != NULL) memset(runtime, 0, sizeof(*runtime));
}

static uint8_t panel_byte(const uint8_t *logical, size_t offset)
{
    return (uint8_t)~logical[offset];
}

bool companion_visual_runtime_copy_panel_frame(companion_visual_state_t state,
                                               uint8_t *panel_frame,
                                               size_t panel_frame_bytes)
{
    const uint8_t *logical = companion_visual_frame_for_state(state);
    if (logical == NULL || panel_frame == NULL ||
        panel_frame_bytes < COMPANION_VISUAL_FRAME_BYTES) return false;
    for (size_t i = 0u; i < COMPANION_VISUAL_FRAME_BYTES; ++i) {
        panel_frame[i] = panel_byte(logical, i);
    }
    return true;
}

bool companion_visual_runtime_enqueue(companion_visual_runtime_t *runtime,
                                       companion_visual_runtime_event_kind_t kind,
                                       uint8_t state)
{
    if (runtime == NULL || state >= COMPANION_VISUAL_STATE_COUNT) return false;
    if (kind == COMPANION_VISUAL_RUNTIME_EVENT_GAZE) {
        for (uint8_t i = 0u; i < runtime->ring_count; ++i) {
            uint8_t index = (uint8_t)((runtime->ring_head + i) %
                                      COMPANION_VISUAL_RUNTIME_RING_CAPACITY);
            if (runtime->ring[index].kind == COMPANION_VISUAL_RUNTIME_EVENT_GAZE) {
                runtime->ring[index].state = state;
                runtime->ring[index].sequence = runtime->next_sequence++;
                return true;
            }
        }
    }
    if (runtime->ring_count == COMPANION_VISUAL_RUNTIME_RING_CAPACITY) {
        if (kind == COMPANION_VISUAL_RUNTIME_EVENT_MENU ||
            kind == COMPANION_VISUAL_RUNTIME_EVENT_RECORDING) {
            uint8_t evict = COMPANION_VISUAL_RUNTIME_RING_CAPACITY;
            for (uint8_t i = 0u; i < runtime->ring_count; ++i) {
                uint8_t index = (uint8_t)((runtime->ring_head + i) %
                                          COMPANION_VISUAL_RUNTIME_RING_CAPACITY);
                if (runtime->ring[index].kind ==
                        COMPANION_VISUAL_RUNTIME_EVENT_GAZE ||
                    runtime->ring[index].kind ==
                        COMPANION_VISUAL_RUNTIME_EVENT_TAP) {
                    evict = i;
                    break;
                }
            }
            if (evict == COMPANION_VISUAL_RUNTIME_RING_CAPACITY) return false;
            for (uint8_t i = evict; i + 1u < runtime->ring_count; ++i) {
                uint8_t dst = (uint8_t)((runtime->ring_head + i) %
                                        COMPANION_VISUAL_RUNTIME_RING_CAPACITY);
                uint8_t src = (uint8_t)((runtime->ring_head + i + 1u) %
                                        COMPANION_VISUAL_RUNTIME_RING_CAPACITY);
                runtime->ring[dst] = runtime->ring[src];
            }
            runtime->ring_count--;
        } else {
            return false;
        }
    }
    uint8_t tail = (uint8_t)((runtime->ring_head + runtime->ring_count) %
                             COMPANION_VISUAL_RUNTIME_RING_CAPACITY);
    runtime->ring[tail] = (companion_visual_runtime_event_t){kind, state,
                                                              runtime->next_sequence++};
    runtime->ring_count++;
    return true;
}

bool companion_visual_runtime_enqueue_gesture(
    companion_visual_runtime_t *runtime,
    comp_touch_gesture_type_t gesture,
    uint32_t elapsed_ms,
    uint16_t move_px,
    uint8_t gaze_state)
{
    uint8_t state = COMPANION_VISUAL_STATE_CENTERED_REST;
    companion_visual_runtime_event_kind_t kind =
        COMPANION_VISUAL_RUNTIME_EVENT_GAZE;

    if (!companion_visual_runtime_map_touch(gesture, elapsed_ms, move_px,
                                            gaze_state, &state)) {
        return false;
    }
    switch (gesture) {
    case COMP_TOUCH_GESTURE_TAP:
        kind = COMPANION_VISUAL_RUNTIME_EVENT_TAP;
        break;
    case COMP_TOUCH_GESTURE_DOUBLE_TAP:
        kind = COMPANION_VISUAL_RUNTIME_EVENT_RECORDING;
        break;
    case COMP_TOUCH_GESTURE_HOLD:
        kind = COMPANION_VISUAL_RUNTIME_EVENT_GAZE;
        break;
    case COMP_TOUCH_GESTURE_LONG_PRESS:
        kind = COMPANION_VISUAL_RUNTIME_EVENT_MENU;
        break;
    case COMP_TOUCH_GESTURE_SWIPE_LEFT:
    case COMP_TOUCH_GESTURE_SWIPE_RIGHT:
    case COMP_TOUCH_GESTURE_SWIPE_UP:
    case COMP_TOUCH_GESTURE_SWIPE_DOWN:
        kind = COMPANION_VISUAL_RUNTIME_EVENT_GAZE;
        break;
    case COMP_TOUCH_GESTURE_NONE:
        kind = COMPANION_VISUAL_RUNTIME_EVENT_GAZE;
        break;
    default:
        return false;
    }
    return companion_visual_runtime_enqueue(runtime, kind, state);
}

bool companion_visual_runtime_enqueue_visual_event(
    companion_visual_runtime_t *runtime,
    companion_visual_event_t event,
    uint32_t elapsed_ms,
    uint16_t move_px,
    uint32_t gap_ms,
    bool contact_active,
    uint8_t target_state)
{
    companion_visual_runtime_event_kind_t kind =
        COMPANION_VISUAL_RUNTIME_EVENT_GAZE;
    uint8_t state = target_state;

    if (runtime == NULL || target_state >= COMPANION_VISUAL_STATE_COUNT) return false;
    switch (event) {
    case COMPANION_VISUAL_EVENT_POINTER_MOVE:
        if (!contact_active || target_state > COMPANION_VISUAL_STATE_GAZE_CENTER) return false;
        kind = COMPANION_VISUAL_RUNTIME_EVENT_GAZE;
        break;
    case COMPANION_VISUAL_EVENT_POINTER_DRAG_LEFT:
    case COMPANION_VISUAL_EVENT_POINTER_DRAG_UP:
    case COMPANION_VISUAL_EVENT_POINTER_DRAG_RIGHT:
    case COMPANION_VISUAL_EVENT_POINTER_DRAG_DOWN:
    case COMPANION_VISUAL_EVENT_POINTER_DRAG_CENTER:
        if (move_px <= 40u) return false;
        kind = COMPANION_VISUAL_RUNTIME_EVENT_GAZE;
        break;
    case COMPANION_VISUAL_EVENT_POINTER_UP_OR_CANCEL:
    case COMPANION_VISUAL_EVENT_EARLY_UP_CANCEL_BLUR_OR_DRAG:
    case COMPANION_VISUAL_EVENT_SETTLE:
    case COMPANION_VISUAL_EVENT_RECORDING_RETURN:
    case COMPANION_VISUAL_EVENT_MENU_RETURN:
        state = COMPANION_VISUAL_STATE_CENTERED_REST;
        kind = COMPANION_VISUAL_RUNTIME_EVENT_GAZE;
        break;
    case COMPANION_VISUAL_EVENT_SINGLE_TAP_COMMIT:
        if (gap_ms < 650u) return false;
        state = COMPANION_VISUAL_STATE_SINGLE_TAP_RESPONSE;
        kind = COMPANION_VISUAL_RUNTIME_EVENT_TAP;
        break;
    case COMPANION_VISUAL_EVENT_STATIONARY_POINTERDOWN:
        if (move_px > 40u) return false;
        state = COMPANION_VISUAL_STATE_HOLD_FEEDBACK_50;
        kind = COMPANION_VISUAL_RUNTIME_EVENT_GAZE;
        break;
    case COMPANION_VISUAL_EVENT_HOLD_COMPLETE:
        if (elapsed_ms < 3000u) return false;
        state = COMPANION_VISUAL_STATE_MENU_ROOTS;
        kind = COMPANION_VISUAL_RUNTIME_EVENT_MENU;
        break;
    case COMPANION_VISUAL_EVENT_SECOND_SHORT_TAP:
        if (gap_ms > 650u || move_px > 40u) return false;
        state = COMPANION_VISUAL_STATE_RECORDING_ENTRY;
        kind = COMPANION_VISUAL_RUNTIME_EVENT_RECORDING;
        break;
    case COMPANION_VISUAL_EVENT_SELECT_VOICE:
    case COMPANION_VISUAL_EVENT_SELECT_DEVICE:
    case COMPANION_VISUAL_EVENT_SELECT_CONNECTION:
    case COMPANION_VISUAL_EVENT_SELECT_PREFERENCES:
    case COMPANION_VISUAL_EVENT_SELECT_UI_ASSETS:
    case COMPANION_VISUAL_EVENT_MENU_BACK:
        kind = COMPANION_VISUAL_RUNTIME_EVENT_MENU;
        break;
    default:
        return false;
    }
    return companion_visual_runtime_enqueue(runtime, kind, state);
}

bool companion_visual_runtime_pop(companion_visual_runtime_t *runtime,
                                  companion_visual_runtime_event_t *event)
{
    if (runtime == NULL || event == NULL || runtime->ring_count == 0u) return false;
    *event = runtime->ring[runtime->ring_head];
    runtime->ring_head = (uint8_t)((runtime->ring_head + 1u) %
                                   COMPANION_VISUAL_RUNTIME_RING_CAPACITY);
    runtime->ring_count--;
    return true;
}

bool companion_visual_runtime_peek(const companion_visual_runtime_t *runtime,
                                  companion_visual_runtime_event_t *event)
{
    if (runtime == NULL || event == NULL || runtime->ring_count == 0u) return false;
    *event = runtime->ring[runtime->ring_head];
    return true;
}

bool companion_visual_runtime_discard(companion_visual_runtime_t *runtime)
{
    if (runtime == NULL || runtime->ring_count == 0u) return false;
    runtime->ring_head = (uint8_t)((runtime->ring_head + 1u) %
                                   COMPANION_VISUAL_RUNTIME_RING_CAPACITY);
    runtime->ring_count--;
    return true;
}

bool companion_visual_runtime_frames_equal(const uint8_t *previous,
                                           const uint8_t *current)
{
    if (previous == NULL || current == NULL) return false;
    for (size_t i = 0u; i < COMPANION_VISUAL_FRAME_BYTES; ++i) {
        if (panel_byte(previous, i) != panel_byte(current, i)) return false;
    }
    return true;
}

bool companion_visual_runtime_build_window(const uint8_t *previous,
                                           const uint8_t *current,
                                           uint8_t from_state,
                                           uint8_t to_state,
                                           companion_visual_runtime_window_t *window)
{
#if !COMPANION_VISUAL_ASSET_PACK_ENABLE
    (void)previous; (void)current; (void)from_state; (void)to_state; (void)window;
    return false;
#else
    if (previous == NULL || current == NULL || window == NULL ||
        from_state >= COMPANION_VISUAL_STATE_COUNT ||
        to_state >= COMPANION_VISUAL_STATE_COUNT ||
        !is_declared_transition(from_state, to_state)) return false;
    int first_x = COMPANION_VISUAL_WIDTH;
    int last_x = -1;
    int first_y = COMPANION_VISUAL_HEIGHT;
    int last_y = -1;
    for (int y = 0; y < (int)COMPANION_VISUAL_HEIGHT; ++y) {
        for (int x = 0; x < (int)COMPANION_VISUAL_WIDTH; ++x) {
            size_t offset = (size_t)y * COMPANION_VISUAL_STRIDE_BYTES + (size_t)(x / 8);
            uint8_t mask = (uint8_t)(0x80u >> (x & 7));
            if ((panel_byte(previous, offset) & mask) !=
                (panel_byte(current, offset) & mask)) {
                if (x < first_x) first_x = x;
                if (x > last_x) last_x = x;
                if (y < first_y) first_y = y;
                if (y > last_y) last_y = y;
            }
        }
    }
    if (last_x < 0) return false;
    uint8_t x_start = (uint8_t)(first_x / 8);
    uint8_t x_end = (uint8_t)(last_x / 8);
    bool full_frame = x_start == 0u && x_end == 24u && first_y == 0 && last_y == 199;
    if (full_frame && !menu_transition(from_state, to_state)) return false;
    memset(window, 0, sizeof(*window));
    window->x_byte_start = x_start;
    window->x_byte_end = x_end;
    window->y_start = (uint16_t)first_y;
    window->y_end = (uint16_t)last_y;
    window->payload_bytes = (uint16_t)((x_end - x_start + 1u) * (last_y - first_y + 1));
    window->full_frame_menu = full_frame;
    for (int y = first_y; y <= last_y; ++y) {
        size_t source = (size_t)y * COMPANION_VISUAL_STRIDE_BYTES + x_start;
        size_t target = (size_t)(y - first_y) * (x_end - x_start + 1u);
        for (int byte = x_start; byte <= x_end; ++byte) {
            window->payload[target + (size_t)(byte - x_start)] =
                panel_byte(current, source + (size_t)(byte - x_start));
        }
    }
    return true;
#endif
}

bool companion_visual_runtime_emit_window(const companion_visual_runtime_window_t *window,
                                          companion_visual_runtime_transport_fn transport,
                                          void *context)
{
    if (window == NULL || transport == NULL) return false;
    const uint8_t xy[] = {window->x_byte_start, window->x_byte_end};
    const uint16_t controller_start = 199u - window->y_start;
    const uint16_t controller_end = 199u - window->y_end;
    const uint8_t y[] = {(uint8_t)controller_start, 0u,
                         (uint8_t)controller_end, 0u};
    const uint8_t start[] = {window->x_byte_start};
    const uint8_t end[] = {(uint8_t)controller_start, 0u};
    const uint8_t cf = 0xCFu;
    return transport(context, 0x3Cu, (const uint8_t[]){0x80u}, 1u) &&
           transport(context, 0x44u, xy, 2u) &&
           transport(context, 0x45u, y, 4u) &&
           transport(context, 0x4Eu, start, 1u) &&
           transport(context, 0x4Fu, end, 2u) &&
           transport(context, 0x24u, window->payload, window->payload_bytes) &&
           transport(context, 0x22u, &cf, 1u) && transport(context, 0x20u, NULL, 0u);
}

bool companion_visual_runtime_service(
    companion_visual_runtime_t *runtime,
    companion_visual_runtime_transport_fn transport,
    void *context)
{
    companion_visual_runtime_event_t event;
    const uint8_t *previous;
    const uint8_t *current;
    companion_visual_runtime_window_t window;
    bool emitted;

    if (runtime == NULL || runtime->terminal_fault ||
        !companion_visual_runtime_peek(runtime, &event)) {
        return false;
    }
    previous = companion_visual_frame_for_state(
        (companion_visual_state_t)runtime->current_state);
    current = companion_visual_frame_for_state(
        (companion_visual_state_t)event.state);
    if (previous == NULL || current == NULL) {
        runtime->failed_events++;
        runtime->terminal_fault = true;
        return false;
    }
    if (companion_visual_runtime_frames_equal(previous, current)) {
        (void)companion_visual_runtime_discard(runtime);
        runtime->current_state = event.state;
        runtime->serviced_events++;
        return true;
    }
    if (!companion_visual_runtime_build_window(previous, current,
                                               runtime->current_state,
                                               event.state, &window)) {
        runtime->failed_events++;
        runtime->terminal_fault = true;
        return false;
    }
    emitted = companion_visual_runtime_emit_window(&window, transport, context);
    if (emitted) {
        (void)companion_visual_runtime_discard(runtime);
        runtime->current_state = event.state;
        runtime->serviced_events++;
    } else {
        runtime->failed_events++;
        runtime->terminal_fault = true;
    }
    return emitted;
}

bool companion_visual_runtime_has_terminal_fault(
    const companion_visual_runtime_t *runtime)
{
    return runtime != NULL && runtime->terminal_fault;
}

bool companion_visual_runtime_map_touch(comp_touch_gesture_type_t gesture,
                                        uint32_t elapsed_ms,
                                        uint16_t move_px,
                                        uint8_t gaze_state,
                                        uint8_t *visual_state)
{
    if (visual_state == NULL) return false;
    switch (gesture) {
    case COMP_TOUCH_GESTURE_TAP:
        *visual_state = COMPANION_VISUAL_STATE_SINGLE_TAP_RESPONSE; return true;
    case COMP_TOUCH_GESTURE_DOUBLE_TAP:
        if (elapsed_ms > 650u || move_px > 40u) return false;
        *visual_state = COMPANION_VISUAL_STATE_RECORDING_ENTRY; return true;
    case COMP_TOUCH_GESTURE_HOLD:
        if (elapsed_ms < 650u) return false;
        *visual_state = COMPANION_VISUAL_STATE_HOLD_FEEDBACK_50; return true;
    case COMP_TOUCH_GESTURE_LONG_PRESS:
        if (elapsed_ms < 3000u) return false;
        *visual_state = COMPANION_VISUAL_STATE_MENU_ROOTS; return true;
    case COMP_TOUCH_GESTURE_SWIPE_LEFT:
    case COMP_TOUCH_GESTURE_SWIPE_UP:
    case COMP_TOUCH_GESTURE_SWIPE_RIGHT:
    case COMP_TOUCH_GESTURE_SWIPE_DOWN:
        if (gaze_state > COMPANION_VISUAL_STATE_GAZE_CENTER) return false;
        *visual_state = gaze_state; return true;
    case COMP_TOUCH_GESTURE_NONE:
        *visual_state = COMPANION_VISUAL_STATE_CENTERED_REST; return true;
    default: return false;
    }
}
