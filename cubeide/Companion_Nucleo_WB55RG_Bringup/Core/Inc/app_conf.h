#ifndef COMPANION_NUCLEO_WB55RG_APP_CONF_H
#define COMPANION_NUCLEO_WB55RG_APP_CONF_H

#include_next "app_conf.h"

/* The inherited debug trace path forces CubeWB LPM off.  Direct printf remains
 * available for product diagnostics while normal idle uses the LPM manager. */
#ifndef COMPANION_LOW_POWER_ENABLE
#define COMPANION_LOW_POWER_ENABLE 1
#endif

/* Keep physical FTS02 board facts explicit: an FT6336 I2C configuration
 * readback cannot prove that its INT trace reaches the MCU. P10 A0/TP_INT is
 * now connected for candidate wake validation. Reset is optional for normal
 * wake; set RST to 1 only when P10 A3 is also connected. */
#ifndef COMPANION_TOUCH_INT_WIRED
#define COMPANION_TOUCH_INT_WIRED 1
#endif

#ifndef COMPANION_TOUCH_RST_WIRED
#define COMPANION_TOUCH_RST_WIRED 0
#endif

#if COMPANION_LOW_POWER_ENABLE
#undef CFG_DEBUG_BLE_TRACE
#define CFG_DEBUG_BLE_TRACE 0
#undef CFG_DEBUG_APP_TRACE
#define CFG_DEBUG_APP_TRACE 0
#undef CFG_DEBUG_TRACE
#define CFG_DEBUG_TRACE 0
#undef CFG_DEBUG_TRACE_LIGHT
#define CFG_DEBUG_TRACE_LIGHT 0
#undef CFG_DEBUG_TRACE_FULL
#define CFG_DEBUG_TRACE_FULL 0
#undef APP_DBG_MSG
#define APP_DBG_MSG PRINT_NO_MESG
#undef CFG_LPM_SUPPORTED
#define CFG_LPM_SUPPORTED 1
#undef CFG_DEBUGGER_SUPPORTED
#define CFG_DEBUGGER_SUPPORTED 0
#endif

#undef CFG_BLE_MAX_ATT_MTU
#define CFG_BLE_MAX_ATT_MTU (251)

/* GAP/GATT auto services + VKA1 audio + seven Companion-native services. */
#undef CFG_BLE_NUM_GATT_SERVICES
#define CFG_BLE_NUM_GATT_SERVICES 16

#undef CFG_BLE_NUM_GATT_ATTRIBUTES
#define CFG_BLE_NUM_GATT_ATTRIBUTES 96

#undef CFG_BLE_ATT_VALUE_ARRAY_SIZE
#define CFG_BLE_ATT_VALUE_ARRAY_SIZE (4096)

#ifndef CFG_TASK_COMPANION_GATT_ID
#define CFG_TASK_COMPANION_GATT_ID (CFG_TASK_SW3_BUTTON_PUSHED_ID + 1)
#endif

#ifndef CFG_TASK_COMPANION_DISPLAY_ID
#define CFG_TASK_COMPANION_DISPLAY_ID (CFG_TASK_COMPANION_GATT_ID + 1)
#endif

#undef CFG_LAST_TASK_ID_WITH_HCICMD
#define CFG_LAST_TASK_ID_WITH_HCICMD (CFG_TASK_COMPANION_DISPLAY_ID + 1)

#endif /* COMPANION_NUCLEO_WB55RG_APP_CONF_H */
