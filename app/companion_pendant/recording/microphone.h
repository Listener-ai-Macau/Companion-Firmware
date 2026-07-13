#ifndef COMPANION_MICROPHONE_H
#define COMPANION_MICROPHONE_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMPANION_MIC_BACKEND_SPH0645_I2S 1u
#define COMPANION_MIC_BACKEND_SPH0655_PDM 2u

typedef enum {
    COMP_MIC_SOURCE_SPH0645_I2S_COMPATIBLE = 1,
    COMP_MIC_SOURCE_SPH0655_PDM_COMPATIBLE = 2,
} comp_microphone_source_t;

typedef enum {
    COMP_MIC_STM32_INGRESS_SAI_I2S_PCM = 1,
    COMP_MIC_STM32_INGRESS_SAI_PDM = 2,
    COMP_MIC_STM32_INGRESS_I2S_PDM = 3,
    COMP_MIC_STM32_INGRESS_DFSDM_PDM = 4,
    COMP_MIC_STM32_INGRESS_SOFTWARE_FIXTURE = 5,
} comp_microphone_stm32_ingress_t;

typedef enum {
    COMP_MIC_ENCODING_PCM16_MONO = 1,
    COMP_MIC_ENCODING_PDM_1BIT = 2,
} comp_microphone_encoding_t;

typedef struct {
    comp_microphone_source_t source_family;
    comp_microphone_stm32_ingress_t stm32_ingress;
    comp_microphone_encoding_t encoding;
    uint32_t sample_rate_hz;
    uint16_t bits_per_sample;
    uint8_t channels;
    uint16_t frame_samples;
} comp_microphone_format_t;

typedef struct {
    uint32_t frame_count;
    uint16_t samples_per_frame;
    uint16_t bytes_per_frame;
    uint32_t duration_ms;
    uint32_t dropped_frames;
    uint32_t crc32;
} comp_microphone_frame_batch_t;

const comp_microphone_format_t *comp_microphone_default_format(void);
comp_microphone_format_t comp_microphone_make_fixture_format(uint32_t sample_rate_hz,
                                                             uint16_t frame_samples);
uint32_t comp_microphone_frame_bytes(const comp_microphone_format_t *format);
uint32_t comp_microphone_duration_ms(const comp_microphone_format_t *format,
                                     uint32_t frame_count);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_MICROPHONE_H */
