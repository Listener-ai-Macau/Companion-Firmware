#ifndef COMP_V11_BLE_EXEC_OBSERVATION_H
#define COMP_V11_BLE_EXEC_OBSERVATION_H
#include "ble_route_observation.h"
/* Reuse slot0's16B: starts for host/LL plus their enclosing elapsed sums.
 * Ready-to-run retains slots1/2. No ISR modifies these execution starts.
 * Nested same-task or unmatched edges invalidate that job's coverage;
 * elapsed includes nested other tasks/IRQs, and totals must not be added. */
static inline volatile uint32_t *comp_v11_ble_exec_start_word(comp_v11_ble_route_observation_t *o,uint8_t job)
{ return job==1u?&o->job[0].since_us:&o->job[0].word; }
static inline void comp_v11_ble_exec_begin(comp_v11_ble_route_observation_t *o,uint8_t job,uint32_t now)
{
    volatile uint32_t *start=comp_v11_ble_exec_start_word(o,job);
    if(*start || !now){(void)route_or(&o->job[job].word,ROUTE_UNMARKED);return;}
    *start=now;
}
static inline void comp_v11_ble_exec_end(comp_v11_ble_route_observation_t *o,uint8_t job,uint32_t now)
{
    volatile uint32_t *start=comp_v11_ble_exec_start_word(o,job);
    if(!*start){(void)route_or(&o->job[job].word,ROUTE_UNMARKED);return;}
    uint32_t elapsed=now-*start;*start=0u;
    if(job==1u)o->job[0].total_us+=elapsed;else o->job[0].max_us+=elapsed;
}
#endif
