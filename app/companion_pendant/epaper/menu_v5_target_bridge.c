#include "menu_v5_target_bridge.h"

#include <stddef.h>

static comp_menu_v5_navigation_result_t empty_result(void)
{
    return (comp_menu_v5_navigation_result_t){0};
}

void comp_menu_v5_target_bridge_init(comp_menu_v5_target_bridge_t *bridge,
                                     comp_menu_v5_language_t language)
{
    if (bridge == NULL) {
        return;
    }
    *bridge = (comp_menu_v5_target_bridge_t){0};
    comp_menu_v5_navigation_init(&bridge->navigation, language);
    bridge->initialized = true;
}

bool comp_menu_v5_target_bridge_update_context(comp_menu_v5_target_bridge_t *bridge,
                                                const comp_menu_v5_context_t *context)
{
    if (bridge == NULL || !bridge->initialized || context == NULL) {
        return false;
    }
    bridge->context = *context;
    return true;
}

comp_menu_v5_navigation_result_t comp_menu_v5_target_bridge_tap(
    comp_menu_v5_target_bridge_t *bridge,
    uint16_t x,
    uint16_t y)
{
    if (bridge == NULL || !bridge->initialized) {
        return empty_result();
    }
    return comp_menu_v5_navigation_tap(&bridge->navigation, x, y, &bridge->context);
}

comp_menu_v5_navigation_result_t comp_menu_v5_target_bridge_drag(
    comp_menu_v5_target_bridge_t *bridge,
    int16_t finger_delta_y)
{
    if (bridge == NULL || !bridge->initialized) {
        return empty_result();
    }
    return comp_menu_v5_navigation_drag(&bridge->navigation, finger_delta_y);
}

comp_menu_v5_navigation_result_t comp_menu_v5_target_bridge_back(
    comp_menu_v5_target_bridge_t *bridge)
{
    if (bridge == NULL || !bridge->initialized) {
        return empty_result();
    }
    return comp_menu_v5_navigation_back(&bridge->navigation);
}

bool comp_menu_v5_target_bridge_self_test(void)
{
    const comp_menu_v5_context_t context = {
        .panel_healthy = true,
        .touch_ready = true,
        .ble_connected = true,
        .external_assets_ready = true,
    };
    comp_menu_v5_target_bridge_t bridge;
    comp_menu_v5_navigation_result_t result;

    comp_menu_v5_target_bridge_init(&bridge, COMP_MENU_V5_LANGUAGE_EN);
    if (!comp_menu_v5_target_bridge_update_context(&bridge, &context) ||
        bridge.navigation.view != COMP_MENU_V5_NAVIGATION_ROOTS ||
        bridge.navigation.revision != 1u) {
        return false;
    }
    result = comp_menu_v5_target_bridge_tap(&bridge, 100u, 60u);
    if (!result.changed || result.event != COMP_MENU_V5_NAVIGATION_EVENT_ROOT_OPENED ||
        bridge.navigation.root != COMP_MENU_V5_ROOT_VOICE) {
        return false;
    }
    result = comp_menu_v5_target_bridge_tap(&bridge, 100u, 41u);
    if (!result.changed || !result.has_selection ||
        result.selection.item.item_id != COMP_MENU_V5_ITEM_RECORDING_STATUS ||
        result.selection.outcome != COMP_MENU_V5_SELECTION_LIVE_DATA ||
        result.selection.has_performance_event) {
        return false;
    }
    result = comp_menu_v5_target_bridge_back(&bridge);
    return result.changed && result.event == COMP_MENU_V5_NAVIGATION_EVENT_ROOT_CLOSED &&
           bridge.navigation.view == COMP_MENU_V5_NAVIGATION_ROOTS;
}
