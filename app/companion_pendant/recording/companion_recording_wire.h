#ifndef COMPANION_RECORDING_WIRE_H
#define COMPANION_RECORDING_WIRE_H

/* Explicit little-endian codecs; no packed-struct or host-endian ABI.
 * V2 is a contract only. Do not advertise it before a durable format epoch,
 * session allocator, segmented journal and snapshot paging are implemented. */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define COMP_REC_V1_ENTRY_BYTES 32u
#define COMP_REC_V2_DESCRIPTOR_BYTES 112u
#define COMP_REC_V2_PAGE_HEADER_BYTES 24u
#define COMP_REC_V2_PAGE_ENTRIES 2u
#define COMP_REC_V2_MAX_SEGMENTS 1024u /* directory page count / legacy advertised value */
/* Descriptors use a 32-bit index and total; UINT32_MAX cannot be an index
 * because the terminal descriptor must store index + 1. */
#define COMP_REC_V2_INDEX_EXCLUSIVE_MAX UINT32_MAX
#define COMP_REC_V2_CAP_WIDE_SEGMENT_INDEX 1024u
#define COMP_REC_MAX_ENCODED_BYTES (64u * 1024u * 1024u)
#define COMP_REC_V2_SEALED 1u
#define COMP_REC_V2_LAST 2u
#define COMP_REC_V2_RECOVERED 4u
/* Bits3..5 are a durable terminal cause. Zero means old/unknown, never an
 * inferred user STOP. Only LAST may carry one; payload bytes stay unchanged. */
#define COMP_REC_V2_END_SHIFT 3u
#define COMP_REC_V2_END_MASK 56u
enum { COMP_REC_END_UNKNOWN=0,COMP_REC_END_USER,COMP_REC_END_FULL,
       COMP_REC_END_LIMIT,COMP_REC_END_LOW_BATTERY,COMP_REC_END_SILENCE };

typedef struct {
    uint32_t recording_id, started_unix_s, duration_ms, total_length, content_crc32;
    uint8_t codec, sync_state, source_mode, flags, sha256_prefix[8];
} comp_rec_v1_entry_t;

typedef struct {
    uint32_t recording_id, segment_index, encoded_length, content_crc32, total_segments;
    uint64_t format_epoch, session_id, sample_offset, sample_count;
    uint8_t sha256[32], flags, codec, source_mode, sync_state, device_uid[12];
} comp_rec_v2_descriptor_t;

typedef struct {
    uint32_t snapshot, nonce, start, total;
    uint8_t count;
    comp_rec_v2_descriptor_t entries[COMP_REC_V2_PAGE_ENTRIES];
} comp_rec_v2_page_t;

static inline void comp_rec_put16(uint8_t *p, uint16_t n)
{ p[0]=(uint8_t)n; p[1]=(uint8_t)(n>>8u); }
static inline void comp_rec_put32(uint8_t *p, uint32_t n)
{ for (size_t i=0u;i<4u;i++) p[i]=(uint8_t)(n>>(8u*i)); }
static inline void comp_rec_put64(uint8_t *p, uint64_t n)
{ for (size_t i=0u;i<8u;i++) p[i]=(uint8_t)(n>>(8u*i)); }
static inline uint32_t comp_rec_get32(const uint8_t *p)
{ return (uint32_t)p[0]|((uint32_t)p[1]<<8u)|((uint32_t)p[2]<<16u)|((uint32_t)p[3]<<24u); }
static inline uint64_t comp_rec_get64(const uint8_t *p)
{ return (uint64_t)comp_rec_get32(p)|((uint64_t)comp_rec_get32(p+4u)<<32u); }
static inline uint32_t comp_rec_crc_step(uint32_t crc, const uint8_t *p, size_t n)
{
    for (size_t i=0u;i<n;i++) {
        crc^=p[i];
        for (unsigned b=0u;b<8u;b++) crc=(crc>>1u)^((crc&1u)?UINT32_C(0xedb88320):0u);
    }
    return crc;
}
static inline uint32_t comp_rec_crc(const uint8_t *p, size_t n)
{ return ~comp_rec_crc_step(UINT32_MAX,p,n); }
static inline bool comp_rec_not_uniform(const uint8_t *p, size_t n, uint8_t value)
{
    for (size_t i=0u;i<n;i++) if (p[i]!=value) return true;
    return false;
}

static inline bool comp_rec_v1_encode(const comp_rec_v1_entry_t *e, uint8_t *p, size_t n)
{
    if (e==NULL || p==NULL || n<COMP_REC_V1_ENTRY_BYTES) return false;
    comp_rec_put32(p,e->recording_id); comp_rec_put32(p+4u,e->started_unix_s);
    comp_rec_put32(p+8u,e->duration_ms);
    p[12]=e->codec; p[13]=e->sync_state; p[14]=e->source_mode; p[15]=e->flags;
    comp_rec_put32(p+16u,e->total_length); memcpy(p+20u,e->sha256_prefix,8u);
    comp_rec_put32(p+28u,e->content_crc32);
    return true;
}

static inline bool comp_rec_v2_valid(const comp_rec_v2_descriptor_t *d)
{
    if (d==NULL || d->recording_id==0u || d->format_epoch==0u || d->session_id==0u ||
        d->segment_index>=COMP_REC_V2_INDEX_EXCLUSIVE_MAX || d->codec!=3u || d->source_mode>2u ||
        d->sync_state>2u || (d->flags&~63u) || (d->flags&COMP_REC_V2_SEALED)==0u ||
        (d->flags>>COMP_REC_V2_END_SHIFT)>COMP_REC_END_SILENCE ||
        ((d->flags&COMP_REC_V2_END_MASK) && !(d->flags&COMP_REC_V2_LAST)) ||
        d->encoded_length<15u || d->encoded_length>COMP_REC_MAX_ENCODED_BYTES ||
        d->sample_count==0u || d->sample_count%320u!=0u || d->sample_offset%320u!=0u ||
        d->sample_offset>UINT64_MAX-d->sample_count ||
        !comp_rec_not_uniform(d->device_uid,12u,0u) || !comp_rec_not_uniform(d->device_uid,12u,255u) ||
        !comp_rec_not_uniform(d->sha256,32u,0u)) return false;
    /* Each COP1 packet needs at least two length bytes and one payload byte. */
    if (d->sample_count/320u>(d->encoded_length-12u)/3u) return false;
    if ((d->flags&COMP_REC_V2_LAST)!=0u) {
        if (d->total_segments!=d->segment_index+1u) return false;
    } else if (d->total_segments!=0u) return false;
    return true;
}

static inline bool comp_rec_v2_encode(const comp_rec_v2_descriptor_t *d, uint8_t *p, size_t n)
{
    if (!comp_rec_v2_valid(d) || p==NULL || n<COMP_REC_V2_DESCRIPTOR_BYTES) return false;
    memset(p,0,COMP_REC_V2_DESCRIPTOR_BYTES); memcpy(p,"CRS2",4u);
    comp_rec_put16(p+4u,2u); comp_rec_put16(p+6u,COMP_REC_V2_DESCRIPTOR_BYTES);
    comp_rec_put32(p+8u,d->recording_id); comp_rec_put64(p+12u,d->format_epoch);
    comp_rec_put64(p+20u,d->session_id); comp_rec_put32(p+28u,d->segment_index);
    comp_rec_put64(p+32u,d->sample_offset); comp_rec_put64(p+40u,d->sample_count);
    comp_rec_put32(p+48u,d->encoded_length); comp_rec_put32(p+52u,d->content_crc32);
    memcpy(p+56u,d->sha256,32u); comp_rec_put32(p+88u,d->total_segments);
    p[92]=d->flags; p[93]=d->codec; p[94]=d->source_mode; p[95]=d->sync_state;
    memcpy(p+96u,d->device_uid,12u); comp_rec_put32(p+108u,comp_rec_crc(p,108u));
    return true;
}

static inline bool comp_rec_v2_decode(const uint8_t *p, size_t n, comp_rec_v2_descriptor_t *out)
{
    comp_rec_v2_descriptor_t d;
    if (p==NULL || out==NULL || n!=COMP_REC_V2_DESCRIPTOR_BYTES || memcmp(p,"CRS2",4u)!=0 ||
        p[4]!=2u || p[5]!=0u || p[6]!=COMP_REC_V2_DESCRIPTOR_BYTES || p[7]!=0u ||
        comp_rec_get32(p+108u)!=comp_rec_crc(p,108u)) return false;
    memset(&d,0,sizeof(d)); d.recording_id=comp_rec_get32(p+8u);
    d.format_epoch=comp_rec_get64(p+12u); d.session_id=comp_rec_get64(p+20u);
    d.segment_index=comp_rec_get32(p+28u); d.sample_offset=comp_rec_get64(p+32u);
    d.sample_count=comp_rec_get64(p+40u); d.encoded_length=comp_rec_get32(p+48u);
    d.content_crc32=comp_rec_get32(p+52u); memcpy(d.sha256,p+56u,32u);
    d.total_segments=comp_rec_get32(p+88u); d.flags=p[92]; d.codec=p[93];
    d.source_mode=p[94]; d.sync_state=p[95]; memcpy(d.device_uid,p+96u,12u);
    if (!comp_rec_v2_valid(&d)) return false;
    *out=d; return true;
}

static inline size_t comp_rec_v2_page_encode(uint32_t snapshot, uint32_t nonce,
    uint32_t start, uint32_t total, const comp_rec_v2_descriptor_t *entries,
    uint8_t count, uint8_t *p, size_t n)
{
    size_t bytes=COMP_REC_V2_PAGE_HEADER_BYTES+(size_t)count*COMP_REC_V2_DESCRIPTOR_BYTES;
    if (p==NULL || snapshot==0u || nonce==0u || total>COMP_REC_V2_MAX_SEGMENTS ||
        count>COMP_REC_V2_PAGE_ENTRIES || n<bytes || start>total || count>total-start ||
        (total!=0u && count==0u) || (count!=0u && entries==NULL)) return 0u;
    /* Check everything before mutating the caller's output. */
    for (uint8_t i=0u;i<count;i++) if (!comp_rec_v2_valid(&entries[i])) return 0u;
    memset(p,0,COMP_REC_V2_PAGE_HEADER_BYTES); p[0]=2u; p[1]=count;
    comp_rec_put16(p+2u,COMP_REC_V2_DESCRIPTOR_BYTES); comp_rec_put32(p+4u,snapshot);
    comp_rec_put32(p+8u,start); comp_rec_put32(p+12u,total); comp_rec_put32(p+16u,nonce);
    for (uint8_t i=0u;i<count;i++) {
        if (!comp_rec_v2_encode(&entries[i],p+COMP_REC_V2_PAGE_HEADER_BYTES+
            (size_t)i*COMP_REC_V2_DESCRIPTOR_BYTES,COMP_REC_V2_DESCRIPTOR_BYTES)) return 0u;
    }
    comp_rec_put32(p+20u,~comp_rec_crc_step(comp_rec_crc_step(UINT32_MAX,p,20u),
        p+COMP_REC_V2_PAGE_HEADER_BYTES,bytes-COMP_REC_V2_PAGE_HEADER_BYTES));
    return bytes;
}

static inline bool comp_rec_v2_page_decode(const uint8_t *p, size_t n, comp_rec_v2_page_t *out)
{
    comp_rec_v2_page_t page;
    if (p==NULL || out==NULL || n<COMP_REC_V2_PAGE_HEADER_BYTES || p[0]!=2u ||
        p[1]>COMP_REC_V2_PAGE_ENTRIES || p[2]!=COMP_REC_V2_DESCRIPTOR_BYTES || p[3]!=0u ||
        n!=COMP_REC_V2_PAGE_HEADER_BYTES+(size_t)p[1]*COMP_REC_V2_DESCRIPTOR_BYTES ||
        comp_rec_get32(p+20u)!=~comp_rec_crc_step(comp_rec_crc_step(UINT32_MAX,p,20u),
            p+COMP_REC_V2_PAGE_HEADER_BYTES,n-COMP_REC_V2_PAGE_HEADER_BYTES)) return false;
    memset(&page,0,sizeof(page)); page.snapshot=comp_rec_get32(p+4u);
    page.start=comp_rec_get32(p+8u); page.total=comp_rec_get32(p+12u);
    page.nonce=comp_rec_get32(p+16u); page.count=p[1];
    if (page.snapshot==0u || page.nonce==0u || page.total>COMP_REC_V2_MAX_SEGMENTS ||
        page.start>page.total || page.count>page.total-page.start ||
        (page.total!=0u && page.count==0u)) return false;
    for (uint8_t i=0u;i<page.count;i++) if (!comp_rec_v2_decode(
        p+COMP_REC_V2_PAGE_HEADER_BYTES+(size_t)i*COMP_REC_V2_DESCRIPTOR_BYTES,
        COMP_REC_V2_DESCRIPTOR_BYTES,&page.entries[i])) return false;
    *out=page; return true;
}
#endif
