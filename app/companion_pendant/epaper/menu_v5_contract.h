#ifndef COMPANION_EPAPER_MENU_V5_CONTRACT_H
#define COMPANION_EPAPER_MENU_V5_CONTRACT_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* This is a portable information-architecture contract, not a renderer or an
 * asset selector. The generated v5 reference remains owner-gated. */
typedef enum {
    COMP_MENU_V5_ROOT_VOICE = 0u,
    COMP_MENU_V5_ROOT_DEVICE = 1u,
    COMP_MENU_V5_ROOT_CONNECTION = 2u,
    COMP_MENU_V5_ROOT_PREFERENCES = 3u,
    COMP_MENU_V5_ROOT_COUNT = 4u,
} comp_menu_v5_root_t;

typedef enum {
    COMP_MENU_V5_ITEM_MANUAL_RECORDING = 0u,
    COMP_MENU_V5_ITEM_RECORD_HISTORY,
    COMP_MENU_V5_ITEM_WAKE_WORD,
    COMP_MENU_V5_ITEM_EPAPER_STATUS,
    COMP_MENU_V5_ITEM_TOUCH_STATUS,
    COMP_MENU_V5_ITEM_BATTERY_STATUS,
    COMP_MENU_V5_ITEM_UI_ASSETS,
    COMP_MENU_V5_ITEM_PAIR_NEW_DEVICE,
    COMP_MENU_V5_ITEM_LINK_STATUS,
    COMP_MENU_V5_ITEM_RECONNECT,
    COMP_MENU_V5_ITEM_LANGUAGE,
    COMP_MENU_V5_ITEM_GESTURE_POLICY,
    COMP_MENU_V5_ITEM_REFRESH_POLICY,
    COMP_MENU_V5_ITEM_DIAGNOSTICS,
    COMP_MENU_V5_ITEM_ABOUT,
} comp_menu_v5_item_id_t;

typedef enum {
    COMP_MENU_V5_TEXT_VOICE = 0u,
    COMP_MENU_V5_TEXT_DEVICE,
    COMP_MENU_V5_TEXT_CONNECTION,
    COMP_MENU_V5_TEXT_PREFERENCES,
    COMP_MENU_V5_TEXT_MANUAL_RECORDING,
    COMP_MENU_V5_TEXT_RECORD_HISTORY,
    COMP_MENU_V5_TEXT_WAKE_WORD,
    COMP_MENU_V5_TEXT_EPAPER,
    COMP_MENU_V5_TEXT_TOUCH,
    COMP_MENU_V5_TEXT_BATTERY,
    COMP_MENU_V5_TEXT_UI_ASSETS,
    COMP_MENU_V5_TEXT_PAIR_NEW_DEVICE,
    COMP_MENU_V5_TEXT_LINK_STATUS,
    COMP_MENU_V5_TEXT_RECONNECT,
    COMP_MENU_V5_TEXT_LANGUAGE,
    COMP_MENU_V5_TEXT_GESTURE,
    COMP_MENU_V5_TEXT_REFRESH,
    COMP_MENU_V5_TEXT_DIAGNOSTICS,
    COMP_MENU_V5_TEXT_ABOUT,
} comp_menu_v5_text_key_t;

typedef enum {
    COMP_MENU_V5_ITEM_ACTION = 0u,
    COMP_MENU_V5_ITEM_LIVE_DATA,
    COMP_MENU_V5_ITEM_DEFERRED,
    COMP_MENU_V5_ITEM_PLANNED,
} comp_menu_v5_item_kind_t;

typedef enum {
    COMP_MENU_V5_ACTION_NONE = 0u,
    COMP_MENU_V5_ACTION_RECORD_START,
    COMP_MENU_V5_ACTION_RECORD_STOP,
    COMP_MENU_V5_ACTION_PAIR_NEW_DEVICE,
    COMP_MENU_V5_ACTION_RECONNECT,
    COMP_MENU_V5_ACTION_LANGUAGE,
} comp_menu_v5_action_t;

typedef struct {
    bool recording;
    bool panel_healthy;
    bool touch_ready;
    bool ble_connected;
    bool battery_supported;
    bool external_assets_ready;
    bool record_history_available;
    bool wake_word_available;
    bool diagnostics_available;
} comp_menu_v5_context_t;

typedef struct {
    comp_menu_v5_root_t root;
    comp_menu_v5_item_id_t item_id;
    comp_menu_v5_text_key_t text_key;
    comp_menu_v5_item_kind_t kind;
    comp_menu_v5_action_t action;
    bool has_live_value;
    bool live_value;
} comp_menu_v5_item_t;

uint8_t comp_menu_v5_root_item_count(comp_menu_v5_root_t root);
bool comp_menu_v5_root_text_key(comp_menu_v5_root_t root, comp_menu_v5_text_key_t *out_key);
bool comp_menu_v5_resolve_item(comp_menu_v5_root_t root,
                               uint8_t index,
                               const comp_menu_v5_context_t *context,
                               comp_menu_v5_item_t *out_item);
bool comp_menu_v5_item_is_selectable(const comp_menu_v5_item_t *item);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_MENU_V5_CONTRACT_H */
