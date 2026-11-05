#ifndef COMPANION_OPUS_MEMORY_H
#define COMPANION_OPUS_MEMORY_H
#include <stddef.h>
#include <stdint.h>
void *companion_opus_copy(void *dst,const void *src,size_t bytes);
void *companion_opus_move(void *dst,const void *src,size_t bytes);
void *companion_opus_clear(void *dst,size_t bytes);
#if defined(COMPANION_WBA_CODEC_PROFILE) && COMPANION_WBA_CODEC_PROFILE
typedef struct {uint64_t calls,bytes;} companion_opus_memory_count_t;
const companion_opus_memory_count_t *companion_opus_memory_counts(void);
#endif
#endif
