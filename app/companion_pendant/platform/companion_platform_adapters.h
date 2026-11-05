#ifndef COMPANION_PLATFORM_ADAPTERS_H
#define COMPANION_PLATFORM_ADAPTERS_H

#include "denzic_device_control_v1.h"
#include "denzic_diag_log_gatt_v1.h"
#include "denzic_ota_orchestration_v1.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define COMPANION_PLATFORM_TRACE_CAPACITY 16u
#define COMPANION_PLATFORM_DIAG_EVENT_CAPACITY 8u

typedef bool (*companion_device_capabilities_fn)(void *, uint64_t, uint64_t, uint32_t *, uint64_t *);
typedef bool (*companion_device_settings_fn)(void *, uint64_t, uint64_t, uint32_t *);
typedef bool (*companion_device_write_fn)(void *, uint64_t, uint64_t, uint32_t, uint32_t *);
typedef bool (*companion_device_invoke_fn)(void *, uint64_t, uint64_t, uint32_t);

typedef struct {
    void *context;
    companion_device_capabilities_fn read_capabilities;
    companion_device_settings_fn read_settings;
    companion_device_write_fn write_settings;
    companion_device_invoke_fn invoke_command;
} companion_device_control_transport_t;

typedef struct {
    denzic_device_control_v1_context_t core;
    companion_device_control_transport_t transport;
    uint32_t transport_side_effects;
    uint32_t begin_count;
    uint32_t inflight_count;
    uint32_t terminal_count;
} companion_device_control_adapter_t;

void companion_device_control_adapter_init(
    companion_device_control_adapter_t *,
    const companion_device_control_transport_t *);
bool companion_device_control_read_capabilities(
    companion_device_control_adapter_t *, uint64_t, uint64_t, uint32_t *,
    uint64_t *);
bool companion_device_control_read_settings(
    companion_device_control_adapter_t *, uint64_t, uint64_t, uint32_t *);
bool companion_device_control_write_settings(
    companion_device_control_adapter_t *, uint64_t, uint64_t, uint32_t,
    uint32_t *);
bool companion_device_control_invoke_command(
    companion_device_control_adapter_t *, uint64_t, uint64_t, uint32_t);
bool companion_device_control_expire(
    companion_device_control_adapter_t *, uint32_t);

void companion_platform_device_control_bind(
    const companion_device_control_transport_t *);

/* Product event bridges used by the existing STM32WB GATT entry points. */
bool companion_platform_device_control_capabilities_event(
    uint32_t now_ms, uint64_t operation_id, uint64_t idempotency_key,
    uint32_t *revision, uint64_t *mask);
bool companion_platform_device_control_settings_event(
    uint32_t now_ms, uint64_t operation_id, uint64_t idempotency_key,
    uint32_t expected_revision, uint32_t *ack_revision);
bool companion_platform_device_control_invoke_event(
    uint32_t now_ms, uint64_t operation_id, uint64_t idempotency_key,
    uint32_t command);

typedef bool (*companion_diag_count_fn)(void *, uint16_t *);
typedef bool (*companion_diag_start_fn)(void *);
typedef bool (*companion_diag_read_fn)(void *, uint32_t, uint8_t *, size_t,
                                       size_t *);
typedef bool (*companion_diag_stop_fn)(void *);

typedef struct {
    void *context;
    companion_diag_count_fn count;
    companion_diag_start_fn start;
    companion_diag_read_fn read;
    companion_diag_stop_fn stop;
} companion_diag_transport_t;

typedef struct {
    uint16_t observed_events;
    uint16_t retained_events;
    uint16_t dropped_events;
    uint16_t capacity;
    uint32_t reads;
    uint32_t stop_calls;
    uint32_t crc_failures;
    uint32_t offset_failures;
    bool started;
    bool stopped;
    bool overflow;
} companion_diag_result_t;

bool companion_diag_log_pull(
    const companion_diag_transport_t *, companion_diag_result_t *);
bool companion_platform_diag_encode_chunk(
    uint32_t global_offset, uint16_t event_count, const uint8_t *events,
    size_t event_bytes, uint8_t *out, size_t out_capacity, size_t *out_bytes);

typedef enum {
    COMPANION_OTA_TARGET_STM32WB = 1,
    COMPANION_OTA_TARGET_ESP = 2,
} companion_ota_target_t;

typedef struct {
    uint32_t schema_version;
    companion_ota_target_t target;
    const char *platform_adapter;
    const char *rollback_strategy;
    size_t image_size;
    size_t partition_size;
} companion_ota_manifest_v2_t;

typedef struct {
    bool accepted;
    bool transport_contact;
    bool apply_requested;
    denzic_ota_orchestration_v1_blocker_t blocker;
} companion_ota_admission_result_t;

companion_ota_admission_result_t companion_ota_manifest_v2_admit(
    const companion_ota_manifest_v2_t *,
    const denzic_ota_orchestration_v1_blocker_inputs_t *);
companion_ota_admission_result_t companion_platform_ota_readiness_event(
    bool recording_active, bool ble_audio_active, bool diag_export_active,
    uint8_t battery_percent, bool has_update_partition, size_t image_size,
    size_t partition_size, bool pending_verify, bool post_update_self_check);

#endif
