#include "menu_v5_navigation.h"
#include "pet_performance.h"

#include <stdio.h>

static int fail(const char *message)
{
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

static int expect_scene(const comp_menu_v5_navigation_result_t *result,
                        comp_pet_performance_scene_t expected_scene,
                        const char *message)
{
    comp_pet_performance_t performance;
    comp_pet_performance_frame_t frame;

    if (!result->has_selection || !result->selection.has_performance_event) {
        return fail(message);
    }
    comp_pet_performance_init(&performance);
    if (!comp_pet_performance_apply_event(&performance, result->selection.performance_event,
                                          &frame) ||
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
    const uint16_t root_y[COMP_MENU_V5_ROOT_COUNT] = {60u, 100u, 140u, 180u};
    comp_menu_v5_navigation_t navigation;
    comp_menu_v5_navigation_result_t result;
    comp_menu_v5_item_t item;
    uint8_t index;
    uint8_t root;

    comp_menu_v5_navigation_init(&navigation, (comp_menu_v5_language_t)9u);
    if (navigation.view != COMP_MENU_V5_NAVIGATION_ROOTS ||
        navigation.language != COMP_MENU_V5_LANGUAGE_EN || navigation.revision != 1u ||
        comp_menu_v5_navigation_root_hit_test(200u, 0u, NULL)) {
        return fail("initial state must use English and reject off-panel root hits");
    }
    for (root = 0u; root < COMP_MENU_V5_ROOT_COUNT; ++root) {
        result = comp_menu_v5_navigation_tap(&navigation, 100u, root_y[root], &ready);
        if (!result.changed || result.event != COMP_MENU_V5_NAVIGATION_EVENT_ROOT_OPENED ||
            navigation.view != COMP_MENU_V5_NAVIGATION_DETAILS ||
            navigation.root != (comp_menu_v5_root_t)root || result.has_selection) {
            return fail("each of the four root rows must open its matching detail page");
        }
        result = comp_menu_v5_navigation_back(&navigation);
        if (!result.changed || navigation.view != COMP_MENU_V5_NAVIGATION_ROOTS) {
            return fail("detail header back must return to the four root rows");
        }
    }

    result = comp_menu_v5_navigation_tap(&navigation, 100u, 60u, &ready);
    if (!result.changed || !comp_menu_v5_navigation_detail_hit_test(
                               &navigation, 100u, 41u, &ready, &index, &item) ||
        index != 0u || item.item_id != COMP_MENU_V5_ITEM_MANUAL_RECORDING) {
        return fail("voice first row must be the manual recording action");
    }
    result = comp_menu_v5_navigation_tap(&navigation, 100u, 41u, &ready);
    if (!result.has_selection || result.selection.item.action != COMP_MENU_V5_ACTION_RECORD_START ||
        result.selection.outcome != COMP_MENU_V5_SELECTION_ACTION_COMMITTED ||
        expect_scene(&result, COMP_PET_PERFORMANCE_SCENE_MENU_SELECT,
                     "record action must enter the menu select scene")) {
        return fail("voice selection must retain the actual recording action");
    }
    (void)comp_menu_v5_navigation_back(&navigation);

    result = comp_menu_v5_navigation_tap(&navigation, 100u, 100u, &ready);
    if (!result.changed || navigation.root != COMP_MENU_V5_ROOT_DEVICE ||
        !comp_menu_v5_navigation_detail_hit_test(&navigation, 100u, 41u, &ready, &index, &item) ||
        item.item_id != COMP_MENU_V5_ITEM_EPAPER_STATUS) {
        return fail("device first row must be the e-paper live status");
    }
    result = comp_menu_v5_navigation_tap(&navigation, 100u, 41u, &ready);
    if (!result.has_selection || result.selection.outcome != COMP_MENU_V5_SELECTION_LIVE_DATA ||
        result.selection.has_performance_event) {
        return fail("live status must remain display-only");
    }
    result = comp_menu_v5_navigation_tap(&navigation, 100u, 113u, &ready);
    if (!result.has_selection || result.selection.item.item_id != COMP_MENU_V5_ITEM_BATTERY_STATUS ||
        result.selection.outcome != COMP_MENU_V5_SELECTION_UNAVAILABLE ||
        expect_scene(&result, COMP_PET_PERFORMANCE_SCENE_MENU_BLOCKED,
                     "planned battery row must enter the menu blocked scene")) {
        return fail("planned status must remain visibly unavailable");
    }
    (void)comp_menu_v5_navigation_back(&navigation);

    result = comp_menu_v5_navigation_tap(&navigation, 100u, 180u, &ready);
    if (!result.changed || navigation.root != COMP_MENU_V5_ROOT_PREFERENCES ||
        comp_menu_v5_navigation_max_scroll_px(&navigation) != 20u) {
        return fail("preferences must provide the continuous-scroll detail page");
    }
    result = comp_menu_v5_navigation_drag(&navigation, -15);
    if (!result.changed || navigation.scroll_offset_px != 15u ||
        !comp_menu_v5_navigation_detail_hit_test(&navigation, 100u, 100u, &ready, &index, &item) ||
        index != 2u || item.item_id != COMP_MENU_V5_ITEM_REFRESH_POLICY) {
        return fail("drag offset must move content and hit testing together");
    }
    result = comp_menu_v5_navigation_drag_to(&navigation, 0);
    if (!result.changed || navigation.scroll_offset_px != 0u) {
        return fail("scroll must return to the exact finger-derived origin");
    }
    result = comp_menu_v5_navigation_tap(&navigation, 100u, 41u, &ready);
    if (!result.has_selection || !result.selection.language_changed ||
        navigation.language != COMP_MENU_V5_LANGUAGE_ZH_CN ||
        result.selection.performance_event != COMP_PET_PERFORMANCE_EVENT_MENU_SELECT) {
        return fail("language row must toggle the active menu language through selection");
    }
    result = comp_menu_v5_navigation_drag_to(&navigation, 99);
    if (!result.changed || navigation.scroll_offset_px != 20u) {
        return fail("scroll must clamp only at the real content limit");
    }
    result = comp_menu_v5_navigation_tap(&navigation, 100u, 60u, &ready);
    if (!result.has_selection || result.selection.item.item_id != COMP_MENU_V5_ITEM_GESTURE_POLICY ||
        result.selection.outcome != COMP_MENU_V5_SELECTION_UNAVAILABLE) {
        return fail("scrolled preference rows must remain index-correct and honest");
    }
    result = comp_menu_v5_navigation_tap(&navigation, 100u, 10u, &ready);
    if (!result.changed || result.event != COMP_MENU_V5_NAVIGATION_EVENT_ROOT_CLOSED ||
        navigation.view != COMP_MENU_V5_NAVIGATION_ROOTS || navigation.scroll_offset_px != 0u ||
        !comp_menu_v5_navigation_self_test()) {
        return fail("header back and portable self-test must preserve navigation state");
    }

    puts("PASS: menu-v5 navigation keeps four roots, finger-following detail scroll, and truthful row actions.");
    return 0;
}
