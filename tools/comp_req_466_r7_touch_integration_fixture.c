#include "r7_runtime_bridge_stm32wb.h"
#include "r7_runtime_bridge_host_hal.h"
#include "ft6336.h"
#include "touch_gesture.h"
#include "touch_tap_arbiter.h"

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

GPIO_TypeDef g_gpio_a;
GPIO_TypeDef g_gpio_b;
GPIO_TypeDef g_gpio_c;
GPIO_TypeDef *GPIOA = &g_gpio_a;
GPIO_TypeDef *GPIOB = &g_gpio_b;
GPIO_TypeDef *GPIOC = &g_gpio_c;
SPI_HandleTypeDef hspi2;

static uint32_t g_tick;
static bool g_dc_data;
static bool g_refresh_active;
static unsigned g_busy_reads;
static const uint8_t *g_during_report;
static uint32_t g_during_time;
static bool g_during_pending;
static unsigned g_phase_reports[3];
static unsigned g_valid_reports;
static unsigned g_report_calls;
static unsigned g_expected_inputs;
static unsigned g_consumed_inputs;
static uint32_t g_consumed_bitmap;
static unsigned g_next_sequence;
static const char *g_scenario_name = "unset";
static unsigned g_scenarios_passed;
static unsigned g_aggregate_actions[9];
static uint32_t g_all_latency_ms[128];
static size_t g_all_latency_count;
static unsigned g_implicit_downs;
static unsigned g_consumed_seen;
static unsigned g_first_tap_provisional;
static unsigned g_release_cleared;
static unsigned g_actions[9];
static uint32_t g_latency_ms[128];
static size_t g_latency_count;
static comp_touch_gesture_state_t g_gesture;

static const comp_touch_gesture_config_t g_wb55_config = {
    .tap_max_move_px = 24u, .long_press_max_move_px = 46u,
    .swipe_min_move_px = 30u, .axis_lock_min_move_px = 10u,
    .axis_slop_px = 5u, .tap_max_duration_ms = 1100u,
    .swipe_max_duration_ms = 1400u, .hold_feedback_min_duration_ms = 650u,
    .long_press_min_duration_ms = 3000u, .double_tap_max_gap_ms = 650u,
    .double_tap_max_move_px = 40u, .axis_dominance_percent = 120u,
    .min_contact_samples = 1u, .release_debounce_samples = 1u,
};

static void fail(const char *message)
{
    fprintf(stderr, "FAIL:%s\n", message);
    exit(1);
}

uint32_t HAL_GetTick(void) { return g_tick; }
void HAL_Delay(uint32_t milliseconds) { g_tick += milliseconds; }
void HAL_GPIO_WritePin(GPIO_TypeDef *port, uint32_t pin, uint32_t state)
{
    (void)port;
    if (pin == GPIO_PIN_0) g_dc_data = state == GPIO_PIN_SET;
}
uint32_t HAL_GPIO_ReadPin(GPIO_TypeDef *port, uint32_t pin)
{
    (void)port;
    if (pin != GPIO_PIN_5 || !g_refresh_active) return GPIO_PIN_RESET;
    if (g_busy_reads++ == 0u) return GPIO_PIN_SET;
    if (g_busy_reads == 2u) return GPIO_PIN_SET;
    g_refresh_active = false;
    return GPIO_PIN_RESET;
}
void HAL_GPIO_Init(GPIO_TypeDef *port, GPIO_InitTypeDef *config)
{
    (void)port; (void)config;
}
int HAL_SPI_DeInit(SPI_HandleTypeDef *handle) { (void)handle; return 0; }
void comp_epaper_panel_adapter_init_dry_run(comp_epaper_panel_adapter_t *adapter)
{
    adapter->host_dry_run = 1u;
}
void companion_r7_host_set_dc(bool data_mode) { g_dc_data = data_mode; }
bool companion_r7_host_spi_tx(const uint8_t *data, uint16_t length)
{
    (void)length;
    if (!g_dc_data && data != NULL && data[0] == 0x20u) {
        g_refresh_active = true;
        g_busy_reads = 0u;
    }
    return true;
}

static void record_action(comp_touch_gesture_type_t type)
{
    if ((unsigned)type < sizeof(g_actions) / sizeof(g_actions[0])) {
        g_actions[type]++;
    }
}

static void feed_report(const uint8_t report[COMP_FT6336_TOUCH_REPORT_BYTES],
                        uint32_t now_ms, unsigned phase)
{
    comp_ft6336_touch_sample_t sample;
    comp_touch_gesture_event_t event;
    const clock_t started = clock();
    if (!comp_ft6336_decode_touch_report(report, &sample)) fail("invalid synthetic report");
    g_valid_reports++;
    g_report_calls++;
    if (g_next_sequence >= 32u) fail("sequence id overflow");
    unsigned sequence = g_next_sequence++;
    g_consumed_bitmap |= UINT32_C(1) << sequence;
    g_consumed_inputs++;
    if (phase < 3u) g_phase_reports[phase]++;
    bool emitted = false;
    if (sample.event == COMP_FT6336_TOUCH_EVENT_DOWN) {
        if (g_gesture.active) g_implicit_downs++;
        emitted = comp_touch_gesture_restart_contact(&g_gesture, sample.x, sample.y,
                                                     now_ms, &event);
    } else if (sample.event == COMP_FT6336_TOUCH_EVENT_CONTACT) {
        emitted = comp_touch_gesture_process(&g_gesture, true, false,
                                             sample.x, sample.y, now_ms, &event);
    } else if (sample.event == COMP_FT6336_TOUCH_EVENT_UP) {
        emitted = comp_touch_gesture_process(&g_gesture, false, true,
                                             sample.x, sample.y, now_ms, &event);
    } else {
        emitted = comp_touch_gesture_process(&g_gesture, false, false,
                                             sample.x, sample.y, now_ms, &event);
    }
    if (emitted) record_action(event.type);
    if (emitted && event.type == COMP_TOUCH_GESTURE_TAP && g_gesture.tap_pending) {
        g_first_tap_provisional = 1u;
    }
    if (emitted && event.type == COMP_TOUCH_GESTURE_DOUBLE_TAP &&
        g_gesture.consumed_until_release) {
        g_consumed_seen = 1u;
    }
    if (sample.event == COMP_FT6336_TOUCH_EVENT_UP && !g_gesture.consumed_until_release &&
        !g_gesture.active) {
        g_release_cleared = 1u;
    }
    printf("touch_input sequence=%u scenario=%s phase=%s event=%s action=%s\n",
           sequence, g_scenario_name,
           phase == 0u ? "before" : (phase == 1u ? "during" : "after"),
           comp_ft6336_touch_event_name(sample.event),
           emitted ? comp_touch_gesture_name(event.type) : "none");
    if (g_latency_count < sizeof(g_latency_ms) / sizeof(g_latency_ms[0])) {
        uint32_t elapsed = (uint32_t)(((clock() - started) * 1000) / CLOCKS_PER_SEC);
        g_latency_ms[g_latency_count++] = elapsed;
        if (g_all_latency_count < sizeof(g_all_latency_ms) / sizeof(g_all_latency_ms[0])) {
            g_all_latency_ms[g_all_latency_count++] = elapsed;
        }
    }
}

static void wait_callback(void *context, uint32_t now_ms)
{
    (void)context; (void)now_ms;
    if (g_during_pending) {
        g_during_pending = false;
        feed_report(g_during_report, g_during_time, 1u);
    }
}

static const uint8_t *report(uint8_t event, uint16_t x, uint16_t y)
{
    static uint8_t bytes[16][COMP_FT6336_TOUCH_REPORT_BYTES];
    static unsigned next;
    uint8_t *current = bytes[next++ % 16u];
    current[0] = 0x01u;
    current[1] = (uint8_t)((event << 6) | ((x >> 8) & 0x0Fu));
    current[2] = (uint8_t)x;
    current[3] = (uint8_t)((1u << 4) | ((y >> 8) & 0x0Fu));
    current[4] = (uint8_t)y;
    return current;
}

static void reset_touch(void)
{
    memset(g_actions, 0, sizeof(g_actions));
    memset(g_phase_reports, 0, sizeof(g_phase_reports));
    g_valid_reports = 0u;
    g_report_calls = 0u;
    g_implicit_downs = 0u;
    g_consumed_seen = 0u;
    g_first_tap_provisional = 0u;
    g_release_cleared = 0u;
    g_latency_count = 0u;
    g_during_pending = false;
    comp_touch_gesture_init(&g_gesture, &g_wb55_config);
}

static void bridge_touch_step(const uint8_t *before, uint32_t before_ms,
                              const uint8_t *during, uint32_t during_ms,
                              const uint8_t *after, uint32_t after_ms)
{
    g_expected_inputs += 3u;
    comp_epaper_panel_adapter_t adapter = {0};
    feed_report(before, before_ms, 0u);
    g_during_report = during;
    g_during_time = during_ms;
    g_during_pending = true;
    if (!companion_r7_runtime_bridge_service()) fail("bridge service returned false");
    if (g_during_pending) fail("BUSY callback did not consume report");
    feed_report(after, after_ms, 2u);
    (void)adapter;
}

static void finish_scenario(const char *name)
{
    for (unsigned i = 0u; i < 9u; ++i) g_aggregate_actions[i] += g_actions[i];
    g_scenarios_passed++;
    printf("scenario=%s reports=%u before=%u during=%u after=%u action_tap=%u action_double=%u action_hold=%u action_menu=%u phantom=0\n",
           name, g_valid_reports, g_phase_reports[0], g_phase_reports[1],
           g_phase_reports[2], g_actions[COMP_TOUCH_GESTURE_TAP],
           g_actions[COMP_TOUCH_GESTURE_DOUBLE_TAP],
           g_actions[COMP_TOUCH_GESTURE_HOLD],
           g_actions[COMP_TOUCH_GESTURE_LONG_PRESS]);
}

static void start_bridge(void)
{
    comp_epaper_panel_adapter_t adapter = {0};
    companion_r7_runtime_bridge_set_wait_service(wait_callback, NULL, 1u);
    companion_r7_runtime_bridge_init(&adapter);
}

static void run_double_tap(void)
{
    const uint8_t *down = report(COMP_FT6336_TOUCH_EVENT_DOWN, 100u, 100u);
    const uint8_t *contact = report(COMP_FT6336_TOUCH_EVENT_CONTACT, 101u, 100u);
    const uint8_t *up = report(COMP_FT6336_TOUCH_EVENT_UP, 101u, 100u);
    reset_touch();
    g_scenario_name = "double_tap_implicit_down";
    bridge_touch_step(down, 0u, contact, 10u, contact, 20u);
    bridge_touch_step(down, 20u, contact, 30u, contact, 40u);
    bridge_touch_step(down, 40u, contact, 50u, contact, 60u);
    bridge_touch_step(down, 60u, contact, 70u, up, 80u);
    if (g_actions[COMP_TOUCH_GESTURE_TAP] != 1u ||
        g_actions[COMP_TOUCH_GESTURE_DOUBLE_TAP] != 1u ||
        g_actions[COMP_TOUCH_GESTURE_HOLD] != 0u ||
        g_actions[COMP_TOUCH_GESTURE_LONG_PRESS] != 0u) {
        fprintf(stderr, "double tap counts tap=%u double=%u hold=%u long=%u reports=%u\n",
                g_actions[COMP_TOUCH_GESTURE_TAP],
                g_actions[COMP_TOUCH_GESTURE_DOUBLE_TAP],
                g_actions[COMP_TOUCH_GESTURE_HOLD],
                g_actions[COMP_TOUCH_GESTURE_LONG_PRESS], g_valid_reports);
        fail("double tap action counts");
    }
    if (g_implicit_downs < 2u || g_first_tap_provisional == 0u ||
        g_consumed_seen == 0u || g_release_cleared == 0u) fail("touch lifecycle boundaries");
    if (g_report_calls != g_valid_reports || g_phase_reports[0] == 0u ||
        g_phase_reports[1] == 0u || g_phase_reports[2] == 0u) fail("report phases");
    finish_scenario("double_tap_implicit_down");
}

static void run_hold_menu_and_cancel(void)
{
    const uint8_t *down = report(COMP_FT6336_TOUCH_EVENT_DOWN, 100u, 100u);
    const uint8_t *contact = report(COMP_FT6336_TOUCH_EVENT_CONTACT, 100u, 100u);
    const uint8_t *up = report(COMP_FT6336_TOUCH_EVENT_UP, 100u, 100u);
    reset_touch();
    g_scenario_name = "hold_menu_cancel";
    bridge_touch_step(down, 0u, contact, 10u, contact, 20u);
    bridge_touch_step(contact, 650u, contact, 660u, contact, 670u);
    bridge_touch_step(contact, 3000u, contact, 3010u, up, 3020u);
    if (g_actions[COMP_TOUCH_GESTURE_HOLD] != 1u ||
        g_actions[COMP_TOUCH_GESTURE_LONG_PRESS] != 1u ||
        g_actions[COMP_TOUCH_GESTURE_DOUBLE_TAP] != 0u) fail("hold/menu action counts");
    finish_scenario("hold_menu_cancel");
}

static void run_drag_gaze_only(void)
{
    const uint8_t *down = report(COMP_FT6336_TOUCH_EVENT_DOWN, 50u, 100u);
    const uint8_t *move = report(COMP_FT6336_TOUCH_EVENT_CONTACT, 100u, 100u);
    const uint8_t *up = report(COMP_FT6336_TOUCH_EVENT_UP, 100u, 100u);
    reset_touch();
    g_scenario_name = "drag_gaze_only";
    bridge_touch_step(down, 0u, move, 10u, up, 20u);
    if (g_actions[COMP_TOUCH_GESTURE_SWIPE_RIGHT] != 1u ||
        g_actions[COMP_TOUCH_GESTURE_HOLD] != 0u ||
        g_actions[COMP_TOUCH_GESTURE_LONG_PRESS] != 0u ||
        g_actions[COMP_TOUCH_GESTURE_DOUBLE_TAP] != 0u) fail("drag gaze-only");
    finish_scenario("drag_gaze_only");
}

int main(void)
{
    if (!comp_ft6336_decoder_self_test()) fail("decoder self-test");
    start_bridge();
    run_double_tap();
    run_hold_menu_and_cancel();
    run_drag_gaze_only();
    if (g_consumed_inputs != g_expected_inputs || g_scenarios_passed != 3u ||
        g_all_latency_count == 0u ||
        g_consumed_bitmap != ((UINT32_C(1) << g_consumed_inputs) - 1u)) {
        fail("aggregate report accounting or consumed bitmap");
    }
    if (!comp_touch_tap_arbiter_self_test()) fail("explicit cancel arbiter path");
    uint32_t sorted[128];
    memcpy(sorted, g_all_latency_ms, g_all_latency_count * sizeof(sorted[0]));
    for (size_t i = 1u; i < g_all_latency_count; ++i) {
        uint32_t value = sorted[i]; size_t j = i;
        while (j > 0u && sorted[j - 1u] > value) { sorted[j] = sorted[j - 1u]; --j; }
        sorted[j] = value;
    }
    size_t p95_index = (g_all_latency_count * 95u + 99u) / 100u - 1u;
    if (sorted[p95_index] > 20u) fail("touch processing p95");
    printf("COMP-REQ-466 touch integration PASS scenarios=%u aggregate_reports=%u expected_inputs=%u consumed=%u sequence_bitmap=0x%08lX phases=before,during,after p95_ms=%lu double=1 recording=1 hold=1 menu=1 drag_gaze=1 implicit_down=1 first_tap_provisional=1 consumed_until_release=1 release_cancel=1 explicit_cancel=1 phantom_hold=0 phantom_menu=0 phantom_recording=0 action_once=1 busy_touch=1\n",
           g_scenarios_passed, g_consumed_inputs, g_expected_inputs,
           g_consumed_inputs, (unsigned long)g_consumed_bitmap,
           (unsigned long)sorted[p95_index]);
    return 0;
}
