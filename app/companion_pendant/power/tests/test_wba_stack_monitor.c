#include "wba_stack_monitor.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do { if (!(x)) { printf("FAIL line %d: %s\n",__LINE__,#x);return 1; } } while (0)
int main(void)
{
    uint32_t region[512];comp_wba_stack_monitor_t s={0};
    for (unsigned i=0;i<512;++i) region[i]=COMP_WBA_STACK_PATTERN;
    comp_wba_stack_sample(&s,region,512,2048);CHECK(s.sampled && s.minimum_free_bytes==2048 && !s.low_latched);
    region[400]=0;
    comp_wba_stack_sample(&s,region,512,1800);CHECK(s.minimum_free_bytes==1600 && !s.low_latched);
    /* MSP catches reserved-but-unwritten frames; minimum/alerts never recover
     * simply because a later shallower frame happens to match the paint. */
    comp_wba_stack_sample(&s,region,512,1000);CHECK(s.minimum_free_bytes==1000 && s.low_latched);
    region[400]=COMP_WBA_STACK_PATTERN;
    comp_wba_stack_sample(&s,region,512,2048);CHECK(s.minimum_free_bytes==1000 && s.low_latched);
    region[0]=0;comp_wba_stack_sample(&s,region,512,2048);
    CHECK(s.minimum_free_bytes==0 && s.guard_failed);
    memset(&s,0,sizeof(s));comp_wba_stack_sample(&s,NULL,512,0);CHECK(!s.sampled);
    comp_wba_stack_sample(&s,region,0,0);CHECK(!s.sampled);
    puts("PASS stack watermark: untouched, written, reserved frame, latched low/guard, bounds");return 0;
}
