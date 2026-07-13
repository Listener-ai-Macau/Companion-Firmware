#ifndef COMPANION_EPAPER_SCREEN_ASSETS_STM32WBA_H
#define COMPANION_EPAPER_SCREEN_ASSETS_STM32WBA_H

#include "asset_store.h"
#include "panel_target_stm32wba.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef bool (*companion_screen_assets_stm32wba_read_fn_t)(
    void *context,
    uint32_t partition_offset,
    uint8_t *destination,
    size_t length);

typedef struct {
    companion_epaper_panel_stm32wba_target_t target;
    uint32_t partition_size;
    companion_screen_assets_stm32wba_read_fn_t read;
    void *context;
} companion_screen_assets_stm32wba_config_t;

typedef struct {
    companion_screen_assets_stm32wba_config_t config;
} companion_screen_assets_stm32wba_t;

void companion_screen_assets_stm32wba_init(
    companion_screen_assets_stm32wba_t *adapter);

bool companion_screen_assets_stm32wba_ready(
    const companion_screen_assets_stm32wba_t *adapter);

bool companion_screen_assets_stm32wba_bind(
    companion_screen_assets_stm32wba_t *adapter,
    comp_asset_store_t *store,
    const companion_screen_assets_stm32wba_config_t *config);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_SCREEN_ASSETS_STM32WBA_H */
