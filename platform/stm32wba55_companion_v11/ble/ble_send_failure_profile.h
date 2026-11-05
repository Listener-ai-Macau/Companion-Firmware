#ifndef COMP_V11_BLE_SEND_FAILURE_PROFILE_H
#define COMP_V11_BLE_SEND_FAILURE_PROFILE_H
#include <stdint.h>

/* Retain across transfers/disconnects until normal application restart.
 * Public host-to-controller ACL metadata only, not RF fragment/payload data.
 * Caller serializes record/snapshot with its existing PRIMASK primitives. */
typedef struct {
    uint32_t count;
    uint32_t first;
    uint32_t last;
} comp_v11_ble_send_failure_profile_t;
_Static_assert(sizeof(comp_v11_ble_send_failure_profile_t)==12u,"bounded LL failure history");

static inline void comp_v11_ble_send_failure_record(
    comp_v11_ble_send_failure_profile_t *history,
    uint8_t status,uint8_t flags,uint16_t bytes)
{
    if(status==0u)return;
    const uint32_t metadata=(uint32_t)status|((uint32_t)flags<<8u)|((uint32_t)bytes<<16u);
    if(history->count==0u)history->first=metadata;
    history->last=metadata;
    if(history->count!=UINT32_MAX)++history->count;
}
#endif
