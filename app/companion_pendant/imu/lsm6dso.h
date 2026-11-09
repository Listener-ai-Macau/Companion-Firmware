#ifndef COMP_LSM6DSO_H
#define COMP_LSM6DSO_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
typedef bool (*comp_lsm6dso_read_fn)(void *, uint8_t, uint8_t *, size_t);
typedef bool (*comp_lsm6dso_write_fn)(void *, uint8_t, const uint8_t *, size_t);
typedef enum { COMP_IMU_OFF, COMP_IMU_RESET_WAIT, COMP_IMU_READY, COMP_IMU_FAULT } comp_imu_state_t;
typedef enum { COMP_IMU_NO_SAMPLE, COMP_IMU_SAMPLE, COMP_IMU_IO_ERROR } comp_imu_poll_t;
typedef struct {
    int16_t accel_mg[3];
    int32_t gyro_mdps[3];
    int16_t temperature_c_x10;
    uint32_t timestamp_ms;
} comp_imu_sample_t;
typedef struct {
    comp_lsm6dso_read_fn read;
    comp_lsm6dso_write_fn write;
    void *context;
    comp_imu_state_t state;
    uint32_t reset_ms;
    uint32_t errors;
    uint32_t samples;
    bool idle_accel_only;
    uint8_t recovery_attempts;
    bool recovery_waiting;
    uint8_t tap_source; /* Fresh TAP_SRC of the last successful sample; tail padding. */
    bool recording_taps;
} comp_lsm6dso_t;
#define COMP_LSM6DSO_DOUBLE_TAP 0x50u /* TAP_IA and DOUBLE_TAP, AN5192 */
/* Registers callbacks use one atomic CS-bounded shared-bus transaction.
 * Driver configures +/-4g, +/-250dps, 52Hz, BDU, auto-increment, DRDY INT1.
 * Poll fallback is required: V1.1 INT1 arrives via the I/O expander. */
bool comp_lsm6dso_start(comp_lsm6dso_t *imu, comp_lsm6dso_read_fn read,
                       comp_lsm6dso_write_fn write, void *context, uint32_t now_ms);
comp_imu_poll_t comp_lsm6dso_poll(comp_lsm6dso_t *imu, uint32_t now_ms,
                                 comp_imu_sample_t *sample);
/* Product-idle mode keeps pickup/orientation sensing at 12.5 Hz in the
 * accelerometer low-power mode and powers the gyroscope down. Returning to
 * run mode restores the accepted 52 Hz accel+gyro configuration. */
bool comp_lsm6dso_set_idle(comp_lsm6dso_t *imu, bool idle);
/* Call only before microphone START / after actual STOP. Embedded taps need
 * the AN5192 recommended417Hz accel rate; gyro and host polling stay52Hz.
 * Ordinary awake/idle modes remain52/12.5Hz with the tap route disabled. */
bool comp_lsm6dso_set_recording_taps(comp_lsm6dso_t *imu, bool enabled);
/* Idle-only product recovery. Wait at least 1 s before each reset; stop after
 * three attempts without a valid sample. No loop, delay or sample is emitted
 * here. Poll RESET_WAIT normally; only a real sample clears the retry budget.
 * The caller must also defer reset/configuration while audio/OTA owns time. */
bool comp_lsm6dso_recover(comp_lsm6dso_t *imu, uint32_t now_ms);
bool comp_lsm6dso_stop(comp_lsm6dso_t *imu);
#endif
