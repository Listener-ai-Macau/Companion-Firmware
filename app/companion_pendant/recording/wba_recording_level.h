#ifndef COMP_WBA_RECORDING_LEVEL_H
#define COMP_WBA_RECORDING_LEVEL_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

/* One second of accepted mono output, sampled one complete 10 ms frame in
 * ten. Mean and peak describe only sampled frames, not an acoustic SPL or
 * an all-sample peak. Saturation is the existing all-output PDM counter. */
typedef struct {
    uint64_t saturation_baseline;
    uint32_t sum, stamp_ms, output_saturated;
    uint16_t samples, peak, mean, output_peak;
    uint8_t frames;
    bool valid;
} comp_wba_recording_level_t;
typedef struct {
    uint16_t sampled_mean, sampled_peak;
    uint32_t saturated_samples, age_ms;
} comp_wba_recording_level_snapshot_t;

/* Display code: 0 is unavailable; 1..5 mean zero through four bars. This
 * logarithmic digital-amplitude display is not an acoustic or speech-quality
 * measurement: a loud background sound can fill it too. */
static inline uint8_t comp_wba_recording_level_bars(uint16_t mean)
{
    return (uint8_t)(1u + (mean >= 16u) + (mean >= 64u) +
                     (mean >= 256u) + (mean >= 1024u));
}

static inline void comp_wba_recording_level_reset(comp_wba_recording_level_t *m,uint64_t saturated)
{if(m){memset(m,0,sizeof(*m));m->saturation_baseline=saturated;}}

static inline void comp_wba_recording_level_pcm(comp_wba_recording_level_t *m,
    const int16_t *pcm,size_t count,uint64_t saturated,uint32_t now_ms)
{
    if(!m||!pcm||count!=160u)return;
    if(m->frames%10u==0u) {
        for(size_t i=0u;i<count;i++) {
            const int32_t s=pcm[i];const uint32_t a=(uint32_t)(s<0?-s:s);
            m->sum+=a;if(a>m->peak)m->peak=(uint16_t)a;
        }
        m->samples+=(uint16_t)count;
    }
    if(++m->frames==100u) {
        const uint64_t clipped=saturated-m->saturation_baseline;
        m->mean=(uint16_t)(m->sum/m->samples);m->output_peak=m->peak;
        m->output_saturated=clipped>UINT32_MAX?UINT32_MAX:(uint32_t)clipped;
        m->stamp_ms=now_ms;m->valid=true;m->saturation_baseline=saturated;
        m->sum=0u;m->samples=0u;m->peak=0u;m->frames=0u;
    }
}
static inline bool comp_wba_recording_level_snapshot(const comp_wba_recording_level_t *m,
    bool recording,uint32_t now_ms,comp_wba_recording_level_snapshot_t *out)
{
    if(!m||!out||!recording||!m->valid||(uint32_t)(now_ms-m->stamp_ms)>=2000u)return false;
    out->sampled_mean=m->mean;out->sampled_peak=m->output_peak;
    out->saturated_samples=m->output_saturated;out->age_ms=now_ms-m->stamp_ms;return true;
}
#endif
