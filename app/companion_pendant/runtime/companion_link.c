#include "companion_link.h"
#include <string.h>
_Static_assert(sizeof(comp_link_reclaim_t)<=80u,"bounded reclaim state");
_Static_assert(sizeof(companion_recording_discard_v2_t)==84u,"bounded discard wire");
_Static_assert(sizeof(comp_link_discard_t)<=96u,"bounded discard state");
#define MEETING_STATE_IDLE 0u
#define MEETING_STATE_RECORDING 1u
#define MEETING_STATE_FINALIZED 2u
#define MEETING_STATE_PAUSED 3u
#define MEETING_STATE_PAUSING 4u
#define MEETING_STATE_RESUMING 5u
#define MEETING_STATE_STOPPING 6u
static bool publish(comp_link_t *l,companion_gatt_char_id_t id,const void *bytes,uint16_t n)
{
    if(l->config.publish(l->config.context,id,bytes,n))return true;
    ++l->publish_failures; return false;
}
static bool recording_io_idle(const comp_link_t *l)
{
    const comp_runtime_t *r=l->config.runtime;
    if(l->segmented) {
        const comp_wba_recording_pipeline_t *p=l->segmented->config.pipeline;
        return !r->capture_active&&!r->command_pending&&!r->start_pending&&!r->prepare_pending&&
            (p->state==COMP_PIPE_IDLE||p->state==COMP_PIPE_FINISHED)&&
            !p->config.recording->microphone_active&&!p->config.catalog->phase;
    }
#ifndef COMPANION_RECORDING_SEGMENTED_ONLY
    comp_wba_recording_service_state_t s=l->config.recorder->state;
    return !r->capture_active && !r->command_pending && !r->start_pending &&
        !r->prepare_pending &&
        (s==COMP_WBA_RECORDING_IDLE || s==COMP_WBA_RECORDING_TRANSFER_READY || s==COMP_WBA_RECORDING_FAULT);
#else
    return false;
#endif
}
static bool meeting_publish(comp_link_t *l,const companion_gatt_meeting_status_v1_t *status)
{
    if(!l->connected||!l->encrypted)return false;
    if(l->segmented) {
        const comp_wba_recording_pipeline_t *p=l->segmented->config.pipeline;
        uint8_t wire[80]={0};
        memcpy(wire,status,sizeof(*status));memcpy(wire+28u,l->meeting_extended?"CMS3":"CMS2",4u);
        memcpy(wire+32u,p->config.catalog->uid,12u);
        comp_rec_put64(wire+44u,p->config.catalog->epoch);
        comp_rec_put64(wire+52u,p->engine_bound&&p->token==l->meeting_record_token&&
            p->config.recording->state!=COMP_CONT_CANCELED?
            p->config.recording->active.descriptor.session_id:0u);
        if(l->meeting_extended) {
            comp_rec_put32(wire+60u,l->meeting_control_sequence);wire[64]=l->meeting_timeline?1u:0u;
            wire[65]=(uint8_t)(l->meeting_command&0x7fu);
            if(l->meeting_command&0x80u) {
                wire[66]=1u;comp_rec_put32(wire+67u,l->meeting_start_request_id);
            }
            /* Independent cause, never a synthetic STOP command/ACK. The
             * engine owns its first accepted stop and eventual durable tail. */
            if(p->engine_bound && p->token==l->meeting_record_token &&
               (status->state==MEETING_STATE_FINALIZED||status->state==MEETING_STATE_STOPPING))
                wire[71]=comp_cont_recording_end_reason(p->config.recording->stop_reason);
            comp_rec_put32(wire+76u,comp_rec_crc(wire,76u));
            return publish(l,COMPANION_GATT_CHAR_MEETING_STATUS,wire,80u);
        }
        comp_rec_put32(wire+60u,comp_rec_crc(wire,60u));
        return publish(l,COMPANION_GATT_CHAR_MEETING_STATUS,wire,64u);
    }
    return publish(l,COMPANION_GATT_CHAR_MEETING_STATUS,status,sizeof(*status));
}
static bool meeting_reject_flush(comp_link_t *l)
{
    if(!l->meeting_reject_error)return true;
    companion_gatt_meeting_status_v1_t status=l->config.features->meeting;
    status.schema_version=1u;status.request_id=l->meeting_reject_request_id;
    status.last_error=l->meeting_reject_error;
    if(!meeting_publish(l,&status))return false;
    l->meeting_reject_error=0u;return true;
}
static void meeting_reject_code(comp_link_t *l,uint32_t request_id,uint8_t error)
{
    /* Keep the first pending reply while the controller has no credit.
     * The authoritative recording state and its active request stay intact. */
    if(!l->meeting_reject_error) {
        l->meeting_reject_request_id=request_id;l->meeting_reject_error=error;
    }
    (void)meeting_reject_flush(l);
}
static void meeting_reject(comp_link_t *l,uint32_t request_id)
{
    meeting_reject_code(l,request_id,COMPANION_V1_MEETING_ERROR_REJECTED);
}
static void meeting_refresh(comp_link_t *l,uint32_t now)
{
    companion_gatt_meeting_status_v1_t *status=&l->config.features->meeting;
    if(l->segmented) {
        const comp_wba_recording_pipeline_t *p=l->segmented->config.pipeline;
        const comp_cont_recording_t *e=p->config.recording;
        /* Remote START attaches synchronously. Only a real engine with the
         * runtime's new token and no matching link owner is a local start. */
        if(p->engine_bound && p->token && p->token!=l->meeting_record_token &&
           p->token==l->config.runtime->record_token && p->pause_timeline &&
           p->state==COMP_PIPE_RECORDING) {
            memset(status,0,sizeof(*status));status->schema_version=1u;
            l->meeting_record_token=p->token;l->meeting_start_request_id=p->token;
            l->meeting_control_sequence=0u;l->meeting_command=0x81u;
            l->meeting_extended=true;l->meeting_timeline=true;
            l->meeting_max_seconds=0u;l->remote_limit_ms=0u;l->remote_record_token=0u;
            status->request_id=p->token;l->meeting_status_dirty=true;
        }
        if(!l->meeting_start_request_id)return;
        const comp_runtime_t *r=l->config.runtime;
        /* Bounded fault recovery retires the old engine only when the
         * product has rebuilt its durable catalogue/capacity and is IDLE.
         * Do not keep a stale active/error CMS3 after that transition, and
         * do not acknowledge a STOP which was never completed. A new remote
         * START can be waiting on this same recovery: keep its correlation. */
        if(p->state==COMP_PIPE_IDLE&&!p->token&&!p->engine_bound&&
           !p->config.catalog->phase&&!r->capture_active&&
           !(r->record_token==l->meeting_record_token&&
             (r->command_pending||r->prepare_pending||r->start_pending))) {
            memset(status,0,sizeof(*status));status->schema_version=1u;
            l->meeting_start_request_id=0u;l->meeting_record_token=0u;
            l->meeting_control_sequence=0u;l->meeting_command=0u;
            l->meeting_max_seconds=0u;l->remote_limit_ms=0u;l->remote_record_token=0u;
            l->meeting_extended=false;l->meeting_timeline=false;l->meeting_status_dirty=true;
            return;
        }
        companion_gatt_meeting_status_v1_t before=*status;
        if(p->token!=l->meeting_record_token)return;
        /* The product key uses the same engine sequence. Remote controls
         * bind it synchronously before this poll, so a newer engine sequence
         * here is a physical PAUSE/RESUME, never a remote acknowledgement. */
        if(p->engine_bound && p->pause_timeline && p->state==COMP_PIPE_RECORDING &&
           !p->stop_requested && e->command_sequence>l->meeting_control_sequence) {
            uint8_t command=(e->state==COMP_CONT_PAUSE_PENDING ||
                e->state==COMP_CONT_PAUSING || e->state==COMP_CONT_PAUSED)?4u:5u;
            uint32_t request=l->meeting_start_request_id^e->command_sequence^0x4c4f4300u;
            status->request_id=request?request:1u;l->meeting_command=(uint8_t)(0x80u|command);
            l->meeting_control_sequence=e->command_sequence;l->meeting_status_dirty=true;
        }
        if(p->state==COMP_PIPE_FINISHED && p->engine_bound && e->state==COMP_CONT_CANCELED) {
            /* A cancelled prepared writer has no original audio to sync.
             * Do not turn its allocated-but-retired ID into a finalized row. */
            const uint8_t why=l->config.runtime->record_stop_reason;
            status->state=MEETING_STATE_IDLE;status->meeting_id=0u;status->duration_ms=0u;
            status->last_error=why==COMP_RECORD_STOP_LOW_BATTERY?COMPANION_V1_MEETING_ERROR_POWER_LOW:
                why==COMP_RECORD_STOP_POWER_UNKNOWN?COMPANION_V1_MEETING_ERROR_POWER_UNKNOWN:COMPANION_V1_MEETING_ERROR_REJECTED;
        } else if(p->state==COMP_PIPE_IDLE&&!p->engine_bound&&p->failure==COMP_SEG_FULL) {
            /* Product reports a failed empty START, then releases its storage
             * owner before this poll. Keep the request's terminal failure:
             * an idle/pending snapshot would hide FULL and fence every retry. */
            status->last_error=COMPANION_V1_MEETING_ERROR_STORAGE_FULL;
        } else if(p->state==COMP_PIPE_FAILED) {
            status->last_error=COMPANION_V1_MEETING_ERROR_REJECTED;
            /* Retain the original key and failure, but never advertise an
             * already-quiesced fault as still recording or safely finalized.
             * Recovery must validate its durable prefix before it is saved. */
            if(p->engine_bound&&!e->microphone_active) {
                status->state=MEETING_STATE_IDLE;
                status->duration_ms=e->stats.accepted_pcm_blocks*10u;
            }
        }
        else if(p->engine_bound&&(p->state==COMP_PIPE_RECORDING||p->state==COMP_PIPE_STOPPING||p->state==COMP_PIPE_FINISHED)) {
            /* Opening the microphone is still START preparation: its first
             * DMA halves are acoustic settling, not accepted audio. Keep the
             * existing pending reply until the real PCM owner accepts a block.
             * STOP/cancel and pause transitions retain their actual results. */
            if(p->state==COMP_PIPE_RECORDING&&!p->stop_requested&&
               e->state==COMP_CONT_RUNNING&&!e->stats.accepted_pcm_blocks)return;
            status->state=p->state==COMP_PIPE_FINISHED?MEETING_STATE_FINALIZED:MEETING_STATE_RECORDING;
            if(l->meeting_extended&&p->state!=COMP_PIPE_FINISHED) {
                if(p->stop_requested||p->state==COMP_PIPE_STOPPING)status->state=MEETING_STATE_STOPPING;
                else if(e->state==COMP_CONT_PAUSED)status->state=MEETING_STATE_PAUSED;
                else if(e->state==COMP_CONT_PAUSE_PENDING||e->state==COMP_CONT_PAUSING)status->state=MEETING_STATE_PAUSING;
                else if(e->state==COMP_CONT_RESUMING)status->state=MEETING_STATE_RESUMING;
            }
            /* The V1 anchor belongs to the START, not the current extent.
             * CMS2 separately carries the durable logical session identity. */
            if(!status->meeting_id) {
                status->meeting_id=e->active.descriptor.recording_id;
                status->started_tick_ms=l->config.runtime->recording_since_ms;
            }
            status->duration_ms=e->stats.accepted_pcm_blocks*10u;
            status->sync_state=(uint8_t)(p->state==COMP_PIPE_FINISHED?COMP_WBA_RECORDING_WIRE_UNSYNCED:COMP_WBA_RECORDING_WIRE_ACTIVE);
            status->segment_count=(uint16_t)e->stats.sealed_segments;status->last_error=0u;
        }
        if(memcmp(&before,status,sizeof(before)))l->meeting_status_dirty=true;
        return;
    }
#ifndef COMPANION_RECORDING_SEGMENTED_ONLY
    const comp_wba_recording_service_t *recorder=l->config.recorder;
    const comp_recording_journal_entry_t *entry=recorder->entry.recording_id?
        comp_recording_journal_find(l->config.journal,recorder->entry.recording_id):NULL;
    companion_gatt_meeting_status_v1_t before=*status;
    if(!l->meeting_start_request_id)return;
    status->schema_version=1u;
    if((recorder->token==l->meeting_record_token&&recorder->state==COMP_WBA_RECORDING_FAULT)||
       (l->config.runtime->record_token==l->meeting_record_token&&
        !l->config.runtime->prepare_pending&&!l->config.runtime->start_pending&&
        (l->config.runtime->recording==DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY||
         l->config.runtime->recording==DENZIC_AUDIO_RECORDING_STATE_CANCELED))) {
        status->last_error=COMPANION_V1_MEETING_ERROR_REJECTED;
    } else if(recorder->token==l->meeting_record_token&&entry&&
              recorder->state==COMP_WBA_RECORDING_TRANSFER_READY) {
        status->state=MEETING_STATE_FINALIZED;status->meeting_id=entry->recording_id;
        status->duration_ms=entry->duration_ms;status->sync_state=COMP_WBA_RECORDING_WIRE_UNSYNCED;
        status->summary_state=0u;status->segment_count=1u;status->last_error=0u;
    } else if(recorder->token==l->meeting_record_token&&entry&&l->config.runtime->capture_active&&
              recorder->state==COMP_WBA_RECORDING_CAPTURING) {
        if(status->state!=MEETING_STATE_RECORDING||status->meeting_id!=entry->recording_id) {
            status->state=MEETING_STATE_RECORDING;status->meeting_id=entry->recording_id;
            status->started_tick_ms=l->config.runtime->recording_since_ms;
            status->duration_ms=now-status->started_tick_ms;status->sync_state=COMP_WBA_RECORDING_WIRE_ACTIVE;
            status->summary_state=0u;status->last_error=0u;
        }
    }
    if(memcmp(&before,status,sizeof(before))!=0)l->meeting_status_dirty=true;
#else
    (void)now;
#endif
}
static bool storage_full(const comp_link_t *l)
{
    if(l->segmented)return l->segmented->config.pipeline->failure==COMP_SEG_FULL;
#ifndef COMPANION_RECORDING_SEGMENTED_ONLY
    return l->config.recorder->last_fault_reason==COMP_WBA_RECORDING_FAULT_STORAGE_FULL;
#else
    return false;
#endif
}
static bool meeting_control(comp_link_t *l,const companion_gatt_meeting_control_v1_t *request,uint32_t now)
{
    companion_gatt_meeting_status_v1_t *status=&l->config.features->meeting;
    bool ok;
    if(request->schema_version!=1u||request->request_id==0u||request->flags!=0u||
       request->reserved!=0u||request->profile_id!=2u||request->command<1u||request->command>3u){
        meeting_reject(l,request->request_id);return false;
    }
    if(request->command==1u) {
        if(l->meeting_start_request_id==request->request_id) {
            if(l->meeting_max_seconds!=request->max_seconds||l->meeting_command!=1u||
               status->state==MEETING_STATE_FINALIZED) {
                meeting_reject(l,request->request_id);return false;
            }
            companion_gatt_meeting_status_v1_t retry=*status;
            retry.request_id=request->request_id;
            (void)meeting_publish(l,&retry);return true;
        }
        if(l->meeting_start_request_id&&status->state!=MEETING_STATE_FINALIZED&&!status->last_error) {
            meeting_reject(l,request->request_id);return false;
        }
        /* A requested fragmented-capacity snapshot authorizes only this
         * exact START, at its original catalog generation. Both CMC2 and
         * CMC3 pass here. Keep the fence after failure so a retry cannot
         * bypass it; a fresh query or disconnect can replace/retire it. */
        if(l->segmented&&l->segmented->capacity_token==request->request_id) {
            comp_wba_recording_pipeline_t *p=l->segmented->config.pipeline;
            uint32_t generation=0u;uint8_t segments=0u;
            const uint8_t *reply=l->segmented->config.transfer->packet;
            if(!p||!reply||memcmp(reply,"CSN1",4u)||comp_rec_get32(reply+4u)!=request->request_id||
               memcmp(reply+16u,p->config.catalog->uid,12u)||comp_rec_get32(reply+28u)!=comp_rec_crc(reply,28u)||
               !p->config.capacity_snapshot||!p->config.capacity_snapshot(p,&generation,&segments)||
               generation!=comp_rec_get32(reply+8u)) {
                meeting_reject(l,request->request_id);return false;
            }
        }
        if(l->segmented) {
            const comp_wba_recording_pipeline_t *p=l->segmented->config.pipeline;
            uint32_t generation=0u;uint8_t segments=0u;
            /* A current product capacity walk can refuse FULL immediately.
             * Unknown/stale capacity still uses asynchronous preparation;
             * never allocate a durable session or scan NOR merely to reject. */
            if(p->config.capacity_snapshot&&p->config.capacity_snapshot(p,&generation,&segments)&&!segments) {
                meeting_reject_code(l,request->request_id,COMPANION_V1_MEETING_ERROR_STORAGE_FULL);return false;
            }
        }
        uint8_t preparing=l->timeline_prepare;
        uint32_t previous_token=l->config.runtime->record_token;
        if(!l->meeting_extended)l->timeline_prepare=1u;
        ok=!l->maintenance&&comp_runtime_record_start_limited(
            l->config.runtime,request->max_seconds,now)==COMP_RUNTIME_OK;
        l->timeline_prepare=preparing;
        if(!ok){
            uint8_t error=storage_full(l)?COMPANION_V1_MEETING_ERROR_STORAGE_FULL:COMPANION_V1_MEETING_ERROR_REJECTED;
            const comp_runtime_t *r=l->config.runtime;
            if(!l->maintenance && r->record_token!=previous_token && r->last_result==COMP_RUNTIME_UNAVAILABLE) {
                if(r->record_stop_reason==COMP_RECORD_STOP_LOW_BATTERY)error=COMPANION_V1_MEETING_ERROR_POWER_LOW;
                else if(r->record_stop_reason==COMP_RECORD_STOP_POWER_UNKNOWN)error=COMPANION_V1_MEETING_ERROR_POWER_UNKNOWN;
            }
            meeting_reject_code(
                l,request->request_id,error);
            return false;
        }
        if(l->segmented&&l->segmented->capacity_token==request->request_id)
            l->segmented->capacity_token=0u;
        memset(status,0,sizeof(*status));status->schema_version=1u;
        status->request_id=request->request_id;status->flags=request->flags;
        l->meeting_start_request_id=request->request_id;
        l->meeting_record_token=l->config.runtime->record_token;l->meeting_command=1u;
        l->meeting_max_seconds=request->max_seconds;
        l->remote_limit_ms=(uint32_t)request->max_seconds*1000u;
        l->remote_record_token=l->meeting_record_token;l->meeting_status_dirty=true;
        return true;
    }
    if(l->meeting_command==request->command&&status->request_id==request->request_id) {
        (void)meeting_publish(l,status);return true;
    }
    if(!l->meeting_start_request_id) {meeting_reject(l,request->request_id);return false;}
    if(request->command==2u) {
        if(status->state==MEETING_STATE_FINALIZED) {
            status->request_id=request->request_id;status->last_error=0u;
        } else {
            ok=comp_runtime_record(l->config.runtime,false,now)==COMP_RUNTIME_OK;
            if(!ok){meeting_reject(l,request->request_id);return false;}
            status->request_id=request->request_id;status->last_error=0u;
            l->remote_limit_ms=0u;l->remote_record_token=0u;
        }
    } else {
        if(status->state!=MEETING_STATE_FINALIZED) {meeting_reject(l,request->request_id);return false;}
        status->request_id=request->request_id;status->last_error=0u;
    }
    l->meeting_command=request->command;l->meeting_status_dirty=true;return true;
}
static bool meeting_control_v2(comp_link_t *l,const uint8_t *wire,uint32_t now)
{
    uint32_t request_id=comp_rec_get32(wire+36u);
    const comp_wba_recording_pipeline_t *p=l->segmented?l->segmented->config.pipeline:NULL;
    uint64_t session=comp_rec_get64(wire+28u);
    uint32_t start=comp_rec_get32(wire+40u);
    if(!p||memcmp(wire,"CMC2",4u)||wire[4]!=2u||wire[7]||wire[46]||wire[47]||
        comp_rec_crc(wire,48u)!=comp_rec_get32(wire+48u)||
        memcmp(wire+8u,p->config.catalog->uid,12u)||
        comp_rec_get64(wire+20u)!=p->config.catalog->epoch||
        (wire[5]==1u?(session!=0u||start!=request_id):
            (!session||!p->engine_bound||p->token!=l->meeting_record_token||
             session!=p->config.recording->active.descriptor.session_id||start!=l->meeting_start_request_id))) {
        meeting_reject(l,request_id);return false;
    }
    companion_gatt_meeting_control_v1_t request={0};
    request.schema_version=1u;request.command=wire[5];request.profile_id=wire[6];
    request.request_id=request_id;request.max_seconds=(uint16_t)((uint16_t)wire[44]|((uint16_t)wire[45]<<8u));
    if(request.command==1u) {
        if(l->meeting_extended&&l->meeting_start_request_id==request_id){meeting_reject(l,request_id);return false;}
        bool old=l->meeting_extended;l->meeting_extended=false;
        bool accepted=meeting_control(l,&request,now);
        if(!accepted)l->meeting_extended=old;
        else {l->meeting_control_sequence=0u;l->meeting_timeline=false;}
        return accepted;
    }
    if(l->meeting_extended){meeting_reject(l,request_id);return false;}
    return meeting_control(l,&request,now);
}
bool comp_link_recording_timeline_requested(const comp_link_t *l,uint32_t token)
{return l&&token&&l->config.runtime->record_token==token&&
    (!l->timeline_prepare||l->timeline_prepare==3u);}
/* CMC3 56B: CMC2 identity/start fields; flag1@7 opts in at START;
 * control sequence u32@48; CRC@52. CMS3 80B carries exact sequence@60,
 * timeline flag@64 and accepted command@65. Never acknowledge PAUSED or
 * FINALIZED before the actual engine/pipeline completes that transition. */
static bool meeting_control_v3(comp_link_t *l,const uint8_t *wire,uint32_t now)
{
    comp_wba_recording_pipeline_t *p=l->segmented?l->segmented->config.pipeline:NULL;
    const uint8_t command=wire[5];const uint32_t request_id=comp_rec_get32(wire+36u);
    const uint32_t sequence=comp_rec_get32(wire+48u),start=comp_rec_get32(wire+40u);
    const uint64_t session=comp_rec_get64(wire+28u);
    if(!p||memcmp(wire,"CMC3",4u)||wire[4]!=3u||command<1u||command>5u||wire[6]!=2u||
       wire[7]>1u||wire[46]||wire[47]||!request_id||!start||l->maintenance||
       comp_rec_crc(wire,52u)!=comp_rec_get32(wire+52u)||
       memcmp(wire+8u,p->config.catalog->uid,12u)||comp_rec_get64(wire+20u)!=p->config.catalog->epoch||
       (command==1u?(session||start!=request_id||sequence):
        (!l->meeting_extended||wire[7]||!sequence||!session||!p->engine_bound||p->token!=l->meeting_record_token||
         session!=p->config.recording->active.descriptor.session_id||start!=l->meeting_start_request_id))||
       (command!=1u&&(wire[44]||wire[45]))||
       ((command==4u||command==5u)&&sequence==UINT32_MAX)) {
        meeting_reject(l,request_id);return false;
    }
    companion_gatt_meeting_status_v1_t *status=&l->config.features->meeting;
    if(command!=1u&&sequence==l->meeting_control_sequence) {
        if(command!=l->meeting_command||request_id!=status->request_id){meeting_reject(l,request_id);return false;}
        (void)meeting_publish(l,status);return true;
    }
    if(command!=1u&&sequence<l->meeting_control_sequence){meeting_reject(l,request_id);return false;}
    if(command==1u&&l->meeting_extended&&l->meeting_start_request_id==request_id) {
        if(l->meeting_timeline!=(wire[7]==1u)||l->meeting_max_seconds!=
           (uint16_t)((uint16_t)wire[44]|((uint16_t)wire[45]<<8u))||status->state==MEETING_STATE_FINALIZED) {
            meeting_reject(l,request_id);return false;
        }
        companion_gatt_meeting_status_v1_t retry=*status;retry.request_id=request_id;
        (void)meeting_publish(l,&retry);return true;
    }
    if(command==4u||command==5u) {
        if(!l->meeting_timeline||p->stop_requested||
           !(command==4u?comp_wba_recording_pipeline_pause(p,l->meeting_record_token,sequence):
             comp_wba_recording_pipeline_resume(p,l->meeting_record_token,sequence))) {
            meeting_reject(l,request_id);return false;
        }
        status->request_id=request_id;status->last_error=0u;l->meeting_command=command;
        l->meeting_control_sequence=sequence;l->meeting_status_dirty=true;return true;
    }
    companion_gatt_meeting_control_v1_t request={0};request.schema_version=1u;request.command=command;request.profile_id=2u;
    request.request_id=request_id;request.max_seconds=(uint16_t)((uint16_t)wire[44]|((uint16_t)wire[45]<<8u));
    bool previous_extended=l->meeting_extended,previous_timeline=l->meeting_timeline;
    if(command==1u){l->meeting_extended=true;l->meeting_timeline=wire[7]==1u;l->timeline_prepare=l->meeting_timeline?3u:2u;}
    bool accepted=meeting_control(l,&request,now);l->timeline_prepare=0u;
    if(!accepted){l->meeting_extended=previous_extended;l->meeting_timeline=previous_timeline;return false;}
    if(command==1u) {
        /* The logical recorder counts captured10ms blocks. A paused mic must
         * not cancel the limit or restart a wall-clock timer on RESUME. */
        l->remote_limit_ms=l->config.runtime->record_limit_seconds*1000u;
        l->config.runtime->record_limit_seconds=0u;
    }
    l->meeting_control_sequence=sequence;return true;
}
bool comp_link_heavy_io_allowed(void *context)
{
    const comp_link_t *l=context;
    if(l->segmented&&(l->segmented->negotiated&2u)) {
        const comp_runtime_t *r=l->config.runtime;
        const comp_wba_recording_pipeline_t *p=l->segmented->config.pipeline;
        /* Only the sealed-transfer pump gets the read-only reclaim lease.
         * All mutation/exclusive callers retain recording_io_idle's barrier. */
        return !l->maintenance&&!r->capture_active&&!r->command_pending&&!r->start_pending&&!r->prepare_pending&&
            (p->state==COMP_PIPE_IDLE||p->state==COMP_PIPE_FINISHED)&&!p->config.recording->microphone_active&&
            comp_wba_recording_radio_read_allowed(l->segmented);
    }
    if(l->segmented)return !l->maintenance&&!l->segmented->consume_pending&&recording_io_idle(l)&&
        comp_wba_recording_pipeline_page_available(l->segmented->config.pipeline);
#ifndef COMPANION_RECORDING_SEGMENTED_ONLY
    return !l->maintenance && !l->io.legacy.reclaim.active && recording_io_idle(l);
#else
    return false;
#endif
}
#ifndef COMPANION_RECORDING_SEGMENTED_ONLY
static bool live_entry(void *context,uint32_t id,comp_recording_journal_entry_t *entry)
{
    const comp_link_t *l=context;
    return !l->maintenance && !l->io.legacy.reclaim.active &&
        l->config.recorder->entry.recording_id==id &&
        comp_wba_recording_service_live_entry(l->config.recorder,entry);
}
static bool live_read_allowed(void *context)
{
    const comp_link_t *l=context;
    const comp_wba_recording_service_t *recorder=l->config.recorder;
    if(l->maintenance || l->io.legacy.reclaim.active)return false;
    if(recording_io_idle(l))return true;
    /* Audio is serviced first by product_app. One <=192-byte read or notify
     * can use an otherwise idle foreground slot; drains/programs win. The
     * platform's complete-iteration 10ms deadline still applies. */
    return l->config.runtime->capture_active &&
        recorder->state==COMP_WBA_RECORDING_CAPTURING &&
        recorder->ring_count==0u && recorder->stage_length<256u;
}
static bool notify(void *c,const uint8_t *bytes,uint16_t n)
{
    comp_link_t *l=c;
    const companion_gatt_char_id_t lane = (l->transfer.packet_sequence & 1u) &&
        l->subscribed[COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B]
            ? COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B
            : COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL;
    return l->connected && l->encrypted && l->subscribed[COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL] &&
        publish(l,lane,bytes,n);
}
static bool transfer_idle(const comp_link_t *l)
{
    return l->transfer.state!=COMP_WBA_RECORDING_TRANSFER_ACTIVE &&
        l->transfer.state!=COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED;
}
static const comp_recording_journal_entry_t *find_reclaimable(
    comp_link_t *l,comp_recording_journal_state_t state)
{
    const comp_recording_journal_entry_t *oldest=NULL;
    uint32_t count=comp_recording_journal_count(l->config.journal);
    for(uint32_t i=0u;i<count;++i) {
        const comp_recording_journal_entry_t *entry=
            comp_recording_journal_at(l->config.journal,i);
        if(!entry || entry->sync_state!=(uint8_t)state)continue;
        /* ACKED is host proof persisted by ack_complete, never a partial
         * transfer offset. ERASING may also follow explicit local deletion. */
        if(state==COMP_RECORDING_JOURNAL_ACKED &&
           (entry->total_length==0u || entry->acked_offset!=entry->total_length))continue;
        if(!oldest || (int32_t)(entry->recording_id-oldest->recording_id)<0)
            oldest=entry;
    }
    return oldest;
}
static void select_reclaim(comp_link_t *l,
                           const comp_recording_journal_entry_t *entry)
{
    if(!entry)return;
    l->io.legacy.reclaim.recording_id=entry->recording_id;
    l->io.legacy.reclaim.cursor=0u;l->io.legacy.reclaim.retry_ms=0u;
    l->io.legacy.reclaim.last_result=COMP_RECORDING_JOURNAL_OK;
    l->io.legacy.reclaim.retry_pending=false;
    l->io.legacy.reclaim.active=true;l->io.legacy.reclaim.complete=false;
}
static void resume_erasing(comp_link_t *l)
{
    select_reclaim(l,find_reclaimable(l,COMP_RECORDING_JOURNAL_ERASING));
}
static void recover_consumed(comp_link_t *l)
{
    if(l->maintenance || l->io.legacy.reclaim.active || l->io.legacy.reclaim.complete ||
       l->io.legacy.reclaim.response_pending || !recording_io_idle(l) || !transfer_idle(l))return;
    /* Finish already committed erasures first. The ACKED/ERASING commit gap
     * is repaired in the same bounded worker, without a connection or a new
     * host request. Discovery itself does not write NOR. */
    resume_erasing(l);
    if(!l->io.legacy.reclaim.active)
        select_reclaim(l,find_reclaimable(l,COMP_RECORDING_JOURNAL_ACKED));
}
bool comp_link_discard_all_confirmed(comp_link_t *l)
{
    /* V2 explicit user discard needs its own loss offer/physical worker. It
     * cannot reinterpret the old V1 catalog as the new shared pool. */
    if(l&&l->segmented)return false;
    if(!l || l->maintenance || !recording_io_idle(l) || l->io.legacy.reclaim.active || l->io.legacy.reclaim.response_pending)return false;
    if(comp_recording_journal_discard_all_confirmed(l->config.journal)!=COMP_RECORDING_JOURNAL_OK)return false;
    l->io.legacy.discard.offered=false;l->io.legacy.discard.accepted=false;
    comp_wba_recording_transfer_cancel(&l->transfer);resume_erasing(l);return true;
}
bool comp_link_init(comp_link_t *l,const comp_link_config_t *config)
{
    comp_wba_recording_transfer_config_t transfer;
    if(!l || !config || !config->runtime || !config->recorder || !config->journal ||
       !config->features || !config->publish)return false;
    memset(l,0,sizeof(*l));l->config=*config;
    transfer=(comp_wba_recording_transfer_config_t){config->journal,notify,comp_link_heavy_io_allowed,l,live_entry,live_read_allowed};
    if(!comp_wba_recording_transfer_init(&l->transfer,&transfer))return false;
    config->features->meeting.schema_version=1u;
    config->features->meeting.state=MEETING_STATE_IDLE;
    resume_erasing(l);
    return true;
}
#else
bool comp_link_discard_all_confirmed(comp_link_t *l)
{
    /* Segmented loss consent is a separate worker. Never interpret the old
     * journal or offer as ownership of the new dynamic pool. */
    (void)l;return false;
}
#endif
static bool segmented_publish(void *context,companion_gatt_char_id_t id,const uint8_t *p,uint16_t n)
{
    comp_link_t *l=context;
    /* V2 keeps the same packet framing and optional second recording lane
     * as V1. The receiver already subscribes to both, but the segmented
     * adapter previously sent every long value through the first attribute.
     * Keep a retry on its sequence's lane; the GATT owner fences any retired
     * subscription's staging before falling back to the primary lane. */
    if(id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL&&
       (l->transfer.packet_sequence&1u)&&l->subscribed[COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B])
        id=COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B;
    return publish(l,id,p,n);
}
static bool segmented_discard_random(void *context,uint32_t *out)
{
    comp_link_t *l=context;comp_runtime_t *r=l->config.runtime;
    return r&&r->config.random_u32&&r->config.random_u32(r->config.context,out);
}
static bool segmented_discard_acquire(void *context)
{
    comp_link_t *l=context;
    if(!l||!l->segmented||l->maintenance||!recording_io_idle(l)||
       l->config.runtime->menu_pending||comp_wba_recording_radio_busy(l->segmented))return false;
    return comp_wba_recording_pipeline_discard_acquire(l->segmented->config.pipeline);
}
static bool segmented_discard_release(void *context)
{
    comp_link_t *l=context;
    return l&&l->segmented&&comp_wba_recording_pipeline_discard_release(l->segmented->config.pipeline);
}
bool comp_link_init_segmented(comp_link_t *l,const comp_link_config_t *config,
    comp_wba_recording_radio_t *radio,comp_wba_recording_pipeline_t *pipeline,uint16_t capacity)
{
    if(!l||!config||!config->runtime||!config->features||!config->publish||!radio||!pipeline||
       config->recorder||config->journal)return false;
    memset(l,0,sizeof(*l));l->config=*config;l->segmented=radio;
    static const comp_wba_recording_discard_hooks_t discard_hooks={
        segmented_discard_random,segmented_discard_acquire,segmented_discard_release};
    comp_wba_recording_radio_config_t cfg={pipeline,&l->transfer,segmented_publish,l,capacity,&discard_hooks};
    if(!comp_wba_recording_radio_init(radio,&cfg)){l->segmented=NULL;return false;}
    config->features->meeting.schema_version=1u;config->features->meeting.state=MEETING_STATE_IDLE;
    return true;
}
void comp_link_connection(comp_link_t *l,bool connected,bool encrypted,uint32_t now)
{
    if(!l)return;
    bool changed=l->connected!=connected || l->encrypted!=(connected&&encrypted);
#ifndef COMPANION_RECORDING_SEGMENTED_ONLY
    if(!l->segmented && (!connected || !encrypted || !l->connected)) {
        /* A confirmation can never cross disconnection or a new encrypted
         * connection. Already committed ERASING work must still finish. */
        l->io.legacy.discard.offered=false;l->io.legacy.discard.connection_valid=false;
    }
#endif
    /* An encryption-change event must not clear already enabled subscriptions. */
    if(!connected || !l->connected)memset(l->subscribed,0,sizeof(l->subscribed));
    l->connected=connected;l->encrypted=connected&&encrypted;
    if(!l->encrypted)l->meeting_reject_error=0u;
    /* A READ may precede CCCD subscription or the first recorder command.
     * Refresh on each protected link so a freshly registered zero-filled
     * attribute, or an old offline snapshot, cannot masquerade as status.
     * The normal poll publishes with CRC/identity and retries backpressure;
     * no recorder command, capture or sequence is synthesized here. */
    if(changed&&l->encrypted)l->meeting_status_dirty=true;
    if(l->segmented && changed) {
        comp_wba_recording_radio_connection(l->segmented,l->encrypted);
        comp_wba_recording_radio_consume_subscription(l->segmented,
            l->encrypted&&l->subscribed[COMPANION_GATT_CHAR_DELETE_PRIVACY]);
    }
#ifndef COMPANION_RECORDING_SEGMENTED_ONLY
    else comp_wba_recording_transfer_set_connected(&l->transfer,l->encrypted);
#endif
    comp_runtime_set_connected(l->config.runtime,connected,now);
    l->next_status_ms=now;
}
static void list(comp_link_t *l)
{
#ifndef COMPANION_RECORDING_SEGMENTED_ONLY
    if(l->segmented)return; /* only negotiated, correlated V2 pages */
    uint8_t value[248];
    if(!l->connected || !l->encrypted)return;
    size_t n=comp_wba_recording_transfer_build_list(&l->transfer,value,sizeof(value));
    if(n)(void)publish(l,COMPANION_GATT_CHAR_RECORDING_LIST,value,(uint16_t)n);
#else
    (void)l; /* V2 directories require an explicit correlated request. */
#endif
}
#ifndef COMPANION_RECORDING_SEGMENTED_ONLY
static void pull_error(comp_link_t *l,uint32_t id,uint32_t offset,uint32_t result)
{
    companion_recording_adapter_header_t h={0};
    h.schema_version=1; h.flags=COMPANION_RECORDING_ADAPTER_ERROR_FLAG;
    h.recording_id=id;h.byte_offset=offset;h.packet_crc32=result;
    (void)publish(l,COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,&h,sizeof(h));
}
static bool reclaim_request_matches(
    const companion_gatt_delete_privacy_v1_t *request,
    const comp_recording_journal_entry_t *entry)
{
    return request->recording_id==entry->recording_id &&
        request->validated_total_length==entry->total_length &&
        memcmp(request->validated_sha256,entry->sha256,
               COMP_RECORDING_JOURNAL_SHA256_BYTES)==0;
}
/* Request IDs are transport correlation, not recording identity. */
static bool same_reclaim_proof(const companion_gatt_delete_privacy_v1_t *a,
                               const companion_gatt_delete_privacy_v1_t *b)
{
    return a->schema_version==b->schema_version && a->operation==b->operation &&
        a->flags==b->flags && a->recording_id==b->recording_id &&
        a->validated_total_length==b->validated_total_length &&
        !memcmp(a->validated_sha256,b->validated_sha256,COMP_RECORDING_JOURNAL_SHA256_BYTES);
}
static void reject_delete(comp_link_t *l,
                          const companion_gatt_delete_privacy_v1_t *request)
{
    companion_gatt_delete_privacy_v1_t response=*request;
    response.flags|=1u;
    (void)publish(l,COMPANION_GATT_CHAR_DELETE_PRIVACY,&response,sizeof(response));
}
static bool accept_delete(comp_link_t *l,
                          const companion_gatt_delete_privacy_v1_t *request)
{
    const comp_recording_journal_entry_t *entry;
    if((l->io.legacy.discard.accepted && (l->io.legacy.reclaim.active || l->io.legacy.reclaim.complete || l->io.legacy.reclaim.response_pending)) ||
       l->maintenance || !recording_io_idle(l) || request->schema_version!=1u || request->operation!=1u ||
       request->recording_id==0u)return false;
    if(l->io.legacy.reclaim.complete && l->io.legacy.reclaim.response_pending) {
        if(!same_reclaim_proof(request,&l->io.legacy.reclaim.response))return false;
        l->io.legacy.reclaim.response=*request;return true;
    }
    entry=comp_recording_journal_find(l->config.journal,request->recording_id);
    /* Retain one exact completed proof in RAM. Type allocates a fresh request
     * ID on reconnect; replay is allowed only while mounted, after removal,
     * and never if a current entry with that ID or another worker exists. */
    if(!entry && l->config.journal && l->config.journal->mounted &&
       !l->io.legacy.reclaim.active && !l->io.legacy.reclaim.complete &&
       !l->io.legacy.reclaim.response_pending && l->io.legacy.reclaim.receipt_valid &&
       same_reclaim_proof(request,&l->io.legacy.reclaim.response)) {
        l->io.legacy.reclaim.response=*request;l->io.legacy.reclaim.response_pending=true;
        l->io.legacy.reclaim.complete=true;return true;
    }
    if(l->io.legacy.reclaim.active) {
        if(l->io.legacy.reclaim.recording_id!=request->recording_id || !entry ||
           !reclaim_request_matches(request,entry))return false;
        l->io.legacy.reclaim.receipt_valid=false;
        l->io.legacy.reclaim.response=*request;l->io.legacy.reclaim.response_pending=true;
        return true;
    }
    if(!entry || (l->transfer.state==COMP_WBA_RECORDING_TRANSFER_ACTIVE ||
                  l->transfer.state==COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED))return false;
    if((entry->sync_state!=COMP_RECORDING_JOURNAL_UNSYNCED &&
        entry->sync_state!=COMP_RECORDING_JOURNAL_ACKED &&
        entry->sync_state!=COMP_RECORDING_JOURNAL_ERASING) ||
       !reclaim_request_matches(request,entry))return false;
    /* GATT event dispatch only accepts an authenticated exact host receipt.
     * Both durable catalog transactions belong to separate foreground polls,
     * never to a write callback that must let the stack return its ATT reply.
     * A reset before the first commit leaves UNSYNCED protected and retryable. */
    l->io.legacy.reclaim.recording_id=entry->recording_id;l->io.legacy.reclaim.cursor=0u;
    l->io.legacy.discard.offered=false;l->io.legacy.discard.accepted=false;
    l->io.legacy.reclaim.retry_ms=0u;l->io.legacy.reclaim.active=true;l->io.legacy.reclaim.complete=false;
    l->io.legacy.reclaim.last_result=COMP_RECORDING_JOURNAL_OK;l->io.legacy.reclaim.retry_pending=false;
    l->io.legacy.reclaim.receipt_valid=false;
    l->io.legacy.reclaim.response=*request;l->io.legacy.reclaim.response_pending=true;
    return true;
}
static bool discard_matches(const companion_recording_discard_v2_t *a,
                            const companion_recording_discard_v2_t *b)
{
    return memcmp((const uint8_t *)a+4u,(const uint8_t *)b+4u,sizeof(*a)-4u)==0;
}
static bool discard_reply(comp_link_t *l,const companion_recording_discard_v2_t *request,
                          uint16_t flags)
{
    companion_recording_discard_v2_t response=*request;
    response.flags=flags;
    return publish(l,COMPANION_GATT_CHAR_DELETE_PRIVACY,&response,sizeof(response));
}
static bool discard_control(comp_link_t *l,
                            const companion_recording_discard_v2_t *request,uint32_t now)
{
    comp_recording_journal_entry_t candidate;
    uint32_t largest_after;
    comp_runtime_t *r=l->config.runtime;
    if(request->schema_version!=2u || request->flags || !request->request_id ||
       request->requested_seconds>65535u) goto refuse;
    if(request->operation==COMPANION_RECORDING_DISCARD_PREVIEW) {
        companion_recording_discard_v2_t empty={0};
        empty.schema_version=2u;empty.operation=COMPANION_RECORDING_DISCARD_PREVIEW;
        empty.request_id=request->request_id;empty.requested_seconds=request->requested_seconds;
        if(memcmp(request,&empty,sizeof(empty)) || l->maintenance || !recording_io_idle(l) ||
           r->menu_pending || !transfer_idle(l) || l->io.legacy.reclaim.active || l->io.legacy.reclaim.complete ||
           l->io.legacy.reclaim.response_pending) goto refuse;
        l->io.legacy.discard.offered=false;l->io.legacy.discard.connection_valid=false;
        if(!comp_recording_journal_discard_candidate(l->config.journal,request->requested_seconds,
                                                   &candidate,&largest_after)) {
            (void)discard_reply(l,request,COMPANION_RECORDING_DISCARD_NO_CANDIDATE);return true;
        }
        if(!r->config.random_u32 ||
           !r->config.random_u32(r->config.context,&empty.token[0]) ||
           !r->config.random_u32(r->config.context,&empty.token[1]) ||
           (!empty.token[0] && !empty.token[1])) goto refuse;
        empty.recording_id=candidate.recording_id;empty.total_length=candidate.total_length;
        memcpy(empty.sha256,candidate.sha256,sizeof(empty.sha256));
        empty.catalog_generation=l->config.journal->catalog.generation;
        empty.started_unix_s=candidate.started_unix_s;empty.duration_ms=candidate.duration_ms;
        empty.reserved_bytes=candidate.reserved_bytes;empty.largest_extent_after=largest_after;
        empty.expires_in_ms=COMPANION_RECORDING_DISCARD_TTL_MS;
        l->io.legacy.discard.offer=empty;l->io.legacy.discard.issued_ms=now;
        l->io.legacy.discard.offered=true;l->io.legacy.discard.accepted=false;l->io.legacy.discard.connection_valid=true;
        if(!discard_reply(l,&empty,0u))l->io.legacy.discard.offered=false;
        return true;
    }
    if(request->operation==COMPANION_RECORDING_DISCARD_CONFIRM &&
       l->io.legacy.discard.accepted && l->io.legacy.discard.connection_valid &&
       discard_matches(request,&l->io.legacy.discard.offer)) {
        (void)discard_reply(l,request,l->io.legacy.discard.offer.flags);return true;
    }
    if(!l->io.legacy.discard.offered || !l->io.legacy.discard.connection_valid ||
       now-l->io.legacy.discard.issued_ms>=COMPANION_RECORDING_DISCARD_TTL_MS ||
       !discard_matches(request,&l->io.legacy.discard.offer)) goto refuse;
    if(request->operation==COMPANION_RECORDING_DISCARD_CANCEL) {
        l->io.legacy.discard.offered=false;
        (void)discard_reply(l,request,COMPANION_RECORDING_DISCARD_CANCELLED);return true;
    }
    if(request->operation!=COMPANION_RECORDING_DISCARD_CONFIRM || l->maintenance ||
       !recording_io_idle(l) || r->menu_pending || !transfer_idle(l) || l->io.legacy.reclaim.active ||
       l->io.legacy.reclaim.complete || l->io.legacy.reclaim.response_pending) goto refuse;
    /* Check the full proposal against a fresh, read-only candidate as well as
     * the catalog generation. Never turn a stale identity into delete-all. */
    if(!comp_recording_journal_discard_candidate(l->config.journal,request->requested_seconds,
                                               &candidate,&largest_after) ||
       candidate.recording_id!=request->recording_id ||
       largest_after!=request->largest_extent_after) goto refuse;
    l->io.legacy.discard.offered=false;
    if(comp_recording_journal_discard_oldest_confirmed(l->config.journal,
        request->catalog_generation,request->recording_id,request->total_length,
        request->sha256)!=COMP_RECORDING_JOURNAL_OK) goto refuse;
    l->io.legacy.reclaim.receipt_valid=false;
    l->io.legacy.discard.accepted=true;l->io.legacy.discard.offer.operation=COMPANION_RECORDING_DISCARD_CONFIRM;
    l->io.legacy.discard.offer.flags=COMPANION_RECORDING_DISCARD_PENDING;
    select_reclaim(l,comp_recording_journal_find(l->config.journal,request->recording_id));
    l->io.legacy.reclaim.response_pending=true;
    (void)discard_reply(l,request,COMPANION_RECORDING_DISCARD_PENDING);return true;
refuse:
    (void)discard_reply(l,request,COMPANION_RECORDING_DISCARD_REFUSED);return false;
}
#endif
void comp_link_event(comp_link_t *l,const companion_gatt_event_t *e,uint32_t now)
{
    bool ok=false;
    if(!l || !e || (unsigned)e->char_id>=COMPANION_GATT_CHAR_COUNT)return;
    if(e->type!=COMPANION_GATT_EVENT_WRITE) {
        /* CCCD events belong to the current encrypted connection.  Ignoring
         * stale/pre-encryption events prevents them from arming a later link. */
        if(!l->connected || !l->encrypted) {++l->rejected_writes;return;}
        if(e->type!=COMPANION_GATT_EVENT_NOTIFY_ENABLED &&
           e->type!=COMPANION_GATT_EVENT_NOTIFY_DISABLED) {
            ++l->rejected_writes;return;
        }
        l->subscribed[e->char_id]=e->type==COMPANION_GATT_EVENT_NOTIFY_ENABLED;
        if(l->segmented && e->char_id==COMPANION_GATT_CHAR_DELETE_PRIVACY)
            comp_wba_recording_radio_consume_subscription(l->segmented,l->subscribed[e->char_id]);
        if(l->segmented&&!l->subscribed[e->char_id]&&
           (e->char_id==COMPANION_GATT_CHAR_RECORDING_CONTROL||e->char_id==COMPANION_GATT_CHAR_RECORDING_LIST||
            e->char_id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL||e->char_id==COMPANION_GATT_CHAR_DELETE_PRIVACY))
            comp_wba_recording_radio_unsubscribe(l->segmented,e->char_id);
        if(e->char_id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL && !l->subscribed[e->char_id])
            comp_wba_recording_transfer_cancel(&l->transfer);
        if(e->char_id==COMPANION_GATT_CHAR_RECORDING_LIST)list(l);
        if(e->char_id==COMPANION_GATT_CHAR_MEETING_STATUS&&l->subscribed[e->char_id])
            (void)meeting_publish(l,&l->config.features->meeting);
        l->next_status_ms=now;return;
    }
    if(!l->connected || !l->encrypted) {++l->rejected_writes;return;}
    if(comp_wba_recording_radio_claims(e->char_id,e->payload,e->payload_len)) {
        bool subscribed=l->subscribed[e->char_id];
        if(e->char_id==COMPANION_GATT_CHAR_RECORDING_CONTROL&&e->payload_len>=2u&&
           (e->payload[1]==0x20u||e->payload[1]==0x23u))
            subscribed=subscribed&&l->subscribed[COMPANION_GATT_CHAR_RECORDING_LIST];
        if(!l->segmented||l->maintenance||!comp_wba_recording_radio_write(l->segmented,
            e->char_id,e->payload,e->payload_len,subscribed))++l->rejected_writes;
        return;
    }
    if(l->segmented&&(e->char_id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL||
        e->char_id==COMPANION_GATT_CHAR_DELETE_PRIVACY)) {++l->rejected_writes;return;}
    if(e->char_id==COMPANION_GATT_CHAR_MEETING_CONTROL && e->payload_len==56u) {
        ok=meeting_control_v3(l,e->payload,now);
    } else if(e->char_id==COMPANION_GATT_CHAR_MEETING_CONTROL && e->payload_len==52u) {
        ok=meeting_control_v2(l,e->payload,now);
#ifndef COMPANION_RECORDING_SEGMENTED_ONLY
    /* The WBA product requires negotiated UID/epoch/session controls. Old
     * unscoped START/STOP is retained only for the separate V1/WB port. */
    } else if(e->char_id==COMPANION_GATT_CHAR_MEETING_CONTROL && e->payload_len==sizeof(companion_gatt_meeting_control_v1_t)) {
        companion_gatt_meeting_control_v1_t request;
        memcpy(&request,e->payload,sizeof(request));ok=meeting_control(l,&request,now);
    } else if(e->char_id==COMPANION_GATT_CHAR_RECORDING_CONTROL && e->payload_len==sizeof(companion_gatt_recording_control_v1_t)) {
        companion_gatt_recording_control_v1_t request;
        memcpy(&request,e->payload,sizeof(request));
        request.privacy_flags=(uint8_t)(request.privacy_flags & 0x3fu);
        if(request.schema_version==1 && (request.command==2 || (!l->maintenance && request.command==1 && request.profile_id==2))) {
            ok=(request.command==1
                ? comp_runtime_record_start_limited(l->config.runtime,request.max_seconds,now)
                : comp_runtime_record(l->config.runtime,false,now))==COMP_RUNTIME_OK;
            if(ok && request.command==1) {
                l->remote_limit_ms=(uint32_t)request.max_seconds*1000u;
                l->remote_record_token=l->config.runtime->record_token;
            } else if(ok) {
                l->remote_limit_ms=0u;l->remote_record_token=0u;
            }
        }
        if(!ok) {
            request.privacy_flags|=COMPANION_GATT_RECORDING_STATUS_ERROR;
            if(request.command==1u &&
               storage_full(l))
                request.privacy_flags|=
                    COMPANION_GATT_RECORDING_STATUS_STORAGE_FULL;
        }
        (void)publish(l,e->char_id,&request,sizeof(request));
    } else if(e->char_id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL && e->payload_len==sizeof(companion_recording_adapter_request_t)) {
        companion_recording_adapter_request_t request;comp_wba_recording_transfer_result_t result;
        memcpy(&request,e->payload,sizeof(request));
        result=l->subscribed[e->char_id]?comp_wba_recording_transfer_start(&l->transfer,&request):COMP_WBA_RECORDING_TRANSFER_NOT_CONNECTED;
        ok=result==COMP_WBA_RECORDING_TRANSFER_OK;
        if(!ok)pull_error(l,request.recording_id,request.byte_offset,result);
#endif
    } else if(e->char_id==COMPANION_GATT_CHAR_SPEAKER_CONTROL && e->payload_len==sizeof(companion_gatt_speaker_control_v1_t)) {
        companion_gatt_speaker_control_v1_t request;memcpy(&request,e->payload,sizeof(request));
        /* Cancel is ownership-checked by the speaker backend and cannot
         * start audio. Allow it while capture/maintenance forbids starts. */
        if(request.schema_version==1 &&
           (request.command==COMPANION_V1_SPEAKER_COMMAND_FIND_STOP ||
            (!l->maintenance && !l->config.runtime->capture_active &&
             !l->config.runtime->command_pending && !l->config.runtime->start_pending)))
            ok=companion_v1_apply_speaker_control(l->config.features,&request,now)==COMPANION_V1_RESULT_OK;
        (void)publish(l,COMPANION_GATT_CHAR_SPEAKER_STATUS,&l->config.features->speaker,sizeof(l->config.features->speaker));
#ifndef COMPANION_RECORDING_SEGMENTED_ONLY
    } else if(e->char_id==COMPANION_GATT_CHAR_DELETE_PRIVACY && e->payload_len==sizeof(companion_recording_discard_v2_t)) {
        companion_recording_discard_v2_t request;
        memcpy(&request,e->payload,sizeof(request));ok=discard_control(l,&request,now);
    } else if(e->char_id==COMPANION_GATT_CHAR_DELETE_PRIVACY && e->payload_len==sizeof(companion_gatt_delete_privacy_v1_t)) {
        companion_gatt_delete_privacy_v1_t request;
        memcpy(&request,e->payload,sizeof(request));
        ok=accept_delete(l,&request);
        /* Schema 1 operation 1 is exact host-copy consume, never user discard.
         * It succeeds only after payload erasure and catalog removal. */
        if(!ok)reject_delete(l,&request);
#endif
    }
    if(!ok)++l->rejected_writes;
}
void comp_link_poll(comp_link_t *l,uint32_t now)
{
    comp_link_poll_with_clock(l,now,NULL,NULL);
}
void comp_link_poll_with_clock(comp_link_t *l,uint32_t now,
    comp_wba_recording_transfer_clock_fn clock,void *clock_context)
{
    comp_link_poll_with_budget(l,now,clock,clock_context,NULL);
}
void comp_link_poll_with_budget(comp_link_t *l,uint32_t now,
    comp_wba_recording_transfer_clock_fn clock,void *clock_context,
    const comp_wba_recording_transfer_budget_t *budget)
{
    comp_runtime_t *r;
    if(!l)return;
    r=l->config.runtime;
    meeting_refresh(l,now);
    /* Updating this READ|NOTIFY attribute refreshes its readable value.
     * CCCD controls notifications in the stack, not database freshness;
     * disconnect clears CCCD while the original recording may seal offline.
     * meeting_publish still requires an encrypted connection. */
    if(l->meeting_reject_error)(void)meeting_reject_flush(l);
    else if(l->meeting_status_dirty&&
            meeting_publish(l,&l->config.features->meeting))l->meeting_status_dirty=false;
#ifndef COMPANION_RECORDING_SEGMENTED_ONLY
    if(!l->segmented&&l->last_catalog_generation!=l->config.journal->catalog.generation) {
        uint32_t bytes=0,count=0;
        for(unsigned i=0;i<COMP_RECORDING_JOURNAL_MAX_ENTRIES;++i) {
            const comp_recording_journal_entry_t *e=&l->config.journal->catalog.entries[i];
            if(e->sync_state==COMP_RECORDING_JOURNAL_UNSYNCED || e->sync_state==COMP_RECORDING_JOURNAL_ACKED) {++count;bytes+=e->total_length;}
        }
        r->menu.browser.recording_count=(uint16_t)count;r->menu.browser.recording_storage_kb=(uint16_t)(bytes/1024u);
        ++r->menu.revision;++r->revision;l->last_catalog_generation=l->config.journal->catalog.generation;
    }
#endif
    if(l->remote_limit_ms) {
        const bool same_request=r->record_token==l->remote_record_token;
        const bool pending=r->command_pending || r->start_pending || r->prepare_pending;
        const bool logical_open=l->meeting_extended&&l->segmented&&
            l->segmented->config.pipeline->state==COMP_PIPE_RECORDING;
        const uint64_t elapsed=logical_open?
            (uint64_t)l->segmented->config.pipeline->config.recording->stats.accepted_pcm_blocks*10u:
            (uint64_t)(now-r->recording_since_ms);
        if(!same_request || (!r->capture_active && !pending&&!logical_open)) {
            /* A failed/cancelled remote start must never stop a later local
             * recording merely because its old duration limit survived. */
            l->remote_limit_ms=0u;l->remote_record_token=0u;
        } else if(r->capture_active &&
                  elapsed>=l->remote_limit_ms) {
            (void)comp_runtime_record_stop(r,COMP_RECORD_STOP_DURATION_LIMIT,now);
            l->remote_limit_ms=0u;l->remote_record_token=0u;
        }
    }
    /* Check before polling transfer: its last read/notify and a recovery
     * catalog write must not share one foreground iteration. */
    if(l->segmented) {
        if(!l->maintenance)comp_wba_recording_radio_poll(l->segmented,clock,clock_context,budget);
        goto status_publish;
    }
#ifndef COMPANION_RECORDING_SEGMENTED_ONLY
    recover_consumed(l);
    (void)comp_wba_recording_transfer_poll_budget(&l->transfer,clock,clock_context,budget);
    if(!l->maintenance && l->io.legacy.reclaim.active && recording_io_idle(l) && transfer_idle(l) &&
       (!l->io.legacy.reclaim.retry_pending || (int32_t)(now-l->io.legacy.reclaim.retry_ms)>=0)) {
        bool complete=false;
        const comp_recording_journal_entry_t *entry=comp_recording_journal_find(
            l->config.journal,l->io.legacy.reclaim.recording_id);
        /* One durable operation per poll: host-copy ACK, ERASING marker,
         * payload erase, or final removal. Never erase an uncommitted receipt. */
        comp_recording_journal_result_t result;
        if(entry && entry->sync_state==COMP_RECORDING_JOURNAL_UNSYNCED) {
            result=l->io.legacy.reclaim.response_pending &&
                reclaim_request_matches(&l->io.legacy.reclaim.response,entry)
                ? comp_recording_journal_ack_complete(l->config.journal,
                    entry->recording_id,l->io.legacy.reclaim.response.validated_total_length,
                    l->io.legacy.reclaim.response.validated_sha256)
                : COMP_RECORDING_JOURNAL_ACK_MISMATCH;
            if(result==COMP_RECORDING_JOURNAL_OK)++l->transfer.stats.acknowledgements;
        } else if(entry && entry->sync_state==COMP_RECORDING_JOURNAL_ACKED) {
            result=comp_recording_journal_begin_reclaim(l->config.journal,l->io.legacy.reclaim.recording_id);
        } else {
            result=comp_recording_journal_reclaim_step(l->config.journal,
                l->io.legacy.reclaim.recording_id,&l->io.legacy.reclaim.cursor,&complete);
        }
        l->io.legacy.reclaim.last_result=result;
        l->io.legacy.reclaim.retry_pending=result!=COMP_RECORDING_JOURNAL_OK;
        if(result!=COMP_RECORDING_JOURNAL_OK)l->io.legacy.reclaim.retry_ms=now+1000u;
        else if(complete) {l->io.legacy.reclaim.active=false;l->io.legacy.reclaim.complete=true;}
    }
    if(l->io.legacy.reclaim.complete && l->io.legacy.reclaim.response_pending &&
       l->connected && l->encrypted && l->subscribed[COMPANION_GATT_CHAR_DELETE_PRIVACY] &&
       (!l->io.legacy.reclaim.retry_pending || (int32_t)(now-l->io.legacy.reclaim.retry_ms)>=0)) {
        bool sent;
        if(l->io.legacy.discard.accepted) {
            l->io.legacy.discard.offer.flags=COMPANION_RECORDING_DISCARD_COMPLETE;
            sent=discard_reply(l,&l->io.legacy.discard.offer,COMPANION_RECORDING_DISCARD_COMPLETE);
        } else sent=publish(l,COMPANION_GATT_CHAR_DELETE_PRIVACY,&l->io.legacy.reclaim.response,
                          sizeof(l->io.legacy.reclaim.response));
        if(sent) {
            /* Keep complete until the common queue-advance step below. A
             * matching Type retry during local clear must not expose an idle
             * gap and make the menu claim all recordings are already gone. */
            l->io.legacy.reclaim.response_pending=false;
            l->io.legacy.reclaim.retry_pending=false;
            if(l->io.legacy.discard.accepted) {
                l->io.legacy.reclaim.receipt_valid=false;
                memset(&l->io.legacy.reclaim.response,0,sizeof(l->io.legacy.reclaim.response));
            } else l->io.legacy.reclaim.receipt_valid=true;
            list(l);
        } else {l->io.legacy.reclaim.retry_ms=now+100u;l->io.legacy.reclaim.retry_pending=true;}
    }
    if(l->io.legacy.reclaim.complete && !l->io.legacy.reclaim.response_pending) {
        l->io.legacy.reclaim.complete=false;l->io.legacy.reclaim.recording_id=0u;
        l->io.legacy.reclaim.cursor=0u;l->io.legacy.reclaim.retry_ms=0u;
        l->io.legacy.reclaim.retry_pending=false;resume_erasing(l);
    }
#endif
status_publish:
    if(l->connected && l->encrypted &&
       ((int32_t)(now-l->next_status_ms)>=0 ||
        l->last_recording_state!=(uint8_t)r->recording)) {
        companion_gatt_device_status_v1_t device={1,0,0,COMPANION_WBA_APP_VERSION,COMPANION_WBA_BUILD_ID,COMPANION_WBA_BOARD_ID,now};
        companion_gatt_battery_charge_v1_t battery={1,255,0,0,0,0};
        companion_gatt_ota_readiness_v1_t ota={1,0,0,255,0,0xFFFFu,0,0,{0}};
        device.active_mode=r->capture_active?1u:0u;
        (void)publish(l,COMPANION_GATT_CHAR_DEVICE_STATUS,&device,sizeof(device));
        (void)publish(l,COMPANION_GATT_CHAR_BATTERY_CHARGE,&battery,sizeof(battery));
        (void)publish(l,COMPANION_GATT_CHAR_IMU_STATUS,&l->config.features->imu,sizeof(l->config.features->imu));
        (void)publish(l,COMPANION_GATT_CHAR_SPEAKER_STATUS,&l->config.features->speaker,sizeof(l->config.features->speaker));
        (void)publish(l,COMPANION_GATT_CHAR_OTA_READINESS,&ota,sizeof(ota));
        list(l); l->next_status_ms=now+1000u;l->last_recording_state=(uint8_t)r->recording;
    }
}
