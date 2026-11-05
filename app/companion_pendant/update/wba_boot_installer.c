#include "wba_boot_installer.h"

#include <string.h>

enum { OP_NONE,OP_STAGING_VERIFY,
       OP_BACKUP_ERASE,OP_BACKUP_COPY,OP_BACKUP_VERIFY,
       OP_INSTALL_ERASE,OP_INSTALL_COPY,OP_INSTALL_VERIFY,
       OP_RESTORE_ERASE,OP_RESTORE_COPY,OP_RESTORE_VERIFY,
       OP_RESOURCE_BACKUP_ERASE,OP_RESOURCE_BACKUP_COPY,OP_RESOURCE_BACKUP_VERIFY,
       OP_RESOURCE_INSTALL_ERASE,OP_RESOURCE_INSTALL_COPY,OP_RESOURCE_INSTALL_VERIFY,
       OP_RESOURCE_RESTORE_ERASE,OP_RESOURCE_RESTORE_COPY,OP_RESOURCE_RESTORE_VERIFY };

static uint32_t crc32_update(uint32_t crc,const uint8_t *data,size_t length)
{
    while(length--){crc^=*data++;for(uint8_t b=0u;b<8u;++b)
        crc=(crc>>1u)^(UINT32_C(0xEDB88320)&(uint32_t)-(int32_t)(crc&1u));}
    return crc;
}
static uint32_t record_crc(const comp_wba_boot_record_t *r)
{return crc32_update(UINT32_C(0xFFFFFFFF),(const uint8_t*)r,offsetof(comp_wba_boot_record_t,crc32))^UINT32_C(0xFFFFFFFF);}
bool comp_wba_boot_record_valid(const comp_wba_boot_record_t *r)
{return r&&r->magic==COMP_WBA_BOOT_RECORD_MAGIC&&r->auth_length&&r->auth_length<=COMP_WBA_UPDATE_AUTH_MAX_BYTES&&r->crc32==record_crc(r);}

static bool store(comp_wba_boot_installer_t *i,uint8_t phase)
{
    comp_wba_boot_record_t previous=i->record;
    i->record.magic=COMP_WBA_BOOT_RECORD_MAGIC;i->record.phase=phase;
    i->record.sequence++;i->record.crc32=record_crc(&i->record);
    if(i->config.ports.metadata_store(i->config.ports.context,&i->record))return true;
    i->record=previous;return false;
}

static bool candidate_valid(comp_wba_boot_installer_t *i,
                            const comp_wba_update_manifest_t *m,
                            const uint8_t *auth,uint8_t auth_length,
                            uint32_t installed_component_version,
                            uint32_t compatible_app_version,
                            bool allow_installed_version,
                            bool require_staging_vector)
{
    uint8_t vector[8];uint32_t sp,reset,app_base=i->config.flash_base+COMP_WBA_BOOT_APP_OFFSET;
    if(!m||m->schema_version!=COMP_WBA_UPDATE_MANIFEST_SCHEMA||
       (m->target!=COMP_WBA_UPDATE_TARGET_FIRMWARE&&m->target!=COMP_WBA_UPDATE_TARGET_UI_ASSETS)||
       m->target_family!=i->config.target_family||m->board_target!=i->config.board_target||
       (allow_installed_version?m->component_version!=installed_component_version:
                                m->component_version<=installed_component_version)||
       m->minimum_app_version>compatible_app_version||
       (m->maximum_app_version!=0u&&compatible_app_version>m->maximum_app_version)||
       m->size_bytes<8u||m->size_bytes>COMP_WBA_NOR_UPDATE_STAGING_BYTES||
       !auth||!auth_length||
       !i->config.ports.authorize_manifest(i->config.ports.context,m,auth,auth_length))return false;
    if(m->target==COMP_WBA_UPDATE_TARGET_UI_ASSETS)
        return m->format_version==COMP_WBA_UPDATE_UI_FORMAT_PARTITION_IMAGE_V1&&
               m->size_bytes<=COMP_WBA_NOR_UI_BYTES;
    if(m->format_version!=COMP_WBA_UPDATE_FIRMWARE_FORMAT_RELOCATED_BIN||
       m->size_bytes>COMP_WBA_BOOT_APP_CAPACITY)return false;
    if(!require_staging_vector)return true;
    if(
       !i->config.ports.nor_read(i->config.ports.context,COMP_WBA_NOR_UPDATE_STAGING_BASE,vector,sizeof(vector)))return false;
    sp=(uint32_t)vector[0]|((uint32_t)vector[1]<<8)|((uint32_t)vector[2]<<16)|((uint32_t)vector[3]<<24);
    reset=(uint32_t)vector[4]|((uint32_t)vector[5]<<8)|((uint32_t)vector[6]<<16)|((uint32_t)vector[7]<<24);
    return sp>=i->config.sram_base&&sp<=i->config.sram_base+i->config.sram_bytes&&
           (reset&1u)!=0u&&(reset&~1u)>=app_base&&
           (reset&~1u)<app_base+m->size_bytes;
}

static void start_op(comp_wba_boot_installer_t *i,uint8_t op)
{
    i->operation=op;i->cursor=0u;
    comp_wba_update_sha256_init(&i->verify_hash);
}

bool comp_wba_boot_init(comp_wba_boot_installer_t *i,
                        const comp_wba_boot_config_t *c,bool bootloader_context)
{
    if(!i||!c||!c->ports.authorize_manifest||!c->ports.nor_read||
       !c->ports.nor_erase_4k||!c->ports.nor_write||!c->ports.flash_read||
       !c->ports.flash_erase_page||!c->ports.flash_write||
       !c->ports.metadata_load||!c->ports.metadata_store||!c->target_family||
       !c->board_target||!c->flash_base||!c->flash_page_bytes||!c->sram_bytes||
       c->installed_image_size>COMP_WBA_BOOT_APP_CAPACITY)return false;
    memset(i,0,sizeof(*i));i->config=*c;i->bootloader_context=bootloader_context;
    if(!c->ports.metadata_load(c->ports.context,&i->record)){
        if(bootloader_context)i->action=COMP_WBA_BOOT_ACTION_BOOT_APP;
        return true;
    }
    if(!comp_wba_boot_record_valid(&i->record)||
       !candidate_valid(i,&i->record.candidate,i->record.authentication,
                        i->record.auth_length,
                        i->record.candidate.target==COMP_WBA_UPDATE_TARGET_FIRMWARE?
                            i->record.installed_firmware_version:i->record.installed_ui_version,
                        i->record.phase==COMP_WBA_BOOT_CONFIRMED&&
                            i->record.candidate.target==COMP_WBA_UPDATE_TARGET_FIRMWARE?
                                i->record.previous_version:i->record.installed_firmware_version,
                        i->record.phase==COMP_WBA_BOOT_CONFIRMED,
                        i->record.phase==COMP_WBA_BOOT_CANDIDATE_READY||
                        i->record.phase==COMP_WBA_BOOT_BACKUP_VALID||
                        i->record.phase==COMP_WBA_BOOT_INSTALLING)){
        i->action=COMP_WBA_BOOT_ACTION_RECOVERY;return true;
    }
    i->loaded=true;
    if(!bootloader_context)return true;
    switch(i->record.phase){
    case COMP_WBA_BOOT_CANDIDATE_READY:start_op(i,OP_STAGING_VERIFY);break;
    case COMP_WBA_BOOT_BACKUP_VALID:
        if(store(i,COMP_WBA_BOOT_INSTALLING))start_op(i,i->record.candidate.target==COMP_WBA_UPDATE_TARGET_FIRMWARE?OP_INSTALL_ERASE:OP_RESOURCE_INSTALL_ERASE);else i->action=COMP_WBA_BOOT_ACTION_RECOVERY;break;
    case COMP_WBA_BOOT_INSTALLING:start_op(i,i->record.candidate.target==COMP_WBA_UPDATE_TARGET_FIRMWARE?OP_INSTALL_ERASE:OP_RESOURCE_INSTALL_ERASE);break;
    case COMP_WBA_BOOT_TRIAL_READY:
        i->action=store(i,COMP_WBA_BOOT_AWAIT_CONFIRM)?COMP_WBA_BOOT_ACTION_BOOT_APP:COMP_WBA_BOOT_ACTION_RECOVERY;break;
    case COMP_WBA_BOOT_AWAIT_CONFIRM:
        if(store(i,COMP_WBA_BOOT_ROLLBACK))start_op(i,i->record.candidate.target==COMP_WBA_UPDATE_TARGET_FIRMWARE?OP_RESTORE_ERASE:OP_RESOURCE_RESTORE_ERASE);else i->action=COMP_WBA_BOOT_ACTION_RECOVERY;break;
    case COMP_WBA_BOOT_ROLLBACK:start_op(i,i->record.candidate.target==COMP_WBA_UPDATE_TARGET_FIRMWARE?OP_RESTORE_ERASE:OP_RESOURCE_RESTORE_ERASE);break;
    case COMP_WBA_BOOT_CONFIRMED:case COMP_WBA_BOOT_ROLLED_BACK:i->action=COMP_WBA_BOOT_ACTION_BOOT_APP;break;
    default:i->action=COMP_WBA_BOOT_ACTION_RECOVERY;break;
    }
    return true;
}

comp_wba_update_step_result_t comp_wba_boot_activate_step(
    void *context,const comp_wba_update_manifest_t *m,
    const uint8_t *auth,uint8_t auth_length,uint32_t staging_offset,
    uint32_t size,uint8_t *scratch,size_t scratch_bytes)
{
    comp_wba_boot_installer_t *i=context;uint32_t installed_firmware,installed_ui;
    comp_wba_boot_record_t previous_record;
    (void)scratch;(void)scratch_bytes;
    if(!i)return COMP_WBA_UPDATE_STEP_FAILED;
    installed_firmware=i->config.installed_version;
    installed_ui=i->config.installed_ui_version;
    if(i->loaded){
        if(i->record.installed_firmware_version>installed_firmware)
            installed_firmware=i->record.installed_firmware_version;
        if(i->record.installed_ui_version>installed_ui)
            installed_ui=i->record.installed_ui_version;
    }
    if(!i||!m||staging_offset!=COMP_WBA_NOR_UPDATE_STAGING_BASE||size!=m->size_bytes||
       auth_length>COMP_WBA_UPDATE_AUTH_MAX_BYTES||!candidate_valid(i,m,auth,auth_length,
       m->target==COMP_WBA_UPDATE_TARGET_FIRMWARE?installed_firmware:installed_ui,
       installed_firmware,false,true))return COMP_WBA_UPDATE_STEP_FAILED;
    previous_record=i->record;
    memset(&i->record,0,sizeof(i->record));i->record.candidate=*m;
    i->record.auth_length=auth_length;memcpy(i->record.authentication,auth,auth_length);
    i->record.installed_firmware_version=installed_firmware;
    i->record.installed_ui_version=installed_ui;
    i->record.previous_version=m->target==COMP_WBA_UPDATE_TARGET_FIRMWARE?
                                   installed_firmware:installed_ui;
    i->record.previous_size=m->target==COMP_WBA_UPDATE_TARGET_FIRMWARE?
                                i->config.installed_image_size:
                                COMP_WBA_NOR_UI_BYTES;
    if(store(i,COMP_WBA_BOOT_CANDIDATE_READY))return COMP_WBA_UPDATE_STEP_DONE;
    i->record=previous_record;return COMP_WBA_UPDATE_STEP_FAILED;
}

static bool erase_step(comp_wba_boot_installer_t *i,bool nor,uint32_t base,
                       uint32_t bytes,uint32_t unit,uint8_t next)
{
    if(i->cursor>=bytes){start_op(i,next);return true;}
    bool ok=nor?i->config.ports.nor_erase_4k(i->config.ports.context,base+i->cursor):
                 i->config.ports.flash_erase_page(i->config.ports.context,base+i->cursor);
    if(ok)i->cursor+=unit;
    return ok;
}

static bool copy_step(comp_wba_boot_installer_t *i,bool source_nor,bool destination_nor,uint32_t source,
                      uint32_t destination,uint32_t bytes,uint8_t next,
                      uint8_t *scratch,size_t capacity)
{
    if(i->cursor>=bytes){
        /* Preserve the completed rollback-source digest before reusing the
         * same hash state for destination readback. Firmware/resource backups
         * both need it; install/restore digests are checked against metadata. */
        if(next==OP_BACKUP_VERIFY || next==OP_RESOURCE_BACKUP_VERIFY)
            comp_wba_update_sha256_final(&i->source_hash,i->record.previous_sha256);
        i->operation=next;i->cursor=0u;
        comp_wba_update_sha256_init(&i->verify_hash);
        return true;
    }
    size_t n=bytes-i->cursor<capacity?bytes-i->cursor:capacity;
    if(!destination_nor&&bytes-i->cursor>n){n&=~(size_t)15u;if(n==0u)return false;}
    bool ok=source_nor?i->config.ports.nor_read(i->config.ports.context,source+i->cursor,scratch,n):
                       i->config.ports.flash_read(i->config.ports.context,source+i->cursor,scratch,n);
    if(ok)ok=destination_nor?i->config.ports.nor_write(i->config.ports.context,destination+i->cursor,scratch,n):
                              i->config.ports.flash_write(i->config.ports.context,destination+i->cursor,scratch,n);
    if(ok){comp_wba_update_sha256_update(&i->source_hash,scratch,n);i->cursor+=(uint32_t)n;}
    return ok;
}

static bool verify_step(comp_wba_boot_installer_t *i,bool nor,uint32_t base,
                        uint32_t bytes,const uint8_t expected[32],uint8_t next,
                        uint8_t *scratch,size_t capacity)
{
    if(i->cursor<bytes){size_t n=bytes-i->cursor<capacity?bytes-i->cursor:capacity;
        bool ok=nor?i->config.ports.nor_read(i->config.ports.context,base+i->cursor,scratch,n):
                    i->config.ports.flash_read(i->config.ports.context,base+i->cursor,scratch,n);
        if(ok){comp_wba_update_sha256_update(&i->verify_hash,scratch,n);i->cursor+=(uint32_t)n;}return ok;}
    uint8_t digest[32];comp_wba_update_sha256_final(&i->verify_hash,digest);
    if(memcmp(digest,expected,32u)!=0)return false;
    start_op(i,next);
    return true;
}

comp_wba_boot_action_t comp_wba_boot_poll(comp_wba_boot_installer_t *i,
                                          uint8_t *scratch,size_t capacity)
{
    uint32_t app=i->config.flash_base+COMP_WBA_BOOT_APP_OFFSET;bool ok=true;
    if(!i||!i->bootloader_context||!scratch||!capacity)return COMP_WBA_BOOT_ACTION_RECOVERY;
    if(i->action!=COMP_WBA_BOOT_ACTION_NONE)return (comp_wba_boot_action_t)i->action;
    switch(i->operation){
    case OP_STAGING_VERIFY:ok=verify_step(i,true,COMP_WBA_NOR_UPDATE_STAGING_BASE,i->record.candidate.size_bytes,i->record.candidate.sha256,OP_NONE,scratch,capacity);if(ok&&i->operation==OP_NONE)start_op(i,i->record.candidate.target==COMP_WBA_UPDATE_TARGET_FIRMWARE?OP_BACKUP_ERASE:OP_RESOURCE_BACKUP_ERASE);break;
    case OP_BACKUP_ERASE:ok=erase_step(i,true,COMP_WBA_NOR_ROLLBACK_BASE,i->record.previous_size,4096u,OP_BACKUP_COPY);break;
    case OP_BACKUP_COPY:ok=copy_step(i,false,true,app,COMP_WBA_NOR_ROLLBACK_BASE,i->record.previous_size,OP_BACKUP_VERIFY,scratch,capacity);break;
    case OP_BACKUP_VERIFY:ok=verify_step(i,true,COMP_WBA_NOR_ROLLBACK_BASE,i->record.previous_size,i->record.previous_sha256,OP_NONE,scratch,capacity);if(ok&&i->operation==OP_NONE){if(store(i,COMP_WBA_BOOT_BACKUP_VALID)&&store(i,COMP_WBA_BOOT_INSTALLING))start_op(i,OP_INSTALL_ERASE);else i->action=COMP_WBA_BOOT_ACTION_RECOVERY;}break;
    case OP_INSTALL_ERASE:ok=erase_step(i,false,app,i->record.candidate.size_bytes,i->config.flash_page_bytes,OP_INSTALL_COPY);break;
    case OP_INSTALL_COPY:ok=copy_step(i,true,false,COMP_WBA_NOR_UPDATE_STAGING_BASE,app,i->record.candidate.size_bytes,OP_INSTALL_VERIFY,scratch,capacity);break;
    case OP_INSTALL_VERIFY:ok=verify_step(i,false,app,i->record.candidate.size_bytes,i->record.candidate.sha256,OP_NONE,scratch,capacity);if(ok&&i->operation==OP_NONE)i->action=store(i,COMP_WBA_BOOT_TRIAL_READY)&&store(i,COMP_WBA_BOOT_AWAIT_CONFIRM)?COMP_WBA_BOOT_ACTION_BOOT_APP:COMP_WBA_BOOT_ACTION_RECOVERY;break;
    case OP_RESTORE_ERASE:ok=erase_step(i,false,app,i->record.previous_size,i->config.flash_page_bytes,OP_RESTORE_COPY);break;
    case OP_RESTORE_COPY:ok=copy_step(i,true,false,COMP_WBA_NOR_ROLLBACK_BASE,app,i->record.previous_size,OP_RESTORE_VERIFY,scratch,capacity);break;
    case OP_RESTORE_VERIFY:ok=verify_step(i,false,app,i->record.previous_size,i->record.previous_sha256,OP_NONE,scratch,capacity);if(ok&&i->operation==OP_NONE)i->action=store(i,COMP_WBA_BOOT_ROLLED_BACK)?COMP_WBA_BOOT_ACTION_BOOT_APP:COMP_WBA_BOOT_ACTION_RECOVERY;break;
    case OP_RESOURCE_BACKUP_ERASE:ok=erase_step(i,true,COMP_WBA_NOR_RESOURCE_BACKUP_BASE,COMP_WBA_NOR_UI_BYTES,COMP_WBA_NOR_SECTOR_BYTES,OP_RESOURCE_BACKUP_COPY);break;
    case OP_RESOURCE_BACKUP_COPY:ok=copy_step(i,true,true,COMP_WBA_NOR_UI_BASE,COMP_WBA_NOR_RESOURCE_BACKUP_BASE,COMP_WBA_NOR_UI_BYTES,OP_RESOURCE_BACKUP_VERIFY,scratch,capacity);break;
    case OP_RESOURCE_BACKUP_VERIFY:ok=verify_step(i,true,COMP_WBA_NOR_RESOURCE_BACKUP_BASE,COMP_WBA_NOR_UI_BYTES,i->record.previous_sha256,OP_NONE,scratch,capacity);if(ok&&i->operation==OP_NONE){if(store(i,COMP_WBA_BOOT_BACKUP_VALID)&&store(i,COMP_WBA_BOOT_INSTALLING))start_op(i,OP_RESOURCE_INSTALL_ERASE);else i->action=COMP_WBA_BOOT_ACTION_RECOVERY;}break;
    case OP_RESOURCE_INSTALL_ERASE:ok=erase_step(i,true,COMP_WBA_NOR_UI_BASE,COMP_WBA_NOR_UI_BYTES,COMP_WBA_NOR_SECTOR_BYTES,OP_RESOURCE_INSTALL_COPY);break;
    case OP_RESOURCE_INSTALL_COPY:ok=copy_step(i,true,true,COMP_WBA_NOR_UPDATE_STAGING_BASE,COMP_WBA_NOR_UI_BASE,i->record.candidate.size_bytes,OP_RESOURCE_INSTALL_VERIFY,scratch,capacity);break;
    case OP_RESOURCE_INSTALL_VERIFY:ok=verify_step(i,true,COMP_WBA_NOR_UI_BASE,i->record.candidate.size_bytes,i->record.candidate.sha256,OP_NONE,scratch,capacity);if(ok&&i->operation==OP_NONE)i->action=store(i,COMP_WBA_BOOT_TRIAL_READY)&&store(i,COMP_WBA_BOOT_AWAIT_CONFIRM)?COMP_WBA_BOOT_ACTION_BOOT_APP:COMP_WBA_BOOT_ACTION_RECOVERY;break;
    case OP_RESOURCE_RESTORE_ERASE:ok=erase_step(i,true,COMP_WBA_NOR_UI_BASE,COMP_WBA_NOR_UI_BYTES,COMP_WBA_NOR_SECTOR_BYTES,OP_RESOURCE_RESTORE_COPY);break;
    case OP_RESOURCE_RESTORE_COPY:ok=copy_step(i,true,true,COMP_WBA_NOR_RESOURCE_BACKUP_BASE,COMP_WBA_NOR_UI_BASE,COMP_WBA_NOR_UI_BYTES,OP_RESOURCE_RESTORE_VERIFY,scratch,capacity);break;
    case OP_RESOURCE_RESTORE_VERIFY:ok=verify_step(i,true,COMP_WBA_NOR_UI_BASE,COMP_WBA_NOR_UI_BYTES,i->record.previous_sha256,OP_NONE,scratch,capacity);if(ok&&i->operation==OP_NONE)i->action=store(i,COMP_WBA_BOOT_ROLLED_BACK)?COMP_WBA_BOOT_ACTION_BOOT_APP:COMP_WBA_BOOT_ACTION_RECOVERY;break;
    default:i->action=COMP_WBA_BOOT_ACTION_RECOVERY;return COMP_WBA_BOOT_ACTION_RECOVERY;
    }
    if(!ok){
        if((i->operation==OP_INSTALL_ERASE||i->operation==OP_INSTALL_COPY||i->operation==OP_INSTALL_VERIFY||i->operation==OP_RESOURCE_INSTALL_ERASE||i->operation==OP_RESOURCE_INSTALL_COPY||i->operation==OP_RESOURCE_INSTALL_VERIFY)&&i->record.previous_size&&store(i,COMP_WBA_BOOT_ROLLBACK))start_op(i,i->record.candidate.target==COMP_WBA_UPDATE_TARGET_FIRMWARE?OP_RESTORE_ERASE:OP_RESOURCE_RESTORE_ERASE);
        else {store(i,COMP_WBA_BOOT_FAILED);i->action=COMP_WBA_BOOT_ACTION_RECOVERY;}
    }
    return i->action?(comp_wba_boot_action_t)i->action:COMP_WBA_BOOT_ACTION_WORK;
}

bool comp_wba_boot_confirm(comp_wba_boot_installer_t *i,uint32_t version,
                           const uint8_t sha[32])
{
    comp_wba_boot_record_t previous;
    if(!i||i->bootloader_context||!i->loaded||
       i->record.phase!=COMP_WBA_BOOT_AWAIT_CONFIRM||!sha||
       version!=i->record.candidate.component_version||
       memcmp(sha,i->record.candidate.sha256,32u)!=0)return false;
    previous=i->record;
    if(i->record.candidate.target==COMP_WBA_UPDATE_TARGET_FIRMWARE)
        i->record.installed_firmware_version=version;
    else i->record.installed_ui_version=version;
    if(store(i,COMP_WBA_BOOT_CONFIRMED))return true;
    i->record=previous;return false;
}
