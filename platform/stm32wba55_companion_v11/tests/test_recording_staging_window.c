#include "companion_continuous_recording.h"
#include "capture_encode_window.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){printf("FAIL line=%d %s\n",__LINE__,#x);return 1;}}while(0)
static comp_cont_recording_t recorder;
int main(void)
{
    comp_cont_recording_t *r=&recorder;memset(r,0,sizeof(*r));
    r->state=COMP_CONT_RUNNING;r->ring_count=8u;r->codec.frame_samples=320u;r->encoder_owned=true;r->codec.ready=true;
    CHECK(comp_cont_recording_pcm_staging_pending(r));
    CHECK(comp_v11_capture_work_window_open(4u,comp_cont_recording_pcm_staging_pending(r),false));
    CHECK(comp_v11_capture_work_window_open(5u,true,false));
    CHECK(!comp_v11_capture_work_window_open(6u,true,true));
    r->codec.pcm_fill=160u;CHECK(!comp_cont_recording_pcm_staging_pending(r));
    CHECK(!comp_v11_capture_work_window_open(4u,false,true));
    CHECK(!comp_v11_capture_work_window_open(2u,false,false));
    CHECK(comp_v11_capture_work_window_open(2u,false,true));
    r->codec.pcm_fill=0u;r->writer.phase=1u;CHECK(!comp_cont_recording_pcm_staging_pending(r));r->writer.phase=0u;
    r->roll_packet_bytes=42u;CHECK(!comp_cont_recording_pcm_staging_pending(r));r->roll_packet_bytes=0u;
    r->bookmark_phase=1u;CHECK(!comp_cont_recording_pcm_staging_pending(r));r->bookmark_phase=0u;
    r->stage_length=COMP_CONT_STAGE_BYTES;CHECK(!comp_cont_recording_pcm_staging_pending(r));r->stage_length=12u;
    r->state=COMP_CONT_FAULT;CHECK(!comp_cont_recording_pcm_staging_pending(r));
    r->state=COMP_CONT_PAUSING;CHECK(comp_cont_recording_pcm_staging_pending(r));
    r->ring_count=0u;CHECK(!comp_cont_recording_pcm_staging_pending(r));
    CHECK(!comp_cont_recording_pcm_staging_pending(NULL));
    puts("PASS_PCM_STAGING_NOT_FULL_ENCODE old_closed_window_counterexample=1 actual_encoder_guards_retained=1 housekeeping_excluded=1");return 0;
}
