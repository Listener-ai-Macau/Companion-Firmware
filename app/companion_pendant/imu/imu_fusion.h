#ifndef COMP_IMU_FUSION_H
#define COMP_IMU_FUSION_H
#include "lsm6dso.h"
#include "../../../third_party/imu-fusion/Fusion/FusionAhrs.h"
#include "../../../third_party/imu-fusion/Fusion/FusionBias.h"
/* One static owner, no heap. Runs only for an explicitly enabled pointer. */
typedef struct {FusionAhrs ahrs;FusionBias bias;uint32_t last_ms;bool active;} comp_imu_fusion_t;
bool comp_imu_fusion_update(comp_imu_fusion_t *state,const comp_imu_sample_t *raw,comp_imu_sample_t *fused);
#endif
