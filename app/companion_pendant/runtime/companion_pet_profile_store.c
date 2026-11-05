#include "companion_pet_profile_store.h"
#include "companion_crc32.h"
#include <string.h>
#define PET_COMMIT UINT32_C(0x314B4F4D)
#define PET_TIMEOUT_MS 60000u
static uint32_t get32(const uint8_t *p)
{return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static void put32(uint8_t *p,uint32_t v)
{for(unsigned i=0;i<4u;i++)p[i]=(uint8_t)(v>>(8u*i));}
static bool blank(comp_pet_profile_store_t *s,unsigned bank)
{
    uint8_t block[64];
    for(uint32_t at=0;at<4096u;at+=64u) {
        if(!s->port.read(s->port.context,bank*4096u+at,block,64u))return false;
        for(unsigned i=0;i<64u;i++)if(block[i]!=255u)return false;
    }
    return true;
}
typedef struct { comp_pet_profile_store_t *store;uint32_t base; } reader_t;
static bool body_read(void *context,uint32_t at,uint8_t *out,size_t n)
{reader_t *r=context;return r->store->port.read(r->store->port.context,r->base+at,out,n);}
static bool body_valid(comp_pet_profile_store_t *s,unsigned bank,uint32_t length,uint32_t expected)
{
    uint8_t block[64];uint32_t crc=0u,base=bank*4096u+64u;
    for(uint32_t at=0;at<length;) {
        uint32_t n=length-at;if(n>64u)n=64u;
        if(!s->port.read(s->port.context,base+at,block,n))return false;
        crc=companion_crc32(crc,block,n);at+=n;
    }
    reader_t reader={s,base};
    uint8_t seed[4];
    return crc==expected && body_read(&reader,8u,seed,4u) &&
        get32(seed)==comp_pet_profile_seed(s->uid) && comp_pet_profile_validate(body_read,&reader,length);
}
comp_pet_store_result_t comp_pet_profile_mount(comp_pet_profile_store_t *s,
    const comp_pet_profile_port_t *port,const uint8_t uid[12])
{
    uint8_t header[2][40];bool committed[2]={false,false},valid[2]={false,false};
    bool unknown[2]={false,false};
    if(!s || !port || !port->read || !port->write || !port->erase || !uid)return COMP_PET_STORE_INVALID;
    memset(s,0,sizeof(*s));s->port=*port;memcpy(s->uid,uid,12u);
    for(unsigned b=0;b<2u;b++) {
        uint8_t *h=header[b];
        if(!port->read(port->context,b*4096u,h,40u))return COMP_PET_STORE_IO;
        if(!memcmp(h,"\xff\xff\xff\xff",4u)) {
            unknown[b]=!blank(s,b);
            continue;
        }
        /* A torn header from our own BEGIN may be erased on an explicit new
         * write. Unknown metadata must never be claimed by auto-format. */
        if(memcmp(h,"PMB1",4u)) {unknown[b]=true;continue;}
        if(get32(h+36)!=PET_COMMIT) {
            bool complete=get32(h+4)==1u && get32(h+32)==companion_crc32(0u,h,32u);
            if(complete && memcmp(h+16,uid,12u))return COMP_PET_STORE_UNAVAILABLE;
            unknown[b]=!complete;continue;
        }
        committed[b]=true;
        if(get32(h+4)!=1u || !get32(h+8) || get32(h+12)<16u ||
           get32(h+12)>1536u || memcmp(h+16,uid,12u) ||
           get32(h+32)!=companion_crc32(0u,h,32u))return COMP_PET_STORE_UNAVAILABLE;
        valid[b]=body_valid(s,b,get32(h+12),get32(h+28));
    }
    unsigned selected=committed[1]?1u:0u;
    if(committed[0] && committed[1]) {
        uint32_t a=get32(header[0]+8),b=get32(header[1]+8);
        if(a==b)return COMP_PET_STORE_UNAVAILABLE;
        selected=b>a?1u:0u;
    }
    if(committed[selected]) {
        /* Do not resurrect an older memory after a newer committed record is
         * corrupt. A retained physical backup is not permission to remember. */
        if(!valid[selected])return COMP_PET_STORE_UNAVAILABLE;
        s->persisted=true;s->active_bank=(uint8_t)selected;
        s->generation=get32(header[selected]+8);s->length=get32(header[selected]+12);
        s->active_crc=get32(header[selected]+28);
        s->cleanup_pending=!blank(s,selected^1u);
    } else if(unknown[0] || unknown[1])return COMP_PET_STORE_UNAVAILABLE;
    s->mounted=true;return COMP_PET_STORE_OK;
}
static bool candidate_header(comp_pet_profile_store_t *s,uint8_t h[36])
{
    return s->port.read(s->port.context,s->writing_bank*4096u,h,36u) &&
        !memcmp(h,"PMB1",4u) && get32(h+4)==1u && get32(h+8)==s->generation+1u &&
        get32(h+12)>=16u && get32(h+12)<=1536u && !memcmp(h+16,s->uid,12u) &&
        get32(h+28)==s->expected_crc && get32(h+32)==companion_crc32(0u,h,32u);
}
void comp_pet_profile_abort(comp_pet_profile_store_t *s)
{if(s){s->writing=false;s->token=0u;s->received=0u;}}
void comp_pet_profile_expire(comp_pet_profile_store_t *s,uint32_t now)
{if(s && s->writing && (now-s->started_ms>=PET_TIMEOUT_MS || now-s->last_progress_ms>=5000u))comp_pet_profile_abort(s);}
comp_pet_store_result_t comp_pet_profile_begin(comp_pet_profile_store_t *s,uint32_t expected,
    uint32_t token,uint32_t bytes,uint32_t crc,uint32_t now)
{
    uint8_t h[36],verify[36];
    if(!s || !s->mounted)return COMP_PET_STORE_UNAVAILABLE;
    comp_pet_profile_expire(s,now);
    if(s->writing)return COMP_PET_STORE_BUSY;
    if(expected!=s->generation)return COMP_PET_STORE_STALE;
    if(!token || bytes<16u || bytes>1536u || s->generation==UINT32_MAX)return COMP_PET_STORE_INVALID;
    unsigned bank=s->persisted?(s->active_bank^1u):0u;
    if(!s->port.erase(s->port.context,bank*4096u) || !blank(s,bank))return COMP_PET_STORE_IO;
    memset(h,0,sizeof(h));memcpy(h,"PMB1",4u);put32(h+4,1u);put32(h+8,s->generation+1u);
    put32(h+12,bytes);memcpy(h+16,s->uid,12u);put32(h+28,crc);put32(h+32,companion_crc32(0u,h,32u));
    if(!s->port.write(s->port.context,bank*4096u,h,36u) ||
       !s->port.read(s->port.context,bank*4096u,verify,36u) || memcmp(h,verify,36u))return COMP_PET_STORE_IO;
    s->writing=true;s->writing_bank=(uint8_t)bank;s->token=token;
    s->expected_crc=crc;s->received=0u;s->started_ms=now;s->last_progress_ms=now;
    /* Candidate size is kept in NOR. Only committed length is observable. */
    return COMP_PET_STORE_OK;
}
comp_pet_store_result_t comp_pet_profile_append(comp_pet_profile_store_t *s,uint32_t token,
    uint32_t offset,const uint8_t *data,size_t n,uint32_t now)
{
    uint8_t h[36],verify[64];
    if(!s || !s->mounted)return COMP_PET_STORE_UNAVAILABLE;
    comp_pet_profile_expire(s,now);
    if(!s->writing || token!=s->token)return COMP_PET_STORE_STALE;
    if(!data || !n || n>64u || offset!=s->received)return COMP_PET_STORE_INVALID;
    if(!candidate_header(s,h)) {comp_pet_profile_abort(s);return COMP_PET_STORE_IO;}
    uint32_t length=get32(h+12);
    if(offset>length || n>length-offset)return COMP_PET_STORE_INVALID;
    uint32_t at=s->writing_bank*4096u+64u+offset;
    if(!s->port.write(s->port.context,at,data,n) || !s->port.read(s->port.context,at,verify,n) ||
       memcmp(data,verify,n)) {comp_pet_profile_abort(s);return COMP_PET_STORE_IO;}
    s->received+=(uint32_t)n;s->last_progress_ms=now;return COMP_PET_STORE_OK;
}
comp_pet_store_result_t comp_pet_profile_cleanup(comp_pet_profile_store_t *s)
{
    if(!s || !s->mounted)return COMP_PET_STORE_UNAVAILABLE;
    if(s->writing)return COMP_PET_STORE_BUSY;
    if(!s->persisted || !s->cleanup_pending)return COMP_PET_STORE_OK;
    unsigned old=s->active_bank^1u;
    if(!s->port.erase(s->port.context,old*4096u) || !blank(s,old))return COMP_PET_STORE_CLEANUP_PENDING;
    s->cleanup_pending=false;return COMP_PET_STORE_OK;
}
comp_pet_store_result_t comp_pet_profile_commit(comp_pet_profile_store_t *s,uint32_t token,uint32_t now)
{
    uint8_t h[40],commit[4];
    if(!s || !s->mounted)return COMP_PET_STORE_UNAVAILABLE;
    comp_pet_profile_expire(s,now);
    if(!s->writing || token!=s->token)return COMP_PET_STORE_STALE;
    unsigned bank=s->writing_bank;uint32_t base=bank*4096u;
    if(!candidate_header(s,h)) {comp_pet_profile_abort(s);return COMP_PET_STORE_IO;}
    uint32_t length=get32(h+12);
    if(s->received!=length || !body_valid(s,bank,length,s->expected_crc))return COMP_PET_STORE_INVALID;
    put32(commit,PET_COMMIT);
    if(!s->port.write(s->port.context,base+36u,commit,4u) ||
       !s->port.read(s->port.context,base,h,40u) || get32(h+36)!=PET_COMMIT || !candidate_header(s,h)) {
        /* The commit might have landed. A read-only remount is mandatory
         * before another append; never reuse its generation or claim success. */
        comp_pet_profile_abort(s);s->mounted=false;return COMP_PET_STORE_IO;
    }
    s->active_bank=(uint8_t)bank;s->persisted=true;s->generation=get32(h+8);s->length=length;
    s->active_crc=s->expected_crc;
    comp_pet_profile_abort(s);s->cleanup_pending=!blank(s,bank^1u);
    return comp_pet_profile_cleanup(s);
}
bool comp_pet_profile_read(comp_pet_profile_store_t *s,uint32_t generation,uint32_t at,uint8_t *out,size_t n)
{
    return s && s->mounted && s->persisted && generation==s->generation && out && n<=64u &&
        at<=s->length && n<=s->length-at &&
        s->port.read(s->port.context,s->active_bank*4096u+64u+at,out,n);
}
