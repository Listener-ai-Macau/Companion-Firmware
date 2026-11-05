#include "wba_flash_migration.h"
#include "wba_storage_layout.h"
#include "companion_recording_journal.h"
#include "companion_recording_wire.h"
#include "companion_recording_resource_pack.h"
#include "wba_update_service.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL_MIGRATION line=%d %s\n",__LINE__,#x);exit(2);}}while(0)
#define TOTAL COMP_WBA_NOR_TOTAL_BYTES
#define SECTOR COMP_WBA_NOR_SECTOR_BYTES
#define EPOCH UINT64_C(0x0102030405060708)
static uint8_t *nor,*initial,*saved,scratch[4096],uid[12]={1,2,3,4,5,6,7,8,9,10,11,12};
static int64_t meta_program_cut=-1,meta_erase_cut=-1,data_program_cut=-1,data_erase_cut=-1,pool_program_cut=-1;
static uint32_t programs,erases,data_erases;
static bool idle=true,authorized=true,read_failure=false,dishonest=false;
static bool is_root(uint32_t at)
{
    const uint32_t bases[]={COMP_WBA_MIGRATION_ROOT_A,COMP_WBA_MIGRATION_ROOT_B,COMP_WBA_V2_LAYOUT_A,COMP_WBA_V2_LAYOUT_B};
    for(size_t i=0u;i<4u;i++)if(at>=bases[i]&&at<bases[i]+SECTOR)return true;
    return false;
}
static bool read_nor(void *context,uint32_t at,uint8_t *out,size_t n)
{(void)context;if(read_failure||at>TOTAL||n>TOTAL-at)return false;memcpy(out,nor+at,n);return true;}
static bool program_nor(void *context,uint32_t at,const uint8_t *bytes,size_t n)
{
    (void)context;programs++;if(at>TOTAL||n>TOTAL-at)return false;
    bool pool_meta=at>=COMP_WBA_V2_POOL_META_BASE&&at<COMP_WBA_V2_POOL_META_BASE+COMP_WBA_V2_POOL_META_BYTES;
    int64_t *cut=pool_meta?&pool_program_cut:is_root(at)?&meta_program_cut:&data_program_cut;
    size_t count=n;if(*cut>=0&&(uint64_t)*cut<n)count=(size_t)*cut;
    for(size_t i=0u;i<count;i++){if((nor[at+i]&bytes[i])!=bytes[i])return false;nor[at+i]&=bytes[i];}
    if(*cut>=0){*cut-=(int64_t)count;if(*cut==0)return false;}
    return count==n;
}
static bool erase_nor(void *context,uint32_t at)
{
    (void)context;if(at%SECTOR||at>TOTAL-SECTOR)return false;
    erases++;if(!is_root(at))data_erases++;
    int64_t *cut=is_root(at)?&meta_erase_cut:&data_erase_cut;
    size_t count=SECTOR;if(*cut>=0&&(uint64_t)*cut<SECTOR)count=(size_t)*cut;
    if(dishonest&&!is_root(at))count=SECTOR/2u;
    memset(nor+at,255,count);
    if(*cut>=0){*cut-=(int64_t)count;if(*cut==0)return false;}
    return true;
}
static const comp_wba_pool_port_t port={read_nor,program_nor,erase_nor,NULL};
static bool authorize(void *context){(void)context;return authorized;}
static bool exclusive(void *context){(void)context;return idle;}
static const comp_wba_migration_gate_t gate={authorize,exclusive,NULL};
static void no_faults(void)
{meta_program_cut=meta_erase_cut=data_program_cut=data_erase_cut=pool_program_cut=-1;idle=authorized=true;read_failure=dishonest=false;}
static void mount(comp_wba_migration_t *m)
{CHECK(comp_wba_migration_mount(m,&port,&gate,uid,EPOCH));}
static bool old_read(void *c,uint32_t at,uint8_t *out,uint32_t n)
{(void)c;return at<=COMP_WBA_NOR_RECORDING_BYTES&&n<=COMP_WBA_NOR_RECORDING_BYTES-at&&read_nor(NULL,COMP_WBA_NOR_RECORDING_BASE+at,out,n);}
static bool old_program(void *c,uint32_t at,const uint8_t *bytes,uint32_t n)
{(void)c;return at<=COMP_WBA_NOR_RECORDING_BYTES&&n<=COMP_WBA_NOR_RECORDING_BYTES-at&&program_nor(NULL,COMP_WBA_NOR_RECORDING_BASE+at,bytes,n);}
static bool old_erase(void *c,uint32_t at,uint32_t n)
{(void)c;if(n!=SECTOR)return false;return erase_nor(NULL,COMP_WBA_NOR_RECORDING_BASE+at);}
static uint32_t crc_add(uint32_t seed,const uint8_t *bytes,uint32_t n)
{
    for(uint32_t i=0u;i<n;i++){seed^=bytes[i];for(uint8_t b=0u;b<8u;b++)seed=(seed>>1)^((seed&1u)?UINT32_C(0xEDB88320):0u);}
    return seed;
}
static const comp_recording_journal_port_t old_port={old_read,old_program,old_erase,crc_add};
static bool new_read(void *c,uint32_t off,uint8_t *out,uint32_t n)
{
    (void)c;uint32_t base=off>=COMP_WBA_V2_POOL_BYTES?COMP_WBA_V2_CATALOG_BASE:COMP_WBA_V2_POOL_BASE;
    uint32_t relative=off>=COMP_WBA_V2_POOL_BYTES?off-COMP_WBA_V2_POOL_BYTES:off;
    return read_nor(NULL,base+relative,out,n);
}
static bool ro_program(void *c,uint32_t at,const uint8_t *p,uint32_t n)
{(void)c;(void)at;(void)p;(void)n;return false;}
static bool ro_erase(void *c,uint32_t at,uint32_t n)
{(void)c;(void)at;(void)n;return false;}
static const comp_recording_journal_port_t new_port={new_read,ro_program,ro_erase,crc_add};
static void sha(const uint8_t *bytes,size_t n,uint8_t out[32])
{comp_wba_update_sha256_t h;comp_wba_update_sha256_init(&h);comp_wba_update_sha256_update(&h,bytes,n);comp_wba_update_sha256_final(&h,out);}
static void seed_diagnostic(void)
{
    uint8_t *p=nor+COMP_RECORDING_RESOURCE_EXTERNAL_OFFSET;
    memset(p,0,128u);memcpy(p,"CRRP",4u);comp_rec_put16(p+4u,1u);comp_rec_put16(p+6u,64u);
    uint32_t total=128u+COMP_RECORDING_RESOURCE_G7_BYTES+COMP_RECORDING_RESOURCE_OPUS16_BYTES;
    comp_rec_put32(p+8u,total);comp_rec_put32(p+12u,2u);comp_rec_put32(p+16u,64u);comp_rec_put32(p+20u,64u);
    comp_rec_put32(p+24u,128u);comp_rec_put32(p+28u,total-128u);
    for(uint32_t i=128u;i<total;i++)p[i]=(uint8_t)((i*37u+9u)%251u);
    for(uint8_t index=0u;index<2u;index++) {
        uint8_t *entry=p+64u+(uint32_t)index*32u;
        uint32_t off=index?128u+COMP_RECORDING_RESOURCE_G7_BYTES:128u;
        uint32_t length=index?COMP_RECORDING_RESOURCE_OPUS16_BYTES:COMP_RECORDING_RESOURCE_G7_BYTES;
        comp_rec_put32(entry,(uint32_t)index+1u);comp_rec_put32(entry+4u,off);comp_rec_put32(entry+8u,length);
        comp_rec_put32(entry+12u,comp_rec_crc(p+off,length));
        comp_rec_put32(entry+16u,index?12000u:640u);comp_rec_put32(entry+20u,index?0u:175u);
    }
    comp_rec_put32(p+32u,comp_rec_crc(p+128u,total-128u));comp_rec_put32(p+36u,comp_rec_crc(p+64u,64u));
    comp_rec_put32(p+40u,comp_rec_crc(p,40u));
}
static void seed(const char *ui)
{
    no_faults();memset(nor,255,TOTAL);
    FILE *file=NULL;CHECK(fopen_s(&file,ui,"rb")==0&&file!=NULL);
    CHECK(fread(nor,1u,COMP_WBA_NOR_UI_BYTES,file)==COMP_WBA_NOR_UI_BYTES);CHECK(fgetc(file)==EOF);fclose(file);
    comp_recording_journal_t j;CHECK(comp_recording_journal_mount_strict(&j,&old_port,NULL,COMP_WBA_NOR_RECORDING_BYTES)==COMP_RECORDING_JOURNAL_OK);
    for(uint32_t index=0u;index<4u;index++) {
        comp_recording_journal_entry_t entry;
        CHECK(comp_recording_journal_begin(&j,UINT32_C(0x80000),100u+index,200u+index,3u,1u,&entry)==COMP_RECORDING_JOURNAL_OK);
        for(uint32_t i=0u;i<10000u;i++)nor[COMP_WBA_NOR_RECORDING_BASE+entry.payload_offset+i]=(uint8_t)((i*13u+index*5u)%251u);
        if(index==3u) {
            CHECK(comp_recording_journal_checkpoint(&j,entry.recording_id,10000u,0u)==COMP_RECORDING_JOURNAL_OK);
        } else {
            uint8_t digest[32];sha(nor+COMP_WBA_NOR_RECORDING_BASE+entry.payload_offset,10000u,digest);
            CHECK(comp_recording_journal_finalize(&j,entry.recording_id,10000u,4000u,comp_rec_crc(nor+COMP_WBA_NOR_RECORDING_BASE+entry.payload_offset,10000u),digest,3u)==COMP_RECORDING_JOURNAL_OK);
            if(index==1u)CHECK(comp_recording_journal_ack_complete(&j,entry.recording_id,10000u,digest)==COMP_RECORDING_JOURNAL_OK);
            if(index==2u) {
                CHECK(comp_recording_journal_ack_complete(&j,entry.recording_id,10000u,digest)==COMP_RECORDING_JOURNAL_OK);
                CHECK(comp_recording_journal_begin_reclaim(&j,entry.recording_id)==COMP_RECORDING_JOURNAL_OK);
            }
        }
    }
    /* Nonuniform high data makes descending overlap and holes observable. */
    for(uint32_t at=UINT32_C(0x800000);at<UINT32_C(0x9FE000);at++)nor[at]=(uint8_t)((at*19u+7u)%251u);
    for(uint32_t i=0u;i<UINT32_C(0x6000);i++)nor[COMP_WBA_NOR_PREFS_A+i]=(uint8_t)((i*11u+5u)%251u);
    for(uint32_t i=0u;i<SECTOR;i++)nor[UINT32_C(0x1FD000)+i]=(uint8_t)((i*23u+2u)%251u);
    seed_diagnostic();memcpy(initial,nor,TOTAL);programs=erases=data_erases=0u;
}
static void poll(comp_wba_migration_t *m,bool *done)
{uint32_t before=data_erases;CHECK(comp_wba_migration_poll(m,scratch,sizeof(scratch),done));CHECK(data_erases-before<=1u);}
static void until(comp_wba_migration_t *m,uint8_t phase,uint32_t cursor)
{
    bool done=false;for(uint32_t step=0u;step<4000u;step++) {
        if(m->phase==phase&&m->cursor==cursor)return;
        poll(m,&done);CHECK(!done);
    }
    CHECK(false);
}
static void finish(comp_wba_migration_t *m)
{bool done=false;for(uint32_t step=0u;!done&&step<4000u;step++)poll(m,&done);CHECK(done&&comp_wba_migration_verify(m));}
static void output_valid(void)
{
    CHECK(!memcmp(nor+COMP_WBA_V2_POOL_BASE,initial+COMP_WBA_NOR_RECORDING_BASE,COMP_WBA_NOR_RECORDING_BYTES));
    CHECK(!memcmp(nor,initial,COMP_WBA_V2_RECORDING_RESOURCE_BASE));
    CHECK(!memcmp(nor+COMP_WBA_V2_RECORDING_RESOURCE_BASE,initial+COMP_RECORDING_RESOURCE_EXTERNAL_OFFSET,COMP_RECORDING_RESOURCE_EXTERNAL_CAPACITY));
    CHECK(!memcmp(nor+COMP_WBA_V2_CATALOG_BASE,initial+UINT32_C(0x9FE000),8192u));
    CHECK(!memcmp(nor+COMP_WBA_V2_SYSTEM_BASE,initial+COMP_WBA_NOR_PREFS_A,16384u));
    CHECK(!memcmp(nor+COMP_WBA_V2_SYSTEM_BASE+UINT32_C(0x6000),initial+COMP_WBA_NOR_RECORDING_IDENTITY_BASE,8192u));
    uint32_t before=programs;comp_recording_journal_t j;
    CHECK(comp_recording_journal_mount_readonly_strict(&j,&new_port,NULL,COMP_WBA_V2_POOL_BYTES+8192u)==COMP_RECORDING_JOURNAL_OK&&programs==before);
    CHECK(comp_recording_journal_count(&j)==4u&&j.catalog.next_recording_id==5u);
    CHECK(comp_recording_journal_find(&j,1u)->sync_state==COMP_RECORDING_JOURNAL_UNSYNCED);
    CHECK(comp_recording_journal_find(&j,2u)->sync_state==COMP_RECORDING_JOURNAL_ACKED);
    CHECK(comp_recording_journal_find(&j,3u)->sync_state==COMP_RECORDING_JOURNAL_ERASING);
    CHECK(comp_recording_journal_find(&j,4u)->sync_state==COMP_RECORDING_JOURNAL_WRITING);
}
static void checkpoint_faults(void)
{
    comp_wba_migration_t m,reboot;
    for(uint32_t cut=0u;cut<=512u;cut++) {
        memcpy(nor,saved,TOTAL);no_faults();mount(&m);uint32_t cursor=m.cursor;meta_program_cut=(int64_t)cut;
        bool done=true;CHECK(!comp_wba_migration_poll(&m,scratch,sizeof(scratch),&done)&&!done&&!m.ready);
        uint32_t before=programs;CHECK(!comp_wba_migration_poll(&m,scratch,sizeof(scratch),&done)&&programs==before);
        no_faults();mount(&reboot);CHECK(reboot.phase==COMP_WBA_MIGRATION_MOVE_RECORDING&&(reboot.cursor==cursor||reboot.cursor==cursor+SECTOR));
        uint32_t old=reboot.cursor,data_before=data_erases;poll(&reboot,&done);
        if(reboot.cursor==old)CHECK(data_erases==data_before); /* repair, no data erase */
        CHECK(!memcmp(nor+COMP_WBA_V2_POOL_BASE+COMP_WBA_NOR_RECORDING_BYTES-reboot.cursor,
            initial+COMP_WBA_NOR_RECORDING_END-reboot.cursor,reboot.cursor));
    }
    for(uint32_t bank=0u;bank<2u;bank++)for(uint32_t cut=0u;cut<=SECTOR;cut+=128u) {
        memcpy(nor,saved,TOTAL);no_faults();mount(&m);meta_erase_cut=(int64_t)(bank*SECTOR+cut);
        bool done=true;CHECK(!comp_wba_migration_poll(&m,scratch,sizeof(scratch),&done)&&!done&&!m.ready);
        no_faults();mount(&reboot);poll(&reboot,&done);
        CHECK(!memcmp(nor+COMP_WBA_V2_POOL_BASE+COMP_WBA_NOR_RECORDING_BYTES-reboot.cursor,
            initial+COMP_WBA_NOR_RECORDING_END-reboot.cursor,reboot.cursor));
    }
    for(uint32_t kind=0u;kind<2u;kind++)for(uint32_t cut=0u;cut<=SECTOR;cut+=128u) {
        memcpy(nor,saved,TOTAL);no_faults();mount(&m);
        if(kind)data_erase_cut=(int64_t)cut;else data_program_cut=(int64_t)cut;
        bool done=true;uint32_t cursor=m.cursor;CHECK(!comp_wba_migration_poll(&m,scratch,sizeof(scratch),&done)&&!done&&!m.ready);
        no_faults();mount(&reboot);CHECK(reboot.cursor==cursor);poll(&reboot,&done);CHECK(reboot.cursor==cursor+SECTOR);
        CHECK(!memcmp(nor+COMP_WBA_V2_POOL_BASE+COMP_WBA_NOR_RECORDING_BYTES-reboot.cursor,
            initial+COMP_WBA_NOR_RECORDING_END-reboot.cursor,reboot.cursor));
    }
    memcpy(nor,saved,TOTAL);no_faults();mount(&m);meta_program_cut=25;bool done=false;
    CHECK(!comp_wba_migration_poll(&m,scratch,sizeof(scratch),&done));no_faults();mount(&reboot);finish(&reboot);output_valid();
}
static void negatives(void)
{
    comp_wba_migration_t m,stale;bool done=true;
    memcpy(nor,saved,TOTAL);no_faults();mount(&m);mount(&stale);poll(&m,&done);uint32_t before=programs;
    CHECK(!comp_wba_migration_poll(&stale,scratch,sizeof(scratch),&done)&&!stale.ready&&programs==before);
    idle=false;CHECK(!comp_wba_migration_poll(&m,scratch,sizeof(scratch),&done)&&programs==before);idle=true;
    uint8_t alien[12];memcpy(alien,uid,12u);alien[0]^=1u;
    CHECK(!comp_wba_migration_mount(&stale,&port,&gate,alien,EPOCH)&&programs==before);
    CHECK(!comp_wba_migration_mount(&stale,&port,&gate,uid,2u)&&programs==before);
    memcpy(nor,saved,TOTAL);mount(&m);dishonest=true;
    CHECK(!comp_wba_migration_poll(&m,scratch,sizeof(scratch),&done)&&!m.ready);no_faults();mount(&m);CHECK(m.cursor==UINT32_C(0x1F000));
    memcpy(nor,initial,TOTAL);mount(&m);authorized=false;before=programs;CHECK(!comp_wba_migration_begin(&m)&&programs==before);authorized=true;
    nor[COMP_WBA_V2_RECORDING_RESOURCE_BASE]=0x42u;CHECK(!comp_wba_migration_begin(&m)&&programs==before);
    memcpy(nor,initial,TOTAL);mount(&m);nor[COMP_RECORDING_RESOURCE_EXTERNAL_OFFSET+128u]^=1u;CHECK(!comp_wba_migration_begin(&m)&&programs==before);
    memcpy(nor,initial,TOTAL);mount(&m);memset(nor+UINT32_C(0x9FE000),0,8192u);CHECK(!comp_wba_migration_begin(&m)&&programs==before);
    memcpy(nor,initial,TOTAL);mount(&m);memcpy(nor+UINT32_C(0x9FE000),"CRJ3",4u);
    CHECK(!comp_wba_migration_begin(&m)&&programs==before);
    memcpy(nor,initial,TOTAL);mount(&m);nor[COMP_WBA_NOR_UNASSIGNED_BASE]=0u;CHECK(!comp_wba_migration_begin(&m)&&programs==before);
    memcpy(nor,initial,TOTAL);mount(&m);CHECK(comp_wba_migration_begin(&m));until(&m,COMP_WBA_MIGRATION_ANNOUNCE,0u);
    before=programs;nor[COMP_WBA_NOR_RECORDING_BASE]^=1u;CHECK(!comp_wba_migration_poll(&m,scratch,sizeof(scratch),&done)&&!m.ready&&programs==before);
    memcpy(nor,saved,TOTAL);no_faults();read_failure=true;before=programs;CHECK(!comp_wba_migration_mount(&m,&port,&gate,uid,EPOCH)&&programs==before);
    no_faults();memcpy(nor,saved,TOTAL);memcpy(nor+COMP_WBA_V2_LAYOUT_A,"CFL3",4u);CHECK(!comp_wba_migration_mount(&m,&port,&gate,uid,EPOCH)&&programs==before);
}
static void promotion_and_reboot(void)
{
    comp_wba_migration_t m,reboot;bool done=false;
    memcpy(nor,initial,TOTAL);no_faults();mount(&m);CHECK(comp_wba_migration_begin(&m));
    until(&m,COMP_WBA_MIGRATION_ANNOUNCE,0u);
    uint8_t *prepared=malloc(TOTAL);CHECK(prepared!=NULL);memcpy(prepared,nor,TOTAL);
    for(uint32_t kind=0u;kind<2u;kind++)for(uint32_t cut=0u;cut<=(kind?8192u:512u);cut+=(kind?128u:1u)) {
        memcpy(nor,prepared,TOTAL);no_faults();mount(&m);
        if(kind)meta_erase_cut=(int64_t)cut;else meta_program_cut=(int64_t)cut;
        CHECK(!comp_wba_migration_poll(&m,scratch,sizeof(scratch),&done)&&!done&&!m.ready);
        no_faults();mount(&reboot);
        for(uint32_t step=0u;step<4u&&reboot.phase!=COMP_WBA_MIGRATION_MOVE_RECORDING;step++)poll(&reboot,&done);
        CHECK(reboot.phase==COMP_WBA_MIGRATION_MOVE_RECORDING);
        /* No original recording was modified during root publication. */
        CHECK(!memcmp(nor+COMP_WBA_NOR_RECORDING_BASE,initial+COMP_WBA_NOR_RECORDING_BASE,COMP_WBA_NOR_RECORDING_BYTES));
        poll(&reboot,&done);CHECK(reboot.current_mask==12u);
    }
    memcpy(nor,prepared,TOTAL);no_faults();mount(&m);meta_program_cut=13;
    CHECK(!comp_wba_migration_poll(&m,scratch,sizeof(scratch),&done));no_faults();mount(&m);finish(&m);output_valid();
    /* A real new object after EVERY foreground step, including all boundaries,
     * final validation, system/catalog restore, and workspace erasure. */
    memcpy(nor,initial,TOTAL);no_faults();mount(&m);CHECK(comp_wba_migration_begin(&m));done=false;
    for(uint32_t step=0u;!done&&step<4000u;step++){mount(&reboot);poll(&reboot,&done);}
    CHECK(done);output_valid();free(prepared);
}
static void first_root_recovery(void)
{
    comp_wba_migration_t m;uint32_t cases=0u;
    for(uint32_t cut=1u;cut<256u;cut++) {
        memcpy(nor,initial,TOTAL);no_faults();mount(&m);meta_program_cut=(int64_t)cut;
        CHECK(!comp_wba_migration_begin(&m)&&!m.ready);
        no_faults();CHECK(!comp_wba_migration_mount(&m,&port,&gate,uid,EPOCH)&&!m.loaded);
        uint32_t before=erases;CHECK(comp_wba_migration_recover_begin(&m)&&m.loaded&&m.current_mask==3u&&erases==before);
        CHECK(!memcmp(nor,initial,COMP_WBA_MIGRATION_UI_BACKUP));cases++;
    }
    CHECK(cases==255u);
    /* Unknown/future/valid-foreign roots are never erased to repair begin. */
    memcpy(nor,initial,TOTAL);no_faults();memcpy(nor+COMP_WBA_MIGRATION_ROOT_A,"CLM3",4u);
    CHECK(!comp_wba_migration_mount(&m,&port,&gate,uid,EPOCH));uint32_t before=programs;
    CHECK(!comp_wba_migration_recover_begin(&m)&&programs==before);
}
static void ownership_import(void)
{
    memcpy(nor,initial,TOTAL);no_faults();comp_wba_migration_t m;comp_wba_pool_t pool;
    mount(&m);CHECK(comp_wba_migration_begin(&m));finish(&m);pool_program_cut=0;
    CHECK(!comp_wba_migration_import_pool(&m,&pool)&&!m.ready);
    no_faults();mount(&m);CHECK(m.phase==COMP_WBA_MIGRATION_IMPORTING);
    uint8_t *importing=malloc(TOTAL);CHECK(importing!=NULL);memcpy(importing,nor,TOTAL);
    CHECK(comp_wba_migration_import_pool(&m,&pool)&&m.phase==COMP_WBA_MIGRATION_OWNERSHIP_READY&&pool.count==5u);
    output_valid();uint32_t before=programs;CHECK(comp_wba_migration_import_pool(&m,&pool)&&programs==before);
    comp_wba_pool_lease_t leases[5];
    for(uint64_t id=1u;id<=5u;id++)CHECK(comp_wba_pool_find(&pool,id,leases+(size_t)(id-1u)));
    CHECK(leases[0].owner==COMP_WBA_POOL_RECORDING&&leases[0].state==COMP_WBA_POOL_SEALED);
    CHECK(leases[2].state==COMP_WBA_POOL_ERASING&&leases[3].state==COMP_WBA_POOL_WRITING);
    CHECK(leases[4].owner==COMP_WBA_POOL_MIGRATION&&leases[4].start==COMP_WBA_MIGRATION_UI_BACKUP);
    CHECK(leases[4].bytes==COMP_WBA_MIGRATION_BACKUP_END-COMP_WBA_MIGRATION_UI_BACKUP);
    /* Exact initial CPL snapshot completion at EVERY byte. The controller's
     * actual hash/catalog verification above supplies these same leases. */
    for(uint32_t cut=0u;cut<=2048u;cut++) {
        memset(nor+COMP_WBA_V2_POOL_META_BASE,255,COMP_WBA_V2_POOL_META_BYTES);no_faults();pool_program_cut=(int64_t)cut;
        uint32_t erase_before=erases;
        CHECK(!comp_wba_pool_initialize_import(&pool,&port,uid,EPOCH,leases,5u,6u,2u));
        no_faults();CHECK(comp_wba_pool_initialize_import(&pool,&port,uid,EPOCH,leases,5u,6u,2u)&&pool.current_mask==3u);
        CHECK(erases==erase_before);CHECK(comp_wba_pool_find(&pool,1u,leases));
    }
    /* Actual controller restart after a partially written CPL root. */
    memcpy(nor,importing,TOTAL);pool_program_cut=731;mount(&m);CHECK(!comp_wba_migration_import_pool(&m,&pool));
    no_faults();mount(&m);CHECK(m.phase==COMP_WBA_MIGRATION_IMPORTING);CHECK(comp_wba_migration_import_pool(&m,&pool));output_valid();
    /* A different valid snapshot and occupied extra slot cannot be mistaken
     * for the compatible torn initializer. Neither is changed on rejection. */
    uint8_t foreign[COMP_WBA_V2_POOL_META_BYTES];memcpy(foreign,nor+COMP_WBA_V2_POOL_META_BASE,sizeof(foreign));
    comp_rec_put64(nor+COMP_WBA_V2_POOL_META_BASE+8u,2u);
    comp_rec_put32(nor+COMP_WBA_V2_POOL_META_BASE+1020u,comp_rec_crc(nor+COMP_WBA_V2_POOL_META_BASE,1020u));
    before=programs;CHECK(!comp_wba_pool_initialize_import(&pool,&port,uid,EPOCH,leases,5u,6u,2u)&&programs==before);
    memcpy(nor+COMP_WBA_V2_POOL_META_BASE,foreign,sizeof(foreign));nor[COMP_WBA_V2_POOL_META_BASE+1024u]=0u;
    CHECK(!comp_wba_pool_initialize_import(&pool,&port,uid,EPOCH,leases,5u,6u,2u)&&programs==before);
    free(importing);
}
int main(int argc,char **argv)
{
    CHECK(argc==2);nor=malloc(TOTAL);initial=malloc(TOTAL);saved=malloc(TOTAL);CHECK(nor&&initial&&saved);
    seed(argv[1]);comp_wba_migration_t m;mount(&m);CHECK(!m.loaded&&programs==0u&&comp_wba_v2_layout_absent(&port));
    CHECK(comp_wba_migration_begin(&m)&&m.loaded&&!comp_wba_v2_layout_absent(&port));
    until(&m,COMP_WBA_MIGRATION_MOVE_RECORDING,UINT32_C(0x1F000));CHECK(m.next_slot[2]==16u&&m.next_slot[3]==16u);
    memcpy(saved,nor,TOTAL);checkpoint_faults();negatives();promotion_and_reboot();first_root_recovery();ownership_import();
    printf("PASS_FLASH_MIGRATION_SOFTWARE_ONLY metadata_byte_cuts=513 metadata_erase_cuts=66 data_cuts=66 promotion_cuts=578 first_root_cuts=255 import_byte_cuts=2049 restart_every_poll=1 "
        "actual_legacy_journal_states_preserved=4 approved_ui_bytes_preserved=1 diagnostic_crc_verified=1 "
        "one_data_sector_per_poll=1 stale_writer_rejected=1 relocation_only=1 migration_object_bytes=%zu\n",sizeof(m));
    free(saved);free(initial);free(nor);return 0;
}
