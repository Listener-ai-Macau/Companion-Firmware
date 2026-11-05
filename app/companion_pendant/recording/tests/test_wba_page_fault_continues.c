#define COMP_PRODUCT_TEST_MAIN continue_fixture_main
#include "test_wba_recording_product.c"

int main(int argc,char **argv)
{
    const bool inject=!(argc==2&&!strcmp(argv[1],"--normal"));
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
    uint32_t bytes=capture_engine->writer.committed_bytes;
    unsigned writes=f.writes,erases=f.erases;
    if(argc==2&&(!strcmp(argv[1],"--repeat")||!strcmp(argv[1],"--header")||
                 !strcmp(argv[1],"--release")||!strcmp(argv[1],"--slow")||
                 !strcmp(argv[1],"--other")||!strcmp(argv[1],"--corrupt"))) {
        const bool repeat=!strcmp(argv[1],"--repeat");
        if(repeat)for(unsigned retry_index=0u;retry_index<2u;retry_index++) {
            f.fail_read_data_once=true;product_tick();
            assert(!f.fail_read_data_once&&mic&&!product_rec.storage.poisoned&&
                   capture_engine->writer.phase==6u&&capture_engine->writer.committed_bytes==bytes&&
                   f.writes==writes&&f.erases==erases);
        }
        if(!strcmp(argv[1],"--corrupt")) {
            uint32_t at=DATA_BASE+capture_engine->active.extent_offset+256u+capture_engine->writer.pages*256u;
            assert(at<sizeof(f.bytes));f.bytes[at]^=1u;
        } else if(repeat||!strcmp(argv[1],"--slow")||!strcmp(argv[1],"--other")) {
            if(!strcmp(argv[1],"--other"))nor.info.jedec_id=0x0b6018u;
            f.fail_read_data_once=true;f.fail_read_delay_ms=!strcmp(argv[1],"--slow")?8u:0u;
        } else if(!strcmp(argv[1],"--header"))f.fail_command=3u;
        else f.fail_deassert_once=true;
        product_tick();
        assert(product_rec.pipeline.state==COMP_PIPE_FAILED&&!mic&&
               capture_engine->writer.committed_bytes==bytes&&f.writes==writes&&f.erases==erases&&
               !memcmp(previous,f.bytes+DATA_BASE+old.extent_offset,sizeof(previous)));
        if(!repeat&&strcmp(argv[1],"--corrupt"))assert(product_rec.storage.poisoned);
        puts("PASS retry limit or uncertain/slow read remains a recording fault; software only");
        return 0;
    }
    if(inject) {
        f.fail_read_data_once=true;f.fail_read_delay_ms=0u;product_tick();
        assert(!f.fail_read_data_once&&mic&&!product_rec.storage.poisoned&&
               product_rec.pipeline.state==COMP_PIPE_RECORDING&&capture_engine->writer.committed_bytes==bytes&&
               capture_engine->writer.phase==6u&&f.writes==writes&&f.erases==erases);
    }
    for(unsigned i=0u;i<2000u&&capture_engine->writer.phase==6u;i++)product_tick();
    assert(capture_engine->writer.phase!=6u&&mic&&!product_rec.storage.poisoned);
    /* A later commit verification is a distinct read: a successful body
     * verification resets this writer's retry budget. */
    for(unsigned i=0u;i<2000u&&capture_engine->writer.phase!=8u;i++)product_tick();
    assert(capture_engine->writer.phase==8u&&mic);
    if(inject) {
        f.fail_read_data_once=true;product_tick();
        assert(!f.fail_read_data_once&&mic&&!product_rec.storage.poisoned&&
               capture_engine->writer.phase==8u&&capture_engine->writer.committed_bytes==bytes);
    }
    for(unsigned i=0u;i<2000u&&capture_engine->writer.phase==8u;i++)product_tick();
    assert(capture_engine->writer.phase!=8u&&mic);
    for(unsigned block=0u;block<12u;block++) {
        int16_t samples[160];pcm(block+80u,samples);assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<160u;i++)product_tick();
    }
    assert(comp_wba_recording_product_control(&product_rec,false,102u));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED&&!mic&&
           !memcmp(previous,f.bytes+DATA_BASE+old.extent_offset,sizeof(previous)));
    for(uint8_t i=0u;i<64u;i++) {
        comp_segment_entry_t got;comp_segment_result_t r=comp_wba_segment_storage_entry(&product_rec.storage,&product_rec.catalog,i,&got);
        assert(r==COMP_SEG_OK||r==COMP_SEG_NOT_FOUND);if(r!=COMP_SEG_OK||got.descriptor.session_id!=702u)continue;
        printf("ORIGINAL segment=%lu bytes=%lu samples=%llu sha=",(unsigned long)got.descriptor.segment_index,
            (unsigned long)got.descriptor.encoded_length,(unsigned long long)got.descriptor.sample_count);
        for(unsigned k=0u;k<32u;k++)printf("%02x",got.descriptor.sha256[k]);puts("");
    }
    puts("PASS fast released page-read failure yields and recording continues; software only");
    return 0;
}
