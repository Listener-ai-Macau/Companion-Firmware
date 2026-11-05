#ifndef COMP_V11_PIPE_PROFILE_H
#define COMP_V11_PIPE_PROFILE_H
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
typedef struct {
 uint32_t span_us;volatile uint32_t clock_fallbacks;
 uint32_t depth,handle,accepted,radio_starts,queued_sum,zero_starts;
 uint32_t radio_us,radio_stamp,completed,window_depths,flags;
} comp_v11_pipe_profile_t;
_Static_assert(sizeof(comp_v11_pipe_profile_t)==52u,"52B+originalHCIcallback4B=56B");
#define PIPE_ON 1u
#define PIPE_HANDLE 2u
#define PIPE_LIVE_INVALID 4u
#define PIPE_CLIPPED 8u
#define PIPE_RADIO_KNOWN 16u
#define PIPE_IN_API 32u
#define PIPE_DUP 64u
#define PIPE_LINK_CHANGE 128u
#define PIPE_OVERFLOW 256u
#define PIPE_UNDERFLOW 512u
#define PIPE_BACKWARD 1024u
#define PIPE_MALFORMED 2048u
#define PIPE_UNBOUND 4096u
#define PIPE_NO_BASELINE 8192u
#define PIPE_ERRORS UINT32_C(0x3fc4)
static inline unsigned pipe_peak(const comp_v11_pipe_profile_t*v){return (v->flags>>16u)&255u;}
static inline unsigned pipe_skipped(const comp_v11_pipe_profile_t*v){return v->flags>>24u;}
static inline void pipe_add(comp_v11_pipe_profile_t*v,uint32_t*s,uint32_t n)
{if(n>UINT32_MAX-*s)v->flags|=PIPE_OVERFLOW;else *s+=n;}
static inline bool pipe_delta(comp_v11_pipe_profile_t*v,uint32_t now,uint32_t start,uint32_t*out)
{*out=now-start;if(*out>INT32_MAX){v->flags|=PIPE_BACKWARD;return false;}return true;}
static inline void comp_pipe_begin(comp_v11_pipe_profile_t*v,uint32_t now)
{
 uint32_t depth=v->depth,handle=v->handle,keep=v->flags&(PIPE_ON|PIPE_HANDLE|PIPE_LIVE_INVALID|PIPE_RADIO_KNOWN|PIPE_IN_API);
 memset(v,0,sizeof(*v));v->depth=depth;v->handle=handle;v->flags=keep;v->span_us=now;
 if(!(keep&PIPE_HANDLE) || (keep&(PIPE_IN_API|PIPE_LIVE_INVALID)))v->flags|=PIPE_LIVE_INVALID|PIPE_NO_BASELINE;
 if(depth>255u)v->flags|=PIPE_OVERFLOW;
 else {v->window_depths=depth;v->flags|=depth<<16u;}
 if(keep&PIPE_ON){v->radio_stamp=now;v->flags|=PIPE_CLIPPED;}
}
static inline void comp_pipe_end(comp_v11_pipe_profile_t*v,uint32_t now)
{
 uint32_t dt;
 if(v->flags&PIPE_ON){if(pipe_delta(v,now,v->radio_stamp,&dt))pipe_add(v,&v->radio_us,dt);v->flags|=PIPE_CLIPPED;}
 if(v->depth>255u)v->flags|=PIPE_OVERFLOW;
 v->window_depths|=(v->depth&255u)<<8u;
 if(v->flags&PIPE_IN_API)v->flags|=PIPE_LIVE_INVALID;
 v->span_us=now-v->span_us;if(v->span_us>INT32_MAX)v->flags|=PIPE_BACKWARD;
 v->window_depths|=(v->flags&65535u)<<16u; /* immutable window-end flags */
}
static inline void comp_pipe_send_begin(comp_v11_pipe_profile_t*v,uint16_t h,bool active)
{
 if(!(v->flags&PIPE_HANDLE)){
  v->handle=h;v->depth=0u;v->flags=(v->flags&~PIPE_LIVE_INVALID)|PIPE_HANDLE;
 }else if(v->handle!=h){
  if(active || v->depth)v->flags|=PIPE_LINK_CHANGE|PIPE_LIVE_INVALID;
  v->handle=h;v->depth=0u;
 }
 if(v->flags&PIPE_IN_API)v->flags|=PIPE_DUP|PIPE_LIVE_INVALID;
 v->flags|=PIPE_IN_API;if(v->depth==UINT32_MAX)v->flags|=PIPE_LIVE_INVALID;pipe_add(v,&v->depth,1u); /* provisional, excluded from feed snapshots */
}
static inline void comp_pipe_send_end(comp_v11_pipe_profile_t*v,uint16_t h,bool success,bool active)
{
 if(!(v->flags&PIPE_IN_API) || v->handle!=h)v->flags|=PIPE_DUP|PIPE_LIVE_INVALID;
 if(!success){if(v->depth)--v->depth;else v->flags|=PIPE_UNDERFLOW|PIPE_LIVE_INVALID;}
 else if(active){
  pipe_add(v,&v->accepted,1u);
  if(v->depth>255u)v->flags|=PIPE_OVERFLOW;
  else if(v->depth>pipe_peak(v))v->flags=(v->flags&~UINT32_C(0xff0000))|(v->depth<<16u);
 }
 v->flags&=~PIPE_IN_API;
}
static inline void comp_pipe_complete(comp_v11_pipe_profile_t*v,uint32_t n,bool active)
{
 if(!(v->flags&PIPE_HANDLE) || n>v->depth)v->flags|=PIPE_UNDERFLOW|PIPE_LIVE_INVALID;
 else v->depth-=n;
 if(active)pipe_add(v,&v->completed,n);
}
static inline void comp_pipe_disconnect(comp_v11_pipe_profile_t*v,uint16_t h,bool active)
{
 if((v->flags&PIPE_HANDLE) && v->handle==h){
  if(active)v->flags|=PIPE_LINK_CHANGE|PIPE_LIVE_INVALID;
  else v->flags&=~(PIPE_LIVE_INVALID|PIPE_DUP|PIPE_UNDERFLOW|PIPE_LINK_CHANGE);
  v->flags&=~(PIPE_HANDLE|PIPE_IN_API);v->depth=0u;
 }
}
static inline void comp_pipe_radio(comp_v11_pipe_profile_t*v,uint32_t now,bool on,bool active,bool ci6)
{
 if(on){
  if((v->flags&(PIPE_ON|PIPE_RADIO_KNOWN))==(PIPE_ON|PIPE_RADIO_KNOWN) && active)v->flags|=PIPE_DUP;
  v->flags|=PIPE_ON|PIPE_RADIO_KNOWN;
  if(active){
   v->radio_stamp=now;pipe_add(v,&v->radio_starts,1u);
   if(!ci6 || (v->flags&PIPE_IN_API) || !(v->flags&PIPE_HANDLE) || (v->flags&PIPE_LIVE_INVALID)){
    if(pipe_skipped(v)==255u)v->flags|=PIPE_OVERFLOW;else v->flags+=UINT32_C(0x1000000);
   }else{pipe_add(v,&v->queued_sum,v->depth);if(!v->depth)pipe_add(v,&v->zero_starts,1u);}
  }
 }else{
  if(active){
   uint32_t dt;
   if(!(v->flags&PIPE_ON))v->flags|=PIPE_DUP;
   else if(pipe_delta(v,now,v->radio_stamp,&dt))pipe_add(v,&v->radio_us,dt);
  }
  v->flags=(v->flags&~PIPE_ON)|PIPE_RADIO_KNOWN;
 }
}
#endif
