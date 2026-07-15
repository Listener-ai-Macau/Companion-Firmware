#include "menu_v5_contract.h"

#include <stdio.h>

static int fail(const char *message)
{
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

static int expect_item(comp_menu_v5_root_t root,
                       uint8_t index,
                       comp_menu_v5_item_id_t expected_id,
                       comp_menu_v5_item_kind_t expected_kind,
                       const comp_menu_v5_context_t *context)
{
    comp_menu_v5_item_t item;
    if (!comp_menu_v5_resolve_item(root, index, context, &item) ||
        item.item_id != expected_id || item.kind != expected_kind) {
        return fail("menu-v5 item contract drifted");
    }
    return 0;
}

int main(void)
{
    const comp_menu_v5_context_t ready = {
        .panel_healthy = true,
        .touch_ready = true,
        .ble_connected = true,
        .battery_supported = true,
        .external_assets_ready = true,
        .record_history_available = true,
        .wake_word_available = false,
        .diagnostics_available = true,
    };
    comp_menu_v5_context_t recording = ready;
    comp_menu_v5_item_t item;
    comp_menu_v5_text_key_t root_key;
    uint8_t total = 0u;

    if (COMP_MENU_V5_ROOT_COUNT != 4u ||
        comp_menu_v5_root_item_count(COMP_MENU_V5_ROOT_VOICE) != 3u ||
        comp_menu_v5_root_item_count(COMP_MENU_V5_ROOT_DEVICE) != 4u ||
        comp_menu_v5_root_item_count(COMP_MENU_V5_ROOT_CONNECTION) != 3u ||
        comp_menu_v5_root_item_count(COMP_MENU_V5_ROOT_PREFERENCES) != 5u ||
        comp_menu_v5_root_item_count((comp_menu_v5_root_t)4u) != 0u) {
        return fail("four-root menu count");
    }
    for (uint8_t root = 0u; root < COMP_MENU_V5_ROOT_COUNT; ++root) {
        total = (uint8_t)(total + comp_menu_v5_root_item_count((comp_menu_v5_root_t)root));
        if (!comp_menu_v5_root_text_key((comp_menu_v5_root_t)root, &root_key) ||
            root_key != (comp_menu_v5_text_key_t)root) {
            return fail("four-root menu ordering");
        }
    }
    if (total != 15u) {
        return fail("four-root menu item total");
    }
    if (expect_item(COMP_MENU_V5_ROOT_VOICE, 0u, COMP_MENU_V5_ITEM_MANUAL_RECORDING,
                    COMP_MENU_V5_ITEM_ACTION, &ready) ||
        expect_item(COMP_MENU_V5_ROOT_VOICE, 1u, COMP_MENU_V5_ITEM_RECORD_HISTORY,
                    COMP_MENU_V5_ITEM_LIVE_DATA, &ready) ||
        expect_item(COMP_MENU_V5_ROOT_VOICE, 2u, COMP_MENU_V5_ITEM_WAKE_WORD,
                    COMP_MENU_V5_ITEM_DEFERRED, &ready) ||
        expect_item(COMP_MENU_V5_ROOT_DEVICE, 0u, COMP_MENU_V5_ITEM_EPAPER_STATUS,
                    COMP_MENU_V5_ITEM_LIVE_DATA, &ready) ||
        expect_item(COMP_MENU_V5_ROOT_DEVICE, 3u, COMP_MENU_V5_ITEM_UI_ASSETS,
                    COMP_MENU_V5_ITEM_LIVE_DATA, &ready) ||
        expect_item(COMP_MENU_V5_ROOT_CONNECTION, 0u, COMP_MENU_V5_ITEM_PAIR_NEW_DEVICE,
                    COMP_MENU_V5_ITEM_ACTION, &ready) ||
        expect_item(COMP_MENU_V5_ROOT_CONNECTION, 2u, COMP_MENU_V5_ITEM_RECONNECT,
                    COMP_MENU_V5_ITEM_ACTION, &ready) ||
        expect_item(COMP_MENU_V5_ROOT_PREFERENCES, 4u, COMP_MENU_V5_ITEM_ABOUT,
                    COMP_MENU_V5_ITEM_LIVE_DATA, &ready)) {
        return 1;
    }
    if (!comp_menu_v5_resolve_item(COMP_MENU_V5_ROOT_VOICE, 0u, &ready, &item) ||
        item.action != COMP_MENU_V5_ACTION_RECORD_START ||
        !comp_menu_v5_item_is_selectable(&item)) {
        return fail("record start action");
    }
    recording.recording = true;
    if (!comp_menu_v5_resolve_item(COMP_MENU_V5_ROOT_VOICE, 0u, &recording, &item) ||
        item.action != COMP_MENU_V5_ACTION_RECORD_STOP ||
        !comp_menu_v5_item_is_selectable(&item)) {
        return fail("record stop action");
    }
    if (!comp_menu_v5_resolve_item(COMP_MENU_V5_ROOT_PREFERENCES, 1u, &ready, &item) ||
        item.kind != COMP_MENU_V5_ITEM_DEFERRED || comp_menu_v5_item_is_selectable(&item) ||
        comp_menu_v5_resolve_item(COMP_MENU_V5_ROOT_PREFERENCES, 5u, &ready, &item)) {
        return fail("deferred and bounds contract");
    }
    printf("PASS: menu-v5 keeps four roots, 15 real/deferred rows, and only committed actions selectable.\n");
    return 0;
}
