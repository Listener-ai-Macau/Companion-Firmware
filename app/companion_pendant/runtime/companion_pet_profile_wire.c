#include "companion_pet_profile_wire.h"
#include <string.h>
static uint32_t get32(const uint8_t *p)
{return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static void put32(uint8_t *p,uint32_t v)
{for(unsigned i=0;i<4u;i++)p[i]=(uint8_t)(v>>(8u*i));}
size_t comp_pet_profile_exchange(comp_pet_profile_store_t *s,const uint8_t *p,size_t n,
    bool admitted,uint32_t now,uint8_t out[96])
{
    if(!s || !p || !out || n<16u || n>80u || memcmp(p,"PMP1",4u))return 0u;
    uint32_t token=get32(p+8),expected=get32(p+12);
    uint16_t arg=(uint16_t)(p[6]|((uint16_t)p[7]<<8));uint8_t op=p[4];
    comp_pet_store_result_t r=COMP_PET_STORE_OK;size_t used=32u;uint32_t value=s->length;
    comp_pet_profile_expire(s,now);
    if(!admitted)r=COMP_PET_STORE_BUSY;
    else if(!s->mounted)r=COMP_PET_STORE_UNAVAILABLE;
    else if(!token || p[5] || op>7u || (op!=2u && op!=3u && n!=16u))r=COMP_PET_STORE_INVALID;
    else if(op && expected!=s->generation)r=COMP_PET_STORE_STALE;
    else switch(op) {
    case 0u:
        out[32]=(uint8_t)((s->persisted?1u:0u)|(s->writing?2u:0u)|(s->cleanup_pending?4u:0u));
        out[33]=out[34]=out[35]=0u;used=36u;break;
    case 1u: {
        value=arg;
        if(!s->persisted || arg>s->length)r=COMP_PET_STORE_INVALID;
        else {
            size_t count=s->length-arg;if(count>64u)count=64u;
            if(!comp_pet_profile_read(s,expected,arg,out+32,count))r=COMP_PET_STORE_IO;
            else used+=count;
        }
        break;
    }
    case 2u:
        if(n!=20u)r=COMP_PET_STORE_INVALID;
        else r=comp_pet_profile_begin(s,expected,token,arg,get32(p+16),now);
        value=s->received;break;
    case 3u:
        r=comp_pet_profile_append(s,token,arg,p+16,n-16u,now);value=s->received;break;
    case 4u:r=comp_pet_profile_commit(s,token,now);value=s->length;break;
    case 5u:case 7u:
        if(s->writing && token!=s->token)r=COMP_PET_STORE_STALE;
        else comp_pet_profile_abort(s);
        value=0u;break;
    case 6u:r=comp_pet_profile_cleanup(s);break;
    default:r=COMP_PET_STORE_INVALID;break;
    }
    if(r!=COMP_PET_STORE_OK)used=32u;
    memcpy(out,"PMP1",4u);out[4]=op;out[5]=(uint8_t)r;out[6]=(uint8_t)value;out[7]=(uint8_t)(value>>8);
    put32(out+8,token);put32(out+12,s->generation);memcpy(out+16,s->uid,12u);put32(out+28,s->active_crc);
    return used;
}
