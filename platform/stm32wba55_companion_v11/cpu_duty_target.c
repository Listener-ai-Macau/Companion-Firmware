#include "cpu_duty_target.h"
#if COMPANION_WBA_CPU_DUTY_OBSERVER
#include "stm32wbaxx_hal.h"
#include "clock_target.h"
#include "cpu_duty_bound.h"
#include "cpu_counter_clock.h"

/* RM0493 12.8.32: TIM2SMEN=0 gates both TIM2 clocks in Sleep/Stop, while
 * TIM2EN retains them in Run. Count Run time, including IRQs and this code,
 * against the independent retained 1024Hz RTC. No DWT/IRQ hook/extra IRQ,
 * WFI masking, cache experiment, audio buffer or heap. A debug configuration
 * that keeps the clock running in sleep can only make this bound worse.
 * The owned counter excludes Stop1; no normal product clock is changed. */
#define CPU_BOUNDARY_MARGIN_US 2200u
#define CPU_SNAPSHOT_MAX_US 40u
static struct {
    comp_cpu_duty_bound_t duty;
    comp_cpu_counter_clock_t clock;
    uint32_t token,core_hz,bus_config,last_ticks,wall_us,last_active_us;
    uint8_t wall_fraction,invalid_reason;
    bool active,recording,timer_owned,sleep_was_on;
} observer;
_Static_assert(sizeof(observer)<=96u,"compact CPU duty observer RAM");
enum {CPU_FOREIGN_TIMER=1,CPU_RTC_DOMAIN,CPU_TIMER_CONFIG,CPU_SLOW_SNAPSHOT,
      CPU_LATE_SAMPLE,CPU_STUCK_COUNTER,CPU_COUNTER_CONVERSION,CPU_EXCESS_ACTIVE,
      CPU_DEBUG_FREEZE,CPU_CLOCK_SETUP};
static void reject(uint8_t reason)
{
    if(!observer.duty.invalid)observer.invalid_reason=reason;
    ++observer.duty.invalid;
}

static bool timer_matches(void)
{
    return observer.timer_owned&&__HAL_RCC_TIM2_IS_CLK_ENABLED()&&
        !__HAL_RCC_TIM2_IS_CLK_SLEEP_ENABLED()&&
        !(DBGMCU->APB1LFZR&DBGMCU_APB1LFZR_DBG_TIM2_STOP)&&
        TIM2->CR1==TIM_CR1_CEN&&TIM2->DIER==0u&&TIM2->SMCR==0u&&
        TIM2->PSC==observer.clock.divider-1u&&TIM2->ARR==UINT32_MAX&&
        observer.core_hz==SystemCoreClock&&
        (RCC->CFGR2&(RCC_CFGR2_HPRE|RCC_CFGR2_PPRE1))==observer.bus_config;
}
static void sample(void)
{
    if(!timer_matches()){reject(CPU_TIMER_CONFIG);return;}
    if(!comp_v11_clock_domain_continuous()){reject(CPU_RTC_DOMAIN);return;}
    /* IRQs are masked by the caller only for this bounded register snapshot,
     * never around WFI. Reject a snapshot wider than its explicit bound. */
    uint32_t before=TIM2->CNT,ticks=UINT32_MAX-RTC->SSR,raw=TIM2->CNT;
    uint32_t elapsed=ticks-observer.last_ticks;
    uint64_t snapshot=(uint64_t)(raw-before)*observer.clock.divider*1000000u;
    if(snapshot>(uint64_t)CPU_SNAPSHOT_MAX_US*observer.clock.timer_hz){reject(CPU_SLOW_SNAPSHOT);return;}
    if(elapsed>2048u){reject(CPU_LATE_SAMPLE);return;}
    if(!elapsed)return;
    uint32_t active=0u,previous=observer.last_active_us;
    if(raw==observer.clock.raw){reject(CPU_STUCK_COUNTER);return;}
    if(!comp_cpu_counter_clock_read(&observer.clock,raw,&active)){reject(CPU_COUNTER_CONVERSION);return;}
    uint32_t scaled=elapsed*15625u+observer.wall_fraction;
    observer.wall_us+=scaled>>4u;observer.wall_fraction=(uint8_t)(scaled&15u);
    observer.last_ticks=ticks;observer.last_active_us=active;
    uint32_t busy=active-previous,wall=observer.wall_us-observer.duty.last_us;
    /* Two RTC endpoints, two <=40us snapshot offsets, active counter
     * rounding and frequency margin are charged BUSY once per second.
     * Charge an entire crossing interval to EACH window fragment below. */
    if((uint64_t)busy>(uint64_t)wall+CPU_BOUNDARY_MARGIN_US){
        reject(CPU_EXCESS_ACTIVE);return;
    }
    comp_cpu_duty_account(&observer.duty,observer.wall_us,true,busy);
}
static void timer_release(void)
{
    if(!observer.timer_owned)return;
    if(timer_matches()){
        TIM2->CR1=0u;
        if(observer.sleep_was_on)__HAL_RCC_TIM2_CLK_SLEEP_ENABLE();
        __HAL_RCC_TIM2_CLK_DISABLE();
    }else reject(CPU_TIMER_CONFIG);
    observer.timer_owned=false;
}
bool comp_cpu_duty_counter_owned(void){return observer.timer_owned;}
void comp_cpu_duty_begin(uint32_t token,bool recording)
{
    if(!token||__get_IPSR())return;
    if(!observer.active&&observer.recording&&!recording)return;
    if(observer.active){
        if(observer.recording||!recording)return;
        comp_cpu_duty_end(observer.token,false);
    }
    uint32_t mask=__get_PRIMASK();__disable_irq();
    memset(&observer,0,sizeof(observer));observer.token=token;
    observer.recording=recording;observer.active=true;observer.core_hz=SystemCoreClock;
    if(__HAL_RCC_TIM2_IS_CLK_ENABLED()||NVIC_GetEnableIRQ(TIM2_IRQn)){
        reject(CPU_FOREIGN_TIMER);__set_PRIMASK(mask);return;
    }
    if(DBGMCU->APB1LFZR&DBGMCU_APB1LFZR_DBG_TIM2_STOP){reject(CPU_DEBUG_FREEZE);__set_PRIMASK(mask);return;}
    if(!comp_v11_clock_domain_continuous()){reject(CPU_RTC_DOMAIN);__set_PRIMASK(mask);return;}
    uint32_t hz=HAL_RCC_GetPCLK1Freq();
    if((RCC->CFGR2&RCC_CFGR2_PPRE1)!=RCC_HCLK_DIV1){
        if(hz>UINT32_MAX/2u){reject(CPU_CLOCK_SETUP);__set_PRIMASK(mask);return;}hz*=2u;
    }
    if(!comp_cpu_counter_clock_init(&observer.clock,hz,0u)){
        reject(CPU_CLOCK_SETUP);__set_PRIMASK(mask);return;
    }
    observer.bus_config=RCC->CFGR2&(RCC_CFGR2_HPRE|RCC_CFGR2_PPRE1);
    observer.sleep_was_on=__HAL_RCC_TIM2_IS_CLK_SLEEP_ENABLED();
    __HAL_RCC_TIM2_CLK_ENABLE();__HAL_RCC_TIM2_FORCE_RESET();__HAL_RCC_TIM2_RELEASE_RESET();
    TIM2->CR1=0u;TIM2->DIER=0u;TIM2->SMCR=0u;TIM2->CCER=0u;
    TIM2->PSC=observer.clock.divider-1u;TIM2->ARR=UINT32_MAX;
    TIM2->EGR=TIM_EGR_UG;TIM2->SR=0u;TIM2->CNT=0u;
    __HAL_RCC_TIM2_CLK_SLEEP_DISABLE();TIM2->CR1=TIM_CR1_CEN;observer.timer_owned=true;
    observer.last_ticks=UINT32_MAX-RTC->SSR;
    if(!timer_matches())reject(CPU_TIMER_CONFIG);
    comp_cpu_duty_account(&observer.duty,0u,true,0u);
    __set_PRIMASK(mask);
}
void comp_cpu_duty_end(uint32_t token,bool recording)
{
    if(!observer.active||observer.recording!=recording||(recording&&observer.token!=token)||__get_IPSR())return;
    uint32_t mask=__get_PRIMASK();__disable_irq();sample();
    observer.active=false;timer_release();__set_PRIMASK(mask);
}
void comp_cpu_duty_poll(void)
{
    if(!observer.active||__get_IPSR())return;
    uint32_t mask=__get_PRIMASK();__disable_irq();sample();__set_PRIMASK(mask);
}
void comp_cpu_duty_wait_enter(void){}
void comp_cpu_duty_wait_exit(void){}
void comp_cpu_duty_wfi(void){if(observer.active)++observer.duty.waits;__WFI();}
comp_cpu_duty_snapshot_t comp_cpu_duty_snapshot(void)
{
    uint32_t mask=__get_PRIMASK();__disable_irq();
    uint32_t peak=observer.duty.peak_busy_upper_us;
    if(observer.duty.windows)peak=peak>1000000u-CPU_BOUNDARY_MARGIN_US?
        1000000u:peak+CPU_BOUNDARY_MARGIN_US;
    comp_cpu_duty_snapshot_t r={.enabled=true,.active=observer.active,.recording=observer.recording,
        .windows=observer.duty.windows,.peak_busy_upper_us=peak,
        .invalid=observer.duty.invalid,.waits=observer.duty.waits,
        .token=observer.token,.invalid_reason=observer.invalid_reason};
    __set_PRIMASK(mask);return r;
}
#endif
