#ifndef COMP_V11_MAINTENANCE_PROTOCOL_H
#define COMP_V11_MAINTENANCE_PROTOCOL_H
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include "companion_crc32.h"
enum { COMP_MAINT_QUERY=0,COMP_MAINT_PAIR_WINDOW=1,COMP_MAINT_DEFAULTS=2,COMP_MAINT_CLEAR_BONDS=3 };
enum { COMP_MAINT_OK=0,COMP_MAINT_PENDING=1,COMP_MAINT_BUSY=2,COMP_MAINT_INVALID=3,COMP_MAINT_FAILED=4 };
static inline uint32_t comp_maint_get32(const uint8_t *p)
{return (uint32_t)p[0]|((uint32_t)p[1]<<8u)|((uint32_t)p[2]<<16u)|((uint32_t)p[3]<<24u);}
static inline void comp_maint_put32(uint8_t *p,uint32_t n)
{for(unsigned i=0u;i<4u;i++)p[i]=(uint8_t)(n>>(8u*i));}
/* Existing encrypted4003 characteristic. No new GATT service or database. */
static inline bool comp_maint_request(const uint8_t *p,uint16_t n,uint8_t *operation,uint32_t *request)
{
    if(!p||!operation||!request||n!=16u||memcmp(p,"CRM1",4u)||p[4]>COMP_MAINT_CLEAR_BONDS||
       p[5]||p[6]||p[7]||!comp_maint_get32(p+8u)||
       companion_crc32(0u,p,12u)!=comp_maint_get32(p+12u))return false;
    *operation=p[4];*request=comp_maint_get32(p+8u);return true;
}
static inline void comp_maint_response(uint8_t p[32],uint8_t operation,uint8_t result,uint32_t request,
    uint8_t flags,uint8_t bonds,uint32_t preferences_generation,uint32_t preferences_crc,
    uint32_t bonds_generation,uint32_t last_request)
{
    memset(p,0,32u);memcpy(p,"CRM1",4u);p[4]=operation;p[5]=result;p[6]=flags;p[7]=bonds;
    comp_maint_put32(p+8u,request);comp_maint_put32(p+12u,preferences_generation);
    comp_maint_put32(p+16u,preferences_crc);comp_maint_put32(p+20u,bonds_generation);
    comp_maint_put32(p+24u,last_request);comp_maint_put32(p+28u,companion_crc32(0u,p,28u));
}
#endif
