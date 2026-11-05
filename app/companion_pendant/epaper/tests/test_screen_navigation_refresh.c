#include "screen_presenter_wba.h"

#include <stdio.h>
#include <string.h>

#define REQUIRE(condition)                                                       \
    do {                                                                         \
        if (!(condition)) {                                                       \
            fprintf(stderr, "FAIL:%d: %s\n", __LINE__, #condition);             \
            return 1;                                                            \
        }                                                                        \
    } while (0)

typedef struct {
    uint32_t now;
    uint32_t busy_until;
    uint32_t transfers;
    uint32_t fail_transfer_at;
    uint32_t completions;
    uint32_t visible;
    uint32_t failed;
    uint32_t last_token;
    uint32_t last_completion_ms;
    uint8_t pattern;
    uint8_t last_render_kind;
    uint32_t command_24;
    uint32_t command_26;
    uint32_t activation_commands;
    uint8_t recording_wave;
    bool draw_recording;
    bool cross_recording_bounds;
    bool render_fail;
} fixture_t;

static bool transfer(void *context, bool data, const uint8_t *bytes,
                     uint16_t size)
{
    fixture_t *fixture = context;

    fixture->transfers++;
    if (fixture->fail_transfer_at != 0u &&
        fixture->transfers == fixture->fail_transfer_at) {
        return false;
    }
    if (bytes == NULL || size == 0u) return false;
    if (!data && size == 1u) {
        if (bytes[0] == 0x24u) fixture->command_24++;
        if (bytes[0] == 0x26u) fixture->command_26++;
        if (bytes[0] == 0x20u) fixture->activation_commands++;
        if (bytes[0] == 0x12u || bytes[0] == 0x20u) {
            fixture->busy_until = fixture->now + 2u;
        }
    }
    return true;
}

static bool set_reset(void *context, bool asserted)
{
    (void)context;
    (void)asserted;
    return true;
}

static bool is_busy(void *context)
{
    const fixture_t *fixture = context;
    return fixture->now < fixture->busy_until;
}

static uint32_t panel_now(void *context)
{
    return ((fixture_t *)context)->now;
}

static bool render(void *context, const comp_runtime_frame_t *request,
                   uint8_t frame[COMP_SSD1681_WBA_FRAME_BYTES])
{
    fixture_t *fixture = context;

    fixture->last_render_kind = (uint8_t)request->kind;
    if (fixture->render_fail) return false;
    memset(frame, 0xFF, COMP_SSD1681_WBA_FRAME_BYTES);
    frame[3u] = 0x00u;
    if (fixture->pattern >= 2u) {
        frame[COMP_SSD1681_WBA_BYTES_PER_ROW + 4u] = 0x7Fu;
    }
    if (fixture->pattern >= 3u) {
        frame[2u * COMP_SSD1681_WBA_BYTES_PER_ROW + 5u] = 0x3Fu;
    }
    if (fixture->pattern >= 4u) {
        frame[3u * COMP_SSD1681_WBA_BYTES_PER_ROW + 6u] = 0x1Fu;
    }
    if (fixture->pattern >= 5u) {
        frame[4u * COMP_SSD1681_WBA_BYTES_PER_ROW + 7u] = 0x0Fu;
    }
    if (fixture->pattern >= 6u) {
        frame[5u * COMP_SSD1681_WBA_BYTES_PER_ROW + 8u] = 0x07u;
    }
    if (fixture->draw_recording) {
        frame[COMP_SSD1681_WBA_RECORDING_Y_MIN * COMP_SSD1681_WBA_BYTES_PER_ROW + 1u] =
            fixture->recording_wave;
        frame[(COMP_SSD1681_WBA_RECORDING_Y_MIN + 8u) * COMP_SSD1681_WBA_BYTES_PER_ROW + 3u] = 0x00u;
    }
    if (fixture->cross_recording_bounds) {
        frame[99u * COMP_SSD1681_WBA_BYTES_PER_ROW + 3u] = 0x7Eu;
        frame[199u * COMP_SSD1681_WBA_BYTES_PER_ROW + 3u] = 0x3Cu;
    }
    return true;
}

static void complete(void *context, uint32_t token, bool visible,
                     uint32_t now_ms)
{
    fixture_t *fixture = context;

    fixture->completions++;
    fixture->last_token = token;
    fixture->last_completion_ms = now_ms;
    if (visible) fixture->visible++;
    else fixture->failed++;
}

static comp_ssd1681_wba_config_t panel_config(fixture_t *fixture)
{
    const comp_ssd1681_wba_config_t config = {
        .transfer = transfer,
        .set_reset = set_reset,
        .is_busy = is_busy,
        .now_ms = panel_now,
        .context = fixture,
        .payload_chunk_bytes = 64u,
        .busy_timeout_ms = 30u,
        .partial_limit = 8u,
    };
    return config;
}

static bool drive(comp_screen_presenter_wba_t *presenter,
                  comp_ssd1681_wba_t *panel,
                  fixture_t *fixture)
{
    for (uint32_t count = 0u; count < 3000u; ++count) {
        (void)comp_ssd1681_wba_poll(panel);
        (void)comp_screen_presenter_wba_service(presenter, fixture->now);
        if (presenter->status != COMP_SCREEN_PRESENTER_WBA_ACTIVE) return true;
        fixture->now++;
    }
    return false;
}

static comp_runtime_frame_t request(uint32_t token,
                                    comp_screen_surface_t surface,
                                    comp_runtime_frame_kind_t kind)
{
    comp_runtime_frame_t frame;

    memset(&frame, 0, sizeof(frame));
    frame.token = token;
    frame.revision = token + 100u;
    frame.surface = surface;
    frame.kind = kind;
    frame.gaze_x = 100u;
    frame.gaze_y = 100u;
    return frame;
}


static int navigation(void)
{
    uint8_t committed[5000], staging[5000]; fixture_t fixture={0};
    comp_ssd1681_wba_t panel; comp_screen_presenter_wba_t p;
    comp_ssd1681_wba_config_t pc=panel_config(&fixture);
    comp_screen_presenter_wba_config_t config={&panel,render,complete,&fixture,committed,staging,UINT8_MAX};
    comp_runtime_frame_t f=request(1,COMP_SCREEN_SURFACE_HOME,COMP_RUNTIME_FRAME_STATUS);
    pc.partial_limit=UINT8_MAX;
    pc.busy_timeout_ms=5000u;
    REQUIRE(comp_ssd1681_wba_init(&panel,&pc));
    REQUIRE(comp_screen_presenter_wba_init(&p,&config));
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(p.selection.decision==COMP_EPAPER_REFRESH_DECISION_FULL);
    REQUIRE(drive(&p,&panel,&fixture)); REQUIRE(p.committed_valid);

    /* Enter menu, enter a child, return to root, leave menu. Each visible
     * navigation boundary stages the complete observed old/current pair. */
    for(unsigned step=0;step<4;step++) {
        f.token++; fixture.pattern=(uint8_t)(step+2);
        f.surface=step==3?COMP_SCREEN_SURFACE_HOME:COMP_SCREEN_SURFACE_MENU;
        f.menu.view=step==1?(comp_screen_menu_view_t)(COMP_SCREEN_MENU_VIEW_BROWSER_HOME+1):COMP_SCREEN_MENU_VIEW_BROWSER_HOME;
        REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
        REQUIRE(p.selection.decision==COMP_EPAPER_REFRESH_DECISION_FAST);
        REQUIRE(panel.previous_frame==committed && panel.current_frame==staging);
        REQUIRE(panel.window.x_start_byte==0 && panel.window.x_end_byte==24 && panel.window.y_start==0 && panel.window.y_end==199);
        REQUIRE(drive(&p,&panel,&fixture)); REQUIRE(p.committed_valid);
    }
    REQUIRE(p.stats.full_started==1 && p.stats.fast_started==4);

    /* Menu entry and same-view page changes both use full-RAM Mode2. */
    f.token++; fixture.pattern=2; f.surface=COMP_SCREEN_SURFACE_MENU;
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(p.selection.decision==COMP_EPAPER_REFRESH_DECISION_FAST);
    REQUIRE(drive(&p,&panel,&fixture));
    f.token++; fixture.pattern=3; f.menu.home_page=1;
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(p.selection.decision==COMP_EPAPER_REFRESH_DECISION_FAST);
    REQUIRE(drive(&p,&panel,&fixture));

    /* Repainting identical menu pixels does not manufacture an activation. */
    const uint32_t activations=fixture.activation_commands;
    f.token++;
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED);
    REQUIRE(fixture.activation_commands==activations && p.committed_valid);

    /* Missing physical baseline cannot be laundered by a menu transition. */
    p.committed_valid=false;
    comp_epaper_refresh_policy_commit(&p.refresh_policy,COMP_EPAPER_REFRESH_DECISION_PARTIAL,false);
    f.token++; fixture.pattern=4;
    f.menu.view=(comp_screen_menu_view_t)(COMP_SCREEN_MENU_VIEW_BROWSER_HOME+1);
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(p.selection.decision==COMP_EPAPER_REFRESH_DECISION_FULL);
    REQUIRE(p.selection.reason==COMP_EPAPER_REFRESH_REASON_BASELINE_REQUIRED);
    REQUIRE(drive(&p,&panel,&fixture)); REQUIRE(p.committed_valid);

    /* A truly due settled-family cleanup remains independent of menu speed. */
    f.token++; fixture.pattern=5; f.surface=COMP_SCREEN_SURFACE_HOME;
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(drive(&p,&panel,&fixture));
    p.full_cadence_updates=192; p.full_cadence_ms=fixture.now;
    fixture.now+=300000;
    f.token++; fixture.pattern=6; f.kind=COMP_RUNTIME_FRAME_LIFE; f.family_clean=true;
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(p.selection.decision==COMP_EPAPER_REFRESH_DECISION_FULL);
    REQUIRE(p.selection.reason==COMP_EPAPER_REFRESH_REASON_GHOST_MAINTENANCE);
    REQUIRE(drive(&p,&panel,&fixture));
    return 0;
}
int main(void) {
    if(navigation()!=0) return 1;
    puts("PASS: every changed menu page uses paired full-RAM Mode2; identical pixels skip activation; invalid baseline and due cleanup stay full; host only");
    return 0;
}
