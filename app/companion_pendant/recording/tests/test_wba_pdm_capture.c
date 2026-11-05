#include "wba_pdm_capture.h"

#include <limits.h>
#include <stdio.h>
#include <string.h>

#define TEST_PCM_SAMPLES 320u
#define TEST_MAX_RAW_BYTES \
    (TEST_PCM_SAMPLES * 128u / 8u * COMP_WBA_PDM_CHANNEL_COUNT)
#define TEST_MAX_FRAMES 4u

typedef struct {
    int16_t samples[TEST_MAX_FRAMES * COMP_WBA_PDM_PCM_FRAME_SAMPLES];
    size_t frames;
    bool reject;
} pcm_sink_t;

typedef struct {
    int64_t accumulator;
} sigma_delta_t;

typedef struct {
    uint64_t integrator1;
    uint64_t integrator2;
    uint64_t integrator3;
    uint64_t comb1;
    uint64_t comb2;
    uint64_t comb3;
    int32_t previous_input;
    int32_t previous_output;
    uint16_t phase;
    bool dc_initialized;
} reference_channel_t;

typedef struct {
    comp_wba_pdm_config_t config;
    reference_channel_t channels[2];
    pcm_sink_t *sink;
    int16_t frame[COMP_WBA_PDM_PCM_FRAME_SAMPLES];
    size_t frame_count;
} reference_capture_t;

static int failures;
static uint8_t raw_lr_msb[TEST_MAX_RAW_BYTES];
static uint8_t raw_rl_msb[TEST_MAX_RAW_BYTES];
static uint8_t raw_lr_lsb[TEST_MAX_RAW_BYTES];

#define CHECK(condition) do {                                                \
    if (!(condition)) {                                                      \
        (void)fprintf(stderr, "FAIL %s:%d: %s\n",                          \
                      __FILE__, __LINE__, #condition);                       \
        failures++;                                                          \
    }                                                                        \
} while (0)

static bool collect_pcm(void *context, const int16_t *pcm16_mono,
                        size_t sample_count, uint32_t sample_rate_hz)
{
    pcm_sink_t *sink = (pcm_sink_t *)context;

    CHECK(sample_count == COMP_WBA_PDM_PCM_FRAME_SAMPLES);
    CHECK(sample_rate_hz == COMP_WBA_PDM_PCM_SAMPLE_RATE_HZ);
    if (sink->frames >= TEST_MAX_FRAMES || sink->reject) return false;
    memcpy(&sink->samples[sink->frames * COMP_WBA_PDM_PCM_FRAME_SAMPLES],
           pcm16_mono, sample_count * sizeof(pcm16_mono[0]));
    sink->frames++;
    return true;
}

typedef struct {
    pcm_sink_t pcm;
    const comp_wba_pdm_capture_t *capture;
    uint64_t callback_bits[TEST_MAX_FRAMES];
    size_t callbacks;
} observed_sink_t;

static bool collect_observed_pcm(void *context, const int16_t *pcm16_mono,
                                 size_t sample_count, uint32_t sample_rate_hz)
{
    observed_sink_t *sink = (observed_sink_t *)context;

    CHECK(sink->callbacks < TEST_MAX_FRAMES);
    if (sink->callbacks >= TEST_MAX_FRAMES) return false;
    sink->callback_bits[sink->callbacks++] =
        comp_wba_pdm_capture_stats(sink->capture)->pdm_bits_per_channel;
    return collect_pcm(&sink->pcm, pcm16_mono, sample_count, sample_rate_hz);
}

static bool sigma_delta_bit(sigma_delta_t *state, int16_t target)
{
    state->accumulator += target;
    if (state->accumulator >= 0) {
        state->accumulator -= INT16_MAX;
        return true;
    }
    state->accumulator += 32768;
    return false;
}

static int64_t reference_modulo_i64(uint64_t value)
{
    if (value <= (uint64_t)INT64_MAX) return (int64_t)value;
    return -1 - (int64_t)(UINT64_MAX - value);
}

static int32_t reference_clamp_i32(int64_t value)
{
    if (value > INT32_MAX) return INT32_MAX;
    if (value < INT32_MIN) return INT32_MIN;
    return (int32_t)value;
}

static int16_t reference_clamp_pcm(int32_t value)
{
    if (value > INT16_MAX) return INT16_MAX;
    if (value < INT16_MIN) return INT16_MIN;
    return (int16_t)value;
}

static int32_t reference_dc(reference_channel_t *channel, int32_t sample)
{
    int64_t filtered;

    if (!channel->dc_initialized) {
        channel->previous_input = sample;
        channel->dc_initialized = true;
        return 0;
    }
    filtered = (int64_t)sample - channel->previous_input +
               (((int64_t)channel->previous_output * 32375) >> 15u);
    channel->previous_input = sample;
    channel->previous_output = reference_clamp_i32(filtered);
    return channel->previous_output;
}

static bool reference_feed_bit(reference_capture_t *reference,
                               unsigned channel_index, bool one,
                               int32_t *sample)
{
    reference_channel_t *channel = &reference->channels[channel_index];
    uint64_t difference1;
    uint64_t difference2;
    uint64_t difference3;
    uint64_t cic_gain;
    int64_t normalized;

    channel->integrator1 += one ? UINT64_C(1) : UINT64_MAX;
    channel->integrator2 += channel->integrator1;
    channel->integrator3 += channel->integrator2;
    channel->phase++;
    if (channel->phase < reference->config.decimation) return false;
    channel->phase = 0u;
    difference1 = channel->integrator3 - channel->comb1;
    channel->comb1 = channel->integrator3;
    difference2 = difference1 - channel->comb2;
    channel->comb2 = difference1;
    difference3 = difference2 - channel->comb3;
    channel->comb3 = difference2;
    cic_gain = (uint64_t)reference->config.decimation *
               reference->config.decimation * reference->config.decimation;
    normalized = reference_modulo_i64(difference3);
    normalized = (normalized * reference->config.gain_q15) /
                 (int64_t)cic_gain;
    *sample = reference_dc(channel, reference_clamp_i32(normalized));
    return true;
}

static void reference_emit(reference_capture_t *reference,
                           int32_t left, int32_t right)
{
    int32_t selected;

    if (reference->config.output == COMP_WBA_PDM_OUTPUT_LEFT) {
        selected = left;
    } else if (reference->config.output == COMP_WBA_PDM_OUTPUT_RIGHT) {
        selected = right;
    } else {
        selected = reference_clamp_i32(
            ((int64_t)left + (int64_t)right) / 2);
    }
    reference->frame[reference->frame_count++] = reference_clamp_pcm(selected);
    if (reference->frame_count == COMP_WBA_PDM_PCM_FRAME_SAMPLES) {
        CHECK(reference->sink->frames < TEST_MAX_FRAMES);
        memcpy(&reference->sink->samples[
                   reference->sink->frames * COMP_WBA_PDM_PCM_FRAME_SAMPLES],
               reference->frame, sizeof(reference->frame));
        reference->sink->frames++;
        reference->frame_count = 0u;
    }
}

static void reference_ingest(reference_capture_t *reference,
                             const uint8_t *raw, size_t raw_bytes)
{
    size_t pair;

    for (pair = 0u; pair < raw_bytes; pair += 2u) {
        uint8_t left = raw[pair];
        uint8_t right = raw[pair + 1u];
        unsigned bit;

        if (reference->config.layout ==
            COMP_WBA_PDM_LAYOUT_RIGHT_LEFT_BYTES) {
            uint8_t temporary = left;
            left = right;
            right = temporary;
        }
        for (bit = 0u; bit < 8u; ++bit) {
            unsigned shift = reference->config.bit_order ==
                COMP_WBA_PDM_MSB_FIRST ? 7u - bit : bit;
            bool left_one = ((left >> shift) & 1u) != 0u;
            bool right_one = ((right >> shift) & 1u) != 0u;
            int32_t left_sample = 0;
            int32_t right_sample = 0;
            bool left_ready;
            bool right_ready;

            if (reference->config.invert_left) left_one = !left_one;
            if (reference->config.invert_right) right_one = !right_one;
            left_ready = reference_feed_bit(
                reference, 0u, left_one, &left_sample);
            right_ready = reference_feed_bit(
                reference, 1u, right_one, &right_sample);
            CHECK(left_ready == right_ready);
            if (left_ready) reference_emit(reference, left_sample, right_sample);
        }
    }
}

static uint32_t random_next(uint32_t *state)
{
    uint32_t value = *state;

    value ^= value << 13u;
    value ^= value >> 17u;
    value ^= value << 5u;
    *state = value;
    return value;
}

static int16_t left_target(size_t sample)
{
    return ((sample / 10u) & 1u) != 0u ? (int16_t)-15000 : (int16_t)15000;
}

static int16_t right_target(size_t sample)
{
    return ((sample / 17u) & 1u) != 0u ? (int16_t)9000 : (int16_t)-9000;
}

static size_t make_pdm(uint8_t *raw, size_t pcm_samples, uint16_t decimation,
                       comp_wba_pdm_layout_t layout,
                       comp_wba_pdm_bit_order_t bit_order,
                       bool quiet_right)
{
    sigma_delta_t left = {0};
    sigma_delta_t right = {0};
    size_t pairs = pcm_samples * decimation / 8u;
    size_t sample;

    memset(raw, 0, pairs * 2u);
    for (sample = 0u; sample < pcm_samples; ++sample) {
        unsigned pdm_bit;
        for (pdm_bit = 0u; pdm_bit < decimation; ++pdm_bit) {
            size_t pair = sample * (decimation / 8u) + pdm_bit / 8u;
            unsigned bit_in_byte = pdm_bit & 7u;
            unsigned shift = bit_order == COMP_WBA_PDM_MSB_FIRST
                ? 7u - bit_in_byte : bit_in_byte;
            size_t left_offset = pair * 2u;
            size_t right_offset = left_offset + 1u;
            bool left_one;
            bool right_one;

            if (layout == COMP_WBA_PDM_LAYOUT_RIGHT_LEFT_BYTES) {
                size_t temporary = left_offset;
                left_offset = right_offset;
                right_offset = temporary;
            }
            left_one = sigma_delta_bit(&left, left_target(sample));
            right_one = sigma_delta_bit(
                &right, quiet_right ? 0 : right_target(sample));
            if (left_one) raw[left_offset] |= (uint8_t)(1u << shift);
            if (right_one) raw[right_offset] |= (uint8_t)(1u << shift);
        }
    }
    return pairs * 2u;
}

static comp_wba_pdm_config_t make_config(
    pcm_sink_t *sink, uint16_t decimation, comp_wba_pdm_layout_t layout,
    comp_wba_pdm_bit_order_t bit_order, comp_wba_pdm_output_t output)
{
    comp_wba_pdm_config_t config;

    memset(&config, 0, sizeof(config));
    config.layout = layout;
    config.bit_order = bit_order;
    config.output = output;
    config.decimation = decimation;
    config.gain_q15 = COMP_WBA_PDM_GAIN_Q15_ONE;
    config.emit_pcm_frame = collect_pcm;
    config.context = sink;
    return config;
}

static void test_layout_bit_order_and_chunking(void)
{
    pcm_sink_t sink_a = {0};
    pcm_sink_t sink_b = {0};
    pcm_sink_t sink_c = {0};
    comp_wba_pdm_capture_t capture_a;
    comp_wba_pdm_capture_t capture_b;
    comp_wba_pdm_capture_t capture_c;
    comp_wba_pdm_config_t config_a = make_config(
        &sink_a, 64u, COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES,
        COMP_WBA_PDM_MSB_FIRST, COMP_WBA_PDM_OUTPUT_MIX);
    comp_wba_pdm_config_t config_b = make_config(
        &sink_b, 64u, COMP_WBA_PDM_LAYOUT_RIGHT_LEFT_BYTES,
        COMP_WBA_PDM_MSB_FIRST, COMP_WBA_PDM_OUTPUT_MIX);
    comp_wba_pdm_config_t config_c = make_config(
        &sink_c, 64u, COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES,
        COMP_WBA_PDM_LSB_FIRST, COMP_WBA_PDM_OUTPUT_MIX);
    size_t raw_bytes = make_pdm(
        raw_lr_msb, TEST_PCM_SAMPLES, 64u,
        COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES, COMP_WBA_PDM_MSB_FIRST, false);

    CHECK(raw_bytes == TEST_PCM_SAMPLES * 64u / 8u * 2u);
    CHECK(make_pdm(raw_rl_msb, TEST_PCM_SAMPLES, 64u,
                   COMP_WBA_PDM_LAYOUT_RIGHT_LEFT_BYTES,
                   COMP_WBA_PDM_MSB_FIRST, false) == raw_bytes);
    CHECK(make_pdm(raw_lr_lsb, TEST_PCM_SAMPLES, 64u,
                   COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES,
                   COMP_WBA_PDM_LSB_FIRST, false) == raw_bytes);

    comp_wba_pdm_capture_init(&capture_a, &config_a);
    comp_wba_pdm_capture_init(&capture_b, &config_b);
    comp_wba_pdm_capture_init(&capture_c, &config_c);
    CHECK(comp_wba_pdm_capture_ready(&capture_a));
    CHECK(comp_wba_pdm_capture_ingest(&capture_a, raw_lr_msb, raw_bytes, 10u));
    CHECK(comp_wba_pdm_capture_ingest(&capture_b, raw_rl_msb, 738u, 20u));
    CHECK(comp_wba_pdm_capture_ingest(&capture_b, raw_rl_msb + 738u,
                                      raw_bytes - 738u, 21u));
    CHECK(comp_wba_pdm_capture_ingest(&capture_c, raw_lr_lsb, 1000u, 30u));
    CHECK(comp_wba_pdm_capture_ingest(&capture_c, raw_lr_lsb + 1000u,
                                      raw_bytes - 1000u, 31u));

    CHECK(sink_a.frames == 2u);
    CHECK(sink_b.frames == sink_a.frames);
    CHECK(sink_c.frames == sink_a.frames);
    CHECK(memcmp(sink_a.samples, sink_b.samples,
                 2u * COMP_WBA_PDM_PCM_FRAME_SAMPLES * sizeof(int16_t)) == 0);
    CHECK(memcmp(sink_a.samples, sink_c.samples,
                 2u * COMP_WBA_PDM_PCM_FRAME_SAMPLES * sizeof(int16_t)) == 0);
    CHECK(capture_a.stats.pdm_bits_per_channel ==
          (uint64_t)TEST_PCM_SAMPLES * 64u);
    CHECK(capture_a.stats.pcm_samples_generated == TEST_PCM_SAMPLES);
    CHECK(capture_a.stats.pcm_frames_emitted == 2u);
}

static void test_bit_accounting_at_callbacks_partial_spans_and_faults(void)
{
    observed_sink_t sink = {0};
    comp_wba_pdm_capture_t capture;
    comp_wba_pdm_config_t config = make_config(
        &sink.pcm, 96u, COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES,
        COMP_WBA_PDM_MSB_FIRST, COMP_WBA_PDM_OUTPUT_LEFT);
    size_t raw_bytes = make_pdm(
        raw_lr_msb, TEST_PCM_SAMPLES, 96u, config.layout,
        config.bit_order, false);
    const uint64_t initial_bits = UINT64_MAX - 63u;
    const uint64_t frame_bits = COMP_WBA_PDM_PCM_FRAME_SAMPLES * UINT64_C(96);

    sink.capture = &capture;
    config.emit_pcm_frame = collect_observed_pcm;
    config.context = &sink;
    comp_wba_pdm_capture_init(&capture, &config);
    capture.stats.pdm_bits_per_channel = initial_bits;
    CHECK(comp_wba_pdm_capture_ingest(&capture, raw_lr_msb, 14u, 1u));
    CHECK(capture.stats.pdm_bits_per_channel == initial_bits + 56u);
    CHECK(capture.channels[0].decimation_phase == 56u);
    CHECK(sink.callbacks == 0u);
    CHECK(comp_wba_pdm_capture_ingest(
        &capture, raw_lr_msb + 14u, raw_bytes - 14u, 2u));
    CHECK(sink.callbacks == 2u);
    CHECK(sink.callback_bits[0] == initial_bits + frame_bits);
    CHECK(sink.callback_bits[1] == initial_bits + 2u * frame_bits);
    CHECK(capture.stats.pdm_bits_per_channel == initial_bits + 2u * frame_bits);
    CHECK(comp_wba_pdm_capture_ingest(&capture, raw_lr_msb, 2u, 3u));
    CHECK(capture.stats.pdm_bits_per_channel == initial_bits + 2u * frame_bits + 8u);
    CHECK(capture.channels[0].decimation_phase == 8u);

    /* A mismatched ready boundary must still credit the consumed pair, then
     * clear filter history without exposing a half-channel PCM sample. */
    capture.channels[0].decimation_phase = 88u;
    capture.channels[1].decimation_phase = 0u;
    CHECK(!comp_wba_pdm_capture_ingest(&capture, raw_lr_msb, 2u, 4u));
    CHECK(capture.stats.pdm_bits_per_channel == initial_bits + 2u * frame_bits + 16u);
    CHECK(capture.stats.invalid_dma_blocks == 1u);
    CHECK(capture.channels[0].decimation_phase == 0u);
    CHECK(capture.channels[1].integrator1 == 0u);
    CHECK(capture.stats.pcm_samples_generated == TEST_PCM_SAMPLES);
    CHECK(sink.callbacks == 2u);
}

static void test_decimation_128_and_channel_observability(void)
{
    pcm_sink_t sink = {0};
    comp_wba_pdm_capture_t capture;
    comp_wba_pdm_config_t config = make_config(
        &sink, 128u, COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES,
        COMP_WBA_PDM_LSB_FIRST, COMP_WBA_PDM_OUTPUT_LEFT);
    size_t raw_bytes = make_pdm(
        raw_lr_lsb, TEST_PCM_SAMPLES, 128u,
        COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES, COMP_WBA_PDM_LSB_FIRST, true);

    _Static_assert(COMP_WBA_PDM_PCM_SAMPLE_RATE_HZ * 64u == 1024000u,
                   "16 kHz times 64 must be 1.024 MHz");
    _Static_assert(COMP_WBA_PDM_PCM_SAMPLE_RATE_HZ * 128u == 2048000u,
                   "16 kHz times 128 must be 2.048 MHz");
    comp_wba_pdm_capture_init(&capture, &config);
    CHECK(comp_wba_pdm_capture_ingest(&capture, raw_lr_lsb, 2048u, 100u));
    CHECK(comp_wba_pdm_capture_ingest(&capture, raw_lr_lsb + 2048u,
                                      raw_bytes - 2048u, 101u));
    CHECK(sink.frames == 2u);
    CHECK(capture.stats.pdm_bits_per_channel ==
          (uint64_t)TEST_PCM_SAMPLES * 128u);
    CHECK(capture.stats.left_abs_energy >
          capture.stats.right_abs_energy * 4u);
    CHECK(capture.stats.left_peak != 0);
}

static void test_gap_reorder_invalid_and_backpressure(void)
{
    pcm_sink_t sink = {0};
    comp_wba_pdm_capture_t capture;
    comp_wba_pdm_config_t config = make_config(
        &sink, 64u, COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES,
        COMP_WBA_PDM_MSB_FIRST, COMP_WBA_PDM_OUTPUT_LEFT);
    size_t raw_bytes = make_pdm(
        raw_lr_msb, 160u, 64u, COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES,
        COMP_WBA_PDM_MSB_FIRST, false);
    size_t half_bytes = raw_bytes / 2u;
    uint64_t accepted_raw_bytes;
    uint64_t generated_samples;

    sink.reject = true;
    comp_wba_pdm_capture_init(&capture, &config);
    CHECK(comp_wba_pdm_capture_ingest(
        &capture, raw_lr_msb, half_bytes, 5u));
    CHECK(capture.pcm_frame_count == 80u);
    CHECK(comp_wba_pdm_capture_ingest(
        &capture, raw_lr_msb, raw_bytes, 7u));
    CHECK(capture.stats.missing_dma_blocks == 1u);
    CHECK(capture.stats.pcm_samples_discarded == 240u);
    CHECK(capture.stats.pcm_frames_rejected == 1u);
    CHECK(capture.stats.pcm_frames_emitted == 0u);

    accepted_raw_bytes = capture.stats.raw_bytes;
    generated_samples = capture.stats.pcm_samples_generated;
    CHECK(!comp_wba_pdm_capture_ingest(&capture, raw_lr_msb, 2u, 7u));
    CHECK(capture.stats.reordered_dma_blocks == 1u);
    CHECK(capture.stats.raw_bytes == accepted_raw_bytes);
    CHECK(capture.stats.pcm_samples_generated == generated_samples);
    CHECK(capture.expected_dma_sequence == 8u);
    CHECK(!comp_wba_pdm_capture_ingest(&capture, raw_lr_msb, 3u, 8u));
    CHECK(capture.stats.invalid_dma_blocks == 1u);
    CHECK(comp_wba_pdm_capture_ingest(&capture, raw_lr_msb, 2u, 8u));
    CHECK(capture.expected_dma_sequence == 9u);
    comp_wba_pdm_capture_reset_stream(&capture);
    CHECK(!capture.have_dma_sequence);
}

static void test_invalid_configuration(void)
{
    pcm_sink_t sink = {0};
    comp_wba_pdm_capture_t capture;
    comp_wba_pdm_config_t config = make_config(
        &sink, 80u, COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES,
        COMP_WBA_PDM_MSB_FIRST, COMP_WBA_PDM_OUTPUT_LEFT);
    uint8_t pair[2] = {0u, 0u};

    comp_wba_pdm_capture_init(&capture, &config);
    CHECK(!comp_wba_pdm_capture_ready(&capture));
    CHECK(!comp_wba_pdm_capture_ingest(&capture, pair, sizeof(pair), 0u));
    CHECK(capture.stats.invalid_dma_blocks == 1u);

    config.decimation = 64u;
    config.gain_q15 = 0u;
    comp_wba_pdm_capture_init(&capture, &config);
    CHECK(!comp_wba_pdm_capture_ready(&capture));
    config.gain_q15 = COMP_WBA_PDM_GAIN_Q15_MAX + 1u;
    comp_wba_pdm_capture_init(&capture, &config);
    CHECK(!comp_wba_pdm_capture_ready(&capture));
    config.gain_q15 = COMP_WBA_PDM_GAIN_Q15_ONE;
    config.emit_pcm_frame = NULL;
    comp_wba_pdm_capture_init(&capture, &config);
    CHECK(!comp_wba_pdm_capture_ready(&capture));
}

static void test_random_reference_equivalence(void)
{
    unsigned scenario;

    for (scenario = 0u; scenario < 24u; ++scenario) {
        pcm_sink_t optimized_sink = {0};
        pcm_sink_t reference_sink = {0};
        comp_wba_pdm_capture_t optimized;
        reference_capture_t reference;
        const uint16_t decimations[] = {64u, 96u, 128u};
        uint16_t decimation = decimations[scenario % 3u];
        comp_wba_pdm_config_t config = make_config(
            &optimized_sink, decimation,
            (scenario & 2u) != 0u ?
                COMP_WBA_PDM_LAYOUT_RIGHT_LEFT_BYTES :
                COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES,
            (scenario & 4u) != 0u ?
                COMP_WBA_PDM_LSB_FIRST : COMP_WBA_PDM_MSB_FIRST,
            (comp_wba_pdm_output_t)(scenario % 3u));
        size_t raw_bytes = TEST_PCM_SAMPLES * decimation / 8u * 2u;
        size_t offset = 0u;
        uint32_t random = UINT32_C(0x6D2B79F5) ^ scenario;
        uint32_t sequence = 1000u;

        config.invert_left = (scenario & 8u) != 0u;
        config.invert_right = (scenario & 3u) == 3u;
        for (offset = 0u; offset < raw_bytes; ++offset) {
            raw_lr_msb[offset] = (uint8_t)random_next(&random);
        }
        memset(&reference, 0, sizeof(reference));
        reference.config = config;
        reference.sink = &reference_sink;
        comp_wba_pdm_capture_init(&optimized, &config);
        offset = 0u;
        while (offset < raw_bytes) {
            size_t chunk = 2u * (size_t)((random_next(&random) % 97u) + 1u);

            if (chunk > raw_bytes - offset) chunk = raw_bytes - offset;
            CHECK(comp_wba_pdm_capture_ingest(
                &optimized, raw_lr_msb + offset, chunk, sequence));
            offset += chunk;
            sequence++;
        }
        reference_ingest(&reference, raw_lr_msb, raw_bytes);
        CHECK(optimized_sink.frames == 2u);
        CHECK(reference_sink.frames == optimized_sink.frames);
        CHECK(memcmp(reference_sink.samples, optimized_sink.samples,
                     2u * COMP_WBA_PDM_PCM_FRAME_SAMPLES *
                         sizeof(int16_t)) == 0);
    }
}

static void test_normal_mode_integer_scaling_boundaries(void)
{
    const int32_t targets[] = {INT32_MIN, INT32_MIN + 1, -884737,
        -884736, -884735, -27, -1, 0, 1, 27, 884735, 884736, 884737,
        INT32_MAX - 1, INT32_MAX};
    const uint32_t gains[] = {1u, COMP_WBA_PDM_GAIN_Q15_ONE - 17u,
        COMP_WBA_PDM_GAIN_Q15_ONE, COMP_WBA_PDM_GAIN_Q15_ONE + 123u,
        COMP_WBA_PDM_GAIN_Q15_MAX - 17u, COMP_WBA_PDM_GAIN_Q15_MAX};
    const uint8_t raw[24] = {0}; /* 96 chronological zero bits per channel. */
    uint32_t random = UINT32_C(0x923ADB71);
    for (unsigned gain = 0u; gain < sizeof(gains) / sizeof(gains[0]); ++gain) {
        for (unsigned trial = 0u; trial < 512u; ++trial) {
            uint32_t bits = random_next(&random);
            int32_t target = trial < sizeof(targets) / sizeof(targets[0])
                ? targets[trial] : bits <= INT32_MAX ? (int32_t)bits
                : -1 - (int32_t)(UINT32_MAX - bits);
            pcm_sink_t actual = {0}, expected = {0};
            comp_wba_pdm_capture_t optimized;
            reference_capture_t reference = {0};
            comp_wba_pdm_config_t config = make_config(&actual, 96u,
                COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES, COMP_WBA_PDM_MSB_FIRST,
                COMP_WBA_PDM_OUTPUT_MIX);
            config.gain_q15 = gains[gain];
            reference.config = config; reference.sink = &expected;
            comp_wba_pdm_capture_init(&optimized, &config);
            /* Inject matching comb history to exercise any signed 32-bit
             * CIC difference. The oracle still integrates all 96 bits and
             * normalizes with ordinary signed 64-bit division. */
            int64_t history = -INT64_C(152096) - target;
            for (unsigned channel = 0u; channel < 2u; ++channel) {
                optimized.channels[channel].comb3 = (uint32_t)history;
                reference.channels[channel].comb3 = (uint64_t)history;
            }
            CHECK(comp_wba_pdm_capture_ingest(&optimized, raw, sizeof(raw), 0u));
            reference_ingest(&reference, raw, sizeof(raw));
            for (unsigned channel = 0u; channel < 2u; ++channel) {
                /* Compare before PCM clipping/DC removal can hide a
                 * quotient or rounding error. */
                CHECK(optimized.channels[channel].dc_previous_input ==
                      reference.channels[channel].previous_input);
            }
            CHECK(optimized.stats.pcm_samples_generated == 1u);
            CHECK(actual.frames == 0u && expected.frames == 0u);
        }
    }
}

static void test_long_wrap_and_gain_reference(void)
{
    /* The independent oracle still integrates every bit using 64-bit state.
     * Retain state across blocks to exercise repeated 32-bit CIC wrap. */
    for (unsigned scenario=0u;scenario<24u;++scenario) {
        pcm_sink_t actual={0},expected={0};
        comp_wba_pdm_capture_t optimized;reference_capture_t reference={0};
        const uint16_t decimations[] = {64u, 96u, 128u};
        uint16_t decimation=decimations[scenario%3u];
        comp_wba_pdm_config_t config=make_config(&actual,decimation,
            (scenario&2u)?COMP_WBA_PDM_LAYOUT_RIGHT_LEFT_BYTES:COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES,
            (scenario&4u)?COMP_WBA_PDM_LSB_FIRST:COMP_WBA_PDM_MSB_FIRST,
            (comp_wba_pdm_output_t)(scenario%3u));
        config.gain_q15=(scenario&1u)?COMP_WBA_PDM_GAIN_Q15_MAX:COMP_WBA_PDM_GAIN_Q15_ONE+123u;
        config.invert_left=(scenario&8u)!=0u;config.invert_right=(scenario&3u)==3u;
        reference.config=config;reference.sink=&expected;
        comp_wba_pdm_capture_init(&optimized,&config);
        size_t raw_bytes=TEST_PCM_SAMPLES*decimation/8u*2u;
        uint32_t random=0xA316BA91u+scenario;
        for(uint32_t block=0u;block<50u;++block) {
            for(size_t i=0u;i<raw_bytes;++i)
                raw_lr_msb[i]=block<20u?(uint8_t)((i&1u)?0u:255u):
                    block<35u?(uint8_t)((i&1u)?255u:0u):(uint8_t)random_next(&random);
            actual.frames=0u;expected.frames=0u;
            CHECK(comp_wba_pdm_capture_ingest(&optimized,raw_lr_msb,raw_bytes,block));
            reference_ingest(&reference,raw_lr_msb,raw_bytes);
            CHECK(actual.frames==2u && expected.frames==2u);
            CHECK(memcmp(actual.samples,expected.samples,TEST_PCM_SAMPLES*sizeof(int16_t))==0);
            for(unsigned channel=0u;channel<2u;++channel) {
                CHECK(optimized.channels[channel].integrator3==(uint32_t)reference.channels[channel].integrator3);
                CHECK(optimized.channels[channel].comb3==(uint32_t)reference.channels[channel].comb3);
            }
        }
    }
}

static void test_startup_constant_input_has_no_false_impulse(void)
{
    const uint8_t patterns[] = {0xAAu, 0x55u, 0x77u, 0x88u, 0xFFu, 0x00u};
    unsigned scenario;
    size_t p;

    for (scenario = 0u; scenario < 24u; ++scenario) {
        for (p = 0u; p < sizeof(patterns); ++p) {
            pcm_sink_t sink = {0};
            comp_wba_pdm_capture_t capture;
            const uint16_t decimations[] = {64u, 96u, 128u};
            uint16_t decimation = decimations[scenario % 3u];
            comp_wba_pdm_config_t config = make_config(
                &sink, decimation,
                (scenario & 2u) != 0u ? COMP_WBA_PDM_LAYOUT_RIGHT_LEFT_BYTES
                                      : COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES,
                (scenario & 4u) != 0u ? COMP_WBA_PDM_LSB_FIRST
                                      : COMP_WBA_PDM_MSB_FIRST,
                COMP_WBA_PDM_OUTPUT_MIX);
            size_t raw_bytes = 160u * decimation / 8u * 2u;
            size_t i;

            config.gain_q15 = (scenario & 8u) != 0u
                ? COMP_WBA_PDM_GAIN_Q15_MAX : COMP_WBA_PDM_GAIN_Q15_ONE;
            comp_wba_pdm_capture_init(&capture, &config);
            memset(raw_lr_msb, patterns[p], raw_bytes);
            /* Simulate invalid initial PDM/TDM bytes. They must not reach
             * the recorder or survive a full startup span in CIC history. */
            raw_lr_msb[0] ^= UINT8_MAX;
            raw_lr_msb[1] ^= UINT8_MAX;
            raw_lr_msb[2] ^= UINT8_MAX;
            raw_lr_msb[3] ^= UINT8_MAX;
            CHECK(comp_wba_pdm_capture_prime(
                &capture, raw_lr_msb, raw_bytes, 10u));
            CHECK(sink.frames == 0u);
            CHECK(capture.stats.pcm_samples_generated == 160u);
            CHECK(capture.stats.pcm_samples_discarded == 160u);
            CHECK(capture.stats.pcm_frames_rejected == 0u);
            CHECK(capture.expected_dma_sequence == 11u);
            memset(raw_lr_msb, patterns[p], raw_bytes);
            CHECK(comp_wba_pdm_capture_ingest(
                &capture, raw_lr_msb, raw_bytes, 11u));
            CHECK(sink.frames == 1u);
            for (i = 0u; i < 160u; ++i) CHECK(sink.samples[i] == 0);
            CHECK(capture.stats.saturated_samples == 0u);
            CHECK(capture.stats.missing_dma_blocks == 0u);
        }
    }
}

static void test_primed_signal_matches_bitwise_reference(void)
{
    unsigned scenario;

    for (scenario = 0u; scenario < 24u; ++scenario) {
        pcm_sink_t sink = {0};
        pcm_sink_t expected = {0};
        comp_wba_pdm_capture_t capture;
        reference_capture_t reference = {0};
        const uint16_t decimations[] = {64u, 96u, 128u};
        uint16_t decimation = decimations[scenario % 3u];
        comp_wba_pdm_config_t config = make_config(
            &sink, decimation,
            (scenario & 2u) != 0u ? COMP_WBA_PDM_LAYOUT_RIGHT_LEFT_BYTES
                                  : COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES,
            (scenario & 4u) != 0u ? COMP_WBA_PDM_LSB_FIRST
                                  : COMP_WBA_PDM_MSB_FIRST,
            (comp_wba_pdm_output_t)(scenario % 3u));
        size_t warm_bytes = 160u * decimation / 8u * 2u;
        size_t signal_bytes;

        config.gain_q15 = scenario >= 8u ? COMP_WBA_PDM_GAIN_Q15_MAX
                                          : COMP_WBA_PDM_GAIN_Q15_ONE;
        config.invert_left = (scenario & 1u) != 0u;
        config.invert_right = (scenario & 2u) != 0u;
        reference.config = config;
        reference.sink = &expected;
        comp_wba_pdm_capture_init(&capture, &config);
        memset(raw_lr_msb, 0xAA, warm_bytes);
        CHECK(comp_wba_pdm_capture_prime(
            &capture, raw_lr_msb, warm_bytes, 100u));
        reference_ingest(&reference, raw_lr_msb, warm_bytes);
        memset(&expected, 0, sizeof(expected));
        reference.channels[0].previous_output = 0;
        reference.channels[1].previous_output = 0;

        signal_bytes = make_pdm(raw_lr_msb, TEST_PCM_SAMPLES, decimation,
                               config.layout, config.bit_order, false);
        CHECK(comp_wba_pdm_capture_ingest(
            &capture, raw_lr_msb, signal_bytes / 2u, 101u));
        CHECK(comp_wba_pdm_capture_ingest(
            &capture, raw_lr_msb + signal_bytes / 2u,
            signal_bytes / 2u, 102u));
        reference_ingest(&reference, raw_lr_msb, signal_bytes);
        CHECK(sink.frames == 2u);
        CHECK(expected.frames == sink.frames);
        CHECK(memcmp(sink.samples, expected.samples,
                     TEST_PCM_SAMPLES * sizeof(int16_t)) == 0);
        CHECK(capture.stats.pcm_samples_generated == 480u);
        CHECK(capture.stats.pcm_samples_discarded == 160u);
    }
}

static void test_priming_guards_sequence_reset_and_backpressure(void)
{
    pcm_sink_t sink = {0};
    comp_wba_pdm_capture_t capture;
    comp_wba_pdm_config_t config = make_config(
        &sink, 64u, COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES,
        COMP_WBA_PDM_MSB_FIRST, COMP_WBA_PDM_OUTPUT_LEFT);
    size_t raw_bytes = make_pdm(raw_lr_msb, 160u, 64u, config.layout,
                               config.bit_order, false);
    comp_wba_pdm_channel_state_t history[2];
    uint64_t raw_count;

    sink.reject = true;
    comp_wba_pdm_capture_init(&capture, &config);
    CHECK(!comp_wba_pdm_capture_prime(&capture, raw_lr_msb, 32u, 1u));
    CHECK(!comp_wba_pdm_capture_prime(&capture, raw_lr_msb, raw_bytes - 2u, 1u));
    CHECK(!capture.have_dma_sequence);
    CHECK(capture.stats.raw_bytes == 0u);
    CHECK(capture.stats.invalid_dma_blocks == 2u);
    CHECK(comp_wba_pdm_capture_prime(&capture, raw_lr_msb, raw_bytes, 1u));
    CHECK(capture.stats.pcm_frames_rejected == 0u);
    memcpy(history, capture.channels, sizeof(history));
    raw_count = capture.stats.raw_bytes;
    CHECK(!comp_wba_pdm_capture_prime(&capture, raw_lr_msb, raw_bytes, 2u));
    CHECK(capture.stats.raw_bytes == raw_count);
    CHECK(memcmp(history, capture.channels, sizeof(history)) == 0);
    CHECK(!comp_wba_pdm_capture_ingest(&capture, raw_lr_msb, raw_bytes, 1u));
    CHECK(capture.stats.reordered_dma_blocks == 1u);
    CHECK(comp_wba_pdm_capture_ingest(&capture, raw_lr_msb, raw_bytes, 3u));
    CHECK(capture.stats.missing_dma_blocks == 1u);
    CHECK(capture.stats.pcm_frames_rejected == 1u);
    CHECK(capture.stats.pcm_samples_discarded == 320u);
    comp_wba_pdm_capture_reset_stream(&capture);
    CHECK(comp_wba_pdm_capture_prime(&capture, raw_lr_msb, raw_bytes, 50u));
    CHECK(capture.expected_dma_sequence == 51u);
    CHECK(sink.frames == 0u);
    CHECK(capture.stats.pcm_samples_discarded == 480u);
}

typedef struct {
    const uint8_t *raw;
    size_t raw_bytes;
    size_t fail_at;
    uint8_t scratch[256];
    unsigned malformed;
} dma_reader_t;

static bool copy_dma_chunk(void *context, size_t offset,
                            const uint8_t **bytes, size_t *count)
{
    dma_reader_t *reader = context;
    if (offset >= reader->fail_at) return false;
    *count = reader->raw_bytes - offset;
    if (*count > sizeof(reader->scratch)) *count = sizeof(reader->scratch);
    memcpy(reader->scratch, reader->raw + offset, *count);
    *bytes = reader->scratch;
    if (reader->malformed == 1u) *count = 0u;
    if (reader->malformed == 2u) *count = 3u;
    if (reader->malformed == 3u) *count = reader->raw_bytes + 2u;
    if (reader->malformed == 4u) *bytes = NULL;
    return true;
}

static void test_normal_mode_bounded_dma_reader(void)
{
    for (unsigned mode = 0u; mode < 3u; ++mode) {
        pcm_sink_t copied = {0}, contiguous = {0};
        comp_wba_pdm_capture_t actual, expected;
        comp_wba_pdm_config_t config = make_config(&copied, 96u,
            COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES, COMP_WBA_PDM_MSB_FIRST,
            (comp_wba_pdm_output_t)mode);
        config.gain_q15 = COMP_WBA_PDM_GAIN_Q15_MAX;
        size_t raw_bytes = make_pdm(raw_lr_msb, 160u, 96u, config.layout,
                                    config.bit_order, false);
        dma_reader_t reader = {0};
        reader.raw = raw_lr_msb; reader.raw_bytes = raw_bytes; reader.fail_at = SIZE_MAX;
        comp_wba_pdm_capture_init(&actual, &config);
        config.context = &contiguous;
        comp_wba_pdm_capture_init(&expected, &config);
        CHECK(comp_wba_pdm_capture_read_frame(&actual, copy_dma_chunk, &reader, raw_bytes, 10u, true));
        CHECK(comp_wba_pdm_capture_prime(&expected, raw_lr_msb, raw_bytes, 10u));
        CHECK(copied.frames == 0u && actual.stats.pcm_samples_discarded == 160u);
        for (uint32_t sequence = 11u; sequence < 14u; ++sequence) {
            CHECK(comp_wba_pdm_capture_read_frame(&actual, copy_dma_chunk, &reader, raw_bytes, sequence, false));
            CHECK(comp_wba_pdm_capture_ingest(&expected, raw_lr_msb, raw_bytes, sequence));
        }
        CHECK(copied.frames == 3u);
        CHECK(memcmp(copied.samples, contiguous.samples, sizeof(copied.samples)) == 0);
        CHECK(memcmp(&actual.stats, &expected.stats, sizeof(actual.stats)) == 0);
    }
    /* A late source overwrite must never publish the partially decoded frame. */
    const size_t failures_at[] = {0u, 256u, 3584u};
    for (unsigned failure = 0u; failure < 7u; ++failure) {
        pcm_sink_t sink = {0};
        comp_wba_pdm_capture_t capture;
        comp_wba_pdm_config_t config = make_config(&sink, 96u,
            COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES, COMP_WBA_PDM_MSB_FIRST,
            COMP_WBA_PDM_OUTPUT_LEFT);
        size_t raw_bytes = make_pdm(raw_lr_msb, 160u, 96u, config.layout,
                                    config.bit_order, false);
        dma_reader_t reader = {0};
        reader.raw = raw_lr_msb; reader.raw_bytes = raw_bytes;
        reader.fail_at = failure < 3u ? failures_at[failure] : SIZE_MAX;
        reader.malformed = failure < 3u ? 0u : failure - 2u;
        comp_wba_pdm_capture_init(&capture, &config);
        CHECK(!comp_wba_pdm_capture_read_frame(&capture, copy_dma_chunk, &reader, raw_bytes, 1u, false));
        CHECK(sink.frames == 0u && capture.pcm_frame_count == 0u);
        CHECK(capture.stats.invalid_dma_blocks == 1u);
        CHECK(capture.channels[0].integrator1 == 0u);
        reader.fail_at = SIZE_MAX; reader.malformed = 0u;
        CHECK(comp_wba_pdm_capture_read_frame(&capture, copy_dma_chunk, &reader, raw_bytes, 2u, false));
        CHECK(sink.frames == 1u);
    }
}

int main(void)
{
    test_layout_bit_order_and_chunking();
    test_bit_accounting_at_callbacks_partial_spans_and_faults();
    test_decimation_128_and_channel_observability();
    test_gap_reorder_invalid_and_backpressure();
    test_invalid_configuration();
    test_random_reference_equivalence();
    test_normal_mode_integer_scaling_boundaries();
    test_long_wrap_and_gain_reference();
    test_startup_constant_input_has_no_false_impulse();
    test_primed_signal_matches_bitwise_reference();
    test_priming_guards_sequence_reset_and_backpressure();
    test_normal_mode_bounded_dma_reader();
    if (failures != 0) {
        (void)fprintf(stderr, "wba_pdm_capture: %d failure(s)\n", failures);
        return 1;
    }
    (void)puts("PASS_PREHARDWARE_SOFTWARE_ONLY wba_pdm_capture host tests");
    return 0;
}
