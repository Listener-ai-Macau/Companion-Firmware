#include "audio_stream_stm32wb.h"

#include "common_blesvc.h"
#include "companion_gatt_stm32wb.h"

#include <string.h>

#ifndef __WEAK
#define __WEAK __attribute__((weak))
#endif

#define COMP_AUDIO_STREAM_STM32WB_ENCRY_KEY_SIZE 10u
#define COMP_AUDIO_STREAM_STM32WB_NOTIFY_CCCD_OFFSET 2u
#define COMP_AUDIO_STREAM_STM32WB_VALUE_HANDLE_OFFSET 1u
#define COMP_AUDIO_STREAM_STM32WB_SERVICE_ATTRIBUTE_RECORDS (1u + 3u + 2u + 2u + 2u)
#define COMP_AUDIO_STREAM_STM32WB_NOTIFY_RETRY_LIMIT 96u
#define COMP_AUDIO_STREAM_STM32WB_NOTIFY_RETRY_EVENT_PUMPS 6u

typedef struct {
    uint16_t service_handle;
    uint16_t notify_char_handle;
    uint16_t control_char_handle;
    uint16_t readiness_char_handle;
    uint16_t capabilities_char_handle;
    comp_audio_stream_t *stream;
} comp_audio_stream_stm32wb_context_t;

/* STM32_WPAN stores 128-bit UUID bytes least-significant byte first. */
static const uint8_t COMP_AUDIO_STREAM_STM32WB_SERVICE_UUID[16] = {
    0x1a, 0x09, 0xc3, 0x3b, 0x5b, 0x9e, 0x4d, 0x0c,
    0x83, 0x65, 0x9f, 0x6d, 0x45, 0xf8, 0x0a, 0x71,
};

static const uint8_t COMP_AUDIO_STREAM_STM32WB_NOTIFY_UUID[16] = {
    0x1b, 0x09, 0xc3, 0x3b, 0x5b, 0x9e, 0x4d, 0x0c,
    0x83, 0x65, 0x9f, 0x6d, 0x45, 0xf8, 0x0a, 0x71,
};

static const uint8_t COMP_AUDIO_STREAM_STM32WB_READINESS_UUID[16] = {
    0x1c, 0x09, 0xc3, 0x3b, 0x5b, 0x9e, 0x4d, 0x0c,
    0x83, 0x65, 0x9f, 0x6d, 0x45, 0xf8, 0x0a, 0x71,
};

static const uint8_t COMP_AUDIO_STREAM_STM32WB_CAPABILITIES_UUID[16] = {
    0x1d, 0x09, 0xc3, 0x3b, 0x5b, 0x9e, 0x4d, 0x0c,
    0x83, 0x65, 0x9f, 0x6d, 0x45, 0xf8, 0x0a, 0x71,
};

static const uint8_t COMP_AUDIO_STREAM_STM32WB_CONTROL_UUID[16] = {
    0x1e, 0x09, 0xc3, 0x3b, 0x5b, 0x9e, 0x4d, 0x0c,
    0x83, 0x65, 0x9f, 0x6d, 0x45, 0xf8, 0x0a, 0x71,
};

static const uint8_t COMP_AUDIO_STREAM_STM32WB_DEFAULT_READINESS[] =
    "ready:listener_vka1 sample_rate=16000 channels=1 width_bits=16";

static const uint8_t COMP_AUDIO_STREAM_STM32WB_DEFAULT_CAPABILITIES[] =
    "caps:vka1=1 pcm16=1 live_notify=1 gatt_value=248";

PLACE_IN_SECTION("BLE_DRIVER_CONTEXT")
static comp_audio_stream_stm32wb_context_t s_comp_audio_stream_stm32wb;
static volatile tBleStatus s_comp_audio_stream_stm32wb_last_notify_status =
    BLE_STATUS_SUCCESS;
static volatile uint32_t s_comp_audio_stream_stm32wb_tx_pool_available_seq;
static volatile uint32_t s_comp_audio_stream_stm32wb_notification_complete_seq;

static SVCCTL_EvtAckStatus_t comp_audio_stream_stm32wb_event_handler(void *event);

static uint8_t comp_audio_stream_stm32wb_is_notify_cccd_handle(uint16_t event_handle)
{
    return event_handle ==
           (uint16_t)(s_comp_audio_stream_stm32wb.notify_char_handle +
                      COMP_AUDIO_STREAM_STM32WB_NOTIFY_CCCD_OFFSET);
}

static uint8_t comp_audio_stream_stm32wb_is_value_handle(uint16_t event_handle,
                                                         uint16_t char_handle)
{
    return event_handle ==
           (uint16_t)(char_handle + COMP_AUDIO_STREAM_STM32WB_VALUE_HANDLE_OFFSET);
}

static uint8_t comp_audio_stream_stm32wb_is_notify_value_handle(uint16_t event_handle)
{
    return comp_audio_stream_stm32wb_is_value_handle(
               event_handle,
               s_comp_audio_stream_stm32wb.notify_char_handle) ||
           event_handle == s_comp_audio_stream_stm32wb.notify_char_handle;
}

static uint8_t comp_audio_stream_stm32wb_is_retryable_status(tBleStatus status)
{
    return status == BLE_STATUS_BUSY ||
           status == BLE_STATUS_INSUFFICIENT_RESOURCES;
}

static void comp_audio_stream_stm32wb_note_tx_pool_available(void)
{
    s_comp_audio_stream_stm32wb_tx_pool_available_seq++;
}

static void comp_audio_stream_stm32wb_note_notification_complete(uint16_t attr_handle)
{
    if (comp_audio_stream_stm32wb_is_notify_value_handle(attr_handle)) {
        s_comp_audio_stream_stm32wb_notification_complete_seq++;
    }
}

static void comp_audio_stream_stm32wb_wait_for_retry_window(
    tBleStatus status,
    uint32_t tx_pool_available_seq,
    uint32_t notification_complete_seq)
{
    for (uint8_t i = 0u; i < COMP_AUDIO_STREAM_STM32WB_NOTIFY_RETRY_EVENT_PUMPS; ++i) {
        comp_audio_stream_stm32wb_notify_pump();
        if (status == BLE_STATUS_INSUFFICIENT_RESOURCES &&
            s_comp_audio_stream_stm32wb_tx_pool_available_seq != tx_pool_available_seq) {
            break;
        }
        if (status == BLE_STATUS_BUSY &&
            s_comp_audio_stream_stm32wb_notification_complete_seq !=
                notification_complete_seq) {
            break;
        }
        if (s_comp_audio_stream_stm32wb.stream != 0 &&
            !comp_audio_stream_is_ready(s_comp_audio_stream_stm32wb.stream)) {
            break;
        }
    }
}

static void comp_audio_stream_stm32wb_emit_event(
    comp_audio_stream_stm32wb_event_t event,
    comp_audio_stream_status_t control_status,
    const uint8_t *payload,
    uint8_t length)
{
    comp_audio_stream_stm32wb_notification_t notification = {
        .event = event,
        .control_status = control_status,
        .payload = payload,
        .length = length,
    };
    comp_audio_stream_stm32wb_app_notification(&notification);
}

static tBleStatus comp_audio_stream_stm32wb_update_char(uint16_t char_handle,
                                                        const uint8_t *data,
                                                        uint8_t length)
{
    if (char_handle == 0u || (length != 0u && data == 0)) {
        return BLE_STATUS_INVALID_PARAMS;
    }
    return aci_gatt_update_char_value(s_comp_audio_stream_stm32wb.service_handle,
                                      char_handle,
                                      0u,
                                      length,
                                      data);
}

static tBleStatus comp_audio_stream_stm32wb_add_char(const uint8_t *uuid,
                                                     uint16_t value_length,
                                                     uint8_t properties,
                                                     uint8_t event_mask,
                                                     uint8_t is_variable,
                                                     uint16_t *handle)
{
    return aci_gatt_add_char(s_comp_audio_stream_stm32wb.service_handle,
                             UUID_TYPE_128,
                             (Char_UUID_t *)uuid,
                             value_length,
                             properties,
                             ATTR_PERMISSION_NONE,
                             event_mask,
                             COMP_AUDIO_STREAM_STM32WB_ENCRY_KEY_SIZE,
                             is_variable,
                             handle);
}

static tBleStatus comp_audio_stream_stm32wb_publish_static_read_values(void)
{
    tBleStatus status = comp_audio_stream_stm32wb_update_readiness(
        COMP_AUDIO_STREAM_STM32WB_DEFAULT_READINESS,
        (uint8_t)(sizeof(COMP_AUDIO_STREAM_STM32WB_DEFAULT_READINESS) - 1u));
    if (status != BLE_STATUS_SUCCESS) {
        return status;
    }

    return comp_audio_stream_stm32wb_update_capabilities(
        COMP_AUDIO_STREAM_STM32WB_DEFAULT_CAPABILITIES,
        (uint8_t)(sizeof(COMP_AUDIO_STREAM_STM32WB_DEFAULT_CAPABILITIES) - 1u));
}

static SVCCTL_EvtAckStatus_t comp_audio_stream_stm32wb_event_handler(void *event)
{
    SVCCTL_EvtAckStatus_t return_value = SVCCTL_EvtNotAck;
    hci_event_pckt *event_pckt;
    evt_blecore_aci *blecore_evt;
    aci_gatt_attribute_modified_event_rp0 *attribute_modified;

    if (event == 0) {
        return return_value;
    }

    event_pckt = (hci_event_pckt *)(((hci_uart_pckt *)event)->data);
    if (event_pckt->evt != HCI_VENDOR_SPECIFIC_DEBUG_EVT_CODE) {
        return return_value;
    }

    blecore_evt = (evt_blecore_aci *)event_pckt->data;
    if (blecore_evt->ecode == ACI_GATT_TX_POOL_AVAILABLE_VSEVT_CODE) {
        comp_audio_stream_stm32wb_note_tx_pool_available();
        return SVCCTL_EvtAckFlowEnable;
    }

    if (blecore_evt->ecode == ACI_GATT_NOTIFICATION_COMPLETE_VSEVT_CODE) {
        aci_gatt_notification_complete_event_rp0 *notification_complete =
            (aci_gatt_notification_complete_event_rp0 *)blecore_evt->data;
        comp_audio_stream_stm32wb_note_notification_complete(
            notification_complete->Attr_Handle);
        return SVCCTL_EvtAckFlowEnable;
    }

    if (blecore_evt->ecode != ACI_GATT_ATTRIBUTE_MODIFIED_VSEVT_CODE) {
        return return_value;
    }

    attribute_modified = (aci_gatt_attribute_modified_event_rp0 *)blecore_evt->data;
    if (comp_audio_stream_stm32wb_is_notify_cccd_handle(attribute_modified->Attr_Handle)) {
        uint8_t enabled = 0u;
        if (attribute_modified->Attr_Data_Length > 0u &&
            (attribute_modified->Attr_Data[0] & COMSVC_Notification) != 0u) {
            enabled = 1u;
        }

        if (s_comp_audio_stream_stm32wb.stream != 0) {
            comp_audio_stream_set_notify_enabled(s_comp_audio_stream_stm32wb.stream,
                                                 enabled != 0u);
        }
        comp_audio_stream_stm32wb_emit_event(
            enabled != 0u ? COMP_AUDIO_STREAM_STM32WB_NOTIFY_ENABLED
                          : COMP_AUDIO_STREAM_STM32WB_NOTIFY_DISABLED,
            COMP_AUDIO_STREAM_OK,
            attribute_modified->Attr_Data,
            attribute_modified->Attr_Data_Length);
        return SVCCTL_EvtAckFlowEnable;
    }

    if (comp_audio_stream_stm32wb_is_value_handle(attribute_modified->Attr_Handle,
                                                  s_comp_audio_stream_stm32wb.control_char_handle)) {
        comp_audio_stream_status_t status = COMP_AUDIO_STREAM_NOT_READY;
        if (s_comp_audio_stream_stm32wb.stream != 0) {
            status = comp_audio_stream_handle_control_write(
                s_comp_audio_stream_stm32wb.stream,
                attribute_modified->Attr_Data,
                attribute_modified->Attr_Data_Length);
        }
        comp_audio_stream_stm32wb_emit_event(COMP_AUDIO_STREAM_STM32WB_CONTROL_WRITE,
                                             status,
                                             attribute_modified->Attr_Data,
                                             attribute_modified->Attr_Data_Length);
        return_value = SVCCTL_EvtAckFlowEnable;
    }

    return return_value;
}

comp_audio_stream_config_t comp_audio_stream_stm32wb_default_config(
    comp_audio_stream_control_fn_t control,
    void *context)
{
    comp_audio_stream_config_t config = {
        .notify = comp_audio_stream_stm32wb_notify,
        .control = control,
        .context = context,
        .gatt_value_max_bytes = COMP_AUDIO_STREAM_STM32WB_GATT_VALUE_BYTES,
    };
    return config;
}

tBleStatus comp_audio_stream_stm32wb_init(comp_audio_stream_t *stream)
{
    if (stream == 0) {
        return BLE_STATUS_INVALID_PARAMS;
    }

    memset(&s_comp_audio_stream_stm32wb, 0, sizeof(s_comp_audio_stream_stm32wb));
    s_comp_audio_stream_stm32wb.stream = stream;
    s_comp_audio_stream_stm32wb_tx_pool_available_seq = 0u;
    s_comp_audio_stream_stm32wb_notification_complete_seq = 0u;

    SVCCTL_RegisterSvcHandler(comp_audio_stream_stm32wb_event_handler);

    tBleStatus status = aci_gatt_add_service(
        UUID_TYPE_128,
        (Service_UUID_t *)COMP_AUDIO_STREAM_STM32WB_SERVICE_UUID,
        PRIMARY_SERVICE,
        COMP_AUDIO_STREAM_STM32WB_SERVICE_ATTRIBUTE_RECORDS,
        &s_comp_audio_stream_stm32wb.service_handle);
    if (status != BLE_STATUS_SUCCESS) {
        return status;
    }

    status = comp_audio_stream_stm32wb_add_char(
        COMP_AUDIO_STREAM_STM32WB_NOTIFY_UUID,
        COMP_AUDIO_STREAM_STM32WB_GATT_VALUE_BYTES,
        CHAR_PROP_NOTIFY,
        GATT_NOTIFY_ATTRIBUTE_WRITE | GATT_NOTIFY_NOTIFICATION_COMPLETION,
        1u,
        &s_comp_audio_stream_stm32wb.notify_char_handle);
    if (status != BLE_STATUS_SUCCESS) {
        return status;
    }

    status = comp_audio_stream_stm32wb_add_char(
        COMP_AUDIO_STREAM_STM32WB_CONTROL_UUID,
        COMP_AUDIO_STREAM_STM32WB_CONTROL_VALUE_BYTES,
        CHAR_PROP_WRITE | CHAR_PROP_WRITE_WITHOUT_RESP,
        GATT_NOTIFY_ATTRIBUTE_WRITE,
        1u,
        &s_comp_audio_stream_stm32wb.control_char_handle);
    if (status != BLE_STATUS_SUCCESS) {
        return status;
    }

    status = comp_audio_stream_stm32wb_add_char(
        COMP_AUDIO_STREAM_STM32WB_READINESS_UUID,
        COMP_AUDIO_STREAM_STM32WB_READINESS_VALUE_BYTES,
        CHAR_PROP_READ,
        GATT_DONT_NOTIFY_EVENTS,
        1u,
        &s_comp_audio_stream_stm32wb.readiness_char_handle);
    if (status != BLE_STATUS_SUCCESS) {
        return status;
    }

    status = comp_audio_stream_stm32wb_add_char(
        COMP_AUDIO_STREAM_STM32WB_CAPABILITIES_UUID,
        COMP_AUDIO_STREAM_STM32WB_CAPABILITIES_VALUE_BYTES,
        CHAR_PROP_READ,
        GATT_DONT_NOTIFY_EVENTS,
        1u,
        &s_comp_audio_stream_stm32wb.capabilities_char_handle);
    if (status != BLE_STATUS_SUCCESS) {
        return status;
    }

    return comp_audio_stream_stm32wb_publish_static_read_values();
}

comp_audio_stream_status_t comp_audio_stream_stm32wb_notify(void *context,
                                                            const uint8_t *data,
                                                            uint16_t length)
{
    (void)context;

    if (data == 0 || length == 0u) {
        return COMP_AUDIO_STREAM_BAD_ARGUMENT;
    }
    if (s_comp_audio_stream_stm32wb.service_handle == 0u ||
        s_comp_audio_stream_stm32wb.notify_char_handle == 0u) {
        return COMP_AUDIO_STREAM_NOT_READY;
    }
    if (s_comp_audio_stream_stm32wb.stream != 0 &&
        !comp_audio_stream_is_ready(s_comp_audio_stream_stm32wb.stream)) {
        return COMP_AUDIO_STREAM_NOT_READY;
    }
    if (length > COMP_AUDIO_STREAM_STM32WB_GATT_VALUE_BYTES) {
        return COMP_AUDIO_STREAM_PACKET_TOO_LARGE;
    }

    tBleStatus status = BLE_STATUS_FAILED;
    for (uint8_t attempt = 0u;
         attempt <= COMP_AUDIO_STREAM_STM32WB_NOTIFY_RETRY_LIMIT;
         ++attempt) {
        uint32_t tx_pool_available_seq =
            s_comp_audio_stream_stm32wb_tx_pool_available_seq;
        uint32_t notification_complete_seq =
            s_comp_audio_stream_stm32wb_notification_complete_seq;
        status = aci_gatt_update_char_value(
            s_comp_audio_stream_stm32wb.service_handle,
            s_comp_audio_stream_stm32wb.notify_char_handle,
            0u,
            (uint8_t)length,
            data);
        s_comp_audio_stream_stm32wb_last_notify_status = status;
        if (status == BLE_STATUS_SUCCESS) {
            comp_audio_stream_stm32wb_notify_pump();
            return COMP_AUDIO_STREAM_OK;
        }
        if (!comp_audio_stream_stm32wb_is_retryable_status(status)) {
            break;
        }
        comp_audio_stream_stm32wb_wait_for_retry_window(status,
                                                        tx_pool_available_seq,
                                                        notification_complete_seq);
    }
    return COMP_AUDIO_STREAM_NOTIFY_FAILED;
}

tBleStatus comp_audio_stream_stm32wb_last_notify_status(void)
{
    return s_comp_audio_stream_stm32wb_last_notify_status;
}

tBleStatus comp_audio_stream_stm32wb_update_readiness(const uint8_t *data,
                                                      uint8_t length)
{
    if (length > COMP_AUDIO_STREAM_STM32WB_READINESS_VALUE_BYTES) {
        return BLE_STATUS_INVALID_PARAMS;
    }
    return comp_audio_stream_stm32wb_update_char(
        s_comp_audio_stream_stm32wb.readiness_char_handle,
        data,
        length);
}

tBleStatus comp_audio_stream_stm32wb_update_capabilities(const uint8_t *data,
                                                         uint8_t length)
{
    if (length > COMP_AUDIO_STREAM_STM32WB_CAPABILITIES_VALUE_BYTES) {
        return BLE_STATUS_INVALID_PARAMS;
    }
    return comp_audio_stream_stm32wb_update_char(
        s_comp_audio_stream_stm32wb.capabilities_char_handle,
        data,
        length);
}

__WEAK void comp_audio_stream_stm32wb_app_notification(
    const comp_audio_stream_stm32wb_notification_t *notification)
{
    (void)notification;
}

__WEAK void comp_audio_stream_stm32wb_notify_pump(void)
{
}

/* Optional product hook: refill GATT notify producers from TX-pool events. */
__WEAK void companion_ble_on_tx_pool_available(void)
{
}

void aci_gatt_tx_pool_available_event(uint16_t Connection_Handle,
                                      uint16_t Available_Buffers)
{
    (void)Connection_Handle;
    (void)Available_Buffers;
    comp_audio_stream_stm32wb_note_tx_pool_available();
    companion_ble_on_tx_pool_available();
    companion_gatt_stm32wb_schedule_task();
}

void aci_gatt_notification_complete_event(uint16_t Attr_Handle)
{
    comp_audio_stream_stm32wb_note_notification_complete(Attr_Handle);
    companion_ble_on_tx_pool_available();
    companion_gatt_stm32wb_schedule_task();
}
