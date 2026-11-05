#include "wba_segment_discard_control.h"

enum { CTRL_PREVIEW=1,CTRL_OFFERED,CTRL_RECHECK,CTRL_ANCHOR,CTRL_COMMIT,CTRL_WORK,CTRL_COMPACT,CTRL_DONE };
static comp_segment_result_t done(comp_discard_control_t *c,comp_segment_result_t r,bool release)
{
    c->phase=CTRL_DONE;
    /* A failed release leaves the buffer and storage owner intact. A clean
     * media operation is not complete until the pipeline releases ownership. */
    if(release&&c->owns) {
        if(c->port.release(c->port.context))c->owns=false;
        else if(r==COMP_SEG_OK)r=COMP_SEG_BAD_STATE;
    }
    c->result=r;return r;
}
static bool same_preview(const comp_discard_preview_t *p,const comp_discard_offer_t *o)
{
    return p->generation==o->generation&&p->epoch==o->epoch&&p->session_id==o->session&&
        p->slots==o->slots&&p->sample_count==o->samples&&p->oldest_id==o->oldest_id&&p->max_id==o->max_id&&
        p->segments==o->segments&&p->encoded_bytes==o->encoded_bytes&&p->reserved_bytes==o->reserved_bytes&&
        p->started_unix_s==o->started_unix_s&&p->last_index==o->last_index&&p->anchor_slot==o->anchor_slot&&
        !memcmp(p->uid,o->uid,12u);
}
static bool same_offer(const comp_discard_offer_t *a,const comp_discard_offer_t *b)
{
    return a->generation==b->generation&&a->epoch==b->epoch&&a->session==b->session&&
        a->slots==b->slots&&a->samples==b->samples&&a->oldest_id==b->oldest_id&&a->max_id==b->max_id&&
        a->segments==b->segments&&a->encoded_bytes==b->encoded_bytes&&a->reserved_bytes==b->reserved_bytes&&
        a->started_unix_s==b->started_unix_s&&a->last_index==b->last_index&&a->anchor_slot==b->anchor_slot&&
        a->token[0]==b->token[0]&&a->token[1]==b->token[1]&&a->request_id==b->request_id&&
        !memcmp(a->uid,b->uid,12u);
}
comp_segment_result_t comp_discard_control_begin(comp_discard_control_t *c,comp_segment_catalog_t *catalog,
    const comp_discard_control_port_t *port,uint32_t peer,uint32_t request_id)
{
    if(!c||!catalog||!port||!port->random_u32||!port->acquire||!port->release||!port->read||!port->poll||!peer||!request_id)
        return COMP_SEG_BAD_ARGUMENT;
    if(c->owns||(c->phase&&c->phase!=CTRL_DONE))return COMP_SEG_BAD_STATE;
    memset(c,0,sizeof(*c));c->catalog=catalog;c->port=*port;c->peer=peer;c->connected=true;
    c->offer.request_id=request_id;c->phase=CTRL_PREVIEW;c->result=COMP_SEG_PENDING;
    comp_segment_result_t r=comp_discard_preview_begin(&c->preview,catalog,port->read,port->context);
    if(r!=COMP_SEG_PENDING)return done(c,r,true);
    return r;
}
const comp_discard_offer_t *comp_discard_control_offer(const comp_discard_control_t *c)
{return c&&c->connected&&c->phase==CTRL_OFFERED?&c->offer:NULL;}
comp_segment_result_t comp_discard_control_confirm(comp_discard_control_t *c,uint32_t peer,uint32_t now,const comp_discard_offer_t *o)
{
    if(!c||!o||!c->connected||c->phase!=CTRL_OFFERED||peer!=c->peer||
       (uint32_t)(now-c->issued_ms)>=60000u||!same_offer(&c->offer,o))return COMP_SEG_BAD_ARGUMENT;
    if(!c->port.acquire(c->port.context))return COMP_SEG_BAD_STATE;
    c->owns=true;c->phase=CTRL_RECHECK;
    comp_segment_result_t r=comp_discard_preview_begin(&c->preview,c->catalog,c->port.read,c->port.context);
    if(r!=COMP_SEG_PENDING)return done(c,r,true);
    return r;
}
bool comp_discard_control_cancel(comp_discard_control_t *c,uint32_t peer)
{
    if(!c||!c->connected||peer!=c->peer||c->commit_started||c->phase==CTRL_DONE)return false;
    (void)done(c,COMP_SEG_BAD_STATE,true);return true;
}
void comp_discard_control_disconnect(comp_discard_control_t *c,uint32_t peer)
{
    if(!c||peer!=c->peer)return;
    c->connected=false;
    if(!c->commit_started&&c->phase!=CTRL_DONE)(void)done(c,COMP_SEG_BAD_STATE,true);
}
comp_segment_result_t comp_discard_control_poll(comp_discard_control_t *c,uint32_t now)
{
    if(!c||!c->catalog)return COMP_SEG_BAD_ARGUMENT;
    if(c->phase==CTRL_DONE)return c->result;
    if(c->phase==CTRL_OFFERED)return COMP_SEG_PENDING;
    if(c->phase==CTRL_PREVIEW||c->phase==CTRL_RECHECK) {
        comp_segment_result_t r=comp_discard_preview_poll(&c->preview);
        if(r==COMP_SEG_PENDING)return r;
        if(r!=COMP_SEG_OK)return done(c,r,true);
        if(c->phase==CTRL_RECHECK) {
            if(!c->connected||!same_preview(&c->preview,&c->offer))return done(c,COMP_SEG_STALE_SNAPSHOT,true);
            c->phase=CTRL_ANCHOR;return COMP_SEG_PENDING;
        }
        comp_discard_preview_t *p=&c->preview;comp_discard_offer_t *o=&c->offer;
        memcpy(o->uid,p->uid,12u);o->epoch=p->epoch;o->session=p->session_id;o->slots=p->slots;o->samples=p->sample_count;
        o->generation=p->generation;o->oldest_id=p->oldest_id;o->max_id=p->max_id;o->segments=p->segments;
        o->encoded_bytes=p->encoded_bytes;o->reserved_bytes=p->reserved_bytes;o->started_unix_s=p->started_unix_s;
        o->last_index=p->last_index;o->anchor_slot=p->anchor_slot;
        if(!c->port.random_u32(c->port.context,&o->token[0])||!c->port.random_u32(c->port.context,&o->token[1])||
           (!o->token[0]&&!o->token[1]))return done(c,COMP_SEG_BAD_STATE,true);
        c->issued_ms=now;c->phase=CTRL_OFFERED;return COMP_SEG_PENDING;
    }
    if(c->phase==CTRL_ANCHOR) {
        if(!c->connected)return done(c,COMP_SEG_BAD_STATE,true);
        if(c->catalog->generation!=c->offer.generation||c->catalog->phase)return done(c,COMP_SEG_STALE_SNAPSHOT,true);
        comp_segment_result_t r=c->port.read(c->port.context,c->catalog,c->offer.anchor_slot,&c->worker.entry,NULL);
        if(r==COMP_SEG_PENDING)return r;
        if(r!=COMP_SEG_OK)return done(c,r,true);
        if(c->catalog->generation!=c->offer.generation||c->worker.entry.state!=COMP_SEG_UNSYNCED||
           c->worker.entry.descriptor.recording_id!=c->offer.oldest_id||c->worker.entry.descriptor.session_id!=c->offer.session)
            return done(c,COMP_SEG_STALE_SNAPSHOT,true);
        c->worker.entry.state=COMP_SEG_SESSION_DISCARD;
        c->worker.anchor.intent.slots=c->offer.slots;c->worker.anchor.intent.max_id=c->offer.max_id;
        r=comp_segment_catalog_session_discard_begin(c->catalog,&c->worker.entry,&c->worker.anchor.intent,c->offer.generation);
        if(r!=COMP_SEG_PENDING)return done(c,r,true);
        c->commit_started=true;c->phase=CTRL_COMMIT;return COMP_SEG_PENDING;
    }
    if(c->phase==CTRL_COMMIT) {
        if(c->catalog->pending!=&c->worker.entry)return done(c,COMP_SEG_BAD_STATE,false);
        comp_segment_result_t r=c->port.poll(c->port.context,c->catalog);
        if(r==COMP_SEG_PENDING)return r;
        if(r!=COMP_SEG_OK)return done(c,r,false);
        r=comp_discard_worker_resume(&c->worker,c->catalog,c->port.read,c->port.poll,c->port.context,c->offer.anchor_slot,&c->worker.entry,&c->worker.anchor.intent);
        if(r!=COMP_SEG_PENDING)return done(c,r,false);
        c->phase=CTRL_WORK;return COMP_SEG_PENDING;
    }
    if(c->phase==CTRL_WORK) {
        comp_segment_result_t r=comp_discard_worker_poll(&c->worker);
        if(r==COMP_SEG_PENDING)return r;
        if(r!=COMP_SEG_OK)return done(c,r,false);
        r=comp_segment_catalog_compact_legacy_begin(c->catalog);
        if(r==COMP_SEG_OK)return done(c,r,true);
        if(r!=COMP_SEG_PENDING)return done(c,r,false);
        c->phase=CTRL_COMPACT;return COMP_SEG_PENDING;
    }
    if(c->phase==CTRL_COMPACT) {
        comp_segment_result_t r=c->port.poll(c->port.context,c->catalog);
        if(r==COMP_SEG_PENDING)return r;
        return done(c,r,r==COMP_SEG_OK);
    }
    return done(c,COMP_SEG_BAD_STATE,false);
}
