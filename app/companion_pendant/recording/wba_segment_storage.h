#ifndef COMPANION_WBA_SEGMENT_STORAGE_H
#define COMPANION_WBA_SEGMENT_STORAGE_H
#include "companion_segment_audio.h"
#include "companion_segment_reserve.h"
#include "../storage/spi_nor_stm32wba.h"

/* Actual NOR adapter for the continuous recorder. Only the two catalog banks
 * and the payload arena are accessible; settings, identity, resources and OTA
 * roots are outside this capability. No additional page buffer or heap. */
typedef struct {
    companion_spi_nor_stm32wba_t *nor;
    uint32_t banks[2],data_base,data_bytes;
    uint32_t arbitration_yields;
    bool poisoned;
    bool transfer_read_released_failure; /* most recent radio page read only */
    bool idle_lookup_read_failed; /* first error was a phase-free directory or sealed-audio read */
    bool transfer_read_yield; /* existing padding: one owner poll yields to an attempted read */
} comp_wba_segment_storage_t;

bool comp_wba_segment_storage_init(comp_wba_segment_storage_t *,companion_spi_nor_stm32wba_t *,
    uint32_t bank_a,uint32_t bank_b,uint32_t data_base,uint32_t data_bytes);
/* Only the already-qualified bounded suspended-read path can overlap reclaim. */
bool comp_wba_segment_storage_reclaim_read_supported(const comp_wba_segment_storage_t *);
/* Mount plus the platform's cached SFDP policy, including runtime remounts.
 * Generic/read-only mounts retain their default sector policy. No NOR I/O. */
comp_segment_result_t comp_wba_segment_storage_mount_begin(comp_wba_segment_storage_t *,
    comp_segment_catalog_t *,const uint8_t uid[12],uint64_t epoch);
comp_segment_port_t comp_wba_segment_storage_catalog_port(comp_wba_segment_storage_t *);
comp_segment_audio_port_t comp_wba_segment_storage_audio_port(comp_wba_segment_storage_t *);
/* Recorder-owned verification: only a fast, fully released read failure may
 * be retried by that writer. Recovery readers retain the normal port. */
comp_segment_audio_port_t comp_wba_segment_storage_writer_audio_port(comp_wba_segment_storage_t *);
/* For radio payload reads only, never writer verification or recovery. */
comp_segment_audio_port_t comp_wba_segment_storage_transfer_audio_port(comp_wba_segment_storage_t *);
/* Use these instead of raw bool-callback polls when an erase may run. Each
 * slice either progresses arbitration OR performs one normal worker I/O.
 * Pending never poisons the catalog or advances its durable ownership. */
comp_segment_result_t comp_wba_segment_storage_catalog_poll(comp_wba_segment_storage_t *,comp_segment_catalog_t *);
comp_segment_result_t comp_wba_segment_storage_reserve_poll(comp_wba_segment_storage_t *,comp_segment_reserve_t *);
comp_segment_result_t comp_wba_segment_storage_reserve_cancel_poll(comp_wba_segment_storage_t *,comp_segment_reserve_t *);
comp_segment_result_t comp_wba_segment_storage_entry(comp_wba_segment_storage_t *,comp_segment_catalog_t *,uint8_t,comp_segment_entry_t *);
/* Only for a radio-owned, read-only directory lookup. */
comp_segment_result_t comp_wba_segment_storage_transfer_entry(comp_wba_segment_storage_t *,comp_segment_catalog_t *,uint8_t,comp_segment_entry_t *);
comp_segment_result_t comp_wba_segment_storage_entry_intent(comp_wba_segment_storage_t *,comp_segment_catalog_t *,uint8_t,comp_segment_entry_t *,comp_segment_discard_intent_t *);
comp_segment_result_t comp_wba_segment_storage_receipt(comp_wba_segment_storage_t *,comp_segment_catalog_t *,uint8_t,comp_segment_entry_t *);
comp_segment_result_t comp_wba_segment_storage_cancel_poll(comp_wba_segment_storage_t *,comp_segment_audio_t *);

#endif
