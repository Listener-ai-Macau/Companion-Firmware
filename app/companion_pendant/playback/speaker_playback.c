#include "speaker_playback.h"

#include <limits.h>
#include <string.h>

#define COMP_SPEAKER_GAIN_ONE_Q15 32767
#define COMP_SPEAKER_GAIN_RAMP_STEP_Q15 512
#define COMP_SPEAKER_CUE_AMPLITUDE 7000
#define COMP_SPEAKER_CUE_FADE_FRAMES 64u

static void set_activity(comp_speaker_t *speaker, bool active)
{
    if (speaker->config.set_playback_active != NULL) {
        speaker->config.set_playback_active(speaker->config.context, active);
    }
}

static void enter_fault(comp_speaker_t *speaker)
{
    speaker->state = COMP_SPEAKER_STATE_FAULT;
    speaker->last_error = COMP_SPEAKER_IO_ERROR;
    speaker->tx_pending = false;
    speaker->fifo_count = 0u;
    speaker->cue_active = false;
    (void)speaker->config.set_amplifier_enabled(speaker->config.context, false);
    set_activity(speaker, false);
}

static int32_t requested_gain(const comp_speaker_t *speaker)
{
    if (speaker->muted) {
        return 0;
    }
    return ((int32_t)speaker->volume_percent * COMP_SPEAKER_GAIN_ONE_Q15) / 100;
}

static void refresh_target_gain(comp_speaker_t *speaker)
{
    speaker->target_gain_q15 = requested_gain(speaker);
    if ((speaker->stop_requested &&
         (!speaker->drain_requested || speaker->fifo_count <=
             COMP_SPEAKER_BLOCK_FRAMES)) ||
        (speaker->cue_active &&
         speaker->cue_frames_remaining <= COMP_SPEAKER_CUE_FADE_FRAMES)) {
        speaker->target_gain_q15 = 0;
    }
}

static int16_t scale_sample(comp_speaker_t *speaker, int16_t sample)
{
    int32_t scaled;

    if (speaker->current_gain_q15 < speaker->target_gain_q15) {
        speaker->current_gain_q15 += COMP_SPEAKER_GAIN_RAMP_STEP_Q15;
        if (speaker->current_gain_q15 > speaker->target_gain_q15) {
            speaker->current_gain_q15 = speaker->target_gain_q15;
        }
    } else if (speaker->current_gain_q15 > speaker->target_gain_q15) {
        speaker->current_gain_q15 -= COMP_SPEAKER_GAIN_RAMP_STEP_Q15;
        if (speaker->current_gain_q15 < speaker->target_gain_q15) {
            speaker->current_gain_q15 = speaker->target_gain_q15;
        }
    }

    /* PCM16 times a validated0..32767 gain fits signed32 exactly. */
    scaled = (int32_t)sample * speaker->current_gain_q15;
    scaled /= COMP_SPEAKER_GAIN_ONE_Q15;
    if (scaled > INT16_MAX) {
        speaker->clipped_samples++;
        return INT16_MAX;
    }
    if (scaled < INT16_MIN) {
        speaker->clipped_samples++;
        return INT16_MIN;
    }
    return (int16_t)scaled;
}

static const comp_speaker_clip_t *cue_clip(const comp_speaker_t *speaker,
                                           comp_speaker_cue_t cue)
{
    if(!speaker || !speaker->pet_voice || !speaker->cue_library ||
       (unsigned)cue>=COMP_SPEAKER_CLIP_CUE_COUNT)return NULL;
    const comp_speaker_clip_t *clip=&speaker->cue_library->cues[(unsigned)cue];
    return clip->data?clip:NULL;
}

static uint16_t cue_duration_frames(comp_speaker_cue_t cue,
                                     const comp_speaker_t *speaker)
{
    if(cue>=COMP_SPEAKER_CUE_REFERENCE_1K && cue<=COMP_SPEAKER_CUE_REFERENCE_2K)
        return 16000u; /* One second, never an open-ended stream. */
    const comp_speaker_clip_t *clip=cue_clip(speaker,cue);
    if(clip)return clip->frames;
    if(speaker && speaker->pet_voice) {
        switch(cue) {
        case COMP_SPEAKER_CUE_CONFIRM: return 1408u;
        case COMP_SPEAKER_CUE_RECORDING_STARTED: return 3200u;
        case COMP_SPEAKER_CUE_RECORDING_STOPPED:
        case COMP_SPEAKER_CUE_ERROR: return 3840u;
        case COMP_SPEAKER_CUE_PET_GREETING: return 3200u;
        case COMP_SPEAKER_CUE_PET_CONTENT: return 1920u;
        case COMP_SPEAKER_CUE_PET_PLAYFUL: return 2816u;
        case COMP_SPEAKER_CUE_PET_SHY: return 1536u;
        default: return 0u;
        }
    }
    switch (cue) {
    case COMP_SPEAKER_CUE_CONFIRM:
        return 1280u;
    case COMP_SPEAKER_CUE_RECORDING_STARTED:
    case COMP_SPEAKER_CUE_RECORDING_STOPPED:
        return 1920u;
    case COMP_SPEAKER_CUE_ERROR:
        return 2560u;
    default:
        return 0u;
    }
}

static uint16_t cue_frequency(const comp_speaker_t *speaker)
{
    uint16_t elapsed = (uint16_t)(speaker->cue_frames_total -
                                  speaker->cue_frames_remaining);
    bool second_half = elapsed >= (speaker->cue_frames_total / 2u);

    switch (speaker->cue) {
    case COMP_SPEAKER_CUE_CONFIRM:
        return 988u;
    case COMP_SPEAKER_CUE_RECORDING_STARTED:
        return second_half ? 880u : 659u;
    case COMP_SPEAKER_CUE_RECORDING_STOPPED:
        return second_half ? 659u : 880u;
    case COMP_SPEAKER_CUE_ERROR:
        return ((elapsed / 320u) & 1u) != 0u ? 0u : 247u;
    default:
        return 0u;
    }
}

/* Quarter-wave interpolation, no floating point, heap or sample buffers. */
static int32_t pet_sine(uint32_t phase)
{
    static const int16_t quarter[33]={0,1608,3212,4808,6393,7962,9512,11039,
        12539,14010,15446,16846,18204,19519,20787,22005,23170,24279,25329,
        26319,27245,28105,28898,29621,30273,30852,31356,31785,32137,32412,
        32609,32728,32767};
    uint32_t angle=phase&0x3FFFFFFFu;
    if(phase&0x40000000u)angle=0x40000000u-angle;
    uint32_t index=angle>>25;
    int32_t value=quarter[index];
    if(index<32u)value+=((quarter[index+1u]-value)*(int32_t)((angle>>10)&32767u))/32768;
    return (phase&0x80000000u)?-value:value;
}
/* Exact ((uint64_t)n <<32)/16000 modulo32 for cue inputs n<=107520.
 * 2^32=268435*16000+7296; both remainder products fit32. */
static uint32_t phase_16k(uint32_t n)
{ return n*268435u+(n*7296u)/16000u; }

/* Owner chose ordinary electronic feedback after rejecting vocal references.
 * Use steady sine notes with a finite envelope, without pitch glides, flutter
 * or added harmonics. Wire meanings, volume and admission policy stay shared. */
static int16_t next_pet_hint_sample(comp_speaker_t *speaker)
{
    uint32_t local=speaker->cue_frames_total-speaker->cue_frames_remaining;
    uint32_t span=speaker->cue_frames_total;
    uint32_t frequency=880u;
    switch(speaker->cue) {
    case COMP_SPEAKER_CUE_PET_GREETING:
        span=1152u;
        if(local>=1152u && local<1536u)return 0;
        if(local>=1536u) {local-=1536u;span=1664u;frequency=880u;}
        else frequency=659u;
        break;
    case COMP_SPEAKER_CUE_PET_CONTENT: frequency=784u;break;
    case COMP_SPEAKER_CUE_PET_PLAYFUL:
        span=1024u;
        if(local>=1024u && local<1280u)return 0;
        if(local>=1280u) {local-=1280u;span=1536u;frequency=988u;}
        else frequency=784u;
        break;
    case COMP_SPEAKER_CUE_PET_SHY: frequency=698u;break;
    default: break; /* Confirm. */
    }
    speaker->cue_phase+=phase_16k(frequency);
    const uint32_t remaining=span-1u-local;
    int32_t envelope=32767;
    if(local<128u)envelope=(int32_t)(local*32767u/128u);
    if(remaining<640u && (int32_t)(remaining*32767u/640u)<envelope)
        envelope=(int32_t)(remaining*32767u/640u);
    const int32_t squared=(envelope*envelope)/32767;
    envelope=(squared*(32767-envelope))/32767*2+squared;
    int32_t sample=(pet_sine(speaker->cue_phase)*envelope)/32767;
    return (int16_t)((sample*COMP_SPEAKER_CUE_AMPLITUDE)/32767);
}

static int16_t next_pet_sample(comp_speaker_t *speaker)
{
    if(speaker->cue==COMP_SPEAKER_CUE_CONFIRM ||
       (speaker->cue>=COMP_SPEAKER_CUE_PET_GREETING &&
        speaker->cue<=COMP_SPEAKER_CUE_PET_SHY))
        return next_pet_hint_sample(speaker);
    /* Keep recording/connection/error cue PCM unchanged. These system cues
     * also own the recording-start acoustic gate. */
    uint32_t elapsed=speaker->cue_frames_total-speaker->cue_frames_remaining;
    uint32_t local=elapsed,span=speaker->cue_frames_total;
    int32_t frequency=0,modulation=32767;
    if(speaker->cue==COMP_SPEAKER_CUE_RECORDING_STARTED) {
        span=1408u;
        if(elapsed>=1408u && elapsed<1792u)return 0;
        if(elapsed>=1792u)local-=1792u;
        frequency=(elapsed<1408u?720:1120)+(int32_t)(local*400u/span);
    } else if(speaker->cue==COMP_SPEAKER_CUE_RECORDING_STOPPED) {
        frequency=380-(int32_t)(local*140u/span);
        /* 28 Hz soft amplitude flutter, a brief contented purr. */
        modulation=24575+pet_sine(phase_16k(elapsed*28u))/4;
    } else {
        span=1792u;
        if(elapsed>=1792u && elapsed<2048u)return 0;
        if(elapsed>=2048u)local-=2048u;
        frequency=elapsed<1792u?520-(int32_t)(local*140u/span):430+(int32_t)(local*190u/span);
    }
    speaker->cue_phase+=phase_16k((uint32_t)frequency);
    int32_t voice=(pet_sine(speaker->cue_phase)*7+
                   pet_sine(speaker->cue_phase*2u))/8;
    uint32_t remaining=span-1u-local;
    int32_t envelope=32767;
    if(local<192u)envelope=(int32_t)(local*32767u/192u);
    if(remaining<640u && (int32_t)(remaining*32767u/640u)<envelope)
        envelope=(int32_t)(remaining*32767u/640u);
    /* Smoothstep avoids sudden slope changes at each syllable's boundaries. */
    int32_t squared=(envelope*envelope)/32767;
    envelope=(squared*(32767-envelope))/32767*2+squared;
    voice=(voice*envelope)/32767;
    voice=(voice*modulation)/32767;
    return (int16_t)((voice*COMP_SPEAKER_CUE_AMPLITUDE)/32767);
}
/* Intel/DVI4bit ADPCM, high nibble first, explicit initial state.
 * State fits the existing cue_phase word, unused by sampled clips. */
static int16_t next_clip_sample(comp_speaker_t *speaker,
                                 const comp_speaker_clip_t *clip)
{
    const unsigned elapsed=speaker->cue_frames_total-speaker->cue_frames_remaining;
    if(clip->format==COMP_SPEAKER_CLIP_PCM16_LE) {
        const unsigned raw=(unsigned)clip->data[elapsed*2u] |
                           ((unsigned)clip->data[elapsed*2u+1u]<<8);
        return (int16_t)(raw<32768u?(int32_t)raw:(int32_t)raw-65536);
    }
    static const int16_t steps[89]={7,8,9,10,11,12,13,14,16,17,19,21,23,25,
        28,31,34,37,41,45,50,55,60,66,73,80,88,97,107,118,130,143,157,173,
        190,209,230,253,279,307,337,371,408,449,494,544,598,658,724,796,
        876,963,1060,1166,1282,1411,1552,1707,1878,2066,2272,2499,2749,
        3024,3327,3660,4026,4428,4871,5358,5894,6484,7132,7845,8630,
        9493,10442,11487,12635,13899,15289,16818,18500,20350,22385,
        24623,27086,29794,32767};
    static const int8_t adjustment[8]={-1,-1,-1,-1,2,4,6,8};
    unsigned nibble=clip->data[elapsed/2u];
    nibble=(elapsed&1u)?nibble&15u:nibble>>4;
    int index=(int)((speaker->cue_phase>>16)&255u);
    const unsigned raw=speaker->cue_phase&65535u;
    int32_t prediction=raw<32768u?(int32_t)raw:(int32_t)raw-65536;
    const int32_t step=steps[index];
    int32_t difference=step>>3;
    if(nibble&1u)difference+=step>>2;
    if(nibble&2u)difference+=step>>1;
    if(nibble&4u)difference+=step;
    prediction+=(nibble&8u)?-difference:difference;
    if(prediction>32767)prediction=32767;
    if(prediction< -32768)prediction= -32768;
    index+=adjustment[nibble&7u];
    if(index<0)index=0;
    if(index>88)index=88;
    speaker->cue_phase=(uint32_t)(uint16_t)prediction|((uint32_t)index<<16);
    return (int16_t)prediction;
}

static int16_t next_cue_sample(comp_speaker_t *speaker)
{
    const comp_speaker_clip_t *clip=cue_clip(speaker,speaker->cue);
    if(clip)return next_clip_sample(speaker,clip);

    if(speaker->cue>=COMP_SPEAKER_CUE_REFERENCE_1K &&
       speaker->cue<=COMP_SPEAKER_CUE_REFERENCE_2K) {
        const uint32_t frequency=1000u+
            ((unsigned)speaker->cue-(unsigned)COMP_SPEAKER_CUE_REFERENCE_1K)*500u;
        speaker->cue_phase+=phase_16k(frequency);
        return (int16_t)((pet_sine(speaker->cue_phase)*COMP_SPEAKER_CUE_AMPLITUDE)/32767);
    }
    if(speaker->pet_voice)return next_pet_sample(speaker);
    uint16_t frequency = cue_frequency(speaker);
    int32_t triangle;

    if (frequency == 0u) {
        return 0;
    }
    speaker->cue_phase += phase_16k(frequency);
    triangle = (int32_t)((speaker->cue_phase >> 16) & 0xffffu);
    triangle = triangle < 32768 ? triangle : 65535 - triangle;
    triangle = (triangle * (COMP_SPEAKER_CUE_AMPLITUDE * 2)) / 32767 -
               COMP_SPEAKER_CUE_AMPLITUDE;
    return (int16_t)triangle;
}

static void finish(comp_speaker_t *speaker)
{
    if (!speaker->config.set_amplifier_enabled(speaker->config.context, false)) {
        enter_fault(speaker);
        return;
    }
    speaker->state = COMP_SPEAKER_STATE_SHUTDOWN;
    speaker->last_error = COMP_SPEAKER_OK;
    speaker->tx_pending = false;
    speaker->stop_requested = false;
    speaker->drain_requested = false;
    speaker->cue_active = false;
    speaker->fifo_count = 0u;
    speaker->current_gain_q15 = 0;
    speaker->target_gain_q15 = 0;
    set_activity(speaker, false);
}

void comp_speaker_init(comp_speaker_t *speaker,
                       const comp_speaker_config_t *config)
{
    if (speaker == NULL) {
        return;
    }
    memset(speaker, 0, sizeof(*speaker));
    speaker->state = COMP_SPEAKER_STATE_SHUTDOWN;
    speaker->volume_percent = 50u;
    if (config != NULL) {
        speaker->config = *config;
    }
}

bool comp_speaker_ready(const comp_speaker_t *speaker)
{
    return speaker != NULL &&
           speaker->config.set_amplifier_enabled != NULL &&
           speaker->config.submit_i2s != NULL;
}

comp_speaker_result_t comp_speaker_set_pet_voice(comp_speaker_t *speaker,bool enabled)
{
    if(speaker==NULL)return COMP_SPEAKER_BAD_ARGUMENT;
    if(speaker->state!=COMP_SPEAKER_STATE_SHUTDOWN)return COMP_SPEAKER_BUSY;
    speaker->pet_voice=enabled;
    return COMP_SPEAKER_OK;
}

comp_speaker_result_t comp_speaker_set_cue_library(
    comp_speaker_t *speaker,const comp_speaker_cue_library_t *library)
{
    if(!speaker)return COMP_SPEAKER_BAD_ARGUMENT;
    if(speaker->state!=COMP_SPEAKER_STATE_SHUTDOWN)return COMP_SPEAKER_BUSY;
    if(library)for(unsigned i=0u;i<COMP_SPEAKER_CLIP_CUE_COUNT;++i) {
        const comp_speaker_clip_t *clip=&library->cues[i];
        if(!clip->data) {
            if(clip->frames || clip->bytes || clip->format ||
               clip->initial_predictor || clip->initial_step_index)
                return COMP_SPEAKER_BAD_ARGUMENT;
            continue;
        }
        if((i>=1u && i<=3u) || clip->frames<COMP_SPEAKER_CLIP_MIN_FRAMES ||
           clip->frames>COMP_SPEAKER_CLIP_MAX_FRAMES)
            return COMP_SPEAKER_BAD_ARGUMENT;
        if(clip->format==COMP_SPEAKER_CLIP_PCM16_LE) {
            if(clip->bytes!=(unsigned)clip->frames*2u ||
               clip->initial_predictor || clip->initial_step_index)
                return COMP_SPEAKER_BAD_ARGUMENT;
        } else if(clip->format==COMP_SPEAKER_CLIP_IMA_ADPCM) {
            if(clip->bytes!=((unsigned)clip->frames+1u)/2u ||
               clip->initial_step_index>88u)return COMP_SPEAKER_BAD_ARGUMENT;
        } else return COMP_SPEAKER_BAD_ARGUMENT;
    }
    speaker->cue_library=library;
    return COMP_SPEAKER_OK;
}

static comp_speaker_result_t start(comp_speaker_t *speaker)
{
    if (!comp_speaker_ready(speaker)) {
        return COMP_SPEAKER_BAD_ARGUMENT;
    }
    /* A hardware failure is terminal until explicit board recovery. Returning
     * BUSY here keeps queued error/stop cues pending forever, also blocking
     * diagnostics and power policy after recording has already stopped. */
    if (speaker->state == COMP_SPEAKER_STATE_FAULT) {
        return COMP_SPEAKER_IO_ERROR;
    }
    if (speaker->state != COMP_SPEAKER_STATE_SHUTDOWN) {
        return COMP_SPEAKER_BUSY;
    }
    if (!speaker->config.set_amplifier_enabled(speaker->config.context, true)) {
        enter_fault(speaker);
        return COMP_SPEAKER_IO_ERROR;
    }
    ++speaker->playback_generation;
    if (speaker->playback_generation == 0u) { ++speaker->playback_generation; }
    speaker->state = COMP_SPEAKER_STATE_STARTING;
    speaker->last_error = COMP_SPEAKER_OK;
    speaker->current_gain_q15 = 0;
    speaker->target_gain_q15 = requested_gain(speaker);
    speaker->stop_requested = false;
    speaker->drain_requested = false;
    speaker->fifo_head = 0u;
    speaker->fifo_count = 0u;
    speaker->cue_frames_total = 0u;
    set_activity(speaker, true);
    return COMP_SPEAKER_OK;
}

#if !COMP_SPEAKER_CUES_ONLY
comp_speaker_result_t comp_speaker_start_stream(comp_speaker_t *speaker)
{
    return start(speaker);
}

size_t comp_speaker_write_pcm16(comp_speaker_t *speaker,
                                const int16_t *mono_pcm,
                                size_t frame_count)
{
    size_t accepted = 0u;

    if (speaker == NULL || mono_pcm == NULL || speaker->cue_frames_total != 0u ||
        (speaker->state != COMP_SPEAKER_STATE_STARTING &&
         speaker->state != COMP_SPEAKER_STATE_PLAYING)) {
        return 0u;
    }
    while (accepted < frame_count &&
           speaker->fifo_count < COMP_SPEAKER_FIFO_FRAMES) {
        uint16_t tail = (uint16_t)((speaker->fifo_head + speaker->fifo_count) %
                                   COMP_SPEAKER_FIFO_FRAMES);
        speaker->fifo[tail] = mono_pcm[accepted++];
        speaker->fifo_count++;
    }
    return accepted;
}

#endif
comp_speaker_result_t comp_speaker_play_cue(comp_speaker_t *speaker,
                                            comp_speaker_cue_t cue)
{
    uint16_t frames = cue_duration_frames(cue,speaker);
    comp_speaker_result_t result;

    if (frames == 0u) {
        return COMP_SPEAKER_BAD_ARGUMENT;
    }
    result = start(speaker);
    if (result != COMP_SPEAKER_OK) {
        return result;
    }
    speaker->cue = cue;
    speaker->cue_active = true;
    speaker->cue_frames_total = frames;
    speaker->cue_frames_remaining = frames;
    const comp_speaker_clip_t *clip=cue_clip(speaker,cue);
    speaker->cue_phase = clip?
        (uint32_t)(uint16_t)clip->initial_predictor |
        ((uint32_t)clip->initial_step_index<<16):0u;
    return COMP_SPEAKER_OK;
}

comp_speaker_result_t comp_speaker_stop(comp_speaker_t *speaker, bool drain)
{
    if (speaker == NULL) {
        return COMP_SPEAKER_BAD_ARGUMENT;
    }
    if (speaker->state == COMP_SPEAKER_STATE_SHUTDOWN) {
        return COMP_SPEAKER_NOT_RUNNING;
    }
    if (speaker->state == COMP_SPEAKER_STATE_FAULT) {
        return COMP_SPEAKER_IO_ERROR;
    }
    speaker->stop_requested = true;
    speaker->drain_requested = drain;
    speaker->state = COMP_SPEAKER_STATE_STOPPING;
    speaker->target_gain_q15 = 0;
    if (!drain) {
        speaker->fifo_count = 0u;
        speaker->cue_active = false;
        if (!speaker->tx_pending) {
            finish(speaker);
        }
    }
    return COMP_SPEAKER_OK;
}

comp_speaker_result_t comp_speaker_set_volume(comp_speaker_t *speaker,
                                              uint8_t percent)
{
    if (speaker == NULL || percent > 100u) {
        return COMP_SPEAKER_BAD_ARGUMENT;
    }
    speaker->volume_percent = percent;
    refresh_target_gain(speaker);
    return COMP_SPEAKER_OK;
}

void comp_speaker_set_muted(comp_speaker_t *speaker, bool muted)
{
    if (speaker == NULL) {
        return;
    }
    speaker->muted = muted;
    refresh_target_gain(speaker);
}

static uint8_t prepare_block(comp_speaker_t *speaker, int16_t *stereo, bool starting)
{
    size_t frame;
    bool source_empty = false;

    uint8_t flags=COMP_SPEAKER_CUE_PREFILLED | (starting?4u:0u);
    if (starting) {
        memset(stereo, 0, sizeof(speaker->tx_stereo));
    } else {
        if (!speaker->cue_active && speaker->fifo_count == 0u &&
            !speaker->stop_requested) {
            return false;
        }
        for (frame = 0u; frame < COMP_SPEAKER_BLOCK_FRAMES; ++frame) {
            int16_t mono = 0;
            if (speaker->cue_active && speaker->cue_frames_remaining > 0u) {
                refresh_target_gain(speaker);
                mono = next_cue_sample(speaker);
                speaker->cue_frames_remaining--;
                if (speaker->cue_frames_remaining == 0u) {
                    speaker->cue_active = false;
                    speaker->stop_requested = true;
                    speaker->state = COMP_SPEAKER_STATE_STOPPING;
                }
            } else if (speaker->fifo_count > 0u) {
                refresh_target_gain(speaker);
                mono = speaker->fifo[speaker->fifo_head];
                speaker->fifo_head = (uint16_t)((speaker->fifo_head + 1u) %
                                                COMP_SPEAKER_FIFO_FRAMES);
                speaker->fifo_count--;
            } else {
                source_empty = true;
            }
            mono = scale_sample(speaker, mono);
            stereo[frame * 2u] = mono;
            stereo[frame * 2u + 1u] = mono;
        }
        if (speaker->stop_requested && speaker->fifo_count == 0u &&
            !speaker->cue_active && speaker->current_gain_q15 == 0) {
            flags|=COMP_SPEAKER_CUE_PREFILL_FINAL;
        } else if (source_empty && !speaker->stop_requested) {
            speaker->underruns++;
        }
    }

    return flags;
}

uint8_t comp_speaker_cue_prefill(comp_speaker_t *speaker)
{
    if (speaker == NULL || !speaker->tx_pending ||
        speaker->cue_frames_total == 0u || speaker->pending_finishes_audio) return 0u;
    _Static_assert(sizeof(speaker->fifo) >= sizeof(speaker->tx_stereo),
                   "Cue lookahead must fit the idle PCM FIFO");
    return prepare_block(speaker,speaker->fifo,false);
}

bool comp_speaker_cue_advance(comp_speaker_t *speaker,uint8_t prefilled)
{
    if (speaker == NULL || !(prefilled&COMP_SPEAKER_CUE_PREFILLED) ||
        !speaker->tx_pending ||
        (speaker->stop_requested && !speaker->drain_requested &&
         speaker->cue_frames_remaining != 0u)) return false;
    /* Valid lookahead was prepared only for a nonterminal in-flight block.
     * Foreground cannot replace block metadata while tx_pending; entering
     * FAULT clears tx_pending, so no duplicate state/final check is needed. */
    ++speaker->completed_blocks;
    speaker->played_frames+=COMP_SPEAKER_BLOCK_FRAMES;
    if (speaker->state==COMP_SPEAKER_STATE_STARTING)
        speaker->state=COMP_SPEAKER_STATE_PLAYING;
    memcpy(speaker->tx_stereo,speaker->fifo,sizeof(speaker->tx_stereo));
    /* A quiet/mute request between half and full completion must not emit
     * the already prepared nonzero block. Never touch the live DMA half. */
    if (speaker->muted || speaker->volume_percent==0u) memset(speaker->tx_stereo,0,sizeof(speaker->tx_stereo));
    speaker->pending_starts_audio=false;
    speaker->pending_finishes_audio=(prefilled&COMP_SPEAKER_CUE_PREFILL_FINAL)!=0u;
    return true;
}

bool comp_speaker_service(comp_speaker_t *speaker)
{
    if (!comp_speaker_ready(speaker) || speaker->tx_pending ||
        speaker->state == COMP_SPEAKER_STATE_SHUTDOWN ||
        speaker->state == COMP_SPEAKER_STATE_FAULT) return false;
    const uint8_t flags=prepare_block(speaker,speaker->tx_stereo,
        speaker->state==COMP_SPEAKER_STATE_STARTING);
    if (!flags) return false;
    speaker->pending_starts_audio=(flags&4u)!=0u;
    speaker->pending_finishes_audio=(flags&COMP_SPEAKER_CUE_PREFILL_FINAL)!=0u;
    if (!speaker->config.submit_i2s(speaker->config.context,
                                    speaker->tx_stereo,
                                    COMP_SPEAKER_BLOCK_FRAMES)) {
        enter_fault(speaker);
        return false;
    }
    speaker->tx_pending = true;
    speaker->submitted_blocks++;
    return true;
}

void comp_speaker_tx_complete(comp_speaker_t *speaker, bool success)
{
    if (speaker == NULL || !speaker->tx_pending) {
        return;
    }
    speaker->tx_pending = false;
    if (!success) {
        enter_fault(speaker);
        return;
    }
    speaker->completed_blocks++;
    speaker->played_frames += COMP_SPEAKER_BLOCK_FRAMES;
    if (speaker->pending_starts_audio) {
        speaker->pending_starts_audio = false;
        speaker->state = COMP_SPEAKER_STATE_PLAYING;
    }
    if (speaker->pending_finishes_audio) {
        speaker->pending_finishes_audio = false;
        finish(speaker);
    }
}

bool comp_speaker_active(const comp_speaker_t *speaker)
{
    return speaker != NULL && speaker->state != COMP_SPEAKER_STATE_SHUTDOWN &&
           speaker->state != COMP_SPEAKER_STATE_FAULT;
}

#if !COMP_SPEAKER_CUES_ONLY
size_t comp_speaker_writable_frames(const comp_speaker_t *speaker)
{
    if (speaker == NULL) {
        return 0u;
    }
    return COMP_SPEAKER_FIFO_FRAMES - speaker->fifo_count;
}

#endif
const char *comp_speaker_state_name(comp_speaker_state_t state)
{
    switch (state) {
    case COMP_SPEAKER_STATE_SHUTDOWN: return "shutdown";
    case COMP_SPEAKER_STATE_STARTING: return "starting";
    case COMP_SPEAKER_STATE_PLAYING: return "playing";
    case COMP_SPEAKER_STATE_STOPPING: return "stopping";
    case COMP_SPEAKER_STATE_FAULT: return "fault";
    default: return "unknown";
    }
}

const char *comp_speaker_result_name(comp_speaker_result_t result)
{
    switch (result) {
    case COMP_SPEAKER_OK: return "ok";
    case COMP_SPEAKER_BAD_ARGUMENT: return "bad_argument";
    case COMP_SPEAKER_BUSY: return "busy";
    case COMP_SPEAKER_NOT_RUNNING: return "not_running";
    case COMP_SPEAKER_IO_ERROR: return "io_error";
    default: return "unknown";
    }
}
