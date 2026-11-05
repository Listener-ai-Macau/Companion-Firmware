#ifndef COMPANION_WBA_RECORDING_TRANSFER_H
#define COMPANION_WBA_RECORDING_TRANSFER_H

#include "companion_recording_gatt_adapter.h"
#include "companion_recording_journal.h"
#include "wba_segment_discard_control.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Negotiated value ceiling509, compact audio489 and FINAL/SHA audio453.
 * Zero/legacy handshake retains244/224. Large values may cross physical248B
 * NOR pages; neither persistent recording format nor live total_length changes. */
#define COMP_WBA_RECORDING_TRANSFER_VALUE_BYTES 509u
#define COMP_WBA_RECORDING_TRANSFER_PAYLOAD_BYTES \
    (COMP_WBA_RECORDING_TRANSFER_VALUE_BYTES - \
     (uint32_t)sizeof(companion_recording_adapter_header_t))
#define COMP_WBA_RECORDING_TRANSFER_COMPACT_PAYLOAD_BYTES 489u
#define COMP_WBA_RECORDING_TRANSFER_COMPACT_FLAG 0x08u
#define COMP_WBA_RECORDING_TRANSFER_STREAM_ALL_FLAG 0x04u
#define COMP_WBA_RECORDING_TRANSFER_LIST_HEADER_BYTES 4u
#define COMP_WBA_RECORDING_TRANSFER_LIST_ENTRY_BYTES 32u
/* V1 wire states are deliberately distinct from the on-flash journal enum. */
#define COMP_WBA_RECORDING_WIRE_UNSYNCED 0u
#define COMP_WBA_RECORDING_WIRE_ACTIVE 1u
#define COMP_WBA_RECORDING_WIRE_TRANSFERRED 2u

typedef enum {
    COMP_WBA_RECORDING_TRANSFER_OK = 0,
    COMP_WBA_RECORDING_TRANSFER_BAD_ARGUMENT,
    COMP_WBA_RECORDING_TRANSFER_NOT_CONNECTED,
    COMP_WBA_RECORDING_TRANSFER_BUSY,
    COMP_WBA_RECORDING_TRANSFER_NOT_FOUND,
    COMP_WBA_RECORDING_TRANSFER_NOT_FINALIZED,
    COMP_WBA_RECORDING_TRANSFER_OFFSET_OUT_OF_RANGE,
    COMP_WBA_RECORDING_TRANSFER_STORAGE_IO,
    COMP_WBA_RECORDING_TRANSFER_ACK_MISMATCH,
    COMP_WBA_RECORDING_TRANSFER_BAD_STATE,
} comp_wba_recording_transfer_result_t;

typedef enum {
    COMP_WBA_RECORDING_TRANSFER_IDLE = 0,
    COMP_WBA_RECORDING_TRANSFER_ACTIVE,
    COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED,
    COMP_WBA_RECORDING_TRANSFER_COMPLETE,
    COMP_WBA_RECORDING_TRANSFER_FAILED,
} comp_wba_recording_transfer_state_t;

/* Return true only after the characteristic value was accepted by the BLE
 * stack. A false result is transport backpressure and is retried byte-for-byte
 * on a later poll. */
typedef bool (*comp_wba_recording_transfer_notify_fn)(
    void *context, const uint8_t *value, uint16_t value_length);

/* This policy hook must return false while recording prepare, capture, drain,
 * or finalize owns the NOR/foreground budget. */
typedef bool (*comp_wba_recording_transfer_heavy_io_allowed_fn)(void *context);
typedef bool (*comp_wba_recording_transfer_live_entry_fn)(
    void *context, uint32_t recording_id, comp_recording_journal_entry_t *entry);
typedef bool (*comp_wba_recording_transfer_read_allowed_fn)(void *context);

typedef struct {
    comp_recording_journal_t *journal;
    comp_wba_recording_transfer_notify_fn notify;
    comp_wba_recording_transfer_heavy_io_allowed_fn heavy_io_allowed;
    void *context;
    comp_wba_recording_transfer_live_entry_fn live_entry;
    comp_wba_recording_transfer_read_allowed_fn live_read_allowed;
} comp_wba_recording_transfer_config_t;

/* Optional storage port for the segmented recorder. The metadata lookup is
 * pure/cached and must validate the backing extent before supplying a sealed
 * entry. READ_WAIT performs no accepted packet advance and is not an IO fault;
 * the same destination/window is retried. The legacy journal port is unchanged.
 * This reuses the existing packet buffer, CRC framing and bounded radio queue. */
typedef enum {COMP_WBA_TRANSFER_READ_OK=0,COMP_WBA_TRANSFER_READ_WAIT,COMP_WBA_TRANSFER_READ_ERROR}
    comp_wba_transfer_read_result_t;
typedef struct {
    bool (*metadata)(void *,uint32_t,comp_recording_journal_entry_t *);
    comp_wba_transfer_read_result_t (*read)(void *,uint32_t,uint32_t,uint8_t *,uint32_t);
} comp_wba_recording_transfer_backend_t;

typedef struct {
    uint32_t starts;
    uint32_t completed_windows;
    uint32_t disconnects;
    uint32_t busy_rejections;
    uint32_t notify_backpressure;
    uint32_t storage_errors;
    uint32_t packets_notified;
    uint32_t payload_bytes_notified;
    uint32_t acknowledgements;
    uint32_t ack_mismatches;
} comp_wba_recording_transfer_stats_t;

/* Public for static allocation. All calls are foreground/task calls and must
 * be serialized with journal mutations by the product owner. */
typedef struct {
    comp_wba_recording_transfer_config_t config;
    const comp_wba_recording_transfer_backend_t *backend; /* NULL: existing V1 journal */
    comp_wba_recording_transfer_stats_t stats;
    /* Packet transfer and explicitly confirmed discard are exclusive.
     * A separate response stays valid even while control state is live. */
    union {
        uint8_t packet[COMP_WBA_RECORDING_TRANSFER_VALUE_BYTES];
        struct {comp_discard_control_t owner;uint8_t response[96];} discard_workspace;
    };
    uint32_t recording_id;
    uint32_t next_offset;
    uint32_t remaining;
    uint32_t packet_sequence;
    uint32_t host_resume_token;
    uint32_t snapshot_length;
    /* Foreground owner supplies negotiated compact capacity;0 uses value cap.
     * Only new compact packets use it; cached retries and live stay intact. */
    uint16_t compact_payload_limit;
    /* Negotiated application value limit. Zero retains legacy248B value;
     * unlike DLE compact_payload_limit this also bounds FINAL/SHA and live. */
    uint16_t value_capacity;
    uint16_t packet_length;
    uint16_t packet_payload_length;
    /* Transport-local long-value progress, owned by this immutable packet.
     * It is not an acknowledged audio/file byte offset. */
    uint16_t notify_staged_bytes;
    uint8_t notify_staged_lane;
    comp_wba_recording_transfer_state_t state;
    comp_wba_recording_transfer_result_t last_result;
    uint32_t window_generation;
    bool connected;
    bool packet_ready;
    bool snapshot_live;
    bool compact_stream;
} comp_wba_recording_transfer_t;
#if UINTPTR_MAX == UINT32_MAX
_Static_assert(sizeof(((comp_wba_recording_transfer_t *)0)->discard_workspace)<=
    COMP_WBA_RECORDING_TRANSFER_VALUE_BYTES,"discard workspace exceeds packet buffer");
#endif

bool comp_wba_recording_transfer_init(
    comp_wba_recording_transfer_t *transfer,
    const comp_wba_recording_transfer_config_t *config);
bool comp_wba_recording_transfer_init_backend(comp_wba_recording_transfer_t *,
    const comp_wba_recording_transfer_config_t *,const comp_wba_recording_transfer_backend_t *);
/* Between windows only. A cached or partially assembled packet must retain
 * its original layout until canceled/finished; no mid-window resize/retry. */
bool comp_wba_recording_transfer_set_value_capacity(comp_wba_recording_transfer_t *,uint16_t);

/* Disconnect discards only the transient window. The durable journal and ACK
 * state remain unchanged. Reconnect requires a new host pull at its last
 * verified byte offset. */
void comp_wba_recording_transfer_set_connected(
    comp_wba_recording_transfer_t *transfer, bool connected);

comp_wba_recording_transfer_result_t comp_wba_recording_transfer_start(
    comp_wba_recording_transfer_t *transfer,
    const companion_recording_adapter_request_t *request);

/* Performs at most one storage read or one notify attempt. */
comp_wba_recording_transfer_state_t comp_wba_recording_transfer_poll(
    comp_wba_recording_transfer_t *transfer);

/* Stopped recordings fill the radio queue in bounded batches (at most four
 * packets or 2ms). Live capture keeps exactly one existing foreground step.
 * Backpressure preserves the same packet/offset; no spinning on a full queue.
 * A NULL clock is for portable callers and retains the fixed step bound. */
typedef uint32_t (*comp_wba_recording_transfer_clock_fn)(void *context);
typedef struct {
    uint8_t max_packets;
    uint8_t max_steps;
    uint8_t max_elapsed_ms;
} comp_wba_recording_transfer_budget_t;

/* The foreground owner supplies its IO budget. Any zero field pauses the
 * window without preparing/advancing a packet. Stopped work is capped at
 * seven packets, fourteen IO steps and 4ms; live capture always retains one
 * step and the existing ownership gate, regardless of the requested budget.
 * The elapsed bound is checked between indivisible port calls. */
comp_wba_recording_transfer_state_t comp_wba_recording_transfer_poll_budget(
    comp_wba_recording_transfer_t *transfer,
    comp_wba_recording_transfer_clock_fn clock, void *clock_context,
    const comp_wba_recording_transfer_budget_t *budget);
comp_wba_recording_transfer_state_t comp_wba_recording_transfer_poll_bulk(
    comp_wba_recording_transfer_t *transfer,
    comp_wba_recording_transfer_clock_fn clock, void *clock_context);

void comp_wba_recording_transfer_cancel(
    comp_wba_recording_transfer_t *transfer);

/* Builds the existing recording_list wire value. WRITING entries are visible
 * only through an explicitly bound live owner, with committed-prefix length.
 * Journal UNSYNCED/ACKED map to wire 0/2, live prefix maps to wire 1. */
size_t comp_wba_recording_transfer_build_list(
    const comp_wba_recording_transfer_t *transfer,
    uint8_t *output, size_t output_capacity);

/* ACK is deliberately separate from transfer completion. It persists ACKED
 * only after exact length+SHA validation and never erases payload bytes. */
comp_wba_recording_transfer_result_t comp_wba_recording_transfer_acknowledge(
    comp_wba_recording_transfer_t *transfer,
    uint32_t recording_id,
    uint32_t validated_total_length,
    const uint8_t validated_sha256[COMP_RECORDING_JOURNAL_SHA256_BYTES]);

void comp_wba_recording_transfer_get_stats(
    const comp_wba_recording_transfer_t *transfer,
    comp_wba_recording_transfer_stats_t *stats);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_WBA_RECORDING_TRANSFER_H */
