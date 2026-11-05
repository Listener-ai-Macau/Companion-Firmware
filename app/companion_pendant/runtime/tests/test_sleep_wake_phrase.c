#include "companion_runtime.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do{if(!(x)){printf("FAIL %u %s\n",(unsigned)__LINE__,#x);return 1;}}while(0)
static unsigned starts;
static bool ready(void *c){(void)c;return true;}
static bool record(void *c,bool start,uint32_t token){(void)c;(void)token;if(start)++starts;return true;}
static void setup(comp_runtime_t *r,uint32_t now)
{
    const comp_runtime_config_t config={.recording_ready=ready,.recording_control=record};
    comp_runtime_init(r,&config,now);comp_runtime_set_quiet(r,true);
    r->pet_startup_pending=false;r->menu.browser.auto_sleep_minutes=1u;
    r->last_activity_ms=now-60001u;comp_runtime_service(r,now);
}
int main(void)
{
    comp_runtime_t r;comp_runtime_frame_t f,g;
    setup(&r,60001u);r.surface=COMP_SCREEN_SURFACE_LOW_POWER;r.sleep_phase=COMP_RUNTIME_SLEEP_NONE;
    comp_runtime_wake_from(&r,60002u,COMP_RUNTIME_WAKE_KEY);
    comp_runtime_wake_from(&r,60032u,COMP_RUNTIME_WAKE_KEY);
    CHECK(r.sleep_phase==COMP_RUNTIME_SLEEP_WAKE&&r.wake_count==1u);
    CHECK(comp_runtime_take_frame(&r,60033u,&f)&&f.sleep_phase==COMP_RUNTIME_SLEEP_WAKE);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,60733u));
    comp_runtime_wake_from(&r,60734u,COMP_RUNTIME_WAKE_KEY);
    CHECK(r.sleep_phase==COMP_RUNTIME_SLEEP_ATTEND&&r.wake_count==1u);
    puts("PASS_DUPLICATE_WAKE: same physical edge/debounce wake cannot cancel either visible wake beat");
    setup(&r,60001u);
    CHECK(r.sleep_phase==COMP_RUNTIME_SLEEP_DOZE&&r.surface==COMP_SCREEN_SURFACE_HOME);
    CHECK(comp_runtime_take_frame(&r,60001u,&f)&&f.sleep_phase==COMP_RUNTIME_SLEEP_DOZE);
    CHECK(!comp_runtime_take_frame(&r,60002u,&g));
    CHECK(comp_runtime_complete_frame_timed(&r,f.token,false,60501u,60400u));
    CHECK(r.sleep_phase==COMP_RUNTIME_SLEEP_DOZE&&r.visible_frames==0u);
    CHECK(comp_runtime_take_frame(&r,61000u,&g)&&g.pet_seed==f.pet_seed&&g.sleep_phase==f.sleep_phase);
    CHECK(comp_runtime_complete_frame_timed(&r,g.token,true,61500u,61100u));
    CHECK(r.sleep_phase==COMP_RUNTIME_SLEEP_YAWN&&r.reaction_due_ms==62000u);
    CHECK(!comp_runtime_take_frame(&r,61999u,&f));
    CHECK(comp_runtime_take_frame(&r,62000u,&f)&&f.sleep_phase==COMP_RUNTIME_SLEEP_YAWN);
    CHECK(comp_runtime_complete_frame_timed(&r,f.token,true,62500u,62400u));
    CHECK(r.sleep_phase==COMP_RUNTIME_SLEEP_PARK&&r.surface==COMP_SCREEN_SURFACE_LOW_POWER);
    CHECK(r.visible_surface==COMP_SCREEN_SURFACE_HOME&&r.visible_revision!=r.revision);
    CHECK(!comp_runtime_take_frame(&r,63499u,&f));
    CHECK(comp_runtime_take_frame(&r,63500u,&f)&&f.surface==COMP_SCREEN_SURFACE_LOW_POWER);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,64000u));
    CHECK(!r.sleep_phase&&r.visible_surface==COMP_SCREEN_SURFACE_LOW_POWER&&r.visible_revision==r.revision);
    comp_runtime_service(&r,80000u);CHECK(!comp_runtime_take_frame(&r,80000u,&f));
    comp_runtime_wake_from(&r,80001u,COMP_RUNTIME_WAKE_KEY);
    CHECK(r.wake_count==1u&&r.sleep_phase==COMP_RUNTIME_SLEEP_WAKE);
    CHECK(comp_runtime_take_frame(&r,80001u,&f)&&f.family==COMP_BROWSER_FAMILY_CALM);
    CHECK(comp_runtime_complete_frame_timed(&r,f.token,true,80501u,80401u));
    CHECK(r.sleep_phase==COMP_RUNTIME_SLEEP_ATTEND&&r.reaction_due_ms==81051u);
    CHECK(!comp_runtime_take_frame(&r,81050u,&f));
    CHECK(comp_runtime_take_frame(&r,81051u,&f));CHECK(comp_runtime_complete_frame(&r,f.token,true,81551u));
    CHECK(!r.sleep_phase&&r.life.next_request_ms==83351u&&r.blink.awake);
    puts("PASS_FINITE_SLEEP_WAKE: visible holds, failed retry, one in flight, parked no animation, wake anchors");
    setup(&r,60001u);CHECK(comp_runtime_take_frame(&r,60001u,&f));
    CHECK(comp_runtime_complete_frame(&r,f.token,true,61001u));
    CHECK(r.sleep_phase==COMP_RUNTIME_SLEEP_YAWN);
    puts("PASS_SLOW_PANEL: normal RAM tail cannot omit the yawn anchor; one beat only, no catch-up");
    setup(&r,60001u);CHECK(comp_runtime_take_frame(&r,60001u,&f));
    comp_runtime_wake_from(&r,60002u,COMP_RUNTIME_WAKE_TOUCH);
    CHECK(!r.sleep_phase&&r.surface==COMP_SCREEN_SURFACE_HOME);
    CHECK(comp_runtime_complete_frame(&r,f.token,true,60501u));CHECK(!r.sleep_phase&&r.surface==COMP_SCREEN_SURFACE_HOME);
    CHECK(r.wake_count==0u);
    puts("PASS_INTERRUPTED_DOZE: new input generation cannot inherit an old sleep completion");
    setup(&r,60001u);CHECK(comp_runtime_take_frame(&r,60001u,&f));
    comp_runtime_update_progress(&r,(uint16_t)(COMP_RUNTIME_UPDATE_RECEIVING|(25u<<8u)),60002u);
    CHECK(!r.sleep_phase);CHECK(comp_runtime_complete_frame(&r,f.token,true,60501u));CHECK(!r.sleep_phase);
    puts("PASS_UPDATE_PREEMPTION: old sleep completion cannot overwrite OTA owner");
    setup(&r,60001u);r.surface=COMP_SCREEN_SURFACE_LOW_POWER;r.sleep_phase=COMP_RUNTIME_SLEEP_NONE;
    CHECK(comp_runtime_record_start_limited(&r,60u,60002u)==COMP_RUNTIME_OK);
    CHECK(!r.sleep_phase&&r.surface==COMP_SCREEN_SURFACE_HOME);comp_runtime_service(&r,60003u);CHECK(starts==1u);
    puts("PASS_RECORD_WAKE: capture command does not wait for decorative wake frames");
    setup(&r,60001u);r.surface=COMP_SCREEN_SURFACE_LOW_POWER;r.sleep_phase=COMP_RUNTIME_SLEEP_NONE;
    comp_runtime_motion(&r,COMP_MOTION_PICKUP,1u,1u,60002u);
    CHECK(r.sleep_phase==COMP_RUNTIME_SLEEP_WAKE&&!r.reaction_pending);
    comp_runtime_motion(&r,COMP_MOTION_SETTLED,1u,2u,60003u);
    CHECK(r.sleep_phase==COMP_RUNTIME_SLEEP_WAKE&&!r.reaction_pending&&r.reaction_due_ms==60002u);
    puts("PASS_PICKUP_WAKE: sensor follow-up cannot overwrite the wake dwell");
    comp_runtime_init(&r,NULL,0u);r.pet_startup_pending=false;r.menu.browser.auto_sleep_minutes=1u;
    r.taps.pending=true;comp_runtime_service(&r,60001u);
    CHECK(r.sleep_phase==COMP_RUNTIME_SLEEP_DOZE&&!r.taps.pending&&!r.reaction_pending);
    puts("PASS_OLD_TAP_RETIRED: pre-sleep tap arbitration cannot start a hidden response");
    setup(&r,0xfffffff0u);CHECK(comp_runtime_take_frame(&r,0xfffffff0u,&f));
    CHECK(comp_runtime_complete_frame(&r,f.token,true,0x000001e4u));
    CHECK(r.sleep_phase==COMP_RUNTIME_SLEEP_YAWN);
    CHECK(!comp_runtime_take_frame(&r,r.reaction_due_ms-1u,&f));
    CHECK(comp_runtime_take_frame(&r,r.reaction_due_ms,&f));
    printf("PASS_MENU_CONTROL_CONTINUITY_SOFTWARE: sleep/wake only runtime_bytes=%u frame_bytes=%u\n",(unsigned)sizeof(r),(unsigned)sizeof(f));return 0;
}
