#ifndef COMP_V11_COMPLETION_PROFILE_H
#define COMP_V11_COMPLETION_PROFILE_H
#include "ble_route_observation.h"
/* Current56B retains completion pairs, trades historical host/LL ready
 * totals and completion maximum for same-packet wake/retry/admission.
 * No radio/payload/event modification or per-event UART. */
typedef struct {volatile uint32_t since_us,word;uint32_t total_us;} comp_completion_route_slot_t;
typedef struct {uint32_t stamp[2],total_us,samples,flags;} comp_completion_queue_t;
/* Same prepared packet owner; do not confuse two packets of one window. */
typedef struct {uint32_t stamp,generation,offset,first_delta,first_us,accepted_us,word;} comp_wake_retry_t;
#define WAKE_PENDING 1u
#define WAKE_ATTEMPTED 2u
#define WAKE_MISSING 4u
#define WAKE_OVERFLOW 8u
#define WAKE_BACKWARD 16u
#define WAKE_STALE 32u
#define WAKE_FLAGS 255u
#define WAKE_COUNT UINT32_C(0xffffff)
static inline bool comp_wake_same(const comp_wake_retry_t *q,uint32_t generation,uint32_t offset)
{return q->generation==generation && q->offset==offset;}
static inline void comp_wake_stale(comp_wake_retry_t *q)
{q->word=(q->word&~(WAKE_PENDING|WAKE_ATTEMPTED))|WAKE_STALE;}
static inline void comp_wake_ready(comp_wake_retry_t *q,uint32_t generation,uint32_t offset,uint32_t now)
{
 if(q->word&WAKE_PENDING) {
  if(!comp_wake_same(q,generation,offset))comp_wake_stale(q);
  return; /* Same-owner coalescing retains the first event, not a new clock. */
 }
 q->generation=generation;q->offset=offset;q->stamp=now;q->first_delta=0u;q->word|=WAKE_PENDING;
}
static inline void comp_wake_attempt(comp_wake_retry_t *q,uint32_t generation,uint32_t offset,uint32_t now)
{
 if(!(q->word&WAKE_PENDING))return;
 if(!comp_wake_same(q,generation,offset)){comp_wake_stale(q);return;}
 if(q->word&WAKE_ATTEMPTED)return;
 uint32_t elapsed=now-q->stamp;
 if(elapsed>INT32_MAX){q->word=(q->word&~WAKE_PENDING)|WAKE_BACKWARD;return;}
 q->first_delta=elapsed;q->word|=WAKE_ATTEMPTED;
}
static inline void comp_wake_accepted(comp_wake_retry_t *q,uint32_t generation,uint32_t offset,uint32_t now)
{
 if(!(q->word&WAKE_PENDING))return;
 if(!comp_wake_same(q,generation,offset)){comp_wake_stale(q);return;}
 uint32_t elapsed=now-q->stamp;
 bool attempted=(q->word&WAKE_ATTEMPTED)!=0u;
 q->word&=~(WAKE_PENDING|WAKE_ATTEMPTED);
 if(!attempted){q->word|=WAKE_MISSING;return;}
 if(elapsed>INT32_MAX || elapsed<q->first_delta){q->word|=WAKE_BACKWARD;return;}
 if(q->first_delta>UINT32_MAX-q->first_us || elapsed>UINT32_MAX-q->accepted_us ||
    (q->word>>8u)==WAKE_COUNT){q->word|=WAKE_OVERFLOW;return;}
 q->first_us+=q->first_delta;q->accepted_us+=elapsed;q->word+=256u;
}
typedef struct {
 uint32_t span_us;volatile uint32_t clock_fallbacks;
 comp_completion_queue_t completion;comp_wake_retry_t retry;
} comp_v11_completion_profile_t;
_Static_assert(sizeof(comp_v11_completion_profile_t)==56u,"reuse original56B");
#define COMPLETION_PENDING 3u
#define COMPLETION_DUPLICATE 4u
#define COMPLETION_MISSING 8u
#define COMPLETION_OVERFLOW 16u
#define COMPLETION_BACKWARD 32u
/* Callers serialize queue state with a short incoming-mask-restoring critical section. */
static inline void comp_completion_enqueue(comp_completion_queue_t *q,unsigned lane,uint32_t now)
{
 if(lane<1u || lane>2u)return;
 uint32_t bit=1u<<(lane-1u);
 if(q->flags&bit){q->flags|=COMPLETION_DUPLICATE;return;}
 q->stamp[lane-1u]=now;q->flags|=bit;
}
static inline void comp_completion_dispatch(comp_completion_queue_t *q,unsigned lane,uint32_t now)
{
 if(lane<1u || lane>2u)return;
 uint32_t bit=1u<<(lane-1u);
 if(!(q->flags&bit)){q->flags|=COMPLETION_MISSING;return;}
 uint32_t elapsed=now-q->stamp[lane-1u];q->flags&=~bit;
 if(elapsed>INT32_MAX){q->flags|=COMPLETION_BACKWARD;return;}
 if(elapsed>UINT32_MAX-q->total_us || q->samples==UINT32_MAX) {
  q->flags|=COMPLETION_OVERFLOW;return;
 }
 q->total_us+=elapsed;++q->samples;
}
static inline void comp_completion_route_ready(comp_completion_route_slot_t *s,uint32_t now)
{
 if(!(route_load(&s->word)&ROUTE_PENDING)){s->since_us=now;(void)route_or(&s->word,ROUTE_PENDING);}
}
static inline void comp_completion_route_run(comp_completion_route_slot_t *s,uint32_t now)
{
 if(!(route_load(&s->word)&ROUTE_PENDING)){(void)route_or(&s->word,ROUTE_UNMARKED);return;}
 uint32_t since=s->since_us;(void)route_and(&s->word,~ROUTE_PENDING);
 uint32_t elapsed=now-since;
 if(elapsed>UINT32_MAX-s->total_us || (route_load(&s->word)&ROUTE_COUNT)==ROUTE_COUNT) {
  (void)route_or(&s->word,ROUTE_UNMARKED);return;
 }
 s->total_us+=elapsed;(void)route_add(&s->word,1u);
}
#endif
