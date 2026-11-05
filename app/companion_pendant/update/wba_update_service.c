#include "wba_update_service.h"
#include "wba_update_manifest_wire.h"

/* Legacy service adapter belongs to the service, not the standalone wire
 * codec used by the minimal resident Boot. */
bool comp_wba_update_open_wire(comp_wba_update_service_t *service,
                               const uint8_t *wire, size_t wire_bytes,
                               uint32_t expected_key_id)
{
    comp_wba_update_manifest_envelope_t envelope;
    if(expected_key_id==0u||
       !comp_wba_update_manifest_wire_decode(wire,wire_bytes,&envelope)||
       envelope.key_id!=expected_key_id)return false;
    return comp_wba_update_open(service,&envelope.manifest,envelope.signature,
                               COMP_WBA_UPDATE_P256_SIGNATURE_BYTES);
}

#include <string.h>

static uint32_t crc32_update(uint32_t crc, const uint8_t *data, size_t length)
{
    for (size_t i = 0u; i < length; ++i) {
        crc ^= data[i];
        for (uint8_t bit = 0u; bit < 8u; ++bit) {
            crc = (crc >> 1u) ^ (UINT32_C(0xEDB88320) &
                                 (uint32_t)-(int32_t)(crc & 1u));
        }
    }
    return crc;
}

uint32_t comp_wba_update_checkpoint_crc32(
    const comp_wba_update_checkpoint_t *checkpoint)
{
    if (checkpoint == NULL) return 0u;
    return crc32_update(UINT32_C(0xFFFFFFFF),
                        (const uint8_t *)checkpoint,
                        offsetof(comp_wba_update_checkpoint_t, crc32)) ^
           UINT32_C(0xFFFFFFFF);
}

bool comp_wba_update_checkpoint_valid(
    const comp_wba_update_checkpoint_t *checkpoint)
{
    return checkpoint != NULL &&
           checkpoint->magic == COMP_WBA_UPDATE_CHECKPOINT_MAGIC &&
           checkpoint->auth_length != 0u &&
           checkpoint->auth_length <= COMP_WBA_UPDATE_AUTH_MAX_BYTES &&
           checkpoint->crc32 == comp_wba_update_checkpoint_crc32(checkpoint);
}

void comp_wba_update_sha256_init(comp_wba_update_sha256_t *hash)
{
    companion_sha256_init(hash);
}

void comp_wba_update_sha256_update(comp_wba_update_sha256_t *hash,
                                   const uint8_t *data, size_t length)
{
    companion_sha256_update(hash, data, length);
}

void comp_wba_update_sha256_final(comp_wba_update_sha256_t *hash,
                                  uint8_t digest[32])
{
    companion_sha256_final(hash, digest);
}

static uint32_t current_version(const comp_wba_update_service_t *service,
                                uint8_t target)
{
    return target == COMP_WBA_UPDATE_TARGET_FIRMWARE
               ? service->config.current_firmware_version
               : service->config.current_ui_version;
}

static bool manifest_valid(const comp_wba_update_service_t *service,
                           const comp_wba_update_manifest_t *manifest)
{
    bool format_valid;
    if (manifest == NULL) return false;
    format_valid = manifest->target == COMP_WBA_UPDATE_TARGET_FIRMWARE
                       ? manifest->format_version ==
                             COMP_WBA_UPDATE_FIRMWARE_FORMAT_RELOCATED_BIN &&
                             manifest->size_bytes <= COMP_WBA_UPDATE_FIRMWARE_MAX_BYTES
                       : manifest->format_version ==
                              COMP_WBA_UPDATE_UI_FORMAT_PARTITION_IMAGE_V1 &&
                             manifest->size_bytes <= COMP_WBA_NOR_UI_BYTES;
    return manifest != NULL &&
           manifest->schema_version == COMP_WBA_UPDATE_MANIFEST_SCHEMA &&
           (manifest->target == COMP_WBA_UPDATE_TARGET_FIRMWARE ||
            manifest->target == COMP_WBA_UPDATE_TARGET_UI_ASSETS) &&
           manifest->target_family == service->config.target_family &&
           manifest->board_target == service->config.board_target &&
           manifest->component_version > current_version(service,manifest->target) &&
           format_valid &&
           manifest->size_bytes != 0u &&
           manifest->size_bytes <= service->config.staging_capacity &&
           manifest->minimum_app_version <= service->config.current_app_version &&
           (manifest->maximum_app_version == 0u ||
            service->config.current_app_version <= manifest->maximum_app_version);
}

static void set_error(comp_wba_update_service_t *service,uint8_t error)
{
    service->state=COMP_WBA_UPDATE_ERROR;
    service->last_error=error;
    service->bootable=false;
    service->installed=false;
    service->pending_reboot=false;
}

static bool store_checkpoint(comp_wba_update_service_t *service,uint8_t state)
{
    comp_wba_update_checkpoint_t cp;
    if(service->config.ports.checkpoint_store==NULL)return true;
    memset(&cp,0,sizeof(cp));cp.magic=COMP_WBA_UPDATE_CHECKPOINT_MAGIC;
    cp.sequence=++service->checkpoint_sequence;cp.state=state;
    cp.auth_length=service->authentication_length;cp.manifest=service->manifest;
    memcpy(cp.auth,service->authentication,cp.auth_length);
    cp.crc32=comp_wba_update_checkpoint_crc32(&cp);
    return service->config.ports.checkpoint_store(service->config.ports.context,&cp);
}

static bool storage_begin(void *context,uint32_t image_size)
{
    comp_wba_update_service_t *service=context;
    if(service->state!=COMP_WBA_UPDATE_AUTHORIZED ||
       image_size!=service->manifest.size_bytes ||
       service->transfer.image_crc32!=service->manifest.crc32 ||
       (service->config.ports.activity_idle!=NULL &&
        !service->config.ports.activity_idle(service->config.ports.context)) ||
       !service->config.ports.staging_begin(service->config.ports.context,image_size))return false;
    comp_wba_update_sha256_init(&service->stream_hash);service->received_bytes=0u;
    service->stream_hash_ready=false;service->state=COMP_WBA_UPDATE_RECEIVING;
    if(!store_checkpoint(service,COMP_WBA_UPDATE_RECEIVING)){set_error(service,COMP_WBA_UPDATE_ERROR_CHECKPOINT);return false;}
    return true;
}

static bool storage_write(void *context,const uint8_t *data,size_t length)
{
    comp_wba_update_service_t *service=context;
    uint32_t offset=service->transfer.bytes_written;
    if(service->state!=COMP_WBA_UPDATE_RECEIVING ||
       !service->config.ports.staging_write(service->config.ports.context,offset,data,length))return false;
    comp_wba_update_sha256_update(&service->stream_hash,data,length);
    service->received_bytes+=(uint32_t)length;
    return true;
}

static bool storage_finish(void *context)
{
    comp_wba_update_service_t *service=context;uint8_t digest[32];
    if(service->state!=COMP_WBA_UPDATE_RECEIVING ||
       service->received_bytes!=service->manifest.size_bytes)return false;
    comp_wba_update_sha256_final(&service->stream_hash,digest);service->stream_hash_ready=true;
    if(memcmp(digest,service->manifest.sha256,sizeof(digest))!=0){set_error(service,COMP_WBA_UPDATE_ERROR_STREAM_HASH);return false;}
    service->verify_offset=0u;comp_wba_update_sha256_init(&service->readback_hash);
    service->state=COMP_WBA_UPDATE_VERIFYING;
    if(!store_checkpoint(service,COMP_WBA_UPDATE_VERIFYING)){
        set_error(service,COMP_WBA_UPDATE_ERROR_CHECKPOINT);return false;
    }
    return true;
}

static void storage_abort(void *context)
{
    comp_wba_update_service_t *service=context;
    if(service->config.ports.staging_abort)service->config.ports.staging_abort(service->config.ports.context);
    service->received_bytes=0u;service->verify_offset=0u;
}

bool comp_wba_update_init(comp_wba_update_service_t *service,
                          const comp_wba_update_config_t *config)
{
    denzic_ota_v1_storage_driver_t driver;
    if(service==NULL||config==NULL||config->target_family==0u||
       config->board_target==0u||config->staging_capacity==0u||
       config->maximum_chunk_bytes==0u||config->ports.authorize_manifest==NULL||
       config->ports.staging_begin==NULL||config->ports.staging_write==NULL||
       config->ports.staging_read==NULL)return false;
    memset(service,0,sizeof(*service));service->config=*config;
    driver=(denzic_ota_v1_storage_driver_t){storage_begin,storage_write,storage_finish,storage_abort};
    denzic_ota_v1_init(&service->transfer,driver,service,
                       config->maximum_chunk_bytes,config->default_window_chunks);
    service->state=COMP_WBA_UPDATE_IDLE;
    if(config->ports.checkpoint_load!=NULL){
        comp_wba_update_checkpoint_t cp;
        if(config->ports.checkpoint_load(config->ports.context,&cp)){
            if(!comp_wba_update_checkpoint_valid(&cp)){set_error(service,COMP_WBA_UPDATE_ERROR_CHECKPOINT);return true;}
            service->checkpoint_sequence=cp.sequence;
            if(cp.state==COMP_WBA_UPDATE_VERIFIED||cp.state==COMP_WBA_UPDATE_ACTIVATING){
                if(!manifest_valid(service,&cp.manifest)||
                   !config->ports.authorize_manifest(config->ports.context,&cp.manifest,cp.auth,cp.auth_length)){
                    set_error(service,COMP_WBA_UPDATE_ERROR_UNTRUSTED);return true;
                }
                service->manifest=cp.manifest;service->authentication_length=cp.auth_length;
                memcpy(service->authentication,cp.auth,cp.auth_length);
                comp_wba_update_sha256_init(&service->readback_hash);service->state=COMP_WBA_UPDATE_VERIFYING;
                return true;
            }
            if(cp.state==COMP_WBA_UPDATE_COMPLETE){
                service->checkpoint_sequence=cp.sequence;
                if(config->ports.checkpoint_clear)
                    (void)config->ports.checkpoint_clear(config->ports.context);
                return true;
            }
            if(config->ports.staging_abort)config->ports.staging_abort(config->ports.context);
            if(config->ports.checkpoint_clear)config->ports.checkpoint_clear(config->ports.context);
            set_error(service,COMP_WBA_UPDATE_ERROR_INTERRUPTED);
        }
    }
    return true;
}

bool comp_wba_update_open(comp_wba_update_service_t *service,
                          const comp_wba_update_manifest_t *manifest,
                          const uint8_t *authentication,uint8_t authentication_length)
{
    if(service!=NULL&&(service->state==COMP_WBA_UPDATE_VERIFYING||
       service->state==COMP_WBA_UPDATE_VERIFIED||service->state==COMP_WBA_UPDATE_ACTIVATING||
       service->state==COMP_WBA_UPDATE_COMPLETE)){service->rejected_packets++;return false;}
    if(service==NULL||manifest==NULL||authentication==NULL||authentication_length==0u||
       authentication_length>COMP_WBA_UPDATE_AUTH_MAX_BYTES){if(service)set_error(service,COMP_WBA_UPDATE_ERROR_ARGUMENT);return false;}
    if(!manifest_valid(service,manifest)){set_error(service,
        (manifest->target_family!=service->config.target_family||manifest->board_target!=service->config.board_target)?COMP_WBA_UPDATE_ERROR_TARGET:COMP_WBA_UPDATE_ERROR_ROLLBACK);return false;}
    if(service->config.ports.activity_idle!=NULL&&!service->config.ports.activity_idle(service->config.ports.context)){set_error(service,COMP_WBA_UPDATE_ERROR_BUSY);return false;}
    if(!service->config.ports.authorize_manifest(service->config.ports.context,manifest,authentication,authentication_length)){set_error(service,COMP_WBA_UPDATE_ERROR_UNTRUSTED);return false;}
    if(service->state==COMP_WBA_UPDATE_RECEIVING){
        if(memcmp(&service->manifest,manifest,sizeof(*manifest))==0&&service->authentication_length==authentication_length&&memcmp(service->authentication,authentication,authentication_length)==0)return true;
        denzic_ota_v1_reset(&service->transfer);storage_abort(service);
    }
    service->manifest=*manifest;memcpy(service->authentication,authentication,authentication_length);
    service->authentication_length=authentication_length;service->last_error=COMP_WBA_UPDATE_ERROR_NONE;
    service->bootable=false;service->installed=false;service->pending_reboot=false;service->state=COMP_WBA_UPDATE_AUTHORIZED;
    denzic_ota_v1_reset(&service->transfer);
    return true;
}

bool comp_wba_update_control(comp_wba_update_service_t *service,
                             const uint8_t *packet,size_t packet_bytes)
{
    bool ok;
    if(service==NULL||packet==NULL)return false;
    if(service->state!=COMP_WBA_UPDATE_AUTHORIZED&&service->state!=COMP_WBA_UPDATE_RECEIVING){service->rejected_packets++;return false;}
    ok=denzic_ota_v1_handle_control(&service->transfer,packet,packet_bytes);
    if(!ok&&service->state!=COMP_WBA_UPDATE_ERROR)service->rejected_packets++;
    return ok;
}

bool comp_wba_update_data(comp_wba_update_service_t *service,
                          const uint8_t *packet,size_t packet_bytes)
{
    bool ok;
    if(service==NULL||service->state!=COMP_WBA_UPDATE_RECEIVING){if(service)service->rejected_packets++;return false;}
    ok=denzic_ota_v1_handle_data(&service->transfer,packet,packet_bytes);
    if(!ok)service->rejected_packets++;
    return ok;
}

size_t comp_wba_update_transfer_status(const comp_wba_update_service_t *service,
                                       uint8_t *output,size_t output_bytes)
{
    size_t written=service?denzic_ota_v1_encode_status(&service->transfer,output,output_bytes):0u;
    if(written==0u)return 0u;
    if(service->state==COMP_WBA_UPDATE_ERROR){output[5]=DENZIC_OTA_V1_STATE_ERROR;output[6]=DENZIC_OTA_V1_ERROR_STORAGE_FINISH;}
    else if(service->state==COMP_WBA_UPDATE_VERIFYING||service->state==COMP_WBA_UPDATE_VERIFIED||service->state==COMP_WBA_UPDATE_ACTIVATING){output[5]=DENZIC_OTA_V1_STATE_ERASING;output[6]=DENZIC_OTA_V1_ERROR_NONE;}
    else if(service->state==COMP_WBA_UPDATE_COMPLETE){output[5]=DENZIC_OTA_V1_STATE_COMPLETE;output[6]=DENZIC_OTA_V1_ERROR_NONE;}
    return written;
}

bool comp_wba_update_poll(comp_wba_update_service_t *service,
                          uint8_t *scratch,size_t scratch_bytes)
{
    if(service==NULL)return false;
    if(service->state==COMP_WBA_UPDATE_VERIFYING){
        uint32_t left=service->manifest.size_bytes-service->verify_offset;
        size_t chunk=left<scratch_bytes?left:scratch_bytes;
        if(scratch==NULL||scratch_bytes==0u){set_error(service,COMP_WBA_UPDATE_ERROR_ARGUMENT);return false;}
        if(chunk!=0u){
            if(!service->config.ports.staging_read(service->config.ports.context,service->verify_offset,scratch,chunk)){set_error(service,COMP_WBA_UPDATE_ERROR_READBACK);return false;}
            comp_wba_update_sha256_update(&service->readback_hash,scratch,chunk);service->verify_offset+=(uint32_t)chunk;return true;
        }
        uint8_t digest[32];comp_wba_update_sha256_final(&service->readback_hash,digest);
        if(memcmp(digest,service->manifest.sha256,sizeof(digest))!=0){set_error(service,COMP_WBA_UPDATE_ERROR_READBACK_HASH);return false;}
        service->state=COMP_WBA_UPDATE_VERIFIED;
        if(!store_checkpoint(service,COMP_WBA_UPDATE_VERIFIED)){set_error(service,COMP_WBA_UPDATE_ERROR_CHECKPOINT);return false;}
        return true;
    }
    if(service->state==COMP_WBA_UPDATE_VERIFIED){
        if(service->config.ports.activate_step==NULL)return true;
        service->state=COMP_WBA_UPDATE_ACTIVATING;
        if(!store_checkpoint(service,COMP_WBA_UPDATE_ACTIVATING)){set_error(service,COMP_WBA_UPDATE_ERROR_CHECKPOINT);return false;}
    }
    if(service->state==COMP_WBA_UPDATE_ACTIVATING){
        comp_wba_update_step_result_t result;
        if(service->config.ports.activity_idle!=NULL&&!service->config.ports.activity_idle(service->config.ports.context))return true;
        result=service->config.ports.activate_step(service->config.ports.context,&service->manifest,
            service->authentication,service->authentication_length,
            COMP_WBA_NOR_UPDATE_STAGING_BASE,service->manifest.size_bytes,scratch,scratch_bytes);
        service->activation_steps++;
        if(result==COMP_WBA_UPDATE_STEP_FAILED){set_error(service,COMP_WBA_UPDATE_ERROR_ACTIVATION);return false;}
        if(result==COMP_WBA_UPDATE_STEP_DONE){
            service->state=COMP_WBA_UPDATE_COMPLETE;
            service->bootable=service->manifest.target==COMP_WBA_UPDATE_TARGET_FIRMWARE;
            service->installed=false;service->pending_reboot=true;
            if(!store_checkpoint(service,COMP_WBA_UPDATE_COMPLETE)){set_error(service,COMP_WBA_UPDATE_ERROR_CHECKPOINT);return false;}
        }
    }
    return service->state!=COMP_WBA_UPDATE_ERROR;
}

void comp_wba_update_abort(comp_wba_update_service_t *service)
{
    if(service==NULL)return;
    if(service->state==COMP_WBA_UPDATE_RECEIVING||service->state==COMP_WBA_UPDATE_VERIFYING||service->state==COMP_WBA_UPDATE_VERIFIED||service->state==COMP_WBA_UPDATE_ACTIVATING)storage_abort(service);
    if(service->config.ports.checkpoint_clear)service->config.ports.checkpoint_clear(service->config.ports.context);
    denzic_ota_v1_reset(&service->transfer);service->state=COMP_WBA_UPDATE_IDLE;
    service->last_error=COMP_WBA_UPDATE_ERROR_NONE;service->bootable=false;service->installed=false;
    service->pending_reboot=false;
}

comp_wba_update_status_t comp_wba_update_status(const comp_wba_update_service_t *service)
{
    comp_wba_update_status_t s={0};if(service==NULL)return s;
    s.state=service->state;s.error=service->last_error;s.target=service->manifest.target;
    s.transfer_state=service->transfer.state;s.received_bytes=service->received_bytes;
    s.expected_bytes=service->manifest.size_bytes;s.verify_offset=service->verify_offset;
    s.component_version=service->manifest.component_version;s.authenticated=service->authentication_length!=0u;
    s.bootable=service->bootable;s.installed=service->installed;s.pending_reboot=service->pending_reboot;return s;
}
