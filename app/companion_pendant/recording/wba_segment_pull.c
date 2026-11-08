#include "wba_segment_pull.h"
#include "wba_recording_service.h"
#include "companion_range_reclaim.h"
enum {PULL_IDLE=0,PULL_FIND,PULL_READY,PULL_DONE,PULL_FAILED};
static bool owned_prefix(const comp_segment_entry_t *a,const comp_segment_entry_t *b)
{
    const comp_rec_v2_descriptor_t *x=&a->descriptor,*y=&b->descriptor;
    return (b->state==COMP_SEG_WRITING||b->state==COMP_SEG_UNSYNCED||b->state==COMP_SEG_ACKED)&&
        x->recording_id==y->recording_id&&x->format_epoch==y->format_epoch&&x->session_id==y->session_id&&
        x->segment_index==y->segment_index&&x->sample_offset==y->sample_offset&&
        x->codec==y->codec&&x->source_mode==y->source_mode&&!memcmp(x->device_uid,y->device_uid,12u)&&
        a->extent_offset==b->extent_offset&&a->reserved_bytes==b->reserved_bytes&&
        a->started_unix_s==b->started_unix_s&&
        (b->state==COMP_SEG_WRITING||(comp_rec_v2_valid(y)&&x->encoded_length<=y->encoded_length));
}
static bool same_entry(const comp_segment_entry_t *a,const comp_segment_entry_t *b)
{
    const comp_rec_v2_descriptor_t *x=&a->descriptor,*y=&b->descriptor;
    return (b->state==COMP_SEG_UNSYNCED||b->state==COMP_SEG_ACKED)&&comp_rec_v2_valid(y)&&
        x->recording_id==y->recording_id&&x->format_epoch==y->format_epoch&&x->session_id==y->session_id&&
        x->segment_index==y->segment_index&&x->sample_offset==y->sample_offset&&x->sample_count==y->sample_count&&
        x->encoded_length==y->encoded_length&&x->content_crc32==y->content_crc32&&x->total_segments==y->total_segments&&
        x->flags==y->flags&&x->codec==y->codec&&x->source_mode==y->source_mode&&
        !memcmp(x->device_uid,y->device_uid,12u)&&!memcmp(x->sha256,y->sha256,32u)&&
        a->extent_offset==b->extent_offset&&a->reserved_bytes==b->reserved_bytes&&a->started_unix_s==b->started_unix_s;
}
static bool allowed(void *v)
{comp_wba_segment_pull_t *p=v;return p->config.foreground_allowed(p->config.context);}
static bool notify(void *v,const uint8_t *bytes,uint16_t length)
{comp_wba_segment_pull_t *p=v;return p->config.notify(p->config.context,bytes,length);}
static bool metadata(void *v,uint32_t id,comp_recording_journal_entry_t *out)
{
    comp_wba_segment_pull_t *p=v;const comp_segment_entry_t *e=p->config.selected;
    const comp_rec_v2_descriptor_t *d=&e->descriptor;comp_segment_catalog_t *c=p->config.catalog;
    if(p->phase!=PULL_READY||id!=d->recording_id||!c->mounted||p->config.storage->poisoned||
       (!p->live&&((e->state!=COMP_SEG_UNSYNCED&&e->state!=COMP_SEG_ACKED)||!comp_rec_v2_valid(d)))||
       e->extent_offset>c->data_bytes||e->reserved_bytes>c->data_bytes-e->extent_offset||
       d->encoded_length>comp_segment_audio_capacity(e->reserved_bytes))return false;
    memset(out,0,sizeof(*out));out->recording_id=id;out->extent_offset=e->extent_offset;
    out->payload_offset=e->extent_offset+256u;out->reserved_bytes=e->reserved_bytes;
    out->committed_bytes=out->total_length=d->encoded_length;out->content_crc32=d->content_crc32;
    out->started_unix_s=e->started_unix_s;out->codec=d->codec;out->source_mode=d->source_mode;
    out->sync_state=p->live?COMP_RECORDING_JOURNAL_WRITING:
        (e->state==COMP_SEG_UNSYNCED?COMP_RECORDING_JOURNAL_UNSYNCED:COMP_RECORDING_JOURNAL_ACKED);
    memcpy(out->sha256,d->sha256,32u);return true;
}
/* Directory rechecks are as read-only as payload reads. A released transient
 * failure yields at most twice and never retires the running recorder. */
static comp_segment_result_t transfer_entry(comp_wba_segment_pull_t *p,uint8_t slot,comp_segment_entry_t *out)
{
    companion_spi_nor_stm32wba_t *nor=p->config.storage->nor;
    const bool timed=nor&&nor->config.now_ms;
    uint32_t started=timed?nor->config.now_ms(nor->config.context):0u;
    comp_segment_result_t r=comp_wba_segment_storage_transfer_entry(p->config.storage,p->config.catalog,slot,out);
    if(r==COMP_SEG_PENDING&&p->config.storage->transfer_read_released_failure) {
        uint32_t elapsed=timed?nor->config.now_ms(nor->config.context)-started:10u;
        if(p->read_retries<2u&&elapsed<10u&&elapsed+(uint32_t)p->read_retry_elapsed_ms<10u) {
            ++p->read_retries;p->read_retry_elapsed_ms+=(uint8_t)elapsed;return COMP_SEG_PENDING;
        }
        p->read_retries=0u;p->read_retry_elapsed_ms=0u;return COMP_SEG_IO_ERROR;
    }
    if(r!=COMP_SEG_PENDING){p->read_retries=0u;p->read_retry_elapsed_ms=0u;}
    return r;
}
static comp_wba_transfer_read_result_t read_preflight(comp_wba_segment_pull_t *p,uint32_t id,uint32_t offset,uint32_t bytes)
{
    comp_segment_catalog_t *c=p->config.catalog;
    const comp_segment_entry_t *e=p->config.selected;
    if(!c->mounted||p->config.storage->poisoned)return COMP_WBA_TRANSFER_READ_ERROR;
    /* A negotiated radio value spans multiple physical248B pages. Cache fills
     * remain page-sized, but validating the caller's compact packet must keep
     * the original489B logical limit or current Android receives no first packet. */
    if(id!=e->descriptor.recording_id||!bytes||bytes>COMP_WBA_RECORDING_TRANSFER_COMPACT_PAYLOAD_BYTES||offset>e->descriptor.encoded_length||
       bytes>e->descriptor.encoded_length-offset)return COMP_WBA_TRANSFER_READ_ERROR;
    if(p->slot<64u){
        uint16_t frontier=c->range_id[p->slot]==id?c->range_end[p->slot]:0u;
        if(c->range_worker&&c->range_worker->plan.recording_id==id&&
           c->range_worker->plan.end_sector>frontier)frontier=c->range_worker->plan.end_sector;
        uint32_t gone=frontier?((uint32_t)frontier*16u-1u)*248u:0u;
        if(offset<gone)return COMP_WBA_TRANSFER_READ_ERROR;
    }
    /* Already verified immutable bytes need no NOR scratch or transaction.
     * Keep the identity/frontier checks above, and recheck changed catalog
     * generations through the ordinary storage path before draining RAM. */
    if(p->cache&&c->generation==p->generation&&offset>=p->cache_offset&&
       offset-p->cache_offset+bytes<=p->cache_bytes)
        return COMP_WBA_TRANSFER_READ_OK;
    if(!comp_segment_catalog_transfer_readable(c)||!p->config.page_available(p->config.context))return COMP_WBA_TRANSFER_READ_WAIT;
    if(c->generation!=p->generation) {
        comp_segment_entry_t actual;
        comp_segment_result_t result=transfer_entry(p,p->slot,&actual);
        if(result==COMP_SEG_PENDING)return COMP_WBA_TRANSFER_READ_WAIT;
        if(result!=COMP_SEG_OK||!(p->live?owned_prefix(e,&actual):same_entry(e,&actual)))return COMP_WBA_TRANSFER_READ_ERROR;
        p->generation=c->generation;return COMP_WBA_TRANSFER_READ_WAIT;
    }
    return COMP_WBA_TRANSFER_READ_OK;
}
static comp_wba_transfer_read_result_t read_source(comp_wba_segment_pull_t *p,uint32_t id,uint32_t offset,uint8_t *out,uint32_t bytes)
{
    comp_wba_transfer_read_result_t ready=read_preflight(p,id,offset,bytes);
    if(ready!=COMP_WBA_TRANSFER_READ_OK)return ready;
    comp_segment_catalog_t *c=p->config.catalog;
    const comp_segment_entry_t *e=p->config.selected;
    if(!p->read_bytes) {
        p->read_bytes=bytes;p->read_offset=offset;p->read_destination=out;p->copied=0u;
    } else if(p->read_bytes!=bytes||p->read_offset!=offset||p->read_destination!=out)
        return COMP_WBA_TRANSFER_READ_ERROR;
    uint32_t logical=offset+p->copied,index=logical/248u,in_page=logical%248u;
    uint8_t length=0u;comp_segment_audio_port_t port=comp_wba_segment_storage_transfer_audio_port(p->config.storage);
    p->config.storage->transfer_read_released_failure=false;
    companion_spi_nor_stm32wba_t *nor=p->config.storage->nor;
    const bool timed=nor && nor->config.now_ms;
    const uint32_t read_started=timed?nor->config.now_ms(nor->config.context):0u;
    comp_segment_result_t result=comp_segment_audio_read_page(&port,e,c->data_base,index,p->config.page,&length);
    if(result==COMP_SEG_PENDING)return COMP_WBA_TRANSFER_READ_WAIT;
    /* Retry only a read command whose payload failed and whose CS was
     * released; retain the unchanged cursor and yield to capture each time.
     * A read that already exceeded a PCM period must not cause extra stalls. */
    if(result==COMP_SEG_IO_ERROR && p->config.storage->transfer_read_released_failure &&
       !p->config.storage->poisoned && p->read_retries<2u && timed) {
        uint32_t elapsed=nor->config.now_ms(nor->config.context)-read_started;
        if(elapsed<10u && elapsed+(uint32_t)p->read_retry_elapsed_ms<10u) {
            p->read_retry_elapsed_ms+=(uint8_t)elapsed;
            p->read_retries++;return COMP_WBA_TRANSFER_READ_WAIT;
        }
    }
    if(result==COMP_SEG_OK){p->read_retries=0u;p->read_retry_elapsed_ms=0u;}
    /* If a sealed read still poisoned the adapter (for example CS release
     * was uncertain), let the existing idle-only recovery perform its own
     * hardware preflight after every owner releases. Never classify live
     * prefixes, corrupt pages, writes or an active erase as idle recovery. */
    if(result==COMP_SEG_IO_ERROR && p->config.storage->poisoned && !p->live && !c->phase &&
       p->config.storage->nor && !p->config.storage->nor->erase_active)
        p->config.storage->idle_lookup_read_failed=true;
    if(result!=COMP_SEG_OK||in_page>=length)return COMP_WBA_TRANSFER_READ_ERROR;
    uint32_t n=(uint32_t)length-in_page;
    if(n>bytes-p->copied)n=bytes-p->copied;
    memcpy(out+p->copied,p->config.page+in_page,n);p->copied=(uint16_t)(p->copied+n);
    /* The physical scratch is released here even when a packet crosses two
     * pages. Only copied bytes in the EXISTING packet buffer remain pending. */
    if(p->copied!=bytes)return COMP_WBA_TRANSFER_READ_WAIT;
    p->read_bytes=0u;p->read_destination=NULL;p->copied=0u;return COMP_WBA_TRANSFER_READ_OK;
}
void comp_wba_segment_pull_cache_release(comp_wba_segment_pull_t *p)
{
    if(!p||!p->cache)return;
    p->cache_ports->release(p->cache_ports->context,p->cache);p->cache=NULL;
    p->cache_head=p->cache_bytes=0u;
    /* Any incomplete cache fill is read-only and has not advanced its ring.
     * Drop its scratch destination before a producer reuses the workspace. */
    p->read_bytes=0u;p->read_destination=NULL;p->copied=0u;
}
void comp_wba_segment_pull_cache_bind(comp_wba_segment_pull_t *p,const comp_wba_segment_pull_cache_ports_t *ports)
{
    if(!p)return;
    comp_wba_segment_pull_cache_release(p);
    p->cache_ports=ports&&ports->acquire&&ports->release?ports:NULL;
}
static comp_wba_transfer_read_result_t read_logical(void *v,uint32_t id,uint32_t offset,uint8_t *out,uint32_t bytes)
{
    comp_wba_segment_pull_t *p=v;
    if(p->live||!p->cache_ports)return read_source(p,id,offset,out,bytes);
    comp_wba_transfer_read_result_t r=read_preflight(p,id,offset,bytes);
    if(r!=COMP_WBA_TRANSFER_READ_OK)return r;
    if(!p->cache) {
        if(p->read_bytes)return read_source(p,id,offset,out,bytes);
        p->cache=p->cache_ports->acquire(p->cache_ports->context,COMP_SEG_PULL_PREFETCH_BYTES);
        if(!p->cache)return read_source(p,id,offset,out,bytes);
        p->cache_offset=offset;p->cache_head=p->cache_bytes=0u;
    }
    if(offset<p->cache_offset||offset-p->cache_offset>p->cache_bytes) {
        comp_wba_segment_pull_cache_release(p);return COMP_WBA_TRANSFER_READ_ERROR;
    }
    uint32_t drop=offset-p->cache_offset;
    p->cache_head=(uint16_t)((p->cache_head+drop)%COMP_SEG_PULL_PREFETCH_BYTES);
    p->cache_bytes=(uint16_t)(p->cache_bytes-drop);p->cache_offset=offset;
    companion_spi_nor_stm32wba_t *nor=p->config.storage->nor;
    const uint32_t started=nor->config.now_ms(nor->config.context);
    /* Up to four existing page reads, within 1ms. Reads outrun consumption
     * while idle, then radio drains the same ring with NO NOR access or erase
     * suspension while its independently owned prefix is physically erased. */
    for(unsigned i=0u;i<4u&&!nor->erase_active&&
        COMP_SEG_PULL_PREFETCH_BYTES-p->cache_bytes>=248u;i++) {
        uint32_t end=p->cache_offset+p->cache_bytes;
        if(end==p->config.selected->descriptor.encoded_length)break;
        uint32_t tail=((uint32_t)p->cache_head+p->cache_bytes)%COMP_SEG_PULL_PREFETCH_BYTES;
        uint32_t n=248u-end%248u;
        if(n>p->config.selected->descriptor.encoded_length-end)n=p->config.selected->descriptor.encoded_length-end;
        if(n>COMP_SEG_PULL_PREFETCH_BYTES-tail)n=COMP_SEG_PULL_PREFETCH_BYTES-tail;
        r=read_source(p,id,end,p->cache+tail,n);
        if(r==COMP_WBA_TRANSFER_READ_ERROR){comp_wba_segment_pull_cache_release(p);return r;}
        if(r==COMP_WBA_TRANSFER_READ_WAIT)break;
        p->cache_bytes=(uint16_t)(p->cache_bytes+n);++p->cache_pages;
        if((uint32_t)(nor->config.now_ms(nor->config.context)-started)>=1u)break;
    }
    if(p->cache_bytes<bytes)return COMP_WBA_TRANSFER_READ_WAIT;
    uint32_t first=COMP_SEG_PULL_PREFETCH_BYTES-p->cache_head;
    if(first>bytes)first=bytes;
    memcpy(out,p->cache+p->cache_head,first);
    if(first<bytes)memcpy(out+first,p->cache,bytes-first);
    ++p->cache_hits;if(nor->erase_active)++p->cache_erase_hits;
    if(offset+bytes==p->config.selected->descriptor.encoded_length)
        comp_wba_segment_pull_cache_release(p); /* final bytes now in existing TX packet */
    return COMP_WBA_TRANSFER_READ_OK;
}
static const comp_wba_recording_transfer_backend_t backend={metadata,read_logical};
bool comp_wba_segment_pull_init(comp_wba_segment_pull_t *p,const comp_wba_segment_pull_config_t *cfg)
{
    if(!p||!cfg||!cfg->storage||!cfg->catalog||!cfg->transfer||!cfg->selected||!cfg->page||
       !cfg->foreground_allowed||!cfg->page_available||!cfg->notify||!cfg->catalog->mounted||
       cfg->storage->data_base!=cfg->catalog->data_base||cfg->storage->data_bytes!=cfg->catalog->data_bytes||
       cfg->storage->banks[0]!=cfg->catalog->banks[0]||cfg->storage->banks[1]!=cfg->catalog->banks[1]||
       cfg->storage->poisoned)return false;
    memset(p,0,sizeof(*p));p->config=*cfg;p->slot=64u;
    comp_wba_recording_transfer_config_t transfer={0};transfer.notify=notify;
    transfer.heavy_io_allowed=allowed;transfer.live_read_allowed=allowed;transfer.context=p;
    return comp_wba_recording_transfer_init_backend(cfg->transfer,&transfer,&backend);
}
void comp_wba_segment_pull_cancel(comp_wba_segment_pull_t *p)
{
    if(!p)return;
    comp_wba_segment_pull_cache_release(p);
    if(p->config.storage)p->config.storage->transfer_read_yield=false;
    comp_wba_recording_transfer_cancel(p->config.transfer);p->phase=PULL_IDLE;
    p->read_bytes=0u;p->read_destination=NULL;p->copied=0u;p->read_retries=0u;p->read_retry_elapsed_ms=0u;p->result=COMP_SEG_OK;p->live=false;
}
static bool tail_prefix(comp_wba_segment_pull_t *p,const comp_segment_entry_t *e,
    uint32_t committed,uint32_t non_audio)
{
    if(!p||!e||!p->config.transfer->connected||e->state!=COMP_SEG_WRITING||
       e->descriptor.codec!=3u||e->descriptor.source_mode!=COMP_WBA_RECORDING_SOURCE_MIC_SAI||committed<54u||
       committed>comp_segment_audio_capacity(e->reserved_bytes)||
       e->descriptor.format_epoch!=p->config.catalog->epoch||
       memcmp(e->descriptor.device_uid,p->config.catalog->uid,12u)||non_audio>committed-12u)return false;
    const uint32_t frames=(committed-12u-non_audio)/COMP_SEG_AUDIO_FRAME_BYTES;
    if(!frames)return false;
    comp_wba_segment_pull_cancel(p);*p->config.selected=*e;
    p->config.selected->descriptor.encoded_length=12u+non_audio+frames*COMP_SEG_AUDIO_FRAME_BYTES;
    p->config.selected->descriptor.sample_count=(uint64_t)frames*320u;
    p->live=true;p->phase=PULL_DONE;return true;
}
bool comp_wba_segment_pull_tail(comp_wba_segment_pull_t *p,const comp_segment_entry_t *e,uint32_t committed)
{return tail_prefix(p,e,committed,0u);}
bool comp_wba_segment_pull_tail_timeline(comp_wba_segment_pull_t *p,const comp_segment_entry_t *e,
    uint32_t committed,uint32_t non_audio)
{return tail_prefix(p,e,committed,non_audio);}
bool comp_wba_segment_pull_peer(comp_wba_segment_pull_t *p,const uint8_t uid[12],uint64_t epoch,bool authenticated)
{
    if(!p)return false;
    bool valid=authenticated&&uid&&epoch==p->config.catalog->epoch&&!memcmp(uid,p->config.catalog->uid,12u);
    if(!valid)comp_wba_segment_pull_cancel(p);
    comp_wba_recording_transfer_set_connected(p->config.transfer,valid);return valid;
}
comp_segment_result_t comp_wba_segment_pull_begin(comp_wba_segment_pull_t *p,const uint8_t request[32])
{
    if(!p||!request||request[0]!=2u||(request[1]!=COMP_SEG_PULL_COMMAND&&request[1]!=0x24u)||
       (request[2]&4u)!=request[2]||request[3]||!comp_rec_get32(request+4u)||
       comp_rec_get64(request+8u)!=p->config.catalog->epoch||!comp_rec_get64(request+16u)||
       comp_rec_get32(request+24u)>=COMP_REC_V2_INDEX_EXCLUSIVE_MAX)return COMP_SEG_BAD_ARGUMENT;
    if(!p->config.transfer->connected)return COMP_SEG_BAD_STATE;
    bool live=request[1]==0x24u;
    if(live) {
        const comp_rec_v2_descriptor_t *d=&p->config.selected->descriptor;
        if(!p->live||d->recording_id!=comp_rec_get32(request+4u)||d->session_id!=comp_rec_get64(request+16u)||
           d->segment_index!=comp_rec_get32(request+24u)||comp_rec_get32(request+28u)>=d->encoded_length)
            return COMP_SEG_BAD_ARGUMENT;
    }
    comp_wba_segment_pull_cancel(p);p->live=live;p->session=comp_rec_get64(request+16u);
    p->cache_hits=p->cache_erase_hits=p->cache_pages=0u;
    p->segment_index=comp_rec_get32(request+24u);
    memset(&p->request,0,sizeof(p->request));p->request.schema_version=1u;p->request.flags=request[2];
    p->request.recording_id=comp_rec_get32(request+4u);p->request.byte_offset=comp_rec_get32(request+28u);
    /* A slot is only a read hint, never a cached descriptor. Re-read it and
     * check the complete request before using it. Recycled reservations often
     * keep the same logical slot; unrelated selections fall back to slot0. */
    p->generation=p->config.catalog->generation;
    p->scan=p->slot<64u?(uint8_t)(p->slot|128u):0u;
    p->phase=PULL_FIND;p->result=COMP_SEG_PENDING;
    return COMP_SEG_PENDING;
}
static comp_segment_result_t failure(comp_wba_segment_pull_t *p,comp_segment_result_t result)
{comp_wba_segment_pull_cache_release(p);p->phase=PULL_FAILED;p->result=result;comp_wba_recording_transfer_cancel(p->config.transfer);return result;}
comp_segment_result_t comp_wba_segment_pull_select_poll(comp_wba_segment_pull_t *p)
{
    if(!p)return COMP_SEG_BAD_ARGUMENT;
    if(p->phase==PULL_DONE||p->phase==PULL_FAILED)return p->result;
    if(!p->config.transfer->connected)return COMP_SEG_BAD_STATE;
    comp_segment_catalog_t *c=p->config.catalog;
    if(p->phase==PULL_FIND) {
        if(!comp_segment_catalog_transfer_readable(c)||!allowed(p))return COMP_SEG_PENDING;
        if(c->generation!=p->generation){p->scan=0u;p->generation=c->generation;}
        if(p->scan==64u)return failure(p,COMP_SEG_NOT_FOUND);
        comp_segment_entry_t e;
        const bool hinted=(p->scan&128u)!=0u;
        const uint8_t slot=(uint8_t)(p->scan&63u);
        comp_segment_result_t result=transfer_entry(p,slot,&e);
        if(result==COMP_SEG_PENDING)return result;
        p->scan=hinted?0u:(uint8_t)(slot+1u);
        if(result==COMP_SEG_NOT_FOUND)return COMP_SEG_PENDING;
        if(result!=COMP_SEG_OK)return failure(p,result);
        if(e.descriptor.recording_id!=p->request.recording_id)return COMP_SEG_PENDING;
        if(p->live) {
            if(!owned_prefix(p->config.selected,&e))return failure(p,COMP_SEG_BAD_ARGUMENT);
        } else {
            if((e.state!=COMP_SEG_UNSYNCED&&e.state!=COMP_SEG_ACKED)||e.descriptor.session_id!=p->session||
               e.descriptor.segment_index!=p->segment_index||!comp_rec_v2_valid(&e.descriptor))return failure(p,COMP_SEG_BAD_ARGUMENT);
            *p->config.selected=e;
        }
        p->slot=slot;p->phase=PULL_READY;
    }
    if(p->phase!=PULL_READY)return COMP_SEG_BAD_STATE;
    if(p->config.transfer->state==COMP_WBA_RECORDING_TRANSFER_IDLE) {
        if(!comp_segment_catalog_transfer_readable(c))return COMP_SEG_PENDING;
        /* Capture can claim the foreground after selection. Keep the exact
         * request on BUSY, but never start from an outdated catalog proof. */
        if(c->generation!=p->generation) {
            p->scan=0u;p->generation=c->generation;p->phase=PULL_FIND;
            return COMP_SEG_PENDING;
        }
        comp_wba_recording_transfer_result_t result=
            comp_wba_recording_transfer_start(p->config.transfer,&p->request);
        if(result==COMP_WBA_RECORDING_TRANSFER_BUSY)return COMP_SEG_PENDING;
        if(result!=COMP_WBA_RECORDING_TRANSFER_OK)return failure(p,COMP_SEG_BAD_ARGUMENT);
    }
    return COMP_SEG_OK;
}
comp_segment_result_t comp_wba_segment_pull_poll(comp_wba_segment_pull_t *p)
{
    if(!p)return COMP_SEG_BAD_ARGUMENT;
    /* Preserve the original <=1I/O contract when selection reads metadata. */
    if(p->phase==PULL_FIND||(p->phase==PULL_READY&&
       p->config.transfer->state==COMP_WBA_RECORDING_TRANSFER_IDLE)) {
        comp_segment_result_t result=comp_wba_segment_pull_select_poll(p);
        return result==COMP_SEG_OK?COMP_SEG_PENDING:result;
    }
    if(p->phase==PULL_DONE||p->phase==PULL_FAILED)return p->result;
    if(!p->config.transfer->connected||p->phase!=PULL_READY)return COMP_SEG_BAD_STATE;
    /* Capture has priority over this reader, including an already cached
     * notify. Healthy foreground waiting must retain the window exactly. */
    if(!allowed(p))return COMP_SEG_PENDING;
    comp_wba_recording_transfer_state_t state=comp_wba_recording_transfer_poll(p->config.transfer);
    if(state==COMP_WBA_RECORDING_TRANSFER_COMPLETE){p->phase=PULL_DONE;p->result=COMP_SEG_OK;return COMP_SEG_OK;}
    if(state==COMP_WBA_RECORDING_TRANSFER_FAILED)return failure(p,COMP_SEG_IO_ERROR);
    return COMP_SEG_PENDING;
}
