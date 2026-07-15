#include "menu_v5_contract.h"

#include <stddef.h>

typedef struct {
    comp_menu_v5_item_id_t item_id;
    comp_menu_v5_text_key_t text_key;
    comp_menu_v5_item_kind_t kind;
} comp_menu_v5_item_definition_t;

static const comp_menu_v5_text_key_t k_root_text_keys[COMP_MENU_V5_ROOT_COUNT] = {
    COMP_MENU_V5_TEXT_VOICE,
    COMP_MENU_V5_TEXT_DEVICE,
    COMP_MENU_V5_TEXT_CONNECTION,
    COMP_MENU_V5_TEXT_PREFERENCES,
};

static const comp_menu_v5_item_definition_t k_voice_items[] = {
    {COMP_MENU_V5_ITEM_MANUAL_RECORDING, COMP_MENU_V5_TEXT_MANUAL_RECORDING, COMP_MENU_V5_ITEM_ACTION},
    {COMP_MENU_V5_ITEM_RECORD_HISTORY, COMP_MENU_V5_TEXT_RECORD_HISTORY, COMP_MENU_V5_ITEM_DEFERRED},
    {COMP_MENU_V5_ITEM_WAKE_WORD, COMP_MENU_V5_TEXT_WAKE_WORD, COMP_MENU_V5_ITEM_DEFERRED},
};

static const comp_menu_v5_item_definition_t k_device_items[] = {
    {COMP_MENU_V5_ITEM_EPAPER_STATUS, COMP_MENU_V5_TEXT_EPAPER, COMP_MENU_V5_ITEM_LIVE_DATA},
    {COMP_MENU_V5_ITEM_TOUCH_STATUS, COMP_MENU_V5_TEXT_TOUCH, COMP_MENU_V5_ITEM_LIVE_DATA},
    {COMP_MENU_V5_ITEM_BATTERY_STATUS, COMP_MENU_V5_TEXT_BATTERY, COMP_MENU_V5_ITEM_PLANNED},
    {COMP_MENU_V5_ITEM_UI_ASSETS, COMP_MENU_V5_TEXT_UI_ASSETS, COMP_MENU_V5_ITEM_LIVE_DATA},
};

static const comp_menu_v5_item_definition_t k_connection_items[] = {
    {COMP_MENU_V5_ITEM_PAIR_NEW_DEVICE, COMP_MENU_V5_TEXT_PAIR_NEW_DEVICE, COMP_MENU_V5_ITEM_ACTION},
    {COMP_MENU_V5_ITEM_LINK_STATUS, COMP_MENU_V5_TEXT_LINK_STATUS, COMP_MENU_V5_ITEM_LIVE_DATA},
    {COMP_MENU_V5_ITEM_RECONNECT, COMP_MENU_V5_TEXT_RECONNECT, COMP_MENU_V5_ITEM_ACTION},
};

static const comp_menu_v5_item_definition_t k_preferences_items[] = {
    {COMP_MENU_V5_ITEM_LANGUAGE, COMP_MENU_V5_TEXT_LANGUAGE, COMP_MENU_V5_ITEM_ACTION},
    {COMP_MENU_V5_ITEM_GESTURE_POLICY, COMP_MENU_V5_TEXT_GESTURE, COMP_MENU_V5_ITEM_DEFERRED},
    {COMP_MENU_V5_ITEM_REFRESH_POLICY, COMP_MENU_V5_TEXT_REFRESH, COMP_MENU_V5_ITEM_DEFERRED},
    {COMP_MENU_V5_ITEM_DIAGNOSTICS, COMP_MENU_V5_TEXT_DIAGNOSTICS, COMP_MENU_V5_ITEM_DEFERRED},
    {COMP_MENU_V5_ITEM_ABOUT, COMP_MENU_V5_TEXT_ABOUT, COMP_MENU_V5_ITEM_LIVE_DATA},
};

static bool definition_at(comp_menu_v5_root_t root,
                          uint8_t index,
                          const comp_menu_v5_item_definition_t **out_definition)
{
    const comp_menu_v5_item_definition_t *items = NULL;
    uint8_t count = 0u;

    if (out_definition == NULL) {
        return false;
    }
    switch (root) {
    case COMP_MENU_V5_ROOT_VOICE:
        items = k_voice_items;
        count = (uint8_t)(sizeof(k_voice_items) / sizeof(k_voice_items[0]));
        break;
    case COMP_MENU_V5_ROOT_DEVICE:
        items = k_device_items;
        count = (uint8_t)(sizeof(k_device_items) / sizeof(k_device_items[0]));
        break;
    case COMP_MENU_V5_ROOT_CONNECTION:
        items = k_connection_items;
        count = (uint8_t)(sizeof(k_connection_items) / sizeof(k_connection_items[0]));
        break;
    case COMP_MENU_V5_ROOT_PREFERENCES:
        items = k_preferences_items;
        count = (uint8_t)(sizeof(k_preferences_items) / sizeof(k_preferences_items[0]));
        break;
    default:
        return false;
    }
    if (index >= count) {
        return false;
    }
    *out_definition = &items[index];
    return true;
}

uint8_t comp_menu_v5_root_item_count(comp_menu_v5_root_t root)
{
    switch (root) {
    case COMP_MENU_V5_ROOT_VOICE:
        return (uint8_t)(sizeof(k_voice_items) / sizeof(k_voice_items[0]));
    case COMP_MENU_V5_ROOT_DEVICE:
        return (uint8_t)(sizeof(k_device_items) / sizeof(k_device_items[0]));
    case COMP_MENU_V5_ROOT_CONNECTION:
        return (uint8_t)(sizeof(k_connection_items) / sizeof(k_connection_items[0]));
    case COMP_MENU_V5_ROOT_PREFERENCES:
        return (uint8_t)(sizeof(k_preferences_items) / sizeof(k_preferences_items[0]));
    default:
        return 0u;
    }
}

bool comp_menu_v5_root_text_key(comp_menu_v5_root_t root, comp_menu_v5_text_key_t *out_key)
{
    if (out_key == NULL || root >= COMP_MENU_V5_ROOT_COUNT) {
        return false;
    }
    *out_key = k_root_text_keys[(uint8_t)root];
    return true;
}

bool comp_menu_v5_resolve_item(comp_menu_v5_root_t root,
                               uint8_t index,
                               const comp_menu_v5_context_t *context,
                               comp_menu_v5_item_t *out_item)
{
    const comp_menu_v5_item_definition_t *definition;
    const comp_menu_v5_context_t empty_context = {0};

    if (out_item == NULL || !definition_at(root, index, &definition)) {
        return false;
    }
    if (context == NULL) {
        context = &empty_context;
    }
    *out_item = (comp_menu_v5_item_t){
        .root = root,
        .item_id = definition->item_id,
        .text_key = definition->text_key,
        .kind = definition->kind,
        .action = COMP_MENU_V5_ACTION_NONE,
    };
    switch (definition->item_id) {
    case COMP_MENU_V5_ITEM_MANUAL_RECORDING:
        out_item->action = context->recording ? COMP_MENU_V5_ACTION_RECORD_STOP :
                                                COMP_MENU_V5_ACTION_RECORD_START;
        break;
    case COMP_MENU_V5_ITEM_RECORD_HISTORY:
        out_item->kind = context->record_history_available ? COMP_MENU_V5_ITEM_LIVE_DATA :
                                                            COMP_MENU_V5_ITEM_DEFERRED;
        out_item->has_live_value = context->record_history_available;
        out_item->live_value = context->record_history_available;
        break;
    case COMP_MENU_V5_ITEM_WAKE_WORD:
        out_item->kind = context->wake_word_available ? COMP_MENU_V5_ITEM_LIVE_DATA :
                                                       COMP_MENU_V5_ITEM_DEFERRED;
        out_item->has_live_value = context->wake_word_available;
        out_item->live_value = context->wake_word_available;
        break;
    case COMP_MENU_V5_ITEM_EPAPER_STATUS:
        out_item->has_live_value = true;
        out_item->live_value = context->panel_healthy;
        break;
    case COMP_MENU_V5_ITEM_TOUCH_STATUS:
        out_item->has_live_value = true;
        out_item->live_value = context->touch_ready;
        break;
    case COMP_MENU_V5_ITEM_BATTERY_STATUS:
        out_item->kind = context->battery_supported ? COMP_MENU_V5_ITEM_LIVE_DATA :
                                                     COMP_MENU_V5_ITEM_PLANNED;
        out_item->has_live_value = context->battery_supported;
        out_item->live_value = context->battery_supported;
        break;
    case COMP_MENU_V5_ITEM_UI_ASSETS:
        out_item->has_live_value = true;
        out_item->live_value = context->external_assets_ready;
        break;
    case COMP_MENU_V5_ITEM_PAIR_NEW_DEVICE:
        out_item->action = COMP_MENU_V5_ACTION_PAIR_NEW_DEVICE;
        break;
    case COMP_MENU_V5_ITEM_LINK_STATUS:
        out_item->has_live_value = true;
        out_item->live_value = context->ble_connected;
        break;
    case COMP_MENU_V5_ITEM_RECONNECT:
        out_item->action = COMP_MENU_V5_ACTION_RECONNECT;
        break;
    case COMP_MENU_V5_ITEM_LANGUAGE:
        out_item->action = COMP_MENU_V5_ACTION_LANGUAGE;
        break;
    case COMP_MENU_V5_ITEM_GESTURE_POLICY:
    case COMP_MENU_V5_ITEM_REFRESH_POLICY:
        break;
    case COMP_MENU_V5_ITEM_DIAGNOSTICS:
        out_item->kind = context->diagnostics_available ? COMP_MENU_V5_ITEM_LIVE_DATA :
                                                         COMP_MENU_V5_ITEM_DEFERRED;
        out_item->has_live_value = context->diagnostics_available;
        out_item->live_value = context->diagnostics_available;
        break;
    case COMP_MENU_V5_ITEM_ABOUT:
        out_item->has_live_value = true;
        out_item->live_value = true;
        break;
    default:
        return false;
    }
    return true;
}

bool comp_menu_v5_item_is_selectable(const comp_menu_v5_item_t *item)
{
    return item != NULL && item->kind == COMP_MENU_V5_ITEM_ACTION &&
           item->action != COMP_MENU_V5_ACTION_NONE;
}
