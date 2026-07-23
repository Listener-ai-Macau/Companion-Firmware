#include "panel_target_stm32wb.h"

#ifndef COMPANION_EPAPER_PANEL_SSD1681_BRINGUP
#define COMPANION_EPAPER_PANEL_SSD1681_BRINGUP 0
#endif

#if COMPANION_EPAPER_PANEL_SSD1681_BRINGUP
#include "panel_target_stm32wb_ssd1681.h"
#endif

void companion_epaper_panel_stm32wb_init(
    comp_epaper_panel_adapter_t *adapter,
    comp_epaper_expression_asset_source_t *expression_assets)
{
#if COMPANION_EPAPER_PANEL_SSD1681_BRINGUP
    companion_epaper_panel_stm32wb_ssd1681_init(adapter, expression_assets);
#else
    (void)expression_assets;
    comp_epaper_panel_adapter_init_dry_run(adapter);
#endif
}

bool companion_epaper_panel_stm32wb_set_temporary_partial_limit(uint8_t partial_limit)
{
#if COMPANION_EPAPER_PANEL_SSD1681_BRINGUP
    return companion_epaper_panel_stm32wb_ssd1681_set_temporary_partial_limit(partial_limit);
#else
    (void)partial_limit;
    return false;
#endif
}
