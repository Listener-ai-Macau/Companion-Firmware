#include "ssd1681_wba.h"

#include <stdio.h>
#include <string.h>

#define CHECK(c) do { if (!(c)) { \
    fprintf(stderr, "FAIL:%d: %s\n", __LINE__, #c); return 1; } } while (0)

/* Only the software-reset entry is modeled. The late BUSY is injected after
 * the previous poll qualified ready, before the next poll can issue 0x12.
 * This proves a software ordering defect, not a physical screen root cause. */
typedef struct {
    uint32_t now, busy_until, reset_at, writes_while_busy;
    uint32_t resets;
} fixture_t;

static bool transfer(void *context, bool data, const uint8_t *bytes, uint16_t size)
{
    fixture_t *f = context;
    if ((int32_t)(f->now - f->busy_until) < 0) {
        ++f->writes_while_busy;
        return false;
    }
    if (!data && size == 1u && bytes[0] == 0x12u) {
        ++f->resets;
        f->reset_at = f->now;
    }
    return true;
}
static bool busy(void *context)
{
    fixture_t *f = context;
    return (int32_t)(f->now - f->busy_until) < 0;
}
static uint32_t tick(void *context) { return ((fixture_t *)context)->now; }

static bool enter_reset(comp_ssd1681_wba_t *driver, fixture_t *f, uint16_t timeout)
{
    static uint8_t frame[5000];
    memset(frame, 255, sizeof(frame));
    const comp_ssd1681_wba_config_t config = {
        .transfer = transfer, .is_busy = busy, .now_ms = tick, .context = f,
        .reset_mode = COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY,
        .busy_timeout_ms = timeout, .partial_limit = UINT8_MAX,
    };
    if (!comp_ssd1681_wba_init(driver, &config) ||
        !comp_ssd1681_wba_start_full(driver, frame, frame, sizeof(frame))) return false;
    for (unsigned n = 0; n < 200u; ++n, ++f->now) {
        /* ST_SOFTWARE_RESET=6 is the stage retained in actual failure traces.
         * Stop between polls, with no reset command already sent. */
        if (driver->stage == 6u) return f->resets == 0u;
        if (comp_ssd1681_wba_poll(driver) != COMP_SSD1681_WBA_ACTIVE) return false;
    }
    return false;
}

int main(void)
{
    fixture_t f = {.now = 100u};
    comp_ssd1681_wba_t driver;
    CHECK(enter_reset(&driver, &f, 100u));
    CHECK(comp_ssd1681_wba_poll(&driver) == COMP_SSD1681_WBA_ACTIVE);
    CHECK(f.resets == 1u && f.writes_while_busy == 0u);
    puts("NORMAL_READY: one software reset after ready qualification");

    f = (fixture_t){.now = 100u};
    CHECK(enter_reset(&driver, &f, 100u));
    f.busy_until = f.now + 35u;
    const uint32_t release = f.busy_until;
    CHECK(comp_ssd1681_wba_poll(&driver) == COMP_SSD1681_WBA_ACTIVE);
    CHECK(f.resets == 0u && f.writes_while_busy == 0u);
    for (unsigned n = 0; n < 60u && f.resets == 0u; ++n) {
        ++f.now;
        CHECK(comp_ssd1681_wba_poll(&driver) == COMP_SSD1681_WBA_ACTIVE);
    }
    CHECK(f.resets == 1u && f.reset_at >= release + 20u);
    CHECK(f.writes_while_busy == 0u);
    printf("LATE_BUSY: reset deferred until stable ready; release=%lu reset=%lu\n",
           (unsigned long)release, (unsigned long)f.reset_at);

    f = (fixture_t){.now = 100u};
    CHECK(enter_reset(&driver, &f, 100u));
    const uint32_t deadline = driver.deadline_ms;
    f.busy_until = deadline + 200u;
    for (unsigned n = 0; n < 200u && driver.status == COMP_SSD1681_WBA_ACTIVE; ++n) {
        (void)comp_ssd1681_wba_poll(&driver);
        if (driver.status == COMP_SSD1681_WBA_ACTIVE) ++f.now;
    }
    CHECK(driver.status == COMP_SSD1681_WBA_ERROR);
    CHECK(driver.error == COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
    CHECK(!driver.baseline_valid && driver.stats.busy_timeouts == 1u);
    CHECK(f.now == deadline && f.resets == 0u && f.writes_while_busy == 0u);
    puts("STUCK_BUSY: original deadline expires without reset or valid baseline");
    puts("PASS_SOFTWARE_RESET_READY_GUARD_ONLY; physical screen NOT_RUN");
    return 0;
}
