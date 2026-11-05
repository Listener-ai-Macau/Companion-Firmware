#include "wba_system_anchor.h"
#include "wba_workspace_layout.h"
#include <string.h>

static uint32_t u32(const uint8_t *p)
{return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static uint64_t u64(const uint8_t *p)
{return (uint64_t)u32(p)|((uint64_t)u32(p+4u)<<32);}
static void p32(uint8_t *p,uint32_t v)
{p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);p[2]=(uint8_t)(v>>16);p[3]=(uint8_t)(v>>24);}
static void p64(uint8_t *p,uint64_t v){p32(p,(uint32_t)v);p32(p+4u,(uint32_t)(v>>32));}
static uint32_t anchor_address(unsigned sector)
{return COMP_WBA_NOR_TOTAL_BYTES-COMP_WBA_SYSTEM_ANCHOR_BYTES+sector*4096u;}
static const uint8_t *wire(const comp_wba_system_anchor_t *a){return a->record+96u;}
static bool ff(const uint8_t *p,size_t n){while(n--)if(*p++!=255u)return false;return true;}
static bool own(const uint8_t *p)
{const uint8_t m[4]={'W','S','A','2'};for(unsigned i=0;i<4u;i++)if((p[i]&m[i])!=m[i])return false;return true;}
static bool fail(comp_wba_system_anchor_t *a){a->usable=false;return false;}
static bool overlap(const uint8_t *x,size_t xn,const uint8_t *y,size_t yn)
{uintptr_t a=(uintptr_t)x,b=(uintptr_t)y;return a<=b?b-a<xn:a-b<yn;}
static bool scratch_valid(const comp_wba_system_anchor_t *a,uint8_t *p,size_t n)
{return p && n>=256u && n<=4096u && !overlap(p,n,(const uint8_t *)a,sizeof(*a));}
static bool held(comp_wba_system_anchor_t *a)
{return a->ports.idle(a->ports.context) && a->ports.claim_held(a->ports.context,u32(a->record+20u),u32(wire(a)+52u));}
static bool record_valid(const uint8_t *r)
{
    comp_wba_system_pair_t pair;
    uint32_t old=u32(r+16u),base=u32(r+20u);
    return !memcmp(r,"WSA2",4u) && r[4]==1u && r[5]>=1u && r[5]<=4u &&
        r[6]==44u && r[7]==2u && u64(r+8u) && old>=8192u && !(old%4096u) &&
        old<=COMP_WBA_NOR_TOTAL_BYTES-COMP_WBA_NOR_SYSTEM_BYTES-4096u &&
        comp_wba_system_record_valid(r+64u) && r[69u]==COMP_WBA_SYSTEM_PAIR_READY &&
        comp_wba_system_wire_decode(r+96u,452u,&pair) && u32(r+80u)==base &&
        base==COMP_WBA_NOR_TOTAL_BYTES-pair.staging_bytes &&
        base>=(old>pair.static_bytes?old:pair.static_bytes)+pair.system_bytes &&
        u32(r+24u)==pair.resource_offset+pair.static_bytes && u32(r+28u)==pair.system_bytes &&
        u32(r+552u)==comp_wba_update_wire_crc32(r,552u);
}
/* Read ALL bytes, including padding, to establish erased versus touched. */
static bool read_sector(const comp_wba_system_anchor_ports_t *p,unsigned sector,
    uint8_t out[556],bool *blank,bool *padding)
{
    uint8_t chunk[256];uint32_t base=anchor_address(sector);
    if(!p->read(p->context,base,out,556u))return false;
    *blank=ff(out,556u);*padding=true;
    for(uint32_t at=556u;at<4096u;){size_t n=4096u-at<sizeof(chunk)?4096u-at:sizeof(chunk);
        if(!p->read(p->context,base+at,chunk,n))return false;
        if(!ff(chunk,n))*padding=false;
        at+=(uint32_t)n;}
    *blank=*blank && *padding;return true;
}
bool comp_wba_system_anchor_mount(comp_wba_system_anchor_t *a,const comp_wba_system_anchor_ports_t *p,bool *blank)
{
    uint8_t candidate[556];bool all_blank=true;
    if(!a || !p || !blank || !p->read || !p->program || !p->erase_sector || !p->idle ||
        !p->claim_held || !p->keep_alive || !comp_wba_update_p256_trust_configured(&p->trust))return false;
    comp_wba_system_anchor_ports_t copy=*p;memset(a,0,sizeof(*a));a->ports=copy;*blank=false;
    for(unsigned sector=0;sector<2u;sector++){
        bool empty,padding;
        if(!read_sector(&copy,sector,candidate,&empty,&padding))return false;
        if(empty)continue;
        all_blank=false;
        if(!own(candidate) || !padding)return false;
        if(!record_valid(candidate))continue;
        if(a->loaded && u64(candidate+8u)==u64(a->record+8u) && memcmp(candidate,a->record,556u))return false;
        if(!a->loaded || u64(candidate+8u)>u64(a->record+8u)){
            memcpy(a->record,candidate,556u);a->sector=(uint8_t)sector;a->loaded=true;}
    }
    if(!a->loaded && !all_blank)return false;
    if(a->loaded){comp_wba_system_pair_t pair;
        if(!comp_wba_system_wire_authorize(wire(a),452u,&copy.trust,&pair))return false;}
    *blank=!a->loaded;a->mounted=a->usable=true;return true;
}
static bool store(comp_wba_system_anchor_t *a,const uint8_t next[556])
{
    uint8_t check[556];bool blank,padding;
    unsigned sector=a->loaded?a->sector^1u:0u;
    if(!held(a) || !record_valid(next) ||
        !a->ports.erase_sector(a->ports.context,anchor_address(sector)) ||
        !held(a) || !a->ports.program(a->ports.context,anchor_address(sector),next,556u) ||
        !read_sector(&a->ports,sector,check,&blank,&padding) || !padding || memcmp(check,next,556u))return fail(a);
    memcpy(a->record,next,556u);a->sector=(uint8_t)sector;a->loaded=true;return true;
}
static bool digest_range(comp_wba_system_anchor_t *a,uint32_t address,uint32_t bytes,
    uint8_t *scratch,size_t capacity,uint8_t digest[32],uint32_t *crc)
{
    companion_sha256_t hash;uint32_t sum=UINT32_MAX;
    companion_sha256_init(&hash);
    for(uint32_t at=0u;at<bytes;){size_t n=bytes-at<capacity?bytes-at:capacity;
        if(!held(a) || !a->ports.read(a->ports.context,address+at,scratch,n))return fail(a);
        companion_sha256_update(&hash,scratch,n);
        if(crc)for(size_t i=0u;i<n;i++){sum^=scratch[i];for(unsigned k=0;k<8u;k++)sum=(sum>>1)^((sum&1u)?UINT32_C(0xEDB88320):0u);}
        at+=(uint32_t)n;a->ports.keep_alive(a->ports.context);}
    companion_sha256_final(&hash,digest);if(crc)*crc=sum^UINT32_MAX;return true;
}
bool comp_wba_system_anchor_verify_snapshot(comp_wba_system_anchor_t *a,uint8_t *scratch,size_t capacity)
{
    uint8_t digest[32];
    if(!a || !a->mounted || !a->usable || !a->loaded || !scratch_valid(a,scratch,capacity))return false;
    return digest_range(a,u32(a->record+20u)+u32(a->record+24u),u32(a->record+28u),scratch,capacity,digest,NULL) &&
        (!memcmp(digest,a->record+32u,32u) || fail(a));
}
bool comp_wba_system_anchor_prepare(comp_wba_system_anchor_t *a,const uint8_t ready[488],
    uint32_t old,uint8_t *scratch,size_t capacity)
{
    uint8_t latest[488],next[556],digest[32];bool blank;
    comp_wba_system_pair_t pair;comp_wba_system_journal_t journal;
    if(!a || !a->mounted || !a->usable || !ready || !scratch_valid(a,scratch,capacity) ||
        overlap(scratch,capacity,ready,488u) ||
        !comp_wba_system_record_valid(ready) || ready[5]!=COMP_WBA_SYSTEM_PAIR_READY ||
        !comp_wba_system_wire_authorize(ready+32u,452u,&a->ports.trust,&pair))return false;
    if(a->loaded){
        if(a->record[5]!=COMP_WBA_SYSTEM_ANCHOR_PREPARED || u32(a->record+16u)!=old ||
            memcmp(a->record+64u,ready,488u))return false;
        return comp_wba_system_anchor_verify_snapshot(a,scratch,capacity);
    }
    comp_wba_system_journal_ports_t jp={a->ports.read,a->ports.program,a->ports.erase_sector,a->ports.context,old};
    if(!comp_wba_workspace_layout_valid_at(a->ports.read,a->ports.context,old) ||
        !comp_wba_system_journal_mount(&journal,&jp,latest,&blank) || blank || memcmp(latest,ready,488u))return false;
    memset(next,0,sizeof(next));memcpy(next,"WSA2",4u);next[4]=1u;next[5]=1u;next[6]=44u;next[7]=2u;
    p64(next+8u,1u);p32(next+16u,old);p32(next+20u,u32(ready+16u));
    p32(next+24u,pair.resource_offset+pair.static_bytes);p32(next+28u,pair.system_bytes);memcpy(next+64u,ready,488u);
    p32(next+552u,comp_wba_update_wire_crc32(next,552u));
    if(!record_valid(next))return false;
    memcpy(a->record,next,556u); /* Not committed/loaded: only establishes bounds. */
    if(!held(a))return fail(a);
    companion_sha256_t hash;companion_sha256_init(&hash);
    uint32_t dest=u32(next+20u)+u32(next+24u);
    for(uint32_t sector=0u;sector<pair.system_bytes;sector+=4096u){
        if(!held(a) || !a->ports.erase_sector(a->ports.context,dest+sector))return fail(a);
        for(uint32_t at=0u;at<4096u;){size_t n=4096u-at<capacity?4096u-at:capacity;
            if(!held(a) || !a->ports.read(a->ports.context,old+sector+at,scratch,n))return fail(a);
            companion_sha256_update(&hash,scratch,n);
            if(!held(a) || !a->ports.program(a->ports.context,dest+sector+at,scratch,n))return fail(a);
            at+=(uint32_t)n;a->ports.keep_alive(a->ports.context);}
    }
    companion_sha256_final(&hash,next+32u);
    if(!digest_range(a,dest,pair.system_bytes,scratch,capacity,digest,NULL) || memcmp(digest,next+32u,32u))return fail(a);
    p32(next+552u,comp_wba_update_wire_crc32(next,552u));return store(a,next);
}
bool comp_wba_system_anchor_reprepare_first(comp_wba_system_anchor_t *a,
    const uint8_t ready[488],const uint8_t current[452],uint32_t old,
    uint8_t *scratch,size_t capacity)
{
    uint8_t expected[556],other[556],latest[488];bool blank,padding;
    comp_wba_system_pair_t pair,active;comp_wba_system_journal_t journal;
    if(!a || !ready || !current || !scratch_valid(a,scratch,capacity) ||
       overlap(scratch,capacity,ready,488u) || overlap(scratch,capacity,current,452u) ||
       !a->ports.running_pair_verified || !a->ports.running_pair_verified(a->ports.context,current) ||
       !comp_wba_system_wire_authorize(current,452u,&a->ports.trust,&active) || active.static_bytes!=old ||
       !comp_wba_system_record_valid(ready) || ready[5]!=COMP_WBA_SYSTEM_PAIR_READY ||
       !comp_wba_system_wire_authorize(ready+32u,452u,&a->ports.trust,&pair) ||
       pair.firmware.manifest.component_version<=active.firmware.manifest.component_version ||
       !comp_wba_workspace_layout_valid_at(a->ports.read,a->ports.context,old))return false;
    comp_wba_system_journal_ports_t jp={a->ports.read,a->ports.program,a->ports.erase_sector,a->ports.context,old};
    if(!comp_wba_system_journal_mount(&journal,&jp,latest,&blank) || blank || memcmp(latest,ready,488u))return false;
    memset(expected,0,sizeof(expected));memcpy(expected,"WSA2",4u);
    expected[4]=expected[5]=1u;expected[6]=44u;expected[7]=2u;p64(expected+8u,1u);
    p32(expected+16u,old);p32(expected+20u,u32(ready+16u));
    p32(expected+24u,pair.resource_offset+pair.static_bytes);p32(expected+28u,pair.system_bytes);
    memcpy(expected+64u,ready,488u);
    /* Establish only authenticated, bounded read coordinates. This is not a
     * mounted or committed anchor and cannot authorize the resident installer. */
    memcpy(a->record,expected,sizeof(expected));a->mounted=a->loaded=a->usable=false;
    if(!held(a) || !digest_range(a,u32(expected+20u)+u32(expected+24u),
       pair.system_bytes,scratch,capacity,expected+32u,NULL))return false;
    p32(expected+552u,comp_wba_update_wire_crc32(expected,552u));
    if(!record_valid(expected) || !read_sector(&a->ports,1u,other,&blank,&padding) || !blank ||
       !read_sector(&a->ports,0u,other,&blank,&padding) || blank || !padding || record_valid(other))return false;
    for(size_t i=0u;i<sizeof(other);i++)if((other[i]&expected[i])!=expected[i])return false;
    if(!held(a) || !a->ports.erase_sector(a->ports.context,anchor_address(0u)) ||
       !read_sector(&a->ports,0u,other,&blank,&padding) || !blank)return false;
    if(!comp_wba_system_anchor_mount(a,&a->ports,&blank) || !blank)return false;
    return comp_wba_system_anchor_prepare(a,ready,old,scratch,capacity);
}
bool comp_wba_system_anchor_verify_candidate(comp_wba_system_anchor_t *a,uint8_t *scratch,size_t capacity)
{
    uint8_t digest[32];uint32_t crc;
    if(!a || !a->mounted || !a->usable || !a->loaded || !held(a) || !scratch_valid(a,scratch,capacity) ||
        a->record[5]>COMP_WBA_SYSTEM_ANCHOR_INSTALLING)return false;
    const uint8_t *w=wire(a);uint32_t base=u32(a->record+20u);
    for(unsigned part=0;part<2u;part++){
            const uint8_t *m=w+(part?240u:96u);
            uint32_t at=base+u32(w+(part?48u:44u));
            if(!digest_range(a,at,u32(m+28u),scratch,capacity,digest,&crc) || memcmp(digest,m+36u,32u) || crc!=u32(m+32u))return fail(a);
    }
    if(!a->ports.read(a->ports.context,base,scratch,8u))return fail(a);
    uint32_t sp=u32(scratch),reset=u32(scratch+4u);
    if(!comp_wba_sram_stack_pointer_valid(sp) || !(reset&1u) ||
        (reset&~1u)<COMP_WBA_APP_ADDRESS || (reset&~1u)>=COMP_WBA_APP_ADDRESS+u32(w+124u) ||
        !comp_wba_system_anchor_verify_snapshot(a,scratch,capacity))return fail(a);
    return true;
}
bool comp_wba_system_anchor_advance(comp_wba_system_anchor_t *a,uint8_t phase,uint8_t *scratch,size_t capacity)
{
    uint8_t next[556];
    if(!a || !a->mounted || !a->usable || !a->loaded || !held(a) || !scratch_valid(a,scratch,capacity) ||
        phase!=a->record[5]+1u || phase>4u || u64(a->record+8u)==UINT64_MAX)return false;
    const uint8_t *w=wire(a);
    if(phase==COMP_WBA_SYSTEM_ANCHOR_INSTALLING){
        if(!comp_wba_system_anchor_verify_candidate(a,scratch,capacity))return false;
    }else if(phase==COMP_WBA_SYSTEM_ANCHOR_INSTALLED){
        if(!a->ports.installed_pair_verified || !a->ports.installed_pair_verified(a->ports.context,w))return false;
    }else if(!a->ports.running_pair_verified || !a->ports.running_pair_verified(a->ports.context,w))return false;
    memcpy(next,a->record,556u);next[5]=phase;p64(next+8u,u64(next+8u)+1u);
    p32(next+552u,comp_wba_update_wire_crc32(next,552u));return store(a,next);
}
