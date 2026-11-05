#include "../ble_wait_phase.h"
#include <assert.h>
int main(void)
{
 comp_v11_wait_phase_t v={0};comp_wait_start(&v,0u);comp_wait_open(&v,10u);
 comp_wait_post(&v,1u,110u);comp_wait_enter(&v,1u,210u);comp_wait_leave(&v,230u);
 comp_wait_close(&v,330u);comp_wait_end(&v,400u);
 assert(v.before_us==100u && v.queued_us==100u && v.handler_us==20u && v.after_us==100u);
 assert(v.pair_us==100u && !(v.flags&WAIT_ERRORS) && !wait_pending(&v));
 /* A later report transitions from released-handler wait back to queue.
  * Queue exists before gate opening and can close inside the SDK callback. */
 v=(comp_v11_wait_phase_t){0};comp_wait_post(&v,1u,0u);comp_wait_start(&v,5u);
 comp_wait_open(&v,10u);comp_wait_enter(&v,1u,20u);comp_wait_close(&v,30u);
 comp_wait_leave(&v,40u);comp_wait_open(&v,50u);comp_wait_post(&v,2u,60u);
 comp_wait_enter(&v,2u,70u);comp_wait_leave(&v,80u);comp_wait_post(&v,3u,90u);
 comp_wait_enter(&v,3u,100u);comp_wait_leave(&v,110u);comp_wait_close(&v,120u);
 comp_wait_end(&v,130u);
 assert(v.before_us==10u && v.queued_us==30u && v.handler_us==30u && v.after_us==20u);
 assert(!(v.flags&WAIT_ERRORS));
 v=(comp_v11_wait_phase_t){0};comp_wait_start(&v,UINT32_MAX-20u);
 comp_wait_open(&v,UINT32_MAX-10u);comp_wait_post(&v,1u,9u);comp_wait_enter(&v,1u,19u);
 comp_wait_leave(&v,29u);comp_wait_close(&v,39u);comp_wait_end(&v,49u);
 assert(v.before_us==20u && v.queued_us==10u && v.handler_us==10u && v.after_us==10u && !(v.flags&WAIT_ERRORS));
 v=(comp_v11_wait_phase_t){0};comp_wait_start(&v,0u);comp_wait_post(&v,1u,1u);comp_wait_post(&v,2u,2u);
 comp_wait_enter(&v,2u,3u);assert(v.flags&WAIT_REORDER);
 v=(comp_v11_wait_phase_t){0};comp_wait_post(&v,1u,1u);comp_wait_post(&v,1u,2u);assert(v.flags&WAIT_DUPLICATE);
 v=(comp_v11_wait_phase_t){0};comp_wait_post(&v,1u,1u);comp_wait_post(&v,2u,2u);comp_wait_post(&v,3u,3u);assert(v.flags&WAIT_OVERFLOW);
 v=(comp_v11_wait_phase_t){0};comp_wait_start(&v,0u);comp_wait_open(&v,10u);comp_wait_close(&v,9u);assert(v.flags&WAIT_BACKWARD);
 v=(comp_v11_wait_phase_t){0};comp_wait_start(&v,0u);v.before_us=UINT32_MAX;comp_wait_open(&v,0u);comp_wait_close(&v,1u);assert(v.flags&WAIT_OVERFLOW);
 v=(comp_v11_wait_phase_t){0};comp_wait_start(&v,0u);comp_wait_post(&v,1u,1u);comp_wait_end(&v,2u);
 comp_wait_enter(&v,1u,3u);comp_wait_leave(&v,4u);assert(v.pair_us==0u && ((v.flags>>16u)&3u)==1u);
 return 0;
}
