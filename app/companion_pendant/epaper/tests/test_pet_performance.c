#include "pet_performance.h"
#include "pet_performance_event_bridge.h"

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

    if (require_true(comp_pet_performance_self_test(), "portable self-test") ||
        require_true(comp_pet_performance_event_bridge_self_test(), "event bridge self-test")) {
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
                     "recovery returns through the only universal idle path") ||
        require_true(comp_pet_performance_apply_expression_signal(
                         &performance, COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START, &frame) &&
                         frame.scene == COMP_PET_PERFORMANCE_SCENE_RECORDING_START,
                     "recording signal selects a portable recording scene") ||
        require_true(comp_pet_performance_apply_expression_signal(
                         &performance, COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_STOP, &frame) &&
                         frame.scene == COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVING,
                     "recording stop selects saving without target code") ||
        require_true(comp_pet_performance_apply_expression_signal(
                         &performance, COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_FINISHED, &frame) &&
                         frame.scene == COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVED,
                     "recording finished selects saved scene") ||
        require_true(comp_pet_performance_apply_expression_signal(
                         &performance, COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY, &frame),
                     "recovery signal returns to idle") ||
        require_true(comp_pet_performance_apply_event(
                         &performance, COMP_PET_PERFORMANCE_EVENT_DAILY_SWIPE_RIGHT, &frame) &&
                         strcmp(frame.resource_family, "daily.swipe_right") == 0,
                     "direct stroke event keeps its direction") ||
        require_true(!comp_pet_performance_apply_expression_signal(
                          &performance, COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_RESULT, &frame),
                     "generic speaker result cannot erase precise touch semantics") ||
        require_true(comp_pet_performance_apply_event(
                         &performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_OFFER, &frame) &&
                         frame.scene == COMP_PET_PERFORMANCE_SCENE_UPGRADE_OFFER &&
                         comp_pet_performance_event_is_replay_only(
                             COMP_PET_PERFORMANCE_EVENT_UPGRADE_OFFER),
                     "upgrade offer remains explicit replay-only scene metadata") ||
        require_true(comp_pet_performance_apply_event(
                         &performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_PREPARE, &frame) &&
                         comp_pet_performance_apply_event(
                             &performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_TRANSFER, &frame) &&
                         !comp_pet_performance_apply_event(
                             &performance, COMP_PET_PERFORMANCE_EVENT_MENU_HOLD, &frame) &&
                         !comp_pet_performance_apply_event(
                             &performance, COMP_PET_PERFORMANCE_EVENT_RECORDING_START, &frame),
                     "upgrade transfer protects its committed visual journey") ||
        require_true(comp_pet_performance_apply_event(
                         &performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_ERROR, &frame) &&
                         frame.scene == COMP_PET_PERFORMANCE_SCENE_UPGRADE_ERROR &&
                         comp_pet_performance_apply_event(
                             &performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_DISMISS, &frame) &&
                         frame.scene == COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE &&
                         !comp_pet_performance_event_is_replay_only(
                             COMP_PET_PERFORMANCE_EVENT_RECORDING_START),
                     "upgrade error recovers without turning recording into replay") ||
        require_true(comp_pet_performance_apply_event(
                         &performance, COMP_PET_PERFORMANCE_EVENT_RECORDING_START, &frame) &&
                         frame.scene == COMP_PET_PERFORMANCE_SCENE_RECORDING_START &&
                         comp_pet_performance_apply_event(
                             &performance, COMP_PET_PERFORMANCE_EVENT_RECORDING_ACTIVE, &frame) &&
                         comp_pet_performance_apply_event(
                             &performance, COMP_PET_PERFORMANCE_EVENT_RECORDING_SAVING, &frame) &&
                         comp_pet_performance_apply_event(
                             &performance, COMP_PET_PERFORMANCE_EVENT_RECORDING_SAVED, &frame) &&
                         frame.scene == COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVED &&
                         comp_pet_performance_apply_event(
                             &performance, COMP_PET_PERFORMANCE_EVENT_RECORDING_ERROR, &frame) &&
                         frame.scene == COMP_PET_PERFORMANCE_SCENE_RECORDING_ERROR &&
                         comp_pet_performance_apply_event(
                             &performance, COMP_PET_PERFORMANCE_EVENT_RECORDING_RECOVER, &frame) &&
                         frame.scene == COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE,
                     "recording event path remains a portable observation and recovery contract")) {
        return 1;
    }

    puts("PASS: pet performance scene contract");
    return 0;
}
