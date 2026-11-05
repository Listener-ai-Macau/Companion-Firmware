#include "../ble_transit_profile.h"
#include <assert.h>
#include <stdio.h>
int main(void){
 comp_v11_transit_profile_t v={0};
 comp_transit_accept(&v,1u,7u,10u);comp_transit_accept(&v,2u,7u,20u);
 comp_transit_enqueue(&v,1u,7u,30u);comp_transit_accept(&v,1u,7u,40u); /* old completion awaits dispatch */
 comp_transit_dispatch(&v,1u,7u,50u);comp_transit_enqueue(&v,2u,7u,60u);
 comp_transit_enqueue(&v,1u,7u,70u);comp_transit_dispatch(&v,2u,7u,80u);comp_transit_dispatch(&v,1u,7u,90u);
 assert(v.admission_us==90u && v.admission_max_us==40u && v.admission_samples==3u && v.dispatch_us==60u && v.dispatch_samples==3u);
 assert(!(v.flags&TRANSIT_LOW) && comp_transit_peak(&v)==2u);
 comp_transit_accept(&v,1u,7u,UINT32_MAX-10u);comp_transit_enqueue(&v,1u,7u,9u);comp_transit_dispatch(&v,1u,7u,19u);
 assert(v.admission_us==110u && v.dispatch_us==70u && !(v.flags&TRANSIT_LOW));
 v=(comp_v11_transit_profile_t){0};comp_transit_accept(&v,1u,0u,0u);comp_transit_enqueue(&v,1u,0u,0u);comp_transit_dispatch(&v,1u,0u,0u);assert(v.admission_samples==1u && !(v.flags&TRANSIT_LOW));
 v=(comp_v11_transit_profile_t){0};comp_transit_accept(&v,1u,1u,0u);comp_transit_accept(&v,1u,1u,1u);assert(v.flags&TRANSIT_DUP_ACCEPT);assert(comp_transit_duplicates(&v)==1u);
 v=(comp_v11_transit_profile_t){0};comp_transit_accept(&v,1u,1u,0u);comp_transit_enqueue(&v,1u,1u,1u);comp_transit_accept(&v,1u,1u,2u);comp_transit_enqueue(&v,1u,1u,3u);assert(v.flags&TRANSIT_DUP_QUEUE);
 v=(comp_v11_transit_profile_t){0};comp_transit_enqueue(&v,1u,1u,1u);assert(v.flags==TRANSIT_MISSING_ACCEPT);
 v=(comp_v11_transit_profile_t){0};comp_transit_dispatch(&v,1u,1u,1u);assert(v.flags==TRANSIT_MISSING_QUEUE);
 v=(comp_v11_transit_profile_t){0};comp_transit_accept(&v,1u,1u,100u);comp_transit_enqueue(&v,1u,2u,110u);assert(v.flags&TRANSIT_STALE_LINK);
 v=(comp_v11_transit_profile_t){0};comp_transit_accept(&v,1u,1u,100u);comp_transit_enqueue(&v,1u,1u,99u);assert(v.flags&TRANSIT_BACKWARD);
 v=(comp_v11_transit_profile_t){.admission_us=UINT32_MAX};comp_transit_accept(&v,1u,1u,0u);comp_transit_enqueue(&v,1u,1u,1u);assert(v.flags&TRANSIT_OVERFLOW);
 assert(sizeof(v)==56u);puts("PASS_TRANSIT_DUAL_LANE_QUEUE_OVERLAP_WRAP_ZERO_DUPLICATE_MISSING_STALE_SATURATION_56B");return 0;
}
