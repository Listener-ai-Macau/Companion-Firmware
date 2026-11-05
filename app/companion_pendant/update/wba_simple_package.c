#include "../storage/companion_crc32.h"
#include "wba_simple_package.h"
#include <string.h>
#if defined(STM32WBA25xx)
#include "wba25_memory_geometry.h"
#endif

#if defined(__GNUC__)
__attribute__((weak))
#endif
void comp_wba_simple_verify_failure(uint32_t stage){(void)stage;}
static bool failure(uint32_t stage)
{comp_wba_simple_verify_failure(stage);return false;}

static uint16_t u16(const uint8_t *p)
{return (uint16_t)((uint16_t)p[0]|((uint16_t)p[1]<<8u));}
static uint32_t u32(const uint8_t *p)
{return (uint32_t)p[0]|((uint32_t)p[1]<<8u)|((uint32_t)p[2]<<16u)|((uint32_t)p[3]<<24u);}

bool comp_wba_simple_package_open(comp_wba_simple_package_t *p,
    const uint8_t *h,size_t n,const comp_wba_simple_limits_t *g)
{
    if(!p)return false;
    memset(p,0,sizeof(*p));
    if(!h||!g||n!=COMP_WBA_SIMPLE_HEADER_BYTES||!g->board_target||
       !g->app_address||g->app_capacity<8u||g->static_bytes<8192u||
       g->static_bytes>g->nor_bytes||
       g->metadata_bytes>g->nor_bytes-g->static_bytes)return false;
    comp_wba_simple_package_t candidate;
    memset(&candidate,0,sizeof(candidate));
    if(!comp_wba_update_manifest_wire_decode(h,COMP_WBA_UPDATE_MANIFEST_WIRE_BYTES,
                                           &candidate.signed_manifest))return false;
    const comp_wba_update_manifest_t *m=&candidate.signed_manifest.manifest;
    const uint8_t *d=h+COMP_WBA_UPDATE_MANIFEST_WIRE_BYTES;
    uint32_t app=u32(d+16u),resources=u32(d+20u);
    if(m->target!=COMP_WBA_UPDATE_TARGET_FIRMWARE||
       m->format_version!=COMP_WBA_SIMPLE_FORMAT||
       m->target_family!=COMP_WBA_UPDATE_TARGET_FAMILY_STM32WBA||
       m->board_target!=g->board_target||memcmp(d,"CUP3",4u)||
       u16(d+4u)!=3u||u16(d+6u)!=COMP_WBA_SIMPLE_DESCRIPTOR_BYTES||
       u32(d+8u)!=m->component_version||!u32(d+12u)||
       app<8u||app>g->app_capacity||resources!=g->static_bytes||
       u32(d+24u)!=g->static_bytes||u32(d+28u)!=g->app_address)return false;
    /* Subtraction checks precede all additions from untrusted lengths. */
    uint32_t capacity=g->nor_bytes-g->static_bytes-g->metadata_bytes;
    if(capacity<COMP_WBA_SIMPLE_HEADER_BYTES||
       app>capacity-COMP_WBA_SIMPLE_HEADER_BYTES||
       resources>capacity-COMP_WBA_SIMPLE_HEADER_BYTES-app||
       m->size_bytes!=COMP_WBA_SIMPLE_DESCRIPTOR_BYTES+app+resources)return false;
    memcpy(candidate.descriptor,d,sizeof(candidate.descriptor));
    candidate.app_bytes=app;candidate.resource_bytes=resources;
    candidate.resource_version=u32(d+12u);
    *p=candidate;
    return true;
}

bool comp_wba_simple_package_newer(const comp_wba_simple_package_t *p,
    uint32_t app,uint32_t resources)
{
    if(!p)return false;
    const comp_wba_update_manifest_t *m=&p->signed_manifest.manifest;
    return m->component_version>app&&p->resource_version>=resources&&
        app>=m->minimum_app_version&&
        (!m->maximum_app_version||app<=m->maximum_app_version);
}

bool comp_wba_simple_package_verify(const comp_wba_simple_package_t *p,
    const comp_wba_simple_limits_t *g,const comp_wba_update_p256_trust_t *trust,
    comp_wba_simple_read_fn read,void *context,uint8_t *scratch,size_t capacity)
{
    if(!p||!g||!trust||!read||!scratch||capacity<8u||
       p->signed_manifest.key_id!=trust->key_id)return failure(1u);
    /* Canonical reconstruction makes an accidentally edited parsed object
     * fail the same structural checks as the original header. */
    uint8_t header[COMP_WBA_SIMPLE_HEADER_BYTES];
    if(!comp_wba_update_manifest_wire_encode(&p->signed_manifest.manifest,
        p->signed_manifest.key_id,p->signed_manifest.signature,header))return failure(2u);
    memcpy(header+COMP_WBA_UPDATE_MANIFEST_WIRE_BYTES,p->descriptor,sizeof(p->descriptor));
    comp_wba_simple_package_t checked;
    if(!comp_wba_simple_package_open(&checked,header,sizeof(header),g)||
       checked.app_bytes!=p->app_bytes||checked.resource_bytes!=p->resource_bytes||
       checked.resource_version!=p->resource_version)return failure(3u);
    if(!comp_wba_update_p256_authorize_manifest((void*)trust,
           &p->signed_manifest.manifest,p->signed_manifest.signature,
           sizeof(p->signed_manifest.signature)))return failure(4u);
    /* The retained NOR header is checked too; a parsed RAM copy cannot
     * authenticate a different file after a power interruption. */
    for(size_t at=0u;at<sizeof(header);) {
        size_t n=sizeof(header)-at;if(n>capacity)n=capacity;
        if(!read(context,(uint32_t)at,scratch,n)||memcmp(scratch,header+at,n))return failure(5u);
        at+=n;
    }
    companion_sha256_t hash;companion_sha256_init(&hash);
    uint32_t crc=0u,total=p->signed_manifest.manifest.size_bytes;
    for(uint32_t at=0u;at<total;) {
        size_t n=total-at;if(n>capacity)n=capacity;
        if(!read(context,COMP_WBA_UPDATE_MANIFEST_WIRE_BYTES+at,scratch,n))return failure(6u);
        companion_sha256_update(&hash,scratch,n);
        /* Retain the full independent payload CRC alongside SHA/signature. */
        crc=companion_crc32(crc,scratch,n);
        at+=(uint32_t)n;
    }
    uint8_t digest[32];companion_sha256_final(&hash,digest);
    if(memcmp(digest,p->signed_manifest.manifest.sha256,sizeof(digest)))return failure(7u);
    if(crc!=p->signed_manifest.manifest.crc32)return failure(8u);
    if(!read(context,COMP_WBA_SIMPLE_HEADER_BYTES,scratch,8u))return failure(9u);
    uint32_t sp=u32(scratch),pc=u32(scratch+4u);
    /* The future WBA25 target has contiguous 64+32 KiB nonsecure SRAM;
     * its bounds differ from the WBA55CE's 32+64 KiB and address gap.
     * Secure applications need an explicitly designed boot handoff. */
#if defined(STM32WBA25xx)
    bool stack=comp_wba25_stack_pointer_valid(sp,false);
#else
    bool stack=(sp>UINT32_C(0x20000000)&&sp<=UINT32_C(0x20008000))||
               (sp>UINT32_C(0x20010000)&&sp<=UINT32_C(0x20020000));
#endif
    if(!stack||(sp&7u)||!(pc&1u)||(pc&~1u)<g->app_address||
       (pc&~1u)-g->app_address>=p->app_bytes)return failure(10u);
    return true;
}
