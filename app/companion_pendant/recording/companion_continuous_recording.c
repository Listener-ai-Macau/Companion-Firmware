#include "companion_continuous_recording.h"
#include "companion_cpu_stage.h"
#include "companion_recording_space_bound.h"

/* Four queued20ms packets plus the codec's half-packet and final padding. */
#define DRAIN_PACKETS ((COMP_CONT_PCM_SLOTS+1u)/2u+1u)
_Static_assert(DRAIN_PACKETS==COMP_REC_BOUND_DRAIN_PACKETS,"planner and actual PCM drain agree");
#define PACKET_CAPACITY (COMPANION_OPUS16_MAX_PACKET+2u)
#define PACKET_OFFSET (COMP_CONT_STAGE_BYTES-PACKET_CAPACITY)
/* Encoding and page commit never run in the same slice. Reuse the empty
 * suffix of the logical stage for the unchanged402B Opus output capacity.
 * A rollover packet stays beyond the old logical length while its last page
 * drains; the separate256B physical commit page is untouched. */
static uint8_t *packet(comp_cont_recording_t *r){return r->stage+PACKET_OFFSET;}

static const uint8_t cop1_header[12]={'C','O','P','1',1u,1u,20u,0u,0x80u,0x3eu,0u,0u};
static bool source_boundary(const comp_cont_recording_t *r)
{return r->config.pause_timeline>=COMP_CONT_TIMELINE_SOURCE_BOUNDARY;}
static bool audio_profile(const comp_cont_recording_t *r)
{return r->config.pause_timeline==COMP_CONT_TIMELINE_AUDIO_PROFILE;}

static bool prepared(const comp_segment_entry_t *e,const comp_segment_audio_t *w)
{
    return e && w && w->prepared && !w->phase && !w->failed && !w->committed_bytes && !w->pages &&
        e->state==COMP_SEG_WRITING && w->entry==e && e->descriptor.codec==3u &&
        !e->descriptor.sample_count && !e->descriptor.encoded_length;
}

static bool append(comp_cont_recording_t *r,const uint8_t *p,size_t n)
{
    if (n>COMP_CONT_STAGE_BYTES-r->stage_length ||
        r->writer.committed_bytes+r->stage_length>comp_segment_audio_capacity(r->active.reserved_bytes) ||
        n>comp_segment_audio_capacity(r->active.reserved_bytes)-r->writer.committed_bytes-r->stage_length)
        return false;
    memmove(r->stage+r->stage_length,p,n);r->stage_length=(uint16_t)(r->stage_length+n);
    return true;
}

static bool append_header(comp_cont_recording_t *r)
{
    uint8_t h[12];memcpy(h,cop1_header,sizeof(h));
    if(r->config.pause_timeline){h[4]=audio_profile(r)?COMP_REC_AUDIO_PROFILE_SCHEMA:source_boundary(r)?COMP_REC_CODEC_BOUNDARY_SCHEMA:
        r->config.pause_timeline==COMP_CONT_TIMELINE_BOOKMARKS?COMP_REC_BOOKMARK_SCHEMA:COMP_REC_TIMELINE_SCHEMA;
        h[7]=audio_profile(r)?15u:source_boundary(r)?7u:h[4]==COMP_REC_BOOKMARK_SCHEMA?3u:1u;}
    if(!append(r,h,sizeof(h)))return false;
    if(source_boundary(r)) {
        uint8_t wire[COMP_REC_CODEC_BOUNDARY_BYTES];
        comp_rec_codec_boundary_t config={(uint64_t)r->active_first_frame*320u,UINT64_MAX,
            r->codec.encoder_delay_samples,COMP_REC_CODEC_CONFIG};
        if(!comp_rec_codec_boundary_encode(&config,wire)||!append(r,wire,sizeof(wire)))return false;
        r->active_non_audio_bytes+=sizeof(wire);
    }
    if(audio_profile(r)) {
        comp_rec_audio_profile_t profile={0};uint8_t wire[COMP_REC_AUDIO_PROFILE_BYTES];
        if(!r->config.audio_profile(r->config.context,&profile) || !comp_rec_audio_profile_encode(&profile,wire))return false;
        const uint32_t crc=comp_rec_get32(wire+92u);
        if(r->active.descriptor.segment_index && crc!=r->audio_profile_crc)return false;
        if(!append(r,wire,sizeof(wire)))return false;
        r->audio_profile_crc=crc;r->active_non_audio_bytes+=sizeof(wire);
    }
    return true;
}
static void observe_clock(comp_cont_recording_t *r,uint32_t now)
{
    r->elapsed_ms+=(uint32_t)(now-r->clock_ms);r->clock_ms=now;
}
static bool begin_pause(comp_cont_recording_t *r)
{
    if(r->stats.accepted_pcm_blocks<2u||(r->stats.accepted_pcm_blocks&1u))return true;
    if(!r->config.microphone(r->config.context,false)) {
        comp_cont_recording_fault(r,COMP_SEG_IO_ERROR);return false;
    }
    r->microphone_active=false;r->stats.microphone_stops++;
    observe_clock(r,r->config.now_ms(r->config.context));r->transition_ms=r->elapsed_ms;
    r->transition_recorded=false;r->state=COMP_CONT_PAUSING;return true;
}

static void destroy_encoder(comp_cont_recording_t *r)
{
    if (r->encoder_owned) {companion_opus16_rt_destroy(&r->codec);r->encoder_owned=false;}
}

void comp_cont_recording_fault(comp_cont_recording_t *r,comp_segment_result_t why)
{
    if (!r || r->state==COMP_CONT_UNBOUND) return;
    r->state=COMP_CONT_FAULT;r->failure=why;r->stop_reason=COMP_CONT_STOP_ERROR;
    if (r->microphone_active && r->config.microphone(r->config.context,false)) {
        r->microphone_active=false;r->stats.microphone_stops++;
    }
    destroy_encoder(r);
}

bool comp_cont_recording_init(comp_cont_recording_t *r,const comp_cont_config_t *cfg,
    const comp_segment_entry_t *e,comp_segment_audio_t *writer,uint32_t token)
{
    if (!r || !cfg || !cfg->microphone || !cfg->now_ms || !cfg->next || !cfg->seal || !cfg->cancel ||
        !token || cfg->pause_timeline>COMP_CONT_TIMELINE_AUDIO_PROFILE ||
        (cfg->pause_timeline==COMP_CONT_TIMELINE_AUDIO_PROFILE&&!cfg->audio_profile) || !prepared(e,writer) || writer->claimed || e->descriptor.segment_index || e->descriptor.sample_offset ||
        !cfg->segment_frames || cfg->segment_frames>UINT32_MAX/COMP_SEG_AUDIO_FRAME_BYTES-DRAIN_PACKETS ||
        comp_recording_required_capacity_profile(cfg->segment_frames,cfg->pause_timeline>=COMP_CONT_TIMELINE_SOURCE_BOUNDARY,cfg->pause_timeline==COMP_CONT_TIMELINE_AUDIO_PROFILE)>
            comp_segment_audio_capacity(e->reserved_bytes)) return false;
    memset(r,0,sizeof(*r));r->config=*cfg;r->active=*e;r->writer=*writer;r->token=token;
    r->active_frame_limit=cfg->segment_frames;
    r->writer.entry=&r->active;r->writer.page=r->stage+COMP_CONT_STAGE_BYTES;
    if (!r->config.foreground_budget_ms) r->config.foreground_budget_ms=10u;
    if (!companion_opus16_rt_init_rate_frame(&r->codec,16000u,20u)) return false;
    r->encoder_owned=true;companion_sha256_init(&r->sha);
    if (!append_header(r)) {destroy_encoder(r);return false;}
    writer->claimed=true;r->writer.claimed=true;r->state=COMP_CONT_READY;return true;
}

bool comp_cont_recording_start(comp_cont_recording_t *r,uint32_t token)
{
    if (!r || token!=r->token || r->state!=COMP_CONT_READY || !r->encoder_owned) return false;
    if (!r->config.microphone(r->config.context,true)) {comp_cont_recording_fault(r,COMP_SEG_IO_ERROR);return false;}
    r->clock_ms=r->config.now_ms(r->config.context);r->elapsed_ms=0u;
    r->microphone_active=true;r->stats.microphone_starts++;r->state=COMP_CONT_RUNNING;return true;
}

static bool reserve_event_space(comp_cont_recording_t *r,uint32_t pages)
{
    /* Timeline pages consume the same extent as audio. Shorten this physical
     * segment's audio horizon, rather than rejecting ordinary repeated PAUSE
     * against an unchanged two-minute reservation. Keep the full drain and
     * pause/resume (or paused STOP) page allowance. Never rebase a packet
     * already handed to the successor, or cut behind accepted real PCM. */
    uint32_t capacity=comp_segment_audio_capacity(r->active.reserved_bytes);
    uint64_t overhead=12u+(uint64_t)r->active_non_audio_bytes+(uint64_t)pages*COMP_SEG_AUDIO_DATA_BYTES+
        DRAIN_PACKETS*COMP_SEG_AUDIO_FRAME_BYTES+(source_boundary(r)?2u*COMP_SEG_AUDIO_DATA_BYTES:0u);
    if(r->roll_packet_bytes||overhead>=capacity)return false;
    uint32_t limit=(uint32_t)((capacity-overhead)/COMP_SEG_AUDIO_FRAME_BYTES);
    if(limit>r->active_frame_limit)limit=r->active_frame_limit;
    uint32_t queued=((uint32_t)r->ring_count*COMP_CONT_PCM_BLOCK_SAMPLES+r->codec.pcm_fill+319u)/320u;
    if(!limit||r->codec.frames_encoded-r->active_first_frame+queued>limit)return false;
    r->active_frame_limit=limit;
    return true;
}
bool comp_cont_recording_pause(comp_cont_recording_t *r,uint32_t token,uint32_t sequence)
{
    if(!r||!r->config.pause_timeline||token!=r->token||!sequence||sequence==UINT32_MAX||r->state==COMP_CONT_FAULT)return false;
    if(sequence==r->command_sequence)return r->command_kind==COMP_REC_TIMELINE_PAUSE;
    if(sequence<=r->command_sequence||r->state!=COMP_CONT_RUNNING)return false;
    if(!reserve_event_space(r,3u+(r->bookmark_phase?2u:0u)))return false;
    r->command_sequence=sequence;r->command_kind=COMP_REC_TIMELINE_PAUSE;
    r->state=COMP_CONT_PAUSE_PENDING;return begin_pause(r);
}
bool comp_cont_recording_resume(comp_cont_recording_t *r,uint32_t token,uint32_t sequence)
{
    if(!r||!r->config.pause_timeline||token!=r->token||!sequence||r->state==COMP_CONT_FAULT)return false;
    if(sequence==r->command_sequence)return r->command_kind==COMP_REC_TIMELINE_RESUME;
    if(sequence<=r->command_sequence||r->state!=COMP_CONT_PAUSED)return false;
    if(!r->config.microphone(r->config.context,true)) {
        comp_cont_recording_fault(r,COMP_SEG_IO_ERROR);return false;
    }
    r->microphone_active=true;r->stats.microphone_starts++;
    observe_clock(r,r->config.now_ms(r->config.context));r->transition_ms=r->elapsed_ms;
    r->command_sequence=sequence;r->command_kind=COMP_REC_TIMELINE_RESUME;
    r->transition_recorded=false;r->state=COMP_CONT_RESUMING;return true;
}
bool comp_cont_recording_bookmark(comp_cont_recording_t *r,uint32_t token,uint32_t request)
{
    if(!r||!token||token!=r->token||!request||r->config.pause_timeline<COMP_CONT_TIMELINE_BOOKMARKS||
       (r->state!=COMP_CONT_RUNNING&&r->state!=COMP_CONT_PAUSED)||!r->encoder_owned)return false;
    if(request==r->bookmark_request)return r->bookmark_sequence!=0u;
    if(r->bookmark_phase||r->bookmark_sequence>=COMP_CONT_BOOKMARK_LIMIT||
       (r->bookmark_request&&(int32_t)(request-r->bookmark_request)<=0)||
       r->stats.accepted_pcm_blocks<2u||!reserve_event_space(r,5u))return false;
    observe_clock(r,r->config.now_ms(r->config.context));
    r->bookmark_sample=((uint64_t)r->stats.accepted_pcm_blocks/2u)*320u;
    r->bookmark_ms=r->elapsed_ms;r->bookmark_request=request;++r->bookmark_sequence;
    r->bookmark_phase=1u;return true;
}
comp_segment_result_t comp_cont_recording_bookmark_result(const comp_cont_recording_t *r,uint32_t token,uint32_t request)
{
    if(!r||!token||token!=r->token||!request||request!=r->bookmark_request||!r->bookmark_sequence)return COMP_SEG_BAD_STATE;
    if(r->state==COMP_CONT_FAULT)return r->failure;
    return r->bookmark_phase?COMP_SEG_PENDING:COMP_SEG_OK;
}
uint32_t comp_cont_recording_non_audio_bytes(const comp_cont_recording_t *r)
{return r?r->active_non_audio_bytes:0u;}

static bool request_stop(comp_cont_recording_t *r,comp_cont_stop_t reason)
{
    if (r->state==COMP_CONT_STOPPING || r->state==COMP_CONT_SEALED ||
        r->state==COMP_CONT_CANCELING || r->state==COMP_CONT_CANCELED) return true;
    if (r->state==COMP_CONT_READY) {r->state=COMP_CONT_STOPPING;r->stop_reason=reason;return true;}
    if(r->state==COMP_CONT_ENDING_PAUSE)return true;
    if(r->state==COMP_CONT_PAUSED) {
        if(r->command_sequence==UINT32_MAX)return false;
        observe_clock(r,r->config.now_ms(r->config.context));r->transition_ms=r->elapsed_ms;
        ++r->command_sequence;r->command_kind=COMP_REC_TIMELINE_END_PAUSED;
        r->transition_recorded=false;r->stop_reason=reason;r->state=COMP_CONT_ENDING_PAUSE;
        return true;
    }
    if (r->state!=COMP_CONT_RUNNING&&r->state!=COMP_CONT_PAUSE_PENDING) return false;
    if (r->microphone_active) {
        if (!r->config.microphone(r->config.context,false)) {comp_cont_recording_fault(r,COMP_SEG_IO_ERROR);return false;}
        r->microphone_active=false;r->stats.microphone_stops++;
    } else if(r->stop_reason!=reason || reason==COMP_CONT_STOP_NONE) return false;
    r->flush_complete=false;r->state=COMP_CONT_STOPPING;r->stop_reason=reason;
    if (reason==COMP_CONT_STOP_FULL) r->stats.storage_full_stops++;
    return true;
}

bool comp_cont_recording_quiesce_resume(comp_cont_recording_t *r,uint32_t token,comp_cont_stop_t reason)
{
    if(!r||!token||token!=r->token||r->state!=COMP_CONT_RESUMING||
       (reason!=COMP_CONT_STOP_USER && reason!=COMP_CONT_STOP_LOW_BATTERY &&
        reason!=COMP_CONT_STOP_LIMIT && reason!=COMP_CONT_STOP_SILENCE))return false;
    if(!r->microphone_active)return r->stop_reason==reason;
    if(!r->config.microphone(r->config.context,false)) {
        comp_cont_recording_fault(r,COMP_SEG_IO_ERROR);return false;
    }
    r->microphone_active=false;r->stats.microphone_stops++;r->stop_reason=reason;
    return true;
}

bool comp_cont_recording_stop(comp_cont_recording_t *r,uint32_t token)
{return r && token && token==r->token && request_stop(r,COMP_CONT_STOP_USER);}
bool comp_cont_recording_stop_reason(comp_cont_recording_t *r,uint32_t token,comp_cont_stop_t reason)
{
    return r && token && token==r->token &&
        (reason==COMP_CONT_STOP_USER || reason==COMP_CONT_STOP_LOW_BATTERY ||
         reason==COMP_CONT_STOP_LIMIT || reason==COMP_CONT_STOP_SILENCE) && request_stop(r,reason);
}

bool comp_cont_recording_pcm(comp_cont_recording_t *r,const int16_t *pcm,size_t samples)
{
    if (!r || !pcm || samples!=COMP_CONT_PCM_BLOCK_SAMPLES ||
        (r->state!=COMP_CONT_RUNNING&&r->state!=COMP_CONT_PAUSE_PENDING&&r->state!=COMP_CONT_RESUMING) ||
        !r->microphone_active) return false;
    if (r->ring_count==COMP_CONT_PCM_SLOTS) {
        r->stats.overflows++;comp_cont_recording_fault(r,COMP_SEG_FULL);return false;
    }
    memcpy(r->pcm[r->ring_write],pcm,COMP_CONT_PCM_BLOCK_SAMPLES*sizeof(int16_t));
    r->ring_write=(uint8_t)((r->ring_write+1u)%COMP_CONT_PCM_SLOTS);r->ring_count++;
    r->stats.accepted_pcm_blocks++;
    if (r->ring_count>r->stats.max_ring_depth) r->stats.max_ring_depth=r->ring_count;
    return r->state!=COMP_CONT_PAUSE_PENDING||begin_pause(r);
}

static comp_segment_result_t next_extent(comp_cont_recording_t *r,bool take,
    const comp_segment_entry_t **e,comp_segment_audio_t **writer)
{
    *e=NULL;*writer=NULL;
    comp_segment_result_t result=r->config.next(r->config.context,take,e,writer);
    if (result!=COMP_SEG_OK) return result;
    const comp_rec_v2_descriptor_t *current=&r->active.descriptor;
    if (!prepared(*e,*writer) || (*writer)->claimed || (*writer)->data_base!=r->writer.data_base ||
        (*e)->descriptor.format_epoch!=current->format_epoch ||
        (*e)->descriptor.session_id!=current->session_id ||
        (*e)->descriptor.segment_index!=current->segment_index+1u ||
        (*e)->descriptor.sample_offset!=current->sample_offset+(uint64_t)r->active_frame_limit*320u ||
        (*e)->descriptor.source_mode!=current->source_mode ||
        (*e)->descriptor.recording_id==current->recording_id ||
        comp_segment_audio_capacity((*e)->reserved_bytes)<
            comp_recording_required_capacity_profile(r->config.segment_frames,source_boundary(r),audio_profile(r)) ||
        memcmp((*e)->descriptor.device_uid,current->device_uid,12u)!=0 ||
        !((*e)->extent_offset+(*e)->reserved_bytes<=r->active.extent_offset ||
          r->active.extent_offset+r->active.reserved_bytes<=(*e)->extent_offset)) return COMP_SEG_BAD_STATE;
    return COMP_SEG_OK;
}

static bool writer_progress(comp_cont_recording_t *r)
{
    comp_segment_result_t result=comp_segment_audio_poll(&r->writer);
    if (result==COMP_SEG_PENDING) return true;
    if (result!=COMP_SEG_OK) {comp_cont_recording_fault(r,result);return false;}
    uint8_t length=r->writer.length;
    if (length>r->stage_length) {comp_cont_recording_fault(r,COMP_SEG_CORRUPT);return false;}
    companion_sha256_update(&r->sha,r->stage,length);
    r->content_crc=~comp_rec_crc_step(~r->content_crc,r->stage,length);
    r->stats.durable_bytes+=length;
    r->stage_length=(uint16_t)(r->stage_length-length);
    memmove(r->stage,r->stage+length,r->stage_length);return true;
}

static bool program_stage(comp_cont_recording_t *r,bool partial)
{
    if (!r->stage_length || (!partial && r->stage_length<COMP_SEG_AUDIO_DATA_BYTES)) return true;
    uint8_t length=(uint8_t)(r->stage_length>COMP_SEG_AUDIO_DATA_BYTES?COMP_SEG_AUDIO_DATA_BYTES:r->stage_length);
    comp_segment_result_t result=comp_segment_audio_append_begin(&r->writer,r->stage,length);
    if (result!=COMP_SEG_PENDING) {comp_cont_recording_fault(r,result);return false;}
    /* Beginning only copies stable bytes; exactly one backend operation. */
    return writer_progress(r);
}

static bool encoded_packet(comp_cont_recording_t *r,uint32_t before,size_t bytes)
{
    if (bytes && before-r->active_first_frame>=r->active_frame_limit) {
        const comp_segment_entry_t *e;comp_segment_audio_t *writer;
        comp_segment_result_t next=next_extent(r,false,&e,&writer);
        if (next==COMP_SEG_OK) {
            /* Hold the first successor packet while the last old page commits.
             * No PCM/encoder reset, flush, zero padding or microphone restart. */
            r->roll_packet_bytes=(uint16_t)bytes;return true;
        }
        /* A full pool with no durable successor can use the explicitly
         * reserved drain headroom in this final extent. */
        if (r->state!=COMP_CONT_STOPPING || next!=COMP_SEG_FULL) {
            comp_cont_recording_fault(r,next);return false;
        }
    }
    if (!append(r,packet(r),bytes)) {comp_cont_recording_fault(r,COMP_SEG_FULL);return false;}
    return true;
}

static bool encode_one(comp_cont_recording_t *r)
{
    uint32_t before=r->codec.frames_encoded;
    comp_duration_stamp_t at=comp_duration_begin(r->config.now_ms(r->config.context));
    const bool complete_input=r->codec.pcm_fill+COMP_CONT_PCM_BLOCK_SAMPLES>=r->codec.frame_samples;
    comp_cpu_stage_span_t cpu_span=complete_input?comp_cpu_stage_begin():(comp_cpu_stage_span_t){0};
    if(complete_input)comp_cpu_codec_cache_begin();
    size_t bytes=companion_opus16_rt_encode(&r->codec,r->pcm[r->ring_read],
        COMP_CONT_PCM_BLOCK_SAMPLES,packet(r),PACKET_CAPACITY,false);
    if(complete_input)comp_cpu_stage_end(COMP_CPU_STAGE_OPUS,cpu_span,r->codec.frames_encoded!=before);
    if (r->codec.frames_encoded!=before) {
        comp_duration_end(&r->stats.encoding_duration,at,r->config.now_ms(r->config.context));
        if (bytes!=COMP_SEG_AUDIO_FRAME_BYTES) {comp_cont_recording_fault(r,COMP_SEG_CORRUPT);return false;}
    } else if (bytes || r->codec.pcm_fill>=r->codec.frame_samples) {
        comp_cont_recording_fault(r,COMP_SEG_CORRUPT);return false;
    }
    r->ring_read=(uint8_t)((r->ring_read+1u)%COMP_CONT_PCM_SLOTS);r->ring_count--;
    r->stats.encoded_packets+=r->codec.frames_encoded-before;
    return encoded_packet(r,before,bytes);
}

bool comp_cont_recording_stage_pcm_half(comp_cont_recording_t *r)
{
    if(!comp_cont_recording_pcm_staging_pending(r))return false;
    uint32_t at=r->config.now_ms(r->config.context);observe_clock(r,at);
    /* This is exactly the first-half path in opus16_rt_encode, without
     * entering work(), which can prioritize full-pool stop or sealing. */
    memcpy(r->codec.pcm_acc,r->pcm[r->ring_read],COMP_CONT_PCM_BLOCK_SAMPLES*sizeof(int16_t));
    r->codec.pcm_fill=COMP_CONT_PCM_BLOCK_SAMPLES;
    r->ring_read=(uint8_t)((r->ring_read+1u)%COMP_CONT_PCM_SLOTS);--r->ring_count;
    uint32_t elapsed=r->config.now_ms(r->config.context)-at;
    if(elapsed>r->stats.max_poll_ms)r->stats.max_poll_ms=elapsed;
    if(r->microphone_active&&elapsed>r->config.foreground_budget_ms) {
        ++r->stats.budget_failures;comp_cont_recording_fault(r,COMP_SEG_BAD_STATE);return false;
    }
    return true;
}

static bool make_closing(comp_cont_recording_t *r,bool last,uint32_t frames)
{
    if (!frames || r->closing_pending || r->stage_length || r->writer.phase ||
        r->writer.committed_bytes!=12u+frames*COMP_SEG_AUDIO_FRAME_BYTES+r->active_non_audio_bytes) {
        comp_cont_recording_fault(r,COMP_SEG_BAD_STATE);return false;
    }
    r->closing=r->active;r->closing.state=COMP_SEG_UNSYNCED;
    comp_rec_v2_descriptor_t *d=&r->closing.descriptor;
    d->sample_count=(uint64_t)frames*320u;d->encoded_length=r->writer.committed_bytes;
    d->content_crc32=r->content_crc;d->sync_state=1u;
    d->flags=(uint8_t)(COMP_REC_V2_SEALED|(last?COMP_REC_V2_LAST:0u));
    if(last)d->flags|=(uint8_t)(comp_cont_recording_end_reason(r->stop_reason)<<COMP_REC_V2_END_SHIFT);
    /* A late successor is not a full device. Preserve the sealed prefix and
     * use the existing interrupted-capture flag, which old readers understand.
     * The more specific cause remains local; do not write a new reason code
     * that old clients and downgraded firmware reject. */
    if(last && r->stop_reason==COMP_CONT_STOP_PREPARE_DELAYED)
        d->flags|=COMP_REC_V2_RECOVERED;
    d->total_segments=last?d->segment_index+1u:0u;
    companion_sha256_t hash=r->sha;companion_sha256_final(&hash,d->sha256);
    if (!comp_rec_v2_valid(d)) {comp_cont_recording_fault(r,COMP_SEG_CORRUPT);return false;}
    r->closing_pending=true;r->closing_last=last;return true;
}

static bool advance_roll(comp_cont_recording_t *r)
{
    const comp_segment_entry_t *e;comp_segment_audio_t *writer;
    comp_segment_result_t result=next_extent(r,true,&e,&writer);
    if (result!=COMP_SEG_OK) {comp_cont_recording_fault(r,result);return false;}
    if (!make_closing(r,false,r->active_frame_limit)) return false;
    writer->claimed=true;
    r->active=*e;r->writer=*writer;r->writer.entry=&r->active;
    r->writer.page=r->stage+COMP_CONT_STAGE_BYTES;
    r->active_first_frame=r->codec.frames_encoded-1u;
    r->active_frame_limit=r->config.segment_frames;
    r->content_crc=0u;r->active_non_audio_bytes=0u;companion_sha256_init(&r->sha);
    if (!append_header(r) || !append(r,packet(r),r->roll_packet_bytes)) {
        comp_cont_recording_fault(r,COMP_SEG_FULL);return false;
    }
    r->roll_packet_bytes=0u;return true;
}

static bool seal_progress(comp_cont_recording_t *r)
{
    /* The durable successor prevents an empty-tail/STOP-boundary session from
     * disappearing after the receiver consumes every already-listed segment.
     * A stop at the exact boundary seals the old nonempty segment as LAST. */
    if (!r->closing_last && r->writer.committed_bytes<12u+(source_boundary(r)?32u:0u)+(audio_profile(r)?COMP_REC_AUDIO_PROFILE_BYTES:0u)+COMP_SEG_AUDIO_FRAME_BYTES) return true;
    comp_segment_result_t result=r->config.seal(r->config.context,&r->closing,!r->closing_started);
    if (result==COMP_SEG_PENDING) {r->closing_started=true;return true;}
    if (result!=COMP_SEG_OK) {comp_cont_recording_fault(r,result);return false;}
    r->closing_pending=false;r->closing_started=false;r->stats.sealed_segments++;
    if (r->closing_last) {
        destroy_encoder(r);r->active=r->closing;r->writer.entry=&r->active;r->state=COMP_CONT_SEALED;
    }
    return true;
}

static bool pad_timeline_page(comp_cont_recording_t *r)
{
    if(!r->stage_length||r->stage_length>=COMP_SEG_AUDIO_DATA_BYTES)return true;
    uint16_t padding=(uint16_t)(COMP_SEG_AUDIO_DATA_BYTES-r->stage_length);
    if(r->writer.committed_bytes+r->stage_length+padding>comp_segment_audio_capacity(r->active.reserved_bytes)) {
        comp_cont_recording_fault(r,COMP_SEG_FULL);return false;
    }
    memset(r->stage+r->stage_length,255u,padding);r->stage_length+=padding;
    r->active_non_audio_bytes+=padding;return true;
}
static void transition_progress(comp_cont_recording_t *r)
{
    /* No Opus flush/reset: resume must not introduce a padded audio frame.
     * Align the event to a fresh media page. Full commits preserve the same
     * fixed248B logical page mapping used by protected prefix/radio reads. */
    if(r->stage_length) {
        if(pad_timeline_page(r))(void)program_stage(r,false);
        return;
    }
    if(!r->transition_recorded) {
        uint8_t wire[COMP_REC_TIMELINE_BYTES];
        comp_rec_timeline_event_t event={(uint64_t)r->codec.frames_encoded*320u,
            r->transition_ms,r->command_sequence,r->command_kind};
        if(!comp_rec_timeline_encode(&event,wire)||!append(r,wire,sizeof(wire))) {
            comp_cont_recording_fault(r,COMP_SEG_FULL);return;
        }
        r->active_non_audio_bytes+=sizeof(wire);r->transition_recorded=true;
        if(pad_timeline_page(r))(void)program_stage(r,false);
        return;
    }
    if(r->state==COMP_CONT_PAUSING)r->state=COMP_CONT_PAUSED;
    else if(r->state==COMP_CONT_RESUMING)r->state=COMP_CONT_RUNNING;
    else {r->state=COMP_CONT_STOPPING;r->flush_complete=false;return;}
    r->transition_recorded=false;
}
static void bookmark_progress(comp_cont_recording_t *r)
{
    if(r->bookmark_sample!=(uint64_t)r->codec.frames_encoded*320u) {
        comp_cont_recording_fault(r,COMP_SEG_CORRUPT);return;
    }
    if(r->stage_length) {
        if(pad_timeline_page(r))(void)program_stage(r,false);
        return;
    }
    if(r->bookmark_phase==1u) {
        uint8_t wire[COMP_REC_TIMELINE_BYTES];
        comp_rec_timeline_event_t event={r->bookmark_sample,r->bookmark_ms,r->bookmark_sequence,COMP_REC_TIMELINE_BOOKMARK};
        if(!comp_rec_timeline_encode(&event,wire)||!append(r,wire,sizeof(wire))) {
            comp_cont_recording_fault(r,COMP_SEG_FULL);return;
        }
        r->active_non_audio_bytes+=sizeof(wire);r->bookmark_phase=2u;
        if(pad_timeline_page(r))(void)program_stage(r,false);
        return;
    }
    /* The page/body/readback/commit/readback owner is now idle. A queued
     * request did not become durable merely by being copied to the stage. */
    r->bookmark_phase=0u;
}

static void source_end_progress(comp_cont_recording_t *r)
{
    /* Commit the exact source end before its one final codec packet. A live
     * reader can cap that packet without publishing padding then retracting
     * it. This declaration is not a normal STOP or a sealed descriptor. */
    if(r->stage_length) {
        if(pad_timeline_page(r))(void)program_stage(r,false);
        return;
    }
    if(r->closing_pending) {(void)seal_progress(r);return;}
    if(r->codec.frames_encoded-r->active_first_frame>=r->active_frame_limit) {
        const comp_segment_entry_t *e;comp_segment_audio_t *writer;
        comp_segment_result_t result=next_extent(r,false,&e,&writer);
        if(result==COMP_SEG_PENDING) {
            /* An already-owned successor cannot be overwritten by the tail.
             * Finish its bounded preparation while MIC is stopped; FULL may
             * instead use the active extent's reserved drain headroom. */
            if(!r->config.background){comp_cont_recording_fault(r,COMP_SEG_BAD_STATE);return;}
            result=r->config.background(r->config.context);
            if(result!=COMP_SEG_OK&&result!=COMP_SEG_PENDING&&result!=COMP_SEG_FULL)
                comp_cont_recording_fault(r,result);
            return;
        }
        if(result!=COMP_SEG_OK&&result!=COMP_SEG_FULL){comp_cont_recording_fault(r,result);return;}
    }
    uint8_t wire[COMP_REC_CODEC_BOUNDARY_BYTES];
    comp_rec_codec_boundary_t end={((uint64_t)r->codec.frames_encoded+1u)*320u,
        (uint64_t)r->stats.accepted_pcm_blocks*COMP_CONT_PCM_BLOCK_SAMPLES,
        r->codec.encoder_delay_samples,COMP_REC_CODEC_END};
    if(!comp_rec_codec_boundary_encode(&end,wire)||!append(r,wire,sizeof(wire))) {
        comp_cont_recording_fault(r,COMP_SEG_CORRUPT);return;
    }
    r->active_non_audio_bytes+=sizeof(wire);r->source_end_phase=1u;
    if(pad_timeline_page(r))(void)program_stage(r,false);
}

static void work(comp_cont_recording_t *r)
{
    if (r->writer.phase) {(void)writer_progress(r);return;}
    if (r->roll_packet_bytes) {
        if (r->stage_length) {(void)program_stage(r,true);return;}
        (void)advance_roll(r);return;
    }
    if(r->bookmark_phase && (uint64_t)r->codec.frames_encoded*320u>=r->bookmark_sample) {
        bookmark_progress(r);return;
    }
    if(r->state==COMP_CONT_PAUSING) {
        if(r->ring_count) {
            if(r->stage_length>PACKET_OFFSET)(void)program_stage(r,false);
            else (void)encode_one(r);
            return;
        }
        if(r->codec.pcm_fill){comp_cont_recording_fault(r,COMP_SEG_CORRUPT);return;}
        transition_progress(r);return;
    }
    if(r->state==COMP_CONT_RESUMING||r->state==COMP_CONT_ENDING_PAUSE) {
        transition_progress(r);return;
    }
    if (r->state==COMP_CONT_RUNNING||r->state==COMP_CONT_PAUSE_PENDING) {
        uint32_t frames=r->codec.frames_encoded-r->active_first_frame;
        const comp_segment_entry_t *e;comp_segment_audio_t *writer;
        comp_segment_result_t next=next_extent(r,false,&e,&writer);
        if (next!=COMP_SEG_OK && next!=COMP_SEG_PENDING && next!=COMP_SEG_FULL) {
            comp_cont_recording_fault(r,next);return;
        }
        if (frames>=r->active_frame_limit && next==COMP_SEG_FULL) {
            (void)request_stop(r,COMP_CONT_STOP_FULL);return;
        }
        /* A still-owned but unprepared reservation already has the next
         * sample offset. Stop soon enough to drain accepted PCM without
         * overlapping it. Failure keeps that reservation for recovery. */
        uint32_t queued_packets=((uint32_t)r->ring_count*COMP_CONT_PCM_BLOCK_SAMPLES+
                                 r->codec.pcm_fill+319u)/320u;
        if (next==COMP_SEG_PENDING && frames+queued_packets>=r->active_frame_limit) {
            (void)request_stop(r,COMP_CONT_STOP_PREPARE_DELAYED);return;
        }
        if (r->stage_length>PACKET_OFFSET) {(void)program_stage(r,false);return;}
        if (r->ring_count && !(frames>=r->active_frame_limit && r->closing_pending)) {(void)encode_one(r);return;}
        if (r->stage_length>=COMP_SEG_AUDIO_DATA_BYTES) {(void)program_stage(r,false);return;}
    } else if (r->state==COMP_CONT_STOPPING) {
        if (!r->stats.accepted_pcm_blocks && !r->ring_count && !r->codec.frames_encoded &&
            !r->writer.pages && !r->writer.committed_bytes) {
            /* No data page was ever offered. A user can cancel before the
             * first10ms block without an empty recording or leaked extent. */
            r->writer.claimed=false;r->stage_length=0u;destroy_encoder(r);
            comp_segment_result_t result=r->config.cancel(r->config.context,&r->writer,true);
            if (result==COMP_SEG_PENDING) r->state=COMP_CONT_CANCELING;
            else if (result==COMP_SEG_OK) r->state=COMP_CONT_CANCELED;
            else comp_cont_recording_fault(r,result);
            return;
        }
        if (r->ring_count) {
            if (r->stage_length>PACKET_OFFSET) (void)program_stage(r,false);
            else (void)encode_one(r);
            return;
        }
        if (!r->flush_complete) {
            if(source_boundary(r)&&!r->source_end_phase){source_end_progress(r);return;}
            if(r->stage_length>PACKET_OFFSET){(void)program_stage(r,false);return;}
            uint32_t before=r->codec.frames_encoded;
            comp_duration_stamp_t at=comp_duration_begin(r->config.now_ms(r->config.context));
            bool will_encode=source_boundary(r)||r->codec.pcm_fill!=0u;
            comp_cpu_stage_span_t span=will_encode?comp_cpu_stage_begin():(comp_cpu_stage_span_t){0};
            if(will_encode)comp_cpu_codec_cache_begin();
            size_t n=source_boundary(r)?companion_opus16_rt_finish_exact(&r->codec,packet(r),PACKET_CAPACITY):
                companion_opus16_rt_flush(&r->codec,packet(r),PACKET_CAPACITY);
            if(will_encode)comp_cpu_stage_end(COMP_CPU_STAGE_OPUS,span,r->codec.frames_encoded!=before);
            if(r->codec.frames_encoded!=before)
                comp_duration_end(&r->stats.encoding_duration,at,r->config.now_ms(r->config.context));
            if(source_boundary(r)&&(n!=COMP_SEG_AUDIO_FRAME_BYTES||r->codec.frames_encoded!=before+1u)) {
                comp_cont_recording_fault(r,COMP_SEG_CORRUPT);return;
            }
            if (r->codec.frames_encoded!=before && n!=COMP_SEG_AUDIO_FRAME_BYTES) {
                comp_cont_recording_fault(r,COMP_SEG_CORRUPT);return;
            }
            r->stats.encoded_packets+=r->codec.frames_encoded-before;r->flush_complete=true;
            (void)encoded_packet(r,before,n);
            return;
        }
        if (r->stage_length) {(void)program_stage(r,true);return;}
        if (!r->closing_pending) {
            (void)make_closing(r,true,r->codec.frames_encoded-r->active_first_frame);return;
        }
    }
    if (r->closing_pending) {(void)seal_progress(r);return;}
    if (r->config.background) {
        comp_segment_result_t result=r->config.background(r->config.context);
        if (result!=COMP_SEG_OK && result!=COMP_SEG_PENDING && result!=COMP_SEG_FULL)
            comp_cont_recording_fault(r,result);
    }
}

comp_cont_state_t comp_cont_recording_poll(comp_cont_recording_t *r)
{
    if (!r) return COMP_CONT_UNBOUND;
    if (r->state==COMP_CONT_UNBOUND || r->state==COMP_CONT_READY ||
        r->state==COMP_CONT_SEALED || r->state==COMP_CONT_CANCELED) return r->state;
    if (r->state==COMP_CONT_CANCELING) {
        comp_segment_result_t result=r->config.cancel(r->config.context,&r->writer,false);
        if (result==COMP_SEG_OK) r->state=COMP_CONT_CANCELED;
        else if (result!=COMP_SEG_PENDING) comp_cont_recording_fault(r,result);
        return r->state;
    }
    if (r->state==COMP_CONT_FAULT) {
        if (r->microphone_active && r->config.microphone(r->config.context,false)) {
            r->microphone_active=false;r->stats.microphone_stops++;
        }
        return r->state;
    }
    bool was_capture=r->microphone_active;
    uint32_t at=r->config.now_ms(r->config.context);
    observe_clock(r,at);work(r);
    uint32_t elapsed=r->config.now_ms(r->config.context)-at;
    if (elapsed>r->stats.max_poll_ms) r->stats.max_poll_ms=elapsed;
    if (was_capture && elapsed>r->config.foreground_budget_ms) {
        r->stats.budget_failures++;comp_cont_recording_fault(r,COMP_SEG_BAD_STATE);
    }
    return r->state;
}
