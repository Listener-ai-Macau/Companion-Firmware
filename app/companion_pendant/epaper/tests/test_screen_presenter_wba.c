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
    bool large_page;
    uint8_t command,parameter_count,parameters[4],entry;
    uint16_t x0,x1,y0,y1,x,y;
    uint8_t ram[2][COMP_SSD1681_WBA_FRAME_BYTES];
    uint32_t microphone_writes[2],invalid_ram_writes,reset_calls;
    uint32_t control_activations;
    uint8_t update_control;
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
        if (bytes[0] == 0x20u) {
            ++fixture->control_activations;
            /* B1/B9 load temperature/profile without a visible update. */
            if(fixture->update_control==0xF7u || fixture->update_control==0xC7u ||
               fixture->update_control==0xFFu || fixture->update_control==0xCFu)
                ++fixture->activation_commands;
        }
        if (bytes[0] == 0x12u || bytes[0] == 0x20u) {
            fixture->busy_until = fixture->now + 2u;
        }
    }
    if (!data && size==1u) {
        fixture->command=bytes[0];fixture->parameter_count=0u;
    } else if (data && (fixture->command==0x24u || fixture->command==0x26u)) {
        const unsigned plane=fixture->command==0x24u?0u:1u;
        for(uint16_t i=0u;i<size;++i) {
            if(fixture->x>=25u || fixture->y>=200u || fixture->entry!=1u) {
                ++fixture->invalid_ram_writes;continue;
            }
            const unsigned offset=fixture->y*25u+fixture->x;
            fixture->ram[plane][offset]=bytes[i];
            if(offset==(COMP_SSD1681_WBA_RECORDING_Y_MIN+8u)*25u+3u)
                ++fixture->microphone_writes[plane];
            if(++fixture->x>fixture->x1) {
                fixture->x=fixture->x0;
                if(fixture->y==fixture->y1)fixture->y=fixture->y0;
                else --fixture->y;
            }
        }
    } else if(data && (fixture->command==0x11u || fixture->command==0x22u || fixture->command==0x44u || fixture->command==0x45u ||
                      fixture->command==0x4Eu || fixture->command==0x4Fu)) {
        for(uint16_t i=0u;i<size;++i) {
            if(fixture->parameter_count>=4u) {++fixture->invalid_ram_writes;continue;}
            fixture->parameters[fixture->parameter_count++]=bytes[i];
        }
        const uint8_t *v=fixture->parameters;
        if(fixture->command==0x11u && fixture->parameter_count==1u)fixture->entry=v[0];
        if(fixture->command==0x22u && fixture->parameter_count==1u)fixture->update_control=v[0];
        if(fixture->command==0x44u && fixture->parameter_count==2u) {fixture->x0=v[0];fixture->x1=v[1];}
        if(fixture->command==0x45u && fixture->parameter_count==4u) {
            fixture->y0=(uint16_t)(v[0]|((uint16_t)v[1]<<8u));
            fixture->y1=(uint16_t)(v[2]|((uint16_t)v[3]<<8u));
        }
        if(fixture->command==0x4Eu && fixture->parameter_count==1u)fixture->x=v[0];
        if(fixture->command==0x4Fu && fixture->parameter_count==2u)
            fixture->y=(uint16_t)(v[0]|((uint16_t)v[1]<<8u));
    }
    return true;
}

static bool set_reset(void *context, bool asserted)
{
    ++((fixture_t *)context)->reset_calls;
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
    if (fixture->large_page)memset(frame+40u*25u,0,40u*25u);
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
#if COMP_V11_PANEL_VENDOR_QUICK_SOFTWARE_RESET
        .set_reset = NULL,
#else
        .set_reset = set_reset,
#endif
        .is_busy = is_busy,
        .now_ms = panel_now,
        .context = fixture,
        .payload_chunk_bytes = 64u,
        /* Current driver includes120ms profile/rearm settles. The original
         * 30ms fixture failed before any initial baseline became visible. */
        .busy_timeout_ms = 5000u,
        .partial_limit = 8u,
#if COMP_V11_PANEL_VENDOR_QUICK_SOFTWARE_RESET
        .reset_mode=COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY,
#else
        .reset_mode=COMP_SSD1681_WBA_RESET_HARDWARE,
#endif
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

typedef union {
    uint8_t plain[COMP_SSD1681_WBA_FRAME_BYTES];
    comp_wba_frame_store_t packed;
} old_store_t;

static bool stored_matches(const comp_screen_presenter_wba_t *p,const uint8_t *expected)
{
#if COMP_WBA_PACKED_OLD_FRAME
    comp_wba_frame_store_t copy=*(const comp_wba_frame_store_t *)(const void *)p->config.committed_frame;
    uint8_t row[25];
    for(size_t at=0u;at<5000u;at+=25u)
        if(!comp_wba_frame_store_read(&copy,at,row,25u) || memcmp(row,expected+at,25u))return false;
    return true;
#else
    return memcmp(p->config.committed_frame,expected,5000u)==0;
#endif
}
static bool both_ram_planes_match(const comp_screen_presenter_wba_t *p,const fixture_t *f)
{
    if(f->invalid_ram_writes || !stored_matches(p,p->config.staging_frame))return false;
    if(p->config.panel->config.reset_mode==COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY && f->reset_calls)return false;
    /* RAM registers run X+/Y-. Presenter storage uses the retained row-flipped
     * order, so translate addresses explicitly rather than assuming Y+. */
    for(unsigned y=0u;y<200u;++y)for(unsigned x=0u;x<25u;++x)
        if(f->ram[0][(199u-y)*25u+x]!=p->config.staging_frame[y*25u+x] ||
           f->ram[1][(199u-y)*25u+x]!=p->config.staging_frame[y*25u+x])return false;
    return true;
}
static bool wait_for_ready(comp_screen_presenter_wba_t *p,comp_ssd1681_wba_t *panel,fixture_t *f)
{
    for(unsigned i=0u;i<200u;++i) {
        (void)comp_ssd1681_wba_poll(panel);
        if(comp_screen_presenter_wba_ready_for_frame(p,f->now))return true;
        ++f->now;
    }
    return false;
}

static int test_presenter_journey(void)
{
    old_store_t old_store;
    uint8_t *committed=old_store.plain;
    uint8_t staging[COMP_SSD1681_WBA_FRAME_BYTES];
    fixture_t fixture = {0};
    comp_ssd1681_wba_t panel;
    comp_screen_presenter_wba_t presenter;
    comp_screen_presenter_wba_stats_t stats;
    comp_ssd1681_wba_config_t panel_value = panel_config(&fixture);
    comp_screen_presenter_wba_config_t presenter_value = {
        .panel = &panel,
        .render = render,
        .complete = complete,
        .context = &fixture,
        .committed_frame = committed,
        .staging_frame = staging,
        .partial_limit = 1u,
    };
    comp_runtime_frame_t frame;
    uint32_t transfers_before;

    memset(&old_store, 0xA5, sizeof(old_store));
    memset(staging, 0x5A, sizeof(staging));
    REQUIRE(comp_ssd1681_wba_init(&panel, &panel_value));
    REQUIRE(comp_screen_presenter_wba_init(&presenter, &presenter_value));

    /* First full seeds both planes with the target, still logically invalid.
     * Browser row zero maps
     * to controller row 199 and no horizontal mirror is introduced. */
    fixture.pattern = 1u;
    frame = request(11u, COMP_SCREEN_SURFACE_HOME, COMP_RUNTIME_FRAME_STATUS);
    REQUIRE(comp_screen_presenter_wba_submit(&presenter, &frame, fixture.now) ==
            COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(staging[199u * COMP_SSD1681_WBA_BYTES_PER_ROW + 3u] == 0x00u);
    REQUIRE(staging[3u] == 0xFFu);
    REQUIRE(stored_matches(&presenter,staging));
    REQUIRE(!presenter.committed_valid && !presenter.refresh_policy.baseline_valid &&
            !comp_ssd1681_wba_baseline_valid(&panel));
    REQUIRE(panel.previous_frame == committed && panel.current_frame == staging);
    frame.token = 999u;
    REQUIRE(comp_screen_presenter_wba_submit(&presenter, &frame, fixture.now) ==
            COMP_SCREEN_PRESENTER_WBA_SUBMIT_BUSY);
    REQUIRE(fixture.completions == 0u);
    REQUIRE(drive(&presenter, &panel, &fixture));
    REQUIRE(fixture.completions == 1u && fixture.last_token == 11u &&
            fixture.visible == 1u);
    REQUIRE(both_ram_planes_match(&presenter,&fixture));
    REQUIRE(presenter.refresh_policy.baseline_valid);

    /* One browser byte changes on row one. The partial window is exact after
     * row mapping: controller byte x=4, row y=198. */
    fixture.pattern = 2u;
    frame = request(12u, COMP_SCREEN_SURFACE_HOME, COMP_RUNTIME_FRAME_LIFE);
    const bool full_priming=panel.stats.mode2_since_full==0u;
    REQUIRE(comp_screen_presenter_wba_submit(&presenter, &frame, fixture.now) ==
            COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(presenter.selection.decision ==
            COMP_EPAPER_REFRESH_DECISION_PARTIAL);
    REQUIRE(presenter.dirty_window.x_start_byte==4u && presenter.dirty_window.x_end_byte==4u &&
            presenter.dirty_window.y_start==198u && presenter.dirty_window.y_end==198u);
    /* First Mode2 after a full retains the existing complete priming write.
     * Later local requests still use their exact validated difference. */
    if(full_priming) {
        REQUIRE(panel.window.x_start_byte==0u && panel.window.x_end_byte==24u &&
                panel.window.y_start==0u && panel.window.y_end==199u);
    } else {
        REQUIRE(panel.window.x_start_byte==4u && panel.window.x_end_byte==4u &&
                panel.window.y_start==198u && panel.window.y_end==198u);
    }
    REQUIRE(drive(&presenter, &panel, &fixture));
    REQUIRE(fixture.last_token == 12u && presenter.refresh_policy.partial_count == 1u);

    /* Same pixels complete synchronously and do not spend a refresh budget or
     * transfer another byte. */
    transfers_before = fixture.transfers;
    frame = request(13u, COMP_SCREEN_SURFACE_HOME, COMP_RUNTIME_FRAME_BLINK);
    REQUIRE(comp_screen_presenter_wba_submit(&presenter, &frame, fixture.now) ==
            COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED);
    REQUIRE(fixture.last_token == 13u && fixture.transfers == transfers_before);
    REQUIRE(presenter.refresh_policy.partial_count == 1u);

    /* The shared refresh policy turns the next partial into a full maintenance
     * boundary once its configured limit is reached. */
    fixture.pattern = 3u;
    frame = request(14u, COMP_SCREEN_SURFACE_HOME, COMP_RUNTIME_FRAME_REACTION);
    REQUIRE(comp_screen_presenter_wba_submit(&presenter, &frame, fixture.now) ==
            COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(presenter.selection.decision == COMP_EPAPER_REFRESH_DECISION_FAST &&
            presenter.selection.reason == COMP_EPAPER_REFRESH_REASON_PARTIAL_LIMIT);
    REQUIRE(drive(&presenter, &panel, &fixture));
    REQUIRE(presenter.refresh_policy.partial_count == 0u);

    /* An identical sleep landing needs no activation. Explicit strong-boundary
     * policy remains available, but a surface label alone does not request it. */
    fixture.pattern=3u;transfers_before=fixture.transfers;
    frame=request(15u,COMP_SCREEN_SURFACE_LOW_POWER,COMP_RUNTIME_FRAME_STATUS);
    REQUIRE(comp_screen_presenter_wba_submit(&presenter,&frame,fixture.now)==
            COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED);
    REQUIRE(fixture.transfers==transfers_before && both_ram_planes_match(&presenter,&fixture));
    { const comp_epaper_refresh_selection_t strong=comp_epaper_refresh_policy_select(
          &presenter.refresh_policy,COMP_EPAPER_REFRESH_IDLE_ENTER_STRONG);
      REQUIRE(strong.decision==COMP_EPAPER_REFRESH_DECISION_FULL &&
              strong.reason==COMP_EPAPER_REFRESH_REASON_IDLE_ENTER_STRONG_BOUNDARY); }

    /* A renderer failure consumes the request but leaves a known physical
     * baseline intact because no panel operation started. */
    fixture.render_fail = true;
    frame = request(16u, COMP_SCREEN_SURFACE_LOW_POWER,
                    COMP_RUNTIME_FRAME_STATUS);
    REQUIRE(comp_screen_presenter_wba_submit(&presenter, &frame, fixture.now) ==
            COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED);
    REQUIRE(fixture.last_token == 16u && fixture.failed == 1u);
    REQUIRE(presenter.committed_valid && presenter.refresh_policy.baseline_valid);
    fixture.render_fail = false;

    /* A transport failure after launch rolls back the logical commit and
     * invalidates both baselines. */
    fixture.pattern = 4u;
    fixture.fail_transfer_at = fixture.transfers + 1u;
    frame = request(17u, COMP_SCREEN_SURFACE_LOW_POWER,
                    COMP_RUNTIME_FRAME_LIFE);
    REQUIRE(comp_screen_presenter_wba_submit(&presenter, &frame, fixture.now) ==
            COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(comp_screen_presenter_wba_service(&presenter, fixture.now) ==
            COMP_SCREEN_PRESENTER_WBA_ACTIVE);
    REQUIRE(drive(&presenter, &panel, &fixture));
    REQUIRE(fixture.last_token == 17u && fixture.failed == 2u);
    REQUIRE(!presenter.committed_valid &&
            !presenter.refresh_policy.baseline_valid);

    /* Recovery is necessarily full and re-establishes the baseline. */
    fixture.fail_transfer_at = 0u;
    REQUIRE(!comp_screen_presenter_wba_ready_for_frame(&presenter,fixture.now));
    REQUIRE(wait_for_ready(&presenter,&panel,&fixture));
    fixture.pattern = 5u;
    frame = request(18u, COMP_SCREEN_SURFACE_LOW_POWER,
                    COMP_RUNTIME_FRAME_STATUS);
    REQUIRE(comp_screen_presenter_wba_submit(&presenter, &frame, fixture.now) ==
            COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(presenter.selection.decision == COMP_EPAPER_REFRESH_DECISION_FULL &&
            presenter.selection.reason == COMP_EPAPER_REFRESH_REASON_BASELINE_REQUIRED);
    REQUIRE(drive(&presenter, &panel, &fixture));

    comp_screen_presenter_wba_get_stats(&presenter, &stats);
    REQUIRE(stats.submitted == 8u && stats.rendered == 7u &&
            stats.render_failures == 1u && stats.no_change_completions == 2u);
    REQUIRE(stats.full_started == 2u && stats.fast_started == 1u && stats.partial_started == 2u &&
            stats.visible_completions == 6u && stats.failed_completions == 2u &&
            stats.busy_rejections == 1u);
    REQUIRE(fixture.completions == 8u && fixture.visible == 6u &&
            fixture.last_token == 18u);
    return 0;
}

static int test_unready_panel_fails_closed(void)
{
    old_store_t old_store;
    uint8_t *committed=old_store.plain;
    uint8_t staging[COMP_SSD1681_WBA_FRAME_BYTES];
    fixture_t fixture = {0};
    comp_ssd1681_wba_t panel;
    comp_screen_presenter_wba_t presenter;
    comp_ssd1681_wba_config_t panel_value = panel_config(&fixture);
    comp_screen_presenter_wba_config_t presenter_value = {
        .panel = &panel,
        .render = render,
        .complete = complete,
        .context = &fixture,
        .committed_frame = committed,
        .staging_frame = staging,
        .partial_limit = 2u,
    };
    comp_runtime_frame_t frame =
        request(91u, COMP_SCREEN_SURFACE_HOME, COMP_RUNTIME_FRAME_STATUS);

    panel_value.set_reset = NULL;
    panel_value.reset_mode=COMP_SSD1681_WBA_RESET_HARDWARE;
    REQUIRE(!comp_ssd1681_wba_init(&panel, &panel_value));
    REQUIRE(comp_screen_presenter_wba_init(&presenter, &presenter_value));
    fixture.pattern = 1u;
    REQUIRE(comp_screen_presenter_wba_submit(&presenter, &frame, 7u) ==
            COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED);
    REQUIRE(fixture.completions == 1u && fixture.failed == 1u &&
            fixture.last_token == 91u && fixture.transfers == 0u);
    REQUIRE(!presenter.committed_valid &&
            !presenter.refresh_policy.baseline_valid);
    /* Explicit software binding must not borrow a nonexistent RESET callback.
     * It still requires a complete baseline and the following paired update. */
    memset(&fixture,0,sizeof(fixture));
    panel_value.reset_mode=COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY;
    panel_value.set_reset=set_reset;
    REQUIRE(!comp_ssd1681_wba_init(&panel,&panel_value));
    REQUIRE(fixture.transfers==0u && fixture.reset_calls==0u);
    panel_value.set_reset=NULL;
    REQUIRE(comp_ssd1681_wba_init(&panel,&panel_value));
    REQUIRE(comp_screen_presenter_wba_init(&presenter,&presenter_value));
    frame=request(92u,COMP_SCREEN_SURFACE_HOME,COMP_RUNTIME_FRAME_STATUS);
    REQUIRE(comp_screen_presenter_wba_submit(&presenter,&frame,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(drive(&presenter,&panel,&fixture) && both_ram_planes_match(&presenter,&fixture));
    fixture.pattern=2u;frame.token++;frame.kind=COMP_RUNTIME_FRAME_LIFE;
    REQUIRE(comp_screen_presenter_wba_submit(&presenter,&frame,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(drive(&presenter,&panel,&fixture) && both_ram_planes_match(&presenter,&fixture));
    REQUIRE(fixture.reset_calls==0u);
    return 0;
}

static int test_family_and_menu_boundaries(void)
{
    old_store_t old_store;uint8_t *committed=old_store.plain;uint8_t staging[5000];fixture_t fixture={0};
    comp_ssd1681_wba_t panel;comp_screen_presenter_wba_t p;
    comp_ssd1681_wba_config_t pc=panel_config(&fixture);
    comp_screen_presenter_wba_config_t config={&panel,render,complete,&fixture,committed,staging,UINT8_MAX};
    comp_runtime_frame_t f=request(1u,COMP_SCREEN_SURFACE_HOME,COMP_RUNTIME_FRAME_STATUS);
    pc.partial_limit=UINT8_MAX;
    REQUIRE(comp_ssd1681_wba_init(&panel,&pc));REQUIRE(comp_screen_presenter_wba_init(&p,&config));
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(drive(&p,&panel,&fixture) && both_ram_planes_match(&p,&fixture));
    uint32_t before=fixture.transfers;
    f.token++;f.family_clean=true;f.kind=COMP_RUNTIME_FRAME_LIFE;
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED);
    REQUIRE(fixture.transfers==before && p.full_cadence_updates==0u);
    fixture.pattern=2u;f.token++;
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(p.selection.decision==COMP_EPAPER_REFRESH_DECISION_PARTIAL &&
            p.dirty_window.x_start_byte==4u && p.dirty_window.x_end_byte==4u &&
            p.dirty_window.y_start==198u && p.dirty_window.y_end==198u);
    REQUIRE(drive(&p,&panel,&fixture) && both_ram_planes_match(&p,&fixture));
    fixture.pattern=3u;f.token++;
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(p.selection.decision==COMP_EPAPER_REFRESH_DECISION_PARTIAL &&
            panel.window.x_start_byte==5u && panel.window.x_end_byte==5u &&
            panel.window.y_start==197u && panel.window.y_end==197u);
    REQUIRE(drive(&p,&panel,&fixture) && both_ram_planes_match(&p,&fixture));

    /* Periodic clean requires all three independent conditions, never a
     * mere family label, blink or recording. These are software boundary
     * predicates; no elapsed physical ink quality is inferred. */
    p.full_cadence_updates=191u;p.full_cadence_ms=fixture.now;fixture.now+=300000u;
    before=fixture.transfers;f.token++;
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED);
    REQUIRE(fixture.transfers==before);
    p.full_cadence_updates=192u;p.full_cadence_ms=fixture.now;f.token++;
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED);
    fixture.now+=299999u;f.token++;
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED);
    ++fixture.now;f.token++;f.kind=COMP_RUNTIME_FRAME_BLINK;
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED);
    f.token++;f.kind=COMP_RUNTIME_FRAME_LIFE;f.recording=DENZIC_AUDIO_RECORDING_STATE_RECORDING;
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED);
    f.token++;f.recording=DENZIC_AUDIO_RECORDING_STATE_IDLE;
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED);
    REQUIRE(fixture.transfers==before);
    f.token++;
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(p.selection.decision==COMP_EPAPER_REFRESH_DECISION_FULL && p.selection.reason==COMP_EPAPER_REFRESH_REASON_GHOST_MAINTENANCE);
    REQUIRE(drive(&p,&panel,&fixture) && both_ram_planes_match(&p,&fixture));
    REQUIRE(p.full_cadence_updates==0u);

    /* Menu metadata with identical pixels is also a no-op. Large actual
     * changes select maintenance; the supplier option controls its waveform. */
    f.token++;f.family_clean=false;f.surface=COMP_SCREEN_SURFACE_MENU;
    f.menu.view=COMP_SCREEN_MENU_VIEW_BROWSER_HOME;before=fixture.transfers;
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED);
    REQUIRE(fixture.transfers==before);
    fixture.large_page=true;f.token++;f.menu.view=(comp_screen_menu_view_t)(COMP_SCREEN_MENU_VIEW_BROWSER_HOME+1);
    const bool vendor=comp_ssd1681_wba_vendor_quick_full_available(&panel);
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(p.selection.decision==(vendor?COMP_EPAPER_REFRESH_DECISION_FULL:COMP_EPAPER_REFRESH_DECISION_FAST));
    REQUIRE(drive(&p,&panel,&fixture) && both_ram_planes_match(&p,&fixture));
    f.token++;f.menu.home_page=1u;fixture.pattern=4u;
    REQUIRE(comp_screen_presenter_wba_submit(&p,&f,fixture.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(p.selection.decision==COMP_EPAPER_REFRESH_DECISION_PARTIAL);
    REQUIRE(drive(&p,&panel,&fixture) && both_ram_planes_match(&p,&fixture));
    REQUIRE(p.stats.full_started==(vendor?3u:2u) && p.stats.fast_started==(vendor?0u:1u) && p.stats.partial_started==3u);
    return 0;
}

static int test_recording_enter_active_and_exit_use_exact_delta(void)
{
    old_store_t old_store;uint8_t *committed=old_store.plain;
    uint8_t staging[5000];
    fixture_t fixture = {0};
    comp_ssd1681_wba_t panel;
    comp_screen_presenter_wba_t presenter;
    comp_ssd1681_wba_config_t pc = panel_config(&fixture);
    comp_screen_presenter_wba_config_t config = {
        &panel, render, complete, &fixture, committed, staging, UINT8_MAX};
    comp_runtime_frame_t frame =
        request(201u, COMP_SCREEN_SURFACE_HOME, COMP_RUNTIME_FRAME_STATUS);
    uint32_t c24;
    uint32_t c26;
    uint32_t activations;
    uint32_t mic_current,mic_old;
    uint32_t control_before;

    pc.partial_limit = UINT8_MAX;
    REQUIRE(comp_ssd1681_wba_init(&panel, &pc));
    REQUIRE(comp_screen_presenter_wba_init(&presenter, &config));
    REQUIRE(comp_screen_presenter_wba_submit(&presenter, &frame, fixture.now) ==
            COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(drive(&presenter, &panel, &fixture));

    c24 = fixture.command_24;
    c26 = fixture.command_26;
    activations = fixture.activation_commands;
    const bool needs_rearm=panel.mode2_rearm_pending;
    control_before=fixture.control_activations;
    fixture.draw_recording = true;
    fixture.recording_wave = 0x7Fu;
    frame.token++;
    frame.kind = COMP_RUNTIME_FRAME_RECORDING_WAVE;
    frame.recording = DENZIC_AUDIO_RECORDING_STATE_RECORDING;
    REQUIRE(comp_screen_presenter_wba_submit(&presenter, &frame, fixture.now) ==
            COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(drive(&presenter, &panel, &fixture));
    REQUIRE(fixture.command_26 - c26 == 4u); /* old+post-old for wave and entering microphone */
    REQUIRE(fixture.command_24 - c24 == 4u); /* current + post for both runs */
    REQUIRE(fixture.activation_commands - activations == 1u);
    REQUIRE(presenter.stats.recording_started == 1u);
    REQUIRE(fixture.control_activations-control_before==(needs_rearm?2u:1u));

    REQUIRE(both_ram_planes_match(&presenter,&fixture));
    mic_current=fixture.microphone_writes[0];mic_old=fixture.microphone_writes[1];

    /* An active wave update leaves the microphone byte unchanged.  Only one
     * old/current/post run is sent and it still has exactly one activation. */
    c24 = fixture.command_24;
    c26 = fixture.command_26;
    activations = fixture.activation_commands;
    fixture.recording_wave = 0x3Fu;
    frame.token++;
    REQUIRE(comp_screen_presenter_wba_submit(&presenter, &frame, fixture.now) ==
            COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(drive(&presenter, &panel, &fixture));
    REQUIRE(fixture.command_26 - c26 == 2u); /* old+post-old for one changed run */
    REQUIRE(fixture.command_24 - c24 == 2u);
    REQUIRE(fixture.activation_commands - activations == 1u);

    REQUIRE(both_ram_planes_match(&presenter,&fixture));
    REQUIRE(fixture.microphone_writes[0]==mic_current && fixture.microphone_writes[1]==mic_old);

    /* No recording pixel changes here.  Two ordinary dirty points produce a
     * bounding rectangle that crosses the recording window.  Recording state
     * still routes through the splitter: two ordinary rectangles rebased in
     * both RAM planes, one activation, and no static microphone rewrite. */
    c24 = fixture.command_24;
    c26 = fixture.command_26;
    activations = fixture.activation_commands;
    fixture.cross_recording_bounds = true;
    frame.token++;
    frame.kind = COMP_RUNTIME_FRAME_STATUS;
    REQUIRE(comp_screen_presenter_wba_submit(&presenter, &frame, fixture.now) ==
            COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(drive(&presenter, &panel, &fixture));
    REQUIRE(fixture.command_26 - c26 == 2u); /* both ordinary rectangles rebased in OLD */
    REQUIRE(fixture.command_24 - c24 == 4u); /* current+post for two ordinary rectangles */
    REQUIRE(fixture.activation_commands - activations == 1u);

    REQUIRE(both_ram_planes_match(&presenter,&fixture));
    REQUIRE(fixture.microphone_writes[0]==mic_current && fixture.microphone_writes[1]==mic_old);

    /* Exit clears both recording runs through the same dual-plane path. */
    c24 = fixture.command_24;
    c26 = fixture.command_26;
    activations = fixture.activation_commands;
    fixture.draw_recording = false;
    frame.token++;
    frame.kind = COMP_RUNTIME_FRAME_STATUS;
    frame.recording = DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY;
    REQUIRE(comp_screen_presenter_wba_submit(&presenter, &frame, fixture.now) ==
            COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    REQUIRE(drive(&presenter, &panel, &fixture));
    REQUIRE(fixture.command_26 - c26 == 4u); /* old+post-old for both exiting runs */
    REQUIRE(fixture.command_24 - c24 == 4u);
    REQUIRE(fixture.activation_commands - activations == 1u);
    REQUIRE(presenter.stats.recording_started == 4u);
    REQUIRE(!presenter.committed_recording_active);
    REQUIRE(both_ram_planes_match(&presenter,&fixture));
    REQUIRE(fixture.microphone_writes[0]>mic_current && fixture.microphone_writes[1]>mic_old);
    return 0;
}
int main(int argc,char **argv)
{
    struct {const char *name;int (*run)(void);} groups[]={
        {"presenter_journey",test_presenter_journey},
        {"unready_panel_fails_closed",test_unready_panel_fails_closed},
        {"family_and_menu_boundaries",test_family_and_menu_boundaries},
        {"recording_enter_active_exit_exact_delta",test_recording_enter_active_and_exit_use_exact_delta}
    };
    unsigned ran=0u,failed=0u;
    if(argc>2)return 2;
    for(unsigned i=0u;i<sizeof(groups)/sizeof(groups[0]);++i) {
        if(argc==2 && strcmp(argv[1],groups[i].name))continue;
        const int result=groups[i].run();++ran;if(result)++failed;
        printf("%s: GROUP|%s|%s\n",result?"FAIL":"PASS",groups[i].name,result?"FAIL":"PASS");
    }
    if(!ran)return 2;if(failed)return 1;
    puts("PASS: WBA presenter immutable snapshots, accepted mapping, visible baseline, "
         "bounded completion, both RAM planes, recording exact-delta routing, "
         "refresh policy and rollback; physical acceptance NOT_RUN");
    return 0;
}
