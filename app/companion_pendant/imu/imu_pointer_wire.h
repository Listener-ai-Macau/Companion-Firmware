#ifndef COMP_IMU_POINTER_WIRE_H
#define COMP_IMU_POINTER_WIRE_H
#include "lsm6dso.h"
#include "companion_crc32.h"
#include <string.h>

/* CIM1 is opt-in on the existing encrypted CIN1 settings subscription.
 * 32B, integer data only. Sensor time, not BLE arrival time, drives mapping.
 * Rates are centidegrees/s, preserving the LSM6DSO sub-degree precision.
 * The legacy9001 diagnostic schema and its1Hz publication stay unchanged. */
static inline void comp_imu_pointer_put16(uint8_t *p,int16_t v)
{p[0]=(uint8_t)v;p[1]=(uint8_t)((uint16_t)v>>8u);}
static inline void comp_imu_pointer_put32(uint8_t *p,uint32_t v)
{for(unsigned i=0;i<4u;++i)p[i]=(uint8_t)(v>>(8u*i));}
static inline void comp_imu_pointer_packet(const comp_imu_sample_t *s,uint32_t sequence,
                                         bool held,uint8_t packet[32])
{
    memcpy(packet,"CIM1",4u);packet[4]=1u;packet[5]=3u;packet[6]=held?1u:0u;packet[7]=0u;
    comp_imu_pointer_put32(packet+8u,sequence);
    comp_imu_pointer_put32(packet+12u,s->timestamp_ms);
    for(unsigned i=0;i<3u;++i) {
        comp_imu_pointer_put16(packet+16u+2u*i,s->accel_mg[i]);
        int32_t rate=s->gyro_mdps[i]/10;
        if(rate>32767)rate=32767;else if(rate< -32768)rate= -32768;
        comp_imu_pointer_put16(packet+22u+2u*i,(int16_t)rate);
    }
    comp_imu_pointer_put32(packet+28u,companion_crc32(0u,packet,28u));
}
#endif
