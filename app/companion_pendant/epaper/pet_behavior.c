#include "pet_behavior.h"

#include <string.h>

#define COMP_PET_BEHAVIOR_MEMORY_SCHEMA_VERSION 1u
#define COMP_PET_BEHAVIOR_QUIET_MAX_MS 604800000u

static const char *const k_mood_names[COMP_PET_MOOD_COUNT] = {
    "calm",
    "curious",
    "affectionate",
    "delighted",
    "restful",
    "worried",
};

static const char *const k_stroke_names[] = {
    "none",
    "left",
    "right",
    "up",
    "down",
};

static uint32_t s_pet_behavior_self_test_failure_code = 0u;

uint32_t comp_pet_behavior_self_test_failure_code(void)
{
    return s_pet_behavior_self_test_failure_code;
}

static int8_t clamp_valence(int16_t value)
{
    if (value < -100) {
        return -100;
    }
    if (value > 100) {
        return 100;
    }
    return (int8_t)value;
}

static uint8_t clamp_percent(int16_t value, uint8_t minimum, uint8_t maximum)
{
    if (value < minimum) {
        return minimum;
    }
    if (value > maximum) {
        return maximum;
    }
    return (uint8_t)value;
}

static int8_t approach_zero(int8_t value, int8_t amount)
{
    if (value > amount) {
        return (int8_t)(value - amount);
    }
    if (value < -amount) {
        return (int8_t)(value + amount);
    }
    return 0;
}

static int8_t approach_valence(int8_t value, int8_t target, int8_t amount)
{
    if (value < target - amount) {
        return (int8_t)(value + amount);
    }
    if (value > target + amount) {
        return (int8_t)(value - amount);
    }
    return target;
}

static uint8_t approach_percent(uint8_t value, uint8_t target, uint8_t amount)
{
    if (value + amount < target) {
        return (uint8_t)(value + amount);
    }
    if (value > target + amount) {
        return (uint8_t)(value - amount);
    }
    return target;
}

static int8_t clamp_gaze(int16_t value)
{
    if (value < -32) {
        return -32;
    }
    if (value > 32) {
        return 32;
    }
    return (int8_t)value;
}

static uint16_t absolute_delta(uint16_t first, uint16_t second)
{
    return first >= second ? (uint16_t)(first - second) :
                             (uint16_t)(second - first);
}

static uint32_t saturating_add_ms(uint32_t current, uint32_t elapsed_ms)
{
    if (current >= COMP_PET_BEHAVIOR_QUIET_MAX_MS ||
        elapsed_ms >= COMP_PET_BEHAVIOR_QUIET_MAX_MS - current) {
        return COMP_PET_BEHAVIOR_QUIET_MAX_MS;
    }
    return current + elapsed_ms;
}

static uint8_t trait_from_seed(uint32_t seed, uint8_t shift, uint8_t base, uint8_t span)
{
    return (uint8_t)(base + ((seed >> shift) % span));
}

static void refresh_mood(comp_pet_behavior_t *behavior)
{
    if (behavior == NULL) {
        return;
    }
    if (behavior->valence <= -32) {
        behavior->mood = COMP_PET_MOOD_WORRIED;
    } else if (behavior->arousal <= 31u &&
               behavior->quiet_elapsed_ms >= 1800000u) {
        behavior->mood = COMP_PET_MOOD_RESTFUL;
    } else if (behavior->valence >= 54 && behavior->affection >= 62u) {
        behavior->mood = COMP_PET_MOOD_DELIGHTED;
    } else if (behavior->attachment >= 58u && behavior->valence >= 12) {
        behavior->mood = COMP_PET_MOOD_AFFECTIONATE;
    } else if (behavior->curiosity >= 58u && behavior->arousal >= 38u) {
        behavior->mood = COMP_PET_MOOD_CURIOUS;
    } else {
        behavior->mood = COMP_PET_MOOD_CALM;
    }
}

static int8_t clamp_face_shift(int16_t value)
{
    if (value < -18) {
        return -18;
    }
    if (value > 18) {
        return 18;
    }
    return (int8_t)value;
}

static uint8_t clamp_eye_spacing(int16_t value)
{
    if (value < 76) {
        return 76u;
    }
    if (value > 124) {
        return 124u;
    }
    return (uint8_t)value;
}

static void apply_visual_character(const comp_pet_behavior_t *behavior,
                                   uint8_t phase,
                                   comp_pet_expression_pose_t *pose)
{
    int16_t warmth;
    int16_t alertness;
    int16_t curiosity_bias;

    if (behavior == NULL || pose == NULL) {
        return;
    }
    warmth = behavior->valence / 5;
    alertness = ((int16_t)behavior->arousal - 50) / 3;
    curiosity_bias = ((int16_t)behavior->curiosity - 50) / 5;
    pose->eye_width = clamp_percent((int16_t)pose->eye_width + warmth +
                                        curiosity_bias,
                                    60u,
                                    140u);
    pose->highlight_scale = clamp_percent((int16_t)pose->highlight_scale +
                                              warmth - alertness / 2,
                                          60u,
                                          140u);
    pose->eye_open = clamp_percent((int16_t)pose->eye_open + alertness / 2,
                                   18u,
                                   100u);
    pose->eye_spacing = clamp_eye_spacing((int16_t)pose->eye_spacing - warmth / 3 +
                                          alertness / 8);
    pose->face_shift_x = clamp_face_shift((int16_t)pose->face_shift_x + pose->gaze_x / 10);
    pose->face_shift_y = clamp_face_shift((int16_t)pose->face_shift_y - alertness / 10);
    if (pose->expression == COMP_EPAPER_EXPRESSION_IDLE &&
        behavior->engagement == COMP_PET_ENGAGEMENT_REST) {
        pose->gaze_x = (int8_t)(pose->gaze_x +
                                 (int8_t)((behavior->personality_seed + phase) % 3u) -
                                 1);
    }
    if (behavior->engagement == COMP_PET_ENGAGEMENT_SETTLING &&
        pose->expression == COMP_EPAPER_EXPRESSION_IDLE) {
        pose->eye_open = clamp_percent((int16_t)pose->eye_open - 8,
                                       18u,
                                       100u);
        pose->face_shift_y = clamp_face_shift((int16_t)pose->face_shift_y + 2);
        pose->brow = COMP_PET_BROW_WARM;
    }
    if (pose->expression != COMP_EPAPER_EXPRESSION_IDLE) {
        return;
    }
    switch (comp_pet_behavior_mood(behavior)) {
    case COMP_PET_MOOD_CURIOUS:
        pose->gaze_x = clamp_gaze((int16_t)pose->gaze_x +
                                   (int8_t)((behavior->personality_seed + phase) % 5u) - 2);
        pose->brow = COMP_PET_BROW_RAISED;
        pose->brow_lift = clamp_percent((int16_t)pose->brow_lift + 8, 0u, 36u);
        pose->eye_spacing = clamp_eye_spacing((int16_t)pose->eye_spacing + 5);
        pose->mouth = COMP_PET_MOUTH_POUT;
        pose->mouth_scale = 82u;
        break;
    case COMP_PET_MOOD_AFFECTIONATE:
        pose->brow = COMP_PET_BROW_WARM;
        pose->brow_lift = clamp_percent((int16_t)pose->brow_lift + 4, 0u, 36u);
        pose->highlight_scale = clamp_percent((int16_t)pose->highlight_scale + 12,
                                              60u,
                                              140u);
        pose->eye_spacing = clamp_eye_spacing((int16_t)pose->eye_spacing - 4);
        pose->mouth = COMP_PET_MOUTH_SOFT;
        pose->mouth_scale = 96u;
        pose->cheek_strength = 1u;
        break;
    case COMP_PET_MOOD_DELIGHTED:
        pose->brow = COMP_PET_BROW_WARM;
        pose->brow_lift = clamp_percent((int16_t)pose->brow_lift + 6, 0u, 36u);
        pose->eye_spacing = clamp_eye_spacing((int16_t)pose->eye_spacing - 8);
        pose->mouth = COMP_PET_MOUTH_SMILE;
        pose->mouth_scale = 116u;
        pose->cheek_strength = 3u;
        break;
    case COMP_PET_MOOD_RESTFUL:
        pose->eye_open = clamp_percent((int16_t)pose->eye_open - 18, 18u, 100u);
        pose->brow = COMP_PET_BROW_SLEEPY;
        pose->mouth = COMP_PET_MOUTH_SOFT;
        pose->mouth_scale = 76u;
        pose->face_shift_y = clamp_face_shift((int16_t)pose->face_shift_y + 3);
        break;
    case COMP_PET_MOOD_WORRIED:
        pose->brow = COMP_PET_BROW_WORRIED;
        pose->brow_lift = clamp_percent((int16_t)pose->brow_lift + 5, 0u, 36u);
        pose->eye_open = clamp_percent((int16_t)pose->eye_open - 8, 18u, 100u);
        pose->mouth = COMP_PET_MOUTH_FROWN;
        pose->mouth_scale = 82u;
        break;
    case COMP_PET_MOOD_CALM:
    case COMP_PET_MOOD_COUNT:
    default:
        break;
    }
}

static void apply_living_phase(const comp_pet_behavior_t *behavior,
                               uint8_t phase,
                               comp_pet_expression_pose_t *pose)
{
    uint8_t beat;
    uint8_t warmth;

    if (pose == NULL) {
        return;
    }
    beat = (uint8_t)(phase % 3u);
    warmth = behavior == NULL ? 0u : (uint8_t)(behavior->affection / 24u);

    if (beat == 0u) {
        pose->face_shift_y = clamp_face_shift((int16_t)pose->face_shift_y + 1);
        pose->eye_width = clamp_percent((int16_t)pose->eye_width - 3,
                                        60u,
                                        140u);
        pose->mouth_scale = clamp_percent((int16_t)pose->mouth_scale - 4,
                                          60u,
                                          140u);
        pose->highlight_scale = clamp_percent((int16_t)pose->highlight_scale - 3,
                                              60u,
                                              140u);
    } else if (beat == 1u) {
        pose->face_shift_y = clamp_face_shift((int16_t)pose->face_shift_y - 2);
        pose->eye_open = clamp_percent((int16_t)pose->eye_open + 6,
                                       18u,
                                       100u);
        pose->eye_width = clamp_percent((int16_t)pose->eye_width + 5,
                                        60u,
                                        140u);
        pose->mouth_scale = clamp_percent((int16_t)pose->mouth_scale + 6 + warmth,
                                          60u,
                                          140u);
        pose->highlight_scale = clamp_percent((int16_t)pose->highlight_scale + 8,
                                              60u,
                                              140u);
        if (pose->brow == COMP_PET_BROW_WARM && pose->cheek_strength < 3u) {
            pose->cheek_strength++;
        }
    } else {
        pose->face_shift_y = clamp_face_shift((int16_t)pose->face_shift_y + 2);
        pose->eye_open = clamp_percent((int16_t)pose->eye_open - 5,
                                       18u,
                                       100u);
        pose->eye_spacing = clamp_eye_spacing((int16_t)pose->eye_spacing - 2);
        pose->mouth_scale = clamp_percent((int16_t)pose->mouth_scale - 2,
                                          60u,
                                          140u);
    }
}

void comp_pet_behavior_init(comp_pet_behavior_t *behavior, uint32_t personality_seed)
{
    uint32_t seed;

    if (behavior == NULL) {
        return;
    }
    seed = personality_seed == 0u ? 1u : personality_seed;
    memset(behavior, 0, sizeof(*behavior));
    behavior->sociability = trait_from_seed(seed, 0u, 43u, 30u);
    behavior->sensitivity = trait_from_seed(seed, 8u, 35u, 34u);
    behavior->playfulness = trait_from_seed(seed, 16u, 39u, 34u);
    behavior->arousal = (uint8_t)(34u + behavior->playfulness / 5u);
    behavior->curiosity = (uint8_t)(42u + seed % 29u);
    behavior->affection = (uint8_t)(46u + (seed >> 8u) % 25u);
    behavior->attachment = (uint8_t)(18u + (seed >> 24u) % 18u);
    behavior->engagement = COMP_PET_ENGAGEMENT_REST;
    behavior->last_stroke = COMP_PET_STROKE_NONE;
    behavior->personality_seed = seed;
    refresh_mood(behavior);
}

void comp_pet_behavior_advance(comp_pet_behavior_t *behavior, uint32_t elapsed_ms)
{
    uint32_t minutes;
    uint8_t settle;
    uint8_t baseline_arousal;
    uint8_t baseline_curiosity;
    int8_t baseline_valence;

    if (behavior == NULL || elapsed_ms == 0u) {
        return;
    }
    behavior->quiet_elapsed_ms = saturating_add_ms(behavior->quiet_elapsed_ms, elapsed_ms);
    minutes = elapsed_ms / 60000u;
    if (minutes == 0u) {
        refresh_mood(behavior);
        return;
    }
    settle = (uint8_t)(1u + minutes / 45u);
    if (settle > 12u) {
        settle = 12u;
    }
    baseline_valence = behavior->attachment >= 70u ? 8 : 0;
    baseline_arousal = (uint8_t)(30u + behavior->playfulness / 5u);
    baseline_curiosity = (uint8_t)(36u + behavior->playfulness / 2u);
    behavior->valence = approach_valence(behavior->valence, baseline_valence, (int8_t)settle);
    behavior->arousal = approach_percent(behavior->arousal, baseline_arousal, settle);
    behavior->curiosity = approach_percent(behavior->curiosity,
                                           baseline_curiosity,
                                           (uint8_t)(1u + settle / 2u));
    refresh_mood(behavior);
}

void comp_pet_behavior_apply_expression(comp_pet_behavior_t *behavior,
                                        comp_epaper_expression_t expression)
{
    if (behavior == NULL || !comp_epaper_expression_is_supported(expression)) {
        return;
    }
    switch (expression) {
    case COMP_EPAPER_EXPRESSION_IDLE:
        behavior->valence = approach_zero(behavior->valence, 4);
        behavior->arousal = clamp_percent((int16_t)behavior->arousal - 8, 18u, 100u);
        behavior->engagement = behavior->focus_valid
                                   ? COMP_PET_ENGAGEMENT_SETTLING
                                   : COMP_PET_ENGAGEMENT_REST;
        behavior->focus_valid = false;
        behavior->last_stroke = COMP_PET_STROKE_NONE;
        behavior->stroke_energy = 0u;
        break;
    case COMP_EPAPER_EXPRESSION_LISTENING:
    case COMP_EPAPER_EXPRESSION_RECORDING:
        behavior->arousal = clamp_percent((int16_t)behavior->arousal +
                                              16 + behavior->sensitivity / 5,
                                          18u,
                                          100u);
        behavior->curiosity = clamp_percent((int16_t)behavior->curiosity + 8,
                                            20u,
                                            100u);
        behavior->engagement = COMP_PET_ENGAGEMENT_NOTICE;
        break;
    case COMP_EPAPER_EXPRESSION_THINKING:
        behavior->arousal = clamp_percent((int16_t)behavior->arousal + 8, 18u, 100u);
        behavior->curiosity = clamp_percent((int16_t)behavior->curiosity + 5,
                                            20u,
                                            100u);
        behavior->engagement = COMP_PET_ENGAGEMENT_NOTICE;
        break;
    case COMP_EPAPER_EXPRESSION_SPEAKING:
        behavior->valence = clamp_valence((int16_t)behavior->valence + 5);
        behavior->arousal = clamp_percent((int16_t)behavior->arousal + 14, 18u, 100u);
        behavior->affection = clamp_percent((int16_t)behavior->affection + 1, 20u, 100u);
        behavior->engagement = COMP_PET_ENGAGEMENT_ENGAGED;
        break;
    case COMP_EPAPER_EXPRESSION_HAPPY:
    case COMP_EPAPER_EXPRESSION_SYNC_COMPLETE:
        behavior->valence = clamp_valence((int16_t)behavior->valence + 16);
        behavior->arousal = clamp_percent((int16_t)behavior->arousal + 10, 18u, 100u);
        behavior->affection = clamp_percent((int16_t)behavior->affection + 2, 20u, 100u);
        behavior->engagement = COMP_PET_ENGAGEMENT_ENGAGED;
        break;
    case COMP_EPAPER_EXPRESSION_SLEEPY:
        behavior->arousal = clamp_percent((int16_t)behavior->arousal - 24, 18u, 100u);
        behavior->engagement = COMP_PET_ENGAGEMENT_REST;
        break;
    case COMP_EPAPER_EXPRESSION_LOW_BATTERY:
        behavior->valence = clamp_valence((int16_t)behavior->valence -
                                          (6 + behavior->sensitivity / 10));
        behavior->arousal = clamp_percent((int16_t)behavior->arousal - 12, 18u, 100u);
        behavior->engagement = COMP_PET_ENGAGEMENT_REST;
        break;
    case COMP_EPAPER_EXPRESSION_ERROR:
        behavior->valence = clamp_valence((int16_t)behavior->valence -
                                          (16 + behavior->sensitivity / 5));
        behavior->arousal = clamp_percent((int16_t)behavior->arousal + 18, 18u, 100u);
        behavior->engagement = COMP_PET_ENGAGEMENT_NOTICE;
        break;
    case COMP_EPAPER_EXPRESSION_COUNT:
    default:
        return;
    }
    if (expression != COMP_EPAPER_EXPRESSION_IDLE &&
        expression != COMP_EPAPER_EXPRESSION_SLEEPY) {
        behavior->quiet_elapsed_ms = 0u;
    }
    behavior->interaction_count++;
    refresh_mood(behavior);
}

void comp_pet_behavior_note_touch(comp_pet_behavior_t *behavior,
                                  uint16_t x,
                                  uint16_t y,
                                  uint16_t width,
                                  uint16_t height)
{
    if (behavior == NULL || width == 0u || height == 0u) {
        return;
    }
    behavior->focus_x = x >= width ? (uint16_t)(width - 1u) : x;
    behavior->focus_y = y >= height ? (uint16_t)(height - 1u) : y;
    behavior->focus_valid = true;
    behavior->valence = clamp_valence((int16_t)behavior->valence +
                                      8 + behavior->sociability / 10);
    behavior->arousal = clamp_percent((int16_t)behavior->arousal +
                                          12 + behavior->playfulness / 8,
                                      18u,
                                      100u);
    behavior->curiosity = clamp_percent((int16_t)behavior->curiosity + 3, 20u, 100u);
    behavior->affection = clamp_percent((int16_t)behavior->affection + 2, 20u, 100u);
    behavior->attachment = clamp_percent((int16_t)behavior->attachment + 1, 0u, 100u);
    behavior->engagement = COMP_PET_ENGAGEMENT_ENGAGED;
    behavior->quiet_elapsed_ms = 0u;
    behavior->interaction_count++;
    refresh_mood(behavior);
}

comp_pet_stroke_direction_t comp_pet_behavior_stroke_direction(uint16_t start_x,
                                                                uint16_t start_y,
                                                                uint16_t end_x,
                                                                uint16_t end_y)
{
    uint16_t horizontal = absolute_delta(end_x, start_x);
    uint16_t vertical = absolute_delta(end_y, start_y);

    if (horizontal == 0u && vertical == 0u) {
        return COMP_PET_STROKE_NONE;
    }
    if (horizontal >= vertical) {
        return end_x < start_x ? COMP_PET_STROKE_LEFT :
                                 COMP_PET_STROKE_RIGHT;
    }
    return end_y < start_y ? COMP_PET_STROKE_UP : COMP_PET_STROKE_DOWN;
}

const char *comp_pet_behavior_stroke_name(comp_pet_stroke_direction_t direction)
{
    return direction <= COMP_PET_STROKE_DOWN ? k_stroke_names[direction] :
                                                k_stroke_names[COMP_PET_STROKE_NONE];
}

void comp_pet_behavior_note_stroke(comp_pet_behavior_t *behavior,
                                   uint16_t start_x,
                                   uint16_t start_y,
                                   uint16_t end_x,
                                   uint16_t end_y,
                                   uint16_t width,
                                   uint16_t height,
                                   uint32_t duration_ms)
{
    comp_pet_stroke_direction_t direction;
    uint16_t travel;
    uint8_t energy;
    bool gentle;

    if (behavior == NULL || width == 0u || height == 0u) {
        return;
    }
    direction = comp_pet_behavior_stroke_direction(start_x, start_y, end_x, end_y);
    if (direction == COMP_PET_STROKE_NONE) {
        comp_pet_behavior_note_touch(behavior, end_x, end_y, width, height);
        return;
    }
    travel = absolute_delta(end_x, start_x) + absolute_delta(end_y, start_y);
    energy = clamp_percent((int16_t)(38u + (uint32_t)travel * 62u /
                                                 (uint32_t)(width + height) +
                                         (duration_ms <= 360u ? 14u : 0u)),
                           32u,
                           100u);
    gentle = duration_ms >= 420u;
    behavior->focus_x = end_x >= width ? (uint16_t)(width - 1u) : end_x;
    behavior->focus_y = end_y >= height ? (uint16_t)(height - 1u) : end_y;
    behavior->focus_valid = true;
    behavior->last_stroke = direction;
    behavior->stroke_energy = energy;
    behavior->valence = clamp_valence((int16_t)behavior->valence +
                                      7 + behavior->sociability / 12 +
                                      (gentle ? 3 : 0));
    behavior->affection = clamp_percent((int16_t)behavior->affection +
                                        2 + (gentle ? 3 : 0),
                                        20u,
                                        100u);
    behavior->attachment = clamp_percent((int16_t)behavior->attachment +
                                         (gentle ? 2 : 1),
                                         0u,
                                         100u);
    switch (direction) {
    case COMP_PET_STROKE_LEFT:
    case COMP_PET_STROKE_RIGHT:
        behavior->arousal = clamp_percent((int16_t)behavior->arousal +
                                          7 + behavior->playfulness / 8,
                                          18u,
                                          100u);
        behavior->curiosity = clamp_percent((int16_t)behavior->curiosity + 8,
                                            20u,
                                            100u);
        break;
    case COMP_PET_STROKE_UP:
        behavior->arousal = clamp_percent((int16_t)behavior->arousal +
                                          14 + behavior->playfulness / 10,
                                          18u,
                                          100u);
        behavior->curiosity = clamp_percent((int16_t)behavior->curiosity + 14,
                                            20u,
                                            100u);
        break;
    case COMP_PET_STROKE_DOWN:
        behavior->arousal = clamp_percent((int16_t)behavior->arousal -
                                          (gentle ? 10 : 5),
                                          18u,
                                          100u);
        behavior->valence = clamp_valence((int16_t)behavior->valence + 5);
        behavior->affection = clamp_percent((int16_t)behavior->affection + 3,
                                            20u,
                                            100u);
        break;
    case COMP_PET_STROKE_NONE:
    default:
        break;
    }
    behavior->engagement = COMP_PET_ENGAGEMENT_ENGAGED;
    behavior->quiet_elapsed_ms = 0u;
    behavior->interaction_count++;
    refresh_mood(behavior);
}

comp_pet_mood_t comp_pet_behavior_mood(const comp_pet_behavior_t *behavior)
{
    if (behavior == NULL || behavior->mood >= COMP_PET_MOOD_COUNT) {
        return COMP_PET_MOOD_CALM;
    }
    return behavior->mood;
}

const char *comp_pet_behavior_mood_name(comp_pet_mood_t mood)
{
    return mood < COMP_PET_MOOD_COUNT ? k_mood_names[mood] : "calm";
}

bool comp_pet_behavior_export_memory(const comp_pet_behavior_t *behavior,
                                     comp_pet_behavior_memory_t *out_memory)
{
    if (behavior == NULL || out_memory == NULL) {
        return false;
    }
    *out_memory = (comp_pet_behavior_memory_t){
        .schema_version = COMP_PET_BEHAVIOR_MEMORY_SCHEMA_VERSION,
        .valence = behavior->valence,
        .arousal = behavior->arousal,
        .curiosity = behavior->curiosity,
        .affection = behavior->affection,
        .attachment = behavior->attachment,
        .interaction_count = behavior->interaction_count,
        .personality_seed = behavior->personality_seed,
    };
    return true;
}

bool comp_pet_behavior_import_memory(comp_pet_behavior_t *behavior,
                                     const comp_pet_behavior_memory_t *memory)
{
    if (behavior == NULL || memory == NULL ||
        memory->schema_version != COMP_PET_BEHAVIOR_MEMORY_SCHEMA_VERSION) {
        return false;
    }
    comp_pet_behavior_init(behavior, memory->personality_seed);
    behavior->valence = clamp_valence(memory->valence);
    behavior->arousal = clamp_percent(memory->arousal, 18u, 100u);
    behavior->curiosity = clamp_percent(memory->curiosity, 20u, 100u);
    behavior->affection = clamp_percent(memory->affection, 20u, 100u);
    behavior->attachment = clamp_percent(memory->attachment, 0u, 100u);
    behavior->interaction_count = memory->interaction_count;
    refresh_mood(behavior);
    return true;
}

void comp_pet_behavior_compose_expression_pose(
    const comp_pet_behavior_t *behavior,
    comp_epaper_expression_t expression,
    uint8_t phase,
    uint32_t variation_seed,
    comp_pet_expression_pose_t *out_pose)
{
    if (out_pose == NULL) {
        return;
    }
    comp_pet_expression_pose_from_expression(out_pose,
                                              expression,
                                              phase,
                                              variation_seed);
    apply_visual_character(behavior, phase, out_pose);
    apply_living_phase(behavior, phase, out_pose);
}

void comp_pet_behavior_compose_touch_pose(const comp_pet_behavior_t *behavior,
                                          uint16_t x,
                                          uint16_t y,
                                          uint16_t width,
                                          uint16_t height,
                                          uint8_t phase,
                                          uint32_t variation_seed,
                                          comp_pet_expression_pose_t *out_pose)
{
    if (out_pose == NULL) {
        return;
    }
    comp_pet_expression_pose_from_touch(out_pose,
                                         x,
                                         y,
                                         width,
                                         height,
                                         phase,
                                         variation_seed);
    apply_visual_character(behavior, phase, out_pose);
    if (behavior != NULL && behavior->affection >= 62u && phase != 1u) {
        out_pose->highlight_scale = clamp_percent((int16_t)out_pose->highlight_scale + 14,
                                                  60u,
                                                  140u);
    }
    /* A touch has a little semantic texture beyond its exact gaze target.
     * These are still one bounded pose rig, not stored reaction bitmaps. */
    if (height != 0u && (uint32_t)y * 3u < height) {
        out_pose->eye_open = clamp_percent((int16_t)out_pose->eye_open + 6,
                                           18u,
                                           100u);
        out_pose->face_shift_y = clamp_face_shift((int16_t)out_pose->face_shift_y - 3);
        out_pose->brow = COMP_PET_BROW_RAISED;
        out_pose->brow_lift = 16u;
        out_pose->eye_spacing = 106u;
        out_pose->mouth = COMP_PET_MOUTH_POUT;
        out_pose->mouth_scale = 82u;
        if (phase == 0u) {
            out_pose->mark = COMP_PET_MARK_SPARK;
        }
    } else if (height != 0u && (uint32_t)y * 3u >= (uint32_t)height * 2u) {
        out_pose->eye_open = clamp_percent((int16_t)out_pose->eye_open - 9,
                                           18u,
                                           100u);
        out_pose->eyelid_tilt = -6;
        out_pose->face_shift_y = clamp_face_shift((int16_t)out_pose->face_shift_y + 3);
        out_pose->brow = COMP_PET_BROW_WARM;
        out_pose->brow_lift = 4u;
        out_pose->eye_spacing = 92u;
        out_pose->mouth = COMP_PET_MOUTH_SOFT;
        out_pose->mouth_scale = 96u;
        out_pose->cheek_strength = 3u;
    } else if (width != 0u &&
               (uint32_t)x * 4u >= width &&
               (uint32_t)x * 4u < (uint32_t)width * 3u) {
        out_pose->eye_width = clamp_percent((int16_t)out_pose->eye_width + 8,
                                            60u,
                                            140u);
        out_pose->brow = COMP_PET_BROW_WARM;
        out_pose->brow_lift = 8u;
        out_pose->eye_spacing = 88u;
        out_pose->mouth = COMP_PET_MOUTH_SMILE;
        out_pose->mouth_scale = 128u;
        out_pose->cheek_strength = 3u;
    }
    /* E-paper cannot sell a fluid 30 fps loop honestly.  These three sparse
     * poses still carry the same living rhythm: notice the finger, brighten
     * into the answer, then soften back into contact. */
    if (phase == 0u) {
        out_pose->eye_open = clamp_percent((int16_t)out_pose->eye_open - 8,
                                           18u,
                                           100u);
        out_pose->eye_width = clamp_percent((int16_t)out_pose->eye_width - 5,
                                            60u,
                                            140u);
        out_pose->face_shift_y = clamp_face_shift((int16_t)out_pose->face_shift_y - 2);
    } else if (phase == 1u) {
        out_pose->eye_open = clamp_percent((int16_t)out_pose->eye_open + 14,
                                           18u,
                                           100u);
        out_pose->eye_width = clamp_percent((int16_t)out_pose->eye_width + 9,
                                            60u,
                                            140u);
        out_pose->eye_spacing = clamp_eye_spacing((int16_t)out_pose->eye_spacing + 7);
        out_pose->mouth = COMP_PET_MOUTH_SMILE;
        out_pose->mouth_scale = 122u;
        out_pose->cheek_strength = 3u;
        out_pose->mark = COMP_PET_MARK_SPARK;
    } else {
        out_pose->eye_open = clamp_percent((int16_t)out_pose->eye_open - 20,
                                           18u,
                                           100u);
        out_pose->eye_spacing = clamp_eye_spacing((int16_t)out_pose->eye_spacing - 5);
        out_pose->brow = COMP_PET_BROW_WARM;
        out_pose->brow_lift = 5u;
        out_pose->mouth = COMP_PET_MOUTH_SOFT;
        out_pose->mouth_scale = 104u;
        out_pose->cheek_strength = 3u;
    }
}

void comp_pet_behavior_compose_stroke_pose(const comp_pet_behavior_t *behavior,
                                           uint16_t end_x,
                                           uint16_t end_y,
                                           uint16_t width,
                                           uint16_t height,
                                           uint8_t phase,
                                           uint32_t variation_seed,
                                           comp_pet_expression_pose_t *out_pose)
{
    comp_pet_stroke_direction_t direction;
    uint8_t energy;

    if (out_pose == NULL) {
        return;
    }
    comp_pet_behavior_compose_touch_pose(behavior,
                                         end_x,
                                         end_y,
                                         width,
                                         height,
                                         phase,
                                         variation_seed,
                                         out_pose);
    direction = behavior == NULL ? COMP_PET_STROKE_NONE : behavior->last_stroke;
    energy = behavior == NULL ? 50u : behavior->stroke_energy;
    switch (direction) {
    case COMP_PET_STROKE_LEFT:
        out_pose->gaze_x = clamp_gaze((int16_t)out_pose->gaze_x - 10);
        out_pose->face_shift_x = clamp_face_shift((int16_t)out_pose->face_shift_x - 6);
        out_pose->eye_pair_tilt = -6;
        out_pose->brow = COMP_PET_BROW_RAISED;
        out_pose->brow_lift = 12u;
        out_pose->brow_asymmetry = -9;
        out_pose->eye_width = clamp_percent((int16_t)out_pose->eye_width + 8,
                                            60u,
                                            140u);
        out_pose->mouth = COMP_PET_MOUTH_POUT;
        out_pose->mouth_scale = 78u;
        break;
    case COMP_PET_STROKE_RIGHT:
        out_pose->gaze_x = clamp_gaze((int16_t)out_pose->gaze_x + 10);
        out_pose->face_shift_x = clamp_face_shift((int16_t)out_pose->face_shift_x + 6);
        out_pose->eye_pair_tilt = 6;
        out_pose->brow = COMP_PET_BROW_RAISED;
        out_pose->brow_lift = 12u;
        out_pose->brow_asymmetry = 9;
        out_pose->eye_width = clamp_percent((int16_t)out_pose->eye_width + 8,
                                            60u,
                                            140u);
        out_pose->mouth = COMP_PET_MOUTH_POUT;
        out_pose->mouth_scale = 78u;
        break;
    case COMP_PET_STROKE_UP:
        out_pose->gaze_y = clamp_gaze((int16_t)out_pose->gaze_y - 8);
        out_pose->face_shift_y = clamp_face_shift((int16_t)out_pose->face_shift_y - 6);
        out_pose->eye_open = clamp_percent((int16_t)out_pose->eye_open + 10,
                                           18u,
                                           100u);
        out_pose->eye_spacing = clamp_eye_spacing((int16_t)out_pose->eye_spacing + 7);
        out_pose->brow = COMP_PET_BROW_RAISED;
        out_pose->brow_lift = 20u;
        out_pose->mouth = COMP_PET_MOUTH_POUT;
        out_pose->mouth_scale = 86u;
        if (phase == 0u) {
            out_pose->mark = COMP_PET_MARK_SPARK;
        }
        break;
    case COMP_PET_STROKE_DOWN:
        out_pose->gaze_y = clamp_gaze((int16_t)out_pose->gaze_y + 5);
        out_pose->face_shift_y = clamp_face_shift((int16_t)out_pose->face_shift_y + 5);
        out_pose->eye_open = clamp_percent((int16_t)out_pose->eye_open - 14,
                                           18u,
                                           100u);
        out_pose->eye_spacing = clamp_eye_spacing((int16_t)out_pose->eye_spacing - 5);
        out_pose->brow = COMP_PET_BROW_WARM;
        out_pose->brow_lift = 6u;
        out_pose->mouth = COMP_PET_MOUTH_SMILE;
        out_pose->mouth_scale = 112u;
        out_pose->cheek_strength = 3u;
        break;
    case COMP_PET_STROKE_NONE:
    default:
        break;
    }
    if (direction == COMP_PET_STROKE_NONE) {
        return;
    }
    if (phase == 0u) {
        /* A tiny recoil makes the later directional response read as motion. */
        switch (direction) {
        case COMP_PET_STROKE_LEFT:
            out_pose->gaze_x = clamp_gaze((int16_t)out_pose->gaze_x + 20);
            out_pose->face_shift_x = clamp_face_shift((int16_t)out_pose->face_shift_x + 12);
            break;
        case COMP_PET_STROKE_RIGHT:
            out_pose->gaze_x = clamp_gaze((int16_t)out_pose->gaze_x - 20);
            out_pose->face_shift_x = clamp_face_shift((int16_t)out_pose->face_shift_x - 12);
            break;
        case COMP_PET_STROKE_UP:
            out_pose->gaze_y = clamp_gaze((int16_t)out_pose->gaze_y + 16);
            out_pose->face_shift_y = clamp_face_shift((int16_t)out_pose->face_shift_y + 12);
            break;
        case COMP_PET_STROKE_DOWN:
            out_pose->gaze_y = clamp_gaze((int16_t)out_pose->gaze_y - 10);
            out_pose->face_shift_y = clamp_face_shift((int16_t)out_pose->face_shift_y - 10);
            break;
        case COMP_PET_STROKE_NONE:
        default:
            break;
        }
        out_pose->eye_open = clamp_percent((int16_t)out_pose->eye_open - 10,
                                           18u,
                                           100u);
        out_pose->mouth = COMP_PET_MOUTH_SOFT;
        out_pose->mouth_scale = 92u;
        out_pose->cheek_strength = 1u;
    } else if (phase == 1u) {
        out_pose->eye_open = clamp_percent((int16_t)out_pose->eye_open +
                                           (int16_t)(6u + energy / 20u),
                                           18u,
                                           100u);
        out_pose->eye_width = clamp_percent((int16_t)out_pose->eye_width + 8,
                                            60u,
                                            140u);
        out_pose->mark = COMP_PET_MARK_SPARK;
        out_pose->cheek_strength = 3u;
    } else {
        out_pose->eye_open = clamp_percent((int16_t)out_pose->eye_open -
                                           (int16_t)(18u + energy / 20u),
                                           18u,
                                           100u);
        out_pose->brow = COMP_PET_BROW_WARM;
        out_pose->brow_lift = 4u;
        out_pose->mouth = COMP_PET_MOUTH_SMILE;
        out_pose->mouth_scale = 124u;
        out_pose->cheek_strength = 3u;
    }
}

bool comp_pet_behavior_self_test(void)
{
    comp_pet_behavior_t behavior;
    comp_pet_behavior_t restored;
    comp_pet_behavior_memory_t memory;
    comp_pet_expression_pose_t pose;
    comp_pet_expression_pose_t anticipation_pose;
    comp_pet_expression_pose_t peak_pose;
    comp_pet_expression_pose_t settle_pose;

    s_pet_behavior_self_test_failure_code = 0u;

    comp_pet_behavior_init(&behavior, 0x5Au);
    if (behavior.curiosity < 42u || behavior.affection < 46u ||
        behavior.sociability < 43u || behavior.sensitivity < 35u ||
        behavior.playfulness < 39u || behavior.engagement != COMP_PET_ENGAGEMENT_REST ||
        comp_pet_behavior_mood(&behavior) >= COMP_PET_MOOD_COUNT) {
        s_pet_behavior_self_test_failure_code = 1u;
        return false;
    }

    /* Keep every named long-lived mood executable, not merely documented. */
    behavior.valence = 0;
    behavior.arousal = 40u;
    behavior.curiosity = 40u;
    behavior.affection = 50u;
    behavior.attachment = 20u;
    behavior.quiet_elapsed_ms = 0u;
    refresh_mood(&behavior);
    if (comp_pet_behavior_mood(&behavior) != COMP_PET_MOOD_CALM) {
        s_pet_behavior_self_test_failure_code = 2u;
        return false;
    }
    comp_pet_behavior_compose_expression_pose(&behavior,
                                               COMP_EPAPER_EXPRESSION_IDLE,
                                               0u,
                                               3u,
                                               &pose);
    if (!comp_pet_expression_pose_is_valid(&pose)) {
        s_pet_behavior_self_test_failure_code = 3u;
        return false;
    }
    behavior.curiosity = 70u;
    behavior.arousal = 50u;
    refresh_mood(&behavior);
    comp_pet_behavior_compose_expression_pose(&behavior,
                                               COMP_EPAPER_EXPRESSION_IDLE,
                                               0u,
                                               3u,
                                               &pose);
    if (comp_pet_behavior_mood(&behavior) != COMP_PET_MOOD_CURIOUS ||
        pose.brow != COMP_PET_BROW_RAISED ||
        pose.mouth != COMP_PET_MOUTH_POUT || pose.eye_spacing < 96u) {
        s_pet_behavior_self_test_failure_code = 4u;
        return false;
    }
    behavior.curiosity = 40u;
    behavior.attachment = 70u;
    behavior.valence = 20;
    refresh_mood(&behavior);
    comp_pet_behavior_compose_expression_pose(&behavior,
                                               COMP_EPAPER_EXPRESSION_IDLE,
                                               0u,
                                               3u,
                                               &pose);
    if (comp_pet_behavior_mood(&behavior) != COMP_PET_MOOD_AFFECTIONATE ||
        pose.brow != COMP_PET_BROW_WARM ||
        pose.mouth != COMP_PET_MOUTH_SOFT || pose.cheek_strength != 1u) {
        s_pet_behavior_self_test_failure_code = 5u;
        return false;
    }
    behavior.valence = 60;
    behavior.affection = 80u;
    refresh_mood(&behavior);
    comp_pet_behavior_compose_expression_pose(&behavior,
                                               COMP_EPAPER_EXPRESSION_IDLE,
                                               0u,
                                               3u,
                                               &pose);
    if (comp_pet_behavior_mood(&behavior) != COMP_PET_MOOD_DELIGHTED ||
        pose.brow != COMP_PET_BROW_WARM ||
        pose.mouth != COMP_PET_MOUTH_SMILE || pose.cheek_strength != 3u) {
        s_pet_behavior_self_test_failure_code = 6u;
        return false;
    }
    behavior.valence = 0;
    behavior.arousal = 20u;
    behavior.quiet_elapsed_ms = 1800000u;
    refresh_mood(&behavior);
    comp_pet_behavior_compose_expression_pose(&behavior,
                                               COMP_EPAPER_EXPRESSION_IDLE,
                                               0u,
                                               3u,
                                               &pose);
    if (comp_pet_behavior_mood(&behavior) != COMP_PET_MOOD_RESTFUL ||
        pose.brow != COMP_PET_BROW_SLEEPY ||
        pose.mouth != COMP_PET_MOUTH_SOFT || pose.eye_open >= 70u) {
        s_pet_behavior_self_test_failure_code = 7u;
        return false;
    }
    behavior.valence = -40;
    behavior.quiet_elapsed_ms = 0u;
    refresh_mood(&behavior);
    comp_pet_behavior_compose_expression_pose(&behavior,
                                               COMP_EPAPER_EXPRESSION_IDLE,
                                               0u,
                                               3u,
                                               &pose);
    if (comp_pet_behavior_mood(&behavior) != COMP_PET_MOOD_WORRIED ||
        pose.brow != COMP_PET_BROW_WORRIED ||
        pose.mouth != COMP_PET_MOUTH_FROWN) {
        s_pet_behavior_self_test_failure_code = 8u;
        return false;
    }

    comp_pet_behavior_init(&behavior, 0x5Au);
    comp_pet_behavior_note_touch(&behavior, 199u, 0u, 200u, 200u);
    if (!behavior.focus_valid || behavior.focus_x != 199u || behavior.focus_y != 0u ||
        behavior.engagement != COMP_PET_ENGAGEMENT_ENGAGED || behavior.valence <= 0 ||
        behavior.attachment == 0u || behavior.quiet_elapsed_ms != 0u) {
        s_pet_behavior_self_test_failure_code = 9u;
        return false;
    }
    comp_pet_behavior_compose_touch_pose(&behavior, 199u, 0u, 200u, 200u, 0u, 3u, &pose);
    if (!comp_pet_expression_pose_is_valid(&pose) || pose.gaze_x <= 0 || pose.gaze_y >= 0 ||
        pose.eye_width < 100u || pose.mark != COMP_PET_MARK_SPARK ||
        pose.brow != COMP_PET_BROW_RAISED || pose.brow_lift != 16u ||
        pose.eye_spacing != 106u ||
        pose.mouth != COMP_PET_MOUTH_POUT || pose.face_shift_y >= 0) {
        s_pet_behavior_self_test_failure_code = 10u;
        return false;
    }
    comp_pet_behavior_init(&behavior, 0x5Au);
    comp_pet_behavior_note_stroke(&behavior,
                                  20u,
                                  100u,
                                  180u,
                                  100u,
                                  200u,
                                  200u,
                                  180u);
    comp_pet_behavior_compose_stroke_pose(&behavior,
                                           180u,
                                           100u,
                                           200u,
                                           200u,
                                           1u,
                                           5u,
                                           &pose);
    if (comp_pet_behavior_stroke_direction(20u, 100u, 180u, 100u) !=
            COMP_PET_STROKE_RIGHT ||
        comp_pet_behavior_stroke_direction(180u, 100u, 20u, 100u) !=
            COMP_PET_STROKE_LEFT ||
        comp_pet_behavior_stroke_direction(100u, 100u, 100u, 100u) !=
            COMP_PET_STROKE_NONE ||
        strcmp(comp_pet_behavior_stroke_name(COMP_PET_STROKE_RIGHT), "right") != 0 ||
        behavior.last_stroke != COMP_PET_STROKE_RIGHT || behavior.stroke_energy < 32u ||
        !comp_pet_expression_pose_is_valid(&pose) || pose.gaze_x <= 0 ||
        pose.face_shift_x <= 0 || pose.eye_pair_tilt <= 0 ||
        pose.brow != COMP_PET_BROW_RAISED || pose.mouth != COMP_PET_MOUTH_POUT) {
        s_pet_behavior_self_test_failure_code = 11u;
        return false;
    }
    comp_pet_behavior_init(&behavior, 0x5Au);
    comp_pet_behavior_note_stroke(&behavior,
                                  100u,
                                  180u,
                                  100u,
                                  20u,
                                  200u,
                                  200u,
                                  180u);
    comp_pet_behavior_compose_stroke_pose(&behavior,
                                           100u,
                                           20u,
                                           200u,
                                           200u,
                                           1u,
                                           6u,
                                           &pose);
    if (behavior.last_stroke != COMP_PET_STROKE_UP ||
        !comp_pet_expression_pose_is_valid(&pose) || pose.gaze_y >= 0 ||
        pose.face_shift_y >= 0 || pose.brow != COMP_PET_BROW_RAISED ||
        pose.mark != COMP_PET_MARK_SPARK) {
        s_pet_behavior_self_test_failure_code = 12u;
        return false;
    }
    comp_pet_behavior_init(&behavior, 0x5Au);
    comp_pet_behavior_note_stroke(&behavior,
                                  100u,
                                  20u,
                                  100u,
                                  180u,
                                  200u,
                                  200u,
                                  600u);
    comp_pet_behavior_compose_stroke_pose(&behavior,
                                           100u,
                                           180u,
                                           200u,
                                           200u,
                                           1u,
                                           7u,
                                           &pose);
    if (behavior.last_stroke != COMP_PET_STROKE_DOWN ||
        !comp_pet_expression_pose_is_valid(&pose) || pose.gaze_y <= 0 ||
        pose.face_shift_y <= 0 || pose.brow != COMP_PET_BROW_WARM ||
        pose.mouth != COMP_PET_MOUTH_SMILE || pose.cheek_strength != 3u) {
        s_pet_behavior_self_test_failure_code = 13u;
        return false;
    }
    comp_pet_behavior_compose_stroke_pose(&behavior,
                                           100u,
                                           180u,
                                           200u,
                                           200u,
                                           0u,
                                           8u,
                                           &anticipation_pose);
    comp_pet_behavior_compose_stroke_pose(&behavior,
                                           100u,
                                           180u,
                                           200u,
                                           200u,
                                           1u,
                                           8u,
                                           &peak_pose);
    comp_pet_behavior_compose_stroke_pose(&behavior,
                                           100u,
                                           180u,
                                           200u,
                                           200u,
                                           2u,
                                           8u,
                                           &settle_pose);
    if (!comp_pet_expression_pose_is_valid(&anticipation_pose) ||
        !comp_pet_expression_pose_is_valid(&peak_pose) ||
        !comp_pet_expression_pose_is_valid(&settle_pose) ||
        anticipation_pose.gaze_y >= peak_pose.gaze_y ||
        peak_pose.eye_open <= settle_pose.eye_open ||
        anticipation_pose.mouth != COMP_PET_MOUTH_SOFT ||
        peak_pose.mark != COMP_PET_MARK_SPARK ||
        settle_pose.mouth != COMP_PET_MOUTH_SMILE) {
        s_pet_behavior_self_test_failure_code = 14u;
        return false;
    }
    comp_pet_behavior_apply_expression(&behavior, COMP_EPAPER_EXPRESSION_IDLE);
    comp_pet_behavior_compose_expression_pose(&behavior,
                                               COMP_EPAPER_EXPRESSION_IDLE,
                                               0u,
                                               4u,
                                               &pose);
    if (!comp_pet_expression_pose_is_valid(&pose) ||
        behavior.engagement != COMP_PET_ENGAGEMENT_SETTLING ||
        behavior.last_stroke != COMP_PET_STROKE_NONE || behavior.stroke_energy != 0u) {
        s_pet_behavior_self_test_failure_code = 15u;
        return false;
    }
    comp_pet_behavior_advance(&behavior, 7200000u);
    if (behavior.quiet_elapsed_ms < 7200000u ||
        comp_pet_behavior_mood(&behavior) >= COMP_PET_MOOD_COUNT ||
        !comp_pet_behavior_export_memory(&behavior, &memory) ||
        !comp_pet_behavior_import_memory(&restored, &memory) ||
        restored.valence != behavior.valence || restored.arousal != behavior.arousal ||
        restored.curiosity != behavior.curiosity || restored.affection != behavior.affection ||
        restored.attachment != behavior.attachment ||
        restored.interaction_count != behavior.interaction_count ||
        restored.personality_seed != behavior.personality_seed) {
        s_pet_behavior_self_test_failure_code = 16u;
        return false;
    }
    comp_pet_behavior_apply_expression(&restored, COMP_EPAPER_EXPRESSION_ERROR);
    comp_pet_behavior_apply_expression(&restored, COMP_EPAPER_EXPRESSION_ERROR);
    return comp_pet_behavior_mood(&restored) == COMP_PET_MOOD_WORRIED &&
           strcmp(comp_pet_behavior_mood_name(COMP_PET_MOOD_AFFECTIONATE),
                  "affectionate") == 0;
}
