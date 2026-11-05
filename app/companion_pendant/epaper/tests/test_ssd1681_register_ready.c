#include "ssd1681_wba.h"

#include <stdio.h>
#include <string.h>

#define CHECK(c) do { if (!(c)) { \
    fprintf(stderr, "FAIL:%d: %s\n", __LINE__, #c); return 1; } } while (0)

/* The real production driver is linked. Inject BUSY inside one foreground
 * poll, after the window command but before its parameter transfer. This
 * checks software packet ownership, not panel waveforms or physical ghosting. */
typedef struct {
    uint32_t now, busy_until, inject_ms, window_at, parameters_at;
    unsigned window_commands, window_parameters, writes_while_busy;
    uint8_t command;
    bool injected;
} fixture_t;

static bool busy(void *context)
{
    fixture_t *f = context;
    return (int32_t)(f->now - f->busy_until) < 0;
}
static uint32_t tick(void *context) { return ((fixture_t *)context)->now; }
static bool transfer(void *context, bool data, const uint8_t *bytes, uint16_t size)
{
    fixture_t *f = context;
    if (busy(f)) {
        ++f->writes_while_busy;
        return false;
    }
    if (!bytes || !size) return false;
    if (!data) {
        if (size != 1u) return false;
        f->command = bytes[0];
        if (bytes[0] == 0x44u) {
            ++f->window_commands;
            f->window_at = f->now;
            if (!f->injected && f->inject_ms != 0u) {
                f->injected = true;
                f->busy_until = f->now + f->inject_ms;
            }
        } else if (bytes[0] == 0x12u || bytes[0] == 0x20u) {
            f->busy_until = f->now + 30u;
        }
    } else if (f->command == 0x44u) {
        if (size != 2u || bytes[0] != 0u || bytes[1] != 24u) return false;
        ++f->window_parameters;
        f->parameters_at = f->now;
    }
    return true;
}
static bool start(comp_ssd1681_wba_t *d, fixture_t *f)
{
    static uint8_t frame[5000];
    memset(frame, 255, sizeof(frame));
    const comp_ssd1681_wba_config_t c = {
        .transfer = transfer, .is_busy = busy, .now_ms = tick, .context = f,
        .reset_mode = COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY,
        .busy_timeout_ms = 5000u, .partial_limit = UINT8_MAX,
    };
    return comp_ssd1681_wba_init(d, &c) &&
        comp_ssd1681_wba_start_full(d, frame, frame, sizeof(frame));
}
static bool run_to_window(comp_ssd1681_wba_t *d, fixture_t *f)
{
    for (unsigned n = 0; n < 1000u; ++n, ++f->now) {
        if (comp_ssd1681_wba_poll(d) != COMP_SSD1681_WBA_ACTIVE) return false;
        if (f->window_commands) return true;
    }
    return false;
}
int main(void)
{
    comp_ssd1681_wba_t d;
    fixture_t f = {.now = 100u};
    CHECK(start(&d, &f) && run_to_window(&d, &f));
    CHECK(f.window_commands == 1u && f.window_parameters == 1u);
    CHECK(f.parameters_at == f.window_at && f.writes_while_busy == 0u);
    puts("NORMAL_REGISTER: command and parameters retain the same foreground poll");

    f = (fixture_t){.now = 100u, .inject_ms = 35u};
    CHECK(start(&d, &f) && run_to_window(&d, &f));
    CHECK(f.window_parameters == 0u && f.writes_while_busy == 0u);
    CHECK(d.sequence_data_pending == 1u);
    const uint32_t release = f.busy_until;
    for (unsigned n = 0; n < 80u && f.window_parameters == 0u; ++n) {
        ++f.now;
        CHECK(comp_ssd1681_wba_poll(&d) == COMP_SSD1681_WBA_ACTIVE);
    }
    CHECK(f.window_commands == 1u && f.window_parameters == 1u);
    CHECK(d.sequence_data_pending == 0u && f.writes_while_busy == 0u);
    CHECK(f.parameters_at >= release + 20u);
    printf("LATE_BUSY: retained parameters sent once after stable ready; release=%lu parameters=%lu\n",
           (unsigned long)release, (unsigned long)f.parameters_at);

    f = (fixture_t){.now = 100u, .inject_ms = 10000u};
    CHECK(start(&d, &f) && run_to_window(&d, &f));
    const uint32_t deadline = d.deadline_ms;
    while (d.status == COMP_SSD1681_WBA_ACTIVE && f.now <= deadline) {
        ++f.now;
        (void)comp_ssd1681_wba_poll(&d);
    }
    CHECK(d.status == COMP_SSD1681_WBA_ERROR);
    CHECK(d.error == COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT && f.now == deadline);
    CHECK(f.window_commands == 1u && f.window_parameters == 0u);
    CHECK(f.writes_while_busy == 0u && !d.baseline_valid);
    puts("STUCK_BUSY: original deadline retained; no parameters or valid baseline fabricated");
    puts("PASS_REGISTER_PARAMETER_READY_GUARD_ONLY; physical screen NOT_RUN");
    return 0;
}
