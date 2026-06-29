#include "companion_gatt_stm32wb.h"

#include "common_blesvc.h"

#include <string.h>

#ifndef __WEAK
#define __WEAK __attribute__((weak))
#endif

#define COMPANION_GATT_SCHEMA_VERSION 1u
#define COMPANION_GATT_ENCRY_KEY_SIZE 10u
#define COMPANION_GATT_VALUE_HANDLE_OFFSET 1u
#define COMPANION_GATT_CCCD_HANDLE_OFFSET 2u

typedef struct {
    companion_gatt_char_id_t id;
    uint16_t uuid_prefix;
    uint16_t value_len;
    uint8_t properties;
    uint8_t event_mask;
    uint8_t variable;
} companion_gatt_char_def_t;

typedef struct {
    uint16_t uuid_prefix;
    uint8_t attr_records;
    uint8_t char_count;
    const companion_gatt_char_def_t *chars;
} companion_gatt_service_def_t;

typedef struct {
    uint16_t char_service_handles[COMPANION_GATT_CHAR_COUNT];
    uint16_t char_handles[COMPANION_GATT_CHAR_COUNT];
    companion_gatt_event_t queue[COMPANION_GATT_QUEUE_DEPTH];
    uint8_t head;
    uint8_t tail;
    uint8_t count;
    uint8_t overflow_count;
} companion_gatt_context_t;

static const companion_gatt_char_def_t COMPANION_GATT_DEVICE_STATUS_CHARS[] = {
    {COMPANION_GATT_CHAR_DEVICE_STATUS, 0x1001u, 64u, CHAR_PROP_READ | CHAR_PROP_NOTIFY, GATT_DONT_NOTIFY_EVENTS, 1u},
    {COMPANION_GATT_CHAR_BATTERY_CHARGE, 0x1002u, 16u, CHAR_PROP_READ | CHAR_PROP_NOTIFY, GATT_DONT_NOTIFY_EVENTS, 1u},
};

static const companion_gatt_char_def_t COMPANION_GATT_EPAPER_CHARS[] = {
    {COMPANION_GATT_CHAR_E_PAPER_CARD_WRITE, 0x2001u, COMPANION_GATT_MAX_PAYLOAD_BYTES, CHAR_PROP_WRITE, GATT_NOTIFY_ATTRIBUTE_WRITE, 1u},
    {COMPANION_GATT_CHAR_E_PAPER_CARD_STATUS, 0x2002u, 32u, CHAR_PROP_READ | CHAR_PROP_NOTIFY, GATT_DONT_NOTIFY_EVENTS, 1u},
};

static const companion_gatt_char_def_t COMPANION_GATT_RECORDING_CHARS[] = {
    {COMPANION_GATT_CHAR_RECORDING_CONTROL, 0x3001u, 32u, CHAR_PROP_WRITE | CHAR_PROP_NOTIFY, GATT_NOTIFY_ATTRIBUTE_WRITE, 1u},
    {COMPANION_GATT_CHAR_RECORDING_LIST, 0x3002u, COMPANION_GATT_MAX_PAYLOAD_BYTES, CHAR_PROP_READ | CHAR_PROP_NOTIFY, GATT_DONT_NOTIFY_EVENTS, 1u},
    {COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL, 0x3003u, COMPANION_GATT_MAX_PAYLOAD_BYTES, CHAR_PROP_WRITE | CHAR_PROP_NOTIFY, GATT_NOTIFY_ATTRIBUTE_WRITE, 1u},
};

static const companion_gatt_char_def_t COMPANION_GATT_SETTINGS_CHARS[] = {
    {COMPANION_GATT_CHAR_SETTINGS, 0x4001u, 96u, CHAR_PROP_READ | CHAR_PROP_WRITE | CHAR_PROP_NOTIFY, GATT_NOTIFY_ATTRIBUTE_WRITE, 1u},
    {COMPANION_GATT_CHAR_BLE_NAME_CONFIG, 0x4002u, 64u, CHAR_PROP_READ | CHAR_PROP_WRITE | CHAR_PROP_NOTIFY, GATT_NOTIFY_ATTRIBUTE_WRITE, 1u},
};

static const companion_gatt_char_def_t COMPANION_GATT_DIAGNOSTICS_CHARS[] = {
    {COMPANION_GATT_CHAR_DIAGNOSTICS_LOG_PULL, 0x5001u, COMPANION_GATT_MAX_PAYLOAD_BYTES, CHAR_PROP_WRITE | CHAR_PROP_NOTIFY, GATT_NOTIFY_ATTRIBUTE_WRITE, 1u},
};

static const companion_gatt_char_def_t COMPANION_GATT_PRIVACY_CHARS[] = {
    {COMPANION_GATT_CHAR_DELETE_PRIVACY, 0x6001u, 96u, CHAR_PROP_WRITE | CHAR_PROP_NOTIFY, GATT_NOTIFY_ATTRIBUTE_WRITE, 1u},
};

static const companion_gatt_char_def_t COMPANION_GATT_OTA_CHARS[] = {
    {COMPANION_GATT_CHAR_OTA_READINESS, 0x7001u, 128u, CHAR_PROP_READ | CHAR_PROP_NOTIFY, GATT_DONT_NOTIFY_EVENTS, 1u},
};

static const companion_gatt_char_def_t COMPANION_GATT_MEETING_CHARS[] = {
    {COMPANION_GATT_CHAR_MEETING_CONTROL, 0x8001u, 32u, CHAR_PROP_WRITE | CHAR_PROP_NOTIFY, GATT_NOTIFY_ATTRIBUTE_WRITE, 1u},
    {COMPANION_GATT_CHAR_MEETING_STATUS, 0x8002u, 64u, CHAR_PROP_READ | CHAR_PROP_NOTIFY, GATT_DONT_NOTIFY_EVENTS, 1u},
};

static const companion_gatt_char_def_t COMPANION_GATT_SENSOR_CHARS[] = {
    {COMPANION_GATT_CHAR_IMU_STATUS, 0x9001u, 64u, CHAR_PROP_READ | CHAR_PROP_NOTIFY, GATT_DONT_NOTIFY_EVENTS, 1u},
};

static const companion_gatt_char_def_t COMPANION_GATT_AUDIO_OUTPUT_CHARS[] = {
    {COMPANION_GATT_CHAR_SPEAKER_CONTROL, 0xa001u, 32u, CHAR_PROP_WRITE | CHAR_PROP_NOTIFY, GATT_NOTIFY_ATTRIBUTE_WRITE, 1u},
    {COMPANION_GATT_CHAR_SPEAKER_STATUS, 0xa002u, 64u, CHAR_PROP_READ | CHAR_PROP_NOTIFY, GATT_DONT_NOTIFY_EVENTS, 1u},
    {COMPANION_GATT_CHAR_WAKE_WORD_CONTROL, 0xa003u, 32u, CHAR_PROP_WRITE | CHAR_PROP_NOTIFY, GATT_NOTIFY_ATTRIBUTE_WRITE, 1u},
    {COMPANION_GATT_CHAR_WAKE_WORD_STATUS, 0xa004u, 64u, CHAR_PROP_READ | CHAR_PROP_NOTIFY, GATT_DONT_NOTIFY_EVENTS, 1u},
};

static const companion_gatt_service_def_t COMPANION_GATT_SERVICES[] = {
    {0x0001u, 7u, 2u, COMPANION_GATT_DEVICE_STATUS_CHARS},
    {0x0002u, 7u, 2u, COMPANION_GATT_EPAPER_CHARS},
    {0x0003u, 10u, 3u, COMPANION_GATT_RECORDING_CHARS},
    {0x0004u, 7u, 2u, COMPANION_GATT_SETTINGS_CHARS},
    {0x0005u, 4u, 1u, COMPANION_GATT_DIAGNOSTICS_CHARS},
    {0x0006u, 4u, 1u, COMPANION_GATT_PRIVACY_CHARS},
    {0x0007u, 4u, 1u, COMPANION_GATT_OTA_CHARS},
    {0x0008u, 7u, 2u, COMPANION_GATT_MEETING_CHARS},
    {0x0009u, 4u, 1u, COMPANION_GATT_SENSOR_CHARS},
    {0x000au, 13u, 4u, COMPANION_GATT_AUDIO_OUTPUT_CHARS},
};

PLACE_IN_SECTION("BLE_DRIVER_CONTEXT")
static companion_gatt_context_t s_companion_gatt;

static SVCCTL_EvtAckStatus_t companion_gatt_stm32wb_event_handler(void *event);

static void companion_gatt_make_uuid(uint16_t prefix, uint8_t out_uuid[16])
{
    static const uint8_t suffix[12] = {
        0x00, 0x00, 0x7c, 0x1b,
        0x2d, 0x6c, 0x6f, 0x9d,
        0x3d, 0x4f, 0x7d, 0x7b,
    };
    memcpy(out_uuid, suffix, sizeof(suffix));
    out_uuid[12] = (uint8_t)(prefix & 0xffu);
    out_uuid[13] = (uint8_t)((prefix >> 8) & 0xffu);
    out_uuid[14] = 0x7au;
    out_uuid[15] = 0x8fu;
}

static uint8_t companion_gatt_is_value_handle(uint16_t attr_handle,
                                              uint16_t char_handle)
{
    return attr_handle == (uint16_t)(char_handle + COMPANION_GATT_VALUE_HANDLE_OFFSET) ||
           attr_handle == char_handle;
}

static uint8_t companion_gatt_is_cccd_handle(uint16_t attr_handle,
                                             uint16_t char_handle)
{
    return attr_handle == (uint16_t)(char_handle + COMPANION_GATT_CCCD_HANDLE_OFFSET);
}

static const companion_gatt_char_def_t *companion_gatt_find_char_by_handle(
    uint16_t attr_handle,
    uint8_t *is_cccd)
{
    if (is_cccd != 0) {
        *is_cccd = 0u;
    }

    for (uint8_t id = 0u; id < (uint8_t)COMPANION_GATT_CHAR_COUNT; ++id) {
        uint16_t char_handle = s_companion_gatt.char_handles[id];
        if (char_handle == 0u) {
            continue;
        }
        for (size_t s = 0u; s < sizeof(COMPANION_GATT_SERVICES) / sizeof(COMPANION_GATT_SERVICES[0]); ++s) {
            const companion_gatt_service_def_t *service = &COMPANION_GATT_SERVICES[s];
            for (uint8_t c = 0u; c < service->char_count; ++c) {
                const companion_gatt_char_def_t *def = &service->chars[c];
                if ((uint8_t)def->id != id) {
                    continue;
                }
                if (companion_gatt_is_value_handle(attr_handle, char_handle)) {
                    return def;
                }
                if ((def->properties & (CHAR_PROP_NOTIFY | CHAR_PROP_INDICATE)) != 0u &&
                    companion_gatt_is_cccd_handle(attr_handle, char_handle)) {
                    if (is_cccd != 0) {
                        *is_cccd = 1u;
                    }
                    return def;
                }
            }
        }
    }

    return 0;
}

static bool companion_gatt_enqueue(companion_gatt_event_type_t type,
                                   companion_gatt_char_id_t char_id,
                                   uint16_t attr_handle,
                                   const uint8_t *payload,
                                   uint16_t payload_len)
{
    if (payload_len > COMPANION_GATT_MAX_PAYLOAD_BYTES ||
        (payload_len != 0u && payload == 0)) {
        return false;
    }
    if (s_companion_gatt.count >= COMPANION_GATT_QUEUE_DEPTH) {
        s_companion_gatt.overflow_count++;
        return false;
    }

    companion_gatt_event_t *event = &s_companion_gatt.queue[s_companion_gatt.head];
    event->type = type;
    event->char_id = char_id;
    event->attr_handle = attr_handle;
    event->payload_len = payload_len;
    if (payload_len != 0u) {
        memcpy(event->payload, payload, payload_len);
    }

    s_companion_gatt.head =
        (uint8_t)((s_companion_gatt.head + 1u) % COMPANION_GATT_QUEUE_DEPTH);
    s_companion_gatt.count++;
    companion_gatt_stm32wb_schedule_task();
    return true;
}

static tBleStatus companion_gatt_add_char(uint16_t service_handle,
                                          const companion_gatt_char_def_t *def)
{
    uint8_t uuid[16];
    companion_gatt_make_uuid(def->uuid_prefix, uuid);
    tBleStatus status = aci_gatt_add_char(service_handle,
                                          UUID_TYPE_128,
                                          (Char_UUID_t *)uuid,
                                          def->value_len,
                                          def->properties,
                                          ATTR_PERMISSION_NONE,
                                          def->event_mask,
                                          COMPANION_GATT_ENCRY_KEY_SIZE,
                                          def->variable,
                                          &s_companion_gatt.char_handles[def->id]);
    if (status == BLE_STATUS_SUCCESS) {
        s_companion_gatt.char_service_handles[def->id] = service_handle;
    }
    return status;
}

static tBleStatus companion_gatt_add_service(
    const companion_gatt_service_def_t *service)
{
    uint8_t uuid[16];
    uint16_t service_handle = 0u;
    companion_gatt_make_uuid(service->uuid_prefix, uuid);
    tBleStatus status = aci_gatt_add_service(UUID_TYPE_128,
                                             (Service_UUID_t *)uuid,
                                             PRIMARY_SERVICE,
                                             service->attr_records,
                                             &service_handle);
    if (status != BLE_STATUS_SUCCESS) {
        return status;
    }
    for (uint8_t i = 0u; i < service->char_count; ++i) {
        status = companion_gatt_add_char(service_handle, &service->chars[i]);
        if (status != BLE_STATUS_SUCCESS) {
            return status;
        }
    }

    return BLE_STATUS_SUCCESS;
}

static SVCCTL_EvtAckStatus_t companion_gatt_stm32wb_event_handler(void *event)
{
    hci_event_pckt *event_pckt;
    evt_blecore_aci *blecore_evt;
    aci_gatt_attribute_modified_event_rp0 *attribute_modified;
    uint8_t is_cccd = 0u;

    if (event == 0) {
        return SVCCTL_EvtNotAck;
    }

    event_pckt = (hci_event_pckt *)(((hci_uart_pckt *)event)->data);
    if (event_pckt->evt != HCI_VENDOR_SPECIFIC_DEBUG_EVT_CODE) {
        return SVCCTL_EvtNotAck;
    }

    blecore_evt = (evt_blecore_aci *)event_pckt->data;
    /* ST exposes the contract's EVT_BLUE_GATT_ATTRIBUTE_MODIFIED path here. */
    if (blecore_evt->ecode != ACI_GATT_ATTRIBUTE_MODIFIED_VSEVT_CODE) {
        return SVCCTL_EvtNotAck;
    }

    attribute_modified = (aci_gatt_attribute_modified_event_rp0 *)blecore_evt->data;
    const companion_gatt_char_def_t *def = companion_gatt_find_char_by_handle(
        attribute_modified->Attr_Handle,
        &is_cccd);
    if (def == 0) {
        return SVCCTL_EvtNotAck;
    }

    if (is_cccd != 0u) {
        uint8_t enabled = 0u;
        if (attribute_modified->Attr_Data_Length > 0u &&
            (attribute_modified->Attr_Data[0] & COMSVC_Notification) != 0u) {
            enabled = 1u;
        }
        (void)companion_gatt_enqueue(
            enabled != 0u ? COMPANION_GATT_EVENT_NOTIFY_ENABLED
                          : COMPANION_GATT_EVENT_NOTIFY_DISABLED,
            def->id,
            attribute_modified->Attr_Handle,
            attribute_modified->Attr_Data,
            attribute_modified->Attr_Data_Length);
        return SVCCTL_EvtAckFlowEnable;
    }

    if ((def->properties & (CHAR_PROP_WRITE | CHAR_PROP_WRITE_WITHOUT_RESP)) == 0u) {
        return SVCCTL_EvtNotAck;
    }

    (void)companion_gatt_enqueue(COMPANION_GATT_EVENT_WRITE,
                                 def->id,
                                 attribute_modified->Attr_Handle,
                                 attribute_modified->Attr_Data,
                                 attribute_modified->Attr_Data_Length);
    return SVCCTL_EvtAckFlowEnable;
}

static companion_gatt_parse_result_t companion_gatt_copy_fixed(
    const uint8_t *payload,
    uint16_t length,
    void *out,
    size_t expected_len)
{
    if (payload == 0 || out == 0) {
        return COMPANION_GATT_PARSE_BAD_ARGUMENT;
    }
    if (length < expected_len) {
        return COMPANION_GATT_PARSE_TOO_SHORT;
    }
    if (length > COMPANION_GATT_MAX_PAYLOAD_BYTES) {
        return COMPANION_GATT_PARSE_TOO_LONG;
    }
    if (payload[0] != COMPANION_GATT_SCHEMA_VERSION) {
        return COMPANION_GATT_PARSE_UNSUPPORTED_VERSION;
    }

    memcpy(out, payload, expected_len);
    return COMPANION_GATT_PARSE_OK;
}

tBleStatus companion_gatt_stm32wb_init(void)
{
    memset(&s_companion_gatt, 0, sizeof(s_companion_gatt));
    SVCCTL_RegisterSvcHandler(companion_gatt_stm32wb_event_handler);

    for (size_t i = 0u; i < sizeof(COMPANION_GATT_SERVICES) / sizeof(COMPANION_GATT_SERVICES[0]); ++i) {
        tBleStatus status = companion_gatt_add_service(&COMPANION_GATT_SERVICES[i]);
        if (status != BLE_STATUS_SUCCESS) {
            return status;
        }
    }

    return BLE_STATUS_SUCCESS;
}

size_t companion_gatt_stm32wb_drain(companion_gatt_event_fn_t handler,
                                    void *context)
{
    size_t drained = 0u;
    while (s_companion_gatt.count > 0u) {
        companion_gatt_event_t event = s_companion_gatt.queue[s_companion_gatt.tail];
        s_companion_gatt.tail =
            (uint8_t)((s_companion_gatt.tail + 1u) % COMPANION_GATT_QUEUE_DEPTH);
        s_companion_gatt.count--;
        drained++;
        if (handler != 0) {
            handler(&event, context);
        }
    }
    return drained;
}

bool companion_gatt_stm32wb_has_pending(void)
{
    return s_companion_gatt.count > 0u;
}

tBleStatus companion_gatt_stm32wb_publish(companion_gatt_char_id_t char_id,
                                          const uint8_t *payload,
                                          uint16_t length)
{
    if ((uint8_t)char_id >= (uint8_t)COMPANION_GATT_CHAR_COUNT ||
        length > COMPANION_GATT_MAX_PAYLOAD_BYTES ||
        (length != 0u && payload == 0)) {
        return BLE_STATUS_INVALID_PARAMS;
    }

    uint16_t char_handle = s_companion_gatt.char_handles[char_id];
    uint16_t service_handle = s_companion_gatt.char_service_handles[char_id];
    if (service_handle == 0u || char_handle == 0u) {
        return BLE_STATUS_INVALID_PARAMS;
    }

    return aci_gatt_update_char_value(service_handle,
                                      char_handle,
                                      0u,
                                      (uint8_t)length,
                                      payload);
}

companion_gatt_parse_result_t companion_gatt_parse_device_status_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_device_status_v1_t *out)
{
    return companion_gatt_copy_fixed(payload, length, out, sizeof(*out));
}

companion_gatt_parse_result_t companion_gatt_parse_battery_charge_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_battery_charge_v1_t *out)
{
    return companion_gatt_copy_fixed(payload, length, out, sizeof(*out));
}

companion_gatt_parse_result_t companion_gatt_parse_card_write_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_card_write_v1_t *out)
{
    companion_gatt_parse_result_t result =
        companion_gatt_copy_fixed(payload, length, out, sizeof(*out));
    if (result != COMPANION_GATT_PARSE_OK) {
        return result;
    }
    if ((uint32_t)out->utf8_title_len + (uint32_t)out->utf8_body_len >
        (uint32_t)(length - sizeof(*out))) {
        return COMPANION_GATT_PARSE_BAD_LENGTH;
    }
    return COMPANION_GATT_PARSE_OK;
}

companion_gatt_parse_result_t companion_gatt_parse_card_status_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_card_status_v1_t *out)
{
    return companion_gatt_copy_fixed(payload, length, out, sizeof(*out));
}

companion_gatt_parse_result_t companion_gatt_parse_recording_control_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_recording_control_v1_t *out)
{
    return companion_gatt_copy_fixed(payload, length, out, sizeof(*out));
}

companion_gatt_parse_result_t companion_gatt_parse_recording_list_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_recording_list_v1_t *out)
{
    companion_gatt_parse_result_t result =
        companion_gatt_copy_fixed(payload, length, out, sizeof(*out));
    if (result != COMPANION_GATT_PARSE_OK) {
        return result;
    }
    if ((uint32_t)out->count * (uint32_t)out->entry_bytes >
        (uint32_t)(length - sizeof(*out))) {
        return COMPANION_GATT_PARSE_BAD_LENGTH;
    }
    return COMPANION_GATT_PARSE_OK;
}

companion_gatt_parse_result_t companion_gatt_parse_recording_chunk_pull_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_recording_chunk_pull_v1_t *out)
{
    return companion_gatt_copy_fixed(payload, length, out, sizeof(*out));
}

companion_gatt_parse_result_t companion_gatt_parse_settings_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_settings_v1_t *out)
{
    return companion_gatt_copy_fixed(payload, length, out, sizeof(*out));
}

companion_gatt_parse_result_t companion_gatt_parse_ble_name_config_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_ble_name_config_v1_t *out)
{
    companion_gatt_parse_result_t result =
        companion_gatt_copy_fixed(payload, length, out, sizeof(*out));
    if (result != COMPANION_GATT_PARSE_OK) {
        return result;
    }
    if (out->name_len > COMPANION_GATT_BLE_NAME_MAX_BYTES) {
        return COMPANION_GATT_PARSE_BAD_LENGTH;
    }
    return COMPANION_GATT_PARSE_OK;
}

companion_gatt_parse_result_t companion_gatt_parse_meeting_control_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_meeting_control_v1_t *out)
{
    return companion_gatt_copy_fixed(payload, length, out, sizeof(*out));
}

companion_gatt_parse_result_t companion_gatt_parse_meeting_status_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_meeting_status_v1_t *out)
{
    return companion_gatt_copy_fixed(payload, length, out, sizeof(*out));
}

companion_gatt_parse_result_t companion_gatt_parse_imu_status_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_imu_status_v1_t *out)
{
    return companion_gatt_copy_fixed(payload, length, out, sizeof(*out));
}

companion_gatt_parse_result_t companion_gatt_parse_speaker_control_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_speaker_control_v1_t *out)
{
    return companion_gatt_copy_fixed(payload, length, out, sizeof(*out));
}

companion_gatt_parse_result_t companion_gatt_parse_speaker_status_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_speaker_status_v1_t *out)
{
    return companion_gatt_copy_fixed(payload, length, out, sizeof(*out));
}

companion_gatt_parse_result_t companion_gatt_parse_wake_word_control_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_wake_word_control_v1_t *out)
{
    return companion_gatt_copy_fixed(payload, length, out, sizeof(*out));
}

companion_gatt_parse_result_t companion_gatt_parse_wake_word_status_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_wake_word_status_v1_t *out)
{
    return companion_gatt_copy_fixed(payload, length, out, sizeof(*out));
}

companion_gatt_parse_result_t companion_gatt_parse_diag_log_pull_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_diag_log_pull_v1_t *out)
{
    return companion_gatt_copy_fixed(payload, length, out, sizeof(*out));
}

companion_gatt_parse_result_t companion_gatt_parse_delete_privacy_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_delete_privacy_v1_t *out)
{
    return companion_gatt_copy_fixed(payload, length, out, sizeof(*out));
}

companion_gatt_parse_result_t companion_gatt_parse_ota_readiness_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_ota_readiness_v1_t *out)
{
    return companion_gatt_copy_fixed(payload, length, out, sizeof(*out));
}

const char *companion_gatt_char_name(companion_gatt_char_id_t char_id)
{
    switch (char_id) {
    case COMPANION_GATT_CHAR_DEVICE_STATUS:
        return "device_status";
    case COMPANION_GATT_CHAR_BATTERY_CHARGE:
        return "battery_charge";
    case COMPANION_GATT_CHAR_E_PAPER_CARD_WRITE:
        return "e_paper_card_write";
    case COMPANION_GATT_CHAR_E_PAPER_CARD_STATUS:
        return "e_paper_card_status";
    case COMPANION_GATT_CHAR_RECORDING_CONTROL:
        return "recording_control";
    case COMPANION_GATT_CHAR_RECORDING_LIST:
        return "recording_list";
    case COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL:
        return "recording_chunk_pull";
    case COMPANION_GATT_CHAR_SETTINGS:
        return "settings";
    case COMPANION_GATT_CHAR_BLE_NAME_CONFIG:
        return "ble_name_config";
    case COMPANION_GATT_CHAR_DIAGNOSTICS_LOG_PULL:
        return "diagnostics_log_pull";
    case COMPANION_GATT_CHAR_DELETE_PRIVACY:
        return "delete_privacy";
    case COMPANION_GATT_CHAR_OTA_READINESS:
        return "ota_readiness";
    case COMPANION_GATT_CHAR_MEETING_CONTROL:
        return "meeting_control";
    case COMPANION_GATT_CHAR_MEETING_STATUS:
        return "meeting_status";
    case COMPANION_GATT_CHAR_IMU_STATUS:
        return "imu_status";
    case COMPANION_GATT_CHAR_SPEAKER_CONTROL:
        return "speaker_control";
    case COMPANION_GATT_CHAR_SPEAKER_STATUS:
        return "speaker_status";
    case COMPANION_GATT_CHAR_WAKE_WORD_CONTROL:
        return "wake_word_control";
    case COMPANION_GATT_CHAR_WAKE_WORD_STATUS:
        return "wake_word_status";
    default:
        return "unknown";
    }
}

__WEAK void companion_gatt_stm32wb_schedule_task(void)
{
}
