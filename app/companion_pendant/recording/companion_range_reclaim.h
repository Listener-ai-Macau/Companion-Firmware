#ifndef COMPANION_RANGE_RECLAIM_H
#define COMPANION_RANGE_RECLAIM_H

#include "companion_range_receipt.h"
#include "companion_segment_audio.h"

/* Transaction core for the range-reclaim refactor. The catalogue owner must
 * exclusively retain the sealed extent AND its committed CRR3 journal page
 * through the entire operation. A range receipt never frees a catalogue slot,
 * changes the original SHA/length, or proves the whole recording complete.
 * Not yet advertised by the product: catalogue GC/rebase and host persistence
 * must be integrated before enabling destructive partial reclamation. */
typedef struct {
    comp_segment_port_t port;
    const comp_segment_entry_t *entry;
    comp_range_plan_t plan;
    companion_sha256_t sha;
    uint8_t *scratch; /* stable256B caller-owned page */
    uint32_t data_base,journal_address,bank_serial,page_index;
    uint32_t encoded_begin,encoded_end,hash_cursor,erase_cursor,verify_end;
    uint8_t expected_sha[32],header[32],record[32];
    uint8_t phase,record_index;
    comp_segment_result_t result;
} comp_range_reclaim_t;

/* Pure begin: the exact range SHA is supplied ONLY after the receiver has
 * synced the original bytes and their discoverable recovery index. The device
 * independently hashes CRC/identity-checked CSP2 pages before committing an
 * erase intent. journal_address identifies an already committed CRR3 page;
 * this core neither allocates/initializes it nor authorizes catalogue GC. */
comp_segment_result_t comp_range_reclaim_begin(comp_range_reclaim_t *,
    const comp_segment_port_t *,const comp_segment_entry_t *,uint32_t data_base,
    uint32_t journal_address,uint32_t bank_serial,uint32_t page_index,
    uint8_t record_index,const comp_range_plan_t *,const uint8_t durable_sha[32],
    uint8_t scratch[256]);

/* Same one-backend-I/O-per-poll contract as the catalogue. Preview permits the
 * platform to suspend/arbitrate NOR BEFORE invoking bool read/program ports.
 * Pending physical erase never advances the cursor; a persisted pending intent
 * can restart at its first sector after power loss. OK requires real erase,
 * complete blank readback AND a readback-verified durable DONE word. */
comp_segment_result_t comp_range_reclaim_next_io(const comp_range_reclaim_t *,comp_segment_io_t *);
comp_segment_result_t comp_range_reclaim_poll(comp_range_reclaim_t *);

#endif
