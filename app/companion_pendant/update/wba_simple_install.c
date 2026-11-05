#include "wba_simple_install.h"
#include <string.h>

static uint32_t u32(const uint8_t *p)
{return (uint32_t)p[0]|((uint32_t)p[1]<<8u)|((uint32_t)p[2]<<16u)|((uint32_t)p[3]<<24u);}
static void put32(uint8_t *p,uint32_t v)
{for(unsigned i=0u;i<4u;++i)p[i]=(uint8_t)(v>>(8u*i));}
static bool record_valid(const uint8_t *p,const char *magic,size_t n)
{return !memcmp(p,magic,4u)&&p[4]==3u&&p[5]==0u&&
    ((size_t)p[6]|((size_t)p[7]<<8u))==n&&
    u32(p+n-4u)==comp_wba_update_wire_crc32(p,n-4u);}
static void record_start(uint8_t *p,const char *magic,size_t n)
{memset(p,0,n);memcpy(p,magic,4u);p[4]=3u;p[6]=(uint8_t)n;p[7]=(uint8_t)(n>>8u);}
bool comp_wba_simple_current_record(uint8_t out[COMP_SIMPLE_CURRENT_BYTES],
    const uint8_t h[COMP_WBA_SIMPLE_HEADER_BYTES])
{
    if(!out||!h)return false;
    record_start(out,"SCU3",COMP_SIMPLE_CURRENT_BYTES);
    memcpy(out+12u,h,COMP_WBA_SIMPLE_HEADER_BYTES);
    put32(out+188u,comp_wba_update_wire_crc32(out,188u));return true;
}
bool comp_wba_simple_pending_record(uint8_t out[COMP_SIMPLE_PENDING_BYTES],
    uint32_t base,uint32_t bytes,const uint8_t h[COMP_WBA_SIMPLE_HEADER_BYTES])
{
    if(!out||!h||!bytes||base%4096u)return false;
    record_start(out,"SPU3",COMP_SIMPLE_PENDING_BYTES);
    put32(out+8u,base);put32(out+12u,bytes);
    memcpy(out+16u,h,COMP_WBA_SIMPLE_HEADER_BYTES);
    put32(out+192u,comp_wba_update_wire_crc32(out,192u));return true;
}
typedef struct {
    const comp_wba_simple_install_config_t *c;
    const uint8_t *header;
    const comp_wba_simple_package_t *package;
    uint32_t base,bytes;
    bool destination;
} reader_t;
static bool read_package(void *context,uint32_t at,uint8_t *out,size_t n)
{
    reader_t *r=context;const comp_wba_simple_install_ports_t *p=&r->c->ports;
    if(at>r->bytes||n>r->bytes-at)return false;
    if(p->keep_alive)p->keep_alive(p->context);
    if(!r->destination)return p->nor_read(p->context,r->base+at,out,n);
    while(n) {
        uint32_t end;size_t k;bool ok;
        if(at<COMP_WBA_SIMPLE_HEADER_BYTES) {
            end=COMP_WBA_SIMPLE_HEADER_BYTES;k=end-at;if(k>n)k=n;
            memcpy(out,r->header+at,k);ok=true;
        }else if(at-COMP_WBA_SIMPLE_HEADER_BYTES<r->package->app_bytes) {
            uint32_t off=at-COMP_WBA_SIMPLE_HEADER_BYTES;
            end=r->package->app_bytes;k=end-off;if(k>n)k=n;
            ok=p->flash_read(p->context,r->c->limits.app_address+off,out,k);
        }else {
            uint32_t off=at-COMP_WBA_SIMPLE_HEADER_BYTES-r->package->app_bytes;
            end=r->package->resource_bytes;if(off>end)return false;
            k=end-off;if(k>n)k=n;
            if(!k)return false;
            ok=p->nor_read(p->context,off,out,k);
        }
        if(!ok)return false;
        at+=(uint32_t)k;out+=k;n-=k;
    }
    return true;
}
static bool metadata_range(const comp_wba_simple_install_config_t *c,uint32_t at)
{return !(at%4096u)&&at>=c->limits.static_bytes&&
    at-c->limits.static_bytes<=c->limits.metadata_bytes&&
    c->limits.metadata_bytes-(at-c->limits.static_bytes)>=4096u;}
static bool copy_app(reader_t *r,uint8_t *scratch,size_t capacity)
{
    const comp_wba_simple_install_config_t *c=r->c;
    const comp_wba_simple_install_ports_t *p=&c->ports;
    uint32_t bytes=r->package->app_bytes;
    for(uint32_t page=0u;page<bytes;page+=c->flash_page_bytes) {
        if(p->keep_alive)p->keep_alive(p->context);
        if(!p->flash_erase(p->context,c->limits.app_address+page))return false;
        uint32_t page_bytes=bytes-page;if(page_bytes>c->flash_page_bytes)page_bytes=c->flash_page_bytes;
        for(uint32_t at=0u;at<page_bytes;) {
            size_t n=page_bytes-at;if(n>capacity)n=capacity;
            if(!read_package(r,COMP_WBA_SIMPLE_HEADER_BYTES+page+at,scratch,n)||
               !p->flash_write(p->context,c->limits.app_address+page+at,scratch,n))return false;
            at+=(uint32_t)n;
        }
    }
    return true;
}
static bool copy_resources(reader_t *r,uint8_t *scratch,size_t capacity)
{
    const comp_wba_simple_install_ports_t *p=&r->c->ports;
    for(uint32_t page=0u;page<r->package->resource_bytes;page+=4096u) {
        if(p->keep_alive)p->keep_alive(p->context);
        if(!p->nor_erase(p->context,page))return false;
        for(uint32_t at=0u;at<4096u;) {
            size_t n=4096u-at;if(n>capacity)n=capacity;
            if(!read_package(r,COMP_WBA_SIMPLE_HEADER_BYTES+r->package->app_bytes+page+at,scratch,n)||
               !p->nor_write(p->context,page+at,scratch,n))return false;
            at+=(uint32_t)n;
        }
    }
    return true;
}
static bool retire_pending(const comp_wba_simple_install_config_t *c,uint8_t *scratch)
{
    if(!c->ports.nor_erase(c->ports.context,c->pending)||
       !c->ports.nor_read(c->ports.context,c->pending,scratch,COMP_SIMPLE_PENDING_BYTES))return false;
    for(size_t i=0u;i<COMP_SIMPLE_PENDING_BYTES;++i)if(scratch[i]!=255u)return false;
    return true;
}
static comp_wba_simple_boot_result_t intact_current(reader_t *current,
    uint8_t *scratch,size_t capacity,bool discard_pending,comp_wba_simple_boot_error_t *error)
{
    *error=COMP_SIMPLE_ERROR_AUTH;
    if(!comp_wba_simple_package_verify(current->package,&current->c->limits,
        &current->c->trust,read_package,current,scratch,capacity))return COMP_SIMPLE_BOOT_RECOVERY;
    /* Rejecting a damaged download is safe only while the actual current
     * App AND resources still authenticate in place. Never restore an old
     * image or discard the sole candidate after a partial installation. */
    if(discard_pending&&!retire_pending(current->c,scratch))return COMP_SIMPLE_BOOT_RECOVERY;
    *error=COMP_SIMPLE_ERROR_NONE;return COMP_SIMPLE_BOOT_CURRENT;
}
comp_wba_simple_boot_result_t comp_wba_simple_boot_run(
    const comp_wba_simple_install_config_t *c,uint8_t *scratch,size_t capacity,
    comp_wba_simple_boot_error_t *error)
{
    comp_wba_simple_boot_error_t local;
    if(!error)error=&local;
    *error=COMP_SIMPLE_ERROR_CONFIG;
    if(!c||!scratch||capacity<512u||!c->ports.nor_read||!c->ports.nor_write||
       !c->ports.nor_erase||!c->ports.flash_read||!c->ports.flash_write||
       !c->ports.flash_erase||
#if defined(COMP_WBA_SIMPLE_ALLOW_4K_INTERNAL_FLASH) && COMP_WBA_SIMPLE_ALLOW_4K_INTERNAL_FLASH
       (c->flash_page_bytes!=8192u&&c->flash_page_bytes!=4096u)||
       c->limits.app_address%c->flash_page_bytes||c->limits.app_capacity%c->flash_page_bytes||
#else
       c->flash_page_bytes!=8192u||
       c->limits.app_address%8192u||c->limits.app_capacity%8192u||
#endif
       !c->limits.static_bytes||c->limits.static_bytes%4096u||
       c->limits.static_bytes>c->limits.nor_bytes||
       c->limits.metadata_bytes>c->limits.nor_bytes-c->limits.static_bytes||
       !metadata_range(c,c->current[0])||!metadata_range(c,c->current[1])||
       !metadata_range(c,c->pending)||c->current[0]==c->current[1]||
       c->current[0]==c->pending||c->current[1]==c->pending)return COMP_SIMPLE_BOOT_RECOVERY;
    /* Internal Flash writes start on a 16-byte quadword. A caller's odd
     * scratch capacity must never make the next chunk unaligned. */
    capacity-=capacity%16u;
    /* Both small current records are read, no historical image backup. */
    uint8_t current[2][COMP_SIMPLE_CURRENT_BYTES],pending[COMP_SIMPLE_PENDING_BYTES];
    comp_wba_simple_package_t selected={0},parsed;bool found=false;unsigned bank=0u;
    *error=COMP_SIMPLE_ERROR_CURRENT;
    for(unsigned i=0u;i<2u;++i) {
        if(!c->ports.nor_read(c->ports.context,c->current[i],current[i],sizeof(current[i])))return COMP_SIMPLE_BOOT_RECOVERY;
        if(!record_valid(current[i],"SCU3",sizeof(current[i]))||u32(current[i]+8u)||
           !comp_wba_simple_package_open(&parsed,current[i]+12u,COMP_WBA_SIMPLE_HEADER_BYTES,&c->limits))continue;
        if(!found||parsed.signed_manifest.manifest.component_version>selected.signed_manifest.manifest.component_version) {
            selected=parsed;bank=i;found=true;
        }else if(parsed.signed_manifest.manifest.component_version==selected.signed_manifest.manifest.component_version&&
                 memcmp(current[i]+12u,current[bank]+12u,COMP_WBA_SIMPLE_HEADER_BYTES))return COMP_SIMPLE_BOOT_RECOVERY;
    }
    if(!found||selected.signed_manifest.manifest.component_version<c->minimum_app||
       selected.resource_version<c->minimum_resources)return COMP_SIMPLE_BOOT_RECOVERY;
    *error=COMP_SIMPLE_ERROR_PENDING;
    if(!c->ports.nor_read(c->ports.context,c->pending,pending,sizeof(pending)))return COMP_SIMPLE_BOOT_RECOVERY;
    bool installing=record_valid(pending,"SPU3",sizeof(pending));
    const uint8_t *header=current[bank]+12u;
    reader_t reader={c,header,&selected,0u,
        COMP_WBA_UPDATE_MANIFEST_WIRE_BYTES+selected.signed_manifest.manifest.size_bytes,true};
    reader_t current_reader=reader;
    bool pending_dirty=false;
    for(size_t i=0u;i<sizeof(pending);++i)if(pending[i]!=255u)pending_dirty=true;
    if(installing) {
        if(!comp_wba_simple_package_open(&parsed,pending+16u,COMP_WBA_SIMPLE_HEADER_BYTES,&c->limits))
            return intact_current(&current_reader,scratch,capacity,true,error);
        bool same=!memcmp(header,pending+16u,COMP_WBA_SIMPLE_HEADER_BYTES);
        if(!same&&!comp_wba_simple_package_newer(&parsed,selected.signed_manifest.manifest.component_version,
                                               selected.resource_version))return intact_current(&current_reader,scratch,capacity,true,error);
        reader.base=u32(pending+8u);reader.bytes=u32(pending+12u);reader.destination=false;
        reader.header=pending+16u;reader.package=&parsed;
        if(reader.base%4096u||reader.base<c->limits.static_bytes+c->limits.metadata_bytes||
           reader.base>c->limits.nor_bytes||reader.bytes>c->limits.nor_bytes-reader.base||
           reader.bytes!=COMP_WBA_UPDATE_MANIFEST_WIRE_BYTES+parsed.signed_manifest.manifest.size_bytes)
            return intact_current(&current_reader,scratch,capacity,true,error);
    }
    if(!installing)return intact_current(&current_reader,scratch,capacity,pending_dirty,error);
    *error=COMP_SIMPLE_ERROR_AUTH;
    if(!comp_wba_simple_package_verify(reader.package,&c->limits,&c->trust,
                                      read_package,&reader,scratch,capacity))
        return intact_current(&current_reader,scratch,capacity,true,error);
    /* No destination mutation occurs before the complete verification above. */
    *error=COMP_SIMPLE_ERROR_FLASH;
    if(!copy_app(&reader,scratch,capacity))return COMP_SIMPLE_BOOT_RECOVERY;
    *error=COMP_SIMPLE_ERROR_RESOURCES;
    if(!copy_resources(&reader,scratch,capacity))return COMP_SIMPLE_BOOT_RECOVERY;
    reader.destination=true;*error=COMP_SIMPLE_ERROR_DESTINATION;
    if(!comp_wba_simple_package_verify(reader.package,&c->limits,&c->trust,
                                      read_package,&reader,scratch,capacity))return COMP_SIMPLE_BOOT_RECOVERY;
    *error=COMP_SIMPLE_ERROR_PUBLICATION;
    if(memcmp(header,reader.header,COMP_WBA_SIMPLE_HEADER_BYTES)) {
        uint8_t published[COMP_SIMPLE_CURRENT_BYTES];
        unsigned next=1u-bank;
        if(!comp_wba_simple_current_record(published,reader.header)||
           !c->ports.nor_erase(c->ports.context,c->current[next])||
           !c->ports.nor_write(c->ports.context,c->current[next],published,sizeof(published))||
           !c->ports.nor_read(c->ports.context,c->current[next],scratch,sizeof(published))||
           memcmp(published,scratch,sizeof(published)))return COMP_SIMPLE_BOOT_RECOVERY;
    }
    if(!retire_pending(c,scratch))return COMP_SIMPLE_BOOT_RECOVERY;
    *error=COMP_SIMPLE_ERROR_NONE;return COMP_SIMPLE_BOOT_INSTALLED;
}
