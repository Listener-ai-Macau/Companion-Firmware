#include "pet_performance.h"
#include "v9_candidate_resource_binding.h"

#include <stdio.h>
#include <string.h>

typedef struct {
    comp_v9_candidate_resource_status_t status;
    const char *clip_name;
} expected_scene_t;

#define EXPECTED_PENDING {COMP_V9_CANDIDATE_RESOURCE_PENDING_VISUAL_BASELINE, NULL}
#define EXPECTED_MENU_PENDING {COMP_V9_CANDIDATE_RESOURCE_PENDING_MENU_VISUAL_BASELINE, NULL}

static int require_true(bool condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

int main(void)
{
    static const expected_scene_t expected[COMP_PET_PERFORMANCE_SCENE_COUNT] = {
        [COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE] = {COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE, "idle"},
        [COMP_PET_PERFORMANCE_SCENE_DAILY_TAP] = {COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE, "touch"},
        [COMP_PET_PERFORMANCE_SCENE_DAILY_STROKE] = {COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE, "touch"},
        [COMP_PET_PERFORMANCE_SCENE_DAILY_SWIPE_LEFT] = {COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE, "swipe_left"},
        [COMP_PET_PERFORMANCE_SCENE_DAILY_SWIPE_RIGHT] = {COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE, "swipe_right"},
        [COMP_PET_PERFORMANCE_SCENE_DAILY_SWIPE_UP] = {COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE, "swipe_up"},
        [COMP_PET_PERFORMANCE_SCENE_DAILY_SWIPE_DOWN] = {COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE, "swipe_down"},
        [COMP_PET_PERFORMANCE_SCENE_VOICE_LISTENING] = {COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE, "listening"},
        [COMP_PET_PERFORMANCE_SCENE_VOICE_SPEAKING] = EXPECTED_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_MENU_HOLD] = {COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE, "menu_hold"},
        [COMP_PET_PERFORMANCE_SCENE_MENU_ENTER] = {COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE, "menu_hold"},
        [COMP_PET_PERFORMANCE_SCENE_MENU_OPEN] = EXPECTED_MENU_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_MENU_SELECT] = {COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE, "menu_hold"},
        [COMP_PET_PERFORMANCE_SCENE_MENU_BLOCKED] = EXPECTED_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_MENU_EXIT] = EXPECTED_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_RECORDING_START] = {COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE, "recording"},
        [COMP_PET_PERFORMANCE_SCENE_RECORDING_ACTIVE] = {COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE, "recording"},
        [COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVING] = {COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE, "saving"},
        [COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVED] = {COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE, "saved"},
        [COMP_PET_PERFORMANCE_SCENE_RECORDING_ERROR] = EXPECTED_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_SLEEP_ENTRY] = {COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE, "sleep"},
        [COMP_PET_PERFORMANCE_SCENE_DEEP_SLEEP] = {COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE, "sleep"},
        [COMP_PET_PERFORMANCE_SCENE_WAKE] = {COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE, "wake"},
        [COMP_PET_PERFORMANCE_SCENE_CHARGE_DETECTED] = EXPECTED_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_CHARGING] = EXPECTED_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_CHARGED] = EXPECTED_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_LOW_BATTERY] = EXPECTED_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_LINK_PAIRING] = EXPECTED_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_LINK_CONNECTED] = EXPECTED_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_LINK_SYNCING] = EXPECTED_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_LINK_SYNCED] = EXPECTED_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_LINK_ERROR] = EXPECTED_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_UPGRADE_OFFER] = EXPECTED_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_UPGRADE_PREPARE] = EXPECTED_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_UPGRADE_TRANSFER] = EXPECTED_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_UPGRADE_VERIFY] = EXPECTED_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_UPGRADE_RESTART] = EXPECTED_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_UPGRADE_SUCCESS] = EXPECTED_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_UPGRADE_ERROR] = EXPECTED_PENDING,
        [COMP_PET_PERFORMANCE_SCENE_SYSTEM_ERROR] = EXPECTED_PENDING,
    };
    comp_pet_performance_t performance;
    comp_pet_performance_frame_t frame;
    comp_v9_candidate_resource_binding_t binding;
    uint8_t available_count = 0u;
    uint8_t pending_count = 0u;

    if (require_true(comp_pet_performance_self_test(), "pet-performance self-test") ||
        require_true(comp_v9_candidate_resource_binding_self_test(), "v9 binding self-test") ||
        require_true(!comp_v9_candidate_resource_runtime_activation_allowed(),
                     "candidate must stay runtime-inactive") ||
        require_true(comp_v9_candidate_resource_pack_identity_matches(
                         "companion-v9-expression-candidate-200x200", 90u, 13u, 39u),
                     "v9 identity must match only the locked CEMP geometry") ||
        require_true(!comp_v9_candidate_resource_pack_identity_matches(
                         "emote-matrix-white-200x200-v1", 53u, 33u, 75u),
                     "legacy r53 CEMP must not match the v9 identity gate")) {
        return 1;
    }

    for (uint32_t scene = 0u; scene < COMP_PET_PERFORMANCE_SCENE_COUNT; ++scene) {
        comp_pet_performance_init(&performance);
        if (require_true(comp_pet_performance_begin(&performance,
                                                    (comp_pet_performance_scene_t)scene,
                                                    &frame),
                         "scene begins") ||
            require_true(comp_v9_candidate_resource_resolve(&frame, &binding),
                         "scene resolves") ||
            require_true(binding.status == expected[scene].status,
                         "scene has the expected v9 availability") ||
            require_true(binding.resource_family != NULL &&
                             !binding.runtime_activation_allowed &&
                             binding.candidate_pack_revision == 90u &&
                             strcmp(binding.candidate_pack_name,
                                    "companion-v9-expression-candidate-200x200") == 0,
                         "binding keeps pack identity but no activation")) {
            return 1;
        }
        if (expected[scene].clip_name != NULL) {
            if (require_true(binding.frame_available &&
                                 strcmp(binding.candidate_clip_name,
                                        expected[scene].clip_name) == 0,
                             "available scene resolves only to its declared v9 clip")) {
                return 1;
            }
            available_count++;
        } else {
            if (require_true(!binding.frame_available && binding.candidate_clip_name == NULL,
                             "pending scene has no legacy or procedural fallback")) {
                return 1;
            }
            pending_count++;
        }
    }
    if (require_true(available_count == 18u && pending_count == 22u,
                     "all 40 scenes are exhaustive")) {
        return 1;
    }

    comp_pet_performance_init(&performance);
    if (require_true(comp_pet_performance_begin(&performance,
                                                COMP_PET_PERFORMANCE_SCENE_RECORDING_ACTIVE,
                                                &frame) &&
                         comp_v9_candidate_resource_resolve(&frame, &binding) &&
                         binding.candidate_frame_index == 0u &&
                         comp_pet_performance_advance(&performance,
                                                      COMP_PET_PERFORMANCE_PHASE_SUSTAINED,
                                                      &frame) &&
                         comp_v9_candidate_resource_resolve(&frame, &binding) &&
                         binding.candidate_frame_index == 1u &&
                         comp_pet_performance_advance(&performance,
                                                      COMP_PET_PERFORMANCE_PHASE_SETTLE,
                                                      &frame) &&
                         comp_v9_candidate_resource_resolve(&frame, &binding) &&
                         binding.candidate_frame_index == 2u,
                     "motion phases map to v9 entry sustain settle frames") ||
        require_true(comp_pet_performance_recover_to_idle(&performance, &frame) &&
                         comp_v9_candidate_resource_resolve(&frame, &binding) &&
                         binding.candidate_frame_index == 1u,
                     "static idle maps to the v9 sustained frame")) {
        return 1;
    }
    return 0;
}
