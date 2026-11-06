#ifndef COMPANION_WBA_AUTOMATIC_STOP1
#define COMPANION_WBA_AUTOMATIC_STOP1 0
#endif
#if defined(COMPANION_WBA_EXPERIMENTAL_STOP1) && COMPANION_WBA_EXPERIMENTAL_STOP1
#include "board_hal.h"
#endif
#include "low_power_target.h"
#include "cpu_profile_target.h"
#if COMPANION_WBA_DUAL_PAIR_CAPTURE
#include "dual_mic_capture.h"
#endif
#ifdef COMPANION_WBA_BLE_LINKED
#include "ble_product.h"
#include "wba_ota_gatt.h"
#endif
static bool foreground_pending(const comp_v11_product_app_t *app)
{
#if COMPANION_WBA_DUAL_PAIR_CAPTURE
    if(comp_v11_dual_pair_foreground_pending(app)) return true;
#endif
    if(app&&comp_wba_recording_product_foreground_pending(&app->recording))return true;
    /* A pending ordinary-display row is foreground work, just like FW124's
     * sendable BLE data. Return to the whole product poll rather than paying
     * a WFI/tick gap for every row. One driver poll still sends at most one
     * row; radio and inputs run between rows, IRQs stay enabled. Capture and
     * playback retain their previous idle policy. Inactive recorder storage
     * work above follows the same bounded foreground handoff. */
    if(app && app->board && !app->board->microphone.running &&
       !app->board->playback_active && !app->runtime.prepare_pending &&
       !app->runtime.start_pending && !app->runtime.command_pending &&
       !app->runtime.capture_active && !app->runtime.stop_pending &&
       comp_ssd1681_wba_ram_write_pending(&app->board->panel)) return true;
#ifdef COMPANION_WBA_BLE_LINKED
    /* The HCI callback has already retired when it leaves complete OTA
     * commands for the next product turn. Do not WFI with that work queued;
     * keep the bounded DATA slice so radio, inputs and audio guards still run
     * every product turn (at most2 DATA, no append after a slow first one). */
    return comp_v11_ota_gatt_foreground_pending() || comp_v11_ble_foreground_pending();
#else
    return false;
#endif
}
#if defined(COMPANION_WBA_BLE_LINKED) && COMPANION_WBA_EXPERIMENTAL_STOP1
#include "ble/main.h"
#include "ble_product.h"
#include "stm32_lpm.h"
#include "stm32_lpm_if.h"
#include "stm32_seq.h"
#include "stm32_timer.h"
#include "timer_if.h"
#include "wba_stop.h"
#include "stm32wbaxx_ll_iwdg.h"

/* Stop1 retains SRAM/peripheral registers. Standby/Stop2 are deliberately
 * absent: PB14 EXTI, display baseline and the in-RAM recording/runtime remain. */
static comp_wba_stop_t stop;
static comp_wba_rtc_clock_t stop_timeline;
static UTIL_TIMER_Object_t wake_timer;
static comp_v11_product_app_t *product;
static uint32_t saved_primask, saved_systick;
static volatile bool timer_elapsed;
static bool clock_restored;
static volatile uint8_t stop_stage;
volatile uint32_t companion_stop1_entries;
static bool trial_armed, trial_window, app_stop_permission, entry_owned;
static uint16_t trial_entries_left;
static uint32_t trial_deadline, last_wake_flags;
static comp_v11_stop_wake_snapshot_t last_wake;
_Static_assert(RCC_AUDIOSYNC_IRQn < 32u * COMP_V11_STOP_IRQ_WORDS,
               "Stop1 wake snapshot must cover the target's last IRQ");
static void capture_pending_irqs(comp_v11_stop_irq_snapshot_t *snapshot)
{
    /* Called only inside the existing PRIMASK transaction. Read-only: never
     * clear a pending IRQ/EXTI edge to make the sleep trial look successful. */
    for (unsigned i=0; i<COMP_V11_STOP_IRQ_WORDS; ++i)
        snapshot->pending_enabled[i]=NVIC->ISPR[i]&NVIC->ISER[i];
    snapshot->icsr=SCB->ICSR;
    snapshot->exti_rising=EXTI->RPR1;
    snapshot->exti_falling=EXTI->FPR1;
}
static bool eligible(comp_v11_product_app_t *app);
static void trial_expire(uint32_t now)
{
    if (trial_armed && (int32_t)(now-trial_deadline)>=0) trial_armed=false;
}
static void trial_entered(void)
{
    ++companion_stop1_entries;
    if (trial_entries_left) --trial_entries_left;
    if (!trial_entries_left) trial_armed=false;
}
extern void LINKLAYER_PLAT_NotifyWFIEnter(void);
extern void LINKLAYER_PLAT_NotifyWFIExit(void);

static uint32_t rtc(void *context)
{ (void)context; return TIMER_IF_GetTimerValue(); }
/* Keep the original HAL SysTick for every ordinary foreground/IRQ path.
 * RTC phase remains continuous across repeated short Stop1 transactions.
 * SysTick is disabled, not reset: its retained partial period belongs to the
 * awake interval and must survive each bounded Stop1 transaction. */
static bool wait_bit(volatile uint32_t *reg, uint32_t mask, uint32_t expected)
{
    uint32_t started=rtc(NULL), spins=0u;
    while ((*reg & mask)!=expected) {
        /* RTC is independent of stopped SysTick. The spin cap also handles
         * a failed LSE without an infinite clock-restoration wait. */
        if (rtc(NULL)-started>=64u || ++spins>=2000000u) return false;
    }
    return true;
}
static bool restore_audio_clock(uint32_t expected_core_clock, uint32_t ram1_wait,
                                uint32_t ram2_wait, uint32_t saved_flash_latency)
{
    /* Preserve board_hal's actual fractional CPU/audio PLL and Flash wait
     * states, including the qualified lower CPU clock. No HAL timeout while
     * SysTick is suspended; audio IRQs remain masked until restoration. */
    stop_stage=10u;
    LL_RCC_HSI_Enable(); LL_RCC_HSE_Enable();
    if (!wait_bit(&RCC->CR,RCC_CR_HSIRDY|RCC_CR_HSERDY,RCC_CR_HSIRDY|RCC_CR_HSERDY)) return false;
    LL_RCC_HSE_DisablePrescaler();
    stop_stage=11u;
    LL_PWR_SetRegulVoltageScaling(LL_PWR_REGU_VOLTAGE_SCALE1);
    if (!wait_bit(&PWR->VOSR,PWR_VOSR_VOSRDY,PWR_VOSR_VOSRDY)) return false;
    stop_stage=12u;
    __HAL_FLASH_SET_LATENCY(FLASH_LATENCY_3);
    if (!wait_bit(&FLASH->ACR,FLASH_ACR_LATENCY,FLASH_LATENCY_3)) return false;
    MODIFY_REG(RAMCFG_SRAM1->CR,RAMCFG_CR_WSC,ram1_wait);
    MODIFY_REG(RAMCFG_SRAM2->CR,RAMCFG_CR_WSC,ram2_wait);
    stop_stage=13u;
    if (!wait_bit(&RAMCFG_SRAM1->CR,RAMCFG_CR_WSC,ram1_wait)) return false;
    stop_stage=14u;
    if (!wait_bit(&RAMCFG_SRAM2->CR,RAMCFG_CR_WSC,ram2_wait)) return false;
    stop_stage=15u;
    LL_RCC_PLL1_EnableDomain_PLL1P(); LL_RCC_PLL1_EnableDomain_PLL1R();
    LL_RCC_PLL1_Enable();
    if (!wait_bit(&RCC->CR,RCC_CR_PLL1RDY,RCC_CR_PLL1RDY)) return false;
    stop_stage=16u;
    LL_RCC_SetSysClkSource(LL_RCC_SYS_CLKSOURCE_PLL1R);
    if (!wait_bit(&RCC->CFGR1,RCC_CFGR1_SWS,LL_RCC_SYS_CLKSOURCE_STATUS_PLL1R)) return false;
    stop_stage=17u;
    SystemCoreClockUpdate();
    if (SystemCoreClock!=expected_core_clock) return false;
    /* Three wait states are a safe transition value, not the final clock
     * policy. Restore the exact pre-entry value only after the expected PLL
     * clock is confirmed; otherwise every low-clock wake regresses latency. */
    stop_stage=18u;
    __HAL_FLASH_SET_LATENCY(saved_flash_latency);
    if (!wait_bit(&FLASH->ACR,FLASH_ACR_LATENCY,saved_flash_latency)) return false;
    /* Board's AHB5 divider and SAI source registers are retained by Stop1. */
    __HAL_RCC_SAI1_CONFIG(RCC_SAI1CLKSOURCE_PLL1P);
    /* Stop1 retains the disabled SysTick registers. The exact pre-entry
     * core clock was checked above, so LOAD and the unfinished VAL period
     * remain valid. Clearing VAL here would discard awake time at every
     * wake; writing a saved value to VAL would also clear it (PM0264 4.4.3).
     * Leave a late pending SysTick exception for normal IRQ dispatch. */
    return true;
}
void LPM_IdleMode(uint32_t option) { (void)option; }
void LPM_SleepMode(uint32_t option)
{
    (void)option;
    LINKLAYER_PLAT_NotifyWFIEnter(); LL_LPM_EnableSleep(); __DSB();
    comp_v11_cpu_wait_enter(); __WFI(); comp_v11_cpu_wait_exit();
    LINKLAYER_PLAT_NotifyWFIExit();
}
void LPM_Stop1Mode(uint32_t option)
{
    (void)option;
    /* No caller, including SDK initialization/profiling, owns this driver
     * unless the product transaction passed the IRQ-masked final recheck. */
    if (!entry_owned || !(COMPANION_WBA_AUTOMATIC_STOP1 || trial_armed) || __get_PRIMASK()!=1u || !eligible(product)) return;
    /* A pending/partial UART command aborts entry without discarding it. */
    if (!comp_v11_hal_debug_stop_arm()) return;
    stop_stage=1u;
    LL_PWR_ClearFlag_STOP();
    /* These values belong to this single retained-stack transaction, rather
     * than consuming static RAM for every recording/OTA/idle state. */
    const uint32_t expected_core_clock=SystemCoreClock;
    const uint32_t saved_flash_latency=__HAL_FLASH_GET_LATENCY();
    const bool saved_icache_enabled=LL_ICACHE_IsEnabled()!=0u;
    LINKLAYER_PLAT_NotifyWFIEnter();
    stop_stage=2u;
    LL_ICACHE_Disable();
    if (!wait_bit(&ICACHE->SR,ICACHE_SR_BUSYF,0u)) { comp_v11_hal_debug_stop_disarm(); clock_restored=false; return; }
    __HAL_FLASH_SET_LATENCY(FLASH_LATENCY_3);
    /* Cube's MX_RAMCFG_Init -> HAL_RAMCFG_MspInit enables this register
     * clock. Our custom board startup does not call that initialization.
     * Lease it before even reading CR: a gated read/write is not a valid
     * saved latency or successful wait-state update. Keep any prior owner. */
    const bool ramcfg_clock_was_enabled=__HAL_RCC_RAMCFG_IS_CLK_ENABLED();
    __HAL_RCC_RAMCFG_CLK_ENABLE();
    const uint32_t ram1_wait=RAMCFG_SRAM1->CR&RAMCFG_CR_WSC;
    const uint32_t ram2_wait=RAMCFG_SRAM2->CR&RAMCFG_CR_WSC;
    /* Modify latency only; do not clear SRAM parity/ECC protection bits. */
    MODIFY_REG(RAMCFG_SRAM1->CR,RAMCFG_CR_WSC,RAMCFG_CR_WSC_0);
    MODIFY_REG(RAMCFG_SRAM2->CR,RAMCFG_CR_WSC,RAMCFG_CR_WSC_0);
    stop_stage=3u;
    if (!wait_bit(&RAMCFG_SRAM1->CR,RAMCFG_CR_WSC,RAMCFG_CR_WSC_0)) {
        if (!ramcfg_clock_was_enabled) __HAL_RCC_RAMCFG_CLK_DISABLE();
        comp_v11_hal_debug_stop_disarm(); clock_restored=false; return;
    }
    stop_stage=4u;
    if (!wait_bit(&RAMCFG_SRAM2->CR,RAMCFG_CR_WSC,RAMCFG_CR_WSC_0)) {
        if (!ramcfg_clock_was_enabled) __HAL_RCC_RAMCFG_CLK_DISABLE();
        comp_v11_hal_debug_stop_disarm(); clock_restored=false; return;
    }
    stop_stage=5u;
    if (!wait_bit(&PWR->SVMSR,PWR_SVMSR_ACTVOSRDY,PWR_SVMSR_ACTVOSRDY)) {
        if (!ramcfg_clock_was_enabled) __HAL_RCC_RAMCFG_CLK_DISABLE();
        comp_v11_hal_debug_stop_disarm(); clock_restored=false; return;
    }
    stop_stage=6u;
    LL_PWR_SetPowerMode(LL_PWR_MODE_STOP1); LL_LPM_EnableDeepSleep();
    __DSB(); capture_pending_irqs(&last_wake.before);
    __WFI(); __ISB();
    /* Capture before restoring clocks or dispatching any normal interrupt.
     * A pending IRQ in 'before' identifies the late-entry race; multiple
     * 'after' bits may coexist. A debugger wake can still leave all zero. */
    capture_pending_irqs(&last_wake.after);
    last_wake.entered_stop=LL_PWR_IsActiveFlag_STOP()!=0u;
    last_wake.captured=true;
    stop_stage=7u;
    LL_LPM_EnableSleep();
    /* Record before IRQ dispatch/RTC callback clears the flags. These may
     * coexist; do not infer a unique wake cause from a later UART reply. */
    last_wake_flags=(comp_v11_hal_debug_stop_rx_pending()?1u:0u)|
        ((RTC->SR&RTC_SR_ALRAF)?2u:0u);
    if (last_wake.entered_stop) trial_entered();
    clock_restored=restore_audio_clock(expected_core_clock,ram1_wait,ram2_wait,saved_flash_latency);
    /* Preserve the failing restore stage when enter() subsequently stops. */
    if (clock_restored) stop_stage=19u;
    __HAL_RCC_RADIO_CLK_ENABLE();
    LINKLAYER_PLAT_NotifyWFIExit();
    if (saved_icache_enabled) LL_ICACHE_Enable();
    comp_v11_hal_debug_stop_disarm();
    /* SRAM wait states have been restored (or the transaction is fatal).
     * Restore only the register-clock lease; never disable another owner. */
    if (!ramcfg_clock_was_enabled) __HAL_RCC_RAMCFG_CLK_DISABLE();
    if (clock_restored) stop_stage=20u;
}
const UTIL_LPM_Driver_fp UTIL_LPM_Driver[]={LPM_IdleMode,LPM_SleepMode,LPM_Stop1Mode};
const uint32_t UTIL_LPM_Driver_num=sizeof(UTIL_LPM_Driver)/sizeof(UTIL_LPM_Driver[0]);
_Static_assert(UTIL_LPM_NUM_MODES==3,"Companion supports only Idle/Sleep/Stop1");

static void wake(void *context) { (void)context; timer_elapsed=true; }
static bool arm(void *context, uint32_t period)
{
    (void)context; timer_elapsed=false;
    return UTIL_TIMER_StartWithPeriod(&wake_timer,period)==UTIL_TIMER_OK &&
        UTIL_TIMER_IsRunning(&wake_timer) &&
        (RTC->CR&(RTC_CR_ALRAE|RTC_CR_ALRAIE))==(RTC_CR_ALRAE|RTC_CR_ALRAIE);
}
static bool disarm(void *context)
{ (void)context; return UTIL_TIMER_Stop(&wake_timer)==UTIL_TIMER_OK; }
static bool eligible(comp_v11_product_app_t *app)
{
    return app && app==product && app->board && app->board->idle_peripherals &&
        !app->runtime.prepare_pending && !app->runtime.start_pending &&
        !app->runtime.command_pending && !app->runtime.capture_active && !app->runtime.stop_pending &&
        comp_v11_hal_debug_stop_available() &&
        !comp_v11_cpu_counter_owned() &&
        comp_power_policy_stop_allowed(&app->board->power) && app->board->audio_clock_ready &&
        app->board->lse_ready && comp_v11_ble_host_ready() &&
        !app->board->microphone.running && !app->board->playback_active;
}
static bool lock_recheck(void *context)
{
    comp_v11_product_app_t *app=context;
    saved_primask=__get_PRIMASK(); __disable_irq();
    if (saved_primask || timer_elapsed || !eligible(app) ||
        app->board->wake_events.pending || comp_v11_hal_key_pressed() ||
        HAL_GPIO_ReadPin(GPIOC,GPIO_PIN_13)==GPIO_PIN_RESET ||
        UTIL_LPM_GetMaxMode()!=UTIL_LPM_STOP1_MODE ||
        LL_PWR_GetRadioMode()==LL_PWR_RADIO_ACTIVE_MODE ||
        (SCB->ICSR&(SCB_ICSR_PENDSTSET_Msk|SCB_ICSR_PENDSVSET_Msk))) return false;
    for (unsigned i=0;i<sizeof(NVIC->ISPR)/sizeof(NVIC->ISPR[0]);++i)
        if (NVIC->ISPR[i]&NVIC->ISER[i]) return false;
    /* This SDK's API tests that ALL bits in its argument are pending. Query
     * one task at a time; passing UTIL_SEQ_DEFAULT would miss a single task. */
    for (unsigned i=0;i<32u;++i)
        if (UTIL_SEQ_IsSchedulableTask(1u<<i)) return false;
    return true;
}
static void unlock(void *context) { (void)context; __set_PRIMASK(saved_primask); }
static void suspend(void *context)
{
    (void)context; saved_systick=SysTick->CTRL;
    /* Stop the whole counter, not just TICKINT; avoid a pending tick during
     * clock restore being counted in addition to the RTC compensation. */
    SysTick->CTRL=0u;
}
static void resume(void *context, uint32_t ms)
{
    (void)context;
    /* Adding separately rounded stopped intervals loses the relation between
     * RTC's1024Hz grid and the retained awake SysTick phase. Keep one RTC
     * timeline over consecutive sleeps, while retaining SysTick foreground
     * timing. Long awake gaps fall back once and reanchor at this wake. */
    const uint32_t before=uwTick;
    uwTick=comp_wba_rtc_clock_compensate(&stop_timeline,rtc(NULL),before,ms);
    /* The coordinator already counted ms. Report what was actually applied,
     * including phase reconciliation, without a second diagnostic counter. */
    stop.compensated_ms+=(uwTick-before)-ms;
    /* Re-enable from the retained count, including a zero awaiting reload.
     * Do not reset VAL or clear a pending tick from the final entry race. */
    SysTick->CTRL=saved_systick;
}
static void watchdog(void *context) { (void)context; LL_IWDG_ReloadCounter(IWDG); }
static bool enter(void *context)
{
    (void)context; clock_restored=true; entry_owned=true;
    UTIL_LPM_Enter(0u); entry_owned=false;
    if (!clock_restored) {
        product->board->audio_clock_ready=false; product->board->faults|=COMP_V11_FAULT_CLOCK;
        /* Never run UART/I2C/SAI or service a radio IRQ with unknown clocks.
         * Resident boot watchdog supplies recovery; do not feed it here. */
        Error_Handler();
    }
    return clock_restored;
}
void comp_v11_low_power_init(comp_v11_product_app_t *app, bool ble_initialized)
{
    static const comp_wba_stop_ports_t ports={arm,disarm,lock_recheck,unlock,suspend,resume,rtc,enter,watchdog};
    stop_stage=0u; product=app; trial_armed=false; trial_window=false;
    trial_entries_left=0u; app_stop_permission=false; entry_owned=false;
    last_wake=(comp_v11_stop_wake_snapshot_t){0};
    bool ready=ble_initialized && app && comp_v11_hal_debug_stop_available() && app->board->lse_ready && app->board->audio_clock_ready &&
        UTIL_TIMER_Create(&wake_timer,COMP_WBA_STOP_WAKE_MS,UTIL_TIMER_ONESHOT,wake,NULL)==UTIL_TIMER_OK;
    comp_wba_stop_init(&stop,&ports,app,ready);
    comp_wba_rtc_clock_init(&stop_timeline,rtc(NULL),HAL_GetTick());
    if (ble_initialized) UTIL_LPM_SetMaxMode(1u<<CFG_LPM_APP,UTIL_LPM_SLEEP_MODE);
}
void comp_v11_low_power_idle(comp_v11_product_app_t *app)
{
    if (__get_IPSR() || __get_PRIMASK()) return;
    trial_expire(HAL_GetTick());
    bool pending=foreground_pending(app);
    bool allowed=stop.enabled && (COMPANION_WBA_AUTOMATIC_STOP1 || trial_armed) && !pending && eligible(app);
    /* This APP vote is owned by this target in experimental builds. Change
     * it on transitions, not on every hot BLE/recording foreground turn. */
    if (product && comp_v11_ble_host_ready() && app_stop_permission!=allowed) {
        UTIL_LPM_SetMaxMode(1u<<CFG_LPM_APP,allowed ? UTIL_LPM_STOP1_MODE : UTIL_LPM_SLEEP_MODE);
        app_stop_permission=allowed;
    }
    if (pending) return;
    comp_wba_stop_result_t result=comp_wba_stop_run(&stop,allowed);
    if (((!COMPANION_WBA_AUTOMATIC_STOP1 && !trial_armed) || !stop.enabled) && app_stop_permission) {
        UTIL_LPM_SetMaxMode(1u<<CFG_LPM_APP,UTIL_LPM_SLEEP_MODE);
        app_stop_permission=false;
    }
    if (result==COMP_WBA_STOP_SKIPPED) {
        comp_v11_cpu_wait_enter(); __WFI(); comp_v11_cpu_wait_exit();
    }
    /* An aborted atomic recheck means foreground work/IRQ is pending: return
     * to poll immediately, rather than sleeping with a consumed edge. */
}
const char *comp_v11_low_power_identity(void)
{
    if(stop.enabled && COMPANION_WBA_AUTOMATIC_STOP1)return "STOP1_AUTOMATIC";
    return !stop.enabled ? "STOP1_UNAVAILABLE" : trial_window ?
        (trial_armed ? "STOP1_WINDOW_ARMED" : "STOP1_WINDOW_UNARMED") :
        (trial_armed ? "STOP1_ONCE_ARMED" : "STOP1_ONCE_UNARMED");
}
static bool arm_trial(comp_v11_product_app_t *app, bool window)
{
    if (__get_IPSR() || __get_PRIMASK() || !stop.enabled || trial_armed ||
        !eligible(app) || foreground_pending(app)) return false;
    stop_stage=0u; last_wake_flags=0u; last_wake=(comp_v11_stop_wake_snapshot_t){0};
    /* Explicit bounded trial only. Every subsequent foreground turn still
     * rechecks all product/IRQ/timer/radio admission. Never loop here or
     * suppress an input to fill the budget. Automatic mode is build-selected. */
    trial_window=window; trial_entries_left=window ? 256u : 1u;
    trial_deadline=HAL_GetTick()+(window ? 5000u : 1000u); trial_armed=true;
    return true;
}
bool comp_v11_low_power_arm_once(comp_v11_product_app_t *app)
{ return arm_trial(app,false); }
bool comp_v11_low_power_arm_window(comp_v11_product_app_t *app)
{ return arm_trial(app,true); }
uint32_t comp_v11_low_power_stage(void) { return stop_stage; }
uint32_t comp_v11_low_power_wake_flags(void) { return last_wake_flags; }
const comp_v11_stop_wake_snapshot_t *comp_v11_low_power_wake_snapshot(void) { return &last_wake; }
void comp_v11_low_power_stats(uint32_t *entries,uint32_t *ms,uint32_t *failures)
{ *entries=companion_stop1_entries; *ms=stop.compensated_ms; *failures=stop.failures; }
#else
void comp_v11_low_power_init(comp_v11_product_app_t *app, bool ready) { (void)app; (void)ready; }
void comp_v11_low_power_idle(comp_v11_product_app_t *app)
{
    if (__get_IPSR() || __get_PRIMASK() || foreground_pending(app)) return;
    comp_v11_cpu_wait_enter(); __WFI(); comp_v11_cpu_wait_exit();
}
const char *comp_v11_low_power_identity(void) { return "WFI_STOP1_DISABLED"; }
void comp_v11_low_power_stats(uint32_t *entries,uint32_t *ms,uint32_t *failures)
{ *entries=0u; *ms=0u; *failures=0u; }
#endif
