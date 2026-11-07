#ifndef COMPANION_WBA_SEGMENT_DIRECTORY_H
#define COMPANION_WBA_SEGMENT_DIRECTORY_H
#include "wba_segment_storage.h"

/* GATT-facing V2 page request: schema2/command20/reserved00, snapshot u32 at4
 * (zero only to start at0), request nonce at8, logical cursor at12, all LE.
 * Request byte2 bit0 opts into a4B LE started_unix_s sidecar per descriptor;
 * FW66703+ bit1 requests consecutive bounded pages for this one nonce.
 * byte3 stays zero. Legacy replies keep112B rows, calendar rows are116B.
 * The underlying112B descriptors, raw audio and consume proofs do not change.
 * Do not advertise this capability until the full production binding exists. */
#define COMP_SEG_DIRECTORY_REQUEST_BYTES 16u
#define COMP_SEG_DIRECTORY_COMMAND 0x20u
typedef struct {
    comp_segment_catalog_t *catalog;
    comp_wba_segment_storage_t *storage;
    uint8_t *output; /* caller-owned existing248B GATT value buffer */
    uint32_t snapshot,nonce,start,total;
    uint16_t capacity,bytes;
    uint8_t scan,count,target;
    comp_segment_result_t result;
    bool active;
    uint8_t options;
} comp_wba_segment_directory_t;

comp_segment_result_t comp_wba_segment_directory_begin(comp_wba_segment_directory_t *,
    comp_wba_segment_storage_t *,comp_segment_catalog_t *,const uint8_t request[16],
    uint8_t *,uint16_t capacity);
/* At most one descriptor read/arbitration slice. Pending buffers are never
 * publishable. A changing generation fails with0 reply bytes; the caller
 * sends a correlated error/restarts the snapshot, never mixes old/new pages. */
comp_segment_result_t comp_wba_segment_directory_poll(comp_wba_segment_directory_t *);
/* Advance only AFTER the previous page notification was accepted. No I/O;
 * the next poll checks the same generation and reads at most one entry. */
bool comp_wba_segment_directory_next(comp_wba_segment_directory_t *);
void comp_wba_segment_directory_cancel(comp_wba_segment_directory_t *);
#endif
