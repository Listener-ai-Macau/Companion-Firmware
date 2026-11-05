#include "../wba_pdm_capture.h"
#include "../wba_dual_mic_probe.h"
#define main existing_pdm_test_main
#include "test_wba_pdm_capture.c"
#undef main

typedef struct {
    pcm_sink_t mono;
    int16_t pairs[TEST_MAX_FRAMES*320u];
    size_t pair_frames;
} pair_sink_t;
static void pair_callback(void *context,const int16_t *pairs,size_t frames,uint32_t rate)
{
    pair_sink_t *s=context;
    CHECK(frames==160u&&rate==16000u&&s->pair_frames<TEST_MAX_FRAMES);
    if(s->pair_frames<TEST_MAX_FRAMES)memcpy(s->pairs+320u*s->pair_frames++,pairs,640u);
}
static uint32_t random_state=0x718e13u;
static uint32_t rnd(void)
{random_state^=random_state<<13;random_state^=random_state>>17;random_state^=random_state<<5;return random_state;}

static void verified_pairs(void)
{
    const size_t bytes=160u*96u/8u*2u;
    for(size_t n=0;n<bytes;++n)raw_lr_msb[n]=(uint8_t)rnd();
    pair_sink_t s={0};pcm_sink_t ls={0},rs={0};comp_wba_pdm_capture_t pair,left,right;
    int16_t storage[322];storage[320]=1234;storage[321]=-5678;
    comp_wba_pdm_config_t cfg=make_config(&s.mono,96u,COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES,
        COMP_WBA_PDM_MSB_FIRST,COMP_WBA_PDM_OUTPUT_LEFT);
    cfg.context=&s;
    cfg.selected_only=true;cfg.observe_pair_frame=pair_callback;cfg.pair_pcm_storage=storage;cfg.pair_pcm_capacity=320u;
    comp_wba_pdm_capture_init(&pair,&cfg);CHECK(comp_wba_pdm_capture_ready(&pair));
    CHECK(comp_wba_pdm_capture_channel_mask(&pair)==3u);
    cfg.observe_pair_frame=NULL;cfg.pair_pcm_storage=NULL;cfg.pair_pcm_capacity=0;cfg.context=&ls;
    comp_wba_pdm_capture_init(&left,&cfg);cfg.output=COMP_WBA_PDM_OUTPUT_RIGHT;cfg.context=&rs;
    comp_wba_pdm_capture_init(&right,&cfg);
    dma_reader_t reader={0};reader.raw=raw_lr_msb;reader.raw_bytes=bytes;reader.fail_at=SIZE_MAX;
    CHECK(comp_wba_pdm_capture_read_frame(&pair,copy_dma_chunk,&reader,bytes,1u,true));
    CHECK(comp_wba_pdm_capture_read_frame(&left,copy_dma_chunk,&reader,bytes,1u,true));
    CHECK(comp_wba_pdm_capture_read_frame(&right,copy_dma_chunk,&reader,bytes,1u,true));
    CHECK(s.pair_frames==0u&&s.mono.frames==0u);
    CHECK(comp_wba_pdm_capture_read_frame(&pair,copy_dma_chunk,&reader,bytes,2u,false));
    CHECK(comp_wba_pdm_capture_read_frame(&left,copy_dma_chunk,&reader,bytes,2u,false));
    CHECK(comp_wba_pdm_capture_read_frame(&right,copy_dma_chunk,&reader,bytes,2u,false));
    CHECK(s.pair_frames==1u&&s.mono.frames==1u);
    for(size_t n=0;n<160u;++n){CHECK(s.pairs[2*n]==ls.samples[n]);CHECK(s.pairs[2*n+1]==rs.samples[n]);CHECK(s.mono.samples[n]==ls.samples[n]);}
    CHECK(storage[320]==1234&&storage[321]==-5678);
    reader.fail_at=bytes-256u;
    CHECK(!comp_wba_pdm_capture_read_frame(&pair,copy_dma_chunk,&reader,bytes,3u,false));
    CHECK(s.pair_frames==1u&&s.mono.frames==1u&&pair.pcm_frame_count==0u);
    reader.fail_at=SIZE_MAX;s.mono.reject=true;
    CHECK(!comp_wba_pdm_capture_read_frame(&pair,copy_dma_chunk,&reader,bytes,4u,false)||pair.stats.pcm_frames_rejected>0);
    CHECK(s.pair_frames==1u);
    s.mono.reject=false;CHECK(comp_wba_pdm_capture_read_frame(&pair,copy_dma_chunk,&reader,bytes,5u,false));
    CHECK(s.pair_frames==2u);
    cfg.observe_pair_frame=pair_callback;cfg.pair_pcm_storage=storage;cfg.pair_pcm_capacity=319u;
    comp_wba_pdm_capture_init(&pair,&cfg);CHECK(!comp_wba_pdm_capture_ready(&pair));
    cfg.pair_pcm_capacity=320u;cfg.observe_pair_frame=NULL;
    comp_wba_pdm_capture_init(&pair,&cfg);CHECK(!comp_wba_pdm_capture_ready(&pair));
}

static int16_t synthetic[32000u*2u];
static comp_wba_dual_mic_probe_t probe;
static void exact_probe(void)
{
    for(size_t n=0;n<32000u*2u;++n)synthetic[n]=(int16_t)((int)(rnd()%50001u)-25000);
    comp_wba_dual_probe_reset(&probe);
    for(size_t n=0;n<32000u;n+=160u)comp_wba_dual_probe_add(&probe,synthetic+2u*n,160u);
    CHECK(probe.samples==32000u&&probe.count==31994u&&!probe.invalid);
    int64_t sum=0;uint64_t sq=0;
    for(size_t n=3;n<31997u;++n){int64_t v=synthetic[2u*n];sum+=v;sq+=(uint64_t)(v*v);}
    CHECK(sum==probe.left_sum&&sq==probe.left_square);
    for(int lag=-3;lag<=3;++lag){
        int64_t cross=0,rs=0;uint64_t rss=0;
        for(int n=3;n<31997;++n){int64_t l=synthetic[2*n],r=synthetic[2*(n+lag)+1];cross+=l*r;rs+=r;rss+=(uint64_t)(r*r);}
        CHECK(cross==probe.cross[lag+3]&&rs==probe.right_sum[lag+3]&&rss==probe.right_square[lag+3]);
    }
    comp_wba_dual_mic_probe_t saved=probe;
    comp_wba_dual_probe_add(&probe,synthetic,160u);CHECK(!memcmp(&saved,&probe,sizeof(probe)));
    comp_wba_dual_probe_reset(&probe);comp_wba_dual_probe_add(&probe,synthetic,160u);
    comp_wba_dual_probe_invalidate(&probe);saved=probe;comp_wba_dual_probe_add(&probe,synthetic+320u,160u);
    CHECK(!memcmp(&saved,&probe,sizeof(probe))&&probe.invalid);
}

static void write_synthetic_probe(void)
{
    int32_t old0=0,old1=0,old2=0;
    for(size_t n=0;n<32000u;++n){
        int32_t value=(int32_t)(((int64_t)old0*85+(int32_t)(rnd()%20001u)-10000)/100);
        synthetic[2u*n]=(int16_t)value;
        synthetic[2u*n+1u]=(int16_t)(((old1+old2)*3)/8); /* known1.5sample delay,0.75gain */
        old2=old1;old1=value;old0=value;
    }
    comp_wba_dual_probe_reset(&probe);comp_wba_dual_probe_add(&probe,synthetic,32000u);
    FILE *f=fopen("synthetic-probe.log","wb");CHECK(f!=NULL);if(!f)return;
    fprintf(f,"SYNTHETIC_ONLY not a physical microphone capture\n");
    fprintf(f,"DMIC1 schema=1 token=77 samples=%u count=%u invalid=%u clip_l=%u clip_r=%u ls_hi=%d ls_lo=%u lss_hi=%u lss_lo=%u\n",
        probe.samples,probe.count,probe.invalid,probe.clipped_left,probe.clipped_right,
        (int32_t)((uint64_t)probe.left_sum>>32),(uint32_t)probe.left_sum,(uint32_t)(probe.left_square>>32),(uint32_t)probe.left_square);
    for(int lag=-3;lag<=3;++lag){unsigned k=(unsigned)(lag+3);
        fprintf(f,"DMIC1 lag=%d rs_hi=%d rs_lo=%u rss_hi=%u rss_lo=%u cross_hi=%d cross_lo=%u\n",lag,
            (int32_t)((uint64_t)probe.right_sum[k]>>32),(uint32_t)probe.right_sum[k],(uint32_t)(probe.right_square[k]>>32),(uint32_t)probe.right_square[k],
            (int32_t)((uint64_t)probe.cross[k]>>32),(uint32_t)probe.cross[k]);}
    CHECK(fclose(f)==0);
}
int main(void)
{
    verified_pairs();exact_probe();write_synthetic_probe();
    if(failures)return 1;
    puts("PASS_SYNCHRONOUS_PAIR_COMMIT_AND_FINITE_PROBE independent lag sums, bounds, priming/stale/reject and bit-identical mono; synthetic only");
    return 0;
}
