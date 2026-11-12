/* Real continuous core, Opus and CRC/SHA-backed NOR fixture. No board/audio. */
#define main original_continuous_fixture_main
#include "test_companion_continuous_recording.c"
#undef main

static bool gate_closed;
static unsigned gate_calls,drain_calls,finish_calls;
static unsigned successor_calls;
static comp_segment_result_t invalid_successor(void *context,bool take,
    const comp_segment_entry_t **entry,comp_segment_audio_t **writer)
{
    (void)context;(void)take;*entry=NULL;*writer=NULL;
    ++successor_calls;return COMP_SEG_CORRUPT;
}
static bool empty_poll_and_boundary(void)
{
    fixture_t *f=&fixture;CHECK(initialize_mode(f,true,0u));
    comp_cont_recording_t *r=&f->recorder;
    successor_calls=0u;r->config.next=invalid_successor;
    /* No samples can cross into a successor during these idle calls. */
    CHECK(poll_many(f,100u));CHECK(!successor_calls && r->state==COMP_CONT_RUNNING);
    int16_t pcm[160];pcm_block(0u,pcm);CHECK(comp_cont_recording_pcm(r,pcm,160u));
    CHECK(comp_cont_recording_poll(r)==COMP_CONT_FAULT);
    CHECK(successor_calls==1u && r->failure==COMP_SEG_CORRUPT && !r->codec.frames_encoded);
    /* A staged half at the last packet still needs the late/full decision,
     * even when no further PCM is queued. */
    CHECK(initialize_mode(f,true,0u));r=&f->recorder;
    r->codec.frames_encoded=r->active_frame_limit-1u;r->codec.pcm_fill=160u;
    r->config.next=invalid_successor;successor_calls=0u;
    CHECK(comp_cont_recording_poll(r)==COMP_CONT_FAULT && successor_calls==1u);
    return true;
}
static bool admission(void *context,bool active,uint8_t queued)
{
    fixture_t *f=context;
    ++gate_calls;
    if(!active)++drain_calls;
    if(!queued)++finish_calls;
    /* The same engine state must arrive through every actual encode entry. */
    if(active!=f->recorder.microphone_active || queued!=f->recorder.ring_count)return false;
    return !gate_closed;
}

static bool run_case(unsigned blocks,unsigned mode,uint8_t timeline,bool gated,
                     uint8_t *raw,uint32_t *length)
{
    fixture_t *f=&fixture;CHECK(initialize_mode(f,true,timeline));
    comp_cont_recording_t *r=&f->recorder;
    gate_closed=gated;gate_calls=drain_calls=finish_calls=0u;
    r->config.encode_window=gated?admission:NULL;
    int16_t pcm[160];pcm_block(0u,pcm);
    CHECK(comp_cont_recording_pcm(r,pcm,160u));f->now=10u;
    CHECK(poll_many(f,100u));
    CHECK(r->codec.pcm_fill==160u && !r->ring_count && !gate_calls);
    for(unsigned b=1u;b<blocks;b++) {
        pcm_block(b,pcm);CHECK(comp_cont_recording_pcm(r,pcm,160u));
    }
    f->now=blocks*10u;
    if(mode==1u)CHECK(comp_cont_recording_stop(r,91u));
    if(mode==2u)CHECK(comp_cont_recording_pause(r,91u,1u));
    if(gated) {
        for(unsigned i=0u;i<100u&&!gate_calls;i++)CHECK(poll_many(f,1u));
        CHECK(gate_calls && !r->codec.frames_encoded && r->codec.pcm_fill==160u);
        CHECK(r->ring_count==blocks-1u);
        companion_opus16_rt_t before=r->codec;
        const uint8_t read=r->ring_read,count=r->ring_count;
        const uint32_t packets=r->stats.encoded_packets;
        CHECK(poll_many(f,8u));
        CHECK(!memcmp(&before,&r->codec,sizeof(before)) && r->ring_read==read &&
              r->ring_count==count && r->stats.encoded_packets==packets);
    }
    /* Both runs use the same clock and source/control timeline. Only the
     * blocked run makes extra rejected cooperative calls before this point. */
    f->now+=12u;gate_closed=false;
    if(mode==0u) {
        CHECK(poll_many(f,100u));
        CHECK(r->codec.frames_encoded==blocks/2u);
        CHECK(comp_cont_recording_stop(r,91u));
    }
    if(mode==2u) {
        CHECK(poll_many(f,500u));CHECK(r->state==COMP_CONT_PAUSED && !f->microphone);
        f->now+=100u;CHECK(comp_cont_recording_stop(r,91u));
    }
    for(unsigned i=0u;i<5000u&&r->state!=COMP_CONT_SEALED;i++)CHECK(poll_many(f,1u));
    CHECK(r->state==COMP_CONT_SEALED && f->starts==1u && f->stops==1u && f->count==1u);
    CHECK(!r->stats.overflows && !r->stats.budget_failures && r->stats.accepted_pcm_blocks==blocks);
    if(gated && (mode!=0u || timeline>=COMP_CONT_TIMELINE_SOURCE_BOUNDARY))CHECK(drain_calls);
    if(gated && timeline>=COMP_CONT_TIMELINE_SOURCE_BOUNDARY)CHECK(finish_calls);
    for(unsigned i=0u;i<5000u&&f->reclaims<f->count;i++) {
        comp_segment_result_t result=background(f);CHECK(result==COMP_SEG_OK || result==COMP_SEG_PENDING);
    }
    CHECK(f->reclaims==1u);*length=f->sealed[0].descriptor.encoded_length;
    memcpy(raw,f->raw[0],*length);
    return true;
}

int main(void)
{
    if(!empty_poll_and_boundary())return 1;
    static uint8_t expected[MAX_RAW],actual[MAX_RAW];unsigned cases=0u;
    const unsigned specs[][3]={{2u,0u,0u},{4u,0u,3u},{2u,1u,0u},
        {4u,1u,3u},{1u,1u,0u},{1u,1u,3u},{2u,1u,3u},{2u,2u,3u},{4u,2u,3u}};
    for(unsigned i=0u;i<sizeof(specs)/sizeof(specs[0]);i++) {
#ifdef COMP_TEST_BEFORE_ENGINE
        if(specs[i][1]!=1u)continue;
#endif
        printf("case blocks=%u mode=%u timeline=%u\n",specs[i][0],specs[i][1],specs[i][2]);
        uint32_t a=0u,b=0u;
        if(!run_case(specs[i][0],specs[i][1],(uint8_t)specs[i][2],false,expected,&a) ||
           !run_case(specs[i][0],specs[i][1],(uint8_t)specs[i][2],true,actual,&b))return 1;
        if(a!=b||memcmp(expected,actual,a))return 2;
        ++cases;
    }
    printf("PASS unified encode admission: %u running/STOP/PAUSE/final-frame cases; rejected calls preserve codec/PCM/packet counters; real Opus original bytes identical; CRC/SHA and physical-model reclaim; no microphone restart; software only\n",cases);
    return 0;
}
