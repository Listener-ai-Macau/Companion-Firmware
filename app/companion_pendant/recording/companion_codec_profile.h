#ifndef COMPANION_CODEC_PROFILE_H
#define COMPANION_CODEC_PROFILE_H
#include <stdint.h>
#define COMP_CODEC_PHASES 7u
/* Contiguous wall times, including IRQs. Not core-active CPU time.
 * 0 setup, 1 prefilter, 2 pre-MDCT, 3 MDCT, 4 energy/allocation,
 * 5 residual quantization, 6 finish. Reset with the normal application boot. */
typedef struct {
    uint32_t calls, invalid, clock_fallbacks, peak_total_us;
    uint64_t total_us, phase_total_us[COMP_CODEC_PHASES];
    uint32_t phase_peak_us[COMP_CODEC_PHASES], worst_us[COMP_CODEC_PHASES];
} companion_codec_profile_t;
#if defined(COMPANION_WBA_CODEC_PROFILE) && COMPANION_WBA_CODEC_PROFILE
void companion_codec_profile_begin(void);
void companion_codec_profile_mark(unsigned phase);
void companion_codec_profile_end(void);
const companion_codec_profile_t *companion_codec_profile_get(void);
#else
#define companion_codec_profile_begin() ((void)0)
#define companion_codec_profile_mark(phase) ((void)0)
#define companion_codec_profile_end() ((void)0)
#endif
#endif
