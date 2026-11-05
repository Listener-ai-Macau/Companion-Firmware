#ifndef COMPANION_DIAG_LOG_H
#define COMPANION_DIAG_LOG_H

#include "diag_log_events.h"

#include <stddef.h>
#include <stdint.h>

#ifndef COMP_DIAG_LOG_RING_CAPACITY
#define COMP_DIAG_LOG_RING_CAPACITY 128u
#endif

typedef uint32_t (*comp_diag_clock_fn_t)(void *context);

typedef struct {
    uint32_t sequence;
    uint32_t t_ms;
    uint8_t source;
    uint8_t event_id;
    uint8_t severity;
    uint8_t flags;
    uint32_t arg0;
    uint32_t arg1;
    uint32_t arg2;
    uint32_t arg3;
} comp_diag_event_t;

void comp_diag_log_init(void);
void comp_diag_log_clear(void);
void comp_diag_log_set_clock(comp_diag_clock_fn_t clock_fn, void *context);

void comp_diag_log_record(uint8_t source,
                          uint8_t event_id,
                          uint8_t severity,
                          uint32_t arg0,
                          uint32_t arg1,
                          uint32_t arg2,
                          uint32_t arg3);

void comp_diag_log_record_code(uint16_t event_code,
                               uint8_t severity,
                               uint32_t arg0,
                               uint32_t arg1,
                               uint32_t arg2,
                               uint32_t arg3);

size_t comp_diag_log_count(void);
size_t comp_diag_log_capacity(void);
size_t comp_diag_log_read_tail(comp_diag_event_t *out_events, size_t max_events);
size_t comp_diag_log_read_tail_by_source(uint8_t source,
                                         comp_diag_event_t *out_events,
                                         size_t max_events);

/* Cursor zero returns the newest bounded tail. A nonzero cursor returns the
 * oldest matching events with a sequence newer than the cursor. A zero mask
 * selects every value; source bits 0..7 select source IDs 1..8. */
size_t comp_diag_log_read_page(uint32_t cursor,
                               uint8_t source_mask,
                               uint16_t severity_mask,
                               comp_diag_event_t *out_events,
                               size_t max_events,
                               size_t *out_total_available);

const char *comp_diag_source_name(uint8_t source);
const char *comp_diag_severity_name(uint8_t severity);

#endif /* COMPANION_DIAG_LOG_H */
