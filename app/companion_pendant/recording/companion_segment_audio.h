#ifndef COMPANION_SEGMENT_AUDIO_H
#define COMPANION_SEGMENT_AUDIO_H

#include "companion_segment_catalog.h"
#include "../core/companion_sha256.h"
#include "companion_recording_timeline.h"
#include "companion_recording_audio_profile.h"

/* Physical media framing only. BLE and Type see the selected COP1 schema.
 * byte stream. Each 256-byte page has 248 data bytes, bound CRC and a separate
 * commit word. A whole erased extent is first bound to its durable reservation
 * by a committed provenance page, so recovery cannot adopt old audio from an
 * interrupted preerase. A program/readback failure remains uncertain. */
#define COMP_SEG_AUDIO_DATA_BYTES 248u
#define COMP_SEG_AUDIO_PREFIX_BYTES 256u
#define COMP_SEG_AUDIO_FRAME_BYTES 42u /* Existing16kbps CBR/20ms COP1 packet. */

typedef struct {
    comp_segment_result_t (*read)(void *,uint32_t,uint8_t *,uint32_t);
    /* PENDING means no accepted audio program; NOR arbitration may progress.
     * A failed/uncertain accepted program must return IO_ERROR, never PENDING
     * and retry blindly. The caller retains identical pending bytes. */
    comp_segment_result_t (*program)(void *,uint32_t,const uint8_t *,uint32_t);
    void *context;
} comp_segment_audio_port_t;

typedef struct {
    comp_segment_audio_port_t port;
    const comp_segment_entry_t *entry;
    comp_segment_catalog_t *cancellation;
    uint8_t *page; /* caller-owned stable256B scratch, no heap/extra page */
    uint32_t data_base, committed_bytes, pages, binding_crc;
    uint8_t phase, length, read_retries;
    bool prepared, failed,canceled,claimed;
} comp_segment_audio_t;

uint32_t comp_segment_audio_capacity(uint32_t reserved_bytes);
/* Entry must be durable WRITING and its entire extent verified erased by the
 * reservation worker. The entry/page remain owned until the operation ends. */
comp_segment_result_t comp_segment_audio_prepare_begin(comp_segment_audio_t *,
    const comp_segment_audio_port_t *,const comp_segment_entry_t *,uint32_t data_base,
    uint8_t page[COMP_SEGMENT_PAGE_BYTES]);
/* A logical append is at most248B; only the final append may be shorter. A
 * pending operation never advances committed_bytes. One backend I/O per poll. */
comp_segment_result_t comp_segment_audio_append_begin(comp_segment_audio_t *,
    const uint8_t *,uint8_t length);
comp_segment_result_t comp_segment_audio_poll(comp_segment_audio_t *);
/* Release an unused future extent after STOP or a canceled start. Only an
 * unmodified, unclaimed future writer is eligible. Poll verifies provenance and every
 * audio page blank before the durable catalog tombstone. No audio deletion,
 * optimistic cursor reset or leaked reservation between logical sessions. */
comp_segment_result_t comp_segment_audio_cancel_begin(comp_segment_audio_t *,comp_segment_catalog_t *);
/* Cancellation includes a catalog transaction. A real NOR adapter supplies
 * its arbitration-aware poll here; raw comp_segment_audio_poll remains the
 * software/exclusive-port default. The callback is used only for that owned
 * catalog transaction, not for provenance/audio reads. */
comp_segment_result_t comp_segment_audio_cancel_poll(comp_segment_audio_t *,
    comp_segment_result_t (*catalog_poll)(void *,comp_segment_catalog_t *),void *);

/* One validated physical data page. Sealed/live callers control the logical
 * limit; this primitive never turns a growing tail into an ACK-able segment. */
comp_segment_result_t comp_segment_audio_read_page(const comp_segment_audio_port_t *,
    const comp_segment_entry_t *,uint32_t data_base,uint32_t page_index,
    uint8_t page[COMP_SEGMENT_PAGE_BYTES],uint8_t *length);

typedef struct {
    comp_segment_audio_port_t port;
    const comp_segment_entry_t *entry;
    uint8_t *page;
    companion_sha256_t prefix_sha, complete_sha;
    uint32_t data_base, pages, bytes, complete_bytes, crc, complete_crc, frames;
    uint16_t packet_remaining, packet_length;
    uint64_t timeline_ms;
    uint32_t timeline_sequence,bookmark_sequence;
    uint8_t phase, header_bytes, length_bytes,container_schema;
    bool pause_open,ended_paused;
    bool prefix_ended, failed, allow_unwritten, unwritten_provenance, empty_verified;
    uint8_t codec_delay;
    bool codec_config_seen,codec_end_seen,codec_drain_pending,audio_profile_seen;
} comp_segment_audio_recovery_t;

/* Recovery is read-only and bounded. It accepts only a matching provenance
 * commit and contiguous, CRC-valid committed pages. Uncommitted tail pages
 * end the prefix; a later nonblank page or a damaged committed page fails
 * closed. Schema2 pause events/padding contribute bytes/CRC/SHA, never
 * samples. Their monotonic sequence/time, exact sample point and pairing
 * are validated. An unmatched final PAUSE remains explicitly interrupted. */
comp_segment_result_t comp_segment_audio_recover_begin(comp_segment_audio_recovery_t *,
    const comp_segment_audio_port_t *,const comp_segment_entry_t *,uint32_t data_base,
    uint8_t page[COMP_SEGMENT_PAGE_BYTES]);
/* Exclusive boot recovery may also prove an unused reservation entirely
 * empty. A blank/matching uncommitted provenance is accepted ONLY if every
 * remaining page is blank. Mismatched provenance/old data stays owned.
 * This does not automatically cancel or erase anything. */
comp_segment_result_t comp_segment_audio_recover_owned_begin(comp_segment_audio_recovery_t *,
    const comp_segment_audio_port_t *,const comp_segment_entry_t *,uint32_t data_base,
    uint8_t page[COMP_SEGMENT_PAGE_BYTES]);
comp_segment_result_t comp_segment_audio_recover_poll(comp_segment_audio_recovery_t *);
bool comp_segment_audio_recovered(const comp_segment_audio_recovery_t *,
    uint32_t *bytes,uint32_t *frames,uint32_t *crc,uint8_t sha[32]);
bool comp_segment_audio_recovery_empty_verified(const comp_segment_audio_recovery_t *);

#endif
