#include "lsm6dso.h"
#include <string.h>

/* ST LSM6DSO DS12140 / STMicroelectronics/lsm6dso-pid register definitions. */
static bool write_byte(comp_lsm6dso_t *imu, uint8_t reg, uint8_t value)
{ return imu->write(imu->context, reg, &value, 1u); }
static comp_imu_poll_t fail(comp_lsm6dso_t *imu)
{
    imu->state = COMP_IMU_FAULT;
    imu->recovery_waiting = false;
    imu->tap_source = 0u;
    imu->tap_irq_pending=false;
    imu->errors++;
    return COMP_IMU_IO_ERROR;
}
static bool configure_taps(comp_lsm6dso_t *imu)
{
    /* AN5192 sec5.5 and ST lsm6dso-pid: latched XYZ double-tap to INT1.
     * Route remains disabled until recording uses recommended417Hz accel.
     * At+/-4g,4LSB=0.5g slope threshold for a finger tap on the small card;
     * shock/quiet/duration are provisional until real enclosure tuning. */
    static const uint8_t config[6]={0x0Fu,0x04u,0x84u,0x04u,0x7Fu,0x80u};
    uint8_t actual[6],route;
    return imu->write(imu->context,0x56u,config,sizeof(config)) &&
        write_byte(imu,0x5Eu,0u) &&
        imu->read(imu->context,0x56u,actual,sizeof(actual)) &&
        imu->read(imu->context,0x5Eu,&route,1u) &&
        !memcmp(config,actual,sizeof(config)) && route==0u;
}
static bool configure_idle(comp_lsm6dso_t *imu, bool idle)
{
    uint8_t ctrl[2], ctrl6, int1;
    const uint8_t ctrl1 = idle ? 0x18u : imu->recording_taps ? 0x68u : 0x38u;
    const uint8_t ctrl2 = idle ? 0x00u : 0x30u; /* gyro off / 52 Hz +/-250 dps */
    const uint8_t low_power = idle ? 0x10u : 0x00u; /* CTRL6_C XL_HM_MODE */
    const uint8_t route = idle ? 0x01u : imu->recording_taps ? 0u : 0x03u;

    /* Power down the accelerometer before changing its operating mode. This
     * also gives one deterministic restore path after a partial transaction. */
    if (!write_byte(imu, 0x0Du, 0x00u) ||
        !write_byte(imu, 0x10u, 0x00u) ||
        !write_byte(imu, 0x11u, ctrl2) ||
        !write_byte(imu, 0x15u, low_power) ||
        !write_byte(imu, 0x10u, ctrl1) ||
        !write_byte(imu, 0x0Du, route) ||
        !imu->read(imu->context, 0x10u, ctrl, sizeof(ctrl)) ||
        !imu->read(imu->context, 0x15u, &ctrl6, 1u) ||
        !imu->read(imu->context, 0x0Du, &int1, 1u) ||
        ctrl[0] != ctrl1 || ctrl[1] != ctrl2 || ctrl6 != low_power ||
        int1 != route) {
        (void)fail(imu);
        return false;
    }
    imu->idle_accel_only = idle;
    return true;
}
static int32_t signed16(const uint8_t *p)
{
    uint32_t value = (uint32_t)p[0] | ((uint32_t)p[1] << 8);
    return value >= 32768u ? (int32_t)value - 65536 : (int32_t)value;
}
bool comp_lsm6dso_start(comp_lsm6dso_t *imu, comp_lsm6dso_read_fn read,
                       comp_lsm6dso_write_fn write, void *context, uint32_t now_ms)
{
    uint8_t id;
    if (imu == NULL) { return false; }
    memset(imu, 0, sizeof(*imu));
    if (read == NULL || write == NULL) { return false; }
    imu->read = read; imu->write = write; imu->context = context;
    if (!read(context, 0x0Fu, &id, 1u) || id != 0x6Cu || !write_byte(imu, 0x12u, 0x01u)) {
        (void)fail(imu); return false;
    }
    imu->state = COMP_IMU_RESET_WAIT; imu->reset_ms = now_ms;
    return true;
}
comp_imu_poll_t comp_lsm6dso_poll(comp_lsm6dso_t *imu, uint32_t now_ms,
                                 comp_imu_sample_t *sample)
{
    uint8_t status, bytes[14], tap;
    comp_imu_sample_t value = {.timestamp_ms = now_ms};
    if (imu == NULL || sample == NULL || imu->read == NULL || imu->write == NULL) {
        return COMP_IMU_IO_ERROR;
    }
    imu->tap_source=0u;
    if (imu->state == COMP_IMU_RESET_WAIT) {
        if (!imu->read(imu->context, 0x12u, &status, 1u)) { return fail(imu); }
        if ((status & 1u) != 0u) {
            return now_ms - imu->reset_ms >= 100u ? fail(imu) : COMP_IMU_NO_SAMPLE;
        }
        if (!write_byte(imu, 0x12u, 0x44u) || /* BDU + IF_INC, SPI four-wire */
            !write_byte(imu, 0x18u, 0x02u) || /* disable I3C */
            !write_byte(imu, 0x10u, 0x38u) || /* 52Hz, +/-4g */
            !write_byte(imu, 0x11u, 0x30u) || /* 52Hz, +/-250dps */
            !write_byte(imu, 0x0Du, 0x03u) || /* both data-ready signals to INT1 */
            !imu->read(imu->context, 0x10u, bytes, 3u) ||
            bytes[0] != 0x38u || bytes[1] != 0x30u || bytes[2] != 0x44u ||
            !configure_taps(imu)) { return fail(imu); }
        imu->state = COMP_IMU_READY;
        return COMP_IMU_NO_SAMPLE;
    }
    if (imu->state != COMP_IMU_READY) { return COMP_IMU_NO_SAMPLE; }
    if (!imu->read(imu->context, 0x1Eu, &status, 1u)) { return fail(imu); }
    if (imu->idle_accel_only) {
        if ((status & 1u) == 0u) { return COMP_IMU_NO_SAMPLE; }
        if (!imu->read(imu->context, 0x28u, bytes + 8u, 6u)) { return fail(imu); }
    } else {
        if ((status & 3u) != 3u) { return COMP_IMU_NO_SAMPLE; }
        if (!imu->read(imu->context, 0x20u, bytes, sizeof(bytes))) { return fail(imu); }
        value.temperature_c_x10 = (int16_t)(250 + signed16(bytes) * 10 / 256);
        for (size_t axis = 0u; axis < 3u; ++axis) {
            value.gyro_mdps[axis] = signed16(bytes + 2u + 2u * axis) * 875 / 100;
        }
    }
    for (size_t axis = 0u; axis < 3u; ++axis) {
        value.accel_mg[axis] = (int16_t)(signed16(bytes + 8u + 2u * axis) * 122 / 1000);
    }
    /* TAP_SRC also resets the in-progress recognition algorithm. Never read
     * between the two finger taps merely because data-ready was polled.
     * During recording INT1 carries DOUBLE_TAP only; the IO-expander reports
     * that physical high level, then the next real sample consumes it once. */
    if(imu->recording_taps && imu->tap_irq_pending) {
        if(!imu->read(imu->context,0x1Cu,&tap,1u))return fail(imu);
        imu->tap_irq_pending=false;
        imu->tap_source=tap;
        if(imu->tap_reads!=UINT32_MAX)++imu->tap_reads;
        if(tap&0x40u) {
            if((tap&0x20u) && (imu->tap_counts&0xFFFFu)!=0xFFFFu)++imu->tap_counts;
            if((tap&0x10u) && (imu->tap_counts>>16u)!=0xFFFFu)imu->tap_counts+=0x10000u;
        }
    }
    *sample = value; imu->samples++;
    imu->recovery_attempts = 0u;
    imu->recovery_waiting = false;
    return COMP_IMU_SAMPLE;
}
bool comp_lsm6dso_set_idle(comp_lsm6dso_t *imu, bool idle)
{
    if (imu == NULL || (idle && imu->recording_taps) || imu->state != COMP_IMU_READY || imu->read == NULL ||
        imu->write == NULL) {
        return false;
    }
    if (imu->idle_accel_only == idle) {
        return true;
    }
    return configure_idle(imu, idle);
}
bool comp_lsm6dso_set_recording_taps(comp_lsm6dso_t *imu, bool enabled)
{
    uint8_t ctrl,route,drdy,discard;
    if(!imu || imu->state!=COMP_IMU_READY)return false;
    if(imu->recording_taps==enabled)return true;
    if(enabled && imu->idle_accel_only && !configure_idle(imu,false))return false;
    const uint8_t rate=enabled?0x68u:0x38u;
    if(!write_byte(imu,0x10u,rate) || !write_byte(imu,0x0Du,enabled?0u:3u) ||
       !write_byte(imu,0x5Eu,enabled?8u:0u) ||
       !imu->read(imu->context,0x10u,&ctrl,1u) || !imu->read(imu->context,0x5Eu,&route,1u) ||
       !imu->read(imu->context,0x0Du,&drdy,1u) ||
       !imu->read(imu->context,0x1Cu,&discard,1u) || ctrl!=rate || route!=(enabled?8u:0u) || drdy!=(enabled?0u:3u)) {
        (void)fail(imu);return false;
    }
    imu->recording_taps=enabled;imu->tap_source=0u;imu->tap_irq_pending=false;
    return true;
}
bool comp_lsm6dso_stop(comp_lsm6dso_t *imu)
{
    if (imu == NULL || imu->write == NULL) { return false; }
    if (!write_byte(imu, 0x5Eu, 0u) || !write_byte(imu, 0x0Du, 0u) ||
        !write_byte(imu, 0x10u, 0u) || !write_byte(imu, 0x11u, 0u)) {
        (void)fail(imu); return false;
    }
    imu->state = COMP_IMU_OFF;
    imu->idle_accel_only = false;
    imu->tap_source=0u;
    imu->recording_taps=false;
    imu->tap_irq_pending=false;
    return true;
}

bool comp_lsm6dso_recover(comp_lsm6dso_t *imu, uint32_t now_ms)
{
    uint8_t id;
    if (imu == NULL || imu->state != COMP_IMU_FAULT || imu->read == NULL ||
        imu->write == NULL || imu->recovery_attempts >= 3u) return false;
    if (!imu->recovery_waiting) {
        /* reset_ms has no reset deadline owner while in FAULT. Reuse it for
         * the retry delay; unsigned subtraction also handles tick wrap. */
        imu->reset_ms = now_ms;
        imu->recovery_waiting = true;
        return false;
    }
    if (now_ms - imu->reset_ms < 1000u) return false;
    ++imu->recovery_attempts;
    imu->recovery_waiting = false;
    if (!imu->read(imu->context, 0x0Fu, &id, 1u) || id != 0x6Cu ||
        !write_byte(imu, 0x12u, 0x01u)) {
        (void)fail(imu);
        return false;
    }
    /* Do not call start(): it clears the original error/sample counters.
     * RESET_WAIT will restore the full verified configuration before data. */
    imu->state = COMP_IMU_RESET_WAIT;
    imu->reset_ms = now_ms;
    imu->idle_accel_only = false;
    imu->recording_taps=false;
    imu->tap_irq_pending=false;
    return true;
}
