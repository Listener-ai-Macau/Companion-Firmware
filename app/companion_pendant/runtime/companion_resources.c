#include "../storage/companion_crc32.h"
#include "companion_resources.h"
#if defined(COMPANION_WBA_RESOURCE_PROFILE) && COMPANION_WBA_RESOURCE_PROFILE
#include "companion_wba_resource_contract.h"
#if COMPANION_WBA_RESOURCE_GENERATION >= 84u
#include "companion_wba_customer_ui.h"
#endif
#define COMP_RESOURCE_EXPECTED_ID COMPANION_WBA_RESOURCE_ID
#define COMP_RESOURCE_REVISION COMPANION_WBA_RESOURCE_PROFILE_REVISION
#define COMP_RESOURCE_CLIPS companion_wba_cemp_clips
#define COMP_RESOURCE_CLIP_COUNT COMPANION_WBA_CEMP_CLIP_COUNT
#define COMP_RESOURCE_FRAMES companion_wba_cemp_frames
#define COMP_RESOURCE_FRAME_COUNT COMPANION_WBA_CEMP_FRAME_COUNT
#define COMP_RESOURCE_STRINGS companion_wba_cemp_strings
#define COMP_RESOURCE_STRING_BYTES COMPANION_WBA_CEMP_STRING_BYTES
#define COMP_RESOURCE_TOTAL_BYTES COMPANION_WBA_CEMP_TOTAL_BYTES
#else
#include "companion_browser_cemp_contract.h"
#include "companion_browser_interaction_contract.h"
#define COMP_RESOURCE_EXPECTED_ID COMPANION_BROWSER_INTERACTION_PRODUCT_RESOURCE_ID
#define COMP_RESOURCE_REVISION COMPANION_BROWSER_CEMP_PACK_REVISION
#define COMP_RESOURCE_CLIPS companion_browser_cemp_clips
#define COMP_RESOURCE_CLIP_COUNT COMPANION_BROWSER_CEMP_CLIP_COUNT
#define COMP_RESOURCE_FRAMES companion_browser_cemp_frames
#define COMP_RESOURCE_FRAME_COUNT COMPANION_BROWSER_CEMP_FRAME_COUNT
#define COMP_RESOURCE_STRINGS companion_browser_cemp_strings
#define COMP_RESOURCE_STRING_BYTES sizeof(companion_browser_cemp_strings)
#define COMP_RESOURCE_TOTAL_BYTES COMPANION_BROWSER_CEMP_TOTAL_BYTES
#endif
#include <string.h>
#if COMPANION_WBA_UI_EXTERNAL
#include "companion_wba_external_ui.h"
static uint16_t le16(const uint8_t *p)
{ return (uint16_t)((uint16_t)p[0] | (uint16_t)p[1]<<8u); }
static uint32_t le32(const uint8_t *p)
{ return (uint32_t)p[0] | (uint32_t)p[1]<<8u | (uint32_t)p[2]<<16u | (uint32_t)p[3]<<24u; }
static uint32_t crc_bytes(uint32_t crc,const uint8_t *p,size_t n)
{return companion_crc32(crc^UINT32_MAX,p,n)^UINT32_MAX;}
static bool store_crc(const comp_asset_store_t *s,uint32_t at,uint32_t n,uint32_t expected)
{
    uint8_t scratch[256];uint32_t crc=0xFFFFFFFFu;
    if(at>s->size_bytes || n>s->size_bytes-at)return false;
    while(n) {
        const size_t count=n>sizeof(scratch)?sizeof(scratch):n;
        if(!comp_asset_store_read(s,at,scratch,count))return false;
        crc=crc_bytes(crc,scratch,count);at+=(uint32_t)count;n-=(uint32_t)count;
    }
    return (crc^0xFFFFFFFFu)==expected;
}
static bool mount_index(comp_runtime_resources_t *r,const comp_asset_store_t *s)
{
    uint8_t h[COMP_EMOTE_ASSET_PACK_HEADER_BYTES];
    if(!comp_asset_store_read(s,0,h,sizeof(h)) || memcmp(h,"CEMP",4u) ||
       le16(h+4)!=1u || le16(h+6)!=sizeof(h) ||
       le32(h+8)!=COMP_RESOURCE_TOTAL_BYTES || le32(h+12)!=COMP_RESOURCE_REVISION ||
       le16(h+20)!=200u || le16(h+22)!=200u || le16(h+24)!=25u || h[26]!=1u ||
       (h[27]!=1u && h[27]!=2u) || le16(h+28)!=COMP_RESOURCE_CLIP_COUNT ||
       le16(h+30)!=COMP_RESOURCE_FRAME_COUNT)return false;
    const uint32_t ft=80u+16u*COMP_RESOURCE_CLIP_COUNT;
    const uint32_t st=ft+20u*COMP_RESOURCE_FRAME_COUNT;
    const uint32_t po=st+COMP_RESOURCE_STRING_BYTES;
    const uint32_t ps=le32(h+52);
    if(le32(h+32)!=80u || le32(h+36)!=ft || le32(h+40)!=st ||
       le32(h+44)!=COMP_RESOURCE_STRING_BYTES || le32(h+48)!=po ||
       po>COMP_RESOURCE_TOTAL_BYTES || ps!=COMP_RESOURCE_TOTAL_BYTES-po ||
       le32(h+56)!=COMPANION_WBA_CEMP_PAYLOAD_CRC32 ||
       le32(h+60)!=COMPANION_WBA_CEMP_INDEX_CRC32 ||
       !store_crc(s,80u,po-80u,COMPANION_WBA_CEMP_INDEX_CRC32) ||
       !store_crc(s,po,ps,COMPANION_WBA_CEMP_PAYLOAD_CRC32))return false;
    r->store=s;r->frame_table_offset=ft;r->payload_offset=po;r->payload_size=ps;
    r->frame_count=COMP_RESOURCE_FRAME_COUNT;r->frame_encoding=h[27];
    return true;
}
static bool read_base(comp_runtime_resources_t *r,uint16_t index,uint8_t *frame)
{
    uint8_t wire[COMP_EMOTE_ASSET_PACK_FRAME_ENTRY_BYTES];
    if(index>=r->frame_count || !comp_asset_store_read(r->store,
       r->frame_table_offset+20u*index,wire,sizeof(wire)))return false;
    const uint32_t bytes=le32(wire+4);
    if(!bytes || bytes>UINT16_MAX || le32(wire)>r->payload_size ||
       bytes>r->payload_size-le32(wire) || !le16(wire+8) ||
       le16(wire+10)>200u || le16(wire+12)>200u ||
       le16(wire+14)>200u-le16(wire+10) || le16(wire+16)>200u-le16(wire+12))return false;
    const comp_emote_frame_t f={le32(wire),(uint16_t)bytes,le16(wire+8),
        le16(wire+10),le16(wire+12),le16(wire+14),le16(wire+16)};
    const comp_emote_catalog_t catalog={.frames=&f,.frame_count=1u};
    const comp_emote_asset_pack_t pack={.format_version=1u,
        .profile={200u,200u,25u,COMP_SCREEN_PIXEL_FORMAT_MONO_1BPP_WHITE_IS_ONE_MSB},
        .frame_encoding=(comp_emote_frame_encoding_t)r->frame_encoding,
        .payload_offset=r->payload_offset,.payload_size=r->payload_size,
        .has_payload_crc32=true,.catalog=&catalog,.store=r->store};
    return comp_emote_asset_pack_read_frame(&pack,&f,frame,5000u);
}
#endif
static bool identity(const uint8_t id[32])
{
    const char *expected = COMP_RESOURCE_EXPECTED_ID;
    const char hex[] = "0123456789ABCDEF";
    for (unsigned i=0; i<32u; ++i)
        if (hex[id[i] >> 4] != expected[i*2] || hex[id[i] & 15] != expected[i*2+1]) return false;
    return true;
}
bool comp_runtime_resources_mount(comp_runtime_resources_t *r, const comp_asset_store_t *store)
{
    if (!r || !store) return false;
    memset(r,0,sizeof(*r));
#if COMPANION_WBA_UI_EXTERNAL
    if(!mount_index(r,store) ||
       !comp_ui_asset_generation_mount(&r->generation,store) ||
       !identity(r->generation.root.resource_id) ||
       r->generation.root.base_pack_size!=COMP_RESOURCE_TOTAL_BYTES ||
       r->generation.root.generation!=COMPANION_WBA_RESOURCE_GENERATION ||
       !store_crc(store,COMP_WBA_EXTERNAL_UI_OFFSET,COMP_WBA_EXTERNAL_UI_BYTES,
           COMP_WBA_EXTERNAL_UI_CRC32))return false;
#else
    const comp_screen_asset_profile_t profile = {200,200,25,COMP_SCREEN_PIXEL_FORMAT_MONO_1BPP_WHITE_IS_ONE_MSB};
    uint8_t scratch[256];
    if (comp_emote_asset_pack_mount_preloaded_catalog(&r->base,store,&profile,
        COMP_RESOURCE_CLIPS,COMP_RESOURCE_CLIP_COUNT,
        COMP_RESOURCE_FRAMES,COMP_RESOURCE_FRAME_COUNT,
        (const char *)COMP_RESOURCE_STRINGS,COMP_RESOURCE_STRING_BYTES,scratch,sizeof(scratch)) != COMP_EMOTE_ASSET_MOUNT_OK ||
        r->base.pack.revision!=COMP_RESOURCE_REVISION ||
        r->base.catalog.clip_count!=COMP_RESOURCE_CLIP_COUNT ||
        r->base.catalog.frame_count!=COMP_RESOURCE_FRAME_COUNT ||
        r->base.pack.payload_offset+r->base.pack.payload_size!=COMP_RESOURCE_TOTAL_BYTES ||
        !comp_emote_asset_pack_verify_payload(&r->base.pack,scratch,sizeof(scratch)) ||
        !comp_ui_asset_generation_mount(&r->generation,store) || !identity(r->generation.root.resource_id) ||
        r->generation.root.base_pack_size!=COMP_RESOURCE_TOTAL_BYTES) return false;
#endif
    r->ready = true;
    return true;
}
bool comp_runtime_resources_read(void *context, const char *state, uint8_t frame[5000])
{
    comp_runtime_resources_t *r = context;
    comp_ui_asset_generation_entry_t e;
    uint16_t encoding;
    if (!r || !r->ready || !state || !frame ||
        !comp_ui_asset_generation_find(&r->generation,comp_ui_asset_state_hash(state),&e)) return false;
    encoding = e.flags & (COMP_UI_ASSET_ENTRY_OVERRIDE_RAW_1BPP |
        COMP_UI_ASSET_ENTRY_OVERRIDE_PACKBITS_1BPP | COMP_UI_ASSET_ENTRY_XOR_PATCH_1BPP);
    if ((encoding == 0u || encoding == COMP_UI_ASSET_ENTRY_XOR_PATCH_1BPP) &&
#if COMPANION_WBA_UI_EXTERNAL
        !read_base(r,e.base_frame_index,frame))return false;
#else
        (e.base_frame_index >= r->base.catalog.frame_count ||
         !comp_emote_asset_pack_read_frame(&r->base.pack,&r->base.catalog.frames[e.base_frame_index],frame,5000u))) return false;
#endif
    if(encoding==0u)return companion_crc32(0u,frame,5000u)==e.frame_crc32;
    return comp_ui_asset_generation_read_override(&r->generation,&e,frame,5000u);
}
bool comp_runtime_resources_read_ui(void *context,uint32_t at,uint8_t *data,size_t n)
{
#if COMPANION_WBA_UI_EXTERNAL
    comp_runtime_resources_t *r=context;
#if COMPANION_WBA_RESOURCE_GENERATION >= 84u
    if(at & COMP_CUSTOMER_BITMAP_FLAG) {
        at &= ~COMP_CUSTOMER_BITMAP_FLAG;
        if(!r || !r->ready || !data || at>COMP_CUSTOMER_ATLAS_BYTES || n>COMP_CUSTOMER_ATLAS_BYTES-at)return false;
        return comp_asset_store_read(r->store,COMP_CUSTOMER_ATLAS_OFFSET+at,data,n);
    }
#endif
    if(!r || !r->ready || !data || at>COMP_WBA_EXTERNAL_UI_BYTES ||
       n>COMP_WBA_EXTERNAL_UI_BYTES-at)return false;
    return comp_asset_store_read(r->store,COMP_WBA_EXTERNAL_UI_OFFSET+at,data,n);
#else
    (void)context;(void)at;(void)data;(void)n;return false;
#endif
}
