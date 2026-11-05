#include "wba_stop.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    bool arm_ok, cleanup_ok, recheck_ok, enter_ok, locked, tick_on;
    uint32_t ticks, delta, added_ms, deadline, enters, arms, disarms, feeds;
    char order[64]; unsigned next;
} fixture_t;
static void note(fixture_t *f,char c) { f->order[f->next++]=c; }
static bool arm(void *p,uint32_t period)
{ fixture_t *f=p;assert(f->tick_on&&!f->locked);note(f,'A');++f->arms;f->deadline=period;return f->arm_ok; }
static bool disarm(void *p)
{ fixture_t *f=p;assert(f->tick_on&&!f->locked);note(f,'D');++f->disarms;return f->cleanup_ok; }
static bool lock(void *p)
{ fixture_t *f=p;assert(!f->locked);f->locked=true;note(f,'L');return f->recheck_ok; }
static void unlock(void *p)
{ fixture_t *f=p;assert(f->locked&&f->tick_on);f->locked=false;note(f,'U'); }
static void suspend(void *p)
{ fixture_t *f=p;assert(f->locked&&f->tick_on);f->tick_on=false;note(f,'S'); }
static void resume(void *p,uint32_t elapsed)
{ fixture_t *f=p;assert(f->locked&&!f->tick_on);f->added_ms+=elapsed;f->tick_on=true;note(f,'R'); }
static uint32_t rtc(void *p)
{ fixture_t *f=p;assert(f->locked&&!f->tick_on);note(f,'T');return f->ticks; }
static void feed(void *p)
{ fixture_t *f=p;assert(f->locked&&!f->tick_on);note(f,'F');++f->feeds; }
static bool enter(void *p)
{ fixture_t *f=p;assert(f->locked&&!f->tick_on);note(f,'E');++f->enters;f->ticks+=f->delta;return f->enter_ok; }
static fixture_t fixture(void)
{ fixture_t f={0};f.arm_ok=f.cleanup_ok=f.recheck_ok=f.enter_ok=f.tick_on=true;f.delta=21u;return f; }
static void init(comp_wba_stop_t *s,fixture_t *f,bool enabled)
{
    static const comp_wba_stop_ports_t p={arm,disarm,lock,unlock,suspend,resume,rtc,enter,feed};
    comp_wba_stop_init(s,&p,f,enabled);
    assert(s->ports==&p && s->context==f);
}
int main(void)
{
    comp_wba_stop_t s;fixture_t f=fixture();init(&s,&f,false);
    assert(comp_wba_stop_run(&s,true)==COMP_WBA_STOP_SKIPPED&&!f.arms);
    init(&s,&f,true);assert(comp_wba_stop_run(&s,false)==COMP_WBA_STOP_SKIPPED&&!f.arms);
    assert(comp_wba_stop_run(&s,true)==COMP_WBA_STOP_COMPLETED);
    assert(!strcmp(f.order,"ALSTFETRUD"));assert(f.deadline==20u&&f.added_ms==20u&&f.feeds==1u);
    assert(!f.locked&&f.tick_on&&s.completed==1u&&s.failures==0u);
    puts("PASS Stop lifecycle: RTC armed before atomic recheck; tick suspended only under lock; watchdog fed; clock-return before compensation; cleanup after unlock");

    f=fixture();f.recheck_ok=false;init(&s,&f,true);
    assert(comp_wba_stop_run(&s,true)==COMP_WBA_STOP_ABORTED);
    assert(!strcmp(f.order,"ALUD")&&!f.enters&&!f.feeds&&f.tick_on&&!f.locked&&s.enabled);
    f.next=0;memset(f.order,0,sizeof(f.order));f.recheck_ok=true;
    assert(comp_wba_stop_run(&s,true)==COMP_WBA_STOP_COMPLETED);
    assert(s.aborted==1u&&s.completed==1u);
    puts("PASS race abort: late button/radio/task veto leaves tick running and timer removed, then retry succeeds");

    f=fixture();f.arm_ok=false;init(&s,&f,true);
    assert(comp_wba_stop_run(&s,true)==COMP_WBA_STOP_FAULT);
    assert(!strcmp(f.order,"AD")&&!s.enabled&&!f.enters);
    assert(comp_wba_stop_run(&s,true)==COMP_WBA_STOP_SKIPPED&&f.arms==1u);
    f=fixture();f.cleanup_ok=false;init(&s,&f,true);
    assert(comp_wba_stop_run(&s,true)==COMP_WBA_STOP_FAULT&&!s.enabled&&!f.locked&&f.tick_on);
    f=fixture();f.enter_ok=false;init(&s,&f,true);
    assert(comp_wba_stop_run(&s,true)==COMP_WBA_STOP_FAULT&&!s.enabled&&!f.locked&&f.tick_on);
    puts("PASS alarm/cleanup/clock failures disable further Stop attempts and restore tick/IRQ ownership");

    f=fixture();f.ticks=UINT32_MAX-9u;f.delta=21u;init(&s,&f,true);
    assert(comp_wba_stop_run(&s,true)==COMP_WBA_STOP_COMPLETED&&f.added_ms==20u);
    f=fixture();f.delta=1u;init(&s,&f,true);
    for(unsigned i=0;i<1024u;++i) { f.next=0;assert(comp_wba_stop_run(&s,true)==COMP_WBA_STOP_COMPLETED); }
    assert(f.added_ms==1000u&&s.compensated_ms==1000u&&!s.fraction);
    f=fixture();f.delta=UINT32_MAX;init(&s,&f,true);
    assert(comp_wba_stop_run(&s,true)==COMP_WBA_STOP_FAULT&&f.added_ms==0u&&s.compensated_ms==0u);
    f=fixture();f.delta=1025u;init(&s,&f,true);
    assert(comp_wba_stop_run(&s,true)==COMP_WBA_STOP_FAULT&&!s.enabled);
    puts("PASS RTC compensation: unsigned wrap, fractional remainder, 1024 short sleeps equal 1000ms, backward/overlong time rejected");
    comp_wba_rtc_clock_t clock;
    uint32_t counter=UINT32_MAX-500u;
    comp_wba_rtc_clock_init(&clock,counter,500u);
    for(unsigned i=0;i<1024u;++i) {
        /* 1 RTC tick awake, 20 asleep, 1 awake. Every entry happens between
         * millisecond boundaries; the complete timeline must remain exact. */
        assert(comp_wba_rtc_clock_update(&clock,++counter));
        counter+=20u;assert(comp_wba_rtc_clock_update(&clock,counter));
        assert(comp_wba_rtc_clock_update(&clock,++counter));
    }
    assert(clock.milliseconds==22500u&&!clock.fraction);
    assert(!comp_wba_rtc_clock_update(&clock,counter-1u)&&clock.milliseconds==22500u);
    comp_wba_rtc_clock_init(&clock,0u,UINT32_MAX-9u);
    assert(comp_wba_rtc_clock_update(&clock,1024u)&&clock.milliseconds==990u);
    puts("PASS continuous timebase: partial awake ticks survive 1024 Stop cycles; RTC and HAL millisecond wraps; invalid read cannot change time");
    /* 64MHz model: one RTC tick=62500 cycles, one ms=64000 cycles.
     * Each RTC wake returns at a fixed200us phase. A900us awake interval
     * crosses the RTC boundary before the next20-tick sleep. Summing only
     * stopped RTC deltas plus independent awake SysTick loses79ms in21s. */
    uint64_t wall_cycles=12800u;
    uint32_t awake_phase=0u,hal=0u,legacy=0u,sleep_fraction=0u;
    comp_wba_rtc_clock_init(&clock,0u,0u);
    for(unsigned i=0;i<1024u;++i) {
        wall_cycles+=57600u;awake_phase+=57600u;
        uint32_t awake_ms=awake_phase/64000u;awake_phase%=64000u;
        hal+=awake_ms;legacy+=awake_ms;
        uint32_t rtc_before=(uint32_t)(wall_cycles/62500u);
        wall_cycles=(uint64_t)(rtc_before+20u)*62500u+12800u;
        uint32_t scaled=20u*1000u+sleep_fraction;
        uint32_t slept=scaled/1024u;sleep_fraction=scaled%1024u;
        legacy+=slept;
        hal=comp_wba_rtc_clock_compensate(&clock,(uint32_t)(wall_cycles/62500u),hal,slept);
    }
    assert(legacy==20921u&&hal==21000u);
    puts("PASS repeated Stop phase regression: old hybrid20921ms vs21000ms real; continuous wake alignment21000ms");
    comp_wba_rtc_clock_init(&clock,0u,100u);
    assert(comp_wba_rtc_clock_compensate(&clock,1u,101u,0u)==101u);
    assert(comp_wba_rtc_clock_compensate(&clock,2u,102u,1u)==102u);
    comp_wba_rtc_clock_init(&clock,UINT32_MAX-5u,UINT32_MAX-2u);
    assert(comp_wba_rtc_clock_compensate(&clock,1018u,UINT32_MAX-2u,1000u)==997u);
    assert(comp_wba_rtc_clock_compensate(&clock,1017u,997u,20u)==1017u);
    assert(clock.last_ticks==1017u&&clock.milliseconds==1017u&&!clock.fraction);
    assert(comp_wba_rtc_clock_compensate(&clock,5000u,4000u,20u)==4020u);
    puts("PASS wake alignment: never reverses an ahead SysTick; RTC/HAL wraps; backward or long awake RTC gaps use bounded fallback and reanchor");
    comp_wba_stop_init(&s,NULL,&f,true);assert(!s.enabled);
    assert(comp_wba_stop_run(NULL,true)==COMP_WBA_STOP_SKIPPED);
    puts("PASS_PREHARDWARE_SOFTWARE_ONLY Stop coordinator; clocks/radio/EXTI/current hardware acceptance NOT_RUN");
    return 0;
}
