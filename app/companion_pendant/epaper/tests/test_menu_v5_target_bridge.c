#include "menu_v5_target_bridge.h"

#include <stdio.h>

static int fail(const char *message)
{
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

int main(void)
{
    const comp_menu_v5_context_t ready = {
        .panel_healthy = true,
        .touch_ready = true,
        .ble_connected = true,
        .external_assets_ready = true,
        .record_history_available = true,
    };
    comp_menu_v5_context_t recording = ready;
    comp_menu_v5_target_bridge_t bridge;
    comp_menu_v5_navigation_result_t result;

    if (comp_menu_v5_target_bridge_update_context(NULL, &ready) ||
        comp_menu_v5_target_bridge_tap(NULL, 100u, 60u).changed) {
        return fail("uninitialized target bridge must reject input");
    }
    comp_menu_v5_target_bridge_init(&bridge, COMP_MENU_V5_LANGUAGE_EN);
    if (!comp_menu_v5_target_bridge_update_context(&bridge, &ready)) {
        return fail("target bridge must accept the runtime context");
    }
    result = comp_menu_v5_target_bridge_tap(&bridge, 100u, 60u);
    if (!result.changed || result.event != COMP_MENU_V5_NAVIGATION_EVENT_ROOT_OPENED ||
        bridge.navigation.root != COMP_MENU_V5_ROOT_VOICE) {
        return fail("the target bridge must open the Voice root from its r4 row");
    }
    result = comp_menu_v5_target_bridge_tap(&bridge, 100u, 41u);
    if (!result.has_selection ||
        result.selection.item.action != COMP_MENU_V5_ACTION_RECORD_START ||
        result.selection.outcome != COMP_MENU_V5_SELECTION_ACTION_COMMITTED ||
        result.selection.performance_event != COMP_PET_PERFORMANCE_EVENT_MENU_SELECT) {
        return fail("voice action must return a real recording decision and select scene");
    }
    recording.recording = true;
    if (!comp_menu_v5_target_bridge_update_context(&bridge, &recording)) {
        return fail("target bridge must accept a recording-state update");
    }
    result = comp_menu_v5_target_bridge_tap(&bridge, 100u, 41u);
    if (!result.has_selection ||
        result.selection.item.action != COMP_MENU_V5_ACTION_RECORD_STOP) {
        return fail("the same Voice row must become the real stop action while recording");
    }
    result = comp_menu_v5_target_bridge_back(&bridge);
    if (!result.changed || bridge.navigation.view != COMP_MENU_V5_NAVIGATION_ROOTS) {
        return fail("target bridge back must return from details to roots");
    }
    result = comp_menu_v5_target_bridge_tap(&bridge, 100u, 180u);
    if (!result.changed || bridge.navigation.root != COMP_MENU_V5_ROOT_PREFERENCES) {
        return fail("the fourth r4 row must remain Preferences");
    }
    result = comp_menu_v5_target_bridge_drag(&bridge, -20);
    if (!result.changed || bridge.navigation.scroll_offset_px != 20u) {
        return fail("target bridge must preserve finger-following continuous scrolling");
    }
    result = comp_menu_v5_target_bridge_tap(&bridge, 100u, 41u);
    if (!result.has_selection || !result.selection.language_changed ||
        bridge.navigation.language != COMP_MENU_V5_LANGUAGE_ZH_CN) {
        return fail("language selection must change the bridge-local language state");
    }
    if (!comp_menu_v5_target_bridge_self_test()) {
        return fail("target bridge self-test must pass");
    }

    puts("PASS: target bridge keeps the four-root UI contract and returns only truthful decisions.");
    return 0;
}
