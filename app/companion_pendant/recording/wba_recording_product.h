#ifndef COMPANION_WBA_RECORDING_PRODUCT_H
#define COMPANION_WBA_RECORDING_PRODUCT_H
#include "wba_recording_pipeline.h"
#include "wba_recording_recovery.h"
#include "wba_recording_service.h" /* Existing diagnostic/state codes only. */

/* A generation-qualified, cooperative view. Physical segments and logical
 * recordings are separate counts. No array of64 descriptors or heap. */
typedef struct {
    uint64_t session;
    uint32_t generation,arena_bytes,encoded_bytes,reserved_bytes,consumed_bytes;
    uint32_t highest_end,largest_gap,largest_gap_offset,cursor,nearest_start,nearest_end;
    uint8_t used,unsynced,writing,consumed,logical; /* each <=64 catalog slots */
    uint8_t phase,scan,look;
    uint8_t allocatable_segments; /* Whole independent extents in all free gaps. */
    bool valid,allocation_uncertain,microphone_owned; /* no optimistic count for overlapping owners */
    bool microphone_sealed_owned; /* a real original still requires durable sync before OTA */
} comp_wba_recording_space_t;

/* This is the actual product capture owner. Recovery and the live engine
 * have disjoint lifetimes and share RAM. It replaces the V1 journal/service,
 * rather than keeping a second encoder or audio buffer alongside them. */
typedef struct {
    union {comp_cont_recording_t engine;comp_wba_recording_recovery_t recovery;} capture;
    comp_segment_catalog_t catalog;
    comp_wba_recording_pipeline_t pipeline;
    comp_wba_segment_storage_t storage;
    /* The old-catalog blank proof is boot-only. Its cursors retire before
     * the generation-qualified capacity scan starts, so share that RAM. */
    union {
        comp_wba_recording_space_t space;
        struct {uint32_t legacy_catalog,boot_cursor;} boot;
    };
    comp_wba_recording_report_fn_t report;
    uint8_t boot_phase,last_fault,reported_state;
    bool media_ready,ready,reported_active,retained_tail;
    struct {uint32_t generation;uint8_t phase;} blank_warm;
} comp_wba_recording_product_t;

/* Optional read-only idle preparation. No owner/allocation/erase/format change.
 * Callers revoke permission before user control, update or other storage work. */
void comp_wba_recording_product_warm_blank(comp_wba_recording_product_t *,bool allowed);

/* The caller first mounts CSI1 and obtains its durable random epoch. Blank
 * V2 banks may be formatted only after the entire old V1 catalog is blank.
 * A development installer can explicitly clear that old catalog; boot never
 * silently deletes existing/foreign/uncertain ownership or an OTA root. */
bool comp_wba_recording_product_bind(comp_wba_recording_product_t *,
    companion_spi_nor_stm32wba_t *,uint32_t bank_a,uint32_t bank_b,
    uint32_t data_base,uint32_t data_bytes,uint32_t legacy_catalog,
    const uint8_t uid[12],uint64_t epoch,const comp_wba_pipeline_config_t *,
    comp_wba_recording_report_fn_t);
void comp_wba_recording_product_poll(comp_wba_recording_product_t *);
/* Pending inactive storage work should return to the complete product poll,
 * with IRQs/radio/inputs serviced between bounded slices. Erase waits and
 * active/paused/draining audio retain their normal idle policy. */
bool comp_wba_recording_product_foreground_pending(const comp_wba_recording_product_t *);
/* Operational capture gate; a retained tail alone does not grant OTA space. */
bool comp_wba_recording_product_capture_available(const comp_wba_recording_product_t *);
bool comp_wba_recording_product_capture_prepare_available(const comp_wba_recording_product_t *);
bool comp_wba_recording_product_salvaging(const comp_wba_recording_product_t *);
/* Observation survives a temporary remount; it is not an access gate. */
bool comp_wba_recording_product_tail_retained(const comp_wba_recording_product_t *);
bool comp_wba_recording_product_update_available(const comp_wba_recording_product_t *);
static inline bool comp_wba_recording_product_pcm_staging_pending(const comp_wba_recording_product_t *p)
{
    return comp_wba_recording_product_capture_available(p)&&p->pipeline.engine_bound&&
        p->pipeline.state==COMP_PIPE_RECORDING&&!p->pipeline.stop_requested&&
        comp_cont_recording_pcm_staging_pending(&p->capture.engine);
}
bool comp_wba_recording_product_stage_pcm_half(comp_wba_recording_product_t *);
/* Explicit retry after a stopped capture fault. The caller first retires all
 * external radio/update/playback owners. This checks internal ownership before
 * lending the dead engine's RAM to bounded CSP2 recovery. No microphone start,
 * new session ID, erase of unconsumed audio, or implicit boot-lease replay. */
bool comp_wba_recording_product_recover_begin(comp_wba_recording_product_t *);
/* The caller must defer every other NOR mutation until this is false. */
bool comp_wba_recording_product_recovering(const comp_wba_recording_product_t *);
/* Caller must establish the same whole-NOR external exclusion as runtime
 * recovery. Only failed initial read-only mount or qualified idle capacity
 * reads may be retried; no active write, erase or workspace is retired. */
bool comp_wba_recording_product_boot_retry(comp_wba_recording_product_t *,uint32_t now_ms);
bool comp_wba_recording_product_idle_retry_exhausted(const comp_wba_recording_product_t *);
/* User START may re-arm only the exhausted, read-only idle retry. The caller
 * must provide the same whole-NOR and audio exclusion as boot_retry. */
bool comp_wba_recording_product_retry_idle_explicit(comp_wba_recording_product_t *,uint32_t now_ms);
bool comp_wba_recording_product_boot_retry_pending(const comp_wba_recording_product_t *);
bool comp_wba_recording_product_boot_retry_owned(const comp_wba_recording_product_t *);
/* Called once after WUS2 is mounted, its active tail lease restored and the
 * update allocator has accepted the exact physical boundary. */
void comp_wba_recording_product_lease_result(comp_wba_recording_product_t *,bool);
bool comp_wba_recording_product_prepare(comp_wba_recording_product_t *,
    uint64_t session,uint8_t mode,uint32_t started_unix_s,uint32_t token);
bool comp_wba_recording_product_prepare_timeline(comp_wba_recording_product_t *,
    uint64_t session,uint8_t mode,uint32_t started_unix_s,uint32_t token,bool timeline);
/* Current schema3 capture. Requires a matching TypeR44+ receiver; old stored
 * schema1/2 remain recoverable. No second encoder or storage partition. */
bool comp_wba_recording_product_prepare_bookmarked(comp_wba_recording_product_t *,
    uint64_t session,uint8_t mode,uint32_t started_unix_s,uint32_t token);
/* Explicit schema5 producer. Caller must provide an immutable pure profile
 * callback, use profile-aware geometry, and qualify matching receivers before
 * choosing this format. Existing entry points keep schema1..4 unchanged. */
bool comp_wba_recording_product_prepare_audio_profile(comp_wba_recording_product_t *,
    uint64_t session,uint8_t mode,uint32_t started_unix_s,uint32_t token);
bool comp_wba_recording_product_bookmark(comp_wba_recording_product_t *,uint32_t token,uint32_t request);
comp_segment_result_t comp_wba_recording_product_bookmark_result(const comp_wba_recording_product_t *,uint32_t token,uint32_t request);
bool comp_wba_recording_product_ready(const comp_wba_recording_product_t *,uint32_t token);
/* Physical short press: share the original engine and monotonic sequence. */
bool comp_wba_recording_product_pause_resume(comp_wba_recording_product_t *,uint32_t token);
/* Explicit wired service command is idempotent; a retry cannot toggle back. */
bool comp_wba_recording_product_set_paused(comp_wba_recording_product_t *,uint32_t token,bool paused);
bool comp_wba_recording_product_control(comp_wba_recording_product_t *,bool start,uint32_t token);
bool comp_wba_recording_product_stop_reason(comp_wba_recording_product_t *,uint32_t token,comp_cont_stop_t);
bool comp_wba_recording_product_pcm(comp_wba_recording_product_t *,const int16_t *,size_t,uint32_t rate);
void comp_wba_recording_product_fault(comp_wba_recording_product_t *,uint8_t reason);
uint8_t comp_wba_recording_product_state(const comp_wba_recording_product_t *);
/* Snapshot is current only after its bounded scan completes. OTA allocation
 * never does an unbounded directory walk inside a bool write callback. */
/* Extent inventory freshness is independent of our own tail lease size.
 * Capacity displays and recording budgets still require space_current(). */
bool comp_wba_recording_product_catalog_current(const comp_wba_recording_product_t *);
bool comp_wba_recording_product_space_current(const comp_wba_recording_product_t *);
/* Mounted/reconciled originals can remain readable after a completed recovery
 * scan found an unresolved tail. It does not grant a new OTA workspace; the
 * ordinary exact consume path owns sealed originals. */
bool comp_wba_recording_product_readable(const comp_wba_recording_product_t *);
bool comp_wba_recording_product_workspace(comp_wba_recording_product_t *,uint32_t bytes,uint32_t *physical);
bool comp_wba_recording_product_update_workspace(comp_wba_recording_product_t *,uint32_t bytes,uint32_t *physical);
bool comp_wba_recording_product_capability(const comp_wba_recording_product_t *,uint8_t out[32]);
#endif
