#ifndef COMPANION_GATT_PUBLIC_HASH_DIAGNOSTIC_H
#define COMPANION_GATT_PUBLIC_HASH_DIAGNOSTIC_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

/* Observation only. Pinned ST full-stack v2.10.0's actual public hash
 * call site is checked again in the linked ELF before signing. Other CMAC
 * callers (including pairing/authentication) cannot enter this recorder.
 * Tags below use the same reversed byte order as the compact NVM record. */
#define COMP_V11_GATT_PUBLIC_CMAC_RETURN_OFFSET 0xf4u
typedef struct {
    uint32_t calls,input_bytes,complete_input_bytes,faults;
    uint8_t last[16],previous[16];
} comp_v11_public_hash_trace_t;
static inline void comp_v11_public_hash_observe(comp_v11_public_hash_trace_t *s,
    uintptr_t caller,uintptr_t hash_function,uint32_t bytes,const uint8_t tag[16])
{
    if((caller&~(uintptr_t)1u)!=(hash_function&~(uintptr_t)1u)+COMP_V11_GATT_PUBLIC_CMAC_RETURN_OFFSET || bytes>672u)return;
    memcpy(s->previous,s->last,16u);
    for(unsigned i=0u;i<16u;++i)s->last[i]=tag[15u-i];
    s->input_bytes=bytes;
    if(s->calls!=UINT32_MAX)++s->calls;
}
const comp_v11_public_hash_trace_t *comp_v11_ble_public_hash_trace(void);
bool comp_v11_ble_public_hash_fault(void);

typedef struct {
    uint16_t live_records;
    bool envelope_valid,hash_valid,service_changed_present;
    uint8_t hash[16],service_changed_cccd;
} comp_v11_public_nvm_digest_t;
static inline uint32_t comp_v11_public_u32(const uint8_t *p)
{
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
/* Exact compact record framing from the pinned SDK, public fields only.
 * Security payloads and peer address bytes are skipped without reading.
 * Ambiguous/malformed/missing records remain explicitly unqualified. */
static inline comp_v11_public_nvm_digest_t comp_v11_public_nvm_digest(const void *memory,size_t size)
{
    comp_v11_public_nvm_digest_t s={0};
    const uint8_t *b=(const uint8_t*)memory;
    for(size_t off=0u;off<=size && size-off>=4u;) {
        uint32_t h=comp_v11_public_u32(b+off);
        if(h==0u){s.envelope_valid=true;s.hash_valid=s.live_records==1u;return s;}
        size_t n=(size_t)(h&65535u),step=(n+11u)&~(size_t)7u;
        unsigned type=(unsigned)((h>>16)&255u),live=(unsigned)(h>>24);
        if(live>1u || (type!=0u && type!=1u && type!=255u) || n>size-off-4u || step>size-off)return s;
        if(type==1u && live==1u) {
            const uint8_t *v=b+off+4u;
            if(n<28u || v[0]!=254u || v[7]!=255u || comp_v11_public_u32(v+8u)!=n-12u || (n-28u)%3u!=0u)return s;
            if(s.live_records==UINT16_MAX)return s;
            ++s.live_records;
            memcpy(s.hash,v+12u,16u);
            s.service_changed_present=false;s.service_changed_cccd=0u;
            for(size_t i=28u;i<n;i+=3u) {
                if(v[i]==4u && v[i+1u]==0u){s.service_changed_present=true;s.service_changed_cccd=v[i+2u];}
            }
        }
        off+=step;
    }
    return s;
}
static inline void comp_v11_public_hash_hex(const uint8_t value[16],char out[33])
{
    static const char digits[]="0123456789abcdef";
    for(unsigned i=0u;i<16u;++i){out[2u*i]=digits[value[i]>>4];out[2u*i+1u]=digits[value[i]&15u];}
    out[32]=0;
}
#endif
