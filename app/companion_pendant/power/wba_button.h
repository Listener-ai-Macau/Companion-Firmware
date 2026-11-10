#ifndef COMPANION_WBA_BUTTON_H
#define COMPANION_WBA_BUTTON_H
#include <stdbool.h>
#include <stdint.h>
typedef struct {
    uint32_t changed_ms;
    /* Double-click timing and IRQ replay are mutually exclusive policies. */
    union { uint32_t click_ms, edge_observed_ms; };
    unsigned char raw:1, pressed:1, consumed:1, wake_only:1;
    unsigned char click_pending:1, second_press:1, double_enabled:1;
    uint8_t last_event;
    uint16_t max_hold_ms; /* Diagnostic values use the previous tail padding. */
} comp_wba_button_t;
_Static_assert(sizeof(comp_wba_button_t)==12u,"button diagnostics must not grow RAM");
enum { COMP_WBA_BUTTON_WAKE=1u, COMP_WBA_BUTTON_CONFIRM=2u,
       COMP_WBA_BUTTON_RECORD_TOGGLE=4u, COMP_WBA_BUTTON_DOUBLE_CONFIRM=8u,
       COMP_WBA_BUTTON_DOWN=16u, COMP_WBA_BUTTON_UP=32u };
enum { COMP_WBA_BUTTON_EDGE_DOWN=1u, COMP_WBA_BUTTON_EDGE_UP=2u };
typedef struct {
    uint32_t down_ms, up_ms;
    uint8_t flags;
    bool raw_pressed;
} comp_wba_button_edges_t;
/* Recorder-card input uses actual IRQ edges, so a completed short press and
 * the real hold duration survive a delayed foreground sample. No ISR runs
 * product actions; timestamps are replayed by the foreground owner. */
uint8_t comp_wba_button_poll_edges(comp_wba_button_t *,
    const comp_wba_button_edges_t *, uint16_t hold_ms, uint32_t now);
/* Qualified transitions for recorder/desktop mode. No long-hold action;
 * a held boot key is retired, and complete delayed presses retain both edges. */
uint8_t comp_wba_button_poll_transitions(comp_wba_button_t *,
    const comp_wba_button_edges_t *,uint32_t now);
void comp_wba_button_init(comp_wba_button_t *, bool raw_pressed, uint32_t now);
uint8_t comp_wba_button_poll(comp_wba_button_t *, bool raw_pressed, bool sleeping, uint32_t now);
/* Opt in only on the idle Companion screen. The first release waits 320 ms so a
 * double click emits only DOUBLE_CONFIRM, never a preceding single refresh. */
uint8_t comp_wba_button_poll_with_double(comp_wba_button_t *, bool raw_pressed,
    bool sleeping, bool enable_double, uint32_t now);
/* Product gesture policy, independent of the MCU: Capture uses1000ms with
 * no double-click interpretation; Companion retains the existing700ms path. */
uint8_t comp_wba_button_poll_with_hold(comp_wba_button_t *, bool raw_pressed,
    bool sleeping, bool enable_double, uint16_t hold_ms, uint32_t now);
bool comp_wba_button_busy(const comp_wba_button_t *);
#endif
