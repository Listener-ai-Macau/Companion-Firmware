#ifndef WBA_SEGMENT_DISCARD_WORKER_H
#define WBA_SEGMENT_DISCARD_WORKER_H
#include "wba_segment_discard_preview.h"
/* The caller exclusively owns catalog, recording, transfer and OTA until
 * terminal completion. Recovery runs before admitting new work. */
typedef comp_segment_result_t (*comp_discard_poll_fn)(void *,comp_segment_catalog_t *);
typedef struct {
    comp_segment_catalog_t *catalog;comp_discard_entry_fn read;comp_discard_poll_fn poll;void *context;
    /* Only the intent fields needed to verify identity and scope survive. */
    struct {uint8_t uid[12],sha256[32];uint64_t epoch,session;comp_segment_discard_intent_t intent;
        uint32_t recording_id;} anchor;
    comp_segment_entry_t entry;uint32_t generation;uint8_t anchor_slot,slot,phase;
    comp_segment_result_t result;
} comp_discard_worker_t;
comp_segment_result_t comp_discard_worker_resume(comp_discard_worker_t *,comp_segment_catalog_t *,
    comp_discard_entry_fn,comp_discard_poll_fn,void *,uint8_t,const comp_segment_entry_t *,const comp_segment_discard_intent_t *);
comp_segment_result_t comp_discard_worker_poll(comp_discard_worker_t *);
#endif
