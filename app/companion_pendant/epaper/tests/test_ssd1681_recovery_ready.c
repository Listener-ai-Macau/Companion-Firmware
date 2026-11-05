#include "ssd1681_wba.h"

#include <stdio.h>
#include <string.h>

#define CHECK(c) do { if (!(c)) { \
    fprintf(stderr, "FAIL:%d: %s\n", __LINE__, #c); return 1; } } while (0)

/* Link the real driver and replay only its missed-start reset handoff.
 * A modeled original activation begins just beyond the 100ms start gate.
 * This is a software ordering reproduction, not a panel waveform model. */
typedef struct {
    uint32_t now, busy_from, busy_until, first_activation, retry_reset;
    uint32_t missing_at, original_deadline, delay;
    unsigned activations, resets, writes_while_busy;
    uint8_t command, control;
    bool scenario, reset_stuck;
} fixture_t;

static bool busy(void *context)
{
    fixture_t *f = context;
    return (int32_t)(f->now - f->busy_from) >= 0 &&
           (int32_t)(f->now - f->busy_until) < 0;
}
static uint32_t tick(void *context) { return ((fixture_t *)context)->now; }
static bool allowed(void *context) { (void)context; return true; }
static bool transfer(void *context, bool data, const uint8_t *bytes, uint16_t size)
{
    fixture_t *f = context;
    if (!bytes || !size) return false;
    if (busy(f)) { ++f->writes_while_busy; return false; }
    if (data) {
        if (f->command == 0x22u) f->control = bytes[0];
        return true;
    }
    if (size != 1u) return false;
    f->command = bytes[0];
    if (f->command == 0x12u) {
        if (f->scenario) { ++f->resets; f->retry_reset = f->now; }
        f->busy_from = f->now;
        f->busy_until = f->now + (f->scenario && f->reset_stuck ? 10000u : 30u);
    } else if (f->command == 0x20u) {
        uint32_t delay = 0u;
        if (f->scenario && (f->control & 4u)) {
            if (++f->activations == 1u) {
                f->first_activation = f->now;
                delay = f->delay;
            }
        }
        /* UINT32_MAX denotes no assertion from the original command. */
        f->busy_from = f->now + (delay == UINT32_MAX ? 100000u : delay);
        f->busy_until = f->busy_from + 30u;
    }
    return true;
}
static comp_ssd1681_wba_status_t step(comp_ssd1681_wba_t *d, fixture_t *f)
{
    ++f->now;
    const comp_ssd1681_wba_status_t s = comp_ssd1681_wba_poll(d);
    if (d->stats.activation_start_misses && !f->missing_at) {
        f->missing_at = f->now;
        f->original_deadline = d->deadline_ms;
    }
    return s;
}
static bool start(comp_ssd1681_wba_t *d, fixture_t *f, bool recording)
{
    static uint8_t previous[5000], current[5000];
    memset(previous, 255, sizeof(previous));
    memcpy(current, previous, sizeof(current));
    current[22u * 25u + 3u] = 0u;
    const comp_ssd1681_wba_config_t c = {
        .transfer = transfer, .is_busy = busy, .now_ms = tick, .context = f,
        .reset_mode = COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY,
        .allow_mode2_recovery = allowed, .busy_timeout_ms = 5000u,
        .partial_limit = UINT8_MAX,
    };
    if (!comp_ssd1681_wba_init(d, &c) ||
        !comp_ssd1681_wba_start_full(d, previous, previous, sizeof(previous))) return false;
    for (unsigned n = 0u; d->status == COMP_SSD1681_WBA_ACTIVE && n < 3000u; ++n)
        (void)step(d, f);
    if (d->status != COMP_SSD1681_WBA_COMPLETE || !d->baseline_valid) return false;
    f->scenario = true;
    const comp_ssd1681_wba_window_t w = {3u, 3u, 22u, 22u};
    return recording ? comp_ssd1681_wba_start_recording_partial(
        d, previous, current, sizeof(current), &w) :
        comp_ssd1681_wba_start_partial_pair(d, previous, current, sizeof(current), &w);
}
static void finish(comp_ssd1681_wba_t *d, fixture_t *f)
{
    for (unsigned n = 0u; d->status == COMP_SSD1681_WBA_ACTIVE && n < 7000u; ++n)
        (void)step(d, f);
}
int main(void)
{
    comp_ssd1681_wba_t d;
    fixture_t f;
    for (unsigned recording = 0u; recording < 2u; ++recording) {
        f = (fixture_t){.now = 100u, .delay = 108u};
        CHECK(start(&d, &f, recording != 0u));
        finish(&d, &f);
        CHECK(d.status == COMP_SSD1681_WBA_COMPLETE && d.baseline_valid);
        CHECK(f.missing_at == f.first_activation + 100u);
        CHECK(f.resets == 0u && f.activations == 1u && f.writes_while_busy == 0u);
        CHECK(d.stats.activation_retries == 0u && d.stats.delayed_starts == 1u);
        printf("LATE_ORIGINAL recording=%u: BUSY at +108ms wins; no reset or second activation\n", recording);
    }

    f = (fixture_t){.now = 100u, .delay = 0u};
    CHECK(start(&d, &f, false));
    finish(&d, &f);
    CHECK(d.status == COMP_SSD1681_WBA_COMPLETE && f.resets == 0u && f.activations == 1u);
    CHECK(f.missing_at == 0u && f.writes_while_busy == 0u);
    puts("NORMAL: ordinary start path retains its cadence");

    f = (fixture_t){.now = 100u, .delay = UINT32_MAX};
    CHECK(start(&d, &f, false));
    finish(&d, &f);
    CHECK(d.status == COMP_SSD1681_WBA_COMPLETE && d.baseline_valid);
    CHECK(f.resets == 1u && f.activations == 2u && f.writes_while_busy == 0u);
    CHECK(f.retry_reset >= f.missing_at + 21u);
    CHECK(d.stats.activation_retries == 1u && d.stats.activation_recoveries == 1u);
    printf("ABSENT_START: one reset after ready qualification; missing=%lu reset=%lu\n",
           (unsigned long)f.missing_at, (unsigned long)f.retry_reset);

    f = (fixture_t){.now = 100u, .delay = UINT32_MAX, .reset_stuck = true};
    CHECK(start(&d, &f, false));
    finish(&d, &f);
    CHECK(d.status == COMP_SSD1681_WBA_ERROR && !d.baseline_valid);
    CHECK(d.error == COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT && f.now == f.original_deadline);
    CHECK(f.resets == 1u && f.activations == 1u && f.writes_while_busy == 0u);
    puts("STUCK_RECOVERY: original 5s deadline retained; no fabricated completion");
    puts("PASS_RECOVERY_READY_HANDOFF_ONLY; physical screen NOT_RUN");
    return 0;
}
