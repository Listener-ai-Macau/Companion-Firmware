#ifndef COMPANION_CAPTURE_RADIO_WINDOW_H
#define COMPANION_CAPTURE_RADIO_WINDOW_H

#include <stdbool.h>
#include <stdint.h>

/* Cooperative admission only. Radio IRQ priorities and scheduling are untouched.
 * The 7ms gap covers the observed codec thread and controller dispatch margin;
 * it is not a promise that no new controller work can arrive during a frame.
 * A missing query or 10ms of waiting falls back to the existing DMA admission.
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
    if (now_ms-w->since_ms >= 10u) { w->waiting=false; return true; }
    return false;
}

/* A completed DMA half remains live until the next10ms boundary. Wait only
 * while more than3ms remains for copying it; urgency always wins over radio.
 * Snapshot/sequence/deadline checks still run unchanged after admission. */
static inline bool comp_capture_radio_convert_open(bool valid,bool radio_busy,
    uint32_t next_us,uint32_t remaining,uint32_t half_bytes)
{
    if(!valid || !half_bytes || half_bytes>UINT32_MAX/2u || !remaining ||
       remaining>2u*half_bytes)return true;
    uint32_t to_boundary=remaining>half_bytes?remaining-half_bytes:remaining;
    if((uint64_t)to_boundary*10u<=(uint64_t)half_bytes*3u)return true;
    return !radio_busy && next_us>3500u;
}

#endif
