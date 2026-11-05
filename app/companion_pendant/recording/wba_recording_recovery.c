#include "wba_recording_recovery.h"

enum {SESSION_SCAN=1,SESSION_WAIT,RECLAIM_SCAN,RECLAIM_WAIT,COMPACT_WAIT,WRITING_SCAN,AUDIO_WAIT,LOOK_SCAN,LOOK_AUDIO,
      SEAL_WAIT,CANCEL_WAIT,DONE,FAILED};

static comp_segment_result_t discard_read(void *context,comp_segment_catalog_t *catalog,uint8_t index,comp_segment_entry_t *entry,comp_segment_discard_intent_t *intent)
{return comp_wba_segment_storage_entry_intent((comp_wba_segment_storage_t *)context,catalog,index,entry,intent);}
static comp_segment_result_t discard_poll(void *context,comp_segment_catalog_t *catalog)
{return comp_wba_segment_storage_catalog_poll((comp_wba_segment_storage_t *)context,catalog);}
static comp_segment_result_t fail(comp_wba_recording_recovery_t *r,comp_segment_result_t result)
{r->result=result;r->phase=FAILED;return result;}
static comp_segment_result_t recover_audio(comp_wba_recording_recovery_t *r,const comp_segment_entry_t *entry)
{
    memset(&r->audio,0,sizeof(r->audio));
    comp_segment_audio_port_t port=comp_wba_segment_storage_audio_port(r->storage);
    return comp_segment_audio_recover_owned_begin(&r->audio,&port,entry,r->catalog->data_base,r->page);
}
static comp_segment_result_t advance(comp_wba_recording_recovery_t *r)
{r->phase=WRITING_SCAN;return COMP_SEG_PENDING;}
static comp_segment_result_t seal(comp_wba_recording_recovery_t *r)
{
    comp_rec_v2_descriptor_t *d=&r->entry.descriptor;
    d->flags=(uint8_t)(COMP_REC_V2_SEALED|COMP_REC_V2_RECOVERED|(r->last?COMP_REC_V2_LAST:0u));
    d->total_segments=r->last?d->segment_index+1u:0u;
    comp_segment_result_t result=comp_segment_catalog_put_begin(r->catalog,&r->entry);
    if(result==COMP_SEG_PENDING)r->phase=SEAL_WAIT;
    return result;
}
comp_segment_result_t comp_wba_recording_recovery_begin(comp_wba_recording_recovery_t *r,
    comp_wba_segment_storage_t *s,comp_segment_catalog_t *c,uint8_t page[256])
{
    if(!r||!s||!c||!page)return COMP_SEG_BAD_ARGUMENT;
    if(!c->mounted||c->phase||s->poisoned||s->nor->erase_active||s->data_base!=c->data_base||
       s->data_bytes!=c->data_bytes||s->banks[0]!=c->banks[0]||s->banks[1]!=c->banks[1])return COMP_SEG_BAD_STATE;
    memset(r,0,sizeof(*r));r->storage=s;r->catalog=c;r->page=page;
    r->phase=SESSION_SCAN;r->result=COMP_SEG_PENDING;return COMP_SEG_PENDING;
}
comp_segment_result_t comp_wba_recording_recovery_poll(comp_wba_recording_recovery_t *r)
{
    if(!r)return COMP_SEG_BAD_ARGUMENT;
    if(r->phase==DONE||r->phase==FAILED)return r->result;
    if(!r->phase)return COMP_SEG_BAD_STATE;
    comp_segment_result_t result;
    switch(r->phase) {
    case SESSION_SCAN:
        if(r->scan==64u){r->scan=0u;r->phase=RECLAIM_SCAN;return COMP_SEG_PENDING;}
        result=comp_wba_segment_storage_entry_intent(r->storage,r->catalog,r->scan,&r->entry,&r->discard.anchor.intent);
        if(result==COMP_SEG_PENDING)return result;
        if(result==COMP_SEG_NOT_FOUND){r->scan++;return COMP_SEG_PENDING;}
        if(result!=COMP_SEG_OK)return fail(r,result);
        if(r->entry.state!=COMP_SEG_SESSION_DISCARD){r->scan++;return COMP_SEG_PENDING;}
        result=comp_discard_worker_resume(&r->discard,r->catalog,discard_read,discard_poll,
                                          r->storage,r->scan,&r->entry,&r->discard.anchor.intent);
        if(result==COMP_SEG_PENDING)r->phase=SESSION_WAIT;
        break;
    case SESSION_WAIT:
        result=comp_discard_worker_poll(&r->discard);
        if(result==COMP_SEG_OK){r->reclaimed++;r->scan++;r->phase=SESSION_SCAN;return COMP_SEG_PENDING;}
        break;
    case RECLAIM_SCAN:
        if(r->scan==64u){
            r->scan=0u;result=comp_segment_catalog_compact_legacy_begin(r->catalog);
            if(result==COMP_SEG_PENDING){r->phase=COMPACT_WAIT;return result;}
            if(result!=COMP_SEG_OK)return fail(r,result);
            r->phase=WRITING_SCAN;return COMP_SEG_PENDING;
        }
        result=comp_wba_segment_storage_entry(r->storage,r->catalog,r->scan,&r->entry);
        if(result==COMP_SEG_PENDING)return result;
        r->scan++;
        if(result==COMP_SEG_NOT_FOUND)return COMP_SEG_PENDING;
        if(result!=COMP_SEG_OK)return fail(r,result);
        if(r->entry.state==COMP_SEG_DISCARDING)
            result=comp_segment_catalog_discard_begin(r->catalog,&r->entry,r->catalog->generation);
        else {
            if(r->entry.state!=COMP_SEG_ACKED&&r->entry.state!=COMP_SEG_ERASING)return COMP_SEG_PENDING;
            result=comp_segment_catalog_reclaim_begin(r->catalog,&r->entry);
        }
        if(result==COMP_SEG_PENDING)r->phase=RECLAIM_WAIT;
        break;
    case RECLAIM_WAIT:
        result=comp_wba_segment_storage_catalog_poll(r->storage,r->catalog);
        if(result==COMP_SEG_OK){r->reclaimed++;r->phase=RECLAIM_SCAN;return COMP_SEG_PENDING;}
        break;
    case COMPACT_WAIT:
        result=comp_wba_segment_storage_catalog_poll(r->storage,r->catalog);
        if(result==COMP_SEG_OK){r->phase=WRITING_SCAN;return COMP_SEG_PENDING;}
        break;
    case WRITING_SCAN:
        if(r->scan==64u){r->phase=DONE;r->result=COMP_SEG_OK;return COMP_SEG_OK;}
        result=comp_wba_segment_storage_entry(r->storage,r->catalog,r->scan,&r->entry);
        if(result==COMP_SEG_PENDING)return result;
        r->scan++;
        if(result==COMP_SEG_NOT_FOUND)return COMP_SEG_PENDING;
        if(result!=COMP_SEG_OK)return fail(r,result);
        if(r->entry.state!=COMP_SEG_WRITING)return COMP_SEG_PENDING;
        result=recover_audio(r,&r->entry);
        if(result==COMP_SEG_PENDING)r->phase=AUDIO_WAIT;
        break;
    case AUDIO_WAIT:
        result=comp_segment_audio_recover_poll(&r->audio);
        if(result==COMP_SEG_CORRUPT){r->unresolved++;return advance(r);}
        if(result!=COMP_SEG_OK)break;
        if(comp_segment_audio_recovery_empty_verified(&r->audio)) {
            /* Only exclusive boot's whole-extent blank proof can release this
             * unpublished reservation. No physical audio is erased. */
            result=comp_segment_catalog_cancel_unwritten_begin(r->catalog,&r->entry);
            if(result==COMP_SEG_PENDING)r->phase=CANCEL_WAIT;
            break;
        }
        {
            comp_rec_v2_descriptor_t *d=&r->entry.descriptor;uint32_t frames;
            if(!comp_segment_audio_recovered(&r->audio,&d->encoded_length,&frames,&d->content_crc32,d->sha256)) {
                r->unresolved++;return advance(r);
            }
            d->sample_count=(uint64_t)frames*320u;d->sync_state=1u;
            r->entry.state=COMP_SEG_UNSYNCED;r->last=true;r->look=0u;r->phase=LOOK_SCAN;
            return COMP_SEG_PENDING;
        }
    case LOOK_SCAN:
        if(r->look==64u){result=seal(r);break;}
        result=comp_wba_segment_storage_entry(r->storage,r->catalog,r->look,&r->candidate);
        if(result==COMP_SEG_PENDING)return result;
        r->look++;
        if(result==COMP_SEG_NOT_FOUND)return COMP_SEG_PENDING;
        if(result!=COMP_SEG_OK)return fail(r,result);
        if(r->candidate.descriptor.session_id!=r->entry.descriptor.session_id||
           r->candidate.descriptor.segment_index<=r->entry.descriptor.segment_index)return COMP_SEG_PENDING;
        if(r->candidate.state!=COMP_SEG_WRITING){r->last=false;result=seal(r);break;}
        /* A later unused future does not create an empty terminal segment.
         * A later uncertain/nonempty tail prevents claiming a complete end. */
        result=recover_audio(r,&r->candidate);
        if(result==COMP_SEG_PENDING)r->phase=LOOK_AUDIO;
        break;
    case LOOK_AUDIO:
        result=comp_segment_audio_recover_poll(&r->audio);
        if(result==COMP_SEG_CORRUPT||result==COMP_SEG_OK) {
            if(result==COMP_SEG_OK&&comp_segment_audio_recovery_empty_verified(&r->audio)) {
                r->phase=LOOK_SCAN;return COMP_SEG_PENDING;
            }
            r->last=false;result=seal(r);
        }
        break;
    case SEAL_WAIT:
    case CANCEL_WAIT:
        result=comp_wba_segment_storage_catalog_poll(r->storage,r->catalog);
        if(result==COMP_SEG_OK) {
            if(r->phase==SEAL_WAIT)r->sealed++;else r->canceled++;
            return advance(r);
        }
        break;
    default:return fail(r,COMP_SEG_BAD_STATE);
    }
    if(result!=COMP_SEG_PENDING)return fail(r,result);
    return COMP_SEG_PENDING;
}
bool comp_wba_recording_recovery_ready(const comp_wba_recording_recovery_t *r)
{return r&&r->phase==DONE&&r->result==COMP_SEG_OK&&!r->unresolved;}
