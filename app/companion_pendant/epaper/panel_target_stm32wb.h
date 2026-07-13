#ifndef COMPANION_EPAPER_PANEL_TARGET_STM32WB_H
#define COMPANION_EPAPER_PANEL_TARGET_STM32WB_H

#include "panel_adapter.h"
#include "expression_asset_source.h"

#ifdef __cplusplus
extern "C" {
#endif

void companion_epaper_panel_stm32wb_init(
    comp_epaper_panel_adapter_t *adapter,
    comp_epaper_expression_asset_source_t *expression_assets);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_PANEL_TARGET_STM32WB_H */
