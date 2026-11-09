#include "lsm6dso.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
/* Register/bus model: reading TAP_SRC during the first-tap state resets the
 * recognizer, as described by ST Technical Moderator on2024-03-12. */
typedef struct {uint8_t reg[256],stage;unsigned resets;uint32_t first;} bus_t;
static bool read_bus(void *context,uint8_t reg,uint8_t *p,size_t n)
{
    bus_t *b=context;memcpy(p,b->reg+reg,n);
    if(reg==0x1Cu){if(b->stage==1u)++b->resets;b->stage=0u;b->reg[reg]=0u;}
    return true;
}
static bool write_bus(void *context,uint8_t reg,const uint8_t *p,size_t n)
{bus_t *b=context;memcpy(b->reg+reg,p,n);return true;}
static void finger(bus_t *b,uint32_t now)
{
    if(b->stage==1u&&now-b->first>=30u&&now-b->first<=538u){b->stage=2u;b->reg[0x1C]=0x50u;}
    else {b->stage=1u;b->first=now;b->reg[0x1C]=0x20u;}
}
int main(void)
{
    bus_t b={0};comp_lsm6dso_t imu;comp_imu_sample_t sample={0};b.reg[0x0F]=0x6Cu;
    assert(comp_lsm6dso_start(&imu,read_bus,write_bus,&b,0u));b.reg[0x12]=0u;
    assert(comp_lsm6dso_poll(&imu,10u,&sample)==COMP_IMU_NO_SAMPLE);
    assert(comp_lsm6dso_set_recording_taps(&imu,true));
    for(uint32_t now=20u;now<=3000u;now+=20u) {
        if(now>=100u&&(now-100u)%600u==0u)finger(&b,now);
        if(now>=300u&&(now-300u)%600u==0u)finger(&b,now);
        b.reg[0x1E]=3u;
#if COMP_TEST_IRQ_LATCH
        /* Physical high sampled through the IO expander. DRDY must not share
         * the pin, otherwise the first-tap state is read/cleared prematurely. */
        if((b.reg[0x5E]&8u)&&b.reg[0x0D]==0u&&b.stage==2u)imu.tap_irq_pending=true;
#endif
        assert(comp_lsm6dso_poll(&imu,now,&sample)==COMP_IMU_SAMPLE);
    }
#if COMP_TEST_IRQ_LATCH
    assert(b.resets==0u&&imu.tap_reads==5u&&(imu.tap_counts>>16u)==5u);
    puts("PASS_MODEL: five double taps survive first-tap interval, only five latched reads,150 real samples retained");
#else
    assert(b.resets==10u&&imu.tap_reads==150u&&imu.tap_counts==0u);
    puts("REPRODUCED_MODEL: eager status polling resets all ten individual taps and yields zero double taps");
#endif
    return 0;
}
