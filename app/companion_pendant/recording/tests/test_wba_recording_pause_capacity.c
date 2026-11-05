/* Actual production 6000-frame /256KiB policy, real Opus, command-level NOR.
 * This is software storage/control evidence, never a physical recording. */
#define COMP_PRODUCT_TEST_MAIN prior_product_capacity_main
#include "test_wba_recording_product.c"

static uint8_t expected_audio[600000],actual_raw[262144];
static size_t expected_bytes;
static unsigned blocks;

static void capacity_start(void)
{
    reset();nor=make();f.automatic_erase=true;mic=false;mic_starts=mic_stops=reports=0u;
    comp_wba_pipeline_config_t cfg={0};cfg.microphone=microphone;cfg.now_ms=now;
    cfg.segment_frames=6000u;cfg.extent_bytes=262144u;
    assert(comp_wba_recording_product_bind(&product_rec,&nor,0u,24576u,DATA_BASE,786432u,
        49152u,device_uid,7u,&cfg,product_report));
    product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    assert(comp_wba_recording_product_prepare_timeline(&product_rec,101u,1u,0u,91u,true));
    for(unsigned i=0u;i<20000u&&!comp_wba_recording_product_ready(&product_rec,91u);i++)product_tick();
    assert(comp_wba_recording_product_ready(&product_rec,91u)&&comp_wba_recording_product_control(&product_rec,true,91u));
    blocks=0u;
}
static void audio_frames(unsigned frames)
{
    for(unsigned i=0u;i<frames*2u;i++) {
        int16_t samples[160];pcm(blocks++,samples);
        assert(mic&&comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned step=0u;step<40u;step++)product_tick();
        assert(product_rec.pipeline.state==COMP_PIPE_RECORDING);
    }
}
static void change_pause(bool paused)
{
    assert(comp_wba_recording_product_set_paused(&product_rec,91u,paused));
    comp_cont_state_t desired=paused?COMP_CONT_PAUSED:COMP_CONT_RUNNING;
    for(unsigned i=0u;i<30000u&&product_rec.capture.engine.state!=desired;i++)product_tick();
    assert(product_rec.capture.engine.state==desired&&mic!=paused);
}
static void finish(void)
{
    assert(comp_wba_recording_product_control(&product_rec,false,91u));
    for(unsigned i=0u;i<40000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED&&!mic);
}
static void reference(void)
{
    companion_opus16_rt_t codec;assert(companion_opus16_rt_init_rate_frame(&codec,16000u,20u));
    expected_bytes=0u;
    for(unsigned i=0u;i<blocks;i++) {
        int16_t samples[160];uint8_t packet[402];pcm(i,samples);
        size_t n=companion_opus16_rt_encode(&codec,samples,160u,packet,sizeof(packet),false);
        assert(expected_bytes+n<=sizeof(expected_audio));
        memcpy(expected_audio+expected_bytes,packet,n);expected_bytes+=n;
    }
    uint8_t tail[402];size_t n=companion_opus16_rt_flush(&codec,tail,sizeof(tail));
    memcpy(expected_audio+expected_bytes,tail,n);expected_bytes+=n;
    companion_opus16_rt_destroy(&codec);
}
static void verify_entry(const comp_segment_entry_t *e,size_t *audio_at,unsigned *events)
{
    comp_segment_audio_port_t port=comp_wba_segment_storage_audio_port(&product_rec.storage);
    size_t bytes=0u;
    for(uint32_t page=0u;bytes<e->descriptor.encoded_length;page++) {
        uint8_t raw[256],length=0u;comp_segment_result_t r;
        do {f.now+=2u;r=comp_segment_audio_read_page(&port,e,DATA_BASE,page,raw,&length);} while(r==COMP_SEG_PENDING);
        assert(r==COMP_SEG_OK&&bytes+length<=sizeof(actual_raw));
        memcpy(actual_raw+bytes,raw,length);bytes+=length;
    }
    assert(bytes==e->descriptor.encoded_length&&actual_raw[4]==2u);
    companion_sha256_t h;uint8_t digest[32];companion_sha256_init(&h);
    companion_sha256_update(&h,actual_raw,bytes);companion_sha256_final(&h,digest);
    assert(!memcmp(digest,e->descriptor.sha256,32u)&&comp_rec_crc(actual_raw,bytes)==e->descriptor.content_crc32);
    size_t frames=0u;
    for(size_t at=12u;at<bytes;) {
        if(actual_raw[at]==255u){at++;continue;}
        if(actual_raw[at]==0u) {
            comp_rec_timeline_event_t event={0};
            assert(at+COMP_REC_TIMELINE_BYTES<=bytes&&comp_rec_timeline_decode(actual_raw+at,bytes-at,&event));
            assert(event.sample_offset==e->descriptor.sample_offset+frames*320u);
            (*events)++;at+=COMP_REC_TIMELINE_BYTES;continue;
        }
        assert(at+42u<=bytes&&*audio_at+42u<=expected_bytes);
        assert(!memcmp(actual_raw+at,expected_audio+*audio_at,42u));
        at+=42u;*audio_at+=42u;frames++;
    }
    assert(frames*320u==e->descriptor.sample_count);
    /* Re-open the immutable provenance as boot recovery would. Cancellation
     * and replacement cannot leave an old offset binding behind. */
    comp_segment_entry_t writing=*e;writing.state=COMP_SEG_WRITING;
    writing.descriptor.sample_count=writing.descriptor.encoded_length=0u;
    writing.descriptor.flags=writing.descriptor.sync_state=0u;writing.descriptor.total_segments=0u;
    comp_segment_audio_recovery_t recovered={0};uint8_t page[256];
    assert(comp_segment_audio_recover_begin(&recovered,&port,&writing,DATA_BASE,page)==COMP_SEG_PENDING);
    comp_segment_result_t r=COMP_SEG_PENDING;
    for(unsigned i=0u;i<10000u&&r==COMP_SEG_PENDING;i++){f.now+=2u;r=comp_segment_audio_recover_poll(&recovered);}
    uint32_t recovered_bytes=0u,recovered_frames=0u,crc=0u;
    assert(r==COMP_SEG_OK&&comp_segment_audio_recovered(&recovered,&recovered_bytes,&recovered_frames,&crc,digest));
    assert(recovered_bytes==bytes&&recovered_frames==frames&&crc==e->descriptor.content_crc32&&!memcmp(digest,e->descriptor.sha256,32u));
}
static void repeated_pause_and_roll(void)
{
    capacity_start();comp_cont_recording_t *r=&product_rec.capture.engine;
    for(unsigned cycle=0u;cycle<16u;cycle++) {
        audio_frames(4u);change_pause(true);change_pause(false);
    }
    assert(r->active_frame_limit<6000u&&r->command_sequence==32u);
    uint32_t limit=r->active_frame_limit;
    while(r->active.descriptor.segment_index==0u)audio_frames(1u);
    assert(r->active.descriptor.sample_offset==(uint64_t)limit*320u);
    audio_frames(8u);change_pause(true);finish();reference();
    comp_segment_entry_t first=product_entry(0u),last=product_entry(1u);
    assert(first.descriptor.sample_offset==0u&&first.descriptor.sample_count==(uint64_t)limit*320u&&
        last.descriptor.sample_offset==first.descriptor.sample_count&&last.descriptor.segment_index==1u&&
        (last.descriptor.flags&COMP_REC_V2_LAST)&&last.descriptor.total_segments==2u);
    size_t audio_at=0u;unsigned events=0u;verify_entry(&first,&audio_at,&events);verify_entry(&last,&audio_at,&events);
    assert(audio_at==expected_bytes&&events==34u&&r->stats.overflows==0u&&r->stats.budget_failures==0u);
    printf("PASS 6000-frame/256KiB policy:16 pause/resume cycles, shortened first segment=%u frames, exact successor offset/provenance/recovery, paused STOP; all Opus packets identical to uncut encode; software only\n",limit);
}
static void reject_nonempty_future(void)
{
    capacity_start();comp_cont_recording_t *r=&product_rec.capture.engine;
    for(unsigned cycle=0u;cycle<2u;cycle++){audio_frames(4u);change_pause(true);change_pause(false);}
    for(unsigned i=0u;i<30000u&&(!product_rec.pipeline.future_writer.prepared||product_rec.pipeline.future_writer.phase);i++)product_tick();
    assert(product_rec.pipeline.future_writer.prepared&&!product_rec.pipeline.future_writer.claimed);
    uint32_t at=DATA_BASE+product_rec.pipeline.future.extent_offset+256u;
    f.bytes[at]=0u;audio_frames(4u);change_pause(true);
    assert(r->active_frame_limit<6000u);
    unsigned erases=f.erases;
    for(unsigned i=0u;i<30000u&&product_rec.pipeline.state!=COMP_PIPE_FAILED;i++)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FAILED&&r->state==COMP_CONT_FAULT&&!mic&&f.bytes[at]==0u&&f.erases==erases);
    puts("PASS shortened-horizon replacement refuses a nonempty future; reservation remains owned, no erase or provenance rewrite; software only");
}
static void stop_during_future_replacement(void)
{
    capacity_start();
    for(unsigned cycle=0u;cycle<2u;cycle++){audio_frames(4u);change_pause(true);change_pause(false);}
    audio_frames(4u);change_pause(true);
    for(unsigned i=0u;i<30000u&&!product_rec.pipeline.future_writer.cancellation;i++)product_tick();
    assert(product_rec.pipeline.future_writer.cancellation&&!product_rec.pipeline.future_writer.claimed);
    finish();reference();
    comp_segment_entry_t only=product_entry(0u);size_t at=0u;unsigned events=0u;
    verify_entry(&only,&at,&events);product_refresh_space();
    assert(at==expected_bytes&&events==6u&&product_rec.space.used==1u&&product_rec.space.unsynced==1u);
    puts("PASS paused STOP during future cancellation finishes its owned transaction, preserves original bytes/6 events and releases unused extent; software only");
}
#ifndef COMP_CAPACITY_TEST_MAIN
#define COMP_CAPACITY_TEST_MAIN main
#endif
int COMP_CAPACITY_TEST_MAIN(void)
{
    repeated_pause_and_roll();stop_during_future_replacement();reject_nonempty_future();return 0;
}
