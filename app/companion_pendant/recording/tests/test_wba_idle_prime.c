/* Full production allocator/NOR/Opus ports; no physical timing claim. */
#define COMP_PRODUCT_TEST_MAIN idle_prime_fixture_main
#include "test_wba_recording_product.c"

#define PRIME_EXTENT 270336u
#define PRIME_ARENA (PRIME_EXTENT*2u+4096u)
static void fresh_prime(void)
{
    reset();nor=make();f.automatic_erase=true;mic=false;mic_starts=mic_stops=reports=fail_mic_stops=0u;
    comp_wba_pipeline_config_t cfg={0};cfg.microphone=microphone;cfg.now_ms=now;
    cfg.segment_frames=6211u;cfg.extent_bytes=PRIME_EXTENT;
    assert(comp_wba_recording_product_bind(&product_rec,&nor,0u,24576u,DATA_BASE,PRIME_ARENA,
        49152u,device_uid,7u,&cfg,product_report));
    product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    memset(f.bytes+DATA_BASE,0x5au,PRIME_ARENA);
}
static void prime_tick(bool allowed)
{f.now+=2u;comp_wba_recording_product_prime(&product_rec,allowed);}
static void prime_ready(void)
{
    for(unsigned i=0u;i<20000u;++i) {
        prime_tick(true);
        if(comp_wba_recording_pipeline_primed(&product_rec.pipeline)&&
           comp_segment_reserve_ready(&product_rec.pipeline.reserve))return;
        if(product_rec.pipeline.state==COMP_PIPE_FAILED) {
            fprintf(stderr,"prime failed: result=%d phase=%u cursor=%u id=%u poisoned=%u erase=%u address=%u bytes=%u\n",
                (int)product_rec.pipeline.failure,product_rec.pipeline.reserve.phase,product_rec.pipeline.reserve.cursor,
                product_rec.pipeline.future.descriptor.recording_id,(unsigned)product_rec.storage.poisoned,
                (unsigned)nor.erase_active,nor.erase_address,nor.erase_bytes);
            assert(!"idle preparation failed");
        }
    }
    assert(!"idle preparation did not finish");
}
static void finish_empty(uint32_t token)
{
    assert(comp_wba_recording_product_control(&product_rec,false,token));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;++i)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED&&!mic&&!product_rec.capture.engine.encoder_owned);
}
static void bind_ready(uint64_t session,uint32_t token)
{
    assert(comp_wba_recording_product_prepare(&product_rec,session,1u,1794180000u,token));
    for(unsigned i=0u;i<20000u&&!comp_wba_recording_product_ready(&product_rec,token);++i)product_tick();
    assert(comp_wba_recording_product_ready(&product_rec,token));
    assert(product_rec.capture.engine.active.descriptor.session_id==session);
    assert(product_rec.capture.engine.active_frame_limit==6211u);
    assert(product_rec.capture.engine.active.reserved_bytes==PRIME_EXTENT);
}
static void full_proof_handoff(void)
{
    fresh_prime();unsigned writes=f.writes;uint32_t generation=product_rec.catalog.generation,id=product_rec.catalog.next_id;
    prime_ready();uint32_t offset=product_rec.pipeline.future.extent_offset;
    assert(f.erases>0u&&f.writes==writes&&product_rec.catalog.generation==generation&&product_rec.catalog.next_id==id);
    assert(!product_rec.pipeline.future.descriptor.recording_id&&!product_rec.catalog.visible_mask&&!mic);
    for(unsigned i=0u;i<PRIME_EXTENT;++i)assert(f.bytes[DATA_BASE+offset+i]==255u);
    comp_segment_entry_t *taken=NULL;
    assert(!comp_segment_reserve_take(&product_rec.pipeline.reserve,&taken));
    unsigned reads=f.reads,erases=f.erases;
    bind_ready(901u,901u);
    assert(f.erases==erases&&f.reads-reads<150u);
    finish_empty(901u);
    product_refresh_space();assert(product_rec.space.allocatable_segments==2u);
    puts("PASS dirty full270336B idle preparation: no phantom catalog/ID, complete proof, real session durable handoff, zero START erase/full rescan,6211-frame capacity retained");
}
static void start_during_erase(void)
{
    fresh_prime();f.automatic_erase=false;
    for(unsigned i=0u;i<20000u&&!nor.erase_active;++i)prime_tick(true);
    assert(nor.erase_active&&!product_rec.pipeline.future.descriptor.recording_id);
    assert(comp_wba_recording_product_prepare(&product_rec,902u,1u,1u,902u));
    assert(product_rec.pipeline.state==COMP_PIPE_PREPARING&&!mic);
    for(unsigned i=0u;i<10u;++i)product_tick();
    assert(!product_rec.pipeline.future.descriptor.recording_id&&!mic);
    complete();f.automatic_erase=true;
    for(unsigned i=0u;i<20000u&&!comp_wba_recording_product_ready(&product_rec,902u);++i)product_tick();
    assert(comp_wba_recording_product_ready(&product_rec,902u)&&!nor.erase_active);
    finish_empty(902u);
    puts("PASS START during physical preparation: original erase retained, no early ID/PCM, complete proof precedes real durable owner");
}
static void cancel_and_workspace(void)
{
    fresh_prime();f.automatic_erase=false;
    for(unsigned i=0u;i<20000u&&!nor.erase_active;++i)prime_tick(true);
    assert(nor.erase_active);unsigned erases=f.erases;uint32_t at=nor.erase_address,bytes=nor.erase_bytes;
    prime_tick(false);assert(nor.erase_active&&f.erases==erases);
    complete();
    for(unsigned i=0u;i<20u&&comp_wba_recording_pipeline_primed(&product_rec.pipeline);++i)prime_tick(false);
    assert(!nor.erase_active&&!comp_wba_recording_pipeline_primed(&product_rec.pipeline)&&f.erases==erases);
    for(uint32_t i=0u;i<PRIME_ARENA;++i)assert(f.bytes[DATA_BASE+i]==
        (DATA_BASE+i>=at&&DATA_BASE+i<at+bytes?255u:0x5au));
    uint32_t physical=0u;
    assert(comp_wba_recording_product_workspace(&product_rec,PRIME_EXTENT,&physical));
    prime_tick(true);assert(!comp_wba_recording_pipeline_primed(&product_rec.pipeline));
    assert(comp_wba_recording_product_workspace(&product_rec,0u,&physical));product_refresh_space();
    f.automatic_erase=true;
    prime_ready();
    assert(comp_wba_recording_pipeline_discard_acquire(&product_rec.pipeline));
    assert(!comp_wba_recording_pipeline_primed(&product_rec.pipeline));
    assert(comp_wba_recording_pipeline_discard_release(&product_rec.pipeline));
    puts("PASS cancel/OTA/discard: only issued chunk retires, no next erase, proof released before workspace or discard, no idle starvation");
}
static void protected_owner(void)
{
    fresh_prime();comp_segment_entry_t e={0};e.state=COMP_SEG_WRITING;e.reserved_bytes=4096u;
    e.descriptor.recording_id=product_rec.catalog.next_id;e.descriptor.session_id=77u;
    e.descriptor.codec=3u;e.descriptor.format_epoch=7u;memcpy(e.descriptor.device_uid,device_uid,12u);
    assert(comp_segment_catalog_put_begin(&product_rec.catalog,&e)==COMP_SEG_PENDING);
    comp_segment_result_t r=COMP_SEG_PENDING;
    while(r==COMP_SEG_PENDING){f.now+=2u;r=comp_wba_segment_storage_catalog_poll(&product_rec.storage,&product_rec.catalog);}
    assert(r==COMP_SEG_OK);product_refresh_space();
    prime_ready();
    for(unsigned i=0u;i<4096u;++i)assert(f.bytes[DATA_BASE+i]==0x5au);
    assert(product_rec.pipeline.future.extent_offset>=4096u);
    assert(product_rec.pipeline.future.reserved_bytes==PRIME_EXTENT);
    /* Changed metadata invalidates a saved free-space proof before reuse. */
    e.descriptor.recording_id=product_rec.catalog.next_id;e.descriptor.session_id=78u;
    e.extent_offset=product_rec.pipeline.future.extent_offset==4096u?4096u+PRIME_EXTENT:4096u;
    assert(comp_segment_catalog_put_begin(&product_rec.catalog,&e)==COMP_SEG_PENDING);r=COMP_SEG_PENDING;
    while(r==COMP_SEG_PENDING){f.now+=2u;r=comp_wba_segment_storage_catalog_poll(&product_rec.storage,&product_rec.catalog);}
    assert(r==COMP_SEG_OK);prime_tick(true);
    assert(!comp_wba_recording_pipeline_primed(&product_rec.pipeline));
    puts("PASS existing WRITING owner protected byte-for-byte; metadata generation change discards idle proof");
}
static void reset_free_preparation(void)
{
    for(unsigned cut=1u;cut<=8u;++cut) {
        fresh_prime();unsigned before=f.writes;uint32_t id=product_rec.catalog.next_id;
        for(unsigned i=0u;i<cut*20u;++i)prime_tick(true);
        if(nor.erase_active)complete();
        /* Volatile coordinator and driver are lost, as after a real reboot;
         * the NOR model's durable catalog and partially erased free data stay. */
        nor=make();
        comp_wba_pipeline_config_t cfg={0};cfg.microphone=microphone;cfg.now_ms=now;
        cfg.segment_frames=6211u;cfg.extent_bytes=PRIME_EXTENT;
        assert(comp_wba_recording_product_bind(&product_rec,&nor,0u,24576u,DATA_BASE,PRIME_ARENA,
            49152u,device_uid,7u,&cfg,product_report));
        product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
        assert(f.writes==before&&product_rec.catalog.next_id==id&&!product_rec.catalog.visible_mask&&!mic);
    }
    puts("PASS eight interrupted idle preparations: remount original catalog, no phantom recording/reservation or metadata write");
}
int main(void)
{
    setvbuf(stdout,NULL,_IONBF,0);
    full_proof_handoff();start_during_erase();cancel_and_workspace();protected_owner();reset_free_preparation();
    return 0;
}
