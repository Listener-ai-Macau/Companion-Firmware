#include "wake_events.h"

#include <stdio.h>

static int fail(const char *message)
{
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

int main(void)
{
    comp_v11_wake_events_t events;
    uint32_t pending;

    comp_v11_wake_events_init(&events);
    if (events.pending != 0u || events.tca_falling_count != 0u ||
        events.key_falling_count != 0u || events.key_rising_count != 0u) {
        return fail("initial state");
    }

    /* A level-aggregated TCA IRQ may represent several expander inputs. The
     * latch coalesces foreground work while retaining diagnostic edge counts. */
    comp_v11_wake_events_note_isr(&events, COMP_V11_WAKE_TCA_FALLING);
    comp_v11_wake_events_note_isr(&events, COMP_V11_WAKE_TCA_FALLING);
    comp_v11_wake_events_note_isr(&events, COMP_V11_WAKE_KEY_FALLING);
    pending = comp_v11_wake_events_take_critical(&events);
    if (pending != (COMP_V11_WAKE_TCA_FALLING | COMP_V11_WAKE_KEY_FALLING) ||
        events.pending != 0u || events.tca_falling_count != 2u ||
        events.key_falling_count != 1u) {
        return fail("coalesced sources and diagnostic counts");
    }

    comp_v11_wake_events_note_isr(&events, COMP_V11_WAKE_KEY_RISING);
    if (comp_v11_wake_events_take_critical(&events) != COMP_V11_WAKE_KEY_RISING ||
        comp_v11_wake_events_take_critical(&events) != 0u ||
        events.key_rising_count != 1u) {
        return fail("take clears only pending state");
    }

    comp_v11_wake_events_note_key_isr(&events,COMP_V11_WAKE_KEY_FALLING,1000u);
    comp_v11_wake_events_note_key_isr(&events,COMP_V11_WAKE_KEY_RISING,2080u);
    pending=comp_v11_wake_events_take_critical(&events);
    if(pending!=(COMP_V11_WAKE_KEY_FALLING|COMP_V11_WAKE_KEY_RISING) ||
       events.key_pending!=pending || events.key_down_ms!=1000u || events.key_up_ms!=2080u ||
       events.key_falling_count!=2u || events.key_rising_count!=2u) {
        return fail("physical key timing survives generic foreground wake take");
    }
    comp_v11_wake_events_note_key_isr(&events,COMP_V11_WAKE_TCA_FALLING,3000u);
    if(events.pending!=0u || events.key_down_ms!=1000u || events.key_up_ms!=2080u) {
        return fail("non-key source cannot overwrite physical key timing");
    }
    comp_v11_wake_events_note_key_isr(NULL,COMP_V11_WAKE_KEY_FALLING,1000u);
    comp_v11_wake_events_note_isr(NULL, COMP_V11_WAKE_TCA_FALLING);
    if (comp_v11_wake_events_take_critical(NULL) != 0u) {
        return fail("null safety");
    }

    printf("PASS_HOST_ONLY: WBA wake ISR latch coalesces TCA/key edges; "
           "foreground critical take preserves source counters\n");
    return 0;
}
