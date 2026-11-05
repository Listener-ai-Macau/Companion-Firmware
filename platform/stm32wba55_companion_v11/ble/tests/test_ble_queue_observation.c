#include "../ble_queue_observation.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    comp_v11_ble_queue_observation_t q={0};
    comp_v11_ble_queue_start(&q,100u);
    assert(comp_v11_ble_queue_begin(&q,0u,true));
    comp_v11_ble_queue_complete(&q,0u,101u); /* nested before ACI returns */
    comp_v11_ble_queue_finish(&q,true,102u);
    assert(q.accepted==1 && q.completed==1 && q.nested==1 && q.unmatched==0 && q.empty_ms==2);
    assert(comp_v11_ble_queue_begin(&q,0u,false));comp_v11_ble_queue_finish(&q,false,104u);
    assert(q.accepted==1 && comp_v11_ble_queue_depth(&q)==0 && q.empty_ms==4);
    assert(comp_v11_ble_queue_begin(&q,0u,true));comp_v11_ble_queue_finish(&q,true,105u);
    assert(comp_v11_ble_queue_begin(&q,0u,true));comp_v11_ble_queue_finish(&q,true,106u);
    assert(comp_v11_ble_queue_begin(&q,1u,false));comp_v11_ble_queue_finish(&q,true,107u);
    comp_v11_ble_queue_complete(&q,0u,110u);comp_v11_ble_queue_complete(&q,1u,111u);
    comp_v11_ble_queue_stop(&q,112u);assert(q.running);
    comp_v11_ble_queue_complete(&q,0u,115u);
    assert(!q.running && q.completed==4 && q.accepted==4 && q.data_accepted==3);
    assert(q.peak==3 && q.queued_ms==18 && q.empty_ms==5 && q.elapsed_ms==15);
    comp_v11_ble_queue_tick(&q,1000u);assert(q.elapsed_ms==15);
    /* Keep prior reply inventory on a new batch, and handle tick wrap. */
    assert(comp_v11_ble_queue_begin(&q,1u,false));comp_v11_ble_queue_finish(&q,true,1001u);
    comp_v11_ble_queue_start(&q,UINT32_MAX-1u);assert(q.pending[1]==1 && q.accepted==0);
    comp_v11_ble_queue_complete(&q,1u,1u);assert(q.queued_ms==3 && q.completed==1);
    assert(comp_v11_ble_queue_begin(&q,0u,true));comp_v11_ble_queue_disconnect(&q,2u);
    comp_v11_ble_queue_finish(&q,true,3u);assert(q.pending[0]==0 && !q.running);
    comp_v11_ble_queue_start(&q,10u);assert(comp_v11_ble_queue_begin(&q,0u,true));
    comp_v11_ble_queue_complete(&q,0u,11u);comp_v11_ble_queue_finish(&q,false,12u);
    assert(q.unmatched==1 && q.accepted==0 && q.completed==0);
    puts("PASS scoped queue inventory, nested ACI completion, failure, drain, reset and wrap");return 0;
}
