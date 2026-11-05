#include "wba_system_install.h"
#include <string.h>
enum {COMPARE=1,ERASE=2,WRITE=3,METADATA=4,VERIFY=5,FINISH=6,COMPLETE=7,FAILED=8};
static uint32_t u32(const uint8_t *p)
{return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static const uint8_t *wire(const comp_wba_system_installer_t *i){return i->anchor->record+96u;}
static const uint8_t *manifest(const comp_wba_system_installer_t *i){return wire(i)+(i->component?240u:96u);}
static uint32_t bytes(const comp_wba_system_installer_t *i){return u32(manifest(i)+28u);}
static uint32_t page_bytes(const comp_wba_system_installer_t *i){return i->component?4096u:8192u;}
static uint32_t destination(const comp_wba_system_installer_t *i,uint32_t at)
{return (i->component?0u:COMP_WBA_APP_ADDRESS)+at;}
static bool overlap(const uint8_t *a,size_t an,const uint8_t *b,size_t bn)
{uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return x<=y?y-x<an:x-y<bn;}
static bool scratch_valid(comp_wba_system_installer_t *i,uint8_t *p,size_t n)
{return p && n>=512u && n<=8192u && !overlap(p,n,(const uint8_t *)i,sizeof(*i)) &&
    !overlap(p,n,(const uint8_t *)i->anchor,sizeof(*i->anchor));}
static bool held(comp_wba_system_installer_t *i)
{comp_wba_system_anchor_t*a=i->anchor;return a->usable && a->ports.idle(a->ports.context) &&
    a->ports.claim_held(a->ports.context,u32(a->record+20u),u32(wire(i)+52u));}
static comp_wba_system_install_action_t fail(comp_wba_system_installer_t *i)
{if(i){i->usable=false;i->stage=FAILED;}return COMP_WBA_SYSTEM_INSTALL_RECOVERY;}
static bool read_destination(comp_wba_system_installer_t *i,uint32_t at,uint8_t *out,size_t n)
{return i->component?i->anchor->ports.read(i->anchor->ports.context,at,out,n):i->ports.flash_read(i->ports.context,at,out,n);}
static bool expected(comp_wba_system_installer_t *i,uint32_t at,uint8_t *out,size_t n)
{
    memset(out,255,n);
    if(at>=bytes(i))return true;
    size_t count=bytes(i)-at<n?bytes(i)-at:n;
    uint32_t base=u32(i->anchor->record+20u)+u32(wire(i)+(i->component?48u:44u));
    return i->anchor->ports.read(i->anchor->ports.context,base+at,out,count);
}
static void hash_reset(comp_wba_system_installer_t *i)
{i->offset=0u;i->crc=UINT32_MAX;companion_sha256_init(&i->hash);}
bool comp_wba_system_install_init(comp_wba_system_installer_t *i,comp_wba_system_anchor_t *a,
    const comp_wba_system_install_ports_t *p,uint8_t *scratch,size_t n)
{
    comp_wba_system_pair_t pair;
    if(!i || !a || overlap((const uint8_t *)i,sizeof(*i),(const uint8_t *)a,sizeof(*a)))return false;
    /* A refused re-init must never leave an earlier transaction pollable. */
    i->usable=false;i->stage=FAILED;
    if(!p || (scratch && overlap(scratch,n,(const uint8_t *)p,sizeof(*p))) ||
        !a->mounted || !a->loaded || !a->usable || a->record[5]<1u || a->record[5]>3u ||
        !p->flash_read || !p->flash_erase_page || !p->flash_program ||
        !p->layout_authorized || !p->layout_step || !p->layout_verified ||
        !comp_wba_system_wire_authorize(a->record+96u,452u,&a->ports.trust,&pair))return false;
    comp_wba_system_install_ports_t copy=*p;memset(i,0,sizeof(*i));i->ports=copy;i->anchor=a;
    if(!scratch_valid(i,scratch,n) || !held(i))return false;
    if(a->record[5]==COMP_WBA_SYSTEM_ANCHOR_INSTALLED){i->stage=VERIFY;hash_reset(i);}
    else {
        if(!p->layout_authorized(p->context,a->record))return false;
        if(a->record[5]==COMP_WBA_SYSTEM_ANCHOR_PREPARED){
            if(!comp_wba_system_anchor_advance(a,COMP_WBA_SYSTEM_ANCHOR_INSTALLING,scratch,n/2u))return false;
        }else if(!comp_wba_system_anchor_verify_candidate(a,scratch,n/2u))return false;
        i->stage=COMPARE;
    }
    i->usable=true;return true;
}
static void next_page(comp_wba_system_installer_t *i)
{
    i->page+=page_bytes(i);i->offset=0u;i->page_diff=false;
    if(i->page>=bytes(i)){
        i->page=0u;
        if(!i->component){i->component=1u;i->stage=COMPARE;}
        else i->stage=METADATA;
    }else i->stage=COMPARE;
}
comp_wba_system_install_action_t comp_wba_system_install_poll(comp_wba_system_installer_t *i,uint8_t *scratch,size_t capacity)
{
    if(!i || !i->usable || !scratch_valid(i,scratch,capacity) || !held(i))return fail(i);
    size_t unit=(capacity/2u)&~(size_t)15u;uint8_t *verify=scratch+unit;
    if(i->stage==COMPARE || i->stage==WRITE){
        size_t n=page_bytes(i)-i->offset<unit?page_bytes(i)-i->offset:unit;
        uint32_t at=i->page+i->offset,target=destination(i,at);
        if(!expected(i,at,scratch,n))return fail(i);
        if(i->stage==COMPARE){
            if(!read_destination(i,target,verify,n))return fail(i);
            if(memcmp(scratch,verify,n))i->page_diff=true;
        }else {
            bool ok=i->component?i->anchor->ports.program(i->anchor->ports.context,target,scratch,n):
                i->ports.flash_program(i->ports.context,target,scratch,n);
            if(!ok || !read_destination(i,target,verify,n) || memcmp(scratch,verify,n))return fail(i);
        }
        i->offset+=(uint32_t)n;
        if(i->offset==page_bytes(i)){
            if(i->stage==COMPARE && i->page_diff){i->offset=0u;i->stage=ERASE;}
            else next_page(i);
        }
    }else if(i->stage==ERASE){
        uint32_t target=destination(i,i->page);
        bool ok=i->component?i->anchor->ports.erase_sector(i->anchor->ports.context,target):
            i->ports.flash_erase_page(i->ports.context,target);
        if(!ok)return fail(i);
        i->stage=WRITE;i->offset=0u;
    }else if(i->stage==METADATA){
        bool done=false;
        if(!i->ports.layout_step(i->ports.context,i->anchor->record,scratch,unit,&done))return fail(i);
        if(done){i->component=0u;i->stage=VERIFY;hash_reset(i);}
    }else if(i->stage==VERIFY){
        size_t n=bytes(i)-i->offset<unit?bytes(i)-i->offset:unit;
        if(n){
            if(!read_destination(i,destination(i,i->offset),scratch,n))return fail(i);
            companion_sha256_update(&i->hash,scratch,n);
            for(size_t k=0;k<n;k++){i->crc^=scratch[k];for(unsigned bit=0;bit<8u;bit++)i->crc=(i->crc>>1)^((i->crc&1u)?UINT32_C(0xEDB88320):0u);}
            i->offset+=(uint32_t)n;
        }else {
            uint8_t digest[32];companion_sha256_final(&i->hash,digest);
            if(memcmp(digest,manifest(i)+36u,32u) || (i->crc^UINT32_MAX)!=u32(manifest(i)+32u))return fail(i);
            if(!i->component){i->component=1u;hash_reset(i);}
            else i->stage=FINISH;
        }
    }else if(i->stage==FINISH){
        if(!i->ports.layout_verified(i->ports.context,i->anchor->record))return fail(i);
        if(i->anchor->record[5]!=COMP_WBA_SYSTEM_ANCHOR_INSTALLED &&
            !comp_wba_system_anchor_advance(i->anchor,COMP_WBA_SYSTEM_ANCHOR_INSTALLED,scratch,unit))return fail(i);
        i->stage=COMPLETE;
    }else if(i->stage!=COMPLETE)return fail(i);
    i->anchor->ports.keep_alive(i->anchor->ports.context);
    return i->stage==COMPLETE?COMP_WBA_SYSTEM_INSTALL_BOOT_PAIR:COMP_WBA_SYSTEM_INSTALL_WORK;
}
