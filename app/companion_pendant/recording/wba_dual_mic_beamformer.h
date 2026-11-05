#ifndef COMPANION_WBA_DUAL_MIC_BEAMFORMER_H
#define COMPANION_WBA_DUAL_MIC_BEAMFORMER_H

#include <stdbool.h>
#include <stdint.h>
#include <limits.h>
#include <string.h>

/* Calibrated fixed delay-and-sum, before PCM16 clipping and Opus. No heap,
 * FFT, extra frame, VAD or claim of identifying a particular speaker.
 * Positive delay means the right microphone hears the desired voice later:
 * delay LEFT to align it. Negative delay delays RIGHT. Units: 1/256 sample
 * at the existing 16 kHz PCM rate. Geometry/phase/gain must be measured;
 * zero is only the broadside assumption, never an automatic calibration. */
#define COMP_WBA_DUAL_MAX_DELAY_SAMPLES 8
#define COMP_WBA_DUAL_HISTORY (COMP_WBA_DUAL_MAX_DELAY_SAMPLES + 2)

typedef struct {
    int16_t delay_q8;
    uint16_t right_gain_q15; /* 16384..65535; unity=32768, fixed trim only */
    bool invert_right;
} comp_wba_dual_mic_config_t;

typedef struct {
    comp_wba_dual_mic_config_t config;
    int32_t history[2][COMP_WBA_DUAL_HISTORY];
    uint8_t write_index;
} comp_wba_dual_mic_t;

static inline bool comp_wba_dual_mic_config_valid(const comp_wba_dual_mic_config_t *c)
{
    return c && c->delay_q8 >= -COMP_WBA_DUAL_MAX_DELAY_SAMPLES * 256 &&
        c->delay_q8 <= COMP_WBA_DUAL_MAX_DELAY_SAMPLES * 256 &&
        c->right_gain_q15 >= 16384u;
}

static inline int32_t comp_wba_dual_mic_clamp32(int64_t value)
{
    return value > INT32_MAX ? INT32_MAX :
        value < INT32_MIN ? INT32_MIN : (int32_t)value;
}

static inline void comp_wba_dual_mic_reset(comp_wba_dual_mic_t *b)
{
    memset(b->history, 0, sizeof(b->history));
    b->write_index = 0u;
}

static inline int32_t comp_wba_dual_mic_tap(const comp_wba_dual_mic_t *b,
                                          unsigned channel, unsigned delay_q8)
{
    unsigned whole = delay_q8 / 256u, fraction = delay_q8 % 256u;
    /* Validated delay gives whole<=8 and write_index<10: the sum is
     * in [2,19], so at most one wrap is needed. Keep the ten-sample
     * history and exact signed interpolation; no larger padded ring. */
    unsigned index = b->write_index + COMP_WBA_DUAL_HISTORY - whole;
    if (index >= COMP_WBA_DUAL_HISTORY) index -= COMP_WBA_DUAL_HISTORY;
    int32_t recent = b->history[channel][index];
    if (!fraction) return recent;
    unsigned older_index = index ? index - 1u : COMP_WBA_DUAL_HISTORY - 1u;
    /* Linear fractional delay: bounded two taps, no unbounded search. It is
     * not an all-pass filter; off-axis/high-frequency response needs A/B. */
    return (int32_t)(((int64_t)recent * (256u - fraction) +
                     (int64_t)b->history[channel][older_index] * fraction) / 256);
}

/* Caller validates config at capture initialization. Startup history is
 * warmed using the same hardware startup span already discarded by capture.
 * Reset on discontinuity prevents joining unrelated microphone samples. */
static inline int32_t comp_wba_dual_mic_process(comp_wba_dual_mic_t *b,
                                              int32_t left, int32_t right)
{
    int64_t trimmed = (int64_t)right * b->config.right_gain_q15 / 32768;
    if (b->config.invert_right) trimmed = -trimmed;
    b->history[0][b->write_index] = left;
    b->history[1][b->write_index] = comp_wba_dual_mic_clamp32(trimmed);
    int delay = b->config.delay_q8;
    /* Only one channel is delayed. The other is the sample just stored;
     * avoid calculating its zero-delay ring index on every PCM sample. */
    int32_t l = left, r = b->history[1][b->write_index];
    if (delay > 0) l = comp_wba_dual_mic_tap(b, 0u, (unsigned)delay);
    else if (delay < 0) r = comp_wba_dual_mic_tap(b, 1u, (unsigned)-delay);
    if (++b->write_index == COMP_WBA_DUAL_HISTORY) b->write_index = 0u;
    /* Unity target level, wide intermediate, then the existing single PCM16
     * saturation and 10 ms callback. No hidden doubling of volume. */
    return (int32_t)(((int64_t)l + r) / 2);
}

#endif
