#ifndef COMPANION_DIAG_LOG_EXPORT_H
#define COMPANION_DIAG_LOG_EXPORT_H

#include "diag_log.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define COMP_DIAG_LOG_EXPORT_SCHEMA_VERSION 1u
#define COMP_DIAG_LOG_EXPORT_HEADER_BYTES 20u
#define COMP_DIAG_LOG_EXPORT_MAX_EVENTS 8u

enum {
    COMP_DIAG_LOG_EXPORT_FLAG_TAIL = 1u << 0,
    COMP_DIAG_LOG_EXPORT_FLAG_TRUNCATED = 1u << 1,
    COMP_DIAG_LOG_EXPORT_FLAG_EMPTY = 1u << 2,
    COMP_DIAG_LOG_EXPORT_FLAG_ERROR = 1u << 7,
};

typedef struct {
    uint32_t cursor;
    uint8_t source_mask;
    uint16_t severity_mask;
    uint16_t max_events;
    uint16_t max_bytes;
} comp_diag_log_export_request_t;

/* The field order is the DiagLogPacketV1 little-endian wire layout. The
 * 20-byte header plus at most eight 28-byte events fits one 248-byte GATT
 * value without allocating a second log ring. */
typedef struct {
    uint8_t schema_version;
    uint8_t flags;
    uint16_t event_count;
    uint32_t request_cursor;
    uint32_t next_cursor;
    uint16_t total_available;
    uint16_t payload_bytes;
    uint32_t payload_crc32;
    comp_diag_event_t events[COMP_DIAG_LOG_EXPORT_MAX_EVENTS];
} comp_diag_log_export_packet_t;

bool comp_diag_log_export_build(const comp_diag_log_export_request_t *request,
                                comp_diag_log_export_packet_t *packet,
                                size_t *out_packet_bytes);

uint32_t comp_diag_log_export_crc32(const uint8_t *data, size_t length);

#endif /* COMPANION_DIAG_LOG_EXPORT_H */
