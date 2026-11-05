#include "companion_pet_profile.h"
#include <string.h>
static const char types[16][5]={"ISTJ","ISFJ","INFJ","INTJ","ISTP","ISFP","INFP","INTP",
    "ESTP","ESFP","ENFP","ENTP","ESTJ","ESFJ","ENFJ","ENTJ"};
static uint32_t get32(const uint8_t *p)
{return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
const char *comp_pet_profile_type(unsigned type){return type<16u?types[type]:NULL;}
uint32_t comp_pet_profile_seed(const uint8_t uid[12])
{
    uint32_t seed=UINT32_C(2166136261);
    for(unsigned i=0;i<12u;i++)seed=(seed^uid[i])*UINT32_C(16777619);
    return seed?seed:1u;
}
comp_pet_traits_t comp_pet_profile_traits(unsigned type,uint32_t seed)
{
    const char *t=comp_pet_profile_type(type);comp_pet_traits_t v={40,50,50,60};
    if(!t)return v;
    uint8_t *out=(uint8_t *)&v;
    const uint8_t base[4]={(uint8_t)(t[0]=='E'?73u:32u),(uint8_t)(t[1]=='N'?76u:41u),
        (uint8_t)(t[2]=='F'?68u:37u),(uint8_t)(t[3]=='J'?77u:46u)};
    for(unsigned i=0;i<4u;i++) {
        seed^=seed<<13;seed^=seed>>17;seed^=seed<<5;
        out[i]=(uint8_t)((int)base[i]+(int)(seed%15u)-7);
    }
    return v;
}
static bool utf8(comp_pet_profile_read_fn read,void *ctx,uint32_t at,unsigned bytes)
{
    uint8_t block[32];unsigned left=0u;uint32_t code=0u,minimum=0u;
    while(bytes) {
        unsigned n=bytes>sizeof(block)?(unsigned)sizeof(block):bytes;
        if(!read(ctx,at,block,n))return false;
        for(unsigned i=0;i<n;i++) {
            uint8_t c=block[i];
            if(!left) {
                if(c<0x80u) {if(c<32u || c==127u)return false;continue;}
                if(c>=0xC2u && c<=0xDFu){left=1u;code=c&31u;minimum=0x80u;}
                else if(c>=0xE0u && c<=0xEFu){left=2u;code=c&15u;minimum=0x800u;}
                else if(c>=0xF0u && c<=0xF4u){left=3u;code=c&7u;minimum=0x10000u;}
                else return false;
            } else {
                if((c&0xC0u)!=0x80u)return false;
                code=(code<<6)|(c&63u);
                if(!--left && (code<minimum || code>0x10FFFFu ||
                    (code>=0xD800u && code<=0xDFFFu) || (code>=0x80u && code<=0x9Fu)))return false;
            }
        }
        at+=n;bytes-=n;
    }
    return left==0u;
}
bool comp_pet_profile_validate(comp_pet_profile_read_fn read,void *ctx,uint32_t bytes)
{
    uint8_t h[16];uint32_t ids[8]={0},at=16u;
    if(!read || bytes<16u || bytes>COMP_PET_PROFILE_BODY_MAX || !read(ctx,0u,h,16u) ||
       h[0]!=1u || h[1]>=16u || (h[2]&~7u) || h[3]>48u || h[4]>48u || h[5]>8u ||
       h[6] || h[7] || !get32(h+8) || get32(h+12))return false;
    unsigned count=h[5],name=h[3],owner=h[4];
    if(at+name+owner>bytes || !utf8(read,ctx,at,name) || !utf8(read,ctx,at+name,owner))return false;
    at+=name+owner;
    for(unsigned i=0;i<count;i++) {
        if(at+16u>bytes || !read(ctx,at,h,16u))return false;
        uint32_t id=get32(h),created=get32(h+4),expires=get32(h+8);
        unsigned n=h[13];
        if(!id || !created || (expires && expires<=created) || h[12]>2u || !n ||
           n>COMP_PET_PROFILE_NOTE_BYTES || h[14] || h[15] || at+16u+n>bytes)return false;
        for(unsigned k=0;k<i;k++)if(ids[k]==id)return false;
        ids[i]=id;at+=16u;if(!utf8(read,ctx,at,n))return false;at+=n;
    }
    return at==bytes;
}
