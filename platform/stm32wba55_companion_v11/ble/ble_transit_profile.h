#ifndef COMP_V11_TRANSIT_PROFILE_H
#define COMP_V11_TRANSIT_PROFILE_H
#include <stdbool.h>
#include <stdint.h>
typedef struct {uint32_t link_generation,accepted_us,enqueued_us;} comp_transit_lane_t;
typedef struct {
 uint32_t span_us;volatile uint32_t clock_fallbacks;comp_transit_lane_t lane[2];
 uint32_t admission_us,admission_max_us,admission_samples,dispatch_us,dispatch_samples,flags;
} comp_v11_transit_profile_t;
_Static_assert(sizeof(comp_v11_transit_profile_t)==56u,"reuse original56B");
/* accepted[0:1], queued[2:3] are independent; a completed old packet may
 * wait for dispatch while a new packet is accepted on that same lane. */
#define TRANSIT_ACCEPTED 3u
#define TRANSIT_QUEUED 12u
#define TRANSIT_DUP_ACCEPT 16u
#define TRANSIT_MISSING_ACCEPT 32u
#define TRANSIT_DUP_QUEUE 64u
#define TRANSIT_MISSING_QUEUE 128u
#define TRANSIT_OVERFLOW 256u
#define TRANSIT_BACKWARD 512u
#define TRANSIT_STALE_LINK 1024u
#define TRANSIT_LOW 2047u
#define TRANSIT_PEAK_MASK UINT32_C(0x30000)
static inline unsigned comp_transit_peak(const comp_v11_transit_profile_t *v)
{return (v->flags>>16u)&3u;}
static inline uint32_t comp_transit_duplicates(const comp_v11_transit_profile_t *v)
{return v->flags>>18u;}
static inline bool comp_transit_lane(unsigned lane){return lane>=1u && lane<=2u;}
static inline bool comp_transit_link(comp_v11_transit_profile_t *v,unsigned i,uint32_t link)
{
 if(v->lane[i].link_generation==link)return true;
 v->flags=(v->flags&~((1u|4u)<<i))|TRANSIT_STALE_LINK;return false;
}
static inline void comp_transit_accept(comp_v11_transit_profile_t *v,unsigned lane,uint32_t link,uint32_t now)
{
 if(!comp_transit_lane(lane))return;unsigned i=lane-1u;uint32_t bit=1u<<i;
 if(v->flags&bit) {
  v->flags|=TRANSIT_DUP_ACCEPT;
  if(comp_transit_duplicates(v)==16383u)v->flags|=TRANSIT_OVERFLOW;
  else v->flags+=UINT32_C(0x40000);
  return;
 }
 if((v->flags&(4u<<i)) && !comp_transit_link(v,i,link))return;
 v->lane[i].link_generation=link;v->lane[i].accepted_us=now;v->flags|=bit;
 unsigned active=(v->flags&1u)+((v->flags>>1u)&1u);
 if(active>comp_transit_peak(v))v->flags=(v->flags&~TRANSIT_PEAK_MASK)|(active<<16u);
}
static inline void comp_transit_enqueue(comp_v11_transit_profile_t *v,unsigned lane,uint32_t link,uint32_t now)
{
 if(!comp_transit_lane(lane))return;unsigned i=lane-1u;uint32_t a=1u<<i,q=4u<<i;
 if(!(v->flags&a)){v->flags|=TRANSIT_MISSING_ACCEPT;return;}
 if(!comp_transit_link(v,i,link))return;
 uint32_t elapsed=now-v->lane[i].accepted_us;v->flags&=~a;
 if(elapsed>INT32_MAX){v->flags|=TRANSIT_BACKWARD;return;}
 if(elapsed>UINT32_MAX-v->admission_us || v->admission_samples==UINT32_MAX)v->flags|=TRANSIT_OVERFLOW;
 else {
  v->admission_us+=elapsed;++v->admission_samples;
  if(elapsed>v->admission_max_us)v->admission_max_us=elapsed;
 }
 if(v->flags&q){v->flags|=TRANSIT_DUP_QUEUE;return;}
 v->lane[i].enqueued_us=now;v->flags|=q;
}
static inline void comp_transit_dispatch(comp_v11_transit_profile_t *v,unsigned lane,uint32_t link,uint32_t now)
{
 if(!comp_transit_lane(lane))return;unsigned i=lane-1u;uint32_t q=4u<<i;
 if(!(v->flags&q)){v->flags|=TRANSIT_MISSING_QUEUE;return;}
 if(!comp_transit_link(v,i,link))return;
 uint32_t elapsed=now-v->lane[i].enqueued_us;v->flags&=~q;
 if(elapsed>INT32_MAX){v->flags|=TRANSIT_BACKWARD;return;}
 if(elapsed>UINT32_MAX-v->dispatch_us || v->dispatch_samples==UINT32_MAX)v->flags|=TRANSIT_OVERFLOW;
 else {v->dispatch_us+=elapsed;++v->dispatch_samples;}
}
#endif
