#ifndef COMPANION_WBA_RECORDING_SERVICE_H
#define COMPANION_WBA_RECORDING_SERVICE_H

#include "companion_opus16_rt.h"
#include "companion_recording_journal.h"
#include "companion_duration_stats.h"
#include "denzic_audio_recording_v1.h"
#include "../update/wba_storage_layout.h"

#include "../core/companion_sha256.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_WBA_RECORDING_CODEC_OPUS16 3u
#define COMP_WBA_RECORDING_SOURCE_MIC_SAI 1u
#define COMP_WBA_RECORDING_PCM_FRAME_SAMPLES 160u
#define COMP_WBA_RECORDING_PCM_RING_SLOTS 8u
#define COMP_WBA_RECORDING_STAGE_BYTES 1024u
#define COMP_WBA_RECORDING_PACKET_BYTES (COMPANION_OPUS16_MAX_PACKET + 2u)
#define COMP_WBA_RECORDING_MIN_PARTITION_BASE COMP_WBA_NOR_RECORDING_BASE

typedef enum {
    COMP_WBA_RECORDING_UNBOUND = 0,
    COMP_WBA_RECORDING_IDLE,
    COMP_WBA_RECORDING_PREPARING,
    COMP_WBA_RECORDING_READY,
    COMP_WBA_RECORDING_CAPTURING,
    COMP_WBA_RECORDING_STOPPING,
    COMP_WBA_RECORDING_TRANSFER_READY,
    COMP_WBA_RECORDING_FAULT,
} comp_wba_recording_service_state_t;

typedef enum {
    COMP_WBA_RECORDING_STOP_NONE = 0,
    COMP_WBA_RECORDING_STOP_USER,
    COMP_WBA_RECORDING_STOP_STORAGE_LIMIT,
    COMP_WBA_RECORDING_STOP_FAILURE,
} comp_wba_recording_stop_reason_t;

typedef enum {
    COMP_WBA_RECORDING_FAULT_NONE = 0,
    COMP_WBA_RECORDING_FAULT_PLATFORM_CAPTURE,
    COMP_WBA_RECORDING_FAULT_PCM_OVERFLOW,
    COMP_WBA_RECORDING_FAULT_DEADLINE,
    COMP_WBA_RECORDING_FAULT_CODEC,
    COMP_WBA_RECORDING_FAULT_STORAGE_IO,
    COMP_WBA_RECORDING_FAULT_MIC_CONTROL,
    COMP_WBA_RECORDING_FAULT_STORAGE_FULL,
} comp_wba_recording_fault_reason_t;

typedef bool (*comp_wba_recording_mic_control_fn_t)(void *context,
                                                     bool enabled);
typedef uint32_t (*comp_wba_recording_now_ms_fn_t)(void *context);
typedef uint32_t (*comp_wba_recording_unix_s_fn_t)(void *context);
typedef void (*comp_wba_recording_report_fn_t)(
    void *context,
    uint32_t token,
    denzic_audio_recording_state_v1_t state,
    bool capture_active);

typedef struct {
    comp_recording_journal_t *journal;
    uint32_t partition_base_address;
    uint32_t reserve_bytes;
    comp_wba_recording_mic_control_fn_t mic_control;
    comp_wba_recording_now_ms_fn_t now_ms;
    comp_wba_recording_unix_s_fn_t unix_s;
    comp_wba_recording_report_fn_t report;
    void *context;
    /* Actual-board foreground budget. Exceeding it while the microphone runs
     * fails the recording rather than hiding likely DMA half loss. */
    uint16_t foreground_budget_ms;
} comp_wba_recording_service_config_t;

typedef struct {
    uint32_t prepare_requests;
    uint32_t prepared;
    uint32_t starts;
    uint32_t stops;
    uint32_t cancellations;
    uint32_t finalized;
    uint32_t failures;
    uint32_t erase_sectors;
    uint32_t program_calls;
    uint32_t pcm_frames;
    uint32_t dropped_pcm_frames;
    uint32_t encoded_frames;
    uint32_t committed_bytes;
    uint32_t max_ring_depth;
    uint32_t max_poll_ms;
    uint32_t max_encode_ms;
    uint32_t max_program_ms;
    uint32_t budget_violations;
    uint32_t storage_limit_stops;
    uint32_t trim_failures;
    uint32_t external_capture_faults;
    comp_duration_stats_t encode_duration;
} comp_wba_recording_service_stats_t;

typedef companion_sha256_t comp_wba_recording_sha256_t;

/* Public for static allocation. Treat fields after config as service-owned. */
typedef struct {
    comp_wba_recording_service_config_t config;
    comp_wba_recording_service_stats_t stats;
    companion_opus16_rt_t codec;
    comp_recording_journal_entry_t entry;
    comp_wba_recording_sha256_t sha256;
    int16_t pcm_ring[COMP_WBA_RECORDING_PCM_RING_SLOTS]
                    [COMP_WBA_RECORDING_PCM_FRAME_SAMPLES];
    uint8_t stage[COMP_WBA_RECORDING_STAGE_BYTES];
    uint8_t packet[COMP_WBA_RECORDING_PACKET_BYTES];
    uint8_t sha256_digest[COMP_RECORDING_JOURNAL_SHA256_BYTES];
    uint32_t token;
    uint32_t erase_offset;
    uint32_t committed_bytes;
    uint32_t checkpoint_bytes;
    uint32_t checkpoint_interval_bytes;
    uint32_t payload_limit;
    uint32_t content_crc32;
    uint32_t durable_frames;
    uint16_t durable_packet_remaining;
    uint16_t durable_length_word;
    uint8_t durable_header_remaining;
    uint8_t durable_length_bytes;
    uint32_t capture_started_ms;
    uint16_t ring_read;
    uint16_t ring_write;
    uint16_t ring_count;
    uint16_t stage_length;
    comp_wba_recording_service_state_t state;
    comp_wba_recording_stop_reason_t last_stop_reason;
    comp_wba_recording_fault_reason_t last_fault_reason;
    bool encoder_initialized;
    bool microphone_active;
    bool flush_complete;
    bool fault_reported;
    bool pcm_overflowed;
} comp_wba_recording_service_t;

bool comp_wba_recording_service_init(
    comp_wba_recording_service_t *service,
    const comp_wba_recording_service_config_t *config);

/* Two-phase runtime ports: prepare reserves and pre-erases before any cue;
 * ready becomes true only after all sectors and codec setup have completed. */
bool comp_wba_recording_service_prepare_port(void *context, uint32_t token);
bool comp_wba_recording_service_ready_port(void *context, uint32_t token);
bool comp_wba_recording_service_control_port(void *context, bool start,
                                              uint32_t token);

/* Foreground/task context. Never call from the DMA ISR. Exactly 160 samples at
 * 16 kHz are accepted from the WBA PDM capture layer. */
bool comp_wba_recording_service_pcm(void *context, const int16_t *samples,
                                    size_t count, uint32_t sample_rate_hz);

/* Foreground notification for DMA stale halves, HAL errors, capture queue
 * overflow, or rejected PDM processing.  It stops capture and deliberately
 * leaves the journal entry WRITING for explicit reboot recovery. */
bool comp_wba_recording_service_capture_fault(
    void *context, uint32_t token,
    comp_wba_recording_fault_reason_t reason);

/* Performs at most one normal erase, encode, page program, flush or finalize
 * unit. Fault recovery stops the microphone before checkpointing/verifying
 * the complete programmed prefix; it never claims a normal STOP result. */
comp_wba_recording_service_state_t comp_wba_recording_service_poll(
    comp_wba_recording_service_t *service);

bool comp_wba_recording_service_recover(
    comp_wba_recording_service_t *service);
/* Boot recovery: validate the durable identity, then seal complete COP1
 * packets. Unknown/legacy/unverified writes stay reserved, never scan-adopted.
 * Recovered entries are explicitly marked incomplete, not normal STOP results. */
bool comp_wba_recording_salvage(comp_recording_journal_t *,uint32_t *recovered,uint32_t *unresolved);
void comp_wba_recording_service_get_stats(
    const comp_wba_recording_service_t *service,
    comp_wba_recording_service_stats_t *stats);
const comp_recording_journal_entry_t *comp_wba_recording_service_entry(
    const comp_wba_recording_service_t *service);
/* RAM snapshot of NOR bytes whose program call completed. A live prefix can
 * end inside an Opus packet; Type decodes only complete packets. Never marks
 * the journal finalized, never supplies a final SHA, and never permits ACK.
 * Survives BLE disconnect while this capture owner lives, not MCU reset. */
bool comp_wba_recording_service_live_entry(
    const comp_wba_recording_service_t *service,
    comp_recording_journal_entry_t *entry);
comp_wba_recording_stop_reason_t comp_wba_recording_service_stop_reason(
    const comp_wba_recording_service_t *service);
comp_wba_recording_fault_reason_t comp_wba_recording_service_fault_reason(
    const comp_wba_recording_service_t *service);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_WBA_RECORDING_SERVICE_H */
