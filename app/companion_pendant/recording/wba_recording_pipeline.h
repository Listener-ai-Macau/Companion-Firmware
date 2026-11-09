#ifndef COMPANION_WBA_RECORDING_PIPELINE_H
#define COMPANION_WBA_RECORDING_PIPELINE_H
#include "companion_segment_catalog.h"
#include "companion_continuous_recording.h"
#include "wba_segment_storage.h"
#include "companion_range_reclaim.h"

/* One cooperative producer/directory/consumer owner. Capture buffers live in
 * the supplied engine, not in this coordinator. BLE handles do not appear in
 * the capture lifetime. The caller allocates ONE CSI1 logical-session ID
 * before begin and uses the same UID/epoch as the mounted catalog. */
typedef struct {
    comp_cont_recording_t *recording;
    comp_segment_catalog_t *catalog;
    comp_wba_segment_storage_t *storage;
    bool (*microphone)(void *,bool);
    uint32_t (*now_ms)(void *);
    void *context;
    uint32_t segment_frames,extent_bytes;
    bool (*audio_profile)(void *,comp_rec_audio_profile_t *);
    bool (*capacity_snapshot)(const void *,uint32_t *,uint8_t *);
} comp_wba_pipeline_config_t;

typedef enum {COMP_PIPE_IDLE=0,COMP_PIPE_PREPARING,COMP_PIPE_READY,COMP_PIPE_RECORDING,
    COMP_PIPE_STOPPING,COMP_PIPE_CLEANUP,COMP_PIPE_FINISHED,COMP_PIPE_FAILED} comp_wba_pipeline_state_t;

typedef struct {
    comp_wba_pipeline_config_t config;
    union {comp_segment_reserve_t reserve;comp_range_reclaim_t range_worker;};
    comp_segment_entry_t future,consume;
    comp_segment_audio_t future_writer;
    const comp_segment_entry_t *sealing;
    uint32_t token;
    union {uint32_t full_generation;uint32_t fault_stop_due_ms;}; /* exclusive FAILED/normal states */
    uint32_t consumed_segments;
    uint32_t workspace_bytes,workspace_requested,workspace_generation,workspace_offset;
    comp_segment_result_t failure,consume_result;
    comp_wba_pipeline_state_t state;
    uint8_t future_phase,consume_phase,consume_scan;
    uint8_t workspace_scan;
    bool seal_started,core_cancel_started;
    bool discard_exclusive; /* confirmed discard owns NOR across poll gaps */
    uint8_t stop_requested; /*0 none; otherwise queued comp_cont_stop_t, same byte*/
    bool engine_bound;
    uint8_t pause_timeline; /*same one-byte field; COMP_CONT_TIMELINE_* */
    uint8_t fault_stop_attempts; /* bounded microphone-stop retry in FAILED */
    uint8_t range_operation; /*0 status,1 durable range reclaim; idle producer union*/
#if COMPANION_WBA_RECLAIM_TIMING
    uint32_t consume_timing_ms[5]; /* accepted, exact owner found, ACK durable, reclaim begin, removal durable */
#endif
} comp_wba_recording_pipeline_t;

bool comp_wba_recording_pipeline_init(comp_wba_recording_pipeline_t *,const comp_wba_pipeline_config_t *);
/* Optional idle work, with the same full-sized allocator and existing scratch.
 * allowed=false settles only an issued erase, then drops the unbound proof.
 * No session/recording ID exists until an explicit begin. */
bool comp_wba_recording_pipeline_primed(const comp_wba_recording_pipeline_t *);
comp_segment_result_t comp_wba_recording_pipeline_prime(comp_wba_recording_pipeline_t *,bool allowed);
comp_segment_result_t comp_wba_recording_pipeline_begin(comp_wba_recording_pipeline_t *,
    uint64_t session_id,uint8_t source_mode,uint32_t started_unix_s,uint32_t token);
/* Explicit per-session format opt-in. Legacy begin remains schema1. Product
 * control must confirm receiver capability before selecting the new format. */
comp_segment_result_t comp_wba_recording_pipeline_begin_timeline(comp_wba_recording_pipeline_t *,
    uint64_t session_id,uint8_t source_mode,uint32_t started_unix_s,uint32_t token,bool timeline);
bool comp_wba_recording_pipeline_start(comp_wba_recording_pipeline_t *,uint32_t token);
bool comp_wba_recording_pipeline_pause(comp_wba_recording_pipeline_t *,uint32_t token,uint32_t sequence);
bool comp_wba_recording_pipeline_resume(comp_wba_recording_pipeline_t *,uint32_t token,uint32_t sequence);
bool comp_wba_recording_pipeline_stop(comp_wba_recording_pipeline_t *,uint32_t token);
bool comp_wba_recording_pipeline_stop_reason(comp_wba_recording_pipeline_t *,uint32_t token,comp_cont_stop_t);
comp_wba_pipeline_state_t comp_wba_recording_pipeline_poll(comp_wba_recording_pipeline_t *);
/* A validated sealed proof from a durable receiver, one at a time. Physical
 * offsets/start time are loaded from NOR, never trusted from the peer. Exact
 * match -> durable ACKED -> physical erase -> durable removal -> OK receipt.
 * Invalid peer proof is rejected independently and does not stop capture. */
comp_segment_result_t comp_wba_recording_pipeline_consume(comp_wba_recording_pipeline_t *,
    const comp_rec_v2_descriptor_t *proof);
comp_segment_result_t comp_wba_recording_pipeline_consume_result(const comp_wba_recording_pipeline_t *);
/* Only a directory/receipt read failure before a consume write, while idle. */
bool comp_wba_recording_pipeline_consume_idle_read_failed(const comp_wba_recording_pipeline_t *);
/* Existing Type durable receiver's84B CRA2 command. Authenticate/negotiate V2
 * before calling. UID/epoch/session/index/ID/length/fullSHA are matched to the
 * locally validated sealed entry (or exact durable completed-removal proof).
 * Physical range, flags/sample axis/CRC are loaded from NOR, not the peer.
 * Receipt becomes available ONLY after durable physical removal, or an exact
 * replay of its retained proof. No new84B buffer lives in this coordinator. */
comp_segment_result_t comp_wba_recording_pipeline_consume_wire(comp_wba_recording_pipeline_t *,const uint8_t wire[84]);
/* Internal lookup hint only. Physical row identity/state/proof are re-read;
 * an empty or unrelated slot falls back to the complete search. */
comp_segment_result_t comp_wba_recording_pipeline_consume_wire_hint(comp_wba_recording_pipeline_t *,const uint8_t wire[84],uint8_t slot);
comp_segment_result_t comp_wba_recording_pipeline_range_wire(comp_wba_recording_pipeline_t *,const uint8_t wire[96],uint8_t slot);
bool comp_wba_recording_pipeline_range_reply(const comp_wba_recording_pipeline_t *,uint8_t wire[60]);
void comp_wba_recording_pipeline_range_reply_retired(comp_wba_recording_pipeline_t *);
bool comp_wba_recording_pipeline_receipt(const comp_wba_recording_pipeline_t *,uint8_t wire[84]);
bool comp_wba_recording_pipeline_storage_busy(const comp_wba_recording_pipeline_t *);
/* Called only after BLE/OTA/transfer owners are known idle. A failed or
 * uncertain discard retains ownership until explicit storage recovery. */
bool comp_wba_recording_pipeline_discard_acquire(comp_wba_recording_pipeline_t *);
bool comp_wba_recording_pipeline_discard_release(comp_wba_recording_pipeline_t *);
/* After reporting an empty pre-START capacity rejection, release only the
 * unallocated idle coordinator. All nonempty/unknown faults stay exclusive. */
bool comp_wba_recording_pipeline_release_empty_full(comp_wba_recording_pipeline_t *);
/* Pure shared-scratch ownership gate for the radio reader. The catalog page
 * must remain unchanged across provenance/cancellation/metadata commits. */
bool comp_wba_recording_pipeline_page_available(const comp_wba_recording_pipeline_t *);
/* Transfer-only page lease during this pipeline's own physical reclaim. */
bool comp_wba_recording_pipeline_transfer_page_available(const comp_wba_recording_pipeline_t *);
/* Tail space is borrowed on demand from the SAME dynamic payload pool. Scan
 * every owned state, including WRITING/ACKED/ERASING, without deleting data or
 * changing catalog geometry. One occupied entry read per continuation.
 * OTA must durably persist/restore this lease via its existing update root
 * before writing/enabling capture after restart, and release only when done.
 * zero releases an unused/completed lease; no automatic unconfirmed loss. */
comp_segment_result_t comp_wba_recording_pipeline_workspace(comp_wba_recording_pipeline_t *,
    uint32_t bytes,uint32_t *physical);
/* A complete product ownership scan, qualified by this exact generation.
 * Pure cached claim with the same exclusivity rules; stale snapshots refuse. */
comp_segment_result_t comp_wba_recording_pipeline_workspace_snapshot(comp_wba_recording_pipeline_t *,
    uint32_t bytes,uint32_t generation,uint32_t highest_owned_end,uint32_t *physical);
/* The product's completed gap walk proves this range free in this generation.
 * Capture/consume stay excluded until the exact claim is released. */
comp_segment_result_t comp_wba_recording_pipeline_workspace_at_snapshot(comp_wba_recording_pipeline_t *,
    uint32_t bytes,uint32_t generation,uint32_t offset,uint32_t *physical);
#endif
