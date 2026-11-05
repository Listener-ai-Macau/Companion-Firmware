#ifndef COMPANION_TOUCH_TAP_ARBITER_H
#define COMPANION_TOUCH_TAP_ARBITER_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    bool pending;
    uint16_t x;
    uint16_t y;
    uint16_t confirmation_window_ms;
    uint32_t due_ms;
} comp_touch_tap_arbiter_t;

typedef struct {
    uint16_t x;
    uint16_t y;
} comp_touch_tap_arbiter_event_t;

void comp_touch_tap_arbiter_init(comp_touch_tap_arbiter_t *arbiter,
                                 uint16_t confirmation_window_ms);
void comp_touch_tap_arbiter_defer(comp_touch_tap_arbiter_t *arbiter,
                                  uint16_t x,
                                  uint16_t y,
                                  uint32_t now_ms);
void comp_touch_tap_arbiter_cancel(comp_touch_tap_arbiter_t *arbiter);
bool comp_touch_tap_arbiter_poll(comp_touch_tap_arbiter_t *arbiter,
                                 uint32_t now_ms,
                                 bool contact_active,
                                 bool detector_tap_pending,
                                 comp_touch_tap_arbiter_event_t *event);
bool comp_touch_tap_arbiter_self_test(void);

#endif
