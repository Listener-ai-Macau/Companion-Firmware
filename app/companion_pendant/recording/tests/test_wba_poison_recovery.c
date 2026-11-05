#include <stdlib.h>
#define COMP_PRODUCT_TEST_MAIN poison_fixture_main
#include "test_wba_recording_product.c"

static void stopped_read_fault(unsigned remount_failure)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    product_ready_capture(701u,101u);
    for(unsigned block=0u;block<14u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<160u;i++)product_tick();
    }
    assert(comp_wba_recording_product_control(&product_rec,false,101u));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED);
    comp_segment_entry_t old=product_entry(0u);
    uint8_t original[4096];memcpy(original,f.bytes+DATA_BASE+old.extent_offset,sizeof(original));
    product_ready_capture(702u,102u);
    for(unsigned i=0u;i<1000u&&product_rec.catalog.phase;i++)product_tick();
    assert(!product_rec.catalog.phase);
    assert(comp_wba_recording_pipeline_consume(&product_rec.pipeline,&old.descriptor)==COMP_SEG_PENDING);
    f.fail_command=3u;
    for(unsigned i=0u;i<1000u&&product_rec.pipeline.state!=COMP_PIPE_FAILED;i++)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FAILED&&!mic&&product_rec.storage.poisoned);
    assert(!product_rec.catalog.mounted);
    printf("fault=%u consume=%u phase=%u future=%u pending=%u catalog=%u\n",(unsigned)product_rec.pipeline.failure,
        (unsigned)comp_wba_recording_pipeline_consume_result(&product_rec.pipeline),(unsigned)product_rec.pipeline.consume_phase,
        (unsigned)product_rec.pipeline.future_phase,(unsigned)product_rec.catalog.phase,(unsigned)product_rec.catalog.mounted);
    assert(comp_wba_recording_pipeline_consume_result(&product_rec.pipeline)==COMP_SEG_PENDING);
    assert(!memcmp(original,f.bytes+DATA_BASE+old.extent_offset,sizeof(original)));
#if TEST_FIXED
    unsigned writes=f.writes,erases=f.erases,starts=mic_starts;
    product_tick();
    assert(comp_wba_recording_pipeline_consume_result(&product_rec.pipeline)==COMP_SEG_IO_ERROR);
    assert(!mic&&mic_starts==starts&&f.writes==writes&&f.erases==erases);
    assert(!memcmp(original,f.bytes+DATA_BASE+old.extent_offset,sizeof(original)));
    uint8_t receipt[84];assert(!comp_wba_recording_pipeline_receipt(&product_rec.pipeline,receipt));
    f.sr1=1u;assert(!comp_wba_recording_product_recover_begin(&product_rec));f.sr1=0u;
    f.sr2=128u;assert(!comp_wba_recording_product_recover_begin(&product_rec));f.sr2=0u;
    nor.erase_active=true;assert(!comp_wba_recording_product_recover_begin(&product_rec));nor.erase_active=false;
    assert(product_rec.storage.poisoned&&!product_rec.catalog.mounted);
    if(remount_failure==2u) {
        /* Simulate loss of both roots, independently of the retained audio.
         * Runtime mount may report blank, but must never format it. */
        memset(f.bytes,255u,49152u);
    }
    assert(comp_wba_recording_product_recover_begin(&product_rec));
    assert(comp_wba_recording_product_recovering(&product_rec)&&!product_rec.ready&&!product_rec.media_ready);
    assert(!comp_wba_recording_product_recover_begin(&product_rec));
    if(remount_failure) {
        if(remount_failure==1u){f.fail_command=3u;product_tick();}
        else for(unsigned i=0u;i<30000u&&comp_wba_recording_product_recovering(&product_rec);i++)product_tick();
        assert(!product_rec.ready&&!product_rec.media_ready&&!product_rec.catalog.mounted&&
            comp_wba_recording_product_state(&product_rec)==COMP_WBA_RECORDING_FAULT);
        assert(f.writes==writes&&f.erases==erases&&!memcmp(original,f.bytes+DATA_BASE+old.extent_offset,sizeof(original)));
        puts("FIXED: failed remount stays closed, never formats or changes old audio");return;
    }
    for(unsigned i=0u;i<30000u&&comp_wba_recording_product_recovering(&product_rec);i++)product_tick();
    assert(product_rec.ready&&product_rec.media_ready&&product_rec.pipeline.state==COMP_PIPE_IDLE&&!mic);
    assert(mic_starts==starts&&!memcmp(original,f.bytes+DATA_BASE+old.extent_offset,sizeof(original)));
    comp_segment_entry_t restored=product_entry(0u);
    assert(restored.descriptor.recording_id==old.descriptor.recording_id&&
        !memcmp(restored.descriptor.sha256,old.descriptor.sha256,32u));
    assert(!comp_wba_recording_pipeline_receipt(&product_rec.pipeline,receipt));
    puts("FIXED: poison returns error, busy/suspended/owned preflight refuses, remount recovers old exact audio without auto-start or fake receipt");
#else
    (void)remount_failure;
    product_tick();assert(comp_wba_recording_pipeline_consume_result(&product_rec.pipeline)==COMP_SEG_PENDING);
    assert(!comp_wba_recording_product_recover_begin(&product_rec));
    puts("BASELINE: read I/O fault stops capture and retains old bytes, but explicit online recovery refuses poisoned/unmounted catalogue");
#endif
}
#if TEST_FIXED
static void pending_catalog_owner(void)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    product_ready_capture(801u,111u);
    for(unsigned block=0u;block<14u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<160u;i++)product_tick();
    }
    assert(comp_wba_recording_product_control(&product_rec,false,111u));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED);
    comp_segment_entry_t old=product_entry(0u);product_ready_capture(802u,112u);
    assert(comp_wba_recording_pipeline_consume(&product_rec.pipeline,&old.descriptor)==COMP_SEG_PENDING);
    for(unsigned i=0u;i<2000u&&!(product_rec.catalog.phase&&product_rec.catalog.pending==&product_rec.pipeline.consume);i++)product_tick();
    assert(product_rec.catalog.phase&&product_rec.catalog.pending==&product_rec.pipeline.consume);
    comp_segment_entry_t owner=product_rec.pipeline.consume;
    uint8_t before[4096];memcpy(before,f.bytes+DATA_BASE+old.extent_offset,sizeof(before));
    product_rec.storage.poisoned=true;
    comp_wba_recording_product_fault(&product_rec,COMP_WBA_RECORDING_FAULT_STORAGE_IO);
    unsigned writes=f.writes,erases=f.erases;uint8_t phase=product_rec.catalog.phase;
    product_tick();
    assert(comp_wba_recording_pipeline_consume_result(&product_rec.pipeline)==COMP_SEG_IO_ERROR);
    assert(product_rec.catalog.phase==phase&&product_rec.catalog.pending==&product_rec.pipeline.consume);
    assert(!memcmp(&owner,&product_rec.pipeline.consume,sizeof(owner)));
    assert(writes==f.writes&&erases==f.erases&&!memcmp(before,f.bytes+DATA_BASE+old.extent_offset,sizeof(before)));
    uint8_t receipt[84];assert(!comp_wba_recording_pipeline_receipt(&product_rec.pipeline,receipt));
    assert(comp_wba_recording_product_recover_begin(&product_rec));
    for(unsigned i=0u;i<30000u&&comp_wba_recording_product_recovering(&product_rec);i++)product_tick();
    assert(product_rec.ready&&!mic&&!memcmp(before,f.bytes+DATA_BASE+old.extent_offset,sizeof(before)));
    comp_segment_entry_t restored=product_entry(0u);
    assert(restored.descriptor.recording_id==old.descriptor.recording_id&&
        !memcmp(restored.descriptor.sha256,old.descriptor.sha256,32u));
    puts("FIXED: poison while consume owns catalogue retains exact owner until remount; unconfirmed audio survives");
}
static void radio_failure_reply(void)
{
    comp_segment_entry_t original=setup_radio();
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    ready(56u);assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    uint8_t proof[84];consumption_proof(&original,proof);last_reply_bytes=0u;
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,proof,sizeof(proof));assert(radio.consume_pending);
    storage.poisoned=true;comp_cont_recording_fault(&engine,COMP_SEG_IO_ERROR);
    (void)comp_wba_recording_pipeline_poll(&pipeline);assert(pipeline.state==COMP_PIPE_FAILED);
    (void)comp_wba_recording_pipeline_poll(&pipeline);
    radio_tick();radio_tick();
    assert(!radio.consume_pending&&last_reply_bytes==16u&&!memcmp(last_reply,"CAE2",4u));
    assert(comp_rec_get32(last_reply+8u)==original.descriptor.recording_id&&
           comp_rec_get32(last_reply+12u)==COMP_SEG_IO_ERROR&&receipt_count==0u);
    puts("FIXED: authenticated radio receives correlated CAE2 failure, releases pending request and never emits successful receipt");
}
static void offline_failed_request(void)
{
    comp_segment_entry_t original=setup_radio();
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    ready(56u);assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    uint8_t proof[84];consumption_proof(&original,proof);
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,proof,sizeof(proof));assert(radio.consume_pending);
    comp_link_connection(&link_owner.link,false,false,f.now);
    storage.poisoned=true;comp_cont_recording_fault(&engine,COMP_SEG_IO_ERROR);
    (void)comp_wba_recording_pipeline_poll(&pipeline);(void)comp_wba_recording_pipeline_poll(&pipeline);
    assert(comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_IO_ERROR);
    radio_tick();radio_tick();
    assert(!radio.consume_pending&&!comp_wba_recording_radio_busy(&radio));
    assert(receipt_count==0u);
    puts("FIXED: disconnected failed request releases radio without false receipt; exact proof remains in pipeline");
}
static void boot_read_retry(void)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    product_ready_capture(901u,121u);
    for(unsigned block=0u;block<14u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<160u;i++)product_tick();
    }
    assert(comp_wba_recording_product_control(&product_rec,false,121u));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED);
    comp_segment_entry_t old=product_entry(0u);uint8_t original[4096];
    memcpy(original,f.bytes+DATA_BASE+old.extent_offset,sizeof(original));
    product_bind();f.fail_command=3u;product_tick();
    assert(comp_wba_recording_product_state(&product_rec)==COMP_WBA_RECORDING_FAULT&&comp_wba_recording_product_boot_retry_pending(&product_rec));
    f.sr1=1u;assert(!comp_wba_recording_product_boot_retry(&product_rec,f.now));f.sr1=0u;
    assert(comp_wba_recording_product_boot_retry_pending(&product_rec)&&!comp_wba_recording_product_boot_retry(&product_rec,f.now+999u));
    assert(comp_wba_recording_product_boot_retry(&product_rec,f.now+1000u));
    assert(comp_wba_recording_product_recovering(&product_rec));
    for(unsigned i=0u;i<30000u&&!comp_wba_recording_product_space_current(&product_rec);i++)product_tick();
    assert(product_rec.media_ready&&!product_rec.ready&&comp_wba_recording_product_recovering(&product_rec));
    assert(!memcmp(original,f.bytes+DATA_BASE+old.extent_offset,sizeof(original)));
    comp_wba_recording_product_lease_result(&product_rec,true);
    assert(product_rec.ready&&!comp_wba_recording_product_recovering(&product_rec)&&!mic);
    comp_segment_entry_t restored=product_entry(0u);
    assert(restored.descriptor.recording_id==old.descriptor.recording_id&&
        !memcmp(restored.descriptor.sha256,old.descriptor.sha256,32u));
    puts("PASS boot initial read fault: two bounded preflight attempts, exact media remount and original retained; WUS2 lease required");
}
static void boot_retry_closed(void)
{
    product_fresh();f.fail_command=3u;product_tick();assert(comp_wba_recording_product_boot_retry_pending(&product_rec));
    f.fail_command=0x9Fu;assert(!comp_wba_recording_product_boot_retry(&product_rec,f.now));
    assert(!comp_wba_recording_product_boot_retry(&product_rec,f.now+999u));
    f.fail_command=0x9Fu;assert(!comp_wba_recording_product_boot_retry(&product_rec,f.now+1000u));
    unsigned writes=f.writes,erases=f.erases;assert(!comp_wba_recording_product_boot_retry(&product_rec,f.now+100000u));
    assert(!comp_wba_recording_product_boot_retry_pending(&product_rec)&&f.writes==writes&&f.erases==erases);
    assert(!comp_wba_recording_product_retry_idle_explicit(&product_rec,f.now+100001u));
    product_fresh();f.fail_command=3u;product_tick();assert(comp_wba_recording_product_boot_retry_pending(&product_rec));
    assert(comp_wba_recording_product_boot_retry(&product_rec,f.now));
    for(unsigned i=0u;i<30000u&&comp_wba_recording_product_recovering(&product_rec);i++)product_tick();
    assert(comp_wba_recording_product_state(&product_rec)==COMP_WBA_RECORDING_FAULT&&!comp_wba_recording_product_boot_retry_pending(&product_rec));
    assert(f.writes==0u&&f.erases==0u&&!product_rec.ready&&!mic);
    assert(!comp_wba_recording_product_retry_idle_explicit(&product_rec,f.now));
    product_fresh();
    for(unsigned i=0u;i<30000u&&!product_rec.catalog.blank_verified;i++)product_tick();
    assert(product_rec.catalog.blank_verified&&!product_rec.ready);
    f.fail_command=3u;product_tick();
    assert(comp_wba_recording_product_state(&product_rec)==COMP_WBA_RECORDING_FAULT&&!comp_wba_recording_product_boot_retry_pending(&product_rec));
    assert(!comp_wba_recording_product_boot_retry(&product_rec,f.now)&&f.writes==0u&&f.erases==0u);
    product_fresh();f.fail_command=3u;product_tick();assert(comp_wba_recording_product_boot_retry_pending(&product_rec));
    f.fail_command=0x9Fu;assert(!comp_wba_recording_product_boot_retry(&product_rec,0xFFFFFF00u));
    assert(!comp_wba_recording_product_boot_retry(&product_rec,0x000002E7u));
    f.fail_command=0x9Fu;assert(!comp_wba_recording_product_boot_retry(&product_rec,0x000002E8u));
    assert(!comp_wba_recording_product_boot_retry_pending(&product_rec));
    puts("PASS boot retries are bounded; unknown blank media after failed mount never formatted");
}
#endif
int main(void)
{
    setvbuf(stdout,NULL,_IONBF,0);
#ifdef _WIN32
    _set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);
#endif
    stopped_read_fault(0u);
#if TEST_FIXED
    stopped_read_fault(1u);stopped_read_fault(2u);
    pending_catalog_owner();
    radio_failure_reply();
    offline_failed_request();
    boot_read_retry();boot_retry_closed();
#endif
    return 0;
}
