#include "wba_shared_pool.h"
#include "wba_flash_migration.h"
#include <string.h>

bool comp_wba_v2_layout_absent(const comp_wba_pool_port_t *port)
{
    uint8_t prefix[4];
    if(!port||!port->read)return false;
    for(uint8_t bank=0u;bank<2u;bank++) {
        uint32_t at=bank?COMP_WBA_V2_LAYOUT_B:COMP_WBA_V2_LAYOUT_A;
        if(!port->read(port->context,at,prefix,sizeof(prefix)))return false;
        /* An announced future layout, even torn, is not V1-owned storage. */
        if(!memcmp(prefix,"CFL",3u))return false;
    }
    /* A prepared relocation already freezes V1, before overwriting front
     * resource bytes. Old inactive OTA backup data has no CLM ownership. */
    for(uint8_t bank=0u;bank<2u;bank++) {
        uint32_t at=bank?COMP_WBA_MIGRATION_ROOT_B:COMP_WBA_MIGRATION_ROOT_A;
        if(!port->read(port->context,at,prefix,sizeof(prefix)))return false;
        if(!memcmp(prefix,"CLM",3u))return false;
    }
    return true;
}
