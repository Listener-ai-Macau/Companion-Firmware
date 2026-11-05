#include "wba_recording_service.h"

#include <limits.h>
#include <string.h>

#define RECORDING_SECTOR_BYTES COMP_RECORDING_JOURNAL_SECTOR_BYTES
#define RECORDING_PROGRAM_UNIT 256u
#define RECORDING_DEFAULT_BUDGET_MS 10u
#define RECORDING_MAX_ENCODED_PACKET (COMPANION_OPUS16_MAX_PACKET + 2u)
#define RECORDING_DRAIN_PACKETS \
    ((COMP_WBA_RECORDING_PCM_RING_SLOTS + 1u) / 2u + 1u)
#define RECORDING_DRAIN_RESERVE_BYTES \
    (RECORDING_DRAIN_PACKETS * RECORDING_MAX_ENCODED_PACKET)

static uint32_t service_now(const comp_wba_recording_service_t *service)
{
    return service->config.now_ms(service->config.context);
}

static void report_state(comp_wba_recording_service_t *service,
                         denzic_audio_recording_state_v1_t state,
                         bool capture_active)
{
    service->config.report(service->config.context, service->token, state,
                           capture_active);
}

static void destroy_encoder(comp_wba_recording_service_t *service)
{
    if (service->encoder_initialized) {
        companion_opus16_rt_destroy(&service->codec);
        service->encoder_initialized = false;
    }
}

static uint32_t align_up_sector(uint32_t value)
{
    const uint32_t remainder = value % RECORDING_SECTOR_BYTES;
    if (remainder == 0u) return value;
    if (value > UINT32_MAX - (RECORDING_SECTOR_BYTES - remainder)) return 0u;
    return value + RECORDING_SECTOR_BYTES - remainder;
}

static bool journal_entry_live(const comp_recording_journal_entry_t *entry)
{
    return entry->recording_id != 0u &&
           entry->sync_state != COMP_RECORDING_JOURNAL_EMPTY;
}

static bool ranges_overlap(uint32_t a_offset, uint32_t a_length,
                           uint32_t b_offset, uint32_t b_length)
{
    return a_offset < b_offset + b_length &&
           b_offset < a_offset + a_length;
}

/* Product capture requires both an empty directory slot and a free extent
 * before calling begin().  The journal also protects UNSYNCED recordings, but
 * this preflight gives the runtime an immediate storage-full result instead of
 * relying on an ACKED eviction plan during capture preparation. */
static bool non_evicting_reservation_available(
    const comp_recording_journal_t *journal,
    uint32_t requested_bytes)
{
    uint32_t bytes;
    uint32_t candidate = 0u;
    bool empty_slot = false;

    if (journal == NULL || !journal->mounted || requested_bytes == 0u) {
        return false;
    }
    bytes = align_up_sector(requested_bytes);
    if (bytes == 0u || bytes > journal->allocation_bytes) return false;
    for (uint32_t index = 0u;
         index < COMP_RECORDING_JOURNAL_MAX_ENTRIES; ++index) {
        if (!journal_entry_live(&journal->catalog.entries[index])) {
            empty_slot = true;
            break;
        }
    }
    if (!empty_slot) return false;

    while (candidate <= journal->allocation_bytes &&
           bytes <= journal->allocation_bytes - candidate) {
        bool collision = false;
        uint32_t next = candidate + RECORDING_SECTOR_BYTES;
        for (uint32_t index = 0u;
             index < COMP_RECORDING_JOURNAL_MAX_ENTRIES; ++index) {
            const comp_recording_journal_entry_t *entry =
                &journal->catalog.entries[index];
            if (!journal_entry_live(entry)) continue;
            if (ranges_overlap(candidate, bytes, entry->extent_offset,
                               entry->reserved_bytes)) {
                const uint32_t end =
                    entry->extent_offset + entry->reserved_bytes;
                collision = true;
                next = align_up_sector(end);
                break;
            }
        }
        if (!collision) return true;
        if (next == 0u || next <= candidate) return false;
        candidate = next;
    }
    return false;
}

static void note_duration(uint32_t elapsed, uint32_t *maximum)
{
    if (elapsed > *maximum) *maximum = elapsed;
}

static bool active_budget_ok(comp_wba_recording_service_t *service,
                             uint32_t elapsed)
{
    if (service->state == COMP_WBA_RECORDING_CAPTURING &&
        elapsed > service->config.foreground_budget_ms) {
        service->stats.budget_violations++;
        return false;
    }
    return true;
}

static bool salvage_entries(comp_recording_journal_t *, uint32_t selected_id,
                            uint32_t *recovered, uint32_t *unresolved);

static void seal_stopped_fault_prefix(comp_wba_recording_service_t *service)
{
    comp_recording_journal_t *journal = service->config.journal;
    const comp_recording_journal_entry_t *entry =
        comp_recording_journal_find(journal, service->entry.recording_id);
    if (service->microphone_active || !journal->append_catalogs || !entry ||
        entry->sync_state != COMP_RECORDING_JOURNAL_WRITING ||
        service->committed_bytes <= 12u || service->durable_frames == 0u) return;
    /* The microphone is stopped: checkpoint the already-programmed bytes
     * before reporting the fault or allowing restart. Never add staged PCM,
     * retry an unknown failed payload write or adopt unchecked NOR contents. */
    if (service->committed_bytes > service->checkpoint_bytes) {
        comp_wba_recording_sha256_t checkpoint = service->sha256;
        uint8_t digest[32]; companion_sha256_final(&checkpoint, digest);
        if (comp_recording_journal_checkpoint_verified(journal,
                service->entry.recording_id, service->committed_bytes,
                service->content_crc32, digest) != COMP_RECORDING_JOURNAL_OK) return;
        service->checkpoint_bytes = service->committed_bytes;
    }
    /* Re-read and verify only this capture's prefix, seal complete COP1
     * packets and mark it incomplete. An I/O/digest failure stays reserved. */
    (void)salvage_entries(journal, service->entry.recording_id, NULL, NULL);
}

static void enter_fault(comp_wba_recording_service_t *service,
                        bool abort_unwritten_prepare,
                        comp_wba_recording_fault_reason_t reason)
{
    const comp_wba_recording_service_state_t prior = service->state;

    service->state = COMP_WBA_RECORDING_FAULT;
    service->last_stop_reason = COMP_WBA_RECORDING_STOP_FAILURE;
    service->last_fault_reason = reason;
    service->stats.failures++;
    if (service->microphone_active) {
        if (service->config.mic_control(service->config.context, false)) {
            service->microphone_active = false;
        } else {
            report_state(service, DENZIC_AUDIO_RECORDING_STATE_STOPPING, true);
        }
    }
    destroy_encoder(service);
    if (abort_unwritten_prepare &&
        (prior == COMP_WBA_RECORDING_PREPARING ||
         prior == COMP_WBA_RECORDING_READY) &&
        service->entry.recording_id != 0u) {
        if (comp_recording_journal_abort(service->config.journal,
                                         service->entry.recording_id) ==
            COMP_RECORDING_JOURNAL_OK) {
            memset(&service->entry, 0, sizeof(service->entry));
        }
    }
    if (!service->microphone_active) {
        seal_stopped_fault_prefix(service);
        report_state(service, DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY,
                     false);
        service->fault_reported = true;
    }
}

static bool append_encoded(comp_wba_recording_service_t *service,
                           const uint8_t *data, size_t length)
{
    if (length == 0u) return true;
    if (length > COMP_WBA_RECORDING_STAGE_BYTES - service->stage_length ||
        service->committed_bytes + service->stage_length >
            service->payload_limit ||
        length > service->payload_limit -
                     (service->committed_bytes + service->stage_length)) {
        return false;
    }
    memcpy(&service->stage[service->stage_length], data, length);
    service->stage_length =
        (uint16_t)(service->stage_length + (uint16_t)length);
    return true;
}

static bool program_stage(comp_wba_recording_service_t *service,
                          bool allow_partial)
{
    uint32_t length;
    uint32_t started;
    uint32_t elapsed;

    if (service->stage_length == 0u) return true;
    if (!allow_partial && service->stage_length < RECORDING_PROGRAM_UNIT) {
        return true;
    }
    length = service->stage_length < RECORDING_PROGRAM_UNIT
                 ? service->stage_length : RECORDING_PROGRAM_UNIT;
    started = service_now(service);
    if (!service->config.journal->port.program(
            service->config.journal->port_context,
            service->entry.payload_offset + service->committed_bytes,
            service->stage, length)) {
        enter_fault(service, false, COMP_WBA_RECORDING_FAULT_STORAGE_IO);
        return false;
    }
    elapsed = service_now(service) - started;
    note_duration(elapsed, &service->stats.max_program_ms);
    service->stats.program_calls++;
    /* Identity follows programmed bytes, never encoded-but-staged audio. */
    companion_sha256_update(&service->sha256,service->stage,length);
    service->content_crc32=service->config.journal->port.crc32(service->content_crc32,service->stage,length);
    /* Count complete COP1 packets in the committed stream, across NOR page
     * boundaries. Encoded-but-staged PCM must not inflate live duration. */
    for (uint32_t i = 0u; i < length; ++i) {
        if (service->durable_header_remaining != 0u) {
            --service->durable_header_remaining;
        } else if (service->durable_packet_remaining != 0u) {
            if (--service->durable_packet_remaining == 0u)
                ++service->durable_frames;
        } else if (service->durable_length_bytes == 0u) {
            service->durable_length_word = service->stage[i];
            service->durable_length_bytes = 1u;
        } else {
            service->durable_packet_remaining = (uint16_t)(
                service->durable_length_word | ((uint16_t)service->stage[i] << 8u));
            service->durable_length_bytes = 0u;
        }
    }
    service->committed_bytes += length;
    service->stats.committed_bytes = service->committed_bytes;
    if(service->config.journal->append_catalogs &&
       (service->checkpoint_bytes==0u || service->committed_bytes-service->checkpoint_bytes>=service->checkpoint_interval_bytes)) {
        comp_wba_recording_sha256_t checkpoint=service->sha256;
        uint8_t digest[32];companion_sha256_final(&checkpoint,digest);
        if(comp_recording_journal_checkpoint_verified(service->config.journal,service->entry.recording_id,
            service->committed_bytes,service->content_crc32,digest)!=COMP_RECORDING_JOURNAL_OK) {
            enter_fault(service,false,COMP_WBA_RECORDING_FAULT_STORAGE_IO);return false;
        }
        service->checkpoint_bytes=service->committed_bytes;
    }
    service->stage_length = (uint16_t)(service->stage_length - length);
    if (service->stage_length != 0u) {
        memmove(service->stage, &service->stage[length], service->stage_length);
    }
    /* A catalog checkpoint is part of this foreground operation too. Its
     * cost must not be hidden behind the payload-only program statistic. */
    elapsed = service_now(service) - started;
    if (!active_budget_ok(service, elapsed)) {
        enter_fault(service, false, COMP_WBA_RECORDING_FAULT_DEADLINE);
        return false;
    }
    return true;
}

static bool encode_one_pcm(comp_wba_recording_service_t *service)
{
    const uint32_t frames_before = service->codec.frames_encoded;
    uint32_t started;
    uint32_t elapsed;
    size_t length;

    if (service->ring_count == 0u) return true;
    started = service_now(service);
    length = companion_opus16_rt_encode(
        &service->codec, service->pcm_ring[service->ring_read],
        COMP_WBA_RECORDING_PCM_FRAME_SAMPLES, service->packet,
        sizeof(service->packet), false);
    elapsed = service_now(service) - started;
    note_duration(elapsed, &service->stats.max_encode_ms);
    /* A 10 ms half can only buffer PCM; count completed Opus frames rather
     * than mixing those cheap half-frame calls into the 20 ms codec P95. */
    if (service->codec.frames_encoded != frames_before)
        comp_duration_stats_note(&service->stats.encode_duration, elapsed);
    if (service->codec.pcm_fill >= service->codec.frame_samples ||
        !append_encoded(service, service->packet, length)) {
        enter_fault(service, false, COMP_WBA_RECORDING_FAULT_CODEC);
        return false;
    }
    service->ring_read =
        (uint16_t)((service->ring_read + 1u) %
                   COMP_WBA_RECORDING_PCM_RING_SLOTS);
    service->ring_count--;
    service->stats.encoded_frames +=
        service->codec.frames_encoded - frames_before;
    if (!active_budget_ok(service, elapsed)) {
        enter_fault(service, false, COMP_WBA_RECORDING_FAULT_DEADLINE);
        return false;
    }
    return true;
}

static bool finish_prepare(comp_wba_recording_service_t *service)
{
    static const int16_t dummy = 0;
    size_t header_length;

    if(service->config.journal->append_catalogs) {
        if(comp_recording_journal_checkpoint_log_init(service->config.journal,service->entry.recording_id)!=
           COMP_RECORDING_JOURNAL_OK) {
            enter_fault(service,true,COMP_WBA_RECORDING_FAULT_STORAGE_IO);return false;
        }
        service->entry=*comp_recording_journal_find(service->config.journal,service->entry.recording_id);
    }
    service->payload_limit=comp_recording_journal_payload_limit(&service->entry);
    /* Leave room for the initial and final short program. The maximum loss
     * interval scales with the reserved extent; this is a finite prefix log. */
    uint32_t interval=(service->payload_limit+61u)/62u+256u;
    interval=(interval+255u)/256u*256u;
    service->checkpoint_interval_bytes=interval<65536u ? 65536u : interval;

    if (!companion_opus16_rt_init_rate_frame(
            &service->codec, 16000u, 20u)) {
        enter_fault(service, true, COMP_WBA_RECORDING_FAULT_CODEC);
        return false;
    }
    service->encoder_initialized = true;
    companion_sha256_init(&service->sha256);
    service->content_crc32 = 0u;
    service->stage_length = 0u;
    header_length = companion_opus16_rt_encode(
        &service->codec, &dummy, 0u, service->packet,
        sizeof(service->packet), true);
    if (header_length != 12u ||
        !append_encoded(service, service->packet, header_length)) {
        enter_fault(service, true, COMP_WBA_RECORDING_FAULT_CODEC);
        return false;
    }
    service->state = COMP_WBA_RECORDING_READY;
    service->stats.prepared++;
    return true;
}

static bool cancel_prepare(comp_wba_recording_service_t *service)
{
    const uint32_t recording_id = service->entry.recording_id;

    destroy_encoder(service);
    if (recording_id != 0u &&
        comp_recording_journal_abort(service->config.journal, recording_id) !=
            COMP_RECORDING_JOURNAL_OK) {
        enter_fault(service, false, COMP_WBA_RECORDING_FAULT_STORAGE_IO);
        return false;
    }
    service->stats.cancellations++;
    report_state(service, DENZIC_AUDIO_RECORDING_STATE_CANCELED, false);
    memset(&service->entry, 0, sizeof(service->entry));
    service->stage_length = 0u;
    service->state = COMP_WBA_RECORDING_IDLE;
    return true;
}

bool comp_wba_recording_service_init(
    comp_wba_recording_service_t *service,
    const comp_wba_recording_service_config_t *config)
{
    if (service == NULL) return false;
    memset(service, 0, sizeof(*service));
    service->state = COMP_WBA_RECORDING_UNBOUND;
    if (config == NULL || config->journal == NULL ||
        !config->journal->mounted || config->reserve_bytes == 0u ||
        config->mic_control == NULL || config->now_ms == NULL ||
        config->report == NULL ||
        config->partition_base_address <
            COMP_WBA_RECORDING_MIN_PARTITION_BASE ||
        (config->partition_base_address % RECORDING_SECTOR_BYTES) != 0u ||
        config->journal->region_bytes >
            UINT32_MAX - config->partition_base_address) {
        return false;
    }
    service->config = *config;
    if (service->config.foreground_budget_ms == 0u) {
        service->config.foreground_budget_ms = RECORDING_DEFAULT_BUDGET_MS;
    }
    service->state = COMP_WBA_RECORDING_IDLE;
    return true;
}

bool comp_wba_recording_service_prepare_port(void *context, uint32_t token)
{
    comp_wba_recording_service_t *service = context;
    comp_recording_journal_result_t result;
    uint32_t unix_s = 0u;

    if (service == NULL || token == 0u ||
        (service->state != COMP_WBA_RECORDING_IDLE &&
         service->state != COMP_WBA_RECORDING_TRANSFER_READY)) {
        return false;
    }
    service->last_fault_reason = COMP_WBA_RECORDING_FAULT_NONE;
    if(service->config.journal->append_catalogs && service->config.reserve_bytes<8192u) {
        service->last_fault_reason=COMP_WBA_RECORDING_FAULT_STORAGE_FULL;
        return false;
    }
    if (!non_evicting_reservation_available(service->config.journal,
                                             service->config.reserve_bytes)) {
        service->last_fault_reason = COMP_WBA_RECORDING_FAULT_STORAGE_FULL;
        return false;
    }
    if (service->config.unix_s != NULL) {
        unix_s = service->config.unix_s(service->config.context);
    }
    memset(&service->entry, 0, sizeof(service->entry));
    result = comp_recording_journal_begin(
        service->config.journal, service->config.reserve_bytes,
        unix_s, service_now(service), COMP_WBA_RECORDING_CODEC_OPUS16,
        COMP_WBA_RECORDING_SOURCE_MIC_SAI, &service->entry);
    if (result != COMP_RECORDING_JOURNAL_OK ||
        service->config.journal->last_ring_evicted_count != 0u) {
        service->last_fault_reason =
            (result == COMP_RECORDING_JOURNAL_STORAGE_FULL ||
             result == COMP_RECORDING_JOURNAL_DIRECTORY_FULL)
                ? COMP_WBA_RECORDING_FAULT_STORAGE_FULL
                : COMP_WBA_RECORDING_FAULT_STORAGE_IO;
        return false;
    }
    service->token = token;
    service->erase_offset = 0u;
    service->committed_bytes = 0u;
    service->checkpoint_bytes=0u;
    service->durable_frames = 0u;
    service->durable_packet_remaining = 0u;
    service->durable_length_word = 0u;
    service->durable_header_remaining = 12u;
    service->durable_length_bytes = 0u;
    service->stats.committed_bytes = 0u;
    memset(&service->stats.encode_duration, 0, sizeof(service->stats.encode_duration));
    service->ring_read = service->ring_write = service->ring_count = 0u;
    service->stage_length = 0u;
    service->flush_complete = false;
    service->fault_reported = false;
    service->pcm_overflowed = false;
    service->state = COMP_WBA_RECORDING_PREPARING;
    service->last_stop_reason = COMP_WBA_RECORDING_STOP_NONE;
    service->last_fault_reason = COMP_WBA_RECORDING_FAULT_NONE;
    service->stats.prepare_requests++;
    report_state(service, DENZIC_AUDIO_RECORDING_STATE_PENDING_START, false);
    return true;
}

bool comp_wba_recording_service_ready_port(void *context, uint32_t token)
{
    const comp_wba_recording_service_t *service = context;
    return service != NULL && token != 0u && service->token == token &&
           service->state == COMP_WBA_RECORDING_READY;
}

bool comp_wba_recording_service_control_port(void *context, bool start,
                                              uint32_t token)
{
    comp_wba_recording_service_t *service = context;

    if (service == NULL || token == 0u || token != service->token) return false;
    if (!start) {
        if (service->state == COMP_WBA_RECORDING_PREPARING ||
            service->state == COMP_WBA_RECORDING_READY) {
            return cancel_prepare(service);
        }
        if (service->state == COMP_WBA_RECORDING_STOPPING) return true;
        if (service->state != COMP_WBA_RECORDING_CAPTURING) return false;
        if (!service->config.mic_control(service->config.context, false)) {
            service->state = COMP_WBA_RECORDING_FAULT;
            service->last_stop_reason = COMP_WBA_RECORDING_STOP_FAILURE;
            service->last_fault_reason = COMP_WBA_RECORDING_FAULT_MIC_CONTROL;
            service->stats.failures++;
            destroy_encoder(service);
            report_state(service, DENZIC_AUDIO_RECORDING_STATE_STOPPING, true);
            return false;
        }
        service->microphone_active = false;
        service->state = COMP_WBA_RECORDING_STOPPING;
        service->last_stop_reason = COMP_WBA_RECORDING_STOP_USER;
        service->stats.stops++;
        report_state(service, DENZIC_AUDIO_RECORDING_STATE_STOPPING, false);
        return true;
    }
    if (service->state != COMP_WBA_RECORDING_READY ||
        !service->encoder_initialized) {
        return false;
    }
    if (!service->config.mic_control(service->config.context, true)) {
        enter_fault(service, true, COMP_WBA_RECORDING_FAULT_MIC_CONTROL);
        return false;
    }
    service->capture_started_ms = service_now(service);
    service->microphone_active = true;
    service->state = COMP_WBA_RECORDING_CAPTURING;
    service->stats.starts++;
    report_state(service, DENZIC_AUDIO_RECORDING_STATE_RECORDING, true);
    return true;
}

bool comp_wba_recording_service_pcm(void *context, const int16_t *samples,
                                    size_t count, uint32_t sample_rate_hz)
{
    comp_wba_recording_service_t *service = context;

    if (service == NULL || samples == NULL ||
        count != COMP_WBA_RECORDING_PCM_FRAME_SAMPLES ||
        sample_rate_hz != 16000u ||
        service->state != COMP_WBA_RECORDING_CAPTURING ||
        !service->microphone_active) {
        return false;
    }
    if (service->ring_count == COMP_WBA_RECORDING_PCM_RING_SLOTS) {
        service->stats.dropped_pcm_frames++;
        service->pcm_overflowed = true;
        return false;
    }
    memcpy(service->pcm_ring[service->ring_write], samples,
           COMP_WBA_RECORDING_PCM_FRAME_SAMPLES * sizeof(int16_t));
    service->ring_write =
        (uint16_t)((service->ring_write + 1u) %
                   COMP_WBA_RECORDING_PCM_RING_SLOTS);
    service->ring_count++;
    service->stats.pcm_frames++;
    if (service->ring_count > service->stats.max_ring_depth) {
        service->stats.max_ring_depth = service->ring_count;
    }
    return true;
}

bool comp_wba_recording_service_capture_fault(
    void *context, uint32_t token,
    comp_wba_recording_fault_reason_t reason)
{
    comp_wba_recording_service_t *service = context;
    if (service == NULL || token == 0u || token != service->token) return false;
    if (service->state == COMP_WBA_RECORDING_FAULT) return true;
    if (service->state != COMP_WBA_RECORDING_CAPTURING &&
        service->state != COMP_WBA_RECORDING_STOPPING) return false;
    if (reason == COMP_WBA_RECORDING_FAULT_NONE) {
        reason = COMP_WBA_RECORDING_FAULT_PLATFORM_CAPTURE;
    }
    service->stats.external_capture_faults++;
    enter_fault(service, false, reason);
    return true;
}

static void finalize_recording(comp_wba_recording_service_t *service)
{
    const uint32_t duration_ms =
        service->codec.frames_encoded * (uint32_t)service->codec.frame_ms;
    comp_recording_journal_result_t result;

    /* A quick stop before the first PCM frame leaves only the COP1 header.
     * Cancel it instead of advertising an undecodable zero-audio recording. */
    if (service->codec.frames_encoded == 0u) {
        (void)cancel_prepare(service);
        return;
    }
    if (service->committed_bytes == 0u) {
        enter_fault(service, false, COMP_WBA_RECORDING_FAULT_CODEC);
        return;
    }
    comp_wba_recording_sha256_t final_identity = service->sha256;
    companion_sha256_final(&final_identity, service->sha256_digest);
    result = comp_recording_journal_finalize(
        service->config.journal, service->entry.recording_id,
        service->committed_bytes, duration_ms, service->content_crc32,
        service->sha256_digest, COMP_WBA_RECORDING_CODEC_OPUS16);
    if (result != COMP_RECORDING_JOURNAL_OK) {
        enter_fault(service, false, COMP_WBA_RECORDING_FAULT_STORAGE_IO);
        return;
    }
    if (comp_recording_journal_trim_completed_extent(
            service->config.journal, service->entry.recording_id) !=
        COMP_RECORDING_JOURNAL_OK) {
        service->stats.trim_failures++;
    }
    destroy_encoder(service);
    service->state = COMP_WBA_RECORDING_TRANSFER_READY;
    service->stats.finalized++;
    report_state(service, DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY, false);
}

comp_wba_recording_service_state_t comp_wba_recording_service_poll(
    comp_wba_recording_service_t *service)
{
    uint32_t poll_started;

    if (service == NULL || service->state == COMP_WBA_RECORDING_UNBOUND ||
        service->config.now_ms == NULL) {
        return COMP_WBA_RECORDING_UNBOUND;
    }
    poll_started = service_now(service);
    if (service->state == COMP_WBA_RECORDING_PREPARING) {
        if (service->erase_offset < service->entry.reserved_bytes) {
            if (!service->config.journal->port.erase(
                    service->config.journal->port_context,
                    service->entry.extent_offset + service->erase_offset,
                    RECORDING_SECTOR_BYTES)) {
                enter_fault(service, true,
                            COMP_WBA_RECORDING_FAULT_STORAGE_IO);
            } else {
                service->erase_offset += RECORDING_SECTOR_BYTES;
                service->stats.erase_sectors++;
            }
        } else {
            (void)finish_prepare(service);
        }
    } else if (service->state == COMP_WBA_RECORDING_CAPTURING) {
        if (service->pcm_overflowed) {
            enter_fault(service, false,
                        COMP_WBA_RECORDING_FAULT_PCM_OVERFLOW);
        } else if (service->payload_limit - service->committed_bytes <=
                   (uint32_t)service->stage_length +
                       RECORDING_DRAIN_RESERVE_BYTES) {
            if (!service->config.mic_control(service->config.context, false)) {
                service->state = COMP_WBA_RECORDING_FAULT;
                service->last_stop_reason = COMP_WBA_RECORDING_STOP_FAILURE;
                service->last_fault_reason =
                    COMP_WBA_RECORDING_FAULT_MIC_CONTROL;
                service->stats.failures++;
                destroy_encoder(service);
                report_state(service,
                             DENZIC_AUDIO_RECORDING_STATE_STOPPING, true);
            } else {
                service->microphone_active = false;
                service->state = COMP_WBA_RECORDING_STOPPING;
                service->last_stop_reason =
                    COMP_WBA_RECORDING_STOP_STORAGE_LIMIT;
                service->stats.stops++;
                service->stats.storage_limit_stops++;
                report_state(service,
                             DENZIC_AUDIO_RECORDING_STATE_STOPPING, false);
            }
        } else if (service->stage_length >
                   COMP_WBA_RECORDING_STAGE_BYTES -
                       COMP_WBA_RECORDING_PACKET_BYTES) {
            (void)program_stage(service, false);
        } else if (service->ring_count != 0u) {
            (void)encode_one_pcm(service);
        } else if (service->stage_length >= RECORDING_PROGRAM_UNIT) {
            (void)program_stage(service, false);
        }
    } else if (service->state == COMP_WBA_RECORDING_STOPPING) {
        if (service->ring_count != 0u) {
            if (service->stage_length >
                COMP_WBA_RECORDING_STAGE_BYTES -
                    COMP_WBA_RECORDING_PACKET_BYTES) {
                (void)program_stage(service, true);
            } else {
                (void)encode_one_pcm(service);
            }
        } else if (!service->flush_complete) {
            size_t length = companion_opus16_rt_flush(
                &service->codec, service->packet, sizeof(service->packet));
            service->flush_complete = true;
            if (!append_encoded(service, service->packet, length)) {
                enter_fault(service, false, COMP_WBA_RECORDING_FAULT_CODEC);
            }
        } else if (service->stage_length != 0u) {
            (void)program_stage(service, true);
        } else {
            finalize_recording(service);
        }
    } else if (service->state == COMP_WBA_RECORDING_FAULT &&
               service->microphone_active) {
        if (service->config.mic_control(service->config.context, false)) {
            service->microphone_active = false;
            if (!service->fault_reported) {
                seal_stopped_fault_prefix(service);
                report_state(service,
                             DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY,
                             false);
                service->fault_reported = true;
            }
        }
    }
    note_duration(service_now(service) - poll_started,
                  &service->stats.max_poll_ms);
    return service->state;
}

static bool prefix_identity(comp_recording_journal_t *j,const comp_recording_journal_entry_t *e,
                            uint32_t bytes,uint8_t digest[32],uint32_t *crc)
{
    comp_wba_recording_sha256_t sha;uint8_t buffer[256];companion_sha256_init(&sha);*crc=0u;
    for(uint32_t offset=0u;offset<bytes;) {
        uint32_t length=bytes-offset;if(length>(uint32_t)sizeof(buffer))length=(uint32_t)sizeof(buffer);
        if(!j->port.read(j->port_context,e->payload_offset+offset,buffer,length))return false;
        companion_sha256_update(&sha,buffer,length);*crc=j->port.crc32(*crc,buffer,length);offset+=length;
    }
    companion_sha256_final(&sha,digest);return true;
}

static bool salvage_entries(comp_recording_journal_t *j,uint32_t selected_id,
                            uint32_t *recovered,uint32_t *unresolved)
{
    if(recovered) {*recovered=0u;}
    if(unresolved) {*unresolved=0u;}
    if(!j || !j->mounted || !j->append_catalogs)return false;
    static const uint8_t header[12]={'C','O','P','1',1u,1u,20u,0u,0x80u,0x3eu,0u,0u};
    for(uint32_t index=0u;index<COMP_RECORDING_JOURNAL_MAX_ENTRIES;++index) {
        comp_recording_journal_entry_t e=j->catalog.entries[index];
        if(selected_id && e.recording_id != selected_id)continue;
        if(e.sync_state!=COMP_RECORDING_JOURNAL_WRITING)continue;
        uint8_t digest[32],actual_header[12];uint32_t crc;
        /* An initialized but entirely erased reservation contains no audio.
         * Check the entire extent (including the checkpoint log), not merely
         * the COP1 header or committed length: a failed NOR program may have
         * changed bytes before a durable checkpoint was published. Legacy
         * intents without our initialized-log marker remain protected. */
        if(e.codec==COMP_WBA_RECORDING_CODEC_OPUS16 && e.committed_bytes==0u &&
           e.total_length==0u && e.reserved==COMP_RECORDING_CHECKPOINT_LOG_READY) {
            uint8_t page[256];bool blank=true;
            for(uint32_t offset=0u;blank && offset<e.reserved_bytes;) {
                uint32_t count=e.reserved_bytes-offset;
                if(count>sizeof(page))count=(uint32_t)sizeof(page);
                if(!j->port.read(j->port_context,e.extent_offset+offset,page,count))return false;
                for(uint32_t byte=0u;byte<count;++byte)if(page[byte]!=255u) {blank=false;break;}
                offset+=count;
            }
            if(blank) {
                if(comp_recording_journal_abort(j,e.recording_id)!=COMP_RECORDING_JOURNAL_OK)return false;
                continue;
            }
        }
        /* Never scan payload beyond the durable catalog's verified boundary.
         * Old firmware's uncheckpointed writes stay protected for recovery. */
        if(e.codec!=COMP_WBA_RECORDING_CODEC_OPUS16 || e.committed_bytes<=12u ||
            !(e.reserved&COMP_RECORDING_CHECKPOINT_VERIFIED)) {if(unresolved)++*unresolved;continue;}
        if(!prefix_identity(j,&e,e.committed_bytes,digest,&crc))return false;
        if(crc!=e.content_crc32 || memcmp(digest,e.sha256,32u)!=0) {if(unresolved)++*unresolved;continue;}
        if(!j->port.read(j->port_context,e.payload_offset,actual_header,12u))return false;
        if(memcmp(header,actual_header,12u)!=0) {if(unresolved)++*unresolved;continue;}
        uint32_t offset=12u,frames=0u;
        while(offset+2u<=e.committed_bytes) {
            uint8_t word[2];if(!j->port.read(j->port_context,e.payload_offset+offset,word,2u))return false;
            uint32_t length=(uint32_t)word[0]|((uint32_t)word[1]<<8u);
            if(length==0u || length>400u || length>e.committed_bytes-offset-2u)break;
            offset+=length+2u;++frames;
        }
        if(frames==0u) {if(unresolved)++*unresolved;continue;}
        if(!prefix_identity(j,&e,offset,digest,&crc))return false;
        if(comp_recording_journal_finalize_recovered(j,e.recording_id,offset,frames*20u,crc,digest)!=COMP_RECORDING_JOURNAL_OK)return false;
        if(comp_recording_journal_trim_completed_extent(j,e.recording_id)!=COMP_RECORDING_JOURNAL_OK)return false;
        if(recovered)++*recovered;
    }
    return true;
}

bool comp_wba_recording_salvage(comp_recording_journal_t *j,uint32_t *recovered,uint32_t *unresolved)
{
    return salvage_entries(j,0u,recovered,unresolved);
}

bool comp_wba_recording_service_recover(
    comp_wba_recording_service_t *service)
{
    if (service == NULL || service->state != COMP_WBA_RECORDING_FAULT ||
        service->microphone_active || !service->fault_reported) {
        return false;
    }
    service->state = COMP_WBA_RECORDING_IDLE;
    report_state(service, DENZIC_AUDIO_RECORDING_STATE_IDLE, false);
    return true;
}

void comp_wba_recording_service_get_stats(
    const comp_wba_recording_service_t *service,
    comp_wba_recording_service_stats_t *stats)
{
    if (service != NULL && stats != NULL) *stats = service->stats;
}

const comp_recording_journal_entry_t *comp_wba_recording_service_entry(
    const comp_wba_recording_service_t *service)
{
    if (service == NULL || service->entry.recording_id == 0u) return NULL;
    return comp_recording_journal_find(service->config.journal,
                                       service->entry.recording_id);
}

comp_wba_recording_stop_reason_t comp_wba_recording_service_stop_reason(
    const comp_wba_recording_service_t *service)
{
    return service == NULL ? COMP_WBA_RECORDING_STOP_NONE
                           : service->last_stop_reason;
}

bool comp_wba_recording_service_live_entry(
    const comp_wba_recording_service_t *service,
    comp_recording_journal_entry_t *entry)
{
    const comp_recording_journal_entry_t *stored;
    if (service == NULL || entry == NULL || service->durable_frames == 0u ||
        (service->state != COMP_WBA_RECORDING_CAPTURING &&
         service->state != COMP_WBA_RECORDING_STOPPING)) return false;
    stored = comp_wba_recording_service_entry(service);
    if (stored == NULL || stored->sync_state != COMP_RECORDING_JOURNAL_WRITING ||
        service->committed_bytes > stored->reserved_bytes) return false;
    *entry = *stored;
    entry->total_length = service->committed_bytes;
    entry->committed_bytes = service->committed_bytes;
    entry->duration_ms = service->durable_frames * (uint32_t)service->codec.frame_ms;
    entry->content_crc32 = 0u;
    memset(entry->sha256, 0, sizeof(entry->sha256));
    return true;
}

comp_wba_recording_fault_reason_t comp_wba_recording_service_fault_reason(
    const comp_wba_recording_service_t *service)
{
    return service == NULL ? COMP_WBA_RECORDING_FAULT_NONE
                           : service->last_fault_reason;
}
