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
    union {uint32_t peak_ms,peak_us;};
    /* Reuse the existing alignment bytes; legacy ports keep millisecond
     * observations, precise target ports retain a unit and invalid-clock bit. */
    bool saturated,microseconds,clock_invalid;
} comp_duration_stats_t;
_Static_assert(sizeof(comp_duration_stats_t)==56u,"duration statistics reuse existing padding");

static inline void comp_duration_stats_note(comp_duration_stats_t *stats,
                                            uint32_t elapsed_ms)
{
    if(stats->microseconds){stats->clock_invalid=true;return;}
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
    if (stats->samples == 0u || stats->saturated || stats->clock_invalid || stats->peak_ms == UINT32_MAX)
        return false;
    if(stats->microseconds){*upper_ms=stats->peak_us/1000u+1u;return true;}
    *upper_ms = stats->peak_ms + 1u;
    return true;
}

/* Fixed bounds retain the original eleven counters. They resolve the frozen
 * PDM3ms/Opus5ms/6ms requirements, without a larger histogram or frame trace.
 * One microsecond is added for stamp quantization before selecting a bound. */
static inline uint32_t comp_duration_us_bound(unsigned bin)
{
    static const uint16_t upper[10]={1000u,2000u,3000u,4000u,4500u,5000u,5500u,6000u,7000u,8000u};
    return upper[bin];
}
static inline void comp_duration_stats_note_us(comp_duration_stats_t *stats,uint32_t elapsed_us)
{
    if(stats->samples&&!stats->microseconds){stats->clock_invalid=true;return;}
    stats->microseconds=true;
    if(elapsed_us>stats->peak_us)stats->peak_us=elapsed_us;
    if(stats->samples==UINT32_MAX||elapsed_us==UINT32_MAX){stats->saturated=true;return;}
    unsigned bin=0u;
    while(bin<10u&&elapsed_us>=comp_duration_us_bound(bin))++bin;
    stats->bins[bin]++;stats->samples++;
}
static inline bool comp_duration_stats_peak_upper_us(const comp_duration_stats_t *stats,uint32_t *upper_us)
{
    *upper_us=0u;
    if(!stats->samples||stats->saturated||stats->clock_invalid||stats->peak_us==UINT32_MAX)return false;
    if(stats->microseconds){*upper_us=stats->peak_us+1u;return true;}
    if(stats->peak_ms>=UINT32_MAX/1000u)return false;
    *upper_us=(stats->peak_ms+1u)*1000u;return true;
}
static inline bool comp_duration_stats_percentile_upper_us(
    const comp_duration_stats_t *stats,unsigned percentile,uint32_t *upper_us)
{
    *upper_us=0u;
    if(stats->samples<COMP_DURATION_MIN_PERCENTILE_SAMPLES||stats->saturated||stats->clock_invalid||
       !percentile||percentile>100u||stats->peak_us==UINT32_MAX)return false;
    uint64_t rank=((uint64_t)stats->samples*percentile+99u)/100u,cumulative=0u;
    for(unsigned bin=0u;bin<COMP_DURATION_MS_BINS;bin++) {
        cumulative+=stats->bins[bin];
        if(cumulative>=rank) {
            if(bin==10u)return comp_duration_stats_peak_upper_us(stats,upper_us);
            *upper_us=stats->microseconds?comp_duration_us_bound(bin):(bin+1u)*1000u;return true;
        }
    }
    return false;
}
static inline bool comp_duration_stats_percentile_upper_ms(
    const comp_duration_stats_t *stats, unsigned percentile, uint32_t *upper_ms)
{
    *upper_ms = 0u;
    if(stats->microseconds) {
        uint32_t us;
        if(!comp_duration_stats_percentile_upper_us(stats,percentile,&us))return false;
        *upper_ms=us/1000u+(us%1000u!=0u);return true;
    }
    if (stats->samples < COMP_DURATION_MIN_PERCENTILE_SAMPLES ||
        stats->saturated || stats->clock_invalid || percentile == 0u || percentile > 100u ||
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

#ifndef COMPANION_FINE_DURATION_CLOCK
#define COMPANION_FINE_DURATION_CLOCK 0
#endif
typedef struct {uint32_t stamp;bool valid;} comp_duration_stamp_t;
#if COMPANION_FINE_DURATION_CLOCK
/* Platform read-only clock. Failure is explicit, never a coarser silent
 * fallback. Each span must be shorter than the modulo32-bit71minute period. */
bool comp_duration_clock_us(uint32_t *);
#endif
static inline comp_duration_stamp_t comp_duration_begin(uint32_t fallback_ms)
{
    comp_duration_stamp_t s={fallback_ms,true};
#if COMPANION_FINE_DURATION_CLOCK
    s.valid=comp_duration_clock_us(&s.stamp);
#endif
    return s;
}
static inline void comp_duration_end(comp_duration_stats_t *stats,comp_duration_stamp_t start,uint32_t fallback_ms)
{
#if COMPANION_FINE_DURATION_CLOCK
    uint32_t end=0u;(void)fallback_ms;
    bool valid=comp_duration_clock_us(&end);
    if(!start.valid||!valid){stats->clock_invalid=true;return;}
    comp_duration_stats_note_us(stats,end-start.stamp);
#else
    comp_duration_stats_note(stats,fallback_ms-start.stamp);
#endif
}

#endif
