#include "diag_log.h"
#include "diag_log_export.h"

#include <stdio.h>
#include <string.h>

static int s_failures;

#define CHECK(condition, message)                                      \
    do {                                                               \
        if (!(condition)) {                                            \
            (void)fprintf(stderr, "FAIL: %s\n", (message));           \
            s_failures++;                                              \
        }                                                              \
    } while (0)

static void seed_log(void)
{
    comp_diag_log_init();
    for (uint32_t sequence = 1u; sequence <= 12u; ++sequence) {
        uint8_t source = (sequence & 1u) != 0u
                             ? COMP_DIAG_SRC_BOOT
                             : COMP_DIAG_SRC_BLE;
        uint8_t severity = (uint8_t)(sequence % 3u);
        comp_diag_log_record(source,
                             (uint8_t)sequence,
                             severity,
                             sequence,
                             sequence + 100u,
                             sequence + 200u,
                             sequence + 300u);
    }
}

static comp_diag_log_export_packet_t build_packet(
    const comp_diag_log_export_request_t *request,
    size_t *packet_bytes)
{
    comp_diag_log_export_packet_t packet;
    bool built = comp_diag_log_export_build(request, &packet, packet_bytes);
    CHECK(built, "packet build failed");
    return packet;
}

static void test_tail_and_byte_bound(void)
{
    const comp_diag_log_export_request_t request = {
        .cursor = 0u,
        .source_mask = 0u,
        .severity_mask = 0u,
        .max_events = 4u,
        .max_bytes = 64u,
    };
    size_t packet_bytes = 0u;
    comp_diag_log_export_packet_t packet = build_packet(&request, &packet_bytes);

    CHECK(packet_bytes == 48u, "64-byte bound should fit one event packet");
    CHECK(packet.event_count == 1u, "byte bound did not cap the event count");
    CHECK(packet.total_available == 12u, "tail total_available mismatch");
    CHECK(packet.events[0].sequence == 12u, "tail did not return newest event");
    CHECK(packet.next_cursor == 12u, "tail next cursor mismatch");
    CHECK((packet.flags & COMP_DIAG_LOG_EXPORT_FLAG_TAIL) != 0u,
          "tail flag missing");
    CHECK((packet.flags & COMP_DIAG_LOG_EXPORT_FLAG_TRUNCATED) != 0u,
          "truncated flag missing");
    CHECK(packet.payload_crc32 == comp_diag_log_export_crc32(
                                        (const uint8_t *)packet.events,
                                        packet.payload_bytes),
          "event payload CRC mismatch");
}

static void test_cursor_paging(void)
{
    const comp_diag_log_export_request_t request = {
        .cursor = 8u,
        .source_mask = 0u,
        .severity_mask = 0u,
        .max_events = 2u,
        .max_bytes = 0u,
    };
    size_t packet_bytes = 0u;
    comp_diag_log_export_packet_t packet = build_packet(&request, &packet_bytes);

    CHECK(packet.event_count == 2u, "cursor page count mismatch");
    CHECK(packet.total_available == 4u, "cursor available count mismatch");
    CHECK(packet.events[0].sequence == 9u && packet.events[1].sequence == 10u,
          "cursor page skipped or reordered events");
    CHECK(packet.next_cursor == 10u, "cursor page next cursor mismatch");
    CHECK((packet.flags & COMP_DIAG_LOG_EXPORT_FLAG_TAIL) == 0u,
          "cursor page incorrectly marked as tail");
    CHECK(packet_bytes == COMP_DIAG_LOG_EXPORT_HEADER_BYTES +
                              2u * sizeof(comp_diag_event_t),
          "cursor packet size mismatch");
}

static void test_filters(void)
{
    const comp_diag_log_export_request_t boot_request = {
        .cursor = 0u,
        .source_mask = 1u << (COMP_DIAG_SRC_BOOT - 1u),
        .severity_mask = 0u,
        .max_events = 3u,
        .max_bytes = 0u,
    };
    const comp_diag_log_export_request_t warn_request = {
        .cursor = 0u,
        .source_mask = 0u,
        .severity_mask = 1u << COMP_DIAG_SEV_WARN,
        .max_events = 2u,
        .max_bytes = 0u,
    };
    size_t packet_bytes = 0u;
    comp_diag_log_export_packet_t packet = build_packet(&boot_request, &packet_bytes);

    CHECK(packet.total_available == 6u, "source filter available mismatch");
    CHECK(packet.event_count == 3u, "source filter event count mismatch");
    CHECK(packet.events[0].sequence == 7u &&
              packet.events[1].sequence == 9u &&
              packet.events[2].sequence == 11u,
          "source filter tail mismatch");

    packet = build_packet(&warn_request, &packet_bytes);
    CHECK(packet.total_available == 4u, "severity filter available mismatch");
    CHECK(packet.events[0].sequence == 7u && packet.events[1].sequence == 10u,
          "severity filter tail mismatch");
}

static void test_empty_and_invalid_bound(void)
{
    const comp_diag_log_export_request_t empty_request = {
        .cursor = 12u,
        .source_mask = 0u,
        .severity_mask = 0u,
        .max_events = 4u,
        .max_bytes = 0u,
    };
    const comp_diag_log_export_request_t invalid_request = {
        .cursor = 0u,
        .source_mask = 0u,
        .severity_mask = 0u,
        .max_events = 4u,
        .max_bytes = COMP_DIAG_LOG_EXPORT_HEADER_BYTES - 1u,
    };
    size_t packet_bytes = 0u;
    comp_diag_log_export_packet_t packet = build_packet(&empty_request, &packet_bytes);

    CHECK(packet.event_count == 0u && packet.total_available == 0u,
          "empty cursor response contains events");
    CHECK(packet.next_cursor == 12u, "empty cursor should remain stable");
    CHECK((packet.flags & COMP_DIAG_LOG_EXPORT_FLAG_EMPTY) != 0u,
          "empty flag missing");

    packet = build_packet(&invalid_request, &packet_bytes);
    CHECK(packet_bytes == COMP_DIAG_LOG_EXPORT_HEADER_BYTES,
          "invalid byte bound must return only the protocol header");
    CHECK((packet.flags & COMP_DIAG_LOG_EXPORT_FLAG_ERROR) != 0u,
          "invalid byte bound did not set error flag");
}

int main(void)
{
    static const uint8_t crc_vector[] = "123456789";

    CHECK(comp_diag_log_export_crc32(crc_vector, strlen((const char *)crc_vector)) ==
              0xCBF43926u,
          "CRC32 standard vector mismatch");
    seed_log();
    test_tail_and_byte_bound();
    test_cursor_paging();
    test_filters();
    test_empty_and_invalid_bound();

    if (s_failures != 0) {
        (void)fprintf(stderr, "FAIL: %d diagnostics export checks failed\n", s_failures);
        return 1;
    }
    (void)printf("PASS: portable bounded diagnostics export host replay passed.\n");
    return 0;
}
