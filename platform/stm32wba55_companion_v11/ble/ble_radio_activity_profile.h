#ifndef COMP_V11_BLE_RADIO_ACTIVITY_PROFILE_H
#define COMP_V11_BLE_RADIO_ACTIVITY_PROFILE_H
#include <stdbool.h>
#include <stdint.h>
#include <limits.h>
/* Existing LL platform callbacks, not antenna on/off edges or an end reason.
 * Caller supplies its serialized existing SysTick wall clock. Partial first
 * or last activities stay censored; no command, packet or UART in callbacks. */
typedef struct {
    uint32_t since_us,min_us,max_us;
    uint16_t bins[4];
    uint8_t active,flags;
} comp_ble_radio_activity_profile_t;
_Static_assert(sizeof(comp_ble_radio_activity_profile_t)==24u,"bounded radio span profile");
static inline void comp_radio_activity_reset(comp_ble_radio_activity_profile_t *p)
{*p=(comp_ble_radio_activity_profile_t){.min_us=UINT32_MAX};}
static inline void comp_radio_activity_observe(comp_ble_radio_activity_profile_t *p,bool active,uint32_t now)
{
    if(active) {
        if(p->active)p->flags|=1u;
        p->since_us=now;p->active=1u;return;
    }
    if(!p->active){p->flags|=1u;return;}
    p->active=0u;uint32_t elapsed=now-p->since_us;
    if(elapsed>65535u){p->flags|=2u;return;}
    unsigned bin=(elapsed>=3000u)+(elapsed>=5500u)+(elapsed>=7000u);
    if(p->bins[bin]==UINT16_MAX)p->flags|=4u;else ++p->bins[bin];
    if(elapsed<p->min_us)p->min_us=elapsed;
    if(elapsed>p->max_us)p->max_us=elapsed;
}
#endif
