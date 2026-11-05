#include "companion_v11_board.h"
#include "lsm6dso.h"
#include "motion_events.h"
#include "companion_v11_services.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    uint8_t regs[256], writes[64], values[64];
    unsigned count;
    bool fail, corrupt, partial;
} device_t;
static bool rd(void *p, uint8_t reg, uint8_t *data, size_t n)
{
    device_t *d = p;
    if (d->fail) { return false; }
    memcpy(data, d->regs + reg, n);
    if (d->partial && n > 1u) { data[0] = 0xFF; return false; }
    if (d->corrupt) { data[0] ^= 1u; }
    return true;
}
static bool wr(void *p, uint8_t reg, const uint8_t *data, size_t n)
{
    device_t *d = p;
    if (d->fail) { return false; }
    assert(d->count < 64u);
    d->writes[d->count] = reg; d->values[d->count++] = *data;
    memcpy(d->regs + reg, data, n); return true;
}
static bool iord(void *p, uint8_t addr, uint8_t reg, uint8_t *v)
{ assert(addr == 0x20u); return rd(p, reg, v, 1u); }
static bool iowr(void *p, uint8_t addr, uint8_t reg, uint8_t v)
{ assert(addr == 0x20u); return wr(p, reg, &v, 1u); }
static bool gate_rd(void *p, uint8_t addr, uint8_t reg, uint8_t *v)
{
    device_t *d=p;
    if(!iord(p,addr,reg,v))return false;
    if(reg==0u) {
        *v=(uint8_t)((d->regs[0]&d->regs[3])|(d->regs[1]&~d->regs[3]));
        if(d->partial)*v&=0x7Fu;
    }
    return true;
}
static void test_battery_gate(void)
{
    device_t d={0};comp_tca6408_t io;uint8_t observation;
    assert(comp_tca6408_init(&io,gate_rd,iowr,&d,0x20,COMP_V11_TCA_INPUTS,0x52));
    /* A stale shadow must not turn enable into a cached no-op. */
    io.outputs|=COMP_V11_BATTERY_ENABLE;
    d.count=0;
    assert(comp_v11_battery_enable(&io,true,&observation));
    assert(d.count==1u&&d.writes[0]==1u&&d.regs[1]==0xD2u&&observation==0x0Bu);
    assert(comp_v11_battery_enable(&io,false,&observation));
    assert(d.regs[1]==0x52u&&observation==8u);
    /* Recover P7's input direction, with the latch written first. */
    d.regs[3]|=COMP_V11_BATTERY_ENABLE;d.count=0;
    assert(comp_v11_battery_enable(&io,true,&observation));
    assert(d.count==2u&&d.writes[0]==1u&&d.writes[1]==3u);
    assert(d.regs[3]==COMP_V11_TCA_INPUTS&&d.regs[1]==0xD2u);
    assert(comp_v11_battery_enable(&io,false,&observation));
    /* A bus success is insufficient if the physical gate stays low. */
    d.partial=true;
    assert(!comp_v11_battery_enable(&io,true,&observation)&&!io.ready);
    assert(observation==9u);
    d.partial=false;
    assert(comp_tca6408_init(&io,gate_rd,iowr,&d,0x20,COMP_V11_TCA_INPUTS,0x52));
    d.fail=true;
    assert(!comp_v11_battery_enable(&io,true,&observation)&&!io.ready);
}
static void test_io_power(void)
{
    device_t d = {0}; comp_tca6408_t io; comp_v11_power_t power;
    uint8_t inputs = 0xFF;
    assert(comp_tca6408_init(&io, iord, iowr, &d, 0x20, COMP_V11_TCA_INPUTS, 0));
    assert(d.writes[0] == 1 && d.values[0] == 0 && d.writes[2] == 3 && d.values[2] == 0x2D);
    assert(!comp_tca6408_update(&io, COMP_V11_TP_INT, 1));
    assert(comp_tca6408_update(&io, COMP_V11_AMP_ENABLE, COMP_V11_AMP_ENABLE));
    comp_v11_power_init(&power, &io);
    assert(comp_v11_power_request(&power, true, UINT32_MAX - 10u));
    assert(io.outputs == 0x50);
    comp_v11_power_poll(&power, 8u); assert(power.state == COMP_V11_POWER_SETTLE);
    comp_v11_power_poll(&power, 9u); assert(io.outputs == 0x52);
    comp_v11_power_poll(&power, 208u); assert(power.state == COMP_V11_TOUCH_RESET_WAIT);
    comp_v11_power_poll(&power, 209u); assert(power.state == COMP_V11_POWER_READY);
    assert(comp_v11_power_request(&power, false, 210u)); assert(io.outputs == 0x40);
    d.regs[0] = 0xFF; assert(comp_tca6408_sample(&io, &inputs) && inputs == 0x2D);
    d.fail = true; inputs = 0xAA;
    assert(!comp_tca6408_sample(&io, &inputs) && inputs == 0xAA);
    assert(!comp_tca6408_update(&io, 0x40, 0) && !io.ready);
    assert(!comp_tca6408_update(&io, 0x10, 0x10));
    d.fail = false; d.corrupt = true;
    assert(!comp_tca6408_init(&io, iord, iowr, &d, 0x20, 0x2D, 0));
}
static void test_always_on_display_rail(void)
{
    device_t d = {0}; comp_tca6408_t io; comp_v11_power_t power;
    /* Keep an unrelated amp output and the P4 latch intact. */
    assert(comp_tca6408_init(&io, iord, iowr, &d, 0x20, COMP_V11_TCA_INPUTS, 0x50));
    comp_v11_power_init_always_on(&power, &io);
    assert(comp_v11_power_request(&power, true, 0u));
    assert(io.outputs == 0x50);
    comp_v11_power_poll(&power, 20u);
    assert(io.outputs == 0x52);
    comp_v11_power_poll(&power, 220u);
    assert(power.state == COMP_V11_POWER_READY && !power.switched);
    unsigned writes = d.count;
    assert(!comp_v11_power_request(&power, false, 221u));
    assert(d.count == writes && io.outputs == 0x52 && power.state == COMP_V11_POWER_READY);
}

static void test_battery(void)
{
    uint16_t mv = 999;
    assert(!comp_v11_battery_divider_safe(68000, 68000, 1800, 4200));
    assert(!comp_v11_battery_mv(3000, 4095, 1800, 68000, 68000, &mv) && mv == 999);
    assert(comp_v11_battery_divider_safe(150000, 68000, 1800, 4350));
    assert(comp_v11_battery_mv(2904, 4095, 1800, 150000, 68000, &mv));
    assert(mv > 4080 && mv < 4100);
    assert(!comp_v11_battery_mv(4094, 4095, 1800, 150000, 68000, &mv));
    assert(!comp_v11_battery_divider_safe(0, 68000, 1800, 4350));
}
static void put16(device_t *d, uint8_t reg, int16_t value)
{ d->regs[reg] = (uint8_t)value; d->regs[reg + 1u] = (uint8_t)((uint16_t)value >> 8); }
static void test_imu(void)
{
    device_t d = {0}; comp_lsm6dso_t imu; comp_imu_sample_t sample = {0}, previous;
    d.regs[0x0F] = 0x6C;
    assert(comp_lsm6dso_start(&imu, rd, wr, &d, UINT32_MAX - 20u));
    assert(comp_lsm6dso_poll(&imu, 1, &sample) == COMP_IMU_NO_SAMPLE);
    d.regs[0x12] = 0;
    assert(comp_lsm6dso_poll(&imu, 2, &sample) == COMP_IMU_NO_SAMPLE && imu.state == COMP_IMU_READY);
    d.regs[0x1E] = 1;
    assert(comp_lsm6dso_poll(&imu, 22, &sample) == COMP_IMU_NO_SAMPLE);
    d.regs[0x1E] = 3;
    put16(&d, 0x20, 256); put16(&d, 0x22, -1000); put16(&d, 0x24, 1000);
    put16(&d, 0x28, 8197); put16(&d, 0x2A, -8197); put16(&d, 0x2C, 32767);
    assert(comp_lsm6dso_poll(&imu, 42, &sample) == COMP_IMU_SAMPLE);
    assert(sample.accel_mg[0] == 1000 && sample.accel_mg[1] == -1000 && sample.accel_mg[2] == 3997);
    assert(sample.gyro_mdps[0] == -8750 && sample.gyro_mdps[1] == 8750 && sample.temperature_c_x10 == 260);
    previous = sample; d.partial = true;
    assert(comp_lsm6dso_poll(&imu, 62, &sample) == COMP_IMU_IO_ERROR);
    assert(memcmp(&sample, &previous, sizeof(sample)) == 0 && imu.samples == 1);
    d.partial = false; d.regs[0x0F] = 0;
    assert(!comp_lsm6dso_start(&imu, rd, wr, &d, 0));
    d.regs[0x0F] = 0x6C;
    assert(comp_lsm6dso_start(&imu, rd, wr, &d, UINT32_MAX - 50u));
    assert(comp_lsm6dso_poll(&imu, 49, &sample) == COMP_IMU_IO_ERROR);
    assert(comp_lsm6dso_start(&imu, rd, wr, &d, 0)); d.regs[0x12] = 0;
    assert(comp_lsm6dso_poll(&imu, 1, &sample) == COMP_IMU_NO_SAMPLE);
    assert(comp_lsm6dso_stop(&imu) && d.regs[0x10] == 0 && d.regs[0x11] == 0 && d.regs[0x0D] == 0);
}
static void test_motion(void)
{
    comp_motion_events_t m; comp_imu_sample_t s = {0}; uint8_t events = 0;
    comp_motion_events_init(&m); s.accel_mg[2] = 1000;
    for (unsigned t = 0; t <= 1200; t += 20) { s.timestamp_ms = t; events |= comp_motion_events_update(&m, &s); }
    assert((events & COMP_MOTION_ORIENTATION_CHANGED) != 0 && m.orientation == 5);
    s.timestamp_ms += 20; s.accel_mg[0] = 500;
    assert((comp_motion_events_update(&m, &s) & COMP_MOTION_PICKUP) != 0);
    assert(comp_motion_events_update(&m, &s) == 0); /* same sample never repeats an action */
    s.timestamp_ms += 20; s.accel_mg[0] = 3000;
    assert((comp_motion_events_update(&m, &s) & COMP_MOTION_SHAKE) == 0);
    s.timestamp_ms += 1000;
    assert((comp_motion_events_update(&m, &s) & COMP_MOTION_SHAKE) != 0);
    s.timestamp_ms += 1000; s.accel_mg[0] = INT16_MIN; s.accel_mg[1] = INT16_MIN; s.accel_mg[2] = INT16_MIN;
    assert((comp_motion_events_update(&m, &s) & COMP_MOTION_SHAKE) != 0);
}
typedef struct { bool enabled, pending, fail; } speaker_io_t;
static bool speaker_amp(void *p, bool on) { ((speaker_io_t *)p)->enabled = on; return true; }
static bool speaker_tx(void *p, const int16_t *pcm, size_t frames)
{
    speaker_io_t *io = p; assert(pcm != NULL && frames == 64);
    if (io->fail) { return false; } io->pending = true; return true;
}
static void test_services(void)
{
    speaker_io_t io = {0}; comp_speaker_t speaker;
    comp_speaker_config_t config = {speaker_amp, speaker_tx, NULL, &io};
    companion_v1_features_t features; comp_v11_services_t services;
    comp_lsm6dso_t imu = {.state = COMP_IMU_READY, .samples = 1};
    comp_imu_sample_t sample = {.timestamp_ms = 100, .accel_mg = {1, 2, 1000}, .gyro_mdps = {-8750, 0, 1000}};
    companion_gatt_speaker_control_v1_t request = {.schema_version = 1, .command = 1,
        .volume_percent = 20, .request_id = 55, .prompt_id = 0};
    comp_speaker_init(&speaker, &config); companion_v1_features_init(&features, 0);
    comp_v11_services_bind(&services, &features, &speaker, true, &imu, &sample);
    (void)companion_v1_features_refresh_peripherals(&features, 100);
    assert(features.imu.sensor_state == COMPANION_V1_IMU_STATE_READY && features.imu.gyro_x_dps == -8);
    (void)companion_v1_features_refresh_peripherals(&features, 601);
    assert(features.imu.sensor_state == COMPANION_V1_IMU_STATE_ERROR && features.imu.accel_z_mg == 0);
    services.playback_inhibited=true;
    assert(companion_v1_apply_speaker_control(&features,&request,100)==COMPANION_V1_RESULT_BUSY);
    assert(!comp_speaker_active(&speaker) && !io.enabled && features.speaker.played_count==0);
    services.playback_inhibited=false;
    assert(companion_v1_apply_speaker_control(&features, &request, 100) == COMPANION_V1_RESULT_OK);
    assert(features.speaker.played_count == 0 && features.speaker.request_id == 55);
    assert(companion_v1_apply_speaker_control(&features, &request, 100) == COMPANION_V1_RESULT_BUSY);
    assert(features.speaker.last_error == COMP_V11_SPEAKER_ERROR_BUSY);
    for (unsigned i = 0; i < 100 && comp_speaker_active(&speaker); ++i) {
        assert(comp_speaker_service(&speaker) && io.pending);
        io.pending = false; comp_speaker_tx_complete(&speaker, true);
        (void)companion_v1_features_refresh_peripherals(&features, 100 + i);
    }
    assert(!comp_speaker_active(&speaker) && features.speaker.played_count == 1 && !io.enabled);
    request.prompt_id = 255;
    assert(companion_v1_apply_speaker_control(&features, &request, 300) == COMPANION_V1_RESULT_UNSUPPORTED_COMMAND);
    assert(features.speaker.last_error == COMPANION_V1_SPEAKER_ERROR_UNSUPPORTED);
    assert(features.speaker.played_count == 1);
    request.prompt_id = 0; io.fail = true;
    assert(companion_v1_apply_speaker_control(&features, &request, 300) == COMPANION_V1_RESULT_OK);
    assert(!comp_speaker_service(&speaker));
    (void)companion_v1_features_refresh_peripherals(&features, 301);
    assert(features.speaker.state == COMPANION_V1_SPEAKER_STATE_ERROR && features.speaker.played_count == 1);
}
int main(void)
{
    test_battery_gate(); test_io_power(); test_always_on_display_rail(); test_battery(); test_imu(); test_motion(); test_services();
    puts("PASS_PREHARDWARE: V1.1 expander/power/battery/IMU/motion including bus failures and timer wrap");
    return 0;
}
