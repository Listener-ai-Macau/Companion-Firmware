#include "pet_performance_event_bridge.h"

#include <stddef.h>
#include <string.h>

static const char *const k_event_names[COMP_PET_PERFORMANCE_EVENT_COUNT] = {
    "daily_tap",
    "daily_stroke",
    "daily_swipe_left",
    "daily_swipe_right",
    "daily_swipe_up",
    "daily_swipe_down",
    "menu_hold",
    "menu_enter",
    "menu_open",
    "menu_select",
    "menu_blocked",
    "menu_exit",
    "sleep_entry",
    "deep_sleep",
    "wake",
    "recording_start",
    "recording_active",
    "recording_saving",
    "recording_saved",
    "recording_error",
    "recording_recover",
    "upgrade_offer",
    "upgrade_prepare",
    "upgrade_transfer",
    "upgrade_verify",
    "upgrade_restart",
    "upgrade_success",
    "upgrade_error",
    "upgrade_dismiss",
    "recover_to_idle",
};

static bool event_scene(comp_pet_performance_event_t event,
                        comp_pet_performance_scene_t *out_scene)
{
    if (out_scene == NULL) {
        return false;
    }
    switch (event) {
    case COMP_PET_PERFORMANCE_EVENT_DAILY_TAP:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_DAILY_TAP;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_DAILY_STROKE:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_DAILY_STROKE;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_DAILY_SWIPE_LEFT:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_DAILY_SWIPE_LEFT;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_DAILY_SWIPE_RIGHT:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_DAILY_SWIPE_RIGHT;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_DAILY_SWIPE_UP:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_DAILY_SWIPE_UP;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_DAILY_SWIPE_DOWN:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_DAILY_SWIPE_DOWN;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_MENU_HOLD:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_MENU_HOLD;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_MENU_ENTER:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_MENU_ENTER;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_MENU_OPEN:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_MENU_OPEN;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_MENU_SELECT:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_MENU_SELECT;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_MENU_BLOCKED:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_MENU_BLOCKED;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_MENU_EXIT:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_MENU_EXIT;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_SLEEP_ENTRY:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_SLEEP_ENTRY;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_DEEP_SLEEP:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_DEEP_SLEEP;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_WAKE:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_WAKE;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_RECORDING_START:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_RECORDING_START;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_RECORDING_ACTIVE:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_RECORDING_ACTIVE;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_RECORDING_SAVING:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVING;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_RECORDING_SAVED:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVED;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_RECORDING_ERROR:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_RECORDING_ERROR;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_UPGRADE_OFFER:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_UPGRADE_OFFER;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_UPGRADE_PREPARE:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_UPGRADE_PREPARE;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_UPGRADE_TRANSFER:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_UPGRADE_TRANSFER;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_UPGRADE_VERIFY:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_UPGRADE_VERIFY;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_UPGRADE_RESTART:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_UPGRADE_RESTART;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_UPGRADE_SUCCESS:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_UPGRADE_SUCCESS;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_UPGRADE_ERROR:
        *out_scene = COMP_PET_PERFORMANCE_SCENE_UPGRADE_ERROR;
        return true;
    case COMP_PET_PERFORMANCE_EVENT_RECORDING_RECOVER:
    case COMP_PET_PERFORMANCE_EVENT_UPGRADE_DISMISS:
    case COMP_PET_PERFORMANCE_EVENT_RECOVER_TO_IDLE:
    case COMP_PET_PERFORMANCE_EVENT_COUNT:
    default:
        return false;
    }
}

static bool performance_is_recording(const comp_pet_performance_t *performance)
{
    comp_pet_performance_frame_t frame;
    if (!comp_pet_performance_current(performance, &frame)) {
        return false;
    }
    return frame.scene == COMP_PET_PERFORMANCE_SCENE_RECORDING_START ||
           frame.scene == COMP_PET_PERFORMANCE_SCENE_RECORDING_ACTIVE ||
           frame.scene == COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVING ||
           frame.scene == COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVED ||
           frame.scene == COMP_PET_PERFORMANCE_SCENE_RECORDING_ERROR;
}

const char *comp_pet_performance_event_name(comp_pet_performance_event_t event)
{
    return event < COMP_PET_PERFORMANCE_EVENT_COUNT ? k_event_names[event] : "unknown";
}

bool comp_pet_performance_event_is_replay_only(comp_pet_performance_event_t event)
{
    return event >= COMP_PET_PERFORMANCE_EVENT_UPGRADE_OFFER &&
           event <= COMP_PET_PERFORMANCE_EVENT_UPGRADE_DISMISS;
}

bool comp_pet_performance_apply_event(comp_pet_performance_t *performance,
                                      comp_pet_performance_event_t event,
                                      comp_pet_performance_frame_t *out_frame)
{
    comp_pet_performance_scene_t scene;
    if (event == COMP_PET_PERFORMANCE_EVENT_RECORDING_RECOVER ||
        event == COMP_PET_PERFORMANCE_EVENT_UPGRADE_DISMISS ||
        event == COMP_PET_PERFORMANCE_EVENT_RECOVER_TO_IDLE) {
        return comp_pet_performance_recover_to_idle(performance, out_frame);
    }
    return event_scene(event, &scene) &&
           comp_pet_performance_begin(performance, scene, out_frame);
}

bool comp_pet_performance_apply_expression_signal(
    comp_pet_performance_t *performance,
    comp_epaper_expression_signal_t signal,
    comp_pet_performance_frame_t *out_frame)
{
    if (performance == NULL || out_frame == NULL) {
        return false;
    }
    switch (signal) {
    case COMP_EPAPER_EXPRESSION_SIGNAL_BOOT_IDLE:
    case COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_ARMED:
    case COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_CANCEL:
    case COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY:
    case COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED:
        return comp_pet_performance_recover_to_idle(performance, out_frame);
    case COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_DISABLED:
    case COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY:
        return comp_pet_performance_apply_event(performance,
                                                COMP_PET_PERFORMANCE_EVENT_SLEEP_ENTRY,
                                                out_frame);
    case COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_DETECTED:
        return comp_pet_performance_begin(performance,
                                          COMP_PET_PERFORMANCE_SCENE_VOICE_LISTENING,
                                          out_frame);
    case COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_PROMPT:
        return comp_pet_performance_begin(performance,
                                          COMP_PET_PERFORMANCE_SCENE_VOICE_SPEAKING,
                                          out_frame);
    case COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_START:
    case COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START:
        return comp_pet_performance_begin(performance,
                                          COMP_PET_PERFORMANCE_SCENE_RECORDING_START,
                                          out_frame);
    case COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_STOP:
    case COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_STOP:
        return comp_pet_performance_begin(performance,
                                          COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVING,
                                          out_frame);
    case COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_FINALIZE:
    case COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_FINISHED:
        return comp_pet_performance_begin(performance,
                                          COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVED,
                                          out_frame);
    case COMP_EPAPER_EXPRESSION_SIGNAL_LOW_BATTERY:
        return comp_pet_performance_begin(performance,
                                          COMP_PET_PERFORMANCE_SCENE_LOW_BATTERY,
                                          out_frame);
    case COMP_EPAPER_EXPRESSION_SIGNAL_ERROR:
        return comp_pet_performance_begin(
            performance,
            performance_is_recording(performance)
                ? COMP_PET_PERFORMANCE_SCENE_RECORDING_ERROR
                : COMP_PET_PERFORMANCE_SCENE_SYSTEM_ERROR,
            out_frame);
    case COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_RESULT:
    case COMP_EPAPER_EXPRESSION_SIGNAL_COUNT:
    default:
        return false;
    }
}

bool comp_pet_performance_event_bridge_self_test(void)
{
    comp_pet_performance_t performance;
    comp_pet_performance_frame_t frame;

    comp_pet_performance_init(&performance);
    if (!comp_pet_performance_apply_expression_signal(
            &performance, COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START, &frame) ||
        frame.scene != COMP_PET_PERFORMANCE_SCENE_RECORDING_START ||
        !comp_pet_performance_apply_expression_signal(
            &performance, COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_STOP, &frame) ||
        frame.scene != COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVING ||
        !comp_pet_performance_apply_expression_signal(
            &performance, COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_FINISHED, &frame) ||
        frame.scene != COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVED ||
        !comp_pet_performance_apply_expression_signal(
            &performance, COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY, &frame) ||
        frame.scene != COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE) {
        return false;
    }
    if (!comp_pet_performance_apply_expression_signal(
            &performance, COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_DETECTED, &frame) ||
        frame.scene != COMP_PET_PERFORMANCE_SCENE_VOICE_LISTENING ||
        !comp_pet_performance_apply_expression_signal(
            &performance, COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_PROMPT, &frame) ||
        frame.scene != COMP_PET_PERFORMANCE_SCENE_VOICE_SPEAKING ||
        comp_pet_performance_apply_expression_signal(
            &performance, COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_RESULT, &frame)) {
        return false;
    }
    if (!comp_pet_performance_apply_expression_signal(
            &performance, COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY, &frame) ||
        !comp_pet_performance_apply_event(
            &performance, COMP_PET_PERFORMANCE_EVENT_DAILY_SWIPE_LEFT, &frame) ||
        strcmp(frame.resource_family, "daily.swipe_left") != 0 ||
        !comp_pet_performance_apply_event(
            &performance, COMP_PET_PERFORMANCE_EVENT_MENU_HOLD, &frame) ||
        !comp_pet_performance_apply_event(
            &performance, COMP_PET_PERFORMANCE_EVENT_MENU_OPEN, &frame) ||
        frame.scene != COMP_PET_PERFORMANCE_SCENE_MENU_OPEN ||
        !comp_pet_performance_apply_event(
            &performance, COMP_PET_PERFORMANCE_EVENT_MENU_EXIT, &frame) ||
        frame.scene != COMP_PET_PERFORMANCE_SCENE_MENU_EXIT ||
        !comp_pet_performance_apply_expression_signal(
            &performance, COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY, &frame) ||
        frame.scene != COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE ||
        !comp_pet_performance_apply_event(
            &performance, COMP_PET_PERFORMANCE_EVENT_DAILY_TAP, &frame) ||
        frame.scene != COMP_PET_PERFORMANCE_SCENE_DAILY_TAP) {
        return false;
    }
    if (!comp_pet_performance_recover_to_idle(&performance, &frame) ||
        !comp_pet_performance_apply_event(
            &performance, COMP_PET_PERFORMANCE_EVENT_SLEEP_ENTRY, &frame) ||
        frame.scene != COMP_PET_PERFORMANCE_SCENE_SLEEP_ENTRY ||
        !comp_pet_performance_apply_expression_signal(
            &performance, COMP_EPAPER_EXPRESSION_SIGNAL_LOW_BATTERY, &frame) ||
        frame.scene != COMP_PET_PERFORMANCE_SCENE_LOW_BATTERY ||
        !comp_pet_performance_apply_expression_signal(
            &performance, COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED, &frame) ||
        frame.scene != COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE ||
        !comp_pet_performance_apply_expression_signal(
            &performance, COMP_EPAPER_EXPRESSION_SIGNAL_ERROR, &frame) ||
        frame.scene != COMP_PET_PERFORMANCE_SCENE_SYSTEM_ERROR ||
        strcmp(comp_pet_performance_event_name(COMP_PET_PERFORMANCE_EVENT_MENU_EXIT),
               "menu_exit") != 0 ||
        strcmp(comp_pet_performance_event_name(COMP_PET_PERFORMANCE_EVENT_COUNT),
               "unknown") != 0) {
        return false;
    }
    if (!comp_pet_performance_recover_to_idle(&performance, &frame) ||
        !comp_pet_performance_apply_event(
            &performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_OFFER, &frame) ||
        frame.scene != COMP_PET_PERFORMANCE_SCENE_UPGRADE_OFFER ||
        !comp_pet_performance_event_is_replay_only(
            COMP_PET_PERFORMANCE_EVENT_UPGRADE_OFFER) ||
        comp_pet_performance_event_is_replay_only(
            COMP_PET_PERFORMANCE_EVENT_RECORDING_START) ||
        !comp_pet_performance_apply_event(
            &performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_PREPARE, &frame) ||
        !comp_pet_performance_apply_event(
            &performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_TRANSFER, &frame) ||
        comp_pet_performance_apply_event(
            &performance, COMP_PET_PERFORMANCE_EVENT_MENU_HOLD, &frame) ||
        comp_pet_performance_apply_event(
            &performance, COMP_PET_PERFORMANCE_EVENT_RECORDING_START, &frame) ||
        !comp_pet_performance_apply_event(
            &performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_ERROR, &frame) ||
        frame.scene != COMP_PET_PERFORMANCE_SCENE_UPGRADE_ERROR ||
        !comp_pet_performance_apply_event(
            &performance, COMP_PET_PERFORMANCE_EVENT_UPGRADE_DISMISS, &frame) ||
        frame.scene != COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE) {
        return false;
    }
    return true;
}
