#include "lsm6dso.h"
#include "motion_events.h"
#include "power_policy.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

/* Only board/peripheral plumbing is modeled. The driver, mode transition,
 * recovery poll and motion classifier below are the actual product code. */
#define COMP_V11_FAULT_IMU 4u
#define COMP_SSD1681_WBA_ACTIVE 1u
typedef struct {
    comp_lsm6dso_t imu;
    comp_motion_events_t motion;
    comp_imu_sample_t imu_sample;
    comp_power_policy_t power;
    struct { bool running; } microphone;
    bool playback_active, power_sampling_inhibited, idle_peripherals,input_taps_requested;
    uint32_t faults, motion_event_ms;
    uint8_t sample_events, motion_event_flags, panel;
} comp_v11_hal_t;
static uint32_t HAL_GetTick(void){return 12u;}
static bool imu_start_pending, bus_held;
static bool panel_holds_shared_bus(comp_v11_hal_t *b) { (void)b; return bus_held; }
static uint8_t comp_ssd1681_wba_status(uint8_t *p) { return *p; }
#include "product_imu_functions.inc"

typedef struct { uint8_t reg[256]; unsigned ops, fail_at, resets; bool wrong_id; } bus_t;
static bool read_bus(void *context, uint8_t reg, uint8_t *out, size_t n)
{
    bus_t *b=context;
    if (++b->ops==b->fail_at) return false;
    memcpy(out,b->reg+reg,n);
    if (reg==0x0f && b->wrong_id) *out=0;
    return true;
}
static bool write_bus(void *context, uint8_t reg, const uint8_t *in, size_t n)
{
    bus_t *b=context;
    if (++b->ops==b->fail_at) return false;
    memcpy(b->reg+reg,in,n);
    if (reg==0x12 && *in==1) ++b->resets;
    return true;
}
static void ready(comp_lsm6dso_t *imu,bus_t *bus)
{
    comp_imu_sample_t sample;
    memset(bus,0,sizeof(*bus)); bus->reg[0x0f]=0x6c;
    assert(comp_lsm6dso_start(imu,read_bus,write_bus,bus,0));
    bus->reg[0x12]=0;
    assert(comp_lsm6dso_poll(imu,1,&sample)==COMP_IMU_NO_SAMPLE);
    assert(imu->state==COMP_IMU_READY);
    bus->reg[0x1e]=3;bus->reg[0x2d]=0x20;
    assert(comp_lsm6dso_poll(imu,2,&sample)==COMP_IMU_SAMPLE);
    assert(imu->samples==1);
    bus->ops=0;
}
static void recover_sample(comp_lsm6dso_t *imu,bus_t *bus,uint32_t at)
{
    comp_imu_sample_t sample;
    unsigned ops=bus->ops,errors=imu->errors,samples=imu->samples;
    assert(!comp_lsm6dso_recover(imu,at));
    assert(!comp_lsm6dso_recover(imu,at+999));assert(bus->ops==ops);
    assert(comp_lsm6dso_recover(imu,at+1000));
    assert(imu->state==COMP_IMU_RESET_WAIT&&imu->recovery_attempts==1);
    assert(imu->errors==errors&&imu->samples==samples&&!imu->idle_accel_only);
    bus->reg[0x12]=0;
    assert(comp_lsm6dso_poll(imu,at+1001,&sample)==COMP_IMU_NO_SAMPLE);
    assert(imu->state==COMP_IMU_READY&&imu->recovery_attempts==1);
    bus->reg[0x1e]=0;
    assert(comp_lsm6dso_poll(imu,at+1002,&sample)==COMP_IMU_NO_SAMPLE);
    assert(imu->recovery_attempts==1);
    bus->reg[0x1e]=3;
    assert(comp_lsm6dso_poll(imu,at+1003,&sample)==COMP_IMU_SAMPLE);
    assert(imu->samples==samples+1&&imu->errors==errors&&!imu->recovery_attempts);
    assert(bus->reg[0x10]==0x38&&bus->reg[0x11]==0x30&&bus->reg[0x12]==0x44);
}
int main(void)
{
    comp_lsm6dso_t imu;bus_t bus;comp_imu_sample_t sample;
    for(unsigned operation=1;operation<=12;++operation) {
        ready(&imu,&bus);bus.fail_at=operation;
        assert(!comp_lsm6dso_set_idle(&imu,true,12u));
        assert(imu.state==COMP_IMU_FAULT&&imu.errors==1);
        bus.fail_at=0;recover_sample(&imu,&bus,UINT32_MAX-500u);
        assert(comp_lsm6dso_set_idle(&imu,true,12u));
        assert(imu.idle_accel_only&&bus.reg[0x10]==0x18&&bus.reg[0x11]==0);
        assert(comp_lsm6dso_set_idle(&imu,false,12u));
    }
    puts("PASS all twelve mode-switch I/O failures recover after delay, preserve history and tick wrap, and restore run/idle registers");

    ready(&imu,&bus);bus.fail_at=1;
    assert(comp_lsm6dso_poll(&imu,4,&sample)==COMP_IMU_IO_ERROR);
    bus.fail_at=0;bus.wrong_id=true;
    for(unsigned attempt=0;attempt<3;++attempt) {
        uint32_t now=100+attempt*1001;
        assert(!comp_lsm6dso_recover(&imu,now));
        assert(!comp_lsm6dso_recover(&imu,now+1000));
        assert(imu.recovery_attempts==attempt+1);
    }
    unsigned ops=bus.ops,resets=bus.resets;
    for(unsigned i=0;i<100;++i) assert(!comp_lsm6dso_recover(&imu,10000+i*1000));
    assert(bus.ops==ops&&bus.resets==resets&&resets==1&&imu.errors==4);
    puts("PASS wrong identity never reset; persistent fault stops bus work after three attempts");

    ready(&imu,&bus);bus.fail_at=1;
    assert(comp_lsm6dso_poll(&imu,4,&sample)==COMP_IMU_IO_ERROR);bus.fail_at=0;
    for(unsigned attempt=0;attempt<3;++attempt) {
        uint32_t now=100+attempt*1201;
        assert(!comp_lsm6dso_recover(&imu,now));
        assert(comp_lsm6dso_recover(&imu,now+1000));
        /* Reset never finishes: do not reset the budget at RESET_WAIT/READY. */
        assert(comp_lsm6dso_poll(&imu,now+1100,&sample)==COMP_IMU_IO_ERROR);
    }
    ops=bus.ops;assert(!comp_lsm6dso_recover(&imu,10000));assert(bus.ops==ops);
    puts("PASS stuck reset cannot create an unlimited reset loop");

    comp_v11_hal_t b={0};ready(&b.imu,&bus);comp_motion_events_init(&b.motion);
    assert(comp_motion_events_set_screen_axes(&b.motion,1,3,5));
    uint8_t axes=b.motion.screen_axes;
    b.motion.initialized=true;b.motion.carried=true;
    b.sample_events=COMP_MOTION_SHAKE;b.motion_event_flags=COMP_MOTION_PICKUP;
    b.idle_peripherals=true;bus.fail_at=1;
    imu_poll_with_recovery(&b,10);assert(b.imu.state==COMP_IMU_FAULT);
    assert(!b.idle_peripherals&&b.faults==COMP_V11_FAULT_IMU&&!b.sample_events&&!b.motion_event_flags);
    bus.fail_at=0;b.idle_peripherals=true;
    assert(!comp_v11_hal_set_idle_peripherals(&b,true));
    const uint32_t blockers[]={COMP_POWER_BLOCKER_MIC_CAPTURE,COMP_POWER_BLOCKER_PLAYBACK,
        COMP_POWER_BLOCKER_STORAGE,COMP_POWER_BLOCKER_UPDATE,
        COMP_POWER_BLOCKER_RECORDING_TRANSFER,COMP_POWER_BLOCKER_BOND_NVM};
    ops=bus.ops;
    for(unsigned i=0;i<sizeof(blockers)/sizeof(blockers[0]);++i) {
        b.power.blockers=blockers[i];imu_poll_with_recovery(&b,100+i*2000);
        assert(bus.ops==ops&&!b.imu.recovery_waiting);
    }
    b.power.blockers=0;b.microphone.running=true;imu_poll_with_recovery(&b,20000);
    b.microphone.running=false;b.playback_active=true;imu_poll_with_recovery(&b,22000);
    b.playback_active=false;b.power_sampling_inhibited=true;imu_poll_with_recovery(&b,24000);
    assert(bus.ops==ops&&!b.imu.recovery_waiting);
    b.power_sampling_inhibited=false;
    imu_poll_with_recovery(&b,25000);imu_poll_with_recovery(&b,26000);
    assert(b.imu.state==COMP_IMU_RESET_WAIT&&b.faults==COMP_V11_FAULT_IMU);
    assert(!b.motion.initialized&&!b.motion.carried&&b.motion.screen_axes==axes);
    ops=bus.ops;b.microphone.running=true;bus.reg[0x12]=0;
    imu_poll_with_recovery(&b,27000);assert(bus.ops==ops&&b.imu.state==COMP_IMU_RESET_WAIT);
    b.microphone.running=false;imu_poll_with_recovery(&b,27001);
    assert(b.imu.state==COMP_IMU_READY&&b.faults==COMP_V11_FAULT_IMU);
    bus.reg[0x1e]=0;imu_poll_with_recovery(&b,27002);assert(b.faults==COMP_V11_FAULT_IMU);
    bus.reg[0x1e]=3;imu_poll_with_recovery(&b,27003);
    assert(!b.faults&&!b.imu.recovery_attempts&&!b.sample_events&&!b.motion_event_flags);
    b.power.button_wake_ready=true;
    assert(comp_v11_hal_set_idle_peripherals(&b,true)&&b.imu.idle_accel_only);
    bus.fail_at=bus.ops+1;
    assert(!comp_v11_hal_set_idle_peripherals(&b,false));
    assert(b.imu.state==COMP_IMU_FAULT&&!b.idle_peripherals);
    bus.fail_at=0;imu_poll_with_recovery(&b,28000);imu_poll_with_recovery(&b,29000);
    bus.reg[0x12]=0;imu_poll_with_recovery(&b,29001);imu_poll_with_recovery(&b,29002);
    assert(comp_v11_hal_set_idle_peripherals(&b,false)&&!b.imu.idle_accel_only);
    puts("PASS actual board recovery defers all busy owners, clears fault only after a real sample, preserves mounting and suppresses stale motion");
    puts("SOFTWARE_ONLY: no physical IMU, current, wake-source or acoustic qualification");
    return 0;
}
