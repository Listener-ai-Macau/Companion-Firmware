#include "screen_menu.h"

#include "screen_framebuffer.h"

#include <stdio.h>
#include <string.h>

#define MENU_WIDTH 200u
#define MENU_HEIGHT 200u
#define MENU_FRAME_BYTES ((MENU_WIDTH / 8u) * MENU_HEIGHT)
#define MENU_HEADER_HEIGHT COMP_SCREEN_MENU_HEADER_HEIGHT_PX
#define MENU_HOME_CONTENT_TOP COMP_SCREEN_MENU_HOME_CONTENT_TOP_PX
#define MENU_HOME_PET_PANEL_HEIGHT COMP_SCREEN_MENU_HOME_PET_PANEL_HEIGHT_PX
#define MENU_HOME_ITEM_STEP COMP_SCREEN_MENU_HOME_ITEM_STEP_PX
#define MENU_HOME_SCROLLBAR_TOP (MENU_HOME_CONTENT_TOP + 1u)
#define MENU_HOME_SCROLLBAR_BOTTOM (MENU_HEIGHT - 5u)
#define MENU_HOME_SCROLLBAR_THUMB_HEIGHT 36u
#define MENU_HOME_SCROLLBAR_TRAVEL \
    (MENU_HOME_SCROLLBAR_BOTTOM - MENU_HOME_SCROLLBAR_TOP - \
     MENU_HOME_SCROLLBAR_THUMB_HEIGHT + 1u)

static const comp_screen_menu_view_t s_home_views[COMP_SCREEN_MENU_ITEM_COUNT] = {
    COMP_SCREEN_MENU_VIEW_RECORD,
    COMP_SCREEN_MENU_VIEW_STATUS,
    COMP_SCREEN_MENU_VIEW_PHONE,
    COMP_SCREEN_MENU_VIEW_DEVICE,
    COMP_SCREEN_MENU_VIEW_PREFERENCES,
    COMP_SCREEN_MENU_VIEW_ABOUT,
};

uint16_t comp_screen_menu_scroll_offset_px(uint8_t home_page)
{
    uint16_t offset = (uint16_t)home_page * COMP_SCREEN_MENU_SCROLL_QUANTUM_PX;
    return offset > COMP_SCREEN_MENU_SCROLL_MAX_PX
               ? COMP_SCREEN_MENU_SCROLL_MAX_PX
               : offset;
}

static uint8_t home_scroll_frame_from_offset(int32_t offset_px)
{
    if (offset_px <= 0) {
        return 0u;
    }
    if (offset_px >= (int32_t)COMP_SCREEN_MENU_SCROLL_MAX_PX) {
        return COMP_SCREEN_MENU_SCROLL_FRAME_COUNT - 1u;
    }
    return (uint8_t)((offset_px + COMP_SCREEN_MENU_SCROLL_QUANTUM_PX / 2u) /
                     COMP_SCREEN_MENU_SCROLL_QUANTUM_PX);
}

uint16_t comp_screen_menu_exact_scroll_offset_px(const comp_screen_menu_t *menu)
{
    return menu != NULL ? menu->home_scroll_offset_px : 0u;
}

bool comp_screen_menu_home_hit_test(const comp_screen_menu_t *menu,
                                    uint16_t x,
                                    uint16_t y,
                                    uint8_t *item,
                                    comp_screen_menu_view_t *view)
{
    uint16_t content_y;
    uint8_t hit;

    if (menu == NULL || menu->view != COMP_SCREEN_MENU_VIEW_HOME ||
        x < 4u || x >= 196u || y < MENU_HOME_CONTENT_TOP || y >= MENU_HEIGHT) {
        return false;
    }
    content_y = (uint16_t)(y - MENU_HOME_CONTENT_TOP) +
                menu->home_scroll_offset_px;
    /* The accepted v3 source has no separate home pet panel. Row separators
     * remain visual only, preserving a contiguous touch target. */
    hit = (uint8_t)(content_y / MENU_HOME_ITEM_STEP);
    if (hit >= COMP_SCREEN_MENU_ITEM_COUNT) {
        return false;
    }
    if (item != NULL) {
        *item = hit;
    }
    if (view != NULL) {
        *view = s_home_views[hit];
    }
    return true;
}

static void menu_result_from_state(const comp_screen_menu_t *menu,
                                   comp_screen_menu_result_t *result)
{
    result->view = menu->view;
    result->language = menu->language;
    result->home_page = menu->home_page;
    result->flags = menu->flags;
    result->revision = menu->revision;
}

void comp_screen_menu_init(comp_screen_menu_t *menu)
{
    if (menu != NULL) {
        *menu = (comp_screen_menu_t){
            .view = COMP_SCREEN_MENU_VIEW_HOME,
            .language = COMP_SCREEN_MENU_LANGUAGE_ZH,
            .revision = 1u,
        };
    }
}

void comp_screen_menu_set_flags(comp_screen_menu_t *menu, uint8_t flags)
{
    if (menu != NULL && menu->flags != flags) {
        menu->flags = flags;
        menu->revision++;
    }
}

void comp_screen_menu_set_phone_reconnect_state(
    comp_screen_menu_t *menu,
    comp_screen_menu_phone_reconnect_state_t state)
{
    if (menu != NULL && menu->view == COMP_SCREEN_MENU_VIEW_PHONE) {
        menu->home_page = (uint8_t)state;
    }
}

uint8_t comp_screen_menu_with_ble_flag(uint8_t flags, bool connected)
{
    flags &= (uint8_t)~COMP_SCREEN_MENU_FLAG_BLE_CONNECTED;
    if (connected) {
        flags |= COMP_SCREEN_MENU_FLAG_BLE_CONNECTED;
    }
    return flags;
}

bool comp_screen_menu_is_daily_entry_gesture(
    const comp_touch_gesture_event_t *gesture)
{
    /* three-second hold anywhere enters the product menu; precise taps and
     * directional strokes remain pet interactions. */
    return gesture != NULL &&
           gesture->type == COMP_TOUCH_GESTURE_LONG_PRESS;
}

bool comp_screen_menu_is_exit_gesture(
    const comp_touch_gesture_event_t *gesture)
{
    /* The gesture layer already direction-locks and debounces this event.
     * Do not turn exit into a hidden edge affordance in a board target. */
    return gesture != NULL &&
           gesture->type == COMP_TOUCH_GESTURE_SWIPE_RIGHT;
}

comp_screen_menu_result_t comp_screen_menu_tap(comp_screen_menu_t *menu,
                                               uint16_t x,
                                               uint16_t y)
{
    comp_screen_menu_result_t result = {0};
    comp_screen_menu_view_t hit_view;

    if (menu == NULL) {
        return result;
    }
    if (x >= MENU_WIDTH || y >= MENU_HEIGHT) {
        menu_result_from_state(menu, &result);
        return result;
    }
    if (menu->view != COMP_SCREEN_MENU_VIEW_HOME && y < 34u) {
        menu->view = COMP_SCREEN_MENU_VIEW_HOME;
        menu->home_page = 0u;
        menu->revision++;
        result.changed = true;
    } else if (comp_screen_menu_home_hit_test(menu, x, y, NULL, &hit_view)) {
        menu->view = hit_view;
        menu->revision++;
        result.changed = true;
    } else if (menu->view == COMP_SCREEN_MENU_VIEW_RECORD &&
               x >= 25u && x < 175u && y >= 88u && y < 154u) {
        if ((menu->flags & COMP_SCREEN_MENU_FLAG_RECORDING) != 0u) {
            menu->flags &= (uint8_t)~COMP_SCREEN_MENU_FLAG_RECORDING;
            result.action = COMP_SCREEN_MENU_ACTION_RECORD_STOP;
        } else {
            menu->flags |= COMP_SCREEN_MENU_FLAG_RECORDING;
            result.action = COMP_SCREEN_MENU_ACTION_RECORD_START;
        }
        menu->revision++;
        result.changed = true;
    } else if (menu->view == COMP_SCREEN_MENU_VIEW_PREFERENCES &&
               x >= 12u && x < 188u && y >= 43u && y < 87u) {
        menu->language = menu->language == COMP_SCREEN_MENU_LANGUAGE_ZH
                             ? COMP_SCREEN_MENU_LANGUAGE_EN
                             : COMP_SCREEN_MENU_LANGUAGE_ZH;
        menu->revision++;
        result.action = COMP_SCREEN_MENU_ACTION_LANGUAGE_CHANGED;
        result.changed = true;
    } else if (menu->view == COMP_SCREEN_MENU_VIEW_PHONE &&
               x >= 12u && x < 188u && y >= 140u && y < 184u) {
        menu->revision++;
        result.action = COMP_SCREEN_MENU_ACTION_PHONE_RECONNECT;
        result.changed = true;
    }
    menu_result_from_state(menu, &result);
    return result;
}

comp_screen_menu_result_t comp_screen_menu_gesture(
    comp_screen_menu_t *menu,
    const comp_touch_gesture_event_t *gesture)
{
    comp_screen_menu_result_t result = {0};

    if (menu == NULL || gesture == NULL) {
        return result;
    }
    if (comp_screen_menu_is_exit_gesture(gesture)) {
        /* This layer has no daily-surface state. The target consumes the
         * explicit action and performs its single clean transition there. */
        result.action = COMP_SCREEN_MENU_ACTION_EXIT_DAILY;
        result.changed = true;
    }
    menu_result_from_state(menu, &result);
    return result;
}

comp_screen_menu_result_t comp_screen_menu_drag(comp_screen_menu_t *menu,
                                                int16_t finger_delta_y)
{
    int32_t offset;

    if (menu == NULL) {
        comp_screen_menu_result_t result = {0};
        return result;
    }
    offset = (int32_t)menu->home_scroll_offset_px - finger_delta_y;
    return comp_screen_menu_drag_to(menu, offset);
}

comp_screen_menu_result_t comp_screen_menu_drag_to(
    comp_screen_menu_t *menu,
    int32_t home_scroll_offset_px)
{
    comp_screen_menu_result_t result = {0};

    if (menu == NULL) {
        return result;
    }
    if (menu->view == COMP_SCREEN_MENU_VIEW_HOME) {
        if (home_scroll_offset_px < 0) {
            home_scroll_offset_px = 0;
        } else if (home_scroll_offset_px >
                   (int32_t)COMP_SCREEN_MENU_SCROLL_MAX_PX) {
            home_scroll_offset_px = COMP_SCREEN_MENU_SCROLL_MAX_PX;
        }
        if ((uint16_t)home_scroll_offset_px != menu->home_scroll_offset_px) {
            menu->home_scroll_offset_px = (uint16_t)home_scroll_offset_px;
            menu->home_page = home_scroll_frame_from_offset(home_scroll_offset_px);
            menu->revision++;
            result.changed = true;
        }
    }
    menu_result_from_state(menu, &result);
    return result;
}

static void draw_centered_text(comp_screen_framebuffer_t *framebuffer,
                               int16_t y,
                               const char *text,
                               uint8_t scale,
                               bool black)
{
    uint16_t width = comp_screen_framebuffer_text_width(text, scale);
    int16_t x = (int16_t)(((int16_t)framebuffer->width - (int16_t)width) / 2);
    comp_screen_framebuffer_draw_text(framebuffer, x, y, text, scale, black);
}

static void draw_header(comp_screen_framebuffer_t *framebuffer,
                        const char *title,
                        bool show_back)
{
    comp_screen_framebuffer_fill_rect(framebuffer, 0, 0, MENU_WIDTH,
                                      MENU_HEADER_HEIGHT, true);
    if (show_back) {
        comp_screen_framebuffer_draw_line(framebuffer, 18, 9, 9, 16, false);
        comp_screen_framebuffer_draw_line(framebuffer, 9, 16, 18, 23, false);
        comp_screen_framebuffer_draw_line(framebuffer, 9, 16, 25, 16, false);
    }
    draw_centered_text(framebuffer, 9, title, 2u, false);
}

static void draw_header_pet_chip(comp_screen_framebuffer_t *framebuffer)
{
    comp_screen_framebuffer_stroke_rect(framebuffer, 5, 5, 31u, 22u, 3u, false);
    comp_screen_framebuffer_fill_rect(framebuffer, 14, 13, 5u, 6u, false);
    comp_screen_framebuffer_fill_rect(framebuffer, 24, 13, 5u, 6u, false);
    comp_screen_framebuffer_draw_line(framebuffer, 19, 22, 22, 24, false);
    comp_screen_framebuffer_draw_line(framebuffer, 22, 24, 25, 22, false);
}

static void draw_corner_spark(comp_screen_framebuffer_t *framebuffer,
                              int16_t x,
                              int16_t y,
                              bool black)
{
    comp_screen_framebuffer_draw_line(framebuffer, x, (int16_t)(y - 5), x,
                                      (int16_t)(y + 5), black);
    comp_screen_framebuffer_draw_line(framebuffer, (int16_t)(x - 5), y,
                                      (int16_t)(x + 5), y, black);
    comp_screen_framebuffer_draw_line(framebuffer, (int16_t)(x - 3),
                                      (int16_t)(y - 3), (int16_t)(x + 3),
                                      (int16_t)(y + 3), black);
    comp_screen_framebuffer_draw_line(framebuffer, (int16_t)(x + 3),
                                      (int16_t)(y - 3), (int16_t)(x - 3),
                                      (int16_t)(y + 3), black);
}

static void draw_cat_badge(comp_screen_framebuffer_t *framebuffer,
                           int16_t x,
                           int16_t y,
                           uint8_t mood)
{
    /* The physical shell owns the cat outline; screen UI draws only inner face marks. */
    if (mood == 1u) {
        comp_screen_framebuffer_fill_rect(framebuffer, x + 12, y + 17, 4u, 8u, true);
        comp_screen_framebuffer_fill_rect(framebuffer, x + 24, y + 17, 4u, 8u, true);
        comp_screen_framebuffer_draw_line(framebuffer, x + 17, y + 29, x + 23, y + 29, true);
        draw_corner_spark(framebuffer, (int16_t)(x + 32), (int16_t)(y + 13), true);
    } else if (mood == 2u) {
        comp_screen_framebuffer_stroke_rect(framebuffer, x + 11, y + 16, 7u, 8u, 2u, true);
        comp_screen_framebuffer_stroke_rect(framebuffer, x + 23, y + 16, 7u, 8u, 2u, true);
        comp_screen_framebuffer_fill_rect(framebuffer, x + 18, y + 28, 5u, 3u, true);
    } else {
        comp_screen_framebuffer_draw_line(framebuffer, x + 11, y + 20, x + 16, y + 18, true);
        comp_screen_framebuffer_draw_line(framebuffer, x + 24, y + 18, x + 29, y + 20, true);
        comp_screen_framebuffer_draw_line(framebuffer, x + 20, y + 27, x + 16, y + 30, true);
        comp_screen_framebuffer_draw_line(framebuffer, x + 20, y + 27, x + 24, y + 30, true);
    }
}

static void draw_microphone_icon(comp_screen_framebuffer_t *framebuffer,
                                 int16_t x,
                                 int16_t y)
{
    comp_screen_framebuffer_stroke_rect(framebuffer, x + 7, y, 10u, 20u, 2u, true);
    comp_screen_framebuffer_draw_line(framebuffer, x + 3, y + 12, x + 3, y + 18, true);
    comp_screen_framebuffer_draw_line(framebuffer, x + 3, y + 18, x + 8, y + 23, true);
    comp_screen_framebuffer_draw_line(framebuffer, x + 8, y + 23, x + 16, y + 23, true);
    comp_screen_framebuffer_draw_line(framebuffer, x + 16, y + 23, x + 21, y + 18, true);
    comp_screen_framebuffer_draw_line(framebuffer, x + 21, y + 18, x + 21, y + 12, true);
    comp_screen_framebuffer_fill_rect(framebuffer, x + 11, y + 23, 2u, 5u, true);
    comp_screen_framebuffer_fill_rect(framebuffer, x + 6, y + 28, 12u, 2u, true);
}

static void draw_status_icon(comp_screen_framebuffer_t *framebuffer,
                             int16_t x,
                             int16_t y)
{
    comp_screen_framebuffer_stroke_rect(framebuffer, x, y, 28u, 28u, 2u, true);
    comp_screen_framebuffer_fill_rect(framebuffer, x + 6, y + 17, 3u, 6u, true);
    comp_screen_framebuffer_fill_rect(framebuffer, x + 13, y + 11, 3u, 12u, true);
    comp_screen_framebuffer_fill_rect(framebuffer, x + 20, y + 7, 3u, 16u, true);
}

static void draw_settings_icon(comp_screen_framebuffer_t *framebuffer,
                               int16_t x,
                               int16_t y)
{
    comp_screen_framebuffer_stroke_rect(framebuffer, x + 5, y + 5, 20u, 20u, 3u, true);
    comp_screen_framebuffer_stroke_rect(framebuffer, x + 11, y + 11, 8u, 8u, 2u, true);
    comp_screen_framebuffer_fill_rect(framebuffer, x + 12, y, 6u, 5u, true);
    comp_screen_framebuffer_fill_rect(framebuffer, x + 12, y + 25, 6u, 5u, true);
    comp_screen_framebuffer_fill_rect(framebuffer, x, y + 12, 5u, 6u, true);
    comp_screen_framebuffer_fill_rect(framebuffer, x + 25, y + 12, 5u, 6u, true);
}

static void draw_phone_icon(comp_screen_framebuffer_t *framebuffer,
                            int16_t x,
                            int16_t y)
{
    comp_screen_framebuffer_draw_line(framebuffer, x + 4, y + 9, x + 22, y + 9, true);
    comp_screen_framebuffer_draw_line(framebuffer, x + 22, y + 9, x + 18, y + 5, true);
    comp_screen_framebuffer_draw_line(framebuffer, x + 22, y + 9, x + 18, y + 13, true);
    comp_screen_framebuffer_draw_line(framebuffer, x + 26, y + 21, x + 8, y + 21, true);
    comp_screen_framebuffer_draw_line(framebuffer, x + 8, y + 21, x + 12, y + 17, true);
    comp_screen_framebuffer_draw_line(framebuffer, x + 8, y + 21, x + 12, y + 25, true);
}

static void draw_device_icon(comp_screen_framebuffer_t *framebuffer,
                             int16_t x,
                             int16_t y)
{
    comp_screen_framebuffer_stroke_rect(framebuffer, x + 5, y + 1, 20u, 28u, 2u, true);
    comp_screen_framebuffer_stroke_rect(framebuffer, x + 8, y + 5, 14u, 17u, 1u, true);
    comp_screen_framebuffer_fill_rect(framebuffer, x + 14, y + 25, 3u, 2u, true);
}

static void draw_about_icon(comp_screen_framebuffer_t *framebuffer,
                            int16_t x,
                            int16_t y)
{
    comp_screen_framebuffer_stroke_rect(framebuffer, x + 2, y + 2, 26u, 26u, 2u, true);
    comp_screen_framebuffer_fill_rect(framebuffer, x + 13, y + 7, 4u, 4u, true);
    comp_screen_framebuffer_fill_rect(framebuffer, x + 13, y + 14, 4u, 9u, true);
}

static void draw_home_row(comp_screen_framebuffer_t *framebuffer,
                          int16_t y,
                          const char *label,
                          uint8_t icon,
                          bool selected)
{
    comp_screen_framebuffer_fill_rect(framebuffer, 8, y, 184u, 38u, selected);
    comp_screen_framebuffer_stroke_rect(framebuffer, 8, y, 184u, 38u,
                                        selected ? 3u : 2u, true);
    if (selected) {
        comp_screen_framebuffer_stroke_rect(framebuffer, 20, (int16_t)(y + 7),
                                            24u, 24u, 2u, false);
    } else if (icon == 0u) {
        draw_microphone_icon(framebuffer, 18, (int16_t)(y + 4));
    } else if (icon == 1u) {
        draw_status_icon(framebuffer, 18, (int16_t)(y + 5));
    } else if (icon == 3u) {
        draw_settings_icon(framebuffer, 17, (int16_t)(y + 4));
    } else if (icon == 4u) {
        draw_phone_icon(framebuffer, 17, (int16_t)(y + 4));
    } else if (icon == 6u) {
        draw_device_icon(framebuffer, 17, (int16_t)(y + 4));
    } else {
        draw_about_icon(framebuffer, 17, (int16_t)(y + 4));
    }
    comp_screen_framebuffer_draw_text(framebuffer, 58, (int16_t)(y + 12),
                                      label, 2u, !selected);
    if (icon == 0u || icon == 3u) {
        draw_corner_spark(framebuffer, 151, (int16_t)(y + 11), !selected);
    }
    comp_screen_framebuffer_draw_line(framebuffer, 174, y + 11, 182, y + 19,
                                      !selected);
    comp_screen_framebuffer_draw_line(framebuffer, 182, y + 19, 174, y + 27,
                                      !selected);
}

static void draw_home(comp_screen_framebuffer_t *framebuffer, uint8_t scroll_frame)
{
    static const char *const labels[COMP_SCREEN_MENU_ITEM_COUNT] = {
        "RECORD", "STATUS", "PHONE", "DEVICE",
        "PREFERENCES", "ABOUT",
    };
    static const uint8_t icons[COMP_SCREEN_MENU_ITEM_COUNT] = {
        0u, 1u, 4u, 6u, 3u, 7u,
    };
    uint16_t offset = comp_screen_menu_scroll_offset_px(scroll_frame);
    int16_t pet_y = (int16_t)(39 - (int16_t)offset / 4);

    comp_screen_framebuffer_stroke_rect(framebuffer, 11, pet_y, 178u, 44u, 2u, true);
    comp_screen_framebuffer_fill_rect(framebuffer, 63, (int16_t)(pet_y + 15), 10u, 16u, true);
    comp_screen_framebuffer_fill_rect(framebuffer, 91, (int16_t)(pet_y + 15), 10u, 16u, true);
    comp_screen_framebuffer_draw_line(framebuffer, 78, (int16_t)(pet_y + 34), 83,
                                      (int16_t)(pet_y + 38), true);
    comp_screen_framebuffer_draw_line(framebuffer, 83, (int16_t)(pet_y + 38), 88,
                                      (int16_t)(pet_y + 34), true);
    comp_screen_framebuffer_draw_text(framebuffer, 121, (int16_t)(pet_y + 9),
                                      "HOLD 3S", 1u, true);
    draw_corner_spark(framebuffer, 32, (int16_t)(pet_y + 16), true);
    draw_corner_spark(framebuffer, 173, (int16_t)(pet_y + 31), true);

    for (uint8_t item = 0u; item < COMP_SCREEN_MENU_ITEM_COUNT; ++item) {
        int16_t y = (int16_t)(MENU_HOME_CONTENT_TOP + MENU_HOME_PET_PANEL_HEIGHT +
                              (int16_t)item * MENU_HOME_ITEM_STEP -
                              (int16_t)offset);
        if (y < (int16_t)MENU_HEIGHT && y + 38 > (int16_t)MENU_HOME_CONTENT_TOP) {
            draw_home_row(framebuffer, y, labels[item], icons[item], false);
        }
    }
    comp_screen_framebuffer_fill_rect(framebuffer, 196, MENU_HOME_CONTENT_TOP, 3u,
                                      MENU_HOME_SCROLLBAR_BOTTOM -
                                          MENU_HOME_CONTENT_TOP + 1u,
                                      false);
    comp_screen_framebuffer_stroke_rect(
        framebuffer, 196, MENU_HOME_CONTENT_TOP, 3u,
        MENU_HOME_SCROLLBAR_BOTTOM - MENU_HOME_CONTENT_TOP + 1u, 1u, true);
    comp_screen_framebuffer_fill_rect(framebuffer,
                                      196,
                                      MENU_HOME_SCROLLBAR_TOP,
                                      3u,
                                      MENU_HOME_SCROLLBAR_THUMB_HEIGHT,
                                      true);
    draw_header(framebuffer, "COMPANION", false);
    draw_header_pet_chip(framebuffer);
    /* A fixed, white gutter makes the scrolling viewport unable to paint over
     * the persistent black navigation header. */
    comp_screen_framebuffer_fill_rect(framebuffer, 0, MENU_HEADER_HEIGHT,
                                      MENU_WIDTH,
                                      MENU_HOME_CONTENT_TOP - MENU_HEADER_HEIGHT,
                                      false);
}

static void draw_record(comp_screen_framebuffer_t *framebuffer, uint8_t flags)
{
    bool recording = (flags & COMP_SCREEN_MENU_FLAG_RECORDING) != 0u;
    draw_header(framebuffer, "RECORD", true);
    draw_cat_badge(framebuffer, 82, 39, 1u);
    draw_centered_text(framebuffer, 76, recording ? "RECORDING" : "READY", 2u, true);
    comp_screen_framebuffer_fill_rect(framebuffer, 25, 88, 150u, 66u, recording);
    comp_screen_framebuffer_stroke_rect(framebuffer, 25, 88, 150u, 66u, 3u, true);
    draw_centered_text(framebuffer, 111, recording ? "STOP" : "START", 3u, !recording);
    draw_centered_text(framebuffer, 174, "TAP TO RECORD", 1u, true);
}

static void draw_status_row(comp_screen_framebuffer_t *framebuffer,
                            int16_t y,
                            const char *label,
                            bool ok)
{
    comp_screen_framebuffer_draw_text(framebuffer, 14, y, label, 2u, true);
    comp_screen_framebuffer_draw_text(framebuffer, 151, y, ok ? "OK" : "WAIT", 2u, true);
    comp_screen_framebuffer_draw_line(framebuffer, 10, y + 19, 190, y + 19, true);
}

static void draw_status(comp_screen_framebuffer_t *framebuffer, uint8_t flags)
{
    draw_header(framebuffer, "STATUS", true);
    draw_cat_badge(framebuffer, 82, 39, 0u);
    draw_status_row(framebuffer, 84, "DISPLAY", true);
    draw_status_row(framebuffer, 112, "TOUCH", (flags & COMP_SCREEN_MENU_FLAG_TOUCH_OK) != 0u);
    draw_status_row(framebuffer, 140, "BLE", (flags & COMP_SCREEN_MENU_FLAG_BLE_CONNECTED) != 0u);
    draw_status_row(framebuffer, 168, "RECORD", (flags & COMP_SCREEN_MENU_FLAG_RECORDING) != 0u);
}

static void draw_settings(comp_screen_framebuffer_t *framebuffer)
{
    draw_header(framebuffer, "PREFERENCES", true);
    draw_cat_badge(framebuffer, 82, 36, 2u);
    comp_screen_framebuffer_draw_text(framebuffer, 14, 76, "LANGUAGE", 2u, true);
    comp_screen_framebuffer_stroke_rect(framebuffer, 112, 70, 78u, 28u, 2u, true);
    comp_screen_framebuffer_fill_rect(framebuffer, 114, 72, 35u, 24u, true);
    comp_screen_framebuffer_draw_text(framebuffer, 122, 80, "EN", 1u, false);
    comp_screen_framebuffer_draw_text(framebuffer, 160, 80, "ZH", 1u, true);
    comp_screen_framebuffer_draw_text(framebuffer, 14, 110, "DISPLAY", 2u, true);
    comp_screen_framebuffer_draw_text(framebuffer, 138, 110, "200x200", 1u, true);
    comp_screen_framebuffer_draw_line(framebuffer, 10, 131, 190, 131, true);
    comp_screen_framebuffer_draw_text(framebuffer, 14, 142, "REFRESH", 2u, true);
    comp_screen_framebuffer_draw_text(framebuffer, 151, 142, "SMART", 1u, true);
    comp_screen_framebuffer_draw_line(framebuffer, 10, 163, 190, 163, true);
    comp_screen_framebuffer_draw_text(framebuffer, 14, 174, "ASSETS", 2u, true);
    comp_screen_framebuffer_draw_text(framebuffer, 136, 174, "EXT FLASH", 1u, true);
}

static void draw_info_page(comp_screen_framebuffer_t *framebuffer,
                           const char *title,
                           const char *line1,
                           const char *line2,
                           uint8_t mood)
{
    draw_header(framebuffer, title, true);
    draw_cat_badge(framebuffer, 82, 43, mood);
    draw_centered_text(framebuffer, 100, line1, 2u, true);
    draw_centered_text(framebuffer, 139, line2, 2u, true);
}

bool comp_screen_menu_render(comp_screen_menu_view_t view,
                             comp_screen_menu_language_t language,
                             uint8_t home_page,
                             uint8_t flags,
                             uint8_t *frame,
                             size_t frame_bytes,
                             uint16_t width,
                             uint16_t height)
{
    comp_screen_framebuffer_t framebuffer;

    if (width != MENU_WIDTH || height != MENU_HEIGHT ||
        frame_bytes < MENU_FRAME_BYTES ||
        !comp_screen_framebuffer_init(&framebuffer, frame, frame_bytes, width, height)) {
        return false;
    }
    comp_screen_framebuffer_clear(&framebuffer, false);
    (void)language;
    switch (view) {
    case COMP_SCREEN_MENU_VIEW_HOME:
        draw_home(&framebuffer, home_page);
        break;
    case COMP_SCREEN_MENU_VIEW_RECORD:
        draw_record(&framebuffer, flags);
        break;
    case COMP_SCREEN_MENU_VIEW_STATUS:
        draw_status(&framebuffer, flags);
        break;
    case COMP_SCREEN_MENU_VIEW_PHONE:
        draw_info_page(&framebuffer, "PHONE", "BLE LINK", "READY", 2u);
        break;
    case COMP_SCREEN_MENU_VIEW_DEVICE:
        draw_info_page(&framebuffer, "DEVICE", "WB55", "200x200", 0u);
        break;
    case COMP_SCREEN_MENU_VIEW_PREFERENCES:
        draw_settings(&framebuffer);
        break;
    case COMP_SCREEN_MENU_VIEW_ABOUT:
        draw_info_page(&framebuffer, "ABOUT", "COMPANION", "PET UI", 0u);
        break;
    default:
        return false;
    }
    return true;
}

bool comp_screen_menu_asset_name(comp_screen_menu_view_t view,
                                 comp_screen_menu_language_t language,
                                 uint8_t home_page,
                                 char *destination,
                                 size_t destination_size)
{
    static const char *const view_names[] = {
        "home", "record", "status", "phone", "device",
        "preferences", "about",
    };
    const char *language_name;
    const char *view_name;
    int written;

    if (destination == NULL || destination_size == 0u ||
        view > COMP_SCREEN_MENU_VIEW_ABOUT ||
        (language != COMP_SCREEN_MENU_LANGUAGE_EN &&
         language != COMP_SCREEN_MENU_LANGUAGE_ZH)) {
        return false;
    }
    language_name = language == COMP_SCREEN_MENU_LANGUAGE_ZH ? "zh" : "en";
    (void)home_page;
    view_name = view_names[(uint8_t)view];
    written = snprintf(destination,
                       destination_size,
                       "menu.%s.%s",
                       view_name,
                       language_name);
    return written > 0 && (size_t)written < destination_size;
}

bool comp_screen_menu_render_dynamic(comp_screen_menu_view_t view,
                                     uint8_t flags,
                                     uint8_t home_page,
                                     uint8_t *frame,
                                     size_t frame_bytes,
                                     uint16_t width,
                                     uint16_t height)
{
    comp_screen_framebuffer_t framebuffer;

    if (width != MENU_WIDTH || height != MENU_HEIGHT ||
        frame_bytes < MENU_FRAME_BYTES ||
        !comp_screen_framebuffer_init(&framebuffer, frame, frame_bytes, width, height)) {
        return false;
    }
    if (view == COMP_SCREEN_MENU_VIEW_HOME &&
        (flags & COMP_SCREEN_MENU_FLAG_PRESS_ACTIVE) != 0u) {
        uint8_t item = (uint8_t)((flags & COMP_SCREEN_MENU_FLAG_PRESS_ITEM_MASK) >>
                                 COMP_SCREEN_MENU_FLAG_PRESS_ITEM_SHIFT);
        if (item < COMP_SCREEN_MENU_ITEM_COUNT) {
            int16_t row_y = (int16_t)(MENU_HOME_CONTENT_TOP +
                                      (int16_t)item * MENU_HOME_ITEM_STEP);
            comp_screen_framebuffer_invert_rect(&framebuffer, 6, row_y + 1,
                                                188u, 24u);
        }
    } else if (view == COMP_SCREEN_MENU_VIEW_RECORD) {
        bool recording = (flags & COMP_SCREEN_MENU_FLAG_RECORDING) != 0u;
        if (recording) {
            /* The accepted source already owns the action-button geometry.
             * Replace its idle glyph with the universal stop glyph only while
             * the real recorder FSM is active. */
            comp_screen_framebuffer_fill_rect(&framebuffer, 6, 96, 188u, 28u, true);
            comp_screen_framebuffer_fill_rect(&framebuffer, 91, 103, 18u, 14u, false);
        }
    } else if (view == COMP_SCREEN_MENU_VIEW_STATUS) {
        const bool values[] = {
            true,
            (flags & COMP_SCREEN_MENU_FLAG_TOUCH_OK) != 0u,
            (flags & COMP_SCREEN_MENU_FLAG_BLE_CONNECTED) != 0u,
            (flags & COMP_SCREEN_MENU_FLAG_RECORDING) != 0u,
        };
        static const int16_t rows[] = {41, 80, 119, 158};
        static const char *const online[] = {"OK", "OK", "LINK", "REC"};
        for (size_t index = 0u; index < 4u; ++index) {
            comp_screen_framebuffer_fill_rect(&framebuffer, 140, rows[index], 60u, 20u, false);
            comp_screen_framebuffer_draw_text(&framebuffer, 164, rows[index] + 5,
                                              values[index] ? online[index] : "--",
                                              1u, true);
        }
    } else if (view == COMP_SCREEN_MENU_VIEW_PHONE) {
        bool connected = (flags & COMP_SCREEN_MENU_FLAG_BLE_CONNECTED) != 0u;
        static const int16_t rows[] = {41, 80, 119};
        static const char *const values[] = {"--", "--", "LINK"};
        for (size_t index = 0u; index < 3u; ++index) {
            comp_screen_framebuffer_fill_rect(&framebuffer, 145, rows[index], 55u, 20u, false);
            comp_screen_framebuffer_draw_text(&framebuffer, 166, rows[index] + 5,
                                              index == 2u && connected ? values[index] : "--",
                                              1u, true);
        }
        if (home_page != COMP_SCREEN_MENU_PHONE_RECONNECT_IDLE) {
            const char *retry = home_page == COMP_SCREEN_MENU_PHONE_RECONNECT_ADVERTISING
                                    ? "ADV"
                                    : home_page == COMP_SCREEN_MENU_PHONE_RECONNECT_CONNECTED
                                          ? "LINK"
                                          : "ERR";
            comp_screen_framebuffer_fill_rect(&framebuffer, 145, 158, 55u, 20u, false);
            comp_screen_framebuffer_draw_text(&framebuffer, 166, 163, retry, 1u, true);
        }
    } else if (view == COMP_SCREEN_MENU_VIEW_DEVICE) {
        const bool touch_ok = (flags & COMP_SCREEN_MENU_FLAG_TOUCH_OK) != 0u;
        static const int16_t rows[] = {42, 80, 118, 156};
        static const char *const values[] = {"A2", "OK", "EXT", "PLAN"};

        for (size_t index = 0u; index < 4u; ++index) {
            comp_screen_framebuffer_fill_rect(&framebuffer, 136, rows[index], 64u, 20u, false);
            comp_screen_framebuffer_draw_text(&framebuffer, 164, rows[index] + 5,
                                              index == 1u && !touch_ok ? "--" : values[index],
                                              1u, true);
        }
    }
    return true;
}

static uint32_t framebuffer_fingerprint(const uint8_t *frame, size_t frame_bytes)
{
    uint32_t fingerprint = 0x811C9DC5u;
    size_t index;

    for (index = 0u; index < frame_bytes; ++index) {
        fingerprint = (fingerprint ^ frame[index]) * 0x01000193u;
    }
    return fingerprint;
}

bool comp_screen_menu_v2_self_test(void)
{
    comp_screen_menu_t menu;
    comp_screen_menu_result_t result;
    comp_screen_menu_view_t hit_view;
    uint8_t hit_item;
    comp_touch_gesture_event_t gesture = {0};
    uint8_t frame[MENU_FRAME_BYTES];
    char asset_name[32];
    uint32_t home_idle_fingerprint;
    uint32_t detail_idle_fingerprint;

    comp_screen_menu_init(&menu);
    gesture = (comp_touch_gesture_event_t){
        .type = COMP_TOUCH_GESTURE_LONG_PRESS,
        .start_x = 100u,
        .start_y = 100u,
        .end_x = 101u,
        .end_y = 99u,
    };
    if (!comp_screen_menu_is_daily_entry_gesture(&gesture)) {
        return false;
    }
    gesture.start_x = 4u;
    gesture.start_y = 180u;
    gesture.end_x = 8u;
    gesture.end_y = 177u;
    if (!comp_screen_menu_is_daily_entry_gesture(&gesture)) {
        return false;
    }
    gesture.type = COMP_TOUCH_GESTURE_TAP;
    if (comp_screen_menu_is_daily_entry_gesture(&gesture)) {
        return false;
    }
    if (!comp_screen_menu_home_hit_test(&menu, 4u, 100u, &hit_item, &hit_view) ||
        hit_item != 0u || hit_view != COMP_SCREEN_MENU_VIEW_RECORD ||
        comp_screen_menu_home_hit_test(&menu, 3u, 100u, NULL, NULL) ||
        comp_screen_menu_home_hit_test(&menu, 100u, 76u, NULL, NULL)) {
        return false;
    }
    if (comp_screen_menu_with_ble_flag(
            (uint8_t)(COMP_SCREEN_MENU_FLAG_TOUCH_OK |
                      COMP_SCREEN_MENU_FLAG_BLE_CONNECTED),
            false) != COMP_SCREEN_MENU_FLAG_TOUCH_OK ||
        comp_screen_menu_with_ble_flag(COMP_SCREEN_MENU_FLAG_TOUCH_OK, true) !=
            (uint8_t)(COMP_SCREEN_MENU_FLAG_TOUCH_OK |
                      COMP_SCREEN_MENU_FLAG_BLE_CONNECTED)) {
        return false;
    }
    /* A visible row opens directly; the list position remains independent. */
    result = comp_screen_menu_tap(&menu, 100u, 158u);
    if (!result.changed || result.view != COMP_SCREEN_MENU_VIEW_PHONE) {
        return false;
    }
    gesture = (comp_touch_gesture_event_t){
        .type = COMP_TOUCH_GESTURE_SWIPE_RIGHT,
        .start_x = 112u,
        .end_x = 130u,
    };
    result = comp_screen_menu_gesture(&menu, &gesture);
    if (!comp_screen_menu_is_exit_gesture(&gesture) || !result.changed ||
        result.action != COMP_SCREEN_MENU_ACTION_EXIT_DAILY ||
        result.view != COMP_SCREEN_MENU_VIEW_PHONE) {
        return false;
    }
    comp_screen_menu_init(&menu);
    result = comp_screen_menu_drag(&menu, -53);
    if (!result.changed || result.home_page != 27u ||
        comp_screen_menu_scroll_offset_px(result.home_page) != 54u ||
        comp_screen_menu_exact_scroll_offset_px(&menu) != 53u) {
        return false;
    }
    result = comp_screen_menu_tap(&menu, 100u, 164u);
    if (!result.changed || result.view != COMP_SCREEN_MENU_VIEW_DEVICE) {
        return false;
    }
    result = comp_screen_menu_tap(&menu, 10u, 16u);
    if (!result.changed || result.view != COMP_SCREEN_MENU_VIEW_HOME) {
        return false;
    }
    result = comp_screen_menu_drag_to(&menu, COMP_SCREEN_MENU_SCROLL_MAX_PX);
    if (!result.changed || result.home_page != 42u ||
        comp_screen_menu_exact_scroll_offset_px(&menu) !=
            COMP_SCREEN_MENU_SCROLL_MAX_PX) {
        return false;
    }
    result = comp_screen_menu_tap(&menu, 100u, 140u);
    if (!result.changed || result.view != COMP_SCREEN_MENU_VIEW_PREFERENCES) {
        return false;
    }
    result = comp_screen_menu_tap(&menu, 100u, 60u);
    if (!result.changed ||
        result.action != COMP_SCREEN_MENU_ACTION_LANGUAGE_CHANGED ||
        menu.language != COMP_SCREEN_MENU_LANGUAGE_EN) {
        return false;
    }
    gesture.start_x = 154u;
    result = comp_screen_menu_gesture(&menu, &gesture);
    if (!result.changed ||
        result.action != COMP_SCREEN_MENU_ACTION_EXIT_DAILY ||
        result.view != COMP_SCREEN_MENU_VIEW_PREFERENCES) {
        return false;
    }
    menu.view = COMP_SCREEN_MENU_VIEW_HOME;
    menu.home_page = 42u;
    menu.home_scroll_offset_px = COMP_SCREEN_MENU_SCROLL_MAX_PX;
    result = comp_screen_menu_drag(&menu, -75);
    if (result.changed || result.home_page != 42u ||
        comp_screen_menu_exact_scroll_offset_px(&menu) !=
            COMP_SCREEN_MENU_SCROLL_MAX_PX ||
        !comp_screen_menu_asset_name(result.view,
                                     result.language,
                                     result.home_page,
                                     asset_name,
                                     sizeof(asset_name)) ||
        strcmp(asset_name, "menu.home.en") != 0) {
        return false;
    }
    result = comp_screen_menu_drag(&menu, 45);
    if (!result.changed || result.home_page != 20u ||
        comp_screen_menu_exact_scroll_offset_px(&menu) != 39u) {
        return false;
    }
    gesture.type = COMP_TOUCH_GESTURE_SWIPE_LEFT;
    result = comp_screen_menu_gesture(&menu, &gesture);
    if (comp_screen_menu_is_exit_gesture(&gesture) || result.changed ||
        result.view != COMP_SCREEN_MENU_VIEW_HOME) {
        return false;
    }
    gesture.type = COMP_TOUCH_GESTURE_SWIPE_RIGHT;
    gesture.start_x = 180u;
    result = comp_screen_menu_gesture(&menu, &gesture);
    if (!comp_screen_menu_is_exit_gesture(&gesture) || !result.changed ||
        result.action != COMP_SCREEN_MENU_ACTION_EXIT_DAILY ||
        result.view != COMP_SCREEN_MENU_VIEW_HOME ||
        result.home_page != 20u ||
        comp_screen_menu_exact_scroll_offset_px(&menu) != 39u ||
        !comp_screen_framebuffer_self_test() ||
        !comp_screen_menu_render(COMP_SCREEN_MENU_VIEW_HOME,
                                 COMP_SCREEN_MENU_LANGUAGE_EN,
                                 0u,
                                 COMP_SCREEN_MENU_FLAG_TOUCH_OK,
                                 frame,
                                 sizeof(frame),
                                 MENU_WIDTH,
                                 MENU_HEIGHT)) {
        return false;
    }
    home_idle_fingerprint = framebuffer_fingerprint(frame, sizeof(frame));
    if (!comp_screen_menu_render_dynamic(
            COMP_SCREEN_MENU_VIEW_HOME,
            (uint8_t)(COMP_SCREEN_MENU_FLAG_PRESS_ACTIVE |
                      (3u << COMP_SCREEN_MENU_FLAG_PRESS_ITEM_SHIFT)),
            0u,
            frame,
            sizeof(frame),
            MENU_WIDTH,
            MENU_HEIGHT) ||
        framebuffer_fingerprint(frame, sizeof(frame)) == home_idle_fingerprint) {
        return false;
    }
    if (!comp_screen_menu_render_dynamic(COMP_SCREEN_MENU_VIEW_STATUS,
                                         0u,
                                         0u,
                                         frame,
                                         sizeof(frame),
                                         MENU_WIDTH,
                                         MENU_HEIGHT)) {
        return false;
    }
    detail_idle_fingerprint = framebuffer_fingerprint(frame, sizeof(frame));
    return comp_screen_menu_render_dynamic(COMP_SCREEN_MENU_VIEW_STATUS,
                                           COMP_SCREEN_MENU_FLAG_PRESS_ACTIVE,
                                           0u,
                                           frame,
                                           sizeof(frame),
                                           MENU_WIDTH,
                                           MENU_HEIGHT) &&
           framebuffer_fingerprint(frame, sizeof(frame)) != detail_idle_fingerprint &&
           memchr(frame, 0x00, sizeof(frame)) != NULL &&
           memchr(frame, 0xFF, sizeof(frame)) != NULL;
}

bool comp_screen_menu_self_test(void)
{
    comp_screen_menu_t menu;
    comp_screen_menu_result_t result;
    comp_screen_menu_view_t hit_view;
    uint8_t hit_item;
    comp_touch_gesture_event_t gesture = {0};
    uint8_t frame[MENU_FRAME_BYTES];
    uint32_t fingerprint;

    comp_screen_menu_init(&menu);
    gesture = (comp_touch_gesture_event_t){
        .type = COMP_TOUCH_GESTURE_LONG_PRESS,
        .start_x = 4u,
        .start_y = 180u,
        .end_x = 8u,
        .end_y = 177u,
    };
    if (!comp_screen_menu_is_daily_entry_gesture(&gesture)) {
        return false;
    }
    gesture.type = COMP_TOUCH_GESTURE_TAP;
    if (comp_screen_menu_is_daily_entry_gesture(&gesture) ||
        !comp_screen_menu_home_hit_test(&menu, 4u, 47u, &hit_item, &hit_view) ||
        hit_item != 0u || hit_view != COMP_SCREEN_MENU_VIEW_RECORD ||
        !comp_screen_menu_home_hit_test(&menu, 100u, 178u, &hit_item, &hit_view) ||
        hit_item != 5u || hit_view != COMP_SCREEN_MENU_VIEW_ABOUT ||
        comp_screen_menu_home_hit_test(&menu, 100u, 34u, NULL, NULL)) {
        return false;
    }
    result = comp_screen_menu_tap(&menu, 100u, 73u);
    if (!result.changed || result.view != COMP_SCREEN_MENU_VIEW_STATUS) {
        return false;
    }
    gesture = (comp_touch_gesture_event_t){
        .type = COMP_TOUCH_GESTURE_SWIPE_RIGHT,
        .start_x = 144u,
        .end_x = 188u,
    };
    result = comp_screen_menu_gesture(&menu, &gesture);
    if (!comp_screen_menu_is_exit_gesture(&gesture) || !result.changed ||
        result.action != COMP_SCREEN_MENU_ACTION_EXIT_DAILY ||
        result.view != COMP_SCREEN_MENU_VIEW_STATUS) {
        return false;
    }
    comp_screen_menu_init(&menu);
    result = comp_screen_menu_drag(&menu, -54);
    if (result.changed || result.home_page != 0u ||
        comp_screen_menu_exact_scroll_offset_px(&menu) != 0u) {
        return false;
    }
    result = comp_screen_menu_tap(&menu, 100u, 151u);
    if (!result.changed || result.view != COMP_SCREEN_MENU_VIEW_PREFERENCES) {
        return false;
    }
    result = comp_screen_menu_tap(&menu, 100u, 60u);
    if (!result.changed ||
        result.action != COMP_SCREEN_MENU_ACTION_LANGUAGE_CHANGED ||
        menu.language != COMP_SCREEN_MENU_LANGUAGE_EN) {
        return false;
    }
    gesture.start_x = 160u;
    gesture.end_x = 194u;
    result = comp_screen_menu_gesture(&menu, &gesture);
    if (!comp_screen_menu_is_exit_gesture(&gesture) || !result.changed ||
        result.action != COMP_SCREEN_MENU_ACTION_EXIT_DAILY ||
        result.view != COMP_SCREEN_MENU_VIEW_PREFERENCES) {
        return false;
    }
    comp_screen_menu_init(&menu);
    menu.language = COMP_SCREEN_MENU_LANGUAGE_EN;
    result = comp_screen_menu_tap(&menu, 100u, 99u);
    if (!result.changed || result.view != COMP_SCREEN_MENU_VIEW_PHONE) {
        return false;
    }
    result = comp_screen_menu_tap(&menu, 100u, 160u);
    if (!result.changed ||
        result.action != COMP_SCREEN_MENU_ACTION_PHONE_RECONNECT) {
        return false;
    }
    comp_screen_menu_set_phone_reconnect_state(
        &menu, COMP_SCREEN_MENU_PHONE_RECONNECT_ADVERTISING);
    if (menu.home_page != COMP_SCREEN_MENU_PHONE_RECONNECT_ADVERTISING) {
        return false;
    }
    if (!comp_screen_menu_render(COMP_SCREEN_MENU_VIEW_PHONE,
                                 COMP_SCREEN_MENU_LANGUAGE_EN,
                                 0u,
                                 0u,
                                 frame,
                                 sizeof(frame),
                                 MENU_WIDTH,
                                 MENU_HEIGHT)) {
        return false;
    }
    fingerprint = framebuffer_fingerprint(frame, sizeof(frame));
    if (!comp_screen_menu_render_dynamic(
            COMP_SCREEN_MENU_VIEW_PHONE,
            0u,
            COMP_SCREEN_MENU_PHONE_RECONNECT_ADVERTISING,
            frame,
            sizeof(frame),
            MENU_WIDTH,
            MENU_HEIGHT) ||
        framebuffer_fingerprint(frame, sizeof(frame)) == fingerprint) {
        return false;
    }
    result = comp_screen_menu_gesture(&menu, &gesture);
    if (!result.changed ||
        result.action != COMP_SCREEN_MENU_ACTION_EXIT_DAILY ||
        result.view != COMP_SCREEN_MENU_VIEW_PHONE ||
        result.home_page != COMP_SCREEN_MENU_PHONE_RECONNECT_ADVERTISING) {
        return false;
    }
    if (!comp_screen_menu_render(COMP_SCREEN_MENU_VIEW_HOME,
                                 COMP_SCREEN_MENU_LANGUAGE_EN,
                                 0u,
                                 COMP_SCREEN_MENU_FLAG_TOUCH_OK,
                                 frame,
                                 sizeof(frame),
                                 MENU_WIDTH,
                                 MENU_HEIGHT)) {
        return false;
    }
    fingerprint = framebuffer_fingerprint(frame, sizeof(frame));
    if (!comp_screen_menu_render_dynamic(
            COMP_SCREEN_MENU_VIEW_HOME,
            (uint8_t)(COMP_SCREEN_MENU_FLAG_PRESS_ACTIVE |
                      (3u << COMP_SCREEN_MENU_FLAG_PRESS_ITEM_SHIFT)),
            0u,
            frame,
            sizeof(frame),
            MENU_WIDTH,
            MENU_HEIGHT) ||
        framebuffer_fingerprint(frame, sizeof(frame)) == fingerprint) {
        return false;
    }
    if (!comp_screen_menu_render(COMP_SCREEN_MENU_VIEW_STATUS,
                                 COMP_SCREEN_MENU_LANGUAGE_EN,
                                 0u,
                                 COMP_SCREEN_MENU_FLAG_TOUCH_OK,
                                 frame,
                                 sizeof(frame),
                                 MENU_WIDTH,
                                 MENU_HEIGHT)) {
        return false;
    }
    fingerprint = framebuffer_fingerprint(frame, sizeof(frame));
    if (!comp_screen_menu_render_dynamic(
            COMP_SCREEN_MENU_VIEW_STATUS,
            (uint8_t)(COMP_SCREEN_MENU_FLAG_TOUCH_OK |
                      COMP_SCREEN_MENU_FLAG_BLE_CONNECTED),
            0u,
            frame,
            sizeof(frame),
            MENU_WIDTH,
            MENU_HEIGHT) ||
        framebuffer_fingerprint(frame, sizeof(frame)) == fingerprint ||
        memchr(frame, 0x00, sizeof(frame)) == NULL ||
        memchr(frame, 0xFF, sizeof(frame)) == NULL ||
        !comp_screen_menu_render(COMP_SCREEN_MENU_VIEW_DEVICE,
                                 COMP_SCREEN_MENU_LANGUAGE_EN,
                                 0u,
                                 COMP_SCREEN_MENU_FLAG_TOUCH_OK,
                                 frame,
                                 sizeof(frame),
                                 MENU_WIDTH,
                                 MENU_HEIGHT)) {
        return false;
    }
    fingerprint = framebuffer_fingerprint(frame, sizeof(frame));
    return comp_screen_menu_render_dynamic(COMP_SCREEN_MENU_VIEW_DEVICE,
                                           COMP_SCREEN_MENU_FLAG_TOUCH_OK,
                                           0u,
                                           frame,
                                           sizeof(frame),
                                           MENU_WIDTH,
                                           MENU_HEIGHT) &&
           framebuffer_fingerprint(frame, sizeof(frame)) != fingerprint;
}
