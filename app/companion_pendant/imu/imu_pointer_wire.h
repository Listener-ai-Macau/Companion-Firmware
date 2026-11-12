#ifndef COMP_IMU_POINTER_WIRE_H
#define COMP_IMU_POINTER_WIRE_H
#include "lsm6dso.h"
#include "imu_fusion.h"
#include "companion_crc32.h"
#include <string.h>
#include <math.h>

/* CIM1 is opt-in on the existing encrypted CIN1 settings subscription.
 * 32B, integer data only. Sensor time, not BLE arrival time, drives mapping.
 * Rates are centidegrees/s, preserving the LSM6DSO sub-degree precision.
 * The legacy9001 diagnostic schema and its1Hz publication stay unchanged. */
static inline void comp_imu_pointer_put16(uint8_t *p,int16_t v)
{p[0]=(uint8_t)v;p[1]=(uint8_t)((uint16_t)v>>8u);}
static inline void comp_imu_pointer_put32(uint8_t *p,uint32_t v)
{for(unsigned i=0;i<4u;++i)p[i]=(uint8_t)(v>>(8u*i));}
static inline void comp_imu_pointer_pack(uint32_t timestamp,uint32_t sequence,bool held,uint8_t tap_serial,
    uint8_t schema,bool ready,const int16_t acceleration[3],const int32_t gyro[3],uint8_t packet[32])
{
    memcpy(packet,"CIM1",4u);packet[4]=schema;packet[5]=3u;packet[6]=(held?1u:0u)|(ready?2u:0u);packet[7]=tap_serial;
    comp_imu_pointer_put32(packet+8u,sequence);
    comp_imu_pointer_put32(packet+12u,timestamp);
    for(unsigned i=0;i<3u;++i) {
        comp_imu_pointer_put16(packet+16u+2u*i,acceleration[i]);
        int32_t rate=gyro[i]/10;
        if(rate>32767)rate=32767;else if(rate< -32768)rate= -32768;
        comp_imu_pointer_put16(packet+22u+2u*i,(int16_t)rate);
    }
    comp_imu_pointer_put32(packet+28u,companion_crc32(0u,packet,28u));
}
static inline void comp_imu_pointer_packet(const comp_imu_sample_t *s,uint32_t sequence,
    bool held,uint8_t tap_serial,bool fused,uint8_t packet[32])
{comp_imu_pointer_pack(s->timestamp_ms,sequence,held,tap_serial,fused?2u:1u,false,s->accel_mg,s->gyro_mdps,packet);}
static inline void comp_imu_pointer_fused_packet(const comp_imu_fused_sample_t *s,uint32_t sequence,
    bool held,uint8_t tap_serial,uint8_t packet[32])
{comp_imu_pointer_pack(s->timestamp_ms,sequence,held,tap_serial,3u,s->ready,s->gravity_q14,s->gyro_mdps,packet);}
/* WatchPointer computes heading at EVERY device sample, before testing radio
 * readiness. Sending a later absolute heading cannot lose an intervening turn.
 * Gravity/elevation stays absolute; only the platform/wire adapter changes. */
static inline float comp_imu_pointer_yaw(const comp_imu_fused_sample_t *s)
{
    float yaw=0.0f,norm=0.0f;
    for(unsigned i=0;i<3u;++i){const float g=(float)s->gravity_q14[i];yaw+=(float)s->gyro_mdps[i]*g;norm+=g*g;}
    return norm>0.0f?yaw/sqrtf(norm)*0.001f:0.0f;
}
static inline float comp_imu_pointer_heading(float heading,float yaw,uint32_t dt_ms)
{
    heading+=yaw*(float)(dt_ms>50u?50u:dt_ms)*0.001f;
    if(heading>180.0f)heading-=360.0f;
    else if(heading< -180.0f)heading+=360.0f;
    return heading;
}
static inline int16_t comp_imu_pointer_centidegrees(float value)
{
    value*=100.0f;if(value>32767.0f)value=32767.0f;else if(value< -32768.0f)value=-32768.0f;
    return (int16_t)(value+(value>=0.0f?0.5f:-0.5f));
}
static inline void comp_imu_pointer_aim_packet(const comp_imu_fused_sample_t *s,uint32_t sequence,
    bool held,uint8_t tap_serial,float heading,float yaw,uint8_t packet[32])
{
    comp_imu_pointer_fused_packet(s,sequence,held,tap_serial,packet);packet[4]=4u;
    comp_imu_pointer_put16(packet+16u,comp_imu_pointer_centidegrees(heading));
    for(unsigned i=0;i<3u;++i)comp_imu_pointer_put16(packet+18u+2u*i,s->gravity_q14[i]);
    comp_imu_pointer_put16(packet+24u,comp_imu_pointer_centidegrees(yaw));
    comp_imu_pointer_put16(packet+26u,comp_imu_pointer_centidegrees((float)s->gyro_mdps[0]*0.001f));
    comp_imu_pointer_put32(packet+28u,companion_crc32(0u,packet,28u));
}
#endif
