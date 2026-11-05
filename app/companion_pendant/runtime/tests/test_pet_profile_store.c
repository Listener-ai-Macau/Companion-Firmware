#include "companion_pet_profile_store.h"
#include "companion_pet_profile_wire.h"
#include "companion_crc32.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static uint8_t flash[8192],baseline[8192],body[256];
static long budget=-1;static unsigned changes;static bool fail_commit_read;
static bool rd(void *c,uint32_t at,uint8_t *out,size_t n)
{
    (void)c;if(at>8192u || n>8192u-at)return false;
    if(fail_commit_read && at%4096u==0u && n==40u && flash[at+36u]!=255u) {
        fail_commit_read=false;return false;
    }
    memcpy(out,flash+at,n);return true;
}
static bool mutation(void)
{if(budget==0)return false;if(budget>0)--budget;++changes;return true;}
static bool wr(void *c,uint32_t at,const uint8_t *p,size_t n)
{
    (void)c;if(at>8192u || n>8192u-at)return false;
    for(size_t i=0;i<n;i++) {
        if(!mutation())return false;
        if((flash[at+i]&p[i])!=p[i])return false;
        flash[at+i]&=p[i];
    }
    return true;
}
static bool er(void *c,uint32_t at)
{
    (void)c;if(at%4096u || at>4096u)return false;
    for(unsigned i=0;i<4096u;i++){if(!mutation())return false;flash[at+i]=255u;}
    return true;
}
static comp_pet_profile_port_t port={rd,wr,er,NULL};
static const uint8_t uid[12]={0x12,0,0x11,0,0x0d,0x50,0x33,0x57,0x54,0x36,0x37,0x20};
static void put(uint8_t *p,uint32_t n)
{for(unsigned i=0;i<4u;i++)p[i]=(uint8_t)(n>>(8u*i));}
static unsigned make_body(unsigned type,const char *note)
{
    unsigned n=note?(unsigned)strlen(note):0u;
    memset(body,0,sizeof(body));body[0]=1u;body[1]=(uint8_t)type;body[2]=3u;
    body[3]=3u;memcpy(body+16,"Miu",3u);put(body+8,comp_pet_profile_seed(uid));
    if(!note)return 19u;
    body[5]=1u;put(body+19,7u);put(body+23,1792886000u);body[31]=0u;body[32]=(uint8_t)n;
    memcpy(body+35,note,n);return 35u+n;
}
static comp_pet_store_result_t save(comp_pet_profile_store_t *s,unsigned n,uint32_t now)
{
    comp_pet_store_result_t r=comp_pet_profile_begin(s,s->generation,91u,n,companion_crc32(0u,body,n),now);
    if(r!=COMP_PET_STORE_OK)return r;
    for(unsigned at=0;at<n;) {
        unsigned count=n-at;if(count>17u)count=17u;
        r=comp_pet_profile_append(s,91u,at,body+at,count,now+1u);if(r!=COMP_PET_STORE_OK)return r;at+=count;
    }
    return comp_pet_profile_commit(s,91u,now+2u);
}
static void traits_and_validation(void)
{
    comp_pet_traits_t all[16];uint32_t seed=comp_pet_profile_seed(uid);
    assert(seed && seed==comp_pet_profile_seed(uid));assert(comp_pet_profile_type(16)==NULL);
    for(unsigned i=0;i<16u;i++) {
        assert(strlen(comp_pet_profile_type(i))==4u);all[i]=comp_pet_profile_traits(i,seed);
        const uint8_t *v=(const uint8_t *)&all[i];for(unsigned k=0;k<4u;k++)assert(v[k]<=100u);
        for(unsigned j=0;j<i;j++)assert(memcmp(&all[j],&all[i],sizeof(all[i]))!=0);
    }
    puts("16 creative presets: stable distinct traits, no psychological claim");
}
static void stale_timeout_and_identity(void)
{
    comp_pet_profile_store_t s;uint8_t other[12],out[64];memset(flash,255,sizeof(flash));budget=-1;
    assert(comp_pet_profile_mount(&s,&port,uid)==COMP_PET_STORE_OK && !s.persisted);
    unsigned n=make_body(6u,"Prefer brief replies");assert(save(&s,n,100u)==COMP_PET_STORE_OK);
    assert(s.persisted && s.generation==1u && !s.cleanup_pending);
    unsigned before=changes;
    assert(comp_pet_profile_begin(&s,0u,1u,n,0u,200u)==COMP_PET_STORE_STALE && changes==before);
    assert(comp_pet_profile_read(&s,1u,0u,out,n) && !memcmp(out,body,n));
    assert(!comp_pet_profile_read(&s,0u,0u,out,n));
    assert(comp_pet_profile_begin(&s,1u,91u,n,companion_crc32(0u,body,n),UINT32_MAX-20u)==COMP_PET_STORE_OK);
    assert(comp_pet_profile_append(&s,92u,0u,body,1u,0u)==COMP_PET_STORE_STALE);
    assert(comp_pet_profile_append(&s,91u,1u,body,1u,0u)==COMP_PET_STORE_INVALID);
    assert(comp_pet_profile_append(&s,91u,0u,body,1u,10000u)==COMP_PET_STORE_STALE);
    memcpy(other,uid,12u);other[0]^=1u;
    assert(comp_pet_profile_mount(&s,&port,other)==COMP_PET_STORE_UNAVAILABLE);
    assert(comp_pet_profile_mount(&s,&port,uid)==COMP_PET_STORE_OK && s.generation==1u);
    memset(flash,255,sizeof(flash));flash[99]=0u;
    assert(comp_pet_profile_mount(&s,&port,uid)==COMP_PET_STORE_UNAVAILABLE);
    puts("UID separation, stale generations/tokens, ordered chunks, timeout and unknown-media refusal");
}
static void all_power_cuts(void)
{
    comp_pet_profile_store_t s;uint8_t old[64],replacement[64],out[64];budget=-1;memset(flash,255,sizeof(flash));
    unsigned old_n=make_body(6u,"Old explicitly confirmed note");memcpy(old,body,old_n);
    assert(comp_pet_profile_mount(&s,&port,uid)==COMP_PET_STORE_OK && save(&s,old_n,0u)==COMP_PET_STORE_OK);
    memcpy(baseline,flash,sizeof(flash));unsigned n=make_body(15u,NULL);memcpy(replacement,body,n);
    /* Erase candidate + header + body + commit + erase previous private note. */
    unsigned last=4096u+36u+n+4u+4096u;
    for(unsigned cut=0;cut<=last;cut++) {
        memcpy(flash,baseline,sizeof(flash));budget=-1;
        assert(comp_pet_profile_mount(&s,&port,uid)==COMP_PET_STORE_OK);
        budget=(long)cut;(void)save(&s,n,30u);budget=-1;
        assert(comp_pet_profile_mount(&s,&port,uid)==COMP_PET_STORE_OK);
        assert(s.generation==1u || s.generation==2u);
        unsigned length=(unsigned)s.length;assert(length<=sizeof(out));
        assert(comp_pet_profile_read(&s,s.generation,0u,out,length));
        if(s.generation==1u)assert(length==old_n && !memcmp(out,old,old_n));
        else assert(length==n && !memcmp(out,replacement,n));
    }
    printf("%u mutation-byte power cuts: only prior or full committed choice, no partial memory\n",last+1u);
}
static void commit_uncertain_and_no_resurrection(void)
{
    comp_pet_profile_store_t s;uint8_t out[64];budget=-1;memcpy(flash,baseline,sizeof(flash));
    assert(comp_pet_profile_mount(&s,&port,uid)==COMP_PET_STORE_OK);
    unsigned n=make_body(0u,NULL);fail_commit_read=true;
    assert(save(&s,n,0u)==COMP_PET_STORE_IO && !s.mounted);
    assert(comp_pet_profile_begin(&s,1u,1u,n,0u,10u)==COMP_PET_STORE_UNAVAILABLE);
    assert(comp_pet_profile_mount(&s,&port,uid)==COMP_PET_STORE_OK && s.generation==2u);
    assert(comp_pet_profile_read(&s,2u,0u,out,n) && !memcmp(out,body,n));
    /* Simulate post-commit media corruption while the old committed bank
     * remains after the uncertain read. Never restore its deleted old note. */
    flash[s.active_bank*4096u+64u]^=1u;
    assert(comp_pet_profile_mount(&s,&port,uid)==COMP_PET_STORE_UNAVAILABLE);
    puts("uncertain commit requires remount; corrupt newer committed memory never resurrects older notes");
}
static void malformed_body_not_committed(void)
{
    comp_pet_profile_store_t s;budget=-1;memcpy(flash,baseline,sizeof(flash));
    assert(comp_pet_profile_mount(&s,&port,uid)==COMP_PET_STORE_OK);
    unsigned n=make_body(16u,"bad preset");assert(save(&s,n,0u)==COMP_PET_STORE_INVALID);
    assert(comp_pet_profile_mount(&s,&port,uid)==COMP_PET_STORE_OK && s.generation==1u);
    n=make_body(0u,"\xc0\xaf");assert(save(&s,n,0u)==COMP_PET_STORE_INVALID);
    assert(comp_pet_profile_mount(&s,&port,uid)==COMP_PET_STORE_OK && s.generation==1u);
    puts("invalid schema/UTF8 cannot become committed memory");
}
static void wire_admission_and_generation(void)
{
    comp_pet_profile_store_t s;uint8_t request[80]={0},response[96];
    budget=-1;memset(flash,255,sizeof(flash));assert(comp_pet_profile_mount(&s,&port,uid)==COMP_PET_STORE_OK);
    memcpy(request,"PMP1",4u);put(request+8,42u);
    unsigned before=changes;
    assert(comp_pet_profile_exchange(&s,request,16u,false,0u,response)==32u && response[5]==COMP_PET_STORE_BUSY);
    assert(changes==before);
    assert(comp_pet_profile_exchange(&s,request,16u,true,0u,response)==36u && response[32]==0u);
    assert(!memcmp(response+16,uid,12u));
    unsigned n=make_body(6u,"Prefer brief replies");request[4]=2u;request[6]=(uint8_t)n;
    put(request+16,companion_crc32(0u,body,n));
    assert(comp_pet_profile_exchange(&s,request,20u,true,1u,response)==32u && response[5]==0u);
    request[4]=3u;request[6]=0u;put(request+8,43u);memcpy(request+16,body,n);
    before=changes;
    assert(comp_pet_profile_exchange(&s,request,16u+n,true,2u,response)==32u && response[5]==COMP_PET_STORE_STALE);
    assert(changes==before);
    put(request+8,42u);
    assert(comp_pet_profile_exchange(&s,request,16u+n,true,2u,response)==32u && response[5]==0u);
    assert(response[6]==n);request[4]=4u;
    assert(comp_pet_profile_exchange(&s,request,16u,true,3u,response)==32u && response[5]==0u && response[12]==1u);
    request[4]=1u;
    assert(comp_pet_profile_exchange(&s,request,16u,true,4u,response)==32u && response[5]==COMP_PET_STORE_STALE);
    put(request+12,1u);
    assert(comp_pet_profile_exchange(&s,request,16u,true,4u,response)==32u+n && !memcmp(response+32,body,n));
    request[4]=7u;
    assert(comp_pet_profile_exchange(&s,request,16u,true,5u,response)==32u && response[5]==0u);
    puts("PMP1 admission/nonces/generation/ordered save/read/end; legacy restore still requires GATT integration");
}
int main(void)
{
    traits_and_validation();stale_timeout_and_identity();all_power_cuts();
    commit_uncertain_and_no_resurrection();malformed_body_not_committed();wire_admission_and_generation();
    puts("PASS_PORTABLE_PET_PROFILE_STORE_NOT_DEVICE_OR_RUNTIME_INTEGRATION");return 0;
}
