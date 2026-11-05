#include "companion_ble_name_entry.h"
#include "companion_gatt_stm32wb.h"
#include "companion_ble_repair.h"
#include "companion_platform_adapters.h"
#include "companion_product_entry_glue.h"
#include "companion_product_identity.h"

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define REPAIR_COMMAND 0x52455052u
#define NAME_STAGE 1u
#define NAME_APPLY 2u
#define NAME_RESET 3u
#define TRACE_CAPACITY 32u

typedef struct {
    unsigned calls;
    bool succeed;
    char gap[COMPANION_GATT_BLE_NAME_MAX_BYTES + 1u];
    char advertising[COMPANION_GATT_BLE_NAME_MAX_BYTES + 1u];
} name_sink_t;

typedef struct {
    uint32_t revision;
    uint64_t capabilities;
    unsigned reads;
    unsigned writes;
    unsigned invokes;
    bool fail_read;
    bool fail_write;
    bool fail_invoke;
    bool invalid_input;
} device_sink_t;

typedef struct {
    unsigned calls;
    bool succeed;
    uint32_t last_window_ms;
} repair_sink_t;

static bool target_restart(void *context, const uint8_t *name, uint8_t length)
{
    name_sink_t *sink = (name_sink_t *)context;
    if (sink == NULL || name == NULL || length > COMPANION_GATT_BLE_NAME_MAX_BYTES) {
        return false;
    }
    sink->calls += 1u;
    if (!sink->succeed) {
        return false;
    }
    memset(sink->gap, 0, sizeof(sink->gap));
    memset(sink->advertising, 0, sizeof(sink->advertising));
    memcpy(sink->gap, name, length);
    memcpy(sink->advertising, name, length);
    return true;
}

static size_t name_wire(uint8_t *out, uint32_t request_id, uint8_t command,
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

static bool read_capabilities(void *context, uint64_t id, uint64_t key,
                              uint32_t *revision, uint64_t *mask)
{
    device_sink_t *sink = (device_sink_t *)context;
    (void)id; (void)key;
    sink->reads += 1u;
    if (sink->fail_read || revision == NULL || mask == NULL) return false;
    *revision = sink->revision;
    *mask = sink->capabilities;
    return true;
}

static bool read_settings(void *context, uint64_t id, uint64_t key,
                          uint32_t *revision)
{
    device_sink_t *sink = (device_sink_t *)context;
    (void)id; (void)key;
    sink->reads += 1u;
    if (sink->fail_read || revision == NULL) return false;
    *revision = sink->revision;
    return true;
}

static bool write_settings(void *context, uint64_t id, uint64_t key,
                           uint32_t expected, uint32_t *ack)
{
    device_sink_t *sink = (device_sink_t *)context;
    (void)id; (void)key;
    sink->writes += 1u;
    if (sink->fail_write || ack == NULL || expected != sink->revision) return false;
    sink->revision += 1u;
    *ack = sink->revision;
    return true;
}

static bool invoke_command(void *context, uint64_t id, uint64_t key,
                           uint32_t command)
{
    device_sink_t *sink = (device_sink_t *)context;
    (void)id; (void)key; (void)command;
    sink->invokes += 1u;
    return !sink->fail_invoke;
}

static bool repair_request(void *context, uint32_t pairing_window_ms)
{
    repair_sink_t *sink = (repair_sink_t *)context;
    if (sink == NULL) return false;
    sink->calls += 1u;
    sink->last_window_ms = pairing_window_ms;
    return sink->succeed;
}

static size_t repair_wire(uint8_t *out, uint32_t request_id,
                          uint32_t pairing_window_ms)
{
    companion_gatt_repair_control_v1_t request;
    memset(&request, 0, sizeof(request));
    request.schema_version = 1u;
    request.command = 1u;
    request.request_id = request_id;
    request.pairing_window_ms = pairing_window_ms;
    memcpy(out, &request, sizeof(request));
    return sizeof(request);
}

typedef struct {
    companion_product_entry_glue_t glue;
} product_context_t;

static bool product_begin_settings(void *context, uint32_t now_ms,
                                   uint64_t operation_id, uint64_t key,
                                   uint32_t expected, const void *payload,
                                   uint32_t *ack)
{
    companion_gatt_settings_v1_t request;
    (void)context;
    if (companion_gatt_parse_settings_v1((const uint8_t *)payload,
                                         (uint16_t)sizeof(request), &request) !=
        COMPANION_GATT_PARSE_OK) return false;
    (void)request;
    return companion_platform_device_control_settings_event(
        now_ms, operation_id, key, expected, ack);
}

static bool product_begin_meeting(void *context, uint32_t now_ms,
                                  uint64_t operation_id, uint64_t key,
                                  const void *payload)
{
    companion_gatt_meeting_control_v1_t request;
    if (companion_gatt_parse_meeting_control_v1((const uint8_t *)payload,
                                                (uint16_t)sizeof(request),
                                                &request) != COMPANION_GATT_PARSE_OK) {
        return false;
    }
    (void)context;
    return companion_platform_device_control_invoke_event(
        now_ms, operation_id, key, request.command);
}

static bool gatt_settings_entry(product_context_t *context, const uint8_t *payload,
                                size_t length, uint32_t now_ms,
                                uint32_t deadline_ms, uint32_t expected,
                                uint64_t forced_key, bool use_forced_key,
                                uint32_t *ack, bool *replayed)
{
    companion_gatt_settings_v1_t request;
    companion_product_identity_t identity;
    if (context == NULL || payload == NULL || ack == NULL ||
        companion_gatt_parse_settings_v1(payload, (uint16_t)length, &request) !=
        COMPANION_GATT_PARSE_OK || !companion_product_identity_derive(
            "companion.settings", 0u, &request, sizeof(request), &identity)) {
        return false;
    }
    return companion_product_entry_settings(
        &context->glue, identity.operation_id,
        use_forced_key ? forced_key : identity.idempotency_key,
        now_ms, deadline_ms, expected, &request, ack, replayed);
}

static bool gatt_invoke_entry(product_context_t *context, const uint8_t *payload,
                              size_t length, uint32_t now_ms,
                              uint32_t deadline_ms, uint64_t forced_key,
                              bool use_forced_key, bool *replayed)
{
    companion_gatt_meeting_control_v1_t request;
    companion_product_identity_t identity;
    if (context == NULL || payload == NULL ||
        companion_gatt_parse_meeting_control_v1(payload, (uint16_t)length,
                                                &request) != COMPANION_GATT_PARSE_OK ||
        !companion_product_identity_derive("companion.meeting", request.request_id,
                                           &request, sizeof(request), &identity)) {
        return false;
    }
    return companion_product_entry_meeting(
        &context->glue, identity.operation_id,
        use_forced_key ? forced_key : identity.idempotency_key,
        now_ms, deadline_ms, &request, replayed);
}

static int require(bool condition, const char *label)
{
    if (!condition) {
        fprintf(stderr, "FAIL %s\n", label);
        return 1;
    }
    return 0;
}

int main(void)
{
    unsigned failures = 0u;
    uint8_t payload[sizeof(companion_gatt_ble_name_config_v1_t)];
    companion_ble_name_state_t name_state;
    name_sink_t name_sink = {0u, true, {0}, {0}};
    companion_ble_name_init(&name_state);

    size_t stage_len = name_wire(payload, 1u, NAME_STAGE, "luna-host");
    failures += require(companion_ble_name_product_entry(
        &name_state, payload, (uint16_t)stage_len, 101u,
        target_restart, &name_sink) == COMPANION_BLE_NAME_OK, "stage");
    failures += require(name_sink.calls == 0u, "stage_no_target_call");
    size_t apply_len = name_wire(payload, 2u, NAME_APPLY, NULL);
    failures += require(companion_ble_name_product_entry(
        &name_state, payload, (uint16_t)apply_len, 102u,
        target_restart, &name_sink) == COMPANION_BLE_NAME_OK, "apply");
    failures += require(name_sink.calls == 1u && strcmp(name_sink.gap, "luna-host") == 0 &&
                         strcmp(name_sink.advertising, "luna-host") == 0,
                         "target_readback");
    failures += require(companion_ble_name_product_entry(
        &name_state, payload, (uint16_t)apply_len, 102u,
        target_restart, &name_sink) == COMPANION_BLE_NAME_OK &&
                         name_sink.calls == 1u, "duplicate_replay");
    failures += require(companion_ble_name_product_entry(
        &name_state, payload, (uint16_t)apply_len, 103u,
        target_restart, &name_sink) == COMPANION_BLE_NAME_COLLISION &&
                         name_sink.calls == 1u, "mismatched_key_fail_closed");

    name_wire(payload, 3u, NAME_STAGE, "stale");
    failures += require(companion_ble_name_product_entry(
        &name_state, payload, (uint16_t)sizeof(payload), 104u,
        target_restart, &name_sink) == COMPANION_BLE_NAME_OK, "stage_reset_fixture");
    name_wire(payload, 4u, NAME_RESET, NULL);
    failures += require(companion_ble_name_product_entry(
        &name_state, payload, (uint16_t)sizeof(payload), 105u,
        target_restart, &name_sink) == COMPANION_BLE_NAME_OK &&
                         strcmp(name_sink.gap, COMPANION_BLE_NAME_DEFAULT) == 0,
                         "reset_discards_pending");

    companion_ble_name_set_connection(&name_state, true, false);
    name_wire(payload, 5u, NAME_STAGE, "connected");
    failures += require(companion_ble_name_product_entry(
        &name_state, payload, (uint16_t)sizeof(payload), 106u,
        target_restart, &name_sink) == COMPANION_BLE_NAME_OK, "connected_stage");
    name_wire(payload, 6u, NAME_APPLY, NULL);
    failures += require(companion_ble_name_product_entry(
        &name_state, payload, (uint16_t)sizeof(payload), 107u,
        target_restart, &name_sink) == COMPANION_BLE_NAME_CONNECTED &&
                         name_sink.calls == 2u, "connected_apply_blocked");
    companion_ble_name_set_connection(&name_state, false, false);
    name_wire(payload, 8u, NAME_APPLY, NULL);
    failures += require(companion_ble_name_product_entry(
        &name_state, payload, (uint16_t)sizeof(payload), 108u,
        target_restart, &name_sink) == COMPANION_BLE_NAME_OK &&
                         name_sink.calls == 3u, "disconnect_reconnect_apply");

    device_sink_t device = {7u, 0x55u, 0u, 0u, 0u, false, false, false, false};
    const companion_device_control_transport_t transport = {
        &device, read_capabilities, read_settings, write_settings, invoke_command};
    companion_platform_device_control_bind(&transport);
    product_context_t product;
    companion_product_entry_glue_init(&product.glue, &product,
                                      product_begin_settings, product_begin_meeting);
    uint32_t revision = 0u;
    uint64_t mask = 0u;
    failures += require(companion_platform_device_control_capabilities_event(
        100u, 201u, 301u, &revision, &mask) && revision == 7u && mask == 0x55u,
        "device_capabilities");
    uint8_t settings_payload[sizeof(companion_gatt_settings_v1_t)] = {0};
    settings_payload[0] = 1u;
    uint32_t ack = 0u;
    bool replayed = false;
    failures += require(gatt_settings_entry(&product, settings_payload,
        sizeof(settings_payload), 101u, 1101u, revision, 0u, false,
        &ack, &replayed) && ack == 8u && !replayed,
        "device_settings_product_gatt");
    unsigned writes = device.writes;
    failures += require(gatt_settings_entry(&product, settings_payload,
        sizeof(settings_payload), 101u, 1101u, revision, 0u, false,
        &ack, &replayed) && replayed && device.writes == writes,
        "device_settings_duplicate");
    failures += require(!gatt_settings_entry(&product, settings_payload,
        sizeof(settings_payload) - 1u, 101u, 1101u, revision, 0u, false,
        &ack, &replayed) &&
                         device.writes == writes, "malformed_no_transport");
    failures += require(!gatt_settings_entry(&product, settings_payload,
        sizeof(settings_payload), 101u, 1101u, revision, 0xA5A5u, true,
        &ack, &replayed) && device.writes == writes,
        "same_operation_different_key");
    settings_payload[6] = 1u;
    failures += require(!gatt_settings_entry(&product, settings_payload,
        sizeof(settings_payload), 2000u, 1000u, revision, 0u, false,
        &ack, &replayed) && device.writes == writes,
        "deadline_fail_closed");
    unsigned invokes = device.invokes;
    uint8_t meeting_payload[sizeof(companion_gatt_meeting_control_v1_t)] = {0};
    meeting_payload[0] = 1u;
    meeting_payload[1] = 9u;
    meeting_payload[4] = 1u;
    bool meeting_ok = gatt_invoke_entry(&product, meeting_payload,
        sizeof(meeting_payload), 102u, 1102u, 0u, false, &replayed);
    fprintf(stderr, "meeting-first ok=%d replay=%d invokes=%u\n",
            meeting_ok ? 1 : 0, replayed ? 1 : 0, device.invokes);
    failures += require(meeting_ok && !replayed, "re_pair_command");
    failures += require(gatt_invoke_entry(&product, meeting_payload,
        sizeof(meeting_payload), 102u, 1102u, 0u, false, &replayed) &&
                         replayed && device.invokes == invokes + 1u,
        "re_pair_duplicate_replay");

    device.fail_invoke = true;
    uint8_t failed_meeting_payload[sizeof(meeting_payload)];
    memcpy(failed_meeting_payload, meeting_payload, sizeof(meeting_payload));
    failed_meeting_payload[4] = 2u;
    bool failure_ok = gatt_invoke_entry(&product, failed_meeting_payload,
        sizeof(meeting_payload), 103u, 1103u, 0u, false, &replayed);
    fprintf(stderr, "meeting-failure ok=%d replay=%d invokes=%u\n",
            failure_ok ? 1 : 0, replayed ? 1 : 0, device.invokes);
    failures += require(!failure_ok && !replayed, "transport_failure");
    unsigned failed_invokes = device.invokes;
    failures += require(!gatt_invoke_entry(&product, failed_meeting_payload,
        sizeof(failed_meeting_payload), 103u, 1103u, 0u, false, &replayed) &&
                         replayed && device.invokes == failed_invokes,
        "failed_duplicate_replay");
    device.fail_invoke = false;
    failures += require(!gatt_invoke_entry(&product, meeting_payload,
        sizeof(meeting_payload) - 1u, 0u, 1104u, 0u, false, &replayed), "invalid_operation");
    companion_ble_name_set_connection(&name_state, false, true);
    name_wire(payload, 9u, NAME_STAGE, "busy");
    failures += require(companion_ble_name_product_entry(
        &name_state, payload, (uint16_t)sizeof(payload), 109u,
        target_restart, &name_sink) == COMPANION_BLE_NAME_OK, "busy_stage");

    companion_ble_repair_state_t repair_state;
    repair_sink_t repair_sink = {0u, true, 0u};
    uint8_t repair_payload[sizeof(companion_gatt_repair_control_v1_t)];
    companion_ble_repair_init(&repair_state);
    companion_ble_repair_set_connection(&repair_state, false, false);
    size_t repair_len = repair_wire(repair_payload, 501u, 120000u);
    failures += require(companion_ble_repair_product_entry(
        &repair_state, repair_payload, (uint16_t)repair_len, REPAIR_COMMAND,
        repair_request, &repair_sink) == COMPANION_BLE_REPAIR_OK &&
                         repair_sink.calls == 1u &&
                         repair_sink.last_window_ms == 120000u,
        "repair_product_entry");
    failures += require(companion_ble_repair_product_entry(
        &repair_state, repair_payload, (uint16_t)repair_len, REPAIR_COMMAND,
        repair_request, &repair_sink) == COMPANION_BLE_REPAIR_OK &&
                         repair_sink.calls == 1u, "repair_duplicate_replay");
    failures += require(companion_ble_repair_product_entry(
        &repair_state, repair_payload, (uint16_t)repair_len, REPAIR_COMMAND + 1u,
        repair_request, &repair_sink) == COMPANION_BLE_REPAIR_COLLISION &&
                         repair_sink.calls == 1u, "repair_key_collision");
    companion_ble_repair_set_connection(&repair_state, true, false);
    repair_wire(repair_payload, 502u, 120000u);
    failures += require(companion_ble_repair_product_entry(
        &repair_state, repair_payload, (uint16_t)repair_len, REPAIR_COMMAND,
        repair_request, &repair_sink) == COMPANION_BLE_REPAIR_CONNECTED &&
                         repair_sink.calls == 1u, "repair_connected_blocked");
    companion_ble_repair_set_connection(&repair_state, false, true);
    repair_wire(repair_payload, 503u, 120000u);
    failures += require(companion_ble_repair_product_entry(
        &repair_state, repair_payload, (uint16_t)repair_len, REPAIR_COMMAND,
        repair_request, &repair_sink) == COMPANION_BLE_REPAIR_BUSY &&
                         repair_sink.calls == 1u, "repair_busy_blocked");
    companion_ble_repair_set_connection(&repair_state, false, false);
    repair_sink.succeed = false;
    repair_wire(repair_payload, 504u, 120000u);
    failures += require(companion_ble_repair_product_entry(
        &repair_state, repair_payload, (uint16_t)repair_len, REPAIR_COMMAND,
        repair_request, &repair_sink) == COMPANION_BLE_REPAIR_FAILED &&
                         repair_sink.calls == 2u, "repair_transport_failure");
    failures += require(companion_ble_repair_product_entry(
        &repair_state, repair_payload, (uint16_t)repair_len, REPAIR_COMMAND,
        repair_request, &repair_sink) == COMPANION_BLE_REPAIR_FAILED &&
                         repair_sink.calls == 2u, "repair_failed_replay");
    repair_wire(repair_payload, 505u, 120001u);
    failures += require(companion_ble_repair_product_entry(
        &repair_state, repair_payload, (uint16_t)repair_len, REPAIR_COMMAND,
        repair_request, &repair_sink) == COMPANION_BLE_REPAIR_INVALID &&
                         repair_sink.calls == 2u, "repair_invalid_window");

    if (failures != 0u) {
        fprintf(stderr, "COMP_REQ_562_BLE FAIL count=%u\n", failures);
        return 1;
    }
    printf("COMP_REQ_562_BLE PASS name_target_calls=%u settings_writes=%u invokes=%u "
           "repair_calls=%u repair_capacity=%u replay_capacity=%u trace_capacity=%u "
           "hardware=0 ble_write=0 bond_erase=0 radio=0\n",
           name_sink.calls, device.writes, device.invokes, repair_sink.calls,
           COMPANION_BLE_REPAIR_REPLAY_CAPACITY,
           COMPANION_BLE_NAME_REPLAY_CAPACITY, TRACE_CAPACITY);
    return 0;
}
