#define COMP_PRODUCT_TEST_MAIN settlement_product_fixture_main
#include "test_wba_recording_product.c"
static void assert_no_live(void)
{assert(!mic&&product_rec.pipeline.state==COMP_PIPE_FAILED&&product_rec.capture.engine.state==COMP_CONT_FAULT&&
    !product_rec.capture.engine.encoder_owned&&product_rec.last_fault==COMP_WBA_RECORDING_FAULT_DEADLINE);}
static void wait_recovery(void)
{
    assert(comp_wba_recording_product_recover_begin(&product_rec));
    for(unsigned i=0u;i<30000u&&!comp_wba_recording_product_capture_available(&product_rec);i++)product_tick();
    /* An uncertain old tail remains diagnosed and owned. The product's
     * public capture gate, rather than fully healthy OTA readiness, decides
     * whether the user can record into a separate verified free extent. */
    assert(comp_wba_recording_product_capture_available(&product_rec)&&
           product_rec.pipeline.state==COMP_PIPE_IDLE&&!mic);
}
static void producer_commit(void)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    product_ready_capture(601u,91u);
    for(unsigned i=0u;i<3000u&&!product_rec.catalog.phase;i++)product_tick();
    assert(product_rec.catalog.phase&&product_rec.catalog.pending==&product_rec.pipeline.future);
    unsigned starts=mic_starts;comp_wba_recording_product_fault(&product_rec,COMP_WBA_RECORDING_FAULT_DEADLINE);assert_no_live();
    unsigned writes=f.writes,reads=f.reads;
    product_rec.capture.engine.encoder_owned=true;product_tick();assert(f.writes==writes&&f.reads==reads);product_rec.capture.engine.encoder_owned=false;
    /* Keep the simulated HAL and engine in the same live state. A failed
     * stop must preserve the live-mic exclusion even when the fault poll
     * performs its existing bounded stop retry. */
    product_rec.capture.engine.microphone_active=true;mic=true;fail_mic_stops=1u;
    product_tick();assert(f.writes==writes&&f.reads==reads&&mic);
    product_rec.capture.engine.microphone_active=false;mic=false;
    const comp_segment_entry_t *owner=product_rec.catalog.pending;comp_segment_entry_t stranger={0};
    product_rec.catalog.pending=&stranger;product_tick();assert(f.writes==writes&&f.reads==reads);product_rec.catalog.pending=owner;
    for(unsigned i=0u;i<500u&&product_rec.catalog.phase;i++)product_tick();
    assert(!product_rec.catalog.phase);assert_no_live();assert(mic_starts==starts);
    wait_recovery();assert(mic_starts==starts);
    puts("PASS_FAULT_SETTLE_PRODUCER owned metadata commit finishes; active encoder/mic/unknown owner refused; no restart; ordinary bounded recovery usable");
}
static void consumer_commit(void)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    product_ready_capture(701u,101u);
    for(unsigned block=0u;block<14u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<160u;i++)product_tick();
    }
    assert(comp_wba_recording_product_control(&product_rec,false,101u));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED);comp_segment_entry_t old=product_entry(0u);
    product_ready_capture(702u,102u);
    comp_segment_entry_t current=product_rec.capture.engine.active;
    uint8_t before[4096];memcpy(before,f.bytes+DATA_BASE+current.extent_offset,sizeof(before));
    assert(comp_wba_recording_pipeline_consume(&product_rec.pipeline,&old.descriptor)==COMP_SEG_PENDING);
    for(unsigned i=0u;i<2000u&&!(product_rec.catalog.phase&&product_rec.catalog.pending==&product_rec.pipeline.consume);i++)product_tick();
    assert(product_rec.catalog.phase&&product_rec.catalog.pending==&product_rec.pipeline.consume);
    unsigned starts=mic_starts;comp_wba_recording_product_fault(&product_rec,COMP_WBA_RECORDING_FAULT_DEADLINE);
    for(unsigned i=0u;i<10000u&&comp_wba_recording_pipeline_consume_result(&product_rec.pipeline)==COMP_SEG_PENDING;i++)product_tick();
    assert(comp_wba_recording_pipeline_consume_result(&product_rec.pipeline)==COMP_SEG_OK&&!product_rec.catalog.phase);
    assert_no_live();assert(mic_starts==starts&&!memcmp(before,f.bytes+DATA_BASE+current.extent_offset,sizeof(before)));
    uint8_t ack[84];assert(comp_wba_recording_pipeline_receipt(&product_rec.pipeline,ack));
    assert(comp_rec_get32(ack+40u)==old.descriptor.recording_id&&!memcmp(ack+48u,old.descriptor.sha256,32u));
    wait_recovery();assert(mic_starts==starts);
    puts("PASS_FAULT_SETTLE_CONSUMER only prior exact-proof consume commits/reclaims; receipt kept, new unconfirmed extent untouched; no auto-capture");
}
static void sealing_commit(void)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);product_ready_capture(801u,111u);
    for(unsigned block=0u;block<14u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<160u;i++)product_tick();
    }
    assert(comp_wba_recording_product_control(&product_rec,false,111u));
    for(unsigned i=0u;i<20000u&&!(product_rec.pipeline.sealing&&product_rec.catalog.phase);i++)product_tick();
    assert(product_rec.pipeline.sealing&&product_rec.catalog.phase&&product_rec.catalog.pending==product_rec.pipeline.sealing);
    comp_segment_entry_t old=*product_rec.pipeline.sealing;unsigned starts=mic_starts,erases=f.erases;
    uint8_t before[4096];memcpy(before,f.bytes+DATA_BASE+old.extent_offset,sizeof(before));
    comp_wba_recording_product_fault(&product_rec,COMP_WBA_RECORDING_FAULT_DEADLINE);
    for(unsigned i=0u;i<500u&&product_rec.catalog.phase;i++)product_tick();
    assert_no_live();assert(!product_rec.catalog.phase&&!product_rec.pipeline.sealing&&!product_rec.pipeline.seal_started);
    assert(f.erases==erases&&!memcmp(before,f.bytes+DATA_BASE+old.extent_offset,sizeof(before)));
    wait_recovery();assert(mic_starts==starts);comp_segment_entry_t retained=product_entry(0u);
    assert(retained.descriptor.recording_id==old.descriptor.recording_id&&
        !memcmp(retained.descriptor.sha256,old.descriptor.sha256,32u));
    puts("PASS_FAULT_SETTLE_SEAL previously accepted exact metadata seal completes, audio SHA/extent retained, fault not promoted to normal finish, recovery unblocked");
}

static void future_erase_fault(bool suspended,bool half)
{
    product_fresh();
    if(half) {
        f.sfdp[80]=15u;f.sfdp[81]=0x52u;
        assert(companion_spi_nor_stm32wba_probe_erase_suspend(&nor)==COMPANION_SPI_NOR_STM32WBA_OK);
        assert(nor.info.erase_32k_supported);
    }
    product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    const uint32_t extent=half?32768u:8192u;
    product_rec.pipeline.config.extent_bytes=extent;
    product_ready_capture(901u,121u);f.automatic_erase=false;
    /* A blank free extent legitimately needs no erase. Model the dirty,
     * reusable next extent so this case reaches a real in-flight erase. */
    memset(f.bytes+DATA_BASE+extent,0u,extent);
    for(unsigned i=0u;i<3000u&&!nor.erase_active;i++)product_tick();
    assert(nor.erase_active&&!product_rec.catalog.phase&&product_rec.pipeline.reserve.entry==&product_rec.pipeline.future);
    if(suspended) {
        for(unsigned i=0u;i<10u&&!companion_spi_nor_stm32wba_erase_is_suspended(&nor);i++){
            f.now+=2u;(void)companion_spi_nor_stm32wba_erase_suspend_step(&nor);
        }
        assert(companion_spi_nor_stm32wba_erase_is_suspended(&nor));
    }
    uint32_t at=nor.erase_address,bytes=nor.erase_bytes,erases=f.erases,starts=mic_starts;
    assert(bytes==(half?32768u:4096u));
    uint32_t cursor=product_rec.pipeline.reserve.cursor,reads=f.reads,writes=f.writes,resumes=f.resumes;
    comp_segment_entry_t original=product_rec.capture.engine.active;
    uint8_t before[4096];memcpy(before,f.bytes+DATA_BASE+original.extent_offset,sizeof(before));
    comp_wba_recording_product_fault(&product_rec,COMP_WBA_RECORDING_FAULT_DEADLINE);assert_no_live();
    product_rec.capture.engine.encoder_owned=true;product_tick();product_rec.capture.engine.encoder_owned=false;
    product_rec.capture.engine.microphone_active=true;mic=true;fail_mic_stops=1u;
    product_tick();assert(mic);product_rec.capture.engine.microphone_active=false;mic=false;
    product_rec.pipeline.workspace_bytes=4096u;product_tick();product_rec.pipeline.workspace_bytes=0u;
    product_rec.pipeline.workspace_requested=4096u;product_tick();product_rec.pipeline.workspace_requested=0u;
    product_rec.storage.poisoned=true;product_tick();product_rec.storage.poisoned=false;
    comp_segment_entry_t stranger={0};product_rec.pipeline.reserve.entry=&stranger;product_tick();
    product_rec.pipeline.reserve.entry=&product_rec.pipeline.future;
    nor.erase_address+=4096u;product_tick();nor.erase_address=at;
    nor.erase_bytes=bytes==4096u?65536u:4096u;product_tick();nor.erase_bytes=bytes;
    assert(f.reads==reads&&f.writes==writes&&f.erases==erases&&f.resumes==resumes&&product_rec.pipeline.reserve.cursor==cursor);
    f.automatic_erase=true;
    for(unsigned i=0u;i<500u&&nor.erase_active;i++)product_tick();
    assert(!nor.erase_active&&nor.erase_address==at&&nor.erase_bytes==bytes);
    assert_no_live();assert(mic_starts==starts&&f.erases==erases);
    if(half) {
        comp_segment_io_t next_io;
        assert(product_rec.pipeline.reserve.cursor==0u&&
            comp_segment_reserve_next_io(&product_rec.pipeline.reserve,&next_io)==COMP_SEG_OK&&
            next_io.kind==COMP_SEG_IO_READ&&next_io.address==at);
    } else assert(product_rec.pipeline.reserve.cursor==cursor+bytes&&
        product_rec.pipeline.reserve.cursor<product_rec.pipeline.reserve.bytes);
    reads=f.reads;writes=f.writes;
    for(unsigned i=0u;i<30u;i++)product_tick();
    assert(f.reads==reads&&f.writes==writes&&f.erases==erases); /* no next chunk/provenance/READY */
    assert(!memcmp(before,f.bytes+DATA_BASE+original.extent_offset,sizeof(before)));
    assert(product_rec.pipeline.future.state==COMP_SEG_WRITING&&!product_rec.pipeline.future_writer.prepared);
    wait_recovery();assert(mic_starts==starts);
    printf("PASS_FAULT_OWNED_ERASE suspended=%u half32=%u only pre-existing exact command retired; unknown/live/workspace/poison refused; no new erase/provenance/capture; original retained; explicit recovery usable\n",suspended,half);
}

int main(void)
{setvbuf(stdout,NULL,_IONBF,0);producer_commit();consumer_commit();sealing_commit();future_erase_fault(false,false);future_erase_fault(true,false);future_erase_fault(false,true);future_erase_fault(true,true);puts("SOFTWARE_ONLY no claim for actual593 fault/root/64MHz CPU");return 0;}
