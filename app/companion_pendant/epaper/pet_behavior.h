#ifndef COMPANION_EPAPER_PET_BEHAVIOR_H
#define COMPANION_EPAPER_PET_BEHAVIOR_H

#include "pet_expression.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* This is deliberately a small emotional state, not an animation library.
 * Product events and touch update it; the renderer turns it into a pose. */
typedef enum {
    COMP_PET_ENGAGEMENT_REST = 0u,
    COMP_PET_ENGAGEMENT_NOTICE = 1u,
    COMP_PET_ENGAGEMENT_ENGAGED = 2u,
    COMP_PET_ENGAGEMENT_SETTLING = 3u,
} comp_pet_engagement_t;

typedef enum {
    COMP_PET_MOOD_CALM = 0u,
    COMP_PET_MOOD_CURIOUS = 1u,
    COMP_PET_MOOD_AFFECTIONATE = 2u,
    COMP_PET_MOOD_DELIGHTED = 3u,
    COMP_PET_MOOD_RESTFUL = 4u,
    COMP_PET_MOOD_WORRIED = 5u,
    COMP_PET_MOOD_COUNT,
} comp_pet_mood_t;

/* Finger travel is a different social cue from a point tap. Keep it in the
 * portable behavior layer so every target gets the same pet semantics after
 * it converts raw touch into logical display coordinates. */
typedef enum {
    COMP_PET_STROKE_NONE = 0u,
    COMP_PET_STROKE_LEFT,
    COMP_PET_STROKE_RIGHT,
    COMP_PET_STROKE_UP,
    COMP_PET_STROKE_DOWN,
} comp_pet_stroke_direction_t;

/* This is a target-owned persistence payload. The portable behavior layer
 * never writes Flash; WB55/WBA profile storage owns CRC, wear limits, and
 * coalesced commits. */
typedef struct {
    uint8_t schema_version;
    int8_t valence;
    uint8_t arousal;
    uint8_t curiosity;
    uint8_t affection;
    uint8_t attachment;
    uint8_t reserved[2];
    uint32_t interaction_count;
    uint32_t personality_seed;
} comp_pet_behavior_memory_t;

typedef struct {
    int8_t valence;
    uint8_t arousal;
    uint8_t curiosity;
    uint8_t affection;
    uint8_t attachment;
    uint8_t sociability;
    uint8_t sensitivity;
    uint8_t playfulness;
    comp_pet_mood_t mood;
    comp_pet_engagement_t engagement;
    uint16_t focus_x;
    uint16_t focus_y;
    uint32_t interaction_count;
    uint32_t quiet_elapsed_ms;
    uint32_t personality_seed;
    comp_pet_stroke_direction_t last_stroke;
    uint8_t stroke_energy;
    bool focus_valid;
} comp_pet_behavior_t;

void comp_pet_behavior_init(comp_pet_behavior_t *behavior, uint32_t personality_seed);
void comp_pet_behavior_advance(comp_pet_behavior_t *behavior, uint32_t elapsed_ms);
void comp_pet_behavior_apply_expression(comp_pet_behavior_t *behavior,
                                        comp_epaper_expression_t expression);
void comp_pet_behavior_note_touch(comp_pet_behavior_t *behavior,
                                  uint16_t x,
                                  uint16_t y,
                                  uint16_t width,
                                  uint16_t height);
comp_pet_stroke_direction_t comp_pet_behavior_stroke_direction(uint16_t start_x,
                                                                uint16_t start_y,
                                                                uint16_t end_x,
                                                                uint16_t end_y);
const char *comp_pet_behavior_stroke_name(comp_pet_stroke_direction_t direction);
void comp_pet_behavior_note_stroke(comp_pet_behavior_t *behavior,
                                   uint16_t start_x,
                                   uint16_t start_y,
                                   uint16_t end_x,
                                   uint16_t end_y,
                                   uint16_t width,
                                   uint16_t height,
                                   uint32_t duration_ms);
void comp_pet_behavior_compose_expression_pose(
    const comp_pet_behavior_t *behavior,
    comp_epaper_expression_t expression,
    uint8_t phase,
    uint32_t variation_seed,
    comp_pet_expression_pose_t *out_pose);
void comp_pet_behavior_compose_touch_pose(const comp_pet_behavior_t *behavior,
                                          uint16_t x,
                                          uint16_t y,
                                          uint16_t width,
                                          uint16_t height,
                                          uint8_t phase,
                                          uint32_t variation_seed,
                                          comp_pet_expression_pose_t *out_pose);
void comp_pet_behavior_compose_stroke_pose(const comp_pet_behavior_t *behavior,
                                           uint16_t end_x,
                                           uint16_t end_y,
                                           uint16_t width,
                                           uint16_t height,
                                           uint8_t phase,
                                           uint32_t variation_seed,
                                           comp_pet_expression_pose_t *out_pose);
comp_pet_mood_t comp_pet_behavior_mood(const comp_pet_behavior_t *behavior);
const char *comp_pet_behavior_mood_name(comp_pet_mood_t mood);
bool comp_pet_behavior_export_memory(const comp_pet_behavior_t *behavior,
                                     comp_pet_behavior_memory_t *out_memory);
bool comp_pet_behavior_import_memory(comp_pet_behavior_t *behavior,
                                     const comp_pet_behavior_memory_t *memory);
uint32_t comp_pet_behavior_self_test_failure_code(void);
bool comp_pet_behavior_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_PET_BEHAVIOR_H */
