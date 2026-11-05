#ifndef COMP_V11_CPU_RESIDENCE_H
#define COMP_V11_CPU_RESIDENCE_H
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

enum {COMP_CPU_THREAD=0,COMP_CPU_IRQ,COMP_CPU_WFI_ENVELOPE,COMP_CPU_BUCKETS};
/* Read-only-clock wall residence, not DWT instruction cycles or current.
 * WFI_ENVELOPE includes its non-IRQ call/return boundary overhead. Actual
 * sleep and physical CPU duty require calibration; do not claim QM14 from
 * this lower bound on busy time alone. All returned IRQ C bodies are hooked. */
typedef struct {
    uint64_t total_us[COMP_CPU_BUCKETS];
    uint32_t token,core_hz,windows,invalid_windows,clock_errors,order_errors;
    uint32_t reference_errors,peak_busy_us,peak_irq_us,max_poll_gap_us;
    uint32_t peak_busy_window,peak_busy_irq_us;
    uint32_t last_window[COMP_CPU_BUCKETS];
    uint32_t irq_entries,nested_entries,wfi_entries;
    uint32_t last_bad_kind,last_bad_delta_us;
} comp_cpu_residence_stats_t;
typedef struct {
    comp_cpu_residence_stats_t stats;
    uint32_t last_us,window_us,bucket[COMP_CPU_BUCKETS],last_poll_us;
    uint32_t reference_us,reference_ticks;
    uint8_t irq_depth,observer_kind;
    bool waiting,have_stamp,reference_valid;
    volatile bool active;
} comp_cpu_residence_t;
_Static_assert(sizeof(comp_cpu_residence_t)<=152u,"bounded CPU residence state");

static inline void comp_cpu_residence_bad_clock(comp_cpu_residence_t *p,uint32_t reason,uint32_t delta)
{
    ++p->stats.clock_errors;++p->stats.invalid_windows;
    p->stats.last_bad_kind=reason|p->observer_kind;p->stats.last_bad_delta_us=delta;
    p->have_stamp=false;p->window_us=0u;memset(p->bucket,0,sizeof(p->bucket));
}
static inline void comp_cpu_residence_account(comp_cpu_residence_t *p,uint32_t now,bool valid)
{
    if(!p->active)return;
    if(!valid){comp_cpu_residence_bad_clock(p,0x100u,0u);return;}
    if(!p->have_stamp){p->last_us=now;p->last_poll_us=now;p->have_stamp=true;return;}
    uint32_t delta=now-p->last_us;p->last_us=now;
    /* No silent backwards clock, missed multi-wrap, or >2s blind interval.
     * Normal SysTick interrupts and foreground checkpoints are much shorter. */
    if(delta>2000000u){comp_cpu_residence_bad_clock(p,0x200u,delta);return;}
    unsigned mode=p->irq_depth?COMP_CPU_IRQ:p->waiting?COMP_CPU_WFI_ENVELOPE:COMP_CPU_THREAD;
    p->stats.total_us[mode]+=delta;
    while(delta) {
        uint32_t n=1000000u-p->window_us;if(n>delta)n=delta;
        p->bucket[mode]+=n;p->window_us+=n;delta-=n;
        if(p->window_us==1000000u) {
            uint32_t busy=p->bucket[COMP_CPU_THREAD]+p->bucket[COMP_CPU_IRQ];
            if(!p->stats.windows || busy>p->stats.peak_busy_us) {
                p->stats.peak_busy_us=busy;
                p->stats.peak_busy_window=p->stats.windows+1u;
                p->stats.peak_busy_irq_us=p->bucket[COMP_CPU_IRQ];
            }
            if(p->bucket[COMP_CPU_IRQ]>p->stats.peak_irq_us)p->stats.peak_irq_us=p->bucket[COMP_CPU_IRQ];
            memcpy(p->stats.last_window,p->bucket,sizeof(p->bucket));++p->stats.windows;
            memset(p->bucket,0,sizeof(p->bucket));p->window_us=0u;
        }
    }
}
static inline void comp_cpu_residence_begin(comp_cpu_residence_t *p,uint32_t token,uint32_t hz,uint32_t now,bool valid)
{
    memset(p,0,sizeof(*p));p->stats.token=token;p->stats.core_hz=hz;
    p->active=true;p->observer_kind=1u;comp_cpu_residence_account(p,now,valid);
}
static inline void comp_cpu_residence_irq_enter(comp_cpu_residence_t *p,uint32_t now,bool valid)
{
    if(!p->active)return;
    p->observer_kind=2u;comp_cpu_residence_account(p,now,valid);
    if(p->irq_depth==UINT8_MAX){++p->stats.order_errors;return;}
    if(p->irq_depth)++p->stats.nested_entries;
    ++p->irq_depth;++p->stats.irq_entries;
}
static inline void comp_cpu_residence_irq_exit(comp_cpu_residence_t *p,uint32_t now,bool valid)
{
    if(!p->active)return;
    p->observer_kind=3u;comp_cpu_residence_account(p,now,valid);
    if(p->irq_depth)--p->irq_depth;else ++p->stats.order_errors;
}
static inline void comp_cpu_residence_wait(comp_cpu_residence_t *p,uint32_t now,bool valid,bool enter)
{
    if(!p->active)return;
    p->observer_kind=enter?4u:5u;comp_cpu_residence_account(p,now,valid);
    if(p->irq_depth||p->waiting==enter){++p->stats.order_errors;return;}
    p->waiting=enter;if(enter)++p->stats.wfi_entries;
}
static inline void comp_cpu_residence_poll(comp_cpu_residence_t *p,uint32_t now,bool valid)
{
    if(!p->active)return;
    p->observer_kind=6u;comp_cpu_residence_account(p,now,valid);
    if(valid&&p->have_stamp) {
        uint32_t gap=now-p->last_poll_us;
        if(gap>p->stats.max_poll_gap_us)p->stats.max_poll_gap_us=gap;
        p->last_poll_us=now;
    }
}
static inline void comp_cpu_residence_reference(comp_cpu_residence_t *p,uint32_t now,uint32_t rtc,bool valid)
{
    if(!p->active)return;
    if(!valid){++p->stats.reference_errors;p->reference_valid=false;return;}
    if(p->reference_valid) {
        uint32_t wall=now-p->reference_us,ticks=rtc-p->reference_ticks;
        uint64_t independent=(uint64_t)ticks*1000000u/1024u;
        uint64_t difference=independent>wall?independent-wall:wall-independent;
        /* Endpoint RTC quantization plus short stamp skew. A disagreement
         * invalidates the capture as a CPU qualification; no repair of time. */
        if(difference>3000u)++p->stats.reference_errors;
    }
    p->reference_valid=true;p->reference_us=now;p->reference_ticks=rtc;
}
static inline void comp_cpu_residence_end(comp_cpu_residence_t *p,uint32_t now,bool valid)
{
    if(!p->active)return;
    p->observer_kind=7u;comp_cpu_residence_account(p,now,valid);
    if(p->irq_depth||p->waiting)++p->stats.order_errors;
    p->active=false;
}
#endif
