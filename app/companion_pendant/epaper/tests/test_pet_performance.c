#include "pet_performance.h"

#include <stdio.h>
#include <string.h>

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
    comp_pet_performance_t performance;
    comp_pet_performance_frame_t frame;

    if (require_true(comp_pet_performance_self_test(), "portable self-test")) {
        return 1;
    }
    comp_pet_performance_init(&performance);
    if (require_true(comp_pet_performance_begin(&performance,
                                                COMP_PET_PERFORMANCE_SCENE_MENU_ENTER,
                                                &frame),
                     "menu entry begins") ||
        require_true(frame.generation == 2u && frame.keyframe_index == 0u &&
                         strcmp(frame.resource_family, "menu.enter") == 0,
                     "menu entry has a generation-scoped entry resource") ||
        require_true(comp_pet_performance_advance(&performance,
                                                  COMP_PET_PERFORMANCE_PHASE_SUSTAINED,
                                                  &frame),
                     "menu entry advances only on an explicit event") ||
        require_true(frame.generation == 2u && frame.keyframe_index == 1u,
                     "advance retains generation and picks the sustained keyframe") ||
        require_true(!comp_pet_performance_advance(&performance,
                                                   COMP_PET_PERFORMANCE_PHASE_ENTRY,
                                                   &frame),
                     "performance cannot rewind itself") ||
        require_true(comp_pet_performance_begin(&performance,
                                                COMP_PET_PERFORMANCE_SCENE_RECORDING_START,
                                                &frame),
                     "recording preempts menu after its real commit") ||
        require_true(!comp_pet_performance_begin(&performance,
                                                 COMP_PET_PERFORMANCE_SCENE_DAILY_TAP,
                                                 &frame),
                     "lower-priority touch cannot preempt recording") ||
        require_true(comp_pet_performance_begin(&performance,
                                                COMP_PET_PERFORMANCE_SCENE_RECORDING_ACTIVE,
                                                &frame) &&
                         comp_pet_performance_begin(&performance,
                                                    COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVING,
                                                    &frame),
                     "recording journey permits active to saving transition") ||
        require_true(comp_pet_performance_recover_to_idle(&performance, &frame) &&
                         frame.scene == COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE &&
                         frame.phase == COMP_PET_PERFORMANCE_PHASE_SUSTAINED,
                     "recovery returns through the only universal idle path")) {
        return 1;
    }

    puts("PASS: pet performance scene contract");
    return 0;
}
