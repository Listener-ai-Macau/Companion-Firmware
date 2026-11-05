/* Current schema5, real production product/catalog/page writer, portable Opus.
 * Deliberately fills a reduced arena without consuming while recording.
 * This is storage ownership evidence, not MCU timing, audio or power evidence. */
#include <stdlib.h>
#define COMP_PRODUCT_TEST_MAIN profile_full_fixture_main
#include "test_wba_recording_product.c"

#define EXTENT_BYTES 270336u
#define SEGMENT_FRAMES 6209u
static uint8_t retained_extent[EXTENT_BYTES],original[EXTENT_BYTES];
static comp_segment_entry_t filled[2];

static bool snapshot(void *v,comp_rec_audio_profile_t *p)
{
    (void)v;memset(p,0,sizeof(*p));p->output=0u;p->filtered_mask=1u;
    p->gain_q15=32768u;p->right_gain_q15=32768u;p->decimation=96u;
    p->firmware_version=0x000103ebu;memset(p->firmware_source,0x74,20u);
    return true;
}
static void wait_progress(void *v){(void)v;f.now++;}
static bool status_transfer(void *v,const uint8_t *tx,uint8_t *rx,size_t n,uint32_t timeout)
{
    /* Adapt the current combined status read to the inherited command-level
     * NOR fixture; retain that fixture's real program/erase ownership rules. */
    if(tx&&rx&&n==2u&&(tx[0]==5u||tx[0]==0x35u)&&!f.command) {
        rx[0]=0u;return transfer(v,tx,NULL,1u,timeout)&&transfer(v,NULL,rx+1u,1u,timeout);
    }
    return transfer(v,tx,rx,n,timeout);
}
static void profile_start_mode(uint64_t session,uint32_t token,uint8_t mode)
{
    assert(comp_wba_recording_product_prepare_audio_profile(&product_rec,session,mode,0u,token));
    for(unsigned i=0u;i<20000u&&!comp_wba_recording_product_ready(&product_rec,token);++i)product_tick();
    assert(comp_wba_recording_product_ready(&product_rec,token));
    assert(comp_wba_recording_product_control(&product_rec,true,token));
}
static void profile_start(uint64_t session,uint32_t token) {profile_start_mode(session,token,1u);}
static void block(unsigned index)
{
    int16_t samples[160];pcm(index,samples);
    assert(mic&&comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
    for(unsigned i=0u;i<160u;++i)product_tick();
}
static void settle(void)
{
    for(unsigned i=0u;i<30000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;++i)product_tick();
    if(product_rec.pipeline.state!=COMP_PIPE_FINISHED)
        fprintf(stderr,"SETTLE pipeline=%u engine=%u failure=%u accepted=%lu\n",
            product_rec.pipeline.state,product_rec.capture.engine.state,product_rec.pipeline.failure,
            (unsigned long)product_rec.capture.engine.stats.accepted_pcm_blocks);
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED&&!mic);
    product_refresh_space();
}
static void consume(const comp_segment_entry_t *e)
{
    assert(comp_wba_recording_pipeline_consume(&product_rec.pipeline,&e->descriptor)==COMP_SEG_PENDING);
    for(unsigned i=0u;i<30000u&&comp_wba_recording_pipeline_consume_result(&product_rec.pipeline)==COMP_SEG_PENDING;++i)product_tick();
    assert(comp_wba_recording_pipeline_consume_result(&product_rec.pipeline)==COMP_SEG_OK);
    product_refresh_space();
}
static void unchanged_retained(const comp_segment_entry_t *retained)
{
    bool found=false;uint8_t expected[112],actual[112];
    assert(comp_rec_v2_encode(&retained->descriptor,expected,sizeof(expected)));
    for(uint8_t i=0u;i<COMP_SEGMENT_CAPACITY;++i)if(product_rec.catalog.slots[i]!=255u) {
        comp_segment_entry_t e;
        assert(comp_wba_segment_storage_entry(&product_rec.storage,&product_rec.catalog,i,&e)==COMP_SEG_OK);
        if(e.descriptor.recording_id!=retained->descriptor.recording_id)continue;
        assert(!found&&e.state==COMP_SEG_UNSYNCED&&e.extent_offset==retained->extent_offset&&e.reserved_bytes==retained->reserved_bytes);
        assert(comp_rec_v2_encode(&e.descriptor,actual,sizeof(actual))&&!memcmp(expected,actual,sizeof(actual)));
        found=true;
    }
    assert(found&&!memcmp(retained_extent,f.bytes+DATA_BASE+retained->extent_offset,EXTENT_BYTES));
}
static void inspect(const comp_segment_entry_t *e,uint64_t *encoded,unsigned *ends,uint64_t accepted)
{
    comp_segment_audio_port_t port=comp_wba_segment_storage_audio_port(&product_rec.storage);
    uint32_t bytes=0u;
    for(uint32_t page=0u;bytes<e->descriptor.encoded_length;++page) {
        uint8_t raw[256],n=0u;
        assert(comp_segment_audio_read_page(&port,e,DATA_BASE,page,raw,&n)==COMP_SEG_OK);
        assert(n&&bytes+n<=sizeof(original));memcpy(original+bytes,raw,n);bytes+=n;
    }
    assert(bytes==e->descriptor.encoded_length&&original[4]==5u&&original[7]==15u);
    companion_sha256_t h;uint8_t digest[32];companion_sha256_init(&h);
    companion_sha256_update(&h,original,bytes);companion_sha256_final(&h,digest);
    assert(!memcmp(digest,e->descriptor.sha256,32u)&&comp_rec_crc(original,bytes)==e->descriptor.content_crc32);
    assert(e->descriptor.sample_offset==*encoded);
    comp_rec_audio_profile_t profile;assert(comp_rec_audio_profile_decode(original+44u,bytes-44u,&profile));
    assert(profile.output==0u&&profile.filtered_mask==1u&&profile.firmware_version==0x000103ebu);
    uint64_t first=*encoded;unsigned configs=0u,profiles=0u;
    for(uint32_t at=12u;at<bytes;) {
        if(original[at]==255u){++at;continue;}
        if(original[at]==0u&&at+1u<bytes&&original[at+1u]==0u) {
            if(at+6u<=bytes&&!memcmp(original+at+2u,"APM1",4u)) {
                assert(at==44u&&++profiles==1u);at+=96u;
            } else if(at+32u<=bytes&&!memcmp(original+at+2u,"CPG1",4u)) {
                comp_rec_timeline_event_t event;
                assert(comp_rec_timeline_decode(original+at,bytes-at,&event));
                assert((event.kind==COMP_REC_TIMELINE_PAUSE&&event.sequence==1u)||
                       (event.kind==COMP_REC_TIMELINE_RESUME&&event.sequence==2u));
                at+=32u;
            } else {
                comp_rec_codec_boundary_t boundary;
                assert(comp_rec_codec_boundary_decode(original+at,bytes-at,&boundary));
                if(boundary.kind==COMP_REC_CODEC_CONFIG) {
                    assert(at==12u&&boundary.encoded_samples==first&&++configs==1u);
                } else {
                    assert(++*ends==1u&&boundary.valid_source_samples==accepted*160u);
                    assert(boundary.encoded_samples==*encoded+320u);
                }
                at+=32u;
            }
            continue;
        }
        assert(at+42u<=bytes&&original[at]==40u&&original[at+1u]==0u);
        *encoded+=320u;at+=42u;
    }
    assert(configs==1u&&profiles==1u&&*encoded-first==e->descriptor.sample_count);
}

static void one_success(unsigned resume_blocks) {
    setvbuf(stdout,NULL,_IONBF,0);
    reset();nor=make();f.automatic_erase=true;mic=false;mic_starts=mic_stops=reports=0u;
    nor.config.wait_progress=wait_progress;nor.config.transfer=status_transfer;
    comp_wba_pipeline_config_t cfg={0};cfg.microphone=microphone;cfg.now_ms=now;
    cfg.segment_frames=SEGMENT_FRAMES;cfg.extent_bytes=EXTENT_BYTES;cfg.audio_profile=snapshot;
    assert(comp_wba_recording_product_bind(&product_rec,&nor,0u,24576u,DATA_BASE,3u*EXTENT_BYTES,49152u,device_uid,7u,&cfg,product_report));
    product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    profile_start(0xabcdu,91u);for(unsigned i=0;i<8u;i++)block(i);
    assert(comp_wba_recording_pipeline_pause(&product_rec.pipeline,91u,1u));
    for(unsigned i=0;i<10000u&&product_rec.capture.engine.state!=COMP_CONT_PAUSED;i++)product_tick();
    assert(product_rec.capture.engine.state==COMP_CONT_PAUSED&&!mic);
    assert(comp_wba_recording_pipeline_resume(&product_rec.pipeline,91u,2u));
    assert(product_rec.capture.engine.state==COMP_CONT_RESUMING&&mic);
    int16_t data[160];pcm(9u,data);
    if(resume_blocks)assert(comp_wba_recording_product_pcm(&product_rec,data,160u,16000u));
    unsigned stops=mic_stops;
    assert(!comp_wba_recording_pipeline_stop(&product_rec.pipeline,92u));
    assert(mic&&mic_stops==stops);
    assert(comp_wba_recording_pipeline_stop(&product_rec.pipeline,91u));
    printf("after STOP accepted: microphone=%u stops_delta=%u state=%u accepted=%llu\n",mic,mic_stops-stops,product_rec.capture.engine.state,(unsigned long long)product_rec.capture.engine.stats.accepted_pcm_blocks);
    assert(!mic&&mic_stops==stops+1u);
    assert(!comp_wba_recording_product_pcm(&product_rec,data,160u,16000u));
    assert(comp_wba_recording_pipeline_stop(&product_rec.pipeline,91u));
    settle();assert(mic_stops==stops+1u);
    comp_segment_entry_t e=product_entry(0u);assert(e.state==COMP_SEG_UNSYNCED);
    uint64_t encoded=0u;unsigned ends=0u;inspect(&e,&encoded,&ends,8u+resume_blocks);assert(ends==1u);
    printf("ORIGINAL blocks=%u sha=",resume_blocks);for(unsigned i=0;i<32u;i++)printf("%02x",e.descriptor.sha256[i]);puts("");
    puts("PASS: stop during resume stops microphone immediately, drains exact accepted PCM once, seals same valid original; production C simulated NOR");
}
static void failing_stop(void) {
    reset();nor=make();f.automatic_erase=true;mic=false;mic_starts=mic_stops=reports=0u;fail_mic_stops=0u;
    nor.config.wait_progress=wait_progress;nor.config.transfer=status_transfer;
    comp_wba_pipeline_config_t cfg={0};cfg.microphone=microphone;cfg.now_ms=now;
    cfg.segment_frames=SEGMENT_FRAMES;cfg.extent_bytes=EXTENT_BYTES;cfg.audio_profile=snapshot;
    assert(comp_wba_recording_product_bind(&product_rec,&nor,0u,24576u,DATA_BASE,3u*EXTENT_BYTES,49152u,device_uid,7u,&cfg,product_report));
    product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    profile_start(0xabceu,91u);for(unsigned i=0;i<8u;i++)block(i);
    assert(comp_wba_recording_pipeline_pause(&product_rec.pipeline,91u,1u));
    for(unsigned i=0;i<10000u&&product_rec.capture.engine.state!=COMP_CONT_PAUSED;i++)product_tick();
    assert(comp_wba_recording_pipeline_resume(&product_rec.pipeline,91u,2u));
    fail_mic_stops=100u;
    assert(!comp_wba_recording_pipeline_stop(&product_rec.pipeline,91u));
    assert(mic&&product_rec.capture.engine.state==COMP_CONT_FAULT&&!product_rec.capture.engine.encoder_owned);
    product_tick();assert(product_rec.pipeline.state==COMP_PIPE_FAILED&&mic);
    unsigned writes=f.writes,erases=f.erases;
    for(unsigned i=0;i<300u;i++)product_tick();
    assert(mic&&product_rec.pipeline.state==COMP_PIPE_FAILED&&f.writes==writes&&f.erases==erases);
    puts("PASS resume stop failure: error retained, no false stop or writes while capture remains live");
}
int main(void) {one_success(0u);one_success(1u);failing_stop();return 0;}

