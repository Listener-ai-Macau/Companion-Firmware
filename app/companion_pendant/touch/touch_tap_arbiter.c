#include "touch_tap_arbiter.h"

#include "touch_gesture.h"

#include <string.h>

void comp_touch_tap_arbiter_init(comp_touch_tap_arbiter_t *arbiter,
                                 uint16_t confirmation_window_ms)
{
    if (arbiter == NULL) {
        return;
    }
    memset(arbiter, 0, sizeof(*arbiter));
    arbiter->confirmation_window_ms = confirmation_window_ms;
}

void comp_touch_tap_arbiter_defer(comp_touch_tap_arbiter_t *arbiter,
                                  uint16_t x,
                                  uint16_t y,
                                  uint32_t now_ms)
{
    if (arbiter == NULL) {
        return;
    }
    arbiter->pending = true;
    arbiter->x = x;
    arbiter->y = y;
    arbiter->due_ms = now_ms + arbiter->confirmation_window_ms + 1u;
}

void comp_touch_tap_arbiter_cancel(comp_touch_tap_arbiter_t *arbiter)
{
    if (arbiter != NULL) {
        arbiter->pending = false;
    }
}

bool comp_touch_tap_arbiter_poll(comp_touch_tap_arbiter_t *arbiter,
                                 uint32_t now_ms,
                                 bool contact_active,
                                 bool detector_tap_pending,
                                 comp_touch_tap_arbiter_event_t *event)
{
    if (arbiter == NULL || event == NULL || !arbiter->pending ||
        (int32_t)(now_ms - arbiter->due_ms) < 0 ||
        contact_active || detector_tap_pending) {
        return false;
    }

    event->x = arbiter->x;
    event->y = arbiter->y;
    arbiter->pending = false;
    return true;
}

static bool self_test_confirmed_single_tap(void)
{
    comp_touch_tap_arbiter_t arbiter;
    comp_touch_tap_arbiter_event_t event = {0};

    comp_touch_tap_arbiter_init(&arbiter, 650u);
    comp_touch_tap_arbiter_defer(&arbiter, 42u, 84u, 100u);
    if (comp_touch_tap_arbiter_poll(&arbiter, 750u, false, false, &event) ||
        comp_touch_tap_arbiter_poll(&arbiter, 751u, false, true, &event) ||
        !comp_touch_tap_arbiter_poll(&arbiter, 752u, false, false, &event)) {
        return false;
    }
    return event.x == 42u && event.y == 84u && !arbiter.pending;
}

static bool self_test_captured_recontact_double_tap(void)
{
    const comp_touch_gesture_config_t config = {
        .tap_max_move_px = 24u,
        .long_press_max_move_px = 46u,
        .swipe_min_move_px = 30u,
        .axis_lock_min_move_px = 10u,
        .axis_slop_px = 5u,
        .tap_max_duration_ms = 1100u,
        .swipe_max_duration_ms = 1400u,
        .hold_feedback_min_duration_ms = 650u,
        .long_press_min_duration_ms = 3000u,
        .double_tap_max_gap_ms = 650u,
        .double_tap_max_move_px = 40u,
        .axis_dominance_percent = 120u,
        .min_contact_samples = 1u,
        .release_debounce_samples = 1u,
    };
    comp_touch_gesture_state_t gesture;
    comp_touch_gesture_event_t gesture_event;
    comp_touch_tap_arbiter_t arbiter;
    comp_touch_tap_arbiter_event_t tap_event = {0};

    comp_touch_gesture_init(&gesture, &config);
    comp_touch_tap_arbiter_init(&arbiter, config.double_tap_max_gap_ms);

    if (comp_touch_gesture_process(&gesture, true, false,
                                   0u, 159u, 100u, &gesture_event) ||
        !comp_touch_gesture_restart_contact(&gesture,
                                            129u, 81u, 145u,
                                            &gesture_event) ||
        gesture_event.type != COMP_TOUCH_GESTURE_TAP) {
        return false;
    }
    comp_touch_tap_arbiter_defer(&arbiter,
                                 gesture_event.end_x,
                                 gesture_event.end_y,
                                 145u);

    if (comp_touch_gesture_process(&gesture, true, false,
                                   121u, 83u, 250u, &gesture_event) ||
        !comp_touch_gesture_process(&gesture, false, false,
                                    121u, 83u, 298u, &gesture_event) ||
        gesture_event.type != COMP_TOUCH_GESTURE_TAP) {
        return false;
    }
    comp_touch_tap_arbiter_defer(&arbiter,
                                 gesture_event.end_x,
                                 gesture_event.end_y,
                                 298u);

    if (comp_touch_tap_arbiter_poll(&arbiter, 400u, false, true, &tap_event) ||
        comp_touch_gesture_process(&gesture, true, false,
                                   109u, 88u, 400u, &gesture_event) ||
        !comp_touch_gesture_process(&gesture, false, false,
                                    109u, 88u, 450u, &gesture_event) ||
        gesture_event.type != COMP_TOUCH_GESTURE_DOUBLE_TAP) {
        return false;
    }

    comp_touch_tap_arbiter_cancel(&arbiter);
    return !comp_touch_tap_arbiter_poll(&arbiter,
                                        1200u,
                                        false,
                                        false,
                                        &tap_event);
}

bool comp_touch_tap_arbiter_self_test(void)
{
    return self_test_confirmed_single_tap() &&
           self_test_captured_recontact_double_tap();
}
