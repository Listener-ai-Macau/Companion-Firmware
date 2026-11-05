#include "wba_stack_monitor.h"
void comp_wba_stack_sample(comp_wba_stack_monitor_t *s,
    const volatile uint32_t *bottom,size_t words,uint32_t msp_free_bytes)
{
    if (!s || !bottom || !words || words>UINT32_MAX/4u) return;
    size_t untouched=0;
    while (untouched<words && bottom[untouched]==COMP_WBA_STACK_PATTERN) ++untouched;
    uint32_t free_bytes=(uint32_t)untouched*4u;
    if (msp_free_bytes<free_bytes) free_bytes=msp_free_bytes;
    if (!s->sampled || free_bytes<s->minimum_free_bytes) s->minimum_free_bytes=free_bytes;
    s->sampled=true;
    s->low_latched|=free_bytes<COMP_WBA_STACK_WARN_BYTES;
    s->guard_failed|=bottom[0]!=COMP_WBA_STACK_PATTERN;
}
