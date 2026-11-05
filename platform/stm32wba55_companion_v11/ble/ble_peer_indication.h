#ifndef COMP_V11_BLE_PEER_INDICATION_H
#define COMP_V11_BLE_PEER_INDICATION_H
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

/* One unenhanced ATT bearer; no remote database/value cache. A phone can be
 * a GATT server even though Companion remains a GAP peripheral. Its Service
 * Changed indication must be confirmed, not rejected as an unknown request.
 * Queue in the event callback and issue the official command in foreground. */
typedef struct {
    uint32_t retry_at,deadline;
    uint16_t connection,attribute;
    uint8_t pending,attempts;
} comp_v11_peer_indication_t;
_Static_assert(sizeof(comp_v11_peer_indication_t)==16u,"peer indication RAM budget");

static inline void comp_v11_peer_indication_reset(comp_v11_peer_indication_t *s)
{ memset(s,0,sizeof(*s)); }

static inline bool comp_v11_peer_indication_receive(comp_v11_peer_indication_t *s,
    uint16_t connection,bool allowed,bool extended,const uint8_t *p,uint16_t n,uint32_t now)
{
    const uint16_t prefix=extended?8u:5u;
    if(!allowed || connection==0xffffu || !p || n<prefix)return false;
    const uint16_t handle=(uint16_t)p[0]|((uint16_t)p[1]<<8);
    const uint16_t attribute=(uint16_t)p[2]|((uint16_t)p[3]<<8);
    const uint16_t length=extended?((uint16_t)p[6]|((uint16_t)p[7]<<8)):p[4];
    if(handle!=connection || !attribute || length!=n-prefix)return false;
    /* Extended fragments describe one ATT indication. Nothing consumes its
     * value here; retain one confirmation, never one per host event fragment.
     * A duplicate must not renew the finite deadline or reset retry count. */
    if(s->pending)return false;
    s->connection=handle;s->attribute=attribute;s->pending=1u;s->attempts=0u;
    s->retry_at=now;s->deadline=now+1000u;return true;
}

static inline bool comp_v11_peer_indication_due(comp_v11_peer_indication_t *s,
    uint16_t connection,bool allowed,bool commands_allowed,uint32_t now)
{
    if(!s->pending)return false;
    if(!allowed || connection==0xffffu || s->connection!=connection ||
       (int32_t)(now-s->deadline)>=0) {s->pending=0u;return false;}
    return commands_allowed && (int32_t)(now-s->retry_at)>=0;
}

static inline void comp_v11_peer_indication_result(comp_v11_peer_indication_t *s,
    uint8_t status,bool transient,uint32_t now)
{
    ++s->attempts;
    if(!status || !transient || s->attempts>=8u)s->pending=0u;
    else s->retry_at=now+10u;
}
#endif
