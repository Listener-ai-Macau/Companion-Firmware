#include "screen_menu.h"
#include <stdio.h>
#define CHECK(c) do { if(!(c)) {fprintf(stderr,"FAIL:%d: %s\n",__LINE__,#c);return 1;} } while(0)
int main(void)
{
    comp_screen_menu_t m;
    comp_screen_menu_result_t r;
    comp_touch_gesture_event_t left={.type=COMP_TOUCH_GESTURE_SWIPE_LEFT};
    comp_touch_gesture_event_t right={.type=COMP_TOUCH_GESTURE_SWIPE_RIGHT};
    comp_screen_menu_init(&m);
    CHECK(comp_screen_menu_navigate_to(&m,COMP_SCREEN_MENU_VIEW_BROWSER_HOME));
    r=comp_screen_menu_gesture(&m,&left);
    CHECK(r.changed && m.home_page==4u && r.action==COMP_SCREEN_MENU_ACTION_NONE);
    r=comp_screen_menu_gesture(&m,&left);
    CHECK(!r.changed && m.home_page==4u);
    r=comp_screen_menu_gesture(&m,&right);
    CHECK(r.changed && m.home_page==0u && r.action==COMP_SCREEN_MENU_ACTION_NONE);
    r=comp_screen_menu_gesture(&m,&right);
    CHECK(r.changed && r.action==COMP_SCREEN_MENU_ACTION_EXIT_DAILY);

    /* Returning a child restores the parent's actual page. Reaching page0
     * and leaving it require separate physical gestures. */
    r=comp_screen_menu_gesture(&m,&left); CHECK(m.home_page==4u);
    CHECK(comp_screen_menu_navigate_to(&m,COMP_SCREEN_MENU_VIEW_BROWSER_VOICE));
    CHECK(m.home_page==0u && m.navigation_depth==1u);
    r=comp_screen_menu_gesture(&m,&left); CHECK(r.changed && m.home_page>0u);
    r=comp_screen_menu_gesture(&m,&right);
    CHECK(r.changed && m.home_page==0u && m.view==COMP_SCREEN_MENU_VIEW_BROWSER_VOICE);
    r=comp_screen_menu_gesture(&m,&right);
    CHECK(r.changed && r.action==COMP_SCREEN_MENU_ACTION_NONE && m.view==COMP_SCREEN_MENU_VIEW_BROWSER_HOME && m.home_page==4u && m.navigation_depth==0u);
    r=comp_screen_menu_gesture(&m,&right); CHECK(m.home_page==0u && r.action==COMP_SCREEN_MENU_ACTION_NONE);
    r=comp_screen_menu_gesture(&m,&right); CHECK(r.action==COMP_SCREEN_MENU_ACTION_EXIT_DAILY);

    /* Original non-browser right-swipe exit remains intact. */
    m.view=COMP_SCREEN_MENU_VIEW_PHONE;
    r=comp_screen_menu_gesture(&m,&right); CHECK(r.action==COMP_SCREEN_MENU_ACTION_EXIT_DAILY);
    puts("PASS: right swipe pages back first, another right at page0 returns/exits, parent page restored; host only");
    return 0;
}
