#include "wba_bond_seal.h"
#include <string.h>

#define SEAL_MAGIC UINT32_C(0x31535042) /* BPS1 */
#define SEAL_NEW 1u
#define SEAL_MIGRATED 2u
#define SEAL_INTENT UINT32_C(0xfffffffe)
#define SEAL_DONE UINT32_C(0xfffffffc)
static uint32_t get32(const uint8_t *p)
{return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static void put32(uint8_t *p,uint32_t v)
{for(unsigned n=0;n<4u;++n)p[n]=(uint8_t)(v>>(8u*n));}
static uint32_t crc32(const uint8_t *p,size_t n)
{
    uint32_t crc=UINT32_MAX;
    while(n--) {
        crc^=*p++;
        for(unsigned bit=0;bit<8u;++bit)
            crc=(crc>>1)^((crc&1u)?UINT32_C(0xedb88320):0u);
    }
    return ~crc;
}
static bool configured(const comp_bond_config_t *c,uint32_t at)
{
    return c && c->read && c->program && c->payload_bytes &&
        c->payload_bytes<=COMP_BOND_MAX_BYTES && !(at&(COMP_BOND_BANK_BYTES-1u)) &&
        at<=UINT32_MAX-COMP_BOND_BANK_BYTES && at!=c->bank[0] && at!=c->bank[1] &&
        !(c->bank[0]&(COMP_BOND_BANK_BYTES-1u)) && !(c->bank[1]&(COMP_BOND_BANK_BYTES-1u));
}
/* Tail is required blank: never claim a sector with unrelated existing data. */
static comp_bond_seal_result_t read_header(const comp_bond_config_t *c,uint32_t at,uint8_t *h)
{
    if(!configured(c,at))return COMP_BOND_SEAL_UNOWNED;
    if(!c->read(c->context,at,h,COMP_BOND_SEAL_HEADER_BYTES))return COMP_BOND_SEAL_IO_FAILED;
    uint8_t bytes[COMP_BOND_STEP_BYTES];
    for(uint32_t offset=COMP_BOND_SEAL_HEADER_BYTES;offset<COMP_BOND_BANK_BYTES;) {
        size_t n=COMP_BOND_BANK_BYTES-offset;if(n>sizeof(bytes))n=sizeof(bytes);
        if(!c->read(c->context,at+offset,bytes,n))return COMP_BOND_SEAL_IO_FAILED;
        for(size_t i=0;i<n;++i)if(bytes[i]!=0xffu)return COMP_BOND_SEAL_UNOWNED;
        offset+=(uint32_t)n;
    }
    bool blank=true;
    for(unsigned i=0;i<COMP_BOND_SEAL_HEADER_BYTES;++i)blank=blank && h[i]==0xffu;
    if(blank)return COMP_BOND_SEAL_BLANK;
    if(get32(h)!=SEAL_MAGIC || get32(h+4u)!=1u || get32(h+8u)!=c->payload_bytes ||
       memcmp(h+16u,c->uid,12u) || get32(h+28u)!=crc32(h+4u,24u))return COMP_BOND_SEAL_INVALID;
    for(unsigned i=36u;i<COMP_BOND_SEAL_HEADER_BYTES;++i)if(h[i]!=0xffu)return COMP_BOND_SEAL_INVALID;
    uint32_t origin=get32(h+12u),phase=get32(h+32u);
    if((origin==SEAL_NEW || origin==SEAL_MIGRATED) && phase==SEAL_DONE)return COMP_BOND_SEAL_COMPLETE;
    if(origin==SEAL_NEW && phase==SEAL_INTENT)return COMP_BOND_SEAL_NEW_PENDING;
    return COMP_BOND_SEAL_INVALID;
}
static void make_header(const comp_bond_config_t *c,uint32_t origin,uint32_t phase,uint8_t *h)
{
    memset(h,0xff,COMP_BOND_SEAL_HEADER_BYTES);
    put32(h,SEAL_MAGIC);put32(h+4u,1u);put32(h+8u,c->payload_bytes);put32(h+12u,origin);
    memcpy(h+16u,c->uid,12u);put32(h+28u,crc32(h+4u,24u));put32(h+32u,phase);
}
/* A recognizable foreign header cannot be reinterpreted as a torn local one.
 * The caller still supplies first-new or internal-COMMITTED authority. */
static bool compatible(const uint8_t *old,const uint8_t *target)
{
    if(get32(old)==SEAL_MAGIC && get32(old+28u)==crc32(old+4u,24u) &&
       memcmp(old+4u,target+4u,28u))return false;
    for(unsigned n=0;n<COMP_BOND_SEAL_HEADER_BYTES;++n)
        if((old[n]&target[n])!=target[n])return false;
    return true;
}
static comp_bond_seal_result_t write_header(const comp_bond_config_t *c,uint32_t at,
                                           const uint8_t *old,uint32_t origin,uint32_t phase)
{
    uint8_t target[COMP_BOND_SEAL_HEADER_BYTES];make_header(c,origin,phase,target);
    if(!compatible(old,target))return COMP_BOND_SEAL_INVALID;
    if(!c->program(c->context,at,target,sizeof(target)))return COMP_BOND_SEAL_IO_FAILED;
    uint8_t got[COMP_BOND_SEAL_HEADER_BYTES];
    comp_bond_seal_result_t result=read_header(c,at,got);
    if(result==COMP_BOND_SEAL_IO_FAILED || result==COMP_BOND_SEAL_UNOWNED)return result;
    if(memcmp(got,target,sizeof(got)))return result==COMP_BOND_SEAL_IO_FAILED?result:COMP_BOND_SEAL_INVALID;
    return result;
}
comp_bond_seal_result_t comp_bond_seal_inspect(const comp_bond_config_t *c,uint32_t at)
{uint8_t h[COMP_BOND_SEAL_HEADER_BYTES];return read_header(c,at,h);}
comp_bond_seal_result_t comp_bond_seal_begin_new(const comp_bond_config_t *c,uint32_t at,bool banks_blank)
{
    uint8_t h[COMP_BOND_SEAL_HEADER_BYTES];
    comp_bond_seal_result_t result=read_header(c,at,h);
    if(!banks_blank || (result!=COMP_BOND_SEAL_BLANK && result!=COMP_BOND_SEAL_INVALID &&
                       result!=COMP_BOND_SEAL_NEW_PENDING))
        return COMP_BOND_SEAL_INVALID;
    if(result==COMP_BOND_SEAL_NEW_PENDING)return result;
    /* Only an incomplete header in an otherwise blank sector may be finished.
     * An invalid configuration or nonblank tail is UNOWNED above. */
    return write_header(c,at,h,SEAL_NEW,SEAL_INTENT);
}
comp_bond_seal_result_t comp_bond_seal_complete_new(const comp_bond_config_t *c,uint32_t at)
{
    uint8_t h[COMP_BOND_SEAL_HEADER_BYTES];
    comp_bond_seal_result_t result=read_header(c,at,h);
    if(result!=COMP_BOND_SEAL_NEW_PENDING)return result==COMP_BOND_SEAL_COMPLETE?result:COMP_BOND_SEAL_INVALID;
    uint8_t phase[4];put32(phase,SEAL_DONE);
    if(!c->program(c->context,at+32u,phase,sizeof(phase)))return COMP_BOND_SEAL_IO_FAILED;
    return comp_bond_seal_inspect(c,at);
}
comp_bond_seal_result_t comp_bond_seal_complete_migration(const comp_bond_config_t *c,uint32_t at)
{
    uint8_t h[COMP_BOND_SEAL_HEADER_BYTES];
    comp_bond_seal_result_t result=read_header(c,at,h);
    if(result==COMP_BOND_SEAL_COMPLETE || result==COMP_BOND_SEAL_IO_FAILED ||
       result==COMP_BOND_SEAL_UNOWNED)return result;
    if(result==COMP_BOND_SEAL_NEW_PENDING)return COMP_BOND_SEAL_INVALID;
    return write_header(c,at,h,SEAL_MIGRATED,SEAL_DONE);
}
