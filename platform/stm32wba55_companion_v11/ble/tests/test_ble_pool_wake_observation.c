#include "../ble_pool_wake_observation.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
 comp_v11_ble_pool_wake_observation_t m={0};
 comp_v11_ble_pool_wake(&m,100u,false,false);assert(!m.pending&&!m.pool_wakes);
 comp_v11_ble_pool_wake(&m,110u,true,true);assert(!m.pending&&m.pool_nested==1u);
 comp_v11_ble_pool_wake(&m,200u,true,false);comp_v11_ble_pool_wake(&m,250u,true,false);
 assert(m.pending&&m.pool_wakes==2u&&m.pending_since_us==200u);
 bool woke=comp_v11_ble_pool_dispatch(&m,310u);assert(woke&&!m.pending&&m.dispatch_us==110u);
 comp_v11_ble_pool_result(&m,woke,false);assert(m.wake_rejected==1u&&!m.commit_calls);
 assert(!comp_v11_ble_pool_dispatch(&m,400u));
 comp_v11_ble_pool_wake(&m,UINT32_MAX-9u,true,false);
 woke=comp_v11_ble_pool_dispatch(&m,1990u);assert(woke&&m.dispatch_us==2110u&&m.dispatch_max_us==2000u);
 comp_v11_ble_pool_result(&m,woke,true);comp_v11_ble_pool_result(&m,false,true);
 assert(m.dispatch_over_1000==1u&&m.commit_calls==2u&&m.wake_success==1u);
 assert(m.dispatch_calls==m.wake_success+m.wake_rejected);
 puts("PASS earliest pool wake, nested isolation, wraparound, immediate resubmission outcomes");return 0;
}
