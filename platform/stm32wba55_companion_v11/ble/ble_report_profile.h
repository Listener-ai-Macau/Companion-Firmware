#ifndef COMP_V11_REPORT_PROFILE_H
#define COMP_V11_REPORT_PROFILE_H
#include <stdbool.h>
#include <stdint.h>
typedef struct {uint32_t key,stamp;} comp_report_slot_t;
typedef struct {
 uint32_t span_us;volatile uint32_t clock_fallbacks;comp_report_slot_t queue[2];
 uint32_t pair_us,pair_max_us,pair_samples,before_us,after_us,gate_stamp,flags;
} comp_v11_report_profile_t;
_Static_assert(sizeof(comp_v11_report_profile_t)==52u,"52B+originalcallback4B=56B");
#define REPORT_WAIT 1u
#define REPORT_SEEN 2u
#define REPORT_REORDER 64u
#define REPORT_DUPLICATE 128u
#define REPORT_MISSING 256u
#define REPORT_OVERFLOW 512u
#define REPORT_BACKWARD 1024u
#define REPORT_MALFORMED 2048u
#define REPORT_UNBOUND 4096u
#define REPORT_STALE 8192u
#define REPORT_ERRORS UINT32_C(0x3fc0)
static inline unsigned report_pending(const comp_v11_report_profile_t*v){return (v->flags>>2u)&3u;}
static inline unsigned report_peak(const comp_v11_report_profile_t*v){return (v->flags>>4u)&3u;}
static inline void report_count(comp_v11_report_profile_t*v,unsigned n){v->flags=(v->flags&~12u)|(n<<2u);}
static inline void report_add(comp_v11_report_profile_t*v,uint32_t*s,uint32_t n)
{if(n>UINT32_MAX-*s)v->flags|=REPORT_OVERFLOW;else *s+=n;}
static inline bool report_delta(comp_v11_report_profile_t*v,uint32_t now,uint32_t start,uint32_t*out)
{*out=now-start;if(*out>INT32_MAX){v->flags|=REPORT_BACKWARD;return false;}return true;}
static inline void comp_report_open(comp_v11_report_profile_t*v,uint32_t now)
{
 if(v->flags&REPORT_WAIT){v->flags|=REPORT_DUPLICATE;return;}
 v->flags=(v->flags&~REPORT_SEEN)|REPORT_WAIT;v->gate_stamp=now;
 if(report_pending(v))v->flags|=REPORT_SEEN; /* already prepared before gate */
}
static inline void comp_report_close(comp_v11_report_profile_t*v,uint32_t now)
{
 if(!(v->flags&REPORT_WAIT))return;uint32_t dt;
 if(report_delta(v,now,v->gate_stamp,&dt))report_add(v,(v->flags&REPORT_SEEN)?&v->after_us:&v->before_us,dt);
 v->flags&=~(REPORT_WAIT|REPORT_SEEN);
}
static inline void comp_report_post(comp_v11_report_profile_t*v,uint32_t key,uint32_t now)
{
 if(!key){v->flags|=REPORT_MALFORMED;return;}
 unsigned n=report_pending(v);
 for(unsigned i=0;i<n && i<2u;++i)if(v->queue[i].key==key){v->flags|=REPORT_DUPLICATE;return;}
 if(n>=2u){v->flags|=REPORT_OVERFLOW;return;}
 uint32_t dt;
 if((v->flags&REPORT_WAIT) && !(v->flags&REPORT_SEEN)){
  if(report_delta(v,now,v->gate_stamp,&dt))report_add(v,&v->before_us,dt);
  v->gate_stamp=now;v->flags|=REPORT_SEEN;
 }
 v->queue[n]=(comp_report_slot_t){key,now};report_count(v,n+1u);
 if(n+1u>report_peak(v))v->flags=(v->flags&~48u)|((n+1u)<<4u);
}
static inline bool comp_report_has(const comp_v11_report_profile_t*v,uint32_t key)
{unsigned n=report_pending(v);for(unsigned i=0;i<n && i<2u;++i)if(v->queue[i].key==key)return true;return false;}
static inline void comp_report_consume(comp_v11_report_profile_t*v,uint32_t key,uint32_t now)
{
 unsigned n=report_pending(v),i=0u;
 while(i<n && i<2u && v->queue[i].key!=key)++i;
 if(i>=n || i>=2u){v->flags|=REPORT_MISSING;return;}
 if(i)v->flags|=REPORT_REORDER;
 uint32_t dt;
 if(report_delta(v,now,v->queue[i].stamp,&dt)){
  report_add(v,&v->pair_us,dt);report_add(v,&v->pair_samples,1u);
  if(dt>v->pair_max_us)v->pair_max_us=dt;
 }
 if(i==0u)v->queue[0]=v->queue[1];report_count(v,n-1u);
}
#endif
