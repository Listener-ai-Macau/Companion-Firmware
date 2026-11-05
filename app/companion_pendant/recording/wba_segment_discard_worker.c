#include "wba_segment_discard_worker.h"

enum {WORK_VALIDATE=1,WORK_SCAN,WORK_ERASING,WORK_ANCHOR_ERASING,WORK_DONE};
static comp_segment_result_t finish(comp_discard_worker_t *w,comp_segment_result_t result)
{w->phase=WORK_DONE;w->result=result;return result;}
comp_segment_result_t comp_discard_worker_resume(comp_discard_worker_t *w,comp_segment_catalog_t *c,
    comp_discard_entry_fn read,comp_discard_poll_fn poll,void *context,uint8_t anchor_slot,const comp_segment_entry_t *anchor,const comp_segment_discard_intent_t *intent)
{
    if(!w||!c||!read||!poll||!anchor||!intent||anchor_slot>=COMP_SEGMENT_CAPACITY)return COMP_SEG_BAD_ARGUMENT;
    if(!c->mounted||c->phase||anchor->state!=COMP_SEG_SESSION_DISCARD||
       !(intent->slots&(UINT64_C(1)<<anchor_slot)) || !intent->max_id || intent->max_id<anchor->descriptor.recording_id||
       anchor->descriptor.format_epoch!=c->epoch||memcmp(anchor->descriptor.device_uid,c->uid,12u))return COMP_SEG_BAD_STATE;
    /* Snapshot only the durable intent needed for future revalidation. The
     * caller may supply w->entry itself; copy identity before clearing it. */
    memcpy(w->anchor.uid,anchor->descriptor.device_uid,sizeof(w->anchor.uid));
    memcpy(w->anchor.sha256,anchor->descriptor.sha256,sizeof(w->anchor.sha256));
    w->anchor.epoch=anchor->descriptor.format_epoch;w->anchor.session=anchor->descriptor.session_id;
    w->anchor.intent=*intent;
    w->anchor.recording_id=anchor->descriptor.recording_id;
    memset(&w->entry,0,sizeof(w->entry));w->slot=0u;
    w->catalog=c;w->read=read;w->poll=poll;w->context=context;
    w->anchor_slot=anchor_slot;w->generation=c->generation;
    w->phase=WORK_VALIDATE;w->result=COMP_SEG_PENDING;return COMP_SEG_PENDING;
}
comp_segment_result_t comp_discard_worker_poll(comp_discard_worker_t *w)
{
    if(!w||!w->catalog||!w->read||!w->poll)return COMP_SEG_BAD_ARGUMENT;
    if(w->phase==WORK_DONE)return w->result;
    comp_segment_catalog_t *c=w->catalog;
    if(!c->mounted)return finish(w,COMP_SEG_BAD_STATE);
    if(w->phase==WORK_ERASING || w->phase==WORK_ANCHOR_ERASING) {
        if(c->pending!=&w->entry)return finish(w,COMP_SEG_BAD_STATE);
        comp_segment_result_t r=w->poll(w->context,c);
        if(r==COMP_SEG_PENDING)return r;
        if(r!=COMP_SEG_OK)return finish(w,r);
        if(w->phase==WORK_ANCHOR_ERASING)return finish(w,COMP_SEG_OK);
        w->generation=c->generation;w->phase=WORK_SCAN;return COMP_SEG_PENDING;
    }
    if(w->phase!=WORK_SCAN && w->phase!=WORK_VALIDATE)return finish(w,COMP_SEG_BAD_STATE);
    if(c->generation!=w->generation)return finish(w,COMP_SEG_STALE_SNAPSHOT);
    if(c->phase)return finish(w,COMP_SEG_BAD_STATE);
    if(w->phase==WORK_VALIDATE) {
        comp_segment_discard_intent_t actual;
        comp_segment_result_t r=w->read(w->context,c,w->anchor_slot,&w->entry,&actual);
        if(r==COMP_SEG_PENDING)return r;
        if(r!=COMP_SEG_OK)return finish(w,r);
        if(c->generation!=w->generation)return finish(w,COMP_SEG_STALE_SNAPSHOT);
        if(w->entry.state!=COMP_SEG_SESSION_DISCARD ||
           actual.slots!=w->anchor.intent.slots || actual.max_id!=w->anchor.intent.max_id ||
           w->entry.descriptor.recording_id!=w->anchor.recording_id ||
           w->entry.descriptor.session_id!=w->anchor.session ||
           memcmp(w->entry.descriptor.sha256,w->anchor.sha256,32u))return finish(w,COMP_SEG_BAD_STATE);
        w->phase=WORK_SCAN;return COMP_SEG_PENDING;
    }
    while(w->slot<COMP_SEGMENT_CAPACITY &&
          (!(w->anchor.intent.slots&(UINT64_C(1)<<w->slot)) || w->slot==w->anchor_slot))w->slot++;
    const bool removing_anchor=w->slot==COMP_SEGMENT_CAPACITY;
    if(removing_anchor) {
        /* Erase anchor last; until then it carries the whole recovery intent. */
        comp_segment_discard_intent_t actual;
        comp_segment_result_t r=w->read(w->context,c,w->anchor_slot,&w->entry,&actual);
        if(r==COMP_SEG_PENDING)return r;
        if(r!=COMP_SEG_OK)return finish(w,r);
        if(c->generation!=w->generation)return finish(w,COMP_SEG_STALE_SNAPSHOT);
        if(w->entry.state!=COMP_SEG_SESSION_DISCARD ||
           actual.slots!=w->anchor.intent.slots || actual.max_id!=w->anchor.intent.max_id ||
           w->entry.descriptor.recording_id!=w->anchor.recording_id ||
           w->entry.descriptor.session_id!=w->anchor.session ||
           memcmp(w->entry.descriptor.sha256,w->anchor.sha256,32u))return finish(w,COMP_SEG_BAD_STATE);
        w->entry.state=COMP_SEG_UNSYNCED;
    } else {
        comp_segment_result_t r=w->read(w->context,c,w->slot,&w->entry,NULL);
        if(r==COMP_SEG_PENDING)return r;
        w->slot++;
        if(c->generation!=w->generation)return finish(w,COMP_SEG_STALE_SNAPSHOT);
        if(r==COMP_SEG_NOT_FOUND)return COMP_SEG_PENDING; /* already reclaimed by this intent */
        if(r!=COMP_SEG_OK)return finish(w,r);
        if((w->entry.state!=COMP_SEG_UNSYNCED&&w->entry.state!=COMP_SEG_DISCARDING)||
           w->entry.descriptor.session_id!=w->anchor.session||
           w->entry.descriptor.format_epoch!=w->anchor.epoch||
           memcmp(w->entry.descriptor.device_uid,w->anchor.uid,12u)||
           w->entry.descriptor.recording_id>w->anchor.intent.max_id||
           w->entry.descriptor.recording_id<w->anchor.recording_id)return finish(w,COMP_SEG_BAD_STATE);
    }
    comp_segment_result_t r=comp_segment_catalog_discard_begin(c,&w->entry,w->generation);
    if(r!=COMP_SEG_PENDING)return finish(w,r);
    /* The marker is erased last; report success only after its durable removal. */
    w->phase=removing_anchor?WORK_ANCHOR_ERASING:WORK_ERASING;
    return COMP_SEG_PENDING;
}
