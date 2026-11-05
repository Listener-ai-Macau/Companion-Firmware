#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "../ble_radio_activity_profile.h"
static void pair(comp_ble_radio_activity_profile_t *p,uint32_t start,uint32_t length)
{comp_radio_activity_observe(p,true,start);comp_radio_activity_observe(p,false,start+length);}
int main(void) {
 _set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0u,_CALL_REPORTFAULT);
 comp_ble_radio_activity_profile_t p;comp_radio_activity_reset(&p);
 comp_radio_activity_observe(&p,false,99);assert(p.flags==1 && !p.active && p.min_us==UINT32_MAX);
 pair(&p,1000,2999);pair(&p,5000,3000);pair(&p,10000,5499);pair(&p,16000,5500);
 pair(&p,23000,6999);pair(&p,31000,7000);
 assert(p.bins[0]==1 && p.bins[1]==2 && p.bins[2]==2 && p.bins[3]==1);
 assert(p.min_us==2999 && p.max_us==7000 && p.flags==1);
 comp_radio_activity_reset(&p);pair(&p,UINT32_MAX-1000u,3001u);
 assert(p.bins[1]==1 && p.min_us==3001 && !p.flags);
 comp_radio_activity_observe(&p,true,100);comp_radio_activity_observe(&p,true,200);
 comp_radio_activity_observe(&p,false,500);assert(p.flags==1 && p.bins[0]==1);
 comp_radio_activity_reset(&p);pair(&p,1000,65536);assert(p.flags==2 && !p.active && !p.bins[3]);
 comp_radio_activity_reset(&p);p.bins[2]=UINT16_MAX;pair(&p,1000,6000);
 assert(p.flags==4 && p.bins[2]==UINT16_MAX);
 comp_radio_activity_reset(&p);comp_radio_activity_observe(&p,true,10);
 assert(p.active==1 && p.min_us==UINT32_MAX && !p.bins[0]);
 puts("PASS actual production counter: boundary bins, censored endpoints,32bit wrap, invalid duration and saturated counts");
 return 0;
}
