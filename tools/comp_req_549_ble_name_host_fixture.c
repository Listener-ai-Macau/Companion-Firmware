#include "companion_ble_name_entry.h"

#include <stdio.h>
#include <string.h>

typedef struct {
    unsigned calls;
    bool succeed;
    char gap_name[COMPANION_GATT_BLE_NAME_MAX_BYTES + 1u];
    char advertising_name[COMPANION_GATT_BLE_NAME_MAX_BYTES + 1u];
} sink_t;

static bool counted_restart(void *context, const uint8_t *name, uint8_t length)
{
    sink_t *sink = (sink_t *)context;
    sink->calls += 1u;
    if (sink->succeed) {
        memset(sink->gap_name, 0, sizeof(sink->gap_name));
        memset(sink->advertising_name, 0, sizeof(sink->advertising_name));
        memcpy(sink->gap_name, name, length);
        memcpy(sink->advertising_name, name, length);
    }
    return sink->succeed;
}

static size_t wire(uint8_t *out, uint32_t request_id, uint8_t command,
                   const char *name)
{
    companion_gatt_ble_name_config_v1_t request;
    memset(&request, 0, sizeof(request));
    request.schema_version = 1u;
    request.command = command;
    request.request_id = request_id;
    request.max_len = COMPANION_GATT_BLE_NAME_MAX_BYTES;
    if (name != NULL) {
        request.name_len = (uint8_t)strlen(name);
        memcpy(request.name, name, request.name_len);
    }
    memcpy(out, &request, sizeof(request));
    return sizeof(request);
}

static int expect(const char *label, companion_ble_name_result_t got,
                  companion_ble_name_result_t wanted)
{
    if (got != wanted) {
        fprintf(stderr, "FAIL %s got=%d want=%d\n", label, (int)got, (int)wanted);
        return 1;
    }
    return 0;
}

static int expect_active(const companion_ble_name_state_t *state, const char *wanted)
{
    uint8_t active[COMPANION_GATT_BLE_NAME_MAX_BYTES] = {0};
    const uint8_t length = companion_ble_name_active(state, active, sizeof(active));
    if (length != strlen(wanted) || memcmp(active, wanted, length) != 0) {
        fprintf(stderr, "FAIL active got=%.*s want=%s\n", (int)length, active, wanted);
        return 1;
    }
    return 0;
}

static int expect_target_names(const sink_t *sink, const char *wanted)
{
    if (strcmp(sink->gap_name, wanted) != 0 ||
        strcmp(sink->advertising_name, wanted) != 0) {
        fprintf(stderr, "FAIL target gap=%s advertising=%s want=%s\n",
                sink->gap_name, sink->advertising_name, wanted);
        return 1;
    }
    return 0;
}

int main(void)
{
    uint8_t payload[sizeof(companion_gatt_ble_name_config_v1_t)];
    companion_ble_name_state_t state;
    sink_t sink = {0u, true, {0}, {0}};
    unsigned failures = 0u;

    companion_ble_name_init(&state);
    failures += expect("stage", companion_ble_name_product_entry(
        &state, payload, (uint16_t)wire(payload, 1u, 1u, "luna"), 10u,
        counted_restart, &sink), COMPANION_BLE_NAME_OK);
    if (sink.calls != 0u) failures += 1u;
    failures += expect("apply", companion_ble_name_product_entry(
        &state, payload, (uint16_t)wire(payload, 2u, 2u, NULL), 20u,
        counted_restart, &sink), COMPANION_BLE_NAME_OK);
    if (sink.calls != 1u || strcmp(sink.gap_name, "luna") != 0 ||
        strcmp(sink.advertising_name, "luna") != 0) failures += 1u;
    failures += (expect_target_names(&sink, "luna") != 0);
    failures += expect("replay-success", companion_ble_name_product_entry(
        &state, payload, (uint16_t)wire(payload, 2u, 2u, NULL), 20u,
        counted_restart, &sink), COMPANION_BLE_NAME_OK);
    if (sink.calls != 1u) failures += 1u;
    failures += expect("collision", companion_ble_name_product_entry(
        &state, payload, (uint16_t)wire(payload, 2u, 2u, NULL), 21u,
        counted_restart, &sink), COMPANION_BLE_NAME_COLLISION);
    if (sink.calls != 1u) failures += 1u;

    companion_ble_name_init(&state);
    sink.calls = 0u;
    memset(sink.gap_name, 0, sizeof(sink.gap_name));
    memset(sink.advertising_name, 0, sizeof(sink.advertising_name));
    failures += expect("stage-before-reset", companion_ble_name_product_entry(
        &state, payload, (uint16_t)wire(payload, 13u, 1u, "stale"), 130u,
        counted_restart, &sink), COMPANION_BLE_NAME_OK);
    failures += expect("reset-replaces-pending", companion_ble_name_product_entry(
        &state, payload, (uint16_t)wire(payload, 14u, 3u, NULL), 140u,
        counted_restart, &sink), COMPANION_BLE_NAME_OK);
    if (strcmp(sink.gap_name, COMPANION_BLE_NAME_DEFAULT) != 0 ||
        strcmp(sink.advertising_name, COMPANION_BLE_NAME_DEFAULT) != 0) failures += 1u;
    failures += expect("invalid", companion_ble_name_product_entry(
        &state, payload, (uint16_t)wire(payload, 3u, 1u, "bad=name"), 30u,
        counted_restart, &sink), COMPANION_BLE_NAME_INVALID);
    if (sink.calls != 1u) failures += 1u;

    companion_ble_name_init(&state);
    sink.calls = 0u;
    memset(sink.gap_name, 0, sizeof(sink.gap_name));
    memset(sink.advertising_name, 0, sizeof(sink.advertising_name));
    failures += expect("no-stage", companion_ble_name_product_entry(
        &state, payload, (uint16_t)wire(payload, 4u, 2u, NULL), 40u,
        counted_restart, &sink), COMPANION_BLE_NAME_NO_STAGE);
    sink.calls = 0u;
    memset(sink.gap_name, 0, sizeof(sink.gap_name));
    memset(sink.advertising_name, 0, sizeof(sink.advertising_name));
    companion_ble_name_set_connection(&state, true, false);
    failures += expect("connected", companion_ble_name_product_entry(
        &state, payload, (uint16_t)wire(payload, 5u, 1u, "connected"), 50u,
        counted_restart, &sink), COMPANION_BLE_NAME_OK);
    failures += expect("connected-apply", companion_ble_name_product_entry(
        &state, payload, (uint16_t)wire(payload, 6u, 2u, NULL), 60u,
        counted_restart, &sink), COMPANION_BLE_NAME_CONNECTED);
    if (sink.calls != 0u) failures += 1u;
    failures += (expect_active(&state, COMPANION_BLE_NAME_DEFAULT) != 0);

    companion_ble_name_init(&state);
    sink.calls = 0u;
    memset(sink.gap_name, 0, sizeof(sink.gap_name));
    memset(sink.advertising_name, 0, sizeof(sink.advertising_name));
    companion_ble_name_set_connection(&state, false, true);
    failures += expect("busy", companion_ble_name_product_entry(
        &state, payload, (uint16_t)wire(payload, 7u, 1u, "busy"), 70u,
        counted_restart, &sink), COMPANION_BLE_NAME_OK);
    failures += expect("busy-apply", companion_ble_name_product_entry(
        &state, payload, (uint16_t)wire(payload, 8u, 2u, NULL), 80u,
        counted_restart, &sink), COMPANION_BLE_NAME_BUSY);
    failures += (expect_active(&state, COMPANION_BLE_NAME_DEFAULT) != 0);

    companion_ble_name_init(&state);
    sink.calls = 0u;
    memcpy(sink.gap_name, COMPANION_BLE_NAME_DEFAULT,
           sizeof(COMPANION_BLE_NAME_DEFAULT));
    memcpy(sink.advertising_name, COMPANION_BLE_NAME_DEFAULT,
           sizeof(COMPANION_BLE_NAME_DEFAULT));
    sink.succeed = false;
    failures += expect("restart-failure", companion_ble_name_product_entry(
        &state, payload, (uint16_t)wire(payload, 9u, 1u, "failed"), 90u,
        counted_restart, &sink), COMPANION_BLE_NAME_OK);
    failures += expect("restart-failure-apply", companion_ble_name_product_entry(
        &state, payload, (uint16_t)wire(payload, 10u, 2u, NULL), 100u,
        counted_restart, &sink), COMPANION_BLE_NAME_RESTART_FAILED);
    const unsigned failed_calls = sink.calls;
    failures += expect("replay-failure", companion_ble_name_product_entry(
        &state, payload, (uint16_t)wire(payload, 10u, 2u, NULL), 100u,
        counted_restart, &sink), COMPANION_BLE_NAME_RESTART_FAILED);
    if (sink.calls != failed_calls) failures += 1u;
    failures += (expect_active(&state, COMPANION_BLE_NAME_DEFAULT) != 0);
    failures += (expect_target_names(&sink, COMPANION_BLE_NAME_DEFAULT) != 0);

    sink.succeed = true;
    companion_ble_name_init(&state);
    sink.calls = 0u;
    memset(sink.gap_name, 0, sizeof(sink.gap_name));
    memset(sink.advertising_name, 0, sizeof(sink.advertising_name));
    failures += expect("reset-default", companion_ble_name_product_entry(
        &state, payload, (uint16_t)wire(payload, 11u, 3u, NULL), 110u,
        counted_restart, &sink), COMPANION_BLE_NAME_OK);
    if (strcmp(sink.gap_name, COMPANION_BLE_NAME_DEFAULT) != 0 ||
        strcmp(sink.advertising_name, COMPANION_BLE_NAME_DEFAULT) != 0) failures += 1u;
    if (companion_ble_name_product_entry(&state, payload,
            (uint16_t)(wire(payload, 12u, 1u, "truncated") - 1u), 120u,
            counted_restart, &sink) != COMPANION_BLE_NAME_INVALID) failures += 1u;

    if (failures != 0u) {
        fprintf(stderr, "BLE_NAME_FIXTURE FAIL count=%u\n", failures);
        return 1;
    }
    puts("BLE_NAME_FIXTURE PASS stage/apply/reset parser counted-sink matrix");
    return 0;
}
