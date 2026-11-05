#define COMP_PRODUCT_TEST_MAIN salvage_fixture_main
#include "test_wba_recording_product.c"

static void capture_blocks(unsigned count)
{
    for(unsigned block=0u;block<count;block++) {
        int16_t samples[160];pcm(block,samples);
        assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<160u;i++)product_tick();
    }
}
#if TEST_FIXED
static void salvage_radio_tick(void)
{
    /* The historical helper assumes one read/poll. Stopped bulk's current
     * default can read several pages, so request the public one-step budget
     * explicitly for this ownership model; do not change production pacing. */
    const comp_wba_recording_transfer_budget_t budget={1u,1u,1u};
    unsigned reads=f.reads,writes=f.writes;
    comp_link_poll_with_budget(&link_owner.link,f.now,NULL,NULL,&budget);
    assert(f.reads-reads<=1u&&f.writes==writes);
}
#endif
static void isolation(bool runtime)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    product_ready_capture(501u,81u);capture_blocks(14u);
    assert(comp_wba_recording_product_control(&product_rec,false,81u));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED);
    comp_segment_entry_t good=product_entry(0u);
    uint8_t good_bytes[4096];memcpy(good_bytes,f.bytes+DATA_BASE+good.extent_offset,sizeof(good_bytes));
    product_ready_capture(502u,82u);capture_blocks(14u);
    comp_segment_entry_t bad=product_entry(1u);
    comp_wba_recording_product_fault(&product_rec,COMP_WBA_RECORDING_FAULT_DEADLINE);
    f.bytes[DATA_BASE+bad.extent_offset+37u]^=1u;
    uint8_t bad_bytes[4096];memcpy(bad_bytes,f.bytes+DATA_BASE+bad.extent_offset,sizeof(bad_bytes));
    unsigned erases=f.erases,starts=mic_starts;
    if(runtime)assert(comp_wba_recording_product_recover_begin(&product_rec));
    else product_bind();
    for(unsigned i=0u;i<30000u;i++) {
        if(comp_wba_recording_product_state(&product_rec)==COMP_WBA_RECORDING_FAULT)break;
        if(product_rec.media_ready&&comp_wba_recording_product_space_current(&product_rec))break;
#if TEST_FIXED
        if(runtime&&comp_wba_recording_product_state(&product_rec)==COMP_WBA_RECORDING_PREPARING)
            assert(!comp_wba_recording_pipeline_page_available(&product_rec.pipeline));
#endif
        product_tick();
    }
    uint8_t capability[32];
#if !TEST_FIXED
    assert(!product_rec.media_ready&&!product_rec.ready&&!mic);
    assert(!comp_wba_recording_product_capability(&product_rec,capability));
    assert(!comp_wba_recording_pipeline_page_available(&product_rec.pipeline));
    assert(!memcmp(good_bytes,f.bytes+DATA_BASE+good.extent_offset,sizeof(good_bytes)));
    assert(!memcmp(bad_bytes,f.bytes+DATA_BASE+bad.extent_offset,sizeof(bad_bytes)));
    assert(f.erases==erases&&mic_starts==starts);
    puts("REPRODUCED745: one unresolved WRITING extent hides intact sealed original and its CRV2 reader");
#else
    if(!runtime) {
        assert(!comp_wba_recording_product_readable(&product_rec));
        assert(!comp_wba_recording_product_capability(&product_rec,capability));
        comp_wba_recording_product_lease_result(&product_rec,true);
    }
    assert(!product_rec.ready&&product_rec.media_ready&&!mic&&mic_starts==starts);
    assert(comp_wba_recording_product_state(&product_rec)==COMP_WBA_RECORDING_FAULT);
    assert(comp_wba_recording_product_readable(&product_rec));
    assert(comp_wba_recording_product_capability(&product_rec,capability));
    assert(comp_wba_recording_pipeline_page_available(&product_rec.pipeline));
    assert(product_rec.space.unsynced==1u&&product_rec.space.writing==1u);
    uint32_t physical;unsigned writes=f.writes;
    assert(comp_wba_recording_product_capture_prepare_available(&product_rec));
    assert(!comp_wba_recording_product_workspace(&product_rec,4096u,&physical));
    assert(!comp_wba_recording_product_update_workspace(&product_rec,4096u,&physical));
    assert(!comp_wba_recording_product_recover_begin(&product_rec));
    assert(f.writes==writes&&f.erases==erases&&!mic&&mic_starts==starts);
    /* Use the actual protected dispatcher, directory, pull, CRC/SHA and
     * exact consume route. A sealed original is accessible; the bad tail
     * never becomes a directory item, microphone owner or reclaim target. */
    memset(&link_owner,0,sizeof(link_owner));test_value_capacity=136u;
    last_reply_bytes=retry_bytes=0u;saved_bytes=receipt_count=blocked=0u;
    comp_link_config_t cfg={&link_owner.runtime,NULL,NULL,&link_owner.features,radio_publish,NULL};
    assert(comp_link_init_segmented(&link_owner.link,&cfg,&radio,&product_rec.pipeline,test_value_capacity));
    connect_peer();uint8_t request[32]={2u,0x20u};comp_rec_put32(request+8u,71u);
    last_reply_char=COMPANION_GATT_CHAR_MEETING_STATUS;
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,request,16u);
    for(unsigned i=0u;i<100u&&last_reply_char!=COMPANION_GATT_CHAR_RECORDING_LIST;i++){product_tick();salvage_radio_tick();}
    assert(last_reply_char==COMPANION_GATT_CHAR_RECORDING_LIST&&last_reply_bytes==136u&&comp_rec_get32(last_reply+12u)==1u);
    comp_rec_v2_descriptor_t listed;assert(comp_rec_v2_decode(last_reply+24u,112u,&listed));
    assert(listed.recording_id==good.descriptor.recording_id&&listed.session_id==501u);
    sealed_request(&good,0u,request);send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);
    for(unsigned i=0u;i<3000u&&saved_bytes<good.descriptor.encoded_length;i++){product_tick();salvage_radio_tick();}
    assert(saved_bytes==good.descriptor.encoded_length);
    companion_sha256_t sha;uint8_t digest[32];companion_sha256_init(&sha);
    companion_sha256_update(&sha,saved,saved_bytes);companion_sha256_final(&sha,digest);
    assert(!memcmp(digest,good.descriptor.sha256,32u));salvage_radio_tick();
    uint8_t proof[84];consumption_proof(&good,proof);send(COMPANION_GATT_CHAR_DELETE_PRIVACY,proof,84u);
    for(unsigned i=0u;i<20000u&&receipt_count==0u;i++){product_tick();salvage_radio_tick();}
    assert(receipt_count==1u&&!memcmp(last_reply,proof,84u));
    assert(f.erases==erases+1u&&!memcmp(bad_bytes,f.bytes+DATA_BASE+bad.extent_offset,sizeof(bad_bytes)));
    product_refresh_space();assert(product_rec.space.writing==1u&&!product_rec.space.unsynced);
    assert(!product_rec.ready&&comp_wba_recording_product_readable(&product_rec)&&!mic);
    comp_segment_entry_t remaining=product_entry(0u);assert(remaining.state==COMP_SEG_WRITING&&remaining.descriptor.recording_id==bad.descriptor.recording_id);
    assert(comp_wba_recording_product_update_workspace(&product_rec,4096u,&physical));
    assert(comp_wba_recording_product_update_workspace(&product_rec,0u,&physical));
    assert(!memcmp(bad_bytes,f.bytes+DATA_BASE+bad.extent_offset,sizeof(bad_bytes)));
    puts("PASS: intact original exact consume precedes isolated OTA claim; bad bytes/ownership and FAULT retained; no automatic START");
#endif
}
#if TEST_FIXED
static void catalogue_io_stays_closed(void)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    product_bind();f.fail_command=0x03u;
    unsigned erases=f.erases;
    for(unsigned i=0u;i<20000u&&comp_wba_recording_product_state(&product_rec)!=COMP_WBA_RECORDING_FAULT;i++)product_tick();
    uint8_t capability[32];
    assert(product_rec.storage.poisoned&&!product_rec.media_ready&&!product_rec.ready);
    assert(!comp_wba_recording_product_readable(&product_rec));
    assert(!comp_wba_recording_product_capability(&product_rec,capability));
    assert(!mic&&f.erases==erases);
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,false);
    assert(!comp_wba_recording_product_readable(&product_rec)&&!product_rec.ready&&!mic);
    puts("PASS: catalogue read I/O failure and WUS2 reconciliation refusal remain closed; no degraded reader granted");
}
#endif
int main(void){
    setvbuf(stdout,NULL,_IONBF,0);isolation(false);isolation(true);
#if TEST_FIXED
    catalogue_io_stays_closed();
#endif
    return 0;
}
