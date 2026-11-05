#ifndef COMP_V11_BLE_TX_GATE_H
#define COMP_V11_BLE_TX_GATE_H

#include <stdbool.h>
#include <stdint.h>

/* Foreground-owned: HCI events may run inside a nested sequencer wait.
 * Arm before entering the stack so a TX_POOL event cannot be overwritten
 * by the command's later INSUFFICIENT_RESOURCES return. */
typedef struct {
    uint32_t retry_ms;
    bool waiting;
    bool in_call;
    uint8_t retry_delay_ms;
} comp_v11_ble_tx_gate_t;

static inline bool comp_v11_ble_tx_gate_ready(
    const comp_v11_ble_tx_gate_t *gate, uint32_t now)
{
    return !gate->waiting || (int32_t)(now - gate->retry_ms) >= 0;
}

static inline uint32_t comp_v11_ble_tx_retry_delay(uint16_t interval_units)
{
    /* A missed pool event must not waste a whole short connection event.
     * Retry after a quarter interval, rounded up to the 1ms timebase.
     * Unknown/slow links retain the previous 20ms recovery ceiling. */
    uint32_t delay = ((uint32_t)interval_units * 5u + 15u) / 16u;
    if (interval_units == 0u || delay > 20u) delay = 20u;
    return delay == 0u ? 1u : delay;
}

static inline void comp_v11_ble_tx_gate_begin(
    comp_v11_ble_tx_gate_t *gate, uint32_t now, uint16_t interval_units)
{
    gate->retry_delay_ms = (uint8_t)comp_v11_ble_tx_retry_delay(interval_units);
    gate->retry_ms = now + gate->retry_delay_ms;
    gate->waiting = true;
    gate->in_call = true;
}

static inline void comp_v11_ble_tx_gate_end(
    comp_v11_ble_tx_gate_t *gate, bool insufficient_resources)
{
    gate->in_call = false;
    if (!insufficient_resources) gate->waiting = false;
}

static inline void comp_v11_ble_tx_gate_available(comp_v11_ble_tx_gate_t *gate)
{
    gate->waiting = false;
}

#endif
