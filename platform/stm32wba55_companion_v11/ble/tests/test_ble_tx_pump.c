#include "ble_tx_pump.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

enum { SEND = 1u << 13, RADIO = 1u << 1, WAKE = 1u };
static comp_v11_ble_tx_pump_t pump;
static comp_v11_ble_tx_gate_t gate;
static comp_wba_recording_transfer_t transfer;
static uint32_t now, started, calls, sent, credits, radio_calls, round_trip;
static uint32_t calls_at_radio, elapsed_per_packet, first_radio_sent;
static uint8_t depth;
static bool allowed, yielded, wake_inside_call, radio_nested, in_poll;

static uint32_t clock_ms(void *context) {(void)context;return now;}
static void queue_send(void)
{
    comp_v11_ble_tx_pump_schedule(&transfer,&gate,allowed,now,SEND,1u);
}
static void pool_event(void)
{
    comp_v11_ble_tx_gate_available(&gate);
    queue_send();
}
static void send_task(void)
{
    comp_v11_ble_tx_pump_poll(&pump,&transfer,&gate,allowed,depth,
        clock_ms,NULL,SEND,1u);
}
static void radio_task(void)
{
    ++radio_calls;calls_at_radio=calls;
    if(radio_calls==1u)first_radio_sent=sent;
    if(radio_nested) {
        radio_nested=false;
        queue_send();
        UTIL_SEQ_Run(SEND); /* Nested SDK task must not enter the transfer. */
    }
    UTIL_SEQ_SetEvt(WAKE);
}
void UTIL_SEQ_PreTask(uint32_t id) {(void)id;++depth;}
void UTIL_SEQ_PostTask(uint32_t id)
{
    (void)id;assert(depth>0u);--depth;
    /* The existing product owner yields only after the outer task returns. */
    if(pump.foreground_run && !depth && now-started>=2u) {
        UTIL_SEQ_PauseTask(UTIL_SEQ_DEFAULT);yielded=true;
    }
}

/* Radio queue boundary only is mocked. The production pump and ST's real
 * sequencer (including round-robin, pause and nested WaitEvt) are exercised. */
comp_wba_recording_transfer_state_t comp_wba_recording_transfer_poll_budget(
    comp_wba_recording_transfer_t *t, comp_wba_recording_transfer_clock_fn clock,
    void *context, const comp_wba_recording_transfer_budget_t *budget)
{
    assert(!in_poll && depth==1u && pump.foreground_run && !gate.in_call);
    in_poll=true;++calls;
    const uint32_t turn_started=clock(context);
    for(uint32_t packet=0u;packet<budget->max_packets;++packet) {
        if(packet && clock(context)-turn_started>=budget->max_elapsed_ms)break;
        now+=elapsed_per_packet;
        comp_v11_ble_tx_gate_begin(&gate,now,12u);
        if(wake_inside_call) {
            wake_inside_call=false;
            credits=8u;pool_event();
            UTIL_SEQ_SetTask(RADIO,0u);
            UTIL_SEQ_WaitEvt(WAKE);
            ++round_trip;
            comp_v11_ble_tx_gate_end(&gate,true);
            t->state=COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED;
            break;
        } else if(credits==0u) {
            comp_v11_ble_tx_gate_end(&gate,true);
            t->state=COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED;
            break;
        } else {
            --credits;++sent;t->next_offset+=224u;--t->remaining;
            comp_v11_ble_tx_gate_end(&gate,false);
            t->state=t->remaining?COMP_WBA_RECORDING_TRANSFER_ACTIVE:COMP_WBA_RECORDING_TRANSFER_COMPLETE;
            if(!t->remaining)break;
            UTIL_SEQ_SetTask(RADIO,0u);
        }
    }
    in_poll=false;return t->state;
}
static void setup(uint32_t packets, uint32_t queue_credits)
{
    UTIL_SEQ_Init();
    UTIL_SEQ_ResumeTask(UTIL_SEQ_DEFAULT);
    memset(&pump,0,sizeof(pump));memset(&gate,0,sizeof(gate));
    memset(&transfer,0,sizeof(transfer));
    transfer.state=COMP_WBA_RECORDING_TRANSFER_ACTIVE;transfer.connected=true;
    transfer.remaining=packets;credits=queue_credits;
    now=started=calls=sent=radio_calls=round_trip=calls_at_radio=elapsed_per_packet=first_radio_sent=0u;
    depth=0u;allowed=true;yielded=wake_inside_call=radio_nested=in_poll=false;
    UTIL_SEQ_RegTask(SEND,UTIL_SEQ_RFU,send_task);
    UTIL_SEQ_RegTask(RADIO,UTIL_SEQ_RFU,radio_task);
}
static void foreground_run(void)
{
    if(yielded) {UTIL_SEQ_ResumeTask(UTIL_SEQ_DEFAULT);yielded=false;}
    queue_send();started=now;pump.foreground_run=true;
    UTIL_SEQ_Run(UTIL_SEQ_DEFAULT);
    pump.foreground_run=false;
}
int main(void)
{
    setup(2u,8u);queue_send();UTIL_SEQ_SetTask(RADIO,0u);foreground_run();
    assert(first_radio_sent==0u && sent==2u && depth==0u);
    puts("PASS already-ready radio runs before priority1 file preparation");

    setup(6u,8u);foreground_run();
    assert(sent==6u && transfer.next_offset==1344u);
    assert(radio_calls>0u && first_radio_sent>0u && first_radio_sent<=4u && depth==0u);
    assert(!UTIL_SEQ_IsSchedulableTask(SEND));
    puts("PASS stopped-file burst refills queue with bounded radio round-robin");

    setup(6u,2u);foreground_run();
    assert(sent==2u && gate.waiting);
    const uint32_t blocked_calls=calls;
    foreground_run();assert(calls==blocked_calls);
    assert(!UTIL_SEQ_IsSchedulableTask(SEND));
    credits=4u;pool_event();foreground_run();
    assert(sent==6u && transfer.next_offset==1344u && !gate.waiting);
    puts("PASS full pool stops; pool event resumes unchanged cursor");

    setup(2u,0u);foreground_run();assert(calls==1u);
    now=3u;foreground_run();assert(calls==1u);
    now=4u;credits=2u;foreground_run();assert(sent==2u);
    puts("PASS missed event uses the connection-derived 4ms deadline");

    setup(3u,0u);wake_inside_call=true;foreground_run();
    assert(round_trip==1u && sent==3u && !gate.waiting);
    puts("PASS pool wake inside ACI wait retained without reentrant send");

    setup(2u,8u);now=4u;queue_send();UTIL_SEQ_SetTask(RADIO,0u);
    UTIL_SEQ_WaitEvt(WAKE);assert(calls==0u && sent==0u && !yielded);
    foreground_run();assert(sent==2u);
    setup(2u,8u);radio_nested=true;UTIL_SEQ_SetTask(RADIO,0u);
    started=now;pump.foreground_run=true;UTIL_SEQ_Run(RADIO);
    pump.foreground_run=false;assert(calls==0u);
    foreground_run();assert(sent==2u);
    puts("PASS external and nested SDK runs cannot take the transfer owner");

    setup(6u,8u);elapsed_per_packet=1u;foreground_run();
    assert(sent==2u && yielded && transfer.state==COMP_WBA_RECORDING_TRANSFER_ACTIVE);
    foreground_run();assert(sent==4u && yielded);
    foreground_run();assert(sent==6u);
    setup(1u,8u);allowed=false;foreground_run();assert(calls==0u);
    allowed=true;transfer.snapshot_live=true;foreground_run();assert(calls==0u);
    transfer.snapshot_live=false;transfer.connected=false;foreground_run();assert(calls==0u);
    puts("PASS bounded owner yields and IO/live/disconnect exclusions preserved");
    return 0;
}
