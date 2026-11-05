#include "companion_runtime.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do { if (!(x)) { printf("FAIL %d: %s\n", __LINE__, #x); return 1; } } while (0)
typedef struct {
    unsigned starts, stops, menu_calls;
    uint32_t token;
    comp_screen_menu_action_t last_menu_action;
    uint8_t last_menu_item;
    uint32_t menu_token;
    comp_runtime_menu_dispatch_t menu_dispatch;
    bool ready, accept, menu_accept, amp, polluted;
    comp_speaker_t *speaker;
    comp_runtime_t *inline_runtime;
    uint32_t inline_started_ms;
    bool inline_report_accepted;
} io_t;
static bool amp(void *c, bool enable) { ((io_t *)c)->amp = enable; return true; }
static bool tx(void *c, const int16_t *data, size_t n) { (void)c; (void)data; return n == 64u; }
static void power(void *c, bool active) { (void)c; (void)active; }
static bool ready(void *c) { return ((io_t *)c)->ready; }
static bool prepare(void *c, uint32_t token)
{
    io_t *io=c;
    io->ready=false; io->token=token;
    return io->accept;
}
static bool record(void *c, bool start, uint32_t token)
{
    io_t *io = c;
    if (start) { ++io->starts; io->polluted = io->amp || comp_speaker_active(io->speaker); }
    else ++io->stops;
    io->token = token;
    if (start && io->accept && io->inline_runtime)
        io->inline_report_accepted = comp_runtime_recording_update(
            io->inline_runtime, token, DENZIC_AUDIO_RECORDING_STATE_RECORDING,
            true, io->inline_started_ms);
    return io->accept;
}
static bool menu_action(void *c, const comp_screen_menu_result_t *result,
                        const comp_screen_menu_t *menu)
{
    io_t *io = c;
    (void)menu;
    ++io->menu_calls;
    io->last_menu_action = result->action;
    io->last_menu_item = result->browser_item;
    return io->menu_accept;
}
static comp_runtime_menu_dispatch_t menu_begin(void *c,const comp_screen_menu_result_t *result,
    const comp_screen_menu_t *menu,uint32_t token)
{
    io_t *io=c;
    (void)menu_action(c,result,menu);
    io->menu_token=token;
    return io->menu_dispatch;
}
static void setup_at(comp_runtime_t *r, comp_speaker_t *s, io_t *io,
                     uint32_t now)
{
    comp_speaker_config_t sc = {amp, tx, power, io};
    comp_runtime_config_t rc = {s, io, ready, record, menu_action, NULL, NULL, NULL};
    memset(io, 0, sizeof(*io));
    io->ready = io->accept = io->menu_accept = true;
    io->speaker = s;
    comp_speaker_init(s, &sc); comp_runtime_init(r, &rc, now);
}
static void setup(comp_runtime_t *r, comp_speaker_t *s, io_t *io)
{
    setup_at(r, s, io, 0u);
}
static void tick(comp_runtime_t *r, comp_speaker_t *s, uint32_t now)
{
    comp_runtime_service(r, now);
    if (s->tx_pending) comp_speaker_tx_complete(s, true);
}
static void touch(comp_runtime_t *r, bool down, uint16_t x, uint16_t y, uint32_t now)
{
    comp_ft6336_touch_sample_t sample = {(uint8_t)(down ? 1 : 0),
        down ? COMP_FT6336_TOUCH_EVENT_CONTACT : COMP_FT6336_TOUCH_EVENT_UP, 0, x, y};
    comp_runtime_touch(r, &sample, now, true, now);
}
static void tap(comp_runtime_t *r, uint16_t x, uint16_t y, uint32_t now)
{
    touch(r, true, x, y, now); touch(r, true, x, y, now+20);
    touch(r, false, x, y, now+60); touch(r, false, x, y, now+80);
}
static bool commit_current(comp_runtime_t *r, uint32_t now)
{
    comp_runtime_frame_t frame;
    return comp_runtime_take_frame(r, now, &frame) &&
        comp_runtime_complete_frame(r, frame.token, true, now + 1u);
}
static int record_journey(void)
{
    comp_runtime_t r; comp_speaker_t s; io_t io;
    setup(&r,&s,&io);
    tap(&r,20,175,10); tap(&r,20,175,140);
    CHECK(r.start_pending && io.starts == 0 && r.affect.taps == 0);
    for (uint32_t n=230; n<1500 && !io.starts; n++) tick(&r,&s,n);
    CHECK(io.starts == 1 && !io.polluted && r.command_pending);
    CHECK(comp_runtime_recording_update(&r,io.token,DENZIC_AUDIO_RECORDING_STATE_RECORDING,true,1500));
    CHECK(!comp_runtime_recording_update(&r,io.token+1,DENZIC_AUDIO_RECORDING_STATE_IDLE,false,1501));
    comp_runtime_set_connected(&r,true,1510);
    CHECK(!comp_speaker_active(&s));
    tap(&r,100,100,1600); tap(&r,100,100,1730);
    CHECK(io.stops == 1 && r.capture_active);
    CHECK(!comp_runtime_recording_update(&r,io.token,DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY,true,1900));
    CHECK(comp_runtime_recording_update(&r,io.token,DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY,false,1950));
    for (uint32_t n=1950;n<2300;n++) tick(&r,&s,n);
    CHECK(r.audio.stats.played >= 2u);
    printf("PASS recording: corner start, acoustic gate, async stop, stale token, no capture cue\n");
    return 0;
}
static int cancellation_and_unavailable(void)
{
    comp_runtime_t r; comp_speaker_t s; io_t io;
    setup(&r,&s,&io);
    CHECK(comp_runtime_record(&r,true,0) == COMP_RUNTIME_OK);
    tick(&r,&s,1);
    CHECK(comp_runtime_record(&r,false,2) == COMP_RUNTIME_OK);
    for (uint32_t n=3;n<400;n++) tick(&r,&s,n);
    CHECK(io.starts == 0 && !r.start_pending);
    io.ready = false;
    CHECK(comp_runtime_record(&r,true,1000) == COMP_RUNTIME_UNAVAILABLE);
    CHECK(io.starts == 0);
    io.ready = true; comp_runtime_set_quiet(&r,true);
    for (uint32_t n=1001;n<1300;n++) tick(&r,&s,n);
    CHECK(comp_runtime_record(&r,true,1500) == COMP_RUNTIME_OK);
    tick(&r,&s,1501);
    CHECK(io.starts == 1 && !io.polluted);
    printf("PASS cancellation/unavailable: no late start, quiet gate, no fake backend\n");
    return 0;
}
static int display_and_input(void)
{
    comp_runtime_t r; comp_speaker_t s; io_t io; comp_runtime_frame_t f;
    setup(&r,&s,&io);
    CHECK(comp_runtime_take_frame(&r,0,&f));
    CHECK(!comp_runtime_take_frame(&r,1,&f));
    CHECK(comp_runtime_complete_frame(&r,f.token,false,10));
    CHECK(!comp_runtime_take_frame(&r,100,&f));
    CHECK(comp_runtime_take_frame(&r,490,&f));
    CHECK(comp_runtime_complete_frame(&r,f.token,true,500));
    CHECK(!comp_runtime_complete_frame(&r,f.token,true,501));
    CHECK(comp_runtime_take_frame(&r,600,&f) && f.kind == COMP_RUNTIME_FRAME_LIFE);
    { comp_epaper_motion_phase_t phase=f.motion.phase;
      CHECK(comp_runtime_complete_frame(&r,f.token,false,620));
      CHECK(comp_runtime_take_frame(&r,1600,&f)); CHECK(f.motion.phase==phase);
      CHECK(comp_runtime_complete_frame(&r,f.token,true,1610)); }
    comp_runtime_motion(&r,COMP_MOTION_SHAKE,1,1,2000);
    { uint32_t rev=r.revision; comp_runtime_motion(&r,COMP_MOTION_SHAKE,1,1,2100); CHECK(r.revision==rev); }
    CHECK(io.starts==0);
    touch(&r,true,100,100,2200);
    touch(&r,true,100,100,2220);
    comp_runtime_touch(&r,NULL,2221,false,2221);
    comp_runtime_service(&r,5000);
    CHECK(!r.hold.active && !r.gesture.active && r.affect.taps==0);
    printf("PASS display/input: commit-only progression, retry, duplicate sequence, invalid contact cancellation\n");
    return 0;
}
static int menu_and_sleep(void)
{
    comp_runtime_t r; comp_speaker_t s; io_t io; comp_runtime_frame_t f;
    setup(&r,&s,&io);
    CHECK(comp_runtime_take_frame(&r,0,&f)); CHECK(comp_runtime_complete_frame(&r,f.token,true,1));
    touch(&r,true,100,100,100); touch(&r,true,100,100,120);
    for (uint32_t n=1600;n<=3100;n+=500) {
        touch(&r,true,100,100,n);
        CHECK(comp_runtime_take_frame(&r,n,&f) && f.kind == COMP_RUNTIME_FRAME_HOLD);
        CHECK(r.surface==COMP_SCREEN_SURFACE_HOME);
        CHECK(comp_runtime_complete_frame(&r,f.token,true,n+20));
    }
    CHECK(r.surface==COMP_SCREEN_SURFACE_MENU);
    touch(&r,false,100,100,3150); touch(&r,false,100,100,3170);
    r.menu.browser.auto_sleep_minutes=1;
    comp_runtime_service(&r,64000);
    CHECK(r.surface==COMP_SCREEN_SURFACE_LOW_POWER);
    comp_runtime_motion(&r,COMP_MOTION_PICKUP,1,10,65000);
    CHECK(r.surface==COMP_SCREEN_SURFACE_HOME && io.starts==0);
    comp_runtime_local_hour(&r,true,23); CHECK(r.audio.quiet);
    comp_runtime_local_hour(&r,false,23); CHECK(!r.audio.quiet);
    printf("PASS menu/sleep: four visible hold stages, idle sleep, pickup wake, truthful local clock\n");
    return 0;
}
static int menu_routes_and_rollback(void)
{
    comp_runtime_t r; comp_speaker_t s; io_t io;
    uint8_t before;
    uint32_t audio_submitted;
    setup(&r,&s,&io);
    r.surface = COMP_SCREEN_SURFACE_MENU;
    CHECK(comp_screen_menu_navigate_to(&r.menu,
        COMP_SCREEN_MENU_VIEW_BROWSER_INTERACTION));
    ++r.revision;
    CHECK(commit_current(&r,1u));
    before = r.menu.browser.interaction_level;
    io.menu_accept = false;
    audio_submitted = r.audio.stats.submitted;
    tap(&r,100,135,100);
    CHECK(io.menu_calls==1 &&
        io.last_menu_action==COMP_SCREEN_MENU_ACTION_BROWSER_SETTING_CHANGED);
    CHECK(r.menu.browser.interaction_level==before &&
        r.last_result==COMP_RUNTIME_UNAVAILABLE);
    CHECK(r.audio.stats.submitted==audio_submitted+1u); /* error only */

    io.menu_accept = true;
    CHECK(commit_current(&r,500u));
    tap(&r,100,135,1000);
    CHECK(io.menu_calls==2 && r.menu.browser.interaction_level!=before &&
        r.last_result==COMP_RUNTIME_OK);
    CHECK(r.audio.stats.submitted==audio_submitted+2u); /* touch confirm */

    CHECK(comp_screen_menu_navigate_to(&r.menu,
        COMP_SCREEN_MENU_VIEW_BROWSER_HOME));
    ++r.revision;
    CHECK(commit_current(&r,1500u));
    tap(&r,100,55,2000);
    CHECK(r.menu.view==COMP_SCREEN_MENU_VIEW_BROWSER_VOICE && io.menu_calls==2);

    CHECK(comp_screen_menu_navigate_to(&r.menu,
        COMP_SCREEN_MENU_VIEW_BROWSER_CLEAR_RECORDINGS));
    ++r.revision;
    CHECK(commit_current(&r,2500u));
    io.menu_accept = false;
    tap(&r,100,95,3000);
    CHECK(io.menu_calls==3 &&
        io.last_menu_action==COMP_SCREEN_MENU_ACTION_BROWSER_CLEAR_RECORDINGS &&
        r.menu.view==COMP_SCREEN_MENU_VIEW_BROWSER_CLEAR_RECORDINGS &&
        r.last_result==COMP_RUNTIME_UNAVAILABLE);
    printf("PASS menu routes: real tap navigation, rejected setting rollback, recovery, unsupported action failure\n");
    return 0;
}
static int menu_record_truth_and_pending_cancel(void)
{
    comp_runtime_t r; comp_speaker_t s; io_t io;
    setup(&r,&s,&io);
    r.surface = COMP_SCREEN_SURFACE_MENU;
    r.menu.view = COMP_SCREEN_MENU_VIEW_RECORD;
    ++r.revision;
    CHECK(commit_current(&r,1u));
    io.ready = false;
    tap(&r,100,110,100);
    CHECK(!r.start_pending &&
        (r.menu.flags & COMP_SCREEN_MENU_FLAG_RECORDING)==0u &&
        r.last_result==COMP_RUNTIME_UNAVAILABLE);

    io.ready = true;
    CHECK(commit_current(&r,500u));
    tap(&r,100,110,1000);
    CHECK(r.start_pending &&
        (r.menu.flags & COMP_SCREEN_MENU_FLAG_RECORDING)==0u);
    CHECK(r.audio.stats.submitted==2u); /* first error, then start cue; no tap cue */
    CHECK(comp_runtime_record(&r,false,1100)==COMP_RUNTIME_OK);
    CHECK(!r.start_pending && io.starts==0);

    comp_runtime_set_quiet(&r,true);
    CHECK(comp_runtime_record(&r,true,2000)==COMP_RUNTIME_OK);
    tick(&r,&s,2001);
    CHECK(io.starts==1 && r.command_pending && !r.capture_active);
    r.surface = COMP_SCREEN_SURFACE_HOME;
    ++r.revision;
    CHECK(commit_current(&r,2050u));
    tap(&r,20,175,2100); tap(&r,20,175,2230);
    CHECK(io.stops==1 && r.stop_pending);
    CHECK(comp_runtime_record(&r,false,2300)==COMP_RUNTIME_OK && io.stops==1);
    printf("PASS record control: menu truth, gate cancellation, pending-backend double-tap stop, idempotent stop\n");
    return 0;
}
static int menu_input_requires_visible_commit(void)
{
    comp_runtime_t r; comp_speaker_t s; io_t io; comp_runtime_frame_t frame;
    comp_screen_menu_view_t visible_view;
    unsigned menu_calls;
    setup(&r,&s,&io);
    r.surface=COMP_SCREEN_SURFACE_MENU;
    CHECK(comp_screen_menu_navigate_to(&r.menu,COMP_SCREEN_MENU_VIEW_BROWSER_HOME));
    ++r.revision;
    CHECK(commit_current(&r,1u));
    CHECK(r.visible_menu_valid && r.visible_menu_view==r.menu.view);

    /* A contact beginning while the panel owns a frame cannot be replayed
     * against the page after that frame completes. */
    visible_view=r.menu.view;
    comp_runtime_status(&r,0x00008001u);
    CHECK(comp_runtime_take_frame(&r,100u,&frame));
    tap(&r,100u,55u,110u);
    CHECK(r.menu.view==visible_view);
    CHECK(comp_runtime_complete_frame(&r,frame.token,true,200u));

    /* Even a refresh of the same logical menu page can partially update an
     * e-paper panel before reporting failure.  Keep coordinates disabled
     * until an exact retry is visibly committed. */
    comp_runtime_status(&r,0x00008003u);
    CHECK(comp_runtime_take_frame(&r,210u,&frame));
    CHECK(comp_runtime_complete_frame(&r,frame.token,false,220u));
    CHECK(!r.visible_menu_valid);
    tap(&r,100u,55u,230u);
    CHECK(r.menu.view==visible_view);
    CHECK(comp_runtime_take_frame(&r,700u,&frame));
    CHECK(comp_runtime_complete_frame(&r,frame.token,true,701u));
    CHECK(r.visible_menu_valid && r.visible_menu_view==visible_view);

    /* A contact that starts on one committed frame and crosses another
     * successful commit is also discarded on release. */
    touch(&r,true,100u,55u,800u);
    touch(&r,true,100u,55u,820u);
    comp_runtime_status(&r,0x00008002u);
    CHECK(comp_runtime_take_frame(&r,830u,&frame));
    CHECK(comp_runtime_complete_frame(&r,frame.token,true,840u));
    touch(&r,false,100u,55u,860u);
    touch(&r,false,100u,55u,880u);
    CHECK(r.menu.view==visible_view);

    /* Navigation may mutate the model immediately, but coordinates for the
     * new page remain inert until that exact menu revision is visible. */
    tap(&r,100u,55u,1400u);
    CHECK(r.menu.view==COMP_SCREEN_MENU_VIEW_BROWSER_VOICE);
    menu_calls=io.menu_calls;
    tap(&r,100u,135u,1900u);
    CHECK(io.menu_calls==menu_calls);
    CHECK(commit_current(&r,2400u));
    CHECK(r.visible_menu_valid && r.visible_menu_revision==r.menu.revision &&
        r.visible_menu_view==r.menu.view && !r.frame_outstanding);
    { comp_screen_menu_t probe=r.menu;
      comp_screen_menu_result_t result=comp_screen_menu_tap(&probe,100u,135u);
      CHECK(result.action==COMP_SCREEN_MENU_ACTION_BROWSER_SETTING_CHANGED); }
    touch(&r,true,100u,135u,3100u);
    CHECK(r.input_contact_eligible);
    touch(&r,true,100u,135u,3120u);
    touch(&r,false,100u,135u,3160u);
    touch(&r,false,100u,135u,3180u);
    CHECK(io.menu_calls==menu_calls+1u);
    printf("PASS menu input: pending, failed/partial and cross-commit frames reject stale coordinates\n");
    return 0;
}
static int touch_sequence_and_blink_competition(void)
{
    comp_runtime_t r; comp_speaker_t s; io_t io; comp_runtime_frame_t f;
    comp_ft6336_touch_sample_t sample = {1u,COMP_FT6336_TOUCH_EVENT_CONTACT,0u,100u,100u};
    uint32_t due;
    setup(&r,&s,&io);
    comp_runtime_touch(&r,&sample,77u,true,100u);
    CHECK(r.touch_contact && (r.menu.flags & COMP_SCREEN_MENU_FLAG_TOUCH_OK));
    comp_runtime_touch(&r,NULL,77u,false,101u);
    CHECK(r.touch_contact && r.gesture.active);
    comp_runtime_touch(&r,NULL,78u,false,102u);
    CHECK(!r.touch_contact && !r.gesture.active &&
        (r.menu.flags & COMP_SCREEN_MENU_FLAG_TOUCH_OK)==0u);
    comp_runtime_touch(&r,&sample,78u,true,103u);
    CHECK(!r.touch_contact); /* duplicate invalid acquisition cannot revive */
    comp_runtime_touch(&r,&sample,79u,true,104u);
    CHECK(r.touch_contact && (r.menu.flags & COMP_SCREEN_MENU_FLAG_TOUCH_OK));
    sample.touch_count=0u; sample.event=COMP_FT6336_TOUCH_EVENT_UP;
    comp_runtime_touch(&r,&sample,80u,true,120u);

    CHECK(comp_runtime_take_frame(&r,130u,&f));
    CHECK(comp_runtime_complete_frame(&r,f.token,true,140u));
    due = r.blink.next_due_ms;
    CHECK(comp_runtime_take_frame(&r,due,&f) &&
        f.kind==COMP_RUNTIME_FRAME_BLINK && f.blink_closed);
    comp_runtime_motion(&r,COMP_MOTION_SHAKE,1u,1u,due+1u);
    CHECK(r.reaction_pending);
    CHECK(comp_runtime_complete_frame(&r,f.token,false,due+2u));
    CHECK(!comp_runtime_take_frame(&r,due+100u,&f));
    CHECK(comp_runtime_take_frame(&r,due+482u,&f) &&
        f.kind==COMP_RUNTIME_FRAME_REACTION);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,due+483u));
    CHECK(comp_runtime_take_frame(&r,due+484u,&f) &&
        f.kind==COMP_RUNTIME_FRAME_BLINK && f.blink_closed);
    printf("PASS input/display race: invalid-sequence dedup and failed blink preserves newer reaction then retries\n");
    return 0;
}
static int timers_status_and_recording_life(void)
{
    const uint32_t boot = 0xFFFFFF00u;
    comp_runtime_t r; comp_speaker_t s; io_t io; comp_runtime_frame_t f;
    uint32_t revision;
    setup_at(&r,&s,&io,boot);
    CHECK(comp_runtime_take_frame(&r,boot,&f));
    CHECK((f.status_packed & COMP_SCREEN_STATUS_REQUIRE_MEASURED_BATTERY)!=0u);
    CHECK(comp_runtime_complete_frame(&r,f.token,false,boot+8u));
    CHECK(!comp_runtime_take_frame(&r,100u,&f));
    CHECK(comp_runtime_take_frame(&r,472u,&f));
    CHECK(comp_runtime_complete_frame(&r,f.token,true,473u));

    comp_runtime_set_connected(&r,true,500u);
    comp_runtime_status(&r,0x6402A500u);
    CHECK(comp_runtime_take_frame(&r,501u,&f));
    CHECK((f.status_packed & (1u<<16))!=0u &&
        (f.status_packed & COMP_SCREEN_STATUS_REQUIRE_MEASURED_BATTERY)!=0u &&
        (f.status_packed>>24)==100u);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,502u));

    comp_runtime_set_quiet(&r,true);
    CHECK(comp_runtime_record(&r,true,600u)==COMP_RUNTIME_OK);
    tick(&r,&s,601u);
    CHECK(io.starts==1);
    CHECK(comp_runtime_recording_update(&r,io.token,
        DENZIC_AUDIO_RECORDING_STATE_RECORDING,true,0xFFFFFF80u));
    CHECK(r.recording_display_second==0u);
    comp_runtime_service(&r,0x00000367u); /* 999 ms across wrap */
    CHECK(r.recording_display_second==0u);
    comp_runtime_service(&r,0x00000368u);
    CHECK(r.recording_display_second==1u);

    r.record_limit_seconds=60u; /* accepted limit of this simulated capture */
    r.menu.browser.recording_limit_minutes=15u; /* later edit cannot extend it */
    comp_runtime_service(&r,0x0000E9E0u); /* exactly 60000 ms elapsed */
    CHECK(io.stops==1 && r.stop_pending);
    revision=r.revision;
    comp_runtime_service(&r,0x0000E9E1u);
    CHECK(io.stops==1 && r.revision==revision);

    /* Recording remains an overlay/state, not a second owner of the life
     * scheduler. Once its status frame commits, ordinary life still advances
     * without changing the recording command count. */
    CHECK(comp_runtime_take_frame(&r,0x0000EA00u,&f));
    CHECK(comp_runtime_complete_frame(&r,f.token,true,0x0000EA01u));
    r.stop_pending=false; /* isolate scheduler behavior after accepted stop */
    r.menu.browser.natural_blink=false;
    r.life.next_request_ms=0x0000EA02u;
    CHECK(comp_runtime_take_frame(&r,0x0000EA02u,&f) &&
        f.kind==COMP_RUNTIME_FRAME_LIFE);
    CHECK(io.starts==1 && io.stops==1);
    printf("PASS timers/status: wrap-safe boot/retry/countdown, measured status, one auto-stop, independent life\n");
    return 0;
}
static int storage_before_sound(void)
{
    comp_runtime_t r; comp_speaker_t s; io_t io;
    setup(&r,&s,&io); r.config.recording_prepare=prepare;
    CHECK(comp_runtime_record(&r,true,100)==COMP_RUNTIME_OK);
    CHECK(r.prepare_pending && r.command_pending && !r.start_pending);
    for (uint32_t n=101;n<800;n++) tick(&r,&s,n);
    CHECK(!comp_speaker_active(&s) && io.starts==0);
    io.ready=true;
    for (uint32_t n=800;n<1400;n++) tick(&r,&s,n);
    CHECK(io.starts==1 && !io.polluted && io.token==r.record_token);
    setup(&r,&s,&io); r.config.recording_prepare=prepare;
    CHECK(comp_runtime_record(&r,true,100)==COMP_RUNTIME_OK);
    CHECK(comp_runtime_record(&r,false,200)==COMP_RUNTIME_OK && io.stops==1);
    io.ready=true;
    for (uint32_t n=201;n<800;n++) tick(&r,&s,n);
    CHECK(io.starts==0 && !r.start_pending && !r.prepare_pending);
    CHECK(comp_runtime_record(&r,true,1000)==COMP_RUNTIME_OK);
    tick(&r,&s,121001);
    CHECK(io.stops==2 && io.starts==0 && r.last_result==COMP_RUNTIME_BACKEND_FAILED);
    CHECK(comp_runtime_recording_update(&r,r.record_token,DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY,false,121010));
    CHECK(comp_runtime_record(&r,true,122000)==COMP_RUNTIME_OK && r.prepare_pending);
    printf("PASS prepare: storage before sound, cancellation and timeout never start microphone\n");
    return 0;
}
static int preparation_clock_order_and_stop_cause(void)
{
    const uint32_t starts[]={100u,0u,UINT32_MAX-3u};
    for(size_t i=0;i<sizeof(starts)/sizeof(starts[0]);++i) {
        comp_runtime_t r;comp_speaker_t s;io_t io;uint32_t start=starts[i];
        setup_at(&r,&s,&io,start-2u);r.config.recording_prepare=prepare;
        CHECK(comp_runtime_record(&r,true,start)==COMP_RUNTIME_OK);
        /* A callback may receive a newer tick than its caller's cached tick.
         * Neither order nor natural uint32 wrap is a two-minute timeout. */
        comp_runtime_service(&r,start-1u);
        CHECK(r.prepare_pending && !io.starts && !io.stops && !r.record_stop_reason);
        comp_runtime_service(&r,start+120000u);
        CHECK(r.prepare_pending && !io.stops);
        comp_runtime_service(&r,start+120001u);
        CHECK(!r.prepare_pending && io.stops==1u && !io.starts);
        CHECK(r.record_stop_reason==2u && r.last_result==COMP_RUNTIME_BACKEND_FAILED);
        /* Later UI outcomes cannot lose this capture's actual stop origin. */
        r.last_result=COMP_RUNTIME_OK;
        comp_runtime_service(&r,start+120002u);
        CHECK(r.record_stop_reason==2u && io.stops==1u);
    }
    puts("PASS_RECORDING_START_CLOCK: cached older tick and wrap cannot cancel preparation; real120001ms timeout still cancels once with sticky cause, never starts microphone");
    return 0;
}
static bool entropy(void *c,uint32_t *value)
{ io_t *io=c; if (!io->ready) return false; *value=++io->menu_calls*0x12345u; return true; }
static int recording_wave_sequence_contract(void)
{
    comp_runtime_t r; comp_speaker_t s; io_t io; comp_runtime_frame_t f, old;
    uint32_t now=10u;
    setup(&r,&s,&io); r.menu.browser.natural_blink=false;
    CHECK(comp_runtime_take_frame(&r,0,&f));
    CHECK(comp_runtime_complete_frame(&r,f.token,true,1));

    /* A frame already owned by the panel can finish after a stop/new-start.
     * Its old session identity must not consume the new session's frame 00. */
    r.record_token=40u;
    CHECK(comp_runtime_recording_update(&r,40u,DENZIC_AUDIO_RECORDING_STATE_RECORDING,true,2u));
    CHECK(comp_runtime_take_frame(&r,3u,&old) && old.recording_wave_index==0u);
    CHECK(comp_runtime_recording_update(&r,40u,DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY,false,4u));
    r.record_token=41u;
    CHECK(comp_runtime_recording_update(&r,41u,DENZIC_AUDIO_RECORDING_STATE_RECORDING,true,5u));
    CHECK(comp_runtime_complete_frame(&r,old.token,true,6u));
    CHECK(!r.recording_wave_started && r.recording_wave_due && r.recording_wave_index==0u);
    r.life.next_request_ms=100000u;

    CHECK(comp_runtime_take_frame(&r,now++,&f) && f.recording_wave_index==0u);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,now++));
    CHECK(comp_runtime_take_frame(&r,now++,&f) && f.recording_wave_index==1u);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,now++));
    CHECK(comp_runtime_take_frame(&r,now++,&f) && f.recording_wave_index==2u);
    CHECK(comp_runtime_complete_frame(&r,f.token,false,now++));
    CHECK(r.recording_wave_index==1u);
    now+=480u;
    CHECK(comp_runtime_take_frame(&r,now++,&f) && f.recording_wave_index==2u);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,now++));
    for (uint8_t expected=3u; expected<=63u; ++expected) {
        CHECK(comp_runtime_take_frame(&r,now++,&f));
        CHECK(f.kind==COMP_RUNTIME_FRAME_RECORDING_WAVE &&
              f.recording_wave_index==expected);
        CHECK(comp_runtime_complete_frame(&r,f.token,true,now++));
    }
    CHECK(comp_runtime_take_frame(&r,now++,&f) && f.recording_wave_index==4u);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,now++));

    CHECK(comp_runtime_recording_update(&r,41u,DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY,false,now++));
    r.record_token=42u;
    CHECK(comp_runtime_recording_update(&r,42u,DENZIC_AUDIO_RECORDING_STATE_RECORDING,true,now++));
    CHECK(comp_runtime_take_frame(&r,now++,&f) && f.recording_wave_index==0u);
    puts("PASS recording wave sequence: 00 entry, 01/02/03, 04..63 loop, retry and session isolation");
    return 0;
}
static int independent_tracks_and_family(void)
{
    comp_runtime_t r; comp_speaker_t s; io_t io; comp_runtime_frame_t f;
    uint32_t life_due,life_count; unsigned changes=0;
    setup(&r,&s,&io); r.config.random_u32=entropy;
    r.menu.browser.natural_blink=false; r.menu.browser.auto_sleep_minutes=0;
    for (uint32_t now=0;now<120000u;now+=240u) {
        comp_runtime_service(&r,now);
        if (comp_runtime_take_frame(&r,now,&f)) {
            if (f.family_clean) { ++changes; CHECK(f.kind==COMP_RUNTIME_FRAME_LIFE && f.family!=COMP_BROWSER_FAMILY_SLEEPY); }
            CHECK(comp_runtime_complete_frame(&r,f.token,true,now+200u));
        }
    }
    CHECK(changes>=3 && changes==r.autonomous_family_changes && io.menu_calls==changes);
    setup(&r,&s,&io); r.menu.browser.natural_blink=false;
    CHECK(comp_runtime_take_frame(&r,0,&f)); CHECK(comp_runtime_complete_frame(&r,f.token,true,1));
    r.record_token=5;
    CHECK(comp_runtime_recording_update(&r,5,DENZIC_AUDIO_RECORDING_STATE_RECORDING,true,10));
    CHECK(comp_runtime_take_frame(&r,11,&f) && f.kind==COMP_RUNTIME_FRAME_RECORDING_WAVE && f.recording_wave_index==0);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,12));
    r.life.next_request_ms=5000; life_due=r.life.next_request_ms; life_count=r.life.completed_requests;
    CHECK(comp_runtime_take_frame(&r,20,&f) && f.kind==COMP_RUNTIME_FRAME_RECORDING_WAVE && f.recording_wave_index==1);
    CHECK(comp_runtime_complete_frame(&r,f.token,false,21) && r.recording_wave_index==0);
    CHECK(comp_runtime_take_frame(&r,501,&f) && f.kind==COMP_RUNTIME_FRAME_RECORDING_WAVE && f.recording_wave_index==1);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,502) && r.recording_wave_index==1);
    CHECK(r.life.next_request_ms==life_due && r.life.completed_requests==life_count);
    CHECK(comp_runtime_take_frame(&r,503,&f) && f.recording_wave_index==2);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,504));
    r.config.random_u32=entropy;r.menu.browser.auto_sleep_minutes=0;
    for (uint32_t now=600u;now<120000u;now+=500u) {
        comp_runtime_service(&r,now);
        if (comp_runtime_take_frame(&r,now,&f)) {
            CHECK(!f.family_clean); /* No full-frame cleanup while recording. */
            CHECK(comp_runtime_complete_frame(&r,f.token,true,now+350u));
        }
    }
    printf("recording trace: changes=%lu wave=%u life=%lu action=%u phase=%u due=%lu now=120000\n",(unsigned long)r.autonomous_family_changes,r.recording_wave_index,(unsigned long)r.life.completed_requests,r.life.action,r.life.next_phase,(unsigned long)r.life.next_request_ms);
    CHECK(r.autonomous_family_changes>=3);
    CHECK(r.family_clean); /* Deferred cleanup survives recording. */
    CHECK(comp_runtime_recording_update(&r,5,DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY,false,120000u));
    changes=0;
    for(uint32_t now=120000u;now<130000u;now+=500u) {
        comp_runtime_service(&r,now);
        if(comp_runtime_take_frame(&r,now,&f)) {
            if(f.family_clean)++changes;
            CHECK(comp_runtime_complete_frame(&r,f.token,true,now+350u));
        }
    }
    CHECK(changes>=1);
    printf("PASS independent tracks: entropy family boundary, no sleepy, wave commit/retry never advances life\n");
    return 0;
}
static int wave_fairness_after_late_display(void)
{
    comp_runtime_t r;comp_speaker_t s;io_t io;comp_runtime_frame_t f;
    uint32_t deadline,count,blink_due;uint8_t wave;
    setup(&r,&s,&io);r.menu.browser.natural_blink=false;r.menu.browser.auto_sleep_minutes=0;
    CHECK(comp_runtime_take_frame(&r,0,&f));CHECK(comp_runtime_complete_frame(&r,f.token,true,1));
    r.record_token=7;
    CHECK(comp_runtime_recording_update(&r,7,DENZIC_AUDIO_RECORDING_STATE_RECORDING,true,10));
    CHECK(comp_runtime_take_frame(&r,11,&f)&&f.kind==COMP_RUNTIME_FRAME_RECORDING_WAVE);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,12));
    r.life.next_request_ms=20;
    CHECK(comp_runtime_take_frame(&r,20,&f)&&f.kind==COMP_RUNTIME_FRAME_LIFE);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,900));
    deadline=r.life.next_request_ms;count=r.life.completed_requests;blink_due=r.blink.next_due_ms;
    wave=r.recording_wave_index;
    /* Let the panel/foreground delay exceed even a 4-beat life dwell. A new
     * clock revision and overdue life must not erase the pure-wave turn. */
    comp_runtime_status(&r,0x8000u|(10u<<8u)|25u);
    CHECK(comp_runtime_take_frame(&r,3000,&f)&&f.kind==COMP_RUNTIME_FRAME_RECORDING_WAVE);
    CHECK(comp_runtime_complete_frame(&r,f.token,false,3400));
    CHECK(r.recording_wave_due&&r.recording_wave_index==wave);
    CHECK(comp_runtime_take_frame(&r,3880,&f)&&f.kind==COMP_RUNTIME_FRAME_RECORDING_WAVE);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,4300));
    CHECK(!r.recording_wave_due&&r.recording_wave_index==(uint8_t)(wave+1u));
    CHECK(r.life.next_request_ms==deadline&&r.life.completed_requests==count&&r.blink.next_due_ms==blink_due);
    CHECK(comp_runtime_take_frame(&r,4301,&f)&&f.kind==COMP_RUNTIME_FRAME_LIFE);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,4700));
    CHECK(comp_runtime_recording_update(&r,7,DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY,false,4701));
    CHECK(!r.recording_wave_due);
    puts("PASS wave fairness: bootstrap, delayed BUSY, pending clock, failed commit retry; life/blink deadlines unchanged");
    return 0;
}
static int blink_then_drag_and_reaction_cadence(void)
{
    comp_runtime_t r; comp_speaker_t s; io_t io; comp_runtime_frame_t f;
    uint32_t due;
    setup(&r,&s,&io);
    CHECK(comp_runtime_take_frame(&r,0,&f)); CHECK(comp_runtime_complete_frame(&r,f.token,true,1));
    due=r.blink.next_due_ms;
    CHECK(comp_runtime_take_frame(&r,due,&f) && f.kind==COMP_RUNTIME_FRAME_BLINK && f.blink_closed);
    /* Zero-latency host display: even a status/wave request in the same ms
     * cannot steal the scheduler's remaining closed interval. */
    CHECK(comp_runtime_complete_frame(&r,f.token,true,due));
    comp_runtime_status(&r,0x8000u | (9u<<8u) | 41u);
    CHECK(comp_runtime_take_frame(&r,due,&f) && f.kind==COMP_RUNTIME_FRAME_STATUS && f.blink_closed);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,due));
    r.capture_active=true;
    CHECK(comp_runtime_take_frame(&r,due,&f) && f.kind==COMP_RUNTIME_FRAME_RECORDING_WAVE && f.blink_closed);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,due));
    r.capture_active=false;
    touch(&r,true,15,180,due+201); touch(&r,true,120,180,due+221);
    CHECK(r.reaction_pending && r.gaze_x==120 && !r.hold.active);
    CHECK(comp_runtime_take_frame(&r,due+222,&f) && f.kind==COMP_RUNTIME_FRAME_BLINK && !f.blink_closed);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,due+422));
    CHECK(comp_runtime_take_frame(&r,due+423,&f) && f.kind==COMP_RUNTIME_FRAME_REACTION);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,due+623));
    r.menu.browser.interaction_level=COMP_SCREEN_MENU_INTERACTION_QUIET;
    r.menu.browser.natural_blink=false;
    touch(&r,false,120,180,due+630);
    r.reaction_pending=false; r.visible_revision=r.revision; r.life.next_request_ms=due+700;
    CHECK(comp_runtime_take_frame(&r,due+700,&f) && f.kind==COMP_RUNTIME_FRAME_LIFE);
    uint32_t visible_time=due+900;
    due=r.life.outstanding_due_ms+(uint32_t)r.life.dwell_commits*480u;
    CHECK(comp_runtime_complete_frame(&r,f.token,true,visible_time));
    CHECK(r.life.next_request_ms==due); /* setting never changes authored beat */
    printf("PASS eye/input: finish reopening before corner drag, full-area gaze, interaction setting preserves life clock\n");
    return 0;
}
static int causal_transition(void)
{
    comp_runtime_t r; comp_speaker_t s; io_t io; comp_runtime_frame_t f;
    uint32_t now=1000u; uint8_t prior_step; unsigned phases=0;
    setup(&r,&s,&io); r.menu.browser.natural_blink=false;
    for (unsigned i=0;i<20 && r.reaction_route_count<2;++i) {
        tap(&r,160,90,now); now+=1500;
    }
    CHECK(r.reaction_route_count>=2 && r.reaction_pending);
    CHECK(comp_runtime_take_frame(&r,now,&f) && f.kind==COMP_RUNTIME_FRAME_REACTION && f.reaction_transition);
    prior_step=f.reaction_step;
    CHECK(comp_runtime_complete_frame(&r,f.token,false,now+100));
    CHECK(r.reaction_step==prior_step);
    now+=580;
    while (r.reaction_pending && phases<50) {
        CHECK(comp_runtime_take_frame(&r,now,&f) && f.kind==COMP_RUNTIME_FRAME_REACTION && f.reaction_transition);
        CHECK(comp_runtime_complete_frame(&r,f.token,true,now+200));
        now+=680; ++phases;
    }
    CHECK(!r.reaction_pending && phases>=5 && phases%5==0);
    printf("PASS causal transition: authored edges finish all phases, failed display retries same phase\n");
    return 0;
}
static int reaction_in_flight_cooldown(void)
{
    comp_runtime_t r; comp_speaker_t s; io_t io; comp_runtime_frame_t f;
    uint32_t first_generation;
    setup(&r,&s,&io); r.menu.browser.natural_blink=false;
    tap(&r,150,100,100);
    CHECK(comp_runtime_take_frame(&r,190,&f) && f.kind==COMP_RUNTIME_FRAME_REACTION);
    first_generation=f.reaction_generation;
    comp_runtime_motion(&r,COMP_MOTION_SHAKE,1,1,250);
    CHECK(r.reaction_generation!=first_generation);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,300));
    CHECK(r.reaction_pending && r.reaction_input_after_ms>300);
    CHECK(comp_runtime_take_frame(&r,301,&f) && f.kind==COMP_RUNTIME_FRAME_STATUS);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,302));
    CHECK(!comp_runtime_take_frame(&r,303,&f));
    CHECK(comp_runtime_take_frame(&r,r.reaction_input_after_ms,&f) && f.kind==COMP_RUNTIME_FRAME_REACTION);
    printf("PASS reaction race: stale completion cannot bypass new-input cooldown or advance life early\n");
    return 0;
}
static int pet_sound_policy(void)
{
    comp_runtime_t r; comp_speaker_t s; io_t io;
    setup(&r,&s,&io);
    CHECK(s.pet_voice && s.volume_percent==25u);
    tap(&r,130,100,100);
    CHECK(r.audio.stats.submitted==1u);
    for(uint32_t n=200;n<700;++n)tick(&r,&s,n);
    tap(&r,130,100,750);
    CHECK(r.audio.stats.submitted==1u);
    tap(&r,130,100,1900);
    CHECK(r.audio.stats.submitted==2u);
    comp_runtime_set_quiet(&r,true);
    tap(&r,130,100,4000);
    CHECK(r.audio.stats.submitted==2u);
    comp_runtime_set_quiet(&r,false);
    comp_runtime_motion(&r,COMP_MOTION_PICKUP|COMP_MOTION_SHAKE,1,1,6000);
    comp_runtime_set_connected(&r,true,7000);
    CHECK(r.audio.stats.submitted==2u);
    puts("PASS pet sounds: opt-in voice, quiet/record guards, 1.5s touch cooldown, motion/reconnect silent");
    return 0;
}
static int menu_completion_truth(void)
{
    comp_runtime_t r;comp_speaker_t s;io_t io;comp_runtime_frame_t f;
    setup(&r,&s,&io);r.config.menu_action_begin=menu_begin;
    r.surface=COMP_SCREEN_SURFACE_MENU;
    CHECK(comp_screen_menu_navigate_to(&r.menu,COMP_SCREEN_MENU_VIEW_BROWSER_CLEAR_RECORDINGS));
    r.menu.browser.recording_count=3u;io.menu_dispatch=COMP_RUNTIME_MENU_PENDING;++r.revision;
    CHECK(commit_current(&r,1u));tap(&r,100,95,100u);
    CHECK(io.menu_calls==1u && r.menu_pending && io.menu_token==r.menu_token &&
        r.menu_feedback==COMP_RUNTIME_MENU_FEEDBACK_CLEARING && r.menu.browser.recording_count==3u);
    CHECK(!comp_runtime_menu_complete(&r,io.menu_token+1u,COMP_RUNTIME_OK,180u));
    CHECK(!comp_runtime_menu_complete(&r,io.menu_token,(comp_runtime_result_t)-1,181u));
    CHECK(commit_current(&r,200u));tap(&r,100,95,300u);
    CHECK(io.menu_calls==1u && r.menu_pending && r.menu_feedback==COMP_RUNTIME_MENU_FEEDBACK_CLEARING);
    CHECK(comp_runtime_record(&r,true,400u)==COMP_RUNTIME_BUSY && io.starts==0u);
    CHECK(comp_runtime_menu_retrying(&r,io.menu_token,true));
    uint32_t revision=r.revision;
    CHECK(comp_runtime_menu_retrying(&r,io.menu_token,true) && r.revision==revision);
    CHECK(comp_runtime_take_frame(&r,500u,&f) && f.menu_feedback==COMP_RUNTIME_MENU_FEEDBACK_RETRYING);
    CHECK(comp_runtime_complete_frame(&r,f.token,false,501u));
    CHECK(!comp_runtime_take_frame(&r,700u,&f));
    CHECK(comp_runtime_take_frame(&r,981u,&f) && f.menu_feedback==COMP_RUNTIME_MENU_FEEDBACK_RETRYING);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,982u));
    CHECK(comp_runtime_menu_complete(&r,io.menu_token,COMP_RUNTIME_OK,1000u));
    CHECK(!r.menu_pending && r.menu_feedback==COMP_RUNTIME_MENU_FEEDBACK_CLEARED &&
        r.menu.browser.recording_count==3u); /* Callback result cannot fabricate catalog entries. */
    CHECK(!comp_runtime_menu_complete(&r,io.menu_token,COMP_RUNTIME_BACKEND_FAILED,1001u));
    CHECK(commit_current(&r,1100u));
    io.menu_dispatch=COMP_RUNTIME_MENU_FAILED;tap(&r,100,95,1200u);
    CHECK(!r.menu_pending && r.menu_feedback==COMP_RUNTIME_MENU_FEEDBACK_FAILED);
    CHECK(comp_screen_menu_navigate_to(&r.menu,COMP_SCREEN_MENU_VIEW_BROWSER_CONNECTION));++r.revision;
    CHECK(commit_current(&r,1500u));io.menu_dispatch=COMP_RUNTIME_MENU_PENDING;
    tap(&r,100,100,1600u);
    CHECK(r.menu_pending && r.menu_feedback==COMP_RUNTIME_MENU_FEEDBACK_PAIRING);
    CHECK(!comp_runtime_menu_pair_timeout(&r,io.menu_token+1u,1700u));
    CHECK(comp_runtime_menu_pair_timeout(&r,io.menu_token,1710u) && !r.menu_pending &&
        r.menu_feedback==COMP_RUNTIME_MENU_FEEDBACK_TIMEOUT && !r.connected);
    CHECK(commit_current(&r,1800u));tap(&r,100,100,2500u);
    CHECK(r.menu_pending && comp_runtime_menu_complete(&r,io.menu_token,COMP_RUNTIME_OK,2600u));
    CHECK(r.menu_feedback==COMP_RUNTIME_MENU_FEEDBACK_CONNECTED);
    r.config.recording_control=NULL;
    CHECK(comp_runtime_record(&r,true,2700u)==COMP_RUNTIME_UNAVAILABLE &&
        r.menu_feedback==COMP_RUNTIME_MENU_FEEDBACK_NONE); /* Fresh capture failure owns its outcome. */
    puts("PASS menu completions: token-bound pending/retry/success/failure/timeout, duplicate and record guards, failed display retry, no fabricated catalog or radio state");
    return 0;
}
static int accepted_recording_limit(void)
{
    comp_runtime_t r;comp_speaker_t s;io_t io;
    setup(&r,&s,&io);comp_runtime_set_quiet(&r,true);
    CHECK(r.menu.browser.recording_limit_minutes==0u);
#ifdef COMPANION_RECORDING_SEGMENTED_ONLY
    r.menu.browser.recording_limit_minutes=30u; /* Legacy saved value must not stop local capture. */
#endif
    CHECK(comp_runtime_record(&r,true,99u)==COMP_RUNTIME_OK && r.record_limit_seconds==0u);
    tick(&r,&s,100u);
    CHECK(comp_runtime_recording_update(&r,io.token,DENZIC_AUDIO_RECORDING_STATE_RECORDING,true,101u));
    comp_runtime_service(&r,7200101u); /* Simulated 2h; no claim about physical media. */
    CHECK(io.stops==0u && !r.stop_pending);
    CHECK(comp_runtime_record(&r,false,7200102u)==COMP_RUNTIME_OK && io.stops==1u);
    setup(&r,&s,&io);r.config.recording_prepare=prepare;
    r.menu.browser.recording_limit_minutes=30u;
    CHECK(comp_runtime_record_start_limited(&r,42u,100u)==COMP_RUNTIME_OK &&
          r.record_limit_seconds==42u && r.prepare_pending);
    CHECK(comp_runtime_record_start_limited(&r,600u,101u)==COMP_RUNTIME_BUSY &&
          r.record_limit_seconds==42u && r.menu.browser.recording_limit_minutes==30u);
    CHECK(comp_runtime_record(&r,false,102u)==COMP_RUNTIME_OK);
    setup(&r,&s,&io);r.config.recording_prepare=prepare;
    r.menu.browser.recording_limit_minutes=15u;
    CHECK(comp_runtime_record_start_limited(&r,0u,200u)==COMP_RUNTIME_OK);
#ifdef COMPANION_RECORDING_SEGMENTED_ONLY
    CHECK(r.record_limit_seconds==0u);
#else
    CHECK(r.record_limit_seconds==900u);
#endif
    puts("PASS accepted recording limit: explicit host seconds, stable busy retry, local zero fallback");
    return 0;
}
static int capture_report_ahead_of_service_clock(void)
{
    const struct { uint32_t service_ms, started_ms; } clocks[] = {
        {7632069u,7632070u}, /* Actual second-start snapshot: HAL advanced 1 ms. */
        {UINT32_MAX,0u},
        {UINT32_MAX-4u,3u}, /* Callback can cross wrap during backend work. */
    };
    for (size_t i=0;i<sizeof(clocks)/sizeof(clocks[0]);i++) {
        comp_runtime_t r;comp_speaker_t s;io_t io;
        uint32_t service=clocks[i].service_ms,started=clocks[i].started_ms;
        setup_at(&r,&s,&io,service-1u);comp_runtime_set_quiet(&r,true);
        io.inline_runtime=&r;io.inline_started_ms=started;
        CHECK(comp_runtime_record_start_limited(&r,60u,service-1u)==COMP_RUNTIME_OK);
        comp_runtime_service(&r,service);
        CHECK(io.starts==1u && io.inline_report_accepted && r.capture_active);
        CHECK(io.stops==0u && !r.stop_pending && r.recording_display_second==0u);
        comp_runtime_service(&r,service);
        CHECK(io.stops==0u && r.recording_display_second==0u);
        comp_runtime_service(&r,started+999u);
        CHECK(io.stops==0u && r.recording_display_second==0u);
        comp_runtime_service(&r,started+1000u);
        CHECK(io.stops==0u && r.recording_display_second==1u);
        comp_runtime_service(&r,started+59999u);
        CHECK(io.stops==0u && r.recording_display_second==59u);
        comp_runtime_service(&r,started+60000u);
        CHECK(io.stops==1u && r.stop_pending && r.recording_display_second==60u);
        comp_runtime_service(&r,started+60001u);
        CHECK(io.stops==1u);
        CHECK(comp_runtime_recording_update(&r,io.token,
            DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY,false,started+60002u));
        /* Repeat on the same runtime: old ended-session time cannot own the new start. */
        io.inline_started_ms=started+61001u;io.inline_report_accepted=false;
        CHECK(comp_runtime_record_start_limited(&r,5u,started+60999u)==COMP_RUNTIME_OK);
        comp_runtime_service(&r,started+61000u);
        CHECK(io.starts==2u && io.inline_report_accepted && io.stops==1u &&
              r.capture_active && r.recording_display_second==0u);
        comp_runtime_service(&r,io.inline_started_ms+4999u);
        CHECK(io.stops==1u);
        comp_runtime_service(&r,io.inline_started_ms+5000u);
        CHECK(io.stops==2u && r.stop_pending);
    }
    puts("PASS recording clocks: synchronous later backend time, second start, counter wrap, real deadline and one stop");
    return 0;
}
static int battery_voltage_status(void)
{
    comp_runtime_t r; comp_speaker_t s; io_t io;comp_runtime_frame_t f;
    setup(&r,&s,&io);comp_runtime_status(&r,0u);
    uint32_t revision=r.revision;
    comp_runtime_battery_voltage(&r,3832u);
    CHECK(r.battery_mv==3830u && r.revision==revision && r.menu.browser.battery_percent==255u);
    comp_runtime_battery_voltage(&r,UINT16_MAX);
    CHECK(r.battery_mv==0u && r.revision==revision);
    r.surface=COMP_SCREEN_SURFACE_MENU;r.menu.view=COMP_SCREEN_MENU_VIEW_BROWSER_POWER;r.menu.home_page=0u;
    comp_runtime_battery_voltage(&r,3832u);
    CHECK(r.revision==revision+1u);
    comp_runtime_battery_voltage(&r,3834u);CHECK(r.revision==revision+1u);
    CHECK(comp_runtime_take_frame(&r,10u,&f) && f.battery_mv==3830u);
    comp_runtime_battery_voltage(&r,3700u);
    CHECK(f.battery_mv==3830u && r.in_flight.battery_mv==3830u); /* Submitted frame is immutable. */
    comp_runtime_status(&r,(1u<<17)|(75u<<24));revision=r.revision;
    comp_runtime_battery_voltage(&r,3900u);CHECK(r.revision==revision);
    comp_runtime_status(&r,0u);revision=r.revision;
    r.menu.home_page=4u;comp_runtime_battery_voltage(&r,3600u);CHECK(r.revision==revision);
    r.menu.home_page=0u;comp_runtime_battery_voltage(&r,0u);CHECK(r.battery_mv==0u && r.revision==revision+1u);
    CHECK(io.starts==0u && io.stops==0u);
    puts("PASS_BATTERY_RUNTIME: qualified volts, unknown SOC, 10mV display precision, power-page-only invalidation, immutable submitted frame");
    return 0;
}
static int paused_corner_double_tap_stops_original(void)
{
    comp_runtime_t r;comp_speaker_t s;io_t io;
    setup(&r,&s,&io);comp_runtime_set_quiet(&r,true);
    /* Use the existing touch recognizer and configured default shortcut,
     * not a direct recording API, for both user gestures. */
    tap(&r,20,175,10u);tap(&r,20,175,140u);tick(&r,&s,230u);
    CHECK(io.starts==1u && io.stops==0u);
    uint32_t original=io.token;
    CHECK(comp_runtime_recording_update(&r,original,
        DENZIC_AUDIO_RECORDING_STATE_RECORDING,true,240u));
    CHECK(comp_runtime_recording_captured(&r,original,100u));
    CHECK(comp_runtime_recording_update(&r,original,
        DENZIC_AUDIO_RECORDING_STATE_RECORDING,false,350u));
    CHECK(!r.capture_active && r.recording==DENZIC_AUDIO_RECORDING_STATE_RECORDING);
    tap(&r,20,175,500u);tap(&r,20,175,630u);
    CHECK(io.stops==1u && io.starts==1u && r.stop_pending);
    CHECK(r.record_token==original && io.token==original);
    tap(&r,20,175,1000u);tap(&r,20,175,1130u);
    CHECK(io.stops==1u && io.starts==1u && r.record_token==original);
    puts("PASS_PAUSED_CORNER_GESTURE: existing lower-left double-tap starts; paused original stops once through the same touch recognizer, never restarts");
    return 0;
}
static int recording_hold_local_input_and_emergency_stop(void)
{
    /* Owner cancelled HOLD. Old API callers cannot leave an invisible lock. */
    comp_runtime_t r;comp_speaker_t s;io_t io;comp_runtime_frame_t frame;
    setup(&r,&s,&io);comp_runtime_set_quiet(&r,true);
    CHECK(comp_runtime_record(&r,true,10u)==COMP_RUNTIME_OK);tick(&r,&s,11u);
    const uint32_t original=io.token;CHECK(io.starts==1u);
    CHECK(comp_runtime_recording_update(&r,original,DENZIC_AUDIO_RECORDING_STATE_RECORDING,true,12u));
    CHECK(comp_runtime_recording_set_hold(&r,original,true,14u)==COMP_RUNTIME_UNAVAILABLE);
    CHECK(!comp_runtime_recording_hold(&r)&&r.capture_active);
    CHECK(comp_runtime_take_frame(&r,15u,&frame)&&!frame.recording_input_locked&&!frame.recording_hold_control);
    CHECK(comp_runtime_complete_frame(&r,frame.token,true,16u));
    CHECK(comp_runtime_recording_update(&r,original,DENZIC_AUDIO_RECORDING_STATE_RECORDING,false,1000u));
    CHECK(!comp_runtime_recording_hold(&r)&&comp_runtime_recording_owned(&r));
    tap(&r,20u,175u,1500u);tap(&r,20u,175u,1650u);
    CHECK(io.stops==1u&&r.stop_pending&&io.starts==1u&&r.record_token==original);
    CHECK(comp_runtime_record(&r,false,1800u)==COMP_RUNTIME_OK&&io.stops==1u);
    CHECK(comp_runtime_recording_update(&r,original,DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY,false,1900u));
    CHECK(!comp_runtime_recording_owned(&r));
    puts("PASS_RECORDING_NO_HOLD: cancelled lock rejects enable, original paused double-tap STOP/emergency STOP idempotent");return 0;
}
static int paused_capture_clock_and_stop(void)
{
    comp_runtime_t r;comp_speaker_t s;io_t io;
    setup(&r,&s,&io);comp_runtime_set_quiet(&r,true);
    CHECK(comp_runtime_record_start_limited(&r,60u,100u)==COMP_RUNTIME_OK);
    tick(&r,&s,101u);CHECK(io.starts==1u);
    comp_runtime_set_quiet(&r,false);
    CHECK(comp_runtime_recording_captured(&r,io.token,0u));
    CHECK(comp_runtime_recording_update(&r,io.token,DENZIC_AUDIO_RECORDING_STATE_RECORDING,true,102u));
    CHECK(comp_runtime_recording_captured(&r,io.token,1200u));
    comp_runtime_service(&r,1302u);CHECK(r.recording_display_second==1u);
    unsigned submitted=r.audio.stats.submitted;
    uint32_t anchor=r.recording_since_ms;
    CHECK(comp_runtime_recording_update(&r,io.token,DENZIC_AUDIO_RECORDING_STATE_RECORDING,false,1303u));
    CHECK(r.audio.stats.submitted==submitted&&!r.audio.last_accepted_valid[COMP_AUDIO_FEEDBACK_RECORDING_STOPPED]);
    comp_runtime_service(&r,100000u);
    CHECK(r.recording_display_second==1u&&!io.stops&&r.recording_since_ms==anchor);
    CHECK(!comp_runtime_recording_captured(&r,io.token+1u,4000u));
    CHECK(!comp_runtime_recording_captured(&r,io.token,1190u));
    CHECK(comp_runtime_recording_update(&r,io.token,DENZIC_AUDIO_RECORDING_STATE_RECORDING,true,100001u));
    CHECK(r.recording_since_ms==anchor&&r.recording_display_second==1u&&r.audio.stats.submitted==submitted);
    CHECK(comp_runtime_recording_captured(&r,io.token,2400u));
    comp_runtime_service(&r,100002u);CHECK(r.recording_display_second==2u);
    CHECK(comp_runtime_recording_update(&r,io.token,DENZIC_AUDIO_RECORDING_STATE_RECORDING,false,100003u));
    CHECK(comp_runtime_record(&r,false,100004u)==COMP_RUNTIME_OK&&io.stops==1u&&r.stop_pending);
    CHECK(comp_runtime_recording_update(&r,io.token,DENZIC_AUDIO_RECORDING_STATE_STOPPING,false,100005u));
    CHECK(r.stop_pending&&r.audio.stats.submitted==submitted);
    CHECK(comp_runtime_record(&r,false,100006u)==COMP_RUNTIME_OK&&io.stops==1u);
    CHECK(comp_runtime_recording_update(&r,io.token,DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY,false,100007u));
    CHECK(!r.stop_pending&&r.audio.stats.submitted==submitted+1u);
    CHECK(comp_runtime_recording_update(&r,io.token,DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY,false,100008u));
    CHECK(r.audio.stats.submitted==submitted+1u);
    comp_runtime_set_quiet(&r,true);
    CHECK(comp_runtime_record_start_limited(&r,5u,100100u)==COMP_RUNTIME_OK);
    CHECK(!r.recording_capture_clock&&r.recording_captured_ms==0u);
    tick(&r,&s,100101u);
    CHECK(comp_runtime_recording_update(&r,io.token,DENZIC_AUDIO_RECORDING_STATE_RECORDING,true,100102u));
    comp_runtime_service(&r,101102u);CHECK(r.recording_display_second==1u);
    puts("PASS_CAPTURE_PAUSE_RUNTIME: actual runtime preserves anchor and captured duration through long pause/resume; no false end cue; one paused STOP/one sealed cue; stale/backward capture clocks rejected; next legacy recording resets clock source");
    return 0;
}
int main(int argc,char **argv)
{
    if(argc==2&&!strcmp(argv[1],"--recording-start-only"))
        return preparation_clock_order_and_stop_cause()||storage_before_sound();
    if(argc==2&&!strcmp(argv[1],"--recording-pause-only"))
        return recording_hold_local_input_and_emergency_stop()||paused_corner_double_tap_stops_original()||record_journey()||paused_capture_clock_and_stop()||capture_report_ahead_of_service_clock()||accepted_recording_limit();
    if(argc==2 && !strcmp(argv[1],"--battery-only"))return battery_voltage_status();
    if (capture_report_ahead_of_service_clock() || accepted_recording_limit() || record_journey() || cancellation_and_unavailable() || display_and_input() ||
        menu_and_sleep() || menu_routes_and_rollback() || menu_completion_truth() ||
        menu_input_requires_visible_commit() ||
        menu_record_truth_and_pending_cancel() ||
        touch_sequence_and_blink_competition() ||
        timers_status_and_recording_life() || storage_before_sound() ||
        recording_wave_sequence_contract() || independent_tracks_and_family() ||
        wave_fairness_after_late_display() || blink_then_drag_and_reaction_cadence() || causal_transition() || reaction_in_flight_cooldown() || pet_sound_policy()) return 1;
    puts("PASS_PREHARDWARE_RUNTIME: portable product journeys; physical acceptance NOT_RUN");
    return 0;
}
