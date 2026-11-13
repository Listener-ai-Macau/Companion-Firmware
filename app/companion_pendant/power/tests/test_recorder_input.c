#include "recorder_input.h"
#include "imu_pointer_wire.h"
#include <assert.h>
#include <stdio.h>

static uint8_t physical(comp_wba_button_t *b,uint32_t down,uint32_t up)
{
    comp_wba_button_edges_t e={down,up,COMP_WBA_BUTTON_EDGE_DOWN|COMP_WBA_BUTTON_EDGE_UP,false};
    return comp_wba_button_poll_transitions(b,&e,up+30u);
}
int main(void)
{
    comp_wba_button_t b;comp_wba_button_init(&b,false,0u);
    assert(physical(&b,100u,110u)==0u);
    uint8_t key=physical(&b,200u,280u);
    assert((key&(COMP_WBA_BUTTON_DOWN|COMP_WBA_BUTTON_UP))==(COMP_WBA_BUTTON_DOWN|COMP_WBA_BUTTON_UP));
    comp_recorder_input_t s={0};
    assert(comp_input_key(&s,key,false)==COMP_INPUT_START);
    assert(comp_input_key(&s,physical(&b,400u,480u),true)==COMP_INPUT_STOP);
    comp_wba_button_init(&b,false,UINT32_MAX-200u);
    assert(comp_input_key(&s,physical(&b,UINT32_MAX-50u,40u),false)==COMP_INPUT_START);
    comp_wba_button_init(&b,true,0u);
    comp_wba_button_edges_t up={0u,100u,COMP_WBA_BUTTON_EDGE_UP,false};
    assert(!(comp_wba_button_poll_transitions(&b,&up,130u)&COMP_WBA_BUTTON_UP));
    puts("PASS actual IRQ replay: bounce ignored, delayed complete clicks and tick wrap retained, held boot key never starts recording");

    assert(comp_input_mode(&s,COMP_INPUT_DICTATION,7u,false,false));
    assert(comp_input_key(&s,key,false)==(COMP_INPUT_START|COMP_INPUT_STOP));
    assert(!comp_input_mode(&s,COMP_INPUT_RECORDER,0u,true,false));
    assert(comp_input_key(&s,COMP_WBA_BUTTON_DOWN,false)==COMP_INPUT_START);
    s.record_token=91u;
    assert(comp_input_motion(&s,COMP_MOTION_DOUBLE_TAP,NULL,0u,true)==0u);
    assert(comp_input_motion(&s,COMP_MOTION_SHAKE,NULL,0u,true)==(COMP_INPUT_CANCEL|COMP_INPUT_STOP));
    assert(comp_input_motion(&s,COMP_MOTION_SHAKE,NULL,0u,true)==0u);
    assert(comp_input_key(&s,COMP_WBA_BUTTON_UP,true)==0u);
    assert(comp_input_motion(&s,COMP_MOTION_DOUBLE_TAP,NULL,0u,false)==COMP_INPUT_UNDO_LAST);
    assert(comp_input_key(&s,COMP_WBA_BUTTON_DOWN,false)==COMP_INPUT_START);s.record_token=92u;
    comp_input_connection(&s,false);assert(s.mode==COMP_INPUT_DICTATION);
    assert(comp_input_key(&s,COMP_WBA_BUTTON_UP,true)==COMP_INPUT_STOP&&s.mode==COMP_INPUT_RECORDER);
    puts("PASS desktop lifecycle: mode cannot change while active, cancelled hold stops once, disconnect preserves capture until physical release then returns to recorder");

    comp_wba_button_init(&b,false,0u);
    comp_wba_button_edges_t down={100u,0u,COMP_WBA_BUTTON_EDGE_DOWN,true};
    assert(!(comp_wba_button_poll_transitions(&b,&down,100u)&COMP_WBA_BUTTON_DOWN));
    down.flags=0u;assert(comp_wba_button_poll_transitions(&b,&down,130u)&COMP_WBA_BUTTON_DOWN);
    assert(comp_wba_button_poll_transitions(&b,&down,100000u)==0u);
    up.up_ms=100100u;assert(comp_wba_button_poll_transitions(&b,&up,100130u)&COMP_WBA_BUTTON_UP);
    puts("PASS long desktop hold: no recorder toggle or power-off after 100 seconds; physical release is retained");

    assert(comp_input_mode(&s,COMP_INPUT_DICTATION,COMP_INPUT_FLICK,false,false));
    assert(comp_input_key(&s,COMP_WBA_BUTTON_DOWN,false)==COMP_INPUT_START);s.record_token=93u;
    comp_imu_sample_t sample={0};sample.gyro_mdps[0]=-150000;sample.timestamp_ms=1000u;
    assert(comp_input_motion(&s,0u,&sample,0u,true)==0u);
    for(unsigned i=0u;i<3u;++i) {
        sample.timestamp_ms+=20u;assert(comp_input_motion(&s,0u,&sample,0u,true)==0u);
        for(unsigned j=0u;j<20u;++j)assert(comp_input_motion(&s,0u,&sample,0u,true)==0u);
    }
    sample.timestamp_ms+=20u;
    assert(comp_input_motion(&s,0u,&sample,0u,true)==(COMP_INPUT_SUBMIT|COMP_INPUT_STOP));
    assert(comp_input_key(&s,COMP_WBA_BUTTON_UP,true)==0u);
    assert(comp_input_mode(&s,COMP_INPUT_RECORDER,0u,false,false));
    assert(comp_input_motion(&s,COMP_MOTION_DOUBLE_TAP,NULL,0u,true)==COMP_INPUT_MARK);
    assert(comp_input_motion(&s,COMP_MOTION_DOUBLE_TAP,NULL,0u,false)==0u);
    comp_input_note(&s,COMP_INPUT_MARK,123u);assert(s.sequence==1u&&s.event_ms==123u&&s.events==COMP_INPUT_MARK);
    s.sequence=UINT32_MAX;comp_input_note(&s,COMP_INPUT_WAKE,124u);assert(s.sequence==1u);
    puts("PASS shared IMU dispatch: recorder tap marks, idle cannot start, optional flick requires fresh coherent angular samples; duplicate samples do not integrate");
    assert(comp_input_mode(&s,COMP_INPUT_POINTER,0u,false,false));
    assert(comp_input_key(&s,COMP_WBA_BUTTON_DOWN,false)==0u);
    assert(s.flags&COMP_INPUT_HELD);
    assert(comp_input_motion(&s,255u,&sample,COMP_MOTION_TILT_RIGHT,false)==0u);
    assert(s.flick_sample_ms==1u);
    assert(comp_input_key(&s,COMP_WBA_BUTTON_DOWN,false)==0u&&s.flick_sample_ms==1u);
    assert(comp_input_key(&s,COMP_WBA_BUTTON_UP,false)==0u&&!(s.flags&COMP_INPUT_HELD));
    assert(!comp_input_mode(&s,4u,0u,false,false));
    assert(!comp_input_mode(&s,COMP_INPUT_POINTER,0u,true,false));
    comp_input_connection(&s,false);assert(s.mode==COMP_INPUT_RECORDER);
    assert(comp_input_mode(&s,COMP_INPUT_POINTER,0u,false,false));
    assert(comp_input_key(&s,COMP_WBA_BUTTON_DOWN,false)==0u);
    comp_input_connection(&s,false);
    assert(s.mode==COMP_INPUT_POINTER&&(s.flags&COMP_INPUT_DETACHED));
    assert(comp_input_key(&s,COMP_WBA_BUTTON_UP,false)==0u&&s.mode==COMP_INPUT_RECORDER);
    sample=(comp_imu_sample_t){.timestamp_ms=0xfffffff0u,.accel_mg={1,-2,1000},.gyro_mdps={8750,-250000,500000}};
    uint8_t packet[32];comp_imu_pointer_packet(&sample,7u,true,0u,false,packet);
    assert(!memcmp(packet,"CIM1",4u)&&packet[4]==1u&&packet[5]==3u&&packet[6]==1u);
    assert(packet[22]==0x6bu&&packet[23]==3u&&packet[24]==0x58u&&packet[25]==0x9eu);
    assert(packet[26]==0xffu&&packet[27]==0x7fu);
    comp_imu_pointer_packet(&sample,7u,true,255u,true,packet);assert(packet[7]==255u&&packet[4]==2u);
    printf("CIM2_GOLDEN ");for(unsigned i=0;i<32u;++i)printf("%02x",packet[i]);puts("");
    comp_imu_pointer_packet(&sample,7u,true,0u,false,packet);
    printf("CIM1_GOLDEN ");for(unsigned i=0;i<32u;++i)printf("%02x",packet[i]);puts("");
    comp_imu_fused_sample_t fused={.gravity_q14={0,8192,14189},.gyro_mdps={8750,-250000,500000},.timestamp_ms=0xfffffff0u,.ready=true};
    comp_imu_pointer_fused_packet(&fused,7u,true,255u,packet);
    assert(packet[4]==3u&&packet[6]==3u);
    printf("CIM3_GOLDEN ");for(unsigned i=0;i<32u;++i)printf("%02x",packet[i]);puts("");
    comp_imu_pointer_aim_packet(&fused,7u,true,255u,12.34f,-23.45f,packet);
    assert(packet[4]==4u&&packet[16]==0xd2u&&packet[17]==4u);
    printf("CIM4_GOLDEN ");for(unsigned i=0;i<32u;++i)printf("%02x",packet[i]);puts("");
    fused=(comp_imu_fused_sample_t){.gravity_q14={0,0,16384},.gyro_mdps={0,0,90000},.ready=true};
    float heading=0.0f;unsigned delivered=0u;
    for(unsigned i=1u;i<=100u;++i){
        heading=comp_imu_pointer_heading(heading,comp_imu_pointer_yaw(&fused),10u);
        /* Radio cannot accept the middle80 samples. Heading still advances. */
        if(i<=10u||i>90u){comp_imu_pointer_aim_packet(&fused,i,false,0u,heading,90.0f,packet);++delivered;}
    }
    assert(delivered==20u&&heading>89.99f&&heading<90.01f&&packet[16]==0x28u&&packet[17]==0x23u);
    assert(comp_imu_pointer_heading(179.0f,100.0f,100u)==-176.0f);
    assert(comp_input_mode(&s,COMP_INPUT_POINTER,COMP_INPUT_POINTER_V4,false,false));
    assert(!comp_input_mode(&s,COMP_INPUT_DICTATION,COMP_INPUT_POINTER_V4,false,false));
    uint16_t edge_events=comp_input_key(&s,COMP_WBA_BUTTON_DOWN,false);
    assert(edge_events==COMP_INPUT_DOWN);comp_input_note(&s,edge_events,200u);
    uint32_t down_sequence=s.sequence;
    edge_events=comp_input_key(&s,COMP_WBA_BUTTON_UP,false);
    assert(edge_events==COMP_INPUT_UP);comp_input_note(&s,edge_events,280u);
    const comp_pointer_event_t *edge=comp_input_pointer_event(&s);
    assert(edge&&edge->sequence==down_sequence&&edge->event_ms==200u&&(edge->flags&COMP_INPUT_HELD));
    comp_input_pointer_ack(&s,down_sequence+1u);assert(s.pointer_count==2u); /* Cannot ACK out of order. */
    s.events=0u;assert(comp_input_pointer_event(&s)); /* publish is not consumption */
    comp_input_pointer_ack(&s,down_sequence);edge=comp_input_pointer_event(&s);
    assert(edge&&edge->event_ms==280u&&!(edge->flags&COMP_INPUT_HELD));
    comp_input_pointer_ack(&s,down_sequence);assert(s.pointer_count==1u); /* repeated ACK */
    comp_input_pointer_ack(&s,edge->sequence);assert(!comp_input_pointer_event(&s));
    for(unsigned i=0;i<9u;++i)comp_input_note(&s,COMP_INPUT_CLICK,300u+i);
    edge=comp_input_pointer_event(&s);assert(s.pointer_count==1u&&(edge->events&COMP_INPUT_OVERFLOW)&&(edge->events&COMP_INPUT_UP));
    comp_input_connection(&s,false);assert(!s.pointer_count);
    assert(!comp_input_mode(&s,COMP_INPUT_POINTER,COMP_INPUT_POINTER_RAW,false,false));
    assert(comp_input_mode(&s,COMP_INPUT_POINTER,COMP_INPUT_POINTER_V4|COMP_INPUT_POINTER_RAW,false,false));
    assert(!comp_input_mode(&s,COMP_INPUT_RECORDER,24u,false,false));
    assert(!comp_input_mode(&s,COMP_INPUT_POINTER,COMP_INPUT_POINTER_FUSED_RATES,false,false));
    assert(!comp_input_mode(&s,COMP_INPUT_POINTER,COMP_INPUT_POINTER_V4|COMP_INPUT_POINTER_RAW|COMP_INPUT_POINTER_FUSED_RATES,false,false));
    assert(comp_input_mode(&s,COMP_INPUT_POINTER,COMP_INPUT_POINTER_V4|COMP_INPUT_POINTER_FUSED_RATES,false,false));
    assert(comp_input_pointer_v4(&s));
    edge_events=comp_input_key(&s,COMP_WBA_BUTTON_DOWN,false);assert(edge_events==COMP_INPUT_DOWN);
    comp_input_note(&s,edge_events,500u);assert(comp_input_pointer_event(&s));
    comp_imu_pointer_fused_packet(&fused,9u,true,0u,packet);assert(packet[4]==3u&&packet[6]==3u);
    comp_imu_pointer_pack(sample.timestamp_ms,8u,false,1u,5u,true,sample.accel_mg,sample.gyro_mdps,packet);
    assert(packet[4]==5u&&packet[6]==2u&&packet[16]==1u&&packet[18]==0xfeu&&packet[20]==0xe8u);
    printf("CIM5_RAW_GOLDEN ");for(unsigned i=0;i<32u;++i)printf("%02x",packet[i]);puts("");
    puts("PASS Watch device heading survives80 missing aim samples; reliable control head retries, ACK order/duplicate, bounded overflow, mode isolation and legacy schemas retained");
    puts("PASS pointer mode: keys/motion never start MIC; disconnect restores recorder; timestamp/centidegree precision and bounded saturation");
    puts("SOFTWARE_ONLY: real enclosure thresholds, wake, audio first-word and Mac insertion not qualified");
    return 0;
}
