#include "../ble_completion_profile.h"
#include <assert.h>
#include <stdio.h>
int main(void){
 comp_v11_completion_profile_t v={0};comp_completion_queue_t *q=&v.completion;
 comp_completion_enqueue(q,1u,0u);comp_completion_enqueue(q,2u,20u);
 comp_completion_dispatch(q,2u,50u);comp_completion_dispatch(q,1u,80u);
 assert(q->samples==2u && q->total_us==110u && q->flags==0u);
 comp_completion_enqueue(q,1u,UINT32_MAX-10u);comp_completion_dispatch(q,1u,9u);
 assert(q->total_us==130u && q->samples==3u && q->flags==0u);
 comp_completion_enqueue(q,1u,100u);comp_completion_enqueue(q,1u,200u);
 comp_completion_dispatch(q,1u,250u);assert(q->flags==COMPLETION_DUPLICATE && q->total_us==280u);
 *q=(comp_completion_queue_t){0};comp_completion_dispatch(q,2u,1u);assert(q->flags==COMPLETION_MISSING);
 *q=(comp_completion_queue_t){0};comp_completion_enqueue(q,1u,100u);comp_completion_dispatch(q,1u,99u);assert(q->flags==COMPLETION_BACKWARD && q->samples==0u);
 *q=(comp_completion_queue_t){.total_us=UINT32_MAX};comp_completion_enqueue(q,1u,0u);comp_completion_dispatch(q,1u,1u);assert(q->flags==COMPLETION_OVERFLOW);
 *q=(comp_completion_queue_t){.samples=UINT32_MAX};comp_completion_enqueue(q,1u,0u);comp_completion_dispatch(q,1u,0u);assert(q->flags==COMPLETION_OVERFLOW);
 *q=(comp_completion_queue_t){0};comp_completion_enqueue(q,0u,1u);comp_completion_enqueue(q,3u,1u);assert(q->flags==0u);
 comp_completion_enqueue(q,2u,10u);assert(q->flags==2u); /* pending tail cannot qualify */
 assert(q->flags==2u && sizeof(v)==56u);puts("PASS_DUAL_COMPLETION_WRAP_ZERO_DUPLICATE_MISSING_OVERFLOW_AND_56B");return 0;
}
