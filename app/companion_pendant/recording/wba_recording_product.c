#include "wba_recording_product.h"
#include "wba_recording_transfer.h"
#include "wba_recording_crc.h"
#include "companion_recording_space_bound.h"
#include <stddef.h>

enum {BOOT_UNBOUND=0,BOOT_MOUNT,BOOT_OLD_BLANK,BOOT_FORMAT,BOOT_RECOVER,BOOT_SPACE,BOOT_LEASE,BOOT_READY,BOOT_FAILED,BOOT_RUNTIME_RECOVER,BOOT_RUNTIME_SPACE,
      BOOT_SALVAGE_SPACE,BOOT_SALVAGE_RUNTIME_SPACE,BOOT_SALVAGE_LEASE,BOOT_SALVAGE_READY,BOOT_RUNTIME_REMOUNT,BOOT_BOOT_REMOUNT};
enum {SPACE_METRICS=0,SPACE_LOGICAL,SPACE_GAP,SPACE_DONE};
/* During a failed read-only mount or failed idle capacity walk, reporting
 * and capacity are unavailable. Reuse their retired state for bounded retry;
 * the ordinary unset report sentinel is restored at the recovery handoff. */
enum {BOOT_RETRY_ARM0=240,BOOT_RETRY_ARM1,BOOT_RETRY_ARM2,BOOT_RETRY_IDLE_ARM0=243,BOOT_RETRY_IDLE_ARM1,BOOT_RETRY_OWN1=245,BOOT_RETRY_OWN2,BOOT_RETRY_IDLE_OWN1,BOOT_RETRY_IDLE_OWN2,BOOT_RETRY_IDLE_EXHAUSTED};
_Static_assert((int)DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY<(int)BOOT_RETRY_ARM0,
    "boot retry sentinels must not overlap normal recording reports");
/* These ownership walks run at boot or while capture is idle. Keeping them
 * out of hot call-site inlining saves CE flash without changing codec/PDM
 * optimization or adding work to the10ms capture path. */
#if defined(__GNUC__)
#define COMP_REC_BOOT_ONLY __attribute__((cold,noinline))
#else
#define COMP_REC_BOOT_ONLY
#endif

static bool capacity_snapshot(const void *context,uint32_t *generation,uint8_t *segments)
{
    /* This callback is installed only by product_bind on its embedded
     * pipeline. It does not apply to independent/legacy pipeline owners. */
    if(!context)return false;
    const comp_wba_recording_product_t *p=(const comp_wba_recording_product_t *)
        ((const unsigned char *)context - offsetof(comp_wba_recording_product_t,pipeline));
    if(!p||!generation||!segments||!comp_wba_recording_product_capture_available(p)||
       !comp_wba_recording_product_space_current(p)||p->space.allocation_uncertain||
       comp_wba_recording_pipeline_storage_busy(&p->pipeline))return false;
    *generation=p->catalog.generation;*segments=p->space.allocatable_segments;return true;
}

static void fail(comp_wba_recording_product_t *p,comp_segment_result_t why)
{
    bool retry=why==COMP_SEG_IO_ERROR&&p->storage.poisoned;
    if(p->boot_phase==BOOT_MOUNT&&retry)p->reported_state=BOOT_RETRY_ARM0;
    else if(p->boot_phase==BOOT_BOOT_REMOUNT&&retry)
        p->reported_state=p->reported_state==BOOT_RETRY_OWN1?BOOT_RETRY_ARM1:BOOT_RETRY_ARM2;
    else if(p->boot_phase==BOOT_RUNTIME_REMOUNT&&retry&&
            (p->reported_state==BOOT_RETRY_IDLE_OWN1||p->reported_state==BOOT_RETRY_IDLE_OWN2))
        p->reported_state=p->reported_state==BOOT_RETRY_IDLE_OWN1?BOOT_RETRY_IDLE_ARM1:BOOT_RETRY_IDLE_EXHAUSTED;
    else if(comp_wba_recording_product_boot_retry_owned(p))p->reported_state=255u;
    p->last_fault=COMP_WBA_RECORDING_FAULT_STORAGE_IO;
    if(p->media_ready&&p->pipeline.engine_bound)comp_cont_recording_fault(&p->capture.engine,why);
    p->pipeline.failure=why;p->pipeline.state=COMP_PIPE_FAILED;
    p->ready=false;p->boot_phase=BOOT_FAILED;
}
bool comp_wba_recording_product_bind(comp_wba_recording_product_t *p,
    companion_spi_nor_stm32wba_t *nor,uint32_t a,uint32_t b,uint32_t base,uint32_t bytes,
    uint32_t legacy,const uint8_t uid[12],uint64_t epoch,
    const comp_wba_pipeline_config_t *cfg,comp_wba_recording_report_fn_t report)
{
    if(!p||!cfg||!cfg->microphone||!cfg->now_ms||!report||!uid||!epoch||legacy%4096u||
       legacy>base||8192u>base-legacy)return false;
    memset(p,0,sizeof(*p));p->reported_state=255u;p->boot.legacy_catalog=legacy;p->report=report;
    if(!comp_wba_segment_storage_init(&p->storage,nor,a,b,base,bytes)){fail(p,COMP_SEG_BAD_ARGUMENT);return false;}
    p->pipeline.config=*cfg;p->pipeline.config.recording=&p->capture.engine;
    p->pipeline.config.catalog=&p->catalog;p->pipeline.config.storage=&p->storage;
    p->pipeline.config.capacity_snapshot=capacity_snapshot;
    if(comp_wba_segment_storage_mount_begin(&p->storage,&p->catalog,uid,epoch)!=COMP_SEG_PENDING) {
        fail(p,COMP_SEG_BAD_STATE);return false;
    }
    p->boot_phase=BOOT_MOUNT;return true;
}
bool comp_wba_recording_product_catalog_current(const comp_wba_recording_product_t *p)
{
    return p&&p->media_ready&&!p->storage.poisoned&&p->space.valid&&p->catalog.generation==p->space.generation;
}
bool comp_wba_recording_product_space_current(const comp_wba_recording_product_t *p)
{
    return comp_wba_recording_product_catalog_current(p)&&
        p->space.arena_bytes==p->catalog.data_bytes-p->pipeline.workspace_bytes;
}
static bool visible(const comp_segment_entry_t *e)
{return e->state==COMP_SEG_UNSYNCED||e->state==COMP_SEG_ACKED;}
static COMP_REC_BOOT_ONLY comp_segment_result_t space_poll(comp_wba_recording_product_t *p)
{
    comp_wba_recording_space_t *s=&p->space;comp_segment_catalog_t *c=&p->catalog;
    /* An interior OTA claim is exclusive, so its completed inventory cannot
     * change. Keep that inventory for release; the ordinary capacity view is
     * marked busy while the claim exists. Do not mistake owners beyond the
     * middle claim for entries beyond a truncated tail. */
    if(p->pipeline.workspace_bytes&&p->pipeline.workspace_offset!=c->data_bytes-p->pipeline.workspace_bytes)
        return COMP_SEG_PENDING;
    uint32_t arena=c->data_bytes-p->pipeline.workspace_bytes;
    if(s->generation!=c->generation||s->arena_bytes!=arena) {
        memset(s,0,sizeof(*s));s->generation=c->generation;s->arena_bytes=arena;
    }
    if(s->valid)return COMP_SEG_OK;
    /* Runtime recovery remains FAILED to other page users until this scan
     * finishes. Only its exclusive continuation may access the scratch page. */
    if(p->boot_phase!=BOOT_RUNTIME_SPACE&&p->boot_phase!=BOOT_SALVAGE_RUNTIME_SPACE &&
       !comp_wba_recording_pipeline_page_available(&p->pipeline))return COMP_SEG_PENDING;
    comp_segment_entry_t e;comp_segment_result_t r;
    if(s->phase==SPACE_LOGICAL) {
        while(s->look<s->scan&&c->slots[s->look]==255u)s->look++;
        if(s->look==s->scan){s->logical++;s->scan++;s->phase=SPACE_METRICS;return COMP_SEG_PENDING;}
        r=comp_wba_segment_storage_entry(&p->storage,c,s->look,&e);
        if(r!=COMP_SEG_OK)return r;
        s->look++;
        if(visible(&e)&&e.descriptor.session_id==s->session){s->scan++;s->phase=SPACE_METRICS;}
        return COMP_SEG_PENDING;
    }
    while(s->scan<COMP_SEGMENT_CAPACITY&&c->slots[s->scan]==255u)s->scan++;
    if(s->phase==SPACE_METRICS) {
        if(s->scan==COMP_SEGMENT_CAPACITY) {
            s->phase=SPACE_GAP;s->scan=0u;s->nearest_start=arena;return COMP_SEG_PENDING;
        }
        r=comp_wba_segment_storage_entry(&p->storage,c,s->scan,&e);
        if(r!=COMP_SEG_OK)return r;
        uint32_t end=e.extent_offset+e.reserved_bytes;
        if(end>arena||s->reserved_bytes>arena-e.reserved_bytes)return COMP_SEG_CORRUPT;
        s->used++;s->reserved_bytes+=e.reserved_bytes;
        if(e.descriptor.source_mode==COMP_WBA_RECORDING_SOURCE_MIC_SAI) {
            s->microphone_owned=true;
            if(e.state!=COMP_SEG_WRITING)s->microphone_sealed_owned=true;
        }
        if(end>s->highest_end)s->highest_end=end;
        if(e.state==COMP_SEG_WRITING)s->writing++;
        else if(e.state==COMP_SEG_UNSYNCED)s->unsynced++;
        else if(e.state==COMP_SEG_ACKED||e.state==COMP_SEG_ERASING) {
            s->consumed++;s->consumed_bytes+=e.reserved_bytes;
        }
        if(visible(&e)) {
            s->encoded_bytes+=e.descriptor.encoded_length;s->session=e.descriptor.session_id;
            s->look=0u;s->phase=SPACE_LOGICAL;
        } else s->scan++;
        return COMP_SEG_PENDING;
    }
    if(s->phase!=SPACE_GAP)return COMP_SEG_BAD_STATE;
    if(s->scan==COMP_SEGMENT_CAPACITY) {
        uint32_t gap=s->nearest_start-s->cursor;
        if(gap>s->largest_gap){s->largest_gap=gap;s->largest_gap_offset=s->cursor;}
        /* Each segment is allocated independently. Sum only whole extents in
         * each gap, then cap by currently unowned catalog slots. Never infer
         * this from total free bytes, which can include unusable fragments. */
        uint32_t extent=p->pipeline.config.extent_bytes;
        if(!extent||s->used>COMP_SEGMENT_CAPACITY)return COMP_SEG_CORRUPT;
        uint32_t slots=(uint32_t)s->allocatable_segments+gap/extent;
        uint32_t available=COMP_SEGMENT_CAPACITY-s->used;
        s->allocatable_segments=(uint8_t)(slots<available?slots:available);
        if(!s->nearest_end){s->phase=SPACE_DONE;s->valid=true;return COMP_SEG_OK;}
        s->cursor=s->nearest_end;s->nearest_start=arena;s->nearest_end=0u;s->scan=0u;
        return COMP_SEG_PENDING;
    }
    r=comp_wba_segment_storage_entry(&p->storage,c,s->scan,&e);
    if(r!=COMP_SEG_OK)return r;
    s->scan++;
    /* A previously scanned owner crosses this cursor: an overlapping/corrupt
     * ownership map cannot yield a safe independent-extent count. Preserve
     * the pre-existing space view, but refuse the optional new snapshot. */
    if(e.extent_offset<s->cursor && e.extent_offset+e.reserved_bytes>s->cursor)
        s->allocation_uncertain=true;
    /* Compare candidates before choosing the nearest. Equal or fully nested
     * extents can end at/before the later cursor and would otherwise escape
     * the crossing test, despite having two owners for the same bytes. */
    if(s->nearest_end && e.extent_offset<s->nearest_end &&
       s->nearest_start<e.extent_offset+e.reserved_bytes)
        s->allocation_uncertain=true;
    if(e.extent_offset>=s->cursor&&e.extent_offset<s->nearest_start) {
        s->nearest_start=e.extent_offset;s->nearest_end=e.extent_offset+e.reserved_bytes;
    }
    return COMP_SEG_PENDING;
}
uint8_t comp_wba_recording_product_state(const comp_wba_recording_product_t *p)
{
    if(!p||p->boot_phase==BOOT_UNBOUND)return COMP_WBA_RECORDING_UNBOUND;
    if(p->boot_phase==BOOT_RUNTIME_RECOVER||p->boot_phase==BOOT_RUNTIME_SPACE||p->boot_phase==BOOT_RUNTIME_REMOUNT||p->boot_phase==BOOT_BOOT_REMOUNT||
       p->boot_phase==BOOT_SALVAGE_RUNTIME_SPACE)
        return COMP_WBA_RECORDING_PREPARING;
    if(p->boot_phase==BOOT_FAILED||
       p->pipeline.state==COMP_PIPE_FAILED)return COMP_WBA_RECORDING_FAULT;
    if(p->boot_phase==BOOT_SALVAGE_READY&&p->pipeline.state==COMP_PIPE_IDLE)return COMP_WBA_RECORDING_FAULT;
    if(!comp_wba_recording_product_capture_available(p))return COMP_WBA_RECORDING_PREPARING;
    switch(p->pipeline.state) {
    case COMP_PIPE_IDLE:return COMP_WBA_RECORDING_IDLE;
    case COMP_PIPE_PREPARING:return COMP_WBA_RECORDING_PREPARING;
    case COMP_PIPE_READY:return COMP_WBA_RECORDING_READY;
    case COMP_PIPE_RECORDING:return COMP_WBA_RECORDING_CAPTURING;
    case COMP_PIPE_STOPPING:case COMP_PIPE_CLEANUP:return COMP_WBA_RECORDING_STOPPING;
    case COMP_PIPE_FINISHED:return COMP_WBA_RECORDING_TRANSFER_READY;
    default:return COMP_WBA_RECORDING_FAULT;
    }
}
static void report(comp_wba_recording_product_t *p)
{
    if(!p->media_ready||!p->pipeline.token)return;
    bool active=p->capture.engine.microphone_active;
    denzic_audio_recording_state_v1_t state;
    switch(p->pipeline.state) {
    case COMP_PIPE_PREPARING:case COMP_PIPE_READY:state=DENZIC_AUDIO_RECORDING_STATE_PENDING_START;break;
    case COMP_PIPE_RECORDING:state=DENZIC_AUDIO_RECORDING_STATE_RECORDING;break;
    case COMP_PIPE_STOPPING:case COMP_PIPE_CLEANUP:state=DENZIC_AUDIO_RECORDING_STATE_STOPPING;break;
    case COMP_PIPE_FINISHED:state=p->capture.engine.state==COMP_CONT_CANCELED?
        DENZIC_AUDIO_RECORDING_STATE_CANCELED:DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY;break;
    case COMP_PIPE_FAILED:state=active?DENZIC_AUDIO_RECORDING_STATE_STOPPING:DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY;break;
    default:return;
    }
    if(p->reported_state!=(uint8_t)state||p->reported_active!=active) {
        p->report(p->pipeline.config.context,p->pipeline.token,state,active);
        p->reported_state=(uint8_t)state;p->reported_active=active;
    }
}
bool comp_wba_recording_product_stage_pcm_half(comp_wba_recording_product_t *p)
{
    if(!comp_wba_recording_product_pcm_staging_pending(p))return false;
    if(comp_cont_recording_stage_pcm_half(&p->capture.engine))return true;
    if(p->capture.engine.state==COMP_CONT_FAULT) {
        p->pipeline.failure=p->capture.engine.failure;p->pipeline.state=COMP_PIPE_FAILED;
        p->last_fault=COMP_WBA_RECORDING_FAULT_DEADLINE;report(p);
    }
    return false;
}
static COMP_REC_BOOT_ONLY void boot_poll(comp_wba_recording_product_t *p)
{
    comp_segment_result_t r;
    if(p->boot_phase==BOOT_RUNTIME_REMOUNT||p->boot_phase==BOOT_BOOT_REMOUNT) {
        bool startup=p->boot_phase==BOOT_BOOT_REMOUNT;
        r=comp_wba_segment_storage_catalog_poll(&p->storage,&p->catalog);
        if(r==COMP_SEG_PENDING)return;
        /* A runtime remount must never interpret blank/invalid banks as a
         * new device. Only a fully reconstructed durable root may proceed. */
        if(r!=COMP_SEG_OK){fail(p,r);return;}
        r=comp_wba_recording_recovery_begin(&p->capture.recovery,&p->storage,&p->catalog,p->catalog.page);
        if(r!=COMP_SEG_PENDING){fail(p,r);return;}
        p->boot_phase=startup?BOOT_RECOVER:BOOT_RUNTIME_RECOVER;return;
    }
    if(p->boot_phase==BOOT_MOUNT||p->boot_phase==BOOT_FORMAT) {
        r=comp_wba_segment_storage_catalog_poll(&p->storage,&p->catalog);
        if(r==COMP_SEG_PENDING)return;
        if(r==COMP_SEG_UNFORMATTED&&p->boot_phase==BOOT_MOUNT) {p->boot_phase=BOOT_OLD_BLANK;return;}
        if(r!=COMP_SEG_OK){fail(p,r);return;}
        r=comp_wba_recording_recovery_begin(&p->capture.recovery,&p->storage,&p->catalog,p->catalog.page);
        if(r!=COMP_SEG_PENDING){fail(p,r);return;}
        p->boot_phase=BOOT_RECOVER;return;
    }
    if(p->boot_phase==BOOT_OLD_BLANK) {
        if(p->boot.boot_cursor==8192u) {
            r=comp_segment_catalog_format_blank_begin(&p->catalog);
            if(r!=COMP_SEG_PENDING){fail(p,r);return;}
            p->boot_phase=BOOT_FORMAT;return;
        }
        if(companion_spi_nor_stm32wba_read(p->storage.nor,p->boot.legacy_catalog+p->boot.boot_cursor,p->catalog.page,256u)!=COMPANION_SPI_NOR_STM32WBA_OK) {
            fail(p,COMP_SEG_IO_ERROR);return;
        }
        if(comp_rec_not_uniform(p->catalog.page,256u,255u)){fail(p,COMP_SEG_UNFORMATTED);return;}
        p->boot.boot_cursor+=256u;return;
    }
    if(p->boot_phase==BOOT_RECOVER||p->boot_phase==BOOT_RUNTIME_RECOVER) {
        r=comp_wba_recording_recovery_poll(&p->capture.recovery);
        if(r==COMP_SEG_PENDING)return;
        if(r!=COMP_SEG_OK){fail(p,r);return;}
        /* A completed scan with an unresolved WRITING extent is not a bad
         * catalogue. Preserve its ownership, but retire the recovery union
         * so intact SEALED originals can use the ordinary reader/consume.
         * I/O or catalogue failures never enter this path. Runtime recovery
         * already reconciled WUS2 at boot. */
        bool salvage=!comp_wba_recording_recovery_ready(&p->capture.recovery);
        /* Keep the last completed recovery result while a later remount is
         * in flight or fails. Only a new completed scan can clear it. */
        p->retained_tail=salvage;
        bool runtime=p->boot_phase==BOOT_RUNTIME_RECOVER;
        /* No live pointer can retain recovery after this exclusive handoff. */
        memset(&p->capture.engine,0,sizeof(p->capture.engine));
        comp_wba_pipeline_config_t cfg=p->pipeline.config;
        if(!comp_wba_recording_pipeline_init(&p->pipeline,&cfg)){fail(p,COMP_SEG_BAD_ARGUMENT);return;}
        memset(&p->space,0,sizeof(p->space));
        if(salvage) {
            p->last_fault=COMP_WBA_RECORDING_FAULT_STORAGE_IO;
            p->ready=false;p->media_ready=true;
            p->boot_phase=runtime?BOOT_SALVAGE_RUNTIME_SPACE:BOOT_SALVAGE_SPACE;
            if(runtime)p->pipeline.state=COMP_PIPE_FAILED; /* exclusive scratch scan */
        } else if(runtime) {
            /* Keep every public page/update admission closed until the
             * ownership view is current. WUS2 is already mounted and zero
             * workspace was required before retiring this engine. */
            p->pipeline.state=COMP_PIPE_FAILED;p->boot_phase=BOOT_RUNTIME_SPACE;
        } else {p->media_ready=true;p->boot_phase=BOOT_SPACE;}
        return;
    }
    if(p->boot_phase==BOOT_SPACE||p->boot_phase==BOOT_RUNTIME_SPACE||
       p->boot_phase==BOOT_SALVAGE_SPACE||p->boot_phase==BOOT_SALVAGE_RUNTIME_SPACE) {
        r=space_poll(p);
        if(r==COMP_SEG_OK) {
            if(p->boot_phase==BOOT_SALVAGE_RUNTIME_SPACE) {
                p->pipeline.state=COMP_PIPE_IDLE;
                if(comp_wba_recording_product_boot_retry_owned(p))p->reported_state=255u;
                p->boot_phase=BOOT_SALVAGE_READY;
            }
            else if(p->boot_phase==BOOT_SALVAGE_SPACE)p->boot_phase=BOOT_SALVAGE_LEASE;
            else if(p->boot_phase==BOOT_RUNTIME_SPACE) {
                p->pipeline.state=COMP_PIPE_IDLE;p->media_ready=true;p->ready=true;
                if(comp_wba_recording_product_boot_retry_owned(p))p->reported_state=255u;
                p->boot_phase=BOOT_READY;
            } else p->boot_phase=BOOT_LEASE;
        }
        else if(r!=COMP_SEG_PENDING)fail(p,r);
    }
}
bool comp_wba_recording_product_recover_begin(comp_wba_recording_product_t *p)
{
    if(!comp_wba_recording_product_capture_available(p)||
       p->pipeline.state!=COMP_PIPE_FAILED||!p->pipeline.engine_bound||
       p->capture.engine.state!=COMP_CONT_FAULT||p->capture.engine.microphone_active||
       p->capture.engine.encoder_owned||p->pipeline.workspace_bytes||
       p->pipeline.workspace_requested||p->pipeline.discard_exclusive||
       comp_wba_recording_pipeline_consume_result(&p->pipeline)==COMP_SEG_PENDING||
       !p->storage.nor||p->storage.nor->erase_active)return false;
    if(p->storage.poisoned||!p->catalog.mounted) {
        /* Caller holds the full-device lease across preflight and all polls.
         * Retire no uncertain erase and never treat cached ready as WIP/SUS. */
        if(companion_spi_nor_stm32wba_recovery_observe(p->storage.nor)!=COMPANION_SPI_NOR_STM32WBA_OK)return false;
        uint8_t uid[12];memcpy(uid,p->catalog.uid,sizeof(uid));
        uint64_t epoch=p->catalog.epoch;
        p->storage.idle_lookup_read_failed=false;p->storage.poisoned=false;
        comp_segment_result_t r=comp_wba_segment_storage_mount_begin(&p->storage,&p->catalog,uid,epoch);
        if(r!=COMP_SEG_PENDING){p->storage.poisoned=true;return false;}
        p->pipeline.engine_bound=false;p->ready=false;p->media_ready=false;
        p->boot_phase=BOOT_RUNTIME_REMOUNT;return true;
    }
    if(p->pipeline.sealing||p->catalog.phase)return false;
    if(comp_wba_recording_recovery_begin(&p->capture.recovery,&p->storage,
        &p->catalog,p->catalog.page)!=COMP_SEG_PENDING)return false;
    p->pipeline.engine_bound=false;p->ready=false;p->media_ready=false;
    p->boot_phase=BOOT_RUNTIME_RECOVER;return true;
}
static bool inactive_storage_slice(const comp_wba_recording_product_t *p)
{
    return (p->pipeline.state==COMP_PIPE_PREPARING||p->pipeline.state==COMP_PIPE_CLEANUP)&&
        !p->capture.engine.microphone_active&&!p->capture.engine.encoder_owned;
}
bool comp_wba_recording_product_foreground_pending(const comp_wba_recording_product_t *p)
{
    /* Metadata/search/blank reads can progress now. A physical erase still
     * needs time, so keep its normal WFI policy instead of busy-spinning. */
    return p&&p->media_ready&&!p->storage.poisoned&&p->storage.nor&&
        !p->storage.nor->erase_active&&(inactive_storage_slice(p)||
        p->storage.nor->blank_cache.flags==COMP_NOR_BLANK_READING);
}
#if defined(__GNUC__)
__attribute__((noinline)) /* Keep the idle-only256B scratch out of capture's stack frame. */
#endif
void comp_wba_recording_product_warm_blank(comp_wba_recording_product_t *p,bool allowed)
{
    if(!p || !p->storage.nor)return;
    companion_spi_nor_stm32wba_t *n=p->storage.nor;
    companion_nor_blank_cache_t *cache=&n->blank_cache;
    const uint32_t bytes=p->pipeline.config.extent_bytes;
    bool idle=p->pipeline.state==COMP_PIPE_IDLE || p->pipeline.state==COMP_PIPE_FINISHED;
    if(!allowed || !idle || !p->ready || !p->media_ready || p->storage.poisoned ||
       p->catalog.phase || !companion_spi_nor_stm32wba_ready(n) || n->erase_active || p->pipeline.workspace_bytes ||
       p->pipeline.workspace_requested || p->pipeline.discard_exclusive ||
       !comp_wba_recording_product_space_current(p) || p->space.allocation_uncertain ||
       !bytes || p->space.largest_gap<bytes ||
       n->config.target!=COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55 ||
       n->info.jedec_id!=UINT32_C(0xef6018)) {
        if(cache->flags==COMP_NOR_BLANK_READING)cache->flags=0u;
        p->blank_warm.phase=0u;return;
    }
    const uint32_t slots=p->space.largest_gap/bytes;
    uint32_t hint=comp_segment_reserve_rotated_hint(&p->catalog);
    if(p->pipeline.state==COMP_PIPE_FINISHED && p->pipeline.engine_bound) {
        uint32_t end=p->capture.engine.active.extent_offset+p->capture.engine.active.reserved_bytes;
        if(end<=p->catalog.data_bytes)hint=end==p->catalog.data_bytes?0u:end;
    }
    uint32_t chosen=hint/bytes%slots;
    uint32_t candidate=p->space.largest_gap_offset+chosen*bytes;
    /* Predict the existing allocator's capacity-preserving32K preference.
     * This never changes its hint or ownership/search: a different actual
     * candidate simply takes the unchanged full-blank verification path. */
    if(p->catalog.reclaim_block_sectors==8u && bytes>=32768u) {
        for(uint32_t i=0u;i<8u;++i) {
            uint32_t slot=chosen>=i?chosen-i:i;
            if(slot>=slots)continue;
            uint32_t at=p->space.largest_gap_offset+slot*bytes;
            uint32_t padding=(0u-p->storage.data_base-at)&32767u;
            if(padding<=p->space.largest_gap%bytes){candidate=at+padding;break;}
        }
    }
    uint32_t start=p->storage.data_base+candidate;
    if(companion_nor_blank_known(cache,start,bytes)) {
        p->blank_warm.phase=2u;return;
    }
    if(p->blank_warm.phase==2u && p->blank_warm.generation==p->catalog.generation)return;
    if(!p->blank_warm.phase || p->blank_warm.generation!=p->catalog.generation) {
        cache->flags=0u;p->blank_warm.phase=1u;
        p->blank_warm.generation=p->catalog.generation;
    }
    const uint32_t began=n->config.now_ms(n->config.context);
    uint8_t page[COMP_SEGMENT_PAGE_BYTES];
    for(unsigned step=0u;step<16u;++step) {
        if(cache->flags!=COMP_NOR_BLANK_READING) {
            if(!companion_nor_blank_begin(cache,n->info.size_bytes,start,bytes)) {
                p->blank_warm.phase=2u;return;
            }
        }
        bool released=false;
        companion_spi_nor_stm32wba_status_t result=companion_spi_nor_stm32wba_read_transient(
            n,cache->base+cache->read_bytes,page,sizeof(page),&released);
        if(result!=COMPANION_SPI_NOR_STM32WBA_OK) {
            cache->flags=0u;p->blank_warm.phase=2u;
            if(result!=COMPANION_SPI_NOR_STM32WBA_PENDING &&
               (!released || n->config.now_ms(n->config.context)-began>=3u)) {
                p->storage.poisoned=true;p->storage.idle_lookup_read_failed=true;
            }
            return;
        }
        if(cache->flags==COMP_NOR_BLANK_KNOWN){p->blank_warm.phase=2u;return;}
        if(cache->flags!=COMP_NOR_BLANK_READING){p->blank_warm.phase=2u;return;}
        if(n->config.now_ms(n->config.context)-began>=1u)return;
    }
}
void comp_wba_recording_product_poll(comp_wba_recording_product_t *p)
{
    if(!p||p->boot_phase==BOOT_UNBOUND||p->boot_phase==BOOT_FAILED)return;
    if(p->boot_phase<BOOT_LEASE||p->boot_phase==BOOT_BOOT_REMOUNT||p->boot_phase==BOOT_RUNTIME_REMOUNT||p->boot_phase==BOOT_RUNTIME_RECOVER||
       p->boot_phase==BOOT_RUNTIME_SPACE||p->boot_phase==BOOT_SALVAGE_SPACE||
       p->boot_phase==BOOT_SALVAGE_RUNTIME_SPACE){boot_poll(p);return;}
    if(!p->ready&&p->boot_phase!=BOOT_SALVAGE_READY)return;
    /* CDS3 owns the catalog worker until its durable intent has finished.
     * The BLE foreground continues that worker; capacity refresh follows it. */
    if(p->pipeline.discard_exclusive)return;
    bool idle=p->pipeline.state==COMP_PIPE_IDLE||p->pipeline.state==COMP_PIPE_FINISHED;
    /* A peer's phase-free directory or sealed-audio read may fail after capacity was
     * cached; the cached walk must not hide the poisoned adapter forever.
     * Radio/other owners release before the foreground remount proceeds. */
    if(idle&&p->storage.poisoned&&p->storage.idle_lookup_read_failed&&
       (p->boot_phase==BOOT_READY||p->boot_phase==BOOT_SALVAGE_READY)&&
       !p->pipeline.workspace_bytes&&!p->pipeline.workspace_requested&&!p->pipeline.discard_exclusive&&
       !p->pipeline.sealing&&!p->catalog.phase&&p->storage.nor&&!p->storage.nor->erase_active&&
       comp_wba_recording_pipeline_consume_result(&p->pipeline)!=COMP_SEG_PENDING&&
       (!p->pipeline.engine_bound||(!p->capture.engine.microphone_active&&!p->capture.engine.encoder_owned))) {
        p->last_fault=COMP_WBA_RECORDING_FAULT_STORAGE_IO;
        p->ready=false;p->media_ready=false;p->boot_phase=BOOT_FAILED;p->reported_state=BOOT_RETRY_IDLE_ARM0;
        return;
    }
    if(idle&&comp_wba_recording_pipeline_consume_result(&p->pipeline)!=COMP_SEG_PENDING) {
        comp_segment_result_t r=space_poll(p);
        if(r!=COMP_SEG_OK&&r!=COMP_SEG_PENDING) {
            /* A read-only capacity walk can fail while no capture or writer
             * exists. Its catalogue RAM is stale after IO failure; use the
             * same bounded exclusive re-mount as an initial root read, never
             * format or retry a write, active lease or uncertain owner. */
            bool retry=r==COMP_SEG_IO_ERROR&&p->storage.poisoned&&
                (p->boot_phase==BOOT_READY||p->boot_phase==BOOT_SALVAGE_READY)&&
                !p->pipeline.workspace_bytes&&
                !p->pipeline.workspace_requested&&!p->pipeline.discard_exclusive&&
                !p->pipeline.sealing&&!p->catalog.phase&&p->storage.nor&&
                !p->storage.nor->erase_active&&
                (!p->pipeline.engine_bound||(!p->capture.engine.microphone_active&&
                                             !p->capture.engine.encoder_owned));
            fail(p,r);
            if(retry){p->media_ready=false;p->reported_state=BOOT_RETRY_IDLE_ARM0;}
        }
    } else {
        /* A 270KiB blank walk has over1000 pages. Idle preparation/cleanup
         * must not wait one foreground round per page. Bound each slice by
         * both sixteen existing steps and1ms; active/paused/draining capture
         * retains exactly one step and its original real-time scheduling. */
        uint8_t steps=1u;uint32_t began=0u;
        if(inactive_storage_slice(p)){steps=16u;began=p->pipeline.config.now_ms(p->pipeline.config.context);}
        do {(void)comp_wba_recording_pipeline_poll(&p->pipeline);}
        while(--steps&&inactive_storage_slice(p)&&
            (uint32_t)(p->pipeline.config.now_ms(p->pipeline.config.context)-began)<1u);
        /* A failed pre-commit consume lookup is still read-only. Preserve the
         * error for its radio owner; the foreground retry waits until that
         * owner releases it, then uses the existing bounded remount. */
        if(comp_wba_recording_pipeline_consume_idle_read_failed(&p->pipeline)&&
           p->storage.poisoned&&(p->boot_phase==BOOT_READY||p->boot_phase==BOOT_SALVAGE_READY)&&
           !p->pipeline.workspace_bytes&&!p->pipeline.workspace_requested&&!p->pipeline.discard_exclusive&&
           !p->pipeline.sealing&&!p->catalog.phase&&p->storage.nor&&!p->storage.nor->erase_active&&
           (!p->pipeline.engine_bound||(!p->capture.engine.microphone_active&&!p->capture.engine.encoder_owned))) {
            p->last_fault=COMP_WBA_RECORDING_FAULT_STORAGE_IO;
            p->ready=false;p->media_ready=false;p->boot_phase=BOOT_FAILED;
            p->reported_state=BOOT_RETRY_IDLE_ARM0;
        }
        if(p->pipeline.state==COMP_PIPE_FAILED&&!p->last_fault)p->last_fault=
            p->pipeline.failure==COMP_SEG_FULL?COMP_WBA_RECORDING_FAULT_STORAGE_FULL:COMP_WBA_RECORDING_FAULT_STORAGE_IO;
        if(p->pipeline.engine_bound&&p->capture.engine.stop_reason==COMP_CONT_STOP_FULL)
            p->last_fault=COMP_WBA_RECORDING_FAULT_STORAGE_FULL;
    }
    report(p);
    /* Report the rejected START before returning empty capacity failure to
     * idle storage access. Nested report callbacks may begin another owner;
     * never retire its recovery/workspace or a real failed audio extent. */
    if(comp_wba_recording_product_capture_available(p))
        (void)comp_wba_recording_pipeline_release_empty_full(&p->pipeline);
}
bool comp_wba_recording_product_recovering(const comp_wba_recording_product_t *p)
{
    return p&&(p->boot_phase==BOOT_RUNTIME_REMOUNT||p->boot_phase==BOOT_RUNTIME_RECOVER||
        p->boot_phase==BOOT_RUNTIME_SPACE||p->boot_phase==BOOT_SALVAGE_RUNTIME_SPACE||
        comp_wba_recording_product_boot_retry_owned(p));
}
bool comp_wba_recording_product_boot_retry_pending(const comp_wba_recording_product_t *p)
{return p&&p->boot_phase==BOOT_FAILED&&(p->reported_state==BOOT_RETRY_ARM0||p->reported_state==BOOT_RETRY_ARM1||
    p->reported_state==BOOT_RETRY_IDLE_ARM0||p->reported_state==BOOT_RETRY_IDLE_ARM1);}
bool comp_wba_recording_product_boot_retry_owned(const comp_wba_recording_product_t *p)
{return p&&(p->reported_state==BOOT_RETRY_OWN1||p->reported_state==BOOT_RETRY_OWN2||
    p->reported_state==BOOT_RETRY_IDLE_OWN1||p->reported_state==BOOT_RETRY_IDLE_OWN2);}
bool comp_wba_recording_product_boot_retry(comp_wba_recording_product_t *p,uint32_t now_ms)
{
    if(!comp_wba_recording_product_boot_retry_pending(p)||!p->storage.nor||p->storage.nor->erase_active)return false;
    bool idle=p->reported_state==BOOT_RETRY_IDLE_ARM0||p->reported_state==BOOT_RETRY_IDLE_ARM1;
    bool first=p->reported_state==BOOT_RETRY_ARM0||p->reported_state==BOOT_RETRY_IDLE_ARM0;
    if(!first&&(int32_t)(now_ms-p->boot.boot_cursor)<0)return false;
    p->reported_state=idle?(first?BOOT_RETRY_IDLE_ARM1:BOOT_RETRY_IDLE_EXHAUSTED):(first?BOOT_RETRY_ARM1:BOOT_RETRY_ARM2);
    p->boot.boot_cursor=now_ms+1000u;
    if(companion_spi_nor_stm32wba_recovery_observe(p->storage.nor)!=COMPANION_SPI_NOR_STM32WBA_OK)return false;
    uint8_t uid[12];memcpy(uid,p->catalog.uid,sizeof(uid));uint64_t epoch=p->catalog.epoch;
    p->storage.idle_lookup_read_failed=false;p->storage.poisoned=false;
    comp_segment_result_t r=comp_wba_segment_storage_mount_begin(&p->storage,&p->catalog,uid,epoch);
    if(r!=COMP_SEG_PENDING){p->storage.poisoned=true;p->reported_state=255u;return false;}
    p->reported_state=idle?(first?BOOT_RETRY_IDLE_OWN1:BOOT_RETRY_IDLE_OWN2):
                           (first?BOOT_RETRY_OWN1:BOOT_RETRY_OWN2);
    if(idle)p->pipeline.engine_bound=false;
    p->boot_phase=idle?BOOT_RUNTIME_REMOUNT:BOOT_BOOT_REMOUNT;return true;
}
bool comp_wba_recording_product_idle_retry_exhausted(const comp_wba_recording_product_t *p)
{return p&&p->boot_phase==BOOT_FAILED&&p->reported_state==BOOT_RETRY_IDLE_EXHAUSTED;}
bool comp_wba_recording_product_retry_idle_explicit(comp_wba_recording_product_t *p,uint32_t now_ms)
{
    /* Only an exhausted, previously mounted read-only idle walk can be
     * re-armed by a new user START. Corrupt roots and uncertain writers do
     * not carry this sentinel and must never be reformatted or guessed. */
    if(!comp_wba_recording_product_idle_retry_exhausted(p)||
       !p->storage.poisoned||!p->storage.nor||p->storage.nor->erase_active||
       p->pipeline.workspace_bytes||p->pipeline.workspace_requested||p->pipeline.discard_exclusive||
       p->pipeline.sealing||p->catalog.phase||
       comp_wba_recording_pipeline_consume_result(&p->pipeline)==COMP_SEG_PENDING)return false;
    p->reported_state=BOOT_RETRY_IDLE_ARM0;
    return comp_wba_recording_product_boot_retry(p,now_ms);
}
void comp_wba_recording_product_lease_result(comp_wba_recording_product_t *p,bool ok)
{
    if(!p||(p->boot_phase!=BOOT_LEASE&&p->boot_phase!=BOOT_SALVAGE_LEASE)||
       !p->space.valid||p->space.generation!=p->catalog.generation)return;
    if(!ok){fail(p,COMP_SEG_BAD_STATE);return;}
    if(comp_wba_recording_product_boot_retry_owned(p))p->reported_state=255u;
    if(p->boot_phase==BOOT_SALVAGE_LEASE)p->boot_phase=BOOT_SALVAGE_READY;
    else {p->ready=true;p->boot_phase=BOOT_READY;}
}
bool comp_wba_recording_product_prepare(comp_wba_recording_product_t *p,
    uint64_t session,uint8_t mode,uint32_t started,uint32_t token)
{return comp_wba_recording_product_prepare_timeline(p,session,mode,started,token,false);}
bool comp_wba_recording_product_prepare_timeline(comp_wba_recording_product_t *p,
    uint64_t session,uint8_t mode,uint32_t started,uint32_t token,bool timeline)
{
    if(!comp_wba_recording_product_capture_prepare_available(p))return false;
    /* A known free gap avoids repeatedly starting inside old owners. This
     * only chooses the first candidate: the allocator still checks every
     * occupied extent and restarts on a changed catalog generation. */
    const bool gap=comp_wba_recording_product_space_current(p)&&!p->space.allocation_uncertain&&
        p->space.largest_gap>=p->pipeline.config.extent_bytes;
    const uint32_t offset=gap?p->space.largest_gap_offset:0u;
    const uint32_t slots=gap?p->space.largest_gap/p->pipeline.config.extent_bytes:0u;
    if(p->ready)p->last_fault=COMP_WBA_RECORDING_FAULT_NONE;
    comp_segment_result_t r=comp_wba_recording_pipeline_begin_timeline(&p->pipeline,session,mode,started,token,timeline);
    if(r!=COMP_SEG_PENDING){p->last_fault=r==COMP_SEG_FULL?COMP_WBA_RECORDING_FAULT_STORAGE_FULL:COMP_WBA_RECORDING_FAULT_STORAGE_IO;return false;}
    if(gap)(void)comp_segment_reserve_set_search_hint(&p->pipeline.reserve,
        offset+(p->pipeline.reserve.hint/p->pipeline.config.extent_bytes%slots)*p->pipeline.config.extent_bytes);
    if(p->storage.nor && p->storage.nor->blank_cache.flags==COMP_NOR_BLANK_READING)
        p->storage.nor->blank_cache.flags=0u;
    p->blank_warm.phase=0u;
    p->reported_state=255u;report(p);return true;
}
bool comp_wba_recording_product_ready(const comp_wba_recording_product_t *p,uint32_t token)
{return comp_wba_recording_product_capture_available(p)&&token&&token==p->pipeline.token&&p->pipeline.state==COMP_PIPE_READY;}
bool comp_wba_recording_product_prepare_bookmarked(comp_wba_recording_product_t *p,
    uint64_t session,uint8_t mode,uint32_t started,uint32_t token)
{
    if(!comp_wba_recording_product_prepare_timeline(p,session,mode,started,token,true))return false;
    p->pipeline.pause_timeline=COMP_CONT_TIMELINE_SOURCE_BOUNDARY;return true;
}
bool comp_wba_recording_product_prepare_audio_profile(comp_wba_recording_product_t *p,
    uint64_t session,uint8_t mode,uint32_t started,uint32_t token)
{
    if(!p || !p->pipeline.config.audio_profile ||
       comp_recording_required_capacity_profile(p->pipeline.config.segment_frames,true,true)>
           comp_segment_audio_capacity(p->pipeline.config.extent_bytes) ||
       !comp_wba_recording_product_prepare_bookmarked(p,session,mode,started,token))return false;
    p->pipeline.pause_timeline=COMP_CONT_TIMELINE_AUDIO_PROFILE;return true;
}
bool comp_wba_recording_product_bookmark(comp_wba_recording_product_t *p,uint32_t token,uint32_t request)
{
    return comp_wba_recording_product_capture_available(p)&&p->pipeline.engine_bound&&!p->pipeline.stop_requested&&
        p->pipeline.state==COMP_PIPE_RECORDING&&comp_cont_recording_bookmark(&p->capture.engine,token,request);
}
comp_segment_result_t comp_wba_recording_product_bookmark_result(const comp_wba_recording_product_t *p,uint32_t token,uint32_t request)
{
    if(!comp_wba_recording_product_capture_available(p)||!p->pipeline.engine_bound)return COMP_SEG_BAD_STATE;
    return comp_cont_recording_bookmark_result(&p->capture.engine,token,request);
}
bool comp_wba_recording_product_control(comp_wba_recording_product_t *p,bool start,uint32_t token)
{
    if(!comp_wba_recording_product_capture_available(p))return false;
    bool ok=start?comp_wba_recording_pipeline_start(&p->pipeline,token):comp_wba_recording_pipeline_stop(&p->pipeline,token);
    if(ok)report(p);
    return ok;
}
bool comp_wba_recording_product_stop_reason(comp_wba_recording_product_t *p,uint32_t token,comp_cont_stop_t why)
{
    if(!comp_wba_recording_product_capture_available(p))return false;
    bool ok=comp_wba_recording_pipeline_stop_reason(&p->pipeline,token,why);
    if(ok)report(p);
    return ok;
}
bool comp_wba_recording_product_pcm(comp_wba_recording_product_t *p,const int16_t *pcm,size_t count,uint32_t rate)
{
    if(!comp_wba_recording_product_capture_available(p)||rate!=16000u)return false;
    if(comp_cont_recording_pcm(&p->capture.engine,pcm,count))return true;
    if(p->capture.engine.stats.overflows)p->last_fault=COMP_WBA_RECORDING_FAULT_PCM_OVERFLOW;
    return false;
}
void comp_wba_recording_product_fault(comp_wba_recording_product_t *p,uint8_t reason)
{
    if(!p||!p->media_ready||!p->pipeline.engine_bound||!reason)return;
    /* Fault polling may observe the same broken capture repeatedly. Preserve
     * the first cause and leave bounded stop retry to the pipeline owner. */
    if(p->pipeline.state==COMP_PIPE_FAILED&&p->capture.engine.state==COMP_CONT_FAULT) {
        if(!p->last_fault)p->last_fault=reason;
        return;
    }
    p->last_fault=reason;comp_cont_recording_fault(&p->capture.engine,COMP_SEG_IO_ERROR);
    p->pipeline.state=COMP_PIPE_FAILED;p->pipeline.failure=COMP_SEG_IO_ERROR;report(p);
}
bool comp_wba_recording_product_workspace(comp_wba_recording_product_t *p,uint32_t bytes,uint32_t *physical)
{
    if(!p||!p->media_ready||!physical)return false;
    *physical=0u;
    /* A degraded reader may finish/release an already-restored boot lease;
     * it cannot start a new firmware/resource download over uncertain audio. */
    if(p->boot_phase==BOOT_SALVAGE_READY&&bytes&&bytes!=p->pipeline.workspace_bytes)return false;
    /* An existing durable tail claim is replayed exactly, even while its
     * capacity view is being refreshed. Zero always reconciles release. */
    if(!bytes||bytes==p->pipeline.workspace_bytes)
        return comp_wba_recording_pipeline_workspace(&p->pipeline,bytes,physical)==COMP_SEG_OK;
    /* Releasing our own tail changes the free-space denominator, not the
     * immutable extent inventory. BEGIN may immediately claim a new size
     * before the foreground capacity view is rebuilt. Require the completed
     * catalogue generation here; the pipeline rechecks generation, active
     * consumers, NOR state and highest extent against the requested boundary.
     * Public free-space reporting still requires space_current(). */
    if(!comp_wba_recording_product_catalog_current(p))return false;
    return comp_wba_recording_pipeline_workspace_snapshot(&p->pipeline,bytes,
        p->space.generation,p->space.highest_end,physical)==COMP_SEG_OK;
}
bool comp_wba_recording_product_update_workspace(comp_wba_recording_product_t *p,
    uint32_t bytes,uint32_t *physical)
{
    if(!p||!physical)return false;
    if(comp_wba_recording_product_salvaging(p)&&bytes&&bytes!=p->pipeline.workspace_bytes) {
        *physical=0u;
        /* The unresolved WRITING extent remains an owner, never a reusable
         * hole. All sealed microphone originals still require ordinary sync.
         * Allocate only a current, unambiguous tail strictly beyond every
         * retained extent; ordinary WUS2 and signature checks still apply. */
        if(!comp_wba_recording_product_update_available(p))return false;
        return comp_wba_recording_pipeline_workspace_snapshot(&p->pipeline,bytes,
            p->space.generation,p->space.highest_end,physical)==COMP_SEG_OK;
    }
    /* Prefer the existing tail path. If a retained owner occupies that tail,
     * use a whole free gap from the completed generation-qualified walk.
     * This claims space only; no audio/catalogue is moved or consumed. */
    if(bytes&&!p->pipeline.workspace_bytes&&comp_wba_recording_product_catalog_current(p)&&
       !p->space.allocation_uncertain&&bytes%4096u==0u&&bytes<=p->space.largest_gap&&
       p->space.highest_end>p->catalog.data_bytes-bytes)
        return comp_wba_recording_pipeline_workspace_at_snapshot(&p->pipeline,bytes,
            p->space.generation,p->space.largest_gap_offset,physical)==COMP_SEG_OK;
    return comp_wba_recording_product_workspace(p,bytes,physical);
}
bool comp_wba_recording_product_readable(const comp_wba_recording_product_t *p)
{
    return p&&p->media_ready&&((p->ready&&p->boot_phase==BOOT_READY)||
        p->boot_phase==BOOT_SALVAGE_READY);
}
bool comp_wba_recording_product_capture_available(const comp_wba_recording_product_t *p)
{
    return p&&p->media_ready&&((p->ready&&p->boot_phase==BOOT_READY)||
        p->boot_phase==BOOT_SALVAGE_READY);
}
bool comp_wba_recording_product_salvaging(const comp_wba_recording_product_t *p)
{return p&&p->boot_phase==BOOT_SALVAGE_READY;}
bool comp_wba_recording_product_tail_retained(const comp_wba_recording_product_t *p)
{return p&&p->retained_tail;}
bool comp_wba_recording_product_update_available(const comp_wba_recording_product_t *p)
{
    if(!comp_wba_recording_product_capture_available(p))return false;
    if(p->ready)return true;
    if(!p->catalog.mounted||p->storage.poisoned||!p->storage.nor)return false;
    /* An already-restored WUS2 claim was checked against all owners before
     * this point. Preserve its continuation while the free-space view is
     * cooperatively rebuilt for the smaller arena. */
    if(p->pipeline.workspace_bytes)return true;
    return comp_wba_recording_product_space_current(p)&&!p->space.allocation_uncertain&&
        !p->space.microphone_sealed_owned&&!p->storage.nor->erase_active;
}
bool comp_wba_recording_product_capture_prepare_available(const comp_wba_recording_product_t *p)
{
    if(!comp_wba_recording_product_capture_available(p))return false;
    return !comp_wba_recording_product_salvaging(p)||
        (comp_wba_recording_product_space_current(p)&&!p->space.allocation_uncertain&&
         p->space.allocatable_segments&&p->catalog.mounted&&!p->storage.poisoned&&
         p->storage.nor&&!p->storage.nor->erase_active);
}
bool comp_wba_recording_product_capability(const comp_wba_recording_product_t *p,uint8_t out[32])
{
    if(!out||!comp_wba_recording_product_readable(p))return false;
    memset(out,0,32u);memcpy(out,"CRV2",4u);comp_rec_put16(out+4u,2u);comp_rec_put16(out+6u,32u);
    /* bit256: explicit codec delay/source end. Older Type's strict mask
     * rejects this writer during setup, before START/partial consumption;
     * install its matching reader before enabling this firmware. */
    /* bit512 means this image may create schema5 originals. Old strict
     * readers refuse setup before START/consume; install matching Type first. */
    /* Wide-index capability: old strict hosts refuse setup before consuming;
     * matching updated hosts must be deployed before this firmware. */
    comp_rec_put32(out+8u,255u|256u|(p->pipeline.config.audio_profile?512u:0u)|COMP_REC_V2_CAP_WIDE_SEGMENT_INDEX);comp_rec_put64(out+12u,p->catalog.epoch);
    comp_rec_put16(out+20u,COMP_SEGMENT_CAPACITY);comp_rec_put16(out+22u,COMP_REC_V2_MAX_SEGMENTS);
    comp_rec_put16(out+24u,COMP_WBA_RECORDING_TRANSFER_VALUE_BYTES);comp_rec_put32(out+28u,comp_wba_recording_crc32(0u,out,28u));return true;
}

bool comp_wba_recording_product_set_paused(comp_wba_recording_product_t *product,uint32_t token,bool paused)
{
    if(!comp_wba_recording_product_capture_available(product))return false;
    comp_wba_recording_pipeline_t *p=&product->pipeline;
    comp_cont_recording_t *e=p->config.recording;
    if(!p->engine_bound || !p->pause_timeline || p->stop_requested ||
       p->state!=COMP_PIPE_RECORDING || p->token!=token ||
       e->command_sequence>=UINT32_MAX-1u)return false;
    if((paused&&e->state==COMP_CONT_PAUSED)||(!paused&&e->state==COMP_CONT_RUNNING))return true;
    uint32_t sequence=e->command_sequence+1u;
    return paused && e->state==COMP_CONT_RUNNING?comp_wba_recording_pipeline_pause(p,p->token,sequence):
        !paused && e->state==COMP_CONT_PAUSED?comp_wba_recording_pipeline_resume(p,p->token,sequence):false;
}
bool comp_wba_recording_product_pause_resume(comp_wba_recording_product_t *product,uint32_t token)
{
    if(!product)return false;
    const comp_cont_state_t state=product->capture.engine.state;
    if(state!=COMP_CONT_RUNNING && state!=COMP_CONT_PAUSED)return false;
    return comp_wba_recording_product_set_paused(product,token,state==COMP_CONT_RUNNING);
}

