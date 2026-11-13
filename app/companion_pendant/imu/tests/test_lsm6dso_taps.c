#include "lsm6dso.h"
#include "../../power/recorder_input.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct { uint8_t reg[256]; int fail_read,fail_write,corrupt; unsigned taps_read; } bus_t;
static bool read_reg(void *context,uint8_t reg,uint8_t *p,size_t n)
{
    bus_t *b=context;
    if(b->fail_read==reg)return false;
    memcpy(p,b->reg+reg,n);
    if(b->corrupt>=reg&&b->corrupt<reg+(int)n)p[b->corrupt-reg]^=1u;
    if(reg==0x1Cu){b->taps_read++;b->reg[reg]=0u;}
    return true;
}
static bool write_reg(void *context,uint8_t reg,const uint8_t *p,size_t n)
{
    bus_t *b=context;
    if(b->fail_write==reg)return false;
    memcpy(b->reg+reg,p,n);return true;
}
static void start(comp_lsm6dso_t *imu,bus_t *b)
{
    memset(b,0,sizeof(*b));b->fail_read=b->fail_write=b->corrupt=-1;b->reg[0x0F]=0x6Cu;
    assert(comp_lsm6dso_start(imu,read_reg,write_reg,b,0u));
    b->reg[0x12]=0u;comp_imu_sample_t sample={0};
    assert(comp_lsm6dso_poll(imu,10u,&sample)==COMP_IMU_NO_SAMPLE&&imu->state==COMP_IMU_READY);
    assert(b->reg[0x56]==0x4Fu&&b->reg[0x57]==4u&&b->reg[0x58]==0x84u&&b->reg[0x59]==4u);
    assert(b->reg[0x5A]==0x7Fu&&b->reg[0x5B]==0x82u&&b->reg[0x5E]==0u&&b->reg[0x0D]==3u);
}
int main(void)
{
    comp_lsm6dso_t imu;bus_t b;comp_imu_sample_t sample={0};start(&imu,&b);
    assert(comp_lsm6dso_set_recording_taps(&imu,true)&&b.reg[0x10]==0x68u&&b.reg[0x11]==0x30u&&b.reg[0x5E]==8u);
    assert(!comp_lsm6dso_set_idle(&imu,true,12u));b.taps_read=0u;
    /* No sample must leave the chip's latched gesture for the next real sample. */
    b.reg[0x1C]=COMP_LSM6DSO_DOUBLE_TAP;imu.event_irq_pending=true;
    assert(comp_lsm6dso_poll(&imu,20u,&sample)==COMP_IMU_NO_SAMPLE&&b.taps_read==0u&&imu.tap_source==0u);
    b.reg[0x1E]=3u;
    assert(comp_lsm6dso_poll(&imu,30u,&sample)==COMP_IMU_SAMPLE&&imu.tap_source==0x50u&&b.taps_read==1u);
    assert(comp_lsm6dso_poll(&imu,40u,&sample)==COMP_IMU_SAMPLE&&imu.tap_source==0u&&b.taps_read==1u);
    b.reg[0x1C]=0x60u;imu.event_irq_pending=true;assert(comp_lsm6dso_poll(&imu,41u,&sample)==COMP_IMU_SAMPLE);
    assert(imu.tap_reads==2u&&imu.tap_counts==0x00010001u);
    b.reg[0x1C]=0x10u;imu.event_irq_pending=true;assert(comp_lsm6dso_poll(&imu,42u,&sample)==COMP_IMU_SAMPLE&&imu.tap_counts==0x00010001u);
    imu.tap_reads=UINT32_MAX;imu.tap_counts=UINT32_MAX;b.reg[0x1C]=0x70u;imu.event_irq_pending=true;
    assert(comp_lsm6dso_poll(&imu,43u,&sample)==COMP_IMU_SAMPLE&&imu.tap_reads==UINT32_MAX&&imu.tap_counts==UINT32_MAX);
    b.reg[0x1E]=0u;
    assert(comp_lsm6dso_poll(&imu,50u,&sample)==COMP_IMU_NO_SAMPLE&&imu.tap_source==0u);
    assert(comp_lsm6dso_set_recording_taps(&imu,false)&&b.reg[0x10]==0x38u&&b.reg[0x5E]==0u);
    assert(imu.tap_reads==UINT32_MAX&&imu.tap_counts==UINT32_MAX);
    assert(comp_lsm6dso_set_idle(&imu,true,12u)&&b.reg[0x10]==0x18u&&b.reg[0x11]==0u&&b.reg[0x0D]==0u);
    b.reg[0x1E]=1u;b.reg[0x1C]=0x50u;
    assert(comp_lsm6dso_poll(&imu,60u,&sample)==COMP_IMU_SAMPLE&&imu.tap_source==0u);
    assert(comp_lsm6dso_set_recording_taps(&imu,true)&&b.reg[0x10]==0x68u&&b.reg[0x11]==0x30u&&b.reg[0x0D]==0u&&b.reg[0x1C]==0u);
    b.reg[0x1E]=3u;b.fail_read=0x1C;imu.event_irq_pending=true;unsigned samples=imu.samples;
    assert(comp_lsm6dso_poll(&imu,70u,&sample)==COMP_IMU_IO_ERROR&&imu.tap_source==0u&&imu.samples==samples);
    b.fail_read=-1;assert(!comp_lsm6dso_recover(&imu,80u));assert(comp_lsm6dso_recover(&imu,1080u));
    b.reg[0x12]=0u;b.reg[0x56]=0u;b.reg[0x5E]=0u;
    assert(comp_lsm6dso_poll(&imu,1090u,&sample)==COMP_IMU_NO_SAMPLE&&imu.state==COMP_IMU_READY&&b.reg[0x56]==0x4Fu&&b.reg[0x5E]==0u&&!imu.recording_taps);
    assert(comp_lsm6dso_stop(&imu)&&b.reg[0x5E]==0u&&b.reg[0x0D]==0u&&b.reg[0x10]==0u&&b.reg[0x11]==0u&&imu.tap_source==0u);
    /* Pointer ownership changes only gyro ODR; recording/idle restore exactly. */
    start(&imu,&b);
    assert(comp_lsm6dso_set_idle(&imu,true,2000u));
    assert(comp_lsm6dso_set_pointer(&imu,true)&&imu.pointer_mode&&!imu.idle_accel_only);
    assert(b.reg[0x10]==0x68u&&b.reg[0x11]==0x40u&&b.reg[0x5E]==8u);
    assert(!comp_lsm6dso_set_idle(&imu,true,2001u));
    assert(comp_lsm6dso_set_pointer(&imu,false)&&!imu.pointer_mode&&b.reg[0x11]==0x30u);
    assert(imu.recording_taps); /* Recording keeps417Hz accel /52Hz gyro. */
    assert(comp_lsm6dso_set_recording_taps(&imu,false));
    assert(comp_lsm6dso_set_idle(&imu,true,2002u)&&b.reg[0x11]==0u);
    assert(comp_lsm6dso_set_pointer(&imu,false)&&b.reg[0x11]==0u);
    assert(comp_lsm6dso_set_pointer(&imu,true));b.corrupt=0x11;
    assert(!comp_lsm6dso_set_pointer(&imu,false)&&imu.state==COMP_IMU_FAULT);
    start(&imu,&b);assert(!comp_lsm6dso_set_pointer_single_taps(&imu,true));
    assert(comp_lsm6dso_set_pointer(&imu,true));
    assert(comp_lsm6dso_set_pointer_single_taps(&imu,true));
    assert(b.reg[0x5B]==0x02u&&b.reg[0x5E]==0x40u&&b.reg[0x10]==0x68u&&b.reg[0x11]==0x40u);
    b.reg[0x1E]=3u;b.reg[0x1C]=0x6Cu;imu.event_irq_pending=true;
    unsigned tap_reads=b.taps_read;
    assert(comp_lsm6dso_poll(&imu,100u,&sample)==COMP_IMU_SAMPLE&&imu.tap_source==0x6Cu&&b.taps_read==tap_reads+1u);
    assert(comp_lsm6dso_poll(&imu,110u,&sample)==COMP_IMU_SAMPLE&&imu.tap_source==0u&&b.taps_read==tap_reads+1u);
    b.reg[0x1C]=0x64u;imu.event_irq_pending=true;
    assert(comp_lsm6dso_poll(&imu,180u,&sample)==COMP_IMU_SAMPLE&&imu.tap_source==0x64u);
    assert(comp_lsm6dso_set_pointer(&imu,false)&&!imu.pointer_single_taps&&b.reg[0x5B]==0x82u&&b.reg[0x5E]==8u);
    assert(comp_lsm6dso_set_recording_taps(&imu,false)&&b.reg[0x5E]==0u);
    puts("PASS opt-in pointer single tap: source axis/sign retained once per impact, fast second tap separate, pointer exit restores recording double-tap engine");
    /* Both real pointer wire modes must select the same ST single-tap
     * registers and forward each latched source to the reliable queue once. */
    const uint8_t wire_options[]={COMP_INPUT_POINTER_V4,
        COMP_INPUT_POINTER_V4|COMP_INPUT_POINTER_RAW,
        COMP_INPUT_POINTER_V4|COMP_INPUT_POINTER_FUSED_RATES};
    for(unsigned mode=0u;mode<3u;++mode) {
        comp_recorder_input_t input={0};start(&imu,&b);
        assert(comp_input_mode(&input,COMP_INPUT_POINTER,
            wire_options[mode],false,false));
        assert(comp_input_pointer_single_taps(&input));
        assert(comp_lsm6dso_set_pointer(&imu,true));
        assert(comp_lsm6dso_set_pointer_single_taps(&imu,comp_input_pointer_single_taps(&input)));
        assert(b.reg[0x5B]==0x02u&&b.reg[0x5E]==0x40u);
        for(unsigned tap=0u;tap<2u;++tap) {
            b.reg[0x1E]=3u;b.reg[0x1C]=0x64u;imu.event_irq_pending=true;
            assert(comp_lsm6dso_poll(&imu,100u+tap*150u,&sample)==COMP_IMU_SAMPLE);
            assert(comp_input_pointer_contact(&input,&imu.tap_source,sample.timestamp_ms));
            const comp_pointer_event_t *edge=comp_input_pointer_event(&input);
            assert(edge&&edge->events==COMP_INPUT_CLICK&&edge->reserved==0x64u);
            assert(!comp_input_pointer_contact(&input,&imu.tap_source,sample.timestamp_ms));
            comp_input_pointer_ack(&input,edge->sequence);assert(input.pointer_count==0u);
        }
        assert(input.flick_sample_ms==2u);
        input.flags|=COMP_INPUT_HELD;imu.tap_source=0x64u;
        assert(comp_input_pointer_contact(&input,&imu.tap_source,500u));
        const comp_pointer_event_t *held=comp_input_pointer_event(&input);
        assert(imu.tap_source==0u&&input.pointer_count==1u&&held&&held->events==COMP_INPUT_CLICK&&(held->flags&COMP_INPUT_HELD));
        assert(!comp_input_pointer_contact(&input,&imu.tap_source,500u));
        comp_input_pointer_ack(&input,held->sequence);assert(input.pointer_count==0u);
        input.flags=0u;assert(comp_input_mode(&input,COMP_INPUT_RECORDER,0u,false,false));
        assert(!comp_input_pointer_single_taps(&input));
        assert(comp_lsm6dso_set_pointer_single_taps(&imu,false));
        assert(b.reg[0x5B]==0x82u&&b.reg[0x5E]==8u);
        assert(comp_input_motion(&input,COMP_MOTION_DOUBLE_TAP,&sample,0u,true)==COMP_INPUT_MARK);
    }
    puts("PASS fused/raw pointer taps reach reliable queue once, including held-key taps for host clutch; host owns drag/click decision; recorder double-tap marking retained");
    /* Configuration failures do not report READY with a missing gesture route. */
    for(unsigned i=0u;i<3u;i++) {
        start(&imu,&b);assert(comp_lsm6dso_start(&imu,read_reg,write_reg,&b,2000u));b.reg[0x12]=0u;
        if(i==0u)b.fail_write=0x56;else if(i==1u)b.corrupt=0x58;else b.fail_read=0x5E;
        assert(comp_lsm6dso_poll(&imu,2010u,&sample)==COMP_IMU_IO_ERROR&&imu.state==COMP_IMU_FAULT&&imu.tap_source==0u);
    }
    puts("PASS LSM6DSO double-tap: verified417Hz recording accel/52Hz gyro,52Hz awake/12.5Hz idle, latched event once, no-sample retention, recovery and I/O failure");
    return 0;
}
