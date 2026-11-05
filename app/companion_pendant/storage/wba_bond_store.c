#include "wba_bond_store.h"
#include <string.h>

enum { IDLE, ERASE, PROGRAM, VERIFY, HEADER, COMMIT };
#define BOND_MAGIC UINT32_C(0x31444e42) /* BND1 */
static uint32_t get32(const uint8_t *p)
{return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static void put32(uint8_t *p,uint32_t v)
{for(unsigned n=0;n<4u;++n)p[n]=(uint8_t)(v>>(8u*n));}
static uint32_t crc_step(uint32_t crc,const uint8_t *p,size_t n)
{
    while(n--) {
        crc^=*p++;
        for(unsigned bit=0;bit<8u;++bit)
            crc=(crc>>1)^((crc&1u)?UINT32_C(0xedb88320):0u);
    }
    return crc;
}
static bool configured(const comp_bond_config_t *c)
{
    return c && c->read && c->program && c->erase_step && c->source_read &&
        c->restore && c->source_revision && c->payload_bytes &&
        c->payload_bytes<=COMP_BOND_MAX_BYTES && c->bank[0]!=c->bank[1] &&
        !(c->bank[0]&(COMP_BOND_BANK_BYTES-1u)) &&
        !(c->bank[1]&(COMP_BOND_BANK_BYTES-1u)) &&
        c->bank[0]<=UINT32_MAX-COMP_BOND_BANK_BYTES &&
        c->bank[1]<=UINT32_MAX-COMP_BOND_BANK_BYTES;
}
static comp_bond_result_t finish(comp_bond_store_t *s,comp_bond_result_t result)
{s->phase=IDLE;s->result=result;return result;}
static bool image_crc(comp_bond_store_t *s,uint32_t base,uint32_t *value)
{
    uint8_t bytes[COMP_BOND_STEP_BYTES];uint32_t crc=UINT32_MAX;
    for(uint32_t at=0;at<s->config.payload_bytes;) {
        size_t n=s->config.payload_bytes-at;if(n>sizeof(bytes))n=sizeof(bytes);
        if(!s->config.read(s->config.context,base+COMP_BOND_HEADER_BYTES+at,bytes,n))return false;
        crc=crc_step(crc,bytes,n);at+=(uint32_t)n;
    }
    *value=~crc;return true;
}
static bool source_crc(comp_bond_store_t *s,uint32_t *value)
{
    uint8_t bytes[COMP_BOND_STEP_BYTES];uint32_t crc=UINT32_MAX;
    for(uint32_t at=0;at<s->config.payload_bytes;) {
        size_t n=s->config.payload_bytes-at;if(n>sizeof(bytes))n=sizeof(bytes);
        if(!s->config.source_read(s->config.context,at,bytes,n))return false;
        crc=crc_step(crc,bytes,n);at+=(uint32_t)n;
    }
    *value=~crc;return true;
}
static void make_header(const comp_bond_store_t *s,uint8_t h[COMP_BOND_HEADER_BYTES])
{
    memset(h,0xff,COMP_BOND_HEADER_BYTES);put32(h,BOND_MAGIC);
    put32(h+4u,1u);put32(h+8u,s->generation+1u);
    put32(h+12u,s->config.payload_bytes);put32(h+16u,s->source_crc);
    memcpy(h+20u,s->config.uid,12u);
    put32(h+32u,~crc_step(UINT32_MAX,h+4u,28u));
}
/* 1 valid; 0 invalid/nonblank; 2 fully blank; -1 I/O error. */
static int inspect(comp_bond_store_t *s,unsigned bank,uint8_t h[COMP_BOND_HEADER_BYTES])
{
    const comp_bond_config_t *c=&s->config;uint32_t crc;
    if(!c->read(c->context,c->bank[bank],h,COMP_BOND_HEADER_BYTES))return -1;
    if(get32(h)==BOND_MAGIC && get32(h+4u)==1u &&
       get32(h+12u)==c->payload_bytes && !memcmp(h+20u,c->uid,12u) &&
       get32(h+32u)==~crc_step(UINT32_MAX,h+4u,28u)) {
        if(!image_crc(s,c->bank[bank],&crc))return -1;
        if(crc==get32(h+16u))return 1;
    }
    /* Header erased alone is not authority to initialize. A torn first write
     * can have programmed payload and an erased publication word. */
    uint8_t bytes[COMP_BOND_STEP_BYTES];
    for(uint32_t at=0;at<COMP_BOND_BANK_BYTES;at+=sizeof(bytes)) {
        if(!c->read(c->context,c->bank[bank]+at,bytes,sizeof(bytes)))return -1;
        for(size_t k=0;k<sizeof(bytes);++k)if(bytes[k]!=0xffu)return 0;
    }
    return 2;
}
comp_bond_result_t comp_bond_store_mount(comp_bond_store_t *s,const comp_bond_config_t *c)
{
    if(!s || !configured(c))return COMP_BOND_BAD_ARGUMENT;
    /* Accept remount with &s->config at startup without clearing its ports. */
    comp_bond_config_t config=*c;
    memset(s,0,sizeof(*s));s->config=config;s->active=3u;
    uint8_t h[2][COMP_BOND_HEADER_BYTES];int a=inspect(s,0u,h[0]),b=inspect(s,1u,h[1]);
    if(a<0 || b<0)return finish(s,COMP_BOND_IO_FAILED);
    if(a!=1 && b!=1) {
        if(a==2 && b==2){s->active=2u;return finish(s,COMP_BOND_EMPTY);}
        return finish(s,COMP_BOND_CORRUPT);
    }
    unsigned selected=a==1?0u:1u;
    if(a==1 && b==1) {
        uint32_t delta=get32(h[1]+8u)-get32(h[0]+8u);
        if(delta==UINT32_C(0x80000000) ||
           (!delta && memcmp(h[0],h[1],COMP_BOND_HEADER_BYTES)))
            return finish(s,COMP_BOND_CORRUPT);
        if(delta && delta<UINT32_C(0x80000000))selected=1u;
    }
    uint8_t bytes[COMP_BOND_STEP_BYTES];
    for(uint32_t at=0;at<c->payload_bytes;) {
        size_t n=c->payload_bytes-at;if(n>sizeof(bytes))n=sizeof(bytes);
        if(!c->read(c->context,c->bank[selected]+COMP_BOND_HEADER_BYTES+at,bytes,n) ||
           !c->restore(c->context,at,bytes,n))return finish(s,COMP_BOND_IO_FAILED);
        at+=(uint32_t)n;
    }
    s->active=(uint8_t)selected;s->generation=get32(h[selected]+8u);
    s->stored_crc=get32(h[selected]+16u);return finish(s,COMP_BOND_READY);
}
comp_bond_result_t comp_bond_store_begin(comp_bond_store_t *s)
{
    if(!s || !configured(&s->config))return COMP_BOND_BAD_ARGUMENT;
    if(s->phase!=IDLE)return COMP_BOND_PENDING;
    /* A failed write may be requested again against its same inactive bank.
     * Failed/foreign startup mount has active=3 and never gains erase rights.
     * No live remount/restore is needed to retry, so newer RAM keys survive. */
    if(s->active>2u)return s->result;
    s->source_revision=s->config.source_revision(s->config.context);
    if(!source_crc(s,&s->source_crc))return finish(s,COMP_BOND_IO_FAILED);
    if(s->source_revision!=s->config.source_revision(s->config.context))return finish(s,COMP_BOND_STALE);
    if(s->active<2u && s->stored_crc==s->source_crc)return finish(s,COMP_BOND_READY);
    s->target=s->active==0u?1u:0u;s->offset=0u;s->phase=ERASE;
    s->result=COMP_BOND_PENDING;return s->result;
}
comp_bond_result_t comp_bond_store_step(comp_bond_store_t *s)
{
    if(!s || !configured(&s->config))return COMP_BOND_BAD_ARGUMENT;
    if(s->phase==IDLE)return s->result;
    const comp_bond_config_t *c=&s->config;uint32_t base=c->bank[s->target];
    if(s->phase==ERASE) {
        /* Finish/retire this same physical owner even if source has changed. */
        comp_bond_io_t io=c->erase_step(c->context,base);
        if(io==COMP_BOND_IO_PENDING)return COMP_BOND_PENDING;
        if(io!=COMP_BOND_IO_OK)return finish(s,COMP_BOND_IO_FAILED);
        s->phase=PROGRAM;
        return s->source_revision==c->source_revision(c->context)?COMP_BOND_PENDING:finish(s,COMP_BOND_STALE);
    }
    if(s->source_revision!=c->source_revision(c->context))return finish(s,COMP_BOND_STALE);
    uint8_t bytes[COMP_BOND_STEP_BYTES],check[COMP_BOND_STEP_BYTES];
    if(s->phase==PROGRAM) {
        size_t n=c->payload_bytes-s->offset;if(n>sizeof(bytes))n=sizeof(bytes);
        /* Each <=128-byte write remains within one physical256-byte page. */
        size_t page_left=256u-((COMP_BOND_HEADER_BYTES+s->offset)&255u);
        if(n>page_left)n=page_left;
        if(!c->source_read(c->context,s->offset,bytes,n) ||
           !c->program(c->context,base+COMP_BOND_HEADER_BYTES+s->offset,bytes,n) ||
           !c->read(c->context,base+COMP_BOND_HEADER_BYTES+s->offset,check,n) || memcmp(bytes,check,n))
            return finish(s,COMP_BOND_IO_FAILED);
        s->offset+=(uint32_t)n;
        if(s->offset==c->payload_bytes){s->offset=0u;s->verify_crc=UINT32_MAX;s->phase=VERIFY;}
        return COMP_BOND_PENDING;
    }
    if(s->phase==VERIFY) {
        size_t n=c->payload_bytes-s->offset;if(n>sizeof(bytes))n=sizeof(bytes);
        if(!c->read(c->context,base+COMP_BOND_HEADER_BYTES+s->offset,bytes,n))return finish(s,COMP_BOND_IO_FAILED);
        s->verify_crc=crc_step(s->verify_crc,bytes,n);s->offset+=(uint32_t)n;
        if(s->offset==c->payload_bytes) {
            if(~s->verify_crc!=s->source_crc)return finish(s,COMP_BOND_CORRUPT);
            s->phase=HEADER;
        }
        return COMP_BOND_PENDING;
    }
    make_header(s,bytes);
    if(s->phase==HEADER) {
        /* Publish magic only after the complete payload and header read back. */
        if(!c->program(c->context,base+4u,bytes+4u,COMP_BOND_HEADER_BYTES-4u) ||
           !c->read(c->context,base+4u,check,COMP_BOND_HEADER_BYTES-4u) ||
           memcmp(bytes+4u,check,COMP_BOND_HEADER_BYTES-4u))return finish(s,COMP_BOND_IO_FAILED);
        s->phase=COMMIT;return COMP_BOND_PENDING;
    }
    if(s->phase!=COMMIT)return finish(s,COMP_BOND_BAD_ARGUMENT);
    if(!c->program(c->context,base,bytes,4u) || !c->read(c->context,base,check,4u) ||
       memcmp(bytes,check,4u))return finish(s,COMP_BOND_IO_FAILED);
    s->active=s->target;++s->generation;s->stored_crc=s->source_crc;
    return finish(s,COMP_BOND_READY);
}

comp_bond_result_t comp_bond_store_import_begin(comp_bond_store_t *s)
{
    if(!s || !configured(&s->config) || s->phase!=IDLE ||
       (s->result!=COMP_BOND_EMPTY && s->result!=COMP_BOND_CORRUPT))
        return COMP_BOND_BAD_ARGUMENT;
    /* Even an interrupted-import receipt cannot claim a recognizably foreign
     * device/schema. Leave those committed headers and their data untouched. */
    uint8_t h[COMP_BOND_HEADER_BYTES];
    for(unsigned bank=0u;bank<2u;++bank) {
        if(!s->config.read(s->config.context,s->config.bank[bank],h,sizeof(h)))
            return finish(s,COMP_BOND_IO_FAILED);
        if(get32(h)==BOND_MAGIC && get32(h+32u)==~crc_step(UINT32_MAX,h+4u,28u) &&
           (get32(h+4u)!=1u || get32(h+12u)!=s->config.payload_bytes ||
            memcmp(h+20u,s->config.uid,12u)))return COMP_BOND_CORRUPT;
    }
    /* The caller's internal receipt, not the corrupt media itself, supplies
     * erase authority. Never use this function on a normal runtime retry. */
    s->active=2u;s->generation=0u;s->stored_crc=0u;
    s->result=COMP_BOND_EMPTY;return comp_bond_store_begin(s);
}
