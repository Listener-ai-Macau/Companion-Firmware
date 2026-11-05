#ifndef COMPANION_AUDIO_FEEDBACK_H
#define COMPANION_AUDIO_FEEDBACK_H

#include "speaker_playback.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_AUDIO_FEEDBACK_QUEUE_DEPTH 8u
#define COMP_AUDIO_FEEDBACK_DEFAULT_START_TIMEOUT_MS 3000u
#define COMP_AUDIO_FEEDBACK_DEFAULT_MAX_DEFERRED_MS 1500u
/* Software admission budget from a qualified visible pet frame. Actual
 * acoustic onset remains a separately measured QM21 requirement. */
#define COMP_AUDIO_FEEDBACK_PET_VISIBLE_MAX_MS 150u

typedef enum {
    COMP_AUDIO_FEEDBACK_TOUCH_CONFIRM = 0,
    COMP_AUDIO_FEEDBACK_CONNECTED,
    COMP_AUDIO_FEEDBACK_DISCONNECTED,
    COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST,
    COMP_AUDIO_FEEDBACK_RECORDING_STOPPED,
    COMP_AUDIO_FEEDBACK_ERROR,
    COMP_AUDIO_FEEDBACK_PET_GREETING,
    COMP_AUDIO_FEEDBACK_PET_CONTENT,
    COMP_AUDIO_FEEDBACK_PET_PLAYFUL,
    COMP_AUDIO_FEEDBACK_PET_SHY,
    COMP_AUDIO_FEEDBACK_EVENT_COUNT,
} comp_audio_feedback_event_t;

typedef enum {
    COMP_AUDIO_FEEDBACK_OUTCOME_NONE = 0,
    COMP_AUDIO_FEEDBACK_OUTCOME_PLAYED,
    COMP_AUDIO_FEEDBACK_OUTCOME_SILENT,
    COMP_AUDIO_FEEDBACK_OUTCOME_FAILED,
    COMP_AUDIO_FEEDBACK_OUTCOME_DROPPED,
} comp_audio_feedback_outcome_t;

typedef enum {
    COMP_AUDIO_FEEDBACK_GATE_IDLE = 0,
    COMP_AUDIO_FEEDBACK_GATE_WAITING,
    COMP_AUDIO_FEEDBACK_GATE_READY_PLAYED,
    COMP_AUDIO_FEEDBACK_GATE_READY_SILENT,
    COMP_AUDIO_FEEDBACK_GATE_READY_FAILED,
} comp_audio_feedback_start_gate_t;

typedef enum {
    COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED = 0,
    COMP_AUDIO_FEEDBACK_SUBMIT_DEDUPLICATED,
    COMP_AUDIO_FEEDBACK_SUBMIT_SUPPRESSED_QUIET,
    COMP_AUDIO_FEEDBACK_SUBMIT_SUPPRESSED_RECORDING,
    COMP_AUDIO_FEEDBACK_SUBMIT_QUEUE_FULL,
    COMP_AUDIO_FEEDBACK_SUBMIT_INVALID_STATE,
    COMP_AUDIO_FEEDBACK_SUBMIT_BAD_ARGUMENT,
    COMP_AUDIO_FEEDBACK_SUBMIT_EXPIRED,
} comp_audio_feedback_submit_result_t;

typedef void (*comp_audio_feedback_finished_fn_t)(
    void *context,
    comp_audio_feedback_event_t event,
    comp_audio_feedback_outcome_t outcome);

typedef struct {
    comp_speaker_t *speaker;
    comp_audio_feedback_finished_fn_t on_finished;
    void *context;
    uint32_t start_gate_timeout_ms;
    uint32_t max_deferred_ms;
} comp_audio_feedback_config_t;

typedef struct {
    comp_audio_feedback_event_t event;
    uint32_t submitted_ms;
    uint32_t sequence;
} comp_audio_feedback_queue_item_t;

typedef struct {
    uint32_t submitted;
    uint32_t played;
    uint32_t silent;
    uint32_t failed;
    uint32_t deduplicated;
    uint32_t suppressed_recording;
    uint32_t dropped;
    uint32_t queue_replacements;
    uint8_t queue_high_water;
} comp_audio_feedback_stats_t;

/* Public for static allocation. Treat fields after config as module-owned. */
typedef struct {
    comp_audio_feedback_config_t config;
    comp_audio_feedback_queue_item_t queue[COMP_AUDIO_FEEDBACK_QUEUE_DEPTH];
    comp_audio_feedback_stats_t stats;
    uint32_t last_accepted_ms[COMP_AUDIO_FEEDBACK_EVENT_COUNT];
    bool last_accepted_valid[COMP_AUDIO_FEEDBACK_EVENT_COUNT];
    uint32_t next_sequence;
    uint32_t start_requested_ms;
    uint8_t queue_count;
    uint8_t volume_percent;
    bool quiet;
    bool recording_active;
    bool active;
    comp_audio_feedback_event_t active_event;
    comp_audio_feedback_outcome_t active_forced_outcome;
    comp_audio_feedback_start_gate_t start_gate;
    bool gate_release_pending;
    comp_audio_feedback_outcome_t gate_release_outcome;
    bool start_cancelled;
} comp_audio_feedback_t;

void comp_audio_feedback_init(comp_audio_feedback_t *feedback,
                              const comp_audio_feedback_config_t *config);

comp_audio_feedback_submit_result_t comp_audio_feedback_submit(
    comp_audio_feedback_t *feedback,
    comp_audio_feedback_event_t event,
    uint32_t now_ms);

/* Pet-emotion cues only. Reuse the existing queue timestamp for the matching
 * visible frame; never queue a late cue after driver cleanup or task delay. */
comp_audio_feedback_submit_result_t comp_audio_feedback_submit_visible_pet(
    comp_audio_feedback_t *feedback,
    comp_audio_feedback_event_t event,
    uint32_t visible_ms,
    uint32_t now_ms);

/* Task-context only. Services the existing async speaker and starts at most
 * one queued cue. DMA completion must still be deferred to the product task. */
void comp_audio_feedback_service(comp_audio_feedback_t *feedback,
                                 uint32_t now_ms);

void comp_audio_feedback_set_quiet(comp_audio_feedback_t *feedback, bool quiet);
bool comp_audio_feedback_set_volume(comp_audio_feedback_t *feedback,
                                    uint8_t percent);
/* Retire only pet-emotion cues when their home-page intent is no longer
 * relevant. System/recording cues and the recording-start gate are retained. */
void comp_audio_feedback_cancel_pet(comp_audio_feedback_t *feedback);

/* Setting true is rejected while a recording-start gate is waiting or ready
 * but unconsumed. Stop capture first, set false, then submit RECORDING_STOPPED. */
bool comp_audio_feedback_set_recording_active(
    comp_audio_feedback_t *feedback,
    bool active);

comp_audio_feedback_start_gate_t comp_audio_feedback_start_gate(
    const comp_audio_feedback_t *feedback);
/* Returns true once the start cue has played, has been deliberately skipped by
 * quiet mode, or has failed after the speaker is no longer able to pollute the
 * capture. Consuming it resets the gate to IDLE. */
bool comp_audio_feedback_take_recording_start_gate(
    comp_audio_feedback_t *feedback,
    comp_audio_feedback_outcome_t *outcome);
/* Cancels only a WAITING request. A later speaker completion cannot turn the
 * cancelled request into a READY gate. READY outcomes remain consumable. */
bool comp_audio_feedback_cancel_recording_start(
    comp_audio_feedback_t *feedback,
    uint32_t now_ms);

bool comp_audio_feedback_busy(const comp_audio_feedback_t *feedback);
void comp_audio_feedback_get_stats(const comp_audio_feedback_t *feedback,
                                   comp_audio_feedback_stats_t *stats);
const char *comp_audio_feedback_event_name(comp_audio_feedback_event_t event);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_AUDIO_FEEDBACK_H */
