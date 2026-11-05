#ifndef COMPANION_WBA_PDM_CAPTURE_H
#define COMPANION_WBA_PDM_CAPTURE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "wba_dual_mic_beamformer.h"

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_WBA_PDM_PCM_SAMPLE_RATE_HZ 16000u
#define COMP_WBA_PDM_PCM_FRAME_SAMPLES 160u
#define COMP_WBA_PDM_CHANNEL_COUNT 2u
#define COMP_WBA_PDM_GAIN_Q15_ONE 32768u
#define COMP_WBA_PDM_GAIN_Q15_MAX (128u * COMP_WBA_PDM_GAIN_Q15_ONE)

typedef enum {
    /* STM32 SAI PDM interface, one mic pair, 16-bit slot, DMA memory bytes
     * expected as mic-left byte then mic-right byte. */
    COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES = 0,
    COMP_WBA_PDM_LAYOUT_RIGHT_LEFT_BYTES = 1,
} comp_wba_pdm_layout_t;

typedef enum {
    COMP_WBA_PDM_MSB_FIRST = 0,
    COMP_WBA_PDM_LSB_FIRST = 1,
} comp_wba_pdm_bit_order_t;

typedef enum {
    COMP_WBA_PDM_OUTPUT_LEFT = 0,
    COMP_WBA_PDM_OUTPUT_RIGHT,
    COMP_WBA_PDM_OUTPUT_MIX,
    COMP_WBA_PDM_OUTPUT_BEAMFORM, /* explicit calibrated candidate, never implicit MIX */
} comp_wba_pdm_output_t;

typedef bool (*comp_wba_pdm_pcm_frame_fn_t)(
    void *context,
    const int16_t *pcm16_mono,
    size_t sample_count,
    uint32_t sample_rate_hz);

/* Optional synchronous observation of verified, accepted10ms PCM pairs.
 * Interleaved [left,right], before beamforming, already using normal channel
 * gain/DC/clipping. Pointer is valid only during this call. The caller owns
 * pair_pcm_storage (>=320 int16 values); no extra frame is allocated by capture.
 * No callback for priming, rejected/stale/partial frames. Never block or do I/O. */
typedef void (*comp_wba_pdm_pair_frame_fn_t)(void *context,
    const int16_t *pcm16_interleaved, size_t frames, uint32_t sample_rate_hz);

/* Return a stable, even-sized copy of the next DMA span. The copy stays valid
 * until the next call; return false if DMA has overwritten the source. */
typedef bool (*comp_wba_pdm_read_fn_t)(void *context, size_t offset,
                                     const uint8_t **bytes, size_t *count);

typedef struct {
    comp_wba_pdm_layout_t layout;
    comp_wba_pdm_bit_order_t bit_order;
    comp_wba_pdm_output_t output;
    uint16_t decimation;
    uint32_t gain_q15;
    bool invert_left;
    bool invert_right;
    /* Default false preserves dual-channel diagnostics. True computes only
     * the selected mono output; MIX still processes both. Raw DMA, sequence,
     * stale-copy and frame boundaries are unchanged. Inactive channel filter
     * statistics are unavailable, not evidence of silence or failed hardware. */
    bool selected_only;
    comp_wba_dual_mic_config_t dual_mic; /* required only for BEAMFORM */
    comp_wba_pdm_pair_frame_fn_t observe_pair_frame;
    int16_t *pair_pcm_storage;
    size_t pair_pcm_capacity; /* int16 count, not bytes */
    comp_wba_pdm_pcm_frame_fn_t emit_pcm_frame;
    void *context;
} comp_wba_pdm_config_t;

typedef struct {
    uint64_t dma_blocks;
    uint64_t raw_bytes;
    uint64_t pdm_bits_per_channel;
    uint64_t pcm_samples_generated;
    uint64_t pcm_frames_emitted;
    uint64_t pcm_frames_rejected;
    uint64_t pcm_samples_discarded;
    uint64_t missing_dma_blocks;
    uint64_t reordered_dma_blocks;
    uint64_t invalid_dma_blocks;
    uint64_t saturated_samples;
    uint64_t left_abs_energy;
    uint64_t right_abs_energy;
    uint32_t last_dma_sequence;
    int16_t left_peak;
    int16_t right_peak;
} comp_wba_pdm_stats_t;

typedef struct {
    /* CIC arithmetic wraps modulo 2^32. With R<=128, the final third
     * difference is bounded by R^3=2^21 and has an exact signed result. */
    uint32_t integrator1;
    uint32_t integrator2;
    uint32_t integrator3;
    uint32_t comb1;
    uint32_t comb2;
    uint32_t comb3;
    int32_t dc_previous_input;
    int32_t dc_previous_output;
    uint16_t decimation_phase;
    bool dc_initialized;
} comp_wba_pdm_channel_state_t;

typedef struct {
    comp_wba_pdm_config_t config;
    comp_wba_pdm_channel_state_t channels[COMP_WBA_PDM_CHANNEL_COUNT];
    comp_wba_pdm_stats_t stats;
    comp_wba_dual_mic_t dual_mic;
    int16_t pcm_frame[COMP_WBA_PDM_PCM_FRAME_SAMPLES];
    uint16_t pcm_frame_count;
    uint32_t expected_dma_sequence;
    bool have_dma_sequence;
    bool configured;
} comp_wba_pdm_capture_t;

void comp_wba_pdm_capture_init(comp_wba_pdm_capture_t *capture,
                               const comp_wba_pdm_config_t *config);
bool comp_wba_pdm_capture_ready(const comp_wba_pdm_capture_t *capture);
void comp_wba_pdm_capture_reset_stream(comp_wba_pdm_capture_t *capture);
/* bit0=left/bit1=right actually filtered; do not qualify inactive stats. */
uint8_t comp_wba_pdm_capture_channel_mask(const comp_wba_pdm_capture_t *capture);

/* Warm the CIC/DC history using the already-discarded hardware startup span.
 * Call only before ingest after init/reset, with a whole decimation boundary
 * and at least three PCM periods. No callback runs; generated samples are
 * counted as discarded. The following DMA sequence must remain contiguous. */
bool comp_wba_pdm_capture_prime(comp_wba_pdm_capture_t *capture,
                                const uint8_t *raw,
                                size_t raw_bytes,
                                uint32_t dma_sequence);

/* Consume one completed DMA span from a deferred audio task. The byte count
 * must be even because each pair contains one byte from each microphone. */
bool comp_wba_pdm_capture_ingest(comp_wba_pdm_capture_t *capture,
                                 const uint8_t *raw,
                                 size_t raw_bytes,
                                 uint32_t dma_sequence);

/* Exactly one 10 ms frame, read in bounded copies. No PCM callback runs until
 * all source bytes have been copied and validated. A failed copy discards the
 * partial frame and resets filter history. Priming retains its usual meaning. */
bool comp_wba_pdm_capture_read_frame(comp_wba_pdm_capture_t *capture,
                                    comp_wba_pdm_read_fn_t read,
                                    void *context, size_t raw_bytes,
                                    uint32_t dma_sequence, bool priming);

const comp_wba_pdm_stats_t *comp_wba_pdm_capture_stats(
    const comp_wba_pdm_capture_t *capture);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_WBA_PDM_CAPTURE_H */
