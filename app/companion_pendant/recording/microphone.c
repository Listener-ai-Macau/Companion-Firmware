#include "microphone.h"

#ifndef COMPANION_MIC_BACKEND
#define COMPANION_MIC_BACKEND COMPANION_MIC_BACKEND_SPH0655_PDM
#endif

static const comp_microphone_format_t k_default_format = {
#if COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM
    .source_family = COMP_MIC_SOURCE_SPH0655_PDM_COMPATIBLE,
    .stm32_ingress = COMP_MIC_STM32_INGRESS_SAI_PDM,
#else
    .source_family = COMP_MIC_SOURCE_SPH0645_I2S_COMPATIBLE,
    .stm32_ingress = COMP_MIC_STM32_INGRESS_SAI_I2S_PCM,
#endif
    .encoding = COMP_MIC_ENCODING_PCM16_MONO,
    .sample_rate_hz = 16000u,
    .bits_per_sample = 16u,
    .channels = 1u,
    .frame_samples = 160u,
};

const comp_microphone_format_t *comp_microphone_default_format(void)
{
    return &k_default_format;
}

comp_microphone_format_t comp_microphone_make_fixture_format(uint32_t sample_rate_hz,
                                                             uint16_t frame_samples)
{
    comp_microphone_format_t format = k_default_format;
    format.stm32_ingress = COMP_MIC_STM32_INGRESS_SOFTWARE_FIXTURE;
    if (sample_rate_hz != 0u) {
        format.sample_rate_hz = sample_rate_hz;
    }
    if (frame_samples != 0u) {
        format.frame_samples = frame_samples;
    }
    return format;
}

uint32_t comp_microphone_frame_bytes(const comp_microphone_format_t *format)
{
    const comp_microphone_format_t *selected = format != 0 ? format : &k_default_format;
    uint32_t bytes_per_sample = ((uint32_t)selected->bits_per_sample + 7u) / 8u;
    return (uint32_t)selected->frame_samples * bytes_per_sample * (uint32_t)selected->channels;
}

uint32_t comp_microphone_duration_ms(const comp_microphone_format_t *format,
                                     uint32_t frame_count)
{
    const comp_microphone_format_t *selected = format != 0 ? format : &k_default_format;
    if (selected->sample_rate_hz == 0u) {
        return 0u;
    }
    uint64_t samples = (uint64_t)selected->frame_samples * (uint64_t)frame_count;
    return (uint32_t)((samples * 1000u) / (uint64_t)selected->sample_rate_hz);
}
