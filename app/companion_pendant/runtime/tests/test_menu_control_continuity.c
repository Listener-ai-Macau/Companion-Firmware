#include "companion_runtime.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){printf("FAIL %d: %s\n",__LINE__,#x);return 1;}} while(0)
typedef struct {unsigned menu_calls,starts,stops;uint32_t token;} io_t;
static bool ready(void *c){(void)c;return true;}
static bool record(void *c,bool start,uint32_t token)
{io_t *io=c;if(start)++io->starts;else ++io->stops;io->token=token;return true;}
static bool action(void *c,const comp_screen_menu_result_t *result,const comp_screen_menu_t *menu)
{(void)result;(void)menu;++((io_t*)c)->menu_calls;return true;}
static void setup(comp_runtime_t *r,io_t *io,comp_screen_menu_view_t view)
{
    memset(io,0,sizeof(*io));
    const comp_runtime_config_t config={.context=io,.recording_ready=ready,.recording_control=record,.menu_action=action};
    comp_runtime_init(r,&config,0u);comp_runtime_set_quiet(r,true);
    r->surface=COMP_SCREEN_SURFACE_MENU;r->menu.view=view;r->menu.home_page=0u;
    ++r->menu.revision;++r->revision;
}
static bool commit(comp_runtime_t *r,uint32_t now)
{comp_runtime_frame_t f;return comp_runtime_take_frame(r,now,&f)&&comp_runtime_complete_frame(r,f.token,true,now+1u);}
static void report(comp_runtime_t *r,uint8_t event,bool down,uint16_t x,uint16_t y,uint32_t now)
{
    const comp_ft6336_touch_sample_t s={(uint8_t)(down?1u:0u),event,0u,x,y};
    comp_runtime_touch(r,&s,r->last_touch_sequence+1u,true,now);
}
static void tap(comp_runtime_t *r,uint16_t x,uint16_t y,uint32_t now)
{
    report(r,COMP_FT6336_TOUCH_EVENT_DOWN,true,x,y,now);
    report(r,COMP_FT6336_TOUCH_EVENT_CONTACT,true,x,y,now+20u);
    report(r,COMP_FT6336_TOUCH_EVENT_UP,false,x,y,now+60u);
    report(r,COMP_FT6336_TOUCH_EVENT_UP,false,x,y,now+80u);
}
static bool repaint(comp_runtime_t *r,comp_runtime_frame_t *f,uint32_t now)
{comp_runtime_status(r,0x8001u);return comp_runtime_take_frame(r,now,f);}
static int tap_during_same_controls(void)
{
    comp_runtime_t r;io_t io;comp_runtime_frame_t f;
    setup(&r,&io,COMP_SCREEN_MENU_VIEW_BROWSER_DISPLAY);CHECK(commit(&r,1u));
    const bool before=r.menu.browser.clock_24_hour;
    CHECK(repaint(&r,&f,100u));CHECK(f.menu.revision==r.visible_menu_revision);
    tap(&r,100u,65u,110u);
    CHECK(io.menu_calls==1u&&r.menu.browser.clock_24_hour!=before);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,201u));
    /* A changed setting is a new control revision: no second stale tap. */
    tap(&r,100u,65u,220u);CHECK(io.menu_calls==1u);
    CHECK(commit(&r,310u));tap(&r,100u,65u,330u);CHECK(io.menu_calls==2u);
    puts("PASS_SAME_CONTROL_REPAINT: one real menu action during status frame; changed setting waits for its visible revision");return 0;
}
static int status_completion_during_finger(void)
{
    comp_runtime_t r;io_t io;comp_runtime_frame_t f;
    setup(&r,&io,COMP_SCREEN_MENU_VIEW_BROWSER_DISPLAY);CHECK(commit(&r,1u));CHECK(repaint(&r,&f,100u));
    report(&r,COMP_FT6336_TOUCH_EVENT_DOWN,true,100u,65u,110u);
    report(&r,COMP_FT6336_TOUCH_EVENT_CONTACT,true,100u,65u,130u);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,140u));
    report(&r,COMP_FT6336_TOUCH_EVENT_UP,false,100u,65u,170u);
    report(&r,COMP_FT6336_TOUCH_EVENT_UP,false,100u,65u,190u);
    CHECK(io.menu_calls==1u);
    puts("PASS_SAME_CONTROL_COMPLETION: status completion between DOWN/UP preserves exactly one action");return 0;
}
static int new_page_and_failure_stay_inert(void)
{
    comp_runtime_t r;io_t io;comp_runtime_frame_t f;
    setup(&r,&io,COMP_SCREEN_MENU_VIEW_BROWSER_DISPLAY);CHECK(commit(&r,1u));
    CHECK(comp_screen_menu_navigate_to(&r.menu,COMP_SCREEN_MENU_VIEW_BROWSER_INTERACTION));++r.revision;
    CHECK(comp_runtime_take_frame(&r,100u,&f));
    report(&r,COMP_FT6336_TOUCH_EVENT_DOWN,true,100u,132u,110u);
    report(&r,COMP_FT6336_TOUCH_EVENT_CONTACT,true,100u,132u,130u);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,140u));
    report(&r,COMP_FT6336_TOUCH_EVENT_UP,false,100u,132u,170u);
    report(&r,COMP_FT6336_TOUCH_EVENT_UP,false,100u,132u,190u);CHECK(!io.menu_calls);
    /* Interaction's first row is read-only. Row2 is the actual mode cycle. */
    tap(&r,100u,132u,210u);CHECK(io.menu_calls==1u);
    setup(&r,&io,COMP_SCREEN_MENU_VIEW_BROWSER_DISPLAY);CHECK(commit(&r,1u));CHECK(repaint(&r,&f,100u));
    report(&r,COMP_FT6336_TOUCH_EVENT_DOWN,true,100u,65u,110u);
    report(&r,COMP_FT6336_TOUCH_EVENT_CONTACT,true,100u,65u,130u);
    CHECK(comp_runtime_complete_frame(&r,f.token,false,140u));
    report(&r,COMP_FT6336_TOUCH_EVENT_UP,false,100u,65u,170u);
    report(&r,COMP_FT6336_TOUCH_EVENT_UP,false,100u,65u,190u);CHECK(!io.menu_calls);
    tap(&r,100u,65u,210u);CHECK(!io.menu_calls&&!r.visible_menu_valid);
    puts("PASS_NEW_PAGE_FAILED_IMAGE: unseen page cannot inherit a held finger; failed image cannot dispatch coordinates");return 0;
}
static int visible_recording_lock_owner(void)
{
    /* Owner removed the optional touch lock. Keep the historical test entry
     * name while checking that its old coordinates cannot enable a lock. */
    comp_runtime_t r;io_t io;comp_runtime_frame_t f;
    setup(&r,&io,COMP_SCREEN_MENU_VIEW_BROWSER_DISPLAY);
    r.surface=COMP_SCREEN_SURFACE_HOME;CHECK(comp_runtime_record_start_limited(&r,60u,100u)==COMP_RUNTIME_OK);
    comp_runtime_service(&r,101u);CHECK(io.starts==1u);
    CHECK(comp_runtime_recording_update(&r,io.token,DENZIC_AUDIO_RECORDING_STATE_RECORDING,true,102u));
    CHECK(comp_runtime_recording_captured(&r,io.token,0u));CHECK(commit(&r,103u));
    report(&r,COMP_FT6336_TOUCH_EVENT_DOWN,true,138u,8u,110u);
    report(&r,COMP_FT6336_TOUCH_EVENT_CONTACT,true,138u,8u,150u);
    report(&r,COMP_FT6336_TOUCH_EVENT_CONTACT,true,138u,8u,1110u);
    report(&r,COMP_FT6336_TOUCH_EVENT_UP,false,138u,8u,1120u);
    CHECK(!comp_runtime_recording_hold(&r)&&!io.stops);
    CHECK(comp_runtime_recording_set_hold(&r,io.token,true,1200u)==COMP_RUNTIME_UNAVAILABLE);
    CHECK(comp_runtime_recording_update(&r,io.token,DENZIC_AUDIO_RECORDING_STATE_RECORDING,false,1300u));
    CHECK(comp_runtime_take_frame(&r,1301u,&f)&&f.recording_paused&&!f.recording_hold_control&&!f.recording_input_locked);
    puts("PASS_NO_RECORD_LOCK: old touch area inert, hidden enabling rejected, paused original remains visible");return 0;
}

int main(void)
{
    if(tap_during_same_controls()||status_completion_during_finger()||new_page_and_failure_stay_inert()||visible_recording_lock_owner())return 1;
    puts("PASS_MENU_CONTROL_CONTINUITY_SOFTWARE: real runtime/recognizer/menu, fake I/O and visible-completion calls; physical latency/optics/recording NOT_RUN");return 0;
}
