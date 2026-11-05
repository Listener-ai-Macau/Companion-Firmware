#include "pet_performance.h"
#include "pet_performance_event_bridge.h"

#include <stdio.h>
#include <string.h>

static int fail(const char *message)
{
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

static int expect_event(comp_pet_performance_t *performance,
                        comp_pet_performance_event_t event,
                        comp_pet_performance_scene_t expected_scene,
                        const char *message)
{
    comp_pet_performance_frame_t frame;
    const uint32_t previous_generation = performance->generation;
    if (!comp_pet_performance_apply_event(performance, event, &frame) ||
        frame.scene != expected_scene || frame.generation != previous_generation + 1u) {
        return fail(message);
    }
    return 0;
}

static int expect_phase(comp_pet_performance_t *performance,
                        comp_pet_performance_phase_t phase,
                        const char *message)
{
    comp_pet_performance_frame_t frame;
    const uint32_t generation = performance->generation;
    if (!comp_pet_performance_advance(performance, phase, &frame) ||
        frame.phase != phase || frame.generation != generation) {
        return fail(message);
    }
    return 0;
}

static int run_upgrade_replay(comp_pet_performance_t *performance)
{
    comp_pet_performance_frame_t frame;
    if (!comp_pet_performance_event_is_replay_only(
            COMP_PET_PERFORMANCE_EVENT_UPGRADE_OFFER) ||
        !comp_pet_performance_event_is_replay_only(
            COMP_PET_PERFORMANCE_EVENT_UPGRADE_SUCCESS) ||
        comp_pet_performance_event_is_replay_only(
            COMP_PET_PERFORMANCE_EVENT_RECORDING_START) ||
        strcmp(comp_pet_performance_event_name(COMP_PET_PERFORMANCE_EVENT_UPGRADE_TRANSFER),
               "upgrade_transfer") != 0 ||
        strcmp(comp_pet_performance_event_name(COMP_PET_PERFORMANCE_EVENT_RECOVER_TO_IDLE),
               "recover_to_idle") != 0) {
        return fail("upgrade replay event identity");
    }
    if (expect_event(performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_OFFER,
                     COMP_PET_PERFORMANCE_SCENE_UPGRADE_OFFER, "upgrade offer") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_PREPARE,
                     COMP_PET_PERFORMANCE_SCENE_UPGRADE_PREPARE, "upgrade prepare") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_TRANSFER,
                     COMP_PET_PERFORMANCE_SCENE_UPGRADE_TRANSFER, "upgrade transfer") ||
        expect_phase(performance, COMP_PET_PERFORMANCE_PHASE_SUSTAINED,
                     "upgrade transfer sustained") ||
        comp_pet_performance_apply_event(
            performance, COMP_PET_PERFORMANCE_EVENT_MENU_ENTER, &frame) ||
        comp_pet_performance_apply_event(
            performance, COMP_PET_PERFORMANCE_EVENT_RECORDING_START, &frame) ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_VERIFY,
                     COMP_PET_PERFORMANCE_SCENE_UPGRADE_VERIFY, "upgrade verify") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_RESTART,
                     COMP_PET_PERFORMANCE_SCENE_UPGRADE_RESTART, "upgrade restart") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_SUCCESS,
                     COMP_PET_PERFORMANCE_SCENE_UPGRADE_SUCCESS, "upgrade success") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_DISMISS,
                     COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE, "upgrade success dismiss")) {
        return 1;
    }
    if (expect_event(performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_OFFER,
                     COMP_PET_PERFORMANCE_SCENE_UPGRADE_OFFER, "upgrade error offer") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_TRANSFER,
                     COMP_PET_PERFORMANCE_SCENE_UPGRADE_TRANSFER, "upgrade error transfer") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_ERROR,
                     COMP_PET_PERFORMANCE_SCENE_UPGRADE_ERROR, "upgrade error") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_DISMISS,
                     COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE, "upgrade error dismiss")) {
        return 1;
    }
    return 0;
}

static int run_recording_replay(comp_pet_performance_t *performance)
{
    comp_pet_performance_frame_t frame;
    if (expect_event(performance, COMP_PET_PERFORMANCE_EVENT_RECORDING_START,
                     COMP_PET_PERFORMANCE_SCENE_RECORDING_START, "recording start") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_RECORDING_ACTIVE,
                     COMP_PET_PERFORMANCE_SCENE_RECORDING_ACTIVE, "recording active") ||
        expect_phase(performance, COMP_PET_PERFORMANCE_PHASE_SUSTAINED,
                     "recording active sustained") ||
        comp_pet_performance_apply_event(
            performance, COMP_PET_PERFORMANCE_EVENT_MENU_HOLD, &frame) ||
        comp_pet_performance_apply_event(
            performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_OFFER, &frame) ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_RECORDING_SAVING,
                     COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVING, "recording saving") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_RECORDING_SAVED,
                     COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVED, "recording saved") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_RECORDING_RECOVER,
                     COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE, "recording saved recover") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_RECORDING_START,
                     COMP_PET_PERFORMANCE_SCENE_RECORDING_START, "recording error start") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_RECORDING_ERROR,
                     COMP_PET_PERFORMANCE_SCENE_RECORDING_ERROR, "recording error") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_RECORDING_RECOVER,
                     COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE, "recording error recover")) {
        return 1;
    }
    return 0;
}

static int run_menu_replay(comp_pet_performance_t *performance)
{
    if (expect_event(performance, COMP_PET_PERFORMANCE_EVENT_MENU_HOLD,
                     COMP_PET_PERFORMANCE_SCENE_MENU_HOLD, "menu hold") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_MENU_ENTER,
                     COMP_PET_PERFORMANCE_SCENE_MENU_ENTER, "menu enter") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_MENU_OPEN,
                     COMP_PET_PERFORMANCE_SCENE_MENU_OPEN, "menu open") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_MENU_SELECT,
                     COMP_PET_PERFORMANCE_SCENE_MENU_SELECT, "menu select") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_MENU_EXIT,
                     COMP_PET_PERFORMANCE_SCENE_MENU_EXIT, "menu exit") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_RECOVER_TO_IDLE,
                     COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE, "menu exit recover") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_MENU_HOLD,
                     COMP_PET_PERFORMANCE_SCENE_MENU_HOLD, "menu blocked hold") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_MENU_ENTER,
                     COMP_PET_PERFORMANCE_SCENE_MENU_ENTER, "menu blocked enter") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_MENU_OPEN,
                     COMP_PET_PERFORMANCE_SCENE_MENU_OPEN, "menu blocked open") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_MENU_BLOCKED,
                     COMP_PET_PERFORMANCE_SCENE_MENU_BLOCKED, "menu blocked") ||
        expect_event(performance, COMP_PET_PERFORMANCE_EVENT_RECOVER_TO_IDLE,
                     COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE, "menu blocked recover")) {
        return 1;
    }
    return 0;
}

int main(void)
{
    comp_pet_performance_t performance;

    if (!comp_pet_performance_self_test() ||
        !comp_pet_performance_event_bridge_self_test()) {
        return fail("portable scene self-test");
    }
    comp_pet_performance_init(&performance);
    if (run_upgrade_replay(&performance) || run_recording_replay(&performance) ||
        run_menu_replay(&performance)) {
        return 1;
    }

    puts("PASS: total scene portable replay contract");
    return 0;
}
