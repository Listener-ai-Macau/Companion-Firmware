#include "audio_feedback.h"

#include <stdio.h>
#include <string.h>

#define REQUIRE(condition)                                                       \
    do {                                                                         \
        if (!(condition)) {                                                       \
            fprintf(stderr, "FAIL:%d: %s\n", __LINE__, #condition);             \
            return 1;                                                            \
        }                                                                        \
    } while (0)

typedef struct {
    bool amplifier_enabled;
    bool submit_ok;
    unsigned submits;
    comp_audio_feedback_event_t events[32];
    comp_audio_feedback_outcome_t outcomes[32];
    unsigned finished;
} fixture_t;

static bool enable_amplifier(void *context, bool enabled)
{
    ((fixture_t *)context)->amplifier_enabled = enabled;
    return true;
}

static bool submit_i2s(void *context, const int16_t *pcm, size_t frames)
{
    fixture_t *fixture = context;
    (void)pcm;
    if (frames != COMP_SPEAKER_BLOCK_FRAMES) {
        return false;
    }
    fixture->submits++;
    return fixture->submit_ok;
}

static void playback_active(void *context, bool active)
{
    (void)context;
    (void)active;
}

static void finished(void *context,
                     comp_audio_feedback_event_t event,
                     comp_audio_feedback_outcome_t outcome)
{
    fixture_t *fixture = context;
    if (fixture->finished < 32u) {
        fixture->events[fixture->finished] = event;
        fixture->outcomes[fixture->finished] = outcome;
        fixture->finished++;
    }
}

static void setup(fixture_t *fixture,
                  comp_speaker_t *speaker,
                  comp_audio_feedback_t *feedback,
                  uint32_t start_timeout_ms,
                  uint32_t max_deferred_ms)
{
    const comp_speaker_config_t speaker_config = {
        enable_amplifier, submit_i2s, playback_active, fixture};
    comp_audio_feedback_config_t feedback_config;

    memset(fixture, 0, sizeof(*fixture));
    fixture->submit_ok = true;
    comp_speaker_init(speaker, &speaker_config);
    feedback_config = (comp_audio_feedback_config_t){
        speaker, finished, fixture, start_timeout_ms, max_deferred_ms};
    comp_audio_feedback_init(feedback, &feedback_config);
}

static void tick(comp_audio_feedback_t *feedback,
                 comp_speaker_t *speaker,
                 uint32_t now_ms,
                 bool dma_success)
{
    comp_audio_feedback_service(feedback, now_ms);
    if (speaker->tx_pending) {
        comp_speaker_tx_complete(speaker, dma_success);
    }
}

static bool run_until_not_busy(comp_audio_feedback_t *feedback,
                               comp_speaker_t *speaker,
                               uint32_t *now_ms)
{
    for (unsigned guard = 0u; guard < 256u; ++guard) {
        tick(feedback, speaker, (*now_ms)++, true);
        if (!comp_audio_feedback_busy(feedback) &&
            !comp_speaker_active(speaker)) {
            return true;
        }
    }
    return false;
}

static int test_recording_gate_and_capture_policy(void)
{
    fixture_t fixture;
    comp_speaker_t speaker;
    comp_audio_feedback_t feedback;
    comp_audio_feedback_outcome_t outcome = COMP_AUDIO_FEEDBACK_OUTCOME_NONE;
    uint32_t now = 0u;

    setup(&fixture, &speaker, &feedback, 3000u, 1500u);
    REQUIRE(comp_audio_feedback_submit(
                &feedback, COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST, now) ==
            COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED);
    REQUIRE(comp_audio_feedback_start_gate(&feedback) ==
            COMP_AUDIO_FEEDBACK_GATE_WAITING);
    REQUIRE(!comp_audio_feedback_set_recording_active(&feedback, true));
    for (unsigned guard = 0u;
         guard < 128u && comp_audio_feedback_start_gate(&feedback) ==
                              COMP_AUDIO_FEEDBACK_GATE_WAITING;
         ++guard) {
        tick(&feedback, &speaker, now++, true);
    }
    REQUIRE(comp_audio_feedback_start_gate(&feedback) ==
            COMP_AUDIO_FEEDBACK_GATE_READY_PLAYED);
    REQUIRE(comp_audio_feedback_take_recording_start_gate(&feedback, &outcome));
    REQUIRE(outcome == COMP_AUDIO_FEEDBACK_OUTCOME_PLAYED);
    REQUIRE(comp_audio_feedback_set_recording_active(&feedback, true));
    REQUIRE(comp_audio_feedback_submit(
                &feedback, COMP_AUDIO_FEEDBACK_TOUCH_CONFIRM, now) ==
            COMP_AUDIO_FEEDBACK_SUBMIT_SUPPRESSED_RECORDING);
    REQUIRE(comp_audio_feedback_submit(
                &feedback, COMP_AUDIO_FEEDBACK_CONNECTED, now) ==
            COMP_AUDIO_FEEDBACK_SUBMIT_SUPPRESSED_RECORDING);
    REQUIRE(comp_audio_feedback_submit(
                &feedback, COMP_AUDIO_FEEDBACK_RECORDING_STOPPED, now) ==
            COMP_AUDIO_FEEDBACK_SUBMIT_INVALID_STATE);
    REQUIRE(comp_audio_feedback_set_recording_active(&feedback, false));
    REQUIRE(comp_audio_feedback_submit(
                &feedback, COMP_AUDIO_FEEDBACK_RECORDING_STOPPED, now) ==
            COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED);
    REQUIRE(run_until_not_busy(&feedback, &speaker, &now));
    REQUIRE(fixture.finished == 2u);
    REQUIRE(fixture.events[0] ==
                COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST &&
            fixture.outcomes[0] == COMP_AUDIO_FEEDBACK_OUTCOME_PLAYED);
    REQUIRE(fixture.events[1] == COMP_AUDIO_FEEDBACK_RECORDING_STOPPED &&
            fixture.outcomes[1] == COMP_AUDIO_FEEDBACK_OUTCOME_PLAYED);
    return 0;
}

static int test_quiet_and_cancel_gate(void)
{
    fixture_t fixture;
    comp_speaker_t speaker;
    comp_audio_feedback_t feedback;
    comp_audio_feedback_outcome_t outcome;

    setup(&fixture, &speaker, &feedback, 3000u, 1500u);
    comp_audio_feedback_set_quiet(&feedback, true);
    REQUIRE(comp_audio_feedback_submit(
                &feedback, COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST, 0u) ==
            COMP_AUDIO_FEEDBACK_SUBMIT_SUPPRESSED_QUIET);
    REQUIRE(comp_audio_feedback_take_recording_start_gate(&feedback, &outcome));
    REQUIRE(outcome == COMP_AUDIO_FEEDBACK_OUTCOME_SILENT);
    REQUIRE(fixture.submits == 0u);

    setup(&fixture, &speaker, &feedback, 3000u, 1500u);
    REQUIRE(comp_audio_feedback_submit(
                &feedback, COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST, 10u) ==
            COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED);
    comp_audio_feedback_service(&feedback, 10u);
    REQUIRE(feedback.active);
    REQUIRE(comp_audio_feedback_cancel_recording_start(&feedback, 11u));
    comp_audio_feedback_service(&feedback, 11u);
    REQUIRE(comp_audio_feedback_start_gate(&feedback) ==
            COMP_AUDIO_FEEDBACK_GATE_IDLE);
    REQUIRE(!comp_audio_feedback_take_recording_start_gate(&feedback, &outcome));
    REQUIRE(fixture.finished == 1u &&
            fixture.outcomes[0] == COMP_AUDIO_FEEDBACK_OUTCOME_DROPPED);
    REQUIRE(!comp_audio_feedback_cancel_recording_start(&feedback, 12u));

    setup(&fixture, &speaker, &feedback, 3000u, 1500u);
    REQUIRE(comp_audio_feedback_submit(
                &feedback, COMP_AUDIO_FEEDBACK_TOUCH_CONFIRM, 20u) ==
            COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED);
    comp_audio_feedback_service(&feedback, 20u);
    REQUIRE(feedback.active);
    REQUIRE(comp_audio_feedback_submit(
                &feedback, COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST, 21u) ==
            COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED);
    comp_audio_feedback_set_quiet(&feedback, true);
    comp_audio_feedback_service(&feedback, 22u);
    REQUIRE(comp_audio_feedback_take_recording_start_gate(&feedback, &outcome));
    REQUIRE(outcome == COMP_AUDIO_FEEDBACK_OUTCOME_SILENT);
    REQUIRE(fixture.finished == 2u);
    REQUIRE(fixture.events[0] == COMP_AUDIO_FEEDBACK_TOUCH_CONFIRM &&
            fixture.outcomes[0] == COMP_AUDIO_FEEDBACK_OUTCOME_SILENT);
    REQUIRE(fixture.events[1] ==
                COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST &&
            fixture.outcomes[1] == COMP_AUDIO_FEEDBACK_OUTCOME_SILENT);
    return 0;
}

static int test_priority_dedup_and_recording_error(void)
{
    fixture_t fixture;
    comp_speaker_t speaker;
    comp_audio_feedback_t feedback;
    comp_audio_feedback_stats_t stats;
    uint32_t now = 1000u;

    setup(&fixture, &speaker, &feedback, 3000u, 1500u);
    REQUIRE(comp_audio_feedback_submit(
                &feedback, COMP_AUDIO_FEEDBACK_TOUCH_CONFIRM, now) ==
            COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED);
    REQUIRE(comp_audio_feedback_submit(
                &feedback, COMP_AUDIO_FEEDBACK_CONNECTED, now) ==
            COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED);
    REQUIRE(comp_audio_feedback_submit(
                &feedback, COMP_AUDIO_FEEDBACK_ERROR, now) ==
            COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED);
    comp_audio_feedback_service(&feedback, now++);
    REQUIRE(feedback.active_event == COMP_AUDIO_FEEDBACK_ERROR);
    REQUIRE(!comp_audio_feedback_set_recording_active(&feedback, true));
    REQUIRE(run_until_not_busy(&feedback, &speaker, &now));
    REQUIRE(fixture.finished == 3u);
    REQUIRE(fixture.events[0] == COMP_AUDIO_FEEDBACK_ERROR);
    REQUIRE(fixture.events[1] == COMP_AUDIO_FEEDBACK_CONNECTED);
    REQUIRE(fixture.events[2] == COMP_AUDIO_FEEDBACK_TOUCH_CONFIRM);

    REQUIRE(comp_audio_feedback_submit(
                &feedback, COMP_AUDIO_FEEDBACK_TOUCH_CONFIRM, now) ==
            COMP_AUDIO_FEEDBACK_SUBMIT_DEDUPLICATED);
    now += 250u;
    REQUIRE(comp_audio_feedback_submit(
                &feedback, COMP_AUDIO_FEEDBACK_TOUCH_CONFIRM, now) ==
            COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED);
    REQUIRE(feedback.queue_count <= COMP_AUDIO_FEEDBACK_QUEUE_DEPTH);

    REQUIRE(comp_audio_feedback_set_recording_active(&feedback, true));
    REQUIRE(feedback.queue_count == 0u);
    REQUIRE(comp_audio_feedback_submit(
                &feedback, COMP_AUDIO_FEEDBACK_DISCONNECTED, now) ==
            COMP_AUDIO_FEEDBACK_SUBMIT_SUPPRESSED_RECORDING);
    now += 500u;
    REQUIRE(comp_audio_feedback_submit(
                &feedback, COMP_AUDIO_FEEDBACK_ERROR, now) ==
            COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED);
    comp_audio_feedback_service(&feedback, now);
    REQUIRE(feedback.active_event == COMP_AUDIO_FEEDBACK_ERROR);
    comp_audio_feedback_get_stats(&feedback, &stats);
    REQUIRE(stats.deduplicated == 1u);
    REQUIRE(stats.suppressed_recording >= 1u);
    REQUIRE(stats.queue_high_water <= COMP_AUDIO_FEEDBACK_QUEUE_DEPTH);
    return 0;
}

static int test_timeout_waits_for_speaker_quiet_and_dma_failure(void)
{
    fixture_t fixture;
    comp_speaker_t speaker;
    comp_audio_feedback_t feedback;
    comp_audio_feedback_outcome_t outcome;
    uint32_t now = 0u;

    setup(&fixture, &speaker, &feedback, 5u, 1500u);
    REQUIRE(comp_speaker_start_stream(&speaker) == COMP_SPEAKER_OK);
    REQUIRE(comp_audio_feedback_submit(
                &feedback, COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST, 0u) ==
            COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED);
    for (; now < 5u; ++now) {
        tick(&feedback, &speaker, now, true);
    }
    comp_audio_feedback_service(&feedback, now++);
    REQUIRE(comp_audio_feedback_start_gate(&feedback) ==
            COMP_AUDIO_FEEDBACK_GATE_WAITING);
    for (unsigned guard = 0u;
         guard < 16u && comp_audio_feedback_start_gate(&feedback) ==
                            COMP_AUDIO_FEEDBACK_GATE_WAITING;
         ++guard) {
        tick(&feedback, &speaker, now++, true);
    }
    REQUIRE(!comp_speaker_active(&speaker));
    REQUIRE(comp_audio_feedback_take_recording_start_gate(&feedback, &outcome));
    REQUIRE(outcome == COMP_AUDIO_FEEDBACK_OUTCOME_FAILED);

    setup(&fixture, &speaker, &feedback, 3000u, 1500u);
    REQUIRE(comp_audio_feedback_submit(
                &feedback, COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST, 0u) ==
            COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED);
    comp_audio_feedback_service(&feedback, 0u);
    comp_audio_feedback_service(&feedback, 1u);
    REQUIRE(speaker.tx_pending);
    comp_speaker_tx_complete(&speaker, false);
    comp_audio_feedback_service(&feedback, 2u);
    REQUIRE(comp_audio_feedback_take_recording_start_gate(&feedback, &outcome));
    REQUIRE(outcome == COMP_AUDIO_FEEDBACK_OUTCOME_FAILED);
    REQUIRE(!fixture.amplifier_enabled);
    return 0;
}

static int test_volume_and_missing_speaker(void)
{
    fixture_t fixture;
    comp_speaker_t speaker;
    comp_audio_feedback_t feedback;
    comp_audio_feedback_config_t config = {0};
    comp_audio_feedback_outcome_t outcome;

    setup(&fixture, &speaker, &feedback, 3000u, 1500u);
    REQUIRE(comp_audio_feedback_set_volume(&feedback, 73u));
    REQUIRE(speaker.volume_percent == 73u);
    REQUIRE(!comp_audio_feedback_set_volume(&feedback, 101u));

    comp_audio_feedback_init(&feedback, &config);
    REQUIRE(comp_audio_feedback_submit(
                &feedback, COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST, 0u) ==
            COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED);
    comp_audio_feedback_service(&feedback, 0u);
    REQUIRE(comp_audio_feedback_take_recording_start_gate(&feedback, &outcome));
    REQUIRE(outcome == COMP_AUDIO_FEEDBACK_OUTCOME_FAILED);
    return 0;
}

static int test_hardware_fault_does_not_leave_cues_busy(void)
{
    fixture_t fixture;
    comp_speaker_t speaker;
    comp_audio_feedback_t feedback;
    uint32_t now=0u;
    setup(&fixture,&speaker,&feedback,3000u,1500u);
    REQUIRE(comp_audio_feedback_submit(&feedback,COMP_AUDIO_FEEDBACK_RECORDING_STOPPED,now)==
        COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED);
    comp_audio_feedback_service(&feedback,now++);
    comp_audio_feedback_service(&feedback,now++);
    REQUIRE(speaker.tx_pending);
    comp_speaker_tx_complete(&speaker,false);
    REQUIRE(comp_audio_feedback_submit(&feedback,COMP_AUDIO_FEEDBACK_ERROR,now)==
        COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED);
    comp_audio_feedback_service(&feedback,now++);
    REQUIRE(!comp_audio_feedback_busy(&feedback));
    REQUIRE(speaker.state==COMP_SPEAKER_STATE_FAULT);
    REQUIRE(!fixture.amplifier_enabled);
    REQUIRE(fixture.finished==2u);
    REQUIRE(fixture.outcomes[0]==COMP_AUDIO_FEEDBACK_OUTCOME_FAILED &&
        fixture.outcomes[1]==COMP_AUDIO_FEEDBACK_OUTCOME_FAILED);
    /* Busy still means actual live playback, not an erased fault. */
    setup(&fixture,&speaker,&feedback,3000u,1500u);
    REQUIRE(comp_speaker_start_stream(&speaker)==COMP_SPEAKER_OK);
    REQUIRE(comp_speaker_play_cue(&speaker,COMP_SPEAKER_CUE_ERROR)==COMP_SPEAKER_BUSY);
    return 0;
}

int main(void)
{
    if (test_recording_gate_and_capture_policy() != 0 ||
        test_quiet_and_cancel_gate() != 0 ||
        test_priority_dedup_and_recording_error() != 0 ||
        test_timeout_waits_for_speaker_quiet_and_dma_failure() != 0 ||
        test_volume_and_missing_speaker() != 0 ||
        test_hardware_fault_does_not_leave_cues_busy() != 0) {
        return 1;
    }
    puts("PASS: portable audio feedback gates recording and bounds product cues");
    return 0;
}
