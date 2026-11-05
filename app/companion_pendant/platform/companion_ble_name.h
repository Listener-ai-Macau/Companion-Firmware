#ifndef COMPANION_BLE_NAME_H
#define COMPANION_BLE_NAME_H

#include "../gatt/companion_gatt_stm32wb.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMPANION_BLE_NAME_DEFAULT "companion"
#define COMPANION_BLE_NAME_REPLAY_CAPACITY 8u
#if defined(COMPANION_GATT_WBA_HOST)
#include "../runtime/companion_preferences.h"
/* The WBA persistence/readback path already advertises and enforces24B.
 * The generic wire structure remains29B; do not reserve its unsupported
 * tail in every active/pending/replay entry. */
#define COMPANION_BLE_NAME_STORAGE_BYTES COMP_PREFS_NAME_BYTES
#else
#define COMPANION_BLE_NAME_STORAGE_BYTES COMPANION_GATT_BLE_NAME_MAX_BYTES
#endif

#ifndef COMPANION_BLE_NAME_PLATFORM_GATE
#define COMPANION_BLE_NAME_PLATFORM_GATE 0
#endif

typedef enum {
    COMPANION_BLE_NAME_STAGE = 1,
    COMPANION_BLE_NAME_APPLY = 2,
    COMPANION_BLE_NAME_RESET = 3,
} companion_ble_name_command_t;

typedef enum {
    COMPANION_BLE_NAME_OK = 0,
    COMPANION_BLE_NAME_INVALID = 1,
    COMPANION_BLE_NAME_NO_STAGE = 2,
    COMPANION_BLE_NAME_CONNECTED = 3,
    COMPANION_BLE_NAME_BUSY = 4,
    COMPANION_BLE_NAME_RESTART_FAILED = 5,
    COMPANION_BLE_NAME_COLLISION = 6,
    COMPANION_BLE_NAME_NULL = 7,
} companion_ble_name_result_t;

typedef bool (*companion_ble_name_restart_fn)(
    void *context, const uint8_t *name, uint8_t length);

typedef struct {
    uint32_t request_id;
    uint32_t idempotency_key;
    uint8_t name[COMPANION_BLE_NAME_STORAGE_BYTES];
    companion_ble_name_result_t result;
    uint8_t command;
    uint8_t name_len;
    bool occupied;
} companion_ble_name_terminal_t;

typedef struct {
    uint8_t active_len;
    uint8_t active[COMPANION_BLE_NAME_STORAGE_BYTES];
    uint8_t pending_len;
    uint8_t pending[COMPANION_BLE_NAME_STORAGE_BYTES];
    bool pending_valid;
    bool connected;
    bool busy;
    uint8_t replay_next;
    companion_ble_name_terminal_t replay[COMPANION_BLE_NAME_REPLAY_CAPACITY];
} companion_ble_name_state_t;

void companion_ble_name_init(companion_ble_name_state_t *state);
bool companion_ble_name_is_valid(const uint8_t *name, uint8_t length);
companion_ble_name_result_t companion_ble_name_handle(
    companion_ble_name_state_t *state,
    const companion_gatt_ble_name_config_v1_t *request,
    uint32_t idempotency_key,
    companion_ble_name_restart_fn restart,
    void *restart_context);

void companion_ble_name_set_connection(companion_ble_name_state_t *state,
                                       bool connected, bool busy);
void companion_ble_name_get_config(const companion_ble_name_state_t *state,
                                   companion_gatt_ble_name_config_v1_t *out);
uint8_t companion_ble_name_active(const companion_ble_name_state_t *state,
                                  uint8_t *out, uint8_t capacity);
uint8_t companion_ble_name_pending(const companion_ble_name_state_t *state,
                                   uint8_t *out, uint8_t capacity);

#ifdef __cplusplus
}
#endif

#endif
