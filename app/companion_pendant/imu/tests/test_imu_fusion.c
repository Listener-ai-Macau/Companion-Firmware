#include "imu_fusion.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
int main(void) {
    comp_imu_fusion_t s={0};comp_imu_sample_t raw={0},out={0};
    raw.accel_mg[2]=1000;
    for(unsigned n=0;n<500u;++n){raw.timestamp_ms=n*10u;assert(comp_imu_fusion_update(&s,&raw,&out));}
    assert(abs(out.accel_mg[0])<=1&&abs(out.accel_mg[1])<=1&&abs(out.accel_mg[2]-1000)<=1);
    assert(!comp_imu_fusion_update(&s,&raw,&out));
    raw.gyro_mdps[2]=15000;
    for(unsigned n=500;n<700u;++n){raw.timestamp_ms=n*10u;assert(comp_imu_fusion_update(&s,&raw,&out));}
    FusionQuaternion q=FusionAhrsGetQuaternion(&s.ahrs);
    float yaw=2.0f*atan2f(q.element.z,q.element.w)*57.2957795f;
    assert(fabsf(yaw-30.0f)<0.5f); /* Independent2s*15deg/s physical rotation. */
    raw.gyro_mdps[2]=0;
    for(unsigned n=700;n<720u;++n){raw.timestamp_ms=n*10u;raw.accel_mg[0]=700;assert(comp_imu_fusion_update(&s,&raw,&out));}
    assert(abs(out.accel_mg[0])<90); /*20*10ms translation must not become41deg tilt. */
    s.last_ms=0xfffffff8u;raw.timestamp_ms=2u;raw.accel_mg[0]=0;
    assert(comp_imu_fusion_update(&s,&raw,&out));
    assert(s.last_ms==2u);
    printf("PASS Fusion real C wrapper: stationary gravity, duplicate rejection,30deg physical yaw, acceleration rejection, clock wrap; state%zuB\n",sizeof(s));
    return 0;
}
