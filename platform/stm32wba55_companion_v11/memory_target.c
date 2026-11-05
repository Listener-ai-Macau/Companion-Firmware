#include "memory_target.h"
#include "stm32wbaxx.h"
extern uint32_t _sstack, _estack, _end;
void comp_v11_memory_sample(comp_v11_memory_stats_t *s)
{
    uintptr_t bottom=(uintptr_t)&_sstack,top=(uintptr_t)&_estack;
    uintptr_t msp=__get_MSP(),end=(uintptr_t)&_end;
    s->stack_reserved_bytes=(uint32_t)(top-bottom);
    s->static_gap_bytes=bottom>=end ? (uint32_t)(bottom-end) : 0u;
    uint32_t free_bytes=msp>=bottom && msp<=top ? (uint32_t)(msp-bottom) : 0u;
    comp_wba_stack_sample(&s->stack,&_sstack,s->stack_reserved_bytes/4u,free_bytes);
}
