#include "wba_segment_discard_preview.h"

enum { PREVIEW_FIND=1,PREVIEW_GROUP,PREVIEW_DONE };
static comp_segment_result_t finish(comp_discard_preview_t *p,comp_segment_result_t r)
{p->phase=PREVIEW_DONE;p->result=r;return r;}
comp_segment_result_t comp_discard_preview_begin(comp_discard_preview_t *p,comp_segment_catalog_t *c,comp_discard_entry_fn read,void *context)
{
    if(!p||!c||!read)return COMP_SEG_BAD_ARGUMENT;
    if(!c->mounted||c->phase)return COMP_SEG_BAD_STATE;
    memset(p,0,sizeof(*p));p->catalog=c;p->read=read;p->context=context;
    p->epoch=c->epoch;p->generation=c->generation;memcpy(p->uid,c->uid,12u);
    p->oldest_id=UINT32_MAX;p->phase=PREVIEW_FIND;p->result=COMP_SEG_PENDING;return COMP_SEG_PENDING;
}
comp_segment_result_t comp_discard_preview_poll(comp_discard_preview_t *p)
{
    if(!p||!p->catalog||!p->read)return COMP_SEG_BAD_ARGUMENT;
    if(p->phase==PREVIEW_DONE)return p->result;
    comp_segment_catalog_t *c=p->catalog;
    if(!c->mounted)return finish(p,COMP_SEG_BAD_STATE);
    if(c->generation!=p->generation||c->epoch!=p->epoch||memcmp(c->uid,p->uid,12u))
        return finish(p,COMP_SEG_STALE_SNAPSHOT);
    if(c->phase)return COMP_SEG_PENDING;
    if(p->slot==COMP_SEGMENT_CAPACITY) {
        if(p->phase==PREVIEW_FIND) {
            if(!p->session_id)return finish(p,COMP_SEG_NOT_FOUND);
            p->slot=0u;p->phase=PREVIEW_GROUP;return COMP_SEG_PENDING;
        }
        if(p->phase!=PREVIEW_GROUP||!p->segments||!p->last_seen||p->max_index!=p->last_index)return finish(p,COMP_SEG_BAD_STATE);
        return finish(p,COMP_SEG_OK);
    }
    comp_segment_entry_t e;comp_segment_result_t r=p->read(p->context,c,p->slot,&e,NULL);
    if(r==COMP_SEG_PENDING)return r;
    if(r==COMP_SEG_NOT_FOUND){p->slot++;return COMP_SEG_PENDING;}
    if(r!=COMP_SEG_OK)return finish(p,r);
    /* A callback must not accept a changing directory while scanning. */
    if(c->generation!=p->generation||c->epoch!=p->epoch||memcmp(c->uid,p->uid,12u))
        return finish(p,COMP_SEG_STALE_SNAPSHOT);
    p->slot++;
    if(p->phase==PREVIEW_FIND) {
        if(e.state==COMP_SEG_UNSYNCED&&e.descriptor.recording_id<p->oldest_id) {
            p->oldest_id=e.descriptor.recording_id;p->session_id=e.descriptor.session_id;
        }
        return COMP_SEG_PENDING;
    }
    if(p->phase!=PREVIEW_GROUP)return finish(p,COMP_SEG_BAD_STATE);
    if(e.descriptor.session_id!=p->session_id)return COMP_SEG_PENDING;
    if(e.state!=COMP_SEG_UNSYNCED)return finish(p,COMP_SEG_BAD_STATE);
    if(!comp_rec_v2_valid(&e.descriptor)||e.descriptor.sync_state!=1u ||
       e.descriptor.format_epoch!=p->epoch||memcmp(e.descriptor.device_uid,p->uid,12u))
        return finish(p,COMP_SEG_CORRUPT);
    if(p->encoded_bytes>UINT32_MAX-e.descriptor.encoded_length||
       p->reserved_bytes>UINT32_MAX-e.reserved_bytes||
       p->sample_count>UINT64_MAX-e.descriptor.sample_count)return finish(p,COMP_SEG_CORRUPT);
    if(e.descriptor.recording_id==p->oldest_id){p->started_unix_s=e.started_unix_s;p->anchor_slot=(uint8_t)(p->slot-1u);}
    if(e.descriptor.flags&COMP_REC_V2_LAST) {
        if(p->last_seen)return finish(p,COMP_SEG_CORRUPT);
        p->last_seen=true;p->last_index=e.descriptor.segment_index;
    }
    if(e.descriptor.segment_index>p->max_index)p->max_index=e.descriptor.segment_index;
    p->slots|=UINT64_C(1)<<(p->slot-1u);
    if(e.descriptor.recording_id>p->max_id)p->max_id=e.descriptor.recording_id;
    p->segments++;p->encoded_bytes+=e.descriptor.encoded_length;
    p->reserved_bytes+=e.reserved_bytes;p->sample_count+=e.descriptor.sample_count;
    return COMP_SEG_PENDING;
}
