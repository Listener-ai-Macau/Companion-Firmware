#include "../wba_segment_pull.h"
#define COMP_BOOT_TEST_MAIN recovery_fixture_main
#include "test_wba_recording_recovery.c"
static comp_wba_segment_pull_t pull;
static comp_wba_recording_transfer_t transfer_window;
static comp_segment_entry_t selected;
static bool foreground,scratch;
static unsigned foreground_calls,foreground_block_call;
static unsigned reject_count;
static uint8_t host_bytes[4096],retry_packet[248];
static uint16_t retry_length;
static uint32_t host_offset;
static bool foreground_available(void *v)
{(void)v;foreground_calls++;return foreground&&foreground_calls!=foreground_block_call;}
static bool page_available(void *v){(void)v;return scratch&&engine.writer.phase==0u;}
static bool host_notify(void *v,const uint8_t *value,uint16_t n)
{
    (void)v;assert(n>=20u&&n<=248u&&value[0]==1u);
    uint32_t bytes=(uint32_t)value[2]|((uint32_t)value[3]<<8u);
    bool final=(value[1]&1u)!=0u;uint32_t header=final?56u:20u;
    assert(n==header+bytes&&value[1]==(final?1u:8u)&&bytes<=(final?192u:224u));
    uint8_t fields[16];comp_rec_put32(fields,selected.descriptor.recording_id);
    comp_rec_put32(fields+4u,comp_rec_get32(value+8u));comp_rec_put32(fields+8u,comp_rec_get32(value+12u));
    comp_rec_put32(fields+12u,selected.descriptor.encoded_length);
    uint32_t crc=~comp_rec_crc_step(comp_rec_crc_step(UINT32_MAX,fields,16u),value+header,bytes);
    assert(comp_rec_get32(value+(final?20u:16u))==crc&&comp_rec_get32(value+4u)==selected.descriptor.recording_id);
    if(final)assert(comp_rec_get32(value+16u)==selected.descriptor.encoded_length&&!memcmp(value+24u,selected.descriptor.sha256,32u));
    if(reject_count) {
        reject_count--;memcpy(retry_packet,value,n);retry_length=n;return false;
    }
    if(retry_length){assert(n==retry_length&&!memcmp(value,retry_packet,n));retry_length=0u;}
    assert(comp_rec_get32(value+12u)==host_offset&&host_offset+bytes<=sizeof(host_bytes));
    memcpy(host_bytes+host_offset,value+header,bytes);host_offset+=bytes;return true;
}
static void init_pull(void)
{
    foreground=scratch=true;host_offset=0u;retry_length=0u;reject_count=0u;memset(host_bytes,0,sizeof(host_bytes));
    foreground_calls=foreground_block_call=0u;
    comp_wba_segment_pull_config_t cfg={&storage,&catalog,&transfer_window,&selected,engine.stage+768u,
        foreground_available,page_available,host_notify,NULL};
    assert(comp_wba_segment_pull_init(&pull,&cfg));
}
static void request_for(const comp_segment_entry_t *e,uint32_t offset,uint8_t request[32])
{
    memset(request,0,32u);request[0]=2u;request[1]=0x21u;request[2]=4u;
    comp_rec_put32(request+4u,e->descriptor.recording_id);comp_rec_put64(request+8u,e->descriptor.format_epoch);
    comp_rec_put64(request+16u,e->descriptor.session_id);comp_rec_put32(request+24u,e->descriptor.segment_index);
    comp_rec_put32(request+28u,offset);
}
static comp_segment_result_t pull_poll(void)
{
    unsigned reads=f.reads;f.now+=2u;comp_segment_result_t result=comp_wba_segment_pull_poll(&pull);
    assert(f.reads-reads<=1u);return result;
}
static void stop_recording(void)
{
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED);
}
static void sealed_capture(void)
{
    init();comp_wba_pipeline_config_t cfg=pipeline.config;cfg.segment_frames=20u;
    assert(comp_wba_recording_pipeline_init(&pipeline,&cfg));ready(55u);
    assert(comp_wba_recording_pipeline_start(&pipeline,91u));
    for(unsigned block=0u;block<36u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u;i++)poll();
    }
    stop_recording();assert(recovered_entry().descriptor.encoded_length==768u);
}
static void transfer_and_resume(void)
{
    sealed_capture();comp_segment_entry_t original=recovered_entry();uint8_t request[32];request_for(&original,0u,request);
    uint8_t expected[768];
    for(unsigned at=0u;at<sizeof(expected);at++)expected[at]=f.bytes[DATA_BASE+original.extent_offset+256u+(at/248u)*256u+at%248u];
    init_pull();unsigned reads=f.reads;
    assert(comp_wba_segment_pull_begin(&pull,request)==COMP_SEG_BAD_STATE&&f.reads==reads);
    uint8_t wrong_uid[12];memcpy(wrong_uid,device_uid,12u);wrong_uid[0]^=1u;
    assert(!comp_wba_segment_pull_peer(&pull,wrong_uid,7u,true)&&!comp_wba_segment_pull_peer(&pull,device_uid,8u,true));
    assert(comp_wba_segment_pull_peer(&pull,device_uid,7u,true));
    assert(comp_wba_segment_pull_begin(&pull,request)==COMP_SEG_PENDING);
    reject_count=1u;
    for(unsigned i=0u;i<1000u&&host_offset==0u;i++)assert(pull_poll()==COMP_SEG_PENDING);
    assert(host_offset==224u&&transfer_window.stats.notify_backpressure==1u&&transfer_window.next_offset==224u);
    /* Disconnect only the transient reader; verified host bytes survive. */
    uint32_t generation=catalog.generation;
    assert(!comp_wba_segment_pull_peer(&pull,NULL,0u,false)&&catalog.generation==generation);
    assert(comp_wba_segment_pull_peer(&pull,device_uid,7u,true));
    request_for(&original,host_offset,request);assert(comp_wba_segment_pull_begin(&pull,request)==COMP_SEG_PENDING);
    for(unsigned i=0u;i<1000u&&pull.copied==0u;i++)assert(pull_poll()==COMP_SEG_PENDING);
    assert(pull.copied==24u&&host_offset==224u);
    scratch=false;reads=f.reads;
    for(unsigned i=0u;i<3u;i++)assert(pull_poll()==COMP_SEG_PENDING&&f.reads==reads&&pull.copied==24u);
    scratch=true;memset(pull.config.page,0xa5u,256u); /* scratch is never retained */
    /* Preparing/starting another session changes catalog generation while a
     * radio packet is half-assembled. The old sealed proof must be rechecked;
     * the capture owner and packet bytes keep their independent lifetimes. */
    ready(56u);assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    for(unsigned block=0u;block<6u;block++) {
        int16_t samples[160];pcm(block+100u,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u;i++) {
            poll();comp_segment_result_t result=pull_poll();assert(result==COMP_SEG_PENDING||result==COMP_SEG_OK);
        }
    }
    assert(host_offset==768u&&!memcmp(expected,host_bytes,sizeof(expected))&&mic&&engine.stats.accepted_pcm_blocks==6u);
    assert(comp_wba_recording_transfer_acknowledge(&transfer_window,original.descriptor.recording_id,
        original.descriptor.encoded_length,original.descriptor.sha256)==COMP_WBA_RECORDING_TRANSFER_BAD_STATE);
    stop_recording();
    puts("PASS segmented pull over existing compact224/finalSHA framing: two-page slices, exact backpressure retry, scratch/capture yield, metadata-generation recheck and verified-offset reconnect; real Opus/NOR software only");
}
static void recovered_clip(void)
{
    partial_capture();reboot();finish_recovery();comp_segment_entry_t e=recovered_entry();
    assert(e.descriptor.encoded_length==222u);uint8_t expected[222];memcpy(expected,f.bytes+DATA_BASE+256u,222u);
    init_pull();assert(comp_wba_segment_pull_peer(&pull,device_uid,7u,true));uint8_t request[32];request_for(&e,0u,request);
    assert(comp_wba_segment_pull_begin(&pull,request)==COMP_SEG_PENDING);comp_segment_result_t result=COMP_SEG_PENDING;
    for(unsigned i=0u;i<1000u&&result==COMP_SEG_PENDING;i++)result=pull_poll();
    assert(result==COMP_SEG_OK&&host_offset==222u&&!memcmp(expected,host_bytes,222u));
    request_for(&e,0u,request);comp_rec_put64(request+16u,e.descriptor.session_id+1u);
    assert(comp_wba_segment_pull_begin(&pull,request)==COMP_SEG_PENDING);unsigned before=f.writes;
    result=COMP_SEG_PENDING;for(unsigned i=0u;i<1000u&&result==COMP_SEG_PENDING;i++)result=pull_poll();
    assert(result==COMP_SEG_BAD_ARGUMENT&&f.writes==before);
    puts("PASS recovered prefix pull: physical248B page exposes only verified222B complete COP1 prefix; wrong logical session rejects without media writes; software only");
}
static void selection_admission_race(void)
{
    sealed_capture();comp_segment_entry_t original=recovered_entry();uint8_t request[32];
    request_for(&original,224u,request);init_pull();host_offset=224u;
    assert(comp_wba_segment_pull_peer(&pull,device_uid,7u,true));
    assert(comp_wba_segment_pull_begin(&pull,request)==COMP_SEG_PENDING);
    /* Selection is admitted, then capture gains priority before start. */
    foreground_block_call=2u;unsigned reads=f.reads;
    assert(comp_wba_segment_pull_select_poll(&pull)==COMP_SEG_PENDING);
    assert(f.reads-reads==1u&&transfer_window.last_result==COMP_WBA_RECORDING_TRANSFER_BUSY);
    assert(transfer_window.state==COMP_WBA_RECORDING_TRANSFER_IDLE&&pull.request.byte_offset==224u);
    assert(selected.descriptor.recording_id==original.descriptor.recording_id);
    foreground=false;reads=f.reads;
    for(unsigned i=0u;i<3u;i++)assert(pull_poll()==COMP_SEG_PENDING&&f.reads==reads&&host_offset==224u);
    foreground=true;comp_segment_result_t result=COMP_SEG_PENDING;
    for(unsigned i=0u;i<1000u&&result==COMP_SEG_PENDING;i++)result=pull_poll();
    assert(result==COMP_SEG_OK&&host_offset==original.descriptor.encoded_length);
    for(unsigned at=224u;at<host_offset;at++)
        assert(host_bytes[at]==f.bytes[DATA_BASE+original.extent_offset+256u+(at/248u)*256u+at%248u]);
    assert(transfer_window.stats.busy_rejections>=1u);
    /* A catalog mutation before deferred admission invalidates the proof.
     * Rescan its owner before accepting data, even if start would now fit. */
    request_for(&original,224u,request);init_pull();host_offset=224u;
    assert(comp_wba_segment_pull_peer(&pull,device_uid,7u,true));
    assert(comp_wba_segment_pull_begin(&pull,request)==COMP_SEG_PENDING);
    foreground_block_call=2u;assert(comp_wba_segment_pull_select_poll(&pull)==COMP_SEG_PENDING);
    ready(57u);assert(comp_wba_recording_pipeline_start(&pipeline,91u));
    assert(catalog.generation!=pull.generation);
    /* Change only the requested logical owner: the new scan must reject it. */
    pull.session=original.descriptor.session_id+1u;result=COMP_SEG_PENDING;unsigned writes=f.writes;
    for(unsigned i=0u;i<1000u&&result==COMP_SEG_PENDING;i++)result=pull_poll();
    assert(result==COMP_SEG_BAD_ARGUMENT&&host_offset==224u&&f.writes==writes);
    stop_recording();
    puts("PASS transient capture admission retains original selection/offset; deferred start yields without I/O and revalidates changed catalog ownership; real Opus/NOR software only");
}
static void erase_resume_handoff_yields(void)
{
    init();f.automatic_erase=false;
    assert(companion_spi_nor_stm32wba_erase_step(&nor,DATA_BASE,65536u)==PENDING);
    f.now+=nor.resume_guard_ms;
    assert(companion_spi_nor_stm32wba_erase_suspend_step(&nor)==PENDING);
    f.now+=nor.suspend_wait_ms;
    assert(companion_spi_nor_stm32wba_erase_suspend_step(&nor)==OK);
    assert(companion_spi_nor_stm32wba_erase_resume_step(&nor)==PENDING);
    /* The audio reader wins the next slice before the erase owner qualifies
     * its RESUME. Do not require that owner to run to break the wait cycle. */
    comp_segment_audio_port_t port=comp_wba_segment_storage_audio_port(&storage);
    uint8_t page[256];comp_segment_result_t result=COMP_SEG_PENDING;unsigned slices=0u;
    while(result==COMP_SEG_PENDING&&slices<10u) {
        f.now+=2u;result=port.read(port.context,32768u,page,sizeof(page));slices++;
    }
    assert(result==COMP_SEG_OK&&slices<10u&&nor.erase_active);
    assert(companion_spi_nor_stm32wba_erase_is_suspended(&nor)&&f.erases==1u&&f.resumes==1u&&f.suspends==2u);
    for(unsigned i=0u;i<sizeof(page);i++)assert(page[i]==255u);
    /* The reader may not credit or release the owner's erase completion. */
    complete();assert(companion_spi_nor_stm32wba_erase_suspend_step(&nor)==OK&&nor.erase_active);
    assert(companion_spi_nor_stm32wba_erase_step(&nor,DATA_BASE,65536u)==OK&&!nor.erase_active&&f.erases==1u);
    puts("PASS resumed-erase/audio admission wait cycle resolves in bounded slices; original erase owner/completion preserved without extra erase or premature read; command-level NOR software only");
}
static void sealed_payload_transient_read_fault(bool live_guard)
{
    sealed_capture();comp_segment_entry_t original=recovered_entry();uint8_t request[32];
    request_for(&original,0u,request);init_pull();
    assert(comp_wba_segment_pull_peer(&pull,device_uid,7u,true));
    assert(comp_wba_segment_pull_begin(&pull,request)==COMP_SEG_PENDING);
    for(unsigned i=0u;i<1000u && transfer_window.state==COMP_WBA_RECORDING_TRANSFER_IDLE;i++) {
        comp_segment_result_t r=comp_wba_segment_pull_select_poll(&pull);
        assert(r==COMP_SEG_PENDING||r==COMP_SEG_OK);
    }
    assert(transfer_window.state!=COMP_WBA_RECORDING_TRANSFER_IDLE && !catalog.phase && !nor.erase_active);
    static uint8_t before[COMP_NOR_FIXTURE_BYTES];memcpy(before,f.bytes,sizeof(before));
    unsigned writes=f.writes,erases=f.erases;pull.live=live_guard;f.fail_command=3u;
    comp_segment_result_t r=COMP_SEG_PENDING;
    for(unsigned i=0u;i<1000u && r==COMP_SEG_PENDING;i++)r=pull_poll();
    assert(r==COMP_SEG_IO_ERROR && storage.poisoned && !f.fail_command);
    assert(f.writes==writes && f.erases==erases && !memcmp(before,f.bytes,sizeof(before)));
    /* Header failure remains uncertain even if the release callback succeeds.
     * Only the sealed case can request an idle preflight after owners release. */
    assert(storage.idle_lookup_read_failed==!live_guard);
    puts(live_guard?"PASS_LIVE_UNCERTAIN_READ_STAYS_FAULT; SOFTWARE ONLY":"PASS_SEALED_UNCERTAIN_READ_REQUESTS_IDLE_PREFLIGHT; SOFTWARE ONLY");
}
/* The actual transfer port, not the ordinary capture reader, may read a
 * non-overlapping page after an erase is explicitly suspended. */
static void transfer_during_suspended_erase(void)
{
    init();f.automatic_erase=false;
    assert(companion_spi_nor_stm32wba_erase_step(&nor,DATA_BASE,65536u)==PENDING);
    f.now+=nor.resume_guard_ms;assert(companion_spi_nor_stm32wba_erase_suspend_step(&nor)==PENDING);
    f.now+=nor.suspend_wait_ms;assert(companion_spi_nor_stm32wba_erase_suspend_step(&nor)==OK);
    f.bytes[32768u]=0x53u;uint8_t page[256];unsigned reads=f.reads,writes=f.writes,erases=f.erases;
    comp_segment_audio_port_t port=comp_wba_segment_storage_transfer_audio_port(&storage);
    assert(port.read(port.context,32768u,page,sizeof(page))==COMP_SEG_OK&&page[0]==0x53u);
    assert(f.reads==reads+1u&&f.writes==writes&&f.erases==erases&&nor.erase_active&&!storage.poisoned);
    f.sr1=1u;reads=f.reads;assert(port.read(port.context,32768u,page,sizeof(page))==COMP_SEG_PENDING);
    assert(f.reads==reads&&nor.erase_active&&!storage.poisoned);f.sr1=0u;
    f.fail_read_data_once=true;assert(port.read(port.context,32768u,page,sizeof(page))==COMP_SEG_IO_ERROR);
    assert(storage.transfer_read_released_failure&&!storage.poisoned&&nor.erase_active&&!f.selected);
    assert(port.read(port.context,32768u,page,sizeof(page))==COMP_SEG_OK&&page[0]==0x53u&&nor.erase_active);
    /* Unqualified NOR keeps its original suspended-read behaviour. */
    nor.info.jedec_id=0x0b6018u;assert(port.read(port.context,32768u,page,sizeof(page))==COMP_SEG_OK&&page[0]==0x53u);
    assert(nor.erase_active&&!storage.poisoned&&f.writes==writes&&f.erases==erases);
    puts("PASS transfer reads safely across suspended erase, preserves owner and isolates released read failure; software only");
}
static void directory_during_suspended_erase(void)
{
    sealed_capture();
    uint8_t slot=0u;while(slot<64u&&catalog.slots[slot]==255u)slot++;
    assert(slot<64u&&!catalog.phase&&!nor.erase_active);
    comp_segment_entry_t expected,actual;
    assert(comp_wba_segment_storage_entry(&storage,&catalog,slot,&expected)==COMP_SEG_OK);
    f.automatic_erase=false;
    assert(companion_spi_nor_stm32wba_erase_step(&nor,DATA_BASE+61440u,4096u)==PENDING);
    f.now+=nor.resume_guard_ms;assert(companion_spi_nor_stm32wba_erase_suspend_step(&nor)==PENDING);
    f.now+=nor.suspend_wait_ms;assert(companion_spi_nor_stm32wba_erase_suspend_step(&nor)==OK);
    const unsigned writes=f.writes,erases=f.erases;
    f.fail_read_data_once=true;
    assert(comp_wba_segment_storage_transfer_entry(&storage,&catalog,slot,&actual)==COMP_SEG_PENDING);
    assert(storage.transfer_read_released_failure&&!storage.poisoned&&!catalog.phase&&nor.erase_active&&!f.selected);
    assert(comp_wba_segment_storage_transfer_entry(&storage,&catalog,slot,&actual)==COMP_SEG_OK);
    assert(actual.descriptor.recording_id==expected.descriptor.recording_id&&
           !memcmp(actual.descriptor.sha256,expected.descriptor.sha256,32u));
    assert(f.writes==writes&&f.erases==erases&&nor.erase_active);
    /* A different, unqualified NOR must keep its original failure behavior. */
    nor.info.jedec_id=0x0b6018u;f.fail_read_data_once=true;
    assert(comp_wba_segment_storage_transfer_entry(&storage,&catalog,slot,&actual)==COMP_SEG_IO_ERROR);
    assert(storage.poisoned&&nor.erase_active&&!f.selected);
    puts("PASS suspended erase directory read isolates released payload fault; software only");
}
static void directory_fault_while_recording(void)
{
    sealed_capture();ready(56u);
    assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    uint8_t slot=0u;while(slot<64u&&catalog.slots[slot]==255u)slot++;
    assert(slot<64u&&!catalog.phase&&!nor.erase_active);
    comp_segment_entry_t expected,actual;
    assert(comp_wba_segment_storage_entry(&storage,&catalog,slot,&expected)==COMP_SEG_OK);
    f.automatic_erase=false;
    assert(companion_spi_nor_stm32wba_erase_step(&nor,DATA_BASE+61440u,4096u)==PENDING);
    f.now+=nor.resume_guard_ms;assert(companion_spi_nor_stm32wba_erase_suspend_step(&nor)==PENDING);
    f.now+=nor.suspend_wait_ms;assert(companion_spi_nor_stm32wba_erase_suspend_step(&nor)==OK);
    unsigned writes=f.writes,erases=f.erases;f.fail_read_data_once=true;
    assert(comp_wba_segment_storage_transfer_entry(&storage,&catalog,slot,&actual)==COMP_SEG_PENDING);
    assert(storage.transfer_read_released_failure&&!storage.poisoned&&!catalog.phase&&mic&&nor.erase_active);
    assert(comp_wba_segment_storage_transfer_entry(&storage,&catalog,slot,&actual)==COMP_SEG_OK);
    assert(actual.descriptor.recording_id==expected.descriptor.recording_id&&
           !memcmp(actual.descriptor.sha256,expected.descriptor.sha256,32u));
    assert(f.writes==writes&&f.erases==erases);
    complete();assert(companion_spi_nor_stm32wba_erase_suspend_step(&nor)==OK&&nor.erase_active);
    assert(companion_spi_nor_stm32wba_erase_step(&nor,DATA_BASE+61440u,4096u)==OK&&!nor.erase_active);
    f.automatic_erase=true;
    for(unsigned block=0u;block<20u;block++) {
        int16_t samples[160];pcm(block,samples);assert(mic&&comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u;i++)poll();
    }
    assert(mic&&!storage.poisoned&&engine.stats.overflows==0u);
    stop_recording();
    puts("PASS running recorder survives released directory failure during suspended erase; software only");
}
/* The timeout passed to the actual NOR port must be short for all three
 * read-only reservation phases. The fake models a HAL timeout, not wall time. */
static comp_segment_result_t deferred_read(void *v,uint32_t at,uint8_t *p,uint32_t bytes)
{(void)v;(void)at;(void)p;(void)bytes;return COMP_SEG_PENDING;}
static void audio_verify_read_is_bounded(bool qualified)
{
    init();ready(55u);assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    comp_segment_audio_port_t port=comp_wba_segment_storage_audio_port(&storage);
    uint8_t page[256];unsigned writes=f.writes,erases=f.erases;
    if(!qualified)nor.info.jedec_id=0x0b6018u;
    f.fail_read_data_once=true;f.fail_read_delay_ms=50u;uint32_t started=f.now;
    assert(port.read(port.context,DATA_BASE+61440u,page,sizeof(page))==COMP_SEG_IO_ERROR);
    fprintf(stderr,"audio verify timeout=%lu model_elapsed=%lu ms\n",(unsigned long)f.last_read_timeout,(unsigned long)(f.now-started));
    if(qualified)assert(f.last_read_timeout<=8u&&f.now-started<=8u);
    else assert(f.last_read_timeout==200u&&f.now-started==50u);
    assert(storage.poisoned&&!f.selected&&f.writes==writes&&f.erases==erases);
}
static void writer_verification_failure_does_not_commit(void)
{
    init();ready(55u);assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    for(unsigned block=0u;block<80u&&engine.writer.phase!=6u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u&&engine.writer.phase!=6u;i++)poll();
    }
    assert(engine.writer.phase==6u&&mic); /* page body has been written, not committed */
    comp_segment_audio_t *w=&engine.writer;
    uint32_t commit=w->data_base+w->entry->extent_offset+256u+w->pages*256u+252u;
    assert(commit<sizeof(f.bytes)&&f.bytes[commit]==255u);
    const uint32_t previous=w->committed_bytes;const unsigned writes=f.writes;
    f.fail_read_data_once=true;f.fail_read_delay_ms=50u;uint32_t started=f.now;
    assert(comp_segment_audio_poll(w)==COMP_SEG_IO_ERROR);
    assert(w->failed&&storage.poisoned&&f.last_read_timeout<=8u&&f.now-started<=8u&&
           w->committed_bytes==previous&&f.bytes[commit]==255u&&f.writes==writes&&!f.selected);
    puts("PASS failed bounded verification cannot commit a partial recording page; software only");
}
static void recover_original_after_writer_verify_fault(void)
{
    sealed_capture();comp_segment_entry_t old=recovered_entry();
    assert(old.reserved_bytes<=4096u);
    uint8_t preserved_old[4096];memcpy(preserved_old,f.bytes+DATA_BASE+old.extent_offset,old.reserved_bytes);
    comp_wba_pipeline_config_t cfg=pipeline.config;cfg.segment_frames=50u;
    assert(comp_wba_recording_pipeline_init(&pipeline,&cfg));ready(56u);
    assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    for(unsigned block=0u;block<90u && !(engine.writer.phase==6u && engine.writer.committed_bytes>=248u);block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u && !(engine.writer.phase==6u && engine.writer.committed_bytes>=248u);i++)poll();
    }
    assert(engine.writer.phase==6u&&engine.writer.committed_bytes>=248u&&mic);
    const uint32_t id=engine.active.descriptor.recording_id;
    const uint32_t offset=engine.active.extent_offset;
    uint8_t original_first_page[256];memcpy(original_first_page,f.bytes+DATA_BASE+offset+256u,sizeof(original_first_page));
    f.fail_read_data_once=true;f.fail_read_delay_ms=8u;
    comp_wba_pipeline_state_t state=comp_wba_recording_pipeline_poll(&pipeline);
    for(unsigned i=0u;i<100u&&state!=COMP_PIPE_FAILED;i++)state=comp_wba_recording_pipeline_poll(&pipeline);
    assert(state==COMP_PIPE_FAILED&&!f.fail_read_data_once&&storage.poisoned);
    reboot();finish_recovery();
    assert(!memcmp(preserved_old,f.bytes+DATA_BASE+old.extent_offset,old.reserved_bytes));
    assert(!memcmp(original_first_page,f.bytes+DATA_BASE+offset+256u,sizeof(original_first_page)));
    bool found_old=false,found_original=false;
    for(uint8_t i=0u;i<64u;i++) {
        comp_segment_entry_t got;comp_segment_result_t r=comp_wba_segment_storage_entry(&storage,&catalog,i,&got);
        assert(r==COMP_SEG_OK||r==COMP_SEG_NOT_FOUND);
        if(r!=COMP_SEG_OK)continue;
        if(got.descriptor.recording_id==old.descriptor.recording_id) {
            assert(!memcmp(got.descriptor.sha256,old.descriptor.sha256,32u));found_old=true;
        }
        if(got.descriptor.recording_id==id) {
            fprintf(stderr,"recovered session=%llu encoded=%lu flags=%u\n",(unsigned long long)got.descriptor.session_id,
                    (unsigned long)got.descriptor.encoded_length,(unsigned)got.descriptor.flags);
            /* committed_bytes includes the COP1 framing; encoded_length is
             * the verified complete Opus prefix, not raw page payload size. */
            assert(got.descriptor.session_id==56u&&got.descriptor.encoded_length>0u&&
                   (got.descriptor.flags&COMP_REC_V2_RECOVERED));found_original=true;
        }
    }
    assert(found_old&&found_original);
    puts("PASS page-verify fault recovers committed original prefix without changing earlier recording; software only");
}
static void reserve_reads_are_bounded(unsigned target_phase,bool qualified)
{
    sealed_capture();ready(56u);assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    comp_segment_reserve_t worker={0};comp_segment_entry_t entry={0};entry.state=COMP_SEG_WRITING;
    entry.descriptor.format_epoch=engine.active.descriptor.format_epoch;
    entry.descriptor.session_id=engine.active.descriptor.session_id;entry.descriptor.codec=3u;
    entry.descriptor.source_mode=engine.active.descriptor.source_mode;
    memcpy(entry.descriptor.device_uid,engine.active.descriptor.device_uid,12u);
    entry.descriptor.segment_index=engine.active.descriptor.segment_index+1u;
    entry.descriptor.sample_offset=engine.active.descriptor.sample_offset+(uint64_t)engine.active_frame_limit*320u;
    if(target_phase==4u)f.bytes[DATA_BASE+61440u]=0u; /* force ERASE->VERIFY */
    assert(comp_segment_reserve_begin(&worker,&catalog,&entry,4096u,61440u)==COMP_SEG_PENDING);
    for(unsigned i=0u;i<50000u;i++) {
        if(worker.phase==target_phase && (target_phase!=1u ||
           (worker.scan<64u && catalog.slots[worker.scan]!=255u)))break;
        f.now+=2u;comp_segment_result_t step=comp_wba_segment_storage_reserve_poll(&storage,&worker);
        if(step!=COMP_SEG_PENDING)fprintf(stderr,"prepare target=%u step=%u reserve_phase=%u catalog_phase=%u scan=%u candidate=%lu\n",target_phase,(unsigned)step,(unsigned)worker.phase,(unsigned)catalog.phase,(unsigned)worker.scan,(unsigned long)worker.candidate);
        assert(step==COMP_SEG_PENDING);
    }
    assert(worker.phase==target_phase);
    if(target_phase==1u)assert(worker.scan<64u&&catalog.slots[worker.scan]!=255u);
    uint8_t scan=worker.scan;uint32_t cursor=worker.cursor,candidate=worker.candidate;
    const unsigned writes=f.writes,erases=f.erases;
    assert(comp_segment_reserve_poll_scoped(&worker,deferred_read,NULL)==COMP_SEG_PENDING);
    assert(worker.scan==scan&&worker.cursor==cursor&&worker.candidate==candidate&&
           worker.phase==target_phase&&f.writes==writes&&f.erases==erases);
    if(!qualified)nor.info.jedec_id=0x0b6018u;
    const uint32_t before=f.now;f.fail_read_delay_ms=50u;f.fail_read_data_once=true;
    assert(comp_wba_segment_storage_reserve_poll(&storage,&worker)==COMP_SEG_IO_ERROR);
    fprintf(stderr,"reserve phase=%u timeout=%lu model_elapsed=%lu ms\n",target_phase,
        (unsigned long)f.last_read_timeout,(unsigned long)(f.now-before));
    assert(!f.fail_read_data_once);
    if(qualified)assert(f.last_read_timeout<=8u&&f.now-before<=8u);
    else assert(f.last_read_timeout==200u&&f.now-before==50u);
    assert(storage.poisoned&&mic&&!f.selected&&f.writes==writes&&f.erases==erases);
}
static void recording_survives_suspended_read_failure(void)
{
    init();ready(55u);assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    f.automatic_erase=false;
    assert(companion_spi_nor_stm32wba_erase_step(&nor,32768u,4096u)==PENDING);
    f.now+=nor.resume_guard_ms;assert(companion_spi_nor_stm32wba_erase_suspend_step(&nor)==PENDING);
    f.now+=nor.suspend_wait_ms;assert(companion_spi_nor_stm32wba_erase_suspend_step(&nor)==OK);
    comp_segment_audio_port_t port=comp_wba_segment_storage_transfer_audio_port(&storage);
    uint8_t page[256];unsigned writes=f.writes,erases=f.erases;f.fail_read_data_once=true;
    assert(port.read(port.context,DATA_BASE+32768u,page,sizeof(page))==COMP_SEG_IO_ERROR);
    assert(storage.transfer_read_released_failure&&!storage.poisoned&&mic&&nor.erase_active);
    assert(f.writes==writes&&f.erases==erases);
    assert(port.read(port.context,DATA_BASE+32768u,page,sizeof(page))==COMP_SEG_OK);
    for(unsigned block=0u;block<20u;block++) {
        int16_t samples[160];pcm(block,samples);
        assert(mic&&comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u;i++)poll();
    }
    assert(mic&&!storage.poisoned&&engine.stats.overflows==0u);
    complete();assert(companion_spi_nor_stm32wba_erase_suspend_step(&nor)==OK&&nor.erase_active);
    assert(companion_spi_nor_stm32wba_erase_step(&nor,32768u,4096u)==OK&&!nor.erase_active);
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u)&&!mic);
    for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED&&!storage.poisoned);
    puts("PASS running recorder survives released payload failure during suspended erase and stops normally; software only");
}
static void reserve_fast_read_recovery(unsigned target_phase,unsigned fault_case)
{
    sealed_capture();comp_segment_entry_t old=recovered_entry();
    assert(old.reserved_bytes<=4096u);uint8_t preserved[4096];
    memcpy(preserved,f.bytes+DATA_BASE+old.extent_offset,old.reserved_bytes);
    ready(56u);assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    comp_segment_reserve_t worker={0};comp_segment_entry_t entry={0};entry.state=COMP_SEG_WRITING;
    entry.descriptor.format_epoch=engine.active.descriptor.format_epoch;
    entry.descriptor.session_id=engine.active.descriptor.session_id;entry.descriptor.codec=3u;
    entry.descriptor.source_mode=engine.active.descriptor.source_mode;
    memcpy(entry.descriptor.device_uid,engine.active.descriptor.device_uid,12u);
    entry.descriptor.segment_index=engine.active.descriptor.segment_index+1u;
    entry.descriptor.sample_offset=engine.active.descriptor.sample_offset+(uint64_t)engine.active_frame_limit*320u;
    if(target_phase==4u)f.bytes[DATA_BASE+61440u]=0u;
    assert(comp_segment_reserve_begin(&worker,&catalog,&entry,4096u,61440u)==COMP_SEG_PENDING);
    for(unsigned i=0u;i<50000u;i++) {
        if(worker.phase==target_phase&&(target_phase!=1u||
            (worker.scan<64u&&catalog.slots[worker.scan]!=255u)))break;
        f.now+=2u;assert(comp_wba_segment_storage_reserve_poll(&storage,&worker)==COMP_SEG_PENDING);
    }
    assert(worker.phase==target_phase);
    uint8_t scan=worker.scan;uint32_t cursor=worker.cursor,candidate=worker.candidate;
    unsigned writes=f.writes,erases=f.erases;
    for(unsigned i=0u;i<(fault_case<2u?2u:0u);i++) {
        f.fail_read_delay_ms=0u;f.fail_read_data_once=true;
        assert(comp_wba_segment_storage_reserve_poll(&storage,&worker)==COMP_SEG_PENDING);
        assert(!f.fail_read_data_once&&!storage.poisoned&&mic&&worker.phase==target_phase&&
            worker.scan==scan&&worker.cursor==cursor&&worker.candidate==candidate&&
            f.writes==writes&&f.erases==erases);
    }
    if(fault_case) {
        if(fault_case==1u)f.fail_read_data_once=true;
        else if(fault_case==2u)f.fail_command=3u;
        else f.fail_deassert_once=true;
        assert(comp_wba_segment_storage_reserve_poll(&storage,&worker)==COMP_SEG_IO_ERROR);
        assert(storage.poisoned&&worker.phase!=target_phase);
    } else {
        assert(comp_wba_segment_storage_reserve_poll(&storage,&worker)==COMP_SEG_PENDING||
               worker.phase==5u);
        assert(!storage.poisoned&&mic&&(worker.scan!=scan||worker.cursor!=cursor||worker.phase!=target_phase));
        assert(worker.read_retries==0u);
        if(target_phase==7u&&worker.phase==7u) {
            cursor=worker.cursor;
            f.fail_read_data_once=true;
            assert(comp_wba_segment_storage_reserve_poll(&storage,&worker)==COMP_SEG_PENDING);
            assert(!f.fail_read_data_once&&!storage.poisoned&&worker.cursor==cursor&&worker.read_retries==1u);
            assert(comp_wba_segment_storage_reserve_poll(&storage,&worker)==COMP_SEG_PENDING);
            assert(worker.cursor>cursor&&worker.read_retries==0u);
        }
    }
    assert(!memcmp(preserved,f.bytes+DATA_BASE+old.extent_offset,old.reserved_bytes));
    puts("PASS reserve fast failure retries safely or stops after the retry limit; software only");
}
static uint32_t injected_status_timeout;
static bool delayed_erase_status(void *context,const uint8_t *tx,uint8_t *rx,size_t size,uint32_t timeout)
{
    if(tx && rx && size==2u && tx[0]==5u) {
        injected_status_timeout=timeout;f.now+=timeout<50u?timeout:50u;return false;
    }
    return transfer(context,tx,rx,size,timeout);
}
static void erase_gate_status_wait_is_bounded(void)
{
    init();f.automatic_erase=false;
    assert(companion_spi_nor_stm32wba_erase_step(&nor,DATA_BASE,65536u)==PENDING);
    f.now+=nor.resume_guard_ms;uint32_t start=f.now,erases=f.erases,writes=f.writes;
    nor.config.transfer=delayed_erase_status;injected_status_timeout=0u;
    comp_segment_audio_port_t port=comp_wba_segment_storage_audio_port(&storage);
    uint8_t page[256];
    assert(port.read(port.context,32768u,page,sizeof(page))==COMP_SEG_IO_ERROR);
    assert(injected_status_timeout==8u && f.now-start==8u && nor.erase_active &&
        storage.poisoned && !f.selected && f.erases==erases && f.writes==writes);
    puts("PASS recording storage gate: simulated first erase-status stall is bounded, owner retained, storage faulted without extra media mutation");
}
static void failed_erase_does_not_stall_gate(void)
{
    init();f.automatic_erase=false;
    assert(companion_spi_nor_stm32wba_erase_step(&nor,DATA_BASE,65536u)==PENDING);
    nor.erase_phase=4u;nor.erase_command_failed=true;
    comp_segment_audio_port_t port=comp_wba_segment_storage_audio_port(&storage);
    uint8_t page[256];unsigned erases=f.erases,writes=f.writes;
    assert(port.read(port.context,32768u,page,sizeof(page))==COMP_SEG_IO_ERROR);
    assert(storage.poisoned&&nor.erase_active&&f.erases==erases&&f.writes==writes);
    puts("PASS failed erase completion reaches storage fault without losing ownership or new media mutation");
}
static bool delayed_erase_command(void *context,const uint8_t *tx,uint8_t *rx,size_t size,uint32_t timeout)
{
    if(tx && !rx && size==4u && (tx[0]==0x20u || tx[0]==0xd8u)) f.now+=5u;
    return transfer(context,tx,rx,size,timeout);
}
static void erase_timeout_starts_after_command(void)
{
    init();f.automatic_erase=false;nor.config.transfer=delayed_erase_command;
    assert(companion_spi_nor_stm32wba_erase_step(&nor,DATA_BASE,65536u)==PENDING);
    assert(nor.erase_active && nor.erase_started_ms==f.now && nor.erase_run_since_ms==f.now && f.erases==1u);
    init();f.automatic_erase=false;nor.config.transfer=delayed_erase_command;f.fail_command=0xd8u;
    assert(companion_spi_nor_stm32wba_erase_step(&nor,DATA_BASE,65536u)==ERROR);
    assert(nor.erase_active && nor.erase_command_failed && nor.erase_started_ms==f.now && nor.erase_run_since_ms==f.now && f.erases==1u);
    assert(companion_spi_nor_stm32wba_erase_step(&nor,DATA_BASE,65536u)==PENDING && f.erases==1u);
    puts("PASS erase timeout and resume guard start after command completion; original owner retained");
}
int main(int argc,char **argv)
{
    if(argc==2&&!strcmp(argv[1],"--erase-start-guard")){erase_timeout_starts_after_command();return 0;}
    if(argc==2&&!strcmp(argv[1],"--failed-erase-owner")){failed_erase_does_not_stall_gate();return 0;}
    if(argc==2&&!strcmp(argv[1],"--erase-gate-budget")){erase_gate_status_wait_is_bounded();return 0;}
    if(argc==2&&!strcmp(argv[1],"--reserve-fast-search")){reserve_fast_read_recovery(1u,0u);return 0;}
    if(argc==2&&!strcmp(argv[1],"--reserve-fast-blank")){reserve_fast_read_recovery(7u,0u);return 0;}
    if(argc==2&&!strcmp(argv[1],"--reserve-fast-verify")){reserve_fast_read_recovery(4u,0u);return 0;}
    if(argc==2&&!strcmp(argv[1],"--reserve-fast-repeat")){reserve_fast_read_recovery(7u,1u);return 0;}
    if(argc==2&&!strcmp(argv[1],"--reserve-fast-header")){reserve_fast_read_recovery(7u,2u);return 0;}
    if(argc==2&&!strcmp(argv[1],"--reserve-fast-release")){reserve_fast_read_recovery(7u,3u);return 0;}
    if(argc==2&&!strcmp(argv[1],"--reserve-search")){reserve_reads_are_bounded(1u,true);return 0;}
    if(argc==2&&!strcmp(argv[1],"--reserve-blank")){reserve_reads_are_bounded(7u,true);return 0;}
    if(argc==2&&!strcmp(argv[1],"--reserve-verify")){reserve_reads_are_bounded(4u,true);return 0;}
    if(argc==2&&!strcmp(argv[1],"--reserve-other")){reserve_reads_are_bounded(1u,false);return 0;}
    if(argc==2&&!strcmp(argv[1],"--audio-verify")){audio_verify_read_is_bounded(true);return 0;}
    if(argc==2&&!strcmp(argv[1],"--audio-other")){audio_verify_read_is_bounded(false);return 0;}
    if(argc==2&&!strcmp(argv[1],"--writer-verify")){writer_verification_failure_does_not_commit();return 0;}
    if(argc==2&&!strcmp(argv[1],"--writer-recover")){recover_original_after_writer_verify_fault();return 0;}
    if(argc==2&&!strcmp(argv[1],"--payload-read-fault")){sealed_payload_transient_read_fault(false);return 0;}
    if(argc==2&&!strcmp(argv[1],"--payload-live-guard")){sealed_payload_transient_read_fault(true);return 0;}
    directory_fault_while_recording();directory_during_suspended_erase();recording_survives_suspended_read_failure();transfer_during_suspended_erase();erase_resume_handoff_yields();selection_admission_race();transfer_and_resume();recovered_clip();return 0;
}
