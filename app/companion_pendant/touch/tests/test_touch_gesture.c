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

static bool replay_two_recording_double_taps(void)
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
    const uint32_t cycle_start_ms[] = { 100u, 1200u };
    comp_touch_gesture_state_t state;
    comp_touch_gesture_event_t event;
    unsigned double_taps = 0u;

    comp_touch_gesture_init(&state, &config);
    for (size_t cycle = 0u;
         cycle < sizeof(cycle_start_ms) / sizeof(cycle_start_ms[0]);
         ++cycle) {
        uint32_t start = cycle_start_ms[cycle];

        CHECK(!comp_touch_gesture_process(&state, true, false,
                                          96u, 104u, start, &event),
              "recording double tap first DOWN must stay active");
        CHECK(comp_touch_gesture_process(&state, false, false,
                                         96u, 104u, start + 80u, &event),
              "recording double tap first release must emit tap");
        CHECK(event.type == COMP_TOUCH_GESTURE_TAP && state.tap_pending,
              "recording first tap must remain provisional");
        CHECK(!comp_touch_gesture_process(&state, true, false,
                                          101u, 108u, start + 230u, &event),
              "recording double tap second DOWN must stay active");
        CHECK(comp_touch_gesture_process(&state, false, false,
                                         101u, 108u, start + 310u, &event),
              "recording double tap second release must complete gesture");
        CHECK(event.type == COMP_TOUCH_GESTURE_DOUBLE_TAP,
              "both start and stop cycles must emit double tap");
        CHECK(!state.active && !state.tap_pending,
              "completed recording double tap must re-arm the next cycle");
        double_taps++;
    }
    CHECK(double_taps == 2u,
          "recording replay must preserve start and stop double taps");
    return true;
}

static bool emit_recording_double_tap(
    comp_touch_gesture_state_t *state,
    uint32_t start_ms,
    comp_touch_gesture_event_t *event)
{
    CHECK(!comp_touch_gesture_process(state, true, false,
                                      96u, 104u, start_ms, event),
          "rapid recording first DOWN must stay active");
    CHECK(comp_touch_gesture_process(state, false, false,
                                     96u, 104u, start_ms + 60u, event),
          "rapid recording first release must emit provisional tap");
    CHECK(event->type == COMP_TOUCH_GESTURE_TAP && state->tap_pending,
          "rapid recording first tap must remain provisional");
    CHECK(!comp_touch_gesture_process(state, true, false,
                                      100u, 107u, start_ms + 150u, event),
          "rapid recording second DOWN must stay active");
    CHECK(comp_touch_gesture_process(state, false, false,
                                     100u, 107u, start_ms + 220u, event),
          "rapid recording second release must complete double tap");
    CHECK(event->type == COMP_TOUCH_GESTURE_DOUBLE_TAP,
          "rapid recording pair must emit exactly one double tap");
    CHECK(!state->active && !state->tap_pending &&
              !state->consumed_until_release,
          "rapid recording pair must immediately re-arm the next toggle");
    return true;
}

static bool replay_rapid_recording_toggle_bursts(void)
{
    const comp_touch_gesture_config_t config = {
        .tap_max_move_px = 24u,
        .long_press_max_move_px = 46u,
        .swipe_min_move_px = 24u,
        .horizontal_swipe_min_move_px = 36u,
        .axis_lock_min_move_px = 10u,
        .axis_slop_px = 5u,
        .tap_max_duration_ms = 1100u,
        .swipe_max_duration_ms = 1400u,
        .hold_feedback_min_duration_ms = 1000u,
        .long_press_min_duration_ms = 3000u,
        .double_tap_max_gap_ms = 350u,
        .double_tap_max_move_px = 32u,
        .axis_dominance_percent = 140u,
        .min_contact_samples = 1u,
        .release_debounce_samples = 1u,
    };
    comp_touch_gesture_state_t state;
    comp_touch_gesture_event_t event;
    uint32_t now_ms = 100u;
    unsigned toggles = 0u;

    comp_touch_gesture_init(&state, &config);
    for (unsigned cycle = 0u; cycle < 1000u; ++cycle) {
        CHECK(emit_recording_double_tap(&state, now_ms, &event),
              "rapid recording entry pair failed");
        toggles++;
        now_ms += 320u;
        CHECK(emit_recording_double_tap(&state, now_ms, &event),
              "rapid pending/active recording exit pair failed");
        toggles++;
        now_ms += 320u;
        CHECK(emit_recording_double_tap(&state, now_ms, &event),
              "rapid recording re-entry pair failed");
        toggles++;
        now_ms += 500u;
    }
    CHECK(toggles == 3000u,
          "rapid recording replay must preserve every toggle");
    CHECK(!state.active && !state.tap_pending &&
              !state.consumed_until_release,
          "rapid recording replay must leave no stuck gesture state");
    return true;
}

static bool replay_independent_browser_swipe_thresholds(void)
{
    const comp_touch_gesture_config_t config = {
        .tap_max_move_px = 24u,
        .long_press_max_move_px = 46u,
        .swipe_min_move_px = 24u,
        .horizontal_swipe_min_move_px = 36u,
        .axis_lock_min_move_px = 10u,
        .axis_slop_px = 5u,
        .tap_max_duration_ms = 1100u,
        .swipe_max_duration_ms = 1400u,
        .hold_feedback_min_duration_ms = 1000u,
        .long_press_min_duration_ms = 3000u,
        .double_tap_max_gap_ms = 350u,
        .double_tap_max_move_px = 32u,
        .axis_dominance_percent = 140u,
        .min_contact_samples = 1u,
        .release_debounce_samples = 2u,
    };
    comp_touch_gesture_state_t state;
    comp_touch_gesture_event_t event;

    comp_touch_gesture_init(&state, &config);
    CHECK(!comp_touch_gesture_process(&state, true, false,
                                      0u, 100u, 100u, &event),
          "right swipe DOWN must remain active");
    CHECK(!comp_touch_gesture_process(&state, true, false,
                                      30u, 100u, 180u, &event),
          "vertical threshold must not consume a short horizontal swipe");
    CHECK(state.active && !state.consumed_until_release,
          "short horizontal swipe must retain later coordinates");
    CHECK(comp_touch_gesture_process(&state, true, false,
                                     36u, 100u, 200u, &event),
          "browser right-exit threshold must classify immediately");
    CHECK(event.type == COMP_TOUCH_GESTURE_SWIPE_RIGHT &&
              event.end_x - event.start_x == 36u,
          "right swipe must preserve the browser threshold displacement");
    return true;
}

static bool replay_browser_mixed_trajectory_matrix(void)
{
    const comp_touch_gesture_config_t config = {
        .tap_max_move_px = 24u,
        .long_press_max_move_px = 46u,
        .swipe_min_move_px = 24u,
        .horizontal_swipe_min_move_px = 36u,
        .axis_lock_min_move_px = 10u,
        .axis_slop_px = 5u,
        .tap_max_duration_ms = 1100u,
        .swipe_max_duration_ms = 1400u,
        .hold_feedback_min_duration_ms = 1000u,
        .long_press_min_duration_ms = 3000u,
        .double_tap_max_gap_ms = 350u,
        .double_tap_max_move_px = 32u,
        .axis_dominance_percent = 140u,
        .min_contact_samples = 1u,
        .release_debounce_samples = 2u,
    };
    uint32_t failed_cycle = 0u;
    comp_touch_gesture_type_t expected = COMP_TOUCH_GESTURE_NONE;
    comp_touch_gesture_type_t actual = COMP_TOUCH_GESTURE_NONE;
    const bool passed = comp_touch_gesture_verify_mixed_replay(
        &config, 1000u, &failed_cycle, &expected, &actual);

    if (!passed) {
        fprintf(stderr,
                "mixed replay failed cycle=%lu expected=%s actual=%s\n",
                (unsigned long)failed_cycle,
                comp_touch_gesture_name(expected),
                comp_touch_gesture_name(actual));
    }
    CHECK(passed,
          "1000 browser mixed trajectories must replay without divergence");
    CHECK(failed_cycle == 1000u &&
              expected == COMP_TOUCH_GESTURE_NONE &&
              actual == COMP_TOUCH_GESTURE_NONE,
          "mixed replay completion receipt must be exact");
    return true;
}

static bool replay_menu_micro_drag_evidence(void)
{
    const comp_touch_gesture_config_t config = {
        .tap_max_move_px = 24u,
        .long_press_max_move_px = 46u,
        .swipe_min_move_px = 24u,
        .horizontal_swipe_min_move_px = 36u,
        .axis_lock_min_move_px = 10u,
        .axis_slop_px = 5u,
        .tap_max_duration_ms = 1100u,
        .swipe_max_duration_ms = 1400u,
        .double_tap_max_gap_ms = 350u,
        .double_tap_max_move_px = 32u,
        .axis_dominance_percent = 140u,
        .min_contact_samples = 1u,
        .release_debounce_samples = 1u,
    };
    comp_touch_gesture_state_t state;
    comp_touch_gesture_event_t event;

    comp_touch_gesture_init(&state, &config);
    CHECK(!comp_touch_gesture_process(&state, true, false,
                                      159u, 170u, 100u, &event),
          "menu micro-drag DOWN must remain active");
    CHECK(!comp_touch_gesture_process(&state, true, false,
                                      159u, 150u, 250u, &event),
          "20 px menu micro-drag must await release");
    CHECK(comp_touch_gesture_process(&state, false, true,
                                     159u, 150u, 280u, &event),
          "menu micro-drag release must remain machine-observable");
    CHECK(event.type == COMP_TOUCH_GESTURE_TAP,
          "global 24 px policy should expose the historical false tap");
    CHECK(state.max_excursion_x == 0u && state.max_excursion_y == 20u,
          "release must preserve excursion for the stricter menu gate");
    CHECK(!comp_touch_gesture_process(&state, true, false,
                                      100u, 100u, 500u, &event),
          "next menu contact must start normally");
    CHECK(state.max_excursion_x == 0u && state.max_excursion_y == 0u,
          "next DOWN must reset preserved excursion");
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
    if (!replay_two_recording_double_taps()) {
        return 1;
    }
    if (!replay_rapid_recording_toggle_bursts()) {
        return 1;
    }
    if (!replay_independent_browser_swipe_thresholds()) {
        return 1;
    }
    if (!replay_browser_mixed_trajectory_matrix()) {
        return 1;
    }
    if (!replay_menu_micro_drag_evidence()) {
        return 1;
    }
    puts("PASS: WB55 replay produced recording start/stop double taps with no phantom long press.");
    return 0;
}
