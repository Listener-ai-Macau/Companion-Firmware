#include "ble_tx_gate.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    comp_v11_ble_tx_gate_t gate = {0};
    assert(comp_v11_ble_tx_gate_ready(&gate, 0u));
    /* Full queue sleeps; a free-pool callback wakes without a timer delay. */
    comp_v11_ble_tx_gate_begin(&gate, 100u, 12u);
    comp_v11_ble_tx_gate_end(&gate, true);
    assert(!comp_v11_ble_tx_gate_ready(&gate, 103u));
    comp_v11_ble_tx_gate_available(&gate);
    assert(comp_v11_ble_tx_gate_ready(&gate, 103u));

    /* The event may arrive before the stack command returns its failure.
     * Re-arming on return loses this wakeup and used to cost another 20ms. */
    comp_v11_ble_tx_gate_begin(&gate, 200u, 12u);
    assert(gate.in_call);
    comp_v11_ble_tx_gate_available(&gate);
    comp_v11_ble_tx_gate_end(&gate, true);
    assert(!gate.in_call);
    assert(comp_v11_ble_tx_gate_ready(&gate, 200u));

    /* A missed event retries at the actual interval's bounded fallback. */
    comp_v11_ble_tx_gate_begin(&gate, 300u, 12u);
    comp_v11_ble_tx_gate_end(&gate, true);
    assert(!comp_v11_ble_tx_gate_ready(&gate, 303u));
    assert(comp_v11_ble_tx_gate_ready(&gate, 304u));
    comp_v11_ble_tx_gate_begin(&gate, 304u, 12u);
    comp_v11_ble_tx_gate_end(&gate, false);
    assert(comp_v11_ble_tx_gate_ready(&gate, 304u));
    assert(comp_v11_ble_tx_retry_delay(6u) == 2u);
    assert(comp_v11_ble_tx_retry_delay(12u) == 4u);
    assert(comp_v11_ble_tx_retry_delay(48u) == 15u);
    assert(comp_v11_ble_tx_retry_delay(0u) == 20u);
    assert(comp_v11_ble_tx_retry_delay(UINT16_MAX) == 20u);

    comp_v11_ble_tx_gate_begin(&gate, UINT32_MAX - 1u, 12u);
    comp_v11_ble_tx_gate_end(&gate, true);
    assert(!comp_v11_ble_tx_gate_ready(&gate, UINT32_MAX));
    assert(!comp_v11_ble_tx_gate_ready(&gate, 1u));
    assert(comp_v11_ble_tx_gate_ready(&gate, 2u));
    puts("PASS_WBA_BLE_TX_GATE_HOST_ONLY");
    return 0;
}
