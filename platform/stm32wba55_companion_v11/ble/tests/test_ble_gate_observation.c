#include "../ble_gate_observation.h"
#include "../ble_tx_gate.h"
#include <assert.h>
int main(void)
{
    comp_v11_ble_gate_observation_t p={0};
    comp_v11_ble_tx_gate_t gate={0};
    comp_gate_observation_start(&p);
    comp_gate_observation_origin(&p,false);
    comp_gate_observation_origin(&p,true);
    comp_gate_observation_open(&p,100u);
    comp_gate_observation_close(&p,1u,150u);
    comp_gate_observation_close(&p,2u,180u); /* no second charge for same wake */
    comp_gate_observation_open(&p,200u);
    comp_gate_observation_close(&p,2u,230u);
    comp_gate_observation_open(&p,300u);
    comp_gate_observation_close(&p,3u,2300u);
    assert(p.origins==UINT32_C(0x00010001));
    assert(p.wait_us[0]==50u && p.wait_us[1]==30u && p.wait_us[2]==2000u);
    assert(p.wakes[0]==1u && p.wakes[1]==1u && p.wakes[2]==1u);
    comp_gate_observation_radio_end(&p,8u,false);
    comp_gate_observation_radio_end(&p,0u,false);
    comp_gate_observation_radio_end(&p,1u,true);
    assert(p.radio_ends==UINT32_C(0x00010001));
    assert(p.flags==(GATE_OBS_MEASURED|GATE_OBS_RADIO_API_CENSORED));

    /* A callback within the original ACI can precede its resource failure.
     * Keep the actual gate's wake: there is no post-return wait to charge. */
    comp_gate_observation_start(&p);
    comp_v11_ble_tx_gate_begin(&gate,20u,6u);
    comp_gate_observation_close(&p,1u,20001u);
    comp_v11_ble_tx_gate_available(&gate);
    comp_gate_observation_origin(&p,true);
    comp_v11_ble_tx_gate_end(&gate,true);
    if(gate.waiting)comp_gate_observation_open(&p,20002u);
    assert(!(p.flags&GATE_OBS_ACTIVE) && p.origins==UINT32_C(0x00010000));
    assert(p.wakes[0]==0u && p.wait_us[0]==0u);

    /* Timestamp rollover is valid; backwards time, canceled ownership and
     * overflowing fields stay explicit rather than silently becoming zero. */
    comp_gate_observation_open(&p,UINT32_MAX-5u);
    comp_gate_observation_close(&p,3u,9u);
    assert(p.wait_us[2]==15u);
    comp_gate_observation_open(&p,30u);
    comp_gate_observation_close(&p,1u,29u);
    assert(p.flags&GATE_OBS_BACKWARD);
    comp_gate_observation_open(&p,40u);
    comp_gate_observation_close(&p,0u,50u);
    assert(p.flags&GATE_OBS_CENSORED);
    comp_gate_observation_start(&p);
    assert(p.origins==0u && p.radio_ends==0u && p.wait_us[2]==0u);
    p.origins=UINT32_C(0x1234ffff);
    comp_gate_observation_origin(&p,false);
    assert(p.origins==UINT32_C(0x1234ffff) && (p.flags&GATE_OBS_OVERFLOW));
    p.wait_us[0]=UINT32_MAX;
    comp_gate_observation_open(&p,60u);
    comp_gate_observation_close(&p,1u,61u);
    assert(p.wait_us[0]==UINT32_MAX && p.wakes[0]==0u);
    return 0;
}
