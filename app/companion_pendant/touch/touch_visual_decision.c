#include "touch_visual_decision.h"

#include "companion_visual_asset_pack.h"

#include <string.h>

#if COMPANION_VISUAL_ASSET_PACK_ENABLE
static uint32_t frame_hash(const uint8_t *bytes, size_t size)
{
    uint32_t hash = UINT32_C(2166136261);
    size_t i;
    for (i = 0u; i < size; ++i) {
        hash ^= bytes[i];
        hash *= UINT32_C(16777619);
    }
    return hash;
}
#endif

static bool is_ui_assets_tap(const comp_screen_menu_t *menu,
                             const comp_touch_gesture_event_t *gesture)
{
    return menu != NULL && gesture != NULL &&
           menu->view == COMP_SCREEN_MENU_VIEW_DEVICE &&
           gesture->type == COMP_TOUCH_GESTURE_TAP &&
           gesture->end_x >= 136u && gesture->end_y >= 146u &&
           gesture->end_y < 190u;
}

const char *comp_touch_visual_event_name(companion_visual_event_t event)
{
    static const char *const names[COMPANION_VISUAL_EVENT_COUNT] = {
        "pointer_drag_left", "pointer_drag_up", "pointer_drag_right",
        "pointer_drag_down", "pointer_drag_center", "pointer_move",
        "pointer_up_or_cancel", "single_tap_commit", "stationary_pointerdown",
        "hold_complete", "early_up_cancel_blur_or_drag", "second_short_tap",
        "recording_return", "select_voice", "select_device",
        "select_connection", "select_preferences", "select_ui_assets",
        "menu_back", "menu_return", "settle"
    };
    return event < COMPANION_VISUAL_EVENT_COUNT ? names[event] : "invalid";
}

uint8_t comp_touch_visual_target_partition(uint16_t logical_x,
                                           uint16_t logical_y)
{
    if (logical_x >= COMP_TOUCH_VISUAL_CENTER_MIN_X &&
        logical_x <= COMP_TOUCH_VISUAL_CENTER_MAX_X &&
        logical_y >= COMP_TOUCH_VISUAL_CENTER_MIN_Y &&
        logical_y <= COMP_TOUCH_VISUAL_CENTER_MAX_Y) {
        return COMPANION_VISUAL_STATE_GAZE_CENTER;
    }
    if (logical_x < COMP_TOUCH_VISUAL_CENTER_MIN_X) {
        return COMPANION_VISUAL_STATE_GAZE_LEFT;
    }
    if (logical_x > COMP_TOUCH_VISUAL_CENTER_MAX_X) {
        return COMPANION_VISUAL_STATE_GAZE_RIGHT;
    }
    if (logical_y < COMP_TOUCH_VISUAL_CENTER_MIN_Y) {
        return COMPANION_VISUAL_STATE_GAZE_UP;
    }
    return COMPANION_VISUAL_STATE_GAZE_DOWN;
}

bool comp_touch_visual_process_raw(
    const comp_ft6336_touch_sample_t *sample,
    uint16_t logical_x,
    uint16_t logical_y,
    uint32_t now_ms,
    comp_touch_gesture_state_t *gesture_state,
    comp_touch_visual_runtime_t *runtime,
    comp_touch_visual_decision_t *decision)
{
    bool contact_now;
    bool explicit_release;
    bool was_hold_feedback;
    bool was_active;
    bool was_consumed;
    bool implicit_restart = false;
    bool ready;

    if (sample == NULL || gesture_state == NULL || runtime == NULL || decision == NULL) {
        return false;
    }
    memset(decision, 0, sizeof(*decision));
    contact_now = sample->touch_count > 0u &&
                  sample->event != COMP_FT6336_TOUCH_EVENT_UP;
    explicit_release = sample->touch_count > 0u &&
                       sample->event == COMP_FT6336_TOUCH_EVENT_UP;
    was_hold_feedback = gesture_state->hold_feedback_sent;
    was_active = gesture_state->active;
    was_consumed = gesture_state->consumed_until_release;

    if (contact_now && sample->event == COMP_FT6336_TOUCH_EVENT_DOWN &&
        (gesture_state->active || gesture_state->consumed_until_release)) {
        implicit_restart = true;
        ready = comp_touch_gesture_restart_contact(
            gesture_state, logical_x, logical_y, now_ms, &decision->gesture);
    } else {
        ready = comp_touch_gesture_process(
            gesture_state, contact_now, explicit_release, logical_x,
            logical_y, now_ms, &decision->gesture);
    }
    /* An implicit new-DOWN closes the previous contact.  The recognizer may
     * return the old contact's provisional TAP while restarting, but that is
     * a cancellation boundary, never a new recording/menu decision. */
    if (implicit_restart) {
        ready = false;
        decision->gesture.type = COMP_TOUCH_GESTURE_NONE;
        /* The old contact was not a released first tap.  Do not carry its
         * provisional tap across the implicit boundary into a phantom
         * recording/menu double tap. */
        gesture_state->tap_pending = false;
    }
    decision->gesture_ready = ready;

    if (ready) {
        decision->visual_event_valid = true;
        decision->visual_from_state = runtime->current_visual_state;
        switch (decision->gesture.type) {
        case COMP_TOUCH_GESTURE_TAP:
            decision->visual_event = COMPANION_VISUAL_EVENT_SINGLE_TAP_COMMIT;
            decision->visual_target_state = COMPANION_VISUAL_STATE_SINGLE_TAP_RESPONSE;
            break;
        case COMP_TOUCH_GESTURE_DOUBLE_TAP:
            decision->visual_event = COMPANION_VISUAL_EVENT_SECOND_SHORT_TAP;
            decision->visual_target_state = COMPANION_VISUAL_STATE_RECORDING_ENTRY;
            break;
        case COMP_TOUCH_GESTURE_HOLD:
            decision->visual_event = COMPANION_VISUAL_EVENT_STATIONARY_POINTERDOWN;
            decision->visual_target_state = COMPANION_VISUAL_STATE_HOLD_FEEDBACK_50;
            break;
        case COMP_TOUCH_GESTURE_LONG_PRESS:
            decision->visual_event = COMPANION_VISUAL_EVENT_HOLD_COMPLETE;
            decision->visual_target_state = COMPANION_VISUAL_STATE_MENU_ROOTS;
            break;
        case COMP_TOUCH_GESTURE_SWIPE_LEFT:
            decision->visual_event = COMPANION_VISUAL_EVENT_POINTER_DRAG_LEFT;
            decision->visual_target_state = COMPANION_VISUAL_STATE_GAZE_LEFT;
            break;
        case COMP_TOUCH_GESTURE_SWIPE_RIGHT:
            decision->visual_event = COMPANION_VISUAL_EVENT_POINTER_DRAG_RIGHT;
            decision->visual_target_state = COMPANION_VISUAL_STATE_GAZE_RIGHT;
            break;
        case COMP_TOUCH_GESTURE_SWIPE_UP:
            decision->visual_event = COMPANION_VISUAL_EVENT_POINTER_DRAG_UP;
            decision->visual_target_state = COMPANION_VISUAL_STATE_GAZE_UP;
            break;
        case COMP_TOUCH_GESTURE_SWIPE_DOWN:
            decision->visual_event = COMPANION_VISUAL_EVENT_POINTER_DRAG_DOWN;
            decision->visual_target_state = COMPANION_VISUAL_STATE_GAZE_DOWN;
            break;
        default:
            decision->visual_event_valid = false;
            break;
        }
        if (decision->visual_event_valid)
            runtime->current_visual_state = decision->visual_target_state;
    }

    if (contact_now && !ready && !gesture_state->consumed_until_release) {
        uint8_t target = comp_touch_visual_target_partition(logical_x, logical_y);
        if (target != runtime->current_visual_state) {
            decision->visual_event_valid = true;
            decision->visual_from_state = runtime->current_visual_state;
            decision->visual_event = target == COMPANION_VISUAL_STATE_GAZE_CENTER
                ? COMPANION_VISUAL_EVENT_POINTER_DRAG_CENTER
                : COMPANION_VISUAL_EVENT_POINTER_MOVE;
            decision->visual_target_state = target;
            runtime->current_visual_state = target;
        }
    }

    /* NONE is intentionally not a public gesture.  A hold-feedback release
     * or implicit new-DOWN is nevertheless a real visual cancellation and
     * must reach the controller once, rather than disappearing in the generic
     * gesture recognizer's NONE return path. */
    if (!ready && was_hold_feedback &&
        (explicit_release ||
         (contact_now && sample->event == COMP_FT6336_TOUCH_EVENT_DOWN))) {
        decision->cancellation = true;
        decision->gesture.type = COMP_TOUCH_GESTURE_NONE;
        decision->gesture.start_x = gesture_state->start_x;
        decision->gesture.start_y = gesture_state->start_y;
        decision->gesture.end_x = logical_x;
        decision->gesture.end_y = logical_y;
        decision->gesture.duration_ms = (uint16_t)(now_ms - gesture_state->start_ms);
        decision->visual_event_valid = true;
        decision->visual_from_state = runtime->current_visual_state;
        decision->visual_event = COMPANION_VISUAL_EVENT_EARLY_UP_CANCEL_BLUR_OR_DRAG;
        decision->visual_target_state = COMPANION_VISUAL_STATE_CENTERED_REST;
        runtime->current_visual_state = COMPANION_VISUAL_STATE_CENTERED_REST;
        runtime->cancellation_emitted = true;
    } else if (!ready && ((explicit_release && (was_active || was_consumed)) ||
                          (contact_now && sample->event == COMP_FT6336_TOUCH_EVENT_DOWN && was_active))) {
        decision->cancellation = true;
        decision->gesture.type = COMP_TOUCH_GESTURE_NONE;
        decision->visual_event_valid = true;
        decision->visual_from_state = runtime->current_visual_state;
        decision->visual_event = COMPANION_VISUAL_EVENT_POINTER_UP_OR_CANCEL;
        decision->visual_target_state = COMPANION_VISUAL_STATE_CENTERED_REST;
        runtime->current_visual_state = COMPANION_VISUAL_STATE_CENTERED_REST;
        runtime->cancellation_emitted = true;
    }
    return ready || decision->cancellation || decision->visual_event_valid;
}

bool comp_touch_visual_cancel(
    comp_touch_gesture_state_t *gesture_state,
    comp_touch_visual_runtime_t *runtime,
    comp_touch_visual_cancel_kind_t kind,
    comp_touch_visual_decision_t *decision)
{
    if (gesture_state == NULL || runtime == NULL || decision == NULL) return false;
    memset(decision, 0, sizeof(*decision));
    decision->cancellation = true;
    decision->visual_event_valid = true;
    decision->visual_from_state = runtime->current_visual_state;
    decision->visual_target_state = COMPANION_VISUAL_STATE_CENTERED_REST;
    decision->visual_event = kind == COMP_TOUCH_VISUAL_CANCEL_SETTLE
        ? COMPANION_VISUAL_EVENT_SETTLE
        : kind == COMP_TOUCH_VISUAL_CANCEL_RECORDING_RETURN
        ? COMPANION_VISUAL_EVENT_RECORDING_RETURN
        : kind == COMP_TOUCH_VISUAL_CANCEL_TRANSPORT_BLUR
            ? COMPANION_VISUAL_EVENT_EARLY_UP_CANCEL_BLUR_OR_DRAG
            : COMPANION_VISUAL_EVENT_POINTER_UP_OR_CANCEL;
    runtime->current_visual_state = COMPANION_VISUAL_STATE_CENTERED_REST;
    runtime->cancellation_emitted = true;
    comp_touch_gesture_init(gesture_state, &gesture_state->config);
    return true;
}

bool comp_touch_visual_emit_decision(
    const comp_touch_visual_decision_t *decision,
    const comp_screen_menu_t *menu,
    const comp_touch_visual_sinks_t *sinks)
{
    uint32_t previous_hash = 0u;
    uint32_t current_hash = 0u;
#if COMPANION_VISUAL_ASSET_PACK_ENABLE
    const uint8_t *previous;
    const uint8_t *current;
#endif
    if (decision == NULL || sinks == NULL || sinks->event == NULL ||
        !decision->visual_event_valid) return false;
#if COMPANION_VISUAL_ASSET_PACK_ENABLE
    previous = companion_visual_frame_for_state(
        (companion_visual_state_t)decision->visual_from_state);
    current = companion_visual_frame_for_state(
        (companion_visual_state_t)decision->visual_target_state);
    if (previous != NULL && current != NULL) {
        previous_hash = frame_hash(previous, COMPANION_VISUAL_FRAME_BYTES);
        current_hash = frame_hash(current, COMPANION_VISUAL_FRAME_BYTES);
    }
#endif
    if (!sinks->event(sinks->context, decision->visual_event,
                     decision->gesture.duration_ms, 41u,
                     decision->visual_target_state)) return false;
    if (sinks->route != NULL && decision->menu_result.changed)
        sinks->route(sinks->context, &decision->menu_result);
    if (sinks->render != NULL && menu != NULL)
        sinks->render(sinks->context, menu);
    if (sinks->frame != NULL)
        sinks->frame(sinks->context, decision->visual_from_state,
                     decision->visual_target_state, previous_hash, current_hash);
    return true;
}

bool comp_touch_visual_apply_menu(
    comp_screen_menu_t *menu,
    comp_touch_visual_decision_t *decision)
{
    if (menu == NULL || decision == NULL || !decision->gesture_ready) {
        return false;
    }
    decision->ui_assets_selected = is_ui_assets_tap(menu, &decision->gesture);
    if (decision->gesture.type == COMP_TOUCH_GESTURE_TAP) {
        /* This is the same production menu hit test used by board main. */
        decision->menu_result = comp_screen_menu_tap(
            menu, decision->gesture.end_x, decision->gesture.end_y);
    } else {
        decision->menu_result = comp_screen_menu_gesture(menu,
                                                         &decision->gesture);
    }
    if (decision->ui_assets_selected) {
        decision->visual_event = COMPANION_VISUAL_EVENT_SELECT_UI_ASSETS;
        decision->visual_target_state = COMPANION_VISUAL_STATE_MENU_DEVICE_UI_ASSETS;
        decision->visual_event_valid = true;
    } else if (decision->menu_result.action == COMP_SCREEN_MENU_ACTION_EXIT_DAILY) {
        decision->visual_event = COMPANION_VISUAL_EVENT_MENU_RETURN;
        decision->visual_target_state = COMPANION_VISUAL_STATE_MENU_RETURN_REST;
        decision->visual_event_valid = true;
    } else if (decision->menu_result.changed) {
        decision->visual_event_valid = true;
        switch (decision->menu_result.view) {
        case COMP_SCREEN_MENU_VIEW_RECORD:
            decision->visual_event = COMPANION_VISUAL_EVENT_SELECT_VOICE;
            decision->visual_target_state = COMPANION_VISUAL_STATE_MENU_VOICE; break;
        case COMP_SCREEN_MENU_VIEW_DEVICE:
            decision->visual_event = COMPANION_VISUAL_EVENT_SELECT_DEVICE;
            decision->visual_target_state = COMPANION_VISUAL_STATE_MENU_DEVICE; break;
        case COMP_SCREEN_MENU_VIEW_PHONE:
            decision->visual_event = COMPANION_VISUAL_EVENT_SELECT_CONNECTION;
            decision->visual_target_state = COMPANION_VISUAL_STATE_MENU_CONNECTION; break;
        case COMP_SCREEN_MENU_VIEW_PREFERENCES:
            decision->visual_event = COMPANION_VISUAL_EVENT_SELECT_PREFERENCES;
            decision->visual_target_state = COMPANION_VISUAL_STATE_MENU_PREFERENCES; break;
        case COMP_SCREEN_MENU_VIEW_HOME:
            decision->visual_event = decision->menu_result.action ==
                COMP_SCREEN_MENU_ACTION_EXIT_DAILY
                ? COMPANION_VISUAL_EVENT_MENU_RETURN
                : COMPANION_VISUAL_EVENT_MENU_BACK;
            decision->visual_target_state = COMPANION_VISUAL_STATE_MENU_RETURN_REST; break;
        default:
            decision->visual_event = COMPANION_VISUAL_EVENT_SETTLE;
            decision->visual_target_state = COMPANION_VISUAL_STATE_CENTERED_REST; break;
        }
    }
    return true;
}
