#ifndef COMP_CPU_COUNTER_CLOCK_H
#define COMP_CPU_COUNTER_CLOCK_H
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
/* A free-running peripheral counter, independent of exception/HAL tick phase.
 * Convert deltas, not absolute CNT, so both counter and microsecond wraps work.
 * Q31 is prepared once: no division or tick-phase repair in the read path.
 * Quantisation is below 0.00025us/second for a counter near 1MHz. */
typedef struct {
    uint32_t raw,us,fraction,q31,timer_hz,divider,max_delta;
} comp_cpu_counter_clock_t;
static inline bool comp_cpu_counter_clock_init(comp_cpu_counter_clock_t *c,
    uint32_t timer_hz,uint32_t initial_raw)
{
    memset(c,0,sizeof(*c));
    if(timer_hz<1000000u || timer_hz>200000000u)return false;
    c->timer_hz=timer_hz;c->divider=timer_hz/1000000u;c->raw=initial_raw;
    c->q31=(uint32_t)((((uint64_t)c->divider*1000000u<<31u)+timer_hz/2u)/timer_hz);
    c->max_delta=(uint32_t)(((uint64_t)timer_hz*2u)/c->divider);
    return c->q31!=0u;
}
static inline bool comp_cpu_counter_clock_read(comp_cpu_counter_clock_t *c,
    uint32_t raw,uint32_t *us)
{
    uint32_t delta=raw-c->raw;c->raw=raw;
    if(!c->q31 || delta>c->max_delta)return false;
    uint64_t scaled=(uint64_t)delta*c->q31+c->fraction;
    c->fraction=(uint32_t)scaled&UINT32_C(0x7fffffff);
    c->us+=(uint32_t)(scaled>>31u);*us=c->us;return true;
}
#endif
