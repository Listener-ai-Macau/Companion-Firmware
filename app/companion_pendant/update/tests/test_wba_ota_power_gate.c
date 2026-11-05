/* Exercise real monitor observations under both compile-time admissions.
 * Reuse only the ADC/GPIO fixture; no hardware or current qualification. */
#define main prior_monitor_suite_main
#include "../../power/tests/test_wba_power_monitor.c"
#undef main
#include "wba_ota_power_gate.h"
static int admission(comp_wba_power_monitor_t *m,uint32_t now,uint16_t expected)
{
    CHECK(comp_wba_power_monitor_ota_blockers(m,now)==expected);
    comp_wba_power_snapshot_t before=comp_wba_power_monitor_snapshot(m,now);
    CHECK(comp_wba_ota_admission_power_blockers(m,now)==
        (COMPANION_WBA_OTA_DEV_IGNORE_POWER?0u:expected));
    CHECK(comp_wba_power_monitor_ota_blockers(m,now)==expected);
    comp_wba_power_snapshot_t after=comp_wba_power_monitor_snapshot(m,now);
    CHECK(before.voltage_valid==after.voltage_valid && before.millivolts==after.millivolts &&
          before.charge_state==after.charge_state && before.percent==after.percent);
    return 0;
}
int main(void)
{
    comp_wba_power_monitor_t m;fixture_t f;comp_wba_power_profile_t p=profile();
    init(&m,&f,&p,0);CHECK(!admission(&m,0,COMP_WBA_OTA_POWER_UNKNOWN));
    f.raw=2200;
    comp_wba_power_monitor_poll(&m,true,0);
    comp_wba_power_monitor_poll(&m,true,2);
    comp_wba_power_monitor_poll(&m,true,3);
    CHECK(!admission(&m,3,COMP_WBA_OTA_POWER_LOW));
    init(&m,&f,&p,0);
    for(uint32_t now=3000;now<=5000;now+=20)
        comp_wba_power_monitor_inputs(&m,true,false,((now-3000)/500)%2!=0,now);
    CHECK(!admission(&m,5000,COMP_WBA_OTA_CHARGER_FAULT));
    printf("OTA_ADMISSION_SOFTWARE_ONLY developer_unrestricted=%u raw_monitor_unchanged=1\n",
        COMPANION_WBA_OTA_DEV_IGNORE_POWER);return 0;
}
