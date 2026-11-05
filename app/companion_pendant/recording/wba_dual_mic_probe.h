#ifndef COMPANION_WBA_DUAL_MIC_PROBE_H
#define COMPANION_WBA_DUAL_MIC_PROBE_H

#include <stddef.h>
#include <stdint.h>
#include <string.h>

/* Finite, passive correlation of simultaneous PCM pairs. No UART, recording
 * control, allocation, FFT, automatic calibration or signal modification here.
 * A known single desired source is required before using host-side estimates.
 * Seven lags cover +/-3 PCM samples. The archived PCB component centers are
 * ~31.8mm apart, not proof of current acoustic holes or assembled channel order. */
#define COMP_WBA_DUAL_PROBE_LAG 3
#define COMP_WBA_DUAL_PROBE_LAGS (2 * COMP_WBA_DUAL_PROBE_LAG + 1)
#define COMP_WBA_DUAL_PROBE_LIMIT 32000u

typedef struct {
    int64_t cross[COMP_WBA_DUAL_PROBE_LAGS];
    uint64_t right_square[COMP_WBA_DUAL_PROBE_LAGS];
    int64_t right_sum[COMP_WBA_DUAL_PROBE_LAGS];
    uint64_t left_square;
    int64_t left_sum;
    int16_t history[2][COMP_WBA_DUAL_PROBE_LAGS];
    uint32_t samples, count, clipped_left, clipped_right;
    uint8_t cursor;
    uint8_t invalid; /* sticky discontinuity; never silently join two takes */
} comp_wba_dual_mic_probe_t;

static inline void comp_wba_dual_probe_reset(comp_wba_dual_mic_probe_t *p)
{ memset(p, 0, sizeof(*p)); }

static inline void comp_wba_dual_probe_invalidate(comp_wba_dual_mic_probe_t *p)
{ p->invalid = 1u; }

static inline void comp_wba_dual_probe_add(comp_wba_dual_mic_probe_t *p,
                                          const int16_t *interleaved, size_t frames)
{
    if (!p || !interleaved || p->invalid) return;
    for (size_t n = 0; n < frames && p->samples < COMP_WBA_DUAL_PROBE_LIMIT; ++n) {
        const int16_t l = interleaved[2u*n], r = interleaved[2u*n+1u];
        const unsigned cursor = p->cursor;
        p->history[0][cursor] = l; p->history[1][cursor] = r;
        p->clipped_left += l == INT16_MIN || l == INT16_MAX;
        p->clipped_right += r == INT16_MIN || r == INT16_MAX;
        if (p->samples >= COMP_WBA_DUAL_PROBE_LAGS - 1u) {
            const unsigned center = (cursor + COMP_WBA_DUAL_PROBE_LAGS - COMP_WBA_DUAL_PROBE_LAG) % COMP_WBA_DUAL_PROBE_LAGS;
            const int64_t left = p->history[0][center];
            p->left_sum += left; p->left_square += (uint64_t)(left*left);
            for (int lag = -COMP_WBA_DUAL_PROBE_LAG; lag <= COMP_WBA_DUAL_PROBE_LAG; ++lag) {
                const unsigned k = (unsigned)(lag + COMP_WBA_DUAL_PROBE_LAG);
                const unsigned index = (unsigned)((int)center + lag + COMP_WBA_DUAL_PROBE_LAGS) % COMP_WBA_DUAL_PROBE_LAGS;
                const int64_t right = p->history[1][index];
                p->right_sum[k] += right;
                p->right_square[k] += (uint64_t)(right*right);
                p->cross[k] += left*right;
            }
            ++p->count;
        }
        p->cursor = (uint8_t)((cursor + 1u) % COMP_WBA_DUAL_PROBE_LAGS);
        ++p->samples;
    }
}

#endif
