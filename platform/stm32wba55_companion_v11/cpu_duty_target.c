#include "cpu_duty_target.h"
#if COMPANION_WBA_CPU_DUTY_OBSERVER
#include "stm32wbaxx_hal.h"
#include "clock_target.h"
#include "cpu_duty_bound.h"
#include "cpu_counter_clock.h"

/* Separate small opt-in observer. No legacy stage arrays, cache trials,
 * UART formatting, IRQ hooks, frame buffers, heap, NVIC writes or DWT reset.
 * ST LL owns CYCCNT during its delays. Borrow ONLY across a PRIMASK=1 WFI,
 * then restore only the two enable bits we acquired before IRQs may run.
 * Unmasked waits receive no sleep credit; all IRQ time stays busy. */
static struct {
    comp_cpu_duty_bound_t duty;
    comp_cpu_counter_clock_t clock;
    uint32_t token,core_hz,bus_config,wait_cycle,wait_raw,reference_us,reference_ticks;
    bool active,recording,timer_owned,sleep_was_on;
    bool waiting,cycle_lease,owned_trcena,owned_cyccnt,reference_valid;
} observer;
_Static_assert(sizeof(observer)<=104u,"compact CPU duty observer RAM");

static bool timer_matches(void)
{
    return observer.timer_owned&&__HAL_RCC_TIM2_IS_CLK_ENABLED()&&
        TIM2->CR1==TIM_CR1_CEN&&TIM2->DIER==0u&&TIM2->SMCR==0u&&
        TIM2->PSC==observer.clock.divider-1u&&TIM2->ARR==UINT32_MAX&&
        observer.core_hz==SystemCoreClock&&
        (RCC->CFGR2&(RCC_CFGR2_HPRE|RCC_CFGR2_PPRE1))==observer.bus_config;
}
static bool timer_stamp(uint32_t *now)
{return timer_matches()&&comp_cpu_counter_clock_read(&observer.clock,TIM2->CNT,now);}
static void reference(uint32_t now)
{
    if(!comp_v11_clock_domain_continuous()){++observer.duty.invalid;observer.reference_valid=false;return;}
    uint32_t ticks=UINT32_MAX-RTC->SSR;
    if(observer.reference_valid){
        uint32_t wall=now-observer.reference_us;
        uint64_t rtc=(uint64_t)(ticks-observer.reference_ticks)*1000000u/1024u;
        uint64_t difference=rtc>wall?rtc-wall:wall-rtc;
        if(difference>3000u)++observer.duty.invalid;
    }
    observer.reference_us=now;observer.reference_ticks=ticks;observer.reference_valid=true;
}
static void timer_release(void)
{
    if(!observer.timer_owned)return;
    if(timer_matches()){
        TIM2->CR1=0u;
        if(!observer.sleep_was_on)__HAL_RCC_TIM2_CLK_SLEEP_DISABLE();
        __HAL_RCC_TIM2_CLK_DISABLE();
    }else ++observer.duty.invalid;
    observer.timer_owned=false;
}
static void cycle_release(void)
{
    if(!observer.cycle_lease)return;
    if(observer.owned_cyccnt)CLEAR_BIT(DWT->CTRL,DWT_CTRL_CYCCNTENA_Msk);
    if(observer.owned_trcena)CLEAR_BIT(DCB->DEMCR,DCB_DEMCR_TRCENA_Msk);
    observer.cycle_lease=false;
}
bool comp_cpu_duty_counter_owned(void){return observer.timer_owned;}
void comp_cpu_duty_begin(uint32_t token,bool recording)
{
    if(!token||__get_IPSR())return;
    /* Do not overwrite the last recording result with its tail upload. */
    if(!observer.active&&observer.recording&&!recording)return;
    if(observer.active){
        if(observer.recording||!recording)return;
        comp_cpu_duty_end(observer.token,false);
    }
    uint32_t mask=__get_PRIMASK();__disable_irq();
    memset(&observer,0,sizeof(observer));observer.token=token;
    observer.recording=recording;observer.active=true;observer.core_hz=SystemCoreClock;
    if(__HAL_RCC_TIM2_IS_CLK_ENABLED()||NVIC_GetEnableIRQ(TIM2_IRQn)){
        ++observer.duty.invalid;__set_PRIMASK(mask);return;
    }
    uint32_t hz=HAL_RCC_GetPCLK1Freq();
    if((RCC->CFGR2&RCC_CFGR2_PPRE1)!=RCC_HCLK_DIV1){
        if(hz>UINT32_MAX/2u){++observer.duty.invalid;__set_PRIMASK(mask);return;}hz*=2u;
    }
    if(!comp_cpu_counter_clock_init(&observer.clock,hz,0u)){
        ++observer.duty.invalid;__set_PRIMASK(mask);return;
    }
    observer.bus_config=RCC->CFGR2&(RCC_CFGR2_HPRE|RCC_CFGR2_PPRE1);
    observer.sleep_was_on=__HAL_RCC_TIM2_IS_CLK_SLEEP_ENABLED();
    __HAL_RCC_TIM2_CLK_ENABLE();__HAL_RCC_TIM2_FORCE_RESET();__HAL_RCC_TIM2_RELEASE_RESET();
    TIM2->CR1=0u;TIM2->DIER=0u;TIM2->SMCR=0u;TIM2->CCER=0u;
    TIM2->PSC=observer.clock.divider-1u;TIM2->ARR=UINT32_MAX;
    TIM2->EGR=TIM_EGR_UG;TIM2->SR=0u;TIM2->CNT=0u;
    __HAL_RCC_TIM2_CLK_SLEEP_ENABLE();TIM2->CR1=TIM_CR1_CEN;observer.timer_owned=true;
    uint32_t now=0u;bool valid=timer_stamp(&now);comp_cpu_duty_busy(&observer.duty,now,valid);
    if(valid)reference(now);
    __set_PRIMASK(mask);
}
void comp_cpu_duty_end(uint32_t token,bool recording)
{
    if(!observer.active||observer.recording!=recording||(recording&&observer.token!=token)||__get_IPSR())return;
    uint32_t mask=__get_PRIMASK();__disable_irq();
    if(observer.waiting||observer.cycle_lease)++observer.duty.invalid;
    cycle_release();uint32_t now=0u;bool valid=timer_stamp(&now);
    if(valid)reference(now);
    comp_cpu_duty_busy(&observer.duty,now,valid);observer.active=false;timer_release();
    __set_PRIMASK(mask);
}
void comp_cpu_duty_poll(void)
{
    if(!observer.active||observer.waiting||__get_IPSR())return;
    uint32_t mask=__get_PRIMASK();__disable_irq();uint32_t now=0u;
    bool valid=timer_stamp(&now);comp_cpu_duty_busy(&observer.duty,now,valid);
    if(valid&&(!observer.reference_valid||now-observer.reference_us>=1000000u))reference(now);
    __set_PRIMASK(mask);
}
void comp_cpu_duty_wait_enter(void)
{
    if(!observer.active)return;
    if(observer.waiting||__get_IPSR()){++observer.duty.invalid;return;}
    uint32_t mask=__get_PRIMASK();__disable_irq();uint32_t now=0u;
    bool valid=timer_stamp(&now);comp_cpu_duty_busy(&observer.duty,now,valid);
    observer.waiting=true;++observer.duty.waits;
    /* Leave unmasked waits wholly busy. No timer/counter writes then race
     * the BLE LL's own interrupt-time delay counter lifecycle. */
    if(mask==1u&&valid&&!(DWT->CTRL&DWT_CTRL_NOCYCCNT_Msk)){
        observer.owned_trcena=!(DCB->DEMCR&DCB_DEMCR_TRCENA_Msk);
        observer.owned_cyccnt=!(DWT->CTRL&DWT_CTRL_CYCCNTENA_Msk);
        SET_BIT(DCB->DEMCR,DCB_DEMCR_TRCENA_Msk);SET_BIT(DWT->CTRL,DWT_CTRL_CYCCNTENA_Msk);
        __DSB();__ISB();
        observer.cycle_lease=true;
        /* Cycle interval encloses the raw wall interval in both directions. */
        observer.wait_cycle=DWT->CYCCNT;observer.wait_raw=TIM2->CNT;
        if(!comp_cpu_counter_clock_read(&observer.clock,observer.wait_raw,&now))valid=false;
        comp_cpu_duty_busy(&observer.duty,now,valid);
    }
    __set_PRIMASK(mask);
}
void comp_cpu_duty_wait_exit(void)
{
    if(!observer.active)return;
    uint32_t mask=__get_PRIMASK();__disable_irq();uint32_t now=0u;
    /* Read wall before cycles, so all active work in that wall span is
     * inside the cycle span. Borrowed DWT is never reset, even if rejected. */
    bool valid=observer.waiting&&timer_matches();
    uint32_t raw=valid?TIM2->CNT:0u;
    uint32_t cycles=observer.cycle_lease?DWT->CYCCNT-observer.wait_cycle:0u,busy=UINT32_MAX;
    if(observer.cycle_lease){
        bool enabled=(DCB->DEMCR&DCB_DEMCR_TRCENA_Msk)&&(DWT->CTRL&DWT_CTRL_CYCCNTENA_Msk);
        if(mask!=1u||__get_IPSR()||!enabled||!cycles)valid=false;
        else busy=comp_cpu_duty_wait_busy_upper(cycles,observer.core_hz);
    }
    cycle_release();observer.waiting=false;
    valid=valid&&comp_cpu_counter_clock_read(&observer.clock,raw,&now);
    if(valid&&busy!=UINT32_MAX&&now-observer.duty.last_us>busy)++observer.duty.proven_waits;
    comp_cpu_duty_account(&observer.duty,now,valid,busy);__set_PRIMASK(mask);
}
comp_cpu_duty_snapshot_t comp_cpu_duty_snapshot(void)
{
    uint32_t mask=__get_PRIMASK();__disable_irq();
    comp_cpu_duty_snapshot_t r={.enabled=true,.active=observer.active,.recording=observer.recording,
        .windows=observer.duty.windows,.peak_busy_upper_us=observer.duty.peak_busy_upper_us,
        .invalid=observer.duty.invalid,.waits=observer.duty.waits,
        .proven_waits=observer.duty.proven_waits,.token=observer.token};
    __set_PRIMASK(mask);return r;
}
#endif
