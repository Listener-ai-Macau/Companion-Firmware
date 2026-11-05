#include "touch_visual_decision.h"
#include "screen_menu.h"
#include "companion_browser_interaction_contract.h"

#include <stdio.h>

#define CHECK(condition, message)       \
    do {                                \
        if (!(condition)) {             \
            fprintf(stderr, "%s\n", message); \
            return 2;                   \
        }                               \
    } while (0)

static comp_ft6336_touch_sample_t report(comp_ft6336_touch_event_t event,
                                         uint8_t touch_count)
{
    comp_ft6336_touch_sample_t sample = {
        .touch_count = touch_count,
        .event = event,
        .touch_id = 0u,
        .x = touch_count == 0u ? 0u : 147u,
        .y = touch_count == 0u ? 0u : 169u,
    };
    return sample;
}

static unsigned browser_field_diff_count(
    const comp_screen_menu_browser_state_t *left,
    const comp_screen_menu_browser_state_t *right)
{
    unsigned count = 0u;
#define COUNT_DIFF(field) count += left->field != right->field ? 1u : 0u
    COUNT_DIFF(link_connected);
    COUNT_DIFF(silent_auto_stop);
    COUNT_DIFF(auto_reconnect);
    COUNT_DIFF(clock_24_hour);
    COUNT_DIFF(gaze_follow);
    COUNT_DIFF(natural_blink);
    COUNT_DIFF(auto_sleep_minutes);
    COUNT_DIFF(recording_limit_minutes);
    COUNT_DIFF(recorder_profile);
    COUNT_DIFF(interaction_level);
    COUNT_DIFF(quiet_hours);
    COUNT_DIFF(recording_gesture);
    COUNT_DIFF(time_zone_offset_minutes);
    COUNT_DIFF(recording_count);
    COUNT_DIFF(recording_storage_kb);
    COUNT_DIFF(battery_percent);
#undef COUNT_DIFF
    return count;
}

static bool tap_browser_setting_once(comp_screen_menu_t *menu,
                                     uint8_t screen,
                                     uint8_t item)
{
    comp_screen_menu_browser_state_t before;
    comp_screen_menu_result_t result;
    uint32_t revision;
    uint8_t index;
    uint8_t page;
    uint16_t y;

    if (menu == NULL || screen >= COMPANION_BROWSER_MENU_SCREEN_COUNT) {
        return false;
    }
    for (index = 0u; index < companion_browser_menu_item_counts[screen];
         ++index) {
        const companion_browser_menu_row_t *row =
            companion_browser_menu_row(screen, index);
        if (row != NULL && row->item == item) {
            break;
        }
    }
    if (index >= companion_browser_menu_item_counts[screen]) {
        return false;
    }
    page = index < COMPANION_BROWSER_MENU_VISIBLE_ROWS
               ? 0u
               : (uint8_t)(index - COMPANION_BROWSER_MENU_VISIBLE_ROWS + 1u);
    y = (uint16_t)(45u + (uint16_t)(index - page) * 40u + 20u);
    menu->view = (comp_screen_menu_view_t)(
        COMP_SCREEN_MENU_VIEW_BROWSER_HOME + screen);
    menu->home_page = page;
    before = menu->browser;
    revision = menu->revision;
    result = comp_screen_menu_tap(menu, 100u, y);
    return result.changed &&
           result.action == COMP_SCREEN_MENU_ACTION_BROWSER_SETTING_CHANGED &&
           result.browser_item == item && menu->revision == revision + 1u &&
           browser_field_diff_count(&before, &menu->browser) == 1u;
}

static bool browser_setting_event_matrix(void)
{
    comp_screen_menu_t menu;
    comp_screen_menu_result_t result;
    uint32_t revision;

    comp_screen_menu_init(&menu);
    if (!tap_browser_setting_once(
            &menu, 1u, COMPANION_BROWSER_MENU_ITEM_AUTO_STOP) ||
        !tap_browser_setting_once(
            &menu, 1u, COMPANION_BROWSER_MENU_ITEM_RECORDER_PROFILE) ||
        !tap_browser_setting_once(
            &menu, 1u, COMPANION_BROWSER_MENU_ITEM_RECORDING_LIMIT) ||
        !tap_browser_setting_once(
            &menu, 2u, COMPANION_BROWSER_MENU_ITEM_CLOCK_FORMAT) ||
        !tap_browser_setting_once(
            &menu, 3u, COMPANION_BROWSER_MENU_ITEM_AUTO_RECONNECT) ||
        !tap_browser_setting_once(
            &menu, 4u, COMPANION_BROWSER_MENU_ITEM_TIME_ZONE) ||
        !tap_browser_setting_once(
            &menu, 4u, COMPANION_BROWSER_MENU_ITEM_QUIET_HOURS) ||
        !tap_browser_setting_once(
            &menu, 5u, COMPANION_BROWSER_MENU_ITEM_EDGE_PULL) ||
        !tap_browser_setting_once(
            &menu, 8u, COMPANION_BROWSER_MENU_ITEM_INTERACTION_LEVEL) ||
        !tap_browser_setting_once(
            &menu, 8u, COMPANION_BROWSER_MENU_ITEM_GAZE_FOLLOW) ||
        !tap_browser_setting_once(
            &menu, 8u, COMPANION_BROWSER_MENU_ITEM_NATURAL_BLINK) ||
        !tap_browser_setting_once(
            &menu, 10u, COMPANION_BROWSER_MENU_ITEM_AUTO_SLEEP)) {
        return false;
    }
    if (menu.browser.silent_auto_stop || menu.browser.auto_reconnect ||
        menu.browser.clock_24_hour || menu.browser.gaze_follow ||
        menu.browser.natural_blink ||
        menu.browser.auto_sleep_minutes != 5u ||
        menu.browser.recording_limit_minutes != 60u ||
        menu.browser.recorder_profile !=
            COMP_SCREEN_MENU_RECORDER_PROFILE_MEETING ||
        menu.browser.interaction_level !=
            COMP_SCREEN_MENU_INTERACTION_LIVELY ||
        menu.browser.quiet_hours != COMP_SCREEN_MENU_QUIET_HOURS_22_08 ||
        menu.browser.recording_gesture !=
            COMP_SCREEN_MENU_RECORDING_GESTURE_EDGE_PULL ||
        menu.browser.time_zone_offset_minutes != 0) {
        return false;
    }

    /* Re-selecting the active radio option is one input and zero state
     * transitions; it must not consume a persistence generation. */
    menu.view = COMP_SCREEN_MENU_VIEW_BROWSER_RECORDING_GESTURE;
    menu.home_page = 0u;
    revision = menu.revision;
    result = comp_screen_menu_tap(&menu, 100u, 105u);
    return !result.changed && menu.revision == revision;
}

static bool browser_navigation_context_matrix(void)
{
    comp_screen_menu_t menu;
    comp_screen_menu_result_t result;
    comp_touch_gesture_event_t right = {
        .type = COMP_TOUCH_GESTURE_SWIPE_RIGHT,
        .start_x = 80u,
        .end_x = 160u,
    };

    comp_screen_menu_init(&menu);
    if (!comp_screen_menu_navigate_to(
            &menu, COMP_SCREEN_MENU_VIEW_BROWSER_HOME)) {
        return false;
    }
    /* Root page 4 -> Storage page 2 -> Clear Recordings. */
    menu.home_page = 4u;
    result = comp_screen_menu_tap(&menu, 100u, 65u);
    if (!result.changed ||
        result.view != COMP_SCREEN_MENU_VIEW_BROWSER_STORAGE ||
        result.home_page != 0u || menu.navigation_depth != 1u) {
        return false;
    }
    menu.home_page = 2u;
    result = comp_screen_menu_tap(&menu, 100u, 65u);
    if (!result.changed ||
        result.view != COMP_SCREEN_MENU_VIEW_BROWSER_CLEAR_RECORDINGS ||
        menu.navigation_depth != 2u) {
        return false;
    }
    /* Header back restores the exact parent page. */
    result = comp_screen_menu_tap(&menu, 10u, 20u);
    if (!result.changed ||
        result.view != COMP_SCREEN_MENU_VIEW_BROWSER_STORAGE ||
        result.home_page != 2u || menu.navigation_depth != 1u) {
        return false;
    }
    /* The explicit BACK row uses the same history. */
    result = comp_screen_menu_tap(&menu, 100u, 65u);
    if (!result.changed ||
        result.view != COMP_SCREEN_MENU_VIEW_BROWSER_CLEAR_RECORDINGS) {
        return false;
    }
    result = comp_screen_menu_tap(&menu, 100u, 145u);
    if (!result.changed ||
        result.view != COMP_SCREEN_MENU_VIEW_BROWSER_STORAGE ||
        result.home_page != 2u) {
        return false;
    }
    /* Right-swipe restores root page 4; at root it exits without resetting it. */
    result = comp_screen_menu_gesture(&menu, &right);
    if (!result.changed ||
        result.view != COMP_SCREEN_MENU_VIEW_BROWSER_HOME ||
        result.home_page != 4u || menu.navigation_depth != 0u) {
        return false;
    }
    result = comp_screen_menu_gesture(&menu, &right);
    if (!result.changed ||
        result.action != COMP_SCREEN_MENU_ACTION_EXIT_DAILY ||
        result.view != COMP_SCREEN_MENU_VIEW_BROWSER_HOME ||
        result.home_page != 4u) {
        return false;
    }

    /* Recording Gesture is reachable from two parents. History, not a static
     * guess, must return it to the actual entry screen. */
    menu.home_page = 2u;
    result = comp_screen_menu_tap(&menu, 100u, 65u);
    if (!result.changed ||
        result.view != COMP_SCREEN_MENU_VIEW_BROWSER_INTERACTION) {
        return false;
    }
    result = comp_screen_menu_tap(&menu, 100u, 105u);
    if (!result.changed ||
        result.view != COMP_SCREEN_MENU_VIEW_BROWSER_RECORDING_GESTURE) {
        return false;
    }
    result = comp_screen_menu_gesture(&menu, &right);
    if (!result.changed ||
        result.view != COMP_SCREEN_MENU_VIEW_BROWSER_INTERACTION ||
        result.home_page != 0u) {
        return false;
    }

    /* A stale saved page from a changed generated catalog is clamped to the
     * current parent screen's last valid page instead of indexing past it. */
    result = comp_screen_menu_tap(&menu, 100u, 105u);
    if (!result.changed || menu.navigation_depth == 0u) {
        return false;
    }
    menu.navigation_pages[menu.navigation_depth - 1u] = 0xFFu;
    result = comp_screen_menu_gesture(&menu, &right);
    return result.changed &&
           result.view == COMP_SCREEN_MENU_VIEW_BROWSER_INTERACTION &&
           result.home_page == 2u;
}

int main(void)
{
    const comp_touch_gesture_config_t config = {
        .tap_max_move_px = 24u,
        .long_press_max_move_px = 40u,
        .swipe_min_move_px = 30u,
        .horizontal_swipe_min_move_px = 36u,
        .axis_lock_min_move_px = 10u,
        .axis_slop_px = 5u,
        .tap_max_duration_ms = 1100u,
        .swipe_max_duration_ms = 1400u,
        .hold_feedback_min_duration_ms = 1000u,
        .long_press_min_duration_ms = 3000u,
        .double_tap_max_gap_ms = 350u,
        .double_tap_max_move_px = 32u,
        .axis_dominance_percent = 140u,
        .min_contact_samples = 1u,
        .release_debounce_samples = 2u,
    };
    comp_touch_gesture_state_t gesture;
    comp_touch_visual_runtime_t runtime = {
        COMPANION_VISUAL_STATE_CENTERED_REST, false};
    comp_touch_visual_decision_t decision;
    comp_ft6336_touch_sample_t sample;
    uint32_t cycle;

    CHECK(comp_screen_menu_self_test(),
          "screen menu touch-slop/row-snap self-test failed");
    CHECK(comp_screen_menu_browser_runtime_self_test(),
          "source-pack browser screen-menu self-test failed");
    CHECK(browser_setting_event_matrix(),
          "browser setting one-input/one-transition matrix failed");
    CHECK(browser_navigation_context_matrix(),
          "browser navigation context/back-path matrix failed");
    comp_touch_gesture_init(&gesture, &config);
    for (cycle = 0u; cycle < 1000u; ++cycle) {
        const uint32_t start_ms = 100u + cycle * 2000u;

        sample = report(COMP_FT6336_TOUCH_EVENT_DOWN, 1u);
        CHECK(!comp_touch_visual_process_raw(&sample, sample.x, sample.y,
                                             start_ms, &gesture, &runtime,
                                             &decision) ||
                  !decision.cancellation,
              "DOWN unexpectedly cancelled");

        sample = report(COMP_FT6336_TOUCH_EVENT_CONTACT, 1u);
        CHECK(comp_touch_visual_process_raw(&sample, sample.x, sample.y,
                                            start_ms + 1016u, &gesture,
                                            &runtime, &decision) &&
                  decision.gesture_ready &&
                  decision.gesture.type == COMP_TOUCH_GESTURE_HOLD,
              "hold feedback was not recognized");

        sample = report(COMP_FT6336_TOUCH_EVENT_NONE, 0u);
        CHECK(!comp_touch_visual_process_raw(&sample, 0u, 0u,
                                             start_ms + 1500u, &gesture,
                                             &runtime, &decision),
              "first debounce sample completed release early");
        CHECK(comp_touch_visual_process_raw(&sample, 0u, 0u,
                                            start_ms + 1508u, &gesture,
                                            &runtime, &decision) &&
                  decision.cancellation && !decision.gesture_ready &&
                  !gesture.active && !gesture.consumed_until_release &&
                  !gesture.hold_feedback_sent,
              "debounced zero-contact release did not cancel hold");
        CHECK(!comp_touch_visual_process_raw(&sample, 0u, 0u,
                                             start_ms + 1516u, &gesture,
                                             &runtime, &decision),
              "zero-contact release emitted duplicate cancellation");
    }

    puts("PASS: 1000 zero-contact FT6336 hold retries cancel exactly once; "
         "menu header/BACK/right-swipe restore nested parent pages and clamp "
         "stale positions.");
    return 0;
}
