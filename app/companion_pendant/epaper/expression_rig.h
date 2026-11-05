#ifndef COMPANION_EPAPER_EXPRESSION_RIG_H
#define COMPANION_EPAPER_EXPRESSION_RIG_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_EXPRESSION_RIG_MAX_LAYERS 16u
#define COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID 0xFFFFu

typedef enum {
    COMP_EXPRESSION_RIG_ROLE_LEFT_BROW = 0u,
    COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW,
    COMP_EXPRESSION_RIG_ROLE_LEFT_EYE,
    COMP_EXPRESSION_RIG_ROLE_RIGHT_EYE,
    COMP_EXPRESSION_RIG_ROLE_LEFT_HIGHLIGHT,
    COMP_EXPRESSION_RIG_ROLE_RIGHT_HIGHLIGHT,
    COMP_EXPRESSION_RIG_ROLE_LEFT_SPARKLE,
    COMP_EXPRESSION_RIG_ROLE_RIGHT_SPARKLE,
    COMP_EXPRESSION_RIG_ROLE_LEFT_CHEEK,
    COMP_EXPRESSION_RIG_ROLE_RIGHT_CHEEK,
    COMP_EXPRESSION_RIG_ROLE_NOSE,
    COMP_EXPRESSION_RIG_ROLE_MOUTH,
    COMP_EXPRESSION_RIG_ROLE_LEFT_DETAIL,
    COMP_EXPRESSION_RIG_ROLE_RIGHT_DETAIL,
    COMP_EXPRESSION_RIG_ROLE_CHARM,
    COMP_EXPRESSION_RIG_ROLE_CHEEK_PAIR,
    COMP_EXPRESSION_RIG_ROLE_LISTENING_DETAIL,
} comp_expression_rig_role_t;

typedef enum {
    COMP_EXPRESSION_RIG_VARIANT_DEFAULT = 0u,
    COMP_EXPRESSION_RIG_VARIANT_OPEN,
    COMP_EXPRESSION_RIG_VARIANT_SLEEPY,
    COMP_EXPRESSION_RIG_VARIANT_SWIPE,
} comp_expression_rig_variant_t;

typedef enum {
    COMP_EXPRESSION_RIG_COMPOSITE_INK = 0u,
    COMP_EXPRESSION_RIG_COMPOSITE_ERASE,
    COMP_EXPRESSION_RIG_COMPOSITE_COUNT,
} comp_expression_rig_composite_op_t;

typedef enum {
    COMP_EXPRESSION_RIG_SCENE_DAILY = 0u,
    COMP_EXPRESSION_RIG_SCENE_TOUCH,
    COMP_EXPRESSION_RIG_SCENE_SWIPE,
    COMP_EXPRESSION_RIG_SCENE_RECORDING,
    COMP_EXPRESSION_RIG_SCENE_MENU,
    COMP_EXPRESSION_RIG_SCENE_SLEEP,
    COMP_EXPRESSION_RIG_SCENE_CHARGING,
    COMP_EXPRESSION_RIG_SCENE_ERROR,
    COMP_EXPRESSION_RIG_SCENE_COUNT,
} comp_expression_rig_scene_t;

typedef enum {
    COMP_EXPRESSION_RIG_EMOTION_CALM = 0u,
    COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
    COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE,
    COMP_EXPRESSION_RIG_EMOTION_FOCUSED,
    COMP_EXPRESSION_RIG_EMOTION_SLEEPY,
    COMP_EXPRESSION_RIG_EMOTION_ALERT,
    COMP_EXPRESSION_RIG_EMOTION_JOYFUL,
    COMP_EXPRESSION_RIG_EMOTION_PLAYFUL,
    COMP_EXPRESSION_RIG_EMOTION_ANTICIPATORY,
    COMP_EXPRESSION_RIG_EMOTION_PUZZLED,
    COMP_EXPRESSION_RIG_EMOTION_LISTENING,
    COMP_EXPRESSION_RIG_EMOTION_THINKING,
    COMP_EXPRESSION_RIG_EMOTION_COUNT,
} comp_expression_rig_emotion_t;

typedef enum {
    COMP_EXPRESSION_RIG_ATTENTION_CENTER = 0u,
    COMP_EXPRESSION_RIG_ATTENTION_LEFT,
    COMP_EXPRESSION_RIG_ATTENTION_RIGHT,
    COMP_EXPRESSION_RIG_ATTENTION_UP,
    COMP_EXPRESSION_RIG_ATTENTION_DOWN,
    COMP_EXPRESSION_RIG_ATTENTION_COUNT,
} comp_expression_rig_attention_t;

typedef enum {
    COMP_EXPRESSION_RIG_ENERGY_LOW = 0u,
    COMP_EXPRESSION_RIG_ENERGY_NORMAL,
    COMP_EXPRESSION_RIG_ENERGY_HIGH,
    COMP_EXPRESSION_RIG_ENERGY_COUNT,
} comp_expression_rig_energy_t;

typedef enum {
    COMP_EXPRESSION_RIG_PHASE_ENTRY = 0u,
    COMP_EXPRESSION_RIG_PHASE_SUSTAIN,
    COMP_EXPRESSION_RIG_PHASE_SETTLE,
    COMP_EXPRESSION_RIG_PHASE_COUNT,
} comp_expression_rig_phase_t;

typedef struct {
    uint16_t component_id;
    comp_expression_rig_role_t role;
    comp_expression_rig_variant_t variant;
    int16_t base_x;
    int16_t base_y;
    int8_t min_offset_x;
    int8_t min_offset_y;
    int8_t max_offset_x;
    int8_t max_offset_y;
    uint8_t z_index;
    comp_expression_rig_composite_op_t composite_op;
} comp_expression_rig_component_info_t;

enum {
    /* Registered poses may opt into small legal context offsets.  These flags
     * move only registered source components; they never create face pixels. */
    COMP_EXPRESSION_RIG_POSE_DYNAMIC_ENERGY_Y = 1u << 0,
    COMP_EXPRESSION_RIG_POSE_DYNAMIC_MEMORY_X = 1u << 1,
};

typedef struct {
    uint16_t component_id;
    int8_t offset_x;
    int8_t offset_y;
    uint8_t dynamic_flags;
} comp_expression_rig_registered_pose_layer_t;

typedef struct {
    comp_expression_rig_scene_t scene;
    comp_expression_rig_emotion_t emotion;
    comp_expression_rig_attention_t attention;
    uint8_t layer_count;
    comp_expression_rig_registered_pose_layer_t layers[COMP_EXPRESSION_RIG_MAX_LAYERS];
} comp_expression_rig_registered_pose_t;

typedef struct {
    const comp_expression_rig_component_info_t *components;
    size_t component_count;
    uint16_t scene_charm_component[COMP_EXPRESSION_RIG_SCENE_COUNT];
    const comp_expression_rig_registered_pose_t *registered_poses;
    size_t registered_pose_count;
} comp_expression_rig_profile_t;

typedef struct {
    comp_expression_rig_scene_t scene;
    comp_expression_rig_emotion_t emotion;
    comp_expression_rig_attention_t attention;
    comp_expression_rig_energy_t energy;
    uint8_t interaction_memory;
    comp_expression_rig_phase_t phase;
} comp_expression_rig_state_t;

typedef struct {
    uint16_t component_id;
    int16_t base_x;
    int16_t base_y;
    int8_t offset_x;
    int8_t offset_y;
    comp_expression_rig_composite_op_t composite_op;
} comp_expression_rig_layer_t;

typedef struct {
    comp_expression_rig_state_t input_state;
    comp_expression_rig_state_t effective_state;
    comp_expression_rig_layer_t layers[COMP_EXPRESSION_RIG_MAX_LAYERS];
    uint8_t layer_count;
} comp_expression_rig_plan_t;

typedef struct {
    uint16_t width;
    uint16_t height;
    uint16_t stride_bytes;
} comp_expression_rig_canvas_t;

typedef struct {
    uint16_t width;
    uint16_t height;
    uint16_t stride_bytes;
    size_t data_size;
} comp_expression_rig_component_mask_info_t;

typedef struct {
    bool has_ink;
    uint16_t left;
    uint16_t top;
    uint16_t width;
    uint16_t height;
} comp_expression_rig_bounds_t;

typedef bool (*comp_expression_rig_component_read_fn)(
    void *context,
    uint16_t component_id,
    uint8_t *destination,
    size_t destination_size,
    comp_expression_rig_component_mask_info_t *out_info);

/* Build an ordered plan from a product state. This performs no drawing and
 * contains only source-derived component ids plus their legal offsets. */
bool comp_expression_rig_build_plan(
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_state_t *state,
    comp_expression_rig_plan_t *out_plan);

/* Build one generated registered pose for a concrete state. This validates
 * every component id and legal offset against the profile; it never accepts
 * geometry or pixels from the caller. Performance scores use this to switch
 * between their registered core and accent component sets. */
bool comp_expression_rig_build_registered_pose_plan(
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_state_t *state,
    const comp_expression_rig_registered_pose_t *pose,
    comp_expression_rig_plan_t *out_plan);

/* Convert one stateful story to its entry/sustain/settle presentation state.
 * Entry and settle deliberately return to daily calm; sustain retains event
 * context. */
bool comp_expression_rig_story_state(
    const comp_expression_rig_state_t *story_state,
    comp_expression_rig_phase_t phase,
    comp_expression_rig_state_t *out_state);

/* Legacy compatibility helper for a baseline-only daily state. The seed is
 * intentionally not consumed: behavior selection belongs to the deterministic
 * choreographer, not a pseudo-random daily picker. */
bool comp_expression_rig_next_daily_state(
    uint32_t *in_out_seed,
    uint8_t interaction_memory,
    comp_expression_rig_state_t *out_state);

/* Compose only black pixels from source masks delivered by the target asset
 * reader. The core never draws facial geometry and never owns asset storage. */
bool comp_expression_rig_compose_1bpp(
    const comp_expression_rig_canvas_t *canvas,
    const comp_expression_rig_plan_t *plan,
    comp_expression_rig_component_read_fn read_component,
    void *read_context,
    uint8_t *component_scratch,
    size_t component_scratch_size,
    uint8_t *destination,
    size_t destination_size,
    comp_expression_rig_bounds_t *out_bounds);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_EXPRESSION_RIG_H */
