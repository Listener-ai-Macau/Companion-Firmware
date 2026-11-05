#include "../wba_microphone_profile.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do { if(!(x)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x);exit(1);} }while(0)
typedef struct { int16_t pcm[320];unsigned samples,frames; } sink_t;
static bool emit(void *ctx,const int16_t *pcm,size_t n,uint32_t rate)
{ sink_t *s=ctx;CHECK(n==160u&&rate==16000u&&s->samples+n<=320u);memcpy(s->pcm+s->samples,pcm,n*sizeof(*pcm));s->samples+=(unsigned)n;++s->frames;return true; }
static void observe(void *ctx,const int16_t *pcm,size_t n,uint32_t rate)
{ (void)ctx;(void)pcm;CHECK(n==160u&&rate==16000u); }
static void init(comp_wba_pdm_capture_t *c,sink_t *s)
{
    comp_wba_pdm_config_t config={0};config.decimation=96u;config.gain_q15=32768u;
    config.output=COMP_WBA_PDM_OUTPUT_LEFT;config.selected_only=true;
    config.emit_pcm_frame=emit;config.context=s;comp_wba_pdm_capture_init(c,&config);
    CHECK(comp_wba_pdm_capture_ready(c));
}
static void refusals(void)
{
    sink_t sink={0};comp_wba_pdm_capture_t c,old;init(&c,&sink);
    comp_wba_dual_mic_config_t measured={384,40000u,true},bad={2049,32768u,false};
    old=c;CHECK(!comp_wba_microphone_profile_select(&c,true,0u,&measured));CHECK(!memcmp(&c,&old,sizeof(c)));
    CHECK(!comp_wba_microphone_profile_select(&c,false,2u,&measured));CHECK(!memcmp(&c,&old,sizeof(c)));
    CHECK(!comp_wba_microphone_profile_select(&c,false,0u,&bad));CHECK(!memcmp(&c,&old,sizeof(c)));
    CHECK(!comp_wba_microphone_profile_select(NULL,false,0u,&measured));
    CHECK(comp_wba_microphone_profile_select(&c,false,0u,NULL));CHECK(c.config.output==COMP_WBA_PDM_OUTPUT_LEFT);
    CHECK(comp_wba_microphone_profile_select(&c,false,0u,&measured));CHECK(c.config.output==COMP_WBA_PDM_OUTPUT_BEAMFORM);
    CHECK(c.dual_mic.config.delay_q8==384&&c.dual_mic.config.invert_right&&c.dual_mic.config.right_gain_q15==40000u);
    CHECK(comp_wba_pdm_capture_channel_mask(&c)==3u);
    CHECK(comp_wba_microphone_profile_select(&c,false,1u,&measured));CHECK(c.config.output==COMP_WBA_PDM_OUTPUT_LEFT);
    CHECK(comp_wba_pdm_capture_channel_mask(&c)==1u);
    int16_t pairs[320];c.config.observe_pair_frame=observe;c.config.pair_pcm_storage=pairs;c.config.pair_pcm_capacity=320u;
    CHECK(comp_wba_microphone_profile_select(&c,false,1u,&measured));CHECK(comp_wba_pdm_capture_channel_mask(&c)==3u);
    puts("PASS atomic refusal, no-calibration baseline, voice/meeting switching, probe retains independent pair");
}
static void actual_pcm(void)
{
    static uint8_t raw_a[3840],raw_b[3840];uint32_t seed=0xa5e9137u;
    for(unsigned i=0u;i<3840u;i+=2u){seed=seed*1664525u+1013904223u;raw_a[i]=raw_b[i]=(uint8_t)(seed>>24u);raw_a[i+1u]=0xffu;raw_b[i+1u]=(uint8_t)(seed>>16u);}
    comp_wba_dual_mic_config_t measured={256,32768u,false};
    sink_t baseline={0},meeting_a={0},meeting_b={0},voice_a={0},voice_b={0};
    comp_wba_pdm_capture_t c[5];sink_t *s[]={&baseline,&meeting_a,&meeting_b,&voice_a,&voice_b};
    for(unsigned i=0u;i<5u;++i){
        init(&c[i],s[i]);if(i)CHECK(comp_wba_microphone_profile_select(&c[i],false,i<3u?1u:0u,&measured));
        const uint8_t *raw=(i==2u||i==4u)?raw_b:raw_a;
        CHECK(comp_wba_pdm_capture_prime(&c[i],raw,3840u,10u));
        CHECK(comp_wba_pdm_capture_ingest(&c[i],raw,3840u,11u));
        CHECK(comp_wba_pdm_capture_ingest(&c[i],raw,3840u,12u));
        CHECK(s[i]->frames==2u&&s[i]->samples==320u&&c[i].stats.missing_dma_blocks==0u);
    }
    CHECK(!memcmp(baseline.pcm,meeting_a.pcm,sizeof(baseline.pcm)));
    CHECK(!memcmp(baseline.pcm,meeting_b.pcm,sizeof(baseline.pcm)));
    CHECK(memcmp(voice_a.pcm,voice_b.pcm,sizeof(voice_a.pcm))!=0);
    const uint64_t frames=c[3].stats.pcm_frames_emitted;
    CHECK(comp_wba_microphone_profile_select(&c[3],false,1u,&measured));
    CHECK(c[3].stats.pcm_frames_emitted==frames);comp_wba_pdm_capture_reset_stream(&c[3]);
    CHECK(c[3].pcm_frame_count==0u&&!c[3].have_dma_sequence);
    for(unsigned k=0u;k<2u;++k)for(unsigned i=0u;i<COMP_WBA_DUAL_HISTORY;++i)CHECK(c[3].dual_mic.history[k][i]==0);
    puts("PASS actual PDM conversion: meeting bit-exact LEFT despite different right input; voice uses both; reset retains counters and clears history");
}
int main(void){refusals();actual_pcm();puts("PASS_MICROPHONE_SESSION_POLICY_SOFTWARE_ONLY");return 0;}
