#include "../ble_pipe_profile.h"
#include <assert.h>
#include <stdio.h>
int main(void){
 comp_v11_pipe_profile_t v={0};
 comp_pipe_send_begin(&v,1u,false);comp_pipe_send_end(&v,1u,true,false);
 comp_pipe_begin(&v,100u);assert((v.window_depths&65535u)==1u);
 comp_pipe_radio(&v,110u,true,true,true);comp_pipe_radio(&v,160u,false,true,true);
 comp_pipe_send_begin(&v,1u,true);comp_pipe_send_end(&v,1u,true,true);comp_pipe_complete(&v,2u,true);
 comp_pipe_radio(&v,200u,true,true,true);comp_pipe_radio(&v,250u,false,true,true);
 comp_pipe_end(&v,300u);assert(v.accepted==1u&&v.completed==2u&&v.depth==0u&&v.radio_us==100u&&v.queued_sum==1u&&v.zero_starts==1u&&v.radio_starts==2u&&pipe_peak(&v)==2u&&!(v.flags&PIPE_ERRORS));
 v=(comp_v11_pipe_profile_t){0};comp_pipe_send_begin(&v,1u,false);comp_pipe_send_end(&v,1u,false,false);assert(v.depth==0u);
 comp_pipe_begin(&v,0u);comp_pipe_send_begin(&v,1u,true);comp_pipe_radio(&v,10u,true,true,true);comp_pipe_radio(&v,20u,false,true,true);comp_pipe_send_end(&v,1u,true,true);assert(pipe_skipped(&v)==1u&&v.queued_sum==0u);
 comp_pipe_complete(&v,1u,true);comp_pipe_end(&v,30u);assert(!(v.flags&PIPE_ERRORS));
 v=(comp_v11_pipe_profile_t){.handle=1u,.flags=PIPE_HANDLE|PIPE_ON|PIPE_RADIO_KNOWN};comp_pipe_begin(&v,UINT32_MAX-10u);comp_pipe_radio(&v,9u,false,true,true);comp_pipe_end(&v,19u);assert(v.radio_us==20u&&v.span_us==30u&&!(v.flags&PIPE_ERRORS));
 v=(comp_v11_pipe_profile_t){.flags=PIPE_HANDLE,.handle=1u};comp_pipe_complete(&v,1u,false);assert(v.flags&PIPE_LIVE_INVALID);
 comp_pipe_disconnect(&v,1u,false);comp_pipe_send_begin(&v,1u,false);comp_pipe_send_end(&v,1u,true,false);assert(!(v.flags&PIPE_LIVE_INVALID));
 v=(comp_v11_pipe_profile_t){.flags=PIPE_HANDLE,.handle=1u,.depth=UINT32_MAX};comp_pipe_send_begin(&v,1u,true);assert(v.flags&PIPE_OVERFLOW);
 v=(comp_v11_pipe_profile_t){.flags=PIPE_HANDLE,.handle=1u};comp_pipe_send_begin(&v,1u,true);comp_pipe_send_begin(&v,1u,true);assert(v.flags&PIPE_DUP);
 v=(comp_v11_pipe_profile_t){.flags=PIPE_HANDLE,.handle=1u};comp_pipe_begin(&v,0u);comp_pipe_radio(&v,10u,true,true,false);comp_pipe_radio(&v,20u,false,true,false);assert(pipe_skipped(&v)==1u);
 v=(comp_v11_pipe_profile_t){.flags=PIPE_HANDLE,.handle=1u};comp_pipe_begin(&v,0u);comp_pipe_send_begin(&v,1u,true);comp_pipe_send_end(&v,1u,true,true);comp_pipe_end(&v,10u);uint32_t frozen=v.window_depths;comp_pipe_disconnect(&v,1u,false);assert(v.window_depths==frozen && ((frozen>>8u)&255u)==1u && (frozen>>16u)&PIPE_HANDLE);
 v=(comp_v11_pipe_profile_t){0};comp_pipe_begin(&v,0u);comp_pipe_send_begin(&v,1u,true);comp_pipe_send_end(&v,1u,true,true);comp_pipe_end(&v,10u);assert((v.window_depths>>16u)&PIPE_NO_BASELINE);
 v=(comp_v11_pipe_profile_t){.flags=PIPE_HANDLE,.handle=1u};comp_pipe_begin(&v,100u);comp_pipe_end(&v,99u);assert((v.window_depths>>16u)&PIPE_BACKWARD);
 assert(sizeof(v)==52u);puts("PASS_PUBLIC_LL_LEDGER_WINDOW_CONSERVATION_REJECTED_ADMISSION_RADIO_SUBSET_CLIP_WRAP_UNDERFLOW_DUPLICATE_52_PLUS4");return 0;
}
