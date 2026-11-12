#include "imu_fusion.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
int main(void) {
    comp_imu_fusion_t s={0};comp_imu_sample_t raw={0};comp_imu_fused_sample_t out={0};
    raw.accel_mg[2]=1000;
    for(unsigned n=0;n<500u;++n){raw.timestamp_ms=n*10u;assert(comp_imu_fusion_update(&s,&raw,&out));}
    assert(abs(out.gravity_q14[0])<=1&&abs(out.gravity_q14[1])<=1&&abs(out.gravity_q14[2]-16384)<=1);
    assert(!comp_imu_fusion_update(&s,&raw,&out));
    raw.gyro_mdps[2]=15000;
    for(unsigned n=500;n<700u;++n){raw.timestamp_ms=n*10u;assert(comp_imu_fusion_update(&s,&raw,&out));}
    FusionQuaternion q=FusionAhrsGetQuaternion(&s.ahrs);
    float yaw=2.0f*atan2f(q.element.z,q.element.w)*57.2957795f;
    assert(fabsf(yaw-30.0f)<0.5f); /* Independent2s*15deg/s physical rotation. */
    raw.gyro_mdps[2]=0;
    for(unsigned n=700;n<720u;++n){raw.timestamp_ms=n*10u;raw.accel_mg[0]=700;assert(comp_imu_fusion_update(&s,&raw,&out));}
    assert(abs(out.gravity_q14[0])<1475); /*20*10ms translation must not become41deg tilt. */
    s.last_ms=0xfffffff8u;raw.timestamp_ms=2u;raw.accel_mg[0]=0;
    assert(comp_imu_fusion_update(&s,&raw,&out));
    assert(s.last_ms==2u);
    s=(comp_imu_fusion_t){0};raw=(comp_imu_sample_t){.accel_mg={283,613,-724},.gyro_mdps={800,-700,500}};
    for(unsigned n=0;n<600u;++n){raw.timestamp_ms=n*10u;assert(comp_imu_fusion_update(&s,&raw,&out));if(n<100u)assert(!out.ready);}
    assert(out.ready&&abs(out.gyro_mdps[0])<=1&&abs(out.gyro_mdps[1])<=1&&abs(out.gyro_mdps[2])<=1);
    assert(out.gravity_q14[2]<-11000);
    /* Skipping startup yaw zeroing must leave gravity unchanged. */
    FusionAhrs a,b;FusionAhrsInitialise(&a);FusionAhrsInitialise(&b);
    FusionAhrsSettings settings=fusionAhrsDefaultSettings;settings.sampleRate=100.0f;
    FusionAhrsSetSettings(&a,&settings);FusionAhrsSetSettings(&b,&settings);
    for(unsigned n=0;n<5000u;++n){
        FusionVector g={.array={(float)((int)(n%41u)-20),7.0f,11.0f}};
        FusionVector accel={.array={0.283f,0.613f,-0.724f}};
        FusionAhrsUpdateNoMagnetometer(&a,g,accel);
        FusionAhrsUpdate(&b,g,accel,FUSION_VECTOR_ZERO);
        FusionVector x=FusionAhrsGetGravity(&a),y=FusionAhrsGetGravity(&b);
        for(unsigned k=0;k<3u;++k)assert(fabsf(x.array[k]-y.array[k])<0.0001f);
    }
    printf("PASS Fusion real C wrapper: stationary gravity, duplicate rejection,30deg physical yaw, acceleration rejection, clock wrap; state%zuB\n",sizeof(s));
    return 0;
}
