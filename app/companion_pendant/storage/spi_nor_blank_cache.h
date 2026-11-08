#ifndef COMPANION_SPI_NOR_BLANK_CACHE_H
#define COMPANION_SPI_NOR_BLANK_CACHE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Volatile physical evidence only. Each bit requires all4096 bytes of that
 * sector to have been read successfully as FF. A dirty sector never proves
 * any bytes; scanning continues at the next sector. Every overlapping write
 * revokes affected sector proofs before the command, even if it later fails.
 * Initialization/probe clears flags. This grants no allocation/ownership. */
#define COMP_NOR_BLANK_SECTOR_BYTES 4096u
#define COMP_NOR_BLANK_SECTORS 96u
typedef struct {
    uint32_t base,bytes,read_bytes,flags;
    uint32_t known_sectors[3];
} companion_nor_blank_cache_t;
enum { COMP_NOR_BLANK_READING=1u,COMP_NOR_BLANK_KNOWN=2u }; /*2=scan finished, not whole-range proof*/
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
    for(unsigned i=0u;i<3u;++i)c->known_sectors[i]=0u;
    if (!bytes || base%4096u || bytes%4096u || bytes/4096u>COMP_NOR_BLANK_SECTORS ||
        base>capacity || bytes>capacity-base) return false;
    c->base=base;c->bytes=bytes;c->flags=COMP_NOR_BLANK_READING;return true;
}
static inline void companion_nor_blank_invalidate(companion_nor_blank_cache_t *c,
    uint32_t at,size_t bytes)
{
    if(!c->flags || !companion_nor_blank_overlap(c,at,bytes))return;
    uint64_t end=(uint64_t)at+(uint64_t)bytes;
    if(end<(uint64_t)at)end=UINT64_MAX;
    uint64_t limit=(uint64_t)c->base+c->bytes;
    if(end>limit)end=limit;
    uint32_t first=at>c->base?(at-c->base)/4096u:0u;
    uint32_t last=(uint32_t)((end-c->base-1u)/4096u);
    for(uint32_t i=first;i<=last;++i)c->known_sectors[i/32u]&=~(UINT32_C(1)<<(i%32u));
    /* An interrupted scan cannot complete a partly observed sector later. */
    if(c->flags==COMP_NOR_BLANK_READING)c->flags=COMP_NOR_BLANK_KNOWN;
}
static inline void companion_nor_blank_observe(companion_nor_blank_cache_t *c,
    uint32_t at,const uint8_t *data,size_t bytes,bool successful)
{
    if (c->flags!=COMP_NOR_BLANK_READING || !bytes || !companion_nor_blank_overlap(c,at,bytes)) return;
    if (!successful || !data || at<c->base || at-c->base!=c->read_bytes ||
        bytes>c->bytes-c->read_bytes || bytes>4096u-c->read_bytes%4096u) {
        c->flags=0u;return;
    }
    uint32_t sector=c->read_bytes/4096u;
    for (size_t i=0;i<bytes;++i) if (data[i]!=255u) {
        c->read_bytes=(sector+1u)*4096u;
        if(c->read_bytes==c->bytes)c->flags=COMP_NOR_BLANK_KNOWN;
        return;
    }
    c->read_bytes+=(uint32_t)bytes;
    if(c->read_bytes%4096u==0u)c->known_sectors[sector/32u]|=UINT32_C(1)<<(sector%32u);
    if (c->read_bytes==c->bytes) c->flags=COMP_NOR_BLANK_KNOWN;
}
static inline bool companion_nor_blank_known(const companion_nor_blank_cache_t *c,
    uint32_t base,uint32_t bytes)
{
    if(!c->flags || !bytes || base<c->base || base-c->base>c->bytes ||
       bytes>c->bytes-(base-c->base))return false;
    uint32_t first=(base-c->base)/4096u;
    uint32_t last=(base-c->base+bytes-1u)/4096u;
    for(uint32_t i=first;i<=last;++i)
        if(!(c->known_sectors[i/32u]&(UINT32_C(1)<<(i%32u))))return false;
    return true;
}
static inline uint32_t companion_nor_blank_count(const companion_nor_blank_cache_t *c)
{
    uint32_t count=0u;
    if(c->flags)for(unsigned i=0u;i<3u;++i)
        for(uint32_t bits=c->known_sectors[i];bits;bits&=bits-1u)++count;
    return count;
}
#endif
