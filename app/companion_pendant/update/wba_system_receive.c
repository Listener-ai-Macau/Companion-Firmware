#include "wba_system_receive.h"
#include <string.h>

static uint32_t get32(const uint8_t *p)
{return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static uint64_t get64(const uint8_t *p)
{return (uint64_t)get32(p)|((uint64_t)get32(p+4u)<<32);}
static void put32(uint8_t *p,uint32_t n)
{p[0]=(uint8_t)n;p[1]=(uint8_t)(n>>8);p[2]=(uint8_t)(n>>16);p[3]=(uint8_t)(n>>24);}
static void put64(uint8_t *p,uint64_t n)
{put32(p,(uint32_t)n);put32(p+4u,(uint32_t)(n>>32));}
static const uint8_t *wire(const comp_wba_system_receiver_t *r)
{return r->record+32u;}
static uint32_t size(const comp_wba_system_receiver_t *r,uint8_t component)
{return get32(wire(r)+(component?240u:96u)+28u);}
static uint32_t source(const comp_wba_system_receiver_t *r,uint8_t component)
{return get32(r->record+16u)+get32(wire(r)+(component?48u:44u));}
static bool fail(comp_wba_system_receiver_t *r)
{r->usable=false;return false;}
static bool overlaps(const uint8_t *a,const uint8_t *b,size_t bytes)
{uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return x<=y?y-x<bytes:x-y<bytes;}
static uint32_t minimum_base(const comp_wba_system_receiver_t *r)
{
    uint32_t candidate=get32(wire(r)+36u);
    return (candidate>r->config.current_static_bytes?candidate:r->config.current_static_bytes)+COMP_WBA_NOR_SYSTEM_BYTES;
}
static bool extent_valid(const comp_wba_system_receiver_t *r,uint32_t base)
{
    uint32_t bytes=get32(wire(r)+52u);
    return base>=minimum_base(r) && base%COMP_WBA_NOR_SECTOR_BYTES==0u &&
        bytes<=COMP_WBA_NOR_TOTAL_BYTES && base==COMP_WBA_NOR_TOTAL_BYTES-bytes;
}
static void verify_reset(comp_wba_system_receiver_t *r)
{r->verify_component=0u;r->verify_offset=0u;r->verify_crc=UINT32_MAX;companion_sha256_init(&r->hash);}

bool comp_wba_system_record_valid(const uint8_t p[COMP_WBA_SYSTEM_RECORD_BYTES])
{
    comp_wba_system_pair_t pair;
    if(!p || memcmp(p,"WSR2",4u) || p[4]!=1u || p[5]<COMP_WBA_SYSTEM_RECEIVING ||
        p[5]>COMP_WBA_SYSTEM_RETIRED || p[6] || p[7] || !get64(p+8u) || get32(p+28u) ||
        get32(p+484u)!=comp_wba_update_wire_crc32(p,484u) ||
        !comp_wba_system_wire_decode(p+32u,452u,&pair))return false;
    uint32_t a=get32(p+20u),b=get32(p+24u);
    return a<=pair.firmware.manifest.size_bytes && b<=pair.resources.manifest.size_bytes &&
        (a==pair.firmware.manifest.size_bytes || a%4096u==0u) &&
        (b==pair.resources.manifest.size_bytes || b%4096u==0u) &&
        ((p[5]!=COMP_WBA_SYSTEM_VERIFYING && p[5]!=COMP_WBA_SYSTEM_PAIR_READY) ||
            (a==pair.firmware.manifest.size_bytes && b==pair.resources.manifest.size_bytes));
}

static bool commit(comp_wba_system_receiver_t *r,uint8_t phase,uint32_t a,uint32_t b)
{
    uint8_t next[COMP_WBA_SYSTEM_RECORD_BYTES];
    uint64_t sequence=get64(r->record+8u);
    if(sequence==UINT64_MAX)return fail(r);
    memcpy(next,r->record,sizeof(next));next[5]=phase;
    put64(next+8u,sequence+1u);put32(next+20u,a);put32(next+24u,b);
    put32(next+484u,comp_wba_update_wire_crc32(next,484u));
    if(!comp_wba_system_record_valid(next) || !r->config.ports.store(r->config.ports.context,next))return fail(r);
    memcpy(r->record,next,sizeof(next));r->loaded=true;
    return true;
}

static bool config_valid(const comp_wba_system_receive_config_t *cfg)
{
    if(!cfg)return false;
    const comp_wba_system_receive_ports_t *p=&cfg->ports;
    return p->load && p->store && p->idle && p->claim && p->release && p->reconcile_empty && p->read &&
        p->erase_sector && p->program && comp_wba_update_p256_trust_configured(&cfg->trust) &&
        cfg->current_static_bytes>=8192u && !(cfg->current_static_bytes%4096u) &&
        cfg->current_static_bytes<=COMP_WBA_NOR_TOTAL_BYTES-COMP_WBA_NOR_SYSTEM_BYTES-4096u;
}
bool comp_wba_system_receive_prepare_first_retry(comp_wba_system_receiver_t *r,const comp_wba_system_receive_config_t *cfg)
{
    if(!r || !config_valid(cfg))return false;
    comp_wba_system_receive_config_t copy=*cfg;
    memset(r,0,sizeof(*r));r->config=copy;r->mounted=r->usable=true;return true;
}
bool comp_wba_system_receive_mount(comp_wba_system_receiver_t *r,const comp_wba_system_receive_config_t *cfg)
{
    bool blank=false;comp_wba_system_pair_t pair;
    if(!r || !config_valid(cfg))return false;
    comp_wba_system_receive_config_t copy=*cfg;
    memset(r,0,sizeof(*r));r->config=copy;
    const comp_wba_system_receive_ports_t *p=&r->config.ports;
    if(!p->load(p->context,r->record,&blank))return false;
    r->mounted=true;r->usable=true;
    if(blank){memset(r->record,0,sizeof(r->record));return p->reconcile_empty(p->context)?true:fail(r);}
    if(!comp_wba_system_record_valid(r->record) ||
        !comp_wba_system_wire_authorize(wire(r),452u,&cfg->trust,&pair))return fail(r);
    r->loaded=true;
    uint32_t base=get32(r->record+16u),claimed=0u;
    if(!extent_valid(r,base))return fail(r);
    if(r->record[5]==COMP_WBA_SYSTEM_RETIRED)
        return p->release(p->context,base,pair.staging_bytes)?true:fail(r);
    if(!p->claim(p->context,pair.staging_bytes,minimum_base(r),base,&claimed) || claimed!=base)return fail(r);
    for(uint8_t i=0u;i<2u;i++){
        r->received[i]=get32(r->record+20u+4u*i);
        r->erased_until[i]=r->received[i]==size(r,i)?(r->received[i]+4095u)&~UINT32_C(4095):r->received[i];
    }
    verify_reset(r);
    return true;
}

bool comp_wba_system_receive_begin(comp_wba_system_receiver_t *r,const uint8_t *descriptor,size_t bytes)
{
    comp_wba_system_pair_t pair;
    if(!r || !r->mounted || !r->usable ||
        (r->loaded && r->record[5]!=COMP_WBA_SYSTEM_RETIRED) ||
        !r->config.ports.idle(r->config.ports.context) ||
        !comp_wba_system_wire_authorize(descriptor,bytes,&r->config.trust,&pair))return false;
    const comp_wba_update_manifest_t *fw=&pair.firmware.manifest;
    if(fw->component_version<=r->config.current_firmware ||
        fw->minimum_app_version>r->config.current_firmware ||
        (fw->maximum_app_version && fw->maximum_app_version<r->config.current_firmware) ||
        pair.resources.manifest.component_version<r->config.current_resources ||
        (pair.resources.manifest.component_version==r->config.current_resources &&
            (!r->config.current_resource_sha256 || memcmp(r->config.current_resource_sha256,pair.resources.manifest.sha256,32u))))return false;
    uint64_t sequence=r->loaded?get64(r->record+8u):0u;
    memset(r->record,0,sizeof(r->record));memcpy(r->record,"WSR2",4u);r->record[4]=1u;
    put64(r->record+8u,sequence);memcpy(r->record+32u,descriptor,452u);
    uint32_t base=0u;
    if(!r->config.ports.claim(r->config.ports.context,pair.staging_bytes,minimum_base(r),
        COMP_WBA_SYSTEM_ALLOCATE_NEW,&base) || !extent_valid(r,base))return fail(r);
    put32(r->record+16u,base);
    if(!commit(r,COMP_WBA_SYSTEM_RECEIVING,0u,0u))return false;
    memset(r->received,0,sizeof(r->received));memset(r->erased_until,0,sizeof(r->erased_until));verify_reset(r);
    return true;
}

bool comp_wba_system_receive_data(comp_wba_system_receiver_t *r,const uint8_t id[32],uint8_t component,
    uint32_t offset,const uint8_t *data,size_t length,uint8_t *scratch,size_t scratch_bytes)
{
    if(!r || !r->usable || !r->loaded || r->record[5]!=COMP_WBA_SYSTEM_RECEIVING ||
        !id || memcmp(id,wire(r)+64u,32u) || component>1u || !data || !length ||
        length>COMP_WBA_SYSTEM_MAX_CHUNK_BYTES || !scratch || scratch_bytes<length ||
        overlaps(data,scratch,length) || offset>size(r,component) ||
        length>size(r,component)-offset || !r->config.ports.idle(r->config.ports.context))return false;
    const comp_wba_system_receive_ports_t *p=&r->config.ports;
    uint32_t address=source(r,component)+offset;
    if(offset<r->received[component]){
        return length<=r->received[component]-offset && p->read(p->context,address,scratch,length) &&
            !memcmp(scratch,data,length);
    }
    if(offset!=r->received[component])return false;
    uint32_t end=offset+(uint32_t)length;
    while(r->erased_until[component]<end){
        if(!p->erase_sector(p->context,source(r,component)+r->erased_until[component]))return fail(r);
        r->erased_until[component]+=4096u;
    }
    if(!p->program(p->context,address,data,length) || !p->read(p->context,address,scratch,length) ||
        memcmp(scratch,data,length))return fail(r);
    r->received[component]=end;
    uint32_t durable=end==size(r,component)?end:end&~UINT32_C(4095);
    if(durable!=get32(r->record+20u+4u*component)){
        uint32_t a=component==0u?durable:get32(r->record+20u);
        uint32_t b=component==1u?durable:get32(r->record+24u);
        if(!commit(r,COMP_WBA_SYSTEM_RECEIVING,a,b))return false;
    }
    return true;
}

bool comp_wba_system_receive_finish(comp_wba_system_receiver_t *r)
{
    if(!r || !r->usable || !r->loaded || r->record[5]!=COMP_WBA_SYSTEM_RECEIVING ||
        r->received[0]!=size(r,0u) || r->received[1]!=size(r,1u) ||
        !r->config.ports.idle(r->config.ports.context))return false;
    /* Clear only this authenticated claim's future anchor sectors BEFORE a
     * verified/activatable state exists. An interrupted erase leaves RECEIVING
     * and can be retried without touching either staged payload or recordings.
     * Later Boot must never clear these sectors while installation is active.
     */
    for(uint32_t at=COMP_WBA_NOR_TOTAL_BYTES-COMP_WBA_SYSTEM_ANCHOR_BYTES;
        at<COMP_WBA_NOR_TOTAL_BYTES;at+=COMP_WBA_NOR_SECTOR_BYTES)
        if(!r->config.ports.erase_sector(r->config.ports.context,at))return fail(r);
    if(!commit(r,COMP_WBA_SYSTEM_VERIFYING,r->received[0],r->received[1]))return false;
    verify_reset(r);return true;
}

bool comp_wba_system_receive_poll(comp_wba_system_receiver_t *r,uint8_t *scratch,size_t capacity)
{
    if(!r || !r->usable || !r->loaded || !scratch || !capacity ||
        r->record[5]!=COMP_WBA_SYSTEM_VERIFYING || !r->config.ports.idle(r->config.ports.context))return false;
    uint32_t left=size(r,r->verify_component)-r->verify_offset;
    size_t length=left<capacity?left:capacity;
    if(length){
        if(!r->config.ports.read(r->config.ports.context,source(r,r->verify_component)+r->verify_offset,scratch,length))return fail(r);
        companion_sha256_update(&r->hash,scratch,length);
        for(size_t i=0u;i<length;i++){
            r->verify_crc^=scratch[i];
            for(uint8_t j=0u;j<8u;j++)r->verify_crc=(r->verify_crc>>1)^((r->verify_crc&1u)?UINT32_C(0xEDB88320):0u);
        }
        r->verify_offset+=(uint32_t)length;return true;
    }
    uint8_t digest[32];companion_sha256_final(&r->hash,digest);
    const uint8_t *manifest=wire(r)+(r->verify_component?240u:96u);
    if(memcmp(digest,manifest+36u,32u) || (r->verify_crc^UINT32_MAX)!=get32(manifest+32u))return fail(r);
    if(r->verify_component==0u){r->verify_component=1u;r->verify_offset=0u;r->verify_crc=UINT32_MAX;companion_sha256_init(&r->hash);return true;}
    return commit(r,COMP_WBA_SYSTEM_PAIR_READY,r->received[0],r->received[1]);
}

bool comp_wba_system_receive_cancel(comp_wba_system_receiver_t *r,const uint8_t id[32])
{
    if(!r || !r->usable || !r->loaded || !id || memcmp(id,wire(r)+64u,32u) ||
        r->record[5]==COMP_WBA_SYSTEM_PAIR_READY || !r->config.ports.idle(r->config.ports.context))return false;
    if(r->record[5]!=COMP_WBA_SYSTEM_RETIRED &&
        !commit(r,COMP_WBA_SYSTEM_RETIRED,get32(r->record+20u),get32(r->record+24u)))return false;
    if(!r->config.ports.release(r->config.ports.context,get32(r->record+16u),get32(wire(r)+52u)))return fail(r);
    return true;
}

bool comp_wba_system_receive_confirm(comp_wba_system_receiver_t *r,const uint8_t id[32])
{
    if(!r || !r->usable || !r->loaded || r->record[5]!=COMP_WBA_SYSTEM_PAIR_READY ||
        !id || memcmp(id,wire(r)+64u,32u) || !r->config.ports.running_pair_verified ||
        !r->config.ports.idle(r->config.ports.context) ||
        !r->config.ports.running_pair_verified(r->config.ports.context,wire(r)))return false;
    if(!commit(r,COMP_WBA_SYSTEM_RETIRED,get32(r->record+20u),get32(r->record+24u)))return false;
    if(!r->config.ports.release(r->config.ports.context,get32(r->record+16u),get32(wire(r)+52u)))return fail(r);
    return true;
}
