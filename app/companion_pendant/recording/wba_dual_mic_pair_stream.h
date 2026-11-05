#ifndef COMPANION_WBA_DUAL_MIC_PAIR_STREAM_H
#define COMPANION_WBA_DUAL_MIC_PAIR_STREAM_H

/* Finite engineering source, not a new production recording codec. Caller
 * owns the queue and a sufficiently fast storage/transport port. All calls
 * are from one foreground task. No I/O, heap, ISR work or implicit retry.
 * Acknowledgement is legal only after the selected packet has been accepted
 * by the caller's actual sink. This module does NOT acquire NOR ownership or
 * make115200 UART capable of carrying continuous stereo PCM.
 *
 * Feed only verified, accepted10ms PDM pairs, before beamforming. The caller
 * supplies the REAL source sample position and invalidates on capture faults;
 * numbering callbacks consecutively is not proof that DMA was continuous.
 * Finish after the actual capture/finite observation window has ended and its
 * counters have been checked. A bad source is retained as a failed prefix,
 * never silently padded, resampled, overwritten or published as clean audio.
 */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define COMP_DMIC_STREAM_HEADER_BYTES 80u
#define COMP_DMIC_STREAM_PACKET_BYTES 664u
#define COMP_DMIC_STREAM_END_BYTES 48u
#define COMP_DMIC_STREAM_BLOCK_FRAMES 160u
#define COMP_DMIC_STREAM_MAX_BLOCKS 6000u /* finite60s at16kHz */
#define COMP_DMIC_STREAM_FLAG_SYNTHETIC 1u
#define COMP_DMIC_STREAM_BAD_INPUT 1u
#define COMP_DMIC_STREAM_DISCONTINUITY 2u
#define COMP_DMIC_STREAM_OVERFLOW 4u
#define COMP_DMIC_STREAM_CAPTURE_FAULT 8u
#define COMP_DMIC_STREAM_EMPTY 16u

typedef struct {
    uint8_t header[COMP_DMIC_STREAM_HEADER_BYTES];
    uint8_t end[COMP_DMIC_STREAM_END_BYTES];
    uint8_t *queue; /* queue_slots * COMP_DMIC_STREAM_PACKET_BYTES */
    uint64_t first_sample;
    uint32_t blocks,limit,pcm_crc,clipped_left,clipped_right,faults;
    uint16_t queue_slots,head,tail,queued;
    uint8_t peek_kind; /*0 none,1 header,2 pair block,3 end*/
    bool initialized,closed,header_sent,end_sent;
} comp_dmic_stream_t;

static inline void comp_dmic_put16(uint8_t *p,uint16_t v)
{p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);}
static inline void comp_dmic_put32(uint8_t *p,uint32_t v)
{for(unsigned i=0;i<4u;++i)p[i]=(uint8_t)(v>>(8u*i));}
static inline void comp_dmic_put64(uint8_t *p,uint64_t v)
{for(unsigned i=0;i<8u;++i)p[i]=(uint8_t)(v>>(8u*i));}
static inline uint32_t comp_dmic_crc(uint32_t previous,const uint8_t *p,size_t n)
{
    uint32_t crc=previous^UINT32_MAX;
    for(size_t i=0;i<n;++i){crc^=p[i];for(unsigned b=0;b<8u;++b)
        crc=(crc>>1)^(UINT32_C(0xEDB88320)&(0u-(crc&1u)));}
    return crc^UINT32_MAX;
}
static inline bool comp_dmic_nonzero(const uint8_t *p,size_t n)
{uint8_t any=0;for(size_t i=0;i<n;++i)any|=p[i];return any!=0;}

/* UID/source are the exact capture image identity, never the current mutable
 * worktree. synthetic is explicit and remains in-band through file export.
 * A new session discards only this caller-owned volatile queue. */
static inline bool comp_dmic_stream_begin(comp_dmic_stream_t *s,
    uint8_t *queue,uint16_t slots,const uint8_t uid[12],const uint8_t source[20],
    uint32_t recording_id,uint32_t token,uint64_t first_sample,
    uint32_t max_blocks,bool synthetic)
{
    if(!s)return false;
    memset(s,0,sizeof(*s));
    if(!queue||!slots||slots>32u||!uid||!source||!recording_id||!token||
       !comp_dmic_nonzero(uid,12u)||!comp_dmic_nonzero(source,20u)||
       !max_blocks||max_blocks>COMP_DMIC_STREAM_MAX_BLOCKS||
       first_sample>UINT64_MAX-(uint64_t)max_blocks*160u)return false;
    s->queue=queue;s->queue_slots=slots;s->limit=max_blocks;s->first_sample=first_sample;
    uint8_t *h=s->header;memcpy(h,"DMP1",4u);
    comp_dmic_put16(h+4u,1u);comp_dmic_put16(h+6u,80u);comp_dmic_put32(h+8u,16000u);
    comp_dmic_put16(h+12u,160u);h[14]=2u;h[15]=2u;
    memcpy(h+16u,uid,12u);memcpy(h+28u,source,20u);
    comp_dmic_put32(h+48u,token);comp_dmic_put32(h+52u,recording_id);
    comp_dmic_put64(h+56u,first_sample);comp_dmic_put32(h+64u,max_blocks);
    comp_dmic_put32(h+68u,synthetic?COMP_DMIC_STREAM_FLAG_SYNTHETIC:0u);
    comp_dmic_put32(h+76u,comp_dmic_crc(0u,h,76u));s->initialized=true;return true;
}
static inline void comp_dmic_stream_invalidate(comp_dmic_stream_t *s)
{if(s&&s->initialized&&!s->end_sent){s->faults|=COMP_DMIC_STREAM_CAPTURE_FAULT;s->closed=true;}}

/* A full finite window returns false without accepting further samples.
 * Backpressure BEFORE that limit is a sticky failure, never a drop-oldest
 * queue. Actual transport scheduling belongs outside this callback. */
static inline bool comp_dmic_stream_push(comp_dmic_stream_t *s,const int16_t *pairs,
    size_t frames,uint32_t rate,uint64_t source_first_sample)
{
    if(!s||!s->initialized||s->closed||s->faults)return false;
    if(s->blocks==s->limit)return false;
    if(!pairs||frames!=160u||rate!=16000u){s->faults|=COMP_DMIC_STREAM_BAD_INPUT;s->closed=true;return false;}
    if(source_first_sample!=s->first_sample+(uint64_t)s->blocks*160u){
        s->faults|=COMP_DMIC_STREAM_DISCONTINUITY;s->closed=true;return false;}
    if(s->queued==s->queue_slots){s->faults|=COMP_DMIC_STREAM_OVERFLOW;s->closed=true;return false;}
    uint8_t *p=s->queue+(size_t)s->tail*COMP_DMIC_STREAM_PACKET_BYTES;
    memcpy(p,"DMPF",4u);comp_dmic_put32(p+4u,s->blocks);
    comp_dmic_put64(p+8u,source_first_sample);comp_dmic_put16(p+16u,160u);comp_dmic_put16(p+18u,0u);
    for(size_t i=0;i<320u;++i){int16_t v=pairs[i];comp_dmic_put16(p+20u+2u*i,(uint16_t)v);
        if(v==INT16_MIN||v==INT16_MAX){if(i&1u)s->clipped_right++;else s->clipped_left++;}}
    comp_dmic_put32(p+660u,comp_dmic_crc(0u,p,660u));
    s->pcm_crc=comp_dmic_crc(s->pcm_crc,p+20u,640u);
    s->blocks++;s->tail=(uint16_t)((s->tail+1u)%s->queue_slots);s->queued++;return true;
}
static inline bool comp_dmic_stream_finish(comp_dmic_stream_t *s,bool actual_capture_ok)
{
    if(!s||!s->initialized||s->end_sent)return false;
    if(!actual_capture_ok)s->faults|=COMP_DMIC_STREAM_CAPTURE_FAULT;
    if(!s->blocks)s->faults|=COMP_DMIC_STREAM_EMPTY;
    s->closed=true;return s->faults==0u;
}
static inline bool comp_dmic_stream_peek(comp_dmic_stream_t *s,const uint8_t **bytes,size_t *count)
{
    if(!s||!s->initialized||!bytes||!count)return false;
    s->peek_kind=0u;
    if(!s->header_sent){*bytes=s->header;*count=80u;s->peek_kind=1u;return true;}
    if(s->queued){*bytes=s->queue+(size_t)s->head*664u;*count=664u;s->peek_kind=2u;return true;}
    if(!s->closed||s->end_sent)return false;
    uint8_t *e=s->end;memset(e,0,48u);memcpy(e,"DMPE",4u);comp_dmic_put32(e+4u,s->blocks);
    comp_dmic_put64(e+8u,(uint64_t)s->blocks*160u);comp_dmic_put32(e+16u,s->faults);
    comp_dmic_put32(e+20u,s->clipped_left);comp_dmic_put32(e+24u,s->clipped_right);
    comp_dmic_put32(e+28u,s->pcm_crc);memcpy(e+36u,s->header+76u,4u);
    comp_dmic_put32(e+44u,comp_dmic_crc(0u,e,44u));*bytes=e;*count=48u;s->peek_kind=3u;return true;
}
static inline bool comp_dmic_stream_consume(comp_dmic_stream_t *s)
{
    if(!s||!s->initialized)return false;
    if(s->peek_kind==1u)s->header_sent=true;
    else if(s->peek_kind==2u){s->head=(uint16_t)((s->head+1u)%s->queue_slots);s->queued--;}
    else if(s->peek_kind==3u)s->end_sent=true;
    else return false;
    s->peek_kind=0u;return true;
}
#endif
