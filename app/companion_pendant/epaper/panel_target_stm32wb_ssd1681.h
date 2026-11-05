#ifndef COMPANION_EPAPER_PANEL_TARGET_STM32WB_SSD1681_H
#define COMPANION_EPAPER_PANEL_TARGET_STM32WB_SSD1681_H

#include "panel_adapter.h"
#include "expression_asset_source.h"

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef void (*companion_epaper_wait_service_fn)(void *context,
                                                 uint32_t now_ms);

typedef struct {
    bool changed;
    uint8_t x_start_byte;
    uint8_t x_end_byte;
    uint16_t y_start;
    uint16_t y_end;
    uint32_t transferred_bytes;
    uint32_t transaction_elapsed_ms;
    uint32_t busy_elapsed_ms;
    uint32_t plane_sync_elapsed_ms;
    uint32_t post_sync_bytes;
    uint8_t ready_checks;
    uint8_t control;
    uint8_t activation_count;
    uint8_t source_reset_count;
    uint8_t previous_plane_sync;
    uint8_t post_sync_command;
    uint8_t staged_region_count;
} companion_epaper_cached_mode2_report_t;

void companion_epaper_panel_stm32wb_ssd1681_init(
    comp_epaper_panel_adapter_t *adapter,
    comp_epaper_expression_asset_source_t *expression_assets);
/* One-time controller preparation for the isolated canonical sync runner.
 * Frame activations themselves remain on the no-reset native path. */
bool companion_epaper_panel_stm32wb_ssd1681_comp_req_616_prepare(void);
void companion_epaper_panel_stm32wb_ssd1681_set_wait_service(
    companion_epaper_wait_service_fn service,
    void *context,
    uint16_t period_ms);
bool companion_epaper_panel_stm32wb_ssd1681_set_temporary_partial_limit(
    uint8_t partial_limit);
bool companion_epaper_panel_stm32wb_ssd1681_enter_deep_sleep(void);
/* True between a lifecycle Mode-1 GC commit and its one required Mode-2
 * rebaseline activation. Recording start waits for this to clear so the full
 * settle cannot become the first recording-owned frame. */
bool companion_epaper_panel_stm32wb_ssd1681_mode2_settle_pending(void);
bool companion_epaper_panel_stm32wb_ssd1681_cached_mode2_diff(
    const uint8_t *previous_frame,
    const uint8_t *current_frame,
    size_t frame_bytes,
    bool persistent_content_window,
    companion_epaper_cached_mode2_report_t *report);
bool companion_epaper_panel_stm32wb_ssd1681_comp_req_611_full_0xff(
    const uint8_t *frame,
    size_t frame_bytes,
    companion_epaper_cached_mode2_report_t *report);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_PANEL_TARGET_STM32WB_SSD1681_H */
