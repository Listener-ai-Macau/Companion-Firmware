#include "reset_witness.h"
#include "cpu_profile_target.h"
#if COMPANION_WBA_CPU_RESIDENCE_PROFILE
#include "board_hal.h"
#include "clock_target.h"
#include "cpu_residence.h"
#include "cpu_counter_clock.h"
#include "companion_cpu_stage.h"
#include "cpu_self_ledger.h"
#include "cpu_codec_irq.h"
#include "ble/ble_micro_observation.h"
#include <stdio.h>
static comp_cpu_residence_t residence;
/* Same bounded ledger/clock, mutually exclusive purpose. No second timer or
 * per-packet buffer. Separate output prevents treating upload as audio CPU. */
static bool transport_capture;
/* Shared accounting RAM must retain the closed recording ledger until its
 * safe UART report, even when the final sealed segment is received first. */
static bool recording_report_pending;

typedef struct {uint64_t all_bytes,wall,irq;uint32_t calls,min,max;uint16_t bytes;} panel_byte_stats_t;
static panel_byte_stats_t panel_bytes;
_Static_assert(sizeof(panel_byte_stats_t)<=48u,"bounded actual SPI byte accounting");
/* The outer IRQ envelope includes any nested IRQs; never present it as the
 * exclusive cost of that one exception. All uses share the existing stamp. */
static struct {uint32_t entered,max_us,max_at;uint16_t kind,max_kind;} outer_irq;
_Static_assert(sizeof(outer_irq)==16u,"bounded outer IRQ envelope");
/* Wall is exactly thread+IRQ for these valid spans; its redundant storage
 * now holds exclusive foreground time without enlarging the per-stage array. */
typedef struct {uint64_t self_thread_us,thread_us,irq_us;uint32_t calls,max_wall_us,invalid;} stage_stats_t;
typedef struct {
    uint32_t self_us[COMP_BULK_CPU_STAGES];
    uint16_t calls[COMP_BULK_CPU_STAGES],flags,cropped;
} bulk_phase_stats_t;
_Static_assert(sizeof(bulk_phase_stats_t)<=3u*sizeof(stage_stats_t),"upload phases reuse normal audio stage storage");
static union {
    stage_stats_t capture[COMP_CPU_STAGE_STORAGE_COUNT];
    bulk_phase_stats_t transfer;
} observation_stages;
#define stage_stats observation_stages.capture
#define bulk_phase observation_stages.transfer
static comp_cpu_self_ledger_t stage_self;
/* Three exact exceedance counts prove the frozen percentile bounds without
 * per-frame traces or a large histogram. Only completed, valid Opus spans. */
static uint32_t opus_over_budget[3];
_Static_assert(COMP_CPU_STAGE_COUNT==17u && sizeof(stage_stats)==40u*COMP_CPU_STAGE_STORAGE_COUNT,"bounded selected-stage observation");
/* CPU_CACHE_TRIAL_MODEL_BEGIN */
/* Wired, explicit, one-capture engineering trial. Normal captures leave the
 * original ICACHE alone. This is a zero-cache stress, never a 4KB emulation. */
static struct {uint32_t token,armed_until_ms;bool armed,used,owned_off,restored,error;} cache_trial;
static void cache_trial_restore(void)
{
    if(!cache_trial.owned_off)return;
    if(HAL_ICACHE_Enable()==HAL_OK && HAL_ICACHE_IsEnabled()) {
        cache_trial.owned_off=false;cache_trial.restored=true;
    } else cache_trial.error=true;
}
bool comp_v11_cpu_arm_cache_off_trial(void)
{
    if(residence.active || __get_IPSR() || cache_trial.armed || cache_trial.owned_off ||
       !HAL_ICACHE_IsEnabled() || (ICACHE->CR&ICACHE_MONITOR_HIT_MISS))return false;
    memset(&cache_trial,0,sizeof(cache_trial));cache_trial.armed=true;
    cache_trial.armed_until_ms=HAL_GetTick()+30000u;return true;
}
static void cache_trial_begin(uint32_t token)
{
    /* A failed host connection must not leave a surprise for a later user. */
    const bool armed=cache_trial.armed && (int32_t)(HAL_GetTick()-cache_trial.armed_until_ms)<0;
    cache_trial_restore();if(cache_trial.owned_off)return;
    memset(&cache_trial,0,sizeof(cache_trial));cache_trial.token=token;
    if(!armed)return;
    cache_trial.used=true;
    HAL_StatusTypeDef status=HAL_ICACHE_Disable();
    cache_trial.owned_off=!HAL_ICACHE_IsEnabled();
    if(status!=HAL_OK || !cache_trial.owned_off)cache_trial.error=true;
}
/* CPU_CACHE_TRIAL_MODEL_END */
/* CODEC_CACHE_MODEL_BEGIN */
static comp_cpu_codec_irq_t codec_irq;
_Static_assert(sizeof(outer_irq)+sizeof(codec_irq)==36u,"reuse original IRQ observation storage");
typedef struct {
    uint64_t hits,misses;
    uint32_t begins,calls,saturations,foreign,peak_us,peak_hits,peak_misses,peak_irq_us;
    uint32_t peak_admission_flags,peak_admission_next_us;
    bool owned;
} codec_cache_stats_t;
static codec_cache_stats_t codec_cache;
static uint32_t codec_admission_flags,codec_admission_next_us;
static bool codec_admission_pending;
void comp_cpu_codec_admission(uint32_t flags,uint32_t next_radio_us)
{codec_admission_flags=flags;codec_admission_next_us=next_radio_us;codec_admission_pending=true;}
void comp_cpu_codec_admission_end(void){codec_admission_pending=false;}
void comp_cpu_codec_source(uint32_t recording_state,uint32_t queued_pcm)
{
    /* Unported callers can encode without a platform admission ticket. Never
     * attach a previous frame's quiet-gap ticket to that later work. */
    if(!codec_admission_pending){codec_admission_flags=5u<<8u;codec_admission_next_us=0u;}
    codec_admission_flags=(codec_admission_flags&65535u)|((queued_pcm&255u)<<16u)|((recording_state&255u)<<24u);
    codec_admission_pending=false;
}
_Static_assert(sizeof(codec_cache_stats_t)<=64u,"bounded optional codec cache observation");
static void codec_cache_stop_owned(void)
{
    if(codec_cache.owned){(void)HAL_ICACHE_Monitor_Stop(ICACHE_MONITOR_HIT_MISS);codec_cache.owned=false;}
}
void comp_cpu_codec_cache_begin(void)
{
    if(!residence.active || transport_capture || !HAL_ICACHE_IsEnabled())return;
    if(codec_cache.owned)codec_cache_stop_owned();
    /* Do not reset another owner's monitor or alter cache enable/ways/data. */
    if(ICACHE->CR&ICACHE_MONITOR_HIT_MISS){++codec_cache.foreign;return;}
    (void)HAL_ICACHE_Monitor_Reset(ICACHE_MONITOR_HIT_MISS);
    (void)HAL_ICACHE_Monitor_Start(ICACHE_MONITOR_HIT_MISS);
    codec_cache.owned=true;++codec_cache.begins;
    comp_cpu_codec_irq_frame_begin(&codec_irq);
}
static void codec_cache_end(uint32_t wall,uint32_t irq,bool completed)
{
    if(!codec_cache.owned)return;
    codec_cache_stop_owned();
    if(!completed)return;
    uint32_t hits=HAL_ICACHE_Monitor_GetHitValue(),misses=HAL_ICACHE_Monitor_GetMissValue();
    ++codec_cache.calls;codec_cache.hits+=hits;codec_cache.misses+=misses;
    /* WBA55 CMSIS defines a 32-bit HIT and 16-bit MISS saturating counter. */
    if(hits==UINT32_MAX || misses>=UINT16_MAX)++codec_cache.saturations;
    if(wall>=codec_cache.peak_us){codec_cache.peak_us=wall;codec_cache.peak_irq_us=irq;codec_cache.peak_hits=hits;codec_cache.peak_misses=misses;codec_cache.peak_admission_flags=codec_admission_flags;codec_cache.peak_admission_next_us=codec_admission_next_us;comp_cpu_codec_irq_peak(&codec_irq);}
}
/* CODEC_CACHE_MODEL_END */
/* Keep explicit IRQ call sites inspectable. The opt-in CPU observer owns
 * TIM2 only during capture, including WFI; no DWT/NVIC/IRQ-context output. */
#if defined(__GNUC__)
#define CPU_HOOK __attribute__((noinline))
#else
#define CPU_HOOK
#endif
/* CPU_TIMER_MODEL_BEGIN */
static struct {
    comp_cpu_counter_clock_t clock;
    uint32_t core_hz,bus_config,rejected;
    bool owned,sleep_was_on,release_refused;
} cpu_timer;
_Static_assert(sizeof(cpu_timer)<=44u,"bounded capture-only independent clock");
static bool timer_config_owned(void)
{
    return cpu_timer.owned && __HAL_RCC_TIM2_IS_CLK_ENABLED() &&
        TIM2->CR1==TIM_CR1_CEN && TIM2->DIER==0u && TIM2->SMCR==0u &&
        TIM2->PSC==cpu_timer.clock.divider-1u && TIM2->ARR==UINT32_MAX;
}
static void timer_stop(void)
{
    if(!cpu_timer.owned)return;
    if(!timer_config_owned()) {cpu_timer.release_refused=true;cpu_timer.owned=false;return;}
    TIM2->CR1=0u;
    if(!cpu_timer.sleep_was_on)__HAL_RCC_TIM2_CLK_SLEEP_DISABLE();
    __HAL_RCC_TIM2_CLK_DISABLE();cpu_timer.owned=false;
}
static bool timer_start(void)
{
    /* Clock-off and IRQ-off are the admission condition. Never reconfigure
     * an existing user's timer. No TIM2 IRQ, DMA, GPIO or debug setting. */
    timer_stop();memset(&cpu_timer,0,sizeof(cpu_timer));
    if(__HAL_RCC_TIM2_IS_CLK_ENABLED() || NVIC_GetEnableIRQ(TIM2_IRQn)) {cpu_timer.rejected=1u;return false;}
    uint32_t hz=HAL_RCC_GetPCLK1Freq();
    if((RCC->CFGR2&RCC_CFGR2_PPRE1)!=RCC_HCLK_DIV1) {
        if(hz>UINT32_MAX/2u){cpu_timer.rejected=1u;return false;}
        hz*=2u;
    }
    if(!comp_cpu_counter_clock_init(&cpu_timer.clock,hz,0u)) {cpu_timer.rejected=1u;return false;}
    cpu_timer.core_hz=SystemCoreClock;
    cpu_timer.bus_config=RCC->CFGR2&(RCC_CFGR2_HPRE|RCC_CFGR2_PPRE1);
    cpu_timer.sleep_was_on=__HAL_RCC_TIM2_IS_CLK_SLEEP_ENABLED();
    __HAL_RCC_TIM2_CLK_ENABLE();__HAL_RCC_TIM2_FORCE_RESET();__HAL_RCC_TIM2_RELEASE_RESET();
    TIM2->CR1=0u;TIM2->DIER=0u;TIM2->SMCR=0u;TIM2->CCER=0u;
    TIM2->PSC=cpu_timer.clock.divider-1u;TIM2->ARR=UINT32_MAX;
    TIM2->EGR=TIM_EGR_UG;TIM2->SR=0u;TIM2->CNT=0u;
    __HAL_RCC_TIM2_CLK_SLEEP_ENABLE();TIM2->CR1=TIM_CR1_CEN;cpu_timer.owned=true;
    return true;
}
static bool stamp(bool systick_entry,uint32_t *out)
{
    (void)systick_entry;
    if(!timer_config_owned() || SystemCoreClock!=cpu_timer.core_hz ||
       (RCC->CFGR2&(RCC_CFGR2_HPRE|RCC_CFGR2_PPRE1))!=cpu_timer.bus_config ||
       !comp_cpu_counter_clock_read(&cpu_timer.clock,TIM2->CNT,out)) {
        if(cpu_timer.rejected!=UINT32_MAX)++cpu_timer.rejected;
        return false;
    }
    return true;
}
/* CPU_TIMER_MODEL_END */
#if defined(COMPANION_WBA_EXPERIMENTAL_STOP1) && COMPANION_WBA_EXPERIMENTAL_STOP1
bool comp_v11_cpu_counter_owned(void) { return cpu_timer.owned; }
#endif
static void reference(uint32_t now)
{
    uint32_t ticks=0u;bool valid=comp_v11_clock_domain_continuous();
    if(valid)ticks=UINT32_MAX-RTC->SSR;
    comp_cpu_residence_reference(&residence,now,ticks,valid);
}
/* CPU_TRANSFER_MODEL_BEGIN */
void comp_v11_cpu_transfer_begin(uint32_t generation)
{
    /* Recording always owns its active ledger. An armed recording-only cache
     * trial remains armed and is never consumed by a bulk observation. */
    if(!generation || __get_IPSR() || residence.active || cache_trial.owned_off || recording_report_pending)return;
    uint32_t mask=__get_PRIMASK();__disable_irq();
    uint32_t now=0u;bool valid=false;
    /* The same owned timer also protects a sealed upload from Stop1. Keep
     * bulk observation valid in the unarmed engineering image. */
    if(timer_start())valid=stamp(false,&now);
    transport_capture=true;
    memset(&bulk_phase,0,sizeof(bulk_phase));comp_cpu_self_reset(&stage_self);
    memset(&outer_irq,0,sizeof(outer_irq));
    comp_cpu_residence_begin(&residence,generation,SystemCoreClock,now,valid);
    reference(now);__set_PRIMASK(mask);
}
void comp_v11_cpu_transfer_end(void)
{
    if(!transport_capture || !residence.active || __get_IPSR())return;
    uint32_t mask=__get_PRIMASK();__disable_irq();uint32_t now=0u;bool valid=stamp(false,&now);
    if(valid)reference(now);
    comp_cpu_residence_end(&residence,now,valid);timer_stop();__set_PRIMASK(mask);
    /* Retain the purpose with the closed ledger for a later safe UART dump.
     * No cache restore/reset and no recording-stage/self-ledger mutation. */
}
/* CPU_TRANSFER_MODEL_END */
void comp_v11_cpu_capture_begin(uint32_t token)
{
    if(!token || (residence.active&&!transport_capture&&residence.stats.token==token))return;
    if(transport_capture)comp_v11_cpu_transfer_end();
    transport_capture=false;recording_report_pending=false;
    /* HAL disable may wait; run before the accounting critical section. */
    cache_trial_begin(token);
    uint32_t mask=__get_PRIMASK();__disable_irq();
    memset(&panel_bytes,0,sizeof(panel_bytes));
    memset(&outer_irq,0,sizeof(outer_irq));memset(&codec_irq,0,sizeof(codec_irq));
    uint32_t now=0u;bool valid=false;
    /* The low-power entry now excludes an owned TIM2. Keep actual CPU
     * accounting in recording builds with optional idle Stop1 enabled. */
    if(timer_start())valid=stamp(false,&now);
    codec_cache_stop_owned();memset(&codec_cache,0,sizeof(codec_cache));
    codec_admission_flags=0u;codec_admission_next_us=0u;codec_admission_pending=false;
    memset(stage_stats,0,sizeof(stage_stats));memset(opus_over_budget,0,sizeof(opus_over_budget));
    comp_cpu_self_reset(&stage_self);
    comp_cpu_residence_begin(&residence,token,SystemCoreClock,now,valid);reference(now);__set_PRIMASK(mask);
}
void comp_v11_cpu_capture_end(uint32_t token)
{
    if(transport_capture||!residence.active||token!=residence.stats.token)return;
    uint32_t mask=__get_PRIMASK();__disable_irq();uint32_t now=0u;bool valid=stamp(false,&now);
    codec_cache_stop_owned();
    if(valid)reference(now);
    comp_cpu_residence_end(&residence,now,valid);comp_cpu_self_finish(&stage_self);timer_stop();__set_PRIMASK(mask);
    cache_trial_restore();recording_report_pending=true;
}
CPU_HOOK void comp_v11_cpu_irq_enter(bool systick_entry)
{
    comp_v11_reset_witness_irq_enter();
    if(!residence.active)return;
    uint32_t mask=__get_PRIMASK();__disable_irq();uint32_t now=0u;bool valid=stamp(systick_entry,&now);
    if(!residence.irq_depth){outer_irq.entered=now;outer_irq.kind=(uint16_t)__get_IPSR();}
    comp_cpu_residence_irq_enter(&residence,now,valid);__set_PRIMASK(mask);
}
CPU_HOOK void comp_v11_cpu_irq_exit(void)
{
    comp_v11_reset_witness_irq_exit();
    if(!residence.active)return;
    uint32_t mask=__get_PRIMASK();__disable_irq();uint32_t now=0u;bool valid=stamp(false,&now);
    if(residence.irq_depth==1u && valid) {
        uint32_t elapsed=now-outer_irq.entered;
        if(elapsed<=2000000u) {
            if(elapsed>outer_irq.max_us){outer_irq.max_us=elapsed;outer_irq.max_kind=outer_irq.kind;outer_irq.max_at=now;}
            if(codec_cache.owned)comp_cpu_codec_irq_note_outer(&codec_irq,elapsed,outer_irq.kind,
                outer_irq.kind==(uint16_t)(RADIO_IRQn+16u) ||
                outer_irq.kind==(uint16_t)(HASH_IRQn+16u));
        }
    }
    comp_cpu_residence_irq_exit(&residence,now,valid);__set_PRIMASK(mask);
}
CPU_HOOK void comp_v11_cpu_wait_enter(void)
{
    if(!residence.active)return;
    uint32_t mask=__get_PRIMASK();__disable_irq();uint32_t now=0u;bool valid=stamp(false,&now);
    comp_cpu_residence_wait(&residence,now,valid,true);__set_PRIMASK(mask);
}
CPU_HOOK void comp_v11_cpu_wait_exit(void)
{
    if(!residence.active)return;
    uint32_t mask=__get_PRIMASK();__disable_irq();uint32_t now=0u;bool valid=stamp(false,&now);
    comp_cpu_residence_wait(&residence,now,valid,false);__set_PRIMASK(mask);
}
void comp_v11_cpu_poll(void)
{
    if(!residence.active)return;
    uint32_t mask=__get_PRIMASK();__disable_irq();uint32_t now=0u;bool valid=stamp(false,&now);
    comp_cpu_residence_poll(&residence,now,valid);
    if(valid&&(!residence.reference_valid||now-residence.reference_us>=1000000u))reference(now);
    __set_PRIMASK(mask);
}
/* CPU_TRANSFER_STAGE_MODEL_BEGIN */
bool comp_cpu_bulk_owned(void){return transport_capture;}
comp_cpu_stage_span_t comp_cpu_bulk_stage_begin(void){return comp_v11_cpu_transfer_stage_begin();}
void comp_cpu_bulk_stage_end(unsigned stage,comp_cpu_stage_span_t span){comp_v11_cpu_transfer_stage_end(stage,span);}
static comp_cpu_stage_span_t stage_begin_owned(bool transfer)
{
    comp_cpu_stage_span_t span={0};
    if(!residence.active||transport_capture!=transfer||__get_IPSR())return span;
    uint32_t mask=__get_PRIMASK();__disable_irq();uint32_t now=0u;bool valid=stamp(false,&now);
    if(valid) {
        /* Thread-only boundaries: every completed IRQ already accounts its
         * duration. Avoid advancing the global ledger for nested stage spans. */
        span=(comp_cpu_stage_span_t){.irq_us=residence.stats.total_us[COMP_CPU_IRQ],
            .at_us=now,.token=residence.stats.token,.sequence=comp_cpu_self_begin(&stage_self),.domain=stage_self.domain};
    }
    __set_PRIMASK(mask);return span;
}
comp_cpu_stage_span_t comp_cpu_stage_begin(void){return stage_begin_owned(false);}
comp_cpu_stage_span_t comp_v11_cpu_transfer_stage_begin(void){return stage_begin_owned(true);}
void comp_v11_cpu_transfer_stage_end(unsigned stage,comp_cpu_stage_span_t span)
{
    if(!transport_capture||stage>=COMP_BULK_CPU_STAGES||!span.token||__get_IPSR())return;
    uint32_t mask=__get_PRIMASK();__disable_irq();
    if(residence.stats.token!=span.token||stage_self.domain!=span.domain) {
        __set_PRIMASK(mask);return;
    }
    /* A sealed transfer may end inside an enclosing product-service scope.
     * Its already-owned parent unwinds to the exact closed ledger edge, not
     * to the later return time. Never restart TIM2 after end or crop a newer
     * capture's domain. Failed clocks stay explicitly unqualified. */
    const bool cropped=!residence.active;
    uint32_t now=residence.last_us;
    bool valid=residence.have_stamp&&!residence.stats.clock_errors;
    if(!cropped)valid=stamp(false,&now);
    if(valid) {
        uint32_t wall=now-span.at_us;uint64_t irq=residence.stats.total_us[COMP_CPU_IRQ]-span.irq_us;
        uint32_t own=0u;
        if(wall<=2000000u&&irq<=wall&&
           comp_cpu_self_end(&stage_self,span.sequence,(uint32_t)(wall-irq),&own)) {
            if(own>UINT32_MAX-bulk_phase.self_us[stage]||
               (cropped&&bulk_phase.cropped==UINT16_MAX)) {
                bulk_phase.flags|=2u;comp_cpu_self_invalidate(&stage_self);
            } else {
                /* Call-count metadata can saturate in cheap idle callbacks.
                 * It does not invalidate the already-popped timing frame or
                 * its parent's children. Flag8 means only count lower bound;
                 * true time/sum/clock/order errors retain flags1/2/4. */
                if(bulk_phase.calls[stage]!=UINT16_MAX)++bulk_phase.calls[stage];
                else bulk_phase.flags|=8u;
                bulk_phase.self_us[stage]+=own;
                if(cropped)++bulk_phase.cropped;
            }
        } else {bulk_phase.flags|=1u;comp_cpu_self_invalidate(&stage_self);}
    } else {bulk_phase.flags|=4u;comp_cpu_self_invalidate(&stage_self);}
    __set_PRIMASK(mask);
}
/* CPU_TRANSFER_STAGE_MODEL_END */
static void stage_end_bytes(unsigned stage,comp_cpu_stage_span_t span,bool completed,uint16_t bytes)
{
    if(transport_capture||stage>=COMP_CPU_STAGE_STORAGE_COUNT||!span.token||__get_IPSR())return;
    uint32_t mask=__get_PRIMASK();__disable_irq();
    /* A terminal recording callback may retire this capture while an outer
     * pipeline/progress span is still open. Its timer has already been released:
     * do not turn that normal unwind into a hardware-clock rejection, and never
     * stop or modify the cache monitor/ledger of a newer capture token. Keep an
     * unmeasured terminal span explicit instead of inventing a completion time. */
    if(!residence.active || residence.stats.token!=span.token || stage_self.domain!=span.domain) {
        if(residence.stats.token==span.token && stage_self.domain==span.domain)++stage_stats[stage].invalid;
        __set_PRIMASK(mask);return;
    }
    uint32_t now=0u;bool valid=stamp(false,&now);
    stage_stats_t *s=&stage_stats[stage];
    if(valid) {
        /* Thread-only boundaries: every completed IRQ already accounts its
         * duration. Avoid advancing the global ledger for nested stage spans. */
        uint32_t wall=now-span.at_us;uint64_t irq=residence.stats.total_us[COMP_CPU_IRQ]-span.irq_us;
        uint32_t exclusive=0u;bool own_valid=false;
        if(wall<=2000000u&&irq<=wall)
            own_valid=comp_cpu_self_end(&stage_self,span.sequence,(uint32_t)(wall-irq),&exclusive);
        else comp_cpu_self_invalidate(&stage_self);
        if(stage==COMP_CPU_STAGE_OPUS)codec_cache_end(wall,(uint32_t)irq,completed&&wall<=2000000u&&irq<=wall);
        if(completed&&wall<=2000000u&&irq<=wall&&s->calls!=UINT32_MAX) {
            s->irq_us+=irq;s->thread_us+=wall-irq;++s->calls;
            if(own_valid)s->self_thread_us+=exclusive;
            if(stage==COMP_CPU_STAGE_OPUS) {
                if(wall>5000u)++opus_over_budget[0];
                if(wall>6000u)++opus_over_budget[1];
                if(wall>8000u)++opus_over_budget[2];
            }
            if(wall>s->max_wall_us)s->max_wall_us=wall;
            if(stage==COMP_CPU_STAGE_PANEL_TX && bytes) {
                panel_bytes.all_bytes+=bytes;
                /* Use an actually observed fixed length, not an assumed row
                 * width. Keep only the largest length encountered so memory
                 * is bounded and a never-triggered 25B bucket is impossible. */
                if(bytes>panel_bytes.bytes){panel_bytes.bytes=bytes;panel_bytes.calls=0u;
                    panel_bytes.wall=panel_bytes.irq=0u;panel_bytes.min=panel_bytes.max=0u;}
                if(bytes==panel_bytes.bytes){panel_bytes.wall+=wall;panel_bytes.irq+=irq;
                    if(!panel_bytes.calls || wall<panel_bytes.min)panel_bytes.min=wall;
                    if(wall>panel_bytes.max)panel_bytes.max=wall;
                    ++panel_bytes.calls;}
            }
        } else {++s->invalid;comp_cpu_self_invalidate(&stage_self);}
    } else {++s->invalid;comp_cpu_self_invalidate(&stage_self);if(stage==COMP_CPU_STAGE_OPUS)codec_cache_stop_owned();}
    __set_PRIMASK(mask);
}
void comp_cpu_stage_end(unsigned stage,comp_cpu_stage_span_t span,bool completed)
{stage_end_bytes(stage,span,completed,0u);}
void comp_cpu_panel_stage_end(comp_cpu_stage_span_t span,bool completed,uint16_t bytes)
{stage_end_bytes(COMP_CPU_STAGE_PANEL_TX,span,completed,bytes);}
void comp_v11_cpu_emit(void)
{
    /* Caller uses the existing safe UART gate after capture; never emit in
     * an IRQ or during a live recording, transfer or update. */
    if(residence.active||__get_IPSR()||!residence.stats.token)return;
    uint32_t mask=__get_PRIMASK();__disable_irq();comp_cpu_residence_t s=residence;__set_PRIMASK(mask);
    char line[256];
    if(transport_capture) {
        (void)snprintf(line,sizeof(line),"BULKCPU1 generation=%lu hz=%lu windows=%lu clock_errors=%lu order_errors=%lu reference_errors=%lu qualified=0\r\n",
            (unsigned long)s.stats.token,(unsigned long)s.stats.core_hz,(unsigned long)s.stats.windows,
            (unsigned long)s.stats.clock_errors,(unsigned long)s.stats.order_errors,(unsigned long)s.stats.reference_errors);
        (void)comp_v11_hal_debug_write(line);
        (void)snprintf(line,sizeof(line),"BULKCPU2 thread_hi=%lu thread_lo=%lu irq_hi=%lu irq_lo=%lu wait_hi=%lu wait_lo=%lu\r\n",
            (unsigned long)(s.stats.total_us[0]>>32u),(unsigned long)s.stats.total_us[0],
            (unsigned long)(s.stats.total_us[1]>>32u),(unsigned long)s.stats.total_us[1],
            (unsigned long)(s.stats.total_us[2]>>32u),(unsigned long)s.stats.total_us[2]);
        (void)comp_v11_hal_debug_write(line);
        (void)snprintf(line,sizeof(line),"BULKCPU3 peak_busy_us=%lu peak_irq_us=%lu poll_gap_us=%lu irq_entries=%lu nested=%lu wfi_entries=%lu invalid_windows=%lu\r\n",
            (unsigned long)s.stats.peak_busy_us,(unsigned long)s.stats.peak_irq_us,(unsigned long)s.stats.max_poll_gap_us,
            (unsigned long)s.stats.irq_entries,(unsigned long)s.stats.nested_entries,(unsigned long)s.stats.wfi_entries,(unsigned long)s.stats.invalid_windows);
        (void)comp_v11_hal_debug_write(line);
        (void)snprintf(line,sizeof(line),"BULKCPU4 source=tim2 timer_hz=%lu divider=%lu rejected=%lu released=%u release_refused=%u no_irq=1 no_gpio=1 sleep_clock=1\r\n",
            (unsigned long)cpu_timer.clock.timer_hz,(unsigned long)cpu_timer.clock.divider,(unsigned long)cpu_timer.rejected,
            (unsigned)(!cpu_timer.owned&&!cpu_timer.release_refused),(unsigned)cpu_timer.release_refused);
        (void)comp_v11_hal_debug_write(line);
        (void)snprintf(line,sizeof(line),"BULKPHASE schema=3 slots=19 flags=%u cropped=%u self_invalid=%lu open=%lu\r\n",
            (unsigned)bulk_phase.flags,(unsigned)bulk_phase.cropped,(unsigned long)stage_self.invalid,(unsigned long)stage_self.depth);
        (void)comp_v11_hal_debug_write(line);
        (void)comp_v11_hal_debug_write("BULKMAP1 p0=product p1=hal p2=reserved p3=panel_tx p4=hal_inputs p5=mic_poll p6=validate p7=pipeline p8=capture_progress p9=main_services\r\n");
        (void)comp_v11_hal_debug_write("BULKMAP2 p10=ble_service p11=runtime p12=presenter p13=render p14=sequencer p15=ble_link p16=meeting_aci p17=backend_read p18=publish\r\n");
        for(unsigned i=0u;i<COMP_BULK_CPU_STAGES;++i) {
            (void)snprintf(line,sizeof(line),"BULKPHASE1 phase=%u calls=%u self_us=%lu count_lower_bound=%u\r\n",
                i,(unsigned)bulk_phase.calls[i],(unsigned long)bulk_phase.self_us[i],(unsigned)(bulk_phase.calls[i]==UINT16_MAX));
            (void)comp_v11_hal_debug_write(line);
        }
        /* WFI envelope includes entry/exit overhead. This ledger is the
         * sealed-transfer observer window, not the benchmark denominator,
         * radio airtime, physical current or recording CPU qualification. */
        return;
    }
    recording_report_pending=false;
    (void)snprintf(line,sizeof(line),"CPU1 SCOPE token=%lu hz=%lu source=tim2 mode=thread_irq_wfi_envelope qualified=0 windows=%lu clock_errors=%lu order_errors=%lu reference_errors=%lu\r\n",
        (unsigned long)s.stats.token,(unsigned long)s.stats.core_hz,(unsigned long)s.stats.windows,
        (unsigned long)s.stats.clock_errors,(unsigned long)s.stats.order_errors,(unsigned long)s.stats.reference_errors);
    (void)comp_v11_hal_debug_write(line);
    (void)snprintf(line,sizeof(line),"CPU1 WINDOW token=%lu thread_us=%lu irq_us=%lu wait_us=%lu peak_busy_us=%lu peak_irq_us=%lu poll_gap_us=%lu irq_entries=%lu nested=%lu wfi_entries=%lu\r\n",
        (unsigned long)s.stats.token,(unsigned long)s.stats.last_window[0],(unsigned long)s.stats.last_window[1],
        (unsigned long)s.stats.last_window[2],(unsigned long)s.stats.peak_busy_us,(unsigned long)s.stats.peak_irq_us,
        (unsigned long)s.stats.max_poll_gap_us,(unsigned long)s.stats.irq_entries,(unsigned long)s.stats.nested_entries,(unsigned long)s.stats.wfi_entries);
    (void)comp_v11_hal_debug_write(line);
    /* One retained window, no per-second UART or hot-path stage logging.
     * Starts at actual mic enable; ties retain the first complete window. */
    (void)snprintf(line,sizeof(line),"CPU1 PEAK token=%lu window=%lu busy_us=%lu irq_us=%lu\r\n",
        (unsigned long)s.stats.token,(unsigned long)s.stats.peak_busy_window,
        (unsigned long)s.stats.peak_busy_us,(unsigned long)s.stats.peak_busy_irq_us);
    (void)comp_v11_hal_debug_write(line);
    (void)snprintf(line,sizeof(line),"CPU1 TOTAL token=%lu thread_hi=%lu thread_lo=%lu irq_hi=%lu irq_lo=%lu wait_hi=%lu wait_lo=%lu\r\n",
        (unsigned long)s.stats.token,(unsigned long)(s.stats.total_us[0]>>32u),(unsigned long)s.stats.total_us[0],
        (unsigned long)(s.stats.total_us[1]>>32u),(unsigned long)s.stats.total_us[1],
        (unsigned long)(s.stats.total_us[2]>>32u),(unsigned long)s.stats.total_us[2]);
    (void)comp_v11_hal_debug_write(line);
    (void)snprintf(line,sizeof(line),"CPU1 PARTIAL token=%lu thread_us=%lu irq_us=%lu wait_us=%lu invalid_windows=%lu\r\n",
        (unsigned long)s.stats.token,
        (unsigned long)s.bucket[0],(unsigned long)s.bucket[1],(unsigned long)s.bucket[2],(unsigned long)s.stats.invalid_windows);
    (void)comp_v11_hal_debug_write(line);
    (void)snprintf(line,sizeof(line),"CPU2 token=%lu bad_kind=%lu bad_delta_us=%lu qualified=0\r\n",
        (unsigned long)s.stats.token,(unsigned long)s.stats.last_bad_kind,(unsigned long)s.stats.last_bad_delta_us);
    (void)comp_v11_hal_debug_write(line);
    (void)snprintf(line,sizeof(line),"CACHEMODE1 token=%lu requested_off=%u applied_off=%u restored=%u enabled_now=%u error=%u capacity_emulated=0\r\n",
        (unsigned long)cache_trial.token,(unsigned)cache_trial.used,
        (unsigned)(cache_trial.used&&(cache_trial.owned_off||cache_trial.restored)),
        (unsigned)cache_trial.restored,(unsigned)HAL_ICACHE_IsEnabled(),(unsigned)cache_trial.error);
    (void)comp_v11_hal_debug_write(line);
    (void)snprintf(line,sizeof(line),"CPUTIME1 token=%lu source=tim2 timer_hz=%lu divider=%lu q31=%lu rejected=%lu released=%u release_refused=%u no_irq=1 no_gpio=1 sleep_clock=1\r\n",
        (unsigned long)s.stats.token,(unsigned long)cpu_timer.clock.timer_hz,
        (unsigned long)cpu_timer.clock.divider,(unsigned long)cpu_timer.clock.q31,
        (unsigned long)cpu_timer.rejected,(unsigned)(!cpu_timer.owned&&!cpu_timer.release_refused),(unsigned)cpu_timer.release_refused);
    (void)comp_v11_hal_debug_write(line);
#if COMPANION_WBA_CPU_DETAILED_PROFILE
    (void)snprintf(line,sizeof(line),"SPIPROF1 token=%lu sample_bytes=%u calls=%lu min_us=%lu max_us=%lu selection=largest_seen\r\n",
        (unsigned long)s.stats.token,(unsigned)panel_bytes.bytes,(unsigned long)panel_bytes.calls,(unsigned long)panel_bytes.min,(unsigned long)panel_bytes.max);
    (void)comp_v11_hal_debug_write(line);
    (void)snprintf(line,sizeof(line),"SPIPROF2 all_bytes_hi=%lu all_bytes_lo=%lu sample_wall_hi=%lu sample_wall_lo=%lu sample_irq_hi=%lu sample_irq_lo=%lu\r\n",
        (unsigned long)(panel_bytes.all_bytes>>32u),(unsigned long)panel_bytes.all_bytes,
        (unsigned long)(panel_bytes.wall>>32u),(unsigned long)panel_bytes.wall,
        (unsigned long)(panel_bytes.irq>>32u),(unsigned long)panel_bytes.irq);
    (void)comp_v11_hal_debug_write(line);
#endif
    (void)snprintf(line,sizeof(line),"OCACHE1 SCOPE token=%lu calls=%lu begins=%lu saturations=%lu foreign=%lu irq_included=1\r\n",
        (unsigned long)s.stats.token,(unsigned long)codec_cache.calls,(unsigned long)codec_cache.begins,(unsigned long)codec_cache.saturations,(unsigned long)codec_cache.foreign);
    (void)comp_v11_hal_debug_write(line);
    (void)snprintf(line,sizeof(line),"OCACHE1 TOTAL hits_hi=%lu hits_lo=%lu misses_hi=%lu misses_lo=%lu\r\n",
        (unsigned long)(codec_cache.hits>>32u),(unsigned long)codec_cache.hits,(unsigned long)(codec_cache.misses>>32u),(unsigned long)codec_cache.misses);
    (void)comp_v11_hal_debug_write(line);
    (void)snprintf(line,sizeof(line),"OCACHE1 PEAK wall_us=%lu irq_us=%lu hits=%lu misses=%lu\r\n",
        (unsigned long)codec_cache.peak_us,(unsigned long)codec_cache.peak_irq_us,(unsigned long)codec_cache.peak_hits,(unsigned long)codec_cache.peak_misses);
    (void)comp_v11_hal_debug_write(line);
    (void)snprintf(line,sizeof(line),"CPUIRQ1 token=%lu outer_max_us=%lu exception=%lu at_us=%lu includes_nested=1\r\n",
        (unsigned long)s.stats.token,(unsigned long)outer_irq.max_us,(unsigned long)outer_irq.max_kind,(unsigned long)outer_irq.max_at);
    (void)comp_v11_hal_debug_write(line);
    (void)snprintf(line,sizeof(line),"OCACHE2 token=%lu peak_outer_irq_us=%lu peak_outer_exception=%lu includes_nested=1\r\n",
        (unsigned long)s.stats.token,(unsigned long)codec_irq.peak_us,(unsigned long)codec_irq.peak_kind);
    (void)comp_v11_hal_debug_write(line);
    uint32_t admission=codec_cache.peak_admission_flags;
    (void)snprintf(line,sizeof(line),"OCACHE4 token=%lu reason=%lu pending=%u query_valid=%u radio_busy=%u queued_pcm=%lu next_radio_us=%lu recording_state=%lu same_worst_wall=1\r\n",
        (unsigned long)s.stats.token,(unsigned long)((admission>>8u)&255u),
        (unsigned)(admission&1u),(unsigned)((admission>>1u)&1u),(unsigned)((admission>>2u)&1u),
        (unsigned long)((admission>>16u)&255u),(unsigned long)codec_cache.peak_admission_next_us,(unsigned long)(admission>>24u));
    (void)comp_v11_hal_debug_write(line);
    /* Radio classes are outer envelopes, including any nested capture/tick
     * IRQs. Their complement partitions this same worst-wall Opus frame;
     * it is not exclusive radio CPU or a claim about all frame maxima. */
    uint32_t radio_outer=codec_irq.peak_radio_us;
    bool irq_split_valid=codec_cache.calls>0u && !residence.stats.clock_errors &&
        !residence.stats.order_errors && radio_outer<=codec_cache.peak_irq_us;
    (void)snprintf(line,sizeof(line),"OCACHE3 token=%lu peak_radio_outer_us=%lu peak_other_outer_us=%lu valid=%u includes_nested=1 exclusive=0\r\n",
        (unsigned long)s.stats.token,(unsigned long)radio_outer,
        (unsigned long)(irq_split_valid?codec_cache.peak_irq_us-radio_outer:0u),irq_split_valid?1u:0u);
    (void)comp_v11_hal_debug_write(line);
    (void)snprintf(line,sizeof(line),"CPUBUDGET1 token=%lu calls=%lu gt5000=%lu gt6000=%lu gt8000=%lu invalid=%lu irq_included=1 qualified=0\r\n",
        (unsigned long)s.stats.token,(unsigned long)stage_stats[COMP_CPU_STAGE_OPUS].calls,
        (unsigned long)opus_over_budget[0],(unsigned long)opus_over_budget[1],(unsigned long)opus_over_budget[2],
        (unsigned long)stage_stats[COMP_CPU_STAGE_OPUS].invalid);
    (void)comp_v11_hal_debug_write(line);
#if COMPANION_WBA_CPU_DETAILED_PROFILE
    (void)comp_v11_hal_debug_write("CPHMAP schema=5 slots=17 stage3=panel_tx stage4=hal_inputs_power stage8=capture_progress stage9=main_services stage10=ble_service_capture stage11=runtime_service_capture stage12=presenter_service_capture stage13=render_service_capture stage14=ble_sequencer_capture stage15=ble_link_capture stage16=meeting_aci_capture\r\n");
    (void)snprintf(line,sizeof(line),"CPHSELF0 token=%lu schema=4 slots=17 invalid=%lu open=%lu frame_bytes=%u observation_only=1\r\n",
        (unsigned long)s.stats.token,(unsigned long)stage_self.invalid,(unsigned long)stage_self.depth,(unsigned)sizeof(comp_cpu_stage_span_t));
    (void)comp_v11_hal_debug_write(line);
#else
    (void)comp_v11_hal_debug_write("CPHMAP schema=6 slots=3 mode=audio_nor\r\n");
    (void)snprintf(line,sizeof(line),"CPHSELF0 token=%lu schema=5 slots=3 invalid=%lu open=%lu frame_bytes=%u observation_only=1\r\n",
        (unsigned long)s.stats.token,(unsigned long)stage_self.invalid,(unsigned long)stage_self.depth,(unsigned)sizeof(comp_cpu_stage_span_t));
    (void)comp_v11_hal_debug_write(line);
#endif
    for(unsigned i=0u;i<COMP_CPU_STAGE_STORAGE_COUNT;++i) {
        const stage_stats_t *p=&stage_stats[i];
        (void)snprintf(line,sizeof(line),"CPH1 token=%lu stage=%u calls=%lu wall_hi=%lu wall_lo=%lu thread_hi=%lu thread_lo=%lu irq_hi=%lu irq_lo=%lu max_wall_us=%lu invalid=%lu qualified=0\r\n",
            (unsigned long)s.stats.token,i,(unsigned long)p->calls,
            (unsigned long)((p->thread_us+p->irq_us)>>32u),(unsigned long)(p->thread_us+p->irq_us),
            (unsigned long)(p->thread_us>>32u),(unsigned long)p->thread_us,
            (unsigned long)(p->irq_us>>32u),(unsigned long)p->irq_us,
            (unsigned long)p->max_wall_us,(unsigned long)p->invalid);
        (void)comp_v11_hal_debug_write(line);
        (void)snprintf(line,sizeof(line),"CPHSELF1 token=%lu stage=%u thread_hi=%lu thread_lo=%lu\r\n",
            (unsigned long)s.stats.token,i,(unsigned long)(p->self_thread_us>>32u),(unsigned long)p->self_thread_us);
        (void)comp_v11_hal_debug_write(line);
    }
}
#endif
