#ifndef COMPANION_EPAPER_DISPLAY_QUEUE_H
#define COMPANION_EPAPER_DISPLAY_QUEUE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "expression_state.h"
#include "pet_expression.h"

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_EPAPER_DISPLAY_QUEUE_DEPTH 4u
#define COMP_EPAPER_DISPLAY_PAYLOAD_MAX_BYTES 236u

typedef enum {
    COMP_EPAPER_DISPLAY_QUEUE_OK = 0,
    COMP_EPAPER_DISPLAY_QUEUE_FULL = 1,
    COMP_EPAPER_DISPLAY_QUEUE_PAYLOAD_TOO_LONG = 2,
    COMP_EPAPER_DISPLAY_QUEUE_BAD_ARGUMENT = 3,
    COMP_EPAPER_DISPLAY_QUEUE_UNSUPPORTED_EXPRESSION = 4,
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
    COMP_EPAPER_DISPLAY_REQUEST_PET_EXPRESSION = 3,
} comp_epaper_display_request_kind_t;

typedef enum {
    COMP_EPAPER_REFRESH_AUTO = 0,
    COMP_EPAPER_REFRESH_FULL = 1,
    COMP_EPAPER_REFRESH_PARTIAL = 2,
    COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE = 3,
    /* Deferred after the user releases touch; allowed to restore contrast. */
    COMP_EPAPER_REFRESH_MAINTENANCE = 4,
} comp_epaper_refresh_mode_t;

typedef struct {
    uint32_t sequence;
    uint32_t request_id;
    uint32_t content_crc32;
    uint32_t resource_revision;
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
    uint16_t asset_frame_index;
    uint16_t dirty_x;
    uint16_t dirty_y;
    uint16_t dirty_width;
    uint16_t dirty_height;
    comp_pet_expression_pose_t pet_pose;
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
    uint32_t request_id,
    const comp_epaper_expression_decision_t *decision,
    uint16_t frame_index,
    comp_epaper_refresh_mode_t refresh_mode,
    uint16_t dirty_x,
    uint16_t dirty_y,
    uint16_t dirty_width,
    uint16_t dirty_height,
    uint32_t content_crc32);

comp_epaper_display_queue_result_t comp_epaper_display_queue_enqueue_pet_expression(
    comp_epaper_display_queue_t *queue,
    uint8_t card_slot,
    uint16_t display_flags,
    uint32_t request_id,
    const comp_epaper_expression_decision_t *decision,
    const comp_pet_expression_pose_t *pose,
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

size_t comp_epaper_display_queue_discard_kind(
    comp_epaper_display_queue_t *queue,
    comp_epaper_display_request_kind_t request_kind);

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
