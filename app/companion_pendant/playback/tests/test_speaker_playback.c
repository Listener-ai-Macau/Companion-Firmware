#include "speaker_playback.h"

#include <stdio.h>
#include <string.h>

typedef struct {
    bool amplifier_enabled;
    bool activity;
    bool enable_result;
    bool submit_result;
    unsigned enable_calls;
    unsigned activity_calls;
    unsigned submit_calls;
    size_t last_frames;
    int16_t last_pcm[COMP_SPEAKER_BLOCK_FRAMES * COMP_SPEAKER_CHANNELS];
} fake_target_t;

static bool fake_enable(void *context, bool enabled)
{
    fake_target_t *fake = context;
    fake->enable_calls++;
    fake->amplifier_enabled = enabled;
    return fake->enable_result;
}

static bool fake_submit(void *context, const int16_t *pcm, size_t frames)
{
    fake_target_t *fake = context;
    fake->submit_calls++;
    fake->last_frames = frames;
    memcpy(fake->last_pcm, pcm, frames * 2u * sizeof(*pcm));
    return fake->submit_result;
}

static void fake_activity(void *context, bool active)
{
    fake_target_t *fake = context;
    fake->activity_calls++;
    fake->activity = active;
}

static int fail(const char *message)
{
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

static void complete_block(comp_speaker_t *speaker)
{
    comp_speaker_tx_complete(speaker, true);
}

static int test_stream_and_drain(void)
{
    comp_speaker_t speaker;
    fake_target_t fake = {.enable_result = true, .submit_result = true};
    const comp_speaker_config_t config = {
        .set_amplifier_enabled = fake_enable,
        .submit_i2s = fake_submit,
        .set_playback_active = fake_activity,
        .context = &fake,
    };
    int16_t input[80];
    size_t i;
    int16_t prior = 0;

    for (i = 0u; i < 80u; ++i) input[i] = 30000;
    comp_speaker_init(&speaker, &config);
    if (!comp_speaker_ready(&speaker) ||
        comp_speaker_set_volume(&speaker, 100u) != COMP_SPEAKER_OK ||
        comp_speaker_start_stream(&speaker) != COMP_SPEAKER_OK ||
        !fake.amplifier_enabled || !fake.activity ||
        comp_speaker_write_pcm16(&speaker, input, 80u) != 80u) {
        return fail("stream startup");
    }
    if (!comp_speaker_service(&speaker) || fake.last_frames != 64u) {
        return fail("startup silence submit");
    }
    for (i = 0u; i < 128u; ++i) {
        if (fake.last_pcm[i] != 0) return fail("startup block was not silent");
    }
    if (comp_speaker_service(&speaker)) return fail("double DMA submit");
    complete_block(&speaker);
    if (speaker.state != COMP_SPEAKER_STATE_PLAYING ||
        !comp_speaker_service(&speaker)) return fail("first PCM block");
    for (i = 0u; i < 64u; ++i) {
        int16_t left = fake.last_pcm[i * 2u];
        if (left != fake.last_pcm[i * 2u + 1u] || left < prior ||
            left > input[i]) return fail("stereo duplication or gain ramp");
        prior = left;
    }
    complete_block(&speaker);
    if (!comp_speaker_service(&speaker)) {
        return fail("partial PCM block was dropped");
    }
    for (i = 0u; i < 64u; ++i) {
        if (fake.last_pcm[i * 2u] != fake.last_pcm[i * 2u + 1u]) {
            return fail("partial PCM stereo duplication");
        }
    }
    if (speaker.underruns != 1u) return fail("partial block underrun accounting");
    complete_block(&speaker);
    if (comp_speaker_stop(&speaker, true) != COMP_SPEAKER_OK) {
        return fail("draining stop request");
    }
    for (i = 0u; i < 8u && speaker.state != COMP_SPEAKER_STATE_SHUTDOWN; ++i) {
        if (comp_speaker_service(&speaker)) complete_block(&speaker);
    }
    if (speaker.state != COMP_SPEAKER_STATE_SHUTDOWN ||
        fake.amplifier_enabled || fake.activity || speaker.clipped_samples != 0u) {
        return fail("draining stop completion");
    }
    return 0;
}

static int test_cues_and_mute(void)
{
    comp_speaker_t speaker;
    fake_target_t fake = {.enable_result = true, .submit_result = true};
    const comp_speaker_config_t config = {
        .set_amplifier_enabled = fake_enable,
        .submit_i2s = fake_submit,
        .set_playback_active = fake_activity,
        .context = &fake,
    };
    unsigned guard;
    bool heard_nonzero = false;

    comp_speaker_init(&speaker, &config);
    if (comp_speaker_play_cue(&speaker, COMP_SPEAKER_CUE_RECORDING_STARTED) !=
        COMP_SPEAKER_OK || !comp_speaker_service(&speaker)) {
        return fail("cue startup");
    }
    complete_block(&speaker);
    for (guard = 0u; guard < 64u && speaker.state != COMP_SPEAKER_STATE_SHUTDOWN;
         ++guard) {
        size_t i;
        if (!comp_speaker_service(&speaker)) continue;
        for (i = 0u; i < 64u; ++i) {
            if (fake.last_pcm[i * 2u] != fake.last_pcm[i * 2u + 1u]) {
                return fail("cue stereo mismatch");
            }
            heard_nonzero = heard_nonzero || fake.last_pcm[i * 2u] != 0;
        }
        complete_block(&speaker);
    }
    if (!heard_nonzero || speaker.state != COMP_SPEAKER_STATE_SHUTDOWN) {
        return fail("cue did not play and terminate");
    }

    if (comp_speaker_start_stream(&speaker) != COMP_SPEAKER_OK) {
        return fail("mute stream start");
    }
    comp_speaker_set_muted(&speaker, true);
    if (speaker.target_gain_q15 != 0) return fail("mute target");
    if (comp_speaker_stop(&speaker, false) != COMP_SPEAKER_OK ||
        speaker.state != COMP_SPEAKER_STATE_SHUTDOWN) {
        return fail("immediate stop");
    }
    return 0;
}

static int test_capacity_and_fail_closed(void)
{
    comp_speaker_t speaker;
    fake_target_t fake = {.enable_result = true, .submit_result = true};
    const comp_speaker_config_t config = {
        .set_amplifier_enabled = fake_enable,
        .submit_i2s = fake_submit,
        .set_playback_active = fake_activity,
        .context = &fake,
    };
    int16_t samples[COMP_SPEAKER_FIFO_FRAMES + 1u] = {0};

    comp_speaker_init(&speaker, &config);
    if (comp_speaker_start_stream(&speaker) != COMP_SPEAKER_OK ||
        comp_speaker_write_pcm16(&speaker, samples,
                                 COMP_SPEAKER_FIFO_FRAMES + 1u) !=
            COMP_SPEAKER_FIFO_FRAMES ||
        comp_speaker_writable_frames(&speaker) != 0u) {
        return fail("bounded FIFO");
    }
    fake.submit_result = false;
    if (comp_speaker_service(&speaker) ||
        speaker.state != COMP_SPEAKER_STATE_FAULT || fake.amplifier_enabled ||
        fake.activity || speaker.last_error != COMP_SPEAKER_IO_ERROR) {
        return fail("submit failure did not fail closed");
    }

    fake.enable_result = false;
    fake.submit_result = true;
    comp_speaker_init(&speaker, &config);
    if (comp_speaker_start_stream(&speaker) != COMP_SPEAKER_IO_ERROR ||
        speaker.state != COMP_SPEAKER_STATE_FAULT) {
        return fail("amplifier enable failure");
    }
    comp_speaker_init(&speaker, NULL);
    if (comp_speaker_ready(&speaker) ||
        comp_speaker_start_stream(&speaker) != COMP_SPEAKER_BAD_ARGUMENT ||
        comp_speaker_set_volume(&speaker, 101u) != COMP_SPEAKER_BAD_ARGUMENT) {
        return fail("invalid configuration guards");
    }
    return 0;
}

static int test_dma_completion_failure(void)
{
    comp_speaker_t speaker;
    fake_target_t fake = {.enable_result = true, .submit_result = true};
    const comp_speaker_config_t config = {
        .set_amplifier_enabled = fake_enable,
        .submit_i2s = fake_submit,
        .set_playback_active = fake_activity,
        .context = &fake,
    };

    comp_speaker_init(&speaker, &config);
    if (comp_speaker_play_cue(&speaker, COMP_SPEAKER_CUE_ERROR) !=
            COMP_SPEAKER_OK ||
        !comp_speaker_service(&speaker)) {
        return fail("DMA failure setup");
    }
    comp_speaker_tx_complete(&speaker, false);
    if (speaker.state != COMP_SPEAKER_STATE_FAULT || speaker.tx_pending ||
        fake.amplifier_enabled || fake.activity) {
        return fail("DMA completion failure did not fail closed");
    }
    return 0;
}

static int test_drain_preserves_queued_audio(void)
{
    comp_speaker_t speaker;
    fake_target_t fake = {.enable_result = true, .submit_result = true};
    const comp_speaker_config_t config = {
        .set_amplifier_enabled = fake_enable,
        .submit_i2s = fake_submit,
        .set_playback_active = fake_activity,
        .context = &fake,
    };
    int16_t samples[192];
    size_t i;
    bool first_block_audible = false;

    for (i = 0u; i < 192u; ++i) samples[i] = 20000;
    comp_speaker_init(&speaker, &config);
    (void)comp_speaker_set_volume(&speaker, 100u);
    if (comp_speaker_start_stream(&speaker) != COMP_SPEAKER_OK ||
        comp_speaker_write_pcm16(&speaker, samples, 192u) != 192u ||
        !comp_speaker_service(&speaker)) {
        return fail("drain preservation setup");
    }
    complete_block(&speaker);
    if (comp_speaker_stop(&speaker, true) != COMP_SPEAKER_OK ||
        !comp_speaker_service(&speaker)) {
        return fail("drain preservation start");
    }
    for (i = 0u; i < 64u; ++i) {
        first_block_audible = first_block_audible || fake.last_pcm[i * 2u] != 0;
    }
    if (!first_block_audible || speaker.fifo_count != 128u) {
        return fail("drain discarded queued PCM");
    }
    complete_block(&speaker);
    for (i = 0u; i < 8u && speaker.state != COMP_SPEAKER_STATE_SHUTDOWN; ++i) {
        if (comp_speaker_service(&speaker)) complete_block(&speaker);
    }
    if (speaker.state != COMP_SPEAKER_STATE_SHUTDOWN) {
        return fail("drain preservation completion");
    }
    return 0;
}

int main(void)
{
    if (test_stream_and_drain() != 0 || test_cues_and_mute() != 0 ||
        test_capacity_and_fail_closed() != 0 ||
        test_dma_completion_failure() != 0 ||
        test_drain_preserves_queued_audio() != 0) return 1;
    printf("PASS: WBA speaker portable async PCM/cues/stereo/ramp/mute/drain/fault contract\n");
    return 0;
}
