#include "../ble_credit_wakeup.h"
#include "../ble_tx_gate.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    assert(comp_credit_wakeup_transport_queued(true,true,1u));
    assert(!comp_credit_wakeup_transport_queued(true,true,0u)); /* ACI success is a different API. */
    assert(!comp_credit_wakeup_transport_queued(false,true,1u));
    assert(!comp_credit_wakeup_transport_queued(true,false,1u));

    comp_v11_ble_credit_wakeup_t s={0};
    comp_v11_ble_tx_gate_t gate={0};
    comp_credit_wakeup_reset(&s,7u);
    comp_v11_ble_tx_gate_begin(&gate,100u,6u);
    comp_v11_ble_tx_gate_end(&gate,true);
    comp_credit_wakeup_note(&s,7u);
    assert(!comp_credit_wakeup_take(&s,7u,true,gate.waiting,false));
    comp_credit_wakeup_host_cycle(&s);
    comp_credit_wakeup_note(&s,7u); /* Duplicate report cannot undo readiness. */
    assert(!comp_credit_wakeup_take(&s,7u,true,true,true)); /* Nested ACI. */
    assert(s.pending==2u&&s.wakes==0u);
    assert(comp_credit_wakeup_take(&s,7u,true,gate.waiting,false));
    comp_v11_ble_tx_gate_available(&gate);
    assert(!comp_credit_wakeup_take(&s,7u,true,gate.waiting,false));
    /* A failed actual API preserves the original resource gate/deadline. */
    comp_v11_ble_tx_gate_begin(&gate,101u,6u);
    comp_v11_ble_tx_gate_end(&gate,true);
    comp_credit_wakeup_result(&s,7u,false,true);
    assert(gate.waiting&&s.wakes==1u&&s.accepted==0u&&s.resource==1u);
    assert(!comp_v11_ble_tx_gate_ready(&gate,102u));
    assert(comp_v11_ble_tx_gate_ready(&gate,103u));
    comp_credit_wakeup_note(&s,7u);comp_credit_wakeup_host_cycle(&s);
    assert(comp_credit_wakeup_take(&s,7u,true,true,false));
    comp_v11_ble_tx_gate_available(&gate);
    comp_v11_ble_tx_gate_begin(&gate,102u,6u);
    comp_v11_ble_tx_gate_end(&gate,false);
    comp_credit_wakeup_result(&s,7u,true,false);
    comp_credit_wakeup_result(&s,7u,true,false); /* One result per taken hint. */
    assert(s.wakes==2u&&s.accepted==1u&&s.resource==1u&&!gate.waiting);
    comp_credit_wakeup_note(&s,7u);comp_credit_wakeup_host_cycle(&s);
    assert(!comp_credit_wakeup_take(&s,8u,true,true,false)&&!s.pending);
    comp_credit_wakeup_note(&s,8u);comp_credit_wakeup_host_cycle(&s);
    assert(!comp_credit_wakeup_take(&s,8u,false,true,false)&&!s.pending);
    comp_credit_wakeup_note(&s,8u);comp_credit_wakeup_host_cycle(&s);
    assert(comp_credit_wakeup_take(&s,8u,true,true,false));
    comp_credit_wakeup_result(&s,8u,false,false); /* Explicitly unclassified. */
    assert(s.wakes==1u&&s.accepted==0u&&s.resource==0u);
    s.wakes=UINT16_MAX;s.accepted=UINT16_MAX;s.resource=UINT16_MAX;
    comp_credit_wakeup_note(&s,8u);comp_credit_wakeup_host_cycle(&s);
    assert(comp_credit_wakeup_take(&s,8u,true,true,false));
    comp_credit_wakeup_result(&s,8u,true,false);
    assert(s.wakes==UINT16_MAX&&s.accepted==UINT16_MAX&&s.resource==UINT16_MAX);
    puts("PASS_CONTROLLER_PROGRESS_RETRY queued_not_credit host_cycle_required nested_deferred coalesced generation_disarmed resource_gate_retained actual_admission_only saturated_visible software_only");
    return 0;
}
