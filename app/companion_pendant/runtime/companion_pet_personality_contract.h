#ifndef COMPANION_PET_PERSONALITY_CONTRACT_H
#define COMPANION_PET_PERSONALITY_CONTRACT_H

#include "companion_pet_behavior.h"

/* Reserved contract only. No profile store, chat service, microphone session
 * or speech playback is enabled by including this header. These C structs
 * are not a persistent or wire encoding; adapters must validate/version data. */
#define COMP_PET_PERSONALITY_SCHEMA 1u

typedef struct {
    uint16_t schema_version;
    uint8_t pet_id[16];       /* Stable per pet, not regenerated at startup. */
    uint32_t character_seed; /* Stable individual habits; not action entropy. */
    char mbti_hint[5];       /* Optional fictional label, e.g. "INFP" or "". */
    uint8_t sociability;     /* All four creative traits are 0..100. */
    uint8_t curiosity;
    uint8_t expressiveness;
    uint8_t calmness;
} comp_pet_personality_profile_t;

typedef enum {
    COMP_PET_REPLY_WAITING,
    COMP_PET_REPLY_READY,
    COMP_PET_REPLY_CANCELLED,
    COMP_PET_REPLY_OFFLINE,
    COMP_PET_REPLY_FAILED
} comp_pet_reply_state_t;

typedef enum {
    COMP_PET_AUDIO_NONE,
    COMP_PET_AUDIO_CUE,
    COMP_PET_AUDIO_VOCAL,
    COMP_PET_AUDIO_SPEECH_RESERVED
} comp_pet_reply_audio_t;

typedef struct {
    uint32_t request_id;      /* Reject cancelled/stale conversation replies. */
    uint32_t reply_sequence;
    comp_pet_reply_state_t state;
    comp_browser_family_t expression_intent;
    uint8_t intensity;        /* 0..100, clamped by the panel choreography. */
    const char *text_utf8;    /* Borrowed whole reply; adapter owns lifetime. */
    uint16_t text_bytes;      /* No implicit truncation of UTF-8/whole phrases. */
    comp_pet_reply_audio_t audio;
    uint32_t audio_asset_id;  /* Zero means absent; speech requires capability. */
} comp_pet_reply_envelope_t;

/* Future adapters load one durable profile and pass complete semantic replies.
 * The screen alone schedules visible frames after actual panel completion.
 * Quiet mode, recording ownership, cancellation and unavailable capabilities
 * take precedence. No implementation or persistent allocation is registered. */
typedef bool (*comp_pet_profile_load_fn)(void *context,
    comp_pet_personality_profile_t *profile);
typedef bool (*comp_pet_reply_submit_fn)(void *context,
    const comp_pet_reply_envelope_t *reply);

#endif
