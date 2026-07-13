#ifndef COMPANION_TOUCH_GESTURE_H
#define COMPANION_TOUCH_GESTURE_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    COMP_TOUCH_GESTURE_NONE = 0u,
    COMP_TOUCH_GESTURE_TAP = 1u,
    COMP_TOUCH_GESTURE_SWIPE_LEFT = 2u,
    COMP_TOUCH_GESTURE_SWIPE_RIGHT = 3u,
    COMP_TOUCH_GESTURE_SWIPE_UP = 4u,
    COMP_TOUCH_GESTURE_SWIPE_DOWN = 5u,
    /* A short, non-consuming hold lets a product acknowledge the finger. */
    COMP_TOUCH_GESTURE_HOLD = 6u,
    /* Reported while contact is still held once the deliberate hold completes. */
    COMP_TOUCH_GESTURE_LONG_PRESS = 7u,
    /* The second short tap stays responsive while providing a distinct action. */
    COMP_TOUCH_GESTURE_DOUBLE_TAP = 8u,
} comp_touch_gesture_type_t;

typedef struct {
    uint16_t tap_max_move_px;
    uint16_t long_press_max_move_px;
    uint16_t swipe_min_move_px;
    uint16_t axis_lock_min_move_px;
    uint16_t axis_slop_px;
    uint16_t tap_max_duration_ms;
    uint16_t swipe_max_duration_ms;
    uint16_t hold_feedback_min_duration_ms;
    uint16_t long_press_min_duration_ms;
    uint16_t double_tap_max_gap_ms;
    uint16_t double_tap_max_move_px;
    uint8_t axis_dominance_percent;
    uint8_t min_contact_samples;
    uint8_t release_debounce_samples;
} comp_touch_gesture_config_t;

typedef struct {
    comp_touch_gesture_type_t type;
    uint16_t start_x;
    uint16_t start_y;
    uint16_t end_x;
    uint16_t end_y;
    uint16_t duration_ms;
} comp_touch_gesture_event_t;

typedef struct {
    comp_touch_gesture_config_t config;
    uint16_t start_x;
    uint16_t start_y;
    uint16_t latest_x;
    uint16_t latest_y;
    uint16_t last_tap_x;
    uint16_t last_tap_y;
    uint32_t start_ms;
    uint32_t last_tap_ms;
    uint8_t contact_samples;
    uint8_t release_samples;
    uint8_t locked_axis;
    bool hold_feedback_sent;
    bool active;
    bool consumed_until_release;
    bool tap_pending;
} comp_touch_gesture_state_t;

void comp_touch_gesture_init(comp_touch_gesture_state_t *state,
                             const comp_touch_gesture_config_t *config);
bool comp_touch_gesture_process(comp_touch_gesture_state_t *state,
                                bool contact,
                                bool explicit_release,
                                uint16_t x,
                                uint16_t y,
                                uint32_t now_ms,
                                comp_touch_gesture_event_t *out_event);
bool comp_touch_gesture_is_vertical_drag(const comp_touch_gesture_state_t *state);
const char *comp_touch_gesture_name(comp_touch_gesture_type_t type);
bool comp_touch_gesture_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_TOUCH_GESTURE_H */
