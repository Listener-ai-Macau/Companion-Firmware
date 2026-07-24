#include "ble_gatt_aci.h"
#include "svc_ctl.h"

tBleStatus aci_gatt_add_service(uint8_t type, const Service_UUID_t *uuid,
                                uint8_t service_type, uint8_t records,
                                uint16_t *handle) {
  (void)type; (void)uuid; (void)service_type; (void)records;
  if (handle != NULL) *handle = 1u;
  return BLE_STATUS_SUCCESS;
}

tBleStatus aci_gatt_add_char(uint16_t service, uint8_t type,
                             const Char_UUID_t *uuid, uint16_t value_length,
                             uint8_t properties, uint8_t permissions,
                             uint8_t event_mask, uint8_t key_size,
                             uint8_t variable, uint16_t *handle) {
  (void)service; (void)type; (void)uuid; (void)value_length;
  (void)properties; (void)permissions; (void)event_mask;
  (void)key_size; (void)variable;
  if (handle != NULL) *handle = 1u;
  return BLE_STATUS_SUCCESS;
}

tBleStatus aci_gatt_update_char_value(uint16_t service, uint16_t characteristic,
                                      uint8_t offset, uint8_t length,
                                      const uint8_t *value) {
  (void)service; (void)characteristic; (void)offset; (void)length;
  (void)value;
  return BLE_STATUS_SUCCESS;
}

void SVCCTL_RegisterSvcHandler(SVC_CTL_p_EvtHandler_t handler) {
  (void)handler;
}
