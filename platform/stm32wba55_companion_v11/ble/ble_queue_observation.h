#ifndef COMP_V11_BLE_QUEUE_OBSERVATION_H
#define COMP_V11_BLE_QUEUE_OBSERVATION_H
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
/* Foreground SDK accept-return / completion-dispatch inventory, not RF ACKs.
 * Recording lanes include their protocol replies. A completion dispatched
 * inside ACI can precede a successful return; defer only that unknown entry.
 * Residence integral excludes the command's own time, a deliberate lower
 * bound. No GATT call, scheduling decision or payload is changed here. */
typedef struct {
    uint32_t last_ms,elapsed_ms,queued_ms,empty_ms,accepted,completed,data_accepted;
    uint32_t empty_since_ms,empty_max_ms;
    uint16_t pending[2],peak,unmatched,nested,deferred,empty_windows;
    bool running,stopping,in_call,data_call;
    uint8_t call_lane;
} comp_v11_ble_queue_observation_t;
_Static_assert(sizeof(comp_v11_ble_queue_observation_t)<=56u,"bounded queue observation");
static inline unsigned comp_v11_ble_queue_depth(const comp_v11_ble_queue_observation_t *q)
{return (unsigned)q->pending[0]+q->pending[1];}
static inline void comp_v11_ble_queue_tick(comp_v11_ble_queue_observation_t *q,uint32_t now)
{
    if(q->running) {
        uint32_t delta=now-q->last_ms;unsigned depth=comp_v11_ble_queue_depth(q);
        q->elapsed_ms+=delta;q->queued_ms+=delta*depth;
        if(!depth)q->empty_ms+=delta;
    }
    q->last_ms=now;
}
static inline void comp_v11_ble_queue_start(comp_v11_ble_queue_observation_t *q,uint32_t now)
{
    uint16_t a=q->pending[0],b=q->pending[1];
    memset(q,0,sizeof(*q));q->pending[0]=a;q->pending[1]=b;
    q->last_ms=q->empty_since_ms=now;q->peak=(uint16_t)(a+b);q->running=true;
}
static inline void comp_v11_ble_queue_stop(comp_v11_ble_queue_observation_t *q,uint32_t now)
{
    comp_v11_ble_queue_tick(q,now);q->stopping=true;
    if(!comp_v11_ble_queue_depth(q) && !q->in_call)q->running=false;
}
static inline bool comp_v11_ble_queue_begin(comp_v11_ble_queue_observation_t *q,unsigned lane,bool data)
{
    if(lane>=2u || q->in_call){if(q->running)++q->unmatched;return false;}
    q->in_call=true;q->call_lane=(uint8_t)lane;q->data_call=data;q->deferred=0u;return true;
}
static inline void comp_v11_ble_queue_complete(comp_v11_ble_queue_observation_t *q,unsigned lane,uint32_t now)
{
    if(lane>=2u){if(q->running)++q->unmatched;return;}
    comp_v11_ble_queue_tick(q,now);
    if(q->pending[lane]) {
        --q->pending[lane];if(q->running)++q->completed;
        if(!comp_v11_ble_queue_depth(q)) {
            q->empty_since_ms=now;
            if(q->stopping && !q->in_call)q->running=false;
        }
    } else if(q->in_call && q->call_lane==lane)++q->deferred;
    else if(q->running)++q->unmatched;
}
static inline void comp_v11_ble_queue_finish(comp_v11_ble_queue_observation_t *q,bool success,uint32_t now)
{
    if(!q->in_call)return; /* disconnect invalidates the pending call */
    unsigned lane=q->call_lane;uint16_t deferred=q->deferred;
    comp_v11_ble_queue_tick(q,now);q->in_call=false;q->deferred=0u;
    if(success) {
        if(q->running) {
            ++q->accepted;if(q->data_call)++q->data_accepted;
            if(!comp_v11_ble_queue_depth(q)) {
                uint32_t gap=now-q->empty_since_ms;
                ++q->empty_windows;if(gap>q->empty_max_ms)q->empty_max_ms=gap;
            }
        }
        ++q->pending[lane];unsigned depth=comp_v11_ble_queue_depth(q);
        if(q->running && depth>q->peak)q->peak=(uint16_t)depth;
        if(deferred){if(q->running)++q->nested;comp_v11_ble_queue_complete(q,lane,now);--deferred;}
    }
    if(deferred && q->running)q->unmatched=(uint16_t)(q->unmatched+deferred);
    if(q->stopping && !comp_v11_ble_queue_depth(q))q->running=false;
}
static inline void comp_v11_ble_queue_disconnect(comp_v11_ble_queue_observation_t *q,uint32_t now)
{
    comp_v11_ble_queue_tick(q,now);q->pending[0]=q->pending[1]=0u;
    q->running=false;q->in_call=false;q->deferred=0u;
}
#endif
