#include "cpu_residence.h"
#include "ble/ble_micro_observation.h"
#include <stdio.h>
#include <assert.h>

static void exact_nested_ledger(void)
{
    comp_cpu_residence_t p;comp_cpu_residence_begin(&p,7u,61439820u,0u,true);
    comp_cpu_residence_wait(&p,100000u,true,true);
    comp_cpu_residence_irq_enter(&p,150000u,true);
    comp_cpu_residence_irq_enter(&p,160000u,true);
    comp_cpu_residence_irq_exit(&p,170000u,true);
    comp_cpu_residence_irq_exit(&p,180000u,true);
    comp_cpu_residence_wait(&p,230000u,true,false);
    comp_cpu_residence_irq_enter(&p,300000u,true);
    comp_cpu_residence_irq_exit(&p,470000u,true);
    comp_cpu_residence_poll(&p,1000000u,true);
    assert(p.stats.windows==1u&&p.stats.last_window[0]==700000u&&p.stats.last_window[1]==200000u&&p.stats.last_window[2]==100000u);
    assert(p.stats.peak_busy_us==900000u&&p.stats.peak_irq_us==200000u&&p.stats.irq_entries==3u&&p.stats.nested_entries==1u);
    assert(p.stats.peak_busy_window==1u&&p.stats.peak_busy_irq_us==200000u);
    comp_cpu_residence_end(&p,1050000u,true);
    assert(!p.active&&p.window_us==50000u&&p.bucket[0]==50000u&&p.stats.total_us[0]+p.stats.total_us[1]+p.stats.total_us[2]==1050000u);
    comp_cpu_residence_stats_t saved=p.stats;
    comp_cpu_residence_irq_enter(&p,1100000u,true);comp_cpu_residence_poll(&p,1200000u,true);
    assert(!memcmp(&saved,&p.stats,sizeof(saved)));
    puts("PASS exact1s ledger=700000thread+200000IRQ+100000wait; nested IRQ counted once; frozen partial retained");
}
static void split_and_wrap(void)
{
    comp_cpu_residence_t p;uint32_t base=UINT32_MAX-100u;
    comp_cpu_residence_begin(&p,8u,98303712u,base,true);
    comp_cpu_residence_wait(&p,base+400000u,true,true);
    comp_cpu_residence_wait(&p,base+1500000u,true,false);
    comp_cpu_residence_end(&p,base+2300000u,true);
    assert(p.stats.windows==2u&&p.window_us==300000u&&p.stats.peak_busy_us==500000u&&
        p.stats.total_us[0]==1200000u&&p.stats.total_us[2]==1100000u&&!p.stats.clock_errors&&!p.stats.order_errors);
    /* Every full window is exactly one second, even when one checkpoint
     * crosses the boundary or the public32-bit microsecond clock wraps. */
    assert(p.stats.last_window[0]+p.stats.last_window[1]+p.stats.last_window[2]==1000000u);
    assert(p.stats.peak_busy_window==2u&&p.stats.peak_busy_irq_us==0u);
    puts("PASS fixed-window split and32bit clock wrap; totals survive >one window without averaging away peak");
}
static void invalid_is_not_idle(void)
{
    comp_cpu_residence_t p;comp_cpu_residence_begin(&p,9u,61439820u,1000u,true);
    comp_cpu_residence_poll(&p,900u,true);assert(p.stats.clock_errors==1u&&!p.have_stamp&&p.stats.invalid_windows==1u);
    assert(p.stats.last_bad_kind==0x206u&&p.stats.last_bad_delta_us==UINT32_MAX-99u);
    comp_cpu_residence_poll(&p,1100u,false);assert(p.stats.clock_errors==2u);
    assert(p.stats.last_bad_kind==0x106u&&p.stats.last_bad_delta_us==0u);
    comp_cpu_residence_poll(&p,1200u,true);
    comp_cpu_residence_irq_exit(&p,1250u,true);assert(p.stats.order_errors==1u);
    comp_cpu_residence_wait(&p,1300u,true,false);assert(p.stats.order_errors==2u);
    comp_cpu_residence_reference(&p,10000u,10u,true);
    comp_cpu_residence_reference(&p,1010000u,1030u,true);assert(p.stats.reference_errors==1u);
    comp_cpu_residence_reference(&p,2010000u,2054u,true);assert(p.stats.reference_errors==1u);
    comp_cpu_residence_reference(&p,3010000u,3078u,false);assert(p.stats.reference_errors==2u);
    comp_cpu_residence_end(&p,1400u,true);assert(!p.active&&!p.stats.windows);
    puts("PASS backwards/fallback/unpaired IRQ/wait/independent RTC mismatch invalidate; no0percent-as-success");
}
static void pending_and_no_irq_wait(void)
{
    uint32_t normal=comp_v11_ble_micro_stamp(50u,61438u,60000u,false);
    uint32_t before_hal=comp_v11_ble_micro_stamp(49u,61438u,60000u,true);
    assert(normal==before_hal);
    comp_cpu_residence_t p;comp_cpu_residence_begin(&p,10u,61439820u,0u,true);
    comp_cpu_residence_wait(&p,100u,true,true);comp_cpu_residence_wait(&p,100u,true,false);
    comp_cpu_residence_wait(&p,200u,true,true);
    comp_cpu_residence_irq_enter(&p,220u,true);comp_cpu_residence_irq_exit(&p,240u,true);
    /* IRQ before the WFI instruction still returns to the SAME measured
     * wait scope; it cannot make the actual later sleep count as busy. */
    comp_cpu_residence_wait(&p,1000u,true,false);comp_cpu_residence_end(&p,1100u,true);
    assert(p.stats.total_us[0]==300u&&p.stats.total_us[1]==20u&&p.stats.total_us[2]==780u&&p.stats.wfi_entries==2u);
    assert(!p.stats.windows); /* partial is not a one-second qualification */
    puts("PASS SysTick before/afterHAL same epoch; spuriousWFI/pre-WFI IRQ/noIRQ wake scope consistent; partial never full-window");
}
int main(void)
{
    exact_nested_ledger();split_and_wrap();invalid_is_not_idle();pending_and_no_irq_wait();
    printf("CPU_RESIDENCE_MODEL_SOFTWARE_ONLY state_bytes=%zu physicalCpuDuty/lowClock/current NOT_QUALIFIED\n",sizeof(comp_cpu_residence_t));return 0;
}
