#include "companion_opus16_rt.h"
#include "companion_codec_profile.h"

#include <stdio.h>
#include <string.h>

#include "opus.h"
/* Private CTL values from opus_private.h (avoid pulling whole private header). */
#ifndef MODE_SILK_ONLY
#define MODE_SILK_ONLY 1000
#endif
#ifndef MODE_CELT_ONLY
#define MODE_CELT_ONLY 1002
#endif
#ifndef OPUS_SET_FORCE_MODE
#define OPUS_SET_FORCE_MODE_REQUEST 11002
#ifdef opus_check_int
#define OPUS_SET_FORCE_MODE(x) OPUS_SET_FORCE_MODE_REQUEST, opus_check_int(x)
#else
#define OPUS_SET_FORCE_MODE(x) OPUS_SET_FORCE_MODE_REQUEST, __opus_check_int(x)
#endif
#endif

#ifndef COMPANION_OPUS16_COMPLEXITY
#define COMPANION_OPUS16_COMPLEXITY 0
#endif

/* WBA has a 10 ms DMA-half service deadline. Its measured VOIP/SILK first
 * packet took 58 ms at 98 MHz. Use the public low-delay Opus application for
 * the WBA 16 kHz path; leave the accepted WB55/8 kHz configuration intact.
 * This remains mono 16 kbps Opus in the same COP1 container. */
#ifndef COMPANION_OPUS16_WBA_LOWDELAY
#define COMPANION_OPUS16_WBA_LOWDELAY 0
#endif
#ifndef COMPANION_OPUS16_WBA_CELT16
#define COMPANION_OPUS16_WBA_CELT16 0
#endif
#if COMPANION_OPUS16_WBA_CELT16 && !defined(OPUS_APPLICATION_RESTRICTED_CELT)
#error "WBA restricted CELT profile requires the pinned official Opus1.6 API"
#endif

#ifndef COMPANION_OPUS16_ENCODER_BYTES
#define COMPANION_OPUS16_ENCODER_BYTES 24576u
#endif

#ifndef COMPANION_OPUS8_LIVE_BITRATE_BPS
/* The realtime WB55 SILK path needs more residual detail than the former
 * 8 kbps setting once its peak-stack pitch search is disabled. 16 kbps still
 * uses only about 1.2 MB for ten minutes and fits NOR/BLE with wide margin. */
#define COMPANION_OPUS8_LIVE_BITRATE_BPS 16000
#endif

/* r126 (2026-08-06): companion_opus16_rt_init_rate_frame is now invoked from
 * recording_flash_activate_capture INSIDE a taskENTER_CRITICAL() prologue (to
 * block the syscall-prio ISR that wild-stored during activate). printf there
 * uses UART-DMA + ulTaskNotifyTake, which is a blocking API forbidden inside a
 * critical section (corrupts scheduler -> CPU lockup, seen as "encoder ready"
 * truncating at "bitr"). Gate the init diagnostics off by default so opus init
 * is silent and safe under the lock; success is still observable via the bool
 * return + the caller's capture_begin marker. Encode/flush errors retain the
 * actual Opus code in the encoder. WBA's POSIX stdout is unsupported; its
 * existing explicit UART snapshot reports this code without libc FILE I/O. */
#ifndef COMPANION_OPUS16_INIT_VERBOSE
#define COMPANION_OPUS16_INIT_VERBOSE 0
#endif
#ifndef COMPANION_OPUS16_STDIO_ERRORS
#define COMPANION_OPUS16_STDIO_ERRORS 1
#endif
#if COMPANION_OPUS16_INIT_VERBOSE
#define OPUS_INIT_PRINTF(...) printf(__VA_ARGS__)
#else
#define OPUS_INIT_PRINTF(...) do {} while (0)
#endif

static union {
  uint64_t align8;
#if COMPANION_WBA_CE_SHARED_CAPTURE
  uint8_t bytes[COMPANION_CE_ENCODER_STATE_BYTES+COMPANION_CE_DMA_BYTES];
#else
  uint8_t bytes[COMPANION_OPUS16_ENCODER_BYTES];
#endif
} s_opus_encoder_mem
#if COMPANION_OPUS16_WBA_CELT16 && COMP_WBA_INTERNAL_FLASH_KIB == 512u
    __attribute__((section(".sram1.bss"),aligned(8)))
#endif
    ;
/* Foreground-serialized ownership: an OTA queue may borrow the encoder arena
 * only between recordings. Paused recording retains encoder ownership. */
enum { OPUS_MEM_FREE=0, OPUS_MEM_ENCODER, OPUS_MEM_BORROWED };
static uint8_t s_opus_encoder_mem_owner;
#if COMPANION_WBA_CE_SHARED_CAPTURE
static void *s_dma_owner;
uint32_t *companion_opus16_rt_dma_address(size_t bytes)
{return bytes==COMPANION_CE_DMA_BYTES?(uint32_t *)(void *)(s_opus_encoder_mem.bytes+COMPANION_CE_ENCODER_STATE_BYTES):NULL;}
bool companion_opus16_rt_dma_claim(void *owner)
{
  if(!owner || s_dma_owner || s_opus_encoder_mem_owner==OPUS_MEM_BORROWED)return false;
  s_dma_owner=owner;return true;
}
void companion_opus16_rt_dma_release(void *owner)
{if(owner && owner==s_dma_owner)s_dma_owner=NULL;}
#endif
bool companion_opus16_rt_workspace_available(void)
{ return s_opus_encoder_mem_owner==OPUS_MEM_FREE
#if COMPANION_WBA_CE_SHARED_CAPTURE
    && !s_dma_owner
#endif
    ; }
void *companion_opus16_rt_workspace_borrow(size_t bytes)
{
  /* In the CE shared layout the actual arena contains encoder state plus
   * the idle DMA region. The legacy encoder-only budget is not its size.
   * workspace_available still excludes BOTH live DMA and encoder owners. */
  if (!bytes || bytes>sizeof(s_opus_encoder_mem.bytes) ||
      !companion_opus16_rt_workspace_available()) return NULL;
  s_opus_encoder_mem_owner=OPUS_MEM_BORROWED;
  return s_opus_encoder_mem.bytes;
}
void companion_opus16_rt_workspace_release(void *memory)
{
  if (memory==s_opus_encoder_mem.bytes && s_opus_encoder_mem_owner==OPUS_MEM_BORROWED)
    s_opus_encoder_mem_owner=OPUS_MEM_FREE;
}

static void write_u16_le(uint8_t *p, uint16_t v)
{
  p[0] = (uint8_t)(v & 0xFFu);
  p[1] = (uint8_t)((v >> 8) & 0xFFu);
}

static void write_u32_le(uint8_t *p, uint32_t v)
{
  p[0] = (uint8_t)(v & 0xFFu);
  p[1] = (uint8_t)((v >> 8) & 0xFFu);
  p[2] = (uint8_t)((v >> 16) & 0xFFu);
  p[3] = (uint8_t)((v >> 24) & 0xFFu);
}

static size_t write_cop1_header(companion_opus16_rt_t *rt, uint8_t *out, size_t cap)
{
  if (cap < 12u || rt == NULL) {
    return 0u;
  }
  write_u32_le(out, COMPANION_OPUS16_COP1_MAGIC);
  out[4] = 1u; /* version */
  out[5] = 1u; /* channels */
  out[6] = (uint8_t)(rt->frame_ms != 0u ? rt->frame_ms : COMPANION_OPUS16_FRAME_MS);
  out[7] = 0u;
  write_u32_le(out + 8, rt->sample_rate_hz);
  return 12u;
}

bool companion_opus16_rt_init(companion_opus16_rt_t *rt)
{
  return companion_opus16_rt_init_rate_frame(
      rt, COMPANION_OPUS16_SAMPLE_RATE_HZ, COMPANION_OPUS16_FRAME_MS);
}

bool companion_opus16_rt_init_rate(companion_opus16_rt_t *rt, uint32_t sample_rate_hz)
{
  return companion_opus16_rt_init_rate_frame(
      rt, sample_rate_hz, COMPANION_OPUS16_FRAME_MS);
}

bool companion_opus16_rt_init_rate_frame(companion_opus16_rt_t *rt,
                                         uint32_t sample_rate_hz,
                                         uint32_t frame_ms)
{
  int err = OPUS_OK;
  int need = 0;
  OpusEncoder *enc;
  uint16_t frame_samples;
  int opus_frame_dur = OPUS_FRAMESIZE_20_MS;

  if (rt == NULL) {
    return false;
  }
#if COMPANION_OPUS16_WBA_CELT16
  /* The WBA product contract is 16kHz/20ms/16kbps mono. Legacy WB's8kHz
   * SILK path remains in the default profile; never silently accept another
   * shape in this bounded CELT state allocation. */
  if (sample_rate_hz != 16000u || frame_ms != 20u) return false;
#endif
  if (sample_rate_hz != 8000u && sample_rate_hz != 12000u &&
      sample_rate_hz != 16000u && sample_rate_hz != 24000u &&
      sample_rate_hz != 48000u) {
    sample_rate_hz = COMPANION_OPUS16_SAMPLE_RATE_HZ;
  }
  if (frame_ms != 10u && frame_ms != 20u && frame_ms != 40u && frame_ms != 60u) {
    frame_ms = COMPANION_OPUS16_FRAME_MS;
  }
  if (frame_ms == 10u) {
    opus_frame_dur = OPUS_FRAMESIZE_10_MS;
  } else if (frame_ms == 40u) {
    opus_frame_dur = OPUS_FRAMESIZE_40_MS;
  } else if (frame_ms == 60u) {
    opus_frame_dur = OPUS_FRAMESIZE_60_MS;
  } else {
    opus_frame_dur = OPUS_FRAMESIZE_20_MS;
  }
  frame_samples = (uint16_t)((sample_rate_hz * frame_ms) / 1000u);
  if (frame_samples == 0u || frame_samples > COMPANION_OPUS16_PCM_ACC_MAX) {
    return false;
  }

  memset(rt, 0, sizeof(*rt));
  rt->sample_rate_hz = sample_rate_hz;
  rt->frame_samples = frame_samples;
  rt->frame_ms = (uint16_t)frame_ms;

#if COMPANION_OPUS16_WBA_CELT16
  /* Pinned1.6.1 init(NULL,...) reports the selected application's actual
   * state. The public generic get_size includes unused SILK state and is
   * deliberately not used to size the OTA-shared bounded allocation.
   * The build verifies this exact upstream implementation/profile. */
  need = opus_encoder_init(NULL,(opus_int32)sample_rate_hz,1,OPUS_APPLICATION_RESTRICTED_CELT);
#else
  need = opus_encoder_get_size(1);
#endif
  if (need <= 0 || (size_t)need >
#if COMPANION_WBA_CE_SHARED_CAPTURE
      COMPANION_CE_ENCODER_STATE_BYTES
#else
      sizeof(s_opus_encoder_mem.bytes)
#endif
      ) {
    OPUS_INIT_PRINTF("[opus16] encoder_get_size=%d cap=%u FAIL\r\n",
           need,
           (unsigned)sizeof(s_opus_encoder_mem.bytes));
    return false;
  }
  if (!companion_opus16_rt_workspace_available()) {
    OPUS_INIT_PRINTF("[opus16] encoder mem busy\r\n");
    return false;
  }

  memset(s_opus_encoder_mem.bytes, 0, (size_t)need);
  enc = (OpusEncoder *)(void *)s_opus_encoder_mem.bytes;
  err = opus_encoder_init(enc, (opus_int32)sample_rate_hz, 1,
#if COMPANION_OPUS16_WBA_CELT16
      OPUS_APPLICATION_RESTRICTED_CELT);
#else
      COMPANION_OPUS16_WBA_LOWDELAY && sample_rate_hz >= 16000u
          ? OPUS_APPLICATION_RESTRICTED_LOWDELAY : OPUS_APPLICATION_VOIP);
#endif
  if (err != OPUS_OK) {
    OPUS_INIT_PRINTF("[opus16] encoder_init err=%d rate=%lu\r\n",
           err,
           (unsigned long)sample_rate_hz);
    return false;
  }
  {
    /* Meeting 16 kHz and product 8 kHz board capture both use 16 kbps. */
    const int bitrate =
        (sample_rate_hz >= 16000u) ? 16000 : COMPANION_OPUS8_LIVE_BITRATE_BPS;
    const int cplx = (sample_rate_hz >= 16000u)
        ? (COMPANION_OPUS16_WBA_LOWDELAY ? 0 : 2) : COMPANION_OPUS16_COMPLEXITY;
    if (opus_encoder_ctl(enc, OPUS_SET_BITRATE(bitrate)) != OPUS_OK ||
        opus_encoder_ctl(enc, OPUS_SET_COMPLEXITY(cplx)) != OPUS_OK) return false;
    (void)opus_encoder_ctl(enc, OPUS_SET_SIGNAL(OPUS_SIGNAL_VOICE));
    (void)opus_encoder_ctl(enc, OPUS_SET_VBR(0));
    (void)opus_encoder_ctl(enc, OPUS_SET_DTX(0));
    (void)opus_encoder_ctl(enc, OPUS_SET_PACKET_LOSS_PERC(0));
    if (sample_rate_hz >= 16000u) {
      (void)opus_encoder_ctl(enc, OPUS_SET_BANDWIDTH(OPUS_BANDWIDTH_WIDEBAND));
      (void)opus_encoder_ctl(enc, OPUS_SET_MAX_BANDWIDTH(OPUS_BANDWIDTH_WIDEBAND));
    } else {
      (void)opus_encoder_ctl(enc, OPUS_SET_BANDWIDTH(OPUS_BANDWIDTH_NARROWBAND));
      (void)opus_encoder_ctl(enc, OPUS_SET_MAX_BANDWIDTH(OPUS_BANDWIDTH_NARROWBAND));
    }
    (void)opus_encoder_ctl(enc, OPUS_SET_INBAND_FEC(0));
    (void)opus_encoder_ctl(enc, OPUS_SET_EXPERT_FRAME_DURATION(opus_frame_dur));
    /* Product 8 kHz board capture: SILK-only is the only realtime Opus mode on
     * WB55. The bounded LIVE_FAST hooks own its peak-stack policy. */
#if !COMPANION_OPUS16_WBA_CELT16
    if (sample_rate_hz == 8000u) {
      (void)opus_encoder_ctl(enc, OPUS_SET_FORCE_MODE(MODE_SILK_ONLY));
      (void)opus_encoder_ctl(enc, OPUS_SET_FORCE_CHANNELS(1));
    }
#endif
    opus_int32 lookahead=0;
    if (opus_encoder_ctl(enc,OPUS_GET_LOOKAHEAD(&lookahead))!=OPUS_OK ||
        lookahead<0 || lookahead>UINT16_MAX) return false;
    rt->encoder_delay_samples=(uint16_t)lookahead;
    s_opus_encoder_mem_owner = OPUS_MEM_ENCODER;
    rt->encoder = enc;
    rt->ready = true;
    OPUS_INIT_PRINTF("[opus16] encoder ready need=%d bitrate=%d rate=%lu fs=%u frame_ms=%u app=voip cplx=%d\r\n",
           need,
           bitrate,
           (unsigned long)sample_rate_hz,
           (unsigned)frame_samples,
           (unsigned)frame_ms,
           cplx);
  }
  return true;
}

void companion_opus16_rt_reset(companion_opus16_rt_t *rt)
{
  if (rt == NULL) {
    return;
  }
  rt->pcm_fill = 0u;
  rt->frames_encoded = 0u;
  rt->bytes_out = 0u;
  rt->end_drained = false;
  if (rt->encoder != NULL) {
    (void)opus_encoder_ctl((OpusEncoder *)rt->encoder, OPUS_RESET_STATE);
  }
}

void companion_opus16_rt_destroy(companion_opus16_rt_t *rt)
{
  if (rt == NULL) {
    return;
  }
  if (rt->encoder != NULL) {
    rt->encoder = NULL;
    if (s_opus_encoder_mem_owner==OPUS_MEM_ENCODER) s_opus_encoder_mem_owner=OPUS_MEM_FREE;
  }
  rt->ready = false;
  rt->pcm_fill = 0u;
}

static size_t encode_one_frame(
    companion_opus16_rt_t *rt,
    uint8_t *out_buf,
    size_t out_cap)
{
  int n;

  /* Encode after the two-byte COP1 length directly into the caller-owned
   * packet.  The former second 400-byte static packet duplicated this exact
   * lifetime for every build, even though the service already owns a bounded
   * output packet.  Require the complete codec ceiling before entering Opus
   * so a short caller buffer cannot advance encoder state and then lose the
   * encoded frame. */
  if (out_cap < 2u + COMPANION_OPUS16_MAX_PACKET ||
      rt->frame_samples == 0u) {
    return 0u;
  }
  companion_codec_profile_begin();
  n = opus_encode(
      (OpusEncoder *)rt->encoder,
      rt->pcm_acc,
      (int)rt->frame_samples,
      out_buf + 2u,
      (opus_int32)COMPANION_OPUS16_MAX_PACKET);
  companion_codec_profile_end();
  if (n <= 0) {
    rt->last_encode_error=(int16_t)(n>=INT16_MIN&&n<0?n:OPUS_INTERNAL_ERROR);
#if COMPANION_OPUS16_STDIO_ERRORS
    static uint8_t s_enc_err_logs;
    if (s_enc_err_logs < 4u) {
      printf("[opus16] encode err=%d frame_samples=%u\r\n",
             n,
             (unsigned)rt->frame_samples);
      s_enc_err_logs++;
    }
#endif
    return 0u;
  }
  rt->last_encode_error=0;
  write_u16_le(out_buf, (uint16_t)n);
  rt->frames_encoded++;
  rt->bytes_out += (uint32_t)n + 2u;
  rt->pcm_fill = 0u;
  return (size_t)n + 2u;
}

size_t companion_opus16_rt_encode(
    companion_opus16_rt_t *rt,
    const int16_t *pcm,
    size_t pcm_samples,
    uint8_t *out_buf,
    size_t out_cap,
    bool write_header)
{
  size_t out_used = 0u;
  size_t i = 0u;

  if (rt == NULL || !rt->ready || rt->end_drained || pcm == NULL || out_buf == NULL) {
    return 0u;
  }
  if (write_header) {
    size_t h = write_cop1_header(rt, out_buf, out_cap);
    if (h == 0u) {
      return 0u;
    }
    out_used += h;
  }

  while (i < pcm_samples) {
    size_t need = (size_t)rt->frame_samples - (size_t)rt->pcm_fill;
    size_t take = pcm_samples - i;
    if (take > need) {
      take = need;
    }
    memcpy(
        &rt->pcm_acc[rt->pcm_fill],
        &pcm[i],
        take * sizeof(int16_t));
    rt->pcm_fill = (uint16_t)(rt->pcm_fill + (uint16_t)take);
    i += take;
    if (rt->pcm_fill >= rt->frame_samples) {
      size_t n = encode_one_frame(rt, out_buf + out_used, out_cap - out_used);
      if (n == 0u) {
        break;
      }
      out_used += n;
    }
  }
  return out_used;
}

size_t companion_opus16_rt_flush(
    companion_opus16_rt_t *rt,
    uint8_t *out_buf,
    size_t out_cap)
{
  if (rt == NULL || !rt->ready || rt->pcm_fill == 0u) {
    return 0u;
  }
  while (rt->pcm_fill < rt->frame_samples) {
    rt->pcm_acc[rt->pcm_fill++] = 0;
  }
  return encode_one_frame(rt, out_buf, out_cap);
}

size_t companion_opus16_rt_finish_exact(
    companion_opus16_rt_t *rt,uint8_t *out_buf,size_t out_cap)
{
  if (rt==NULL || !rt->ready || rt->end_drained || out_buf==NULL ||
      out_cap<2u+COMPANION_OPUS16_MAX_PACKET) return 0u;
  /* This promise belongs to the product's160-sample input blocks, not the
   * generic Opus wrapper. A single packet must contain all delayed real PCM. */
  if (rt->sample_rate_hz!=16000u || rt->frame_samples!=320u ||
      rt->frame_ms!=20u || (rt->pcm_fill!=0u && rt->pcm_fill!=160u) ||
      rt->encoder_delay_samples>160u) return 0u;
  if (rt->frames_encoded==0u && rt->pcm_fill==0u) {
    rt->end_drained=true;
    return 0u;
  }
  while (rt->pcm_fill<rt->frame_samples) rt->pcm_acc[rt->pcm_fill++]=0;
  size_t written=encode_one_frame(rt,out_buf,out_cap);
  if (written!=0u) rt->end_drained=true;
  return written;
}
