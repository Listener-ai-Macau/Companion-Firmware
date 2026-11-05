#include "wba_recording_transfer.h"
#include "companion_recording_wire.h"
#include "wba_recording_crc.h"

#include <limits.h>
#include <string.h>

_Static_assert(sizeof(companion_recording_adapter_header_t) == 56u,
               "recording transfer header drift");
_Static_assert(COMP_WBA_RECORDING_TRANSFER_PAYLOAD_BYTES == 453u,
               "recording transfer payload drift");

static void put_le16(uint8_t *destination, uint16_t value)
{
    destination[0] = (uint8_t)value;
    destination[1] = (uint8_t)(value >> 8u);
}

static void put_le32(uint8_t *destination, uint32_t value)
{
    destination[0] = (uint8_t)value;
    destination[1] = (uint8_t)(value >> 8u);
    destination[2] = (uint8_t)(value >> 16u);
    destination[3] = (uint8_t)(value >> 24u);
}

static bool finalized(const comp_recording_journal_entry_t *entry)
{
    return entry != NULL && entry->total_length != 0u &&
           (entry->sync_state == COMP_RECORDING_JOURNAL_UNSYNCED ||
            entry->sync_state == COMP_RECORDING_JOURNAL_ACKED);
}

static bool heavy_io_allowed(const comp_wba_recording_transfer_t *transfer)
{
    return transfer->config.heavy_io_allowed == NULL ||
           transfer->config.heavy_io_allowed(transfer->config.context);
}

static const comp_recording_journal_entry_t *readable_entry(
    const comp_wba_recording_transfer_t *transfer, uint32_t id,
    comp_recording_journal_entry_t *snapshot)
{
    if(transfer->backend) {
        if(transfer->backend->metadata(transfer->config.context,id,snapshot)&&
           (finalized(snapshot)||(transfer->config.live_read_allowed&&snapshot->recording_id==id&&
            snapshot->sync_state==COMP_RECORDING_JOURNAL_WRITING&&snapshot->total_length)))return snapshot;
        return NULL;
    }
#ifndef COMPANION_RECORDING_SEGMENTED_ONLY
    const comp_recording_journal_entry_t *stored =
        comp_recording_journal_find(transfer->config.journal, id);
    if (finalized(stored)) return stored;
    if (stored != NULL && stored->sync_state == COMP_RECORDING_JOURNAL_WRITING &&
        transfer->config.live_entry != NULL &&
        transfer->config.live_entry(transfer->config.context, id, snapshot) &&
        snapshot->recording_id == id && snapshot->sync_state == COMP_RECORDING_JOURNAL_WRITING &&
        snapshot->payload_offset == stored->payload_offset &&
        snapshot->extent_offset == stored->extent_offset &&
        snapshot->reserved_bytes == stored->reserved_bytes &&
        snapshot->total_length != 0u) return snapshot;
    return NULL;
#else
    return NULL; /* Product V2 requires an explicit segmented storage port. */
#endif
}

static bool window_io_allowed(const comp_wba_recording_transfer_t *transfer)
{
    if (!transfer->snapshot_live) return heavy_io_allowed(transfer);
    return transfer->config.live_read_allowed != NULL &&
        transfer->config.live_read_allowed(transfer->config.context);
}

static bool entry_bounds_valid(
    const comp_recording_journal_t *journal,
    const comp_recording_journal_entry_t *entry)
{
    uint32_t payload_prefix;
    if (entry == NULL || (journal!=NULL&&
        (entry->payload_offset > journal->data_bytes ||
        entry->total_length > journal->data_bytes - entry->payload_offset))) {
        return false;
    }
    if (entry->reserved_bytes == 0u ||
        entry->payload_offset < entry->extent_offset ||
        (journal!=NULL&&(entry->extent_offset > journal->data_bytes ||
        entry->reserved_bytes > journal->data_bytes - entry->extent_offset))) {
        return false;
    }
    payload_prefix = entry->payload_offset - entry->extent_offset;
    return payload_prefix <= entry->reserved_bytes &&
           entry->total_length <= entry->reserved_bytes - payload_prefix;
}

static void reset_window(comp_wba_recording_transfer_t *transfer,
                         comp_wba_recording_transfer_state_t state)
{
    ++transfer->window_generation;
    transfer->notify_staged_bytes=0u;
    transfer->notify_staged_lane=0u;
    transfer->recording_id = 0u;
    transfer->next_offset = 0u;
    transfer->remaining = 0u;
    transfer->packet_sequence = 0u;
    transfer->host_resume_token = 0u;
    transfer->snapshot_length = 0u;
    transfer->snapshot_live = false;
    transfer->compact_stream = false;
    transfer->packet_length = 0u;
    transfer->packet_payload_length = 0u;
    transfer->packet_ready = false;
    transfer->state = state;
}

bool comp_wba_recording_transfer_init(
    comp_wba_recording_transfer_t *transfer,
    const comp_wba_recording_transfer_config_t *config)
{
    return comp_wba_recording_transfer_init_backend(transfer,config,NULL);
}

bool comp_wba_recording_transfer_init_backend(comp_wba_recording_transfer_t *transfer,
    const comp_wba_recording_transfer_config_t *config,const comp_wba_recording_transfer_backend_t *backend)
{
    if (transfer == NULL || config == NULL || config->notify == NULL ||
        (backend?(!backend->metadata||!backend->read||config->journal!=NULL):
#ifndef COMPANION_RECORDING_SEGMENTED_ONLY
        (config->journal == NULL || !config->journal->mounted ||
        config->journal->port.read == NULL || config->journal->port.crc32 == NULL)
#else
        true
#endif
        )) {
        return false;
    }
    memset(transfer, 0, sizeof(*transfer));
    transfer->config = *config;
    transfer->backend=backend;
    transfer->state = COMP_WBA_RECORDING_TRANSFER_IDLE;
    transfer->last_result = COMP_WBA_RECORDING_TRANSFER_OK;
    return true;
}

bool comp_wba_recording_transfer_set_value_capacity(comp_wba_recording_transfer_t *t,uint16_t bytes)
{
    if(!t||bytes<20u||bytes>COMP_WBA_RECORDING_TRANSFER_VALUE_BYTES)return false;
    uint16_t previous=t->value_capacity?t->value_capacity:COMP_WBA_RECORDING_TRANSFER_VALUE_BYTES;
    if(bytes!=previous&&(t->state==COMP_WBA_RECORDING_TRANSFER_ACTIVE||
       t->state==COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED))return false;
    t->value_capacity=bytes;return true;
}
void comp_wba_recording_transfer_set_connected(
    comp_wba_recording_transfer_t *transfer, bool connected)
{
    if (transfer == NULL) return;
    if (transfer->connected && !connected) {
        transfer->stats.disconnects++;
        reset_window(transfer, COMP_WBA_RECORDING_TRANSFER_IDLE);
    }
    transfer->connected = connected;
    if (!connected) transfer->last_result = COMP_WBA_RECORDING_TRANSFER_NOT_CONNECTED;
}

comp_wba_recording_transfer_result_t comp_wba_recording_transfer_start(
    comp_wba_recording_transfer_t *transfer,
    const companion_recording_adapter_request_t *request)
{
    const comp_recording_journal_entry_t *entry;
    comp_recording_journal_entry_t live;
    uint32_t requested;
    uint32_t available;

    if (transfer == NULL || request == NULL || request->schema_version != 1u ||
        (request->flags & COMP_WBA_RECORDING_TRANSFER_STREAM_ALL_FLAG) !=
            request->flags ||
        request->recording_id == 0u) {
        return COMP_WBA_RECORDING_TRANSFER_BAD_ARGUMENT;
    }
    reset_window(transfer, COMP_WBA_RECORDING_TRANSFER_IDLE);
    if (!transfer->connected) {
        transfer->last_result = COMP_WBA_RECORDING_TRANSFER_NOT_CONNECTED;
        return transfer->last_result;
    }
    if(transfer->value_capacity && transfer->value_capacity<=56u) {
        transfer->last_result=COMP_WBA_RECORDING_TRANSFER_BAD_STATE;
        return transfer->last_result;
    }
#ifndef COMPANION_RECORDING_SEGMENTED_ONLY
    entry = transfer->backend?readable_entry(transfer,request->recording_id,&live):
        comp_recording_journal_find(transfer->config.journal,request->recording_id);
#else
    entry = readable_entry(transfer,request->recording_id,&live);
#endif
    if (entry == NULL) {
        transfer->last_result = COMP_WBA_RECORDING_TRANSFER_NOT_FOUND;
        return transfer->last_result;
    }
    entry = readable_entry(transfer, request->recording_id, &live);
    if (entry == NULL) {
        transfer->last_result = COMP_WBA_RECORDING_TRANSFER_NOT_FINALIZED;
        return transfer->last_result;
    }
    if (finalized(entry) && !heavy_io_allowed(transfer)) {
        transfer->stats.busy_rejections++;
        transfer->last_result = COMP_WBA_RECORDING_TRANSFER_BUSY;
        return transfer->last_result;
    }
    if (!finalized(entry) && transfer->config.live_read_allowed == NULL) {
        transfer->last_result = COMP_WBA_RECORDING_TRANSFER_BUSY;
        return transfer->last_result;
    }
    if (!entry_bounds_valid(transfer->config.journal, entry)) {
        transfer->last_result = COMP_WBA_RECORDING_TRANSFER_BAD_STATE;
        return transfer->last_result;
    }
    if (request->byte_offset >= entry->total_length) {
        transfer->last_result = COMP_WBA_RECORDING_TRANSFER_OFFSET_OUT_OF_RANGE;
        return transfer->last_result;
    }
    available = entry->total_length - request->byte_offset;
    if ((request->flags & COMP_WBA_RECORDING_TRANSFER_STREAM_ALL_FLAG) != 0u) {
        requested = available;
    } else if (request->requested_length == 0u) {
        requested = COMP_WBA_RECORDING_TRANSFER_PAYLOAD_BYTES;
    } else {
        requested = request->requested_length;
    }
    if (requested > available) requested = available;

    transfer->recording_id = request->recording_id;
    transfer->next_offset = request->byte_offset;
    transfer->remaining = requested;
    transfer->packet_sequence = 0u;
    transfer->host_resume_token = request->host_resume_token;
    transfer->snapshot_length = entry->total_length;
    transfer->snapshot_live = !finalized(entry);
    transfer->compact_stream = !transfer->snapshot_live &&
        (request->flags & COMP_WBA_RECORDING_TRANSFER_STREAM_ALL_FLAG) != 0u;
    transfer->packet_ready = false;
    transfer->state = COMP_WBA_RECORDING_TRANSFER_ACTIVE;
    transfer->last_result = COMP_WBA_RECORDING_TRANSFER_OK;
    transfer->stats.starts++;
    return COMP_WBA_RECORDING_TRANSFER_OK;
}

static bool prepare_packet(comp_wba_recording_transfer_t *transfer)
{
    comp_recording_journal_entry_t live;
    const comp_recording_journal_entry_t *entry =
        readable_entry(transfer, transfer->recording_id, &live);
    uint8_t crc_fields[16];
    uint8_t *payload;
    uint32_t payload_length = transfer->remaining;
    uint32_t crc;
    uint32_t header_bytes;
    bool final_packet;

    if (entry == NULL || !entry_bounds_valid(transfer->config.journal, entry) ||
        entry->total_length < transfer->snapshot_length ||
        transfer->next_offset >= transfer->snapshot_length) {
        transfer->last_result = COMP_WBA_RECORDING_TRANSFER_BAD_STATE;
        transfer->state = COMP_WBA_RECORDING_TRANSFER_FAILED;
        return false;
    }
    uint32_t maximum = transfer->compact_stream ?
        COMP_WBA_RECORDING_TRANSFER_COMPACT_PAYLOAD_BYTES :
        COMP_WBA_RECORDING_TRANSFER_PAYLOAD_BYTES;
    uint32_t value_capacity=transfer->value_capacity?transfer->value_capacity:
        248u; /* unnegotiated/legacy callers retain their wire ceiling */
    uint32_t normal_header=transfer->compact_stream?20u:24u;
    if(value_capacity<=56u) {
        transfer->last_result=COMP_WBA_RECORDING_TRANSFER_BAD_STATE;
        transfer->state=COMP_WBA_RECORDING_TRANSFER_FAILED;return false;
    }
    if(transfer->compact_stream && value_capacity<=248u && maximum>224u)maximum=224u;
    if(maximum>value_capacity-normal_header)maximum=value_capacity-normal_header;
    if(transfer->compact_stream && transfer->compact_payload_limit &&
       transfer->compact_payload_limit<maximum)maximum=transfer->compact_payload_limit;
    if (payload_length > maximum) payload_length = maximum;
    if (payload_length > transfer->snapshot_length - transfer->next_offset) {
        payload_length = transfer->snapshot_length - transfer->next_offset;
    }
    /* A large last remainder needs an intermediate packet before the SHA
     * packet. Compute its layout before reading: never write past packet[]. */
    if (!transfer->snapshot_live &&
        transfer->next_offset + payload_length == transfer->snapshot_length &&
        payload_length > value_capacity-56u)
        payload_length = value_capacity-56u;
    final_packet = !transfer->snapshot_live &&
        transfer->next_offset + payload_length == transfer->snapshot_length;
    header_bytes = final_packet ? 56u : transfer->compact_stream ? 20u : 24u;
    memset(transfer->packet, 0, header_bytes);
    payload = transfer->packet + header_bytes;
    if (payload_length == 0u || payload_length > UINT16_MAX) {
        transfer->last_result=COMP_WBA_RECORDING_TRANSFER_BAD_STATE;
        transfer->state=COMP_WBA_RECORDING_TRANSFER_FAILED;return false;
    }
    comp_wba_transfer_read_result_t read_result;
    if(transfer->backend)read_result=transfer->backend->read(transfer->config.context,
        transfer->recording_id,transfer->next_offset,payload,payload_length);
#ifndef COMPANION_RECORDING_SEGMENTED_ONLY
    else read_result=transfer->config.journal->port.read(
            transfer->config.journal->port_context,
            entry->payload_offset + transfer->next_offset,
            payload, payload_length)?COMP_WBA_TRANSFER_READ_OK:COMP_WBA_TRANSFER_READ_ERROR;
#else
    else read_result=COMP_WBA_TRANSFER_READ_ERROR;
#endif
    if(read_result==COMP_WBA_TRANSFER_READ_WAIT)return false;
    if(read_result!=COMP_WBA_TRANSFER_READ_OK) {
        transfer->stats.storage_errors++;
        transfer->last_result = COMP_WBA_RECORDING_TRANSFER_STORAGE_IO;
        transfer->state = COMP_WBA_RECORDING_TRANSFER_FAILED;
        return false;
    }

    transfer->packet[0] = 1u;
    transfer->packet[1] = final_packet ? COMPANION_RECORDING_ADAPTER_FINAL_FLAG :
        transfer->compact_stream ? COMP_WBA_RECORDING_TRANSFER_COMPACT_FLAG : 0u;
    put_le16(&transfer->packet[2], (uint16_t)payload_length);
    put_le32(&transfer->packet[4], entry->recording_id);
    put_le32(&transfer->packet[8], transfer->packet_sequence);
    put_le32(&transfer->packet[12], transfer->next_offset);
    if (header_bytes != 20u) put_le32(&transfer->packet[16], transfer->snapshot_length);

    put_le32(&crc_fields[0], entry->recording_id);
    put_le32(&crc_fields[4], transfer->packet_sequence);
    put_le32(&crc_fields[8], transfer->next_offset);
    put_le32(&crc_fields[12], transfer->snapshot_length);
#ifndef COMPANION_RECORDING_SEGMENTED_ONLY
    crc = transfer->backend?comp_wba_recording_crc32(0u,crc_fields,sizeof(crc_fields)):
        transfer->config.journal->port.crc32(0u, crc_fields,
                                               sizeof(crc_fields));
    crc = transfer->backend?comp_wba_recording_crc32(crc,payload,payload_length):
        transfer->config.journal->port.crc32(crc, payload,
                                               payload_length);
#else
    crc = comp_wba_recording_crc32(0u,crc_fields,sizeof(crc_fields));
    crc = comp_wba_recording_crc32(crc,payload,payload_length);
#endif
    put_le32(&transfer->packet[header_bytes == 20u ? 16u : 20u], crc);
    if (final_packet) {
        memcpy(&transfer->packet[24], entry->sha256,
               COMP_RECORDING_JOURNAL_SHA256_BYTES);
    }
    /* Compact CRC uses the immutable sealed list total; live snapshots keep
     * the explicit total because the recording can grow after discovery. */
    transfer->packet_payload_length = (uint16_t)payload_length;
    transfer->packet_length = (uint16_t)(header_bytes + payload_length);
    transfer->notify_staged_bytes=0u;
    transfer->notify_staged_lane=0u;
    transfer->packet_ready = true;
    return true;
}

comp_wba_recording_transfer_state_t comp_wba_recording_transfer_poll(
    comp_wba_recording_transfer_t *transfer)
{
    uint32_t sent;
    if (transfer == NULL) return COMP_WBA_RECORDING_TRANSFER_FAILED;
    if (transfer->state != COMP_WBA_RECORDING_TRANSFER_ACTIVE &&
        transfer->state != COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED) {
        return transfer->state;
    }
    if (!transfer->connected) {
        reset_window(transfer, COMP_WBA_RECORDING_TRANSFER_IDLE);
        transfer->last_result = COMP_WBA_RECORDING_TRANSFER_NOT_CONNECTED;
        return transfer->state;
    }
    if (!window_io_allowed(transfer)) {
        transfer->stats.busy_rejections++;
        /* A live reader yields to capture/flush and resumes the same window.
         * No offset advances, no storage read and no cached notify escapes. */
        if (transfer->snapshot_live||transfer->backend) return transfer->state;
        reset_window(transfer, COMP_WBA_RECORDING_TRANSFER_IDLE);
        transfer->last_result = COMP_WBA_RECORDING_TRANSFER_BUSY;
        return transfer->state;
    }
    if (!transfer->packet_ready) {
        (void)prepare_packet(transfer);
        return transfer->state;
    }
    const uint32_t generation=transfer->window_generation;
    const bool accepted=transfer->config.notify(transfer->config.context,
        transfer->packet,transfer->packet_length);
    /* Nested radio dispatch can end this window while notify waits. Never
     * advance its stale packet, nor mark the new/cleared window pressured. */
    if(generation!=transfer->window_generation)return transfer->state;
    if (!accepted) {
        transfer->stats.notify_backpressure++;
        transfer->state = COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED;
        return transfer->state;
    }

    sent = transfer->packet_payload_length;
    transfer->stats.packets_notified++;
    transfer->stats.payload_bytes_notified += sent;
    transfer->next_offset += sent;
    transfer->remaining -= sent;
    transfer->packet_sequence++;
    transfer->packet_ready = false;
    transfer->packet_length = 0u;
    transfer->packet_payload_length = 0u;
    transfer->notify_staged_bytes=0u;
    transfer->notify_staged_lane=0u;
    if (transfer->remaining == 0u) {
        transfer->stats.completed_windows++;
        transfer->state = COMP_WBA_RECORDING_TRANSFER_COMPLETE;
    } else {
        transfer->state = COMP_WBA_RECORDING_TRANSFER_ACTIVE;
    }
    return transfer->state;
}

comp_wba_recording_transfer_state_t comp_wba_recording_transfer_poll_budget(
    comp_wba_recording_transfer_t *transfer,
    comp_wba_recording_transfer_clock_fn clock, void *clock_context,
    const comp_wba_recording_transfer_budget_t *budget)
{
    if (transfer == NULL) return COMP_WBA_RECORDING_TRANSFER_FAILED;
    const comp_wba_recording_transfer_budget_t normal = {4u, 8u, 2u};
    if (budget == NULL) budget = &normal;
    if (budget->max_packets == 0u || budget->max_steps == 0u ||
        budget->max_elapsed_ms == 0u) return transfer->state;
    const uint32_t started = clock != NULL ? clock(clock_context) : 0u;
    /* During capture, an explicitly timed one-packet slice can read and
     * publish the same packet without waiting for another foreground turn.
     * Every step still rechecks capture/storage ownership; if the first step
     * consumes the one-millisecond budget the packet remains prepared. */
    const bool live_pair = transfer->snapshot_live && clock != NULL &&
        budget->max_packets == 1u && budget->max_steps == 2u &&
        budget->max_elapsed_ms == 1u;
    const uint32_t packet_limit = transfer->snapshot_live ? 1u :
        (budget->max_packets < 7u ? budget->max_packets : 7u);
    const uint32_t step_limit = transfer->snapshot_live ? (live_pair ? 2u : 1u) :
        (budget->max_steps < 14u ? budget->max_steps : 14u);
    const uint32_t elapsed_limit = transfer->snapshot_live ? (live_pair ? 1u : 2u) :
        (budget->max_elapsed_ms < 4u ? budget->max_elapsed_ms : 4u);
    const uint32_t notified = transfer->stats.packets_notified;
    for (uint32_t step = 0u; step < step_limit; ++step) {
        if (step != 0u && clock != NULL && clock(clock_context) - started >= elapsed_limit) break;
        if (transfer->stats.packets_notified - notified >= packet_limit) break;
        const uint32_t offset = transfer->next_offset;
        const bool prepared = transfer->packet_ready;
        if (comp_wba_recording_transfer_poll(transfer) !=
                COMP_WBA_RECORDING_TRANSFER_ACTIVE) break;
        if (transfer->next_offset == offset && transfer->packet_ready == prepared) break;
    }
    return transfer->state;
}

comp_wba_recording_transfer_state_t comp_wba_recording_transfer_poll_bulk(
    comp_wba_recording_transfer_t *transfer,
    comp_wba_recording_transfer_clock_fn clock, void *clock_context)
{
    return comp_wba_recording_transfer_poll_budget(transfer, clock, clock_context, NULL);
}

void comp_wba_recording_transfer_cancel(
    comp_wba_recording_transfer_t *transfer)
{
    if (transfer == NULL) return;
    reset_window(transfer, COMP_WBA_RECORDING_TRANSFER_IDLE);
    transfer->last_result = COMP_WBA_RECORDING_TRANSFER_OK;
}

size_t comp_wba_recording_transfer_build_list(
    const comp_wba_recording_transfer_t *transfer,
    uint8_t *output, size_t output_capacity)
{
    uint32_t live_count;
    uint8_t count = 0u;
    size_t offset = COMP_WBA_RECORDING_TRANSFER_LIST_HEADER_BYTES;

    if (transfer == NULL || output == NULL || output_capacity < offset ||
        transfer->config.journal == NULL || !transfer->config.journal->mounted) {
        return 0u;
    }
    {
        const size_t maximum_list_bytes =
            COMP_WBA_RECORDING_TRANSFER_LIST_HEADER_BYTES +
            COMP_RECORDING_JOURNAL_MAX_ENTRIES *
                COMP_WBA_RECORDING_TRANSFER_LIST_ENTRY_BYTES;
        memset(output, 0, output_capacity < maximum_list_bytes
            ? output_capacity : maximum_list_bytes);
    }
    live_count = comp_recording_journal_count(transfer->config.journal);
    for (uint32_t i = 0u; i < live_count; ++i) {
        comp_recording_journal_entry_t live;
        const comp_recording_journal_entry_t *entry =
            comp_recording_journal_at(transfer->config.journal, i);
        uint8_t *wire;
        comp_rec_v1_entry_t descriptor;
        if (entry == NULL) continue;
        entry = readable_entry(transfer, entry->recording_id, &live);
        if (entry == NULL || !entry_bounds_valid(transfer->config.journal, entry)) continue;
        if (output_capacity - offset < COMP_WBA_RECORDING_TRANSFER_LIST_ENTRY_BYTES) {
            break;
        }
        wire = &output[offset];
        memset(&descriptor, 0, sizeof(descriptor));
        descriptor.recording_id = entry->recording_id;
        descriptor.started_unix_s = entry->started_unix_s;
        descriptor.duration_ms = entry->duration_ms;
        descriptor.codec = entry->codec;
        descriptor.sync_state = entry->sync_state == COMP_RECORDING_JOURNAL_WRITING
            ? COMP_WBA_RECORDING_WIRE_ACTIVE
            : entry->sync_state == COMP_RECORDING_JOURNAL_ACKED
                ? COMP_WBA_RECORDING_WIRE_TRANSFERRED : COMP_WBA_RECORDING_WIRE_UNSYNCED;
        descriptor.source_mode = entry->source_mode;
        descriptor.flags = (entry->reserved&COMP_RECORDING_RECOVERED_PREFIX)?1u:0u;
        descriptor.total_length = entry->total_length;
        memcpy(descriptor.sha256_prefix, entry->sha256, 8u);
        descriptor.content_crc32 = entry->content_crc32;
        if (!comp_rec_v1_encode(&descriptor, wire,
                COMP_WBA_RECORDING_TRANSFER_LIST_ENTRY_BYTES)) return 0u;
        offset += COMP_WBA_RECORDING_TRANSFER_LIST_ENTRY_BYTES;
        count++;
    }
    output[0] = 1u;
    output[1] = count;
    put_le16(&output[2], count == 0u ? 0u :
             COMP_WBA_RECORDING_TRANSFER_LIST_ENTRY_BYTES);
    return offset;
}

comp_wba_recording_transfer_result_t comp_wba_recording_transfer_acknowledge(
    comp_wba_recording_transfer_t *transfer,
    uint32_t recording_id,
    uint32_t validated_total_length,
    const uint8_t validated_sha256[COMP_RECORDING_JOURNAL_SHA256_BYTES])
{
    const comp_recording_journal_entry_t *entry;
    comp_recording_journal_result_t result;
    if (transfer == NULL || recording_id == 0u || validated_sha256 == NULL) {
        return COMP_WBA_RECORDING_TRANSFER_BAD_ARGUMENT;
    }
    /* A segmented peer must supply the complete V2 sealed proof to its
     * coordinator, never use this legacy length/SHA-only acknowledgement. */
    if(transfer->backend)return COMP_WBA_RECORDING_TRANSFER_BAD_STATE;
    if (!transfer->connected) {
        return COMP_WBA_RECORDING_TRANSFER_NOT_CONNECTED;
    }
    if (!heavy_io_allowed(transfer)) {
        transfer->stats.busy_rejections++;
        return COMP_WBA_RECORDING_TRANSFER_BUSY;
    }
    entry = comp_recording_journal_find(transfer->config.journal, recording_id);
    if (entry == NULL) return COMP_WBA_RECORDING_TRANSFER_NOT_FOUND;
    if (!finalized(entry)) return COMP_WBA_RECORDING_TRANSFER_NOT_FINALIZED;
    if (entry->total_length != validated_total_length ||
        memcmp(entry->sha256, validated_sha256,
               COMP_RECORDING_JOURNAL_SHA256_BYTES) != 0) {
        transfer->stats.ack_mismatches++;
        return COMP_WBA_RECORDING_TRANSFER_ACK_MISMATCH;
    }
    if (entry->sync_state == COMP_RECORDING_JOURNAL_ACKED) {
        return COMP_WBA_RECORDING_TRANSFER_OK;
    }
    result = comp_recording_journal_ack_complete(
        transfer->config.journal, recording_id, validated_total_length,
        validated_sha256);
    if (result != COMP_RECORDING_JOURNAL_OK) {
        return result == COMP_RECORDING_JOURNAL_ACK_MISMATCH
            ? COMP_WBA_RECORDING_TRANSFER_ACK_MISMATCH
            : COMP_WBA_RECORDING_TRANSFER_STORAGE_IO;
    }
    transfer->stats.acknowledgements++;
    return COMP_WBA_RECORDING_TRANSFER_OK;
}

void comp_wba_recording_transfer_get_stats(
    const comp_wba_recording_transfer_t *transfer,
    comp_wba_recording_transfer_stats_t *stats)
{
    if (transfer == NULL || stats == NULL) return;
    *stats = transfer->stats;
}
