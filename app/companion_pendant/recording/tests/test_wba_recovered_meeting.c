#define COMP_PRODUCT_TEST_MAIN recovered_meeting_fixture_main
#include "test_wba_recording_product.c"

static void failed_original(void)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    memset(&link_owner,0,sizeof(link_owner));memset(logical_status,0,sizeof(logical_status));
    logical_status_bytes=0u;logical_publish_failures=0u;logical_publish_attempts=0u;
    comp_link_config_t cfg={&link_owner.runtime,NULL,NULL,&link_owner.features,logical_publish,NULL};
    assert(comp_link_init_segmented(&link_owner.link,&cfg,&radio,&product_rec.pipeline,248u));
    comp_link_connection(&link_owner.link,true,true,f.now);subscribe(COMPANION_GATT_CHAR_MEETING_STATUS,true);
    comp_link_test_record_hook=pause_record_hook;pause_session=501u;
    uint8_t wire[56];pause_command(wire,1u,101u,0u,0u);send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,56u);
    for(unsigned i=0u;i<20000u&&!comp_wba_recording_product_ready(&product_rec,link_owner.runtime.record_token);i++)product_tick();
    assert(comp_wba_recording_product_control(&product_rec,true,link_owner.runtime.record_token));
    link_owner.runtime.prepare_pending=link_owner.runtime.command_pending=false;pause_control_tick();
    assert(logical_status_bytes==80u&&logical_status[1]==1u&&!logical_status[2]);
    for(unsigned block=0u;block<14u;block++) {
        int16_t samples[160];pcm(block,samples);
        assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<160u;i++)pause_control_tick();
    }
    assert(product_rec.capture.engine.stats.durable_bytes>0u);
    int16_t samples[160];pcm(15u,samples);
    for(unsigned block=0u;block<8u;block++)assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
    assert(!comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
    pause_control_tick();
    /* Runtime is a documented port in this link fixture. The separate real
     * app test exercises the production report, pending/cancel and CSI1. */
    link_owner.runtime.recording=DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY;
    assert(!mic&&product_rec.pipeline.state==COMP_PIPE_FAILED&&logical_status_bytes==80u&&
        logical_status[1]==1u&&logical_status[2]==COMPANION_V1_MEETING_ERROR_REJECTED);
}
static void finish_runtime_link_recovery(bool retain_request)
{
    unsigned starts=mic_starts,erases=f.erases;comp_segment_entry_t old=product_entry(0u);
    uint8_t before[4096];memcpy(before,f.bytes+DATA_BASE+old.extent_offset,sizeof(before));
    unsigned polls=0u;
    for(;polls<30000u&&!product_rec.ready;polls++) {
        pause_control_tick();
        if(!product_rec.ready)assert(product_rec.pipeline.state==COMP_PIPE_FAILED&&
            logical_status_bytes==80u); /* No idle claim while scanning. */
    }
    assert(product_rec.ready&&product_rec.media_ready&&product_rec.pipeline.state==COMP_PIPE_IDLE&&
        !product_rec.pipeline.token&&!product_rec.pipeline.engine_bound&&!mic&&mic_starts==starts);
    assert(f.erases==erases&&!memcmp(before,f.bytes+DATA_BASE+old.extent_offset,sizeof(before)));
    comp_segment_entry_t recovered=product_entry(0u);
    assert(recovered.descriptor.session_id==old.descriptor.session_id&&
        recovered.descriptor.recording_id==old.descriptor.recording_id&&
        (recovered.descriptor.flags&COMP_REC_V2_RECOVERED)&&recovered.descriptor.sample_count>0u);
    assert(logical_status_bytes==(retain_request?80u:64u));
}
static void assert_idle(void)
{
    assert(logical_status_bytes==64u&&!memcmp(logical_status+28u,"CMS2",4u)&&
        logical_status[0]==1u&&!logical_status[1]&&!logical_status[2]&&
        !comp_rec_get32(logical_status+8u)&&!comp_rec_get32(logical_status+12u)&&
        !comp_rec_get64(logical_status+52u)&&!memcmp(logical_status+32u,device_uid,12u)&&
        comp_rec_get64(logical_status+44u)==7u&&
        comp_rec_get32(logical_status+60u)==comp_rec_crc(logical_status,60u));
    assert(!link_owner.link.meeting_start_request_id&&!link_owner.link.meeting_record_token&&
        !link_owner.link.meeting_control_sequence&&!link_owner.link.remote_limit_ms&&
        !link_owner.link.remote_record_token&&!link_owner.link.meeting_extended);
}
static bool retry_recovery(comp_runtime_t *runtime,bool start)
{
    (void)runtime;return start&&comp_wba_recording_product_recover_begin(&product_rec);
}
static void idle_after_explicit_recovery(void)
{
    failed_original();unsigned starts=mic_starts;
    assert(comp_wba_recording_product_recover_begin(&product_rec));
    finish_runtime_link_recovery(false);assert_idle();
    unsigned attempts=logical_publish_attempts;pause_control_tick();assert(logical_publish_attempts==attempts);
    /* Reconnect re-publishes actual idle identity, never the old failure. */
    comp_link_connection(&link_owner.link,false,false,f.now);
    comp_link_connection(&link_owner.link,true,true,f.now);pause_control_tick();assert_idle();
    assert(mic_starts==starts&&!link_owner.runtime.capture_active);
    FILE *out=fopen("recovered-idle.cms2","wb");assert(out);
    assert(fwrite(logical_status,1u,64u,out)==64u&&fclose(out)==0);
    puts("PASS_RECOVERED_LINK_IDLE real C/NOR/Opus fault-recovery clears stale active/error; CMS2 CRC UID epoch, recovered catalogue retained; no STOP ACK or mic restart");
}
static void pending_remote_start(bool cancel)
{
    failed_original();comp_link_test_record_hook=retry_recovery;
    unsigned starts=mic_starts;uint32_t old_token=link_owner.runtime.record_token;
    uint8_t wire[56];pause_command(wire,1u,202u,0u,0u);
    comp_rec_put32(wire+40u,202u);comp_rec_put32(wire+52u,comp_rec_crc(wire,52u));
    send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,56u);
    uint32_t token=link_owner.runtime.record_token;
    assert(token!=old_token&&link_owner.link.meeting_start_request_id==202u&&
        link_owner.link.meeting_record_token==token&&link_owner.runtime.prepare_pending);
    finish_runtime_link_recovery(true);
    /* Any one pending phase must preserve correlation through the brief
     * IDLE/token0 interval before ordinary identity/prepare. */
    for(unsigned phase=0u;phase<3u;phase++) {
        link_owner.runtime.command_pending=phase==0u;
        link_owner.runtime.prepare_pending=phase==1u;
        link_owner.runtime.start_pending=phase==2u;
        pause_control_tick();
        assert(logical_status_bytes==80u&&!logical_status[2]&&
            link_owner.link.meeting_start_request_id==202u&&link_owner.link.meeting_record_token==token&&
            comp_rec_get32(logical_status+8u)==202u&&!memcmp(logical_status+28u,"CMS3",4u));
    }
    link_owner.runtime.command_pending=link_owner.runtime.prepare_pending=link_owner.runtime.start_pending=false;
    if(cancel) {
        pause_control_tick();assert_idle();assert(mic_starts==starts);
        puts("PASS_RECOVERY_CANCELED_START idle after actual cancellation; no finalized claim/new recording");return;
    }
    assert(comp_wba_recording_product_prepare_bookmarked(&product_rec,502u,1u,0u,token));
    for(unsigned i=0u;i<20000u&&!comp_wba_recording_product_ready(&product_rec,token);i++)pause_control_tick();
    assert(comp_wba_recording_product_control(&product_rec,true,token));pause_control_tick();
    assert(logical_status_bytes==80u&&logical_status[1]==1u&&!logical_status[2]&&
        comp_rec_get32(logical_status+8u)==202u&&comp_rec_get64(logical_status+52u)==502u&&mic_starts==starts+1u);
    assert(comp_wba_recording_product_control(&product_rec,false,token));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)pause_control_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED&&!mic);
    puts("PASS_PENDING_REMOTE_START command/prepare/start correlation preserved, ordinary prepare/MIC/STOP; software runtime port");
}
int main(void)
{
    setvbuf(stdout,NULL,_IONBF,0);idle_after_explicit_recovery();pending_remote_start(false);pending_remote_start(true);
    comp_link_test_record_hook=NULL;
    logical_control_across_segments();pause_controls("ordinary-pause-control.cpc3");
    puts("SOFTWARE_ONLY actual61MHz/Type reconnect/power NOT_QUALIFIED");return 0;
}
