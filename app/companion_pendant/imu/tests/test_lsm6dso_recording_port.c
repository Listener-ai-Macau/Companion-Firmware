/* Real driver + extracted actual microphone-enable port. No microphone hardware. */
#define main driver_taps_test_main
#include "test_lsm6dso_taps.c"
#undef main
#define COMPANION_WBA_DUAL_MIC_PROBE 0
#define COMP_V11_FAULT_SPEAKER_SHUTDOWN 1u
#define COMP_V11_FAULT_BATTERY 2u
#define COMP_V11_FAULT_IMU 4u
#define COMP_V11_FAULT_MICROPHONE 8u
#define COMP_POWER_BLOCKER_MIC_CAPTURE 1u
#define COMP_POWER_BLOCKER_BATTERY_SAMPLE 2u
typedef struct {bool running;} mic_t;
typedef struct {comp_lsm6dso_t imu;mic_t microphone;unsigned faults,power,power_monitor;} comp_v11_hal_t;
static comp_v11_hal_t *active;
static bus_t *active_bus;
static bool battery_ok=true,start_ok=true,panel_held;
static unsigned starts,stops;
static bool panel_holds_shared_bus(const comp_v11_hal_t *b){(void)b;return panel_held;}
static bool battery_capture_prepare(comp_v11_hal_t *b){(void)b;return battery_ok;}
static void battery_capture_release(comp_v11_hal_t *b){(void)b;}
static bool comp_v11_microphone_hal_start(mic_t *mic)
{
    /* The actual product port must finish configuration before the first PDM start. */
    if(active->imu.state==COMP_IMU_READY&&!panel_held)
        assert(active->imu.recording_taps&&active_bus->reg[0x10]==0x68u&&active_bus->reg[0x5E]==8u);
    starts++;mic->running=start_ok;return start_ok;
}
static bool comp_v11_microphone_hal_stop(mic_t *mic)
{if(mic->running&&active->imu.state==COMP_IMU_READY)assert(active->imu.recording_taps);stops++;mic->running=false;return true;}
static void comp_power_policy_set_blocker(unsigned *p,unsigned flag,bool value){(void)p;(void)flag;(void)value;}
static bool comp_wba_power_monitor_busy(unsigned *p){(void)p;return false;}
static bool comp_v11_battery_adc_busy(void){return false;}
#include "imu_microphone_port.inc"
int main(void)
{
    comp_v11_hal_t board={0};bus_t bus;active=&board;active_bus=&bus;
    start(&board.imu,&bus);assert(comp_lsm6dso_set_idle(&board.imu,true,12u));
    assert(comp_v11_hal_microphone_enable(&board,true)&&board.microphone.running&&starts==1u);
    assert(comp_v11_hal_microphone_enable(&board,true)&&starts==1u);
    assert(comp_v11_hal_microphone_enable(&board,false)&&!board.microphone.running&&!board.imu.recording_taps&&bus.reg[0x10]==0x38u&&bus.reg[0x5E]==0u);
    assert(comp_lsm6dso_set_idle(&board.imu,true,12u)&&bus.reg[0x10]==0x18u&&bus.reg[0x11]==0u);
    start(&board.imu,&bus);start_ok=false;
    assert(!comp_v11_hal_microphone_enable(&board,true)&&!board.imu.recording_taps&&bus.reg[0x10]==0x38u&&bus.reg[0x5E]==0u);
    start_ok=true;start(&board.imu,&bus);battery_ok=false;unsigned count=starts;
    assert(!comp_v11_hal_microphone_enable(&board,true)&&starts==count&&!board.imu.recording_taps);
    battery_ok=true;start(&board.imu,&bus);bus.fail_write=0x10;
    assert(comp_v11_hal_microphone_enable(&board,true)&&board.microphone.running&&(board.faults&COMP_V11_FAULT_IMU));
    assert(comp_v11_hal_microphone_enable(&board,false));
    board.imu.state=COMP_IMU_OFF;
    assert(comp_v11_hal_microphone_enable(&board,true)&&board.microphone.running);
    assert(comp_v11_hal_microphone_enable(&board,false));
    puts("PASS real microphone port: configure417Hz before PDM START, restore52/12.5Hz after STOP or failed start, battery refusal unchanged, unavailable/faulted optional IMU does not refuse recording");
    return 0;
}
