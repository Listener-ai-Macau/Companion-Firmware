#ifndef COMPANION_CPU_SELF_LEDGER_H
#define COMPANION_CPU_SELF_LEDGER_H
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
/* Foreground-only nesting; caller already holds its observation critical
 * section. Inclusive IRQ/thread accounting remains separate and unchanged. */
typedef struct {uint32_t sequence,children_us;} comp_cpu_self_frame_t;
typedef struct {
    comp_cpu_self_frame_t frames[6];
    uint32_t depth,sequence,domain,invalid;
} comp_cpu_self_ledger_t;
_Static_assert(sizeof(comp_cpu_self_ledger_t)<=64u,"bounded observation nesting");
static inline void comp_cpu_self_reset(comp_cpu_self_ledger_t *s)
{
    uint32_t domain=s->domain+1u;if(!domain)domain=1u;
    memset(s,0,sizeof(*s));s->domain=domain;
}
static inline void comp_cpu_self_invalidate(comp_cpu_self_ledger_t *s)
{if(s->invalid!=UINT32_MAX)++s->invalid;s->depth=0u;}
static inline uint32_t comp_cpu_self_begin(comp_cpu_self_ledger_t *s)
{
    if(s->depth>=6u || s->sequence==UINT32_MAX){comp_cpu_self_invalidate(s);return 0u;}
    uint32_t sequence=++s->sequence;
    s->frames[s->depth++]=(comp_cpu_self_frame_t){sequence,0u};return sequence;
}
static inline bool comp_cpu_self_end(comp_cpu_self_ledger_t *s,uint32_t sequence,
    uint32_t thread_us,uint32_t *exclusive_us)
{
    if(!sequence || !s->depth || s->frames[s->depth-1u].sequence!=sequence ||
       s->frames[s->depth-1u].children_us>thread_us){comp_cpu_self_invalidate(s);return false;}
    uint32_t own=thread_us-s->frames[s->depth-1u].children_us;--s->depth;
    if(s->depth) {
        uint32_t *children=&s->frames[s->depth-1u].children_us;
        if(UINT32_MAX-*children<thread_us){comp_cpu_self_invalidate(s);return false;}
        *children+=thread_us;
    }
    *exclusive_us=own;return true;
}
static inline void comp_cpu_self_finish(comp_cpu_self_ledger_t *s)
{if(s->depth)comp_cpu_self_invalidate(s);}
#endif
