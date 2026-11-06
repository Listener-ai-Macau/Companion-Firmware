#ifndef COMP_CPU_DUTY_BOUND_H
#define COMP_CPU_DUTY_BOUND_H
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

/* Every instant is busy unless a masked WFI has a measured lower bound on
 * sleep. IRQ, observer, entry/return and unobserved time are therefore busy.
 * For a wait that crosses a one-second edge, charge its entire possible
 * busy cost to EACH fragment. This can overestimate busy, never understate it.
 * This is an upper bound on fixed non-overlapping one-second windows, not
 * current, instruction attribution or an all-alignment rolling maximum. */
typedef struct {
    uint32_t last_us,window_us,sleep_lower_us;
    uint32_t windows,peak_busy_upper_us,invalid,waits,proven_waits;
    bool have_stamp;
} comp_cpu_duty_bound_t;
_Static_assert(sizeof(comp_cpu_duty_bound_t)<=36u,"bounded CPU duty ledger");

static inline void comp_cpu_duty_account(comp_cpu_duty_bound_t *s,
    uint32_t now,bool valid,uint32_t busy_upper_us)
{
    if(!valid){++s->invalid;s->have_stamp=false;s->window_us=0u;s->sleep_lower_us=0u;return;}
    if(!s->have_stamp){s->last_us=now;s->have_stamp=true;return;}
    uint32_t delta=now-s->last_us;s->last_us=now;
    if(delta>2000000u){++s->invalid;s->have_stamp=false;s->window_us=0u;s->sleep_lower_us=0u;return;}
    while(delta){
        uint32_t n=1000000u-s->window_us;if(n>delta)n=delta;
        if(n>busy_upper_us)s->sleep_lower_us+=n-busy_upper_us;
        s->window_us+=n;delta-=n;
        if(s->window_us==1000000u){
            uint32_t upper=1000000u-s->sleep_lower_us;
            if(!s->windows||upper>s->peak_busy_upper_us)s->peak_busy_upper_us=upper;
            if(s->windows==UINT32_MAX){++s->invalid;return;}
            ++s->windows;s->window_us=0u;s->sleep_lower_us=0u;
        }
    }
}
static inline void comp_cpu_duty_busy(comp_cpu_duty_bound_t *s,uint32_t now,bool valid)
{comp_cpu_duty_account(s,now,valid,UINT32_MAX);}
/* Endpoints of the independent wall clock are rounded down to microseconds.
 * The cycle interval encloses the entire wall interval; ceil division plus
 * one additional microsecond bounds its active part despite quantisation.
 * DWT remaining clocked during WFI merely produces no useful sleep credit. */
static inline uint32_t comp_cpu_duty_wait_busy_upper(uint32_t cycles,uint32_t core_hz)
{
    if(!core_hz||!cycles)return UINT32_MAX;
    uint64_t upper=((uint64_t)cycles*1000000u+core_hz-1u)/core_hz+1u;
    return upper<UINT32_MAX?(uint32_t)upper:UINT32_MAX;
}
#endif
