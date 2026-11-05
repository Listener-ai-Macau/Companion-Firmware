#include "../ble_residence_profile.h"
#include <assert.h>
int main(void)
{
 comp_v11_residence_profile_t v={0};
 comp_residence_send_begin(&v,1u,10u);comp_residence_send_end(&v,1u,true);
 comp_residence_start(&v,20u);comp_residence_send_begin(&v,1u,30u);comp_residence_send_end(&v,1u,true);
 comp_residence_completed(&v,2u,50u,true);comp_residence_end(&v,60u);
 assert(v.accepted==1u&&v.completed==2u&&v.residence_samples==1u&&v.residence_us==20u&&v.residence_max_us==20u);
 assert(((v.handle>>16u)&255u)==1u&&((v.handle>>24u)&255u)==0u&&!(v.flags&RES_ERRORS));
 /* A failed provisional tail is removed without touching accepted older
  * slots. Completion during the original API also retires its prefix. */
 v=(comp_v11_residence_profile_t){0};
 comp_residence_send_begin(&v,1u,0u);comp_residence_send_end(&v,1u,true);comp_residence_start(&v,5u);
 comp_residence_send_begin(&v,1u,10u);comp_residence_completed(&v,1u,20u,true);comp_residence_send_end(&v,1u,false);
 assert(!residence_depth(&v)&&!v.accepted&&v.completed==1u&&!(v.flags&RES_ERRORS));
 comp_residence_send_begin(&v,1u,30u);comp_residence_completed(&v,1u,40u,true);comp_residence_send_end(&v,1u,true);
 comp_residence_end(&v,50u);assert(v.accepted==1u&&v.completed==2u&&v.residence_us==10u&&!(v.flags&RES_ERRORS));
 v=(comp_v11_residence_profile_t){0};comp_residence_send_begin(&v,1u,0u);comp_residence_send_end(&v,1u,false);comp_residence_start(&v,0u);
 for(unsigned i=0u;i<8u;++i){comp_residence_send_begin(&v,1u,10u+i);comp_residence_send_end(&v,1u,true);}
 comp_residence_send_begin(&v,1u,20u);assert(residence_depth(&v)==9u);comp_residence_send_end(&v,1u,false);
 assert(residence_depth(&v)==8u&&!(v.flags&RES_ERRORS));comp_residence_completed(&v,8u,30u,true);
 assert(v.residence_samples==8u&&v.residence_us==132u&&v.accepted==8u&&v.completed==8u);
 /* Wrapped unsigned timestamps, ring wrap and overflow/backward/handle
  * violations; never turn a missing baseline into a qualified mean. */
 v=(comp_v11_residence_profile_t){0};comp_residence_send_begin(&v,1u,UINT32_MAX-20u);comp_residence_send_end(&v,1u,false);
 comp_residence_start(&v,UINT32_MAX-10u);comp_residence_send_begin(&v,1u,UINT32_MAX-5u);comp_residence_send_end(&v,1u,true);
 comp_residence_completed(&v,1u,9u,true);comp_residence_end(&v,19u);assert(v.residence_us==15u&&!(v.flags&RES_ERRORS));
 v=(comp_v11_residence_profile_t){0};comp_residence_start(&v,0u);assert(v.flags&RES_NO_BASELINE);
 v=(comp_v11_residence_profile_t){0};comp_residence_send_begin(&v,1u,0u);comp_residence_send_end(&v,1u,false);comp_residence_start(&v,0u);
 comp_residence_send_begin(&v,1u,10u);comp_residence_send_end(&v,1u,true);comp_residence_completed(&v,1u,9u,true);assert(v.flags&RES_BACKWARD);
 v=(comp_v11_residence_profile_t){0};comp_residence_send_begin(&v,1u,0u);comp_residence_send_end(&v,1u,false);comp_residence_start(&v,0u);
 comp_residence_send_begin(&v,1u,0u);comp_residence_send_end(&v,1u,true);v.residence_us=UINT32_MAX;
 comp_residence_completed(&v,1u,1u,true);assert(v.flags&RES_OVERFLOW);
 v=(comp_v11_residence_profile_t){0};comp_residence_send_begin(&v,1u,0u);comp_residence_send_end(&v,1u,true);comp_residence_start(&v,1u);
 comp_residence_send_begin(&v,2u,2u);assert(v.flags&RES_LINK_CHANGE);
 return 0;
}
