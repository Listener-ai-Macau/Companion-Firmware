#include "update_storage.h"
#include "wba_workspace_layout.h"

#include <string.h>

static bool nor_read_raw(void *context,uint32_t offset,uint8_t *data,size_t length)
{
    comp_v11_update_storage_t *storage=context;
    return storage&&storage->config.nor&&
           companion_spi_nor_stm32wba_read(storage->config.nor,offset,data,length)==COMPANION_SPI_NOR_STM32WBA_OK;
}
static bool nor_write_raw(void *context,uint32_t offset,const uint8_t *data,size_t length)
{
    comp_v11_update_storage_t *storage=context;
    return storage&&storage->config.nor&&
           companion_spi_nor_stm32wba_program(storage->config.nor,offset,data,length)==COMPANION_SPI_NOR_STM32WBA_OK;
}
static bool nor_erase_raw(void *context,uint32_t offset)
{
    comp_v11_update_storage_t *storage=context;
    return storage&&storage->config.nor&&
           companion_spi_nor_stm32wba_erase_4k(storage->config.nor,offset)==COMPANION_SPI_NOR_STM32WBA_OK;
}

static bool metadata_mount(comp_v11_update_storage_t *storage)
{
    if(!comp_wba_workspace_layout_valid(nor_read_raw,storage))return false;
    comp_wba_update_metadata_ports_t ports={nor_read_raw,nor_erase_raw,nor_write_raw,
        storage,COMP_WBA_NOR_UPDATE_META_A,COMP_WBA_NOR_UPDATE_META_B};
    return comp_wba_update_metadata_mount(&storage->metadata,&ports);
}

static bool metadata_commit(comp_v11_update_storage_t *storage,
                            const comp_v11_update_metadata_t *candidate)
{
    comp_wba_update_metadata_ports_t ports={nor_read_raw,nor_erase_raw,nor_write_raw,
        storage,COMP_WBA_NOR_UPDATE_META_A,COMP_WBA_NOR_UPDATE_META_B};
    if(comp_wba_update_metadata_commit(&storage->metadata,&ports,candidate))return true;
    /* A lost write/readback result cannot prove that the old WUS2 still owns
     * the pool. Retain the RAM lease and remount before any more mutations. */
    storage->ready=false;storage->manifest_accepted=false;return false;
}

static bool trial_active(const comp_v11_update_storage_t *s)
{
    return (s->metadata.record.boot_record_valid&&s->metadata.record.boot_record.phase>=COMP_WBA_BOOT_CANDIDATE_READY&&
        s->metadata.record.boot_record.phase<=COMP_WBA_BOOT_AWAIT_CONFIRM) ||
        (s->metadata.record.boot_record_valid&&s->metadata.record.boot_record.phase==COMP_WBA_BOOT_ROLLBACK);
}
static bool workspace_release(comp_v11_update_storage_t *s)
{
    if(trial_active(s))return false;
    if(s->metadata.record.workspace_base) {
        comp_v11_update_metadata_t next=s->metadata.record;
        next.workspace_base=next.staging_bytes=next.backup_bytes=next.workspace_target=0u;
        if(!metadata_commit(s,&next))return false;
    }
    /* Reconcile even a zero durable lease: an earlier release may have
     * committed to NOR before the allocator could acknowledge it in RAM. */
    uint32_t base=0u;
    if(!s->config.workspace_reserve||s->config.workspace_reserve(s->config.context,0u,&base))return true;
    s->ready=false;s->manifest_accepted=false;return false;
}

/* Resident installer addresses are logical windows. Every physical payload
 * access is bounded by the durably reserved WUS2 extent, also after reboot. */
static bool mapped_address(comp_v11_update_storage_t *s,uint32_t offset,size_t n,uint32_t *at)
{
    uint32_t base=0u,bytes=0u;
    const comp_v11_update_metadata_t *m=&s->metadata.record;
    if(offset<COMP_WBA_NOR_UI_BYTES){base=COMP_WBA_NOR_UI_BASE;bytes=COMP_WBA_NOR_UI_BYTES;}
    else if(m->workspace_base&&offset>=COMP_WBA_NOR_UPDATE_STAGING_BASE&&offset<COMP_WBA_NOR_UPDATE_STAGING_BASE+COMP_WBA_NOR_UPDATE_STAGING_BYTES) {
        offset-=COMP_WBA_NOR_UPDATE_STAGING_BASE;base=m->workspace_base;bytes=m->staging_bytes;
    } else if(m->workspace_base&&m->workspace_target==COMP_WBA_UPDATE_TARGET_UI_ASSETS&&offset>=COMP_WBA_NOR_RESOURCE_BACKUP_BASE&&offset<COMP_WBA_NOR_RESOURCE_BACKUP_BASE+COMP_WBA_NOR_RESOURCE_BACKUP_BYTES) {
        offset-=COMP_WBA_NOR_RESOURCE_BACKUP_BASE;base=m->workspace_base+m->staging_bytes;bytes=m->backup_bytes;
    } else if(m->workspace_base&&m->workspace_target==COMP_WBA_UPDATE_TARGET_FIRMWARE&&offset>=COMP_WBA_NOR_FIRMWARE_BACKUP_BASE&&offset<COMP_WBA_NOR_FIRMWARE_BACKUP_BASE+COMP_WBA_NOR_FIRMWARE_BACKUP_BYTES) {
        offset-=COMP_WBA_NOR_FIRMWARE_BACKUP_BASE;base=m->workspace_base+m->staging_bytes;bytes=m->backup_bytes;
    } else return false;
    if(offset>bytes||n>bytes-offset)return false;
    *at=base+offset;return true;
}
static bool mapped_read(void *c,uint32_t o,uint8_t *p,size_t n)
{uint32_t at;return mapped_address(c,o,n,&at)&&nor_read_raw(c,at,p,n);}
static bool mapped_write(void *c,uint32_t o,const uint8_t *p,size_t n)
{uint32_t at;return mapped_address(c,o,n,&at)&&nor_write_raw(c,at,p,n);}
static bool mapped_erase(void *c,uint32_t o)
{uint32_t at;return mapped_address(c,o,4096u,&at)&&nor_erase_raw(c,at);}

static bool checkpoint_load(void *context,comp_wba_update_checkpoint_t *checkpoint)
{comp_v11_update_storage_t*s=context;if(!s->metadata.loaded||!s->metadata.record.checkpoint_valid)return false;*checkpoint=s->metadata.record.checkpoint;return true;}
static bool checkpoint_store(void *context,const comp_wba_update_checkpoint_t *checkpoint)
{comp_v11_update_storage_t*s=context;comp_v11_update_metadata_t next=s->metadata.record;next.checkpoint=*checkpoint;next.checkpoint_valid=1u;return metadata_commit(s,&next);}
static bool checkpoint_clear(void *context)
{comp_v11_update_storage_t*s=context;comp_v11_update_metadata_t next;if(!s->metadata.loaded||!s->metadata.record.checkpoint_valid)return true;next=s->metadata.record;next.checkpoint_valid=0u;memset(&next.checkpoint,0,sizeof(next.checkpoint));if(!metadata_commit(s,&next))return false;return trial_active(s)||workspace_release(s);}
static bool boot_load(void *context,comp_wba_boot_record_t *record)
{comp_v11_update_storage_t*s=context;if(!s->metadata.loaded||!s->metadata.record.boot_record_valid)return false;*record=s->metadata.record.boot_record;return true;}
static bool boot_store(void *context,const comp_wba_boot_record_t *record)
{comp_v11_update_storage_t*s=context;comp_v11_update_metadata_t next=s->metadata.record;next.boot_record=*record;next.boot_record_valid=1u;return metadata_commit(s,&next);}

static bool authorize(void *context,const comp_wba_update_manifest_t *manifest,const uint8_t *auth,uint8_t auth_bytes)
{comp_v11_update_storage_t*s=context;return comp_wba_update_p256_authorize_manifest(&s->trust,manifest,auth,auth_bytes);}
static bool idle(void *context)
{comp_v11_update_storage_t*s=context;return s->config.activity_idle==NULL||s->config.activity_idle(s->config.context);}
static bool staging_begin(void *context,uint32_t bytes)
{
    comp_v11_update_storage_t *s=context;
    if(!s||!s->ready||!bytes||bytes>COMP_WBA_NOR_UPDATE_STAGING_BYTES||!s->config.workspace_reserve||trial_active(s))return false;
    uint32_t staging=(bytes+4095u)&~4095u;
    uint32_t backup=s->service.manifest.target==COMP_WBA_UPDATE_TARGET_UI_ASSETS?COMP_WBA_NOR_UI_BYTES:
        (s->config.installed_image_size+4095u)&~4095u;
    if(!backup)return false;
    uint32_t base=0u,previous=s->metadata.record.staging_bytes+s->metadata.record.backup_bytes;
    if(!s->config.workspace_reserve(s->config.context,staging+backup,&base))return false;
    if(base!=COMP_WBA_NOR_TOTAL_BYTES-staging-backup) {
        (void)s->config.workspace_reserve(s->config.context,previous,&base);return false;
    }
    comp_v11_update_metadata_t next=s->metadata.record;
    next.workspace_base=base;next.staging_bytes=staging;next.backup_bytes=backup;next.workspace_target=s->service.manifest.target;
    if(!metadata_commit(s,&next))return false;
    s->next_staging_erase=0u;return true;
}
static bool staging_write(void *context,uint32_t offset,const uint8_t *data,size_t length)
{
    comp_v11_update_storage_t*s=context;uint32_t end;
    if(!s||!s->ready||!s->metadata.record.workspace_base||!data||!length||offset>s->metadata.record.staging_bytes||length>s->metadata.record.staging_bytes-offset)return false;
    end=offset+(uint32_t)length;
    while(s->next_staging_erase<end){if(!mapped_erase(s,COMP_WBA_NOR_UPDATE_STAGING_BASE+s->next_staging_erase))return false;s->next_staging_erase+=COMP_WBA_NOR_SECTOR_BYTES;}
    return mapped_write(s,COMP_WBA_NOR_UPDATE_STAGING_BASE+offset,data,length);
}
static bool staging_read(void *context,uint32_t offset,uint8_t *data,size_t length)
{return mapped_read(context,COMP_WBA_NOR_UPDATE_STAGING_BASE+offset,data,length);}
static void staging_abort(void *context){(void)context;}
static comp_wba_update_step_result_t activate(
    void *context,const comp_wba_update_manifest_t *manifest,
    const uint8_t *authentication,uint8_t authentication_length,
    uint32_t staging_offset,uint32_t size_bytes,
    uint8_t *scratch,size_t scratch_bytes)
{
    comp_v11_update_storage_t *s=context;
    return comp_wba_boot_activate_step(&s->installer,manifest,authentication,
        authentication_length,staging_offset,size_bytes,scratch,scratch_bytes);
}
static bool flash_read(void *context,uint32_t address,uint8_t *data,size_t length)
{comp_v11_update_storage_t*s=context;return s->config.flash_read(s->config.context,address,data,length);}
static bool flash_erase(void *context,uint32_t address)
{comp_v11_update_storage_t*s=context;return s->config.flash_erase_page(s->config.context,address);}
static bool flash_write(void *context,uint32_t address,const uint8_t*data,size_t length)
{comp_v11_update_storage_t*s=context;return s->config.flash_write(s->config.context,address,data,length);}

static bool setup(comp_v11_update_storage_t *s,const comp_v11_update_storage_config_t*c,bool boot)
{
    comp_wba_boot_config_t bc={0};
    if(!s||!c||(!boot&&!c->workspace_reserve)||!c->nor||!c->hpka||!c->pka_acquire||!c->pka_release||
       !c->flash_read||!c->flash_erase_page||!c->flash_write||!c->public_key_xy||
       !c->key_id||!c->pka_timeout_ms||!c->flash_base||!c->flash_page_bytes||!c->sram_bytes||
       (c->maximum_chunk_bytes<240u || c->maximum_chunk_bytes>505u)||c->default_window_chunks<8u||c->default_window_chunks>16u)return false;
    memset(s,0,sizeof(*s));s->config=*c;
    s->pka=(comp_wba_update_p256_hal_t){c->hpka,c->pka_acquire,c->pka_release,c->context,c->pka_timeout_ms};
    s->trust=(comp_wba_update_p256_trust_t){c->key_id,c->public_key_xy,comp_wba_update_p256_hal_verify_digest,&s->pka};
    if(!comp_wba_update_p256_trust_configured(&s->trust)||!metadata_mount(s))return false;
    if(s->metadata.record.workspace_base&&c->workspace_reserve) {
        uint32_t base=0u;
        if(!c->workspace_reserve(c->context,s->metadata.record.staging_bytes+s->metadata.record.backup_bytes,&base)||
           base!=s->metadata.record.workspace_base)return false;
    }
    bc.ports=(comp_wba_boot_ports_t){authorize,mapped_read,mapped_erase,mapped_write,flash_read,flash_erase,flash_write,boot_load,boot_store,s};
    bc.target_family=COMP_WBA_UPDATE_TARGET_FAMILY_STM32WBA;bc.board_target=COMP_WBA_UPDATE_BOARD_COMPANION_V11;
    bc.flash_base=c->flash_base;bc.flash_page_bytes=c->flash_page_bytes;bc.sram_base=c->sram_base;bc.sram_bytes=c->sram_bytes;
    bc.installed_version=c->current_firmware_version;bc.installed_ui_version=c->current_ui_version;bc.installed_image_size=c->installed_image_size;
    if(!comp_wba_boot_init(&s->installer,&bc,boot))return false;
    if(!boot&&!trial_active(s)&&!s->metadata.record.checkpoint_valid&&!workspace_release(s))return false;
    s->ready=true;return true;
}

bool comp_v11_update_storage_init(comp_v11_update_storage_t*s,const comp_v11_update_storage_config_t*c)
{
    uint32_t firmware_floor,ui_floor;
    comp_wba_update_config_t uc={0};if(!setup(s,c,false))return false;
    /* A reset may occur after the boot candidate is durable but before the
     * service advances its ACTIVATING checkpoint to COMPLETE. The new trial
     * application must still be able to hash and confirm itself. Clear only an
     * exact checkpoint for the exact authenticated boot candidate; a mismatch
     * remains fail-closed. */
    if(s->installer.loaded&&s->installer.record.phase==COMP_WBA_BOOT_AWAIT_CONFIRM&&
       s->metadata.loaded&&s->metadata.record.checkpoint_valid){
        const comp_wba_update_checkpoint_t *cp=&s->metadata.record.checkpoint;
        const comp_wba_boot_record_t *br=&s->installer.record;
        if((cp->state!=COMP_WBA_UPDATE_ACTIVATING&&cp->state!=COMP_WBA_UPDATE_COMPLETE)||
           memcmp(&cp->manifest,&br->candidate,sizeof(cp->manifest))!=0||
           cp->auth_length!=br->auth_length||
           memcmp(cp->auth,br->authentication,cp->auth_length)!=0||!checkpoint_clear(s))return false;
    }
    firmware_floor=c->current_firmware_version;ui_floor=c->current_ui_version;
    if(s->installer.loaded){
        if(s->installer.record.installed_firmware_version>firmware_floor)
            firmware_floor=s->installer.record.installed_firmware_version;
        if(s->installer.record.installed_ui_version>ui_floor)
            ui_floor=s->installer.record.installed_ui_version;
    }
    uc.ports=(comp_wba_update_ports_t){idle,authorize,staging_begin,staging_write,staging_read,staging_abort,activate,checkpoint_load,checkpoint_store,checkpoint_clear,s};
    uc.target_family=COMP_WBA_UPDATE_TARGET_FAMILY_STM32WBA;uc.board_target=COMP_WBA_UPDATE_BOARD_COMPANION_V11;
    uc.current_firmware_version=firmware_floor;uc.current_ui_version=ui_floor;uc.current_app_version=c->current_app_version;
    uc.staging_capacity=COMP_WBA_NOR_UPDATE_STAGING_BYTES;uc.maximum_chunk_bytes=c->maximum_chunk_bytes;uc.default_window_chunks=c->default_window_chunks;
    return comp_wba_update_init(&s->service,&uc);
}
bool comp_v11_update_storage_open_wire(comp_v11_update_storage_t*s,const uint8_t*w,size_t n)
{uint32_t crc;bool trial=s&&s->installer.loaded&&
    (s->installer.record.phase==COMP_WBA_BOOT_CANDIDATE_READY||
     s->installer.record.phase==COMP_WBA_BOOT_BACKUP_VALID||
     s->installer.record.phase==COMP_WBA_BOOT_INSTALLING||
     s->installer.record.phase==COMP_WBA_BOOT_TRIAL_READY||
     s->installer.record.phase==COMP_WBA_BOOT_AWAIT_CONFIRM||
     s->installer.record.phase==COMP_WBA_BOOT_ROLLBACK);
 if(!s||!s->ready||trial||!comp_wba_update_open_wire(&s->service,w,n,s->trust.key_id)){if(s)s->manifest_accepted=false;return false;}crc=comp_wba_update_wire_crc32(w,140u);memcpy(s->manifest_receipt,"WMA1",4u);s->manifest_receipt[4]=(uint8_t)crc;s->manifest_receipt[5]=(uint8_t)(crc>>8);s->manifest_receipt[6]=(uint8_t)(crc>>16);s->manifest_receipt[7]=(uint8_t)(crc>>24);s->manifest_accepted=true;return true;}
size_t comp_v11_update_storage_manifest_receipt(const comp_v11_update_storage_t*s,uint8_t*out,size_t n)
{if(!s||!s->manifest_accepted||!out||n<sizeof(s->manifest_receipt))return 0u;memcpy(out,s->manifest_receipt,sizeof(s->manifest_receipt));return sizeof(s->manifest_receipt);}
bool comp_v11_update_storage_control(comp_v11_update_storage_t*s,const uint8_t*p,size_t n){return s&&s->ready&&s->manifest_accepted&&comp_wba_update_control(&s->service,p,n);}
bool comp_v11_update_storage_data(comp_v11_update_storage_t*s,const uint8_t*p,size_t n){return s&&s->ready&&s->manifest_accepted&&comp_wba_update_data(&s->service,p,n);}
size_t comp_v11_update_storage_transfer_status(const comp_v11_update_storage_t*s,uint8_t*out,size_t n){return s?comp_wba_update_transfer_status(&s->service,out,n):0u;}
bool comp_v11_update_storage_poll(comp_v11_update_storage_t*s,uint8_t*scratch,size_t n)
{
    uint32_t left;size_t chunk;uint8_t digest[32];bool service_ok;
    if(!s||!s->ready)return false;
    service_ok=comp_wba_update_poll(&s->service,scratch,n);
    if(!s->confirm_pending)return service_ok;
    if(!scratch||!n){s->confirm_pending=false;s->confirm_failed=true;return false;}
    left=s->installer.record.candidate.size_bytes-s->confirm_offset;chunk=left<n?left:n;
    if(chunk){bool ok=s->installer.record.candidate.target==COMP_WBA_UPDATE_TARGET_FIRMWARE?
        flash_read(s,s->config.flash_base+COMP_WBA_BOOT_APP_OFFSET+s->confirm_offset,scratch,chunk):
        nor_read_raw(s,COMP_WBA_NOR_UI_BASE+s->confirm_offset,scratch,chunk);
        if(!ok){s->confirm_pending=false;s->confirm_failed=true;return false;}
        comp_wba_update_sha256_update(&s->installer.verify_hash,scratch,chunk);s->confirm_offset+=(uint32_t)chunk;return true;}
    comp_wba_update_sha256_final(&s->installer.verify_hash,digest);s->confirm_pending=false;
    if(memcmp(digest,s->installer.record.candidate.sha256,32u)!=0||
       !comp_wba_boot_confirm(&s->installer,s->confirm_version,digest)||!workspace_release(s)){s->confirm_failed=true;return false;}
    return true;
}
comp_wba_update_status_t comp_v11_update_storage_status(const comp_v11_update_storage_t*s){return s?comp_wba_update_status(&s->service):(comp_wba_update_status_t){0};}
bool comp_v11_update_storage_request_confirm(comp_v11_update_storage_t*s,uint32_t v)
{if(!s||!s->ready||s->installer.bootloader_context||!s->installer.loaded||s->installer.record.phase!=COMP_WBA_BOOT_AWAIT_CONFIRM||v!=s->installer.record.candidate.component_version)return false;s->confirm_version=v;s->confirm_offset=0u;s->confirm_failed=false;s->confirm_pending=true;comp_wba_update_sha256_init(&s->installer.verify_hash);return true;}
bool comp_v11_update_boot_init(comp_v11_update_storage_t*s,const comp_v11_update_storage_config_t*c){return setup(s,c,true);}
comp_wba_boot_action_t comp_v11_update_boot_poll(comp_v11_update_storage_t*s,uint8_t*scratch,size_t n){return s&&s->ready?comp_wba_boot_poll(&s->installer,scratch,n):COMP_WBA_BOOT_ACTION_RECOVERY;}
