#define _CRT_SECURE_NO_WARNINGS
#include "touch_visual_decision.h"
#include "touch_visual_board_dispatch.h"
#include "companion_visual_runtime_adapter.h"
#include "companion_visual_asset_pack.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    unsigned reports;
    unsigned decisions;
    unsigned cancellations;
    unsigned menus;
    unsigned ui_assets;
    unsigned event_records;
    unsigned duplicate_input;
    unsigned missing_input;
    unsigned pair_records;
    unsigned noop_records;
    unsigned frame_hash_records;
    unsigned nonzero_frame_hash_records;
    unsigned render_records;
    unsigned route_records;
    unsigned board_dispatches;
    bool seen_events[COMPANION_VISUAL_EVENT_COUNT];
    uint8_t visual_state;
    companion_visual_event_t current_event;
    char event_names[2048];
    char pair_names[4096];
    char noop_names[2048];
} trace_t;

static bool g_menu_visible;
static const char *g_mutation;

static void append_name(char *buffer, size_t size, const char *name)
{
    size_t used = strlen(buffer);
    (void)snprintf(buffer + used, used < size ? size - used : 0u,
                   "%s%s", used == 0u ? "" : ",", name);
}

static bool sink_event(void *context, companion_visual_event_t event,
                       uint32_t elapsed_ms, uint16_t move_px,
                       uint8_t target_state)
{
    trace_t *trace = (trace_t *)context;
    bool was_seen = trace->seen_events[event];
    (void)elapsed_ms;
    (void)move_px;
    trace->seen_events[event] = true;
    trace->current_event = event;
    if (!was_seen)
        append_name(trace->event_names, sizeof(trace->event_names),
                    comp_touch_visual_event_name(event));
    trace->event_records = 0u;
    for (unsigned i = 0u; i < COMPANION_VISUAL_EVENT_COUNT; ++i)
        if (trace->seen_events[i]) trace->event_records++;
    trace->pair_records++;
    if (event == COMPANION_VISUAL_EVENT_SELECT_UI_ASSETS) trace->ui_assets++;
    trace->visual_state = target_state;
    return true;
}

static void sink_route(void *context, const comp_screen_menu_result_t *result)
{
    trace_t *trace = (trace_t *)context;
    (void)result;
    trace->menus++;
    trace->route_records++;
}

static void sink_render(void *context, const comp_screen_menu_t *menu)
{
    trace_t *trace = (trace_t *)context;
    (void)menu;
    trace->render_records++;
}

static void sink_frame(void *context, uint8_t from_state, uint8_t to_state,
                       uint32_t previous_hash, uint32_t current_hash)
{
    trace_t *trace = (trace_t *)context;
    (void)from_state;
    (void)to_state;
    if (g_mutation != NULL && strcmp(g_mutation, "no_frame_hash") == 0)
        return;
    trace->frame_hash_records++;
    {
        char name[96];
        (void)snprintf(name, sizeof(name), "%s:%u->%u",
                       comp_touch_visual_event_name(trace->current_event),
                       (unsigned)from_state, (unsigned)to_state);
        append_name(trace->pair_names, sizeof(trace->pair_names), name);
    }
    if (previous_hash != 0u && current_hash != 0u) trace->nonzero_frame_hash_records++;
    if (previous_hash == current_hash && previous_hash != 0u) {
        trace->noop_records++;
        append_name(trace->noop_names, sizeof(trace->noop_names),
                    comp_touch_visual_event_name(trace->current_event));
    }
}

static void emit_decision(trace_t *trace, comp_screen_menu_t *menu,
                          comp_touch_visual_decision_t *decision)
{
    comp_touch_visual_board_dispatch_sinks_t sinks = {
        sink_event, sink_route, sink_render, sink_frame, trace};
    if (decision->gesture_ready && g_menu_visible)
        (void)comp_touch_visual_apply_menu(menu, decision);
    if (g_mutation != NULL && strcmp(g_mutation, "drop_decision") == 0 &&
        trace->board_dispatches == 8u)
        return;
    if (g_mutation != NULL && strcmp(g_mutation, "bypass_route_render") == 0) {
        sinks.route = NULL;
        sinks.render = NULL;
    }
    if (g_mutation != NULL && strcmp(g_mutation, "altered_target") == 0 &&
        trace->board_dispatches == 8u)
        decision->visual_target_state = 255u;
    trace->board_dispatches++;
    (void)comp_touch_visual_board_dispatch(decision, menu, &sinks);
    if (g_mutation != NULL && strcmp(g_mutation, "duplicate_decision") == 0 &&
        trace->board_dispatches == 9u) {
        trace->board_dispatches++;
        (void)comp_touch_visual_board_dispatch(decision, menu, &sinks);
    }
    if (g_mutation != NULL && strcmp(g_mutation, "duplicate_sink") == 0 &&
        trace->board_dispatches == 9u)
        (void)sink_event(trace, decision->visual_event, 0u, 0u,
                         decision->visual_target_state);
    if (g_mutation != NULL && strcmp(g_mutation, "legacy_remap") == 0 &&
        trace->board_dispatches == 9u)
        (void)sink_event(trace, decision->visual_event, 0u, 0u,
                         decision->visual_target_state);
    if (g_mutation != NULL && strcmp(g_mutation, "direct_injection") == 0 &&
        trace->reports == 1u)
        (void)sink_event(trace, decision->visual_event, 0u, 0u,
                         decision->visual_target_state);
}

static comp_ft6336_touch_sample_t report(comp_ft6336_touch_event_t event,
                                         uint16_t x, uint16_t y)
{
    comp_ft6336_touch_sample_t sample = {1u, event, 0u, x, y};
    return sample;
}

static bool replay_zero_contact_hold_cancel(void)
{
    const comp_touch_gesture_config_t config = {
        24u, 40u, 30u, 10u, 5u, 1100u, 1400u, 1000u, 3000u,
        350u, 32u, 140u, 1u, 2u};
    comp_touch_gesture_state_t gesture;
    comp_touch_visual_runtime_t runtime = {
        COMPANION_VISUAL_STATE_CENTERED_REST, false};
    comp_touch_visual_decision_t decision;
    comp_ft6336_touch_sample_t sample;

    comp_touch_gesture_init(&gesture, &config);
    sample = report(COMP_FT6336_TOUCH_EVENT_DOWN, 147u, 169u);
    if (comp_touch_visual_process_raw(&sample, sample.x, sample.y, 100u,
                                      &gesture, &runtime, &decision) &&
        decision.cancellation) {
        return false;
    }
    sample = report(COMP_FT6336_TOUCH_EVENT_CONTACT, 147u, 169u);
    if (!comp_touch_visual_process_raw(&sample, sample.x, sample.y, 1116u,
                                       &gesture, &runtime, &decision) ||
        !decision.gesture_ready ||
        decision.gesture.type != COMP_TOUCH_GESTURE_HOLD) {
        return false;
    }
    sample.touch_count = 0u;
    sample.event = COMP_FT6336_TOUCH_EVENT_NONE;
    if (comp_touch_visual_process_raw(&sample, 0u, 0u, 1600u,
                                      &gesture, &runtime, &decision) &&
        decision.cancellation) {
        return false;
    }
    if (!comp_touch_visual_process_raw(&sample, 0u, 0u, 1608u,
                                       &gesture, &runtime, &decision) ||
        !decision.cancellation || decision.gesture_ready ||
        gesture.active || gesture.hold_feedback_sent) {
        return false;
    }
    if (comp_touch_visual_process_raw(&sample, 0u, 0u, 1616u,
                                      &gesture, &runtime, &decision) &&
        decision.cancellation) {
        return false;
    }
    return true;
}

static bool feed(trace_t *trace, comp_touch_gesture_state_t *gesture,
                 comp_screen_menu_t *menu, comp_ft6336_touch_sample_t sample,
                 uint32_t now, unsigned *sequence)
{
    comp_touch_visual_decision_t decision;
    static comp_touch_visual_runtime_t visual_runtime = {
        COMPANION_VISUAL_STATE_CENTERED_REST, false};
    trace->reports++;
    if (g_mutation != NULL && strcmp(g_mutation, "missing_raw") == 0 &&
        trace->reports == 10u) {
        trace->missing_input++;
        return true;
    }
    if (g_mutation != NULL && strcmp(g_mutation, "duplicate_raw") == 0 &&
        trace->reports == 10u) {
        comp_touch_visual_decision_t duplicate;
        trace->duplicate_input++;
        if (comp_touch_visual_process_raw(&sample, sample.x, sample.y, now,
                                          gesture, &visual_runtime, &duplicate) &&
            duplicate.visual_event_valid)
            emit_decision(trace, menu, &duplicate);
    }
    if (!comp_touch_visual_process_raw(&sample, sample.x, sample.y, now,
                                       gesture, &visual_runtime, &decision)) {
        return true;
    }
    trace->decisions++;
    if (decision.cancellation) trace->cancellations++;
    if (decision.visual_event_valid) {
        (*sequence)++;
        emit_decision(trace, menu, &decision);
    }
    return true;
}

static bool tap(trace_t *trace, comp_touch_gesture_state_t *gesture,
                comp_screen_menu_t *menu, uint16_t x, uint16_t y,
                uint32_t start, unsigned *sequence)
{
    return feed(trace, gesture, menu, report(COMP_FT6336_TOUCH_EVENT_DOWN, x, y),
                start, sequence) &&
           feed(trace, gesture, menu, report(COMP_FT6336_TOUCH_EVENT_UP, x, y),
                start + 650u, sequence);
}

int main(void)
{
    comp_touch_gesture_state_t gesture;
    comp_screen_menu_t menu;
    comp_touch_gesture_config_t config = {
        24u, 40u, 30u, 10u, 5u, 1100u, 1400u, 650u, 3000u,
        650u, 40u, 120u, 1u, 1u};
    trace_t trace = {0};
    unsigned sequence = 0u;
    const bool zero_contact_hold_cancel = replay_zero_contact_hold_cancel();
    g_mutation = getenv("COMP_REQ_501_MUTATION");

    comp_touch_gesture_init(&gesture, &config);
    comp_screen_menu_init(&menu);

    /* All observations below start as FT6336 logical reports. */
    tap(&trace, &gesture, &menu, 100u, 100u, 0u, &sequence);
    tap(&trace, &gesture, &menu, 100u, 100u, 1300u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_DOWN, 100u, 100u),
         2600u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_CONTACT, 100u, 100u),
         3250u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_UP, 100u, 100u),
         3300u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_DOWN, 20u, 100u),
         4000u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_CONTACT, 180u, 100u),
         4100u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_UP, 180u, 100u),
         4200u, &sequence);
    comp_touch_gesture_init(&gesture, &config);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_DOWN, 180u, 100u),
         4300u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_CONTACT, 20u, 100u),
         4400u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_UP, 20u, 100u),
         4500u, &sequence);
    comp_touch_gesture_init(&gesture, &config);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_DOWN, 100u, 180u),
         4600u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_CONTACT, 100u, 20u),
         4700u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_UP, 100u, 20u),
         4800u, &sequence);
    comp_touch_gesture_init(&gesture, &config);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_DOWN, 100u, 20u),
         4900u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_CONTACT, 100u, 180u),
         5000u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_UP, 100u, 180u),
         5100u, &sequence);
    comp_touch_gesture_init(&gesture, &config);
    tap(&trace, &gesture, &menu, 100u, 100u, 5150u, &sequence);
    tap(&trace, &gesture, &menu, 100u, 100u, 5700u, &sequence);
    comp_touch_gesture_init(&gesture, &config);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_DOWN, 100u, 100u),
         6400u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_CONTACT, 100u, 100u),
         9400u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_UP, 100u, 100u),
         9450u, &sequence);
    /* Explicitly exercise the production menu hit test and UI-assets route. */
    g_menu_visible = true;
    comp_touch_gesture_init(&gesture, &config);
    comp_screen_menu_init(&menu);
    (void)tap(&trace, &gesture, &menu, 100u, 120u, 5000u, &sequence);
    (void)tap(&trace, &gesture, &menu, 160u, 160u, 6300u, &sequence);
    comp_touch_gesture_init(&gesture, &config);
    comp_touch_gesture_init(&gesture, &config);
    g_menu_visible = false;
    comp_screen_menu_init(&menu);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_DOWN, 20u, 100u),
         7000u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_CONTACT, 180u, 100u),
         7100u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_UP, 180u, 100u),
         7200u, &sequence);
    comp_touch_gesture_init(&gesture, &config);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_DOWN, 100u, 100u),
         7300u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_UP, 100u, 100u),
         7750u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_DOWN, 100u, 100u),
         7800u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_UP, 100u, 100u),
         8200u, &sequence);
    comp_touch_gesture_init(&gesture, &config);
    g_menu_visible = true;
    comp_screen_menu_init(&menu);
    (void)tap(&trace, &gesture, &menu, 100u, 45u, 8000u, &sequence);
    comp_screen_menu_init(&menu);
    (void)tap(&trace, &gesture, &menu, 100u, 150u, 8700u, &sequence);
    comp_screen_menu_init(&menu);
    (void)tap(&trace, &gesture, &menu, 100u, 120u, 9400u, &sequence);
    (void)tap(&trace, &gesture, &menu, 10u, 16u, 10100u, &sequence);
    comp_screen_menu_init(&menu);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_DOWN, 112u, 100u),
         11500u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_CONTACT, 130u, 100u),
         11600u, &sequence);
    {
        comp_touch_visual_decision_t cancel;
        comp_touch_visual_runtime_t runtime = {
            COMPANION_VISUAL_STATE_MENU_DEVICE_UI_ASSETS, false};
        comp_touch_visual_cancel(&gesture, &runtime,
                                 COMP_TOUCH_VISUAL_CANCEL_TRANSPORT_BLUR,
                                 &cancel);
        emit_decision(&trace, &menu, &cancel);
        comp_touch_visual_cancel(&gesture, &runtime,
                                 COMP_TOUCH_VISUAL_CANCEL_SETTLE, &cancel);
        emit_decision(&trace, &menu, &cancel);
        comp_touch_visual_cancel(&gesture, &runtime,
                                 COMP_TOUCH_VISUAL_CANCEL_RECORDING_RETURN,
                                 &cancel);
        emit_decision(&trace, &menu, &cancel);
    }

    {
        comp_touch_visual_decision_t cancel;
        comp_touch_visual_runtime_t runtime = {COMPANION_VISUAL_STATE_CENTERED_REST, false};
        comp_touch_visual_cancel(&gesture, &runtime, COMP_TOUCH_VISUAL_CANCEL_SETTLE, &cancel);
        emit_decision(&trace, &menu, &cancel);
        comp_touch_visual_cancel(&gesture, &runtime, COMP_TOUCH_VISUAL_CANCEL_SETTLE, &cancel);
        emit_decision(&trace, &menu, &cancel);
        runtime.current_visual_state = COMPANION_VISUAL_STATE_GAZE_LEFT;
        comp_touch_visual_cancel(&gesture, &runtime,
                                 COMP_TOUCH_VISUAL_CANCEL_TRANSPORT_BLUR, &cancel);
        emit_decision(&trace, &menu, &cancel);
    }
    g_menu_visible = true;
    comp_touch_gesture_init(&gesture, &config);
    comp_screen_menu_init(&menu);
    (void)tap(&trace, &gesture, &menu, 100u, 90u, 12000u, &sequence);
    comp_touch_gesture_init(&gesture, &config);
    comp_screen_menu_init(&menu);
    (void)tap(&trace, &gesture, &menu, 100u, 150u, 12700u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_DOWN, 112u, 100u), 13400u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_CONTACT, 188u, 100u), 13500u, &sequence);
    feed(&trace, &gesture, &menu, report(COMP_FT6336_TOUCH_EVENT_UP, 188u, 100u), 13600u, &sequence);

    printf("{\"schema\":\"companion.comp_req_501.raw_touch_trace.v1\","
           "\"raw_reports\":%u,\"gesture_decisions\":%u,"
           "\"cancellations\":%u,\"menu_results\":%u,"
           "\"ui_assets\":%u,\"event_records\":%u,"
           "\"pair_records\":%u,\"pixel_noop_records\":%u,"
           "\"center_partition\":true,\"event_mask\":%u,\"frame_hash_records\":%u,"
           "\"nonzero_frame_hash_records\":%u,\"render_records\":%u,"
           "\"hardware_contact\":0,\"write\":0,"
           "\"refresh\":0,\"popup\":0,\"retry\":0,"
           "\"event_names\":\"%s\",\"pair_names\":\"%s\",\"noop_names\":\"%s\","
           "\"duplicate_input\":%u,\"missing_input\":%u}\n",
           trace.reports, trace.decisions, trace.cancellations,
           trace.menus, trace.ui_assets, trace.event_records,
           trace.pair_records, trace.noop_records,
           (unsigned)((trace.seen_events[0] ? 1u : 0u) |
                      (trace.seen_events[1] ? 2u : 0u) |
                      (trace.seen_events[2] ? 4u : 0u) |
                      (trace.seen_events[3] ? 8u : 0u) |
                      (trace.seen_events[4] ? 16u : 0u) |
                      (trace.seen_events[5] ? 32u : 0u) |
                      (trace.seen_events[6] ? 64u : 0u) |
                      (trace.seen_events[7] ? 128u : 0u) |
                      (trace.seen_events[8] ? 256u : 0u) |
                      (trace.seen_events[9] ? 512u : 0u) |
                      (trace.seen_events[10] ? 1024u : 0u) |
                      (trace.seen_events[11] ? 2048u : 0u) |
                      (trace.seen_events[12] ? 4096u : 0u) |
                      (trace.seen_events[13] ? 8192u : 0u) |
                      (trace.seen_events[14] ? 16384u : 0u) |
                      (trace.seen_events[15] ? 32768u : 0u) |
                      (trace.seen_events[16] ? 65536u : 0u) |
                      (trace.seen_events[17] ? 131072u : 0u) |
                      (trace.seen_events[18] ? 262144u : 0u) |
                      (trace.seen_events[19] ? 524288u : 0u) |
                      (trace.seen_events[20] ? 1048576u : 0u)),
           trace.frame_hash_records, trace.nonzero_frame_hash_records,
           trace.render_records,
           trace.event_names, trace.pair_names, trace.noop_names,
           trace.duplicate_input, trace.missing_input);
    return !zero_contact_hold_cancel ||
           trace.cancellations == 0u || trace.ui_assets == 0u ||
           trace.event_records != 21u || trace.pair_records != 59u ||
           trace.noop_records != 10u || trace.frame_hash_records != 59u ||
           trace.nonzero_frame_hash_records != 59u ||
           trace.render_records < trace.pair_records ||
           trace.route_records == 0u ||
           trace.duplicate_input != 0u || trace.missing_input != 0u ? 2 : 0;
}
