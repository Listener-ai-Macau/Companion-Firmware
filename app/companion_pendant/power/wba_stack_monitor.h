#ifndef COMP_WBA_STACK_MONITOR_H
#define COMP_WBA_STACK_MONITOR_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#define COMP_WBA_STACK_PATTERN UINT32_C(0xA55A3CC3)
#define COMP_WBA_STACK_WARN_BYTES 1024u
typedef struct {
    uint32_t minimum_free_bytes;
    bool sampled, low_latched, guard_failed;
} comp_wba_stack_monitor_t;
/* The region is painted before any C code uses the main stack. Scan only in
 * an idle foreground slot; interrupts may still reduce the next observation.
 * Include MSP because reserving a stack frame need not write every byte. */
void comp_wba_stack_sample(comp_wba_stack_monitor_t *,
    const volatile uint32_t *bottom, size_t words, uint32_t msp_free_bytes);
#endif
