#define COMP_PRODUCT_TEST_MAIN prior_product_main
#include "test_wba_recording_product.c"
_Static_assert(sizeof(comp_wba_recording_space_t)==72u,"gap cache must reuse original SRAM");
static void pure_placement_capacity_and_rotation(void)
{
    unsigned cases=0u;
    for(uint32_t residue=0u;residue<8u;residue++)for(uint32_t stride=8u;stride<=72u;stride+=2u)
    for(uint32_t slots=1u;slots<=12u;slots++)for(uint32_t slack=0u;slack<stride&&slack<8u;slack++)
    for(uint32_t hint=0u;hint<slots;hint++) {
        uint32_t extent=stride*4096u,gap=residue*4096u,size=(slots*stride+slack)*4096u,candidate=UINT32_MAX;
        bool possible=false;
        for(uint32_t at=gap;at<=gap+size-extent;at+=4096u)if(at%32768u==0u&&
            (at-gap)/extent+(gap+size-at-extent)/extent+1u==slots){possible=true;break;}
        bool found=comp_segment_reserve_aligned_hint(0u,gap,size,extent,gap+hint*extent,&candidate);
        assert(found==possible);
        if(found)assert(candidate>=gap&&candidate+extent<=gap+size&&candidate%32768u==0u&&
            (candidate-gap)/extent+(gap+size-candidate-extent)/extent+1u==slots);
        else assert(candidate==UINT32_MAX);
        cases++;
    }
    uint32_t at=0u;
    assert(!comp_segment_reserve_aligned_hint(0u,28672u,1892352u,270336u,28672u,&at));
    assert(!comp_segment_reserve_aligned_hint(0u,28672u,270336u,270336u,28672u,&at));
    uint32_t previous=UINT32_MAX;unsigned distinct=0u;
    for(uint32_t slot=0;slot<8u;slot++){
        assert(comp_segment_reserve_aligned_hint(0u,0u,8u*65536u,65536u,slot*65536u,&at));
        assert(at==slot*65536u);if(at!=previous)distinct++;previous=at;
    }
    assert(distinct==8u);
    printf("PASS_ALIGNMENT_PLACEMENT cases=%u actual_largest_gap_zero_slack_refused=1 one_extent_capacity_counterexample_preserved=1 rotated_slots=8\n",cases);
}
static void geometry_fresh(void)
{
    reset();nor=make();f.automatic_erase=true;mic=false;mic_starts=mic_stops=reports=fail_mic_stops=0u;
    nor.info.erase_32k_supported=true;
    comp_wba_pipeline_config_t cfg={0};cfg.microphone=microphone;cfg.now_ms=now;
    cfg.segment_frames=1500u;cfg.extent_bytes=65536u;
    assert(comp_wba_recording_product_bind(&product_rec,&nor,0u,24576u,DATA_BASE,327680u,
        49152u,device_uid,7u,&cfg,product_report));
    product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
}
static void occupied(uint32_t offset,uint32_t bytes,uint64_t session)
{
    comp_segment_entry_t e={0};e.state=COMP_SEG_WRITING;e.extent_offset=offset;e.reserved_bytes=bytes;
    e.descriptor.recording_id=product_rec.catalog.next_id;e.descriptor.format_epoch=7u;e.descriptor.session_id=session;
    e.descriptor.codec=3u;e.descriptor.source_mode=2u;memcpy(e.descriptor.device_uid,device_uid,12u);
    assert(comp_segment_catalog_put_begin(&product_rec.catalog,&e)==COMP_SEG_PENDING);
    comp_segment_result_t r=COMP_SEG_PENDING;
    for(unsigned i=0;i<10000u&&r==COMP_SEG_PENDING;i++){f.now+=2u;r=comp_wba_segment_storage_catalog_poll(&product_rec.storage,&product_rec.catalog);}
    assert(r==COMP_SEG_OK);memset(f.bytes+DATA_BASE+offset,0xa5,bytes);
}
static void arrange(bool aligned)
{
    geometry_fresh();occupied(0u,4096u,501u);
    uint32_t second=aligned?163840u:159744u;
    uint32_t end=aligned?233472u:225280u;
    occupied(135168u,second-135168u,502u);occupied(end,327680u-end,503u);
    product_refresh_space();
    assert(product_rec.space.largest_gap==131072u&&product_rec.space.largest_gap_offset==4096u&&product_rec.space.allocatable_segments==3u);
}
static void prepare_and_cancel(bool aligned)
{
    assert(comp_wba_recording_product_prepare(&product_rec,601u,1u,0u,901u));
    for(unsigned i=0;i<20000u&&!comp_wba_recording_product_ready(&product_rec,901u);i++)product_tick();
    assert(comp_wba_recording_product_ready(&product_rec,901u));
    uint32_t offset=product_rec.capture.engine.active.extent_offset;
    assert((offset+DATA_BASE)%32768u==(aligned?0u:4096u));
    if(aligned)assert(offset==163840u);else assert(offset>=4096u&&offset+65536u<=135168u);
    for(unsigned i=0;i<4096u;i++)assert(f.bytes[DATA_BASE+i]==0xa5);
    assert(f.bytes[DATA_BASE+135168u]==0xa5&&f.bytes[DATA_BASE+327679u]==0xa5);
    assert(comp_wba_recording_product_control(&product_rec,false,901u));
    for(unsigned i=0;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED&&!mic&&!mic_starts&&!product_rec.capture.engine.encoder_owned);
}
static void actual_product_gap_cache(void)
{
    arrange(true);assert(product_rec.space.aligned_gap.offset==163840u&&product_rec.space.aligned_gap.bytes==69632u);
    prepare_and_cancel(true);product_refresh_space();assert(product_rec.space.allocatable_segments==3u);
    arrange(false);assert(!product_rec.space.aligned_gap.bytes);prepare_and_cancel(false);
    arrange(true);occupied(163840u,69632u,504u);
    assert(!comp_wba_recording_product_space_current(&product_rec));product_refresh_space();
    assert(!product_rec.space.aligned_gap.bytes&&product_rec.space.allocatable_segments==2u);
    prepare_and_cancel(false);
    puts("PASS_PRODUCT_ALIGNMENT real_NOR_Opus_owner=1 smaller_aligned_gap_selected=1 largest_gap_report_unchanged=1 all_whole_slots_preserved=1 no_aligned_fallback_original=1 stale_generation_cache_invalidated=1 protected_neighbors_unchanged=1 no_MIC=1 original_space_SRAM72B=1");
}
int main(void){pure_placement_capacity_and_rotation();actual_product_gap_cache();return 0;}
