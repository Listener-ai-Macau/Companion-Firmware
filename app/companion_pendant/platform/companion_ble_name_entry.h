#ifndef COMPANION_BLE_NAME_ENTRY_H
#define COMPANION_BLE_NAME_ENTRY_H

#include "companion_ble_name.h"

companion_ble_name_result_t companion_ble_name_product_entry(
    companion_ble_name_state_t *state,
    const uint8_t *payload,
    uint16_t payload_length,
    uint32_t idempotency_key,
    companion_ble_name_restart_fn restart,
    void *restart_context);

#endif
