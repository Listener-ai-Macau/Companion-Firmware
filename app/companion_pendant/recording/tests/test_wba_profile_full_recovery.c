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
#ifndef COMP_PROFILE_FULL_NO_MAIN
int main(void)
{
    setvbuf(stdout,NULL,_IONBF,0);
#ifdef _WIN32
    _set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);
#endif
    reset();nor=make();f.automatic_erase=true;mic=false;mic_starts=mic_stops=reports=0u;
    nor.config.wait_progress=wait_progress;nor.config.transfer=status_transfer;
    comp_wba_pipeline_config_t cfg={0};cfg.microphone=microphone;cfg.now_ms=now;
    cfg.segment_frames=SEGMENT_FRAMES;cfg.extent_bytes=EXTENT_BYTES;cfg.audio_profile=snapshot;
    assert(comp_wba_recording_product_bind(&product_rec,&nor,0u,24576u,DATA_BASE,3u*EXTENT_BYTES,
        49152u,device_uid,7u,&cfg,product_report));
    product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    profile_start(801u,91u);for(unsigned i=0u;i<8u;++i)block(i);
    assert(comp_wba_recording_product_control(&product_rec,false,91u));settle();
    comp_segment_entry_t retained=product_entry(0u);
    assert(retained.state==COMP_SEG_UNSYNCED&&product_rec.space.reserved_bytes==EXTENT_BYTES);
    memcpy(retained_extent,f.bytes+DATA_BASE+retained.extent_offset,EXTENT_BYTES);
    if(getenv("COMP_MODEL_ONLY_GATE")) {
    /* This original occupies the front of the dynamic arena; the OTA tail is
     * physically disjoint but the product contract still requires its durable
     * upload/consume before a new download starts. */
    assert(retained.descriptor.source_mode==COMP_WBA_RECORDING_SOURCE_MIC_SAI);
    assert(product_rec.space.highest_end<=product_rec.catalog.data_bytes-4096u);
    uint32_t physical=123u;bool granted=comp_wba_recording_product_update_workspace(&product_rec,4096u,&physical);
    printf("PENDING_MIC_OTA_GATE granted=%u protected_mic=%u physical=%u\n",(unsigned)granted,product_rec.space.unsynced,physical);
    assert(!granted && physical==0u);unchanged_retained(&retained);
    /* The dual-microphone diagnostic uses the common temporary workspace,
     * not the OTA entry point. A disjoint lease must remain available while
     * the protected microphone original stays byte-for-byte unchanged. */
    assert(comp_wba_recording_product_workspace(&product_rec,4096u,&physical));
    assert(comp_wba_recording_product_workspace(&product_rec,0u,&physical));
    product_refresh_space();unchanged_retained(&retained);
    /* BOOT_LEASE continues an already durable pre-existing update rather than
     * starting a new download; preserve its exact replay and release. */
    uint8_t boot_phase=product_rec.boot_phase;product_rec.boot_phase=6u;
    assert(comp_wba_recording_product_update_workspace(&product_rec,4096u,&physical));
    assert(comp_wba_recording_product_update_workspace(&product_rec,0u,&physical));product_rec.boot_phase=boot_phase;
    product_refresh_space();unchanged_retained(&retained);
    consume(&retained);physical=123u;
    assert(comp_wba_recording_product_update_workspace(&product_rec,4096u,&physical));
    assert(comp_wba_recording_product_update_workspace(&product_rec,0u,&physical));product_refresh_space();
    profile_start_mode(803u,93u,2u);for(unsigned i=0u;i<8u;i++)block(i);
    assert(comp_wba_recording_product_control(&product_rec,false,93u));settle();
    comp_segment_entry_t diagnostic=product_entry(0u);assert(diagnostic.descriptor.source_mode==2u);
    physical=0u;assert(comp_wba_recording_product_update_workspace(&product_rec,4096u,&physical));
    assert(comp_wba_recording_product_update_workspace(&product_rec,0u,&physical));product_refresh_space();
    printf("PASS microphone drain gate, existing boot lease replay, consumed original and diagnostic-only retention; software only\n");
    return 0;
    }

    profile_start(802u,92u);unsigned accepted=0u;
    while(mic&&accepted<4u*SEGMENT_FRAMES+32u)block(accepted++);
    assert(!mic);settle();
    const comp_cont_recording_t *r=&product_rec.capture.engine;
    assert(r->stop_reason==COMP_CONT_STOP_FULL&&r->stats.storage_full_stops==1u);
    assert(r->stats.accepted_pcm_blocks==accepted&&!r->stats.overflows&&!r->stats.budget_failures);
    assert(mic_starts==2u&&mic_stops==2u&&reported_audio==DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY);
    assert(product_rec.space.used==3u&&product_rec.space.unsynced==3u&&!product_rec.space.largest_gap);
    unchanged_retained(&retained);
    filled[0]=product_entry(1u);filled[1]=product_entry(2u);
    uint64_t encoded=0u;unsigned ends=0u;
    for(unsigned i=0u;i<2u;++i) {
        assert(filled[i].descriptor.session_id==802u&&filled[i].descriptor.segment_index==i);
        inspect(&filled[i],&encoded,&ends,accepted);
    }
    assert(ends==1u&&encoded==(uint64_t)accepted*160u+320u);
    assert(!(filled[0].descriptor.flags&COMP_REC_V2_LAST));
    assert((filled[1].descriptor.flags&COMP_REC_V2_LAST)&&filled[1].descriptor.total_segments==2u);
    assert(((filled[1].descriptor.flags>>COMP_REC_V2_END_SHIFT)&7u)==COMP_REC_END_FULL);
    consume(&filled[0]);consume(&filled[1]);
    assert(product_rec.space.used==1u&&product_rec.space.unsynced==1u&&product_rec.space.largest_gap==2u*EXTENT_BYTES);
    unchanged_retained(&retained);
    unsigned starts=mic_starts;for(unsigned i=0u;i<100u;++i)product_tick();assert(mic_starts==starts&&!mic);
    profile_start(803u,93u);block(0u);block(1u);
    assert(comp_wba_recording_product_control(&product_rec,false,93u));settle();
    assert(mic_starts==3u&&mic_stops==3u);unchanged_retained(&retained);
    printf("PASS schema5 full-pool auto-stop: accepted=%u, exact source boundary/drain, both segment CRC/SHA, END_FULL, old original unchanged, consume then explicit new START; software only\n",accepted);
    return 0;
}
#endif
