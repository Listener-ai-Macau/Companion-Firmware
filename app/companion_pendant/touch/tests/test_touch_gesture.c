#include "touch_gesture.h"

#include <stdbool.h>
#include <stdio.h>

#define CHECK(condition, message)                                              \
    do {                                                                       \
        if (!(condition)) {                                                    \
            fprintf(stderr, "FAIL: %s (line %d)\n", message, __LINE__);       \
            return false;                                                      \
        }                                                                      \
    } while (0)

static bool replay_wb55_double_tap_boundary(void)
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
    comp_touch_gesture_state_t state;
    comp_touch_gesture_event_t event;

    comp_touch_gesture_init(&state, &config);
    CHECK(!comp_touch_gesture_process(&state, true, false,
                                      95u, 128u, 100u, &event),
          "first DOWN must remain active");
    CHECK(!comp_touch_gesture_process(&state, true, false,
                                      105u, 122u, 120u, &event),
          "first CONTACT must remain active");
    CHECK(comp_touch_gesture_restart_contact(&state,
                                             110u, 127u, 168u, &event),
          "missing-release boundary must finish the first tap");
    CHECK(event.type == COMP_TOUCH_GESTURE_TAP,
          "first boundary must emit a provisional tap");
    CHECK(!comp_touch_gesture_process(&state, true, false,
                                      110u, 127u, 180u, &event),
          "second CONTACT must remain active");
    CHECK(comp_touch_gesture_restart_contact(&state,
                                             109u, 129u, 232u, &event),
          "second boundary must complete double tap");
    CHECK(event.type == COMP_TOUCH_GESTURE_DOUBLE_TAP,
          "captured WB55 sequence must emit double tap");
    CHECK(!state.active && state.consumed_until_release && !state.tap_pending,
          "double-tap boundary DOWN must not arm a phantom third contact");

    CHECK(!comp_touch_gesture_process(&state, true, false,
                                      109u, 129u, 260u, &event),
          "repeated contact after double tap must stay consumed");
    CHECK(state.consumed_until_release,
          "repeated contact must not re-arm long press");
    CHECK(!comp_touch_gesture_process(&state, false, false,
                                      0u, 0u, 4535u, &event),
          "late release must only clear the consumed contact");
    CHECK(!state.active && !state.consumed_until_release &&
              event.type == COMP_TOUCH_GESTURE_NONE,
          "4303 ms delayed release must not become menu long press");
    return true;
}

int main(void)
{
    if (!comp_touch_gesture_self_test()) {
        fprintf(stderr, "FAIL: embedded touch gesture self-test\n");
        return 1;
    }
    if (!replay_wb55_double_tap_boundary()) {
        return 1;
    }
    puts("PASS: WB55 double-tap boundary replay produced one double tap and no phantom long press.");
    return 0;
}
