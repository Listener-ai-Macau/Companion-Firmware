#include "system_storage.h"
#include "wba_workspace_layout.h"
#include "wba_system_confirmed.h"
#include <string.h>
static uint32_t u32(const uint8_t *p)
{return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static bool read_raw(void *ctx,uint32_t at,uint8_t *out,size_t n)
{comp_v11_system_storage_t*s=ctx;return companion_spi_nor_stm32wba_read(s->config.nor,at,out,n)==COMPANION_SPI_NOR_STM32WBA_OK;}
static bool write_raw(void *ctx,uint32_t at,const uint8_t *data,size_t n)
{comp_v11_system_storage_t*s=ctx;return companion_spi_nor_stm32wba_program(s->config.nor,at,data,n)==COMPANION_SPI_NOR_STM32WBA_OK;}
static bool erase_raw(void *ctx,uint32_t at)
{comp_v11_system_storage_t*s=ctx;return companion_spi_nor_stm32wba_erase_4k(s->config.nor,at)==COMPANION_SPI_NOR_STM32WBA_OK;}
static bool idle(void *ctx)
{comp_v11_system_storage_t*s=ctx;return !s->config.nor->erase_active && s->config.idle(s->config.context);}
static bool load(void *ctx,uint8_t *record,bool *blank)
{
    comp_v11_system_storage_t*s=ctx;
    comp_wba_system_journal_ports_t p={read_raw,write_raw,erase_raw,s,s->config.current_static_bytes};
    return comp_wba_system_journal_mount(&s->journal,&p,record,blank);
}
static bool store(void *ctx,const uint8_t *record)
{
    comp_v11_system_storage_t*s=ctx;
    if(!idle(s))return false;
    if(s->first_retry_pending) {
        /* begin() has already authorized the new pair/version and acquired its
         * recording-safe exact tail; only now may this first intent be retried. */
        if(!s->claimed_bytes || u32(record+16u)!=s->claimed_base ||
           u32(record+84u)!=s->claimed_bytes ||
           !comp_wba_system_journal_restart_first(&s->journal,record))return false;
        s->first_retry_pending=false;
    }
    return comp_wba_system_journal_store(&s->journal,record);
}
static bool claim(void *ctx,uint32_t bytes,uint32_t minimum,uint32_t exact,uint32_t *base)
{
    comp_v11_system_storage_t*s=ctx;uint32_t expected=COMP_WBA_NOR_TOTAL_BYTES-bytes,got=0u;
    if(!bytes || bytes%4096u || bytes>COMP_WBA_NOR_TOTAL_BYTES || expected<minimum ||
        (exact!=UINT32_MAX && exact!=expected) || (s->claimed_bytes &&
            (bytes!=s->claimed_bytes || s->claimed_base!=expected)) || !idle(s) ||
        !s->config.workspace_reserve(s->config.context,bytes,&got))return false;
    /* Retain even an unexpected accepted claim until remount; do not release
     * ambiguous allocator state and risk another writer reusing its extent.
     */
    s->claimed_bytes=bytes;s->claimed_base=got;
    if(got!=expected)return false;
    *base=got;return true;
}
static bool release(void *ctx,uint32_t base,uint32_t bytes)
{
    comp_v11_system_storage_t*s=ctx;uint32_t ignored=0u;
    if(!bytes || bytes>COMP_WBA_NOR_TOTAL_BYTES || base!=COMP_WBA_NOR_TOTAL_BYTES-bytes ||
        (s->claimed_bytes && (s->claimed_base!=base || s->claimed_bytes!=bytes)) || !idle(s) ||
        !s->config.workspace_reserve(s->config.context,0u,&ignored))return false;
    s->claimed_base=s->claimed_bytes=0u;return true;
}
static bool reconcile(void *ctx)
{
    comp_v11_system_storage_t*s=ctx;uint32_t ignored=0u;
    if(!idle(s) || !s->config.workspace_reserve(s->config.context,0u,&ignored))return false;
    s->claimed_base=s->claimed_bytes=0u;return true;
}
static bool extent(comp_v11_system_storage_t*s,uint32_t at,size_t n)
{
    const uint8_t *r=s->receiver.record;
    return s->receiver.loaded && r[5]!=COMP_WBA_SYSTEM_RETIRED && s->claimed_bytes &&
        u32(r+16u)==s->claimed_base && u32(r+84u)==s->claimed_bytes &&
        at>=s->claimed_base && n<=s->claimed_bytes && at-s->claimed_base<=s->claimed_bytes-n;
}
static bool read_payload(void *ctx,uint32_t at,uint8_t *out,size_t n)
{return extent(ctx,at,n) && idle(ctx) && read_raw(ctx,at,out,n);}
static bool program_payload(void *ctx,uint32_t at,const uint8_t *data,size_t n)
{return extent(ctx,at,n) && idle(ctx) && write_raw(ctx,at,data,n);}
static bool erase_payload(void *ctx,uint32_t at)
{return !(at%4096u) && extent(ctx,at,4096u) && idle(ctx) && erase_raw(ctx,at);}
static bool confirmed(void *ctx,const uint8_t *wire)
{comp_v11_system_storage_t*s=ctx;return s->config.running_pair_verified && s->config.running_pair_verified(s->config.context,wire);}
bool comp_v11_system_storage_init(comp_v11_system_storage_t*s,const comp_v11_system_storage_config_t*c)
{
    if(!s || !c || !c->nor || !c->idle || !c->workspace_reserve ||
        !companion_spi_nor_stm32wba_ready(c->nor) ||
        c->nor->info.size_bytes!=COMP_WBA_NOR_TOTAL_BYTES || c->nor->erase_active ||
        c->current_static_bytes!=COMP_WBA_NOR_UI_BYTES ||
        !comp_wba_update_p256_trust_configured(&c->trust))return false;
    comp_v11_system_storage_config_t copy=*c;memset(s,0,sizeof(*s));s->config=copy;
    comp_wba_system_receive_config_t cfg={0};
    cfg.ports=(comp_wba_system_receive_ports_t){load,store,idle,claim,release,reconcile,confirmed,
        read_payload,erase_payload,program_payload,s};
    cfg.trust=copy.trust;cfg.current_firmware=copy.current_firmware;
    cfg.current_resources=copy.current_resources;cfg.current_static_bytes=copy.current_static_bytes;
    cfg.current_resource_sha256=copy.current_resource_sha256;
    if(!idle(s) || !comp_wba_workspace_layout_valid(read_raw,s))return false;
    s->ready=comp_wba_system_receive_mount(&s->receiver,&cfg);
    if(!s->ready && s->journal.scanned && copy.current_pair_verified &&
       comp_wba_system_journal_first_torn(&s->journal.ports)) {
        comp_wba_system_confirmed_t proof;bool blank;
        comp_wba_system_confirmed_ports_t cp={read_raw,write_raw,erase_raw,NULL,
            confirmed,s,copy.trust};
        if(comp_wba_system_confirmed_mount(&proof,&cp,copy.current_static_bytes,&blank) && !blank &&
           u32(proof.record+128u)==copy.current_firmware &&
           u32(proof.record+272u)==copy.current_resources &&
           copy.current_pair_verified(copy.context,proof.record+16u)) {
            s->ready=comp_wba_system_receive_prepare_first_retry(&s->receiver,&cfg);
            s->first_retry_pending=s->ready;
        }
    }
    return s->ready;
}
