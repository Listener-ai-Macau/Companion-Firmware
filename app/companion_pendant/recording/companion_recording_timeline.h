#ifndef COMPANION_RECORDING_TIMELINE_H
#define COMPANION_RECORDING_TIMELINE_H

#include "companion_recording_wire.h"

/* COP1 schema2 keeps the existing40B Opus packets. At a packet boundary,
 * FF is padding and 0000 introduces this32B event. Events start at a248B
 * media-page boundary and never straddle pages. Audio CRC/SHA includes all
 * events/padding; neither contributes samples or synthesized silence.
 * Schema1 is unchanged. Old readers reject schema2; the product must not
 * enable this format until its actual receiver/control path supports it.
 * elapsed_ms is accumulated monotonic time since capture START, not audio
 * duration or host arrival time. A recovered unmatched PAUSE is an explicit
 * interrupted interval with an unknown end, never an invented duration. */
#define COMP_REC_TIMELINE_BYTES 32u
#define COMP_REC_TIMELINE_SCHEMA 2u
#define COMP_REC_BOOKMARK_SCHEMA 3u
#define COMP_REC_CODEC_BOUNDARY_SCHEMA 4u
#define COMP_REC_TIMELINE_PAUSE 1u
#define COMP_REC_TIMELINE_RESUME 2u
#define COMP_REC_TIMELINE_END_PAUSED 3u
#define COMP_REC_TIMELINE_BOOKMARK 4u
#define COMP_REC_BOOKMARK_LIMIT 1024u

typedef struct {
    uint64_t sample_offset,elapsed_ms;
    uint32_t sequence;
    uint8_t kind;
} comp_rec_timeline_event_t;

static inline bool comp_rec_timeline_encode(const comp_rec_timeline_event_t *e,uint8_t p[32])
{
    if(!e||!p||!e->sequence||e->sample_offset%320u||
       e->kind<COMP_REC_TIMELINE_PAUSE||e->kind>COMP_REC_TIMELINE_BOOKMARK||
       (e->kind==COMP_REC_TIMELINE_BOOKMARK&&e->sequence>COMP_REC_BOOKMARK_LIMIT))return false;
    memset(p,0,32u);memcpy(p+2u,"CPG1",4u);p[6]=e->kind;
    comp_rec_put32(p+8u,e->sequence);comp_rec_put64(p+12u,e->sample_offset);
    comp_rec_put64(p+20u,e->elapsed_ms);comp_rec_put32(p+28u,comp_rec_crc(p,28u));
    return true;
}
static inline bool comp_rec_timeline_decode(const uint8_t *p,size_t n,comp_rec_timeline_event_t *e)
{
    if(!p||!e||n<32u||p[0]||p[1]||memcmp(p+2u,"CPG1",4u)||p[7]||
       p[6]<COMP_REC_TIMELINE_PAUSE||p[6]>COMP_REC_TIMELINE_BOOKMARK||
       !comp_rec_get32(p+8u)||(p[6]==COMP_REC_TIMELINE_BOOKMARK&&comp_rec_get32(p+8u)>COMP_REC_BOOKMARK_LIMIT)||comp_rec_get64(p+12u)%320u||
       comp_rec_get32(p+28u)!=comp_rec_crc(p,28u))return false;
    e->kind=p[6];e->sequence=comp_rec_get32(p+8u);
    e->sample_offset=comp_rec_get64(p+12u);e->elapsed_ms=comp_rec_get64(p+20u);
    return true;
}

/* Schema4 separates the encoded320-sample packet axis from valid source PCM.
 * Each segment carries CONFIG immediately after its12B header. END precedes
 * the final drain packet: a live decoder learns the exact source ceiling
 * before it could publish padding. Its declared encoded end may be completed
 * by the successor segment at an exact rollover; a declaration alone never
 * proves a normal complete recording. CRC and the segmentSHA cover both.
 * CPG1 pause/mark offsets remain accepted source packet boundaries.
 * Unknown/reset prefixes have no invented valid source end. */
#define COMP_REC_CODEC_BOUNDARY_BYTES 32u
#define COMP_REC_CODEC_CONFIG 1u
#define COMP_REC_CODEC_END 2u
typedef struct {
    uint64_t encoded_samples,valid_source_samples;
    uint32_t delay_samples;
    uint8_t kind;
} comp_rec_codec_boundary_t;
static inline bool comp_rec_codec_boundary_valid(const comp_rec_codec_boundary_t *e)
{
    if(!e || e->delay_samples>160u || e->encoded_samples%320u)return false;
    if(e->kind==COMP_REC_CODEC_CONFIG)return e->valid_source_samples==UINT64_MAX;
    if(e->kind!=COMP_REC_CODEC_END || !e->valid_source_samples ||
       e->valid_source_samples%160u || e->valid_source_samples>e->encoded_samples)
        return false;
    uint64_t tail=e->encoded_samples-e->valid_source_samples;
    return tail>=e->delay_samples && tail-e->delay_samples<320u;
}
static inline bool comp_rec_codec_boundary_encode(const comp_rec_codec_boundary_t *e,uint8_t p[32])
{
    if(!p || !comp_rec_codec_boundary_valid(e))return false;
    memset(p,0,32u);memcpy(p+2u,"CDB1",4u);p[6]=e->kind;
    comp_rec_put32(p+8u,e->delay_samples);comp_rec_put64(p+12u,e->encoded_samples);
    comp_rec_put64(p+20u,e->valid_source_samples);comp_rec_put32(p+28u,comp_rec_crc(p,28u));
    return true;
}
static inline bool comp_rec_codec_boundary_decode(const uint8_t *p,size_t n,comp_rec_codec_boundary_t *e)
{
    if(!p || !e || n<32u || p[0] || p[1] || p[7] ||
       memcmp(p+2u,"CDB1",4u) || comp_rec_get32(p+28u)!=comp_rec_crc(p,28u))return false;
    comp_rec_codec_boundary_t value={comp_rec_get64(p+12u),comp_rec_get64(p+20u),
        comp_rec_get32(p+8u),p[6]};
    if(!comp_rec_codec_boundary_valid(&value))return false;
    *e=value;return true;
}
#endif
