#include "menu_v5_view_model.h"

#include <stdio.h>
#include <string.h>

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
        .diagnostics_available = false,
    };
    comp_menu_v5_navigation_t navigation;
    comp_menu_v5_view_model_t model;

    if (comp_menu_v5_view_model_build(NULL, &ready, &model)) {
        return fail("view model must reject a missing navigation state");
    }
    comp_menu_v5_navigation_init(&navigation, COMP_MENU_V5_LANGUAGE_EN);
    if (!comp_menu_v5_view_model_build(&navigation, &ready, &model) ||
        model.view != COMP_MENU_V5_NAVIGATION_ROOTS || !model.has_identity_mark ||
        model.has_back_affordance || model.row_count != 4u ||
        strcmp(model.rows[0].label, "Voice") != 0 ||
        strcmp(model.rows[3].label, "Preferences") != 0 ||
        model.rows[0].trailing != COMP_MENU_V5_VIEW_MODEL_TRAILING_CHEVRON ||
        model.identity_component != COMP_MENU_V5_VIEW_MODEL_COMPONENT_HEADER_FACE ||
        model.rows[0].leading_component != COMP_MENU_V5_VIEW_MODEL_COMPONENT_VOICE_ICON ||
        model.rows[1].leading_component != COMP_MENU_V5_VIEW_MODEL_COMPONENT_DEVICE_ICON ||
        model.rows[2].leading_component != COMP_MENU_V5_VIEW_MODEL_COMPONENT_CONNECTION_ICON ||
        model.rows[3].leading_component != COMP_MENU_V5_VIEW_MODEL_COMPONENT_PREFERENCES_ICON ||
        model.rows[0].trailing_component != COMP_MENU_V5_VIEW_MODEL_COMPONENT_CHEVRON ||
        !model.rows[0].is_navigation) {
        return fail("root model must exactly describe the four-root navigation rows");
    }
    (void)comp_menu_v5_navigation_tap(&navigation, 100u, 60u, &ready);
    if (!comp_menu_v5_view_model_build(&navigation, &ready, &model) ||
        strcmp(model.title, "Voice") != 0 || model.row_count != 3u ||
        strcmp(model.rows[0].label, "Recording") != 0 ||
        model.rows[0].trailing != COMP_MENU_V5_VIEW_MODEL_TRAILING_LIVE_STATUS ||
        model.rows[0].trailing_component != COMP_MENU_V5_VIEW_MODEL_COMPONENT_LIVE_MARK ||
        model.rows[0].action != COMP_MENU_V5_ACTION_NONE ||
        !model.rows[0].has_live_value || model.rows[0].live_value ||
        model.rows[0].action_label != NULL) {
        return fail("Voice must expose recording status as live data, not a record action");
    }
    (void)comp_menu_v5_navigation_back(&navigation);
    (void)comp_menu_v5_navigation_tap(&navigation, 100u, 100u, &ready);
    if (!comp_menu_v5_view_model_build(&navigation, &ready, &model) ||
        strcmp(model.title, "Device") != 0 || !model.has_back_affordance ||
        model.row_count != 4u ||
        model.rows[0].trailing != COMP_MENU_V5_VIEW_MODEL_TRAILING_LIVE_STATUS ||
        !model.rows[0].has_live_value || !model.rows[0].live_value ||
        model.rows[0].action != COMP_MENU_V5_ACTION_NONE ||
        model.rows[2].trailing != COMP_MENU_V5_VIEW_MODEL_TRAILING_PLANNED) {
        return fail("device model must keep live facts and planned rows visually honest");
    }
    (void)comp_menu_v5_navigation_back(&navigation);
    (void)comp_menu_v5_navigation_tap(&navigation, 100u, 180u, &ready);
    if (!comp_menu_v5_view_model_build(&navigation, &ready, &model) ||
        model.row_count != 5u || strcmp(model.rows[0].label, "Language") != 0 ||
        strcmp(model.rows[0].action_label, "Switch language") != 0 ||
        strcmp(model.rows[0].value_label, "English") != 0 ||
        model.rows[1].trailing != COMP_MENU_V5_VIEW_MODEL_TRAILING_DEFERRED ||
        model.rows[1].trailing_component != COMP_MENU_V5_VIEW_MODEL_COMPONENT_DEFERRED_BADGE ||
        model.rows[4].trailing != COMP_MENU_V5_VIEW_MODEL_TRAILING_LIVE_STATUS) {
        return fail("preference model must expose action, deferred, and live rows without fake controls");
    }
    navigation.language = COMP_MENU_V5_LANGUAGE_ZH_CN;
    if (!comp_menu_v5_view_model_build(&navigation, &ready, &model) ||
        strcmp(model.title, "偏好设置") != 0 || strcmp(model.rows[0].label, "语言") != 0 ||
        strcmp(model.rows[0].action_label, "切换语言") != 0 ||
        strcmp(model.rows[0].value_label, "中文") != 0 ||
        !comp_menu_v5_view_model_self_test()) {
        return fail("view model must preserve complete Chinese state and self-test");
    }

    puts("PASS: menu-v5 view model keeps four-root geometry, honest affordances, and bilingual runtime content.");
    return 0;
}
