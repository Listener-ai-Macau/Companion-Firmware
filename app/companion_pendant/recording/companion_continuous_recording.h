#ifndef COMPANION_CONTINUOUS_RECORDING_H
#define COMPANION_CONTINUOUS_RECORDING_H

#include "companion_segment_audio.h"
#include "companion_opus16_rt.h"
#include "companion_duration_stats.h"
#include "companion_recording_timeline.h"

#define COMP_CONT_PCM_BLOCK_SAMPLES 160u
#define COMP_CONT_PCM_SLOTS 8u
#define COMP_CONT_STAGE_BYTES 768u
#define COMP_CONT_TIMELINE_PAUSES 1u
#define COMP_CONT_TIMELINE_BOOKMARKS 2u
#define COMP_CONT_TIMELINE_SOURCE_BOUNDARY 3u
#define COMP_CONT_TIMELINE_AUDIO_PROFILE 4u
#define COMP_CONT_BOOKMARK_LIMIT COMP_REC_BOOKMARK_LIMIT
#if COMPANION_WBA_CE_SHARED_CAPTURE
/*248B logical page plus42B rollover packet remain disjoint. The physical
 *256B commit page is still separate; PCM ring depth and deadlines unchanged. */
#undef COMP_CONT_STAGE_BYTES
#define COMP_CONT_STAGE_BYTES 320u
#endif

typedef enum {
    COMP_CONT_UNBOUND=0,COMP_CONT_READY,COMP_CONT_RUNNING,COMP_CONT_STOPPING,
    COMP_CONT_SEALED,COMP_CONT_FAULT,COMP_CONT_CANCELING,COMP_CONT_CANCELED,
    COMP_CONT_PAUSE_PENDING,COMP_CONT_PAUSING,COMP_CONT_PAUSED,
    COMP_CONT_RESUMING,COMP_CONT_ENDING_PAUSE
} comp_cont_state_t;
typedef enum {
    COMP_CONT_STOP_NONE=0,COMP_CONT_STOP_USER,COMP_CONT_STOP_FULL,COMP_CONT_STOP_ERROR,
    COMP_CONT_STOP_LOW_BATTERY,COMP_CONT_STOP_LIMIT,COMP_CONT_STOP_SILENCE,
    COMP_CONT_STOP_PREPARE_DELAYED
} comp_cont_stop_t;
static inline uint8_t comp_cont_recording_end_reason(comp_cont_stop_t reason)
{
    return reason==COMP_CONT_STOP_USER?COMP_REC_END_USER:
        reason==COMP_CONT_STOP_FULL?COMP_REC_END_FULL:
        reason==COMP_CONT_STOP_LIMIT?COMP_REC_END_LIMIT:
        reason==COMP_CONT_STOP_LOW_BATTERY?COMP_REC_END_LOW_BATTERY:
        reason==COMP_CONT_STOP_SILENCE?COMP_REC_END_SILENCE:COMP_REC_END_UNKNOWN;
}

typedef struct {
    bool (*microphone)(void *,bool);
    uint32_t (*now_ms)(void *);
    /* Pure cached handoff, no backend I/O. OK supplies a completely preerased,
     * provenance-committed WRITING successor at the exact next sample/index.
     * take=true moves its ownership once. FULL is legal only if no successor
     * reservation is durable; PENDING retains any still-owned preparation. */
    comp_segment_result_t (*next)(void *,bool take,
        const comp_segment_entry_t **,comp_segment_audio_t **);
    /* Retain the supplied immutable entry until terminal completion. begin
     * starts an operation without I/O; each continuation performs <=1I/O.
     * Ports must yield on NOR arbitration instead of turning BUSY into error. */
    comp_segment_result_t (*seal)(void *,const comp_segment_entry_t *,bool begin);
    /* Zero accepted PCM only; the engine stops capture and releases its claim
     * before this verified-empty cancellation. Never an audio delete port. */
    comp_segment_result_t (*cancel)(void *,comp_segment_audio_t *,bool begin);
    /* Optional single cooperative allocation/reclaim step when PCM and audio
     * commits do not own this slice. It must never stop/reset the microphone. */
    comp_segment_result_t (*background)(void *);
    void *context;
    uint32_t segment_frames; /*20ms packets, policy; not a sample reset.*/
    uint16_t foreground_budget_ms;
    /* Explicit opt-in after the product/peer supports COP1 schema2. Legacy
     * production callers remain schema1 until their control/UI integration. */
    uint8_t pause_timeline; /*0 schema1,1 schema2,2 schema3,3 schema4,4 schema5*/
    /* Schema5 only: pure immutable session snapshot, no I/O. Each segment
     * repeats it; a changed CRC faults before emitting a successor header. */
    bool (*audio_profile)(void *,comp_rec_audio_profile_t *);
    /* Optional nonblocking admission immediately before each real codec frame,
     * including PAUSE/STOP drain and the final padding frame. false yields
     * without consuming PCM or changing the codec/timeline. The port owns its
     * bounded wait/urgent-capture policy; half-frame staging never calls it. */
    bool (*encode_window)(void *,bool microphone_active,uint8_t queued_pcm);
} comp_cont_config_t;

typedef struct {
    uint32_t accepted_pcm_blocks,encoded_packets,durable_bytes,sealed_segments;
    uint32_t microphone_starts,microphone_stops,overflows,storage_full_stops;
    uint32_t max_poll_ms,max_ring_depth,budget_failures;
    comp_duration_stats_t encoding_duration;
} comp_cont_stats_t;

/* Replaces, rather than duplicates, a production capture buffer at binding.
 * No dynamic allocation, duplicate encoder or per-segment PCM buffer. */
typedef struct {
    comp_cont_config_t config;
    comp_cont_stats_t stats;
    companion_opus16_rt_t codec;
    companion_sha256_t sha;
    comp_segment_entry_t active,closing;
    comp_segment_audio_t writer;
    int16_t pcm[COMP_CONT_PCM_SLOTS][COMP_CONT_PCM_BLOCK_SAMPLES];
    uint8_t stage[COMP_CONT_STAGE_BYTES+COMP_SEGMENT_PAGE_BYTES];
    uint32_t active_first_frame,active_frame_limit,content_crc,token;
    uint32_t audio_profile_crc;
    uint64_t elapsed_ms,transition_ms;
    uint64_t bookmark_sample,bookmark_ms;
    uint32_t clock_ms,command_sequence,active_non_audio_bytes;
    uint32_t bookmark_sequence,bookmark_request;
    uint16_t stage_length,roll_packet_bytes;
    uint8_t ring_read,ring_write,ring_count;
    comp_cont_state_t state;
    comp_cont_stop_t stop_reason;
    comp_segment_result_t failure;
    bool microphone_active,encoder_owned;
    union {bool flush_complete;bool transition_recorded;};
    uint8_t command_kind;
    uint8_t bookmark_phase;
    bool closing_pending,closing_started,closing_last;
    uint8_t source_end_phase; /*former tail padding:0 prelude,1 durable end*/
} comp_cont_recording_t;

/* Caller must own and have readback-qualified the initial prepared writer.
 * Source UID/epoch/session comes from the durable allocator, never uptime.
 * The prepared extent is handed off before the same encoder is initialized. */
/* A queued10ms half with an empty20ms codec input only stages samples.
 * Keep it serviceable outside the long-encode phase window. Housekeeping that
 * could take precedence is excluded; this hint never mutates capture state. */
static inline bool comp_cont_recording_pcm_staging_pending(const comp_cont_recording_t *r)
{
    return r && (r->state==COMP_CONT_RUNNING || r->state==COMP_CONT_PAUSE_PENDING ||
                 r->state==COMP_CONT_PAUSING) && r->ring_count &&
        r->encoder_owned && r->codec.ready && r->codec.frame_samples==320u && r->codec.pcm_fill==0u &&
        !r->writer.phase && !r->roll_packet_bytes && !r->bookmark_phase &&
        r->stage_length<=COMP_CONT_STAGE_BYTES-(COMPANION_OPUS16_MAX_PACKET+2u);
}

/* Only copy one accepted10ms half into the empty20ms codec accumulator.
 * No generic poll/next/stop/roll/seal/background callback and no Opus frame.
 * Same FIFO, elapsed clock and hard budget; next half uses ordinary polling. */
bool comp_cont_recording_stage_pcm_half(comp_cont_recording_t *);
bool comp_cont_recording_init(comp_cont_recording_t *,const comp_cont_config_t *,
    const comp_segment_entry_t *,comp_segment_audio_t *,uint32_t token);
bool comp_cont_recording_start(comp_cont_recording_t *,uint32_t token);
bool comp_cont_recording_stop(comp_cont_recording_t *,uint32_t token);
bool comp_cont_recording_stop_reason(comp_cont_recording_t *,uint32_t token,comp_cont_stop_t);
/* Stop capture now while the already-started resume event finishes committing. */
bool comp_cont_recording_quiesce_resume(comp_cont_recording_t *,uint32_t token,comp_cont_stop_t);
/* Sequence is strictly increasing within this START token; exact duplicate
 * requests are idempotent and delayed older commands cannot toggle capture.
 * PAUSE_PENDING accepts at most the next20ms boundary, then shuts capture
 * down and drains accepted real PCM. PAUSED means its page-backed event and
 * accepted audio are durable. Resume keeps the encoder/session/sample axis.
 * Poll these transitions; an intermediate state is not a completed pause. */
bool comp_cont_recording_pause(comp_cont_recording_t *,uint32_t token,uint32_t sequence);
bool comp_cont_recording_resume(comp_cont_recording_t *,uint32_t token,uint32_t sequence);
/* Queue one device-local mark without stopping capture. request is a nonzero
 * monotonic UI/service nonce within this token (signed modulo32 comparison).
 * true means accepted/idempotent, NOT durable; query result before success UI.
 * Audio location rounds down to its20ms source boundary; wall time is kept.
 * Marks have their own1..1024 sequence, never a CMC3 control sequence. */
bool comp_cont_recording_bookmark(comp_cont_recording_t *,uint32_t token,uint32_t request);
comp_segment_result_t comp_cont_recording_bookmark_result(const comp_cont_recording_t *,uint32_t token,uint32_t request);
/* Used only with RUNNING/PAUSED stable tails: omit timeline/padding bytes
 * when calculating committed audio frames from the current extent. */
uint32_t comp_cont_recording_non_audio_bytes(const comp_cont_recording_t *);
/* Foreground only,16kHz/160 samples. BLE lifetime is deliberately absent. */
bool comp_cont_recording_pcm(comp_cont_recording_t *,const int16_t *,size_t);
comp_cont_state_t comp_cont_recording_poll(comp_cont_recording_t *);
/* Captured failure is explicit, not a normal STOP. Reservations stay owned. */
void comp_cont_recording_fault(comp_cont_recording_t *,comp_segment_result_t);

#endif
