#ifndef COMPANION_WBA_SIMPLE_LAYOUT_H
#define COMPANION_WBA_SIMPLE_LAYOUT_H
#include "wba_storage_layout.h"
/* Reuse existing dynamic metadata pages. No payload/backup partition and no
 * change to recording, CSI1, preferences or the static-resource boundary. */
#define COMP_SIMPLE_CURRENT_A COMP_WBA_NOR_UPDATE_META_A
#define COMP_SIMPLE_CURRENT_B COMP_WBA_NOR_UPDATE_META_B
#define COMP_SIMPLE_PENDING (COMP_WBA_NOR_DYNAMIC_BASE+UINT32_C(0x5000))
/* Physical block alignment, not offset alignment. The package tail claim can
 * start in the middle of a block. Only erase complete blocks entirely inside
 * that live claim; roots, resources and unclaimed recording bytes stay outside.
 * The caller advances its erased frontier only after physical WIP succeeds. */
static inline uint32_t comp_wba_simple_payload_erase_bytes(
    uint32_t base,uint32_t owned_bytes,uint32_t offset)
{
    if(base<COMP_WBA_NOR_RECORDING_BASE || base>COMP_WBA_NOR_TOTAL_BYTES ||
       !owned_bytes || (base&4095u) || (owned_bytes&4095u) || (offset&4095u) ||
       owned_bytes>COMP_WBA_NOR_TOTAL_BYTES-base || offset>=owned_bytes)return 0u;
    return !((base+offset)&65535u) && owned_bytes-offset>=65536u?65536u:4096u;
}
#endif
