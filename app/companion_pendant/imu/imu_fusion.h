#ifndef COMP_IMU_FUSION_H
#define COMP_IMU_FUSION_H
#include "lsm6dso.h"
#include "../../../third_party/imu-fusion/Fusion/FusionAhrs.h"
#include "../../../third_party/imu-fusion/Fusion/FusionBias.h"
/* One static owner, no heap. Runs only for an explicitly enabled pointer. */
typedef struct {
    FusionAhrs ahrs;FusionBias bias;
    uint32_t last_ms,calibration_ms;
    int32_t gyro_sum[3],accel_sum[3];
    uint16_t calibration_samples;bool active,calibrated;
} comp_imu_fusion_t;
typedef struct {int16_t gravity_q14[3];int32_t gyro_mdps[3];uint32_t timestamp_ms;bool ready;} comp_imu_fused_sample_t;
bool comp_imu_fusion_update(comp_imu_fusion_t *state,const comp_imu_sample_t *raw,comp_imu_fused_sample_t *fused);
#endif
