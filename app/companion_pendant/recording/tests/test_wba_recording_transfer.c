#include "wba_recording_transfer.h"
#include "wba_recording_crc.h"

#include <stdio.h>
#include <string.h>

#define FLASH_BYTES (96u * 1024u)
#define DATA_BYTES \
    (FLASH_BYTES - COMP_RECORDING_JOURNAL_CATALOG_SECTORS * \
                       COMP_RECORDING_JOURNAL_SECTOR_BYTES)
#define MAX_NOTIFICATIONS 12u

typedef struct {
    uint8_t flash[FLASH_BYTES];
    uint8_t notifications[MAX_NOTIFICATIONS]
                         [COMP_WBA_RECORDING_TRANSFER_VALUE_BYTES];
    uint16_t notification_lengths[MAX_NOTIFICATIONS];
    uint32_t notification_count;
    uint32_t notify_attempts;
    uint32_t read_calls;
    uint32_t erase_calls;
    uint32_t data_erase_calls;
    bool reject_next_notify;
    bool heavy_io_allowed;
    bool block_after_next_read;
    comp_recording_journal_entry_t live;
    comp_wba_recording_transfer_t *invalidate_transfer;
    bool invalidate_disconnect;
} fixture_t;

static int fail_line(int line, const char *message)
{
    fprintf(stderr, "FAIL line=%d %s\n", line, message);
    return line;
}

#define CHECK(expression, message) \
    do { if (!(expression)) return fail_line(__LINE__, message); } while (0)

static uint16_t get_le16(const uint8_t *source)
{
    return (uint16_t)((uint16_t)source[0] |
                      ((uint16_t)source[1] << 8u));
}

static uint32_t get_le32(const uint8_t *source)
{
    return (uint32_t)source[0] |
           ((uint32_t)source[1] << 8u) |
           ((uint32_t)source[2] << 16u) |
           ((uint32_t)source[3] << 24u);
}

static bool flash_read(void *context, uint32_t offset, uint8_t *destination,
                       uint32_t length)
{
    fixture_t *fixture = context;
    if (destination == NULL || offset > FLASH_BYTES ||
        length > FLASH_BYTES - offset) return false;
    fixture->read_calls++;
    memcpy(destination, &fixture->flash[offset], length);
    if (fixture->block_after_next_read) {
        fixture->block_after_next_read = false;
        fixture->heavy_io_allowed = false;
    }
    return true;
}

static bool flash_program(void *context, uint32_t offset,
                          const uint8_t *source, uint32_t length)
{
    fixture_t *fixture = context;
    if (source == NULL || offset > FLASH_BYTES ||
        length > FLASH_BYTES - offset) return false;
    for (uint32_t i = 0u; i < length; ++i) {
        if ((fixture->flash[offset + i] & source[i]) != source[i]) return false;
        fixture->flash[offset + i] &= source[i];
    }
    return true;
}

static bool flash_erase(void *context, uint32_t offset, uint32_t length)
{
    fixture_t *fixture = context;
    if (offset > FLASH_BYTES || length > FLASH_BYTES - offset ||
        (offset % COMP_RECORDING_JOURNAL_SECTOR_BYTES) != 0u ||
        (length % COMP_RECORDING_JOURNAL_SECTOR_BYTES) != 0u) return false;
    fixture->erase_calls++;
    if (offset < DATA_BYTES) fixture->data_erase_calls++;
    memset(&fixture->flash[offset], 0xFF, length);
    return true;
}

static uint32_t crc32_port(uint32_t seed, const uint8_t *data,
                           uint32_t length)
{
    uint32_t crc = seed ^ 0xFFFFFFFFu;
    for (uint32_t i = 0u; i < length; ++i) {
        uint32_t value = (crc ^ data[i]) & 0xFFu;
        for (uint32_t bit = 0u; bit < 8u; ++bit) {
            value = (value >> 1u) ^
                (0xEDB88320u & (uint32_t)(-(int32_t)(value & 1u)));
        }
        crc = (crc >> 8u) ^ value;
    }
    return crc ^ 0xFFFFFFFFu;
}

static int crc_compatibility(void)
{
    const uint8_t standard[] = "123456789";
    uint8_t bytes[513];
    CHECK(comp_wba_recording_crc32(0u, standard, 9u) == UINT32_C(0xCBF43926),
          "IEEE CRC-32 known vector");
    uint32_t random = UINT32_C(0xD14F902B);
    for (uint32_t i = 0u; i < sizeof(bytes); ++i) {
        random = random * UINT32_C(1664525) + UINT32_C(1013904223);
        bytes[i] = (uint8_t)(random >> 24u);
    }
    for (uint32_t seed_index = 0u; seed_index < 16u; ++seed_index) {
        const uint32_t seed = seed_index * UINT32_C(0x11111111);
        for (uint32_t length = 0u; length <= sizeof(bytes); ++length) {
            const uint32_t expected = crc32_port(seed, bytes, length);
            CHECK(comp_wba_recording_crc32(seed, bytes, length) == expected,
                  "nibble CRC equals independent bitwise reference for seeds and tails");
            const uint32_t split = length / 2u;
            CHECK(comp_wba_recording_crc32(comp_wba_recording_crc32(seed, bytes, split),
                      bytes + split, length - split) == expected,
                  "header/payload and page checkpoint incremental CRC unchanged");
        }
    }
    return 0;
}

static bool notify(void *context, const uint8_t *value, uint16_t length)
{
    fixture_t *fixture = context;
    fixture->notify_attempts++;
    if(fixture->invalidate_transfer) {
        comp_wba_recording_transfer_t *transfer=fixture->invalidate_transfer;
        fixture->invalidate_transfer=NULL;
        if(fixture->invalidate_disconnect)
            comp_wba_recording_transfer_set_connected(transfer,false);
        else comp_wba_recording_transfer_cancel(transfer);
        return true; /* An old ACI response arrives after invalidation. */
    }
    if (fixture->reject_next_notify) {
        fixture->reject_next_notify = false;
        return false;
    }
    if (value == NULL || length > COMP_WBA_RECORDING_TRANSFER_VALUE_BYTES ||
        fixture->notification_count >= MAX_NOTIFICATIONS) return false;
    memcpy(fixture->notifications[fixture->notification_count], value, length);
    fixture->notification_lengths[fixture->notification_count] = length;
    fixture->notification_count++;
    return true;
}

static bool io_allowed(void *context)
{
    return ((fixture_t *)context)->heavy_io_allowed;
}

static void fill_sha(uint8_t sha[COMP_RECORDING_JOURNAL_SHA256_BYTES],
                     uint8_t seed)
{
    for (uint32_t i = 0u; i < COMP_RECORDING_JOURNAL_SHA256_BYTES; ++i) {
        sha[i] = (uint8_t)(seed + i);
    }
}

static bool add_finalized(comp_recording_journal_t *journal,
                          fixture_t *fixture, const uint8_t *payload,
                          uint32_t payload_length, uint8_t sha_seed,
                          uint32_t *recording_id)
{
    comp_recording_journal_entry_t entry;
    uint8_t sha[COMP_RECORDING_JOURNAL_SHA256_BYTES];
    if (comp_recording_journal_begin(
            journal, payload_length, 1700000000u + sha_seed, 100u,
            3u, 1u, &entry) != COMP_RECORDING_JOURNAL_OK) return false;
    if (!flash_erase(fixture, entry.extent_offset, entry.reserved_bytes) ||
        !flash_program(fixture, entry.payload_offset, payload, payload_length)) {
        return false;
    }
    fill_sha(sha, sha_seed);
    if (comp_recording_journal_finalize(
            journal, entry.recording_id, payload_length, payload_length * 2u,
            crc32_port(0u, payload, payload_length), sha, 3u) !=
        COMP_RECORDING_JOURNAL_OK) return false;
    *recording_id = entry.recording_id;
    return true;
}

static uint32_t packet_crc(const uint8_t *packet,uint32_t sealed_total)
{
    uint8_t fields[16];
    const bool compact=(packet[1]&COMP_WBA_RECORDING_TRANSFER_COMPACT_FLAG)!=0u;
    const uint32_t total=compact ? sealed_total : get_le32(packet+16u);
    memcpy(fields, packet+4u, 12u);
    for(unsigned i=0u;i<4u;++i)fields[12u+i]=(uint8_t)((total>>(8u*i))&255u);
    uint32_t crc = crc32_port(0u, fields, sizeof(fields));
    return crc32_port(crc, &packet[(packet[1] & 1u) ? 56u : compact ? 20u : 24u], get_le16(&packet[2]));
}

static int drain(comp_wba_recording_transfer_t *transfer)
{
    for (uint32_t i = 0u; i < 32u; ++i) {
        comp_wba_recording_transfer_state_t state =
            comp_wba_recording_transfer_poll(transfer);
        if (state == COMP_WBA_RECORDING_TRANSFER_COMPLETE) return 0;
        if (state == COMP_WBA_RECORDING_TRANSFER_FAILED ||
            state == COMP_WBA_RECORDING_TRANSFER_IDLE) return 1;
    }
    return 1;
}

static uint32_t advancing_clock(void *context)
{
    uint32_t *tick = context;
    const uint32_t result = *tick;
    ++*tick;
    return result;
}
static uint32_t fixed_clock(void *context)
{
    return *(const uint32_t *)context;
}
static bool live_snapshot(void *context, uint32_t id,
                          comp_recording_journal_entry_t *entry)
{
    const fixture_t *fixture = context;
    if (id != fixture->live.recording_id) return false;
    *entry = fixture->live;
    return true;
}
static int bulk_bounds(fixture_t *fixture, comp_recording_journal_t *journal,
                       const comp_wba_recording_transfer_config_t *config,
                       const comp_recording_journal_entry_t *writing)
{
    uint8_t payload[10u * 224u + 17u]; /* Frozen legacy packet fixture. */
    for (uint32_t i = 0u; i < sizeof(payload); ++i) payload[i] = (uint8_t)(i * 13u);
    uint32_t id;
    CHECK(add_finalized(journal, fixture, payload, sizeof(payload), 0x90u, &id), "bulk fixture stored");
    const uint32_t erases = fixture->data_erase_calls;
    comp_wba_recording_transfer_t transfer;
    CHECK(comp_wba_recording_transfer_init(&transfer, config), "bulk init");
    CHECK(comp_wba_recording_transfer_set_value_capacity(&transfer,248u), "legacy bulk capacity");
    comp_wba_recording_transfer_set_connected(&transfer, true);
    const companion_recording_adapter_request_t request = {
        .schema_version = 1u, .flags = COMP_WBA_RECORDING_TRANSFER_STREAM_ALL_FLAG,
        .recording_id = id,
    };
    fixture->notification_count = 0u;
    CHECK(comp_wba_recording_transfer_start(&transfer, &request) == COMP_WBA_RECORDING_TRANSFER_OK, "bulk start");
    CHECK(comp_wba_recording_transfer_poll_bulk(&transfer, NULL, NULL) == COMP_WBA_RECORDING_TRANSFER_ACTIVE &&
          fixture->notification_count == 4u && transfer.next_offset == 4u * 224u, "bulk bounds four compact packets without clock");
    uint32_t received = 0u;
    for (uint32_t i = 0u; i < 4u; ++i) {
        const uint8_t *packet = fixture->notifications[i];
        CHECK(packet[1] == COMP_WBA_RECORDING_TRANSFER_COMPACT_FLAG &&
              get_le16(packet + 2u) == 224u && get_le32(packet + 12u) == received,
              "sealed compact header retains offset and full payload");
        uint8_t fields[16];
        memcpy(fields, packet + 4u, 12u);
        fields[12] = (uint8_t)(sizeof(payload) & 255u); fields[13] = (uint8_t)(sizeof(payload) >> 8u);
        fields[14] = 0u; fields[15] = 0u;
        CHECK(get_le32(packet + 16u) == crc32_port(crc32_port(0u, fields, 16u), packet + 20u, 224u) &&
              memcmp(packet + 20u, payload + received, 224u) == 0,
              "compact CRC uses sealed total and preserves original bytes");
        received += 224u;
    }
    fixture->reject_next_notify = true;
    const uint32_t before = transfer.next_offset;
    CHECK(comp_wba_recording_transfer_poll_bulk(&transfer, NULL, NULL) == COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED &&
          transfer.next_offset == before && transfer.packet_ready, "bulk yields on first refused packet");
    uint8_t pending[COMP_WBA_RECORDING_TRANSFER_VALUE_BYTES];
    const uint16_t length = transfer.packet_length;
    memcpy(pending, transfer.packet, length);
    CHECK(comp_wba_recording_transfer_poll_bulk(&transfer, NULL, NULL) == COMP_WBA_RECORDING_TRANSFER_ACTIVE &&
          memcmp(fixture->notifications[4], pending, length) == 0, "bulk retry delivers identical retained packet");
    CHECK(drain(&transfer) == 0 && transfer.next_offset == sizeof(payload) &&
          fixture->data_erase_calls == erases &&
          comp_recording_journal_find(journal, id)->sync_state == COMP_RECORDING_JOURNAL_UNSYNCED,
          "bulk finish never acknowledges or erases the recording");
    companion_recording_adapter_request_t tail = request;
    tail.byte_offset = sizeof(payload) - 224u;
    fixture->notification_count = 0u;
    CHECK(comp_wba_recording_transfer_start(&transfer, &tail) == COMP_WBA_RECORDING_TRANSFER_OK &&
          drain(&transfer) == 0 && fixture->notification_count == 2u &&
          fixture->notification_lengths[0] == 20u + 192u &&
          fixture->notification_lengths[1] == 56u + 32u &&
          memcmp(fixture->notifications[0] + 20u, payload + tail.byte_offset, 192u) == 0 &&
          memcmp(fixture->notifications[1] + 56u, payload + sizeof(payload) - 32u, 32u) == 0,
          "large final remainder fits existing packet allocation and retains SHA packet");
    CHECK(comp_wba_recording_transfer_start(&transfer, &request) == COMP_WBA_RECORDING_TRANSFER_OK, "timed bulk start");
    fixture->notification_count = 0u;
    uint32_t tick = UINT32_MAX - 1u;
    CHECK(comp_wba_recording_transfer_poll_bulk(&transfer, advancing_clock, &tick) == COMP_WBA_RECORDING_TRANSFER_ACTIVE &&
          fixture->notification_count == 1u && transfer.next_offset == 224u, "two millisecond bound survives clock wrap");
    const comp_wba_recording_transfer_budget_t stopped = {7u, 14u, 4u};
    const comp_wba_recording_transfer_budget_t waiting = {0u, 0u, 0u};
    const comp_wba_recording_transfer_budget_t oversized = {255u, 255u, 255u};
    CHECK(comp_wba_recording_transfer_start(&transfer, &request) == COMP_WBA_RECORDING_TRANSFER_OK,
          "owner-budget start");
    fixture->notification_count = 0u;
    CHECK(comp_wba_recording_transfer_poll_budget(&transfer, NULL, NULL, &stopped) == COMP_WBA_RECORDING_TRANSFER_ACTIVE &&
          fixture->notification_count == 7u && transfer.next_offset == 7u * 224u,
          "sealed owner fills at most seven packets without allocating a new queue");
    for (uint32_t i = 0u; i < 7u; ++i) {
        const uint8_t *packet = fixture->notifications[i];
        uint8_t fields[16];
        memcpy(fields, packet + 4u, 12u);
        fields[12] = (uint8_t)(sizeof(payload) & 255u); fields[13] = (uint8_t)(sizeof(payload) >> 8u);
        fields[14] = 0u; fields[15] = 0u;
        CHECK(get_le32(packet + 12u) == i * 224u &&
              get_le32(packet + 16u) == crc32_port(crc32_port(0u, fields, 16u), packet + 20u, 224u) &&
              memcmp(packet + 20u, payload + i * 224u, 224u) == 0,
              "budgeted burst retains exact original bytes, offsets and independently checked CRC");
    }
    fixture->reject_next_notify = true;
    CHECK(comp_wba_recording_transfer_poll_budget(&transfer, NULL, NULL, &stopped) == COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED,
          "owner-budget yields at TX refusal");
    const uint32_t paused_reads = fixture->read_calls;
    const uint32_t paused_attempts = fixture->notify_attempts;
    const uint32_t paused_offset = transfer.next_offset;
    const uint16_t paused_length = transfer.packet_length;
    memcpy(pending, transfer.packet, paused_length);
    CHECK(comp_wba_recording_transfer_poll_budget(&transfer, advancing_clock, &tick, &waiting) == COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED &&
          transfer.next_offset == paused_offset && fixture->read_calls == paused_reads &&
          fixture->notify_attempts == paused_attempts && transfer.packet_ready,
          "TX-pool wait performs no Flash read, SDK call or cursor advance");
    CHECK(comp_wba_recording_transfer_poll_budget(&transfer, NULL, NULL, &stopped) == COMP_WBA_RECORDING_TRANSFER_COMPLETE &&
          memcmp(fixture->notifications[7], pending, paused_length) == 0 &&
          transfer.next_offset == sizeof(payload) && fixture->data_erase_calls == erases &&
          comp_recording_journal_find(journal, id)->sync_state == COMP_RECORDING_JOURNAL_UNSYNCED,
          "queue event retries identical bytes; completion alone never consumes the durable recording");
    CHECK(comp_wba_recording_transfer_start(&transfer, &request) == COMP_WBA_RECORDING_TRANSFER_OK,
          "oversized owner-budget start");
    fixture->notification_count = 0u;
    CHECK(comp_wba_recording_transfer_poll_budget(&transfer, NULL, NULL, &oversized) == COMP_WBA_RECORDING_TRANSFER_ACTIVE &&
          fixture->notification_count == 7u, "oversized caller cannot create an unbounded loop");
    CHECK(comp_wba_recording_transfer_start(&transfer, &request) == COMP_WBA_RECORDING_TRANSFER_OK,
          "timed owner-budget start");
    fixture->notification_count = 0u; tick = UINT32_MAX - 2u;
    CHECK(comp_wba_recording_transfer_poll_budget(&transfer, advancing_clock, &tick, &oversized) == COMP_WBA_RECORDING_TRANSFER_ACTIVE &&
          fixture->notification_count == 2u && transfer.next_offset == 448u,
          "elapsed budget is capped at four milliseconds across clock wrap");
    comp_wba_recording_transfer_config_t live_config = *config;
    live_config.live_entry = live_snapshot;
    live_config.live_read_allowed = io_allowed;
    fixture->live = *writing;
    fixture->live.total_length = 100u;
    CHECK(comp_wba_recording_transfer_init(&transfer, &live_config), "live bulk init");
    CHECK(comp_wba_recording_transfer_set_value_capacity(&transfer,248u), "legacy live capacity");
    comp_wba_recording_transfer_set_connected(&transfer, true);
    companion_recording_adapter_request_t live_request = request;
    live_request.recording_id = writing->recording_id;
    CHECK(comp_wba_recording_transfer_start(&transfer, &live_request) == COMP_WBA_RECORDING_TRANSFER_OK, "live start");
    fixture->notification_count = 0u;
    CHECK(comp_wba_recording_transfer_poll_budget(&transfer, NULL, NULL, &stopped) == COMP_WBA_RECORDING_TRANSFER_ACTIVE &&
          transfer.packet_ready && fixture->notification_count == 0u && transfer.next_offset == 0u,
          "live capture clamps sealed budget to the single read-only foreground step");
    fixture->heavy_io_allowed = false;
    CHECK(comp_wba_recording_transfer_poll_budget(&transfer, NULL, NULL, &stopped) == COMP_WBA_RECORDING_TRANSFER_ACTIVE &&
          transfer.packet_ready && fixture->notification_count == 0u,
          "live audio ownership blocks even a prepared notify");
    fixture->heavy_io_allowed = true;
    const comp_wba_recording_transfer_budget_t capture_pair = {1u, 2u, 1u};
    CHECK(comp_wba_recording_transfer_start(&transfer, &live_request) == COMP_WBA_RECORDING_TRANSFER_OK, "timed pair start");
    tick = UINT32_MAX;
    CHECK(comp_wba_recording_transfer_poll_budget(&transfer, advancing_clock, &tick, &capture_pair) == COMP_WBA_RECORDING_TRANSFER_ACTIVE &&
          transfer.packet_ready && fixture->notification_count == 0u,
          "one millisecond budget yields after a read even across clock wrap");
    fixture->heavy_io_allowed = false;
    CHECK(comp_wba_recording_transfer_poll_budget(&transfer, fixed_clock, &tick, &capture_pair) == COMP_WBA_RECORDING_TRANSFER_ACTIVE &&
          transfer.packet_ready && fixture->notification_count == 0u && transfer.next_offset == 0u,
          "capture ownership blocks a prepared packet");
    fixture->heavy_io_allowed = true;
    CHECK(comp_wba_recording_transfer_poll_budget(&transfer, fixed_clock, &tick, &capture_pair) == COMP_WBA_RECORDING_TRANSFER_COMPLETE &&
          fixture->notification_count == 1u && transfer.next_offset == 100u,
          "prepared packet resumes unchanged");
    CHECK(comp_wba_recording_transfer_start(&transfer, &live_request) == COMP_WBA_RECORDING_TRANSFER_OK, "capture-pressure pair start");
    fixture->notification_count = 0u;
    fixture->block_after_next_read = true;
    CHECK(comp_wba_recording_transfer_poll_budget(&transfer, fixed_clock, &tick, &capture_pair) == COMP_WBA_RECORDING_TRANSFER_ACTIVE &&
          transfer.packet_ready && fixture->notification_count == 0u && transfer.next_offset == 0u,
          "capture pressure arriving during read prevents the same-slice notify");
    fixture->heavy_io_allowed = true;
    CHECK(comp_wba_recording_transfer_poll_budget(&transfer, fixed_clock, &tick, &capture_pair) == COMP_WBA_RECORDING_TRANSFER_COMPLETE &&
          fixture->notification_count == 1u && transfer.next_offset == 100u,
          "deferred packet resumes after capture pressure clears");
    CHECK(comp_wba_recording_transfer_start(&transfer, &live_request) == COMP_WBA_RECORDING_TRANSFER_OK, "uncontended pair start");
    fixture->notification_count = 0u;
    CHECK(comp_wba_recording_transfer_poll_budget(&transfer, fixed_clock, &tick, &capture_pair) == COMP_WBA_RECORDING_TRANSFER_COMPLETE &&
          fixture->notification_count == 1u && transfer.next_offset == 100u,
          "one prepared read and one notify share an uncontended capture slice");
    CHECK(comp_wba_recording_transfer_start(&transfer, &live_request) == COMP_WBA_RECORDING_TRANSFER_OK, "missing-clock start");
    fixture->notification_count = 0u;
    CHECK(comp_wba_recording_transfer_poll_budget(&transfer, NULL, NULL, &capture_pair) == COMP_WBA_RECORDING_TRANSFER_ACTIVE &&
          transfer.packet_ready && fixture->notification_count == 0u && transfer.next_offset == 0u,
          "a missing clock retains the single-step capture behavior");
    CHECK(comp_wba_recording_transfer_init(&transfer, config), "sealed capture slice init");
    CHECK(comp_wba_recording_transfer_set_value_capacity(&transfer, 248u), "sealed capture capacity");
    comp_wba_recording_transfer_set_connected(&transfer, true);
    CHECK(comp_wba_recording_transfer_start(&transfer, &request) == COMP_WBA_RECORDING_TRANSFER_OK,
          "sealed capture slice start");
    fixture->notification_count = 0u;
    fixture->block_after_next_read = true;
    CHECK(comp_wba_recording_transfer_poll_budget(&transfer, fixed_clock, &tick, &capture_pair) == COMP_WBA_RECORDING_TRANSFER_IDLE &&
          fixture->notification_count == 0u,
          "legacy sealed capture pressure retires the window without notification");
    fixture->heavy_io_allowed = true;
    CHECK(comp_wba_recording_transfer_start(&transfer, &request) == COMP_WBA_RECORDING_TRANSFER_OK,
          "legacy sealed transfer may be requested again after capture pressure");
    CHECK(comp_wba_recording_transfer_poll_budget(&transfer, fixed_clock, &tick, &capture_pair) == COMP_WBA_RECORDING_TRANSFER_ACTIVE &&
          fixture->notification_count == 1u && transfer.next_offset == 224u &&
          memcmp(fixture->notifications[0] + 20u, payload, 224u) == 0,
          "sealed retry delivers exact original bytes");
    return 0;
}

int main(void)
{
    fixture_t fixture;
    comp_recording_journal_t journal;
    comp_recording_journal_port_t port = {
        flash_read, flash_program, flash_erase, comp_wba_recording_crc32
    };
    comp_wba_recording_transfer_t transfer;
    comp_wba_recording_transfer_config_t config;
    uint8_t payload_a[450];
    uint8_t payload_b[73];
    uint8_t expected_sha_a[COMP_RECORDING_JOURNAL_SHA256_BYTES];
    uint8_t list[COMP_WBA_RECORDING_TRANSFER_VALUE_BYTES];
    uint32_t id_a;
    uint32_t id_b;
    comp_recording_journal_entry_t writing;
    companion_recording_adapter_request_t request;

    CHECK(crc_compatibility() == 0, "recording CRC compatibility");
    memset(&fixture, 0, sizeof(fixture));
    memset(fixture.flash, 0xFF, sizeof(fixture.flash));
    fixture.heavy_io_allowed = true;
    for (uint32_t i = 0u; i < sizeof(payload_a); ++i) {
        payload_a[i] = (uint8_t)(i * 17u + 3u);
    }
    for (uint32_t i = 0u; i < sizeof(payload_b); ++i) {
        payload_b[i] = (uint8_t)(0xE0u ^ i);
    }
    CHECK(comp_recording_journal_mount(&journal, &port, &fixture,
                                       FLASH_BYTES) ==
          COMP_RECORDING_JOURNAL_OK, "journal mount");
    CHECK(add_finalized(&journal, &fixture, payload_a, sizeof(payload_a),
                        0x20u, &id_a), "add first finalized recording");
    CHECK(add_finalized(&journal, &fixture, payload_b, sizeof(payload_b),
                        0x60u, &id_b), "add second finalized recording");
    CHECK(comp_recording_journal_begin(&journal, 512u, 1700000100u, 200u,
                                       3u, 1u, &writing) ==
          COMP_RECORDING_JOURNAL_OK, "add writing entry");
    fill_sha(expected_sha_a, 0x20u);

    config.journal = &journal;
    config.notify = notify;
    config.heavy_io_allowed = io_allowed;
    config.context = &fixture;
    config.live_entry = NULL;
    config.live_read_allowed = NULL;
    CHECK(comp_wba_recording_transfer_init(&transfer, &config),
          "transfer init");
    CHECK(comp_wba_recording_transfer_set_value_capacity(&transfer,248u), "legacy wire fixture capacity");

    size_t list_length = comp_wba_recording_transfer_build_list(
        &transfer, list, sizeof(list));
    CHECK(list_length == 4u + 2u * 32u, "list has only finalized entries");
    CHECK(list[0] == 1u && list[1] == 2u && get_le16(&list[2]) == 32u,
          "list header contract");
    CHECK(get_le32(&list[4]) == id_a && get_le32(&list[36]) == id_b,
          "list recording ids");
    CHECK(list[16] == 3u && list[17] == 0u,
          "Type expects wire UNSYNCED=0, never journal UNSYNCED=2");
    CHECK(list[19]==0u,"complete capture has no recovery flag");
    for(uint32_t n=0u;n<COMP_RECORDING_JOURNAL_MAX_ENTRIES;++n)
        if(journal.catalog.entries[n].recording_id==id_a)
            journal.catalog.entries[n].reserved|=COMP_RECORDING_RECOVERED_PREFIX;
    CHECK(comp_wba_recording_transfer_build_list(&transfer,list,sizeof(list))==list_length &&
          list[19]==1u && list[51]==0u,"incomplete recovery flag stays per recording in existing wire slot");

    memset(&request, 0, sizeof(request));
    request.schema_version = 1u;
    request.flags = COMP_WBA_RECORDING_TRANSFER_STREAM_ALL_FLAG;
    request.recording_id = id_a;
    request.host_resume_token = 0x12345678u;
    CHECK(comp_wba_recording_transfer_start(&transfer, &request) ==
          COMP_WBA_RECORDING_TRANSFER_NOT_CONNECTED,
          "disconnected start rejected");
    comp_wba_recording_transfer_set_connected(&transfer, true);
    fixture.heavy_io_allowed = false;
    CHECK(comp_wba_recording_transfer_start(&transfer, &request) ==
          COMP_WBA_RECORDING_TRANSFER_BUSY, "capture busy start rejected");
    fixture.heavy_io_allowed = true;

    request.byte_offset = sizeof(payload_a);
    CHECK(comp_wba_recording_transfer_start(&transfer, &request) ==
          COMP_WBA_RECORDING_TRANSFER_OFFSET_OUT_OF_RANGE,
          "end offset rejected");
    request.byte_offset = 0u;
    CHECK(comp_wba_recording_transfer_start(&transfer, &request) ==
          COMP_WBA_RECORDING_TRANSFER_OK, "full transfer starts");
    fixture.reject_next_notify = true;
    CHECK(comp_wba_recording_transfer_poll(&transfer) ==
          COMP_WBA_RECORDING_TRANSFER_ACTIVE, "first poll only reads");
    uint32_t reads_after_prepare = fixture.read_calls;
    uint8_t retained[COMP_WBA_RECORDING_TRANSFER_VALUE_BYTES];
    memcpy(retained, transfer.packet, transfer.packet_length);
    uint16_t retained_length = transfer.packet_length;
    CHECK(comp_wba_recording_transfer_poll(&transfer) ==
          COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED,
          "notify backpressure visible");
    CHECK(fixture.read_calls == reads_after_prepare &&
          transfer.next_offset == 0u && transfer.packet_sequence == 0u,
          "backpressure does not reread or advance");
    CHECK(memcmp(retained, transfer.packet, retained_length) == 0,
          "backpressured value retained byte-for-byte");
    CHECK(drain(&transfer) == 0, "full transfer drains");
    CHECK(fixture.notification_count == 3u, "three notifications emitted");
    const uint16_t expected_lengths[3] = {244u, 244u, 58u};
    const uint32_t expected_offsets[3] = {0u, 224u, 448u};
    const uint16_t expected_payloads[3] = {224u, 224u, 2u};
    for (uint32_t i = 0u; i < 3u; ++i) {
        const uint8_t *packet = fixture.notifications[i];
        CHECK(fixture.notification_lengths[i] == expected_lengths[i],
              "notification size");
        CHECK(packet[0] == 1u && get_le32(&packet[4]) == id_a &&
              get_le32(&packet[8]) == i &&
              get_le32(&packet[12]) == expected_offsets[i] &&
              (i!=2u || get_le32(&packet[16]) == sizeof(payload_a)) &&
              get_le16(&packet[2]) == expected_payloads[i],
              "notification header continuity");
        CHECK(get_le32(&packet[i==2u ? 20u : 16u]) == packet_crc(packet,sizeof(payload_a)),
              "packet CRC matches old WB composition");
        CHECK(memcmp(&packet[(packet[1] & 1u) ? 56u : 20u], &payload_a[expected_offsets[i]],
                     expected_payloads[i]) == 0, "packet payload bytes");
        CHECK((packet[1] & COMPANION_RECORDING_ADAPTER_FINAL_FLAG) ==
              (i == 2u ? COMPANION_RECORDING_ADAPTER_FINAL_FLAG : 0u),
              "final flag only at object end");
    }
    CHECK(memcmp(&fixture.notifications[2][24], expected_sha_a,
                 sizeof(expected_sha_a)) == 0, "final SHA exposed");
    CHECK(transfer.host_resume_token == 0x12345678u,
          "resume token retained as correlation only");

    fixture.notification_count = 0u;
    request.flags = 0u;
    request.requested_length = 210u;
    request.byte_offset = 0u;
    request.host_resume_token = 7u;
    CHECK(comp_wba_recording_transfer_start(&transfer, &request) ==
          COMP_WBA_RECORDING_TRANSFER_OK && drain(&transfer) == 0,
          "bounded window transfer");
    CHECK(fixture.notification_count == 1u &&
          get_le16(&fixture.notifications[0][2]) == 210u &&
          fixture.notification_lengths[0]==234u &&
          fixture.notifications[0][1] == 0u,
          "window length honored without false final");

    fixture.notification_count = 0u;
    request.flags = COMP_WBA_RECORDING_TRANSFER_STREAM_ALL_FLAG;
    request.requested_length = 0u;
    request.byte_offset = 0u;
    CHECK(comp_wba_recording_transfer_start(&transfer, &request) ==
          COMP_WBA_RECORDING_TRANSFER_OK, "disconnect scenario starts");
    CHECK(comp_wba_recording_transfer_poll(&transfer) ==
          COMP_WBA_RECORDING_TRANSFER_ACTIVE, "disconnect scenario read");
    CHECK(comp_wba_recording_transfer_poll(&transfer) ==
          COMP_WBA_RECORDING_TRANSFER_ACTIVE, "first packet accepted");
    CHECK(transfer.next_offset == 224u, "accepted offset advances");
    comp_wba_recording_transfer_set_connected(&transfer, false);
    CHECK(transfer.state == COMP_WBA_RECORDING_TRANSFER_IDLE &&
          transfer.recording_id == 0u && !transfer.packet_ready,
          "disconnect clears transient window");
    CHECK(comp_recording_journal_find(&journal, id_a)->sync_state ==
          COMP_RECORDING_JOURNAL_UNSYNCED,
          "disconnect leaves durable unsynced entry");
    comp_wba_recording_transfer_set_connected(&transfer, true);
    request.byte_offset = 192u;
    request.host_resume_token = 0xCAFEBABEu;
    fixture.notification_count = 0u;
    CHECK(comp_wba_recording_transfer_start(&transfer, &request) ==
          COMP_WBA_RECORDING_TRANSFER_OK && drain(&transfer) == 0,
          "host verified offset resumes");
    CHECK(get_le32(&fixture.notifications[0][8]) == 0u &&
          get_le32(&fixture.notifications[0][12]) == 192u,
          "resumed pull resets sequence and preserves absolute offset");

    request.byte_offset = 0u;
    CHECK(comp_wba_recording_transfer_start(&transfer, &request) ==
          COMP_WBA_RECORDING_TRANSFER_OK, "mid-window busy scenario starts");
    fixture.heavy_io_allowed = false;
    CHECK(comp_wba_recording_transfer_poll(&transfer) ==
          COMP_WBA_RECORDING_TRANSFER_IDLE &&
          transfer.last_result == COMP_WBA_RECORDING_TRANSFER_BUSY,
          "capture ownership cancels heavy transfer");
    fixture.heavy_io_allowed = true;

    uint32_t data_erases_before_ack = fixture.data_erase_calls;
    uint8_t payload_before_ack[sizeof(payload_a)];
    const comp_recording_journal_entry_t *entry =
        comp_recording_journal_find(&journal, id_a);
    memcpy(payload_before_ack, &fixture.flash[entry->payload_offset],
           sizeof(payload_before_ack));
    CHECK(comp_wba_recording_transfer_acknowledge(
              &transfer, id_a, sizeof(payload_a) - 1u, expected_sha_a) ==
          COMP_WBA_RECORDING_TRANSFER_ACK_MISMATCH,
          "bad total rejected");
    uint8_t bad_sha[COMP_RECORDING_JOURNAL_SHA256_BYTES];
    memcpy(bad_sha, expected_sha_a, sizeof(bad_sha));
    bad_sha[5] ^= 0x80u;
    CHECK(comp_wba_recording_transfer_acknowledge(
              &transfer, id_a, sizeof(payload_a), bad_sha) ==
          COMP_WBA_RECORDING_TRANSFER_ACK_MISMATCH,
          "bad SHA rejected");
    CHECK(comp_recording_journal_find(&journal, id_a)->sync_state ==
          COMP_RECORDING_JOURNAL_UNSYNCED,
          "failed ACK keeps unsynced state");
    CHECK(comp_wba_recording_transfer_acknowledge(
              &transfer, id_a, sizeof(payload_a), expected_sha_a) ==
          COMP_WBA_RECORDING_TRANSFER_OK,
          "exact terminal ACK accepted");
    CHECK(comp_wba_recording_transfer_acknowledge(
              &transfer, id_a, sizeof(payload_a), expected_sha_a) ==
          COMP_WBA_RECORDING_TRANSFER_OK,
          "terminal ACK retry is idempotent");
    entry = comp_recording_journal_find(&journal, id_a);
    CHECK(entry != NULL && entry->sync_state == COMP_RECORDING_JOURNAL_ACKED &&
          entry->acked_offset == entry->total_length,
          "ACKED journal terminal state");
    CHECK(fixture.data_erase_calls == data_erases_before_ack &&
          memcmp(payload_before_ack, &fixture.flash[entry->payload_offset],
                 sizeof(payload_before_ack)) == 0,
          "ACK never auto-deletes payload");

    request.recording_id = writing.recording_id;
    CHECK(comp_wba_recording_transfer_start(&transfer, &request) ==
          COMP_WBA_RECORDING_TRANSFER_NOT_FINALIZED,
          "writing entry never transfers");
    request.recording_id = id_a;
    CHECK(comp_wba_recording_transfer_start(&transfer, &request) ==
          COMP_WBA_RECORDING_TRANSFER_OK,
          "ACKED recording remains pullable until explicit reclaim");

    comp_wba_recording_transfer_stats_t stats;
    comp_wba_recording_transfer_get_stats(&transfer, &stats);
    CHECK(stats.notify_backpressure == 1u && stats.disconnects == 1u &&
          stats.ack_mismatches == 2u && stats.acknowledgements == 1u,
          "diagnostic counters");
    comp_wba_recording_transfer_cancel(&transfer);
    CHECK(comp_wba_recording_transfer_set_value_capacity(&transfer,509u) &&
          comp_wba_recording_transfer_start(&transfer,&request)==COMP_WBA_RECORDING_TRANSFER_OK,
          "new cancellation fixture explicitly uses long509 packets");
    CHECK(comp_wba_recording_transfer_poll(&transfer)==COMP_WBA_RECORDING_TRANSFER_ACTIVE,
          "prepare packet for nested cancel");
    uint32_t generation=transfer.window_generation;
    transfer.notify_staged_bytes=240u;transfer.notify_staged_lane=1u;
    fixture.invalidate_transfer=&transfer;
    CHECK(comp_wba_recording_transfer_poll(&transfer)==COMP_WBA_RECORDING_TRANSFER_IDLE &&
          transfer.window_generation!=generation && transfer.notify_staged_bytes==0u &&
          transfer.notify_staged_lane==0u && !transfer.packet_ready && transfer.next_offset==0u,
          "nested cancel cannot accept/advance stale packet or retain staging");
    CHECK(comp_wba_recording_transfer_start(&transfer,&request)==COMP_WBA_RECORDING_TRANSFER_OK &&
          comp_wba_recording_transfer_poll(&transfer)==COMP_WBA_RECORDING_TRANSFER_ACTIVE,
          "prepare packet for nested disconnect");
    generation=transfer.window_generation;
    transfer.notify_staged_bytes=480u;transfer.notify_staged_lane=2u;
    fixture.invalidate_transfer=&transfer;fixture.invalidate_disconnect=true;
    CHECK(comp_wba_recording_transfer_poll(&transfer)==COMP_WBA_RECORDING_TRANSFER_IDLE &&
          !transfer.connected && transfer.window_generation!=generation &&
          transfer.notify_staged_bytes==0u && transfer.next_offset==0u,
          "nested disconnect cannot count stale acceptance as uploaded bytes");
    comp_wba_recording_transfer_set_connected(&transfer,true);
    CHECK(comp_wba_recording_transfer_start(&transfer,&request)==COMP_WBA_RECORDING_TRANSFER_OK &&
          transfer.notify_staged_bytes==0u && transfer.notify_staged_lane==0u,
          "new pull starts without another packet/lane staging");
    printf("PASS_WBA_RECORDING_TRANSFER_HOST_ONLY packets=%lu bytes=%lu\n",
           (unsigned long)stats.packets_notified,
           (unsigned long)stats.payload_bytes_notified);
    CHECK(bulk_bounds(&fixture, &journal, &config, &writing) == 0,
          "stopped bulk bounds, backpressure, durable ownership and live fairness");
    return 0;
}
