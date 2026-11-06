#ifndef COMP_V11_MEMORY_TARGET_H
#define COMP_V11_MEMORY_TARGET_H
#include "wba_stack_monitor.h"
typedef struct {
    uint32_t stack_reserved_bytes, static_gap_bytes;
    comp_wba_stack_monitor_t stack;
} comp_v11_memory_stats_t;
/* O(stack size), call only outside capture/playback, at diagnostic cadence. */
void comp_v11_memory_sample(comp_v11_memory_stats_t *);
/* One sticky runtime monitor shared by UART and encrypted diagnostics.
 * Same idle-only sampling restriction; no second monitor/allocation. */
const comp_v11_memory_stats_t *comp_v11_memory_observe(void);
#endif
