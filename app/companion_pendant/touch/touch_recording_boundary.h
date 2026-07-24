#ifndef COMPANION_TOUCH_RECORDING_BOUNDARY_H
#define COMPANION_TOUCH_RECORDING_BOUNDARY_H

#include "../recording/recording_fsm.h"
#include "touch_gesture.h"
#include "touch_visual_decision.h"

#include <stdbool.h>
#include <stdint.h>

typedef enum {
    COMP_TOUCH_RECORDING_ACTION_NONE = 0u,
    COMP_TOUCH_RECORDING_ACTION_TOGGLE = 1u,
} comp_touch_recording_action_t;

typedef bool (*comp_touch_recording_execute_fn)(
    void *context, comp_touch_recording_action_t action,
    comp_recording_state_t state_before);
typedef bool (*comp_touch_recording_menu_fn)(
    void *context, const comp_touch_visual_decision_t *decision,
    const comp_screen_menu_t *menu,
    uint32_t now_ms);

typedef struct {
    comp_touch_recording_execute_fn execute;
    comp_touch_recording_menu_fn menu;
    void *context;
} comp_touch_recording_boundary_sinks_t;

typedef struct {
    comp_touch_recording_boundary_sinks_t sinks;
    comp_touch_recording_action_t queue[2];
    uint8_t queue_count;
    uint32_t submitted;
    uint32_t deduplicated;
    uint32_t executed;
    uint32_t failed;
} comp_touch_recording_boundary_t;

void comp_touch_recording_boundary_init(
    comp_touch_recording_boundary_t *boundary,
    const comp_touch_recording_boundary_sinks_t *sinks);

bool comp_touch_recording_boundary_submit(
    comp_touch_recording_boundary_t *boundary,
    const comp_touch_gesture_event_t *gesture,
    comp_recording_state_t state,
    bool menu_visible,
    uint32_t now_ms);

bool comp_touch_recording_boundary_dispatch(
    comp_touch_recording_boundary_t *boundary,
    const comp_touch_visual_decision_t *decision,
    bool menu_visible,
    const comp_screen_menu_t *menu,
    comp_recording_state_t state,
    uint32_t now_ms);

bool comp_touch_recording_boundary_service(
    comp_touch_recording_boundary_t *boundary,
    comp_recording_state_t state);

uint8_t comp_touch_recording_boundary_pending(
    const comp_touch_recording_boundary_t *boundary);

#endif
