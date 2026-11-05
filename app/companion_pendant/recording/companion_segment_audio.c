#include "companion_segment_audio.h"
#include "wba_recording_crc.h"

enum { IDLE=0, PROVENANCE_BODY, PROVENANCE_VERIFY, PROVENANCE_COMMIT,
       PROVENANCE_COMMIT_VERIFY, PAGE_BODY, PAGE_VERIFY, PAGE_COMMIT,
       PAGE_COMMIT_VERIFY,CANCEL_PROVENANCE,CANCEL_PAGES,CANCEL_BEGIN,CANCEL_DIRECTORY,
       REC_PROVENANCE=1, REC_PAGES=2, REC_DONE=3 };
enum { PROVENANCE_CRC=92, AUDIO_CRC=248, COMMIT=252 };

static bool uniform(const uint8_t *p,size_t bytes,uint8_t value)
{return !comp_rec_not_uniform(p,bytes,value);}

uint32_t comp_segment_audio_capacity(uint32_t reserved_bytes)
{
    if (reserved_bytes<4096u || reserved_bytes%4096u!=0u) return 0u;
    return (reserved_bytes/256u-1u)*COMP_SEG_AUDIO_DATA_BYTES;
}

static bool valid_reservation(const comp_segment_entry_t *e,uint32_t base)
{
    if (!e || e->state!=COMP_SEG_WRITING || !e->descriptor.recording_id ||
        !e->descriptor.format_epoch || !e->descriptor.session_id ||
        e->descriptor.segment_index>=COMP_REC_V2_INDEX_EXCLUSIVE_MAX ||
        e->descriptor.codec!=3u || e->descriptor.source_mode>2u ||
        e->descriptor.sample_offset%320u || e->descriptor.sample_count ||
        e->descriptor.encoded_length || e->descriptor.flags ||
        !comp_segment_audio_capacity(e->reserved_bytes) ||
        base%4096u || e->extent_offset%4096u ||
        base>UINT32_MAX-e->extent_offset ||
        e->reserved_bytes>UINT32_MAX-base-e->extent_offset ||
        comp_segment_provenance_extent(e)%4096u ||
        uniform(e->descriptor.device_uid,12u,0u) ||
        uniform(e->descriptor.device_uid,12u,255u)) return false;
    return true;
}

static void provenance(const comp_segment_entry_t *e,uint8_t *p)
{
    const comp_rec_v2_descriptor_t *d=&e->descriptor;
    memset(p,255,256u);memcpy(p,"CSP2",4u);comp_rec_put16(p+4u,1u);
    comp_rec_put16(p+6u,96u);comp_rec_put32(p+8u,d->recording_id);
    comp_rec_put64(p+12u,d->format_epoch);comp_rec_put64(p+20u,d->session_id);
    comp_rec_put32(p+28u,d->segment_index);comp_rec_put64(p+32u,d->sample_offset);
    comp_rec_put32(p+40u,comp_segment_provenance_extent(e));comp_rec_put32(p+44u,e->reserved_bytes);
    memcpy(p+48u,d->device_uid,12u);p[60]=d->codec;p[61]=d->source_mode;
    comp_rec_put32(p+64u,e->started_unix_s);
    comp_rec_put32(p+PROVENANCE_CRC,comp_rec_crc(p,PROVENANCE_CRC));
}

static uint32_t binding(const comp_segment_entry_t *e)
{
    /* Same on-write/on-recovery binding without another full page buffer. */
    uint8_t p[PROVENANCE_CRC];const comp_rec_v2_descriptor_t *d=&e->descriptor;
    memset(p,255,sizeof(p));memcpy(p,"CSP2",4u);comp_rec_put16(p+4u,1u);
    comp_rec_put16(p+6u,96u);comp_rec_put32(p+8u,d->recording_id);
    comp_rec_put64(p+12u,d->format_epoch);comp_rec_put64(p+20u,d->session_id);
    comp_rec_put32(p+28u,d->segment_index);comp_rec_put64(p+32u,d->sample_offset);
    comp_rec_put32(p+40u,comp_segment_provenance_extent(e));comp_rec_put32(p+44u,e->reserved_bytes);
    memcpy(p+48u,d->device_uid,12u);p[60]=d->codec;p[61]=d->source_mode;
    comp_rec_put32(p+64u,e->started_unix_s);return comp_wba_recording_crc32(0u,p,(uint32_t)sizeof(p));
}

static bool provenance_valid(const comp_segment_entry_t *e,const uint8_t *p,bool committed)
{
    const comp_rec_v2_descriptor_t *d=&e->descriptor;
    return memcmp(p,"CSP2",4u)==0 && p[4]==1u && p[5]==0u && p[6]==96u && p[7]==0u &&
        comp_rec_get32(p+8u)==d->recording_id && comp_rec_get64(p+12u)==d->format_epoch &&
        comp_rec_get64(p+20u)==d->session_id && comp_rec_get32(p+28u)==d->segment_index &&
        comp_rec_get64(p+32u)==d->sample_offset && comp_rec_get32(p+40u)==comp_segment_provenance_extent(e) &&
        comp_rec_get32(p+44u)==e->reserved_bytes && memcmp(p+48u,d->device_uid,12u)==0 &&
        p[60]==d->codec && p[61]==d->source_mode && uniform(p+62u,2u,255u) &&
        comp_rec_get32(p+64u)==e->started_unix_s && uniform(p+68u,24u,255u) &&
        comp_rec_get32(p+PROVENANCE_CRC)==binding(e) &&
        comp_rec_get32(p+PROVENANCE_CRC)==comp_rec_crc(p,PROVENANCE_CRC) &&
        uniform(p+96u,156u,255u) && uniform(p+COMMIT,4u,committed?0u:255u);
}

static uint32_t page_crc(uint32_t bind,uint32_t index,uint8_t length,const uint8_t *p)
{
    uint8_t identity[9];comp_rec_put32(identity,bind);comp_rec_put32(identity+4u,index);
    identity[8]=length;
    return comp_wba_recording_crc32(comp_wba_recording_crc32(0u,identity,sizeof(identity)),
                                    p,COMP_SEG_AUDIO_DATA_BYTES);
}

static bool page_committed(const uint8_t *p)
{
    return p[COMMIT]>0u && p[COMMIT]<=COMP_SEG_AUDIO_DATA_BYTES &&
        (uint8_t)(p[COMMIT]^p[COMMIT+1u])==255u && p[COMMIT+2u]==0xc3u && p[COMMIT+3u]==0x5au;
}

static bool page_valid(uint32_t bind,uint32_t index,const uint8_t *p,uint8_t length,bool commit)
{
    return length && length<=COMP_SEG_AUDIO_DATA_BYTES &&
        uniform(p+length,COMP_SEG_AUDIO_DATA_BYTES-length,255u) &&
        comp_rec_get32(p+AUDIO_CRC)==page_crc(bind,index,length,p) &&
        (commit?(page_committed(p)&&p[COMMIT]==length):uniform(p+COMMIT,4u,255u));
}

static uint32_t page_address(uint32_t base,const comp_segment_entry_t *e,uint32_t index)
{ return base+e->extent_offset+COMP_SEG_AUDIO_PREFIX_BYTES+index*256u; }

static comp_segment_result_t failure(comp_segment_audio_t *a,comp_segment_result_t r)
{a->failed=true;return r;}

/* Retry only a port-qualified, fast read failure. A writer owns its own
 * retry count even when the future and active pages are interleaved. */
static comp_segment_result_t read_retry(comp_segment_audio_t *a)
{
    if(a->read_retries<2u){a->read_retries++;return COMP_SEG_PENDING;}
    return failure(a,COMP_SEG_IO_ERROR);
}

comp_segment_result_t comp_segment_audio_prepare_begin(comp_segment_audio_t *a,
    const comp_segment_audio_port_t *port,const comp_segment_entry_t *e,uint32_t base,
    uint8_t page[COMP_SEGMENT_PAGE_BYTES])
{
    if (!a || !port || !port->read || !port->program || !page || !valid_reservation(e,base))
        return COMP_SEG_BAD_ARGUMENT;
    /* Object is initialized/explicitly recovered by its owner, never reset
     * while a program might still have modified media. */
    if (a->phase || a->prepared || a->failed) return COMP_SEG_BAD_STATE;
    memset(a,0,sizeof(*a));a->port=*port;a->entry=e;a->data_base=base;a->page=page;
    provenance(e,page);a->binding_crc=comp_rec_get32(page+PROVENANCE_CRC);
    a->phase=PROVENANCE_BODY;return COMP_SEG_PENDING;
}

comp_segment_result_t comp_segment_audio_append_begin(comp_segment_audio_t *a,const uint8_t *p,uint8_t length)
{
    if (!a || !p || !length || length>COMP_SEG_AUDIO_DATA_BYTES) return COMP_SEG_BAD_ARGUMENT;
    if (a->failed || !a->prepared || a->phase ||
        a->committed_bytes!=a->pages*COMP_SEG_AUDIO_DATA_BYTES) return COMP_SEG_BAD_STATE;
    if (a->pages>=a->entry->reserved_bytes/256u-1u) return COMP_SEG_FULL;
    memset(a->page,255,256u);memcpy(a->page,p,length);a->length=length;
    comp_rec_put32(a->page+AUDIO_CRC,page_crc(a->binding_crc,a->pages,length,a->page));
    a->phase=PAGE_BODY;return COMP_SEG_PENDING;
}

comp_segment_result_t comp_segment_audio_cancel_begin(comp_segment_audio_t *a,comp_segment_catalog_t *c)
{
    if (!a || !c) return COMP_SEG_BAD_ARGUMENT;
    if (!a->prepared || a->failed || a->claimed || a->phase || a->pages || a->committed_bytes ||
        !valid_reservation(a->entry,a->data_base) || !c->mounted ||
        c->data_base!=a->data_base || c->epoch!=a->entry->descriptor.format_epoch ||
        memcmp(c->uid,a->entry->descriptor.device_uid,12u)!=0) return COMP_SEG_BAD_STATE;
    a->cancellation=c;a->phase=CANCEL_PROVENANCE;return COMP_SEG_PENDING;
}

static comp_segment_result_t cancel_poll(comp_segment_audio_t *a,
    comp_segment_result_t (*poll)(void *,comp_segment_catalog_t *),void *context)
{
    comp_segment_result_t result;
    if (a->phase==CANCEL_PROVENANCE || a->phase==CANCEL_PAGES) {
        uint32_t at=a->phase==CANCEL_PROVENANCE?a->data_base+a->entry->extent_offset:
            page_address(a->data_base,a->entry,a->pages);
        result=a->port.read(a->port.context,at,a->page,256u);
        if (result==COMP_SEG_RETRYABLE_READ) return read_retry(a);
        if (result==COMP_SEG_PENDING) return result;
        if (result!=COMP_SEG_OK) return failure(a,result);
        a->read_retries=0u;
        if (a->phase==CANCEL_PROVENANCE) {
            if (!provenance_valid(a->entry,a->page,true)) return failure(a,COMP_SEG_CORRUPT);
            a->phase=CANCEL_PAGES;
        } else {
            if (!uniform(a->page,256u,255u)) return failure(a,COMP_SEG_CORRUPT);
            if (++a->pages==a->entry->reserved_bytes/256u-1u) a->phase=CANCEL_BEGIN;
        }
        return COMP_SEG_PENDING;
    }
    if (a->phase==CANCEL_BEGIN) {
        if (a->cancellation->phase) return COMP_SEG_PENDING;
        result=comp_segment_catalog_cancel_unwritten_begin(a->cancellation,a->entry);
        if (result!=COMP_SEG_PENDING) return failure(a,result);
        a->phase=CANCEL_DIRECTORY;return result;
    }
    result=poll?poll(context,a->cancellation):comp_segment_catalog_poll(a->cancellation);
    if (result==COMP_SEG_PENDING) return result;
    if (result!=COMP_SEG_OK) return failure(a,result);
    a->phase=IDLE;a->pages=0u;a->prepared=false;a->canceled=true;
    return COMP_SEG_OK;
}

comp_segment_result_t comp_segment_audio_cancel_poll(comp_segment_audio_t *a,
    comp_segment_result_t (*poll)(void *,comp_segment_catalog_t *),void *context)
{
    if(!a||!poll)return COMP_SEG_BAD_ARGUMENT;
    if(a->failed)return COMP_SEG_BAD_STATE;
    if(a->canceled&&!a->phase)return COMP_SEG_OK;
    if(!a->cancellation||a->phase<CANCEL_PROVENANCE)return COMP_SEG_BAD_STATE;
    return cancel_poll(a,poll,context);
}

comp_segment_result_t comp_segment_audio_poll(comp_segment_audio_t *a)
{
    if (!a) return COMP_SEG_BAD_ARGUMENT;
    if (a->failed) return COMP_SEG_BAD_STATE;
    if (!a->phase) return (a->prepared || a->canceled)?COMP_SEG_OK:COMP_SEG_BAD_STATE;
    if (a->phase>=CANCEL_PROVENANCE) return cancel_poll(a,NULL,NULL);
    uint32_t at=a->data_base+a->entry->extent_offset;
    comp_segment_result_t r;uint8_t next=0u;
    if (a->phase>=PAGE_BODY) at=page_address(a->data_base,a->entry,a->pages);
    switch (a->phase) {
    case PROVENANCE_BODY:
    case PAGE_BODY:
        r=a->port.program(a->port.context,at,a->page,COMMIT);
        next=a->phase==PROVENANCE_BODY?PROVENANCE_VERIFY:PAGE_VERIFY;break;
    case PROVENANCE_VERIFY:
    case PAGE_VERIFY:
        r=a->port.read(a->port.context,at,a->page,256u);
        if(r==COMP_SEG_RETRYABLE_READ)return read_retry(a);
        if(r==COMP_SEG_OK)a->read_retries=0u;
        if (r==COMP_SEG_OK && !(a->phase==PROVENANCE_VERIFY?
            provenance_valid(a->entry,a->page,false):page_valid(a->binding_crc,a->pages,a->page,a->length,false)))
            return failure(a,COMP_SEG_CORRUPT);
        next=a->phase==PROVENANCE_VERIFY?PROVENANCE_COMMIT:PAGE_COMMIT;break;
    case PROVENANCE_COMMIT:
    case PAGE_COMMIT:
        /* Set the commit slice once before asking the port. A healthy pending
         * port retries identical bytes and cannot have accepted a program. */
        if (a->phase==PROVENANCE_COMMIT) memset(a->page+COMMIT,0,4u);
        else {a->page[COMMIT]=a->length;a->page[COMMIT+1u]=(uint8_t)~a->length;
              a->page[COMMIT+2u]=0xc3u;a->page[COMMIT+3u]=0x5au;}
        r=a->port.program(a->port.context,at+COMMIT,a->page+COMMIT,4u);
        next=a->phase==PROVENANCE_COMMIT?PROVENANCE_COMMIT_VERIFY:PAGE_COMMIT_VERIFY;break;
    case PROVENANCE_COMMIT_VERIFY:
    case PAGE_COMMIT_VERIFY:
        r=a->port.read(a->port.context,at,a->page,256u);
        if(r==COMP_SEG_RETRYABLE_READ)return read_retry(a);
        if(r==COMP_SEG_OK)a->read_retries=0u;
        if (r==COMP_SEG_OK && !(a->phase==PROVENANCE_COMMIT_VERIFY?
            provenance_valid(a->entry,a->page,true):page_valid(a->binding_crc,a->pages,a->page,a->length,true)))
            return failure(a,COMP_SEG_CORRUPT);
        if (r==COMP_SEG_OK) {
            if (a->phase==PROVENANCE_COMMIT_VERIFY) a->prepared=true;
            else {a->pages++;a->committed_bytes+=a->length;}
        }
        break;
    default:return failure(a,COMP_SEG_BAD_STATE);
    }
    if (r==COMP_SEG_PENDING) return r;
    if (r!=COMP_SEG_OK) return failure(a,r);
    a->phase=next;return next?COMP_SEG_PENDING:COMP_SEG_OK;
}

comp_segment_result_t comp_segment_audio_read_page(const comp_segment_audio_port_t *port,
    const comp_segment_entry_t *e,uint32_t base,uint32_t index,
    uint8_t page[COMP_SEGMENT_PAGE_BYTES],uint8_t *length)
{
    if (!port || !port->read || !e || !page || !length ||
        !comp_segment_audio_capacity(e->reserved_bytes) || index>=e->reserved_bytes/256u-1u ||
        base>UINT32_MAX-e->extent_offset || e->reserved_bytes>UINT32_MAX-base-e->extent_offset)
        return COMP_SEG_BAD_ARGUMENT;
    comp_segment_result_t r=port->read(port->context,page_address(base,e,index),page,256u);
    if (r!=COMP_SEG_OK) return r;
    if (!page_committed(page)) return COMP_SEG_NOT_FOUND;
    if (!page_valid(binding(e),index,page,page[COMMIT],true)) return COMP_SEG_CORRUPT;
    *length=page[COMMIT];return COMP_SEG_OK;
}

comp_segment_result_t comp_segment_audio_recover_begin(comp_segment_audio_recovery_t *r,
    const comp_segment_audio_port_t *port,const comp_segment_entry_t *e,uint32_t base,
    uint8_t page[COMP_SEGMENT_PAGE_BYTES])
{
    if (!r || !port || !port->read || !page || !valid_reservation(e,base)) return COMP_SEG_BAD_ARGUMENT;
    if (r->phase || r->failed) return COMP_SEG_BAD_STATE;
    memset(r,0,sizeof(*r));r->port=*port;r->entry=e;r->data_base=base;r->page=page;
    companion_sha256_init(&r->prefix_sha);r->complete_sha=r->prefix_sha;
    r->phase=REC_PROVENANCE;return COMP_SEG_PENDING;
}

comp_segment_result_t comp_segment_audio_recover_owned_begin(comp_segment_audio_recovery_t *r,
    const comp_segment_audio_port_t *port,const comp_segment_entry_t *e,uint32_t base,uint8_t page[256])
{
    comp_segment_result_t result=comp_segment_audio_recover_begin(r,port,e,base,page);
    if(result==COMP_SEG_PENDING){r->allow_unwritten=true;r->empty_verified=true;}
    return result;
}

static bool parse_byte(comp_segment_audio_recovery_t *r,uint8_t byte)
{
    static const uint8_t header[12]={'C','O','P','1',1u,1u,20u,0u,0x80u,0x3eu,0u,0u};
    companion_sha256_update(&r->prefix_sha,&byte,1u);
    r->crc=~comp_rec_crc_step(~r->crc,&byte,1u);r->bytes++;
    if (r->header_bytes<12u) {
        uint8_t at=r->header_bytes++;
        if(at==4u) {
            if(byte!=1u&&byte!=COMP_REC_TIMELINE_SCHEMA&&byte!=COMP_REC_BOOKMARK_SCHEMA&&byte!=COMP_REC_CODEC_BOUNDARY_SCHEMA&&byte!=COMP_REC_AUDIO_PROFILE_SCHEMA)return false;
            r->container_schema=byte;
        } else if(at==7u) {
            if(byte!=(r->container_schema==COMP_REC_AUDIO_PROFILE_SCHEMA?15u:r->container_schema>=COMP_REC_CODEC_BOUNDARY_SCHEMA?7u:r->container_schema==COMP_REC_BOOKMARK_SCHEMA?3u:r->container_schema==COMP_REC_TIMELINE_SCHEMA?1u:0u))return false;
        } else if(byte!=header[at])return false;
    } else if (r->packet_remaining) {
        if (--r->packet_remaining==0u) {
            if(r->codec_end_seen)r->codec_drain_pending=false;
            r->frames++;r->complete_bytes=r->bytes;r->complete_crc=r->crc;
            r->complete_sha=r->prefix_sha;
        }
    } else if(!r->length_bytes&&r->container_schema>=COMP_REC_TIMELINE_SCHEMA&&byte==255u) {
        if(r->container_schema==COMP_REC_AUDIO_PROFILE_SCHEMA&&!r->audio_profile_seen)return false;
        r->complete_bytes=r->bytes;r->complete_crc=r->crc;r->complete_sha=r->prefix_sha;
    } else if (!r->length_bytes) {
        if(r->container_schema==COMP_REC_AUDIO_PROFILE_SCHEMA&&!r->audio_profile_seen)return false;
        if(r->container_schema>=COMP_REC_CODEC_BOUNDARY_SCHEMA) {
            if(!r->codec_config_seen||(r->codec_end_seen&&!r->codec_drain_pending))return false;
            if((r->pause_open||r->ended_paused)&&!r->codec_drain_pending)return false;
        } else if(r->pause_open||r->ended_paused)return false;
        r->packet_length=byte;r->length_bytes=1u;
    }
    else {
        r->packet_length=(uint16_t)(r->packet_length|((uint16_t)byte<<8u));
        if (r->packet_length!=COMP_SEG_AUDIO_FRAME_BYTES-2u) return false;
        r->packet_remaining=r->packet_length;r->length_bytes=0u;
    }
    return true;
}

static bool parse_page(comp_segment_audio_recovery_t *r,const uint8_t *p,uint8_t length)
{
    for(uint16_t i=0u;i<length;i++) {
        if(r->container_schema>=COMP_REC_TIMELINE_SCHEMA&&r->header_bytes==12u&&
           !r->packet_remaining&&!r->length_bytes&&p[i]==0u&&i+1u<length&&p[i+1u]==0u) {
            if(r->container_schema==COMP_REC_AUDIO_PROFILE_SCHEMA&&(uint16_t)(length-i)>=COMP_REC_AUDIO_PROFILE_BYTES&&
               !memcmp(p+i+2u,"APM1",4u)) {
                comp_rec_audio_profile_t profile;
                if(r->bytes!=44u||!r->codec_config_seen||r->audio_profile_seen||r->frames||
                   !comp_rec_audio_profile_decode(p+i,(size_t)length-i,&profile))return false;
                r->audio_profile_seen=true;
                companion_sha256_update(&r->prefix_sha,p+i,COMP_REC_AUDIO_PROFILE_BYTES);
                r->crc=~comp_rec_crc_step(~r->crc,p+i,COMP_REC_AUDIO_PROFILE_BYTES);
                r->bytes+=COMP_REC_AUDIO_PROFILE_BYTES;r->complete_bytes=r->bytes;
                r->complete_crc=r->crc;r->complete_sha=r->prefix_sha;
                i+=(uint16_t)(COMP_REC_AUDIO_PROFILE_BYTES-1u);continue;
            }
            if(r->container_schema>=COMP_REC_CODEC_BOUNDARY_SCHEMA&&(uint16_t)(length-i)>=COMP_REC_CODEC_BOUNDARY_BYTES&&
               !memcmp(p+i+2u,"CDB1",4u)) {
                comp_rec_codec_boundary_t e;
                uint64_t current=r->entry->descriptor.sample_offset+(uint64_t)r->frames*320u;
                if(!comp_rec_codec_boundary_decode(p+i,(size_t)length-i,&e))return false;
                if(e.kind==COMP_REC_CODEC_CONFIG) {
                    if(r->bytes!=12u||r->codec_config_seen||e.encoded_samples!=current)return false;
                    r->codec_config_seen=true;r->codec_delay=(uint8_t)e.delay_samples;
                } else {
                    if(r->bytes%COMP_SEG_AUDIO_DATA_BYTES||!r->codec_config_seen||r->codec_end_seen||
                       (r->container_schema==COMP_REC_AUDIO_PROFILE_SCHEMA&&!r->audio_profile_seen)||
                       e.delay_samples!=r->codec_delay||e.encoded_samples!=current+320u||
                       (e.valid_source_samples!=current&&e.valid_source_samples!=current+160u))return false;
                    r->codec_end_seen=true;r->codec_drain_pending=true;
                }
                companion_sha256_update(&r->prefix_sha,p+i,COMP_REC_CODEC_BOUNDARY_BYTES);
                r->crc=~comp_rec_crc_step(~r->crc,p+i,COMP_REC_CODEC_BOUNDARY_BYTES);
                r->bytes+=COMP_REC_CODEC_BOUNDARY_BYTES;r->complete_bytes=r->bytes;
                r->complete_crc=r->crc;r->complete_sha=r->prefix_sha;
                i+=(uint16_t)(COMP_REC_CODEC_BOUNDARY_BYTES-1u);continue;
            }
            comp_rec_timeline_event_t e;
            if(r->bytes%COMP_SEG_AUDIO_DATA_BYTES||(uint16_t)(length-i)<COMP_REC_TIMELINE_BYTES||
               !comp_rec_timeline_decode(p+i,(size_t)length-i,&e)||
               (r->container_schema==COMP_REC_AUDIO_PROFILE_SCHEMA&&!r->audio_profile_seen)||
               (e.kind==COMP_REC_TIMELINE_BOOKMARK&&r->container_schema<COMP_REC_BOOKMARK_SCHEMA)||
               (r->container_schema>=COMP_REC_CODEC_BOUNDARY_SCHEMA&&(!r->codec_config_seen||r->codec_end_seen))||
               e.sequence<=(e.kind==COMP_REC_TIMELINE_BOOKMARK?r->bookmark_sequence:r->timeline_sequence)||e.elapsed_ms<r->timeline_ms||
               e.sample_offset!=r->entry->descriptor.sample_offset+(uint64_t)r->frames*320u||
               r->ended_paused)return false;
            if(e.kind==COMP_REC_TIMELINE_BOOKMARK) {
                if(e.sequence>COMP_REC_BOOKMARK_LIMIT)return false;
                r->bookmark_sequence=e.sequence;
            } else if(e.kind==COMP_REC_TIMELINE_PAUSE) {
                if(r->pause_open)return false;
                r->pause_open=true;
            } else {
                if(!r->pause_open)return false;
                r->pause_open=false;r->ended_paused=e.kind==COMP_REC_TIMELINE_END_PAUSED;
            }
            companion_sha256_update(&r->prefix_sha,p+i,COMP_REC_TIMELINE_BYTES);
            r->crc=~comp_rec_crc_step(~r->crc,p+i,COMP_REC_TIMELINE_BYTES);
            r->bytes+=COMP_REC_TIMELINE_BYTES;r->complete_bytes=r->bytes;
            r->complete_crc=r->crc;r->complete_sha=r->prefix_sha;
            if(e.kind!=COMP_REC_TIMELINE_BOOKMARK)r->timeline_sequence=e.sequence;
            r->timeline_ms=e.elapsed_ms;
            i+=(uint16_t)(COMP_REC_TIMELINE_BYTES-1u);
        } else if(!parse_byte(r,p[i]))return false;
    }
    return true;
}

static comp_segment_result_t recovery_failure(comp_segment_audio_recovery_t *r,comp_segment_result_t result)
{r->failed=true;return result;}

comp_segment_result_t comp_segment_audio_recover_poll(comp_segment_audio_recovery_t *r)
{
    if (!r) return COMP_SEG_BAD_ARGUMENT;
    if (r->failed || !r->phase) return COMP_SEG_BAD_STATE;
    if (r->phase==REC_DONE) return COMP_SEG_OK;
    uint32_t at=r->phase==REC_PROVENANCE?r->data_base+r->entry->extent_offset:
        page_address(r->data_base,r->entry,r->pages);
    comp_segment_result_t result=r->port.read(r->port.context,at,r->page,256u);
    if (result==COMP_SEG_PENDING) return result;
    if (result!=COMP_SEG_OK) return recovery_failure(r,result);
    if (r->phase==REC_PROVENANCE) {
        if (!provenance_valid(r->entry,r->page,true)) {
            if(!r->allow_unwritten || !(uniform(r->page,256u,255u)||provenance_valid(r->entry,r->page,false)))
                return recovery_failure(r,COMP_SEG_CORRUPT);
            r->unwritten_provenance=true;
        }
        r->phase=REC_PAGES;return COMP_SEG_PENDING;
    }
    bool blank=uniform(r->page,256u,255u);
    if(!blank)r->empty_verified=false;
    if(r->unwritten_provenance) {
        if(!blank)return recovery_failure(r,COMP_SEG_CORRUPT);
    } else if (r->prefix_ended) {
        if (!uniform(r->page,256u,255u)) return recovery_failure(r,COMP_SEG_CORRUPT);
    } else if (!page_committed(r->page)) {
        /* An uncertain final body/commit may be nonblank. It is never counted
         * as audio; all later pages must still be blank. */
        r->prefix_ended=true;
    } else {
        uint8_t length=r->page[COMMIT];
        if (!page_valid(binding(r->entry),r->pages,r->page,length,true))
            return recovery_failure(r,COMP_SEG_CORRUPT);
        if(!parse_page(r,r->page,length))return recovery_failure(r,COMP_SEG_CORRUPT);
        if (length<COMP_SEG_AUDIO_DATA_BYTES) r->prefix_ended=true;
    }
    if (++r->pages==r->entry->reserved_bytes/256u-1u) {r->phase=REC_DONE;return COMP_SEG_OK;}
    return COMP_SEG_PENDING;
}

bool comp_segment_audio_recovered(const comp_segment_audio_recovery_t *r,
    uint32_t *bytes,uint32_t *frames,uint32_t *crc,uint8_t sha[32])
{
    if (!r || r->failed || r->phase!=REC_DONE || !bytes || !frames || !crc || !sha || !r->frames)
        return false;
    companion_sha256_t final=r->complete_sha;companion_sha256_final(&final,sha);
    *bytes=r->complete_bytes;*frames=r->frames;*crc=r->complete_crc;return true;
}

bool comp_segment_audio_recovery_empty_verified(const comp_segment_audio_recovery_t *r)
{return r&&r->allow_unwritten&&!r->failed&&r->phase==REC_DONE&&r->empty_verified&&!r->frames&&!r->bytes;}
