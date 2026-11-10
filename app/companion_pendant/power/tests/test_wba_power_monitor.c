#include "wba_power_monitor.h"
#include "wba_button.h"
#include "power_policy.h"
#include "wba_board_power_profile.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"FAIL power line=%d: %s\n",__LINE__,#x); return 1; } } while (0)
typedef struct {
    uint32_t gates_on, gates_off, starts, cancels;
    uint16_t raw;
    comp_wba_adc_result_t result;
    bool gate_on, gate_fail, start_fail;
} fixture_t;
static bool gate(void *ctx, bool on)
{
    fixture_t *f=ctx;
    if (on) ++f->gates_on; else ++f->gates_off;
    if (f->gate_fail) return false;
    f->gate_on=on; return true;
}
static bool start(void *ctx) { fixture_t *f=ctx; ++f->starts; return !f->start_fail; }
static comp_wba_adc_result_t read_adc(void *ctx, uint16_t *raw)
{ fixture_t *f=ctx; *raw=f->raw; return f->result; }
static void cancel(void *ctx) { fixture_t *f=ctx; ++f->cancels; }
static const comp_wba_soc_point_t measured_curve[]={{3000,0},{3600,30},{4200,100}};
static comp_wba_power_profile_t profile(void)
{
    return (comp_wba_power_profile_t){.top_ohm=150000,.bottom_ohm=68000,
        .reference_mv=1800,.reference_min_mv=1700,.maximum_battery_mv=4350,
        .minimum_battery_mv=2800,.minimum_update_mv=3600,.adc_full_scale=4095,
        .soc_points=measured_curve,.soc_point_count=3,
        .divider_verified=true,.reference_verified=true,.charger_pullups_verified=true};
}
static void init(comp_wba_power_monitor_t *m, fixture_t *f, comp_wba_power_profile_t *p, uint32_t now)
{
    memset(f,0,sizeof(*f)); f->raw=2800; f->result=COMP_WBA_ADC_READY;
    comp_wba_power_ports_t ports={gate,start,read_adc,cancel,f};
    comp_wba_power_monitor_init(m,p,&ports,now);
}
static void inputs(comp_wba_power_monitor_t *m, bool pg, bool stat, uint32_t from, uint32_t duration)
{
    for (uint32_t offset=0; offset<=duration; offset+=20)
        comp_wba_power_monitor_inputs(m,true,pg,stat,from+offset);
}
static int charger(void)
{
    comp_wba_power_monitor_t m; fixture_t f; comp_wba_power_profile_t p=profile();
    init(&m,&f,&p,0);
    CHECK(comp_wba_power_monitor_ota_blockers(&m,0)==COMP_WBA_OTA_POWER_UNKNOWN);
    inputs(&m,true,true,0,140);
    CHECK(m.value.charger_valid && !m.value.charger_present && m.value.charge_state==COMP_WBA_CHARGE_DISCHARGING);
    inputs(&m,false,true,160,100);
    CHECK(!m.value.charger_valid);
    inputs(&m,false,true,280,2020);
    CHECK(m.value.charger_valid && m.value.charger_present && m.value.charge_state==COMP_WBA_CHARGE_POWERED_IDLE);
    CHECK(comp_wba_power_monitor_ota_blockers(&m,2300)==0u);
    CHECK(!comp_wba_power_monitor_snapshot(&m,2401).charger_valid);
    CHECK(comp_wba_power_monitor_ota_blockers(&m,2401)==COMP_WBA_OTA_POWER_UNKNOWN);
    comp_wba_power_monitor_inputs(&m,false,false,false,2320);
    CHECK(m.value.charge_state==COMP_WBA_CHARGE_UNKNOWN && !m.value.charger_valid);
    /* 1Hz is two 500ms halves. Neither low nor high half gets published as
     * charging/full while the monitor establishes the fault cadence. */
    for (uint32_t now=3000; now<=5000; now+=20) {
        bool stat=((now-3000)/500)%2!=0;
        comp_wba_power_monitor_inputs(&m,true,false,stat,now);
        if (now<4500) CHECK(m.value.charge_state==COMP_WBA_CHARGE_UNKNOWN);
    }
    CHECK(m.value.charge_state==COMP_WBA_CHARGE_FAULT);
    CHECK(comp_wba_power_monitor_ota_blockers(&m,5000)==COMP_WBA_OTA_CHARGER_FAULT);
    inputs(&m,false,false,5020,2020);
    CHECK(m.value.charge_state==COMP_WBA_CHARGE_CHARGING && m.blink_edges==0u);
    inputs(&m,false,true,7060,2020);
    CHECK(m.value.charge_state==COMP_WBA_CHARGE_POWERED_IDLE); /* never FULL */
    p.charger_pullups_verified=false; init(&m,&f,&p,0);
    inputs(&m,false,false,0,3000);
    CHECK(!m.value.charger_valid && m.value.charge_state==COMP_WBA_CHARGE_UNKNOWN);
    init(&m,&f,&(comp_wba_power_profile_t){0},0);
    inputs(&m,false,false,0,3000);
    CHECK(!m.value.charger_valid && !m.sampling_enabled && f.gates_on==0u);
    /* Missing cell ADC must not disable the independently wired charger.
     * The same ADC ports become usable when the real board profile is ready. */
    p=profile();p.divider_verified=false;p.reference_verified=false;
    init(&m,&f,&p,0u);inputs(&m,false,false,0u,2200u);
    comp_wba_power_monitor_poll(&m,true,2200u);
    comp_wba_power_snapshot_t value=comp_wba_power_monitor_snapshot(&m,2200u);
    CHECK(!m.sampling_enabled && f.gates_on==0u && f.starts==0u);
    CHECK(value.charger_valid && value.charger_present && value.charge_state==COMP_WBA_CHARGE_CHARGING);
    CHECK(!value.voltage_valid && !value.percent_valid && value.percent==255u);
    CHECK(comp_wba_power_monitor_recording_allowed(&m,2200u));
    p.divider_verified=true;p.reference_verified=true;
    init(&m,&f,&p,0u);
    comp_wba_power_monitor_poll(&m,true,0u);comp_wba_power_monitor_poll(&m,true,2u);
    comp_wba_power_monitor_poll(&m,true,3u);comp_wba_power_monitor_poll(&m,true,4u);
    CHECK(m.sampling_enabled && m.value.voltage_valid && f.starts==1u && !f.gate_on);
    puts("PASS charger: independent of missing ADC; same ports accept measured profile; debounce, stale input, STAT high never full, 1Hz fault/recovery");
    return 0;
}
static int battery(void)
{
    comp_wba_power_monitor_t m; fixture_t f; comp_wba_power_profile_t p=profile();
    CHECK(comp_wba_power_profile_safe(&p));
    CHECK(comp_wba_power_profile_safe(&comp_v11_qualified_power) && comp_v11_qualified_power.top_ohm==150000u &&
        comp_v11_qualified_power.reference_verified && comp_v11_qualified_power.soc_point_count==0u);
    init(&m,&f,&p,0);
    comp_wba_power_monitor_poll(&m,false,0); CHECK(f.gates_on==0u);
    comp_wba_power_monitor_poll(&m,true,0); CHECK(f.gate_on && f.starts==0u);
    comp_wba_power_monitor_poll(&m,true,1); CHECK(f.starts==0u);
    comp_wba_power_monitor_poll(&m,true,2); CHECK(f.starts==1u && comp_wba_power_monitor_busy(&m));
    comp_wba_power_monitor_poll(&m,true,3); CHECK(m.value.voltage_valid && m.value.percent_valid);
    CHECK(m.value.millivolts>3900u && m.value.millivolts<4000u && m.value.percent>=65u && m.value.percent<=80u);
    CHECK(comp_wba_power_monitor_ota_blockers(&m,3)==0u);
    comp_wba_power_monitor_poll(&m,true,4); CHECK(!f.gate_on && !comp_wba_power_monitor_busy(&m));
    comp_wba_power_monitor_poll(&m,true,5003); CHECK(f.gates_on==1u);
    CHECK(!comp_wba_power_monitor_snapshot(&m,15003).voltage_valid);
    CHECK(comp_wba_power_monitor_snapshot(&m,15003).percent==255u);
    f.raw=2350; comp_wba_power_monitor_poll(&m,true,5004);
    comp_wba_power_monitor_poll(&m,true,5006); comp_wba_power_monitor_poll(&m,true,5007);
    CHECK(m.value.voltage_valid && m.value.millivolts<3600u);
    CHECK(comp_wba_power_monitor_ota_blockers(&m,5007)==COMP_WBA_OTA_POWER_LOW);
    comp_wba_power_monitor_poll(&m,true,5008);
    f.raw=4095; comp_wba_power_monitor_poll(&m,true,10008);
    comp_wba_power_monitor_poll(&m,true,10010); comp_wba_power_monitor_poll(&m,true,10011);
    CHECK(!m.value.voltage_valid && comp_wba_power_monitor_snapshot(&m,10011).millivolts==0u);
    CHECK(comp_wba_power_monitor_ota_blockers(&m,10011)==COMP_WBA_OTA_POWER_UNKNOWN);
    comp_wba_power_monitor_poll(&m,true,10012);
    p.top_ohm=68000; init(&m,&f,&p,0);
    CHECK(!m.sampling_enabled); comp_wba_power_monitor_poll(&m,true,0); CHECK(f.gates_on==0u);
    p=profile(); p.reference_verified=false; CHECK(!comp_wba_power_profile_safe(&p));
    p=profile(); p.soc_points=NULL; CHECK(!comp_wba_power_profile_safe(&p));
    p=profile(); p.soc_point_count=0; p.soc_points=NULL; init(&m,&f,&p,0);
    comp_wba_power_monitor_poll(&m,true,0); comp_wba_power_monitor_poll(&m,true,2);
    comp_wba_power_monitor_poll(&m,true,3);
    CHECK(m.value.voltage_valid && !m.value.percent_valid && comp_wba_power_monitor_snapshot(&m,3).percent==255u);
    puts("PASS battery: explicit electrical/curve qualification, nonblocking gate/settle/ADC/cleanup, no clipping or fabricated SOC, stale/low OTA gate");
    return 0;
}
static int failures_and_wrap(void)
{
    comp_wba_power_monitor_t m; fixture_t f; comp_wba_power_profile_t p=profile();
    init(&m,&f,&p,UINT32_MAX-1u);
    comp_wba_power_monitor_poll(&m,true,UINT32_MAX-1u); comp_wba_power_monitor_poll(&m,true,0);
    CHECK(f.starts==1u); f.result=COMP_WBA_ADC_PENDING;
    comp_wba_power_monitor_poll(&m,true,19); CHECK(m.phase==COMP_WBA_BAT_CONVERT);
    comp_wba_power_monitor_poll(&m,true,249); CHECK(m.phase==COMP_WBA_BAT_CONVERT);
    comp_wba_power_monitor_poll(&m,true,250); CHECK(m.phase==COMP_WBA_BAT_CLEANUP && m.sample_errors==1u);
    f.gate_fail=true; comp_wba_power_monitor_poll(&m,false,251); CHECK(m.gate_may_be_on && comp_wba_power_monitor_busy(&m));
    f.gate_fail=false; comp_wba_power_monitor_poll(&m,false,252); CHECK(!f.gate_on && !comp_wba_power_monitor_busy(&m));
    init(&m,&f,&p,0); comp_wba_power_monitor_poll(&m,true,0);
    comp_wba_power_monitor_poll(&m,false,1); CHECK(m.phase==COMP_WBA_BAT_CLEANUP && f.starts==0u);
    comp_wba_power_monitor_poll(&m,false,2); CHECK(!f.gate_on);
    init(&m,&f,&p,0); f.start_fail=true;
    comp_wba_power_monitor_poll(&m,true,0); comp_wba_power_monitor_poll(&m,true,2);
    CHECK(m.phase==COMP_WBA_BAT_CLEANUP && m.sample_errors==1u && f.cancels==1u);
    comp_wba_power_monitor_poll(&m,false,3); CHECK(!f.gate_on);
    init(&m,&f,&p,UINT32_MAX-2000u);
    inputs(&m,false,false,UINT32_MAX-2000u,2020u);
    CHECK(m.value.charge_state==COMP_WBA_CHARGE_CHARGING);
    puts("PASS failure/wrap: pending timeout, gate ambiguity blocks sleep until successful off, audio cancels sampling, wrap-safe deadlines");
    return 0;
}
static int button(void)
{
    comp_wba_button_t b;
    comp_wba_button_init(&b,false,0);
    CHECK(comp_wba_button_poll(&b,true,true,100)==0u);
    CHECK(comp_wba_button_poll(&b,true,true,130)==COMP_WBA_BUTTON_WAKE);
    CHECK(comp_wba_button_poll(&b,true,false,1000)==0u);
    CHECK(comp_wba_button_poll(&b,false,false,1100)==0u);
    CHECK(comp_wba_button_poll(&b,false,false,1130)==0u && !comp_wba_button_busy(&b));
    CHECK(comp_wba_button_poll(&b,true,false,1200)==0u);
    CHECK(comp_wba_button_poll(&b,true,false,1230)==COMP_WBA_BUTTON_WAKE);
    CHECK(comp_wba_button_poll(&b,true,false,1900)==COMP_WBA_BUTTON_RECORD_TOGGLE);
    CHECK(comp_wba_button_poll(&b,true,false,3000)==0u);
    (void)comp_wba_button_poll(&b,false,false,3100);
    CHECK(comp_wba_button_poll(&b,false,false,3130)==0u);
    (void)comp_wba_button_poll(&b,true,false,3200);
    CHECK(comp_wba_button_poll(&b,true,false,3230)==COMP_WBA_BUTTON_WAKE);
    (void)comp_wba_button_poll(&b,false,false,3300);
    CHECK(comp_wba_button_poll(&b,false,false,3330)==COMP_WBA_BUTTON_CONFIRM);
    comp_wba_button_init(&b,true,0); CHECK(comp_wba_button_poll(&b,true,false,2000)==0u);
    (void)comp_wba_button_poll(&b,false,false,2100); CHECK(comp_wba_button_poll(&b,false,false,2130)==0u);
    comp_wba_button_init(&b,false,UINT32_MAX-100u);
    (void)comp_wba_button_poll(&b,true,false,UINT32_MAX-20u);
    CHECK(comp_wba_button_poll(&b,false,false,UINT32_MAX-10u)==0u);
    (void)comp_wba_button_poll(&b,true,false,UINT32_MAX-1u);
    CHECK(comp_wba_button_poll(&b,true,false,28)==COMP_WBA_BUTTON_WAKE);
    CHECK(comp_wba_button_poll(&b,true,false,698)==COMP_WBA_BUTTON_RECORD_TOGGLE);
    /* The next foreground observation can already be the release. */
    comp_wba_button_init(&b,false,0u);
    (void)comp_wba_button_poll_with_double(&b,true,false,true,10u);
    (void)comp_wba_button_poll_with_double(&b,true,false,true,50u);
    CHECK(comp_wba_button_poll_with_double(&b,false,false,true,1110u)==COMP_WBA_BUTTON_RECORD_TOGGLE);
    CHECK(b.max_hold_ms==1100u&&b.last_event==COMP_WBA_BUTTON_RECORD_TOGGLE);
    CHECK(comp_wba_button_poll_with_double(&b,false,false,true,1150u)==0u);
    /* Even DOWN's debounce poll can be deferred for the entire hold. */
    comp_wba_button_init(&b,false,0u);
    (void)comp_wba_button_poll(&b,true,false,10u);
    CHECK(comp_wba_button_poll(&b,false,false,1010u)==COMP_WBA_BUTTON_RECORD_TOGGLE);
    (void)comp_wba_button_poll(&b,true,false,1100u);
    CHECK(comp_wba_button_poll(&b,false,false,2100u)==COMP_WBA_BUTTON_RECORD_TOGGLE);
    /* A sleeping first press and a key held at boot remain wake-only. */
    comp_wba_button_init(&b,false,0u);
    (void)comp_wba_button_poll(&b,true,true,10u);
    CHECK(comp_wba_button_poll(&b,false,false,1010u)==0u);
    comp_wba_button_init(&b,true,0u);
    CHECK(comp_wba_button_poll(&b,false,false,1010u)==0u);
    /* Idle double click remains one pairing gesture, never a long hold. */
    comp_wba_button_init(&b,false,0u);
    (void)comp_wba_button_poll_with_double(&b,true,false,true,100u);
    CHECK(comp_wba_button_poll_with_double(&b,true,false,true,130u)==COMP_WBA_BUTTON_WAKE);
    (void)comp_wba_button_poll_with_double(&b,false,false,true,160u);
    CHECK(comp_wba_button_poll_with_double(&b,false,false,true,190u)==0u);
    (void)comp_wba_button_poll_with_double(&b,true,false,true,230u);
    CHECK(comp_wba_button_poll_with_double(&b,true,false,true,260u)==COMP_WBA_BUTTON_WAKE);
    (void)comp_wba_button_poll_with_double(&b,false,false,true,290u);
    CHECK(comp_wba_button_poll_with_double(&b,false,false,true,320u)==COMP_WBA_BUTTON_DOUBLE_CONFIRM);
    CHECK(comp_wba_button_poll_with_double(&b,false,false,true,700u)==0u);
    /* Recorder-card policy: a full second, one event while held, no delayed
     * double-click interpretation and no short action after a long release. */
    comp_wba_button_init(&b,false,0u);
    CHECK(comp_wba_button_poll_with_hold(&b,true,false,false,1000u,100u)==0u);
    CHECK(comp_wba_button_poll_with_hold(&b,true,false,false,1000u,130u)==COMP_WBA_BUTTON_WAKE);
    CHECK(comp_wba_button_poll_with_hold(&b,true,false,false,1000u,1099u)==0u);
    CHECK(comp_wba_button_poll_with_hold(&b,true,false,false,1000u,1100u)==COMP_WBA_BUTTON_RECORD_TOGGLE);
    CHECK(comp_wba_button_poll_with_hold(&b,true,false,false,1000u,5000u)==0u);
    CHECK(comp_wba_button_poll_with_hold(&b,false,false,false,1000u,5100u)==0u);
    CHECK(comp_wba_button_poll_with_hold(&b,false,false,false,1000u,5130u)==0u);
    (void)comp_wba_button_poll_with_hold(&b,true,false,false,1000u,5200u);
    (void)comp_wba_button_poll_with_hold(&b,true,false,false,1000u,5230u);
    CHECK(comp_wba_button_poll_with_hold(&b,false,false,false,1000u,5300u)==0u);
    CHECK(comp_wba_button_poll_with_hold(&b,false,false,false,1000u,5330u)==COMP_WBA_BUTTON_CONFIRM);
    CHECK(!comp_wba_button_busy(&b));
    comp_wba_button_init(&b,false,0u);
    (void)comp_wba_button_poll_with_hold(&b,true,false,false,1000u,10u);
    CHECK(comp_wba_button_poll_with_hold(&b,false,false,false,1000u,1010u)==COMP_WBA_BUTTON_RECORD_TOGGLE);
    CHECK(comp_wba_button_poll_with_hold(&b,false,false,false,1000u,1040u)==0u);
    /* Entire short press between polls, exact hardware-second hold with a
     * late DOWN sample, bounce and chronological UP-before-next-DOWN. */
    comp_wba_button_init(&b,false,0u);
    comp_wba_button_edges_t edge={100u,180u,3u,false};
    CHECK(comp_wba_button_poll_edges(&b,&edge,1000u,220u)==(COMP_WBA_BUTTON_WAKE|COMP_WBA_BUTTON_CONFIRM));
    comp_wba_button_init(&b,false,0u);edge=(comp_wba_button_edges_t){100u,0u,1u,true};
    CHECK(comp_wba_button_poll_edges(&b,&edge,1000u,140u)==COMP_WBA_BUTTON_WAKE);
    edge=(comp_wba_button_edges_t){100u,1100u,2u,false};
    CHECK(comp_wba_button_poll_edges(&b,&edge,1000u,1100u)==COMP_WBA_BUTTON_RECORD_TOGGLE);
    edge.flags=0u;CHECK(comp_wba_button_poll_edges(&b,&edge,1000u,1150u)==0u);
    comp_wba_button_init(&b,false,0u);edge=(comp_wba_button_edges_t){100u,110u,3u,false};
    CHECK(comp_wba_button_poll_edges(&b,&edge,1000u,150u)==0u);
    comp_wba_button_init(&b,false,0u);edge=(comp_wba_button_edges_t){100u,0u,1u,true};
    CHECK(comp_wba_button_poll_edges(&b,&edge,1000u,140u)==COMP_WBA_BUTTON_WAKE);
    edge=(comp_wba_button_edges_t){300u,250u,3u,true};
    CHECK(comp_wba_button_poll_edges(&b,&edge,1000u,340u)==(COMP_WBA_BUTTON_CONFIRM|COMP_WBA_BUTTON_WAKE));
    comp_wba_button_init(&b,false,UINT32_MAX-1000u);
    edge=(comp_wba_button_edges_t){UINT32_MAX-499u,500u,3u,false};
    CHECK((comp_wba_button_poll_edges(&b,&edge,1000u,550u)&COMP_WBA_BUTTON_RECORD_TOGGLE)!=0u);
    CHECK(comp_power_policy_self_test());
    puts("PASS button/policy: first sleep press and held boot only wake, next 700ms press toggles once, bounce/wrap, button-only readiness and all module blockers");
    return 0;
}
static int raw_observation(void)
{
    comp_wba_power_monitor_t m; fixture_t f;
    comp_wba_power_profile_t p=comp_v11_qualified_power;
    p.top_ohm=68000u; p.bottom_ohm=68000u;
    p.divider_verified=false; p.reference_verified=false; p.charger_pullups_verified=false;
    init(&m,&f,&p,0u);
    CHECK(!m.sampling_enabled && !comp_wba_power_profile_safe(&m.profile));
    CHECK(!comp_wba_power_monitor_enable_raw(&m));
    comp_wba_power_monitor_poll(&m,true,0u); CHECK(!f.gate_on && f.starts==0u);
    p.divider_verified=true; init(&m,&f,&p,0u);
    CHECK(!comp_wba_power_monitor_enable_raw(&m));
    comp_wba_power_monitor_poll(&m,true,0u); CHECK(!f.gate_on && f.starts==0u);
    p.top_ohm=150000u; p.divider_verified=false; init(&m,&f,&p,0u);
    CHECK(!comp_wba_power_monitor_enable_raw(&m));
    p.divider_verified=true; init(&m,&f,&p,0u);
    CHECK(comp_wba_power_monitor_enable_raw(&m));
    CHECK(m.sampling_enabled && m.raw_diagnostic && m.profile.divider_verified && !m.profile.reference_verified);
    CHECK(!comp_wba_power_monitor_enable_raw(&m));
    comp_wba_power_monitor_poll(&m,false,0u); CHECK(!f.gate_on);
    comp_wba_power_monitor_poll(&m,true,0u); CHECK(f.gate_on && f.starts==0u);
    comp_wba_power_monitor_poll(&m,true,1u); CHECK(f.starts==0u);
    comp_wba_power_monitor_poll(&m,true,2u); CHECK(f.starts==1u);
    comp_wba_power_monitor_poll(&m,true,3u);
    CHECK(!m.value.voltage_valid && !m.value.percent_valid && m.sample_errors==0u);
    CHECK(comp_wba_power_monitor_snapshot(&m,3u).millivolts==0u);
    CHECK(comp_wba_power_monitor_snapshot(&m,3u).percent==255u);
    CHECK(comp_wba_power_monitor_ota_blockers(&m,3u)==COMP_WBA_OTA_POWER_UNKNOWN);
    comp_wba_power_monitor_poll(&m,true,4u); CHECK(!f.gate_on);
    comp_wba_power_monitor_poll(&m,true,5003u); CHECK(f.gates_on==1u);
    /* Clipped raw is an implausible sample and must stay unknown. */
    f.raw=4095u;
    comp_wba_power_monitor_poll(&m,true,5004u);
    comp_wba_power_monitor_poll(&m,true,5006u);
    comp_wba_power_monitor_poll(&m,true,5007u);
    CHECK(m.sample_errors==1u && m.sample_fault && !m.value.voltage_valid);
    CHECK(comp_wba_power_monitor_ota_blockers(&m,5007u)==COMP_WBA_OTA_POWER_UNKNOWN);
    comp_wba_power_monitor_poll(&m,true,5008u); CHECK(!f.gate_on);
    /* Starting audio during conversion cancels and closes the divider. */
    f.result=COMP_WBA_ADC_PENDING;
    comp_wba_power_monitor_poll(&m,true,10008u);
    comp_wba_power_monitor_poll(&m,true,10010u);
    uint32_t cancels=f.cancels;
    comp_wba_power_monitor_poll(&m,false,10011u); CHECK(f.cancels==cancels+1u);
    comp_wba_power_monitor_poll(&m,false,10012u);
    CHECK(!f.gate_on && !comp_wba_power_monitor_busy(&m));
    init(&m,&f,&p,0u); m.ports.cancel=NULL;
    CHECK(!comp_wba_power_monitor_enable_raw(&m));
    init(&m,&f,&p,0u); m.gate_may_be_on=true;
    CHECK(!comp_wba_power_monitor_enable_raw(&m));
    p=profile(); init(&m,&f,&p,0u);
    CHECK(m.sampling_enabled && !comp_wba_power_monitor_enable_raw(&m) && !m.raw_diagnostic);
    puts("PASS raw battery observation: unverified/over-range divider rejected before gate, safe verified divider gated cadence, audio cancellation, saturation remains unqualified, unknown SOC/OTA");
    return 0;
}
int main(int argc, char **argv)
{
    if (argc==2 && strcmp(argv[1],"--raw-only")==0) return raw_observation();
    if (raw_observation()) return 1;
    if (charger() || battery() || failures_and_wrap() || button()) return 1;
    puts("PASS_HOST_ONLY: WBA power monitor and button; physical electrical/ADC/BLE/STOP acceptance NOT_RUN");
    return 0;
}
