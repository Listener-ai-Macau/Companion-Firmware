#include "../wba_pdm_capture.h"
#define main old_pdm_suite_main
#include "test_wba_pdm_capture.c"
#undef main
#include <math.h>

static int32_t reference_clamp(int64_t value)
{
    if (value > INT32_MAX) return INT32_MAX;
    if (value < INT32_MIN) return INT32_MIN;
    return (int32_t)value;
}
static uint32_t next_random(uint32_t *state)
{
    *state ^= *state << 13u; *state ^= *state >> 17u; *state ^= *state << 5u;
    return *state;
}
static int32_t reference_delay(const int32_t *samples, size_t now, unsigned delay)
{
    unsigned age = delay / 256u, fraction = delay % 256u;
    int32_t newer = now >= age ? samples[now-age] : 0;
    int32_t older = now > age ? samples[now-age-1u] : 0;
    return (int32_t)(((int64_t)newer * (256u-fraction)+(int64_t)older*fraction)/256);
}
static void check_math(void)
{
    uint32_t random=0x49ab128u;
    int32_t left[80], right[80], trimmed[80];
    for(unsigned i=0u;i<80u;i++) {
        left[i]=(int32_t)next_random(&random);right[i]=(int32_t)next_random(&random);
    }
    left[0]=INT32_MIN;right[1]=INT32_MIN;left[2]=INT32_MAX;right[3]=INT32_MAX;
    for(int delay=-2048;delay<=2048;delay+=16)
    for(unsigned inversion=0u;inversion<2u;inversion++)
    for(unsigned g=0u;g<3u;g++) {
        uint16_t gain=(uint16_t)(g==0u?16384u:g==1u?32768u:65535u);
        comp_wba_dual_mic_t b={0};
        b.config=(comp_wba_dual_mic_config_t){(int16_t)delay,gain,inversion!=0u};
        CHECK(comp_wba_dual_mic_config_valid(&b.config));
        for(unsigned i=0u;i<80u;i++) {
            int64_t v=(int64_t)right[i]*gain/32768;
            trimmed[i]=reference_clamp(inversion?-v:v);
            int64_t l=reference_delay(left,i,delay>0?(unsigned)delay:0u);
            int64_t r=reference_delay(trimmed,i,delay<0?(unsigned)-delay:0u);
            CHECK(comp_wba_dual_mic_process(&b,left[i],right[i])==(int32_t)((l+r)/2));
        }
        comp_wba_dual_mic_reset(&b);
        for(unsigned i=0u;i<20u;i++)CHECK(comp_wba_dual_mic_process(&b,0,0)==0);
    }
    comp_wba_dual_mic_config_t bad={2049,32768,false};
    CHECK(!comp_wba_dual_mic_config_valid(&bad));bad.delay_q8=-2049;
    CHECK(!comp_wba_dual_mic_config_valid(&bad));bad.delay_q8=0;bad.right_gain_q15=16383;
    CHECK(!comp_wba_dual_mic_config_valid(&bad));CHECK(!comp_wba_dual_mic_config_valid(NULL));
}
static void check_capture(void)
{
    uint32_t random=0x59239abu;
    for(unsigned d=0u;d<3u;d++)for(unsigned layout=0u;layout<2u;layout++)
    for(unsigned order=0u;order<2u;order++) {
        unsigned decimation=d==0u?64u:d==1u?96u:128u;
        size_t bytes=160u*(size_t)decimation/8u*2u;
        for(size_t i=0u;i<bytes;i++)raw_lr_msb[i]=(uint8_t)next_random(&random);
        pcm_sink_t mix={0},dual={0};comp_wba_pdm_capture_t a,b;
        comp_wba_pdm_config_t cfg=make_config(&mix,(uint16_t)decimation,
            (comp_wba_pdm_layout_t)layout,(comp_wba_pdm_bit_order_t)order,COMP_WBA_PDM_OUTPUT_MIX);
        comp_wba_pdm_capture_init(&a,&cfg);
        cfg.output=COMP_WBA_PDM_OUTPUT_BEAMFORM;cfg.selected_only=true;cfg.context=&dual;
        cfg.dual_mic=(comp_wba_dual_mic_config_t){0,32768,false};
        comp_wba_pdm_capture_init(&b,&cfg);
        CHECK(comp_wba_pdm_capture_ready(&b));CHECK(comp_wba_pdm_capture_channel_mask(&b)==3u);
        dma_reader_t reader={0};reader.raw=raw_lr_msb;reader.raw_bytes=bytes;reader.fail_at=SIZE_MAX;
        CHECK(comp_wba_pdm_capture_read_frame(&a,copy_dma_chunk,&reader,bytes,10u,true));
        CHECK(comp_wba_pdm_capture_read_frame(&b,copy_dma_chunk,&reader,bytes,10u,true));
        for(uint32_t seq=11u;seq<14u;seq++) {
            CHECK(comp_wba_pdm_capture_read_frame(&a,copy_dma_chunk,&reader,bytes,seq,false));
            CHECK(comp_wba_pdm_capture_read_frame(&b,copy_dma_chunk,&reader,bytes,seq,false));
        }
        CHECK(mix.frames==3u&&dual.frames==3u);
        CHECK(!memcmp(mix.samples,dual.samples,3u*160u*sizeof(int16_t)));
        CHECK(a.stats.saturated_samples==b.stats.saturated_samples);
        cfg.dual_mic.delay_q8=384;dual.frames=0u;comp_wba_pdm_capture_init(&b,&cfg);
        CHECK(comp_wba_pdm_capture_read_frame(&b,copy_dma_chunk,&reader,bytes,20u,true));
        CHECK(b.dual_mic.write_index==0u); /* 160 samples warmed, not a fresh zero history */
        reader.fail_at=128u;
        CHECK(!comp_wba_pdm_capture_read_frame(&b,copy_dma_chunk,&reader,bytes,21u,false));
        CHECK(dual.frames==0u&&b.pcm_frame_count==0u);
        for(unsigned channel=0u;channel<2u;channel++)for(unsigned i=0u;i<COMP_WBA_DUAL_HISTORY;i++)
            CHECK(b.dual_mic.history[channel][i]==0);
        reader.fail_at=SIZE_MAX;
        CHECK(comp_wba_pdm_capture_read_frame(&b,copy_dma_chunk,&reader,bytes,22u,false));
        CHECK(dual.frames==1u);
        cfg.dual_mic.right_gain_q15=0;comp_wba_pdm_capture_init(&b,&cfg);
        CHECK(!comp_wba_pdm_capture_ready(&b));
    }
}
static void check_noise_model(void)
{
    comp_wba_dual_mic_t b={0};b.config.right_gain_q15=32768u;
    uint32_t random=0xb1492u;uint64_t single_error=0u,dual_error=0u;
    for(unsigned n=0u;n<32000u;n++) {
        int32_t voice=(int32_t)(4000.0*sin(2.0*3.141592653589793*317.0*n/16000.0));
        int32_t nl=(int32_t)(next_random(&random)&2047u)-1024;
        int32_t nr=(int32_t)(next_random(&random)&2047u)-1024;
        int32_t y=comp_wba_dual_mic_process(&b,voice+nl,voice+nr);
        int64_t error=(int64_t)y-voice;
        single_error+=(uint64_t)((int64_t)nl*nl);dual_error+=(uint64_t)(error*error);
    }
    double gain_db=10.0*log10((double)single_error/(double)dual_error);
    CHECK(gain_db>2.7&&gain_db<3.3);
    printf("SYNTHETIC_COHERENT_VOICE_INDEPENDENT_NOISE_GAIN_DB %.6f; NOT_MEASURED_DEVICE\n",gain_db);
    /* Perfectly common noise is not removed: an explicit non-benefit case. */
    comp_wba_dual_mic_reset(&b);
    for(int32_t n=-1000;n<=1000;n++)CHECK(comp_wba_dual_mic_process(&b,n,n)==n);
    /* Known integer arrival difference. Without aligning the desired voice,
     * blindly summing opposite samples would erase it; alignment preserves it. */
    comp_wba_dual_mic_reset(&b);b.config.delay_q8=512;
    for(unsigned n=0u;n<100u;n++) {
        int32_t now=n%4u<2u?10000:-10000;
        int32_t delayed=n<2u?0:(n-2u)%4u<2u?10000:-10000;
        CHECK(comp_wba_dual_mic_process(&b,now,delayed)==delayed);
    }
}
int main(void)
{
    if(old_pdm_suite_main())return 1;
    check_math();check_capture();check_noise_model();
    if(failures)return 2;
    puts("PASS_DUAL_MIC_SOFTWARE_ONLY: calibrated fixed beamformer, original modes, prime/stale/saturation preserved; common noise not suppressed; no physical A/B or wearer identification claim");
    return 0;
}
