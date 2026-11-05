#ifndef COMPANION_SEGMENT_RESERVE_H
#define COMPANION_SEGMENT_RESERVE_H
#include "companion_segment_catalog.h"

/* One future capture extent, prepared ahead of the current segment. The
 * caller supplies the descriptor storage and keeps it alive until sealing or
 * explicit recovery. No payload/descriptor array or separate permanent region. */
typedef struct {
    comp_segment_catalog_t *catalog;
    comp_segment_entry_t *entry;
    uint32_t bytes, hint, candidate, cursor, generation;
    uint8_t scan, phase, read_retries;
    bool wrapped, align_to_gap;
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
