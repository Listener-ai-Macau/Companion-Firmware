#include "audio_feedback.h"

#include <stddef.h>
#include <string.h>

static uint8_t priority(comp_audio_feedback_event_t event)
{
    switch (event) {
    case COMP_AUDIO_FEEDBACK_ERROR:
    case COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST:
        return 4u;
    case COMP_AUDIO_FEEDBACK_RECORDING_STOPPED:
        return 3u;
    case COMP_AUDIO_FEEDBACK_CONNECTED:
    case COMP_AUDIO_FEEDBACK_DISCONNECTED:
        return 2u;
    case COMP_AUDIO_FEEDBACK_TOUCH_CONFIRM:
    case COMP_AUDIO_FEEDBACK_PET_GREETING:
    case COMP_AUDIO_FEEDBACK_PET_CONTENT:
    case COMP_AUDIO_FEEDBACK_PET_PLAYFUL:
    case COMP_AUDIO_FEEDBACK_PET_SHY:
        return 1u;
    default:
        return 0u;
    }
}

static uint32_t cooldown_ms(comp_audio_feedback_event_t event)
{
    switch (event) {
    case COMP_AUDIO_FEEDBACK_TOUCH_CONFIRM:
        return 250u;
    case COMP_AUDIO_FEEDBACK_PET_GREETING:
    case COMP_AUDIO_FEEDBACK_PET_CONTENT:
    case COMP_AUDIO_FEEDBACK_PET_PLAYFUL:
    case COMP_AUDIO_FEEDBACK_PET_SHY:
        return 1500u;
    case COMP_AUDIO_FEEDBACK_CONNECTED:
    case COMP_AUDIO_FEEDBACK_DISCONNECTED:
        return 1000u;
    case COMP_AUDIO_FEEDBACK_ERROR:
        return 500u;
    default:
        return 0u;
    }
}

static bool nonessential_during_recording(comp_audio_feedback_event_t event)
{
    return event == COMP_AUDIO_FEEDBACK_TOUCH_CONFIRM ||
           event == COMP_AUDIO_FEEDBACK_CONNECTED ||
           event == COMP_AUDIO_FEEDBACK_DISCONNECTED ||
           (event>=COMP_AUDIO_FEEDBACK_PET_GREETING && event<=COMP_AUDIO_FEEDBACK_PET_SHY);
}

static bool pet_emotion_cue(comp_audio_feedback_event_t event)
{
    return event >= COMP_AUDIO_FEEDBACK_PET_GREETING &&
           event <= COMP_AUDIO_FEEDBACK_PET_SHY;
}

static comp_speaker_cue_t cue_for_event(comp_audio_feedback_event_t event)
{
    switch (event) {
    case COMP_AUDIO_FEEDBACK_TOUCH_CONFIRM:
        return COMP_SPEAKER_CUE_CONFIRM;
    case COMP_AUDIO_FEEDBACK_PET_GREETING:return COMP_SPEAKER_CUE_PET_GREETING;
    case COMP_AUDIO_FEEDBACK_PET_CONTENT:return COMP_SPEAKER_CUE_PET_CONTENT;
    case COMP_AUDIO_FEEDBACK_PET_PLAYFUL:return COMP_SPEAKER_CUE_PET_PLAYFUL;
    case COMP_AUDIO_FEEDBACK_PET_SHY:return COMP_SPEAKER_CUE_PET_SHY;
    case COMP_AUDIO_FEEDBACK_CONNECTED:
    case COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST:
        return COMP_SPEAKER_CUE_RECORDING_STARTED;
    case COMP_AUDIO_FEEDBACK_DISCONNECTED:
    case COMP_AUDIO_FEEDBACK_RECORDING_STOPPED:
        return COMP_SPEAKER_CUE_RECORDING_STOPPED;
    case COMP_AUDIO_FEEDBACK_ERROR:
    default:
        return COMP_SPEAKER_CUE_ERROR;
    }
}

static void notify(comp_audio_feedback_t *feedback,
                   comp_audio_feedback_event_t event,
                   comp_audio_feedback_outcome_t outcome)
{
    if (outcome == COMP_AUDIO_FEEDBACK_OUTCOME_PLAYED) {
        feedback->stats.played++;
    } else if (outcome == COMP_AUDIO_FEEDBACK_OUTCOME_SILENT) {
        feedback->stats.silent++;
    } else if (outcome == COMP_AUDIO_FEEDBACK_OUTCOME_FAILED) {
        feedback->stats.failed++;
    } else if (outcome == COMP_AUDIO_FEEDBACK_OUTCOME_DROPPED) {
        feedback->stats.dropped++;
    }
    if (feedback->config.on_finished != NULL) {
        feedback->config.on_finished(feedback->config.context, event, outcome);
    }
}

static void resolve_start_gate(comp_audio_feedback_t *feedback,
                               comp_audio_feedback_outcome_t outcome)
{
    switch (outcome) {
    case COMP_AUDIO_FEEDBACK_OUTCOME_PLAYED:
        feedback->start_gate = COMP_AUDIO_FEEDBACK_GATE_READY_PLAYED;
        break;
    case COMP_AUDIO_FEEDBACK_OUTCOME_SILENT:
        feedback->start_gate = COMP_AUDIO_FEEDBACK_GATE_READY_SILENT;
        break;
    default:
        feedback->start_gate = COMP_AUDIO_FEEDBACK_GATE_READY_FAILED;
        outcome = COMP_AUDIO_FEEDBACK_OUTCOME_FAILED;
        break;
    }
    notify(feedback, COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST, outcome);
}

static void remove_queue_index(comp_audio_feedback_t *feedback, uint8_t index)
{
    if (index >= feedback->queue_count) {
        return;
    }
    for (uint8_t cursor = index; cursor + 1u < feedback->queue_count; ++cursor) {
        feedback->queue[cursor] = feedback->queue[cursor + 1u];
    }
    feedback->queue_count--;
}

static bool queued(const comp_audio_feedback_t *feedback,
                   comp_audio_feedback_event_t event)
{
    if (feedback->active && feedback->active_event == event) {
        return true;
    }
    for (uint8_t index = 0u; index < feedback->queue_count; ++index) {
        if (feedback->queue[index].event == event) {
            return true;
        }
    }
    return false;
}

static int select_next(const comp_audio_feedback_t *feedback)
{
    int selected = -1;
    uint8_t selected_priority = 0u;
    uint32_t selected_sequence = 0u;

    for (uint8_t index = 0u; index < feedback->queue_count; ++index) {
        const comp_audio_feedback_queue_item_t *item = &feedback->queue[index];
        const uint8_t item_priority = priority(item->event);
        if (selected < 0 || item_priority > selected_priority ||
            (item_priority == selected_priority &&
             item->sequence < selected_sequence)) {
            selected = index;
            selected_priority = item_priority;
            selected_sequence = item->sequence;
        }
    }
    return selected;
}

static void finish_active(comp_audio_feedback_t *feedback,
                          comp_audio_feedback_outcome_t outcome)
{
    const comp_audio_feedback_event_t event = feedback->active_event;
    if (feedback->active_forced_outcome != COMP_AUDIO_FEEDBACK_OUTCOME_NONE) {
        outcome = feedback->active_forced_outcome;
    }
    feedback->active = false;
    feedback->active_forced_outcome = COMP_AUDIO_FEEDBACK_OUTCOME_NONE;
    if (event == COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST) {
        if (feedback->start_cancelled) {
            feedback->start_cancelled = false;
            notify(feedback, event, COMP_AUDIO_FEEDBACK_OUTCOME_DROPPED);
        } else {
            resolve_start_gate(feedback, outcome);
        }
    } else {
        notify(feedback, event, outcome);
    }
}

static void drop_deferred_nonessential(comp_audio_feedback_t *feedback,
                                       uint32_t now_ms)
{
    for (uint8_t index = 0u; index < feedback->queue_count;) {
        const comp_audio_feedback_queue_item_t *item = &feedback->queue[index];
        const uint32_t age = now_ms - item->submitted_ms;
        const bool expired = pet_emotion_cue(item->event) ?
            age > COMP_AUDIO_FEEDBACK_PET_VISIBLE_MAX_MS :
            age >= feedback->config.max_deferred_ms;
        if (nonessential_during_recording(item->event) && expired) {
            const comp_audio_feedback_event_t event = item->event;
            remove_queue_index(feedback, index);
            notify(feedback, event, COMP_AUDIO_FEEDBACK_OUTCOME_DROPPED);
        } else {
            index++;
        }
    }
}

void comp_audio_feedback_init(comp_audio_feedback_t *feedback,
                              const comp_audio_feedback_config_t *config)
{
    if (feedback == NULL) {
        return;
    }
    memset(feedback, 0, sizeof(*feedback));
    feedback->volume_percent = 50u;
    feedback->start_gate = COMP_AUDIO_FEEDBACK_GATE_IDLE;
    if (config != NULL) {
        feedback->config = *config;
    }
    if (feedback->config.start_gate_timeout_ms == 0u) {
        feedback->config.start_gate_timeout_ms =
            COMP_AUDIO_FEEDBACK_DEFAULT_START_TIMEOUT_MS;
    }
    if (feedback->config.max_deferred_ms == 0u) {
        feedback->config.max_deferred_ms =
            COMP_AUDIO_FEEDBACK_DEFAULT_MAX_DEFERRED_MS;
    }
    if (feedback->config.speaker != NULL) {
        (void)comp_speaker_set_volume(feedback->config.speaker,
                                      feedback->volume_percent);
        comp_speaker_set_muted(feedback->config.speaker, false);
    }
}

comp_audio_feedback_submit_result_t comp_audio_feedback_submit(
    comp_audio_feedback_t *feedback,
    comp_audio_feedback_event_t event,
    uint32_t now_ms)
{
    int replacement = -1;
    uint8_t replacement_priority = UINT8_MAX;
    uint32_t replacement_sequence = UINT32_MAX;
    const uint32_t cooldown = cooldown_ms(event);

    if (feedback == NULL || event >= COMP_AUDIO_FEEDBACK_EVENT_COUNT) {
        return COMP_AUDIO_FEEDBACK_SUBMIT_BAD_ARGUMENT;
    }
    if (event == COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST) {
        if (feedback->recording_active ||
            feedback->start_gate != COMP_AUDIO_FEEDBACK_GATE_IDLE) {
            return COMP_AUDIO_FEEDBACK_SUBMIT_INVALID_STATE;
        }
        feedback->start_gate = COMP_AUDIO_FEEDBACK_GATE_WAITING;
        feedback->start_requested_ms = now_ms;
    } else if (event == COMP_AUDIO_FEEDBACK_RECORDING_STOPPED &&
               feedback->recording_active) {
        return COMP_AUDIO_FEEDBACK_SUBMIT_INVALID_STATE;
    }
    if (feedback->quiet) {
        if (event == COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST) {
            resolve_start_gate(feedback, COMP_AUDIO_FEEDBACK_OUTCOME_SILENT);
        }
        return COMP_AUDIO_FEEDBACK_SUBMIT_SUPPRESSED_QUIET;
    }
    if (feedback->recording_active && nonessential_during_recording(event)) {
        feedback->stats.suppressed_recording++;
        return COMP_AUDIO_FEEDBACK_SUBMIT_SUPPRESSED_RECORDING;
    }
    if (queued(feedback, event) ||
        (feedback->last_accepted_valid[event] && cooldown != 0u &&
         (uint32_t)(now_ms - feedback->last_accepted_ms[event]) < cooldown)) {
        feedback->stats.deduplicated++;
        if (event == COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST) {
            feedback->start_gate = COMP_AUDIO_FEEDBACK_GATE_IDLE;
        }
        return COMP_AUDIO_FEEDBACK_SUBMIT_DEDUPLICATED;
    }
    if (feedback->queue_count == COMP_AUDIO_FEEDBACK_QUEUE_DEPTH) {
        for (uint8_t index = 0u; index < feedback->queue_count; ++index) {
            const uint8_t item_priority = priority(feedback->queue[index].event);
            if (replacement < 0 || item_priority < replacement_priority ||
                (item_priority == replacement_priority &&
                 feedback->queue[index].sequence < replacement_sequence)) {
                replacement = index;
                replacement_priority = item_priority;
                replacement_sequence = feedback->queue[index].sequence;
            }
        }
        if (replacement < 0 || priority(event) <= replacement_priority) {
            if (event == COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST) {
                feedback->start_gate = COMP_AUDIO_FEEDBACK_GATE_IDLE;
            }
            return COMP_AUDIO_FEEDBACK_SUBMIT_QUEUE_FULL;
        }
        notify(feedback, feedback->queue[replacement].event,
               COMP_AUDIO_FEEDBACK_OUTCOME_DROPPED);
        remove_queue_index(feedback, (uint8_t)replacement);
        feedback->stats.queue_replacements++;
    }
    feedback->queue[feedback->queue_count++] =
        (comp_audio_feedback_queue_item_t){event, now_ms,
                                           feedback->next_sequence++};
    feedback->last_accepted_valid[event] = true;
    feedback->last_accepted_ms[event] = now_ms;
    feedback->stats.submitted++;
    if (feedback->queue_count > feedback->stats.queue_high_water) {
        feedback->stats.queue_high_water = feedback->queue_count;
    }
    return COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED;
}

comp_audio_feedback_submit_result_t comp_audio_feedback_submit_visible_pet(
    comp_audio_feedback_t *feedback,
    comp_audio_feedback_event_t event,
    uint32_t visible_ms,
    uint32_t now_ms)
{
    if (feedback == NULL || !pet_emotion_cue(event))
        return COMP_AUDIO_FEEDBACK_SUBMIT_BAD_ARGUMENT;
    if (now_ms - visible_ms > COMP_AUDIO_FEEDBACK_PET_VISIBLE_MAX_MS) {
        notify(feedback, event, COMP_AUDIO_FEEDBACK_OUTCOME_DROPPED);
        return COMP_AUDIO_FEEDBACK_SUBMIT_EXPIRED;
    }
    return comp_audio_feedback_submit(feedback, event, visible_ms);
}

void comp_audio_feedback_service(comp_audio_feedback_t *feedback,
                                 uint32_t now_ms)
{
    comp_speaker_t *speaker;
    int selected;
    comp_audio_feedback_event_t event;
    comp_speaker_result_t result;

    if (feedback == NULL) {
        return;
    }
    if (feedback->config.speaker == NULL) {
        if (feedback->start_gate == COMP_AUDIO_FEEDBACK_GATE_WAITING) {
            for (uint8_t index = 0u; index < feedback->queue_count; ++index) {
                if (feedback->queue[index].event ==
                    COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST) {
                    remove_queue_index(feedback, index);
                    break;
                }
            }
            resolve_start_gate(feedback, COMP_AUDIO_FEEDBACK_OUTCOME_FAILED);
        }
        return;
    }
    speaker = feedback->config.speaker;
    (void)comp_speaker_service(speaker);

    if (feedback->active) {
        if (speaker->state == COMP_SPEAKER_STATE_SHUTDOWN) {
            finish_active(feedback, COMP_AUDIO_FEEDBACK_OUTCOME_PLAYED);
        } else if (speaker->state == COMP_SPEAKER_STATE_FAULT) {
            finish_active(feedback, COMP_AUDIO_FEEDBACK_OUTCOME_FAILED);
        }
    }
    if (feedback->gate_release_pending && !comp_speaker_active(speaker)) {
        feedback->gate_release_pending = false;
        resolve_start_gate(feedback, feedback->gate_release_outcome);
    }
    if (feedback->start_gate == COMP_AUDIO_FEEDBACK_GATE_WAITING &&
        (uint32_t)(now_ms - feedback->start_requested_ms) >=
            feedback->config.start_gate_timeout_ms) {
        for (uint8_t index = 0u; index < feedback->queue_count; ++index) {
            if (feedback->queue[index].event ==
                COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST) {
                remove_queue_index(feedback, index);
                break;
            }
        }
        if (feedback->active && feedback->active_event ==
                                    COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST) {
            feedback->active_forced_outcome =
                COMP_AUDIO_FEEDBACK_OUTCOME_FAILED;
        } else {
            feedback->gate_release_pending = true;
            feedback->gate_release_outcome =
                COMP_AUDIO_FEEDBACK_OUTCOME_FAILED;
        }
        if (comp_speaker_active(speaker)) {
            (void)comp_speaker_stop(speaker, false);
        } else if (!feedback->active) {
            feedback->gate_release_pending = false;
            resolve_start_gate(feedback, COMP_AUDIO_FEEDBACK_OUTCOME_FAILED);
        }
        return;
    }
    if (feedback->active || feedback->gate_release_pending || feedback->quiet) {
        return;
    }

    drop_deferred_nonessential(feedback, now_ms);
    selected = select_next(feedback);
    if (selected < 0) {
        return;
    }
    event = feedback->queue[selected].event;
    result = comp_speaker_play_cue(speaker, cue_for_event(event));
    if (result == COMP_SPEAKER_BUSY) {
        return;
    }
    remove_queue_index(feedback, (uint8_t)selected);
    if (result != COMP_SPEAKER_OK) {
        if (event == COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST) {
            resolve_start_gate(feedback, COMP_AUDIO_FEEDBACK_OUTCOME_FAILED);
        } else {
            notify(feedback, event, COMP_AUDIO_FEEDBACK_OUTCOME_FAILED);
        }
        return;
    }
    feedback->active = true;
    feedback->active_event = event;
    feedback->active_forced_outcome = COMP_AUDIO_FEEDBACK_OUTCOME_NONE;
    /* A delayed admission cannot shorten the next pet cue's cooldown.
     * Keep queue age tied to visibility, but accepted history to actual
     * speaker command admission. Functional cue timing is unchanged. */
    if (pet_emotion_cue(event)) feedback->last_accepted_ms[event] = now_ms;
}

void comp_audio_feedback_set_quiet(comp_audio_feedback_t *feedback, bool quiet)
{
    bool queued_start = false;

    if (feedback == NULL || feedback->quiet == quiet) {
        return;
    }
    feedback->quiet = quiet;
    if (feedback->config.speaker != NULL) {
        comp_speaker_set_muted(feedback->config.speaker, quiet);
    }
    if (!quiet) {
        return;
    }
    for (uint8_t index = 0u; index < feedback->queue_count; ++index) {
        if (feedback->queue[index].event ==
            COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST) {
            queued_start = true;
        } else {
            notify(feedback, feedback->queue[index].event,
                   COMP_AUDIO_FEEDBACK_OUTCOME_DROPPED);
        }
    }
    feedback->queue_count = 0u;
    if (feedback->active) {
        feedback->active_forced_outcome =
            COMP_AUDIO_FEEDBACK_OUTCOME_SILENT;
        if (queued_start && feedback->active_event !=
                                COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST) {
            feedback->gate_release_pending = true;
            feedback->gate_release_outcome =
                COMP_AUDIO_FEEDBACK_OUTCOME_SILENT;
        }
        (void)comp_speaker_stop(feedback->config.speaker, false);
    } else if (queued_start &&
               feedback->start_gate == COMP_AUDIO_FEEDBACK_GATE_WAITING) {
        if (comp_speaker_active(feedback->config.speaker)) {
            feedback->gate_release_pending = true;
            feedback->gate_release_outcome =
                COMP_AUDIO_FEEDBACK_OUTCOME_SILENT;
            (void)comp_speaker_stop(feedback->config.speaker, false);
        } else {
            resolve_start_gate(feedback, COMP_AUDIO_FEEDBACK_OUTCOME_SILENT);
        }
    }
}

bool comp_audio_feedback_set_volume(comp_audio_feedback_t *feedback,
                                    uint8_t percent)
{
    if (feedback == NULL || feedback->config.speaker == NULL || percent > 100u ||
        comp_speaker_set_volume(feedback->config.speaker, percent) !=
            COMP_SPEAKER_OK) {
        return false;
    }
    feedback->volume_percent = percent;
    return true;
}

void comp_audio_feedback_cancel_pet(comp_audio_feedback_t *feedback)
{
    if (feedback == NULL) return;
    for (uint8_t index = 0u; index < feedback->queue_count;) {
        const comp_audio_feedback_event_t event = feedback->queue[index].event;
        if (pet_emotion_cue(event)) {
            remove_queue_index(feedback, index);
            notify(feedback, event, COMP_AUDIO_FEEDBACK_OUTCOME_DROPPED);
        } else {
            index++;
        }
    }
    if (feedback->active && pet_emotion_cue(feedback->active_event) &&
        feedback->active_forced_outcome != COMP_AUDIO_FEEDBACK_OUTCOME_DROPPED) {
        feedback->active_forced_outcome = COMP_AUDIO_FEEDBACK_OUTCOME_DROPPED;
        if (feedback->config.speaker != NULL)
            (void)comp_speaker_stop(feedback->config.speaker, false);
    }
}

bool comp_audio_feedback_set_recording_active(
    comp_audio_feedback_t *feedback,
    bool active)
{
    if (feedback == NULL) {
        return false;
    }
    if (active &&
        (feedback->start_gate != COMP_AUDIO_FEEDBACK_GATE_IDLE ||
         feedback->active || feedback->gate_release_pending ||
         (feedback->config.speaker != NULL &&
          comp_speaker_active(feedback->config.speaker)))) {
        return false;
    }
    feedback->recording_active = active;
    if (active) {
        for (uint8_t index = 0u; index < feedback->queue_count;) {
            if (nonessential_during_recording(feedback->queue[index].event)) {
                const comp_audio_feedback_event_t event =
                    feedback->queue[index].event;
                remove_queue_index(feedback, index);
                feedback->stats.suppressed_recording++;
                notify(feedback, event, COMP_AUDIO_FEEDBACK_OUTCOME_DROPPED);
            } else {
                index++;
            }
        }
    }
    return true;
}

comp_audio_feedback_start_gate_t comp_audio_feedback_start_gate(
    const comp_audio_feedback_t *feedback)
{
    return feedback == NULL ? COMP_AUDIO_FEEDBACK_GATE_IDLE :
                              feedback->start_gate;
}

bool comp_audio_feedback_take_recording_start_gate(
    comp_audio_feedback_t *feedback,
    comp_audio_feedback_outcome_t *outcome)
{
    comp_audio_feedback_outcome_t value;

    if (feedback == NULL ||
        feedback->start_gate < COMP_AUDIO_FEEDBACK_GATE_READY_PLAYED) {
        return false;
    }
    value = feedback->start_gate == COMP_AUDIO_FEEDBACK_GATE_READY_PLAYED
                ? COMP_AUDIO_FEEDBACK_OUTCOME_PLAYED
                : feedback->start_gate == COMP_AUDIO_FEEDBACK_GATE_READY_SILENT
                      ? COMP_AUDIO_FEEDBACK_OUTCOME_SILENT
                      : COMP_AUDIO_FEEDBACK_OUTCOME_FAILED;
    feedback->start_gate = COMP_AUDIO_FEEDBACK_GATE_IDLE;
    if (outcome != NULL) {
        *outcome = value;
    }
    return true;
}

bool comp_audio_feedback_cancel_recording_start(
    comp_audio_feedback_t *feedback,
    uint32_t now_ms)
{
    bool removed = false;
    (void)now_ms;

    if (feedback == NULL ||
        feedback->start_gate != COMP_AUDIO_FEEDBACK_GATE_WAITING) {
        return false;
    }
    for (uint8_t index = 0u; index < feedback->queue_count; ++index) {
        if (feedback->queue[index].event ==
            COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST) {
            remove_queue_index(feedback, index);
            removed = true;
            break;
        }
    }
    feedback->start_gate = COMP_AUDIO_FEEDBACK_GATE_IDLE;
    feedback->gate_release_pending = false;
    feedback->gate_release_outcome = COMP_AUDIO_FEEDBACK_OUTCOME_NONE;
    if (feedback->active && feedback->active_event ==
                                COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST) {
        feedback->start_cancelled = true;
        feedback->active_forced_outcome =
            COMP_AUDIO_FEEDBACK_OUTCOME_DROPPED;
        if (feedback->config.speaker != NULL) {
            (void)comp_speaker_stop(feedback->config.speaker, false);
        }
    } else if (removed) {
        notify(feedback, COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST,
               COMP_AUDIO_FEEDBACK_OUTCOME_DROPPED);
    }
    return true;
}

bool comp_audio_feedback_busy(const comp_audio_feedback_t *feedback)
{
    return feedback != NULL &&
           (feedback->active || feedback->queue_count != 0u ||
            feedback->gate_release_pending ||
            feedback->start_gate == COMP_AUDIO_FEEDBACK_GATE_WAITING);
}

void comp_audio_feedback_get_stats(const comp_audio_feedback_t *feedback,
                                   comp_audio_feedback_stats_t *stats)
{
    if (stats == NULL) {
        return;
    }
    if (feedback == NULL) {
        memset(stats, 0, sizeof(*stats));
    } else {
        *stats = feedback->stats;
    }
}

const char *comp_audio_feedback_event_name(comp_audio_feedback_event_t event)
{
    switch (event) {
    case COMP_AUDIO_FEEDBACK_TOUCH_CONFIRM: return "touch_confirm";
    case COMP_AUDIO_FEEDBACK_CONNECTED: return "connected";
    case COMP_AUDIO_FEEDBACK_DISCONNECTED: return "disconnected";
    case COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST: return "recording_start";
    case COMP_AUDIO_FEEDBACK_RECORDING_STOPPED: return "recording_stopped";
    case COMP_AUDIO_FEEDBACK_ERROR: return "error";
    case COMP_AUDIO_FEEDBACK_PET_GREETING: return "pet_greeting";
    case COMP_AUDIO_FEEDBACK_PET_CONTENT: return "pet_content";
    case COMP_AUDIO_FEEDBACK_PET_PLAYFUL: return "pet_playful";
    case COMP_AUDIO_FEEDBACK_PET_SHY: return "pet_shy";
    default: return "unknown";
    }
}
