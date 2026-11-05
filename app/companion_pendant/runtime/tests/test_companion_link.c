#include "companion_link.h"

#include <stdio.h>
#include <string.h>

#define FLASH_BYTES (64u * 1024u)
#define MAX_PUBLISHES 64u
_Static_assert(sizeof(companion_gatt_meeting_control_v1_t)==12u,
               "Type meeting wire remains exactly 12 bytes");

typedef struct {
    companion_gatt_char_id_t id;
    uint16_t length;
    uint8_t value[COMP_WBA_RECORDING_TRANSFER_VALUE_BYTES];
} published_value_t;

typedef struct {
    /* Keep runtime first so the runtime stubs can recover the fixture. */
    comp_runtime_t runtime;
    comp_wba_recording_service_t recorder;
    comp_recording_journal_t journal;
    companion_v1_features_t features;
    comp_link_t link;
    uint8_t flash[FLASH_BYTES];
    published_value_t published[MAX_PUBLISHES];
    uint32_t publish_count;
    uint32_t record_calls;
    uint32_t connect_calls;
    uint32_t data_erase_calls;
    uint32_t catalog_erase_calls;
    uint32_t fail_catalog_erase_after;
    uint32_t nor_calls;
    bool last_record_start;
    bool publish_allowed;
    bool fail_next_data_erase;
    bool short_next_catalog_program;
    comp_runtime_result_t record_result;
    uint32_t random_counter;
    bool random_failed;
} fixture_t;

static int fail_line(int line, const char *message)
{
    fprintf(stderr, "FAIL line=%d %s\n", line, message);
    return line;
}

#define CHECK(expression, message) \
    do { if (!(expression)) return fail_line(__LINE__, message); } while (0)

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

static bool flash_read(void *context, uint32_t offset, uint8_t *destination,
                       uint32_t length)
{
    fixture_t *fixture = context;
    ++fixture->nor_calls;
    if (destination == NULL || offset > FLASH_BYTES ||
        length > FLASH_BYTES - offset) return false;
    memcpy(destination, &fixture->flash[offset], length);
    return true;
}

static bool flash_program(void *context, uint32_t offset,
                          const uint8_t *source, uint32_t length)
{
    fixture_t *fixture = context;
    ++fixture->nor_calls;
    bool short_write = offset >= FLASH_BYTES -
        COMP_RECORDING_JOURNAL_CATALOG_SECTORS *
            COMP_RECORDING_JOURNAL_SECTOR_BYTES &&
        fixture->short_next_catalog_program;
    if (source == NULL || offset > FLASH_BYTES ||
        length > FLASH_BYTES - offset) return false;
    if (short_write) {
        fixture->short_next_catalog_program = false;
        length /= 2u;
    }
    for (uint32_t i = 0u; i < length; ++i) {
        if ((fixture->flash[offset + i] & source[i]) != source[i]) return false;
        fixture->flash[offset + i] &= source[i];
    }
    return !short_write;
}

static bool flash_erase(void *context, uint32_t offset, uint32_t length)
{
    fixture_t *fixture = context;
    ++fixture->nor_calls;
    if (offset > FLASH_BYTES || length > FLASH_BYTES - offset ||
        (offset % COMP_RECORDING_JOURNAL_SECTOR_BYTES) != 0u ||
        (length % COMP_RECORDING_JOURNAL_SECTOR_BYTES) != 0u) return false;
    if (offset < FLASH_BYTES -
            COMP_RECORDING_JOURNAL_CATALOG_SECTORS *
                COMP_RECORDING_JOURNAL_SECTOR_BYTES) {
        fixture->data_erase_calls++;
        if (fixture->fail_next_data_erase) {
            fixture->fail_next_data_erase = false;
            return false;
        }
    } else {
        fixture->catalog_erase_calls++;
        if (fixture->fail_catalog_erase_after != 0u &&
            --fixture->fail_catalog_erase_after == 0u) return false;
    }
    memset(&fixture->flash[offset], 0xFF, length);
    return true;
}

static const comp_recording_journal_port_t journal_port = {
    flash_read, flash_program, flash_erase, crc32_port
};

static bool publish_value(void *context, companion_gatt_char_id_t id,
                          const uint8_t *value, uint16_t length)
{
    fixture_t *fixture = context;
    if (!fixture->publish_allowed || value == NULL ||
        length > COMP_WBA_RECORDING_TRANSFER_VALUE_BYTES ||
        fixture->publish_count >= MAX_PUBLISHES) return false;
    published_value_t *published = &fixture->published[fixture->publish_count++];
    published->id = id;
    published->length = length;
    memcpy(published->value, value, length);
    return true;
}

/* Link against the real portable link while keeping the much larger UI/audio
 * runtime outside this focused host test. These stubs model its documented
 * request-token and asynchronous-start contract. */
bool comp_wba_recording_service_live_entry(
    const comp_wba_recording_service_t *service,
    comp_recording_journal_entry_t *entry)
{
    /* Production durable-prefix parsing is exercised with real libopus by
     * test_wba_recording_service_real_opus.c, not duplicated in this fixture. */
    (void)service;
    (void)entry;
    return false;
}
void comp_runtime_set_connected(comp_runtime_t *runtime, bool connected,
                                uint32_t now_ms)
{
    fixture_t *fixture = (fixture_t *)runtime;
    (void)now_ms;
    runtime->connected = connected;
    fixture->connect_calls++;
}

/* Optional affected product callback; default legacy fixture is unchanged. */
static bool (*comp_link_test_record_hook)(comp_runtime_t *,bool);
comp_runtime_result_t comp_runtime_record(comp_runtime_t *runtime, bool start,
                                          uint32_t now_ms)
{
    fixture_t *fixture = (fixture_t *)runtime;
    (void)now_ms;
    fixture->record_calls++;
    fixture->last_record_start = start;
    if (fixture->record_result != COMP_RUNTIME_OK) return fixture->record_result;
    if (start) {
        if (++runtime->record_token == 0u) ++runtime->record_token;
        runtime->command_pending = true;
        runtime->prepare_pending = true;
    } else {
        runtime->stop_pending = true;
    }
    if(comp_link_test_record_hook&&!comp_link_test_record_hook(runtime,start))return COMP_RUNTIME_BACKEND_FAILED;
    return COMP_RUNTIME_OK;
}

/* This focused port records the requested limit; real scheduling/prepare is
 * exercised by the separate runtime and product recording integration. */
comp_runtime_result_t comp_runtime_record_start_limited(comp_runtime_t *runtime,
                                                      uint16_t seconds,uint32_t now)
{
    comp_runtime_result_t result=comp_runtime_record(runtime,true,now);
    if (result==COMP_RUNTIME_OK)runtime->record_limit_seconds=seconds ? seconds :
        (uint32_t)runtime->menu.browser.recording_limit_minutes*60u;
    return result;
}
/* Runtime scheduling is a port here; the independent product integration
 * exercises the actual runtime stop path. Preserve the requested cause for
 * the link's duration-stop branch without pretending this shim is that path. */
comp_runtime_result_t comp_runtime_record_stop(comp_runtime_t *runtime,
    comp_runtime_record_stop_reason_t reason,uint32_t now)
{
    runtime->record_stop_reason=(uint8_t)reason;
    return comp_runtime_record(runtime,false,now);
}
companion_v1_result_t companion_v1_apply_speaker_control(
    companion_v1_features_t *features,
    const companion_gatt_speaker_control_v1_t *request,
    uint32_t now_ms)
{
    (void)now_ms;
    features->speaker.schema_version = 1u;
    features->speaker.state = COMPANION_V1_SPEAKER_STATE_PROMPT_ACCEPTED;
    features->speaker.request_id = request->request_id;
    features->speaker.prompt_id = request->prompt_id;
    return COMPANION_V1_RESULT_OK;
}

static bool fixture_random(void *context,uint32_t *value)
{
    fixture_t *f=context;
    if(f->random_failed)return false;
    *value=0xDC000000u+(++f->random_counter);return true;
}
static bool initialize(fixture_t *fixture, uint32_t *recording_id)
{
    comp_link_config_t config;
    comp_recording_journal_entry_t entry;
    uint8_t sha[COMP_RECORDING_JOURNAL_SHA256_BYTES];
    const uint8_t payload[] = {0x43u, 0x4Fu, 0x50u, 0x31u, 1u, 2u, 3u, 4u};

    memset(fixture, 0, sizeof(*fixture));
    memset(fixture->flash, 0xFF, sizeof(fixture->flash));
    fixture->publish_allowed = true;
    fixture->record_result = COMP_RUNTIME_OK;
    fixture->recorder.state = COMP_WBA_RECORDING_IDLE;
    fixture->runtime.recording = DENZIC_AUDIO_RECORDING_STATE_IDLE;
    fixture->runtime.config.context=fixture;
    fixture->runtime.config.random_u32=fixture_random;
    fixture->features.imu.schema_version = 1u;
    fixture->features.speaker.schema_version = 1u;
    if (comp_recording_journal_mount(&fixture->journal, &journal_port, fixture,
                                     FLASH_BYTES) !=
        COMP_RECORDING_JOURNAL_OK) return false;
    if (comp_recording_journal_begin(&fixture->journal, sizeof(payload),
                                     1700000000u, 100u, 3u, 1u, &entry) !=
        COMP_RECORDING_JOURNAL_OK) return false;
    if (!flash_erase(fixture, entry.extent_offset, entry.reserved_bytes) ||
        !flash_program(fixture, entry.payload_offset, payload,
                       (uint32_t)sizeof(payload))) return false;
    memset(sha, 0xA5, sizeof(sha));
    if (comp_recording_journal_finalize(&fixture->journal, entry.recording_id,
                                        (uint32_t)sizeof(payload), 20u,
                                        crc32_port(0u, payload,
                                                   (uint32_t)sizeof(payload)),
                                        sha, 3u) !=
        COMP_RECORDING_JOURNAL_OK) return false;
    config.runtime = &fixture->runtime;
    config.recorder = &fixture->recorder;
    config.journal = &fixture->journal;
    config.features = &fixture->features;
    config.publish = publish_value;
    config.context = fixture;
    if (!comp_link_init(&fixture->link, &config)) return false;
    *recording_id = entry.recording_id;
    return true;
}

static void event_notify(companion_gatt_event_t *event,
                         companion_gatt_event_type_t type,
                         companion_gatt_char_id_t id)
{
    memset(event, 0, sizeof(*event));
    event->type = type;
    event->char_id = id;
}

static void event_write(companion_gatt_event_t *event,
                        companion_gatt_char_id_t id,
                        const void *payload, uint16_t length)
{
    memset(event, 0, sizeof(*event));
    event->type = COMPANION_GATT_EVENT_WRITE;
    event->char_id = id;
    event->payload_len = length;
    memcpy(event->payload, payload, length);
}

static uint32_t count_published(const fixture_t *fixture,
                                companion_gatt_char_id_t id)
{
    uint32_t count = 0u;
    for (uint32_t i = 0u; i < fixture->publish_count; ++i) {
        if (fixture->published[i].id == id) ++count;
    }
    return count;
}

static const companion_gatt_meeting_status_v1_t *last_meeting_status(
    const fixture_t *fixture)
{
    for (uint32_t i=fixture->publish_count;i>0u;--i) {
        const published_value_t *value=&fixture->published[i-1u];
        if(value->id==COMPANION_GATT_CHAR_MEETING_STATUS&&
           value->length==sizeof(companion_gatt_meeting_status_v1_t))
            return (const companion_gatt_meeting_status_v1_t *)value->value;
    }
    return NULL;
}

static bool add_recording(fixture_t *fixture, uint32_t reserve,
                          uint8_t marker, bool finalized, bool acked,
                          comp_recording_journal_entry_t *entry)
{
    uint8_t payload[32], sha[COMP_RECORDING_JOURNAL_SHA256_BYTES];
    memset(payload, marker, sizeof(payload));
    memset(sha, marker, sizeof(sha));
    if (comp_recording_journal_begin(&fixture->journal, reserve, 0u, 0u,
                                     3u, 1u, entry) !=
            COMP_RECORDING_JOURNAL_OK ||
        !flash_erase(fixture, entry->extent_offset, entry->reserved_bytes) ||
        !flash_program(fixture, entry->payload_offset, payload,
                        sizeof(payload))) return false;
    if (!finalized) return true;
    if (comp_recording_journal_finalize(&fixture->journal, entry->recording_id,
            sizeof(payload), 20u, crc32_port(0u, payload, sizeof(payload)),
            sha, 3u) != COMP_RECORDING_JOURNAL_OK) return false;
    return !acked || comp_recording_journal_ack_complete(&fixture->journal,
        entry->recording_id, sizeof(payload), sha) == COMP_RECORDING_JOURNAL_OK;
}

static bool remount_link(fixture_t *fixture)
{
    comp_link_config_t config = fixture->link.config;
    return comp_recording_journal_mount_strict(&fixture->journal, &journal_port,
        fixture, FLASH_BYTES) == COMP_RECORDING_JOURNAL_OK &&
        comp_link_init(&fixture->link, &config);
}

static bool bytes_equal(const fixture_t *fixture, uint32_t offset,
                         uint32_t length, uint8_t expected)
{
    for (uint32_t i = 0u; i < length; ++i) {
        if (fixture->flash[offset + i] != expected) return false;
    }
    return true;
}

static int test_acked_reboot_recovery(void)
{
    fixture_t fixture;
    uint32_t id;
    comp_recording_journal_entry_t unsynced, writing, consumed;
    const comp_recording_journal_entry_t *entry;
    uint8_t sha[COMP_RECORDING_JOURNAL_SHA256_BYTES];
    companion_gatt_event_t event;
    companion_recording_adapter_request_t pull = {0};
    CHECK(initialize(&fixture, &id), "ACKED reboot fixture");
    memset(sha, 0xA5, sizeof(sha));
    CHECK(comp_recording_journal_ack_complete(&fixture.journal, id, 8u, sha) ==
              COMP_RECORDING_JOURNAL_OK, "persist consumed ACKED only");
    CHECK(add_recording(&fixture, 4096u, 0x62u, true, false, &unsynced) &&
          add_recording(&fixture, 4096u, 0x73u, false, false, &writing) &&
          add_recording(&fixture, 8192u, 0x84u, true, true, &consumed),
          "mixed consumed, unsynced and WRITING durable records");
    uint32_t erases = fixture.data_erase_calls;
    uint32_t catalogs = fixture.catalog_erase_calls;
    uint32_t generation = fixture.journal.catalog.generation;
    CHECK(remount_link(&fixture), "power loss in ACKED/ERASING gap");
    CHECK(fixture.data_erase_calls == erases &&
          fixture.catalog_erase_calls == catalogs,
          "initialization performs no flash recovery writes");

    /* Each foreground owner independently excludes automatic recovery. */
    fixture.runtime.capture_active = true;
    comp_link_poll(&fixture.link, 10u);
    fixture.runtime.capture_active = false;
    fixture.runtime.prepare_pending = true;
    comp_link_poll(&fixture.link, 11u);
    fixture.runtime.prepare_pending = false;
    fixture.runtime.start_pending = true;
    comp_link_poll(&fixture.link, 12u);
    fixture.runtime.start_pending = false;
    fixture.runtime.command_pending = true;
    comp_link_poll(&fixture.link, 13u);
    fixture.runtime.command_pending = false;
    fixture.recorder.state = COMP_WBA_RECORDING_PREPARING;
    comp_link_poll(&fixture.link, 14u);
    fixture.recorder.state = COMP_WBA_RECORDING_IDLE;
    fixture.link.maintenance = true;
    comp_link_poll(&fixture.link, 15u);
    fixture.link.maintenance = false;
    CHECK(!fixture.link.io.legacy.reclaim.active &&
          fixture.journal.catalog.generation == generation &&
          fixture.data_erase_calls == erases,
          "capture, preparation, commands and OTA defer ACKED discovery");

    comp_link_connection(&fixture.link, true, true, 20u);
    event_notify(&event, COMPANION_GATT_EVENT_NOTIFY_ENABLED,
                 COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL);
    comp_link_event(&fixture.link, &event, 21u);
    pull.schema_version = 1u; pull.recording_id = id;
    pull.flags = COMP_WBA_RECORDING_TRANSFER_STREAM_ALL_FLAG;
    event_write(&event, COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,
                &pull, sizeof(pull));
    comp_link_event(&fixture.link, &event, 22u);
    fixture.publish_allowed = false;
    comp_link_poll(&fixture.link, 23u);
    comp_link_poll(&fixture.link, 24u);
    CHECK(fixture.link.transfer.state == COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED &&
          !fixture.link.io.legacy.reclaim.active &&
          fixture.journal.catalog.generation == generation &&
          fixture.data_erase_calls == erases,
          "active and backpressured pull retain consumed payload");
    fixture.publish_allowed = true;
    comp_link_poll(&fixture.link, 25u);
    CHECK(fixture.link.transfer.state == COMP_WBA_RECORDING_TRANSFER_COMPLETE &&
          !fixture.link.io.legacy.reclaim.active &&
          fixture.journal.catalog.generation == generation,
          "transfer completion and reclaim marker use separate polls");
    comp_link_connection(&fixture.link, false, false, 26u);

    fixture.short_next_catalog_program = true;
    comp_link_poll(&fixture.link, 30u);
    CHECK(fixture.link.io.legacy.reclaim.active && fixture.link.io.legacy.reclaim.recording_id == id &&
          fixture.link.io.legacy.reclaim.last_result == COMP_RECORDING_JOURNAL_IO_ERROR &&
          fixture.data_erase_calls == erases &&
          comp_recording_journal_find(&fixture.journal, id)->sync_state ==
              COMP_RECORDING_JOURNAL_ACKED,
          "partial ERASING commit leaves oldest ACKED payload untouched");
    CHECK(remount_link(&fixture) &&
          comp_recording_journal_find(&fixture.journal, id)->sync_state ==
              COMP_RECORDING_JOURNAL_ACKED,
          "reboot ignores torn marker catalog and retains consumed identity");
    comp_link_poll(&fixture.link, 40u);
    CHECK(fixture.link.io.legacy.reclaim.active && fixture.link.io.legacy.reclaim.recording_id == id &&
          fixture.data_erase_calls == erases &&
          comp_recording_journal_find(&fixture.journal, id)->sync_state ==
              COMP_RECORDING_JOURNAL_ERASING,
          "automatic recovery durably marks without same-poll payload erase");
    catalogs = fixture.catalog_erase_calls;
    CHECK(remount_link(&fixture) && fixture.link.io.legacy.reclaim.active &&
          fixture.link.io.legacy.reclaim.cursor == 0u &&
          fixture.catalog_erase_calls == catalogs,
          "second reboot resumes durable marker without rewriting it");
    comp_link_poll(&fixture.link, 41u);
    CHECK(fixture.data_erase_calls == erases + 1u &&
          comp_recording_journal_find(&fixture.journal, id) != NULL,
          "one payload sector per poll; final catalog removal is separate");
    comp_link_poll(&fixture.link, 42u);
    CHECK(comp_recording_journal_find(&fixture.journal, id) == NULL &&
          !fixture.link.io.legacy.reclaim.response_pending,
          "automatic recovery frees consumed entry without inventing a response");
    erases = fixture.data_erase_calls;
    comp_link_poll(&fixture.link, 43u);
    CHECK(fixture.link.io.legacy.reclaim.recording_id == consumed.recording_id &&
          fixture.data_erase_calls == erases,
          "next consumed entry is marked after oldest completes");
    comp_link_poll(&fixture.link, 44u);
    CHECK(fixture.link.io.legacy.reclaim.cursor == COMP_RECORDING_JOURNAL_SECTOR_BYTES,
          "multi-sector consumed extent advances one sector");
    CHECK(remount_link(&fixture) && fixture.link.io.legacy.reclaim.cursor == 0u,
          "repeated power loss loses only bounded RAM cursor");
    for (uint32_t tick = 45u; tick < 51u; ++tick)
        comp_link_poll(&fixture.link, tick);
    CHECK(comp_recording_journal_find(&fixture.journal, consumed.recording_id) == NULL &&
          bytes_equal(&fixture, consumed.extent_offset, consumed.reserved_bytes, 0xFFu),
          "rebooted multi-sector consumed extent is physically erased");
    entry = comp_recording_journal_find(&fixture.journal, unsynced.recording_id);
    CHECK(entry && entry->sync_state == COMP_RECORDING_JOURNAL_UNSYNCED &&
          bytes_equal(&fixture, unsynced.payload_offset, 32u, 0x62u),
          "other unconsumed finalized recording remains byte-for-byte intact");
    entry = comp_recording_journal_find(&fixture.journal, writing.recording_id);
    CHECK(entry && entry->sync_state == COMP_RECORDING_JOURNAL_WRITING &&
          bytes_equal(&fixture, writing.payload_offset, 32u, 0x73u) &&
          count_published(&fixture, COMPANION_GATT_CHAR_DELETE_PRIVACY) == 0u,
          "automatic recovery never erases WRITING or fabricates deletion success");
    return 0;
}

static int test_acked_live_gap_and_backoff(void)
{
    fixture_t fixture;
    comp_recording_journal_entry_t later_consumed;
    companion_gatt_event_t event;
    companion_gatt_delete_privacy_v1_t deletion = {0};
    uint32_t id;
    CHECK(initialize(&fixture, &id), "live ACKED gap fixture");
    CHECK(add_recording(&fixture, 4096u, 0x91u, true, true, &later_consumed),
          "another consumed entry must not replace a pending completion");
    comp_link_connection(&fixture.link, true, true, 1u);
    deletion.schema_version = 1u; deletion.operation = 1u;
    deletion.request_id = 0x101u; deletion.recording_id = id;
    deletion.validated_total_length = 8u;
    memset(deletion.validated_sha256, 0xA5, sizeof(deletion.validated_sha256));
    event_write(&event, COMPANION_GATT_CHAR_DELETE_PRIVACY, &deletion,
                sizeof(deletion));
    uint32_t erases = fixture.data_erase_calls;
    uint32_t io = fixture.nor_calls;
    fixture.fail_catalog_erase_after = 2u;
    comp_link_event(&fixture.link, &event, 2u);
    CHECK(fixture.nor_calls == io && fixture.link.io.legacy.reclaim.active &&
          fixture.link.io.legacy.reclaim.response_pending &&
          comp_recording_journal_find(&fixture.journal, id)->sync_state ==
              COMP_RECORDING_JOURNAL_UNSYNCED,
          "exact GATT consume queues in RAM with zero NOR I/O or early success");
    comp_link_poll(&fixture.link, 2u);
    CHECK(comp_recording_journal_find(&fixture.journal, id)->sync_state ==
              COMP_RECORDING_JOURNAL_ACKED &&
          fixture.link.transfer.stats.acknowledgements == 1u &&
          fixture.data_erase_calls == erases &&
          count_published(&fixture, COMPANION_GATT_CHAR_DELETE_PRIVACY) == 0u,
          "first foreground poll persists only ACK and withholds completion");
    comp_link_connection(&fixture.link, false, false, 3u);
    fixture.fail_catalog_erase_after = 1u;
    comp_link_poll(&fixture.link, UINT32_MAX - 999u);
    CHECK(fixture.link.io.legacy.reclaim.active &&
          fixture.link.io.legacy.reclaim.last_result == COMP_RECORDING_JOURNAL_IO_ERROR,
          "live ACKED leftover is discovered without reboot or host retry");
    uint32_t catalogs = fixture.catalog_erase_calls;
    comp_link_poll(&fixture.link, UINT32_MAX);
    CHECK(fixture.catalog_erase_calls == catalogs &&
          fixture.data_erase_calls == erases,
          "marker retry does not fire early when deadline wraps to zero");
    comp_link_poll(&fixture.link, 0u);
    CHECK(comp_recording_journal_find(&fixture.journal, id)->sync_state ==
              COMP_RECORDING_JOURNAL_ERASING &&
          fixture.catalog_erase_calls == catalogs + 1u &&
          fixture.data_erase_calls == erases,
          "marker retry at wrapped zero persists before any payload erase");
    comp_link_connection(&fixture.link, true, true, 1u);
    event_notify(&event,COMPANION_GATT_EVENT_NOTIFY_ENABLED,COMPANION_GATT_CHAR_DELETE_PRIVACY);
    comp_link_event(&fixture.link,&event,1u);
    deletion.validated_sha256[0] ^= 1u;
    event_write(&event, COMPANION_GATT_CHAR_DELETE_PRIVACY, &deletion,
                sizeof(deletion));
    comp_link_event(&fixture.link, &event, 1u);
    CHECK(fixture.link.io.legacy.reclaim.response_pending &&
          fixture.link.io.legacy.reclaim.response.validated_sha256[0] == 0xA5u,
          "wrong proof cannot replace the queued exact receipt during recovery");
    deletion.validated_sha256[0] ^= 1u;
    event_write(&event, COMPANION_GATT_CHAR_DELETE_PRIVACY, &deletion,
                sizeof(deletion));
    comp_link_event(&fixture.link, &event, 2u);
    uint32_t generation = fixture.journal.catalog.generation;
    comp_link_event(&fixture.link, &event, 3u);
    CHECK(fixture.link.io.legacy.reclaim.response_pending &&
          fixture.link.transfer.stats.acknowledgements == 1u &&
          fixture.journal.catalog.generation == generation,
          "exact host retry joins recovered erase without a second ACK or commit");
    fixture.runtime.capture_active = true;
    comp_link_poll(&fixture.link, 4u);
    fixture.runtime.capture_active = false;
    fixture.link.maintenance = true;
    comp_link_poll(&fixture.link, 5u);
    fixture.link.maintenance = false;
    CHECK(fixture.data_erase_calls == erases,
          "recovered physical erasure still defers to capture and OTA");
    fixture.fail_next_data_erase = true;
    comp_link_poll(&fixture.link, 6u);
    comp_link_poll(&fixture.link, 1005u);
    CHECK(fixture.data_erase_calls == erases + 1u &&
          fixture.link.io.legacy.reclaim.cursor == 0u,
          "recovered erase error retries with one-second backoff");
    comp_link_poll(&fixture.link, 1006u);
    CHECK(fixture.link.io.legacy.reclaim.cursor == COMP_RECORDING_JOURNAL_SECTOR_BYTES,
          "recovered erase retries only the failed sector");
    fixture.short_next_catalog_program = true;
    comp_link_poll(&fixture.link, 1007u);
    CHECK(comp_recording_journal_find(&fixture.journal, id) != NULL &&
          fixture.link.io.legacy.reclaim.response_pending &&
          fixture.link.io.legacy.reclaim.last_result == COMP_RECORDING_JOURNAL_IO_ERROR,
          "torn final catalog removal still withholds host success");
    uint32_t responses = count_published(&fixture, COMPANION_GATT_CHAR_DELETE_PRIVACY);
    fixture.publish_allowed = false;
    comp_link_poll(&fixture.link, 2007u);
    CHECK(comp_recording_journal_find(&fixture.journal, id) == NULL &&
          fixture.link.io.legacy.reclaim.complete && fixture.link.io.legacy.reclaim.response_pending,
          "notification backpressure retains completed exact response");
    comp_link_poll(&fixture.link, 2008u);
    CHECK(comp_recording_journal_find(&fixture.journal,
              later_consumed.recording_id)->sync_state == COMP_RECORDING_JOURNAL_ACKED &&
          fixture.link.io.legacy.reclaim.recording_id == id && !fixture.link.io.legacy.reclaim.active,
          "pending exact completion excludes discovery of a different consumed entry");
    fixture.publish_allowed = true;
    comp_link_poll(&fixture.link, 2106u);
    CHECK(count_published(&fixture, COMPANION_GATT_CHAR_DELETE_PRIVACY) == responses,
          "completion publication respects its own retry backoff");
    comp_link_poll(&fixture.link, 2107u);
    CHECK(count_published(&fixture, COMPANION_GATT_CHAR_DELETE_PRIVACY) == responses + 1u &&
          !fixture.link.io.legacy.reclaim.response_pending,
          "success echo appears only after physical erase and durable catalog removal");
    comp_link_poll(&fixture.link, 2108u);
    CHECK(fixture.link.io.legacy.reclaim.recording_id == later_consumed.recording_id &&
          comp_recording_journal_find(&fixture.journal,
              later_consumed.recording_id)->sync_state == COMP_RECORDING_JOURNAL_ERASING,
          "other consumed recovery resumes after exact response is published");
    return 0;
}

static int test_failed_ack_protects_payload(void)
{
    fixture_t fixture;
    companion_gatt_event_t event;
    companion_gatt_delete_privacy_v1_t deletion = {0};
    uint32_t id;
    CHECK(initialize(&fixture, &id), "failed ACK protection fixture");
    comp_link_connection(&fixture.link, true, true, 1u);
    deletion.schema_version = 1u; deletion.operation = 1u;
    deletion.recording_id = id; deletion.validated_total_length = 8u;
    memset(deletion.validated_sha256, 0xA5, sizeof(deletion.validated_sha256));
    event_write(&event, COMPANION_GATT_CHAR_DELETE_PRIVACY, &deletion,
                sizeof(deletion));
    uint32_t erases = fixture.data_erase_calls;
    fixture.short_next_catalog_program = true;
    comp_link_event(&fixture.link, &event, 2u);
    CHECK(fixture.short_next_catalog_program,
          "GATT callback never attempts the queued ACK catalog program");
    CHECK(remount_link(&fixture) && !fixture.link.io.legacy.reclaim.active &&
          comp_recording_journal_find(&fixture.journal, id)->sync_state ==
              COMP_RECORDING_JOURNAL_UNSYNCED &&
          fixture.data_erase_calls == erases,
          "reset before first ACK commit loses only RAM intent and keeps original protected");
    comp_link_connection(&fixture.link, true, true, 2u);
    comp_link_event(&fixture.link, &event, 2u);
    uint32_t io = fixture.nor_calls;
    fixture.runtime.capture_active = true;
    comp_link_poll(&fixture.link, 2u);
    fixture.runtime.capture_active = false;
    fixture.link.maintenance = true;
    comp_link_poll(&fixture.link, 2u);
    fixture.link.maintenance = false;
    CHECK(fixture.nor_calls == io && fixture.short_next_catalog_program,
          "queued ACK itself also defers to capture and OTA before any NOR I/O");
    comp_link_poll(&fixture.link, 2u);
    CHECK(fixture.link.transfer.stats.acknowledgements == 0u &&
          comp_recording_journal_find(&fixture.journal, id)->sync_state ==
              COMP_RECORDING_JOURNAL_UNSYNCED,
          "failed durable ACK never becomes consumed in RAM");
    CHECK(remount_link(&fixture), "reboot after a partial ACK catalog write");
    for (uint32_t tick = 3u; tick < 20u; ++tick)
        comp_link_poll(&fixture.link, tick);
    const comp_recording_journal_entry_t *entry =
        comp_recording_journal_find(&fixture.journal, id);
    CHECK(entry && entry->sync_state == COMP_RECORDING_JOURNAL_UNSYNCED &&
          fixture.data_erase_calls == erases && !fixture.link.io.legacy.reclaim.active &&
          fixture.flash[entry->payload_offset] == 0x43u,
          "automatic recovery leaves uncommitted ACK and original bytes protected");
    return 0;
}

static int test_clear_queue_with_exact_retry(void)
{
    fixture_t fixture;
    comp_recording_journal_entry_t other;
    companion_gatt_event_t event;
    companion_gatt_delete_privacy_v1_t deletion = {0};
    uint32_t id;
    CHECK(initialize(&fixture, &id) &&
          add_recording(&fixture, 4096u, 0x92u, true, false, &other),
          "multi-record confirmed clear fixture");
    CHECK(comp_link_discard_all_confirmed(&fixture.link),
          "confirmed clear starts bounded erase queue");
    comp_link_connection(&fixture.link, true, true, 1u);
    event_notify(&event,COMPANION_GATT_EVENT_NOTIFY_ENABLED,COMPANION_GATT_CHAR_DELETE_PRIVACY);
    comp_link_event(&fixture.link,&event,1u);
    deletion.schema_version = 1u; deletion.operation = 1u;
    deletion.recording_id = id; deletion.validated_total_length = 8u;
    memset(deletion.validated_sha256, 0xA5, sizeof(deletion.validated_sha256));
    event_write(&event, COMPANION_GATT_CHAR_DELETE_PRIVACY, &deletion,
                sizeof(deletion));
    comp_link_event(&fixture.link, &event, 2u);
    CHECK(fixture.link.io.legacy.reclaim.response_pending,
          "matching host retry attaches while confirmed clear is active");
    comp_link_poll(&fixture.link, 3u);
    comp_link_poll(&fixture.link, 4u);
    CHECK(comp_recording_journal_find(&fixture.journal, id) == NULL &&
          count_published(&fixture, COMPANION_GATT_CHAR_DELETE_PRIVACY) == 1u &&
          fixture.link.io.legacy.reclaim.active &&
          fixture.link.io.legacy.reclaim.recording_id == other.recording_id,
          "success publication keeps remaining clear queue continuously busy");
    comp_link_poll(&fixture.link, 5u);
    comp_link_poll(&fixture.link, 6u);
    CHECK(!fixture.link.io.legacy.reclaim.active &&
          comp_recording_journal_count(&fixture.journal) == 0u &&
          bytes_equal(&fixture, other.extent_offset, other.reserved_bytes, 0xFFu),
          "clear completion requires every queued extent physically gone");
    return 0;
}

static int test_meeting_control(void)
{
    fixture_t fixture;companion_gatt_event_t event;
    companion_gatt_meeting_control_v1_t request;
    const companion_gatt_meeting_status_v1_t *status;uint32_t recording_id;
    CHECK(initialize(&fixture,&recording_id),"meeting fixture initialization");
    comp_link_connection(&fixture.link,true,true,100u);
    event_notify(&event,COMPANION_GATT_EVENT_NOTIFY_ENABLED,
                 COMPANION_GATT_CHAR_MEETING_STATUS);
    comp_link_event(&fixture.link,&event,101u);
    CHECK(count_published(&fixture,COMPANION_GATT_CHAR_MEETING_STATUS)==1u,
          "meeting subscription publishes readable idle state");

    memset(&request,0,sizeof(request));request.schema_version=1u;request.command=1u;
    request.profile_id=1u;request.request_id=0x101u;request.max_seconds=30u;
    event_write(&event,COMPANION_GATT_CHAR_MEETING_CONTROL,&request,sizeof(request));
    comp_link_event(&fixture.link,&event,102u);status=last_meeting_status(&fixture);
    CHECK(fixture.record_calls==0u&&status&&status->request_id==request.request_id&&status->last_error!=0u,
          "Type meeting profile must select the real board microphone");

    const uint8_t type_start_wire[12]={1u,1u,0u,0u,0x02u,0x01u,0u,0u,30u,0u,2u,0u};
    request.profile_id=2u;request.request_id=0x102u;
    event_write(&event,COMPANION_GATT_CHAR_MEETING_CONTROL,type_start_wire,sizeof(type_start_wire));
    comp_link_event(&fixture.link,&event,103u);
    CHECK(fixture.record_calls==1u&&fixture.last_record_start&&
          fixture.link.meeting_record_token==fixture.runtime.record_token,
          "meeting START delegates to the existing asynchronous runtime FSM");
    comp_link_event(&fixture.link,&event,104u);
    CHECK(fixture.record_calls==1u,"duplicate meeting START is idempotent");
    request.max_seconds=31u;
    event_write(&event,COMPANION_GATT_CHAR_MEETING_CONTROL,&request,sizeof(request));
    comp_link_event(&fixture.link,&event,105u);status=last_meeting_status(&fixture);
    CHECK(fixture.record_calls==1u&&status&&status->request_id==0x102u&&
          status->last_error!=0u&&fixture.link.remote_limit_ms==30000u,
          "same meeting request id with different arguments is rejected as a collision");
    request.max_seconds=30u;

    fixture.runtime.command_pending=false;fixture.runtime.prepare_pending=false;
    fixture.runtime.capture_active=true;fixture.runtime.recording_since_ms=150u;
    fixture.runtime.recording=DENZIC_AUDIO_RECORDING_STATE_RECORDING;
    fixture.recorder.token=fixture.link.meeting_record_token;
    fixture.recorder.entry.recording_id=recording_id;
    fixture.recorder.state=COMP_WBA_RECORDING_CAPTURING;
    comp_link_poll(&fixture.link,200u);status=last_meeting_status(&fixture);
    CHECK(status&&status->request_id==0x102u&&status->state==1u&&
          status->meeting_id==recording_id&&status->duration_ms==50u&&status->sync_state==1u,
          "meeting becomes RECORDING only after real capture owns a journal id");
    uint32_t meeting_publishes=count_published(&fixture,COMPANION_GATT_CHAR_MEETING_STATUS);
    comp_link_poll(&fixture.link,201u);
    CHECK(count_published(&fixture,COMPANION_GATT_CHAR_MEETING_STATUS)==meeting_publishes,
          "steady capture does not flood BLE with per-poll duration updates");
    request.request_id=0x103u;
    event_write(&event,COMPANION_GATT_CHAR_MEETING_CONTROL,&request,sizeof(request));
    comp_link_event(&fixture.link,&event,202u);status=last_meeting_status(&fixture);
    CHECK(fixture.record_calls==1u&&status&&status->request_id==0x103u&&status->last_error!=0u,
          "a second START cannot replace the active meeting");

    request.command=2u;request.request_id=0x202u;
    event_write(&event,COMPANION_GATT_CHAR_MEETING_CONTROL,&request,sizeof(request));
    comp_link_event(&fixture.link,&event,201u);
    CHECK(fixture.record_calls==2u&&!fixture.last_record_start,
          "meeting STOP delegates to the same runtime FSM");
    comp_link_event(&fixture.link,&event,202u);
    CHECK(fixture.record_calls==2u,"duplicate meeting STOP is idempotent");
    fixture.runtime.capture_active=false;fixture.runtime.stop_pending=false;
    fixture.runtime.recording=DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY;
    fixture.recorder.state=COMP_WBA_RECORDING_TRANSFER_READY;
    comp_link_poll(&fixture.link,220u);status=last_meeting_status(&fixture);
    CHECK(status&&status->request_id==0x202u&&status->state==2u&&
          status->meeting_id==recording_id&&status->duration_ms==20u&&
          status->last_error==0u&&status->sync_state==0u,
          "STOP becomes FINALIZED only at the durable journal boundary");

    fixture.link.meeting_command=1u;
    request.command=1u;request.request_id=0x102u;
    event_write(&event,COMPANION_GATT_CHAR_MEETING_CONTROL,&request,sizeof(request));
    comp_link_event(&fixture.link,&event,220u);status=last_meeting_status(&fixture);
    CHECK(fixture.record_calls==2u&&status&&status->request_id==0x102u&&
          status->last_error!=0u,
          "a START retry after autonomous finalization gets a correlated terminal error");
    fixture.link.meeting_command=2u;

    request.command=3u;request.request_id=0x302u;
    event_write(&event,COMPANION_GATT_CHAR_MEETING_CONTROL,&request,sizeof(request));
    comp_link_event(&fixture.link,&event,221u);comp_link_poll(&fixture.link,222u);
    status=last_meeting_status(&fixture);
    CHECK(fixture.record_calls==2u&&status&&status->request_id==0x302u&&
          status->state==2u&&status->meeting_id==recording_id,
          "FINALIZE correlates the Type request without creating another recording");
    request.command=1u;request.request_id=0x102u;
    event_write(&event,COMPANION_GATT_CHAR_MEETING_CONTROL,&request,sizeof(request));
    comp_link_event(&fixture.link,&event,223u);status=last_meeting_status(&fixture);
    CHECK(fixture.record_calls==2u&&status&&status->request_id==0x102u&&
          status->last_error!=0u,
          "a terminal START retry gets a correlated error instead of timing out on a later request id");
    return 0;
}

static int test_ended_meeting_read_after_disconnect(void)
{
    fixture_t f; companion_gatt_event_t event; uint32_t id;
    companion_gatt_meeting_control_v1_t request={0};
    const companion_gatt_meeting_status_v1_t *status;
    CHECK(initialize(&f,&id),"ended reconnect fixture");
    const uint32_t catalog_generation=f.journal.catalog.generation;
    comp_link_connection(&f.link,true,true,100u);
    event_notify(&event,COMPANION_GATT_EVENT_NOTIFY_ENABLED,COMPANION_GATT_CHAR_MEETING_STATUS);
    comp_link_event(&f.link,&event,101u);
    request.schema_version=1u;request.command=1u;request.profile_id=2u;
    request.request_id=0x12345678u;request.max_seconds=5u;
    event_write(&event,COMPANION_GATT_CHAR_MEETING_CONTROL,&request,sizeof(request));
    comp_link_event(&f.link,&event,102u);
    f.runtime.command_pending=false;f.runtime.prepare_pending=false;
    f.runtime.capture_active=true;f.runtime.recording_since_ms=150u;
    f.runtime.recording=DENZIC_AUDIO_RECORDING_STATE_RECORDING;
    f.recorder.token=f.link.meeting_record_token;f.recorder.entry.recording_id=id;
    f.recorder.state=COMP_WBA_RECORDING_CAPTURING;
    comp_link_poll(&f.link,200u);status=last_meeting_status(&f);
    CHECK(status&&status->state==1u&&status->request_id==request.request_id,
          "original START reaches the readable GATT value");
    const uint32_t recording_publishes=count_published(&f,COMPANION_GATT_CHAR_MEETING_STATUS);

    comp_link_connection(&f.link,false,false,250u);
    CHECK(!f.link.subscribed[COMPANION_GATT_CHAR_MEETING_STATUS],"disconnect clears the original CCCD");
    /* The recorder has sealed its original journal entry autonomously. No
     * host STOP, FINALIZE or replacement START is sent on the new link. */
    f.runtime.capture_active=false;f.runtime.recording=DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY;
    f.recorder.state=COMP_WBA_RECORDING_TRANSFER_READY;
    comp_link_poll(&f.link,6000u);
    CHECK(f.features.meeting.state==2u&&f.link.meeting_status_dirty&&
          count_published(&f,COMPANION_GATT_CHAR_MEETING_STATUS)==recording_publishes,
          "offline finalization stays dirty without publishing outside a connection");
    comp_link_connection(&f.link,true,false,6100u);
    comp_link_poll(&f.link,6101u);
    CHECK(f.link.meeting_status_dirty&&
          count_published(&f,COMPANION_GATT_CHAR_MEETING_STATUS)==recording_publishes,
          "unencrypted reconnect cannot publish the protected meeting");
    f.publish_allowed=false;
    comp_link_connection(&f.link,true,true,6200u);
    comp_link_poll(&f.link,6201u);
    CHECK(f.link.meeting_status_dirty,"failed GATT update retains the sealed status for retry");
    f.publish_allowed=true;
    comp_link_poll(&f.link,6202u);status=last_meeting_status(&f);
    CHECK(status&&status->state==2u&&status->last_error==0u&&
          status->request_id==request.request_id&&status->meeting_id==id&&
          status->duration_ms==20u&&status->sync_state==0u&&
          !f.link.meeting_status_dirty&&!f.link.subscribed[COMPANION_GATT_CHAR_MEETING_STATUS]&&
          count_published(&f,COMPANION_GATT_CHAR_MEETING_STATUS)==recording_publishes+1u,
          "encrypted reconnect refreshes readable sealed identity without requiring a new CCCD");
    comp_link_poll(&f.link,6203u);
    CHECK(count_published(&f,COMPANION_GATT_CHAR_MEETING_STATUS)==recording_publishes+1u,
          "unchanged sealed status does not flood the link");
    CHECK(f.record_calls==1u&&f.last_record_start&&
          f.journal.catalog.generation==catalog_generation&&
          comp_recording_journal_find(&f.journal,id)->sync_state==COMP_RECORDING_JOURNAL_UNSYNCED,
          "status recovery invents no STOP, new capture, ACK or original recording consumption");
    return 0;
}

static int test_meeting_failure_retry(void)
{
    fixture_t fixture; companion_gatt_event_t event; uint32_t id;
    const companion_gatt_meeting_status_v1_t *status;
    companion_gatt_meeting_control_v1_t request={0};
    CHECK(initialize(&fixture,&id),"retry fixture");
    comp_link_connection(&fixture.link,true,true,1u);
    event_notify(&event,COMPANION_GATT_EVENT_NOTIFY_ENABLED,COMPANION_GATT_CHAR_MEETING_STATUS);
    comp_link_event(&fixture.link,&event,2u);
    request.schema_version=1u;request.command=1u;request.profile_id=2u;request.request_id=10u;
    event_write(&event,COMPANION_GATT_CHAR_MEETING_CONTROL,&request,sizeof(request));
    comp_link_event(&fixture.link,&event,3u);
    fixture.recorder.token=fixture.runtime.record_token;
    fixture.recorder.state=COMP_WBA_RECORDING_FAULT;
    fixture.runtime.recording=DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY;
    fixture.runtime.command_pending=false;fixture.runtime.prepare_pending=false;
    comp_link_poll(&fixture.link,4u);status=last_meeting_status(&fixture);
    CHECK(status&&status->request_id==10u&&status->last_error!=0u,"capture failure published");
    comp_link_event(&fixture.link,&event,5u);
    CHECK(fixture.record_calls==1u,"same failed request stays terminal and idempotent");
    request.request_id=11u;
    event_write(&event,COMPANION_GATT_CHAR_MEETING_CONTROL,&request,sizeof(request));
    comp_link_event(&fixture.link,&event,6u);comp_link_poll(&fixture.link,7u);
    status=last_meeting_status(&fixture);
    CHECK(fixture.record_calls==2u&&status&&status->request_id==11u&&status->last_error==0u,
          "new meeting after failure accepted; old recorder fault does not poison preparation");
    fixture.runtime.command_pending=false;fixture.runtime.prepare_pending=false;
    fixture.runtime.capture_active=true;fixture.runtime.recording=DENZIC_AUDIO_RECORDING_STATE_RECORDING;
    fixture.recorder.token=fixture.runtime.record_token;fixture.recorder.entry.recording_id=id;
    fixture.recorder.state=COMP_WBA_RECORDING_CAPTURING;
    comp_link_poll(&fixture.link,8u);status=last_meeting_status(&fixture);
    CHECK(status&&status->state==1u&&status->last_error==0u,"retry progresses to real capture");
    fixture.recorder.ring_count=1u;
    CHECK(!fixture.link.transfer.config.live_read_allowed(&fixture.link),"queued PCM blocks live read");
    fixture.recorder.ring_count=0u;fixture.recorder.stage_length=256u;
    CHECK(!fixture.link.transfer.config.live_read_allowed(&fixture.link),"pending page wins over live read");
    fixture.recorder.stage_length=255u;
    CHECK(fixture.link.transfer.config.live_read_allowed(&fixture.link),"idle capture slot permits bounded live read");
    fixture.link.maintenance=true;
    CHECK(!fixture.link.transfer.config.live_read_allowed(&fixture.link),"maintenance blocks live read");
    CHECK(initialize(&fixture,&id),"cancelled preparation fixture");
    comp_link_connection(&fixture.link,true,true,10u);
    event_notify(&event,COMPANION_GATT_EVENT_NOTIFY_ENABLED,COMPANION_GATT_CHAR_MEETING_STATUS);
    comp_link_event(&fixture.link,&event,11u);
    request.request_id=20u;
    event_write(&event,COMPANION_GATT_CHAR_MEETING_CONTROL,&request,sizeof(request));
    comp_link_event(&fixture.link,&event,12u);
    request.command=2u;request.request_id=21u;
    event_write(&event,COMPANION_GATT_CHAR_MEETING_CONTROL,&request,sizeof(request));
    comp_link_event(&fixture.link,&event,13u);
    fixture.runtime.command_pending=false;fixture.runtime.prepare_pending=false;
    fixture.runtime.stop_pending=false;fixture.runtime.recording=DENZIC_AUDIO_RECORDING_STATE_CANCELED;
    comp_link_poll(&fixture.link,14u);status=last_meeting_status(&fixture);
    CHECK(status&&status->request_id==21u&&status->last_error!=0u&&status->state==0u,
          "cancel before microphone starts is terminal and never claims a saved meeting");
    request.command=1u;request.request_id=22u;
    event_write(&event,COMPANION_GATT_CHAR_MEETING_CONTROL,&request,sizeof(request));
    comp_link_event(&fixture.link,&event,15u);comp_link_poll(&fixture.link,16u);
    status=last_meeting_status(&fixture);
    CHECK(fixture.record_calls==3u&&status&&status->request_id==22u&&status->last_error==0u,
          "cancelled preparation does not permanently lock out the next meeting");
    return 0;
}

static int test_storage_full_wire_status(void)
{
    fixture_t fixture; companion_gatt_event_t event; uint32_t id;
    companion_gatt_meeting_control_v1_t meeting={0};
    companion_gatt_recording_control_v1_t recording={0};
    const companion_gatt_meeting_status_v1_t *meeting_status;
    const companion_gatt_recording_control_v1_t *recording_status;

    CHECK(initialize(&fixture,&id),"storage status meeting fixture");
    comp_link_connection(&fixture.link,true,true,1u);
    event_notify(&event,COMPANION_GATT_EVENT_NOTIFY_ENABLED,
                 COMPANION_GATT_CHAR_MEETING_STATUS);
    comp_link_event(&fixture.link,&event,2u);
    fixture.recorder.last_fault_reason=COMP_WBA_RECORDING_FAULT_STORAGE_FULL;
    fixture.record_result=COMP_RUNTIME_UNAVAILABLE;
    meeting.schema_version=1u;meeting.command=1u;meeting.request_id=71u;
    meeting.profile_id=2u;
    event_write(&event,COMPANION_GATT_CHAR_MEETING_CONTROL,&meeting,sizeof(meeting));
    comp_link_event(&fixture.link,&event,3u);
    meeting_status=last_meeting_status(&fixture);
    CHECK(meeting_status&&meeting_status->request_id==71u&&
          meeting_status->last_error==COMPANION_V1_MEETING_ERROR_STORAGE_FULL,
          "meeting status distinguishes protected full storage");

    CHECK(initialize(&fixture,&id),"storage status recording fixture");
    comp_link_connection(&fixture.link,true,true,4u);
    fixture.recorder.last_fault_reason=COMP_WBA_RECORDING_FAULT_STORAGE_FULL;
    fixture.record_result=COMP_RUNTIME_UNAVAILABLE;
    recording.schema_version=1u;recording.command=1u;recording.profile_id=2u;
    recording.privacy_flags=(uint8_t)(
        COMPANION_GATT_RECORDING_STATUS_ERROR |
        COMPANION_GATT_RECORDING_STATUS_STORAGE_FULL);
    event_write(&event,COMPANION_GATT_CHAR_RECORDING_CONTROL,&recording,
                sizeof(recording));
    comp_link_event(&fixture.link,&event,5u);
    CHECK(fixture.publish_count==1u&&
          fixture.published[0].id==COMPANION_GATT_CHAR_RECORDING_CONTROL&&
          fixture.published[0].length==sizeof(recording),
          "recording failure publishes correlated control echo");
    recording_status=(const companion_gatt_recording_control_v1_t *)
        fixture.published[0].value;
    CHECK((recording_status->privacy_flags &
           (COMPANION_GATT_RECORDING_STATUS_ERROR |
            COMPANION_GATT_RECORDING_STATUS_STORAGE_FULL)) ==
          (COMPANION_GATT_RECORDING_STATUS_ERROR |
           COMPANION_GATT_RECORDING_STATUS_STORAGE_FULL),
          "recording echo distinguishes protected full storage");
    return 0;
}

static bool discard_preview(fixture_t *f,uint32_t now,
                            companion_recording_discard_v2_t *offer)
{
    companion_gatt_event_t event;
    companion_recording_discard_v2_t request={0};
    request.schema_version=2u;request.operation=COMPANION_RECORDING_DISCARD_PREVIEW;
    request.request_id=731u;request.requested_seconds=60u;
    event_write(&event,COMPANION_GATT_CHAR_DELETE_PRIVACY,&request,sizeof(request));
    uint32_t before=f->publish_count;
    comp_link_event(&f->link,&event,now);
    if(f->publish_count<=before || f->published[before].length!=sizeof(*offer))return false;
    memcpy(offer,f->published[before].value,sizeof(*offer));return true;
}
static void discard_send(fixture_t *f,companion_recording_discard_v2_t *request,uint32_t now)
{
    companion_gatt_event_t event;
    event_write(&event,COMPANION_GATT_CHAR_DELETE_PRIVACY,request,sizeof(*request));
    comp_link_event(&f->link,&event,now);
}
static bool write_discard_wire(const char *name,const companion_recording_discard_v2_t *value)
{
    FILE *file=NULL;
#ifdef _MSC_VER
    if(fopen_s(&file,name,"wb")!=0)return false;
#else
    file=fopen(name,"wb");if(!file)return false;
#endif
    bool ok=fwrite(value,1,sizeof(*value),file)==sizeof(*value);
    return fclose(file)==0 && ok;
}
static int test_confirmed_unsynced_discard(void)
{
    fixture_t f;
    uint32_t id;
    companion_recording_discard_v2_t offer,confirmation,response;
    CHECK(initialize(&f,&id),"discard fixture");
    comp_link_connection(&f.link,true,true,1u);
    companion_gatt_event_t subscription;
    event_notify(&subscription,COMPANION_GATT_EVENT_NOTIFY_ENABLED,COMPANION_GATT_CHAR_DELETE_PRIVACY);
    comp_link_event(&f.link,&subscription,1u);
    uint32_t generation=f.journal.catalog.generation;
    uint32_t erases=f.data_erase_calls;
    CHECK(discard_preview(&f,100u,&offer) && offer.flags==0u && offer.recording_id==id &&
          offer.catalog_generation==generation && offer.reserved_bytes==4096u &&
          offer.started_unix_s==1700000000u && offer.duration_ms==20u &&
          offer.expires_in_ms==60000u && offer.largest_extent_after==FLASH_BYTES-8192u,
          "read-only offer identifies oldest exact data and post-delete extent");
    CHECK(f.journal.catalog.generation==generation && f.data_erase_calls==erases &&
          comp_recording_journal_find(&f.journal,id)->sync_state==COMP_RECORDING_JOURNAL_UNSYNCED,
          "preview never ACKs, reserves, erases or changes catalog");
    CHECK(write_discard_wire("discard-preview.bin",&offer),"write actual C preview wire");
    confirmation=offer;confirmation.operation=COMPANION_RECORDING_DISCARD_CONFIRM;
    discard_send(&f,&confirmation,101u);
    CHECK(f.link.io.legacy.reclaim.active && f.link.io.legacy.discard.accepted &&
          comp_recording_journal_find(&f.journal,id)->sync_state==COMP_RECORDING_JOURNAL_ERASING &&
          comp_recording_journal_find(&f.journal,id)->acked_offset==0u &&
          f.data_erase_calls==erases,"confirmation commits explicit loss intent, not fake host ACK");
    memcpy(&response,f.published[f.publish_count-1u].value,sizeof(response));
    CHECK(response.flags==COMPANION_RECORDING_DISCARD_PENDING,"no premature success");
    generation=f.journal.catalog.generation;
    discard_send(&f,&confirmation,102u);
    CHECK(f.journal.catalog.generation==generation && f.data_erase_calls==erases,
          "duplicate confirmed request is idempotent before physical erase");
    f.fail_next_data_erase=true;
    comp_link_poll(&f.link,103u);
    CHECK(f.link.io.legacy.reclaim.active && f.link.io.legacy.reclaim.cursor==0u,"erase error cannot complete user discard");
    comp_link_poll(&f.link,1103u);
    CHECK(f.link.io.legacy.reclaim.cursor==4096u && comp_recording_journal_find(&f.journal,id),
          "bounded sector erase keeps directory until durable final removal");
    comp_link_poll(&f.link,1104u);
    CHECK(!comp_recording_journal_find(&f.journal,id),"only confirmed entry is gone");
    bool complete=false;
    for(uint32_t i=0u;i<f.publish_count;++i) {
        if(f.published[i].id==COMPANION_GATT_CHAR_DELETE_PRIVACY && f.published[i].length==sizeof(response)) {
            memcpy(&response,f.published[i].value,sizeof(response));
            if(response.flags==COMPANION_RECORDING_DISCARD_COMPLETE)complete=true;
        }
    }
    CHECK(complete,"success follows physical erase and catalog commit");
    CHECK(write_discard_wire("discard-completed.bin",&f.link.io.legacy.discard.offer),"write actual completed C wire");
    erases=f.data_erase_calls;discard_send(&f,&confirmation,1200u);
    CHECK(f.data_erase_calls==erases && f.link.io.legacy.discard.offer.flags==COMPANION_RECORDING_DISCARD_COMPLETE,
          "completed exact retry never deletes another recording");

    /* Bind every identity byte, including generation, nonce, request ID,
     * timestamp, duration, reservation and requested recording budget. */
    for(uint32_t at=4u;at<sizeof(confirmation);++at) {
        CHECK(initialize(&f,&id),"tamper fixture");
        comp_link_connection(&f.link,true,true,1u);
        CHECK(discard_preview(&f,100u,&offer) && !offer.flags,"tamper offer");
        confirmation=offer;confirmation.operation=COMPANION_RECORDING_DISCARD_CONFIRM;
        ((uint8_t *)&confirmation)[at]^=1u;generation=f.journal.catalog.generation;
        discard_send(&f,&confirmation,101u);
        CHECK(f.journal.catalog.generation==generation && !f.link.io.legacy.reclaim.active &&
              comp_recording_journal_find(&f.journal,id)->sync_state==COMP_RECORDING_JOURNAL_UNSYNCED,
              "mutated proof must never erase or ACK");
    }
    for(uint32_t mode=0u;mode<7u;++mode) {
        CHECK(initialize(&f,&id),"invalidated offer fixture");
        comp_link_connection(&f.link,true,true,1u);
        CHECK(discard_preview(&f,0xFFFFFFF0u,&offer) && !offer.flags,"wrapped-clock offer");
        confirmation=offer;confirmation.operation=COMPANION_RECORDING_DISCARD_CONFIRM;
        uint32_t now=0xFFFFFFF1u;
        if(mode==0u) {
            companion_recording_discard_v2_t cancel=offer;cancel.operation=COMPANION_RECORDING_DISCARD_CANCEL;
            discard_send(&f,&cancel,now);
        } else if(mode==1u) {comp_link_connection(&f.link,false,false,now);comp_link_connection(&f.link,true,true,now);}
        else if(mode==2u)now=0xFFFFFFF0u+60000u;
        else if(mode==3u)f.runtime.capture_active=true;
        else if(mode==4u)f.link.maintenance=true;
        else if(mode==5u) {
            comp_recording_journal_entry_t extra;
            CHECK(comp_recording_journal_begin(&f.journal,4096u,0u,0u,3u,1u,&extra)==COMP_RECORDING_JOURNAL_OK,"concurrent directory change");
        } else f.link.transfer.state=COMP_WBA_RECORDING_TRANSFER_ACTIVE;
        generation=f.journal.catalog.generation;erases=f.data_erase_calls;
        discard_send(&f,&confirmation,now);
        CHECK(f.journal.catalog.generation==generation && f.data_erase_calls==erases &&
              comp_recording_journal_find(&f.journal,id)->sync_state==COMP_RECORDING_JOURNAL_UNSYNCED,
              "cancel/disconnect/expiry/busy/update/catalog/pull invalidates confirmation");
    }
    for(uint32_t mode=0u;mode<2u;++mode) {
        CHECK(initialize(&f,&id),"marker IO fault fixture");
        comp_link_connection(&f.link,true,true,1u);CHECK(discard_preview(&f,100u,&offer),"fault offer");
        confirmation=offer;confirmation.operation=COMPANION_RECORDING_DISCARD_CONFIRM;
        if(mode==0u)f.fail_catalog_erase_after=1u;else f.short_next_catalog_program=true;
        erases=f.data_erase_calls;discard_send(&f,&confirmation,101u);
        CHECK(f.data_erase_calls==erases && !f.link.io.legacy.reclaim.active &&
              comp_recording_journal_find(&f.journal,id)->sync_state==COMP_RECORDING_JOURNAL_UNSYNCED,
              "failed durable intent cannot begin payload erasure");
        CHECK(comp_recording_journal_mount_strict(&f.journal,&journal_port,&f,FLASH_BYTES)==COMP_RECORDING_JOURNAL_OK &&
              comp_recording_journal_find(&f.journal,id)->sync_state==COMP_RECORDING_JOURNAL_UNSYNCED,
              "torn intent keeps oldest original after remount");
    }
    CHECK(initialize(&f,&id),"reboot explicit discard fixture");
    comp_link_connection(&f.link,true,true,1u);CHECK(discard_preview(&f,100u,&offer),"reboot offer");
    confirmation=offer;confirmation.operation=COMPANION_RECORDING_DISCARD_CONFIRM;
    discard_send(&f,&confirmation,101u);
    comp_link_config_t config=f.link.config;
    CHECK(comp_recording_journal_mount_strict(&f.journal,&journal_port,&f,FLASH_BYTES)==COMP_RECORDING_JOURNAL_OK &&
          comp_recording_journal_find(&f.journal,id)->sync_state==COMP_RECORDING_JOURNAL_ERASING &&
          comp_recording_journal_find(&f.journal,id)->acked_offset==0u,"confirmed intent survives reset without fake ACK");
    CHECK(comp_link_init(&f.link,&config) && !f.link.io.legacy.discard.offered,"reset loses unused authority");
    comp_link_poll(&f.link,103u);comp_link_poll(&f.link,104u);
    CHECK(!comp_recording_journal_find(&f.journal,id),"bounded reboot recovery finishes only committed explicit discard");
    CHECK(initialize(&f,&id),"single-entry-only fixture");
    comp_recording_journal_entry_t extra;
    const uint8_t audio[8]={7u,6u,5u,4u,3u,2u,1u,0u};uint8_t sha[32];memset(sha,0x5Au,sizeof(sha));
    CHECK(comp_recording_journal_begin(&f.journal,4096u,1700000001u,300u,3u,1u,&extra)==COMP_RECORDING_JOURNAL_OK &&
          flash_erase(&f,extra.extent_offset,extra.reserved_bytes) &&
          flash_program(&f,extra.payload_offset,audio,sizeof(audio)) &&
          comp_recording_journal_finalize(&f.journal,extra.recording_id,sizeof(audio),40u,0u,sha,3u)==COMP_RECORDING_JOURNAL_OK,
          "newer protected recording");
    comp_link_connection(&f.link,true,true,1u);
    { companion_gatt_event_t ready;
      event_notify(&ready,COMPANION_GATT_EVENT_NOTIFY_ENABLED,COMPANION_GATT_CHAR_DELETE_PRIVACY);
      comp_link_event(&f.link,&ready,1u); }
    CHECK(discard_preview(&f,0xFFFFFFF0u,&offer) && offer.recording_id==id,"oldest selected with another original present");
    confirmation=offer;confirmation.operation=COMPANION_RECORDING_DISCARD_CONFIRM;
    discard_send(&f,&confirmation,0xFFFFFFF0u+59999u);
    CHECK(f.link.io.legacy.reclaim.active,"confirmation remains valid just before TTL across wrap");
    companion_gatt_delete_privacy_v1_t legacy={0};legacy.schema_version=1u;legacy.operation=1u;
    legacy.request_id=1u;legacy.recording_id=id;legacy.validated_total_length=offer.total_length;
    memcpy(legacy.validated_sha256,offer.sha256,32u);
    companion_gatt_event_t event;event_write(&event,COMPANION_GATT_CHAR_DELETE_PRIVACY,&legacy,sizeof(legacy));
    comp_link_event(&f.link,&event,60000u);
    CHECK(f.link.io.legacy.discard.accepted && comp_recording_journal_find(&f.journal,id)->acked_offset==0u,
          "legacy ACK cannot replace an active user-discard response");
    comp_link_poll(&f.link,60001u);comp_link_poll(&f.link,60002u);
    CHECK(!comp_recording_journal_find(&f.journal,id) &&
          comp_recording_journal_find(&f.journal,extra.recording_id)->sync_state==COMP_RECORDING_JOURNAL_UNSYNCED &&
          memcmp(f.flash+extra.payload_offset,audio,sizeof(audio))==0,"newer unconfirmed original is byte-for-byte preserved");
    companion_recording_discard_v2_t no_loss={0};no_loss.schema_version=2u;
    no_loss.operation=COMPANION_RECORDING_DISCARD_PREVIEW;no_loss.request_id=732u;no_loss.requested_seconds=1u;
    generation=f.journal.catalog.generation;discard_send(&f,&no_loss,60003u);
    memcpy(&response,f.published[f.publish_count-1u].value,sizeof(response));
    CHECK(response.flags==COMPANION_RECORDING_DISCARD_NO_CANDIDATE && f.journal.catalog.generation==generation,
          "space already sufficient cannot offer unnecessary recording loss");
    CHECK(initialize(&f,&id),"RNG refusal fixture");comp_link_connection(&f.link,true,true,1u);
    f.random_failed=true;CHECK(discard_preview(&f,100u,&offer) && offer.flags==COMPANION_RECORDING_DISCARD_REFUSED,
                             "unavailable hardware randomness fails closed");
    return 0;
}
static int test_stopped_dual_lane_bulk(void)
{
    fixture_t f;
    uint32_t id;
    CHECK(initialize(&f, &id), "dual lane fixture");
    uint8_t payload[720], sha[COMP_RECORDING_JOURNAL_SHA256_BYTES];
    for (uint32_t i=0u;i<sizeof(payload);++i) payload[i]=(uint8_t)(i*7u);
    memset(sha,0x91,sizeof(sha));
    comp_recording_journal_entry_t entry;
    CHECK(comp_recording_journal_begin(&f.journal,4096u,0u,0u,3u,1u,&entry)==COMP_RECORDING_JOURNAL_OK &&
          flash_erase(&f,entry.extent_offset,entry.reserved_bytes) &&
          flash_program(&f,entry.payload_offset,payload,sizeof(payload)) &&
          comp_recording_journal_finalize(&f.journal,entry.recording_id,sizeof(payload),1000u,
              crc32_port(0u,payload,sizeof(payload)),sha,3u)==COMP_RECORDING_JOURNAL_OK,"dual lane stored bytes");
    comp_link_connection(&f.link,true,true,10u);
    companion_gatt_event_t event;
    event_notify(&event,COMPANION_GATT_EVENT_NOTIFY_ENABLED,COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL);
    comp_link_event(&f.link,&event,11u);
    event_notify(&event,COMPANION_GATT_EVENT_NOTIFY_ENABLED,COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B);
    comp_link_event(&f.link,&event,12u);
    const companion_recording_adapter_request_t request={.schema_version=1u,
        .flags=COMP_WBA_RECORDING_TRANSFER_STREAM_ALL_FLAG,.recording_id=entry.recording_id};
    event_write(&event,COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,&request,sizeof(request));
    comp_link_event(&f.link,&event,13u);
    f.publish_allowed=false;
    comp_link_poll(&f.link,14u);
    CHECK(f.link.transfer.state==COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED &&
          f.link.transfer.packet_sequence==0u && f.link.transfer.next_offset==0u,
          "full radio queue yields without advancing lane or stored offset");
    f.publish_allowed=true;
    comp_link_poll(&f.link,15u);
    CHECK(f.link.transfer.state==COMP_WBA_RECORDING_TRANSFER_COMPLETE &&
          count_published(&f,COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL)==2u &&
          count_published(&f,COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B)==2u,
          "stopped batch uses both subscribed lanes");
    uint32_t packets=0u,offset=0u;
    for(uint32_t i=0u;i<f.publish_count;++i) {
        const published_value_t *p=&f.published[i];
        if(p->id!=COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL &&
           p->id!=COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B)continue;
        CHECK(p->id==((packets&1u)?COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B:
              COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL),"lane follows successful sequence");
        const uint16_t bytes=(uint16_t)((uint16_t)p->value[2]|((uint16_t)p->value[3]<<8u));
        const uint32_t header=(p->value[1]&1u)?56u:
            (p->value[1]&COMP_WBA_RECORDING_TRANSFER_COMPACT_FLAG)?20u:24u;
        CHECK(offset+bytes<=sizeof(payload) &&
              memcmp(&p->value[header],&payload[offset],bytes)==0,"ordered batch byte continuity");
        offset+=bytes;++packets;
    }
    CHECK(packets==4u && offset==sizeof(payload) &&
          comp_recording_journal_find(&f.journal,entry.recording_id)->sync_state==COMP_RECORDING_JOURNAL_UNSYNCED,
          "batch completion retains durable unconsumed original");
    event_notify(&event,COMPANION_GATT_EVENT_NOTIFY_DISABLED,COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B);
    comp_link_event(&f.link,&event,16u);
    const uint32_t old_b=count_published(&f,COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B);
    event_write(&event,COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,&request,sizeof(request));
    comp_link_event(&f.link,&event,17u);
    comp_link_poll(&f.link,18u);
    CHECK(f.link.transfer.state==COMP_WBA_RECORDING_TRANSFER_COMPLETE &&
          count_published(&f,COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B)==old_b,
          "single lane clients never receive an unsubscribed second lane");
    return 0;
}
#ifndef COMP_LINK_TEST_MAIN
#define COMP_LINK_TEST_MAIN main
#endif
int COMP_LINK_TEST_MAIN(int argc,char **argv)
{
    if(argc==2&&strcmp(argv[1],"ended-reconnect")==0) {
        const int result=test_ended_meeting_read_after_disconnect();
        if(!result)printf("PASS_ENDED_MEETING_READ_AFTER_DISCONNECT_HOST_ONLY\n");
        return result;
    }
    int ended_result=test_ended_meeting_read_after_disconnect();
    if(ended_result)return ended_result;
    int bulk_result=test_stopped_dual_lane_bulk();
    if(bulk_result)return bulk_result;
    int discard_result=test_confirmed_unsynced_discard();
    if(discard_result)return discard_result;
    fixture_t fixture;
    companion_gatt_event_t event;
    companion_gatt_recording_control_v1_t recording;
    companion_recording_adapter_request_t pull;
    companion_gatt_speaker_control_v1_t speaker;
    companion_gatt_delete_privacy_v1_t deletion;
    uint32_t recording_id;

    int meeting_result=test_meeting_control();
    if(meeting_result)return meeting_result;
    meeting_result=test_meeting_failure_retry();
    if(meeting_result)return meeting_result;
    meeting_result=test_storage_full_wire_status();
    if(meeting_result)return meeting_result;
    meeting_result=test_acked_reboot_recovery();
    if(meeting_result)return meeting_result;
    meeting_result=test_acked_live_gap_and_backoff();
    if(meeting_result)return meeting_result;
    meeting_result=test_failed_ack_protects_payload();
    if(meeting_result)return meeting_result;
    meeting_result=test_clear_queue_with_exact_retry();
    if(meeting_result)return meeting_result;

    CHECK(initialize(&fixture, &recording_id), "fixture initialization");

    comp_link_connection(&fixture.link, true, false, 10u);
    event_notify(&event, COMPANION_GATT_EVENT_NOTIFY_ENABLED,
                 COMPANION_GATT_CHAR_RECORDING_LIST);
    comp_link_event(&fixture.link, &event, 11u);
    CHECK(!fixture.link.subscribed[COMPANION_GATT_CHAR_RECORDING_LIST] &&
          fixture.link.rejected_writes == 1u,
          "pre-encryption CCCD cannot arm a later link");
    comp_link_poll(&fixture.link, 12u);
    CHECK(fixture.publish_count == 0u,
          "unencrypted connection receives no status or catalog updates");

    memset(&recording, 0, sizeof(recording));
    recording.schema_version = 1u;
    recording.command = 1u;
    recording.profile_id = 2u;
    recording.max_seconds = 3u;
    event_write(&event, COMPANION_GATT_CHAR_RECORDING_CONTROL, &recording,
                (uint16_t)sizeof(recording));
    comp_link_event(&fixture.link, &event, 13u);
    CHECK(fixture.record_calls == 0u && fixture.link.rejected_writes == 2u,
          "pre-encryption write rejected before product runtime");

    memset(&pull, 0, sizeof(pull));
    pull.schema_version = 1u;
    pull.flags = COMP_WBA_RECORDING_TRANSFER_STREAM_ALL_FLAG;
    pull.recording_id = recording_id;
    uint32_t generation_before_faults = fixture.journal.catalog.generation;
    event_write(&event, COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL, &pull,
                (uint16_t)sizeof(pull));
    comp_link_event(&fixture.link, &event, 14u);
    CHECK(fixture.link.transfer.state == COMP_WBA_RECORDING_TRANSFER_IDLE &&
          fixture.journal.catalog.generation == generation_before_faults &&
          fixture.link.rejected_writes == 3u,
          "pre-encryption pull has no transfer or journal side effect");

    comp_link_connection(&fixture.link, true, true, 20u);
    event_notify(&event, COMPANION_GATT_EVENT_NOTIFY_ENABLED,
                 COMPANION_GATT_CHAR_RECORDING_LIST);
    comp_link_event(&fixture.link, &event, 21u);
    CHECK(fixture.link.subscribed[COMPANION_GATT_CHAR_RECORDING_LIST] &&
          count_published(&fixture, COMPANION_GATT_CHAR_RECORDING_LIST) == 1u,
          "encrypted list subscription publishes finalized directory");
    CHECK(fixture.published[0].length ==
              COMP_WBA_RECORDING_TRANSFER_LIST_HEADER_BYTES +
              COMP_WBA_RECORDING_TRANSFER_LIST_ENTRY_BYTES,
          "directory excludes no finalized recording");

    uint32_t before = fixture.publish_count;
    comp_link_poll(&fixture.link, 22u);
    CHECK(fixture.publish_count > before &&
          count_published(&fixture, COMPANION_GATT_CHAR_DEVICE_STATUS) == 1u &&
          count_published(&fixture, COMPANION_GATT_CHAR_OTA_READINESS) == 1u,
          "encrypted poll publishes bounded status snapshot");

    /* Invalid internal event values and negative enum values never index the
     * subscription array. */
    event_notify(&event, (companion_gatt_event_type_t)99,
                 COMPANION_GATT_CHAR_RECORDING_LIST);
    comp_link_event(&fixture.link, &event, 23u);
    uint32_t rejected_after_bad_type = fixture.link.rejected_writes;
    event.char_id = (companion_gatt_char_id_t)-1;
    comp_link_event(&fixture.link, &event, 24u);
    CHECK(fixture.link.rejected_writes == rejected_after_bad_type,
          "invalid characteristic is dropped without array access");

    recording.profile_id = 1u;
    event_write(&event, COMPANION_GATT_CHAR_RECORDING_CONTROL, &recording,
                (uint16_t)sizeof(recording));
    comp_link_event(&fixture.link, &event, 30u);
    CHECK(fixture.record_calls == 0u,
          "only product profile 2 may start recording");
    recording.command = 2u;
    event_write(&event, COMPANION_GATT_CHAR_RECORDING_CONTROL, &recording,
                (uint16_t)sizeof(recording));
    comp_link_event(&fixture.link, &event, 31u);
    CHECK(fixture.record_calls == 1u && !fixture.last_record_start,
          "stop remains profile independent");

    recording.command = 1u;
    recording.profile_id = 2u;
    recording.max_seconds = 3u;
    event_write(&event, COMPANION_GATT_CHAR_RECORDING_CONTROL, &recording,
                (uint16_t)sizeof(recording));
    comp_link_event(&fixture.link, &event, 40u);
    CHECK(fixture.record_calls == 2u && fixture.last_record_start &&
          fixture.link.remote_limit_ms == 3000u &&
          fixture.link.remote_record_token == fixture.runtime.record_token,
          "accepted remote start binds duration to request token");
    fixture.runtime.command_pending = false;
    fixture.runtime.prepare_pending = false;
    fixture.runtime.start_pending = false;
    fixture.runtime.capture_active = false;
    comp_link_poll(&fixture.link, 41u);
    CHECK(fixture.link.remote_limit_ms == 0u &&
          fixture.link.remote_record_token == 0u,
          "failed or cancelled start clears stale remote duration");
    fixture.runtime.record_token++;
    fixture.runtime.capture_active = true;
    fixture.runtime.recording_since_ms = 100u;
    comp_link_poll(&fixture.link, 4000u);
    CHECK(fixture.record_calls == 2u,
          "later local recording is not stopped by stale duration");

    fixture.runtime.capture_active = false;
    fixture.runtime.recording = DENZIC_AUDIO_RECORDING_STATE_IDLE;
    recording.max_seconds = 2u;
    event_write(&event, COMPANION_GATT_CHAR_RECORDING_CONTROL, &recording,
                (uint16_t)sizeof(recording));
    comp_link_event(&fixture.link, &event, 5000u);
    uint32_t active_token = fixture.runtime.record_token;
    fixture.runtime.command_pending = false;
    fixture.runtime.prepare_pending = false;
    fixture.runtime.capture_active = true;
    fixture.runtime.recording_since_ms = 5100u;
    comp_link_poll(&fixture.link, 7099u);
    CHECK(fixture.record_calls == 3u &&
          fixture.link.remote_record_token == active_token,
          "duration does not stop one millisecond early");
    comp_link_poll(&fixture.link, 7100u);
    CHECK(fixture.record_calls == 4u && !fixture.last_record_start &&
          fixture.link.remote_limit_ms == 0u,
          "same-token capture stops at requested duration once");
    comp_link_poll(&fixture.link, 9000u);
    CHECK(fixture.record_calls == 4u, "remote auto-stop is one shot");

    fixture.runtime.capture_active = false;
    fixture.runtime.command_pending = false;
    fixture.runtime.start_pending = false;
    fixture.runtime.prepare_pending = false;
    fixture.runtime.stop_pending = false;
    event_notify(&event, COMPANION_GATT_EVENT_NOTIFY_ENABLED,
                 COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL);
    comp_link_event(&fixture.link, &event, 10000u);
    generation_before_faults = fixture.journal.catalog.generation;
    uint32_t rejected_before_faults = fixture.link.rejected_writes;
    event_write(&event, COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL, &pull,
                (uint16_t)(sizeof(pull) - 1u));
    comp_link_event(&fixture.link, &event, 10001u);
    event_write(&event, COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL, &pull,
                (uint16_t)sizeof(pull));
    event.payload[sizeof(pull)] = 0u;
    event.payload_len = (uint16_t)(sizeof(pull) + 1u);
    comp_link_event(&fixture.link, &event, 10002u);
    pull.schema_version = 2u;
    event_write(&event, COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL, &pull,
                (uint16_t)sizeof(pull));
    comp_link_event(&fixture.link, &event, 10003u);
    pull.schema_version = 1u;
    pull.flags = (uint8_t)(COMP_WBA_RECORDING_TRANSFER_STREAM_ALL_FLAG | 0x80u);
    event_write(&event, COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL, &pull,
                (uint16_t)sizeof(pull));
    comp_link_event(&fixture.link, &event, 10004u);
    pull.flags = COMP_WBA_RECORDING_TRANSFER_STREAM_ALL_FLAG;
    pull.byte_offset = 8u;
    event_write(&event, COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL, &pull,
                (uint16_t)sizeof(pull));
    comp_link_event(&fixture.link, &event, 10005u);
    CHECK(fixture.link.transfer.state == COMP_WBA_RECORDING_TRANSFER_IDLE &&
          fixture.journal.catalog.generation == generation_before_faults &&
          fixture.link.rejected_writes == rejected_before_faults + 5u,
          "malformed schema flags length and offset cannot start or mutate recording");
    uint32_t pull_publishes_before_valid = count_published(
        &fixture, COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL);
    pull.byte_offset = 0u;
    pull.host_resume_token = 0x10203040u;
    event_write(&event, COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL, &pull,
                (uint16_t)sizeof(pull));
    comp_link_event(&fixture.link, &event, 10006u);
    CHECK(fixture.link.transfer.state == COMP_WBA_RECORDING_TRANSFER_ACTIVE,
          "encrypted subscribed pull enters portable transfer");
    comp_link_poll(&fixture.link, 10007u);
    comp_link_poll(&fixture.link, 10008u);
    CHECK(count_published(&fixture,
                          COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL) ==
              pull_publishes_before_valid + 1u &&
          fixture.link.transfer.host_resume_token == 0x10203040u,
          "link delivers real journal chunk with correlation token");

    fixture.runtime.capture_active = true;
    memset(&speaker, 0, sizeof(speaker));
    speaker.schema_version = 1u;
    speaker.request_id = 77u;
    speaker.prompt_id = 2u;
    event_write(&event, COMPANION_GATT_CHAR_SPEAKER_CONTROL, &speaker,
                (uint16_t)sizeof(speaker));
    before = fixture.link.rejected_writes;
    comp_link_event(&fixture.link, &event, 11000u);
    CHECK(fixture.link.rejected_writes == before + 1u,
          "speaker command cannot contaminate capture");
    fixture.runtime.capture_active = false;
    comp_link_event(&fixture.link, &event, 11001u);
    CHECK(fixture.features.speaker.request_id == 77u,
          "idle speaker command reaches portable feature backend");
    fixture.link.next_status_ms = 20000u;

    const comp_recording_journal_entry_t *durable =
        comp_recording_journal_find(&fixture.journal, recording_id);
    CHECK(durable != NULL &&
          durable->sync_state == COMP_RECORDING_JOURNAL_UNSYNCED,
          "recording begins unsynced");
    memset(&deletion, 0, sizeof(deletion));
    deletion.schema_version = 1u;
    deletion.operation = 1u;
    deletion.recording_id = recording_id;
    deletion.validated_total_length = 8u;
    event_write(&event, COMPANION_GATT_CHAR_DELETE_PRIVACY, &deletion,
                (uint16_t)sizeof(deletion));
    before = fixture.publish_count;
    comp_link_event(&fixture.link, &event, 12000u);
    durable = comp_recording_journal_find(&fixture.journal, recording_id);
    CHECK(durable != NULL &&
          durable->sync_state == COMP_RECORDING_JOURNAL_UNSYNCED,
          "bad SHA never ACKs or erases recording");
    CHECK((fixture.published[fixture.publish_count - 1u].value[2] & 1u) != 0u,
          "unconfirmed delete explicitly reports rejection");

    memset(deletion.validated_sha256, 0xA5,
           sizeof(deletion.validated_sha256));
    event_write(&event, COMPANION_GATT_CHAR_DELETE_PRIVACY, &deletion,
                (uint16_t)sizeof(deletion));
    before = fixture.publish_count;
    uint32_t consume_io = fixture.nor_calls;
    comp_link_event(&fixture.link, &event, 12001u);
    durable = comp_recording_journal_find(&fixture.journal, recording_id);
    CHECK(durable != NULL &&
          durable->sync_state == COMP_RECORDING_JOURNAL_UNSYNCED &&
          fixture.publish_count == before && fixture.nor_calls == consume_io,
          "exact proof queues without NOR I/O or premature success echo");
    comp_link_poll(&fixture.link, 12001u);
    CHECK(comp_recording_journal_find(&fixture.journal, recording_id)->sync_state ==
              COMP_RECORDING_JOURNAL_ACKED,
          "one foreground poll persists exact ACK only");
    comp_link_poll(&fixture.link, 12001u);
    CHECK(comp_recording_journal_find(&fixture.journal, recording_id)->sync_state ==
              COMP_RECORDING_JOURNAL_ERASING,
          "next foreground poll persists ERASING before any payload erase");
    uint32_t generation_after_ack = fixture.journal.catalog.generation;
    uint32_t acknowledgements_after_ack =
        fixture.link.transfer.stats.acknowledgements;
    comp_link_event(&fixture.link, &event, 12002u);
    CHECK(fixture.journal.catalog.generation == generation_after_ack &&
          fixture.link.transfer.stats.acknowledgements ==
              acknowledgements_after_ack &&
          fixture.link.io.legacy.reclaim.active &&
          fixture.link.io.legacy.reclaim.recording_id == recording_id,
          "duplicate verified delete is idempotent while reclaim is active");
    comp_link_connection(&fixture.link, false, false, 12001u);
    uint32_t erases_before_reclaim = fixture.data_erase_calls;
    fixture.runtime.capture_active = true;
    comp_link_poll(&fixture.link, 12002u);
    CHECK(fixture.data_erase_calls == erases_before_reclaim,
          "capture pauses reclaim flash traffic");
    fixture.runtime.capture_active = false;
    fixture.fail_next_data_erase = true;
    comp_link_poll(&fixture.link, 12003u);
    CHECK(fixture.link.io.legacy.reclaim.cursor == 0u &&
          fixture.link.io.legacy.reclaim.last_result != COMP_RECORDING_JOURNAL_OK &&
          fixture.publish_count == before,
          "erase fault keeps cursor and withholds success");
    comp_link_poll(&fixture.link, 12500u);
    CHECK(fixture.data_erase_calls == erases_before_reclaim + 1u,
          "erase fault retry is bounded by backoff");
    comp_link_poll(&fixture.link, 13003u);
    CHECK(fixture.link.io.legacy.reclaim.cursor ==
              COMP_RECORDING_JOURNAL_SECTOR_BYTES &&
          fixture.link.io.legacy.reclaim.last_result == COMP_RECORDING_JOURNAL_OK &&
          fixture.publish_count == before,
          "one poll erases at most one sector and still withholds echo");
    comp_link_poll(&fixture.link, 13004u);
    CHECK(comp_recording_journal_find(&fixture.journal, recording_id) == NULL,
          "final separate step commits catalog removal");
    CHECK(fixture.publish_count == before &&
          fixture.link.io.legacy.reclaim.response_pending,
          "disconnect keeps completed delete response pending");
    uint32_t deletion_replies = count_published(&fixture, COMPANION_GATT_CHAR_DELETE_PRIVACY);
    comp_link_connection(&fixture.link, true, true, 13005u);
    comp_link_poll(&fixture.link, 13006u);
    CHECK(count_published(&fixture, COMPANION_GATT_CHAR_DELETE_PRIVACY)==deletion_replies &&
          fixture.link.io.legacy.reclaim.response_pending,
          "reconnect retains the exact durable receipt until the new subscription is enabled");
    event_notify(&event, COMPANION_GATT_EVENT_NOTIFY_ENABLED, COMPANION_GATT_CHAR_DELETE_PRIVACY);
    comp_link_event(&fixture.link,&event,13007u);
    /* The new exact request may race the first deferred receipt. */
    deletion.request_id+=1u;
    event_write(&event,COMPANION_GATT_CHAR_DELETE_PRIVACY,&deletion,(uint16_t)sizeof(deletion));
    comp_link_event(&fixture.link,&event,13007u);
    CHECK(fixture.link.io.legacy.reclaim.response_pending &&
          fixture.link.io.legacy.reclaim.response.request_id==deletion.request_id,
          "a fresh request id replaces the pending exact receipt correlation");
    comp_link_poll(&fixture.link,13008u);
    CHECK(count_published(&fixture, COMPANION_GATT_CHAR_DELETE_PRIVACY)==deletion_replies+1u,
          "subscribed reconnect sends the retained completion once");
    const published_value_t *receipt=NULL;
    for(uint32_t i=before;i<fixture.publish_count;i++)
        if(fixture.published[i].id==COMPANION_GATT_CHAR_DELETE_PRIVACY)receipt=&fixture.published[i];
    CHECK(receipt && receipt->length==sizeof(deletion) &&
          memcmp(receipt->value,&deletion,sizeof(deletion))==0 &&
          !fixture.link.io.legacy.reclaim.response_pending,
          "success is the exact accepted proof after extent and catalog removal");

    /* Type allocates a fresh request_id after reconnect. A prior completion
     * can arrive during subscribe, before Type sends its new exact proof. */
    uint32_t receipt_count_before_retry=count_published(&fixture,COMPANION_GATT_CHAR_DELETE_PRIVACY);
    uint32_t erase_count_before_retry=fixture.data_erase_calls;
    deletion.request_id+=1u;
    event_write(&event,COMPANION_GATT_CHAR_DELETE_PRIVACY,&deletion,(uint16_t)sizeof(deletion));
    comp_link_event(&fixture.link,&event,13009u);
    comp_link_poll(&fixture.link,13010u);
    CHECK(count_published(&fixture,COMPANION_GATT_CHAR_DELETE_PRIVACY)==receipt_count_before_retry+1u,
          "fresh request id receives one receipt for the same completed original");
    receipt=NULL;
    for(uint32_t i=before;i<fixture.publish_count;i++)
        if(fixture.published[i].id==COMPANION_GATT_CHAR_DELETE_PRIVACY)receipt=&fixture.published[i];
    CHECK(receipt && receipt->length==sizeof(deletion) && memcmp(receipt->value,&deletion,sizeof(deletion))==0 &&
          fixture.data_erase_calls==erase_count_before_retry,
          "fresh-id retry echoes the exact saved proof without repeating erase");
    deletion.request_id+=1u;deletion.validated_sha256[0]^=1u;
    event_write(&event,COMPANION_GATT_CHAR_DELETE_PRIVACY,&deletion,(uint16_t)sizeof(deletion));
    comp_link_event(&fixture.link,&event,13011u);
    receipt=&fixture.published[fixture.publish_count-1u];
    CHECK(receipt->id==COMPANION_GATT_CHAR_DELETE_PRIVACY && (receipt->value[2]&1u)!=0u &&
          fixture.data_erase_calls==erase_count_before_retry,
          "a different proof is refused and never erases another recording");
    deletion.validated_sha256[0]^=1u;

    /* Recreate one record, enter ERASING, erase its first sector and reboot.
     * The RAM cursor is deliberately lost; remount restarts at zero and an
     * already erased NOR sector is safe to erase again. */
    comp_recording_journal_entry_t reboot_entry;
    uint8_t reboot_payload[32];
    uint8_t reboot_sha[COMP_RECORDING_JOURNAL_SHA256_BYTES];
    memset(reboot_payload, 0x3Cu, sizeof(reboot_payload));
    memset(reboot_sha, 0x5Au, sizeof(reboot_sha));
    CHECK(comp_recording_journal_begin(&fixture.journal,
                                       (uint32_t)sizeof(reboot_payload),
                                       1700000100u, 200u, 3u, 1u,
                                       &reboot_entry) ==
              COMP_RECORDING_JOURNAL_OK,
          "reserve reboot deletion fixture");
    CHECK(flash_erase(&fixture, reboot_entry.extent_offset,
                      reboot_entry.reserved_bytes) &&
          flash_program(&fixture, reboot_entry.payload_offset,
                        reboot_payload, (uint32_t)sizeof(reboot_payload)),
          "write reboot deletion fixture");
    CHECK(comp_recording_journal_finalize(
              &fixture.journal, reboot_entry.recording_id,
              (uint32_t)sizeof(reboot_payload), 20u,
              crc32_port(0u, reboot_payload,
                         (uint32_t)sizeof(reboot_payload)),
              reboot_sha, 3u) == COMP_RECORDING_JOURNAL_OK,
          "finalize reboot deletion fixture");
    memset(&deletion, 0, sizeof(deletion));
    deletion.schema_version = 1u; deletion.operation = 1u;
    deletion.request_id = 99u; deletion.recording_id = reboot_entry.recording_id;
    deletion.validated_total_length = (uint32_t)sizeof(reboot_payload);
    memcpy(deletion.validated_sha256, reboot_sha, sizeof(reboot_sha));
    event_write(&event, COMPANION_GATT_CHAR_DELETE_PRIVACY, &deletion,
                (uint16_t)sizeof(deletion));
    comp_link_event(&fixture.link, &event, 14000u);
    comp_link_poll(&fixture.link, 14000u);
    comp_link_poll(&fixture.link, 14000u);
    comp_link_poll(&fixture.link, 14001u);
    CHECK(fixture.link.io.legacy.reclaim.cursor ==
              COMP_RECORDING_JOURNAL_SECTOR_BYTES,
          "pre-reset reclaim erased one sector");
    comp_link_config_t reboot_config = fixture.link.config;
    CHECK(comp_recording_journal_mount(&fixture.journal, &journal_port,
                                       &fixture, FLASH_BYTES) ==
              COMP_RECORDING_JOURNAL_OK,
          "power loss remounts durable ERASING marker");
    fixture.publish_count = 0u;
    CHECK(comp_link_init(&fixture.link, &reboot_config) &&
          fixture.link.io.legacy.reclaim.active && fixture.link.io.legacy.reclaim.cursor == 0u &&
          !fixture.link.io.legacy.reclaim.response_pending,
          "restart discovers ERASING and resets only RAM cursor");
    comp_link_connection(&fixture.link, true, true, 15000u);
    comp_link_poll(&fixture.link, 15001u);
    CHECK(fixture.link.io.legacy.reclaim.cursor ==
              COMP_RECORDING_JOURNAL_SECTOR_BYTES,
          "restart safely re-erases first sector");
    comp_link_poll(&fixture.link, 15002u);
    CHECK(comp_recording_journal_find(&fixture.journal,
                                      reboot_entry.recording_id) == NULL &&
          count_published(&fixture,
                          COMPANION_GATT_CHAR_DELETE_PRIVACY) == 0u,
          "restart completes deletion without fabricating lost success request");

    comp_link_connection(&fixture.link, false, false, 16000u);
    CHECK(!fixture.link.subscribed[COMPANION_GATT_CHAR_RECORDING_LIST] &&
          !fixture.link.subscribed[COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL] &&
          fixture.link.transfer.state == COMP_WBA_RECORDING_TRANSFER_IDLE,
          "disconnect clears transient subscriptions and transfer");
    before = fixture.publish_count;
    comp_link_poll(&fixture.link, 17000u);
    CHECK(fixture.publish_count == before,
          "disconnect suppresses periodic characteristic updates");

    comp_recording_journal_entry_t discarded;
    CHECK(comp_recording_journal_begin(&fixture.journal,4096u,0u,18000u,3u,1u,&discarded)==COMP_RECORDING_JOURNAL_OK,
          "local clear fixture reserve");
    CHECK(flash_erase(&fixture,discarded.extent_offset,discarded.reserved_bytes) &&
          flash_program(&fixture,discarded.payload_offset,reboot_payload,sizeof(reboot_payload)),"local clear fixture bytes");
    CHECK(comp_recording_journal_finalize(&fixture.journal,discarded.recording_id,sizeof(reboot_payload),20u,
          0u,reboot_sha,3u)==COMP_RECORDING_JOURNAL_OK,"local clear fixture finalize");
    fixture.runtime.capture_active=true;
    CHECK(!comp_link_discard_all_confirmed(&fixture.link),"physical clear blocked during capture");
    fixture.runtime.capture_active=false;
    fixture.link.maintenance=true;
    CHECK(!comp_link_heavy_io_allowed(&fixture.link) && !comp_link_discard_all_confirmed(&fixture.link),
          "update maintenance excludes transfer and physical delete");
    comp_link_connection(&fixture.link,true,true,18001u);
    recording.command=1u;recording.profile_id=2u;
    event_write(&event,COMPANION_GATT_CHAR_RECORDING_CONTROL,&recording,sizeof(recording));
    uint32_t record_calls_before=fixture.record_calls;
    comp_link_event(&fixture.link,&event,18002u);
    CHECK(fixture.record_calls==record_calls_before,"update maintenance rejects remote recording start");
    recording.command=2u;
    event_write(&event,COMPANION_GATT_CHAR_RECORDING_CONTROL,&recording,sizeof(recording));
    comp_link_event(&fixture.link,&event,18003u);
    CHECK(fixture.record_calls==record_calls_before+1u && !fixture.last_record_start,"stop is available during maintenance");
    fixture.link.maintenance=false;
    fixture.runtime.command_pending=false;fixture.runtime.start_pending=false;fixture.runtime.prepare_pending=false;
    CHECK(comp_link_discard_all_confirmed(&fixture.link),"confirmed physical clear accepts unsynced data");
    CHECK(comp_recording_journal_find(&fixture.journal,discarded.recording_id)->sync_state==COMP_RECORDING_JOURNAL_ERASING,
          "physical clear durably marks before erasure");
    CHECK(comp_recording_journal_mount_strict(&fixture.journal,&journal_port,&fixture,FLASH_BYTES)==COMP_RECORDING_JOURNAL_OK,
          "strict remount retains physical deletion");
    CHECK(comp_link_init(&fixture.link,&reboot_config),"local clear reboot link");
    for(uint32_t i=0;i<20u;++i)comp_link_poll(&fixture.link,19000u+i);
    CHECK(comp_recording_journal_find(&fixture.journal,discarded.recording_id)==NULL,"local clear finished after reboot");
    for(uint32_t i=0;i<discarded.reserved_bytes;++i)CHECK(fixture.flash[discarded.extent_offset+i]==255u,"local clear erases physical bytes");

    printf("PASS_WBA_COMPANION_LINK_HOST_ONLY publishes=%lu rejected=%lu\n",
           (unsigned long)fixture.publish_count,
           (unsigned long)fixture.link.rejected_writes);
    printf("PASS_CONFIRMED_UNSYNCED_DISCARD_HOST_ONLY exact-proof/cancel/expiry/reboot/IO\n");
    return 0;
}
