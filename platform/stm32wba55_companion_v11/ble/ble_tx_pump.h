#ifndef COMP_V11_BLE_TX_PUMP_H
#define COMP_V11_BLE_TX_PUMP_H

#include "ble_tx_gate.h"
#include "wba_recording_transfer.h"
#include "stm32_seq.h"

typedef struct {
    bool foreground_run;
    bool dispatching;
} comp_v11_ble_tx_pump_t;

static inline bool comp_v11_ble_tx_pump_ready(
    const comp_wba_recording_transfer_t *transfer,
    const comp_v11_ble_tx_gate_t *gate, bool allowed, uint32_t now)
{
    return allowed && transfer->connected && !transfer->snapshot_live &&
        (transfer->state == COMP_WBA_RECORDING_TRANSFER_ACTIVE ||
         transfer->state == COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED) &&
        comp_v11_ble_tx_gate_ready(gate, now);
}

static inline void comp_v11_ble_tx_pump_schedule(
    const comp_wba_recording_transfer_t *transfer,
    const comp_v11_ble_tx_gate_t *gate, bool allowed, uint32_t now,
    uint32_t task, uint32_t priority)
{
    if (comp_v11_ble_tx_pump_ready(transfer, gate, allowed, now))
        UTIL_SEQ_SetTask(task, priority);
}

static inline void comp_v11_ble_tx_pump_poll(
    comp_v11_ble_tx_pump_t *pump, comp_wba_recording_transfer_t *transfer,
    const comp_v11_ble_tx_gate_t *gate, bool allowed, uint8_t sequencer_depth,
    comp_wba_recording_transfer_clock_fn clock, void *clock_context,
    uint32_t task, uint32_t priority)
{
    /* ACI can itself run a nested UTIL_SEQ_WaitEvt, even when invoked outside
     * the product's sequencer. Never enter GATT/NOR from that nested dispatch.
     * An ordinary foreground run will requeue a skipped task from its cursor. */
    if (!pump->foreground_run || pump->dispatching || sequencer_depth != 1u ||
        gate->in_call || !comp_v11_ble_tx_pump_ready(
            transfer, gate, allowed, clock(clock_context))) return;

    static const comp_wba_recording_transfer_budget_t turn = {1u, 2u, 1u};
    pump->dispatching = true;
    (void)comp_wba_recording_transfer_poll_budget(
        transfer, clock, clock_context, &turn);
    pump->dispatching = false;
    /* Like ST's throughput example, successful work requeues the send task.
     * Radio/HCI tasks at the same priority get their round-robin turn before
     * the next packet. A full pool stops here until its event (or deadline).
     * Also retains a pool wake delivered inside the preceding ACI command. */
    comp_v11_ble_tx_pump_schedule(
        transfer, gate, allowed, clock(clock_context), task, priority);
}

#endif
