#include "../ble_report_profile.h"
#include <assert.h>
#include <stdio.h>
int main(void){
 comp_v11_report_profile_t v={0};
 comp_report_open(&v,0u);comp_report_post(&v,1u,100u);comp_report_post(&v,2u,110u);
 comp_report_consume(&v,1u,150u);comp_report_consume(&v,2u,160u);comp_report_close(&v,200u);
 assert(v.before_us==100u && v.after_us==100u && v.pair_us==100u && v.pair_max_us==50u && v.pair_samples==2u && report_peak(&v)==2u && !report_pending(&v) && !(v.flags&REPORT_ERRORS));
 v=(comp_v11_report_profile_t){0};comp_report_post(&v,1u,0u);comp_report_open(&v,10u);comp_report_consume(&v,1u,20u);comp_report_close(&v,30u);assert(v.before_us==0u && v.after_us==20u && v.pair_us==20u);
 v=(comp_v11_report_profile_t){0};comp_report_open(&v,UINT32_MAX-10u);comp_report_post(&v,1u,9u);comp_report_consume(&v,1u,19u);comp_report_close(&v,29u);assert(v.before_us==20u && v.after_us==20u && v.pair_us==10u && !(v.flags&REPORT_ERRORS));
 v=(comp_v11_report_profile_t){0};comp_report_post(&v,1u,0u);comp_report_post(&v,1u,1u);assert(v.flags&REPORT_DUPLICATE);
 v=(comp_v11_report_profile_t){0};comp_report_post(&v,1u,0u);comp_report_post(&v,2u,1u);comp_report_consume(&v,2u,2u);assert(v.flags&REPORT_REORDER);
 v=(comp_v11_report_profile_t){0};comp_report_consume(&v,1u,0u);assert(v.flags&REPORT_MISSING);
 v=(comp_v11_report_profile_t){0};comp_report_post(&v,1u,0u);comp_report_post(&v,2u,1u);comp_report_post(&v,3u,2u);assert(v.flags&REPORT_OVERFLOW);
 v=(comp_v11_report_profile_t){0};comp_report_post(&v,1u,10u);comp_report_consume(&v,1u,9u);assert(v.flags&REPORT_BACKWARD);
 v=(comp_v11_report_profile_t){.pair_us=UINT32_MAX};comp_report_post(&v,1u,0u);comp_report_consume(&v,1u,1u);assert(v.flags&REPORT_OVERFLOW);
 assert(sizeof(v)==52u);puts("PASS_REPORT_POINTER_FIFO_SAME_GATE_PARTITION_PREQUEUED_WRAP_ZERO_DUPLICATE_MISSING_REORDER_OVERFLOW_52_PLUS4");return 0;
}
