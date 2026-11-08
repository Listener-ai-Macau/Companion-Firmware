#include "wba_recording_radio.h"
#include "wba_recording_crc.h"

enum {RADIO_IDLE=0,RADIO_NEGOTIATE,RADIO_DIRECTORY,RADIO_REPLY,RADIO_PULL,RADIO_CONSUME};
static bool publish(comp_wba_recording_radio_t *r,companion_gatt_char_id_t id,const uint8_t *p,uint16_t n)
{return r->authenticated&&r->config.publish(r->config.context,id,p,n);}
static bool notify(void *v,const uint8_t *p,uint16_t n)
{comp_wba_recording_radio_t *r=v;return r->negotiated&&publish(r,COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,p,n);}
static bool page_available(void *v)
{
    const comp_wba_recording_radio_t *r=v;
    return (r->negotiated&2u)?comp_wba_recording_pipeline_transfer_page_available(r->config.pipeline):
        comp_wba_recording_pipeline_page_available(r->config.pipeline);
}
bool comp_wba_recording_radio_read_allowed(void *v)
{
    const comp_wba_recording_radio_t *r=v;
    if(!r||!r->authenticated||!r->negotiated||
       (r->consume_pending&&(!(r->negotiated&2u)||r->phase!=RADIO_PULL))||!page_available((void *)r))return false;
    const comp_cont_recording_t *e=r->config.pipeline->config.recording;
    /* A closed older segment may send during capture, but PCM/program/drain
     * work always owns the next foreground slice. No microphone stop here. */
    return !e->microphone_active ||
        (e->state==COMP_CONT_RUNNING&&!e->ring_count&&!e->writer.phase&&
         e->stage_length<COMP_SEG_AUDIO_DATA_BYTES&&!e->roll_packet_bytes&&!e->closing_pending);
}
static bool transfer_busy(const comp_wba_recording_radio_t *r)
{return r->config.transfer->state==COMP_WBA_RECORDING_TRANSFER_ACTIVE||
    r->config.transfer->state==COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED;}
bool comp_wba_recording_radio_busy(const comp_wba_recording_radio_t *r)
/* Queued requests always have an active range owner; dequeue either installs
 * the next owner or clears the queue in this same serialized foreground call. */
{return r&&(r->discard_running||r->consume_pending||r->range_pending||r->phase!=RADIO_IDLE||transfer_busy(r));}
bool comp_wba_recording_radio_interval_hint(comp_wba_recording_radio_t *r,uint32_t now,bool allowed)
{
    if(!r)return false;
    if(!allowed||!r->authenticated||!r->negotiated||
       r->config.pipeline->state==COMP_PIPE_FAILED||
       r->config.pipeline->config.recording->microphone_active) {
        r->interval_token=r->interval_deadline=0u;return false;
    }
    if(!r->interval_token)return false;
    if(!r->interval_deadline || (transfer_busy(r)&&!r->config.transfer->snapshot_live)||r->range_pending) {
        r->interval_deadline=now+2000u;
        if(!r->interval_deadline)r->interval_deadline=1u;
    }
    if((int32_t)(now-r->interval_deadline)>=0) {
        r->interval_token=r->interval_deadline=0u;return false;
    }
    return true;
}
bool comp_wba_recording_radio_init(comp_wba_recording_radio_t *r,const comp_wba_recording_radio_config_t *cfg)
{
    if(!r||!cfg||!cfg->pipeline||!cfg->transfer||!cfg->publish||
       cfg->value_capacity<20u||cfg->value_capacity>COMP_WBA_RECORDING_TRANSFER_VALUE_BYTES||!cfg->pipeline->config.catalog||
       !cfg->pipeline->config.recording||!cfg->pipeline->config.storage)return false;
    memset(r,0,sizeof(*r));r->config=*cfg;r->selected_value_capacity=244u;
    comp_wba_segment_pull_config_t pull={cfg->pipeline->config.storage,cfg->pipeline->config.catalog,
        cfg->transfer,&r->io.selected,cfg->pipeline->config.catalog->page,
        comp_wba_recording_radio_read_allowed,page_available,notify,r};
    return comp_wba_segment_pull_init(&r->pull,&pull)&&
        comp_wba_recording_transfer_set_value_capacity(cfg->transfer,cfg->value_capacity<244u?cfg->value_capacity:244u);
}
bool comp_wba_recording_radio_set_value_capacity(comp_wba_recording_radio_t *r,uint16_t capacity)
{
    if(!r||capacity<20u||capacity>COMP_WBA_RECORDING_TRANSFER_VALUE_BYTES)return false;
    if(r->config.value_capacity==capacity)return true;
    if(r->pending_bytes||r->phase==RADIO_DIRECTORY||transfer_busy(r))return false;
    uint16_t selected=capacity<r->selected_value_capacity?capacity:r->selected_value_capacity;
    if(!comp_wba_recording_transfer_set_value_capacity(r->config.transfer,selected))return false;
    r->config.value_capacity=capacity;return true;
}
/* A queued consume reply owns only volatile packet space. Its exact durable
 * receipt remains in the catalog; if the sink retires, free the radio and
 * defer replay rather than treating a stack update as proof of delivery. */
static void retire_consume_reply(comp_wba_recording_radio_t *r)
{
    if(r->phase!=RADIO_REPLY || r->pending_char!=COMPANION_GATT_CHAR_DELETE_PRIVACY)return;
    if(r->pending_bytes==84u && !memcmp(r->config.transfer->packet,"CRA2",4u) &&
       comp_wba_recording_pipeline_consume_result(r->config.pipeline)==COMP_SEG_OK)
        r->consume_replay=true;
    r->pending_bytes=0u;r->phase=RADIO_IDLE;
}
void comp_wba_recording_radio_consume_subscription(comp_wba_recording_radio_t *r,bool enabled)
{
    if(!r)return;
    r->consume_subscribed=r->authenticated&&enabled;
    if(!r->consume_subscribed){r->range_pending=false;r->range_queue_count=0u;comp_wba_recording_pipeline_range_reply_retired(r->config.pipeline);}
    if(!r->consume_subscribed)retire_consume_reply(r);
}
void comp_wba_recording_radio_connection(comp_wba_recording_radio_t *r,bool authenticated)
{
    if(!r)return;
    if(r->authenticated&&!authenticated&&r->discard_buffer_owned){
        comp_discard_control_disconnect(&r->config.transfer->discard_workspace.owner,r->discard_peer);
        r->discard_subscribed=false;
        if(!r->config.transfer->discard_workspace.owner.commit_started &&
           !r->config.transfer->discard_workspace.owner.owns) {r->discard_buffer_owned=false;r->discard_running=false;}
    }
    if(!r->authenticated&&authenticated){r->discard_peer++;if(!r->discard_peer)r->discard_peer=1u;}
    if(r->authenticated&&!authenticated)retire_consume_reply(r);
    r->consume_subscribed=false;
    comp_wba_recording_pipeline_range_reply_retired(r->config.pipeline);
    r->range_pending=false;r->range_token=r->range_id=0u;r->range_queue_count=0u;
    r->authenticated=authenticated;r->negotiated=false;r->selected_value_capacity=244u;
    r->interval_token=r->interval_deadline=0u;
    r->capacity_token=0u;
    comp_wba_segment_pull_peer(&r->pull,NULL,0u,false);
    (void)comp_wba_recording_transfer_set_value_capacity(r->config.transfer,
        r->config.value_capacity<244u?r->config.value_capacity:244u);
    r->pending_bytes=0u;r->phase=r->consume_pending?RADIO_CONSUME:RADIO_IDLE;
    /* No directory poll runs after phase retirement. Do not clear the union
     * through its directory member while it contains a selected proof. */
}
bool comp_wba_recording_radio_claims(companion_gatt_char_id_t id,const uint8_t *p,uint16_t n)
{
    return p&&((id==COMPANION_GATT_CHAR_RECORDING_CONTROL&&n>=2u&&p[0]==2u&&
        (p[1]==0x20u||p[1]==0x22u||p[1]==0x23u||p[1]==0x25u||p[1]==0x26u)) ||
        (id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL&&n&&p[0]==2u) ||
        (id==COMPANION_GATT_CHAR_DELETE_PRIVACY&&n>=4u&&(!memcmp(p,"CRA2",4u)||!memcmp(p,"CDS3",4u)||!memcmp(p,"CRG3",4u))));
}
void comp_wba_recording_radio_unsubscribe(comp_wba_recording_radio_t *r,companion_gatt_char_id_t id)
{
    if(!r)return;
    if(id==COMPANION_GATT_CHAR_DELETE_PRIVACY) {
        comp_wba_recording_radio_consume_subscription(r,false);
        r->discard_subscribed=false;
        if(r->discard_buffer_owned) {
            comp_discard_control_disconnect(&r->config.transfer->discard_workspace.owner,r->discard_peer);
            if(!r->config.transfer->discard_workspace.owner.commit_started &&
           !r->config.transfer->discard_workspace.owner.owns) {r->discard_buffer_owned=false;r->discard_running=false;}
        }
    }
    if(id==COMPANION_GATT_CHAR_RECORDING_CONTROL)r->interval_token=r->interval_deadline=0u;
    if((id==COMPANION_GATT_CHAR_RECORDING_CONTROL&&r->phase==RADIO_NEGOTIATE)||
       (id==COMPANION_GATT_CHAR_RECORDING_LIST&&(r->phase==RADIO_DIRECTORY||
        (r->phase==RADIO_REPLY&&r->pending_char==id)))) {
        r->pending_bytes=0u;r->phase=r->consume_pending?RADIO_CONSUME:RADIO_IDLE;
    }
    if(id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL&&r->phase==RADIO_PULL) {
        comp_wba_segment_pull_cancel(&r->pull);r->phase=r->consume_pending?RADIO_CONSUME:RADIO_IDLE;
    }
    /* Accepted consume retains its exact intent and completes durably even
     * without a notification sink. The next subscribed replay gets its receipt.
     * UID/epoch negotiation retires only on actual disconnect/encryption loss. */
}
static void error(comp_wba_recording_radio_t *r,companion_gatt_char_id_t id,
    uint32_t correlation,comp_segment_result_t result)
{
    uint8_t p[16]={0};memcpy(p,id==COMPANION_GATT_CHAR_DELETE_PRIVACY?"CAE2":"CRE2",4u);
    comp_rec_put16(p+4u,2u);comp_rec_put16(p+6u,16u);comp_rec_put32(p+8u,correlation);
    comp_rec_put32(p+12u,(uint32_t)result);(void)publish(r,id,p,16u);
}
static void reply(comp_wba_recording_radio_t *r,companion_gatt_char_id_t id,uint16_t n)
{r->pending_char=id;r->pending_bytes=n;r->phase=RADIO_REPLY;}
static void range_error(comp_wba_recording_radio_t *r,const uint8_t request[96],comp_segment_result_t result)
{
    const comp_segment_catalog_t *c=r->config.pipeline->config.catalog;uint8_t out[60]={0};
    memcpy(out,"CRR3",4u);comp_rec_put16(out+4u,3u);comp_rec_put16(out+6u,60u);
    memcpy(out+8u,c->uid,12u);comp_rec_put64(out+20u,c->epoch);
    comp_rec_put32(out+28u,comp_rec_get32(request+40u));comp_rec_put32(out+32u,comp_rec_get32(request+44u));
    comp_rec_put32(out+44u,(uint32_t)result);comp_rec_put32(out+52u,comp_rec_get32(request+52u));
    comp_rec_put32(out+56u,comp_rec_crc(out,56u));(void)publish(r,COMPANION_GATT_CHAR_DELETE_PRIVACY,out,60u);
}
static bool queue_range_handoff(comp_wba_recording_radio_t *r,const uint8_t *wire,uint16_t bytes)
{
    const uint8_t count=r->range_queue_count;
    if(count>=3u||(count&&r->range_queue[count-1u][3]=='2')||
       comp_rec_get32(wire+40u)!=r->range_id)return false;
    /* Admission retains bytes in RAM, not an erase authorization. The existing
     * pipeline rechecks the entire CRC/UID/epoch/bounds/SHA before journal I/O
     * when popped. Keep only owner, credit and correlation checks here. */
    if(bytes==96u) {
        if(count&&!memcmp(wire,r->range_queue[count-1u],96u))return true;
        if(count>=2u)return false;
    }
    memcpy(r->range_queue[count],wire,bytes);
    r->range_queue_count=(uint8_t)(count+1u);return true;
}
static bool resume_sealed_pull(comp_wba_recording_radio_t *r,const uint8_t p[32])
{
    const comp_wba_recording_transfer_t *t=r->config.transfer;
    const comp_rec_v2_descriptor_t *d=&r->io.selected.descriptor;
    /* An authenticated receiver may have missed already queued bytes. Only
     * rewind this exact sealed window; never let a new file, live tail or
     * unsent offset replace an in-flight packet. begin() retires the staging
     * generation and revalidates the physical descriptor before reading. */
    return r->phase==RADIO_PULL&&(!r->consume_pending||(r->negotiated&2u))&&transfer_busy(r)&&
        !t->snapshot_live&&!r->pull.live&&p[0]==2u&&p[1]==COMP_SEG_PULL_COMMAND&&
        p[2]==r->pull.request.flags&&!p[3]&&
        comp_rec_get32(p+4u)==t->recording_id&&
        comp_rec_get64(p+8u)==d->format_epoch&&
        comp_rec_get64(p+16u)==d->session_id&&
        comp_rec_get32(p+24u)==d->segment_index&&
        comp_rec_get32(p+28u)<=t->next_offset&&
        comp_rec_get32(p+28u)<t->snapshot_length&&
        comp_wba_segment_pull_begin(&r->pull,p)==COMP_SEG_PENDING;
}
static comp_segment_result_t discard_read(void *context,comp_segment_catalog_t *c,uint8_t slot,comp_segment_entry_t *out,comp_segment_discard_intent_t *intent)
{
    comp_wba_recording_radio_t *r=context;
    return comp_wba_segment_storage_entry_intent(r->config.pipeline->config.storage,c,slot,out,intent);
}
static comp_segment_result_t discard_poll(void *context,comp_segment_catalog_t *c)
{
    comp_wba_recording_radio_t *r=context;
    return comp_wba_segment_storage_catalog_poll(r->config.pipeline->config.storage,c);
}
static bool discard_random(void *context,uint32_t *out)
{comp_wba_recording_radio_t *r=context;return r->config.discard_hooks&&r->config.discard_hooks->random&&r->config.discard_hooks->random(r->config.context,out);}
static bool discard_acquire(void *context)
{comp_wba_recording_radio_t *r=context;return r->config.discard_hooks&&r->config.discard_hooks->acquire&&r->config.discard_hooks->acquire(r->config.context);}
static bool discard_release(void *context)
{comp_wba_recording_radio_t *r=context;return r->config.discard_hooks&&r->config.discard_hooks->release&&r->config.discard_hooks->release(r->config.context);}
static bool discard_write(comp_wba_recording_radio_t *r,const uint8_t *p,uint16_t n)
{
    if(n!=COMP_DISCARD_V3_BYTES||r->discard_running||r->phase!=RADIO_IDLE||r->consume_pending||transfer_busy(r)||
       !r->config.discard_hooks||!r->config.discard_hooks->random||!r->config.discard_hooks->acquire||!r->config.discard_hooks->release||
       r->config.value_capacity<COMP_DISCARD_V3_BYTES)return false;
    uint32_t now=r->config.pipeline->config.now_ms(r->config.pipeline->config.context);
    if(p[4]==COMP_DISCARD_V3_PREVIEW) {
        uint32_t request=0u;uint8_t uid[12];uint64_t epoch=0u,session=0u;
        if(!comp_discard_v3_preview(p,n,&request)) {
            comp_segment_catalog_t *c=r->config.pipeline->config.catalog;
            if(!comp_discard_v3_selection(p,n,&request,uid,&epoch,&session)||
               epoch!=c->epoch||memcmp(uid,c->uid,12u))return false;
        }
        if(r->discard_buffer_owned)return false;
        comp_discard_control_port_t port={discard_random,discard_acquire,discard_release,discard_read,discard_poll,r};
        memset(&r->config.transfer->discard_workspace.owner,0,sizeof(r->config.transfer->discard_workspace.owner));
        if(comp_discard_control_begin_selected(&r->config.transfer->discard_workspace.owner,r->config.pipeline->config.catalog,&port,r->discard_peer,request,session)!=COMP_SEG_PENDING)return false;
        r->capacity_token=0u;r->discard_buffer_owned=true;
        r->discard_confirming=false;r->discard_running=true;r->discard_subscribed=true;return true;
    }
    if(!r->discard_buffer_owned)return false;
    const comp_discard_offer_t *offer=comp_discard_control_offer(&r->config.transfer->discard_workspace.owner);
    if(!offer)return false;
    if(p[4]==COMP_DISCARD_V3_CONFIRM) {
        comp_discard_offer_t supplied;
        if(!comp_discard_v3_decode(p,n,COMP_DISCARD_V3_CONFIRM,0u,&supplied)||
           comp_discard_control_confirm(&r->config.transfer->discard_workspace.owner,r->discard_peer,now,&supplied)!=COMP_SEG_PENDING)return false;
        r->discard_confirming=true;r->discard_running=true;r->discard_subscribed=true;return true;
    }
    if(p[4]==COMP_DISCARD_V3_CANCEL) {
        uint8_t expected[COMP_DISCARD_V3_BYTES];
        if(!comp_discard_v3_encode(expected,COMP_DISCARD_V3_CANCEL,0u,offer)||memcmp(p,expected,n))return false;
        uint8_t *out=r->config.transfer->discard_workspace.response;
        if(!comp_discard_v3_encode(out,COMP_DISCARD_V3_CANCEL,COMP_DISCARD_V3_COMPLETE,offer)||
           !comp_discard_control_cancel(&r->config.transfer->discard_workspace.owner,r->discard_peer))return false;
        memmove(r->config.transfer->packet,out,COMP_DISCARD_V3_BYTES);r->discard_buffer_owned=false;
        reply(r,COMPANION_GATT_CHAR_DELETE_PRIVACY,COMP_DISCARD_V3_BYTES);return true;
    }
    return false;
}
bool comp_wba_recording_radio_write(comp_wba_recording_radio_t *r,companion_gatt_char_id_t id,
    const uint8_t *p,uint16_t n,bool subscribed)
{
    /* A stopped fault or exclusive recovery owns the engine union. Refuse
     * new protocol work before any microphone/cursor access. Negotiation,
     * consumption, and transfer never turn this into a storage bypass. */
    if(!r||!r->authenticated||!p||!subscribed||r->config.value_capacity<136u||
       r->config.pipeline->state==COMP_PIPE_FAILED)return false;
    comp_segment_catalog_t *c=r->config.pipeline->config.catalog;
    bool is_discard=id==COMPANION_GATT_CHAR_DELETE_PRIVACY&&n>=4u&&!memcmp(p,"CDS3",4u);
    if(r->discard_buffer_owned&&!is_discard&&!r->discard_running) {
        comp_discard_control_t *d=&r->config.transfer->discard_workspace.owner;
        if(d->owns||d->commit_started)return false;
        (void)comp_discard_control_cancel(d,r->discard_peer);r->discard_buffer_owned=false;
    }
    /* Same-peer renegotiation must not overwrite the shared reply buffer while
     * a discard reply is pending. A new peer may negotiate, but never receives
     * the previous peer's completion. */
    if(r->discard_running&&r->config.transfer->discard_workspace.owner.connected)return false;
    if(id==COMPANION_GATT_CHAR_RECORDING_CONTROL&&n==32u&&p[0]==2u&&p[1]==0x22u) {
        /* Product-private FW66697+ option in the otherwise bounded ATT-value
         * word. Echoed only on the qualified suspended-read NOR path; legacy
         * clients/status capabilities and the physical receipt stay intact. */
        uint16_t selected=(uint16_t)(((uint16_t)p[2]|((uint16_t)p[3]<<8u))&0x1fffu);
        if(!selected)selected=r->config.value_capacity<244u?r->config.value_capacity:244u; /* legacy MTU fallback */
        if(selected<136u||selected>r->config.value_capacity||
           selected>COMP_WBA_RECORDING_TRANSFER_VALUE_BYTES||!comp_rec_get32(p+4u)||memcmp(p+8u,c->uid,12u)||
           comp_rec_get64(p+20u)!=c->epoch||
           comp_rec_get32(p+28u)!=comp_wba_recording_crc32(0u,p,28u)||
            !c->mounted||r->config.pipeline->state==COMP_PIPE_FAILED||r->range_pending||r->range_queue_count||
           (r->phase!=RADIO_IDLE&&r->phase!=RADIO_CONSUME&&r->phase!=RADIO_NEGOTIATE))return false;
        if(!comp_wba_recording_transfer_set_value_capacity(r->config.transfer,selected))return false;
        r->selected_value_capacity=selected;
        r->negotiated=false;comp_wba_segment_pull_peer(&r->pull,NULL,0u,false);
        uint8_t *target=r->discard_buffer_owned?r->config.transfer->discard_workspace.response:r->config.transfer->packet;
        memcpy(target,p,32u);
        if((p[3]&0x80u)&&!comp_wba_segment_storage_reclaim_read_supported(r->config.pipeline->config.storage)) {
            target[3]&=0x7fu;comp_rec_put32(target+28u,comp_wba_recording_crc32(0u,target,28u));
        }
        if((p[3]&0x40u)&&(!(p[3]&0x80u)||!comp_wba_segment_storage_reclaim_read_supported(r->config.pipeline->config.storage))){
            target[3]&=0xbfu;comp_rec_put32(target+28u,comp_wba_recording_crc32(0u,target,28u));
        }
        if((target[3]&0xc0u)!=0xc0u) {
            target[3]&=0xdfu;comp_rec_put32(target+28u,comp_wba_recording_crc32(0u,target,28u));
        }
        r->pending_bytes=32u;
        r->pending_char=id;r->phase=RADIO_NEGOTIATE;return true;
    }
    if(!r->negotiated)return false;
    if(r->range_pending&&id==COMPANION_GATT_CHAR_DELETE_PRIVACY&&
       ((n==96u&&!memcmp(p,"CRG3",4u))||(n==84u&&!memcmp(p,"CRA2",4u)))&&
       (r->negotiated&8u)) {
        if(!queue_range_handoff(r,p,n)) {
            if(n==96u)range_error(r,p,COMP_SEG_BAD_STATE);
            else error(r,id,comp_rec_get32(p+40u),COMP_SEG_BAD_STATE);
        }
        return true;
    }
    if(id==COMPANION_GATT_CHAR_DELETE_PRIVACY&&n==96u&&!memcmp(p,"CRG3",4u)){
        if(!(r->negotiated&4u))return false;
        if(r->consume_pending||r->range_pending||r->discard_running||
           (r->phase!=RADIO_IDLE&&r->phase!=RADIO_PULL)||
           (r->phase==RADIO_PULL&&(r->pull.live||r->pull.request.recording_id!=comp_rec_get32(p+40u)))){
            range_error(r,p,COMP_SEG_BAD_STATE);return true;
        }
        bool selected=r->io.selected.descriptor.recording_id==comp_rec_get32(p+40u)&&
            r->io.selected.descriptor.session_id==comp_rec_get64(p+28u)&&
            r->io.selected.descriptor.segment_index==comp_rec_get32(p+36u);
        comp_segment_result_t result=comp_wba_recording_pipeline_range_wire(r->config.pipeline,p,selected?r->pull.slot:64u);
        if(result!=COMP_SEG_PENDING&&result!=COMP_SEG_OK){range_error(r,p,result);return true;}
        r->consume_replay=false;r->range_token=comp_rec_get32(p+44u);r->range_id=comp_rec_get32(p+40u);
        r->range_pending=true;return true;
    }
    if(r->range_pending&&id!=COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL)return false;
    if(id==COMPANION_GATT_CHAR_DELETE_PRIVACY&&n>=4u&&!memcmp(p,"CDS3",4u))return discard_write(r,p,n);
    if(r->discard_running)return false;
    if(id==COMPANION_GATT_CHAR_RECORDING_CONTROL&&n==32u&&p[0]==2u&&p[1]==0x25u) {
        const uint32_t token=comp_rec_get32(p+4u);
        if(p[2]>1u||p[3]||!token||memcmp(p+8u,c->uid,12u)||
           comp_rec_get64(p+20u)!=c->epoch||
           comp_rec_get32(p+28u)!=comp_wba_recording_crc32(0u,p,28u)||
           r->phase!=RADIO_IDLE||r->consume_pending||transfer_busy(r))return false;
        if(p[2]&&r->config.pipeline->config.recording->microphone_active) {
            error(r,id,token,COMP_SEG_PENDING);return true;
        }
        if(p[2]) {r->interval_token=token;r->interval_deadline=0u;}
        else {
            /* A stale close cannot retire a newer batch's owner. */
            if(r->interval_token && r->interval_token!=token)return false;
            r->interval_token=r->interval_deadline=0u;
        }
        memcpy(r->config.transfer->packet,p,32u);reply(r,id,32u);return true;
    }
    if(id==COMPANION_GATT_CHAR_RECORDING_CONTROL&&n==32u&&p[0]==2u&&p[1]==0x26u) {
        uint32_t generation=0u;uint8_t segments=0u;const uint32_t token=comp_rec_get32(p+4u);
        const comp_wba_pipeline_config_t *cfg=&r->config.pipeline->config;
        if(p[2]||p[3]||!token||memcmp(p+8u,c->uid,12u)||comp_rec_get64(p+20u)!=c->epoch||
           comp_rec_get32(p+28u)!=comp_wba_recording_crc32(0u,p,28u)||
           r->phase!=RADIO_IDLE||r->consume_pending||transfer_busy(r)||!cfg->capacity_snapshot||
           !cfg->capacity_snapshot(r->config.pipeline,&generation,&segments))return false;
        uint8_t *out=r->config.transfer->packet;memset(out,0,32u);memcpy(out,"CSN1",4u);
        comp_rec_put32(out+4u,token);comp_rec_put32(out+8u,generation);out[12]=segments;
        memcpy(out+16u,c->uid,12u);comp_rec_put32(out+28u,comp_wba_recording_crc32(0u,out,28u));
        r->capacity_token=token;reply(r,id,32u);return true;
    }
    if(id==COMPANION_GATT_CHAR_DELETE_PRIVACY&&n==84u&&!memcmp(p,"CRA2",4u)) {
        if((r->phase!=RADIO_IDLE&&r->phase!=RADIO_CONSUME)||transfer_busy(r))return false;
        const bool selected=r->pull.request.recording_id==comp_rec_get32(p+40u)&&
            r->pull.session==comp_rec_get64(p+28u)&&r->pull.segment_index==comp_rec_get32(p+36u);
        comp_segment_result_t result=comp_wba_recording_pipeline_consume_wire_hint(
            r->config.pipeline,p,selected?r->pull.slot:64u);
        if(result==COMP_SEG_PENDING||result==COMP_SEG_OK) {
            r->consume_replay=false;r->consume_pending=true;r->phase=RADIO_CONSUME;return true;
        }
        error(r,id,comp_rec_get32(p+40u),result);return false;
    }
    if(id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL&&n==32u&&r->phase==RADIO_PULL)
        return resume_sealed_pull(r,p);
    if(id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL&&n==32u&&r->phase==RADIO_CONSUME&&
       r->consume_pending&&(r->negotiated&2u)&&!transfer_busy(r)&&
       comp_rec_get32(p+4u)!=r->config.pipeline->consume.descriptor.recording_id) {
        comp_segment_result_t result=comp_wba_segment_pull_begin(&r->pull,p);
        if(result==COMP_SEG_PENDING){r->phase=RADIO_PULL;return true;}
        return false;
    }
    if(r->phase!=RADIO_IDLE||r->consume_pending||transfer_busy(r))return false;
    if(id==COMPANION_GATT_CHAR_RECORDING_CONTROL&&n==32u&&p[0]==2u&&p[1]==0x23u) {
        const comp_cont_recording_t *e=r->config.pipeline->config.recording;
        const uint32_t nonce=comp_rec_get32(p+4u);
        if(p[2]||p[3]||!nonce||comp_rec_get64(p+8u)!=c->epoch||
           !comp_rec_get64(p+16u)||comp_rec_get64(p+24u))return false;
        const bool stable=e->state==COMP_CONT_RUNNING||e->state==COMP_CONT_PAUSED;
        if(!comp_wba_recording_radio_read_allowed(r)||!stable||e->writer.phase||e->bookmark_phase||
           e->active.descriptor.session_id!=comp_rec_get64(p+16u)||
           !(e->config.pause_timeline?
             comp_wba_segment_pull_tail_timeline(&r->pull,&e->active,e->writer.committed_bytes,
                 comp_cont_recording_non_audio_bytes(e)):
             comp_wba_segment_pull_tail(&r->pull,&e->active,e->writer.committed_bytes))) {
            /* No complete committed frame yet, or capture owns this slice.
             * A correlated empty response is not a sealed/consumed segment. */
            uint8_t *out=r->config.transfer->packet;memset(out,0,16u);memcpy(out,"CRE2",4u);
            comp_rec_put16(out+4u,2u);comp_rec_put16(out+6u,16u);comp_rec_put32(out+8u,nonce);
            comp_rec_put32(out+12u,COMP_SEG_PENDING);reply(r,COMPANION_GATT_CHAR_RECORDING_LIST,16u);return true;
        }
        const comp_segment_entry_t *tail=&r->io.selected;const comp_rec_v2_descriptor_t *d=&tail->descriptor;
        uint8_t *out=r->config.transfer->packet;memset(out,0,80u);memcpy(out,"CLP2",4u);
        comp_rec_put16(out+4u,2u);comp_rec_put16(out+6u,80u);memcpy(out+8u,d->device_uid,12u);
        comp_rec_put64(out+20u,d->format_epoch);comp_rec_put64(out+28u,d->session_id);
        comp_rec_put32(out+36u,d->recording_id);comp_rec_put32(out+40u,d->segment_index);
        comp_rec_put64(out+44u,d->sample_offset);comp_rec_put64(out+52u,d->sample_count);
        comp_rec_put32(out+60u,d->encoded_length);comp_rec_put32(out+64u,tail->started_unix_s);
        comp_rec_put32(out+68u,nonce);out[72]=d->codec;out[73]=d->source_mode;
        comp_rec_put16(out+74u,e->config.pause_timeline==COMP_CONT_TIMELINE_AUDIO_PROFILE?31u:
            e->config.pause_timeline==COMP_CONT_TIMELINE_SOURCE_BOUNDARY?15u:
            e->config.pause_timeline==COMP_CONT_TIMELINE_BOOKMARKS?7u:e->config.pause_timeline?3u:1u);
        comp_rec_put32(out+76u,comp_wba_recording_crc32(0u,out,76u));
        reply(r,COMPANION_GATT_CHAR_RECORDING_LIST,80u);return true;
    }
    if(id==COMPANION_GATT_CHAR_RECORDING_CONTROL&&n==16u&&p[0]==2u&&p[1]==0x20u) {
        comp_wba_segment_pull_cancel(&r->pull);const uint32_t nonce=comp_rec_get32(p+8u);
        /* Pull retirement releases this selected-proof storage. Its bytes
         * cannot be read as a previously active directory worker. */
        memset(&r->io,0,sizeof(r->io));
        comp_segment_result_t result=comp_wba_segment_directory_begin(&r->io.directory,
            r->config.pipeline->config.storage,c,p,r->config.transfer->packet,r->config.value_capacity<248u?r->config.value_capacity:248u);
        if(result==COMP_SEG_PENDING){r->phase=RADIO_DIRECTORY;return true;}
        error(r,COMPANION_GATT_CHAR_RECORDING_LIST,nonce,result);return false;
    }
    if(id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL&&n==32u) {
        comp_segment_result_t result=comp_wba_segment_pull_begin(&r->pull,p);
        if(result==COMP_SEG_PENDING){r->phase=RADIO_PULL;return true;}
        return false;
    }
    return false;
}
void comp_wba_recording_radio_poll(comp_wba_recording_radio_t *r,
    comp_wba_recording_transfer_clock_fn clock,void *clock_context,
    const comp_wba_recording_transfer_budget_t *budget)
{
    if(!r)return;
    if(r->discard_running) {
        comp_discard_control_t *d=&r->config.transfer->discard_workspace.owner;
        uint8_t *out=r->config.transfer->discard_workspace.response;
        uint32_t now=r->config.pipeline->config.now_ms(r->config.pipeline->config.context);
        comp_segment_result_t result=comp_discard_control_poll(d,now);
        const comp_discard_offer_t *offer=comp_discard_control_offer(d);
        if(!r->discard_confirming && offer) {
            if(!comp_discard_v3_encode(out,COMP_DISCARD_V3_PREVIEW,COMP_DISCARD_V3_OFFER,offer))return;
            if(publish(r,COMPANION_GATT_CHAR_DELETE_PRIVACY,out,COMP_DISCARD_V3_BYTES))r->discard_running=false;
            return;
        }
        if(result==COMP_SEG_PENDING)return;
        if(!r->discard_confirming&&r->authenticated&&r->negotiated&&r->discard_subscribed&&
           d->connected&&d->peer==r->discard_peer) {
            memset(out,0,16u);memcpy(out,"CDX3",4u);
            comp_rec_put32(out+4u,d->offer.request_id);comp_rec_put32(out+8u,(uint32_t)result);
            comp_rec_put32(out+12u,comp_rec_crc(out,12u));
            if(!publish(r,COMPANION_GATT_CHAR_DELETE_PRIVACY,out,16u))return;
        }
        if(r->discard_confirming&&r->authenticated&&r->negotiated&&r->discard_subscribed&&
           d->connected&&d->peer==r->discard_peer) {
            uint8_t status=result==COMP_SEG_OK?COMP_DISCARD_V3_COMPLETE:COMP_DISCARD_V3_REFUSED;
            if(comp_discard_v3_encode(out,COMP_DISCARD_V3_CONFIRM,status,&d->offer)&&
               !publish(r,COMPANION_GATT_CHAR_DELETE_PRIVACY,out,COMP_DISCARD_V3_BYTES))return;
        }
        /* Failed uncertain work retains both flash and buffer ownership. */
        if(!d->owns) {
            if(r->phase==RADIO_NEGOTIATE&&r->pending_bytes==32u)memmove(r->config.transfer->packet,out,32u);
            r->discard_buffer_owned=false;
        } else if(r->phase==RADIO_NEGOTIATE) {
            /* The staged negotiation lives beside an owner that still holds
             * the packet union. Never publish packet[] until it is released. */
            r->pending_bytes=0u;r->phase=RADIO_IDLE;r->negotiated=false;
        }
        r->discard_running=false;return;
    }
    /* There is no notification sink after disconnect. Once consumption has
     * terminated, release the transient radio owner so an offline recording
     * can start. Preserve successful automatic replay on reconnect and keep
     * the pipeline's proof and any uncertain storage owner intact. A pending
     * transaction still owns the radio until it actually terminates. */
    if((!r->authenticated || !r->consume_subscribed) && r->consume_pending && r->phase==RADIO_CONSUME &&
       comp_wba_recording_pipeline_consume_result(r->config.pipeline)!=COMP_SEG_PENDING) {
        r->consume_replay=comp_wba_recording_pipeline_consume_result(r->config.pipeline)==COMP_SEG_OK;
        r->consume_pending=false;r->phase=RADIO_IDLE;
    }
    if(!r->authenticated)return;
    if(r->range_pending&&r->consume_subscribed&&
       comp_wba_recording_pipeline_consume_result(r->config.pipeline)!=COMP_SEG_PENDING){
        uint8_t receipt[60];
        if(!comp_wba_recording_pipeline_range_reply(r->config.pipeline,receipt)||
           comp_rec_get32(receipt+28u)!=r->range_id||comp_rec_get32(receipt+32u)!=r->range_token){r->range_pending=false;return;}
        if(publish(r,COMPANION_GATT_CHAR_DELETE_PRIVACY,receipt,60u)){
            r->range_pending=false;comp_wba_recording_pipeline_range_reply_retired(r->config.pipeline);
            if(comp_rec_get32(receipt+44u)!=COMP_SEG_OK)r->range_queue_count=0u;
            if(r->range_queue_count) {
                if(r->phase==RADIO_PULL&&!transfer_busy(r))r->phase=RADIO_IDLE;
                uint16_t bytes=r->range_queue[0][3]=='2'?84u:96u;
                /* Dispatch reads synchronously; keep its cell intact until the
                 * existing parser has copied ownership into the pipeline. */
                (void)comp_wba_recording_radio_write(r,COMPANION_GATT_CHAR_DELETE_PRIVACY,r->range_queue[0],bytes,true);
                --r->range_queue_count;
                memmove(r->range_queue,r->range_queue+1u,(size_t)r->range_queue_count*96u);
                if(!r->range_pending&&!r->consume_pending)r->range_queue_count=0u;
            }
        }
        return;
    }
    if(r->phase==RADIO_NEGOTIATE||r->phase==RADIO_REPLY) {
        if(!publish(r,r->pending_char,r->config.transfer->packet,r->pending_bytes))return;
        if(r->phase==RADIO_NEGOTIATE) {
            comp_segment_catalog_t *c=r->config.pipeline->config.catalog;
            bool overlap=(r->config.transfer->packet[3]&0x80u)!=0u;
            bool ranges=(r->config.transfer->packet[3]&0x40u)!=0u;
            bool queued=(r->config.transfer->packet[3]&0x20u)!=0u;
            r->negotiated=comp_wba_segment_pull_peer(&r->pull,c->uid,c->epoch,true)?
                (uint8_t)(1u|(overlap?2u:0u)|(overlap&&ranges?4u:0u)|(queued?8u:0u)):0u;
        }
        else if(r->pending_char==COMPANION_GATT_CHAR_RECORDING_LIST&&r->pending_bytes>=24u&&
                r->config.transfer->packet[0]==2u&&comp_wba_segment_directory_next(&r->io.directory)) {
            r->pending_bytes=0u;r->phase=RADIO_DIRECTORY;return;
        }
        r->pending_bytes=0u;r->phase=r->consume_pending?RADIO_CONSUME:RADIO_IDLE;return;
    }
    if(!r->negotiated)return;
    /* Do not occupy the command path while a peer has not enabled the
     * receipt sink. A reinitialized pipeline may have retired this cache;
     * in that case a later exact proof still retrieves the durable receipt. */
    if(r->consume_replay &&
       comp_wba_recording_pipeline_consume_result(r->config.pipeline)!=COMP_SEG_OK)
        r->consume_replay=false;
    if(r->consume_replay && r->consume_subscribed && r->phase==RADIO_IDLE && !transfer_busy(r)) {
        r->consume_replay=false;r->consume_pending=true;r->phase=RADIO_CONSUME;
    }
    if(r->phase==RADIO_DIRECTORY) {
        if(!page_available(r))return;
        comp_segment_result_t result=comp_wba_segment_directory_poll(&r->io.directory);
        if(result==COMP_SEG_OK) {
            if(r->io.directory.count)r->pull.slot=r->io.directory.scan;
            reply(r,COMPANION_GATT_CHAR_RECORDING_LIST,r->io.directory.bytes);
        }
        else if(result!=COMP_SEG_PENDING) {
            /* Keep the correlated refusal across notification backpressure. */
            uint8_t *p=r->config.transfer->packet;memset(p,0,16u);memcpy(p,"CRE2",4u);
            comp_rec_put16(p+4u,2u);comp_rec_put16(p+6u,16u);
            comp_rec_put32(p+8u,r->io.directory.nonce);comp_rec_put32(p+12u,result);
            reply(r,COMPANION_GATT_CHAR_RECORDING_LIST,16u);
        }
        return;
    }
    if(r->phase==RADIO_PULL) {
        bool selecting=r->config.transfer->state==COMP_WBA_RECORDING_TRANSFER_IDLE;
        if(selecting) {
            comp_segment_result_t result=comp_wba_segment_pull_select_poll(&r->pull);
            if(result!=COMP_SEG_OK&&result!=COMP_SEG_PENDING)r->phase=r->consume_pending?RADIO_CONSUME:RADIO_IDLE;
            return; /* metadata and payload never share this foreground slice */
        }
        if(comp_wba_recording_radio_read_allowed(r)) {
            static const comp_wba_recording_transfer_budget_t live_pair={1u,2u,1u};
            static const comp_wba_recording_transfer_budget_t live_single={1u,1u,1u};
            /* These are SEALED packets, so snapshot_live deliberately stays
             * false. Apply the capture budget explicitly instead of letting
             * their framing accidentally enable stopped bulk work. */
            const comp_wba_recording_transfer_budget_t *allowed=budget;
            if(r->config.pipeline->config.recording->microphone_active&&
               (!budget||(budget->max_packets&&budget->max_steps&&budget->max_elapsed_ms)))
                allowed=clock?&live_pair:&live_single;
            (void)comp_wba_recording_transfer_poll_budget(r->config.transfer,clock,clock_context,allowed);
        }
        if(!transfer_busy(r))r->phase=r->consume_pending?RADIO_CONSUME:RADIO_IDLE;
        return;
    }
    if(r->phase==RADIO_CONSUME) {
        comp_segment_result_t result=comp_wba_recording_pipeline_consume_result(r->config.pipeline);
        if(result==COMP_SEG_PENDING)return; /* app, not radio, progresses NOR */
        uint8_t *p=r->config.transfer->packet;
        if(result==COMP_SEG_OK&&comp_wba_recording_pipeline_receipt(r->config.pipeline,p)) {
            r->consume_pending=false;reply(r,COMPANION_GATT_CHAR_DELETE_PRIVACY,84u);
        } else {
            uint32_t id=r->config.pipeline->consume.descriptor.recording_id;
            memset(p,0,16u);memcpy(p,"CAE2",4u);comp_rec_put16(p+4u,2u);comp_rec_put16(p+6u,16u);
            comp_rec_put32(p+8u,id);comp_rec_put32(p+12u,result);
            r->consume_pending=false;reply(r,COMPANION_GATT_CHAR_DELETE_PRIVACY,16u);
        }
    }
}
