#ifndef COMP_CPU_STAMP_TRACE_H
#define COMP_CPU_STAMP_TRACE_H
#include <stdint.h>
#include <stdbool.h>
/* A finite raw snapshot of the first nonmonotonic projection. No repair,
 * clamp, clock register write, timer or IRQ policy change. Calls are bounded
 * like the existing <2s residence observer; uint32-us wrap remains valid. */
typedef struct {uint32_t tick,load,v1,v2,flags,core_hz;} comp_cpu_stamp_sample_t;
typedef struct {
    comp_cpu_stamp_sample_t last,before,after;
    uint32_t last_us,before_us,after_us,events;
    bool have,captured;
} comp_cpu_stamp_trace_t;
_Static_assert(sizeof(comp_cpu_stamp_trace_t)<=96u,"bounded first clock anomaly snapshot");
static inline void comp_cpu_stamp_trace_note(comp_cpu_stamp_trace_t *t,
    const comp_cpu_stamp_sample_t *s,uint32_t us)
{
    if(t->have && us-t->last_us>UINT32_C(0x80000000)) {
        if(t->events!=UINT32_MAX)++t->events;
        if(!t->captured){t->before=t->last;t->after=*s;t->before_us=t->last_us;t->after_us=us;t->captured=true;}
    }
    t->last=*s;t->last_us=us;t->have=true;
}
#endif
