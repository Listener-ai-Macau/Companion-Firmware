#include "menu_v5_navigation.h"

#include <stddef.h>

#define ROOT_GRID_CELL_WIDTH_PX (COMP_MENU_V5_NAVIGATION_WIDTH_PX / 2u)
#define ROOT_GRID_CELL_HEIGHT_PX (COMP_MENU_V5_NAVIGATION_HEIGHT_PX / 2u)
#define DETAIL_VIEWPORT_HEIGHT_PX \
    (COMP_MENU_V5_NAVIGATION_HEIGHT_PX - COMP_MENU_V5_NAVIGATION_HEADER_HEIGHT_PX)

static void result_from_navigation(const comp_menu_v5_navigation_t *navigation,
                                   comp_menu_v5_navigation_result_t *result)
{
    result->view = navigation->view;
    result->root = navigation->root;
    result->language = navigation->language;
    result->scroll_offset_px = navigation->scroll_offset_px;
    result->revision = navigation->revision;
}

static bool root_is_valid(comp_menu_v5_root_t root)
{
    return root < COMP_MENU_V5_ROOT_COUNT;
}

void comp_menu_v5_navigation_init(comp_menu_v5_navigation_t *navigation,
                                  comp_menu_v5_language_t language)
{
    if (navigation == NULL) {
        return;
    }
    *navigation = (comp_menu_v5_navigation_t){
        .view = COMP_MENU_V5_NAVIGATION_ROOTS,
        .root = COMP_MENU_V5_ROOT_VOICE,
        .language = comp_menu_v5_language_is_valid(language) ? language :
                                                           COMP_MENU_V5_LANGUAGE_EN,
        .revision = 1u,
    };
}

uint16_t comp_menu_v5_navigation_max_scroll_px(const comp_menu_v5_navigation_t *navigation)
{
    uint16_t content_height;

    if (navigation == NULL || navigation->view != COMP_MENU_V5_NAVIGATION_DETAILS ||
        !root_is_valid(navigation->root)) {
        return 0u;
    }
    content_height = (uint16_t)comp_menu_v5_root_item_count(navigation->root) *
                     COMP_MENU_V5_NAVIGATION_DETAIL_ROW_HEIGHT_PX;
    return content_height > DETAIL_VIEWPORT_HEIGHT_PX
               ? (uint16_t)(content_height - DETAIL_VIEWPORT_HEIGHT_PX)
               : 0u;
}

bool comp_menu_v5_navigation_root_hit_test(uint16_t x,
                                           uint16_t y,
                                           comp_menu_v5_root_t *out_root)
{
    uint8_t column;
    uint8_t row;
    comp_menu_v5_root_t root;

    if (x >= COMP_MENU_V5_NAVIGATION_WIDTH_PX || y >= COMP_MENU_V5_NAVIGATION_HEIGHT_PX) {
        return false;
    }
    column = (uint8_t)(x / ROOT_GRID_CELL_WIDTH_PX);
    row = (uint8_t)(y / ROOT_GRID_CELL_HEIGHT_PX);
    root = (comp_menu_v5_root_t)(row * 2u + column);
    if (!root_is_valid(root)) {
        return false;
    }
    if (out_root != NULL) {
        *out_root = root;
    }
    return true;
}

bool comp_menu_v5_navigation_detail_hit_test(
    const comp_menu_v5_navigation_t *navigation,
    uint16_t x,
    uint16_t y,
    const comp_menu_v5_context_t *context,
    uint8_t *out_index,
    comp_menu_v5_item_t *out_item)
{
    uint16_t content_y;
    uint8_t index;
    comp_menu_v5_item_t ignored_item;

    if (navigation == NULL || navigation->view != COMP_MENU_V5_NAVIGATION_DETAILS ||
        x >= COMP_MENU_V5_NAVIGATION_WIDTH_PX ||
        y < COMP_MENU_V5_NAVIGATION_HEADER_HEIGHT_PX ||
        y >= COMP_MENU_V5_NAVIGATION_HEIGHT_PX) {
        return false;
    }
    content_y = (uint16_t)(y - COMP_MENU_V5_NAVIGATION_HEADER_HEIGHT_PX) +
                navigation->scroll_offset_px;
    index = (uint8_t)(content_y / COMP_MENU_V5_NAVIGATION_DETAIL_ROW_HEIGHT_PX);
    if (index >= comp_menu_v5_root_item_count(navigation->root) ||
        !comp_menu_v5_resolve_item(navigation->root, index, context,
                                   out_item != NULL ? out_item : &ignored_item)) {
        return false;
    }
    if (out_index != NULL) {
        *out_index = index;
    }
    return true;
}

comp_menu_v5_navigation_result_t comp_menu_v5_navigation_back(
    comp_menu_v5_navigation_t *navigation)
{
    comp_menu_v5_navigation_result_t result = {0};

    if (navigation == NULL) {
        return result;
    }
    if (navigation->view == COMP_MENU_V5_NAVIGATION_DETAILS) {
        navigation->view = COMP_MENU_V5_NAVIGATION_ROOTS;
        navigation->scroll_offset_px = 0u;
        navigation->revision++;
        result.changed = true;
        result.event = COMP_MENU_V5_NAVIGATION_EVENT_ROOT_CLOSED;
    }
    result_from_navigation(navigation, &result);
    return result;
}

comp_menu_v5_navigation_result_t comp_menu_v5_navigation_tap(
    comp_menu_v5_navigation_t *navigation,
    uint16_t x,
    uint16_t y,
    const comp_menu_v5_context_t *context)
{
    comp_menu_v5_navigation_result_t result = {0};
    comp_menu_v5_root_t root;
    uint8_t index;
    comp_menu_v5_item_t item;

    if (navigation == NULL) {
        return result;
    }
    if (navigation->view == COMP_MENU_V5_NAVIGATION_ROOTS) {
        if (comp_menu_v5_navigation_root_hit_test(x, y, &root)) {
            navigation->view = COMP_MENU_V5_NAVIGATION_DETAILS;
            navigation->root = root;
            navigation->scroll_offset_px = 0u;
            navigation->revision++;
            result.changed = true;
            result.event = COMP_MENU_V5_NAVIGATION_EVENT_ROOT_OPENED;
        }
    } else if (y < COMP_MENU_V5_NAVIGATION_HEADER_HEIGHT_PX) {
        return comp_menu_v5_navigation_back(navigation);
    } else if (comp_menu_v5_navigation_detail_hit_test(navigation, x, y, context, &index, &item) &&
               comp_menu_v5_prepare_selection(navigation->root, index, context,
                                              navigation->language, &result.selection)) {
        (void)item;
        result.has_selection = true;
        result.event = COMP_MENU_V5_NAVIGATION_EVENT_ITEM_SELECTED;
        if (result.selection.language_changed) {
            navigation->language = result.selection.language_after;
        }
        navigation->revision++;
        result.changed = true;
    }
    result_from_navigation(navigation, &result);
    return result;
}

comp_menu_v5_navigation_result_t comp_menu_v5_navigation_drag_to(
    comp_menu_v5_navigation_t *navigation,
    int32_t scroll_offset_px)
{
    comp_menu_v5_navigation_result_t result = {0};
    uint16_t max_scroll;

    if (navigation == NULL) {
        return result;
    }
    max_scroll = comp_menu_v5_navigation_max_scroll_px(navigation);
    if (scroll_offset_px < 0) {
        scroll_offset_px = 0;
    } else if (scroll_offset_px > (int32_t)max_scroll) {
        scroll_offset_px = max_scroll;
    }
    if (navigation->view == COMP_MENU_V5_NAVIGATION_DETAILS &&
        navigation->scroll_offset_px != (uint16_t)scroll_offset_px) {
        navigation->scroll_offset_px = (uint16_t)scroll_offset_px;
        navigation->revision++;
        result.changed = true;
    }
    result_from_navigation(navigation, &result);
    return result;
}

comp_menu_v5_navigation_result_t comp_menu_v5_navigation_drag(
    comp_menu_v5_navigation_t *navigation,
    int16_t finger_delta_y)
{
    if (navigation == NULL) {
        comp_menu_v5_navigation_result_t result = {0};
        return result;
    }
    return comp_menu_v5_navigation_drag_to(
        navigation, (int32_t)navigation->scroll_offset_px - finger_delta_y);
}

bool comp_menu_v5_navigation_self_test(void)
{
    const comp_menu_v5_context_t context = {0};
    comp_menu_v5_navigation_t navigation;
    comp_menu_v5_navigation_result_t result;
    comp_menu_v5_item_t item;
    uint8_t index;

    comp_menu_v5_navigation_init(&navigation, COMP_MENU_V5_LANGUAGE_EN);
    if (navigation.view != COMP_MENU_V5_NAVIGATION_ROOTS || navigation.revision != 1u ||
        !comp_menu_v5_navigation_root_hit_test(150u, 150u, &navigation.root) ||
        navigation.root != COMP_MENU_V5_ROOT_PREFERENCES) {
        return false;
    }
    result = comp_menu_v5_navigation_tap(&navigation, 150u, 150u, &context);
    if (!result.changed || result.event != COMP_MENU_V5_NAVIGATION_EVENT_ROOT_OPENED ||
        navigation.view != COMP_MENU_V5_NAVIGATION_DETAILS ||
        navigation.root != COMP_MENU_V5_ROOT_PREFERENCES ||
        comp_menu_v5_navigation_max_scroll_px(&navigation) != 42u) {
        return false;
    }
    result = comp_menu_v5_navigation_drag(&navigation, -31);
    if (!result.changed || navigation.scroll_offset_px != 31u ||
        !comp_menu_v5_navigation_detail_hit_test(&navigation, 100u, 100u, &context,
                                                  &index, &item) ||
        index != 2u || item.item_id != COMP_MENU_V5_ITEM_REFRESH_POLICY) {
        return false;
    }
    result = comp_menu_v5_navigation_back(&navigation);
    return result.changed && result.event == COMP_MENU_V5_NAVIGATION_EVENT_ROOT_CLOSED &&
           navigation.view == COMP_MENU_V5_NAVIGATION_ROOTS &&
           navigation.scroll_offset_px == 0u;
}
