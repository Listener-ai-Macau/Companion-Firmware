#include "wba_recording_service.h"

#include <stdio.h>
#include <string.h>

#define FLASH_BYTES (48u * 1024u)
#define DATA_BYTES (FLASH_BYTES - 2u * COMP_RECORDING_JOURNAL_SECTOR_BYTES)

typedef struct {
    uint8_t bytes[FLASH_BYTES];
    uint32_t now_ms;
    uint32_t encode_ms;
    uint32_t program_ms;
    uint32_t payload_erases;
    uint32_t payload_programs;
    uint32_t catalog_programs;
    uint32_t mic_on_calls;
    uint32_t mic_off_calls;
    uint32_t report_count;
    uint32_t last_token;
    denzic_audio_recording_state_v1_t last_report;
    bool last_capture_active;
    bool fail_mic_off_once;
    bool fail_program;
} fixture_t;

static fixture_t *s_codec_fixture;

static int fail_line(int line, const char *message)
{
    fprintf(stderr, "FAIL line=%d %s\n", line, message);
    return line;
}

#define CHECK(expr, message) \
    do { if (!(expr)) return fail_line(__LINE__, message); } while (0)

static bool flash_read(void *context, uint32_t offset, uint8_t *dst,
                       uint32_t length)
{
    fixture_t *fixture = context;
    if (dst == NULL || offset > FLASH_BYTES ||
        length > FLASH_BYTES - offset) return false;
    memcpy(dst, &fixture->bytes[offset], length);
    return true;
}

static bool flash_program(void *context, uint32_t offset, const uint8_t *src,
                          uint32_t length)
{
    fixture_t *fixture = context;
    if (src == NULL || offset > FLASH_BYTES ||
        length > FLASH_BYTES - offset) return false;
    if (fixture->fail_program) return false;
    fixture->now_ms += fixture->program_ms;
    if (offset < DATA_BYTES) fixture->payload_programs++;
    else fixture->catalog_programs++;
    for (uint32_t i = 0u; i < length; ++i) {
        if ((fixture->bytes[offset + i] & src[i]) != src[i]) return false;
        fixture->bytes[offset + i] &= src[i];
    }
    return true;
}

static bool flash_erase(void *context, uint32_t offset, uint32_t length)
{
    fixture_t *fixture = context;
    if (offset > FLASH_BYTES || length > FLASH_BYTES - offset ||
        (offset % COMP_RECORDING_JOURNAL_SECTOR_BYTES) != 0u ||
        (length % COMP_RECORDING_JOURNAL_SECTOR_BYTES) != 0u) return false;
    if (offset < DATA_BYTES) fixture->payload_erases +=
        length / COMP_RECORDING_JOURNAL_SECTOR_BYTES;
    memset(&fixture->bytes[offset], 0xFF, length);
    return true;
}

static uint32_t crc32_port(uint32_t seed, const uint8_t *data,
                           uint32_t length)
{
    uint32_t crc = seed ^ 0xFFFFFFFFu;
    for (uint32_t i = 0u; i < length; ++i) {
        uint32_t value = (crc ^ data[i]) & 0xFFu;
        for (uint32_t bit = 0u; bit < 8u; ++bit) {
            value = (value >> 1) ^
                (0xEDB88320u & (uint32_t)(-(int32_t)(value & 1u)));
        }
        crc = (crc >> 8) ^ value;
    }
    return crc ^ 0xFFFFFFFFu;
}

static comp_recording_journal_port_t make_port(void)
{
    comp_recording_journal_port_t port = {
        flash_read, flash_program, flash_erase, crc32_port
    };
    return port;
}

static bool mic_control(void *context, bool enabled)
{
    fixture_t *fixture = context;
    if (enabled) {
        fixture->mic_on_calls++;
        return true;
    }
    fixture->mic_off_calls++;
    if (fixture->fail_mic_off_once) {
        fixture->fail_mic_off_once = false;
        return false;
    }
    return true;
}

static uint32_t now_ms(void *context)
{
    return ((fixture_t *)context)->now_ms;
}

static void report(void *context, uint32_t token,
                   denzic_audio_recording_state_v1_t state,
                   bool capture_active)
{
    fixture_t *fixture = context;
    fixture->report_count++;
    fixture->last_token = token;
    fixture->last_report = state;
    fixture->last_capture_active = capture_active;
}

/* Deterministic codec double: it exercises the service's real COP1 framing,
 * journal, CRC and SHA paths without pretending to benchmark Opus. */
bool companion_opus16_rt_init_rate_frame(companion_opus16_rt_t *rt,
                                          uint32_t rate, uint32_t frame_ms)
{
    memset(rt, 0, sizeof(*rt));
    rt->sample_rate_hz = rate;
    rt->frame_ms = (uint16_t)frame_ms;
    rt->frame_samples = 320u;
    rt->ready = true;
    return true;
}

void companion_opus16_rt_destroy(companion_opus16_rt_t *rt)
{
    rt->ready = false;
    rt->pcm_fill = 0u;
}

void companion_opus16_rt_reset(companion_opus16_rt_t *rt) { (void)rt; }
bool companion_opus16_rt_init(companion_opus16_rt_t *rt) { (void)rt; return false; }
bool companion_opus16_rt_init_rate(companion_opus16_rt_t *rt, uint32_t rate)
{ (void)rt; (void)rate; return false; }

static void write_header(uint8_t *out)
{
    const uint8_t header[12] = {
        'C','O','P','1', 1u,1u,20u,0u, 0x80u,0x3Eu,0u,0u
    };
    memcpy(out, header, sizeof(header));
}

size_t companion_opus16_rt_encode(companion_opus16_rt_t *rt,
                                  const int16_t *pcm, size_t pcm_samples,
                                  uint8_t *out, size_t cap, bool header)
{
    if (!rt->ready || pcm == NULL || out == NULL) return 0u;
    if (s_codec_fixture != NULL) {
        s_codec_fixture->now_ms += s_codec_fixture->encode_ms;
    }
    if (header) {
        if (cap < 12u) return 0u;
        write_header(out);
        return 12u;
    }
    if (pcm_samples > (size_t)(rt->frame_samples - rt->pcm_fill)) return 0u;
    rt->pcm_fill = (uint16_t)(rt->pcm_fill + (uint16_t)pcm_samples);
    if (rt->pcm_fill < rt->frame_samples) return 0u;
    if (cap < 5u) return 0u;
    out[0] = 3u; out[1] = 0u; out[2] = 0xA0u;
    out[3] = (uint8_t)rt->frames_encoded;
    out[4] = (uint8_t)(rt->frames_encoded >> 8);
    rt->frames_encoded++;
    rt->bytes_out += 5u;
    rt->pcm_fill = 0u;
    return 5u;
}

size_t companion_opus16_rt_flush(companion_opus16_rt_t *rt,
                                 uint8_t *out, size_t cap)
{
    int16_t padding[320] = {0};
    if (rt->pcm_fill == 0u) return 0u;
    return companion_opus16_rt_encode(rt, padding,
        (size_t)(rt->frame_samples - rt->pcm_fill), out, cap, false);
}

static bool setup(fixture_t *fixture, comp_recording_journal_t *journal,
                  comp_wba_recording_service_t *service,
                  uint32_t reserve, uint16_t budget)
{
    comp_recording_journal_port_t port = make_port();
    comp_wba_recording_service_config_t config;
    memset(fixture, 0, sizeof(*fixture));
    memset(fixture->bytes, 0xFF, sizeof(fixture->bytes));
    if (comp_recording_journal_mount(journal, &port, fixture, FLASH_BYTES) !=
        COMP_RECORDING_JOURNAL_OK) return false;
    memset(&config, 0, sizeof(config));
    config.journal = journal;
    config.partition_base_address = COMP_WBA_RECORDING_MIN_PARTITION_BASE;
    config.reserve_bytes = reserve;
    config.mic_control = mic_control;
    config.now_ms = now_ms;
    config.report = report;
    config.context = fixture;
    config.foreground_budget_ms = budget;
    s_codec_fixture = fixture;
    return comp_wba_recording_service_init(service, &config);
}

static void fill_pcm(int16_t pcm[COMP_WBA_RECORDING_PCM_FRAME_SAMPLES])
{
    for (uint32_t i = 0u; i < COMP_WBA_RECORDING_PCM_FRAME_SAMPLES; ++i) {
        pcm[i] = (int16_t)(i * 17u);
    }
}

static int poll_until(comp_wba_recording_service_t *service,
                      comp_wba_recording_service_state_t target,
                      uint32_t limit)
{
    while (service->state != target && limit-- != 0u) {
        (void)comp_wba_recording_service_poll(service);
    }
    return service->state == target ? 0 : -1;
}

static int test_prepare_cancel_and_normal_finalize(void)
{
    static const uint8_t expected_sha[32] = {
        0xB5u,0x6Fu,0x97u,0x18u,0x79u,0xAFu,0xEFu,0x99u,
        0x5Du,0x59u,0xC0u,0x7Fu,0x56u,0x35u,0xA4u,0x60u,
        0x4Eu,0x2Bu,0xE3u,0x26u,0x84u,0x70u,0xECu,0xCFu,
        0x99u,0xE3u,0xE1u,0x3Cu,0x8Fu,0x77u,0x85u,0xD1u
    };
    fixture_t fixture;
    comp_recording_journal_t journal;
    comp_wba_recording_service_t service;
    int16_t pcm[COMP_WBA_RECORDING_PCM_FRAME_SAMPLES];
    const comp_recording_journal_entry_t *entry;
    uint32_t erase_before;
    uint32_t program_before;

    CHECK(setup(&fixture, &journal, &service, 8192u, 10u), "setup");
    CHECK(service.config.partition_base_address == COMP_WBA_NOR_RECORDING_BASE,
          "recording boundary follows selected static resource geometry");
    {
        comp_wba_recording_service_t rejected;
        comp_wba_recording_service_config_t bad = service.config;
        bad.partition_base_address =
            COMP_WBA_RECORDING_MIN_PARTITION_BASE - 4096u;
        CHECK(!comp_wba_recording_service_init(&rejected, &bad),
              "partition below product recording region rejected");
    }
    CHECK(comp_wba_recording_service_prepare_port(&service, 11u), "prepare");
    CHECK(service.state == COMP_WBA_RECORDING_PREPARING &&
          fixture.last_report == DENZIC_AUDIO_RECORDING_STATE_PENDING_START,
          "pending report");
    erase_before = fixture.payload_erases;
    (void)comp_wba_recording_service_poll(&service);
    CHECK(fixture.payload_erases == erase_before + 1u &&
          service.state == COMP_WBA_RECORDING_PREPARING,
          "one erase per poll");
    CHECK(comp_wba_recording_service_control_port(&service, false, 11u),
          "cancel prepare");
    for (uint32_t i = 0u; i < 5u; ++i) (void)comp_wba_recording_service_poll(&service);
    CHECK(service.state == COMP_WBA_RECORDING_IDLE && fixture.mic_on_calls == 0u &&
          !comp_wba_recording_service_ready_port(&service, 11u),
          "cancel cannot start later");

    CHECK(comp_wba_recording_service_prepare_port(&service, 12u), "prepare 2");
    CHECK(poll_until(&service, COMP_WBA_RECORDING_READY, 4u) == 0,
          "ready after two erases and codec init");
    CHECK(comp_wba_recording_service_ready_port(&service, 12u), "ready port");
    erase_before = fixture.payload_erases;
    program_before = fixture.payload_programs;
    CHECK(comp_wba_recording_service_control_port(&service, true, 12u),
          "fast start");
    CHECK(fixture.payload_erases == erase_before &&
          fixture.payload_programs == program_before && fixture.mic_on_calls == 1u,
          "start has no flash IO");
    fill_pcm(pcm);
    for (uint32_t i = 0u; i < 4u; ++i) {
        CHECK(comp_wba_recording_service_pcm(&service, pcm, 160u, 16000u),
              "queue pcm");
        (void)comp_wba_recording_service_poll(&service);
    }
    CHECK(service.stats.encode_duration.samples == 2u,
          "encode timing counts completed 20ms packets, not cheap half frames");
    CHECK(comp_wba_recording_service_control_port(&service, false, 12u),
          "stop");
    CHECK(!service.microphone_active &&
          comp_wba_recording_service_stop_reason(&service) ==
              COMP_WBA_RECORDING_STOP_USER,
          "mic stopped before finalize");
    CHECK(poll_until(&service, COMP_WBA_RECORDING_TRANSFER_READY, 16u) == 0,
          "finalize");
    entry = comp_wba_recording_service_entry(&service);
    CHECK(entry != NULL && entry->sync_state == COMP_RECORDING_JOURNAL_UNSYNCED &&
          entry->codec == 3u && entry->source_mode == 1u,
          "unsynced codec3 entry");
    CHECK(entry->total_length == 22u && entry->duration_ms == 40u &&
          entry->reserved_bytes == COMP_RECORDING_JOURNAL_SECTOR_BYTES,
          "length duration and opt-in trim");
    CHECK(memcmp(&fixture.bytes[entry->payload_offset], "COP1", 4u) == 0,
          "cop1 payload");
    CHECK(entry->content_crc32 == crc32_port(
              0u, &fixture.bytes[entry->payload_offset], entry->total_length),
          "payload crc");
    CHECK(memcmp(entry->sha256, expected_sha, sizeof(expected_sha)) == 0,
          "payload sha256");
    return 0;
}

static int test_overflow_and_budget_faults(void)
{
    fixture_t fixture;
    comp_recording_journal_t journal;
    comp_wba_recording_service_t service;
    int16_t pcm[COMP_WBA_RECORDING_PCM_FRAME_SAMPLES];
    const comp_recording_journal_entry_t *entry;

    fill_pcm(pcm);
    CHECK(setup(&fixture, &journal, &service, 8192u, 10u), "overflow setup");
    CHECK(comp_wba_recording_service_prepare_port(&service, 21u), "overflow prepare");
    CHECK(poll_until(&service, COMP_WBA_RECORDING_READY, 4u) == 0, "overflow ready");
    CHECK(comp_wba_recording_service_control_port(&service, true, 21u), "overflow start");
    for (uint32_t i = 0u; i < COMP_WBA_RECORDING_PCM_RING_SLOTS; ++i) {
        CHECK(comp_wba_recording_service_pcm(&service, pcm, 160u, 16000u), "fill ring");
    }
    CHECK(!comp_wba_recording_service_pcm(&service, pcm, 160u, 16000u),
          "overflow visible");
    (void)comp_wba_recording_service_poll(&service);
    CHECK(service.state == COMP_WBA_RECORDING_FAULT && !service.microphone_active &&
          service.stats.dropped_pcm_frames == 1u,
          "overflow fails recording");
    entry = comp_wba_recording_service_entry(&service);
    CHECK(entry != NULL && entry->sync_state == COMP_RECORDING_JOURNAL_WRITING,
          "fault preserves writing extent");
    CHECK(comp_wba_recording_service_recover(&service), "recover overflow");
    CHECK(comp_wba_recording_service_prepare_port(&service, 23u),
          "new prepare after overflow");
    CHECK(poll_until(&service, COMP_WBA_RECORDING_READY, 4u) == 0,
          "new ready after overflow");
    CHECK(comp_wba_recording_service_control_port(&service, true, 23u),
          "new start after overflow");
    (void)comp_wba_recording_service_poll(&service);
    CHECK(service.state == COMP_WBA_RECORDING_CAPTURING,
          "aggregate dropped counter does not poison new capture");
    CHECK(comp_wba_recording_service_capture_fault(
              &service, 23u, COMP_WBA_RECORDING_FAULT_PLATFORM_CAPTURE),
          "explicit platform capture fault");
    CHECK(service.state == COMP_WBA_RECORDING_FAULT &&
          !service.microphone_active && service.stats.external_capture_faults == 1u &&
          comp_wba_recording_service_fault_reason(&service) ==
              COMP_WBA_RECORDING_FAULT_PLATFORM_CAPTURE,
          "platform fault preserves truthful state");

    CHECK(setup(&fixture, &journal, &service, 8192u, 10u), "budget setup");
    CHECK(comp_wba_recording_service_prepare_port(&service, 22u), "budget prepare");
    CHECK(poll_until(&service, COMP_WBA_RECORDING_READY, 4u) == 0, "budget ready");
    CHECK(comp_wba_recording_service_control_port(&service, true, 22u), "budget start");
    fixture.encode_ms = 11u;
    CHECK(comp_wba_recording_service_pcm(&service, pcm, 160u, 16000u), "budget pcm");
    (void)comp_wba_recording_service_poll(&service);
    CHECK(service.state == COMP_WBA_RECORDING_FAULT &&
          service.stats.budget_violations == 1u &&
          service.stats.max_encode_ms == 11u,
          "encode over ten ms fails closed");
    return 0;
}

static int test_storage_stop_and_non_evict(void)
{
    fixture_t fixture;
    comp_recording_journal_t journal;
    comp_wba_recording_service_t service;
    int16_t pcm[COMP_WBA_RECORDING_PCM_FRAME_SAMPLES];
    uint32_t first_id;

    fill_pcm(pcm);
    CHECK(setup(&fixture, &journal, &service, 4096u, 10u), "storage setup");
    CHECK(comp_wba_recording_service_prepare_port(&service, 31u), "storage prepare");
    CHECK(poll_until(&service, COMP_WBA_RECORDING_READY, 3u) == 0, "storage ready");
    CHECK(comp_wba_recording_service_control_port(&service, true, 31u), "storage start");
    /* Simulate a nearly full reservation without thousands of fixture frames. */
    service.committed_bytes = 2100u;
    service.stats.committed_bytes = 2100u;
    (void)comp_wba_recording_service_poll(&service);
    CHECK(service.state == COMP_WBA_RECORDING_STOPPING &&
          !service.microphone_active && service.stats.storage_limit_stops == 1u &&
          comp_wba_recording_service_stop_reason(&service) ==
              COMP_WBA_RECORDING_STOP_STORAGE_LIMIT,
          "storage limit stops normally");

    /* A completed UNSYNCED entry must block a new reservation rather than be
     * silently evicted by the journal's generic ring policy. */
    CHECK(setup(&fixture, &journal, &service, DATA_BYTES, 10u), "full setup");
    CHECK(comp_wba_recording_service_prepare_port(&service, 32u), "full reserve");
    first_id = service.entry.recording_id;
    {
        uint8_t sha[32] = {1u};
        CHECK(comp_recording_journal_finalize(&journal, first_id, 1u, 1u, 1u,
                                              sha, 3u) ==
                  COMP_RECORDING_JOURNAL_OK,
              "make unsynced full extent");
    }
    service.state = COMP_WBA_RECORDING_IDLE;
    CHECK(!comp_wba_recording_service_prepare_port(&service, 33u),
          "non-evicting prepare rejects full unsynced storage");
    CHECK(comp_wba_recording_service_fault_reason(&service) ==
              COMP_WBA_RECORDING_FAULT_STORAGE_FULL,
          "full unsynced storage has a distinct retryable reason");
    CHECK(comp_recording_journal_find(&journal, first_id) != NULL,
          "unsynced entry preserved");
    return 0;
}

static int test_failed_stop_reports_active_until_retry(void)
{
    fixture_t fixture;
    comp_recording_journal_t journal;
    comp_wba_recording_service_t service;

    CHECK(setup(&fixture, &journal, &service, 8192u, 10u), "stop setup");
    CHECK(comp_wba_recording_service_prepare_port(&service, 41u), "stop prepare");
    CHECK(poll_until(&service, COMP_WBA_RECORDING_READY, 4u) == 0, "stop ready");
    CHECK(comp_wba_recording_service_control_port(&service, true, 41u), "stop start");
    fixture.fail_mic_off_once = true;
    CHECK(!comp_wba_recording_service_control_port(&service, false, 41u),
          "failed mic stop rejected");
    CHECK(service.state == COMP_WBA_RECORDING_FAULT && service.microphone_active &&
          fixture.last_report == DENZIC_AUDIO_RECORDING_STATE_STOPPING &&
          fixture.last_capture_active,
          "failed stop remains truthfully active");
    (void)comp_wba_recording_service_poll(&service);
    CHECK(!service.microphone_active &&
          fixture.last_report == DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY &&
          !fixture.last_capture_active,
          "foreground retry reports error only after mic stopped");
    return 0;
}

static int test_stop_before_first_pcm(void)
{
    fixture_t fixture;
    comp_recording_journal_t journal;
    comp_wba_recording_service_t service;
    CHECK(setup(&fixture,&journal,&service,8192u,10u),"empty capture setup");
    CHECK(comp_wba_recording_service_prepare_port(&service,51u),"empty prepare");
    CHECK(poll_until(&service,COMP_WBA_RECORDING_READY,4u)==0,"empty ready");
    CHECK(comp_wba_recording_service_control_port(&service,true,51u),"empty start");
    uint32_t id=service.entry.recording_id;
    CHECK(comp_wba_recording_service_control_port(&service,false,51u),"immediate stop");
    CHECK(poll_until(&service,COMP_WBA_RECORDING_IDLE,8u)==0,"empty capture canceled");
    CHECK(comp_recording_journal_find(&journal,id)==NULL && service.stats.finalized==0u &&
          fixture.last_report==DENZIC_AUDIO_RECORDING_STATE_CANCELED,
          "header-only recording is not advertised as a saved audio file");
    CHECK(comp_wba_recording_service_prepare_port(&service,52u),"empty capture releases reservation for retry");
    return 0;
}

static int test_durable_prefix_salvage(void)
{
    fixture_t fixture;comp_recording_journal_t journal;
    comp_wba_recording_service_t service;int16_t pcm[COMP_WBA_RECORDING_PCM_FRAME_SAMPLES];
    CHECK(setup(&fixture,&journal,&service,8192u,10u),"salvage setup");
    comp_recording_journal_port_t port=make_port();
    CHECK(comp_recording_journal_mount_strict(&journal,&port,&fixture,FLASH_BYTES)==COMP_RECORDING_JOURNAL_OK,"strict append mount");
    CHECK(comp_wba_recording_service_prepare_port(&service,61u),"salvage prepare");
    CHECK(poll_until(&service,COMP_WBA_RECORDING_READY,8u)==0,"salvage ready");
    CHECK(comp_wba_recording_service_control_port(&service,true,61u),"salvage capture");
    uint32_t catalog_programs=fixture.catalog_programs,erases=fixture.payload_erases;
    fill_pcm(pcm);
    for(uint32_t i=0u;i<100u;++i) {
        CHECK(comp_wba_recording_service_pcm(&service,pcm,160u,16000u),"salvage queue");
        (void)comp_wba_recording_service_poll(&service);
    }
    /* The foreground task gets a separate turn to program the page after
     * the final queued PCM half has been encoded. */
    (void)comp_wba_recording_service_poll(&service);
    CHECK(fixture.catalog_programs==catalog_programs && fixture.payload_erases==erases,
          "active capture only programs audio and compact pre-erased checkpoints");
    uint32_t id=service.entry.recording_id;
    const comp_recording_journal_entry_t *writing=comp_recording_journal_find(&journal,id);
    CHECK(writing && writing->committed_bytes>=256u && (writing->reserved&COMP_RECORDING_CHECKPOINT_VERIFIED),"programmed bytes durably checkpointed");
    fixture_t corrupted=fixture;corrupted.bytes[writing->payload_offset+15u]^=1u;
    comp_recording_journal_t rebooted;uint32_t recovered=0u,unresolved=0u;
    CHECK(comp_recording_journal_mount_strict(&rebooted,&port,&corrupted,FLASH_BYTES)==COMP_RECORDING_JOURNAL_OK,"corrupt payload catalog mounts");
    CHECK(comp_wba_recording_salvage(&rebooted,&recovered,&unresolved) && recovered==0u && unresolved==1u,"digest mismatch retained without adoption");
    CHECK(comp_recording_journal_find(&rebooted,id)->sync_state==COMP_RECORDING_JOURNAL_WRITING,"corrupt sole copy remains reserved");
    CHECK(comp_recording_journal_mount_strict(&rebooted,&port,&fixture,FLASH_BYTES)==COMP_RECORDING_JOURNAL_OK,"power loss reloads last valid append");
    CHECK(comp_wba_recording_salvage(&rebooted,&recovered,&unresolved) && recovered==1u && unresolved==0u,"valid prefix salvaged");
    const comp_recording_journal_entry_t *saved=comp_recording_journal_find(&rebooted,id);
    CHECK(saved && saved->sync_state==COMP_RECORDING_JOURNAL_UNSYNCED && (saved->reserved&COMP_RECORDING_RECOVERED_PREFIX),"interrupted capture explicitly marked");
    CHECK(saved->total_length==252u && saved->duration_ms==960u && saved->acked_offset==0u,"only complete packets sealed, no forged ACK");
    CHECK(comp_recording_journal_mount_strict(&rebooted,&port,&fixture,FLASH_BYTES)==COMP_RECORDING_JOURNAL_OK,"salvage receipt survives reload");
    CHECK(comp_wba_recording_salvage(&rebooted,&recovered,&unresolved) && recovered==0u,"salvage idempotent");
    comp_recording_journal_entry_t empty;
    CHECK(comp_recording_journal_begin(&rebooted,4096u,0u,0u,3u,1u,&empty)==COMP_RECORDING_JOURNAL_OK,"legacy unverified write fixture");
    CHECK(comp_wba_recording_salvage(&rebooted,&recovered,&unresolved) && unresolved==1u,"unverified writing intent never silently deleted");
    comp_recording_journal_entry_t initialized;
    CHECK(comp_recording_journal_begin(&rebooted,8192u,0u,0u,3u,1u,&initialized)==COMP_RECORDING_JOURNAL_OK,"initialized empty reservation");
    CHECK(comp_recording_journal_checkpoint_log_init(&rebooted,initialized.recording_id)==COMP_RECORDING_JOURNAL_OK,"empty log ready");
    uint32_t payload_erases=fixture.payload_erases;
    CHECK(comp_wba_recording_salvage(&rebooted,&recovered,&unresolved) && recovered==0u && unresolved==1u &&
          !comp_recording_journal_find(&rebooted,initialized.recording_id) &&
          comp_recording_journal_find(&rebooted,empty.recording_id) && fixture.payload_erases==payload_erases,
          "proved empty reservation reclaimed without erasing payload or legacy intent");
    CHECK(comp_recording_journal_begin(&rebooted,8192u,0u,0u,3u,1u,&initialized)==COMP_RECORDING_JOURNAL_OK,"partial zero-checkpoint reservation");
    CHECK(comp_recording_journal_checkpoint_log_init(&rebooted,initialized.recording_id)==COMP_RECORDING_JOURNAL_OK,"partial log ready");
    uint32_t last_byte=initialized.extent_offset+initialized.reserved_bytes-1u;
    fixture.bytes[last_byte]=0x5Au;
    CHECK(comp_wba_recording_salvage(&rebooted,&recovered,&unresolved) && unresolved==2u &&
          comp_recording_journal_find(&rebooted,initialized.recording_id) && fixture.bytes[last_byte]==0x5Au &&
          fixture.payload_erases==payload_erases,"uncheckpointed partial write was discarded");
    puts("PASS_DURABLE_PREFIX_SALVAGE_HOST valid_identity=1 corrupt_kept=1 complete_packets_only=1 explicit_incomplete=1 ack_forged=0");
    return 0;
}

static int test_fault_preserves_latest_complete_committed_prefix(void)
{
    for (uint32_t failure = 0u; failure < 3u; ++failure) {
        fixture_t fixture; comp_recording_journal_t journal, rebooted;
        comp_wba_recording_service_t service; int16_t pcm[160];
        comp_recording_journal_port_t port = make_port();
        CHECK(setup(&fixture, &journal, &service, 16384u, 10u), "fault tail setup");
        CHECK(comp_recording_journal_mount_strict(&journal, &port, &fixture, FLASH_BYTES) == COMP_RECORDING_JOURNAL_OK, "fault tail strict append mount");
        CHECK(comp_wba_recording_service_prepare_port(&service, 71u), "fault tail prepare");
        CHECK(poll_until(&service, COMP_WBA_RECORDING_READY, 12u) == 0, "fault tail ready");
        CHECK(comp_wba_recording_service_control_port(&service, true, 71u), "fault tail start");
        fill_pcm(pcm);
        for (uint32_t i = 0u; i < 1200u; ++i) {
            CHECK(comp_wba_recording_service_pcm(&service, pcm, 160u, 16000u), "fault tail PCM accepted");
            (void)comp_wba_recording_service_poll(&service);
            (void)comp_wba_recording_service_poll(&service);
        }
        uint32_t id = service.entry.recording_id, committed = service.committed_bytes;
        uint32_t frames = service.durable_frames;
        const comp_recording_journal_entry_t *entry = comp_recording_journal_find(&journal, id);
        CHECK(entry && committed >= 2048u && committed > entry->committed_bytes, "actual programmed audio exceeds old checkpoint");
        uint32_t old_checkpoint = entry->committed_bytes;
        if (failure == 1u) fixture.fail_program = true;
        if (failure == 2u) fixture.bytes[entry->payload_offset + 15u] ^= 1u;
        CHECK(comp_wba_recording_service_capture_fault(&service, 71u, COMP_WBA_RECORDING_FAULT_DEADLINE), "external fault accepted for actual owner");
        CHECK(!service.microphone_active && service.state == COMP_WBA_RECORDING_FAULT, "fault stops capture without claiming normal completion");
        fixture.fail_program = false;
        CHECK(comp_recording_journal_mount_strict(&rebooted, &port, &fixture, FLASH_BYTES) == COMP_RECORDING_JOURNAL_OK, "fault receipt survives immediate reboot");
        entry = comp_recording_journal_find(&rebooted, id);
        if (failure == 0u) {
            CHECK(entry && entry->sync_state == COMP_RECORDING_JOURNAL_UNSYNCED &&
                  (entry->reserved & COMP_RECORDING_RECOVERED_PREFIX), "latest stopped prefix is available and marked incomplete");
            CHECK(entry->total_length > old_checkpoint && entry->total_length <= committed &&
                  entry->duration_ms == frames * 20u && entry->acked_offset == 0u,
                  "all complete committed packets retained, staged tail excluded and no forged ACK");
        } else {
            CHECK(entry && entry->sync_state == COMP_RECORDING_JOURNAL_WRITING &&
                  entry->reserved_bytes == 16384u && entry->acked_offset == 0u,
                  "failed checkpoint or corrupt sole copy remains reserved, not consumed or trimmed");
        }
    }
    puts("PASS_FAULT_TAIL_RECOVERY_SOFTWARE complete_committed_packets=1 explicit_incomplete=1 io_failure_kept=1 corruption_kept=1 fake_ack=0");
    return 0;
}

static int test_duration_quantization_and_insufficient_samples(void)
{
    comp_duration_stats_t stats = {0};
    uint32_t upper = UINT32_MAX;

    CHECK(!comp_duration_stats_peak_upper_ms(&stats, &upper) && upper == 0u,
          "no samples is unknown, not zero cost");
    for (unsigned i = 0u; i < 19u; ++i) comp_duration_stats_note(&stats, 4u);
    CHECK(!comp_duration_stats_percentile_upper_ms(&stats, 95u, &upper),
          "insufficient percentile sample count stays invalid");
    comp_duration_stats_note(&stats, 9u);
    CHECK(comp_duration_stats_percentile_upper_ms(&stats, 95u, &upper) && upper == 5u,
          "P95 uses nearest rank and adds a full tick uncertainty");
    CHECK(comp_duration_stats_peak_upper_ms(&stats, &upper) && upper == 10u,
          "peak reports conservative tick upper bound");
    CHECK(comp_duration_stats_percentile_upper_ms(&stats, 100u, &upper) && upper == 10u,
          "P100 includes isolated slow sample");
    comp_duration_stats_note(&stats, 17u);
    CHECK(comp_duration_stats_percentile_upper_ms(&stats, 100u, &upper) && upper == 18u,
          "tail bucket cannot understate large duration");
    CHECK(!comp_duration_stats_percentile_upper_ms(&stats, 0u, &upper) &&
          !comp_duration_stats_percentile_upper_ms(&stats, 101u, &upper),
          "invalid percentiles rejected");
    stats.samples = UINT32_MAX;
    comp_duration_stats_note(&stats, 1u);
    CHECK(stats.saturated && !comp_duration_stats_percentile_upper_ms(&stats, 95u, &upper),
          "counter overflow invalidates result instead of wrapping");
    return 0;
}

int main(void)
{
    comp_wba_recording_service_t unbound;
    memset(&unbound, 0, sizeof(unbound));
    if (test_duration_quantization_and_insufficient_samples() != 0) return 1;
    CHECK(comp_wba_recording_service_poll(&unbound) ==
              COMP_WBA_RECORDING_UNBOUND,
          "unbound poll safe");
    if (test_prepare_cancel_and_normal_finalize() != 0) return 1;
    if (test_overflow_and_budget_faults() != 0) return 1;
    if (test_storage_stop_and_non_evict() != 0) return 1;
    if (test_failed_stop_reports_active_until_retry() != 0) return 1;
    if (test_stop_before_first_pcm() != 0) return 1;
    if (test_durable_prefix_salvage() != 0) return 1;
    if (test_fault_preserves_latest_complete_committed_prefix() != 0) return 1;
    puts("PASS_WBA_RECORDING_SERVICE_HOST");
    return 0;
}
