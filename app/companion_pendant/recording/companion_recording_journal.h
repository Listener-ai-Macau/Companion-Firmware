#ifndef COMPANION_RECORDING_JOURNAL_H
#define COMPANION_RECORDING_JOURNAL_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* One ATT recording-list notification can carry seven 32-byte entries. */
#define COMP_RECORDING_JOURNAL_MAX_ENTRIES 7u
#define COMP_RECORDING_JOURNAL_SECTOR_BYTES 4096u
#define COMP_RECORDING_JOURNAL_CATALOG_SECTORS 2u
#define COMP_RECORDING_JOURNAL_SHA256_BYTES 32u
#define COMP_RECORDING_CHECKPOINT_VERIFIED 1u
#define COMP_RECORDING_RECOVERED_PREFIX 2u
#define COMP_RECORDING_CHECKPOINT_LOG_READY 4u
#define COMP_RECORDING_CHECKPOINT_RECORD_BYTES 64u
#define COMP_RECORDING_CHECKPOINT_LOG_SLOTS 64u

typedef enum {
    COMP_RECORDING_JOURNAL_EMPTY = 0u,
    COMP_RECORDING_JOURNAL_WRITING = 1u,
    COMP_RECORDING_JOURNAL_UNSYNCED = 2u,
    COMP_RECORDING_JOURNAL_ACKED = 3u,
    /* Opt-in WBA asynchronous deletion. Never list or transfer this entry;
     * after reboot erasure may safely restart from its first sector. */
    COMP_RECORDING_JOURNAL_ERASING = 4u,
} comp_recording_journal_state_t;

typedef enum {
    COMP_RECORDING_JOURNAL_OK = 0u,
    COMP_RECORDING_JOURNAL_BAD_ARGUMENT,
    COMP_RECORDING_JOURNAL_IO_ERROR,
    COMP_RECORDING_JOURNAL_STORAGE_FULL,
    COMP_RECORDING_JOURNAL_DIRECTORY_FULL,
    COMP_RECORDING_JOURNAL_NOT_FOUND,
    COMP_RECORDING_JOURNAL_BAD_STATE,
    COMP_RECORDING_JOURNAL_ACK_MISMATCH,
} comp_recording_journal_result_t;

typedef struct {
    uint32_t recording_id;
    uint32_t extent_offset;
    uint32_t payload_offset;
    uint32_t reserved_bytes;
    uint32_t committed_bytes;
    uint32_t total_length;
    uint32_t acked_offset;
    uint32_t started_unix_s;
    uint32_t started_tick_ms;
    uint32_t duration_ms;
    uint32_t content_crc32;
    uint8_t sha256[COMP_RECORDING_JOURNAL_SHA256_BYTES];
    uint8_t codec;
    uint8_t sync_state;
    uint8_t source_mode;
    uint8_t reserved;
} comp_recording_journal_entry_t;

typedef bool (*comp_recording_journal_read_fn)(
    void *context, uint32_t offset, uint8_t *destination, uint32_t length);
typedef bool (*comp_recording_journal_program_fn)(
    void *context, uint32_t offset, const uint8_t *source, uint32_t length);
typedef bool (*comp_recording_journal_erase_fn)(
    void *context, uint32_t offset, uint32_t length);
/* A bounded cooperative erase. Healthy pending returns true with zero bytes;
 * only physically completed, sector-aligned bytes may advance the cursor. */
typedef bool (*comp_recording_journal_erase_step_fn)(
    void *context, uint32_t offset, uint32_t remaining_bytes, uint32_t *erased_bytes);
typedef uint32_t (*comp_recording_journal_crc32_fn)(
    uint32_t seed, const uint8_t *data, uint32_t length);

typedef struct {
    comp_recording_journal_read_fn read;
    comp_recording_journal_program_fn program;
    comp_recording_journal_erase_fn erase;
    comp_recording_journal_crc32_fn crc32;
} comp_recording_journal_port_t;

typedef struct {
    uint32_t magic;
    uint16_t version;
    uint16_t entry_capacity;
    uint32_t generation;
    uint32_t next_recording_id;
    uint32_t crc32;
    comp_recording_journal_entry_t entries[COMP_RECORDING_JOURNAL_MAX_ENTRIES];
} comp_recording_journal_catalog_t;

typedef struct {
    comp_recording_journal_port_t port;
    void *port_context;
    /* Optional RAM-only opt-in, bind after mount. Catalog writes keep the
     * synchronous port; no on-media catalog or legacy WB contract changes. */
    comp_recording_journal_erase_step_fn reclaim_erase_step;
    uint32_t region_bytes;
    uint32_t data_bytes;
    /* Defaults to data_bytes; durable OTA metadata may reserve a shared tail. */
    uint32_t allocation_bytes;
    uint8_t active_catalog;
    uint8_t active_catalog_slot;
    bool append_catalogs;
    bool mounted;
    uint8_t checkpoint_slots[COMP_RECORDING_JOURNAL_MAX_ENTRIES];
    /* Result of the most recent successful begin().  These counters are
     * diagnostic-only and are intentionally not persisted in the catalog. */
    uint32_t last_ring_evicted_count;
    comp_recording_journal_catalog_t catalog;
} comp_recording_journal_t;

/* Actual mounted geometry; reservations include padding and active erasures.
 * A free byte is not necessarily part of a usable contiguous extent. */
typedef struct {
    uint32_t free_bytes;
    uint32_t largest_free_extent;
    uint32_t protected_bytes;
    uint32_t consumed_bytes;
    uint8_t used_entries;
    uint8_t unsynced_entries;
    uint8_t writing_entries;
    uint8_t consumed_entries;
} comp_recording_journal_space_t;

/* Pure RAM query. Invalid/overlapping catalog extents fail closed. */
bool comp_recording_journal_space(const comp_recording_journal_t *,
                                comp_recording_journal_space_t *);
/* RAM-only, capture-off. Refuses overlap with any live recording extent. */
bool comp_recording_journal_set_allocation_bytes(comp_recording_journal_t *,uint32_t);

/* COP1 CBR: 40-byte Opus plus 2-byte length every 20ms. */
#define COMP_RECORDING_BYTES_PER_SECOND 2100u
#define COMP_RECORDING_RESERVE_HEADROOM (4096u + 12u)
/* Fixed seconds must fit in full. Zero means the largest current extent;
 * it is a finite storage budget, not uninterrupted infinite recording. */
bool comp_recording_journal_recording_budget(const comp_recording_journal_t *,
                                           uint32_t seconds,uint32_t *bytes);

/* Mounts the newest valid A/B catalog. Blank media gets one empty catalog. */
comp_recording_journal_result_t comp_recording_journal_mount(
    comp_recording_journal_t *journal,
    const comp_recording_journal_port_t *port,
    void *port_context,
    uint32_t region_bytes);

/* WBA opt-in: append CRC-checked catalog snapshots inside each A/B sector,
 * validate every extent and refuse to format nonblank corrupt catalogs.
 * Read-compatible with CRJ1; after a CRJ2 commit, firmware that only reads
 * CRJ1 must not be installed. Existing WB mount behavior is unchanged. */
comp_recording_journal_result_t comp_recording_journal_mount_strict(
    comp_recording_journal_t *, const comp_recording_journal_port_t *, void *, uint32_t);

/* Migration preflight: identical strict extent/checkpoint validation, with
 * no blank-media formatting. Caller must also supply read-only program/erase
 * callbacks; the result is for inspection, not a writable journal. */
comp_recording_journal_result_t comp_recording_journal_mount_readonly_strict(
    comp_recording_journal_t *, const comp_recording_journal_port_t *, void *, uint32_t);

/* Reserve the final sector of an already erased WBA extent for 64 compact
 * checkpoints. The readiness flag is committed before the microphone starts;
 * no checkpoint performs a catalog write or sector erase during capture. */
comp_recording_journal_result_t comp_recording_journal_checkpoint_log_init(
    comp_recording_journal_t *, uint32_t recording_id);
uint32_t comp_recording_journal_payload_limit(const comp_recording_journal_entry_t *);

/* Imports one legacy single-slot recording without moving or erasing payload.
 * Legacy extent_offset may be sector-aligned while payload_offset follows its
 * old inline header. */
comp_recording_journal_result_t comp_recording_journal_import_legacy(
    comp_recording_journal_t *journal,
    const comp_recording_journal_entry_t *legacy);

/* Returns whether a new reservation can be made immediately.  The read-only
 * preflight includes the same completed-recording eviction plan used by
 * begin(); WRITING entries are never considered reclaimable. */
bool comp_recording_journal_can_reserve(
    const comp_recording_journal_t *journal,
    uint32_t reserve_payload_bytes);

/* Legacy WB-only recovery policy. WBA uses verified-prefix salvage instead.
 * After a reboot there is no live capture owner, so every WRITING entry is an
 * abandoned partial recording that cannot be finalized or consumed.  Release
 * all such catalog extents; the next begin() still erases its selected extent
 * before capture.  Completed UNSYNCED/ACKED recordings remain available. */
comp_recording_journal_result_t
comp_recording_journal_recover_abandoned_writes(
    comp_recording_journal_t *journal,
    uint32_t *out_recovered_count);

/* Atomically reserves a sector-aligned extent.  If capacity or directory slots
 * are exhausted, only host-validated ACKED entries may be evicted as a bounded
 * ring in recording age order.  UNSYNCED, WRITING and ERASING entries are never
 * reused implicitly.  The product storage task erases the selected new extent
 * asynchronously afterward. */
comp_recording_journal_result_t comp_recording_journal_begin(
    comp_recording_journal_t *journal,
    uint32_t reserve_payload_bytes,
    uint32_t started_unix_s,
    uint32_t started_tick_ms,
    uint8_t codec,
    uint8_t source_mode,
    comp_recording_journal_entry_t *out_entry);

/* Persists a coarse committed/ACK cursor; values are monotonic and bounded. */
comp_recording_journal_result_t comp_recording_journal_checkpoint(
    comp_recording_journal_t *journal,
    uint32_t recording_id,
    uint32_t committed_bytes,
    uint32_t acked_offset);
/* WBA durable receive identity; only already programmed bytes qualify. */
comp_recording_journal_result_t comp_recording_journal_checkpoint_verified(
    comp_recording_journal_t *,uint32_t recording_id,uint32_t committed_bytes,
    uint32_t content_crc32,const uint8_t sha256[COMP_RECORDING_JOURNAL_SHA256_BYTES]);
comp_recording_journal_result_t comp_recording_journal_finalize_recovered(
    comp_recording_journal_t *,uint32_t recording_id,uint32_t bytes,uint32_t duration_ms,
    uint32_t content_crc32,const uint8_t sha256[32]);

/* Releases a WRITING reservation after capture preparation/finalize failed. */
comp_recording_journal_result_t comp_recording_journal_abort(
    comp_recording_journal_t *journal, uint32_t recording_id);

comp_recording_journal_result_t comp_recording_journal_finalize(
    comp_recording_journal_t *journal,
    uint32_t recording_id,
    uint32_t total_length,
    uint32_t duration_ms,
    uint32_t content_crc32,
    const uint8_t sha256[COMP_RECORDING_JOURNAL_SHA256_BYTES],
    uint8_t codec);

/* Opt-in capacity recovery for a completed recording.  The default journal
 * behavior continues to retain the full reservation until callers request
 * this operation.  No payload bytes are erased. */
comp_recording_journal_result_t comp_recording_journal_trim_completed_extent(
    comp_recording_journal_t *journal, uint32_t recording_id);

/* Full length + SHA confirmation is required before an entry becomes reclaimable. */
comp_recording_journal_result_t comp_recording_journal_ack_complete(
    comp_recording_journal_t *journal,
    uint32_t recording_id,
    uint32_t validated_total_length,
    const uint8_t validated_sha256[COMP_RECORDING_JOURNAL_SHA256_BYTES]);

/* Erases and removes exactly one ACKED extent. UNSYNCED data fails closed. */
comp_recording_journal_result_t comp_recording_journal_reclaim_acked(
    comp_recording_journal_t *journal,
    uint32_t recording_id);

/* Durably marks one ACKED extent for bounded erasure. Unlike the legacy
 * synchronous reclaim API, no payload is erased until the marker commits. */
comp_recording_journal_result_t comp_recording_journal_begin_reclaim(
    comp_recording_journal_t *journal, uint32_t recording_id);
/* Only a physically confirmed delete-all action may discard UNSYNCED data.
 * Marks all completed entries ERASING in one durable catalog transaction. */
comp_recording_journal_result_t comp_recording_journal_discard_all_confirmed(comp_recording_journal_t *);
/* Read-only loss proposal, only when the full requested budget/slot cannot fit.
 * Consumed recovery takes priority; WRITING is never a candidate. The caller
 * must obtain an explicit, short-lived user confirmation of this exact entry. */
bool comp_recording_journal_discard_candidate(const comp_recording_journal_t *,
    uint32_t seconds, comp_recording_journal_entry_t *, uint32_t *largest_after);
/* Separate from ACK: validates generation, oldest UNSYNCED identity/length/SHA,
 * then commits ERASING without fabricating a durable host-copy receipt. */
comp_recording_journal_result_t comp_recording_journal_discard_oldest_confirmed(
    comp_recording_journal_t *, uint32_t generation, uint32_t recording_id,
    uint32_t total_length, const uint8_t sha256[COMP_RECORDING_JOURNAL_SHA256_BYTES]);
/* Erases at most one payload sector per call, or one bounded step through the
 * optional reclaim_erase_step port. Pending keeps cursor unchanged. The last
 * call only commits the
 * catalog removal. cursor is RAM-only, initialize to zero after every reboot.
 * A failed call does not advance cursor or declare completion. */
comp_recording_journal_result_t comp_recording_journal_reclaim_step(
    comp_recording_journal_t *journal, uint32_t recording_id,
    uint32_t *cursor, bool *complete);

uint32_t comp_recording_journal_count(const comp_recording_journal_t *journal);
const comp_recording_journal_entry_t *comp_recording_journal_at(
    const comp_recording_journal_t *journal, uint32_t index);
const comp_recording_journal_entry_t *comp_recording_journal_find(
    const comp_recording_journal_t *journal, uint32_t recording_id);

#ifdef __cplusplus
}
#endif

#endif
