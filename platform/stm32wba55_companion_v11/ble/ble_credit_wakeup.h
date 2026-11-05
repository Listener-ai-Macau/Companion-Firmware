#ifndef COMP_V11_BLE_CREDIT_WAKEUP_H
#define COMP_V11_BLE_CREDIT_WAKEUP_H
#include <stdbool.h>
#include <stdint.h>
#include <limits.h>

/* A public controller report successfully queued to the original SDK is a
 * progress hint, not a resource credit or a durable/transmit acknowledgement.
 * Only a subsequent normal host cycle qualifies a foreground retry. The
 * actual GATT API still decides admission; no packet/cursor lives here. */
typedef struct {
    uint32_t generation;
    volatile uint8_t pending; /* 0=none,1=queued,2=normal host cycle observed */
    bool attempting;
    uint16_t wakes,accepted,resource;
} comp_v11_ble_credit_wakeup_t;
_Static_assert(sizeof(comp_v11_ble_credit_wakeup_t)==12u,"bounded progress hint");

/* Pinned original hci_queue_send_pckt returns boolean1 after posting or
 * synchronous dispatch. This is NOT the GATT/ACI BLE_STATUS_SUCCESS(0).
 * Only the known original callback has this audited transport contract. */
static inline bool comp_credit_wakeup_transport_queued(bool progress,bool original_bound,uint8_t result)
{return progress&&original_bound&&result==1u;}

static inline void comp_credit_wakeup_disarm(comp_v11_ble_credit_wakeup_t *s)
{s->pending=0u;s->attempting=false;}
static inline void comp_credit_wakeup_reset(comp_v11_ble_credit_wakeup_t *s,uint32_t generation)
{*s=(comp_v11_ble_credit_wakeup_t){.generation=generation};}
static inline void comp_credit_wakeup_increment(uint16_t *n)
{if(*n!=UINT16_MAX)++*n;}
static inline void comp_credit_wakeup_note(comp_v11_ble_credit_wakeup_t *s,uint32_t generation)
{
    if(s->generation!=generation)comp_credit_wakeup_reset(s,generation);
    if(!s->pending)s->pending=1u; /* Coalesce, never demote an observed cycle. */
}
static inline void comp_credit_wakeup_host_cycle(comp_v11_ble_credit_wakeup_t *s)
{if(s->pending==1u)s->pending=2u;}
static inline bool comp_credit_wakeup_take(comp_v11_ble_credit_wakeup_t *s,
    uint32_t generation,bool allowed,bool waiting,bool in_call)
{
    if(s->generation!=generation||!allowed){comp_credit_wakeup_disarm(s);return false;}
    if(!waiting){s->pending=0u;return false;}
    if(s->pending!=2u||in_call)return false;
    s->pending=0u;s->attempting=true;comp_credit_wakeup_increment(&s->wakes);
    return true;
}
static inline void comp_credit_wakeup_result(comp_v11_ble_credit_wakeup_t *s,
    uint32_t generation,bool accepted,bool resource)
{
    if(s->generation!=generation){comp_credit_wakeup_disarm(s);return;}
    if(!s->attempting)return;
    s->attempting=false;
    if(accepted)comp_credit_wakeup_increment(&s->accepted);
    else if(resource)comp_credit_wakeup_increment(&s->resource);
    /* Other failures/cancellation remain an unclassified wake, never success. */
}
#endif
