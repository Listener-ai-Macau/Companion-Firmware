#ifndef COMP_V11_BLE_MTU_H
#define COMP_V11_BLE_MTU_H
#include <stdbool.h>
#include <stdint.h>

/* One ATT bearer per connection. Ask the configured maximum once; ATT chooses
 * min(local, peer). Retry only a transient command rejection, at most twice.
 * Command success is NOT an agreed MTU. No callback commands or blocking wait. */
typedef struct {
    uint32_t retry_after;
    uint16_t mtu;
    uint8_t attempts, status;
} comp_v11_ble_mtu_t;

static inline void comp_v11_ble_mtu_open(comp_v11_ble_mtu_t *s,uint32_t now)
{ s->retry_after=now+500u;s->mtu=23u;s->attempts=0u;s->status=0xFFu; }

static inline bool comp_v11_ble_mtu_due(const comp_v11_ble_mtu_t *s,
    uint32_t now,bool authorized,bool command_slot)
{
    return authorized && command_slot && s->attempts<2u &&
        (int32_t)(now-s->retry_after)>=0;
}

static inline void comp_v11_ble_mtu_requested(comp_v11_ble_mtu_t *s,
    uint32_t now,uint8_t status,bool transient)
{
    s->status=status;
    if(status==0u)s->attempts=0x40u; /* accepted, await the actual event */
    else if(transient){++s->attempts;s->retry_after=now+1000u;}
    else s->attempts=2u;
}

static inline bool comp_v11_ble_mtu_agreed(comp_v11_ble_mtu_t *s,
    uint16_t peer_mtu,uint16_t local_max)
{
    if(peer_mtu<23u || local_max<23u)return false;
    s->mtu=peer_mtu<local_max?peer_mtu:local_max;
    s->attempts=0x80u;return true;
}

static inline uint16_t comp_v11_ble_mtu_value_capacity(const comp_v11_ble_mtu_t *s)
{
    uint16_t bytes=s->mtu>=23u?(uint16_t)(s->mtu-3u):20u;
    return bytes>509u?509u:bytes;
}

/* ATT forbids the initiator's notifications between accepted exchange request
 * and response. Preserve queued packets; MIC/NOR work keeps running. */
static inline bool comp_v11_ble_mtu_notifications_allowed(const comp_v11_ble_mtu_t *s)
{ return s->attempts!=0x40u; }

static inline bool comp_v11_ble_mtu_refused(comp_v11_ble_mtu_t *s,uint8_t error)
{
    if(s->attempts!=0x40u || !error)return false;
    s->status=error;s->attempts=2u;return true; /* retain default ATT23 */
}
#endif
