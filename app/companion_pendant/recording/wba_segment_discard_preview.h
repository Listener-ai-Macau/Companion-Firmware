#ifndef WBA_SEGMENT_DISCARD_PREVIEW_H
#define WBA_SEGMENT_DISCARD_PREVIEW_H
#include "companion_segment_catalog.h"

/* Read callback follows the storage adapter: PENDING retries the same slot. */
typedef comp_segment_result_t (*comp_discard_entry_fn)(void *,comp_segment_catalog_t *,uint8_t,comp_segment_entry_t *,comp_segment_discard_intent_t *);
typedef struct {
    comp_segment_catalog_t *catalog;comp_discard_entry_fn read;void *context;
    uint64_t epoch,session_id,sample_count,slots;
    uint32_t generation,oldest_id,max_id,started_unix_s,encoded_bytes,reserved_bytes,segments,last_index,max_index;
    uint8_t uid[12],slot,anchor_slot,phase;bool last_seen;comp_segment_result_t result;
} comp_discard_preview_t;
/* Preview is read-only. It does not authorize any deletion. Caller must hold
 * recording/OTA ownership stable and check this generation again on confirm. */
comp_segment_result_t comp_discard_preview_begin(comp_discard_preview_t *,comp_segment_catalog_t *,comp_discard_entry_fn,void *);
comp_segment_result_t comp_discard_preview_poll(comp_discard_preview_t *);
#endif
