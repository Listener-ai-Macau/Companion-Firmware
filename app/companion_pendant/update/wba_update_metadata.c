#include "wba_update_metadata.h"

#include "wba_update_manifest_wire.h"

#include <string.h>

static uint32_t record_crc(const comp_wba_update_metadata_record_t *record)
{
    return comp_wba_update_wire_crc32((const uint8_t *)record,
                                      offsetof(comp_wba_update_metadata_record_t,crc32));
}

static bool valid(const comp_wba_update_metadata_record_t *record)
{
    if(!record)return false;
    bool workspace=record->workspace_base!=0u;
    if(workspace) {
        if(record->workspace_base<COMP_WBA_NOR_RECORDING_BASE||record->workspace_base%4096u||
           !record->staging_bytes||record->staging_bytes%4096u||
           record->staging_bytes>COMP_WBA_NOR_UPDATE_STAGING_BYTES||
           !record->backup_bytes||record->backup_bytes%4096u||
           record->backup_bytes>(record->workspace_target==COMP_WBA_UPDATE_TARGET_FIRMWARE ?
               COMP_WBA_NOR_FIRMWARE_BACKUP_BYTES : COMP_WBA_NOR_UI_BYTES)||
           record->workspace_base>COMP_WBA_NOR_TOTAL_BYTES||
           record->staging_bytes+record->backup_bytes!=COMP_WBA_NOR_TOTAL_BYTES-record->workspace_base||
           (record->workspace_target!=COMP_WBA_UPDATE_TARGET_FIRMWARE&&record->workspace_target!=COMP_WBA_UPDATE_TARGET_UI_ASSETS))return false;
    } else if(record->staging_bytes||record->backup_bytes||record->workspace_target)return false;
    return record->magic==COMP_WBA_UPDATE_METADATA_MAGIC&&
           record->reserved==0u&&record->crc32==record_crc(record)&&
           (!record->checkpoint_valid||comp_wba_update_checkpoint_valid(&record->checkpoint))&&
           (!record->boot_record_valid||comp_wba_boot_record_valid(&record->boot_record));
}

static bool all_ff(const void *data,size_t length)
{
    const uint8_t *p=data;
    while(length--)if(*p++!=0xffu)return false;
    return true;
}

static bool newer(uint32_t left,uint32_t right)
{
    return (int32_t)(left-right)>0;
}

bool comp_wba_update_metadata_mount(comp_wba_update_metadata_store_t *store,
                                    const comp_wba_update_metadata_ports_t *ports)
{
    comp_wba_update_metadata_record_t a,b;bool av,bv;
    if(!store||!ports||!ports->read||!ports->erase_4k||!ports->write||
       ports->slot_a==ports->slot_b)return false;
    if(!ports->read(ports->context,ports->slot_a,(uint8_t *)&a,sizeof(a))||
       !ports->read(ports->context,ports->slot_b,(uint8_t *)&b,sizeof(b)))return false;
    av=valid(&a);bv=valid(&b);
    if(!av&&!bv){
        if(!all_ff(&a,sizeof(a))||!all_ff(&b,sizeof(b)))return false;
        memset(store,0,sizeof(*store));store->active_slot=1u;return true;
    }
    memset(store,0,sizeof(*store));
    if(bv&&(!av||newer(b.sequence,a.sequence))){store->record=b;store->active_slot=1u;}
    else {store->record=a;store->active_slot=0u;}
    store->loaded=true;return true;
}

bool comp_wba_update_metadata_commit(comp_wba_update_metadata_store_t *store,
                                     const comp_wba_update_metadata_ports_t *ports,
                                     const comp_wba_update_metadata_record_t *candidate)
{
    comp_wba_update_metadata_record_t next,verify;uint8_t slot;uint32_t offset;
    if(!store||!ports||!candidate||!ports->read||!ports->erase_4k||!ports->write)return false;
    next=*candidate;next.magic=COMP_WBA_UPDATE_METADATA_MAGIC;
    next.sequence=store->record.sequence+1u;next.reserved=0u;next.crc32=record_crc(&next);
    slot=(uint8_t)(store->active_slot^1u);offset=slot?ports->slot_b:ports->slot_a;
    if(!ports->erase_4k(ports->context,offset)||
       !ports->write(ports->context,offset,(const uint8_t *)&next,sizeof(next))||
       !ports->read(ports->context,offset,(uint8_t *)&verify,sizeof(verify))||
       memcmp(&verify,&next,sizeof(verify))!=0||!valid(&verify))return false;
    store->record=next;store->active_slot=slot;store->loaded=true;return true;
}
