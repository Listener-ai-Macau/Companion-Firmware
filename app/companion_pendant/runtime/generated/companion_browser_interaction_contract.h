#ifndef COMPANION_BROWSER_INTERACTION_CONTRACT_H
#define COMPANION_BROWSER_INTERACTION_CONTRACT_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

/* Generated browser base + tools/wba_menu_locale_contract.py (COMP-REQ-792).
 * PAGE/CONTRACT hashes below identify the retained base, not this extension. */
#define COMPANION_WBA_MENU_LANGUAGE_EXTENSION 1u
#define COMPANION_BROWSER_INTERACTION_PAGE_SHA256 "3099CAD055491F5D2E609F6F38851EC90652491CEFCE027DCC930D0EB49FF0A0"
#define COMPANION_BROWSER_INTERACTION_CONTRACT_SHA256 "60CAAB53A192EE91D8ED4D421021F2EBF9E712F8A0A6C7F9529DF5BA8298E36F"
#define COMPANION_BROWSER_INTERACTION_SCORE_FUNCTION_SHA256 "7FD47EAEA4B1C6CD1717327D33B93A5A04D3ECEC2AD21D801D5F2298E549EC78"
#define COMPANION_BROWSER_INTERACTION_EVENT_FUNCTION_SHA256 "3AB2301B642FE572299254DE45C955880AB9C75C45809F68813D3430FE6ABF37"
#define COMPANION_BROWSER_INTERACTION_PRODUCT_RESOURCE_ID "B07892037FF33928733ECE88E1080C4D30F4A592F003F46C0F613E29FF85E202"
#define COMPANION_BROWSER_INTERACTION_DOUBLE_TAP_GAP_MS 350u
#define COMPANION_BROWSER_INTERACTION_DOUBLE_TAP_MAX_DISTANCE_200 32u
#define COMPANION_BROWSER_INTERACTION_MENU_HOLD_MS 3000u
#define COMPANION_BROWSER_INTERACTION_MENU_HOLD_RECOGNITION_MS 1000u
#define COMPANION_BROWSER_INTERACTION_RECORDING_CORNER_MAX_X_200 48u
#define COMPANION_BROWSER_INTERACTION_RECORDING_CORNER_MIN_Y_200 136u
#define COMPANION_BROWSER_INTERACTION_EVIDENCE_WINDOW_MS 2400u
#define COMPANION_BROWSER_INTERACTION_SWITCH_THRESHOLD 2u
#define COMPANION_BROWSER_BLINK_CADENCE_MS 480u
#define COMPANION_BROWSER_BLINK_FIRST_INTERVAL_COMMITS 24u
#define COMPANION_BROWSER_INTERACTION_ZONE_UP_Y_200 60u
#define COMPANION_BROWSER_INTERACTION_ZONE_DOWN_Y_200 144u
#define COMPANION_BROWSER_INTERACTION_ZONE_LEFT_X_200 76u
#define COMPANION_BROWSER_INTERACTION_ZONE_RIGHT_X_200 124u
#define COMPANION_BROWSER_INTERACTION_MENU_RIGHT_EXIT_THRESHOLD_200 36u
#define COMPANION_BROWSER_INTERACTION_MENU_VERTICAL_SWIPE_THRESHOLD_200 24u
#define COMPANION_BROWSER_INTERACTION_MENU_SCROLL_CADENCE_MS 500u
#define COMPANION_BROWSER_INTERACTION_MENU_SCROLL_QUANTUM_PX 10u
#define COMPANION_BROWSER_INTERACTION_MENU_ROW_HEIGHT_PX 40u
#define COMPANION_BROWSER_INTERACTION_POINTER_GRID_WIDTH 9u
#define COMPANION_BROWSER_INTERACTION_POINTER_GRID_HEIGHT 9u
#define COMPANION_BROWSER_INTERACTION_POINTER_FOLLOW_CADENCE_MS 480u
#define COMPANION_BROWSER_INTERACTION_POINTER_FOLLOW_MAX_STEP_PX_PER_AXIS 2u
#define COMPANION_BROWSER_INTERACTION_POINTER_FOLLOW_RELEASE_RETURN_COMMITS 2u
#define COMPANION_BROWSER_INTERACTION_RECORDING_TRIGGER_DX_200 36u
#define COMPANION_BROWSER_INTERACTION_RECORDING_MAX_DY_200 24u
#define COMPANION_BROWSER_INTERACTION_RECORDING_MIN_HOLD_MS 120u
#define COMPANION_BROWSER_INTERACTION_RECORDING_VISIBLE_STAGES 4u
#define COMPANION_BROWSER_INTERACTION_RECORDING_VISIBLE_CADENCE_MS 480u
#define COMPANION_BROWSER_INTERACTION_SCORE_SCALE 20
#define COMPANION_BROWSER_INTERACTION_HAS_EDGE_CLIPS 1
#define COMPANION_BROWSER_INTERACTION_EDGE_CLIP_COUNT 37u
#define COMPANION_BROWSER_INTERACTION_HAS_EDGE_STATES 1
#define COMPANION_BROWSER_INTERACTION_EDGE_STATE_COUNT 37u
#define COMPANION_BROWSER_INTERACTION_EDGE_PHASE_COUNT 5u
#define COMPANION_BROWSER_INTERACTION_TRACE_COUNT 8u
#define COMPANION_BROWSER_INTERACTION_MENU_HOLD_MILESTONE_COUNT 4u
#define COMPANION_BROWSER_INTERACTION_HAS_PRODUCT_GENERATION 1
#define COMPANION_BROWSER_INTERACTION_POINTER_STATE_COUNT 250u
#define COMPANION_BROWSER_INTERACTION_MENU_STATE_COUNT 2110u
#define COMPANION_BROWSER_MENU_SCREEN_COUNT 13u
#define COMPANION_BROWSER_MENU_ROW_COUNT 64u
#define COMPANION_BROWSER_MENU_VISIBLE_ROWS 4u
#define COMPANION_BROWSER_MENU_ROW_HEIGHT_PX 40u
#define COMPANION_BROWSER_MENU_TAP_ACK_MS 500u
#define COMPANION_BROWSER_MENU_ACTION_PROCESSING_MS 700u
#define COMPANION_BROWSER_INTERACTION_PRODUCT_LIFE_FAMILY_MASK 0x03FFu
#define COMPANION_BROWSER_INTERACTION_AWAKE_LIFE_CONTINUOUS 1
#define COMPANION_BROWSER_BLINK_INTERVAL_COUNT 3u

typedef struct {
  uint8_t x;
  uint8_t y;
  uint8_t width;
  uint8_t height;
} companion_browser_blink_eye_box_t;

typedef struct {
  int8_t x;
  int8_t y;
} companion_browser_blink_eye_pixel_t;

typedef struct {
  int8_t x;
  int8_t y;
} companion_browser_affect_center_t;

typedef struct {
  uint16_t x;
  uint16_t y;
  uint8_t target_family;
  uint8_t family_after;
  uint8_t transition;
  uint8_t evidence_after;
} companion_browser_interaction_trace_step_t;

typedef struct {
  uint16_t held_ms;
  const char *state_id;
} companion_browser_menu_hold_milestone_t;

typedef enum {
  COMPANION_BROWSER_MENU_KIND_NONE = 0u,
  COMPANION_BROWSER_MENU_KIND_NAVIGATE = 1u,
  COMPANION_BROWSER_MENU_KIND_STATUS = 2u,
  COMPANION_BROWSER_MENU_KIND_ACTION = 3u,
  COMPANION_BROWSER_MENU_KIND_OPTION = 4u,
  COMPANION_BROWSER_MENU_KIND_TOGGLE = 5u,
  COMPANION_BROWSER_MENU_KIND_CYCLE = 6u,
  COMPANION_BROWSER_MENU_KIND_BACK = 7u,
} companion_browser_menu_kind_t;

typedef enum {
  COMPANION_BROWSER_MENU_ITEM_NONE = 0u,
  COMPANION_BROWSER_MENU_ITEM_VOICE = 1u,
  COMPANION_BROWSER_MENU_ITEM_DISPLAY = 2u,
  COMPANION_BROWSER_MENU_ITEM_INTERACTION = 3u,
  COMPANION_BROWSER_MENU_ITEM_CONNECTION = 4u,
  COMPANION_BROWSER_MENU_ITEM_STORAGE_ROOT = 5u,
  COMPANION_BROWSER_MENU_ITEM_POWER = 6u,
  COMPANION_BROWSER_MENU_ITEM_PREFERENCES = 7u,
  COMPANION_BROWSER_MENU_ITEM_ABOUT = 8u,
  COMPANION_BROWSER_MENU_ITEM_RECORDING_STATUS = 9u,
  COMPANION_BROWSER_MENU_ITEM_RECORDING_START = 10u,
  COMPANION_BROWSER_MENU_ITEM_RECORDER_PROFILE = 11u,
  COMPANION_BROWSER_MENU_ITEM_RECORDING_LIMIT = 12u,
  COMPANION_BROWSER_MENU_ITEM_AUTO_STOP = 13u,
  COMPANION_BROWSER_MENU_ITEM_AUDIO_FORMAT = 14u,
  COMPANION_BROWSER_MENU_ITEM_MICROPHONE = 15u,
  COMPANION_BROWSER_MENU_ITEM_CLOCK_FORMAT = 16u,
  COMPANION_BROWSER_MENU_ITEM_EPAPER = 17u,
  COMPANION_BROWSER_MENU_ITEM_RESOLUTION = 18u,
  COMPANION_BROWSER_MENU_ITEM_STATUS_BAR = 19u,
  COMPANION_BROWSER_MENU_ITEM_LINK_STATUS = 20u,
  COMPANION_BROWSER_MENU_ITEM_PAIR = 21u,
  COMPANION_BROWSER_MENU_ITEM_CONNECTION_TOGGLE = 22u,
  COMPANION_BROWSER_MENU_ITEM_AUTO_RECONNECT = 23u,
  COMPANION_BROWSER_MENU_ITEM_DEVICE_NAME = 24u,
  COMPANION_BROWSER_MENU_ITEM_RESET_NAME = 25u,
  COMPANION_BROWSER_MENU_ITEM_BLUETOOTH = 26u,
  COMPANION_BROWSER_MENU_ITEM_LANGUAGE = 27u,
  COMPANION_BROWSER_MENU_ITEM_TIME_ZONE = 28u,
  COMPANION_BROWSER_MENU_ITEM_QUIET_HOURS = 29u,
  COMPANION_BROWSER_MENU_ITEM_RESTORE_DEFAULTS = 30u,
  COMPANION_BROWSER_MENU_ITEM_CORNER_DOUBLE_TAP = 31u,
  COMPANION_BROWSER_MENU_ITEM_EDGE_PULL = 32u,
  COMPANION_BROWSER_MENU_ITEM_ZH_CN = 33u,
  COMPANION_BROWSER_MENU_ITEM_EN = 34u,
  COMPANION_BROWSER_MENU_ITEM_ZH_TW = 62u,
  COMPANION_BROWSER_MENU_ITEM_PRODUCT = 35u,
  COMPANION_BROWSER_MENU_ITEM_FIRMWARE = 36u,
  COMPANION_BROWSER_MENU_ITEM_UI_VERSION = 37u,
  COMPANION_BROWSER_MENU_ITEM_OTA_READINESS = 38u,
  COMPANION_BROWSER_MENU_ITEM_DEVICE_ID = 39u,
  COMPANION_BROWSER_MENU_ITEM_TOUCH = 40u,
  COMPANION_BROWSER_MENU_ITEM_RECORDING_GESTURE = 41u,
  COMPANION_BROWSER_MENU_ITEM_INTERACTION_LEVEL = 42u,
  COMPANION_BROWSER_MENU_ITEM_GAZE_FOLLOW = 43u,
  COMPANION_BROWSER_MENU_ITEM_NATURAL_BLINK = 44u,
  COMPANION_BROWSER_MENU_ITEM_MENU_HOLD = 45u,
  COMPANION_BROWSER_MENU_ITEM_RECORDING_COUNT = 46u,
  COMPANION_BROWSER_MENU_ITEM_STORAGE_USED = 47u,
  COMPANION_BROWSER_MENU_ITEM_CLEAR_RECORDINGS = 48u,
  COMPANION_BROWSER_MENU_ITEM_STORAGE_MEDIUM = 49u,
  COMPANION_BROWSER_MENU_ITEM_RECORDING_STORAGE = 50u,
  COMPANION_BROWSER_MENU_ITEM_STORAGE = 51u,
  COMPANION_BROWSER_MENU_ITEM_BATTERY_LEVEL = 52u,
  COMPANION_BROWSER_MENU_ITEM_CHARGE_STATE = 53u,
  COMPANION_BROWSER_MENU_ITEM_AUTO_SLEEP = 54u,
  COMPANION_BROWSER_MENU_ITEM_SLEEP_NOW = 55u,
  COMPANION_BROWSER_MENU_ITEM_WAKE_METHOD = 56u,
  COMPANION_BROWSER_MENU_ITEM_ALL_RECORDINGS = 57u,
  COMPANION_BROWSER_MENU_ITEM_CONFIRM_CLEAR = 58u,
  COMPANION_BROWSER_MENU_ITEM_CANCEL = 59u,
  COMPANION_BROWSER_MENU_ITEM_DEFAULTS_SUMMARY = 60u,
  COMPANION_BROWSER_MENU_ITEM_CONFIRM_RESTORE = 61u,
} companion_browser_menu_item_t;

typedef struct {
  uint8_t screen;
  uint8_t index;
  uint8_t kind;
  uint8_t target;
  uint8_t item;
} companion_browser_menu_row_t;

typedef struct {
  uint8_t source_family;
  uint8_t target_family;
  const char *zone_clips[5];
} companion_browser_interaction_edge_clip_t;

typedef struct {
  uint8_t source_family;
  uint8_t target_family;
  const char *zone_phase_states[5][5];
} companion_browser_interaction_edge_state_t;

static const char *const companion_browser_tap_local_state_ids[10][5] = {
  {"tap_local_calm_center", "tap_local_calm_up", "tap_local_calm_down", "tap_local_calm_left", "tap_local_calm_right"}, /* calm */
  {"tap_local_curious_center", "tap_local_curious_up", "tap_local_curious_down", "tap_local_curious_left", "tap_local_curious_right"}, /* curious */
  {"tap_local_delighted_center", "tap_local_delighted_up", "tap_local_delighted_down", "tap_local_delighted_left", "tap_local_delighted_right"}, /* delighted */
  {"tap_local_warm_center", "tap_local_warm_up", "tap_local_warm_down", "tap_local_warm_left", "tap_local_warm_right"}, /* warm */
  {"tap_local_playful_center", "tap_local_playful_up", "tap_local_playful_down", "tap_local_playful_left", "tap_local_playful_right"}, /* playful */
  {"tap_local_sleepy_center", "tap_local_sleepy_up", "tap_local_sleepy_down", "tap_local_sleepy_left", "tap_local_sleepy_right"}, /* sleepy */
  {"tap_local_bashful_center", "tap_local_bashful_up", "tap_local_bashful_down", "tap_local_bashful_left", "tap_local_bashful_right"}, /* bashful */
  {"tap_local_thoughtful_center", "tap_local_thoughtful_up", "tap_local_thoughtful_down", "tap_local_thoughtful_left", "tap_local_thoughtful_right"}, /* thoughtful */
  {"tap_local_focused_center", "tap_local_focused_up", "tap_local_focused_down", "tap_local_focused_left", "tap_local_focused_right"}, /* focused */
  {"tap_local_alert_center", "tap_local_alert_up", "tap_local_alert_down", "tap_local_alert_left", "tap_local_alert_right"}, /* alert */
};

static const char *const companion_browser_legacy_transition_clips[5] = {
  "tap.transition.center", "tap.transition.up", "tap.transition.down", "tap.transition.left", "tap.transition.right"
};

static const uint8_t companion_browser_generation_resource_id[32] = {
  0xB0u, 0x78u, 0x92u, 0x03u, 0x7Fu, 0xF3u, 0x39u, 0x28u, 0x73u, 0x3Eu, 0xCEu, 0x88u, 0xE1u, 0x08u, 0x0Cu, 0x4Du, 0x30u, 0xF4u, 0xA5u, 0x92u, 0xF0u, 0x03u, 0xF4u, 0x6Cu, 0x0Fu, 0x61u, 0x3Eu, 0x29u, 0xFFu, 0x85u, 0xE2u, 0x02u
};

static const uint8_t companion_browser_life_episode_limits[10] = {
  32u, 32u, 32u, 32u, 12u, 12u, 12u, 32u, 12u, 32u
};

static const uint8_t companion_browser_blink_interval_commits
    [COMPANION_BROWSER_BLINK_INTERVAL_COUNT] = {
  24u, 32u, 40u
};

static const companion_browser_blink_eye_box_t
    companion_browser_blink_eye_bounds[10][2] = {
  {{42u, 93u, 33u, 45u}, {125u, 93u, 34u, 45u}},
  {{42u, 93u, 33u, 45u}, {125u, 93u, 34u, 45u}},
  {{42u, 93u, 33u, 45u}, {125u, 93u, 34u, 45u}},
  {{42u, 93u, 33u, 45u}, {125u, 93u, 34u, 45u}},
  {{42u, 93u, 33u, 45u}, {125u, 93u, 34u, 45u}},
  {{0u, 0u, 0u, 0u}, {0u, 0u, 0u, 0u}},
  {{42u, 93u, 33u, 45u}, {125u, 93u, 34u, 45u}},
  {{42u, 93u, 33u, 45u}, {125u, 93u, 34u, 45u}},
  {{42u, 93u, 33u, 45u}, {125u, 93u, 34u, 45u}},
  {{42u, 93u, 33u, 45u}, {125u, 93u, 34u, 45u}},
};

static const companion_browser_blink_eye_box_t
    companion_browser_blink_authored_closed_eye_bounds[2] = {
  {45u, 103u, 28u, 9u},
  {128u, 103u, 28u, 9u},
};

static const uint16_t companion_browser_blink_authored_pixel_offsets[3] = {
  0u, 144u, 289u
};

static const companion_browser_blink_eye_pixel_t
    companion_browser_blink_authored_closed_eye_pixels
    [289] = {
  {-13, -4},
  {-12, -4},
  {-13, -3},
  {-11, -4},
  {-12, -3},
  {-14, -3},
  {-13, -2},
  {-11, -3},
  {-12, -2},
  {-14, -2},
  {-13, -1},
  {-10, -3},
  {-11, -2},
  {-12, -1},
  {-14, -1},
  {-13, 0},
  {-10, -2},
  {-11, -1},
  {-12, 0},
  {-9, -2},
  {-10, -1},
  {-11, 0},
  {-8, -2},
  {-9, -1},
  {-10, 0},
  {-11, 1},
  {-7, -2},
  {-8, -1},
  {-9, 0},
  {-10, 1},
  {-7, -1},
  {-8, 0},
  {-9, 1},
  {-10, 2},
  {-6, -1},
  {-7, 0},
  {-8, 1},
  {-9, 2},
  {-5, -1},
  {-6, 0},
  {-7, 1},
  {-8, 2},
  {-4, -1},
  {-5, 0},
  {-6, 1},
  {-7, 2},
  {-8, 3},
  {-4, 0},
  {-5, 1},
  {-6, 2},
  {-7, 3},
  {-3, 0},
  {-4, 1},
  {-5, 2},
  {-6, 3},
  {-2, 0},
  {-3, 1},
  {-4, 2},
  {-5, 3},
  {-1, 0},
  {-2, 1},
  {-3, 2},
  {-4, 3},
  {0, 0},
  {-1, 1},
  {-2, 2},
  {-3, 3},
  {-4, 4},
  {1, 0},
  {0, 1},
  {-1, 2},
  {-2, 3},
  {-3, 4},
  {2, 0},
  {1, 1},
  {0, 2},
  {-1, 3},
  {-2, 4},
  {3, 0},
  {2, 1},
  {1, 2},
  {0, 3},
  {-1, 4},
  {4, 0},
  {3, 1},
  {2, 2},
  {1, 3},
  {0, 4},
  {5, 0},
  {4, -1},
  {4, 1},
  {3, 2},
  {2, 3},
  {1, 4},
  {6, 0},
  {5, -1},
  {5, 1},
  {4, 2},
  {3, 3},
  {2, 4},
  {7, 0},
  {6, -1},
  {6, 1},
  {5, 2},
  {4, 3},
  {3, 4},
  {8, 0},
  {7, -1},
  {7, 1},
  {6, 2},
  {5, 3},
  {4, 4},
  {9, 0},
  {8, -1},
  {8, 1},
  {7, -2},
  {7, 2},
  {6, 3},
  {10, 0},
  {9, -1},
  {9, 1},
  {8, -2},
  {8, 2},
  {7, 3},
  {11, 0},
  {10, -1},
  {10, 1},
  {9, -2},
  {9, 2},
  {8, 3},
  {12, 0},
  {11, -1},
  {11, 1},
  {10, -2},
  {10, 2},
  {9, -3},
  {12, -1},
  {11, -2},
  {10, -3},
  {13, -1},
  {12, -2},
  {11, -3},
  {13, -2},
  {12, -3},
  {-13, -4},
  {-12, -4},
  {-13, -3},
  {-11, -4},
  {-12, -3},
  {-14, -3},
  {-13, -2},
  {-11, -3},
  {-12, -2},
  {-14, -2},
  {-13, -1},
  {-10, -3},
  {-11, -2},
  {-12, -1},
  {-14, -1},
  {-13, 0},
  {-9, -3},
  {-10, -2},
  {-11, -1},
  {-12, 0},
  {-9, -2},
  {-10, -1},
  {-11, 0},
  {-8, -2},
  {-9, -1},
  {-10, 0},
  {-11, 1},
  {-7, -2},
  {-8, -1},
  {-9, 0},
  {-10, 1},
  {-7, -1},
  {-8, 0},
  {-9, 1},
  {-10, 2},
  {-6, -1},
  {-7, 0},
  {-8, 1},
  {-9, 2},
  {-5, -1},
  {-6, 0},
  {-7, 1},
  {-8, 2},
  {-4, -1},
  {-5, 0},
  {-6, 1},
  {-7, 2},
  {-8, 3},
  {-4, 0},
  {-5, 1},
  {-6, 2},
  {-7, 3},
  {-3, 0},
  {-4, 1},
  {-5, 2},
  {-6, 3},
  {-2, 0},
  {-3, 1},
  {-4, 2},
  {-5, 3},
  {-1, 0},
  {-2, 1},
  {-3, 2},
  {-4, 3},
  {0, 0},
  {-1, 1},
  {-2, 2},
  {-3, 3},
  {-4, 4},
  {1, 0},
  {0, 1},
  {-1, 2},
  {-2, 3},
  {-3, 4},
  {2, 0},
  {1, 1},
  {0, 2},
  {-1, 3},
  {-2, 4},
  {3, 0},
  {2, 1},
  {1, 2},
  {0, 3},
  {-1, 4},
  {4, 0},
  {3, 1},
  {2, 2},
  {1, 3},
  {0, 4},
  {5, 0},
  {4, -1},
  {4, 1},
  {3, 2},
  {2, 3},
  {1, 4},
  {6, 0},
  {5, -1},
  {5, 1},
  {4, 2},
  {3, 3},
  {2, 4},
  {7, 0},
  {6, -1},
  {6, 1},
  {5, 2},
  {4, 3},
  {3, 4},
  {8, 0},
  {7, -1},
  {7, 1},
  {6, 2},
  {5, 3},
  {4, 4},
  {9, 0},
  {8, -1},
  {8, 1},
  {7, -2},
  {7, 2},
  {6, 3},
  {10, 0},
  {9, -1},
  {9, 1},
  {8, -2},
  {8, 2},
  {7, 3},
  {11, 0},
  {10, -1},
  {10, 1},
  {9, -2},
  {9, 2},
  {8, 3},
  {12, 0},
  {11, -1},
  {11, 1},
  {10, -2},
  {10, 2},
  {9, -3},
  {12, -1},
  {11, -2},
  {10, -3},
  {13, -1},
  {12, -2},
  {11, -3},
  {13, -2},
  {12, -3},
};

#if COMPANION_BROWSER_INTERACTION_HAS_PRODUCT_GENERATION
static const char *const companion_browser_pointer_state_ids[10][5][5] = {
  {{"pointer_follow_calm_gx0_gy0", "pointer_follow_calm_gx0_gy2", "pointer_follow_calm_gx0_gy4", "pointer_follow_calm_gx0_gy6", "pointer_follow_calm_gx0_gy8"}, {"pointer_follow_calm_gx2_gy0", "pointer_follow_calm_gx2_gy2", "pointer_follow_calm_gx2_gy4", "pointer_follow_calm_gx2_gy6", "pointer_follow_calm_gx2_gy8"}, {"pointer_follow_calm_gx4_gy0", "pointer_follow_calm_gx4_gy2", "pointer_follow_calm_gx4_gy4", "pointer_follow_calm_gx4_gy6", "pointer_follow_calm_gx4_gy8"}, {"pointer_follow_calm_gx6_gy0", "pointer_follow_calm_gx6_gy2", "pointer_follow_calm_gx6_gy4", "pointer_follow_calm_gx6_gy6", "pointer_follow_calm_gx6_gy8"}, {"pointer_follow_calm_gx8_gy0", "pointer_follow_calm_gx8_gy2", "pointer_follow_calm_gx8_gy4", "pointer_follow_calm_gx8_gy6", "pointer_follow_calm_gx8_gy8"}}, /* calm */
  {{"pointer_follow_curious_gx0_gy0", "pointer_follow_curious_gx0_gy2", "pointer_follow_curious_gx0_gy4", "pointer_follow_curious_gx0_gy6", "pointer_follow_curious_gx0_gy8"}, {"pointer_follow_curious_gx2_gy0", "pointer_follow_curious_gx2_gy2", "pointer_follow_curious_gx2_gy4", "pointer_follow_curious_gx2_gy6", "pointer_follow_curious_gx2_gy8"}, {"pointer_follow_curious_gx4_gy0", "pointer_follow_curious_gx4_gy2", "pointer_follow_curious_gx4_gy4", "pointer_follow_curious_gx4_gy6", "pointer_follow_curious_gx4_gy8"}, {"pointer_follow_curious_gx6_gy0", "pointer_follow_curious_gx6_gy2", "pointer_follow_curious_gx6_gy4", "pointer_follow_curious_gx6_gy6", "pointer_follow_curious_gx6_gy8"}, {"pointer_follow_curious_gx8_gy0", "pointer_follow_curious_gx8_gy2", "pointer_follow_curious_gx8_gy4", "pointer_follow_curious_gx8_gy6", "pointer_follow_curious_gx8_gy8"}}, /* curious */
  {{"pointer_follow_delighted_gx0_gy0", "pointer_follow_delighted_gx0_gy2", "pointer_follow_delighted_gx0_gy4", "pointer_follow_delighted_gx0_gy6", "pointer_follow_delighted_gx0_gy8"}, {"pointer_follow_delighted_gx2_gy0", "pointer_follow_delighted_gx2_gy2", "pointer_follow_delighted_gx2_gy4", "pointer_follow_delighted_gx2_gy6", "pointer_follow_delighted_gx2_gy8"}, {"pointer_follow_delighted_gx4_gy0", "pointer_follow_delighted_gx4_gy2", "pointer_follow_delighted_gx4_gy4", "pointer_follow_delighted_gx4_gy6", "pointer_follow_delighted_gx4_gy8"}, {"pointer_follow_delighted_gx6_gy0", "pointer_follow_delighted_gx6_gy2", "pointer_follow_delighted_gx6_gy4", "pointer_follow_delighted_gx6_gy6", "pointer_follow_delighted_gx6_gy8"}, {"pointer_follow_delighted_gx8_gy0", "pointer_follow_delighted_gx8_gy2", "pointer_follow_delighted_gx8_gy4", "pointer_follow_delighted_gx8_gy6", "pointer_follow_delighted_gx8_gy8"}}, /* delighted */
  {{"pointer_follow_warm_gx0_gy0", "pointer_follow_warm_gx0_gy2", "pointer_follow_warm_gx0_gy4", "pointer_follow_warm_gx0_gy6", "pointer_follow_warm_gx0_gy8"}, {"pointer_follow_warm_gx2_gy0", "pointer_follow_warm_gx2_gy2", "pointer_follow_warm_gx2_gy4", "pointer_follow_warm_gx2_gy6", "pointer_follow_warm_gx2_gy8"}, {"pointer_follow_warm_gx4_gy0", "pointer_follow_warm_gx4_gy2", "pointer_follow_warm_gx4_gy4", "pointer_follow_warm_gx4_gy6", "pointer_follow_warm_gx4_gy8"}, {"pointer_follow_warm_gx6_gy0", "pointer_follow_warm_gx6_gy2", "pointer_follow_warm_gx6_gy4", "pointer_follow_warm_gx6_gy6", "pointer_follow_warm_gx6_gy8"}, {"pointer_follow_warm_gx8_gy0", "pointer_follow_warm_gx8_gy2", "pointer_follow_warm_gx8_gy4", "pointer_follow_warm_gx8_gy6", "pointer_follow_warm_gx8_gy8"}}, /* warm */
  {{"pointer_follow_playful_gx0_gy0", "pointer_follow_playful_gx0_gy2", "pointer_follow_playful_gx0_gy4", "pointer_follow_playful_gx0_gy6", "pointer_follow_playful_gx0_gy8"}, {"pointer_follow_playful_gx2_gy0", "pointer_follow_playful_gx2_gy2", "pointer_follow_playful_gx2_gy4", "pointer_follow_playful_gx2_gy6", "pointer_follow_playful_gx2_gy8"}, {"pointer_follow_playful_gx4_gy0", "pointer_follow_playful_gx4_gy2", "pointer_follow_playful_gx4_gy4", "pointer_follow_playful_gx4_gy6", "pointer_follow_playful_gx4_gy8"}, {"pointer_follow_playful_gx6_gy0", "pointer_follow_playful_gx6_gy2", "pointer_follow_playful_gx6_gy4", "pointer_follow_playful_gx6_gy6", "pointer_follow_playful_gx6_gy8"}, {"pointer_follow_playful_gx8_gy0", "pointer_follow_playful_gx8_gy2", "pointer_follow_playful_gx8_gy4", "pointer_follow_playful_gx8_gy6", "pointer_follow_playful_gx8_gy8"}}, /* playful */
  {{"pointer_follow_sleepy_gx0_gy0", "pointer_follow_sleepy_gx0_gy2", "pointer_follow_sleepy_gx0_gy4", "pointer_follow_sleepy_gx0_gy6", "pointer_follow_sleepy_gx0_gy8"}, {"pointer_follow_sleepy_gx2_gy0", "pointer_follow_sleepy_gx2_gy2", "pointer_follow_sleepy_gx2_gy4", "pointer_follow_sleepy_gx2_gy6", "pointer_follow_sleepy_gx2_gy8"}, {"pointer_follow_sleepy_gx4_gy0", "pointer_follow_sleepy_gx4_gy2", "pointer_follow_sleepy_gx4_gy4", "pointer_follow_sleepy_gx4_gy6", "pointer_follow_sleepy_gx4_gy8"}, {"pointer_follow_sleepy_gx6_gy0", "pointer_follow_sleepy_gx6_gy2", "pointer_follow_sleepy_gx6_gy4", "pointer_follow_sleepy_gx6_gy6", "pointer_follow_sleepy_gx6_gy8"}, {"pointer_follow_sleepy_gx8_gy0", "pointer_follow_sleepy_gx8_gy2", "pointer_follow_sleepy_gx8_gy4", "pointer_follow_sleepy_gx8_gy6", "pointer_follow_sleepy_gx8_gy8"}}, /* sleepy */
  {{"pointer_follow_bashful_gx0_gy0", "pointer_follow_bashful_gx0_gy2", "pointer_follow_bashful_gx0_gy4", "pointer_follow_bashful_gx0_gy6", "pointer_follow_bashful_gx0_gy8"}, {"pointer_follow_bashful_gx2_gy0", "pointer_follow_bashful_gx2_gy2", "pointer_follow_bashful_gx2_gy4", "pointer_follow_bashful_gx2_gy6", "pointer_follow_bashful_gx2_gy8"}, {"pointer_follow_bashful_gx4_gy0", "pointer_follow_bashful_gx4_gy2", "pointer_follow_bashful_gx4_gy4", "pointer_follow_bashful_gx4_gy6", "pointer_follow_bashful_gx4_gy8"}, {"pointer_follow_bashful_gx6_gy0", "pointer_follow_bashful_gx6_gy2", "pointer_follow_bashful_gx6_gy4", "pointer_follow_bashful_gx6_gy6", "pointer_follow_bashful_gx6_gy8"}, {"pointer_follow_bashful_gx8_gy0", "pointer_follow_bashful_gx8_gy2", "pointer_follow_bashful_gx8_gy4", "pointer_follow_bashful_gx8_gy6", "pointer_follow_bashful_gx8_gy8"}}, /* bashful */
  {{"pointer_follow_thoughtful_gx0_gy0", "pointer_follow_thoughtful_gx0_gy2", "pointer_follow_thoughtful_gx0_gy4", "pointer_follow_thoughtful_gx0_gy6", "pointer_follow_thoughtful_gx0_gy8"}, {"pointer_follow_thoughtful_gx2_gy0", "pointer_follow_thoughtful_gx2_gy2", "pointer_follow_thoughtful_gx2_gy4", "pointer_follow_thoughtful_gx2_gy6", "pointer_follow_thoughtful_gx2_gy8"}, {"pointer_follow_thoughtful_gx4_gy0", "pointer_follow_thoughtful_gx4_gy2", "pointer_follow_thoughtful_gx4_gy4", "pointer_follow_thoughtful_gx4_gy6", "pointer_follow_thoughtful_gx4_gy8"}, {"pointer_follow_thoughtful_gx6_gy0", "pointer_follow_thoughtful_gx6_gy2", "pointer_follow_thoughtful_gx6_gy4", "pointer_follow_thoughtful_gx6_gy6", "pointer_follow_thoughtful_gx6_gy8"}, {"pointer_follow_thoughtful_gx8_gy0", "pointer_follow_thoughtful_gx8_gy2", "pointer_follow_thoughtful_gx8_gy4", "pointer_follow_thoughtful_gx8_gy6", "pointer_follow_thoughtful_gx8_gy8"}}, /* thoughtful */
  {{"pointer_follow_focused_gx0_gy0", "pointer_follow_focused_gx0_gy2", "pointer_follow_focused_gx0_gy4", "pointer_follow_focused_gx0_gy6", "pointer_follow_focused_gx0_gy8"}, {"pointer_follow_focused_gx2_gy0", "pointer_follow_focused_gx2_gy2", "pointer_follow_focused_gx2_gy4", "pointer_follow_focused_gx2_gy6", "pointer_follow_focused_gx2_gy8"}, {"pointer_follow_focused_gx4_gy0", "pointer_follow_focused_gx4_gy2", "pointer_follow_focused_gx4_gy4", "pointer_follow_focused_gx4_gy6", "pointer_follow_focused_gx4_gy8"}, {"pointer_follow_focused_gx6_gy0", "pointer_follow_focused_gx6_gy2", "pointer_follow_focused_gx6_gy4", "pointer_follow_focused_gx6_gy6", "pointer_follow_focused_gx6_gy8"}, {"pointer_follow_focused_gx8_gy0", "pointer_follow_focused_gx8_gy2", "pointer_follow_focused_gx8_gy4", "pointer_follow_focused_gx8_gy6", "pointer_follow_focused_gx8_gy8"}}, /* focused */
  {{"pointer_follow_alert_gx0_gy0", "pointer_follow_alert_gx0_gy2", "pointer_follow_alert_gx0_gy4", "pointer_follow_alert_gx0_gy6", "pointer_follow_alert_gx0_gy8"}, {"pointer_follow_alert_gx2_gy0", "pointer_follow_alert_gx2_gy2", "pointer_follow_alert_gx2_gy4", "pointer_follow_alert_gx2_gy6", "pointer_follow_alert_gx2_gy8"}, {"pointer_follow_alert_gx4_gy0", "pointer_follow_alert_gx4_gy2", "pointer_follow_alert_gx4_gy4", "pointer_follow_alert_gx4_gy6", "pointer_follow_alert_gx4_gy8"}, {"pointer_follow_alert_gx6_gy0", "pointer_follow_alert_gx6_gy2", "pointer_follow_alert_gx6_gy4", "pointer_follow_alert_gx6_gy6", "pointer_follow_alert_gx6_gy8"}, {"pointer_follow_alert_gx8_gy0", "pointer_follow_alert_gx8_gy2", "pointer_follow_alert_gx8_gy4", "pointer_follow_alert_gx8_gy6", "pointer_follow_alert_gx8_gy8"}}, /* alert */
};
#endif

static const uint8_t companion_browser_menu_variant_counts
    [COMPANION_BROWSER_MENU_SCREEN_COUNT] = {
  1u, 32u, 2u, 4u, 9u, 2u, 1u, 1u, 24u, 2u, 4u, 2u, 1u
};

static const uint8_t companion_browser_menu_item_counts
    [COMPANION_BROWSER_MENU_SCREEN_COUNT] = {
  8u, 7u, 4u, 7u, 4u, 2u, 3u, 5u, 6u, 7u, 5u, 3u, 3u
};

static const companion_browser_menu_row_t companion_browser_menu_rows
    [COMPANION_BROWSER_MENU_ROW_COUNT] = {
  {0u, 0u, 1u, 1u, 1u},
  {0u, 1u, 1u, 2u, 2u},
  {0u, 2u, 1u, 8u, 3u},
  {0u, 3u, 1u, 3u, 4u},
  {0u, 4u, 1u, 9u, 5u},
  {0u, 5u, 1u, 10u, 6u},
  {0u, 6u, 1u, 4u, 7u},
  {0u, 7u, 1u, 7u, 8u},
  {1u, 0u, 2u, 255u, 9u},
  {1u, 1u, 1u, 5u, 10u},
  {1u, 2u, 6u, 255u, 11u},
  {1u, 3u, 6u, 255u, 12u},
  {1u, 4u, 5u, 255u, 13u},
  {1u, 5u, 2u, 255u, 14u},
  {1u, 6u, 2u, 255u, 15u},
  {2u, 0u, 6u, 255u, 16u},
  {2u, 1u, 2u, 255u, 17u},
  {2u, 2u, 2u, 255u, 18u},
  {2u, 3u, 2u, 255u, 19u},
  {3u, 0u, 2u, 255u, 20u},
  {3u, 1u, 3u, 255u, 21u},
  {3u, 2u, 3u, 255u, 22u},
  {3u, 3u, 5u, 255u, 23u},
  {3u, 4u, 2u, 255u, 24u},
  {3u, 5u, 3u, 255u, 25u},
  {3u, 6u, 2u, 255u, 26u},
  {4u, 0u, 1u, 6u, 27u},
  {4u, 1u, 6u, 255u, 28u},
  {4u, 2u, 6u, 255u, 29u},
  {4u, 3u, 1u, 12u, 30u},
  {5u, 0u, 4u, 255u, 31u},
  {5u, 1u, 4u, 255u, 32u},
  {6u, 0u, 4u, 255u, 33u},
  {6u, 1u, 4u, 255u, 34u},
  {6u, 2u, 4u, 255u, 62u},
  {7u, 0u, 2u, 255u, 35u},
  {7u, 1u, 2u, 255u, 36u},
  {7u, 2u, 2u, 255u, 37u},
  {7u, 3u, 2u, 255u, 38u},
  {7u, 4u, 2u, 255u, 39u},
  {8u, 0u, 2u, 255u, 40u},
  {8u, 1u, 1u, 5u, 41u},
  {8u, 2u, 6u, 255u, 42u},
  {8u, 3u, 5u, 255u, 43u},
  {8u, 4u, 5u, 255u, 44u},
  {8u, 5u, 2u, 255u, 45u},
  {9u, 0u, 2u, 255u, 46u},
  {9u, 1u, 2u, 255u, 47u},
  {9u, 2u, 1u, 11u, 48u},
  {9u, 3u, 2u, 255u, 49u},
  {9u, 4u, 2u, 255u, 50u},
  {9u, 5u, 2u, 255u, 14u},
  {9u, 6u, 2u, 255u, 51u},
  {10u, 0u, 2u, 255u, 52u},
  {10u, 1u, 2u, 255u, 53u},
  {10u, 2u, 6u, 255u, 54u},
  {10u, 3u, 3u, 255u, 55u},
  {10u, 4u, 2u, 255u, 56u},
  {11u, 0u, 2u, 255u, 57u},
  {11u, 1u, 3u, 255u, 58u},
  {11u, 2u, 7u, 255u, 59u},
  {12u, 0u, 2u, 255u, 60u},
  {12u, 1u, 3u, 255u, 61u},
  {12u, 2u, 7u, 255u, 59u},
};

#if COMPANION_BROWSER_INTERACTION_HAS_EDGE_CLIPS
static const companion_browser_interaction_edge_clip_t
    companion_browser_interaction_edge_clips[COMPANION_BROWSER_INTERACTION_EDGE_CLIP_COUNT] = {
  {0u, 1u, {"tap.edge.calm.curious.center", "tap.edge.calm.curious.up", "tap.edge.calm.curious.down", "tap.edge.calm.curious.left", "tap.edge.calm.curious.right"}}, /* calm->curious */
  {0u, 3u, {"tap.edge.calm.warm.center", "tap.edge.calm.warm.up", "tap.edge.calm.warm.down", "tap.edge.calm.warm.left", "tap.edge.calm.warm.right"}}, /* calm->warm */
  {0u, 5u, {"tap.edge.calm.sleepy.center", "tap.edge.calm.sleepy.up", "tap.edge.calm.sleepy.down", "tap.edge.calm.sleepy.left", "tap.edge.calm.sleepy.right"}}, /* calm->sleepy */
  {1u, 0u, {"tap.edge.curious.calm.center", "tap.edge.curious.calm.up", "tap.edge.curious.calm.down", "tap.edge.curious.calm.left", "tap.edge.curious.calm.right"}}, /* curious->calm */
  {1u, 3u, {"tap.edge.curious.warm.center", "tap.edge.curious.warm.up", "tap.edge.curious.warm.down", "tap.edge.curious.warm.left", "tap.edge.curious.warm.right"}}, /* curious->warm */
  {1u, 4u, {"tap.edge.curious.playful.center", "tap.edge.curious.playful.up", "tap.edge.curious.playful.down", "tap.edge.curious.playful.left", "tap.edge.curious.playful.right"}}, /* curious->playful */
  {1u, 7u, {"tap.edge.curious.thoughtful.center", "tap.edge.curious.thoughtful.up", "tap.edge.curious.thoughtful.down", "tap.edge.curious.thoughtful.left", "tap.edge.curious.thoughtful.right"}}, /* curious->thoughtful */
  {1u, 8u, {"tap.edge.curious.focused.center", "tap.edge.curious.focused.up", "tap.edge.curious.focused.down", "tap.edge.curious.focused.left", "tap.edge.curious.focused.right"}}, /* curious->focused */
  {1u, 9u, {"tap.edge.curious.alert.center", "tap.edge.curious.alert.up", "tap.edge.curious.alert.down", "tap.edge.curious.alert.left", "tap.edge.curious.alert.right"}}, /* curious->alert */
  {2u, 3u, {"tap.edge.delighted.warm.center", "tap.edge.delighted.warm.up", "tap.edge.delighted.warm.down", "tap.edge.delighted.warm.left", "tap.edge.delighted.warm.right"}}, /* delighted->warm */
  {2u, 4u, {"tap.edge.delighted.playful.center", "tap.edge.delighted.playful.up", "tap.edge.delighted.playful.down", "tap.edge.delighted.playful.left", "tap.edge.delighted.playful.right"}}, /* delighted->playful */
  {2u, 0u, {"tap.edge.delighted.calm.center", "tap.edge.delighted.calm.up", "tap.edge.delighted.calm.down", "tap.edge.delighted.calm.left", "tap.edge.delighted.calm.right"}}, /* delighted->calm */
  {3u, 0u, {"tap.edge.warm.calm.center", "tap.edge.warm.calm.up", "tap.edge.warm.calm.down", "tap.edge.warm.calm.left", "tap.edge.warm.calm.right"}}, /* warm->calm */
  {3u, 1u, {"tap.edge.warm.curious.center", "tap.edge.warm.curious.up", "tap.edge.warm.curious.down", "tap.edge.warm.curious.left", "tap.edge.warm.curious.right"}}, /* warm->curious */
  {3u, 2u, {"tap.edge.warm.delighted.center", "tap.edge.warm.delighted.up", "tap.edge.warm.delighted.down", "tap.edge.warm.delighted.left", "tap.edge.warm.delighted.right"}}, /* warm->delighted */
  {3u, 4u, {"tap.edge.warm.playful.center", "tap.edge.warm.playful.up", "tap.edge.warm.playful.down", "tap.edge.warm.playful.left", "tap.edge.warm.playful.right"}}, /* warm->playful */
  {3u, 6u, {"tap.edge.warm.bashful.center", "tap.edge.warm.bashful.up", "tap.edge.warm.bashful.down", "tap.edge.warm.bashful.left", "tap.edge.warm.bashful.right"}}, /* warm->bashful */
  {4u, 2u, {"tap.edge.playful.delighted.center", "tap.edge.playful.delighted.up", "tap.edge.playful.delighted.down", "tap.edge.playful.delighted.left", "tap.edge.playful.delighted.right"}}, /* playful->delighted */
  {4u, 3u, {"tap.edge.playful.warm.center", "tap.edge.playful.warm.up", "tap.edge.playful.warm.down", "tap.edge.playful.warm.left", "tap.edge.playful.warm.right"}}, /* playful->warm */
  {4u, 1u, {"tap.edge.playful.curious.center", "tap.edge.playful.curious.up", "tap.edge.playful.curious.down", "tap.edge.playful.curious.left", "tap.edge.playful.curious.right"}}, /* playful->curious */
  {4u, 0u, {"tap.edge.playful.calm.center", "tap.edge.playful.calm.up", "tap.edge.playful.calm.down", "tap.edge.playful.calm.left", "tap.edge.playful.calm.right"}}, /* playful->calm */
  {5u, 0u, {"tap.edge.sleepy.calm.center", "tap.edge.sleepy.calm.up", "tap.edge.sleepy.calm.down", "tap.edge.sleepy.calm.left", "tap.edge.sleepy.calm.right"}}, /* sleepy->calm */
  {5u, 3u, {"tap.edge.sleepy.warm.center", "tap.edge.sleepy.warm.up", "tap.edge.sleepy.warm.down", "tap.edge.sleepy.warm.left", "tap.edge.sleepy.warm.right"}}, /* sleepy->warm */
  {6u, 3u, {"tap.edge.bashful.warm.center", "tap.edge.bashful.warm.up", "tap.edge.bashful.warm.down", "tap.edge.bashful.warm.left", "tap.edge.bashful.warm.right"}}, /* bashful->warm */
  {6u, 1u, {"tap.edge.bashful.curious.center", "tap.edge.bashful.curious.up", "tap.edge.bashful.curious.down", "tap.edge.bashful.curious.left", "tap.edge.bashful.curious.right"}}, /* bashful->curious */
  {6u, 0u, {"tap.edge.bashful.calm.center", "tap.edge.bashful.calm.up", "tap.edge.bashful.calm.down", "tap.edge.bashful.calm.left", "tap.edge.bashful.calm.right"}}, /* bashful->calm */
  {7u, 1u, {"tap.edge.thoughtful.curious.center", "tap.edge.thoughtful.curious.up", "tap.edge.thoughtful.curious.down", "tap.edge.thoughtful.curious.left", "tap.edge.thoughtful.curious.right"}}, /* thoughtful->curious */
  {7u, 8u, {"tap.edge.thoughtful.focused.center", "tap.edge.thoughtful.focused.up", "tap.edge.thoughtful.focused.down", "tap.edge.thoughtful.focused.left", "tap.edge.thoughtful.focused.right"}}, /* thoughtful->focused */
  {7u, 9u, {"tap.edge.thoughtful.alert.center", "tap.edge.thoughtful.alert.up", "tap.edge.thoughtful.alert.down", "tap.edge.thoughtful.alert.left", "tap.edge.thoughtful.alert.right"}}, /* thoughtful->alert */
  {7u, 0u, {"tap.edge.thoughtful.calm.center", "tap.edge.thoughtful.calm.up", "tap.edge.thoughtful.calm.down", "tap.edge.thoughtful.calm.left", "tap.edge.thoughtful.calm.right"}}, /* thoughtful->calm */
  {8u, 1u, {"tap.edge.focused.curious.center", "tap.edge.focused.curious.up", "tap.edge.focused.curious.down", "tap.edge.focused.curious.left", "tap.edge.focused.curious.right"}}, /* focused->curious */
  {8u, 7u, {"tap.edge.focused.thoughtful.center", "tap.edge.focused.thoughtful.up", "tap.edge.focused.thoughtful.down", "tap.edge.focused.thoughtful.left", "tap.edge.focused.thoughtful.right"}}, /* focused->thoughtful */
  {8u, 9u, {"tap.edge.focused.alert.center", "tap.edge.focused.alert.up", "tap.edge.focused.alert.down", "tap.edge.focused.alert.left", "tap.edge.focused.alert.right"}}, /* focused->alert */
  {8u, 0u, {"tap.edge.focused.calm.center", "tap.edge.focused.calm.up", "tap.edge.focused.calm.down", "tap.edge.focused.calm.left", "tap.edge.focused.calm.right"}}, /* focused->calm */
  {9u, 8u, {"tap.edge.alert.focused.center", "tap.edge.alert.focused.up", "tap.edge.alert.focused.down", "tap.edge.alert.focused.left", "tap.edge.alert.focused.right"}}, /* alert->focused */
  {9u, 1u, {"tap.edge.alert.curious.center", "tap.edge.alert.curious.up", "tap.edge.alert.curious.down", "tap.edge.alert.curious.left", "tap.edge.alert.curious.right"}}, /* alert->curious */
  {9u, 0u, {"tap.edge.alert.calm.center", "tap.edge.alert.calm.up", "tap.edge.alert.calm.down", "tap.edge.alert.calm.left", "tap.edge.alert.calm.right"}}, /* alert->calm */
};
#endif

#if COMPANION_BROWSER_INTERACTION_HAS_EDGE_STATES
static const companion_browser_interaction_edge_state_t
    companion_browser_interaction_edge_states
[COMPANION_BROWSER_INTERACTION_EDGE_STATE_COUNT] = {
  {0u, 1u, {{"tap_edge_calm_curious_center_orient", "tap_edge_calm_curious_center_anticipate", "tap_edge_calm_curious_center_accent", "tap_edge_calm_curious_center_follow", "tap_edge_calm_curious_center_settle"}, {"tap_edge_calm_curious_up_orient", "tap_edge_calm_curious_up_anticipate", "tap_edge_calm_curious_up_accent", "tap_edge_calm_curious_up_follow", "tap_edge_calm_curious_up_settle"}, {"tap_edge_calm_curious_down_orient", "tap_edge_calm_curious_down_anticipate", "tap_edge_calm_curious_down_accent", "tap_edge_calm_curious_down_follow", "tap_edge_calm_curious_down_settle"}, {"tap_edge_calm_curious_left_orient", "tap_edge_calm_curious_left_anticipate", "tap_edge_calm_curious_left_accent", "tap_edge_calm_curious_left_follow", "tap_edge_calm_curious_left_settle"}, {"tap_edge_calm_curious_right_orient", "tap_edge_calm_curious_right_anticipate", "tap_edge_calm_curious_right_accent", "tap_edge_calm_curious_right_follow", "tap_edge_calm_curious_right_settle"}}}, /* calm->curious */
  {0u, 3u, {{"tap_edge_calm_warm_center_orient", "tap_edge_calm_warm_center_anticipate", "tap_edge_calm_warm_center_accent", "tap_edge_calm_warm_center_follow", "tap_edge_calm_warm_center_settle"}, {"tap_edge_calm_warm_up_orient", "tap_edge_calm_warm_up_anticipate", "tap_edge_calm_warm_up_accent", "tap_edge_calm_warm_up_follow", "tap_edge_calm_warm_up_settle"}, {"tap_edge_calm_warm_down_orient", "tap_edge_calm_warm_down_anticipate", "tap_edge_calm_warm_down_accent", "tap_edge_calm_warm_down_follow", "tap_edge_calm_warm_down_settle"}, {"tap_edge_calm_warm_left_orient", "tap_edge_calm_warm_left_anticipate", "tap_edge_calm_warm_left_accent", "tap_edge_calm_warm_left_follow", "tap_edge_calm_warm_left_settle"}, {"tap_edge_calm_warm_right_orient", "tap_edge_calm_warm_right_anticipate", "tap_edge_calm_warm_right_accent", "tap_edge_calm_warm_right_follow", "tap_edge_calm_warm_right_settle"}}}, /* calm->warm */
  {0u, 5u, {{"tap_edge_calm_sleepy_center_orient", "tap_edge_calm_sleepy_center_anticipate", "tap_edge_calm_sleepy_center_accent", "tap_edge_calm_sleepy_center_follow", "tap_edge_calm_sleepy_center_settle"}, {"tap_edge_calm_sleepy_up_orient", "tap_edge_calm_sleepy_up_anticipate", "tap_edge_calm_sleepy_up_accent", "tap_edge_calm_sleepy_up_follow", "tap_edge_calm_sleepy_up_settle"}, {"tap_edge_calm_sleepy_down_orient", "tap_edge_calm_sleepy_down_anticipate", "tap_edge_calm_sleepy_down_accent", "tap_edge_calm_sleepy_down_follow", "tap_edge_calm_sleepy_down_settle"}, {"tap_edge_calm_sleepy_left_orient", "tap_edge_calm_sleepy_left_anticipate", "tap_edge_calm_sleepy_left_accent", "tap_edge_calm_sleepy_left_follow", "tap_edge_calm_sleepy_left_settle"}, {"tap_edge_calm_sleepy_right_orient", "tap_edge_calm_sleepy_right_anticipate", "tap_edge_calm_sleepy_right_accent", "tap_edge_calm_sleepy_right_follow", "tap_edge_calm_sleepy_right_settle"}}}, /* calm->sleepy */
  {1u, 0u, {{"tap_edge_curious_calm_center_orient", "tap_edge_curious_calm_center_anticipate", "tap_edge_curious_calm_center_accent", "tap_edge_curious_calm_center_follow", "tap_edge_curious_calm_center_settle"}, {"tap_edge_curious_calm_up_orient", "tap_edge_curious_calm_up_anticipate", "tap_edge_curious_calm_up_accent", "tap_edge_curious_calm_up_follow", "tap_edge_curious_calm_up_settle"}, {"tap_edge_curious_calm_down_orient", "tap_edge_curious_calm_down_anticipate", "tap_edge_curious_calm_down_accent", "tap_edge_curious_calm_down_follow", "tap_edge_curious_calm_down_settle"}, {"tap_edge_curious_calm_left_orient", "tap_edge_curious_calm_left_anticipate", "tap_edge_curious_calm_left_accent", "tap_edge_curious_calm_left_follow", "tap_edge_curious_calm_left_settle"}, {"tap_edge_curious_calm_right_orient", "tap_edge_curious_calm_right_anticipate", "tap_edge_curious_calm_right_accent", "tap_edge_curious_calm_right_follow", "tap_edge_curious_calm_right_settle"}}}, /* curious->calm */
  {1u, 3u, {{"tap_edge_curious_warm_center_orient", "tap_edge_curious_warm_center_anticipate", "tap_edge_curious_warm_center_accent", "tap_edge_curious_warm_center_follow", "tap_edge_curious_warm_center_settle"}, {"tap_edge_curious_warm_up_orient", "tap_edge_curious_warm_up_anticipate", "tap_edge_curious_warm_up_accent", "tap_edge_curious_warm_up_follow", "tap_edge_curious_warm_up_settle"}, {"tap_edge_curious_warm_down_orient", "tap_edge_curious_warm_down_anticipate", "tap_edge_curious_warm_down_accent", "tap_edge_curious_warm_down_follow", "tap_edge_curious_warm_down_settle"}, {"tap_edge_curious_warm_left_orient", "tap_edge_curious_warm_left_anticipate", "tap_edge_curious_warm_left_accent", "tap_edge_curious_warm_left_follow", "tap_edge_curious_warm_left_settle"}, {"tap_edge_curious_warm_right_orient", "tap_edge_curious_warm_right_anticipate", "tap_edge_curious_warm_right_accent", "tap_edge_curious_warm_right_follow", "tap_edge_curious_warm_right_settle"}}}, /* curious->warm */
  {1u, 4u, {{"tap_edge_curious_playful_center_orient", "tap_edge_curious_playful_center_anticipate", "tap_edge_curious_playful_center_accent", "tap_edge_curious_playful_center_follow", "tap_edge_curious_playful_center_settle"}, {"tap_edge_curious_playful_up_orient", "tap_edge_curious_playful_up_anticipate", "tap_edge_curious_playful_up_accent", "tap_edge_curious_playful_up_follow", "tap_edge_curious_playful_up_settle"}, {"tap_edge_curious_playful_down_orient", "tap_edge_curious_playful_down_anticipate", "tap_edge_curious_playful_down_accent", "tap_edge_curious_playful_down_follow", "tap_edge_curious_playful_down_settle"}, {"tap_edge_curious_playful_left_orient", "tap_edge_curious_playful_left_anticipate", "tap_edge_curious_playful_left_accent", "tap_edge_curious_playful_left_follow", "tap_edge_curious_playful_left_settle"}, {"tap_edge_curious_playful_right_orient", "tap_edge_curious_playful_right_anticipate", "tap_edge_curious_playful_right_accent", "tap_edge_curious_playful_right_follow", "tap_edge_curious_playful_right_settle"}}}, /* curious->playful */
  {1u, 7u, {{"tap_edge_curious_thoughtful_center_orient", "tap_edge_curious_thoughtful_center_anticipate", "tap_edge_curious_thoughtful_center_accent", "tap_edge_curious_thoughtful_center_follow", "tap_edge_curious_thoughtful_center_settle"}, {"tap_edge_curious_thoughtful_up_orient", "tap_edge_curious_thoughtful_up_anticipate", "tap_edge_curious_thoughtful_up_accent", "tap_edge_curious_thoughtful_up_follow", "tap_edge_curious_thoughtful_up_settle"}, {"tap_edge_curious_thoughtful_down_orient", "tap_edge_curious_thoughtful_down_anticipate", "tap_edge_curious_thoughtful_down_accent", "tap_edge_curious_thoughtful_down_follow", "tap_edge_curious_thoughtful_down_settle"}, {"tap_edge_curious_thoughtful_left_orient", "tap_edge_curious_thoughtful_left_anticipate", "tap_edge_curious_thoughtful_left_accent", "tap_edge_curious_thoughtful_left_follow", "tap_edge_curious_thoughtful_left_settle"}, {"tap_edge_curious_thoughtful_right_orient", "tap_edge_curious_thoughtful_right_anticipate", "tap_edge_curious_thoughtful_right_accent", "tap_edge_curious_thoughtful_right_follow", "tap_edge_curious_thoughtful_right_settle"}}}, /* curious->thoughtful */
  {1u, 8u, {{"tap_edge_curious_focused_center_orient", "tap_edge_curious_focused_center_anticipate", "tap_edge_curious_focused_center_accent", "tap_edge_curious_focused_center_follow", "tap_edge_curious_focused_center_settle"}, {"tap_edge_curious_focused_up_orient", "tap_edge_curious_focused_up_anticipate", "tap_edge_curious_focused_up_accent", "tap_edge_curious_focused_up_follow", "tap_edge_curious_focused_up_settle"}, {"tap_edge_curious_focused_down_orient", "tap_edge_curious_focused_down_anticipate", "tap_edge_curious_focused_down_accent", "tap_edge_curious_focused_down_follow", "tap_edge_curious_focused_down_settle"}, {"tap_edge_curious_focused_left_orient", "tap_edge_curious_focused_left_anticipate", "tap_edge_curious_focused_left_accent", "tap_edge_curious_focused_left_follow", "tap_edge_curious_focused_left_settle"}, {"tap_edge_curious_focused_right_orient", "tap_edge_curious_focused_right_anticipate", "tap_edge_curious_focused_right_accent", "tap_edge_curious_focused_right_follow", "tap_edge_curious_focused_right_settle"}}}, /* curious->focused */
  {1u, 9u, {{"tap_edge_curious_alert_center_orient", "tap_edge_curious_alert_center_anticipate", "tap_edge_curious_alert_center_accent", "tap_edge_curious_alert_center_follow", "tap_edge_curious_alert_center_settle"}, {"tap_edge_curious_alert_up_orient", "tap_edge_curious_alert_up_anticipate", "tap_edge_curious_alert_up_accent", "tap_edge_curious_alert_up_follow", "tap_edge_curious_alert_up_settle"}, {"tap_edge_curious_alert_down_orient", "tap_edge_curious_alert_down_anticipate", "tap_edge_curious_alert_down_accent", "tap_edge_curious_alert_down_follow", "tap_edge_curious_alert_down_settle"}, {"tap_edge_curious_alert_left_orient", "tap_edge_curious_alert_left_anticipate", "tap_edge_curious_alert_left_accent", "tap_edge_curious_alert_left_follow", "tap_edge_curious_alert_left_settle"}, {"tap_edge_curious_alert_right_orient", "tap_edge_curious_alert_right_anticipate", "tap_edge_curious_alert_right_accent", "tap_edge_curious_alert_right_follow", "tap_edge_curious_alert_right_settle"}}}, /* curious->alert */
  {2u, 3u, {{"tap_edge_delighted_warm_center_orient", "tap_edge_delighted_warm_center_anticipate", "tap_edge_delighted_warm_center_accent", "tap_edge_delighted_warm_center_follow", "tap_edge_delighted_warm_center_settle"}, {"tap_edge_delighted_warm_up_orient", "tap_edge_delighted_warm_up_anticipate", "tap_edge_delighted_warm_up_accent", "tap_edge_delighted_warm_up_follow", "tap_edge_delighted_warm_up_settle"}, {"tap_edge_delighted_warm_down_orient", "tap_edge_delighted_warm_down_anticipate", "tap_edge_delighted_warm_down_accent", "tap_edge_delighted_warm_down_follow", "tap_edge_delighted_warm_down_settle"}, {"tap_edge_delighted_warm_left_orient", "tap_edge_delighted_warm_left_anticipate", "tap_edge_delighted_warm_left_accent", "tap_edge_delighted_warm_left_follow", "tap_edge_delighted_warm_left_settle"}, {"tap_edge_delighted_warm_right_orient", "tap_edge_delighted_warm_right_anticipate", "tap_edge_delighted_warm_right_accent", "tap_edge_delighted_warm_right_follow", "tap_edge_delighted_warm_right_settle"}}}, /* delighted->warm */
  {2u, 4u, {{"tap_edge_delighted_playful_center_orient", "tap_edge_delighted_playful_center_anticipate", "tap_edge_delighted_playful_center_accent", "tap_edge_delighted_playful_center_follow", "tap_edge_delighted_playful_center_settle"}, {"tap_edge_delighted_playful_up_orient", "tap_edge_delighted_playful_up_anticipate", "tap_edge_delighted_playful_up_accent", "tap_edge_delighted_playful_up_follow", "tap_edge_delighted_playful_up_settle"}, {"tap_edge_delighted_playful_down_orient", "tap_edge_delighted_playful_down_anticipate", "tap_edge_delighted_playful_down_accent", "tap_edge_delighted_playful_down_follow", "tap_edge_delighted_playful_down_settle"}, {"tap_edge_delighted_playful_left_orient", "tap_edge_delighted_playful_left_anticipate", "tap_edge_delighted_playful_left_accent", "tap_edge_delighted_playful_left_follow", "tap_edge_delighted_playful_left_settle"}, {"tap_edge_delighted_playful_right_orient", "tap_edge_delighted_playful_right_anticipate", "tap_edge_delighted_playful_right_accent", "tap_edge_delighted_playful_right_follow", "tap_edge_delighted_playful_right_settle"}}}, /* delighted->playful */
  {2u, 0u, {{"tap_edge_delighted_calm_center_orient", "tap_edge_delighted_calm_center_anticipate", "tap_edge_delighted_calm_center_accent", "tap_edge_delighted_calm_center_follow", "tap_edge_delighted_calm_center_settle"}, {"tap_edge_delighted_calm_up_orient", "tap_edge_delighted_calm_up_anticipate", "tap_edge_delighted_calm_up_accent", "tap_edge_delighted_calm_up_follow", "tap_edge_delighted_calm_up_settle"}, {"tap_edge_delighted_calm_down_orient", "tap_edge_delighted_calm_down_anticipate", "tap_edge_delighted_calm_down_accent", "tap_edge_delighted_calm_down_follow", "tap_edge_delighted_calm_down_settle"}, {"tap_edge_delighted_calm_left_orient", "tap_edge_delighted_calm_left_anticipate", "tap_edge_delighted_calm_left_accent", "tap_edge_delighted_calm_left_follow", "tap_edge_delighted_calm_left_settle"}, {"tap_edge_delighted_calm_right_orient", "tap_edge_delighted_calm_right_anticipate", "tap_edge_delighted_calm_right_accent", "tap_edge_delighted_calm_right_follow", "tap_edge_delighted_calm_right_settle"}}}, /* delighted->calm */
  {3u, 0u, {{"tap_edge_warm_calm_center_orient", "tap_edge_warm_calm_center_anticipate", "tap_edge_warm_calm_center_accent", "tap_edge_warm_calm_center_follow", "tap_edge_warm_calm_center_settle"}, {"tap_edge_warm_calm_up_orient", "tap_edge_warm_calm_up_anticipate", "tap_edge_warm_calm_up_accent", "tap_edge_warm_calm_up_follow", "tap_edge_warm_calm_up_settle"}, {"tap_edge_warm_calm_down_orient", "tap_edge_warm_calm_down_anticipate", "tap_edge_warm_calm_down_accent", "tap_edge_warm_calm_down_follow", "tap_edge_warm_calm_down_settle"}, {"tap_edge_warm_calm_left_orient", "tap_edge_warm_calm_left_anticipate", "tap_edge_warm_calm_left_accent", "tap_edge_warm_calm_left_follow", "tap_edge_warm_calm_left_settle"}, {"tap_edge_warm_calm_right_orient", "tap_edge_warm_calm_right_anticipate", "tap_edge_warm_calm_right_accent", "tap_edge_warm_calm_right_follow", "tap_edge_warm_calm_right_settle"}}}, /* warm->calm */
  {3u, 1u, {{"tap_edge_warm_curious_center_orient", "tap_edge_warm_curious_center_anticipate", "tap_edge_warm_curious_center_accent", "tap_edge_warm_curious_center_follow", "tap_edge_warm_curious_center_settle"}, {"tap_edge_warm_curious_up_orient", "tap_edge_warm_curious_up_anticipate", "tap_edge_warm_curious_up_accent", "tap_edge_warm_curious_up_follow", "tap_edge_warm_curious_up_settle"}, {"tap_edge_warm_curious_down_orient", "tap_edge_warm_curious_down_anticipate", "tap_edge_warm_curious_down_accent", "tap_edge_warm_curious_down_follow", "tap_edge_warm_curious_down_settle"}, {"tap_edge_warm_curious_left_orient", "tap_edge_warm_curious_left_anticipate", "tap_edge_warm_curious_left_accent", "tap_edge_warm_curious_left_follow", "tap_edge_warm_curious_left_settle"}, {"tap_edge_warm_curious_right_orient", "tap_edge_warm_curious_right_anticipate", "tap_edge_warm_curious_right_accent", "tap_edge_warm_curious_right_follow", "tap_edge_warm_curious_right_settle"}}}, /* warm->curious */
  {3u, 2u, {{"tap_edge_warm_delighted_center_orient", "tap_edge_warm_delighted_center_anticipate", "tap_edge_warm_delighted_center_accent", "tap_edge_warm_delighted_center_follow", "tap_edge_warm_delighted_center_settle"}, {"tap_edge_warm_delighted_up_orient", "tap_edge_warm_delighted_up_anticipate", "tap_edge_warm_delighted_up_accent", "tap_edge_warm_delighted_up_follow", "tap_edge_warm_delighted_up_settle"}, {"tap_edge_warm_delighted_down_orient", "tap_edge_warm_delighted_down_anticipate", "tap_edge_warm_delighted_down_accent", "tap_edge_warm_delighted_down_follow", "tap_edge_warm_delighted_down_settle"}, {"tap_edge_warm_delighted_left_orient", "tap_edge_warm_delighted_left_anticipate", "tap_edge_warm_delighted_left_accent", "tap_edge_warm_delighted_left_follow", "tap_edge_warm_delighted_left_settle"}, {"tap_edge_warm_delighted_right_orient", "tap_edge_warm_delighted_right_anticipate", "tap_edge_warm_delighted_right_accent", "tap_edge_warm_delighted_right_follow", "tap_edge_warm_delighted_right_settle"}}}, /* warm->delighted */
  {3u, 4u, {{"tap_edge_warm_playful_center_orient", "tap_edge_warm_playful_center_anticipate", "tap_edge_warm_playful_center_accent", "tap_edge_warm_playful_center_follow", "tap_edge_warm_playful_center_settle"}, {"tap_edge_warm_playful_up_orient", "tap_edge_warm_playful_up_anticipate", "tap_edge_warm_playful_up_accent", "tap_edge_warm_playful_up_follow", "tap_edge_warm_playful_up_settle"}, {"tap_edge_warm_playful_down_orient", "tap_edge_warm_playful_down_anticipate", "tap_edge_warm_playful_down_accent", "tap_edge_warm_playful_down_follow", "tap_edge_warm_playful_down_settle"}, {"tap_edge_warm_playful_left_orient", "tap_edge_warm_playful_left_anticipate", "tap_edge_warm_playful_left_accent", "tap_edge_warm_playful_left_follow", "tap_edge_warm_playful_left_settle"}, {"tap_edge_warm_playful_right_orient", "tap_edge_warm_playful_right_anticipate", "tap_edge_warm_playful_right_accent", "tap_edge_warm_playful_right_follow", "tap_edge_warm_playful_right_settle"}}}, /* warm->playful */
  {3u, 6u, {{"tap_edge_warm_bashful_center_orient", "tap_edge_warm_bashful_center_anticipate", "tap_edge_warm_bashful_center_accent", "tap_edge_warm_bashful_center_follow", "tap_edge_warm_bashful_center_settle"}, {"tap_edge_warm_bashful_up_orient", "tap_edge_warm_bashful_up_anticipate", "tap_edge_warm_bashful_up_accent", "tap_edge_warm_bashful_up_follow", "tap_edge_warm_bashful_up_settle"}, {"tap_edge_warm_bashful_down_orient", "tap_edge_warm_bashful_down_anticipate", "tap_edge_warm_bashful_down_accent", "tap_edge_warm_bashful_down_follow", "tap_edge_warm_bashful_down_settle"}, {"tap_edge_warm_bashful_left_orient", "tap_edge_warm_bashful_left_anticipate", "tap_edge_warm_bashful_left_accent", "tap_edge_warm_bashful_left_follow", "tap_edge_warm_bashful_left_settle"}, {"tap_edge_warm_bashful_right_orient", "tap_edge_warm_bashful_right_anticipate", "tap_edge_warm_bashful_right_accent", "tap_edge_warm_bashful_right_follow", "tap_edge_warm_bashful_right_settle"}}}, /* warm->bashful */
  {4u, 2u, {{"tap_edge_playful_delighted_center_orient", "tap_edge_playful_delighted_center_anticipate", "tap_edge_playful_delighted_center_accent", "tap_edge_playful_delighted_center_follow", "tap_edge_playful_delighted_center_settle"}, {"tap_edge_playful_delighted_up_orient", "tap_edge_playful_delighted_up_anticipate", "tap_edge_playful_delighted_up_accent", "tap_edge_playful_delighted_up_follow", "tap_edge_playful_delighted_up_settle"}, {"tap_edge_playful_delighted_down_orient", "tap_edge_playful_delighted_down_anticipate", "tap_edge_playful_delighted_down_accent", "tap_edge_playful_delighted_down_follow", "tap_edge_playful_delighted_down_settle"}, {"tap_edge_playful_delighted_left_orient", "tap_edge_playful_delighted_left_anticipate", "tap_edge_playful_delighted_left_accent", "tap_edge_playful_delighted_left_follow", "tap_edge_playful_delighted_left_settle"}, {"tap_edge_playful_delighted_right_orient", "tap_edge_playful_delighted_right_anticipate", "tap_edge_playful_delighted_right_accent", "tap_edge_playful_delighted_right_follow", "tap_edge_playful_delighted_right_settle"}}}, /* playful->delighted */
  {4u, 3u, {{"tap_edge_playful_warm_center_orient", "tap_edge_playful_warm_center_anticipate", "tap_edge_playful_warm_center_accent", "tap_edge_playful_warm_center_follow", "tap_edge_playful_warm_center_settle"}, {"tap_edge_playful_warm_up_orient", "tap_edge_playful_warm_up_anticipate", "tap_edge_playful_warm_up_accent", "tap_edge_playful_warm_up_follow", "tap_edge_playful_warm_up_settle"}, {"tap_edge_playful_warm_down_orient", "tap_edge_playful_warm_down_anticipate", "tap_edge_playful_warm_down_accent", "tap_edge_playful_warm_down_follow", "tap_edge_playful_warm_down_settle"}, {"tap_edge_playful_warm_left_orient", "tap_edge_playful_warm_left_anticipate", "tap_edge_playful_warm_left_accent", "tap_edge_playful_warm_left_follow", "tap_edge_playful_warm_left_settle"}, {"tap_edge_playful_warm_right_orient", "tap_edge_playful_warm_right_anticipate", "tap_edge_playful_warm_right_accent", "tap_edge_playful_warm_right_follow", "tap_edge_playful_warm_right_settle"}}}, /* playful->warm */
  {4u, 1u, {{"tap_edge_playful_curious_center_orient", "tap_edge_playful_curious_center_anticipate", "tap_edge_playful_curious_center_accent", "tap_edge_playful_curious_center_follow", "tap_edge_playful_curious_center_settle"}, {"tap_edge_playful_curious_up_orient", "tap_edge_playful_curious_up_anticipate", "tap_edge_playful_curious_up_accent", "tap_edge_playful_curious_up_follow", "tap_edge_playful_curious_up_settle"}, {"tap_edge_playful_curious_down_orient", "tap_edge_playful_curious_down_anticipate", "tap_edge_playful_curious_down_accent", "tap_edge_playful_curious_down_follow", "tap_edge_playful_curious_down_settle"}, {"tap_edge_playful_curious_left_orient", "tap_edge_playful_curious_left_anticipate", "tap_edge_playful_curious_left_accent", "tap_edge_playful_curious_left_follow", "tap_edge_playful_curious_left_settle"}, {"tap_edge_playful_curious_right_orient", "tap_edge_playful_curious_right_anticipate", "tap_edge_playful_curious_right_accent", "tap_edge_playful_curious_right_follow", "tap_edge_playful_curious_right_settle"}}}, /* playful->curious */
  {4u, 0u, {{"tap_edge_playful_calm_center_orient", "tap_edge_playful_calm_center_anticipate", "tap_edge_playful_calm_center_accent", "tap_edge_playful_calm_center_follow", "tap_edge_playful_calm_center_settle"}, {"tap_edge_playful_calm_up_orient", "tap_edge_playful_calm_up_anticipate", "tap_edge_playful_calm_up_accent", "tap_edge_playful_calm_up_follow", "tap_edge_playful_calm_up_settle"}, {"tap_edge_playful_calm_down_orient", "tap_edge_playful_calm_down_anticipate", "tap_edge_playful_calm_down_accent", "tap_edge_playful_calm_down_follow", "tap_edge_playful_calm_down_settle"}, {"tap_edge_playful_calm_left_orient", "tap_edge_playful_calm_left_anticipate", "tap_edge_playful_calm_left_accent", "tap_edge_playful_calm_left_follow", "tap_edge_playful_calm_left_settle"}, {"tap_edge_playful_calm_right_orient", "tap_edge_playful_calm_right_anticipate", "tap_edge_playful_calm_right_accent", "tap_edge_playful_calm_right_follow", "tap_edge_playful_calm_right_settle"}}}, /* playful->calm */
  {5u, 0u, {{"tap_edge_sleepy_calm_center_orient", "tap_edge_sleepy_calm_center_anticipate", "tap_edge_sleepy_calm_center_accent", "tap_edge_sleepy_calm_center_follow", "tap_edge_sleepy_calm_center_settle"}, {"tap_edge_sleepy_calm_up_orient", "tap_edge_sleepy_calm_up_anticipate", "tap_edge_sleepy_calm_up_accent", "tap_edge_sleepy_calm_up_follow", "tap_edge_sleepy_calm_up_settle"}, {"tap_edge_sleepy_calm_down_orient", "tap_edge_sleepy_calm_down_anticipate", "tap_edge_sleepy_calm_down_accent", "tap_edge_sleepy_calm_down_follow", "tap_edge_sleepy_calm_down_settle"}, {"tap_edge_sleepy_calm_left_orient", "tap_edge_sleepy_calm_left_anticipate", "tap_edge_sleepy_calm_left_accent", "tap_edge_sleepy_calm_left_follow", "tap_edge_sleepy_calm_left_settle"}, {"tap_edge_sleepy_calm_right_orient", "tap_edge_sleepy_calm_right_anticipate", "tap_edge_sleepy_calm_right_accent", "tap_edge_sleepy_calm_right_follow", "tap_edge_sleepy_calm_right_settle"}}}, /* sleepy->calm */
  {5u, 3u, {{"tap_edge_sleepy_warm_center_orient", "tap_edge_sleepy_warm_center_anticipate", "tap_edge_sleepy_warm_center_accent", "tap_edge_sleepy_warm_center_follow", "tap_edge_sleepy_warm_center_settle"}, {"tap_edge_sleepy_warm_up_orient", "tap_edge_sleepy_warm_up_anticipate", "tap_edge_sleepy_warm_up_accent", "tap_edge_sleepy_warm_up_follow", "tap_edge_sleepy_warm_up_settle"}, {"tap_edge_sleepy_warm_down_orient", "tap_edge_sleepy_warm_down_anticipate", "tap_edge_sleepy_warm_down_accent", "tap_edge_sleepy_warm_down_follow", "tap_edge_sleepy_warm_down_settle"}, {"tap_edge_sleepy_warm_left_orient", "tap_edge_sleepy_warm_left_anticipate", "tap_edge_sleepy_warm_left_accent", "tap_edge_sleepy_warm_left_follow", "tap_edge_sleepy_warm_left_settle"}, {"tap_edge_sleepy_warm_right_orient", "tap_edge_sleepy_warm_right_anticipate", "tap_edge_sleepy_warm_right_accent", "tap_edge_sleepy_warm_right_follow", "tap_edge_sleepy_warm_right_settle"}}}, /* sleepy->warm */
  {6u, 3u, {{"tap_edge_bashful_warm_center_orient", "tap_edge_bashful_warm_center_anticipate", "tap_edge_bashful_warm_center_accent", "tap_edge_bashful_warm_center_follow", "tap_edge_bashful_warm_center_settle"}, {"tap_edge_bashful_warm_up_orient", "tap_edge_bashful_warm_up_anticipate", "tap_edge_bashful_warm_up_accent", "tap_edge_bashful_warm_up_follow", "tap_edge_bashful_warm_up_settle"}, {"tap_edge_bashful_warm_down_orient", "tap_edge_bashful_warm_down_anticipate", "tap_edge_bashful_warm_down_accent", "tap_edge_bashful_warm_down_follow", "tap_edge_bashful_warm_down_settle"}, {"tap_edge_bashful_warm_left_orient", "tap_edge_bashful_warm_left_anticipate", "tap_edge_bashful_warm_left_accent", "tap_edge_bashful_warm_left_follow", "tap_edge_bashful_warm_left_settle"}, {"tap_edge_bashful_warm_right_orient", "tap_edge_bashful_warm_right_anticipate", "tap_edge_bashful_warm_right_accent", "tap_edge_bashful_warm_right_follow", "tap_edge_bashful_warm_right_settle"}}}, /* bashful->warm */
  {6u, 1u, {{"tap_edge_bashful_curious_center_orient", "tap_edge_bashful_curious_center_anticipate", "tap_edge_bashful_curious_center_accent", "tap_edge_bashful_curious_center_follow", "tap_edge_bashful_curious_center_settle"}, {"tap_edge_bashful_curious_up_orient", "tap_edge_bashful_curious_up_anticipate", "tap_edge_bashful_curious_up_accent", "tap_edge_bashful_curious_up_follow", "tap_edge_bashful_curious_up_settle"}, {"tap_edge_bashful_curious_down_orient", "tap_edge_bashful_curious_down_anticipate", "tap_edge_bashful_curious_down_accent", "tap_edge_bashful_curious_down_follow", "tap_edge_bashful_curious_down_settle"}, {"tap_edge_bashful_curious_left_orient", "tap_edge_bashful_curious_left_anticipate", "tap_edge_bashful_curious_left_accent", "tap_edge_bashful_curious_left_follow", "tap_edge_bashful_curious_left_settle"}, {"tap_edge_bashful_curious_right_orient", "tap_edge_bashful_curious_right_anticipate", "tap_edge_bashful_curious_right_accent", "tap_edge_bashful_curious_right_follow", "tap_edge_bashful_curious_right_settle"}}}, /* bashful->curious */
  {6u, 0u, {{"tap_edge_bashful_calm_center_orient", "tap_edge_bashful_calm_center_anticipate", "tap_edge_bashful_calm_center_accent", "tap_edge_bashful_calm_center_follow", "tap_edge_bashful_calm_center_settle"}, {"tap_edge_bashful_calm_up_orient", "tap_edge_bashful_calm_up_anticipate", "tap_edge_bashful_calm_up_accent", "tap_edge_bashful_calm_up_follow", "tap_edge_bashful_calm_up_settle"}, {"tap_edge_bashful_calm_down_orient", "tap_edge_bashful_calm_down_anticipate", "tap_edge_bashful_calm_down_accent", "tap_edge_bashful_calm_down_follow", "tap_edge_bashful_calm_down_settle"}, {"tap_edge_bashful_calm_left_orient", "tap_edge_bashful_calm_left_anticipate", "tap_edge_bashful_calm_left_accent", "tap_edge_bashful_calm_left_follow", "tap_edge_bashful_calm_left_settle"}, {"tap_edge_bashful_calm_right_orient", "tap_edge_bashful_calm_right_anticipate", "tap_edge_bashful_calm_right_accent", "tap_edge_bashful_calm_right_follow", "tap_edge_bashful_calm_right_settle"}}}, /* bashful->calm */
  {7u, 1u, {{"tap_edge_thoughtful_curious_center_orient", "tap_edge_thoughtful_curious_center_anticipate", "tap_edge_thoughtful_curious_center_accent", "tap_edge_thoughtful_curious_center_follow", "tap_edge_thoughtful_curious_center_settle"}, {"tap_edge_thoughtful_curious_up_orient", "tap_edge_thoughtful_curious_up_anticipate", "tap_edge_thoughtful_curious_up_accent", "tap_edge_thoughtful_curious_up_follow", "tap_edge_thoughtful_curious_up_settle"}, {"tap_edge_thoughtful_curious_down_orient", "tap_edge_thoughtful_curious_down_anticipate", "tap_edge_thoughtful_curious_down_accent", "tap_edge_thoughtful_curious_down_follow", "tap_edge_thoughtful_curious_down_settle"}, {"tap_edge_thoughtful_curious_left_orient", "tap_edge_thoughtful_curious_left_anticipate", "tap_edge_thoughtful_curious_left_accent", "tap_edge_thoughtful_curious_left_follow", "tap_edge_thoughtful_curious_left_settle"}, {"tap_edge_thoughtful_curious_right_orient", "tap_edge_thoughtful_curious_right_anticipate", "tap_edge_thoughtful_curious_right_accent", "tap_edge_thoughtful_curious_right_follow", "tap_edge_thoughtful_curious_right_settle"}}}, /* thoughtful->curious */
  {7u, 8u, {{"tap_edge_thoughtful_focused_center_orient", "tap_edge_thoughtful_focused_center_anticipate", "tap_edge_thoughtful_focused_center_accent", "tap_edge_thoughtful_focused_center_follow", "tap_edge_thoughtful_focused_center_settle"}, {"tap_edge_thoughtful_focused_up_orient", "tap_edge_thoughtful_focused_up_anticipate", "tap_edge_thoughtful_focused_up_accent", "tap_edge_thoughtful_focused_up_follow", "tap_edge_thoughtful_focused_up_settle"}, {"tap_edge_thoughtful_focused_down_orient", "tap_edge_thoughtful_focused_down_anticipate", "tap_edge_thoughtful_focused_down_accent", "tap_edge_thoughtful_focused_down_follow", "tap_edge_thoughtful_focused_down_settle"}, {"tap_edge_thoughtful_focused_left_orient", "tap_edge_thoughtful_focused_left_anticipate", "tap_edge_thoughtful_focused_left_accent", "tap_edge_thoughtful_focused_left_follow", "tap_edge_thoughtful_focused_left_settle"}, {"tap_edge_thoughtful_focused_right_orient", "tap_edge_thoughtful_focused_right_anticipate", "tap_edge_thoughtful_focused_right_accent", "tap_edge_thoughtful_focused_right_follow", "tap_edge_thoughtful_focused_right_settle"}}}, /* thoughtful->focused */
  {7u, 9u, {{"tap_edge_thoughtful_alert_center_orient", "tap_edge_thoughtful_alert_center_anticipate", "tap_edge_thoughtful_alert_center_accent", "tap_edge_thoughtful_alert_center_follow", "tap_edge_thoughtful_alert_center_settle"}, {"tap_edge_thoughtful_alert_up_orient", "tap_edge_thoughtful_alert_up_anticipate", "tap_edge_thoughtful_alert_up_accent", "tap_edge_thoughtful_alert_up_follow", "tap_edge_thoughtful_alert_up_settle"}, {"tap_edge_thoughtful_alert_down_orient", "tap_edge_thoughtful_alert_down_anticipate", "tap_edge_thoughtful_alert_down_accent", "tap_edge_thoughtful_alert_down_follow", "tap_edge_thoughtful_alert_down_settle"}, {"tap_edge_thoughtful_alert_left_orient", "tap_edge_thoughtful_alert_left_anticipate", "tap_edge_thoughtful_alert_left_accent", "tap_edge_thoughtful_alert_left_follow", "tap_edge_thoughtful_alert_left_settle"}, {"tap_edge_thoughtful_alert_right_orient", "tap_edge_thoughtful_alert_right_anticipate", "tap_edge_thoughtful_alert_right_accent", "tap_edge_thoughtful_alert_right_follow", "tap_edge_thoughtful_alert_right_settle"}}}, /* thoughtful->alert */
  {7u, 0u, {{"tap_edge_thoughtful_calm_center_orient", "tap_edge_thoughtful_calm_center_anticipate", "tap_edge_thoughtful_calm_center_accent", "tap_edge_thoughtful_calm_center_follow", "tap_edge_thoughtful_calm_center_settle"}, {"tap_edge_thoughtful_calm_up_orient", "tap_edge_thoughtful_calm_up_anticipate", "tap_edge_thoughtful_calm_up_accent", "tap_edge_thoughtful_calm_up_follow", "tap_edge_thoughtful_calm_up_settle"}, {"tap_edge_thoughtful_calm_down_orient", "tap_edge_thoughtful_calm_down_anticipate", "tap_edge_thoughtful_calm_down_accent", "tap_edge_thoughtful_calm_down_follow", "tap_edge_thoughtful_calm_down_settle"}, {"tap_edge_thoughtful_calm_left_orient", "tap_edge_thoughtful_calm_left_anticipate", "tap_edge_thoughtful_calm_left_accent", "tap_edge_thoughtful_calm_left_follow", "tap_edge_thoughtful_calm_left_settle"}, {"tap_edge_thoughtful_calm_right_orient", "tap_edge_thoughtful_calm_right_anticipate", "tap_edge_thoughtful_calm_right_accent", "tap_edge_thoughtful_calm_right_follow", "tap_edge_thoughtful_calm_right_settle"}}}, /* thoughtful->calm */
  {8u, 1u, {{"tap_edge_focused_curious_center_orient", "tap_edge_focused_curious_center_anticipate", "tap_edge_focused_curious_center_accent", "tap_edge_focused_curious_center_follow", "tap_edge_focused_curious_center_settle"}, {"tap_edge_focused_curious_up_orient", "tap_edge_focused_curious_up_anticipate", "tap_edge_focused_curious_up_accent", "tap_edge_focused_curious_up_follow", "tap_edge_focused_curious_up_settle"}, {"tap_edge_focused_curious_down_orient", "tap_edge_focused_curious_down_anticipate", "tap_edge_focused_curious_down_accent", "tap_edge_focused_curious_down_follow", "tap_edge_focused_curious_down_settle"}, {"tap_edge_focused_curious_left_orient", "tap_edge_focused_curious_left_anticipate", "tap_edge_focused_curious_left_accent", "tap_edge_focused_curious_left_follow", "tap_edge_focused_curious_left_settle"}, {"tap_edge_focused_curious_right_orient", "tap_edge_focused_curious_right_anticipate", "tap_edge_focused_curious_right_accent", "tap_edge_focused_curious_right_follow", "tap_edge_focused_curious_right_settle"}}}, /* focused->curious */
  {8u, 7u, {{"tap_edge_focused_thoughtful_center_orient", "tap_edge_focused_thoughtful_center_anticipate", "tap_edge_focused_thoughtful_center_accent", "tap_edge_focused_thoughtful_center_follow", "tap_edge_focused_thoughtful_center_settle"}, {"tap_edge_focused_thoughtful_up_orient", "tap_edge_focused_thoughtful_up_anticipate", "tap_edge_focused_thoughtful_up_accent", "tap_edge_focused_thoughtful_up_follow", "tap_edge_focused_thoughtful_up_settle"}, {"tap_edge_focused_thoughtful_down_orient", "tap_edge_focused_thoughtful_down_anticipate", "tap_edge_focused_thoughtful_down_accent", "tap_edge_focused_thoughtful_down_follow", "tap_edge_focused_thoughtful_down_settle"}, {"tap_edge_focused_thoughtful_left_orient", "tap_edge_focused_thoughtful_left_anticipate", "tap_edge_focused_thoughtful_left_accent", "tap_edge_focused_thoughtful_left_follow", "tap_edge_focused_thoughtful_left_settle"}, {"tap_edge_focused_thoughtful_right_orient", "tap_edge_focused_thoughtful_right_anticipate", "tap_edge_focused_thoughtful_right_accent", "tap_edge_focused_thoughtful_right_follow", "tap_edge_focused_thoughtful_right_settle"}}}, /* focused->thoughtful */
  {8u, 9u, {{"tap_edge_focused_alert_center_orient", "tap_edge_focused_alert_center_anticipate", "tap_edge_focused_alert_center_accent", "tap_edge_focused_alert_center_follow", "tap_edge_focused_alert_center_settle"}, {"tap_edge_focused_alert_up_orient", "tap_edge_focused_alert_up_anticipate", "tap_edge_focused_alert_up_accent", "tap_edge_focused_alert_up_follow", "tap_edge_focused_alert_up_settle"}, {"tap_edge_focused_alert_down_orient", "tap_edge_focused_alert_down_anticipate", "tap_edge_focused_alert_down_accent", "tap_edge_focused_alert_down_follow", "tap_edge_focused_alert_down_settle"}, {"tap_edge_focused_alert_left_orient", "tap_edge_focused_alert_left_anticipate", "tap_edge_focused_alert_left_accent", "tap_edge_focused_alert_left_follow", "tap_edge_focused_alert_left_settle"}, {"tap_edge_focused_alert_right_orient", "tap_edge_focused_alert_right_anticipate", "tap_edge_focused_alert_right_accent", "tap_edge_focused_alert_right_follow", "tap_edge_focused_alert_right_settle"}}}, /* focused->alert */
  {8u, 0u, {{"tap_edge_focused_calm_center_orient", "tap_edge_focused_calm_center_anticipate", "tap_edge_focused_calm_center_accent", "tap_edge_focused_calm_center_follow", "tap_edge_focused_calm_center_settle"}, {"tap_edge_focused_calm_up_orient", "tap_edge_focused_calm_up_anticipate", "tap_edge_focused_calm_up_accent", "tap_edge_focused_calm_up_follow", "tap_edge_focused_calm_up_settle"}, {"tap_edge_focused_calm_down_orient", "tap_edge_focused_calm_down_anticipate", "tap_edge_focused_calm_down_accent", "tap_edge_focused_calm_down_follow", "tap_edge_focused_calm_down_settle"}, {"tap_edge_focused_calm_left_orient", "tap_edge_focused_calm_left_anticipate", "tap_edge_focused_calm_left_accent", "tap_edge_focused_calm_left_follow", "tap_edge_focused_calm_left_settle"}, {"tap_edge_focused_calm_right_orient", "tap_edge_focused_calm_right_anticipate", "tap_edge_focused_calm_right_accent", "tap_edge_focused_calm_right_follow", "tap_edge_focused_calm_right_settle"}}}, /* focused->calm */
  {9u, 8u, {{"tap_edge_alert_focused_center_orient", "tap_edge_alert_focused_center_anticipate", "tap_edge_alert_focused_center_accent", "tap_edge_alert_focused_center_follow", "tap_edge_alert_focused_center_settle"}, {"tap_edge_alert_focused_up_orient", "tap_edge_alert_focused_up_anticipate", "tap_edge_alert_focused_up_accent", "tap_edge_alert_focused_up_follow", "tap_edge_alert_focused_up_settle"}, {"tap_edge_alert_focused_down_orient", "tap_edge_alert_focused_down_anticipate", "tap_edge_alert_focused_down_accent", "tap_edge_alert_focused_down_follow", "tap_edge_alert_focused_down_settle"}, {"tap_edge_alert_focused_left_orient", "tap_edge_alert_focused_left_anticipate", "tap_edge_alert_focused_left_accent", "tap_edge_alert_focused_left_follow", "tap_edge_alert_focused_left_settle"}, {"tap_edge_alert_focused_right_orient", "tap_edge_alert_focused_right_anticipate", "tap_edge_alert_focused_right_accent", "tap_edge_alert_focused_right_follow", "tap_edge_alert_focused_right_settle"}}}, /* alert->focused */
  {9u, 1u, {{"tap_edge_alert_curious_center_orient", "tap_edge_alert_curious_center_anticipate", "tap_edge_alert_curious_center_accent", "tap_edge_alert_curious_center_follow", "tap_edge_alert_curious_center_settle"}, {"tap_edge_alert_curious_up_orient", "tap_edge_alert_curious_up_anticipate", "tap_edge_alert_curious_up_accent", "tap_edge_alert_curious_up_follow", "tap_edge_alert_curious_up_settle"}, {"tap_edge_alert_curious_down_orient", "tap_edge_alert_curious_down_anticipate", "tap_edge_alert_curious_down_accent", "tap_edge_alert_curious_down_follow", "tap_edge_alert_curious_down_settle"}, {"tap_edge_alert_curious_left_orient", "tap_edge_alert_curious_left_anticipate", "tap_edge_alert_curious_left_accent", "tap_edge_alert_curious_left_follow", "tap_edge_alert_curious_left_settle"}, {"tap_edge_alert_curious_right_orient", "tap_edge_alert_curious_right_anticipate", "tap_edge_alert_curious_right_accent", "tap_edge_alert_curious_right_follow", "tap_edge_alert_curious_right_settle"}}}, /* alert->curious */
  {9u, 0u, {{"tap_edge_alert_calm_center_orient", "tap_edge_alert_calm_center_anticipate", "tap_edge_alert_calm_center_accent", "tap_edge_alert_calm_center_follow", "tap_edge_alert_calm_center_settle"}, {"tap_edge_alert_calm_up_orient", "tap_edge_alert_calm_up_anticipate", "tap_edge_alert_calm_up_accent", "tap_edge_alert_calm_up_follow", "tap_edge_alert_calm_up_settle"}, {"tap_edge_alert_calm_down_orient", "tap_edge_alert_calm_down_anticipate", "tap_edge_alert_calm_down_accent", "tap_edge_alert_calm_down_follow", "tap_edge_alert_calm_down_settle"}, {"tap_edge_alert_calm_left_orient", "tap_edge_alert_calm_left_anticipate", "tap_edge_alert_calm_left_accent", "tap_edge_alert_calm_left_follow", "tap_edge_alert_calm_left_settle"}, {"tap_edge_alert_calm_right_orient", "tap_edge_alert_calm_right_anticipate", "tap_edge_alert_calm_right_accent", "tap_edge_alert_calm_right_follow", "tap_edge_alert_calm_right_settle"}}}, /* alert->calm */
};
#endif

static inline const char *companion_browser_tap_local_state_id(
    uint8_t family, uint8_t zone)
{
  return family < 10u && zone < 5u
      ? companion_browser_tap_local_state_ids[family][zone]
      : (const char *)0;
}

static inline const char *companion_browser_legacy_transition_clip(
    uint8_t zone)
{
  return zone < 5u
      ? companion_browser_legacy_transition_clips[zone]
      : (const char *)0;
}

static inline const char *companion_browser_pointer_state_id(
    uint8_t family, uint8_t grid_x, uint8_t grid_y)
{
#if COMPANION_BROWSER_INTERACTION_HAS_PRODUCT_GENERATION
  if (family < 10u && grid_x <= 8u && grid_y <= 8u &&
      (grid_x & 1u) == 0u && (grid_y & 1u) == 0u) {
    return companion_browser_pointer_state_ids[family][grid_x / 2u]
        [grid_y / 2u];
  }
#else
  (void)family;
  (void)grid_x;
  (void)grid_y;
#endif
  return (const char *)0;
}

/* The validated product grid has canonical names. Format into the caller's
 * existing workspace so firmware need not retain 250 full strings/pointers.
 * Keep the table accessor above for callers that require stable pointers. */
static inline const char *companion_browser_pointer_state_id_format(
    char *destination, size_t destination_size,
    uint8_t family, uint8_t grid_x, uint8_t grid_y)
{
#if COMPANION_BROWSER_INTERACTION_HAS_PRODUCT_GENERATION
  static const char *const families[10] = {
      "calm", "curious", "delighted", "warm", "playful",
      "sleepy", "bashful", "thoughtful", "focused", "alert"};
  int written;
  if (destination == NULL || destination_size == 0u || family >= 10u ||
      grid_x > 8u || grid_y > 8u || (grid_x & 1u) || (grid_y & 1u))
    return (const char *)0;
  written = snprintf(destination, destination_size,
      "pointer_follow_%s_gx%u_gy%u", families[family],
      (unsigned)grid_x, (unsigned)grid_y);
  if (written >= 0 && (size_t)written < destination_size) return destination;
#else
  (void)destination;
  (void)destination_size;
  (void)family;
  (void)grid_x;
  (void)grid_y;
#endif
  return (const char *)0;
}

static inline uint8_t companion_browser_life_episode_limit(uint8_t family)
{
  return family < 10u ? companion_browser_life_episode_limits[family] : 0u;
}

static inline bool companion_browser_menu_state_id_format(
    char *destination, size_t destination_size, uint8_t locale,
    uint8_t screen, uint8_t scroll_row, uint8_t absolute_index,
    uint8_t phase, uint8_t variant)
{
  static const char *const locales[3] = {"en", "zh_cn", "zh_tw"};
  static const char *const phases[4] =
      {"normal", "ack", "processing", "result"};
  int written;
  if (destination == NULL || destination_size == 0u || locale >= 3u ||
      screen >= COMPANION_BROWSER_MENU_SCREEN_COUNT || phase >= 4u ||
      variant >= companion_browser_menu_variant_counts[screen] ||
      ((phase == 0u) != (absolute_index == 255u))) return false;
  if (phase == 0u) {
    written = variant == 0u
        ? snprintf(destination, destination_size,
                   "menu_ui_%s_s%u_o%u_normal", locales[locale],
                   (unsigned)screen, (unsigned)scroll_row)
        : snprintf(destination, destination_size,
                   "menu_ui_%s_s%u_o%u_normal_v%u", locales[locale],
                   (unsigned)screen, (unsigned)scroll_row,
                   (unsigned)variant);
  } else {
    written = variant == 0u
        ? snprintf(destination, destination_size,
                   "menu_ui_%s_s%u_o%u_%s_i%u", locales[locale],
                   (unsigned)screen, (unsigned)scroll_row, phases[phase],
                   (unsigned)absolute_index)
        : snprintf(destination, destination_size,
                   "menu_ui_%s_s%u_o%u_%s_i%u_v%u", locales[locale],
                   (unsigned)screen, (unsigned)scroll_row, phases[phase],
                   (unsigned)absolute_index, (unsigned)variant);
  }
  return written >= 0 && (size_t)written < destination_size;
}

static inline const companion_browser_menu_row_t *
companion_browser_menu_row(uint8_t screen, uint8_t index)
{
  uint8_t row;
  for (row = 0u; row < COMPANION_BROWSER_MENU_ROW_COUNT; ++row) {
    if (companion_browser_menu_rows[row].screen == screen &&
        companion_browser_menu_rows[row].index == index) {
      return &companion_browser_menu_rows[row];
    }
  }
  return (const companion_browser_menu_row_t *)0;
}

static inline const char *companion_browser_tap_edge_clip(
    uint8_t source_family, uint8_t target_family, uint8_t zone)
{
#if COMPANION_BROWSER_INTERACTION_HAS_EDGE_CLIPS
  uint16_t index;
  if (zone >= 5u) return (const char *)0;
  for (index = 0u;
       index < COMPANION_BROWSER_INTERACTION_EDGE_CLIP_COUNT;
       ++index) {
    const companion_browser_interaction_edge_clip_t *const edge =
        &companion_browser_interaction_edge_clips[index];
    if (edge->source_family == source_family &&
        edge->target_family == target_family) {
      return edge->zone_clips[zone];
    }
  }
#else
  (void)source_family;
  (void)target_family;
  (void)zone;
#endif
  return (const char *)0;
}

static inline const char *companion_browser_tap_edge_state(
    uint8_t source_family, uint8_t target_family,
    uint8_t zone, uint8_t phase)
{
#if COMPANION_BROWSER_INTERACTION_HAS_EDGE_STATES
  uint16_t index;
  if (zone >= 5u || phase >= 5u) return (const char *)0;
  for (index = 0u;
       index < COMPANION_BROWSER_INTERACTION_EDGE_STATE_COUNT;
       ++index) {
    const companion_browser_interaction_edge_state_t *const edge =
        &companion_browser_interaction_edge_states[index];
    if (edge->source_family == source_family &&
        edge->target_family == target_family) {
      return edge->zone_phase_states[zone][phase];
    }
  }
#else
  (void)source_family;
  (void)target_family;
  (void)zone;
  (void)phase;
#endif
  return (const char *)0;
}

static const companion_browser_affect_center_t
    companion_browser_affect_centers[10] = {
  {0, 0} /* calm */,
  {2, -1} /* curious */,
  {0, -2} /* delighted */,
  {-1, 0} /* warm */,
  {2, 1} /* playful */,
  {-1, 2} /* sleepy */,
  {-2, 1} /* bashful */,
  {1, -1} /* thoughtful */,
  {1, -2} /* focused */,
  {0, -2} /* alert */
};

static const uint16_t companion_browser_affect_graph[10] = {
  0x002Au, /* calm */
  0x0399u, /* curious */
  0x0019u, /* delighted */
  0x0057u, /* warm */
  0x000Fu, /* playful */
  0x0009u, /* sleepy */
  0x000Bu, /* bashful */
  0x0303u, /* thoughtful */
  0x0283u, /* focused */
  0x0103u, /* alert */
};

static const companion_browser_interaction_trace_step_t
    companion_browser_interaction_trace[COMPANION_BROWSER_INTERACTION_TRACE_COUNT] = {
  {100u, 116u, 3u, 0u, 0u, 1u}, /* 0 center */
  {100u, 116u, 7u, 7u, 1u, 0u}, /* 1 center */
  {100u, 40u, 1u, 7u, 0u, 1u}, /* 2 up */
  {100u, 40u, 9u, 9u, 1u, 0u}, /* 3 up */
  {40u, 100u, 1u, 9u, 0u, 1u}, /* 4 left */
  {160u, 100u, 6u, 6u, 1u, 0u}, /* 5 right */
  {100u, 160u, 1u, 6u, 0u, 1u}, /* 6 down */
  {100u, 116u, 8u, 8u, 1u, 0u}, /* 7 center */
};

static const companion_browser_menu_hold_milestone_t
    companion_browser_menu_hold_milestones
[COMPANION_BROWSER_INTERACTION_MENU_HOLD_MILESTONE_COUNT] = {
  {1500u, "menu_hold_1500ms"},
  {2000u, "menu_hold_2000ms"},
  {2500u, "menu_hold_2500ms"},
  {3000u, "menu_hold_3000ms"},
};

#endif /* COMPANION_BROWSER_INTERACTION_CONTRACT_H */
