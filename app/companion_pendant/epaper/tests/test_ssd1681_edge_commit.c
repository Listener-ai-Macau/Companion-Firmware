#include "ssd1681_wba.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(c) do { if (!(c)) { fprintf(stderr,"FAIL:%d: %s\n",__LINE__,#c); return 1; } } while (0)

/* The final RAM callback may latch a BUSY rise before returning to the
 * foreground. Do not commit buffers/baseline in that same callback's poll. */
typedef struct {
    comp_ssd1681_wba_t *driver;
    uint32_t now, busy_until, injected_at;
    unsigned data_calls, activations;
    uint8_t command, latched;
    bool armed, scenario, recording;
} fixture_t;
static bool busy(void *c) { fixture_t *f=c; return f->now<f->busy_until; }
static uint32_t tick(void *c) { return ((fixture_t *)c)->now; }
static uint8_t edges(void *c, comp_ssd1681_wba_busy_edges_action_t action)
{
    fixture_t *f=c; uint8_t result=f->latched; f->latched=0u;
    if (action==COMP_SSD1681_WBA_BUSY_EDGES_ARM) { f->armed=true; return 0u; }
    if (action==COMP_SSD1681_WBA_BUSY_EDGES_STOP) f->armed=false;
    return result;
}
static bool transfer(void *c, bool data, const uint8_t *bytes, uint16_t size)
{
    fixture_t *f=c; comp_ssd1681_wba_t *d=f->driver;
    if (!size || busy(f)) return false;
    if (!data) {
        f->command=bytes[0];
        if (f->command==0x12u || f->command==0x20u) f->busy_until=f->now+30u;
        if (f->command==0x20u) ++f->activations;
    } else {
        ++f->data_calls;
        const bool last_window=f->recording ?
            d->window.x_start_byte==3u && d->window.x_end_byte==3u &&
            d->window.y_start==22u && d->window.y_end==22u :
            d->window.x_start_byte==0u && d->window.x_end_byte==24u &&
            d->window.y_start==0u && d->window.y_end==199u;
        if (f->scenario && !f->injected_at && f->command==0x26u &&
            d->recording_phase==4u && last_window &&
            d->data_y==d->window.y_end && d->data_x+size>d->window.x_end_byte) {
            f->latched=3u; f->injected_at=f->now;
        }
    }
    return true;
}
static void step(comp_ssd1681_wba_t *d, fixture_t *f)
{ ++f->now; (void)comp_ssd1681_wba_poll(d); }
int main(int argc, char **argv)
{
    static uint8_t previous[5000],current[5000];
    comp_ssd1681_wba_t d;
    fixture_t f={.driver=&d,.now=100u,.recording=argc>1 && atoi(argv[1])!=0};
    memset(previous,255,sizeof(previous)); memcpy(current,previous,sizeof(current));
    const comp_ssd1681_wba_config_t c={.transfer=transfer,.is_busy=busy,.now_ms=tick,.context=&f,
        .reset_mode=COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY,.busy_timeout_ms=5000u,
        .partial_limit=UINT8_MAX,.take_busy_edges=edges};
    CHECK(comp_ssd1681_wba_init(&d,&c));
    CHECK(comp_ssd1681_wba_start_full(&d,previous,previous,sizeof(previous)));
    for (unsigned i=0u;i<6500u && d.status==COMP_SSD1681_WBA_ACTIVE;++i) step(&d,&f);
    CHECK(d.status==COMP_SSD1681_WBA_COMPLETE && d.baseline_valid);
    current[22u*25u+3u]=0u; current[2u]=0u;
    const comp_ssd1681_wba_window_t w={3u,3u,22u,22u};
    f.scenario=true;
    CHECK(f.recording ? comp_ssd1681_wba_start_recording_partial(&d,previous,current,sizeof(current),&w) :
          comp_ssd1681_wba_start_partial_pair(&d,previous,current,sizeof(current),&w));
    for (unsigned i=0u;i<6500u && d.status==COMP_SSD1681_WBA_ACTIVE && !f.injected_at;++i) step(&d,&f);
    printf("FINAL_RAM_RISE recording=%u: status=%u paired=%lu recording=%lu armed=%u\n",
        (unsigned)f.recording,(unsigned)d.status,(unsigned long)d.stats.completed_paired,
        (unsigned long)d.stats.completed_recording,(unsigned)f.armed);
    CHECK(f.injected_at!=0u && d.status==COMP_SSD1681_WBA_ACTIVE && f.armed);
    CHECK(d.stats.completed_paired==0u && d.stats.completed_recording==0u);
    const unsigned before_data=f.data_calls, before_activation=f.activations;
    while (d.status==COMP_SSD1681_WBA_ACTIVE && f.now<f.injected_at+20u) step(&d,&f);
    CHECK(d.status==COMP_SSD1681_WBA_ACTIVE);
    for (unsigned i=0u;i<50u && d.status==COMP_SSD1681_WBA_ACTIVE;++i) step(&d,&f);
    CHECK(d.status==COMP_SSD1681_WBA_COMPLETE && d.baseline_valid && !f.armed);
    CHECK(f.data_calls==before_data && f.activations==before_activation);
    CHECK(f.recording ? d.stats.completed_recording==1u : d.stats.completed_paired==1u);
    puts("PASS_FINAL_RAM_EDGE_COMMIT_GATE_ONLY; no additional RAM/activation; physical screen NOT_RUN");
    return 0;
}
