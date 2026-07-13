#include "screen_scheduler_stm32wba.h"

#include <string.h>

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
    if (scheduler == NULL) {
        return;
    }
    if (scheduler->config.stop_expression_tick_timer != NULL) {
        scheduler->config.stop_expression_tick_timer(scheduler->config.context);
    }
    if (remaining_ms == 0u) {
        companion_epaper_stm32wba_schedule_display_task(scheduler);
        return;
    }
    if (scheduler->config.start_expression_tick_timer != NULL) {
        scheduler->config.start_expression_tick_timer(scheduler->config.context,
                                                      remaining_ms);
    }
}
