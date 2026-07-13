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

typedef struct {
    companion_epaper_stm32wba_schedule_fn_t schedule_display_task;
    companion_epaper_stm32wba_timer_fn_t start_expression_tick_timer;
    companion_epaper_stm32wba_schedule_fn_t stop_expression_tick_timer;
    companion_epaper_stm32wba_now_ms_fn_t now_ms;
    void *context;
} companion_epaper_stm32wba_scheduler_config_t;

typedef struct {
    companion_epaper_stm32wba_scheduler_config_t config;
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

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_SCREEN_SCHEDULER_STM32WBA_H */
