#include "companion_ble_name_entry.h"

companion_ble_name_result_t companion_ble_name_product_entry(
    companion_ble_name_state_t *state,
    const uint8_t *payload,
    uint16_t payload_length,
    uint32_t idempotency_key,
    companion_ble_name_restart_fn restart,
    void *restart_context)
{
    companion_gatt_ble_name_config_v1_t request;
    if (companion_gatt_parse_ble_name_config_v1(payload, payload_length,
                                                &request) != COMPANION_GATT_PARSE_OK) {
        return COMPANION_BLE_NAME_INVALID;
    }
    return companion_ble_name_handle(state, &request, idempotency_key,
                                     restart, restart_context);
}
