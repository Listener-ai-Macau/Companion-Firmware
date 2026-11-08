#ifndef COMPANION_SPI_NOR_BLANK_CACHE_H
#define COMPANION_SPI_NOR_BLANK_CACHE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Volatile evidence only. Initialization/power loss discards it. A proof can
 * be produced only by contiguous successful FF readback of the entire range;
 * every overlapping program/erase invalidates it before issuing a command. */
typedef struct { uint32_t base,bytes,read_bytes,flags; } companion_nor_blank_cache_t;
enum { COMP_NOR_BLANK_READING=1u,COMP_NOR_BLANK_KNOWN=2u };
static inline bool companion_nor_blank_overlap(const companion_nor_blank_cache_t *c,
    uint32_t at,size_t bytes)
{
    if (!bytes || !c->bytes) return false;
    /* Subtractions avoid end-address overflow, including oversized callers. */
    return at>=c->base ? (uint64_t)(at-c->base)<c->bytes :
        (uint64_t)(c->base-at)<(uint64_t)bytes;
}
static inline bool companion_nor_blank_begin(companion_nor_blank_cache_t *c,
    uint32_t capacity,uint32_t base,uint32_t bytes)
{
    c->base=c->bytes=c->read_bytes=c->flags=0u;
    if (!bytes || base>capacity || bytes>capacity-base) return false;
    c->base=base;c->bytes=bytes;c->flags=COMP_NOR_BLANK_READING;return true;
}
static inline void companion_nor_blank_invalidate(companion_nor_blank_cache_t *c,
    uint32_t at,size_t bytes)
{ if (companion_nor_blank_overlap(c,at,bytes)) c->flags=0u; }
static inline void companion_nor_blank_observe(companion_nor_blank_cache_t *c,
    uint32_t at,const uint8_t *data,size_t bytes,bool successful)
{
    if (!(c->flags&COMP_NOR_BLANK_READING) || !companion_nor_blank_overlap(c,at,bytes)) return;
    if (!successful || !data || at<c->base || at-c->base!=c->read_bytes ||
        bytes>c->bytes-c->read_bytes) { c->flags=0u;return; }
    for (size_t i=0;i<bytes;++i) if (data[i]!=255u) { c->flags=0u;return; }
    c->read_bytes+=(uint32_t)bytes;
    if (c->read_bytes==c->bytes) c->flags=COMP_NOR_BLANK_KNOWN;
}
static inline bool companion_nor_blank_known(const companion_nor_blank_cache_t *c,
    uint32_t base,uint32_t bytes)
{
    return c->flags==COMP_NOR_BLANK_KNOWN && bytes && base>=c->base &&
        base-c->base<=c->bytes && bytes<=c->bytes-(base-c->base);
}
#endif
