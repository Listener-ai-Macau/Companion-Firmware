#ifndef COMP_V11_BLE_DISPATCH_PROFILE_H
#define COMP_V11_BLE_DISPATCH_PROFILE_H
#include <stdint.h>
#include <limits.h>
/* One earliest outstanding ready mark per cooperative task, not per RF PDU.
 * Caller serializes updates with the existing short IRQ guard. Coalesced
 * ready requests keep the original timestamp. Pending at either boundary
 * is explicitly censored; an unpaired run is never assigned a zero delay.
 * Sums for different tasks overlap and MUST NOT be added to wall time. */
typedef struct {
    uint32_t since_us, count, total_us, max_us, coalesced, unpaired, flags;
} comp_v11_dispatch_slot_t;
typedef struct {comp_v11_dispatch_slot_t job[2];} comp_v11_dispatch_profile_t;
_Static_assert(sizeof(comp_v11_dispatch_profile_t)==56u,"two bounded task summaries");
#define DISPATCH_PENDING 1u
#define DISPATCH_OVERFLOW 2u
#define DISPATCH_BACKWARD 4u
static inline void comp_dispatch_add(comp_v11_dispatch_slot_t *s,uint32_t *p,uint32_t n)
{
    if(n>UINT32_MAX-*p)s->flags|=DISPATCH_OVERFLOW;
    else *p+=n;
}
static inline void comp_dispatch_ready(comp_v11_dispatch_slot_t *s,uint32_t now)
{
    if(s->flags&DISPATCH_PENDING)comp_dispatch_add(s,&s->coalesced,1u);
    else {s->since_us=now;s->flags|=DISPATCH_PENDING;}
}
static inline void comp_dispatch_run(comp_v11_dispatch_slot_t *s,uint32_t now)
{
    if(!(s->flags&DISPATCH_PENDING)){comp_dispatch_add(s,&s->unpaired,1u);return;}
    uint32_t elapsed=now-s->since_us;s->flags&=~DISPATCH_PENDING;
    if(elapsed>INT32_MAX){s->flags|=DISPATCH_BACKWARD;return;}
    comp_dispatch_add(s,&s->count,1u);comp_dispatch_add(s,&s->total_us,elapsed);
    if(elapsed>s->max_us)s->max_us=elapsed;
}
#endif
