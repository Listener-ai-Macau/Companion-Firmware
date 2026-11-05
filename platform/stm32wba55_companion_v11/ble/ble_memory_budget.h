#ifndef COMP_V11_BLE_MEMORY_BUDGET_H
#define COMP_V11_BLE_MEMORY_BUDGET_H
#include "companion_gatt_schema.h"
#include "wba_ota_gatt.h"

/* Keep every existing service, UUID, handle reservation and transport value.
 * Signed single-file OTA uses40/509/64/(56or60)-byte characteristics today; the
 * former452-byte writable system manifest is no longer registered. */
#define COMP_V11_BLE_GATT_SERVICES (2u + COMPANION_GATT_PRODUCT_SERVICE_COUNT + 1u)
#define COMP_V11_BLE_GATT_ATTRIBUTES (9u + COMPANION_GATT_PRODUCT_ATTRIBUTE_RESERVATION + 9u)
/* Existing automatic GATT/GAP values use<=36+24 bytes.128 covers them;
 * another128 explicitly retains allocation/alignment headroom. The old
 * FW217/FW369 out-of-memory failures remain evidence, not a lower target. */
#define COMP_V11_BLE_AUTO_VALUE_BYTES 128u
#define COMP_V11_BLE_VALUE_MARGIN_BYTES 128u
#define COMP_V11_BLE_OTA_VALUE_BYTES \
    (COMP_V11_OTA_CONTROL_BYTES + COMP_V11_OTA_VALUE_BYTES + \
     COMP_V11_OTA_STATUS_BYTES + COMP_V11_OTA_IDENTITY_BYTES + 4u*19u + 2u)
#define COMP_V11_BLE_ATT_VALUE_BYTES \
    (COMPANION_GATT_PRODUCT_VALUE_BYTES + COMP_V11_BLE_OTA_VALUE_BYTES + \
     COMP_V11_BLE_AUTO_VALUE_BYTES + COMP_V11_BLE_VALUE_MARGIN_BYTES)
/* Conservative Full/Basic upper bound, not only the smaller PO bound:
 * 6*links+5 timers plus one spare. Pinned BLE_TIMER_t is40B; AMM adds4B.
 * Keep the shared/event pool unchanged by subtracting ONLY unused timer
 * reservation from the total. This preserves LOGICAL AMM admission, not a
 * proof of the underlying allocator's physical fragmentation capacity.
 * The compact pool therefore requires explicit DEV opt-in and physical
 * burst/pairing/OTA qualification. Packet pools and the event FIFO stay intact. */
#define COMP_V11_BLE_TIMER_STRUCT_BYTES 40u
#define COMP_V11_BLE_TIMER_SLOTS (6u*CFG_BLE_NUM_LINK + 6u)
#ifndef COMPANION_WBA_COMPACT_BLE_AMM
#define COMPANION_WBA_COMPACT_BLE_AMM 0
#endif
#if COMPANION_WBA_COMPACT_BLE_AMM
#define COMP_V11_BLE_TIMER_WORDS (COMP_V11_BLE_TIMER_SLOTS * ((COMP_V11_BLE_TIMER_STRUCT_BYTES+4u)/4u))
#else
#define COMP_V11_BLE_TIMER_WORDS 400u
#endif
#define COMP_V11_BLE_AMM_BYTES (4000u - (400u-COMP_V11_BLE_TIMER_WORDS)*4u)
#define COMP_V11_BLE_SERVICE_CALLBACKS 2u
#define COMP_V11_BLE_ATT_MTU_MAX 512u
#endif
