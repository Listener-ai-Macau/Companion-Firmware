#include "wba_stop.h"
#include <string.h>

void comp_wba_rtc_clock_init(comp_wba_rtc_clock_t *c,uint32_t ticks,uint32_t ms)
{ c->last_ticks=ticks; c->milliseconds=ms; c->fraction=0u; }
bool comp_wba_rtc_clock_update(comp_wba_rtc_clock_t *c,uint32_t ticks)
{
    uint32_t elapsed=ticks-c->last_ticks;
    if (elapsed>COMP_WBA_STOP_RTC_HZ) return false;
    uint32_t scaled=elapsed*1000u+c->fraction;
    c->milliseconds+=scaled/COMP_WBA_STOP_RTC_HZ;
    c->fraction=(uint16_t)(scaled%COMP_WBA_STOP_RTC_HZ);
    c->last_ticks=ticks;
    return true;
}
uint32_t comp_wba_rtc_clock_compensate(comp_wba_rtc_clock_t *c,uint32_t ticks,
                                     uint32_t hal_ms,uint32_t stopped_ms)
{
    if (!comp_wba_rtc_clock_update(c,ticks)) {
        hal_ms+=stopped_ms;
        comp_wba_rtc_clock_init(c,ticks,hal_ms);
        return hal_ms;
    }
    /* RTC is quantized to 1/1024 s and SysTick can already be one partial
     * millisecond ahead. Keep that ordinary tick, but retain the independent
     * RTC anchor so this lead is not accumulated again at every wake. */
    return (int32_t)(c->milliseconds-hal_ms)>0 ? c->milliseconds : hal_ms;
}

void comp_wba_stop_init(comp_wba_stop_t *s, const comp_wba_stop_ports_t *p, void *context, bool enabled)
{
    if (!s) return;
    memset(s,0,sizeof(*s));
    if (!p) return;
    s->ports=p; s->context=context;
    s->enabled=enabled && p->arm && p->disarm && p->lock_recheck && p->unlock &&
        p->suspend_tick && p->resume_tick && p->rtc_ticks && p->enter && p->watchdog;
}
static comp_wba_stop_result_t failed(comp_wba_stop_t *s)
{ ++s->failures; s->enabled=false; return COMP_WBA_STOP_FAULT; }
comp_wba_stop_result_t comp_wba_stop_run(comp_wba_stop_t *s, bool eligible)
{
    uint32_t before, elapsed, ms=0;
    bool clock_ok, time_ok, cleanup_ok;
    if (!s || !s->enabled || !eligible) return COMP_WBA_STOP_SKIPPED;
    const comp_wba_stop_ports_t *p=s->ports;
    if (!p->arm(s->context,COMP_WBA_STOP_WAKE_MS)) {
        (void)p->disarm(s->context);
        return failed(s);
    }
    if (!p->lock_recheck(s->context)) {
        p->unlock(s->context);
        cleanup_ok=p->disarm(s->context);
        ++s->aborted;
        return cleanup_ok ? COMP_WBA_STOP_ABORTED : failed(s);
    }
    p->suspend_tick(s->context);
    before=p->rtc_ticks(s->context);
    p->watchdog(s->context);
    clock_ok=p->enter(s->context);
    elapsed=p->rtc_ticks(s->context)-before;
    /* A 20ms wake timer plus clock recovery must never take a second. Do not
     * fabricate a many-day HAL tick jump after an invalid/backward RTC read. */
    time_ok=elapsed<=COMP_WBA_STOP_RTC_HZ;
    if (time_ok) {
        uint32_t scaled=elapsed*1000u+s->fraction;
        ms=scaled/COMP_WBA_STOP_RTC_HZ;
        s->fraction=(uint16_t)(scaled%COMP_WBA_STOP_RTC_HZ);
        s->compensated_ms+=ms;
    }
    p->resume_tick(s->context,ms);
    p->unlock(s->context);
    cleanup_ok=p->disarm(s->context);
    if (!clock_ok || !time_ok || !cleanup_ok) return failed(s);
    ++s->completed;
    return COMP_WBA_STOP_COMPLETED;
}
