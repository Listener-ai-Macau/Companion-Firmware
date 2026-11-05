#define COMP_CUSTOMER_MENU_TABLES
#include "screen_menu.h"
#undef COMP_CUSTOMER_MENU_TABLES

#include "screen_framebuffer.h"
#if COMPANION_WBA_RESOURCE_PROFILE
#include "companion_wba_menu_geometry.h"
#include "companion_wba_resource_contract.h"
#endif

#if COMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK
#include "companion_browser_interaction_contract.h"
#endif

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

#if !COMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK
static const comp_screen_menu_view_t s_browser_home_views[8] = {
    COMP_SCREEN_MENU_VIEW_BROWSER_VOICE,
    COMP_SCREEN_MENU_VIEW_BROWSER_DISPLAY,
    COMP_SCREEN_MENU_VIEW_BROWSER_INTERACTION,
    COMP_SCREEN_MENU_VIEW_BROWSER_CONNECTION,
    COMP_SCREEN_MENU_VIEW_BROWSER_STORAGE,
    COMP_SCREEN_MENU_VIEW_BROWSER_POWER,
    COMP_SCREEN_MENU_VIEW_BROWSER_PREFERENCES,
    COMP_SCREEN_MENU_VIEW_BROWSER_ABOUT,
};

static const uint8_t s_browser_menu_item_counts[13] = {
    8u, 7u, 4u, 7u, 4u, 2u, 2u, 5u, 6u, 7u, 5u, 3u, 3u,
};
#endif

bool comp_screen_menu_is_browser_view(comp_screen_menu_view_t view)
{
    if(comp_screen_menu_customer_active() &&
       ((unsigned)view==COMP_CUSTOMER_FILE_HELP_VIEW || (unsigned)view==COMP_CUSTOMER_DEVICE_VIEW ||
        ((unsigned)view>=COMP_CUSTOMER_CHOICE_BASE && comp_screen_menu_customer_count(view))))return true;
    return view >= COMP_SCREEN_MENU_VIEW_BROWSER_HOME &&
           view <= COMP_SCREEN_MENU_VIEW_BROWSER_QUICK;
}

bool comp_screen_menu_is_home_view(comp_screen_menu_view_t view)
{
    return view == COMP_SCREEN_MENU_VIEW_HOME ||
           view == COMP_SCREEN_MENU_VIEW_BROWSER_HOME;
}

static uint8_t browser_screen_index(comp_screen_menu_view_t view)
{
    return (uint8_t)(view - COMP_SCREEN_MENU_VIEW_BROWSER_HOME);
}

uint8_t comp_screen_menu_source_row(comp_screen_menu_view_t view,uint8_t logical)
{
#if COMPANION_WBA_RESOURCE_PROFILE
    /* Everyday controls precede read-only technical/status rows. Preserve
     * all original rows, native labels, item IDs, settings and navigation. */
    if(view==COMP_SCREEN_MENU_VIEW_BROWSER_VOICE && logical<2u)return (uint8_t)(1u-logical);
    if(view==COMP_SCREEN_MENU_VIEW_BROWSER_DISPLAY && logical>0u && logical<4u)
        return logical==1u?3u:(uint8_t)(logical-1u);
#else
    (void)view;
#endif
    return logical;
}
static uint8_t browser_item_count(comp_screen_menu_view_t view)
{
    if(comp_screen_menu_customer_active())return comp_screen_menu_customer_count(view);
    if(view==COMP_SCREEN_MENU_VIEW_BROWSER_QUICK)return 0u;
    if(view==COMP_SCREEN_MENU_VIEW_BROWSER_PET_HELP)return 3u;
    const uint8_t index=browser_screen_index(view);
    if(index>=13u)return 0u;
#if COMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK
    uint8_t count=companion_browser_menu_item_counts[index];
#else
    uint8_t count=s_browser_menu_item_counts[index];
#endif
#if COMPANION_WBA_RESOURCE_PROFILE
    if(view==COMP_SCREEN_MENU_VIEW_BROWSER_INTERACTION)++count;
#endif
    return count;
}

static uint8_t browser_scroll_max(comp_screen_menu_view_t view)
{
    uint8_t count;
#if COMPANION_WBA_RESOURCE_PROFILE
    if (view == COMP_SCREEN_MENU_VIEW_BROWSER_HOME) return comp_screen_menu_customer_active()?0u:4u;
#endif
    count=browser_item_count(view);
#if COMPANION_WBA_RESOURCE_PROFILE
    if(comp_screen_menu_customer_active())
        return count>COMP_WBA_MENU_VISIBLE_ROWS?(uint8_t)(count-COMP_WBA_MENU_VISIBLE_ROWS):0u;
    return count > 0u
        ? (uint8_t)(((count - 1u) / COMP_WBA_MENU_VISIBLE_ROWS) * COMP_WBA_MENU_VISIBLE_ROWS) : 0u;
#else
    return count > 4u ? (uint8_t)(count - 4u) : 0u;
#endif
}

uint8_t comp_screen_menu_browser_page_count(comp_screen_menu_view_t view)
{
#if COMPANION_WBA_RESOURCE_PROFILE
    if(comp_screen_menu_customer_active())return (uint8_t)(browser_scroll_max(view)+1u);
    return (uint8_t)(browser_scroll_max(view) / COMP_WBA_MENU_VISIBLE_ROWS + 1u);
#else
    return (uint8_t)(browser_scroll_max(view) + 1u);
#endif
}

static uint8_t browser_hit_index(const comp_screen_menu_t *menu,
                                 uint16_t x, uint16_t y)
{
#if COMPANION_WBA_RESOURCE_PROFILE
    if(menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_PET_HELP) {
        if(x<12u || x>188u)return 0xffu;
        for(uint8_t i=0u;i<3u;++i)
            if(y>=106u+28u*i && y<130u+28u*i)return i;
        return 0xffu;
    }
    if (menu->view == COMP_SCREEN_MENU_VIEW_BROWSER_CLEAR_RECORDINGS ||
        menu->view == COMP_SCREEN_MENU_VIEW_BROWSER_RESTORE_DEFAULTS) {
        /* Only the two visible confirmation buttons are active. The icon,
         * count, explanation and the gap between buttons never confirm. */
        if (y < COMP_WBA_CONFIRM_TOP || y > COMP_WBA_CONFIRM_BOTTOM) return 0xFFu;
        if (x >= COMP_WBA_CONFIRM_LEFT && x <= COMP_WBA_CONFIRM_RIGHT) return 1u;
        if (x >= COMP_WBA_CANCEL_LEFT && x <= COMP_WBA_CANCEL_RIGHT) return 2u;
        return 0xFFu;
    }
    if (menu->view == COMP_SCREEN_MENU_VIEW_BROWSER_HOME) {
        /* WBA menu art: two 2x2 pages. The gutters and page indicator are
         * intentionally inert; a tap there must not open a nearby tile. */
        if (x < 8u || x >= 192u || (x >= 94u && x < 106u) ||
            y < 46u || y >= 187u ||
            (!comp_screen_menu_customer_active() && y >= 115u && y < 121u)) return 0xFFu;
        /* The customer menu has no drawn horizontal gutter. Its category
         * name and surrounding tile space form one target, including y115.
         * Keep the centre column gap and different start/end tile guard. */
        return (uint8_t)((menu->home_page >= 4u ? 4u : 0u) +
                         (y >= 121u ? 2u : 0u) + (x >= 106u ? 1u : 0u));
    }
    /* The subtitle gap, side gutters and position footer are
     * display-only. Hidden fourth rows must never remain active. */
    if (x < 12u || x > 188u || y < COMP_WBA_MENU_ROW_TOP ||
        y >= COMP_WBA_MENU_BODY_BOTTOM) return 0xFFu;
    return (uint8_t)(menu->home_page +
                    (y - COMP_WBA_MENU_ROW_TOP) / COMP_WBA_MENU_ROW_HEIGHT);
#else
    (void)x;
    return (uint8_t)(menu->home_page + (y - 45u) / 40u);
#endif
}

static void browser_navigation_clear(comp_screen_menu_t *menu)
{
    if (menu != NULL) {
        menu->navigation_depth = 0u;
    }
}

static void browser_navigation_push(comp_screen_menu_t *menu)
{
    if (menu == NULL || !comp_screen_menu_is_browser_view(menu->view)) {
        return;
    }
    if (menu->navigation_depth >= COMP_SCREEN_MENU_NAV_HISTORY_DEPTH) {
        return;
    }
    menu->navigation_views[menu->navigation_depth] = (uint8_t)menu->view;
    menu->navigation_pages[menu->navigation_depth++] = menu->home_page;
}

bool comp_screen_menu_navigate_to(comp_screen_menu_t *menu,
                                  comp_screen_menu_view_t target)
{
    if (menu == NULL || !comp_screen_menu_is_browser_view(target) ||
        menu->view == target) {
        return false;
    }
    if (comp_screen_menu_is_browser_view(menu->view)) {
        if (menu->navigation_depth >= COMP_SCREEN_MENU_NAV_HISTORY_DEPTH) {
            return false;
        }
        browser_navigation_push(menu);
    } else {
        browser_navigation_clear(menu);
    }
    menu->view = target;
    menu->home_page = 0u;
    menu->revision++;
    return true;
}

bool comp_screen_menu_back(comp_screen_menu_t *menu)
{
    comp_screen_menu_view_t parent;
    uint8_t page = 0u;

    if (menu == NULL || !comp_screen_menu_is_browser_view(menu->view) ||
        menu->view == COMP_SCREEN_MENU_VIEW_BROWSER_HOME) {
        return false;
    }
    if (menu->navigation_depth > 0u) {
        const uint8_t index = --menu->navigation_depth;
        parent = (comp_screen_menu_view_t)menu->navigation_views[index];
        page = menu->navigation_pages[index];
        if (!comp_screen_menu_is_browser_view(parent)) {
            parent = COMP_SCREEN_MENU_VIEW_BROWSER_HOME;
            page = 0u;
            browser_navigation_clear(menu);
        }
    } else {
        /* Navigation history is not persisted. A corrupt or legacy direct
         * child state fails safely to browser home instead of guessing the
         * wrong parent for shared screens. */
        parent = COMP_SCREEN_MENU_VIEW_BROWSER_HOME;
    }
    if (page > browser_scroll_max(parent)) {
        page = browser_scroll_max(parent);
    }
#if COMPANION_WBA_RESOURCE_PROFILE
    if (!comp_screen_menu_customer_active() && parent != COMP_SCREEN_MENU_VIEW_BROWSER_HOME)
        page = (uint8_t)((page / COMP_WBA_MENU_VISIBLE_ROWS) * COMP_WBA_MENU_VISIBLE_ROWS);
#endif
    menu->view = parent;
    menu->home_page = page;
    menu->revision++;
    return true;
}

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

    if (menu == NULL || !comp_screen_menu_is_home_view(menu->view) ||
        x < 4u || x >= 196u || y >= MENU_HEIGHT) {
        return false;
    }
    if (menu->view == COMP_SCREEN_MENU_VIEW_BROWSER_HOME) {
        if (y < 45u) {
            return false;
        }
        hit = browser_hit_index(menu, x, y);
        if (hit >= 8u) {
            return false;
        }
        if (item != NULL) {
            *item = hit;
        }
        if (view != NULL) {
            if(comp_screen_menu_customer_active()) {
                comp_customer_menu_row_t row;
                if(!comp_screen_menu_customer_row(menu,hit,&row) || row.kind!=1u)return false;
                *view=(comp_screen_menu_view_t)row.target;return true;
            }
#if COMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK
            const companion_browser_menu_row_t *row =
                companion_browser_menu_row(0u, hit);
            if (row == NULL ||
                row->kind != COMPANION_BROWSER_MENU_KIND_NAVIGATE ||
                row->target >= COMPANION_BROWSER_MENU_SCREEN_COUNT) {
                return false;
            }
            *view = (comp_screen_menu_view_t)(
                COMP_SCREEN_MENU_VIEW_BROWSER_HOME + row->target);
#else
            *view = s_browser_home_views[hit];
#endif
        }
        return true;
    }
    if (y < MENU_HOME_CONTENT_TOP) {
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

static void browser_defaults(comp_screen_menu_t *menu, bool initialize)
{
    bool link_connected;
    uint16_t recording_count;
    uint16_t recording_storage_kb;
    uint8_t battery_percent;

    if (menu == NULL) return;
    link_connected = initialize ? false : menu->browser.link_connected;
    recording_count = initialize ? 0u : menu->browser.recording_count;
    recording_storage_kb = initialize ? 0u : menu->browser.recording_storage_kb;
    /* NUCLEO-WB55RG has no product battery gauge.  0xFF is unavailable,
     * never a fabricated charge percentage. */
    battery_percent = initialize ? 0xFFu : menu->browser.battery_percent;
    menu->browser = (comp_screen_menu_browser_state_t){
        .link_connected = link_connected,
        .silent_auto_stop = true,
        .auto_reconnect = true,
        .clock_24_hour = true,
        .gaze_follow = true,
        .natural_blink = true,
        .auto_sleep_minutes = 3u,
        .recording_limit_minutes = 0u,
        .recorder_profile = COMP_SCREEN_MENU_RECORDER_PROFILE_VOICE,
        .interaction_level = COMP_SCREEN_MENU_INTERACTION_STANDARD,
        .pet_volume = 25u,
        .quiet_hours = COMP_SCREEN_MENU_QUIET_HOURS_23_07,
        .recording_gesture =
            COMP_SCREEN_MENU_RECORDING_GESTURE_CORNER_DOUBLE_TAP,
        .time_zone_offset_minutes = 480,
        .recording_count = recording_count,
        .recording_storage_kb = recording_storage_kb,
        .battery_percent = battery_percent,
    };
}

void comp_screen_menu_restore_browser_defaults(comp_screen_menu_t *menu)
{
    if (menu == NULL) return;
    browser_defaults(menu, false);
    menu->language = COMP_SCREEN_MENU_LANGUAGE_ZH;
    menu->revision++;
}

bool comp_screen_menu_complete_browser_action(comp_screen_menu_t *menu,
                                              uint8_t browser_item)
{
#if COMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK
    if (menu == NULL) return false;
    switch (browser_item) {
    case COMPANION_BROWSER_MENU_ITEM_CONNECTION_TOGGLE:
        /* Link state is hardware truth and is refreshed by the target after
         * the HCI event; acknowledging a press must not fabricate it. */
        break;
    case COMPANION_BROWSER_MENU_ITEM_CONFIRM_CLEAR:
        menu->browser.recording_count = 0u;
        menu->browser.recording_storage_kb = 0u;
        break;
    case COMPANION_BROWSER_MENU_ITEM_CONFIRM_RESTORE:
        comp_screen_menu_restore_browser_defaults(menu);
        return true;
    case COMPANION_BROWSER_MENU_ITEM_PAIR:
    case COMPANION_BROWSER_MENU_ITEM_RESET_NAME:
    case COMPANION_BROWSER_MENU_ITEM_SLEEP_NOW:
        break;
    default:
        return false;
    }
    menu->revision++;
    return true;
#else
    (void)menu;
    (void)browser_item;
    return false;
#endif
}

#if COMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK
static bool apply_browser_setting(comp_screen_menu_t *menu, uint8_t item)
{
    static const uint8_t sleep_choices[] = {1u, 3u, 5u, 0u};
    static const uint8_t recording_limit_choices[] = {15u, 30u, 60u, 0u};
    static const int16_t timezone_choices[] = {480, 0, -300};
    uint8_t index;

    if (menu == NULL) return false;
    switch (item) {
#if COMPANION_WBA_RESOURCE_PROFILE
    case COMPANION_BROWSER_MENU_ITEM_STATUS_BAR:
        menu->browser.battery_fill = !menu->browser.battery_fill;
        return true;
#endif
    case COMPANION_BROWSER_MENU_ITEM_AUTO_STOP:
        menu->browser.silent_auto_stop = !menu->browser.silent_auto_stop;
        return true;
    case COMPANION_BROWSER_MENU_ITEM_AUTO_RECONNECT:
        menu->browser.auto_reconnect = !menu->browser.auto_reconnect;
        return true;
    case COMPANION_BROWSER_MENU_ITEM_CLOCK_FORMAT:
        menu->browser.clock_24_hour = !menu->browser.clock_24_hour;
        return true;
    case COMPANION_BROWSER_MENU_ITEM_GAZE_FOLLOW:
        menu->browser.gaze_follow = !menu->browser.gaze_follow;
        return true;
    case COMPANION_BROWSER_MENU_ITEM_NATURAL_BLINK:
        menu->browser.natural_blink = !menu->browser.natural_blink;
        return true;
    case COMPANION_BROWSER_MENU_ITEM_RECORDER_PROFILE:
        menu->browser.recorder_profile =
            menu->browser.recorder_profile ==
                    COMP_SCREEN_MENU_RECORDER_PROFILE_VOICE
                ? COMP_SCREEN_MENU_RECORDER_PROFILE_MEETING
                : COMP_SCREEN_MENU_RECORDER_PROFILE_VOICE;
        return true;
    case COMPANION_BROWSER_MENU_ITEM_INTERACTION_LEVEL:
        menu->browser.interaction_level =
            (uint8_t)((menu->browser.interaction_level + 1u) % 3u);
        return true;
    case COMPANION_BROWSER_MENU_ITEM_QUIET_HOURS:
        menu->browser.quiet_hours =
            (uint8_t)((menu->browser.quiet_hours + 1u) % 3u);
        return true;
    case COMPANION_BROWSER_MENU_ITEM_CORNER_DOUBLE_TAP:
        if (menu->browser.recording_gesture ==
            COMP_SCREEN_MENU_RECORDING_GESTURE_CORNER_DOUBLE_TAP) return false;
        menu->browser.recording_gesture =
            COMP_SCREEN_MENU_RECORDING_GESTURE_CORNER_DOUBLE_TAP;
        return true;
    case COMPANION_BROWSER_MENU_ITEM_EDGE_PULL:
        if (menu->browser.recording_gesture ==
            COMP_SCREEN_MENU_RECORDING_GESTURE_EDGE_PULL) return false;
        menu->browser.recording_gesture =
            COMP_SCREEN_MENU_RECORDING_GESTURE_EDGE_PULL;
        return true;
    case COMPANION_BROWSER_MENU_ITEM_AUTO_SLEEP:
        for (index = 0u; index < 4u; ++index) {
            if (sleep_choices[index] == menu->browser.auto_sleep_minutes) {
                menu->browser.auto_sleep_minutes =
                    sleep_choices[(index + 1u) % 4u];
                return true;
            }
        }
        menu->browser.auto_sleep_minutes = sleep_choices[0];
        return true;
    case COMPANION_BROWSER_MENU_ITEM_RECORDING_LIMIT:
        for (index = 0u; index < 4u; ++index) {
            if (recording_limit_choices[index] ==
                menu->browser.recording_limit_minutes) {
                menu->browser.recording_limit_minutes =
                    recording_limit_choices[(index + 1u) % 4u];
                return true;
            }
        }
        menu->browser.recording_limit_minutes = recording_limit_choices[0];
        return true;
    case COMPANION_BROWSER_MENU_ITEM_TIME_ZONE:
        for (index = 0u; index < 3u; ++index) {
            if (timezone_choices[index] ==
                menu->browser.time_zone_offset_minutes) {
                menu->browser.time_zone_offset_minutes =
                    timezone_choices[(index + 1u) % 3u];
                return true;
            }
        }
        menu->browser.time_zone_offset_minutes = timezone_choices[0];
        return true;
    default:
        return false;
    }
}

uint8_t comp_screen_menu_browser_variant(const comp_screen_menu_t *menu)
{
    uint8_t screen;
    uint8_t gesture;
    uint8_t index;

    if (menu == NULL || !comp_screen_menu_is_browser_view(menu->view)) return 0u;
    screen = browser_screen_index(menu->view);
    gesture = menu->browser.recording_gesture ==
                      COMP_SCREEN_MENU_RECORDING_GESTURE_EDGE_PULL
                  ? 1u : 0u;
    switch (screen) {
    case 1u:
        index = menu->browser.recording_limit_minutes == 30u ? 0u :
                menu->browser.recording_limit_minutes == 15u ? 1u :
                menu->browser.recording_limit_minutes == 60u ? 2u : 3u;
        return (uint8_t)((((gesture * 2u + menu->browser.recorder_profile) *
                            4u + index) * 2u) +
                         (menu->browser.silent_auto_stop ? 0u : 1u));
    case 2u:
        return menu->browser.clock_24_hour ? 0u : 1u;
    case 3u:
        return (uint8_t)((menu->browser.link_connected ? 0u : 2u) +
                         (menu->browser.auto_reconnect ? 0u : 1u));
    case 4u:
        index = menu->browser.time_zone_offset_minutes == 480 ? 0u :
                menu->browser.time_zone_offset_minutes == 0 ? 1u : 2u;
        return (uint8_t)(index * 3u + menu->browser.quiet_hours);
    case 5u:
        return gesture;
    case 8u:
        index = menu->browser.interaction_level ==
                        COMP_SCREEN_MENU_INTERACTION_STANDARD ? 0u :
                menu->browser.interaction_level ==
                        COMP_SCREEN_MENU_INTERACTION_LIVELY ? 1u : 2u;
        return (uint8_t)((((gesture * 3u + index) * 2u +
                            (menu->browser.gaze_follow ? 0u : 1u)) * 2u) +
                         (menu->browser.natural_blink ? 0u : 1u));
    case 9u:
    case 11u:
        return menu->browser.recording_count == 0u ? 1u : 0u;
    case 10u:
        return menu->browser.auto_sleep_minutes == 3u ? 0u :
               menu->browser.auto_sleep_minutes == 5u ? 1u :
               menu->browser.auto_sleep_minutes == 0u ? 2u : 3u;
    default:
        return 0u;
    }
}

bool comp_screen_menu_browser_runtime_self_test(void)
{
    comp_screen_menu_t menu;
    uint8_t index;

    comp_screen_menu_init(&menu);
    if (menu.browser.link_connected ||
        !menu.browser.silent_auto_stop ||
        !menu.browser.auto_reconnect ||
        !menu.browser.clock_24_hour ||
        !menu.browser.gaze_follow ||
        !menu.browser.natural_blink ||
        menu.browser.auto_sleep_minutes != 3u ||
        menu.browser.recording_limit_minutes != 0u ||
        menu.browser.recorder_profile !=
            COMP_SCREEN_MENU_RECORDER_PROFILE_VOICE ||
        menu.browser.interaction_level !=
            COMP_SCREEN_MENU_INTERACTION_STANDARD ||
        menu.browser.time_zone_offset_minutes != 480 ||
        menu.browser.quiet_hours != COMP_SCREEN_MENU_QUIET_HOURS_23_07 ||
        menu.browser.recording_gesture !=
            COMP_SCREEN_MENU_RECORDING_GESTURE_CORNER_DOUBLE_TAP ||
        menu.browser.recording_count != 0u ||
        menu.browser.recording_storage_kb != 0u ||
        menu.browser.battery_percent != 0xFFu) {
        return false;
    }
    for (index = 0u; index < 2u; ++index) {
        if (!apply_browser_setting(
                &menu, COMPANION_BROWSER_MENU_ITEM_AUTO_STOP) ||
            !apply_browser_setting(
                &menu, COMPANION_BROWSER_MENU_ITEM_AUTO_RECONNECT) ||
            !apply_browser_setting(
                &menu, COMPANION_BROWSER_MENU_ITEM_CLOCK_FORMAT) ||
            !apply_browser_setting(
                &menu, COMPANION_BROWSER_MENU_ITEM_GAZE_FOLLOW) ||
            !apply_browser_setting(
                &menu, COMPANION_BROWSER_MENU_ITEM_NATURAL_BLINK) ||
            !apply_browser_setting(
                &menu, COMPANION_BROWSER_MENU_ITEM_RECORDER_PROFILE)) {
            return false;
        }
    }
    for (index = 0u; index < 4u; ++index) {
        if (!apply_browser_setting(
                &menu, COMPANION_BROWSER_MENU_ITEM_AUTO_SLEEP) ||
            !apply_browser_setting(
                &menu, COMPANION_BROWSER_MENU_ITEM_RECORDING_LIMIT)) {
            return false;
        }
    }
    for (index = 0u; index < 3u; ++index) {
        if (!apply_browser_setting(
                &menu, COMPANION_BROWSER_MENU_ITEM_INTERACTION_LEVEL) ||
            !apply_browser_setting(
                &menu, COMPANION_BROWSER_MENU_ITEM_TIME_ZONE) ||
            !apply_browser_setting(
                &menu, COMPANION_BROWSER_MENU_ITEM_QUIET_HOURS)) {
            return false;
        }
    }
    if (menu.browser.silent_auto_stop != true ||
        menu.browser.auto_reconnect != true ||
        menu.browser.clock_24_hour != true ||
        menu.browser.gaze_follow != true ||
        menu.browser.natural_blink != true ||
        menu.browser.auto_sleep_minutes != 3u ||
        menu.browser.recording_limit_minutes != 0u ||
        menu.browser.recorder_profile !=
            COMP_SCREEN_MENU_RECORDER_PROFILE_VOICE ||
        menu.browser.interaction_level !=
            COMP_SCREEN_MENU_INTERACTION_STANDARD ||
        menu.browser.time_zone_offset_minutes != 480 ||
        menu.browser.quiet_hours != COMP_SCREEN_MENU_QUIET_HOURS_23_07 ||
        !apply_browser_setting(
            &menu, COMPANION_BROWSER_MENU_ITEM_EDGE_PULL) ||
        apply_browser_setting(
            &menu, COMPANION_BROWSER_MENU_ITEM_EDGE_PULL) ||
        !apply_browser_setting(
            &menu, COMPANION_BROWSER_MENU_ITEM_CORNER_DOUBLE_TAP)) {
        return false;
    }
    if (!comp_screen_menu_complete_browser_action(
            &menu, COMPANION_BROWSER_MENU_ITEM_CONNECTION_TOGGLE) ||
        menu.browser.link_connected ||
        !comp_screen_menu_complete_browser_action(
            &menu, COMPANION_BROWSER_MENU_ITEM_CONFIRM_CLEAR) ||
        menu.browser.recording_count != 0u ||
        menu.browser.recording_storage_kb != 0u) {
        return false;
    }
    /* Restore defaults must preserve target-owned hardware truth. */
    menu.browser.link_connected = true;
    menu.browser.natural_blink = false;
    menu.language = COMP_SCREEN_MENU_LANGUAGE_EN;
    if (!comp_screen_menu_complete_browser_action(
            &menu, COMPANION_BROWSER_MENU_ITEM_CONFIRM_RESTORE) ||
        !menu.browser.natural_blink ||
        menu.language != COMP_SCREEN_MENU_LANGUAGE_ZH ||
        !menu.browser.link_connected ||
        menu.browser.recording_count != 0u) {
        return false;
    }
    return true;
}
#endif

void comp_screen_menu_init(comp_screen_menu_t *menu)
{
    if (menu != NULL) {
        *menu = (comp_screen_menu_t){
            .view = COMP_SCREEN_MENU_VIEW_HOME,
            .language = COMP_SCREEN_MENU_LANGUAGE_ZH,
            .revision = 1u,
        };
        browser_defaults(menu, true);
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

static bool browser_back_hit(uint16_t x, uint16_t y)
{
#if COMPANION_WBA_RESOURCE_PROFILE
    /* The retained WBA status strip contains the clock above the title.
     * Only the title's visible arrow owns back; clock/BLE/battery are not
     * menu buttons. Apply the same boundary at DOWN and at release. */
    if (y < 20u) return false;
#endif
    return x <= 40u && y < 45u;
}

#include "customer_menu_runtime.h"

#if COMPANION_WBA_RESOURCE_PROFILE
static uint8_t browser_tap_target(const comp_screen_menu_t *menu,
                                  uint16_t x, uint16_t y)
{
    if (x >= MENU_WIDTH || y >= MENU_HEIGHT) return 0xffu;
    if (browser_back_hit(x, y)) return 0xfeu; /* back/exit */
    if (menu->view == COMP_SCREEN_MENU_VIEW_BROWSER_QUICK) {
        if(x>=COMP_SCREEN_QUICK_MENU_LEFT && x<COMP_SCREEN_QUICK_MENU_RIGHT &&
           y>=COMP_SCREEN_QUICK_MENU_TOP && y<COMP_SCREEN_QUICK_MENU_BOTTOM)return 3u;
        if (x < 12u || x > 188u) return 0xffu;
        if (y >= COMP_SCREEN_QUICK_VOLUME_TOP && y < COMP_SCREEN_QUICK_VOLUME_BOTTOM) return 0u;
        if (y >= COMP_SCREEN_QUICK_ACTIVITY_TOP && y < COMP_SCREEN_QUICK_ACTIVITY_BOTTOM) return 4u;
        if (y >= COMP_SCREEN_QUICK_MUTE_TOP && y < 158u) return 1u;
        if (y >= COMP_SCREEN_QUICK_SETTINGS_TOP && y < 192u) return 2u;
        return 0xffu;
    }
    return browser_hit_index(menu, x, y);
}
#endif

comp_screen_menu_result_t comp_screen_menu_tap_contact(comp_screen_menu_t *menu,
    uint16_t start_x, uint16_t start_y, uint16_t end_x, uint16_t end_y)
{
#if COMPANION_WBA_RESOURCE_PROFILE
    if (menu && comp_screen_menu_is_browser_view(menu->view)) {
        const uint8_t start = browser_tap_target(menu, start_x, start_y);
        if (start == 0xffu || start != browser_tap_target(menu, end_x, end_y)) {
            comp_screen_menu_result_t result = {0};
            menu_result_from_state(menu, &result);
            return result;
        }
    }
#else
    (void)start_x;
    (void)start_y;
#endif
    return comp_screen_menu_tap(menu, end_x, end_y);
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
    if(comp_screen_menu_customer_active() &&
       menu->view!=COMP_SCREEN_MENU_VIEW_BROWSER_QUICK &&
       menu->view!=COMP_SCREEN_MENU_VIEW_BROWSER_PET_HELP)
        return customer_tap(menu,x,y);
    if(menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_QUICK) {
        result.browser_item=255u;
        if(browser_back_hit(x,y)) {
            if(comp_screen_menu_customer_active() && menu->navigation_depth)
                result.changed=comp_screen_menu_back(menu);
            else {result.action=COMP_SCREEN_MENU_ACTION_EXIT_DAILY;result.changed=true;}
        } else if(x>=COMP_SCREEN_QUICK_MENU_LEFT && x<COMP_SCREEN_QUICK_MENU_RIGHT &&
                  y>=COMP_SCREEN_QUICK_MENU_TOP && y<COMP_SCREEN_QUICK_MENU_BOTTOM) {
            result.changed=comp_screen_menu_navigate_to(menu,COMP_SCREEN_MENU_VIEW_BROWSER_HOME);
            menu->navigation_depth=0u;
        } else if(x>=12u && x<=188u) {
            if(y>=COMP_SCREEN_QUICK_VOLUME_TOP && y<COMP_SCREEN_QUICK_VOLUME_BOTTOM)
                return comp_screen_menu_quick_volume(menu,x);
            if(y>=COMP_SCREEN_QUICK_ACTIVITY_TOP && y<COMP_SCREEN_QUICK_ACTIVITY_BOTTOM) {
                /* Reuse the existing three choices: no new state, no hidden
                 * replacement of a user's Lively preference with Standard. */
                if(comp_screen_menu_customer_active())
                    result.changed=comp_screen_menu_navigate_to(menu,
                        (comp_screen_menu_view_t)(COMP_CUSTOMER_CHOICE_BASE+42u));
            } else if(y>=COMP_SCREEN_QUICK_MUTE_TOP && y<158u) {
                result.action=COMP_SCREEN_MENU_ACTION_PET_MUTE_TOGGLE;result.changed=true;
            } else if(y>=COMP_SCREEN_QUICK_SETTINGS_TOP && y<192u) {
                /* An everyday action uses the same real recorder entry as
                 * the original corner gesture. Full settings stay in the
                 * header menu control and original long-hold path. */
                result.action=COMP_SCREEN_MENU_ACTION_RECORD_START;
                result.browser_kind=COMPANION_BROWSER_MENU_KIND_ACTION;
                result.changed=true;
            }
        }
        menu_result_from_state(menu,&result);return result;
    }
    if (comp_screen_menu_is_browser_view(menu->view)) {
        uint8_t absolute_index;
        uint8_t screen_index = browser_screen_index(menu->view);
        uint8_t item_count;
        item_count=browser_item_count(menu->view);
        if(menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_PET_HELP) {
            if(browser_back_hit(x,y))result.changed=comp_screen_menu_back(menu);
            else {
                absolute_index=browser_hit_index(menu,x,y);
                if(absolute_index<3u) {
#if COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 71u
                    if(absolute_index==2u) {
                        /* Open the existing explicit volume/mute controls.
                         * Merely asking to adjust sound must not raise it. */
                        result.changed=comp_screen_menu_navigate_to(menu,COMP_SCREEN_MENU_VIEW_BROWSER_QUICK);
                        result.browser_item=255u;
                        menu_result_from_state(menu,&result);return result;
                    }
#endif
                    result.action=absolute_index==0u?COMP_SCREEN_MENU_ACTION_PET_GREETING:
                        absolute_index==1u?COMP_SCREEN_MENU_ACTION_PET_PLAY:
                        COMP_SCREEN_MENU_ACTION_PET_VOLUME_NEXT;
                    result.browser_item=255u;
                    result.browser_kind=COMPANION_BROWSER_MENU_KIND_ACTION;
                    result.changed=true;
                }
            }
            menu_result_from_state(menu,&result);return result;
        }
#if COMPANION_WBA_RESOURCE_PROFILE
        if (menu->view == COMP_SCREEN_MENU_VIEW_BROWSER_HOME && browser_back_hit(x, y)) {
            result.action = COMP_SCREEN_MENU_ACTION_EXIT_DAILY;
            result.changed = true;
        } else
#endif
        if (menu->view != COMP_SCREEN_MENU_VIEW_BROWSER_HOME &&
            browser_back_hit(x, y)) {
            result.changed = comp_screen_menu_back(menu);
        } else if (y >= 45u) {
            absolute_index = browser_hit_index(menu, x, y);
#if COMPANION_WBA_RESOURCE_PROFILE
            if(menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_INTERACTION && absolute_index==6u) {
                result.changed=comp_screen_menu_navigate_to(menu,COMP_SCREEN_MENU_VIEW_BROWSER_PET_HELP);
                menu_result_from_state(menu,&result);return result;
            }
#endif
            if (absolute_index < item_count) {
#if COMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK
                const companion_browser_menu_row_t *row =
                    companion_browser_menu_row(screen_index,comp_screen_menu_source_row(menu->view,absolute_index));
                if (row == NULL) {
                    menu_result_from_state(menu, &result);
                    return result;
                }
                result.browser_item = row->item;
                result.browser_kind = row->kind;
                /* The WBA display page's former static status-bar row is
                 * now the live battery presentation choice. Other authored
                 * status rows and the WB catalog retain their behavior. */
#if COMPANION_WBA_RESOURCE_PROFILE
                if (row->item == COMPANION_BROWSER_MENU_ITEM_STATUS_BAR)
                    result.browser_kind = COMPANION_BROWSER_MENU_KIND_CYCLE;
#endif
                if (result.browser_kind == COMPANION_BROWSER_MENU_KIND_STATUS) {
                    menu_result_from_state(menu, &result);
                    return result;
                }
                if(menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_VOICE &&
                   row->item==COMPANION_BROWSER_MENU_ITEM_RECORDING_START) {
                    /* The original row navigated to gesture preferences.
                     * Voice now has a real record control; gesture selection
                     * remains separately available under Interaction. */
                    result.browser_kind=COMPANION_BROWSER_MENU_KIND_ACTION;
                    result.action=(menu->flags&COMP_SCREEN_MENU_FLAG_RECORDING)?
                        COMP_SCREEN_MENU_ACTION_RECORD_STOP:COMP_SCREEN_MENU_ACTION_RECORD_START;
                } else if (row->kind == COMPANION_BROWSER_MENU_KIND_NAVIGATE) {
                    (void)comp_screen_menu_navigate_to(
                        menu, (comp_screen_menu_view_t)(
                                  COMP_SCREEN_MENU_VIEW_BROWSER_HOME +
                                  row->target));
                } else if (row->kind == COMPANION_BROWSER_MENU_KIND_BACK) {
                    (void)comp_screen_menu_back(menu);
                } else if (row->kind == COMPANION_BROWSER_MENU_KIND_OPTION &&
                           (row->item == COMPANION_BROWSER_MENU_ITEM_ZH_CN ||
                            row->item == COMPANION_BROWSER_MENU_ITEM_EN
#ifdef COMPANION_WBA_MENU_LANGUAGE_EXTENSION
                            || row->item == COMPANION_BROWSER_MENU_ITEM_ZH_TW
#endif
                            )) {
                    const comp_screen_menu_language_t next_language =
                        row->item == COMPANION_BROWSER_MENU_ITEM_ZH_CN
                            ? COMP_SCREEN_MENU_LANGUAGE_ZH
                            :
#ifdef COMPANION_WBA_MENU_LANGUAGE_EXTENSION
                              row->item == COMPANION_BROWSER_MENU_ITEM_ZH_TW
                                ? COMP_SCREEN_MENU_LANGUAGE_ZH_TW
                                :
#endif
                                  COMP_SCREEN_MENU_LANGUAGE_EN;
                    if (menu->language == next_language) {
                        menu_result_from_state(menu, &result);
                        return result;
                    }
                    menu->language = next_language;
                    result.action = COMP_SCREEN_MENU_ACTION_LANGUAGE_CHANGED;
                } else if (row->kind == COMPANION_BROWSER_MENU_KIND_ACTION) {
                    switch (row->item) {
                    case COMPANION_BROWSER_MENU_ITEM_RECORDING_START:
                        result.action=(menu->flags&COMP_SCREEN_MENU_FLAG_RECORDING)?
                            COMP_SCREEN_MENU_ACTION_RECORD_STOP:COMP_SCREEN_MENU_ACTION_RECORD_START;
                        break;
                    case COMPANION_BROWSER_MENU_ITEM_PAIR:
                        result.action = COMP_SCREEN_MENU_ACTION_BROWSER_PAIR; break;
                    case COMPANION_BROWSER_MENU_ITEM_CONNECTION_TOGGLE:
                        result.action = COMP_SCREEN_MENU_ACTION_BROWSER_CONNECTION_TOGGLE; break;
                    case COMPANION_BROWSER_MENU_ITEM_RESET_NAME:
                        result.action = COMP_SCREEN_MENU_ACTION_BROWSER_RESET_NAME; break;
                    case COMPANION_BROWSER_MENU_ITEM_CONFIRM_CLEAR:
                        result.action = COMP_SCREEN_MENU_ACTION_BROWSER_CLEAR_RECORDINGS; break;
                    case COMPANION_BROWSER_MENU_ITEM_CONFIRM_RESTORE:
                        result.action = COMP_SCREEN_MENU_ACTION_BROWSER_RESTORE_DEFAULTS; break;
                    case COMPANION_BROWSER_MENU_ITEM_SLEEP_NOW:
                        result.action = COMP_SCREEN_MENU_ACTION_BROWSER_SLEEP_NOW; break;
                    default:
                        result.action = COMP_SCREEN_MENU_ACTION_BROWSER_SETTING_CHANGED; break;
                    }
                } else {
                    if (!apply_browser_setting(menu, row->item)) {
                        menu_result_from_state(menu, &result);
                        return result;
                    }
                    result.action = COMP_SCREEN_MENU_ACTION_BROWSER_SETTING_CHANGED;
                }
                if (row->kind != COMPANION_BROWSER_MENU_KIND_NAVIGATE &&
                    row->kind != COMPANION_BROWSER_MENU_KIND_BACK) {
                    menu->revision++;
                }
                result.changed = true;
#else
                comp_screen_menu_view_t target = menu->view;
                if (menu->view == COMP_SCREEN_MENU_VIEW_BROWSER_HOME) {
                    target = s_browser_home_views[absolute_index];
                } else if (menu->view == COMP_SCREEN_MENU_VIEW_BROWSER_VOICE &&
                           absolute_index == 1u) {
                    target = COMP_SCREEN_MENU_VIEW_BROWSER_RECORDING_GESTURE;
                } else if (menu->view == COMP_SCREEN_MENU_VIEW_BROWSER_INTERACTION &&
                           absolute_index == 1u) {
                    target = COMP_SCREEN_MENU_VIEW_BROWSER_RECORDING_GESTURE;
                } else if (menu->view == COMP_SCREEN_MENU_VIEW_BROWSER_PREFERENCES &&
                           absolute_index == 0u) {
                    target = COMP_SCREEN_MENU_VIEW_BROWSER_LANGUAGE;
                } else if (menu->view == COMP_SCREEN_MENU_VIEW_BROWSER_PREFERENCES &&
                           absolute_index == 3u) {
                    target = COMP_SCREEN_MENU_VIEW_BROWSER_RESTORE_DEFAULTS;
                } else if (menu->view == COMP_SCREEN_MENU_VIEW_BROWSER_STORAGE &&
                           absolute_index == 2u) {
                    target = COMP_SCREEN_MENU_VIEW_BROWSER_CLEAR_RECORDINGS;
                } else if (menu->view == COMP_SCREEN_MENU_VIEW_BROWSER_LANGUAGE) {
                    menu->language = absolute_index == 0u
                                         ? COMP_SCREEN_MENU_LANGUAGE_ZH
                                         : COMP_SCREEN_MENU_LANGUAGE_EN;
                    result.action = COMP_SCREEN_MENU_ACTION_LANGUAGE_CHANGED;
                }
                if (target != menu->view) {
                    (void)comp_screen_menu_navigate_to(menu, target);
                } else {
                    menu->revision++;
                }
                result.changed = true;
#endif
            }
        }
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

bool comp_screen_menu_browser_hit_test(const comp_screen_menu_t *menu,
                                       uint16_t x,
                                       uint16_t y,
                                       uint8_t *absolute_index,
                                       uint8_t *item,
                                       uint8_t *kind)
{
#if COMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK
    uint8_t screen;
    uint8_t index;
    const companion_browser_menu_row_t *row;
    if (menu == NULL || absolute_index == NULL || item == NULL || kind == NULL ||
        !comp_screen_menu_is_browser_view(menu->view) || x >= MENU_WIDTH ||
        y < 45u || y >= MENU_HEIGHT) {
        return false;
    }
    screen = browser_screen_index(menu->view);
    index = browser_hit_index(menu, x, y);
    if(comp_screen_menu_customer_active() && menu->view!=COMP_SCREEN_MENU_VIEW_BROWSER_PET_HELP) {
        comp_customer_menu_row_t selected;
        if(!comp_screen_menu_customer_row(menu,index,&selected) || selected.kind==2u)return false;
        *absolute_index=index;*item=selected.item;*kind=selected.kind;return true;
    }
#if COMPANION_WBA_RESOURCE_PROFILE
    if((menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_PET_HELP && index<3u) ||
       (menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_INTERACTION && index==6u)) {
        *absolute_index=index;*item=255u;
        *kind=menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_PET_HELP?
            COMPANION_BROWSER_MENU_KIND_ACTION:COMPANION_BROWSER_MENU_KIND_NAVIGATE;
        return true;
    }
#endif
    row = companion_browser_menu_row(screen,comp_screen_menu_source_row(menu->view,index));
    if (row == NULL || (row->kind == COMPANION_BROWSER_MENU_KIND_STATUS &&
        !(COMPANION_WBA_RESOURCE_PROFILE && row->item==COMPANION_BROWSER_MENU_ITEM_STATUS_BAR))) {
        return false;
    }
    *absolute_index = index;
    *item = row->item;
    *kind = row->kind;
#if COMPANION_WBA_RESOURCE_PROFILE
    if(row->item==COMPANION_BROWSER_MENU_ITEM_STATUS_BAR)*kind=COMPANION_BROWSER_MENU_KIND_CYCLE;
#endif
    if(menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_VOICE &&
       row->item==COMPANION_BROWSER_MENU_ITEM_RECORDING_START)
        *kind=COMPANION_BROWSER_MENU_KIND_ACTION;
    return true;
#else
    (void)menu;
    (void)x;
    (void)y;
    (void)absolute_index;
    (void)item;
    (void)kind;
    return false;
#endif
}

comp_screen_menu_result_t comp_screen_menu_quick_volume(comp_screen_menu_t *menu,uint16_t x)
{
    comp_screen_menu_result_t result={0};
    if(!menu || menu->view!=COMP_SCREEN_MENU_VIEW_BROWSER_QUICK)return result;
    if(x<COMP_SCREEN_QUICK_VOLUME_LEFT)x=COMP_SCREEN_QUICK_VOLUME_LEFT;
    if(x>COMP_SCREEN_QUICK_VOLUME_RIGHT)x=COMP_SCREEN_QUICK_VOLUME_RIGHT;
    const unsigned span=COMP_SCREEN_QUICK_VOLUME_RIGHT-COMP_SCREEN_QUICK_VOLUME_LEFT;
    const uint8_t value=(uint8_t)((((x-COMP_SCREEN_QUICK_VOLUME_LEFT)*4u+span/2u)/span)*25u);
    if(value!=menu->browser.pet_volume) {
        result.action=COMP_SCREEN_MENU_ACTION_PET_VOLUME_SET;
        result.browser_item=255u;result.browser_kind=value;result.changed=true;
    }
    menu_result_from_state(menu,&result);return result;
}

comp_screen_menu_result_t comp_screen_menu_gesture(
    comp_screen_menu_t *menu,
    const comp_touch_gesture_event_t *gesture)
{
    comp_screen_menu_result_t result = {0};

    if (menu == NULL || gesture == NULL) {
        return result;
    }
    if(menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_QUICK) {
        if(gesture->type==COMP_TOUCH_GESTURE_SWIPE_UP ||
           comp_screen_menu_is_exit_gesture(gesture)) {
            if(comp_screen_menu_customer_active() && menu->navigation_depth)
                result.changed=comp_screen_menu_back(menu);
            else {result.action=COMP_SCREEN_MENU_ACTION_EXIT_DAILY;result.changed=true;}
        }
        menu_result_from_state(menu,&result);return result;
    }
    /* Vertical gestures page the WBA root and lists; right always returns
     * one level. A completed contact owns at most one page change. */
    if (comp_screen_menu_is_browser_view(menu->view) &&
        (gesture->type == COMP_TOUCH_GESTURE_SWIPE_UP ||
         gesture->type == COMP_TOUCH_GESTURE_SWIPE_DOWN
        )) {
        uint8_t next_page = menu->home_page;
        uint8_t maximum = browser_scroll_max(menu->view);
        uint8_t step = 1u;
#if COMPANION_WBA_RESOURCE_PROFILE
        step = menu->view == COMP_SCREEN_MENU_VIEW_BROWSER_HOME ? 4u :
            comp_screen_menu_customer_active()?2u:COMP_WBA_MENU_VISIBLE_ROWS;
#endif
        if (gesture->type == COMP_TOUCH_GESTURE_SWIPE_UP && next_page < maximum) {
            next_page = (uint8_t)(next_page + step);
            if (next_page > maximum) next_page = maximum;
        } else if (gesture->type == COMP_TOUCH_GESTURE_SWIPE_DOWN && next_page > 0u) {
            next_page = next_page > step ? (uint8_t)(next_page - step) : 0u;
        }
        if (next_page != menu->home_page) {
#if COMPANION_WBA_RESOURCE_PROFILE
            /* Reuse the legacy scroll field:1/2 is one pending arrive pose,
             * cleared only after a successfully visible transaction. */
            if (!(menu->home_scroll_offset_px & COMP_SCREEN_MENU_SCROLL_SLOW))
                menu->home_scroll_offset_px = next_page > menu->home_page ? 1u : 2u;
#endif
            menu->home_page = next_page;
            menu->revision++;
            result.changed = true;
        }
    } else if (comp_screen_menu_is_exit_gesture(gesture)) {
        if (comp_screen_menu_is_browser_view(menu->view) &&
            menu->view != COMP_SCREEN_MENU_VIEW_BROWSER_HOME) {
            (void)comp_screen_menu_back(menu);
            result.view = menu->view;
            result.home_page = menu->home_page;
            result.revision = menu->revision;
            result.changed = true;
        } else {
            /* The owner performs the single menu-to-daily maintenance
             * boundary only when the browser root itself exits. */
            result.action = COMP_SCREEN_MENU_ACTION_EXIT_DAILY;
            result.changed = true;
        }
    }
    menu_result_from_state(menu, &result);
    return result;
}

comp_screen_menu_result_t comp_screen_menu_browser_drag_from(
    comp_screen_menu_t *menu,
    uint8_t start_page,
    int16_t finger_delta_y,
    uint16_t touch_slop_px,
    uint16_t row_height_px)
{
    comp_screen_menu_result_t result = {0};
    uint16_t distance;
    uint16_t rows;
    uint8_t maximum;
    int16_t destination;

    if (menu == NULL || !comp_screen_menu_is_browser_view(menu->view) ||
        row_height_px == 0u) {
        return result;
    }
#if COMPANION_WBA_RESOURCE_PROFILE
    if (menu->view != COMP_SCREEN_MENU_VIEW_BROWSER_HOME)
        row_height_px = COMP_WBA_MENU_ROW_HEIGHT;
#endif
    distance = (uint16_t)(finger_delta_y < 0
                              ? -(int32_t)finger_delta_y
                              : finger_delta_y);
    if (distance == 0u || distance < touch_slop_px) {
        menu_result_from_state(menu, &result);
        return result;
    }

    /* Row snapping uses the original pointer-down position. This avoids the
     * sampled-delta drift and floor-to-zero dead zone that made a 12--39 px
     * drag feel ignored. Crossing slop always moves at least one row; longer
     * drags round to the nearest row exactly once. */
    rows = (uint16_t)((distance + row_height_px / 2u) / row_height_px);
    if (rows == 0u) {
        rows = 1u;
    }
#if COMPANION_WBA_RESOURCE_PROFILE
    /* Customer lists overlap by two rows; the last offset keeps a full
     * viewport. Root tiles and legacy banks retain their existing paging. */
    rows = menu->view == COMP_SCREEN_MENU_VIEW_BROWSER_HOME ? 4u :
        comp_screen_menu_customer_active()?2u:COMP_WBA_MENU_VISIBLE_ROWS;
#endif
    maximum = browser_scroll_max(menu->view);
    destination = (int16_t)start_page +
                  (finger_delta_y < 0 ? (int16_t)rows : -(int16_t)rows);
    if (destination < 0) {
        destination = 0;
    } else if (destination > (int16_t)maximum) {
        destination = maximum;
    }
    if (menu->home_page != (uint8_t)destination) {
        menu->home_page = (uint8_t)destination;
        menu->revision++;
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

bool comp_screen_menu_render_browser_catalog(comp_screen_menu_view_t view,
                                             uint16_t packed_catalog,
                                             uint8_t *frame,
                                             size_t frame_bytes,
                                             uint16_t width,
                                             uint16_t height)
{
    comp_screen_framebuffer_t framebuffer;
    char value[8];

    if ((view != COMP_SCREEN_MENU_VIEW_BROWSER_STORAGE &&
         view != COMP_SCREEN_MENU_VIEW_BROWSER_CLEAR_RECORDINGS) ||
        width != MENU_WIDTH || height != MENU_HEIGHT ||
        frame_bytes < MENU_FRAME_BYTES ||
        !comp_screen_framebuffer_init(&framebuffer, frame, frame_bytes,
                                      width, height)) {
        return false;
    }

    value[0] = (char)('0' + (packed_catalog & 0x0Fu));
    value[1] = '\0';
    /* Preserve the authored Chinese unit to the right; only its baked digit
     * is replaced. The recording journal has seven slots, so one digit is
     * the complete product range. */
    comp_screen_framebuffer_fill_rect(&framebuffer, 168, 48, 9u, 11u, false);
    comp_screen_framebuffer_draw_text(&framebuffer, 170, 50, value, 1u, true);

    if (view == COMP_SCREEN_MENU_VIEW_BROWSER_STORAGE) {
        (void)snprintf(value, sizeof(value), "%uKB",
                       (unsigned)(packed_catalog >> 4u));
        /* Erase the whole fabricated "384KB / 2MB" value field so shifted
         * glyphs cannot survive, then right-align measured payload usage. */
        comp_screen_framebuffer_fill_rect(&framebuffer, 124, 86, 70u, 16u,
                                          false);
        comp_screen_framebuffer_draw_text(
            &framebuffer,
            (int16_t)(194 - (int16_t)(strlen(value) * 6u)),
            90, value, 1u, true);
    }
    return true;
}

bool comp_screen_menu_render_battery_reading(const char *reading,
                                             uint8_t *frame,
                                             size_t frame_bytes,
                                             uint16_t width,
                                             uint16_t height)
{
    static const uint8_t digits[10][5] = {
        {7u,5u,5u,5u,7u}, {2u,6u,2u,2u,7u},
        {7u,1u,7u,4u,7u}, {7u,1u,7u,1u,7u},
        {5u,5u,7u,1u,1u}, {7u,4u,7u,1u,7u},
        {7u,4u,7u,5u,7u}, {7u,1u,2u,2u,2u},
        {7u,5u,7u,5u,7u}, {7u,5u,7u,1u,7u},
    };
    comp_screen_framebuffer_t framebuffer;
    size_t count = 0u;
    int16_t left;

    if (reading == NULL ||
        width != MENU_WIDTH || height != MENU_HEIGHT ||
        !comp_screen_framebuffer_init(&framebuffer,frame,frame_bytes,width,height)) {
        return false;
    }
    while (reading[count] != '\0') {
        const char ch = reading[count];
        if (count >= 4u || !((ch >= '0' && ch <= '9') ||
                            ch == '~' || ch == '-' || ch == '.' || ch == 'V')) {
            return false;
        }
        ++count;
    }
    if (count == 0u) return false;
    /* Preserve the original outline at (175,4),18x9 and its terminal.
     * Five ink rows leave one pixel of clearance above and below each digit. */
    comp_screen_framebuffer_fill_rect(&framebuffer,176,5,16u,7u,false);
    left = (int16_t)(176u + (16u - (count * 4u - 1u)) / 2u);
    for (size_t index = 0u; index < count; ++index) {
        const char ch = reading[index];
        for (uint16_t row = 0u; row < 5u; ++row) {
            uint8_t ink;
            if (ch >= '0' && ch <= '9') ink = digits[(uint8_t)(ch - '0')][row];
            else if (ch == '~') ink = row == 1u ? 6u : row == 2u ? 3u : 0u;
            else if (ch == '-') ink = row == 2u ? 7u : 0u;
            else if (ch == '.') ink = row == 4u ? 2u : 0u;
            else ink = row < 3u ? 5u : 2u;
            for (uint16_t col = 0u; col < 3u; ++col) {
                if ((ink & (1u << (2u-col))) != 0u) {
                    const int16_t x = (int16_t)(left + index * 4u + col);
                    comp_screen_framebuffer_set_pixel(&framebuffer,x,
                        (int16_t)(6u + row),true);
                }
            }
        }
    }
    return true;
}

bool comp_screen_menu_render_status_bar(uint32_t packed_status,
                                        uint8_t *frame,
                                        size_t frame_bytes,
                                        uint16_t width,
                                        uint16_t height)
{
    comp_screen_framebuffer_t framebuffer;
    char text[6];
    const uint16_t packed_clock = (uint16_t)packed_status;
    const bool clock_valid = (packed_clock & 0x8000u) != 0u;
    const uint8_t hour = (uint8_t)((packed_clock >> 8) & 0x1Fu);
    const uint8_t minute = (uint8_t)(packed_clock & 0x3Fu);
    const bool ble_connected = (packed_status & (1u << 16)) != 0u;
    const bool battery_valid = (packed_status & (1u << 17)) != 0u;
    const uint8_t battery_percent = (uint8_t)(packed_status >> 24u);
    uint16_t fill_width = 0u;

    if ((clock_valid && (hour > 23u || minute > 59u)) ||
        width != MENU_WIDTH || height != MENU_HEIGHT ||
        !comp_screen_framebuffer_init(&framebuffer, frame, frame_bytes,
                                      width, height)) {
        return false;
    }
    if (clock_valid) {
        text[0] = (char)('0' + hour / 10u);
        text[1] = (char)('0' + hour % 10u);
        text[2] = ':';
        text[3] = (char)('0' + minute / 10u);
        text[4] = (char)('0' + minute % 10u);
        text[5] = '\0';
    } else {
        /* This is a product surface, not a diagnostic console. A fresh or
         * power-cycled board cannot know wall time until Type appends UTC to
         * Settings; show the conventional unknown-time form meanwhile. */
        memcpy(text, "--:--", 6u);
    }
    /* The status bar is runtime state, not authored expression art. Rebuild
     * all 16 rows so a clip cannot leak stale clock/link pixels into the next
     * frame. Never touch y=16. */
    memset(frame, 0xFF, 16u * (MENU_WIDTH / 8u));
    /* Free-standing ink and equal edge gutters keep the rail subordinate
     * to the face. A single native 5x7 stroke retains open counters. */
    comp_screen_framebuffer_draw_text(&framebuffer, 6, 5, text, 1u, true);

    /* Separate the disconnected x from the rune so its strokes stay clear
     * at native resolution. Leave room for the real charger indicator. */
    const int16_t ble_x=COMP_SCREEN_STATUS_BLE_CENTER_X;
    comp_screen_framebuffer_draw_line(&framebuffer, ble_x, 2, ble_x, 12, true);
    comp_screen_framebuffer_draw_line(&framebuffer, ble_x, 2, ble_x+4, 5, true);
    comp_screen_framebuffer_draw_line(&framebuffer, ble_x+4, 5, ble_x-4, 11, true);
    comp_screen_framebuffer_draw_line(&framebuffer, ble_x, 12, ble_x+4, 9, true);
    comp_screen_framebuffer_draw_line(&framebuffer, ble_x+4, 9, ble_x-4, 3, true);
    if (!ble_connected) {
        const int16_t link_x=COMP_SCREEN_STATUS_BLE_DISCONNECTED_X;
        comp_screen_framebuffer_draw_line(&framebuffer, link_x, 9, link_x+3, 12, true);
        comp_screen_framebuffer_draw_line(&framebuffer, link_x, 12, link_x+3, 9, true);
    }

    /* Product hardware displays measured 0..100 data. The Nucleo bench has
     * no battery ADC/fuel gauge; Owner 2026-08-17 explicitly selected an 80%
     * screen fallback. GATT remains unavailable so hosts cannot consume it as
     * a measurement. */
    /* Owner wants the original small battery, with either fill or digits.
     * Percent units belong to this icon; the details page retains NN%. */
    comp_screen_framebuffer_stroke_rect(&framebuffer, 175, 4, 18u, 9u,
                                         1u, true);
    comp_screen_framebuffer_fill_rect(&framebuffer, 193, 7, 2u, 3u, true);
    if ((packed_status & COMP_SCREEN_STATUS_CHARGER_FAULT) != 0u) {
        comp_screen_framebuffer_draw_text(&framebuffer, 167, 5, "!", 1u, true);
    } else if ((packed_status & COMP_SCREEN_STATUS_CHARGING) != 0u) {
        /* Active charging needs qualified PG/STAT, not just USB presence.
         * These static marks never start a charging animation on e-paper. */
        comp_screen_framebuffer_draw_line(&framebuffer, 172, 3, 167, 8, true);
        comp_screen_framebuffer_draw_line(&framebuffer, 167, 8, 172, 8, true);
        comp_screen_framebuffer_draw_line(&framebuffer, 172, 8, 168, 12, true);
    } else if ((packed_status & COMP_SCREEN_STATUS_EXTERNAL_POWER) != 0u) {
        comp_screen_framebuffer_draw_line(&framebuffer, 168, 3, 168, 5, true);
        comp_screen_framebuffer_draw_line(&framebuffer, 171, 3, 171, 5, true);
        comp_screen_framebuffer_stroke_rect(&framebuffer, 167, 5, 6, 5, 1, true);
        comp_screen_framebuffer_draw_line(&framebuffer, 170, 10, 170, 12, true);
    }
    if (battery_valid && battery_percent <= 100u) {
        fill_width = (uint16_t)((14u*battery_percent+99u)/100u);
        (void)snprintf(text, sizeof(text), "%u", (unsigned)battery_percent);
    } else if ((packed_status & COMP_SCREEN_STATUS_REQUIRE_MEASURED_BATTERY) != 0u) {
        memcpy(text, "--", 3u);
    } else {
        memcpy(text, "80", 3u);
        fill_width = 12u;
    }
    /* Center only compact digits inside the old outline, including 100.
     * Estimated status remains in the power model and battery details.
     * Unknown product measurements remain --; charger state never fabricates
     * a percentage. Stable ink also avoids a charging animation on e-paper. */
    if ((packed_status & COMP_SCREEN_STATUS_BATTERY_FILL_ONLY) != 0u &&
        ((battery_valid && battery_percent <= 100u) ||
         (packed_status & COMP_SCREEN_STATUS_REQUIRE_MEASURED_BATTERY) == 0u)) {
        comp_screen_framebuffer_fill_rect(&framebuffer,176,5,16u,7u,false);
        /* Keep one white pixel between the original black outline and fill,
         * including at 100%; the compact icon must not become a solid block. */
        if(fill_width != 0u)
            comp_screen_framebuffer_fill_rect(&framebuffer,177,6,fill_width,5u,true);
        return true;
    }
    return comp_screen_menu_render_battery_reading(text,frame,frame_bytes,width,height);
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
#if COMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK
    if (!comp_screen_menu_browser_runtime_self_test()) {
        return false;
    }
#endif
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

    memset(frame, 0xFF, sizeof(frame));
    fingerprint = framebuffer_fingerprint(frame, sizeof(frame));
    if (!comp_screen_menu_render_status_bar(
            (uint32_t)(0x8000u | (12u << 8) | 48u | (1u << 16)),
            frame, sizeof(frame), MENU_WIDTH, MENU_HEIGHT) ||
        framebuffer_fingerprint(frame, sizeof(frame)) == fingerprint ||
        memchr(&frame[16u * (MENU_WIDTH / 8u)], 0x00,
               sizeof(frame) - 16u * (MENU_WIDTH / 8u)) != NULL ||
        !comp_screen_menu_render_status_bar(0u, frame, sizeof(frame),
                                            MENU_WIDTH, MENU_HEIGHT) ||
        comp_screen_menu_render_status_bar(
            (uint32_t)(0x8000u | (24u << 8)),
            frame, sizeof(frame), MENU_WIDTH, MENU_HEIGHT)) {
        return false;
    }

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
#if !COMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK
    /* Host-only physical menu traces: product builds use the generated browser
     * source pack and keep these exhaustive constants out of tight App Flash. */
    comp_screen_menu_init(&menu);
    if (!comp_screen_menu_navigate_to(
            &menu, COMP_SCREEN_MENU_VIEW_BROWSER_HOME)) {
        return false;
    }
    result = comp_screen_menu_browser_drag_from(&menu, 0u, -11, 12u, 40u);
    if (result.changed || result.home_page != 0u) {
        return false;
    }
    result = comp_screen_menu_browser_drag_from(&menu, 0u, -12, 12u, 40u);
    if (!result.changed || result.home_page != 1u) {
        return false;
    }
    result = comp_screen_menu_browser_drag_from(&menu, 0u, -78, 12u, 40u);
    if (!result.changed || result.home_page != 2u) {
        return false;
    }
    result = comp_screen_menu_browser_drag_from(&menu, 2u, 22, 12u, 40u);
    if (!result.changed || result.home_page != 1u) {
        return false;
    }
    result = comp_screen_menu_browser_drag_from(&menu, 0u, -199, 12u, 40u);
    if (!result.changed || result.home_page != 4u) {
        return false;
    }
#endif
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
