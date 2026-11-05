#include "wba_flash_migration.h"
#include "wba_storage_layout.h"
#include "companion_recording_wire.h"
#include "companion_recording_journal.h"
#include "companion_recording_resource_pack.h"
#include "wba_update_service.h"
#include <string.h>

#define SECTOR COMP_WBA_NOR_SECTOR_BYTES
#define SLOTS (SECTOR/COMP_WBA_MIGRATION_WIRE_BYTES)
#define TAIL_BYTES UINT32_C(0x6000)
#define CATALOG_BYTES UINT32_C(0x2000)
#define OLD_CATALOG UINT32_C(0x9FE000)
#define OLD_DIAGNOSTIC UINT32_C(0x1DC000)
#define DIAGNOSTIC_BYTES UINT32_C(0x21000)
#define OLD_POWER UINT32_C(0x1FD000)
#define ROOT_CRC 252u

static const uint32_t roots[4]={COMP_WBA_MIGRATION_ROOT_A,COMP_WBA_MIGRATION_ROOT_B,
    COMP_WBA_V2_LAYOUT_A,COMP_WBA_V2_LAYOUT_B};
static const uint32_t source_base[4]={0u,COMP_WBA_NOR_PREFS_A,OLD_CATALOG,COMP_WBA_NOR_RECORDING_BASE};
static const uint32_t source_bytes[4]={COMP_WBA_NOR_UI_BYTES,TAIL_BYTES,CATALOG_BYTES,COMP_WBA_NOR_RECORDING_BYTES};
static const uint32_t backup_base[3]={COMP_WBA_MIGRATION_UI_BACKUP,COMP_WBA_MIGRATION_TAIL_BACKUP,COMP_WBA_MIGRATION_CATALOG_BACKUP};

#if UINTPTR_MAX == UINT32_MAX
_Static_assert(sizeof(comp_wba_migration_t)<=224u,"migration RAM budget exceeded");
#endif
_Static_assert(COMP_WBA_V2_RECORDING_RESOURCE_BASE+DIAGNOSTIC_BYTES<=COMP_WBA_V2_SYSTEM_BASE,"diagnostic overlaps system");
_Static_assert(COMP_WBA_V2_POOL_BASE+COMP_WBA_NOR_RECORDING_BYTES<COMP_WBA_MIGRATION_UI_BACKUP,"move overlaps backup");

static bool read_at(comp_wba_migration_t *m,uint32_t at,uint8_t *out,size_t n)
{
    if(at<=COMP_WBA_NOR_TOTAL_BYTES&&n<=COMP_WBA_NOR_TOTAL_BYTES-at&&m->port.read(m->port.context,at,out,n))return true;
    m->ready=false;return false;
}
static bool poison(comp_wba_migration_t *m){m->ready=false;return false;}
static uint16_t get16(const uint8_t *p)
{return (uint16_t)((uint16_t)p[0]|(uint16_t)((uint16_t)p[1]<<8u));}
static bool allowed(comp_wba_migration_t *m)
{return m&&m->ready&&m->gate.exclusive_idle(m->gate.context);}
static bool hash_at(comp_wba_migration_t *m,uint32_t at,uint32_t n,uint8_t sha[32])
{
    comp_wba_update_sha256_t h;uint8_t bytes[256];
    comp_wba_update_sha256_init(&h);
    for(uint32_t off=0u;off<n;) {
        uint32_t count=n-off;if(count>sizeof(bytes))count=(uint32_t)sizeof(bytes);
        if(!read_at(m,at+off,bytes,count))return false;
        comp_wba_update_sha256_update(&h,bytes,count);off+=count;
    }
    comp_wba_update_sha256_final(&h,sha);return true;
}
static bool hash_matches(comp_wba_migration_t *m,uint32_t at,uint32_t n,const uint8_t sha[32])
{uint8_t actual[32];return hash_at(m,at,n,actual)&&!memcmp(actual,sha,32u);}
static bool erased(comp_wba_migration_t *m,uint32_t at,uint32_t n)
{
    uint8_t bytes[128];
    for(uint32_t off=0u;off<n;off+=(uint32_t)sizeof(bytes))
        if(!read_at(m,at+off,bytes,sizeof(bytes))||comp_rec_not_uniform(bytes,sizeof(bytes),255u))return false;
    return true;
}
static uint32_t limit(uint8_t phase)
{
    switch(phase) {
    case COMP_WBA_MIGRATION_BACKUP_UI:return COMP_WBA_NOR_UI_BYTES;
    case COMP_WBA_MIGRATION_BACKUP_TAIL:return TAIL_BYTES;
    case COMP_WBA_MIGRATION_BACKUP_CATALOG:return CATALOG_BYTES;
    case COMP_WBA_MIGRATION_MOVE_RECORDING:return COMP_WBA_NOR_RECORDING_BYTES;
    case COMP_WBA_MIGRATION_MOVE_RESOURCE:return DIAGNOSTIC_BYTES;
    case COMP_WBA_MIGRATION_RESTORE_SYSTEM:return 8u*SECTOR;
    case COMP_WBA_MIGRATION_RESTORE_CATALOG:return CATALOG_BYTES;
    case COMP_WBA_MIGRATION_CLEAR_WORKSPACE:return 20u*SECTOR;
    default:return 0u;
    }
}
static void encode(const comp_wba_migration_t *m,bool front,uint8_t wire[COMP_WBA_MIGRATION_WIRE_BYTES])
{
    memset(wire,0,COMP_WBA_MIGRATION_WIRE_BYTES);memcpy(wire,front?"CFL2":"CLM2",4u);
    comp_rec_put16(wire+4u,2u);comp_rec_put16(wire+6u,COMP_WBA_MIGRATION_WIRE_BYTES);
    comp_rec_put64(wire+8u,m->sequence);memcpy(wire+16u,m->device_uid,12u);
    comp_rec_put64(wire+28u,m->format_epoch);wire[36]=m->phase;wire[37]=1u;wire[38]=(uint8_t)m->diagnostic_present;
    comp_rec_put32(wire+40u,m->cursor);memcpy(wire+44u,m->source_sha256,128u);
    comp_rec_put32(wire+172u,COMP_WBA_MIGRATION_BOOT_GENERATION);
    comp_rec_put32(wire+176u,COMP_WBA_NOR_TOTAL_BYTES);
    comp_rec_put32(wire+180u,COMP_WBA_NOR_RECORDING_BASE);comp_rec_put32(wire+184u,COMP_WBA_NOR_RECORDING_BYTES);
    comp_rec_put32(wire+188u,COMP_WBA_V2_POOL_BASE);comp_rec_put32(wire+192u,COMP_WBA_V2_POOL_BYTES);
    comp_rec_put32(wire+196u,COMP_WBA_V2_RECORDING_RESOURCE_BASE);comp_rec_put32(wire+200u,DIAGNOSTIC_BYTES);
    comp_rec_put32(wire+204u,COMP_WBA_V2_SYSTEM_BASE);comp_rec_put32(wire+ROOT_CRC,comp_rec_crc(wire,ROOT_CRC));
}
static bool decode(const uint8_t wire[COMP_WBA_MIGRATION_WIRE_BYTES],bool front,comp_wba_migration_t *m)
{
    if(memcmp(wire,front?"CFL2":"CLM2",4u)||get16(wire+4u)!=2u||
       get16(wire+6u)!=COMP_WBA_MIGRATION_WIRE_BYTES||wire[37]!=1u||wire[38]>1u||wire[39]||
       comp_rec_get32(wire+172u)!=COMP_WBA_MIGRATION_BOOT_GENERATION||
       comp_rec_get32(wire+176u)!=COMP_WBA_NOR_TOTAL_BYTES||comp_rec_get32(wire+180u)!=COMP_WBA_NOR_RECORDING_BASE||
       comp_rec_get32(wire+184u)!=COMP_WBA_NOR_RECORDING_BYTES||comp_rec_get32(wire+188u)!=COMP_WBA_V2_POOL_BASE||
       comp_rec_get32(wire+192u)!=COMP_WBA_V2_POOL_BYTES||comp_rec_get32(wire+196u)!=COMP_WBA_V2_RECORDING_RESOURCE_BASE||
       comp_rec_get32(wire+200u)!=DIAGNOSTIC_BYTES||comp_rec_get32(wire+204u)!=COMP_WBA_V2_SYSTEM_BASE||
       comp_rec_not_uniform(wire+208u,44u,0u)||comp_rec_get32(wire+ROOT_CRC)!=comp_rec_crc(wire,ROOT_CRC))return false;
    m->sequence=comp_rec_get64(wire+8u);memcpy(m->device_uid,wire+16u,12u);m->format_epoch=comp_rec_get64(wire+28u);
    m->phase=wire[36];m->diagnostic_present=wire[38]!=0u;m->cursor=comp_rec_get32(wire+40u);
    memcpy(m->source_sha256,wire+44u,128u);
    if(!m->sequence||!m->format_epoch||!comp_rec_not_uniform(m->device_uid,12u,0u)||
       !comp_rec_not_uniform(m->device_uid,12u,255u)||m->phase<1u||m->phase>COMP_WBA_MIGRATION_OWNERSHIP_READY||
       (front&&m->phase<COMP_WBA_MIGRATION_MOVE_RECORDING)||
       (!front&&m->phase>COMP_WBA_MIGRATION_ANNOUNCE)||m->cursor%SECTOR||m->cursor>limit(m->phase))return false;
    for(uint8_t i=0u;i<4u;i++)if(!comp_rec_not_uniform(m->source_sha256[i],32u,0u))return false;
    return true;
}
static bool identity_same(const comp_wba_migration_t *a,const comp_wba_migration_t *b)
{
    return a->format_epoch==b->format_epoch&&a->diagnostic_present==b->diagnostic_present&&
        !memcmp(a->device_uid,b->device_uid,12u)&&!memcmp(a->source_sha256,b->source_sha256,128u);
}
bool comp_wba_migration_mount(comp_wba_migration_t *m,const comp_wba_pool_port_t *port,
    const comp_wba_migration_gate_t *gate,const uint8_t uid[12],uint64_t epoch)
{
    if(!m)return false;
    memset(m,0,sizeof(*m));
    if(!port||!port->read||!port->program||!port->erase||!gate||!gate->authorize||!gate->exclusive_idle||
       !uid||!epoch||!comp_rec_not_uniform(uid,12u,0u)||!comp_rec_not_uniform(uid,12u,255u))return false;
    m->port=*port;m->gate=*gate;m->format_epoch=epoch;memcpy(m->device_uid,uid,12u);m->ready=true;
    bool announced=false;uint8_t wire[COMP_WBA_MIGRATION_WIRE_BYTES];
    for(uint8_t bank=0u;bank<4u;bank++)for(uint8_t slot=0u;slot<SLOTS;slot++) {
        uint32_t at=roots[bank]+(uint32_t)slot*COMP_WBA_MIGRATION_WIRE_BYTES;
        if(!read_at(m,at,wire,sizeof(wire)))return false;
        /* Front banks can still hold known old diagnostic bytes. They are
         * not migration roots. Scratch can contain an inactive V1 backup. */
        const char *magic=bank>=2u?"CFL":"CLM";
        bool prefix=wire[0]==(uint8_t)magic[0]&&
            (wire[1]==255u||wire[1]==(uint8_t)magic[1])&&
            (wire[2]==255u||wire[2]==(uint8_t)magic[2]);
        if(comp_rec_not_uniform(wire,sizeof(wire),255u))m->next_slot[bank]=(uint8_t)(slot+1u);
        if(!prefix)continue;
        announced=true;
        if((wire[3]!=255u&&wire[3]!='2')||(wire[4]!=255u&&wire[4]!=2u))return poison(m);
        comp_wba_migration_t candidate={0};
        if(!decode(wire,bank>=2u,&candidate))continue;
        if(memcmp(candidate.device_uid,uid,12u)||candidate.format_epoch!=epoch)return poison(m);
        if(m->loaded) {
            if(!identity_same(m,&candidate))return poison(m);
            if(candidate.sequence==m->sequence&&(candidate.phase!=m->phase||candidate.cursor!=m->cursor))return poison(m);
            if((candidate.sequence>m->sequence&&(candidate.phase<m->phase||(candidate.phase==m->phase&&candidate.cursor<m->cursor)))||
               (candidate.sequence<m->sequence&&(candidate.phase>m->phase||(candidate.phase==m->phase&&candidate.cursor>m->cursor))))return poison(m);
        }
        if(!m->loaded||candidate.sequence>m->sequence) {
            m->sequence=candidate.sequence;m->phase=candidate.phase;m->cursor=candidate.cursor;
            m->diagnostic_present=candidate.diagnostic_present;memcpy(m->source_sha256,candidate.source_sha256,128u);
            m->active_offset=at;m->loaded=true;m->current_mask=0u;
        }
        if(candidate.sequence==m->sequence)m->current_mask|=(uint8_t)(1u<<bank);
    }
    if(announced&&!m->loaded)return poison(m);
    return true;
}
static bool fresh(comp_wba_migration_t *m)
{
    if(!allowed(m)||!m->loaded)return false;
    comp_wba_migration_t latest;
    if(!comp_wba_migration_mount(&latest,&m->port,&m->gate,m->device_uid,m->format_epoch)||!latest.loaded||
       latest.sequence!=m->sequence||latest.phase!=m->phase||latest.cursor!=m->cursor||!identity_same(m,&latest))return poison(m);
    memcpy(m->next_slot,latest.next_slot,sizeof(m->next_slot));m->current_mask=latest.current_mask;m->active_offset=latest.active_offset;
    return true;
}
static bool write_root(comp_wba_migration_t *m,uint8_t bank,const comp_wba_migration_t *next,uint32_t *at)
{
    uint8_t wire[COMP_WBA_MIGRATION_WIRE_BYTES],check[COMP_WBA_MIGRATION_WIRE_BYTES];
    if(m->next_slot[bank]>=SLOTS) {
        if(!m->port.erase(m->port.context,roots[bank])||!erased(m,roots[bank],SECTOR))return poison(m);
        m->next_slot[bank]=0u;
    }
    *at=roots[bank]+(uint32_t)m->next_slot[bank]*COMP_WBA_MIGRATION_WIRE_BYTES;
    if(!erased(m,*at,COMP_WBA_MIGRATION_WIRE_BYTES))return poison(m);
    encode(next,bank>=2u,wire);
    if(!m->port.program(m->port.context,*at,wire,sizeof(wire))||!read_at(m,*at,check,sizeof(check))||
       memcmp(wire,check,sizeof(wire)))return poison(m);
    m->next_slot[bank]++;return true;
}
static bool commit(comp_wba_migration_t *m,uint8_t phase,uint32_t cursor)
{
    if(m->sequence==UINT64_MAX)return poison(m);
    comp_wba_migration_t next=*m;next.sequence++;next.phase=phase;next.cursor=cursor;
    uint8_t first=phase>=COMP_WBA_MIGRATION_MOVE_RECORDING?2u:0u;
    bool same_group=m->loaded&&(m->phase>=COMP_WBA_MIGRATION_MOVE_RECORDING)==(phase>=COMP_WBA_MIGRATION_MOVE_RECORDING);
    const uint8_t group=first;
    if(same_group)for(uint8_t bank=group;bank<(uint8_t)(group+2u);bank++)
        if(m->active_offset>=roots[bank]&&m->active_offset<roots[bank]+SECTOR)first=(uint8_t)(bank^1u);
    /* First promotion may overwrite diagnostic bytes only after all backups
     * have been verified. Later commits always preserve the selected peer. */
    if(!same_group)for(uint8_t bank=first;bank<(uint8_t)(first+2u);bank++) {
        if(!m->port.erase(m->port.context,roots[bank])||!erased(m,roots[bank],SECTOR))return poison(m);
        m->next_slot[bank]=0u;
    }
    uint32_t a,b;
    if(!write_root(m,first,&next,&a)||!write_root(m,(uint8_t)(first^1u),&next,&b))return false;
    m->sequence=next.sequence;m->phase=phase;m->cursor=cursor;m->active_offset=a;m->loaded=true;
    m->current_mask=(uint8_t)(3u<<(first>=2u?2u:0u));return true;
}
static bool sources_match(comp_wba_migration_t *m)
{
    for(uint8_t i=0u;i<4u;i++)if(!hash_matches(m,source_base[i],source_bytes[i],m->source_sha256[i]))return false;
    return true;
}
static bool backups_match(comp_wba_migration_t *m)
{
    for(uint8_t i=0u;i<3u;i++)if(!hash_matches(m,backup_base[i],source_bytes[i],m->source_sha256[i]))return false;
    return true;
}
static bool equal_ranges(comp_wba_migration_t *,uint32_t,uint32_t,uint32_t);
static bool announce_sources_match(comp_wba_migration_t *m)
{
    /* ANNOUNCE is already a durable, authorized intent. A failed first root
     * promotion can have erased/partially written the two front root sectors.
     * Their ORIGINAL bytes are retained in the verified resource backup.
     * Every other V1 byte must still match before any recording is moved. */
    if(!backups_match(m)||!equal_ranges(m,0u,COMP_WBA_MIGRATION_UI_BACKUP,COMP_WBA_V2_LAYOUT_A)||
       !equal_ranges(m,COMP_WBA_V2_LAYOUT_B+SECTOR,COMP_WBA_MIGRATION_UI_BACKUP+COMP_WBA_V2_LAYOUT_B+SECTOR,
            COMP_WBA_NOR_UI_BYTES-COMP_WBA_V2_LAYOUT_B-SECTOR))return false;
    for(uint8_t i=1u;i<4u;i++)if(!hash_matches(m,source_base[i],source_bytes[i],m->source_sha256[i]))return false;
    return true;
}
static bool diagnostic_shape(comp_wba_migration_t *m)
{
    uint8_t header[64];
    if(!read_at(m,OLD_DIAGNOSTIC,header,sizeof(header)))return false;
    if(!memcmp(header,"CRRP",4u)) {
        if(get16(header+4u)!=1u||get16(header+6u)!=64u||
           comp_rec_get32(header+8u)>DIAGNOSTIC_BYTES||comp_rec_get32(header+8u)<128u||
           comp_rec_get32(header+12u)!=2u||comp_rec_get32(header+40u)!=comp_rec_crc(header,40u))return false;
        m->diagnostic_present=true;return true;
    }
    if(!erased(m,OLD_DIAGNOSTIC,DIAGNOSTIC_BYTES))return false;
    m->diagnostic_present=false;return true;
}
static bool legacy_read(void *context,uint32_t off,uint8_t *out,uint32_t n)
{
    comp_wba_migration_t *m=context;
    return off<=COMP_WBA_NOR_RECORDING_BYTES&&n<=COMP_WBA_NOR_RECORDING_BYTES-off&&
        read_at(m,COMP_WBA_NOR_RECORDING_BASE+off,out,n);
}
static bool readonly_program(void *context,uint32_t off,const uint8_t *bytes,uint32_t n)
{(void)context;(void)off;(void)bytes;(void)n;return false;}
static bool readonly_erase(void *context,uint32_t off,uint32_t n)
{(void)context;(void)off;(void)n;return false;}
static uint32_t journal_crc(uint32_t seed,const uint8_t *p,uint32_t n)
{
    for(uint32_t i=0u;i<n;i++) {
        seed^=p[i];for(uint8_t b=0u;b<8u;b++)seed=(seed>>1)^((seed&1u)?UINT32_C(0xEDB88320):0u);
    }
    return seed;
}
static bool legacy_catalog_valid(comp_wba_migration_t *m)
{
    const comp_recording_journal_port_t p={legacy_read,readonly_program,readonly_erase,journal_crc};
    comp_recording_journal_t j;
    return comp_recording_journal_mount_readonly_strict(&j,&p,m,COMP_WBA_NOR_RECORDING_BYTES)==COMP_RECORDING_JOURNAL_OK;
}
static bool diagnostic_read(void *context,uint32_t off,uint8_t *out,size_t n)
{
    comp_wba_migration_t *m=context;
    return off<=DIAGNOSTIC_BYTES&&n<=DIAGNOSTIC_BYTES-off&&read_at(m,OLD_DIAGNOSTIC+off,out,n);
}
static bool diagnostic_valid(comp_wba_migration_t *m)
{
    if(!diagnostic_shape(m))return false;
    if(!m->diagnostic_present)return true;
    comp_asset_store_t store;comp_recording_resource_pack_t pack;uint8_t scratch[256];
    return comp_asset_store_init_reader(&store,COMP_ASSET_STORAGE_EXTERNAL_NOR,DIAGNOSTIC_BYTES,diagnostic_read,m)&&
        comp_recording_resource_pack_mount(&pack,&store)==COMP_RECORDING_RESOURCE_MOUNT_OK&&
        comp_recording_resource_pack_verify_all(&pack,scratch,sizeof(scratch));
}
bool comp_wba_migration_begin(comp_wba_migration_t *m)
{
    if(!allowed(m)||m->loaded||!m->gate.authorize(m->gate.context))return false;
    if(!comp_wba_v2_layout_absent(&m->port)||!legacy_catalog_valid(m)||!diagnostic_valid(m)||
       !erased(m,COMP_WBA_V2_RECORDING_RESOURCE_BASE,DIAGNOSTIC_BYTES)||
       !erased(m,COMP_WBA_NOR_UNASSIGNED_BASE,COMP_WBA_NOR_UNASSIGNED_BYTES))return false;
    for(uint8_t i=0u;i<4u;i++)if(!hash_at(m,source_base[i],source_bytes[i],m->source_sha256[i]))return false;
    return commit(m,COMP_WBA_MIGRATION_BACKUP_UI,0u);
}
bool comp_wba_migration_recover_begin(comp_wba_migration_t *m)
{
    if(!m||m->loaded||!m->port.read||!m->port.program||!m->gate.exclusive_idle||!m->gate.authorize||
       !m->gate.exclusive_idle(m->gate.context)||!m->gate.authorize(m->gate.context))return false;
    m->ready=true;
    uint8_t actual[COMP_WBA_MIGRATION_WIRE_BYTES],expected[COMP_WBA_MIGRATION_WIRE_BYTES];
    for(uint8_t bank=2u;bank<4u;bank++)for(uint8_t slot=0u;slot<SLOTS;slot++) {
        if(!read_at(m,roots[bank]+(uint32_t)slot*COMP_WBA_MIGRATION_WIRE_BYTES,actual,sizeof(actual)))return false;
        if(!memcmp(actual,"CFL",3u))return poison(m);
    }
    if(!legacy_catalog_valid(m)||!diagnostic_valid(m)||
       !erased(m,COMP_WBA_V2_RECORDING_RESOURCE_BASE,DIAGNOSTIC_BYTES)||
       !erased(m,COMP_WBA_NOR_UNASSIGNED_BASE,COMP_WBA_NOR_UNASSIGNED_BYTES))return poison(m);
    for(uint8_t i=0u;i<4u;i++)if(!hash_at(m,source_base[i],source_bytes[i],m->source_sha256[i]))return false;
    m->sequence=1u;m->phase=COMP_WBA_MIGRATION_BACKUP_UI;m->cursor=0u;encode(m,false,expected);
    bool any=false;
    for(uint8_t bank=0u;bank<2u;bank++)for(uint8_t slot=0u;slot<SLOTS;slot++) {
        if(!read_at(m,roots[bank]+(uint32_t)slot*COMP_WBA_MIGRATION_WIRE_BYTES,actual,sizeof(actual)))return false;
        if(!memcmp(actual,"CLM",3u)&&((actual[3]!=255u&&actual[3]!='2')||
             (actual[4]!=255u&&actual[4]!=2u)))return poison(m);
        comp_wba_migration_t valid={0};if(decode(actual,false,&valid))return poison(m);
        any|=comp_rec_not_uniform(actual,sizeof(actual),255u);
        for(size_t i=0u;i<sizeof(actual);i++) {
            uint8_t wanted=slot?255u:expected[i];
            if((actual[i]&wanted)!=wanted)return poison(m);
        }
    }
    if(!any)return poison(m); /* normal erased-media begin has its own gate */
    for(uint8_t bank=0u;bank<2u;bank++)if(!m->port.program(m->port.context,roots[bank],expected,sizeof(expected))||
        !read_at(m,roots[bank],actual,sizeof(actual))||memcmp(actual,expected,sizeof(actual)))return poison(m);
    comp_wba_migration_t recovered;
    if(!comp_wba_migration_mount(&recovered,&m->port,&m->gate,m->device_uid,m->format_epoch))return poison(m);
    *m=recovered;return true;
}
static bool copy_sector(comp_wba_migration_t *m,uint32_t from,uint32_t to,uint8_t *scratch)
{
    uint8_t check[256];
    if(!read_at(m,from,scratch,SECTOR)||!m->port.erase(m->port.context,to)||!erased(m,to,SECTOR))return poison(m);
    for(uint32_t off=0u;off<SECTOR;off+=(uint32_t)sizeof(check)) {
        if(!m->port.program(m->port.context,to+off,scratch+off,sizeof(check))||
           !read_at(m,to+off,check,sizeof(check))||memcmp(check,scratch+off,sizeof(check)))return poison(m);
    }
    return true;
}
static bool equal_ranges(comp_wba_migration_t *m,uint32_t a,uint32_t b,uint32_t n)
{
    uint8_t x[256],y[256];
    for(uint32_t off=0u;off<n;off+=(uint32_t)sizeof(x))
        if(!read_at(m,a+off,x,sizeof(x))||!read_at(m,b+off,y,sizeof(y))||memcmp(x,y,sizeof(x)))return false;
    return true;
}
static uint32_t system_source(uint32_t index)
{
    if(index<4u)return COMP_WBA_MIGRATION_TAIL_BACKUP+index*SECTOR;
    if(index<6u)return COMP_WBA_MIGRATION_UI_BACKUP+OLD_POWER;
    return COMP_WBA_MIGRATION_TAIL_BACKUP+(index-2u)*SECTOR;
}
static bool content_valid(comp_wba_migration_t *m)
{
    if(!backups_match(m)||
       !hash_matches(m,COMP_WBA_V2_POOL_BASE,COMP_WBA_NOR_RECORDING_BYTES,m->source_sha256[3])||
       !equal_ranges(m,COMP_WBA_V2_CATALOG_BASE,COMP_WBA_MIGRATION_CATALOG_BACKUP,CATALOG_BYTES))return false;
    if(m->diagnostic_present&&!equal_ranges(m,COMP_WBA_V2_RECORDING_RESOURCE_BASE,
            COMP_WBA_MIGRATION_UI_BACKUP+OLD_DIAGNOSTIC,DIAGNOSTIC_BYTES))return false;
    for(uint32_t i=0u;i<8u;i++)if(!equal_ranges(m,COMP_WBA_V2_SYSTEM_BASE+i*SECTOR,system_source(i),SECTOR))return false;
    return erased(m,COMP_WBA_V2_SYSTEM_BASE+10u*SECTOR,6u*SECTOR)&&
        erased(m,COMP_WBA_V2_POOL_META_BASE+COMP_WBA_V2_POOL_META_BYTES,10u*SECTOR);
}
bool comp_wba_migration_verify(comp_wba_migration_t *m)
{
    return fresh(m)&&m->phase>=COMP_WBA_MIGRATION_RELOCATED&&content_valid(m)&&
        (m->phase!=COMP_WBA_MIGRATION_RELOCATED||erased(m,COMP_WBA_V2_POOL_META_BASE,COMP_WBA_V2_POOL_META_BYTES));
}
bool comp_wba_migration_poll(comp_wba_migration_t *m,uint8_t *scratch,size_t n,bool *relocated)
{
    if(relocated)*relocated=false;
    if(!relocated||!scratch||n<SECTOR||!fresh(m))return false;
    uint8_t required=(uint8_t)(m->phase>=COMP_WBA_MIGRATION_MOVE_RECORDING?12u:3u);
    if(m->current_mask!=required)return commit(m,m->phase,m->cursor);
    uint32_t from=0u,to=0u,bytes=limit(m->phase);
    switch(m->phase) {
    case COMP_WBA_MIGRATION_BACKUP_UI:
    case COMP_WBA_MIGRATION_BACKUP_TAIL:
    case COMP_WBA_MIGRATION_BACKUP_CATALOG: {
        uint8_t i=(uint8_t)(m->phase-1u);
        if(m->cursor==bytes) {
            if(!hash_matches(m,backup_base[i],source_bytes[i],m->source_sha256[i]))return poison(m);
            if(m->phase==COMP_WBA_MIGRATION_BACKUP_CATALOG&&
               (!m->gate.authorize(m->gate.context)||!sources_match(m)||!backups_match(m)))return poison(m);
            return commit(m,(uint8_t)(m->phase+1u),0u);
        }
        from=source_base[i]+m->cursor;to=backup_base[i]+m->cursor;break;
    }
    case COMP_WBA_MIGRATION_ANNOUNCE:
        if(!announce_sources_match(m))return poison(m);
        return commit(m,COMP_WBA_MIGRATION_MOVE_RECORDING,0u);
    case COMP_WBA_MIGRATION_MOVE_RECORDING:
        if(m->cursor==bytes) {
            if(!hash_matches(m,COMP_WBA_V2_POOL_BASE,bytes,m->source_sha256[3]))return poison(m);
            return commit(m,COMP_WBA_MIGRATION_MOVE_RESOURCE,0u);
        }
        /* Descending memmove: destination is 64 KiB to the right. Every
         * source potentially destroyed was already copied AND checkpointed. */
        from=COMP_WBA_NOR_RECORDING_BASE+bytes-SECTOR-m->cursor;
        to=from+(COMP_WBA_V2_POOL_BASE-COMP_WBA_NOR_RECORDING_BASE);break;
    case COMP_WBA_MIGRATION_MOVE_RESOURCE:
        if(!m->diagnostic_present||m->cursor==bytes) {
            if(m->diagnostic_present&&!equal_ranges(m,COMP_WBA_V2_RECORDING_RESOURCE_BASE,
                    COMP_WBA_MIGRATION_UI_BACKUP+OLD_DIAGNOSTIC,bytes))return poison(m);
            return commit(m,COMP_WBA_MIGRATION_RESTORE_SYSTEM,0u);
        }
        from=COMP_WBA_MIGRATION_UI_BACKUP+OLD_DIAGNOSTIC+m->cursor;
        to=COMP_WBA_V2_RECORDING_RESOURCE_BASE+m->cursor;break;
    case COMP_WBA_MIGRATION_RESTORE_SYSTEM:
        if(m->cursor==bytes)return commit(m,COMP_WBA_MIGRATION_RESTORE_CATALOG,0u);
        from=system_source(m->cursor/SECTOR);to=COMP_WBA_V2_SYSTEM_BASE+m->cursor;break;
    case COMP_WBA_MIGRATION_RESTORE_CATALOG:
        if(m->cursor==bytes)return commit(m,COMP_WBA_MIGRATION_CLEAR_WORKSPACE,0u);
        from=COMP_WBA_MIGRATION_CATALOG_BACKUP+m->cursor;to=COMP_WBA_V2_CATALOG_BASE+m->cursor;break;
    case COMP_WBA_MIGRATION_CLEAR_WORKSPACE:
        if(m->cursor==bytes)return commit(m,COMP_WBA_MIGRATION_RELOCATED,0u);
        to=m->cursor<6u*SECTOR?COMP_WBA_V2_SYSTEM_BASE+10u*SECTOR+m->cursor:
            COMP_WBA_V2_POOL_META_BASE+m->cursor-6u*SECTOR;
        if(!m->port.erase(m->port.context,to)||!erased(m,to,SECTOR))return poison(m);
        return commit(m,m->phase,m->cursor+SECTOR);
    case COMP_WBA_MIGRATION_RELOCATED:
        if(!comp_wba_migration_verify(m))return poison(m);
        *relocated=true;return true;
    case COMP_WBA_MIGRATION_IMPORTING:
    case COMP_WBA_MIGRATION_OWNERSHIP_READY:
        /* This API never retries copying/clearing after ownership import. */
        return false;
    default:return poison(m);
    }
    if(!copy_sector(m,from,to,scratch))return false;
    return commit(m,m->phase,m->cursor+SECTOR);
}
static bool imported_catalog_read(void *context,uint32_t off,uint8_t *out,uint32_t n)
{
    comp_wba_migration_t *m=context;
    const uint32_t data_bytes=COMP_WBA_NOR_RECORDING_BYTES-CATALOG_BYTES;
    if(off>COMP_WBA_NOR_RECORDING_BYTES||n>COMP_WBA_NOR_RECORDING_BYTES-off)return false;
    if(off>=data_bytes)return read_at(m,COMP_WBA_MIGRATION_CATALOG_BACKUP+off-data_bytes,out,n);
    return n<=data_bytes-off&&read_at(m,COMP_WBA_V2_POOL_BASE+off,out,n);
}
bool comp_wba_migration_import_pool(comp_wba_migration_t *m,comp_wba_pool_t *pool)
{
    if(!pool||!fresh(m)||m->phase<COMP_WBA_MIGRATION_RELOCATED||!comp_wba_migration_verify(m))return false;
    if(m->current_mask!=12u&&!commit(m,m->phase,0u))return false;
    /* Capture the durable import intent BEFORE touching CPL2. It is the
     * authorization for deterministic completion of a torn initial snapshot. */
    if(m->phase==COMP_WBA_MIGRATION_RELOCATED&&!commit(m,COMP_WBA_MIGRATION_IMPORTING,0u))return false;
    const comp_recording_journal_port_t p={imported_catalog_read,readonly_program,readonly_erase,journal_crc};
    comp_recording_journal_t journal;
    if(comp_recording_journal_mount_readonly_strict(&journal,&p,m,COMP_WBA_NOR_RECORDING_BYTES)!=COMP_RECORDING_JOURNAL_OK)return poison(m);
    comp_wba_pool_lease_t leases[COMP_RECORDING_JOURNAL_MAX_ENTRIES+1u];size_t count=0u;uint64_t next_id=1u;
    memset(leases,0,sizeof(leases));
    for(uint32_t index=0u;index<COMP_RECORDING_JOURNAL_MAX_ENTRIES;index++) {
        const comp_recording_journal_entry_t *entry=journal.catalog.entries+index;
        if(entry->sync_state==COMP_RECORDING_JOURNAL_EMPTY)continue;
        comp_wba_pool_lease_t *lease=leases+count++;lease->id=entry->recording_id;
        if(next_id<=lease->id)next_id=lease->id+1u;
        lease->transaction_id=1u;lease->object_id=entry->recording_id;
        lease->start=COMP_WBA_V2_POOL_BASE+entry->extent_offset;lease->bytes=entry->reserved_bytes;lease->owner=COMP_WBA_POOL_RECORDING;
        lease->state=entry->sync_state==COMP_RECORDING_JOURNAL_WRITING?COMP_WBA_POOL_WRITING:
            entry->sync_state==COMP_RECORDING_JOURNAL_ERASING?COMP_WBA_POOL_ERASING:COMP_WBA_POOL_SEALED;
        if(lease->state!=COMP_WBA_POOL_WRITING) {
            lease->payload_bytes=lease->bytes;
            if(!hash_at(m,lease->start,lease->bytes,lease->sha256))return false;
        }
    }
    comp_wba_pool_lease_t *backup=leases+count++;backup->id=next_id++;backup->transaction_id=1u;
    backup->object_id=UINT32_C(0x3247494D);backup->start=COMP_WBA_MIGRATION_UI_BACKUP;
    backup->bytes=COMP_WBA_MIGRATION_BACKUP_END-backup->start;backup->payload_bytes=backup->bytes;
    backup->owner=COMP_WBA_POOL_MIGRATION;backup->state=COMP_WBA_POOL_SEALED;
    if(!hash_at(m,backup->start,backup->bytes,backup->sha256))return false;
    if(!comp_wba_pool_initialize_import(pool,&m->port,m->device_uid,m->format_epoch,leases,count,next_id,2u))return poison(m);
    /* A fully verified imported pool is still unavailable to other writers.
     * Retain the original backups until the future activation transaction. */
    if(m->phase==COMP_WBA_MIGRATION_OWNERSHIP_READY)return true;
    return commit(m,COMP_WBA_MIGRATION_OWNERSHIP_READY,0u);
}
