#include "companion_opus_memory.h"
#include <string.h>

/* Keep the bounded word loops even under LTO; converting them back into a
 * variable-size libc call restores the measured nano byte-copy path. Constant
 * four-byte memcpy accesses preserve aliasing and never read beyond the span. */
#if defined(__GNUC__)
#define MEMORY_OP __attribute__((noinline,optimize("O3","no-tree-loop-distribute-patterns")))
#define MEMORY_INLINE static inline __attribute__((always_inline))
#elif defined(_MSC_VER)
#define MEMORY_OP __declspec(noinline)
#define MEMORY_INLINE static __forceinline
#else
#define MEMORY_OP
#define MEMORY_INLINE static inline
#endif

#if defined(COMPANION_WBA_CODEC_PROFILE) && COMPANION_WBA_CODEC_PROFILE
static companion_opus_memory_count_t counts[3]
#if defined(__GNUC__) && defined(__arm__)
    __attribute__((section(".sram1.bss"),aligned(8)))
#endif
    ;
#define NOTE(kind,n) do {++counts[kind].calls;counts[kind].bytes+=(n);}while(0)
const companion_opus_memory_count_t *companion_opus_memory_counts(void){return counts;}
#else
#define NOTE(kind,n) ((void)0)
#endif

MEMORY_INLINE uint32_t load_word(const unsigned char *src)
{uint32_t word;memcpy(&word,src,sizeof(word));return word;}
MEMORY_INLINE void store_word(unsigned char *dst,uint32_t word)
{memcpy(dst,&word,sizeof(word));}
MEMORY_INLINE void copy_words(unsigned char *dst,const unsigned char *src)
{
    /* Load the entire group before storing: move may overlap inside it. */
    uint32_t a=load_word(src),b=load_word(src+4),c=load_word(src+8),d=load_word(src+12);
    store_word(dst,a);store_word(dst+4,b);store_word(dst+8,c);store_word(dst+12,d);
}

MEMORY_INLINE void *copy_forward(void *dst,const void *src,size_t bytes)
{
    unsigned char *d=dst;const unsigned char *s=src;
    if(!bytes || d==s)return dst;
    if((((uintptr_t)d^(uintptr_t)s)&3u)==0u) {
        while(bytes && ((uintptr_t)d&3u)) {*d++=*s++;--bytes;}
        while(bytes>=16u) {copy_words(d,s);d+=16;s+=16;bytes-=16;}
        while(bytes>=4u) {store_word(d,load_word(s));d+=4;s+=4;bytes-=4;}
    }
    while(bytes) {*d++=*s++;--bytes;}
    return dst;
}

MEMORY_OP void *companion_opus_copy(void *dst,const void *src,size_t bytes)
{NOTE(0,bytes);return copy_forward(dst,src,bytes);}

MEMORY_OP void *companion_opus_move(void *dst,const void *src,size_t bytes)
{
    NOTE(1,bytes);
    unsigned char *d=dst;const unsigned char *s=src;
    if(!bytes || d==s)return dst;
    if((uintptr_t)d<(uintptr_t)s || (uintptr_t)d-(uintptr_t)s>=bytes)
        return copy_forward(dst,src,bytes);
    d+=bytes;s+=bytes;
    if((((uintptr_t)d^(uintptr_t)s)&3u)==0u) {
        while(bytes && ((uintptr_t)d&3u)) {*--d=*--s;--bytes;}
        while(bytes>=16u) {d-=16;s-=16;copy_words(d,s);bytes-=16;}
        while(bytes>=4u) {d-=4;s-=4;store_word(d,load_word(s));bytes-=4;}
    }
    while(bytes) {*--d=*--s;--bytes;}
    return dst;
}

MEMORY_OP void *companion_opus_clear(void *dst,size_t bytes)
{
    NOTE(2,bytes);
    unsigned char *d=dst;
    while(bytes && ((uintptr_t)d&3u)) {*d++=0;--bytes;}
    while(bytes>=16u) {store_word(d,0);store_word(d+4,0);store_word(d+8,0);store_word(d+12,0);d+=16;bytes-=16;}
    while(bytes>=4u) {store_word(d,0);d+=4;bytes-=4;}
    while(bytes) {*d++=0;--bytes;}
    return dst;
}
