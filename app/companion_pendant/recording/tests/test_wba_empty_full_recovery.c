#include <stdlib.h>
#include "opus.h"
#define COMP_PRODUCT_TEST_MAIN empty_full_fixture_main
#include "test_wba_recording_product.c"

static uint8_t saved_extent[65536];
static unsigned full_reports;
static void ordered_report(void *context,uint32_t token,denzic_audio_recording_state_v1_t state,bool active)
{
    if(state==DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY) {
        assert(product_rec.pipeline.state==COMP_PIPE_FAILED&&!active);
        assert(!comp_wba_recording_pipeline_page_available(&product_rec.pipeline));full_reports++;
    }
    product_report(context,token,state,active);
}
/* Real SysTick advances while the NOR status transaction busy-spins. The
 * inherited portable fixture advances time only between foreground polls;
 * explicitly supply progress for the production synchronous wait hook. */
static void model_wait_progress(void *context){(void)context;f.now++;}
/* Current driver combines opcode+status into16 clocks. Forward both phases
 * under the existing asserted CS to the inherited command-level NOR model;
 * its status/busy/program/erase behavior remains authoritative. */
static bool model_transfer(void *context,const uint8_t *tx,uint8_t *rx,size_t n,uint32_t timeout)
{
    if(tx&&rx&&n==2u&&(tx[0]==5u||tx[0]==0x35u)&&!f.command) {
        rx[0]=0u;
        return transfer(context,tx,NULL,1u,timeout)&&transfer(context,NULL,rx+1u,1u,timeout);
    }
    return transfer(context,tx,rx,n,timeout);
}
static comp_segment_entry_t fill_with_one_original(void)
{
    puts("MODEL fresh");product_fresh();product_rec.report=ordered_report;full_reports=0u;nor.config.wait_progress=model_wait_progress;nor.config.transfer=model_transfer;puts("MODEL mount");
    for(unsigned i=0u;i<20000u&&!comp_wba_recording_product_space_current(&product_rec)&&
        comp_wba_recording_product_state(&product_rec)!=COMP_WBA_RECORDING_FAULT;++i)product_tick();
    printf("MODEL mount-end phase=%u fail=%u catalog=%u poisoned=%u command=%u SR=%u/%u programs=%lu erases=%lu now=%lu\n",
        product_rec.boot_phase,product_rec.pipeline.failure,product_rec.catalog.phase,product_rec.storage.poisoned,
        f.command,f.sr1,f.sr2,(unsigned long)f.writes,(unsigned long)f.erases,(unsigned long)f.now);
    assert(product_rec.media_ready&&comp_wba_recording_product_space_current(&product_rec));
    comp_wba_recording_product_lease_result(&product_rec,true);puts("MODEL mounted");
    /* One valid original owns the whole model arena. This uses the ordinary
     * production writer and portable host Opus, not fabricated catalog bits.
     * This model does not qualify the ARM CELT profile or MCU arena/timing. */
    product_rec.pipeline.config.extent_bytes=65536u;
    product_ready_capture(701u,91u);puts("MODEL first capture ready");
    for(unsigned block=0u;block<8u;++block) {
        int16_t samples[160];pcm(block,samples);
        assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<160u;++i)product_tick();
    }
    assert(comp_wba_recording_product_control(&product_rec,false,91u));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;++i)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED&&!mic&&mic_starts==1u&&mic_stops==1u);
    product_refresh_space();assert(product_rec.space.reserved_bytes==65536u&&product_rec.space.largest_gap==0u);
    comp_segment_entry_t entry=product_entry(0u);
    assert(entry.state==COMP_SEG_UNSYNCED&&entry.descriptor.sample_count==1280u&&entry.descriptor.encoded_length>54u);
    memcpy(saved_extent,f.bytes+DATA_BASE,sizeof(saved_extent));return entry;
}
static void reject_full(void)
{
    unsigned starts=mic_starts,writes=f.writes,erases=f.erases,old_reports=full_reports;reported_audio=DENZIC_AUDIO_RECORDING_STATE_IDLE;
    assert(comp_wba_recording_product_prepare(&product_rec,702u,1u,0u,92u));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state==COMP_PIPE_PREPARING;++i)product_tick();
    assert(!mic&&mic_starts==starts&&!reported_capture&&reported_token==92u);
    assert(reported_audio==DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY);
    assert(full_reports==old_reports+1u);
    assert(product_rec.last_fault==COMP_WBA_RECORDING_FAULT_STORAGE_FULL&&product_rec.pipeline.failure==COMP_SEG_FULL);
    assert(!product_rec.pipeline.engine_bound&&!product_rec.pipeline.future.descriptor.recording_id);
    assert(writes==f.writes&&erases==f.erases&&!memcmp(saved_extent,f.bytes+DATA_BASE,sizeof(saved_extent)));
}
#if TEST_FIXED
static void full_start_status_and_retry(void)
{
    memset(&link_owner,0,sizeof(link_owner));memset(logical_status,0,sizeof(logical_status));
    logical_status_bytes=0u;logical_publish_failures=0u;
    comp_link_config_t cfg={&link_owner.runtime,NULL,NULL,&link_owner.features,logical_publish,NULL};
    assert(comp_link_init_segmented(&link_owner.link,&cfg,&radio,&product_rec.pipeline,136u));
    comp_link_connection(&link_owner.link,true,true,f.now);subscribe(COMPANION_GATT_CHAR_MEETING_STATUS,true);
    comp_link_test_record_hook=pause_record_hook;
    for(uint32_t request=101u;request<=102u;++request) {
        pause_session=800u+request;uint8_t wire[56];pause_command(wire,1u,request,0u,0u);
        comp_rec_put32(wire+40u,request);comp_rec_put32(wire+52u,comp_rec_crc(wire,52u));
        unsigned calls=link_owner.record_calls;
        send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,56u);
        assert(link_owner.record_calls==calls+1u); /* A fresh request must reach prepare. */
        for(unsigned i=0u;i<20000u&&product_rec.pipeline.state==COMP_PIPE_PREPARING;++i)product_tick();
        assert(product_rec.pipeline.state==COMP_PIPE_IDLE&&!product_rec.pipeline.engine_bound&&!mic);
        /* This fixture ports runtime scheduling. Apply the terminal callback
         * already emitted by the production product before the link polls. */
        assert(reported_audio==DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY);
        link_owner.runtime.prepare_pending=link_owner.runtime.command_pending=false;
        link_owner.runtime.recording=reported_audio;comp_link_poll(&link_owner.link,f.now);
        assert(logical_status[1]==0u&&logical_status[2]==COMPANION_V1_MEETING_ERROR_STORAGE_FULL&&
            comp_rec_get32(logical_status+8u)==request);
    }
    comp_link_test_record_hook=NULL;
    puts("FULL_START_STATUS: asynchronous empty-full failure reports exact request/error and permits a fresh START; no microphone start. Runtime scheduling is ported.");
}
static void guards(void)
{
    /* Exercise the real release predicate against the actual rejected state;
     * every foreign/live/partially-owned state must remain blocked. */
    product_rec.pipeline.state=COMP_PIPE_FAILED;
    comp_wba_recording_pipeline_t *p=&product_rec.pipeline;
#define REFUSE(field,value) do {field=value;assert(!comp_wba_recording_pipeline_release_empty_full(p));field=0;}while(0)
    REFUSE(p->engine_bound,true);REFUSE(p->future.descriptor.recording_id,1u);
    REFUSE(p->config.recording->microphone_active,true);REFUSE(p->config.recording->encoder_owned,true);
    REFUSE(p->config.catalog->phase,1u);REFUSE(p->config.storage->poisoned,true);
    p->config.catalog->mounted=false;assert(!comp_wba_recording_pipeline_release_empty_full(p));p->config.catalog->mounted=true;
    REFUSE(p->consume_phase,1u);
    REFUSE(p->config.storage->nor->erase_active,true);REFUSE(p->workspace_bytes,4096u);REFUSE(p->workspace_requested,4096u);
    p->sealing=&p->future;assert(!comp_wba_recording_pipeline_release_empty_full(p));p->sealing=NULL;
    p->failure=COMP_SEG_IO_ERROR;assert(!comp_wba_recording_pipeline_release_empty_full(p));p->failure=COMP_SEG_FULL;
    assert(comp_wba_recording_pipeline_release_empty_full(p));
#undef REFUSE
}
static void sync_consume_and_record_again(const comp_segment_entry_t *entry)
{
    comp_segment_audio_port_t audio=comp_wba_segment_storage_audio_port(&product_rec.storage);
    companion_sha256_t hash;companion_sha256_init(&hash);uint32_t total=0u;
    for(uint32_t page=0u;total<entry->descriptor.encoded_length;++page) {
        uint8_t bytes[256],count=0u;assert(comp_segment_audio_read_page(&audio,entry,DATA_BASE,page,bytes,&count)==COMP_SEG_OK);
        assert(count&&count<=entry->descriptor.encoded_length-total);companion_sha256_update(&hash,bytes,count);total+=count;
    }
    uint8_t digest[32];companion_sha256_final(&hash,digest);assert(!memcmp(digest,entry->descriptor.sha256,32u));
    /* Existing exact proof/physical reclaim path only after complete readback. */
    assert(comp_wba_recording_pipeline_consume(&product_rec.pipeline,&entry->descriptor)==COMP_SEG_PENDING);
    for(unsigned i=0u;i<20000u&&comp_wba_recording_pipeline_consume_result(&product_rec.pipeline)==COMP_SEG_PENDING;++i)product_tick();
    assert(comp_wba_recording_pipeline_consume_result(&product_rec.pipeline)==COMP_SEG_OK);product_refresh_space();
    assert(product_rec.space.unsynced==0u&&product_rec.space.largest_gap==65536u&&mic_starts==1u);
    uint32_t physical=0u;assert(comp_wba_recording_product_workspace(&product_rec,4096u,&physical));
    assert(comp_wba_recording_product_workspace(&product_rec,0u,&physical));product_refresh_space();
    product_ready_capture(703u,93u);assert(mic_starts==2u);
    assert(comp_wba_recording_product_control(&product_rec,false,93u));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;++i)product_tick();
    assert(!mic&&product_rec.pipeline.state==COMP_PIPE_FINISHED);
    printf("FIXED_FULL_REJECTION originalBytes=%lu completeSHA=1 consumed=1 newExplicitStart=1 noAutoStart=1 workspaceUsable=1\n",(unsigned long)total);
}
#endif
int main(void)
{
    setvbuf(stdout,NULL,_IONBF,0);
#ifdef _WIN32
    _set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);
#endif
    printf("MODEL opus=%s\n",opus_get_version_string());
    comp_segment_entry_t old=fill_with_one_original();puts("MODEL full arena ready");
#if TEST_FIXED
    full_start_status_and_retry();
#endif
    reject_full();
#if TEST_FIXED
    assert(product_rec.pipeline.state==COMP_PIPE_IDLE&&comp_wba_recording_pipeline_page_available(&product_rec.pipeline)&&!comp_wba_recording_pipeline_storage_busy(&product_rec.pipeline));
    reject_full();assert(product_rec.pipeline.state==COMP_PIPE_IDLE);guards();sync_consume_and_record_again(&old);
#else
    assert(product_rec.pipeline.state==COMP_PIPE_FAILED&&!comp_wba_recording_pipeline_page_available(&product_rec.pipeline));
    assert(!comp_wba_recording_product_recover_begin(&product_rec));
    assert(comp_wba_recording_pipeline_consume(&product_rec.pipeline,&old.descriptor)==COMP_SEG_BAD_STATE);
    uint32_t physical=0u;assert(!comp_wba_recording_product_workspace(&product_rec,4096u,&physical));
    puts("BASELINE_BUG_REPRODUCED FULL_before_microphone_locks_reader_consumer_next_START_and_workspace");
#endif
    return 0;
}
