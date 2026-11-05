#ifndef COMPANION_BLE_REPAIR_H
#define COMPANION_BLE_REPAIR_H

#include "../gatt/companion_gatt_stm32wb.h"

#include <stdbool.h>
#include <stdint.h>

#define COMPANION_BLE_REPAIR_REPLAY_CAPACITY 8u
#define COMPANION_BLE_REPAIR_MAX_WINDOW_MS 120000u

#ifndef COMPANION_BLE_REPAIR_PLATFORM_GATE
#define COMPANION_BLE_REPAIR_PLATFORM_GATE 0
#endif

typedef enum {
    COMPANION_BLE_REPAIR_OK = 0,
    COMPANION_BLE_REPAIR_INVALID = 1,
    COMPANION_BLE_REPAIR_CONNECTED = 2,
    COMPANION_BLE_REPAIR_BUSY = 3,
    COMPANION_BLE_REPAIR_FAILED = 4,
    COMPANION_BLE_REPAIR_COLLISION = 5,
    COMPANION_BLE_REPAIR_UNSUPPORTED = 6,
} companion_ble_repair_result_t;

typedef bool (*companion_ble_repair_request_fn)(void *, uint32_t);

typedef struct {
    bool occupied;
    uint32_t request_id;
    uint32_t idempotency_key;
    uint32_t pairing_window_ms;
    companion_ble_repair_result_t result;
} companion_ble_repair_terminal_t;

typedef struct {
    bool connected;
    bool busy;
    uint32_t callback_count;
    uint32_t replay_next;
    companion_ble_repair_terminal_t replay[COMPANION_BLE_REPAIR_REPLAY_CAPACITY];
} companion_ble_repair_state_t;

void companion_ble_repair_init(companion_ble_repair_state_t *state);
void companion_ble_repair_set_connection(companion_ble_repair_state_t *state,
                                          bool connected, bool busy);
companion_ble_repair_result_t companion_ble_repair_product_entry(
    companion_ble_repair_state_t *state,
    const uint8_t *payload,
    uint16_t payload_length,
    uint32_t idempotency_key,
    companion_ble_repair_request_fn request,
    void *request_context);

#endif
