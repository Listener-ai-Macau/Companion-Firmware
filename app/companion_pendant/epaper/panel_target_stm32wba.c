#include "panel_target_stm32wba.h"

const char *companion_epaper_panel_stm32wba_target_name(
    companion_epaper_panel_stm32wba_target_t target)
{
    switch (target) {
    case COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55:
        return "WBA55";
    case COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA65:
        return "WBA65";
    default:
        return "WBA";
    }
}

void companion_epaper_panel_stm32wba_init(comp_epaper_panel_adapter_t *adapter,
                                          companion_epaper_panel_stm32wba_target_t target)
{
    (void)target;
    comp_epaper_panel_adapter_init_dry_run(adapter);
}

bool companion_epaper_panel_stm32wba_bind(
    comp_epaper_panel_adapter_t *adapter,
    const companion_epaper_panel_stm32wba_config_t *config)
{
    comp_epaper_panel_config_t panel_config;

    if (adapter == NULL || config == NULL ||
        (config->target != COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55 &&
         config->target != COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA65)) {
        comp_epaper_panel_adapter_init_dry_run(adapter);
        return false;
    }

    panel_config = (comp_epaper_panel_config_t){
        .hardware_present = config->hardware_present,
        .controller_known = config->controller_known,
        .width = config->width,
        .height = config->height,
        .controller_name = config->controller_name,
        .refresh = config->refresh,
        .context = config->context,
    };
    comp_epaper_panel_adapter_init(adapter, &panel_config);
    return panel_config.hardware_present &&
           panel_config.controller_known &&
           panel_config.width != 0u &&
           panel_config.height != 0u &&
           panel_config.refresh != NULL;
}
