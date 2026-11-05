#include "../ble_credit_profile.h"
#include <assert.h>
#include <stdio.h>
int main(void){
 comp_v11_credit_profile_t v={0};
 comp_credit_open(&v,0u);comp_credit_begin(&v,100u,2u);comp_credit_end(&v,110u);
 comp_credit_pool(&v,120u);comp_credit_pool(&v,121u);comp_credit_close(&v,200u);
 assert(v.before_us==100u && v.after_us==100u && v.run_us==10u && v.events==1u && v.packets==2u && v.pool_us==20u && v.pool_samples==1u && v.flags==0u);
 comp_credit_begin(&v,250u,2u);comp_credit_end(&v,260u);assert(v.gap_us==150u && v.events==2u && v.run_us==20u);
 comp_credit_open(&v,300u);comp_credit_close(&v,350u);assert(v.before_us==150u && v.after_us==100u);
 v=(comp_v11_credit_profile_t){0};comp_credit_open(&v,UINT32_MAX-10u);comp_credit_begin(&v,9u,3u);comp_credit_end(&v,19u);comp_credit_close(&v,29u);assert(v.before_us==20u&&v.after_us==20u&&v.run_us==10u&&!(v.flags&CREDIT_ERRORS));
 v=(comp_v11_credit_profile_t){0};comp_credit_open(&v,20u);comp_credit_close(&v,19u);assert(v.flags&CREDIT_BACKWARD);
 v=(comp_v11_credit_profile_t){.before_us=UINT32_MAX};comp_credit_open(&v,0u);comp_credit_close(&v,1u);assert(v.flags&CREDIT_OVERFLOW);
 v=(comp_v11_credit_profile_t){0};comp_credit_begin(&v,1u,2u);comp_credit_begin(&v,2u,2u);assert(v.flags&CREDIT_DUPLICATE);
 uint32_t count;uint8_t p[]={0x13,9,2,1,0,2,0,3,0,4,0};assert(comp_credit_packet_count(p,1u,&count)&&count==3u);assert(comp_credit_packet_count(p,2u,&count)&&count==4u);assert(comp_credit_packet_count(p,3u,&count)&&count==0u);
 p[1]=8u;assert(!comp_credit_packet_count(p,1u,&count));assert(!comp_credit_packet_count(NULL,1u,&count));
 assert(sizeof(v)==56u);puts("PASS_CREDIT_GATE_FIRST_COMPLETION_SPLIT_CALLBACK_POOL_SUBSET_WRAP_ZERO_INVALID_56B");return 0;
}
