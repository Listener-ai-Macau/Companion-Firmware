#include "update_storage.h"
#include "wba_workspace_layout.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FLASH_BASE_TEST UINT32_C(0x08000000)
#define FLASH_BYTES COMP_WBA_INTERNAL_FLASH_BYTES
#define PAGE_BYTES UINT32_C(0x00002000)
#define IMAGE_BYTES UINT32_C(0x00003000)

typedef struct {
    uint8_t *nor,*flash;
    uint32_t protected_end,claimed_bytes,fail_read_address;
    bool fail_commit_readback,fail_release;
} fixture_t;

static void require(bool ok,const char *message)
{if(!ok){fprintf(stderr,"FAIL: %s\n",message);exit(1);}}

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_read(
    companion_spi_nor_stm32wba_t *nor,uint32_t address,uint8_t *data,size_t length)
{fixture_t*f=nor?(fixture_t*)nor->config.context:NULL;if(!f||address>COMP_WBA_NOR_TOTAL_BYTES||length>COMP_WBA_NOR_TOTAL_BYTES-address)return COMPANION_SPI_NOR_STM32WBA_ERROR;if(f->fail_read_address==address&&address){f->fail_read_address=0u;return COMPANION_SPI_NOR_STM32WBA_ERROR;}memcpy(data,f->nor+address,length);return COMPANION_SPI_NOR_STM32WBA_OK;}
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_program(
    companion_spi_nor_stm32wba_t *nor,uint32_t address,const uint8_t *data,size_t length)
{fixture_t*f=nor?(fixture_t*)nor->config.context:NULL;if(!f||address>COMP_WBA_NOR_TOTAL_BYTES||length>COMP_WBA_NOR_TOTAL_BYTES-address)return COMPANION_SPI_NOR_STM32WBA_ERROR;for(size_t i=0;i<length;++i)f->nor[address+i]&=data[i];if(f->fail_commit_readback&&(address==COMP_WBA_NOR_UPDATE_META_A||address==COMP_WBA_NOR_UPDATE_META_B)){f->fail_commit_readback=false;f->fail_read_address=address;}return COMPANION_SPI_NOR_STM32WBA_OK;}
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_4k(
    companion_spi_nor_stm32wba_t *nor,uint32_t address)
{fixture_t*f=nor?(fixture_t*)nor->config.context:NULL;if(!f||(address%4096u)||address>COMP_WBA_NOR_TOTAL_BYTES-4096u)return COMPANION_SPI_NOR_STM32WBA_ERROR;memset(f->nor+address,0xff,4096u);return COMPANION_SPI_NOR_STM32WBA_OK;}

bool comp_wba_update_p256_trust_configured(const comp_wba_update_p256_trust_t *trust)
{return trust&&trust->key_id&&trust->public_key_xy&&trust->verify_digest;}
bool comp_wba_update_p256_authorize_manifest(const comp_wba_update_p256_trust_t *trust,
    const comp_wba_update_manifest_t *manifest,const uint8_t *authentication,uint8_t authentication_length)
{return comp_wba_update_p256_trust_configured(trust)&&manifest&&authentication&&authentication_length==64u;}
bool comp_wba_update_p256_hal_verify_digest(void *context,const uint8_t public_key_xy[64],
    const uint8_t digest[32],const uint8_t signature_rs[64])
{return context&&public_key_xy&&digest&&signature_rs;}

static bool acquire(void*context){return context!=NULL;}
static void release_pka(void*context){(void)context;}
static bool idle(void*context){return context!=NULL;}
static bool reserve(void *context,uint32_t bytes,uint32_t *base)
{
    fixture_t *f=context;
    if(!bytes&&f->fail_release){f->fail_release=false;return false;}
    if(bytes>COMP_WBA_NOR_RECORDING_DATA_BYTES||bytes%4096u||
       f->protected_end>COMP_WBA_NOR_TOTAL_BYTES-bytes)return false;
    f->claimed_bytes=bytes;*base=bytes?COMP_WBA_NOR_TOTAL_BYTES-bytes:0u;return true;
}
static bool flash_read(void*context,uint32_t address,uint8_t*data,size_t length)
{fixture_t*f=context;if(address<FLASH_BASE_TEST||address-FLASH_BASE_TEST>FLASH_BYTES||length>FLASH_BYTES-(address-FLASH_BASE_TEST))return false;memcpy(data,f->flash+address-FLASH_BASE_TEST,length);return true;}
static bool flash_erase(void*context,uint32_t address)
{fixture_t*f=context;if(address<FLASH_BASE_TEST||(address-FLASH_BASE_TEST)%PAGE_BYTES||address-FLASH_BASE_TEST>FLASH_BYTES-PAGE_BYTES)return false;memset(f->flash+address-FLASH_BASE_TEST,0xff,PAGE_BYTES);return true;}
static bool flash_write(void*context,uint32_t address,const uint8_t*data,size_t length)
{fixture_t*f=context;if(address<FLASH_BASE_TEST||address-FLASH_BASE_TEST>FLASH_BYTES||length>FLASH_BYTES-(address-FLASH_BASE_TEST))return false;for(size_t i=0;i<length;++i)f->flash[address-FLASH_BASE_TEST+i]&=data[i];return true;}
static void put32(uint8_t*p,uint32_t v){p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);p[2]=(uint8_t)(v>>16);p[3]=(uint8_t)(v>>24);}
static void digest(const uint8_t*d,size_t n,uint8_t out[32]){comp_wba_update_sha256_t h;comp_wba_update_sha256_init(&h);comp_wba_update_sha256_update(&h,d,n);comp_wba_update_sha256_final(&h,out);}

static comp_v11_update_storage_config_t config(fixture_t*f,companion_spi_nor_stm32wba_t*n,PKA_HandleTypeDef*pka)
{
    static const uint8_t key[64]={1u};comp_v11_update_storage_config_t c={0};
    memset(n,0,sizeof(*n));n->config.context=f;n->probed=true;n->info.size_bytes=COMP_WBA_NOR_TOTAL_BYTES;
    c.nor=n;c.hpka=pka;c.pka_acquire=acquire;c.pka_release=release_pka;c.activity_idle=idle;
    c.flash_read=flash_read;c.flash_erase_page=flash_erase;c.flash_write=flash_write;c.context=f;
    c.workspace_reserve=reserve;
    c.public_key_xy=key;c.key_id=3u;c.pka_timeout_ms=250u;c.current_firmware_version=7u;
    c.current_ui_version=21u;c.current_app_version=7u;c.installed_image_size=0x2000u;
    c.flash_base=FLASH_BASE_TEST;c.flash_page_bytes=PAGE_BYTES;c.sram_base=0x20000000u;c.sram_bytes=0x20000u;
    c.maximum_chunk_bytes=240u;c.default_window_chunks=8u;return c;
}

static void prepare(fixture_t*f,uint8_t candidate[IMAGE_BYTES])
{
    f->nor=malloc(COMP_WBA_NOR_TOTAL_BYTES);f->flash=malloc(FLASH_BYTES);require(f->nor&&f->flash,"allocate fixture");
    memset(f->nor,0xff,COMP_WBA_NOR_TOTAL_BYTES);memset(f->flash,0xa5,FLASH_BYTES);
    for(uint32_t i=0;i<IMAGE_BYTES;++i)candidate[i]=(uint8_t)(i*19u+5u);
    put32(candidate,0x20010000u);put32(candidate+4u,FLASH_BASE_TEST+COMP_WBA_BOOT_APP_OFFSET+0x101u);
    uint8_t root[64]={0};memcpy(root,"CFL3",4u);put32(root+4u,3u);put32(root+8u,64u);
    put32(root+12u,COMP_WBA_NOR_UI_BYTES);put32(root+16u,COMP_WBA_NOR_DYNAMIC_BASE);
    put32(root+20u,COMP_WBA_NOR_RECORDING_CATALOG);put32(root+24u,COMP_WBA_NOR_RECORDING_BASE);
    put32(root+28u,COMP_WBA_NOR_RECORDING_DATA_BYTES);put32(root+60u,comp_wba_update_wire_crc32(root,60u));
    memcpy(f->nor+COMP_WBA_NOR_LAYOUT_A,root,sizeof(root));memcpy(f->nor+COMP_WBA_NOR_LAYOUT_B,root,sizeof(root));
    f->protected_end=COMP_WBA_NOR_RECORDING_BASE;
}
static void release_fixture(fixture_t*f){free(f->nor);free(f->flash);}
static bool meta_read(void*context,uint32_t offset,uint8_t*data,size_t length)
{fixture_t*f=context;if(offset>COMP_WBA_NOR_TOTAL_BYTES||length>COMP_WBA_NOR_TOTAL_BYTES-offset)return false;memcpy(data,f->nor+offset,length);return true;}
static bool meta_erase(void*context,uint32_t offset)
{fixture_t*f=context;if((offset%4096u)||offset>COMP_WBA_NOR_TOTAL_BYTES-4096u)return false;memset(f->nor+offset,0xff,4096u);return true;}
static bool meta_write(void*context,uint32_t offset,const uint8_t*data,size_t length)
{fixture_t*f=context;if(offset>COMP_WBA_NOR_TOTAL_BYTES||length>COMP_WBA_NOR_TOTAL_BYTES-offset)return false;for(size_t i=0;i<length;++i)f->nor[offset+i]&=data[i];return true;}
static void inject_activating_checkpoint(fixture_t*f)
{
    comp_wba_update_metadata_ports_t ports={meta_read,meta_erase,meta_write,f,COMP_WBA_NOR_UPDATE_META_A,COMP_WBA_NOR_UPDATE_META_B};
    comp_wba_update_metadata_store_t store;require(comp_wba_update_metadata_mount(&store,&ports)&&store.loaded&&store.record.boot_record_valid,"mount trial metadata for power-cut fixture");
    comp_wba_update_metadata_record_t next=store.record;comp_wba_update_checkpoint_t *cp=&next.checkpoint;
    memset(cp,0,sizeof(*cp));cp->magic=COMP_WBA_UPDATE_CHECKPOINT_MAGIC;cp->sequence=17u;cp->state=COMP_WBA_UPDATE_ACTIVATING;
    cp->auth_length=store.record.boot_record.auth_length;cp->manifest=store.record.boot_record.candidate;
    memcpy(cp->auth,store.record.boot_record.authentication,cp->auth_length);cp->crc32=comp_wba_update_checkpoint_crc32(cp);
    next.checkpoint_valid=1u;require(comp_wba_update_metadata_commit(&store,&ports,&next),"persist ACTIVATING power-cut window");
}

static void install_trial(fixture_t*f,const uint8_t candidate[IMAGE_BYTES],companion_spi_nor_stm32wba_t*n,PKA_HandleTypeDef*pka)
{
    comp_v11_update_storage_t app,boot;comp_v11_update_storage_config_t c=config(f,n,pka);
    comp_wba_update_manifest_t m={0};uint8_t sig[64]={1u},scratch[257];
    m.schema_version=1u;m.target=COMP_WBA_UPDATE_TARGET_FIRMWARE;m.format_version=1u;
    m.target_family=COMP_WBA_UPDATE_TARGET_FAMILY_STM32WBA;m.board_target=COMP_WBA_UPDATE_BOARD_COMPANION_V11;
    m.component_version=8u;m.minimum_app_version=7u;m.maximum_app_version=7u;m.size_bytes=IMAGE_BYTES;digest(candidate,IMAGE_BYTES,m.sha256);
    require(comp_v11_update_storage_init(&app,&c),"application facade init");
    require(comp_wba_update_open(&app.service,&m,sig,sizeof(sig)),"authorize transfer");
    app.config.context=f;
    require(app.service.config.ports.staging_begin(&app,IMAGE_BYTES),"durable shared workspace reservation");
    require(f->claimed_bytes==IMAGE_BYTES+0x2000u,"reserve exact staging and rollback bytes");
    require(app.service.config.ports.staging_write(&app,0u,candidate,IMAGE_BYTES),"write reserved staging");
    require(!memcmp(f->nor+COMP_WBA_NOR_TOTAL_BYTES-f->claimed_bytes,candidate,IMAGE_BYTES),"mapped staging physical address");
    uint8_t invalid_read;
    require(companion_spi_nor_stm32wba_read(n,COMP_WBA_NOR_UPDATE_STAGING_BASE,&invalid_read,1u)==COMPANION_SPI_NOR_STM32WBA_ERROR,
        "logical staging cannot be used as a raw physical NOR address");
    require(comp_wba_boot_activate_step(&app.installer,&m,sig,sizeof(sig),COMP_WBA_NOR_UPDATE_STAGING_BASE,IMAGE_BYTES,NULL,0u)==COMP_WBA_UPDATE_STEP_DONE,"publish candidate");
    require(comp_v11_update_boot_init(&boot,&c),"resident boot mount");
    unsigned guard=0u;comp_wba_boot_action_t action=COMP_WBA_BOOT_ACTION_WORK;
    while(action==COMP_WBA_BOOT_ACTION_WORK&&guard++<20000u)action=comp_v11_update_boot_poll(&boot,scratch,sizeof(scratch));
    require(action==COMP_WBA_BOOT_ACTION_BOOT_APP&&guard<20000u,"resident boot installs trial");
}

int main(void)
{
    uint8_t candidate[IMAGE_BYTES],scratch[191];fixture_t good={0};companion_spi_nor_stm32wba_t nor;PKA_HandleTypeDef pka={0};
    /* A failed readback can hide a successfully committed WUS2 lease. The
     * recorder must not get those bytes back before remount decides ownership. */
    fixture_t ambiguous={0};prepare(&ambiguous,candidate);
    comp_v11_update_storage_t uncertain;comp_v11_update_storage_config_t uncertain_c=config(&ambiguous,&nor,&pka);
    require(comp_v11_update_storage_init(&uncertain,&uncertain_c),"uncertain lease initial mount");
    uncertain.service.manifest.target=COMP_WBA_UPDATE_TARGET_FIRMWARE;
    ambiguous.fail_commit_readback=true;
    require(!uncertain.service.config.ports.staging_begin(&uncertain,IMAGE_BYTES),"injected lease readback failure");
    require(ambiguous.claimed_bytes==IMAGE_BYTES+0x2000u,"ambiguous durable lease must stay reserved in RAM");
    require(!uncertain.ready&&!uncertain.manifest_accepted,"uncertain metadata blocks further update mutations");
    require(!uncertain.service.config.ports.staging_write(&uncertain,0u,candidate,1u),"uncertain root cannot accept payload");
    require(!comp_v11_update_storage_poll(&uncertain,scratch,sizeof(scratch)),"uncertain root cannot advance checkpoints");
    comp_wba_update_metadata_ports_t ambiguous_ports={meta_read,meta_erase,meta_write,&ambiguous,
        COMP_WBA_NOR_UPDATE_META_A,COMP_WBA_NOR_UPDATE_META_B};
    comp_wba_update_metadata_store_t durable;
    require(comp_wba_update_metadata_mount(&durable,&ambiguous_ports)&&durable.loaded&&
        durable.record.workspace_base==COMP_WBA_NOR_TOTAL_BYTES-ambiguous.claimed_bytes,
        "independent remount sees committed lease despite failed readback");
    comp_v11_update_storage_config_t no_allocator=uncertain_c;no_allocator.workspace_reserve=NULL;
    require(!comp_v11_update_storage_init(&uncertain,&no_allocator),"app cannot mount shared OTA without recording allocator");
    require(comp_v11_update_boot_init(&uncertain,&no_allocator),"resident boot maps durable lease without app allocator");
    require(comp_v11_update_storage_init(&uncertain,&uncertain_c)&&!ambiguous.claimed_bytes&&
        !uncertain.metadata.record.workspace_base,"remount safely releases unused lease before new recording");
    release_fixture(&ambiguous);

    /* Durable release can succeed before the in-RAM allocator responds.
     * Reinitialization must reconcile zero, even when WUS2 already says free. */
    fixture_t release_lost={0};prepare(&release_lost,candidate);install_trial(&release_lost,candidate,&nor,&pka);
    uncertain_c=config(&release_lost,&nor,&pka);
    require(comp_v11_update_storage_init(&uncertain,&uncertain_c)&&
        comp_v11_update_storage_request_confirm(&uncertain,8u),"lost allocator release trial");
    release_lost.fail_release=true;
    unsigned release_guard=0u;
    while(uncertain.confirm_pending&&release_guard++<1000u)(void)comp_v11_update_storage_poll(&uncertain,scratch,sizeof(scratch));
    require(uncertain.confirm_failed&&!uncertain.ready&&!uncertain.metadata.record.workspace_base&&
        release_lost.claimed_bytes>0u,"durable free plus pending RAM lease fails closed");
    require(comp_v11_update_storage_init(&uncertain,&uncertain_c)&&!release_lost.claimed_bytes,
        "zero durable lease reconciles pending allocator release on remount");
    release_fixture(&release_lost);
    prepare(&good,candidate);install_trial(&good,candidate,&nor,&pka);
    inject_activating_checkpoint(&good);
    comp_v11_update_storage_t app;comp_v11_update_storage_config_t c=config(&good,&nor,&pka);
    c.current_firmware_version=8u;c.current_app_version=8u;
    require(comp_v11_update_storage_init(&app,&c),"trial application facade init");
    require(!app.metadata.record.checkpoint_valid&&app.service.state==COMP_WBA_UPDATE_IDLE,
            "exact stale ACTIVATING checkpoint cleared without blocking trial confirmation");
    comp_wba_update_manifest_t replacement={0};uint8_t signature[64]={1u},wire[COMP_WBA_UPDATE_MANIFEST_WIRE_BYTES];
    replacement.schema_version=1u;replacement.target=COMP_WBA_UPDATE_TARGET_FIRMWARE;replacement.format_version=1u;
    replacement.target_family=COMP_WBA_UPDATE_TARGET_FAMILY_STM32WBA;replacement.board_target=COMP_WBA_UPDATE_BOARD_COMPANION_V11;
    replacement.component_version=9u;replacement.minimum_app_version=7u;replacement.maximum_app_version=8u;replacement.size_bytes=IMAGE_BYTES;
    digest(candidate,IMAGE_BYTES,replacement.sha256);
    require(comp_wba_update_manifest_wire_encode(&replacement,3u,signature,wire),"encode replacement manifest");
    require(!comp_v11_update_storage_open_wire(&app,wire,sizeof(wire)),"trial awaiting confirmation blocks a new transfer");
    require(comp_v11_update_storage_request_confirm(&app,8u),"request exact trial confirmation");
    unsigned guard=0u;while(app.confirm_pending&&guard++<1000u)require(comp_v11_update_storage_poll(&app,scratch,sizeof(scratch)),"incremental running image hash");
    require(!app.confirm_pending&&!app.confirm_failed&&app.installer.record.phase==COMP_WBA_BOOT_CONFIRMED,"actual installed bytes confirmed");
    require(!app.metadata.record.workspace_base&&good.claimed_bytes==0u,"confirmed update returns shared bytes to recorder");
    comp_v11_update_storage_t floor_app;comp_v11_update_storage_config_t floor_c=config(&good,&nor,&pka);
    floor_c.current_firmware_version=6u;floor_c.current_ui_version=20u;
    require(comp_v11_update_storage_init(&floor_app,&floor_c)&&
            floor_app.service.config.current_firmware_version==8u&&
            floor_app.service.config.current_ui_version==21u,
            "persisted confirmed component floors override older build defaults");
    floor_c.current_firmware_version=12u;floor_c.current_ui_version=30u;
    require(comp_v11_update_storage_init(&floor_app,&floor_c)&&
            floor_app.service.config.current_firmware_version==12u&&
            floor_app.service.config.current_ui_version==30u,
            "newer build defaults remain authoritative over older persisted floors");
    release_fixture(&good);

    fixture_t corrupt={0};prepare(&corrupt,candidate);install_trial(&corrupt,candidate,&nor,&pka);c=config(&corrupt,&nor,&pka);
    require(comp_v11_update_storage_init(&app,&c)&&comp_v11_update_storage_request_confirm(&app,8u),"request corrupt trial confirmation");
    corrupt.flash[COMP_WBA_BOOT_APP_OFFSET+100u]^=1u;guard=0u;
    while(app.confirm_pending&&guard++<1000u)(void)comp_v11_update_storage_poll(&app,scratch,sizeof(scratch));
    require(app.confirm_failed&&app.installer.record.phase==COMP_WBA_BOOT_AWAIT_CONFIRM,"running image mismatch remains unconfirmed for rollback");
    release_fixture(&corrupt);
    /* Resource OTA shares the very same arena. Its full-bank rollback must
     * leave the dynamic system roots alone and return capacity after rollback. */
    fixture_t ui={0};prepare(&ui,candidate);c=config(&ui,&nor,&pka);
    memset(ui.nor,0x95,COMP_WBA_NOR_UI_BYTES);
    require(comp_v11_update_storage_init(&app,&c),"resource update init");
    replacement.target=COMP_WBA_UPDATE_TARGET_UI_ASSETS;
    replacement.format_version=COMP_WBA_UPDATE_UI_FORMAT_PARTITION_IMAGE_V1;
    replacement.component_version=22u;replacement.minimum_app_version=7u;replacement.maximum_app_version=7u;
    require(comp_wba_update_open(&app.service,&replacement,signature,sizeof(signature)),"authorize resource transfer");
    require(app.service.config.ports.staging_begin(&app,IMAGE_BYTES),"reserve resource staging and bank rollback");
    require(ui.claimed_bytes==IMAGE_BYTES+COMP_WBA_NOR_UI_BYTES,"resource workspace only on demand");
    require(app.service.config.ports.staging_write(&app,0u,candidate,IMAGE_BYTES),"stage resource bytes");
    require(!app.service.config.ports.staging_write(&app,IMAGE_BYTES,candidate,1u),"staging bounds protect rollback");
    require(comp_wba_boot_activate_step(&app.installer,&replacement,signature,sizeof(signature),COMP_WBA_NOR_UPDATE_STAGING_BASE,IMAGE_BYTES,NULL,0u)==COMP_WBA_UPDATE_STEP_DONE,"activate resource bank");
    comp_v11_update_storage_t ui_boot;uint8_t ui_scratch[256];
    const unsigned ui_step_limit=8u*(COMP_WBA_NOR_UI_BYTES+IMAGE_BYTES)/sizeof(ui_scratch)+4096u;
    require(comp_v11_update_boot_init(&ui_boot,&c),"resource boot mount");
    comp_wba_boot_action_t ui_action=COMP_WBA_BOOT_ACTION_WORK;guard=0u;
    while(ui_action==COMP_WBA_BOOT_ACTION_WORK&&guard++<ui_step_limit)ui_action=comp_v11_update_boot_poll(&ui_boot,ui_scratch,sizeof(ui_scratch));
    require(ui_action==COMP_WBA_BOOT_ACTION_BOOT_APP&&!memcmp(ui.nor,candidate,IMAGE_BYTES),"resource bank installed from shared workspace");
    require(comp_wba_workspace_layout_valid(meta_read,&ui),"resource install preserves dynamic layout roots");
    require(comp_v11_update_boot_init(&ui_boot,&c),"unconfirmed resource restart");ui_action=COMP_WBA_BOOT_ACTION_WORK;guard=0u;
    while(ui_action==COMP_WBA_BOOT_ACTION_WORK&&guard++<ui_step_limit)ui_action=comp_v11_update_boot_poll(&ui_boot,ui_scratch,sizeof(ui_scratch));
    require(ui_action==COMP_WBA_BOOT_ACTION_BOOT_APP,"unconfirmed resource rollback finishes");
    for(size_t n=0u;n<COMP_WBA_NOR_UI_BYTES;n++)require(ui.nor[n]==0x95u,"original bank restored");
    require(comp_v11_update_storage_init(&app,&c)&&!ui.claimed_bytes&&!app.metadata.record.workspace_base,"rollback returns shared capacity");
    release_fixture(&ui);
    fixture_t future={0};prepare(&future,candidate);c=config(&future,&nor,&pka);
    memset(future.nor+COMP_WBA_NOR_LAYOUT_A,255,64u);memcpy(future.nor+COMP_WBA_NOR_LAYOUT_B,"CFL4",4u);
    uint8_t preserved[8192];memcpy(preserved,future.nor+COMP_WBA_NOR_UPDATE_META_A,sizeof(preserved));
    require(!comp_v11_update_storage_init(&app,&c),"V1 app accepted future layout ownership");
    require(!comp_v11_update_boot_init(&app,&c),"V1 resident boot accepted future layout ownership");
    require(!memcmp(preserved,future.nor+COMP_WBA_NOR_UPDATE_META_A,sizeof(preserved)),"future layout touched old metadata");
    memset(future.nor+COMP_WBA_NOR_LAYOUT_B,255,64u);
    require(!comp_v11_update_storage_init(&app,&c)&&!comp_v11_update_boot_init(&app,&c),"missing layout allowed writer");
    require(!memcmp(preserved,future.nor+COMP_WBA_NOR_UPDATE_META_A,sizeof(preserved)),"prepared migration touched old metadata");
    release_fixture(&future);
    printf("PASS_WBA_UPDATE_STORAGE_CONFIRM actual_running_hash=1 incremental_bounded=1 mismatch_unconfirmed=1 persisted_version_floors=1 ambiguous_lease_retained=1 zero_release_reconciled=1 app_allocator_required=1\n");return 0;
}
