#include "companion_platform_contracts.h"

#include <stdint.h>

#include "denzic_audio_transport_v1.h"
#include "denzic_device_control_v1.h"
#include "denzic_diag_log_gatt_v1.h"
#include "denzic_ota_orchestration_v1.h"
#include "denzic_ota_v1_generated.h"

bool companion_platform_contract_probe(void) {
    denzic_audio_transport_v1_pacing_t pacing;
    denzic_device_control_v1_context_t device;
    uint8_t packet[DENZIC_OBSERVABILITY_V1_DIAG_LOG_CHUNK_HEADER_BYTES +
                   DENZIC_OBSERVABILITY_V1_DIAG_LOG_EVENT_WIRE_BYTES] = {0};
    const uint8_t *payload = NULL;
    size_t payload_len = 0;
    uint16_t event_count = 0;
    uint32_t global_offset = 0;
    uint32_t events_crc32 = 0;
    denzic_ota_orchestration_v1_blocker_inputs_t ota_inputs = {0};

    if (DENZIC_AUDIO_TRANSPORT_V1_PROTOCOL_VERSION != 1u ||
        DENZIC_DEVICE_CONTROL_V1_CONTRACT_VERSION != 1u ||
        DENZIC_OBSERVABILITY_V1_CONTRACT_VERSION != 1u ||
        DENZIC_OTA_V1_PROTOCOL_VERSION != 1u) {
        return false;
    }
    companion_platform_audio_transport_init(&pacing);
    if (companion_platform_audio_transport_note_pcm_sent(&pacing, 480u) == UINT32_MAX) {
        return false;
    }
    denzic_device_control_v1_init(&device, DENZIC_DEVICE_CONTROL_V1_TRANSPORT_BLE);
    if (!denzic_device_control_v1_format_settings_revision(
            (char *)packet, sizeof(packet), 1u)) {
        return false;
    }
    denzic_diag_log_gatt_v1_encode_chunk_header(packet, 1u, 0u, 0u);
    if (denzic_diag_log_gatt_v1_decode_chunk(
            packet, sizeof(packet), &event_count, &global_offset,
            &events_crc32, &payload, &payload_len) != DENZIC_DIAG_LOG_GATT_V1_CHUNK_OK ||
        event_count != 1u || payload_len != DENZIC_OBSERVABILITY_V1_DIAG_LOG_EVENT_WIRE_BYTES) {
        return false;
    }
    ota_inputs.battery_valid = true;
    ota_inputs.battery_percent = DENZIC_OTA_ORCHESTRATION_V1_MIN_BATTERY_PERCENT;
    ota_inputs.has_update_partition = true;
    return denzic_ota_orchestration_v1_evaluate_blocker(
               &ota_inputs, DENZIC_OTA_ORCHESTRATION_V1_MIN_BATTERY_PERCENT) ==
           DENZIC_OTA_ORCHESTRATION_V1_BLOCKER_NONE;
}

void companion_platform_audio_transport_init(
    denzic_audio_transport_v1_pacing_t *pacing) {
    denzic_audio_transport_v1_pacing_init(pacing);
}

uint32_t companion_platform_audio_transport_note_pcm_sent(
    denzic_audio_transport_v1_pacing_t *pacing,
    uint32_t packet_pcm_bytes) {
    return denzic_audio_transport_v1_pacing_note_pcm_sent(pacing, packet_pcm_bytes);
}
