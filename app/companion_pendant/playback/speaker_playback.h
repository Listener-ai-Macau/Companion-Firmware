#ifndef COMPANION_SPEAKER_PLAYBACK_H
#define COMPANION_SPEAKER_PLAYBACK_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Portable MAX98357A-facing audio contract.  The board adapter configures
 * standard I2S, 16-bit left/right slots and 32 BCLK periods per LRCLK. */
#define COMP_SPEAKER_SAMPLE_RATE_HZ 16000u
#define COMP_SPEAKER_BLOCK_FRAMES 64u
#ifndef COMP_SPEAKER_CUES_ONLY
#define COMP_SPEAKER_CUES_ONLY 0
#endif
#if COMP_SPEAKER_CUES_ONLY
/* WBA product controls use finite cues only. The IRQ lookahead is one
 * stereo block, not a512-frame mono streaming queue. Keep the actual block,
 * sample rate, sample generator, gain and DMA completion path unchanged. */
#define COMP_SPEAKER_FIFO_FRAMES (COMP_SPEAKER_BLOCK_FRAMES * 2u)
#else
#define COMP_SPEAKER_FIFO_FRAMES 512u
#endif
#define COMP_SPEAKER_CHANNELS 2u

typedef enum {
    COMP_SPEAKER_STATE_SHUTDOWN = 0,
    COMP_SPEAKER_STATE_STARTING,
    COMP_SPEAKER_STATE_PLAYING,
    COMP_SPEAKER_STATE_STOPPING,
    COMP_SPEAKER_STATE_FAULT,
} comp_speaker_state_t;

typedef enum {
    COMP_SPEAKER_OK = 0,
    COMP_SPEAKER_BAD_ARGUMENT,
    COMP_SPEAKER_BUSY,
    COMP_SPEAKER_NOT_RUNNING,
    COMP_SPEAKER_IO_ERROR,
} comp_speaker_result_t;

typedef enum {
    COMP_SPEAKER_CUE_CONFIRM = 0,
    COMP_SPEAKER_CUE_RECORDING_STARTED,
    COMP_SPEAKER_CUE_RECORDING_STOPPED,
    COMP_SPEAKER_CUE_ERROR,
    /* Existing wire IDs0..3 retain their meaning. FW443 additionally accepts
     * these explicit pet audition IDs4..7 on the encrypted speaker control. */
    COMP_SPEAKER_CUE_PET_GREETING,
    COMP_SPEAKER_CUE_PET_CONTENT,
    COMP_SPEAKER_CUE_PET_PLAYFUL,
    COMP_SPEAKER_CUE_PET_SHY,
    /* Explicit local diagnostic only; encrypted product IDs remain0..7. */
    COMP_SPEAKER_CUE_REFERENCE_1K, COMP_SPEAKER_CUE_REFERENCE_1500,
    COMP_SPEAKER_CUE_REFERENCE_2K,
} comp_speaker_cue_t;

/* Authored nonverbal clips use the same finite cue/volume/quiet path.
 * Data/descriptors must remain immutable and memory-readable for the complete
 * library binding lifetime. This is not an external-NOR reader: cue lookahead
 * runs in the DMA IRQ, where SPI reads and mutable/temporary storage are unsafe.
 * Fixed16kHz mono. No looping, arbitrary streaming or dynamic allocation. */
#define COMP_SPEAKER_CLIP_MIN_FRAMES 128u
#define COMP_SPEAKER_CLIP_MAX_FRAMES 8000u
#define COMP_SPEAKER_CLIP_CUE_COUNT 8u
typedef enum {
    COMP_SPEAKER_CLIP_NONE = 0,
    COMP_SPEAKER_CLIP_PCM16_LE,
    COMP_SPEAKER_CLIP_IMA_ADPCM,
} comp_speaker_clip_format_t;
typedef struct {
    const uint8_t *data;
    uint16_t frames;
    uint16_t bytes;
    int16_t initial_predictor;
    uint8_t initial_step_index;
    uint8_t format;
} comp_speaker_clip_t;
typedef struct {
    /* Only confirm0/pet4..7 may override; slots1..3 stay empty. */
    comp_speaker_clip_t cues[COMP_SPEAKER_CLIP_CUE_COUNT];
} comp_speaker_cue_library_t;

/* set_amplifier_enabled owns only the logical MAX98357A SD_MODE level.  Its
 * board implementation may route that level through an I/O expander.
 * submit_i2s must start one bounded asynchronous transfer and return quickly;
 * it must retain neither the pointer nor the samples after tx_complete(). */
typedef bool (*comp_speaker_set_amplifier_enabled_fn_t)(void *context,
                                                        bool enabled);
typedef bool (*comp_speaker_submit_i2s_fn_t)(void *context,
                                             const int16_t *stereo_pcm,
                                             size_t frame_count);
typedef void (*comp_speaker_activity_fn_t)(void *context, bool active);

typedef struct {
    comp_speaker_set_amplifier_enabled_fn_t set_amplifier_enabled;
    comp_speaker_submit_i2s_fn_t submit_i2s;
    comp_speaker_activity_fn_t set_playback_active;
    void *context;
} comp_speaker_config_t;

typedef struct {
    comp_speaker_config_t config;
    volatile comp_speaker_state_t state;
    comp_speaker_result_t last_error;
    volatile uint8_t volume_percent;
    volatile bool muted;
    volatile bool tx_pending;
    /* Block metadata/gain/phase have one audio owner. WBA publishes final
     * completion with DMB; foreground acquires it under an IRQ mask before
     * reading these fields. Live foreground controls remain volatile. */
    bool pending_starts_audio;
    bool pending_finishes_audio;
    volatile bool stop_requested;
    volatile bool drain_requested;
    volatile bool cue_active;
    bool pet_voice;
    const comp_speaker_cue_library_t *cue_library;
    comp_speaker_cue_t cue;
    uint16_t fifo_head;
    uint16_t fifo_count;
    uint16_t cue_frames_remaining;
    uint16_t cue_frames_total;
    uint32_t cue_phase;
    int32_t current_gain_q15;
    int32_t target_gain_q15;
    int16_t fifo[COMP_SPEAKER_FIFO_FRAMES];
    int16_t tx_stereo[COMP_SPEAKER_BLOCK_FRAMES * COMP_SPEAKER_CHANNELS];
    volatile uint32_t submitted_blocks;
    volatile uint32_t completed_blocks;
    volatile uint32_t played_frames;
    /* Foreground-only ownership generation, advanced for every new stream or
     * cue. A delayed cancel must never stop a later playback owner. */
    uint32_t playback_generation;
    uint32_t clipped_samples;
    uint32_t underruns;
} comp_speaker_t;

void comp_speaker_init(comp_speaker_t *speaker,
                       const comp_speaker_config_t *config);
bool comp_speaker_ready(const comp_speaker_t *speaker);
/* Opt in while idle. Existing board callers retain their original cues. */
comp_speaker_result_t comp_speaker_set_pet_voice(comp_speaker_t *speaker,bool enabled);
/* Bind/clear only while idle; malformed libraries leave the old binding intact.
 * No default library is installed by this API. Unbound cues retain their exact
 * legacy generator. Library data is authored/trusted, never a wire pointer. */
comp_speaker_result_t comp_speaker_set_cue_library(
    comp_speaker_t *speaker,const comp_speaker_cue_library_t *library);


#if !COMP_SPEAKER_CUES_ONLY
comp_speaker_result_t comp_speaker_start_stream(comp_speaker_t *speaker);
size_t comp_speaker_write_pcm16(comp_speaker_t *speaker,
                                const int16_t *mono_pcm,
                                size_t frame_count);
#endif /* PCM streaming is absent in the explicit cue-only profile. */
comp_speaker_result_t comp_speaker_play_cue(comp_speaker_t *speaker,
                                            comp_speaker_cue_t cue);
comp_speaker_result_t comp_speaker_stop(comp_speaker_t *speaker, bool drain);
comp_speaker_result_t comp_speaker_set_volume(comp_speaker_t *speaker,
                                              uint8_t percent);
void comp_speaker_set_muted(comp_speaker_t *speaker, bool muted);

/* Call from the product task to start at most one DMA block. */
bool comp_speaker_service(comp_speaker_t *speaker);
/* WBA cue-only DMA lookahead. These two helpers do no I/O or callbacks.
 * The half-complete ISR prepares into the otherwise unused PCM FIFO; the
 * complete ISR retires the old block and copies that lookahead into tx_stereo.
 * The board must submit the next DMA immediately and count it only on success.
 * Stream PCM keeps the original foreground service path. */
#define COMP_SPEAKER_CUE_PREFILLED 1u
#define COMP_SPEAKER_CUE_PREFILL_FINAL 2u
uint8_t comp_speaker_cue_prefill(comp_speaker_t *speaker);
bool comp_speaker_cue_advance(comp_speaker_t *speaker, uint8_t prefilled);
/* Call from the product task after the I2S/SAI DMA IRQ has published a
 * completion/error flag. This may advance playback and call board callbacks
 * such as an I/O-expander-backed amplifier enable, so it is not ISR-safe. */
void comp_speaker_tx_complete(comp_speaker_t *speaker, bool success);

bool comp_speaker_active(const comp_speaker_t *speaker);
#if !COMP_SPEAKER_CUES_ONLY
size_t comp_speaker_writable_frames(const comp_speaker_t *speaker);
#endif
const char *comp_speaker_state_name(comp_speaker_state_t state);
const char *comp_speaker_result_name(comp_speaker_result_t result);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_SPEAKER_PLAYBACK_H */
