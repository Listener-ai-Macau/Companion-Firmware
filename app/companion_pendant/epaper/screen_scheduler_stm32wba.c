#include "screen_scheduler_stm32wba.h"

#include <string.h>

static bool tick_valid(companion_epaper_stm32wba_tick_t tick)
{
    return (unsigned)tick < (unsigned)COMPANION_WBA_SCREEN_TICK_COUNT;
}

static bool deadline_due(uint32_t now_ms, uint32_t deadline_ms)
{
    return now_ms - deadline_ms <= (uint32_t)INT32_MAX;
}

static void stop_timer(companion_epaper_stm32wba_scheduler_t *scheduler)
{
    if (scheduler->timer_armed) {
        scheduler->config.stop_expression_tick_timer(scheduler->config.context);
        scheduler->timer_armed = false;
    }
}

static void arm_earliest(companion_epaper_stm32wba_scheduler_t *scheduler,
                         uint32_t now_ms)
{
    uint32_t shortest = UINT32_MAX;
    uint32_t earliest = 0u;
    for (unsigned tick = 0u; tick < (unsigned)COMPANION_WBA_SCREEN_TICK_COUNT; ++tick) {
        uint32_t deadline;
        uint32_t remaining;
        if ((scheduler->active_mask & COMPANION_WBA_SCREEN_TICK_MASK(tick)) == 0u) {
            continue;
        }
        deadline = scheduler->deadlines_ms[tick];
        remaining = deadline_due(now_ms, deadline) ? 0u : deadline - now_ms;
        if (remaining < shortest) {
            shortest = remaining;
            earliest = deadline;
        }
    }
    if (shortest == UINT32_MAX || shortest == 0u) {
        stop_timer(scheduler);
        if (shortest == 0u && !scheduler->immediate_wake_pending) {
            scheduler->immediate_wake_pending = true;
            companion_epaper_stm32wba_schedule_display_task(scheduler);
        }
        return;
    }
    if (scheduler->timer_armed && scheduler->armed_deadline_ms == earliest) {
        return;
    }
    stop_timer(scheduler);
    scheduler->armed_deadline_ms = earliest;
    scheduler->timer_armed = true;
    scheduler->config.start_expression_tick_timer(scheduler->config.context, shortest);
}

void companion_epaper_stm32wba_scheduler_init(
    companion_epaper_stm32wba_scheduler_t *scheduler,
    const companion_epaper_stm32wba_scheduler_config_t *config)
{
    if (scheduler == NULL) {
        return;
    }
    memset(scheduler, 0, sizeof(*scheduler));
    if (config != NULL) {
        scheduler->config = *config;
    }
}

bool companion_epaper_stm32wba_scheduler_ready(
    const companion_epaper_stm32wba_scheduler_t *scheduler)
{
    return scheduler != NULL &&
           scheduler->config.schedule_display_task != NULL &&
           scheduler->config.start_expression_tick_timer != NULL &&
           scheduler->config.stop_expression_tick_timer != NULL &&
           scheduler->config.now_ms != NULL;
}

uint32_t companion_epaper_stm32wba_now_ms(
    const companion_epaper_stm32wba_scheduler_t *scheduler)
{
    if (scheduler == NULL || scheduler->config.now_ms == NULL) {
        return 0u;
    }
    return scheduler->config.now_ms(scheduler->config.context);
}

void companion_epaper_stm32wba_schedule_display_task(
    companion_epaper_stm32wba_scheduler_t *scheduler)
{
    if (scheduler == NULL || scheduler->config.schedule_display_task == NULL) {
        return;
    }
    scheduler->config.schedule_display_task(scheduler->config.context);
}

void companion_epaper_stm32wba_schedule_expression_tick(
    companion_epaper_stm32wba_scheduler_t *scheduler,
    uint32_t remaining_ms)
{
    (void)companion_epaper_stm32wba_schedule_tick(
        scheduler, COMPANION_WBA_SCREEN_TICK_EXPRESSION, remaining_ms);
}

bool companion_epaper_stm32wba_schedule_tick(
    companion_epaper_stm32wba_scheduler_t *scheduler,
    companion_epaper_stm32wba_tick_t tick,
    uint32_t delay_ms)
{
    uint32_t now_ms;
    if (!companion_epaper_stm32wba_scheduler_ready(scheduler) ||
        !tick_valid(tick) || delay_ms > (uint32_t)INT32_MAX) {
        return false;
    }
    now_ms = companion_epaper_stm32wba_now_ms(scheduler);
    scheduler->deadlines_ms[tick] = now_ms + delay_ms;
    scheduler->active_mask |= COMPANION_WBA_SCREEN_TICK_MASK(tick);
    arm_earliest(scheduler, now_ms);
    return true;
}

void companion_epaper_stm32wba_cancel_tick(
    companion_epaper_stm32wba_scheduler_t *scheduler,
    companion_epaper_stm32wba_tick_t tick)
{
    if (!companion_epaper_stm32wba_scheduler_ready(scheduler) || !tick_valid(tick)) {
        return;
    }
    scheduler->active_mask &= ~COMPANION_WBA_SCREEN_TICK_MASK(tick);
    arm_earliest(scheduler, companion_epaper_stm32wba_now_ms(scheduler));
}

uint32_t companion_epaper_stm32wba_take_due(
    companion_epaper_stm32wba_scheduler_t *scheduler)
{
    uint32_t due = 0u;
    uint32_t now_ms;
    if (!companion_epaper_stm32wba_scheduler_ready(scheduler)) {
        return 0u;
    }
    /* The task can also be woken by input or a stale/early timer event.
     * Re-evaluate actual deadlines, then rearm even if the one-shot expired. */
    stop_timer(scheduler);
    scheduler->immediate_wake_pending = false;
    now_ms = companion_epaper_stm32wba_now_ms(scheduler);
    for (unsigned tick = 0u; tick < (unsigned)COMPANION_WBA_SCREEN_TICK_COUNT; ++tick) {
        const uint32_t mask = COMPANION_WBA_SCREEN_TICK_MASK(tick);
        if ((scheduler->active_mask & mask) != 0u &&
            deadline_due(now_ms, scheduler->deadlines_ms[tick])) {
            due |= mask;
        }
    }
    scheduler->active_mask &= ~due;
    arm_earliest(scheduler, now_ms);
    return due;
}

void companion_epaper_stm32wba_cancel_all_ticks(
    companion_epaper_stm32wba_scheduler_t *scheduler)
{
    if (!companion_epaper_stm32wba_scheduler_ready(scheduler)) {
        return;
    }
    stop_timer(scheduler);
    scheduler->active_mask = 0u;
    scheduler->immediate_wake_pending = false;
}
