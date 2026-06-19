#include "diag_log.h"

#include <stdbool.h>
#include <string.h>

typedef struct {
    uint8_t id;
    const char *name;
} comp_diag_source_def_t;

static const comp_diag_source_def_t k_sources[] = {
#define COMP_DIAG_SOURCE_DEF(symbol, value, name) {(uint8_t)(value), (name)},
    COMP_DIAG_SOURCE_LIST(COMP_DIAG_SOURCE_DEF)
#undef COMP_DIAG_SOURCE_DEF
};

static comp_diag_event_t s_ring[COMP_DIAG_LOG_RING_CAPACITY];
static size_t s_write_index;
static size_t s_count;
static uint32_t s_next_sequence;
static comp_diag_clock_fn_t s_clock_fn;
static void *s_clock_context;

#if defined(__GNUC__)
__attribute__((weak)) void comp_diag_log_lock(void)
{
}

__attribute__((weak)) void comp_diag_log_unlock(void)
{
}
#else
void comp_diag_log_lock(void)
{
}

void comp_diag_log_unlock(void)
{
}
#endif

static uint32_t comp_diag_now_ms(void)
{
    if (s_clock_fn != 0) {
        return s_clock_fn(s_clock_context);
    }
    return 0;
}

static size_t comp_diag_oldest_index_locked(void)
{
    if (s_count < COMP_DIAG_LOG_RING_CAPACITY) {
        return 0;
    }
    return s_write_index;
}

static size_t comp_diag_advance(size_t index)
{
    index++;
    if (index >= COMP_DIAG_LOG_RING_CAPACITY) {
        return 0;
    }
    return index;
}

void comp_diag_log_init(void)
{
    comp_diag_log_clear();
}

void comp_diag_log_clear(void)
{
    comp_diag_log_lock();
    memset(s_ring, 0, sizeof(s_ring));
    s_write_index = 0;
    s_count = 0;
    s_next_sequence = 1;
    comp_diag_log_unlock();
}

void comp_diag_log_set_clock(comp_diag_clock_fn_t clock_fn, void *context)
{
    comp_diag_log_lock();
    s_clock_fn = clock_fn;
    s_clock_context = context;
    comp_diag_log_unlock();
}

void comp_diag_log_record(uint8_t source,
                          uint8_t event_id,
                          uint8_t severity,
                          uint32_t arg0,
                          uint32_t arg1,
                          uint32_t arg2,
                          uint32_t arg3)
{
    comp_diag_event_t event = {
        .sequence = 0,
        .t_ms = comp_diag_now_ms(),
        .source = source,
        .event_id = event_id,
        .severity = severity,
        .flags = 0,
        .arg0 = arg0,
        .arg1 = arg1,
        .arg2 = arg2,
        .arg3 = arg3,
    };

    comp_diag_log_lock();
    event.sequence = s_next_sequence++;
    s_ring[s_write_index] = event;
    s_write_index = comp_diag_advance(s_write_index);
    if (s_count < COMP_DIAG_LOG_RING_CAPACITY) {
        s_count++;
    }
    comp_diag_log_unlock();
}

void comp_diag_log_record_code(uint16_t event_code,
                               uint8_t severity,
                               uint32_t arg0,
                               uint32_t arg1,
                               uint32_t arg2,
                               uint32_t arg3)
{
    comp_diag_log_record(COMP_DIAG_EVENT_SOURCE(event_code),
                         COMP_DIAG_EVENT_ID(event_code),
                         severity,
                         arg0,
                         arg1,
                         arg2,
                         arg3);
}

size_t comp_diag_log_count(void)
{
    comp_diag_log_lock();
    size_t count = s_count;
    comp_diag_log_unlock();
    return count;
}

size_t comp_diag_log_capacity(void)
{
    return COMP_DIAG_LOG_RING_CAPACITY;
}

size_t comp_diag_log_read_tail(comp_diag_event_t *out_events, size_t max_events)
{
    if (out_events == 0 || max_events == 0) {
        return 0;
    }

    comp_diag_log_lock();
    size_t take = s_count < max_events ? s_count : max_events;
    size_t skip = s_count - take;
    size_t index = comp_diag_oldest_index_locked();
    for (size_t i = 0; i < skip; ++i) {
        index = comp_diag_advance(index);
    }
    for (size_t i = 0; i < take; ++i) {
        out_events[i] = s_ring[index];
        index = comp_diag_advance(index);
    }
    comp_diag_log_unlock();
    return take;
}

size_t comp_diag_log_read_tail_by_source(uint8_t source,
                                         comp_diag_event_t *out_events,
                                         size_t max_events)
{
    if (out_events == 0 || max_events == 0) {
        return 0;
    }

    comp_diag_log_lock();
    size_t written = 0;
    size_t index = comp_diag_oldest_index_locked();
    for (size_t i = 0; i < s_count; ++i) {
        const comp_diag_event_t event = s_ring[index];
        if (event.source == source) {
            if (written < max_events) {
                out_events[written++] = event;
            } else {
                memmove(out_events, out_events + 1, (max_events - 1) * sizeof(out_events[0]));
                out_events[max_events - 1] = event;
            }
        }
        index = comp_diag_advance(index);
    }
    comp_diag_log_unlock();
    return written;
}

const char *comp_diag_source_name(uint8_t source)
{
    for (size_t i = 0; i < sizeof(k_sources) / sizeof(k_sources[0]); ++i) {
        if (k_sources[i].id == source) {
            return k_sources[i].name;
        }
    }
    return "unknown";
}

const char *comp_diag_severity_name(uint8_t severity)
{
    switch (severity) {
    case COMP_DIAG_SEV_INFO:
        return "info";
    case COMP_DIAG_SEV_WARN:
        return "warn";
    case COMP_DIAG_SEV_ERROR:
        return "error";
    default:
        return "unknown";
    }
}
