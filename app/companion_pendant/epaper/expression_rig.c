#include "expression_rig.h"

#include <string.h>

static bool state_is_valid(const comp_expression_rig_state_t *state)
{
    return state != NULL && state->scene < COMP_EXPRESSION_RIG_SCENE_COUNT &&
           state->emotion < COMP_EXPRESSION_RIG_EMOTION_COUNT &&
           state->attention < COMP_EXPRESSION_RIG_ATTENTION_COUNT &&
           state->energy < COMP_EXPRESSION_RIG_ENERGY_COUNT &&
           state->interaction_memory <= 2u && state->phase < COMP_EXPRESSION_RIG_PHASE_COUNT;
}

static bool profile_is_valid(const comp_expression_rig_profile_t *profile)
{
    return profile != NULL && profile->components != NULL && profile->component_count > 0u &&
           profile->component_count <= 255u;
}

static const comp_expression_rig_component_info_t *find_component(
    const comp_expression_rig_profile_t *profile,
    comp_expression_rig_role_t role,
    comp_expression_rig_variant_t variant)
{
    const comp_expression_rig_component_info_t *result = NULL;
    size_t index;

    for (index = 0u; index < profile->component_count; ++index) {
        const comp_expression_rig_component_info_t *candidate = &profile->components[index];

        if (candidate->role != role || candidate->variant != variant) {
            continue;
        }
        if (result != NULL) {
            return NULL;
        }
        result = candidate;
    }
    return result;
}

static const comp_expression_rig_component_info_t *find_component_id(
    const comp_expression_rig_profile_t *profile,
    uint16_t component_id)
{
    size_t index;

    for (index = 0u; index < profile->component_count; ++index) {
        if (profile->components[index].component_id == component_id) {
            return &profile->components[index];
        }
    }
    return NULL;
}

static const comp_expression_rig_registered_pose_t *find_registered_pose(
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_state_t *state)
{
    size_t index;

    if (profile == NULL || state == NULL || profile->registered_poses == NULL ||
        profile->registered_pose_count == 0u) {
        return NULL;
    }
    for (index = 0u; index < profile->registered_pose_count; ++index) {
        const comp_expression_rig_registered_pose_t *candidate = &profile->registered_poses[index];

        if (candidate->scene == state->scene && candidate->emotion == state->emotion &&
            candidate->attention == state->attention) {
            return candidate;
        }
    }
    return NULL;
}

static void attention_offset(comp_expression_rig_attention_t attention,
                             int8_t *out_x,
                             int8_t *out_y)
{
    *out_x = 0;
    *out_y = 0;
    switch (attention) {
    case COMP_EXPRESSION_RIG_ATTENTION_LEFT:
        *out_x = -3;
        break;
    case COMP_EXPRESSION_RIG_ATTENTION_RIGHT:
        *out_x = 3;
        break;
    case COMP_EXPRESSION_RIG_ATTENTION_UP:
        *out_y = -2;
        break;
    case COMP_EXPRESSION_RIG_ATTENTION_DOWN:
        *out_y = 2;
        break;
    case COMP_EXPRESSION_RIG_ATTENTION_CENTER:
    default:
        break;
    }
}

static void emotion_offsets(comp_expression_rig_emotion_t emotion,
                            int8_t *out_brow_y,
                            int8_t *out_mouth_y,
                            int8_t *out_cheek_y,
                            int8_t *out_charm_y)
{
    *out_brow_y = 0;
    *out_mouth_y = 0;
    *out_cheek_y = 0;
    *out_charm_y = 0;
    switch (emotion) {
    case COMP_EXPRESSION_RIG_EMOTION_CURIOUS:
        *out_brow_y = -2;
        *out_mouth_y = 1;
        *out_cheek_y = -1;
        *out_charm_y = -2;
        break;
    case COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE:
        *out_brow_y = -2;
        *out_mouth_y = -1;
        *out_cheek_y = -1;
        *out_charm_y = -2;
        break;
    case COMP_EXPRESSION_RIG_EMOTION_FOCUSED:
        *out_mouth_y = -1;
        *out_cheek_y = 1;
        *out_charm_y = -2;
        break;
    case COMP_EXPRESSION_RIG_EMOTION_SLEEPY:
        *out_brow_y = 1;
        break;
    case COMP_EXPRESSION_RIG_EMOTION_CALM:
    default:
        break;
    }
}

static int8_t energy_offset(comp_expression_rig_energy_t energy)
{
    switch (energy) {
    case COMP_EXPRESSION_RIG_ENERGY_LOW:
        return 1;
    case COMP_EXPRESSION_RIG_ENERGY_HIGH:
        return -1;
    case COMP_EXPRESSION_RIG_ENERGY_NORMAL:
    default:
        return 0;
    }
}

static bool append_layer(comp_expression_rig_plan_t *plan,
                         const comp_expression_rig_component_info_t *component,
                         int8_t offset_x,
                         int8_t offset_y)
{
    comp_expression_rig_layer_t *layer;

    if (plan == NULL || component == NULL || plan->layer_count >= COMP_EXPRESSION_RIG_MAX_LAYERS ||
        component->min_offset_x > component->max_offset_x ||
        component->min_offset_y > component->max_offset_y ||
        component->composite_op >= COMP_EXPRESSION_RIG_COMPOSITE_COUNT) {
        return false;
    }
    if (offset_x < component->min_offset_x) {
        offset_x = component->min_offset_x;
    } else if (offset_x > component->max_offset_x) {
        offset_x = component->max_offset_x;
    }
    if (offset_y < component->min_offset_y) {
        offset_y = component->min_offset_y;
    } else if (offset_y > component->max_offset_y) {
        offset_y = component->max_offset_y;
    }
    layer = &plan->layers[plan->layer_count++];
    *layer = (comp_expression_rig_layer_t){
        .component_id = component->component_id,
        .base_x = component->base_x,
        .base_y = component->base_y,
        .offset_x = offset_x,
        .offset_y = offset_y,
        .composite_op = component->composite_op,
    };
    return true;
}

static bool build_registered_pose_plan(const comp_expression_rig_profile_t *profile,
                                       const comp_expression_rig_state_t *input,
                                       const comp_expression_rig_state_t *effective,
                                       const comp_expression_rig_registered_pose_t *pose,
                                       comp_expression_rig_plan_t *out_plan)
{
    size_t index;

    if (pose == NULL || pose->layer_count == 0u || pose->layer_count > COMP_EXPRESSION_RIG_MAX_LAYERS) {
        return false;
    }
    memset(out_plan, 0, sizeof(*out_plan));
    out_plan->input_state = *input;
    out_plan->effective_state = *effective;
    for (index = 0u; index < pose->layer_count; ++index) {
        const comp_expression_rig_registered_pose_layer_t *layer = &pose->layers[index];
        const comp_expression_rig_component_info_t *component = find_component_id(profile, layer->component_id);
        int8_t offset_x = layer->offset_x;
        int8_t offset_y = layer->offset_y;

        if (component == NULL) {
            return false;
        }
        if ((layer->dynamic_flags & COMP_EXPRESSION_RIG_POSE_DYNAMIC_ENERGY_Y) != 0u) {
            offset_y = (int8_t)(offset_y + energy_offset(effective->energy));
        }
        if ((layer->dynamic_flags & COMP_EXPRESSION_RIG_POSE_DYNAMIC_MEMORY_X) != 0u) {
            offset_x = (int8_t)(offset_x + effective->interaction_memory);
        }
        if (!append_layer(out_plan, component, offset_x, offset_y)) {
            return false;
        }
    }
    return true;
}

static bool build_registered_plan(const comp_expression_rig_profile_t *profile,
                                  const comp_expression_rig_state_t *input,
                                  const comp_expression_rig_state_t *effective,
                                  comp_expression_rig_plan_t *out_plan)
{
    return build_registered_pose_plan(profile, input, effective,
                                      find_registered_pose(profile, effective), out_plan);
}

bool comp_expression_rig_build_registered_pose_plan(
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_state_t *state,
    const comp_expression_rig_registered_pose_t *pose,
    comp_expression_rig_plan_t *out_plan)
{
    if (!profile_is_valid(profile) || !state_is_valid(state) || pose == NULL || out_plan == NULL) {
        return false;
    }
    return build_registered_pose_plan(profile, state, state, pose, out_plan);
}

bool comp_expression_rig_story_state(const comp_expression_rig_state_t *story_state,
                                     comp_expression_rig_phase_t phase,
                                     comp_expression_rig_state_t *out_state)
{
    if (!state_is_valid(story_state) || out_state == NULL || phase >= COMP_EXPRESSION_RIG_PHASE_COUNT) {
        return false;
    }
    if (phase == COMP_EXPRESSION_RIG_PHASE_SUSTAIN) {
        *out_state = *story_state;
        out_state->phase = phase;
    } else {
        *out_state = (comp_expression_rig_state_t){
            .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
            .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
            .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
            .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL,
            .interaction_memory = 0u,
            .phase = phase,
        };
    }
    return true;
}

bool comp_expression_rig_next_daily_state(uint32_t *in_out_seed,
                                          uint8_t interaction_memory,
                                          comp_expression_rig_state_t *out_state)
{
    if (in_out_seed == NULL || out_state == NULL || interaction_memory > 2u) {
        return false;
    }
    *out_state = (comp_expression_rig_state_t){
        .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
        .emotion = interaction_memory == 2u ? COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE :
                   interaction_memory == 1u ? COMP_EXPRESSION_RIG_EMOTION_CURIOUS :
                                             COMP_EXPRESSION_RIG_EMOTION_CALM,
        .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
        .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL,
        .interaction_memory = interaction_memory,
        .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN,
    };
    return true;
}

bool comp_expression_rig_build_plan(const comp_expression_rig_profile_t *profile,
                                    const comp_expression_rig_state_t *state,
                                    comp_expression_rig_plan_t *out_plan)
{
    comp_expression_rig_state_t effective;
    comp_expression_rig_variant_t eye_variant;
    comp_expression_rig_variant_t brow_variant;
    const comp_expression_rig_component_info_t *components[12];
    const comp_expression_rig_component_info_t *detail_component = NULL;
    uint16_t charm_id;
    int8_t attention_x;
    int8_t attention_y;
    int8_t brow_y;
    int8_t mouth_y;
    int8_t cheek_y;
    int8_t charm_y;
    int8_t energy_y;
    int8_t eye_body_x;
    int8_t eye_body_y;
    int8_t left_highlight_x;
    int8_t right_highlight_x;
    int8_t highlight_y;
    int8_t sparkle_x;
    int8_t sparkle_y;
    bool ok;
    size_t index;

    if (!profile_is_valid(profile) || !state_is_valid(state) || out_plan == NULL ||
        !comp_expression_rig_story_state(state, state->phase, &effective)) {
        return false;
    }
    if (profile->registered_poses != NULL && profile->registered_pose_count > 0u) {
        return build_registered_plan(profile, state, &effective, out_plan);
    }
    eye_variant = effective.emotion == COMP_EXPRESSION_RIG_EMOTION_SLEEPY ?
                  COMP_EXPRESSION_RIG_VARIANT_SLEEPY : COMP_EXPRESSION_RIG_VARIANT_OPEN;
    brow_variant = eye_variant;
    charm_id = profile->scene_charm_component[effective.scene];
    components[0] = find_component(profile, COMP_EXPRESSION_RIG_ROLE_LEFT_BROW, brow_variant);
    components[1] = find_component(profile, COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW, brow_variant);
    components[2] = find_component(profile, COMP_EXPRESSION_RIG_ROLE_LEFT_EYE, eye_variant);
    components[3] = find_component(profile, COMP_EXPRESSION_RIG_ROLE_RIGHT_EYE, eye_variant);
    components[4] = eye_variant == COMP_EXPRESSION_RIG_VARIANT_OPEN ?
                    find_component(profile, COMP_EXPRESSION_RIG_ROLE_LEFT_HIGHLIGHT, eye_variant) : NULL;
    components[5] = eye_variant == COMP_EXPRESSION_RIG_VARIANT_OPEN ?
                    find_component(profile, COMP_EXPRESSION_RIG_ROLE_RIGHT_HIGHLIGHT, eye_variant) : NULL;
    components[6] = eye_variant == COMP_EXPRESSION_RIG_VARIANT_OPEN ?
                    find_component(profile, COMP_EXPRESSION_RIG_ROLE_LEFT_SPARKLE, eye_variant) : NULL;
    components[7] = eye_variant == COMP_EXPRESSION_RIG_VARIANT_OPEN ?
                    find_component(profile, COMP_EXPRESSION_RIG_ROLE_RIGHT_SPARKLE, eye_variant) : NULL;
    components[8] = find_component(profile, COMP_EXPRESSION_RIG_ROLE_LEFT_CHEEK, COMP_EXPRESSION_RIG_VARIANT_DEFAULT);
    components[9] = find_component(profile, COMP_EXPRESSION_RIG_ROLE_RIGHT_CHEEK, COMP_EXPRESSION_RIG_VARIANT_DEFAULT);
    components[10] = find_component(profile, COMP_EXPRESSION_RIG_ROLE_NOSE, COMP_EXPRESSION_RIG_VARIANT_DEFAULT);
    components[11] = find_component(profile, COMP_EXPRESSION_RIG_ROLE_MOUTH, COMP_EXPRESSION_RIG_VARIANT_DEFAULT);
    for (index = 0u; index < 12u; ++index) {
        if (index >= 4u && index <= 7u && eye_variant != COMP_EXPRESSION_RIG_VARIANT_OPEN) {
            continue;
        }
        if (components[index] == NULL) {
            return false;
        }
    }
    if (effective.scene == COMP_EXPRESSION_RIG_SCENE_SWIPE &&
        effective.attention == COMP_EXPRESSION_RIG_ATTENTION_LEFT) {
        detail_component = find_component(profile, COMP_EXPRESSION_RIG_ROLE_LEFT_DETAIL,
                                          COMP_EXPRESSION_RIG_VARIANT_SWIPE);
        if (detail_component == NULL) {
            return false;
        }
    } else if (effective.scene == COMP_EXPRESSION_RIG_SCENE_SWIPE &&
               effective.attention == COMP_EXPRESSION_RIG_ATTENTION_RIGHT) {
        detail_component = find_component(profile, COMP_EXPRESSION_RIG_ROLE_RIGHT_DETAIL,
                                          COMP_EXPRESSION_RIG_VARIANT_SWIPE);
        if (detail_component == NULL) {
            return false;
        }
    }
    attention_offset(effective.attention, &attention_x, &attention_y);
    emotion_offsets(effective.emotion, &brow_y, &mouth_y, &cheek_y, &charm_y);
    energy_y = energy_offset(effective.energy);
    eye_body_x = effective.scene == COMP_EXPRESSION_RIG_SCENE_DAILY ? 0 : attention_x;
    eye_body_y = effective.scene == COMP_EXPRESSION_RIG_SCENE_DAILY ? 0 : attention_y;
    left_highlight_x = attention_x;
    right_highlight_x = attention_x;
    highlight_y = attention_y;
    sparkle_x = attention_x;
    sparkle_y = attention_y;
    if (effective.scene == COMP_EXPRESSION_RIG_SCENE_DAILY) {
        switch (effective.attention) {
        case COMP_EXPRESSION_RIG_ATTENTION_LEFT:
            left_highlight_x = -1;
            right_highlight_x = -1;
            highlight_y = 2;
            sparkle_x = -1;
            sparkle_y = 2;
            break;
        case COMP_EXPRESSION_RIG_ATTENTION_RIGHT:
            left_highlight_x = 1;
            right_highlight_x = 1;
            highlight_y = 2;
            sparkle_x = 1;
            sparkle_y = 2;
            break;
        case COMP_EXPRESSION_RIG_ATTENTION_UP:
            left_highlight_x = 0;
            right_highlight_x = 0;
            highlight_y = 1;
            sparkle_x = 0;
            sparkle_y = 1;
            break;
        case COMP_EXPRESSION_RIG_ATTENTION_DOWN:
            left_highlight_x = 0;
            right_highlight_x = 0;
            highlight_y = 2;
            sparkle_x = 0;
            sparkle_y = 2;
            break;
        case COMP_EXPRESSION_RIG_ATTENTION_CENTER:
        default:
            left_highlight_x = 0;
            right_highlight_x = 0;
            highlight_y = 0;
            sparkle_x = 0;
            sparkle_y = 0;
            break;
        }
    }

    memset(out_plan, 0, sizeof(*out_plan));
    out_plan->input_state = *state;
    out_plan->effective_state = effective;
    ok = append_layer(out_plan, components[0], (int8_t)(attention_x / 2),
                      (int8_t)(attention_y / 2 + brow_y + energy_y)) &&
         append_layer(out_plan, components[1], (int8_t)(attention_x / 2),
                      (int8_t)(attention_y / 2 + brow_y + energy_y)) &&
         append_layer(out_plan, components[2], eye_body_x, eye_body_y) &&
         append_layer(out_plan, components[3], eye_body_x, eye_body_y);
    if (ok && eye_variant == COMP_EXPRESSION_RIG_VARIANT_OPEN) {
        ok = append_layer(out_plan, components[4], left_highlight_x, highlight_y) &&
             append_layer(out_plan, components[5], right_highlight_x, highlight_y) &&
             append_layer(out_plan, components[6], sparkle_x, sparkle_y) &&
             append_layer(out_plan, components[7], sparkle_x, sparkle_y);
    }
    ok = ok && append_layer(out_plan, components[8], 0, cheek_y) &&
         append_layer(out_plan, components[9], 0, cheek_y) &&
         append_layer(out_plan, components[10], 0, 0) &&
         append_layer(out_plan, components[11], 0, mouth_y);
    if (ok && detail_component != NULL) {
        const int8_t detail_x = effective.attention == COMP_EXPRESSION_RIG_ATTENTION_LEFT ? -1 : 1;

        ok = append_layer(out_plan, detail_component, detail_x, energy_y);
    }
    return ok && append_layer(out_plan, find_component_id(profile, charm_id), effective.interaction_memory,
                              (int8_t)(charm_y + energy_y));
}

static bool canvas_is_valid(const comp_expression_rig_canvas_t *canvas, size_t *out_size)
{
    size_t required;
    uint16_t minimum_stride;

    if (canvas == NULL || out_size == NULL || canvas->width == 0u || canvas->height == 0u) {
        return false;
    }
    minimum_stride = (uint16_t)((canvas->width + 7u) / 8u);
    if (canvas->stride_bytes < minimum_stride) {
        return false;
    }
    required = (size_t)canvas->stride_bytes * canvas->height;
    if (required / canvas->height != canvas->stride_bytes) {
        return false;
    }
    *out_size = required;
    return true;
}

static bool is_black(const uint8_t *data, uint16_t stride, uint16_t x, uint16_t y)
{
    return (data[(size_t)y * stride + x / 8u] & (uint8_t)(0x80u >> (x & 7u))) == 0u;
}

static void set_black(uint8_t *data, uint16_t stride, uint16_t x, uint16_t y)
{
    data[(size_t)y * stride + x / 8u] &= (uint8_t)~(uint8_t)(0x80u >> (x & 7u));
}

static void set_white(uint8_t *data, uint16_t stride, uint16_t x, uint16_t y)
{
    data[(size_t)y * stride + x / 8u] |= (uint8_t)(0x80u >> (x & 7u));
}

bool comp_expression_rig_compose_1bpp(const comp_expression_rig_canvas_t *canvas,
                                      const comp_expression_rig_plan_t *plan,
                                      comp_expression_rig_component_read_fn read_component,
                                      void *read_context,
                                      uint8_t *component_scratch,
                                      size_t component_scratch_size,
                                      uint8_t *destination,
                                      size_t destination_size,
                                      comp_expression_rig_bounds_t *out_bounds)
{
    size_t required_size;
    bool has_ink = false;
    uint16_t left = 0u;
    uint16_t top = 0u;
    uint16_t right = 0u;
    uint16_t bottom = 0u;
    uint8_t layer_index;

    if (!canvas_is_valid(canvas, &required_size) || plan == NULL || read_component == NULL ||
        component_scratch == NULL || destination == NULL || out_bounds == NULL ||
        destination_size < required_size || plan->layer_count == 0u ||
        plan->layer_count > COMP_EXPRESSION_RIG_MAX_LAYERS) {
        return false;
    }
    memset(destination, 0xFF, required_size);
    for (layer_index = 0u; layer_index < plan->layer_count; ++layer_index) {
        const comp_expression_rig_layer_t *layer = &plan->layers[layer_index];
        comp_expression_rig_component_mask_info_t info;
        int32_t origin_x = (int32_t)layer->base_x + layer->offset_x;
        int32_t origin_y = (int32_t)layer->base_y + layer->offset_y;
        uint16_t y;

        memset(&info, 0, sizeof(info));
        if (!read_component(read_context, layer->component_id, component_scratch,
                            component_scratch_size, &info) || info.width == 0u || info.height == 0u ||
            info.stride_bytes < (uint16_t)((info.width + 7u) / 8u) ||
            info.data_size > component_scratch_size ||
            info.data_size < (size_t)info.stride_bytes * info.height || origin_x < 0 || origin_y < 0 ||
            origin_x + info.width > canvas->width || origin_y + info.height > canvas->height ||
            layer->composite_op >= COMP_EXPRESSION_RIG_COMPOSITE_COUNT) {
            return false;
        }
        for (y = 0u; y < info.height; ++y) {
            uint16_t x;
            for (x = 0u; x < info.width; ++x) {
                uint16_t destination_x;
                uint16_t destination_y;

                if (!is_black(component_scratch, info.stride_bytes, x, y)) {
                    continue;
                }
                destination_x = (uint16_t)(origin_x + x);
                destination_y = (uint16_t)(origin_y + y);
                if (layer->composite_op == COMP_EXPRESSION_RIG_COMPOSITE_ERASE) {
                    set_white(destination, canvas->stride_bytes, destination_x, destination_y);
                } else {
                    set_black(destination, canvas->stride_bytes, destination_x, destination_y);
                }
            }
        }
    }
    for (uint16_t y = 0u; y < canvas->height; ++y) {
        for (uint16_t x = 0u; x < canvas->width; ++x) {
            if (!is_black(destination, canvas->stride_bytes, x, y)) {
                continue;
            }
            if (!has_ink) {
                left = right = x;
                top = bottom = y;
                has_ink = true;
            } else {
                if (x < left) {
                    left = x;
                }
                if (x > right) {
                    right = x;
                }
                if (y < top) {
                    top = y;
                }
                if (y > bottom) {
                    bottom = y;
                }
            }
        }
    }
    if (!has_ink) {
        return false;
    }
    *out_bounds = (comp_expression_rig_bounds_t){
        .has_ink = true,
        .left = left,
        .top = top,
        .width = (uint16_t)(right - left + 1u),
        .height = (uint16_t)(bottom - top + 1u),
    };
    return true;
}
