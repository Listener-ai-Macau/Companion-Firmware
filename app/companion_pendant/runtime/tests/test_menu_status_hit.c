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

static int status_is_read_only(comp_screen_menu_view_t view)
{
    comp_runtime_t r;io_t io;setup(&r,&io,view);CHECK(commit(&r,1u));
    const uint32_t revision=r.menu.revision;
    tap(&r,20u,7u,100u);
    printf("CLOCK_TAP view=%u surface_after=%u view_after=%u\n",(unsigned)view,(unsigned)r.surface,(unsigned)r.menu.view);
    CHECK(r.surface==COMP_SCREEN_SURFACE_MENU && r.menu.view==view);
    CHECK(r.menu.revision==revision && !io.menu_calls && !io.starts && !io.stops);
    /* A status contact cannot drift into the title's back control. */
    report(&r,COMP_FT6336_TOUCH_EVENT_DOWN,true,20u,19u,300u);
    report(&r,COMP_FT6336_TOUCH_EVENT_CONTACT,true,20u,23u,320u);
    report(&r,COMP_FT6336_TOUCH_EVENT_UP,false,20u,25u,360u);
    report(&r,COMP_FT6336_TOUCH_EVENT_UP,false,20u,25u,380u);
    CHECK(r.surface==COMP_SCREEN_SURFACE_MENU && r.menu.view==view && r.menu.revision==revision);
    /* The visible back arrow in the title remains actionable. */
    tap(&r,20u,30u,500u);
    if(view==COMP_SCREEN_MENU_VIEW_BROWSER_HOME || view==COMP_SCREEN_MENU_VIEW_BROWSER_QUICK)
        CHECK(r.surface==COMP_SCREEN_SURFACE_HOME);
    else CHECK(r.surface==COMP_SCREEN_SURFACE_MENU && r.menu.view==COMP_SCREEN_MENU_VIEW_BROWSER_HOME);
    CHECK(!io.menu_calls && !io.starts && !io.stops);
    return 0;
}
static int right_swipe_and_setting(void)
{
    comp_runtime_t r;io_t io;setup(&r,&io,COMP_SCREEN_MENU_VIEW_BROWSER_DISPLAY);CHECK(commit(&r,1u));
    const bool clock24=r.menu.browser.clock_24_hour;
    tap(&r,100u,65u,100u);CHECK(io.menu_calls==1u && r.menu.browser.clock_24_hour!=clock24);
    CHECK(commit(&r,201u));
    report(&r,COMP_FT6336_TOUCH_EVENT_DOWN,true,40u,100u,300u);
    report(&r,COMP_FT6336_TOUCH_EVENT_CONTACT,true,80u,100u,320u);
    report(&r,COMP_FT6336_TOUCH_EVENT_CONTACT,true,160u,100u,400u);
    report(&r,COMP_FT6336_TOUCH_EVENT_UP,false,160u,100u,460u);
    report(&r,COMP_FT6336_TOUCH_EVENT_UP,false,160u,100u,480u);
    CHECK(r.surface==COMP_SCREEN_SURFACE_MENU && r.menu.view==COMP_SCREEN_MENU_VIEW_BROWSER_HOME);
    CHECK(io.menu_calls==1u && !io.starts && !io.stops);
    return 0;
}
int main(void)
{
    const comp_screen_menu_view_t views[]={COMP_SCREEN_MENU_VIEW_BROWSER_HOME,
        COMP_SCREEN_MENU_VIEW_BROWSER_DISPLAY,COMP_SCREEN_MENU_VIEW_BROWSER_RESTORE_DEFAULTS,
        COMP_SCREEN_MENU_VIEW_BROWSER_PET_HELP,COMP_SCREEN_MENU_VIEW_BROWSER_QUICK};
    for(unsigned i=0u;i<sizeof(views)/sizeof(views[0]);++i)if(status_is_read_only(views[i]))return 1;
    if(right_swipe_and_setting())return 1;
    puts("PASS_MENU_STATUS_HIT_SOFTWARE: actual runtime/recognizer/menu external UI80; status inert, title back/right swipe/settings retained; physical NOT_RUN");return 0;
}
