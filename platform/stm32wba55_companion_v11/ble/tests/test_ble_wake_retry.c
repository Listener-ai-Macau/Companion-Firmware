#include "../ble_completion_profile.h"
#include <assert.h>
#include <stdio.h>
int main(void){
 comp_wake_retry_t q={0};
 comp_wake_ready(&q,7u,100u,0u);comp_wake_ready(&q,7u,100u,5u);
 comp_wake_attempt(&q,7u,100u,10u);comp_wake_attempt(&q,7u,100u,20u);
 comp_wake_accepted(&q,7u,100u,100u);
 assert(q.first_us==10u && q.accepted_us==100u && q.word==256u);
 comp_wake_ready(&q,7u,200u,UINT32_MAX-10u);comp_wake_attempt(&q,7u,200u,9u);comp_wake_accepted(&q,7u,200u,29u);
 assert(q.first_us==30u && q.accepted_us==140u && q.word==512u);
 comp_wake_ready(&q,7u,300u,100u);comp_wake_attempt(&q,7u,301u,120u);assert((q.word&WAKE_FLAGS)==WAKE_STALE && (q.word>>8u)==2u);
 q=(comp_wake_retry_t){0};comp_wake_ready(&q,1u,2u,100u);comp_wake_ready(&q,2u,2u,200u);assert(q.word==WAKE_STALE);
 q=(comp_wake_retry_t){0};comp_wake_ready(&q,1u,2u,100u);comp_wake_accepted(&q,1u,2u,110u);assert(q.word==WAKE_MISSING);
 q=(comp_wake_retry_t){0};comp_wake_ready(&q,1u,2u,100u);comp_wake_attempt(&q,1u,2u,99u);assert(q.word==WAKE_BACKWARD);
 q=(comp_wake_retry_t){.first_us=UINT32_MAX};comp_wake_ready(&q,1u,2u,0u);comp_wake_attempt(&q,1u,2u,1u);comp_wake_accepted(&q,1u,2u,2u);assert(q.word==WAKE_OVERFLOW);
 q=(comp_wake_retry_t){.word=WAKE_COUNT<<8u};comp_wake_ready(&q,1u,2u,0u);comp_wake_attempt(&q,1u,2u,0u);comp_wake_accepted(&q,1u,2u,0u);assert((q.word&WAKE_FLAGS)==WAKE_OVERFLOW);
 q=(comp_wake_retry_t){0};comp_wake_attempt(&q,1u,2u,0u);comp_wake_accepted(&q,1u,2u,0u);assert(q.word==0u);
 comp_wake_ready(&q,1u,2u,0u);assert(q.word==WAKE_PENDING);
 assert(sizeof(comp_v11_completion_profile_t)==56u);puts("PASS_SAME_GENERATION_AND_OFFSET_COALESCE_FIRST_ATTEMPT_WRAP_STALE_SATURATION_56B");return 0;
}
