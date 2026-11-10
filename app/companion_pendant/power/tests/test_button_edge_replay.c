#include "wba_button.h"
#include <stdio.h>

#define CHECK(condition) do { if (!(condition)) { \
    fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#condition);return 1; } } while (0)

static uint8_t sample(comp_wba_button_t *b,bool pressed,uint32_t now)
{
    const comp_wba_button_edges_t e={0u,0u,0u,pressed};
    return comp_wba_button_poll_transitions(b,&e,now);
}

int main(void)
{
    comp_wba_button_t b;
    comp_wba_button_init(&b,false,0u);
    CHECK(sample(&b,true,100u)==0u);
    CHECK(sample(&b,true,130u)&COMP_WBA_BUTTON_DOWN);
    CHECK(sample(&b,false,200u)==0u);
    CHECK(sample(&b,false,230u)&COMP_WBA_BUTTON_UP);
    /* IRQ publication can arrive after the foreground has already sampled
     * these levels. Replaying that completed press again creates a second
     * recorder toggle, or another empty desktop START/STOP. */
    const comp_wba_button_edges_t delayed={100u,200u,
        COMP_WBA_BUTTON_EDGE_DOWN|COMP_WBA_BUTTON_EDGE_UP,false};
    CHECK(comp_wba_button_poll_transitions(&b,&delayed,260u)==0u);
    CHECK(comp_wba_button_poll_transitions(&b,&delayed,300u)==0u);
    CHECK(sample(&b,false,340u)==0u);

    /* A genuinely unseen completed press must survive foreground work. */
    const comp_wba_button_edges_t fresh={400u,480u,
        COMP_WBA_BUTTON_EDGE_DOWN|COMP_WBA_BUTTON_EDGE_UP,false};
    uint8_t keys=comp_wba_button_poll_transitions(&b,&fresh,520u);
    CHECK((keys&(COMP_WBA_BUTTON_DOWN|COMP_WBA_BUTTON_UP))==
          (COMP_WBA_BUTTON_DOWN|COMP_WBA_BUTTON_UP));
    CHECK(comp_wba_button_poll_transitions(&b,&fresh,560u)==0u);

    /* Ringing first sampled as a level must not mature a backwards clock. */
    CHECK(sample(&b,true,600u)==0u);
    const comp_wba_button_edges_t chatter={590u,595u,
        COMP_WBA_BUTTON_EDGE_DOWN|COMP_WBA_BUTTON_EDGE_UP,true};
    CHECK(comp_wba_button_poll_transitions(&b,&chatter,610u)==0u);
    CHECK(sample(&b,true,630u)&COMP_WBA_BUTTON_DOWN);
    CHECK(sample(&b,false,700u)==0u);
    CHECK(sample(&b,false,730u)&COMP_WBA_BUTTON_UP);
    CHECK(sample(&b,false,780u)==0u);

    comp_wba_button_init(&b,false,UINT32_MAX-200u);
    const comp_wba_button_edges_t wrap={UINT32_MAX-50u,40u,
        COMP_WBA_BUTTON_EDGE_DOWN|COMP_WBA_BUTTON_EDGE_UP,false};
    keys=comp_wba_button_poll_transitions(&b,&wrap,80u);
    CHECK((keys&(COMP_WBA_BUTTON_DOWN|COMP_WBA_BUTTON_UP))==
          (COMP_WBA_BUTTON_DOWN|COMP_WBA_BUTTON_UP));
    CHECK(comp_wba_button_poll_transitions(&b,&wrap,120u)==0u);
    _Static_assert(sizeof(comp_wba_button_t)==12u,"retain button RAM layout");
    puts("PASS late IRQs cannot replay accepted physical input; unseen press, debounce, tick wrap and12B state retained");
    return 0;
}
