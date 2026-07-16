#ifndef COMPANION_POWER_TARGET_STM32WBA_H
#define COMPANION_POWER_TARGET_STM32WBA_H

#include "power_policy.h"

#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    COMP_POWER_STM32WBA_TARGET_WBA55 = 0,
    COMP_POWER_STM32WBA_TARGET_WBA65 = 1,
} comp_power_stm32wba_target_t;

typedef bool (*comp_power_stm32wba_configure_touch_wake_fn_t)(void *context);
typedef bool (*comp_power_stm32wba_set_stop_allowed_fn_t)(void *context,
                                                          bool allowed);

typedef struct {
    comp_power_stm32wba_target_t target;
    comp_power_stm32wba_configure_touch_wake_fn_t configure_touch_wake;
    comp_power_stm32wba_set_stop_allowed_fn_t set_stop_allowed;
    void *context;
} comp_power_stm32wba_config_t;

typedef struct {
    comp_power_stm32wba_config_t config;
    comp_power_idle_settings_t idle_settings;
    bool touch_wake_configured;
    bool stop_state_applied;
    bool last_stop_allowed;
    bool last_apply_succeeded;
} comp_power_stm32wba_t;

const char *comp_power_stm32wba_target_name(comp_power_stm32wba_target_t target);

void comp_power_stm32wba_init(comp_power_stm32wba_t *target,
                              const comp_power_stm32wba_config_t *config);

bool comp_power_stm32wba_ready(const comp_power_stm32wba_t *target);

/* Configure the board-specific FT6336 interrupt wake path before allowing
 * the portable policy to request Stop. */
bool comp_power_stm32wba_prepare_touch_wake(comp_power_stm32wba_t *target,
                                            comp_power_policy_t *policy);

/* Apply only transitions. The future CubeWBA wrapper owns LPM/radio details. */
bool comp_power_stm32wba_apply_policy(comp_power_stm32wba_t *target,
                                      comp_power_policy_t *policy);

bool comp_power_stm32wba_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_POWER_TARGET_STM32WBA_H */
