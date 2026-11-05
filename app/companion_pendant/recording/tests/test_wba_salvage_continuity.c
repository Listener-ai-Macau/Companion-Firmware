#define COMP_PRODUCT_TEST_MAIN continuity_fixture_main
#include "test_wba_recording_product.c"

static void stopped_overflow(void)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    product_ready_capture(501u,81u);
    for(unsigned block=0u;block<14u;block++) {
        int16_t samples[160];pcm(block,samples);
        assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<160u;i++)product_tick();
    }
    int16_t samples[160];pcm(15u,samples);
    for(unsigned block=0u;block<8u;block++)assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
    assert(!comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
    product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FAILED&&!mic);
}

static bool fragmented_start(comp_runtime_t *runtime,bool start)
{
    return start && comp_wba_recording_product_prepare_bookmarked(&product_rec,502u,1u,0u,runtime->record_token);
}

/* Exercise the negotiated, UID/epoch-bound capacity and CMC3 START path.
 * The runtime scheduler is the existing link fixture shim; the real runtime
 * plus product integration is exercised separately. */
static void start_through_link(void)
{
    memset(&link_owner,0,sizeof(link_owner));test_value_capacity=136u;
    last_reply_bytes=retry_bytes=0u;blocked=0u;
    comp_link_config_t cfg={&link_owner.runtime,NULL,NULL,&link_owner.features,radio_publish,NULL};
    assert(comp_link_init_segmented(&link_owner.link,&cfg,&radio,&product_rec.pipeline,test_value_capacity));
    connect_peer();subscribe(COMPANION_GATT_CHAR_MEETING_STATUS,true);
    uint8_t request[32]={2u,0x26u};comp_rec_put32(request+4u,901u);
    memcpy(request+8u,device_uid,12u);comp_rec_put64(request+20u,7u);
    comp_rec_put32(request+28u,comp_rec_crc(request,28u));
    last_reply_bytes=0u;send(COMPANION_GATT_CHAR_RECORDING_CONTROL,request,32u);radio_tick();
    assert(last_reply_bytes==32u&&!memcmp(last_reply,"CSN1",4u)&&
           last_reply[12]==product_rec.space.allocatable_segments&&radio.capacity_token==901u);
    uint8_t start[56]={0};memcpy(start,"CMC3",4u);start[4]=3u;start[5]=1u;start[6]=2u;start[7]=1u;
    memcpy(start+8u,device_uid,12u);comp_rec_put64(start+20u,7u);
    comp_rec_put32(start+36u,901u);comp_rec_put32(start+40u,901u);comp_rec_put16(start+44u,200u);
    comp_rec_put32(start+52u,comp_rec_crc(start,52u));
    comp_link_test_record_hook=fragmented_start;
    send(COMPANION_GATT_CHAR_MEETING_CONTROL,start,56u);
    assert(link_owner.record_calls==1u&&!radio.capacity_token);
    comp_link_test_record_hook=NULL;
    for(unsigned i=0u;i<20000u&&!comp_wba_recording_product_ready(&product_rec,link_owner.runtime.record_token);i++)product_tick();
    assert(comp_wba_recording_product_ready(&product_rec,link_owner.runtime.record_token));
    assert(comp_wba_recording_product_control(&product_rec,true,link_owner.runtime.record_token));
    assert(mic);
}

/* Fault injection in the in-memory NOR fixture only. The damaged owner's
 * entire extent must survive a separate capture, including a reboot. */
static void record_around_bad_tail(bool runtime)
{
    stopped_overflow();
    comp_segment_entry_t old=product_entry(0u);
    uint32_t at=DATA_BASE+old.extent_offset;
    assert(old.reserved_bytes==4096u);
    f.bytes[at+37u]^=1u;
    uint8_t original[4096];memcpy(original,f.bytes+at,sizeof(original));
    if(runtime)assert(comp_wba_recording_product_recover_begin(&product_rec));
    else product_bind();
    for(unsigned i=0u;i<30000u;i++) {
        if(comp_wba_recording_product_state(&product_rec)==COMP_WBA_RECORDING_FAULT)break;
        if(!runtime&&product_rec.media_ready&&comp_wba_recording_product_space_current(&product_rec)) {
            comp_wba_recording_product_lease_result(&product_rec,true);
        }
        product_tick();
    }
    assert(comp_wba_recording_product_readable(&product_rec));
    assert(product_rec.space.valid&&!product_rec.space.allocation_uncertain);
    uint32_t physical;
    assert(product_rec.space.highest_end<=product_rec.catalog.data_bytes-4096u);
    assert(comp_wba_recording_product_update_available(&product_rec));
    assert(!comp_wba_recording_product_update_workspace(&product_rec,
        product_rec.catalog.data_bytes-old.extent_offset,&physical));
    assert(comp_wba_recording_product_update_workspace(&product_rec,4096u,&physical));
    assert(physical==DATA_BASE+product_rec.catalog.data_bytes-4096u);
    assert(!memcmp(original,f.bytes+at,sizeof(original)));
    /* Emulate the already-owned update bytes and a reboot. This is not a
     * signed-install test: only the exact restored lease and isolation are
     * exercised, using the real product owner and synthetic NOR. */
    memset(f.bytes+physical,0x5au,4096u);
    product_bind();product_mount();
    assert(comp_wba_recording_product_workspace(&product_rec,4096u,&physical));
    comp_wba_recording_product_lease_result(&product_rec,true);
    assert(comp_wba_recording_product_update_available(&product_rec));
    assert(physical==DATA_BASE+product_rec.catalog.data_bytes-4096u);
    assert(!memcmp(original,f.bytes+at,sizeof(original)));
    assert(comp_wba_recording_product_update_workspace(&product_rec,0u,&physical));
    product_refresh_space();
    unsigned writes=f.writes,erases=f.erases;
    product_rec.space.allocation_uncertain=true;
    assert(!comp_wba_recording_product_prepare(&product_rec,502u,1u,0u,82u));
    assert(!comp_wba_recording_product_update_workspace(&product_rec,4096u,&physical));
    product_rec.space.allocation_uncertain=false;
    product_rec.storage.poisoned=true;
    assert(!comp_wba_recording_product_prepare(&product_rec,502u,1u,0u,82u));
    assert(!comp_wba_recording_product_update_workspace(&product_rec,4096u,&physical));
    product_rec.storage.poisoned=false;
    uint8_t available=product_rec.space.allocatable_segments;
    product_rec.space.allocatable_segments=0u;
    assert(!comp_wba_recording_product_prepare(&product_rec,502u,1u,0u,82u));
    product_rec.space.allocatable_segments=available;
    product_rec.space.valid=false;
    assert(!comp_wba_recording_product_prepare(&product_rec,502u,1u,0u,82u));
    assert(!comp_wba_recording_product_update_workspace(&product_rec,4096u,&physical));
    product_rec.space.valid=true;
    assert(f.writes==writes&&f.erases==erases&&!mic);
    if(runtime)product_ready_capture(502u,82u);
    else start_through_link();
    for(unsigned block=0u;block<14u;block++) {
        int16_t samples[160];pcm(block,samples);
        assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<160u;i++)product_tick();
    }
    assert(comp_wba_recording_product_control(&product_rec,false,runtime?82u:link_owner.runtime.record_token));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED&&!mic);
    product_refresh_space();
    assert(!memcmp(original,f.bytes+at,sizeof(original)));
    comp_segment_entry_t bad=product_entry(0u),fresh=product_entry(1u);
    assert(bad.state==COMP_SEG_WRITING&&bad.descriptor.recording_id==old.descriptor.recording_id);
    assert(fresh.state==COMP_SEG_UNSYNCED&&fresh.descriptor.session_id==502u);
    assert(fresh.extent_offset>=old.extent_offset+old.reserved_bytes ||
           old.extent_offset>=fresh.extent_offset+fresh.reserved_bytes);
    product_bind();
    for(unsigned i=0u;i<30000u;i++) {
        if(comp_wba_recording_product_state(&product_rec)==COMP_WBA_RECORDING_FAULT)break;
        if(product_rec.media_ready&&comp_wba_recording_product_space_current(&product_rec))
            comp_wba_recording_product_lease_result(&product_rec,true);
        product_tick();
    }
    assert(comp_wba_recording_product_readable(&product_rec));
    assert(!memcmp(original,f.bytes+at,sizeof(original)));
    bad=product_entry(0u);fresh=product_entry(1u);
    assert(bad.state==COMP_SEG_WRITING&&fresh.state==COMP_SEG_UNSYNCED&&fresh.descriptor.session_id==502u);
    puts("PASS new capture around retained corrupt extent, including remount; simulated NOR only");
}
/* A transient read failure while rebuilding the capacity view must not make
 * an already-isolated recording tail permanently block unrelated recording.
 * All faults and flash bytes in this test are simulated. */
static void setup_salvage(uint8_t original[4096], uint32_t *old_at)
{
    stopped_overflow();
    comp_segment_entry_t old=product_entry(0u);
    *old_at=DATA_BASE+old.extent_offset;
    f.bytes[*old_at+37u]^=1u;
    memcpy(original,f.bytes+*old_at,4096u);
    product_bind();product_mount();
    comp_wba_recording_product_lease_result(&product_rec,true);
    assert(comp_wba_recording_product_salvaging(&product_rec)&&
           comp_wba_recording_product_tail_retained(&product_rec)&&!mic);
}

static void transient_idle_read(void)
{
    uint8_t original[4096];uint32_t at;
    setup_salvage(original,&at);
    unsigned writes=f.writes,erases=f.erases,starts=mic_starts;
    memset(&product_rec.space,0,sizeof(product_rec.space));
    f.fail_command=3u;product_tick();
    assert(product_rec.storage.poisoned&&
           comp_wba_recording_product_state(&product_rec)==COMP_WBA_RECORDING_FAULT);
    assert(!comp_wba_recording_product_salvaging(&product_rec)&&
           comp_wba_recording_product_tail_retained(&product_rec));
    assert(comp_wba_recording_product_boot_retry_pending(&product_rec));
    assert(comp_wba_recording_product_boot_retry(&product_rec,f.now));
    assert(comp_wba_recording_product_tail_retained(&product_rec));
    for(unsigned i=0u;i<30000u&&comp_wba_recording_product_recovering(&product_rec);++i)product_tick();
    assert(comp_wba_recording_product_salvaging(&product_rec)&&
           comp_wba_recording_product_tail_retained(&product_rec)&&
           comp_wba_recording_product_capture_prepare_available(&product_rec)&&!mic);
    assert(f.writes==writes&&f.erases==erases&&mic_starts==starts);
    assert(!memcmp(original,f.bytes+at,sizeof(original)));
    comp_segment_entry_t retained=product_entry(0u);
    assert(retained.state==COMP_SEG_WRITING);
    puts("PASS salvage idle read fault: bounded remount keeps damaged owner and resumes available space");
}

static void guarded_idle_read(void)
{
    uint8_t original[4096];uint32_t at,physical;
    setup_salvage(original,&at);
    unsigned writes=f.writes,erases=f.erases;
    memset(&product_rec.space,0,sizeof(product_rec.space));
    f.fail_command=3u;product_tick();
    assert(comp_wba_recording_product_boot_retry_pending(&product_rec));
    f.fail_command=0x9fu;
    assert(!comp_wba_recording_product_boot_retry(&product_rec,f.now));
    assert(!comp_wba_recording_product_boot_retry(&product_rec,f.now+999u));
    f.fail_command=0x9fu;
    assert(!comp_wba_recording_product_boot_retry(&product_rec,f.now+1000u));
    assert(!comp_wba_recording_product_boot_retry_pending(&product_rec));
    assert(!comp_wba_recording_product_capture_available(&product_rec));
    assert(comp_wba_recording_product_tail_retained(&product_rec));
    assert(f.writes==writes&&f.erases==erases&&!memcmp(original,f.bytes+at,sizeof(original)));

    setup_salvage(original,&at);
    assert(comp_wba_recording_product_update_workspace(&product_rec,4096u,&physical));
    writes=f.writes;erases=f.erases;
    memset(&product_rec.space,0,sizeof(product_rec.space));
    f.fail_command=3u;product_tick();
    assert(product_rec.storage.poisoned&&!comp_wba_recording_product_boot_retry_pending(&product_rec));
    assert(product_rec.pipeline.workspace_bytes==4096u);
    assert(f.writes==writes&&f.erases==erases&&!memcmp(original,f.bytes+at,sizeof(original)));
    puts("PASS salvage retry stays bounded and never clears an active update owner");
}

static void completed_scan_clears_retained_status(void)
{
    uint8_t original[4096];uint32_t at;
    setup_salvage(original,&at);
    /* In this synthetic fixture only, reverse the earlier injected damage.
     * This is not a recipe for changing real recordings. */
    f.bytes[at+37u]^=1u;
    memset(&product_rec.space,0,sizeof(product_rec.space));
    f.fail_command=3u;product_tick();
    assert(comp_wba_recording_product_tail_retained(&product_rec));
    assert(comp_wba_recording_product_boot_retry(&product_rec,f.now));
    for(unsigned i=0u;i<30000u&&comp_wba_recording_product_recovering(&product_rec);++i)product_tick();
    assert(product_rec.ready&&!comp_wba_recording_product_tail_retained(&product_rec)&&!mic);
    comp_segment_entry_t recovered=product_entry(0u);
    assert(recovered.state==COMP_SEG_UNSYNCED);
    puts("PASS retained-tail status clears only after successful full scan; synthetic media only");
}

int main(void)
{
    setvbuf(stdout,NULL,_IONBF,0);
    transient_idle_read();
    guarded_idle_read();
    completed_scan_clears_retained_status();
    record_around_bad_tail(true);
    record_around_bad_tail(false);
    return 0;
}
