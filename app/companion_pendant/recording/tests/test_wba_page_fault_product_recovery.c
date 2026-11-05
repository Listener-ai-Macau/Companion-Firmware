#define COMP_PRODUCT_TEST_MAIN recovery_fixture_main
#include "test_wba_recording_product.c"

/* Same production recorder, storage and real Opus; NOR and clock are modeled.
 * A separate process owns this faulted fixture, not a real device. */
int main(void)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    product_ready_capture(701u,101u);
    for(unsigned block=0u;block<14u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<160u;i++)product_tick();
    }
    assert(comp_wba_recording_product_control(&product_rec,false,101u));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED&&!mic);
    comp_segment_entry_t old=product_entry(0u);uint8_t previous[4096];
    assert(old.reserved_bytes==sizeof(previous));memcpy(previous,f.bytes+DATA_BASE+old.extent_offset,sizeof(previous));
    product_ready_capture(702u,102u);comp_cont_recording_t *capture_engine=&product_rec.capture.engine;
    for(unsigned block=0u;block<80u&&!(capture_engine->writer.phase==6u&&capture_engine->writer.committed_bytes>=248u);block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<160u&&!(capture_engine->writer.phase==6u&&capture_engine->writer.committed_bytes>=248u);i++)product_tick();
    }
    assert(capture_engine->writer.phase==6u&&capture_engine->writer.committed_bytes>=248u&&mic);
    const uint32_t recording_id=capture_engine->active.descriptor.recording_id,offset=capture_engine->active.extent_offset;
    uint8_t prefix[256];memcpy(prefix,f.bytes+DATA_BASE+offset+256u,sizeof(prefix));
    f.fail_read_delay_ms=8u;f.fail_read_data_once=true;
    for(unsigned i=0u;i<100u&&product_rec.pipeline.state!=COMP_PIPE_FAILED;i++)product_tick();
    assert(!f.fail_read_data_once&&product_rec.pipeline.state==COMP_PIPE_FAILED&&product_rec.storage.poisoned);
    for(unsigned i=0u;i<100u&&(mic||capture_engine->encoder_owned);i++)product_tick();
    assert(!mic&&!capture_engine->encoder_owned);
    const unsigned starts=mic_starts;
    assert(comp_wba_recording_product_recover_begin(&product_rec));
    for(unsigned i=0u;i<30000u&&comp_wba_recording_product_recovering(&product_rec);i++)product_tick();
    assert(product_rec.ready&&product_rec.media_ready&&!mic&&mic_starts==starts);
    assert(!memcmp(previous,f.bytes+DATA_BASE+old.extent_offset,sizeof(previous))&&
           !memcmp(prefix,f.bytes+DATA_BASE+offset+256u,sizeof(prefix)));
    bool found_old=false,found_new=false;
    for(uint8_t i=0u;i<64u;i++) {
        comp_segment_entry_t got;comp_segment_result_t r=comp_wba_segment_storage_entry(&product_rec.storage,&product_rec.catalog,i,&got);
        assert(r==COMP_SEG_OK||r==COMP_SEG_NOT_FOUND);if(r!=COMP_SEG_OK)continue;
        if(got.descriptor.recording_id==old.descriptor.recording_id) {
            assert(!memcmp(got.descriptor.sha256,old.descriptor.sha256,32u));found_old=true;
        }
        if(got.descriptor.recording_id==recording_id) {
            assert(got.descriptor.session_id==702u&&got.descriptor.encoded_length>0u&&
                   (got.descriptor.flags&COMP_REC_V2_RECOVERED));found_new=true;
        }
    }
    assert(found_old&&found_new);
    product_ready_capture(703u,103u);
    assert(comp_wba_recording_product_control(&product_rec,false,103u));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED&&!mic);
    puts("PASS page-verify failure: original prefix and earlier recording survive runtime recovery, next capture works; software only");
    return 0;
}
