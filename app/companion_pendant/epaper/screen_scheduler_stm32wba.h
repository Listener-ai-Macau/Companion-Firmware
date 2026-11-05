#ifndef COMPANION_EPAPER_SCREEN_SCHEDULER_STM32WBA_H
#define COMPANION_EPAPER_SCREEN_SCHEDULER_STM32WBA_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef void (*companion_epaper_stm32wba_schedule_fn_t)(void *context);
typedef void (*companion_epaper_stm32wba_timer_fn_t)(void *context,
                                                     uint32_t delay_ms);
typedef uint32_t (*companion_epaper_stm32wba_now_ms_fn_t)(void *context);

/* Independent producers share one wake timer, never one mutable deadline.
 * These slots request work; display_queue still owns physical ordering. */
typedef enum {
    COMPANION_WBA_SCREEN_TICK_EXPRESSION = 0,
    COMPANION_WBA_SCREEN_TICK_LIFE,
    COMPANION_WBA_SCREEN_TICK_BLINK,
    COMPANION_WBA_SCREEN_TICK_RECORDING,
    COMPANION_WBA_SCREEN_TICK_CHARGING,
    COMPANION_WBA_SCREEN_TICK_COUNT,
} companion_epaper_stm32wba_tick_t;

#define COMPANION_WBA_SCREEN_TICK_MASK(tick) (UINT32_C(1) << (tick))

typedef struct {
    companion_epaper_stm32wba_schedule_fn_t schedule_display_task;
    companion_epaper_stm32wba_timer_fn_t start_expression_tick_timer;
    companion_epaper_stm32wba_schedule_fn_t stop_expression_tick_timer;
    companion_epaper_stm32wba_now_ms_fn_t now_ms;
    void *context;
} companion_epaper_stm32wba_scheduler_config_t;

typedef struct {
    companion_epaper_stm32wba_scheduler_config_t config;
    uint32_t deadlines_ms[COMPANION_WBA_SCREEN_TICK_COUNT];
    uint32_t active_mask;
    uint32_t armed_deadline_ms;
    bool timer_armed;
    bool immediate_wake_pending;
} companion_epaper_stm32wba_scheduler_t;

void companion_epaper_stm32wba_scheduler_init(
    companion_epaper_stm32wba_scheduler_t *scheduler,
    const companion_epaper_stm32wba_scheduler_config_t *config);

bool companion_epaper_stm32wba_scheduler_ready(
    const companion_epaper_stm32wba_scheduler_t *scheduler);

uint32_t companion_epaper_stm32wba_now_ms(
    const companion_epaper_stm32wba_scheduler_t *scheduler);

void companion_epaper_stm32wba_schedule_display_task(
    companion_epaper_stm32wba_scheduler_t *scheduler);

void companion_epaper_stm32wba_schedule_expression_tick(
    companion_epaper_stm32wba_scheduler_t *scheduler,
    uint32_t remaining_ms);

/* All mutation runs in the display actor, not an ISR. The one-shot timer
 * callback only posts schedule_display_task; the actor then calls take_due.
 * now_ms must stay monotonic through sleep. Delays and time between servicing
 * an active deadline must be <= INT32_MAX ms (wraparound-safe half range).
 * Replacing/cancelling one producer cannot postpone another producer. */
bool companion_epaper_stm32wba_schedule_tick(
    companion_epaper_stm32wba_scheduler_t *scheduler,
    companion_epaper_stm32wba_tick_t tick,
    uint32_t delay_ms);
void companion_epaper_stm32wba_cancel_tick(
    companion_epaper_stm32wba_scheduler_t *scheduler,
    companion_epaper_stm32wba_tick_t tick);
uint32_t companion_epaper_stm32wba_take_due(
    companion_epaper_stm32wba_scheduler_t *scheduler);
void companion_epaper_stm32wba_cancel_all_ticks(
    companion_epaper_stm32wba_scheduler_t *scheduler);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_SCREEN_SCHEDULER_STM32WBA_H */
