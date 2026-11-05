#include "companion_ble_repair.h"

#include <stdbool.h>
#include <stdint.h>
#include <string.h>

static bool same(const companion_ble_repair_terminal_t *entry,
                 const companion_gatt_repair_control_v1_t *request,
                 uint32_t key)
{
    return entry->occupied && entry->request_id == request->request_id &&
           entry->idempotency_key == key &&
           entry->pairing_window_ms == request->pairing_window_ms;
}

static bool collision(const companion_ble_repair_terminal_t *entry,
                      const companion_gatt_repair_control_v1_t *request,
                      uint32_t key)
{
    return entry->occupied && entry->request_id == request->request_id &&
           (entry->idempotency_key != key ||
            entry->pairing_window_ms != request->pairing_window_ms);
}

static companion_ble_repair_result_t lookup(
    const companion_ble_repair_state_t *state,
    const companion_gatt_repair_control_v1_t *request,
    uint32_t key, bool *found)
{
    *found = false;
    for (uint8_t i = 0u; i < COMPANION_BLE_REPAIR_REPLAY_CAPACITY; ++i) {
        const companion_ble_repair_terminal_t *entry = &state->replay[i];
        if (same(entry, request, key)) {
            *found = true;
            return entry->result;
        }
        if (collision(entry, request, key)) {
            *found = true;
            return COMPANION_BLE_REPAIR_COLLISION;
        }
    }
    return COMPANION_BLE_REPAIR_UNSUPPORTED;
}

static void remember(companion_ble_repair_state_t *state,
                     const companion_gatt_repair_control_v1_t *request,
                     uint32_t key, companion_ble_repair_result_t result)
{
    companion_ble_repair_terminal_t *entry =
        &state->replay[state->replay_next % COMPANION_BLE_REPAIR_REPLAY_CAPACITY];
    memset(entry, 0, sizeof(*entry));
    entry->occupied = true;
    entry->request_id = request->request_id;
    entry->idempotency_key = key;
    entry->pairing_window_ms = request->pairing_window_ms;
    entry->result = result;
    state->replay_next = (state->replay_next + 1u) %
                          COMPANION_BLE_REPAIR_REPLAY_CAPACITY;
}

void companion_ble_repair_init(companion_ble_repair_state_t *state)
{
    if (state != NULL) {
        memset(state, 0, sizeof(*state));
    }
}

void companion_ble_repair_set_connection(companion_ble_repair_state_t *state,
                                          bool connected, bool busy)
{
    if (state != NULL) {
        state->connected = connected;
        state->busy = busy;
    }
}

companion_ble_repair_result_t companion_ble_repair_product_entry(
    companion_ble_repair_state_t *state,
    const uint8_t *payload,
    uint16_t payload_length,
    uint32_t idempotency_key,
    companion_ble_repair_request_fn request,
    void *request_context)
{
    companion_gatt_repair_control_v1_t parsed;
    bool found = false;
    companion_ble_repair_result_t result;
    if (state == NULL || payload == NULL ||
        companion_gatt_parse_repair_control_v1(payload, payload_length,
                                               &parsed) != COMPANION_GATT_PARSE_OK) {
        return COMPANION_BLE_REPAIR_INVALID;
    }
#if !COMPANION_BLE_REPAIR_PLATFORM_GATE
    (void)request;
    (void)request_context;
    return COMPANION_BLE_REPAIR_UNSUPPORTED;
#else
    result = lookup(state, &parsed, idempotency_key, &found);
    if (found) {
        return result;
    }
    if (state->connected) {
        result = COMPANION_BLE_REPAIR_CONNECTED;
    } else if (state->busy) {
        result = COMPANION_BLE_REPAIR_BUSY;
    } else if (request == NULL ||
               !request(request_context, parsed.pairing_window_ms)) {
        state->callback_count += request == NULL ? 0u : 1u;
        result = COMPANION_BLE_REPAIR_FAILED;
    } else {
        state->callback_count += 1u;
        result = COMPANION_BLE_REPAIR_OK;
    }
    remember(state, &parsed, idempotency_key, result);
    return result;
#endif
}
