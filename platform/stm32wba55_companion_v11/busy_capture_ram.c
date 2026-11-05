/* Temporary, reversible SRAM capture. This is not part of the product image.
 * The host saves/restores core context and the entire 4 KiB scratch range.
 * It enables DWT under halt, then makes no SWD access during this routine.
 * No peripheral output, interrupt controller or panel command is written.
 * These are MCU digital samples, not a measurement at the EPD connector. */
#include <stdint.h>
#include "stm32wba55xx.h"

#define RESULT_ADDRESS 0x2001a400u
#define CAPTURE_MAGIC 0x42555359u
#define CAPTURE_DONE 0x444f4e45u
#define MAX_SAMPLES 1000000u
#define EDGE_RECORDS 128u

typedef struct {
    uint32_t magic, done, target_cycles, core_hz;
    uint32_t samples, low_samples, high_samples, edges;
    uint32_t elapsed_cycles, longest_low, longest_high, max_sample_gap;
    uint32_t first_idr, last_idr, initial_level, final_level;
    uint32_t low_runs, high_runs, low_20ms_runs, high_20ms_runs;
    uint32_t low_bins[6], high_bins[6];
    uint32_t edges_recorded, invalid_counter, swd_clock_changes, swd_data_changes;
    struct { uint32_t cycles, idr; } edge[EDGE_RECORDS];
} capture_t;

static __attribute__((always_inline)) inline void finish_run(
    volatile capture_t *r, uint32_t level, uint32_t duration)
{
    uint32_t bin = 5u;
    if (duration < r->core_hz / 100000u) bin = 0u;       /* <10 us */
    else if (duration < r->core_hz / 10000u) bin = 1u;   /* <100 us */
    else if (duration < r->core_hz / 1000u) bin = 2u;    /* <1 ms */
    else if (duration < r->core_hz / 200u) bin = 3u;     /* <5 ms */
    else if (duration < r->core_hz / 50u) bin = 4u;      /* <20 ms */
    if (level) {
        ++r->high_runs; ++r->high_bins[bin];
        if (duration > r->longest_high) r->longest_high = duration;
        if (duration >= r->core_hz / 50u) ++r->high_20ms_runs;
    } else {
        ++r->low_runs; ++r->low_bins[bin];
        if (duration > r->longest_low) r->longest_low = duration;
        if (duration >= r->core_hz / 50u) ++r->low_20ms_runs;
    }
}

__attribute__((noreturn, section(".capture_entry"))) void busy_capture_entry(void)
{
    volatile capture_t *r = (volatile capture_t *)RESULT_ADDRESS;
    /* Configuration is supplied by the host in an otherwise zeroed result. */
    r->magic = CAPTURE_MAGIC;
    /* Exclude the resume command itself. Also sample the actual SWD pins:
     * no Python API calls alone cannot rule out adapter/library traffic. */
    uint32_t warmup = DWT->CYCCNT;
    for (uint32_t i = 0; i < MAX_SAMPLES; ++i) {
        if (DWT->CYCCNT - warmup >= r->core_hz / 20u) break;
        __NOP();
    }
    uint32_t begin = DWT->CYCCNT, previous = begin, run_start = begin;
    uint32_t idr = GPIOA->IDR, level = (idr >> 12) & 1u;
    uint32_t previous_idr = idr;
    r->first_idr = idr; r->initial_level = level;
    for (uint32_t i = 0; i < MAX_SAMPLES; ++i) {
        uint32_t current = DWT->CYCCNT;
        idr = GPIOA->IDR;
        uint32_t changed = idr ^ previous_idr;
        if (changed & (1u << 14)) ++r->swd_clock_changes;
        if (changed & (1u << 13)) ++r->swd_data_changes;
        previous_idr = idr;
        uint32_t next = (idr >> 12) & 1u, elapsed = current - begin;
        uint32_t gap = current - previous;
        if (gap > r->max_sample_gap) r->max_sample_gap = gap;
        previous = current;
        ++r->samples;
        if (next) ++r->high_samples; else ++r->low_samples;
        if (next != level) {
            finish_run(r, level, current - run_start);
            ++r->edges;
            uint32_t n = r->edges_recorded;
            if (n < EDGE_RECORDS) {
                r->edge[n].cycles = elapsed; r->edge[n].idr = idr;
                r->edges_recorded = n + 1u;
            }
            level = next; run_start = current;
        }
        r->elapsed_cycles = elapsed;
        if (elapsed >= r->target_cycles) break;
    }
    finish_run(r, level, previous - run_start);
    r->last_idr = idr; r->final_level = level;
    r->invalid_counter = r->elapsed_cycles == 0u;
    r->done = CAPTURE_DONE;
    __DSB();
    __BKPT(0);
    for (;;) __NOP();
}
