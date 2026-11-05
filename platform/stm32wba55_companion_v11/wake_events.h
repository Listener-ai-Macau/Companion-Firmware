#ifndef COMPANION_V11_WAKE_EVENTS_H
#define COMPANION_V11_WAKE_EVENTS_H

#include <stddef.h>
#include <stdint.h>

/* PC13 is the active-low TCA6408 interrupt aggregator and PB14 is the
 * active-low key on Companion V1.1. Interrupt handlers only latch these
 * events. I2C/SPI and product state remain foreground-owned. */
enum {
    COMP_V11_WAKE_TCA_FALLING = 1u << 0,
    COMP_V11_WAKE_KEY_FALLING = 1u << 1,
    COMP_V11_WAKE_KEY_RISING = 1u << 2,
};

typedef struct {
    volatile uint32_t pending;
    volatile uint32_t tca_falling_count;
    volatile uint32_t key_falling_count;
    volatile uint32_t key_rising_count;
    volatile uint32_t key_down_ms, key_up_ms, key_pending;
} comp_v11_wake_events_t;
_Static_assert(sizeof(comp_v11_wake_events_t)==28u,"key timing adds only three words");

static inline void comp_v11_wake_events_init(comp_v11_wake_events_t *events)
{
    if (events == NULL) {
        return;
    }
    events->pending = 0u;
    events->tca_falling_count = 0u;
    events->key_falling_count = 0u;
    events->key_rising_count = 0u;
    events->key_down_ms = events->key_up_ms = events->key_pending = 0u;
}

static inline void comp_v11_wake_events_note_isr(comp_v11_wake_events_t *events,
                                                  uint32_t flags)
{
    if (events == NULL) {
        return;
    }
    events->pending |= flags;
    if ((flags & COMP_V11_WAKE_TCA_FALLING) != 0u) {
        events->tca_falling_count++;
    }
    if ((flags & COMP_V11_WAKE_KEY_FALLING) != 0u) {
        events->key_falling_count++;
    }
    if ((flags & COMP_V11_WAKE_KEY_RISING) != 0u) {
        events->key_rising_count++;
    }
}

/* Key timing survives an entire press between two foreground polls. The
 * separate latch is not consumed by the generic wake-only exchange. */
static inline void comp_v11_wake_events_note_key_isr(
    comp_v11_wake_events_t *events, uint32_t flag, uint32_t now)
{
    if (events == NULL) return;
    if (flag == COMP_V11_WAKE_KEY_FALLING) events->key_down_ms = now;
    else if (flag == COMP_V11_WAKE_KEY_RISING) events->key_up_ms = now;
    else return;
    events->key_pending |= flag;
    comp_v11_wake_events_note_isr(events,flag);
}

/* The foreground caller must mask the two EXTI IRQs (or all IRQs) around
 * this exchange so an ISR event cannot land between the load and clear. */
static inline uint32_t comp_v11_wake_events_take_critical(
    comp_v11_wake_events_t *events)
{
    uint32_t pending;

    if (events == NULL) {
        return 0u;
    }
    pending = events->pending;
    events->pending = 0u;
    return pending;
}

#endif /* COMPANION_V11_WAKE_EVENTS_H */
