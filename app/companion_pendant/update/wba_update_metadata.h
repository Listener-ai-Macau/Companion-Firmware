#ifndef COMPANION_WBA_UPDATE_METADATA_H
#define COMPANION_WBA_UPDATE_METADATA_H

#include "wba_boot_installer.h"

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_WBA_UPDATE_METADATA_MAGIC UINT32_C(0x32535557) /* WUS2, layout 3 */

typedef struct {
    uint32_t magic;
    uint32_t sequence;
    uint8_t checkpoint_valid;
    uint8_t boot_record_valid;
    uint16_t reserved;
    /* One atomic shared-arena reservation for staging + exact rollback copy.
     * Zero means the entire arena belongs to the recording allocator. */
    uint32_t workspace_base,staging_bytes,backup_bytes,workspace_target;
    comp_wba_update_checkpoint_t checkpoint;
    comp_wba_boot_record_t boot_record;
    uint32_t crc32;
} comp_wba_update_metadata_record_t;

typedef struct {
    bool (*read)(void *context,uint32_t offset,uint8_t *data,size_t length);
    bool (*erase_4k)(void *context,uint32_t offset);
    bool (*write)(void *context,uint32_t offset,const uint8_t *data,size_t length);
    void *context;
    uint32_t slot_a;
    uint32_t slot_b;
} comp_wba_update_metadata_ports_t;

typedef struct {
    comp_wba_update_metadata_record_t record;
    uint8_t active_slot;
    bool loaded;
} comp_wba_update_metadata_store_t;

/* Both slots must be readable. Only two entirely erased record prefixes count
 * as a new device; any nonblank invalid record fails closed. */
bool comp_wba_update_metadata_mount(comp_wba_update_metadata_store_t *store,
                                    const comp_wba_update_metadata_ports_t *ports);

/* Commits candidate to the inactive erased slot and verifies it. The in-RAM
 * store changes only after durable readback succeeds. */
bool comp_wba_update_metadata_commit(comp_wba_update_metadata_store_t *store,
                                     const comp_wba_update_metadata_ports_t *ports,
                                     const comp_wba_update_metadata_record_t *candidate);

#ifdef __cplusplus
}
#endif

#endif
