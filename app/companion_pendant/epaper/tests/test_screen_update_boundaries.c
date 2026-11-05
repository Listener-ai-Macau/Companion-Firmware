#include "screen_presenter_wba.h"

#include <stdio.h>
#include <string.h>

#define CHECK(c) do { if (!(c)) { \
    fprintf(stderr, "FAIL:%d: %s\n", __LINE__, #c); return 1; } } while (0)

/* Controller BUSY/transport fixture, not an electrophoretic or power model. */
typedef struct {
    uint32_t now, busy_until, calls, visible_activations, full_activations;
    uint32_t completions, failures;
    uint8_t command, control, pattern;
} fixture_t;

static bool transfer(void *context, bool data, const uint8_t *bytes, uint16_t size)
{
    fixture_t *f = context;
    if (!bytes || !size) return false;
    ++f->calls;
    if (!data) {
        if (size != 1u) return false;
        f->command = bytes[0];
        if (bytes[0] == 0x12u || bytes[0] == 0x20u)
            f->busy_until = f->now + 30u;
        if (bytes[0] == 0x20u && (f->control & 4u)) {
            ++f->visible_activations;
            if (f->control == 0xF7u) ++f->full_activations;
        }
    } else if (f->command == 0x22u) {
        if (size != 1u) return false;
        f->control = bytes[0];
    }
    return true;
}
static bool busy(void *context)
{ const fixture_t *f = context; return (int32_t)(f->now - f->busy_until) < 0; }
static uint32_t tick(void *context)
{ return ((fixture_t *)context)->now; }

static bool render(void *context, const comp_runtime_frame_t *request, uint8_t frame[5000])
{
    const fixture_t *f = context;
    memset(frame, 255, 5000u);
    frame[10u * 25u + 3u] = 0u; /* Stable authored background. */
    frame[100u * 25u + 9u] = request->surface == COMP_SCREEN_SURFACE_LOW_POWER ? 0xFEu : 0xC0u;
    frame[90u * 25u + 8u] = (uint8_t)(255u - f->pattern);
    if (request->recording == DENZIC_AUDIO_RECORDING_STATE_RECORDING)
        frame[COMP_SSD1681_WBA_RECORDING_Y_MIN * 25u + 1u] = 0x7Eu;
    return true;
}
static void complete(void *context, uint32_t token, bool visible, uint32_t now)
{
    fixture_t *f = context;
    (void)token; (void)now;
    ++f->completions;
    if (!visible) ++f->failures;
}
static bool drive(comp_screen_presenter_wba_t *p, comp_ssd1681_wba_t *panel, fixture_t *f)
{
    for (unsigned n = 0; n < 8000u; ++n) {
        (void)comp_ssd1681_wba_poll(panel);
        (void)comp_screen_presenter_wba_service(p, f->now);
        if (p->status != COMP_SCREEN_PRESENTER_WBA_ACTIVE)
            return panel->status == COMP_SSD1681_WBA_COMPLETE;
        ++f->now;
    }
    return false;
}

int main(void)
{
    fixture_t f = {.now = 100u};
    comp_ssd1681_wba_t panel;
    comp_screen_presenter_wba_t p;
    uint8_t committed[5000], staging[5000];
    const comp_ssd1681_wba_config_t bus = {
        .transfer = transfer, .is_busy = busy, .now_ms = tick, .context = &f,
        .reset_mode = COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY,
        .payload_chunk_bytes = 128u, .busy_timeout_ms = 5000u, .partial_limit = UINT8_MAX,
    };
    const comp_screen_presenter_wba_config_t view = {
        .panel = &panel, .render = render, .complete = complete, .context = &f,
        .committed_frame = committed, .staging_frame = staging, .partial_limit = UINT8_MAX,
    };
    comp_runtime_frame_t r = {0};
    r.token = 1u; r.surface = COMP_SCREEN_SURFACE_HOME;
    r.kind = COMP_RUNTIME_FRAME_LIFE; r.recording = DENZIC_AUDIO_RECORDING_STATE_IDLE;
    CHECK(comp_ssd1681_wba_init(&panel, &bus));
    CHECK(comp_screen_presenter_wba_init(&p, &view));
    CHECK(comp_screen_presenter_wba_submit(&p, &r, f.now) == COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    CHECK(p.selection.decision == COMP_EPAPER_REFRESH_DECISION_FULL);
    CHECK(drive(&p, &panel, &f) && f.full_activations == 1u);

    /* Three sleep/wake cycles must use local dirty windows and one activation
     * each; neither sleep nor wake may increase the Mode1 flash counter. */
    for (unsigned n = 0; n < 6u; ++n) {
        const uint32_t activations = f.visible_activations;
        ++r.token;
        r.surface = n % 2u == 0u ? COMP_SCREEN_SURFACE_LOW_POWER : COMP_SCREEN_SURFACE_HOME;
        CHECK(comp_screen_presenter_wba_submit(&p, &r, f.now) == COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
        CHECK(p.selection.decision == COMP_EPAPER_REFRESH_DECISION_PARTIAL);
        CHECK(p.dirty_window.x_start_byte == 9u && p.dirty_window.x_end_byte == 9u);
        CHECK(p.dirty_window.y_start == 99u && p.dirty_window.y_end == 99u);
        CHECK(drive(&p, &panel, &f));
        CHECK(f.full_activations == 1u && f.visible_activations == activations + 1u);
        CHECK(!memcmp(committed, staging, 5000u));
    }

    /* A label/family boundary with identical pixels does no bus I/O. */
    r.family_clean = true; ++r.token;
    uint32_t calls = f.calls;
    CHECK(comp_screen_presenter_wba_submit(&p, &r, f.now) == COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED);
    CHECK(f.calls == calls && p.stats.no_change_completions == 1u);

    /* Genuine maintenance still runs when both existing conditions are due. */
    p.full_cadence_updates = 192u;
    f.now = p.full_cadence_ms + 300000u;
    ++r.token;
    CHECK(comp_screen_presenter_wba_submit(&p, &r, f.now) == COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    CHECK(p.selection.decision == COMP_EPAPER_REFRESH_DECISION_FULL);
    CHECK(p.selection.reason == COMP_EPAPER_REFRESH_REASON_GHOST_MAINTENANCE);
    CHECK(drive(&p, &panel, &f) && f.full_activations == 2u);

    /* Capture family changes and the stop transition retain OP_RECORDING. */
    uint32_t fast = p.stats.fast_started;
    for (unsigned n = 0; n < 2u; ++n) {
        ++r.token; ++f.pattern;
        r.recording = n == 0u ? DENZIC_AUDIO_RECORDING_STATE_RECORDING : DENZIC_AUDIO_RECORDING_STATE_IDLE;
        uint32_t recordings = p.stats.recording_started;
        CHECK(comp_screen_presenter_wba_submit(&p, &r, f.now) == COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
        CHECK(p.selection.decision == COMP_EPAPER_REFRESH_DECISION_PARTIAL);
        CHECK(comp_ssd1681_wba_recording_active(&panel));
        CHECK(p.stats.recording_started == recordings + 1u && p.stats.fast_started == fast);
        CHECK(drive(&p, &panel, &f));
    }

    /* Identical pixels cannot qualify an invalid controller baseline. */
    r.family_clean = false; ++r.token;
    panel.baseline_valid = false;
    CHECK(comp_screen_presenter_wba_submit(&p, &r, f.now) == COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    CHECK(p.selection.decision == COMP_EPAPER_REFRESH_DECISION_FULL);
    CHECK(drive(&p, &panel, &f) && f.full_activations == 3u);
    CHECK(f.failures == 0u);
    puts("PASS_CHANGED_SCREEN_BOUNDARIES: six local sleep/wakes, no-change family skips, due clean retained, capture/stop sparse path, invalid baseline restored; hardware NOT_RUN");
    return 0;
}
