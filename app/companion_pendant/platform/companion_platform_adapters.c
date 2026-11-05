#include "companion_platform_adapters.h"

#include <string.h>

static uint32_t product_now_ms;

static denzic_device_control_v1_decision_t begin(
    companion_device_control_adapter_t *a, uint64_t id, uint64_t key,
    denzic_device_control_v1_operation_kind_t kind, uint32_t expected,
    uint32_t now) {
    denzic_device_control_v1_request_t request = {0};
    request.operation_id = id;
    request.idempotency_key = key;
    request.kind = kind;
    request.timeout_ms = 1000u;
    request.target_id = 1u;
    request.expected_settings_revision = expected;
    (void)now;
    return denzic_device_control_v1_begin(&a->core, &request, product_now_ms);
}

static bool finish(companion_device_control_adapter_t *a,
                   uint64_t id, uint64_t key, bool ok) {
    denzic_device_control_v1_decision_t d = denzic_device_control_v1_complete(
        &a->core, id, key,
        ok ? DENZIC_DEVICE_CONTROL_V1_OPERATION_RESULT_SUCCEEDED
           : DENZIC_DEVICE_CONTROL_V1_OPERATION_RESULT_FAILED,
        ok ? DENZIC_DEVICE_CONTROL_V1_ERROR_CATEGORY_NONE
           : DENZIC_DEVICE_CONTROL_V1_ERROR_CATEGORY_TRANSPORT);
    a->terminal_count += 1u; a->inflight_count = 0u;
    return ok && d.result == DENZIC_DEVICE_CONTROL_V1_OPERATION_RESULT_SUCCEEDED;
}

void companion_device_control_adapter_init(
    companion_device_control_adapter_t *a,
    const companion_device_control_transport_t *transport) {
    memset(a, 0, sizeof(*a));
    if (transport != NULL) a->transport = *transport;
    denzic_device_control_v1_init(&a->core, DENZIC_DEVICE_CONTROL_V1_TRANSPORT_BLE);
    denzic_device_control_v1_set_lifecycle(
        &a->core, DENZIC_DEVICE_CONTROL_V1_LIFECYCLE_STATE_READY);
}

bool companion_device_control_read_capabilities(
    companion_device_control_adapter_t *a, uint64_t id, uint64_t key,
    uint32_t *revision, uint64_t *mask) {
    denzic_device_control_v1_decision_t d = begin(a, id, key,
        DENZIC_DEVICE_CONTROL_V1_OPERATION_KIND_READ_CAPABILITIES, 0u, 0u);
    if (!d.execute) return d.result == DENZIC_DEVICE_CONTROL_V1_OPERATION_RESULT_SUCCEEDED;
    a->begin_count += 1u; a->inflight_count = 1u;
    bool ok = a->transport.read_capabilities != NULL &&
              a->transport.read_capabilities(a->transport.context, id, key, revision, mask);
    if (ok) ok = denzic_device_control_v1_report_capabilities(&a->core, id, key,
                                                               *revision, *mask);
    if (ok) { a->transport_side_effects += 1u; a->terminal_count += 1u; a->inflight_count = 0u; return true; }
    return finish(a, id, key, false);
}

bool companion_device_control_read_settings(
    companion_device_control_adapter_t *a, uint64_t id, uint64_t key,
    uint32_t *revision) {
    denzic_device_control_v1_decision_t d = begin(a, id, key,
        DENZIC_DEVICE_CONTROL_V1_OPERATION_KIND_READ_SETTING, 0u, 0u);
    if (!d.execute) return d.result == DENZIC_DEVICE_CONTROL_V1_OPERATION_RESULT_SUCCEEDED;
    a->begin_count += 1u; a->inflight_count = 1u;
    bool ok = a->transport.read_settings != NULL &&
              a->transport.read_settings(a->transport.context, id, key, revision);
    if (ok) ok = denzic_device_control_v1_confirm_setting_readback(&a->core, id, key, *revision);
    if (ok) { a->transport_side_effects += 1u; a->terminal_count += 1u; a->inflight_count = 0u; return true; }
    return finish(a, id, key, false);
}

bool companion_device_control_write_settings(
    companion_device_control_adapter_t *a, uint64_t id, uint64_t key,
    uint32_t expected, uint32_t *ack_revision) {
    denzic_device_control_v1_decision_t d = begin(a, id, key,
        DENZIC_DEVICE_CONTROL_V1_OPERATION_KIND_WRITE_SETTING, expected, 0u);
    if (!d.execute) return d.result == DENZIC_DEVICE_CONTROL_V1_OPERATION_RESULT_SUCCEEDED;
    a->begin_count += 1u; a->inflight_count = 1u;
    bool ok = a->transport.write_settings != NULL &&
              a->transport.write_settings(a->transport.context, id, key, expected, ack_revision);
    if (ok) ok = denzic_device_control_v1_acknowledge_setting_write(&a->core, id, key,
                                                                     *ack_revision);
    if (ok) {
        uint32_t readback = 0u;
        ok = a->transport.read_settings != NULL &&
             a->transport.read_settings(a->transport.context, id, key, &readback) &&
             denzic_device_control_v1_confirm_setting_readback(&a->core, id, key, readback) &&
             readback >= *ack_revision;
    }
    if (ok) { a->transport_side_effects += 1u; a->terminal_count += 1u; a->inflight_count = 0u; return true; }
    return finish(a, id, key, false);
}

bool companion_device_control_invoke_command(
    companion_device_control_adapter_t *a, uint64_t id, uint64_t key,
    uint32_t command) {
    denzic_device_control_v1_decision_t d = begin(a, id, key,
        DENZIC_DEVICE_CONTROL_V1_OPERATION_KIND_INVOKE_COMMAND, 0u, 0u);
    if (!d.execute) return d.result == DENZIC_DEVICE_CONTROL_V1_OPERATION_RESULT_SUCCEEDED;
    a->begin_count += 1u; a->inflight_count = 1u;
    bool ok = a->transport.invoke_command != NULL &&
              a->transport.invoke_command(a->transport.context, id, key, command);
    if (ok) a->transport_side_effects += 1u;
    return finish(a, id, key, ok);
}

bool companion_device_control_expire(companion_device_control_adapter_t *a, uint32_t now) {
    return denzic_device_control_v1_expire(&a->core, now);
}

static companion_device_control_adapter_t product_device_adapter;
static bool product_device_adapter_ready;
static companion_device_control_transport_t product_device_transport;
static void product_device_init(void) {
    if (!product_device_adapter_ready) {
        companion_device_control_adapter_init(&product_device_adapter,
                                              &product_device_transport);
        product_device_adapter_ready = true;
    }
}
void companion_platform_device_control_bind(
    const companion_device_control_transport_t *transport) {
    product_device_adapter_ready = false;
    memset(&product_device_transport, 0, sizeof(product_device_transport));
    if (transport != NULL) product_device_transport = *transport;
}
bool companion_platform_device_control_capabilities_event(
    uint32_t now_ms, uint64_t operation_id, uint64_t idempotency_key,
    uint32_t *revision, uint64_t *mask) {
    product_now_ms = now_ms; product_device_init();
    if (product_device_transport.read_capabilities == NULL) return false;
    return companion_device_control_read_capabilities(&product_device_adapter,
        operation_id, idempotency_key, revision, mask);
}
bool companion_platform_device_control_settings_event(
    uint32_t now_ms, uint64_t operation_id, uint64_t idempotency_key,
    uint32_t expected_revision, uint32_t *ack_revision) {
    product_now_ms = now_ms; product_device_init();
    if (product_device_transport.write_settings == NULL) return false;
    return companion_device_control_write_settings(&product_device_adapter,
        operation_id, idempotency_key, expected_revision, ack_revision);
}
bool companion_platform_device_control_invoke_event(
    uint32_t now_ms, uint64_t operation_id, uint64_t idempotency_key,
    uint32_t command) {
    product_now_ms = now_ms; product_device_init();
    if (product_device_transport.invoke_command == NULL) return false;
    return companion_device_control_invoke_command(&product_device_adapter,
        operation_id, idempotency_key, command);
}

static uint32_t crc32(const uint8_t *p, size_t n) {
    uint32_t c = 0xffffffffu;
    for (size_t i = 0; i < n; ++i) {
        c ^= p[i];
        for (unsigned b = 0; b < 8u; ++b) c = (c >> 1) ^ (0xedb88320u & (uint32_t)-(int)(c & 1u));
    }
    return ~c;
}

bool companion_diag_log_pull(const companion_diag_transport_t *t,
                             companion_diag_result_t *out) {
    uint8_t packet[DENZIC_OBSERVABILITY_V1_DIAG_LOG_CHUNK_HEADER_BYTES +
                   DENZIC_OBSERVABILITY_V1_DIAG_LOG_EVENT_WIRE_BYTES * COMPANION_PLATFORM_DIAG_EVENT_CAPACITY];
    if (out == NULL) return false;
    memset(out, 0, sizeof(*out));
    out->capacity = COMPANION_PLATFORM_DIAG_EVENT_CAPACITY;
    uint16_t advertised = 0;
    if (t == NULL || t->count == NULL || t->start == NULL || t->read == NULL || t->stop == NULL ||
        !t->count(t->context, &advertised) || !t->start(t->context)) return false;
    out->started = true;
    bool ok = true;
    uint32_t expected = 0u;
    if (advertised > out->capacity) {
        out->overflow = true;
        out->dropped_events = (uint16_t)(advertised - out->capacity);
        ok = false;
    }
    while (ok && expected < advertised) {
        size_t len = 0;
        if (!t->read(t->context, expected, packet, sizeof(packet), &len)) { ok = false; break; }
        out->reads += 1u;
        uint16_t count = 0; uint32_t offset = 0; uint32_t wire_crc = 0;
        const uint8_t *payload = NULL; size_t payload_len = 0;
        if (denzic_diag_log_gatt_v1_decode_chunk(packet, len, &count, &offset, &wire_crc,
                                                  &payload, &payload_len) != DENZIC_DIAG_LOG_GATT_V1_CHUNK_OK) { ok = false; break; }
        if (offset != expected) { out->offset_failures += 1u; ok = false; break; }
        if (count == 0u || expected + count > out->capacity) { out->overflow = true; out->dropped_events = (uint16_t)(advertised - out->capacity); ok = false; break; }
        if (crc32(payload, payload_len) != wire_crc) { out->crc_failures += 1u; ok = false; break; }
        out->observed_events = (uint16_t)(out->observed_events + count);
        out->retained_events = out->observed_events;
        expected += count;
    }
    if (!t->stop(t->context)) ok = false;
    out->stop_calls = 1u; out->stopped = true;
    return ok && expected == advertised;
}

bool companion_platform_diag_encode_chunk(
    uint32_t global_offset, uint16_t event_count, const uint8_t *events,
    size_t event_bytes, uint8_t *out, size_t out_capacity, size_t *out_bytes) {
    const size_t header = DENZIC_OBSERVABILITY_V1_DIAG_LOG_CHUNK_HEADER_BYTES;
    const size_t expected = (size_t)event_count *
        DENZIC_OBSERVABILITY_V1_DIAG_LOG_EVENT_WIRE_BYTES;
    uint16_t decoded_count = 0u; uint32_t decoded_offset = 0u;
    uint32_t decoded_crc = 0u; const uint8_t *decoded_payload = NULL;
    size_t decoded_len = 0u;
    if (out == NULL || out_bytes == NULL || (event_count != 0u && events == NULL) ||
        event_count > COMPANION_PLATFORM_DIAG_EVENT_CAPACITY || event_bytes != expected ||
        out_capacity < header + event_bytes) return false;
    denzic_diag_log_gatt_v1_encode_chunk_header(out, event_count, global_offset,
        crc32(events, event_bytes));
    if (event_bytes != 0u) memcpy(out + header, events, event_bytes);
    *out_bytes = header + event_bytes;
    return denzic_diag_log_gatt_v1_decode_chunk(out, *out_bytes, &decoded_count,
           &decoded_offset, &decoded_crc, &decoded_payload, &decoded_len) ==
           DENZIC_DIAG_LOG_GATT_V1_CHUNK_OK && decoded_count == event_count &&
           decoded_offset == global_offset && decoded_len == event_bytes &&
           decoded_crc == crc32(events, event_bytes) &&
           (event_bytes == 0u || memcmp(decoded_payload, events, event_bytes) == 0);
}

companion_ota_admission_result_t companion_ota_manifest_v2_admit(
    const companion_ota_manifest_v2_t *m,
    const denzic_ota_orchestration_v1_blocker_inputs_t *inputs) {
    companion_ota_admission_result_t r = {0};
    if (m == NULL || inputs == NULL || m->schema_version != 2u ||
        m->target != COMPANION_OTA_TARGET_STM32WB ||
        m->platform_adapter == NULL || m->rollback_strategy == NULL ||
        strcmp(m->platform_adapter, "stm32wb_denzic_ota_v1") != 0 ||
        strcmp(m->rollback_strategy, "stm32wb_resident_bootloader_pending_verify") != 0 ||
        !denzic_ota_orchestration_v1_image_size_accepted(m->image_size, 0u, m->partition_size)) return r;
    r.blocker = denzic_ota_orchestration_v1_evaluate_blocker(
        inputs, DENZIC_OTA_ORCHESTRATION_V1_MIN_BATTERY_PERCENT);
    r.accepted = r.blocker == DENZIC_OTA_ORCHESTRATION_V1_BLOCKER_NONE;
    r.transport_contact = false;
    r.apply_requested = false;
    return r;
}

companion_ota_admission_result_t companion_platform_ota_readiness_event(
    bool recording_active, bool ble_audio_active, bool diag_export_active,
    uint8_t battery_percent, bool has_update_partition, size_t image_size,
    size_t partition_size, bool pending_verify, bool post_update_self_check) {
    const companion_ota_manifest_v2_t manifest = {
        2u, COMPANION_OTA_TARGET_STM32WB, "stm32wb_denzic_ota_v1",
        "stm32wb_resident_bootloader_pending_verify", image_size, partition_size};
    const denzic_ota_orchestration_v1_blocker_inputs_t inputs = {
        pending_verify, post_update_self_check, recording_active, ble_audio_active,
        diag_export_active, true, battery_percent, has_update_partition};
    return companion_ota_manifest_v2_admit(&manifest, &inputs);
}
