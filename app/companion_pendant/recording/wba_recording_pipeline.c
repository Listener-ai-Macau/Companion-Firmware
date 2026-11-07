#include "companion_cpu_stage.h"
#include "wba_recording_pipeline.h"
#include "wba_recording_crc.h"

enum {FUTURE_NONE=0,FUTURE_RESERVE,FUTURE_PROVENANCE,FUTURE_READY,FUTURE_TAKEN,FUTURE_FULL,FUTURE_CANCEL};
enum {CONSUME_NONE=0,CONSUME_FIND,CONSUME_RECEIPT,CONSUME_ACK,CONSUME_RECLAIM_BEGIN,CONSUME_RECLAIM,CONSUME_DONE,CONSUME_FAILED,CONSUME_IDLE_READ_FAILED};

static bool same_proof(const comp_rec_v2_descriptor_t *a,const comp_rec_v2_descriptor_t *b)
{
    uint8_t x[112],y[112];comp_rec_v2_descriptor_t normalized=*a;
    normalized.sync_state=2u;
    if(!comp_rec_v2_encode(&normalized,x,sizeof(x)))return false;
    normalized=*b;normalized.sync_state=2u;
    return comp_rec_v2_encode(&normalized,y,sizeof(y))&&!memcmp(x,y,sizeof(x));
}
static bool wire_proof(const comp_rec_v2_descriptor_t *a,const comp_rec_v2_descriptor_t *b)
{
    return a->recording_id==b->recording_id&&a->format_epoch==b->format_epoch&&a->session_id==b->session_id&&
        a->segment_index==b->segment_index&&a->encoded_length==b->encoded_length&&
        !memcmp(a->sha256,b->sha256,32u)&&!memcmp(a->device_uid,b->device_uid,12u);
}
static bool queued_proof(const comp_wba_recording_pipeline_t *p,const comp_rec_v2_descriptor_t *actual)
{
    /* CRA2 has no sealed/sample fields. The zero flags in its validated,
     * limited input become full SEALED metadata only after local lookup.
     * Direct112B proofs are validated SEALED before they can be queued. */
    return (p->consume.descriptor.flags&COMP_REC_V2_SEALED)?
        same_proof(actual,&p->consume.descriptor):wire_proof(actual,&p->consume.descriptor);
}
static comp_segment_result_t failed(comp_wba_recording_pipeline_t *p,comp_segment_result_t r)
{
    p->failure=r;p->state=COMP_PIPE_FAILED;
    if(p->engine_bound && p->consume_phase!=CONSUME_IDLE_READ_FAILED)
        comp_cont_recording_fault(p->config.recording,r);
    return r;
}
static bool consumer_active(const comp_wba_recording_pipeline_t *p)
{return p->consume_phase>=CONSUME_FIND&&p->consume_phase<=CONSUME_RECLAIM;}
bool comp_wba_recording_pipeline_release_empty_full(comp_wba_recording_pipeline_t *p)
{
    /* Expected capacity rejection before the first extent/PCM/encoder owner.
     * The product must publish ERROR_RECOVERY for the rejected START first.
     * Only this empty terminal can return to IDLE: no media operation, erase,
     * acknowledgement, recovery scan or automatic recording start occurs. */
    if(!p||p->state!=COMP_PIPE_FAILED||p->failure!=COMP_SEG_FULL||p->engine_bound||
       p->future_phase!=FUTURE_FULL||p->future.descriptor.recording_id||
       !p->config.recording||p->config.recording->microphone_active||
       p->config.recording->encoder_owned||!p->config.catalog||!p->config.catalog->mounted||p->config.catalog->phase||
       !p->config.storage||p->config.storage->poisoned||!p->config.storage->nor||
       p->config.storage->nor->erase_active||p->sealing||consumer_active(p)||
       p->workspace_bytes||p->workspace_requested)return false;
    p->state=COMP_PIPE_IDLE;return true;
}

static bool page_available(const comp_wba_recording_pipeline_t *p,bool transfer)
{
    return p&&!p->discard_exclusive&&p->config.catalog&&
        (!p->config.catalog->phase||(transfer&&p->consume_phase==CONSUME_RECLAIM&&
         p->config.catalog->pending==&p->consume&&comp_segment_catalog_transfer_readable(p->config.catalog)))&&!p->sealing&&
        p->future_phase!=FUTURE_PROVENANCE&&p->future_phase!=FUTURE_CANCEL&&
        !(p->core_cancel_started&&p->config.recording->state==COMP_CONT_CANCELING)&&
        p->state!=COMP_PIPE_PREPARING&&p->state!=COMP_PIPE_FAILED;
}
bool comp_wba_recording_pipeline_page_available(const comp_wba_recording_pipeline_t *p)
{return page_available(p,false);}
bool comp_wba_recording_pipeline_transfer_page_available(const comp_wba_recording_pipeline_t *p)
{return page_available(p,true);}
bool comp_wba_recording_pipeline_storage_busy(const comp_wba_recording_pipeline_t *p)
{
    return p&&(p->discard_exclusive||p->workspace_bytes||p->workspace_requested||consumer_active(p)||p->sealing||p->config.catalog->phase||
        p->state==COMP_PIPE_PREPARING||p->state==COMP_PIPE_READY||p->state==COMP_PIPE_RECORDING||
        p->state==COMP_PIPE_STOPPING||p->state==COMP_PIPE_CLEANUP||p->state==COMP_PIPE_FAILED);
}
bool comp_wba_recording_pipeline_discard_acquire(comp_wba_recording_pipeline_t *p)
{
    if(!p||!p->config.catalog||!p->config.storage||!p->config.storage->nor||!p->config.recording||
       !p->config.catalog->mounted||p->config.storage->poisoned||p->config.storage->nor->erase_active||
       p->config.recording->microphone_active||p->config.recording->encoder_owned||
       (p->state!=COMP_PIPE_IDLE&&p->state!=COMP_PIPE_FINISHED)||
       comp_wba_recording_pipeline_storage_busy(p))return false;
    p->discard_exclusive=true;return true;
}
bool comp_wba_recording_pipeline_discard_release(comp_wba_recording_pipeline_t *p)
{
    if(p&&p->discard_exclusive&&p->config.catalog&&p->config.storage&&p->config.storage->nor&&
       p->config.catalog->mounted&&!p->config.catalog->phase&&!p->config.storage->poisoned&&
       !p->config.storage->nor->erase_active){p->discard_exclusive=false;return true;}
    return false;
}
static comp_segment_result_t start_future(comp_wba_recording_pipeline_t *p,const comp_segment_entry_t *active)
{
    if(p->future_phase!=FUTURE_TAKEN&&p->future_phase!=FUTURE_FULL&&p->future_phase!=FUTURE_NONE)return COMP_SEG_BAD_STATE;
    uint32_t frames=p->config.recording->active_frame_limit;
    if(active->descriptor.segment_index==COMP_REC_V2_INDEX_EXCLUSIVE_MAX-1u||
       active->descriptor.sample_offset>UINT64_MAX-(uint64_t)frames*320u) {
        p->future_phase=FUTURE_FULL;p->full_generation=p->config.catalog->generation;return COMP_SEG_FULL;
    }
    memset(&p->future,0,sizeof(p->future));memset(&p->future_writer,0,sizeof(p->future_writer));
    memset(&p->reserve,0,sizeof(p->reserve));p->future.state=COMP_SEG_WRITING;
    comp_rec_v2_descriptor_t *d=&p->future.descriptor;
    const comp_rec_v2_descriptor_t *old=&active->descriptor;
    d->format_epoch=old->format_epoch;d->session_id=old->session_id;d->codec=3u;d->source_mode=old->source_mode;
    memcpy(d->device_uid,old->device_uid,12u);p->future.started_unix_s=active->started_unix_s;
    d->segment_index=old->segment_index+1u;
    d->sample_offset=old->sample_offset+(uint64_t)frames*320u;
    uint32_t end=active->extent_offset+active->reserved_bytes;
    uint32_t hint=end==p->config.catalog->data_bytes?0u:end;
    comp_segment_result_t r=comp_segment_reserve_begin(&p->reserve,p->config.catalog,&p->future,p->config.extent_bytes,hint);
    if(r==COMP_SEG_PENDING)p->future_phase=FUTURE_RESERVE;
    return r;
}
static comp_segment_result_t future_progress(comp_wba_recording_pipeline_t *p)
{
    comp_segment_result_t r;
    if(p->future_phase==FUTURE_CANCEL) {
        r=comp_wba_segment_storage_cancel_poll(p->config.storage,&p->future_writer);
        if(r==COMP_SEG_OK)p->future_phase=FUTURE_NONE;
        return r;
    }
    if(p->future_phase==FUTURE_RESERVE) {
        r=comp_wba_segment_storage_reserve_poll(p->config.storage,&p->reserve);
        if(r==COMP_SEG_FULL&&!p->future.descriptor.recording_id) {
            p->future_phase=FUTURE_FULL;p->full_generation=p->config.catalog->generation;return COMP_SEG_FULL;
        }
        if(r!=COMP_SEG_OK)return r;
        comp_segment_entry_t *owned=NULL;
        if(!comp_segment_reserve_take(&p->reserve,&owned)||owned!=&p->future)return COMP_SEG_BAD_STATE;
        comp_segment_audio_port_t port=comp_wba_segment_storage_writer_audio_port(p->config.storage);
        r=comp_segment_audio_prepare_begin(&p->future_writer,&port,&p->future,p->config.catalog->data_base,p->config.catalog->page);
        if(r==COMP_SEG_PENDING)p->future_phase=FUTURE_PROVENANCE;
        return r;
    }
    if(p->future_phase==FUTURE_PROVENANCE) {
        r=comp_segment_audio_poll(&p->future_writer);
        if(r==COMP_SEG_OK)p->future_phase=FUTURE_READY;
        return r;
    }
    return p->future_phase==FUTURE_FULL?COMP_SEG_FULL:COMP_SEG_OK;
}
static comp_segment_result_t consume_failed(comp_wba_recording_pipeline_t *p,comp_segment_result_t r)
{
    /* A gate failure before the catalog can retire its transaction is an
     * uncertain media owner, not a harmless rejected proof. Stop the pipeline
     * so capture cannot run against a permanently blocked catalog. */
    const bool retained=p->config.catalog->phase && p->config.catalog->pending==&p->consume;
    const bool idle_read=r==COMP_SEG_IO_ERROR&&!retained&&!p->config.catalog->phase&&
        (p->state==COMP_PIPE_IDLE||p->state==COMP_PIPE_FINISHED)&&
        (p->consume_phase==CONSUME_FIND||p->consume_phase==CONSUME_RECEIPT);
    p->consume_result=r;p->consume_phase=idle_read?CONSUME_IDLE_READ_FAILED:CONSUME_FAILED;
    return (retained||r==COMP_SEG_IO_ERROR||r==COMP_SEG_CORRUPT)?r:COMP_SEG_OK;
}
static comp_segment_result_t consume_progress(comp_wba_recording_pipeline_t *p)
{
    comp_segment_catalog_t *c=p->config.catalog;comp_segment_result_t r;
    if(p->consume_phase==CONSUME_FIND) {
        if(c->phase)return COMP_SEG_PENDING;
        if(p->consume_scan==64u){p->consume_scan=0u;p->consume_phase=CONSUME_RECEIPT;return COMP_SEG_PENDING;}
        comp_segment_entry_t entry;
        const bool hinted=(p->consume_scan&128u)!=0u;
        const uint8_t slot=(uint8_t)(p->consume_scan&63u);
        r=comp_wba_segment_storage_entry(p->config.storage,c,slot,&entry);
        if(r==COMP_SEG_PENDING)return r;
        p->consume_scan=hinted?0u:(uint8_t)(slot+1u);
        if(r==COMP_SEG_NOT_FOUND)return COMP_SEG_PENDING;
        if(r!=COMP_SEG_OK)return consume_failed(p,r);
        if(entry.descriptor.recording_id!=p->consume.descriptor.recording_id)return COMP_SEG_PENDING;
        if((entry.state!=COMP_SEG_UNSYNCED&&entry.state!=COMP_SEG_ACKED)||
           !queued_proof(p,&entry.descriptor))return consume_failed(p,COMP_SEG_BAD_ARGUMENT);
        p->consume_scan=(uint8_t)(slot+1u);
        p->consume=entry;p->consume.state=COMP_SEG_ACKED;p->consume.descriptor.sync_state=2u;
#if COMPANION_WBA_RECLAIM_TIMING
        p->consume_timing_ms[1]=p->config.now_ms(p->config.context);
#endif
        /* Begin is pure; this slice already used its one catalog read. */
        r=comp_segment_catalog_ack_at_begin(c,&p->consume,(uint8_t)(p->consume_scan-1u));
        if(r==COMP_SEG_PENDING)p->consume_phase=CONSUME_ACK;
        else return consume_failed(p,r);
        return r;
    }
    if(p->consume_phase==CONSUME_RECEIPT) {
        if(c->phase)return COMP_SEG_PENDING;
        if(p->consume_scan==COMP_SEGMENT_RECEIPT_CAPACITY)return consume_failed(p,COMP_SEG_NOT_FOUND);
        comp_segment_entry_t receipt;
        r=comp_wba_segment_storage_receipt(p->config.storage,c,p->consume_scan,&receipt);
        if(r==COMP_SEG_PENDING)return r;
        p->consume_scan++;
        if(r==COMP_SEG_NOT_FOUND)return COMP_SEG_PENDING;
        if(r!=COMP_SEG_OK)return consume_failed(p,r);
        if(receipt.descriptor.recording_id!=p->consume.descriptor.recording_id)return COMP_SEG_PENDING;
        if(!queued_proof(p,&receipt.descriptor))return consume_failed(p,COMP_SEG_BAD_ARGUMENT);
        p->consume=receipt;p->consume_phase=CONSUME_DONE;p->consume_result=COMP_SEG_OK;
        return COMP_SEG_OK; /* replay performs no new erase or stats increment */
    }
    if(p->consume_phase==CONSUME_ACK) {
        r=comp_wba_segment_storage_catalog_poll(p->config.storage,c);
        if(r==COMP_SEG_OK) {
            p->consume_phase=CONSUME_RECLAIM_BEGIN;
#if COMPANION_WBA_RECLAIM_TIMING
            p->consume_timing_ms[2]=p->config.now_ms(p->config.context);
#endif
        }
        else if(r!=COMP_SEG_PENDING)return consume_failed(p,r);
        return COMP_SEG_PENDING;
    }
    if(p->consume_phase==CONSUME_RECLAIM_BEGIN) {
        if(c->phase)return COMP_SEG_PENDING;
        r=comp_segment_catalog_reclaim_at_begin(c,&p->consume,(uint8_t)(p->consume_scan-1u));
        if(r==COMP_SEG_PENDING) {
            p->consume_phase=CONSUME_RECLAIM;
#if COMPANION_WBA_RECLAIM_TIMING
            p->consume_timing_ms[3]=p->config.now_ms(p->config.context);
#endif
        }
        else return consume_failed(p,r);
        return r;
    }
    if(p->consume_phase==CONSUME_RECLAIM) {
        r=comp_wba_segment_storage_catalog_poll(p->config.storage,c);
        if(r==COMP_SEG_OK){
            p->consume_phase=CONSUME_DONE;p->consume_result=COMP_SEG_OK;p->consumed_segments++;
#if COMPANION_WBA_RECLAIM_TIMING
            p->consume_timing_ms[4]=p->config.now_ms(p->config.context);
            p->config.storage->nor->reclaim_timing.active=false;
#endif
        }
        else if(r!=COMP_SEG_PENDING)return consume_failed(p,r);
        return r;
    }
    return COMP_SEG_OK;
}
static comp_segment_result_t other_owner(comp_wba_recording_pipeline_t *p)
{
    const comp_segment_catalog_t *c=p->config.catalog;
    if(!c->phase)return COMP_SEG_OK;
    if(c->pending==&p->future&&(p->future_phase==FUTURE_RESERVE||p->future_phase==FUTURE_CANCEL))return future_progress(p);
    if(c->pending==&p->consume&&consumer_active(p))return consume_progress(p);
    return COMP_SEG_BAD_STATE;
}
static bool audio_profile(void *context,comp_rec_audio_profile_t *out)
{
    comp_wba_recording_pipeline_t *p=context;
    return p && p->config.audio_profile && p->config.audio_profile(p->config.context,out);
}
static bool microphone(void *v,bool enabled)
{comp_wba_recording_pipeline_t *p=v;return p->config.microphone(p->config.context,enabled);}
static uint32_t now(void *v)
{comp_wba_recording_pipeline_t *p=v;return p->config.now_ms(p->config.context);}
static comp_segment_result_t next(void *v,bool take,const comp_segment_entry_t **e,comp_segment_audio_t **writer)
{
    comp_wba_recording_pipeline_t *p=v;
    if(p->future_phase==FUTURE_FULL)return COMP_SEG_FULL;
    if(p->future_phase!=FUTURE_READY)return COMP_SEG_PENDING;
    /* The immutable future was prepared before a PAUSE shortened the active
     * horizon. Do not expose or take its stale sample binding. Background
     * first verifies/cancels the entirely empty owner, then reserves and
     * commits a new exact provenance. No in-place metadata rewrite. */
    if(p->future.descriptor.sample_offset!=p->config.recording->active.descriptor.sample_offset+
        (uint64_t)p->config.recording->active_frame_limit*320u)return COMP_SEG_PENDING;
    *e=&p->future;*writer=&p->future_writer;
    if(take)p->future_phase=FUTURE_TAKEN;
    return COMP_SEG_OK;
}
static comp_segment_result_t seal(void *v,const comp_segment_entry_t *entry,bool begin)
{
    comp_wba_recording_pipeline_t *p=v;comp_segment_catalog_t *c=p->config.catalog;(void)begin;
    if(p->sealing&&p->sealing!=entry)return COMP_SEG_BAD_STATE;
    p->sealing=entry;
    if(!p->seal_started) {
        if(c->phase){comp_segment_result_t r=other_owner(p);return r==COMP_SEG_OK?COMP_SEG_PENDING:r;}
        /* Provenance uses the shared catalog page until its commit completes. */
        if(p->future_phase==FUTURE_PROVENANCE||p->future_phase==FUTURE_CANCEL){comp_segment_result_t r=future_progress(p);return r==COMP_SEG_OK?COMP_SEG_PENDING:r;}
        comp_segment_result_t r=comp_segment_catalog_put_begin(c,entry);
        if(r==COMP_SEG_PENDING)p->seal_started=true;
        return r;
    }
    comp_segment_result_t r=comp_wba_segment_storage_catalog_poll(p->config.storage,c);
    if(r==COMP_SEG_OK){p->seal_started=false;p->sealing=NULL;}
    return r;
}
static comp_segment_result_t cancel_core(void *v,comp_segment_audio_t *writer,bool begin)
{
    comp_wba_recording_pipeline_t *p=v;(void)begin;
    if(!p->core_cancel_started) {
        if(p->config.catalog->phase){comp_segment_result_t r=other_owner(p);return r==COMP_SEG_OK?COMP_SEG_PENDING:r;}
        if(p->future_phase==FUTURE_PROVENANCE||p->future_phase==FUTURE_CANCEL){comp_segment_result_t r=future_progress(p);return r==COMP_SEG_OK?COMP_SEG_PENDING:r;}
        comp_segment_result_t r=comp_segment_audio_cancel_begin(writer,p->config.catalog);
        if(r==COMP_SEG_PENDING)p->core_cancel_started=true;
        return r;
    }
    return comp_wba_segment_storage_cancel_poll(p->config.storage,writer);
}
static comp_segment_result_t background(void *v)
{
    comp_wba_recording_pipeline_t *p=v;comp_segment_catalog_t *c=p->config.catalog;
    if(c->phase)return other_owner(p);
    if(p->future_phase==FUTURE_TAKEN) {
        if(p->config.recording->active.descriptor.recording_id!=p->future.descriptor.recording_id)return COMP_SEG_BAD_STATE;
        return start_future(p,&p->config.recording->active);
    }
    if(p->future_phase==FUTURE_NONE)return start_future(p,&p->config.recording->active);
    if(p->future_phase==FUTURE_RESERVE||p->future_phase==FUTURE_PROVENANCE||p->future_phase==FUTURE_CANCEL)return future_progress(p);
    if(p->future_phase==FUTURE_READY&&p->future.descriptor.sample_offset!=
       p->config.recording->active.descriptor.sample_offset+(uint64_t)p->config.recording->active_frame_limit*320u) {
        comp_segment_result_t r=comp_segment_audio_cancel_begin(&p->future_writer,c);
        if(r==COMP_SEG_PENDING)p->future_phase=FUTURE_CANCEL;
        return r;
    }
    if(consumer_active(p))return consume_progress(p);
    if(p->future_phase==FUTURE_FULL&&p->full_generation!=c->generation)
        return start_future(p,&p->config.recording->active);
    return COMP_SEG_OK;
}
bool comp_wba_recording_pipeline_init(comp_wba_recording_pipeline_t *p,const comp_wba_pipeline_config_t *cfg)
{
    if(!p||!cfg||!cfg->recording||!cfg->catalog||!cfg->storage||!cfg->microphone||!cfg->now_ms||
       !cfg->catalog->mounted||cfg->storage->poisoned||cfg->storage->data_base!=cfg->catalog->data_base||
       cfg->storage->data_bytes!=cfg->catalog->data_bytes||cfg->storage->banks[0]!=cfg->catalog->banks[0]||
       cfg->storage->banks[1]!=cfg->catalog->banks[1]||!cfg->segment_frames||cfg->extent_bytes>cfg->catalog->data_bytes||
       !comp_segment_audio_capacity(cfg->extent_bytes)||
       12u+((uint64_t)cfg->segment_frames+5u)*42u>comp_segment_audio_capacity(cfg->extent_bytes))return false;
    memset(p,0,sizeof(*p));p->config=*cfg;p->state=COMP_PIPE_IDLE;return true;
}
comp_segment_result_t comp_wba_recording_pipeline_begin(comp_wba_recording_pipeline_t *p,
    uint64_t session,uint8_t mode,uint32_t started,uint32_t token)
{return comp_wba_recording_pipeline_begin_timeline(p,session,mode,started,token,false);}
comp_segment_result_t comp_wba_recording_pipeline_begin_timeline(comp_wba_recording_pipeline_t *p,
    uint64_t session,uint8_t mode,uint32_t started,uint32_t token,bool timeline)
{
    if(!p||!session||!token||mode>2u)return COMP_SEG_BAD_ARGUMENT;
    if((p->state!=COMP_PIPE_IDLE&&p->state!=COMP_PIPE_FINISHED)||p->discard_exclusive||p->workspace_bytes||p->workspace_requested||consumer_active(p)||
       p->config.catalog->phase||p->config.storage->poisoned)return COMP_SEG_BAD_STATE;
    const bool previous=p->state==COMP_PIPE_FINISHED&&p->engine_bound;
    const uint32_t end=previous?p->config.recording->active.extent_offset+p->config.recording->active.reserved_bytes:0u;
    p->engine_bound=false;p->stop_requested=false;p->seal_started=false;p->core_cancel_started=false;p->sealing=NULL;
    p->fault_stop_attempts=0u;
    p->pause_timeline=timeline;
    memset(&p->future,0,sizeof(p->future));memset(&p->future_writer,0,sizeof(p->future_writer));memset(&p->reserve,0,sizeof(p->reserve));
    p->future.state=COMP_SEG_WRITING;p->future.descriptor.session_id=session;p->future.descriptor.codec=3u;
    p->future.descriptor.format_epoch=p->config.catalog->epoch;p->future.descriptor.source_mode=mode;
    memcpy(p->future.descriptor.device_uid,p->config.catalog->uid,12u);p->future.started_unix_s=started;p->token=token;
    comp_segment_result_t r=comp_segment_reserve_begin_rotated(&p->reserve,p->config.catalog,&p->future,p->config.extent_bytes);
    if(r==COMP_SEG_PENDING&&previous&&end<=p->config.catalog->data_bytes)
        (void)comp_segment_reserve_set_search_hint(&p->reserve,end==p->config.catalog->data_bytes?0u:end);
    if(r==COMP_SEG_PENDING){p->state=COMP_PIPE_PREPARING;p->future_phase=FUTURE_RESERVE;}
    return r;
}
bool comp_wba_recording_pipeline_start(comp_wba_recording_pipeline_t *p,uint32_t token)
{
    if(!p||p->state!=COMP_PIPE_READY||token!=p->token||p->stop_requested)return false;
    if(!comp_cont_recording_start(p->config.recording,token)){(void)failed(p,COMP_SEG_IO_ERROR);return false;}
    p->state=COMP_PIPE_RECORDING;return true;
}
bool comp_wba_recording_pipeline_pause(comp_wba_recording_pipeline_t *p,uint32_t token,uint32_t sequence)
{
    return p&&p->state==COMP_PIPE_RECORDING&&p->engine_bound&&p->pause_timeline&&
        comp_cont_recording_pause(p->config.recording,token,sequence);
}
bool comp_wba_recording_pipeline_resume(comp_wba_recording_pipeline_t *p,uint32_t token,uint32_t sequence)
{
    return p&&p->state==COMP_PIPE_RECORDING&&p->engine_bound&&p->pause_timeline&&
        comp_cont_recording_resume(p->config.recording,token,sequence);
}
bool comp_wba_recording_pipeline_stop(comp_wba_recording_pipeline_t *p,uint32_t token)
{return comp_wba_recording_pipeline_stop_reason(p,token,COMP_CONT_STOP_USER);}
bool comp_wba_recording_pipeline_stop_reason(comp_wba_recording_pipeline_t *p,uint32_t token,comp_cont_stop_t reason)
{
    if(!p||!token||token!=p->token ||
       (reason!=COMP_CONT_STOP_USER && reason!=COMP_CONT_STOP_LOW_BATTERY &&
        reason!=COMP_CONT_STOP_LIMIT && reason!=COMP_CONT_STOP_SILENCE))return false;
    if(p->stop_requested)reason=(comp_cont_stop_t)p->stop_requested;
    if(p->state==COMP_PIPE_FINISHED||p->state==COMP_PIPE_STOPPING||p->state==COMP_PIPE_CLEANUP)return true;
    if(p->state==COMP_PIPE_PREPARING){p->stop_requested=(uint8_t)reason;return true;}
    if(p->state!=COMP_PIPE_READY&&p->state!=COMP_PIPE_RECORDING)return false;
    if(p->state==COMP_PIPE_RECORDING&&p->pause_timeline&&
       (p->config.recording->state==COMP_CONT_PAUSING||p->config.recording->state==COMP_CONT_RESUMING||
        p->config.recording->state==COMP_CONT_ENDING_PAUSE)) {
        /* Once STOP is accepted during a resume, stop accepting new audio
         * immediately; finish its durable timeline event, then drain PCM. */
        if(p->config.recording->state==COMP_CONT_RESUMING&&
           !comp_cont_recording_quiesce_resume(p->config.recording,token,reason))return false;
        p->stop_requested=(uint8_t)reason;return true;
    }
    if(!comp_cont_recording_stop_reason(p->config.recording,token,reason))return false;
    p->state=COMP_PIPE_STOPPING;return true;
}
static comp_segment_result_t cleanup(comp_wba_recording_pipeline_t *p)
{
    if(p->future_phase==FUTURE_RESERVE) {
        if(p->config.catalog->phase&&p->config.catalog->pending!=&p->future)return other_owner(p);
        comp_segment_result_t r=comp_wba_segment_storage_reserve_cancel_poll(p->config.storage,&p->reserve);
        if(r==COMP_SEG_OK)p->future_phase=FUTURE_NONE;
        return r;
    }
    if(p->config.catalog->phase&&p->future_phase!=FUTURE_CANCEL)return other_owner(p);
    if(p->future_phase==FUTURE_PROVENANCE)return future_progress(p);
    if(p->future_phase==FUTURE_READY) {
        comp_segment_result_t r=comp_segment_audio_cancel_fresh_begin(&p->future_writer,p->config.catalog);
        if(r==COMP_SEG_PENDING)p->future_phase=FUTURE_CANCEL;
        return r;
    }
    if(p->future_phase==FUTURE_CANCEL) {
        comp_segment_result_t r=comp_wba_segment_storage_cancel_poll(p->config.storage,&p->future_writer);
        if(r==COMP_SEG_OK)p->future_phase=FUTURE_NONE;
        return r;
    }
    /* TAKEN belongs to the core, already sealed or canceled there. FULL has
     * no durable reservation. Never forget a failed/uncertain preparation. */
    if(consumer_active(p))return consume_progress(p);
    p->state=COMP_PIPE_FINISHED;return COMP_SEG_OK;
}
static comp_wba_pipeline_state_t pipeline_poll_body(comp_wba_recording_pipeline_t *p)
{
    if(!p)return COMP_PIPE_FAILED;
    if(p->discard_exclusive)return p->state;
    if(p->state==COMP_PIPE_FAILED) {
        /* A real stopped fault must not strand a catalogue commit which
         * already began under this pipeline's ownership. Never restart the
         * encoder or producer/reservation/provenance/normal seal machinery.
         * Completing an already-authorized consumer retains its exact proof.
         * Keep the original recording failure even if settlement fails. */
        comp_cont_recording_t *e=p->config.recording;
        comp_segment_catalog_t *c=p->config.catalog;
        /* A failed DMA stop must not strand the microphone forever. Retry only
         * the existing fault stop, at most three times and 100 ms apart; never
         * start capture, alter the original error, or touch storage while live. */
        if(p->engine_bound&&e->state==COMP_CONT_FAULT&&e->microphone_active&&p->fault_stop_attempts<3u) {
            uint32_t now_ms=p->config.now_ms(p->config.context);
            if(!p->fault_stop_attempts||(int32_t)(now_ms-p->fault_stop_due_ms)>=0) {
                ++p->fault_stop_attempts;p->fault_stop_due_ms=now_ms+100u;
                (void)comp_cont_recording_poll(e);
            }
        }
        /* A different recorder operation can poison storage while a valid
         * consume proof is queued. No pending consumer can advance on a
         * poisoned adapter; report failure so radio can release its request.
         * Keep the exact proof and any catalogue pending pointer untouched;
         * a failed result is never an acknowledgement or permission to erase. */
        if(p->config.storage->poisoned&&consumer_active(p))
            (void)consume_failed(p,COMP_SEG_IO_ERROR);
        if(!p->engine_bound||e->state!=COMP_CONT_FAULT||e->microphone_active||
           e->encoder_owned||p->workspace_bytes||p->workspace_requested||p->config.storage->poisoned)
            return p->state;
        if(c->phase) {
            const bool sealing=p->sealing&&c->pending==p->sealing;
            const bool future=c->pending==&p->future&&
                (p->future_phase==FUTURE_RESERVE||p->future_phase==FUTURE_CANCEL);
            const bool consume=c->pending==&p->consume&&consumer_active(p);
            if((sealing||future||consume)&&
               comp_wba_segment_storage_catalog_poll(p->config.storage,c)==COMP_SEG_OK&&sealing) {
                p->sealing=NULL;p->seal_started=false;
            }
        } else {
            /* The future extent may already own a suspended physical erase,
             * independently of a catalogue commit. Retire just that command;
             * never start its next erase chunk, provenance, or a new reserve.
             * Keeping the cursor/WRITING entry permits explicit recovery and
             * prevents an unconfirmed extent from becoming writable/READY. */
            const companion_spi_nor_stm32wba_t *n=p->config.storage->nor;
            comp_segment_io_t io;
            bool owned=n->erase_active&&p->future_phase==FUTURE_RESERVE&&
               p->reserve.catalog==c&&p->reserve.entry==&p->future&&
               comp_segment_reserve_next_io(&p->reserve,&io)==COMP_SEG_OK&&io.kind==COMP_SEG_IO_ERASE&&
               io.address==n->erase_address&&
               companion_spi_nor_stm32wba_erase_chunk(n,io.address,io.bytes)==n->erase_bytes;
            if(owned)
                (void)comp_wba_segment_storage_reserve_poll(p->config.storage,&p->reserve);
            else if(consumer_active(p))
                (void)consume_progress(p);
        }
        return p->state;
    }
    comp_segment_result_t result=COMP_SEG_OK;
    if(p->state==COMP_PIPE_PREPARING) {
        result=future_progress(p);
        if(result==COMP_SEG_OK&&p->future_phase==FUTURE_READY) {
            comp_cont_config_t cfg={microphone,now,next,seal,cancel_core,background,p,p->config.segment_frames,10u,p->pause_timeline,
                p->config.audio_profile?audio_profile:NULL};
            if(!comp_cont_recording_init(p->config.recording,&cfg,&p->future,&p->future_writer,p->token))
                result=COMP_SEG_BAD_STATE;
            else {
                p->engine_bound=true;p->future_phase=FUTURE_TAKEN;p->state=COMP_PIPE_READY;
                if(p->stop_requested)(void)comp_wba_recording_pipeline_stop_reason(p,p->token,(comp_cont_stop_t)p->stop_requested);
            }
        }
    } else if(p->state==COMP_PIPE_RECORDING||p->state==COMP_PIPE_STOPPING) {
        comp_cont_state_t state=comp_cont_recording_poll(p->config.recording);
        if(p->stop_requested&&(state==COMP_CONT_RUNNING||state==COMP_CONT_PAUSED)) {
            if(!comp_cont_recording_stop_reason(p->config.recording,p->token,(comp_cont_stop_t)p->stop_requested)) {
                (void)failed(p,COMP_SEG_BAD_STATE);return p->state;
            }
            p->state=COMP_PIPE_STOPPING;
        }
        if(state==COMP_CONT_FAULT){(void)failed(p,p->config.recording->failure);return p->state;}
        else if(state==COMP_CONT_SEALED||state==COMP_CONT_CANCELED)p->state=COMP_PIPE_CLEANUP;
        else if(state==COMP_CONT_STOPPING)p->state=COMP_PIPE_STOPPING;
    } else if(p->state==COMP_PIPE_READY)result=background(p);
    else if(p->state==COMP_PIPE_CLEANUP)result=cleanup(p);
    else if((p->state==COMP_PIPE_IDLE||p->state==COMP_PIPE_FINISHED)&&consumer_active(p))result=consume_progress(p);
    if(result!=COMP_SEG_OK&&result!=COMP_SEG_PENDING&&result!=COMP_SEG_FULL)(void)failed(p,result);
    if(p->state==COMP_PIPE_PREPARING&&result==COMP_SEG_FULL)(void)failed(p,COMP_SEG_FULL);
    return p->state;
}
comp_segment_result_t comp_wba_recording_pipeline_consume(comp_wba_recording_pipeline_t *p,const comp_rec_v2_descriptor_t *proof)
{
    if(!p||!comp_rec_v2_valid(proof))return COMP_SEG_BAD_ARGUMENT;
    if(p->state==COMP_PIPE_FAILED||p->discard_exclusive)return COMP_SEG_BAD_STATE;
    if(p->workspace_bytes||p->workspace_requested)return COMP_SEG_BAD_STATE;
    if(proof->format_epoch!=p->config.catalog->epoch||memcmp(proof->device_uid,p->config.catalog->uid,12u))return COMP_SEG_BAD_ARGUMENT;
    if(p->consume_phase!=CONSUME_NONE&&same_proof(&p->consume.descriptor,proof))return p->consume_result;
    if(consumer_active(p))return COMP_SEG_BAD_STATE;
    /* A failed storage gate can leave the catalog pointing into consume.
     * Preserve that in-flight owner until explicit storage recovery. */
    if(p->config.storage->poisoned ||
       (p->config.catalog->phase && p->config.catalog->pending==&p->consume))return COMP_SEG_BAD_STATE;
    memset(&p->consume,0,sizeof(p->consume));p->consume.descriptor=*proof;
    p->consume.descriptor.sync_state=2u;p->consume_result=COMP_SEG_PENDING;p->consume_scan=0u;p->consume_phase=CONSUME_FIND;
    return COMP_SEG_PENDING;
}
comp_segment_result_t comp_wba_recording_pipeline_consume_wire_hint(comp_wba_recording_pipeline_t *p,const uint8_t wire[84],uint8_t slot)
{
    static const uint8_t prefix[8]={'C','R','A','2',2u,0u,84u,0u};
    if(!p||!wire||memcmp(wire,prefix,8u)||comp_rec_get32(wire+80u)!=comp_wba_recording_crc32(0u,wire,80u))
        return COMP_SEG_BAD_ARGUMENT;
    comp_rec_v2_descriptor_t proof={0};memcpy(proof.device_uid,wire+8u,12u);
    proof.format_epoch=comp_rec_get64(wire+20u);proof.session_id=comp_rec_get64(wire+28u);
    proof.segment_index=comp_rec_get32(wire+36u);proof.recording_id=comp_rec_get32(wire+40u);
    proof.encoded_length=comp_rec_get32(wire+44u);memcpy(proof.sha256,wire+48u,32u);
    if(proof.format_epoch!=p->config.catalog->epoch||memcmp(proof.device_uid,p->config.catalog->uid,12u)||
       !proof.session_id||!proof.recording_id||proof.segment_index>=COMP_REC_V2_INDEX_EXCLUSIVE_MAX||
       proof.encoded_length<54u||proof.encoded_length>COMP_REC_MAX_ENCODED_BYTES||
       !comp_rec_not_uniform(proof.sha256,32u,0u))return COMP_SEG_BAD_ARGUMENT;
    if(p->state==COMP_PIPE_FAILED||p->discard_exclusive||p->workspace_bytes||p->workspace_requested)return COMP_SEG_BAD_STATE;
    if((consumer_active(p)||p->consume_phase==CONSUME_DONE)&&wire_proof(&p->consume.descriptor,&proof))return p->consume_result;
    if(consumer_active(p))return COMP_SEG_BAD_STATE;
    /* Do not replace an owner retained by an unfinished catalog operation. */
    if(p->config.storage->poisoned ||
       (p->config.catalog->phase && p->config.catalog->pending==&p->consume))return COMP_SEG_BAD_STATE;
    memset(&p->consume,0,sizeof(p->consume));p->consume.descriptor=proof;
    p->consume_scan=slot<64u?(uint8_t)(slot|128u):0u;
    p->consume_phase=CONSUME_FIND;p->consume_result=COMP_SEG_PENDING;
#if COMPANION_WBA_RECLAIM_TIMING
    memset(p->consume_timing_ms,0,sizeof(p->consume_timing_ms));
    p->consume_timing_ms[0]=p->config.now_ms(p->config.context);
    memset(&p->config.storage->nor->reclaim_timing,0,sizeof(p->config.storage->nor->reclaim_timing));
    p->config.storage->nor->reclaim_timing.active=true;
    if(p->config.storage->nor->erase_active)p->config.storage->nor->reclaim_timing.interrupted++;
#endif
    return COMP_SEG_PENDING;
}
comp_segment_result_t comp_wba_recording_pipeline_consume_wire(comp_wba_recording_pipeline_t *p,const uint8_t wire[84])
{return comp_wba_recording_pipeline_consume_wire_hint(p,wire,64u);}
bool comp_wba_recording_pipeline_receipt(const comp_wba_recording_pipeline_t *p,uint8_t wire[84])
{
    if(!p||!wire||p->consume_phase!=CONSUME_DONE||p->consume_result!=COMP_SEG_OK||
       !comp_rec_v2_valid(&p->consume.descriptor))return false;
    const comp_rec_v2_descriptor_t *d=&p->consume.descriptor;memset(wire,0,84u);
    memcpy(wire,"CRA2",4u);comp_rec_put16(wire+4u,2u);comp_rec_put16(wire+6u,84u);
    memcpy(wire+8u,d->device_uid,12u);comp_rec_put64(wire+20u,d->format_epoch);comp_rec_put64(wire+28u,d->session_id);
    comp_rec_put32(wire+36u,d->segment_index);comp_rec_put32(wire+40u,d->recording_id);
    comp_rec_put32(wire+44u,d->encoded_length);memcpy(wire+48u,d->sha256,32u);
    comp_rec_put32(wire+80u,comp_wba_recording_crc32(0u,wire,80u));return true;
}
comp_segment_result_t comp_wba_recording_pipeline_consume_result(const comp_wba_recording_pipeline_t *p)
{return p&&p->consume_phase!=CONSUME_NONE?p->consume_result:COMP_SEG_BAD_STATE;}
bool comp_wba_recording_pipeline_consume_idle_read_failed(const comp_wba_recording_pipeline_t *p)
{return p&&p->consume_phase==CONSUME_IDLE_READ_FAILED&&p->consume_result==COMP_SEG_IO_ERROR;}

comp_segment_result_t comp_wba_recording_pipeline_workspace(comp_wba_recording_pipeline_t *p,
    uint32_t bytes,uint32_t *physical)
{
    if(!p||!physical)return COMP_SEG_BAD_ARGUMENT;
    *physical=0u;
    if((p->state!=COMP_PIPE_IDLE&&p->state!=COMP_PIPE_FINISHED)||p->discard_exclusive||consumer_active(p)||
       p->config.catalog->phase||p->config.storage->poisoned||p->config.storage->nor->erase_active)
        return COMP_SEG_BAD_STATE;
    comp_segment_catalog_t *c=p->config.catalog;
    if(bytes%4096u||bytes>c->data_bytes)return COMP_SEG_BAD_ARGUMENT;
    if(!bytes){p->workspace_bytes=0u;p->workspace_requested=0u;p->workspace_offset=0u;return COMP_SEG_OK;}
    if(p->workspace_bytes) {
        if(p->workspace_bytes!=bytes)return COMP_SEG_BAD_STATE;
        *physical=c->data_base+p->workspace_offset;return COMP_SEG_OK;
    }
    if(p->workspace_requested&&p->workspace_requested!=bytes)return COMP_SEG_BAD_STATE;
    if(!p->workspace_requested||p->workspace_generation!=c->generation) {
        p->workspace_requested=bytes;p->workspace_generation=c->generation;p->workspace_scan=0u;
    }
    while(p->workspace_scan<64u&&c->slots[p->workspace_scan]==255u)p->workspace_scan++;
    if(p->workspace_scan<64u) {
        comp_segment_entry_t entry;
        comp_segment_result_t r=comp_wba_segment_storage_entry(p->config.storage,c,p->workspace_scan,&entry);
        if(r!=COMP_SEG_OK){if(r!=COMP_SEG_PENDING)p->workspace_requested=0u;return r;}
        if(entry.extent_offset+entry.reserved_bytes>c->data_bytes-bytes) {
            p->workspace_requested=0u;return COMP_SEG_FULL;
        }
        p->workspace_scan++;return COMP_SEG_PENDING;
    }
    p->workspace_bytes=bytes;p->workspace_requested=0u;p->workspace_offset=c->data_bytes-bytes;
    *physical=c->data_base+c->data_bytes-bytes;return COMP_SEG_OK;
}
comp_segment_result_t comp_wba_recording_pipeline_workspace_snapshot(comp_wba_recording_pipeline_t *p,
    uint32_t bytes,uint32_t generation,uint32_t highest,uint32_t *physical)
{
    if(!p||!physical||!p->config.catalog)return COMP_SEG_BAD_ARGUMENT;
    *physical=0u;
    if(bytes>p->config.catalog->data_bytes||highest>p->config.catalog->data_bytes)return COMP_SEG_BAD_ARGUMENT;
    if(highest>p->config.catalog->data_bytes-bytes)return COMP_SEG_FULL;
    return comp_wba_recording_pipeline_workspace_at_snapshot(p,bytes,generation,
        p->config.catalog->data_bytes-bytes,physical);
}
comp_segment_result_t comp_wba_recording_pipeline_workspace_at_snapshot(comp_wba_recording_pipeline_t *p,
    uint32_t bytes,uint32_t generation,uint32_t offset,uint32_t *physical)
{
    if(!p||!physical||!p->config.catalog||!p->config.storage)return COMP_SEG_BAD_ARGUMENT;
    *physical=0u;
    if((p->state!=COMP_PIPE_IDLE&&p->state!=COMP_PIPE_FINISHED)||p->discard_exclusive||consumer_active(p)||p->workspace_requested||
       p->config.catalog->phase||p->config.storage->poisoned||p->config.storage->nor->erase_active)
        return COMP_SEG_BAD_STATE;
    comp_segment_catalog_t *c=p->config.catalog;
    if(!c->mounted||bytes%4096u||bytes>c->data_bytes||offset%4096u||offset>c->data_bytes-bytes)return COMP_SEG_BAD_ARGUMENT;
    if(c->generation!=generation)return COMP_SEG_STALE_SNAPSHOT;
    if(p->workspace_bytes&&(p->workspace_bytes!=bytes||p->workspace_offset!=offset))return COMP_SEG_BAD_STATE;
    p->workspace_bytes=bytes;p->workspace_offset=bytes?offset:0u;
    *physical=bytes?c->data_base+offset:0u;return COMP_SEG_OK;
}

comp_wba_pipeline_state_t comp_wba_recording_pipeline_poll(comp_wba_recording_pipeline_t *p)
{
    comp_cpu_stage_span_t cpu=comp_cpu_detail_begin();
    comp_wba_pipeline_state_t r=pipeline_poll_body(p);
    comp_cpu_detail_end(COMP_CPU_STAGE_PIPELINE,cpu,true);
    return r;
}
