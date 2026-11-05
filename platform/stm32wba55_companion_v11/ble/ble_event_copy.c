#include "ble_event_copy.h"

#include <stddef.h>
#include <string.h>

comp_v11_ble_event_copy_result_t comp_v11_ble_event_plan(
    const uint8_t *data, uint16_t length,
    const uint8_t *ext_data, uint16_t ext_length,
    uint16_t *total_length)
{
    uint32_t total;
    uint32_t declared;
    if(data==NULL || total_length==NULL ||
       (ext_length!=0u && ext_data==NULL))
        return COMP_V11_BLE_EVENT_COPY_BAD_ARGUMENT;
    *total_length=0u;
    if(length<COMP_V11_BLE_HCI_EVENT_HEADER_BYTES)
        return COMP_V11_BLE_EVENT_COPY_BAD_LENGTH;
    if(data[0]!=COMP_V11_BLE_HCI_EVENT_PACKET_TYPE)
        return COMP_V11_BLE_EVENT_COPY_BAD_TYPE;
    total=(uint32_t)length+(uint32_t)ext_length;
    declared=COMP_V11_BLE_HCI_EVENT_HEADER_BYTES+(uint32_t)data[2];
    if(total>UINT16_MAX || total>COMP_V11_BLE_HCI_EVENT_MAX_BYTES ||
       total!=declared || (uint32_t)length>declared)
        return COMP_V11_BLE_EVENT_COPY_BAD_LENGTH;
    *total_length=(uint16_t)total;
    return COMP_V11_BLE_EVENT_COPY_OK;
}

comp_v11_ble_event_copy_result_t comp_v11_ble_event_flatten(
    const uint8_t *data, uint16_t length,
    const uint8_t *ext_data, uint16_t ext_length,
    uint8_t *output, uint16_t output_capacity,
    uint16_t *output_length)
{
    uint16_t total=0u;
    comp_v11_ble_event_copy_result_t result=comp_v11_ble_event_plan(
        data,length,ext_data,ext_length,&total);
    if(output_length==NULL)return COMP_V11_BLE_EVENT_COPY_BAD_ARGUMENT;
    *output_length=0u;
    if(result!=COMP_V11_BLE_EVENT_COPY_OK)return result;
    if(output==NULL)return COMP_V11_BLE_EVENT_COPY_BAD_ARGUMENT;
    if(output_capacity<total)return COMP_V11_BLE_EVENT_COPY_OUTPUT_TOO_SMALL;
    memcpy(output,data,length);
    if(ext_length!=0u)memcpy(&output[length],ext_data,ext_length);
    *output_length=total;
    return COMP_V11_BLE_EVENT_COPY_OK;
}
