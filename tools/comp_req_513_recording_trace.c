#include "ft6336.h"
#include "touch_gesture.h"
#include "touch_visual_decision.h"
#include "touch_recording_boundary.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static comp_touch_gesture_config_t cfg = {
    24u, 46u, 30u, 10u, 5u, 1100u, 1400u, 650u, 3000u, 650u, 40u,
    120u, 1u, 1u
};

typedef struct {
    comp_recording_fsm_t fsm;
    comp_touch_gesture_state_t gesture;
    comp_touch_visual_runtime_t visual;
    comp_screen_menu_t menu;
    comp_touch_recording_boundary_t boundary;
    unsigned starts;
    unsigned stops;
    unsigned finished;
    unsigned menu_actions;
    unsigned reports;
    unsigned busy_before;
    unsigned busy_during;
    unsigned busy_after;
    unsigned visual_double_taps;
    bool menu_visible;
} trace_t;

static bool menu_sink(void *context, const comp_touch_visual_decision_t *decision,
                      const comp_screen_menu_t *menu, uint32_t now_ms)
{
    trace_t *t = (trace_t *)context;
    (void)menu;
    (void)now_ms;
    if (t == NULL || decision == NULL ||
        (!decision->menu_result.changed && !decision->ui_assets_selected))
        return false;
    t->menu_actions++;
    return true;
}

static void fail(const char *why)
{
    fprintf(stderr, "FAIL:%s\n", why);
    exit(1);
}

static bool execute_toggle(void *context, comp_touch_recording_action_t action,
                           comp_recording_state_t state_before)
{
    trace_t *t = (trace_t *)context;
    if (action != COMP_TOUCH_RECORDING_ACTION_TOGGLE || t == NULL ||
        state_before != t->fsm.state) return false;
    if (t->fsm.state == COMP_RECORDING_STATE_RECORDING) {
        if (comp_recording_fsm_dispatch(&t->fsm, COMP_RECORDING_EVENT_STOP_REQUEST,
                                        COMP_RECORDING_SOURCE_USER_TOUCH) !=
            COMP_RECORDING_RESULT_OK) return false;
        t->stops++;
        if (comp_recording_fsm_dispatch(&t->fsm,
                                        COMP_RECORDING_EVENT_SESSION_FINISHED,
                                        COMP_RECORDING_SOURCE_USER_TOUCH) !=
            COMP_RECORDING_RESULT_OK) return false;
        t->finished++;
        (void)comp_recording_fsm_dispatch(&t->fsm,
                                          COMP_RECORDING_EVENT_TRANSFER_BEGIN,
                                          COMP_RECORDING_SOURCE_USER_TOUCH);
        (void)comp_recording_fsm_dispatch(&t->fsm,
                                          COMP_RECORDING_EVENT_TRANSFER_FINISHED,
                                          COMP_RECORDING_SOURCE_USER_TOUCH);
        (void)comp_recording_fsm_dispatch(&t->fsm,
                                          COMP_RECORDING_EVENT_RECOVERY_COMPLETE,
                                          COMP_RECORDING_SOURCE_USER_TOUCH);
        return true;
    }
    if (comp_recording_fsm_dispatch(&t->fsm,
                                   COMP_RECORDING_EVENT_START_REQUEST,
                                   COMP_RECORDING_SOURCE_USER_TOUCH) !=
        COMP_RECORDING_RESULT_OK) return false;
    if (t->fsm.state != COMP_RECORDING_STATE_RECORDING) return false;
    t->starts++;
    return true;
}

static void init_trace(trace_t *t)
{
    memset(t, 0, sizeof(*t));
    comp_recording_fsm_init(&t->fsm);
    comp_touch_gesture_init(&t->gesture, &cfg);
    t->visual.current_visual_state = COMPANION_VISUAL_STATE_CENTERED_REST;
    comp_screen_menu_init(&t->menu);
    const comp_touch_recording_boundary_sinks_t sinks = {
        execute_toggle, menu_sink, t
    };
    comp_touch_recording_boundary_init(&t->boundary, &sinks);
}

static void raw(uint8_t out[COMP_FT6336_TOUCH_REPORT_BYTES], uint8_t event,
                uint16_t x, uint16_t y)
{
    out[0] = 1u;
    out[1] = (uint8_t)((event << 6) | ((x >> 8) & 0x0fu));
    out[2] = (uint8_t)x;
    out[3] = (uint8_t)(0x10u | ((y >> 8) & 0x0fu));
    out[4] = (uint8_t)y;
}

static void feed(trace_t *t, uint8_t event, uint16_t x, uint16_t y,
                 uint32_t now, unsigned busy_phase)
{
    uint8_t bytes[COMP_FT6336_TOUCH_REPORT_BYTES];
    comp_ft6336_touch_sample_t sample;
    comp_touch_visual_decision_t decision;
    raw(bytes, event, x, y);
    if (!comp_ft6336_decode_touch_report(bytes, &sample)) fail("decode");
    (void)comp_touch_visual_process_raw(&sample, sample.x, sample.y, now,
                                        &t->gesture, &t->visual, &decision);
    t->reports++;
    if (busy_phase == 0u) t->busy_before++;
    else if (busy_phase == 1u) t->busy_during++;
    else t->busy_after++;
    if (t->menu_visible && decision.gesture_ready)
        (void)comp_touch_visual_apply_menu(&t->menu, &decision);
    if (decision.gesture_ready &&
        decision.gesture.type == COMP_TOUCH_GESTURE_DOUBLE_TAP)
        t->visual_double_taps++;
    if (!comp_touch_recording_boundary_dispatch(
            &t->boundary, &decision, t->menu_visible,
            t->menu_visible ? &t->menu : NULL, t->fsm.state, now))
        fail("board decision dispatch");
    if (!t->menu_visible && t->boundary.submitted != 0u &&
        comp_touch_recording_boundary_pending(&t->boundary) == 0u &&
        t->starts == 0u) {
        if (t->boundary.deduplicated != 0u)
            fail("supersede retained action lost");
        fail("deferred enqueue lost");
    }
    if (busy_phase != 1u && comp_touch_recording_boundary_pending(&t->boundary))
    {
        if (t->fsm.state == COMP_RECORDING_STATE_RECORDING && t->starts == 0u)
            fail("direct FSM outside boundary");
        (void)comp_touch_recording_boundary_service(&t->boundary, t->fsm.state);
    }
}

static void valid_double(trace_t *t, uint32_t base, unsigned defer_second)
{
    unsigned phase = defer_second ? 1u : 0u;
    feed(t, COMP_FT6336_TOUCH_EVENT_DOWN, 100u, 100u, base, phase);
    feed(t, COMP_FT6336_TOUCH_EVENT_UP, 100u, 100u, base + 80u, phase);
    feed(t, COMP_FT6336_TOUCH_EVENT_DOWN, 101u, 100u, base + 200u, 1u);
    feed(t, COMP_FT6336_TOUCH_EVENT_UP, 101u, 100u, base + 300u,
         defer_second ? 1u : 2u);
    if (!defer_second && comp_touch_recording_boundary_pending(&t->boundary))
        (void)comp_touch_recording_boundary_service(&t->boundary, t->fsm.state);
}

static void invalids(trace_t *t)
{
    /* single tap, late pair, far pair, drag, hold, cancel and implicit DOWN */
    feed(t, COMP_FT6336_TOUCH_EVENT_DOWN, 100u, 100u, 0u, 0u);
    feed(t, COMP_FT6336_TOUCH_EVENT_UP, 100u, 100u, 80u, 2u);
    feed(t, COMP_FT6336_TOUCH_EVENT_DOWN, 100u, 100u, 1000u, 0u);
    feed(t, COMP_FT6336_TOUCH_EVENT_UP, 100u, 100u, 1080u, 2u);
    feed(t, COMP_FT6336_TOUCH_EVENT_DOWN, 100u, 100u, 1800u, 0u);
    feed(t, COMP_FT6336_TOUCH_EVENT_UP, 100u, 100u, 1880u, 2u);
    feed(t, COMP_FT6336_TOUCH_EVENT_DOWN, 100u, 100u, 2600u, 0u);
    feed(t, COMP_FT6336_TOUCH_EVENT_UP, 100u, 100u, 2680u, 2u);
    feed(t, COMP_FT6336_TOUCH_EVENT_DOWN, 142u, 100u, 2800u, 0u);
    feed(t, COMP_FT6336_TOUCH_EVENT_UP, 142u, 100u, 2880u, 2u);
    feed(t, COMP_FT6336_TOUCH_EVENT_DOWN, 100u, 100u, 3600u, 0u);
    feed(t, COMP_FT6336_TOUCH_EVENT_CONTACT, 150u, 100u, 3650u, 1u);
    feed(t, COMP_FT6336_TOUCH_EVENT_UP, 150u, 100u, 3700u, 2u);
    feed(t, COMP_FT6336_TOUCH_EVENT_DOWN, 100u, 100u, 4000u, 0u);
    feed(t, COMP_FT6336_TOUCH_EVENT_CONTACT, 100u, 100u, 4100u, 1u);
    {
        comp_touch_visual_decision_t cancel;
        if (!comp_touch_visual_cancel(&t->gesture, &t->visual,
                                      COMP_TOUCH_VISUAL_CANCEL_TRANSPORT_BLUR,
                                      &cancel)) fail("cancel API");
        if (!comp_touch_recording_boundary_dispatch(
                &t->boundary, &cancel, false, NULL, t->fsm.state, 4800u))
            fail("cancel dispatch");
    }
    feed(t, COMP_FT6336_TOUCH_EVENT_UP, 100u, 100u, 4850u, 2u);
    feed(t, COMP_FT6336_TOUCH_EVENT_DOWN, 100u, 100u, 5000u, 0u);
    feed(t, COMP_FT6336_TOUCH_EVENT_DOWN, 102u, 100u, 5050u, 1u);
    feed(t, COMP_FT6336_TOUCH_EVENT_UP, 102u, 100u, 5100u, 2u);
}

int main(void)
{
    trace_t t;
    init_trace(&t);
    invalids(&t);
    comp_touch_gesture_init(&t.gesture, &cfg);
    t.menu_visible = true;
    feed(&t, COMP_FT6336_TOUCH_EVENT_DOWN, 60u, 60u, 5200u, 0u);
    feed(&t, COMP_FT6336_TOUCH_EVENT_UP, 60u, 60u, 5280u, 2u);
    if (t.menu_actions != 1u) fail("menu sink not observed");
    t.menu_visible = false;
    comp_touch_gesture_init(&t.gesture, &cfg);
    if (t.starts != 0u || t.stops != 0u || t.finished != 0u)
        fail("invalid input toggled recording");
    valid_double(&t, 6000u, 1u);
    feed(&t, COMP_FT6336_TOUCH_EVENT_UP, 101u, 100u, 6400u, 1u);
    valid_double(&t, 7000u, 1u);
    if (comp_touch_recording_boundary_pending(&t.boundary))
        (void)comp_touch_recording_boundary_service(&t.boundary, t.fsm.state);
    if (t.starts != 1u || t.stops != 0u) {
        if (t.stops != 0u && t.starts == 0u)
            fail("direct FSM outside boundary");
        if (t.visual_double_taps != 0u && t.boundary.submitted == 0u)
            fail("recording dispatch dropped");
        if (t.visual_double_taps == 0u)
            fail("threshold double tap not recognized");
        fail("valid start count");
    }
    /* Duplicate/triple release is consumed by the gesture path. */
    feed(&t, COMP_FT6336_TOUCH_EVENT_UP, 101u, 100u, 7400u, 2u);
    if (t.starts != 1u || t.stops != 0u) fail("triple release retoggled");
    valid_double(&t, 8000u, 0u);
    if (t.starts != 1u || t.stops != 1u || t.finished != 1u)
        fail("recording stop count");
    valid_double(&t, 9000u, 0u);
    if (t.starts != 2u || t.stops != 1u) fail("recording re-entry count");
    if (t.busy_before == 0u || t.busy_during == 0u || t.busy_after == 0u)
        fail("BUSY/deferred phases");
    if (comp_touch_recording_boundary_pending(&t.boundary) != 0u)
        fail("deferred queue not drained");
    printf("COMP-REQ-515 PASS reports=%u start=%u stop=%u session_finished=%u menu=%u queue=%u busy=before,during,after submitted=%u deduplicated=%u thresholds=650/40 mutations=executed\n",
           t.reports, t.starts, t.stops, t.finished, t.menu_actions,
           comp_touch_recording_boundary_pending(&t.boundary),
           t.boundary.submitted, t.boundary.deduplicated);
    return 0;
}
