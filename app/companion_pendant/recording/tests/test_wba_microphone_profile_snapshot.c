#include "../wba_microphone_profile_snapshot.h"
#include "../wba_microphone_profile.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"FAIL %d: %s\n",__LINE__,#x);exit(1);}}while(0)
static bool emit(void *c,const int16_t *p,size_t n,uint32_t r){(void)c;(void)p;(void)n;(void)r;return true;}
int main(void){
 comp_wba_pdm_capture_t c;comp_wba_pdm_config_t cfg={0};cfg.decimation=96u;cfg.gain_q15=32768u;cfg.output=COMP_WBA_PDM_OUTPUT_LEFT;cfg.selected_only=true;cfg.emit_pcm_frame=emit;
 comp_wba_pdm_capture_init(&c,&cfg);CHECK(comp_wba_pdm_capture_ready(&c));
 uint8_t source[20]={1u},cal[32]={2u},none[32]={0};comp_rec_audio_profile_t p,old;uint8_t bytes[96];
 CHECK(comp_wba_microphone_profile_snapshot(&c,0u,703u,source,none,&p));CHECK(p.output==0u&&p.filtered_mask==1u&&p.delay_q8==0&&p.right_gain_q15==32768u);
 CHECK(comp_rec_audio_profile_encode(&p,bytes));
 comp_wba_dual_mic_config_t measured={128,40000u,true};CHECK(comp_wba_microphone_profile_select(&c,false,0u,&measured));
 CHECK(comp_wba_microphone_profile_snapshot(&c,0u,703u,source,cal,&p));CHECK(p.output==3u&&p.filtered_mask==3u&&p.delay_q8==128&&p.right_gain_q15==40000u&&(p.inversion_flags&4u));
 old=p;CHECK(!comp_wba_microphone_profile_snapshot(&c,0u,703u,source,none,&p));CHECK(!memcmp(&old,&p,sizeof(p)));
 CHECK(!comp_wba_microphone_profile_snapshot(&c,1u,703u,source,cal,&p));CHECK(!memcmp(&old,&p,sizeof(p)));
 CHECK(comp_wba_microphone_profile_select(&c,false,1u,&measured));CHECK(comp_wba_microphone_profile_snapshot(&c,1u,703u,source,cal,&p));
 CHECK(p.output==0u&&p.recorder_profile==1u&&p.delay_q8==0&&p.right_gain_q15==32768u&&!(p.inversion_flags&4u)&&!memcmp(p.calibration_sha256,none,32u));
 CHECK(!comp_wba_microphone_profile_snapshot(&c,1u,0u,source,cal,&p));CHECK(!comp_wba_microphone_profile_snapshot(NULL,0u,703u,source,cal,&p));
 puts("PASS actual capture configuration -> canonical original-bound profile; calibrated voice/meeting separation and atomic refusal");return 0;
}
