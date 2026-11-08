#ifndef COMPANION_RANGE_RECEIPT_H
#define COMPANION_RANGE_RECEIPT_H

#include "companion_segment_catalog.h"

/* A compact journal page shares the existing CSG2 metadata banks. It does
 * not reserve payload sectors or create additional catalog entries. A32B
 * committed page header binds all six32B records to this UID/epoch/bank/
 * page. Intent and physical completion have separate verified commit words.
 * This format module issues no erase and is not a host-consume permission.
 * The production worker must validate durable local range SHA proof first. */
#define COMP_RANGE_JOURNAL_HEADER_BYTES 32u
#define COMP_RANGE_JOURNAL_RECORD_BYTES 32u
#define COMP_RANGE_JOURNAL_RECORDS 6u
#define COMP_RANGE_JOURNAL_DONE_OFFSET 24u
#define COMP_RANGE_JOURNAL_COMMIT_OFFSET 28u

typedef enum {
    COMP_RANGE_EMPTY=0,COMP_RANGE_TORN,COMP_RANGE_INVALID,
    COMP_RANGE_PENDING,COMP_RANGE_DONE
} comp_range_journal_state_t;

typedef struct {
    uint32_t recording_id,request_nonce,descriptor_binding;
    uint16_t first_sector,end_sector;
    uint8_t slot;
} comp_range_plan_t;

/* A sealed entry's immutable catalogue identity reconstructs the CSP2 page
 * binding; after a committed range intent, sector0 can be reclaimed too.
 * Returned encoded offsets cover exactly the data in the requested whole
 * physical sectors; bytes outside actual audio never enter speed metrics. */
bool comp_range_plan(const comp_segment_entry_t *,uint8_t slot,
    uint16_t first_sector,uint16_t end_sector,uint32_t request_nonce,
    comp_range_plan_t *,uint32_t *encoded_begin,uint32_t *encoded_end);
bool comp_range_plan_matches(const comp_range_plan_t *,const comp_segment_entry_t *,uint8_t slot);

void comp_range_journal_header_prepare(uint8_t header[32],const uint8_t uid[12],
    uint64_t epoch,uint32_t bank_serial,uint32_t page_index);
void comp_range_journal_snapshot_header_prepare(uint8_t header[32],const uint8_t uid[12],
    uint64_t epoch,uint32_t bank_serial,uint32_t page_index);
bool comp_range_journal_is_snapshot(const uint8_t header[32]);
comp_range_journal_state_t comp_range_journal_header_decode(const uint8_t header[32],
    const uint8_t uid[12],uint64_t epoch,uint32_t bank_serial,uint32_t page_index);

/* prepare leaves both words FF. Verify body, program+verify COMMIT=0 BEFORE
 * erasing. After real erase completion, program+verify DONE=0 BEFORE reply.
 * A torn DONE remains pending and may be idempotently completed on reboot.
 * A torn/uncommitted intent never authorizes an erase. */
bool comp_range_journal_record_prepare(uint8_t record[32],const uint8_t header[32],
    uint8_t index,const comp_range_plan_t *);
comp_range_journal_state_t comp_range_journal_record_decode(const uint8_t record[32],
    const uint8_t header[32],uint8_t index,comp_range_plan_t *);

#endif
