#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Product default container: 16 kHz mono Opus, 20 ms frames (auto_fill / wire).
 * Live-mic may init at 8 kHz / 40 ms for realtime budget; COP1 fields tell host. */
#define COMPANION_OPUS16_SAMPLE_RATE_HZ 16000u
#define COMPANION_OPUS16_FRAME_MS 20u
#define COMPANION_OPUS16_FRAME_SAMPLES \
  ((COMPANION_OPUS16_SAMPLE_RATE_HZ * COMPANION_OPUS16_FRAME_MS) / 1000u)
#ifndef COMPANION_OPUS16_BITRATE_BPS
/* Legacy 16 kHz default retained for resource/fixture callers. Live 8 kHz
 * capture has its own 16 kbps quality contract in companion_opus16_rt.c. */
#define COMPANION_OPUS16_BITRATE_BPS 8000
#endif
#define COMPANION_OPUS16_MAX_PACKET 400u
#ifndef COMPANION_WBA_CE_SHARED_CAPTURE
#define COMPANION_WBA_CE_SHARED_CAPTURE 0
#endif
#if COMPANION_WBA_CE_SHARED_CAPTURE
/* Restricted CELT16/CBR only: the codec and COP1 page contract require40B. */
#undef COMPANION_OPUS16_MAX_PACKET
#define COMPANION_OPUS16_MAX_PACKET 40u
#if UINTPTR_MAX > UINT32_MAX
/* Host verification has two wider pointers in the upstream CELT state.
 * The actual32-bit CE allocation remains5456B, not the host layout. */
#define COMPANION_CE_ENCODER_STATE_BYTES 5472u
#else
#define COMPANION_CE_ENCODER_STATE_BYTES 5456u
#endif
#define COMPANION_CE_DMA_BYTES 7680u
#endif
/* Max PCM accumulator: fits 16 kHz/20 ms or live 8 kHz/40 ms (both 320 samples). */
#define COMPANION_OPUS16_PCM_ACC_MAX 320u

/* COP1 container: Companion Opus Packet stream v1 (Type can decode). */
#define COMPANION_OPUS16_COP1_MAGIC 0x31504F43u /* 'COP1' LE */
/* Bytes: magic u32 LE, version u8=1, channels u8=1, frame_ms u8, reserved u8=0,
 * sample_rate u32 LE, then packets: u16 LE len + bytes. */

typedef struct companion_opus16_rt {
  void *encoder; /* OpusEncoder* */
  int16_t pcm_acc[COMPANION_OPUS16_PCM_ACC_MAX];
  uint16_t pcm_fill;
  uint16_t frame_samples;
  uint16_t frame_ms;
  int16_t last_encode_error; /* Uses existing32-bit alignment padding. */
  uint32_t sample_rate_hz;
  uint32_t frames_encoded;
  uint32_t bytes_out;
  bool ready;
  bool end_drained;
  uint16_t encoder_delay_samples; /* Uses the former tail alignment padding. */
} companion_opus16_rt_t;

#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
_Static_assert(sizeof(companion_opus16_rt_t)==(UINTPTR_MAX>UINT32_MAX?672u:668u),
               "exact finish must not grow the shared capture state");
#endif

/* Foreground calls only. Borrow blocks init; encoder ownership blocks borrow,
 * including pause, drain and STOP finalization. Release accepts only this arena. */
bool companion_opus16_rt_workspace_available(void);
void *companion_opus16_rt_workspace_borrow(size_t bytes);
void companion_opus16_rt_workspace_release(void *memory);
#if COMPANION_WBA_CE_SHARED_CAPTURE
/* DMA and the encoder occupy disjoint parts of the capture view. OTA may
 * borrow the whole view only after both owners have retired. Address is
 * stable across leases; configuring a DMA node does not acquire ownership. */
uint32_t *companion_opus16_rt_dma_address(size_t bytes);
bool companion_opus16_rt_dma_claim(void *owner);
void companion_opus16_rt_dma_release(void *owner);
#endif
bool companion_opus16_rt_init(companion_opus16_rt_t *rt);
/* Live-mic realtime: pass 8000 (+ optional 40 ms frames) for M4 budget (codec=3). */
bool companion_opus16_rt_init_rate(companion_opus16_rt_t *rt, uint32_t sample_rate_hz);
bool companion_opus16_rt_init_rate_frame(companion_opus16_rt_t *rt,
                                         uint32_t sample_rate_hz,
                                         uint32_t frame_ms);
void companion_opus16_rt_reset(companion_opus16_rt_t *rt);
void companion_opus16_rt_destroy(companion_opus16_rt_t *rt);

size_t companion_opus16_rt_encode(
    companion_opus16_rt_t *rt,
    const int16_t *pcm,
    size_t pcm_samples,
    uint8_t *out_buf,
    size_t out_cap,
    bool write_header);

size_t companion_opus16_rt_flush(
    companion_opus16_rt_t *rt,
    uint8_t *out_buf,
    size_t out_cap);

/* New explicit-boundary recordings only. With160-sample product input blocks,
 * one final20ms packet pads a partial block or drains the codec lookahead.
 * The caller must persist the real accepted sample count separately from
 * encoded frames. Legacy flush/container policy is deliberately unchanged.
 * No state change on an undersized output; repeated completed finish returns0.
 * A nonempty admitted recording must yield exactly one packet or fail. */
size_t companion_opus16_rt_finish_exact(
    companion_opus16_rt_t *rt, uint8_t *out_buf, size_t out_cap);

#ifdef __cplusplus
}
#endif
