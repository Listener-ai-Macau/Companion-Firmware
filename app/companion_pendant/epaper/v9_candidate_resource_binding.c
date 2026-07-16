#include "v9_candidate_resource_binding.h"

#include <stddef.h>
#include <string.h>

#define COMP_V9_CANDIDATE_PACK_NAME "companion-v9-expression-candidate-200x200"
#define COMP_V9_CANDIDATE_PACK_REVISION 90u
#define COMP_V9_CANDIDATE_FRAME_ENTRY 0u
#define COMP_V9_CANDIDATE_FRAME_SUSTAINED 1u
#define COMP_V9_CANDIDATE_FRAME_SETTLE 2u

typedef struct {
    comp_v9_candidate_resource_status_t status;
    const char *clip_name;
} comp_v9_candidate_scene_definition_t;

#define V9_AVAILABLE(clip) {COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE, clip}
#define V9_PENDING {COMP_V9_CANDIDATE_RESOURCE_PENDING_VISUAL_BASELINE, NULL}
#define V9_MENU_PENDING {COMP_V9_CANDIDATE_RESOURCE_PENDING_MENU_VISUAL_BASELINE, NULL}

static const comp_v9_candidate_scene_definition_t
    k_v9_candidate_scene_definitions[COMP_PET_PERFORMANCE_SCENE_COUNT] = {
        [COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE] = V9_AVAILABLE("idle"),
        [COMP_PET_PERFORMANCE_SCENE_DAILY_TAP] = V9_AVAILABLE("touch"),
        [COMP_PET_PERFORMANCE_SCENE_DAILY_STROKE] = V9_AVAILABLE("touch"),
        [COMP_PET_PERFORMANCE_SCENE_DAILY_SWIPE_LEFT] = V9_AVAILABLE("swipe_left"),
        [COMP_PET_PERFORMANCE_SCENE_DAILY_SWIPE_RIGHT] = V9_AVAILABLE("swipe_right"),
        [COMP_PET_PERFORMANCE_SCENE_DAILY_SWIPE_UP] = V9_AVAILABLE("swipe_up"),
        [COMP_PET_PERFORMANCE_SCENE_DAILY_SWIPE_DOWN] = V9_AVAILABLE("swipe_down"),
        [COMP_PET_PERFORMANCE_SCENE_VOICE_LISTENING] = V9_AVAILABLE("listening"),
        [COMP_PET_PERFORMANCE_SCENE_VOICE_SPEAKING] = V9_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_MENU_HOLD] = V9_AVAILABLE("menu_hold"),
        [COMP_PET_PERFORMANCE_SCENE_MENU_ENTER] = V9_AVAILABLE("menu_hold"),
        [COMP_PET_PERFORMANCE_SCENE_MENU_OPEN] = V9_MENU_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_MENU_SELECT] = V9_AVAILABLE("menu_hold"),
        [COMP_PET_PERFORMANCE_SCENE_MENU_BLOCKED] = V9_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_MENU_EXIT] = V9_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_RECORDING_START] = V9_AVAILABLE("recording"),
        [COMP_PET_PERFORMANCE_SCENE_RECORDING_ACTIVE] = V9_AVAILABLE("recording"),
        [COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVING] = V9_AVAILABLE("saving"),
        [COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVED] = V9_AVAILABLE("saved"),
        [COMP_PET_PERFORMANCE_SCENE_RECORDING_ERROR] = V9_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_SLEEP_ENTRY] = V9_AVAILABLE("sleep"),
        [COMP_PET_PERFORMANCE_SCENE_DEEP_SLEEP] = V9_AVAILABLE("sleep"),
        [COMP_PET_PERFORMANCE_SCENE_WAKE] = V9_AVAILABLE("wake"),
        [COMP_PET_PERFORMANCE_SCENE_CHARGE_DETECTED] = V9_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_CHARGING] = V9_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_CHARGED] = V9_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_LOW_BATTERY] = V9_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_LINK_PAIRING] = V9_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_LINK_CONNECTED] = V9_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_LINK_SYNCING] = V9_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_LINK_SYNCED] = V9_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_LINK_ERROR] = V9_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_UPGRADE_OFFER] = V9_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_UPGRADE_PREPARE] = V9_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_UPGRADE_TRANSFER] = V9_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_UPGRADE_VERIFY] = V9_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_UPGRADE_RESTART] = V9_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_UPGRADE_SUCCESS] = V9_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_UPGRADE_ERROR] = V9_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_SYSTEM_ERROR] = V9_PENDING,
    };

static uint8_t candidate_frame_index(comp_pet_performance_phase_t phase)
{
    switch (phase) {
    case COMP_PET_PERFORMANCE_PHASE_ENTRY:
        return COMP_V9_CANDIDATE_FRAME_ENTRY;
    case COMP_PET_PERFORMANCE_PHASE_SUSTAINED:
        return COMP_V9_CANDIDATE_FRAME_SUSTAINED;
    case COMP_PET_PERFORMANCE_PHASE_SETTLE:
    case COMP_PET_PERFORMANCE_PHASE_EXIT:
        return COMP_V9_CANDIDATE_FRAME_SETTLE;
    case COMP_PET_PERFORMANCE_PHASE_COUNT:
    default:
        return 0u;
    }
}

const char *comp_v9_candidate_resource_status_name(
    comp_v9_candidate_resource_status_t status)
{
    switch (status) {
    case COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE:
        return "candidate_available_not_active";
    case COMP_V9_CANDIDATE_RESOURCE_PENDING_VISUAL_BASELINE:
        return "pending_visual_baseline";
    case COMP_V9_CANDIDATE_RESOURCE_PENDING_MENU_VISUAL_BASELINE:
        return "pending_menu_visual_baseline";
    case COMP_V9_CANDIDATE_RESOURCE_INVALID:
    default:
        return "invalid";
    }
}

bool comp_v9_candidate_resource_resolve(
    const comp_pet_performance_frame_t *performance_frame,
    comp_v9_candidate_resource_binding_t *out_binding)
{
    const comp_v9_candidate_scene_definition_t *definition;

    if (performance_frame == NULL || out_binding == NULL ||
        (uint32_t)performance_frame->scene >=
            (uint32_t)COMP_PET_PERFORMANCE_SCENE_COUNT ||
        (uint32_t)performance_frame->phase >=
            (uint32_t)COMP_PET_PERFORMANCE_PHASE_COUNT ||
        !comp_pet_performance_phase_is_supported(performance_frame->scene,
                                                 performance_frame->phase)) {
        return false;
    }

    definition = &k_v9_candidate_scene_definitions[performance_frame->scene];
    *out_binding = (comp_v9_candidate_resource_binding_t){
        .status = definition->status,
        .resource_family = comp_pet_performance_scene_name(performance_frame->scene),
        .candidate_pack_name = COMP_V9_CANDIDATE_PACK_NAME,
        .candidate_pack_revision = COMP_V9_CANDIDATE_PACK_REVISION,
        .candidate_clip_name = definition->clip_name,
        .candidate_frame_index = candidate_frame_index(performance_frame->phase),
        .frame_available =
            definition->status == COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE,
        .runtime_activation_allowed = false,
    };
    if (!out_binding->frame_available) {
        out_binding->candidate_clip_name = NULL;
        out_binding->candidate_frame_index = 0u;
    }
    return true;
}

bool comp_v9_candidate_resource_runtime_activation_allowed(void)
{
    return false;
}

bool comp_v9_candidate_resource_binding_self_test(void)
{
    comp_pet_performance_t performance;
    comp_pet_performance_frame_t frame;
    comp_v9_candidate_resource_binding_t binding;
    uint8_t available_count = 0u;
    uint8_t pending_count = 0u;

    if (comp_v9_candidate_resource_runtime_activation_allowed()) {
        return false;
    }
    for (uint32_t scene = 0u; scene < COMP_PET_PERFORMANCE_SCENE_COUNT; ++scene) {
        comp_pet_performance_init(&performance);
        if (!comp_pet_performance_begin(&performance,
                                        (comp_pet_performance_scene_t)scene,
                                        &frame) ||
            !comp_v9_candidate_resource_resolve(&frame, &binding) ||
            binding.resource_family == NULL || binding.runtime_activation_allowed ||
            binding.candidate_pack_revision != COMP_V9_CANDIDATE_PACK_REVISION ||
            strcmp(binding.candidate_pack_name, COMP_V9_CANDIDATE_PACK_NAME) != 0) {
            return false;
        }
        if (binding.status == COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE) {
            if (!binding.frame_available || binding.candidate_clip_name == NULL) {
                return false;
            }
            available_count++;
        } else if (binding.status == COMP_V9_CANDIDATE_RESOURCE_PENDING_VISUAL_BASELINE ||
                   binding.status == COMP_V9_CANDIDATE_RESOURCE_PENDING_MENU_VISUAL_BASELINE) {
            if (binding.frame_available || binding.candidate_clip_name != NULL) {
                return false;
            }
            pending_count++;
        } else {
            return false;
        }
    }
    return available_count == 18u && pending_count == 22u;
}
