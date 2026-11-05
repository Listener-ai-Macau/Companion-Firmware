#include "companion_renderer.h"
#include "generated/companion_wba_menu_geometry.h"
#include "generated/companion_wba_live_menu_values.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do { if (!(x)) { printf("FAIL %d: %s\n",__LINE__,#x); return 1; } } while(0)
enum { VALUE_Y = COMP_WBA_MENU_ROW_TOP + COMP_WBA_MENU_VALUE_TOP,
       SECOND_VALUE_Y = VALUE_Y + COMP_WBA_MENU_ROW_HEIGHT,
       VALUE_HEIGHT = COMP_WBA_LIVE_VALUE_HEIGHT };
typedef struct { bool fail; char last[128]; uint8_t value; } source_t;
static void ink(uint8_t *f,unsigned x,unsigned y) { f[y*25+x/8] &= (uint8_t)~(0x80u>>(x%8)); }
/* Deliberate synthetic masks test pixel ownership; they are not product art. */
static bool source(void *context,const char *name,uint8_t *f)
{
    source_t *s=context;
    (void)snprintf(s->last,sizeof(s->last),"%s",name);
    if(s->fail) return false;
    memset(f,0xFF,5000);
    if(!strcmp(name,"blink_open") || !strcmp(name,"blink_closed")) {
        unsigned top=!strcmp(name,"blink_open")?88u:107u,bottom=!strcmp(name,"blink_open")?123u:110u;
        for(unsigned y=top;y<bottom;++y) for(unsigned x=45;x<70;x++) { ink(f,x,y); ink(f,x+80,y); }
    } else if(!strcmp(name,"recording_timeline_00")) {
        for(unsigned y=156;y<180;y++) for(unsigned x=2;x<22;x++) ink(f,x,y);
    } else {
        f[2500]=s->value; f[2510]=0x55; f[3000]=0x12;
        for(unsigned y=112;y<147;y++) for(unsigned x=42;x<69;x++) {ink(f,x,y);ink(f,x+79,y);}
        for(unsigned x=48;x<70;x++)ink(f,x,75); /* A brow must never become an eyelid. */
        /* Retained curious/sleepy/alert art occupies part of the old wave
         * destination. Keep a representative cheek edge to catch erasure. */
        for(unsigned y=156;y<169;y++) for(unsigned x=33;x<42;x++) ink(f,x,y);
    }
    return true;
}
typedef struct { unsigned calls, fail_after; } progress_t;
static bool audio_checkpoint(void *context)
{
    progress_t *p=context;
    ++p->calls;
    return p->fail_after==0u || p->calls<p->fail_after;
}
static int battery_power_page(void)
{
    comp_runtime_renderer_t r;source_t s={0};uint8_t unknown[5000],volts[5000],frame[5000];
    comp_runtime_renderer_init(&r,source,&s);
    comp_runtime_frame_t f={0};f.surface=COMP_SCREEN_SURFACE_MENU;
    f.menu.view=COMP_SCREEN_MENU_VIEW_BROWSER_POWER;f.menu.language=COMP_SCREEN_MENU_LANGUAGE_ZH;
    f.token=1;CHECK(comp_runtime_renderer_render(&r,&f,unknown));CHECK(comp_runtime_renderer_complete(&r,1,true));
    f.battery_mv=3830u;f.token=2;
    CHECK(comp_runtime_renderer_render(&r,&f,volts));CHECK(comp_runtime_renderer_complete(&r,2,true));
    CHECK(memcmp(unknown+VALUE_Y*25,volts+VALUE_Y*25,VALUE_HEIGHT*25)!=0);
    for(unsigned y=0;y<200;y++)for(unsigned x=0;x<200;x++) {
        if(x>=COMP_WBA_MENU_VALUE_LEFT && x<COMP_WBA_MENU_VALUE_LEFT+COMP_WBA_MENU_VALUE_WIDTH &&
           y>=VALUE_Y && y<VALUE_Y+VALUE_HEIGHT)continue;
        CHECK((unknown[y*25+x/8]&(0x80u>>(x%8)))==(volts[y*25+x/8]&(0x80u>>(x%8))));
    }
    f.battery_mv=3840u;f.token=3;
    CHECK(comp_runtime_renderer_render(&r,&f,frame));CHECK(comp_runtime_renderer_complete(&r,3,true));
    CHECK(memcmp(frame+VALUE_Y*25,volts+VALUE_Y*25,VALUE_HEIGHT*25)!=0);
    f.battery_mv=5001u;f.token=4;
    CHECK(comp_runtime_renderer_render(&r,&f,frame));CHECK(comp_runtime_renderer_complete(&r,4,true));
    CHECK(!memcmp(frame,unknown,5000));
    f.battery_mv=3830u;f.status_packed=(1u<<17)|(75u<<24);f.token=5;
    CHECK(comp_runtime_renderer_render(&r,&f,volts));CHECK(comp_runtime_renderer_complete(&r,5,true));
    f.battery_mv=0u;f.token=6;
    CHECK(comp_runtime_renderer_render(&r,&f,frame));CHECK(comp_runtime_renderer_complete(&r,6,true));
    CHECK(!memcmp(frame,volts,5000)); /* Qualified percentage has priority. */
    f.status_packed=0u;f.menu.home_page=4u;f.token=7;
    CHECK(comp_runtime_renderer_render(&r,&f,unknown));CHECK(comp_runtime_renderer_complete(&r,7,true));
    f.battery_mv=3830u;f.token=8;
    CHECK(comp_runtime_renderer_render(&r,&f,frame));CHECK(comp_runtime_renderer_complete(&r,8,true));
    CHECK(!memcmp(frame,unknown,5000));
    puts("PASS_BATTERY_RENDERER: volts only with qualified cell reading, unknown fallback, measured SOC priority, field-only pixels, hidden-page unchanged");
    return 0;
}
int main(int argc,char **argv)
{
    if(argc==2 && !strcmp(argv[1],"--battery-only"))return battery_power_page();
    static comp_runtime_renderer_t r;
    source_t s={0}; uint8_t frame[5000], original[5000], status_a[5000], status_b[5000];
    comp_runtime_frame_t f={0};
    f.token=1; f.family=COMP_BROWSER_FAMILY_CURIOUS; f.gaze_x=f.gaze_y=100;
    comp_runtime_renderer_init(&r,source,&s);
    CHECK(comp_runtime_renderer_render(&r,&f,frame));
    CHECK(!r.base_valid && !comp_runtime_renderer_complete(&r,2,true));
    CHECK(comp_runtime_renderer_complete(&r,1,true)); CHECK(r.base_valid);
    memcpy(original,r.base,5000);
    f.token=2; f.kind=COMP_RUNTIME_FRAME_REACTION; f.gaze_x=199; s.value=0x77;
    CHECK(comp_runtime_renderer_render(&r,&f,frame)); CHECK(comp_runtime_renderer_complete(&r,2,false));
    CHECK(!memcmp(r.base,original,5000));
    f.token=3; f.kind=COMP_RUNTIME_FRAME_BLINK; f.blink_closed=true;
    CHECK(comp_runtime_renderer_render(&r,&f,frame)); CHECK(comp_runtime_renderer_complete(&r,3,true));
    CHECK(!memcmp(r.base,original,5000));
    for(unsigned y=16;y<200;y++) for(unsigned x=0;x<200;x++) {
        if(y>=112 && y<147 && ((x>=42 && x<69)||(x>=121 && x<148))) continue;
        CHECK((frame[y*25+x/8] & (0x80u>>(x%8)))==(original[y*25+x/8] & (0x80u>>(x%8))));
    }
    CHECK(frame[145*25+7]==0xFF && frame[145*25+16]==0xFF); /* No orphaned lower half of the eye. */
    memcpy(status_a,frame,5000);
    {
        progress_t checkpoint={0};
        comp_runtime_renderer_set_progress(&r,audio_checkpoint,&checkpoint);
        f.token=30;
        CHECK(comp_runtime_renderer_render(&r,&f,status_b));
        CHECK(checkpoint.calls>=128u); /* Four CPU-only eye scans yield by row. */
        CHECK(!memcmp(status_a,status_b,5000)); /* Same eyelids and pixel ownership. */
        CHECK(comp_runtime_renderer_complete(&r,f.token,false));
        CHECK(!memcmp(r.base,original,5000));
        checkpoint=(progress_t){0,8}; f.token=300;
        CHECK(!comp_runtime_renderer_render(&r,&f,status_b) && !r.pending);
        CHECK(checkpoint.calls==8u && !memcmp(r.base,original,5000));
        comp_runtime_renderer_set_progress(&r,NULL,NULL);
    }
    f.token=31; f.kind=COMP_RUNTIME_FRAME_STATUS;
    f.status_packed=0x8000u | (12u<<8u) | 34u;
    CHECK(comp_runtime_renderer_render(&r,&f,frame)); CHECK(comp_runtime_renderer_complete(&r,31,true));
    CHECK(!memcmp(frame+400,status_a+400,4600)); /* A clock update cannot open the eyelids. */
    f.token=32; f.kind=COMP_RUNTIME_FRAME_RECORDING_WAVE; f.recording=DENZIC_AUDIO_RECORDING_STATE_RECORDING;
    CHECK(comp_runtime_renderer_render(&r,&f,frame)); CHECK(comp_runtime_renderer_complete(&r,32,true));
    CHECK(!memcmp(frame+112*25,status_a+112*25,35*25));
    for(unsigned y=156;y<169;y++) for(unsigned x=33;x<42;x++)
        CHECK(!(frame[y*25+x/8] & (0x80u>>(x%8)))); /* White overlay cannot erase the cheek. */
    CHECK(frame[156*25]==0xC0 && frame[156*25+1]==0); /* Native y156 wave origin. */
    CHECK(!memcmp(frame+180*25,status_a+180*25,20*25)); /* No translated bottom rail. */
    CHECK(!memcmp(r.base,original,5000));
    f.recording=DENZIC_AUDIO_RECORDING_STATE_IDLE;
    f.kind=COMP_RUNTIME_FRAME_BLINK;
    f.token=4; f.blink_closed=false;
    CHECK(comp_runtime_renderer_render(&r,&f,frame)); CHECK(comp_runtime_renderer_complete(&r,4,true));
    CHECK(!memcmp(frame+400,original+400,4600));
    f.kind=COMP_RUNTIME_FRAME_HOLD;
    for(unsigned bucket=0;bucket<4u;++bucket) {
        f.token=40u+bucket; f.hold_bucket=(uint8_t)bucket;
        CHECK(comp_runtime_renderer_render(&r,&f,frame)); CHECK(comp_runtime_renderer_complete(&r,f.token,true));
        CHECK(!memcmp(frame+400,original+400,4600)); /* Preserve the actual curious face. */
        if(bucket) CHECK(memcmp(frame,status_b,400)!=0);
        memcpy(status_b,frame,5000);
    }
    f.token=44; f.hold_bucket=4;
    CHECK(!comp_runtime_renderer_render(&r,&f,frame)); CHECK(!r.pending);
    f.hold_bucket=3; f.recording=DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY;
    CHECK(comp_runtime_renderer_render(&r,&f,frame)); CHECK(comp_runtime_renderer_complete(&r,44,true));
    CHECK((frame[7*25+5] & 0xC0u)==0xC0u); /* Menu progress still visible next to the saved cue. */
    f.token=5; f.kind=COMP_RUNTIME_FRAME_STATUS; f.recording=DENZIC_AUDIO_RECORDING_STATE_RECORDING;
    CHECK(comp_runtime_renderer_render(&r,&f,frame)); CHECK(comp_runtime_renderer_complete(&r,5,true));
    CHECK(!memcmp(r.base,original,5000)); CHECK(frame[176*25]==0xC0 && frame[176*25+1]==0);
    f.token=55; f.family=COMP_BROWSER_FAMILY_WARM;
    CHECK(comp_runtime_renderer_render(&r,&f,frame)); CHECK(comp_runtime_renderer_complete(&r,55,true));
    CHECK(!memcmp(r.base,original,5000) && r.base_family==COMP_BROWSER_FAMILY_CURIOUS);
    f.token=6; f.surface=COMP_SCREEN_SURFACE_MENU; f.menu.view=COMP_SCREEN_MENU_VIEW_BROWSER_HOME;
    f.menu.language=COMP_SCREEN_MENU_LANGUAGE_ZH;
    CHECK(comp_runtime_renderer_render(&r,&f,frame)); CHECK(strstr(s.last,"menu_ui_zh_cn_s0_o0_normal")!=NULL);
    CHECK(comp_runtime_renderer_complete(&r,6,true)); CHECK(!memcmp(r.base,original,5000));
    f.menu.view=COMP_SCREEN_MENU_VIEW_BROWSER_STORAGE;
    f.menu.browser.recording_count=1;f.menu.browser.recording_storage_kb=384;
    f.token=60;CHECK(comp_runtime_renderer_render(&r,&f,status_a));CHECK(comp_runtime_renderer_complete(&r,60,true));
    f.menu.browser.recording_count=7;f.menu.browser.recording_storage_kb=915;
    f.token=61;CHECK(comp_runtime_renderer_render(&r,&f,status_b));CHECK(comp_runtime_renderer_complete(&r,61,true));
    CHECK(memcmp(status_a+VALUE_Y*25,status_b+VALUE_Y*25,VALUE_HEIGHT*25)!=0);
    CHECK(memcmp(status_a+SECOND_VALUE_Y*25,status_b+SECOND_VALUE_Y*25,VALUE_HEIGHT*25)!=0);
    for(unsigned y=16;y<200;y++)for(unsigned x=0;x<200;x++) {
        if(x>=COMP_WBA_MENU_VALUE_LEFT && x<COMP_WBA_MENU_VALUE_LEFT+COMP_WBA_MENU_VALUE_WIDTH &&
           ((y>=VALUE_Y && y<VALUE_Y+VALUE_HEIGHT) ||
            (y>=SECOND_VALUE_Y && y<SECOND_VALUE_Y+VALUE_HEIGHT)))continue;
        CHECK((status_a[y*25+x/8]&(0x80u>>(x%8)))==(status_b[y*25+x/8]&(0x80u>>(x%8))));
    }
    f.menu.browser.recording_storage_kb=4096;
    f.token=62;CHECK(comp_runtime_renderer_render(&r,&f,status_a));CHECK(comp_runtime_renderer_complete(&r,62,true));
    f.menu.browser.recording_storage_kb=8192;
    f.token=63;CHECK(comp_runtime_renderer_render(&r,&f,status_b));CHECK(comp_runtime_renderer_complete(&r,63,true));
    CHECK(memcmp(status_a+SECOND_VALUE_Y*25,status_b+SECOND_VALUE_Y*25,VALUE_HEIGHT*25)!=0); /* WBA values do not wrap at 4096KiB. */
    CHECK(!memcmp(status_a+VALUE_Y*25,status_b+VALUE_Y*25,VALUE_HEIGHT*25));
    f.menu.home_page=4;f.token=631;
    CHECK(comp_runtime_renderer_render(&r,&f,status_a));CHECK(comp_runtime_renderer_complete(&r,631,true));
    f.menu.browser.recording_count=123;f.menu.browser.recording_storage_kb=65535;f.token=632;
    CHECK(comp_runtime_renderer_render(&r,&f,status_b));CHECK(comp_runtime_renderer_complete(&r,632,true));
    CHECK(!memcmp(status_a+400,status_b+400,4600)); /* Values hidden on another whole page stay hidden. */
    f.menu.view=COMP_SCREEN_MENU_VIEW_BROWSER_CLEAR_RECORDINGS;f.menu.home_page=0;
    f.menu.browser.recording_count=7;f.token=64;
    CHECK(comp_runtime_renderer_render(&r,&f,status_a));CHECK(comp_runtime_renderer_complete(&r,64,true));
    f.menu.browser.recording_count=0;f.token=65;
    CHECK(comp_runtime_renderer_render(&r,&f,status_b));CHECK(comp_runtime_renderer_complete(&r,65,true));
    CHECK(memcmp(status_a+COMP_WBA_CONFIRM_COUNT_TOP*25,status_b+COMP_WBA_CONFIRM_COUNT_TOP*25,COMP_WBA_COUNT_HEIGHT*25)!=0);
    /* Real bilingual values replace the recording menu placeholder. */
    f.menu.view=COMP_SCREEN_MENU_VIEW_BROWSER_VOICE;f.menu.home_page=0;
    f.recording=DENZIC_AUDIO_RECORDING_STATE_IDLE;f.token=70;
    CHECK(comp_runtime_renderer_render(&r,&f,status_a));CHECK(comp_runtime_renderer_complete(&r,70,true));
    f.recording=DENZIC_AUDIO_RECORDING_STATE_RECORDING;f.token=71;
    CHECK(comp_runtime_renderer_render(&r,&f,status_b));CHECK(comp_runtime_renderer_complete(&r,71,true));
    CHECK(memcmp(status_a+VALUE_Y*25,status_b+VALUE_Y*25,VALUE_HEIGHT*25)!=0);
    for(unsigned y=16;y<200;y++)for(unsigned x=0;x<200;x++) {
        if(x>=COMP_WBA_MENU_VALUE_LEFT && x<COMP_WBA_MENU_VALUE_LEFT+COMP_WBA_MENU_VALUE_WIDTH &&
           y>=VALUE_Y && y<VALUE_Y+VALUE_HEIGHT)continue;
        CHECK((status_a[y*25+x/8]&(0x80u>>(x%8)))==(status_b[y*25+x/8]&(0x80u>>(x%8))));
    }
    f.menu.language=COMP_SCREEN_MENU_LANGUAGE_EN;f.token=72;
    CHECK(comp_runtime_renderer_render(&r,&f,status_a));CHECK(comp_runtime_renderer_complete(&r,72,true));
    CHECK(memcmp(status_a+VALUE_Y*25,status_b+VALUE_Y*25,VALUE_HEIGHT*25)!=0);
    f.recording=DENZIC_AUDIO_RECORDING_STATE_IDLE;f.last_result=COMP_RUNTIME_BACKEND_FAILED;f.token=721;
    CHECK(comp_runtime_renderer_render(&r,&f,status_b));CHECK(comp_runtime_renderer_complete(&r,721,true));
    CHECK(memcmp(status_a+(COMP_WBA_MENU_ROW_TOP+COMP_WBA_MENU_STACK_VALUE_TOP)*25,
                 status_b+(COMP_WBA_MENU_ROW_TOP+COMP_WBA_MENU_STACK_VALUE_TOP)*25,VALUE_HEIGHT*25)!=0);
    for(unsigned y=16;y<200;y++)for(unsigned x=0;x<200;x++) {
        if(x>=COMP_WBA_MENU_STACK_VALUE_LEFT && x<COMP_WBA_MENU_STACK_VALUE_LEFT+COMP_WBA_MENU_STACK_VALUE_WIDTH &&
           y>=COMP_WBA_MENU_ROW_TOP+COMP_WBA_MENU_STACK_VALUE_TOP &&
           y<COMP_WBA_MENU_ROW_TOP+COMP_WBA_MENU_STACK_VALUE_TOP+VALUE_HEIGHT)continue;
        CHECK((status_a[y*25+x/8]&(0x80u>>(x%8)))==(status_b[y*25+x/8]&(0x80u>>(x%8))));
    }
    f.last_result=COMP_RUNTIME_OK;
    f.menu.home_page=4;f.token=73;
    CHECK(comp_runtime_renderer_render(&r,&f,status_a));CHECK(comp_runtime_renderer_complete(&r,73,true));
    f.recording=DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY;f.token=74;
    CHECK(comp_runtime_renderer_render(&r,&f,status_b));CHECK(comp_runtime_renderer_complete(&r,74,true));
    CHECK(!memcmp(status_a+400,status_b+400,4600)); /* Offscreen state never overwrites another row. */
    f.menu.view=COMP_SCREEN_MENU_VIEW_BROWSER_POWER;f.menu.home_page=0;
    f.status_packed=0;f.token=75;
    CHECK(comp_runtime_renderer_render(&r,&f,status_a));CHECK(comp_runtime_renderer_complete(&r,75,true));
    f.status_packed=(1u<<17)|(75u<<24);f.token=76;
    CHECK(comp_runtime_renderer_render(&r,&f,status_b));CHECK(comp_runtime_renderer_complete(&r,76,true));
    CHECK(memcmp(status_a+VALUE_Y*25,status_b+VALUE_Y*25,VALUE_HEIGHT*25)!=0);
    f.status_packed=(1u<<17)|(255u<<24);f.token=77;
    CHECK(comp_runtime_renderer_render(&r,&f,frame));CHECK(comp_runtime_renderer_complete(&r,77,true));
    CHECK(!memcmp(frame+VALUE_Y*25,status_a+VALUE_Y*25,VALUE_HEIGHT*25)); /* Invalid battery remains unknown. */
    f.surface=COMP_SCREEN_SURFACE_HOME;f.recording=DENZIC_AUDIO_RECORDING_STATE_IDLE;
    f.status_packed=0;f.token=78;
    CHECK(comp_runtime_renderer_render(&r,&f,status_a));CHECK(comp_runtime_renderer_complete(&r,78,true));
    f.status_packed=(1u<<17);f.token=79;
    CHECK(comp_runtime_renderer_render(&r,&f,status_b));CHECK(comp_runtime_renderer_complete(&r,79,true));
    CHECK((status_a[8*25+22]&7u)==7u && (status_b[8*25+22]&7u)==0u);
    CHECK(!memcmp(status_a+400,status_b+400,4600));
    f.status_packed=(1u<<17)|(100u<<24)|(1u<<16);f.token=80;
    CHECK(comp_runtime_renderer_render(&r,&f,frame));CHECK(comp_runtime_renderer_complete(&r,80,true));
    for(unsigned y=6;y<11;y++)for(unsigned x=177;x<191;x++)CHECK(frame[y*25+x/8]&(0x80u>>(x%8)));
    for(unsigned y=16;y<200;y++)CHECK(!memcmp(frame+y*25,status_a+y*25,25));
    for(unsigned y=0;y<16;y++)for(unsigned x=195;x<200;x++)CHECK(!(frame[y*25+x/8]&(0x80u>>(x%8))));
    /* Operation results own only their static message strip. A pending or
     * failed operation cannot erase counts, settings, confirmation targets
     * or the face. Exercise every authored message in all three languages. */
    f.surface=COMP_SCREEN_SURFACE_MENU;f.status_packed=0;f.last_result=COMP_RUNTIME_OK;
    const comp_screen_menu_view_t feedback_views[]={COMP_SCREEN_MENU_VIEW_BROWSER_STORAGE,
        COMP_SCREEN_MENU_VIEW_BROWSER_CLEAR_RECORDINGS,COMP_SCREEN_MENU_VIEW_BROWSER_RESTORE_DEFAULTS};
    for(unsigned locale=0;locale<3u;++locale)for(unsigned v=0;v<3u;++v) {
        f.menu.language=(comp_screen_menu_language_t)locale;f.menu.view=feedback_views[v];
        f.menu.home_page=0;f.menu.browser.recording_count=7;f.menu_feedback=COMP_RUNTIME_MENU_FEEDBACK_NONE;
        ++f.token;CHECK(comp_runtime_renderer_render(&r,&f,status_a));CHECK(comp_runtime_renderer_complete(&r,f.token,true));
        for(unsigned feedback=1;feedback<=COMP_RUNTIME_MENU_FEEDBACK_TIMEOUT;++feedback) {
            f.menu_feedback=(comp_runtime_menu_feedback_t)feedback;
            ++f.token;CHECK(comp_runtime_renderer_render(&r,&f,status_b));CHECK(comp_runtime_renderer_complete(&r,f.token,true));
            CHECK(memcmp(status_a,status_b,5000)!=0);
            const unsigned top=v?142u:186u,bottom=v?160u:200u;
            for(unsigned y=0;y<200;y++)for(unsigned x=0;x<200;x++) {
                if(x>=12u && x<188u && y>=top && y<bottom)continue;
                CHECK((status_a[y*25+x/8]&(0x80u>>(x%8)))==(status_b[y*25+x/8]&(0x80u>>(x%8))));
            }
        }
    }
    f.menu_feedback=(comp_runtime_menu_feedback_t)255;f.token++;
    CHECK(!comp_runtime_renderer_render(&r,&f,frame) && !r.pending);
    f.surface=COMP_SCREEN_SURFACE_HOME;f.menu_feedback=COMP_RUNTIME_MENU_FEEDBACK_NONE;
    ++f.token;CHECK(comp_runtime_renderer_render(&r,&f,status_a));CHECK(comp_runtime_renderer_complete(&r,f.token,true));
    f.menu_feedback=COMP_RUNTIME_MENU_FEEDBACK_RETRYING;
    ++f.token;CHECK(comp_runtime_renderer_render(&r,&f,status_b));CHECK(comp_runtime_renderer_complete(&r,f.token,true));
    CHECK(!memcmp(status_a,status_b,5000));
    f.menu_feedback=COMP_RUNTIME_MENU_FEEDBACK_NONE;
    f.surface=COMP_SCREEN_SURFACE_MENU;s.fail=true; f.token=7; CHECK(!comp_runtime_renderer_render(&r,&f,frame)); CHECK(!r.pending);
    memset(status_a,0xFF,5000); memcpy(status_b,status_a,5000);
    CHECK(comp_screen_menu_render_status_bar(0,status_a,5000,200,200));
    CHECK(comp_screen_menu_render_status_bar(COMP_SCREEN_STATUS_REQUIRE_MEASURED_BATTERY,status_b,5000,200,200));
    CHECK(memcmp(status_a,status_b,400)!=0); CHECK(!memcmp(status_a+400,status_b+400,4600));
    CHECK((status_b[4u*25u+23u]&0xE0u)==0xE0u); /* '?' has ink, rather than an empty/dead battery. */
    memset(status_a,255,5000);memcpy(status_b,status_a,5000);
    CHECK(comp_screen_menu_render_status_bar(COMP_SCREEN_STATUS_EXTERNAL_POWER,status_a,5000,200,200));
    CHECK(comp_screen_menu_render_status_bar(COMP_SCREEN_STATUS_EXTERNAL_POWER|COMP_SCREEN_STATUS_CHARGER_FAULT,status_b,5000,200,200));
    CHECK(memcmp(status_a,status_b,400)!=0 && !memcmp(status_a+400,status_b+400,4600));
    for (unsigned y=0;y<16;y++)for (unsigned x=0;x<200;x++) {
        if (x>=168 && x<=173) continue;
        CHECK((status_a[y*25+x/8]&(0x80u>>(x%8)))==(status_b[y*25+x/8]&(0x80u>>(x%8))));
    }
    puts("PASS_PREHARDWARE_RENDERER: committed face, failed render, blink held through clock/wave, emotion-preserving four-stage hold, nonverbal status, unknown battery; synthetic masks only");
    return 0;
}
