#ifndef COMPANION_PET_BEHAVIOR_H
#define COMPANION_PET_BEHAVIOR_H
#include "browser_interaction_runtime.h"
#include <stdbool.h>
#include <stdint.h>
#if COMPANION_WBA_RESOURCE_PROFILE
#include "companion_wba_resource_contract.h"
#endif
#if COMPANION_WBA_RESOURCE_PROFILE && COMPANION_WBA_RESOURCE_GENERATION >= 66u
#define COMP_PET_PROCEDURAL 1
#else
#define COMP_PET_PROCEDURAL 0
#endif

typedef enum {
    COMP_PET_IDLE, COMP_PET_HEAD_PAT, COMP_PET_CHEEK, COMP_PET_NOSE,
    COMP_PET_CHIN, COMP_PET_PICKUP, COMP_PET_SHAKE, COMP_PET_SETTLE,
    COMP_PET_TILT, COMP_PET_INVERTED, COMP_PET_GREETING
} comp_pet_interaction_t;

/* Contextual whole-face accents supplement the original ten families.
 * Resource capability, not the enum alone, enables their new rasters. */
typedef enum {
    COMP_PET_ACCENT_NONE, COMP_PET_ACCENT_ANTICIPATING,
    COMP_PET_ACCENT_PUZZLED, COMP_PET_ACCENT_RELIEVED,
    COMP_PET_ACCENT_DEJECTED, COMP_PET_ACCENT_PROTEST, COMP_PET_ACCENT_NERVOUS,
    COMP_PET_ACCENT_PROUD
} comp_pet_accent_t;
_Static_assert(COMP_PET_ACCENT_PROUD<8u,"pet accent exceeds private frame bits");

/* An accepted interaction chooses one intent. Parts and all visible phases
 * derive from its seed; panel retries never choose another expression. */
typedef struct {
    uint32_t seed, last_input_ms, life_key; /* last_input_ms is accepted-input trace time. */
    uint32_t character_seed; /* Stable device-owned habits; never hardware RNG. */
    /* Brief emotional afterglow from a genuinely visible touch/greeting peak.
     * Zero family code means unavailable; this is not persistent personality. */
    uint32_t attention_visible_ms; /* Latest visible affection / first visible motion peak. */
    /* Optional speech is a rare accent. Cooldown starts at real visibility,
     * not a contact, render attempt, retry or failed panel transaction. */
    uint32_t caption_visible_ms;
    uint16_t peak_hold_ms;
    uint8_t interaction, last_interaction, repetitions, intensity; /* Last two are visible history / strength. */
    uint8_t first_family, second_family, first_zone, second_zone;
    uint8_t personality_code; /* Zero retains legacy behavior, otherwise type+1. */
    /* Low4 bits: afterglow family+1. High3: last visibly shown head-pat zone.
     * Both histories survive cancelled candidate replies; no new RAM bytes. */
    uint8_t attention_family_code;
    bool caption_selected : 1;
    bool caption_committed : 1;
    uint8_t accent : 3; /* Chosen once with the accepted interaction. */
    uint8_t pending_repetitions : 2; /* Proposed count; committed at visible first peak. */
} comp_pet_behavior_t;

void comp_pet_behavior_idle(comp_pet_behavior_t *, uint32_t entropy);
comp_browser_family_t comp_pet_behavior_idle_family(comp_browser_family_t current,
    uint32_t entropy);
void comp_pet_behavior_interact(comp_pet_behavior_t *, comp_pet_interaction_t,
    bool entropy_available, uint32_t entropy, uint16_t x, uint32_t now_ms);
/* Existing persisted interaction level: quiet=0, standard=1, lively=2.
 * Apply once to an accepted affection intent, before its route is scheduled. */
void comp_pet_behavior_apply_activity(comp_pet_behavior_t *,unsigned level,uint16_t x);
void comp_pet_behavior_set_personality(comp_pet_behavior_t *,unsigned type,uint32_t seed);
/* Uses only retained whole faces and the existing at-most-two-peak route.
 * Quiet/activity and physical completion gates still run afterwards. */
void comp_pet_behavior_apply_personality(comp_pet_behavior_t *);
comp_browser_family_t comp_pet_behavior_personal_idle(const comp_pet_behavior_t *,
    comp_browser_family_t current,uint32_t entropy);
uint32_t comp_pet_behavior_personal_gap(const comp_pet_behavior_t *,uint32_t baseline_ms);
/* A lift inherits the accepted feeling, with an original open-eye peak. Some
 * authored up poses are smiles with closed eyes, so retain their open centre
 * pose rather than turning spatial attention into another blink. */
void comp_pet_behavior_pickup_attention(comp_pet_behavior_t *,comp_browser_family_t);
/* Called only for the matching, successfully visible expression peak. */
void comp_pet_behavior_visible(comp_pet_behavior_t *, uint32_t visible_ms);
void comp_pet_behavior_caption_visible(comp_pet_behavior_t *, uint32_t visible_ms);
/* Call at each matching visible expressive peak, with its actual family.
 * A new contact can inherit that feeling briefly; a live contact keeps its
 * already accepted feeling. Failed frames/idle/reads never renew this age. */
void comp_pet_behavior_attention_visible(comp_pet_behavior_t *,
    comp_browser_family_t family, uint32_t visible_ms);
comp_browser_family_t comp_pet_behavior_attention_family(const comp_pet_behavior_t *,
    comp_browser_family_t fallback, uint32_t now_ms);
#endif
