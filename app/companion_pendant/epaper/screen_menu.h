#ifndef COMPANION_EPAPER_SCREEN_MENU_H
#define COMPANION_EPAPER_SCREEN_MENU_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "touch_gesture.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    COMP_SCREEN_MENU_VIEW_HOME = 0u,
    COMP_SCREEN_MENU_VIEW_RECORD = 1u,
    COMP_SCREEN_MENU_VIEW_STATUS = 2u,
    COMP_SCREEN_MENU_VIEW_PHONE = 3u,
    COMP_SCREEN_MENU_VIEW_DEVICE = 4u,
    COMP_SCREEN_MENU_VIEW_PREFERENCES = 5u,
    COMP_SCREEN_MENU_VIEW_ABOUT = 6u,
} comp_screen_menu_view_t;

typedef enum {
    COMP_SCREEN_MENU_LANGUAGE_EN = 0u,
    COMP_SCREEN_MENU_LANGUAGE_ZH = 1u,
} comp_screen_menu_language_t;

typedef enum {
    COMP_SCREEN_MENU_ACTION_NONE = 0u,
    COMP_SCREEN_MENU_ACTION_RECORD_START = 1u,
    COMP_SCREEN_MENU_ACTION_RECORD_STOP = 2u,
    COMP_SCREEN_MENU_ACTION_LANGUAGE_CHANGED = 3u,
} comp_screen_menu_action_t;

enum {
    COMP_SCREEN_MENU_FLAG_RECORDING = 1u << 0,
    COMP_SCREEN_MENU_FLAG_TOUCH_OK = 1u << 1,
    COMP_SCREEN_MENU_FLAG_BLE_CONNECTED = 1u << 2,
    COMP_SCREEN_MENU_FLAG_PRESS_ACTIVE = 1u << 3,
    COMP_SCREEN_MENU_FLAG_PRESS_ITEM_SHIFT = 4u,
    COMP_SCREEN_MENU_FLAG_PRESS_ITEM_MASK = 7u << COMP_SCREEN_MENU_FLAG_PRESS_ITEM_SHIFT,
};

#define COMP_SCREEN_MENU_ITEM_COUNT 6u
#define COMP_SCREEN_MENU_VISIBLE_ITEMS 4u
#define COMP_SCREEN_MENU_BACK_EDGE_MAX_X 48u
/* Daily taps and strokes belong to the pet. A deliberate three-second hold anywhere
 * becomes navigation; precise taps and strokes keep driving pet expression
 * reactions without teaching the user a narrow hit target. */
#define COMP_SCREEN_MENU_ENTER_CENTER_MIN_X 40u
#define COMP_SCREEN_MENU_ENTER_CENTER_MAX_X 160u
#define COMP_SCREEN_MENU_ENTER_CENTER_MIN_Y 40u
#define COMP_SCREEN_MENU_ENTER_CENTER_MAX_Y 160u
#define COMP_SCREEN_MENU_HEADER_HEIGHT_PX 30u
#define COMP_SCREEN_MENU_HOME_CONTENT_TOP_PX 38u
#define COMP_SCREEN_MENU_HOME_PET_PANEL_HEIGHT_PX 48u
#define COMP_SCREEN_MENU_HOME_ITEM_STEP_PX 34u
#define COMP_SCREEN_MENU_SCROLL_QUANTUM_PX 2u
#define COMP_SCREEN_MENU_SCROLL_MAX_PX 84u
#define COMP_SCREEN_MENU_SCROLL_FRAME_COUNT \
    (((COMP_SCREEN_MENU_SCROLL_MAX_PX + COMP_SCREEN_MENU_SCROLL_QUANTUM_PX - 1u) / \
      COMP_SCREEN_MENU_SCROLL_QUANTUM_PX) + 1u)

typedef struct {
    comp_screen_menu_view_t view;
    comp_screen_menu_language_t language;
    uint16_t home_scroll_offset_px;
    uint8_t home_page;
    uint8_t flags;
    uint32_t revision;
} comp_screen_menu_t;

typedef struct {
    bool changed;
    comp_screen_menu_action_t action;
    comp_screen_menu_view_t view;
    comp_screen_menu_language_t language;
    uint8_t home_page;
    uint8_t flags;
    uint32_t revision;
} comp_screen_menu_result_t;

void comp_screen_menu_init(comp_screen_menu_t *menu);
void comp_screen_menu_set_flags(comp_screen_menu_t *menu, uint8_t flags);
uint8_t comp_screen_menu_with_ble_flag(uint8_t flags, bool connected);
bool comp_screen_menu_is_daily_entry_gesture(
    const comp_touch_gesture_event_t *gesture);
comp_screen_menu_result_t comp_screen_menu_tap(comp_screen_menu_t *menu,
                                               uint16_t x,
                                               uint16_t y);
comp_screen_menu_result_t comp_screen_menu_gesture(
    comp_screen_menu_t *menu,
    const comp_touch_gesture_event_t *gesture);
comp_screen_menu_result_t comp_screen_menu_drag(comp_screen_menu_t *menu,
                                                int16_t finger_delta_y);
comp_screen_menu_result_t comp_screen_menu_drag_to(comp_screen_menu_t *menu,
                                                   int32_t home_scroll_offset_px);
bool comp_screen_menu_home_hit_test(const comp_screen_menu_t *menu,
                                    uint16_t x,
                                    uint16_t y,
                                    uint8_t *item,
                                    comp_screen_menu_view_t *view);
uint16_t comp_screen_menu_scroll_offset_px(uint8_t home_page);
uint16_t comp_screen_menu_exact_scroll_offset_px(const comp_screen_menu_t *menu);
bool comp_screen_menu_render(comp_screen_menu_view_t view,
                             comp_screen_menu_language_t language,
                             uint8_t home_page,
                             uint8_t flags,
                             uint8_t *frame,
                             size_t frame_bytes,
                             uint16_t width,
                             uint16_t height);
bool comp_screen_menu_asset_name(comp_screen_menu_view_t view,
                                 comp_screen_menu_language_t language,
                                 uint8_t home_page,
                                 char *destination,
                                 size_t destination_size);
bool comp_screen_menu_render_dynamic(comp_screen_menu_view_t view,
                                     uint8_t flags,
                                     uint8_t home_page,
                                     uint8_t *frame,
                                     size_t frame_bytes,
                                     uint16_t width,
                                     uint16_t height);
bool comp_screen_menu_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_SCREEN_MENU_H */
