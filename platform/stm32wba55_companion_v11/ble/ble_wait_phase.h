#ifndef COMP_V11_WAIT_PHASE_H
#define COMP_V11_WAIT_PHASE_H
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
/* Four mutually exclusive states of the SAME resource gate. Reports are
 * matched by immutable raw-event pointer to the pinned SDK's actual0x13
 * consumer. Callback time is kept separate, not added to ready queue time.
 * The pointer is observed only; ownership stays with the original SDK. */
typedef struct {uint32_t key,stamp;} comp_wait_slot_t;
typedef struct {
 uint32_t span_us;volatile uint32_t clock_fallbacks;comp_wait_slot_t queue[2];
 uint32_t pair_us,before_us,queued_us,handler_us,after_us,gate_stamp,flags;
} comp_v11_wait_phase_t;
_Static_assert(sizeof(comp_v11_wait_phase_t)==52u,"52B+originalcallback4B=56B");
#define WAIT_GATE 1u
#define WAIT_SEEN 2u
#define WAIT_CALLBACK 16u
#define WAIT_MEASURING 32u
#define WAIT_REORDER 64u
#define WAIT_DUPLICATE 128u
#define WAIT_MISSING 256u
#define WAIT_OVERFLOW 512u
#define WAIT_BACKWARD 1024u
#define WAIT_MALFORMED 2048u
#define WAIT_UNBOUND 4096u
#define WAIT_STALE 8192u
#define WAIT_ERRORS UINT32_C(0x3fc0)
static inline unsigned wait_pending(const comp_v11_wait_phase_t*v){return (v->flags>>2u)&3u;}
static inline void wait_count(comp_v11_wait_phase_t*v,unsigned n){v->flags=(v->flags&~12u)|(n<<2u);}
static inline void wait_add(comp_v11_wait_phase_t*v,uint32_t*s,uint32_t n)
{if(n>UINT32_MAX-*s)v->flags|=WAIT_OVERFLOW;else *s+=n;}
static inline bool wait_delta(comp_v11_wait_phase_t*v,uint32_t now,uint32_t stamp,uint32_t*out)
{*out=now-stamp;if(*out>INT32_MAX){v->flags|=WAIT_BACKWARD;return false;}return true;}
static inline void wait_advance(comp_v11_wait_phase_t*v,uint32_t now)
{
 if(!(v->flags&WAIT_GATE))return;
 uint32_t dt;
 if(wait_delta(v,now,v->gate_stamp,&dt)){
  uint32_t*sum=(v->flags&WAIT_CALLBACK)?&v->handler_us:
   wait_pending(v)?&v->queued_us:(v->flags&WAIT_SEEN)?&v->after_us:&v->before_us;
  wait_add(v,sum,dt);
 }
 v->gate_stamp=now;
}
static inline void comp_wait_start(comp_v11_wait_phase_t*v,uint32_t now)
{
 comp_wait_slot_t q0=v->queue[0],q1=v->queue[1];uint32_t flags=v->flags;
 memset(v,0,sizeof(*v));v->queue[0]=q0;v->queue[1]=q1;
 v->flags=(flags&(12u|WAIT_CALLBACK|WAIT_ERRORS))|WAIT_MEASURING;
 if(flags&(WAIT_GATE|WAIT_CALLBACK))v->flags|=WAIT_STALE;
 v->span_us=now;
}
static inline void comp_wait_open(comp_v11_wait_phase_t*v,uint32_t now)
{
 if(v->flags&WAIT_GATE){v->flags|=WAIT_DUPLICATE;return;}
 v->flags=(v->flags&~WAIT_SEEN)|WAIT_GATE;v->gate_stamp=now;
}
static inline void comp_wait_close(comp_v11_wait_phase_t*v,uint32_t now)
{wait_advance(v,now);v->flags&=~(WAIT_GATE|WAIT_SEEN);}
static inline void comp_wait_end(comp_v11_wait_phase_t*v,uint32_t now)
{
 if(v->flags&(WAIT_GATE|WAIT_CALLBACK))v->flags|=WAIT_STALE;
 v->span_us=now-v->span_us;if(v->span_us>INT32_MAX)v->flags|=WAIT_BACKWARD;
 /* Window pending is immutable even as ordinary host dispatch continues. */
 v->flags=(v->flags&~(WAIT_MEASURING|UINT32_C(0x30000)))|((uint32_t)wait_pending(v)<<16u);
}
static inline void comp_wait_post(comp_v11_wait_phase_t*v,uint32_t key,uint32_t now)
{
 unsigned n=wait_pending(v);if(!key){v->flags|=WAIT_MALFORMED;return;}
 for(unsigned i=0u;i<n && i<2u;++i)if(v->queue[i].key==key){v->flags|=WAIT_DUPLICATE;return;}
 if(n>=2u){v->flags|=WAIT_OVERFLOW;return;}
 if(v->flags&WAIT_MEASURING)wait_advance(v,now);
 v->queue[n]=(comp_wait_slot_t){key,now};wait_count(v,n+1u);
}
static inline bool comp_wait_has(const comp_v11_wait_phase_t*v,uint32_t key)
{unsigned n=wait_pending(v);for(unsigned i=0u;i<n && i<2u;++i)if(v->queue[i].key==key)return true;return false;}
static inline void comp_wait_enter(comp_v11_wait_phase_t*v,uint32_t key,uint32_t now)
{
 if(v->flags&WAIT_CALLBACK){v->flags|=WAIT_DUPLICATE;return;}
 unsigned n=wait_pending(v);if(!n || v->queue[0].key!=key){v->flags|=comp_wait_has(v,key)?WAIT_REORDER:WAIT_MISSING;return;}
 if(v->flags&WAIT_MEASURING){uint32_t dt;wait_advance(v,now);
  if(wait_delta(v,now,v->queue[0].stamp,&dt))wait_add(v,&v->pair_us,dt);
 }
 v->flags|=WAIT_CALLBACK;
}
static inline void comp_wait_leave(comp_v11_wait_phase_t*v,uint32_t now)
{
 if(!(v->flags&WAIT_CALLBACK)){v->flags|=WAIT_MISSING;return;}
 if(v->flags&WAIT_MEASURING)wait_advance(v,now);
 unsigned n=wait_pending(v);if(!n){v->flags|=WAIT_MISSING;return;}
 v->queue[0]=v->queue[1];v->queue[1]=(comp_wait_slot_t){0};wait_count(v,n-1u);
 v->flags&=~WAIT_CALLBACK;if(v->flags&WAIT_GATE)v->flags|=WAIT_SEEN;
}
#endif
