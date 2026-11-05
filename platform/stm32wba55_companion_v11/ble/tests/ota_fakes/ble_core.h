#ifndef OTA_TEST_BLE_CORE_H
#define OTA_TEST_BLE_CORE_H
#include <stdint.h>
#define HCI_VENDOR_SPECIFIC_DEBUG_EVT_CODE 255u
#define ACI_GATT_ATTRIBUTE_MODIFIED_VSEVT_CODE 0x0C01u
#define UUID_TYPE_128 2u
#define PRIMARY_SERVICE 1u
#define CHAR_PROP_READ 2u
#define CHAR_PROP_WRITE_WITHOUT_RESP 4u
#define CHAR_PROP_WRITE 8u
#define CHAR_PROP_NOTIFY 16u
#define CHAR_PROP_INDICATE 32u
#define ATTR_PERMISSION_ENCRY_READ 4u
#define ATTR_PERMISSION_ENCRY_WRITE 32u
#define ATTR_PERMISSION_NONE 0u
#define GATT_DONT_NOTIFY_EVENTS 0u
#define GATT_NOTIFY_ATTRIBUTE_WRITE 1u
#define GATT_NOTIFY_NOTIFICATION_COMPLETION 8u
#define BLE_STATUS_SUCCESS 0u
#define BLE_STATUS_INVALID_PARAMS 18u
#define BLE_STATUS_INSUFFICIENT_RESOURCES 0x64u
#define BLE_STATUS_BUSY 0x93u
typedef uint8_t tBleStatus;
typedef union {uint8_t bytes[16];} Service_UUID_t,Char_UUID_t;
#pragma pack(push,1)
typedef struct {uint8_t type,data[257];} hci_uart_pckt;
typedef struct {uint8_t evt,plen,data[255];} hci_event_pckt;
typedef struct {uint16_t ecode;uint8_t data[253];} evt_blecore_aci;
typedef struct {uint16_t Connection_Handle,Attr_Handle,Offset,Attr_Data_Length;uint8_t Attr_Data[245];} aci_gatt_attribute_modified_event_rp0;
#pragma pack(pop)
uint8_t aci_gatt_add_service(uint8_t,const Service_UUID_t *,uint8_t,uint8_t,uint16_t *);
uint8_t aci_gatt_add_char(uint16_t,uint8_t,const Char_UUID_t *,uint16_t,uint8_t,uint8_t,uint8_t,uint8_t,uint8_t,uint16_t *);
uint8_t aci_gatt_update_char_value(uint16_t,uint16_t,uint8_t,uint8_t,const uint8_t *);
uint8_t aci_gatt_update_char_value_ext(uint16_t,uint16_t,uint16_t,uint8_t,uint16_t,uint16_t,uint8_t,const uint8_t *);
#endif
