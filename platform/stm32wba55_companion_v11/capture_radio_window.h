#ifndef COMPANION_CAPTURE_RADIO_WINDOW_H
#define COMPANION_CAPTURE_RADIO_WINDOW_H

#include <stdbool.h>
#include <stdint.h>

/* Cooperative admission only. Radio IRQ priorities and scheduling are untouched.
 * The 7ms gap covers the observed codec thread and controller dispatch margin;
 * it is not a promise that no new controller work can arrive during a frame.
 * A missing query or12ms of waiting falls back to existing DMA admission.
 * Six milliseconds can expire just BEFORE an already announced radio event;
 * allow that event to finish instead. The product's independent30ms queued
 * PCM override still bypasses courtesy before its eight-slot ring fills.
 * Capture service continues on every deferred foreground turn. */
typedef struct { uint32_t since_ms; bool waiting; } comp_capture_radio_window_t;

static inline bool comp_capture_radio_window_open(comp_capture_radio_window_t *w,
    uint32_t now_ms,bool pending,bool valid,bool radio_busy,uint32_t next_us)
{
    if (!pending || !valid || (!radio_busy && next_us > 7000u)) {
        w->waiting=false;
        return true;
    }
    if (!w->waiting) { w->since_ms=now_ms; w->waiting=true; }
    if (now_ms-w->since_ms >= 12u) { w->waiting=false; return true; }
    return false;
}

#endif
