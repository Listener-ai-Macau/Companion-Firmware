#include "../ble_exec_observation.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void)
{
    comp_v11_ble_route_observation_t o={0};
    comp_v11_ble_exec_begin(&o,1u,10u);
    comp_v11_ble_route_ready(&o.job[1],12u); /* ISR schedules next host work */
    comp_v11_ble_exec_begin(&o,2u,15u);comp_v11_ble_exec_end(&o,2u,20u);
    comp_v11_ble_exec_end(&o,1u,35u);
    assert(o.job[0].total_us==25u && o.job[0].max_us==5u);
    assert(o.job[1].since_us==12u && (o.job[1].word&ROUTE_PENDING));
    assert(!o.job[0].since_us && !o.job[0].word);
    comp_v11_ble_route_run(&o.job[1],40u);assert(o.job[1].total_us==28u);
    memset(&o,0,sizeof(o));comp_v11_ble_exec_begin(&o,2u,0xfffffff0u);
    comp_v11_ble_exec_end(&o,2u,16u);assert(o.job[0].max_us==32u);
    memset(&o,0,sizeof(o));comp_v11_ble_exec_begin(&o,1u,5u);
    comp_v11_ble_exec_begin(&o,1u,6u);assert(o.job[1].word&ROUTE_UNMARKED);
    comp_v11_ble_exec_end(&o,1u,8u);comp_v11_ble_exec_end(&o,1u,9u);
    assert(o.job[1].word&ROUTE_UNMARKED);
    memset(&o,0,sizeof(o));comp_v11_ble_exec_end(&o,2u,9u);
    assert(o.job[2].word&ROUTE_UNMARKED);
    puts("PASS IRQ-ready timestamp independent, nested elapsed overlap explicit, wrap and unmatched edges invalidate coverage");
    return 0;
}
