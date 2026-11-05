#include "diag_log_export.h"

#include <limits.h>
#include <string.h>

_Static_assert(sizeof(comp_diag_event_t) == 28u,
               "DiagLogPacketV1 requires a stable 28-byte event record");
_Static_assert(offsetof(comp_diag_log_export_packet_t, events) ==
                   COMP_DIAG_LOG_EXPORT_HEADER_BYTES,
               "DiagLogPacketV1 header layout changed");
_Static_assert(sizeof(comp_diag_log_export_packet_t) == 244u,
               "DiagLogPacketV1 must fit the 248-byte GATT value");

uint32_t comp_diag_log_export_crc32(const uint8_t *data, size_t length)
{
    uint32_t crc = 0xFFFFFFFFu;

    if (data == 0 && length != 0u) {
        return 0u;
    }
    for (size_t index = 0u; index < length; ++index) {
        crc ^= data[index];
        for (uint8_t bit = 0u; bit < 8u; ++bit) {
            uint32_t mask = (uint32_t)(0u - (crc & 1u));
            crc = (crc >> 1u) ^ (0xEDB88320u & mask);
        }
    }
    return crc ^ 0xFFFFFFFFu;
}

bool comp_diag_log_export_build_status(uint32_t request_cursor,
                                       uint8_t status_flags,
                                       comp_diag_log_export_packet_t *packet,
                                       size_t *out_packet_bytes)
{
    if (packet == 0 || out_packet_bytes == 0u) {
        return false;
    }
    memset(packet, 0, sizeof(*packet));
    packet->schema_version = COMP_DIAG_LOG_EXPORT_SCHEMA_VERSION;
    packet->flags = (uint8_t)(COMP_DIAG_LOG_EXPORT_FLAG_ERROR |
                              COMP_DIAG_LOG_EXPORT_FLAG_EMPTY |
                              status_flags);
    packet->request_cursor = request_cursor;
    packet->next_cursor = request_cursor;
    *out_packet_bytes = COMP_DIAG_LOG_EXPORT_HEADER_BYTES;
    return true;
}

bool comp_diag_log_export_should_defer(bool update_busy,
                                       bool recording_or_storage_busy,
                                       bool transfer_busy,
                                       bool playback_active)
{
    return update_busy || recording_or_storage_busy || transfer_busy ||
           playback_active;
}

bool comp_diag_log_export_build(const comp_diag_log_export_request_t *request,
                                comp_diag_log_export_packet_t *packet,
                                size_t *out_packet_bytes)
{
    size_t max_packet_bytes;
    size_t max_events;
    size_t byte_event_limit;
    size_t total_available = 0u;
    size_t event_count;

    if (request == 0 || packet == 0 || out_packet_bytes == 0) {
        return false;
    }

    memset(packet, 0, sizeof(*packet));
    packet->schema_version = COMP_DIAG_LOG_EXPORT_SCHEMA_VERSION;
    packet->request_cursor = request->cursor;
    packet->next_cursor = request->cursor;
    if (request->cursor == 0u) {
        packet->flags |= COMP_DIAG_LOG_EXPORT_FLAG_TAIL;
    }

    max_packet_bytes = request->max_bytes == 0u
                           ? sizeof(*packet)
                           : request->max_bytes;
    if (max_packet_bytes > sizeof(*packet)) {
        max_packet_bytes = sizeof(*packet);
    }
    if (max_packet_bytes < COMP_DIAG_LOG_EXPORT_HEADER_BYTES) {
        return comp_diag_log_export_build_status(
            request->cursor,
            COMP_DIAG_LOG_EXPORT_FLAG_INVALID_REQUEST,
            packet,
            out_packet_bytes);
    }

    byte_event_limit = (max_packet_bytes - COMP_DIAG_LOG_EXPORT_HEADER_BYTES) /
                       sizeof(comp_diag_event_t);
    max_events = request->max_events == 0u ? 4u : request->max_events;
    if (max_events > COMP_DIAG_LOG_EXPORT_MAX_EVENTS) {
        max_events = COMP_DIAG_LOG_EXPORT_MAX_EVENTS;
    }
    if (max_events > byte_event_limit) {
        max_events = byte_event_limit;
    }

    if (max_events != 0u) {
        event_count = comp_diag_log_read_page(request->cursor,
                                              request->source_mask,
                                              request->severity_mask,
                                              packet->events,
                                              max_events,
                                              &total_available);
    } else {
        comp_diag_event_t ignored;
        event_count = comp_diag_log_read_page(request->cursor,
                                              request->source_mask,
                                              request->severity_mask,
                                              &ignored,
                                              1u,
                                              &total_available);
        event_count = 0u;
    }

    packet->event_count = (uint16_t)event_count;
    packet->total_available = total_available > UINT16_MAX
                                  ? UINT16_MAX
                                  : (uint16_t)total_available;
    packet->payload_bytes = (uint16_t)(event_count * sizeof(comp_diag_event_t));
    if (event_count != 0u) {
        packet->next_cursor = packet->events[event_count - 1u].sequence;
        packet->payload_crc32 = comp_diag_log_export_crc32(
            (const uint8_t *)packet->events,
            packet->payload_bytes);
    } else {
        packet->flags |= COMP_DIAG_LOG_EXPORT_FLAG_EMPTY;
    }
    if (total_available > event_count) {
        packet->flags |= COMP_DIAG_LOG_EXPORT_FLAG_TRUNCATED;
    }

    *out_packet_bytes = COMP_DIAG_LOG_EXPORT_HEADER_BYTES + packet->payload_bytes;
    return true;
}
