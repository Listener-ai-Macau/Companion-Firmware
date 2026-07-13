#ifndef COMPANION_EPAPER_PANEL_TARGET_STM32WBA_H
#define COMPANION_EPAPER_PANEL_TARGET_STM32WBA_H

#include "panel_adapter.h"

#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55 = 0,
    COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA65 = 1,
} companion_epaper_panel_stm32wba_target_t;

typedef struct {
    companion_epaper_panel_stm32wba_target_t target;
    bool hardware_present;
    bool controller_known;
    uint16_t width;
    uint16_t height;
    const char *controller_name;
    comp_epaper_panel_refresh_fn_t refresh;
    void *context;
} companion_epaper_panel_stm32wba_config_t;

const char *companion_epaper_panel_stm32wba_target_name(
    companion_epaper_panel_stm32wba_target_t target);

void companion_epaper_panel_stm32wba_init(comp_epaper_panel_adapter_t *adapter,
                                          companion_epaper_panel_stm32wba_target_t target);

bool companion_epaper_panel_stm32wba_bind(
    comp_epaper_panel_adapter_t *adapter,
    const companion_epaper_panel_stm32wba_config_t *config);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_PANEL_TARGET_STM32WBA_H */
