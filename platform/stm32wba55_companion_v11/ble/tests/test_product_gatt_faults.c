#include "companion_gatt_stm32wb.h"
#include "ble_core.h"
#include "diag_log.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

uint8_t *comp_v11_ble_command_payload_claim(uint16_t bytes){return malloc(bytes);}
void comp_v11_ble_command_payload_release(uint8_t *p){free(p);}
void comp_v11_ble_command_payload_resume(void){}
void comp_v11_ble_observe_aci_resource_origin(bool notify,const uint32_t *generation)
{(void)notify;(void)generation;}

#define CHECK(x) do { if(!(x)){fprintf(stderr,"FAIL line=%d %s\n",__LINE__,#x);return 1;} } while(0)

static SVCCTL_EvtAckStatus_t (*handler)(void *);
static uint16_t char_handles[COMPANION_GATT_CHAR_COUNT];
static uint8_t char_events[COMPANION_GATT_CHAR_COUNT];
static unsigned added_chars;
static int repair_control_registered;
static uint16_t device_status_length;
static uint8_t published_status[117];
static uint8_t published_status_bytes;

uint8_t aci_gatt_add_service(uint8_t type,const Service_UUID_t *uuid,uint8_t primary,
                             uint8_t records,uint16_t *handle)
{(void)type;(void)uuid;(void)primary;(void)records;*handle=(uint16_t)(0x100u+added_chars);return 0u;}
uint8_t aci_gatt_add_char(uint16_t service,uint8_t type,const Char_UUID_t *uuid,
                          uint16_t length,uint8_t properties,uint8_t permissions,
                          uint8_t events,uint8_t key_size,uint8_t variable,uint16_t *handle)
{(void)service;(void)type;(void)uuid;(void)length;(void)properties;(void)permissions;
 (void)events;(void)key_size;(void)variable;
 if(uuid->bytes[12]==0x03u&&uuid->bytes[13]==0x40u)repair_control_registered=1;
 if(uuid->bytes[12]==0x01u&&uuid->bytes[13]==0x10u)device_status_length=length;
 *handle=(uint16_t)(0x200u+3u*added_chars);
 if(added_chars<COMPANION_GATT_CHAR_COUNT) {
     char_handles[added_chars]=*handle;char_events[added_chars]=events;
 }
 added_chars++;return 0u;}
uint8_t aci_gatt_update_char_value(uint16_t service,uint16_t handle,uint8_t offset,
                                   uint8_t length,const uint8_t *value)
{
    (void)service;(void)offset;
    if(handle==char_handles[COMPANION_GATT_CHAR_DEVICE_STATUS]) {
        if(length>device_status_length)return BLE_STATUS_INVALID_PARAMS;
        if(length>sizeof(published_status))return BLE_STATUS_INVALID_PARAMS;
        memcpy(published_status,value,length);published_status_bytes=length;
    }
    return 0u;
}
void SVCCTL_RegisterSvcHandler(SVCCTL_EvtAckStatus_t (*fn)(void *)){handler=fn;}
/* Registration/handle routing only; a long publication would be outside this
 * fixture's contract. Keep it a hard failure rather than simulating success. */
uint8_t aci_gatt_update_char_value_ext(uint16_t connection,uint16_t service,
    uint16_t handle,uint8_t kind,uint16_t total,uint16_t offset,uint8_t length,
    const uint8_t *value)
{
    (void)connection;(void)service;(void)handle;(void)kind;(void)total;
    (void)offset;(void)length;(void)value;return BLE_STATUS_INVALID_PARAMS;
}
/* Fault publication checks do not exercise the unrelated privacy log ring. */
void comp_diag_log_record_code(uint16_t code,uint8_t severity,uint32_t a,
                               uint32_t b,uint32_t c,uint32_t d)
{(void)code;(void)severity;(void)a;(void)b;(void)c;(void)d;}

static SVCCTL_EvtAckStatus_t packet(uint16_t handle,uint16_t offset,
                                    const uint8_t *bytes,uint16_t length,
                                    int truncate)
{
    uint8_t raw[sizeof(hci_uart_pckt)]={0};hci_uart_pckt *uart=(void*)raw;
    hci_event_pckt *event=(void*)uart->data;evt_blecore_aci *blue=(void*)event->data;
    aci_gatt_attribute_modified_event_rp0 *modified=(void*)blue->data;
    uart->type=0x04u;event->evt=HCI_VENDOR_SPECIFIC_DEBUG_EVT_CODE;
    blue->ecode=ACI_GATT_ATTRIBUTE_MODIFIED_VSEVT_CODE;
    modified->Attr_Handle=handle;modified->Offset=offset;
    modified->Attr_Data_Length=length;
    if(length)memcpy(modified->Attr_Data,bytes,length);
    event->plen=(uint8_t)(sizeof(uint16_t)+
        offsetof(aci_gatt_attribute_modified_event_rp0,Attr_Data)+length-
        (truncate?1u:0u));
    return handler(raw);
}

static void capture(const companion_gatt_event_t *event,void *context)
{*(companion_gatt_event_t*)context=*event;}
typedef struct {companion_gatt_event_t events[8];unsigned count;} captured_queue_t;
static void capture_queue(const companion_gatt_event_t *event,void *context)
{captured_queue_t *q=context;if(q->count<8u)q->events[q->count++]=*event;}

int main(int argc,char **argv)
{
    _Static_assert(sizeof(companion_gatt_device_status_v1_t)==20u,"legacy identity prefix");
    _Static_assert(sizeof(companion_gatt_device_status_v1_wba_ext_t)==36u,"WBA identity prefix");
    _Static_assert(sizeof(companion_recording_capacity_v1_t)==48u,"capacity tail layout");
    _Static_assert(sizeof(companion_gatt_device_status_v1_wba_capacity_t)==84u,"capacity status layout");
    companion_gatt_recording_chunk_pull_v1_t request={0},parsed={0};
    companion_gatt_event_t event={0};
    uint8_t oversized[33u]={0};
    request.schema_version=1u;request.flags=1u;request.recording_id=7u;
    CHECK(companion_gatt_stm32wb_init()==BLE_STATUS_SUCCESS&&handler!=NULL);
    CHECK(added_chars==COMPANION_GATT_CHAR_COUNT&&repair_control_registered&&device_status_length==116u);
    if(argc==2&&strcmp(argv[1],"queue")==0) {
        uint16_t h=char_handles[COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL];
        uint8_t cccd[2]={1u,0u};captured_queue_t q={0};
        for(unsigned i=0;i<8u;i++) {
            uint16_t off=(uint16_t)(i%3u);
            CHECK(packet((uint16_t)(h+off),0u,off==2u?cccd:(const uint8_t*)&request,
                off==2u?2u:sizeof(request),0)==SVCCTL_EvtAckFlowEnable);
        }
        CHECK(packet(h,0u,(const uint8_t*)&request,sizeof(request),0)==SVCCTL_EvtAckFlowEnable);
        CHECK(companion_gatt_stm32wb_drain(capture_queue,&q)==8u&&q.count==8u);
        for(unsigned i=0;i<8u;i++) {
            unsigned off=i%3u;const companion_gatt_event_t *v=&q.events[i];
            CHECK(v->attr_handle==h+off&&v->char_id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL);
            CHECK(v->type==(off==2u?COMPANION_GATT_EVENT_NOTIFY_ENABLED:COMPANION_GATT_EVENT_WRITE));
            CHECK(v->payload_len==(off==2u?2u:sizeof(request)));
            CHECK(!memcmp(v->payload,off==2u?cccd:(const uint8_t*)&request,v->payload_len));
        }
        CHECK(!companion_gatt_stm32wb_has_pending());puts("PASS compact queue depth=8 overflow and exact handle/payload");return 0;
    }
    if(argc==2&&strcmp(argv[1],"completion")==0) {
        for(unsigned id=0u;id<COMPANION_GATT_CHAR_COUNT;++id) {
            bool lane=id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL ||
                id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B;
            CHECK(((char_events[id]&GATT_NOTIFY_NOTIFICATION_COMPLETION)!=0u)==lane);
            CHECK(companion_gatt_stm32wb_is_recording_value_handle((uint16_t)(char_handles[id]+1u))==lane);
            CHECK(!companion_gatt_stm32wb_is_recording_value_handle(char_handles[id]));
            CHECK(!companion_gatt_stm32wb_is_recording_value_handle((uint16_t)(char_handles[id]+2u)));
        }
        CHECK(!companion_gatt_stm32wb_is_recording_value_handle(0u));
        CHECK(!companion_gatt_stm32wb_is_recording_value_handle(UINT16_MAX));
        CHECK(!companion_gatt_stm32wb_has_pending());
        puts("PASS_WBA_RECORDING_COMPLETION_ROUTING two_lanes=1 unrelated_and_cccd_rejected=1 no_control_queue=1 software_only=1");
        return 0;
    }
    uint8_t status[117]={0};status[0]=1u;memcpy(status+84u,"CRV2",4u);
    /* Model the ST API's actual declared-value bound: the old allocation
     * rejects the WHOLE update rather than truncating just its extension. */
    device_status_length=84u;
    CHECK(companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_DEVICE_STATUS,status,116u)==BLE_STATUS_INVALID_PARAMS);
    CHECK(published_status_bytes==0u);
    device_status_length=116u;
    CHECK(companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_DEVICE_STATUS,status,116u)==BLE_STATUS_SUCCESS);
    CHECK(published_status_bytes==116u&&memcmp(status,published_status,116u)==0);
    CHECK(companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_DEVICE_STATUS,status,117u)==BLE_STATUS_INVALID_PARAMS);
    CHECK(published_status_bytes==116u);
    if(argc==2&&strcmp(argv[1],"capability")==0) {
        puts("PASS_WBA_STATUS_CAPABILITY_PUBLICATION old84_rejects116=1 registered116_preserves_full_value=1 oversize117_rejected=1 software_only=1");
        return 0;
    }

    CHECK(packet(char_handles[COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL],0u,
                 (const uint8_t*)&request,sizeof(request),0)==SVCCTL_EvtAckFlowEnable);
    CHECK(companion_gatt_stm32wb_drain(capture,&event)==1u&&
          event.type==COMPANION_GATT_EVENT_WRITE&&
          event.char_id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL&&
          event.payload_len==sizeof(request));

    CHECK(packet(char_handles[COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL],1u,
                 (const uint8_t*)&request,sizeof(request),0)==SVCCTL_EvtAckFlowEnable&&
          !companion_gatt_stm32wb_has_pending());
    CHECK(packet(char_handles[COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL],0x8000u,
                 (const uint8_t*)&request,sizeof(request),0)==SVCCTL_EvtAckFlowEnable&&
          !companion_gatt_stm32wb_has_pending());
    CHECK(packet(char_handles[COMPANION_GATT_CHAR_RECORDING_CONTROL],0u,
                 oversized,sizeof(oversized),0)==SVCCTL_EvtAckFlowEnable&&
          !companion_gatt_stm32wb_has_pending());
    CHECK(packet(char_handles[COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL],0u,
                 (const uint8_t*)&request,sizeof(request),1)==SVCCTL_EvtNotAck&&
          !companion_gatt_stm32wb_has_pending());
    CHECK(packet((uint16_t)(char_handles[COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL]+2u),0u,
                 (const uint8_t*)&request,1u,0)==SVCCTL_EvtAckFlowEnable&&
          !companion_gatt_stm32wb_has_pending());

    CHECK(companion_gatt_parse_recording_chunk_pull_v1((const uint8_t*)&request,
              (uint16_t)(sizeof(request)-1u),&parsed)==COMPANION_GATT_PARSE_TOO_SHORT);
    request.schema_version=2u;
    CHECK(companion_gatt_parse_recording_chunk_pull_v1((const uint8_t*)&request,
              sizeof(request),&parsed)==COMPANION_GATT_PARSE_UNSUPPORTED_VERSION);
    CHECK(companion_gatt_parse_recording_chunk_pull_v1(NULL,sizeof(request),&parsed)==
              COMPANION_GATT_PARSE_BAD_ARGUMENT);
    puts("PASS_WBA_PRODUCT_GATT_FAULTS repair_control_registered=1 nonzero_offset=2 oversized=1 truncated=1 bad_cccd=1 short=1 schema=1 null=1 queued_side_effects=0");
    return 0;
}
