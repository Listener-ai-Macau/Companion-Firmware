#include "companion_ima_adpcm.h"

static const int16_t s_ima_step_table[89] = {
    7,     8,     9,     10,    11,    12,    13,    14,    16,    17,
    19,    21,    23,    25,    28,    31,    34,    37,    41,    45,
    50,    55,    60,    66,    73,    80,    88,    97,    107,   118,
    130,   143,   157,   173,   190,   209,   230,   253,   279,   307,
    337,   371,   408,   449,   494,   544,   598,   658,   724,   796,
    876,   963,   1060,  1166,  1282,  1411,  1552,  1707,  1878,  2066,
    2272,  2499,  2749,  3024,  3327,  3660,  4026,  4428,  4871,  5358,
    5894,  6484,  7132,  7845,  8630,  9493,  10442, 11487, 12635, 13899,
    15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767};

static const int8_t s_ima_index_table[16] = {
    -1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8};

static int16_t companion_ima_clamp_i16(int32_t value)
{
    if (value > 32767) {
        return 32767;
    }
    if (value < -32768) {
        return -32768;
    }
    return (int16_t)value;
}

static uint8_t companion_ima_encode_nibble(companion_ima_adpcm_state_t *state, int16_t sample)
{
    int32_t step = s_ima_step_table[state->step_index];
    int32_t diff = (int32_t)sample - (int32_t)state->predictor;
    uint8_t nibble = 0;
    if (diff < 0) {
        nibble = 8;
        diff = -diff;
    }
    if (diff >= step) {
        nibble |= 4;
        diff -= step;
    }
    if (diff >= (step >> 1)) {
        nibble |= 2;
        diff -= (step >> 1);
    }
    if (diff >= (step >> 2)) {
        nibble |= 1;
    }

    int32_t delta = step >> 3;
    if ((nibble & 4) != 0) {
        delta += step;
    }
    if ((nibble & 2) != 0) {
        delta += step >> 1;
    }
    if ((nibble & 1) != 0) {
        delta += step >> 2;
    }
    if ((nibble & 8) != 0) {
        delta = -delta;
    }
    state->predictor = companion_ima_clamp_i16((int32_t)state->predictor + delta);

    int32_t step_index = (int32_t)state->step_index + s_ima_index_table[nibble & 0x0Fu];
    if (step_index < 0) {
        step_index = 0;
    }
    if (step_index > 88) {
        step_index = 88;
    }
    state->step_index = (int8_t)step_index;
    return (uint8_t)(nibble & 0x0Fu);
}

static int16_t companion_ima_decode_nibble(companion_ima_adpcm_state_t *state, uint8_t nibble)
{
    int32_t step = s_ima_step_table[state->step_index];
    int32_t delta = step >> 3;
    if ((nibble & 4) != 0) {
        delta += step;
    }
    if ((nibble & 2) != 0) {
        delta += step >> 1;
    }
    if ((nibble & 1) != 0) {
        delta += step >> 2;
    }
    if ((nibble & 8) != 0) {
        delta = -delta;
    }
    state->predictor = companion_ima_clamp_i16((int32_t)state->predictor + delta);

    int32_t step_index = (int32_t)state->step_index + s_ima_index_table[nibble & 0x0Fu];
    if (step_index < 0) {
        step_index = 0;
    }
    if (step_index > 88) {
        step_index = 88;
    }
    state->step_index = (int8_t)step_index;
    return state->predictor;
}

void companion_ima_adpcm_state_reset(companion_ima_adpcm_state_t *state)
{
    if (state == NULL) {
        return;
    }
    state->predictor = 0;
    state->step_index = 0;
}

uint16_t companion_ima_adpcm_encode(companion_ima_adpcm_state_t *state,
                                    const int16_t *pcm_samples,
                                    uint16_t sample_count,
                                    uint8_t *out,
                                    uint16_t out_capacity)
{
    if (state == NULL || pcm_samples == NULL || out == NULL || sample_count == 0u) {
        return 0;
    }
    /* 6-byte frame header + ceil(samples/2) nibble bytes */
    uint16_t nibble_bytes = (uint16_t)((sample_count + 1u) / 2u);
    uint16_t need = (uint16_t)(6u + nibble_bytes);
    if (out_capacity < need) {
        return 0;
    }

    out[0] = (uint8_t)((uint16_t)state->predictor & 0xFFu);
    out[1] = (uint8_t)(((uint16_t)state->predictor >> 8) & 0xFFu);
    out[2] = (uint8_t)state->step_index;
    out[3] = 0u;
    out[4] = (uint8_t)(sample_count & 0xFFu);
    out[5] = (uint8_t)((sample_count >> 8) & 0xFFu);

    for (uint16_t i = 0; i < sample_count; i += 2u) {
        uint8_t n0 = companion_ima_encode_nibble(state, pcm_samples[i]);
        uint8_t n1 = 0;
        if ((uint16_t)(i + 1u) < sample_count) {
            n1 = companion_ima_encode_nibble(state, pcm_samples[i + 1u]);
        }
        out[6u + (i / 2u)] = (uint8_t)((n1 << 4) | n0);
    }
    return need;
}

uint16_t companion_ima_adpcm_decode(const uint8_t *frame,
                                    uint16_t frame_bytes,
                                    int16_t *pcm_out,
                                    uint16_t pcm_capacity_samples)
{
    if (frame == NULL || pcm_out == NULL || frame_bytes < 6u) {
        return 0;
    }
    companion_ima_adpcm_state_t state;
    state.predictor = (int16_t)((uint16_t)frame[0] | ((uint16_t)frame[1] << 8));
    state.step_index = (int8_t)frame[2];
    if (state.step_index < 0 || state.step_index > 88) {
        return 0;
    }
    uint16_t samples = (uint16_t)frame[4] | ((uint16_t)frame[5] << 8);
    if (samples > pcm_capacity_samples) {
        return 0;
    }
    uint16_t nibble_bytes = (uint16_t)((samples + 1u) / 2u);
    if (frame_bytes < (uint16_t)(6u + nibble_bytes)) {
        return 0;
    }
    uint16_t written = 0;
    for (uint16_t b = 0; b < nibble_bytes && written < samples; ++b) {
        uint8_t packed = frame[6u + b];
        pcm_out[written++] = companion_ima_decode_nibble(&state, (uint8_t)(packed & 0x0Fu));
        if (written >= samples) {
            break;
        }
        pcm_out[written++] = companion_ima_decode_nibble(&state, (uint8_t)((packed >> 4) & 0x0Fu));
    }
    return written;
}
