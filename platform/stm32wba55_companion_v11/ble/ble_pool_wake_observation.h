#ifndef COMP_V11_BLE_POOL_WAKE_OBSERVATION_H
#define COMP_V11_BLE_POOL_WAKE_OBSERVATION_H
#include "ble_micro_observation.h"
/* Observe an already-open resource wait. A pool event inside an ACI call
 * is counted separately, never assumed to describe a completed failure.
 * Earliest wake is retained until the next immutable data publication.
 * No scheduling, gate changes, per-packet UART, or extra packet buffers. */
typedef struct {
    uint32_t window_start_us,window_us,clock_fallbacks;
    uint32_t pending_since_us,pending;
    uint32_t pool_wakes,pool_nested,dispatch_calls;
    uint32_t dispatch_us,dispatch_max_us,dispatch_over_1000;
    uint32_t wake_success,wake_rejected,commit_calls;
} comp_v11_ble_pool_wake_observation_t;
_Static_assert(sizeof(comp_v11_ble_pool_wake_observation_t)==56u,"reuse prior56B observer");
static inline void comp_v11_ble_pool_wake(comp_v11_ble_pool_wake_observation_t *m,uint32_t now,bool waiting,bool nested)
{
    if(nested){++m->pool_nested;return;}
    if(!waiting)return;
    ++m->pool_wakes;
    if(!m->pending){m->pending_since_us=now;m->pending=1u;}
}
static inline bool comp_v11_ble_pool_dispatch(comp_v11_ble_pool_wake_observation_t *m,uint32_t now)
{
    if(!m->pending)return false;
    uint32_t elapsed=now-m->pending_since_us;m->pending=0u;
    ++m->dispatch_calls;m->dispatch_us+=elapsed;
    if(elapsed>m->dispatch_max_us)m->dispatch_max_us=elapsed;
    if(elapsed>1000u)++m->dispatch_over_1000;
    return true;
}
static inline void comp_v11_ble_pool_result(comp_v11_ble_pool_wake_observation_t *m,bool after_wake,bool success)
{
    if(success)++m->commit_calls;
    if(after_wake){if(success)++m->wake_success;else ++m->wake_rejected;}
}
#endif
