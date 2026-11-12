#include "companion_gatt_stm32wb.h"

#if defined(COMPANION_GATT_WBA_HOST)
/* This module owns wire definitions/queueing only. WBA uses the same ACI
 * service API from its own host stack, with no WB HAL or CPU2 transport. */
#include "ble_core.h"
#include "diag_log.h"
#include "svc_ctl.h"
extern void comp_v11_ble_observe_aci_resource_origin(bool notify,const uint32_t *generation);
/* Payload overflow belongs to the existing ST event pool. The caller releases
 * each loan before dispatching product work or retiring a connection. */
extern uint8_t *comp_v11_ble_command_payload_claim(uint16_t bytes);
extern void comp_v11_ble_command_payload_release(uint8_t *bytes);
extern void comp_v11_ble_command_payload_resume(void);
#define COMSVC_Notification 1u
#else
#include "common_blesvc.h"
#endif

#include <stddef.h>
#include <string.h>
#include "companion_gatt_schema.h"

#define COMPANION_CHAR_DEFINITION(id, uuid, size, props, events, variable) \
    {id, uuid, size, props, events, variable},

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

/* Only the internal queue is compact. Public callbacks retain full enums,
 * payload limits and exactly the same queue depth. */
typedef struct {
    uint8_t type_and_offset,char_id,payload_len;
#if defined(COMPANION_GATT_WBA_HOST)
    uint8_t borrowed;
    union {uint8_t *loan;uint16_t offset;} storage;
#else
    uint8_t payload[COMPANION_GATT_MAX_PAYLOAD_BYTES];
#endif
} companion_gatt_queued_event_t;
_Static_assert(COMPANION_GATT_EVENT_NOTIFY_DISABLED<=UINT8_MAX &&
    COMPANION_GATT_CHAR_COUNT<=UINT8_MAX && COMPANION_GATT_MAX_PAYLOAD_BYTES<=UINT8_MAX,
    "queue identifiers and payload length must fit");
typedef struct {
    uint16_t char_service_handles[COMPANION_GATT_CHAR_COUNT];
    uint16_t char_handles[COMPANION_GATT_CHAR_COUNT];
    companion_gatt_queued_event_t queue[COMPANION_GATT_QUEUE_DEPTH];
#if defined(COMPANION_GATT_WBA_HOST)
    /* Common controls fit here without allocation. Rare long bursts keep the
     * same eight slots and payload limit by borrowing ST's existing pool. */
    uint8_t payload_arena[512u];
    uint16_t payload_head,payload_used;
    bool payload_waiting;
#endif
    uint8_t head;
    uint8_t tail;
    uint8_t count;
    uint8_t overflow_count;
} companion_gatt_context_t;
#if defined(COMPANION_GATT_WBA_HOST) && defined(__arm__)
_Static_assert(sizeof(companion_gatt_context_t)<=672u,"bounded pooled GATT queue");
#endif

#if defined(COMPANION_GATT_WBA_HOST)
#define COMPANION_DEVICE_STATUS_VALUE_BYTES sizeof(companion_gatt_device_status_v1_wba_recording_t)
#else
#define COMPANION_DEVICE_STATUS_VALUE_BYTES sizeof(companion_gatt_device_status_v1_wba_capacity_t)
#endif
static const companion_gatt_char_def_t COMPANION_GATT_DEVICE_STATUS_CHARS[] = {
    COMPANION_GATT_DEVICE_STATUS_CHARS_SCHEMA(COMPANION_CHAR_DEFINITION)
};

static const companion_gatt_char_def_t COMPANION_GATT_EPAPER_CHARS[] = {
    COMPANION_GATT_EPAPER_CHARS_SCHEMA(COMPANION_CHAR_DEFINITION)
};

static const companion_gatt_char_def_t COMPANION_GATT_RECORDING_CHARS[] = {
    COMPANION_GATT_RECORDING_CHARS_SCHEMA(COMPANION_CHAR_DEFINITION)
};

static const companion_gatt_char_def_t COMPANION_GATT_SETTINGS_CHARS[] = {
    COMPANION_GATT_SETTINGS_CHARS_SCHEMA(COMPANION_CHAR_DEFINITION)
};

static const companion_gatt_char_def_t COMPANION_GATT_DIAGNOSTICS_CHARS[] = {
    COMPANION_GATT_DIAGNOSTICS_CHARS_SCHEMA(COMPANION_CHAR_DEFINITION)
};

static const companion_gatt_char_def_t COMPANION_GATT_PRIVACY_CHARS[] = {
    COMPANION_GATT_PRIVACY_CHARS_SCHEMA(COMPANION_CHAR_DEFINITION)
};

static const companion_gatt_char_def_t COMPANION_GATT_OTA_CHARS[] = {
    COMPANION_GATT_OTA_CHARS_SCHEMA(COMPANION_CHAR_DEFINITION)
};

static const companion_gatt_char_def_t COMPANION_GATT_MEETING_CHARS[] = {
    COMPANION_GATT_MEETING_CHARS_SCHEMA(COMPANION_CHAR_DEFINITION)
};

static const companion_gatt_char_def_t COMPANION_GATT_SENSOR_CHARS[] = {
    COMPANION_GATT_SENSOR_CHARS_SCHEMA(COMPANION_CHAR_DEFINITION)
};

static const companion_gatt_char_def_t COMPANION_GATT_AUDIO_OUTPUT_CHARS[] = {
    COMPANION_GATT_AUDIO_OUTPUT_CHARS_SCHEMA(COMPANION_CHAR_DEFINITION)
};

#undef COMPANION_CHAR_DEFINITION

#define COMPANION_SERVICE_DEFINITION(uuid, records, count, chars) \
    {uuid, records, count, chars},
static const companion_gatt_service_def_t COMPANION_GATT_SERVICES[] = {
    COMPANION_GATT_SERVICE_SCHEMA(COMPANION_SERVICE_DEFINITION)
};
#undef COMPANION_SERVICE_DEFINITION

#if !defined(COMPANION_GATT_WBA_HOST)
PLACE_IN_SECTION("BLE_DRIVER_CONTEXT")
#endif
static companion_gatt_context_t s_companion_gatt
#if COMPANION_WBA_CE_SHARED_CAPTURE && defined(__GNUC__)
    __attribute__((section(".sram1.bss"),aligned(8)))
#endif
    ;

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

typedef enum {GATT_QUEUE_REJECTED,GATT_QUEUE_ACCEPTED,GATT_QUEUE_RETRY} gatt_queue_result_t;
static gatt_queue_result_t companion_gatt_enqueue(companion_gatt_event_type_t type,
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

    /* Attribute is always the registered declaration, value or CCCD.
     * Preserve the exact handle with a two-bit relative offset. */
    if((unsigned)char_id>=COMPANION_GATT_CHAR_COUNT ||
       (unsigned)type>COMPANION_GATT_EVENT_NOTIFY_DISABLED)return false;
    uint16_t base=s_companion_gatt.char_handles[char_id];
    if(!base || attr_handle<base || (uint16_t)(attr_handle-base)>2u)return false;
    companion_gatt_queued_event_t *event = &s_companion_gatt.queue[s_companion_gatt.head];
#if defined(COMPANION_GATT_WBA_HOST)
    event->borrowed=payload_len>sizeof(s_companion_gatt.payload_arena)-s_companion_gatt.payload_used;
    if(event->borrowed) {
        event->storage.loan=comp_v11_ble_command_payload_claim(payload_len);
        if(!event->storage.loan) {
            /* SVCCTL keeps this exact source event at the HCI head. The
             * existing queued commands are runnable and drain in foreground;
             * their retirement resumes the source, without a lost command. */
            s_companion_gatt.payload_waiting=true;
            return GATT_QUEUE_RETRY;
        }
        memcpy(event->storage.loan,payload,payload_len);
    } else {
        unsigned first=sizeof(s_companion_gatt.payload_arena)-s_companion_gatt.payload_head;
        if(first>payload_len)first=payload_len;
        event->storage.offset=s_companion_gatt.payload_head;
        if(first)memcpy(s_companion_gatt.payload_arena+s_companion_gatt.payload_head,payload,first);
        if(payload_len>first)memcpy(s_companion_gatt.payload_arena,payload+first,payload_len-first);
        s_companion_gatt.payload_head=(uint16_t)((s_companion_gatt.payload_head+payload_len)%sizeof(s_companion_gatt.payload_arena));
        s_companion_gatt.payload_used=(uint16_t)(s_companion_gatt.payload_used+payload_len);
    }
#endif
    event->type_and_offset=(uint8_t)((uint8_t)type | ((uint8_t)(attr_handle-base)<<2u));
    event->char_id=(uint8_t)char_id;
    event->payload_len=(uint8_t)payload_len;
    #if !defined(COMPANION_GATT_WBA_HOST)
    if (payload_len != 0u) {
        memcpy(event->payload, payload, payload_len);
    }
    #endif

    s_companion_gatt.head =
        (uint8_t)((s_companion_gatt.head + 1u) % COMPANION_GATT_QUEUE_DEPTH);
    s_companion_gatt.count++;
    companion_gatt_stm32wb_schedule_task();
    return GATT_QUEUE_ACCEPTED;
}

static tBleStatus companion_gatt_add_char(uint16_t service_handle,
                                          const companion_gatt_char_def_t *def)
{
    uint8_t uuid[16];
    uint8_t permissions=ATTR_PERMISSION_NONE;
    uint8_t events=def->event_mask;
#if defined(COMPANION_GATT_WBA_HOST)
    if(def->id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL ||
       def->id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B)
        events|=GATT_NOTIFY_NOTIFICATION_COMPLETION;
    /* The host must establish encryption before recording data or commands.
     * Status/battery discovery remains readable for connection diagnosis. */
    if(def->id!=COMPANION_GATT_CHAR_DEVICE_STATUS && def->id!=COMPANION_GATT_CHAR_BATTERY_CHARGE &&
       def->id!=COMPANION_GATT_CHAR_OTA_READINESS) {
        if(def->properties&CHAR_PROP_READ)permissions|=ATTR_PERMISSION_ENCRY_READ;
        if(def->properties&(CHAR_PROP_WRITE|CHAR_PROP_WRITE_WITHOUT_RESP))permissions|=ATTR_PERMISSION_ENCRY_WRITE;
    }
#endif
    companion_gatt_make_uuid(def->uuid_prefix, uuid);
    tBleStatus status = aci_gatt_add_char(service_handle,
                                          UUID_TYPE_128,
                                          (Char_UUID_t *)uuid,
                                          def->value_len,
                                          def->properties,
                                          permissions,
                                          events,
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

#if defined(COMPANION_GATT_WBA_HOST)
    if (event_pckt->plen < sizeof(uint16_t)) {
        return SVCCTL_EvtNotAck;
    }
#endif
    blecore_evt = (evt_blecore_aci *)event_pckt->data;
    /* ST exposes the contract's EVT_BLUE_GATT_ATTRIBUTE_MODIFIED path here. */
    if (blecore_evt->ecode != ACI_GATT_ATTRIBUTE_MODIFIED_VSEVT_CODE) {
        return SVCCTL_EvtNotAck;
    }

#if defined(COMPANION_GATT_WBA_HOST)
    if (event_pckt->plen < sizeof(uint16_t) +
            offsetof(aci_gatt_attribute_modified_event_rp0, Attr_Data)) {
        return SVCCTL_EvtNotAck;
    }
#endif
    attribute_modified = (aci_gatt_attribute_modified_event_rp0 *)blecore_evt->data;
#if defined(COMPANION_GATT_WBA_HOST)
    if (attribute_modified->Attr_Data_Length >
            (uint16_t)(event_pckt->plen - sizeof(uint16_t) -
                offsetof(aci_gatt_attribute_modified_event_rp0, Attr_Data))) {
        return SVCCTL_EvtNotAck;
    }
#endif
    const companion_gatt_char_def_t *def = companion_gatt_find_char_by_handle(
        attribute_modified->Attr_Handle,
        &is_cccd);
    if (def == 0) {
        return SVCCTL_EvtNotAck;
    }

#if defined(COMPANION_GATT_WBA_HOST)
    /* WBA reports long values as multiple modified events and marks more-data
     * in Offset bit 15. The portable queue has no fragment accumulator, so it
     * must reject every nonzero offset instead of presenting a fragment as a
     * complete product command. Current recording/privacy controls fit one
     * event; the larger card path remains unavailable until it gets an owner. */
    if (attribute_modified->Offset != 0u ||
        attribute_modified->Attr_Data_Length > def->value_len ||
        (is_cccd != 0u && attribute_modified->Attr_Data_Length != 2u)) {
        return SVCCTL_EvtAckFlowEnable;
    }
#endif
    if (is_cccd != 0u) {
        uint8_t enabled = 0u;
        if (attribute_modified->Attr_Data_Length > 0u &&
            (attribute_modified->Attr_Data[0] & COMSVC_Notification) != 0u) {
            enabled = 1u;
        }
        gatt_queue_result_t result=companion_gatt_enqueue(
            enabled != 0u ? COMPANION_GATT_EVENT_NOTIFY_ENABLED
                          : COMPANION_GATT_EVENT_NOTIFY_DISABLED,
            def->id,
            attribute_modified->Attr_Handle,
            attribute_modified->Attr_Data,
            attribute_modified->Attr_Data_Length);
        return result==GATT_QUEUE_RETRY?SVCCTL_EvtAckFlowDisable:SVCCTL_EvtAckFlowEnable;
    }

    if ((def->properties & (CHAR_PROP_WRITE | CHAR_PROP_WRITE_WITHOUT_RESP)) == 0u) {
        return SVCCTL_EvtNotAck;
    }

    gatt_queue_result_t queue_result=companion_gatt_enqueue(COMPANION_GATT_EVENT_WRITE,
                                 def->id,
                                 attribute_modified->Attr_Handle,
                                 attribute_modified->Attr_Data,
                                 attribute_modified->Attr_Data_Length);
    bool queued=queue_result==GATT_QUEUE_ACCEPTED;
#if defined(COMPANION_GATT_WBA_HOST)
    /* A successful ATT write only means the stack received the bytes. The
     * cooperative event queue may still be retired on disconnect. Log one
     * identity-only event per consume request, never audio or proof bytes. */
    if(def->id==COMPANION_GATT_CHAR_DELETE_PRIVACY &&
       attribute_modified->Attr_Data_Length==84u &&
       !memcmp(attribute_modified->Attr_Data,"CRA2\x02\x00\x54\x00",8u)) {
        const uint8_t *p=attribute_modified->Attr_Data;
        uint32_t rid=(uint32_t)p[40]|((uint32_t)p[41]<<8u)|((uint32_t)p[42]<<16u)|((uint32_t)p[43]<<24u);
        comp_diag_log_record_code(COMP_DIAG_EVT_GATT_SEGMENT_CONSUME_QUEUED,
            queued?COMP_DIAG_SEV_INFO:COMP_DIAG_SEV_WARN,rid,(uint32_t)queued,
            s_companion_gatt.count,s_companion_gatt.overflow_count);
    }
    if(def->id==COMPANION_GATT_CHAR_DELETE_PRIVACY &&
       attribute_modified->Attr_Data_Length==sizeof(companion_gatt_delete_privacy_v1_t) &&
       attribute_modified->Attr_Data[0]==1u && attribute_modified->Attr_Data[1]==1u) {
        companion_gatt_delete_privacy_v1_t request;
        memcpy(&request,attribute_modified->Attr_Data,sizeof(request));
        comp_diag_log_record_code(COMP_DIAG_EVT_GATT_RECLAIM_QUEUED,
            queued?COMP_DIAG_SEV_INFO:COMP_DIAG_SEV_WARN,
            request.request_id,request.recording_id,
            (uint32_t)queued|((uint32_t)s_companion_gatt.count<<8u),
            s_companion_gatt.overflow_count);
    }
#else
    (void)queued;
#endif
    return queue_result==GATT_QUEUE_RETRY?SVCCTL_EvtAckFlowDisable:SVCCTL_EvtAckFlowEnable;
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
#if defined(COMPANION_GATT_WBA_HOST)
    (void)companion_gatt_stm32wb_drain(0,0);
#endif
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
        const companion_gatt_queued_event_t *queued=&s_companion_gatt.queue[s_companion_gatt.tail];
        companion_gatt_event_t event={0};
        event.type=(companion_gatt_event_type_t)(queued->type_and_offset&3u);
        event.char_id=(companion_gatt_char_id_t)queued->char_id;
        event.attr_handle=(uint16_t)(s_companion_gatt.char_handles[queued->char_id]+(queued->type_and_offset>>2u));
        event.payload_len=queued->payload_len;
#if defined(COMPANION_GATT_WBA_HOST)
        if(queued->borrowed) {
            memcpy(event.payload,queued->storage.loan,event.payload_len);
            comp_v11_ble_command_payload_release(queued->storage.loan);
        } else {
            unsigned first=sizeof(s_companion_gatt.payload_arena)-queued->storage.offset;
            if(first>event.payload_len)first=event.payload_len;
            if(first)memcpy(event.payload,s_companion_gatt.payload_arena+queued->storage.offset,first);
            if(event.payload_len>first)memcpy(event.payload+first,s_companion_gatt.payload_arena,event.payload_len-first);
            s_companion_gatt.payload_used=(uint16_t)(s_companion_gatt.payload_used-event.payload_len);
        }
#else
        if(event.payload_len)memcpy(event.payload,queued->payload,event.payload_len);
#endif
        s_companion_gatt.tail =
            (uint8_t)((s_companion_gatt.tail + 1u) % COMPANION_GATT_QUEUE_DEPTH);
        s_companion_gatt.count--;
        drained++;
        if (handler != 0) {
            handler(&event, context);
        }
    }
#if defined(COMPANION_GATT_WBA_HOST)
    if(s_companion_gatt.payload_waiting) {
        s_companion_gatt.payload_waiting=false;
        comp_v11_ble_command_payload_resume();
    }
#endif
    return drained;
}

bool companion_gatt_stm32wb_has_pending(void)
{
    return s_companion_gatt.count > 0u;
}

uint8_t companion_gatt_stm32wb_recording_value_lane(uint16_t attr_handle)
{
    const companion_gatt_char_id_t lanes[]={COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,
        COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B};
    for(unsigned i=0u;i<2u;++i) {
        uint16_t handle=s_companion_gatt.char_handles[lanes[i]];
        if(handle && attr_handle==(uint16_t)(handle+COMPANION_GATT_VALUE_HANDLE_OFFSET))return (uint8_t)(i+1u);
    }
    return 0u;
}
bool companion_gatt_stm32wb_is_recording_value_handle(uint16_t attr_handle)
{return companion_gatt_stm32wb_recording_value_lane(attr_handle)!=0u;}

tBleStatus companion_gatt_stm32wb_set_read_value(companion_gatt_char_id_t char_id,
                                               const uint8_t *payload,
                                               uint16_t length)
{
    if(char_id!=COMPANION_GATT_CHAR_SETTINGS || !payload ||
       length>COMPANION_GATT_MAX_PAYLOAD_BYTES)return BLE_STATUS_INVALID_PARAMS;
#if defined(COMPANION_GATT_WBA_HOST)
    uint16_t ch=s_companion_gatt.char_handles[char_id];
    uint16_t svc=s_companion_gatt.char_service_handles[char_id];
    if(!ch || !svc)return BLE_STATUS_INVALID_PARAMS;
    return aci_gatt_update_char_value_ext(0x0FFFu,svc,ch,0u,length,0u,(uint8_t)length,payload);
#else
    return BLE_STATUS_INVALID_PARAMS;
#endif
}

tBleStatus companion_gatt_stm32wb_publish(companion_gatt_char_id_t char_id,
                                          const uint8_t *payload,
                                          uint16_t length)
{
    uint16_t staged_bytes=0u;
    return companion_gatt_stm32wb_publish_progress(
        char_id,payload,length,&staged_bytes,NULL);
}

tBleStatus companion_gatt_stm32wb_publish_progress(
    companion_gatt_char_id_t char_id, const uint8_t *payload, uint16_t length,
    uint16_t *staged_bytes, const uint32_t *generation)
{
    (void)generation; /* WBA resumes long values; other hosts use short API. */
    const bool long_recording=char_id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL ||
        char_id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B;
    if ((uint8_t)char_id >= (uint8_t)COMPANION_GATT_CHAR_COUNT ||
        length > (long_recording?COMPANION_RECORDING_NOTIFY_VALUE_BYTES:COMPANION_GATT_MAX_PAYLOAD_BYTES) ||
        (length != 0u && payload == 0) || staged_bytes==NULL) {
        return BLE_STATUS_INVALID_PARAMS;
    }

    uint16_t char_handle = s_companion_gatt.char_handles[char_id];
    uint16_t service_handle = s_companion_gatt.char_service_handles[char_id];
    if (service_handle == 0u || char_handle == 0u) {
        return BLE_STATUS_INVALID_PARAMS;
    }

#if defined(COMPANION_GATT_WBA_HOST)
    if(length>248u) {
        /* The same attribute accepts <=32B START/resume requests at offset0.
         * Stage the tail first and commit the immutable prefix last, so an
         * intervening client write cannot become the notification header.
         * staged_bytes is a 240B part-index token, NOT a physical extent.
         * Keep the same ACI count and pool retry; notify only after all tail
         * parts succeeded. The owner retires the token on window/lane change. */
        if(*staged_bytes>=length || *staged_bytes%240u!=0u)
            return BLE_STATUS_INVALID_PARAMS;
        const uint32_t expected=generation?*generation:0u;
        const uint16_t parts=(uint16_t)((length+239u)/240u);
        for(uint16_t progress=*staged_bytes;progress<length;) {
            const uint16_t part=(uint16_t)(progress/240u);
            const bool commit=part+1u==parts;
            const uint16_t offset=commit?0u:(uint16_t)((part+1u)*240u);
            uint16_t remaining=(uint16_t)(length-offset);
            uint8_t n=(uint8_t)(remaining>240u?240u:remaining);
            tBleStatus status=aci_gatt_update_char_value_ext(0x0FFFu,service_handle,
                char_handle,commit?1u:0u,length,offset,n,payload+offset);
            /* ACI may dispatch a disconnect while awaiting its response.
             * Do not overwrite the newer owner's cleared progress. */
            if(generation && *generation!=expected)return BLE_STATUS_INVALID_PARAMS;
            if(status!=BLE_STATUS_SUCCESS) {
                if(long_recording && generation &&
                   (status==BLE_STATUS_INSUFFICIENT_RESOURCES || status==BLE_STATUS_BUSY))
                    comp_v11_ble_observe_aci_resource_origin(commit,generation);
                if(status!=BLE_STATUS_INSUFFICIENT_RESOURCES && status!=BLE_STATUS_BUSY)
                    *staged_bytes=0u;
                return status;
            }
            progress=commit?length:(uint16_t)(progress+240u);
            *staged_bytes=commit?0u:progress;
        }
        return BLE_STATUS_SUCCESS;
    }
#endif
    *staged_bytes=0u;
    const uint32_t expected_short=generation?*generation:0u;
    tBleStatus status=aci_gatt_update_char_value(service_handle,char_handle,0u,(uint8_t)length,payload);
#if defined(COMPANION_GATT_WBA_HOST)
    if(generation && *generation!=expected_short)return BLE_STATUS_INVALID_PARAMS;
    if(long_recording && generation &&
       (status==BLE_STATUS_INSUFFICIENT_RESOURCES || status==BLE_STATUS_BUSY))
        comp_v11_ble_observe_aci_resource_origin(true,generation);
#endif
    (void)expected_short;
    return status;
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

companion_gatt_parse_result_t companion_gatt_parse_repair_control_v1(
    const uint8_t *payload,
    uint16_t length,
    companion_gatt_repair_control_v1_t *out)
{
    companion_gatt_parse_result_t result =
        companion_gatt_copy_fixed(payload, length, out, sizeof(*out));
    if (result != COMPANION_GATT_PARSE_OK) {
        return result;
    }
    if (out->command != 1u || out->pairing_window_ms == 0u ||
        out->pairing_window_ms > 120000u) {
        return COMPANION_GATT_PARSE_BAD_ARGUMENT;
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
    case COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B:
        return "recording_chunk_pull_b";
    case COMPANION_GATT_CHAR_SETTINGS:
        return "settings";
    case COMPANION_GATT_CHAR_BLE_NAME_CONFIG:
        return "ble_name_config";
    case COMPANION_GATT_CHAR_REPAIR_CONTROL:
        return "repair_control";
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
