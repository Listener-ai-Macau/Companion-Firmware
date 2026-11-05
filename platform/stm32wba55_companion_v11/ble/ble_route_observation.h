#ifndef COMP_V11_BLE_ROUTE_OBSERVATION_H
#define COMP_V11_BLE_ROUTE_OBSERVATION_H
#include "ble_micro_observation.h"
#if defined(_MSC_VER)
#include <intrin.h>
static inline uint32_t route_load(volatile uint32_t *p){return (uint32_t)_InterlockedCompareExchange((volatile long*)p,0,0);}
static inline uint32_t route_or(volatile uint32_t *p,uint32_t v){return (uint32_t)_InterlockedOr((volatile long*)p,(long)v);}
static inline uint32_t route_and(volatile uint32_t *p,uint32_t v){return (uint32_t)_InterlockedAnd((volatile long*)p,(long)v);}
static inline uint32_t route_add(volatile uint32_t *p,uint32_t v){return (uint32_t)_InterlockedExchangeAdd((volatile long*)p,(long)v);}
#else
static inline uint32_t route_load(volatile uint32_t *p){return __atomic_load_n(p,__ATOMIC_ACQUIRE);}
static inline uint32_t route_or(volatile uint32_t *p,uint32_t v){return __atomic_fetch_or(p,v,__ATOMIC_ACQ_REL);}
static inline uint32_t route_and(volatile uint32_t *p,uint32_t v){return __atomic_fetch_and(p,v,__ATOMIC_ACQ_REL);}
static inline uint32_t route_add(volatile uint32_t *p,uint32_t v){return __atomic_fetch_add(p,v,__ATOMIC_ACQ_REL);}
#endif
#define ROUTE_PENDING UINT32_C(0x80000000)
#define ROUTE_UNMARKED UINT32_C(0x40000000)
#define ROUTE_COUNT UINT32_C(0x3fffffff)
typedef struct {
    volatile uint32_t since_us,word;
    uint32_t total_us,max_us;
} comp_v11_ble_route_slot_t;
typedef struct {
    uint32_t span_us;
    volatile uint32_t clock_fallbacks;
    comp_v11_ble_route_slot_t job[3];
} comp_v11_ble_route_observation_t;
_Static_assert(sizeof(comp_v11_ble_route_observation_t)==56u,"reuse prior56B, no IRQ masking or extra event buffer");
/* All timestamps are acquired before this short publication. Retain the
 * earliest coalesced request. Foreground captures since before clearing;
 * atomic count updates preserve any ISR's newly published pending bit. */
static inline void comp_v11_ble_route_ready(comp_v11_ble_route_slot_t *s,uint32_t now)
{
    if(!(route_load(&s->word)&ROUTE_PENDING)) {
        s->since_us=now;(void)route_or(&s->word,ROUTE_PENDING);
    }
}
static inline void comp_v11_ble_route_run(comp_v11_ble_route_slot_t *s,uint32_t now)
{
    if(!(route_load(&s->word)&ROUTE_PENDING)){(void)route_or(&s->word,ROUTE_UNMARKED);return;}
    uint32_t since=s->since_us;(void)route_and(&s->word,~ROUTE_PENDING);
    uint32_t elapsed=now-since;s->total_us+=elapsed;
    if(elapsed>s->max_us)s->max_us=elapsed;
    (void)route_add(&s->word,1u);
}
/* The timestamp is for a positive pool event successfully copied and
 * enqueued, not the controller's earlier release or an RF ACK. */
static inline bool comp_v11_ble_route_pool_packet(const uint8_t *p,uint16_t n,uint16_t code)
{
    return p && n>=9u && p[0]==4u && p[1]==255u && p[2]>=6u &&
        n>=3u+(uint16_t)p[2] && p[3]==(uint8_t)code && p[4]==(uint8_t)(code>>8u) &&
        (p[7]!=0u || p[8]!=0u);
}
#endif
