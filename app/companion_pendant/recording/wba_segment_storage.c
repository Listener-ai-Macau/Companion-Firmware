#include "wba_segment_storage.h"

static bool range(uint32_t base,uint32_t bytes,uint32_t at,uint32_t n)
{return n&&at>=base&&at-base<=bytes&&n<=bytes-(at-base);}
static bool allowed(const comp_wba_segment_storage_t *s,uint32_t at,uint32_t n)
{
    return s&&!s->poisoned&&s->nor&&(range(s->data_base,s->data_bytes,at,n)||
        range(s->banks[0],COMP_SEGMENT_BANK_BYTES,at,n)||range(s->banks[1],COMP_SEGMENT_BANK_BYTES,at,n));
}
static comp_segment_result_t status(comp_wba_segment_storage_t *s,companion_spi_nor_stm32wba_status_t r)
{
    if(r==COMPANION_SPI_NOR_STM32WBA_OK)return COMP_SEG_OK;
    if(r==COMPANION_SPI_NOR_STM32WBA_PENDING)return COMP_SEG_PENDING;
    s->idle_lookup_read_failed=false;s->poisoned=true;return COMP_SEG_IO_ERROR;
}
static bool matches(const comp_wba_segment_storage_t *s,const comp_segment_catalog_t *c)
{
    return s&&c&&c->port.context==s&&c->banks[0]==s->banks[0]&&c->banks[1]==s->banks[1]&&
        c->data_base==s->data_base&&c->data_bytes==s->data_bytes;
}
static comp_segment_result_t gate(comp_wba_segment_storage_t *s,const comp_segment_io_t *io)
{
    if(!s||s->poisoned||!s->nor||!io)return COMP_SEG_BAD_STATE;
    if(io->kind==COMP_SEG_IO_NONE)return COMP_SEG_OK;
    if(!allowed(s,io->address,io->bytes))return COMP_SEG_BAD_ARGUMENT;
    companion_spi_nor_stm32wba_t *n=s->nor;
    if(io->kind==COMP_SEG_IO_ERASE) {
        /* A different erase worker keeps its owner. The scheduler must run
         * that worker; this new request cannot consume its completion. */
        if(!n->erase_active)return COMP_SEG_OK;
        if(n->erase_address==io->address) {
            uint32_t bytes=companion_spi_nor_stm32wba_erase_chunk(n,io->address,io->bytes);
            if(bytes!=n->erase_bytes)return COMP_SEG_BAD_STATE;
            /* A reader needs a second slice to finish suspension. Do not
             * immediately resume its erase between those two slices. One
             * attempted read buys one yield, so an abandoned reader cannot
             * hold the erase owner after cancellation or capture preemption. */
            if(s->transfer_read_yield){s->transfer_read_yield=false;s->arbitration_yields++;return COMP_SEG_PENDING;}
            return COMP_SEG_OK;
        }
        s->arbitration_yields++;return COMP_SEG_PENDING;
    }
    if(companion_spi_nor_stm32wba_erase_access_ready(n,io->address,io->bytes))return COMP_SEG_OK;
    if(!n->erase_active)return COMP_SEG_BAD_STATE;
    if(io->address<n->erase_address+n->erase_bytes&&n->erase_address<io->address+io->bytes)
        return COMP_SEG_BAD_STATE; /* owned target access is a scheduling bug */
    companion_spi_nor_stm32wba_status_t step =
        n->config.target==COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55 &&
        n->info.jedec_id==UINT32_C(0xef6018) && n->config.transfer_timeout_ms
        ? companion_spi_nor_stm32wba_erase_suspend_step_bounded(n,8u)
        : companion_spi_nor_stm32wba_erase_suspend_step(n);
#if COMPANION_WBA_RECLAIM_TIMING
    if(n->reclaim_timing.active)n->reclaim_timing.interrupted++;
#endif
    comp_segment_result_t r=status(s,step);
    if(r!=COMP_SEG_OK&&r!=COMP_SEG_PENDING)return r;
    /* Even a successful status qualification consumes this slice. Do not
     * stack a page operation onto the same foreground interval. */
    s->arbitration_yields++;return COMP_SEG_PENDING;
}
static bool read_bool(void *v,uint32_t at,uint8_t *p,uint32_t bytes)
{
    comp_wba_segment_storage_t *s=v;
    if(!allowed(s,at,bytes)||!p||bytes>256u)return false;
    return status(s,companion_spi_nor_stm32wba_read(s->nor,at,p,bytes))==COMP_SEG_OK;
}
static bool program_bool(void *v,uint32_t at,const uint8_t *p,uint32_t bytes)
{
    comp_wba_segment_storage_t *s=v;
    if(!allowed(s,at,bytes)||!p||bytes>256u||at/256u!=(at+bytes-1u)/256u)return false;
#if COMPANION_WBA_RECLAIM_TIMING
    const uint32_t before=s->nor->config.now_ms(s->nor->config.context);
#endif
    bool ok=status(s,companion_spi_nor_stm32wba_program(s->nor,at,p,bytes))==COMP_SEG_OK;
#if COMPANION_WBA_RECLAIM_TIMING
    if(s->nor->reclaim_timing.active) {
        s->nor->reclaim_timing.program_calls++;
        s->nor->reclaim_timing.program_ms+=s->nor->config.now_ms(s->nor->config.context)-before;
        if(!ok)s->nor->reclaim_timing.interrupted++;
    }
#endif
    return ok;
}
static bool erase_bool(void *v,uint32_t at,uint32_t remaining,uint32_t *done)
{
    comp_wba_segment_storage_t *s=v;
    if(!done)return false;
    *done=0u;
    if(!allowed(s,at,remaining)||at%4096u||remaining%4096u)return false;
    uint32_t bytes=companion_spi_nor_stm32wba_erase_chunk(s->nor,at,remaining);
    comp_segment_result_t r=status(s,companion_spi_nor_stm32wba_erase_step(s->nor,at,bytes));
    if(r==COMP_SEG_OK)*done=bytes;
    return r==COMP_SEG_OK||r==COMP_SEG_PENDING;
}
static comp_segment_result_t read_audio(void *v,uint32_t at,uint8_t *p,uint32_t bytes)
{
    comp_wba_segment_storage_t *s=v;
    if(!allowed(s,at,bytes)||!p||bytes>256u)return COMP_SEG_BAD_ARGUMENT;
    comp_segment_io_t io={at,bytes,COMP_SEG_IO_READ};comp_segment_result_t r=gate(s,&io);
    if(r!=COMP_SEG_OK)return r;
    if(s->nor->config.target==COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55 &&
       s->nor->info.jedec_id==UINT32_C(0xef6018) && s->nor->config.transfer_timeout_ms) {
        /* Keep verification failures fatal, including released payload errors;
         * the shortened budget changes no write/commit or ownership rules. */
        bool released=false;
        return status(s,companion_spi_nor_stm32wba_read_transient(s->nor,at,p,bytes,&released));
    }
    return status(s,companion_spi_nor_stm32wba_read(s->nor,at,p,bytes));
}
/* A complete radio read command cannot mutate NOR. A failed payload with a
 * successful CS release aborts that transfer, but need not poison an
 * unrelated recording writer. All other failures use the existing fault
 * path; erase owners and program/readback handling are never relaxed. */
static comp_segment_result_t read_transfer_audio(void *v,uint32_t at,uint8_t *p,uint32_t bytes)
{
    comp_wba_segment_storage_t *s=v;
    if(!allowed(s,at,bytes)||!p||bytes>256u)return COMP_SEG_BAD_ARGUMENT;
    if(s->nor->erase_active) {
        /* Other parts keep their existing suspended-erase read path. */
        if(s->nor->config.target!=COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55 ||
           s->nor->info.jedec_id!=UINT32_C(0xef6018) || !s->nor->config.transfer_timeout_ms)
            return read_audio(v,at,p,bytes);
        comp_segment_io_t io={at,bytes,COMP_SEG_IO_READ};
        s->transfer_read_yield=true;
        comp_segment_result_t ready=gate(s,&io);
        if(ready!=COMP_SEG_OK){if(ready!=COMP_SEG_PENDING)s->transfer_read_yield=false;return ready;}
    }
    s->transfer_read_yield=false;
    s->transfer_read_released_failure=false;
    bool released=false;
    companion_spi_nor_stm32wba_status_t r=companion_spi_nor_stm32wba_read_transient(s->nor,at,p,bytes,&released);
    if(r!=COMPANION_SPI_NOR_STM32WBA_OK&&released) {
        s->transfer_read_released_failure=true;return COMP_SEG_IO_ERROR;
    }
    return status(s,r);
}
static comp_segment_result_t read_writer_audio(void *v,uint32_t at,uint8_t *p,uint32_t bytes)
{
    comp_wba_segment_storage_t *s=v;
    if(!allowed(s,at,bytes)||!p||bytes>256u)return COMP_SEG_BAD_ARGUMENT;
    if(s->nor->config.target!=COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55 ||
       s->nor->info.jedec_id!=UINT32_C(0xef6018) || !s->nor->config.transfer_timeout_ms)
        return read_audio(v,at,p,bytes);
    uint32_t started=s->nor->config.now_ms(s->nor->config.context);
    comp_segment_io_t io={at,bytes,COMP_SEG_IO_READ};comp_segment_result_t ready=gate(s,&io);
    if(ready!=COMP_SEG_OK)return ready;
    bool released=false;
    companion_spi_nor_stm32wba_status_t r=companion_spi_nor_stm32wba_read_transient(s->nor,at,p,bytes,&released);
    /* Never stack slow timeouts against the next capture DMA deadline. */
    if(r!=COMPANION_SPI_NOR_STM32WBA_OK&&released&&
       (uint32_t)(s->nor->config.now_ms(s->nor->config.context)-started)<3u)
        return COMP_SEG_RETRYABLE_READ;
    return status(s,r);
}
static comp_segment_result_t program_audio(void *v,uint32_t at,const uint8_t *p,uint32_t bytes)
{
    comp_wba_segment_storage_t *s=v;
    if(!allowed(s,at,bytes)||!p||bytes>256u||at/256u!=(at+bytes-1u)/256u)return COMP_SEG_BAD_ARGUMENT;
    comp_segment_io_t io={at,bytes,COMP_SEG_IO_PROGRAM};comp_segment_result_t r=gate(s,&io);
    if(r!=COMP_SEG_OK)return r;
    return status(s,companion_spi_nor_stm32wba_program(s->nor,at,p,bytes));
}
bool comp_wba_segment_storage_init(comp_wba_segment_storage_t *s,companion_spi_nor_stm32wba_t *n,
    uint32_t a,uint32_t b,uint32_t base,uint32_t bytes)
{
    if(!s||!n||!companion_spi_nor_stm32wba_ready(n)||!n->erase_suspend_supported||
       a%4096u||b%4096u||base%4096u||!bytes||bytes%4096u||
       a>n->info.size_bytes||COMP_SEGMENT_BANK_BYTES>n->info.size_bytes-a||
       b>n->info.size_bytes||COMP_SEGMENT_BANK_BYTES>n->info.size_bytes-b||
       base>n->info.size_bytes||bytes>n->info.size_bytes-base||
       !(a+COMP_SEGMENT_BANK_BYTES<=b||b+COMP_SEGMENT_BANK_BYTES<=a)||
       !(a+COMP_SEGMENT_BANK_BYTES<=base||base+bytes<=a)||
       !(b+COMP_SEGMENT_BANK_BYTES<=base||base+bytes<=b))return false;
    memset(s,0,sizeof(*s));s->nor=n;s->banks[0]=a;s->banks[1]=b;s->data_base=base;s->data_bytes=bytes;
    return true;
}
comp_segment_port_t comp_wba_segment_storage_catalog_port(comp_wba_segment_storage_t *s)
{return (comp_segment_port_t){read_bool,program_bool,erase_bool,s};}
comp_segment_result_t comp_wba_segment_storage_mount_begin(comp_wba_segment_storage_t *s,
    comp_segment_catalog_t *c,const uint8_t uid[12],uint64_t epoch)
{
    if(!s||!s->nor)return COMP_SEG_BAD_ARGUMENT;
    comp_segment_port_t port=comp_wba_segment_storage_catalog_port(s);
    comp_segment_result_t result=comp_segment_catalog_mount_begin(c,&port,s->banks[0],s->banks[1],
        s->data_base,s->data_bytes,uid,epoch);
    if(result==COMP_SEG_PENDING)c->reclaim_block_sectors=s->nor->info.erase_32k_supported?8u:0u;
    return result;
}
comp_segment_audio_port_t comp_wba_segment_storage_audio_port(comp_wba_segment_storage_t *s)
{return (comp_segment_audio_port_t){read_audio,program_audio,s};}
comp_segment_audio_port_t comp_wba_segment_storage_writer_audio_port(comp_wba_segment_storage_t *s)
{return (comp_segment_audio_port_t){read_writer_audio,program_audio,s};}
comp_segment_audio_port_t comp_wba_segment_storage_transfer_audio_port(comp_wba_segment_storage_t *s)
{return (comp_segment_audio_port_t){read_transfer_audio,NULL,s};}
comp_segment_result_t comp_wba_segment_storage_catalog_poll(comp_wba_segment_storage_t *s,comp_segment_catalog_t *c)
{
    if(!matches(s,c))return COMP_SEG_BAD_ARGUMENT;
    comp_segment_io_t io;comp_segment_result_t r=comp_segment_catalog_next_io(c,&io);
    if(r!=COMP_SEG_OK)return r;
    r=gate(s,&io);return r==COMP_SEG_OK?comp_segment_catalog_poll(c):r;
}
typedef struct {
    comp_wba_segment_storage_t *storage;
    comp_segment_reserve_t *reserve;
    uint32_t started;
} reserve_read_context_t;
static comp_segment_result_t reserve_bounded_read(void *v,uint32_t at,uint8_t *p,uint32_t bytes)
{
    reserve_read_context_t *context=v;
    comp_wba_segment_storage_t *s=context->storage;bool released=false;
    if(!allowed(s,at,bytes)||!p||bytes>256u)return COMP_SEG_BAD_ARGUMENT;
    /* Only the reservation reader reuses exact complete-sector physical FF
     * proofs. Catalog/ownership search and dirty-sector erases stay unchanged. */
    if(companion_nor_blank_known(&s->nor->blank_cache,at,bytes)) {
        memset(p,255,bytes);context->reserve->read_retries=0u;return COMP_SEG_OK;
    }
    companion_spi_nor_stm32wba_status_t result=companion_spi_nor_stm32wba_read_transient(s->nor,at,p,bytes,&released);
    if(result==COMPANION_SPI_NOR_STM32WBA_OK)context->reserve->read_retries=0u;
    /* Only a fast payload failure with a definitively released transaction is
     * safe to retry. A pending poll never advances the reservation cursor. */
    if(result!=COMPANION_SPI_NOR_STM32WBA_OK&&released&&
       (uint32_t)(s->nor->config.now_ms(s->nor->config.context)-context->started)<3u&&
       context->reserve->read_retries<2u) {
        context->reserve->read_retries++;
        return COMP_SEG_PENDING;
    }
    return status(s,result);
}
comp_segment_result_t comp_wba_segment_storage_reserve_poll(comp_wba_segment_storage_t *s,comp_segment_reserve_t *reserve)
{
    if(!reserve||!matches(s,reserve->catalog))return COMP_SEG_BAD_ARGUMENT;
    if(!s->nor)return COMP_SEG_BAD_STATE;
    if(reserve->candidate<=UINT32_MAX-s->data_base &&
       companion_nor_blank_known(&s->nor->blank_cache,s->data_base+reserve->candidate,reserve->bytes) &&
       comp_segment_reserve_accept_blank_proof(reserve))return COMP_SEG_OK;
    comp_segment_io_t io;comp_segment_result_t r=comp_segment_reserve_next_io(reserve,&io);
    if(r!=COMP_SEG_OK)return r;
    const bool qualified=s->nor->config.target==COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55 &&
        s->nor->info.jedec_id==UINT32_C(0xef6018) && s->nor->config.transfer_timeout_ms;
    const uint32_t started=qualified?s->nor->config.now_ms(s->nor->config.context):0u;
    r=gate(s,&io);if(r!=COMP_SEG_OK)return r;
    if(qualified) {
        reserve_read_context_t context={s,reserve,started};
        const uint8_t phase=reserve->phase,scan=reserve->scan;
        const uint32_t cursor=reserve->cursor,candidate=reserve->candidate,generation=reserve->generation;
        r=comp_segment_reserve_poll_scoped(reserve,reserve_bounded_read,&context);
        if((r==COMP_SEG_OK||r==COMP_SEG_PENDING)&&
           (phase!=reserve->phase||scan!=reserve->scan||cursor!=reserve->cursor||
            candidate!=reserve->candidate||generation!=reserve->generation))reserve->read_retries=0u;
        return r;
    }
    return comp_segment_reserve_poll(reserve);
}
comp_segment_result_t comp_wba_segment_storage_entry_intent(comp_wba_segment_storage_t *s,
    comp_segment_catalog_t *c,uint8_t index,comp_segment_entry_t *e,comp_segment_discard_intent_t *intent)
{
    if(!matches(s,c)||!e)return COMP_SEG_BAD_ARGUMENT;
    comp_segment_io_t io;comp_segment_result_t r=comp_segment_catalog_entry_io(c,index,&io);
    if(r!=COMP_SEG_OK)return r;
    r=gate(s,&io);
    if(r!=COMP_SEG_OK)return r;
    const bool lookup_idle=!c->phase&&!s->nor->erase_active;
    r=comp_segment_catalog_read_intent(c,index,e,intent);
    if(lookup_idle&&r==COMP_SEG_IO_ERROR&&s->poisoned)s->idle_lookup_read_failed=true;
    return r;
}
comp_segment_result_t comp_wba_segment_storage_entry(comp_wba_segment_storage_t *s,
    comp_segment_catalog_t *c,uint8_t index,comp_segment_entry_t *e)
{return comp_wba_segment_storage_entry_intent(s,c,index,e,NULL);}
static comp_segment_result_t transfer_directory_read(void *v,uint32_t at,uint8_t *p,uint32_t bytes)
{
    comp_wba_segment_storage_t *s=v;
    bool released=false;
    companion_spi_nor_stm32wba_status_t r=companion_spi_nor_stm32wba_read_transient(s->nor,at,p,bytes,&released);
    if(r!=COMPANION_SPI_NOR_STM32WBA_OK&&released) {
        s->transfer_read_released_failure=true;return COMP_SEG_PENDING;
    }
    return status(s,r);
}
bool comp_wba_segment_storage_reclaim_read_supported(const comp_wba_segment_storage_t *s)
{
    const companion_spi_nor_stm32wba_t *n=s?s->nor:NULL;
    return n&&n->config.target==COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55&&
        n->info.jedec_id==UINT32_C(0xef6018)&&n->erase_suspend_supported&&n->config.transfer_timeout_ms;
}
comp_segment_result_t comp_wba_segment_storage_transfer_entry(comp_wba_segment_storage_t *s,
    comp_segment_catalog_t *c,uint8_t index,comp_segment_entry_t *e)
{
    if(!matches(s,c)||!e)return COMP_SEG_BAD_ARGUMENT;
    if(c->phase&&!comp_wba_segment_storage_reclaim_read_supported(s))return COMP_SEG_PENDING;
    s->transfer_read_released_failure=false;
    comp_segment_io_t io;comp_segment_result_t r=comp_segment_catalog_transfer_entry_io(c,index,&io);
    if(r!=COMP_SEG_OK){s->transfer_read_yield=false;return r;}
    if(s->nor->erase_active)s->transfer_read_yield=true;
    r=gate(s,&io);if(r!=COMP_SEG_OK){if(r!=COMP_SEG_PENDING)s->transfer_read_yield=false;return r;}
    s->transfer_read_yield=false;
    /* gate() already admitted a non-overlapping read while the erase owner is
     * suspended. Use the same bounded/released-payload isolation as audio on
     * the qualified WBA55/NOR combination; leave other parts unchanged. */
    if(s->nor->erase_active && !comp_wba_segment_storage_reclaim_read_supported(s))
        return comp_wba_segment_storage_entry(s,c,index,e);
    r=comp_segment_catalog_read_scoped(c,index,e,transfer_directory_read,s);
    if(r==COMP_SEG_IO_ERROR&&s->poisoned&&!c->phase&&!s->nor->erase_active)
        s->idle_lookup_read_failed=true; /* retain existing idle-only recovery */
    return r;
}
static comp_segment_result_t cancellation_catalog(void *s,comp_segment_catalog_t *c)
{return comp_wba_segment_storage_catalog_poll(s,c);}
comp_segment_result_t comp_wba_segment_storage_reserve_cancel_poll(comp_wba_segment_storage_t *s,comp_segment_reserve_t *r)
{
    if(!r||!matches(s,r->catalog))return COMP_SEG_BAD_ARGUMENT;
    if(s->poisoned||!s->nor)return COMP_SEG_BAD_STATE;
    comp_segment_io_t io;comp_segment_result_t result=comp_segment_reserve_next_io(r,&io);
    if(result!=COMP_SEG_OK)return result;
    if(r->catalog->phase&&r->catalog->pending==r->entry) {
        result=gate(s,&io);if(result!=COMP_SEG_OK)return result;
        return comp_segment_reserve_cancel_poll(r);
    }
    if(s->nor->erase_active) {
        /* A live allocator may retire only its exact outstanding chunk.
         * Never cancel a catalog owner while NOR still owns an erase. */
        if(io.kind!=COMP_SEG_IO_ERASE||io.address!=s->nor->erase_address||
           companion_spi_nor_stm32wba_erase_chunk(s->nor,io.address,io.bytes)!=s->nor->erase_bytes)
            return COMP_SEG_PENDING;
        result=comp_wba_segment_storage_reserve_poll(s,r);
        return result==COMP_SEG_OK?COMP_SEG_PENDING:result;
    }
    return comp_segment_reserve_cancel_poll(r);
}
comp_segment_result_t comp_wba_segment_storage_receipt(comp_wba_segment_storage_t *s,
    comp_segment_catalog_t *c,uint8_t index,comp_segment_entry_t *e)
{
    if(!matches(s,c)||!e)return COMP_SEG_BAD_ARGUMENT;
    comp_segment_io_t io;comp_segment_result_t r=comp_segment_catalog_receipt_io(c,index,&io);
    if(r!=COMP_SEG_OK)return r;
    r=gate(s,&io);
    if(r!=COMP_SEG_OK)return r;
    const bool lookup_idle=!c->phase&&!s->nor->erase_active;
    r=comp_segment_catalog_receipt_read(c,index,e);
    if(lookup_idle&&r==COMP_SEG_IO_ERROR&&s->poisoned)s->idle_lookup_read_failed=true;
    return r;
}
comp_segment_result_t comp_wba_segment_storage_cancel_poll(comp_wba_segment_storage_t *s,comp_segment_audio_t *a)
{
    if(!a||!matches(s,a->cancellation))return COMP_SEG_BAD_ARGUMENT;
    return comp_segment_audio_cancel_poll(a,cancellation_catalog,s);
}
