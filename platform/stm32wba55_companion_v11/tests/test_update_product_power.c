#include "update_product.h"
#include "update_storage.h"
#include "wba_ota_gatt.h"
#include "diag_log.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"FAIL OTA power line=%d: %s\n",__LINE__,#x); return 1; } } while (0)
uint8_t _sidata,_sdata,_edata;
static uint32_t tick,opens,writes,controls,polls,confirms,resets,diag_count;
static uint16_t last_diag_code;
static uint32_t interrupted_events;
static bool idle_board=true;
static comp_v11_update_storage_t *store;
static comp_v11_ota_gatt_ports_t gatt;
uint32_t HAL_GetTick(void) { return tick; }
void NVIC_SystemReset(void) { ++resets; }
void comp_diag_log_record_code(uint16_t code,uint8_t severity,uint32_t a0,uint32_t a1,uint32_t a2,uint32_t a3)
{
    (void)severity;(void)a0;(void)a1;(void)a2;(void)a3;
    ++diag_count;last_diag_code=code;
    if(code==COMP_DIAG_EVT_OTA_INTERRUPTED_TRANSFER)++interrupted_events;
}
bool comp_v11_ble_pka_try_acquire(void) { return true; }
void comp_v11_ble_pka_release(void) {}
bool comp_v11_ble_can_update(void) { return idle_board; }
bool comp_v11_ble_host_ready(void) { return true; }
bool comp_v11_ota_gatt_init(const comp_v11_ota_gatt_ports_t *ports) { gatt=*ports; return true; }
void comp_v11_ota_gatt_poll(void) {}
bool comp_v11_update_storage_init(comp_v11_update_storage_t *s,const comp_v11_update_storage_config_t *c)
{ memset(s,0,sizeof(*s)); s->config=*c; s->ready=true; store=s; return true; }
bool comp_v11_update_storage_open_wire(comp_v11_update_storage_t *s,const uint8_t *p,size_t n)
{ (void)s;(void)p;(void)n; ++opens; return true; }
bool comp_v11_update_storage_data(comp_v11_update_storage_t *s,const uint8_t *p,size_t n)
{ (void)s;(void)p;(void)n; ++writes; return true; }
bool comp_v11_update_storage_control(comp_v11_update_storage_t *s,const uint8_t *p,size_t n)
{ (void)s;(void)p;(void)n; ++controls; return true; }
size_t comp_v11_update_storage_transfer_status(const comp_v11_update_storage_t *s,uint8_t *p,size_t n)
{ (void)s;(void)p;(void)n; return 0; }
bool comp_v11_update_storage_poll(comp_v11_update_storage_t *s,uint8_t *p,size_t n)
{
    (void)p;(void)n;
    if (s->config.activity_idle(s->config.context)) ++polls;
    /* Matches the actual storage module's independent confirm hash path.
     * Real readback/hash/metadata validation remains in its own host test. */
    if (s->confirm_pending) { ++confirms; s->confirm_pending=false; }
    return true;
}
bool comp_v11_update_storage_request_confirm(comp_v11_update_storage_t *s,uint32_t v)
{ (void)v; s->confirm_pending=true; return true; }
void comp_wba_update_abort(comp_wba_update_service_t *s) { s->state=COMP_WBA_UPDATE_IDLE; }
size_t denzic_ota_v1_encode_status(const denzic_ota_v1_context_t *s,uint8_t *p,size_t n)
{ (void)s;(void)p;(void)n; return 0; }
static void measured(comp_wba_power_monitor_t *m,uint16_t mv,uint8_t percent)
{
    m->sampling_enabled=true; m->voltage_ms=tick;
    m->profile.minimum_update_mv=3600u;
    m->value=(comp_wba_power_snapshot_t){.millivolts=mv,.percent=percent,
        .voltage_valid=true,.percent_valid=percent<=100u};
}
int main(void)
{
    comp_v11_hal_t board={0};
    comp_v11_product_app_t app={.board=&board,.storage_layout_ready=true,.recording_ready=true};
    companion_gatt_ota_readiness_v1_t status;
    const uint8_t packet[]={1};
    CHECK(comp_v11_update_product_init(&app));
    comp_v11_update_product_readiness(&status);
    CHECK(status.schema_version==1u && status.ready_state==0u && status.battery_percent==255u &&
        (status.blocker_bitmap & COMP_WBA_OTA_POWER_UNKNOWN));
    CHECK(!gatt.manifest(NULL,packet,1) && !gatt.data(NULL,packet,1) && opens==0 && writes==0);
    CHECK(gatt.control(NULL,packet,1) && controls==1); /* abort/status remains available */
    measured(&board.power_monitor,3500,20);
    comp_v11_update_product_readiness(&status);
    CHECK(status.ready_state==0u && status.minimum_required_mv==3600u && status.battery_percent==20u &&
        (status.blocker_bitmap & COMP_WBA_OTA_POWER_LOW));
    CHECK(!gatt.manifest(NULL,packet,1) && !gatt.data(NULL,packet,1));
    measured(&board.power_monitor,3800,55);
    comp_v11_update_product_readiness(&status);
    CHECK(status.ready_state==1u && status.blocker_bitmap==0u);
    CHECK(gatt.manifest(NULL,packet,1) && gatt.data(NULL,packet,1) && opens==1 && writes==1);
    comp_v11_update_product_poll();
    CHECK(diag_count>0u);
    idle_board=false;
    comp_v11_update_product_readiness(&status);
    CHECK((status.blocker_bitmap & 2u) && !gatt.manifest(NULL,packet,1) && !gatt.data(NULL,packet,1));
    idle_board=true; tick=16000;
    CHECK(!gatt.data(NULL,packet,1)); /* old measurement cannot authorize a flash write */
    comp_wba_power_profile_t profile={.charger_pullups_verified=true,.minimum_update_mv=3600u};
    comp_wba_power_monitor_init(&board.power_monitor,&profile,NULL,tick);
    for (uint32_t i=0;i<=2020;i+=20)
        comp_wba_power_monitor_inputs(&board.power_monitor,true,false,true,tick+i);
    tick+=2020;
    CHECK(gatt.manifest(NULL,packet,1)); /* qualified external input, not guessed full charge */
    for (uint32_t i=20;i<=2020;i+=20)
        comp_wba_power_monitor_inputs(&board.power_monitor,true,false,((i/500)%2)!=0,tick+i);
    tick+=2020;
    comp_v11_update_product_readiness(&status);
    CHECK((status.blocker_bitmap & COMP_WBA_OTA_CHARGER_FAULT) && !gatt.data(NULL,packet,1));
    store->service.state=COMP_WBA_UPDATE_COMPLETE;
    comp_v11_update_product_poll(); tick+=6000; comp_v11_update_product_poll();
    CHECK(resets==0u); /* completed data waits for power before reboot/install */
    measured(&board.power_monitor,3800,55);
    comp_v11_update_product_poll(); CHECK(resets==1u);
    store->service.state=COMP_WBA_UPDATE_IDLE;
    board.power_monitor.sampling_enabled=false;
    store->installer.loaded=true; store->installer.record.phase=COMP_WBA_BOOT_AWAIT_CONFIRM;
    store->installer.record.candidate.target=COMP_WBA_UPDATE_TARGET_FIRMWARE;
    store->installer.record.candidate.component_version=COMPANION_WBA_APP_VERSION;
    uint32_t prior_polls=polls;
    comp_v11_update_product_poll();
    CHECK(confirms==1u && polls==prior_polls); /* unknown battery does not undo a valid running image */
    store->installer.loaded=false;store->service.state=COMP_WBA_UPDATE_RECEIVING;
    store->service.received_bytes=240u;tick+=120001u;
    comp_v11_update_product_poll();
    CHECK(interrupted_events==1u && store->service.state==COMP_WBA_UPDATE_IDLE &&
        last_diag_code==COMP_DIAG_EVT_OTA_INTERRUPTED_TRANSFER);
    puts("PASS_HOST_ONLY: actual update_product callbacks reject unknown/low/stale/fault/busy power, qualify PG input, defer complete reboot, and preserve running-image confirmation; storage/radio are mocked");
    return 0;
}
