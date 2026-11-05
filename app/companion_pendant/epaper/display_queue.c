#include "display_queue.h"

#include <string.h>

static size_t comp_epaper_queue_advance(size_t index)
{
    return (index + 1u) % COMP_EPAPER_DISPLAY_QUEUE_DEPTH;
}

static bool comp_epaper_refresh_is_boundary(uint8_t refresh_mode)
{
    return refresh_mode == (uint8_t)COMP_EPAPER_REFRESH_MAINTENANCE ||
           refresh_mode == (uint8_t)COMP_EPAPER_REFRESH_VISIBLE_FULL ||
           refresh_mode == (uint8_t)COMP_EPAPER_REFRESH_IDLE_ENTER_STRONG;
}

bool comp_epaper_display_request_is_boundary(
    const comp_epaper_display_request_t *request)
{
    return request != NULL &&
           comp_epaper_refresh_is_boundary(request->refresh_mode);
}

static bool comp_epaper_queue_has_pending_boundary(
    const comp_epaper_display_queue_t *queue)
{
    size_t index;

    if (queue == NULL) {
        return false;
    }
    index = queue->read_index;
    for (size_t count = 0u; count < queue->count; ++count) {
        if (comp_epaper_display_request_is_boundary(&queue->items[index])) {
            return true;
        }
        index = comp_epaper_queue_advance(index);
    }
    return false;
}

bool comp_epaper_display_queue_boundary_owned(
    const comp_epaper_display_queue_t *queue)
{
    return queue != NULL &&
           (queue->boundary_in_flight_request_id != 0u ||
            comp_epaper_queue_has_pending_boundary(queue));
}

static size_t comp_epaper_queue_discard_ordinary(
    comp_epaper_display_queue_t *queue)
{
    size_t source_index;
    size_t destination_index;
    size_t original_count;
    size_t kept_count = 0u;

    if (queue == NULL) {
        return 0u;
    }
    source_index = queue->read_index;
    destination_index = queue->read_index;
    original_count = queue->count;
    for (size_t index = 0u; index < original_count; ++index) {
        comp_epaper_display_request_t *source = &queue->items[source_index];
        if (comp_epaper_display_request_is_boundary(source)) {
            if (destination_index != source_index) {
                queue->items[destination_index] = *source;
            }
            destination_index = comp_epaper_queue_advance(destination_index);
            kept_count++;
        }
        source_index = comp_epaper_queue_advance(source_index);
    }
    source_index = destination_index;
    for (size_t index = kept_count; index < original_count; ++index) {
        memset(&queue->items[source_index], 0, sizeof(queue->items[source_index]));
        source_index = comp_epaper_queue_advance(source_index);
    }
    queue->write_index = destination_index;
    queue->count = kept_count;
    queue->dropped_count += (uint32_t)(original_count - kept_count);
    return original_count - kept_count;
}

static comp_epaper_display_queue_result_t comp_epaper_queue_reserve(
    comp_epaper_display_queue_t *queue,
    comp_epaper_display_request_t **out_request,
    bool boundary)
{
    if (queue == NULL || out_request == NULL) {
        return COMP_EPAPER_DISPLAY_QUEUE_BAD_ARGUMENT;
    }
    if (boundary) {
        (void)comp_epaper_queue_discard_ordinary(queue);
    } else if (comp_epaper_display_queue_boundary_owned(queue)) {
        queue->dropped_count++;
        queue->boundary_rejected_count++;
        return COMP_EPAPER_DISPLAY_QUEUE_BOUNDARY_OWNS_DISPLAY;
    }
    if (queue->count >= COMP_EPAPER_DISPLAY_QUEUE_DEPTH) {
        queue->dropped_count++;
        return COMP_EPAPER_DISPLAY_QUEUE_FULL;
    }
    *out_request = &queue->items[queue->write_index];
    memset(*out_request, 0, sizeof(**out_request));
    (*out_request)->sequence = queue->next_sequence++;
    (*out_request)->resource_revision = queue->active_resource_revision;
    return COMP_EPAPER_DISPLAY_QUEUE_OK;
}

static void comp_epaper_queue_commit(comp_epaper_display_queue_t *queue)
{
    queue->write_index = comp_epaper_queue_advance(queue->write_index);
    queue->count++;
    if (queue->count > queue->high_water_count) {
        queue->high_water_count = queue->count;
    }
}

void comp_epaper_display_queue_init(comp_epaper_display_queue_t *queue)
{
    if (queue == NULL) {
        return;
    }
    memset(queue, 0, sizeof(*queue));
    queue->next_sequence = 1u;
}

void comp_epaper_display_queue_set_resource_revision(
    comp_epaper_display_queue_t *queue,
    uint32_t resource_revision)
{
    size_t discarded;

    if (queue == NULL || queue->active_resource_revision == resource_revision) {
        return;
    }

    discarded = queue->count;
    if (discarded != 0u) {
        queue->dropped_count += (uint32_t)discarded;
        queue->stale_generation_discard_count += (uint32_t)discarded;
    }
    queue->last_stale_generation_discarded = (uint32_t)discarded;
    queue->generation_switch_count++;
    memset(queue->items, 0, sizeof(queue->items));
    queue->read_index = 0u;
    queue->write_index = 0u;
    queue->count = 0u;
    queue->boundary_in_flight_request_id = 0u;
    queue->active_resource_revision = resource_revision;
}

comp_epaper_display_queue_result_t comp_epaper_display_queue_enqueue_card_write(
    comp_epaper_display_queue_t *queue,
    uint8_t card_slot,
    uint16_t display_flags,
    uint32_t request_id,
    uint16_t utf8_title_len,
    uint16_t utf8_body_len,
    const uint8_t *payload,
    uint16_t payload_len,
    uint32_t content_crc32)
{
    comp_epaper_display_request_t *request = NULL;
    comp_epaper_display_queue_result_t result;

    if (queue == NULL || (payload == NULL && payload_len != 0u)) {
        return COMP_EPAPER_DISPLAY_QUEUE_BAD_ARGUMENT;
    }
    if (payload_len > COMP_EPAPER_DISPLAY_PAYLOAD_MAX_BYTES) {
        queue->dropped_count++;
        return COMP_EPAPER_DISPLAY_QUEUE_PAYLOAD_TOO_LONG;
    }
    result = comp_epaper_queue_reserve(queue, &request, false);
    if (result != COMP_EPAPER_DISPLAY_QUEUE_OK) {
        return result;
    }

    request->request_id = request_id;
    request->content_crc32 = content_crc32;
    request->display_flags = display_flags;
    request->utf8_title_len = utf8_title_len;
    request->utf8_body_len = utf8_body_len;
    request->payload_len = payload_len;
    request->card_slot = card_slot;
    request->request_kind = (uint8_t)COMP_EPAPER_DISPLAY_REQUEST_CARD_WRITE;
    if (payload_len != 0u) {
        memcpy(request->payload, payload, payload_len);
    }

    comp_epaper_queue_commit(queue);
    return COMP_EPAPER_DISPLAY_QUEUE_OK;
}

comp_epaper_display_queue_result_t comp_epaper_display_queue_enqueue_expression(
    comp_epaper_display_queue_t *queue,
    uint8_t card_slot,
    uint16_t display_flags,
    uint32_t request_id,
    const comp_epaper_expression_decision_t *decision,
    uint32_t content_crc32)
{
    comp_epaper_display_request_t *request = NULL;
    comp_epaper_display_queue_result_t result;

    if (queue == NULL || decision == NULL) {
        return COMP_EPAPER_DISPLAY_QUEUE_BAD_ARGUMENT;
    }
    if (!comp_epaper_expression_is_supported(decision->expression)) {
        queue->dropped_count++;
        return COMP_EPAPER_DISPLAY_QUEUE_UNSUPPORTED_EXPRESSION;
    }
    result = comp_epaper_queue_reserve(queue, &request, false);
    if (result != COMP_EPAPER_DISPLAY_QUEUE_OK) {
        return result;
    }

    request->request_id = request_id;
    request->content_crc32 = content_crc32;
    request->display_flags = display_flags;
    request->card_slot = card_slot;
    request->request_kind = (uint8_t)COMP_EPAPER_DISPLAY_REQUEST_EXPRESSION;
    request->expression = (uint8_t)decision->expression;
    request->expression_signal = (uint8_t)decision->signal;
    request->expression_priority = decision->priority;

    comp_epaper_queue_commit(queue);
    return COMP_EPAPER_DISPLAY_QUEUE_OK;
}

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
    uint32_t content_crc32)
{
    return comp_epaper_display_queue_enqueue_expression_frame_with_recording_overlay(
        queue, card_slot, display_flags, charger_frame_index,
        false, false, 0u, 0u, 0u, COMP_EPAPER_DISPLAY_CLASS_BASE,
        request_id, decision, frame_index, refresh_mode,
        dirty_x, dirty_y, dirty_width, dirty_height, content_crc32);
}

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
    uint32_t content_crc32)
{
    comp_epaper_display_request_t *request = NULL;
    comp_epaper_display_queue_result_t result;

    if (queue == NULL || decision == NULL ||
        display_class > COMP_EPAPER_DISPLAY_CLASS_RECORDING ||
        refresh_mode > COMP_EPAPER_REFRESH_IDLE_ENTER_STRONG) {
        return COMP_EPAPER_DISPLAY_QUEUE_BAD_ARGUMENT;
    }
    if (!comp_epaper_expression_is_supported(decision->expression)) {
        queue->dropped_count++;
        return COMP_EPAPER_DISPLAY_QUEUE_UNSUPPORTED_EXPRESSION;
    }
    result = comp_epaper_queue_reserve(
        queue, &request,
        comp_epaper_refresh_is_boundary((uint8_t)refresh_mode));
    if (result != COMP_EPAPER_DISPLAY_QUEUE_OK) {
        return result;
    }
    request->request_id = request_id;
    request->content_crc32 = content_crc32;
    request->display_flags = display_flags;
    request->charger_frame_index = charger_frame_index;
    request->recording_overlay_present = recording_overlay_present ? 1u : 0u;
    request->recording_overlay_only = recording_overlay_only ? 1u : 0u;
    request->recording_overlay_frame_index = recording_overlay_frame_index;
    request->asset_state_hash = asset_state_hash;
    request->recording_overlay_state_hash = recording_overlay_state_hash;
    request->display_class = (uint8_t)display_class;
    request->card_slot = card_slot;
    request->request_kind = (uint8_t)COMP_EPAPER_DISPLAY_REQUEST_EXPRESSION;
    request->expression = (uint8_t)decision->expression;
    request->expression_signal = (uint8_t)decision->signal;
    request->expression_priority = decision->priority;
    request->refresh_mode = (uint8_t)refresh_mode;
    request->asset_frame_valid = 1u;
    request->asset_frame_index = frame_index;
    request->dirty_x = dirty_x;
    request->dirty_y = dirty_y;
    request->dirty_width = dirty_width;
    request->dirty_height = dirty_height;
    comp_epaper_queue_commit(queue);
    return COMP_EPAPER_DISPLAY_QUEUE_OK;
}

comp_epaper_display_queue_result_t comp_epaper_display_queue_enqueue_menu(
    comp_epaper_display_queue_t *queue,
    uint8_t card_slot,
    uint32_t request_id,
    uint8_t menu_view,
    uint8_t menu_flags,
    uint8_t menu_language,
    uint8_t menu_page,
    comp_epaper_refresh_mode_t refresh_mode,
    uint32_t content_crc32)
{
    comp_epaper_display_request_t *request = NULL;
    comp_epaper_display_queue_result_t result;
    bool replace_pending_menu = false;
    uint32_t sequence = 0u;

    if (queue == NULL || refresh_mode > COMP_EPAPER_REFRESH_IDLE_ENTER_STRONG) {
        return COMP_EPAPER_DISPLAY_QUEUE_BAD_ARGUMENT;
    }
    if (queue->count != 0u) {
        size_t latest = queue->write_index == 0u
                            ? COMP_EPAPER_DISPLAY_QUEUE_DEPTH - 1u
                            : queue->write_index - 1u;
        if (queue->items[latest].request_kind ==
                (uint8_t)COMP_EPAPER_DISPLAY_REQUEST_MENU &&
            !comp_epaper_display_request_is_boundary(&queue->items[latest]) &&
            !comp_epaper_refresh_is_boundary((uint8_t)refresh_mode)) {
            request = &queue->items[latest];
            sequence = request->sequence;
            memset(request, 0, sizeof(*request));
            request->sequence = sequence;
            request->resource_revision = queue->active_resource_revision;
            replace_pending_menu = true;
        }
    }
    if (!replace_pending_menu) {
        result = comp_epaper_queue_reserve(
            queue, &request,
            comp_epaper_refresh_is_boundary((uint8_t)refresh_mode));
        if (result != COMP_EPAPER_DISPLAY_QUEUE_OK) {
            return result;
        }
    }
    request->request_id = request_id;
    request->content_crc32 = content_crc32;
    request->card_slot = card_slot;
    request->request_kind = (uint8_t)COMP_EPAPER_DISPLAY_REQUEST_MENU;
    request->menu_view = menu_view;
    request->menu_flags = menu_flags;
    request->menu_language = menu_language;
    request->menu_page = menu_page;
    request->refresh_mode = (uint8_t)refresh_mode;
    if (!replace_pending_menu) {
        comp_epaper_queue_commit(queue);
    }
    return COMP_EPAPER_DISPLAY_QUEUE_OK;
}

bool comp_epaper_display_queue_dequeue(comp_epaper_display_queue_t *queue,
                                       comp_epaper_display_request_t *out_request)
{
    if (queue == NULL || out_request == NULL || queue->count == 0u) {
        return false;
    }

    *out_request = queue->items[queue->read_index];
    if (comp_epaper_display_request_is_boundary(out_request)) {
        queue->boundary_in_flight_request_id = out_request->request_id;
    }
    memset(&queue->items[queue->read_index], 0, sizeof(queue->items[queue->read_index]));
    queue->read_index = comp_epaper_queue_advance(queue->read_index);
    queue->count--;
    return true;
}

bool comp_epaper_display_queue_complete(
    comp_epaper_display_queue_t *queue,
    uint32_t request_id)
{
    if (queue == NULL || request_id == 0u ||
        queue->boundary_in_flight_request_id != request_id) {
        return false;
    }
    queue->boundary_in_flight_request_id = 0u;
    return true;
}

size_t comp_epaper_display_queue_discard_kind(
    comp_epaper_display_queue_t *queue,
    comp_epaper_display_request_kind_t request_kind)
{
    size_t source_index;
    size_t destination_index;
    size_t original_count;
    size_t kept_count = 0u;

    if (queue == NULL || request_kind > COMP_EPAPER_DISPLAY_REQUEST_MENU) {
        return 0u;
    }

    source_index = queue->read_index;
    destination_index = queue->read_index;
    original_count = queue->count;
    for (size_t index = 0u; index < original_count; ++index) {
        comp_epaper_display_request_t *source = &queue->items[source_index];
        if (source->request_kind != (uint8_t)request_kind ||
            comp_epaper_display_request_is_boundary(source)) {
            if (destination_index != source_index) {
                queue->items[destination_index] = *source;
            }
            destination_index = comp_epaper_queue_advance(destination_index);
            kept_count++;
        }
        source_index = comp_epaper_queue_advance(source_index);
    }

    source_index = destination_index;
    for (size_t index = kept_count; index < original_count; ++index) {
        memset(&queue->items[source_index], 0, sizeof(queue->items[source_index]));
        source_index = comp_epaper_queue_advance(source_index);
    }
    queue->write_index = destination_index;
    queue->count = kept_count;
    return original_count - kept_count;
}

size_t comp_epaper_display_queue_discard_display_flags(
    comp_epaper_display_queue_t *queue,
    uint16_t required_flags)
{
    size_t source_index;
    size_t destination_index;
    size_t original_count;
    size_t kept_count = 0u;

    if (queue == NULL || required_flags == 0u) {
        return 0u;
    }

    source_index = queue->read_index;
    destination_index = queue->read_index;
    original_count = queue->count;
    for (size_t index = 0u; index < original_count; ++index) {
        comp_epaper_display_request_t *source = &queue->items[source_index];
        if ((source->display_flags & required_flags) != required_flags ||
            comp_epaper_display_request_is_boundary(source)) {
            if (destination_index != source_index) {
                queue->items[destination_index] = *source;
            }
            destination_index = comp_epaper_queue_advance(destination_index);
            kept_count++;
        }
        source_index = comp_epaper_queue_advance(source_index);
    }

    source_index = destination_index;
    for (size_t index = kept_count; index < original_count; ++index) {
        memset(&queue->items[source_index], 0, sizeof(queue->items[source_index]));
        source_index = comp_epaper_queue_advance(source_index);
    }
    queue->write_index = destination_index;
    queue->count = kept_count;
    return original_count - kept_count;
}

size_t comp_epaper_display_queue_discard_display_class(
    comp_epaper_display_queue_t *queue,
    comp_epaper_display_class_t display_class)
{
    size_t source_index;
    size_t destination_index;
    size_t original_count;
    size_t kept_count = 0u;

    if (queue == NULL || display_class > COMP_EPAPER_DISPLAY_CLASS_RECORDING) {
        return 0u;
    }

    source_index = queue->read_index;
    destination_index = queue->read_index;
    original_count = queue->count;
    for (size_t index = 0u; index < original_count; ++index) {
        comp_epaper_display_request_t *source = &queue->items[source_index];
        if (source->display_class != (uint8_t)display_class ||
            comp_epaper_display_request_is_boundary(source)) {
            if (destination_index != source_index) {
                queue->items[destination_index] = *source;
            }
            destination_index = comp_epaper_queue_advance(destination_index);
            kept_count++;
        }
        source_index = comp_epaper_queue_advance(source_index);
    }

    source_index = destination_index;
    for (size_t index = kept_count; index < original_count; ++index) {
        memset(&queue->items[source_index], 0, sizeof(queue->items[source_index]));
        source_index = comp_epaper_queue_advance(source_index);
    }
    queue->write_index = destination_index;
    queue->count = kept_count;
    return original_count - kept_count;
}

void comp_epaper_display_queue_snapshot(const comp_epaper_display_queue_t *queue,
                                        comp_epaper_display_queue_snapshot_t *out_snapshot)
{
    if (out_snapshot == NULL) {
        return;
    }

    memset(out_snapshot, 0, sizeof(*out_snapshot));
    if (queue == NULL) {
        return;
    }

    out_snapshot->pending_count = queue->count;
    out_snapshot->high_water_count = queue->high_water_count;
    out_snapshot->queue_depth = COMP_EPAPER_DISPLAY_QUEUE_DEPTH;
    out_snapshot->payload_max_bytes = COMP_EPAPER_DISPLAY_PAYLOAD_MAX_BYTES;
    out_snapshot->next_sequence = queue->next_sequence;
    out_snapshot->dropped_count = queue->dropped_count;
    out_snapshot->active_resource_revision = queue->active_resource_revision;
    out_snapshot->generation_switch_count = queue->generation_switch_count;
    out_snapshot->last_stale_generation_discarded =
        queue->last_stale_generation_discarded;
    out_snapshot->stale_generation_discard_count =
        queue->stale_generation_discard_count;
    out_snapshot->boundary_rejected_count = queue->boundary_rejected_count;
    out_snapshot->boundary_in_flight_request_id =
        queue->boundary_in_flight_request_id;
}

size_t comp_epaper_display_queue_pending(const comp_epaper_display_queue_t *queue)
{
    return queue == NULL ? 0u : queue->count;
}

size_t comp_epaper_display_queue_high_water_count(const comp_epaper_display_queue_t *queue)
{
    return queue == NULL ? 0u : queue->high_water_count;
}

uint32_t comp_epaper_display_queue_dropped_count(const comp_epaper_display_queue_t *queue)
{
    return queue == NULL ? 0u : queue->dropped_count;
}

uint32_t comp_epaper_display_queue_active_resource_revision(const comp_epaper_display_queue_t *queue)
{
    return queue == NULL ? 0u : queue->active_resource_revision;
}

uint32_t comp_epaper_display_queue_generation_switch_count(const comp_epaper_display_queue_t *queue)
{
    return queue == NULL ? 0u : queue->generation_switch_count;
}

uint32_t comp_epaper_display_queue_last_stale_generation_discarded(const comp_epaper_display_queue_t *queue)
{
    return queue == NULL ? 0u : queue->last_stale_generation_discarded;
}

uint32_t comp_epaper_display_queue_stale_generation_discard_count(const comp_epaper_display_queue_t *queue)
{
    return queue == NULL ? 0u : queue->stale_generation_discard_count;
}

uint8_t comp_epaper_display_queue_status_error(comp_epaper_display_queue_result_t result)
{
    switch (result) {
    case COMP_EPAPER_DISPLAY_QUEUE_OK:
        return 0u;
    case COMP_EPAPER_DISPLAY_QUEUE_FULL:
        return 1u;
    case COMP_EPAPER_DISPLAY_QUEUE_PAYLOAD_TOO_LONG:
        return 2u;
    case COMP_EPAPER_DISPLAY_QUEUE_BAD_ARGUMENT:
        return 3u;
    case COMP_EPAPER_DISPLAY_QUEUE_UNSUPPORTED_EXPRESSION:
        return 9u;
    case COMP_EPAPER_DISPLAY_QUEUE_BOUNDARY_OWNS_DISPLAY:
        return 10u;
    default:
        return 0x7Fu;
    }
}
