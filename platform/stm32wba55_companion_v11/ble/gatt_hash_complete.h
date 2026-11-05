#ifndef COMPANION_GATT_HASH_COMPLETE_H
#define COMPANION_GATT_HASH_COMPLETE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

/* Fixed and build-checked ST full-stack v2.10.0 ABI only. These are public
 * database declarations, never characteristic user values or bond keys.
 * Follow the exact SDK selection/order, with a complete bounded input.
 * Service node: links0/4, handle8,type10,uuidType12,uuid14,attributes40.
 * Attribute: links0/4,handle8,valueLen10,uuidType15,uuid16,valuePointer32.
 * Service declaration is stored in the service node, not its attr list.
 * Do not publish/trust an incomplete result on any validation failure. */
#define COMP_V11_PUBLIC_GATT_HASH_INPUT_CAPACITY 1024u
#define COMP_V11_PINNED_GATT_SERVICE_HEAD_OFFSET 504u
static inline uint16_t comp_v11_hash_u16(const void *memory)
{ const uint8_t *p=(const uint8_t*)memory;return (uint16_t)((unsigned)p[0]|((unsigned)p[1]<<8)); }
static inline uint32_t comp_v11_hash_u32(const void *memory)
{ const uint8_t *p=(const uint8_t*)memory;return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24); }
static inline bool comp_v11_hash_range(uintptr_t p,size_t n,uintptr_t pool,size_t bytes)
{ return p>=pool && p-pool<=bytes && n<=bytes-(size_t)(p-pool); }
static inline bool comp_v11_hash_append(uint8_t *out,size_t capacity,size_t *used,const void *value,size_t count)
{
    if(*used>capacity || count>capacity-*used)return false;
    if(count)memcpy(out+*used,value,count);
    *used+=count;return true;
}
static inline bool comp_v11_complete_gatt_hash_input(uintptr_t head,
    uintptr_t pool,size_t pool_bytes,uint8_t *out,size_t capacity,size_t *length)
{
    size_t used=0u;unsigned services=0u,attributes=0u;
    uintptr_t previous=head,node=comp_v11_hash_u32((const void*)head);
    *length=0u;
    while(node!=head) {
        if(++services>32u || (node&3u) || !comp_v11_hash_range(node,48u,pool,pool_bytes) || comp_v11_hash_u32((const void*)(node+4u))!=previous)return false;
        const uint8_t *s=(const uint8_t*)node;unsigned type=comp_v11_hash_u16(s+10u),uuid_type=s[12];
        if((type!=0x2800u && type!=0x2801u) || (uuid_type!=1u && uuid_type!=2u))return false;
        if(!comp_v11_hash_append(out,capacity,&used,s+8u,4u) || !comp_v11_hash_append(out,capacity,&used,s+14u,uuid_type==1u?2u:16u))return false;
        uintptr_t ah=node+40u,aprevious=ah,a=comp_v11_hash_u32((const void*)ah);
        while(a!=ah) {
            if(++attributes>256u || (a&3u) || !comp_v11_hash_range(a,40u,pool,pool_bytes) || comp_v11_hash_u32((const void*)(a+4u))!=aprevious)return false;
            const uint8_t *v=(const uint8_t*)a;unsigned atype=comp_v11_hash_u16(v+16u),utype=v[15];
            if(utype!=1u && utype!=2u)return false;
            if(utype==1u) {
                bool value_in_hash=atype==0x2802u || atype==0x2803u || atype==0x2900u;
                if(value_in_hash || (atype>=0x2901u && atype<=0x2905u)) {
                    if(!comp_v11_hash_append(out,capacity,&used,v+8u,2u) || !comp_v11_hash_append(out,capacity,&used,v+16u,2u))return false;
                    if(value_in_hash) {
                        size_t n=comp_v11_hash_u16(v+10u);uintptr_t p=comp_v11_hash_u32(v+32u);
                        if(!comp_v11_hash_range(p,n,pool,pool_bytes) || !comp_v11_hash_append(out,capacity,&used,(const void*)p,n))return false;
                    }
                }
            }
            aprevious=a;a=comp_v11_hash_u32((const void*)a);
        }
        if(comp_v11_hash_u32((const void*)(ah+4u))!=aprevious)return false;
        previous=node;node=comp_v11_hash_u32((const void*)node);
    }
    if(!services || comp_v11_hash_u32((const void*)(head+4u))!=previous)return false;
    *length=used;return true;
}
bool comp_v11_ble_complete_public_hash_input(uint8_t *out,size_t capacity,size_t *length);
#endif
