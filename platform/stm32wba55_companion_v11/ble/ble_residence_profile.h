#ifndef COMP_V11_RESIDENCE_PROFILE_H
#define COMP_V11_RESIDENCE_PROFILE_H
#include <stdbool.h>
#include <stdint.h>
/* Nine timestamp positions: configured eight controller ACL buffers plus
 * one provisional public send whose original return is not known yet.
 * Units are the public LL admissions/completed-packet reports, NOT RF PDUs.
 * Aggregate packet residence overlaps concurrent packets and other work. */
typedef struct {
 uint32_t span_us;volatile uint32_t clock_fallbacks;
 uint32_t stamps[9],flags,handle,accepted,completed;
 uint32_t residence_us,residence_max_us,residence_samples,reports,radio_starts,radio_empty;
} comp_v11_residence_profile_t;
_Static_assert(sizeof(comp_v11_residence_profile_t)==84u,"replace52B route+32B gate");
#define RES_API (1u<<8)
#define RES_DRAINED (1u<<9)
#define RES_HANDLE (1u<<10)
#define RES_INVALID (1u<<11)
#define RES_OVERFLOW (1u<<12)
#define RES_BACKWARD (1u<<13)
#define RES_DUPLICATE (1u<<14)
#define RES_LINK_CHANGE (1u<<15)
#define RES_MALFORMED (1u<<16)
#define RES_UNBOUND (1u<<17)
#define RES_NO_BASELINE (1u<<18)
#define RES_MEASURING (1u<<19)
#define RES_RADIO_ON (1u<<20)
#define RES_RADIO_KNOWN (1u<<21)
#define RES_ERRORS UINT32_C(0x0007f800)
static inline unsigned residence_depth(const comp_v11_residence_profile_t*v){return v->flags&15u;}
static inline unsigned residence_head(const comp_v11_residence_profile_t*v){return (v->flags>>4u)&15u;}
static inline void residence_depth_set(comp_v11_residence_profile_t*v,unsigned n){v->flags=(v->flags&~15u)|n;}
static inline void residence_head_set(comp_v11_residence_profile_t*v,unsigned n){v->flags=(v->flags&~240u)|(n<<4u);}
static inline void residence_add(comp_v11_residence_profile_t*v,uint32_t*s,uint32_t n)
{if(n>UINT32_MAX-*s)v->flags|=RES_OVERFLOW;else *s+=n;}
static inline void comp_residence_start(comp_v11_residence_profile_t*v,uint32_t now)
{
 v->accepted=v->completed=v->residence_us=v->residence_max_us=v->residence_samples=v->reports=v->radio_starts=v->radio_empty=0u;
 v->clock_fallbacks=0u;v->span_us=now;
 v->handle=(v->handle&65535u)|((uint32_t)residence_depth(v)<<16u);
 if(!(v->flags&RES_HANDLE) || (v->flags&RES_API))v->flags|=RES_NO_BASELINE|RES_INVALID;
 v->flags|=RES_MEASURING;
}
static inline void comp_residence_end(comp_v11_residence_profile_t*v,uint32_t now)
{
 if(v->flags&RES_API)v->flags|=RES_INVALID;
 v->handle=(v->handle&UINT32_C(0x00ffffff))|((uint32_t)residence_depth(v)<<24u);
 v->span_us=now-v->span_us;if(v->span_us>INT32_MAX)v->flags|=RES_BACKWARD;
 v->flags&=~RES_MEASURING;
}
static inline void comp_residence_send_begin(comp_v11_residence_profile_t*v,uint16_t h,uint32_t now)
{
 if(!(v->flags&RES_HANDLE) || (v->handle&65535u)!=h){
  if((v->flags&RES_MEASURING) || residence_depth(v))v->flags|=RES_LINK_CHANGE|RES_INVALID;
  else v->flags&=~RES_ERRORS;
  v->handle=(v->handle&UINT32_C(0xffff0000))|h;
  v->flags=(v->flags&~(255u|RES_API|RES_DRAINED))|RES_HANDLE;
 }
 if(v->flags&RES_API){v->flags|=RES_DUPLICATE|RES_INVALID;return;}
 unsigned n=residence_depth(v),head=residence_head(v);
 if(n>=9u || head>=9u){v->flags|=RES_OVERFLOW|RES_INVALID;return;}
 v->stamps[(head+n)%9u]=now;residence_depth_set(v,n+1u);
 v->flags=(v->flags&~RES_DRAINED)|RES_API;
}
static inline void comp_residence_send_end(comp_v11_residence_profile_t*v,uint16_t h,bool success)
{
 if(!(v->flags&RES_API) || (v->handle&65535u)!=h){v->flags|=RES_DUPLICATE|RES_INVALID;return;}
 if(success){if(v->flags&RES_MEASURING)residence_add(v,&v->accepted,1u);}
 else if((v->flags&RES_DRAINED) || !residence_depth(v))v->flags|=RES_INVALID;
 else residence_depth_set(v,residence_depth(v)-1u);
 v->flags&=~(RES_API|RES_DRAINED);
}
static inline void comp_residence_completed(comp_v11_residence_profile_t*v,uint32_t n,uint32_t now,bool valid)
{
 unsigned depth=residence_depth(v),head=residence_head(v);
 if(!n && valid)return;
 if(!valid || !(v->flags&RES_HANDLE) || n>depth || head>=9u){v->flags|=RES_MALFORMED|RES_INVALID;return;}
 if(!n)return;
 if(v->flags&RES_MEASURING){residence_add(v,&v->completed,n);residence_add(v,&v->reports,1u);}
 if((v->flags&RES_API) && n==depth)v->flags|=RES_DRAINED;
 for(unsigned i=0u;i<n;++i){
  uint32_t stamp=v->stamps[head];
  if((v->flags&RES_MEASURING) && (int32_t)(stamp-v->span_us)>=0){
   uint32_t elapsed=now-stamp;
   if(elapsed>INT32_MAX)v->flags|=RES_BACKWARD;
   else {residence_add(v,&v->residence_us,elapsed);residence_add(v,&v->residence_samples,1u);
    if(elapsed>v->residence_max_us)v->residence_max_us=elapsed;}
  }
  head=(head+1u)%9u;
 }
 residence_head_set(v,head);residence_depth_set(v,depth-n);
}
static inline void comp_residence_radio(comp_v11_residence_profile_t*v,bool on)
{
 if(on && (v->flags&RES_MEASURING)){
  residence_add(v,&v->radio_starts,1u);
  if(!(v->flags&RES_API) && !residence_depth(v))residence_add(v,&v->radio_empty,1u);
 }
 v->flags=(v->flags&~RES_RADIO_ON)|RES_RADIO_KNOWN|(on?RES_RADIO_ON:0u);
}
static inline void comp_residence_disconnect(comp_v11_residence_profile_t*v,uint16_t h)
{
 if((v->flags&RES_HANDLE) && (v->handle&65535u)==h){
  if(v->flags&RES_MEASURING)v->flags|=RES_LINK_CHANGE|RES_INVALID;
  v->flags&=~(255u|RES_HANDLE|RES_API|RES_DRAINED);
 }
}
#endif
