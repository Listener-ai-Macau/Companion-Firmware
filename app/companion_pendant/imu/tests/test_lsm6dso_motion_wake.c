#include "lsm6dso.h"
#include "power_policy.h"
#include "maintenance_protocol.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct {uint8_t reg[256];unsigned wake_reads;bool bad_route;} bus_t;
static bool rd(void *v,uint8_t reg,uint8_t *p,size_t n)
{
    bus_t *b=v;memcpy(p,b->reg+reg,n);
    if(reg==0x1Bu){++b->wake_reads;b->reg[reg]=0u;}
    if(reg==0x5Eu && b->bad_route)*p=0u;
    return true;
}
static bool wr(void *v,uint8_t reg,const uint8_t *p,size_t n)
{bus_t *b=v;memcpy(b->reg+reg,p,n);return true;}
static void ready(comp_lsm6dso_t *imu,bus_t *b)
{
    comp_imu_sample_t s;memset(b,0,sizeof(*b));b->reg[0x0F]=0x6Cu;
    assert(comp_lsm6dso_start(imu,rd,wr,b,0u));b->reg[0x12]=0u;
    assert(comp_lsm6dso_poll(imu,1u,&s)==COMP_IMU_NO_SAMPLE&&imu->state==COMP_IMU_READY);
}
typedef struct {comp_lsm6dso_t imu;} board_t;
typedef struct {uint32_t last_activity_ms,wakes,source;} runtime_t;
typedef struct {board_t *board;runtime_t runtime;uint8_t last_imu_wake_sequence;} comp_v11_product_app_t;
#include "wake_source_enum.inc"
static void comp_runtime_wake_from(runtime_t *r,uint32_t now,comp_runtime_wake_source_t source)
{r->last_activity_ms=now;r->source=source;++r->wakes;}
#include "product_wake_dispatch.inc"
static comp_v11_product_app_t *product;
#include "imu_power_wire.inc"

int main(void)
{
    comp_lsm6dso_t imu;bus_t b;comp_imu_sample_t sample,before;
    ready(&imu,&b);memset(&sample,0xA5,sizeof(sample));before=sample;
    assert(comp_lsm6dso_set_idle(&imu,true,1000u));
    assert(b.reg[0x0D]==0u&&b.reg[0x5E]==0u&&b.reg[0x10]==0x18u&&b.reg[0x11]==0u);
    assert(comp_lsm6dso_idle_settling(&imu));
    b.reg[0x1B]=0x0Fu; /* Model an initial gravity/filter transient. */
    assert(comp_lsm6dso_poll(&imu,1239u,&sample)==COMP_IMU_NO_SAMPLE&&b.wake_reads==0u);
    assert(comp_lsm6dso_poll(&imu,1240u,&sample)==COMP_IMU_NO_SAMPLE);
    assert(!comp_lsm6dso_idle_settling(&imu)&&b.reg[0x5E]==0x20u&&b.reg[0x0D]==0u);
    assert(b.wake_reads==1u&&imu.wake_sequence==0u&&!memcmp(&sample,&before,sizeof(sample)));
    imu.event_irq_pending=true;b.reg[0x1B]=0x0Au;
    assert(comp_lsm6dso_poll(&imu,1250u,&sample)==COMP_IMU_NO_SAMPLE);
    assert(imu.wake_sequence==1u&&imu.reset_ms==1250u&&imu.wake_source==0x8Au);
    assert(imu.samples==0u&&b.wake_reads==2u&&!memcmp(&sample,&before,sizeof(sample)));
    for(unsigned i=0;i<100u;++i)assert(comp_lsm6dso_poll(&imu,1251u+i,&sample)==COMP_IMU_NO_SAMPLE);
    assert(b.wake_reads==2u&&imu.wake_sequence==1u&&imu.reset_ms==1250u);
    puts("PASS real idle driver: no12.5Hz DRDY IRQ, settle then arm motion, consume one source only on physical pending, no fabricated sample or repeated event");

    board_t board={0};board.imu=imu;comp_v11_product_app_t app={0};app.board=&board;product=&app;
    imu_wake_activity(&app,1300u);assert(app.runtime.wakes==1u&&app.runtime.source==COMP_RUNTIME_WAKE_MOTION&&app.runtime.last_activity_ms==1300u);
    imu_wake_activity(&app,1301u);assert(app.runtime.wakes==1u);
    ++board.imu.wake_sequence;imu_wake_activity(&app,1500u);assert(app.runtime.wakes==1u); /* Expired once, not replayed. */
    board.imu.reset_ms=1500u;imu_wake_activity(&app,1501u);assert(app.runtime.wakes==1u);
    app.last_imu_wake_sequence=255u;board.imu.wake_sequence=0u;board.imu.reset_ms=UINT32_MAX-100u;
    imu_wake_activity(&app,50u);assert(app.runtime.wakes==2u&&app.runtime.last_activity_ms==50u);
    ++board.imu.wake_sequence;board.imu.state=COMP_IMU_FAULT;imu_wake_activity(&app,51u);assert(app.runtime.wakes==2u);
    puts("PASS actual product wake dispatch: fresh hardware generation wakes core once, no replay after expiry/fault, tick and generation wrap handled");

    comp_power_policy_t power;comp_power_policy_init(&power);power.blockers=0u;power.button_wake_ready=true;
    comp_power_policy_set_blocker(&power,COMP_POWER_BLOCKER_IMU_SETTLING,true);
    assert(comp_power_policy_idle_requested(&power)&&!comp_power_policy_stop_allowed(&power));
    for(unsigned bit=0;bit<15u;++bit){power.blockers|=1u<<bit;assert(!comp_power_policy_idle_requested(&power)&&!comp_power_policy_stop_allowed(&power));power.blockers&=~(1u<<bit);}
    comp_power_policy_set_blocker(&power,COMP_POWER_BLOCKER_IMU_SETTLING,false);
    assert(comp_power_policy_stop_allowed(&power));
    puts("PASS actual power policy: desired idle survives its own bounded setup, real Stop waits until armed, every other owner remains authoritative");

    assert(comp_lsm6dso_set_idle(&imu,false,1400u));assert(comp_lsm6dso_set_idle(&imu,true,1500u));
    assert(comp_lsm6dso_idle_settling(&imu)&&comp_lsm6dso_set_recording_taps(&imu,true));
    assert(!imu.idle_accel_only&&!comp_lsm6dso_idle_settling(&imu)&&b.reg[0x10]==0x68u&&b.reg[0x5E]==8u&&b.reg[0x0D]==0u);
    b.reg[0x1E]=3u;b.reg[0x1C]=0x50u;b.reg[0x1B]=8u;imu.event_irq_pending=true;
    unsigned wake_reads=b.wake_reads;
    assert(comp_lsm6dso_poll(&imu,1510u,&sample)==COMP_IMU_SAMPLE&&imu.tap_counts==0x10000u&&b.wake_reads==wake_reads);
    assert(comp_lsm6dso_set_recording_taps(&imu,false));
    assert(comp_lsm6dso_set_idle(&imu,true,UINT32_MAX-200u));b.reg[0x1E]=0u;
    assert(comp_lsm6dso_poll(&imu,39u,&sample)==COMP_IMU_NO_SAMPLE&&!comp_lsm6dso_idle_settling(&imu));
    assert(comp_lsm6dso_set_idle(&imu,false,50u)&&comp_lsm6dso_set_idle(&imu,true,2000u));b.bad_route=true;
    assert(comp_lsm6dso_poll(&imu,2240u,&sample)==COMP_IMU_IO_ERROR&&imu.state==COMP_IMU_FAULT&&!comp_lsm6dso_idle_settling(&imu));
    puts("PASS capture transition cancels settling and retains double-tap path; arm failure cannot leave a permanent settling vote");

    board.imu.state=COMP_IMU_READY;board.imu.idle_accel_only=true;board.imu.wake_source=0x89u;board.imu.wake_sequence=7u;
    board.imu.samples=123u;board.imu.errors=2u;board.imu.reset_ms=456u;
    comp_lsm6dso_t saved=board.imu;uint8_t packet[32];
    comp_maint_response(packet,COMP_MAINT_IMU_POWER,COMP_MAINT_OK,0x12345678u,0u,0u,0u,0u,0u,0u);
    maintenance_imu_power_fields(packet);comp_maint_put32(packet+28u,companion_crc32(0u,packet,28u));
    assert(packet[6]==11u&&packet[7]==1u&&comp_maint_get32(packet+12u)==123u&&comp_maint_get32(packet+16u)==2u);
    assert(comp_maint_get32(packet+20u)==0x00028907u&&comp_maint_get32(packet+24u)==456u&&!memcmp(&saved,&board.imu,sizeof(saved)));
    assert(comp_maint_operation_supported(16u)&&comp_maint_operation_supported(17u)&&comp_maint_operation_supported(18u)&&!comp_maint_operation_supported(19u));
    assert(companion_crc32(0u,packet,28u)==comp_maint_get32(packet+28u));
    puts("PASS actual cached power serializer: source-bound device identity remains outer protocol, nonce/schema/CRC consistent, no sensor I/O or clearing, no recording session required");
    puts("SOFTWARE_ONLY: physical motion wake, current draw, enclosure sensitivity and normal audio qualification remain unmeasured");
    return 0;
}
