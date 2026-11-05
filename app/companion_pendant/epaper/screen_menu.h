#ifndef COMPANION_EPAPER_SCREEN_MENU_H
#define COMPANION_EPAPER_SCREEN_MENU_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "touch_gesture.h"
#include "../runtime/generated/companion_customer_menu_contract.h"

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
    COMP_SCREEN_MENU_VIEW_BROWSER_HOME = 16u,
    COMP_SCREEN_MENU_VIEW_BROWSER_VOICE = 17u,
    COMP_SCREEN_MENU_VIEW_BROWSER_DISPLAY = 18u,
    COMP_SCREEN_MENU_VIEW_BROWSER_CONNECTION = 19u,
    COMP_SCREEN_MENU_VIEW_BROWSER_PREFERENCES = 20u,
    COMP_SCREEN_MENU_VIEW_BROWSER_RECORDING_GESTURE = 21u,
    COMP_SCREEN_MENU_VIEW_BROWSER_LANGUAGE = 22u,
    COMP_SCREEN_MENU_VIEW_BROWSER_ABOUT = 23u,
    COMP_SCREEN_MENU_VIEW_BROWSER_INTERACTION = 24u,
    COMP_SCREEN_MENU_VIEW_BROWSER_STORAGE = 25u,
    COMP_SCREEN_MENU_VIEW_BROWSER_POWER = 26u,
    COMP_SCREEN_MENU_VIEW_BROWSER_CLEAR_RECORDINGS = 27u,
    COMP_SCREEN_MENU_VIEW_BROWSER_RESTORE_DEFAULTS = 28u,
    COMP_SCREEN_MENU_VIEW_BROWSER_PET_HELP = 29u,
    COMP_SCREEN_MENU_VIEW_BROWSER_QUICK = 30u,
} comp_screen_menu_view_t;

typedef enum {
    COMP_SCREEN_MENU_LANGUAGE_EN = 0u,
    COMP_SCREEN_MENU_LANGUAGE_ZH = 1u,
    COMP_SCREEN_MENU_LANGUAGE_ZH_TW = 2u,
} comp_screen_menu_language_t;

typedef enum {
    COMP_SCREEN_MENU_ACTION_NONE = 0u,
    COMP_SCREEN_MENU_ACTION_RECORD_START = 1u,
    COMP_SCREEN_MENU_ACTION_RECORD_STOP = 2u,
    COMP_SCREEN_MENU_ACTION_LANGUAGE_CHANGED = 3u,
    COMP_SCREEN_MENU_ACTION_PHONE_RECONNECT = 4u,
    /* The target application owns the daily surface and performs the clean
     * menu-to-daily transition after this portable menu action. */
    COMP_SCREEN_MENU_ACTION_EXIT_DAILY = 5u,
    COMP_SCREEN_MENU_ACTION_BROWSER_SETTING_CHANGED = 6u,
    COMP_SCREEN_MENU_ACTION_BROWSER_PAIR = 7u,
    COMP_SCREEN_MENU_ACTION_BROWSER_CONNECTION_TOGGLE = 8u,
    COMP_SCREEN_MENU_ACTION_BROWSER_RESET_NAME = 9u,
    COMP_SCREEN_MENU_ACTION_BROWSER_CLEAR_RECORDINGS = 10u,
    COMP_SCREEN_MENU_ACTION_BROWSER_RESTORE_DEFAULTS = 11u,
    COMP_SCREEN_MENU_ACTION_BROWSER_SLEEP_NOW = 12u,
    /* Internal verified preference effect; no new menu coordinates/wire ID. */
    COMP_SCREEN_MENU_ACTION_PET_DISCOVERY_SEEN = 13u,
    COMP_SCREEN_MENU_ACTION_PET_GREETING = 14u,
    COMP_SCREEN_MENU_ACTION_PET_VOLUME_NEXT = 15u,
    /* Local preference actions; browser_kind carries the exact volume. */
    COMP_SCREEN_MENU_ACTION_PET_VOLUME_SET = 16u,
    COMP_SCREEN_MENU_ACTION_PET_MUTE_TOGGLE = 17u,
    COMP_SCREEN_MENU_ACTION_PET_PLAY = 18u,
    COMP_SCREEN_MENU_ACTION_PET_QUIET_TIMER = 19u, /* Local transient policy, never NVM/wire. */
} comp_screen_menu_action_t;

typedef enum {
    COMP_SCREEN_MENU_PHONE_RECONNECT_IDLE = 0u,
    COMP_SCREEN_MENU_PHONE_RECONNECT_ADVERTISING = 1u,
    COMP_SCREEN_MENU_PHONE_RECONNECT_CONNECTED = 2u,
    COMP_SCREEN_MENU_PHONE_RECONNECT_FAILED = 3u,
} comp_screen_menu_phone_reconnect_state_t;

typedef enum {
    COMP_SCREEN_MENU_RECORDER_PROFILE_VOICE = 0u,
    COMP_SCREEN_MENU_RECORDER_PROFILE_MEETING = 1u,
} comp_screen_menu_recorder_profile_t;

typedef enum {
    COMP_SCREEN_MENU_INTERACTION_QUIET = 0u,
    COMP_SCREEN_MENU_INTERACTION_STANDARD = 1u,
    COMP_SCREEN_MENU_INTERACTION_LIVELY = 2u,
} comp_screen_menu_interaction_level_t;

typedef enum {
    COMP_SCREEN_MENU_QUIET_HOURS_23_07 = 0u,
    COMP_SCREEN_MENU_QUIET_HOURS_22_08 = 1u,
    COMP_SCREEN_MENU_QUIET_HOURS_OFF = 2u,
} comp_screen_menu_quiet_hours_t;

typedef enum {
    COMP_SCREEN_MENU_RECORDING_GESTURE_CORNER_DOUBLE_TAP = 0u,
    COMP_SCREEN_MENU_RECORDING_GESTURE_EDGE_PULL = 1u,
} comp_screen_menu_recording_gesture_t;

typedef struct {
    bool link_connected;
    bool silent_auto_stop;
    bool auto_reconnect;
    bool clock_24_hour;
    bool gaze_follow;
    bool natural_blink;
    uint8_t auto_sleep_minutes;
    uint8_t recording_limit_minutes;
    uint8_t recorder_profile;
    uint8_t interaction_level;
    uint8_t quiet_hours;
    uint8_t recording_gesture;
    int16_t time_zone_offset_minutes;
    uint16_t recording_count;
    uint16_t recording_storage_kb;
    uint8_t battery_percent;
    bool battery_fill; /* false: numeric; true: fill icon, without digits. */
    uint8_t pet_volume; /* Backend readback value; selection is not optimistic. */
    bool pet_muted; /* Persisted manual mute/zero, separate from quiet hours. */
} comp_screen_menu_browser_state_t;

enum {
    COMP_SCREEN_MENU_FLAG_RECORDING = 1u << 0,
    COMP_SCREEN_MENU_FLAG_TOUCH_OK = 1u << 1,
    COMP_SCREEN_MENU_FLAG_BLE_CONNECTED = 1u << 2,
    COMP_SCREEN_MENU_FLAG_PRESS_ACTIVE = 1u << 3,
    COMP_SCREEN_MENU_FLAG_PRESS_ITEM_SHIFT = 4u,
    COMP_SCREEN_MENU_FLAG_PRESS_ITEM_MASK = 7u << COMP_SCREEN_MENU_FLAG_PRESS_ITEM_SHIFT,
    COMP_SCREEN_MENU_FLAG_ACTION_RESULT = 1u << 7,
};

#define COMP_SCREEN_MENU_ITEM_COUNT 6u
#define COMP_SCREEN_MENU_VISIBLE_ITEMS 6u
/* Daily taps and strokes belong to the pet. A deliberate three-second hold anywhere
 * becomes navigation; precise taps and strokes keep driving pet expression
 * reactions without teaching the user a narrow hit target. */
#define COMP_SCREEN_MENU_ENTER_CENTER_MIN_X 40u
#define COMP_SCREEN_MENU_ENTER_CENTER_MAX_X 160u
#define COMP_SCREEN_MENU_ENTER_CENTER_MIN_Y 40u
#define COMP_SCREEN_MENU_ENTER_CENTER_MAX_Y 160u
/* menu-v3 fits the owner-approved six destinations on one 200x200 sheet.
 * Keep a one-frame interface so an old drag request cannot select a retired
 * CEMP scroll bitmap. */
#define COMP_SCREEN_MENU_HEADER_HEIGHT_PX 28u
#define COMP_SCREEN_MENU_HOME_CONTENT_TOP_PX 35u
#define COMP_SCREEN_MENU_HOME_PET_PANEL_HEIGHT_PX 0u
#define COMP_SCREEN_MENU_HOME_ITEM_STEP_PX 26u
#define COMP_SCREEN_MENU_SCROLL_QUANTUM_PX 1u
#define COMP_SCREEN_MENU_SCROLL_MAX_PX 0u
#define COMP_SCREEN_MENU_SCROLL_FRAME_COUNT 1u
/* The generated product tree is currently two levels below browser home.
 * Keep spare depth for future screens while bounding the WB55 RAM cost. */
#define COMP_SCREEN_MENU_NAV_HISTORY_DEPTH 4u
/* Shared drawing/hit geometry, in native200 coordinates. */
#define COMP_SCREEN_QUICK_PULL_MIN_X 148u
#define COMP_SCREEN_QUICK_PULL_MAX_Y 24u
#define COMP_SCREEN_QUICK_VOLUME_LEFT 16u
#define COMP_SCREEN_QUICK_VOLUME_RIGHT 184u
#define COMP_SCREEN_QUICK_VOLUME_TOP 68u
#define COMP_SCREEN_QUICK_VOLUME_BOTTOM 105u
/* Drag ownership follows the visible track/thumb, not the numeric ticks
 * below it. The wider tap target remains available for discrete choices. */
#define COMP_SCREEN_QUICK_VOLUME_DRAG_BOTTOM 92u
#define COMP_SCREEN_QUICK_ACTIVITY_TOP 108u
#define COMP_SCREEN_QUICK_ACTIVITY_BOTTOM 132u
#define COMP_SCREEN_QUICK_MUTE_TOP 134u
#define COMP_SCREEN_QUICK_SETTINGS_TOP 164u
#define COMP_SCREEN_QUICK_MENU_LEFT 156u
#define COMP_SCREEN_QUICK_MENU_RIGHT 192u
#define COMP_SCREEN_QUICK_MENU_TOP 20u
#define COMP_SCREEN_QUICK_MENU_BOTTOM 45u
/* WBA reuses the old scroll-offset slot; no resident state/frame is added. */
#define COMP_SCREEN_MENU_SCROLL_ARRIVAL_MASK 3u
#define COMP_SCREEN_MENU_SCROLL_SLOW 0x8000u

typedef struct {
    comp_screen_menu_view_t view;
    comp_screen_menu_language_t language;
    uint16_t home_scroll_offset_px;
    uint8_t home_page;
    uint8_t navigation_depth;
    uint8_t navigation_views[COMP_SCREEN_MENU_NAV_HISTORY_DEPTH];
    uint8_t navigation_pages[COMP_SCREEN_MENU_NAV_HISTORY_DEPTH];
    uint8_t flags;
    uint32_t revision;
    comp_screen_menu_browser_state_t browser;
} comp_screen_menu_t;

typedef struct {
    bool changed;
    comp_screen_menu_action_t action;
    comp_screen_menu_view_t view;
    comp_screen_menu_language_t language;
    uint8_t home_page;
    uint8_t flags;
    uint8_t browser_item;
    uint8_t browser_kind;
    uint32_t revision;
} comp_screen_menu_result_t;

void comp_screen_menu_init(comp_screen_menu_t *menu);
void comp_screen_menu_set_flags(comp_screen_menu_t *menu, uint8_t flags);
void comp_screen_menu_set_phone_reconnect_state(
    comp_screen_menu_t *menu,
    comp_screen_menu_phone_reconnect_state_t state);
void comp_screen_menu_restore_browser_defaults(comp_screen_menu_t *menu);
bool comp_screen_menu_complete_browser_action(comp_screen_menu_t *menu,
                                              uint8_t browser_item);
uint8_t comp_screen_menu_browser_variant(const comp_screen_menu_t *menu);
uint8_t comp_screen_menu_with_ble_flag(uint8_t flags, bool connected);
bool comp_screen_menu_is_daily_entry_gesture(
    const comp_touch_gesture_event_t *gesture);
bool comp_screen_menu_is_exit_gesture(
    const comp_touch_gesture_event_t *gesture);
bool comp_screen_menu_is_browser_view(comp_screen_menu_view_t view);
bool comp_screen_menu_is_home_view(comp_screen_menu_view_t view);
/* WBA page position for the native vertical scrollbar. Single sheets return1. */
uint8_t comp_screen_menu_browser_page_count(comp_screen_menu_view_t view);
/* UI84 customer menu; retained backend IDs and existing navigation storage. */
bool comp_screen_menu_customer_active(void);
uint8_t comp_screen_menu_customer_count(comp_screen_menu_view_t view);
bool comp_screen_menu_customer_row(const comp_screen_menu_t *, uint8_t, comp_customer_menu_row_t *);
uint8_t comp_screen_menu_customer_title(const comp_screen_menu_t *);
uint8_t comp_screen_menu_customer_value(const comp_screen_menu_t *, uint8_t item);
bool comp_screen_menu_customer_checked(const comp_screen_menu_t *, uint8_t item);
uint8_t comp_screen_menu_customer_setting_value(const comp_screen_menu_t *,uint8_t item);
bool comp_screen_menu_customer_restore_value(comp_screen_menu_t *,uint8_t item,uint8_t value);
bool comp_screen_menu_navigate_to(comp_screen_menu_t *menu,
                                  comp_screen_menu_view_t target);
bool comp_screen_menu_back(comp_screen_menu_t *menu);
comp_screen_menu_result_t comp_screen_menu_tap(comp_screen_menu_t *menu,
                                               uint16_t x,
                                               uint16_t y);
/* WBA browser taps must start and end on the same visible control. Relative
 * swipes and the quick volume drag retain their separate ownership policy. */
comp_screen_menu_result_t comp_screen_menu_tap_contact(comp_screen_menu_t *menu,
    uint16_t start_x, uint16_t start_y, uint16_t end_x, uint16_t end_y);
/* Release-only choice. Never changes the displayed backend readback itself. */
comp_screen_menu_result_t comp_screen_menu_quick_volume(comp_screen_menu_t *menu,
                                                        uint16_t x);
comp_screen_menu_result_t comp_screen_menu_gesture(
    comp_screen_menu_t *menu,
    const comp_touch_gesture_event_t *gesture);
/* Discrete e-paper equivalent of a mature touch scroller: once the caller has
 * crossed its touch-slop, derive the row-aligned destination from the original
 * pointer-down page instead of repeatedly accumulating sampled deltas. */
comp_screen_menu_result_t comp_screen_menu_browser_drag_from(
    comp_screen_menu_t *menu,
    uint8_t start_page,
    int16_t finger_delta_y,
    uint16_t touch_slop_px,
    uint16_t row_height_px);
comp_screen_menu_result_t comp_screen_menu_drag(comp_screen_menu_t *menu,
                                                 int16_t finger_delta_y);
comp_screen_menu_result_t comp_screen_menu_drag_to(comp_screen_menu_t *menu,
                                                   int32_t home_scroll_offset_px);
/* Logical menu row -> retained native resource/catalog row. Both hit testing
 * and painting use this map; technical information remains in the same page. */
uint8_t comp_screen_menu_source_row(comp_screen_menu_view_t view,uint8_t logical);
bool comp_screen_menu_home_hit_test(const comp_screen_menu_t *menu,
                                    uint16_t x,
                                    uint16_t y,
                                    uint8_t *item,
                                    comp_screen_menu_view_t *view);
bool comp_screen_menu_browser_hit_test(const comp_screen_menu_t *menu,
                                       uint16_t x,
                                       uint16_t y,
                                       uint8_t *absolute_index,
                                       uint8_t *item,
                                       uint8_t *kind);
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
bool comp_screen_menu_render_browser_catalog(comp_screen_menu_view_t view,
                                             uint16_t packed_catalog,
                                             uint8_t *frame,
                                             size_t frame_bytes,
                                             uint16_t width,
                                             uint16_t height);
/* Low 16 bits use Companion_App_StatusClockPacked. bit16=BLE connected,
 * bit17=battery measurement valid, bits31:24=battery percent. If bit17 is
 * clear on the Nucleo bench, render the Owner-selected 80% screen fallback;
 * GATT still reports unavailable and product builds use measurement. */
bool comp_screen_menu_render_status_bar(uint32_t packed_status,
                                        uint8_t *frame,
                                        size_t frame_bytes,
                                        uint16_t width,
                                        uint16_t height);
/* Native200px rail: time at left, one central context, link beside power.
 * The original battery at175,4 remains the right-hand anchor. */
#define COMP_SCREEN_STATUS_CONTEXT_CENTER_X 100
#define COMP_SCREEN_STATUS_BLE_CENTER_X 154
#define COMP_SCREEN_STATUS_BLE_DISCONNECTED_X 161
/* Compact native 3x5 readings fit inside the original 18x9 battery outline.
 * Up to four characters: digits, ~, -, decimal point and V. This also lets
 * a voltage-only reading reuse the same inner field without moving the icon. */
bool comp_screen_menu_render_battery_reading(const char *reading,
                                             uint8_t *frame,
                                             size_t frame_bytes,
                                             uint16_t width,
                                             uint16_t height);
/* Bit13 is unused by the hour/minute clock codec. Runtime supplies this
 * presentation flag from the persisted local display preference. */
#define COMP_SCREEN_STATUS_BATTERY_FILL_ONLY (1u << 13)
/* Product boards must opt out of the legacy Nucleo 80% battery illustration.
 * Default is black numeric ink on white, with ~ for an estimate. Optional
 * fill-only mode never overlays digits. Unknown always has --, not 0. */
#define COMP_SCREEN_STATUS_REQUIRE_MEASURED_BATTERY (1u << 18)
#define COMP_SCREEN_STATUS_EXTERNAL_POWER (1u << 19)
#define COMP_SCREEN_STATUS_CHARGER_FAULT (1u << 20)
#define COMP_SCREEN_STATUS_ESTIMATED_BATTERY (1u << 21)
/* These cues follow qualified charger feedback and the live update lease.
 * External power alone does not mean the battery is actively charging. */
#define COMP_SCREEN_STATUS_CHARGING (1u << 22)
#define COMP_SCREEN_STATUS_UPDATING (1u << 23)
bool comp_screen_menu_self_test(void);
bool comp_screen_menu_v2_self_test(void);
#if COMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK
bool comp_screen_menu_browser_runtime_self_test(void);
#endif

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_SCREEN_MENU_H */
