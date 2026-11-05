#include "wba_system_confirmed.h"
#include "wba_workspace_layout.h"
#include <string.h>
static uint32_t get32(const uint8_t*p)
{return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static uint64_t get64(const uint8_t*p){return get32(p)|((uint64_t)get32(p+4u)<<32);}
static void put64(uint8_t*p,uint64_t v)
{for(unsigned i=0u;i<8u;i++)p[i]=(uint8_t)(v>>(8u*i));}
static void put32(uint8_t*p,uint32_t v)
{for(unsigned i=0u;i<4u;i++)p[i]=(uint8_t)(v>>(8u*i));}
static bool blank_bytes(const uint8_t*p,size_t n)
{for(size_t i=0u;i<n;i++)if(p[i]!=255u)return false;return true;}
static uint32_t address(uint32_t s,uint8_t b)
{return s+(b?COMP_WBA_SYSTEM_CONFIRMED_B:COMP_WBA_SYSTEM_CONFIRMED_A);}
static bool valid(const comp_wba_system_confirmed_ports_t*p,const uint8_t*r,uint32_t s)
{
    comp_wba_system_pair_t pair;
    return !memcmp(r,"CFC2",4u) && r[4]==1u && r[5]==1u && r[6]==216u && r[7]==1u &&
        get64(r+8u) && get32(r+468u)==comp_wba_update_wire_crc32(r,468u) &&
        comp_wba_system_wire_authorize(r+16u,452u,&p->trust,&pair) && pair.static_bytes==s;
}
bool comp_wba_system_confirmed_mount(comp_wba_system_confirmed_t *c,
    const comp_wba_system_confirmed_ports_t *p,uint32_t s,bool *blank)
{
    uint8_t other[COMP_WBA_SYSTEM_CONFIRMED_BYTES],page[256];bool occupied=false;
    if(!c || !p || !p->read || !p->program || !p->erase_sector || !p->pair_verified || !blank ||
       !comp_wba_update_p256_trust_configured(&p->trust) || s<8192u || s%4096u ||
       s>COMP_WBA_NOR_TOTAL_BYTES-COMP_WBA_NOR_SYSTEM_BYTES)return false;
    memset(c,0,sizeof(*c));c->ports=*p;c->static_bytes=s;*blank=false;
    for(uint8_t b=0u;b<2u;b++) {
        bool empty=true,padding=true;
        if(!p->read(p->context,address(s,b),other,sizeof(other)))return false;
        if(!blank_bytes(other,sizeof(other)))empty=false;
        for(uint32_t at=sizeof(other);at<4096u;) {
            size_t n=4096u-at;if(n>sizeof(page))n=sizeof(page);
            if(!p->read(p->context,address(s,b)+at,page,n))return false;
            if(!blank_bytes(page,n)){padding=false;empty=false;}at+=(uint32_t)n;
        }
        if(p->keep_alive)p->keep_alive(p->context);
        if(empty)continue;
        occupied=true;
        if(!padding)return false;
        /* Only a partial own prefix can be ignored beside an intact peer. */
        if(!valid(p,other,s)) {
            for(unsigned i=0u;i<4u;i++)if(other[i]!=(uint8_t)"CFC2"[i] && other[i]!=255u)return false;
            if(other[4]!=1u && other[4]!=255u)return false;
            continue;
        }
        if(c->loaded && get64(other+8u)==get64(c->record+8u) && memcmp(other,c->record,sizeof(other)))return false;
        if(!c->loaded || get64(other+8u)>get64(c->record+8u)){memcpy(c->record,other,sizeof(other));c->bank=b;c->loaded=true;}
    }
    if(occupied && !c->loaded)return false;
    *blank=!occupied;c->usable=true;return true;
}
bool comp_wba_system_confirmed_store(comp_wba_system_confirmed_t *c,const uint8_t w[452])
{
    uint8_t next[COMP_WBA_SYSTEM_CONFIRMED_BYTES],check[COMP_WBA_SYSTEM_CONFIRMED_BYTES];
    if(!c || !c->usable || !w)return false;
    uint64_t seq=c->loaded?get64(c->record+8u):0u;
    if(seq==UINT64_MAX)return false;
    memset(next,0,sizeof(next));memcpy(next,"CFC2",4u);next[4]=next[5]=1u;next[6]=216u;next[7]=1u;
    put64(next+8u,seq+1u);memcpy(next+16u,w,452u);put32(next+468u,comp_wba_update_wire_crc32(next,468u));
    if(!valid(&c->ports,next,c->static_bytes) ||
       !comp_wba_workspace_layout_valid_at(c->ports.read,c->ports.context,c->static_bytes) ||
       !c->ports.pair_verified(c->ports.context,w))return false;
    if(c->loaded && (get32(w+112u)<get32(c->record+128u) ||
       get32(w+256u)<get32(c->record+272u)))return false;
    if(c->loaded && !memcmp(c->record+16u,w,452u))return true;
    uint8_t b=c->loaded?(uint8_t)(c->bank^1u):0u;uint32_t at=address(c->static_bytes,b);
    if(!c->ports.erase_sector(c->ports.context,at) || !c->ports.program(c->ports.context,at,next,sizeof(next)) ||
       !c->ports.read(c->ports.context,at,check,sizeof(check)) || memcmp(next,check,sizeof(next))) {
        c->usable=false;return false;
    }
    for(uint32_t offset=sizeof(next);offset<4096u;) {
        size_t n=4096u-offset;if(n>sizeof(check))n=sizeof(check);
        if(!c->ports.read(c->ports.context,at+offset,check,n) || !blank_bytes(check,n)) {
            c->usable=false;return false;
        }
        offset+=(uint32_t)n;
    }
    memcpy(c->record,next,sizeof(next));c->loaded=true;c->bank=b;return true;
}
bool comp_wba_system_confirmed_find(comp_wba_system_confirmed_t *c,
    const comp_wba_system_confirmed_ports_t *p)
{
    comp_wba_system_confirmed_t candidate;uint8_t locator[4];bool found=false;
    if(!c || !p || !p->read || !p->pair_verified)return false;
    memset(c,0,sizeof(*c));
    for(uint32_t s=8192u;s<=COMP_WBA_NOR_TOTAL_BYTES-COMP_WBA_NOR_SYSTEM_BYTES;s+=4096u) {
        if(!p->read(p->context,s+0x8000u,locator,sizeof(locator)))return false;
        if(p->keep_alive)p->keep_alive(p->context);
        if(memcmp(locator,"CFL3",4u)) {
            /* A lost A root can leave the durable B locator intact. */
            if(!p->read(p->context,s+0x9000u,locator,sizeof(locator)))return false;
            if(memcmp(locator,"CFL3",4u))continue;
        }
        bool blank;
        if(!comp_wba_workspace_layout_valid_at(p->read,p->context,s) ||
           !comp_wba_system_confirmed_mount(&candidate,p,s,&blank) || blank ||
           !p->pair_verified(p->context,candidate.record+16u))continue;
        if(found && (s!=c->static_bytes || memcmp(candidate.record+16u,c->record+16u,452u)))return false;
        *c=candidate;found=true;
    }
    return found;
}
