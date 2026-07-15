#include "menu_v5_action_journey.h"
#include "pet_performance.h"

#include <stdio.h>

static int fail(const char *message)
{
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

static int expect_performance_scene(const comp_menu_v5_selection_result_t *result,
                                    comp_pet_performance_scene_t expected_scene,
                                    const char *message)
{
    comp_pet_performance_t performance;
    comp_pet_performance_frame_t frame;

    if (!result->has_performance_event) {
        return fail(message);
    }
    comp_pet_performance_init(&performance);
    if (!comp_pet_performance_apply_event(&performance, result->performance_event, &frame) ||
        frame.scene != expected_scene) {
        return fail(message);
    }
    return 0;
}

int main(void)
{
    const comp_menu_v5_context_t ready = {
        .panel_healthy = true,
        .touch_ready = true,
        .ble_connected = true,
        .battery_supported = false,
        .external_assets_ready = true,
        .record_history_available = true,
        .wake_word_available = false,
        .diagnostics_available = false,
    };
    comp_menu_v5_selection_result_t result;

    if (!comp_menu_v5_prepare_selection(COMP_MENU_V5_ROOT_VOICE, 0u, &ready,
                                        COMP_MENU_V5_LANGUAGE_EN, &result) ||
        result.outcome != COMP_MENU_V5_SELECTION_LIVE_DATA ||
        result.item.item_id != COMP_MENU_V5_ITEM_RECORDING_STATUS ||
        result.item.action != COMP_MENU_V5_ACTION_NONE ||
        !result.item.has_live_value || result.item.live_value ||
        result.has_performance_event ||
        result.language_changed || result.language_after != COMP_MENU_V5_LANGUAGE_EN) {
        return fail("idle recording status must remain display-only without a menu scene");
    }
    {
        comp_menu_v5_context_t recording = ready;
        recording.recording = true;
        if (!comp_menu_v5_prepare_selection(COMP_MENU_V5_ROOT_VOICE, 0u, &recording,
                                            COMP_MENU_V5_LANGUAGE_EN, &result) ||
            result.outcome != COMP_MENU_V5_SELECTION_LIVE_DATA ||
            !result.item.has_live_value || !result.item.live_value ||
            result.has_performance_event) {
            return fail("active recording status must remain display-only without a menu scene");
        }
    }
    if (!comp_menu_v5_prepare_selection(COMP_MENU_V5_ROOT_PREFERENCES, 0u, &ready,
                                        COMP_MENU_V5_LANGUAGE_EN, &result) ||
        result.item.action != COMP_MENU_V5_ACTION_LANGUAGE ||
        !result.language_changed || result.language_after != COMP_MENU_V5_LANGUAGE_ZH_CN ||
        result.performance_event != COMP_PET_PERFORMANCE_EVENT_MENU_SELECT) {
        return fail("language action must commit a select and produce Chinese");
    }
    if (!comp_menu_v5_prepare_selection(COMP_MENU_V5_ROOT_DEVICE, 0u, &ready,
                                        COMP_MENU_V5_LANGUAGE_EN, &result) ||
        result.outcome != COMP_MENU_V5_SELECTION_LIVE_DATA || result.has_performance_event ||
        result.performance_event != COMP_PET_PERFORMANCE_EVENT_COUNT) {
        return fail("live data must not manufacture a menu animation or action");
    }
    if (!comp_menu_v5_prepare_selection(COMP_MENU_V5_ROOT_VOICE, 2u, &ready,
                                        COMP_MENU_V5_LANGUAGE_EN, &result) ||
        result.outcome != COMP_MENU_V5_SELECTION_UNAVAILABLE ||
        !result.has_performance_event ||
        result.performance_event != COMP_PET_PERFORMANCE_EVENT_MENU_BLOCKED) {
        return fail("deferred wake word must report a blocked menu decision");
    }
    if (expect_performance_scene(&result, COMP_PET_PERFORMANCE_SCENE_MENU_BLOCKED,
                                 "deferred wake word must reach the menu blocked scene")) {
        return 1;
    }
    if (!comp_menu_v5_prepare_selection(COMP_MENU_V5_ROOT_DEVICE, 2u, &ready,
                                        COMP_MENU_V5_LANGUAGE_EN, &result) ||
        result.outcome != COMP_MENU_V5_SELECTION_UNAVAILABLE ||
        result.performance_event != COMP_PET_PERFORMANCE_EVENT_MENU_BLOCKED ||
        comp_menu_v5_prepare_selection((comp_menu_v5_root_t)4u, 0u, &ready,
                                       COMP_MENU_V5_LANGUAGE_EN, &result) ||
        comp_menu_v5_prepare_selection(COMP_MENU_V5_ROOT_VOICE, 0u, &ready,
                                       (comp_menu_v5_language_t)2u, &result)) {
        return fail("planned and invalid menu selections must not become actions");
    }
    printf("PASS: menu-v5 selection routes actions, live data, unavailable rows, and language correctly.\n");
    return 0;
}
