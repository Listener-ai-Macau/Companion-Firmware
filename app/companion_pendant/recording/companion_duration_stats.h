#ifndef COMPANION_DURATION_STATS_H
#define COMPANION_DURATION_STATS_H

#include <stdbool.h>
#include <stdint.h>

/* Foreground-only, no allocation. Bins 0..9 hold tick deltas; bin 10 holds
 * the tail. These are durations, never CPU utilization or power measurements.
 * A 1 ms tick delta can understate elapsed wall time by almost 1 ms, so the
 * reported percentile/peak is a conservative upper bound, not an exact P95. */
#define COMP_DURATION_MS_BINS 11u
#define COMP_DURATION_MIN_PERCENTILE_SAMPLES 20u

typedef struct {
    uint32_t bins[COMP_DURATION_MS_BINS];
    uint32_t samples;
    uint32_t peak_ms;
    bool saturated;
} comp_duration_stats_t;

static inline void comp_duration_stats_note(comp_duration_stats_t *stats,
                                            uint32_t elapsed_ms)
{
    if (elapsed_ms > stats->peak_ms) stats->peak_ms = elapsed_ms;
    if (stats->samples == UINT32_MAX) {
        stats->saturated = true;
        return;
    }
    uint32_t bin = elapsed_ms < COMP_DURATION_MS_BINS - 1u ?
                   elapsed_ms : COMP_DURATION_MS_BINS - 1u;
    stats->bins[bin]++;
    stats->samples++;
}

static inline bool comp_duration_stats_peak_upper_ms(
    const comp_duration_stats_t *stats, uint32_t *upper_ms)
{
    *upper_ms = 0u;
    if (stats->samples == 0u || stats->saturated || stats->peak_ms == UINT32_MAX)
        return false;
    *upper_ms = stats->peak_ms + 1u;
    return true;
}

static inline bool comp_duration_stats_percentile_upper_ms(
    const comp_duration_stats_t *stats, unsigned percentile, uint32_t *upper_ms)
{
    *upper_ms = 0u;
    if (stats->samples < COMP_DURATION_MIN_PERCENTILE_SAMPLES ||
        stats->saturated || percentile == 0u || percentile > 100u ||
        stats->peak_ms == UINT32_MAX) return false;
    uint64_t rank = ((uint64_t)stats->samples * percentile + 99u) / 100u;
    uint64_t cumulative = 0u;
    for (unsigned bin = 0u; bin < COMP_DURATION_MS_BINS; ++bin) {
        cumulative += stats->bins[bin];
        if (cumulative >= rank) {
            /* Tail bins have no precise rank: using the measured peak can
             * only make the qualification stricter, never hide a slow frame. */
            *upper_ms = bin == COMP_DURATION_MS_BINS - 1u ?
                        stats->peak_ms + 1u : bin + 1u;
            return true;
        }
    }
    return false;
}

#endif
