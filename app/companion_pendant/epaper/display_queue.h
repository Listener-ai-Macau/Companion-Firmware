#ifndef COMPANION_EPAPER_DISPLAY_QUEUE_H
#define COMPANION_EPAPER_DISPLAY_QUEUE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "expression_state.h"

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_EPAPER_DISPLAY_QUEUE_DEPTH 4u
#define COMP_EPAPER_DISPLAY_PAYLOAD_MAX_BYTES 236u
#define COMP_EPAPER_DISPLAY_FLAG_AUTO_MOTION 0x8000u
#define COMP_EPAPER_DISPLAY_FLAG_NATURAL_BLINK_CLOSED 0x4000u
#define COMP_EPAPER_DISPLAY_FLAG_CHARGER_PRESENT 0x2000u
#define COMP_EPAPER_DISPLAY_FLAG_AUTO_ACCESSORY 0x1000u
#define COMP_EPAPER_DISPLAY_FLAG_NATURAL_BLINK_FRAME 0x0800u
#define COMP_EPAPER_DISPLAY_FLAG_AUX_FRAME_INDEX_MASK 0x07FFu
/* Internal expression request that repaints runtime status from the committed
 * glass baseline instead of loading a possibly stale authored face frame. */
#define COMP_EPAPER_DISPLAY_STATUS_BAR_CARD_SLOT 0xFEu

typedef enum {
    COMP_EPAPER_DISPLAY_QUEUE_OK = 0,
    COMP_EPAPER_DISPLAY_QUEUE_FULL = 1,
    COMP_EPAPER_DISPLAY_QUEUE_PAYLOAD_TOO_LONG = 2,
    COMP_EPAPER_DISPLAY_QUEUE_BAD_ARGUMENT = 3,
    COMP_EPAPER_DISPLAY_QUEUE_UNSUPPORTED_EXPRESSION = 4,
    COMP_EPAPER_DISPLAY_QUEUE_BOUNDARY_OWNS_DISPLAY = 5,
} comp_epaper_display_queue_result_t;

typedef enum {
    COMP_EPAPER_RENDER_STATE_IDLE = 0,
    COMP_EPAPER_RENDER_STATE_ACCEPTED = 1,
    COMP_EPAPER_RENDER_STATE_RENDERED = 2,
    COMP_EPAPER_RENDER_STATE_FAILED = 3,
    COMP_EPAPER_RENDER_STATE_BUSY = 4,
} comp_epaper_render_state_t;

typedef enum {
    COMP_EPAPER_DISPLAY_REQUEST_CARD_WRITE = 0,
    COMP_EPAPER_DISPLAY_REQUEST_EXPRESSION = 1,
    COMP_EPAPER_DISPLAY_REQUEST_MENU = 2,
} comp_epaper_display_request_kind_t;

typedef enum {
    COMP_EPAPER_DISPLAY_CLASS_BASE = 0,
    COMP_EPAPER_DISPLAY_CLASS_TOUCH = 1,
    COMP_EPAPER_DISPLAY_CLASS_ACCESSORY = 2,
    COMP_EPAPER_DISPLAY_CLASS_RECORDING = 3,
} comp_epaper_display_class_t;

typedef enum {
    COMP_EPAPER_REFRESH_AUTO = 0,
    COMP_EPAPER_REFRESH_FULL = 1,
    COMP_EPAPER_REFRESH_PARTIAL = 2,
    COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE = 3,
    /* Explicit noninteractive visual boundary; restores contrast once. */
    COMP_EPAPER_REFRESH_MAINTENANCE = 4,
    /* Legacy explicit full intent; product aliases it to the accepted fast boundary. */
    COMP_EPAPER_REFRESH_VISIBLE_FULL = 5,
    /* Idle entry only: strong-clean target before the panel enters deep sleep. */
    COMP_EPAPER_REFRESH_IDLE_ENTER_STRONG = 6,
} comp_epaper_refresh_mode_t;

typedef struct {
    uint32_t sequence;
    uint32_t request_id;
    uint32_t content_crc32;
    uint32_t resource_revision;
    uint32_t asset_state_hash;
    uint32_t recording_overlay_state_hash;
    uint16_t display_flags;
    uint16_t utf8_title_len;
    uint16_t utf8_body_len;
    uint16_t payload_len;
    uint8_t card_slot;
    uint8_t request_kind;
    uint8_t expression;
    uint8_t expression_signal;
    uint8_t expression_priority;
    uint8_t menu_view;
    uint8_t menu_flags;
    uint8_t menu_language;
    uint8_t menu_page;
    uint8_t refresh_mode;
    uint8_t asset_frame_valid;
    uint8_t charger_frame_index;
    uint8_t recording_overlay_present;
    uint8_t recording_overlay_only;
    uint8_t display_class;
    uint16_t asset_frame_index;
    uint16_t recording_overlay_frame_index;
    uint16_t dirty_x;
    uint16_t dirty_y;
    uint16_t dirty_width;
    uint16_t dirty_height;
    uint8_t payload[COMP_EPAPER_DISPLAY_PAYLOAD_MAX_BYTES];
} comp_epaper_display_request_t;

typedef struct {
    comp_epaper_display_request_t items[COMP_EPAPER_DISPLAY_QUEUE_DEPTH];
    size_t read_index;
    size_t write_index;
    size_t count;
    size_t high_water_count;
    uint32_t next_sequence;
    uint32_t dropped_count;
    uint32_t active_resource_revision;
    uint32_t generation_switch_count;
    uint32_t last_stale_generation_discarded;
    uint32_t stale_generation_discard_count;
    uint32_t boundary_rejected_count;
    uint32_t boundary_in_flight_request_id;
} comp_epaper_display_queue_t;

typedef struct {
    size_t pending_count;
    size_t high_water_count;
    size_t queue_depth;
    size_t payload_max_bytes;
    uint32_t next_sequence;
    uint32_t dropped_count;
    uint32_t active_resource_revision;
    uint32_t generation_switch_count;
    uint32_t last_stale_generation_discarded;
    uint32_t stale_generation_discard_count;
    uint32_t boundary_rejected_count;
    uint32_t boundary_in_flight_request_id;
} comp_epaper_display_queue_snapshot_t;

void comp_epaper_display_queue_init(comp_epaper_display_queue_t *queue);
void comp_epaper_display_queue_set_resource_revision(
    comp_epaper_display_queue_t *queue,
    uint32_t resource_revision);

comp_epaper_display_queue_result_t comp_epaper_display_queue_enqueue_card_write(
    comp_epaper_display_queue_t *queue,
    uint8_t card_slot,
    uint16_t display_flags,
    uint32_t request_id,
    uint16_t utf8_title_len,
    uint16_t utf8_body_len,
    const uint8_t *payload,
    uint16_t payload_len,
    uint32_t content_crc32);

comp_epaper_display_queue_result_t comp_epaper_display_queue_enqueue_expression(
    comp_epaper_display_queue_t *queue,
    uint8_t card_slot,
    uint16_t display_flags,
    uint32_t request_id,
    const comp_epaper_expression_decision_t *decision,
    uint32_t content_crc32);

comp_epaper_display_queue_result_t comp_epaper_display_queue_enqueue_expression_frame(
    comp_epaper_display_queue_t *queue,
    uint8_t card_slot,
    uint16_t display_flags,
    uint8_t charger_frame_index,
    uint32_t request_id,
    const comp_epaper_expression_decision_t *decision,
    uint16_t frame_index,
    comp_epaper_refresh_mode_t refresh_mode,
    uint16_t dirty_x,
    uint16_t dirty_y,
    uint16_t dirty_width,
    uint16_t dirty_height,
    uint32_t content_crc32);

comp_epaper_display_queue_result_t
comp_epaper_display_queue_enqueue_expression_frame_with_recording_overlay(
    comp_epaper_display_queue_t *queue,
    uint8_t card_slot,
    uint16_t display_flags,
    uint8_t charger_frame_index,
    bool recording_overlay_present,
    bool recording_overlay_only,
    uint16_t recording_overlay_frame_index,
    uint32_t asset_state_hash,
    uint32_t recording_overlay_state_hash,
    comp_epaper_display_class_t display_class,
    uint32_t request_id,
    const comp_epaper_expression_decision_t *decision,
    uint16_t frame_index,
    comp_epaper_refresh_mode_t refresh_mode,
    uint16_t dirty_x,
    uint16_t dirty_y,
    uint16_t dirty_width,
    uint16_t dirty_height,
    uint32_t content_crc32);

comp_epaper_display_queue_result_t comp_epaper_display_queue_enqueue_menu(
    comp_epaper_display_queue_t *queue,
    uint8_t card_slot,
    uint32_t request_id,
    uint8_t menu_view,
    uint8_t menu_flags,
    uint8_t menu_language,
    uint8_t menu_page,
    comp_epaper_refresh_mode_t refresh_mode,
    uint32_t content_crc32);

bool comp_epaper_display_queue_dequeue(comp_epaper_display_queue_t *queue,
                                       comp_epaper_display_request_t *out_request);
bool comp_epaper_display_queue_complete(
    comp_epaper_display_queue_t *queue,
    uint32_t request_id);
bool comp_epaper_display_request_is_boundary(
    const comp_epaper_display_request_t *request);
bool comp_epaper_display_queue_boundary_owned(
    const comp_epaper_display_queue_t *queue);

size_t comp_epaper_display_queue_discard_kind(
    comp_epaper_display_queue_t *queue,
    comp_epaper_display_request_kind_t request_kind);
size_t comp_epaper_display_queue_discard_display_flags(
    comp_epaper_display_queue_t *queue,
    uint16_t required_flags);
size_t comp_epaper_display_queue_discard_display_class(
    comp_epaper_display_queue_t *queue,
    comp_epaper_display_class_t display_class);

void comp_epaper_display_queue_snapshot(const comp_epaper_display_queue_t *queue,
                                        comp_epaper_display_queue_snapshot_t *out_snapshot);
size_t comp_epaper_display_queue_pending(const comp_epaper_display_queue_t *queue);
size_t comp_epaper_display_queue_high_water_count(const comp_epaper_display_queue_t *queue);
uint32_t comp_epaper_display_queue_dropped_count(const comp_epaper_display_queue_t *queue);
uint32_t comp_epaper_display_queue_active_resource_revision(const comp_epaper_display_queue_t *queue);
uint32_t comp_epaper_display_queue_generation_switch_count(const comp_epaper_display_queue_t *queue);
uint32_t comp_epaper_display_queue_last_stale_generation_discarded(const comp_epaper_display_queue_t *queue);
uint32_t comp_epaper_display_queue_stale_generation_discard_count(const comp_epaper_display_queue_t *queue);
uint8_t comp_epaper_display_queue_status_error(comp_epaper_display_queue_result_t result);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_DISPLAY_QUEUE_H */
