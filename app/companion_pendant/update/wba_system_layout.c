#include "wba_system_layout.h"
#include "wba_workspace_layout.h"
#include "companion_recording_identity.h"
#include <string.h>

#define SYSTEM_BYTES COMP_WBA_NOR_SYSTEM_BYTES
#define SECTOR_BYTES 4096u
#define SEG_A 0x14000u
#define SEG_B 0x1A000u
#define LEG_A 0x10000u

static uint32_t crc32(uint32_t seed,const uint8_t *p,uint32_t n)
{
    uint32_t c=seed^UINT32_MAX;
    for(uint32_t i=0u;i<n;i++) {c^=p[i];for(unsigned k=0u;k<8u;k++)c=(c>>1)^((c&1u)?UINT32_C(0xEDB88320):0u);}
    return c^UINT32_MAX;
}
static bool denied_program(void *c,uint32_t a,const uint8_t*p,uint32_t n)
{(void)c;(void)a;(void)p;(void)n;return false;}
static bool denied_erase(void*c,uint32_t a,uint32_t n)
{(void)c;(void)a;(void)n;return false;}
static bool denied_erase_step(void*c,uint32_t a,uint32_t n,uint32_t*done)
{(void)c;(void)a;(void)n;(void)done;return false;}
static bool denied_identity_program(void*c,uint32_t a,const uint8_t*p,size_t n)
{(void)c;(void)a;(void)p;(void)n;return false;}
static bool denied_identity_erase(void*c,uint32_t a)
{(void)c;(void)a;return false;}
static bool source_read(void *context,uint32_t a,uint8_t *p,size_t n)
{
    comp_wba_system_layout_t *l=context;
    if(a<l->old_static || a-l->old_static>SYSTEM_BYTES || n>SYSTEM_BYTES-(a-l->old_static))return false;
    return l->ports.read(l->ports.context,l->source+a-l->old_static,p,n);
}
static bool segment_read(void*c,uint32_t a,uint8_t*p,uint32_t n)
{return source_read(c,a,p,n);}
static bool identity_read(void *c,uint32_t a,uint8_t*p,size_t n)
{
    comp_wba_system_layout_t *l=c;
    if(a>8192u || n>8192u-a)return false;
    return source_read(l,l->old_static+0x6000u+a,p,n);
}
static bool legacy_read(void *c,uint32_t a,uint8_t *p,uint32_t n)
{
    comp_wba_system_layout_t *l=c;uint32_t data=COMP_WBA_NOR_TOTAL_BYTES-l->old_static-SYSTEM_BYTES;
    if(a<data) {
        if(n>data-a)return false;
        return l->ports.read(l->ports.context,l->old_static+SYSTEM_BYTES+a,p,n);
    }
    if(a-data>8192u || n>8192u-(a-data))return false;
    return source_read(l,l->old_static+LEG_A+a-data,p,n);
}
static bool blank_source(comp_wba_system_layout_t *l,uint32_t offset,uint32_t bytes)
{
    uint8_t p[128];
    for(uint32_t i=0u;i<bytes;i+=sizeof(p)) {
        if(!source_read(l,l->old_static+offset+i,p,sizeof(p)) || comp_rec_not_uniform(p,sizeof(p),255u))return false;
        if(l->ports.keep_alive)l->ports.keep_alive(l->ports.context);
    }
    return true;
}
static bool separate(uint32_t a,uint32_t an,uint32_t b,uint32_t bn)
{return a+an<=b || b+bn<=a;}
static bool root_matches(const uint8_t*p,uint32_t s)
{
    return !memcmp(p,"CFL3",4u) && comp_rec_get32(p+4u)==3u && comp_rec_get32(p+8u)==64u &&
        comp_rec_get32(p+12u)==s && comp_rec_get32(p+16u)==s &&
        comp_rec_get32(p+20u)==s+LEG_A && comp_rec_get32(p+24u)==s+SYSTEM_BYTES &&
        comp_rec_get32(p+28u)==COMP_WBA_NOR_TOTAL_BYTES-s-SYSTEM_BYTES &&
        comp_rec_get32(p+60u)==crc32(0u,p,60u);
}
bool comp_wba_system_layout_init(comp_wba_system_layout_t *l,
    const comp_wba_system_layout_ports_t *p,uint32_t old,uint32_t next,uint32_t tail,
    uint32_t source,const uint8_t uid[12])
{
    if(!l || !p || !p->read || !p->program || !p->erase_sector || !uid)return false;
    memset(l,0,sizeof(*l));l->ports=*p;l->old_static=old;l->new_static=next;l->tail=tail;l->source=source;
    if(old<8192u || next<8192u || old%4096u || next%4096u || source%4096u || tail%4096u ||
       old>COMP_WBA_NOR_TOTAL_BYTES-SYSTEM_BYTES || next>COMP_WBA_NOR_TOTAL_BYTES-SYSTEM_BYTES ||
       source>COMP_WBA_NOR_TOTAL_BYTES-SYSTEM_BYTES || tail<next+SYSTEM_BYTES ||
       tail<old+SYSTEM_BYTES || tail>COMP_WBA_NOR_TOTAL_BYTES ||
       !comp_wba_workspace_layout_valid_at(source_read,l,old))return false;
    if(!source_read(l,old+0x8000u,l->layout_root,64u))return false;
    if(!root_matches(l->layout_root,old) && (!source_read(l,old+0x9000u,l->layout_root,64u) ||
       !root_matches(l->layout_root,old)))return false;
    comp_rec_put32(l->layout_root+12u,next);comp_rec_put32(l->layout_root+16u,next);
    comp_rec_put32(l->layout_root+20u,next+LEG_A);comp_rec_put32(l->layout_root+24u,next+SYSTEM_BYTES);
    comp_rec_put32(l->layout_root+28u,COMP_WBA_NOR_TOTAL_BYTES-next-SYSTEM_BYTES);
    comp_rec_put32(l->layout_root+60u,crc32(0u,l->layout_root,60u));
    comp_rec_identity_t identity;
    comp_rec_identity_port_t ip={identity_read,denied_identity_program,denied_identity_erase,l};
    if(!comp_rec_identity_mount(&identity,&ip,uid))return false;
    comp_segment_port_t sp={segment_read,denied_program,denied_erase_step,l};
    uint64_t epoch=identity.loaded?identity.record.format_epoch:1u;
    comp_segment_result_t sr=comp_segment_catalog_mount_begin(&l->segments,&sp,old+SEG_A,old+SEG_B,
        old+SYSTEM_BYTES,COMP_WBA_NOR_TOTAL_BYTES-old-SYSTEM_BYTES,uid,epoch);
    for(unsigned i=0u;sr==COMP_SEG_PENDING && i<5000u;i++) {
        sr=comp_segment_catalog_mount_poll(&l->segments);if(p->keep_alive)p->keep_alive(p->context);
    }
    if(sr!=COMP_SEG_OK && sr!=COMP_SEG_UNFORMATTED)return false;
    if(sr==COMP_SEG_OK && (!identity.loaded || l->segments.generation==UINT32_MAX ||
       l->segments.bank_serial==UINT32_MAX))return false;
    l->legacy_blank=blank_source(l,LEG_A,8192u);
    if(!l->legacy_blank) {
        comp_recording_journal_t j;
        comp_recording_journal_port_t jp={legacy_read,denied_program,denied_erase,crc32};
        if(comp_recording_journal_mount_readonly_strict(&j,&jp,l,
            COMP_WBA_NOR_TOTAL_BYTES-old-SYSTEM_BYTES+8192u)!=COMP_RECORDING_JOURNAL_OK)return false;
        l->legacy=j.catalog;
        if(l->legacy.generation==UINT32_MAX)return false;
        for(unsigned k=0u;k<7u;k++) {
            comp_recording_journal_entry_t *e=&l->legacy.entries[k];
            if(e->sync_state==COMP_RECORDING_JOURNAL_EMPTY)continue;
            uint64_t session;
            if((e->sync_state!=COMP_RECORDING_JOURNAL_UNSYNCED && e->sync_state!=COMP_RECORDING_JOURNAL_ACKED) ||
               !identity.loaded || !comp_rec_identity_find(&identity,e->recording_id,&session))return false;
            uint32_t physical=old+SYSTEM_BYTES+e->extent_offset;
            if(physical<next+SYSTEM_BYTES || physical>tail || e->reserved_bytes>tail-physical)return false;
            uint32_t within=e->payload_offset-e->extent_offset;
            e->extent_offset=physical-next-SYSTEM_BYTES;e->payload_offset=e->extent_offset+within;
        }
        l->legacy.magic=UINT32_C(0x324A5243);l->legacy.generation++;l->legacy.crc32=0u;
        l->legacy.crc32=crc32(0u,(const uint8_t*)&l->legacy,sizeof(l->legacy));
    }
    if(sr==COMP_SEG_OK)for(uint8_t k=0u;k<64u;k++) {
        comp_segment_entry_t e,next_entry;sr=comp_segment_catalog_read(&l->segments,k,&e);
        if(sr==COMP_SEG_NOT_FOUND)continue;
        if(sr!=COMP_SEG_OK || (e.state!=COMP_SEG_UNSYNCED && e.state!=COMP_SEG_ACKED) ||
           !comp_segment_catalog_rebase_entry(&e,old+SYSTEM_BYTES,next+SYSTEM_BYTES,tail,&next_entry))return false;
        uint32_t physical=old+SYSTEM_BYTES+e.extent_offset;
        if(!l->legacy_blank)for(unsigned q=0u;q<7u;q++) {
            const comp_recording_journal_entry_t *x=&l->legacy.entries[q];
            if(x->sync_state && !separate(physical,e.reserved_bytes,next+SYSTEM_BYTES+x->extent_offset,x->reserved_bytes))return false;
        }
    }
    l->immutable_source=source>=tail && source<=COMP_WBA_NOR_TOTAL_BYTES-SYSTEM_BYTES-8192u;
    l->usable=true;return true;
}

static bool render(comp_wba_system_layout_t *l,uint32_t at,uint8_t out[256])
{
    /* The old signed confirmation names the old geometry. On growth/shrink
     * the new App creates its freshly verified joint receipt before tail
     * release; Boot keeps the installation anchor until then. Never carry an
     * old-geometry receipt as authority inside a different metadata arena. */
    if(l->old_static!=l->new_static && at>=0xA000u && at<0xC000u) {
        memset(out,255,256u);return true;
    }
    if(at>=SEG_A) return comp_segment_catalog_rebase_page(&l->segments,l->new_static+SEG_A,
        l->new_static+SEG_B,l->new_static+SYSTEM_BYTES,
        COMP_WBA_NOR_TOTAL_BYTES-l->new_static-SYSTEM_BYTES,l->tail,(at-SEG_A)/256u,out);
    if(at>=LEG_A && at<LEG_A+8192u) {
        memset(out,255,256u);
        if(!l->legacy_blank && at-LEG_A<sizeof(l->legacy)) {
            size_t n=sizeof(l->legacy)-(at-LEG_A);if(n>256u)n=256u;
            memcpy(out,((const uint8_t*)&l->legacy)+(at-LEG_A),n);
        }
        return true;
    }
    if(!source_read(l,l->old_static+at,out,256u))return false;
    if(at==0x8000u || at==0x9000u)memcpy(out,l->layout_root,64u);
    return true;
}
static bool equal_target(comp_wba_system_layout_t *l,uint32_t at,const uint8_t p[256],bool *equal)
{
    uint8_t check[64];*equal=true;
    for(uint32_t i=0u;i<256u;i+=sizeof(check)) {
        if(!l->ports.read(l->ports.context,l->new_static+at+i,check,sizeof(check)))return false;
        if(memcmp(p+i,check,sizeof(check)))*equal=false;
    }
    return true;
}
static bool failed(comp_wba_system_layout_t *l)
{l->usable=false;return false;}
bool comp_wba_system_layout_step(comp_wba_system_layout_t *l,uint8_t *p,size_t cap,bool *done)
{
    if(!l || !p || cap<256u || !done || !l->usable || !l->immutable_source)return false;
    *done=false;if(l->finished){*done=true;return true;}
    bool equal;uint32_t at=l->sector+l->offset;
    if(l->ports.keep_alive)l->ports.keep_alive(l->ports.context);
    if(l->phase==1u) {
        if(!l->ports.erase_sector(l->ports.context,l->new_static+l->sector))return failed(l);
        l->phase=2u;l->offset=0u;return true;
    }
    if(!render(l,at,p))return failed(l);
    if(l->phase==0u) {
        if(!equal_target(l,at,p,&equal))return failed(l);
        if(!equal){l->phase=1u;return true;}
    } else {
        if(comp_rec_not_uniform(p,256u,255u) && !l->ports.program(l->ports.context,l->new_static+at,p,256u))return failed(l);
        if(!equal_target(l,at,p,&equal) || !equal)return failed(l);
    }
    l->offset+=256u;
    if(l->offset==SECTOR_BYTES) {
        l->sector+=SECTOR_BYTES;l->offset=0u;l->phase=0u;
        if(l->sector==SYSTEM_BYTES){l->finished=true;*done=true;}
    }
    return true;
}
bool comp_wba_system_layout_verify(comp_wba_system_layout_t *l,uint8_t *p,size_t cap)
{
    if(!l || !l->usable || !l->finished || !p || cap<256u)return false;
    for(uint32_t at=0u;at<SYSTEM_BYTES;at+=256u) {
        bool equal;
        if(!render(l,at,p) || !equal_target(l,at,p,&equal) || !equal)return failed(l);
        if(l->ports.keep_alive)l->ports.keep_alive(l->ports.context);
    }
    return comp_wba_workspace_layout_valid_at(l->ports.read,l->ports.context,l->new_static);
}
