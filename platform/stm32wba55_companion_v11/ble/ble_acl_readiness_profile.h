#ifndef COMP_V11_ACL_READINESS_PROFILE_H
#define COMP_V11_ACL_READINESS_PROFILE_H
#include <stdbool.h>
#include <stdint.h>
/* Only the public typed LL admission contract is observed. No descriptor
 * survives the original call. A 'same idle epoch' row proves that all pieces
 * were admitted without any intervening radio start, not that they were sent
 * or acknowledged. Unknown/active radio, rejection, truncation or a changed
 * epoch must never receive that qualification. No cross-clock subtraction.
 * The first16 split compact values at/after512KiB form a fixed sample, not a
 * sample selected after looking at RF. No audio, keys or payload is retained. */
#define ACL_READY_ROWS 16u
#define ACL_READY_COMPLETE 1u
#define ACL_READY_SAME_IDLE_EPOCH 2u
#define ACL_READY_REJECTED 4u
#define ACL_READY_INTERRUPTED 8u
#define ACL_READY_MALFORMED 16u
#define ACL_READY_SINGLE_EPOCH 32u
#define ACL_READY_EPOCH_OVERFLOW 64u
typedef struct {
 uint32_t offsets[ACL_READY_ROWS];
 uint8_t flags[ACL_READY_ROWS],parts[ACL_READY_ROWS];
 uint32_t pending_epoch,first_epoch;
 uint16_t remaining,pending_bytes;
 uint8_t count,errors;
 bool tracking,pending,pending_idle;
 uint8_t starts,continuations,unbounded;
} comp_acl_ready_t;
_Static_assert(sizeof(comp_acl_ready_t)<=116u,"bounded16row observation without per-row clocks");
/* This typed host-to-controller path uses a zero-initialized header and
 * populates buff_start, offset4, size<=251 and flags0/1, but leaves total_len
 * zero in the pinned official library. Bound the public slice by the actual
 * host LL buffer geometry; never read a descriptor after ownership transfer. */
static inline bool comp_acl_ready_slice_valid(const uint8_t *base,uint16_t offset,
 uint16_t bytes,uint16_t total_len)
{
 if(!base || offset!=4u || !bytes || bytes>251u)return false;
 return !total_len || (total_len>=offset && bytes<=total_len-offset);
}
static inline uint16_t acl_ready_u16(const uint8_t *d)
{return (uint16_t)d[0]|((uint16_t)d[1]<<8u);}
static inline uint32_t acl_ready_u32(const uint8_t *d)
{return (uint32_t)d[0]|((uint32_t)d[1]<<8u)|((uint32_t)d[2]<<16u)|((uint32_t)d[3]<<24u);}
static inline void acl_ready_error(comp_acl_ready_t *v)
{if(v->errors!=UINT8_MAX)++v->errors;}
static inline void comp_acl_ready_begin(comp_acl_ready_t *v,uint16_t h,uint16_t target,
 uint32_t recording_id,const uint8_t *d,uint16_t bytes,uint8_t flags,uint32_t epoch,bool idle)
{
 if(h!=target)return;
 if(v->count==ACL_READY_ROWS && !v->tracking)return;
 /* The pinned official LECTRL_SendAclDataToLL passes START=1 or CONT=0
  * to this typed ACL-only API. ACL_DATA_PCKT is not set here. Verified
  * against the actual linked official library, not inferred from its name. */
 if(flags&0xfeu){acl_ready_error(v);return;}
 uint8_t *counter=(flags&1u)?&v->starts:&v->continuations;
 if(*counter!=UINT8_MAX)++*counter;
 if(!d && v->unbounded!=UINT8_MAX)++v->unbounded;
 if(v->pending){acl_ready_error(v);v->flags[v->count-1u]|=ACL_READY_MALFORMED;return;}
 if(flags&1u){ /* BLE_BUFF_HDR_STRT_PKT in pinned official common_types.h */
  if(v->tracking){v->flags[v->count-1u]|=ACL_READY_INTERRUPTED;v->tracking=false;}
  if(v->count==ACL_READY_ROWS || !d || bytes<27u ||
     acl_ready_u16(d+2)!=4u || d[4]!=0x1bu || d[7]!=1u || d[8]!=8u ||
     acl_ready_u32(d+11)!=recording_id)return;
  const uint32_t total=(uint32_t)acl_ready_u16(d)+4u,payload=acl_ready_u16(d+9),offset=acl_ready_u32(d+19);
  if(offset<524288u || total!=payload+27u || total<bytes || total>UINT16_MAX)return;
  /* The observed 965-us path uses single 199-byte payloads. Store an
   * epoch delta in the existing parts byte, only while the whole sample is
   * this geometry. A split sample keeps the original fragment semantics. */
  const bool single=total==bytes && payload==199u;
  if(total==bytes && !single)return;
  if(v->count && (((v->flags[0]&ACL_READY_SINGLE_EPOCH)!=0u)!=single))return;
  unsigned index=v->count++;
  v->offsets[index]=offset;v->flags[index]=idle?ACL_READY_SAME_IDLE_EPOCH:0u;
  if(single) {
   if(index==0u)v->first_epoch=epoch;
   const uint32_t delta=epoch-v->first_epoch;
   v->flags[index]|=ACL_READY_SINGLE_EPOCH;
   if(delta>UINT8_MAX){v->flags[index]|=ACL_READY_EPOCH_OVERFLOW;v->parts[index]=UINT8_MAX;}
   else v->parts[index]=(uint8_t)delta;
  } else v->first_epoch=epoch;
  v->remaining=(uint16_t)total;v->tracking=true;
 }
 if(!v->tracking)return;
 unsigned index=v->count-1u;
 if(!d || !bytes || bytes>v->remaining){
  v->flags[index]|=ACL_READY_MALFORMED;v->tracking=false;acl_ready_error(v);return;
 }
 if(!idle || (!(v->flags[index]&ACL_READY_SINGLE_EPOCH) && epoch!=v->first_epoch))
  v->flags[index]&=(uint8_t)(UINT8_MAX^ACL_READY_SAME_IDLE_EPOCH);
 v->pending=true;v->pending_bytes=bytes;v->pending_epoch=epoch;v->pending_idle=idle;
}
static inline void comp_acl_ready_end(comp_acl_ready_t *v,bool success,uint32_t epoch,bool idle)
{
 if(!v->pending)return;
 unsigned index=v->count-1u;v->pending=false;
 if(!success){v->flags[index]|=ACL_READY_REJECTED;v->flags[index]&=(uint8_t)(UINT8_MAX^ACL_READY_SAME_IDLE_EPOCH);v->tracking=false;return;}
 if(!idle || !v->pending_idle || epoch!=v->pending_epoch ||
    (!(v->flags[index]&ACL_READY_SINGLE_EPOCH) && epoch!=v->first_epoch))
  v->flags[index]&=(uint8_t)(UINT8_MAX^ACL_READY_SAME_IDLE_EPOCH);
 if(!(v->flags[index]&ACL_READY_SINGLE_EPOCH))++v->parts[index];
 v->remaining-=v->pending_bytes;
 if(!v->remaining){v->flags[index]|=ACL_READY_COMPLETE;v->tracking=false;}
}
#endif
