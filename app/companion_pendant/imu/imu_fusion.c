#include "imu_fusion.h"
static void initialise(comp_imu_fusion_t *s) {
    FusionAhrsInitialise(&s->ahrs);FusionBiasInitialise(&s->bias);
    FusionAhrsSettings a=fusionAhrsDefaultSettings;
    a.sampleRate=100.0f;a.gain=0.5f;a.gyroscopeRange=250.0f;
    a.accelerationRejection=10.0f;a.rejectionTimeout=5.0f;
    FusionAhrsSetSettings(&s->ahrs,&a);
    FusionBiasSettings b=fusionBiasDefaultSettings;
    b.sampleRate=100.0f;b.stationaryThreshold=0.5f;b.stationaryPeriod=1.0f;
    FusionBiasSetSettings(&s->bias,&b);s->active=true;
}
static int32_t rounded(float v) {return (int32_t)(v+(v<0.0f?-0.5f:0.5f));}
bool comp_imu_fusion_update(comp_imu_fusion_t *s,const comp_imu_sample_t *raw,comp_imu_sample_t *fused) {
    const uint32_t elapsed=raw->timestamp_ms-s->last_ms;
    if(s->active&&elapsed==0u)return false;
    if(!s->active||elapsed>200u)initialise(s);
    FusionVector g={.array={raw->gyro_mdps[0]*0.001f,raw->gyro_mdps[1]*0.001f,raw->gyro_mdps[2]*0.001f}};
    const FusionVector a={.array={raw->accel_mg[0]*0.001f,raw->accel_mg[1]*0.001f,raw->accel_mg[2]*0.001f}};
    g=FusionBiasUpdate(&s->bias,g);
    if(elapsed>0u&&elapsed<=200u)FusionAhrsSetSamplePeriod(&s->ahrs,elapsed*0.001f);
    FusionAhrsUpdateNoMagnetometer(&s->ahrs,g,a);
    const FusionVector up=FusionAhrsGetGravity(&s->ahrs);
    *fused=*raw;
    for(unsigned i=0;i<3;++i){fused->accel_mg[i]=rounded(up.array[i]*1000.0f);fused->gyro_mdps[i]=rounded(g.array[i]*1000.0f);}
    s->last_ms=raw->timestamp_ms;return true;
}
