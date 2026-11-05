#include "ssd1681_wba.h"
#include <stdio.h>
#include <string.h>

#define CHECK(c) do { if (!(c)) { fprintf(stderr, "FAIL:%d: %s\n", __LINE__, #c); return 1; } } while (0)

/* Reproduce a short BUSY pulse missed by level polls but retained by EXTI.
 * This checks software admission/commit ordering, not a panel waveform. */
typedef struct {
    uint32_t now, busy_until, pulse_until, last_pulse;
    uint32_t parameter_command_ms, parameter_data_ms;
    unsigned calls, arms, stops, activations;
    uint8_t command, control, latched;
    bool armed, parameter_edge, suppress_activation;
} fixture_t;

static bool busy(void *c) { fixture_t *f = c; return f->now < f->busy_until; }
static uint32_t tick(void *c) { return ((fixture_t *)c)->now; }
static uint8_t edges(void *c, comp_ssd1681_wba_busy_edges_action_t action)
{
    fixture_t *f = c;
    uint8_t result = f->latched;
    f->latched = 0u;
    if (action == COMP_SSD1681_WBA_BUSY_EDGES_ARM) {
        f->armed = true; ++f->arms; return 0u;
    }
    if (action == COMP_SSD1681_WBA_BUSY_EDGES_STOP) { f->armed = false; ++f->stops; }
    return result;
}
static bool transfer(void *c, bool data, const uint8_t *bytes, uint16_t size)
{
    fixture_t *f = c;
    if (!size || busy(f)) return false;
    ++f->calls;
    if (data) {
        if (f->command == 0x22u) f->control = bytes[0];
        if (f->command == 0x18u && f->parameter_command_ms && !f->parameter_data_ms)
            f->parameter_data_ms = f->now;
    } else {
        f->command = bytes[0];
        if (f->command == 0x18u && f->parameter_edge && !f->parameter_command_ms) {
            f->parameter_command_ms = f->now;
            if (f->armed) f->latched |= 3u;
        }
        if (f->command == 0x12u) f->busy_until = f->now + 30u;
        if (f->command == 0x20u) {
            ++f->activations;
            if (f->suppress_activation && (f->control & 4u)) {
                if (f->armed) f->latched |= 3u;
            } else f->busy_until = f->now + 30u;
        }
    }
    return true;
}
static void step(comp_ssd1681_wba_t *d, fixture_t *f)
{
    ++f->now;
    if (f->now < f->pulse_until && f->now % 5u == 0u) {
        if (f->armed) f->latched |= 3u;
        f->last_pulse = f->now;
    }
    (void)comp_ssd1681_wba_poll(d);
}
static bool start(comp_ssd1681_wba_t *d, fixture_t *f, const uint8_t *old, const uint8_t *current)
{
    const comp_ssd1681_wba_config_t config = {
        .transfer=transfer, .is_busy=busy, .now_ms=tick, .context=f,
        .busy_timeout_ms=5000u, .partial_limit=UINT8_MAX,
        .reset_mode=COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY,
        .take_busy_edges=edges,
    };
    return comp_ssd1681_wba_init(d, &config) &&
        comp_ssd1681_wba_start_full(d, old, current, 5000u);
}
static void finish(comp_ssd1681_wba_t *d, fixture_t *f)
{
    for (unsigned i=0u; i<6500u && d->status==COMP_SSD1681_WBA_ACTIVE; ++i) step(d,f);
}

int main(void)
{
    static uint8_t old[5000], current[5000];
    memset(old, 255, sizeof(old)); memcpy(current, old, sizeof(current));
    current[22u*25u+3u]=0u;
    comp_ssd1681_wba_t d;
    fixture_t f = {.now=100u, .pulse_until=300u};
    CHECK(start(&d,&f,old,current));
    while (f.now < 299u) step(&d,&f);
    printf("HIDDEN_RISE: raw pin low; calls=%u last_edge=%lu ready=%u\n",f.calls,(unsigned long)f.last_pulse,(unsigned)d.ready_candidate);
    CHECK(f.calls==0u && d.status==COMP_SSD1681_WBA_ACTIVE);
    while (!f.calls && f.now<350u) step(&d,&f);
    CHECK(f.calls!=0u && f.now>=f.last_pulse+20u);
    finish(&d,&f);
    CHECK(d.status==COMP_SSD1681_WBA_COMPLETE && d.baseline_valid && !f.armed);
    puts("QUIET_RESUMES: no extra reset or activation; normal full completes");

    f=(fixture_t){.now=100u, .parameter_edge=true};
    CHECK(start(&d,&f,old,current)); finish(&d,&f);
    CHECK(d.status==COMP_SSD1681_WBA_COMPLETE);
    CHECK(f.parameter_data_ms>=f.parameter_command_ms+20u);
    puts("BETWEEN_COMMAND_DATA: latched rise holds pending parameters for quiet interval");

    const comp_ssd1681_wba_window_t w={3u,3u,22u,22u};
    const uint32_t previous_visible=d.stats.last_visible_completed_ms;
    CHECK(comp_ssd1681_wba_start_partial_pair(&d,old,current,5000u,&w));
    while (d.status==COMP_SSD1681_WBA_ACTIVE && d.stats.last_visible_completed_ms==previous_visible)
        step(&d,&f);
    CHECK(d.status==COMP_SSD1681_WBA_ACTIVE && d.recording_phase==3u && f.armed);
    /* Drain the view-completion timestamp transition, then inject pulses
     * only while the unchanged full-frame post-sync would otherwise write. */
    while (d.status==COMP_SSD1681_WBA_ACTIVE && !(d.stage==11u && d.data_command_sent)) step(&d,&f);
    CHECK(d.status==COMP_SSD1681_WBA_ACTIVE && f.armed);
    unsigned before=f.calls;
    f.pulse_until=f.now+60u; f.latched=3u;
    while (f.now<f.pulse_until-1u) step(&d,&f);
    CHECK(f.calls==before && d.status==COMP_SSD1681_WBA_ACTIVE && d.stats.completed_paired==0u);
    finish(&d,&f);
    CHECK(d.status==COMP_SSD1681_WBA_COMPLETE && d.baseline_valid && !f.armed);
    CHECK(d.stats.completed_paired==1u);
    puts("POST_SYNC: quiet gate remains armed through both full RAM planes");

    f=(fixture_t){.now=100u, .pulse_until=20000u};
    CHECK(start(&d,&f,old,current)); finish(&d,&f);
    CHECK(d.status==COMP_SSD1681_WBA_ERROR && d.error==COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
    CHECK(f.calls==0u && !f.armed && !d.baseline_valid && f.now==5110u);
    puts("PERSISTENT_RISES: original 5s deadline; no unsafe command or fabricated baseline");

    f=(fixture_t){.now=100u, .suppress_activation=true};
    CHECK(start(&d,&f,old,current)); finish(&d,&f);
    CHECK(d.status==COMP_SSD1681_WBA_ERROR && !d.busy_observed && !d.baseline_valid);
    CHECK(d.stats.visible_edge_flags==3u && d.stats.visible_high_samples==0u && !f.armed);
    puts("EDGE_ONLY: rise/fall flags cannot substitute for actual BUSY-high start");
    puts("PASS_EDGE_READY_VETO_ONLY; physical screen NOT_RUN");
    return 0;
}
