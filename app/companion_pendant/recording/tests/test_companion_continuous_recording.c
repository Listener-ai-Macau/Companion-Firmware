#include "companion_continuous_recording.h"
#include "companion_recording_geometry.h"
#include "companion_segment_reserve.h"
#include "wba_recording_service.h"
#include <stdio.h>
#ifndef COMP_REC_TEST_AUDIO_PROFILE
#define COMP_REC_TEST_AUDIO_PROFILE NULL
#endif

enum { BANK=24576, BASE=2*BANK, DATA=4*4096, BYTES=BASE+DATA,
       BLOCKS=80, SEG_FRAMES=10, MAX_RECORDS=8, MAX_RAW=4096 };
typedef struct {
    uint8_t bytes[BYTES],scratch[256],raw[MAX_RECORDS][MAX_RAW];
    comp_segment_catalog_t catalog;
    comp_segment_reserve_t reserve;
    comp_segment_entry_t next_entry,sealed[MAX_RECORDS],consume_entry;
    comp_segment_audio_t next_writer;
    comp_cont_recording_t recorder;
    uint32_t now,read_page,read_bytes,erased_offset;
    unsigned calls,next_phase,count,consumer,starts,stops,reclaims;
    bool microphone,erase_pending,no_next,hold_next;
} fixture_t;
static fixture_t fixture;
static uint8_t joined[MAX_RAW],baseline[MAX_RAW];
static const uint8_t uid[12]={1u,2u,3u,4u,5u,6u,7u,8u,9u,10u,11u,12u};
#define CHECK(x) do {if (!(x)) {fprintf(stderr,"FAIL %u: %s\n",(unsigned)__LINE__,#x);return false;}} while (0)
static bool read_media(void *v,uint32_t at,uint8_t *p,uint32_t n)
{
    fixture_t *f=v;f->calls++;
    if (at>BYTES || n>BYTES-at) return false;
    memcpy(p,f->bytes+at,n);return true;
}
static bool program_media(void *v,uint32_t at,const uint8_t *p,uint32_t n)
{
    fixture_t *f=v;f->calls++;
    if (!n || at>BYTES || n>BYTES-at || at/256u!=(at+n-1u)/256u) return false;
    for (uint32_t i=0u;i<n;i++) {
        if ((f->bytes[at+i]&p[i])!=p[i]) return false;
        f->bytes[at+i]&=p[i];
    }
    return true;
}
static bool erase_media(void *v,uint32_t at,uint32_t remaining,uint32_t *done)
{
    fixture_t *f=v;*done=0u;f->calls++;
    if (at%4096u || remaining<4096u || at>BYTES-4096u) return false;
    if (!f->erase_pending) {f->erase_pending=true;f->erased_offset=at;return true;}
    if (at!=f->erased_offset) return false;
    f->erase_pending=false;memset(f->bytes+at,255,4096u);*done=4096u;return true;
}
static comp_segment_result_t audio_read(void *v,uint32_t at,uint8_t *p,uint32_t n)
{return read_media(v,at,p,n)?COMP_SEG_OK:COMP_SEG_IO_ERROR;}
static comp_segment_result_t audio_program(void *v,uint32_t at,const uint8_t *p,uint32_t n)
{return program_media(v,at,p,n)?COMP_SEG_OK:COMP_SEG_IO_ERROR;}
static comp_segment_audio_port_t audio_port(fixture_t *f)
{comp_segment_audio_port_t p={audio_read,audio_program,f};return p;}
static bool microphone(void *v,bool enabled)
{
    fixture_t *f=v;if (enabled==f->microphone) return false;
    f->microphone=enabled;if (enabled) f->starts++;else f->stops++;return true;
}
static uint32_t now_ms(void *v) {return ((fixture_t *)v)->now;}

static comp_segment_result_t finish_catalog(fixture_t *f)
{
    comp_segment_result_t result=COMP_SEG_PENDING;
    for (unsigned i=0u;i<5000u && result==COMP_SEG_PENDING;i++) result=comp_segment_catalog_poll(&f->catalog);
    return result;
}
static void template_entry(fixture_t *f,const comp_segment_entry_t *active)
{
    memset(&f->next_entry,0,sizeof(f->next_entry));f->next_entry.state=COMP_SEG_WRITING;
    f->next_entry.descriptor.format_epoch=7u;f->next_entry.descriptor.session_id=55u;
    f->next_entry.descriptor.codec=3u;f->next_entry.descriptor.source_mode=1u;
    memcpy(f->next_entry.descriptor.device_uid,uid,12u);
    if (active) {
        f->next_entry.descriptor.segment_index=active->descriptor.segment_index+1u;
        f->next_entry.descriptor.sample_offset=active->descriptor.sample_offset+(uint64_t)SEG_FRAMES*320u;
    }
    memset(&f->next_writer,0,sizeof(f->next_writer));memset(&f->reserve,0,sizeof(f->reserve));
    uint32_t hint=active?(active->extent_offset+active->reserved_bytes)%DATA:0u;
    (void)comp_segment_reserve_begin(&f->reserve,&f->catalog,&f->next_entry,4096u,hint);
    f->next_phase=1u;
}
static comp_segment_result_t prepare_step(fixture_t *f)
{
    if (f->next_phase==1u) {
        comp_segment_result_t result=comp_segment_reserve_poll(&f->reserve);
        if (result!=COMP_SEG_OK) return result;
        comp_segment_entry_t *entry=NULL;
        if (!comp_segment_reserve_take(&f->reserve,&entry) || entry!=&f->next_entry) return COMP_SEG_BAD_STATE;
        comp_segment_audio_port_t port=audio_port(f);
        result=comp_segment_audio_prepare_begin(&f->next_writer,&port,&f->next_entry,BASE,f->catalog.page);
        if (result!=COMP_SEG_PENDING) return result;
        f->next_phase=2u;return result;
    }
    if (f->next_phase==2u) {
        comp_segment_result_t result=comp_segment_audio_poll(&f->next_writer);
        if (result==COMP_SEG_OK) f->next_phase=3u;
        return result;
    }
    return COMP_SEG_OK;
}
static comp_segment_result_t next(void *v,bool take,const comp_segment_entry_t **e,comp_segment_audio_t **w)
{
    fixture_t *f=v;
    if (f->no_next) return COMP_SEG_FULL;
    if (f->next_phase!=3u) return COMP_SEG_PENDING;
    *e=&f->next_entry;*w=&f->next_writer;
    if (take) f->next_phase=4u;
    return COMP_SEG_OK;
}
static comp_segment_result_t seal(void *v,const comp_segment_entry_t *e,bool begin)
{
    fixture_t *f=v;
    if ((e->descriptor.flags&COMP_REC_V2_LAST)==0u &&
        f->recorder.writer.committed_bytes<54u) return COMP_SEG_BAD_STATE;
    comp_segment_result_t result=begin?comp_segment_catalog_put_begin(&f->catalog,e):comp_segment_catalog_poll(&f->catalog);
    if (result==COMP_SEG_OK) {
        if (f->count==MAX_RECORDS) return COMP_SEG_FULL;
        f->sealed[f->count++]=*e;
    }
    return result;
}
static comp_segment_result_t cancel(void *v,comp_segment_audio_t *writer,bool begin)
{
    fixture_t *f=v;
    return begin?comp_segment_audio_cancel_begin(writer,&f->catalog):comp_segment_audio_poll(writer);
}

static comp_segment_result_t consume_step(fixture_t *f)
{
    comp_segment_entry_t *e=&f->sealed[f->reclaims];
    if (f->consumer==1u) {
        comp_segment_audio_port_t port=audio_port(f);uint8_t length=0u;
        comp_segment_result_t result=comp_segment_audio_read_page(&port,e,BASE,f->read_page,f->scratch,&length);
        if (result!=COMP_SEG_OK || f->read_bytes+length>e->descriptor.encoded_length) return COMP_SEG_CORRUPT;
        memcpy(f->raw[f->reclaims]+f->read_bytes,f->scratch,length);
        f->read_bytes+=length;f->read_page++;
        if (f->read_bytes==e->descriptor.encoded_length) f->consumer=2u;
        return COMP_SEG_PENDING;
    }
    if (f->consumer==2u) {
        companion_sha256_t hash;uint8_t digest[32];companion_sha256_init(&hash);
        companion_sha256_update(&hash,f->raw[f->reclaims],f->read_bytes);companion_sha256_final(&hash,digest);
        if (memcmp(digest,e->descriptor.sha256,32u)!=0 ||
            comp_rec_crc(f->raw[f->reclaims],f->read_bytes)!=e->descriptor.content_crc32) return COMP_SEG_CORRUPT;
        f->consume_entry=*e;f->consume_entry.state=COMP_SEG_ACKED;f->consume_entry.descriptor.sync_state=2u;
        comp_segment_result_t result=comp_segment_catalog_ack_begin(&f->catalog,&f->consume_entry);
        if (result!=COMP_SEG_PENDING) return result;
        f->consumer=3u;return result;
    }
    if (f->consumer==3u) {
        comp_segment_result_t result=comp_segment_catalog_poll(&f->catalog);
        if (result==COMP_SEG_OK) f->consumer=4u;
        return result;
    }
    if (f->consumer==4u) {
        comp_segment_result_t result=comp_segment_catalog_reclaim_begin(&f->catalog,&f->consume_entry);
        if (result!=COMP_SEG_PENDING) return result;
        f->consumer=5u;return result;
    }
    comp_segment_result_t result=comp_segment_catalog_poll(&f->catalog);
    if (result==COMP_SEG_OK) {f->consumer=0u;f->reclaims++;f->read_page=f->read_bytes=0u;}
    return result;
}
static comp_segment_result_t background(void *v)
{
    fixture_t *f=v;
    if (f->consumer) return consume_step(f);
    if (f->reclaims<f->count) {f->consumer=1u;f->read_page=f->read_bytes=0u;return COMP_SEG_PENDING;}
    if (f->no_next) return COMP_SEG_OK;
    if (f->hold_next) return COMP_SEG_PENDING;
    if (f->next_phase==4u) template_entry(f,&f->recorder.active);
    return prepare_step(f);
}
static bool initialize_mode(fixture_t *f,bool no_next,uint8_t timeline)
{
    memset(f,0,sizeof(*f));memset(f->bytes,255,BYTES);
    comp_segment_port_t port={read_media,program_media,erase_media,f,0u};
    CHECK(comp_segment_catalog_mount_begin(&f->catalog,&port,0u,BANK,BASE,DATA,uid,7u)==COMP_SEG_PENDING);
    CHECK(finish_catalog(f)==COMP_SEG_UNFORMATTED);
    CHECK(comp_segment_catalog_format_blank_begin(&f->catalog)==COMP_SEG_PENDING && finish_catalog(f)==COMP_SEG_OK);
    template_entry(f,NULL);
    for (unsigned i=0u;i<1000u && f->next_phase!=3u;i++) CHECK(prepare_step(f)==COMP_SEG_PENDING || f->next_phase==3u);
    CHECK(f->next_phase==3u);
    comp_cont_config_t cfg={microphone,now_ms,next,seal,cancel,background,f,SEG_FRAMES,10u,timeline,timeline==COMP_CONT_TIMELINE_AUDIO_PROFILE?COMP_REC_TEST_AUDIO_PROFILE:NULL};
    CHECK(comp_cont_recording_init(&f->recorder,&cfg,&f->next_entry,&f->next_writer,91u));
    CHECK(comp_segment_audio_cancel_begin(&f->next_writer,&f->catalog)==COMP_SEG_BAD_STATE);
    f->next_phase=4u;f->no_next=no_next;
    CHECK(comp_cont_recording_start(&f->recorder,91u));return true;
}
static bool initialize(fixture_t *f,bool no_next)
{return initialize_mode(f,no_next,false);}
static bool poll_many(fixture_t *f,unsigned n)
{
    for (unsigned i=0u;i<n;i++) {
        unsigned before=f->calls;comp_cont_state_t state=comp_cont_recording_poll(&f->recorder);
        if(f->calls-before>1u||state==COMP_CONT_FAULT)
            fprintf(stderr,"core failure state=%u reason=%u io=%u frames=%u fill=%u ring=%u stage=%u pages=%u writer_phase=%u transition=%u\n",
                (unsigned)state,(unsigned)f->recorder.failure,f->calls-before,
                f->recorder.codec.frames_encoded,f->recorder.codec.pcm_fill,f->recorder.ring_count,
                f->recorder.stage_length,f->recorder.writer.pages,f->recorder.writer.phase,f->recorder.transition_recorded);
        CHECK(f->calls-before<=1u && state!=COMP_CONT_FAULT);
    }
    return true;
}
static void pcm_block(unsigned block,int16_t pcm[160])
{
    for (unsigned i=0u;i<160u;i++) {
        unsigned t=block*160u+i;pcm[i]=(int16_t)((int)(t%73u)*400-14000);
    }
}
static bool capture(void)
{
    fixture_t *f=&fixture;CHECK(initialize(f,false));int16_t pcm[160];
    for (unsigned i=0u;i<BLOCKS;i++) {
        pcm_block(i,pcm);f->now+=10u;
        if (!comp_cont_recording_pcm(&f->recorder,pcm,160u)) {
            fprintf(stderr,"at block%u state%d stop%d failure%d active%u frames%lu nextphase%u closing%d catalogphase%u\n",
                i,(int)f->recorder.state,(int)f->recorder.stop_reason,(int)f->recorder.failure,
                f->recorder.active.descriptor.segment_index,(unsigned long)f->recorder.codec.frames_encoded,
                f->next_phase,f->recorder.closing_pending,f->catalog.phase);return false;
        }
        CHECK(poll_many(f,80u));
    }
    CHECK(comp_cont_recording_stop(&f->recorder,91u));
    for (unsigned i=0u;i<5000u && f->recorder.state!=COMP_CONT_SEALED;i++) CHECK(poll_many(f,1u));
    CHECK(f->recorder.state==COMP_CONT_SEALED && f->count==4u && f->starts==1u && f->stops==1u);
    CHECK(f->recorder.stats.accepted_pcm_blocks==BLOCKS && f->recorder.stats.encoded_packets==BLOCKS/2u);
    /* The final segment no longer captures; finish its already-produced
     * receiver/physical-consume job explicitly, not through an empty loop. */
    for (unsigned i=0u;i<5000u && f->reclaims<f->count;i++) {
        comp_segment_result_t result=background(f);CHECK(result==COMP_SEG_OK || result==COMP_SEG_PENDING);
    }
    CHECK(f->reclaims==4u);
    /* The unused next segment was never handed to PCM. Prove the complete
     * audio extent blank and retire only that reservation. */
    uint32_t unused_id=f->next_entry.descriptor.recording_id;
    CHECK(f->next_phase==3u && comp_segment_audio_cancel_begin(&f->next_writer,&f->catalog)==COMP_SEG_PENDING);
    comp_segment_result_t cancel=COMP_SEG_PENDING;
    for (unsigned i=0u;i<500u && cancel==COMP_SEG_PENDING;i++) {
        unsigned before=f->calls;cancel=comp_segment_audio_poll(&f->next_writer);
        CHECK(f->calls-before<=1u);
    }
    CHECK(cancel==COMP_SEG_OK && f->next_writer.canceled);
    comp_segment_entry_t found;
    for (uint8_t i=0u;i<COMP_SEGMENT_CAPACITY;i++) {
        comp_segment_result_t result=comp_segment_catalog_read(&f->catalog,i,&found);
        CHECK(result==COMP_SEG_NOT_FOUND || (result==COMP_SEG_OK && found.descriptor.recording_id!=unused_id));
    }
    comp_segment_port_t mount_port={read_media,program_media,erase_media,f,0u};
    CHECK(comp_segment_catalog_mount_begin(&f->catalog,&mount_port,0u,BANK,BASE,DATA,uid,7u)==COMP_SEG_PENDING);
    CHECK(finish_catalog(f)==COMP_SEG_OK && f->catalog.visible_mask==0u);
    uint32_t length=0u;
    for (unsigned i=0u;i<f->count;i++) {
        const comp_rec_v2_descriptor_t *d=&f->sealed[i].descriptor;
        CHECK(d->segment_index==i && d->sample_offset==(uint64_t)i*SEG_FRAMES*320u &&
            d->sample_count==SEG_FRAMES*320u && d->session_id==55u && d->format_epoch==7u &&
            (d->flags&COMP_REC_V2_LAST)==(i==3u?COMP_REC_V2_LAST:0u));
        uint32_t skip=i?12u:0u;
        memcpy(joined+length,f->raw[i]+skip,d->encoded_length-skip);length+=d->encoded_length-skip;
    }
    /* Independent full-stream encode of identical PCM. Byte equality proves
     * no encoder reset, duplicated flush/header packet, zero insertion or
     * sample loss at the physical segmentation boundaries. */
    companion_opus16_rt_t codec;CHECK(companion_opus16_rt_init_rate_frame(&codec,16000u,20u));
    uint8_t packet[402];uint32_t baseline_bytes=0u;
    for (unsigned i=0u;i<BLOCKS;i++) {
        pcm_block(i,pcm);size_t n=companion_opus16_rt_encode(&codec,pcm,160u,packet,sizeof(packet),i==0u);
        memcpy(baseline+baseline_bytes,packet,n);baseline_bytes+=(uint32_t)n;
    }
    CHECK(length==baseline_bytes && memcmp(joined,baseline,length)==0 && codec.frames_encoded==40u);
    companion_opus16_rt_destroy(&codec);
    printf("continuous:4segments/40realOpusPackets, one microphone/encoder lifetime, exact baseline bytes,4validated physical reclaims\n");
    return true;
}
static bool full(void)
{
    fixture_t *f=&fixture;CHECK(initialize(f,true));int16_t pcm[160];
    for (unsigned i=0u;i<40u && f->recorder.state==COMP_CONT_RUNNING;i++) {
        pcm_block(i,pcm);f->now+=10u;CHECK(comp_cont_recording_pcm(&f->recorder,pcm,160u));CHECK(poll_many(f,80u));
    }
    for (unsigned i=0u;i<5000u && f->recorder.state!=COMP_CONT_SEALED;i++) CHECK(poll_many(f,1u));
    CHECK(f->recorder.state==COMP_CONT_SEALED && f->count==1u &&
        f->recorder.stop_reason==COMP_CONT_STOP_FULL && !f->microphone &&
        f->recorder.stats.overflows==0u && f->sealed[0].descriptor.sample_count==
            (uint64_t)f->recorder.stats.accepted_pcm_blocks*160u);
    return true;
}
static bool delayed_reservation_is_not_evidence_of_full(void)
{
    fixture_t *f=&fixture;CHECK(initialize(f,false));int16_t pcm[160];
    f->hold_next=true;unsigned blocks=0u;
    while(f->microphone && blocks<40u) {
        pcm_block(blocks,pcm);++blocks;f->now+=10u;
        CHECK(comp_cont_recording_pcm(&f->recorder,pcm,160u));CHECK(poll_many(f,80u));
    }
    printf("OBSERVED microphone=%u state=%u stop_reason=%u accepted=%u next_phase=%u\n", (unsigned)f->microphone,(unsigned)f->recorder.state,(unsigned)f->recorder.stop_reason,blocks,f->next_phase);
    CHECK(!f->microphone && (f->recorder.state==COMP_CONT_STOPPING || f->recorder.state==COMP_CONT_SEALED));
    CHECK(!f->no_next && f->next_phase==4u && DATA-f->recorder.active.reserved_bytes>=4096u);
    printf("PENDING_FREE_SPACE stop_reason=%u available_outside_active=%u accepted_blocks=%u\n",
        (unsigned)f->recorder.stop_reason,(unsigned)(DATA-f->recorder.active.reserved_bytes),blocks);
    CHECK(f->recorder.stop_reason==COMP_CONT_STOP_PREPARE_DELAYED);
    f->hold_next=false;
    for(unsigned i=0;i<5000u && f->recorder.state!=COMP_CONT_SEALED;i++) CHECK(poll_many(f,1u));
    CHECK(f->recorder.state==COMP_CONT_SEALED && f->count>=1u && !f->recorder.stats.overflows);
    CHECK((f->sealed[f->count-1u].descriptor.flags&COMP_REC_V2_LAST)!=0u);
    CHECK((f->sealed[f->count-1u].descriptor.flags&COMP_REC_V2_RECOVERED)!=0u);
    CHECK((f->sealed[f->count-1u].descriptor.flags>>COMP_REC_V2_END_SHIFT)==COMP_REC_END_UNKNOWN);
    CHECK(f->recorder.stats.storage_full_stops==0u);
    uint8_t wire[COMP_REC_V2_DESCRIPTOR_BYTES];
    CHECK(comp_rec_v2_encode(&f->sealed[f->count-1u].descriptor,wire,sizeof(wire)));
    FILE *proof=fopen("pending-reason.crs2","wb");CHECK(proof);
    CHECK(fwrite(wire,1u,sizeof(wire),proof)==sizeof(wire)&&!fclose(proof));
    return true;
}
static bool quick_stop(void)
{
    fixture_t *f=&fixture;CHECK(initialize(f,true));CHECK(comp_cont_recording_stop(&f->recorder,91u));
    for (unsigned i=0u;i<500u && f->recorder.state!=COMP_CONT_CANCELED;i++) CHECK(poll_many(f,1u));
    CHECK(f->recorder.state==COMP_CONT_CANCELED && !f->microphone && !f->count &&
        f->recorder.stats.accepted_pcm_blocks==0u && f->recorder.writer.canceled &&
        f->starts==1u && f->stops==1u && f->catalog.visible_mask==0u);
    return true;
}
static bool cancel_gc(void)
{
    fixture_t *f=&fixture;CHECK(quick_stop());
    comp_cont_config_t cfg={microphone,now_ms,next,seal,cancel,background,f,SEG_FRAMES,10u,false,NULL};
    for (unsigned attempt=1u;attempt<50u;attempt++) {
        template_entry(f,NULL);
        for (unsigned i=0u;i<1000u && f->next_phase!=3u;i++) {
            comp_segment_result_t result=prepare_step(f);
            CHECK(result==COMP_SEG_OK || result==COMP_SEG_PENDING);
        }
        CHECK(f->next_phase==3u);
        CHECK(comp_cont_recording_init(&f->recorder,&cfg,&f->next_entry,&f->next_writer,91u));
        f->next_phase=4u;
        /* Cancel before microphone start as well as immediately after start. */
        CHECK(comp_cont_recording_stop(&f->recorder,91u));
        for (unsigned i=0u;i<1000u && f->recorder.state!=COMP_CONT_CANCELED;i++) CHECK(poll_many(f,1u));
        CHECK(f->recorder.state==COMP_CONT_CANCELED);
    }
    CHECK(f->catalog.bank_serial>=2u && f->catalog.next_id==51u);
    comp_segment_port_t mount_port={read_media,program_media,erase_media,f,0u};
    CHECK(comp_segment_catalog_mount_begin(&f->catalog,&mount_port,0u,BANK,BASE,DATA,uid,7u)==COMP_SEG_PENDING);
    CHECK(finish_catalog(f)==COMP_SEG_OK && f->catalog.visible_mask==0u);
    for (uint8_t i=0u;i<COMP_SEGMENT_CAPACITY;i++) CHECK(f->catalog.slots[i]==255u);
    printf("PASS canceled reservations cross actual catalogGC and remount:50quick cancels,0leaked slots,0published empty audio; software only\n");
    return true;
}
static bool recover_timeline(fixture_t *f,const comp_segment_entry_t *reservation,
    bool open,bool ended,uint32_t frames,uint64_t elapsed)
{
    comp_segment_audio_recovery_t recovered={0};comp_segment_audio_port_t port=audio_port(f);
    CHECK(comp_segment_audio_recover_begin(&recovered,&port,reservation,BASE,f->scratch)==COMP_SEG_PENDING);
    comp_segment_result_t result=COMP_SEG_PENDING;
    for(unsigned i=0u;i<200u&&result==COMP_SEG_PENDING;i++)result=comp_segment_audio_recover_poll(&recovered);
    CHECK(result==COMP_SEG_OK&&recovered.pause_open==open&&recovered.ended_paused==ended&&
        recovered.frames==frames&&recovered.timeline_ms==elapsed);
    uint32_t bytes=0u,actual_frames=0u,crc=0u;uint8_t hash[32];
    CHECK(comp_segment_audio_recovered(&recovered,&bytes,&actual_frames,&crc,hash));
    CHECK(bytes==f->recorder.writer.committed_bytes&&crc==f->recorder.content_crc);
    return true;
}
static bool pause_resume(void)
{
    fixture_t *f=&fixture;CHECK(initialize_mode(f,true,true));int16_t pcm[160];
    /* Monotonic accumulation must survive HAL's32bit tick wrap. */
    f->now=UINT32_MAX-35u;f->recorder.clock_ms=f->now;
    for(unsigned i=0u;i<3u;i++) {
        pcm_block(i,pcm);f->now+=10u;CHECK(comp_cont_recording_pcm(&f->recorder,pcm,160u));CHECK(poll_many(f,80u));
    }
    CHECK(!comp_cont_recording_pause(&f->recorder,90u,1u));
    CHECK(!comp_cont_recording_pause(&f->recorder,91u,UINT32_MAX)&&f->microphone);
    f->recorder.config.segment_frames=80u;
    CHECK(!comp_cont_recording_pause(&f->recorder,91u,1u)&&f->microphone&&f->recorder.command_sequence==0u);
    f->recorder.config.segment_frames=SEG_FRAMES;
    CHECK(comp_cont_recording_pause(&f->recorder,91u,1u)&&f->recorder.state==COMP_CONT_PAUSE_PENDING&&f->microphone);
    CHECK(comp_cont_recording_pause(&f->recorder,91u,1u)&&f->stops==0u);
    pcm_block(3u,pcm);f->now+=10u;CHECK(comp_cont_recording_pcm(&f->recorder,pcm,160u));
    CHECK(!f->microphone&&f->recorder.state==COMP_CONT_PAUSING);
    for(unsigned i=0u;i<500u&&f->recorder.state!=COMP_CONT_PAUSED;i++)CHECK(poll_many(f,1u));
    CHECK(f->recorder.state==COMP_CONT_PAUSED&&f->recorder.encoder_owned&&
        f->recorder.codec.frames_encoded==2u&&!f->recorder.codec.pcm_fill&&!f->recorder.stage_length&&
        f->starts==1u&&f->stops==1u&&f->recorder.stats.accepted_pcm_blocks==4u);
    comp_segment_entry_t reservation=f->recorder.active;
    CHECK(recover_timeline(f,&reservation,true,false,2u,40u));
    f->now+=5000u;CHECK(poll_many(f,2u));
    CHECK(!comp_cont_recording_pcm(&f->recorder,pcm,160u)&&f->recorder.stats.accepted_pcm_blocks==4u);
    CHECK(comp_cont_recording_resume(&f->recorder,91u,2u)&&f->recorder.state==COMP_CONT_RESUMING);
    CHECK(comp_cont_recording_resume(&f->recorder,91u,2u)&&f->starts==2u);
    /* Incoming PCM during the resume commit must remain queued, not move the
     * event's exact pre-resume sample point or reset the encoder. */
    for(unsigned i=4u;i<6u;i++) {
        pcm_block(i,pcm);f->now+=10u;CHECK(comp_cont_recording_pcm(&f->recorder,pcm,160u));
    }
    CHECK(poll_many(f,150u)&&f->recorder.state==COMP_CONT_RUNNING);
    CHECK(!comp_cont_recording_pause(&f->recorder,91u,1u)&&f->microphone);
    for(unsigned i=6u;i<8u;i++) {
        pcm_block(i,pcm);f->now+=10u;CHECK(comp_cont_recording_pcm(&f->recorder,pcm,160u));CHECK(poll_many(f,80u));
    }
    CHECK(comp_cont_recording_stop(&f->recorder,91u));
    for(unsigned i=0u;i<1000u&&f->recorder.state!=COMP_CONT_SEALED;i++)CHECK(poll_many(f,1u));
    CHECK(f->count==1u&&f->recorder.state==COMP_CONT_SEALED&&f->starts==2u&&f->stops==2u&&
        f->sealed[0].descriptor.sample_count==1280u&&f->sealed[0].descriptor.session_id==55u);
    CHECK(recover_timeline(f,&reservation,false,false,4u,5040u));
    uint32_t raw_bytes=0u;comp_segment_audio_port_t port=audio_port(f);
    for(uint32_t page=0u;raw_bytes<f->sealed[0].descriptor.encoded_length;page++) {
        uint8_t n=0u;CHECK(comp_segment_audio_read_page(&port,&f->sealed[0],BASE,page,f->scratch,&n)==COMP_SEG_OK);
        memcpy(f->raw[0]+raw_bytes,f->scratch,n);raw_bytes+=n;
    }
    CHECK(f->raw[0][4]==2u&&f->raw[0][7]==1u);
    memcpy(joined,f->raw[0],12u);joined[4]=1u;joined[7]=0u;
    uint32_t joined_bytes=12u;unsigned events=0u;
    for(uint32_t at=12u;at<raw_bytes;) {
        if(f->raw[0][at]==255u){at++;continue;}
        if(f->raw[0][at]==0u&&f->raw[0][at+1u]==0u) {
            comp_rec_timeline_event_t e;CHECK(comp_rec_timeline_decode(f->raw[0]+at,raw_bytes-at,&e));
            CHECK(at%248u==0u&&e.sample_offset==640u&&e.sequence==events+1u&&
                e.elapsed_ms==(events?5040u:40u)&&e.kind==(events?2u:1u));
            events++;at+=32u;continue;
        }
        CHECK(f->raw[0][at]==40u&&f->raw[0][at+1u]==0u);
        memcpy(joined+joined_bytes,f->raw[0]+at,42u);joined_bytes+=42u;at+=42u;
    }
    CHECK(events==2u&&f->recorder.active_non_audio_bytes==raw_bytes-joined_bytes);
    companion_opus16_rt_t codec;CHECK(companion_opus16_rt_init_rate_frame(&codec,16000u,20u));
    uint32_t baseline_bytes=0u;uint8_t encoded[402];
    for(unsigned i=0u;i<8u;i++) {
        pcm_block(i,pcm);size_t n=companion_opus16_rt_encode(&codec,pcm,160u,encoded,sizeof(encoded),i==0u);
        memcpy(baseline+baseline_bytes,encoded,n);baseline_bytes+=(uint32_t)n;
    }
    CHECK(baseline_bytes==joined_bytes&&!memcmp(joined,baseline,joined_bytes));
    companion_opus16_rt_destroy(&codec);
    puts("pause: real Opus byte identity, no reset/silence/lost half-frame; durable5000ms gap, tick wrap, stale/duplicate controls and pre-mute capacity refusal; software only");
    return true;
}
static bool pause_rollover(void)
{
    fixture_t *f=&fixture;CHECK(initialize_mode(f,false,true));int16_t pcm[160];
    for(unsigned i=0u;i<BLOCKS;i++) {
        pcm_block(i,pcm);f->now+=10u;CHECK(comp_cont_recording_pcm(&f->recorder,pcm,160u));CHECK(poll_many(f,80u));
        if(i==7u) {
            CHECK(comp_cont_recording_pause(&f->recorder,91u,1u));
            for(unsigned n=0u;n<500u&&f->recorder.state!=COMP_CONT_PAUSED;n++)CHECK(poll_many(f,1u));
            CHECK(f->recorder.state==COMP_CONT_PAUSED&&!f->microphone);
            f->now+=2000u;CHECK(comp_cont_recording_resume(&f->recorder,91u,2u));CHECK(poll_many(f,80u));
        }
    }
    CHECK(comp_cont_recording_stop(&f->recorder,91u));
    for(unsigned i=0u;i<3000u&&f->recorder.state!=COMP_CONT_SEALED;i++)CHECK(poll_many(f,1u));
    for(unsigned i=0u;i<3000u&&f->reclaims<f->count;i++) {
        comp_segment_result_t result=background(f);CHECK(result==COMP_SEG_OK||result==COMP_SEG_PENDING);
    }
    CHECK(f->count==4u&&f->reclaims==4u&&f->starts==2u&&f->stops==2u);
    memcpy(joined,f->raw[0],12u);joined[4]=1u;joined[7]=0u;
    uint32_t length=12u;unsigned events=0u;
    for(unsigned segment=0u;segment<f->count;segment++) {
        const comp_rec_v2_descriptor_t *d=&f->sealed[segment].descriptor;
        CHECK(d->session_id==55u&&d->segment_index==segment&&d->sample_offset==(uint64_t)segment*SEG_FRAMES*320u&&
            d->sample_count==SEG_FRAMES*320u&&f->raw[segment][4]==2u);
        for(uint32_t at=12u;at<d->encoded_length;) {
            if(f->raw[segment][at]==255u){at++;continue;}
            if(!f->raw[segment][at]&&!f->raw[segment][at+1u]) {
                comp_rec_timeline_event_t e;CHECK(comp_rec_timeline_decode(f->raw[segment]+at,d->encoded_length-at,&e));
                CHECK(segment==0u&&e.sample_offset==1280u&&e.elapsed_ms==(events?2080u:80u));
                events++;at+=32u;continue;
            }
            CHECK(f->raw[segment][at]==40u&&!f->raw[segment][at+1u]);
            memcpy(joined+length,f->raw[segment]+at,42u);length+=42u;at+=42u;
        }
    }
    companion_opus16_rt_t codec;CHECK(companion_opus16_rt_init_rate_frame(&codec,16000u,20u));
    uint8_t encoded[402];uint32_t baseline_bytes=0u;
    for(unsigned i=0u;i<BLOCKS;i++) {
        pcm_block(i,pcm);size_t n=companion_opus16_rt_encode(&codec,pcm,160u,encoded,sizeof(encoded),i==0u);
        memcpy(baseline+baseline_bytes,encoded,n);baseline_bytes+=(uint32_t)n;
    }
    CHECK(events==2u&&length==baseline_bytes&&!memcmp(joined,baseline,length));
    companion_opus16_rt_destroy(&codec);
    puts("pause rollover:4physical segments keep one session/sample axis and exact40real Opus packets, all CRC/SHA reclaims; software only");
    return true;
}
static bool stop_paused(void)
{
    fixture_t *f=&fixture;CHECK(initialize_mode(f,true,true));int16_t pcm[160];
    for(unsigned i=0u;i<2u;i++) {
        pcm_block(i,pcm);f->now+=10u;CHECK(comp_cont_recording_pcm(&f->recorder,pcm,160u));CHECK(poll_many(f,50u));
    }
    CHECK(comp_cont_recording_pause(&f->recorder,91u,1u));
    for(unsigned i=0u;i<500u&&f->recorder.state!=COMP_CONT_PAUSED;i++)CHECK(poll_many(f,1u));
    comp_segment_entry_t reservation=f->recorder.active;
    f->now+=3000u;CHECK(comp_cont_recording_stop(&f->recorder,91u));
    CHECK(comp_cont_recording_stop(&f->recorder,91u));
    for(unsigned i=0u;i<1000u&&f->recorder.state!=COMP_CONT_SEALED;i++)CHECK(poll_many(f,1u));
    CHECK(f->recorder.state==COMP_CONT_SEALED&&f->starts==1u&&f->stops==1u&&f->count==1u);
    CHECK(recover_timeline(f,&reservation,false,true,1u,3020u));
    /* A CRC-valid RESUME without its PAUSE is still a bad timeline. */
    uint8_t *page=f->bytes+BASE+reservation.extent_offset+512u;
    page[6]=COMP_REC_TIMELINE_RESUME;comp_rec_put32(page+28u,comp_rec_crc(page,28u));
    uint8_t identity[9];comp_rec_put32(identity,f->recorder.writer.binding_crc);
    comp_rec_put32(identity+4u,1u);identity[8]=248u;
    comp_rec_put32(page+248u,~comp_rec_crc_step(comp_rec_crc_step(UINT32_MAX,identity,9u),page,248u));
    comp_segment_audio_recovery_t recovery={0};comp_segment_audio_port_t port=audio_port(f);
    CHECK(comp_segment_audio_recover_begin(&recovery,&port,&reservation,BASE,f->scratch)==COMP_SEG_PENDING);
    comp_segment_result_t result=COMP_SEG_PENDING;
    for(unsigned i=0u;i<100u&&result==COMP_SEG_PENDING;i++)result=comp_segment_audio_recover_poll(&recovery);
    CHECK(result==COMP_SEG_CORRUPT);
    puts("paused STOP: one session, no microphone restart, exact3000ms end gap; CRC-valid unpaired event rejected; software only");
    return true;
}
static bool pause_export(const char *path)
{
    /* Cross-language format fixture from the actual continuous engine and
     * fixed-point Opus. No seed/device/physical-radio acceptance is claimed. */
    CHECK(pause_rollover());fixture_t *f=&fixture;FILE *file=fopen(path,"wb");CHECK(file);
    uint8_t header[8]={'C','P','F','2',0,0,0,0};comp_rec_put32(header+4u,f->count);
    bool ok=fwrite(header,1u,sizeof(header),file)==sizeof(header);
    for(unsigned i=0u;i<f->count;i++) {
        uint8_t length[4],wire[112];uint32_t bytes=f->sealed[i].descriptor.encoded_length;
        comp_rec_put32(length,bytes);ok=comp_rec_v2_encode(&f->sealed[i].descriptor,wire,sizeof(wire))&&ok;
        ok=(fwrite(length,1u,4u,file)==4u)&&ok;
        ok=(fwrite(wire,1u,sizeof(wire),file)==sizeof(wire))&&ok;
        ok=(fwrite(f->raw[i],1u,bytes,file)==bytes)&&ok;
    }
    uint8_t length[4];uint32_t bytes=12u+(BLOCKS/2u)*42u;comp_rec_put32(length,bytes);
    ok=(fwrite(length,1u,4u,file)==4u)&&ok;ok=(fwrite(baseline,1u,bytes,file)==bytes)&&ok;
    ok=fclose(file)==0&&ok;CHECK(ok);
    puts("EXPORTED_C_PAUSE_FORMAT_REAL_OPUS_SOFTWARE_ONLY");return true;
}
static bool source_boundary_case(unsigned blocks,bool no_next,unsigned paused,const char *export_path)
{
    fixture_t *f=&fixture;CHECK(initialize_mode(f,no_next,COMP_CONT_TIMELINE_SOURCE_BOUNDARY));
    int16_t pcm[160];unsigned accepted=0u;
    for(unsigned b=0u;b<blocks&&f->microphone;b++) {
        pcm_block(b,pcm);CHECK(comp_cont_recording_pcm(&f->recorder,pcm,160u));++accepted;
        f->now+=10u;CHECK(poll_many(f,80u));
    }
    if(paused) {
        CHECK(comp_cont_recording_pause(&f->recorder,91u,1u));
        CHECK(poll_many(f,500u));CHECK(f->recorder.state==COMP_CONT_PAUSED);
        if(paused==2u) {
            f->now+=5000u;CHECK(comp_cont_recording_resume(&f->recorder,91u,2u));CHECK(poll_many(f,500u));
            CHECK(f->microphone&&f->recorder.state==COMP_CONT_RUNNING);
            for(unsigned b=0u;b<2u;b++) {
                pcm_block(accepted,pcm);CHECK(comp_cont_recording_pcm(&f->recorder,pcm,160u));++accepted;
                f->now+=10u;CHECK(poll_many(f,80u));
            }
        }
    }
    if(f->recorder.state!=COMP_CONT_SEALED)CHECK(comp_cont_recording_stop(&f->recorder,91u));
    for(unsigned i=0u;i<5000u&&f->recorder.state!=COMP_CONT_SEALED&&f->recorder.state!=COMP_CONT_CANCELED;i++)
        CHECK(poll_many(f,1u));
    CHECK(f->starts==(paused==2u?2u:1u)&&f->stops==f->starts&&!f->microphone);
    if(!accepted){CHECK(f->recorder.state==COMP_CONT_CANCELED&&f->count==0u);return true;}
    CHECK(f->recorder.state==COMP_CONT_SEALED&&f->count>0u);
    /* Re-open the actual final committed media as an interrupted WRITING
     * reservation. Declaration/drain recognition does not promote it to a
     * normal STOP or fabricate a terminal catalogue entry. */
    comp_segment_entry_t reservation=f->sealed[f->count-1u];reservation.state=COMP_SEG_WRITING;
    reservation.descriptor.sample_count=0u;reservation.descriptor.encoded_length=0u;reservation.descriptor.flags=0u;
    comp_segment_audio_recovery_t recovered={0};comp_segment_audio_port_t port=audio_port(f);
    CHECK(comp_segment_audio_recover_begin(&recovered,&port,&reservation,BASE,f->scratch)==COMP_SEG_PENDING);
    comp_segment_result_t recovery=COMP_SEG_PENDING;
    for(unsigned i=0u;i<200u&&recovery==COMP_SEG_PENDING;i++)recovery=comp_segment_audio_recover_poll(&recovered);
    CHECK(recovery==COMP_SEG_OK&&recovered.codec_config_seen&&recovered.frames>0u&&
        recovered.frames*320u==f->sealed[f->count-1u].descriptor.sample_count);
    if(recovered.codec_end_seen)CHECK(!recovered.codec_drain_pending);
    for(unsigned i=0u;i<5000u&&f->reclaims<f->count;i++) {
        comp_segment_result_t result=background(f);CHECK(result==COMP_SEG_OK||result==COMP_SEG_PENDING);
    }
    CHECK(f->reclaims==f->count);
    FILE *file=export_path?fopen(export_path,"wb"):NULL;if(export_path)CHECK(file);
    unsigned frames=0u,configs=0u,ends=0u;uint64_t declared_end=0u;
    for(unsigned s=0u;s<f->count;s++) {
        const comp_rec_v2_descriptor_t *d=&f->sealed[s].descriptor;const uint8_t *raw=f->raw[s];
        CHECK(raw[4]==4u&&raw[7]==7u&&d->sample_offset==(uint64_t)frames*320u);
        unsigned local_frames=0u;
        for(uint32_t at=12u;at<d->encoded_length;) {
            if(raw[at]==255u){++at;continue;}
            if(!raw[at]&&!raw[at+1u]) {
                if(!memcmp(raw+at+2u,"CDB1",4u)) {
                    comp_rec_codec_boundary_t e;CHECK(comp_rec_codec_boundary_decode(raw+at,d->encoded_length-at,&e));
                    CHECK(e.delay_samples==f->recorder.codec.encoder_delay_samples);
                    if(e.kind==COMP_REC_CODEC_CONFIG){CHECK(at==12u&&e.encoded_samples==(uint64_t)frames*320u);++configs;}
                    else {CHECK(at%248u==0u&&e.valid_source_samples==(uint64_t)accepted*160u);
                        CHECK(e.encoded_samples==((uint64_t)frames+1u)*320u);declared_end=e.encoded_samples;++ends;}
                } else {
                    comp_rec_timeline_event_t e;CHECK(!ends&&comp_rec_timeline_decode(raw+at,d->encoded_length-at,&e));
                }
                at+=32u;continue;
            }
            CHECK(raw[at]==40u&&raw[at+1u]==0u&&(!ends||(uint64_t)frames*320u<declared_end));
            ++frames;++local_frames;at+=42u;
        }
        CHECK(d->sample_count==(uint64_t)local_frames*320u);
        if(file){uint8_t length[4];comp_rec_put32(length,d->encoded_length);
            CHECK(fwrite(length,1u,4u,file)==4u&&fwrite(raw,1u,d->encoded_length,file)==d->encoded_length);}
    }
    if(file)CHECK(!fclose(file));
    CHECK(configs==f->count&&ends==1u&&frames==accepted/2u+1u&&declared_end==(uint64_t)frames*320u);
    CHECK((f->sealed[f->count-1u].descriptor.flags&COMP_REC_V2_LAST)!=0u);
    printf("source_boundary accepted_blocks=%u frames=%u segments=%u full=%u paused=%u exact_source_samples=%u\n",
        accepted,frames,f->count,(unsigned)no_next,(unsigned)paused,accepted*160u);return true;
}
static bool geometry_bind_bound(void)
{
    comp_recording_geometry_t g;CHECK(comp_recording_geometry_plan(15695872u,64u,&g));
    CHECK(g.extent_bytes==270336u && g.segment_frames==6211u);
    comp_segment_entry_t e={0};e.state=COMP_SEG_WRITING;e.reserved_bytes=g.extent_bytes;
    e.descriptor.codec=3u;e.descriptor.recording_id=1u;e.descriptor.format_epoch=1u;e.descriptor.session_id=1u;
    memcpy(e.descriptor.device_uid,uid,sizeof(uid));
    comp_segment_audio_t w={0};w.prepared=true;w.entry=&e;
    comp_cont_config_t c={microphone,now_ms,next,seal,cancel,background,&fixture,g.segment_frames,10u,COMP_CONT_TIMELINE_SOURCE_BOUNDARY,NULL};
    comp_cont_recording_t r;
    CHECK(comp_cont_recording_init(&r,&c,&e,&w,1u));
    comp_cont_recording_fault(&r,COMP_SEG_BAD_STATE);
    w.claimed=false; /* Independent admission cases: the first init claimed it. */
    c.segment_frames=6224u;
    CHECK(!comp_cont_recording_init(&r,&c,&e,&w,1u));
    c.pause_timeline=0u;CHECK(comp_cont_recording_init(&r,&c,&e,&w,1u));
    comp_cont_recording_fault(&r,COMP_SEG_BAD_STATE);
    puts("PASS production bind accepts6211 with source boundary, rejects old6596224, legacy mode unchanged; software only");
    return true;
}
int main(int argc,char **argv)
{
    if(argc==2&&!strcmp(argv[1],"pending-free-space"))return delayed_reservation_is_not_evidence_of_full()?0:1;
    if(argc==2&&!strcmp(argv[1],"geometry-bind"))return geometry_bind_bound()?0:1;
    if(argc==2&&!strcmp(argv[1],"source-boundary"))return
        source_boundary_case(0u,false,false,NULL)&&source_boundary_case(1u,false,false,NULL)&&
        source_boundary_case(2u,false,false,NULL)&&source_boundary_case(20u,false,false,NULL)&&
        source_boundary_case(21u,false,false,NULL)&&source_boundary_case(40u,false,false,NULL)&&
        source_boundary_case(40u,true,false,NULL)&&source_boundary_case(4u,false,true,NULL)&&
        source_boundary_case(4u,false,2u,NULL)?0:1;
    if(argc==3&&!strcmp(argv[1],"source-boundary-export"))return source_boundary_case(40u,false,false,argv[2])?0:1;
    if(argc==3&&!strcmp(argv[1],"source-boundary-paused-export"))return source_boundary_case(20u,false,true,argv[2])?0:1;
    if(argc==3&&!strcmp(argv[1],"pause-export"))return pause_export(argv[2])?0:1;
    if(argc==2&&!strcmp(argv[1],"pause"))return pause_resume()&&pause_rollover()&&stop_paused()?0:1;
    if (argc==2 && strcmp(argv[1],"cancel-gc")==0) return cancel_gc()?0:1;
    if (argc==2 && strcmp(argv[1],"full")==0) {
        if(!full())return 1;
        puts("PASS reduced-scratch continuous full-pool safe drain; software only");return 0;
    }
    if (!capture() || !full() || !quick_stop()) return 1;
    printf("PASS real Opus continuous capture software integration: full pool safe seal, durable successor gate, exact STOP boundary; core_context=%zu old_capture_and_journal=%zu; board/Type radio/energy NOT_RUN\n",
        sizeof(comp_cont_recording_t),sizeof(comp_wba_recording_service_t)+sizeof(comp_recording_journal_t));
    return 0;
}
