#include "wba_boot_installer.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NOR_BYTES UINT32_C(0x1000000)
#define FLASH_BYTES COMP_WBA_INTERNAL_FLASH_BYTES
#define PAGE_BYTES COMP_WBA_INTERNAL_FLASH_PAGE_BYTES
#define APP_BASE UINT32_C(0x08008000)
#define IMAGE_BYTES UINT32_C(0x3000)
#define OLD_BYTES UINT32_C(0x2000)
#define FAMILY COMP_WBA_UPDATE_TARGET_FAMILY_STM32WBA
#define BOARD COMP_WBA_UPDATE_BOARD_COMPANION_V11

typedef struct {
    uint8_t *nor,*flash;
    comp_wba_boot_record_t metadata;
    bool have_metadata,trust,corrupt_install_once,fail_metadata_once;
    uint32_t nor_erases,flash_erases,nor_writes,flash_writes;
    uint32_t last_nor_write,last_flash_write,metadata_writes,metadata_attempts;
    uint32_t fail_metadata_attempt;
} fixture_t;

static void require(bool ok,const char *message){if(!ok){fprintf(stderr,"FAIL: %s\n",message);exit(1);}}
/* Installer ports receive logical windows. The production storage adapter
 * maps them into its durable dynamic lease; this fixture must map them too,
 * rather than treating 0x10000000/0x20000000/0x30000000 as array offsets. */
static bool nor_address(uint32_t logical,size_t n,uint32_t *physical)
{
    uint32_t base=0u,limit=NOR_BYTES,offset=logical;
    if(logical>=COMP_WBA_NOR_FIRMWARE_BACKUP_BASE) {
        offset-=COMP_WBA_NOR_FIRMWARE_BACKUP_BASE;
        limit=COMP_WBA_NOR_FIRMWARE_BACKUP_BYTES;base=NOR_BYTES-limit;
    } else if(logical>=COMP_WBA_NOR_RESOURCE_BACKUP_BASE) {
        offset-=COMP_WBA_NOR_RESOURCE_BACKUP_BASE;
        limit=COMP_WBA_NOR_RESOURCE_BACKUP_BYTES;base=NOR_BYTES-limit;
    } else if(logical>=COMP_WBA_NOR_UPDATE_STAGING_BASE) {
        offset-=COMP_WBA_NOR_UPDATE_STAGING_BASE;
        limit=COMP_WBA_NOR_UPDATE_STAGING_BYTES;
        base=COMP_WBA_NOR_RECORDING_BASE;
    }
    if(offset>limit||n>limit-offset||base>NOR_BYTES||offset>NOR_BYTES-base||n>NOR_BYTES-base-offset)return false;
    *physical=base+offset;return true;
}
static uint8_t *nor_at(fixture_t *f,uint32_t logical,size_t n)
{uint32_t at;require(nor_address(logical,n,&at),"logical NOR window bounded");return f->nor+at;}
static bool authorize(void *ctx,const comp_wba_update_manifest_t*m,const uint8_t*a,uint8_t n)
{return ((fixture_t*)ctx)->trust&&m&&a&&n==4u&&memcmp(a,"SIG1",4u)==0;}
static bool nr(void*ctx,uint32_t o,uint8_t*d,size_t n){fixture_t*f=ctx;uint32_t at;if(!nor_address(o,n,&at))return false;memcpy(d,f->nor+at,n);return true;}
static bool ne(void*ctx,uint32_t o){fixture_t*f=ctx;uint32_t at;if((o%4096u)||!nor_address(o,4096u,&at))return false;memset(f->nor+at,0xff,4096u);f->nor_erases++;return true;}
static bool nw(void*ctx,uint32_t o,const uint8_t*d,size_t n){fixture_t*f=ctx;uint32_t at;if(!nor_address(o,n,&at))return false;for(size_t x=0;x<n;++x)f->nor[at+x]&=d[x];f->nor_writes++;f->last_nor_write=o;return true;}
static bool fr(void*ctx,uint32_t a,uint8_t*d,size_t n){fixture_t*f=ctx;if(a<0x08000000u||a-0x08000000u>FLASH_BYTES||n>FLASH_BYTES-(a-0x08000000u))return false;memcpy(d,f->flash+a-0x08000000u,n);return true;}
static bool fe(void*ctx,uint32_t a){fixture_t*f=ctx;if(a<0x08000000u||((a-0x08000000u)%PAGE_BYTES)||a-0x08000000u>FLASH_BYTES-PAGE_BYTES)return false;memset(f->flash+a-0x08000000u,0xff,PAGE_BYTES);f->flash_erases++;return true;}
static bool fw(void*ctx,uint32_t a,const uint8_t*d,size_t n){fixture_t*f=ctx;if(a<0x08000000u||a-0x08000000u>FLASH_BYTES||n>FLASH_BYTES-(a-0x08000000u))return false;uint32_t o=a-0x08000000u;for(size_t x=0;x<n;++x)f->flash[o+x]&=d[x];f->flash_writes++;f->last_flash_write=a;if(f->corrupt_install_once){f->flash[o]^=1u;f->corrupt_install_once=false;}return true;}
static bool ml(void*ctx,comp_wba_boot_record_t*r){fixture_t*f=ctx;if(!f->have_metadata)return false;*r=f->metadata;return true;}
static bool ms(void*ctx,const comp_wba_boot_record_t*r){fixture_t*f=ctx;f->metadata_attempts++;if(f->fail_metadata_once||(f->fail_metadata_attempt&&f->metadata_attempts==f->fail_metadata_attempt)){f->fail_metadata_once=false;return false;}f->metadata=*r;f->have_metadata=true;f->metadata_writes++;return true;}

static comp_wba_boot_config_t config(fixture_t*f)
{
    comp_wba_boot_config_t c={0};c.ports=(comp_wba_boot_ports_t){authorize,nr,ne,nw,fr,fe,fw,ml,ms,f};
    c.target_family=FAMILY;c.board_target=BOARD;c.flash_base=0x08000000u;
    c.flash_page_bytes=PAGE_BYTES;c.sram_base=0x20000000u;c.sram_bytes=0x20000u;
    c.installed_version=7u;c.installed_image_size=OLD_BYTES;return c;
}
static void digest(const uint8_t*d,size_t n,uint8_t out[32]){comp_wba_update_sha256_t h;comp_wba_update_sha256_init(&h);comp_wba_update_sha256_update(&h,d,n);comp_wba_update_sha256_final(&h,out);}
static comp_wba_update_manifest_t make_manifest(const uint8_t*image)
{comp_wba_update_manifest_t m={0};m.schema_version=1u;m.target=COMP_WBA_UPDATE_TARGET_FIRMWARE;m.format_version=1u;m.target_family=FAMILY;m.board_target=BOARD;m.component_version=8u;m.minimum_app_version=7u;m.maximum_app_version=7u;m.size_bytes=IMAGE_BYTES;digest(image,IMAGE_BYTES,m.sha256);return m;}
static comp_wba_update_manifest_t make_resource_manifest(const uint8_t*image,uint32_t size)
{comp_wba_update_manifest_t m={0};m.schema_version=1u;m.target=COMP_WBA_UPDATE_TARGET_UI_ASSETS;m.format_version=COMP_WBA_UPDATE_UI_FORMAT_PARTITION_IMAGE_V1;m.target_family=FAMILY;m.board_target=BOARD;m.component_version=22u;m.minimum_app_version=7u;m.maximum_app_version=8u;m.size_bytes=size;digest(image,size,m.sha256);return m;}
static void put32(uint8_t*p,uint32_t v){p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);p[2]=(uint8_t)(v>>16);p[3]=(uint8_t)(v>>24);}
static void prepare(fixture_t*f,uint8_t old_image[OLD_BYTES],uint8_t candidate[IMAGE_BYTES])
{
    f->nor=malloc(NOR_BYTES);f->flash=malloc(FLASH_BYTES);require(f->nor&&f->flash,"allocate fixture");
    memset(f->nor,0xff,NOR_BYTES);memset(f->flash,0xA5,FLASH_BYTES);f->trust=true;
    for(uint32_t x=0;x<OLD_BYTES;++x)old_image[x]=(uint8_t)(0xC0u+(x%31u));
    memcpy(f->flash+COMP_WBA_BOOT_APP_OFFSET,old_image,OLD_BYTES);
    for(uint32_t x=0;x<IMAGE_BYTES;++x)candidate[x]=(uint8_t)(x*13u+7u);
    put32(candidate,0x20020000u);put32(candidate+4u,APP_BASE+0x101u);
    memcpy(nor_at(f,COMP_WBA_NOR_UPDATE_STAGING_BASE,IMAGE_BYTES),candidate,IMAGE_BYTES);
    memset(f->flash+COMP_WBA_BOOT_NVM_OFFSET,0x5A,0x4000u);
}
static void release(fixture_t*f){free(f->nor);free(f->flash);}
static comp_wba_boot_action_t run_boot(comp_wba_boot_installer_t*i)
{uint8_t scratch[257];comp_wba_boot_action_t a=COMP_WBA_BOOT_ACTION_WORK;unsigned guard=0;while(a==COMP_WBA_BOOT_ACTION_WORK&&guard++<20000u)a=comp_wba_boot_poll(i,scratch,sizeof(scratch));require(guard<20000u,"boot work bounded");return a;}

static void stage(fixture_t*f,comp_wba_boot_installer_t*i,const comp_wba_update_manifest_t*m)
{comp_wba_boot_config_t c=config(f);require(comp_wba_boot_init(i,&c,false),"app installer init");require(comp_wba_boot_activate_step(i,m,(const uint8_t*)"SIG1",4u,COMP_WBA_NOR_UPDATE_STAGING_BASE,m->size_bytes,NULL,0u)==COMP_WBA_UPDATE_STEP_DONE,"stage authenticated candidate");}

static void test_firmware_phase_reboots(void)
{
    uint8_t old_image[OLD_BYTES],candidate[IMAGE_BYTES],scratch[257];
    fixture_t f={0};comp_wba_boot_installer_t i;unsigned guard=0u;
    prepare(&f,old_image,candidate);comp_wba_update_manifest_t m=make_manifest(candidate);
    stage(&f,&i,&m);comp_wba_boot_config_t c=config(&f);
    require(comp_wba_boot_init(&i,&c,true),"phase reboot firmware init");
    while(!(f.nor_writes&&f.last_nor_write>=COMP_WBA_NOR_ROLLBACK_BASE&&
            f.last_nor_write<COMP_WBA_NOR_ROLLBACK_BASE+COMP_WBA_NOR_ROLLBACK_BYTES)&&guard++<20000u)
        require(comp_wba_boot_poll(&i,scratch,sizeof(scratch))==COMP_WBA_BOOT_ACTION_WORK,
                "firmware backup-copy cut point");
    require(guard<20000u&&comp_wba_boot_init(&i,&c,true),
            "reboot during firmware backup copy");
    f.flash_writes=0u;guard=0u;
    while(!(f.metadata.phase==COMP_WBA_BOOT_INSTALLING&&f.flash_writes)&&guard++<20000u)
        require(comp_wba_boot_poll(&i,scratch,sizeof(scratch))==COMP_WBA_BOOT_ACTION_WORK,
                "firmware install-copy cut point");
    require(guard<20000u&&comp_wba_boot_init(&i,&c,true),
            "reboot during firmware install copy");
    require(run_boot(&i)==COMP_WBA_BOOT_ACTION_BOOT_APP&&
            memcmp(f.flash+COMP_WBA_BOOT_APP_OFFSET,candidate,IMAGE_BYTES)==0,
            "firmware install-copy reboot resumes exact candidate");
    f.flash_writes=0u;require(comp_wba_boot_init(&i,&c,true),
            "start unconfirmed firmware rollback");guard=0u;
    while(!f.flash_writes&&guard++<20000u)
        require(comp_wba_boot_poll(&i,scratch,sizeof(scratch))==COMP_WBA_BOOT_ACTION_WORK,
                "firmware restore-copy cut point");
    require(guard<20000u&&comp_wba_boot_init(&i,&c,true),
            "reboot during firmware restore copy");
    require(run_boot(&i)==COMP_WBA_BOOT_ACTION_BOOT_APP&&
            memcmp(f.flash+COMP_WBA_BOOT_APP_OFFSET,old_image,OLD_BYTES)==0,
            "firmware restore-copy reboot restores old image");
    for(uint32_t x=0u;x<COMP_WBA_BOOT_INTERNAL_BYTES;++x)
        require(f.flash[x]==0xA5u,"phase reboot protects resident boot");
    for(uint32_t x=0u;x<0x4000u;++x)
        require(f.flash[COMP_WBA_BOOT_NVM_OFFSET+x]==0x5Au,"phase reboot protects NVM");
    release(&f);
}

static void test_resource_phase_reboots(void)
{
    uint8_t old_image[OLD_BYTES],candidate[IMAGE_BYTES],scratch[257];
    uint8_t *old_ui=malloc(COMP_WBA_NOR_UI_BYTES);uint8_t *resource=malloc(0x12000u);
    fixture_t f={0};comp_wba_boot_installer_t i;unsigned guard=0u;
    require(old_ui&&resource,"allocate resource phase fixtures");
    prepare(&f,old_image,candidate);
    for(uint32_t x=0u;x<COMP_WBA_NOR_UI_BYTES;++x)old_ui[x]=(uint8_t)(0x73u+(x%67u));
    for(uint32_t x=0u;x<0x12000u;++x)resource[x]=(uint8_t)(x*23u+9u);
    memcpy(f.nor+COMP_WBA_NOR_UI_BASE,old_ui,COMP_WBA_NOR_UI_BYTES);
    memcpy(nor_at(&f,COMP_WBA_NOR_UPDATE_STAGING_BASE,0x12000u),resource,0x12000u);
    comp_wba_update_manifest_t m=make_resource_manifest(resource,0x12000u);
    stage(&f,&i,&m);comp_wba_boot_config_t c=config(&f);
    require(comp_wba_boot_init(&i,&c,true),"phase reboot resource init");
    while(!(f.nor_writes&&f.last_nor_write>=COMP_WBA_NOR_RESOURCE_BACKUP_BASE&&
            f.last_nor_write<COMP_WBA_NOR_RESOURCE_BACKUP_BASE+COMP_WBA_NOR_UI_BYTES)&&guard++<50000u)
        require(comp_wba_boot_poll(&i,scratch,sizeof(scratch))==COMP_WBA_BOOT_ACTION_WORK,
                "resource backup-copy cut point");
    require(guard<50000u&&comp_wba_boot_init(&i,&c,true),
            "reboot during resource backup copy");
    f.nor_writes=0u;f.last_nor_write=UINT32_MAX;guard=0u;
    while(!(f.metadata.phase==COMP_WBA_BOOT_INSTALLING&&f.nor_writes&&
            f.last_nor_write<COMP_WBA_NOR_UI_BYTES)&&guard++<50000u)
        require(comp_wba_boot_poll(&i,scratch,sizeof(scratch))==COMP_WBA_BOOT_ACTION_WORK,
                "resource install-copy cut point");
    require(guard<50000u&&comp_wba_boot_init(&i,&c,true),
            "reboot during resource install copy");
    require(run_boot(&i)==COMP_WBA_BOOT_ACTION_BOOT_APP&&
            memcmp(f.nor+COMP_WBA_NOR_UI_BASE,resource,0x12000u)==0,
            "resource install-copy reboot resumes exact candidate");
    f.nor_writes=0u;f.last_nor_write=UINT32_MAX;
    require(comp_wba_boot_init(&i,&c,true),"start unconfirmed resource rollback");guard=0u;
    while(!(f.nor_writes&&f.last_nor_write<COMP_WBA_NOR_UI_BYTES)&&guard++<50000u)
        require(comp_wba_boot_poll(&i,scratch,sizeof(scratch))==COMP_WBA_BOOT_ACTION_WORK,
                "resource restore-copy cut point");
    require(guard<50000u&&comp_wba_boot_init(&i,&c,true),
            "reboot during resource restore copy");
    require(run_boot(&i)==COMP_WBA_BOOT_ACTION_BOOT_APP&&
            memcmp(f.nor+COMP_WBA_NOR_UI_BASE,old_ui,COMP_WBA_NOR_UI_BYTES)==0,
            "resource restore-copy reboot restores full old UI");
    for(uint32_t x=0u;x<COMP_WBA_BOOT_INTERNAL_BYTES;++x)
        require(f.flash[x]==0xA5u,"resource reboot protects resident boot");
    for(uint32_t x=0u;x<0x4000u;++x)
        require(f.flash[COMP_WBA_BOOT_NVM_OFFSET+x]==0x5Au,"resource reboot protects NVM");
    free(resource);free(old_ui);release(&f);
}

static void test_geometry_rejection_before_mutation(void)
{
    uint8_t old_image[OLD_BYTES],candidate[IMAGE_BYTES];fixture_t f={0};
    comp_wba_boot_installer_t i;prepare(&f,old_image,candidate);
    comp_wba_boot_config_t c=config(&f);
    c.installed_image_size=COMP_WBA_BOOT_APP_CAPACITY+1u;
    require(!comp_wba_boot_init(&i,&c,false),"oversize installed app rejected");
    c=config(&f);require(comp_wba_boot_init(&i,&c,false),"geometry test init");
    comp_wba_update_manifest_t m=make_manifest(candidate);
    m.size_bytes=COMP_WBA_BOOT_APP_CAPACITY+1u;
    require(comp_wba_boot_activate_step(&i,&m,(const uint8_t*)"SIG1",4u,
            COMP_WBA_NOR_UPDATE_STAGING_BASE,m.size_bytes,NULL,0u)==COMP_WBA_UPDATE_STEP_FAILED,
            "oversize candidate rejected before mutation");
    m=make_manifest(candidate);
    m.board_target=BOARD==UINT32_C(0x31315643)?UINT32_C(0x45315643):UINT32_C(0x31315643);
    require(comp_wba_boot_activate_step(&i,&m,(const uint8_t*)"SIG1",4u,
            COMP_WBA_NOR_UPDATE_STAGING_BASE,m.size_bytes,NULL,0u)==COMP_WBA_UPDATE_STEP_FAILED,
            "opposite capacity signed target rejected");
    require(f.flash_erases==0u&&f.flash_writes==0u&&!f.have_metadata,
            "geometry rejection leaves boot/app/NVM and metadata unchanged");
    release(&f);
}

int main(void)
{
    test_geometry_rejection_before_mutation();
    uint8_t old_image[OLD_BYTES],candidate[IMAGE_BYTES];fixture_t f={0};prepare(&f,old_image,candidate);
    comp_wba_update_manifest_t m=make_manifest(candidate);comp_wba_boot_installer_t i;stage(&f,&i,&m);
    comp_wba_boot_config_t c=config(&f);require(comp_wba_boot_init(&i,&c,true),"boot init candidate");
    /* Interrupt after the installer has persisted INSTALLING and erased one page. */
    uint8_t scratch[257];unsigned guard=0;while(!(f.metadata.phase==COMP_WBA_BOOT_INSTALLING&&f.flash_erases>0u)&&guard++<10000u)
        require(comp_wba_boot_poll(&i,scratch,sizeof(scratch))==COMP_WBA_BOOT_ACTION_WORK,"pre-cut install step");
    require(comp_wba_boot_init(&i,&c,true),"power-cut reboot during install");
    require(run_boot(&i)==COMP_WBA_BOOT_ACTION_BOOT_APP,"restarted install boots trial");
    require(memcmp(f.flash+COMP_WBA_BOOT_APP_OFFSET,candidate,IMAGE_BYTES)==0,"candidate installed exactly");
    require(memcmp(nor_at(&f,COMP_WBA_NOR_ROLLBACK_BASE,OLD_BYTES),old_image,OLD_BYTES)==0,"previous image backed up");
    for(uint32_t x=0;x<0x4000u;++x)require(f.flash[COMP_WBA_BOOT_NVM_OFFSET+x]==0x5Au,"NVM preserved");
    for(uint32_t x=0;x<COMP_WBA_BOOT_INTERNAL_BYTES;++x)require(f.flash[x]==0xA5u,"resident boot protected");
    /* No application confirmation: next boot restores the verified backup. */
    require(comp_wba_boot_init(&i,&c,true),"unconfirmed reboot");
    require(run_boot(&i)==COMP_WBA_BOOT_ACTION_BOOT_APP,"rollback boots old app");
    require(memcmp(f.flash+COMP_WBA_BOOT_APP_OFFSET,old_image,OLD_BYTES)==0&&f.metadata.phase==COMP_WBA_BOOT_ROLLED_BACK,"unconfirmed image rolled back");
    release(&f);

    fixture_t success={0};prepare(&success,old_image,candidate);m=make_manifest(candidate);stage(&success,&i,&m);c=config(&success);
    require(comp_wba_boot_init(&i,&c,true)&&run_boot(&i)==COMP_WBA_BOOT_ACTION_BOOT_APP,"install confirmed candidate path");
    comp_wba_boot_installer_t app;require(comp_wba_boot_init(&app,&c,false),"application confirm init");
    require(comp_wba_boot_confirm(&app,m.component_version,m.sha256),"post-boot confirm exact identity");
    memset(nor_at(&success,COMP_WBA_NOR_UPDATE_STAGING_BASE,IMAGE_BYTES),0,IMAGE_BYTES);
    require(comp_wba_boot_init(&i,&c,true)&&comp_wba_boot_poll(&i,scratch,sizeof(scratch))==COMP_WBA_BOOT_ACTION_BOOT_APP,"confirmed app remains active");
    require(memcmp(success.flash+COMP_WBA_BOOT_APP_OFFSET,candidate,IMAGE_BYTES)==0,"confirmed candidate retained");
    require(comp_wba_boot_init(&app,&c,false),"reload persisted firmware floor");
    require(comp_wba_boot_activate_step(&app,&m,(const uint8_t*)"SIG1",4u,
        COMP_WBA_NOR_UPDATE_STAGING_BASE,m.size_bytes,NULL,0u)==COMP_WBA_UPDATE_STEP_FAILED,
        "confirmed firmware version cannot be replayed after bootloader rebuild");
    release(&success);

    fixture_t meta_fail={0};prepare(&meta_fail,old_image,candidate);m=make_manifest(candidate);c=config(&meta_fail);
    require(comp_wba_boot_init(&app,&c,false),"metadata failure init");
    comp_wba_boot_record_t record_before=app.record;meta_fail.fail_metadata_once=true;
    require(comp_wba_boot_activate_step(&app,&m,(const uint8_t*)"SIG1",4u,
        COMP_WBA_NOR_UPDATE_STAGING_BASE,m.size_bytes,NULL,0u)==COMP_WBA_UPDATE_STEP_FAILED&&
        memcmp(&app.record,&record_before,sizeof(record_before))==0&&!meta_fail.have_metadata,
        "metadata commit failure restores in-RAM boot record");
    release(&meta_fail);

    fixture_t transition_fail={0};prepare(&transition_fail,old_image,candidate);
    m=make_manifest(candidate);stage(&transition_fail,&i,&m);c=config(&transition_fail);
    /* Candidate staging is attempt 1. Fail the INSTALLING marker after the
     * verified backup marker (attempt 2) has become durable. */
    transition_fail.fail_metadata_attempt=3u;
    require(comp_wba_boot_init(&i,&c,true)&&run_boot(&i)==COMP_WBA_BOOT_ACTION_RECOVERY,
            "installing metadata failure stops this boot");
    require(transition_fail.metadata.phase==COMP_WBA_BOOT_BACKUP_VALID&&
            memcmp(transition_fail.flash+COMP_WBA_BOOT_APP_OFFSET,old_image,OLD_BYTES)==0,
            "backup-valid recovery point is not overwritten by FAILED");
    transition_fail.fail_metadata_attempt=0u;
    require(comp_wba_boot_init(&i,&c,true)&&run_boot(&i)==COMP_WBA_BOOT_ACTION_BOOT_APP,
            "backup-valid metadata failure resumes on reboot");
    require(memcmp(transition_fail.flash+COMP_WBA_BOOT_APP_OFFSET,candidate,IMAGE_BYTES)==0,
            "resumed metadata transition installs exact candidate");
    require(comp_wba_boot_init(&i,&c,true)&&run_boot(&i)==COMP_WBA_BOOT_ACTION_BOOT_APP&&
            memcmp(transition_fail.flash+COMP_WBA_BOOT_APP_OFFSET,old_image,OLD_BYTES)==0,
            "unconfirmed resumed candidate still rolls back exactly");
    release(&transition_fail);

    fixture_t corrupt={0};prepare(&corrupt,old_image,candidate);m=make_manifest(candidate);stage(&corrupt,&i,&m);c=config(&corrupt);corrupt.corrupt_install_once=true;
    require(comp_wba_boot_init(&i,&c,true)&&run_boot(&i)==COMP_WBA_BOOT_ACTION_BOOT_APP,"install corruption triggers rollback");
    require(memcmp(corrupt.flash+COMP_WBA_BOOT_APP_OFFSET,old_image,OLD_BYTES)==0&&corrupt.metadata.phase==COMP_WBA_BOOT_ROLLED_BACK,"corrupt install never becomes trial");
    release(&corrupt);

    fixture_t bad={0};prepare(&bad,old_image,candidate);m=make_manifest(candidate);put32(nor_at(&bad,COMP_WBA_NOR_UPDATE_STAGING_BASE,4u),0x1000u);
    comp_wba_boot_config_t bc=config(&bad);require(comp_wba_boot_init(&i,&bc,false),"bad vector init");
    require(comp_wba_boot_activate_step(&i,&m,(const uint8_t*)"SIG1",4u,COMP_WBA_NOR_UPDATE_STAGING_BASE,m.size_bytes,NULL,0u)==COMP_WBA_UPDATE_STEP_FAILED&&!bad.have_metadata,"invalid vector rejected before metadata");
    release(&bad);

    fixture_t changed={0};prepare(&changed,old_image,candidate);m=make_manifest(candidate);stage(&changed,&i,&m);c=config(&changed);
    *nor_at(&changed,COMP_WBA_NOR_UPDATE_STAGING_BASE+100u,1u)^=1u;
    require(comp_wba_boot_init(&i,&c,true)&&run_boot(&i)==COMP_WBA_BOOT_ACTION_RECOVERY,"changed staging rejected by resident boot");
    require(changed.flash_erases==0u&&memcmp(changed.flash+COMP_WBA_BOOT_APP_OFFSET,old_image,OLD_BYTES)==0,"staging hash checked before app erase");
    release(&changed);

    fixture_t resources={0};prepare(&resources,old_image,candidate);
    uint8_t *old_ui=malloc(COMP_WBA_NOR_UI_BYTES);require(old_ui!=NULL,"allocate old UI image");
    for(uint32_t x=0u;x<COMP_WBA_NOR_UI_BYTES;++x)old_ui[x]=(uint8_t)(0x31u+(x%113u));
    memcpy(resources.nor+COMP_WBA_NOR_UI_BASE,old_ui,COMP_WBA_NOR_UI_BYTES);
    uint8_t resource_image[0x12000];for(size_t x=0u;x<sizeof(resource_image);++x)resource_image[x]=(uint8_t)(x*17u+3u);
    memcpy(nor_at(&resources,COMP_WBA_NOR_UPDATE_STAGING_BASE,sizeof(resource_image)),resource_image,sizeof(resource_image));
    m=make_resource_manifest(resource_image,sizeof(resource_image));stage(&resources,&i,&m);c=config(&resources);
    require(comp_wba_boot_init(&i,&c,true),"resource boot init");
    guard=0u;while(!(resources.metadata.phase==COMP_WBA_BOOT_INSTALLING&&resources.nor[COMP_WBA_NOR_UI_BASE]==0xffu)&&guard++<30000u)
        require(comp_wba_boot_poll(&i,scratch,sizeof(scratch))==COMP_WBA_BOOT_ACTION_WORK,"resource pre-cut step");
    require(comp_wba_boot_init(&i,&c,true)&&run_boot(&i)==COMP_WBA_BOOT_ACTION_BOOT_APP,"resource install resumes after power cut");
    require(memcmp(resources.nor+COMP_WBA_NOR_UI_BASE,resource_image,sizeof(resource_image))==0,"resource candidate installed");
    require(memcmp(nor_at(&resources,COMP_WBA_NOR_RESOURCE_BACKUP_BASE,COMP_WBA_NOR_UI_BYTES),old_ui,COMP_WBA_NOR_UI_BYTES)==0,"full old UI backed up");
    require(resources.metadata.phase==COMP_WBA_BOOT_AWAIT_CONFIRM,"resource waits for application mount confirmation");
    require(comp_wba_boot_init(&app,&c,false)&&comp_wba_boot_confirm(&app,m.component_version,m.sha256),"mounted resource confirmed by app");
    memset(nor_at(&resources,COMP_WBA_NOR_UPDATE_STAGING_BASE,sizeof(resource_image)),0,sizeof(resource_image));
    require(comp_wba_boot_init(&i,&c,true)&&comp_wba_boot_poll(&i,scratch,sizeof(scratch))==COMP_WBA_BOOT_ACTION_BOOT_APP,"confirmed resource retained");
    require(comp_wba_boot_init(&app,&c,false),"reload persisted UI floor");
    require(comp_wba_boot_activate_step(&app,&m,(const uint8_t*)"SIG1",4u,
        COMP_WBA_NOR_UPDATE_STAGING_BASE,m.size_bytes,NULL,0u)==COMP_WBA_UPDATE_STEP_FAILED,
        "confirmed UI generation cannot be replayed");
    free(old_ui);release(&resources);

    fixture_t bad_mount={0};prepare(&bad_mount,old_image,candidate);old_ui=malloc(COMP_WBA_NOR_UI_BYTES);require(old_ui!=NULL,"allocate rollback UI");
    for(uint32_t x=0u;x<COMP_WBA_NOR_UI_BYTES;++x)old_ui[x]=(uint8_t)(0x52u+(x%79u));
    memcpy(bad_mount.nor+COMP_WBA_NOR_UI_BASE,old_ui,COMP_WBA_NOR_UI_BYTES);
    memcpy(nor_at(&bad_mount,COMP_WBA_NOR_UPDATE_STAGING_BASE,sizeof(resource_image)),resource_image,sizeof(resource_image));
    m=make_resource_manifest(resource_image,sizeof(resource_image));stage(&bad_mount,&i,&m);c=config(&bad_mount);
    require(comp_wba_boot_init(&i,&c,true)&&run_boot(&i)==COMP_WBA_BOOT_ACTION_BOOT_APP,"resource trial boot");
    /* Simulated mount failure: do not confirm. Resident boot restores old UI. */
    require(comp_wba_boot_init(&i,&c,true)&&run_boot(&i)==COMP_WBA_BOOT_ACTION_BOOT_APP,"resource mount failure rollback");
    require(memcmp(bad_mount.nor+COMP_WBA_NOR_UI_BASE,old_ui,COMP_WBA_NOR_UI_BYTES)==0&&bad_mount.metadata.phase==COMP_WBA_BOOT_ROLLED_BACK,"unconfirmed resource restored exactly");
    free(old_ui);release(&bad_mount);

    test_firmware_phase_reboots();
    test_resource_phase_reboots();

    printf("PASS_WBA_BOOT_INSTALLER boot_bytes=%lu app_offset=%08lX app_capacity=%08lX nvm_offset=%08lX power_cut_restart=1 unconfirmed_rollback=1 confirmed_retained=1 terminal_staging_independent=1 metadata_failure_ram_rollback=1 backup_valid_metadata_resume=1 persistent_antirollback=1 corrupt_install_rollback=1 invalid_vector_rejected=1 staging_hash_before_erase=1 resource_full_backup=1 resource_mount_confirm=1 resource_mount_rollback=1 firmware_phase_reboots=3 resource_phase_reboots=3 boot_nvm_protected=1\n",
           (unsigned long)COMP_WBA_BOOT_INTERNAL_BYTES,(unsigned long)COMP_WBA_BOOT_APP_OFFSET,
           (unsigned long)COMP_WBA_BOOT_APP_CAPACITY,(unsigned long)COMP_WBA_BOOT_NVM_OFFSET);
    return 0;
}
