#include "recorder_input.h"
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
    puts("SOFTWARE_ONLY: real enclosure thresholds, wake, audio first-word and Mac insertion not qualified");
    return 0;
}
