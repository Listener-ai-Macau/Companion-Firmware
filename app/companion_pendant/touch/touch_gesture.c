#include "touch_gesture.h"

#include <string.h>

enum {
    TOUCH_AXIS_UNLOCKED = 0u,
    TOUCH_AXIS_HORIZONTAL = 1u,
    TOUCH_AXIS_VERTICAL = 2u,
};

static uint16_t distance(uint16_t first, uint16_t second)
{
    return first > second ? (uint16_t)(first - second)
                          : (uint16_t)(second - first);
}

void comp_touch_gesture_init(comp_touch_gesture_state_t *state,
                             const comp_touch_gesture_config_t *config)
{
    static const comp_touch_gesture_config_t defaults = {
        .tap_max_move_px = 32u,
        .long_press_max_move_px = 44u,
        .swipe_min_move_px = 40u,
        .axis_lock_min_move_px = 14u,
        .axis_slop_px = 24u,
        .tap_max_duration_ms = 2000u,
        .swipe_max_duration_ms = 1200u,
        .hold_feedback_min_duration_ms = 650u,
        .long_press_min_duration_ms = 3000u,
        .double_tap_max_gap_ms = 350u,
        .double_tap_max_move_px = 32u,
        .axis_dominance_percent = 140u,
        .min_contact_samples = 2u,
        .release_debounce_samples = 2u,
    };

    if (state == NULL) {
        return;
    }
    memset(state, 0, sizeof(*state));
    state->config = config == NULL ? defaults : *config;
    if (state->config.release_debounce_samples == 0u) {
        state->config.release_debounce_samples = 1u;
    }
    if (state->config.min_contact_samples == 0u) {
        state->config.min_contact_samples = 1u;
    }
    if (state->config.axis_dominance_percent < 100u) {
        state->config.axis_dominance_percent = 100u;
    }
    if (state->config.long_press_min_duration_ms == 0u) {
        state->config.long_press_min_duration_ms =
            defaults.long_press_min_duration_ms;
    }
    if (state->config.long_press_max_move_px == 0u) {
        state->config.long_press_max_move_px =
            defaults.long_press_max_move_px;
    }
    if (state->config.long_press_max_move_px < state->config.tap_max_move_px) {
        state->config.long_press_max_move_px = state->config.tap_max_move_px;
    }
    if (state->config.hold_feedback_min_duration_ms == 0u ||
        state->config.hold_feedback_min_duration_ms >=
            state->config.long_press_min_duration_ms) {
        state->config.hold_feedback_min_duration_ms =
            defaults.hold_feedback_min_duration_ms;
    }
    if (state->config.double_tap_max_gap_ms == 0u) {
        state->config.double_tap_max_gap_ms = defaults.double_tap_max_gap_ms;
    }
    if (state->config.double_tap_max_move_px == 0u) {
        state->config.double_tap_max_move_px = defaults.double_tap_max_move_px;
    }
}

static void update_axis_lock(comp_touch_gesture_state_t *state)
{
    uint16_t move_x;
    uint16_t move_y;

    if (state->locked_axis != TOUCH_AXIS_UNLOCKED) {
        return;
    }
    move_x = distance(state->start_x, state->latest_x);
    move_y = distance(state->start_y, state->latest_y);
    if (move_x < state->config.axis_lock_min_move_px &&
        move_y < state->config.axis_lock_min_move_px) {
        return;
    }
    if (move_x >= (uint16_t)(move_y + state->config.axis_slop_px) &&
        (uint32_t)move_x * 100u >=
            (uint32_t)move_y * state->config.axis_dominance_percent) {
        state->locked_axis = TOUCH_AXIS_HORIZONTAL;
    } else if (move_y >= (uint16_t)(move_x + state->config.axis_slop_px) &&
               (uint32_t)move_y * 100u >=
                   (uint32_t)move_x * state->config.axis_dominance_percent) {
        state->locked_axis = TOUCH_AXIS_VERTICAL;
    }
}

static comp_touch_gesture_type_t classify(const comp_touch_gesture_state_t *state,
                                          uint32_t duration_ms)
{
    uint16_t move_x = distance(state->start_x, state->latest_x);
    uint16_t move_y = distance(state->start_y, state->latest_y);

    if (state->contact_samples >= state->config.min_contact_samples &&
        duration_ms >= state->config.long_press_min_duration_ms &&
        move_x <= state->config.long_press_max_move_px &&
        move_y <= state->config.long_press_max_move_px) {
        return COMP_TOUCH_GESTURE_LONG_PRESS;
    }
    if (state->contact_samples >= state->config.min_contact_samples &&
        duration_ms <= state->config.tap_max_duration_ms &&
        move_x <= state->config.tap_max_move_px &&
        move_y <= state->config.tap_max_move_px) {
        return COMP_TOUCH_GESTURE_TAP;
    }
    if (state->contact_samples < state->config.min_contact_samples ||
        duration_ms > state->config.swipe_max_duration_ms) {
        return COMP_TOUCH_GESTURE_NONE;
    }
    if (state->locked_axis == TOUCH_AXIS_HORIZONTAL &&
        move_x >= state->config.swipe_min_move_px) {
        return state->latest_x < state->start_x
                   ? COMP_TOUCH_GESTURE_SWIPE_LEFT
                   : COMP_TOUCH_GESTURE_SWIPE_RIGHT;
    }
    if (state->locked_axis == TOUCH_AXIS_VERTICAL &&
        move_y >= state->config.swipe_min_move_px) {
        return state->latest_y < state->start_y
                   ? COMP_TOUCH_GESTURE_SWIPE_UP
                   : COMP_TOUCH_GESTURE_SWIPE_DOWN;
    }
    return COMP_TOUCH_GESTURE_NONE;
}

static bool is_horizontal_swipe(comp_touch_gesture_type_t type)
{
    return type == COMP_TOUCH_GESTURE_SWIPE_LEFT ||
           type == COMP_TOUCH_GESTURE_SWIPE_RIGHT;
}

bool comp_touch_gesture_is_vertical_drag(const comp_touch_gesture_state_t *state)
{
    return state != NULL && state->active &&
           state->locked_axis == TOUCH_AXIS_VERTICAL;
}

bool comp_touch_gesture_is_horizontal_drag(const comp_touch_gesture_state_t *state)
{
    return state != NULL && state->active &&
           state->locked_axis == TOUCH_AXIS_HORIZONTAL;
}

static void fill_event(const comp_touch_gesture_state_t *state,
                       comp_touch_gesture_type_t type,
                       uint32_t duration_ms,
                       comp_touch_gesture_event_t *out_event)
{
    out_event->type = type;
    out_event->start_x = state->start_x;
    out_event->start_y = state->start_y;
    out_event->end_x = state->latest_x;
    out_event->end_y = state->latest_y;
    out_event->duration_ms = duration_ms > UINT16_MAX ? UINT16_MAX
                                                     : (uint16_t)duration_ms;
}

bool comp_touch_gesture_process(comp_touch_gesture_state_t *state,
                                bool contact,
                                bool explicit_release,
                                uint16_t x,
                                uint16_t y,
                                uint32_t now_ms,
                                comp_touch_gesture_event_t *out_event)
{
    uint32_t duration_ms;
    comp_touch_gesture_type_t released_type;

    if (state == NULL || out_event == NULL) {
        return false;
    }
    memset(out_event, 0, sizeof(*out_event));

    if (state->tap_pending &&
        now_ms - state->last_tap_ms > state->config.double_tap_max_gap_ms) {
        state->tap_pending = false;
    }

    if (state->consumed_until_release) {
        if (contact) {
            state->release_samples = 0u;
            return false;
        }
        if (state->release_samples < UINT8_MAX) {
            state->release_samples++;
        }
        if (state->release_samples >= state->config.release_debounce_samples) {
            state->consumed_until_release = false;
            state->release_samples = 0u;
        }
        return false;
    }

    if (contact) {
        comp_touch_gesture_type_t live_type;

        if (!state->active) {
            state->active = true;
            state->start_x = x;
            state->start_y = y;
            state->start_ms = now_ms;
            state->contact_samples = 0u;
            state->locked_axis = TOUCH_AXIS_UNLOCKED;
            state->hold_feedback_sent = false;
        }
        state->latest_x = x;
        state->latest_y = y;
        if (state->contact_samples < UINT8_MAX) {
            state->contact_samples++;
        }
        update_axis_lock(state);
        state->release_samples = 0u;
        duration_ms = now_ms - state->start_ms;
        if (!state->hold_feedback_sent &&
            state->contact_samples >= state->config.min_contact_samples &&
            duration_ms >= state->config.hold_feedback_min_duration_ms &&
            distance(state->start_x, state->latest_x) <= state->config.long_press_max_move_px &&
            distance(state->start_y, state->latest_y) <= state->config.long_press_max_move_px) {
            fill_event(state, COMP_TOUCH_GESTURE_HOLD, duration_ms, out_event);
            state->hold_feedback_sent = true;
            return true;
        }
        live_type = classify(state, duration_ms);
        /* Horizontal navigation reacts immediately. The menu may observe the
         * vertical axis lock for live scrolling; the final gesture waits for
         * release so it cannot fire a second navigation while dragging. */
        if (is_horizontal_swipe(live_type) ||
            live_type == COMP_TOUCH_GESTURE_LONG_PRESS) {
            fill_event(state, live_type, duration_ms, out_event);
            state->active = false;
            state->consumed_until_release = true;
            state->release_samples = 0u;
            state->tap_pending = false;
            return true;
        }
        return false;
    }

    if (!state->active) {
        return false;
    }
    if (explicit_release) {
        state->latest_x = x;
        state->latest_y = y;
    } else if (++state->release_samples < state->config.release_debounce_samples) {
        return false;
    }

    duration_ms = now_ms - state->start_ms;
    released_type = classify(state, duration_ms);
    fill_event(state, released_type, duration_ms, out_event);
    if (released_type == COMP_TOUCH_GESTURE_TAP) {
        if (state->tap_pending &&
            now_ms - state->last_tap_ms <= state->config.double_tap_max_gap_ms &&
            distance(state->start_x, state->last_tap_x) <=
                state->config.double_tap_max_move_px &&
            distance(state->start_y, state->last_tap_y) <=
                state->config.double_tap_max_move_px) {
            out_event->type = COMP_TOUCH_GESTURE_DOUBLE_TAP;
            state->tap_pending = false;
        } else {
            state->last_tap_x = state->latest_x;
            state->last_tap_y = state->latest_y;
            state->last_tap_ms = now_ms;
            state->tap_pending = true;
        }
    } else if (released_type != COMP_TOUCH_GESTURE_NONE) {
        state->tap_pending = false;
    }
    state->active = false;
    state->contact_samples = 0u;
    state->release_samples = 0u;
    state->locked_axis = TOUCH_AXIS_UNLOCKED;
    state->hold_feedback_sent = false;
    return out_event->type != COMP_TOUCH_GESTURE_NONE;
}

const char *comp_touch_gesture_name(comp_touch_gesture_type_t type)
{
    switch (type) {
    case COMP_TOUCH_GESTURE_TAP: return "tap";
    case COMP_TOUCH_GESTURE_SWIPE_LEFT: return "swipe_left";
    case COMP_TOUCH_GESTURE_SWIPE_RIGHT: return "swipe_right";
    case COMP_TOUCH_GESTURE_SWIPE_UP: return "swipe_up";
    case COMP_TOUCH_GESTURE_SWIPE_DOWN: return "swipe_down";
    case COMP_TOUCH_GESTURE_HOLD: return "hold";
    case COMP_TOUCH_GESTURE_LONG_PRESS: return "long_press";
    case COMP_TOUCH_GESTURE_DOUBLE_TAP: return "double_tap";
    default: return "none";
    }
}

static bool self_test_swipe(uint16_t start_x,
                            uint16_t start_y,
                            uint16_t end_x,
                            uint16_t end_y,
                            comp_touch_gesture_type_t expected)
{
    comp_touch_gesture_state_t state;
    comp_touch_gesture_event_t event;
    bool recognized;

    comp_touch_gesture_init(&state, NULL);
    if (comp_touch_gesture_process(&state, true, false,
                                   start_x, start_y, 100u, &event)) {
        return false;
    }
    recognized = comp_touch_gesture_process(&state, true, false,
                                            end_x, end_y, 240u, &event);
    if (expected == COMP_TOUCH_GESTURE_SWIPE_LEFT ||
        expected == COMP_TOUCH_GESTURE_SWIPE_RIGHT) {
        if (!recognized || event.type != expected || event.duration_ms != 140u) {
            return false;
        }
        if (comp_touch_gesture_process(&state, false, false,
                                       end_x, end_y, 260u, &event) ||
            comp_touch_gesture_process(&state, false, false,
                                       end_x, end_y, 280u, &event)) {
            return false;
        }
        return !state.consumed_until_release;
    }
    if (recognized ||
        comp_touch_gesture_process(&state, false, false,
                                   end_x, end_y, 260u, &event) ||
        !comp_touch_gesture_process(&state, false, false,
                                    end_x, end_y, 280u, &event)) {
        return false;
    }
    return event.type == expected && event.duration_ms == 180u &&
           !state.consumed_until_release;
}

static bool self_test_responsive_diagonal_swipe(void)
{
    const comp_touch_gesture_config_t config = {
        .tap_max_move_px = 18u,
        .long_press_max_move_px = 44u,
        .swipe_min_move_px = 30u,
        .axis_lock_min_move_px = 10u,
        .axis_slop_px = 4u,
        .tap_max_duration_ms = 700u,
        .swipe_max_duration_ms = 1400u,
        .axis_dominance_percent = 125u,
        .min_contact_samples = 2u,
        .release_debounce_samples = 3u,
    };
    comp_touch_gesture_state_t state;
    comp_touch_gesture_event_t event;

    comp_touch_gesture_init(&state, &config);
    if (comp_touch_gesture_process(&state, true, false,
                                   160u, 105u, 100u, &event) ||
        !comp_touch_gesture_process(&state, true, false,
                                    108u, 76u, 220u, &event) ||
        event.type != COMP_TOUCH_GESTURE_SWIPE_LEFT) {
        return false;
    }
    if (comp_touch_gesture_process(&state, false, false,
                                   0u, 0u, 240u, &event) ||
        comp_touch_gesture_process(&state, true, false,
                                   106u, 74u, 260u, &event) ||
        comp_touch_gesture_process(&state, false, false,
                                   0u, 0u, 280u, &event) ||
        comp_touch_gesture_process(&state, false, false,
                                   0u, 0u, 300u, &event) ||
        comp_touch_gesture_process(&state, false, false,
                                   0u, 0u, 320u, &event)) {
        return false;
    }
    return !state.consumed_until_release;
}

static bool self_test_horizontal_drag_detector(void)
{
    comp_touch_gesture_state_t state;
    comp_touch_gesture_event_t event;

    comp_touch_gesture_init(&state, NULL);
    return !comp_touch_gesture_process(&state, true, false,
                                       120u, 100u, 0u, &event) &&
           !comp_touch_gesture_process(&state, true, false,
                                       100u, 102u, 20u, &event) &&
           comp_touch_gesture_is_horizontal_drag(&state) &&
           !comp_touch_gesture_is_vertical_drag(&state);
}

static bool self_test_one_sample_explicit_release(void)
{
    const comp_touch_gesture_config_t config = {
        .tap_max_move_px = 18u,
        .long_press_max_move_px = 44u,
        .swipe_min_move_px = 30u,
        .axis_lock_min_move_px = 10u,
        .axis_slop_px = 4u,
        .tap_max_duration_ms = 700u,
        .swipe_max_duration_ms = 1400u,
        .axis_dominance_percent = 125u,
        .min_contact_samples = 1u,
        .release_debounce_samples = 3u,
    };
    comp_touch_gesture_state_t state;
    comp_touch_gesture_event_t event;

    comp_touch_gesture_init(&state, &config);
    return !comp_touch_gesture_process(&state, true, false,
                                       100u, 80u, 100u, &event) &&
           comp_touch_gesture_process(&state, false, true,
                                      100u, 80u, 120u, &event) &&
           event.type == COMP_TOUCH_GESTURE_TAP &&
           event.duration_ms == 20u && !state.active &&
           !state.consumed_until_release;
}

static bool self_test_hold_then_long_press_is_live_and_consumed(void)
{
    comp_touch_gesture_state_t state;
    comp_touch_gesture_event_t event;

    comp_touch_gesture_init(&state, NULL);
    if (comp_touch_gesture_process(&state, true, false,
                                   100u, 100u, 0u, &event) ||
        comp_touch_gesture_process(&state, true, false,
                                   126u, 118u, 640u, &event) ||
        !comp_touch_gesture_process(&state, true, false,
                                    127u, 119u, 660u, &event) ||
        event.type != COMP_TOUCH_GESTURE_HOLD || event.duration_ms != 660u ||
        state.consumed_until_release ||
        comp_touch_gesture_process(&state, true, false,
                                   132u, 121u, 2990u, &event) ||
        !comp_touch_gesture_process(&state, true, false,
                                    133u, 122u, 3000u, &event) ||
        event.type != COMP_TOUCH_GESTURE_LONG_PRESS ||
        event.duration_ms != 3000u || !state.consumed_until_release) {
        return false;
    }
    return !comp_touch_gesture_process(&state, false, false,
                                       102u, 101u, 680u, &event) &&
           !comp_touch_gesture_process(&state, false, false,
                                       102u, 101u, 700u, &event) &&
           !state.consumed_until_release;
}

static bool self_test_tap_slop_precedes_drag(void)
{
    const comp_touch_gesture_config_t config = {
        .tap_max_move_px = 24u,
        .long_press_max_move_px = 46u,
        .swipe_min_move_px = 30u,
        .axis_lock_min_move_px = 10u,
        .axis_slop_px = 5u,
        .tap_max_duration_ms = 1100u,
        .swipe_max_duration_ms = 1400u,
        .axis_dominance_percent = 120u,
        .min_contact_samples = 1u,
        .release_debounce_samples = 1u,
    };
    comp_touch_gesture_state_t state;
    comp_touch_gesture_event_t event;

    comp_touch_gesture_init(&state, &config);
    if (comp_touch_gesture_process(&state, true, false,
                                   100u, 100u, 0u, &event) ||
        comp_touch_gesture_process(&state, true, false,
                                   102u, 109u, 20u, &event) ||
        comp_touch_gesture_is_vertical_drag(&state) ||
        !comp_touch_gesture_process(&state, false, true,
                                    102u, 109u, 30u, &event)) {
        return false;
    }
    return event.type == COMP_TOUCH_GESTURE_TAP && event.duration_ms == 30u;
}

static bool self_test_vertical_drag_release(void)
{
    const comp_touch_gesture_config_t config = {
        .tap_max_move_px = 18u,
        .long_press_max_move_px = 44u,
        .swipe_min_move_px = 30u,
        .axis_lock_min_move_px = 10u,
        .axis_slop_px = 4u,
        .tap_max_duration_ms = 700u,
        .swipe_max_duration_ms = 1400u,
        .axis_dominance_percent = 125u,
        .min_contact_samples = 1u,
        .release_debounce_samples = 3u,
    };
    comp_touch_gesture_state_t state;
    comp_touch_gesture_event_t event;

    comp_touch_gesture_init(&state, &config);
    if (comp_touch_gesture_process(&state, true, false,
                                   100u, 160u, 100u, &event) ||
        comp_touch_gesture_process(&state, true, false,
                                   100u, 145u, 120u, &event) ||
        !comp_touch_gesture_is_vertical_drag(&state) ||
        comp_touch_gesture_process(&state, true, false,
                                   100u, 120u, 140u, &event) ||
        comp_touch_gesture_process(&state, false, false,
                                   0u, 0u, 160u, &event) ||
        comp_touch_gesture_process(&state, false, false,
                                   0u, 0u, 180u, &event) ||
        !comp_touch_gesture_process(&state, false, false,
                                    0u, 0u, 200u, &event)) {
        return false;
    }
    return event.type == COMP_TOUCH_GESTURE_SWIPE_UP &&
           event.end_y == 120u && event.duration_ms == 100u &&
           !state.active && !comp_touch_gesture_is_vertical_drag(&state);
}

static bool self_test_expired_drag_rearms_tap(void)
{
    const comp_touch_gesture_config_t config = {
        .tap_max_move_px = 18u,
        .long_press_max_move_px = 44u,
        .swipe_min_move_px = 30u,
        .axis_lock_min_move_px = 10u,
        .axis_slop_px = 4u,
        .tap_max_duration_ms = 700u,
        .swipe_max_duration_ms = 1400u,
        .axis_dominance_percent = 125u,
        .min_contact_samples = 1u,
        .release_debounce_samples = 3u,
    };
    comp_touch_gesture_state_t state;
    comp_touch_gesture_event_t event;

    comp_touch_gesture_init(&state, &config);
    if (comp_touch_gesture_process(&state, true, false,
                                   100u, 160u, 0u, &event) ||
        comp_touch_gesture_process(&state, true, false,
                                   100u, 100u, 100u, &event) ||
        !comp_touch_gesture_is_vertical_drag(&state) ||
        comp_touch_gesture_process(&state, false, false,
                                   0u, 0u, 1500u, &event) ||
        comp_touch_gesture_process(&state, false, false,
                                   0u, 0u, 1520u, &event) ||
        comp_touch_gesture_process(&state, false, false,
                                   0u, 0u, 1540u, &event) ||
        state.active || comp_touch_gesture_is_vertical_drag(&state) ||
        comp_touch_gesture_process(&state, true, false,
                                   80u, 80u, 1600u, &event) ||
        !comp_touch_gesture_process(&state, false, true,
                                    80u, 80u, 1620u, &event)) {
        return false;
    }
    return event.type == COMP_TOUCH_GESTURE_TAP && event.duration_ms == 20u;
}

static bool self_test_double_tap(void)
{
    comp_touch_gesture_state_t state;
    comp_touch_gesture_event_t event;

    comp_touch_gesture_init(&state, NULL);
    if (comp_touch_gesture_process(&state, true, false,
                                   100u, 90u, 0u, &event) ||
        comp_touch_gesture_process(&state, true, false,
                                   101u, 90u, 20u, &event) ||
        !comp_touch_gesture_process(&state, false, true,
                                    101u, 90u, 60u, &event) ||
        event.type != COMP_TOUCH_GESTURE_TAP || !state.tap_pending ||
        comp_touch_gesture_process(&state, true, false,
                                   111u, 98u, 180u, &event) ||
        comp_touch_gesture_process(&state, true, false,
                                   112u, 98u, 200u, &event) ||
        !comp_touch_gesture_process(&state, false, true,
                                    112u, 98u, 230u, &event)) {
        return false;
    }
    return event.type == COMP_TOUCH_GESTURE_DOUBLE_TAP &&
           event.duration_ms == 50u && !state.tap_pending;
}

bool comp_touch_gesture_self_test(void)
{
    comp_touch_gesture_state_t state;
    comp_touch_gesture_event_t event;

    comp_touch_gesture_init(&state, NULL);
    if (comp_touch_gesture_process(&state, true, false, 100u, 80u, 0u, &event) ||
        comp_touch_gesture_process(&state, true, false, 102u, 81u, 10u, &event) ||
        comp_touch_gesture_process(&state, false, false, 0u, 0u, 20u, &event) ||
        !comp_touch_gesture_process(&state, false, false, 0u, 0u, 40u, &event) ||
        event.type != COMP_TOUCH_GESTURE_TAP) {
        return false;
    }
    return self_test_tap_slop_precedes_drag() &&
           self_test_swipe(115u, 77u, 115u, 140u,
                           COMP_TOUCH_GESTURE_SWIPE_DOWN) &&
           self_test_swipe(115u, 140u, 115u, 77u,
                           COMP_TOUCH_GESTURE_SWIPE_UP) &&
           self_test_swipe(150u, 100u, 80u, 100u,
                           COMP_TOUCH_GESTURE_SWIPE_LEFT) &&
           self_test_swipe(80u, 100u, 150u, 100u,
                           COMP_TOUCH_GESTURE_SWIPE_RIGHT) &&
           self_test_responsive_diagonal_swipe() &&
           self_test_horizontal_drag_detector() &&
           self_test_one_sample_explicit_release() &&
           self_test_hold_then_long_press_is_live_and_consumed() &&
           self_test_vertical_drag_release() &&
           self_test_expired_drag_rearms_tap() &&
           self_test_double_tap();
}
