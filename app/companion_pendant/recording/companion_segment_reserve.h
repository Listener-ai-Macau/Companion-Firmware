#ifndef COMPANION_SEGMENT_RESERVE_H
#define COMPANION_SEGMENT_RESERVE_H
#include "companion_segment_catalog.h"

/* One future capture extent, prepared ahead of the current segment. The
 * caller supplies the descriptor storage and keeps it alive until sealing or
 * explicit recovery. No payload/descriptor array or separate permanent region. */
typedef struct {
    comp_segment_catalog_t *catalog;
    comp_segment_entry_t *entry;
    uint32_t bytes;
    /* SEARCH fields are dead after the durable reservation commits. Reuse
     * their storage for the bounded dirty-run/verification cursors. */
    union {uint32_t hint,run_start,verify_end;};
    uint32_t candidate,cursor;
    union {uint32_t generation,resume_cursor;};
    union {uint32_t gap_end,erase_end;};
    uint8_t scan, phase, read_retries;
    bool wrapped, align_to_gap;
    uint8_t preparation; /* 0 durable owner; 1 exclusive unbound idle preparation; 2 verified handoff */
} comp_segment_reserve_t;

/* template contains a session/index/sample_offset/codec/source/UID/epoch;
 * recording_id=0 lets this allocator assign the catalog's next durable ID.
 * Every occupied state, including ACKED/ERASING/WRITING, protects its full
 * extent until a completed catalog removal. No automatic unsynced eviction.
 * hint is a sector-aligned offset within the catalog's dynamic payload arena. */
comp_segment_result_t comp_segment_reserve_begin(comp_segment_reserve_t *,
    comp_segment_catalog_t *,comp_segment_entry_t *template_entry,
    uint32_t bytes,uint32_t hint);

/* At most one backend I/O per poll: incremental gap search -> durable WRITING
 * reservation -> cooperative physical erase -> full blank readback -> READY.
 * Healthy pending never advances the erase cursor or authorizes PCM writes.
 * A failure retains the persisted reservation for recovery. The port must
 * arbitrate NOR suspension before bool reads/programs when audio has priority.
 * The catalog is shared; its unrelated mutation can invalidate/restart a scan,
 * but it cannot be mutated while this worker owns a catalog transaction. */
/* For a new session, rotate through the arena using the durable next ID.
 * Align within the containing free gap so a reservation does not strand
 * full-sized free slots on both sides. No extra persistent cursor writes. */
comp_segment_result_t comp_segment_reserve_begin_rotated(comp_segment_reserve_t *,
    comp_segment_catalog_t *,comp_segment_entry_t *,uint32_t bytes);
/* A search hint only: all occupied entries/generation checks still run.
 * Allowed before the first search step, never for a persisted owner. */
comp_segment_result_t comp_segment_reserve_set_search_hint(comp_segment_reserve_t *,uint32_t);

/* An exclusive idle coordinator may prepare a fully searched FREE extent
 * before a session exists. It must exclude every allocator/workspace writer
 * through handoff or cancellation. No catalog row/recording ID is fabricated.
 * Only a complete blank proof can be bound to a real session; catalog commit
 * still validates the exact physical ownership before exposing a writer. */
comp_segment_result_t comp_segment_reserve_bind_prepared(comp_segment_reserve_t *);

/* Cancel this live, not-yet-taken allocator. The adapter must first settle
 * its exact in-flight physical erase (without starting another chunk) and
 * arbitrate catalog I/O. No full erase/blank/provenance work is started.
 * Failed/uncertain workers stay owned; boot recovery cannot use this API. */
comp_segment_result_t comp_segment_reserve_cancel_poll(comp_segment_reserve_t *);

comp_segment_result_t comp_segment_reserve_poll(comp_segment_reserve_t *);
/* Optional read-only callback for bounded single-page access. PENDING must
 * leave the destination and reservation cursor uncommitted. Writes/erases and
 * catalog transactions keep their original port and ownership. */
comp_segment_result_t comp_segment_reserve_poll_scoped(comp_segment_reserve_t *,
    comp_segment_catalog_scoped_read_fn,void *);
/* Same pure arbitration preview as the shared catalog. */
comp_segment_result_t comp_segment_reserve_next_io(const comp_segment_reserve_t *,comp_segment_io_t *);
bool comp_segment_reserve_ready(const comp_segment_reserve_t *);
/* Transfer a READY extent to capture without deleting its durable reservation;
 * the worker becomes free for preparing the following segment. Failed work
 * cannot be forgotten through this API and requires explicit recovery. */
bool comp_segment_reserve_take(comp_segment_reserve_t *,comp_segment_entry_t **);
#endif
