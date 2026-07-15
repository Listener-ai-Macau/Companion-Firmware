#ifndef COMPANION_EPAPER_MENU_V5_NAVIGATION_H
#define COMPANION_EPAPER_MENU_V5_NAVIGATION_H

#include <stdbool.h>
#include <stdint.h>

#include "menu_v5_action_journey.h"

#ifdef __cplusplus
extern "C" {
#endif

/* The navigation geometry is portable. A target renderer may use a separately
 * approved external-Flash visual source, but must preserve these hit and
 * scroll semantics. */
#define COMP_MENU_V5_NAVIGATION_WIDTH_PX 200u
#define COMP_MENU_V5_NAVIGATION_HEIGHT_PX 200u
#define COMP_MENU_V5_NAVIGATION_ROOT_HEADER_HEIGHT_PX 40u
#define COMP_MENU_V5_NAVIGATION_ROOT_ROW_HEIGHT_PX 40u
#define COMP_MENU_V5_NAVIGATION_HEADER_HEIGHT_PX 40u
#define COMP_MENU_V5_NAVIGATION_DETAIL_ROW_HEIGHT_PX 36u

typedef enum {
    COMP_MENU_V5_NAVIGATION_ROOTS = 0u,
    COMP_MENU_V5_NAVIGATION_DETAILS,
} comp_menu_v5_navigation_view_t;

typedef enum {
    COMP_MENU_V5_NAVIGATION_EVENT_NONE = 0u,
    COMP_MENU_V5_NAVIGATION_EVENT_ROOT_OPENED,
    COMP_MENU_V5_NAVIGATION_EVENT_ROOT_CLOSED,
    COMP_MENU_V5_NAVIGATION_EVENT_ITEM_SELECTED,
} comp_menu_v5_navigation_event_t;

typedef struct {
    comp_menu_v5_navigation_view_t view;
    comp_menu_v5_root_t root;
    comp_menu_v5_language_t language;
    uint16_t scroll_offset_px;
    uint32_t revision;
} comp_menu_v5_navigation_t;

typedef struct {
    bool changed;
    bool has_selection;
    comp_menu_v5_navigation_event_t event;
    comp_menu_v5_navigation_view_t view;
    comp_menu_v5_root_t root;
    comp_menu_v5_language_t language;
    uint16_t scroll_offset_px;
    uint32_t revision;
    comp_menu_v5_selection_result_t selection;
} comp_menu_v5_navigation_result_t;

void comp_menu_v5_navigation_init(comp_menu_v5_navigation_t *navigation,
                                  comp_menu_v5_language_t language);
uint16_t comp_menu_v5_navigation_max_scroll_px(const comp_menu_v5_navigation_t *navigation);
bool comp_menu_v5_navigation_root_hit_test(uint16_t x,
                                           uint16_t y,
                                           comp_menu_v5_root_t *out_root);
bool comp_menu_v5_navigation_detail_hit_test(
    const comp_menu_v5_navigation_t *navigation,
    uint16_t x,
    uint16_t y,
    const comp_menu_v5_context_t *context,
    uint8_t *out_index,
    comp_menu_v5_item_t *out_item);
comp_menu_v5_navigation_result_t comp_menu_v5_navigation_tap(
    comp_menu_v5_navigation_t *navigation,
    uint16_t x,
    uint16_t y,
    const comp_menu_v5_context_t *context);
comp_menu_v5_navigation_result_t comp_menu_v5_navigation_drag(
    comp_menu_v5_navigation_t *navigation,
    int16_t finger_delta_y);
comp_menu_v5_navigation_result_t comp_menu_v5_navigation_drag_to(
    comp_menu_v5_navigation_t *navigation,
    int32_t scroll_offset_px);
comp_menu_v5_navigation_result_t comp_menu_v5_navigation_back(
    comp_menu_v5_navigation_t *navigation);
bool comp_menu_v5_navigation_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_MENU_V5_NAVIGATION_H */
