#ifndef COMPANION_NUCLEO_WB55RG_BLE_CONF_H
#define COMPANION_NUCLEO_WB55RG_BLE_CONF_H

#include_next "ble_conf.h"

/* VKA1 audio and Companion-native GATT each register a service event handler. */
#undef BLE_CFG_SVC_MAX_NBR_CB
#define BLE_CFG_SVC_MAX_NBR_CB 2

#endif /* COMPANION_NUCLEO_WB55RG_BLE_CONF_H */
