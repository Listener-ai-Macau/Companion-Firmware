#define COMP_PRODUCT_TEST_MAIN staging_fixture_main
#include "test_wba_recording_product.c"

static bool legacy_hint(const comp_cont_recording_t *r)
{
    return r&&(r->state==COMP_CONT_RUNNING||r->state==COMP_CONT_PAUSE_PENDING||r->state==COMP_CONT_PAUSING)&&r->ring_count&&
        r->codec.frame_samples==320u&&!r->codec.pcm_fill&&!r->writer.phase&&!r->roll_packet_bytes&&!r->bookmark_phase&&
        r->stage_length<=COMP_CONT_STAGE_BYTES-(COMPANION_OPUS16_MAX_PACKET+2u);
}
static void start_capture(uint32_t extent)
{
    product_fresh();product_rec.pipeline.config.extent_bytes=extent;
    product_mount();comp_wba_recording_product_lease_result(&product_rec,true);product_ready_capture(101u,91u);
}
static void at_full_boundary(void)
{
    start_capture(65536u); /* Exactly one extent; successor is genuinely FULL. */
    for(unsigned block=0u;block<40u;block++) {
        int16_t samples[160];pcm(block,samples);
        assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<2000u&&product_rec.capture.engine.ring_count;i++)product_tick();
        if(block<39u)for(unsigned i=0u;i<100u;i++)product_tick();
    }
    comp_cont_recording_t *r=&product_rec.capture.engine;
    assert(mic&&r->codec.frames_encoded==20u&&!r->codec.pcm_fill&&!r->ring_count&&!r->writer.phase);
    const comp_segment_entry_t *entry=NULL;comp_segment_audio_t *writer=NULL;
    assert(r->config.next(r->config.context,false,&entry,&writer)==COMP_SEG_FULL);
    int16_t samples[160];pcm(40u,samples);
    assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));assert(legacy_hint(r));
}
static void generic_poll_counterexample(void)
{
    at_full_boundary();comp_cont_recording_t *r=&product_rec.capture.engine;
    product_tick();
    assert(!mic&&r->state==COMP_CONT_STOPPING&&!r->codec.pcm_fill&&r->ring_count==1u);
    assert(product_rec.pipeline.state==COMP_PIPE_STOPPING);
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED);
    puts("PASS_OLD_HINT_COUNTEREXAMPLE true hint + generic poll actually stops full-pool MIC; does not stage PCM");
}
static void explicit_only_stages(void)
{
    at_full_boundary();comp_cont_recording_t *r=&product_rec.capture.engine;
    uint32_t frames=r->codec.frames_encoded,packets=r->stats.encoded_packets;
    unsigned reads=f.reads,writes=f.writes,starts=mic_starts,stops=mic_stops;uint8_t read=r->ring_read;
    int16_t expected[160];memcpy(expected,r->pcm[read],sizeof(expected));
    assert(comp_wba_recording_product_pcm_staging_pending(&product_rec));
    assert(comp_wba_recording_product_stage_pcm_half(&product_rec));
    assert(mic&&r->state==COMP_CONT_RUNNING&&r->codec.pcm_fill==160u&&!r->ring_count&&
        !memcmp(expected,r->codec.pcm_acc,sizeof(expected))&&r->codec.frames_encoded==frames&&
        r->stats.encoded_packets==packets&&f.reads==reads&&f.writes==writes&&mic_starts==starts&&mic_stops==stops);
    assert(!comp_wba_recording_product_stage_pcm_half(&product_rec));
    product_tick();assert(!mic&&r->state==COMP_CONT_STOPPING&&r->codec.pcm_fill==160u);
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED&&!r->stats.overflows&&!r->stats.budget_failures);
    puts("PASS_EXPLICIT_HALF_ONLY exact160 samples; no Opus packet/NOR/control; boundary stop retained in ordinary poll; no second-half fast path");
}
typedef struct {uint8_t sha[2][32];uint32_t bytes[2];uint64_t samples[2];uint32_t count;} stream_proof_t;
static stream_proof_t stream(bool separate)
{
    start_capture(4096u);
    for(unsigned block=0u;block<70u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        if(separate&&comp_wba_recording_product_pcm_staging_pending(&product_rec)) {
            uint32_t before=product_rec.capture.engine.codec.frames_encoded;
            assert(comp_wba_recording_product_stage_pcm_half(&product_rec));
            assert(product_rec.capture.engine.codec.frames_encoded==before);
        }
        for(unsigned i=0u;i<160u;i++)product_tick();
    }
    assert(comp_wba_recording_product_control(&product_rec,false,91u));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED&&!mic);product_refresh_space();
    stream_proof_t proof={0};proof.count=product_rec.space.used;assert(proof.count==2u);
    for(unsigned i=0u;i<proof.count;i++) {
        comp_segment_entry_t entry=product_entry(i);proof.bytes[i]=entry.descriptor.encoded_length;proof.samples[i]=entry.descriptor.sample_count;
        memcpy(proof.sha[i],entry.descriptor.sha256,32u);
    }
    assert(proof.samples[0]+proof.samples[1]==70u*160u);
    return proof;
}
static unsigned slow_calls;
static uint32_t slow_clock(void *context){(void)context;return slow_calls++?f.now+11u:f.now;}
static void budget_still_faults(void)
{
    start_capture(4096u);int16_t samples[160];pcm(0u,samples);
    assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
    comp_cont_recording_t *r=&product_rec.capture.engine;r->config.now_ms=slow_clock;slow_calls=0u;
    assert(!comp_wba_recording_product_stage_pcm_half(&product_rec)&&!mic&&r->state==COMP_CONT_FAULT&&
        r->stats.budget_failures==1u&&product_rec.pipeline.state==COMP_PIPE_FAILED&&
        product_rec.last_fault==COMP_WBA_RECORDING_FAULT_DEADLINE&&reported_audio==DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY);
    puts("PASS_STAGE_BUDGET injected11ms still stops/faults/reports original10ms protection; not physical timing");
}
int main(void)
{
    setvbuf(stdout,NULL,_IONBF,0);generic_poll_counterexample();explicit_only_stages();
    stream_proof_t normal=stream(false),separate=stream(true);
    assert(!memcmp(&normal,&separate,sizeof(normal)));
    puts("PASS_SAMPLE_FIFO_AND_HOST_OPUS_EQUIVALENCE same70 actual PCM blocks/two physical segments/sample counts/encoded lengths/fullSHA/STOP with separated staging");
    budget_still_faults();puts("EXPLICIT_STAGING_SOFTWARE_ONLY pinnedM33Opus/low-frequency/real-BLE/current NOT_QUALIFIED");return 0;
}
