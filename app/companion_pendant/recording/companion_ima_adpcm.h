#ifndef COMPANION_IMA_ADPCM_H
#define COMPANION_IMA_ADPCM_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Continuous IMA-ADPCM state for 16-bit mono PCM. */
typedef struct {
    int16_t predictor;
    int8_t step_index;
} companion_ima_adpcm_state_t;

void companion_ima_adpcm_state_reset(companion_ima_adpcm_state_t *state);

/* Encode pcm_samples (i16 LE array) into nibbles packed LSB-first in out.
 * Frame: predictor(i16 LE), step_index(u8), reserved(u8)=0, sample_count(u16 LE),
 * then packed nibbles (low nibble first sample of each pair). */
uint16_t companion_ima_adpcm_encode(companion_ima_adpcm_state_t *state,
                                    const int16_t *pcm_samples,
                                    uint16_t sample_count,
                                    uint8_t *out,
                                    uint16_t out_capacity);

/* Decode one frame; returns PCM samples written (equals frame sample_count). */
uint16_t companion_ima_adpcm_decode(const uint8_t *frame,
                                    uint16_t frame_bytes,
                                    int16_t *pcm_out,
                                    uint16_t pcm_capacity_samples);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_IMA_ADPCM_H */
