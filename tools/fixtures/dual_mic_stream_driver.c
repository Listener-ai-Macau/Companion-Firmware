/* Software source only: unchanged production PDM C -> accepted pair observer
 * -> bounded packet queue -> an ordinary FILE sink AFTER capture returns.
 * No hardware, sound, radio, NOR claim or acoustic quality assertion. */
#define _CRT_SECURE_NO_WARNINGS
#include "wba_pdm_capture.h"
#include "wba_dual_mic_pair_stream.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct {
    comp_wba_pdm_capture_t pdm;
    comp_dmic_stream_t stream;
    uint8_t queue[2u*COMP_DMIC_STREAM_PACKET_BYTES];
    int16_t pair[320],mono[160],expected[320];
    unsigned observed,mono_calls;
    bool reject;
} fixture_t;
static fixture_t f;
static uint8_t raw[3840];
static const uint8_t uid[12]={0x12,0,0x11,0,0x0d,0x50,0x33,0x57,0x54,0x36,0x37,0x20};
static const uint8_t source[20]={0x12,0x08,0x28,0xea,0xd1,0xf3,0x35,0x2e,0xbd,0xed,0x9a,0xf7,0x2e,0xa0,0x88,0x3c,0xf8,0x8a,0x35,0x40};

static bool mono(void *context,const int16_t *pcm,size_t count,uint32_t rate)
{
    fixture_t *x=context;assert(count==160u&&rate==16000u);x->mono_calls++;
    memcpy(x->mono,pcm,320u);return !(x->reject&&x->mono_calls==4u);
}
static void paired(void *context,const int16_t *pcm,size_t count,uint32_t rate)
{
    fixture_t *x=context;
    const comp_wba_pdm_stats_t *s=comp_wba_pdm_capture_stats(&x->pdm);
    if(s->missing_dma_blocks||s->reordered_dma_blocks||s->invalid_dma_blocks||s->pcm_frames_rejected)
        comp_dmic_stream_invalidate(&x->stream);
    /* Position comes from real DMA sequence rather than observer call count.
     * In this fixture sequence0 primes, sequence1 starts at source sample640. */
    uint64_t first=640u+((uint64_t)s->last_dma_sequence-1u)*160u;
    for(size_t i=0;i<count;++i)assert(pcm[2u*i]==x->mono[i]); /* LEFT stays exact */
    memcpy(x->expected,pcm,640u);x->observed++;
    (void)comp_dmic_stream_push(&x->stream,pcm,count,rate,first);
}
static bool read_raw(void *context,size_t offset,const uint8_t **bytes,size_t *count)
{
    bool failing=*(bool *)context;
    if(offset>=sizeof(raw)||(failing&&offset>=256u))return false;
    *bytes=raw+offset;*count=sizeof(raw)-offset;if(*count>256u)*count=256u;return true;
}
static void drain(FILE *out)
{
    const uint8_t *bytes;size_t length;
    while(comp_dmic_stream_peek(&f.stream,&bytes,&length)){
        const uint8_t *again;size_t again_length;
        assert(comp_dmic_stream_peek(&f.stream,&again,&again_length)&&again==bytes&&again_length==length);
        assert(fwrite(bytes,1u,length,out)==length);
        assert(comp_dmic_stream_consume(&f.stream));
        assert(!comp_dmic_stream_consume(&f.stream));
    }
}
static void initialize(void)
{
    memset(&f,0,sizeof(f));
    assert(comp_dmic_stream_begin(&f.stream,f.queue,2u,uid,source,9u,78u,640u,200u,true));
    comp_wba_pdm_config_t c={0};c.decimation=96u;c.gain_q15=32768u;c.selected_only=true;
    c.output=COMP_WBA_PDM_OUTPUT_LEFT;c.emit_pcm_frame=mono;c.observe_pair_frame=paired;
    c.pair_pcm_storage=f.pair;c.pair_pcm_capacity=320u;c.context=&f;
    comp_wba_pdm_capture_init(&f.pdm,&c);assert(comp_wba_pdm_capture_ready(&f.pdm));
    assert(comp_wba_pdm_capture_channel_mask(&f.pdm)==3u);
}
int main(int argc,char **argv)
{
    if(argc!=4)return 2;
    FILE *out=fopen(argv[2],"wb"),*expected=fopen(argv[3],"wb");assert(out&&expected);
    initialize();bool overflow=!strcmp(argv[1],"overflow"),gap=!strcmp(argv[1],"gap");
    bool readfail=!strcmp(argv[1],"readfail"),clip=!strcmp(argv[1],"clip");
    f.reject=!strcmp(argv[1],"reject");
    memset(raw,0x55,sizeof(raw));assert(comp_wba_pdm_capture_prime(&f.pdm,raw,sizeof(raw),0u));
    assert(f.observed==0u&&f.mono_calls==0u);drain(out);
    uint32_t random=1234567u;
    for(uint32_t block=0;block<200u&&!f.stream.closed;++block){
        if(clip){
            int16_t samples[320]={0};samples[6]=INT16_MAX;samples[9]=INT16_MIN;
            assert(comp_dmic_stream_push(&f.stream,samples,160u,16000u,640u+(uint64_t)block*160u));
            assert(fwrite(samples,1u,640u,expected)==640u);
        }else{
            for(size_t i=0;i<sizeof(raw);++i){random=random*1664525u+1013904223u;raw[i]=(uint8_t)(random>>24);}
            unsigned previous=f.observed;bool fail=readfail&&block==3u;
            uint32_t sequence=block+1u+(gap&&block>=3u?1u:0u);
            bool ok=comp_wba_pdm_capture_read_frame(&f.pdm,read_raw,&fail,sizeof(raw),sequence,false);
            if(f.observed!=previous&&!f.stream.faults)assert(fwrite(f.expected,1u,640u,expected)==640u);
            const comp_wba_pdm_stats_t *s=comp_wba_pdm_capture_stats(&f.pdm);
            if(!ok||s->missing_dma_blocks||s->reordered_dma_blocks||s->invalid_dma_blocks||s->pcm_frames_rejected)
                comp_dmic_stream_invalidate(&f.stream);
        }
        if(!overflow)drain(out);
    }
    bool good=comp_dmic_stream_finish(&f.stream,true);
    assert(good==(!overflow&&!gap&&!readfail&&!f.reject));drain(out);
    assert(f.stream.end_sent&&f.stream.queued==0u);assert(!comp_dmic_stream_finish(&f.stream,true));
    assert(fclose(out)==0&&fclose(expected)==0);
    /* Fresh identity/reset cannot return a previous take's terminal packet. */
    assert(!comp_dmic_stream_begin(&f.stream,f.queue,0u,uid,source,1u,1u,0u,1u,true));
    assert(!comp_dmic_stream_begin(&f.stream,f.queue,2u,uid,source,1u,1u,UINT64_MAX,1u,true));
    assert(comp_dmic_stream_begin(&f.stream,f.queue,2u,uid,source,10u,79u,0u,1u,true));
    assert(f.stream.blocks==0u&&!f.stream.closed&&!f.stream.end_sent);
    int16_t pairs[320]={0};assert(!comp_dmic_stream_push(&f.stream,pairs,160u,16000u,160u));
    assert(f.stream.faults&COMP_DMIC_STREAM_DISCONTINUITY);
    return 0;
}
