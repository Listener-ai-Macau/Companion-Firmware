#ifndef COMPANION_VISUAL_RUNTIME_ADAPTER_H
#define COMPANION_VISUAL_RUNTIME_ADAPTER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "touch_gesture.h"
#include "companion_visual_asset_pack.h"

#define COMPANION_VISUAL_RUNTIME_RING_CAPACITY 32u

typedef enum {
    COMPANION_VISUAL_RUNTIME_EVENT_GAZE = 0,
    COMPANION_VISUAL_RUNTIME_EVENT_TAP = 1,
    COMPANION_VISUAL_RUNTIME_EVENT_RECORDING = 2,
    COMPANION_VISUAL_RUNTIME_EVENT_MENU = 3,
} companion_visual_runtime_event_kind_t;

typedef struct {
    companion_visual_runtime_event_kind_t kind;
    uint8_t state;
    uint32_t sequence;
} companion_visual_runtime_event_t;

typedef struct {
    uint8_t x_byte_start;
    uint8_t x_byte_end;
    uint16_t y_start;
    uint16_t y_end;
    uint16_t payload_bytes;
    bool full_frame_menu;
    uint8_t payload[5000];
} companion_visual_runtime_window_t;

typedef bool (*companion_visual_runtime_transport_fn)(void *context,
                                                       uint8_t command,
                                                       const uint8_t *data,
                                                       uint16_t length);

typedef struct {
    uint8_t current_state;
    companion_visual_runtime_event_t ring[COMPANION_VISUAL_RUNTIME_RING_CAPACITY];
    uint8_t ring_head;
    uint8_t ring_count;
    uint32_t next_sequence;
    uint32_t serviced_events;
    uint32_t failed_events;
    bool terminal_fault;
} companion_visual_runtime_t;

void companion_visual_runtime_init(companion_visual_runtime_t *runtime);
bool companion_visual_runtime_enqueue(companion_visual_runtime_t *runtime,
                                      companion_visual_runtime_event_kind_t kind,
                                      uint8_t state);
bool companion_visual_runtime_enqueue_gesture(
    companion_visual_runtime_t *runtime,
    comp_touch_gesture_type_t gesture,
    uint32_t elapsed_ms,
    uint16_t move_px,
    uint8_t gaze_state);
bool companion_visual_runtime_enqueue_visual_event(
    companion_visual_runtime_t *runtime,
    companion_visual_event_t event,
    uint32_t elapsed_ms,
    uint16_t move_px,
    uint32_t gap_ms,
    bool contact_active,
    uint8_t target_state);
bool companion_visual_runtime_pop(companion_visual_runtime_t *runtime,
                                  companion_visual_runtime_event_t *event);
bool companion_visual_runtime_peek(const companion_visual_runtime_t *runtime,
                                   companion_visual_runtime_event_t *event);
bool companion_visual_runtime_discard(companion_visual_runtime_t *runtime);
bool companion_visual_runtime_frames_equal(const uint8_t *previous,
                                           const uint8_t *current);
bool companion_visual_runtime_copy_panel_frame(companion_visual_state_t state,
                                               uint8_t *panel_frame,
                                               size_t panel_frame_bytes);
bool companion_visual_runtime_build_window(const uint8_t *previous,
                                           const uint8_t *current,
                                           uint8_t from_state,
                                           uint8_t to_state,
                                           companion_visual_runtime_window_t *window);
bool companion_visual_runtime_emit_window(const companion_visual_runtime_window_t *window,
                                          companion_visual_runtime_transport_fn transport,
                                          void *context);
bool companion_visual_runtime_service(
    companion_visual_runtime_t *runtime,
    companion_visual_runtime_transport_fn transport,
    void *context);
bool companion_visual_runtime_has_terminal_fault(
    const companion_visual_runtime_t *runtime);
bool companion_visual_runtime_map_touch(comp_touch_gesture_type_t gesture,
                                        uint32_t elapsed_ms,
                                        uint16_t move_px,
                                        uint8_t gaze_state,
                                        uint8_t *visual_state);

#endif
