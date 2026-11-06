#include "clock_target.h"
#include "companion_duration_stats.h"
#if COMPANION_FINE_DURATION_CLOCK
#include "stm32wbaxx_hal.h"
#include "ble/ble_micro_observation.h"
bool comp_duration_clock_us(uint32_t *stamp)
{
    /* Reuse the qualified read-only SysTick projection. DWT is shared with
     * ST's delay code and must not be enabled/reset for measurement. A clock
     * transition/masked IRQ or ambiguous read invalidates the observation. */
    if(!stamp||__get_IPSR()||__get_PRIMASK()||HAL_GetTickFreq()!=HAL_TICK_FREQ_1KHZ||
       (SysTick->CTRL&(SysTick_CTRL_ENABLE_Msk|SysTick_CTRL_CLKSOURCE_Msk))!=
           (SysTick_CTRL_ENABLE_Msk|SysTick_CTRL_CLKSOURCE_Msk))return false;
    for(unsigned tries=0u;tries<4u;tries++) {
        uint32_t tick=HAL_GetTick(),load=SysTick->LOAD,value=SysTick->VAL;
        bool pending=(SCB->ICSR&SCB_ICSR_PENDSTSET_Msk)!=0u;
        uint32_t after=HAL_GetTick(),value_after=SysTick->VAL;
        if(SystemCoreClock>=1000u&&load==SystemCoreClock/1000u-1u&&
           comp_v11_ble_micro_consistent(tick,after,load,value,value_after)) {
            *stamp=comp_v11_ble_micro_stamp(tick,load,value,pending);return true;
        }
    }
    return false;
}
#endif
#ifdef COMPANION_WBA_BLE_LINKED
#include "wba_retained_clock.h"
#include "stm32wbaxx_hal.h"
extern RTC_HandleTypeDef hrtc;
static comp_wba_retained_clock_t retained;
static bool initialized;
/* ST timer_if owns BKP0..2. Product time owns BKP4..15 exclusively. */
static uint32_t read_word(void *context,unsigned index)
{(void)context;return HAL_RTCEx_BKUPRead(&hrtc,RTC_BKP_DR4+index);}
static bool write_word(void *context,unsigned index,uint32_t value)
{
    (void)context;HAL_RTCEx_BKUPWrite(&hrtc,RTC_BKP_DR4+index,value);
    return HAL_RTCEx_BKUPRead(&hrtc,RTC_BKP_DR4+index)==value;
}
bool comp_v11_clock_domain_continuous(void)
{
    return __HAL_RCC_GET_FLAG(RCC_FLAG_LSERDY) &&
        __HAL_RCC_GET_RTC_SOURCE()==RCC_RTCCLKSOURCE_LSE &&
        !__HAL_RCC_GET_FLAG(RCC_FLAG_LSECSSD) &&
        (RTC->ICSR&(RTC_ICSR_BIN|RTC_ICSR_INITS|RTC_ICSR_INIT))==RTC_BINARY_ONLY &&
        ((RTC->PRER&RTC_PRER_PREDIV_A)>>RTC_PRER_PREDIV_A_Pos)==31u;
}
static bool ticks(uint32_t *out)
{
    if (!comp_v11_clock_domain_continuous()) return false;
    /* Direct binary reads; never change the radio timer, alarm, or prescaler. */
    for(unsigned attempt=0;attempt<8;++attempt) {
        uint32_t a=RTC->SSR,b=RTC->SSR;
        if(a==b) {*out=UINT32_MAX-a;return true;}
    }
    return false;
}
void comp_v11_clock_restore(comp_clock_t *clock,bool continuous)
{
    comp_wba_clock_port_t port={NULL,read_word,write_word};uint32_t t=0;
    bool ready=ticks(&t);
    initialized=true;
    (void)comp_wba_retained_clock_mount(&retained,&port,continuous && ready,t);
    comp_v11_clock_poll(clock,HAL_GetTick(),false);
}
void comp_v11_clock_checkpoint(comp_clock_t *clock)
{
    uint32_t t;
    if(!initialized || !clock->valid || !ticks(&t))return;
    comp_clock_poll(clock,HAL_GetTick());
    /* Keep current user-supplied time on write failure, but revoke the older
     * persistent value so a reset cannot silently resurrect stale time. */
    uint32_t utc=(clock->utc_seconds%86400u)*1000u+clock->milliseconds;
    bool saved=clock->calendar_valid?
        comp_wba_retained_clock_save_unix(&retained,t,clock->utc_seconds,clock->milliseconds):
        comp_wba_retained_clock_save(&retained,t,utc);
    if(!saved) {
        comp_wba_retained_clock_invalidate(&retained);
        retained.anchor_ticks=t;retained.anchor_utc_ms=utc;retained.valid=true;
        retained.anchor_day=clock->calendar_valid?(uint16_t)(clock->utc_seconds/86400u):UINT16_MAX;
    }
}
void comp_v11_clock_poll(comp_clock_t *clock,uint32_t now,bool allow_checkpoint)
{
    uint32_t t,utc;
    if(!initialized)return;
    if(!ticks(&t)) {comp_wba_retained_clock_invalidate(&retained);clock->valid=false;clock->calendar_valid=false;return;}
    if(!comp_wba_retained_clock_now(&retained,t,&utc)) {clock->valid=false;clock->calendar_valid=false;return;}
    clock->utc_seconds=utc/1000u;clock->milliseconds=(uint16_t)(utc%1000u);
    clock->calendar_valid=retained.anchor_day!=UINT16_MAX;
    if(clock->calendar_valid && !comp_wba_retained_clock_now_unix(&retained,t,
            &clock->utc_seconds,&clock->milliseconds)) {clock->valid=false;clock->calendar_valid=false;return;}
    clock->tick=now;clock->valid=true;
    if(allow_checkpoint && t-retained.anchor_ticks>=60u*1024u)
        comp_v11_clock_checkpoint(clock);
}
#else
bool comp_v11_clock_domain_continuous(void){return false;}
void comp_v11_clock_restore(comp_clock_t *c,bool continuous){(void)c;(void)continuous;}
void comp_v11_clock_checkpoint(comp_clock_t *c){(void)c;}
void comp_v11_clock_poll(comp_clock_t *c,uint32_t now,bool allow){(void)c;(void)now;(void)allow;}
#endif
