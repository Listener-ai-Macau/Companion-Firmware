#include "companion_screen_assets_stm32wb.h"

#include <stddef.h>

static bool read_partition(void *context,
                           uint32_t offset,
                           uint8_t *destination,
                           size_t length)
{
    companion_screen_assets_stm32wb_t *adapter =
        (companion_screen_assets_stm32wb_t *)context;

    if (adapter == NULL || adapter->nor == NULL || destination == NULL ||
        offset > adapter->partition_size || length > adapter->partition_size - offset) {
        return false;
    }
    return comp_qspi_nor_read(adapter->nor,
                              adapter->partition_offset + offset,
                              destination,
                              length) == COMP_QSPI_NOR_OK;
}

bool companion_screen_assets_stm32wb_init(
    companion_screen_assets_stm32wb_t *adapter,
    comp_asset_store_t *store,
    comp_qspi_nor_t *nor,
    uint32_t partition_offset,
    uint32_t partition_size)
{
    if (adapter == NULL || store == NULL || nor == NULL ||
        nor->info.size_bytes == 0u || partition_size == 0u ||
        partition_offset > nor->info.size_bytes ||
        partition_size > nor->info.size_bytes - partition_offset) {
        return false;
    }
    *adapter = (companion_screen_assets_stm32wb_t){
        .nor = nor,
        .partition_offset = partition_offset,
        .partition_size = partition_size,
    };
    return comp_asset_store_init_reader(store,
                                        COMP_ASSET_STORAGE_EXTERNAL_NOR,
                                        partition_size,
                                        read_partition,
                                        adapter);
}
