#ifndef COMPANION_SEGMENT_CATALOG_H
#define COMPANION_SEGMENT_CATALOG_H

#include "companion_recording_wire.h"

/* Persistent WBA segmented directory. Not a larger RAM copy of the V1 list.
 * Two 24 KiB metadata banks fit inside the existing dynamic metadata arena.
 * No payload extent, resource root, identity allocator or OTA root moves. */
#define COMP_SEGMENT_CAPACITY 64u
#define COMP_SEGMENT_PAGE_BYTES 256u
#define COMP_SEGMENT_PAGE_DATA_BYTES (COMP_SEGMENT_PAGE_BYTES-8u)
#define COMP_SEGMENT_BANK_BYTES 24576u
#define COMP_SEGMENT_BANK_PAGES 96u
#define COMP_SEGMENT_SECTOR_BYTES 4096u
#define COMP_SEGMENT_RECEIPT_CAPACITY 4u

typedef enum {
    COMP_SEG_WRITING=1, COMP_SEG_UNSYNCED=2, COMP_SEG_ACKED=3, COMP_SEG_ERASING=4,
    COMP_SEG_CANCELED=5, /* durable tombstone for physically verified empty reserve */
    COMP_SEG_DISCARDING=6, COMP_SEG_DISCARDED=7, /* confirmed loss, never an ACK */
    COMP_SEG_SESSION_DISCARD=8 /* durable whole-session intent, still owns anchor */
} comp_segment_state_t;
typedef enum {
    COMP_SEG_OK=0, COMP_SEG_PENDING, COMP_SEG_UNFORMATTED, COMP_SEG_BAD_ARGUMENT,
    COMP_SEG_BAD_STATE, COMP_SEG_IO_ERROR, COMP_SEG_CORRUPT,
    COMP_SEG_FULL, COMP_SEG_STALE_SNAPSHOT, COMP_SEG_NOT_FOUND,
    /* Internal writer port result: a fast read payload failed after the
     * command completed and CS was released. Never a durable acknowledgement. */
    COMP_SEG_RETRYABLE_READ
} comp_segment_result_t;

typedef enum { COMP_SEG_IO_NONE=0,COMP_SEG_IO_READ,COMP_SEG_IO_PROGRAM,COMP_SEG_IO_ERASE } comp_segment_io_kind_t;
typedef struct {uint32_t address,bytes;comp_segment_io_kind_t kind;} comp_segment_io_t;

typedef struct {
    comp_rec_v2_descriptor_t descriptor;
    uint32_t extent_offset, reserved_bytes, started_unix_s;
    uint8_t state;
    /* CSG2 rowv2:0 uses the current extent_offset. Nonzero carries the original
     * CSP2 relative extent+1 when resource growth/shrink rebases the directory.
     * Reads/erases still use data_base+extent_offset, NEVER this historical hint.
     * This keeps original audio/provenance bytes and SHA unchanged across OTA. */
    uint32_t provenance_extent_plus1;
    /* Transient CRR3 frontier; zero nonce means no partial physical reclamation.
     * Physical ownership remains the FULL extent until final consumption. */
    uint32_t range_nonce;
    uint16_t range_first,range_end;
} comp_segment_entry_t;
/* Only the exclusive confirmed-discard transaction owns this sidecar. */
typedef struct {uint64_t slots;uint32_t max_id;} comp_segment_discard_intent_t;
static inline uint32_t comp_segment_provenance_extent(const comp_segment_entry_t *e)
{return e->provenance_extent_plus1?e->provenance_extent_plus1-1u:e->extent_offset;}
/* Pure OTA migration of one already validated LIVE catalog entry. Preserve
 * the exact physical audio extent and original CSP2 binding. Refuse growth
 * front collisions or overlap with the OTA tail; no implicit loss/moving audio.
 * Chained migrations retain the first provenance offset. No NOR mutation. */
bool comp_segment_catalog_rebase_entry(const comp_segment_entry_t *,uint32_t old_data_base,
    uint32_t new_data_base,uint32_t protected_tail_base,comp_segment_entry_t *);

typedef struct {
    bool (*read)(void *,uint32_t,uint8_t *,uint32_t);
    /* One aligned-page slice only. Callback must honor its foreground budget. */
    bool (*program)(void *,uint32_t,const uint8_t *,uint32_t);
    /* Healthy pending returns true/zero. Only completed, sector-aligned bytes
     * advance a cursor. This is the same cooperative erase contract as V1. */
    bool (*erase_step)(void *,uint32_t,uint32_t,uint32_t *);
    void *context;
} comp_segment_port_t;

typedef struct {
    comp_segment_port_t port;
    /* Caller retains this immutable entry until poll returns a terminal result.
     * No duplicated descriptor arrays or hidden heap allocation. */
    const comp_segment_entry_t *pending;
    const comp_segment_discard_intent_t *pending_intent;
    uint64_t epoch, visible_mask;
    uint32_t banks[2], data_base, data_bytes, generation, bank_serial, next_id;
    uint32_t cursor, expected_crc;
    uint8_t uid[12], slots[COMP_SEGMENT_CAPACITY];
    /* Recent completed removals use the SAME metadata log, no payload space.
     * Preserve four exact proofs across reboot/GC for a lost final reply. */
    uint8_t receipts[COMP_SEGMENT_RECEIPT_CAPACITY],receipt_next;
    /* Shared read/program scratch, including GC. It is never a whole catalog. */
    uint8_t page[COMP_SEGMENT_PAGE_BYTES];
    uint8_t bank, phase, operation, index, scan, next_slot, target_slot, copy_slot;
    uint8_t snapshot_count, pending_state, root_valid_mask, root_blank_mask, invalid_root_mask;
    bool mounted, blank_verified, retire_authorized;
    bool legacy_dirty,gc_has_v3; /* committed rows newer than resident readers */
    /* Optional platform policy, in existing tail padding. 0 keeps4K sectors;
     * 8 means SFDP-qualified32K normal-prefix coalescing, never more ownership. */
    uint8_t reclaim_block_sectors;
    /* Compact range receipts occupy pages in these SAME metadata banks.
     * GC folds it into compact CRR3 snapshot pages, leaving CSG2 rows and their
     * generation sequence readable by the resident Boot; no payload partition. */
    uint32_t range_nonce[COMP_SEGMENT_CAPACITY];
    uint32_t range_id[COMP_SEGMENT_CAPACITY],range_binding[COMP_SEGMENT_CAPACITY];
    uint16_t range_first[COMP_SEGMENT_CAPACITY],range_end[COMP_SEGMENT_CAPACITY];
    struct comp_range_reclaim_s *range_worker;
    uint8_t range_page,range_record,range_pending_slot,range_pending_page,range_pending_record;
    bool range_snapshot_open;
} comp_segment_catalog_t;

/* Exact sealed range, original identity and durable local range SHA. One
 * exclusive mutation owner; physical reads of untouched transfer tail may
 * continue through the normal NOR arbitration port. Pending replay survives
 * power loss and never authorizes another ID or frees the whole extent. */
comp_segment_result_t comp_segment_catalog_range_begin(comp_segment_catalog_t *,
    struct comp_range_reclaim_s *,const comp_segment_entry_t *,uint8_t slot,
    uint16_t first_sector,uint16_t end_sector,uint32_t nonce,const uint8_t sha[32]);
bool comp_segment_catalog_range_pending(const comp_segment_catalog_t *);

/* Mount and every mutation are cooperative. Each poll issues at most one
 * read/program/erase callback. No metadata erase or full directory scan occurs
 * inside a sampling interrupt. Mount never formats invalid or foreign media. */
comp_segment_result_t comp_segment_catalog_mount_begin(comp_segment_catalog_t *,
    const comp_segment_port_t *,uint32_t bank_a,uint32_t bank_b,
    uint32_t data_base,uint32_t data_bytes,const uint8_t uid[12],uint64_t epoch);
comp_segment_result_t comp_segment_catalog_poll(comp_segment_catalog_t *);
/* Same mount state machine, with no writable/GC states reachable. Resident
 * Boot uses this entry so the linker can discard recorder mutation machinery.
 * CRC/UID/history/overlap checks and mounted results remain identical. */
comp_segment_result_t comp_segment_catalog_mount_poll(comp_segment_catalog_t *);
/* Pure preview of the next single poll. An adapter can suspend an unrelated
 * NOR erase and yield BEFORE entering a bool storage callback. No index,
 * commit, scan cursor or phase advances while that arbitration is pending. */
comp_segment_result_t comp_segment_catalog_next_io(const comp_segment_catalog_t *,comp_segment_io_t *);
comp_segment_result_t comp_segment_catalog_entry_io(const comp_segment_catalog_t *,uint8_t,comp_segment_io_t *);
/* A sealed transfer may read committed metadata during another entry's
 * physical reclaim. Row writes/GC/discard still defer; NOR overlap is gated. */
bool comp_segment_catalog_transfer_readable(const comp_segment_catalog_t *);
comp_segment_result_t comp_segment_catalog_transfer_entry_io(const comp_segment_catalog_t *,uint8_t,comp_segment_io_t *);
comp_segment_result_t comp_segment_catalog_receipt_io(const comp_segment_catalog_t *,uint8_t,comp_segment_io_t *);
/* Only after mount proved both entire banks blank; deliberately explicit. */
comp_segment_result_t comp_segment_catalog_format_blank_begin(comp_segment_catalog_t *);

/* WRITING is a reservation, not a public sealed segment. Callers preerase it
 * before programming audio. IDs are monotonic within the durable epoch.
 * Sealing keeps the same logical session/index/sample offset and full extent. */
comp_segment_result_t comp_segment_catalog_put_begin(comp_segment_catalog_t *,
    const comp_segment_entry_t *);
/* ACKED requires the exact sealed identity/length/CRC/SHA. The receiver must
 * already have durably saved raw data AND its discoverable index. */
comp_segment_result_t comp_segment_catalog_ack_begin(comp_segment_catalog_t *,
    const comp_segment_entry_t *validated);
/* ACKED -> durable ERASING -> physical erase -> durable removal. Resuming an
 * ERASING entry starts at its first sector. No delete receipt before removal.
 * This API cannot delete UNSYNCED data or a growing WRITING tail. */
comp_segment_result_t comp_segment_catalog_reclaim_begin(comp_segment_catalog_t *,
    const comp_segment_entry_t *);
/* Internal consume owner already resolved this logical slot. Re-read and
 * validate its exact immutable identity/proof/state under the catalog lock;
 * unrelated extents cannot change during these state-only transactions.
 * No PUT/delete shortcut, physical layout or receipt semantics change. */
comp_segment_result_t comp_segment_catalog_ack_at_begin(comp_segment_catalog_t *,
    const comp_segment_entry_t *,uint8_t slot);
comp_segment_result_t comp_segment_catalog_reclaim_at_begin(comp_segment_catalog_t *,
    const comp_segment_entry_t *,uint8_t slot);
/* Persist a confirmed whole-session intent before erasing any member. The
 * caller verifies the immutable session preview and exclusive owner first. */
comp_segment_result_t comp_segment_catalog_session_discard_begin(comp_segment_catalog_t *,
    const comp_segment_entry_t *,const comp_segment_discard_intent_t *,uint32_t expected_generation);
/* Internal only: higher layer must first present and confirm this exact sealed
 * identity and generation. Resume a durable DISCARDING intent after restart.
 * This does not authorize a remote request or claim a durable upload. */
comp_segment_result_t comp_segment_catalog_discard_begin(comp_segment_catalog_t *,
    const comp_segment_entry_t *,uint32_t expected_generation);
/* Rewrite only live legacy-compatible entries into a fresh committed bank.
 * Reject pending discard intents; preserves receipts and does not erase data. */
comp_segment_result_t comp_segment_catalog_compact_legacy_begin(comp_segment_catalog_t *);
/* Internal producer handoff only: verified empty audio, or a fresh live
 * allocator/writer that never offered audio and has retired its exact I/O.
 * Boot recovery still proves all empty pages. Never a remote WRITING delete. */
comp_segment_result_t comp_segment_catalog_cancel_unwritten_begin(comp_segment_catalog_t *,
    const comp_segment_entry_t *);

/* Exact slot reads are bounded; no seven-entry ATT list limit. A free slot is
 * NOT_FOUND. Wire paging omits WRITING/ERASING and rejects changed snapshots.
 * read/page APIs require an idle catalog; physical NOR suspension/arbitration
 * remains the adapter's responsibility, not an optimistic read while erasing. */
comp_segment_result_t comp_segment_catalog_read(comp_segment_catalog_t *,
    uint8_t index,comp_segment_entry_t *);
/* A read-only transfer may yield after a positively released transient read.
 * The callback must return PENDING only if no mutation or ownership is uncertain.
 * Real I/O faults and corrupt metadata still invalidate the catalog. */
typedef comp_segment_result_t (*comp_segment_catalog_scoped_read_fn)(void *,uint32_t,uint8_t *,uint32_t);
comp_segment_result_t comp_segment_catalog_read_scoped(comp_segment_catalog_t *,
    uint8_t,comp_segment_entry_t *,comp_segment_catalog_scoped_read_fn,void *);
/* Extract only a validated committed intent; other entries yield zero. */
comp_segment_result_t comp_segment_catalog_read_intent(comp_segment_catalog_t *,
    uint8_t index,comp_segment_entry_t *,comp_segment_discard_intent_t *);
/* state0 proves completed physical erase + durable removal. Exact comparison
 * is still required before replying. Older than the retained four returns
 * NOT_FOUND, never optimistic permission to consume some current recording. */
comp_segment_result_t comp_segment_catalog_receipt_read(comp_segment_catalog_t *,uint8_t,comp_segment_entry_t *);
/* Read-only canonical OTA snapshot: bank A contains only current live rows
 * and the four exact completed-consumption receipts; bank B is blank. Source
 * must be mounted on the immutable metadata snapshot. Preserves the namespace,
 * IDs, physical audio and original provenance. Never formats unknown media.
 * Receipt extents are historical proof fields, never physical ownership. */
bool comp_segment_catalog_rebase_page(const comp_segment_catalog_t *,uint32_t new_bank_a,
    uint32_t new_bank_b,uint32_t new_data_base,uint32_t new_data_bytes,
    uint32_t protected_tail_base,uint32_t page_index,uint8_t out[256]);
comp_segment_result_t comp_segment_catalog_page(comp_segment_catalog_t *,
    uint32_t snapshot,uint32_t nonce,uint32_t start,uint8_t *out,size_t capacity,
    size_t *out_bytes);

#endif
