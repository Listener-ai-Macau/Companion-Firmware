#include "ble_dispatch_profile.h"
#include <assert.h>
#include <stdio.h>
int main(void)
{
    comp_v11_dispatch_profile_t p={0};
    /* Simulated host/LL overlap and a repeated ISR-ready must retain the
     * first ready timestamp; do not count two coalesced requests as jobs. */
    comp_dispatch_ready(&p.job[0],100u);comp_dispatch_ready(&p.job[1],120u);
    comp_dispatch_ready(&p.job[0],140u);comp_dispatch_run(&p.job[0],190u);
    comp_dispatch_run(&p.job[1],200u);
    assert(p.job[0].count==1u && p.job[0].total_us==90u && p.job[0].coalesced==1u);
    assert(p.job[1].total_us==80u && p.job[1].max_us==80u);
    /* 90+80 is an overlapping sample sum, not this 100us wall interval. */
    comp_dispatch_run(&p.job[0],210u);
    assert(p.job[0].unpaired==1u && p.job[0].count==1u);
    comp_dispatch_ready(&p.job[0],UINT32_MAX-10u);comp_dispatch_run(&p.job[0],20u);
    assert(p.job[0].count==2u && p.job[0].total_us==121u && p.job[0].max_us==90u);
    comp_dispatch_ready(&p.job[0],100u);comp_dispatch_run(&p.job[0],99u);
    assert(p.job[0].count==2u && (p.job[0].flags&DISPATCH_BACKWARD));
    p.job[0].total_us=UINT32_MAX-1u;
    comp_dispatch_ready(&p.job[0],10u);comp_dispatch_run(&p.job[0],12u);
    assert(p.job[0].total_us==UINT32_MAX-1u && (p.job[0].flags&DISPATCH_OVERFLOW));
    p.job[1].coalesced=UINT32_MAX;
    comp_dispatch_ready(&p.job[1],20u);comp_dispatch_ready(&p.job[1],21u);
    assert(p.job[1].since_us==20u && p.job[1].coalesced==UINT32_MAX);
    assert((p.job[1].flags&(DISPATCH_PENDING|DISPATCH_OVERFLOW))==(DISPATCH_PENDING|DISPATCH_OVERFLOW));
    puts("PASS dispatch boundary, coalescing, overlap, wrap and invalid-counter checks");
    return 0;
}
