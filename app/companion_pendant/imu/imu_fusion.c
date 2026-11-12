#include "imu_fusion.h"
#include <math.h>
static void calibration_reset(comp_imu_fusion_t *s) {
    s->calibration_samples=0u;s->calibrated=false;
    for(unsigned i=0;i<3;++i)s->gyro_sum[i]=s->accel_sum[i]=0;
}
static void initialise(comp_imu_fusion_t *s) {
    FusionAhrsInitialise(&s->ahrs);FusionBiasInitialise(&s->bias);
    FusionAhrsSettings a=fusionAhrsDefaultSettings;
    a.sampleRate=100.0f;a.gain=0.5f;a.gyroscopeRange=250.0f;
    a.accelerationRejection=10.0f;a.rejectionTimeout=5.0f;
    FusionAhrsSetSettings(&s->ahrs,&a);
    FusionBiasSettings b=fusionBiasDefaultSettings;
    b.sampleRate=100.0f;b.stationaryThreshold=0.5f;b.stationaryPeriod=1.0f;
    FusionBiasSetSettings(&s->bias,&b);s->active=true;calibration_reset(s);
}
static int32_t rounded(float v) {return (int32_t)(v+(v<0.0f?-0.5f:0.5f));}
static void calibrate(comp_imu_fusion_t *s,const comp_imu_sample_t *raw) {
    int32_t norm=0;
    bool still=true;
    for(unsigned i=0;i<3;++i){norm+=(int32_t)raw->accel_mg[i]*raw->accel_mg[i];if(raw->gyro_mdps[i]<=-3000||raw->gyro_mdps[i]>=3000)still=false;}
    if(!still||norm<850*850||norm>1150*1150){calibration_reset(s);return;}
    if(!s->calibration_samples)s->calibration_ms=raw->timestamp_ms;
    for(unsigned i=0;i<3;++i){s->gyro_sum[i]+=raw->gyro_mdps[i];s->accel_sum[i]+=raw->accel_mg[i];}
    ++s->calibration_samples;
    if(raw->timestamp_ms-s->calibration_ms<1000u||s->calibration_samples<50u)return;
    FusionVector offset,gravity;
    const float scale=0.001f/s->calibration_samples;
    for(unsigned i=0;i<3;++i){offset.array[i]=s->gyro_sum[i]*scale;gravity.array[i]=s->accel_sum[i]*scale;}
    FusionBiasSetOffset(&s->bias,offset);
    /* Seed from a measured stationary interval using the upstream correction.
     * Select the correct hemisphere so an upside-down card is not antipodal. */
    FusionAhrsRestart(&s->ahrs);
    if(gravity.axis.z<0.0f)FusionAhrsSetQuaternion(&s->ahrs,(FusionQuaternion){.array={0.0f,1.0f,0.0f,0.0f}});
    for(unsigned i=0;i<300u;++i)FusionAhrsUpdate(&s->ahrs,FUSION_VECTOR_ZERO,gravity,FUSION_VECTOR_ZERO);
    FusionAhrsSkipStartup(&s->ahrs);s->calibrated=true;
}
bool comp_imu_fusion_update(comp_imu_fusion_t *s,const comp_imu_sample_t *raw,comp_imu_fused_sample_t *fused) {
    const uint32_t elapsed=raw->timestamp_ms-s->last_ms;
    if(s->active&&elapsed==0u)return false;
    if(!s->active||elapsed>200u)initialise(s);
    if(!s->calibrated)calibrate(s,raw);
    FusionVector g={.array={raw->gyro_mdps[0]*0.001f,raw->gyro_mdps[1]*0.001f,raw->gyro_mdps[2]*0.001f}};
    const FusionVector a={.array={raw->accel_mg[0]*0.001f,raw->accel_mg[1]*0.001f,raw->accel_mg[2]*0.001f}};
    g=FusionBiasUpdate(&s->bias,g);
    if(elapsed>0u&&elapsed<=200u)FusionAhrsSetSamplePeriod(&s->ahrs,elapsed*0.001f);
    /* The consumer needs gravity and corrected rates, not AHRS yaw. Calling
     * upstream Update with zero magnetometer skips only NoMagnetometer's
     * startup yaw-zeroing (atan2/sin/cos); gravity is yaw-invariant. */
    FusionAhrsUpdate(&s->ahrs,g,a,FUSION_VECTOR_ZERO);
    const FusionVector up=FusionAhrsGetGravity(&s->ahrs);
    /* Match the host's unit-UP contract before Q14 quantisation. Upstream's
     * fast quaternion normalisation intentionally has a small norm error. */
    const float q14_scale=16384.0f/sqrtf(up.axis.x*up.axis.x+up.axis.y*up.axis.y+up.axis.z*up.axis.z);
    fused->timestamp_ms=raw->timestamp_ms;fused->ready=s->calibrated;
    for(unsigned i=0;i<3;++i){fused->gravity_q14[i]=(int16_t)rounded(up.array[i]*q14_scale);fused->gyro_mdps[i]=rounded(g.array[i]*1000.0f);}
    s->last_ms=raw->timestamp_ms;return true;
}
