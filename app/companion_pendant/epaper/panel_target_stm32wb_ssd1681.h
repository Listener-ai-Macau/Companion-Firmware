#ifndef COMPANION_EPAPER_PANEL_TARGET_STM32WB_SSD1681_H
#define COMPANION_EPAPER_PANEL_TARGET_STM32WB_SSD1681_H

#include "panel_adapter.h"
#include "expression_asset_source.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef void (*companion_epaper_wait_service_fn)(void *context,
                                                 uint32_t now_ms);

void companion_epaper_panel_stm32wb_ssd1681_init(
    comp_epaper_panel_adapter_t *adapter,
    comp_epaper_expression_asset_source_t *expression_assets);
void companion_epaper_panel_stm32wb_ssd1681_set_wait_service(
    companion_epaper_wait_service_fn service,
    void *context,
    uint16_t period_ms);
bool companion_epaper_panel_stm32wb_ssd1681_set_temporary_partial_limit(
    uint8_t partial_limit);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_PANEL_TARGET_STM32WB_SSD1681_H */
