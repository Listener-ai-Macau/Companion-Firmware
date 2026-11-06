#ifndef COMP_CPU_DUTY_BOUND_H
#define COMP_CPU_DUTY_BOUND_H
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

/* Account a measured active-time upper bound; all unproved time is busy.
 * IRQ, observer and entry/return work must be included by the target clock.
 * For a sample that crosses a one-second edge, charge its entire possible
 * busy cost to EACH fragment. This can overestimate busy, never understate it.
 * This is an upper bound on fixed non-overlapping one-second windows, not
 * current, instruction attribution or an all-alignment rolling maximum. */
typedef struct {
    uint32_t last_us,window_us,busy_upper_us;
    uint32_t windows,peak_busy_upper_us,invalid,waits;
    bool have_stamp;
} comp_cpu_duty_bound_t;
_Static_assert(sizeof(comp_cpu_duty_bound_t)<=32u,"bounded CPU duty ledger");

static inline void comp_cpu_duty_account(comp_cpu_duty_bound_t *s,
    uint32_t now,bool valid,uint32_t busy_upper_us)
{
    if(!valid){++s->invalid;s->have_stamp=false;s->window_us=0u;s->busy_upper_us=0u;return;}
    if(!s->have_stamp){s->last_us=now;s->have_stamp=true;return;}
    uint32_t delta=now-s->last_us;s->last_us=now;
    if(delta>2000000u){++s->invalid;s->have_stamp=false;s->window_us=0u;s->busy_upper_us=0u;return;}
    while(delta){
        uint32_t n=1000000u-s->window_us;if(n>delta)n=delta;
        /* An RTC-quantized short interval can contain more active time than
         * its reported wall delta. Keep ALL of it, rather than clipping each
         * interval and losing active time repeatedly. Only saturate the
         * completed-second bound at100%; duplicate a crossing interval's
         * entire cost into each adjacent window. */
        uint32_t cost=busy_upper_us==UINT32_MAX?n:busy_upper_us;
        s->busy_upper_us=cost>1000000u-s->busy_upper_us?
            1000000u:s->busy_upper_us+cost;
        s->window_us+=n;delta-=n;
        if(s->window_us==1000000u){
            uint32_t upper=s->busy_upper_us;
            if(!s->windows||upper>s->peak_busy_upper_us)s->peak_busy_upper_us=upper;
            if(s->windows==UINT32_MAX){++s->invalid;return;}
            ++s->windows;s->window_us=0u;s->busy_upper_us=0u;
        }
    }
}
static inline void comp_cpu_duty_busy(comp_cpu_duty_bound_t *s,uint32_t now,bool valid)
{comp_cpu_duty_account(s,now,valid,UINT32_MAX);}
#endif
