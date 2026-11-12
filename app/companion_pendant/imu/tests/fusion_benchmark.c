/* Engineering RAM-only microbenchmark of the unchanged MIT Fusion sources.
 * Not a product image, recording test, BLE throughput or power measurement. */
#include "FusionAhrs.h"
#include "FusionBias.h"
#include <stdint.h>

#define REG(a) (*(volatile uint32_t *)(a))
typedef struct {uint32_t count,total_cycles,min_cycles,max_cycles;} Phase;
typedef struct {
    uint32_t magic,done,core_hz,ahrs_bytes,bias_bytes;
    Phase phase[4];
    float gravity[3],quaternion[4];
    uint32_t counter_overhead;
} Result;
__attribute__((section(".result"))) volatile Result result;
static FusionAhrs ahrs;
static FusionBias bias;
extern unsigned char __bss_start__,__bss_end__;
static void init(void) {
    FusionAhrsInitialise(&ahrs);FusionBiasInitialise(&bias);
    FusionAhrsSettings a=fusionAhrsDefaultSettings;
    a.sampleRate=104.0f;a.gain=0.5f;a.gyroscopeRange=250.0f;
    a.accelerationRejection=10.0f;a.rejectionTimeout=5.0f;
    FusionAhrsSetSettings(&ahrs,&a);
    FusionBiasSettings b=fusionBiasDefaultSettings;
    b.sampleRate=104.0f;b.stationaryThreshold=0.5f;b.stationaryPeriod=1.0f;
    FusionBiasSetSettings(&bias,&b);
}
__attribute__((noinline)) static void update(unsigned kind,unsigned n) {
    const int16_t raw_accel[3]={kind==2u?(int16_t)(n&1u?500:-500):0,0,1000};
    FusionVector a={.array={raw_accel[0]*0.001f,raw_accel[1]*0.001f,raw_accel[2]*0.001f}};
    FusionVector g={.array={kind==1u?25.0f:0.1f,kind==1u?-15.0f:0.1f,kind==1u?45.0f:0.1f}};
    g=FusionBiasUpdate(&bias,g);
    FusionAhrsUpdateNoMagnetometer(&ahrs,g,a);
    const FusionVector up=FusionAhrsGetGravity(&ahrs);
    const FusionQuaternion q=FusionAhrsGetQuaternion(&ahrs);
    for(unsigned i=0;i<3;++i)result.gravity[i]=up.array[i];
    for(unsigned i=0;i<4;++i)result.quaternion[i]=q.array[i];
}
void benchmark_main(void) {
    for(unsigned char *p=&__bss_start__;p<&__bss_end__;++p)*p=0;
    for(unsigned i=0;i<sizeof(result)/4u;++i)((volatile uint32_t*)&result)[i]=0u;
    result.magic=0x46555331u;result.core_hz=61439820u;
    result.ahrs_bytes=sizeof(ahrs);result.bias_bytes=sizeof(bias);
    REG(0xe000edfc)|=1u<<24;REG(0xe0001000)|=1u;
    uint32_t before=REG(0xe0001004);result.counter_overhead=REG(0xe0001004)-before;
    for(unsigned phase=0;phase<4;++phase) {
        init();
        if(phase<3u)for(unsigned i=0;i<400u;++i)update(0u,i);
        Phase r={.count=1024u,.min_cycles=0xffffffffu};
        for(unsigned i=0;i<r.count;++i) {
            uint32_t start=REG(0xe0001004);
            update(phase==3u?1u:phase,i);
            uint32_t elapsed=REG(0xe0001004)-start;
            r.total_cycles+=elapsed;
            if(elapsed<r.min_cycles)r.min_cycles=elapsed;
            if(elapsed>r.max_cycles)r.max_cycles=elapsed;
        }
        result.phase[phase]=r;
    }
    result.done=0x444f4e45u;
    __asm volatile("bkpt #0");
    for(;;){}
}
__attribute__((naked,section(".entry"))) void _start(void) {
    __asm volatile("cpsid i\nldr sp,=0x20020000\nbl benchmark_main\nb .");
}
