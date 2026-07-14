#ifndef COMPANION_SCREEN_ASSETS_STM32WB_H
#define COMPANION_SCREEN_ASSETS_STM32WB_H

#include "asset_store.h"
#include "comp_spi_nor_stm32wb_spi1.h"

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    comp_spi_nor_t *nor;
    uint32_t partition_offset;
    uint32_t partition_size;
} companion_screen_assets_stm32wb_t;

bool companion_screen_assets_stm32wb_init(
    companion_screen_assets_stm32wb_t *adapter,
    comp_asset_store_t *store,
    comp_spi_nor_t *nor,
    uint32_t partition_offset,
    uint32_t partition_size);

#endif /* COMPANION_SCREEN_ASSETS_STM32WB_H */
