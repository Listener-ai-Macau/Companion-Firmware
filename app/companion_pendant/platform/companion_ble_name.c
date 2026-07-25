#include "companion_ble_name.h"

#include <string.h>

static void copy_name(uint8_t *out, uint8_t *out_len,
                      const uint8_t *name, uint8_t length)
{
    memset(out, 0, COMPANION_GATT_BLE_NAME_MAX_BYTES);
    if (length != 0u) {
        memcpy(out, name, length);
    }
    *out_len = length;
}

bool companion_ble_name_is_valid(const uint8_t *name, uint8_t length)
{
    if (name == NULL || length == 0u ||
        length > COMPANION_GATT_BLE_NAME_MAX_BYTES) {
        return false;
    }
    for (uint8_t i = 0u; i < length; ++i) {
        const uint8_t ch = name[i];
        if (ch < 0x20u || ch > 0x7eu || ch == '"' || ch == '\'' ||
            ch == ';' || ch == '=' || ch == '\\') {
            return false;
        }
    }
    return true;
}

static bool same_request(const companion_ble_name_terminal_t *entry,
                         const companion_gatt_ble_name_config_v1_t *request,
                         uint32_t key)
{
    return entry->occupied && entry->request_id == request->request_id &&
           entry->idempotency_key == key && entry->command == request->command &&
           entry->name_len == request->name_len &&
           memcmp(entry->name, request->name, request->name_len) == 0;
}

static bool same_identity_different_payload(
    const companion_ble_name_terminal_t *entry,
    const companion_gatt_ble_name_config_v1_t *request, uint32_t key)
{
    return entry->occupied && entry->request_id == request->request_id &&
           (entry->idempotency_key != key || entry->command != request->command ||
            entry->name_len != request->name_len ||
            memcmp(entry->name, request->name, request->name_len) != 0);
}

static companion_ble_name_result_t lookup(
    const companion_ble_name_state_t *state,
    const companion_gatt_ble_name_config_v1_t *request, uint32_t key,
    bool *found)
{
    *found = false;
    for (uint8_t i = 0u; i < COMPANION_BLE_NAME_REPLAY_CAPACITY; ++i) {
        const companion_ble_name_terminal_t *entry = &state->replay[i];
        if (same_request(entry, request, key)) {
            *found = true;
            return entry->result;
        }
        if (same_identity_different_payload(entry, request, key)) {
            *found = true;
            return COMPANION_BLE_NAME_COLLISION;
        }
    }
    return COMPANION_BLE_NAME_NULL;
}

static void remember(companion_ble_name_state_t *state,
                     const companion_gatt_ble_name_config_v1_t *request,
                     uint32_t key, companion_ble_name_result_t result)
{
    companion_ble_name_terminal_t *entry =
        &state->replay[state->replay_next % COMPANION_BLE_NAME_REPLAY_CAPACITY];
    memset(entry, 0, sizeof(*entry));
    entry->occupied = true;
    entry->request_id = request->request_id;
    entry->idempotency_key = key;
    entry->command = request->command;
    entry->name_len = request->name_len;
    if (request->name_len != 0u) {
        memcpy(entry->name, request->name, request->name_len);
    }
    entry->result = result;
    state->replay_next = (uint8_t)((state->replay_next + 1u) %
                                   COMPANION_BLE_NAME_REPLAY_CAPACITY);
}

void companion_ble_name_init(companion_ble_name_state_t *state)
{
    static const uint8_t default_name[] = COMPANION_BLE_NAME_DEFAULT;
    if (state == NULL) {
        return;
    }
    memset(state, 0, sizeof(*state));
    copy_name(state->active, &state->active_len, default_name,
              (uint8_t)(sizeof(default_name) - 1u));
}

void companion_ble_name_set_connection(companion_ble_name_state_t *state,
                                       bool connected, bool busy)
{
    if (state != NULL) {
        state->connected = connected;
        state->busy = busy;
    }
}

void companion_ble_name_get_config(const companion_ble_name_state_t *state,
                                   companion_gatt_ble_name_config_v1_t *out)
{
    if (state == NULL || out == NULL) {
        return;
    }
    memset(out, 0, sizeof(*out));
    out->schema_version = 1u;
    out->command = COMPANION_BLE_NAME_APPLY;
    out->max_len = COMPANION_GATT_BLE_NAME_MAX_BYTES;
    out->status = state->pending_valid ? 1u : 0u;
    out->flags = state->pending_valid ? 0x0001u : 0u;
    out->name_len = state->active_len;
    memcpy(out->name, state->active, state->active_len);
}

companion_ble_name_result_t companion_ble_name_handle(
    companion_ble_name_state_t *state,
    const companion_gatt_ble_name_config_v1_t *request,
    uint32_t idempotency_key,
    companion_ble_name_restart_fn restart,
    void *restart_context)
{
    bool found;
    companion_ble_name_result_t result;
    if (state == NULL || request == NULL) {
        return COMPANION_BLE_NAME_NULL;
    }
    result = lookup(state, request, idempotency_key, &found);
    if (found) {
        return result;
    }
    if (request->command == COMPANION_BLE_NAME_STAGE &&
        !companion_ble_name_is_valid(request->name, request->name_len)) {
        result = COMPANION_BLE_NAME_INVALID;
    } else if (request->command != COMPANION_BLE_NAME_STAGE &&
               request->command != COMPANION_BLE_NAME_APPLY &&
               request->command != COMPANION_BLE_NAME_RESET) {
        result = COMPANION_BLE_NAME_INVALID;
    } else if (request->command == COMPANION_BLE_NAME_STAGE) {
        copy_name(state->pending, &state->pending_len, request->name,
                  request->name_len);
        state->pending_valid = true;
        result = COMPANION_BLE_NAME_OK;
    } else if (request->command == COMPANION_BLE_NAME_RESET) {
        static const uint8_t default_name[] = COMPANION_BLE_NAME_DEFAULT;
        /* Reset always replaces a previously staged value before apply. */
        copy_name(state->pending, &state->pending_len, default_name,
                  (uint8_t)(sizeof(default_name) - 1u));
        state->pending_valid = true;
        result = COMPANION_BLE_NAME_OK;
        if (state->connected) {
            result = COMPANION_BLE_NAME_CONNECTED;
        } else if (state->busy) {
            result = COMPANION_BLE_NAME_BUSY;
        } else if (restart == NULL ||
                   !restart(restart_context, state->pending, state->pending_len)) {
            result = COMPANION_BLE_NAME_RESTART_FAILED;
        } else {
            copy_name(state->active, &state->active_len,
                      state->pending, state->pending_len);
            state->pending_valid = false;
            state->pending_len = 0u;
            memset(state->pending, 0, sizeof(state->pending));
            result = COMPANION_BLE_NAME_OK;
        }
    } else if (!state->pending_valid) {
        result = COMPANION_BLE_NAME_NO_STAGE;
    } else if (state->connected) {
        result = COMPANION_BLE_NAME_CONNECTED;
    } else if (state->busy) {
        result = COMPANION_BLE_NAME_BUSY;
    } else if (restart == NULL ||
               !restart(restart_context, state->pending, state->pending_len)) {
        result = COMPANION_BLE_NAME_RESTART_FAILED;
    } else {
        copy_name(state->active, &state->active_len,
                  state->pending, state->pending_len);
        state->pending_valid = false;
        state->pending_len = 0u;
        memset(state->pending, 0, sizeof(state->pending));
        result = COMPANION_BLE_NAME_OK;
    }
    remember(state, request, idempotency_key, result);
    return result;
}

uint8_t companion_ble_name_active(const companion_ble_name_state_t *state,
                                  uint8_t *out, uint8_t capacity)
{
    if (state == NULL || out == NULL || capacity < state->active_len) {
        return 0u;
    }
    memcpy(out, state->active, state->active_len);
    return state->active_len;
}

uint8_t companion_ble_name_pending(const companion_ble_name_state_t *state,
                                   uint8_t *out, uint8_t capacity)
{
    if (state == NULL || out == NULL || !state->pending_valid ||
        capacity < state->pending_len) {
        return 0u;
    }
    memcpy(out, state->pending, state->pending_len);
    return state->pending_len;
}
