#include "wba_button.h"
#include <stddef.h>
void comp_wba_button_init(comp_wba_button_t *b, bool raw, uint32_t now)
{
    if (b) *b=(comp_wba_button_t){.changed_ms=now,.raw=raw,.pressed=raw,.consumed=raw,.wake_only=raw};
}
uint8_t comp_wba_button_poll_with_hold(comp_wba_button_t *b, bool raw,
    bool sleeping, bool enable_double, uint16_t hold_ms, uint32_t now)
{
    uint8_t event=0u;
    if (!b) return event;
    if (b->double_enabled!=enable_double) {
        /* Either context transition retires the whole existing press. An UP
         * that began in a recorder/menu context must not become a HOME
         * refresh, and a HOME press must not pause a new recording. */
        if (b->raw || b->pressed) { b->consumed=true; b->wake_only=true; }
        b->click_pending=false; b->second_press=false;
    }
    if (!enable_double) { b->click_pending=false; b->second_press=false; }
    b->double_enabled=enable_double;
    if (raw != b->raw) {
        /* Classify the completed hold BEFORE replacing its DOWN timestamp.
         * Foreground work may span the threshold, with UP as the next sample.
         * A long hold must not disappear merely because no poll saw it held
         * at the hold threshold. Consumed/wake-only presses still cannot toggle. */
        if(!raw && b->raw) {
            uint32_t held=now-b->changed_ms;
            if(held>b->max_hold_ms)b->max_hold_ms=(uint16_t)(held>65535u?65535u:held);
            if(held>=hold_ms && !b->consumed && !b->wake_only) {
                b->consumed=true;b->click_pending=false;b->second_press=false;
                event|=COMP_WBA_BUTTON_RECORD_TOGGLE;
            }
        }
        b->raw=raw; b->changed_ms=now;
        /* Capture at the edge, before waking changes the product surface. */
        if (raw && !b->pressed) {
            b->wake_only=sleeping;
            b->consumed=sleeping;
            b->second_press=enable_double && b->click_pending &&
                now-b->click_ms<320u;
        } else if (!raw && !b->pressed) {
            /* An unqualified second DOWN was electrical bounce, not a
             * second click. Let the first accepted click expire normally. */
            b->second_press=false;
        }
    }
    if (now-b->changed_ms >= 30u && b->pressed != b->raw) {
        b->pressed=b->raw;
        if (b->pressed) { b->consumed=b->wake_only; event|=COMP_WBA_BUTTON_WAKE; }
        else {
            if (!b->consumed) {
                if (!enable_double) event|=COMP_WBA_BUTTON_CONFIRM;
                else if (b->second_press) {
                    event|=COMP_WBA_BUTTON_DOUBLE_CONFIRM; b->click_pending=false;
                } else { b->click_pending=true; b->click_ms=now; }
            }
            b->consumed=false; b->wake_only=false; b->second_press=false;
        }
    }
    if (b->pressed && b->raw && !b->consumed && now-b->changed_ms >= hold_ms) {
        b->consumed=true; b->click_pending=false; b->second_press=false;
        event|=COMP_WBA_BUTTON_RECORD_TOGGLE;
    }
    if (enable_double && b->click_pending && !b->second_press &&
        now-b->click_ms>=320u) {
        b->click_pending=false; event|=COMP_WBA_BUTTON_CONFIRM;
    }
    if(event)b->last_event=event;
    return event;
}
uint8_t comp_wba_button_poll_with_double(comp_wba_button_t *b, bool raw,
    bool sleeping, bool enable_double, uint32_t now)
{ return comp_wba_button_poll_with_hold(b,raw,sleeping,enable_double,700u,now); }
uint8_t comp_wba_button_poll_edges(comp_wba_button_t *b,
    const comp_wba_button_edges_t *edge, uint16_t hold_ms, uint32_t now)
{
    if(!b || !edge)return 0u;
    uint8_t event=0u;
    const bool down=(edge->flags&COMP_WBA_BUTTON_EDGE_DOWN)!=0u;
    const bool up=(edge->flags&COMP_WBA_BUTTON_EDGE_UP)!=0u;
    if(down && up && (int32_t)(edge->up_ms-edge->down_ms)<0) {
        /* A previous release followed by a new press, not a wrapped hold. */
        event|=comp_wba_button_poll_with_hold(b,false,false,false,hold_ms,edge->up_ms);
        event|=comp_wba_button_poll_with_hold(b,b->raw,false,false,hold_ms,edge->down_ms);
        event|=comp_wba_button_poll_with_hold(b,true,false,false,hold_ms,edge->down_ms);
    } else {
        if(down) {
            event|=comp_wba_button_poll_with_hold(b,b->raw,false,false,hold_ms,edge->down_ms);
            event|=comp_wba_button_poll_with_hold(b,true,false,false,hold_ms,edge->down_ms);
            if(up && edge->up_ms-edge->down_ms>=30u)
                event|=comp_wba_button_poll_with_hold(b,true,false,false,hold_ms,edge->down_ms+30u);
        }
        if(up)event|=comp_wba_button_poll_with_hold(b,false,false,false,hold_ms,edge->up_ms);
    }
    event|=comp_wba_button_poll_with_hold(b,edge->raw_pressed,false,false,hold_ms,now);
    return event;
}
uint8_t comp_wba_button_poll(comp_wba_button_t *b, bool raw, bool sleeping, uint32_t now)
{ return comp_wba_button_poll_with_double(b,raw,sleeping,false,now); }
bool comp_wba_button_busy(const comp_wba_button_t *b)
{ return b && (b->raw || b->pressed || b->click_pending); }
