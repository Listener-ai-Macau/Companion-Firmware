#ifndef COMP_V11_CREDIT_PROFILE_H
#define COMP_V11_CREDIT_PROFILE_H
#include <stdbool.h>
#include <stdint.h>
typedef struct {
 uint32_t span_us;volatile uint32_t clock_fallbacks;
 uint32_t events,packets,run_us,run_max_us,before_us,after_us;
 uint32_t gate_stamp,gap_us,last_completion_stamp,pool_us,pool_samples,flags;
} comp_v11_credit_profile_t;
_Static_assert(sizeof(comp_v11_credit_profile_t)==56u,"same56B");
#define CREDIT_WAIT 1u
#define CREDIT_SEEN 2u
#define CREDIT_CALLBACK 4u
#define CREDIT_STAMP 8u
#define CREDIT_OVERFLOW 16u
#define CREDIT_BACKWARD 32u
#define CREDIT_DUPLICATE 64u
#define CREDIT_MALFORMED 128u
#define CREDIT_STALE 256u
#define CREDIT_ERRORS (CREDIT_OVERFLOW|CREDIT_BACKWARD|CREDIT_DUPLICATE|CREDIT_MALFORMED|CREDIT_STALE)
static inline void credit_add(comp_v11_credit_profile_t*v,uint32_t *sum,uint32_t n)
{if(n>UINT32_MAX-*sum)v->flags|=CREDIT_OVERFLOW;else *sum+=n;}
static inline bool credit_delta(comp_v11_credit_profile_t*v,uint32_t now,uint32_t start,uint32_t*out)
{*out=now-start;if(*out>INT32_MAX){v->flags|=CREDIT_BACKWARD;return false;}return true;}
static inline void comp_credit_open(comp_v11_credit_profile_t*v,uint32_t now)
{
 if(v->flags&CREDIT_WAIT){v->flags|=CREDIT_DUPLICATE;return;}
 v->flags=(v->flags&~(CREDIT_SEEN|CREDIT_STAMP))|CREDIT_WAIT;v->gate_stamp=now;
}
static inline void comp_credit_close(comp_v11_credit_profile_t*v,uint32_t now)
{
 if(!(v->flags&CREDIT_WAIT))return;uint32_t dt;
 if(credit_delta(v,now,v->gate_stamp,&dt))credit_add(v,(v->flags&CREDIT_SEEN)?&v->after_us:&v->before_us,dt);
 v->flags&=~(CREDIT_WAIT|CREDIT_SEEN);
}
static inline void comp_credit_begin(comp_v11_credit_profile_t*v,uint32_t now,uint32_t packets)
{
 if(v->flags&CREDIT_CALLBACK){v->flags|=CREDIT_DUPLICATE;return;}
 uint32_t dt;
 if((v->flags&CREDIT_WAIT) && !(v->flags&CREDIT_SEEN)){
  if(credit_delta(v,now,v->gate_stamp,&dt))credit_add(v,&v->before_us,dt);
  v->gate_stamp=now;v->flags|=CREDIT_SEEN;
 }
 if(v->events && credit_delta(v,now,v->last_completion_stamp,&dt))credit_add(v,&v->gap_us,dt);
 v->last_completion_stamp=now;v->flags|=CREDIT_CALLBACK|CREDIT_STAMP;
 credit_add(v,&v->events,1u);credit_add(v,&v->packets,packets);
}
static inline void comp_credit_end(comp_v11_credit_profile_t*v,uint32_t now)
{
 if(!(v->flags&CREDIT_CALLBACK))return;uint32_t dt;
 if(credit_delta(v,now,v->last_completion_stamp,&dt)){
  credit_add(v,&v->run_us,dt);if(dt>v->run_max_us)v->run_max_us=dt;
 }
 v->flags&=~CREDIT_CALLBACK;
}
static inline void comp_credit_pool(comp_v11_credit_profile_t*v,uint32_t now)
{
 if((v->flags&(CREDIT_WAIT|CREDIT_SEEN|CREDIT_STAMP))!=(CREDIT_WAIT|CREDIT_SEEN|CREDIT_STAMP))return;
 uint32_t dt;if(credit_delta(v,now,v->last_completion_stamp,&dt)){
  credit_add(v,&v->pool_us,dt);credit_add(v,&v->pool_samples,1u);
 }
 v->flags&=~CREDIT_STAMP;
}
/* Actual pinned ll_cb layout: event code, parameter length, handle count,
 * all 16-bit handles, then all 16-bit completed counts. Do not use a
 * guessed C prototype for the private callback: assembly preserves ABI. */
static inline bool comp_credit_packet_count(const uint8_t *p,uint16_t current,uint32_t *count)
{
 *count=0u;if(!p || p[0]!=0x13u || p[2]>63u || p[1]!=(uint8_t)(1u+4u*p[2]))return false;
 for(unsigned i=0;i<p[2];++i){
  unsigned h=3u+2u*i,c=3u+2u*p[2]+2u*i;
  uint16_t handle=(uint16_t)((uint16_t)p[h]|((uint16_t)p[h+1u]<<8u));
  if((handle&0x0fffu)==current)*count+=(uint32_t)p[c]|((uint32_t)p[c+1u]<<8u);
 }
 return true;
}
#endif
