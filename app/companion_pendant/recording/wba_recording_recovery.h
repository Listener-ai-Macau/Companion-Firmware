#ifndef COMPANION_WBA_RECORDING_RECOVERY_H
#define COMPANION_WBA_RECORDING_RECOVERY_H
#include "wba_segment_discard_worker.h"
#include "wba_segment_storage.h"

/* Exclusive BOOT owner, after catalog mount and before capture/BLE/OTA.
 * May live in a union with the continuous engine, then be discarded only
 * after a terminal result. Uses caller-owned256B scratch; no heap or copies
 * of the whole catalog. This is NOT a reset/retry of a live recording.
 * Every poll performs at most one normal backend I/O/arbitration slice. */
typedef struct {
    comp_wba_segment_storage_t *storage;
    comp_segment_catalog_t *catalog;
    /* Boot completes discard recovery before starting audio recovery. */
    union { comp_segment_audio_recovery_t audio; comp_discard_worker_t discard; };
    comp_segment_entry_t entry,candidate;
    uint8_t *page;
    uint32_t sealed,canceled,reclaimed,unresolved;
    comp_segment_result_t result;
    uint8_t phase,scan,look;
    bool last;
} comp_wba_recording_recovery_t;

comp_segment_result_t comp_wba_recording_recovery_begin(comp_wba_recording_recovery_t *,
    comp_wba_segment_storage_t *,comp_segment_catalog_t *,uint8_t page[256]);
comp_segment_result_t comp_wba_recording_recovery_poll(comp_wba_recording_recovery_t *);
/* OK alone means the bounded recovery scan completed. Unresolved ownership
 * is preserved; do not advertise a healthy recorder/enable new capture when
 * this readiness predicate is false. No automatic formatting or loss. */
bool comp_wba_recording_recovery_ready(const comp_wba_recording_recovery_t *);
#endif
