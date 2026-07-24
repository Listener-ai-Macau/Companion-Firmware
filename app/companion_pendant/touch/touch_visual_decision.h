#ifndef COMPANION_TOUCH_VISUAL_DECISION_H
#define COMPANION_TOUCH_VISUAL_DECISION_H

#include <stdbool.h>
#include <stdint.h>

#include "ft6336.h"
#include "touch_gesture.h"
#include "screen_menu.h"
#include "companion_visual_asset_pack.h"

#ifdef __cplusplus
extern "C" {
#endif

/* The panel is calibrated in the same 200x200 logical target space used by
 * the upper contract.  These partitions are deliberately independent of the
 * finger's start point, so returning to the calibrated center is observable. */
#define COMP_TOUCH_VISUAL_CENTER_MIN_X 75u
#define COMP_TOUCH_VISUAL_CENTER_MAX_X 124u
#define COMP_TOUCH_VISUAL_CENTER_MIN_Y 75u
#define COMP_TOUCH_VISUAL_CENTER_MAX_Y 124u

typedef struct {
    bool gesture_ready;
    bool cancellation;
    bool ui_assets_selected;
    comp_touch_gesture_event_t gesture;
    comp_screen_menu_result_t menu_result;
    companion_visual_event_t visual_event;
    uint8_t visual_target_state;
    uint8_t visual_from_state;
    bool visual_event_valid;
} comp_touch_visual_decision_t;

typedef struct {
    uint8_t current_visual_state;
    bool cancellation_emitted;
} comp_touch_visual_runtime_t;

typedef bool (*comp_touch_visual_event_sink_t)(
    void *context, companion_visual_event_t event, uint32_t elapsed_ms,
    uint16_t move_px, uint8_t target_state);
typedef void (*comp_touch_visual_route_sink_t)(
    void *context, const comp_screen_menu_result_t *result);
typedef void (*comp_touch_visual_render_sink_t)(
    void *context, const comp_screen_menu_t *menu);
typedef void (*comp_touch_visual_frame_sink_t)(
    void *context, uint8_t from_state, uint8_t to_state,
    uint32_t previous_hash, uint32_t current_hash);

typedef struct {
    comp_touch_visual_event_sink_t event;
    comp_touch_visual_route_sink_t route;
    comp_touch_visual_render_sink_t render;
    comp_touch_visual_frame_sink_t frame;
    void *context;
} comp_touch_visual_sinks_t;

typedef enum {
    COMP_TOUCH_VISUAL_CANCEL_RELEASE = 0u,
    COMP_TOUCH_VISUAL_CANCEL_DRAG = 1u,
    COMP_TOUCH_VISUAL_CANCEL_TRANSPORT_BLUR = 2u,
    COMP_TOUCH_VISUAL_CANCEL_RECORDING_RETURN = 3u,
    COMP_TOUCH_VISUAL_CANCEL_SETTLE = 4u,
} comp_touch_visual_cancel_kind_t;

bool comp_touch_visual_process_raw(
    const comp_ft6336_touch_sample_t *sample,
    uint16_t logical_x,
    uint16_t logical_y,
    uint32_t now_ms,
    comp_touch_gesture_state_t *gesture_state,
    comp_touch_visual_runtime_t *runtime,
    comp_touch_visual_decision_t *decision);

bool comp_touch_visual_apply_menu(
    comp_screen_menu_t *menu,
    comp_touch_visual_decision_t *decision);

bool comp_touch_visual_emit_decision(
    const comp_touch_visual_decision_t *decision,
    const comp_screen_menu_t *menu,
    const comp_touch_visual_sinks_t *sinks);

bool comp_touch_visual_cancel(
    comp_touch_gesture_state_t *gesture_state,
    comp_touch_visual_runtime_t *runtime,
    comp_touch_visual_cancel_kind_t kind,
    comp_touch_visual_decision_t *decision);

uint8_t comp_touch_visual_target_partition(uint16_t logical_x,
                                           uint16_t logical_y);

const char *comp_touch_visual_event_name(companion_visual_event_t event);

#ifdef __cplusplus
}
#endif

#endif
