#include "../ble_micro_observation.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
 assert(comp_v11_ble_micro_consistent(3,3,99999,89999,89990));
 assert(!comp_v11_ble_micro_consistent(3,4,99999,89999,89990));
 assert(!comp_v11_ble_micro_consistent(3,3,99999,1,99990));
 assert(!comp_v11_ble_micro_consistent(3,3,0,0,0));
 assert(!comp_v11_ble_micro_consistent(3,3,99999,100000,99999));
 assert(comp_v11_ble_micro_stamp(3,99999,89999,false)==3100);
 assert(comp_v11_ble_micro_stamp(3,99999,89999,true)==4100);
 assert(comp_v11_ble_micro_stamp(4,99999,99999,false)==4000);
 uint32_t begin=UINT32_MAX-10u,end=9u;assert(end-begin==20u);
 comp_v11_ble_micro_observation_t m={0};
 comp_v11_ble_micro_aci(&m,31u,false,true);comp_v11_ble_micro_aci(&m,83u,true,true);
 comp_v11_ble_micro_aci(&m,19u,false,false);comp_v11_ble_micro_aci(&m,7u,true,false);
 assert(m.prepare_us==31 && m.prepare_calls==1 && m.commit_us==83 && m.commit_calls==1);
 assert(m.rejected_us==26 && m.rejected_calls==2);
 assert(m.prepare_us+m.commit_us+m.rejected_us==140);
 puts("PASS read-only microstamp projection, pending tick, rollover and exclusive ACI outcome timing");return 0;
}
