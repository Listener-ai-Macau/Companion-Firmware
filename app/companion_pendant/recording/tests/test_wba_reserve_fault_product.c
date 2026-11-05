#define COMP_PRODUCT_TEST_MAIN reserve_product_fixture_main
#include "test_wba_recording_product.c"
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
    product_ready_capture(702u,102u);
    bool injected=false;
    for(unsigned block=0u;block<130u;block++) {
        int16_t samples[160];pcm(block+80u,samples);assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<160u;i++) {
            comp_segment_reserve_t *reserve=&product_rec.pipeline.reserve;
            if(!injected&&reserve->phase==7u&&reserve->cursor==0u) {
                uint32_t cursor=reserve->cursor;f.fail_read_delay_ms=0u;f.fail_read_data_once=true;
                for(unsigned k=0u;k<100u&&f.fail_read_data_once;k++)product_tick();
                assert(!f.fail_read_data_once&&mic&&!product_rec.storage.poisoned&&reserve->cursor==cursor&&reserve->read_retries==1u);
                injected=true;
            }
            product_tick();
        }
    }
    assert(injected&&mic&&product_rec.pipeline.state==COMP_PIPE_RECORDING);
    assert(comp_wba_recording_product_control(&product_rec,false,102u));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED&&!mic&&
        !memcmp(previous,f.bytes+DATA_BASE+old.extent_offset,sizeof(previous)));
    puts("PASS product recording continues through next-extent transient read and preserves earlier recording; software only");
    return 0;
}
