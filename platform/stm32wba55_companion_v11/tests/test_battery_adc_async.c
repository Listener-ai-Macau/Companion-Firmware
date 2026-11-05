#include "battery_adc.h"
#include "fake_adc_hal.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){printf("FAIL line=%d %s\n",__LINE__,#x);return 1;}}while(0)

ADC_TypeDef fake_adc;
SYSCFG_TypeDef fake_syscfg;
uint8_t fake_factory[3]={0,0x6f,0x06};
uint32_t fake_ldo,fake_ldo_ready,fake_calibrating,fake_ready,fake_eoc,fake_overrun;
uint32_t fake_init,fake_cal_starts,fake_enables,fake_starts,fake_reset,fake_clock,fake_channel,fake_external;
uint16_t fake_data;
uint32_t fake_enabled;
static comp_wba_power_profile_t qualified(void)
{
    comp_wba_power_profile_t p={.top_ohm=150000,.bottom_ohm=68000,.reference_mv=1800,
        .reference_min_mv=1700,.maximum_battery_mv=4350,.minimum_battery_mv=2800,
        .minimum_update_mv=3600,.adc_full_scale=4095,.divider_verified=true,.reference_verified=true};
    return p;
}
static comp_wba_adc_result_t drive(uint32_t now)
{
    fake_ldo_ready=1;fake_calibrating=0;fake_ready=1;fake_eoc=1;
    fake_data=fake_channel==ADC_CHANNEL_4?2800u:2757u;
    return comp_v11_battery_adc_read(&fake_data,now);
}
static int adc_journey(void)
{
    comp_wba_power_profile_t p=qualified();uint16_t raw=0;
    fake_syscfg.CFGR1=SYSCFG_CFGR1_ANASWVDD;
    CHECK(comp_v11_battery_adc_begin(&p,false,0));
    CHECK(fake_clock && !fake_init && !fake_cal_starts);
    CHECK(comp_v11_battery_adc_read(&raw,1)==COMP_WBA_ADC_PENDING && !fake_init);
    fake_ldo_ready=1;
    CHECK(comp_v11_battery_adc_read(&raw,2)==COMP_WBA_ADC_PENDING && fake_cal_starts==1);
    CHECK(comp_v11_battery_adc_read(&raw,3)==COMP_WBA_ADC_PENDING && !fake_enables);
    fake_calibrating=0;
    CHECK(comp_v11_battery_adc_read(&raw,4)==COMP_WBA_ADC_PENDING && fake_channel==ADC_CHANNEL_VREFINT);
    CHECK(comp_v11_battery_adc_read(&raw,5)==COMP_WBA_ADC_PENDING && !fake_enables);
    CHECK(comp_v11_battery_adc_read(&raw,6)==COMP_WBA_ADC_PENDING && fake_enables==1);
    CHECK(comp_v11_battery_adc_read(&raw,7)==COMP_WBA_ADC_PENDING && !fake_starts);
    fake_ready=1;
    CHECK(comp_v11_battery_adc_read(&raw,8)==COMP_WBA_ADC_PENDING && fake_starts==1);
    CHECK(comp_v11_battery_adc_read(&raw,9)==COMP_WBA_ADC_PENDING);
    for(uint32_t i=0;i<4;i++) {
        fake_eoc=1;fake_data=2757;
        CHECK(comp_v11_battery_adc_read(&raw,10+i)==(i==3?COMP_WBA_ADC_READY:COMP_WBA_ADC_PENDING));
    }
    CHECK(!comp_v11_battery_adc_busy() && !fake_clock && raw==2757);
    CHECK(comp_v11_battery_adc_stats()->reference_valid && comp_v11_battery_adc_stats()->reference_mv==1792);
    CHECK(fake_syscfg.CFGR1==SYSCFG_CFGR1_ANASWVDD && !fake_external);
    uint32_t resets=fake_reset;comp_v11_battery_adc_cancel();CHECK(fake_reset==resets);
    CHECK(comp_v11_battery_adc_begin(&p,true,20));
    comp_wba_adc_result_t result=COMP_WBA_ADC_PENDING;
    for(uint32_t now=21;now<60 && result==COMP_WBA_ADC_PENDING;now++)result=drive(now);
    CHECK(result==COMP_WBA_ADC_READY && fake_external==1 && !fake_clock);
    CHECK(comp_v11_battery_adc_stats()->battery_raw==2800 && comp_v11_battery_adc_stats()->battery_input_valid);
    comp_wba_power_profile_t nominal=p;nominal.top_ohm=100000;nominal.divider_verified=false;nominal.reference_verified=false;
    CHECK(!comp_wba_power_profile_safe(&nominal) && comp_v11_battery_adc_begin_raw(&nominal,40));
    result=COMP_WBA_ADC_PENDING;
    for(uint32_t now=41;now<65 && result==COMP_WBA_ADC_PENDING;now++)result=drive(now);
    CHECK(result==COMP_WBA_ADC_READY && fake_external==2 && !nominal.divider_verified && !nominal.reference_verified);
    /* A successful internal reference makes the previous ADC operation
     * internal. A rejected external request must still invalidate the old
     * external reading, not use the previous operation's ownership. */
    CHECK(comp_v11_battery_adc_stats()->battery_input_valid);
    CHECK(comp_v11_battery_adc_begin(&p,false,66));
    result=COMP_WBA_ADC_PENDING;
    for(uint32_t now=67;now<90 && result==COMP_WBA_ADC_PENDING;now++)result=drive(now);
    CHECK(result==COMP_WBA_ADC_READY && comp_v11_battery_adc_stats()->battery_input_valid);
    p.divider_verified=false;uint32_t before=fake_external;
    CHECK(!comp_v11_battery_adc_begin(&p,true,90) && fake_external==before && !fake_clock);
    CHECK(!comp_v11_battery_adc_stats()->battery_input_valid);
    CHECK(comp_v11_battery_adc_cell_estimate(90)==0u);
    /* Timeout at enable wait with a ready flag after a long service gap.
     * The bound still rejects the sample; the captured evidence is retained. */
    CHECK(comp_v11_battery_adc_begin(&p,false,1000));
    fake_ldo_ready=1;CHECK(comp_v11_battery_adc_read(&raw,1001)==COMP_WBA_ADC_PENDING);
    fake_calibrating=0;CHECK(comp_v11_battery_adc_read(&raw,1002)==COMP_WBA_ADC_PENDING);
    CHECK(comp_v11_battery_adc_read(&raw,1004)==COMP_WBA_ADC_PENDING);
    fake_ready=1;CHECK(comp_v11_battery_adc_read(&raw,1250)==COMP_WBA_ADC_ERROR);
    const comp_v11_battery_adc_stats_t *timeout=comp_v11_battery_adc_stats();
    CHECK(timeout->timeout_valid && timeout->timeout_at_ms==1250 && timeout->timeout_elapsed_ms==250);
    CHECK(timeout->timeout_service_gap_ms==246 && timeout->timeout_phase==4 && timeout->timeout_ready==2);
    CHECK(!fake_clock && !comp_v11_battery_adc_busy());
    CHECK(comp_v11_battery_adc_begin(&p,false,100));
    fake_ldo_ready=0;
    CHECK(comp_v11_battery_adc_read(&raw,349)==COMP_WBA_ADC_PENDING);
    CHECK(comp_v11_battery_adc_read(&raw,350)==COMP_WBA_ADC_ERROR && !fake_clock && !comp_v11_battery_adc_busy());
    CHECK(timeout->timeout_at_ms==1250 && timeout->timeout_phase==4 && timeout->timeout_ready==2);
    CHECK(comp_v11_battery_adc_begin(&p,false,UINT32_MAX-100u));
    fake_ldo_ready=1;CHECK(comp_v11_battery_adc_read(&raw,UINT32_MAX-99u)==COMP_WBA_ADC_PENDING);
    fake_calibrating=1;CHECK(comp_v11_battery_adc_read(&raw,100)==COMP_WBA_ADC_PENDING);
    CHECK(comp_v11_battery_adc_read(&raw,149)==COMP_WBA_ADC_ERROR && !fake_clock);
    before=fake_external;CHECK(!comp_v11_battery_adc_begin_raw(&nominal,160) && fake_external==before);
    CHECK(comp_v11_battery_adc_begin(&p,false,300));
    uint32_t starts=fake_starts,now=301;
    while(fake_starts==starts && now<330){CHECK(drive(now)==COMP_WBA_ADC_PENDING);now++;}
    fake_overrun=1;CHECK(comp_v11_battery_adc_read(&raw,now)==COMP_WBA_ADC_ERROR && !fake_clock);
    puts("PASS ADC production state machine: LDO/calibration/enable each yield, four references then external, timeout/wrap/cancel release only owned ADC, unqualified external rejected");
    return 0;
}
typedef struct {unsigned gates,starts,cancels;bool gate_on,gate_fail,capturing,raw_set;uint16_t raw;comp_wba_adc_result_t result;} ports_t;
static bool gate(void *c,bool on){ports_t *p=c;if(p->capturing){puts("unexpected I2C gate during capture");return false;}p->gates++;p->gate_on=on;return !p->gate_fail;}
static bool start(void *c){((ports_t*)c)->starts++;return true;}
static comp_wba_adc_result_t read_adc(void *c,uint16_t *raw){ports_t *p=c;*raw=p->raw_set?p->raw:(p->raw?p->raw:2800);return p->result;}
static void cancel(void *c){((ports_t*)c)->cancels++;}
static int capture_lease(void)
{
    comp_wba_power_profile_t p=qualified();comp_wba_power_monitor_t m;ports_t f={.result=COMP_WBA_ADC_PENDING};
    comp_wba_power_ports_t ports={gate,start,read_adc,cancel,&f};
    comp_wba_power_monitor_init(&m,&p,&ports,0);
    CHECK(comp_wba_power_monitor_prepare_capture(&m,1) && m.capture_gate && f.gate_on);
    f.capturing=true;unsigned gates=f.gates,cancels=f.cancels;
    CHECK(comp_wba_power_monitor_prepare_capture(&m,2) && f.gates==gates && f.cancels==cancels);
    comp_wba_power_monitor_poll(&m,true,2);comp_wba_power_monitor_poll(&m,true,4);
    CHECK(m.phase==COMP_WBA_BAT_CONVERT && f.starts==1 && f.gates==gates);
    CHECK(comp_wba_power_poll_action(false,true,false,0)==COMP_WBA_POWER_DEFER);
    CHECK(comp_wba_power_poll_action(false,true,true,2)==COMP_WBA_POWER_DEFER);
    CHECK(comp_wba_power_poll_action(false,true,true,1)==COMP_WBA_POWER_SERVICE);
    CHECK(comp_wba_power_poll_action(true,true,true,0)==COMP_WBA_POWER_CANCEL);
    comp_wba_power_monitor_poll(&m,true,100);CHECK(m.phase==COMP_WBA_BAT_CONVERT && f.cancels==cancels);
    f.result=COMP_WBA_ADC_READY;comp_wba_power_monitor_poll(&m,true,101);comp_wba_power_monitor_poll(&m,true,102);
    CHECK(m.value.voltage_valid && f.gates==gates && m.capture_gate && comp_wba_power_monitor_busy(&m));
    f.capturing=false;f.gate_fail=true;comp_wba_power_monitor_release_capture(&m,103);
    CHECK(!m.capture_gate && m.gate_may_be_on && comp_wba_power_monitor_busy(&m));
    f.gate_fail=false;comp_wba_power_monitor_poll(&m,false,104);CHECK(!f.gate_on && !comp_wba_power_monitor_busy(&m));
    p.divider_verified=false;comp_wba_power_monitor_init(&m,&p,&ports,200);
    CHECK(comp_wba_power_monitor_prepare_capture(&m,201) && !m.capture_gate && !f.gate_on);
    CHECK(!comp_wba_power_monitor_snapshot(&m,201).voltage_valid);
    memset(&m,0,sizeof(m));CHECK(comp_wba_power_monitor_prepare_capture(&m,0));
    puts("PASS capture power ownership: qualified gate acquired before mic, no sample I2C writes during capture, missed audio slots defer, stop-off failure remains busy, unqualified voltage stays unknown");
    return 0;
}
static int current_fault_recovery(void)
{
    comp_v11_battery_adc_stats_t a={0}; comp_wba_power_monitor_t m={0};
    bool fault=false;
    a.failures=1; a.error=COMP_V11_ADC_TIMEOUT;
    fault=comp_v11_battery_active_fault(fault,&a,&m,false); CHECK(fault);
    a.error=COMP_V11_ADC_OK; /* begin is not completion */
    CHECK(comp_v11_battery_active_fault(fault,&a,&m,true));
    CHECK(comp_v11_battery_active_fault(fault,&a,&m,false));
    a.reference_measurements=1; a.reference_valid=true; a.reference_ms=100;
    CHECK(!comp_v11_battery_active_fault(fault,&a,&m,false));
    CHECK(a.failures==1); /* never erase the historical failure */
    CHECK(!comp_v11_battery_active_fault(false,&a,&m,true));
    m.sampling_enabled=true; m.raw_diagnostic=true;
    a.battery_measurements=1; a.battery_input_valid=true; a.battery_ms=99;
    CHECK(comp_v11_battery_active_fault(fault,&a,&m,false));
    a.battery_ms=101; CHECK(!comp_v11_battery_active_fault(fault,&a,&m,false));
    a.battery_input_valid=false; CHECK(comp_v11_battery_active_fault(fault,&a,&m,false));
    a.battery_input_valid=true; m.gate_may_be_on=true;
    CHECK(comp_v11_battery_active_fault(fault,&a,&m,false));
    m.gate_may_be_on=false; m.gate_errors=1; m.gate_fault=true;
    CHECK(comp_v11_battery_active_fault(fault,&a,&m,false));
    m.gate_errors=0; m.gate_fault=false; m.sample_errors=1; m.sample_fault=true;
    CHECK(comp_v11_battery_active_fault(fault,&a,&m,false));
    m.sample_fault=false; m.sample_errors=0; m.raw_diagnostic=false; m.value.voltage_valid=false;
    CHECK(comp_v11_battery_active_fault(fault,&a,&m,false));
    m.value.voltage_valid=true; CHECK(!comp_v11_battery_active_fault(fault,&a,&m,false));
    m.sampling_enabled=false; m.profile.divider_verified=true;
    CHECK(comp_v11_battery_active_fault(fault,&a,&m,false));
    m.profile.divider_verified=false; a.reference_valid=false;
    CHECK(comp_v11_battery_active_fault(fault,&a,&m,false));
    a.reference_valid=true; a.failures=0;
    CHECK(comp_v11_battery_active_fault(fault,&a,&m,false));
    puts("PASS active ADC fault clears only after matching recovery; historical, external and gate evidence retained");
    return 0;
}
static int sample_fault_recovers(void)
{
    comp_wba_power_profile_t p=qualified();comp_wba_power_monitor_t m;
    ports_t f={.result=COMP_WBA_ADC_ERROR};
    comp_wba_power_ports_t ports={gate,start,read_adc,cancel,&f};
    comp_v11_battery_adc_stats_t a={0};
    comp_wba_power_monitor_init(&m,&p,&ports,0);
    comp_wba_power_monitor_poll(&m,true,0);
    comp_wba_power_monitor_poll(&m,true,2);
    comp_wba_power_monitor_poll(&m,true,3);
    CHECK(m.sample_errors==1 && m.sample_fault && m.phase==COMP_WBA_BAT_CLEANUP);
    bool active=comp_v11_battery_active_fault(false,&a,&m,false);
    CHECK(active);
    comp_wba_power_monitor_poll(&m,true,4);
    f.result=COMP_WBA_ADC_READY;
    comp_wba_power_monitor_poll(&m,true,5004);
    comp_wba_power_monitor_poll(&m,true,5006);
    CHECK(m.sample_fault && comp_v11_battery_active_fault(active,&a,&m,true));
    comp_wba_power_monitor_poll(&m,true,5007);
    comp_wba_power_monitor_poll(&m,true,5008);
    a.reference_valid=true; a.reference_measurements=1; a.reference_ms=5006;
    a.battery_input_valid=true; a.battery_measurements=1; a.battery_ms=5007;
    CHECK(m.value.voltage_valid && m.sample_errors==1 && !m.gate_may_be_on);
    CHECK(!comp_v11_battery_active_fault(active,&a,&m,false));
    /* Engineering samples cannot regain health from a saturated conversion,
     * and must never grant production voltage. */
    m.raw_diagnostic=true; m.value.voltage_valid=false; f.raw=4095;
    comp_wba_power_monitor_poll(&m,true,10008);
    comp_wba_power_monitor_poll(&m,true,10010);
    comp_wba_power_monitor_poll(&m,true,10011);
    CHECK(m.sample_fault && !m.value.voltage_valid);
    comp_wba_power_monitor_poll(&m,true,10012);
    f.raw=2800;
    comp_wba_power_monitor_poll(&m,true,15012);
    comp_wba_power_monitor_poll(&m,true,15014);
    comp_wba_power_monitor_poll(&m,true,15015);
    CHECK(!m.sample_fault && !m.value.voltage_valid && m.sample_errors==2);
    puts("PASS external sample fault recovers only on a valid subsequent sample; counts and unknown production voltage retained");
    return 0;
}
static int gate_fault_recovers(void)
{
    comp_wba_power_profile_t p=qualified();comp_wba_power_monitor_t m;
    ports_t f={.result=COMP_WBA_ADC_READY};
    comp_wba_power_ports_t ports={gate,start,read_adc,cancel,&f};
    comp_v11_battery_adc_stats_t a={0};
    comp_wba_power_monitor_init(&m,&p,&ports,0);
    f.gate_fail=true;comp_wba_power_monitor_poll(&m,true,0);
    CHECK(m.gate_errors==1 && m.gate_may_be_on && m.phase==COMP_WBA_BAT_CLEANUP);
    bool active=comp_v11_battery_active_fault(false,&a,&m,false); CHECK(active);
    f.gate_fail=false;comp_wba_power_monitor_poll(&m,true,1);
    CHECK(!m.gate_may_be_on && comp_v11_battery_active_fault(active,&a,&m,false));
    /* A saturated engineering read is not a successful gate cycle. */
    m.raw_diagnostic=true;f.raw=4095;
    comp_wba_power_monitor_poll(&m,true,5001);
    comp_wba_power_monitor_poll(&m,true,5003);
    comp_wba_power_monitor_poll(&m,true,5004);
    comp_wba_power_monitor_poll(&m,true,5005);
    CHECK(m.gate_fault && m.sample_fault && !m.value.voltage_valid);
    m.raw_diagnostic=false;f.raw=2800;
    comp_wba_power_monitor_poll(&m,true,10005);
    comp_wba_power_monitor_poll(&m,true,10007);
    comp_wba_power_monitor_poll(&m,true,10008);
    a.reference_valid=true;a.reference_measurements=1;a.reference_ms=10007;
    a.battery_input_valid=true;a.battery_measurements=1;a.battery_ms=10008;
    CHECK(comp_v11_battery_active_fault(active,&a,&m,false));
    /* A failed off cannot clear the latch, nor can a later off alone. */
    f.gate_fail=true;comp_wba_power_monitor_poll(&m,true,10009);
    CHECK(m.gate_fault && m.gate_may_be_on);
    f.gate_fail=false;comp_wba_power_monitor_poll(&m,true,10010);
    CHECK(m.gate_fault && !m.gate_may_be_on);
    comp_wba_power_monitor_poll(&m,true,15010);
    comp_wba_power_monitor_poll(&m,true,15012);
    comp_wba_power_monitor_poll(&m,true,15013);
    a.reference_ms=15012;a.battery_ms=15013;
    comp_wba_power_monitor_poll(&m,true,15014);
    CHECK(m.gate_errors==2 && m.value.voltage_valid && !m.gate_may_be_on);
    CHECK(!comp_v11_battery_active_fault(active,&a,&m,false));
    puts("PASS gate current fault clears after a verified on/sample/off cycle; count retained");
    return 0;
}
static int raw_gate_cannot_qualify(void)
{
    comp_wba_power_profile_t p=qualified(); comp_wba_power_monitor_t m;
    ports_t f={.result=COMP_WBA_ADC_READY,.raw=2800};
    comp_wba_power_ports_t ports={gate,start,read_adc,cancel,&f};
    comp_wba_power_monitor_init(&m,&p,&ports,0);
    f.gate_fail=true;comp_wba_power_monitor_poll(&m,true,0);
    f.gate_fail=false;comp_wba_power_monitor_poll(&m,true,1);
    m.raw_diagnostic=true;
    comp_wba_power_monitor_poll(&m,true,5001);
    comp_wba_power_monitor_poll(&m,true,5003);
    comp_wba_power_monitor_poll(&m,true,5004);
    comp_wba_power_monitor_poll(&m,true,5005);
    CHECK(m.gate_fault && !m.sample_fault && !m.value.voltage_valid && m.gate_errors==1);
    puts("PASS unqualified raw does not clear a gate fault or authorize battery voltage");return 0;
}
static int implausible_raw_does_not_claim_recovery(void)
{
    comp_wba_power_profile_t p=qualified();p.top_ohm=100000u;
    p.divider_verified=false;p.reference_verified=false; /* current FW810 engineering profile */
    comp_wba_power_monitor_t m;ports_t f={.result=COMP_WBA_ADC_READY,.raw_set=true,.raw=0};
    comp_wba_power_ports_t ports={gate,start,read_adc,cancel,&f};
    comp_wba_power_monitor_init(&m,&p,&ports,0);CHECK(comp_wba_power_monitor_enable_raw(&m));
    comp_wba_power_monitor_poll(&m,true,0);comp_wba_power_monitor_poll(&m,true,2);
    comp_wba_power_monitor_poll(&m,true,3);
    CHECK(m.sample_fault && !m.value.voltage_valid && !m.value.percent_valid);
    /* Implausible engineering data is a sampling fault, not a measured low
     * battery. The current unqualified build must still permit recording. */
    comp_v11_battery_adc_stats_t adc_state={0};
    CHECK(comp_v11_battery_active_fault(false,&adc_state,&m,false));
    CHECK(comp_wba_power_monitor_recording_allowed(&m,3));
    CHECK(comp_wba_power_monitor_ota_blockers(&m,3)&COMP_WBA_OTA_POWER_UNKNOWN);
    comp_wba_power_monitor_poll(&m,true,4);f.raw=3;
    comp_wba_power_monitor_poll(&m,true,5004);comp_wba_power_monitor_poll(&m,true,5006);
    comp_wba_power_monitor_poll(&m,true,5007);
    CHECK(m.sample_fault && !m.value.voltage_valid && m.sample_errors==2);
    comp_wba_power_monitor_poll(&m,true,5008);f.raw=2800;
    comp_wba_power_monitor_poll(&m,true,10008);comp_wba_power_monitor_poll(&m,true,10010);
    comp_wba_power_monitor_poll(&m,true,10011);
    CHECK(!m.sample_fault && !m.value.voltage_valid && !m.value.percent_valid && m.sample_errors==2);
    puts("PASS implausible raw stays unknown and cannot claim sampling recovery");return 0;
}
int main(void){return adc_journey()||capture_lease()||current_fault_recovery()||sample_fault_recovers()||gate_fault_recovers()||raw_gate_cannot_qualify()||implausible_raw_does_not_claim_recovery();}
