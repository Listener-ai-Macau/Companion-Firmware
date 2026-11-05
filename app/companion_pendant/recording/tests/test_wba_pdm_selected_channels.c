#define main old_pdm_suite_main
#include "test_wba_pdm_capture.c"
#undef main
int main(void)
{
    if(old_pdm_suite_main())return 1;
    uint32_t random=0x928137u;unsigned cases=0u;
    for(unsigned d=0u;d<3u;d++)for(unsigned mode=0u;mode<3u;mode++)
    for(unsigned layout=0u;layout<2u;layout++)for(unsigned order=0u;order<2u;order++)
    for(unsigned inversion=0u;inversion<4u;inversion++)for(unsigned gain=0u;gain<2u;gain++) {
        uint16_t decimation=(uint16_t)(d==0u?64u:d==1u?96u:128u);
        size_t bytes=160u*(size_t)decimation/8u*2u;
        for(size_t i=0u;i<bytes;i++){random^=random<<13u;random^=random>>17u;random^=random<<5u;raw_lr_msb[i]=(uint8_t)random;}
        pcm_sink_t both={0},selected={0};comp_wba_pdm_capture_t a,b;
        comp_wba_pdm_config_t config=make_config(&both,decimation,(comp_wba_pdm_layout_t)layout,(comp_wba_pdm_bit_order_t)order,(comp_wba_pdm_output_t)mode);
        config.gain_q15=gain?COMP_WBA_PDM_GAIN_Q15_MAX:COMP_WBA_PDM_GAIN_Q15_ONE;
        config.invert_left=(inversion&1u)!=0u;config.invert_right=(inversion&2u)!=0u;
        comp_wba_pdm_capture_init(&a,&config);config.selected_only=true;config.context=&selected;comp_wba_pdm_capture_init(&b,&config);
        CHECK(comp_wba_pdm_capture_channel_mask(&a)==3u);
        CHECK(comp_wba_pdm_capture_channel_mask(&b)==(mode==0u?1u:mode==1u?2u:3u));
        dma_reader_t reader={0};reader.raw=raw_lr_msb;reader.raw_bytes=bytes;reader.fail_at=SIZE_MAX;
        CHECK(comp_wba_pdm_capture_read_frame(&a,copy_dma_chunk,&reader,bytes,10u,true));
        CHECK(comp_wba_pdm_capture_read_frame(&b,copy_dma_chunk,&reader,bytes,10u,true));
        for(uint32_t seq=11u;seq<14u;seq++) {
            CHECK(comp_wba_pdm_capture_read_frame(&a,copy_dma_chunk,&reader,bytes,seq,false));
            CHECK(comp_wba_pdm_capture_read_frame(&b,copy_dma_chunk,&reader,bytes,seq,false));
        }
        CHECK(both.frames==3u&&selected.frames==both.frames);
        CHECK(!memcmp(both.samples,selected.samples,3u*160u*sizeof(int16_t)));
        if(mode==0u)CHECK(!b.channels[1].integrator1&&!b.channels[1].decimation_phase&&!b.stats.right_abs_energy);
        if(mode==1u)CHECK(!b.channels[0].integrator1&&!b.channels[0].decimation_phase&&!b.stats.left_abs_energy);
        CHECK(a.stats.pdm_bits_per_channel==b.stats.pdm_bits_per_channel&&a.stats.raw_bytes==b.stats.raw_bytes);
        /* A stale mid-copy cannot emit a partial selected-channel frame. */
        comp_wba_pdm_capture_reset_stream(&b);selected.frames=0u;reader.fail_at=128u;
        CHECK(!comp_wba_pdm_capture_read_frame(&b,copy_dma_chunk,&reader,bytes,20u,false));
        CHECK(!selected.frames&&!b.pcm_frame_count);
        reader.fail_at=SIZE_MAX;CHECK(comp_wba_pdm_capture_read_frame(&b,copy_dma_chunk,&reader,bytes,21u,false));
        CHECK(selected.frames==1u);cases++;
    }
    if(failures)return 2;
    printf("PASS_SELECTED_PDM_SOFTWARE_ONLY cases=%u selected PCM bit-identical; inactive filter skipped and mask explicit; dual/mix/prime/stale-copy guards preserved; hardware timing NOT_QUALIFIED\n",cases);
    return 0;
}
