#define COMP_PRODUCT_TEST_MAIN recovery_fixture_main
#include "test_wba_recording_product.c"

static void stopped_overflow(bool timeline)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    assert(!comp_wba_recording_product_recover_begin(&product_rec));
    assert(timeline?comp_wba_recording_product_prepare_bookmarked(&product_rec,501u,1u,0u,81u):
        comp_wba_recording_product_prepare(&product_rec,501u,1u,0u,81u));
    for(unsigned i=0u;i<20000u&&!comp_wba_recording_product_ready(&product_rec,81u);i++)product_tick();
    assert(comp_wba_recording_product_control(&product_rec,true,81u));
    assert(!comp_wba_recording_product_recover_begin(&product_rec));
    for(unsigned block=0u;block<14u;block++) {
        int16_t samples[160];pcm(block,samples);
        assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<160u;i++)product_tick();
    }
    assert(product_rec.capture.engine.stats.durable_bytes>0u);
    int16_t samples[160];pcm(15u,samples);
    for(unsigned block=0u;block<8u;block++)assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
    assert(!comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
    product_tick();
    assert(!mic&&!reported_capture&&mic_stops==1u&&product_rec.pipeline.state==COMP_PIPE_FAILED&&
        product_rec.capture.engine.state==COMP_CONT_FAULT&&!product_rec.capture.engine.encoder_owned&&
        product_rec.last_fault==COMP_WBA_RECORDING_FAULT_PCM_OVERFLOW&&
        reported_audio==DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY);
}
static void exclusion_guards(void)
{
    stopped_overflow(false);
    unsigned writes=f.writes,erases=f.erases;
#define EXCLUDE(field,value) do {field=value;assert(!comp_wba_recording_product_recover_begin(&product_rec));field=0;}while(0)
    EXCLUDE(product_rec.capture.engine.microphone_active,true);
    EXCLUDE(product_rec.capture.engine.encoder_owned,true);
    EXCLUDE(product_rec.pipeline.workspace_bytes,4096u);
    EXCLUDE(product_rec.pipeline.workspace_requested,4096u);
    EXCLUDE(product_rec.catalog.phase,1u);
    EXCLUDE(product_rec.storage.poisoned,true);
    EXCLUDE(nor.erase_active,true);
    product_rec.pipeline.sealing=&product_rec.pipeline.future;
    assert(!comp_wba_recording_product_recover_begin(&product_rec));product_rec.pipeline.sealing=NULL;
    product_rec.pipeline.consume_phase=1u;product_rec.pipeline.consume_result=COMP_SEG_PENDING;
    assert(!comp_wba_recording_product_recover_begin(&product_rec));product_rec.pipeline.consume_phase=0u;
    assert(f.writes==writes&&f.erases==erases&&product_rec.ready&&product_rec.media_ready);
    assert(product_rec.capture.engine.stats.overflows==1u);
    puts("PASS_RECOVERY_EXCLUSIVITY active-mic/encoder/lease/catalog/consumer/NOR/poison/seal refused without mutation");
}
static void recover_prefix(bool timeline)
{
    stopped_overflow(timeline);
    comp_segment_entry_t old=product_entry(0u);
    uint8_t before[4096];memcpy(before,f.bytes+DATA_BASE+old.extent_offset,sizeof(before));
    unsigned erases=f.erases,starts=mic_starts;
    assert(comp_wba_recording_product_recover_begin(&product_rec));
    assert(!product_rec.ready&&!product_rec.media_ready&&!product_rec.pipeline.engine_bound);
    assert(!comp_wba_recording_product_recover_begin(&product_rec));
    comp_wba_recording_transfer_t tx={0};comp_wba_recording_radio_t observer={0};
    observer.config.pipeline=&product_rec.pipeline;observer.config.transfer=&tx;
    observer.config.value_capacity=244u;observer.authenticated=true;observer.negotiated=true;
    observer.interval_token=77u;observer.interval_deadline=f.now+2000u;
    uint8_t hint[32]={2u,0x25u,1u};comp_rec_put32(hint+4u,77u);
    memcpy(hint+8u,device_uid,12u);comp_rec_put64(hint+20u,7u);
    comp_rec_put32(hint+28u,comp_rec_crc(hint,28u));
    assert(!comp_wba_recording_radio_interval_hint(&observer,f.now,true)&&!observer.interval_token);
    assert(!comp_wba_recording_radio_write(&observer,COMPANION_GATT_CHAR_RECORDING_CONTROL,hint,32u,true));
    unsigned ticks=0u;
    for(;ticks<30000u&&!product_rec.ready;ticks++) {
        assert(!comp_wba_recording_pipeline_page_available(&product_rec.pipeline));
        uint32_t physical;uint8_t capability[32];
        assert(!comp_wba_recording_product_workspace(&product_rec,4096u,&physical));
        assert(!comp_wba_recording_product_capability(&product_rec,capability));
        assert(!comp_wba_recording_product_prepare(&product_rec,502u,1u,0u,82u));
        product_tick();
    }
    assert(product_rec.ready&&product_rec.media_ready&&product_rec.pipeline.state==COMP_PIPE_IDLE&&
        !product_rec.pipeline.engine_bound&&comp_wba_recording_product_space_current(&product_rec));
    assert(!mic&&mic_starts==starts&&f.erases==erases&&
        !memcmp(before,f.bytes+DATA_BASE+old.extent_offset,sizeof(before)));
    assert(product_rec.last_fault==COMP_WBA_RECORDING_FAULT_PCM_OVERFLOW);
    assert(product_rec.space.logical==1u&&product_rec.space.unsynced==1u&&!product_rec.space.writing);
    comp_segment_entry_t recovered_entry=product_entry(0u);
    assert(recovered_entry.descriptor.session_id==501u&&recovered_entry.descriptor.recording_id==old.descriptor.recording_id&&
        recovered_entry.descriptor.format_epoch==old.descriptor.format_epoch&&
        !memcmp(recovered_entry.descriptor.device_uid,old.descriptor.device_uid,12u)&&
        (recovered_entry.descriptor.flags&COMP_REC_V2_RECOVERED)&&recovered_entry.descriptor.sample_count>0u);
    companion_sha256_t hash;companion_sha256_init(&hash);uint8_t digest[32];uint32_t total=0u;
    comp_segment_audio_port_t audio=comp_wba_segment_storage_audio_port(&product_rec.storage);
    for(uint32_t page=0u;total<recovered_entry.descriptor.encoded_length;page++) {
        uint8_t bytes[256],n;
        assert(comp_segment_audio_read_page(&audio,&recovered_entry,DATA_BASE,page,bytes,&n)==COMP_SEG_OK);
        /* A committed physical page can end in a torn logical packet. Only
         * the complete recovered COP1 prefix belongs to its descriptor/SHA. */
        if(n>recovered_entry.descriptor.encoded_length-total)
            n=(uint8_t)(recovered_entry.descriptor.encoded_length-total);
        companion_sha256_update(&hash,bytes,n);total+=n;
    }
    companion_sha256_final(&hash,digest);
    assert(total==recovered_entry.descriptor.encoded_length&&!memcmp(digest,recovered_entry.descriptor.sha256,32u));
    uint32_t physical;
    assert(comp_wba_recording_product_workspace(&product_rec,4096u,&physical));
    assert(comp_wba_recording_product_workspace(&product_rec,0u,&physical));product_refresh_space();
    product_ready_capture(502u,82u);
    assert(product_rec.last_fault==COMP_WBA_RECORDING_FAULT_NONE&&mic_starts==starts+1u);
    assert(comp_wba_recording_product_control(&product_rec,false,82u));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED&&!mic);
    printf("PASS_RUNTIME_RECOVERY schema=%u ticks=%u durablePrefix=%lu SHA/identity/extent retained; no-auto-start; next-record+OTA-workspace usable\n",
        timeline?3u:1u,ticks,(unsigned long)total);
}
static void corrupt_retained(void)
{
    stopped_overflow(false);comp_segment_entry_t old=product_entry(0u);
    uint32_t at=DATA_BASE+old.extent_offset;
    f.bytes[at+37u]^=1u; /* Deliberate model media corruption, not a real NOR write. */
    uint8_t before[4096];memcpy(before,f.bytes+at,sizeof(before));unsigned erases=f.erases;
    assert(comp_wba_recording_product_recover_begin(&product_rec));
    for(unsigned i=0u;i<30000u&&comp_wba_recording_product_state(&product_rec)!=COMP_WBA_RECORDING_FAULT;i++)product_tick();
    assert(comp_wba_recording_product_state(&product_rec)==COMP_WBA_RECORDING_FAULT&&
        !product_rec.ready&&product_rec.media_ready&&comp_wba_recording_product_readable(&product_rec)&&
        !mic&&f.erases==erases&&
        !memcmp(before,f.bytes+at,sizeof(before)));
    assert(!comp_wba_recording_product_recover_begin(&product_rec));
    assert(product_entry(0u).state==COMP_SEG_WRITING);
    puts("PASS_CORRUPTION_RETAINED unresolved prefix remains FAULT/owned; intact readers stay available; no erase/auto-retry/fabricated saved result");
}
static void discard_owner_prevents_recovery(void)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    product_ready_capture(901u,191u);
    for(unsigned block=0u;block<14u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<160u;i++)product_tick();
    }
    assert(comp_wba_recording_product_control(&product_rec,false,191u));
    for(unsigned i=0;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED&&!mic&&product_rec.pipeline.engine_bound);
    comp_segment_entry_t original=product_entry(0u);uint8_t before[4096];
    memcpy(before,f.bytes+DATA_BASE+original.extent_offset,sizeof(before));
    assert(comp_wba_recording_pipeline_discard_acquire(&product_rec.pipeline));
    comp_wba_recording_product_fault(&product_rec,COMP_WBA_RECORDING_FAULT_DEADLINE);
    assert(product_rec.pipeline.state==COMP_PIPE_FAILED&&product_rec.pipeline.discard_exclusive);
    unsigned writes=f.writes,erases=f.erases;
    bool accepted=comp_wba_recording_product_recover_begin(&product_rec);
    printf("discard recovery admission=%u still_locked=%u ready=%u\n",(unsigned)accepted,
        (unsigned)product_rec.pipeline.discard_exclusive,(unsigned)product_rec.ready);
    assert(!accepted&&product_rec.pipeline.discard_exclusive&&product_rec.ready);
    assert(f.writes==writes&&f.erases==erases);
    assert(comp_wba_recording_pipeline_discard_release(&product_rec.pipeline));
    assert(comp_wba_recording_product_recover_begin(&product_rec));
    for(unsigned i=0;i<30000u&&!product_rec.ready;i++)product_tick();
    assert(product_rec.ready&&!mic&&product_rec.pipeline.state==COMP_PIPE_IDLE);
    comp_segment_entry_t after=product_entry(0u);
    assert(after.descriptor.recording_id==original.descriptor.recording_id&&
        !memcmp(after.descriptor.sha256,original.descriptor.sha256,32u)&&
        !memcmp(before,f.bytes+DATA_BASE+original.extent_offset,sizeof(before)));
    puts("PASS_RECOVERY_REFUSES_DISCARD_OWNER_THEN_RECOVERS; SOFTWARE ONLY");
}
static void repeated_product_fault_preserves_retry_limit(void)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    product_ready_capture(902u,192u);fail_mic_stops=100u;
    comp_wba_recording_product_fault(&product_rec,COMP_WBA_RECORDING_FAULT_DEADLINE);
    assert(mic&&product_rec.pipeline.state==COMP_PIPE_FAILED);
    unsigned reads=f.reads,writes=f.writes,erases=f.erases;
    for(unsigned i=0;i<200u;i++) {
        comp_wba_recording_product_fault(&product_rec,COMP_WBA_RECORDING_FAULT_PLATFORM_CAPTURE);
        product_tick();
    }
    printf("repeat fault mic=%u attempts_left=%u retries=%u first_fault=%u\n",(unsigned)mic,
        fail_mic_stops,(unsigned)product_rec.pipeline.fault_stop_attempts,(unsigned)product_rec.last_fault);
    assert(mic&&product_rec.pipeline.fault_stop_attempts==3u&&fail_mic_stops==96u);
    assert(product_rec.last_fault==COMP_WBA_RECORDING_FAULT_DEADLINE);
    assert(f.reads==reads&&f.writes==writes&&f.erases==erases);
    puts("PASS_REPEATED_PRODUCT_FAULT_BOUNDED_STOP_AND_FIRST_CAUSE; SOFTWARE ONLY");
}
int main(void)
{
    setvbuf(stdout,NULL,_IONBF,0);
    repeated_product_fault_preserves_retry_limit();discard_owner_prevents_recovery();exclusion_guards();recover_prefix(false);recover_prefix(true);corrupt_retained();
    printf("RECOVERY_SOFTWARE_ONLY product_owner_bytes=%zu real-mic/low-frequency/Type/BLE/power NOT_QUALIFIED\n",sizeof(product_rec));
    return 0;
}
