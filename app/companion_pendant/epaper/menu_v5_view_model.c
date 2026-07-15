#include "menu_v5_view_model.h"

#include <stddef.h>
#include <string.h>

static bool root_title(const comp_menu_v5_navigation_t *navigation, const char **out_title)
{
    comp_menu_v5_text_key_t key;

    return navigation != NULL && out_title != NULL &&
           comp_menu_v5_root_text_key(navigation->root, &key) &&
           ((*out_title = comp_menu_v5_text(navigation->language, key)) != NULL);
}

static comp_menu_v5_view_model_trailing_t trailing_for_kind(comp_menu_v5_item_kind_t kind)
{
    switch (kind) {
    case COMP_MENU_V5_ITEM_ACTION:
        return COMP_MENU_V5_VIEW_MODEL_TRAILING_CHEVRON;
    case COMP_MENU_V5_ITEM_LIVE_DATA:
        return COMP_MENU_V5_VIEW_MODEL_TRAILING_LIVE_STATUS;
    case COMP_MENU_V5_ITEM_DEFERRED:
        return COMP_MENU_V5_VIEW_MODEL_TRAILING_DEFERRED;
    case COMP_MENU_V5_ITEM_PLANNED:
        return COMP_MENU_V5_VIEW_MODEL_TRAILING_PLANNED;
    default:
        return COMP_MENU_V5_VIEW_MODEL_TRAILING_NONE;
    }
}

static comp_menu_v5_view_model_component_t trailing_component_for_kind(
    comp_menu_v5_item_kind_t kind)
{
    switch (kind) {
    case COMP_MENU_V5_ITEM_ACTION:
        return COMP_MENU_V5_VIEW_MODEL_COMPONENT_CHEVRON;
    case COMP_MENU_V5_ITEM_LIVE_DATA:
        return COMP_MENU_V5_VIEW_MODEL_COMPONENT_LIVE_MARK;
    case COMP_MENU_V5_ITEM_DEFERRED:
    case COMP_MENU_V5_ITEM_PLANNED:
        return COMP_MENU_V5_VIEW_MODEL_COMPONENT_DEFERRED_BADGE;
    default:
        return COMP_MENU_V5_VIEW_MODEL_COMPONENT_NONE;
    }
}

static comp_menu_v5_view_model_component_t root_component(comp_menu_v5_root_t root)
{
    switch (root) {
    case COMP_MENU_V5_ROOT_VOICE:
        return COMP_MENU_V5_VIEW_MODEL_COMPONENT_VOICE_ICON;
    case COMP_MENU_V5_ROOT_DEVICE:
        return COMP_MENU_V5_VIEW_MODEL_COMPONENT_DEVICE_ICON;
    case COMP_MENU_V5_ROOT_CONNECTION:
        return COMP_MENU_V5_VIEW_MODEL_COMPONENT_CONNECTION_ICON;
    case COMP_MENU_V5_ROOT_PREFERENCES:
        return COMP_MENU_V5_VIEW_MODEL_COMPONENT_PREFERENCES_ICON;
    default:
        return COMP_MENU_V5_VIEW_MODEL_COMPONENT_NONE;
    }
}

bool comp_menu_v5_view_model_build(const comp_menu_v5_navigation_t *navigation,
                                   const comp_menu_v5_context_t *context,
                                   comp_menu_v5_view_model_t *out_model)
{
    comp_menu_v5_view_model_row_t *row;

    if (navigation == NULL || context == NULL || out_model == NULL ||
        !comp_menu_v5_language_is_valid(navigation->language) ||
        navigation->root >= COMP_MENU_V5_ROOT_COUNT) {
        return false;
    }
    *out_model = (comp_menu_v5_view_model_t){
        .view = navigation->view,
        .root = navigation->root,
        .language = navigation->language,
        .scroll_offset_px = navigation->scroll_offset_px,
    };
    if (navigation->view == COMP_MENU_V5_NAVIGATION_ROOTS) {
        out_model->has_identity_mark = true;
        out_model->identity_component = COMP_MENU_V5_VIEW_MODEL_COMPONENT_HEADER_FACE;
        out_model->row_count = COMP_MENU_V5_ROOT_COUNT;
        for (uint8_t index = 0u; index < COMP_MENU_V5_ROOT_COUNT; ++index) {
            comp_menu_v5_text_key_t key;

            if (!comp_menu_v5_root_text_key((comp_menu_v5_root_t)index, &key)) {
                return false;
            }
            row = &out_model->rows[index];
            *row = (comp_menu_v5_view_model_row_t){
                .label = comp_menu_v5_text(navigation->language, key),
                .kind = COMP_MENU_V5_ITEM_ACTION,
                .trailing = COMP_MENU_V5_VIEW_MODEL_TRAILING_CHEVRON,
                .leading_component = root_component((comp_menu_v5_root_t)index),
                .trailing_component = COMP_MENU_V5_VIEW_MODEL_COMPONENT_CHEVRON,
                .is_navigation = true,
            };
            if (row->label == NULL) {
                return false;
            }
        }
        return true;
    }
    if (navigation->view != COMP_MENU_V5_NAVIGATION_DETAILS ||
        !root_title(navigation, &out_model->title)) {
        return false;
    }
    out_model->has_back_affordance = true;
    out_model->has_identity_mark = true;
    out_model->identity_component = COMP_MENU_V5_VIEW_MODEL_COMPONENT_HEADER_FACE;
    out_model->row_count = comp_menu_v5_root_item_count(navigation->root);
    if (out_model->row_count > COMP_MENU_V5_VIEW_MODEL_MAX_ROWS) {
        return false;
    }
    for (uint8_t index = 0u; index < out_model->row_count; ++index) {
        comp_menu_v5_item_t item;

        if (!comp_menu_v5_resolve_item(navigation->root, index, context, &item)) {
            return false;
        }
        row = &out_model->rows[index];
        *row = (comp_menu_v5_view_model_row_t){
            .label = comp_menu_v5_text(navigation->language, item.text_key),
            .action_label = comp_menu_v5_action_label(navigation->language, item.action),
            .kind = item.kind,
            .action = item.action,
            .trailing = trailing_for_kind(item.kind),
            .trailing_component = trailing_component_for_kind(item.kind),
            .has_live_value = item.has_live_value,
            .live_value = item.live_value,
        };
        if (row->label == NULL) {
            return false;
        }
        if (item.item_id == COMP_MENU_V5_ITEM_LANGUAGE) {
            row->value_label = comp_menu_v5_language_display_name(navigation->language);
            if (row->value_label == NULL) {
                return false;
            }
        }
    }
    return true;
}

bool comp_menu_v5_view_model_self_test(void)
{
    const comp_menu_v5_context_t context = {
        .panel_healthy = true,
        .touch_ready = true,
        .ble_connected = true,
        .external_assets_ready = true,
    };
    comp_menu_v5_navigation_t navigation;
    comp_menu_v5_view_model_t model;

    comp_menu_v5_navigation_init(&navigation, COMP_MENU_V5_LANGUAGE_EN);
    if (!comp_menu_v5_view_model_build(&navigation, &context, &model) ||
        !model.has_identity_mark || model.row_count != COMP_MENU_V5_ROOT_COUNT ||
        strcmp(model.rows[0].label, "Voice") != 0 ||
        model.rows[0].trailing != COMP_MENU_V5_VIEW_MODEL_TRAILING_CHEVRON ||
        model.identity_component != COMP_MENU_V5_VIEW_MODEL_COMPONENT_HEADER_FACE ||
        model.rows[0].leading_component != COMP_MENU_V5_VIEW_MODEL_COMPONENT_VOICE_ICON ||
        model.rows[1].leading_component != COMP_MENU_V5_VIEW_MODEL_COMPONENT_DEVICE_ICON ||
        model.rows[2].leading_component != COMP_MENU_V5_VIEW_MODEL_COMPONENT_CONNECTION_ICON ||
        model.rows[3].leading_component != COMP_MENU_V5_VIEW_MODEL_COMPONENT_PREFERENCES_ICON ||
        model.rows[0].trailing_component != COMP_MENU_V5_VIEW_MODEL_COMPONENT_CHEVRON ||
        !model.rows[0].is_navigation) {
        return false;
    }
    (void)comp_menu_v5_navigation_tap(&navigation, 100u, 60u, &context);
    if (!comp_menu_v5_view_model_build(&navigation, &context, &model) ||
        strcmp(model.title, "Voice") != 0 || model.row_count != 3u ||
        strcmp(model.rows[0].label, "Recording") != 0 ||
        model.rows[0].trailing != COMP_MENU_V5_VIEW_MODEL_TRAILING_LIVE_STATUS ||
        model.rows[0].trailing_component != COMP_MENU_V5_VIEW_MODEL_COMPONENT_LIVE_MARK ||
        model.rows[0].action != COMP_MENU_V5_ACTION_NONE ||
        !model.rows[0].has_live_value || model.rows[0].live_value ||
        model.rows[0].action_label != NULL) {
        return false;
    }
    (void)comp_menu_v5_navigation_back(&navigation);
    (void)comp_menu_v5_navigation_tap(&navigation, 100u, 180u, &context);
    if (!comp_menu_v5_view_model_build(&navigation, &context, &model) ||
        !model.has_back_affordance || strcmp(model.title, "Preferences") != 0 ||
        model.row_count != 5u ||
        model.rows[0].trailing != COMP_MENU_V5_VIEW_MODEL_TRAILING_CHEVRON ||
        strcmp(model.rows[0].value_label, "English") != 0 ||
        model.rows[1].trailing != COMP_MENU_V5_VIEW_MODEL_TRAILING_DEFERRED ||
        model.rows[1].trailing_component != COMP_MENU_V5_VIEW_MODEL_COMPONENT_DEFERRED_BADGE) {
        return false;
    }
    navigation.language = COMP_MENU_V5_LANGUAGE_ZH_CN;
    return comp_menu_v5_view_model_build(&navigation, &context, &model) &&
           strcmp(model.title, "偏好设置") == 0 && strcmp(model.rows[0].label, "语言") == 0 &&
           strcmp(model.rows[0].value_label, "中文") == 0;
}
